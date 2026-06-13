# Law Open API Runtime Probe — 2026-06-14

**Context:** Source-grounding & law-MCP audit (`docs/audits/source-grounding-and-law-mcp-audit-2026-06-14.md`).
**Purpose:** Provide *executable* evidence about whether the National Law Information Open API
(법제처 / `law.go.kr` DRF) is actually reachable at runtime, since the previous live smoke
(`LAW_GROUNDING_LIVE_SMOKE_RESULTS.md`, 2026-05-20) ended `NOT_READY` — blocked by the
execution environment, never validated against the API itself.

## What was probed

A single, read-only `GET` against the documented runtime endpoint used by
`backend/services/law_tools.py`:

```
GET http://www.law.go.kr/DRF/lawSearch.do?OC=<oc>&target=law&type=JSON&query=출입국관리법&display=3
```

- `<oc>` = `paradiso` — the **placeholder value documented in `backend/.env.example`** (`LAW_API_OC=paradiso`).
- Timeout: 8s (matches `LAW_GROUNDING_TIMEOUT_SECONDS` default).
- No credential was stored, logged, or committed. No data file was mutated.

## Result

| Aspect | Observation |
|---|---|
| DNS / TCP / HTTP reachability | **Reachable** — HTTP response in ~245 ms (no DNS/timeout/tunnel failure) |
| HTTP status with `OC=paradiso` | **403 Forbidden** |
| Interpretation | The endpoint is reachable from this environment, but the **placeholder OC in `.env.example` does not authorize retrieval**. With the documented config, audit-mode law calls would fail and fall back to manual/generic grounding. |

This is materially different from the 2026-05-20 smoke, which got `000` / `CONNECT tunnel failed`
against the **Railway backend URL** (a transport/proxy block), and never reached `law.go.kr` at all.

## Conclusions (for the audit)

1. **The integration is real and wired** (see audit §2): `/api/ask → build_law_grounding_context → law_tools.search_laws → law.go.kr/DRF`. It is *not* decorative.
2. **It is not verified-working with the committed config.** The `.env.example` placeholder
   `LAW_API_OC=paradiso` returns 403. Live retrieval requires a **registered OC** from
   <https://open.law.go.kr/LSO/main.do> set as a deployment secret (Railway), plus
   `LAW_GROUNDING_MODE=audit` (or `enabled`).
3. **Graceful degradation holds.** On 403/timeout/parse failure, `law_tools._execute` returns a
   typed error (`LAW_API_HTTP_ERROR`, etc.); `/api/ask` keeps answering from manual grounding and
   marks `law_grounding_status="unavailable"` — no crash, no fabricated citation, no raw error to
   the user. (Verified by reading the code paths; see audit §2.4.)

## Caveats

- A 403 can also reflect IP/domain registration or User-Agent policy on the API side; the
  most likely cause given the DRF design is an unregistered/placeholder OC. Either way, the
  **documented credential does not yield law data** from this environment.
- The real Railway deployment may use a different, registered OC; that cannot be verified from
  here. The operator should run `scripts/probe_korean_law_open_api_2026_05.py` with the production
  OC from a network path that can reach `law.go.kr`, and record the result.
- This probe did not store the response body (only status + timing), and made exactly one request.
