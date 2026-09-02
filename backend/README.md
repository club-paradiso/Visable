# Paradiso Backend

FastAPI service that powers the Paradiso frontend's chatbot and visa
lookup flows.

## Routes

| Method | Path                    | Purpose                                                       |
| ------ | ----------------------- | ------------------------------------------------------------- |
| GET    | `/`                     | Service descriptor for humans hitting the bare backend URL.   |
| GET    | `/health`               | Liveness probe; reports configured providers, the resolved LLM provider/model (no secrets), and `law_grounding_mode`. |
| GET    | `/api/visas`            | Returns the visa catalog used by the frontend visa explorer.  |
| POST   | `/api/ask`              | Chatbot endpoint. Routes to OpenRouter or Groq if configured. |
| POST   | `/api/jobcodekeywords`  | Extracts keywords from a job-code search query.               |
| POST   | `/api/debug/law-grounding` | Debug-only inspection of law grounding/citation verification (now also embeds a `preflight` block). |
| GET    | `/api/debug/law-grounding/preflight` | Operator-safe readiness preflight: resolved mode, key/endpoint configured (booleans), sample trigger + query, warning markers. No secrets, no external call. |

> The Paradiso backend is **API-only**. The human-facing frontend
> (`index.html`, `ai.html`) is deployed separately (currently Vercel at
> `visable-mu.vercel.app`). `GET /` returns a small
> JSON descriptor instead of a bare 404 so anyone — especially mobile
> users — who opens the Railway URL directly sees where to go next.

## Local development

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the values you need locally
uvicorn paradiso_backend:app --reload --port 8000
```

Quick checks:

```bash
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/api/visas | jq '.count'
curl -s -X POST http://localhost:8000/api/jobcodekeywords \
  -H 'content-type: application/json' \
  -d '{"query":"senior backend engineer Seoul"}' | jq
curl -s -X POST http://localhost:8000/api/ask \
  -H 'content-type: application/json' \
  -d '{"message":"hello"}' | jq
curl -s -X POST http://localhost:8000/api/debug/law-grounding \
  -H 'content-type: application/json' \
  -d '{"question":"출입국관리법 제10조"}' | jq
```

`/api/ask` returns `503 no_llm_provider_configured` until you set
either `OPENROUTER_API_KEY` or `GROQ_API_KEY`.


## Backend tests and repository validation

From repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python3 backend/tests/test_paradiso_backend.py
```

Or run the full repo validator:

```bash
bash scripts/check_repo.sh
```

`check_repo.sh` auto-detects missing backend test dependencies (`fastapi`, `httpx`, `pydantic`).
If missing, it bootstraps a local `.venv-check` and installs `backend/requirements.txt` there, then runs backend regression tests and golden eval with that interpreter.

### Network-restricted validation mode

In restricted environments (sandbox, proxy, or blocked package index), dependency bootstrap may fail even when repository code is healthy. In that case, run:

```bash
ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh
```

What this does:
- Runs all static/data validation checks as usual.
- If backend dependency bootstrap fails, it runs offline-safe Python syntax checks with `py_compile` on:
  - `backend/services/*.py`
  - `backend/paradiso_backend.py`
  - `backend/tests/test_paradiso_backend.py`
- Skips backend regression tests and golden eval with explicit warnings.

Important:
- Skip mode is for **restricted environments only**.
- Strict CI / production validation should run without `ALLOW_BACKEND_TEST_SKIP` so backend regression tests execute fully.

If you previously saw `ModuleNotFoundError: No module named 'fastapi'`, either:

```bash
pip install -r backend/requirements.txt
```

or re-run:

```bash
bash scripts/check_repo.sh
```

which will provision `.venv-check` automatically.

To run backend tests directly after dependencies are available:

```bash
python3 backend/tests/test_paradiso_backend.py
```

## Required and optional environment variables

All variables are read from the process environment. None are baked
into the image. See `.env.example` for the full list.

| Variable                | Required? | Notes                                                    |
| ----------------------- | --------- | -------------------------------------------------------- |
| `OPENROUTER_API_KEY`    | optional* | Enables `/api/ask` via OpenRouter.                       |
| `OPENROUTER_MODEL`      | optional  | Defaults to `nousresearch/hermes-3-llama-3.1-405b:free` (code default + `.env.example` pin). The Basic answer tier primary. Override per-deploy if the catalog changes. Always tried first for core Paradiso final answers. |
| `OPENROUTER_MODEL_CANDIDATES` | optional | Comma-separated, ordered OpenRouter fallback list (the Basic answer tier). On a **retryable** primary failure (429 rate limit / 503 "no healthy upstream"), Paradiso retries the next non-cooling candidate. Unset → built-in policy list (Hermes 3 405B → Gemma 4 26B). Random routing (`openrouter/auto`, `openrouter/free`) is warned/rejected by policy metadata. `/health` lists the resolved candidates. |
| `OPENROUTER_FAST_MODEL` / `OPENROUTER_FAST_MODEL_CANDIDATES` | optional | The Fast answer tier (UI "⚡ Fast"). Unset → built-in default (`google/gemma-4-26b-a4b-it:free` → `openai/gpt-oss-20b:free`): a light, low-latency primary plus a small fast fallback so the tier cannot collapse into the deterministic note while a model is reachable. |
| `AI_ROUTER_MODEL` | optional | Defaults to `google/gemma-4-31b-it:free`. Used as the declared low-risk router / query-classification model policy. |
| `AI_TRANSLATION_MODEL` | optional | Defaults to `google/gemma-4-31b-it:free`. Used as the declared UI/site translation model policy. |
| `AI_VERIFIER_MODEL` | optional | Defaults to `openai/gpt-oss-120b:free`. Used as the declared verifier / structured answer-audit model policy. **Note on the Basic tier:** a deploy may *intentionally* set `OPENROUTER_MODEL=openai/gpt-oss-120b:free` so Basic answers with that model — that is a valid, supported configuration, **not** an error. The concern is only when the **Fast** tier also resolves to it: Fast must use `OPENROUTER_FAST_MODEL` (default `google/gemma-4-26b-a4b-it:free`), which is independent of `OPENROUTER_MODEL`. To verify Fast and Basic are actually distinct, read the per-answer routing metadata: `answer_mode` (tier requested/used), `selected_model` (== `final_model`, the model that actually answered), and `fast_mode_fell_back` (true when Fast answered on a non-fast model). If Fast shows `selected_model=openai/gpt-oss-120b:free`, check `OPENROUTER_FAST_MODEL`/`OPENROUTER_FAST_MODEL_CANDIDATES` and that the request carried `answer_mode=fast`. |
| `AI_CHINESE_MODEL` | optional | Defaults to `deepseek/deepseek-r1-0528:free`. Reserved for Chinese-language routes only. |
| `AI_CHINESE_FALLBACK_MODELS` | optional | Defaults to `qwen/qwen3-next-80b-a3b-instruct:free,moonshotai/kimi-k2.6:free`. Reserved for Chinese-language fallback only. |
| `OPENROUTER_MODEL_COOLDOWN_SECONDS` | optional | Defaults to `300`. Retryable per-model failures are remembered in memory and skipped during cooldown. If all models are cooling down, Paradiso returns deterministic limited preparation guidance instead of repeatedly hitting upstream. |
| `GROQ_API_KEY`          | optional* | Enables `/api/ask` via Groq **only if** OpenRouter is not set and `ALLOW_GROQ_FALLBACK` is true (or, with that flag, as a last-resort provider-family fallback after all OpenRouter candidates fail). |
| `GROQ_MODEL`            | optional  | Defaults to `llama-3.1-8b-instant`.                      |
| `ALLOW_GROQ_FALLBACK`   | optional  | **Defaults to `false`** (strict OpenRouter-first posture). When `false` and OpenRouter is unset, `/api/ask` returns a safe 503 instead of silently answering via Groq. Set `true` only to opt a Groq-only deployment back in. `/health` reports the resolved value and adds `llm.warnings:["GROQ_FALLBACK_ENABLED"]` when fallback is enabled. |
| `ENABLE_OLLAMA_FALLBACK` | optional | Defaults to `false`. Future private fallback scaffold only; CI and production do not require a live Ollama server. |
| `OLLAMA_BASE_URL`      | optional  | Defaults to `http://localhost:11434`. Keep private if enabled later; `/health` does not probe it. |
| `OLLAMA_MODEL`         | optional  | Defaults to `qwen3:8b`. Used only when `ENABLE_OLLAMA_FALLBACK=true` and all OpenRouter candidates fail. |
| `OLLAMA_TIMEOUT_SECONDS` | optional | Defaults to `20`. Short timeout for optional fallback. |
| `SITE_URL`              | optional  | Sent as `HTTP-Referer` to OpenRouter; set to your frontend origin. |
| `SITE_TITLE`            | optional  | Sent as `X-Title` to OpenRouter. Defaults to `Paradiso`. |
| `FRONTEND_URL`          | optional  | Surfaced by `GET /` so a user who opens the bare backend URL sees where the real app lives. |
| `LAW_API_OC`            | optional  | **Preferred** Open Law API auth identifier (the `OC` query param for open.law.go.kr). Backend-only; never exposed in `/health`, debug, logs, or sanitized URLs. With `LAW_GROUNDING_MODE=audit` it activates the internal law tool layer. |
| `LAW_API_KEY`           | optional  | **Backward-compatibility fallback only.** Used as the OC value when `LAW_API_OC` is unset. If only this is set, `/health` adds `law_api.law_api_credential_source:"LAW_API_KEY"` and a non-secret `LAW_API_OC_RECOMMENDED` warning is surfaced. Do not overwrite an existing Railway value — add `LAW_API_OC` alongside it. |
| `DATABASE_URL`          | optional  | Reserved for future Postgres integration.                |
| `SUPABASE_URL`          | optional  | Reserved for future Supabase integration.                |
| `SUPABASE_SERVICE_KEY`  | optional  | Reserved for future Supabase integration.                |
| `CORS_ALLOW_ORIGINS`    | optional  | Comma-separated origins. Defaults to `*` (dev only).     |
| `LOG_LEVEL`             | optional  | Defaults to `INFO`.                                      |

\* At least one of `OPENROUTER_API_KEY` or `GROQ_API_KEY` is required
for `/api/ask` to return answers.

> **Never commit `.env`.** Only commit `.env.example`.

## Deploying to Railway

> **Status:** the files in this directory **prepare** Railway
> deployment but do not deploy it. Each step below is a manual action a
> human must perform once. No CI deploy hook is configured.

1. Sign in to Railway and choose **New Project → Deploy from GitHub
   repo**.
2. Select the current **Visable** repository.
3. After the service is created, open **Settings → Service → Source**
   and set **Root Directory** to `backend`.
4. Railway will detect `requirements.txt` and `Procfile` automatically.
   The start command is also pinned in `railway.json`:

   ```
   uvicorn paradiso_backend:app --host 0.0.0.0 --port $PORT
   ```

5. Open **Variables** and add the values below. At minimum, set one
   LLM provider key (`OPENROUTER_API_KEY` or `GROQ_API_KEY`):

   ```
   OPENROUTER_API_KEY=...        # or GROQ_API_KEY=...
   CORS_ALLOW_ORIGINS=https://paradiso.example.com
   SITE_URL=https://paradiso.example.com
   # Korean Open Law API grounding (preferred OC + audit mode):
   LAW_API_OC=paradiso
   LAW_GROUNDING_MODE=audit
   # Keep the EXISTING Railway LAW_API_KEY unchanged (backward-compat fallback);
   # do NOT overwrite it — just add LAW_API_OC above.
   # LAW_API_KEY=<existing value, unchanged>
   # Optional, declared but not yet wired:
   # DATABASE_URL=...
   # SUPABASE_URL=...
   # SUPABASE_SERVICE_KEY=...
   ```

   Replace `paradiso.example.com` with your real Paradiso frontend
   origin. Use `*` for `CORS_ALLOW_ORIGINS` only in development.

6. **Never commit `backend/.env`.** The repo `.gitignore` already
   excludes it; only `backend/.env.example` is tracked.
7. The service exposes `/health` and Railway uses it as the health
   check (already configured in `railway.json`).
8. After the first deploy, verify each route with curl using the
   Railway public URL — see _Verification_ below.

### Visa data file path on Railway

`/api/visas` reads from a JSON file. With **Root Directory = backend**,
the repo-root `visa_data.json` is not in the build context, so the
loader looks in three places, in order:

1. `VISA_DATA_PATH` env var (absolute path, e.g. a Railway volume mount).
2. `backend/data/visas.json` — the **committed copy** that ships with
   the backend deploy context.
3. `<repo-root>/visa_data.json` — used only when the backend is built
   from the repo root.

The committed `backend/data/visas.json` is kept in sync with the
canonical repo-root `visa_data.json` by `scripts/sync_visa_data.py`,
which `scripts/check_repo.sh` runs in `--check` mode to fail CI if the
two files drift. Update the canonical file at the repo root, then run
`python3 scripts/sync_visa_data.py` to refresh the backend copy before
committing.

`/api/visas` reports which source it served from via the `source_type`
field: `backend-data`, `repo-root`, `explicit` (from `VISA_DATA_PATH`),
or `fallback` (DEFAULT_VISAS, with an accompanying `warning`).

### Document registry path on Railway

`doc_master.json` has the same problem and the same solution. The procedure
packet builder resolves document IDs (`doc_fee_generic`) to their official
labels (`수수료`) through it; when the registry cannot be loaded the resolver
degrades to passing IDs through, and users see the raw identifier as the name
of a document to bring to an immigration office.

The loader searches, in order:

1. `DOC_MASTER_PATH` env var — when set it is the **only** candidate, so an
   operator override can never be silently replaced by a different registry.
2. `backend/data/doc_master.json` — the committed copy in the deploy context.
3. `<repo-root>/doc_master.json` — the canonical file, for local dev.

`scripts/sync_visa_data.py` keeps the copy byte-identical and
`scripts/check_repo.sh` runs it in `--check` mode to fail CI on drift.
`/api/health/ai` reports `grounding.documentRegistry` — which copy answered and
how many entries it holds.

### Manual search index on Railway

There is **no build step for it**, deliberately. The builder
(`scripts/build_manual_search_index.py`) lives at the repository root, outside
this build context, so it cannot be invoked from `railway.json`. Absence is a
supported state: manual search degrades to `index_unavailable`, and nothing
unapproved can back a direct assertion. To ground answers in production, ship a
prebuilt index as `backend/data/manual_search_index.sqlite3` or point
`MANUAL_SEARCH_INDEX_PATH` at a mounted volume.

## Verification

After deploying (or when running locally), verify each route:

```bash
BASE=https://your-paradiso-backend.up.railway.app   # or http://localhost:8000

curl -fsS "$BASE/" | jq           # service descriptor (200 OK, not 404)
curl -fsS "$BASE/health" | jq
curl -fsS "$BASE/api/visas" | jq '.count, .warning // "ok"'
curl -fsS -X POST "$BASE/api/jobcodekeywords" \
  -H 'content-type: application/json' \
  -d '{"query":"한식 조리사"}' | jq
curl -fsS -X POST "$BASE/api/ask" \
  -H 'content-type: application/json' \
  -d '{"message":"E-7 비자 갱신 요건은?"}' | jq
curl -fsS -X POST "$BASE/api/ask" \
  -H 'content-type: application/json' \
  -d '{"question":"D-2 비자 연장에 필요한 서류는?","visa_code":"D-2"}' | jq
```

`/api/ask` accepts the prompt under any of `message`, `query`, or
`question` (resolution order: `message` → `query` → `question`). The
frontend currently sends `question` plus optional metadata (`consent`,
`context`, `lang`, `visa_data`); curl-driven clients can use any
alias. Schema-only fields (`visa_code`, `visa_data`, …) are accepted
to keep the contract stable even when they are not yet consumed by
answer generation.

### Narrow manual grounding (체류기간 연장허가)

`/api/ask` ships a small set of deterministic grounding paths for
**체류기간 연장허가** questions on selected visa codes. This is
intentionally narrow and is **not** a full RAG pipeline. Currently
grounded entries (each verified against the committed PDF):

| `visa_code` | Section                                          | PDF page(s) |
| ----------- | ------------------------------------------------ | ----------- |
| `D-2`       | 유학(D-2)                                        | 43–44       |
| `D-4`       | 일반연수(D-4) — 어학연수생(D-4-1, D-4-7)          | 90–91       |
| `E-7`       | 특정활동(E-7) — 1. 제출 서류 및 확인사항           | 226         |

See `docs/manual_grounding_expansion_plan.md` for the verification
method, deferred candidates (D-10, F-6, other D-4 sub-codes, E-7
agreement tracks), and the planned next batches.

- The backend detects the visa code (from payload, `visa_data.code`,
  or a regex match in the prompt — text-detection is bounded to
  grounded codes only) and `task_type = "extension"` (from
  Korean/English wording such as "체류기간 연장", "연장 신청",
  "extension", "renew visa"). Payload variants like `d4`, `D4`,
  `e7`, `E-7` normalize to `D-4` / `E-7`.
- Sub-code variants (e.g. `D-4-2K`, `d42k`, `D-10-1`, `d101`, `F-6-1`,
  `f61`, `E-7-4`, `e74`) are also normalized and reported back as
  `visa_sub_code_detected`. Sub-code routing is governed by the
  fixture's `visa_sub_code` and `sub_codes_covered` fields (schema
  1.2), so a `D-4-2K` request does NOT silently borrow the general
  D-4 어학연수생 document list, and an `E-7-4` request does NOT borrow
  the general E-7 document list. See
  `docs/manual_grounding_expansion_plan.md` § "Schema 1.2" for the
  exact selector rules.
- When both fire, the prompt is wrapped with a Korea-specific context
  block built from the legacy compatibility fixture
  `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`,
  whose source references now point at the current June 1 stay/residence
  PDF, *외국인체류 안내매뉴얼 (2026.5; 2026-06-01 source file)* —
  법무부 출입국·외국인정책본부.
- The response carries grounding metadata on the top-level
  `AskResponse`:

  ```json
  {
    "answer": "...",
    "provider": "openrouter",
    "model": "...",
    "grounding_used": true,
    "grounding_sources": [
      {
        "source_file": "docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf",
        "source_title": "외국인체류 안내매뉴얼",
        "source_date": "2026.5",
        "source_revision_date": "2026-06-01",
        "issuing_body": "법무부 출입국·외국인정책본부",
        "visa_code": "D-2",
        "procedure_type": "체류기간 연장허가",
        "section": "유학(D-2)",
        "page_range": "43-44",
        "source_verification_status": "verified_locally",
        "source_confidence": "high"
      }
    ],
    "visa_code_detected": "D-2",
    "visa_sub_code_detected": null,
    "task_type_detected": "extension"
  }
  ```

  When no LLM provider is configured, the same metadata is returned
  inside the 503 `detail`.

- All other questions (including ungrounded visa codes and
  non-extension procedures) fall through to the existing ungrounded
  path with `grounding_used: false`. No law API, no manual chunking,
  no full RAG.

`/health` should return `status: "ok"`, a `providers` map showing
which integrations are configured, and an `llm` object reporting the
resolved provider/model — e.g. `{"provider":"openrouter","model":"qwen/qwen3-next-80b-a3b-instruct:free","configured":true,"groq_fallback_allowed":false,"warnings":[]}`.
With strict OpenRouter-first (the default), `groq_fallback_allowed` is
`false`; if you set `ALLOW_GROQ_FALLBACK=true`, `llm.warnings` includes
`GROQ_FALLBACK_ENABLED` (and `GROQ_FALLBACK_ACTIVE` when Groq is the
resolved provider). Model ids are public catalog identifiers (not
secrets); API keys are never surfaced. The resolved provider/model is
also logged once at startup. `/api/visas` should return a non-empty `data` array and
`source_type: "backend-data"` (no `warning` field) once the deploy
includes `backend/data/visas.json`.

### Law-grounding answer metadata

`/api/ask` returns law-grounding state on every answer so the frontend
source panel can be honest without overclaiming:

- `law_grounding_status` — coarse legacy field: one of `not_attempted` (no legal
  intent in the question), `disabled` (intent detected but
  `LAW_GROUNDING_MODE=disabled`), `unavailable` (attempted but no usable result /
  missing key), or `used`.
- `law_grounding_status_detail` — **granular, user-visible, mutually-exclusive**
  status (the source of truth for the "실시간 법령 확인" panel):
  - `law_grounding_not_attempted` — the question had no legal intent.
  - `law_grounding_disabled` — `LAW_GROUNDING_MODE=disabled`, **or** `enabled`
    with no `LAW_API_OC` credential (the effective-disabled rule): no external
    call, and the answer is NOT treated as real-time-law-grounded. **Scope note:**
    the "enabled-without-`LAW_API_OC`" branch is the **local / CI** default (no OC
    is configured there). It is *not* the diagnosis for Railway production, where
    `LAW_API_OC` is already set — see the environment matrix below.
  - `law_grounding_audit_only` — `LAW_GROUNDING_MODE=audit`: the lookup runs as a
    diagnostics / citation-verifier posture, never as enabled grounding, so its
    output is never presented as verified real-time law.
  - `law_grounding_verified` — `enabled` (credentialed) and the lookup returned
    usable law results. **Only this value means specific real-time statute
    citations may be trusted.**
  - `law_grounding_attempted_no_results` — `enabled` lookup ran, found nothing.
  - `law_grounding_attempted_failed` — `enabled` lookup ran but errored.
- `law_grounding_verified` (bool), `law_grounding_retrieval_timestamp`,
  `law_grounding_user_notice` (non-empty only when NOT verified), and
  `law_grounding_display` (`{verified, sources:[{source_title, law_name, article,
  source_url, relevance}], evidence_role, retrieval_timestamp, notice}`) drive
  the "실시간 법령 확인" panel.
- **Unverified-citation guardrail.** When an answer cites specific statutes/
  articles (`제24조`, `시행규칙 제18조의2`, `별표 1`, …), real-time grounding is NOT
  `verified`, and those citations are not backed by the manual/law evidence
  actually retrieved, the backend prepends an honest notice (it never silently
  presents hallucinated law). The model is also instructed, for every law-intent
  answer, not to invent article numbers from memory. Surfaced via
  `unverified_law_citation_detected`, `unsupported_law_citations`,
  `law_citations_detected`, `law_citation_guard_action`.
- `law_grounding_intent_reasons` — which intent signals fired (e.g.
  `유학/수강/계절학기`, `관광취업/워킹홀리데이/H-1`, `활동범위/자격외활동`,
  `근무처변경/이직`, `체류기간연장/연장허가`).
- `law_search_query` — the compact statutory query that would be/was issued.
  E-7 (특정활동) job-transfer questions are anchored on the official
  근무처 변경·추가 허가/신고 + 체류기간 연장허가 provisions, never on model-invented
  article numbers.
- `law_evidence_pack` — the structured evidence pack (Part D): normalized
  `law_sources`, `planned_law_queries`, `direct_manual_sources` vs
  `related_manual_sources`, `source_confidence_level`, `answer_quality_mode`,
  and localized official-confirmation questions. Secret-free (sanitized URLs).

Intent now covers activity-scope/study/working-holiday questions (H-1
계절학기 수강, 체류자격외활동, etc.), status changes, family/marriage edge cases,
humanitarian/G-1, short-term work/study, reporting duties, and overstay risk —
not just explicit legal-basis wording.

#### Environment matrix (which `law_grounding_status_detail` you get)

The status depends on **mode × credential**, so local/CI and production differ:

| Environment | `LAW_API_OC` | `LAW_GROUNDING_MODE` | Resulting status for a law-intent question |
| --- | --- | --- | --- |
| Local / CI (default) | unset | `enabled` (code default) or unset | `law_grounding_disabled` (effective-disabled: no OC) |
| Local / CI (`.env.example`) | set | `audit` | `law_grounding_audit_only` |
| Railway production (current) | **set** | `audit` | `law_grounding_audit_only` |
| Railway production (target) | **set** | `enabled` | `law_grounding_verified` (when the lookup returns usable results) |

So the bug report's "law not reflected" in **production** is the `audit` →
`law_grounding_audit_only` path (OC is present, but audit is a diagnostics
posture and is never reported as verified), **not** the missing-credential path.
To make live citations trustworthy in production, switch
`LAW_GROUNDING_MODE=enabled` (the OC is already set). The unverified-citation
guardrail protects every non-`verified` state in the meantime.

#### Post-deploy law-grounding verification checklist

After merging and setting `LAW_GROUNDING_MODE=enabled` on Railway (OC already
present), confirm grounding actually reaches `verified`:

1. **Preflight (no external call, no secrets):**
   `GET /api/debug/law-grounding/preflight`
   - `mode: "enabled"`, `external_calls: "enabled"`
   - `law_api_oc_configured: true`, `ready_for_external_calls: true`
   - `warnings` does **not** contain `LAW_API_KEY_MISSING` (a `LAW_API_ENDPOINT_MISSING`
     warning is benign — the tool layer falls back to the public DRF endpoints,
     `law_api_default_endpoint_available: true`)
2. **Selftest (one live call):** `GET /api/debug/law-grounding/selftest` →
   reports a successful Open Law API round-trip (no `LAW_API_*` error type).
3. **E-7 test question** via `POST /api/ask` (`stream:false`):
   `"E-7 체류자격자가 퇴사 후 동종업계 다른 회사로 이직하는 경우, 출입국관리법과 시행령상 근무처 변경허가 또는 신고가 필요한지 법적 근거와 함께 설명해줘."`
   - `law_grounding_status_detail: "law_grounding_verified"`, `law_grounding_verified: true`
   - `law_grounding_display.sources[]` populated; `law_grounding_user_notice` empty
   - `unverified_law_citation_detected: false`
   - `legal_issue_types` ⊇ `workplace_change_addition`, `extension`,
     `employment_condition`, `status_purpose_alignment`
4. **Fast vs Basic routing** (same question, `answer_mode` `fast` then `basic`):
   - Basic: `selected_model` == `OPENROUTER_MODEL` (intentional, e.g.
     `openai/gpt-oss-120b:free`)
   - Fast: `selected_model` == `OPENROUTER_FAST_MODEL` (≠ Basic); if it equals the
     Basic id, check `OPENROUTER_FAST_MODEL` and `fast_mode_fell_back`.

If step 3 still shows `audit_only`, the deploy is still in `audit` mode; if it
shows `disabled`, the OC is not being read by the running process.

The internal **law tool layer** (`services/law_tools.py`) is a typed, mockable
adapter over the National Law Information Open API (open.law.go.kr / DRF
endpoints). It prefers `LAW_API_OC` (falling back to `LAW_API_KEY`), builds the
`OC` parameter internally, and returns normalized, secret-free evidence. External
law-API calls only happen when `LAW_GROUNDING_MODE` is `audit`/`enabled` and a
credential is configured. `/health` exposes the posture as booleans only under
`law_api` (`law_api_configured`, `law_api_oc_configured`,
`law_api_key_fallback_configured`, `law_api_credential_source`) — never the OC/key
value. See `docs/data/LAW_API_OC_EVIDENCE_TOOL_LAYER_2026_05.md`.

## Wiring the frontend

Both `index.html` and `ai.html` define `API_BASE` from a documented
precedence chain (see `docs/backend/BACKEND_DEPLOYMENT_ALIGNMENT.md`):

1. `window.PARADISO_BACKEND_URL` if set and non-empty (highest priority).
2. `""` for local development (`localhost`, `127.0.0.1`, or `file:`).
3. `DEFAULT_API_BASE` constant (currently the legacy Railway URL).

Two ways to point the frontend at a different backend:

1. Inline override in `index.html` head:

   ```html
   <script>window.PARADISO_BACKEND_URL = "https://your-paradiso-backend.up.railway.app";</script>
   ```

2. Or proxy `/api/*` from your static-frontend host to the backend, so
   same-origin (`window.PARADISO_BACKEND_URL = ""`) works.

## Production hardening checklist

- [ ] Set `CORS_ALLOW_ORIGINS` to an explicit allow-list (do not leave `*`).
- [ ] Restrict provider keys to least-privilege scopes where possible.
- [ ] Rotate keys regularly; store them only in Railway, not in git.
- [ ] Add request logging / observability before exposing to real users.
### Law-grounding readiness preflight

`GET /api/debug/law-grounding/preflight` is an operator-safe readiness probe.
It performs **no external call** and returns **no secrets** — only the resolved
`mode`, `external_calls` (`disabled`/`audit_only`/`enabled`), whether the API key
and endpoint are configured (booleans), `ready_for_external_calls`, whether a
sample question would trigger grounding, the statutory query that would be
issued, and warning markers (`LAW_GROUNDING_DISABLED`, `LAW_GROUNDING_AUDIT_ONLY`,
`LAW_API_KEY_MISSING`, `LAW_API_ENDPOINT_MISSING`). Useful even with grounding
disabled (the default). Pass `?question=...` to probe a specific question.

```bash
curl -s "http://localhost:8000/api/debug/law-grounding/preflight" | jq
```

To enable live grounding in a controlled environment, set
`LAW_GROUNDING_MODE=audit` (or `enabled`), `LAW_API_KEY`, `LAW_API_BASE_URL`, and
`LAW_API_SEARCH_PATH` (optionally `LAW_API_ARTICLE_PATH`). Keep
`LAW_GROUNDING_MODE=disabled` by default; the preflight will report exactly which
of these are still missing without exposing any value.

### Debug-only law grounding endpoint

`POST /api/debug/law-grounding` is for development inspection only. It is not a
normal user-facing legal-advice endpoint and is not wired into `/api/ask`. Its
response now also includes a non-secret `preflight` block.

Example request:

```bash
curl -s -X POST http://localhost:8000/api/debug/law-grounding \
  -H 'content-type: application/json' \
  -d '{"question":"출입국관리법 제10조"}' | jq
```

Example disabled-mode response (`LAW_GROUNDING_MODE=disabled`):

```json
{
  "law_grounding_used": false,
  "law_grounding": [],
  "citation_verification": {
    "status": "disabled",
    "citations": [
      {
        "raw": "출입국관리법 제10조",
        "law_name": "출입국관리법",
        "article": "제10조",
        "verification_status": "not_verified"
      }
    ]
  },
  "grounding_warnings": ["LAW_GROUNDING_DISABLED"]
}
```


## Phase 6 live smoke-test readiness

- See `docs/integrations/LAW_GROUNDING_LIVE_SMOKE_TEST_PLAN.md` for the controlled smoke-test runbook.
- Optional helper script: `scripts/smoke_law_grounding.sh` (`BACKEND_URL` defaults to `http://localhost:8000`).
- Keep `LAW_GROUNDING_MODE=disabled` as the default; use `audit` only in controlled operator testing windows.
