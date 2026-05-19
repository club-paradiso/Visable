# Paradiso Backend

FastAPI service that powers the Paradiso frontend's chatbot and visa
lookup flows.

## Routes

| Method | Path                    | Purpose                                                       |
| ------ | ----------------------- | ------------------------------------------------------------- |
| GET    | `/`                     | Service descriptor for humans hitting the bare backend URL.   |
| GET    | `/health`               | Liveness probe; reports which providers are configured.       |
| GET    | `/api/visas`            | Returns the visa catalog used by the frontend visa explorer.  |
| POST   | `/api/ask`              | Chatbot endpoint. Routes to OpenRouter or Groq if configured. |
| POST   | `/api/jobcodekeywords`  | Extracts keywords from a job-code search query.               |

> The Paradiso backend is **API-only**. The human-facing frontend
> (`index.html`, `ai.html`) is deployed separately (currently GitHub
> Pages at `lucanomics.github.io/Paradiso/`). `GET /` returns a small
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
| `OPENROUTER_MODEL`      | optional  | Defaults to `openrouter/auto`.                           |
| `GROQ_API_KEY`          | optional* | Enables `/api/ask` via Groq if OpenRouter is not set.    |
| `GROQ_MODEL`            | optional  | Defaults to `llama-3.1-8b-instant`.                      |
| `SITE_URL`              | optional  | Sent as `HTTP-Referer` to OpenRouter; set to your frontend origin. |
| `SITE_TITLE`            | optional  | Sent as `X-Title` to OpenRouter. Defaults to `Paradiso`. |
| `FRONTEND_URL`          | optional  | Surfaced by `GET /` so a user who opens the bare backend URL sees where the real app lives. |
| `LAW_API_KEY`           | optional  | Reserved for future law-data integration.                |
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
2. Select **Repo:** `lucanomics/Paradiso`.
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
   # Optional, declared but not yet wired:
   # LAW_API_KEY=...
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
  block built from
  `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`,
  which mirrors the 제출서류 listed in the
  *외국인체류 안내매뉴얼 (2026.5)* — 법무부 출입국·외국인정책본부.
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
        "source_file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "source_title": "외국인체류 안내매뉴얼",
        "source_date": "2026.5",
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

`/health` should return `status: "ok"` and a `providers` map showing
which integrations are configured. `/api/visas` should return a non-
empty `data` array and `source_type: "backend-data"` (no `warning`
field) once the deploy includes `backend/data/visas.json`.

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
