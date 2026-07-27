# Unified Search & Legal Evidence — Architecture, Ops & Runbook

Covers the law-search accuracy layer, the citation guard, the manual approval
layer, unified search, and the employment free-text extraction endpoint.

---

## 1. Architecture decision — integrating `korean-law-mcp`

Three options were on the table.

| Option | Approach | Verdict |
| --- | --- | --- |
| **A** | Port the core search/verification algorithms to Python, inside the existing FastAPI app | **Chosen** |
| **B** | Run the `korean-law-mcp` npm package as an internal Node sidecar, called by FastAPI over an internal API | Rejected |
| **C** | Keep MCP for Claude Code / operator QA only; harden Paradiso's own law adapter for production | **Chosen, alongside A** |

### Why A + C

The reusable value in `korean-law-mcp` is not its transport — it is a handful of
small, dense, hard-won pure functions: the normalization ladder, the alias
mechanism, the loose-match guard, the relevance scoring, and the wide-window
retrieval reasoning. Those are ~300 lines that port cleanly to Python and then
live inside the process that already owns `GroundingConfig`, `LAW_API_OC`
redaction, rate limiting and the evidence pack.

Paradiso's backend deploys as a single Railway service running
`uvicorn paradiso_backend:app`, with a five-package dependency set and no build
system anywhere in the repo.

### Why B was rejected

A Node sidecar would have bought us the same ~300 lines of logic at the cost of:

- a second runtime in the image, a second process to supervise, a second
  dependency tree to patch, and a second place `LAW_API_OC` exists;
- an internal network hop inside the request path for `/api/ask`;
- a second failure mode (sidecar down) that the current status enum would have
  to grow a case for;
- Railway's single-process `startCommand` no longer being sufficient.

Reuse gain did not exceed operational cost, which was the stated bar.

### What C means concretely

MCP stays an operator/QA tool. Production traffic never traverses an MCP server:
`/api/ask`, `/api/legal/*` and `/api/search/*` all reach 법제처 through
`backend/services/law_tools.py`, gated by `LAW_GROUNDING_MODE` and `LAW_API_OC`.

**Do not confuse an MCP endpoint address with the production API address.** They
are different systems with different credentials.

### Licensing

Both reference projects are MIT. Ported algorithms are recorded in
[`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md) with a
function-by-function mapping. `Public-Regulation-MCP-Builder` contributed a design
principle only — no code — and is recorded anyway.

---

## 2. Components

| Layer | File | Responsibility |
| --- | --- | --- |
| Query normalization | `backend/services/law_query_normalizer.py` | Normalization, aliases, ranking, lifecycle, status enum |
| Law retrieval | `backend/services/law_tools.py` → `search_laws_ranked` | Fallback ladder, wide window, local re-rank |
| Statute citation guard | `backend/services/statute_citation_guard.py` | 조/항/호/제목 verification against the evidence pack |
| Case citation guard | `backend/services/citation_verifier.py` | Precedent / decision citations (pre-existing) |
| Manual approval | `backend/services/manual_registry.py` | Family / version / approval state |
| Manual search | `backend/services/manual_search.py` | BM25 over the FTS index, approval-separated |
| Unified search | `backend/services/unified_search.py` | Intent routing, organic results |
| Employment NL | `backend/services/employment_nl.py` | Structured extraction + sanitization |

### Evidence status enum

`verified` · `not_found` · `repealed` · `scheduled` · `ambiguous` ·
`unavailable` · `forbidden` · `timeout` · `parse_failed`

`not_found` ("we checked; it is not there") and `unavailable` ("we could not
check") are deliberately distinct. An unknown error degrades to `unavailable`,
never to `verified` and never to `not_found`.

---

## 3. Environment variables

Backend-only. None of these may ever appear in frontend code, a response body, a
source URL, or a log line.

| Variable | Required | Purpose |
| --- | --- | --- |
| `LAW_API_OC` | for law grounding | 법제처 Open API credential. **Backend only.** |
| `LAW_GROUNDING_MODE` | yes | `disabled` · `audit` · `enabled` |
| `LAW_GROUNDING_TIMEOUT_SECONDS` | no | Per-request timeout (default 6) |
| `LAW_GROUNDING_CACHE_TTL_SECONDS` | no | Result cache TTL |
| `OPENROUTER_API_KEY` | for AI Overview / extraction | Absent ⇒ features report `unavailable` and degrade cleanly |
| `MANUAL_SEARCH_INDEX_PATH` | no | Override the FTS index path |
| `PARADISO_ENABLE_DEBUG_ENDPOINTS` | no | **Must stay unset/false in production** |
| `CORS_ALLOW_ORIGINS` | yes | Minimal allow-list |

Check presence without printing values:

```bash
for v in LAW_API_OC LAW_GROUNDING_MODE OPENROUTER_API_KEY; do
  printf '%s set: %s\n' "$v" "$([ -n "${!v}" ] && echo yes || echo no)"
done
```

---

## 4. Deploying to Railway

The service is `backend/` with `railway.json` → `uvicorn paradiso_backend:app`,
healthcheck `/health`. Nothing about the deploy shape changed in this work.

1. Set the variables above in the Railway service (never in the repo).
2. Deploy; confirm `/health` is 200.
3. Run the smoke sequence in §6.
4. Only after §7 passes, set `LAW_GROUNDING_MODE=enabled`.

### Frontend API base

The frontend resolves its backend in this order:
`window.PARADISO_BACKEND_URL` → `""` on localhost/file: → `DEFAULT_API_BASE`.

`DEFAULT_API_BASE` is currently `https://web-production-14f9a.up.railway.app`,
declared identically in `index.html`, `ai.html`,
`assets/js/legal-source-search.js`, `assets/js/unified-search.js`,
`assets/js/nationality-interview-hub.js` and `assets/js/preview/preview-app.js`.

**If the Railway domain changes, all six must change together.** Verify with:

```bash
grep -rn "up.railway.app" --include="*.html" --include="*.js" . \
  | grep -v docs/archive | grep -v node_modules
```

---

## 5. Building the manual search index

The index is a **build artifact** (`build/`, gitignored), not committed.

```bash
python3 scripts/build_manual_search_index.py      # build
python3 scripts/build_manual_search_index.py --check
```

Properties:

- Atomic: built to a temp file, integrity-checked, then `os.replace`d. A failed
  rebuild cannot damage a working index.
- Refuses to publish an empty index.
- Carries each chunk's approval state, so approved and 검토 전 content are
  separable in one query.

Absent index ⇒ `search_manuals` returns `index_unavailable`, which the UI renders
as "not searchable right now" — never as "nothing found".

---

## 6. Production smoke

```bash
BASE=https://<your-railway-domain>

curl -sS "$BASE/health"
curl -sS "$BASE/api/visas" | head -c 200
curl -sS -X POST "$BASE/api/search/unified" \
  -H 'Content-Type: application/json' -d '{"query":"D-2-1"}'
curl -sS -X POST "$BASE/api/search/unified/ai-overview" \
  -H 'Content-Type: application/json' -d '{"query":"D-2-1"}'
curl -sS "$BASE/api/search/manual-evidence-state"
curl -sS "$BASE/api/legal/laws/search?q=%EC%B6%9C%EC%9E%85%EA%B5%AD%EA%B4%80%EB%A6%AC%EB%B2%95"
curl -sS "$BASE/api/legal/precedents/search?q=%EC%B6%9C%EC%9E%85%EA%B5%AD"
curl -sS -X POST "$BASE/api/legal/research" \
  -H 'Content-Type: application/json' -d '{"question":"체류자격 변경 절차","depth":"basic"}'
curl -sS -X POST "$BASE/api/ask" \
  -H 'Content-Type: application/json' -d '{"question":"D-2 체류기간 연장","lang":"ko"}'
```

Pass criteria:

- `/api/search/unified` returns organic results **with no AI provider configured**.
- No response body contains `OC=`, an API key, or an internal hostname.
- `/api/search/manual-evidence-state` reports `approved: 0` until a human review
  record exists (that is the correct default, not a bug).

> **This session could not run the live smoke.** The egress policy for this
> environment rejects `web-production-14f9a.up.railway.app` at the proxy
> (`403` on `CONNECT`), and `law.go.kr` is likewise unreachable. Everything above
> was verified against mocked transports and a local TestClient instead. The
> commands are written to be run by an operator with network access.

---

## 7. Before setting `LAW_GROUNDING_MODE=enabled`

Do not flip this until all four pass on the deployed host:

1. **Live retrieval** — `/api/legal/laws/search?q=출입국관리법` returns the statute
   itself as the top result, not a substring neighbour.
2. **Redaction** — no response field or `sourceUrl` contains `OC=`.
3. **Citation verification** — a statute-citing answer returns a
   `citationVerification` block that is not `unverifiable`.
4. **Failure separation** — with a deliberately wrong `LAW_API_OC`, the status is
   `forbidden`, **not** `not_found`.

Until then the UI must not claim real-time verification. `audit` mode exists for
exactly this window.

---

## 8. Failure runbook

| Symptom | Status | Action |
| --- | --- | --- |
| Wrong statute returned | `verified` but `nameMatch=false` | Add the 약칭 to `LAW_ALIAS_ENTRIES`; add a regression test |
| Every law lookup `forbidden` | `forbidden` | `LAW_API_OC` rejected — re-register/rotate |
| Intermittent `timeout` | `timeout` | Raise `LAW_GROUNDING_TIMEOUT_SECONDS`; check 법제처 status |
| `parse_failed` | `parse_failed` | Upstream changed shape — check `inspect_law_api_response_shape` |
| AI Overview always unavailable | `unavailable` | `OPENROUTER_API_KEY` missing/exhausted. Organic search is unaffected |
| Manual search empty | `index_unavailable` | Rebuild the index (§5) |
| Employment interpret unavailable | `unavailable` | AI provider down; the guided flow is unaffected |

**A law-API outage must never block an answer.** Manual and structured evidence
are the primary sources; live law is legal context and citation verification.

---

## 9. Adding data

### A statutory abbreviation

`backend/services/law_query_normalizer.py` → `LAW_ALIAS_ENTRIES`. Use the official
법제처 약칭. If another real statute could be meant, list it in `alternatives` —
never silently substitute. Add a test in `test_law_query_normalizer.py`.

### A search golden fixture

`backend/tests/test_unified_search.py`. Assert the intent and that every returned
code exists in `visa_data.json`.

### An employment synonym

`data/employment/synonyms.{ko,en,zh}.json`. Map surfaces onto existing
`occupation_terms` / `industry_terms`. **Never add a code** — codes come only from
`data/jobcode_master.json`. Then:

```bash
node scripts/check_employment_code_analyzer.mjs
node scripts/check_employment_analyzer_modes.mjs
```

### Approving a manual version

`data/manual_approval_index.json` → set `approval_state: "approved"` with
`reviewer` and `reviewed_at`, **after** comparing the extracted sections against
the original document. Automation may never set `approved`. Rebuild the index and
open a PR recording what was compared.

---

## 10. Performance & security posture

- Deterministic search is local-only (visa data + FTS). Measured
  `latency.deterministicMs` in tests: single-digit to low-double-digit ms.
- The AI Overview is a separate endpoint and never blocks organic results.
- Law API calls are ladder-bounded and cached by TTL.
- Rate limits: unified 60/min, AI Overview 10/min, employment interpret 12/min,
  legal research 4/min.
- Precedent bodies are bounded; full text is reached via the official link.
- Upstream HTML is never assigned as raw `innerHTML`; every string is escaped.
- Source links are restricted to a government-host allow-list, `https` only,
  with `rel="noopener noreferrer"`. A disallowed URL renders as plain text.
- Retrieved source text is data, never instructions — it is placed in the prompt
  as quoted evidence and its citations are re-verified after generation.
- Debug endpoints are gated behind `PARADISO_ENABLE_DEBUG_ENDPOINTS` (default off).
