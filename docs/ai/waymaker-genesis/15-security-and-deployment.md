# 15 — Security and deployment

Status: **RESEARCHED ONLY.** This document changes no code. It consolidates the
risk registers and verification passes of six research notes, re-runs an offline
probe of the law-API response parser (§5), and records per item whether this PR
fixes it. "Fixed in this PR" means only what
[research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md) lists
(F1–F12 as of 2026-10-21; F9–F12 were added after this document was first written,
see the update notes in §3.6, §3.9 and §5). Those fixes are **IMPLEMENTED BUT NOT
VALIDATED** in production: they pass offline tests (re-run for this document,
§8), and nothing has been deployed. Every other recommendation is open.

Mission 001 "Waymaker Genesis", Part XVI. Research audited origin/main `0713370`.
This worktree is `<repo>`, branch
`research/waymaker-genesis-legal-intelligence`, based on origin/main `fc896c2`.
Live observations are the notes' own (2026-10-19, against `0713370`). The probes
in §5 ran on 2026-10-20, offline.

> **What changed since the audit, for this document.** `git diff --stat 0713370
> fc896c2` is empty for every deploy and law file cited below:
> `backend/paradiso_backend.py`, `rate_limit.py`, `requirements.txt`,
> `railway.json`, `Procfile`, `services/law_tools.py`, `legal_evidence.py`,
> `law_grounding.py`, `law_cloud_fallback.py`, `korean_law_client.py`, the
> knowledge `store.py`/`review.py`/`repository.py`, `lib/`, `api/`,
> `scripts/check_ai_architecture.py`, `railway-live-smoke.yml` and
> `hikorea-manual-sync.yml` (checked for this document). Main did add the R3
> checklist Studio (`backend/services/knowledge/checklist_*.py`, migration 0002),
> the manual reader, the search-first home and one QA workflow; §3.11 and §3.12
> cover the security-relevant parts. **Line numbers:** for `law_tools.py`,
> `law_grounding.py`, `law_citation_guard.py` and `legal_evidence.py` they are
> this worktree's (with F1–F8); every other file is unchanged since `0713370`, so
> its lines hold on main.

Evidence tags as in the notes: `[CODE path:line]`, `[TEST …]`, `[DOC …]`,
`[LIVE …]`, `[WEB url, accessed 2026-10-19]`. Status words: VERIFIED, OBSERVED,
README-ONLY, INFERRED, UNVERIFIED. Nothing here is legal advice; items marked
REQUIRES LEGAL REVIEW stay open.

Register IDs from the notes keep their prefix:

| Prefix | Source |
|---|---|
| LS-R*n*, D*n* | [research-notes/law-stack.md](research-notes/law-stack.md) §(h), §(d) |
| F*n* | [research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md) (this PR) |
| AL-R*n*, AL V*n* | [research-notes/ai-lifecycle.md](research-notes/ai-lifecycle.md) §10, §5, §6, Verification pass |
| SRC-, EXT-, CI-, SUP- | [research-notes/sources-monitoring.md](research-notes/sources-monitoring.md) §5 |
| KP-*n* | [research-notes/knowledge-platform.md](research-notes/knowledge-platform.md) §7 and verifier claims |
| RO §*n* | [research-notes/ref-ops-license.md](research-notes/ref-ops-license.md) §1 (third-party behaviour, described only) |
| TD §*n* | [research-notes/training-distill.md](research-notes/training-distill.md) §0, §3 |
| OA §*n* | [research-notes/official-api.md](research-notes/official-api.md) |
| CO §*n* | [research-notes/cost.md](research-notes/cost.md) §0, §1 |
| ESA-*n* | the matching row in [01](01-existing-system-audit.md) §9 |

## 1. Register at a glance

Severity is the source note's own; `(new)` marks a severity set here (INFERRED).
Where a fix covers part of a risk, the row is split as in [01](01-existing-system-audit.md):
the `a` row is the fixed part, the `b` row stays open.

| ID | Area | Sev | Risk in one line | From | ESA | Fixed in this PR | Owner decision |
|---|---|---|---|---|---|---|---|
| SEC-01 | Access control | high | Diagnostics opt-in was open in production: any caller could request the internal payload | AL-R4 | 03 | **Resolved outside this PR**: PR #666 (merged 2026-10-20, `8cae0cf`) reads `VISABLE_DIAGNOSTICS_TOKEN`; the owner set it on Railway and as the repository secret; `/health` reports `client_diagnostics_mode: token` and the next Railway Live Smoke passed (OBSERVED 2026-10-20) | Done by the owner |
| SEC-02 | Model providers | critical (TD §0.3) | Real user questions go to free channels whose published terms bar personal data or production use (whether they bind OpenRouter-mediated calls is UNVERIFIED) | TD §0.3, §3.3 | 02 | No | **Yes**, with counsel |
| SEC-03 | Deployment | high | `main` is unprotected and every merge deploys within minutes | CI-01 | 16 | No | **Yes** |
| SEC-04 | Timeouts | high | Blocking law I/O on the event loop; no end-to-end deadline; unbudgeted retries | LS-R3, AL-R9, AL V2 #2 | 11 | No | Latency target only |
| SEC-05a | Negative caching | high | Failure shown or cached as absence on D1, D2, D3, D5, D8 | LS-R4, LS-R9 | 10a, 34a | **Yes**: F3, F4, F5, F6 | No |
| SEC-05b | Negative caching | high | Remaining failure-as-absence paths, incl. the missing-OC envelope and any well-formed body of unexpected shape | LS §(d), OA V-E, AL-R14, §5 | 10b, 34b | **Mostly (F9)**: empty, HTML, official-envelope and unexpected-shape bodies are now typed errors in `law_tools`/`legal_evidence`. Open: `precedent_sources` empty-body path, detail-fetch failure after a successful search, D4 | No (D4 sits in an owner file) |
| SEC-06a | Credentials | medium | `LAW_API_BASE_URL` sent the OC to any host | LS-R7 | 32a | **Yes**: F8 | Check the preflight after deploy |
| SEC-06b | Credentials | medium | OC still resent over plaintext HTTP on a connection failure; redirects unchecked; legacy Bearer client | LS-R7, LS verifier omission 3 | 32b | **Partly**: F12 refuses redirects off www.law.go.kr / law.go.kr and https→http downgrades (an off-host 302 used to receive the OC 3 times per search); F8 limits the base URL and logs the plaintext retry. The retry itself and the legacy client remain | **Yes**: after the log check |
| SEC-07 | Rate limits | medium | Unauthenticated, un-rate-limited law proxies spend the owner's OC | LS-R8 | 33 | No | **Yes**: keep them public? |
| SEC-08 | Structured data | high | Client-supplied `visa_data` becomes "manual-backed" prompt evidence | AL-R3 | 13 | No | No |
| SEC-09 | Prompt injection | medium (new) | No data-not-instructions framing; one concatenated user message | AL §5 | 31 | No | No |
| SEC-10 | Parser | medium (new) | Stdlib XML without DTD rejection, unbounded body, superlinear error walk, `RecursionError` escaping a "never raises" API | §5 probe | — | **Partly (F11)**: `RecursionError` is mapped to `law_api_parse_error`; the official-error walk is bounded (a 600-deep, 0.97 MB body: 10.3 s → 4 ms). Open: response byte cap, DOCTYPE/ENTITY rejection, parsing off the event loop | No |
| SEC-11 | Rate limits | medium | Rate-limit key is the first `X-Forwarded-For` token | AL-R10 | 39 | No | No |
| SEC-12 | Second runtime | medium | Vercel AI functions: own model lists, no rate limit, open quota sink | AL-R8, AL V2 #3 | 30 | No | **Yes**: retire or govern |
| SEC-13 | Model fallback | medium | Fallback and stream paths bypass most answer guards; coach reaches Groq without opt-in | AL-R6, TD verifier #1 | 28 | No | **Yes**: Groq for the coach |
| SEC-14 | Cost | medium | No token telemetry; paid enforcement chain; the free daily quota is the binding limit | CO §0.1–0.3, AL-R7 | 29 | No | **Yes**: paid intent, budget |
| SEC-15 | Supply chain | medium | Unpinned tool installs, tag-pinned actions, no lockfile, unpinned production Python | SUP-01, SUP-02, CI-04 | 44, 43, 52 | No | Partly |
| SEC-16 | Privilege | medium | One operator can publish alone in both Studios; raw SQL can edit published citations | KP-3, KP verifier #4, §3.11 | 25 | No | **Yes**: separation of duties |
| SEC-17 | Credentials | low (new) | Database and Supabase service secrets configured but unused by the AI path | AL §3.3 | 54 | No | **Yes**: remove if unused |
| SEC-18 | CI privilege | medium | Write-token job with unpinned installs; shell-interpolated dispatch inputs | SUP-01, sources-monitoring §4.1 | 44 | No | No |
| SEC-19 | Exposure | low | Public health endpoints and responses expose model ids and routing state | AL §6, AL-R17 | 51 | No | **Yes**: what may be public |
| SEC-20 | Cost | low | Live smoke spends production model quota and the OC on every push | CI-05, LS verifier omission 5 | 50 | No | No |
| SEC-21 | Durability | medium | Knowledge store on an ephemeral filesystem unless a volume is mounted | KP-4 | 26 | No | **Yes**: confirm the volume |
| SEC-22 | Source identity | medium | No version store, so no historical immutability or hash-checked cache | LS-R6, SRC-02 | 12 | No | No |
| SEC-23 | Hestia | — | Government-use boundaries are undefined | §6 | — | No | **Yes** |
| SEC-24a | Partial responses | medium | Python article parsing matched heading units and dropped 항/호/목 text | LS-R5 | 35a | **Yes**: F7 | No |
| SEC-24b | Partial responses | medium | Page-limited searches and flattened manual tables still read as complete; JS article parser unchanged | LS-R5, EXT-01, EXT-04 | 35b, 19 | No | No |

F1 (statute rows reach the evidence pack) and F2 (the citation guard binds article
numbers to fetched articles) are answer-integrity fixes, recorded as ESA-08 and
ESA-09a in [01 §9](01-existing-system-audit.md). They matter here through SEC-13 only
(§3.14).

## 2. Deployment topology (as audited)

| Component | State | Evidence |
|---|---|---|
| Static site + serverless | Vercel `visable-mu.vercel.app`, no build step. `api/` serves quick-answer and enforcement analyze/extract/confirm/law-probe/openrouter-probe | [DOC ai-lifecycle.md §1] VERIFIED; quick answer OBSERVED |
| Backend | Railway, NIXPACKS. `backend/railway.json` `startCommand` has no `--workers`. uvicorn 0.30.6 takes its worker count from `WEB_CONCURRENCY` when set, and the Railway env was not read, so "single worker" is INFERRED | [DOC law-stack.md verifier omission 4] |
| Production runtime | No `runtime.txt` or `.python-version`, so the production Python, and the expat it bundles (§5), is unpinned | [DOC sources-monitoring.md §4.5] INFERRED |
| Knowledge store | SQLite at `WAYMAKER_KNOWLEDGE_DB` or a default repo path. `railway.json` declares no volume. On an ephemeral filesystem the default path opens and reports `durable=True`. Since `fc896c2` the same store also holds the checklist Studio tables (migration 0002) | [DOC knowledge-platform.md KP-4, verifier claim 15] production volume UNVERIFIED; [CODE backend/services/knowledge/api.py:342-343 at fc896c2] VERIFIED |
| Deploy trigger | Push to `main` → Railway serves the new commit about 2 minutes later (smoke run 38292940698). Vercel's Git integration is INFERRED | [DOC sources-monitoring.md §3.3] OBSERVED |
| Branch protection | `branches/main/protection` → 404, `/rulesets` → `[]`, `/rules/branches/main` → `[]`. Actions default token permission `read` | [DOC sources-monitoring.md §3.3, verifier claim 10] OBSERVED 2026-10-19 |
| Live config | Railway served `0713370`; law grounding `enabled` via `LAW_API_OC`; `client_diagnostics_mode: open`. Not re-observed against `fc896c2`; the code paths are unchanged (above) | [DOC law-stack.md verifier claim 10; ai-lifecycle.md VL1] OBSERVED 2026-10-19 |

## 3. Operational controls

Each subsection gives the current state, the risk, the recommendation, whether this
PR fixes it and whether the owner must decide something.

### 3.1 Timeouts and deadlines (SEC-04)

- **State.** Per law call 8 s (`LAW_GROUNDING_TIMEOUT_SECONDS`). Statute-stage
  budget 12 s (clamped 1–30 s), applied only inside `build_law_grounding_context`.
  The pack's precedent search and `legal_evidence` have no budget. OpenRouter: 60 s
  per call (code default; the env var is set on Railway, value not observable), 45 s
  chain budget with a 12 s reserve, counted from chain entry. Browser abort 75 s;
  Vercel quick answer 7 s per model; the coach's `AIRuntime` has no chain budget (up
  to 7 candidates × 60 s, INFERRED worst case). [DOC law-stack.md §(e);
  ai-lifecycle.md §3.4] VERIFIED.
- **No end-to-end deadline.** Law grounding, planned-source retrieval and
  `retrieve_legal_evidence` all run before the 45 s chain starts, and `/api/ask`
  passes no `chain_budget_seconds`, so the worst case exceeds the 75 s browser abort
  and the server keeps working after the user has gone. [DOC ai-lifecycle.md V2 #2]
  VERIFIED (code), timing INFERRED.
- **Event loop.** `/api/ask`, `/api/legal/*` and research call synchronous `urllib`
  inside `async def` handlers; only enforcement uses `asyncio.to_thread`. [DOC
  law-stack.md R3, verifier claim 5; ai-lifecycle.md V1 claim 14] VERIFIED. The
  parser itself can spend about 0.3–1.4 s of CPU on a hostile body (§5), on the same
  loop.
- **Risk.** One slow upstream stalls every concurrent request on the worker and
  keeps spending OC and model quota for a user who has already timed out.
- **Recommendation.** One per-request deadline, shorter than the client abort, held
  in a `contextvars` context and consumed by every stage (statute, precedent,
  `legal_evidence`, model chain). Each stage gets `min(remaining, stage cap)`. Run
  law calls and parsing in `asyncio.to_thread` or an async client. Derive the
  numbers from Waymaker's own measurements, not from a third-party constant set
  [DOC ref-ops-license.md §4.1].
- **Fixed in this PR:** No (law-stack-fixes.md, "Not done here": async I/O and
  budget). **Owner:** only the user-facing latency target.

### 3.2 Retries

- **State.** `legal_evidence` makes up to 3 attempts (0.5 s and 1 s backoff) over up
  to 4 query variants × 2 types: 24 attempts for one question when the upstream
  times out (12 with precedents only) [DOC law-stack.md verifier claim 5] VERIFIED.
  The notes list 5xx among the retried cases. Reading the condition for this
  document: with the default urllib transport a 5xx arrives as `ok=False,
  error_type="http_error"` [CODE backend/services/law_tools.py:223-225], and the
  retry test treats only `timeout`/`network`, or an `ok` response with status ≥ 500,
  as transient [CODE backend/services/legal_evidence.py:845]. So in production only
  timeouts and connection failures are retried (VERIFIED by code read; not probed).
  The default transport also swaps https↔http on a `network` error
  [CODE legal_evidence.py:798; law_tools.py:253-281], so a connection failure can
  cost up to 6 sends per request, 3 of them in plaintext with the OC [DOC
  law-stack.md verifier omission 3] INFERRED. OpenRouter failed attempts count
  toward the free daily cap [DOC cost.md §0.2] VERIFIED (provider docs).
- **Risk.** Retry storms multiply upstream load and quota use; retrying a timeout
  inside a user request rarely succeeds.
- **Recommendation.** No retry on timeout inside a user request. Retry once on
  429/503, honouring a clamped `Retry-After`. Never retry with a different scheme.
  A per-upstream-family circuit breaker whose open state is a typed
  `LookupStatus.UNAVAILABLE_*` result, never absence. Count every attempt against
  the request budget (`LookupResult.calls`, [CODE
  experiments/waymaker-ai/waymaker_ai/contracts.py:331-336]).
- **Fixed in this PR:** No. F5 changed which error the ranked ladder *reports*, not
  how often it retries. **Owner:** no.

### 3.3 Inbound rate limits (SEC-07, SEC-11)

- **State.** In-memory sliding windows: `/api/ask` 8/min and 300/day, research 4/min,
  unified overview 10/min, coach 6/min, employment 12/min, enforcement 10/8/2 per
  minute, debug 5/min [DOC ai-lifecycle.md §2.1, §2.3; law-stack.md §(e); cost.md §2]
  VERIFIED. The key is the first `X-Forwarded-For` token that parses as an IP, else
  the socket peer [CODE backend/rate_limit.py:65-87] VERIFIED (re-read). Whether
  Railway's proxy replaces or appends that header is UNVERIFIED.
  `/api/legal/laws/search`, `/precedents/search` and `/precedents/detail` have no
  limit [CODE backend/paradiso_backend.py:6898, 6926, 6961] VERIFIED (re-read), and
  neither do the Vercel quick-answer, law-probe and analyze functions [DOC
  law-stack.md §(e); ai-lifecycle.md §2.4].
- **Risk.** If the proxy appends, a rotating fake first hop bypasses every limit and
  burns provider quota (AL-R10). The law proxies let anyone spend the owner's OC: one
  query can become about 13 upstream calls through the cloud fallback (LS-R8). F6
  removes the cached replay of failed and empty `legal_evidence` responses, so a
  repeated no-results or error question now costs one upstream request each time
  [DOC law-stack-fixes.md, "Behaviour the owner should know", item 4]. Limits are per
  process, so more workers multiply them (INFERRED).
- **Recommendation.** Key on the right-most trusted hop, or on the platform's
  client-IP header once its behaviour is confirmed. Add `rate_limit` dependencies to
  the three `/api/legal` routes. Rate-limit the Vercel functions or route them
  through Railway. Budget cost-bearing upstream calls, not inbound requests.
- **Fixed in this PR:** No. **Owner:** should the law proxies and the Vercel
  law-probe be public at all?

### 3.4 Outbound quotas

- **law.go.kr.** No numeric quota is published on any page fetched. Use can be
  restricted for traffic overload, or for commercial use of APIs that are not
  licensed for it; no page names those APIs (UNVERIFIED). Per a 2015 Q&A an OC works
  only from registered IPs, a browser call needs a matching referer domain, and
  `target`/`type` must match the approval; current enforcement is UNVERIFIED. A
  production (운영) application requires registering the app as a 활용사례.
  `display` is capped at 100. [DOC official-api.md §5] VERIFIED.
- **OpenRouter `:free`.** 20 requests/min; 50/day for accounts that have bought
  fewer than 10 credits, 1,000/day after. That caps Waymaker at about 1,500 or about
  30,000 LLM calls a month (INFERRED), shared by `/api/ask`, Quick Answer,
  enforcement, the coach and the CI smoke. [DOC cost.md §0.2]
- **Dead ids.** Five configured model ids are absent from the OpenRouter catalog, so
  Quick Answer and Vercel analyze are effectively one model deep, and each dead id
  is a failed attempt against the cap. [DOC training-distill.md verifier claim 3;
  cost.md §1] OBSERVED.
- **Risk.** Quota exhaustion looks like provider failure and falls through to the
  deterministic fallback. Throttling by law.go.kr would arrive as errors that several
  paths still report as "no results" (§3.6).
- **Recommendation.** Count calls per upstream family per day and expose them as an
  operator metric; alert at 50 % and 80 % of the free bucket; tag CI traffic; remove
  dead ids; request every target family on the OC application before code depends
  on it [DOC official-api.md §8 item 7] INFERRED.
- **Fixed in this PR:** No. **Owner:** whether to buy credits (50 → 1,000/day);
  whether to file additional OC target approvals.

### 3.5 Cache freshness, historical immutability and invalidation (SEC-22)

**State** [DOC law-stack.md §(e), LS-R9] VERIFIED, with F6 applied:

| Cache | Behaviour |
|---|---|
| Statute lookups | None across requests; per-request dicts only |
| Cloud-fallback pages | Module dict, TTL 15 min, unbounded. Key = credential *source name* + host + page parameters. Caches OK **and empty** pages (D7, open) |
| `legal_evidence` | Module dict, TTL 24 h (`LAW_GROUNDING_CACHE_TTL_SECONDS`), unbounded, key without OC or credential fingerprint. **Since F6:** caches only a body that parses without a typed error and yields at least one case record [CODE legal_evidence.py:762-774, 852-853]. It still stores the raw `LawHttpResponse`, not a parsed record, and it parses each successful body once more to decide (so §5's parse cost is paid twice on that path) |
| Vercel JS | None |
| Version identity | No version store, content hash or retrieval-version record; `source_id` prefers 법령ID over MST (LS-R6) |

Upstream DRF responses carry `Cache-Control: max-age=0, no-store, no-cache,
must-revalidate` (re-read for this document in the headers saved with the documented
samples, `scratchpad/apiguide/live/s1_headers.txt` and `s3_headers.txt`). That is an
HTTP-cache directive. No page read in this mission turns it into a usage term, and
the open.law.go.kr copyright policy guarantees free use including commercial use
[DOC official-api.md §6] (INFERRED: application-level storage of parsed public law
text is not restricted by it).

**Rules** (consistent with [06 §1](06-temporal-law-and-source-identity.md) and the
source-bundle record fields `version_id`, `effective_date`, `retrieved_at`,
`content_sha256`, `provenance`):

| Class | Key | Lifetime and invalidation |
|---|---|---|
| Historical version text (a later version is in force) | `(stable_id, version_id, effective_date, parser_version)` | Immutable once captured with `content_sha256`. Re-fetch only on a parser-version change or an explicit operator action. A re-fetch with a different hash is a conflict to review, never a silent overwrite (upstream corrections are possible, INFERRED) |
| Current-version pointer | `stable_id` | Short TTL. Invalidate from the daily change feed (`lsHstInf`; article history by date is previous-day data) [DOC official-api.md §2.4, §5, §8]. The pointer changes; version text does not |
| Pending (시행예정) version | `(stable_id, version_id, effective_date)` | Text immutable; its status flips on the effective date, so re-check that day ([06 §3](06-temporal-law-and-source-identity.md) step 7) |
| Title → identity index | compacted title | TTL ≤ 1 day, with a coverage flag (current titles only = `partial`) |
| Search pages | query + parameters | Short TTL; an error is never stored as a page |
| Negative entries | §3.6 | §3.6 |

Keys use `(version_id, effective_date)`, never the 법령일련번호 alone: one MST appears
under several 시행일자 (시행규칙 `289833` at 2026-09-15 and 2027-09-16; MST 140323
twice in the eflaw sample) [06 §1; DOC official-api.md §2.2 verifier addition]. Keys
include a credential fingerprint (never the OC), because what a key may read depends
on its approvals, and the WLIE contract version. Caches are bounded LRUs and hold
parsed records, never raw bodies, which can carry OC-bearing links (§3.9).

- **Fixed in this PR:** Partly. F6 stops `legal_evidence` caching failures and empty
  bodies (SEC-05a). Bounds, fingerprints, the fallback's empty-page cache and any
  version store remain (law-stack-fixes.md, "Caches"; spec 06). **Owner:** none
  beyond durability (SEC-21).

### 3.6 Negative caching and failure-as-absence (SEC-05a, SEC-05b)

> **Update 2026-10-21 (F9).** The bodies listed under "Still open" below are now typed errors, never `law_api_no_results`: an empty or HTML body (`law_api_bad_response`), the missing-OC `{result, msg}` envelope and other official envelopes (`law_api_official_error`), and a well-formed body with no explicit empty answer (`law_api_parse_error`). "No results" now requires `totalCnt` 0 or an explicit empty list. A cited law whose search hits one of these is reported as citation `error` + `SOURCE_UNAVAILABLE`, not `CITED_LAW_NOT_FOUND`. Details and the paths that remain open: [law-stack-fixes.md](research-notes/law-stack-fixes.md) F9.

- **Contract.** `LookupStatus.NOT_FOUND` is the only absence; every `UNAVAILABLE_*`
  and `UPSTREAM_ERROR` is a failure; `Coverage.PARTIAL` marks an index that could not
  have returned the item [CODE experiments/waymaker-ai/waymaker_ai/contracts.py:306-328].
  A failed or partial lookup is never evidence of absence
  ([07 §2](07-evidence-verification-design.md), invariants 1–2).
- **Fixed in this PR (SEC-05a)** [DOC law-stack-fixes.md F3–F6]:
  - D1/D2 (F3): a failed search for the law the user cited is now `verification_status:
    "error"` with `SOURCE_UNAVAILABLE`, not `CITED_LAW_NOT_FOUND`, and a real error
    outranks a no-results marker in the status detail.
  - D3 (F4): budget exhaustion maps to `timeout`, unknown codes to `unavailable`.
  - D5 (F5): the ranked ladder keeps the first infrastructure error.
  - D8 (F6): `legal_evidence` no longer caches HTTP-200 official-error bodies or empty
    bodies for 24 h. F6 also leaves genuine no-results uncached, which satisfies rule
    1 below by not caching absence at all.
  - Each defect fails on HEAD and passes on the fix (law-stack-fixes.md, "How fails
    before, passes after was shown"). Re-run for this document: §8.
- **Still open (SEC-05b).**
  - D4: a planned but never queried family is marked `no_results` (`legal_analysis.py`,
    an owner file). D6: an empty HTTP-200 body becomes `law_api_no_results`. D7: the
    cloud fallback caches empty pages for 15 min. D11: JS `fetchJson` returns `null`
    for every failure. D12: relevance-filtered precedents are labelled `no_results`.
    [DOC law-stack.md §(d)] VERIFIED (code).
  - A lawService detail failure after a successful search is still
    `failed_verification`; the `build_law_grounding_context` exception path
    [CODE backend/services/law_grounding.py:547-558] returns no `error_type`, so a
    crash in the statute stage still projects as statute `no_results` [DOC
    law-stack-fixes.md F3, F4 residual risk]. §5 shows one concrete way into that
    path.
  - **The missing-OC envelope.** law.go.kr answers a request without OC with HTTP 200
    and a JSON body holding `result` and `msg` keys and no `resultCode` [DOC
    official-api.md, Verification pass V-E] OBSERVED. `_official_error_info` reads
    `msg` for a few error words and never reads `result` [CODE law_tools.py:589-632].
    Re-run on this worktree: `parse_law_search_response` still returns
    `law_api_no_results` for it (§5). F1–F8 do not touch the detector [DOC
    04-official-api-capability-matrix.md §2 item 7]. Whether invalid-OC and
    unregistered-IP failures use the same envelope is UNVERIFIED.
  - **Any well-formed body of unexpected shape** (an undocumented envelope, a schema
    change, a tampered body) is read as an authoritative "no results"; for a cited law
    that becomes `failed_verification` + `CITED_LAW_NOT_FOUND` (§5, OBSERVED offline).
  - The reverse merge: `source_grounding` maps `no_results` to
    `temporarily_unavailable` (AL-R14).
- **Risk.** A credential or IP problem, or an upstream format change, reads as "no
  such law" or "no such precedent". The reference project's own measurements
  describe an empty body on search endpoints as an outage signal [DOC
  ref-ops-license.md §1.7] README-ONLY.
- **Rules.**
  1. Only `NOT_FOUND` with `Coverage.COMPLETE` may be cached as absence, with a TTL
     of minutes, and never for a law the user cited (re-check it).
  2. `UNAVAILABLE_*` may be cached only as a typed circuit-breaker state, keyed by
     upstream family (not by query), for seconds, and rendered as "could not check".
  3. `NOT_FOUND` from partial coverage becomes `historical_lookup_required` and is
     not cached as absence.
  4. Classify first, cache second: store parsed successes, never raw responses.
  5. "No results" requires positive evidence of an empty result (the expected root
     and list key present with zero rows, or `totalCnt` = 0). A body that lacks the
     expected structure is `UNAVAILABLE_PARSE`, and an empty body is
     `UNAVAILABLE_*` (INFERRED rule; it needs Waymaker's own capture data, RO §5).
- **Owner:** no (D4's file is on the owner's list, so the owner merges that change).

### 3.7 Partial responses (SEC-24a, SEC-24b)

- **State.** Law search requests 5 rows by default (100 in the ranked search, 1 for
  name→detail, 10 on the `/api/legal` proxy); the fallback reads at most 12 pages of
  100 [DOC law-stack.md §(a), §(e)]. Official list responses report `totalCnt`
  (169,418 in the eflaw sample, against 20 rows returned) [DOC official-api.md §7
  S1]; whether the backend compares rows read against `totalCnt` is not recorded in
  the notes (UNVERIFIED). Manual extraction flattens tables and drops images, warned
  only per document (EXT-01, EXT-04).
- **Fixed in this PR (SEC-24a, F7).** `_extract_articles` used to match 편/장/절
  heading units by number ("제1장 총칙" carries 조문번호 1) and read only `조문내용`,
  so a "verified" snippet could be a heading or a title line. F7 skips units whose
  `조문여부` is present and not `조문`, and appends every nested 항/호/목 text. The real
  nesting was confirmed from the documented Open API sample
  (`apiguide/live/s2_law_detail.json`, 71,566 bytes, no credential in it) [DOC
  law-stack-fixes.md F7]. 조문시행일자, 부칙 and 별표 are still not read.
- **Still open (SEC-24b).** JS `findArticle` (lib/enforcement-law-grounding.js) still
  ignores `조문여부` (ESA-35b). Page-limited searches carry no coverage marker.
  Passage-level extraction flags do not reach answers.
- **Risk.** A page-limited result or title-only text is treated as complete: absence
  or an empty snippet is presented as evidence.
- **Recommendation.** Every lookup returns a `Coverage`. A page-limited search is
  `PARTIAL` unless the target was found or `totalCnt` ≤ rows read. Use
  `ParseStatus.PARTIAL` when 항/호 or annex content was not read. Partial results can
  support "found", never "not found". Carry passage-level extraction flags into
  evidence items (sources-monitoring.md recommendation 6). A truncated body fails to
  parse and must map to `UNAVAILABLE_PARSE` (INFERRED).
- **Owner:** no.

### 3.8 Cancellation

- **State.** Client disconnect is not propagated to outbound calls, and blocking
  `urllib` cannot be interrupted, so work continues after the 75 s browser abort [DOC
  ai-lifecycle.md V2 #2]. The reference project wires abort signals into fetches,
  backoff sleeps and body readers [DOC ref-ops-license.md §1.6]; that is a generic
  pattern.
- **Recommendation.** Check for disconnect between stages and schedule no new upstream
  call after it. With `to_thread`, an in-flight call finishes but nothing new starts.
  Cancellation is a typed outcome (budget/cancelled), never absence, and is never
  cached.
- **Fixed in this PR:** No. **Owner:** no.

### 3.9 Credential management (SEC-06a, SEC-06b, SEC-17)

> **Update 2026-10-21 (F12).** Redirects were not checked. In an offline probe on fc896c2, a 302 from www.law.go.kr to another host made `search_laws` send the OC to that host three times per search (the query plus two cloud-fallback pages) and read its body as no results. OC-bearing requests now refuse redirects to any host other than www.law.go.kr / law.go.kr, and refuse https→http downgrades: the result is one request, typed `law_api_http_error`, with the code logged. See [law-stack-fixes.md](research-notes/law-stack-fixes.md) F12. Separately, the production diagnostics opt-in is now token-gated: `VISABLE_DIAGNOSTICS_TOKEN` (PR #666) is set, and `/health` reports `client_diagnostics_mode: token`, observed 2026-10-20.

- **Resolution.** `LAW_API_OC > LAW_OC > OPEN_LAW_ID`, then `LAW_API_KEY`, in Python
  and JS alike; operator scripts use other names (`KOREAN_LAW_API_OC`,
  `OPEN_LAW_API_OC`, `LAW_OPEN_API_OC`). `/health` and preflight expose only booleans
  and the env var *name*. [DOC law-stack.md §(f), §(c)] VERIFIED, OBSERVED.
- **In transit.** The DRF API takes the OC as a query parameter [CODE
  law_tools.py:772-775]. On a `network` error, which includes TLS and certificate
  failures because every non-timeout `URLError` maps to `network` [CODE
  law_tools.py:226-230], the default transport resends the same URL over plaintext
  `http` to law.go.kr hosts [CODE law_tools.py:245-281]. Tests pin this
  (`test_https_network_failure_falls_back_to_http` and three siblings [TEST
  backend/tests/test_law_tools.py:119-175, ran: pass, §8]). Operator scripts try
  http first [DOC law-stack.md §(f)] VERIFIED.
- **Host trust: fixed in this PR (SEC-06a, F8).** `_trusted_base_url` accepts only
  `https://www.law.go.kr` or `https://law.go.kr` (no userinfo, port 443 or none, no
  query or fragment) [CODE law_tools.py:722-746]. Anything else falls back to the
  default host and logs `LAW_API_BASE_URL_IGNORED` once per process, without the
  configured value [CODE law_tools.py:757-769]; the preflight carries the same code.
  On HEAD a `https://korean-law-mcp.fly.dev` override received three OC-bearing URLs;
  on the fix no transport call reaches an untrusted host [DOC law-stack-fixes.md F8;
  TEST `F8HostTrustTests`, ran: pass, §8]. This is stricter than the JS client, which
  accepts any `*.law.go.kr` host and port.
- **Still open (SEC-06b).**
  - The plaintext retry stays, by decision: it came from #432 (`42f0820`) during a
    law-grounding outage, and nothing records which scheme production uses [DOC
    law-stack-fixes.md F8]. F8 confines it to `www.law.go.kr`/`law.go.kr` and logs
    `LAW_API_PLAINTEXT_RETRY_REACHED` or `…_FAILED` once per process, with no URL and no
    OC [CODE law_tools.py:270-278].
  - `urllib.request.urlopen` follows redirects with no host check on the target
    (standard-library default; no custom opener in `law_tools`, grep; not probed,
    INFERRED). The repository already has the safer pattern elsewhere:
    `mofa_public_data` builds its client with `follow_redirects=False` [CODE
    backend/services/mofa_public_data.py:174].
  - The legacy `KoreanLawClient` still sends a Bearer credential to any configured host
    (test imports only) [CODE backend/services/korean_law_client.py:59-63].
  - The owner's netdiag remediation text still recommends routing through a Korean
    proxy via `LAW_API_BASE_URL` [CODE backend/paradiso_backend.py:7508]; after F8
    that advice no longer works.
- **Upstream echo.** List and history responses embed the caller's OC in
  `법령상세링크` and `조문링크` [DOC official-api.md §2.2, §2.5]. Counted again for this
  document in the documented samples, which use the published sample OC: 20
  OC-bearing parameters in the S1 eflaw list, 12 in the S3 article history, none in
  the S2 law detail. That a real OC is echoed the same way is INFERRED. The backend
  ignores those keys or passes precedent links through `_sanitize_url`, which drops
  `oc/key/apikey/servicekey` by name and replaces known values [CODE
  law_tools.py:290-308; precedent_sources.py:343; legal_evidence.py:366-371]; the
  live B2–B4 responses carried no OC [DOC 04-official-api-capability-matrix.md §2
  item 6] OBSERVED. The F7 fixture omits the OC, and no test feeds a realistic
  OC-bearing list body.
- **Other secrets.** The live smoke holds a `PARADISO_DIAGNOSTICS_TOKEN` secret that the
  server does not have (SEC-01). `DATABASE_URL`, `SUPABASE_URL` and
  `SUPABASE_SERVICE_KEY` are read by legacy code, unused by the AI path, and reported
  as configured live [DOC ai-lifecycle.md §3.3]; any other use was not audited. The
  secret scan in `scripts/check_ai_architecture.py` covers `backend/.env.example`,
  `docs/` and `scripts/`, not `lib/` or `api/` [DOC ai-lifecycle.md V1 claim 11].
  The checklist Studio keeps the operator token in `sessionStorage` only [CODE
  assets/js/content-studio.js:9, 82-84] VERIFIED by grep.
- **Lesson from the reference project.** A real OC was once committed in a test
  results file there, and history was not rewritten [DOC ref-ops-license.md §1.3]
  (metadata only). Raw captures must never be committed; this mission records counts
  and hashes, not bodies, and the F7 fixture is a verbatim excerpt with no credential.
- **Risk.** The OC can be read on the network path after a downgrade; a future parser
  that keeps link fields would carry it into prompts, responses or logs.
- **Recommendation.** HTTPS only for every OC-bearing request: once the logs show the
  plaintext retry is unused, put it behind an explicit opt-in flag (law-stack-fixes.md
  recommends this and names the test to update), and return `UNAVAILABLE_NETWORK`
  instead. Disable redirects or allowlist every hop. Delete `KoreanLawClient` and
  `PublicDataClient`. One credential name everywhere. Drop link fields at parse time,
  and add a final masking gate (OC parameters anywhere in text, plus the known value)
  before evidence reaches a prompt, a response or a log. Remove unused secrets. Extend
  the secret scan to `lib/` and `api/`. Write an OC rotation procedure (caches keyed by
  credential fingerprint, §3.5).
- **Owner:** after deploying, check the preflight for `LAW_API_BASE_URL_IGNORED` and
  the Railway logs for `LAW_API_PLAINTEXT_RETRY_REACHED`, then decide on the opt-in
  gate; reword the netdiag text; remove the unused database secrets; decide whether to
  rotate the OC, since no log before F8 records whether a downgrade ever happened
  (INFERRED).

### 3.10 Logging and redaction

- **State.** Before F8 the law modules logged nothing; F8 adds logger
  `paradiso.law_tools`, level WARNING, at most three codes per process, each a code
  plus a fixed sentence [CODE law_tools.py:164-176; DOC law-stack-fixes.md "New
  operator logs"]; F8's tests assert that neither the dummy OC nor the request path
  appears. `legal_evidence` declares a logger and does not use it for requests.
  `/api/ask` prints one `ask_routing` JSON line with no prompt, answer, law fields or
  tokens [DOC law-stack.md §(f); ai-lifecycle.md §2.1; cost.md §0.3] VERIFIED.
  Learning observations keep features, a redacted excerpt of at most 200 characters
  and a fingerprint, expire after 90 days, and never keep raw text [DOC
  knowledge-platform.md §1.8] VERIFIED. Conversation history reaches only the
  repeat-abuse classifier [DOC ai-lifecycle.md V2 #1]. Vercel functions use
  `console.error` only. The content and retention of the safety event log
  (`WAYMAKER_SAFETY_LOG_DIR`) were not audited (UNVERIFIED), and the logging notes are
  stale on law mode (LS-R13). The checklist Studio logs actors and roles to an audit
  table (owner-reported [DOC reports/R3_RISK_AND_SECURITY_REGISTER.md R3-07 at
  fc896c2] README-ONLY).
- **Risk.** Leakage is low today, but law timeouts, errors and budget exhaustion are
  still invisible in production, so SEC-05b cannot be detected there.
- **Recommendation.** Allowlisted structured fields only: upstream family,
  `LookupStatus`, attempts, latency, bytes, coverage, cache hit, budget left. No URL,
  query text, body or OC; a query hash if correlation is needed. Audit the
  safety-event log and publish one retention statement.
- **Fixed in this PR:** Partly (the three F8 operator codes). **Owner:** retention
  period for safety events.

### 3.11 Access control (SEC-01, SEC-16, SEC-19)

- **Diagnostics.** Live mode is `open` (OBSERVED twice on 2026-10-19).
  `_diagnostics_token_ok` returns `True` when `PARADISO_DIAGNOSTICS_TOKEN` is unset,
  and either the body flag or the `X-Paradiso-Diagnostics` header then unlocks the
  payload [CODE backend/paradiso_backend.py:5573-5594] VERIFIED (re-read). When the
  token is set, the comparison is constant-time (`hmac.compare_digest`) against the
  `x-paradiso-diagnostics-token` header. The payload includes
  `grounding_context_prompt`, the knowledge plan and the attempted models; INFERRED
  from code, because no diagnostics request was sent. `ai.html?debug=1` requests it.
  [DOC ai-lifecycle.md §6, V1 claim 4]
- **Public payloads.** The default `/api/ask` projection still has about 130 fields,
  including `law_search_queries` and `parser_status_by_family`. `/health` and
  `/api/health/ai` expose model ids, cooldowns, budgets and an env-presence map; the
  coach returns `provider` and `model`; Vercel quick answer returns `model` and
  `modelCandidates`. Debug endpoints return 404 unless
  `PARADISO_ENABLE_DEBUG_ENDPOINTS` is set; preflight is open (booleans). [DOC
  ai-lifecycle.md §6] VERIFIED, OBSERVED.
- **Knowledge Studio.** Bearer tokens from `WAYMAKER_OPERATOR_TOKENS`, 503 when unset;
  tokens map to names with no roles. One operator may approve, verify and publish;
  the publish reason is enforced only in the UI; the CLI accepts a free-text
  `--operator`. The DB triggers enforce lifecycle states, not actor identity: raw SQL
  could change a published fact's citation page, excerpt, `source_version_id` and
  `verified_by` (OBSERVED on an in-memory store). Whether the Studio is live in
  production is UNVERIFIED. [DOC knowledge-platform.md §1.5, KP-3, verifier claims 4
  and 6]
- **Checklist Studio (new on main since the audit; not covered by any note; code read
  for this document).** `/api/knowledge/studio/checklists/*` uses the same
  `require_operator` token check plus a role lookup [CODE
  backend/services/knowledge/checklist_api.py:54-68]. Roles are `viewer < editor <
  reviewer < publisher`, hierarchical [CODE checklist_models.py:17-44]. Found by
  reading:
  - An operator with no row in `operator_roles` gets `editor` by default [CODE
    checklist_repository.py:157-166].
  - Migration 0002 seeds role rows for the names `admin` (publisher), `reviewer_lead`,
    `editor_staff` and `auditor` [CODE
    backend/services/knowledge/migrations/0002_checklist_operations.sql:141-145]. A
    token mapped to one of those names inherits that role.
  - `act_on_draft` checks the actor's role per action, but nothing compares the
    approver with the draft's `created_by`, so a publisher can create, submit, approve
    and publish the same change alone [CODE checklist_repository.py:428-520] VERIFIED
    by reading; not exercised.
  - The approval evidence gate requires only that `evidence_url` starts with
    `https://`, on any host [CODE checklist_repository.py:486-492].
  - The owner's register marks privilege escalation RESOLVED [DOC
    reports/R3_RISK_AND_SECURITY_REGISTER.md R3-03 at fc896c2] README-ONLY. Its tests
    pass here (6 passed, §8); they check that lower roles are refused, not that duties
    are separated.
- **Risk.** Anonymous callers can obtain prompt-ready evidence and routing internals,
  which helps both injection crafting and quota attacks. A single operator token can
  publish unreviewed facts or checklist changes to every user.
- **Recommendation.** Set `PARADISO_DIAGNOSTICS_TOKEN` (the smoke already sends it) or
  `PARADISO_CLIENT_DIAGNOSTICS=0`, and treat an unset token as "off" in production.
  Reduce `/health` to booleans; drop model ids from public responses. Both Studios:
  approver ≠ author and verifier ≠ reviewer before `PUBLISHED`; a server-side reason;
  no seeded role rows in a production migration (assign roles explicitly); an
  allowlist of official evidence hosts instead of an `https://` prefix; a token for the
  CLI; database file permissions that keep raw SQL to the migration role.
- **Fixed in this PR:** No. **Owner:** which internals may be public; staffing for
  separation of duties.

### 3.12 Dependency and supply-chain security (SEC-15, SEC-18)

- **State** [DOC sources-monitoring.md §4.1, §4.5, SUP-01, SUP-02, CI-04]:
  - Backend pins exact versions without hashes (fastapi 0.115.0, starlette 0.38.6,
    uvicorn 0.30.6, pydantic 2.9.2, httpx 0.27.2).
  - starlette 0.38.6 is in range for CVE-2024-47874 and CVE-2025-54121 (multipart DoS)
    [WEB https://api.osv.dev/v1/vulns/GHSA-f96h-pmfr-66vw and
    …/GHSA-2c2j-9gv5-cj73, accessed 2026-10-19]. Exposure is low: no
    `UploadFile`/`Form`/`request.form()`, and python-multipart is not installed. The
    upgrade needs a FastAPI bump (0.115.0 requires starlette < 0.39). VERIFIED.
  - `olefile` is imported by four scripts and declared nowhere.
  - The `hikorea-manual-sync` job holds `contents: write` and runs unpinned `pip
    install olefile pyhwp`; the converter benchmark installs `@latest` tools; actions
    are tag-pinned, not SHA-pinned; a dispatch input is interpolated into a shell line
    (needs write access); `*_CMD` repository variables are executed by
    `convert_manual_hwp.py`.
  - No Dependabot config (`.github/` still holds only `workflows/`, checked at
    `fc896c2`), no lockfile (caret ranges, ad hoc `--package-lock=false`), production
    Python unpinned, Node versions mixed.
  - No `defusedxml` anywhere: XML goes through the standard library (§5).
  - Since the audit, main added `scripts/requirements-manual-reader.txt` with exact pins
    (no hashes), installed in `repo-validation`, and a read-only QA workflow
    (`immigration-checklists-mobile-qa.yml`: `contents: read`, tag-pinned actions,
    exact `@playwright/test@1.61.0`) [CODE at fc896c2] VERIFIED.
  - The mission's experiment package is standard-library only (pytest in tests only),
    by mission rule.
- **Recommendation.** SHA-pin actions; pin and hash tool installs; pass dispatch inputs
  through `env`; add Dependabot or an OSV scan; commit a lockfile and use `npm ci`;
  pin the Python runtime (which also pins expat, §5); bump FastAPI and Starlette
  together; keep the experiment package stdlib-only.
- **Fixed in this PR:** No. **Owner:** timing of the FastAPI bump; whether the HWP
  converter tools may run in CI at all.

### 3.13 Input bounds

- **State.** `/api/ask`: prompt ≤ 4,000 chars (400 `prompt_too_long`), history 24 ×
  2,000, `context` ≤ 8,000 and then never read, `visa_data` ≤ 300k; the browser caps
  questions at 500 chars; client catalog blocks are trimmed to 240 or 180 chars per
  field. Law summaries enter the prompt at ≤ 700 chars, case chunks at ≤ 280 × 4 × 3.
  [DOC ai-lifecycle.md §2.1, §5] VERIFIED. The Vercel quick-answer server re-validates
  shape and output, but checks facts only against what the client sent [DOC
  ai-lifecycle.md V2 #3]. Upstream bodies are read with no size limit [CODE
  law_tools.py:218-219]. Fan-out is capped by count (7 default, 8 hard per `/api/ask`)
  [CODE law_tools.py:156-159] but not by bytes [DOC ref-ops-license.md §1.5
  verifier]. ReDoS exposure of the normalizer's regexes over user text [CODE
  law_query_normalizer.py:131-148] was not assessed (UNVERIFIED).
- **Experiment side (this PR, not production).** The source-bundle loader accepts only a
  plain file name as bundle id, checks the provenance enum, and refuses synthetic
  records in a verified bundle and the reverse [CODE
  experiments/waymaker-ai/waymaker_ai/legal/adapters.py:122-144, 165-174]. It reads
  the whole file with `json.load` and no byte cap: harmless for committed fixtures,
  required before any bundle comes from outside the repository (INFERRED).
- **Recommendation.** Read upstream bodies through a byte limit sized from observed
  payloads (the documented law-detail sample is 71,566 bytes [DOC official-api.md
  §5]); over the limit is `UNAVAILABLE_PARSE`. Cap query length before any regex. Cap
  JSON/XML depth (§5). Bundle loaders keep JSON only, under a size cap,
  schema-validated, with the provenance enum checked: `synthetic_fixture` records
  never reach a user, and synthetic text never shares a record with a real law id.
- **Fixed in this PR:** No (for production). **Owner:** no.

### 3.14 Model fallback (SEC-13)

- **State.** Groq and Ollama answers skip the shape gate, citation guard, Answer Guard
  and post-generation review; the Groq family fallback also skips the confidence gate
  and metadata scrub. The Groq-primary path applies only the confidence gate
  (unreachable with today's config). The stream path skips most guards (no shipping
  caller streams). The coach calls Groq whenever `GROQ_API_KEY` is set and OpenRouter
  fails, with no opt-in, and Groq is configured live. Retryable failures otherwise end
  in the deterministic fallback with a manual locator. [DOC ai-lifecycle.md §2.1,
  §2.2, AL-R6, V2 #5; training-distill.md verifier claim 1] VERIFIED.
- **Interaction with F1/F2.** After F1, title-only lookups keep
  `law_grounding_verified`, and the prompt switches to the VERIFIED citation directive.
  On the buffered path F2 still gates article numbers. The streamed path has no
  post-hoc guard, so there the directive is the only control [DOC law-stack-fixes.md,
  "Behaviour the owner should know", item 1] INFERRED for production.
- **Risk.** A degraded-mode answer reaches users without the checks the primary path
  applies.
- **Recommendation.** One ordered guard pipeline for every exit: a fallback answer
  passes the same deterministic gates or is replaced by the deterministic fallback.
  Keep streaming off until it has parity. Remove dead ids. Report model health as a
  metric.
- **Fixed in this PR:** No. **Owner:** is Groq allowed for the coach?

### 3.15 Cost monitoring (SEC-14, SEC-20)

- **State.** No code reads provider `usage` fields, and `ask_routing` has no token
  counts [DOC cost.md §0.3] VERIFIED. The live enforcement chain uses paid ids (about
  $0.00015–$0.0012 per call, INFERRED) and needs a positive balance, else 402 [DOC
  cost.md §0.1]. Each push sends 3 `/api/ask` POSTs and 1 enforcement POST to
  production [DOC law-stack.md verifier omission 5]. The Vercel quick answer is an open
  quota sink (SEC-12). law.go.kr calls are counted nowhere. Volumes and budgets are
  in [14](14-hardware-and-cost-model.md).
- **Recommendation.** Log `usage` tokens and the model id per call (about 0.5–1
  engineering day, [DOC cost.md §10 table] INFERRED). Daily counters per upstream (free
  bucket, paid spend, law.go.kr calls by target). A spend alert on the OpenRouter
  account. Tag synthetic traffic.
- **Fixed in this PR:** No. **Owner:** is the paid enforcement chain intended (AL-R7);
  budget ceiling.

## 4. Threat model

| # | Threat | Current state (evidence) | Risk | Recommendation | Fixed in this PR | Owner decision |
|---|---|---|---|---|---|---|
| T1 | API-key leakage | OC in query strings; plaintext resend on connection failure (now law.go.kr only, logged); upstream echoes the OC in links; provider keys server-side only, and the architecture guard finds no frontend-to-provider calls [DOC ai-lifecycle.md VT2]. Details §3.9 | medium | §3.9 | Partly: F8 (host allowlist, retry logging) | §3.9 |
| T2 | Prompt injection from sources | The system prompt never says retrieved text is data. Everything goes into one user message under bracket headings, with no unique fences or length tags. Official text is low-risk, but OCR noise and quoted instructions inside decisions pass unlabelled. Only enforcement prompts call case text untrusted. Quick Answer (JSON in, schema out, deterministic validator) is the strongest posture [DOC ai-lifecycle.md §5]. WLIE specifies flagging instruction-like text and quoting it as data, with no effect on verification ([07 §2](07-evidence-verification-design.md) invariant 5); the experiment package implements that flag as a documented heuristic [CODE experiments/waymaker-ai/waymaker_ai/legal/injection.py:1-27], not wired to production | medium (new) | Data-not-instructions framing in the system prompt; per-request unique fences; evidence as typed JSON fields; flag instruction-like evidence text; output validators that do not depend on the prompt | No (production) | No |
| T3 | Malicious structured data | Client `visa_data` and variant notes are presented as "extracted from the cited official manual pages" with only per-field trims; `visa_data.code` overrides free-text detection (AL-R3). Quick Answer facts come from the client (AL V2 #3). Upstream JSON/XML (§5). Raw SQL on the knowledge store (§3.11). The manual reader inserts committed chapter HTML with `innerHTML` [CODE assets/js/manual-reader.js:266]; the chapters are generated from official manual Markdown by `scripts/build_manual_reader.py`, which has no explicit sanitizer; a grep finds no `<script` in `data/manual-reader/chapters` (not audited further) | high | Resolve `visa_data` server-side by code and ignore client record content; schema-validate every bundle and payload; enforce the provenance enum; sanitize generated HTML at build time with a tag allowlist | No | No |
| T4 | XML parser attacks | Stdlib ElementTree; no DTD rejection; expat refuses entity bombs and external entities in the local build; production expat unpinned (§5) | medium (new) | §5 | No | No |
| T5 | Unbounded bodies and parser cost | `resp.read()` with no limit [CODE law_tools.py:219]; the official-error walk costs superlinear time in depth (a 5.8 KiB body: 0.27 s; 255 KiB: 1.39 s), and an XML body near the recursion limit raises out of `search_laws` (§5) | medium (new) | Byte cap, depth cap, parse off the event loop, guard the parse with the same typed error as the transport | No | No |
| T6 | Recursive requests | The notes record no path where the backend calls itself; the navigator follow-up is a single `/api/ask` hop [DOC ai-lifecycle.md §2.5]. Not a dedicated audit (UNVERIFIED) | low | If an MCP or Hestia surface is exposed: no tool may call the surface itself; a depth counter per request; the advertised tool set equals the callable set [DOC ref-ops-license.md §1.1] | No | No |
| T7 | Amplification | Offline fake transport: 11–12 upstream calls per `/api/ask`, 22 for a pro research request (not production measurements); 24 attempts per question on upstream timeouts; up to 6 sends per connection failure; about 13 upstream calls behind one unauthenticated law-proxy query [DOC law-stack.md Q14, verifier claims 5–6, omission 3, LS-R8]. F6 makes repeated failed or empty `legal_evidence` questions cost a request each time. A 6 KiB hostile body costs about 0.3 s of CPU (§5) | medium | One per-request upstream budget (count and bytes); one precedent client (LS-R10); de-duplicate identical in-flight queries; rate-limit the proxies | No | §3.3 |
| T8 | Sensitive data in logs | Low today (§3.10); F8's three codes carry no URL or OC; the safety-event log was not audited | low | §3.10 | No | §3.10 |
| T9 | Unauthorized model-provider transmission | `/api/ask` sends real user questions to: the NVIDIA API Trial channel (trial purposes only, no production use without a Subscription, no personal information, NVIDIA may use content to improve its models: §1.2, §1.4, §4.3, §3.3(iv)); the Thinking Machines free research tier (no personal data, perpetual licence to train on prompts and outputs); Google AI Studio unpaid terms (no personal information, human review) [DOC training-distill.md §0.3, §3.1 rows 2, 4, 6] VERIFIED (texts). Whether the trial and unpaid terms bind OpenRouter-mediated calls is INFERRED / UNVERIFIED [DOC training-distill.md §0.3 verifier; cost.md §0.9]. OpenRouter documents an account setting to avoid providers that train on prompts, with separate settings for free and paid models; its effect on free-model availability is UNVERIFIED [DOC cost.md §1]. The client sends a `consent` field whose effect was not audited (UNVERIFIED). The owner branch drops `inkling:free` from the Basic chain. The unwired NIM scaffold already blocks personal data and allows only research and internal-QA modes [DOC training-distill.md §1]. In this PR, `experiments/waymaker-ai/configs/teacher_policy.json` defaults to `deny` and the dataset PII screen reports a kind and position, never the value [CODE experiments/waymaker-ai/waymaker_ai/dataset/pii.py:1-30]; both govern distillation and datasets only, not the production path | critical (TD) | Until counsel rules, treat every `:free` and trial channel as unable to receive user questions; move the answer path to channels whose terms allow production use and personal data (reviewed paid hosts or self-hosted). Turn on the OpenRouter training opt-out as an interim step. A deterministic PII scrub reduces exposure but does not change the production-use clause (INFERRED) | No | **Yes**, REQUIRES LEGAL REVIEW |
| T10 | URL manipulation | `LAW_API_BASE_URL` now restricted to https `www.law.go.kr`/`law.go.kr` (F8); redirects still followed; user values are URL-encoded into a fixed host and path in `law_tools` [CODE law_tools.py:772-775] (VERIFIED for `law_tools` only); `/api/ask` `source_url` is the sanitized DRF API URL, useless to a reader without an OC, and precedent list links built that way return an auth-failure page to users [DOC 04-official-api-capability-matrix.md §2 item 5] OBSERVED; the human link `https://www.law.go.kr/법령/<name>` is unversioned [DOC law-stack.md §(a)] | medium | Disable or allowlist redirects (§3.9); build human links from identity and version (`stable_id`/MST + `efYd`, [06](06-temporal-law-and-source-identity.md)), never from model output | Partly: F8 | No |
| T11 | Privilege boundaries | GitHub: §2, §3.12. Runtime: diagnostics open, Knowledge Studio without roles, checklist Studio with roles but no separation of duties, DB triggers state-only, Vercel `lib/`/`api/` outside the architecture guard [DOC ai-lifecycle.md V1 claim 11]. Auto draft PRs opened with `GITHUB_TOKEN` get no CI run (INFERRED). Experiment code makes no network requests; its evaluation driver refuses sockets before importing the backend [CODE experiments/waymaker-ai/waymaker_ai/evaluation/drivers/existing_law_driver.py:29-48] | medium | §3.11, §3.12; extend the architecture guard to `lib/` and `api/` | No | §3.11 |
| T12 | No branch protection on `main` | No protection, rulesets or org rules; merge deploys within minutes; checks are advisory; a failing invariant (`check_260617_subcode_inventory_coverage.py`) already sits on main behind a "passes: true" report [DOC sources-monitoring.md CI-01, CI-02] OBSERVED. This PR's own changes would deploy the same way once merged | high | Protect `main`; require repo-validation and manual-code-coverage; require review for protected data paths | No | **Yes** |
| T13 | Supply chain | §3.12 | medium | §3.12 | No | §3.12 |

## 5. XML and JSON parsing in `law_tools` (SEC-10)

> **Update 2026-10-21 (F11).** `RecursionError` from deeply nested XML/JSON no longer escapes `_parse_payload`; it becomes `law_api_parse_error`. The official-error walk is bounded by depth and size. Official envelopes are detected near the root (depth ≤ 3) only, so error-like keys inside data rows are treated as data. Still open: a byte cap on the response read, DOCTYPE/ENTITY rejection, and moving parsing off the event loop.

**Code (unchanged by F1–F8).** `import xml.etree.ElementTree as ET` [CODE
backend/services/law_tools.py:35]. `_parse_payload` [CODE law_tools.py:675-700] sniffs
the first 200 characters (`_shape_hint`, 543-557): `<!doctype html`, `<html` or
`<body` → HTML (typed `law_api_bad_response`); `<?xml` or any `<` → XML. XML goes
through `ET.fromstring` and the recursive `_xml_to_obj` (560-577) inside a `try`; any
exception becomes `law_api_parse_error` / `xml_parse_error`. JSON goes through
`json.loads`. Both then run `_contains_official_error` **outside** the `try`; it walks
every dict and calls `str(value)` on each value at each level (589-637).
`_xml_root_tag` (640-645) parses again. There is no `defusedxml`, no DOCTYPE
rejection, no depth limit and no size limit before parsing; the body comes from an
unbounded `resp.read()` (218-219). `_execute` (799-883) calls the parser without a guard
(839), while `search_laws` documents "Never raises" (894-906).

**Probe** (written for this document, 2026-10-20; offline: `socket.connect`,
`connect_ex` and `create_connection` replaced in-process with a function that raises,
0 connection attempts recorded; credentials unset, except a dummy value
`probe-dummy-oc` set in-process to reach the parse path through a fake transport;
`.venv-check` Python 3.11.15, `pyexpat.EXPAT_VERSION` `expat_2.7.1`, recursion limit
1000; this worktree with F1–F8; scripts in the session scratchpad, deleted after the
run):

| Input | Result | Time |
|---|---|---|
| Entity bomb (10 nested entities × 10 references) | `xml_parse_error`: expat refused it | 300 ms |
| External general entity `SYSTEM "file:///etc/hosts"` | `xml_parse_error`: entity not resolved | < 1 ms |
| External DTD `SYSTEM "http://127.0.0.1:9/x.dtd"` | `parsed_xml`; no connection attempted | < 1 ms |
| Small internal entity | `parsed_xml`, entity expanded | < 1 ms |
| XML nested 5,000 deep | `xml_parse_error` (recursion caught inside the `try`) | 5 ms |
| JSON nested 5,000 deep | `json_parse_error` | < 1 ms |
| JSON chain `{"a":…}` nested 250 / 500 / 750 / 990 deep (1.5 / 2.9 / 4.4 / 5.8 KiB) | `parsed_json` | 10 / 49 / 146 / 272 ms (best of 3; single runs under load reached 1.4 s) |
| JSON object nested 100 / 300 / 600 deep, ~64 KiB | `parsed_json` | 27 / 99 / 474 ms |
| JSON object nested 600 deep, 255 KiB | `parsed_json` | **1,394 ms** |
| Realistic wide list, 5,000 rows, 467 KiB | `parsed_json` | 25 ms |
| XML within 3 levels of the recursion limit: 993–995 deep from a shallow caller, 933–935 at +60 frames, 873–875 at +120 | `RecursionError` **escapes** `_parse_payload` (`_xml_to_obj` succeeds, the walk overflows) | — |
| JSON at the same margin | no escape (`json.loads` fails first and is caught) | — |
| `search_laws` with a fake transport returning XML nested 990–993 deep | `RecursionError` escapes `search_laws` | — |
| `build_law_grounding_context`, question citing 출입국관리법 제18조, same transport: XML 989–992 deep | the exception path: `law_grounding_used False`, no `error_type`, citation `error`, `SOURCE_UNAVAILABLE` | — |
| same, XML 860–988 deep (well-formed, no expected rows) | `law_api_no_results` → `failed_verification` + `CITED_LAW_NOT_FOUND` | — |
| same, XML 993–1000 deep | `law_api_parse_error` → citation `error` | — |
| Missing-OC JSON envelope (`result` + `msg`, shape from OA V-E) | `law_api_no_results` | — |
| Empty body / auth-failure HTML page | `law_api_no_results` (D6) / `law_api_bad_response` | — |

**Reading.**

- External entities and external DTDs are not resolved by ElementTree in this build
  (OBSERVED). Entity bombs are stopped by expat's amplification limit (OBSERVED for
  expat 2.7.1). That this protection depends on the expat version (added in the 2.4
  line) is background knowledge not re-read in this mission (INFERRED). The production
  Python, and so its expat, is unpinned (§2), so the protection on the deployed runtime
  is UNVERIFIED.
- The official-error walk grows faster than quadratically with depth (OBSERVED:
  doubling the depth from 250 to 500 multiplied the time by about 5) and runs
  synchronously in async handlers, so one such body stalls the worker (SEC-04).
  Realistically shaped bodies are cheap. On the `legal_evidence` path F6 pays the cost
  twice (§3.5).
- The `RecursionError` window is narrow and depends on the caller's stack depth, but it
  breaks the "Never raises" contract and lands in the exception path that F4 left open
  (SEC-05b). A well-formed body of unexpected shape is read as authoritative absence.
- Only a tampered or malformed upstream response could carry such a body: through the
  plaintext retry (SEC-06b), a compromised upstream, or a format change. F8 removed the
  misconfigured-base-URL route. Likelihood low, impact medium (INFERRED).
- The documented official samples (S1 JSON, S2 JSON, S3 XML) contain no `<!DOCTYPE` or
  `<!ENTITY` (re-checked for this document), so legitimate traffic does not appear to
  need DTD support (INFERRED from the samples read).

**Recommendation** (standard library only, deterministic): reject any body that
contains `<!DOCTYPE` or `<!ENTITY` before parsing, or use an expat parser whose doctype
and entity-declaration handlers raise (the `defusedxml` approach without the
dependency); cap body bytes and nesting depth before parsing, and walk iteratively; look
for official error envelopes only at known keys near the root, including `result`
(LS-R15 already asks for schema-based matching); require positive evidence of an empty
result before reporting "no results" (§3.6 rule 5); parse off the event loop; catch
everything the parser can raise inside `_execute` and type it; pin the runtime. Every
rejection maps to `LookupStatus.UNAVAILABLE_PARSE`, never to absence
([07 §2](07-evidence-verification-design.md) invariant 1).
**Fixed in this PR:** No. **Owner:** no.

## 6. Government-use boundaries for Hestia (SEC-23)

Hestia is not defined anywhere in the repository (`git grep` finds nothing [DOC
training-distill.md verifier, not filled #4]). The two notes define it differently: a
professional assistant on a shared base with LoRA adapters [DOC models.md header], or a
self-hosted verifier so that personal data never reaches a third party [DOC
training-distill.md §2.0] (both INFERRED). [08](08-foundation-model-research.md) records
the disagreement; [10 §1](10-athena-and-hestia-strategy.md) settles it for this document
set (Hestia is the professional assistant; claim verification stays the deterministic
WLIE gate of [07](07-evidence-verification-design.md)) and
[10 §6](10-athena-and-hestia-strategy.md) puts government use out of scope today. A later
MCP surface for professional tools is worthwhile only after WLIE is in the backend and
its gates pass ([05 §6](05-legal-intelligence-architecture.md)). The boundaries below are
the B-numbers that [10 §6.2](10-athena-and-hestia-strategy.md) refers to, and they hold
under either reading. They are conditions on any future government or institutional use,
INFERRED unless a source is given, and for the owner and counsel to accept or reject.

| # | Boundary | Basis | Consequence for Hestia |
|---|---|---|---|
| B1 | Not an official determination | law.go.kr: its information has no legal effect and is reference material; the 관보 is authoritative [DOC official-api.md §6] VERIFIED. The procedure packet already models `final_agency_discretion` [DOC ai-lifecycle.md §2.5] | Outputs are evidence packets with `candidate_only` version determinations ([06 §3](06-temporal-law-and-source-identity.md)), never approve/deny decisions. `human_review_required` stays visible. Disclaimers and review warnings are never weakened |
| B2 | Attribution and integrity | open.law.go.kr warns of criminal liability under 「저작권법」 제137조·제138조 for using its law information without stating the source, or naming another agency as the source, and for forging or altering it [DOC official-api.md §6] VERIFIED, as stated on that page | Every statute excerpt carries "출처: 법제처 국가법령정보센터 (law.go.kr)", the URL, `retrieved_at` and `content_sha256`. Text is quoted verbatim and never presented as an official rewording |
| B3 | Personal data stays on infrastructure the deploying body controls | Free and trial channels bar personal data (T9) [DOC training-distill.md §3.1] | Self-hosted only; no `:free`, trial or unreviewed paid channel. A lawful basis under PIPA REQUIRES LEGAL REVIEW [DOC training-distill.md §3.3] |
| B4 | One credential per deployer | OC approvals are per application and bound to targets, IPs and domain (2015 Q&A; current enforcement UNVERIFIED); production use requires registering a 활용사례 [DOC official-api.md §5]. The reference project states that each user obtains an OC usable only by its holder; the Open API's own terms on shared keys were not verified [DOC ref-ops-license.md §2.7, §5] | An institutional deployment files its own OC application. Waymaker's OC is never proxied to third parties (SEC-07) |
| B5 | No impersonation | Answers manipulated through client-supplied `visa_data` would carry Visable branding in screenshots [DOC ai-lifecycle.md §5 item 3] | Hestia never presents itself as a 법무부, HiKorea or 법제처 service, and never uses their marks. INFERRED |
| B6 | Scope separation | Visa-issuance vs stay procedures and parent vs subcode are enforced in the Knowledge Platform (`PROCEDURE_SCOPE_MISMATCH`) and in WLIE L6 ([05 §5](05-legal-intelligence-architecture.md)) | Adapters per procedure scope are selected deterministically and never merged [DOC training-distill.md §2.1, adapter row] |
| B7 | Commercial-use status per API | Use may be restricted for commercial use of APIs not licensed for it; which APIs is not stated (UNVERIFIED) [DOC official-api.md §5] | Before any paid professional offering, confirm each target family's status with 법제처 (contacts in official-api.md §5) |
| B8 | Public-sector security and procurement | Not researched in this mission (UNVERIFIED) | No compliance claim may be made. The owner decides whether to pursue government use at all |
| B9 | Reproducibility | Mirrors the distillation provenance rule [DOC training-distill.md §3.2] | Every answer is reproducible from the evidence-pack hash, model revision SHA, adapter id and prompt hash |
| B10 | MCP surface hygiene (if built) | Generic lessons noted from the reference project: credentials passed as tool arguments end up in transcripts; "advertised" and "callable" tools diverged; unsafe network binds should fail at boot [DOC ref-ops-license.md §1.1, §1.2] (described, not copied) | Credentials only server-side; the advertised tool set equals the callable set; refuse to start on a non-loopback bind without authentication |
| B11 | Honest client, official channels only | The reference project spoofs a browser User-Agent, injects a law.go.kr Referer and decodes an anti-bot challenge; Waymaker uses an honest User-Agent [DOC ref-ops-license.md §1.13] VERIFIED (described, not copied) | No anti-bot circumvention, no browser impersonation, no scraping where an official API exists. A public body cannot defend a tool that evades the provider's own controls (INFERRED) |

**Fixed in this PR:** No. **Owner:** whether government use is in scope, and which of
B1–B11 become requirements.

## 7. Owner decisions, in priority order

1. **Diagnostics** (SEC-01): set `PARADISO_DIAGNOSTICS_TOKEN` on Railway or set
   `PARADISO_CLIENT_DIAGNOSTICS=0`.
2. **Model channels** (SEC-02, T9): with counsel, decide which channels may receive real
   user questions. REQUIRES LEGAL REVIEW. Interim: the OpenRouter training opt-out.
3. **Branch protection** (SEC-03): protect `main` and choose the required checks.
4. **After this PR deploys** (SEC-06a, SEC-06b): check the preflight for
   `LAW_API_BASE_URL_IGNORED`; search the Railway logs for
   `LAW_API_PLAINTEXT_RETRY_REACHED` over a representative period; if it never
   appears, gate the http retry behind an explicit opt-in flag (and update
   `test_law_tools.py:119-175`); reword the netdiag proxy advice
   (`paradiso_backend.py:7508`).
5. **Public law proxies and the Vercel law-probe** (SEC-07): public, limited or removed.
6. **Vercel AI functions** (SEC-12): retire them or bring them under the model policy,
   the architecture guard and a rate limit.
7. **Groq for the coach** (SEC-13).
8. **Spend** (SEC-14): is the paid enforcement chain intended; a budget ceiling; whether
   to buy credits.
9. **Unused database secrets** (SEC-17): remove them if nothing uses them.
10. **Studios** (SEC-16, SEC-21): separation of duties in both the Knowledge Studio and
    the checklist Studio; explicit role assignment instead of seeded names; whether the
    Studios are live; whether a volume is mounted.
11. **Hestia** (SEC-23): whether government use is in scope, and which boundaries in §6
    apply.
12. **Dependencies** (SEC-15): timing of the FastAPI/Starlette bump; converter tools in
    CI.

## 8. Checks run for this document (2026-10-20)

All offline, with `LAW_API_OC LAW_OC OPEN_LAW_ID LAW_API_KEY LAW_GROUNDING_MODE
LAW_API_BASE_URL` and model keys unset, `PYTHONDONTWRITEBYTECODE=1`, Python
`<python3.11-venv>/bin/python` (3.11.15), in this
worktree.

| Check | Result |
|---|---|
| `python -m pytest -q -p no:randomly -p no:cacheprovider backend/tests/test_law_stack_genesis_regressions.py backend/tests/test_law_tools.py backend/tests/test_legal_evidence.py` | exit 0, `159 passed, 5 warnings, 19 subtests passed` (33 + 91 + 35: F1–F8 regressions, the scheme-fallback tests, the `legal_evidence` suite) |
| `python -m pytest -q -p no:randomly -p no:cacheprovider backend/tests/test_checklist_operations.py` | exit 0, `6 passed, 1 warning` |
| Parser probe, five scripts (§5) | as tabulated; 0 socket connection attempts in every script |
| `grep` of the documented samples `apiguide/live/s1_eflaw_list.json`, `s2_law_detail.json`, `s3_johst.xml` | `OC=` parameters 20 / 0 / 12; `<!DOCTYPE` and `<!ENTITY` 0 in all three; both saved header files show the `Cache-Control` line quoted in §3.5 |
| `git diff --stat 0713370 fc896c2 -- <deploy and law files listed at the top>` | empty |
| Code reads | diagnostics gate (`paradiso_backend.py:5548-5594`), rate-limit key (`rate_limit.py:65-87`), `/api/legal` routes, F8 code (`law_tools.py:164-176, 245-281, 722-775`), parser (`law_tools.py:543-700`), `legal_evidence.py:762-855`, checklist Studio (`checklist_api.py`, `checklist_models.py`, `checklist_repository.py`, migration 0002), experiment loader and flags |

The full backend suite and the golden evaluation were not re-run for this document; the
fix agent's results are in law-stack-fixes.md ("Commands run and results": 83 modules
PASS, 50 golden questions PASS).

## 9. Not verified by this document

- Production `/api/ask` behaviour on a law question (AI POSTs were out of bounds for
  every agent) [DOC law-stack.md, open questions], and how F1–F8 behave once deployed.
- Railway values of `WEB_CONCURRENCY`, `LAW_API_BASE_URL` and
  `OPENROUTER_TIMEOUT_SECONDS`; the proxy's `X-Forwarded-For` handling; the deployed
  Python and expat versions; whether a volume is mounted; whether Railway now serves
  `fc896c2`.
- Vercel credentials, whether `api/enforcement/law-probe.js` is deployed, and Vercel's
  deploy trigger.
- The live diagnostics payload; the safety-event log; `privacy.py` redaction patterns;
  the `consent` field's effect; the `CORS_ALLOW_ORIGINS` value.
- Open API terms on key sharing and AI use, and which APIs are non-commercial; whether
  invalid-OC and unregistered-IP failures share the missing-OC envelope.
- Whether the NVIDIA trial and Google unpaid terms bind OpenRouter-mediated calls, and
  what the OpenRouter training opt-out leaves available on the free tier.
- ReDoS exposure of the normalizer's regexes; redirect behaviour of the law transport
  (inferred from the standard library, not probed).
- The checklist Studio beyond the reads in §3.11 (no note covers it); whether
  `build_manual_reader.py` output is safe for `innerHTML` beyond the `<script` grep.

## 10. Sources

- [research-notes/law-stack.md](research-notes/law-stack.md): §0, §(a), §(b) Q14, Q15,
  §(c), §(d), §(e), §(f), §(h) R3–R10, R13, R15, and the verification pass (claims 5, 6,
  10, 12, 13; omissions 3–5).
- [research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md): F3–F8,
  "Behaviour the owner should know before deploying", "Commands run and results", "Not
  done here".
- [research-notes/ai-lifecycle.md](research-notes/ai-lifecycle.md): §1, §2.1–2.5, §3.3,
  §3.4, §5, §6, §10 R3, R4, R6–R10, R14, R17, and the verification pass (VL1, VT2; V1
  claims 4, 11, 14; V2 #1–#3, #5).
- [research-notes/sources-monitoring.md](research-notes/sources-monitoring.md): §3.3,
  §4.1, §4.4, §4.5, §5 (CI-01, CI-02, CI-04, CI-05, SUP-01, SUP-02, EXT-01, EXT-04,
  SRC-02) and the verification pass (claims 10, 15).
- [research-notes/knowledge-platform.md](research-notes/knowledge-platform.md): §1.3,
  §1.5, §1.8, §7 (KP-3, KP-4) and the verification pass (claims 4, 6, 15).
- [research-notes/ref-ops-license.md](research-notes/ref-ops-license.md): §1.1–1.3,
  §1.5–1.8, §1.13, §2.7, §4.1, §5 and the verification pass (claims 10, 15). The
  reference project is described only; no code from it was consulted for any
  recommendation here.
- [research-notes/training-distill.md](research-notes/training-distill.md): §0.1, §0.3,
  §1, §2.0, §2.1, §3.1–3.3 and the verification pass (claims 1, 3; not filled #4).
- [research-notes/official-api.md](research-notes/official-api.md): §2.2, §2.4, §2.5,
  §5, §6, §7, §8, and the verification pass (V-E error envelopes).
- [research-notes/cost.md](research-notes/cost.md): §0.1–0.3, §0.9, §1, §2.
- [research-notes/models.md](research-notes/models.md): header (Hestia role).
- Owner material on main, cited as README-ONLY: `reports/R3_RISK_AND_SECURITY_REGISTER.md`
  at `fc896c2` (read with `git show`; `reports/` is outside this sparse checkout).
- Normative specs: [06](06-temporal-law-and-source-identity.md),
  [07](07-evidence-verification-design.md); contract vocabulary in
  `experiments/waymaker-ai/waymaker_ai/contracts.py` (`LookupStatus`, `Coverage`,
  `ParseStatus`, `ProvenanceStatus`).
- Related documents: [00](00-executive-summary.md), [01](01-existing-system-audit.md)
  (ESA register), [04](04-official-api-capability-matrix.md),
  [05](05-legal-intelligence-architecture.md), [08](08-foundation-model-research.md),
  [09](09-training-and-distillation.md), [10](10-athena-and-hestia-strategy.md),
  [14](14-hardware-and-cost-model.md), [16](16-validation-results.md),
  [17](17-mission-002-plan.md).
