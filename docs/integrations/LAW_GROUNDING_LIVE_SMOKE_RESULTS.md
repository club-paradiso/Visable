# LAW_GROUNDING_LIVE_SMOKE_RESULTS

Date: 2026-05-20 (UTC)  
Phase: 7 (controlled live smoke execution)  
Repository: `lucanomics/Paradiso`

## Environment tested
- Primary target: Railway (documented legacy/public backend URL)
- Local fallback: attempted, blocked by dependency install network restrictions in this execution environment

## Backend URL
- Attempted live target: `https://web-production-14f9a.up.railway.app` (documented in repository diagnostics and deployment audit docs)
- Note: this URL may represent a legacy backend. Operator confirmation is required for the current production/intended backend URL.

## Modes tested
- Disabled mode: **attempted** (live endpoint unreachable from this environment)
- Audit mode (missing key): **not executed** (unsafe to toggle production env; local audit runtime blocked)
- Audit mode (configured): **not executed** (no operator-provided non-git secrets/env in this environment)

## Commands run
```bash
BACKEND_URL=https://web-production-14f9a.up.railway.app bash scripts/smoke_law_grounding.sh
```

```bash
python3 -m venv .venv-smoke
source .venv-smoke/bin/activate
pip install -r backend/requirements.txt
(cd backend && uvicorn paradiso_backend:app --port 8000 >/tmp/paradiso_uvicorn.log 2>&1 &)
BACKEND_URL=http://127.0.0.1:8000 bash scripts/smoke_law_grounding.sh
```

## Results

| Endpoint | Expected (disabled default) | Actual status | Result | Notes |
|---|---|---:|---|---|
| `GET /health` | `200`, provider booleans, backend alive | `000` | BLOCKED | `curl: (56) CONNECT tunnel failed, response 403` when targeting Railway URL from this environment |
| `POST /api/debug/law-grounding` | `200` with `LAW_GROUNDING_DISABLED` warning | `000` | BLOCKED | Same 403 tunnel/connect failure; no body returned |
| `POST /api/ask` (legal-basis question) | Normal `/api/ask` behavior (likely `200` or provider-specific `503`) without key leakage | `000` | BLOCKED | Same 403 tunnel/connect failure; no body returned |

## Observed warnings
- Live smoke output contained repeated transport errors: `CONNECT tunnel failed, response 403`.
- No application-level law-grounding warnings could be verified because responses were not reachable.

## API key exposure check
- No API keys were printed by the smoke script output.
- No secrets were added to tracked files.

## Frontend source-panel visibility check
- Not tested in this phase (backend reachability/dependency blockers prevented end-to-end UI verification).

## Blockers
1. **Live reachability blocker:** Railway backend URL was not reachable from this environment (`curl` tunnel 403).
2. **Local execution blocker:** `pip install -r backend/requirements.txt` failed due proxy/network restrictions (`No matching distribution found for fastapi==0.115.0` after repeated tunnel 403 failures).
3. **Operator input needed:** Confirm current intended backend URL for Phase 7 live smoke (documented URL appears legacy in repo docs).
4. **Controlled env management needed:** Audit-mode tests requiring env changes must run in a non-production or explicitly controlled Railway environment.

## Decision
**NOT_READY**

Reason: Phase 7 live smoke could not validate disabled-mode or audit-mode runtime behavior due environment/network reachability limits and missing operator-controlled backend context.

## Next steps
1. Operator provides/validates the exact current backend URL for controlled smoke (Railway service + environment identity).
2. Re-run `BACKEND_URL=<validated-url> bash scripts/smoke_law_grounding.sh` from a network path that can reach Railway.
3. In a controlled non-production (or temporary audit window) environment, run audit-missing-key smoke with `LAW_GROUNDING_MODE=audit` and no `LAW_API_KEY`; capture warning markers.
4. If secure env vars are available, run configured audit-mode smoke and record only sanitized status/markers/results.
5. Update this results file with executable evidence and revise rollout decision.
