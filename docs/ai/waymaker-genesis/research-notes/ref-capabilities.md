# korean-law-mcp capability study (Mission 001 "Waymaker Genesis")

Date: 2026-10-19. Author: research subagent. Scope: what the third-party reference project
korean-law-mcp actually does, measured against what an immigration-information product
(Visable / Waymaker) needs.

## 0. Provenance, method, evidence rules

| Item | Value | Evidence |
|---|---|---|
| Repo path | `scratchpad/ref/korean-law-mcp` (read-only clone, treated as untrusted data) | — |
| Commit | `0a8f08ef4f697e08047f76bfab8be435f5bdda5a`, 2026-10-15, "chore: 4.15.9 — labor administration decisions (#175)" | [LIVE `git rev-parse HEAD` / `git log -1`, 2026-10-19] VERIFIED |
| Package version | `korean-law-mcp` 4.15.9, MIT, `"type":"module"`, bin `korean-law-mcp` + `korean-law` | [CODE package.json:2-4] VERIFIED |
| server.json | name `io.github.chrisryugj/korean-law-mcp`, v4.15.9, remote streamable-http `https://mcp.gomdori.app/law`; optional `apikey` header, "without it the shared server key is used under a rate limit" | [DOC server.json] VERIFIED |
| Size | 323 files under `src/`, 167 `*.test.ts` (vitest, `src/**/*.test.ts`), 17 `test/*.cjs` scripts (several load `.env` / `LAW_OC` → live) | [LIVE `find`/`wc`, 2026-10-19] VERIFIED |
| Licence notes | NOTICE: MIT covers the author's code; statute text not copyrightable (저작권법 제7조); anti-bot module re-implements an approach from LexLink-ko-mcp, which "has no licence" — NOTICE itself says that part has no redistribution basis. Several files say they are ported from "LexDiff" (same author), whose licence is not stated in this repo. | [DOC NOTICE] VERIFIED |

Method: read README.md (skimmed, 1,181 lines), README-EN.md (full), ROADMAP.md, CHANGELOG.md
(headings + 4.15.x, 4.15.0, 4.10.0 entries), docs/API.md, docs/ARCHITECTURE.md, the
production-review docs, `src/tool-registry.ts`, `src/lib/tool-profiles.ts`, `src/lib/api-client.ts`
and the tool/lib modules named below. **No code from the reference was executed, installed or
built; none of its tests were run** (task rule). All test references below are therefore
"(ran: not run)". Paths below are relative to the repo root unless prefixed.

Live observation: 8 calls to the connected MCP server `mcp__693f13de-…` (a hosted instance whose
tool descriptions match 4.15.9: 21 decision domains including `moel`/`iaciac`/`eiac`). Exact
hosted version is unknown → those results are OBSERVED (hosted instance, version unknown). Only
public law names / fabricated test citations were sent; no personal data.

Tags: [CODE path:line], [TEST path (ran: not run)], [DOC path], [LIVE …]. Status: VERIFIED /
OBSERVED / README-ONLY / INFERRED / UNVERIFIED.

## 1. Architecture facts that matter for integration

* 99 internal tools registered in one array; only 10 are advertised through `tools/list`
  (`legal_research`, `legal_analysis`, `search_law`, `get_law_text`, `get_annexes`,
  `search_decisions`, `get_decision_text`, `ordinance_radar`, `discover_tools`, `execute_tool`);
  the rest are reachable through `execute_tool` or direct `tools/call`.
  [CODE src/lib/tool-profiles.ts:21; src/tool-registry.ts:803-826] VERIFIED.
  package.json says "9개 MCP 도구", README says 10 → doc drift. VERIFIED.
* Every tool returns **one Korean plain-text block** (`content[0].type="text"`), no
  `structuredContent`; errors are text with bracket labels (`[NOT_FOUND]`, `[UPSTREAM_NO_DATA]`, …)
  and `isError`. Output is masked for keys, then truncated to 50,000 UTF-16 chars.
  [CODE src/tool-registry.ts:864-929; src/lib/errors.ts:12-31] VERIFIED. A Waymaker consumer
  would have to parse prose, and the prose embeds next-step instructions addressed to an LLM.
* Upstream: only `https://www.law.go.kr/DRF/lawSearch.do` and `/DRF/lawService.do`
  (protocol switchable), plus web downloads for annex files (`flDownload.do`, `/BYL/...`) and
  `taxlaw.nts.go.kr` for NTS bodies. [CODE src/lib/law-url-config.ts; src/tools/annex.ts:298-308;
  src/tools/precedents.ts:324-349] VERIFIED.
* Resilience layer: 30 s timeout, retries on 404/429/503/504 (404 included because DRF emits
  transient 404 bursts), per-request budget of 48 upstream attempts, 8/24 MiB body caps, 45 s
  chain deadline. [CODE src/lib/api-client.ts:10-24; src/lib/execution-limits.ts; src/tools/chain-deadline.ts:23] VERIFIED.
* A `Referer: https://www.law.go.kr/` header is injected on law.go.kr hosts, and a module parses
  and follows law.go.kr's obfuscated JS anti-bot redirect on cloud IPs.
  [CODE src/lib/fetch-with-retry.ts:94-98,175,193; src/lib/law-antibot.ts:1-14,38,75] VERIFIED.
  **This is an anti-bot bypass; Waymaker must not copy or rely on it.**
  [corrected by verifier: also add that every request without its own User-Agent is sent with a
  hard-coded desktop-Chrome browser User-Agent string because, per the code comment, law.go.kr
  classifies Node's default UA as a bot (overridable by an env var) — [CODE src/lib/fetch-with-retry.ts:88-92,174]
  VERIFIED. NOTICE wording is more precise than "comes from": it says the anti-bot page *parsing
  approach* was re-implemented in TypeScript after LexLink-ko-mcp's client, that the upstream repo
  shows no licence, and that if any expression was copied there is no redistribution basis
  [DOC NOTICE:25-37] VERIFIED.]
* Caches: in-process LRU; search 1 h; `get_law_text` 24 h when MST/efYd pins the version,
  1 h for lawId-only "current" reads; lineage 1 h; failed "upcoming" checks 1 min.
  [CODE src/tools/law-text.ts:66-70; src/tools/search.ts:150-153] VERIFIED.
* Upstream quirks documented in code (useful facts about the public API, not verified by me):
  DRF reports failures as HTTP 200 (empty body / notice XML / permission HTML) depending on
  target×type; `eflaw` single-record lookup by MST alone started returning an HTML notice on
  2026-08-27 (#153), so MST-only reads go to `target=law`; `JO` and `HANG/HO/MOK` parameters can
  be ignored upstream; `lnkDep` ignores `query`; `licbyl` caps `display` at 100.
  [CODE src/lib/upstream-miss.ts:1-17; src/lib/api-client.ts:174-189; src/tools/article-detail.ts:42;
  src/tools/scenarios/delegation.ts:11-21; src/lib/api-client.ts:321-330] INFERRED (code comments
  claim measurements; I did not reproduce them).

## 2. Official open.law.go.kr API targets the code calls

Counted from string literals and dispatch tables in `src/` (excluding tests).
[CODE grep over src/, 2026-10-19] VERIFIED (presence in code); whether each target behaves as the
code assumes is UNVERIFIED except where §5 shows live behaviour.

| Area | `lawSearch.do` targets | `lawService.do` targets |
|---|---|---|
| Statutes (current) | `law` | `law` (MST-only body, incl. 부칙) |
| Statutes (effective-date / lineage / upcoming) | `eflaw` (with `nw` = 1 연혁 / 2 시행예정 / 3 현행, `LID` = 법령ID lineage, `display`, `page`) | `eflaw` (MST+efYd or ID) |
| History | `lsHistory` (requested as `type=HTML`, parsed from HTML), `lsJoHstInf` (article history), `lsHstInf` (laws changed on a date) | — |
| Comparison / hierarchy | — | `oldAndNew` (신구법), `thdCmp` (3단비교, knd 1 인용 / 2 위임), `lsStmd` (체계도) |
| Annexes / forms | `licbyl` (law), `ordinbyl` (ordinance), `admbyl` (admin rule) | annex units read from the `law`/`eflaw` body |
| Admin rules | `admrul`, `admrulOldAndNew` | `admrul`, `admrulOldAndNew` |
| Ordinances & linkage | `ordin`, `lnkLs`, `lnkLsOrdJo`, `lnkDep`, `lnkOrd` | `ordin` |
| Interpretations | `expc`, `kcsCgmExpc` (customs), `ntsCgmExpc` (search only), `moelCgmExpc` | `expc`, `kcsCgmExpc`, `moelCgmExpc` |
| Decisions | `prec` (`nb` exact case no., `search=2` body), `detc`, `decc`, `ttSpecialDecc`, `ftc`, `ppc`, `nlrc`, `acr`, `iaciac`, `eiac`, `adapSpecialDecc`, `acrSpecialDecc` | same set |
| Institutional rules | `school`, `public`, `pi` (admrul-shaped responses) | same |
| Treaties / English | `trty`, `elaw` | `trty`, `elaw` |
| Terms / knowledge base | `lstrm`, `dlytrm`, `lsRlt` | `lstrm`, `lstrmRlt`, `lstrmRltJo`, `dlytrmRlt` |
| Other | `lsAbrv` (abbreviations), `aiSearch` (지능형 검색) | — |

Notable for Waymaker: no Ministry of Justice-specific 1차 해석 target is wired (only
customs/NTS/MOEL). Whether the API offers one is UNVERIFIED.

## 3. Capability tables

Relevance key: High / Medium / Low / Not needed, judged for a Korean visa / status-of-stay
information product (statute + 시행령 + 시행규칙 + 별표 + 법무부 고시 are the primary sources;
litigation is secondary).

### 3.1 Statutory

| Capability | Described (README/docs) | Actual code evidence (own words) | Tests (ran: not run) | Limitations / gaps found | Live-verified? | Waymaker relevance |
|---|---|---|---|---|---|---|
| Statute search | `search_law` returns lawId/MST, abbreviations, rename/upcoming notes, repealed hints, fallbacks [DOC README-EN.md "Tool Structure"] | `searchLaw` asks `target=law` with a floor of 50 rows, splits exact vs partial matches after a current-first sort, retries alias/typo expansions on zero hits and discards expansions whose results don't mention the query, runs an `eflaw nw=2` upcoming check in parallel, then a zero-hit ladder (upcoming → repealed → admin rule → ordinance) [CODE src/tools/search.ts:37-160; src/tools/search-hits.ts:41-95; src/tools/search-fallbacks.ts:35-110] VERIFIED | src/tools/search.test.ts, search-upcoming.test.ts, search-fallbacks.test.ts, search-bulk.test.ts, src/lib/law-search.test.ts, search-normalizer.alias.test.ts | Upstream is LIKE + 가나다 order; alias table has **zero** immigration entries (grep for 출입국/외국인/재외동포/난민/국적/이민/고용허가 in search-normalizer/route-patterns/scenario-rules: 0 hits); upcoming notes capped at 5; result shared-cached 1 h | OBSERVED (call 1) | High |
| Statute text retrieval | `get_law_text` full text; efYd = reference date [DOC docs/API.md "조회"] | MST-only → `target=law` JSON, lawId or efYd → `eflaw`; >20 articles without `jo` returns a table of contents only; truncates on article boundaries; header = 법령명, 구 법령명, 공포일, 시행일 plus a KST "currency" label; appends a 부칙 count hint [CODE src/lib/api-client.ts:165-215; src/tools/law-text.ts:163-189,281-312,332-389] VERIFIED | src/tools/law-text.review.test.ts, law-text.efyd.test.ts, law-text.correction.test.ts, law-cache-ttl.test.ts | Header carries no MST/공포번호/법령ID and **no source URL**; per-article 조문시행일자 not shown; MST-only read of a split-enforcement promulgation can return its *last* slice (code comment measured MST 281865 → 2027-12-31) [CODE src/lib/api-client.ts:182-186] [corrected by verifier: now OBSERVED for an immigration rule — `get_law_text(mst=289833, jo=제73조)` without efYd printed header 시행일 20260915 with the "current version" note, but its body was identical to the efYd=20270916 read (가목 "삭제 <2026.9.15>"), while efYd=20260915 returned different in-force text (가목 present, different payment methods); 부칙 제1125호 제1조 delays 제73조 to one year after promulgation. So an MST-only "current" read can silently serve not-yet-in-force text under the in-force header — LIVE hosted get_law_text ×3, 2026-10-19, OBSERVED]; injects an editorial "strategy warning" for 민법 107–110 [CODE src/tools/law-text.ts:327] | OBSERVED (calls 2, 5) | High |
| Article retrieval | `jo="제38조"` or 6-digit JO code | Converts Korean article labels to JO codes; filters returned units locally by 조문번호+가지번호 because upstream may ignore `JO`; NOT_FOUND includes the article range [CODE src/tools/law-text.ts:55-64,229-279] VERIFIED | src/tools/jo-bounds.review3.test.ts, utils.test.ts, law-text.*.test.ts | Article title rendered twice (header + body line) — OBSERVED in call 2 | OBSERVED | High |
| 항/호/목 handling | "조항호목 단위 정밀 조회" (`get_article_detail`, not exposed) [DOC docs/API.md] | `get_article_detail` filters 항/호/목 locally (upstream ignores HANG/HO/MOK); 목 are re-attached to 호 by detecting resets to '가' and printed as an unassigned block with a notice when counts don't align; missing units are reported, not blanked [CODE src/tools/article-detail.ts:28-166,180-210; src/lib/article-parser.ts:23-104] VERIFIED | src/tools/article-detail.test.ts, src/lib/article-parser.test.ts | No `efYd` → current/MST only; 목 ownership is a heuristic; `verify_citations` checks 항 only (호 parsed but never checked, 목 not parsed) [CODE src/tools/verify-citations.ts:490-521] | OBSERVED indirectly (call 6: 제4항 caught; 제24조제9호 passed with 호 silently dropped) | High (immigration rules cite e.g. "영 별표 1의2 중 24. 거주(F-2)란의 가목", "제76조제2항제5호") |
| Law identifier resolution | Abbreviations auto-resolved; JO ↔ code [DOC README-EN.md "Features"] | Name → 법령ID: exact current name, then former name via `eflaw` search, then prefix of top hit (rejects longer-than-name inputs); MST → 법령ID via a tiny `target=law&JO=000100` read cached 24 h; cache keys keep MST and lawId namespaces apart [CODE src/lib/law-lineage.ts:33-95; src/tools/law-text.ts:396-405,66] VERIFIED | src/lib/law-lineage.test.ts, law-search.test.ts, law-search.memo.test.ts | Alias table general-purpose (labour, tax, privacy…), nothing for immigration statutes; LexDiff-ported normalizer is marked "do not modify" | OBSERVED (IDs returned in calls 1, 5, 7) | High |
| Current vs historical | Point-in-time via efYd, historical search [DOC docs/API.md "기타"] | Search hits flagged 현행/연혁 and sorted current-first; `get_law_text` with a non-effective efYd resolves the version in force via the lawId lineage and states the redirect; `search_historical_law`/`get_historical_law` use lineage with an `lsHistory` HTML fallback [CODE src/tools/search-hits.ts:60-95; src/tools/law-text.ts:423-474; src/lib/law-lineage.ts:108-207; src/lib/historical-utils.ts:79-100] VERIFIED | src/tools/historical-law.test.ts, src/lib/historical-utils*.test.ts, law-lineage.test.ts | Lineage depends on `eflaw` honouring `LID` (guarded: aborts if the filter looks ignored); fallback is name-based HTML scraping; annex-only staggered dates are not slices (see §5 call 5) | OBSERVED (call 5) | High |
| Promulgation vs effective date | Both dates shown; upcoming lists 공포번호/시행일 | Search rows show 공포일 + 시행일; upcoming notes show 공포번호, 공포일, all 시행일 of the same MST; `applicable_law` prints [시행][제N호, 공포일, 제개정구분](MST); `get_law_history(regDt)` lists changes on a date via `lsHstInf` [CODE src/tools/search-hits.ts:89-95; src/lib/upcoming-laws.ts:27-60,101-130; src/tools/applicable-law.ts:241-247; src/tools/law-history.ts:21-60] VERIFIED | src/lib/upcoming-laws.test.ts, search-upcoming.test.ts | Article-level 조문시행일자 only used by the time_travel diff [CODE src/tools/scenarios/time-travel-diff.ts:12-20]; 부칙 단서 dates must be read from 부칙 text | OBSERVED (calls 1, 3, 5, 7) | High |
| Future-effective amendments | "Upcoming-law detection" (v4.5.0) [DOC README-EN.md] | `eflaw nw=2 display=100` per query; classifies rename / amendment / not-yet-in-force new law; sorts by nearest date; "확인 못 함" (null) distinct from "없음" ([]) with a warning line and 1-min cache; `applicable_law` warns of future versions from the lineage [CODE src/lib/upcoming-laws.ts:64-130; src/tools/applicable-law.ts:278-282] VERIFIED | src/lib/upcoming-laws.test.ts, src/tools/search-upcoming.test.ts, search-bulk.test.ts | Upcoming slice can share the current MST (observed 289833 → 2027-09-16), so an MST-only read is ambiguous (INFERRED from code comment) | OBSERVED (calls 1, 7) | High |
| Renamed statutes | v4.15.0 lineage survives renames [DOC README-EN.md v4.15.0] | Former-name lookup in `search_law` when no exact hit; `applicable_law` prints 당시 법령명; `verify_citations` reports `[RENAMED]` and checks the last version under the old name [CODE src/tools/search.ts:137-147; src/tools/applicable-law.ts:241-253; src/tools/verify-citations.ts:528-553] VERIFIED | src/lib/law-lineage.test.ts, src/tools/applicable-law.review.test.ts, verify-citations.review3.test.ts | Not exercised live | No | Medium |
| Repealed statutes | "successor lookup for repealed statutes" [DOC README-EN.md line 3] | Statutes: `eflaw` rows whose latest revision is 폐지/타법폐지 → list with MST and last effective date, plus advice to read 부칙. Admin rules: abolition reason + successor names extracted from text. `get_law_text` after repeal points to the pre-repeal version; same-name re-enactments handled [CODE src/lib/abolished-laws.ts:40-110,134-246; src/tools/law-text.ts:439-446; src/lib/law-lineage.ts:151-175] VERIFIED | src/lib/abolished-laws.test.ts, src/lib/law-search.repealed.test.ts | **No successor extraction for statutes** — only for admin rules (README overclaims; CHANGELOG 4.10.0 is accurate) | No | Medium |
| Supplementary provisions (부칙) | `jo="부칙"` returns addenda newest first (4.15.8) [DOC CHANGELOG.md:13-17] | Reads `법령.부칙.부칙단위` of the fetched version, flattens text, sorts by 부칙공포일자 desc, normalises headers to `<제N호, YYYY.MM.DD>` [CODE src/tools/law-text.ts:191-216] VERIFIED | src/tools/law-text.addenda.test.ts | All-or-nothing (no single 부칙/article selection); subject to 50k truncation; `applicable_law` prints zero-padded numbers (제01125호) while `get_law_text` prints 제1125호 (OBSERVED inconsistency) | OBSERVED (call 3: 72 addenda for 시행규칙 MST 289833) | High |
| Transitional provisions | `applicable_law` "extracts transitional provisions (적용례·경과조치) from every later amendment's addenda" [DOC README-EN.md v4.3] | Reads 부칙 from the **current** version, keeps addenda of later versions + the applicable version, newest first, max 6 addenda × 3 lines (≤250 chars each), lines chosen by article mention then by a keyword signal list; explicitly does not interpret; appends fixed general-principle text (형법 제1조, 행정기본법 제14조) [CODE src/tools/applicable-law.ts:96-137,284,336-366,369-374] VERIFIED | src/tools/applicable-law.test.ts, applicable-law.staggered.test.ts | "every later amendment" is not true: hard cap of 6, newest first, no "N more" notice → **the most relevant 부칙 was dropped live** (§5 call 7) | OBSERVED (call 7) | High |
| Amendment history | `get_article_history`, `get_law_history`, `amendment_track` [DOC docs/API.md] | Article history via `lsJoHstInf` (100-row pages, up to 5 when `jo` given, with cap notice); law changes by date via `lsHstInf`; lineage listing for whole-law history [CODE src/tools/article-history.ts:47-170; src/tools/law-history.ts:21-60] VERIFIED | src/tools/article-history.test.ts, history-review.test.ts, historical-law.test.ts | 500-version cap per article query; not exercised live | No | Medium |
| Article-level comparison (신구법) | `compare_old_new`, time_travel diff [DOC docs/API.md] | `oldAndNew` for one MST (optionally 공포일자/공포번호): pairs old/new articles **by list index**, labels each pair with the first article number found in its text, caps at 30 pairs, shows promulgation dates only [CODE src/tools/comparison.ts:23-117]. time_travel picks versions for two dates and diffs article snapshots (+/−/△), suppressing same-number comparison across 전부개정 [CODE src/tools/scenarios/time-travel.ts:22-66] VERIFIED | src/tools/scenarios/time-travel*.test.ts (5 files) | Index pairing/label regex can mislabel; no annex diff anywhere; admin rule old/new via `admrulOldAndNew` | No | Medium (immigration changes mostly land in 별표 5/5의2/1의2) |
| Annexes and forms (별표/서식) | `get_annexes`: HWPX/HWP/PDF/XLSX/DOCX → Markdown, `date` for version in force [DOC README-EN.md; docs/API.md `get_annexes`] | Lists via `licbyl`/`ordinbyl`/`admbyl` (100/page, max 5 pages, truncation warning), selects by number/bylSeq/query/delegating article, prefers the canonical file link from the version's own annex units, downloads and parses with kordoc 4.18.2 (OCR off); image-only PDF → link; `date` picks the lineage slice [CODE src/lib/api-client.ts:321-392; src/tools/annex.ts:42-420; src/tools/annex-history.ts:30-60; src/lib/annex-file-parser.ts:4-33] VERIFIED | src/tools/annex*.test.ts (13 files), src/lib/annex-*.test.ts | Success output has **no MST/version/source URL**; `date` only for statutes (not admin rules/ordinances); HWP layout fidelity depends on kordoc; ARCHITECTURE.md still says PDF is unparsed (stale) | OBSERVED (call 4: 별표 5의2 as a full HTML table) | High (체류자격 별표 1/1의2/1의3, 첨부서류 별표 5/5의2) |

### 3.2 Other resources

| Capability | Described | Actual code evidence | Tests (not run) | Limitations / gaps | Live? | Waymaker relevance |
|---|---|---|---|---|---|---|
| Administrative rules (행정규칙) | search/get/old-new, history, point-in-time, repeal successor [DOC docs/API.md] | `admrul` search with kind filter and optional per-ID issuance history; `get_admin_rule` partial views (jo/chapter/keyword/page, NFTC section numbers), image-table warning; `admrulOldAndNew`; `applicable_law` falls back to admin-rule lineage when the name isn't a statute [CODE src/tools/admin-rule.ts:30-440; src/lib/admin-rule-history.ts:62-160; src/tools/applicable-admin-rule.ts:45] VERIFIED | src/tools/admin-rule.test.ts (29 cases), admin-rule.current-state.test.ts, src/lib/admin-rule-*.test.ts | Annex `date` unsupported for admin rules; not exercised live | No | High (법무부 고시·훈령·예규) |
| Administrative interpretations (법령해석례) | `expc` + customs/NTS/MOEL first-level interpretations | `expc` search with date range sent as `explYd`, sort; detail via `lawService`; CgmExpc family shares one handler [CODE src/tools/interpretations.ts:21-140; src/tools/customs-interpretations.ts:10-279] VERIFIED | src/tools/interpretations.test.ts | Default search is title-based (live: "체류자격" → 3 hits); no MOJ-specific source; result link is a key-bearing DRF path, masked | OBSERVED (call 8) | Medium |
| Judicial precedents | search (title / body / both), exact case no., full text, summaries | `prec` with `nb` exact match, `search=2` body search, compact rendering, HTML and taxlaw fallbacks, 20-record parsed cache [CODE src/tools/precedents.ts:122-580; src/tools/precedent-search-core.ts] VERIFIED | src/tools/precedent*.test.ts (9), test/test-precedent-*.cjs | Coverage is what law.go.kr carries (mostly Supreme Court), stated in output; summaries/keywords are keyword-frequency, not legal analysis | Partly (case existence via call 6) | Medium |
| Administrative appeal decisions (행정심판) | `admin_appeal` domain | `decc` search/detail; special appeals `acrSpecialDecc`, `adapSpecialDecc` [CODE src/tools/admin-appeals.ts:21-120; src/tools/special-admin-appeals.ts:135-163] VERIFIED | src/tools/decision-domains.*.test.ts | Not exercised live | No | Medium (체류기간 연장 불허 등 취소재결) |
| Constitutional decisions | `constitutional` domain | `detc` search/detail [CODE src/tools/constitutional-decisions.ts:27-130] VERIFIED | decision-domains tests | `verify_citations` checks 헌재 numbers against `prec` only (INFERRED: they will usually come back "미확인") [CODE src/lib/case-citation.ts:155-190] | No | Low |
| Local ordinances (자치법규) | search/get, linkage, `ordinance_radar` | `ordin` search/detail with JO; linkage via `lnk*`; radar parses an ordinance's Article 1 for parent laws and compares effective dates [CODE src/tools/ordinance.ts:25; src/tools/ordinance-search.ts:31; src/tools/law-linkage.ts:92-185; src/tools/ordinance-radar.ts] VERIFIED | src/tools/ordinance*.test.ts, test/test-ordinance.cjs | Not exercised live | No | Low (외국인주민 지원 조례 at most) |
| Official legal terminology | `lstrm` dictionary + KB relations | `lstrm` search/detail, everyday-term mapping (`dlytrm`, `dlytrmRlt`, `lstrmRlt`), term→article (`lstrmRltJo`), related laws (`lsRlt`) [CODE src/tools/legal-terms.ts:17; src/tools/knowledge-base.ts:87-458] VERIFIED | src/tools/knowledge-base*.test.ts | — | No | Low–Medium (glossary of 사증·체류·등록) |
| Hierarchy & delegation (위임/체계도) | 3-tier view, system tree, "finds delegations whose decrees were never made" [DOC README-EN.md "Smart Scenarios"; README.md:493-498] | `thdCmp` 3-tier (위임/인용) rendered and cached 1 h — code notes it always returns the **current** comparison even for an old MST; `lsStmd` tree uses both XML and JSON calls; delegation scenario **explicitly does not detect unimplemented delegations** because `lnkDep` ignores `query` [CODE src/tools/three-tier.ts:25-40; src/tools/law-system-tree.ts:17-60; src/tools/scenarios/delegation.ts:11-21] VERIFIED | src/tools/three-tier.citation.test.ts, law-tree.test.ts | README claim exceeds code; no point-in-time hierarchy; 관세법 3-tier body ≈1.98 MB (comment) | No | High for 법→영→규칙→별표 mapping; the "missing delegation" feature: Not needed |

### 3.3 Verification

| Capability | Described | Actual code evidence | Tests (not run) | Limitations / gaps | Live? | Waymaker relevance |
|---|---|---|---|---|---|---|
| Citation extraction | statute + case citations; 「」, interpunct, 같은 법 anaphora (v4.9.0) [DOC README-EN.md v4.9.0] | Article pattern 제N조(의M)(제K항)(제L호); law name taken from ≤30 chars before the article (never crossing the previous citation), closing brackets stripped, stopwords removed, leading words peeled off as candidates, suffix-only candidates rejected, 같은 법/동법 inherits the previous law but not across a blank line; optional "(제목)" after the article captured as a claim; case numbers via a shared case-code vocabulary incl. 헌재 codes, serial ≤8 digits [CODE src/tools/verify-citations.ts:83-232; src/lib/case-citation.ts:59-127] VERIFIED | src/tools/verify-citations.test.ts (25), verify-citations.review3/production.test.ts, src/lib/case-citation*.test.ts | Not extracted: 목, 별표/서식 (OBSERVED: ignored in call 6), 부칙 articles; in-statute shorthand "영 제N조" / "이 규칙 제N조" cannot yield a law name (INFERRED: suffix list lacks bare 영) — that shorthand is pervasive in 출입국관리법 시행규칙 [corrected by verifier: 부칙 articles are not silently ignored — the bare "제N조" after "…시행규칙 부칙" is extracted, but no law name can be attached, so it is reported "⚠ (법령명 미지정) 제3조 — 법령명 추출 실패" and never checked; "영 제12조" behaves the same way (now OBSERVED, not only INFERRED). 별표 5의2 and "별표 1의2 … 가목" were again not counted (6 statute citations from 8 references). LIVE hosted verify_citations, 2026-10-19] | OBSERVED (call 6) | High |
| Citation existence checks | "existence + content", ✗ ranges [DOC README-EN.md v3.5] | Resolve law among **current** laws (repealed/renamed branches), fetch the article JSON by MST, match number+branch locally, check 항 numbers (circled digits handled); summary markers VERIFIED / PARTIAL_VERIFIED / REPEALED_REFERENCE / HALLUCINATION_DETECTED and `isError` on failure; cases: `prec nb=` exact match [corrected by verifier: upstream `nb=` is a forward/prefix match per the code comment; the code queries `nb=` with display 10 and keeps only rows whose 사건번호 field contains the exact number, so exactness is enforced locally — CODE src/lib/case-citation.ts:166-181], future year ⇒ impossible, otherwise "미확인 ≠ 부존재"; caps 15 (≤30) statute and 5 case citations, skipped ones counted [CODE src/tools/verify-citations.ts:432-526,555-639; src/lib/case-citation.ts:155-222] VERIFIED | same + verify-citations.budget.test.ts | 호 not checked; historical citations ("구 …법") checked against current text (INFERRED) [corrected by verifier: "current" here means the MST-only `target=law` body of the current search hit; for a promulgation with a pending staggered slice that body can be the future text (see verifier note in "Statute text retrieval" row), so an article could be checked against not-yet-in-force wording — INFERRED from CODE src/tools/verify-citations.ts:471 using the same request shape as the observed get_law_text read]; case relevance not checked (call 6: a made-up number happened to exist, in an unrelated price-order case, and passed) | OBSERVED (call 6) | High |
| Citation content comparison | "content hallucinations like 민법 제750조(계약해제)" [DOC README-EN.md v4.6.0] | Only the **article title** in parentheses is compared to the official title: normalised ≥30-char common substring, else character-bigram Jaccard ≥ 0.25 [CODE src/lib/citation-content-matcher.ts:31-34,142; src/tools/verify-citations.ts:494-500] VERIFIED | src/lib/citation-content-matcher.test.ts | No check of substantive claims; lenient: "제12조(체류자격의 구분)" vs actual "일반체류자격" reported "제목 일치" (bigrams 3/8 = 0.375) | OBSERVED (call 6) | High (as a warning: do not treat as content verification) |
| Historical applicability | `applicable_law` (v4.3, v4.15.0) | Lineage-based version in force at the date, staggered-slice correction, 전부개정 warning, prior same-name law, admin-rule lineage, upcoming warning, article then-vs-now comparison, addenda excerpts [CODE src/tools/applicable-law.ts:139-379] VERIFIED | applicable-law*.test.ts, time-travel*.test.ts | Compares article text only: "✅ 동일" although the annex it delegates to changed (call 7); excerpt cap; fixed principle text is editorial legal content | OBSERVED (call 7) | High |
| Subsequent-case analysis | `cite_check` "Korean Shepard's" [DOC README-EN.md v4.3] | Body search for the case number (50), en-banc-first deep scan of ≤3 citing cases for overruling language, alias tracking, verdict tiers that refuse "OK" when scans failed [CODE src/tools/cite-check.ts:56-239] VERIFIED | src/tools/cite-check*.test.ts | Heuristic, law.go.kr coverage only; docs say absence of signals proves nothing [DOC docs/PRODUCTION-REVIEW-2026-10-02.md:61-65] | No | Low |
| Official-source URL generation | `get_external_links` [DOC docs/API.md] | Builds law.go.kr name-based URLs (`/법령/{name}/{jo}`), `lsInfoP.do?lsId=`, `lsStmdInfoP.do?lsiSeq=MST`, `precInfoP.do`, `expcInfoP.do`, plus generic court/ELIS homepages; no fetch/validation [CODE src/tools/external-links.ts:28-254] VERIFIED | src/tools/external-links.test.ts | Not version-pinned; not exposed; law-text/annex success outputs carry no URL (OBSERVED calls 2–5); decision lists echo the upstream DRF 상세링크 with `OC=***` and HTML-escaped `&amp;` (OBSERVED call 8) — not a public permalink | OBSERVED (indirect) | High (need) / Low (this implementation) |
| Missing-source handling | "no longer claims a record is absent when it is merely unreachable" (v4.12.0) | Empty/HTML bodies rejected before parsing; 200-with-empty-body treated as a miss only for `prec`/`thdCmp`/`lsStmd` after one confirmation; `[NOT_FOUND]` messages carry "do not guess" text and re-query hints; null-vs-empty distinction for auxiliary checks; annex list truncation warnings [CODE src/lib/api-client.ts:96-131; src/lib/upstream-miss.ts:1-60; src/lib/upcoming-laws.ts:64-90; src/tools/annex.ts:401-411] VERIFIED | src/lib/api-client.miss.test.ts, api-client.htmlguard.test.ts, src/tools/lookup-miss.test.ts, precedent-miss.test.ts | Messages are prose for an LLM, not typed states | OBSERVED (call 6 NOT_FOUND ranges) | High (pattern to emulate) |
| Partial-results handling | 45 s chain deadline, partial result not an error (v4.12.0) | Deadline race per branch with markers and a closing notice; applies to 3 of 8 research tasks; verify_citations marks skipped (⊘) items and downgrades to PARTIAL; per-request attempt/body budgets; truncation notices [CODE src/tools/chain-deadline.ts:23-110; src/tools/verify-citations.ts:593-611; docs/ARCHITECTURE.md "Pattern 7"] VERIFIED | src/tools/chain-deadline*.test.ts, chains.deadline.test.ts, verify-citations.budget.test.ts, src/lib/execution-limits.test.ts | Not exercised live; deadline absent for 5 of 8 tasks | No | High (pattern) |

## 4. Where README claims exceed the code

| Claim | Reality | Status |
|---|---|---|
| "LLM hallucination guard … existence **+ content**" (README-EN line 3, README.md line 3) | Content = article-title similarity only, threshold 0.25 bigram Jaccard; live false "match" | VERIFIED (code) + OBSERVED |
| "Finds delegated provisions where implementing decrees haven't been created yet" (README-EN.md:307; README.md:493-498) | Delegation scenario states it does **not** do this and tells the LLM not to conclude "no unimplemented delegations" [CODE src/tools/scenarios/delegation.ts:11-21] | VERIFIED |
| "successor lookup for repealed statutes" / "폐지 법령 후속 규정 안내 … 법령·행정규칙 양쪽" (README.md:226-228) | Successor names extracted only for admin rules; statutes get MST + read-the-부칙 advice [CODE src/lib/abolished-laws.ts:87-110 vs 211-246] | VERIFIED |
| `applicable_law` extracts transitional provisions "from every later amendment's addenda" | Max 6 addenda × 3 lines, newest first, silent cap | VERIFIED + OBSERVED |
| "Verified on 100% of …" style counts: "42 APIs → 10 tools", "17/18 decision domains" | Code has 21 domains; package.json says 9 tools; ARCHITECTURE says 98/99 tools in different places | VERIFIED (drift) |
| ARCHITECTURE "PDF: 파싱 불가 → 링크 반환" | PDF parsed by kordoc (OCR off); image-only PDFs fall back to link | VERIFIED (stale doc) |
| ARCHITECTURE references `docs/UPSTREAM-PERF.md` | File does not exist | VERIFIED |
| ROADMAP "로드맵 100% 완료" at v1.3.0, 29 tools | Stale by ~3 major versions | VERIFIED |
| README-EN "Caching — 1-hour search cache, 24-hour article cache" | Article cache is 24 h only when MST/efYd pins the version; 1 h otherwise | VERIFIED |
| `verify_citations` described as a pipeline "gate" | Skips 호/목/별표/부칙 and in-statute shorthand without a ✗; a gate that passes unchecked units | OBSERVED + INFERRED |

## 5. Live observation log (hosted instance, version unknown; 2026-10-19; 8/8 calls used)

| # | Call (public inputs only) | Result | What it shows |
|---|---|---|---|
| 1 | `search_law(query="출입국관리법", display=10)` | 3 hits: 출입국관리법 [현행] 법령ID 001707, MST 290729, 공포 20260804 / 시행 20261002 (법률); 시행령 005256 / MST 290501 / 공포 20260929 / 시행 20261002; 시행규칙 008494 / MST 289833 / 공포·시행 20260915; note: 시행규칙 일부개정 공포 2026-09-15 제01125호, 시행 2027-09-16, same MST 289833 | Identifiers + both dates + upcoming slice sharing the current MST. OBSERVED |
| 2 | `get_law_text(mst="289833", jo="제76조")` | Article text with 3 항 and 호; ① → 별표 5 for 사증·사증발급인정서, ② → 별표 5의2 for 체류자격외활동·근무처·체류자격부여/변경·연장·외국인등록; header 공포일/시행일 + currency note; title printed twice; no MST/URL in header | Primary-law confirmation of Paradiso's 사증 vs 체류 split. OBSERVED |
| 3 | `get_law_text(mst="289833", jo="부칙")` | "부칙 72건 (최근 공포부터)", from `<제1125호, 2026.09.15>` back to `<제367호, 1993.04.01>`; includes 부칙 제1024호 제3조 (pending applications keep prior 별표 5/5의2 attachments) and 제936호 (별표 5/5의2 E-10란 effective 2019.1.1) | Full 부칙 access works; very useful for transitional rules. OBSERVED |
| 4 | `get_annexes(lawName="출입국관리법 시행규칙", annexNo="5의2")` | Title "체류자격 외 활동허가 신청 등 첨부서류(제76조제2항 관련)", "(파일 형식: HWP)", amendment stamp `<개정 2024. 12. 24.>`, then the whole table as HTML (공통사항, A-1 … H-2) | HWP annex → structured table works; output lacks MST/version/link. OBSERVED |
| 5 | `get_law_text(mst="289833", jo="제76조", efYd="20190101")` | Redirect note: version in force = 시행 2018.09.21, 공포 제936호 일부개정, MST 204664; warning that it may not be current | Point-in-time works with version identifiers. 2019-01-01 is not a lineage slice although 부칙 제936호 delays the E-10 annex columns to that date → annex-only staggered dates are invisible to version selection (INFERRED) |
| 6 | `legal_analysis(mode="verify_citations", text=<fabricated mix>)` | `[HALLUCINATION_DETECTED]`, 6 statute citations: ✓ 시행규칙 제76조 제2항; ✗ 제76조 제4항 (max 제3항); ✓ 법 제10조의2(일반체류자격) title match; ✓ 같은 법 시행령 제12조 "제목 일치" although I wrote "(체류자격의 구분)" and the official title is 일반체류자격; ✓ 법 제24조 (my "제9호" silently dropped); ✗ 제999조 (range 1–106); "별표 5의2" not extracted; cases: ✓ 2016두64975 (exists: 대법원 2019.01.31, unrelated subject), ✗ 2099두12345 (future year) | Anaphora works; 항 checked; 호 and 별표 unchecked; title matcher lenient. OBSERVED |
| 7 | `legal_analysis(mode="applicable_law", lawName="출입국관리법 시행규칙", date="2022-03-01", jo="제76조")` | Version 시행 2022.02.07, 제1022호 타법개정, MST 240295; 21 later versions; upcoming 2027.09.16 warning; article text; "현행과 비교: ✅ 동일"; 6 addenda excerpts (제1125, 1103, 1086, 1054, 1042, 1032호); fixed principles block | The directly relevant 부칙 제1024호(2022.04.12) 제3조 — which names 제76조 and 별표 5/5의2 — was **not** excerpted; "동일" hides that 별표 5/5의2 changed after the date. OBSERVED |
| 8 | `search_decisions(domain="interpretation", query="체류자격", display=5)` | 3 results with ID, 해석례번호, 회신일자, 해석기관 and a relative DRF link `…OC=***&amp;target=expc&amp;ID=…&amp;type=HTML…` | Key masking works; link is not a usable public citation; title search only. OBSERVED |

Not observed (budget): admin rules, precedents text, cite_check, renamed/repealed paths, annex `date`.

## 6. Implications for Waymaker (immigration information)

What is worth learning from (patterns, re-implemented independently, no code copying):

1. **Version identity everywhere.** The lawId lineage via `eflaw` + `LID` (all effective slices
   across renames) and "MST + efYd" pinning are the right primitives for "which rule applied on
   the application date". [CODE src/lib/law-lineage.ts:108-147] Waymaker's own client on
   origin/main calls `law`, `admrul`, `lstrm`, `prec` targets only (no `eflaw`, `lsHistory`,
   `licbyl`, `oldAndNew`, 부칙 handling) [CODE /Users/seonjaekim/dev/Visable-genesis/backend/services/law_tools.py:904-1076; precedent_sources.py:60] VERIFIED (grep) — this is the largest capability gap.
2. **별표 as first-class sources.** For 체류 procedures the operative content is in 시행규칙
   별표 5/5의2 and 시행령 별표 1/1의2/1의3; get_annexes shows that `licbyl` + annex units +
   HWP parsing yields usable tables (call 4). Waymaker should store annex text with MST,
   시행일, 별표 번호, file hash and source link, and diff annexes, not only articles.
3. **Fail-closed vocabulary.** Distinguish "not found", "could not check", "skipped (cap)",
   "partial", "repealed", "renamed", "future-effective" as typed states (the reference does this
   in prose). This maps directly onto Paradiso's "keep data intact → prevent misleading
   rendering → log for manual review" rule.
4. **부칙 as data.** 72 addenda for one 시행규칙 contain application-timing rules for pending
   applications (e.g., 제1024호 제3조). Index them per amended provision/annex column instead of
   keyword-sampling them.

What not to adopt:

* Title-only, threshold-0.25 "content verification"; any verifier that silently skips 호/목/별표/
  부칙/"영 제N조" citations; transitional excerpts with silent caps.
* The anti-bot redirect follower and Referer spoofing (bypass; licence-unclear origin per NOTICE).
* Hard-coded legal-principle text and editorial warnings injected into tool output.
* Sending Waymaker user questions to the hosted third-party endpoint (data leaves Visable's
  boundary; version unknown; shared server key under rate limit per server.json; NOTICE says an
  OC key is for its issuer only — shared-key operation is a terms question, UNVERIFIED).

## 7. Open questions

* Does `get_law_text(mst)` without `efYd` on a promulgation with a pending staggered slice (e.g.,
  MST 289833 with 2027-09-16 for 제73조) return the in-force or the future text? Code comment says
  last slice for MST 281865; not reproduced. [corrected by verifier: answered — for MST 289833 제73조
  it returned the future (2027-09-16) text under a 시행일 20260915 "current" header; see Verification pass, LIVE V7–V9]
* Does `get_annexes(date=…)` select the right column-level version when 부칙 단서 delays only part
  of an annex (부칙 제936호 E-10란 → 2019-01-01)?
* Licence status of LexDiff-ported files and the LexLink-derived anti-bot module.
* Is there an open.law.go.kr target for Ministry of Justice first-level interpretations?
* Hosted instance exact version and data-retention/logging policy (access log claims path-only).

## Verification pass

Verifier: adversarial-verification subagent, 2026-10-19. Method: re-opened every cited file at the
cited lines with a file reader, recomputed the bigram score by hand, and re-ran the key live
observations against the same hosted MCP instance. **Environment limitation:** every shell command
in this pass failed before running with `ENOSPC: no space left on device` (the harness could not
create its output file), so I could not run `git`, `grep`, `find`, `wc` or any test. Repo HEAD was
checked by reading `.git/HEAD` and `.git/refs/heads/main`; "zero hits" claims were checked by
reading the whole files. No reference code was executed, installed or built; no tests were run
(reference tests: forbidden; Visable tests: shell unavailable).

### Live re-checks (hosted instance, version unknown; public law names and made-up citations only; no personal data)

9 tool calls were attempted. V1 failed and returned nothing. If a failed attempt counts, this is
**one more than the original 8-call budget**. I am stating this openly.

| # | Call | Result | Status |
|---|---|---|---|
| V1 | `legal_analysis(applicable_law, 출입국관리법 시행규칙, 2022-03-01, 제76조)` | Error, verbatim: "The connector's server isn't responding. You can try again." | OBSERVED (failure) |
| V2 | same call, retried | Same output as the original call 7: version 시행 2022.02.07 [제1022호, 타법개정] MST 240295; 21 later versions; upcoming 2027.09.16 제1125호; "▶ 현행과 비교: ✅ 동일"; exactly 6 excerpts, 제01125/01103/01086/01054/01042/01032호 (zero-padded); no "more addenda" notice; fixed 형법/행정기본법 principles block | OBSERVED |
| V3 | `get_law_text(mst=289833, jo=부칙)` | "부칙 72건 (최근 공포부터)", from <제1125호, 2026.09.15> down to <제367호, 1993.04.01>, not truncated. 부칙 제1024호 (2022.04.12) 제3조 says that applications made before it under 제76조제1항제1호·제3호 and 제2항제5호·제7호 keep the old attachment rules despite the amended 별표 5 and 5의2. Its 제1조 also delays the F-6 columns of 별표 5 and 5의2 to one year after promulgation. **Data oddity:** the 제2조 text of 제1125호 matches 제1103호 word for word (also in V2). Upstream error or a real repeat: UNVERIFIED | OBSERVED |
| V4 | `legal_analysis(verify_citations, <8 made-up references to 출입국관리법/영/규칙>)` | 6 statute citations counted. ✓ 규칙 제76조 제2항. ✗ 제4항 ("최대 제3항"). ✓ 시행령 제12조(일반체류자격) "제목 일치" although I wrote "(체류자격의 구분)". ✓ 법 제24조(체류자격 변경허가): my "제9호" was silently dropped. "영 제12조" → ⚠ 법령명 추출 실패. "…시행규칙 부칙 제3조" → ⚠ 법령명 추출 실패. "별표 5의2" and "별표 1의2 … 가목" not counted. Banner [HALLUCINATION_DETECTED], isError | OBSERVED |
| V5 | `get_law_text(mst=289833, jo=제76조, efYd=20190101)` | Redirect note: "시행 2018.09.21, 공포 제936호 일부개정, MST 204664, 당시 법령명 「출입국관리법 시행규칙」", followed by the article text | OBSERVED |
| V6 | `search_decisions(interpretation, 체류자격, display=5)` | 3 hits (22-0431, 25-0698, 13-0155). Each link is a relative `/DRF/lawService.do` path with the OC value masked as `***` and `&amp;` separators | OBSERVED |
| V7 | `get_law_text(mst=289833, jo=제73조)` (no efYd) | Header: 공포일 20260915 / 시행일 20260915, labelled as that version's body. Body: 가목 "삭제 <2026.9.15>", revision stamp includes 2026.9.15 | OBSERVED |
| V8 | `get_law_text(mst=289833, jo=제73조, efYd=20270916)` | Body identical to V7; header 시행일 20270916 | OBSERVED |
| V9 | `get_law_text(mst=289833, jo=제73조, efYd=20260915)` | Different body: 가목 "외국인등록증 발급 및 재발급 수수료: 현금 …" still present, no 2026.9.15 stamp, narrower payment methods | OBSERVED |

**New finding (V7–V9):** a plain MST read of 제73조, which callers treat as "current", returned the
text due to take effect on 2027-09-16 (부칙 제1125호 제1조 단서). The header showed the in-force date
20260915 and the note said it was that version's body. The text actually in force is the one in V9.
For the second half of this sentence I did not issue a verify_citations call on 제73조, so it rests
on reading the code (INFERRED). `verify_citations` reads articles through the same "MST only, no
date" path [CODE src/tools/verify-citations.ts:471; src/lib/api-client.ts:186-197], so it would
check such an article against future wording. For Waymaker, this rules out treating any MST-only
read as "the rule in force today".

### Verdicts on the 15 headline claims

| # | Verdict | Evidence / correction |
|---|---|---|
| 1 | confirmed | `.git/refs/heads/main` = 0a8f08ef…; [CODE package.json:2-4] 4.15.9; LICENSE MIT. I counted 99 entries in `allTools` [CODE src/tool-registry.ts:88-742]. `V3_EXPOSED` holds 10 names [CODE src/lib/tool-profiles.ts:21-29], and ListTools filters to them [CODE src/tool-registry.ts:804,812-827]. Commit date and subject not re-checked (no shell) |
| 2 | confirmed | [CODE src/tool-registry.ts:900-925]: handler texts are joined into one `type:"text"` item with `isError`, and there is no other output channel. Nuance: the bracket labels are not one vocabulary. `formatToolError` prints `[LAW_NOT_FOUND]`, `[UPSTREAM_NO_DATA]`, etc. [CODE src/lib/errors.ts:12-32,164]. `notFoundResponse`/`noResultHint` print `[NOT_FOUND]` with "do not guess" lines addressed to the LLM [CODE src/lib/errors.ts:76-114]. LLM-directed text seen live in V4 ("절대로 '검증 완료'로 답변하지 마세요") |
| 3 | confirmed | [CODE src/lib/law-lineage.ts:97-136 (eflaw, LID, nw=1,2,3, ≤10 pages of 100; empty result when the filter looks ignored); src/tools/law-text.ts:423-474]. V5 reproduced the redirect, including MST and 공포번호. Whether eflaw+LID really returns every slice across renames is a code-comment claim (README-ONLY/INFERRED) |
| 4 | confirmed | [CODE src/tools/law-text.ts:191-216]. V3: 72 addenda, newest first, untruncated. For larger laws the 50k-char cut [CODE src/lib/schemas.ts:53,80-115] could drop the oldest addenda; the "N건" header counts them before the cut |
| 5 | confirmed | [CODE src/tools/applicable-law.ts:102-137 (default 6 addenda × 3 lines, ≤250 chars, newest first, loop breaks at cap, no notice); 284-288 (addenda from the current MST via target=law); 336-365]. V2+V3 reproduce the omission of 제1024호 제3조. Mechanism detail: only addenda with a matching line count toward the cap. That means a line naming 제76조 or matching the transition keywords, from an addendum whose number belongs to a later version or the applicable one. 제1106/1097/1083/1062/1063/1052/1026호 were skipped without counting; 제1024호 was simply 7th |
| 6 | confirmed | [CODE src/tools/applicable-law.ts:300-333]: only article text is compared, whitespace-normalised. V2 "✅ 동일". Evidence of later annex changes is indirect: 부칙 제1024호 (2022.04.12), 제1054호 (2023.06.30, "별표 5의2 … 개정규정") and 제1086호 (2024.12.24, "별표 1의 개정규정") each name amended annexes after 2022-03-01. Wording fix: the 부칙 do not themselves amend annexes. They are the application rules for annex amendments in the same promulgation |
| 7 | confirmed | [CODE src/lib/citation-content-matcher.ts:31-34,142-189; src/tools/verify-citations.ts:496-501]. Hand computation: 체류자격의구분 has 6 bigrams and 일반체류자격 has 5; 3 are shared, union 8, 0.375 ≥ 0.25. V4 reproduced "제목 일치". Also missed in the notes: a short claim (<30 chars) that appears inside the official title matches outright [CODE …matcher.ts:151-155] |
| 8 | corrected | 호 parsed but never checked: confirmed [CODE src/tools/verify-citations.ts:503-521], and V4 dropped "제9호". 목 and 별표 never parsed [CODE …:54]: confirmed. **Correction:** 부칙 articles *are* extracted as bare "제N조" but get no law name, so they come out as ⚠ "법령명 추출 실패" (V4), not silently ignored. "Current version only" also needs care. The version checked is the MST-only body of the current search hit, which can be future text (V7–V9, INFERRED for this tool). Renamed laws are checked against the last version under the old name [CODE …:528-553] |
| 9 | corrected (minor) | Upstream `nb=` is a prefix match. Exactness comes from a local filter on the 사건번호 field [CODE src/lib/case-citation.ts:166-181]. Future-year ⇒ ✗ only for 4-digit years with a known case code [CODE …:129-134]. Misses are "미확인" [CODE …:182-191]. No relevance check. Not re-run live (budget) |
| 10 | confirmed (code) | [CODE src/lib/api-client.ts:321-366 (licbyl/ordinbyl/admbyl chosen by name keywords; display 100); src/lib/annex-file-parser.ts:30-33 (`ocr:false`); package.json:73 (kordoc 4.18.2 pinned)]. The success header holds law name, annex title, file type and optional page count [CODE src/tools/annex.ts:384-395]: no MST, version date or URL. Failure and image-PDF paths *do* print a download URL [CODE annex.ts:312,326,337,354]. Live call not re-run |
| 11 | confirmed | [CODE src/tools/scenarios/delegation.ts:12-21]; [DOC README-EN.md:307; README.md:492-498]. Additional overclaim: the `chain_law_system` tool description still advertises the delegation scenario as watching for unenacted subordinate laws [CODE src/tool-registry.ts:628] |
| 12 | confirmed | Statutes get only MST plus "read the 부칙/개정문" advice [CODE src/lib/abolished-laws.ts:87-98]. Successor names are extracted only from admin-rule abolition reasons [CODE …:145-156,211-246]. Overclaims: [DOC README-EN.md:3; README.md:226-228 "법령·행정규칙 양쪽 모두 지원"], and the `search_law` tool description [CODE src/tool-registry.ts:92]. CHANGELOG 4.10.0 is accurate [DOC CHANGELOG.md:591] |
| 13 | confirmed | [CODE src/lib/law-antibot.ts:1-14,38-56,75-172; src/lib/fetch-with-retry.ts:94-107,174-175,189-205]. Add: a hard-coded browser User-Agent [CODE fetch-with-retry.ts:88-92]. NOTICE says the *parsing approach* was re-implemented and the source repo shows no licence [DOC NOTICE:25-37] |
| 14 | confirmed | [CODE src/tools/external-links.ts:139-173]: links are name-based (`/법령/{name}/{jo}`), ID-based (`lsInfoP lsId`), or point to the 체계도 page by MST (version-tied, but not the text). Nothing is fetched or validated. Decision links echo the upstream field [CODE src/tools/interpretations.ts:75-77] with masking at the registry. V6 reproduced the relative, OC-masked, `&amp;` link |
| 15 | confirmed (scope-limited) | Reference side: I read search-normalizer.ts (613 lines), route-patterns.ts (882) and scenario-rules.ts (211) in full. None contains 출입국/외국인/재외동포/난민/국적/이민/고용허가. Visable side: [CODE /Users/seonjaekim/dev/Visable-genesis/backend/services/law_tools.py:777,921,1047,1075,1088-1094,1245] use law/admrul/lstrm; [CODE …/precedent_sources.py:60] uses prec. A repo-wide grep showing no other targets anywhere in Visable could not be re-run (ENOSPC). That part rests on the original agent's grep |

### Omissions against the brief, and what I filled

Filled (with evidence above):
1. **MST-only "current" reads can return future-effective text** under the in-force header
   (V7–V9). This answers open question 1 and affects the "Statute text retrieval", "Future-effective
   amendments" and "Citation existence" rows.
2. A **browser User-Agent spoof** sits alongside the Referer injection and anti-bot follower (§1).
3. **Tool-description overclaims**, not just README ones. `search_law` promises successor guidance
   for repealed statutes [CODE src/tool-registry.ts:92]. `chain_law_system` promises unenacted-delegation
   monitoring [CODE src/tool-registry.ts:628]. LLM clients read these descriptions, so they matter more than the README.
4. **A second annex-only staggered date** in this rule. 부칙 제1024호 제1조제2호 delays the F-6 columns of
   별표 5/5의2 by one year, alongside 제936호 (E-10 columns). This backs §5 call 5's INFERRED point
   that version selection cannot see column-level dates.
5. **How the applicable_law cap works** (claim 5 row), plus the short-claim containment rule in
   the title matcher (claim 7 row).
6. **Upstream data oddity:** 부칙 제1125호 제2조 repeats 제1103호 제2조 word for word (V3). Waymaker's
   부칙 ingestion should flag exact duplicate provisions across addenda for manual review instead of
   trusting them.
7. Spot checks: test files src/tools/law-text.addenda.test.ts,
   src/lib/citation-content-matcher.test.ts and src/tools/applicable-law.staggered.test.ts exist and
   target the described behaviour (ran: not run). `docs/UPSTREAM-PERF.md` is missing, confirming §4.
   Execution limits (48 attempts, 8/24 MiB, 50,000 chars) are defaults that environment variables can
   override [CODE src/lib/execution-limits.ts:21-32,65-80].

Could not fill:
* A repo-wide grep of Visable for other DRF targets, a re-check of commit date and subject, and
  file/test counts in §0 (shell unavailable: ENOSPC).
* A live re-run of `get_annexes` 별표 5의2 (budget). Claim 10 rests on code alone.
* 서식 (별지 forms) is still thin. The schema offers knd 2/4 for 서식/부칙서식 [CODE src/tools/annex.ts:31],
  but no form was retrieved, so form parsing quality is unknown (UNVERIFIED).
* Whether open.law.go.kr has a Ministry of Justice 1차 해석 target: not checked (no network
  research in this pass). Still UNVERIFIED.
