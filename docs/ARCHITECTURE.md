# Visable — operational architecture

A one-page map for engineers. Details live in the linked files; when this page
and the code disagree, the code wins and this page should be fixed.

## Frontend surfaces (static, no build step)

| Surface | Entry | Main scripts / styles |
| --- | --- | --- |
| Home, unified search, status guide | `index.html` | `assets/js/unified-search.js`, `search-router.js`, `status-guidance.js`, `visa-route-guide.js`, `short-stay-checker.js` |
| Waymaker (AI answers + procedure navigator) | `ai.html` | `assets/js/waymaker-navigator.js`, `waymaker-workspace.js`, `waymaker-quick-answer.js` |
| Form Helper | `form-helper.html` | `assets/js/form-helper-app.js`, `form-engine.js` |
| Knowledge Studio (operator) | `knowledge-studio.html` | `assets/js/knowledge-studio.js` |
| New Home (nationality / naturalization) | `new-home.html`, `nationality-interview-hub.html` | `assets/js/nationality-interview-hub.js` |
| Enforcement Intelligence | `enforcement.html` | `scripts/enforcement-ui.mjs`, fallback `lib/enforcement-fallback.js` |
| PreView (separate competition MVP) | `preview.html` | `assets/js/preview/` — kept independent of Visable branding |

The backend origin is defined once in `assets/js/backend-origin.js`
(`window.VisableBackend`); pages must not hard-code it.

## Backend

- FastAPI app: `backend/paradiso_backend.py` (module name kept for deploy
  compatibility), services in `backend/services/`.
- Railway: `backend/railway.json` / `Procfile` → `uvicorn paradiso_backend:app`,
  health check `/health`. Production origin: see `backend-origin.js`.
- Vercel serverless functions in `api/` (Waymaker quick answer, enforcement
  extract/analyze, local-practice report) reuse `lib/`.

## Data sources of truth

| Data | Canonical file | Notes |
| --- | --- | --- |
| Status records | `visa_data.json` | Protected (CLAUDE.md). `backend/data/visas.json` is the deploy mirror. |
| Document master | `doc_master.json` | Protected. Mirror `backend/data/doc_master.json` via `scripts/sync_visa_data.py`. |
| Status guidance / procedures | `data/status-guidance-202609.json`, `data/local-practice-202609.json` | Built by `scripts/status_guidance/author_rules.py`. |
| Manual corpus | `data/manual-corpus/`, `backend/data/manual_search_index.sqlite3` | `npm run build:current-manuals`. Visa manual ≠ stay manual — never mix. |
| Short-stay checker | `data/short-stay/fixtures/` (SOT) → `rules.json`, `sources.json` (generated) | `audits/short-stay-country-checker/UPDATE_WORKFLOW.md`. |
| Enforcement rules | `backend/data/enforcement/legal_rules.json` | Shared by the Python service and the JS fallback. |
| Source registry / freshness | `data/source_registry.json` | `scripts/check_source_updates.py`, `short-stay-freshness.yml`. |

## Waymaker answer path (`POST /api/ask`)

1. Safety guardrails and input caps.
2. Deterministic understanding: `services/legal_analysis.py` (activities, legal
   issue types, facts) and `services/unified_search.py` (search intent).
3. Evidence: manual registry / search index, structured requirements, Korean
   Open Law grounding (`law_grounding.py`, `law_tools.py`).
4. Model call through `services/ai_runtime.py` (error taxonomy, cooldowns,
   candidate chain) — OpenRouter first; per-model failures skip to the next
   candidate, account-wide failures (credentials, bad request) stop.
5. Post-processing: confidence gate, internal-metadata scrub
   (`structured_answer.scrub_internal_metadata`, also applied line by line to
   streamed deltas), answer-shape gate, law-citation guard
   (`law_citation_guard.py`), post-generation
   safety review.
6. Public projection: provider/model/routing fields are removed unless explicit
   developer diagnostics are requested.
7. Deterministic fallback: when every candidate fails, a structured
   source-backed answer (document checklists) or a preparation note is returned
   instead of an error.

## Enforcement Intelligence

Deterministic extraction and legal baseline first (`enforcement_service.py`,
`enforcement_rules.py`); the AI may only explain. The JS fallback must classify
identically — `backend/tests/fixtures/enforcement_extraction_parity.json` is run
by both the Python tests and `scripts/check_enforcement_extraction_quality.mjs`.
When the text supports more than one provision (e.g. 제18조제2항 and
제21조제1항 together), no provision is chosen and the user is asked.

## CI

- `repo-validation.yml`: `scripts/check_repo.sh` (data validation, Node checks,
  full backend suite against a registered list of known failures), mobile render
  QA, WebKit QA, landing E2E.
- `railway-live-smoke.yml`: after a push to `main`, waits for Railway to serve
  the new commit, then probes health, Open Law and enforcement.
- Scheduled monitors: `short-stay-freshness.yml`, `source-monitoring.yml`,
  `hikorea-manual-*.yml`.
- Full Playwright matrix: `npm run test:e2e` (local; CI runs a smoke subset).

## Data verification workflow

Never mark data verified or remove `needsManualReview` without an official
source. When a source is stale and the official text cannot be compared, keep
the data, lower confidence, and show the user that the list may be outdated
(see the Jeju short-stay notice handling). OCR text is an audit aid, not a
source of requirements.
