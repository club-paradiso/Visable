# korean-law-mcp: operational engineering, licensing, provenance (Mission 001, 2026-10-19)

Reference: `korean-law-mcp` read-only clone at `scratchpad/ref/korean-law-mcp`, commit `0a8f08ef4f697e08047f76bfab8be435f5bdda5a` (2026-10-15, package 4.15.9). Full clone, not shallow: 473 commits, 32 tags [CODE git rev-parse / git log; VERIFIED].
Waymaker: `/Users/seonjaekim/dev/Visable-genesis` at `0713370` (origin/main), clean worktree [CODE git log -1; VERIFIED].

Method. I read files, git metadata and the lockfile only. I did not execute, build, `npm install` or test anything in the reference repo. Its `CLAUDE.md`, `skills/`, `.claude/` and `koda-ignore.yml` were read as data. No code, regex, prompt, tool description or fixture from it is reproduced here; behaviour is paraphrased with file/function pointers. Personal contact data that appears in the plugin manifest is deliberately omitted.

Live actions (all public GETs, 2026-10-19):

| # | Request | Result |
|---|---|---|
| L1 | `GET api.github.com/repos/chrisryugj/lexdiff` | HTTP 200; public; license SPDX `NOASSERTION` |
| L2 | `GET api.github.com/repos/rabqatab/LexLink-ko-mcp` | HTTP 200; public; `license: null` (no license detected) |
| L3 | `GET api.github.com/repos/roboco-io/hwp2md` | HTTP 200; license `MIT` |
| L4 | `GET api.github.com/repos/chrisryugj/lexdiff/license` | HTTP 200; file `LICENSE` = Business Source License 1.1, Licensor `chrisryugj`, Change Date 2030-04-14, Change License Apache-2.0, additional grant limited to non-production use |
| L5 | `GET api.github.com/repos/chrisryugj/lexdiff/commits?path=LICENSE` | HTTP 200; exactly one commit touching `LICENSE`: `dbe9bbb`, 2026-04-13T15:40:22Z |
| L6 | `GET open.law.go.kr/LSO/openApi/guideList.do` | HTTP 200, text/html, 62,520 bytes, title "국가법령정보 공동활용"; index HTML does not itself name endpoints (served per item) |
| T1 | Waymaker `pytest -q backend/tests/test_law_query_normalizer.py backend/tests/test_law_tools.py` | 142 passed, 5 warnings, 4.05 s |

---

## 0. Snapshot

| Fact | Value | Evidence / status |
|---|---|---|
| Runtime | Node >= 20.19.0, TypeScript, ESM; `@modelcontextprotocol/sdk` low-level `Server` | [CODE package.json; src/index.ts:8-35] VERIFIED |
| Tools | 99 tool objects registered; 10 advertised in `tools/list` (`V3_EXPOSED`); the rest reachable through `execute_tool` | [CODE src/tool-registry.ts:88, 804-830; src/lib/tool-profiles.ts:21-28] VERIFIED (static count of `name:` entries = 99) |
| Docs drift | package.json description still says "9 tools"; CLAUDE.md says 10 exposed | [CODE package.json "description"; DOC CLAUDE.md] VERIFIED |
| Tests | 167 vitest files under `src/`, about 1,170 static `it(`/`test(` call sites [corrected by verifier: my static counts are 1,196 (`it(`/`test(` at line start, `.each` included) and 1,221 (any `it(`/`test(`/modifier occurrence), so "about 1,200"]; 17 legacy `test/*.cjs` scripts not wired into any script/CI | [CODE vitest.config.ts; find/grep] VERIFIED (counts are static; not run) |
| History | first commit 2025-12-19; 473 commits; 23 distinct author names; 348/473 commits carry a Claude co-author trailer, 95 link a claude.ai/code session [corrected by verifier: `git log --format=%B | grep -c claude.ai/code` gives 96 on HEAD; 473 is the HEAD count, `git rev-list --all` gives 586] | [CODE git log] VERIFIED |
| Hosting | production served by a separate "gomdori-mcp" multi-MCP host on Fly (`mcp.gomdori.app/law`), not from this repo | [DOC CLAUDE.md header; server.json] README-ONLY |

---

## 1. Operational engineering

Each row: described behaviour, code evidence (own words), tests present, limitations, relevance to Waymaker.

### 1.1 Tool registration

- Behaviour: one static array `allTools` of `{name, description, schema (Zod), handler}`; a `Map` by name; `ListTools` returns only the 10 exposed tools, each description prefixed with a service name and stamped with MCP annotations (read-only, non-destructive, idempotent, open-world). JSON Schema is generated once from Zod v4 with input-mode serialisation (so defaulted fields are not advertised as required) and the `apiKey` property is stripped from the advertised schema while still accepted by Zod. `CallTool` resolves any of the 99 names (not only exposed ones). [CODE src/tool-registry.ts:747-776 `toMcpInputSchema`, 794-830 `listTools`, 864-929 `registerTools`] VERIFIED.
- Meta-tools: `discover_tools` ranks hidden tools; `execute_tool` re-validates `params` with the target tool's Zod schema and refuses to run meta-tools recursively. [CODE src/tools/meta-tools.ts:92-122] VERIFIED.
- Tests: `src/tool-registry.gate.test.ts`, `src/tool-registry.docs.test.ts`, `src/tool-hints.gate.test.ts`, `test/test-legal-research-analysis-dispatch.cjs` (schema-advertising contract) [CODE file list] VERIFIED present, not run.
- Limitations: hidden tools are callable directly by name, so the "10 exposed" surface is advisory, not an access boundary. `apiKey` remains a tool argument (80 schema fields declare it) so a model can be induced to pass a key in arguments, which then appear in transcripts. [CODE grep `apiKey: z.` = 80] VERIFIED; risk INFERRED.
- Waymaker relevance: Waymaker has no public MCP server; if it ever exposes one, keep credentials out of tool arguments entirely (server-side only), make "advertised" equal "callable", and generate schemas from one source. The general pattern (static registry + per-call validation + final output gate) is a standard idea, not distinctive.

### 1.2 MCP transport modes

- STDIO (default): stdout reserved for JSON-RPC; `console.log/warn/info/debug` are redirected to stderr. [CODE src/index.ts:55-63] VERIFIED.
- HTTP: `--mode http` (and legacy alias `sse`) starts Express with the SDK's Streamable HTTP transport in stateless mode (no session id, JSON responses, fresh Server+Transport per POST, closed on response close); `GET`/`DELETE /mcp` return 405; `/` and `/health` return status JSON. Docker image runs `--mode sse` on 0.0.0.0:3000 as non-root with a wget health check. [CODE src/server/http-server.ts:291-420; Dockerfile] VERIFIED. SSE was replaced by Streamable HTTP on 2025-12-20 [CODE git log 7bde977] VERIFIED.
- Startup fail-closed: a non-loopback bind without `MCP_AUTH_TOKEN` or an explicit unauthenticated override throws at boot; `TRUST_PROXY` must be an exact hop count 1-10; body limit, batch size, rate and fallback limits are parsed as strict integers and rejected if malformed. [CODE src/server/http-config.ts:23-107; src/lib/execution-limits.ts:46-63 `parseIntegerLimit`] VERIFIED. Consequence: the shipped Dockerfile (binds 0.0.0.0) will refuse to start unless the operator sets one of those env vars [INFERRED from the two files].
- Also: a CLI (`korean-law`, commander + natural-language router) and a `setup` subcommand that writes client config files. [CODE src/cli.ts; src/setup.ts] VERIFIED.
- Tests: `src/server/http-config.test.ts`, `http-server.contract.test.ts`, `http-server.envelope.test.ts` [CODE] present, not run.
- Waymaker relevance: Waymaker's backend is FastAPI; the transferable ideas are "fail closed at boot on unsafe bind/config" and "validate every numeric env var strictly", both generic.

### 1.3 API key management

- Resolution order for the upstream OC key: per-call override argument, then the request context (HTTP header or `?oc=` query), then env `LAW_OC` / `KOREAN_LAW_API_KEY`, then constructor default. [CODE src/lib/api-client.ts:60-68 `getApiKey`; src/index.ts:19] VERIFIED.
- HTTP accepts the key from six header spellings, `Authorization: Bearer` (only when it is not the server's own access token, compared in constant time), or `?oc=` unless `ALLOW_QUERY_API_KEY=0`; arrays from repeated query params are rejected with 400. [CODE src/server/http-server.ts:291-317, 22-27 `safeEqual`] VERIFIED.
- Leak prevention: URL masking of key-like query params on all error/log paths (`maskSensitiveUrl`), and a final output gate that masks key params anywhere in tool text plus any known key value of 8+ chars (`maskKeysInText` via `maskToolText`). This was added after upstream responses were found to echo the request OC inside detail links, exposing the shared server key. [CODE src/lib/fetch-with-retry.ts:19-40; src/lib/tool-output.ts; DOC CHANGELOG 4.14.1 Security] VERIFIED (code), README-ONLY (incident description).
- Setup wizard writes home-directory configs with mode 0600, and writes project-folder configs with an env-reference instead of the literal key. [CODE src/setup.ts:118-122; src/lib/project-mcp-config.ts:1-34] VERIFIED.
- Hosted model: a keyless caller is served with the operator's own key under a global token bucket and optional daily cap. [CODE http-server.ts:272-289, 320-340; server.json "Optional: without it the shared server key is used"] VERIFIED.
- Limitations: (a) the README recommends pasting the personal key into the connector URL as `?oc=`, which the code's own comments say leaks into proxy logs [DOC README.md "Q. Claude·ChatGPT…"; CODE http-server.ts:292-298] VERIFIED; (b) sharing the operator key with anonymous users sits uneasily with the project's own NOTICE/README statement that a key may be used only by the person it was issued to [DOC NOTICE; README "데이터 출처"] INFERRED tension; (c) history: commit `e41c4ce` (2026-07-31) states a tracked test-results file contained a real OC value in three links and deleted it; history was not rewritten (the file still exists in earlier commits by `git log -- <file>`). I did not open the blob. [CODE git show --stat e41c4ce; git log -- test-results-final.txt] VERIFIED metadata only.
- Waymaker relevance: Waymaker already redacts OC (`_sanitize_url`, [CODE backend/services/law_tools.py:241-259] VERIFIED). Lessons worth adopting as ideas: mask at the final output gate as well as at URL construction (upstream data can echo the key), and never accept the key from users or query strings.

### 1.4 Rate limiting

- Per-IP fixed 60-second window counting only `tools/call` messages (handshake and `tools/list` exempt), batch counted by number of calls, hard cap on calls per JSON-RPC batch (default 20) that applies even when the per-IP limiter is disabled; 429 with `Retry-After`. [CODE http-server.ts:174-235] VERIFIED.
- Keyless-fallback gate: token bucket (default 120/min, burst = 1 min) plus optional rolling 24 h cap [corrected by verifier: the code comment says "rolling", but `createDailyCap` (rate-limit.ts:60-87) is a fixed 24 h window that starts at the first call after a reset and zeroes the count when it expires]; `now` injectable for tests. [CODE src/lib/rate-limit.ts:28-87; http-server.ts:279-289] VERIFIED. Tests: `src/lib/rate-limit.test.ts` present, not run.
- Limitations: all in-process memory; per instance, not shared across replicas; IP identity depends on correct `TRUST_PROXY`. Nothing throttles the server's own outbound rate to law.go.kr beyond these inbound gates and the per-request budget [INFERRED from code].
- Waymaker relevance: Waymaker's AI endpoints are user-facing; counting cost-bearing calls (not handshakes) and capping batch amplification are sensible generic ideas.

### 1.5 Request budgets and deadlines

- One `RequestExecutionBudget` per outer HTTP request (shared across a JSON-RPC batch; created per call in STDIO) caps upstream attempts (default 48, counting retries and anti-bot hops), bytes per upstream body (8 MiB) and total bytes (24 MiB); final tool text capped at 50,000 chars. Exceeding throws `ExecutionLimitError`. [CODE src/lib/execution-limits.ts:21-146; tool-registry.ts:873-879; fetch-with-retry.ts:178-180] VERIFIED.
- Deadlines: 30 s per attempt, 45 s total per fetch including retries, 1.5 s minimum to start another attempt, 20 s body-idle timeout between chunks, 45 s per chain with partial-result assembly and explicit markers for missing branches. [CODE fetch-with-retry.ts:74-86; src/lib/response-body.ts:35; src/tools/chain-deadline.ts:1-40] VERIFIED.
- Tests: `execution-limits.test.ts`, `fetch-deadline.test.ts`, `response-body.deadline.test.ts`, `response-body.limits.test.ts`, `chain-deadline*.test.ts`, `batch-articles.limits.test.ts`, `verify-citations.budget.test.ts` present, not run.
- Waymaker relevance: high as an idea. A per-request upstream budget held in request context (Python `contextvars`) plus a total deadline shorter than the client timeout would bound `/api/ask` fan-out. Whether Waymaker has an equivalent is not verified in this task [UNVERIFIED]. [corrected by verifier: partly. Waymaker does cap fan-out by count. `_DEFAULT_MAX_QUERIES = 7` and `_HARD_MAX_QUERIES = 8` are commented "so a single /api/ask never fans out" [CODE backend/services/law_tools.py:130-134], and the source-family loop stops at that cap [CODE law_tools.py:1250-1273]. Each GET has its own urllib timeout [CODE law_tools.py:165-195]. A byte budget and a total wall-clock deadline for /api/ask were not checked. VERIFIED for the count cap; the rest is UNVERIFIED.]

### 1.6 Cancellation

- HTTP disconnect aborts a connection-level `AbortController`; each MCP item gets its own SDK signal; the two are combined so cancelling one batch item does not cancel siblings that share the budget. Signals flow into `fetch`, backoff sleeps, body readers and the anti-bot probe; cancelled calls are re-thrown rather than turned into a normal tool result. [CODE src/lib/session-state.ts:19-72; http-server.ts:359-372; tool-registry.ts:909-914 (rethrow at 913); fetch-with-retry.ts:161-171, 251-258, 322-338] VERIFIED.
- Tests: `fetch-with-retry.cancel.test.ts`, cancellation cases in `precedent-production.test.ts`, `verify-citations.production.test.ts` present, not run.
- Waymaker relevance: medium. FastAPI/Starlette can detect client disconnect; propagating it to outbound law calls avoids wasted quota.

### 1.7 Error handling, and whether upstream failure can be reported as absence

Designed defences (all VERIFIED by reading code):
- Retries on 429/503/504 (and 404 for the DRF endpoints, because the authors measured transient 404 bursts), exponential backoff with jitter from a 300 ms base, `Retry-After` honoured but clamped to 30 s; network errors unwrap undici's opaque cause into code + host. [CODE fetch-with-retry.ts:74-86, 116-130, 300-320; api-client.ts:14] 
- A 200 response whose body is empty or a whole HTML page is treated as an outage on search endpoints (retry), and on three single-record targets where the authors measured that a miss arrives as an empty/HTML 200, one short confirmation retry is made and then `UpstreamRecordMissingError` is raised. The error text explicitly says absence is not proven. [CODE src/lib/upstream-miss.ts:1-16, 49-107; api-client.ts:16-27, 113-130; body-shape.ts]
- Separate labels: `UPSTREAM_NO_DATA` is kept distinct from `NOT_FOUND`, with guidance that the reply must be reported as a lookup failure, not as non-existence. [CODE src/lib/errors.ts:12-30, 116-160]
- `rethrowIfFatal` (budget exhaustion or cancellation) is called first in 29 auxiliary `catch` blocks across 19 files so those cannot be swallowed into "0 results". [CODE src/lib/fatal-errors.ts:1-17; grep count] [corrected by verifier: 28 call sites in 18 files. The 29/19 count includes the definition at fatal-errors.ts:15.]
- `verify_citations` has an explicit `error` resolution distinct from `not_found`. [CODE src/tools/verify-citations.ts:288-294]

Residual paths where failure can still surface as absence or as a wrong status (code-read, not executed):

| # | Path | What happens | Status |
|---|---|---|---|
| R1 | `findRepealedLaw` (secondary "was it repealed?" search used by `verify_citations`) | non-fatal errors (network, 5xx after retries) return `undefined`; the comment states this deliberately keeps the old NOT_FOUND path. If the primary current-law search found nothing, the citation is then rendered as `[NOT_FOUND]` "no such law in the 법제처 DB" | [CODE src/lib/law-search.ts:289-303; verify-citations.ts:288-290, 459-460] VERIFIED (code + author comment) |
| R2 | `renamedLineage` | lineage lookup failure falls back to a "repealed" verdict instead of "renamed" (documented choice) | [CODE verify-citations.ts:296-316] VERIFIED |
| R3 | `parseSearchXML` | when the expected root element is missing it returns zero results rather than a parse error; a 200 XML envelope with a different root (the code comments describe a credential-verification failure that arrives as XML when the Referer is missing) would read as "0 results" | [CODE src/lib/xml-parser.ts:53-101; fetch-with-retry.ts:94-98] parser behaviour VERIFIED; end-to-end outcome INFERRED (no explicit detector for that envelope found by grep) [verifier addendum: re-checked. the client's private `readBody` (api-client.ts:101-130) rejects only blank and HTML bodies, and a grep for the envelope's message text, `resultCode` or `resultMsg` finds no detector. The same gap applies to `parseLawXml` (law-search.ts:71-89), a regex over `<law>` rows used by `findLaws`. A 200 envelope on lawSearch would therefore give zero rows without setting `lastInfraError`, and that could feed the R1 `not_found` path. The default Referer injection (fetch-with-retry.ts:175) makes the Referer-missing trigger unlikely unless overridden. INFERRED.] |
| R4 | abolished admin-rule note | `catch` returns `null` without `rethrowIfFatal`, so even budget/cancel is swallowed there (auxiliary note only) | [CODE src/lib/abolished-laws.ts:205-206] VERIFIED |

Waymaker relevance: high. Waymaker already distinguishes `not_found` from `timeout`/`forbidden`/`unavailable`/`parse_failed` and detects official error envelopes [CODE backend/services/law_query_normalizer.py:54-104; law_tools.py:539-604] VERIFIED. Two comparisons worth a Waymaker review (ideas, not code): Waymaker maps an empty 200 body to `law_api_no_results` [CODE law_tools.py:583-584] VERIFIED, while the reference's measurements say an empty 200 on search endpoints indicates an outage [DOC src/lib/upstream-miss.ts header; README-ONLY measurement]. And secondary lookups that decide a status must propagate failure, never default to the negative.

Separate Waymaker observation (not from the reference): Waymaker's default transport retries a law.go.kr request once with the opposite URL scheme on a network failure, which can downgrade an `OC`-bearing request from https to http [CODE backend/services/law_tools.py:197-238] VERIFIED; the security impact is INFERRED. [verifier addendum: the default host is https (law_tools.py:126). `_http_get_once` maps every `URLError` that is not a timeout to `network` (law_tools.py:187-191), so a TLS or certificate failure also triggers the plaintext retry with OC in the query. The downgrade is intended and pinned by `test_https_network_failure_falls_back_to_http` [TEST backend/tests/test_law_tools.py:118-129 (ran: pass as part of T1 re-run, 142 passed)].] The reference only allows http by explicit operator setting (`LAW_API_PROTOCOL`) [DOC .env.example; README].

### 1.8 Caching

- In-process LRU with per-entry TTL, expired-first eviction, hourly sweep; global 500 entries plus dedicated small caches (precedents 20, batch law texts 12, admin-rule documents 20) to bound heap; namespaced keys; TTL 1 h for "current" text by law ID (goes stale on amendment), 24 h for MST/date-pinned text; search results cached 60 s when an auxiliary lookup failed, otherwise 1 h; error results generally not cached; in-flight de-duplication of identical searches scoped to one request. Cache keys exclude the API key on the stated assumption that upstream results do not vary by key. [CODE src/lib/cache.ts:12-121; src/tools/search.ts:41-43, 153; law-text.ts:107-120, 397-412; law-search.ts:105-130; CLAUDE.md rule 10] VERIFIED.
- Limitations: per-process; no persistence; the "results don't vary by key" assumption is contradicted for targets where a key lacking that API's subscription receives a notice page (authors document this in upstream-miss.ts) - mitigated only because error results are not cached [INFERRED].
- Waymaker relevance: medium. Short TTL for "current" law and longer for date-pinned versions is a sound, generic rule; caching must never store failure as "no result".

### 1.9 Input validation

- Zod on every tool input (105 `z.object` uses, 90 `.max(` constraints, no `.strict()`); strict YYYYMMDD date schema; before Zod, a recursive pre-check rejects any string argument over 100 chars for article/annex number keys, 50,000 for `text`, 2,000 otherwise, including nested `execute_tool` params - added after ReDoS-style stalls of 12-24 s were measured. [CODE tool-registry.ts:836-858, 889-897; src/lib/schemas.ts:11-37; DOC CHANGELOG 4.14.1] VERIFIED code, README-ONLY timings.
- Advertised schemas set `additionalProperties: false`, but Zod objects strip rather than reject unknown keys [INFERRED from Zod default + no `.strict()`].
- Waymaker relevance: medium-high. Length caps before any regex and linear-time regexes for user text are generic best practice; Waymaker's normalizer runs regexes over user text [CODE law_query_normalizer.py:131-148].

### 1.10 Output size limits

- Final gate per call: mask keys, then truncate to `MCP_MAX_TOOL_RESPONSE_CHARS` (default 50,000 UTF-16 units, ~150 KB of Hangul) at a safe boundary, reserving room for an appended truncation notice; a summary mode and per-section truncation exist for chains; the env var can only lower the effective limit because inner calls use a fixed 50,000 constant. [CODE tool-registry.ts:859-862; schemas.ts:53-116, 127-170; CLAUDE.md rule 5] VERIFIED. Tests: `schemas.truncate.test.ts`, `schemas.test.ts` present, not run.
- Waymaker relevance: the final prompt in Waymaker already receives a summarised evidence pack [CODE law_tools.py:2456] VERIFIED; an explicit char cap with a visible truncation marker is a generic pattern.

### 1.11 Dependency security

- Production deps: MCP SDK, xmldom, commander, dotenv, express 5, kordoc (pinned 4.18.2, same author), pdfjs-dist (pinned 4.10.38), zod 4; `overrides` force patched transitive versions of hono, ip-address, sharp, adm-zip, onnxruntime-node. [CODE package.json] VERIFIED.
- Install hygiene: `npm ci --ignore-scripts` in CI, Docker and contributor docs; plugin runs `npx --ignore-scripts --omit=optional` pinned to an exact version; production graph pruned of optional deps and smoke-tested (`verify:annex-runtime` parses a generated minimal PDF). [CODE .github/workflows/ci.yml:36-50; Dockerfile; .claude-plugin/plugin.json; scripts/verify-annex-runtime.mjs] VERIFIED.
- CI/publish: actions pinned by commit SHA in `ci.yml` and `publish.yml`; `npm audit --omit=dev` only in `publish.yml`; publish workflow targets npm OIDC trusted publishing with provenance, but CLAUDE.md says the trusted publisher is not registered, so the canonical path is a local `npm publish` (no provenance). [verifier addendum: confirmed live. LIVE GET registry.npmjs.org/korean-law-mcp/4.15.9, 2026-10-19, HTTP 200, 3,482 bytes: `dist` has keys fileCount, integrity, shasum, signatures, tarball and unpackedSize, and no `attestations`. So 4.15.9 carries no provenance attestation. OBSERVED. publish.yml also skips the publish step when the version is already on the registry (publish.yml:47-61), so the release-triggered run only re-verifies.] `mirror-gitlab.yml` uses an unpinned `actions/checkout@v4` and pushes to a government GitLab that runs Gitleaks/Semgrep/OSV/Trivy. [CODE .github/workflows/*.yml; DOC CLAUDE.md] VERIFIED (workflows), README-ONLY (registration status).
- Known residual advisories: CHANGELOG records unpatched moderate advisories via `kordoc -> @huggingface/transformers / onnxruntime-node -> adm-zip` (optional graph). [DOC CHANGELOG.md:404-415] README-ONLY.
- Local gate: husky pre-commit runs `npm test`; `knip` dead-code check; `gc` script chains typecheck, knip, test, build. [CODE .husky/pre-commit; package.json scripts; knip.json] VERIFIED.
- `koda-ignore.yml` (a KODA scanner allow-list) suppresses three rules until 2027-08-03 with reasons: key-passing parameter wiring flagged as secret assignment, intentionally empty catch blocks (STDIO must not log), and XML string assembly in tests. [CODE koda-ignore.yml] VERIFIED as data.

### 1.12 Testing methodology

- Framework: vitest 4, node environment, only `src/**/*.test.ts`. [CODE vitest.config.ts] VERIFIED.
- Fixtures: almost all tests inject a fake `LawApiClient` (`fetchApi`/`searchLaw` stubs returning inline XML/JSON strings shaped like recorded upstream replies, e.g. `*.live-shape.test.ts`) or stub global `fetch` (21 files); one JSON fixture file (`src/tools/fixtures/three-tier-citation.json`). [CODE src/tools/committee-detail.live-shape.test.ts:1-30; grep] VERIFIED. Test names encode review rounds (`*.review2/3.test.ts`, `*.production.test.ts`) and issue numbers.
- Live tests: `test/*.cjs` (17 scripts) include smoke scripts that spawn `build/index.js` with `LAW_OC` from `.env` and one explicitly live fallback test; none is referenced by package scripts, husky or CI. [CODE test/test-all-tools.cjs:1-12; test/test-precedent-html-fallback-live.cjs:1-8; package.json] VERIFIED. Production docs record manual live calls during reviews. [DOC docs/PRODUCTION-REVIEW-*.md] README-ONLY.
- CI: GitHub Actions matrix Node 20.19.0 and 22.12.0: install, build (tsc), test, `verify:package`, prune + `verify:annex-runtime`. No live API job, no coverage gate. [CODE ci.yml] VERIFIED.
- Waymaker relevance: matches Waymaker's own approach (injectable transport, offline CI) [CODE law_tools.py:22-25] VERIFIED. Waymaker should keep fixtures it captured itself (OC-redacted) rather than reuse upstream fixtures.

### 1.13 Practices Waymaker must not adopt

- Browser impersonation: default `User-Agent` is a desktop Chrome string and a law.go.kr `Referer` is injected, because the API rejects Node's default UA and requires the Referer. [CODE fetch-with-retry.ts:88-107] VERIFIED. Waymaker uses an honest UA `Paradiso-law-tool-layer/2026.05` [CODE law_tools.py:137] VERIFIED.
- Anti-bot circumvention: on cloud IPs law.go.kr can return a JavaScript challenge page; `law-antibot.ts` decodes the obfuscated redirect and re-requests the token URL. [CODE src/lib/law-antibot.ts:1-14, 38, 75; fetch-with-retry.ts:189-205] VERIFIED. This conflicts with a no-anti-bot-bypass policy and is also the NOTICE's unlicensed-provenance file (section 2.2).
- A secondary scrape of the National Tax Service web page (`taxlaw.nts.go.kr`) for precedent bodies missing from the API. [DOC README.md "국세청 판례 서버"] README-ONLY. Waymaker should stay on official APIs.

---

## 2. Licensing and provenance

### 2.1 LICENSE (MIT) - what reuse requires

Copyright line: 2025, "Chris" [CODE LICENSE] VERIFIED. Paraphrase of the conditions: anyone may use, copy, modify, merge, publish, distribute, sublicense and sell the Software free of charge, on one condition - the copyright notice and the permission notice must be included in all copies or substantial portions; the Software is provided as-is with no warranty and no liability. MIT has no NOTICE-file clause, no patent clause, no attribution-in-UI requirement and no copyleft. If any portion were reused, Waymaker must preserve: (1) the exact copyright line, (2) the full permission paragraph, (3) the warranty/liability disclaimer, alongside the reused portion (a repository-level notices file is the usual practice).

Scope caveat: the reference's own NOTICE says the MIT license applies to code the maker wrote [DOC NOTICE first section] VERIFIED - so MIT does not by itself clear portions the NOTICE or code identifies as derived from others. 23 author names appear in git history, with no CLA/DCO and no inbound-license clause in CONTRIBUTING.md; inbound-equals-outbound is the usual assumption [CODE git log; DOC CONTRIBUTING.md] VERIFIED facts, INFERRED interpretation.

### 2.2 NOTICE contents

Three sections [DOC NOTICE] VERIFIED:
1. Data source: all statute/precedent/administrative-rule/ordinance/treaty/interpretation text comes from the 법제처 National Law Information Center Open API; statutes are said to be non-protected under Copyright Act Art. 7 but the source is credited; accuracy follows the provider; output may be processed or summarised so original text must be checked for legal effect; NTS interpretations come from taxlaw.nts.go.kr; each user needs their own OC key, usable only by the person it was issued to.
2. Third-party implementation: `src/lib/law-antibot.ts` re-implements in TypeScript the anti-bot parsing approach of LexLink-ko-mcp (`client.py` functions for following the anti-bot page and parsing its URL) and uses the same regex patterns; the NOTICE itself warns the source repository shows no license, that unlicensed works are all-rights-reserved, that copied expression has no redistribution basis without permission, and that permission or an independent replacement is needed - calling the notice provisional. Live check: LexLink-ko-mcp still reports no license (L2). OBSERVED. [verifier addendum: the NOTICE gives a reason for the identical regex patterns: the obfuscated law.go.kr script it parses has the same format. Its warning is also conditional ("if any expression was copied"). The code header of `law-antibot.ts` (lines 1-14) uses the stronger word "이식" (ported) for the LexLink approach. Re-fetched L2 on 2026-10-19: HTTP 200, `license: null`, `pushed_at` 2026-06-21. OBSERVED.]
3. Dependencies follow their own licenses.

[verifier addendum, provenance timeline: `NOTICE` was first added in commit `e41c4ce` on 2026-07-31. The same commit removed the tracked test-results file that held a real OC value. `law-antibot.ts` arrived in `92d5a74` on 2026-07-04, so the anti-bot port shipped for 27 days with no notice. No tag before 2026-07-31 contains NOTICE: `git show v4.9.1:NOTICE` fails. `package.json` `files` now ships `LICENSE` and `NOTICE` in the npm tarball. `exports` also exposes `./lib/*` and `./tools/*`, so the compiled anti-bot and LexDiff-derived modules can be imported from the npm package. [CODE git log --diff-filter=A -- NOTICE; git show --stat e41c4ce; package.json:9-26, 92-97] VERIFIED.]

### 2.3 DO-NOT-TOUCH paths for Waymaker

Tier A - named by NOTICE (unlicensed upstream, unresolved):
- `src/lib/law-antibot.ts` (all of it, including its regex patterns and probe size logic)
- `src/lib/law-antibot.test.ts`, `src/lib/law-antibot.cleanup.test.ts` (fixtures of the challenge pages)
- the anti-bot hook block inside `src/lib/fetch-with-retry.ts` (around lines 189-205) and the feature itself

Tier B - not in NOTICE, but the code/CLAUDE.md say they are ported from LexDiff (`chrisryugj/lexdiff`), whose LICENSE since 2026-04-13 is Business Source License 1.1 (non-production use only until 2030-04-14) (L4, L5); before that date LexDiff had no LICENSE file:
- `src/lib/search-normalizer.ts` (header says ported from LexDiff since the first commit; alias table synced from LexDiff on 2026-04-15) and `src/lib/search-normalizer.alias.test.ts`
- `src/lib/law-parser.ts` (JO code conversion), `src/lib/law-jo.ts` (boundary wrapper around it)
- `src/lib/three-tier-parser.ts`, `src/lib/three-tier-citation.ts` (adapter to the LexDiff parser)
- `src/lib/citation-content-matcher.ts` and its test (ported 2026-07-04 from a pinned LexDiff commit, i.e. after BSL adoption) [corrected by verifier: the port landed in `92d5a74` on 2026-07-04, after the BSL commit. The pin `lexdiff@f15d400` in the header (lines 37-45) is a later comparison reference, added in `787a7fc` on 2026-08-17, not a recorded port source. The same comment says that upstream file last changed on 2026-04-12, one day before LexDiff's LICENSE commit. The ported text may therefore predate the BSL file, but it was never under a permissive LexDiff licence either way.]
- the "LexDiff-style" JSON parsing section of `src/tools/law-text.ts` (~line 113) and the `licbyl` path of `src/lib/api-client.ts` (~line 319)
- [added by verifier] the content-verification step in `src/tools/verify-citations.ts` (~line 494). Its comment says it ports LexDiff `matchCitationContent`. Also `src/lib/article-anchor.ts` (~lines 108-122), which uses the LexDiff normaliser and alias table "read-only" as a consumer. [CODE grep -n -i lexdiff src] VERIFIED.
[CODE file headers; CLAUDE.md "Critical Rules" 1; docs/DEVELOPMENT.md:200, 252; git log] VERIFIED.

Tier C - lineage noted, lower risk or unknown:
- `extractEmbeddedAliases` in `search-normalizer.ts` says it borrows a pattern from the author's "stats-mcp" (license not checked) [CODE src/lib/search-normalizer.ts:388] VERIFIED mention, license UNVERIFIED.
- HWP/HWPX parsers written "with reference to" `roboco-io/hwp2md` (MIT, L3) were deleted on 2026-04-01 when parsing moved to `kordoc` [CODE git log 3821b93, 89211fd, b322038] VERIFIED; only in history.
- `kordoc` (dependency, MIT per lockfile, same author) - use only as a separate tool, never copy.

Interpretation (not legal advice): the LexDiff licensor and the korean-law-mcp author appear to be the same account (`chrisryugj`; CITATION.cff alias) [DOC CITATION.cff; L4] VERIFIED, so the author may have chosen to publish those files under MIT in korean-law-mcp. But the BSL text claims all derivative works of BSL versions, the NOTICE limits MIT to "code the maker wrote" without mentioning LexDiff, and post-2026-04-13 syncs exist. The status of LexDiff-derived code is therefore unresolved [INFERRED].

### 2.4 CITATION.cff

CFF 1.2.0, type software, title "Korean Law MCP", author given-name Chris with alias chrisryugj, repository and npm URLs, license MIT, keywords including citation-verification. It asks users who use the software to cite it; this is a request, not a license condition. [CODE CITATION.cff] VERIFIED.

### 2.5 Dependencies and licenses (from package-lock.json v3, 340 entries)

All 340 lock entries carry a `license` field; none UNKNOWN. [CODE package-lock.json via own parser script] VERIFIED. [corrected by verifier: `packages` has 340 keys including the root project (`""`, korean-law-mcp 4.15.9, MIT). That leaves 339 dependency entries, and the per-license counts below add up to 339. Re-parsed with an independent script; the production subset of 123 and its license mix match exactly. Dependency paths: argparse comes via markdown-it via kordoc, jszip via kordoc, and pako via jszip.]

| Group | Licenses |
|---|---|
| Direct prod | `@modelcontextprotocol/sdk` 1.32.1 MIT; `@xmldom/xmldom` 0.9.12 MIT; `commander` 14.0.3 MIT; `dotenv` 17.4.2 BSD-2-Clause; `express` 5.2.1 MIT; `kordoc` 4.18.2 MIT; `pdfjs-dist` 4.10.38 Apache-2.0; `zod` 4.6.2 MIT |
| Direct dev | `typescript` Apache-2.0; `vitest` MIT; `knip` ISC; `husky` MIT; `@types/*` MIT |
| Production graph (non-dev, non-optional: 123 pkgs) | 104 MIT, 7 ISC, 4 Apache-2.0, 3 BSD-2, 2 BSD-3, plus `argparse` Python-2.0 (via markdown-it, via kordoc), `jszip` "MIT OR GPL-3.0-or-later" (via kordoc; elect MIT), `pako` "MIT AND Zlib" |
| Copyleft flags | `@img/sharp-libvips-*` LGPL-3.0-or-later and `@img/sharp-*` "Apache-2.0 AND LGPL-3.0-or-later" - optional only (kordoc OCR/ML graph; production installs use `--omit=optional`); `lightningcss*` MPL-2.0 - dev only (via vite/vitest) |
| Other | `tslib` 0BSD (optional), `type-fest` "MIT OR CC0-1.0" (optional), `@huggingface/transformers` Apache-2.0 (optional) |

Counts across all 340: MIT 251, Apache-2.0 24, BSD-3 15, ISC 15, MPL-2.0 12, LGPL-3.0-or-later 10, Apache+LGPL 3(+1 with MIT), BSD-2 3, and one each of Python-2.0, MIT-or-GPL-3.0, MIT-and-Zlib, 0BSD, MIT-or-CC0. Lockfile `license` fields are self-declared metadata, not audited license texts [INFERRED].

### 2.6 Release history

- 32 git tags, v2.1.6 (2026-03-24) to v4.15.9 (2026-10-15); 26 of them between 2026-07-06 and 2026-10-15 (roughly one every 4 days); ten v4.15.x patches in 18 days. [corrected by verifier: 30 of the 32 tags fall between 2026-07-06 (v4.6.6) and 2026-10-15 (v4.15.9), about one every 3.4 days. Only v2.1.6 and v4.4.0 are older. The v4.15.x line is ten tags, v4.15.0 plus nine patches, from 2026-09-28 to 2026-10-15, which is 17 days. Six tags are annotated and the rest lightweight. Source: git for-each-ref --sort=creatordate.] CHANGELOG has 79 versioned sections (1.8.0 2026-03-10 onward) plus "Unreleased": major 1 (3), 2 (1), 3 (10), 4 (65). Many versions have no tag. [CODE git for-each-ref; CHANGELOG.md headings] VERIFIED.
- Commit cadence by month: 2025-12 68, 2026-01 2, 02 10, 03 43, 04 67, 05 21, 06 14, 07 68, 08 93, 09 32, 10 55. VERIFIED.
- CHANGELOG themes (keyword counts): measured-evidence wording 28, budget 19, hallucination 16, cancellation 16, cache 15, kordoc 15, repealed-law handling 14, regression 13, security 12, token reduction 12, review rounds 11, anti-bot 9, breaking 3. Section types: Fixed 43, Changed 20, Added 20, Security 6. Security entries cover: OC key masking at output, ReDoS fixes, batch-amplification limit, dependency advisories (hono, xmldom, sharp), plaintext key in project configs. [CODE grep CHANGELOG.md] VERIFIED.
- CLAUDE.md admits GitHub Releases for v4.10.0 and v4.11.0 were created retroactively. [DOC CLAUDE.md] README-ONLY.

### 2.7 Usage obligations for upstream law.go.kr data (as stated by the project)

Only: credit 법제처 as source; check the original for legal effect; accuracy follows the provider; each user obtains their own OC key, usable only by its holder. [DOC NOTICE; README.md "데이터 출처"] VERIFIED. The project does not cite or summarise the Open API's own terms of use; I did not verify those terms (L6 only confirmed the guide index is reachable) [UNVERIFIED]. The Art. 7 claim is README-ONLY; as far as I know Art. 7 also lists court judgments, which the NOTICE does not say - not checked in this task [UNVERIFIED].

### 2.8 Model-training authorisation

No statement anywhere authorises (or forbids) using the tool outputs or docs for model training: grep for train, 학습, terms, 약관, KOGL/공공누리, copyright across README, README-EN, docs/, ROADMAP, CONTRIBUTING, skills/, .claude-plugin/ found only license badges and unrelated hits. [CODE grep] VERIFIED (negative result for those patterns). MIT covers the Software and its documentation files, but tool outputs are government data the project does not own, so nothing here can license training on them [INFERRED]. Waymaker should not treat this repo or its outputs as training or eval data.

### 2.9 CLAUDE.md, skills/, .claude/, koda-ignore.yml read as data

What they show about development practice (not followed as instructions):
- Heavily agent-driven development: 74% of commits have a Claude co-author trailer; numbered "review" rounds with independent re-review are recorded in commit messages, CHANGELOG and `docs/PRODUCTION-REVIEW-*`. Measured numbers ("실측") back most decisions. [CODE git log; DOC CHANGELOG] VERIFIED.
- Hard house rules: LexDiff-ported files must not be edited without comparing against upstream; target under 200 lines per file (admitted: 45 files exceed it); Zod on all inputs; `truncateResponse` on all outputs; no console output (STDIO); log only through a scrub function; mask keys; String() for numeric args. [DOC CLAUDE.md Critical Rules 1-13] VERIFIED as data.
- Deployment knowledge lives outside the repo (`~/workspace/gomdori-mcp`), with a warning never to `fly deploy` from this repo; release = npm publish, wait for propagation, bump a pin in another repo, deploy, then create the GitHub Release. [DOC CLAUDE.md; .claude/commands/deploy.md] VERIFIED as data.
- `skills/korean-law/SKILL.md` (MIT) routes users to tools and tells the model to treat retrieved law text as data, quote from retrieved originals, and run citation verification. [DOC skills/korean-law/SKILL.md] VERIFIED as data.
- `.claude/next-sessions.md` and `.claude/plans/web-ui-chatbot.md` are leftover agent prompts/plans committed to the repo (the latter plans a web chatbot where users type their own key). [DOC] VERIFIED as data.
- References to an uncommitted `_workspace/` (QA verification and legal-wording review notes) mean some cited evidence is not in the repo. [CODE upstream-miss.ts, errors.ts comments] VERIFIED.

---

## 3. Waymaker cross-check

### 3.1 Attribution files

- `ATTRIBUTIONS.md`: shadcn/ui, Unsplash, pdf-lib, fontkit, Nanum Gothic, qrcode-generator, and government forms. No mention of korean-law-mcp. [CODE ATTRIBUTIONS.md:1-15] VERIFIED.
- `THIRD_PARTY_NOTICES.md`: a korean-law-mcp section (author, MIT, "upstream version studied: npm korean-law-mcp@4.9.0", relationship "algorithms ported to Python", nothing vendored or executed), a table mapping upstream `lib/search-normalizer.ts` functions (normalisation, alias key, alias resolution, embedded aliases, query expansion) and `lib/law-search.ts` functions (loose match, resolved match, relevance score, non-law keyword stripper, fallback ladder with display 100) to Python, a "not taken" list (no MCP/transport/CLI, no kordoc, no decision compaction, no citation content matcher, no upstream tax/labour/customs alias data), and the full MIT text. Also Public-Regulation-MCP-Builder (design principle only) and lucide icons. [CODE THIRD_PARTY_NOTICES.md:9-115] VERIFIED. It still says "Paradiso" (pre-rebrand), cosmetic.

### 3.2 Grep results (korean-law-mcp, chrisryugj, kordoc, plus lexdiff/lexlink/hwp2md/gomdori)

14 files match, excluding .git/.venv-check [CODE grep -rIl] VERIFIED: [corrected by verifier: 14 is the count for the three brief terms (korean-law-mcp, chrisryugj, kordoc) alone. That set includes `.github/workflows/hikorea-manual-sync.yml` and `.github/workflows/hikorea-manual-converter-benchmark.yml`, which are not listed below. Both name kordoc and hwp2md as optional external backends that CI does not install (`KORDOC_CMD` repo variable; sync workflow lines 45-58). With the extra terms (lexdiff, lexlink, hwp2md, gomdori) the union is 17 files, the three readability audit reports being the extra ones. Waymaker has zero hits for lexdiff or lexlink.]
- Derived code: `backend/services/law_query_normalizer.py` (docstring attribution lines 25-30), `backend/services/law_tools.py` (line 9 "korean-law-mcp principle").
- Docs: `THIRD_PARTY_NOTICES.md`, `docs/EXTERNAL_SKILLS_AND_LEGAL_GROUNDING_STRATEGY.md` (phased adoption plan, remote `korean-law-mcp.fly.dev` endpoint), `docs/audits/source-grounding-and-law-mcp-audit-2026-06-14.md`, `docs/integrations/PUBLIC_DATA_AND_LAW_GROUNDING_AUDIT.md`, `docs/integrations/UNIFIED_SEARCH_AND_LEGAL_EVIDENCE_OPS.md` (Option A "port the algorithms" chosen), `docs/data/LAW_API_OC_EVIDENCE_TOOL_LAYER_2026_05.md`, `audits/ai-grounding/grounding_code_search.txt`.
- kordoc/hwp2md as optional external converters: `docs/hikorea_manual_sync.md`, `scripts/convert_manual_hwp.py`, `scripts/tests/test_convert_manual_hwp.py`, and three manual-readability audit reports. These invoke tools as subprocesses; nothing vendored. `docs/hikorea_manual_sync.md` labels kordoc "(Python)" / `pipx install` in one table (line ~114/129) and `npm install -g kordoc` in another (line ~195); the reference lockfile shows kordoc is an npm package [CODE package-lock.json] VERIFIED; the "(Python)" label looks wrong [INFERRED]. It also records hephaex/hwp2md as GPL-3.0-only, run only as a subprocess.
- No hits for distinctive upstream identifiers: anti-bot, `location.assign`, `UPSTREAM_NO_DATA`, `[NOT_FOUND]`, rethrow-if-fatal, single-record-lookup, JO builder, `cleanHtml`, compaction helpers, `thdCmp`/`lsStmd`, `discover_tools`/`execute_tool`. `Mozilla/5.0` appears only in Playwright QA scripts, not in backend services. [CODE grep] VERIFIED.

### 3.3 Waymaker files that look derived

| Waymaker file | Evidence of derivation | Acknowledged? |
|---|---|---|
| `backend/services/law_query_normalizer.py` | `normalize_law_search_text` follows the upstream replacement sequence step for step (lines 131-148); the typo map is the six "법" substitutions of the upstream map, same order (113-114); the non-law keyword list has 60 words, 48 shared with the upstream 85-word list, the first 25 in identical order (419-425); loose-match rule (447-454) and relevance weights (469-486) mirror upstream; `LAW_ALIAS_ENTRIES` reuses the upstream identifier (alias content is Waymaker's own immigration list) | Yes, as korean-law-mcp MIT. Not acknowledged: the normaliser, typo map and alias mechanism come from the upstream file that is itself LexDiff-derived (section 2.3 Tier B) |
| `backend/services/law_tools.py` (`search_laws_ranked`, lines 786-860) | implements the ported fallback ladder and display-100 reasoning | Yes in THIRD_PARTY_NOTICES; but the module docstring (lines 1-17) says it was built without copying any third-party code - inconsistent |
| `backend/tests/test_law_query_normalizer.py` | regression tests for the ported behaviour (민법/난민법 substring trap) written in Waymaker's own form | Yes |
| `docs/integrations/PUBLIC_DATA_AND_LAW_GROUNDING_AUDIT.md:223-249`, `docs/data/LAW_API_OC_EVIDENCE_TOOL_LAYER_2026_05.md:62-66` | state "conceptual inspiration only" / "no third-party code" | Stale since the July 2026 port (commit 98288ad, PR #545) |
| `backend/services/citation_verifier.py`, `legal_analysis.py`, `legal_research.py` | names coincide with upstream tool names (`verify_citations`, `legal_analysis`, `legal_research`), but headers and structure show different, immigration-specific deterministic logic | No derivation seen [INFERRED from headers; no full diff] |
| [added by verifier] `backend/services/statute_citation_guard.py` (same commit 98288ad) | Has a `title_mismatch` status, the same idea as upstream's content check, which is LexDiff-derived. The mechanism differs: `_titles_agree` (lines 226-230) tests normalised equality or containment. It has no 30-character substring layer and no character-bigram Jaccard threshold. Its failure taxonomy (law/article not in evidence pack, repealed, unverifiable) is Waymaker's own. | Not derived as far as seen [CODE statute_citation_guard.py:1-25, 226-296] INFERRED |

[CODE paths and lines above; own overlap script] VERIFIED; derivation judgement INFERRED. Waymaker tests T1: 142 passed.

[verifier addendum: lineage split of the port.
- LexDiff-marked part. The upstream file `search-normalizer.ts` has carried the "ported from LexDiff" header since its first commit, `8b8c31f` on 2025-12-19. It holds the normalisation ladder, the typo map, the alias key and alias resolution, which correspond to Waymaker's `normalize_law_search_text`, `_BASIC_CHAR_MAP`/`normalize_basic_typos`, `normalize_alias_key` and `resolve_law_alias`.
- Unmarked part. `law-search.ts` has no LexDiff marker; it was created in korean-law-mcp on 2026-04-18 (`67d0880`). It holds the loose match, relevance weights, non-law keyword list and fallback ladder, which correspond to `loose_match_law_name`, `resolved_law_matches`, `score_law_relevance`, `_NON_LAW_KEYWORD_RE` and `search_laws_ranked`. As far as the repository shows, this part is the korean-law-mcp author's own MIT code.
- Mixed part. `extractEmbeddedAliases` was added 2026-05-19 (`1a9d9df`) inside the LexDiff-headed file, but its comment credits a "stats-mcp" pattern, not LexDiff.
- Waymaker studied `korean-law-mcp@4.9.0` (CHANGELOG: 2026-07-26). That version predates NOTICE (2026-07-31), so no NOTICE existed then. The LexDiff header was present in the 4.9.0-era source (`git show 23f9947:src/lib/search-normalizer.ts`). tsconfig does not set `removeComments`, so the header very likely shipped in the compiled npm build too. I did not download the tarball, which would need the user's permission. INFERRED.
- Re-checked by the verifier: the 60/48/25 keyword overlap (own script, independent of the original), the same normalisation step order (NFC, exotic spaces, dashes, equals signs, section sign, dash and dot spacing, typo map, Latin/Hangul split, whitespace collapse, parenthesis trim; the only difference is which equals-sign variant is folded), the six 법 substitutions in upstream order, and identical loose-match and relevance rules. VERIFIED.] The owner's unpushed branch `fix/waymaker-qa-2026-10-16` does not touch `law_query_normalizer.py`, `law_tools.py`, `citation_verifier.py`, `korean_law_client.py`, `THIRD_PARTY_NOTICES.md` or `ATTRIBUTIONS.md` and adds no korean-law-mcp references [CODE git diff --name-only 0713370...branch] VERIFIED, so it does not change these conclusions.

---

## 4. Independent development policy (Waymaker checklist)

### 4.1 Distinctive expression to avoid (by area; never copy, translate line-by-line or paraphrase closely)

- [ ] Tier A/B/C DO-NOT-TOUCH files in section 2.3 (anti-bot module and tests; LexDiff-derived normaliser, alias table, typo map, JO parser, three-tier parser, citation content matcher).
- [ ] Tool catalogue expression: names, Korean descriptions, category prefixes, exposure choices and aliases in `src/tool-registry.ts`, `src/lib/tool-profiles.ts`, `src/lib/tool-discovery.ts`, `src/tools/meta-tools.ts`.
- [ ] Natural-language routing tables and vocabularies: `src/lib/route-patterns.ts`, `query-router.ts`, `query-extract.ts`, `scenario-rules.ts`, `date-patterns.ts`, `route-explain.ts`, CLI files.
- [ ] Scenario/chain designs and feature names: `src/tools/scenarios/*`, `chains.ts`, `legal-research.ts`, `legal-analysis.ts` (task/mode dispatch), time-travel, impact map, cite check, applicable-law, ordinance radar, five-step action plan.
- [ ] Curated data: `src/lib/risk-rules.ts`, `document-analysis.ts`, the non-law keyword list in `law-search.ts`, ordinance-to-parent-law fallback table in CLAUDE.md, alias dictionaries.
- [ ] Precedent compaction heuristics: `decision-compact.ts`, `precedent-summary.ts`, `precedent-keywords.ts`, `unified-decisions.ts` domain configs.
- [ ] Error/label wording and model-directed warnings in `errors.ts`, `upstream-miss.ts`, `verify-citations.ts` renderers (bracket label vocabulary, uncertainty phrasing).
- [ ] Tests and fixtures: all `src/**/*.test.ts`, `src/tools/fixtures/*`, `test/*.cjs`.
- [ ] Prose and media: README(s), CHANGELOG, CLAUDE.md, `docs/*`, `skills/*`, `.claude/*`, plugin manifests, `demo.gif`, `docs/*.jpg`, icon.
- [ ] Tuning constant sets justified by their measurements (attempt budget, backoff base, idle/miss timers, chain deadline, cache sizes/TTLs): derive Waymaker's own from Waymaker measurements; do not import the set wholesale.
- [ ] Browser-UA impersonation, Referer forging, anti-bot handling, web scraping fallbacks (policy, not only licensing).

### 4.2 Functional overlap that is unavoidable (comes from the official API, the MCP spec, or generic engineering)

- Open API surface from the official guide: DRF search/detail endpoints, parameter names (`OC`, `target`, `type`, `query`, `display`, `page`, IDs, MST, JO, effective-date), target codes, 100-row display ceiling, Korean response field names, the 6-digit article (JO) code format, single-object-vs-array responses, 200-status error envelopes.
- Observable API behaviour any client meets: substring (LIKE) matching with 가나다 ordering (hence the 민법/난민법 hazard), transient errors, empty bodies. Ideas and facts are free; Waymaker's own wording, tests and fixtures must be its own.
- MCP protocol shapes (`tools/list`, `tools/call`, annotation names, stateless Streamable HTTP) from the MCP spec and official SDK examples.
- Generic patterns: retry with exponential backoff and jitter, honouring `Retry-After`, token bucket, LRU+TTL cache, per-request context, abort/timeout propagation, length caps before regex, final output truncation with a marker, secret masking.

### 4.3 Clean-room process

1. Requirements: write them from Waymaker needs (immigration scope, evidence statuses, disclaimers) and the official open.law.go.kr guide pages, recording page URL and access date. Do not reference korean-law-mcp files.
2. Design doc first, in the Waymaker repo, citing only the official guide, the MCP spec/SDK docs, Python stdlib/httpx docs and Waymaker's own measurements. The author states in writing that they did not consult the reference source for that module.
3. Tests first, from the official spec and from responses Waymaker itself captured (OC redacted at capture). No upstream fixture, test name or test structure.
4. Implementation by someone (human or agent session) without the reference repo in context. Agent sessions get a rule: never open `scratchpad/ref/korean-law-mcp` (or any copy) while writing the corresponding module; reference clones stay outside the repo and are never executed.
5. Contaminated people (anyone who read the reference source) may answer only functional yes/no questions, logged in the PR.
6. Similarity review before merge: a reviewer checks the diff against section 4.1 - identifiers, list contents and ordering, regex literals, comments, error strings, test names - and runs a token n-gram overlap check against the DO-NOT-TOUCH files; result recorded in the PR.
7. Provenance record: update `THIRD_PARTY_NOTICES.md` for every module, either "independently developed under the clean-room process (PR #, reviewer)" or, for real ports, upstream file, version, license text and full lineage.
8. For the existing port (`law_query_normalizer.py`): either (a) disclose the LexDiff lineage and get written confirmation from the author that the korean-law-mcp copies are MIT, or (b) re-implement the normaliser, typo map, alias-key/alias-resolution and embedded-alias functions through steps 1-7 and remove the port claim. Owner or counsel decides; this note is not legal advice.

---

## 5. Open questions

- Does the author confirm that LexDiff-derived files published in korean-law-mcp are MIT despite LexDiff's BSL 1.1 (adopted 2026-04-13)?
- What do the Open API's own terms of use say about redistribution, AI use, attribution and shared keys? Not verified here.
- Does Waymaker have a per-request upstream call budget and a total deadline for `/api/ask` law fan-out? Not checked.
- Should Waymaker treat an empty 200 body on law search as `unavailable` rather than `not_found`? That needs Waymaker's own capture data.
- Is the https-to-http scheme fallback in Waymaker's transport intended for credential-bearing requests? [verifier: the fallback is deliberate: a unit test asserts the https-to-http retry on a URL carrying an OC parameter (test_law_tools.py:118-145). Whether the security trade-off was intended is a question for the owner.]

---

## Verification pass

Verifier: independent adversarial re-check on 2026-10-19. Same evidence rules apply. I did not execute, build or install anything from the reference repo. Live requests were public read-only GETs: three to api.github.com (re-fetching L2, L4 and L5) and one to registry.npmjs.org (new, V1). No secrets were printed. The reference author's e-mail address appears in its git metadata and is deliberately omitted here.

| Live # | Request (2026-10-19) | Result |
|---|---|---|
| L2' | `GET api.github.com/repos/rabqatab/LexLink-ko-mcp` | HTTP 200; `private: false`; `license: null`; `pushed_at` 2026-06-21T09:19:34Z |
| L4' | `GET api.github.com/repos/chrisryugj/lexdiff/license` | HTTP 200; path `LICENSE`; SPDX `NOASSERTION`; decoded text is BSL 1.1, Licensor chrisryugj, Licensed Work lexdiff, Change Date 2030-04-14, Change License Apache-2.0, additional grant for non-production use only |
| L5' | `GET api.github.com/repos/chrisryugj/lexdiff/commits?path=LICENSE&per_page=100` | HTTP 200; exactly 1 commit, `dbe9bbb`, 2026-04-13T15:40:22Z, subject "chore: apply recent updates" |
| V1 | `GET registry.npmjs.org/korean-law-mcp/4.15.9` | HTTP 200, 3,482 bytes; license MIT; `dist` has no `attestations` (no npm provenance) |
| T1' | `cd Visable-genesis && .venv-check/bin/python -m pytest -q -p no:cacheprovider backend/tests/test_law_query_normalizer.py backend/tests/test_law_tools.py` | `142 passed, 5 warnings in 4.92s` |

### Verdicts on the 15 headline claims

| # | Claim (short) | Verdict | Evidence / correction |
|---|---|---|---|
| 1 | NOTICE: law-antibot.ts reimplements LexLink-ko-mcp parsing, same regexes, no license, provisional | confirmed | [DOC NOTICE "참조한 제3자 구현" section]; L2'. Nuance: NOTICE explains the identical regexes by the identical target-script format; its warning is conditional ("if expression was copied"); code header uses "이식" (port). |
| 2 | search-normalizer, law-parser, three-tier-parser, citation-content-matcher marked as LexDiff ports; NOTICE silent on LexDiff | confirmed | [CODE search-normalizer.ts:3; law-parser.ts:3; three-tier-parser.ts:3; citation-content-matcher.ts:12-13; CLAUDE.md:150-152; NOTICE]. Headers present since first commit 8b8c31f. More LexDiff markers: verify-citations.ts:494 (content check), law-jo.ts:1, three-tier-citation.ts:2-4, article-anchor.ts:108-122 (consumer), docs/DEVELOPMENT.md:200,252. |
| 3 | LexDiff LICENSE = BSL 1.1 (chrisryugj, non-production, 2030-04-14), one commit 2026-04-13, none before | confirmed | L4', L5'. "None before" holds for the `LICENSE` path only, since GitHub path history does not follow renames. Status OBSERVED. |
| 4 | law_query_normalizer.py closely translates upstream (step order, six 법 typos, 48/60 keywords, first 25 in order, loose-match, weights) | confirmed | Own independent script: Waymaker list has 60 entries, upstream 85, 48 shared, identical prefix of 25, LCS 43. Read side by side: law_query_normalizer.py:113-148, 419-486 against search-normalizer.ts:18-31, 324-357 and law-search.ts:39-106. |
| 5 | THIRD_PARTY_NOTICES credits korean-law-mcp (MIT, 4.9.0, full text) but not LexDiff; law_tools docstring and two docs contradict | confirmed | [CODE THIRD_PARTY_NOTICES.md:9-69]; Waymaker grep for lexdiff/lexlink = 0 hits; law_tools.py:5-7 (blame: written 2026-06-04, before the 2026-07-27 port 98288ad); PUBLIC_DATA_AND_LAW_GROUNDING_AUDIT.md:228; LAW_API_OC_EVIDENCE_TOOL_LAYER_2026_05.md:65. |
| 6 | Failed repealed-law search can surface as [NOT_FOUND], deliberately | confirmed | [CODE law-search.ts:289-303 (comment at 301); verify-citations.ts:288-290, 459-460]. Precondition: every current-law candidate search returned zero rows *without* an infra error. If any search returned rows, the result is `loose_only` (⚠). If all failed for infrastructure reasons, `findLaws` throws (law-search.ts:239-244) and the result is `error` (⚠). |
| 7 | Missing root → 0 results; 200 XML credential-failure envelope could read as "no results" | confirmed (as INFERRED) | [CODE xml-parser.ts:74-76, 82-84; api-client.ts:101-130 (blank and HTML guards only); fetch-with-retry.ts:94-98]. Grep found no envelope detector. The same gap exists in `parseLawXml` (law-search.ts:71-89). Default Referer injection makes this specific trigger unlikely. |
| 8 | Per-request budget shared across batch; 30 s/45 s; 20 s body-idle; combined signals; final mask + 50,000-char gate | confirmed | [CODE execution-limits.ts:21-32 (48 attempts, 8 MiB, 24 MiB, 50,000); fetch-with-retry.ts:74-86, 177-180; response-body.ts:35; session-state.ts:34-63; tool-registry.ts:859-929]. |
| 9 | Stateless Streamable HTTP; non-loopback bind refused without token/override; tools/call-only rate limit, batch cap, token bucket for keyless | confirmed | [CODE http-config.ts:70-107; http-server.ts:174-235, 272-289, 343-349, 404-415; rate-limit.ts:28-87]. Nuance: the "rolling" daily cap is a fixed 24 h window (corrected inline in 1.4). |
| 10 | Spoofed Chrome UA, forged law.go.kr Referer, anti-bot decoding; Waymaker honest UA | confirmed | [CODE fetch-with-retry.ts:88-107, 173-205; law-antibot.ts:1-14; Waymaker law_tools.py:137, 174]. The Waymaker UA still says "Paradiso" (cosmetic). |
| 11 | All 340 lock entries licensed; prod 123 permissive except argparse/jszip/pako; LGPL only optional sharp; MPL only dev lightningcss | confirmed | Own parser: 340 `packages` keys including the root project, so 339 dependencies; 0 missing. Prod 123 = MIT 104, ISC 7, Apache 4, BSD-2 3, BSD-3 2, plus Python-2.0, MIT-or-GPL-3.0+ and MIT-and-Zlib. LGPL-3.0+ appears only on `optional` @img/sharp-*; MPL-2.0 only on `dev` lightningcss*. |
| 12 | Nothing authorises/addresses model training; data obligations = credit 법제처, check original, own OC key | confirmed | Re-ran a case-insensitive grep (train, 학습, 약관, KOGL, 공공누리, 이용조건, terms of use/service, copyright, 저작권) over README*, docs, ROADMAP, CONTRIBUTING, skills, .claude-plugin, .claude, NOTICE, CLAUDE.md, server.json. Only unrelated hits plus NOTICE:12, 34. [DOC README.md:1162-1177]. |
| 13 | vitest, 167 files, ~1,170 call sites, offline; 17 .cjs not in CI; Node matrix, SHA-pinned, `npm ci --ignore-scripts`; audit only in publish; provenance inactive | corrected | Call sites are about 1,200 (1,196 to 1,221 by pattern), not 1,170. Everything else confirmed: [CODE vitest.config.ts; ci.yml (matrix 20.19.0/22.12.0, SHA-pinned checkout/setup-node, `npm ci --ignore-scripts`); publish.yml:40, 62-64; mirror-gitlab.yml:20 unpinned]. Provenance absence is now OBSERVED live (V1), not only README-ONLY. |
| 14 | 32 tags v2.1.6 (2026-03-24) to v4.15.9 (2026-10-15); 79 CHANGELOG versions; 348/473 Claude co-author | confirmed | [CODE git tag / for-each-ref; grep -cE '^## \[x.y.z' = 79; git log --grep = 348; rev-list HEAD = 473]. Inline detail fixed: 30 tags since 2026-07-06, not 26; v4.15.x spans 17 days; 96 session links, not 95. |
| 15 | Waymaker retries once with the opposite scheme, so an OC-bearing request can drop from https to http | confirmed | [CODE law_tools.py:196-238; default https at :126]. Also triggered by TLS or certificate errors (non-timeout `URLError` maps to `network`, :187-191). Pinned by a test [TEST test_law_tools.py:118-129 (ran: pass)]. |

### Other inline corrections made
- §0: 96 claude.ai/code session links, not 95; 473 is the HEAD count (586 across all refs).
- §0 and §1.12: about 1,200 test call sites.
- §1.4: the daily cap is a fixed window.
- §1.7: rethrowIfFatal has 28 call sites in 18 files.
- §2.3 Tier B: corrected the citation-content-matcher port and pin dates, and added the verify-citations content check.
- §2.5: 340 keys = root + 339 dependencies.
- §2.6: tag cadence.
- §3.2: grep file list now includes the two workflows; the union with extra terms is 17.
- Spot-checks that held: 99 tools / 10 exposed; package.json "9 tools"; 80 `apiKey: z.` fields; 105 `z.object`, 90 `.max(` and 0 `.strict()`; abolished-laws.ts:204-206 swallow; e41c4ce metadata (blob not opened); Waymaker empty-body → `law_api_no_results` (law_tools.py:583-584); owner branch touches none of the attribution or normaliser files and adds no korean-law-mcp or LexDiff text (`git diff --name-only 0713370...fix/waymaker-qa-2026-10-16`, 7 commits).

### Omissions against the brief: filled
1. **Provenance timeline.** NOTICE was added 2026-07-31 (e41c4ce), 27 days after law-antibot.ts (2026-07-04). No tag up to v4.9.1 has a NOTICE, so the 4.9.0 version Waymaker studied had none. VERIFIED.
2. **npm distribution.** `files` ships LICENSE and NOTICE. `exports` exposes `./lib/*` and `./tools/*`, so the DO-NOT-TOUCH modules are importable from the package. Waymaker must not depend on or import the npm package's internals. VERIFIED (package.json).
3. **Lineage split of Waymaker's port.** Only the search-normalizer half (normaliser, typo map, alias key and resolution) carries the LexDiff marker. The law-search half (loose match, scores, keyword list, ladder) has no marker. This narrows the re-implementation scope in §4.3 step 8(b). VERIFIED markers; legal effect INFERRED.
4. **statute_citation_guard.py assessed.** Not derived: its title check is equality or containment, not the upstream two-layer matcher. INFERRED.
5. **Waymaker fan-out cap.** It exists (7 default, 8 hard per /api/ask). This partly answers open question 3. VERIFIED.
6. **npm provenance.** Checked live (V1). OBSERVED.
7. **TLS-failure path of the scheme downgrade, and the pinning test.** VERIFIED.
8. **XML-envelope gap in `parseLawXml`** feeding the R1 NOT_FOUND path. INFERRED.

### Omissions: could not fill
- Open API (open.law.go.kr) terms of use on redistribution, AI use and shared keys. Not fetched; this belongs with the official-API notes. UNVERIFIED.
- Whether the compiled `korean-law-mcp@4.9.0` npm tarball carried the LexDiff header comment. Checking would mean downloading the tarball, which needs the user's permission. INFERRED likely, because tsconfig lacks `removeComments`.
- Whether LexDiff had a licence file under another name (e.g. `LICENSE.md`) before 2026-04-13. Not queried, to stay within request limits.
- Whether Waymaker has a total wall-clock deadline or byte budget for /api/ask law fan-out.
- Scope of Copyright Act Art. 7 (whether judgments are covered). Not checked; it stays UNVERIFIED as the original note says.
