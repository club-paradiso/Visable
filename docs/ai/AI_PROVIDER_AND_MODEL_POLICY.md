# Visable AI Provider and Model Policy

Environment variable **names** only. No values appear in this file or anywhere
else in the repository.

---

## 1. Provider precedence

| Order | Provider | When it is reached |
|---|---|---|
| 1 | OpenRouter | `OPENROUTER_API_KEY` is set |
| 2 | Groq | `/api/ask`: only if OpenRouter is unset **and** `ALLOW_GROQ_FALLBACK=true`.<br>`/api/nationality-coach`: whenever `GROQ_API_KEY` is set and the OpenRouter chain is unavailable or exhausted. |
| 3 | Ollama | Only if `ENABLE_OLLAMA_FALLBACK=true` and OpenRouter has already failed |
| — | NVIDIA NIM | Experimental, fail-closed, **not wired to any production endpoint** |

`ALLOW_GROQ_FALLBACK` defaults to **false**: strict OpenRouter-first. If
OpenRouter is unset, `/api/ask` returns a safe 503 rather than silently
answering from a different provider and a model the policy does not govern.

The coach is the one deliberate exception, and it is a narrow one: it produces
interview *practice feedback*, not source-grounded legal answers, and a
Groq-only deployment must keep working. The provider that actually answered is
always reported in the response.

---

## 2. Task roles

A feature asks for a **capability**, never a model string. A feature that
hardcodes a model is a feature nobody updates when the catalog changes.

| Role | Leads with | Rationale |
|---|---|---|
| `ROUTER` | router model | cheap classification |
| `TRANSLATOR` | translation model | glossary-protected translation |
| `FACT_EXTRACTOR` | fast chain, then basic | short structured output — but an extraction that cannot run at all is worse than one that runs on a larger model |
| `FINAL_ANSWER` | basic chain | answers a user acts on |
| `FAST_FINAL_ANSWER` | fast chain | latency promise for genuinely small questions |
| `LEGAL_SYNTHESIS` | basic chain | synthesis over retrieved sources |
| `VERIFIER` | verifier model, then basic | structured audit |
| `NATIONALITY_COACH` | fast, then basic | short structured feedback |
| `EMPLOYMENT_INTERPRETER` | fast, then basic | short structured extraction |
| `ENFORCEMENT_EXPLAINER` | basic chain | explains a statutory range |
| `ENFORCEMENT_STRUCTURED` | fast chain, then verifier | typed enforcement extraction / prediction behind deterministic rules |
| `SEARCH_OVERVIEW` | fast, then basic | short summary over search cards |

Resolution: `services/ai_runtime.py::resolve_task_models` →
`services/model_policy.py`. Deploy overrides that model policy honours apply
uniformly, instead of only to whichever feature happened to read the same
environment variable.

---

## 3. Answer tiers — what each one honestly means

| Tier | Behaviour |
|---|---|
| **Fast** | Low-latency chain. **Auto-promotes to Basic** when the question is high-risk or source-heavy — a latency promise for small questions is not a licence to answer a multi-factor immigration problem with a weaker model. Promotion reasons are returned to the client. |
| **Basic** | Default evidence-grounded answer. Never downgraded. |
| **Pro** | **Not implemented.** `resolve_question_answer_mode` returns `available: false` with `pro_unavailable_basic_fallback` and answers on the Basic chain, reported as Basic. It is never labelled Pro. |

Fast auto-promotes on: a complex legal issue type, high risk level, a
source-heavy question, permission/deadline risk, or a multi-factor question.

---

## 4. Model rules

**Random routing is forbidden.** `openrouter/auto`, `openrouter/free` and any
`*/auto` id are rejected. Which model answered an immigration question must be
auditable after the fact.

**China-origin families** (`deepseek/`, `qwen/`, `moonshotai/`, `z-ai/`) are
reserved for Chinese-language routes by policy and never enter a general chain.
Both the architecture guard and the catalog check enforce this.

**Chains are at least 3–4 deep** for final answers, so two simultaneous free-tier
outages do not force the deterministic fallback.

**Cost posture: free tier by default.** No change here introduces paid model
spend. If a deployment needs paid reliability, set `OPENROUTER_MODEL` /
`OPENROUTER_MODEL_CANDIDATES` to paid ids explicitly — a deliberate,
visible act. `/api/health/ai` reports the active chain, and
`check_model_catalog.py` flags a `:free` id that has started pricing.

---

## 5. Error taxonomy

`services/ai_runtime.py::AIErrorType`. The distinctions are the ones that change
behaviour — collapsing any two produces a real bug.

| Class | Types | Action |
|---|---|---|
| **Retryable** | `rate_limited`, `provider_overloaded`, `timeout`, `network_failure`, `empty_completion`, `malformed_provider_response` | cool the model down, advance the chain |
| **Skip this model** | `invalid_model`, `model_unavailable` | next candidate, no cooldown (a wrong slug is not transient) |
| **Fatal** | `provider_not_configured`, `invalid_provider_credentials`, `invalid_request`, `safety_rejection` | stop immediately — retrying every candidate against a broken account wastes the user's time and hides the cause |

Two rules worth stating explicitly:

* **Auth is classified before the generic 5xx bucket.** A 401/403 must never be
  treated as capacity, or an expired key burns the entire chain on every request.
* **A safety rejection is never reported as "provider offline."** The user is
  owed the real reason.

Wire-format labels are preserved through `LEGACY_ERROR_LABELS`: widening the
taxonomy must not break frontend error cards or existing clients.

---

## 6. Cooldown

One `ModelCooldownRegistry` process-wide, `OPENROUTER_MODEL_COOLDOWN_SECONDS`
(default 300). Previously each feature kept its own map, so a model that had
just rate-limited `/api/ask` was still tried at full cost by the next feature.

When every candidate is cooling down, the runtime issues **zero** requests and
returns `all_candidates_cooling_down` so the caller uses its deterministic
fallback rather than paying the timeouts again.

In-memory by design: a latency optimization, not state worth persisting.

---

## 7. Environment variable names

Providers: `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `NVIDIA_API_KEY`

Model selection: `OPENROUTER_MODEL`, `OPENROUTER_MODEL_CANDIDATES`,
`OPENROUTER_FAST_MODEL`, `OPENROUTER_FAST_MODEL_CANDIDATES`, `GROQ_MODEL`,
`AI_ROUTER_MODEL`, `AI_TRANSLATION_MODEL`, `AI_VERIFIER_MODEL`,
`AI_CHINESE_MODEL`, `AI_CHINESE_FALLBACK_MODELS`

Behaviour: `ALLOW_GROQ_FALLBACK`, `OPENROUTER_TIMEOUT_SECONDS`,
`OPENROUTER_MODEL_COOLDOWN_SECONDS`, `OPENROUTER_MAX_TOKENS`,
`OPENROUTER_FAST_MAX_TOKENS`, `ENABLE_OLLAMA_FALLBACK`, `OLLAMA_BASE_URL`,
`OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`

Grounding: `LAW_API_OC` (preferred), `LAW_API_KEY` (legacy fallback),
`LAW_GROUNDING_MODE`, `LAW_GROUNDING_TIMEOUT_SECONDS`,
`LAW_GROUNDING_CACHE_TTL_SECONDS`, `MANUAL_SEARCH_INDEX_PATH`

Full annotated list: `backend/.env.example`.

---

## 8. Secret handling

Never committed, never logged, never returned to a client, never placed in a
sanitized source URL, never in a test snapshot. `LAW_API_OC` in particular is
stripped from every surfaced URL.

`/health` and `/api/health/ai` report booleans, public model ids and classified
states only. `check_ai_architecture.py` fails the build on a committed key
shape or a credential read outside the approved adapters — while deliberately
not flagging a documented variable *name*, so `.env.example` stays useful.
