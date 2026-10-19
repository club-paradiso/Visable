# Official open.law.go.kr Open API capability catalog (immigration-law view)

Mission 001 "Waymaker Genesis", research date 2026-10-19. Author: research subagent.
Audited code: `/Users/seonjaekim/dev/Visable-genesis` (origin/main 0713370), read-only.

Status vocabulary: VERIFIED (I read the primary page or code myself), OBSERVED (I saw it in a live response during this task), README-ONLY, INFERRED (my reasoning), UNVERIFIED (not seen on an official page).

Credential hygiene: every URL pattern below writes the credential as `OC={OC}`. Official guide samples use a placeholder sample OC that the guide pages publish. No real OC was used or looked for. Links that the API returns with the caller's OC inside them are described by shape only.

---

## 0. Method and coverage

| Step | What I did | Result |
|---|---|---|
| Guide index | GET `https://open.law.go.kr/LSO/openApi/guideList.do` | HTTP 200, 62,520 bytes. The page says "총 191 건". The page source holds 195 distinct `openApiGuide('<htmlName>')` identifiers, because some cells point to the same guide family in mobile and other variants. [LIVE 2026-10-19, 200] VERIFIED [corrected by verifier: re-fetched 2026-10-19T04:25Z, byte-identical (62,520 B), "총 191 건" confirmed; but each of the 195 `openApiGuide('…')` calls appears exactly once with a distinct name (mobile guides have their own names, e.g. `mobLsListGuide`), so the "same guide family" explanation is not supported. The 191 vs 195 gap is unexplained.] |
| Guide pages | GET `https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=<name>` for 55 guides, 1 s apart. The page's own form sends this as a POST, but GET works. | All 55 returned HTTP 200. [LIVE 2026-10-19] VERIFIED |
| Usage and policy pages | `information/service.do`, `information/guide.do`, `openApi/openApiManual.do`, `support/noticeList.do`, `lab/sampleCode.do`, `lab/supportCase.do`, 5 `supportCaseView.do` entries, `lab/lawListSupport.do` | 200 for all. These redirected to login (302): `openApi/cuAskList.do` (OPEN API 신청), `lab/ipErrorCheck.do`, `lab/selfDiagnosis.do`. `support/faq.do` returned 404; its menu item is hidden (`display:none`). [corrected by verifier: every sub-menu `<li>` in the static HTML of guideList.do is `display: none` (service, guide, guideList, cuAsk, faq, …), so the hidden FAQ item says nothing on its own; the 404 stands as reported.] |
| law.go.kr policy | GET `https://www.law.go.kr/lawPetitionForm.do?menuId=13&subMenuId=79` (the "법적효력/저작권" footer link) | 200 [LIVE 2026-10-19] VERIFIED |
| 저작권법 articles | law.go.kr Korean URL `/법령/저작권법/제7조` → iframe `/LSW//lsSideInfoP.do?lsiSeq=283335&joNo=0007&joBrNo=00&docCls=jo&urlMode=lsScJoRltInfoR`. Same pattern for 제24조의2, 제137조, 제138조. | 200 for all. Version shown: 저작권법 [시행 2026. 8. 11.] [법률 제21336호, 2026. 2. 10., 일부개정]. VERIFIED |
| Sample OC calls | 3 documented guide sample URLs (section 7) | 3 × HTTP 200. OBSERVED |
| Waymaker backend | 4 GETs to `https://web-production-14f9a.up.railway.app` (section 7) | 4 × HTTP 200. OBSERVED |

Some HTML comments in the guide pages carry a change history. For example, `lsNwInfoGuide` and `lsEfYdInfoGuide` were last revised "2026. 01. 29. [#38236] 법령 본문 조회 OPEN API 가이드 페이지 개선". `lsEfYdListGuide` records "2023. 10. 17. [#33556] 시행일법령목록 API의 nw파라미터값이 OC가 test일 경우에만 적용되는 현상 조치", which was a past bug where `nw` only took effect for the sample OC. [DOC guideResult.do?htmlName=lsEfYdListGuide, HTML comment] VERIFIED

---

## 1. Interface conventions shared by all families (VERIFIED from guide pages)

- **Two endpoints.** List and search calls use `http://www.law.go.kr/DRF/lawSearch.do?target=<t>`. Body and detail calls use `http://www.law.go.kr/DRF/lawService.do?target=<t>`. [corrected by verifier: confirmed on all 57 guide pages actually saved. The 55 original guides contain 137 lawSearch.do and 102 lawService.do mentions and no other DRF path; the two mobile guides fetched by the verifier (`mobLsListGuide` / `mobLsInfoGuide`) use the same two paths. `openApiManual.do` also states the list/body split. The other ~138 guide links on the index (committee decisions, ministry interpretations, 자치법규, 학칙, special appeals, 감사원) were not opened, so "all 191 use two endpoints" is INFERRED for them, not VERIFIED.] The legacy guides print `http://`. The 지식베이스 (knowledge-base) guides (`lstrmAI`, `lsRlt`, `aiSearch`, `aiRltLs`, `lstrmRltJo`, `joRltLstrm`) and `openApiManual.do` print `https://www.law.go.kr`. A few samples omit `www.`. [DOC guide pages]
- **Required parameters.** `OC` ("신청한 API인증값") and `target` are required on every guide. `type` is required on almost every guide. Exceptions: the `elaw` list and detail guides, the `trty` detail guide and `lsAbrv` list it without "(필수)". `eflaw` list and detail state "생략시 기본값: XML". [DOC] [corrected by verifier: `delHst` (htmlName `datDelHstGuide`, "type | string | XML/JSON") also lacks "(필수)", and so does the mobile law body guide `mobLsInfoGuide` ("type | char | 출력 형태 : HTML"), which instead marks `mobileYn` "char : Y (필수)". Checked on 55 saved guides + 2 mobile guides fetched by the verifier; OC and target are "(필수)" on all 57.]
- **What OC is.** OC is the part of the registered login ID (an e-mail address) before the '@'. [DOC lab/supportCaseView.do?supportCaseSeq=30, 2015] VERIFIED, though the page is old.
- **Formats.** `HTML/XML/JSON` on most guides. Exceptions:
  - `lsHistory` (list and body): HTML only.
  - [added by verifier] Mobile law body (`lawService.do?target=law&mobileYn=Y`, htmlName `mobLsInfoGuide`): HTML only. The mobile law list (`mobLsListGuide`) allows HTML/XML/JSON. [DOC guideResult.do?htmlName=mobLsInfoGuide / mobLsListGuide, fetched 2026-10-19T04:25Z, 200] VERIFIED
  - XML/JSON only: `lsJoHstInf` (both forms), `lsDelegated`, `lsAbrv`, `delHst` and all 지식베이스 targets.
  - `prec` body: HTML only for 국세청 cases ("국세청 판례 본문 조회는 HTML만 가능합니다").
- **Paging.** `display` (default 20, max 100) and `page` (default 1) on nearly every list guide. `aiSearch` gives only "default=20" and no maximum. The date-based `lsJoHstInf` list documents `page` but no `display`.
- **Article address.** `JO` is 6 digits: a 4-digit article number plus a 2-digit branch (`000200` = 제2조, `001002` = 제10조의2). `HANG` and `HO` are also 6 digits (`HO=001002` = 제10호의2). `MOK` is one Hangul character (가…하) and must be URL-encoded.
  - Trap: in the `prec` list, `JO` means "참조법령명", a law **name** string (형법, 민법).
- **Ranges.** Date ranges are written `YYYYMMDD~YYYYMMDD` (`efYd`, `ancYd`, `prmlYd`, `modYd`, `prncYd`, `regYd`, `explYd`, `dpaYd`, `rslYd`, `eftYd`, `concYd`, `regDt` on `lstrm`). The `ancNo` range is written `306~400`.
- **Sort codes.** `lasc`/`ldes` (name), `dasc`/`ddes` (promulgation or decision date), `nasc`/`ndes` (number), `efasc`/`efdes` (effective date). `trty` adds `rasc`/`rdes` (관보게재일). `lstrm` uses `rasc`/`rdes` for 등록일자.
- **제개정 codes (`rrClsCd`).** 300201 제정, 300202 일부개정, 300203 전부개정, 300204 폐지, 300205 폐지제정, 300206 일괄개정, 300207 일괄폐지, 300209 타법개정, 300210 타법폐지, 300208 기타.
- **Law ID versus MST.** `ID` is 법령 ID. `MST` is "법령 마스터 번호 - 법령테이블의 lsi_seq 값", which is the 법령일련번호 returned by lists. The `eflaw` and `lawjosub` guides state that querying by `ID` returns the **current** text ("ID로 검색하면 그 법령의 현행 법령 본문 조회").
- **Status envelope.** Only some list guides document `numOfRows`, `resultCode` (00 success / 01 fail) and `resultMsg` (success/fail): `lsStmd`, `oldAndNew`, `thdCmp`, `admrulOldAndNew` and `lstrmAI` (numOfRows only). I OBSERVED `resultCode`, `resultMsg` and `numOfRows` in a live `eflaw` list JSON response too, although that guide does not list them. **No guide documents an error body for a bad OC, an unregistered IP or a bad target.** [verifier: one live error shape (missing OC) is now OBSERVED; see Verification pass V-E.] The repo fixture shape `resultCode 99 / "ERROR invalid request"` is labelled synthetic in its own README [CODE backend/tests/fixtures/law_api_shapes/README.md:1-8]. It is UNVERIFIED as an official shape.
- **Other common parameters.** `popYn=Y` opens the HTML detail as a popup. `gana` is a dictionary-order filter (ga, na, da…). `org` is a 소관부처 code (예: 1613000 국토교통부, 1741000 행정안전부, 1352000 보건복지부, 1320000 경찰청, 1543000 농림축산식품부, as printed in the samples). No guide prints the full code table ("코드제공"/"코드별도제공"). The 법무부 org code is UNVERIFIED.

---

## 2. Catalog: statute families

Parameter notation: **bold** = marked "(필수)" on the guide; everything else is optional. "OC, target, type" are omitted from the lists below unless they differ.

### 2.1 Current law, promulgation-date basis — `target=law` (htmlName `lsNwListGuide` / `lsNwInfoGuide`)

**List** `lawSearch.do?target=law` — HTML/XML/JSON
- `search`: 1 = 법령명 (default), 2 = 본문검색
- `query`: search string
- `display`, `page`, `sort`
- `date`: 공포일자
- `efYd`: 시행일자 range
- `ancYd`: 공포일자 range
- `ancNo`: 공포번호 range
- `rrClsCd`
- `nb`: 공포번호
- `org`
- `knd`: 법령종류 code
- `lsChapNo`: 법령분류 01–44편
- `gana`, `popYn`

Response fields: `target`, `키워드`, `section`, `totalCnt`, `page`, `law id`, 법령일련번호, 현행연혁코드, 법령명한글, 법령약칭명, 법령ID, 공포일자, 공포번호, 제개정구분명, 소관부처명, 소관부처코드, 법령구분명, 공동부령구분, 공포번호 (공동부령), 시행일자, 자법타법여부, 법령상세링크. [DOC lsNwListGuide] VERIFIED

**Body** `lawService.do?target=law` — HTML/XML/JSON
- `ID`: 법령 ID. One of ID or MST is required.
- `MST`: lsi_seq
- `LM`: 법령명 (makes the law link)
- `LD`: 공포일자
- `LN`: 공포번호
- `JO`: 6-digit article; omit for all articles
- `LANG`: KO or ORI (원문)

Response fields by group:
- **Header.** 법령ID, 공포일자, 공포번호, 언어, 법종구분(+코드), 법령명_한글/_한자, 법령명약칭, 제명변경여부, 한글법령여부, 편장절관, 소관부처코드/소관부처, 전화번호, 시행일자, 제개정구분, 별표편집여부, 공포법령여부, 부서명, 부서연락처, 공동부령구분, 구분코드, 공포번호 (공동부령).
- **Articles.** 조문번호, 조문가지번호, 조문여부, 조문제목, 조문시행일자, 조문제개정유형, 조문이동이전, 조문이동이후, 조문변경여부 ("Y값이 있으면 해당 조문내에 변경 내용 있음"), 조문내용, 항번호, 항제개정유형, 항제개정일자문자열, 항내용, 호번호, 호내용, 목번호, 목내용, 조문참고자료.
- **Addenda (부칙).** 부칙공포일자, 부칙공포번호, 부칙내용.
- **Annexes (별표).** 별표번호, 별표가지번호, 별표구분, 별표제목, 별표서식파일링크, 별표HWP파일명, 별표서식PDF파일링크, 별표PDF파일명, 별표서식이미지파일링크, 별표이미지파일명, 별표내용.
- **Amendment text.** 개정문내용, 제개정이유내용.

[DOC lsNwInfoGuide] VERIFIED

Live JSON shape [LIVE sample 2, section 7] OBSERVED:
- The root is `법령` with `개정문`, `법령키`, `기본정보`, `부칙`, `조문` and `제개정이유`. `별표` is absent when the law has no annex.
- `조문.조문단위[]` carries `조문키`. `부칙.부칙단위[]` carries `부칙키`. `기본정보.연락부서.부서단위` carries `부서키`. None of these keys are in the lsNwInfoGuide table.
- `법령키` has 19 characters and equals 법령ID (6) + 공포일자 (8) + 공포번호 (5). [corrected by verifier: re-checked on the saved S2 file, composition matches (0096822024032620417). But `법령키` is not wholly undocumented: it is listed as a response field ("법령키 | int") on the `lawjosub`, `eflawjosub` and `couseLs` article-list guides. Only its composition is undocumented. `조문키`, `부칙키` and `부서키` appear on none of the 57 guides checked.]
- `부칙키` has 13 characters and equals 부칙공포일자 + 부칙공포번호.
- `조문키` has 7 digits: article (4) + branch (2) + 1 more digit. I INFER that the last digit marks 조문여부, because a 전문 heading had …0 and the article had …1.
- `조문여부` takes the values `조문` and `전문`. 전문 rows are 편/장/절 headings, so they must be filtered before articles are counted.
- `항` is **polymorphic**: an object when there is one paragraph and an array when there are several. In the sample, 25 articles had a list and 1 had a dict. `호` follows the same pattern. [corrected by verifier: re-parsed S2: `항` = list 25, dict 1, absent 21 (confirmed). `호` appeared 9 times, always as a list. An object-form `호` was not observed, so "same pattern" for `호` is INFERRED, not OBSERVED. Also, `기본정보.법종구분` arrives as a nested object (`content` + `법종구분코드`), not a flat string. All 852 leaf values are strings (confirmed).]
- Every value is a JSON string, including the fields the guide types as "int".

### 2.2 Effective-date-based law — `target=eflaw` (htmlName `lsEfYdListGuide` / `lsEfYdInfoGuide`)

**List** `lawSearch.do?target=eflaw` — HTML/XML/JSON, default XML
- `search`, `query`
- **`nw`**: 1 = 연혁, 2 = 시행예정, 3 = 현행. The default is all; combinations are comma-separated, e.g. `nw=1,2` or `nw=1,2,3`.
- **`LID`**: 법령ID, e.g. `LID=830`
- [corrected by verifier: by this file's own legend, bold means "(필수)", but the guide marks neither as required: "nw | int" and "LID | string". Both are optional. The values and comma syntax are confirmed.]
- `display`, `page`, `sort`
- `efYd`: range
- `date`: 공포일자
- `ancYd`, `ancNo`, `rrClsCd`, `nb`, `org`, `knd`, `gana`, `popYn`
- There is no `lsChapNo` on this guide.

The response fields match the `law` list. [DOC lsEfYdListGuide] VERIFIED

Live [sample 1] OBSERVED:
- The root is `LawSearch` with `law[]` (20 items), `resultCode` "00", `resultMsg` "success", `numOfRows` "20", `section` "lawNm", `키워드` "*" and `totalCnt` "169418". The unfiltered list therefore spans 현행 + 연혁 + 예정.
- Item keys: 현행연혁코드, 법령일련번호, 자법타법여부, 법령상세링크, 법령명한글, 법령구분명, 소관부처명, 공포번호, 제개정구분명, 소관부처코드, `id`, 법령ID, 공동부령정보, 시행일자, 공포일자, 법령약칭명.
- On page 1, 현행연혁코드 took the values `현행` and `연혁`.
- `법령상세링크` has the shape `/DRF/lawService.do?OC=<caller OC>&target=eflaw&MST=<n>&type=HTML&mobileYn=&efYd=<n>`. It **embeds the caller's OC**, and it uses a `mobileYn` parameter that no guide documents. [corrected by verifier: `mobileYn` IS documented. The mobile guides `mobLsListGuide` and `mobLsInfoGuide` give the request URL as `…?target=law&mobileYn=Y` and list "mobileYn | char : Y (필수) | 모바일여부" (fetched 2026-10-19T04:25Z, 200). In S1 the value is empty (`mobileYn=`). The S3 `조문링크` carries no `mobileYn` at all. OC embedding was observed only with the published sample OC, which the link echoes back; that it echoes a real OC too is INFERRED, though it is consistent with the backend redaction code.] [added by verifier: S1 also shows that eflaw list rows are keyed by (MST, efYd), not by MST alone. MST 140323 appears twice, with efYd 20130823 and 20130522, both 공포 20130522. A version store keyed only by 법령일련번호 would merge two effective-date states.]

**Body** `lawService.do?target=eflaw` — HTML/XML/JSON, default XML
- `ID`: returns the current text
- `MST`
- **`efYd`**: int, marked 필수. It is ignored and should be omitted when `ID` is given.
- `JO`
- `chrClsCd`: 010202 한글 / 010201 원문

The response matches the `law` body with these additions: 조문시행일자문자열, 별표시행일자문자열, 별표제목문자열, 별표시행일자. It drops 제명변경여부 and 한글법령여부. [DOC lsEfYdInfoGuide] VERIFIED

The pair (MST, efYd) is the documented way to fetch "the text as in force on date X". The article-history API links back to exactly this form; see 2.5.

### 2.3 Law history (연혁) — `target=lsHistory` (htmlName `lsHstListGuide` / `lsHstInfoGuide`)

- **List** `lawSearch.do?target=lsHistory` — **type HTML only.** Parameters: `query`, `display`, `page`, `sort`, `efYd`, `date`, `ancYd`, `ancNo`, `rrClsCd`, `org`, `knd`, `lsChapNo`, `gana`, `popYn`. No response field table is given.
- **Body** `lawService.do?target=lsHistory` — **HTML only.** Parameters: `ID` or `MST`, `LM`, `LD`, `LN`, `chrClsCd`.
- The guide notes "체계도 등 부가서비스는 법령서비스 신청을 하면 추가신청 없이 이용가능합니다".

[DOC both guides] VERIFIED. For machine-readable version enumeration, use `eflaw` list with `LID` + `nw=1,2,3` (documented) or `lsJoHstInf` (2.5). That is INFERRED from the documented parameters.

### 2.4 Law change history by date — `target=lsHstInf` (htmlName `lsChgListGuide`)

List only: `lawSearch.do?target=lsHstInf` — HTML/XML/JSON
- **`regDt`**: int, the 법령 변경일, e.g. 20150101
- `org`, `display`, `page`, `popYn`

Response fields: `target`, `totalCnt`, `page`, `law id`, 법령일련번호, 현행연혁코드, 법령명한글, 법령ID, 공포일자, 공포번호, 제개정구분명, 소관부처코드, 소관부처명, 법령구분명, 시행일자, 자법타법여부, 법령상세링크. [DOC] VERIFIED

This is the natural **daily change feed**: poll yesterday's `regDt`, then filter on 소관부처 법무부 or on a watch-list of 법령ID. INFERRED.

### 2.5 Article-level change history — `target=lsJoHstInf` (two documented forms)

(a) **By date**, htmlName `lsDayJoRvsListGuide`: `lawSearch.do?target=lsJoHstInf` — XML/JSON
- `regDt`: 조문 개정일, 8 digits
- `fromRegDt`, `toRegDt`
- `ID`: 법령ID
- `JO`: 4+2 digits
- `org`, `page`
- The guide says the data is **one day behind**: "이 서비스는 전일 데이터를 기준으로 제공됩니다… 익일에 서비스를 조회".
- Response fields: `target`, `totalCnt` ("검색한 기간에 개정 조문이 있는 법령의 건수"), `law id`, 법령일련번호, 법령명한글, 법령ID, 공포일자, 공포번호, 제개정구분명, 소관부처명, 소관부처코드, 법령구분명, 시행일자, `jo num`, 조문정보, 조문번호, 변경사유, 조문링크, 조문변경이력상세링크, 조문개정일, 조문시행일.

[DOC] VERIFIED

(b) **By article**, htmlName `lsJoChgListGuide`: `lawService.do?target=lsJoHstInf` — XML/JSON
- **`ID`**: char
- **`JO`**: int, 6 digits
- `display`, `page`
- Response fields: 법령ID, 법령명한글, 법령일련번호, 공포일자, 공포번호, 제개정구분명, 소관부처명, 소관부처코드, 법령구분명, 시행일자, 조문번호, 변경사유, 조문링크, 조문변경일.
- The guide's type column has errors: 법령명한글 is typed "int", and 조문링크 is described as "변경사유".

[DOC] VERIFIED

Live XML [sample 3] OBSERVED:
- The root is `LawService` with `target` = lsJoHstInf, `totalCnt` = 12, `법령ID`, `법령명한글` and 12 `law` elements.
- Each `law` holds `법령정보` (법령일련번호, 공포일자, 공포번호, 제개정구분명, 소관부처코드, 소관부처명, 법령구분명, 시행일자) and `조문정보` (조문번호, 변경사유, 조문링크, 조문변경일).
- 변경사유 values seen: 제정, 조문변경, 전부개정.
- 조문변경일 equalled the version's **시행일자** in 11 of 12 rows. The exception was the first 제정 row, where it equalled 공포일자. So this field tracks when the change took effect, not when it was promulgated. INFERRED from that one sample.
- `조문링크` has the shape `lawService.do?OC=<caller OC>&target=eflaw&MST=<n>&JO=<n>&efYd=<n>&type=HTML`. Each article version therefore resolves to a (MST, JO, efYd) triple, and the link embeds the caller's OC.
- [added by verifier, re-read of saved S3 XML] The chain is not one row per version. Rows 1 and 2 share MST 59612: one row with 조문변경일/efYd = 공포일자 19990208, one with 시행일자 20000101. Rows 10 and 11 have different MSTs (193394 and 201168) but the same 조문변경일 20180701. So (ID, JO, 조문변경일) is not a unique key; keep MST in the key. The link is a relative path (`/DRF/lawService.do?...`) with no `mobileYn`. OBSERVED

### 2.6 Article / paragraph / item / sub-item body — `target=lawjosub` and `target=eflawjosub`

- **`lawjosub`** (htmlName `lsNwJoListGuide`): `lawService.do?target=lawjosub` — HTML/XML/JSON
  - `ID` or `MST`; querying by ID returns the current text
  - **`JO`**: char, 6 digits
  - `HANG`: 6 digits
  - `HO`: 6 digits, branch allowed
  - `MOK`: one Hangul character, URL-encoded
  - Response fields: 법령키, 법령ID, 공포일자, 공포번호, 언어, 법령명_한글/_한자, 법종구분코드, 법종구분명, 제명변경여부, 한글법령여부, 편장절관, 소관부처코드, 소관부처, 전화번호, 시행일자, 제개정구분, 제안구분, 의결구분, 이전법령명, 조문별시행일자, 조문시행일자문자열, 별표시행일자문자열, 별표편집여부, 공포법령여부, 시행일기준편집여부, 조문번호, 조문여부, 조문제목, 조문시행일자, 조문이동이전, 조문이동이후, 조문변경여부, 조문내용, 항번호, 항내용, 호번호, 호내용, 목번호, 목내용. [DOC] VERIFIED
- **`eflawjosub`** (htmlName `lsEfYdJoListGuide`): `lawService.do?target=eflawjosub` — HTML/XML/JSON
  - `ID` or `MST`
  - **`efYd`**: ignored when ID is given
  - **`JO`**, `HANG`, `HO`, `MOK`
  - Response: the `lawjosub` fields plus 법령명_영어, **적용시작일자** and **적용종료일자**, which give a validity interval. It drops 제명변경여부, 한글법령여부, 조문별시행일자 and 시행일기준편집여부. [DOC] VERIFIED
- Neither response table lists `조문가지번호`, even though `JO` accepts a branch. Treat the branch as an input-only address. That gap is UNVERIFIED in the documentation.

### 2.7 부칙 (addenda)

- There is **no separate 부칙 API** on the index. None of the 191 guides is a 부칙 guide; I checked every label. [DOC guideList.do] VERIFIED [corrected by verifier: there is no separate 부칙 *target* (the index text has 0 occurrences of "부칙"). However, the mobile law body guide `mobLsInfoGuide` (`lawService.do?target=law&mobileYn=Y`, **HTML only**) documents two 부칙 view parameters: `PD` ("부칙표시 ON일 경우 부칙 목록만 출력"; omitted, it shows 법령 + 부칙) and `PN` (부칙번호, show that one 부칙). These are not on the standard `lsNwInfoGuide`. For machine-readable 부칙, the XML/JSON body remains the only route. [DOC guideResult.do?htmlName=mobLsInfoGuide, 2026-10-19T04:25Z, 200] VERIFIED (doc); behaviour not tested]
- 부칙 arrives inside the `law` and `eflaw` bodies as 부칙공포일자, 부칙공포번호 and 부칙내용. The live JSON adds `부칙키` and `부칙단위[]`. The sample law had 13 부칙 units spanning 20040209–20240326, so **all historical 부칙 are returned with the current body**, not only the newest one. OBSERVED. [corrected by verifier: confirmed on saved S2: 13 `부칙단위`, each `부칙키` = 부칙공포일자 + 부칙공포번호 (13 chars), range 20040209–20240326. This is one law (건강가정기본법, enacted 2004). That every law returns its full 부칙 history is INFERRED from one sample.]
- The `admrul` body carries 부칙, 부칙공포일자, 부칙공포번호 and 부칙내용. [DOC admrulInfoGuide]
- The `lawListSupport.do` bulk-download form (web UI, not the API) offers 조문 종류 "부칙" as a filter. [LIVE page] OBSERVED

### 2.8 별표·서식 (annexes and forms)

**`licbyl`** list (htmlName `lsBylListGuide`): `lawSearch.do?target=licbyl` — HTML/XML/JSON
- `search`: 1 = 별표서식명 (default), 2 = 해당법령검색, 3 = 별표본문검색
- `query`: default *
- `display`, `page`
- `sort`: lasc / ldes
- `org`: several codes allowed, comma-separated
- `mulOrg`: OR (default) / AND
- `knd`: 1 별표, 2 서식, 3 별지, 4 별도, 5 부록
- `gana`, `popYn`
- Response fields: `target`, `키워드`, `section`, `totalCnt`, `page`, `licbyl id`, 별표일련번호, 관련법령일련번호, 관련법령ID, 별표명, 관련법령명, 별표번호, 별표종류, 소관부처명, 공포일자, 공포번호, 제개정구분명, 법령종류, 별표서식파일링크, 별표서식PDF파일링크, 별표법령상세링크. [DOC] VERIFIED

**Annex body API:** the index shows "-" in the body column for 법령, 행정규칙 and 자치법규 별표ㆍ서식. The string `lsBylInfo` appears on **none** of the fetched guide pages, so **`lsBylInfo` is UNVERIFIED as an official target.** [corrected by verifier: `lsBylInfo` absence re-confirmed on all 57 saved guide pages and the info pages. But the mobile law body guide `mobLsInfoGuide` (HTML only) documents annex view parameters: `BD` (별표표시; ON shows all 별표), `BT` (별표구분 1 별표 / 2 서식 / 3 별지 / 4 별도 / 5 부록), `BN` (별표번호) and `BG` (별표가지번호). So a documented HTML annex view exists, but no XML/JSON annex-body target exists. [DOC mobLsInfoGuide, 2026-10-19T04:25Z, 200] VERIFIED (doc); behaviour not tested]

Annex content comes from the `law` / `eflaw` body 별표 fields. Files are fetched by appending `별표서식파일링크` or `별표서식PDF파일링크` to `https://www.law.go.kr`. The documented example path is `/LSW/flDownload.do?flSeq=<n>`, and the guide says files come as HWP and PDF. [DOC openApiManual.do] VERIFIED. A 2019 notice says "openAPI 현행법령 별표서식 PDF 다운로드 가능". [DOC noticeList.do]

**`admbyl`** (htmlName `admrulBylListGuide`, administrative-rule annexes):
- Parameters: `search` (1/2/3), `query`, `display`, `page`, `sort`, `org`, `knd` (1 별표 / 2 서식 / 3 별지), `gana`, `popYn`
- Response fields: 별표일련번호, 관련행정규칙일련번호, 별표명, 관련행정규칙명, 별표번호, 별표종류, 소관부처명, 발령일자, 발령번호, 관련법령ID, 행정규칙종류, 별표서식파일링크, 별표행정규칙상세링크. [DOC] VERIFIED

Immigration relevance: the 체류자격 tables are 출입국관리법 시행령 별표 and the application forms are 시행규칙 별지. Both are reachable only through the body 별표 fields plus a file link. INFERRED.

### 2.9 Delegated laws — `target=lsDelegated` (htmlName `lsDelegated`)

`lawService.do?target=lsDelegated` — XML/JSON
- `ID` or `MST`; ID returns the current law
- Response fields: 법령일련번호, 법령명, 법령ID, 공포일자, 공포번호, 소관부처코드, 전화번호, 시행일자, 조문번호, 조문제목, 위임구분 (시행령, 시행규칙, 인용법령, 위임행정규칙 등), 위임법령일련번호, 위임법령제목, 위임법령조문번호, 위임법령조문가지번호, 위임법령조문제목, 링크텍스트, 라인텍스트, 조항호목, 위임행정규칙일련번호, 위임행정규칙제목, 위임자치법규일련번호, 위임자치법규제목, 위임규정일련번호, 위임규정제목, 조약일련번호, 조약제목. [DOC] VERIFIED

`openApiManual.do` describes this target as the way to build law.go.kr-style links:
- 링크텍스트 is the string that carries the link.
- 라인텍스트 tells apart repeated link texts within the same article.
- 조항호목 gives the 조/항/호/목 position. [DOC] VERIFIED

### 2.10 Law structure — `target=lsStmd` (htmlName `lsStmdListGuide` / `lsStmdInfoGuide`)

- **List**: `query`, `display`, `page`, `sort`, `efYd`, `ancYd`, `date`, `nb`, `ancNo`, `rrClsCd`, `org`, `knd`, `gana`, `popYn`. Response fields: `target`, `키워드`, `section`, `totalCnt`, `page`, `numOfRows`, `resultCode`, `resultMsg`, `law id`, 법령 일련번호, 법령명, 법령ID, 공포일자, 공포번호, 제개정구분명, 소관부처코드, 소관부처명, 법령구분명, 시행일자, 본문 상세링크.
- **Body**: `ID` or `MST`, `LM`, `LD`, `LN`; HTML/XML/JSON. Response fields: 기본정보, 법령ID, 법령일련번호, 공포일자, 공포번호, 법종구분, 법령명, 시행일자, 제개정구분, 상하위법, 법률, 시행령, 시행규칙, 본문 상세링크.
- XML for this family arrived in 2022. [DOC noticeList.do "부가서비스 법령 쳬계도, 신구법, 3단비교 목록과 본문 조회 xml 서비스 추가", 2022-08-26]

VERIFIED

### 2.11 Old-new comparison — `target=oldAndNew` (htmlName `oldAndNewListGuide` / `oldAndNewInfoGuide`)

- **List**: same parameters as `lsStmd`. Response fields: … `oldAndNew id`, 신구법일련번호, 현행연혁구분, 신구법명, 신구법ID, 공포일자, 공포번호, 제개정구분명, 소관부처코드, 소관부처명, 법령구분명, 시행일자, 신구법상세링크.
- **Body**: `ID` or `MST`, `LM`, `LD`, `LN`. Response fields:
  - 구조문_기본정보: 법령일련번호, 법령ID, 시행일자, 공포일자, 공포번호, 현행여부, 제개정구분명, 법령명, 법종구분
  - 신조문_기본정보: same fields
  - 구조문목록/조문, 신조문목록/조문
  - 신구법존재여부: "N" when no comparison exists

[DOC] VERIFIED

### 2.12 Three-way comparison — `target=thdCmp` (htmlName `thdCmpListGuide` / `thdCmpInfoGuide`)

- **List**: same parameters as `lsStmd`. Response fields: `thdCmp id`, 삼단비교일련번호, 법령명 한글, 법령ID, 공포일자, 공포번호, 제개정구분명, 소관부처코드, 소관부처명, 법령구분명, 시행일자, 인용조문_삼단비교상세링크, 위임조문_삼단비교상세링크.
- **Body**:
  - **`knd`**: int; 1 = 인용조문, 2 = 위임조문
  - `ID` or `MST`, `LM`, `LD`, `LN`
- 인용 response: 기본정보, 법령ID, 시행령ID, 시행규칙ID, 법령명, 시행령명, 시행규칙명, 법령/시행령/시행규칙 요약정보, 삼단비교기준, 삼단비교존재여부, 시행일자, 관련삼단비교목록, 목록명, 삼단비교목록상세링크, 인용조문삼단비교 → 법률조문 (조번호, 조가지번호, 조제목, 조내용), 시행령조문목록/시행령조문, 시행규칙조문목록/시행규칙조문, 위임행정규칙목록/위임행정규칙 (명, 일련번호, 조번호, 조가지번호).
- 위임 response: 기본정보 (법령ID, 법령일련번호, 공포일자, 공포번호, 법종구분, 법령명, 시행일자, 제개정구분), 삼단비교존재여부, 기준법법령명, 기준법령목록, 위임3비교상세링크, 위임조문삼단비교 → 법률조문, 시행령조문, 시행규칙조문목록/조문.

[DOC] VERIFIED

Immigration relevance: this is the official 출입국관리법 ↔ 시행령 ↔ 시행규칙 ↔ 위임행정규칙 chain. Visable's resolver can use it instead of inferring the chain. INFERRED.

### 2.13 English law — `target=elaw` (htmlName `lsEngListGuide` / `lsEngInfoGuide`)

- **List**: `search`, `query` (default *; Korean or English), `display`, `page`, `sort`, `date`, `efYd`, `ancYd`, `ancNo`, `rrClsCd`, `nb`, `org`, `knd`, `gana`, `type` (not marked required), `popYn`. Response fields: … 법령일련번호, 현행연혁코드, 법령명한글, **법령명영문**, 법령ID, 공포일자, 공포번호, 제개정구분명, 소관부처명, 법령구분명, 시행일자, 자법타법여부, 법령상세링크.
- **Body**: `ID` or `MST`, `LM`, `LD`, `LN`, `type`. **The body guide has no response-field table**, so the body fields are UNVERIFIED.
- law.go.kr states that translations are not official: "외국어번역 법령정보는 공식적 효력이 있는 번역물이 아니므로 참고로만", and the Korean text prevails. [DOC law.go.kr 법적효력/저작권] VERIFIED

### 2.14 Smaller statute helpers (VERIFIED from guides)

| target | endpoint | params | key response fields |
|---|---|---|---|
| `lsAbrv` (법률명 약칭) | lawSearch | `type` XML/JSON, `stdDt`, `endDt` (등록일 range) | 법령일련번호, 현행연혁코드, 법령명한글, 법령약칭명, 법령ID, 공포일자, 공포번호, 시행일자, 등록일 |
| `delHst` (삭제 데이터) | lawSearch | `type` XML/JSON, `display`, `page`, `knd` (1 법령, 2 행정규칙, 3 자치법규, 13 학칙공단), `delDt`, `frmDt`/`toDt` | `일련번호`, `구분명`, `삭제일자`. The guide's table says the target value is "datDel", but every sample URL uses `target=delHst`. This is a documentation inconsistency; treat `delHst` as the working value (UNVERIFIED live). |
| `oneview` (한눈보기) | lawSearch / lawService | list: `query`, `display`, `page`; body: `MST`, `LM`, `LD`, `LN`, `JO` | list: 법령일련번호, 법령명, 공포일자, 공포번호, 시행일자, 제공건수, 제공일자; body: 패턴일련번호, 조문시행일자, 최초제공일자, 조번호, 조제목, 콘텐츠제목, 링크텍스트, 링크URL |
| `couseLs` (맞춤형) | lawSearch | **`vcode`** (L + 13 digits), `lj=jo` for the article list, `display`, `page`, `popYn` | 법령일련번호, 법령ID, …; the article list adds 조문번호, 조문가지번호, 조문시행일자, 조문제개정유형, 조문제개정일자문자열, 조문상세링크 |

`delHst` lets a mirror detect **withdrawn records**. That matters for a cache: prune them rather than keep serving them. INFERRED.

---

## 3. Catalog: administrative rules and decisions

### 3.1 Administrative rules — `target=admrul` (htmlName `admrulListGuide` / `admrulInfoGuide`)

**List** `lawSearch.do?target=admrul` — HTML/XML/JSON
- **`nw`**: 1 = 현행, 2 = 연혁; default 현행. **The codes mean something different from `eflaw` `nw`**, where 1 = 연혁 and 3 = 현행.
- `search`: 1 = 행정규칙명, 2 = 본문
- `query`, `display`, `page`, `org`
- `knd`: 1 훈령, 2 예규, 3 고시, 4 공고, 5 지침, 6 기타
- `gana`
- `sort`: dasc/ddes = 발령일자
- `date`: 발령일자
- `prmlYd`: 발령일자 range
- `modYd`: 수정일자 range
- `nb`: 발령번호; 제2023-8호 is entered as `nb=20238`
- `popYn`
- Response fields: … `admrul id`, 행정규칙일련번호, 행정규칙명, 행정규칙종류, 발령일자, 발령번호, 소관부처명, 현행연혁구분, 제개정구분코드, 제개정구분명, 행정규칙ID, 행정규칙상세링크, 시행일자, 생성일자. VERIFIED

**Body** `lawService.do?target=admrul` — HTML/XML/JSON
- **`ID` = 행정규칙 일련번호** (the version)
- **`LID` = 행정규칙 ID** (stable)
- [corrected by verifier: `admrulInfoGuide` marks neither as "(필수)" ("ID | char | 행정규칙 일련번호", "LID | char | 행정규칙 ID") and has no "one of the two is required" wording. That wording appears only on `admrulOldAndNewInfoGuide`. The ID = version / LID = stable meaning is confirmed.]
- `LM`: exact rule name
- Response fields: 행정규칙일련번호, 행정규칙명, 행정규칙종류(+코드), 발령일자, 발령번호, 제개정구분명(+코드), 조문형식여부, 행정규칙ID, 소관부처명/코드, 상위부처명, 담당부서기관코드/명, 담당자명, 전화번호, 현행여부, 시행일자, 생성일자, 조문내용, 부칙 (+공포일자/공포번호/내용), 별표 (+번호/가지번호/구분/제목/서식파일링크/PDF링크/내용), 첨부파일, 첨부파일명, 첨부파일링크. VERIFIED

**Trap:** for `admrul`, `ID` is the version-specific serial and `LID` is the stable ID. For `law`/`eflaw`, `ID` is the stable 법령ID and `MST` is the version. A shared "id" field across both families must keep the two apart. The live Waymaker projection already conflates these for laws; see section 8.

**`admrulOldAndNew`** (htmlName `admrulOldAndNewListGuide` / `admrulOldAndNewInfoGuide`): HTML/XML/JSON.
- List parameters: `query`, `display`, `page`, `org`, `knd`, `gana`, `sort`, `date`, `prmlYd`, `nb`, `popYn`.
- Body: `ID` (일련번호) or `LID` is required, plus `LM`.
- The response mirrors `oldAndNew` with 행정규칙 fields and 신구법존재여부.
- The guide says the 부가서비스 needs no extra application beyond the 행정규칙 service.

VERIFIED

### 3.2 Court precedents — `target=prec` (htmlName `precListGuide` / `precInfoGuide`)

**List**
- `search`: 1 = 판례명, 2 = 본문, 3 = 참조판례 (searches the case numbers listed in 참조판례)
- `query`, `display`, `page`
- `org`: 400201 대법원 / 400202 하위법원
- `curt`: 법원명
- **`JO`: 참조법령명** (a law name)
- `gana`
- `sort`: lasc/ldes 사건명; dasc/ddes 선고일자, with **ddes as the default**; nasc/ndes 법원명
- `date`: 선고일자
- `prncYd`: range
- `nb`: 사건번호; the sample passes two numbers separated by a comma
- `datSrcNm`: 국세법령정보시스템, 근로복지공단산재판례, 대법원
- `popYn`
- Response fields: `target`, 공포번호, `키워드`, `section` (EvtNm / bdyText), `totalCnt`, `page`, `prec id`, 판례일련번호, 사건명, 사건번호, 선고일자 (string), 법원명, 법원종류코드, 사건종류명, 사건종류코드, 판결유형, 선고, 데이터출처명, 판례상세링크.

**Body**
- **`ID`**: 판례 일련번호
- `LM`
- Response fields: 판례정보일련번호, 사건명, 사건번호, 선고일자 (int), 선고, 법원명, 법원종류코드, 사건종류명, 사건종류코드, 판결유형, 판시사항, 판결요지, 참조조문, 참조판례, 판례내용.

[DOC] VERIFIED

Live through Waymaker OBSERVED: list `decisionDate` came back as "2023.03.13" and the detail as "20230313". The two forms of 선고일자 must be normalized into one. [verifier: confirmed on saved B3/B4 JSON. Also, the detail `summary` contains raw `<br/>` markup, and the detail `sourceUrl` is not DRF but `https://www.law.go.kr/LSW/precSc.do?menuId=7&query=234321`, a site search for the serial number. See section 8 item 3.]

### 3.3 Constitutional Court — `target=detc` (htmlName `detcListGuide` / `detcInfoGuide`)

- **List**: `search` (1 헌재결정례명 / 2 본문), `query`, `display`, `page`, `gana`, `sort` (lasc/ldes 사건명, dasc/ddes 선고일자, nasc/ndes 사건번호, efasc/efdes 종국일자), `date` (종국일자), `edYd` (종국일자 range), `nb` (사건번호), `popYn`. Response fields: … `detc id`, 헌재결정례일련번호, 종국일자, 사건번호, 사건명, 헌재결정례상세링크.
- **Body**: **`ID`**, `LM`. Response fields: 헌재결정례일련번호, 종국일자, 사건번호, 사건명, 사건종류명, 사건종류코드, 재판부구분코드 (430201 전원재판부 / 430202 지정재판부), 판시사항, 결정요지, 전문, 참조조문, 참조판례, 심판대상조문.

VERIFIED

### 3.4 Legal interpretations — 법제처 `target=expc`, plus ministry first-instance interpretations

**`expc`** (htmlName `expcListGuide` / `expcInfoGuide`):
- List parameters:
  - `search` (1 법령해석례명 / 2 본문), `query`, `display`, `page`
  - `inq`: 질의기관. Its type cell literally says "inq", a documentation error.
  - `rpl`: 회신기관
  - `gana`
  - `itmno`: 안건번호; 13-0217 is entered as 130217
  - `regYd`: 등록일자 range
  - `explYd`: 해석일자 range
  - `sort`, `popYn`
- List response fields: 법령해석례일련번호, 안건명, 안건번호, 질의기관코드/명, 회신기관코드/명, 회신일자, 법령해석례상세링크.
- Body: **`ID`** (int), `LM`. Response fields: 법령해석례일련번호, 안건명, 안건번호, 해석일자, 해석기관코드/명, 질의기관코드/명, 관리기관코드, 등록일시, 질의요지, 회답, 이유.

VERIFIED

**법무부 1차 해석 `target=mojCgmExpc`** (htmlName `cgmExpcMojListGuide` / `cgmExpcMojInfoGuide`):
- List parameters: `search` (1 법령해석명 / 2 본문), `query`, `display`, `page`, `inq` (질의기관코드), `rpl` (해석기관코드), `gana`, `itmno` ("안건번호 변수 적용 시 query 요청변수는 무시됩니다"), `explYd`, `sort`, `popYn`, **`fields`** (response-field selection; empty returns all; not available for HTML).
- List response fields: `id`, 법령해석일련번호, 안건명, 안건번호, 질의기관코드/명, 해석기관코드/명, 해석일자, **데이터기준일시**, 법령해석상세링크.
- Body: **`ID`**, `LM`, `fields`. Response fields: 법령해석일련번호, 안건명, 안건번호, 해석일자, 해석기관코드/명, 질의기관코드/명, 관리기관코드, 등록일시, 질의요지, 회답, 이유, **관련법령**, 데이터기준일시.

VERIFIED. 법무부 is the competent ministry for 출입국관리법, so this is the most immigration-specific interpretation feed on the platform. INFERRED.

**재외동포청 `target=okaCgmExpc`** (htmlName `cgmExpcOkaListGuide`; body `cgmExpcOkaInfoGuide` was fetched, but I extracted only the list): same parameter and response shape as mojCgmExpc. It is relevant to 재외동포 (F-4) questions. VERIFIED for the list.

The index lists 39 ministry and agency interpretation list feeds (37 with a body guide); target names follow `<agency>CgmExpc` for the two I read. Other agency names are UNVERIFIED.

### 3.5 Administrative appeals — `target=decc` (htmlName `deccListGuide` / `deccInfoGuide`)

- **List**:
  - `search`, `query`, `display`, `page`
  - `cls`: 재결례유형, matching the 재결구분코드 response field
  - `gana`
  - `date`: 의결일자
  - `dpaYd`: 처분일자 range
  - `rslYd`: 의결일자 range
  - `sort`, `popYn`
  - Response fields: … `decc id`, 행정심판재결례일련번호, 사건명, 사건번호, 처분일자, 의결일자, 처분청, 재결청, 재결구분명, 재결구분코드, 행정심판례상세링크.
- **Body**: **`ID`**, `LM`. Response fields: 행정심판례일련번호, 사건명, 사건번호, 처분일자, 의결일자, 처분청, 재결청, 재결례유형명, 재결례유형코드, 주문, 청구취지, 이유, 재결요지.

VERIFIED. I did not read the special administrative tribunals (조세심판원, 국민권익위원회, 인사혁신처 소청심사위원회 and others; `specialDecc*` guides).

### 3.6 Legal terms — `target=lstrm` and the 지식베이스 family

- **`lstrm` list**:
  - `query`, `display`, `page`
  - `sort`: lasc/ldes, rasc/rdes = 등록일자
  - `regDt`: range
  - `gana`, `popYn`
  - `dicKndCd`: 010101 법령 / 010102 행정규칙
  - Response fields: 법령용어ID, 법령용어명, 법령용어상세검색, 사전구분코드 (011401 법령용어사전, 011402 법령정의사전, 011403 법령한영사전), 법령용어상세링크, 법령종류코드.
- **`lstrm` body**: `query` (term name). Response fields: 법령용어 일련번호, 법령용어명_한글/_한자, 법령용어코드, 법령용어코드명, 출처, 법령용어정의.

VERIFIED

지식베이스 targets (all XML/JSON, https host):
- **`lstrmAI`** (lawSearch): `query`, `display`, `page`, `homonymYn`.
- **`lstrmRltJo`** (lawService): **`query`**. Returns the articles linked to a term (법령명, 조번호, 조가지번호, 조문내용, 용어구분).
- **`joRltLstrm`** (lawService): `query` or `ID`, **`JO`**. Returns the terms used in an article.
- **`lsRlt`** (lawSearch): `query` (exact name) or `ID`, `rltClsCd`. Returns 기준법령, 관련법령ID/명, 법령간관계코드/관계.
- **`aiSearch`** (lawSearch): `search` (0 법령조문, 1 법령 별표·서식, 2 행정규칙 조문, 3 행정규칙 별표·서식), `query`, `display`, `page`. Returns article-level hits with 법령ID, 법령일련번호, 조문번호, 조문가지번호, 조문내용, 시행일자, 공포일자, 공포번호 and the matching 행정규칙 fields.
- **`aiRltLs`** (lawSearch): `search` (0/1), `query`.

[DOC each guide] VERIFIED. law.go.kr warns: "법령정보지식베이스는 지능형법령검색을 위한 참고자료로만 활용하시기 바랍니다". [DOC law.go.kr 법적효력/저작권] VERIFIED

### 3.7 Treaties — `target=trty` (htmlName `trtyListGuide` / `trtyInfoGuide`)

- **List**:
  - `search` (1 조약명 / 2 본문), `query`, `display`, `page`, `gana`
  - `eftYd`: 발효일자 range
  - `concYd`: 체결일자 range
  - `cls`: 1 양자 / 2 다자
  - `natCd`: 국가코드
  - `sort`: includes rasc/rdes 관보게재일
  - `popYn`
  - Response fields: 조약일련번호, 조약명, 조약구분코드/명, 발효일자, 서명일자, 관보게제일자, 조약번호, 국가번호, 조약상세링크.
- **Body**: `ID`, `chrClsCd` (010202 한글 / 010203 영문). Response fields: 조약일련번호, 조약명_한글/_영문, 조약구분코드 (440101 양자 / 440102 다자), 대통령재가일자, 발효일자, 조약번호, 관보게재일자, 국무회의심의일자/회차, 국회비준동의여부/일자, 서명일자/장소, 체결대상국가(+한글), 양자조약분야코드/명, 다자조약분야코드/명, 국가코드, 조약내용, 체결일자, 국내발효일자, and others.

VERIFIED. Immigration relevance: the 법령목록지원 web form lists 양자 조약 분야 "사증", "사회보장" and "영사", and 다자 분야 "이민" and "난민/국적". [LIVE lab/lawListSupport.do] OBSERVED. **The numeric 분야/국가 codes are not on any guide**, so they are UNVERIFIED. Visa-waiver agreements are therefore reachable through `trty` with `cls=1` + `query`.

---

## 4. Identity and versioning model (synthesis)

| Concept | Field(s) | Request parameter | Stability | Status |
|---|---|---|---|---|
| A law across all versions | 법령ID | `ID` (law, eflaw, josub, lsDelegated, lsStmd, oldAndNew, thdCmp, lsJoHstInf); `LID` on the eflaw list | Stable across amendments | VERIFIED (doc) |
| One promulgated version | 법령일련번호 = MST = lsi_seq | `MST` | New for each version | VERIFIED |
| Version key | 법령키 = 법령ID + 공포일자 + 공포번호 | none documented as input | Derived | OBSERVED |
| Text in force on a date | (MST, efYd); 조문시행일자, 조문시행일자문자열, 별표시행일자; 적용시작일자/적용종료일자 (eflawjosub) | `target=eflaw` / `eflawjosub` + `efYd` | Point-in-time | VERIFIED (doc) |
| Lifecycle | 현행연혁코드 (observed values 현행, 연혁); eflaw `nw` 1/2/3; admrul 현행연혁구분, 현행여부 | `nw` | Changes over time | VERIFIED / OBSERVED. I did not observe the label string for 시행예정 (UNVERIFIED). |
| Amendment type | 제개정구분(명); `rrClsCd` codes | `rrClsCd` | Per version | VERIFIED |
| Promulgation | 공포일자, 공포번호 (+ 공동부령 공포번호) | `date`, `ancYd`, `nb`, `ancNo`, `LD`, `LN` | Per version | VERIFIED |
| Article address | 조문번호, 조문가지번호, 조문여부 (조문/전문), 조문키 | `JO` (4+2), `HANG`, `HO`, `MOK` | Renumbering via 조문이동이전/이후 | VERIFIED + OBSERVED |
| Article change | 조문변경여부 (Y/N), 조문제개정유형, 항제개정유형, 항제개정일자문자열; lsJoHstInf 변경사유, 조문변경일 | `lsJoHstInf` `ID` + `JO` | History chain | VERIFIED + OBSERVED |
| Addenda | 부칙공포일자, 부칙공포번호, 부칙내용, 부칙키 | none (inside the body) | All historical 부칙 returned | VERIFIED + OBSERVED |
| Administrative rule | 행정규칙ID (stable, request `LID`); 행정규칙일련번호 (version, request `ID`); 발령일자, 발령번호, 시행일자, 생성일자 | `ID` / `LID`, `prmlYd`, `modYd` | ID/LID naming is inverted versus law | VERIFIED |
| Precedent | 판례일련번호; 사건번호; 선고일자 | `ID`; `nb`; `prncYd` | Stable | VERIFIED |
| Constitutional decision | 헌재결정례일련번호; 사건번호; 종국일자 | `ID`; `nb`; `edYd` | Stable | VERIFIED |
| Interpretation | 법령해석례일련번호 / 법령해석일련번호; 안건번호; 해석일자; 데이터기준일시 (ministry feeds) | `ID`; `itmno`; `explYd` | Stable | VERIFIED |
| Appeal | 행정심판례일련번호; 사건번호; 의결일자; 처분일자 | `ID`; `rslYd`, `dpaYd` | Stable | VERIFIED |

The sample-2 detail by `MST=261457` returned 건강가정기본법 as promulgated 2024-03-26 and in force from 2024-09-27, so MST pins a version. OBSERVED. Whether `ID=` returns the current version is documented for `eflaw` and `lawjosub` but not on the `law` body guide; for `law` it is INFERRED.

---

## 5. Limits, quotas and onboarding

**Paging limit.** `display` is capped at 100 on list guides. [DOC] VERIFIED. No guide gives a per-call body size limit. The sample-2 body was 71,566 bytes as JSON. OBSERVED.

**No numeric daily quota is published.** I found none on any fetched open.law.go.kr page: 55 guides, service.do, guide.do, openApiManual.do, notices and Q&A. [DOC] VERIFIED (absence, on the pages fetched).

The usage page says use can be restricted in these cases:
- "상업적 이용이 불가능한 API에 대해 상업적 활용한 경우". This implies some APIs are non-commercial, but **no page I fetched says which**. UNVERIFIED.
- "트래픽 초과로 인해 시스템에 부하가 발생할 경우".

Contacts: restrictions and applications 044-200-6797; technical questions 02-2109-6446. [DOC information/guide.do] VERIFIED

**data.go.kr mirror.** The entry 법제처_현행법령 본문 조항호목 조회 (15058878) shows:
- API 유형 "LINK" (the key is issued on open.law.go.kr) [corrected by verifier: re-fetched 2026-10-19T04:33Z (200). "API 유형 LINK", 무료, 업데이트 주기 실시간, 이용허락범위 제한 없음, 개발/운영 자동승인 and the traffic sentence are all confirmed. The page also says 데이터 포맷 XML, 등록일 2018-11-01, 수정일 2025-07-08 and 활용신청 수 400. The page HTML contains no open.law.go.kr link or text, so "the key is issued on open.law.go.kr" is INFERRED from the LINK type.]
- 무료
- 이용허락범위 제한 없음
- 업데이트 실시간
- 심의 "개발단계 : 자동승인 / 운영단계 : 자동승인"
- traffic "해당 기관의 정책에 따라 트래픽 수는 상이 할 수 있음"

[LIVE https://www.data.go.kr/data/15058878/openapi.do, 2026-10-19, 200] VERIFIED

**OC onboarding** [DOC information/guide.do] VERIFIED:
1. 회원가입 (sign up).
2. Log in, choose OPEN API, apply for each data family. Approval is required before any use: "모든 DATA 활용은 공동활용이용 승인 후 가능".
3. Staff review, normally within 1–2 days.
4. Check the result in the 신청 list.
5. An 운영 (production) application requires registering the app as an 활용사례.

Since 2015 the API application can be filed at sign-up. [DOC noticeList #8, 2015-07-03]

**IP, domain and scope binding** (old Q&A, 2015, so current enforcement is UNVERIFIED):
- An approved OC works only from IPs registered on the application.
- Browser-originated calls need a matching **referer domain** and the same protocol.
- The requested `target`/`type` must match what was approved; otherwise the call fails authentication.
- IPs can be added on an approved application and take effect at once.

[DOC lab/supportCaseView.do?supportCaseSeq=30, =5, =29] VERIFIED. That the deployed backend works today implies its current egress satisfies whatever check applies. INFERRED.

**Add-on services.** 체계도, 신구법, 3단비교 and 연혁 come with the 법령 approval at no extra application. 행정규칙 신구법 comes with the 행정규칙 approval. [DOC lsStmd/oldAndNew/thdCmp/lsHistory/admrulOldAndNew guides] VERIFIED

**Freshness.**
- The service page says data is linked in real time: "실시간 연계되어 제공". [DOC information/service.do] README-ONLY. I did not test this claim.
- `lsJoHstInf` by date is previous-day data. [DOC] VERIFIED

**Self-service tools** (login required): "오류자가진단" checks request URLs and "IP 접속이력" shows access logs. [LIVE 302 to login] OBSERVED

---

## 6. Terms of use, copyright and AI use

**open.law.go.kr 저작권 정책** [DOC https://open.law.go.kr/LSO/information/guide.do] VERIFIED, paraphrased: [verifier: re-read on the saved page; every bullet below is confirmed. The page has no legal-effect statement (0 hits for "효력" on guide.do and service.do). The "no legal effect / 관보 prevails / translations and 지식베이스 are reference-only" text exists only on the law.go.kr page, so the two sites do not state an identical policy.]
- Copyright in law information provided by 법제처 belongs to 법제처 to the extent the 저작권법 protects it.
- Under public-data policy the information is open to everyone, and free use **including commercial use** is guaranteed.
- Users must not infringe the public interest or others' rights, and must use the data in good faith.
- Service may be controlled when:
  - a user's breach threatens the centre's functions;
  - use seriously infringes third-party rights;
  - the data is misused for crime;
  - or to prevent errors, forgery and alteration, and to keep government control.
- **Criminal-liability warning**, citing 「저작권법」 제137조 and 제138조, for:
  - (a) forging or altering law information and providing it or submitting it as evidence;
  - (b) using or providing 법제처 law information **without stating the source, or naming an agency other than 법제처 as the source**.

**law.go.kr 법적효력/저작권** [DOC https://www.law.go.kr/lawPetitionForm.do?menuId=13&subMenuId=79] VERIFIED:
- **Legal effect.** Information on the centre "법적 효력이 없으므로, 참고자료로 활용". The authoritative text is in the 관보 and similar official gazettes. Translations are unofficial and the Korean text prevails. The 지식베이스 is reference-only.
- **Copyright and public-data policy:**
  - Information falling under 저작권법 제7조, and works whose economic rights 법제처 wholly owns, may be used freely without permission.
  - Under the 공공데이터법 the data is open to everyone, including for profit.
  - Excluded: 정보공개법 제9조 non-disclosure information, and information containing third-party rights without proper licence (공공데이터법 제17조).
  - The same "통제" reasons apply.
- The prohibited acts listed here are **only** forgery and alteration. The attribution item that open.law.go.kr lists is absent on this page, and the old contact block is commented out in the HTML.

**저작권법 제7조 (보호받지 못하는 저작물)**, verified on law.go.kr; current version 저작권법 [시행 2026. 8. 11.] [법률 제21336호, 2026. 2. 10., 일부개정], article note "<개정 2023. 8. 8.>". Paraphrased, the Act does not protect:
1. the Constitution, laws, treaties, orders, ordinances and rules;
2. state or local 고시·공고·훈령 and similar;
3. court judgments, decisions and orders, and decisions in 심판 or 행정심판 procedures and similar;
4. state or local compilations or translations of 1–3;
5. news reports that merely convey facts.

[DOC https://www.law.go.kr/법령/저작권법/제7조] VERIFIED

**Related articles verified the same way:**
- **제24조의2** (공공저작물의 자유이용): works made and published by the state or a local government in the course of duty may be used without permission, with exceptions for national security, privacy or trade secrets, legally restricted information, and registered state property. [corrected by verifier: ① also covers works whose economic rights the state or local government holds in full under a contract, not only works it made in the course of duty. Re-read on saved cr_0024_02.html.]
- [added by verifier] **제37조** (출처의 명시) ①: anyone who uses a work under "이 관" (this sub-section) must state its source. The exceptions are 제26조, 제29조–제32조, 제34조 and 제35조의2–제35조의4; 제24조의2 is not among them. ② The source must be stated in a reasonable way, including the author's name where one is shown. [DOC https://www.law.go.kr/LSW//lsSideInfoP.do?lsiSeq=283335&joNo=0037&joBrNo=00&docCls=jo&urlMode=lsScJoRltInfoR, WebFetch 2026-10-19, version 법률 제21336호] VERIFIED. That 제24조의2 sits in the same 관 (저작재산권의 제한) is INFERRED from article numbering; I did not check the 관 heading. The consequence: for state works used under 제24조의2 (plausibly 법령해석례 and MOJ manuals), source attribution is a **statutory duty**, enforced by 제138조 item 2, not only a platform expectation. 제7조 works are unprotected, so 제37조 does not reach them.
- **제137조**: false-authorship and other offences; up to 1 year or KRW 10M.
- **제138조**: fine up to KRW 5M. Item 2 covers failing to state the source in breach of 제37조.

**Interpretation for Visable.** This is INFERRED and is not legal advice.
- Statute text, 행정규칙 (고시·훈령), court and Constitutional Court decisions, and 행정심판 decisions fall under 제7조 items 1–3. They carry no copyright for redistribution, commercial use or model training.
- 법령해석례 and ministry interpretations, and MOJ manuals, are not clearly listed in 제7조. They most plausibly fall under 제24조의2 as state works, so they are freely usable unless an exception applies.
- **Editorial value-add** that is not an official publication (summaries, translations, 지식베이스 relations) is not covered by 제7조 item 4. Check it separately.
- Whatever copyright says, the platform's own **attribution expectation** and the **anti-forgery rule** apply. Every surfaced text should state "출처: 법제처 국가법령정보센터" and must never present altered text as official.
- The data has **no legal effect**, so answers must not present API text as authoritative over the 관보.

**AI and model-training use.**
- No page I fetched on open.law.go.kr or law.go.kr mentions AI training, 인공지능 or 학습 data. I searched the saved HTML for those terms. VERIFIED (absence on fetched pages). The only AI-adjacent statement is the "지식베이스 … 참고자료로만" line. [corrected by verifier: the absence is re-confirmed on the saved guide.do, service.do, openApiManual.do, noticeList.do, main.do, the law.go.kr policy page, law.go.kr main and the Q&A pages (0 hits for 인공지능, 학습, AI, 공공누리). This is not evidence that 법제처 says nothing about AI. 법제처 runs an AI search family on this same API ("지능형 법령검색" targets `aiSearch` and `aiRltLs`). A 법제처 press release titled "법제처, 법령정보 제공을 확대해 리걸테크 기업 지원한다" is dated 2024-06-21 [WEB https://www.korea.kr/briefing/pressReleaseView.do?newsId=156637074, accessed 2026-10-19; title and date only, body not readable]. Search summaries also point to 2025 moleg.go.kr releases on opening machine-readable interpretation and 재결례 data for legal-tech (UNVERIFIED; the moleg.go.kr URL returned "page not found" to WebFetch). No primary page read states AI-training licence terms.]
- A 문화체육관광부 press release dated 2026-01-28, titled "인공지능 학습에 자유롭게 활용 가능한 공공누리 유형 신설", announces a new 공공누리 (KOGL) type for AI training. [WEB https://www.mcst.go.kr/site/s_notice/press/pressView.jsp?pSeq=22219, accessed 2026-10-19] VERIFIED for the title and date.
- Its conditions are in attachments I did not open, so the details are UNVERIFIED. [verifier: WebFetch 2026-10-19 confirms title "인공지능 학습에 자유롭게 활용 가능한 공공누리 유형 신설", date 2026.01.28 and issuing unit 문화체육관광부 저작권산업과. The visible body only refers readers to the attachments ("[0128]문체부보도자료-공공저작물 인공지능 학습 활용 확대 방안 발표", .hwpx 464KB / .pdf 344KB). I did not download them, because file downloads need the user's permission, so the conditions stay UNVERIFIED.] News reports describe a "제0유형" with no attribution duty and an "AI유형" (WEB search summary only; UNVERIFIED).
- Nothing indicates that 법제처 has labelled its law data with these types. UNVERIFIED.

---

## 7. Live actions performed (exact record)

All times UTC on 2026-10-19. Only top-level structure was recorded. No credential values appear here, and no OC-bearing link was stored in these notes.

| # | Request | Result |
|---|---|---|
| S1 | Documented sample (lsEfYdListGuide #3): `http://www.law.go.kr/DRF/lawSearch.do?OC={sample}&target=eflaw&type=JSON` at 03:56:40 | HTTP 200, no redirect, `application/json;charset=UTF-8`, 16,895 B. Root `LawSearch`: `law`[20], `resultCode` "00", `resultMsg` "success", `totalCnt` "169418", `numOfRows` "20", `section` "lawNm". The item detail link embeds OC. |
| S2 | Documented sample (lsNwInfoGuide #3): `http://www.law.go.kr/DRF/lawService.do?OC={sample}&target=law&MST=261457&type=JSON` at 03:57:04 | HTTP 200, JSON, 71,566 B. Root `법령`: {개정문, 법령키, 기본정보, 부칙, 조문, 제개정이유}. 47 조문단위 (42 조문 + 5 전문), 13 부칙단위; 항 is polymorphic. 건강가정기본법, 법령ID 009682, 공포 20240326, 제20417호, 시행 20240927, 타법개정. |
| S3 | Documented sample (lsJoChgListGuide #1): `http://www.law.go.kr/DRF/lawService.do?OC={sample}&target=lsJoHstInf&ID=001971&JO=000500&type=XML` at 03:57:36 | HTTP 200, `text/xml;charset=UTF-8`, 8,276 B. Root `LawService`; `totalCnt` 12 (국민건강보험법 제5조 history); `law`×12 → 법령정보 / 조문정보 as described in 2.5. |
| B1 | `GET https://web-production-14f9a.up.railway.app/health` at 03:57:55 | HTTP 200, 0.36 s. Reports `build.commit` 0713370… (= the audited origin/main), `law_api.law_api_configured` true, `law_api_credential_source` "LAW_API_OC", `law_grounding_effective_mode` "enabled". Booleans only were recorded. |
| B2 | `GET …/api/legal/laws/search?q=출입국관리법` at 03:58:02 | HTTP 200, 0.94 s. `{ok:true, kind:"laws", count:3, rawSource:"law.go.kr"}`. Results: 출입국관리법 (id 290729, 공포 20260804, 시행 20261002), 시행령 (id 290501, 공포 20260929, 시행 20261002), 시행규칙 (id 289833, 공포 20260915, 시행 20260915). `lifecycleStatus` and `hierarchyLevel` are empty strings. `sourceUrl` = `https://www.law.go.kr/법령/<name>` with no OC. |
| B3 | `GET …/api/legal/precedents/search?q=출입국관리법` at 04:00:01 | HTTP 200, 1.02 s. `count` 9, courts 대법원 / 창원·제주지방법원 (2020–2023). Each `sourceUrl` = `https://www.law.go.kr/DRF/lawService.do?target=..&ID=..&type=..`, with OC removed. `summary` is empty in the list. |
| B4 | `GET …/api/legal/precedents/detail?id=234321` at 04:00:16 | HTTP 200, 1.23 s. `count` 1; `id` became the 사건번호 "2021도3652"; `decisionDate` "20230313" (the list gave "2023.03.13"); `summary` 500 chars; `detailAvailable` false. [verifier: the detail `sourceUrl` is `https://www.law.go.kr/LSW/precSc.do?menuId=7&query=234321`, a site search on the serial number, not a DRF link. That follows from `_public_precedent_url` falling back to the search link when the item has no URL, and `serialNumber` is missing in detail mode (`_map_precedent_item`, which also explains why `id` became the 사건번호) [CODE backend/paradiso_backend.py:6838-6843, 6869-6888] VERIFIED] |
| G | 55 guide pages + 18 info/support pages on open.law.go.kr (including 5 Q&A views), the law.go.kr policy page and main.html, 5 law.go.kr article-page requests, 2 data.go.kr dataset pages, 1 data.go.kr search page (results are JS-rendered, so nothing could be parsed), HiKorea `Main.pt` and immigration.go.kr index (one GET each) | All 200 except: `support/faq.do` 404; `cuAskList.do`, `ipErrorCheck.do`, `selfDiagnosis.do` 302 to login. One WebFetch of data.go.kr metadata 15058878 timed out at 60 s; the same page fetched through curl returned 200. |
| W | WebSearch ×3 (queries on 법제처 Open API + AI training; 공공누리 AI type; data.go.kr 법무부 출입국 API). WebFetch ×2 of 문화체육관광부 press releases (pSeq=22681, dated 2026.09.03, which mentions only 공공누리 0유형 for its own text; pSeq=22219, dated 2026.01.28, whose title announces the AI-training type with details in attachments). WebFetch ×1 of data.go.kr 15058878 (timed out). | Search summaries are used only as pointers. Each claim above cites the primary page I fetched, or is marked UNVERIFIED. |

Two local tool errors occurred. Several Bash calls failed with `ENOSPC: no space left on device` because the local disk had about 180 MB free. I retried each one after space returned. No result above depends on a failed call.

---

## 8. Findings that matter for Waymaker (origin/main)

1. **Waymaker uses about a quarter of the documented surface.**
   - The backend references only these targets: `law` (most call sites), `admrul`, `lstrm`, `prec` and `decc`. [CODE backend/services/law_tools.py:777, :921, :1047, :1075; backend/services/precedent_sources.py; backend/services/legal_evidence.py — `grep` count] VERIFIED
   - It does not use `eflaw`, `eflawjosub` or `lawjosub`; `lsJoHstInf`, `lsHstInf` or `delHst`; `lsDelegated`, `thdCmp` or `lsStmd`; `licbyl`; `expc`, `mojCgmExpc` or `okaCgmExpc`; `detc`; or `trty`.
   - The owner's branch `fix/waymaker-qa-2026-10-16` adds no new targets in law_tools.py, legal_analysis.py or knowledge/adapters.py. [CODE git show of that branch] VERIFIED [verifier: re-checked with `git diff origin/main...fix/waymaker-qa-2026-10-16` (branch tip 9bf8849, merge-base 0713370) over backend/services and paradiso_backend.py. law_tools.py is unchanged. The only added `"target"` key is a manual-locator visa-code field, not a DRF target. No added lawSearch.do or lawService.do calls. Confirmed.]
   - [added by verifier] The repo's own comment says the 행정심판 target is "NOT publicly confirmed" and keeps `decc` as an env-overridable default (`LAW_API_ADMIN_APPEAL_TARGET`). The special administrative appeal target (`LAW_API_SPECIAL_ADMIN_APPEAL_TARGET`) has no default [CODE backend/services/legal_evidence.py:70-94]. The official guides do confirm `target=decc` for both list and body (`deccListGuide` / `deccInfoGuide`), so the comment is stale. Special-appeal guides exist on the index (`specialDeccTt*`, `specialDeccKmst*`, `specialDeccAcr*`, `specialDeccAdap*`), but their target values were not read (UNVERIFIED). `KoreanLawClient` (backend/services/korean_law_client.py) is never instantiated outside tests, so it adds no target.
2. **Law citations are not version-pinned.**
   - The public law result `id` is the 법령일련번호 (MST) when present [CODE backend/paradiso_backend.py:6850]. The stable 법령ID is not exposed.
   - `sourceUrl` is always `https://www.law.go.kr/법령/<name>` [CODE backend/paradiso_backend.py:6830-6835], which shows whatever version is current when the user clicks. [corrected by verifier: not always. When the title is empty or starts with "(", it falls back to `https://www.law.go.kr/LSW/lsAstSc.do?menuId=1` (line 6833-6834). Otherwise the "unpinned name link" finding is confirmed.]
   - [added by verifier] Latent ID/MST mix-up in `get_law_detail`: any all-digit identifier is sent as `MST`, anything else as `ID` [CODE backend/services/law_tools.py:921-927]. Official 법령IDs are all-digit, zero-padded strings ("009682" in S2, "001971" in S3, "010719" in S1), so a 법령ID that reaches this function would be sent as `MST=<법령ID>`. The caller passes `law_serial_no or law_id` [CODE backend/services/law_grounding.py:349-360], so this fires only when a search candidate lacks 법령일련번호. The likelihood is low and the bug was not exercised live. INFERRED Visable's evidence and the user's view can therefore drift apart.
   - `lifecycleStatus` came back empty in the live 출입국관리법 search. OBSERVED. The docstring promises lifecycle labelling.
3. **Precedent source links point at DRF without OC** (B3), with shape `https://www.law.go.kr/DRF/lawService.do?target=..&ID=..&type=..`. A DRF call without OC most likely fails for an end user. That is INFERRED and **UNVERIFIED**: I did not call DRF without OC. A public law.go.kr precedent page link would be safer. [corrected by verifier: now OBSERVED. One GET of the exact B3 link `https://www.law.go.kr/DRF/lawService.do?target=prec&ID=234321&type=HTML` at 2026-10-19T04:30:40Z returned **HTTP 200**, text/html, 1,415 B, no redirect. The body is an error page: "사용자인증에 실패하였습니다 / OpenAPI 사용자 인증에 실패하였습니다. 접속하신 해당 기관에 문의 바랍니다." Every precedent `sourceUrl` in Waymaker's list response is therefore a broken link for end users. The HTTP status is 200, so a status check would not catch it.]
4. **OC leaks through upstream links.** `법령상세링크` (eflaw list) and `조문링크` (lsJoHstInf) embed the caller's OC (S1, S3), and every list family has a `…상세링크` field. The backend claims to redact these [CODE backend/paradiso_backend.py:6811-6813, law_tools.py:242]. B2–B4 contained no OC. OBSERVED.
5. **Parsing hazards.** These are all documented or observed:
   - JSON `항`/`호` switch between object and array.
   - Every value is a string.
   - 전문 rows sit inside 조문단위.
   - Date formats differ between the prec list and detail.
   - `nw` means opposite things in `eflaw` and `admrul`.
   - `ID`/`LID`/`MST` naming is inverted between `law` and `admrul`.
   - `prec` uses `JO` for a law name.
   - `delHst` versus "datDel".
   - Guide type columns contain errors.
6. **Better official primitives exist for Visable's needs.**
   - **Point-in-time text**: `eflaw` / `eflawjosub` with (MST, efYd), plus 적용시작일자/적용종료일자.
   - **Change detection**: `lsHstInf` (daily) and `lsJoHstInf` (per article; data one day behind).
   - **Hierarchy**: `thdCmp` knd=1/2, `lsDelegated`, `lsStmd`.
   - **Annexes**: body 별표 fields plus `licbyl` and file links.
   - **MOJ interpretations**: `mojCgmExpc`, using `fields` to trim responses.
   - **Visa-waiver treaties**: `trty`.
7. **No published quota**, but use can be throttled for traffic overload, and keys are bound to the approved targets, types, IPs and domain. Request each new target family on the OC application before code depends on it. 부가서비스 come with the 법령 approval; 판례, 해석례 and 조약 need their own approvals. That last point is INFERRED from "target과 type이 신청하신 내용과 동일한지 확인" in the Q&A.

---

## 9. Alternative official sources

| Source | API? | Evidence | Status |
|---|---|---|---|
| data.go.kr 법제처 datasets (e.g. 15058878 현행법령 본문 조항호목) | Listed as "LINK" to open.law.go.kr; no separate key or endpoint; 이용허락범위 제한 없음 | [LIVE data.go.kr/data/15058878/openapi.do] | VERIFIED |
| data.go.kr 외교부_국가·지역별 재외공관 정보 (15075354), already referenced by the repo [CODE assets/js/preview/preview-data.js:181] | REST, free, 이용허락범위 제한 없음; dev auto-approval with traffic 10,000; production needs review ("심의승인"); traffic can be raised once a 활용사례 is registered; error code 22 = "일일 호출 허용량을 초과" | [LIVE data.go.kr/data/15075354/openapi.do] | VERIFIED |
| data.go.kr 외교부_국가별 사증 면제협정 체결현황 (15099235), referenced by the repo | File dataset, not an API | [CODE assets/js/preview/preview-data.js:187] | Page not fetched; UNVERIFIED |
| HiKorea (hikorea.go.kr) | No API mention found on `Main.pt` (0 hits for OpenAPI, 공공데이터개방 or data.go.kr). The repo instead scrapes public board and detail pages: `BoardDataListR.pt`, `BoardNtcDetailR.pt`, `InfoDatail.pt`. | [LIVE Main.pt 200]; [CODE git grep of hikorea URLs] | No-API is INFERRED; UNVERIFIED as an official statement |
| immigration.go.kr / moj.go.kr | No API mention on the immigration.go.kr index (0 hits) | [LIVE immigration/index.do 200] | UNVERIFIED |
| visa.go.kr | Referenced by the repo; not checked | [CODE git grep] | UNVERIFIED |
| law.go.kr web (Korean URLs `/법령/<name>/제N조`) | A human-facing page; it loads an `lsSideInfoP.do` iframe; no OC needed | [LIVE 저작권법 제7조] | VERIFIED as public, but not an API contract |

---

## 10. Open items

- Error bodies for an invalid or unregistered OC, unregistered IP, unapproved target or bad parameter (not documented). [partly filled by verifier, see Verification pass V-E: missing OC returns HTTP 200 in both formats. For JSON the body is `{"result": …, "msg": …}`; for HTML it is an auth-failure page. Invalid-OC, unregistered-IP and unapproved-target bodies are still unobserved.]
- Whether `ID=` on the `law` body returns the current version (documented only for `eflaw` and `lawjosub`).
- The label for 시행예정 in 현행연혁코드.
- The full `org`, `knd`, `natCd`, 분야 and `rltClsCd` code tables, and the 법무부 org code.
- Whether IP and referer binding is still enforced, and how it interacts with Railway egress.
- Which APIs are "상업적 이용이 불가능".
- The details of the 2026-01 공공누리 AI type, and whether 법제처 data carries any KOGL label.
- The `elaw` body response fields.
- The body guides for `okaCgmExpc` and the other 37 agency interpretation list feeds.

---

## Verification pass

Adversarial verifier, 2026-10-19. Method:
- Re-read the saved primary evidence: `apiguide/g_*.html` (55 guides), `apiguide/guideList.html`, `apiguide/info/*`, `apiguide/live/s1–s3`, `apiguide/backend/b1–b4`.
- Converted the HTML with my own tag-stripper (`vf-api/bin/h2t.py`) and parsed S2 with `vf-api/bin/s2check.py`.
- Read code in the read-only worktree at 0713370 and diffed the owner branch.
- Made a small number of new public GETs, listed below.

No sample-OC request was re-run and no Waymaker backend GET was made; the saved S1–S3 and B1–B4 files were re-read instead. No credential was used or looked for.

**New network actions (exact):**

| # | Request | Result |
|---|---|---|
| R1 | GET `https://open.law.go.kr/LSO/openApi/guideList.do` 04:25:02Z | 200, 62,520 B, byte-identical to the saved copy; "총 191 건"; 195 distinct guide links |
| R2–R3 | GET `guideResult.do?htmlName=mobLsListGuide` / `mobLsInfoGuide` 04:25:09–10Z | 200 / 200 (23,954 B / 17,446 B) |
| R4 | GET `https://www.law.go.kr/DRF/lawService.do?target=prec&ID=234321&type=HTML` (the Waymaker B3 link, no OC) 04:30:40Z | 200, text/html, 1,415 B, auth-failure page |
| R5 | GET `https://www.law.go.kr/DRF/lawSearch.do?target=law&type=JSON&query=test` (the backend's own no-OC probe path, paradiso_backend.py:7432) 04:30:50Z | 200, application/json, 170 B, `{result, msg}` |
| R6 | GET `https://www.data.go.kr/data/15058878/openapi.do` 04:33:22Z | 200, 178,762 B |
| W | WebFetch ×2 of the law.go.kr 저작권법 제37조 article page (the same URL twice); WebFetch ×1 each of mcst.go.kr pSeq=22219, korea.kr newsId=156637074 and a moleg.go.kr board URL (the last returned "page not found"); WebSearch ×2 | as recorded in the verdicts |
| L | Ran the repo parser locally on the R5 body: `.venv-check/bin/python` with `PYTHONDONTWRITEBYTECODE=1`, importing `services.law_tools` | `_official_error_info` → False; `parse_law_search_response` → error_type `law_api_no_results`, 0 results |

The local disk filled up (ENOSPC) several times during this pass. Commands that hit ENOSPC were re-run once space came back, and no verdict depends on a failed command.

### Verdicts on the 15 headline claims

| # | Claim (short) | Verdict | Evidence / correction |
|---|---|---|---|
| 1 | 191 guides; all use lawSearch.do / lawService.do; OC, target, type required; HTML/XML/JSON | **corrected** | "총 191 건" re-confirmed live (R1). The two endpoints are confirmed only on the 57 guides actually read; for the other ~138 linked guides it is INFERRED. `type` is not "(필수)" on elaw list/body, trty body, lsAbrv, delHst or the mobile law body. Formats vary: HTML-only for lsHistory list/body and the mobile law body; XML/JSON-only for 11 guides. The 195-vs-191 explanation in section 0 is unsupported, because all 195 links are distinct. |
| 2 | eflaw: nw 1/2/3 comma-combinable, LID; body MST + efYd "(필수)", ignored with ID; eflawjosub 적용시작/종료일자 | **confirmed** | g_lsEfYdListGuide / g_lsEfYdInfoGuide / g_lsEfYdJoListGuide. The bold on nw/LID in 2.2 was wrong, since neither is "(필수)"; fixed inline. New nuance: list rows are keyed by (MST, efYd) (S1, MST 140323 ×2). |
| 3 | lsJoHstInf: date form (regDt/fromRegDt/toRegDt/ID/JO/org/page, previous-day data); article form (ID + JO "(필수)") whose 조문링크 → eflaw MST + JO + efYd; S3 totalCnt 12 | **confirmed** | Both guides re-read; S3 XML re-read: 12 rows, 변경사유 제정 ×2 / 조문변경 ×9 / 전부개정 ×1. Added: there is a duplicate-MST row pair and a same-date row pair, so (ID, JO, 조문변경일) is not unique. |
| 4 | lsHistory list and body HTML only | **confirmed** | "출력 형태 HTML" on both, and all samples use type=HTML. The advice to use eflaw / lsJoHstInf instead stays INFERRED. |
| 5 | No separate 부칙 API; 부칙 inside the body; 13 units 2004–2024 | **corrected** | No 부칙 target exists, and S2 shows 13 units (re-parsed). But the mobile law body guide documents `PD` (부칙 only) and `PN` (one 부칙), HTML only. "Every historical 부칙" rests on one law. |
| 6 | No annex-body API; lsBylInfo absent; annexes via body 별표 fields, licbyl, file links | **corrected** | lsBylInfo is absent on all saved pages; licbyl params, the openApiManual flDownload example and the index "-" are confirmed. But the mobile law body guide documents `BD`/`BT`/`BN`/`BG` annex display (HTML only). "No annex body API" holds only for XML/JSON. |
| 7 | Undocumented JSON keys 법령키 / 부칙키 / 7-digit 조문키; 항/호 polymorphic; all strings | **corrected** | The compositions are confirmed on S2. But `법령키` is documented as a field on the lawjosub, eflawjosub and couseLs-jo guides. `호` was only ever an array (9 of 9), so its polymorphism was not observed. `법종구분` is a nested object. All 852 leaves are strings (confirmed). |
| 8 | 법령상세링크 and 조문링크 embed OC and use undocumented `mobileYn` | **corrected** | `mobileYn` is documented on mobLsListGuide / mobLsInfoGuide ("char : Y (필수)"). It appears (empty) only in the S1 법령상세링크; the S3 조문링크 has none. OC embedding was seen only as the echoed sample OC. |
| 9 | Both sites state the same policy (free incl. commercial; no legal effect); open.law.go.kr adds the 137/138 warning incl. attribution | **corrected** | Free use including commercial use is on both pages (confirmed). The "no legal effect / 관보 / translations / 지식베이스" text is only on law.go.kr; open.law.go.kr guide.do and service.do have 0 hits for 효력. The 137/138 citation and the attribution item are only on open.law.go.kr; law.go.kr lists forgery only, with its contact block commented out (confirmed). |
| 10 | 저작권법 제7조 (법률 제21336호, 시행 2026-08-11) items 1–5; 제24조의2 free use with exceptions | **confirmed** | Saved article pages re-read. Minor: 제24조의2 ① also covers works held in full by contract. Added 제37조 (출처의 명시), which makes attribution a statutory duty for 제24조의2 uses. |
| 11 | No numeric quota published; restriction for traffic or for commercial use of non-commercial APIs (unnamed); display max 100 | **confirmed** | guide.do re-read. `max=100` appears 27 times; `aiSearch` has display with no max. No quota terms on any saved page. data.go.kr 15058878 re-fetched (R6) and its fields confirmed; "key issued on open.law.go.kr" is INFERRED, since the page has no such text or link. |
| 12 | OC = ID prefix before '@'; 2015 Q&A: IP, referer and target/type binding; approval 1–2 days; 운영 requires 활용사례 | **confirmed** | sc_30 items 2–5 and sc_5 (IP binding is described for browser testing too); sc_29 says IP changes apply at once on approved services; sc_15 says sign-up approval takes 1–2 days. guide.do gives 1–2 days for 공동활용 approval and the 활용사례 rule, and its image alt text gives steps 01–04. |
| 13 | No 법제처 page addresses AI or model-training use; MCST 2026-01-28 KOGL AI type with conditions in attachments | **corrected** | Absence on the saved open.law.go.kr / law.go.kr pages is confirmed. But 법제처 does publish AI-related material: the "지능형 법령검색" API family, and a 2024-06-21 리걸테크 data-provision press release (title only). So "no 법제처 page" is too broad; what is true is that no page read states AI-training licence terms. MCST title, date and attachment names confirmed by WebFetch; the attachments were not downloaded. |
| 14 | Waymaker calls only law, admrul, lstrm, prec, decc; law id = MST; sourceUrl unpinned `/법령/<name>`; owner branch adds no targets | **confirmed** | law_tools.py:777, 921, 1047, 1075; precedent_sources.py:60, 629, 688; legal_evidence.py:90 (decc env default); paradiso_backend.py:6830-6866; B2 re-read; branch diff re-run. Minor: sourceUrl falls back to lsAstSc.do when the title is empty or starts with "(". The special-appeal target is env-configurable with no default. |
| 15 | Precedent sourceUrl is a DRF lawService.do link with OC stripped; list and detail date formats differ | **corrected** | True for the **list** (B3), and the date formats differ (confirmed). The **detail** (B4) sourceUrl is instead `LSW/precSc.do?menuId=7&query=234321`. New: the list DRF link returns HTTP 200 with "사용자인증에 실패하였습니다" (R4), so it is broken for users. |

### Omissions filled (with evidence)

- **V-A Mobile guide family (not covered by the original notes).** VERIFIED (doc) [DOC guideResult.do?htmlName=mobLsListGuide, mobLsInfoGuide; R2–R3]; behaviour not tested.
  - `lawSearch.do?target=law&mobileYn=Y` takes the same list parameters as `law`, plus `mobileYn` (Y, required); HTML/XML/JSON.
  - `lawService.do?target=law&mobileYn=Y` is HTML only. It takes `ID`/`MST`, `LM`, `LD`, `LN` and `JO`, plus `PD`/`PN` for 부칙 and `BD`/`BT`/`BN`/`BG` for 별표.
  - The index lists mobile variants for 법령, 행정규칙, 자치법규, 판례, 헌재, 해석례, 행정심판, 조약, 별표서식 and 법령용어.
- **V-B (MST, efYd) is the eflaw version key.** S1 lists MST 140323 twice, with efYd 20130823 and 20130522 [LIVE S1 saved file] OBSERVED. A version store must key on (법령ID, MST, efYd).
- **V-C lsJoHstInf chain caveats.** S3 has a duplicate MST at 공포일 and 시행일 (59612) and two MSTs on one 조문변경일 (193394 and 201168 on 20180701) [LIVE S3 saved file] OBSERVED.
- **V-D 저작권법 제37조.** Attribution is a statutory duty for uses under the 저작재산권의 제한 sub-section, and 제24조의2 is not excepted. Text VERIFIED via WebFetch; that 24조의2 sits in the same 관 is INFERRED.
- **V-E Error envelopes (open item in section 10).** OBSERVED [LIVE R4, R5]; parser result from L.
  - Missing OC, JSON list: **HTTP 200**, body `{"result": "필수입력요소 검증에 실패하였습니다.", "msg": "필수 입력값이 존재하지 않습니다. 요청 URL을 확인해 주세요."}`. There is no `resultCode`.
  - Missing OC, HTML body: **HTTP 200**, an auth-failure page "사용자인증에 실패하였습니다".
  - Waymaker's detector does not flag the JSON envelope. `_official_error_info` checks `msg` only for words such as 오류, 인증, fail and invalid, and does not check `result` [CODE backend/services/law_tools.py:510-533]. Run locally, `parse_law_search_response` returns `law_api_no_results`.
  - So a missing-required-parameter failure is reported as "no results". Whether invalid-OC and unregistered-IP responses use the same envelope is UNVERIFIED.
- **V-F Waymaker precedent links are broken for users.** R4 shows the B3 `sourceUrl` returning an auth failure. The B4 detail link is a search on a serial number, which likely matches nothing (INFERRED; not fetched). OBSERVED for the list link.
- **V-G The repo's "decc unconfirmed" comment is stale.** legal_evidence.py:70-77 versus the deccListGuide / deccInfoGuide request URLs. VERIFIED.
- **V-H Latent ID/MST mix-up in `get_law_detail`.** law_tools.py:921-927 sends any all-digit id as MST, and 법령IDs are all-digit. INFERRED; low likelihood.
- **V-I Uncatalogued guides that were fetched.**
  - `nhrckListGuide` (국가인권위원회 결정문, `https://www.law.go.kr/DRF/lawSearch.do?target=nhrck`) was saved but never discussed. It may matter for discrimination complaints by foreign residents (INFERRED).
  - The index also lists a 법제처 entry under 중앙부처 1차 해석 (`cgmExpcMolegListGuide` / `cgmExpcMolegInfoGuide`), separate from `expc`; its target value was not read (UNVERIFIED).
  - The ministry-interpretation count of 39 list feeds and 37 body feeds is confirmed from the index text; 재정경제부 and 국세청 have no body guide.

### Gaps I could not fill

- The conditions of the MCST AI-training 공공누리 type. They are in the .hwpx/.pdf attachments, and downloading files needs the user's permission.
- Error bodies for an **invalid** or unregistered OC, an unregistered IP or an unapproved target. These need a real OC, and none may be used.
- The target names and parameters for the ~138 unopened guides, including the specialDecc* and cgmExpcMoleg* guides.
- The 법무부 `org` code and the full `org`, `knd`, `natCd` and 분야 code tables. No guide prints them.
- The 현행연혁코드 label for 시행예정, and the `elaw` body response fields. Not on any guide read; a live call would need more sample-OC requests than the limit allows.
- Which APIs count as "상업적 이용이 불가능". No page names them.
- data.go.kr 15075354 / 15099235, HiKorea and immigration.go.kr were not re-checked by the verifier. The original rows in section 9 stand as the original agent recorded them.
