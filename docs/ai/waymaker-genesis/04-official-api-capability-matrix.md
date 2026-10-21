# 04 — Official API capability matrix (open.law.go.kr DRF)

Status: **RESEARCHED ONLY.** This document changes no code. It condenses two
adversarially verified research notes and the law identity seed. Where a
verifier correction and the original note disagree, the correction is used.

Mission 001 "Waymaker Genesis". Network research 2026-10-19 (UTC); this document
was written 2026-10-20 with offline re-checks only (§6.2). Sources:

* [research-notes/official-api.md](research-notes/official-api.md), §0–§10 and
  its verification pass, cited as **OA §n** and **OA-V**;
* [research-notes/law-identity.md](research-notes/law-identity.md), §1–§8 and
  its verification pass, cited as **LI §n** and **LI-V**;
* [research-notes/law_identity_seed.json](research-notes/law_identity_seed.json),
  22 records, cited as **seed**.

**Code baseline.** The notes audited origin/main `0713370`. Main is now
`fc896c2`. `git diff --stat 0713370 fc896c2` is empty for every file this
document cites: the law stack, `backend/paradiso_backend.py`, the status-guidance,
nationality, form, short-stay and source-registry data, and `visa_data.json`. So
`[CODE …]` line numbers hold at both commits, and I re-read the key lines at
`fc896c2` on 2026-10-20. This worktree also holds an uncommitted law-stack fix
pass (F1–F8, [research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md)).
This document describes committed `fc896c2` only.

**Credential hygiene.** Every URL writes the credential as `OC={OC}`. No real OC
was used, looked for or stored. The three documented sample calls used the
placeholder sample OC that the guide pages publish (OA §0, §7).

Evidence tags: `[CODE path:line]`, `[DOC page]`, `[LIVE request, date, result]`,
`[WEB url, accessed 2026-10-19]`. Status words: VERIFIED (primary page or code
read), OBSERVED (seen in a live response), README-ONLY, INFERRED (reasoning),
UNVERIFIED. Nothing here is legal advice.

## Status at a glance

| Part | Status | Basis |
|---|---|---|
| Interface conventions (§1.1) | VERIFIED (doc) on the 57 guide pages actually read. The ~138 other guides on the index were never opened (UNVERIFIED) | OA §1, OA-V claim 1 |
| Onboarding and limits (§1.2–§1.3) | Process VERIFIED (doc). Whether IP, referer and target binding is still enforced is UNVERIFIED (the source is a 2015 Q&A) | OA §5 |
| Family catalog (§2) | VERIFIED (doc) for every family listed. The priority column is INFERRED | OA §2–§3, §8, OA-V |
| Response shapes and failure envelopes (§3) | OBSERVED on 3 documented sample calls and 2 no-OC calls; re-parsed offline 2026-10-20 | OA §2, §7, OA-V V-E |
| Terms of use (§4) | VERIFIED for statute text. AI-training terms UNVERIFIED | OA §6 |
| Official identities (§7) | 20 of 22 records VERIFIED (web, 2026-10-19); 2 not found on law.go.kr (UNVERIFIED) | LI §3–§4, LI-V, seed |
| Stale Waymaker data (§8) | VERIFIED at `0713370`; files unchanged at `fc896c2` | LI §5–§6, LI-V |
| Backend support for the P0/P1 families | NOT STARTED (Mission 002, [17](17-mission-002-plan.md)) | — |

## 0. Findings that drive WLIE

1. **The primitives WLIE's temporal resolver ([06](06-temporal-law-and-source-identity.md))
   needs exist officially, and Waymaker uses none of them.** The official
   primitives are:
   * point-in-time text: the `eflaw` body with (`MST`, `efYd`);
   * version enumeration: the `eflaw` list with `LID` + `nw=1,2,3`;
   * per-article history: `lsJoHstInf`;
   * a daily change feed: `lsHstInf`;
   * withdrawn records: `delHst`.

   Waymaker references only `law`, `admrul`, `lstrm`, `prec` and `decc`. It
   never sends `efYd` and reads no history target. VERIFIED (doc and code; §2.4).
2. **A version is (법령일련번호, 시행일자), not 법령일련번호 alone.** One
   promulgation can carry two effective dates. 출입국관리법 시행규칙 `289833` is
   in force from 2026-09-15, and again from 2027-09-16 for 제73조. The `eflaw`
   list returns two rows for one MST. VERIFIED (web) and OBSERVED (§3.1 item 10,
   §7).
3. **Failures look like successes.** Two cases were seen:
   * A JSON call without OC returns HTTP 200 with `{"result": …, "msg": …}` and
     no `resultCode`. Waymaker's parser reports it as "no results".
   * An OC-less DRF HTML link returns HTTP 200 with an auth-failure page. Every
     precedent list link Waymaker shows its users is such a link.

   OBSERVED (§3.2).
4. **Statute, 고시·훈령 and court text is outside copyright (저작권법 제7조), but
   it comes with three conditions:**
   * open.law.go.kr requires naming 법제처 as the source and forbids altered text;
   * law.go.kr says its text has no legal effect, and the 관보 prevails;
   * no page that was read states terms for AI training.

   Each point is marked VERIFIED or UNVERIFIED in §4.
5. **Waymaker's stored law versions are stale in several places.** One
   status-guidance quote also presents the 2027-09-16 text of 시행규칙 제73조 as
   the text in force today (§8). VERIFIED.

## 1. Endpoints and onboarding

### 1.1 Interface conventions (OA §1; VERIFIED (doc) unless marked)

| Convention | What the guides say | Status |
|---|---|---|
| Endpoints | List and search: `http://www.law.go.kr/DRF/lawSearch.do?target=<t>`. Body and detail: `http://www.law.go.kr/DRF/lawService.do?target=<t>`. The 55 original guides contain 137 `lawSearch.do` and 102 `lawService.do` mentions and no other DRF path; the 2 mobile guides use the same two paths. Legacy guides print `http://`. The 지식베이스 guides and `openApiManual.do` print `https://www.law.go.kr`. A few samples omit `www.` | VERIFIED on 57 guides; INFERRED for the ~138 unopened ones |
| Guide index | `guideList.do` says "총 191 건" but holds 195 distinct `openApiGuide('…')` names. Mobile guides have their own names (e.g. `mobLsListGuide`). The gap is unexplained | VERIFIED (re-fetched byte-identical, OA-V R1) |
| Required parameters | `OC` ("신청한 API인증값") and `target` are "(필수)" on all 57 guides. `type` is "(필수)" almost everywhere, except: `elaw` list and body, `trty` body, `lsAbrv`, `delHst`, and the mobile law body (which instead requires `mobileYn`). `eflaw` list and body say "생략시 기본값: XML" | VERIFIED |
| What OC is | The part of the registered login ID (an e-mail address) before the '@' | VERIFIED, from a 2015 Q&A page [DOC lab/supportCaseView.do?supportCaseSeq=30] |
| Formats | HTML/XML/JSON on most guides. **HTML only:** `lsHistory` list and body, and the mobile law body. **XML/JSON only:** `lsJoHstInf` (both forms), `lsDelegated`, `lsAbrv`, `delHst` and all 지식베이스 targets. The `prec` body is HTML only for 국세청 cases | VERIFIED |
| Paging | `display` (default 20, **max 100**) and `page` (default 1) on nearly every list. `aiSearch` gives "default=20" and no maximum. The `lsJoHstInf` by-date list has `page` but no `display` | VERIFIED (`max=100` appears 27 times) |
| Article address | `JO` is 6 digits, a 4-digit article plus a 2-digit branch (`000200` = 제2조, `001002` = 제10조의2). `HANG` and `HO` are also 6 digits (`HO=001002` = 제10호의2). `MOK` is one Hangul character (가…하), URL-encoded. **Trap:** in the `prec` list, `JO` means 참조법령명, a law *name* | VERIFIED |
| Ranges | `YYYYMMDD~YYYYMMDD` for `efYd`, `ancYd`, `prmlYd`, `modYd`, `prncYd`, `regYd`, `explYd`, `dpaYd`, `rslYd`, `eftYd`, `concYd` and `lstrm` `regDt`. `ancNo` ranges are written `306~400` | VERIFIED |
| Sort codes | `lasc`/`ldes` (name), `dasc`/`ddes` (promulgation or decision date), `nasc`/`ndes` (number), `efasc`/`efdes` (effective date). `trty` adds `rasc`/`rdes` (관보게재일), and `lstrm` uses `rasc`/`rdes` for 등록일자 | VERIFIED |
| 제개정 codes (`rrClsCd`) | 300201 제정, 300202 일부개정, 300203 전부개정, 300204 폐지, 300205 폐지제정, 300206 일괄개정, 300207 일괄폐지, 300208 기타, 300209 타법개정, 300210 타법폐지 | VERIFIED |
| Law ID vs MST | `ID` is the 법령 ID. `MST` is "법령 마스터 번호 - 법령테이블의 lsi_seq 값", which equals the 법령일련번호 that lists return. The `eflaw` and `lawjosub` guides say that querying by `ID` returns the **current** text. The `law` body guide does not say so | VERIFIED; INFERRED for `law` |
| Status envelope | `numOfRows`, `resultCode` (00 / 01) and `resultMsg` are documented only on `lsStmd`, `oldAndNew`, `thdCmp`, `admrulOldAndNew` and `lstrmAI` (numOfRows only). **No guide documents an error body** | VERIFIED (doc); live shapes in §3.2 |
| Other common parameters | `popYn=Y` opens the HTML detail as a popup. `gana` is a dictionary-order filter. `org` is a 소관부처 code; the samples print 1613000 국토교통부, 1741000 행정안전부, 1352000 보건복지부, 1320000 경찰청 and 1543000 농림축산식품부. No guide prints the full code table. **The 법무부 `org` code is UNVERIFIED** | VERIFIED / UNVERIFIED |
| Change history | HTML comments: `lsNwInfoGuide` and `lsEfYdInfoGuide` were revised "2026. 01. 29. [#38236]". `lsEfYdListGuide` records the fix "[#33556]" (2023-10-17) for a bug where `nw` took effect only for the sample OC | VERIFIED |

### 1.2 Onboarding: OC registration and approval (OA §5)

[DOC https://open.law.go.kr/LSO/information/guide.do] VERIFIED unless marked.

1. 회원가입 (sign up). Since 2015 the API application can be filed at sign-up
   [DOC support/noticeList.do #8, 2015-07-03].
2. Log in, choose OPEN API, and apply **per data family**. "모든 DATA 활용은
   공동활용이용 승인 후 가능": no data may be used before approval. The
   application page `openApi/cuAskList.do` redirects to login (302, OBSERVED).
3. Staff review normally takes 1–2 days.
4. Check the result in the 신청 list.
5. A production (운영) application requires registering the app as an
   **활용사례** (use case).

**Add-on services.** 체계도, 신구법, 3단비교 and 연혁 come with the 법령 approval
at no extra application. 행정규칙 신구법 comes with the 행정규칙 approval. VERIFIED
(`lsStmd`, `oldAndNew`, `thdCmp`, `lsHistory` and `admrulOldAndNew` guides).
That 판례, 해석례 and 조약 each need their own approval is INFERRED from the Q&A
line "target과 type이 신청하신 내용과 동일한지 확인". Every new family must
therefore be added to the OC application before code depends on it (OA §8
item 7).

**Binding to IP, referer, target and type.** These rules come from 2015 Q&A
pages [DOC lab/supportCaseView.do?supportCaseSeq=30, =5, =29], so
**current enforcement is UNVERIFIED**:
* An approved OC works only from the IPs registered on the application.
* Browser-originated calls need a matching **referer domain** and the same
  protocol.
* The requested `target` and `type` must match what was approved; otherwise the
  call fails authentication.
* IPs can be added to an approved application and take effect at once.

The deployed backend works, so its current egress satisfies whatever check
applies (INFERRED). How this interacts with Railway egress is UNVERIFIED (OA §10).

**Self-service tools** (login required): 오류자가진단 (request-URL check) and
IP 접속이력 (access log). Both `lab/ipErrorCheck.do` and `lab/selfDiagnosis.do`
returned 302 to login. OBSERVED.

**Contacts:** restrictions and applications 044-200-6797; technical questions
02-2109-6446 [DOC information/guide.do]. VERIFIED.

### 1.3 Limits, quotas and freshness (OA §5)

* **No numeric daily quota is published** on any page fetched: 55 guides,
  `service.do`, `guide.do`, `openApiManual.do`, the notices and the Q&A pages.
  VERIFIED (absence, on those pages). No guide gives a per-call body size limit;
  the S2 law body was 71,566 B of JSON (OBSERVED).
* The usage page says use can be restricted for "상업적 이용이 불가능한 API에
  대해 상업적 활용한 경우" and for "트래픽 초과로 인해 시스템에 부하가 발생할
  경우". VERIFIED as statements. **Which APIs are non-commercial is not named on
  any page fetched** (UNVERIFIED).
* None of the 99 law.go.kr web-view GETs or the 3 sample calls was throttled.
  All returned 200 (LI §1, LI-V, OA §7). No HTTP 429 was ever observed, so rate
  limiting is UNVERIFIED.
* Freshness: the service page says the data is "실시간 연계되어 제공" (README-ONLY,
  not tested). The `lsJoHstInf` by-date list is **previous-day** data ("이 서비스는
  전일 데이터를 기준으로 제공됩니다"). VERIFIED (doc).
* The data.go.kr mirror 법제처_현행법령 본문 조항호목 조회 (15058878) is
  described below. [LIVE https://www.data.go.kr/data/15058878/openapi.do,
  2026-10-19, 200; re-fetched by OA-V R6] VERIFIED.
  * API 유형 "LINK", 무료, 이용허락범위 제한 없음, 업데이트 실시간.
  * 개발단계 and 운영단계 both 자동승인.
  * Traffic: "해당 기관의 정책에 따라 트래픽 수는 상이 할 수 있음".
  * 데이터 포맷 XML; 등록일 2018-11-01; 수정일 2025-07-08; 활용신청 400.
  * That the key is issued on open.law.go.kr is INFERRED from the LINK type; the
    page has no such text or link.

## 2. Family catalog

**Legend.**
* **Params** are copied as the notes record them. **Bold** means the guide marks
  the parameter "(필수)", and "one required" means the guide requires one of two.
  OC, `target` and `type` are omitted unless they differ from §1.1.
* **Formats** follow §1.1 (HTML/XML/JSON) unless the row says otherwise.
* **Uses today** means non-test backend code at `fc896c2` references the target:
  y or n.
* **WLIE** is my priority (INFERRED), not an official classification:
  * **P0**: needed for the lookups that [06](06-temporal-law-and-source-identity.md)
    and [07](07-evidence-verification-design.md) specify. These are the source
    bundle operations `resolve_title`, `list_versions`, `get_provision` and
    `get_addenda`.
  * **P1**: needed for precision, change monitoring or delegation edges in
    Mission 002.
  * **P2**: useful later, or for display only.
  * **no**: not needed, or not acceptable as evidence.

### 2.1 Statutes

| Family (htmlName) | Call | Key params | Formats | Identity / version fields | Limits and caveats | Uses today | WLIE | Src |
|---|---|---|---|---|---|---|---|---|
| `law` (`lsNwListGuide`) | list | `search` (1 법령명 default, 2 본문검색), `query`, `display`, `page`, `sort`, `date` (공포일자), `efYd`, `ancYd`, `ancNo`, `rrClsCd`, `nb` (공포번호), `org`, `knd`, `lsChapNo` (01–44편), `gana`, `popYn` | HTML/XML/JSON | 법령ID, 법령일련번호, 현행연혁코드, 법령명한글, 법령약칭명, 공포일자, 공포번호, 제개정구분명, 시행일자, 자법타법여부 | `display` ≤ 100. `법령상세링크` per row (§3.1 item 11) | **y**: `search_laws` [CODE backend/services/law_tools.py:776-777]; the cloud fallback too [CODE backend/services/law_cloud_fallback.py:146, :205] | **P0** (`resolve_title`) | OA §2.1 |
| `law` (`lsNwInfoGuide`) | body | `ID` (법령 ID) or `MST` (lsi_seq), one required; `LM` (법령명), `LD` (공포일자), `LN` (공포번호), `JO` (6 digits; omit for all articles), `LANG` (KO / ORI 원문) | HTML/XML/JSON | Header: 법령ID, 공포일자, 공포번호, 시행일자, 제개정구분, 제명변경여부. Articles: 조문번호, 조문가지번호, 조문여부, 조문시행일자, 조문제개정유형, 조문이동이전/이후, 조문변경여부. 부칙공포일자/번호/내용. 별표 fields (번호, 가지번호, 구분, 제목, HWP, PDF and image links, 내용). 개정문내용, 제개정이유내용 | Only `MST` pins a version (S2: `MST=261457` returned the 2024-03-26 version). Whether `ID` returns the current version is INFERRED for this guide | **y**: `get_law_detail` [CODE law_tools.py:921-933] | **P0** (current text, 부칙, 별표) | OA §2.1, §4 |
| `eflaw` (`lsEfYdListGuide`) | list | `search`, `query`, `nw` (1 연혁, 2 시행예정, 3 현행; default all; comma-combinable, e.g. `nw=1,2,3`), `LID` (법령ID, e.g. `LID=830`), `display`, `page`, `sort`, `efYd`, `date`, `ancYd`, `ancNo`, `rrClsCd`, `nb`, `org`, `knd`, `gana`, `popYn`. There is no `lsChapNo` | HTML/XML/JSON, default XML | As the `law` list. Rows are keyed by (MST, efYd) | `nw` and `LID` are *not* "(필수)" (verifier correction). `resultCode`, `resultMsg` and `numOfRows` are observed but not on this guide | n | **P0** (`list_versions`: `LID` + `nw=1,2,3`) | OA §2.2, OA-V V-B |
| `eflaw` (`lsEfYdInfoGuide`) | body | `ID` (returns the current text; `efYd` is then ignored and should be omitted), `MST`, **`efYd`** (int), `JO`, `chrClsCd` (010202 한글 / 010201 원문) | HTML/XML/JSON, default XML | The `law` body fields plus 조문시행일자문자열, 별표시행일자문자열, 별표제목문자열 and 별표시행일자; drops 제명변경여부 and 한글법령여부 | The documented way to fetch "the text as in force on date X". `lsJoHstInf` 조문링크 resolves to exactly this form | n | **P0** (`get_provision`, `get_addenda`) | OA §2.2 |
| `eflawjosub` (`lsEfYdJoListGuide`) | body | `ID` or `MST`; **`efYd`** (ignored with `ID`); **`JO`**; `HANG`; `HO`; `MOK` | HTML/XML/JSON | The `lawjosub` fields plus 법령명_영어, **적용시작일자** and **적용종료일자** (a validity interval) | No 조문가지번호 in the response table. That the branch is an input-only address is UNVERIFIED | n | P1 (per-article validity → `provision_effective_dates`) | OA §2.6 |
| `lawjosub` (`lsNwJoListGuide`) | body | `ID` or `MST` (`ID` → current); **`JO`** (char, 6 digits); `HANG`; `HO` (branch allowed); `MOK` (one Hangul character, URL-encoded) | HTML/XML/JSON | 법령키 (documented here), 조문별시행일자, 조문시행일자문자열, 시행일기준편집여부, 조문/항/호/목 | Current text only | n | P2 (`eflawjosub` covers it) | OA §2.6 |
| `lsHistory` (`lsHstListGuide` / `lsHstInfoGuide`) | list + body | List: `query`, `display`, `page`, `sort`, `efYd`, `date`, `ancYd`, `ancNo`, `rrClsCd`, `org`, `knd`, `lsChapNo`, `gana`, `popYn`. Body: `ID` or `MST`, `LM`, `LD`, `LN`, `chrClsCd` | **HTML only** | No response field table | Not machine-readable. Enumerate versions with the `eflaw` list instead (INFERRED) | n | no (machine use; see §9) | OA §2.3 |
| `lsHstInf` (`lsChgListGuide`) | list | **`regDt`** (int, 법령 변경일, e.g. 20150101), `org`, `display`, `page`, `popYn` | HTML/XML/JSON | 법령일련번호, 현행연혁코드, 법령ID, 공포일자, 공포번호, 제개정구분명, 소관부처코드, 시행일자 | Daily change feed: poll yesterday's `regDt`, then filter on 소관부처 or a 법령ID watch-list (INFERRED) | n | P1 (monitoring) | OA §2.4 |
| `lsJoHstInf`, by date (`lsDayJoRvsListGuide`) | list `lawSearch.do` | `regDt` (조문 개정일), `fromRegDt`, `toRegDt`, `ID`, `JO` (4+2), `org`, `page`; no `display` | XML/JSON | 법령일련번호, 법령ID, 시행일자, 조문번호, 변경사유, 조문링크, 조문변경이력상세링크, 조문개정일, 조문시행일 | Previous-day data | n | P1 (per-article change feed) | OA §2.5 |
| `lsJoHstInf`, by article (`lsJoChgListGuide`) | `lawService.do` | **`ID`** (char), **`JO`** (int, 6 digits), `display`, `page` | XML/JSON | 법령일련번호, 공포일자, 공포번호, 제개정구분명, 시행일자, 조문번호, 변경사유, 조문링크 (→ `eflaw` `MST` + `JO` + `efYd`), 조문변경일 | (ID, JO, 조문변경일) is not unique; keep MST in the key (§3.1 item 12). Guide type errors: 법령명한글 typed "int", 조문링크 described as "변경사유" | n | P1 (fills `changed_provisions`; without it [06](06-temporal-law-and-source-identity.md) §3 step 7 fires conservatively) | OA §2.5, OA-V V-C |
| 부칙 (no target) | inside the `law` / `eflaw` body | None in the standard body. The mobile body (HTML only) has `PD` (부칙 list only) and `PN` (one 부칙 by number) | — | 부칙공포일자, 부칙공포번호, 부칙내용; live JSON adds `부칙키` and `부칙단위[]` | The one sample returned all 13 historical 부칙 (20040209–20240326). That every law does so is INFERRED | n (the body is fetched, but 부칙 are not read; [06](06-temporal-law-and-source-identity.md) §5) | **P0** (`get_addenda`, via the body) | OA §2.7 |
| `licbyl` (`lsBylListGuide`) | list | `search` (1 별표서식명 default, 2 해당법령검색, 3 별표본문검색), `query` (default *), `display`, `page`, `sort` (lasc/ldes), `org` (several codes, comma-separated), `mulOrg` (OR default / AND), `knd` (1 별표, 2 서식, 3 별지, 4 별도, 5 부록), `gana`, `popYn` | HTML/XML/JSON | 별표일련번호, 관련법령일련번호, 관련법령ID, 별표명, 별표번호, 별표종류, 공포일자, 공포번호, 별표서식파일링크, 별표서식PDF파일링크 | **No XML/JSON annex-body target** (`lsBylInfo` is on no guide: UNVERIFIED). Files are fetched as `https://www.law.go.kr` + link, e.g. `/LSW/flDownload.do?flSeq=<n>`, as HWP and PDF [DOC openApiManual.do]. The mobile body has `BD`/`BT`/`BN`/`BG` annex views (HTML only) | n | P1 (체류자격 tables are 시행령 별표 and forms are 시행규칙 별지; INFERRED) | OA §2.8, OA-V V-A |
| `lsDelegated` | body | `ID` or `MST` (`ID` → current law) | XML/JSON | 조문번호, 위임구분 (시행령, 시행규칙, 인용법령, 위임행정규칙 등), 위임법령일련번호, 위임법령조문번호(+가지번호), 위임행정규칙일련번호, 링크텍스트, 라인텍스트, 조항호목 | `openApiManual.do` describes it as the way to build law.go.kr-style links | n | P1 (delegation edges, [05](05-legal-intelligence-architecture.md) row D) | OA §2.9 |
| `thdCmp` (`thdCmpListGuide` / `thdCmpInfoGuide`) | list + body | List: as `lsStmd`. Body: **`knd`** (1 인용조문, 2 위임조문), `ID` or `MST`, `LM`, `LD`, `LN` | HTML/XML/JSON | 법령ID, 시행령ID, 시행규칙ID, 삼단비교존재여부, 시행일자, 위임행정규칙 (명, 일련번호, 조번호, 조가지번호) | Add-on service; the list carries `resultCode` | n | P1 (the official Act ↔ 시행령 ↔ 시행규칙 ↔ 위임행정규칙 chain) | OA §2.12 |
| `lsStmd` | list + body | List: `query`, `display`, `page`, `sort`, `efYd`, `ancYd`, `date`, `nb`, `ancNo`, `rrClsCd`, `org`, `knd`, `gana`, `popYn`. Body: `ID` or `MST`, `LM`, `LD`, `LN` | HTML/XML/JSON (XML added 2022-08-26) | 법령ID, 법령일련번호, 상하위법, 법률, 시행령, 시행규칙 | Add-on service | n | P2 | OA §2.10 |
| `oldAndNew` | list + body | Body: `ID` or `MST`, `LM`, `LD`, `LN` | HTML/XML/JSON | 구조문_기본정보 and 신조문_기본정보 (법령일련번호, 시행일자, 현행여부); 신구법존재여부 ("N" = none) | Add-on service | n | P2 (review aid for pending versions) | OA §2.11 |
| `elaw` (`lsEngListGuide` / `lsEngInfoGuide`) | list + body | List: `search`, `query` (Korean or English), `display`, `page`, `sort`, `date`, `efYd`, `ancYd`, `ancNo`, `rrClsCd`, `nb`, `org`, `knd`, `gana`, `type` (not "(필수)"), `popYn`. Body: `ID` or `MST`, `LM`, `LD`, `LN`, `type` | as guide | 법령명영문 (list) | **Body response fields UNVERIFIED** (no table). Translations are unofficial (§4) | n | P2 (display only) | OA §2.13 |
| `lsAbrv` | list | `type` (XML/JSON), `stdDt`, `endDt` (등록일 range) | XML/JSON | 법령ID, 법령일련번호, 법령약칭명, 등록일 | — | n | P2 (`short_titles`) | OA §2.14 |
| `delHst` (`datDelHstGuide`) | list | `type` (XML/JSON), `display`, `page`, `knd` (1 법령, 2 행정규칙, 3 자치법규, 13 학칙공단), `delDt`, `frmDt`/`toDt` | XML/JSON | 일련번호, 구분명, 삭제일자 | The guide table says the target is "datDel"; every sample URL uses `delHst`. `delHst` was not tested live (UNVERIFIED) | n | P1 (prune withdrawn records from a mirror) | OA §2.14 |
| `oneview`, `couseLs` | list / body | `couseLs` needs **`vcode`** (L + 13 digits) | — | — | — | n | no | OA §2.14 |
| Mobile `target=law&mobileYn=Y` (`mobLsListGuide` / `mobLsInfoGuide`) | list + body | List: the `law` list params plus `mobileYn` ("char : Y (필수)"). Body: `ID`/`MST`, `LM`, `LD`, `LN`, `JO`, `PD`, `PN`, `BD`, `BT`, `BN`, `BG` | List HTML/XML/JSON; **body HTML only** | — | Behaviour not tested | n | no | OA-V V-A |

### 2.2 Administrative rules, decisions, terms and treaties

| Family (htmlName) | Call | Key params | Formats | Identity / version fields | Limits and caveats | Uses today | WLIE | Src |
|---|---|---|---|---|---|---|---|---|
| `admrul` (`admrulListGuide`) | list | **`nw`** (1 현행, 2 연혁; default 현행)†, `search` (1 행정규칙명, 2 본문), `query`, `display`, `page`, `org`, `knd` (1 훈령, 2 예규, 3 고시, 4 공고, 5 지침, 6 기타), `gana`, `sort` (dasc/ddes = 발령일자), `date` (발령일자), `prmlYd`, `modYd` (수정일자), `nb` (발령번호; 제2023-8호 → `nb=20238`), `popYn` | HTML/XML/JSON | 행정규칙ID, 행정규칙일련번호, 행정규칙종류, 발령일자, 발령번호, 현행연혁구분, 제개정구분코드, 시행일자, 생성일자 | **`nw` codes differ from `eflaw`**, where 1 = 연혁 and 3 = 현행 | **y**: `search_admin_rules` [CODE law_tools.py:1046-1047] | **P0** (`resolve_title` for 고시·훈령) | OA §3.1 |
| `admrul` (`admrulInfoGuide`) | body | `ID` (= 행정규칙 일련번호, the version), `LID` (= 행정규칙 ID, stable), `LM`. Neither is "(필수)" (verifier) | HTML/XML/JSON | 행정규칙ID, 행정규칙일련번호, 발령일자, 발령번호, 제개정구분명, 현행여부, 시행일자, 조문내용, 부칙, 별표, 첨부파일링크 | **`ID` is the version here but the stable ID for `law`** | n | **P0** (rule text) | OA §3.1 |
| `admrulOldAndNew` | list + body | Body: **`ID` (일련번호) or `LID`** (one required), `LM` | HTML/XML/JSON | Mirrors `oldAndNew`, with 신구법존재여부 | Add-on with the 행정규칙 approval | n | P2 | OA §3.1 |
| `admbyl` (`admrulBylListGuide`) | list | `search` (1/2/3), `query`, `display`, `page`, `sort`, `org`, `knd` (1 별표, 2 서식, 3 별지), `gana`, `popYn` | as guide | 별표일련번호, 관련행정규칙일련번호, 발령일자, 발령번호, 관련법령ID, 별표서식파일링크 | — | n | P2 | OA §2.8 |
| `prec` (`precListGuide`) | list | `search` (1 판례명, 2 본문, 3 참조판례), `query`, `display`, `page`, `org` (400201 대법원 / 400202 하위법원), `curt` (법원명), `JO` (= **참조법령명**), `gana`, `sort` (default `ddes`), `date` (선고일자), `prncYd`, `nb` (사건번호; the sample passes two, comma-separated), `datSrcNm`, `popYn` | HTML/XML/JSON | 판례일련번호, 사건번호, 선고일자 (string), 법원명, 판결유형, 데이터출처명, 판례상세링크 | List 선고일자 "2023.03.13" vs detail "20230313" (§3.1 item 13) | **y** [CODE backend/services/precedent_sources.py:60, :630] | P1 | OA §3.2 |
| `prec` (`precInfoGuide`) | body | **`ID`** (판례 일련번호), `LM` | HTML/XML/JSON; 국세청 cases HTML only | 판례정보일련번호, 사건번호, 선고일자 (int), 판시사항, 판결요지, 참조조문, 참조판례 | — | **y** [CODE backend/services/legal_evidence.py:898-905] | P1 | OA §3.2 |
| `detc` | list + body | List: `search`, `query`, `display`, `page`, `gana`, `sort` (incl. efasc/efdes 종국일자), `date` (종국일자), `edYd`, `nb`, `popYn`. Body: **`ID`**, `LM` | HTML/XML/JSON | 헌재결정례일련번호, 사건번호, 종국일자, 재판부구분코드, 심판대상조문 | — | n (mapped to `None`, §2.4) | P2 | OA §3.3 |
| `expc` | list + body | List: `search`, `query`, `display`, `page`, `inq` (질의기관), `rpl` (회신기관), `gana`, `itmno` (13-0217 → 130217), `regYd`, `explYd`, `sort`, `popYn`. Body: **`ID`** (int), `LM` | HTML/XML/JSON | 법령해석례일련번호, 안건번호, 해석일자, 질의요지, 회답, 이유 | The `inq` type cell literally says "inq" | n (mapped to `None`) | P2 | OA §3.4 |
| `mojCgmExpc` (`cgmExpcMojListGuide` / `cgmExpcMojInfoGuide`) | list + body | List: `search`, `query`, `display`, `page`, `inq`, `rpl`, `gana`, `itmno` (when given, `query` is ignored), `explYd`, `sort`, `popYn`, `fields`. Body: **`ID`**, `LM`, `fields` | HTML/XML/JSON; `fields` not for HTML | 법령해석일련번호, 안건번호, 해석일자, **관련법령**, **데이터기준일시** | 법무부 first-instance interpretations; the most immigration-specific interpretation feed (INFERRED) | n | P1 | OA §3.4 |
| `okaCgmExpc` (`cgmExpcOkaListGuide`) | list (body guide fetched but not extracted) | As `mojCgmExpc` | as guide | As `mojCgmExpc` | 재외동포청 interpretations (F-4) | n | P2 | OA §3.4 |
| `decc` (`deccListGuide` / `deccInfoGuide`) | list + body | List: `search`, `query`, `display`, `page`, `cls` (재결례유형), `gana`, `date` (의결일자), `dpaYd`, `rslYd`, `sort`, `popYn`. Body: **`ID`**, `LM` | HTML/XML/JSON | 행정심판례일련번호, 사건번호, 처분일자, 의결일자, 재결례유형코드 | The repo comment calling it "NOT publicly confirmed" is stale | **y**, as an env-overridable default [CODE backend/services/legal_evidence.py:75, :90] | P2 | OA §3.5, OA-V V-G |
| `specialDecc*`, `cgmExpcMoleg*`, the other 37 agency interpretation feeds | — | Target values not read | — | — | UNVERIFIED. The index lists 39 agency list feeds and 37 body guides | n (`LAW_API_SPECIAL_ADMIN_APPEAL_TARGET` has no default) | no | OA §3.4–§3.5, OA-V V-I |
| `nhrck` (`nhrckListGuide`) | list | `lawSearch.do?target=nhrck`; parameters not catalogued | — | — | Saved but never discussed | n | P2 (possible relevance to discrimination complaints; INFERRED) | OA-V V-I |
| `lstrm` | list + body | List: `query`, `display`, `page`, `sort` (rasc/rdes = 등록일자), `regDt`, `gana`, `popYn`, `dicKndCd` (010101 법령 / 010102 행정규칙). Body: `query` (term name) | HTML/XML/JSON | 법령용어ID, 사전구분코드 (011401 법령용어사전, 011402 법령정의사전, 011403 법령한영사전), 법령용어정의, 출처 | — | **y** (list) [CODE law_tools.py:1074-1075] | P2 | OA §3.6 |
| 지식베이스: `lstrmAI`, `lstrmRltJo`, `joRltLstrm`, `lsRlt`, `aiSearch`, `aiRltLs` | list / body, `https` host | `lstrmAI`: `query`, `display`, `page`, `homonymYn`. `lstrmRltJo`: **`query`**. `joRltLstrm`: `query` or `ID`, **`JO`**. `lsRlt`: `query` or `ID`, `rltClsCd`. `aiSearch`: `search` (0 법령조문, 1 법령 별표·서식, 2 행정규칙 조문, 3 행정규칙 별표·서식), `query`, `display`, `page`. `aiRltLs`: `search` (0/1), `query` | XML/JSON | `aiSearch` hits carry 법령ID, 법령일련번호, 조문번호, 조문가지번호, 시행일자, 공포일자, 공포번호 | "법령정보지식베이스는 지능형법령검색을 위한 참고자료로만 활용하시기 바랍니다" | n | no (never evidence; an `aiSearch` hit would have to be re-fetched through `eflaw`) | OA §3.6 |
| `trty` (`trtyListGuide` / `trtyInfoGuide`) | list + body | List: `search` (1 조약명, 2 본문), `query`, `display`, `page`, `gana`, `eftYd`, `concYd`, `cls` (1 양자, 2 다자), `natCd`, `sort` (incl. rasc/rdes 관보게재일), `popYn`. Body: `ID`, `chrClsCd` (010202 한글 / 010203 영문) | HTML/XML/JSON; body `type` not "(필수)" | 조약일련번호, 조약번호, 발효일자, 국내발효일자, 국가코드, 관보게재일자 | The numeric 분야 and 국가 codes are on no guide (UNVERIFIED). The bulk-download form lists 양자 분야 "사증" and 다자 분야 "이민", "난민/국적" (OBSERVED) | n | P2 (visa-waiver agreements via `cls=1` + `query`) | OA §3.7 |

† Bold as recorded in OA §3.1. The verifier removed the same bold from `eflaw`
`nw` and `LID`, but did not re-check this one. The documented default (현행)
suggests it is in practice optional.

### 2.3 Identity and version fields mapped to the WLIE contract

The official side is VERIFIED (doc) unless marked. The WLIE column names the
field in [06 §1](06-temporal-law-and-source-identity.md) and in the source-bundle
format.

| Concept | Official field(s) | Request parameter | WLIE field | Status |
|---|---|---|---|---|
| Lineage | 법령ID; 행정규칙ID | `ID` (law family), `LID` (`eflaw` list, `admrul` body) | `stable_id` | VERIFIED |
| Version | 법령일련번호 = MST = lsi_seq, **plus** 시행일자; 행정규칙일련번호 | `MST` + `efYd`; `ID` on `admrul` | `version_id` + `effective_date` | VERIFIED; the (MST, efYd) pairing is OBSERVED |
| Composite version key | 법령키 = 법령ID (6) + 공포일자 (8) + 공포번호 (5) | none as input | not used as a key | OBSERVED |
| Provision effective date | 조문시행일자 (+문자열); 적용시작일자 / 적용종료일자 (`eflawjosub`); inline "[시행일: …]" markers on law.go.kr | `JO` | `provision_effective_dates` | VERIFIED (doc); markers VERIFIED (web, LI §2) |
| Changed provisions | `lsJoHstInf` 변경사유 and 조문변경일; 조문변경여부 (Y = "해당 조문내에 변경 내용 있음") | `ID` + `JO` | `changed_provisions` | VERIFIED + OBSERVED |
| Lifecycle | 현행연혁코드 (현행 and 연혁 observed; the 시행예정 label is UNVERIFIED); `eflaw` `nw`; `admrul` 현행연혁구분, 현행여부 | `nw` | no dedicated field: the resolver selects by effective date ([06](06-temporal-law-and-source-identity.md) §3) | VERIFIED / OBSERVED |
| Promulgation | 공포일자, 공포번호 (+ 공동부령 공포번호); 발령일자, 발령번호 for rules | `date`, `ancYd`, `nb`, `ancNo`, `LD`, `LN`; `prmlYd` | `promulgation_date`, `promulgation_no` | VERIFIED |
| Amendment type | 제개정구분(명); `rrClsCd` | `rrClsCd` | `amendment_type` | VERIFIED |
| Repeal | `rrClsCd` 300204 폐지, 300207 일괄폐지, 300210 타법폐지; `delHst` for withdrawn records | `rrClsCd`; `delHst` | `is_repeal` | VERIFIED (doc); never observed live |
| Article address | 조문번호, 조문가지번호, 조문여부 (조문 / 전문), 조문키; renumbering via 조문이동이전/이후 | `JO` (4+2), `HANG`, `HO`, `MOK` | `provision_key` (e.g. "제73조"); `unit_kind` = `heading` for 전문 rows | VERIFIED + OBSERVED |
| Addenda | 부칙공포일자, 부칙공포번호, 부칙내용, 부칙키 | none (inside the body) | `addenda[]` with `kind`; `has_transitional_provisions` | VERIFIED + OBSERVED |
| Titles | 법령명한글, 법령명약칭, 제명변경여부; `lsAbrv` | `query`, `LM` | `official_title`, `short_titles`, `former_titles` | VERIFIED (doc). Former titles come from the law.go.kr 연혁 view, not from an API field (LI §3) |
| Decisions | 판례일련번호 / 사건번호 / 선고일자; 헌재결정례일련번호 / 종국일자; 법령해석(례)일련번호 / 안건번호 / 해석일자; 행정심판례일련번호 / 의결일자 | `ID`; `nb`, `itmno`; date ranges | out of scope for the [06](06-temporal-law-and-source-identity.md) resolver | VERIFIED |

### 2.4 What Waymaker does with the API today (`fc896c2`)

1. **Targets.** Non-test backend code references:
   * `law`, list and body [CODE backend/services/law_tools.py:776-777, :921-933];
   * `admrul`, list only [CODE law_tools.py:1046-1047];
   * `lstrm`, list only [CODE law_tools.py:1074-1075];
   * `prec`, list and body [CODE backend/services/precedent_sources.py:60;
     backend/services/legal_evidence.py:898-905];
   * `decc`, as an env-overridable default [CODE legal_evidence.py:75, :90].

   `KoreanLawClient` is never instantiated outside tests. The owner's branch
   `fix/waymaker-qa-2026-10-16` adds no target. VERIFIED (OA §8 item 1, OA-V
   claim 14; `git grep` re-run at `fc896c2` on 2026-10-20).
2. **Documented targets are treated as unknown.**
   `precedent_sources.SOURCE_FAMILY_LIST_TARGETS` maps `administrative_appeal`,
   `legal_interpretation` and `constitutional_decision` to `None`, with the
   comment "the official target is NOT confirmed yet and we refuse to guess one"
   [CODE backend/services/precedent_sources.py:62-69]. The official guides do
   document `decc`, `expc` and `detc` (§2.2). `legal_evidence.py:70-77` likewise
   calls `decc` "NOT publicly confirmed". Both comments are stale. VERIFIED (my
   re-read at `fc896c2`; the `legal_evidence` comment is also OA-V V-G).
3. **No version pinning.**
   * The public law result `id` is the 법령일련번호 (MST) when present, and the
     stable 법령ID is not exposed [CODE backend/paradiso_backend.py:6850].
   * `sourceUrl` is `https://www.law.go.kr/법령/<name>`, which shows whatever
     version is current when the user clicks. When the title is empty or starts
     with "(", it falls back to `LSW/lsAstSc.do?menuId=1`
     [CODE paradiso_backend.py:6830-6835].
   * No request sends `efYd`. The live 출입국관리법 search returned
     `lifecycleStatus: ""` (OBSERVED, B2).
4. **Latent ID/MST mix-up.** `get_law_detail` sends any all-digit identifier as
   `MST` [CODE law_tools.py:921-927]. Official 법령IDs are all-digit,
   zero-padded strings (`009682`, `001971`, `010719`), so a 법령ID that reaches
   this function would be sent as `MST=<법령ID>`. The caller passes
   `law_serial_no or law_id` [CODE backend/services/law_grounding.py:349-360], so
   the bug fires only when a search candidate lacks a 법령일련번호. INFERRED; low
   likelihood; never exercised live.
5. **Broken precedent links.**
   * Every precedent list `sourceUrl` has the shape
     `https://www.law.go.kr/DRF/lawService.do?target=prec&ID=<n>&type=HTML`,
     with the OC removed (B3). Fetched as-is, it returns HTTP 200 and the page
     "사용자인증에 실패하였습니다" (OA-V R4). OBSERVED.
   * The detail `sourceUrl` is `LSW/precSc.do?menuId=7&query=<serial>`, a site
     search on the serial number (B4), from the fallback at
     [CODE paradiso_backend.py:6838-6843]. That it matches nothing is INFERRED
     (not fetched).
6. **OC redaction.** List families return `…상세링크` and `조문링크` fields that
   echo the caller's OC (§3.1 item 11). The backend redacts them
   [CODE paradiso_backend.py:6811-6813; law_tools.py:242], and no OC appeared in
   the B2–B4 responses. OBSERVED. The OC risk in transport is covered in
   [15](15-security-and-deployment.md).
7. **Failure read as absence.** The missing-OC JSON envelope is not flagged as
   an error. `parse_law_search_response` returns `law_api_no_results` for it
   (OA-V L; detail in §3.2). This breaks [07 §2](07-evidence-verification-design.md)
   invariant 1 ("Failure is not absence"). The uncommitted fixes F1–F8
   ([research-notes/law-stack-fixes.md](research-notes/law-stack-fixes.md)) do
   not touch `_official_error_info` or the ID/MST branch (my `git diff` of the
   worktree, 2026-10-20). F6 does stop `legal_evidence` from caching
   official-error bodies.

## 3. Polymorphic JSON, undocumented keys and failure shapes

### 3.1 Shapes in the documented samples

Sample calls S1 (`eflaw` list JSON), S2 (`law` body JSON, `MST=261457`,
건강가정기본법) and S3 (`lsJoHstInf` by article XML, `ID=001971&JO=000500`,
국민건강보험법 제5조) are listed in §6.1. I re-parsed all three captures offline on
2026-10-20 and every count below reproduced (§6.2).

| # | Shape | Evidence | Status | Consequence for an adapter |
|---|---|---|---|---|
| 1 | `항` is an **object** for one paragraph and an **array** for several | S2: list 25, dict 1, absent 21 | OBSERVED | Normalize to a list before iterating |
| 2 | `호` was only ever an array in S2 (9 of 9) | S2 | OBSERVED as array; the object form is INFERRED from `항` | Treat it like `항` anyway |
| 3 | Every leaf value is a JSON string, including fields the guides type as "int" | S2: 852 of 852 leaves are `str` | OBSERVED | Parse numbers and dates explicitly |
| 4 | `기본정보.법종구분` is a nested object (`content` + `법종구분코드`), not a flat string | S2 | OBSERVED | — |
| 5 | `조문.조문단위[]` mixes articles and 편/장/절 headings: `조문여부` = `조문` (42) or `전문` (5) | S2 | OBSERVED | Filter `전문` before counting or addressing articles; bundles carry `unit_kind: "heading"` rows so that adapters can prove they do |
| 6 | The `별표` key is absent when the law has no annex | S2 | OBSERVED | Absence of the key is not a parse failure |
| 7 | `법령키` (19 chars) = 법령ID (6) + 공포일자 (8) + 공포번호 (5), e.g. `0096822024032620417` | S2. It is listed as a field ("법령키 \| int") on `lawjosub`, `eflawjosub` and `couseLs`, but its composition is documented nowhere | OBSERVED | Derivable; do not use it as the version key (it lacks the 시행일) |
| 8 | `부칙키` (13 chars) = 부칙공포일자 + 부칙공포번호. `조문키` (7 digits) = article (4) + branch (2) + 1 digit: `0001000` was a 전문 row and `0001001` an article. `부서키` sits under `기본정보.연락부서.부서단위`. None of the three keys is on any of the 57 guides | S2 | OBSERVED; the meaning of the 7th 조문키 digit is INFERRED | Do not depend on undocumented keys for identity |
| 9 | The `eflaw` list carries `resultCode` "00", `resultMsg` "success" and `numOfRows` "20", which its guide does not list. The unfiltered `totalCnt` was "169418" (현행 + 연혁 + 예정). On page 1, 현행연혁코드 was 연혁 18 times and 현행 twice | S1 | OBSERVED | Read the status envelope when present; never require it |
| 10 | **`eflaw` list rows are keyed by (MST, efYd):** MST 140323 appears twice, with efYd 20130823 and 20130522, both 공포 20130522 | S1 | OBSERVED | A version store keyed only by 법령일련번호 would merge two effective-date states |
| 11 | `법령상세링크` = `/DRF/lawService.do?OC=<caller OC>&target=eflaw&MST=<n>&type=HTML&mobileYn=&efYd=<n>`. `mobileYn` is documented, but only on the mobile guides. The S3 `조문링크` is a relative `/DRF/lawService.do?OC=…` path with no `mobileYn` | S1, S3 | OBSERVED with the echoed sample OC; that a real OC is echoed too is INFERRED | Strip OC before storing or showing any upstream link |
| 12 | The `lsJoHstInf` chain is not one row per version. MST 59612 appears twice: once with 조문변경일 = 공포일자 19990208, once with 시행일자 20000101. MSTs 193394 and 201168 share 조문변경일 20180701. 조문변경일 equalled 시행일자 in 11 of 12 rows | S3 | OBSERVED | Key on (법령ID, JO, MST, 조문변경일), and read 조문변경일 as an effective date (INFERRED from one sample) |
| 13 | The `prec` list gives 선고일자 as "2023.03.13" and the detail as "20230313". The detail `summary` contains raw `<br/>` | B3/B4, through Waymaker | OBSERVED | Normalize both date forms; strip markup |
| 14 | Parameter traps: `nw` is inverted between `eflaw` and `admrul`; `ID`/`LID`/`MST` are inverted between `law` and `admrul`; the `prec` `JO` is a law name; `delHst` vs "datDel"; guide type columns contain errors (`lsJoChgListGuide`, the `expc` `inq` cell) | guides | VERIFIED (doc) | Encode each target's parameter meaning separately; never share one "id" field across families |

### 3.2 Failure envelopes

[07 §2](07-evidence-verification-design.md) invariant 1 requires every failure to
map to `LookupStatus.UNAVAILABLE_*` or `UPSTREAM_ERROR`, and never to
`NOT_FOUND`. The mapping column below is my reading of that rule against the
contract enum [CODE experiments/waymaker-ai/waymaker_ai/contracts.py:306-315]
(INFERRED).

| Case | Observed response | Status | Contract mapping |
|---|---|---|---|
| JSON list without OC (OA-V R5: `lawSearch.do?target=law&type=JSON&query=test`, the backend's own probe path, `paradiso_backend.py:7432`) | **HTTP 200**, `application/json`, 170 B: `{"result": "필수입력요소 검증에 실패하였습니다.", "msg": "필수 입력값이 존재하지 않습니다. 요청 URL을 확인해 주세요."}`. No `resultCode` | OBSERVED | `UNAVAILABLE_AUTH`, or `UPSTREAM_ERROR` when the cause is unclear; bundle `raw_body_kind: "official_error"`. The evaluation fake replays this exact envelope [CODE experiments/waymaker-ai/waymaker_ai/evaluation/fake_drf.py:74-77, :96, :105] |
| HTML body without OC (OA-V R4: the B3 precedent link) | **HTTP 200**, `text/html`, 1,415 B: "사용자인증에 실패하였습니다 / OpenAPI 사용자 인증에 실패하였습니다. 접속하신 해당 기관에 문의 바랍니다." | OBSERVED | `UNAVAILABLE_AUTH` if recognized, else `UNAVAILABLE_PARSE` (`raw_body_kind: "html"`) |
| Invalid or unregistered OC, unregistered IP, unapproved target, bad parameter | Not observed: testing it needs a real OC, and none may be used | UNVERIFIED | — |
| Rate limiting (HTTP 429) or overload | Never observed; no quota is published | UNVERIFIED | `UNAVAILABLE_RATE_LIMITED` |
| Repo fixture `resultCode 99 / "ERROR invalid request"` | Its own README labels it synthetic [CODE backend/tests/fixtures/law_api_shapes/README.md:1-8] | UNVERIFIED as an official shape | Keep it labelled synthetic |

Both observed failures arrive with HTTP 200, so a status-code check catches
neither.

Waymaker's detector `_official_error_info` flags:
* an error-code key (`error`, `errorcode`, `errcode`, `resultcode`, `code`) with
  a non-success value;
* a `message`/`msg` value containing words such as "error", "오류", "invalid",
  "fail", "인증" or "권한".

It never reads `result`, and the observed `msg` contains none of those words
[CODE backend/services/law_tools.py:510-533]. Run locally on the R5 body,
`_official_error_info` returned False and `parse_law_search_response` returned
`law_api_no_results` (OA-V L). OBSERVED.

## 4. Terms of use and copyright (OA §6)

### 4.1 What the two official pages say

The pages are open.law.go.kr [DOC https://open.law.go.kr/LSO/information/guide.do]
and law.go.kr 법적효력/저작권 [DOC https://www.law.go.kr/lawPetitionForm.do?menuId=13&subMenuId=79].
Both are VERIFIED. The verifier showed that **the two pages do not state an
identical policy**.

| Statement (paraphrased) | open.law.go.kr | law.go.kr |
|---|---|---|
| Copyright in 법제처 law information belongs to 법제처, to the extent the 저작권법 protects it | yes | — |
| Open to everyone under public-data policy, **free use including commercial use** | yes | yes (공공데이터법, including for profit) |
| Excluded: 정보공개법 제9조 non-disclosure information, and information containing third-party rights without a proper licence (공공데이터법 제17조) | — | yes |
| Use in good faith, without infringing the public interest or others' rights | yes | — |
| Service may be controlled for: a breach threatening the centre's functions, serious third-party infringement, misuse for crime, or to prevent errors, forgery and alteration | yes | yes |
| **Criminal-liability warning** citing 「저작권법」 제137조 and 제138조, for (a) forging or altering law information and providing it or submitting it as evidence, and (b) using or providing it **without stating the source, or naming an agency other than 법제처 as the source** | yes | forgery and alteration only; the attribution item is absent, and the old contact block is commented out |
| **No legal effect** ("법적 효력이 없으므로, 참고자료로 활용"); the authoritative text is in the 관보 and similar official gazettes | absent (0 hits for 효력 on `guide.do` and `service.do`) | yes |
| Translations are unofficial and the Korean text prevails ("외국어번역 법령정보는 공식적 효력이 있는 번역물이 아니므로 참고로만") | absent | yes |
| The 지식베이스 is reference-only | absent | yes |

### 4.2 저작권법 articles

Read on law.go.kr; the current version is 저작권법 [시행 2026. 8. 11.]
[법률 제21336호, 2026. 2. 10., 일부개정] [DOC https://www.law.go.kr/법령/저작권법/제7조].
VERIFIED.

* **제7조 (보호받지 못하는 저작물).** The Act does not protect:
  1. the Constitution, laws, treaties, orders, ordinances and rules;
  2. state or local 고시·공고·훈령 and similar;
  3. court judgments, decisions and orders, and decisions in 심판 or 행정심판
     procedures;
  4. state or local compilations or translations of 1–3;
  5. news reports that merely convey facts.
* **제24조의2 (공공저작물의 자유이용).** Works that the state or a local
  government made and published in the course of duty, or whose economic rights
  it holds in full under a contract, may be used without permission. Exceptions:
  national security, privacy or trade secrets, legally restricted information,
  and registered state property.
* **제37조 (출처의 명시).** ① Anyone using a work under "이 관" must state its
  source. The exceptions are 제26조, 제29조–제32조, 제34조 and 제35조의2–제35조의4;
  제24조의2 is not among them. ② The source must be stated in a reasonable way,
  including the author's name where one is shown. VERIFIED (WebFetch). That
  제24조의2 sits in the same 관 is INFERRED from the article numbering.
* **제137조:** up to 1 year or KRW 10M. **제138조:** a fine up to KRW 5M; item 2
  covers failing to state the source in breach of 제37조.

### 4.3 Consequences for Visable

All of the following is INFERRED and is not legal advice.

* Statute text, 행정규칙 (고시·훈령), court and Constitutional Court decisions,
  and 행정심판 decisions fall under 제7조 items 1–3. Copyright does not restrict
  their redistribution, commercial use or use in model training.
* 법령해석례, ministry interpretations and MOJ manuals are not clearly listed in
  제7조. They most plausibly fall under 제24조의2, which makes attribution a
  **statutory** duty (제37조, enforced by 제138조 item 2), not only a platform
  expectation.
* Editorial value-add that is not an official publication (summaries,
  translations, 지식베이스 relations) is not covered by 제7조 item 4 and must be
  checked separately.
* Whatever copyright says, two platform rules apply:
  * **Attribution.** Every stored or surfaced official text states "출처: 법제처
    국가법령정보센터 (law.go.kr)" and carries its retrieval provenance (URL,
    `retrieved_at`, sha256 of the capture). This is the mission rule, enforced
    for datasets in [11](11-dataset-governance.md).
  * **Anti-forgery.** Altered text is never presented as official. Synthetic
    fixtures use fictional law names and never carry a real law ID.
* The API text has no legal effect. An answer must not present it as
  authoritative over the 관보, and the existing disclaimers stay. `elaw`
  translations are display-only reference.

### 4.4 AI and model-training use

* **What the pages say.** No page read on open.law.go.kr or law.go.kr mentions
  AI training, 인공지능, 학습 or 공공누리. There were 0 hits on `guide.do`,
  `service.do`, `openApiManual.do`, `noticeList.do`, `main.do`, the law.go.kr
  policy page, the law.go.kr main page and the Q&A pages. VERIFIED (absence on
  those pages).
* **This is not evidence that 법제처 is silent on AI.**
  * It runs the "지능형 법령검색" targets `aiSearch` and `aiRltLs`.
  * It issued a press release titled "법제처, 법령정보 제공을 확대해 리걸테크 기업
    지원한다", dated 2024-06-21 [WEB https://www.korea.kr/briefing/pressReleaseView.do?newsId=156637074,
    accessed 2026-10-19]. Only the title and date were readable.
  * Search summaries point to 2025 moleg.go.kr releases on machine-readable
    interpretation and 재결례 data. UNVERIFIED: the moleg.go.kr page returned
    "page not found".
* **The 공공누리 AI type.** A 문화체육관광부 press release titled "인공지능 학습에
  자유롭게 활용 가능한 공공누리 유형 신설", dated 2026-01-28 and issued by
  저작권산업과 [WEB https://www.mcst.go.kr/site/s_notice/press/pressView.jsp?pSeq=22219,
  accessed 2026-10-19], announces a new 공공누리 type. VERIFIED for the title,
  date and issuing unit.
  * Its conditions are in attachments (.hwpx 464 KB / .pdf 344 KB) that were
    not downloaded, because file downloads need the user's permission. **The
    conditions are UNVERIFIED.**
  * News describes a "제0유형" and an "AI유형" (search summaries only; UNVERIFIED).
* **Labelling.** Nothing indicates that 법제처 has labelled its law data with any
  공공누리 type (UNVERIFIED).
* **Net position.** For 제7조 material, copyright is not the constraint on
  training, but attribution and anti-forgery still apply. For non-제7조 material,
  AI-training licence terms are unresolved (INFERRED). See [11](11-dataset-governance.md).

## 5. Alternative official sources (OA §9; LI §1)

| Source | API? | Evidence | Status |
|---|---|---|---|
| data.go.kr 법제처 datasets (e.g. 15058878 현행법령 본문 조항호목) | Listed as "LINK" to open.law.go.kr; no separate endpoint found; 이용허락범위 제한 없음 | [LIVE data.go.kr/data/15058878/openapi.do, 200] | VERIFIED |
| data.go.kr 외교부_국가·지역별 재외공관 정보 (15075354), already referenced by the repo [CODE assets/js/preview/preview-data.js:181] | REST, free, 이용허락범위 제한 없음. Development auto-approval with traffic 10,000; production needs 심의승인; traffic can rise once a 활용사례 is registered. Error code 22 = "일일 호출 허용량을 초과" | [LIVE data.go.kr/data/15075354/openapi.do, 200] | VERIFIED (original pass only; not re-checked by the verifier) |
| data.go.kr 외교부_국가별 사증 면제협정 체결현황 (15099235), referenced by the repo [CODE assets/js/preview/preview-data.js:187] | A file dataset, not an API | page not fetched | UNVERIFIED |
| HiKorea (hikorea.go.kr) | No API mention on `Main.pt` (0 hits for OpenAPI, 공공데이터개방 or data.go.kr). The repo scrapes public board pages: `BoardDataListR.pt`, `BoardNtcDetailR.pt`, `InfoDatail.pt` | [LIVE Main.pt, 200]; [CODE git grep of hikorea URLs] | No-API is INFERRED; UNVERIFIED as an official statement |
| immigration.go.kr / moj.go.kr | No API mention on the immigration.go.kr index (0 hits) | [LIVE immigration/index.do, 200] | UNVERIFIED |
| visa.go.kr | Referenced by the repo; not checked | [CODE git grep] | UNVERIFIED |
| law.go.kr Korean article URLs (`/법령/<name>/제N조`) | A human-facing page that loads an `lsSideInfoP.do` iframe; no OC needed | [LIVE 저작권법 제7조, 200] | VERIFIED as public; not an API contract |
| law.go.kr web views used for §7: `/법령/<name>` (its iframe names the current `lsiSeq` + `efYd`), `LSW/lsInfoR.do` (consolidated body with hidden `lsId`, `lsiSeq`, `ancYd`, `ancNo`, `efYd`, `nwYnValue`, plus every 부칙), `LSW/lsHstListR.do` (연혁 rows, newest 시행일 first, with pending rows flagged `alt="앞으로 시행될 법령"`), `LSW/admRulScListR.do`, `LSW/admRulLsInfoP.do` | No key or OC; 99 GETs, all 200 (§6.1). The meaning of the `p6` filter ("1:연혁, 2:시행예정, 3:현행") comes from a site JS comment (README-ONLY). On `admRulLsInfoP`, `pEfYd` holds the **발령일**, not the 시행일 | [LIVE LI §1, LI-V] | OBSERVED. These are not an API contract and can change without notice. LI §7 recommends `lsHstListR.do` (about 20 KB per law) as a key-free source monitor |

## 6. Live checks performed

### 6.1 Network requests (all on 2026-10-19; times UTC)

Official API research (OA §0, §7):

| # | Request | Result |
|---|---|---|
| Index | GET `https://open.law.go.kr/LSO/openApi/guideList.do` | 200, 62,520 B, "총 191 건", 195 distinct guide names |
| Guides | 55 × GET `guideResult.do?htmlName=<name>`, 1 s apart (the page's own form POSTs; GET works) | 55 × 200 |
| Usage and policy | `information/service.do`, `information/guide.do`, `openApi/openApiManual.do`, `support/noticeList.do`, `lab/sampleCode.do`, `lab/supportCase.do`, 5 × `supportCaseView.do`, `lab/lawListSupport.do`. OA §7 counts 18 open.law.go.kr info/support pages fetched in all, including the 5 Q&A views | 200, except `openApi/cuAskList.do`, `lab/ipErrorCheck.do` and `lab/selfDiagnosis.do` (302 to login) and `support/faq.do` (404) |
| law.go.kr policy and 저작권법 | `lawPetitionForm.do?menuId=13&subMenuId=79`; `main.html`; 5 article-page requests (`/법령/저작권법/제7조` → `lsSideInfoP.do?lsiSeq=283335&joNo=0007…`; same pattern for 제24조의2, 제137조, 제138조) | 200 |
| S1 03:56:40 | Documented sample (lsEfYdListGuide #3): `http://www.law.go.kr/DRF/lawSearch.do?OC={sample}&target=eflaw&type=JSON` | 200, `application/json;charset=UTF-8`, 16,895 B |
| S2 03:57:04 | Documented sample (lsNwInfoGuide #3): `…/lawService.do?OC={sample}&target=law&MST=261457&type=JSON` | 200, JSON, 71,566 B |
| S3 03:57:36 | Documented sample (lsJoChgListGuide #1): `…/lawService.do?OC={sample}&target=lsJoHstInf&ID=001971&JO=000500&type=XML` | 200, `text/xml;charset=UTF-8`, 8,276 B |
| B1 03:57:55 | Waymaker `GET https://web-production-14f9a.up.railway.app/health` | 200, 0.36 s. `build.commit` 0713370…, `law_api_configured` true, `law_api_credential_source` "LAW_API_OC", `law_grounding_effective_mode` "enabled" (booleans and labels only) |
| B2 03:58:02 | `…/api/legal/laws/search?q=출입국관리법` | 200, 0.94 s. 3 results: 290729 / 290501 / 289833, with `lifecycleStatus` and `hierarchyLevel` empty |
| B3 04:00:01 | `…/api/legal/precedents/search?q=출입국관리법` | 200, 1.02 s, count 9, DRF `sourceUrl` without OC |
| B4 04:00:16 | `…/api/legal/precedents/detail?id=234321` | 200, 1.23 s. `id` became "2021도3652"; `decisionDate` "20230313"; `detailAvailable` false |
| Other pages | 2 data.go.kr dataset pages, 1 data.go.kr search page (JS-rendered; nothing could be parsed), HiKorea `Main.pt`, the immigration.go.kr index | 200. One WebFetch of 15058878 timed out at 60 s; curl returned 200 |
| Web | WebSearch ×3; WebFetch ×2 of MCST releases (pSeq 22681, dated 2026-09-03, which mentions only 공공누리 0유형 for its own text; pSeq 22219); WebFetch ×1 of data.go.kr (timed out) | Used as pointers only |

Official API verification pass (OA-V):

| # | Request | Result |
|---|---|---|
| R1 04:25:02Z | `guideList.do` | 200, byte-identical |
| R2–R3 04:25:09–10Z | `mobLsListGuide` / `mobLsInfoGuide` | 200 / 200 (23,954 B / 17,446 B) |
| R4 04:30:40Z | `https://www.law.go.kr/DRF/lawService.do?target=prec&ID=234321&type=HTML` (the B3 link, no OC) | 200, `text/html`, 1,415 B, auth-failure page |
| R5 04:30:50Z | `https://www.law.go.kr/DRF/lawSearch.do?target=law&type=JSON&query=test` (no OC) | 200, `application/json`, 170 B, `{result, msg}` |
| R6 04:33:22Z | data.go.kr 15058878 | 200, 178,762 B |
| W | WebFetch ×2 of the 저작권법 제37조 article page; ×1 each of mcst.go.kr pSeq=22219, korea.kr newsId=156637074 and a moleg.go.kr board URL ("page not found"); WebSearch ×2 | As recorded in §4 |
| L | Local run of the repo parser on the R5 body | `_official_error_info` False; `law_api_no_results` |

No sample-OC request was re-run, and no Waymaker GET was repeated, in the
verification pass.

Law identity research (LI §1, LI-V), all to `www.law.go.kr`, with no key, OC or
cookie:

| Pass | Window | Requests | Result |
|---|---|---|---|
| Original | 03:51:33–04:04:45Z, about 1.5 s apart | 60: 13 `/법령/<name>` routes, 1 `lsInfoP.do`, 15 `lsHstListR.do`, 19 `lsInfoR.do` bodies (including 시행예정 versions), 8 `admRulScListR.do` searches, 1 `admRulLsInfoP.do`, 2 JS files (`lsPopLayer.js`, `ls.js`), 1 `admRulSc.do` shell | 60 × 200 (counts from `scratchpad/research/raw/requests.log`) |
| Verifier | 04:35:37–04:42:48Z, about 2 s apart | 39: 2 routes (출입국관리법, 형사소송법); 15 `lsHstListR.do` (all 15 laws); 8 `lsInfoR.do` (289833 at efYd 20260915 and 20270916, 290501, 290729, 291055, 276857, and 형사소송법 290189 twice); 9 `admRulScListR.do` (6 with the 현행+시행예정 filter `p6=2,3`, 3 with the 연혁 filter `p6=1`); 5 `admRulLsInfoP.do` | 39 × 200 (counts from `scratchpad/verifier/raw/requests.log`) |

Several commands failed with ENOSPC during the research passes, because the disk
was full. The notes record that each was re-run once space returned, that no
request was sent in the gaps, and that no result depends on a failed call
(OA §7, LI §1, LI-V).

### 6.2 Offline re-checks for this document (2026-10-20, no network)

* **Sample shapes.** I parsed the saved S1, S2 and S3 captures with the standard
  library under `python -I`. Every count in §3.1 reproduced. Capture hashes
  (sha256), under `scratchpad/apiguide/live/`:
  * `s1_eflaw_list.json`: `b650196dc13774e732d05b575169dd003e48a926f54eff5df22ecdf5d5a49a6f`
  * `s2_law_detail.json`: `c5fb59c02c4b6079e89e60bc27b18ce18cb6572315e58e810af5dd4d1894ad75`
  * `s3_johst.xml`: `936cf015b92709e9c515ffd8951728c0bdd2fdd85e1a31593df99e4b7a8ef314`
* **Seed vs saved 연혁 pages.** For each of the 15 statute records I parsed the
  verifier's saved `lsHstListR.do` page and checked three things:
  * the 현행 (Y) row matches the seed's `version_id`, 공포일자, 공포번호, 시행일자
    and 제개정;
  * the rows above it match `pending_versions`;
  * the row count matches LI §3.

  **15 of 15 match.** VERIFIED (re-parse of saved web captures).
* **Administrative-rule IDs.** The saved `admRulLsInfoP.do` pages give `admRulId`
  27428, 2109471, 2037546, 2075585 and 2090230, and `pAncNo` values matching the
  seed's 발령번호. 5 of 5 agree with LI-V.
* **Code.**
  * `git grep` of DRF `target` values in non-test backend code at `fc896c2`
    (§2.4).
  * `git diff --stat 0713370 fc896c2` over every cited file: empty.
  * Re-read at `fc896c2`: `law_tools.py:508-535, 918-928, 1040-1078`;
    `legal_evidence.py:68-95`; `precedent_sources.py:55-76`;
    `paradiso_backend.py:6826-6852`; `scripts/status_guidance/author_rules.py:314-319, 339`;
    `data/status-guidance-202609.json:558-567, 1877`.
* **Clean-up.** The temporary scripts were written under the scratchpad and
  deleted afterwards.

### 6.3 Not tested

* **Error bodies** for an invalid or unregistered OC, an unregistered IP, an
  unapproved target or a bad parameter. Testing them needs a real OC, and none
  may be used.
* **Rate-limit behaviour.** No 429 was seen, and no quota is published.
* **Documentation gaps:**
  * the 시행예정 label in 현행연혁코드;
  * whether `ID=` on the `law` body returns the current version;
  * the `elaw` body response fields.
* **Code tables:** `org`, `knd`, `natCd`, 분야 and `rltClsCd`, and the 법무부
  `org` code.
* **Policy:** whether IP and referer binding is still enforced, and how it
  interacts with Railway egress; which APIs are "상업적 이용이 불가능"; the
  공공누리 AI-type conditions, and whether 법제처 data carries any 공공누리 label.
* **Unopened guides.** The ~138 guides never opened, including the
  `specialDecc*` and `cgmExpcMoleg*` targets and the `okaCgmExpc` body; also the
  behaviour of the mobile `PD`/`PN`/`BD`/`BT`/`BN`/`BG` parameters.
* **Untested claims:** `delHst` live; the "실시간 연계" freshness claim; that a
  real OC is echoed in `…상세링크`; whether the B4 `precSc.do` link matches
  anything.
* **Laws and rules not covered:**
  * 재한외국인 처우 기본법 (+시행령);
  * 제주특별법 (lsiSeq 279611 in an audit note);
  * 외국인투자촉진법;
  * the HiKorea `LawLink.pt` directory;
  * the rule-level 연혁 of the investment and marriage 고시;
  * the 시행령 omnibus decree 36728호's own 단서;
  * which 별지 서식 국적법 시행규칙 1161호 changed.
* **Other data sources:** data.go.kr 15099235 and visa.go.kr. 15075354, HiKorea
  and immigration.go.kr were not re-checked by the verifier.

## 7. Official identities as of 2026-10-19

Read from law.go.kr public pages on 2026-10-19 (`retrieved_at` 2026-10-19 on
every seed record). This table is the machine-readable seed rendered for review.

URL patterns:
* `https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=<version>&efYd=<시행일>`
* `https://www.law.go.kr/LSW/admRulLsInfoP.do?admRulSeq=<version>`

Status: the seed value, then the evidence behind it.

### 7.1 Statutes, decrees and rules

| # | Exact official title | Family | 법령ID | Version (lsiSeq) | 공포일 | 공포번호 | 시행일 | Amendment | Pending versions (lsiSeq @ 시행일) | 연혁 rows | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 출입국관리법 | statute | 001707 | 290729 | 2026-08-04 | 법률 제21857호 | 2026-10-02 | 타법개정 | none | 61 | VERIFIED_WEB; LI-V claim 1; re-checked 2026-10-20 |
| 2 | 출입국관리법 시행령 | enforcement decree | 005256 | 290501 | 2026-09-29 | 대통령령 제36728호 | 2026-10-02 | 타법개정 | none | 96 | VERIFIED_WEB; LI-V claim 2; re-checked |
| 3 | 출입국관리법 시행규칙 | enforcement rule | 008494 | 289833 | 2026-09-15 | 법무부령 제1125호 | 2026-09-15 | 일부개정 | **289833 @ 2027-09-16** (same promulgation; 제73조) | 93 | VERIFIED_WEB; LI-V claim 3; re-checked |
| 4 | 난민법 | statute | 011546 | 188376 | 2016-12-20 | 법률 제14408호 | 2016-12-20 | 일부개정 | none | 3 | VERIFIED_WEB; LI-V claim 11; re-checked |
| 5 | 난민법 시행령 | enforcement decree | 011878 | 273705 | 2025-09-16 | 대통령령 제35747호 | 2025-09-19 | 타법개정 | none | 10 | VERIFIED_WEB; LI-V claim 11; re-checked |
| 6 | 난민법 시행규칙 | enforcement rule | 011885 | 266929 | 2024-12-03 | 법무부령 제1084호 | 2024-12-03 | 일부개정 | none | 8 | VERIFIED_WEB; LI-V claim 11; re-checked |
| 7 | 국적법 | statute | 001435 | 244609 | 2022-09-15 | 법률 제18978호 | 2022-10-01 | 일부개정 | **286415 @ 2026-12-03** (법률 제21725호, 공포 2026-06-02) | 20 | VERIFIED_WEB; LI-V claim 6; re-checked |
| 8 | 국적법 시행령 | enforcement decree | 002922 | 246165 | 2022-12-20 | 대통령령 제33082호 | 2022-12-20 | 일부개정 | none | 26 | VERIFIED_WEB; LI-V claim 7; re-checked |
| 9 | 국적법 시행규칙 | enforcement rule | 006766 | 291055 | 2026-10-02 | 법무부령 제1161호 | 2026-10-02 | 일부개정 | none | 24 | VERIFIED_WEB; LI-V claim 8; re-checked |
| 10 | 재외동포의 출입국과 법적 지위에 관한 법률 (약칭 재외동포법) | statute | 001999 | 268553 | 2025-01-21 | 법률 제20677호 | 2025-07-22 | 타법개정 | none | 24 | VERIFIED_WEB; LI-V claim 11; re-checked |
| 11 | 재외동포의 출입국과 법적 지위에 관한 법률 시행령 | enforcement decree | 004662 | 284843 | 2026-03-24 | 대통령령 제36220호 | 2026-03-24 | 타법개정 | none | 29 | VERIFIED_WEB; LI-V claim 11; re-checked |
| 12 | 재외동포의 출입국과 법적 지위에 관한 법률 시행규칙 | enforcement rule | 008011 | 267499 | 2024-12-24 | 법무부령 제1087호 | 2025-02-01 (main body 2025-01-01) | 일부개정 | **289831 @ 2027-09-16** (법무부령 제1124호, 공포 2026-09-15) | 23 | VERIFIED_WEB; LI-V claim 10; re-checked |
| 13 | 외국인근로자의 고용 등에 관한 법률 (약칭 외국인고용법) | statute | 009542 | 276857 | 2025-10-01 | 법률 제21065호 | 2025-10-01 | 타법개정 | **286817 @ 2026-12-10** and **286817 @ 2027-06-10** (법률 제21786호, 공포 2026-06-09) | 23 | VERIFIED_WEB; LI-V claim 9; re-checked |
| 14 | 외국인근로자의 고용 등에 관한 법률 시행령 | enforcement decree | 009657 | 244037 | 2022-08-02 | 대통령령 제32844호 | 2023-02-03 | 일부개정 | none | 37 | VERIFIED_WEB; LI-V claim 11; re-checked |
| 15 | 외국인근로자의 고용 등에 관한 법률 시행규칙 | enforcement rule | 009698 | 271599 | 2025-06-02 | 고용노동부령 제442호 | 2025-06-02 | 일부개정 | none | 29 | VERIFIED_WEB; LI-V claim 11; re-checked |

"Re-checked" means matched on 2026-10-20 against the verifier's saved 연혁 pages
(§6.2). Every `/법령/<name>` route in `docs/source-laws/law_sources_2026_05.json`
that was tested resolved to the row above (LI §3). VERIFIED.

### 7.2 Administrative rules

| # | Exact official title | Family | 행정규칙ID (admRulId) | Version (admRulSeq) | 발령일 | 발령번호 | 시행일 | Amendment | Pending versions | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| 16 | 재외동포(F-4) 자격의 취업활동 제한범위 고시 | administrative rule | 2090230 | 2100000275060 | 2026-02-12 | 법무부고시 제2026-65호 | 2026-02-12 | 폐지제정 | seed `null`: one row under the 현행+시행예정 filter (INFERRED none) | VERIFIED_WEB (search row + detail-page variables); LI-V claim 12; ID re-checked 2026-10-20 |
| 17 | 해외투자기업 기술연수생 등에 대한 사증발급인정서 발급 및 관리에 관한 훈령 | administrative rule | 27428 (LI-V; seed `law_id` null) | 2100000210583 | 2022-04-14 | 법무부훈령 제1414호 | 2022-04-14 | 일부개정 | seed `null` (INFERRED none) | VERIFIED_WEB (search row); LI-V claim 13; ID re-checked |
| 18 | 공익사업 투자이민제도 투자대상, 투자금액 등에 관한 기준 고시 | administrative rule | 2109471 (LI-V; seed null) | 2100000225532 | 2023-06-29 | 법무부고시 제2023-319호 | 2023-06-29 | 일부개정 | seed `null` (INFERRED none) | VERIFIED_WEB (search row); the amount Waymaker stores was not checked |
| 19 | 관광·휴양시설 투자이민제 대상지역 지정 절차 고시 | administrative rule | 2075585 (LI-V; seed null) | 2100000250386 | 2024-12-02 | 법무부고시 제2024-588호 | 2024-12-08 | 일부개정 | seed `null` (INFERRED none) | VERIFIED_WEB (search row) |
| 20 | 국제결혼 안내프로그램 이수 대상 및 운영사항 고시 | administrative rule | 2037546 (LI-V; seed null) | 2100000232904 | 2023-12-19 | 법무부고시 제2023-695호 | 2024-01-01 | 일부개정 | seed `null` (INFERRED none) | VERIFIED_WEB (search row); the "7개 국가" count was not checked |
| 21 | 제주특별자치도 무사증입국 불허국가 및 체류지역 확대허가 국가 (Waymaker's title) | administrative rule | — | — | — | Waymaker stores 법무부고시 제2022-189호 | Waymaker stores 2022-06-01 | — | — | **UNVERIFIED**: not found on law.go.kr (§8 item 12) |
| 22 | 외국인 결핵환자 사증발급 및 체류관리 지침 (Waymaker's title) | administrative rule | — | — | — | — | — | — | — | **UNVERIFIED**: not found on law.go.kr (§8 item 13) |

For administrative rules the seed's `promulgation_date` holds the 발령일. Take the
시행일 from the `admRulScListR` row, never from `pEfYd` (LI-V §1 correction). The
verifier found four `admRulId` values but did not write them into the seed. They
are shown here with their source, and the seed still has `law_id: null` for
rows 17–20.

### 7.3 Reading these identities (LI §2–§3, LI-V)

**Identity rules.** VERIFIED (web).
* `lsId` (법령ID) is stable across all amendments and spacing renames.
  출입국관리법 has been `001707` since 1963-03-05.
* `lsiSeq` is assigned once per **promulgation**.
* (lsiSeq, efYd) is one **시행일 version**. A promulgation whose 부칙 sets several
  dates appears as several 연혁 rows with the same lsiSeq: 289833 (§7.1 row 3),
  286817 (row 13), 267499 (row 12, @20250101 and @20250201), and 269943
  (법률 제20794호, @20250601 and @20251023).
* Some deferred provisions get **no** 연혁 row and appear only as an inline
  marker. Version 276857 of 외국인고용법 carries "[시행일: 2026. 1. 2.] 제4조제4항의
  개정부분 중 재정경제부에 관한 부분" inside the text.
* A host-law 부칙 that says "<단서 생략>" hides the amending law's provisos.

**Split effective dates in the latest amendments.** VERIFIED (text).
* **출입국관리법 시행규칙, 1125호.** "공포한 날부터 시행. 다만, 제73조의 개정규정은
  공포 후 1년이 경과한 날부터 시행". The 제73조 (수수료의 납부방법) texts compare
  as follows:

  | Text | 1호 | 2호 | 3호 | 가목 |
  |---|---|---|---|---|
  | In force (efYd 20260915) | 수입인지 or 전자결제 | 수입증지 or 전자결제 | 수입인지·현금·증표 | 외국인등록증 발급·재발급 fees in 현금 or 현금 납입 증표 |
  | From 2027-09-16 | adds 신용카드ㆍ직불카드; the 등록증 cash rule moves into a parenthesis | adds 신용카드ㆍ직불카드 | adds 신용카드ㆍ직불카드 | "삭제 <2026. 9. 15.>" |
* **외국인고용법, 법률 제21065호 (정부조직법).** In force from 공포 (2025-10-01),
  except the 재정경제부 provisions, which took effect 2026-01-02 (inline marker
  only).
* **외국인고용법 시행예정, 법률 제21786호.** 공포 후 6개월 = 2026-12-10, except
  제22조의2 (주거시설의 제공 등) and 제25조 (사업 또는 사업장 변경의 허용),
  which take effect 공포 후 1년 = 2027-06-10. Both matter for E-9 content.
* **외국인고용법 시행령, 대통령령 제32844호.** Promulgated 2022-08-02, but
  제13조의4제5호·제6호 took effect 2023-02-03, which is the current view. The
  latest-*promulgated* decree amendment, 대통령령 제33028호 (2022-12-06, 시행
  2022-12-11, lsiSeq 245799), is older in effect. **Choose the current version by
  시행일, never by 공포일.**
* **재외동포법 시행규칙, 1087호.** 2025-01-01, except 제11조제3항 and 별지
  제7호서식·제7호의2서식, which took effect 2025-02-01. The pending 1124호 has a
  single date, 2027-09-16.
* **출입국관리법, 21857호 (2026-10-02).** A single date. The verifier read the
  full 부칙 제1조 of 형사소송법 21857호 in the current 형사소송법 view (lsiSeq
  290189). None of its five deferred items is 부칙 제15조 <52>, the 출입국관리법
  amendment, whose clause is itself marked "<신설 2026. 9. 29.>".
  * Changed: 제4조②, 제4조의4③2, 제4조의6, 제29조의2① and 제85조② (검사 /
    공소청 wording).
* **출입국관리법 시행령, 36728호.** Its markers sit only in 제5조의2–제5조의4 and
  제93조. The omnibus decree's own 단서 was not checked.
* **Single-date 부칙:** 국적법 21725호 (공포 후 6개월), 국적법 시행령 33082, 국적법
  시행규칙 1161, 난민법 14408, 난민법 시행령 35747, 난민법 시행규칙 1084, 재외동포법
  20677 (with `<단서 생략>`), 재외동포법 시행령 36220, 외국인고용법 시행규칙 442.

**Former titles.** No law in scope was substantively renamed; every change was a
spacing normalization. VERIFIED unless marked.
* **출입국관리법:** 시행령 ← `출입국관리법시행령`; 시행규칙 ←
  `출입국관리법시행규칙` (both to 2004).
* **국적법:** 시행령 ← `국적법시행령` (to 1998); 시행규칙 ← `국적법시행규칙`
  (to 2006).
* **외국인고용법:** the trio ← the no-space forms (2003–2004).
* **재외동포법 (Act):** ← `재외동포의 출입국과 법적지위에 관한 법률`
  (2005-12-29 to 2007-07-13) ← `재외동포의출입국과법적지위에관한법률`
  (1999–2004).
* **재외동포법 시행령 and 시행규칙** (verifier dates):
  * The 시행령 kept its no-space form until the row promulgated 2007-02-28, and
    the "법적지위" spacing until the row promulgated 2016-01-22.
  * The 시행규칙 kept its no-space form until 2003-12-02, and "법적지위" until
    2009-05-28.
  * The seed records only the no-space form for these two. The middle variant is
    truncated in the 연혁 list ("…시…"), so its exact spelling is UNVERIFIED.
* **Administrative rules** (LI-V; not yet in the seed, whose `former_titles` is
  `null`):
  * The 훈령 was "해외투자기업 **산업연수생** 등에 대한 사증발급인정서 발급 및
    관리에 관한 **지침**" on 법무부훈령 제533호 (2005-11-30), 제644호 (2008-07-30)
    and 제753호 (2009-12-22). 제727호 (2009-09-01) reads "…등에 관한…". The
    current title starts with 제853호 (2012-02-13, 시행 2012-03-01).
  * The F-4 고시 has 폐지제정 predecessors 제2023-187호 (2023-05-01), 제2018-70호,
    제2015-29호 and 제2010-297호, and was first made by 제2009-499호 (제정). That
    one abolished "외국국적동포의 취업활동 제한범위에 대한 고시" (제2003-618호).

**Observations.** These are INFERRED from VERIFIED rows.
* No implementing 시행령 or 시행규칙 amendment has been published yet for the
  2026-12-03 국적법 change or the 2026-12-10 외국인고용법 change. Neither
  subordinate law shows a 시행예정 row.
* Three laws changed on 2026-10-02 (출입국관리법, its 시행령, and 국적법 시행규칙),
  after Waymaker's last law snapshot.

**Seen but not referenced by Waymaker:** 투자이민협의회 규정 (법무부훈령 제1553호,
2024-12-02) and 공익사업 투자이민 상담센터 설치 및 운영에 관한 규정 (법무부훈령
제917호, 2013-12-16, 제정) (LI §4).

## 8. Stale or mismatched Waymaker data

Source: LI §5–§6 and LI-V. The data was VERIFIED at `0713370`, and every file
below is unchanged at `fc896c2`. **Nothing here is fixed in this mission.**
`visa_data.json` is a protected file and must not be edited at all. The
status-guidance JSON files are generated, so they are fixed in
`scripts/status_guidance/author_rules.py` and regenerated
(`generated_by: scripts/build_status_coverage_manifest.py`). The fix routes are
LI §7's recommendations.

1. **시행규칙 제73조: future text labelled as current.** VERIFIED.
   * **Where:** the quote at `scripts/status_guidance/author_rules.py:339`, which
     generates `data/status-guidance-202609.json:558-567`. The record carries
     `effective "2026-09-15"`, `checked_on "2026-09-22"` and
     `review_state "CURRENT_TEXT_READ"`.
   * **What it says:** the quote follows the 2027-09-16 wording, with card
     payment added and 가목 dropped. A user-facing line at `:1877` says the
     등록증 fee is paid "현금 또는 현금 납입을 증명하는 증표(또는 카드·전자결제)"
     under 시행규칙 제73조 제1호.
   * **What is in force:** on 2026-10-19 the 2026-09-15 text applies. Under its
     가목, 외국인등록증 발급·재발급 수수료 are paid only in cash or a cash-payment
     receipt (§7.3).
   * **Runtime and impact:** the runtime reads this data
     (`backend/services/knowledge/adapters.py:56`, labelled UNREVIEWED). The
     effect on users is INFERRED. Counter practice may already accept cards,
     but the cited legal basis does not say so before 2027-09-16 (UNVERIFIED).
   * **Mitigating:** `data/form_schemas.json` already records the pending date on
     eight annex templates (e.g. `:780`, `:1556`) as `pendingAmendment:
     "법무부령 제1125호 (공포 2026-09-15, 시행 2027-09-16)"`. The date is known;
     it is just not linked to 제73조.
2. **출입국관리법 stored as `mst 272921, effective 2026-01-23`.** The current
   version is 290729 / 2026-10-02 (법률 제21857호). 272921 is 법률 제20992호
   (공포 2025-07-22, 시행 2026-01-23).
   * **Where:** `author_rules.py:316`; `data/status-guidance-202609.json:379, 395`
     (three article refs: 제35조, 제36조, 제87조); `data/guidance-rules-202609.json`;
     `backend/data/knowledge_deploy/status-guidance-202609.json`.
   * **Text impact:** the cited articles are textually unchanged, by the
     amendment markers, so only the version identity is stale. VERIFIED
     (marker-based).
3. **출입국관리법 시행령 stored as `mst 289697, effective 2026-09-15`.** The
   current version is 290501 / 2026-10-02 (대통령령 제36728호).
   * **Where:** `author_rules.py:317`; `status-guidance-202609.json:427` (four
     refs: 제40조, 제42조, 제44조, 제45조).
   * **Text impact:** 36728호's markers sit only in 제5조의2–제5조의4 and 제93조,
     and 36673호's sit in 제48조 and 제88조의12. The cited articles are unchanged,
     so only the identity is stale. VERIFIED (marker-based).
4. **국적법 시행령 lsiSeq 243829 (2022-07-11 / 2022-07-12).** It is stored with
   `checkedAt 2026-06-28` and marked `official_legal_text_identity_verified`, but
   was superseded on **2022-12-20** by 246165 (대통령령 제33082호). It was already
   stale when "verified". VERIFIED.
   * **Where:** `data/nationality_sources.json:371, 380-381, 384`;
     `data/nationality_service_sources.json:45`.
5. **국적법 시행규칙 lsiSeq 262177 (법무부령 제1076호, 2024-04-29).** Superseded on
   **2026-10-02** by 291055 (법무부령 제1161호).
   * **Where:** `nationality_sources.json:398, 407-408`;
     `nationality_service_sources.json:61`.
   * **Forms:** these files back the naturalization forms (별지 서식). The 291055
     body has a 부칙 "제3조(서식에 관한 적용례)" but no article-level markers, so
     which forms changed is UNVERIFIED. The identity is VERIFIED.
6. **`data/document_help.json:31`.** Links 시행규칙 `lsiSeq=266161` (법무부령
   제1083호, 2024-10-29), `checkedAt 2026-07-02`. It was two versions old when
   checked and is three versions old now. VERIFIED.
7. **`docs/audit/law_crosscheck_2026_06.md:10-11`.** Gives the Act 272921 as
   "시행 2025-07-22", which is its 공포일 (its 시행일 is 2026-01-23). It also
   cites rule 283059. Both versions are superseded. VERIFIED.
8. **`audits/short-stay-country-checker/b1_b21_not_b22_target_fix_2026_06.md:9-10`.**
   Cites 시행령 271319 (대통령령 제35540호, 시행 2025-06-01) and Act 272921, both
   superseded. VERIFIED.
9. **F-4 고시 number mismatch: 제2026-35호 vs 제2026-65호.** VERIFIED (mismatch).
   * **Waymaker's corpus:** "재외동포(F-4) 자격의 취업활동 제한범위 고시 (법무부
     고시 제2026-35호, 2026.2.12.)". '2026-35호' appears in 31 files: manual
     extracts and corpora under `backend/data/sources/manuals`,
     `docs/source-manuals/*`, `data/manual-corpus` and
     `backend/data/knowledge_deploy/manual-corpus`, plus `source_manifest.json`
     and `scripts/extract_dongpo_manual_2026_02.py:7, 78`.
   * **law.go.kr:** 법무부고시 **제2026-65호**, the same date, 폐지제정
     (admRulId 2090230). No 제2026-35호 appears anywhere in the rule's history,
     and '2026-65' appears nowhere in the repo.
   * **Cause:** the number is the manual's own text, not a Waymaker authoring
     error, but every answer that quotes it inherits it.
   * **Needed:** a human check against the 관보 or the MOJ notice.
10. **Trainee rule title.** VERIFIED.
    * **Waymaker:** `visa_data.json:6098, 6349, 6374` calls it
      "「해외투자기업 기술연수생 등에 대한 사증발급인정서 발급 및 관리에 관한
      지침」".
    * **Official:** the title ends in **훈령** (법무부훈령 제1414호, 2022-04-14,
      admRulId 27428).
    * **Why it matches nothing:** "지침" was the suffix of the older "산업연수생"
      title (to 2009). Waymaker's version combines the new noun with the old
      suffix, so it matches neither title.
    * Waymaker's own manual inventory
      (`docs/data/2026_06_17_manual_code_inventory.json`) already quotes "…관한
      훈령". The owner branch keeps "…관한 지침" (3×).
11. **Former spacing "법적지위".** `visa_data.json:30450, 32712` write
    「재외동포의 출입국과 법적지위에 관한 법률」, while the current title reads
    "법적 지위". LI calls it cosmetic but says it breaks exact-title matching.
    Whether WLIE's `compact()` normalization absorbs it was not checked here.
    VERIFIED (mismatch).
12. **Jeju 고시: unverifiable on law.go.kr.** UNVERIFIED.
    * **Where:** `data/short-stay/rules.json:10432-10437, 10606-10611` and
      `data/short-stay/fixtures/jeju_b22_notice.json:4-5`.
    * **Stored:** "법무부고시 제2022-189호", effective 2022-06-01, taken from a
      consular copy dated 2023-09-18 and marked confidence low / needs_refresh.
    * **Searches:** law.go.kr 행정규칙 name searches returned nothing relevant:
      * "무사증", "입국불허" and "확대허가" (현행+시행예정) each returned 0 rows;
      * "제주" returned 104 rows, none from 법무부 or about 무사증/사증;
      * "무사증" with the 연혁 filter returned 0 rows.
    * `visa_data.json` cites a moj.go.kr board post instead.
    * Absence from law.go.kr does not prove the 고시 does not exist; it may sit
      only in the 관보.
13. **"외국인 결핵환자 사증발급 및 체류관리 지침": unverifiable on law.go.kr.**
    It is named in the H-2 extension text of `visa_data.json`. LI-V cites
    `visa_data.json:482` and `:37667` for the Jeju and TB references together,
    without saying which line is which.
    * "결핵" returned 6 rows, none from 법무부.
    * "결핵환자" returned 2 rows, from 질병관리청 and 국가데이터처.
    * It is probably an internal MOJ guideline that is not published as a
      행정규칙. UNVERIFIED.
14. **Coverage gaps.** VERIFIED (grep).
    * The 외국인고용법 trio is absent from `docs/source-laws/law_sources_2026_05.json`
      (14 law rows), although `backend/services/law_query_normalizer.py:193-210`
      treats it as canonical.
    * `data/source_registry.json:203-216` holds a single `law_api_placeholder`
      (`status: not_configured`; version, source date and last check all null).
      The owner branch keeps the same placeholder.
    * Nothing records the pending 외국인고용법 286817 (2026-12-10, and 2027-06-10
      for 제22조의2 and 제25조, both relevant to E-9 workplace-change content).
15. **Stale local law-text copies.**
    `docs/source-manuals/law/crosscheck/lawgokr_act_272921_articles.txt` and
    `lawgokr_rule_283059_articles.txt` hold superseded versions, and no code in
    `backend/` or `scripts/` reads them. Dated audit documents that cite
    272921 / 289697 / 283059 were correct on their dates and are point-in-time
    records. VERIFIED.
16. **Synthetic fixture IDs.** `backend/tests/test_law_tools.py:47, 50`,
    `test_law_cloud_korean_search.py:35-54` and
    `test_generalized_law_grounding_verification.py:37, 106` use 출입국관리법
    "001386", 시행령 "001387" and MST 267581 / 267999. The real 법령IDs are 001707
    and 005256. These are fine as mocks but must never be promoted into data.
    VERIFIED (these tests pass: 106 passed, and 111 with
    `test_law_cloud_korean_search.py`, per LI-V).

**Not stale.** VERIFIED unless marked.
* `data/form_schemas.json` for both 시행규칙: 289833 with the 1125호 pending date,
  and 267499 `inForceFrom 2025-02-01` with pending 1124호 (`:2959-2968`,
  `:3599-3608`).
* The 국적법 current-act and amendment rows
  (`data/nationality_sources.json:326-327, 344, 353-354`).
* The two 2026-06 reconciliation records that treat 286415 as "not treated as
  current law" (`audits/official-external-source-augmentation-2026-06.md:25`,
  `backend/data/visa_authoring/audit/official_external_source_reconciliation_2026_06.json:84`).
* The 법령IDs 001707, 005256 and 008494 wherever stored.
* The canonical titles in `law_query_normalizer.py`. LI §6 also lists the titles
  in `statute_citation_guard.py`, but the verifier did not re-open that file.

**Routes** (LI §7; not done here):
* Key a law identity table on **법령ID + lsiSeq + efYd** and monitor it against
  the 연혁 rows.
* Give article-level citations their own 시행일.
* Fix `author_rules.py:316-318, 339` and regenerate the status-guidance files.
  Reword the `:1877` card-payment line until 2027-09-16, or show both texts
  with their dates.
* Update the nationality and `document_help` lsiSeq values, and re-verify the
  국적법 시행규칙 forms against 291055.
* Add the 외국인고용법 trio and its pending dates to `docs/source-laws`.
* Record rules by `admRulId` and `admRulSeq`, and correct the 훈령 title.
  `visa_data.json` is protected, so this goes through the owner.
* Flag the F-4 number for manual review.
* Mark the Jeju 고시 and the 결핵 지침 as "not on law.go.kr; secondary copy only".

## 9. Open items and requests

* **Spec wording ([06 §5](06-temporal-law-and-source-identity.md),
  [05 row A](05-legal-intelligence-architecture.md)).** Both name `lsHistory` as
  a family the resolver needs. Its list and body are **HTML only** (§2.1), so
  machine-readable version enumeration should come from the `eflaw` list
  (`LID` + `nw=1,2,3`) and `lsJoHstInf`. That replacement is INFERRED from the
  documented parameters. I did not edit those normative documents; this is
  listed as a change request.
* **Seed completeness.** `law_identity_seed.json` still has `law_id: null` for
  the four rules whose `admRulId` the verifier found (§7.2), and `former_titles:
  null` for the 훈령 and the F-4 고시. The values are in LI-V "Omissions found
  and filled", items 1–2.
* **Before Mission 002 code depends on a new family:** add `eflaw` (and the
  others the P0/P1 rows need) to the OC application, and check the approval
  scope (§1.2). Capture one real error body for an unapproved target in a
  controlled test, and add it to the fixture set as `verified_api` provenance.
  This needs the owner's OC and is owner work.
* **Remaining open items:** OA §10 and LI §8 (collected in §6.3).

## Sources

* [research-notes/official-api.md](research-notes/official-api.md): §0 (method),
  §1 (conventions), §2.1–§2.14 (statute families), §3.1–§3.7 (rules, decisions,
  terms, treaties), §4 (identity model), §5 (limits and onboarding), §6 (terms
  and copyright), §7 (live actions), §8 (Waymaker findings), §9 (alternative
  sources), §10 (open items); verification pass R1–R6, W, L, verdicts 1–15 and
  omissions V-A to V-I.
* [research-notes/law-identity.md](research-notes/law-identity.md): §1 (method
  and budget), §2 (version identifiers), §3 (statute identities, former titles,
  split dates), §4 (administrative rules), §5 (what Waymaker stores), §6 (stale
  entries), §7 (recommendations), §8 (not verified); verification pass verdicts
  1–15, inline corrections and filled omissions 1–6.
* [research-notes/law_identity_seed.json](research-notes/law_identity_seed.json):
  all 22 records.
* Related: [01](01-existing-system-audit.md) (existing system),
  [05](05-legal-intelligence-architecture.md) (architecture),
  [06](06-temporal-law-and-source-identity.md) (temporal resolver),
  [07](07-evidence-verification-design.md) (verification invariants),
  [11](11-dataset-governance.md) (dataset licence and attribution rules),
  [15](15-security-and-deployment.md) (OC handling),
  [17](17-mission-002-plan.md) (Mission 002).
