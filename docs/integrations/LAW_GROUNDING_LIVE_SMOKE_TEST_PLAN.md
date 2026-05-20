# LAW_GROUNDING_LIVE_SMOKE_TEST_PLAN

Date: 2026-05-19  
Phase: 6 (live smoke-test readiness)  
Status: Prepared, **not production-enabled**

## Purpose
Prepare a controlled, opt-in smoke-test procedure for live endpoint verification of law/public-data grounding surfaces before any production rollout.

## Scope
- Document required environment variables for law/public-data grounding.
- Provide safe, opt-in smoke commands for `/health`, `/api/debug/law-grounding`, and `/api/ask`.
- Keep default behavior unchanged: `LAW_GROUNDING_MODE=disabled`.
- Validate debug and legal-intent gating behavior without requiring live external API calls in automated tests.

## Non-goals
- Enabling production law grounding.
- Committing real API keys/secrets.
- Modifying frontend UI behavior.
- Adding new external service dependencies.

## Required environment variables

### Law grounding
- `LAW_GROUNDING_MODE` (`disabled` | `audit` | `enabled`) — **default must remain `disabled`**.
- `LAW_API_KEY` (required only for real upstream law API calls in audit/enabled).
- `LAW_API_BASE_URL`
- `LAW_API_SEARCH_PATH`
- `LAW_API_ARTICLE_PATH`
- `LAW_GROUNDING_TIMEOUT_SECONDS` (optional, default 8)
- `LAW_GROUNDING_CACHE_TTL_SECONDS` (optional, default 86400)

### Public-data grounding
- `PUBLIC_DATA_API_KEY` (required only for real upstream public-data calls in audit/enabled)
- `PUBLIC_DATA_BASE_URL`
- `PUBLIC_DATA_VISA_PATH`
- `PUBLIC_DATA_JOB_PATH`

## Local setup
1. Copy env template:
   - `cp backend/.env.example backend/.env`
2. Keep `LAW_GROUNDING_MODE=disabled` for default/local-safe state.
3. Optionally start backend:
   - `uvicorn backend.paradiso_backend:app --reload --port 8000`
4. Run smoke script only when backend is already running.

## Railway setup checklist (controlled audit only)
- [ ] Set variables in Railway Project Variables, never in git.
- [ ] Confirm `LAW_GROUNDING_MODE` is `disabled` by default.
- [ ] For controlled smoke window only, temporarily set `LAW_GROUNDING_MODE=audit`.
- [ ] Configure `LAW_API_BASE_URL`, `LAW_API_SEARCH_PATH`, `LAW_API_ARTICLE_PATH`.
- [ ] Configure `PUBLIC_DATA_BASE_URL`, `PUBLIC_DATA_VISA_PATH`, `PUBLIC_DATA_JOB_PATH`.
- [ ] Add API keys only in Railway secrets (`LAW_API_KEY`, `PUBLIC_DATA_API_KEY`), never in repo files.
- [ ] Record smoke outputs and immediately rollback mode after test window.

## Safety checklist before enabling audit mode
- [ ] No secrets committed to repository.
- [ ] Default branch/release still uses `LAW_GROUNDING_MODE=disabled`.
- [ ] Debug endpoint access is limited to controlled operator validation.
- [ ] Test plan includes rollback step.
- [ ] Stakeholders understand `enabled` mode is blocked until audit evidence is complete.

## Smoke-test commands (opt-in)
Use `scripts/smoke_law_grounding.sh` (defaults `BACKEND_URL=http://localhost:8000`).

Manual equivalents:

```bash
curl -sS "$BACKEND_URL/health"
curl -sS -X POST "$BACKEND_URL/api/debug/law-grounding" \
  -H 'content-type: application/json' \
  -d '{"question":"출입국관리법 제10조"}'
curl -sS -X POST "$BACKEND_URL/api/ask" \
  -H 'content-type: application/json' \
  -d '{"question":"출입국관리법 제10조 근거를 알려줘"}'
```

## Expected disabled-mode response
- `LAW_GROUNDING_MODE=disabled`
- `/api/debug/law-grounding` returns 200 with warnings including `LAW_GROUNDING_DISABLED`.
- `/api/ask` legal question should not expose law-grounding to normal users; no live law retrieval occurs.

## Expected audit-mode missing-key response
- `LAW_GROUNDING_MODE=audit` + missing/blank `LAW_API_KEY`
- `/api/debug/law-grounding` should include warning `LAW_API_KEY_MISSING` (or `SOURCE_UNAVAILABLE` when source is not callable).

## Expected audit-mode configured response shape
- `LAW_GROUNDING_MODE=audit` + configured URLs + API keys in environment.
- Response should include structured metadata fields (e.g., `law_grounding_used`, `law_grounding`, `grounding_warnings`) without exposing secret values.
- `/api/ask` should set `law_grounding_attempted=true` only for legal-intent questions.

## Rollback plan
1. Reset `LAW_GROUNDING_MODE=disabled`.
2. Re-run health/debug checks to confirm disabled warnings.
3. Remove temporary smoke window notes and keep only audit records.
4. If any instability observed, keep audit mode off and file follow-up issues.

## Production enabling criteria
Production `enabled` mode is blocked until all are satisfied:
- Controlled smoke tests completed in local and/or Railway with real env vars.
- Evidence shows stable response shape and safe failure behavior.
- No key leakage in logs or API responses.
- Legal-intent gating verified (`law_grounding_attempted` only for legal-intent in audit/enabled mode).
- Explicit approval to move from `disabled` to production strategy.

## Policy reminders
- **No real API keys should be committed.**
- **`LAW_GROUNDING_MODE=disabled` remains default.**
- **`audit` mode is controlled testing only.**
- **`enabled` mode must not be used until live endpoint behavior is verified.**

## Phase 7 execution note
Before running live smoke, confirm the exact active backend URL with an operator (the repository contains legacy Railway URL references). Do not guess unknown targets. If the execution environment cannot reach Railway (e.g., proxy/tunnel 403), record the blocker and mark live smoke as pending instead of reporting synthetic success.
