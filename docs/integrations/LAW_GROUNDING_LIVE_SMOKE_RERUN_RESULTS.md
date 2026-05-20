# LAW_GROUNDING_LIVE_SMOKE_RERUN_RESULTS

## 1) Date/time and environment
- Date/time (UTC): 2026-05-20 12:20:48 UTC
- Execution environment: Codex review container (`/workspace/Paradiso`)
- Network posture observed: outbound GitHub/package/API traffic blocked by proxy tunnel (`CONNECT tunnel failed, response 403`)

## 2) Git commit/branch inspected
- Branch: `audit/law-grounding-live-smoke-rerun`
- Commit: `7790ca4c683e077a2472845ea70ec601fce8f5f8`

## 3) Commands run
1. `git status --short`
2. `python3 -m json.tool visa_data.json > /dev/null`
3. `bash scripts/check_repo.sh`
4. `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh`
5. `rg -n "LAW_GROUNDING_MODE|LAW_API_KEY|/api/debug/law-grounding|law_grounding" backend scripts docs/integrations docs/audits docs/legal docs/ai`
6. `BACKEND_URL=https://web-production-14f9a.up.railway.app bash scripts/smoke_law_grounding.sh`

## 4) Which commands passed
- `git status --short` (clean before edits)
- `python3 -m json.tool visa_data.json > /dev/null`
- `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh` (completed with explicit backend-test skip warning)
- `rg -n ...` (search completed)
- `scripts/smoke_law_grounding.sh` executed and completed script flow (transport calls blocked; see blocked section)

## 5) Which commands failed or were blocked
- `bash scripts/check_repo.sh` failed strict backend test stage because dependency bootstrap could not reach package index:
  - `ProxyError('Cannot connect to proxy.', OSError('Tunnel connection failed: 403 Forbidden'))`
  - `ERROR: No matching distribution found for fastapi==0.115.0`
- Live smoke HTTP calls blocked by outbound proxy/network:
  - `curl: (56) CONNECT tunnel failed, response 403`
  - Status observed by script: `000` for `/health`, `/api/debug/law-grounding`, `/api/ask`

## 6) `/health` result if reachable
- Not reachable from this environment.
- Observed: status `000` due `CONNECT tunnel failed, response 403`.

## 7) `/api/debug/law-grounding` result if reachable
- Not reachable from this environment.
- Observed: status `000` due `CONNECT tunnel failed, response 403`.

## 8) `/api/ask` result if reachable
- Not reachable from this environment.
- Observed: status `000` due `CONNECT tunnel failed, response 403`.

## 9) Disabled-mode behavior
- Local code/docs signals indicate default remains disabled and guarded:
  - `LAW_GROUNDING_MODE` defaults to `disabled` in config and env example.
  - docs test plan and prior audit state continue to require disabled-by-default posture.
- Live disabled-mode endpoint behavior could not be re-verified over network because endpoint access was blocked.

## 10) Audit-mode missing-key behavior if tested
- Not live-tested end-to-end in this rerun (network blocked).
- Local code/tests indicate explicit non-crash warning paths (e.g., `LAW_API_KEY_MISSING`) and debug endpoint checks are covered in tests.

## 11) Whether any external API call occurred
- No successful external law API call occurred.
- Smoke transport attempts were made to backend URL, but all blocked before application-level response.

## 12) Whether secrets were printed
- No secrets were printed.
- No API key values were echoed in commands or outputs.

## 13) Whether law grounding is ready for production rollout
- **Not ready for production rollout** in this rerun.
- Reason: live smoke could not validate reachable backend behavior due network/proxy blocking; strict backend test bootstrap also blocked by package-index access restrictions.

## 14) Explicit verdict
- **BLOCKED_BY_ENVIRONMENT**

## Notes
- This rerun is audit/documentation-focused and does **not** enable production law grounding.
- Network/path blockages are documented verbatim rather than treated as successful live verification.
