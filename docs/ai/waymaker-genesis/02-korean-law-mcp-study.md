# 02 — korean-law-mcp reference study

Status: **RESEARCHED ONLY**. The reference was read as untrusted data. Nothing
from it was executed, installed, built or tested, and nothing from it was copied
into Waymaker. The "independent Waymaker design" column in §7 points at WLIE
components that are **IMPLEMENTED BUT NOT VALIDATED** ([05](05-legal-intelligence-architecture.md),
[06](06-temporal-law-and-source-identity.md), [07](07-evidence-verification-design.md)),
or at Mission 002 work that is **NOT STARTED** ([17](17-mission-002-plan.md)).

Sources for this document: [research-notes/ref-capabilities.md](research-notes/ref-capabilities.md)
(capabilities, live observations, verification pass),
[research-notes/ref-ops-license.md](research-notes/ref-ops-license.md) (operational
engineering, licensing, verification pass) and
[research-notes/law-stack.md](research-notes/law-stack.md) (the Waymaker side).
Licensing and provenance are covered in [03](03-reference-provenance.md); this
document only summarises them where they decide what Waymaker may learn from.

## 0. Conventions

* `[CODE ref:src/…]`, `[DOC ref:README…]` and `[TEST ref:…]` point into the reference
  repository at the examined commit. The research notes write these paths without
  the `ref:` prefix. The prefix is added here only to keep them apart from Waymaker
  paths.
* Waymaker paths (`backend/…`, `lib/…`, `experiments/…`) are repo-relative. Line
  numbers for `backend/services/*` are those audited at `0713370`. The law-stack
  files have not changed between `0713370` and `fc896c2` (the base of this branch).
  This branch carries uncommitted fixes to some of them, which this document does
  not describe.
* `[NOTE file §n]` names the research-note section a statement comes from.
* Status words: VERIFIED, OBSERVED, README-ONLY, INFERRED, UNVERIFIED, as in the notes.
  Reference tests are always "(ran: not run)", because running them was forbidden.
* Nothing below reproduces the reference's code, regular expressions, tool
  descriptions, prompts, error wording or fixtures. Behaviour is described in this
  document's own words.

## 1. What was examined

| Item | Value | Evidence |
|---|---|---|
| Repository | `chrisryugj/korean-law-mcp`, read-only clone kept in the session scratchpad, outside the Waymaker repo | [NOTE ref-capabilities §0] |
| Commit | `0a8f08ef4f697e08047f76bfab8be435f5bdda5a`, 2026-10-15, release 4.15.9 | [LIVE git rev-parse / git log, 2026-10-19] VERIFIED; verifier re-read `.git/refs/heads/main` [NOTE ref-capabilities, verification pass, claim 1] |
| Package | `korean-law-mcp` 4.15.9, MIT, Node ≥ 20.19, TypeScript ESM, MCP SDK low-level server | [CODE ref:package.json:2-4] VERIFIED; [NOTE ref-ops-license §0] |
| History | Full clone: 473 commits on HEAD (586 across all refs), 32 tags from v2.1.6 (2026-03-24) to v4.15.9; first commit 2025-12-19; 23 author names | [NOTE ref-ops-license §0, §2.6, verification pass] VERIFIED |
| Size | 323 files under `src/`; 167 vitest files, about 1,200 test call sites; 17 legacy `test/*.cjs` scripts that no script or CI job runs | [NOTE ref-capabilities §0] VERIFIED by the original agent (the verifier could not re-run `find`, ENOSPC); test counts [NOTE ref-ops-license, verification pass, claim 13] VERIFIED |
| Tool surface | 99 tools registered; 10 advertised through `tools/list`; the rest reachable by name or through a meta-tool | [CODE ref:src/tool-registry.ts:88-742, 804-830; ref:src/lib/tool-profiles.ts:21-29] VERIFIED |
| Hosting | `server.json` advertises a remote streamable-HTTP endpoint. A caller without its own key is served with the operator's key under a rate limit | [DOC ref:server.json] VERIFIED; production host runs outside this repo [DOC ref:CLAUDE.md] README-ONLY |
| Licence notes | MIT for the author's own code; NOTICE names one module re-implemented from an unlicensed project; several files say they were ported from LexDiff, which is BSL 1.1 since 2026-04-13 | [DOC ref:NOTICE; ref:LICENSE] VERIFIED; details in [03 §3](03-reference-provenance.md) |

Method [NOTE ref-capabilities §0; ref-ops-license, method paragraph]: the research
agents read the READMEs, CHANGELOG, ROADMAP, `docs/`, the tool registry, the API
client and the tool and library modules named below, plus git metadata and the
lockfile. An adversarial verifier then re-opened every cited file at the cited
lines, recomputed the one similarity score by hand and repeated the key live calls.
Live behaviour was observed only through a hosted instance of the server whose tool
set matches 4.15.9. Its exact version is unknown, so live results are OBSERVED
(hosted, version unknown) and are not attributed to the examined commit ([03 §7](03-reference-provenance.md)).

## 2. Architecture in brief

The server is a single Node process. One static registry holds every tool as a
record of name, description, input schema and handler. A thin MCP layer advertises
a curated subset of ten. Two meta-tools let a model discover and run the others by
name, after re-validating their inputs against the target tool's schema. Hidden
tools can also be called directly, so the curated subset limits what is advertised,
not what can be called [NOTE ref-ops-license §1.1].

Every tool is a wrapper over the same two official endpoints, the DRF list/search
endpoint and the DRF body endpoint on law.go.kr. Different `target` values select
statutes, effective-date versions, history, old/new comparison, three-tier
comparison, annexes, administrative rules, ordinances, interpretations, decisions,
treaties and terminology. Annex files are fetched from the web and parsed by a
separate document-conversion dependency by the same author
[NOTE ref-capabilities §1, §2].

On top of the single-purpose tools sits a scenario layer that chains them:
applicable-law-at-a-date, a two-date diff, citation verification, subsequent-case
checks, ordinance monitoring, hierarchy views. Each chain composes retrieval with
local post-processing (filtering, pairing, excerpting, scoring) and returns prose.

Every response is **one Korean plain-text block**. It has no structured output
channel. Errors are text with bracketed labels plus an error flag, and the text
contains next-step instructions addressed to the calling model. A final gate masks
key-like values and truncates the text to 50,000 UTF-16 units
[CODE ref:src/tool-registry.ts:859-929; ref:src/lib/errors.ts:12-32] VERIFIED.

Around the tools sits a resilience layer: per-attempt and total deadlines, retries
(including on 404, because the authors measured transient 404 bursts from DRF), a
per-request attempt and byte budget shared across a JSON-RPC batch, cancellation
propagation, an in-process LRU cache with per-entry TTL, and a guard that refuses
to read an empty or HTML body as data. Transport is STDIO by default or stateless
streamable HTTP. HTTP mode refuses to boot on a public bind without an access token
[NOTE ref-ops-license §1.2-1.10].

Two things in the access path matter for policy. The client sends a hard-coded
desktop-browser User-Agent and a forged law.go.kr Referer, and on cloud IPs it
decodes and follows law.go.kr's JavaScript anti-bot challenge
[CODE ref:src/lib/fetch-with-retry.ts:88-107, 173-205; ref:src/lib/law-antibot.ts:1-14] VERIFIED.
Waymaker does neither, and must not start ([03 §6](03-reference-provenance.md)).

## 3. Capability tables

Relevance is judged for a Korean visa and status-of-stay information product. The
primary sources are the statute, 시행령, 시행규칙, their 별표, and 법무부 고시; case law
is secondary [NOTE ref-capabilities §3].

### 3.1 Statutory

| Capability | Described | Code evidence (own words) | Tests (ran: not run) | Limitations found | Live-observed? | Relevance |
|---|---|---|---|---|---|---|
| Statute search | Search returns IDs, abbreviations, rename and upcoming notes, repeal hints, fallbacks [DOC ref:README-EN.md] | Asks for a wide window, splits exact from partial hits after a current-first sort, tries alias and typo expansions on zero hits and drops expansions whose results do not mention the query, checks for upcoming versions in parallel, then walks a zero-hit ladder (upcoming → repealed → admin rule → ordinance) [CODE ref:src/tools/search.ts:37-160; ref:src/tools/search-hits.ts:41-95; ref:src/tools/search-fallbacks.ts:35-110] VERIFIED | ref:src/tools/search*.test.ts, ref:src/lib/law-search.test.ts | Upstream matching is LIKE in 가나다 order. The alias table has **no** immigration entries (0 hits for 출입국/외국인/재외동포/난민/국적/이민/고용허가). Upcoming notes capped at 5 | OBSERVED (call 1) | High |
| Statute text | Full text, with an optional reference date [DOC ref:docs/API.md] | A serial-only (MST) read uses `target=law`; a lineage ID or date uses `eflaw`; large laws without an article return a table of contents; truncation on article boundaries; header prints name, former name and both dates [CODE ref:src/lib/api-client.ts:165-215; ref:src/tools/law-text.ts:163-389] VERIFIED | law-text.*.test.ts | Header has no serial, 공포번호, lineage ID or source URL. **An MST-only "current" read returned the not-yet-effective 2027-09-16 text of 시행규칙 제73조 under the 2026-09-15 in-force header** (V7–V9) | OBSERVED (calls 2, 5; V7–V9) | High |
| Article selection | Article label or 6-digit code | Converts labels to codes, then filters units locally by article and branch number, because upstream can ignore the article parameter; a miss reports the valid range [CODE ref:src/tools/law-text.ts:55-64, 229-279] VERIFIED | jo-bounds.review3.test.ts, utils.test.ts | Article title printed twice | OBSERVED (call 2) | High |
| 항/호/목 | Precise sub-article reads (hidden tool) [DOC ref:docs/API.md] | Filters 항/호/목 locally because upstream ignores those parameters; re-attaches 목 to 호 by watching for the list to restart; reports missing units instead of blanking them [CODE ref:src/tools/article-detail.ts:28-210; ref:src/lib/article-parser.ts:23-104] VERIFIED | article-detail.test.ts, article-parser.test.ts | Current version only (no date); 목 ownership is a heuristic | Indirectly (call 6) | High: immigration rules cite e.g. "별표 1의2 … 가목", "제76조제2항제5호" |
| Identity resolution | Abbreviations resolved; label ↔ code [DOC ref:README-EN.md] | Name → lineage ID via exact current name, then former name, then prefix of the top hit (rejecting inputs longer than the name); serial → lineage ID via a tiny cached read; cache keys keep serial and lineage namespaces apart [CODE ref:src/lib/law-lineage.ts:33-95; ref:src/tools/law-text.ts:396-405] VERIFIED | law-lineage.test.ts, law-search*.test.ts | Alias data is general-purpose; the normaliser is a LexDiff-marked file ([03 §3.3](03-reference-provenance.md)) | OBSERVED (IDs in calls 1, 5, 7) | High |
| Current vs historical | Point-in-time via a reference date [DOC ref:docs/API.md] | Hits flagged current/history; a date that is not itself a version start is redirected to the version in force via the lineage, and the redirect is stated [CODE ref:src/tools/law-text.ts:423-474; ref:src/lib/law-lineage.ts:108-207] VERIFIED | historical-law.test.ts, law-lineage.test.ts | Lineage depends on upstream honouring the lineage filter (guarded); history fallback scrapes HTML by name; **annex-only staggered dates are invisible** (부칙 제936호 E-10 columns, 제1024호 F-6 columns) | OBSERVED (call 5, V5) | High |
| Promulgation vs effective date | Both dates shown | Search rows, upcoming notes and the applicable-law header keep 공포일, 공포번호 and 시행일 apart; a date-of-change listing exists [CODE ref:src/tools/search-hits.ts:89-95; ref:src/lib/upcoming-laws.ts:27-130; ref:src/tools/law-history.ts:21-60] VERIFIED | upcoming-laws.test.ts | Per-article 조문시행일자 used only by the two-date diff; 부칙 단서 dates must be read from text | OBSERVED (calls 1, 3, 5, 7) | High |
| Future-effective amendments | Upcoming-law detection | One upcoming query per search; classifies rename / amendment / new law; keeps "could not check" (null) distinct from "none" (empty) and caches failures for one minute [CODE ref:src/lib/upcoming-laws.ts:64-130] VERIFIED | upcoming-laws.test.ts | An upcoming slice can share the current serial (289833 → 2027-09-16), so a serial-only read is ambiguous | OBSERVED (calls 1, 7) | High |
| Renamed statutes | Lineage survives renames | Former-name lookup; applicable-law prints the name in force at the time; citation check flags a rename and checks the last version under the old name [CODE ref:src/tools/search.ts:137-147; ref:src/tools/verify-citations.ts:528-553] VERIFIED | law-lineage.test.ts, verify-citations.review3.test.ts | — | No | Medium |
| Repealed statutes | "Successor lookup for repealed statutes" [DOC ref:README-EN.md:3] | Statutes: repealed rows listed with serial and last effective date, plus advice to read the 부칙. Admin rules: successor names extracted from the abolition reason [CODE ref:src/lib/abolished-laws.ts:40-246] VERIFIED | abolished-laws.test.ts | **No successor extraction for statutes** (README overclaims) | No | Medium |
| 부칙 | Addenda newest first (4.15.8) | Reads the addenda of the fetched version, flattens and sorts them by promulgation date, normalises headers [CODE ref:src/tools/law-text.ts:191-216] VERIFIED | law-text.addenda.test.ts | All-or-nothing; subject to the 50k cut; zero-padded numbers in one tool and unpadded in another | OBSERVED (call 3: 72 addenda, V3) | High |
| Transitional provisions | Extracted "from every later amendment's addenda" [DOC ref:README-EN.md] | Keeps at most 6 addenda × 3 lines (≤ 250 chars), newest first, chosen by article mention or a keyword signal; appends fixed general-principle text; does not interpret [CODE ref:src/tools/applicable-law.ts:96-137, 284-374] VERIFIED | applicable-law*.test.ts | Silent cap: **the directly relevant 부칙 제1024호 제3조 was dropped** (it was 7th) | OBSERVED (call 7, V2) | High |
| Amendment history | Article and law history | Article history in 100-row pages (≤ 5 with an article), changes by date, lineage listing [CODE ref:src/tools/article-history.ts:47-170; ref:src/tools/law-history.ts:21-60] VERIFIED | article-history.test.ts | 500-version cap per article query | No | Medium |
| Old/new comparison | Old/new and two-date diff | Pairs old and new articles **by list position**, labels each pair with the first article number in its text, caps at 30 pairs; the two-date diff compares article snapshots and suppresses same-number comparison across a 전부개정 [CODE ref:src/tools/comparison.ts:23-117; ref:src/tools/scenarios/time-travel.ts:22-66] VERIFIED | time-travel*.test.ts | Position pairing can mislabel; **no annex diff** | No | Medium (immigration changes land mostly in 별표 5/5의2/1의2) |
| Annexes and forms | Annex files to Markdown, with a date [DOC ref:docs/API.md] | Lists annexes (100 per page, ≤ 5 pages, truncation warning), selects by number, sequence, query or delegating article, prefers the version's own file link, parses with the conversion dependency (OCR off); image-only PDF → link [CODE ref:src/lib/api-client.ts:321-392; ref:src/tools/annex.ts:42-420] VERIFIED | annex*.test.ts (13) | Success output has **no serial, version or URL**; the date option exists only for statutes; ARCHITECTURE.md is stale on PDF | OBSERVED (call 4: 별표 5의2 as a full table) | High: 별표 1/1의2/1의3, 5/5의2 |

### 3.2 Other resources

| Capability | Described | Code evidence | Tests (not run) | Limitations | Live? | Relevance |
|---|---|---|---|---|---|---|
| Administrative rules | Search, read, old/new, history, point-in-time, successor | Kind filter, per-ID issuance history, partial views, old/new; applicable-law falls back to admin-rule lineage [CODE ref:src/tools/admin-rule.ts:30-440; ref:src/lib/admin-rule-history.ts:62-160] VERIFIED | admin-rule*.test.ts | No annex date for admin rules | No | High (법무부 고시·훈령·예규) |
| Interpretations | 법령해석례 plus customs, NTS and labour first-level interpretations | One handler family; date range and sort [CODE ref:src/tools/interpretations.ts:21-140; ref:src/tools/customs-interpretations.ts:10-279] VERIFIED | interpretations.test.ts | Title search by default ("체류자격" → 3 hits); **no 법무부 feed wired**, though the official guide lists `mojCgmExpc` and `okaCgmExpc` [NOTE official-api §3] VERIFIED | OBSERVED (call 8, V6) | Medium–High |
| Precedents | Title/body search, exact case number, text, summaries | Exact number via local filter over a prefix match; body search; HTML and NTS-site fallbacks [CODE ref:src/tools/precedents.ts:122-580; ref:src/lib/case-citation.ts:166-181] VERIFIED | precedent*.test.ts (9) | law.go.kr coverage only; summaries are keyword frequency, not analysis | Partly (call 6) | Medium |
| 행정심판 | Appeal and special-appeal domains | List and body for `decc` and special targets [CODE ref:src/tools/admin-appeals.ts:21-120] VERIFIED | decision-domains.*.test.ts | — | No | Medium (e.g. refusals of 체류기간 연장) |
| 헌재 | Constitutional decisions | List and body [CODE ref:src/tools/constitutional-decisions.ts:27-130] VERIFIED | same | Citation check looks 헌재 numbers up among precedents only, so they will usually stay unconfirmed (INFERRED) | No | Low |
| Ordinances | Search, read, linkage, ordinance radar | Ordinance search and body, linkage targets, a monitor that compares parent-law dates [CODE ref:src/tools/ordinance*.ts; ref:src/tools/law-linkage.ts:92-185] VERIFIED | ordinance*.test.ts | — | No | Low |
| Terminology | Legal dictionary and knowledge-base relations | Term search and body, everyday-term mapping, term → article, related laws [CODE ref:src/tools/legal-terms.ts:17; ref:src/tools/knowledge-base.ts:87-458] VERIFIED | knowledge-base*.test.ts | — | No | Low–Medium (glossary) |
| Hierarchy and delegation | Three-tier view, system tree, "finds delegations with no implementing decree" [DOC ref:README-EN.md:307] | Three-tier comparison always returns the **current** comparison even for an old serial; the delegation scenario **states that it does not detect unimplemented delegations**, because the linkage target ignores the query [CODE ref:src/tools/three-tier.ts:25-40; ref:src/tools/scenarios/delegation.ts:11-21] VERIFIED | three-tier.citation.test.ts, law-tree.test.ts | README claim exceeds code; no point-in-time hierarchy | No | High for 법 → 영 → 규칙 → 별표 mapping; the missing-delegation feature: Not needed |

### 3.3 Verification

| Capability | Described | Code evidence | Tests (not run) | Limitations | Live? | Relevance |
|---|---|---|---|---|---|---|
| Citation extraction | Statute and case citations, 「」, interpunct, 같은 법 [DOC ref:README-EN.md v4.9.0] | Article pattern with optional branch, 항 and 호; the law name taken from a short window before the article without crossing the previous citation; 같은 법 inherits the previous law, not across a blank line; optional heading captured as a claim; case numbers via a shared case-code vocabulary [CODE ref:src/tools/verify-citations.ts:83-232; ref:src/lib/case-citation.ts:59-127] VERIFIED | verify-citations*.test.ts, case-citation*.test.ts | 목 and 별표/서식 not extracted; a 부칙 article and "영 제N조" are extracted without a law name and reported as name-extraction failures, never checked; "별표 5의2" and "별표 1의2 … 가목" not counted (6 citations counted from 8 references) | OBSERVED (call 6, V4) | High |
| Existence check | "Existence + content" [DOC ref:README-EN.md] | Resolves the law among current laws, fetches the article by serial, matches number and branch locally, checks 항 numbers; summary verdicts; cases looked up by number; future year ⇒ impossible; otherwise "unconfirmed ≠ absent"; caps of 15 (≤ 30) statute and 5 case citations, with skipped items counted [CODE ref:src/tools/verify-citations.ts:432-639] VERIFIED | verify-citations.budget.test.ts | **호 parsed but never checked** (a "제9호" was silently dropped); historical citations checked against the serial-only body, which can be future text (INFERRED from the same read path as V7); case relevance not checked (a made-up number existed in an unrelated case and passed) | OBSERVED (call 6, V4) | High |
| Content comparison | Catches "content hallucinations" [DOC ref:README-EN.md v4.6.0] | Only the **article heading** in parentheses is compared with the official heading: a long common substring, else character-bigram Jaccard ≥ 0.25; a short claim contained in the official heading matches outright [CODE ref:src/lib/citation-content-matcher.ts:31-34, 142-189] VERIFIED | citation-content-matcher.test.ts | No check of substance. Lenient: "(체류자격의 구분)" against the official "일반체류자격" was reported as a match (3 shared of 8 bigrams = 0.375, recomputed by hand) | OBSERVED (call 6, V4) | High, as a warning |
| Historical applicability | Applicable law at a date | Version in force at the date via the lineage, staggered-slice correction, 전부개정 warning, upcoming warning, then-vs-now article comparison, addenda excerpts [CODE ref:src/tools/applicable-law.ts:139-379] VERIFIED | applicable-law*.test.ts | Compares article text only: reported "unchanged" although the annexes the article delegates to changed after the date (부칙 제1024호, 제1054호, 제1086호 name later annex amendments); excerpt cap; fixed principle text is editorial legal content | OBSERVED (call 7, V2) | High |
| Subsequent-case check | "Korean Shepard's" | Body search for the case number, scan of up to 3 citing cases for overruling language, verdict tiers that refuse "OK" when scans failed [CODE ref:src/tools/cite-check.ts:56-239] VERIFIED | cite-check*.test.ts | Heuristic; the reference's own docs say absence of signals proves nothing | No | Low |
| Official-source links | External link builder (hidden) | Builds name-based, lineage-ID-based and tree-page links; nothing fetched or validated [CODE ref:src/tools/external-links.ts:28-254] VERIFIED | external-links.test.ts | Not version-pinned; text and annex success outputs carry no URL; decision links echo the upstream DRF link with the key masked and `&amp;` escaped, which is not a public permalink | OBSERVED (calls 2–5, 8, V6) | High need; this implementation Low |
| Missing-source handling | "No longer claims absence when merely unreachable" (v4.12.0) | Empty and HTML bodies rejected before parsing; on three single-record targets an empty 200 is confirmed once and then raised as a typed miss whose message says absence is unproven; a no-data label kept apart from not-found; null-vs-empty for auxiliary checks [CODE ref:src/lib/api-client.ts:96-131; ref:src/lib/upstream-miss.ts:1-107; ref:src/lib/errors.ts:12-160] VERIFIED | api-client.miss.test.ts, lookup-miss.test.ts | States are prose for a model, not types. Residual absence paths remain (R1–R4 in §3.4) | OBSERVED (call 6 ranges) | High (pattern) |
| Partial results | 45 s chain deadline; partial is not an error | Deadline race per branch with markers; applies to 3 of 8 research tasks; citation check marks skipped items and downgrades the verdict [CODE ref:src/tools/chain-deadline.ts:23-110; ref:src/tools/verify-citations.ts:593-611] VERIFIED | chain-deadline*.test.ts | No deadline on 5 of 8 tasks | No | High (pattern) |

### 3.4 Operational engineering

| Capability | Code evidence (own words) | Tests (not run) | Limitations | Relevance to Waymaker |
|---|---|---|---|---|
| Tool registration | One static array; per-call input validation; schema generated once from the validation library; the key property is stripped from advertised schemas but still accepted [CODE ref:src/tool-registry.ts:747-830] VERIFIED [NOTE ref-ops-license §1.1] | tool-registry.gate.test.ts | Advertised ≠ callable; 80 schema fields accept an API key as a tool argument, so a model can be led to pass a key that then lands in transcripts (risk INFERRED) | Low now (no MCP); if Waymaker ever exposes tools: credentials server-side only, advertised = callable |
| Transport | STDIO with stdout reserved; stateless streamable HTTP with a fresh server per POST; boot refused on a public bind without a token or an explicit override [CODE ref:src/server/http-server.ts:291-420; ref:src/server/http-config.ts:23-107] VERIFIED [NOTE §1.2] | http-config.test.ts, http-server.*.test.ts | The shipped Dockerfile binds publicly and so needs one of those settings (INFERRED) | Generic: fail closed at boot, parse numeric env strictly |
| Key management | Key from per-call argument → request context (headers or query) → env; output gate masks key parameters and any known key value; the gate was added after upstream links were found echoing the shared key [CODE ref:src/lib/api-client.ts:60-68; ref:src/lib/fetch-with-retry.ts:19-40; ref:src/lib/tool-output.ts] VERIFIED; incident README-ONLY [NOTE §1.3] | — | README recommends putting the personal key in the connector URL, which the code's own comments say leaks into proxy logs; a real key value once sat in a tracked file and history was not rewritten (metadata only) | Mask at the final output gate as well as at URL build (upstream bodies echo the key); never accept a key from users or query strings |
| Rate limiting | Per-IP fixed 60 s window counting only tool calls; hard cap per JSON-RPC batch; token bucket plus a 24 h cap for keyless callers (the cap is a fixed window although commented "rolling") [CODE ref:src/server/http-server.ts:174-289; ref:src/lib/rate-limit.ts:28-87] VERIFIED [NOTE §1.4] | rate-limit.test.ts | In-process only; nothing throttles outbound calls beyond inbound gates and the budget (INFERRED) | Count cost-bearing calls, cap batch amplification |
| Budgets and deadlines | One budget per outer request: 48 upstream attempts (retries and anti-bot hops count), 8 MiB per body, 24 MiB total; 30 s per attempt, 45 s per fetch, 20 s body-idle, 45 s per chain [CODE ref:src/lib/execution-limits.ts:21-146; ref:src/lib/fetch-with-retry.ts:74-86] VERIFIED [NOTE §1.5] | execution-limits.test.ts, fetch-deadline.test.ts | Defaults can be overridden by env | High as an idea (Waymaker's legal_evidence has no budget, 24 attempts measured offline) |
| Cancellation | Disconnect aborts a connection signal combined with each item's own signal; cancelled calls are re-thrown, not turned into results [CODE ref:src/lib/session-state.ts:19-72] VERIFIED [NOTE §1.6] | fetch-with-retry.cancel.test.ts | — | Medium |
| Error handling | Retries on 429/503/504 and DRF 404s with jittered backoff, Retry-After clamped to 30 s; a fatal-error re-throw at 28 auxiliary catch sites so budget or cancellation cannot become "0 results" [CODE ref:src/lib/fetch-with-retry.ts:74-130, 300-320; ref:src/lib/fatal-errors.ts:1-17] VERIFIED [NOTE §1.7] | api-client.*.test.ts | Residual paths where failure still reads as absence: R1 a failed "was it repealed?" search falls back to not-found (deliberate); R2 lineage failure → "repealed"; R3 a 200 XML envelope with an unexpected root parses as zero rows (INFERRED end to end); R4 one catch swallows even budget and cancel | High: secondary lookups that decide a status must propagate failure |
| Caching | LRU with per-entry TTL and bounded side caches; 1 h for "current" text by lineage ID, 24 h for serial- or date-pinned text; 60 s for searches whose auxiliary check failed; errors generally not cached; keys exclude the key [CODE ref:src/lib/cache.ts:12-121; ref:src/tools/law-text.ts:107-120, 397-412] VERIFIED [NOTE §1.8] | law-cache-ttl.test.ts | Per process; the "results do not vary by key" assumption fails for unsubscribed targets (mitigated by not caching errors, INFERRED) | Medium: short TTL for current, longer for pinned; never cache failure as "no result" |
| Input validation | Schema on every input; a recursive length pre-check before validation (100 / 50,000 / 2,000 chars) added after measured ReDoS-style stalls [CODE ref:src/tool-registry.ts:836-897; ref:src/lib/schemas.ts:11-37] VERIFIED; timings README-ONLY [NOTE §1.9] | schemas.test.ts | Unknown keys stripped rather than rejected (INFERRED) | Medium–High: length caps before any pattern matching on user text |
| Output size | Mask, then truncate at a safe boundary with a visible notice [CODE ref:src/lib/schemas.ts:53-170] VERIFIED [NOTE §1.10] | schemas.truncate.test.ts | — | Explicit caps with a visible marker |
| Dependency security | Pinned conversion and PDF deps; overrides for patched transitive versions; `npm ci --ignore-scripts`; SHA-pinned actions; audit only on publish; 4.15.9 on npm has no provenance attestation [CODE ref:package.json; ref:.github/workflows/*.yml] VERIFIED; [LIVE registry.npmjs.org, 2026-10-19] OBSERVED [NOTE §1.11, verification pass V1] | — | One mirror workflow uses an unpinned action | Generic hygiene |
| Testing method | vitest with an injected fake client or stubbed `fetch`, inline bodies shaped like recorded upstream replies; Node 20/22 matrix; no live job, no coverage gate [CODE ref:vitest.config.ts; ref:.github/workflows/ci.yml] VERIFIED [NOTE §1.12] | — | Live scripts exist but are not wired in | Same approach as Waymaker (injectable transport, offline CI). Waymaker keeps its own captured fixtures |

## 4. Where the README (and tool descriptions) claim more than the code

| Claim | What the code does | Status |
|---|---|---|
| Hallucination guard checks existence **and content** | Content means article-heading similarity only, at a 0.25 bigram-Jaccard floor; live false match | VERIFIED (code) + OBSERVED |
| Finds delegations whose implementing decrees were never made (README, and the hierarchy tool description) | The delegation scenario says it does not do this and tells the model not to conclude there are none [CODE ref:src/tools/scenarios/delegation.ts:11-21; ref:src/tool-registry.ts:628] | VERIFIED |
| Successor lookup for repealed statutes (README and the search tool description) | Only for administrative rules; statutes get a serial and read-the-부칙 advice [CODE ref:src/lib/abolished-laws.ts:87-110 vs 211-246; ref:src/tool-registry.ts:92]; CHANGELOG 4.10.0 is accurate | VERIFIED |
| Transitional provisions from **every** later amendment | At most 6 addenda × 3 lines, newest first, silent cap | VERIFIED + OBSERVED |
| Citation verification as a pipeline "gate" | 호, 목, 별표, 부칙 and in-statute shorthand pass through unchecked, without a failure mark | OBSERVED + INFERRED |
| Tool and domain counts | package.json says 9 tools, README 10; ARCHITECTURE says 98 and 99 in different places; 21 decision domains in code | VERIFIED (drift) |
| ARCHITECTURE: PDFs are not parsed | PDFs are parsed (OCR off); image-only PDFs fall back to a link | VERIFIED (stale doc) |
| ARCHITECTURE cites a performance document | The file does not exist | VERIFIED |
| ROADMAP "100% complete" at v1.3.0 with 29 tools | Stale by about three major versions | VERIFIED |
| 24 h article cache | 24 h only when serial or date pins the version, 1 h otherwise | VERIFIED |
| Keyless daily cap described as rolling | Fixed 24 h window from the first call after a reset | VERIFIED |
| Users should paste their key into the connector URL (README Q&A) | The server's own comments say query-string keys leak into proxy logs | VERIFIED |

Tool descriptions matter more than the README here, because the calling model reads
them [NOTE ref-capabilities, verification pass, omission 3].

## 5. Live observations (hosted instance, version unknown, 2026-10-19)

The original pass used its full budget of 8 calls. The verifier attempted 9 more.
The first of those returned only a "server isn't responding" error from the
connector, and the verifier disclosed the set as one call over the 8-call budget if
a failed attempt counts [NOTE ref-capabilities §5, verification pass].
Only public law names, public serial numbers and fabricated test citations were
sent. No user question or personal data was sent.

| # | Call | What it showed |
|---|---|---|
| 1 | Search "출입국관리법" | Act 001707 / MST 290729 (공포 2026-08-04, 시행 2026-10-02); 시행령 005256 / 290501 (2026-09-29 / 2026-10-02); 시행규칙 008494 / 289833 (2026-09-15); upcoming 시행규칙 slice 제1125호 effective 2027-09-16 **on the same MST** |
| 2 | Rule 제76조 | ① 별표 5 for 사증 and 사증발급인정서; ② 별표 5의2 for 체류자격외활동, 근무처, 체류자격 부여/변경, 연장 and 외국인등록. This is primary-law confirmation of Waymaker's visa-issuance versus stay split. No serial or URL in the header |
| 3, V3 | Rule 부칙 | 72 addenda, 제1125호 (2026-09-15) back to 제367호 (1993-04-01), not truncated. 제1024호 제3조 keeps the old attachment rules for applications filed earlier. Data oddity: 제1125호 제2조 repeats 제1103호 제2조 word for word (upstream error or real repeat: UNVERIFIED) |
| 4 | 별표 5의2 | HWP annex rendered as a full table; no serial, version or link |
| 5, V5 | Rule 제76조 at 2019-01-01 | Redirected to the version in force (시행 2018-09-21, 제936호, MST 204664). 2019-01-01 is not a version start, although 부칙 제936호 delays the E-10 annex columns to that date |
| 6, V4 | Citation check on made-up references | 제4항 out of range caught; heading "(체류자격의 구분)" accepted against "일반체류자격"; "제9호" dropped; "영 제12조" and a 부칙 article reported as name failures; 별표 references not counted; a made-up case number existed in an unrelated case and passed |
| 7, V2 | Applicable law for Rule 제76조 at 2022-03-01 | Version 시행 2022-02-07 (MST 240295); "unchanged versus current"; 6 excerpts, without the directly relevant 제1024호 제3조 |
| 8, V6 | Interpretations "체류자격" | 3 hits, each with a relative DRF link, key masked, `&amp;` separators |
| V7–V9 | Rule 제73조 without a date, at 2027-09-16 and at 2026-09-15 | **The undated read printed the in-force header (2026-09-15) above the 2027-09-16 text.** Only the explicit 2026-09-15 read returned the text actually in force |

Not observed (budget): administrative rules, precedent text, subsequent-case checks,
rename and repeal paths, annex reads by date.

## 6. Lessons for Waymaker

**Ideas worth re-implementing independently** (from the official API guide and
Waymaker's own needs, never from the reference's code; see [03 §5](03-reference-provenance.md)):

1. **Version identity everywhere.** A lineage ID plus (serial, effective date) is the
   right key for "which rule applied on the application date". V7–V9 show that a
   serial on its own is **not** a version: one 법무부령 can carry two effective dates
   [NOTE ref-capabilities §6.1, verification pass]. This is the largest gap on the
   Waymaker side: no `eflaw`, history or 부칙 handling at all [NOTE law-stack Q5–Q8].
2. **별표 are first-class sources.** For stay procedures the operative content sits in
   시행규칙 별표 5/5의2 and 시행령 별표 1/1의2/1의3. Annex amendments can take effect
   column by column (부칙 제936호, 제1024호). The reference's version selection cannot
   see such dates (INFERRED), Waymaker's backend has no versions at all, and WLIE
   does not yet model dates below the annex level
   [NOTE ref-capabilities §6.2, verification pass omission 4].
3. **Fail-closed, typed vocabulary.** "Not found", "could not check", "skipped (cap)",
   "partial", "repealed", "renamed" and "future-effective" must be types, not prose.
   This matches the repository rule "keep data intact → prevent misleading rendering →
   log for manual review" [NOTE ref-capabilities §6.3].
4. **부칙 as data, indexed per amended provision or annex column**, with duplicate
   provisions across addenda flagged for review (the 제1125호/제1103호 repeat), instead of
   keyword-sampled excerpts with a silent cap [NOTE ref-capabilities §6.4, omission 6].
5. **Local filtering when upstream ignores a parameter** (article, 항/호/목), and a
   guard that rejects empty or HTML bodies before parsing [NOTE ref-capabilities §1].
6. **Bounded work per request** (attempts, bytes, wall clock, cancellation), with
   secondary lookups that propagate failure instead of defaulting to the negative
   [NOTE ref-ops-license §1.5, §1.7].
7. **Mask at the last gate** as well as at URL build, because upstream bodies echo the
   key back [NOTE ref-ops-license §1.3].

**Patterns to avoid** [NOTE ref-capabilities §6, "What not to adopt"; ref-ops-license §1.13]:

* Similarity-threshold "content verification", and any verifier that lets 호, 목, 별표,
  부칙 or "영 제N조" citations through unchecked.
* Silent caps on transitional excerpts.
* Treating a serial-only read as "the rule in force today".
* Hard-coded legal-principle text and editorial warnings injected into tool output.
* Prose outputs that carry instructions to the model. Waymaker's evidence goes to the
  model as typed, quoted data ([07 §5](07-evidence-verification-design.md)).
* Browser impersonation, forged Referer, anti-bot decoding and web-scraping fallbacks.
* Routing Waymaker user questions to a third-party hosted server ([03 §7](03-reference-provenance.md)).

## 7. Comparison matrix (required)

Priority key:
**P0** = needed before any WLIE result may reach the `/api/ask` answer path (the
promotion criteria in [05 §3](05-legal-intelligence-architecture.md));
**P1** = needed to cover common immigration questions soon after;
**P2** = useful, not blocking;
**Not needed** = out of scope or prohibited.
Waymaker-side evidence is from [NOTE law-stack]. WLIE paths are under
`experiments/waymaker-ai/waymaker_ai/`. "Benchmark" means the `legal_verification`
and `temporal` suites (tasks `citation_verification` and
`temporal_version_selection`) scored by the runner ([12](12-evaluation-methodology.md)).
Scenario letters A–N are those of [07 §1](07-evidence-verification-design.md).

| # | Korean Law MCP capability | Existing Waymaker capability | Identified gap | Independent Waymaker design | Priority | Verification method |
|---|---|---|---|---|---|---|
| 1 | Statute search with alias/typo expansion and a zero-hit ladder | Three regimes: `/api/ask` planner with fixed anchors and whitespace-insensitive exact name match; research path through the ported `law_query_normalizer` + `search_laws_ranked`; a cloud fallback over 100-row title pages [CODE backend/services/law_grounding.py:161-187, 330-334; law_tools.py:786-869; law_cloud_fallback.py:140-301] | The fallback maps any phrase containing a core law name to that law's title rows (5/5 issue queries "ok", p10); the ladder lets the last error win (D5); the normaliser's provenance is unresolved ([03 §4](03-reference-provenance.md)) | `legal/identity.py`: a title resolves only by exact `compact()` match over official, former and short titles from the identity registry (`datasets/registry/law_identity_2026-10-19.json`); near matches go to `detail`, never become the identity ([07 §2](07-evidence-verification-design.md) invariant 3). Clean-room replacement of the ported normaliser in Mission 002 ([17](17-mission-002-plan.md)) | P0 | `tests/test_legal_identity.py`; benchmark scenario A (wrong-law substitution) through both WLIE and the existing-law baseline; similarity review of the Mission 002 replacement against the DO-NOT-TOUCH list ([03 §5.4](03-reference-provenance.md)) |
| 2 | Name → lineage ID, serial → lineage ID, separate cache namespaces | `source_id` prefers 법령ID; the detail fetch sends any all-digit value as `MST` (latent ID/MST mix-up, INFERRED) [CODE backend/services/evidence_ontology.py:282-285; law_tools.py:921-927] | No stable identity separate from the version | `SourceIdentity.stable_id` = 법령ID is the **only** identity; `SourceVersion.key` = (version_id, effective_date) ([06 §1](06-temporal-law-and-source-identity.md)) | P0 | `tests/test_contracts.py`, `test_legal_adapters.py`; the `verified_web` capture bundle (15 identities) re-checked against law.go.kr in Mission 002 |
| 3 | Text by serial or by date; local article filter | `lawService` `target=law` by MST/ID; reads only `조문내용`; no `조문여부` filter; 항/호 text dropped [CODE backend/services/law_tools.py:950-1025] (R5) | A heading unit can satisfy "verified"; 항-only rules lose their text | `LegalSourceAdapter.get_provision` returns `ProvisionText` with `paragraphs` and `items`; adapters never return heading units (`legal/adapters.py` guarantees) | P0 | `test_legal_adapters.py`; `evaluation/fake_drf.py` renders heading units and 항/호 nesting so the existing parser is measured on them; sanitized live captures replace shape assumptions in Mission 002 |
| 4 | Point-in-time via lineage; redirect to the version in force | None: no `efYd`, no history target, no version pinning (VERIFIED by grep) | Cannot say which version governs a date | `legal/temporal.py` `select_candidate_versions`: the caller picks the `AnchorKind`; the result is always `candidate_only`; ten warning rules ([06 §3](06-temporal-law-and-source-identity.md)). Mission 002 wires `eflaw`/`eflawjosub`, `lsHistory`, `lsJoHstInf` ([04](04-official-api-capability-matrix.md)) | P0 | `test_legal_temporal.py`; `temporal` suite incl. the real cases in [06 §4](06-temporal-law-and-source-identity.md) |
| 5 | Upcoming-version detection; serial-only read hazard (V7–V9) | `scheduled` lifecycle only in the research search; `/api/legal/laws/search` returns `lifecycleStatus: ""` (OBSERVED) | Pending versions invisible; nothing prevents not-yet-effective text being used as current | Version key carries the effective date; `future_version_pending` warning; L2 `future_not_yet_effective`; a serial-only read is never "in force today" ([07 §3 L2](07-evidence-verification-design.md)) | P0 | 시행규칙 제73조 case (289833 @ 2026-09-15 vs @ 2027-09-16) in the `temporal` suite; synthetic bundle with two versions under one version id (fictional law names) |
| 6 | 항/호/목 selection with local filtering | 항/호 discarded by the `/api/ask` citation parser; four unrelated citation pattern families [CODE backend/services/citation_verifier.py:7-40; statute_citation_guard.py:58-166; law_citation_guard.py:21-44] | 항/호/목 never checked against source | L3 checks each cited 항/호/목 against the provision structure and fails with `citation_not_found` when absent | P0 | `test_legal_verification.py`; scenario B (invented article or sub-unit) |
| 7 | Citation extraction (statute + case, 같은 법) | Same four families; no 같은 법; names ending in 법률 missed by the `/api/ask` parser | No shared parser; 별표, 목, 부칙, 법/영/규칙 shorthand unsupported | `legal/citations.py`: a readable component-by-component scanner (title by longest exact known-title match, 제N조[의M], heading, 항 or ①, 호, 가목, 별표 N의M, 별지 서식, 부칙, 법/영/규칙 relative to a context title, 같은 법/조) | P0 | `test_legal_citations.py`; benchmark claims with shorthand and annex references |
| 8 | Existence check with verdict summary and caps | "Verified" = a title-list hit; when set, the answer guard lets every article number through [CODE backend/services/citation_verifier.py:136; law_citation_guard.py:126-128] (R2); answer citations never checked against article text | One boolean for three different facts | L1 (identity) and L3 (citation) as separate layers; `not_found` only with `Coverage.COMPLETE`; each layer reports the worst outcome over all citations; unchecked units never pass ([07 §3](07-evidence-verification-design.md)) | P0 | `legal_verification` suite; invariant tests in `test_legal_verification.py` |
| 9 | Heading similarity as "content" check | `statute_citation_guard` title equality/containment, wired only into unified search with `evidence_available=False`, so every citation is `unverifiable` [CODE backend/paradiso_backend.py:8165-8166, 8305-8307] | No text correspondence on `/api/ask` | L4: exact `compact()` heading match and quoted-text containment in the attributed version, deliberately without a similarity threshold; L5 passes only on deterministic signals, otherwise `human_review_required` | P0 | Scenario C examples (right article, wrong content); a near-miss heading pair in the style of call 6, written with fictional law names, belongs in this class |
| 10 | Applicable law with addenda excerpts and fixed principle text | None | Transitional and application rules ignored | L6 `transitional_rule_unresolved` when a transitional or application addendum names the cited article or sets a filing-date rule; temporal warning `transitional_provisions_unreviewed`; WLIE never applies a transitional clause and injects no editorial legal text | P0 | Scenario F examples in both suites (4 at the time of writing); a capture-based case on the 부칙 제1024호 제3조 pattern (pending applications keep the earlier attachment rules) is a Mission 002 addition |
| 11 | Full 부칙 read, newest first | "부칙" appears nowhere in backend services or the JS law modules (VERIFIED) | No 부칙 retrieval at all | `LegalSourceAdapter.get_addenda` returns typed `Addendum` records (`kind`, `mentions`); Mission 002 reads them from the body endpoint and flags exact duplicates across addenda | P1 | `test_legal_adapters.py` (addenda coverage); Mission 002 live capture of the 시행규칙 addenda with sha256 |
| 12 | Renamed statutes via former names | None | Old names in user questions or manuals cannot resolve | `former_titles` on `SourceIdentity`; L1 resolves a former title exactly; a partial current-title index yields `historical_lookup_required`, not absence (scenario G) | P1 | Scenario G bundles (`title_index_coverage: partial`) |
| 13 | Repealed statutes (successor only for admin rules) | Ranked `repealed` state in the research path only | Repeal not modelled on the answer path | `is_repeal` versions; L1 `source_repealed`; temporal `source_repealed_before_anchor`; no successor guessing | P1 | Synthetic repeal fixtures in the `temporal` and `legal_verification` suites |
| 14 | Article and law history, changes by date | `check_source_updates.py` hashes local files only; law pins set by hand and already stale [NOTE sources-monitoring SRC-02] | No change detection for law | Extend the existing monitor: `lsHstInf` daily feed filtered to the identity watch-list; compare promulgation and effective dates; emit review tasks into the Knowledge Platform; never auto-publish ([05 §2 row H](05-legal-intelligence-architecture.md)) | P1 | Mission 002 offline tests on a captured daily feed; review-task creation tests |
| 15 | Annex listing and parsing, with dates for statutes | Vercel enforcement code extracts 별표 7 only [CODE lib/enforcement-law-grounding.js:168-191]; manuals carry the document lists | No versioned annex text for 별표 5/5의2/1의2 | Annex units are provisions (`unit_kind: "annex"`, key such as `별표5의2`) with a version key; a deferred date for a whole annex fits `provision_effective_dates`, and a transitional or application 부칙 that names the annex sends the claim to review (L6). **Column-level dates inside an annex (부칙 제936호 E-10란, 제1024호 F-6란) are not modelled yet**; that is an open Mission 002 design item. Mission 002 lists annexes through `licbyl` and converts files with Waymaker's existing subprocess converters, never with reference code | P1 | Annex units in the synthetic core bundle, exercised by `test_legal_citations.py` and `test_legal_verification.py` (no real annex is captured yet); Mission 002 capture of 별표 5의2 with URL, retrieved_at and sha256 |
| 16 | Administrative rules with history and point-in-time | `admrul` search exists but `/api/ask` never calls it [NOTE law-stack (a) #3] | 법무부 고시 have no identity or version | `SourceFamily.ADMINISTRATIVE_RULE` with `admRulId` as `stable_id`; same temporal model; 시행일 taken from the search row, not the frame page (the frame variable holds 발령일자) [NOTE law-identity §1, verifier correction] | P1 | Identity-registry checks; Mission 002 adapter tests |
| 17 | Interpretations (no MOJ feed wired) | Interpretation family is "unsupported" (target `None`) [CODE backend/services/precedent_sources.py:64-69] | No 법무부 1차 해석 | Mission 002 adapter for `mojCgmExpc` (and `okaCgmExpc` for F-4), trimmed with `fields`, typed `OFFICIAL_INTERPRETATION`: supporting evidence, never a legal obligation on its own [NOTE official-api §3, §8] | P1 | Fixture tests from the official guide's documented response fields |
| 18 | Precedents, 행정심판, 헌재 with fallbacks | Two precedent clients in one request; title search in Python, body search in JS; fan-out 11–12 calls offline [NOTE law-stack Q14, R10] | Duplicated, unbudgeted fan-out | Outside WLIE. One precedent client behind the extracted law client ([05 §2 row A](05-legal-intelligence-architecture.md)); `JUDICIAL_DECISION` and `ADMINISTRATIVE_APPEAL` are secondary families | P2 | Upstream call counts in the existing-law baseline before and after |
| 19 | Three-tier comparison and system tree | None | No 법 → 영 → 규칙 → 별표 mapping | Delegation edges stored as data from `lsDelegated`/`lsStmd` (Mission 002); no graph database ([05 §2 row D](05-legal-intelligence-architecture.md)) | P2 | Registry consistency tests |
| 20 | Unimplemented-delegation detection (claimed, not implemented) | — | — | Not built | Not needed | — |
| 21 | Old/new article diff | Manual edition diff tools only | No statutory diff | Not in WLIE; considered for change review after #14 | P2 | — |
| 22 | External link builder (unpinned) | Unversioned `/법령/<name>` links; on `/api/ask` the source URL is the sanitized DRF API URL; precedent links are DRF URLs without a key, which return an authentication-failure page with HTTP 200 (OBSERVED) [NOTE official-api §8.3] | Users get broken or unpinned links | Every version and provision carries a version-pinned `official_url` (`lsInfoP.do?lsiSeq=…&efYd=…`); `identity.py` checks the **parsed host** against `OFFICIAL_SOURCE_HOSTS` and rejects look-alikes | P0 | `test_legal_identity.py` host cases; every URL in the capture bundle is on `www.law.go.kr` |
| 23 | Typed misses kept apart from outages; null vs empty | Typed `error_type`s, but twelve paths (D1–D12) where a failure, or even a successful lookup, surfaces as absence; e.g. an empty 200 body becomes "no results" [CODE backend/services/law_tools.py:583-584] | Outages can be reported as "law not found" | `LookupStatus` (`unavailable_*`, `upstream_error`) and `Coverage`; `LayerOutcome.UNAVAILABLE` is never absence; bundles script faults (HTML, empty, malformed JSON/XML, 429, timeout, 500, official error) ([07 §2](07-evidence-verification-design.md) invariant 1) | P0 | Fault examples in the `legal_verification` suite; the same faults rendered by `fake_drf.py` through the existing backend parser |
| 24 | Per-request budget, deadlines, cancellation | Count cap 7/8 per `/api/ask`; 12 s statute budget; `legal_evidence` unbudgeted (24 attempts offline); synchronous I/O on the event loop [NOTE law-stack R3] | Unbounded latency and quota use | `LookupStatus.UNAVAILABLE_BUDGET`; adapters count calls (`calls == 1` per method); Mission 002: one request budget shared by all law stages (e.g. a context variable), worker threads for I/O, cancellation on disconnect | P1 | Adapter `call_counts`; Mission 002 tests with a counting fake transport |
| 25 | LRU + TTL cache; errors not cached | No statute cache; `legal_evidence` caches official-error bodies for 24 h; unbounded dicts [NOTE law-stack R9] | Cached failures can masquerade as data | Mission 002: cache parsed successes only; short typed negative TTL; bounded LRU; longer TTL for date-pinned versions than for "current"; credential fingerprint in the key | P1 | Unit tests that an error is never served from cache |
| 26 | Key masking at URL build and output gate | `_sanitize_url` by key name; no `OC=` seen live; OC resent over plain HTTP on a network failure; base URL host not checked [NOTE law-stack (f), R7] | Credential exposure in transit and to arbitrary hosts | Credentials stay server-side, never in tool arguments or user input; HTTPS only; host allowlist; `EvidencePackage.public_view()` keeps raw URLs and diagnostics out of public output ([15](15-security-and-deployment.md)) | P0 | Backend law-client tests; `test_legal_evidence_package.py` (public view) |
| 27 | Output cap with a visible notice | Law text appended to one flat prompt without a cap | Silent context growth | `EvidencePackage`: ≤ 12 items, ≤ 2,400 chars per item, ≤ 20,000 total; truncation recorded with the full-text hash ([07 §5](07-evidence-verification-design.md)) | P0 | `test_legal_evidence_package.py` |
| 28 | Retrieved law text treated as data (skill instruction) | One flat prompt; no marking of source text | Instruction-like text in sources could steer the model | `legal/injection.py` flags instruction-like text; package items carry `text_role = "quoted_source_data"`; a flag never changes a verification result | P0 | `test_legal_injection.py`; scenario N |
| 29 | Length caps before pattern matching | Normaliser runs regexes over user text [CODE backend/services/law_query_normalizer.py:131-148] | Untested worst-case input cost | Linear scanner in `citations.py`; Mission 002 adds an input length cap at the API boundary | P2 | Scanner tests with long and adversarial inputs |
| 30 | 99-tool registry, meta-tools, MCP transport | No MCP server | — | None now. A typed MCP surface for Hestia only after WLIE is in the backend and the gates pass ([05 §6](05-legal-intelligence-architecture.md)) | Not needed (now) | — |
| 31 | Browser User-Agent, forged Referer, anti-bot decoding | Honest UA [CODE backend/services/law_tools.py:137] | — | Keep; a challenge page is `unavailable`, never circumvented ([03 §6](03-reference-provenance.md)) | Not needed (prohibited) | Code review; grep in CI for browser UA strings in backend services (Mission 002) |

## 8. Features Waymaker does NOT need

| Feature | Reason |
|---|---|
| Local ordinances (자치법규), ordinance linkage and the ordinance radar | Ordinances do not govern 체류자격 or 사증 procedures. At most a 외국인주민 support ordinance is background, which does not justify a feature [NOTE ref-capabilities §3.2] |
| Broad general-purpose legal search, natural-language routing tables, the 99-tool surface and discovery/execution meta-tools | Waymaker's scope is a closed set of immigration identities (registry plus watch-list). A large tool surface widens the attack and maintenance surface, and advertised ≠ callable there [NOTE ref-ops-license §1.1] |
| Anti-bot access, browser impersonation, forged Referer, NTS web scraping | Policy, not only licence: Waymaker uses official APIs with an honest client and treats a block as `unavailable` ([03 §6](03-reference-provenance.md)) |
| Tax, customs, labour and other agency interpretation feeds, and their alias tables | Not immigration. The immigration-relevant feeds (`mojCgmExpc`, `okaCgmExpc`) are the ones the reference does not wire |
| Committee and special-tribunal decision domains (competition, privacy, labour relations, anti-corruption, insurance appeals and similar) | Not immigration. 행정심판 and 대법원 cases on 체류 matters stay secondary (P2) |
| Subsequent-case "Shepard's" analysis | Heuristic, law.go.kr coverage only, and the reference's own docs say a clean result proves nothing. Waymaker does not present case law as authority for answers |
| Precedent compaction, keyword summaries and keyword "relevance" | Keyword frequency is not legal analysis. Waymaker shows decisions as quoted evidence with identity, not as summaries |
| Unimplemented-delegation detection | The reference does not implement it either; Waymaker has no question type that needs it |
| Hard-coded legal-principle text and editorial strategy warnings in tool output | That is legal content Waymaker must not invent; warnings come from typed verification results |
| A hosted, keyless shared-key service model and its rate-limit tiers | Waymaker uses its own credential server-side. Sharing the operator key with anonymous users conflicts with the reference's own statement that a key is for its issuer only (INFERRED tension) [NOTE ref-ops-license §1.3] |
| Client setup wizard, CLI and natural-language router | Developer tooling for an MCP distribution; Waymaker is a web product |
| Institutional rules (school, public-institution rules) | Not a source for status-of-stay requirements |

## 9. Open questions carried forward

* Does an annex read by date pick the right column-level version when a 부칙 단서
  delays only part of an annex (부칙 제936호 E-10 columns, 2019-01-01)? Not observed
  [NOTE ref-capabilities §7].
* 서식 (별지 forms) were never retrieved, so form parsing quality is UNVERIFIED
  [NOTE ref-capabilities, verification pass].
* Hosted instance version and its data-retention and logging policy are unknown.
* Is 부칙 제1125호 제2조 a real repeat of 제1103호 제2조 or an upstream error? UNVERIFIED.
* The reference's measurement that an empty 200 on search endpoints means an outage
  (README-ONLY) is relevant to Waymaker's D6 path. Waymaker should decide this from
  its own sanitized captures, not from the reference's claim
  [NOTE ref-ops-license §1.7, §5].
* Licensing questions (LexDiff-derived files, the LexLink-derived module) are tracked
  in [03 §9](03-reference-provenance.md).
