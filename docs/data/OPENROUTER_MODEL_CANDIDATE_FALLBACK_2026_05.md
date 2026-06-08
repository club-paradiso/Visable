# OpenRouter Model-Candidate Fallback + Provider Error UX (2026-05)

Reliability + provider-error UX hardening that keeps **strict OpenRouter-first**
behavior while adding an explicit, predictable model-candidate fallback. Builds
on PR #254 (i18n + law-grounding fallback + strict Groq control).

Branch: `claude/hopeful-clarke-SeMC0` (task suggested
`feat/openrouter-model-candidates-provider-error-ux`).
Backend under test: `https://web-production-14f9a.up.railway.app`.

---

## 1. Purpose

Free OpenRouter models are occasionally rate-limited or upstream-unavailable.
When the primary model (now Nemotron Ultra free; previously Gemma free) fails for a **transient** provider reason,
Paradiso should retry an explicit, ordered OpenRouter candidate list — not
silently switch providers, not use random free-model routing, and not show raw
provider JSON to users. This PR adds that candidate fallback, a provider-error
classifier, and user-friendly localized error UX.

---

## 2. User-observed failure

A live AI request failed with:

- OpenRouter `503 openrouter_upstream_error`, raw message included **"no healthy
  upstream"**;
- a preceding provider error referenced **Google AI Studio 429** (Gemma free
  rate-limited upstream);
- model was `google/gemma-4-31b-it:free`;
- the frontend showed **raw technical JSON** to the user.

That failure now classifies as a **retryable** `upstream_unavailable` /
`rate_limited` error and triggers the next OpenRouter candidate; if every
candidate is unavailable the user sees a calm, localized "temporarily busy"
message instead of raw JSON.

---

## 3. Why raw provider JSON should not be shown to users

Raw provider JSON is confusing, may include provider internals (e.g. `user_id`,
request ids, upstream routing), and reads as a hard application error even when
the issue is transient upstream load. Paradiso now renders friendly copy by
default and keeps **sanitized** technical hints (classified error type, attempted
model ids, upstream status codes) behind a collapsed disclosure. API keys,
tokens, request headers, and user ids are never shown.

---

## 4. Candidate policy

Current ordered, explicit, de-duplicated default (primary first):

1. **Primary — `nvidia/nemotron-3-ultra-550b-a55b:free`** — instruction-tuned, long-context assistant/RAG-style default.
2. **`google/gemma-4-31b-it:free`** — strong multilingual legal/administrative fallback, but free upstream availability can be unstable.
3. **`openai/gpt-oss-120b:free`** — long-context fallback.
4. **`google/gemma-4-31b-it:free`** — later general fallback; Korean quality must be smoke-tested.

`OPENROUTER_MODEL` is always attempted first; `OPENROUTER_MODEL_CANDIDATES`
(optional, comma-separated) overrides the rest. When unset, the built-in list
above is used.

---

## 5. Why random free-model routing is not used

`openrouter/auto` (random/variable routing) gives unpredictable model behavior
and non-auditable response metadata. Paradiso needs predictable behavior and a
clear `attempted_models` / `final_model` audit trail, so random routing ids are
**rejected** (the candidate validator flags `MODEL_CANDIDATES_RANDOM_ROUTING`,
surfaced in `/health`).

---

## 6. Retryable vs non-retryable provider errors

Classifier `_classify_openrouter_error(status, message)` → `(error_type, retryable)`:

| error_type | retryable | examples |
| --- | --- | --- |
| `rate_limited` | ✅ retry next candidate | 429, "rate limit", "quota", Google AI Studio 429 |
| `upstream_unavailable` | ✅ | 502/503/504, "no healthy upstream", "overloaded", timeout |
| `provider_unavailable` | ✅ | other 5xx without a clearer reason |
| `invalid_provider_config` | ❌ stop | 401/403 invalid key, 404 model-not-found / unauthorized model |
| `invalid_request` | ❌ stop | 400 bad request / validation / malformed payload |
| `policy_or_safety_rejection` | ❌ stop | moderation / safety / content policy |
| `unknown_provider_error` | ❌ stop | unclassified |

Retryable → try the next candidate. Non-retryable → stop the loop (the failure
is config/request-level, not transient model load) and return a safe response.

---

## 7. Provider-family fallback remains explicit opt-in

Switching to a **different provider family** (Groq) is NOT the normal solution.
It happens only when `ALLOW_GROQ_FALLBACK=true` (default `false`) **and** Groq is
configured **and** every OpenRouter candidate has failed. When it happens it is
marked explicitly as `provider_family_fallback_used: true` (distinct from a
within-OpenRouter `model_fallback_used`). Otherwise all-candidates-failed returns
a deterministic limited preparation note with degraded metadata — no silent provider switch.

Non-secret response metadata: `llm_provider`, `requested_model`, `primary_model`,
`model_candidates`, `attempted_models`, `final_model`, `model_fallback_used`,
`provider_family_fallback_used`, `provider_error_type`, `upstream_statuses`,
`retryable_provider_error`, `all_candidates_failed`. Manual/law grounding and
manual-to-law fallback metadata are preserved across model retries.

---

## 8. Railway env vars

```
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
OPENROUTER_MODEL_CANDIDATES=nvidia/nemotron-3-ultra-550b-a55b:free,google/gemma-4-31b-it:free,openai/gpt-oss-120b:free,google/gemma-4-31b-it:free
OPENROUTER_MODEL_COOLDOWN_SECONDS=300
ALLOW_GROQ_FALLBACK=false
LAW_GROUNDING_MODE=audit
```

Plus secrets (`OPENROUTER_API_KEY`, `LAW_API_KEY`, law endpoint vars) configured
as Railway Project Variables. Do not commit secrets. Model ids are public catalog
identifiers, not secrets.

---

## 9. Smoke commands

Local, no provider (records skipped, exits 0):

```bash
BACKEND_URL=http://127.0.0.1:8000 python3 scripts/smoke_ai_live_quality.py
```

Deployed Railway (run from a networked machine):

```bash
BACKEND_URL="https://web-production-14f9a.up.railway.app" \
  python3 scripts/smoke_ai_live_quality.py --json
```

The harness reports the primary model + candidate list, and per question:
`attempted_models`, `final_model`, `provider_error_type`, `model_fallback_used`,
`provider_family_fallback_used`, `law_grounding_status`,
`manual_to_law_fallback_used`. Gemma 429/503 is treated as **provider-unavailable**
(not an application failure) when another candidate succeeds; all candidates
failing is **provider-unavailable** (not a grounding failure).

**Sandbox status:** the deployed Railway smoke was attempted from CI/sandbox and
**blocked by the egress allowlist** (`Host not in allowlist`). The harness records
this as a non-fatal skip (exit 0). Run the deployed command above from a networked
machine; local live-answer checks here are recorded as **skipped, not passed**.

---

## 10. Known limitations

- Free models may be rate-limited or unavailable at any time; fallback improves
  availability but does **not** guarantee answer quality.
- Gemma 4 31B Korean quality must be smoke-tested before relying on it.
- Candidate availability/ids may change on OpenRouter — verify against the live
  catalog before deploy.
- Deployed live-answer quality could not be verified from this sandbox (egress
  blocked); use the documented command.

---

## 11. Safety note

AI answers, model fallback, law grounding, manual guidance, route explanations,
deadline calculations, and checklists are preparation aids only and do not
determine eligibility, approval, or final required documents.

## 2026-05 follow-up

See [MODEL_PRIORITY_COOLDOWN_OLLAMA_SCAFFOLD_2026_05.md](MODEL_PRIORITY_COOLDOWN_OLLAMA_SCAFFOLD_2026_05.md) for the Qwen-first candidate priority, in-memory per-model cooldown behavior, deterministic fallback answer safety net, and disabled-by-default Ollama scaffold.
