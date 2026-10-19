# Current official identities of immigration-related laws (law.go.kr, 2026-10-19)

Mission 001 "Waymaker Genesis". Audit target: origin/main worktree `/Users/seonjaekim/dev/Visable-genesis` at 0713370 (read-only).
Machine-readable companion: `research/law_identity_seed.json` (22 records).

Evidence tags: `[CODE path:line]`, `[TEST ...]`, `[DOC ...]`, `[LIVE request, date, result]`, `[WEB ...]`.
Status words: VERIFIED, OBSERVED, README-ONLY, INFERRED, UNVERIFIED.

---

## 1. Method and request budget

- All network traffic went to `www.law.go.kr`. I sent exactly 60 polite GETs, spaced about 1.5 s apart, with no API key, no OC value and no cookies. Every request returned HTTP 200. Nothing blocked automated access. The request log is at `scratchpad/research/raw/requests.log`, and a compact extract of every parsed response is at `scratchpad/research/raw/extract_summary.txt`. [LIVE 60 GETs, 2026-10-19 03:51–04:05 UTC, all 200] OBSERVED
- Endpoints used. All are public web views, not the DRF Open API.
  - `/법령/<name without spaces>` returns a 1.3 KB frame page whose iframe `src` names the **currently in-force** version (`lsInfoP.do?lsiSeq=…&efYd=…`). [LIVE] OBSERVED
  - `LSW/lsInfoR.do?lsiSeq=…&efYd=…&chrClsCd=010202&nwYn=1&ancYnChk=0` returns the consolidated body. It carries hidden inputs `lsId`, `lsiSeq`, `ancYd` (공포일자), `ancNo` (공포번호), `efYd` (시행일자) and `nwYnValue` (Y = 현행), a header line `[시행 …] [법률 제…호, …, 일부개정]`, and every 부칙 in full. With `ancYnChk=0` the 부칙 were present in this view. [LIVE] OBSERVED
  - `LSW/lsHstListR.do?lsId=…&chrClsCd=010202` returns the 연혁 list. Each row carries (lsiSeq, 공포일자, 공포번호, 시행일자, 현행 flag, 제개정구분). Rows are ordered by 시행일 descending, so not-yet-effective rows come first and carry the icon `alt="앞으로 시행될 법령"`. [LIVE] OBSERVED
  - `LSW/admRulScListR.do?q=…&section=admRulNm&p6=2,3&…` is the administrative-rule name search. In the site's own JavaScript, `p6` is commented "(1:연혁, 2:시행예정, 3:현행)", and I sent `2,3`. [LIVE] OBSERVED; the meaning of p6 is README-ONLY (site JS comment)
  - `LSW/admRulLsInfoP.do?admRulSeq=…` is an administrative-rule frame page. Its inline JS variables expose `admRulId` (stable ID), `ancNo` and `efYd`. [LIVE] OBSERVED [corrected by verifier: the variable named `pEfYd` holds the 발령일자, not the 시행일자. For 법무부고시 제2023-695호 it is 20231219 while the search list gives 시행 2024-01-01, and for 제2024-588호 it is 20241202 against 시행 2024-12-08. Take 시행일 from the `admRulScListR` row. LIVE admRulLsInfoP ×5, 2026-10-19, all 200]
  - Discovery cost three requests: `LSW/js/ls/lsPopLayer.js`, `LSW/js/ls/ls.js` and the `admRulSc.do` search shell.
- Breakdown: 15 statutes, decrees and rules at 3 requests each (route, body, 연혁) = 45, of which the 출입국관리법 trio took 9 because of probing. There were also 4 bodies for 시행예정 versions, 9 administrative-rule searches and 1 administrative-rule detail page. [corrected by verifier: by `raw/requests.log` the itemisation is 45 law requests (they already include the 289833@20270916 body), 3 more 시행예정 bodies (#48–50), 2 JS files, the `admRulSc.do` shell, 8 name searches (a01–a08) and 1 detail page, for 60 in total. The total of 60 is right; the itemised parts above sum to 62.]
- Incident: the host disk hit ENOSPC twice (about 180 MB free, 100% capacity). During those windows Bash and Write failed before any command ran. The request log confirms nothing was sent in the gaps. I deleted 11 large raw bodies after extraction to free about 7 MB. OBSERVED
- Budget consequence: I could not check 재한외국인 처우 기본법 (+시행령), 제주특별법, 외국인투자촉진법 or the HiKorea `LawLink.pt` directory. All are UNVERIFIED.

## 2. How law.go.kr identifies a version (matters for Waymaker's schema)

| Identifier | Meaning | Example | Evidence |
|---|---|---|---|
| `lsId` (법령ID) | Stable per law across all amendments; never changes on spacing renames | 출입국관리법 = `001707`, from 1963-03-05 to now | [LIVE h01 연혁, 61 rows] VERIFIED |
| `lsiSeq` (법령일련번호, called "MST" in the DRF API and in Waymaker data) | One per **promulgation** (공포) | 289833 = 법무부령 제1125호 | VERIFIED |
| `(lsiSeq, efYd)` | One per **시행일 version**. A promulgation whose 부칙 sets several 시행일 appears as several 연혁 rows with the **same lsiSeq** | 289833@20260915 (current) and 289833@20270916 (시행예정); 269943 (법률 제20794호) @20250601 and @20251023; 267499 @20250101 and @20250201; 286817 @20261210 and @20270610 | [LIVE 연혁 lists] VERIFIED |
| Inline `[시행일: YYYY. M. D.]` | Some deferred provisions get **no** separate 연혁 row and are only flagged inside the article text | 외국인고용법 제4조제4항 "[시행일: 2026. 1. 2.] … 재정경제부에 관한 부분" inside version 276857@20251001 | [LIVE ewa body] VERIFIED |
| `<단서 생략>` in a 타법개정 부칙 | The host-law view omits the amending law's provisos, so split dates in the amending law are not visible from the host law | 출입국관리법 and 시행령 2026-10-02 versions | VERIFIED (text seen) |
| `admRulId` / `admRulSeq` | Administrative-rule stable ID / version serial | F-4 고시: 2090230 / 2100000275060 | [LIVE a09] VERIFIED |

Implication: a stored pair `mst` + `effective` is only safe if `effective` is the 시행일 **of the specific article cited**. Waymaker gets this wrong for 시행규칙 제73조 (see §6).

## 3. Statutes, decrees and rules: current identity (all VERIFIED_WEB, retrieved 2026-10-19)

URL pattern: `https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=<version>&efYd=<시행일>`.

| # | Exact official title | 법령ID | Current lsiSeq | 공포일자 | 공포번호 | 시행일자 | 제개정 | 시행예정 version | 연혁 rows |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 출입국관리법 | 001707 | 290729 | 2026-08-04 | 법률 제21857호 | 2026-10-02 | 타법개정 | none | 61 |
| 2 | 출입국관리법 시행령 | 005256 | 290501 | 2026-09-29 | 대통령령 제36728호 | 2026-10-02 | 타법개정 | none | 96 |
| 3 | 출입국관리법 시행규칙 | 008494 | 289833 | 2026-09-15 | 법무부령 제1125호 | 2026-09-15 | 일부개정 | **289833 @ 2027-09-16** (same 공포; 제73조) | 93 |
| 4 | 난민법 | 011546 | 188376 | 2016-12-20 | 법률 제14408호 | 2016-12-20 | 일부개정 | none | 3 |
| 5 | 난민법 시행령 | 011878 | 273705 | 2025-09-16 | 대통령령 제35747호 | 2025-09-19 | 타법개정 | none | 10 |
| 6 | 난민법 시행규칙 | 011885 | 266929 | 2024-12-03 | 법무부령 제1084호 | 2024-12-03 | 일부개정 | none | 8 |
| 7 | 국적법 | 001435 | 244609 | 2022-09-15 | 법률 제18978호 | 2022-10-01 | 일부개정 | **286415**: 법률 제21725호, 공포 2026-06-02, 시행 2026-12-03 | 20 |
| 8 | 국적법 시행령 | 002922 | 246165 | 2022-12-20 | 대통령령 제33082호 | 2022-12-20 | 일부개정 | none | 26 |
| 9 | 국적법 시행규칙 | 006766 | 291055 | 2026-10-02 | 법무부령 제1161호 | 2026-10-02 | 일부개정 | none | 24 |
| 10 | 재외동포의 출입국과 법적 지위에 관한 법률 (약칭 재외동포법) | 001999 | 268553 | 2025-01-21 | 법률 제20677호 | 2025-07-22 | 타법개정 | none | 24 |
| 11 | 재외동포의 출입국과 법적 지위에 관한 법률 시행령 | 004662 | 284843 | 2026-03-24 | 대통령령 제36220호 | 2026-03-24 | 타법개정 | none | 29 |
| 12 | 재외동포의 출입국과 법적 지위에 관한 법률 시행규칙 | 008011 | 267499 | 2024-12-24 | 법무부령 제1087호 | 2025-02-01 (main body 2025-01-01) | 일부개정 | **289831**: 법무부령 제1124호, 공포 2026-09-15, 시행 2027-09-16 | 23 |
| 13 | 외국인근로자의 고용 등에 관한 법률 (약칭 외국인고용법) | 009542 | 276857 | 2025-10-01 | 법률 제21065호 | 2025-10-01 | 타법개정 | **286817**: 법률 제21786호, 공포 2026-06-09, 시행 2026-12-10 **and** 2027-06-10 | 23 |
| 14 | 외국인근로자의 고용 등에 관한 법률 시행령 | 009657 | 244037 | 2022-08-02 | 대통령령 제32844호 | 2023-02-03 | 일부개정 | none | 37 |
| 15 | 외국인근로자의 고용 등에 관한 법률 시행규칙 | 009698 | 271599 | 2025-06-02 | 고용노동부령 제442호 | 2025-06-02 | 일부개정 | none | 29 |

Evidence for each row: `[LIVE /법령/<name> + lsInfoR + lsHstListR, 2026-10-19, 200]`. Every `/법령/<name>` route in `docs/source-laws/law_sources_2026_05.json` that I tested resolved to the row above. VERIFIED.

### Former titles (from 연혁 row names; VERIFIED unless noted)
No law in scope was substantively renamed. Every change was a spacing normalisation.
- 출입국관리법 시행령 ← `출입국관리법시행령` (to 2004). 출입국관리법 시행규칙 ← `출입국관리법시행규칙` (to 2004).
- 국적법 시행령 ← `국적법시행령` (to 1998). 국적법 시행규칙 ← `국적법시행규칙` (to 2006).
- 재외동포법 ← `재외동포의 출입국과 법적지위에 관한 법률` (2005-12-29 to 2007-07-13) ← `재외동포의출입국과법적지위에관한법률` (1999–2004). The 시행령 and 시행규칙 have the same pattern, but the middle variant shows truncated ("…시…") in the 연혁 list, so I did not spell it out (UNVERIFIED). [corrected by verifier: the pattern is the same but the dates are not. The 시행령 (004662) kept the "법적지위" spacing until the row promulgated 2016-01-22, and its no-space form until the row promulgated 2007-02-28. The 시행규칙 (008011) kept "법적지위" until the row promulgated 2009-05-28, and its no-space form until 2003-12-02. LIVE lsHstListR lsId=004662 and 008011, 2026-10-19, 200]
- 외국인고용법 and its 시행령 and 시행규칙 ← the no-space forms (2003–2004).

### Split effective dates in the latest amendment (부칙 시행일 clauses; VERIFIED text)
- **출입국관리법 시행규칙, 법무부령 제1125호**: "공포한 날부터 시행. 다만, 제73조의 개정규정은 공포 후 1년이 경과한 날부터 시행". So 제73조 (수수료의 납부방법) changes on **2027-09-16**. I fetched both versions and compared 제73조: the current text allows 수입인지 or e-payment, and registration-card fees must be paid 현금/현금 납입 증표. The 2027-09-16 text adds 신용카드ㆍ직불카드 at counters, municipalities and consulates, and deletes 가목. [LIVE b03 @20260915 and b03f @20270916] VERIFIED
- **외국인고용법, 법률 제21065호 (정부조직법)**: in force from 공포 (2025-10-01), except the 재정경제부-related provisions of 1호 가·나목, which took effect 2026-01-02. law.go.kr shows only an inline marker for these. [LIVE ewa body] VERIFIED
- **외국인고용법 시행예정, 법률 제21786호**: 공포 후 6개월 (2026-12-10). 제22조의2 and 제25조 follow 공포 후 1년 (2027-06-10). [LIVE ewa_pend body] VERIFIED
- **외국인고용법 시행령, 대통령령 제32844호**: 공포일 2022-08-02, but 제13조의4제5호·제6호 took effect 공포 후 6개월 (2023-02-03). The current consolidated view is the 2023-02-03 시행일. The latest-*promulgated* decree amendment, 대통령령 제33028호 (2022-12-06, 시행 2022-12-11, lsiSeq 245799), is older in effect. A "latest version" chosen by 공포일 would therefore point at a non-current row. VERIFIED
- **재외동포법 시행규칙, 법무부령 제1087호**: 2025-01-01, but 제11조제3항, 별지 제7호서식 and 제7호의2서식 took effect 2025-02-01. The pending 제1124호 has a single date: 공포 후 1년 = 2027-09-16. VERIFIED
- **출입국관리법, 법률 제21857호** and **시행령, 대통령령 제36728호** (2026-10-02, 타법개정 tied to the 공소청/형사소송법 reform): the host-law 부칙 reads "2026년 10월 2일부터 시행한다. <단서 생략>", so any proviso dates in the amending acts are hidden. The Act's 부칙 lists the amended provisions: 제4조②, 제4조의4③2, 제4조의6, 제29조의2①, 제85조② (검사/공소청 wording). That clause is itself marked "<신설 2026. 9. 29.>". VERIFIED (text). Whether any proviso touches immigration provisions: UNVERIFIED. [corrected by verifier, for the Act only: the full 부칙 제1조 of 형사소송법 법률 제21857호 (as amended 2026-09-29) is visible in the current 형사소송법 view, lsiSeq 290189, which is itself 법률 제22009호 (2026-09-29, 시행 2026-10-02). Its 단서 lists five deferred items: 제197조의4, 제260조①, 제261조 and 부칙 제15조①⑨⑲㊱ (공포 후 6개월); 제220조의2 and 제244조의6 (1년); 제199조의2 (staged); 부칙 제15조㉓ 군인사법 (2026-12-10); and 부칙 제15조 ⑥⓪ 전자문서법 (2027-08-05). None of them is 부칙 제15조 <52>, the 출입국관리법 amendment. So the 2026-10-02 출입국관리법 changes took effect on a single date. VERIFIED. LIVE route /법령/형사소송법 → lsiSeq 290189; lsInfoR 290189 fetched twice, 2026-10-19, 200. The <52> item itself is marked "<신설 2026. 9. 29.>", meaning it was added to 21857's 부칙 by the 2026-09-29 amendment. The 시행령 omnibus decree's own 단서 was not checked. The articles that 대통령령 제36728호 changed are listed in §6 item 3.]
- Single-date 부칙 (VERIFIED): 국적법 시행예정 법률 제21725호 (공포 후 6개월), 국적법 시행령 33082, 국적법 시행규칙 1161, 난민법 14408, 난민법 시행령 35747, 난민법 시행규칙 1084, 재외동포법 20677 (공포 후 6개월, `<단서 생략>`), 재외동포법 시행령 36220, 외국인고용법 시행규칙 442.

### Observations worth carrying forward (INFERRED from VERIFIED rows)
- No implementing 시행령 or 시행규칙 amendment has yet been published for the **2026-12-03 국적법** change or the **2026-12-10 외국인고용법** change. Neither subordinate law shows a 시행예정 row, so the delegated detail may land late or at short notice.
- Three subordinate laws changed on **2026-10-02** (출입국관리법, its 시행령 and 국적법 시행규칙), well after Waymaker's last law snapshot.

## 4. Administrative rules referenced by Waymaker data or docs

How I found them: I grepped `docs/source-laws`, `data/source_registry.json`, `docs/legal` and `visa_data.json` for 고시, 훈령, 예규 and 지침. `docs/legal/*` has no references. `docs/source-laws` names only the HiKorea `출입국관련 법령지침정보` directory. `data/source_registry.json` has none. `visa_data.json` names or implies the rules below. I added the F-4 고시 because `backend/services/legal_research.py:305` uses "F-4 단순노무 취업제한 고시" as a search term and Waymaker's manual corpus cites it by number. [CODE visa_data.json:482-487, 6374, 31435, 37667; backend/services/legal_research.py:305] VERIFIED

| Waymaker's wording | Official title on law.go.kr | 종류 / 번호 | 발령일 | 시행일 | 구분 | admRulSeq (version) | admRulId | Status |
|---|---|---|---|---|---|---|---|---|
| "F-4 단순노무 취업제한 고시"; corpus: "「재외동포(F-4) 자격의 취업활동 제한범위 고시」(법무부 고시 제2026-35호, 2026.2.12.)" | 재외동포(F-4) 자격의 취업활동 제한범위 고시 | 법무부고시 **제2026-65호** | 2026-02-12 | 2026-02-12 | 폐지제정 | 2100000275060 | 2090230 | VERIFIED_WEB (search row + detail page variables) |
| "「해외투자기업 기술연수생 등에 대한 사증발급인정서 발급 및 관리에 관한 지침」 제5조" | 해외투자기업 기술연수생 등에 대한 사증발급인정서 발급 및 관리에 관한 **훈령** | 법무부훈령 제1414호 | 2022-04-14 | 2022-04-14 | 일부개정 | 2100000210583 | not retrieved [corrected by verifier: admRulId **27428** (admRulLsInfoP JS object). The 연혁 filter search (p6=1) shows the former title "해외투자기업 **산업연수생** 등에 대한 사증발급인정서 발급 및 관리에 관한 **지침**" on 법무부훈령 제533호 (2005-11-30), 제644호 (2008-07-30), 제727호 (2009-09-01, which reads "…등에 관한…") and 제753호 (2009-12-22). The current "기술연수생 … 훈령" title first appears on 제853호 (2012-02-13, 시행 2012-03-01). Waymaker's "기술연수생 … 지침" mixes the new noun with the old suffix, so it matches neither title.] | VERIFIED_WEB (search row) |
| F-5-25 "법무부장관이 정하여 고시하는 금액" (공익사업 투자이민 펀드 30억 원) | 공익사업 투자이민제도 투자대상, 투자금액 등에 관한 기준 고시 | 법무부고시 제2023-319호 | 2023-06-29 | 2023-06-29 | 일부개정 | 2100000225532 | not retrieved [corrected by verifier: admRulId **2109471**] | VERIFIED_WEB (search row); amount not checked |
| "관광·휴양시설 투자이민으로 고시한 대상" (manual-derived text) | 관광·휴양시설 투자이민제 대상지역 지정 절차 고시 | 법무부고시 제2024-588호 | 2024-12-02 | 2024-12-08 | 일부개정 | 2100000250386 | not retrieved [corrected by verifier: admRulId **2075585**] | VERIFIED_WEB (search row) |
| "법무부장관이 고시한 국제결혼 안내프로그램 대상 7개 국가" | 국제결혼 안내프로그램 이수 대상 및 운영사항 고시 | 법무부고시 제2023-695호 | 2023-12-19 | 2024-01-01 | 일부개정 | 2100000232904 | not retrieved [corrected by verifier: admRulId **2037546**] | VERIFIED_WEB (search row); country count not checked |
| "법무부고시 — 제주특별자치도 무사증입국불허국가 및 체류지역 확대허가 국가" (`data/short-stay/rules.json`: 법무부고시 제2022-189호, 2022-06-01) | **not found** | — | — | — | — | — | — | UNVERIFIED: name searches "무사증", "입국불허" and "확대허가" each returned 0 rows [LIVE a01, a03, a07] |
| "외국인 결핵환자 사증발급 및 체류관리 지침" | **not found** | — | — | — | — | — | — | UNVERIFIED: "결핵" returned 6 rows, none from 법무부 [LIVE a05]; probably an internal guideline that is not published |

Related 법무부 rules seen but not referenced: 투자이민협의회 규정 (법무부훈령 제1553호, 2024-12-02) and 공익사업 투자이민 상담센터 설치 및 운영에 관한 규정 (법무부훈령 제917호, 2013-12-16, 제정). [LIVE a04] VERIFIED

Pending versions of administrative rules: each search ran with the 현행+시행예정 filter and returned exactly one row per rule. That suggests no 시행예정 version, but I did not fetch the rules' own 연혁, so the seed records `pending_versions: null`. INFERRED

Not checked: 제8차 한국표준직업분류 (admRulSeq 2100000243058, cited in `docs/audits/hikorea-employment-code-source-audit-2026.md:68`), 청소년 출입·고용금지업소 결정 고시 (여성가족부고시 제2013-52호, quoted in the manual corpus) and the employment-reporting 고시 numbers in `scripts/build_employment_reporting_dataset.py`. UNVERIFIED

## 5. What Waymaker stores (origin/main 0713370)

| Location | What is stored | Assessment |
|---|---|---|
| `docs/source-laws/law_sources_2026_05.json` (15 law rows [corrected by verifier: 14 law rows, lines 2–15 (출입국관리법, 국적법, 난민법 and 재외동포법 trios plus the 재한외국인 처우 기본법 and its 시행령), out of 40 rows in all; this matches the 14 rows at `LAW_SOURCESET_INVENTORY_2026_05.md:38-51`]), `LAW_SOURCESET_INVENTORY_2026_05.md:38-51` | Titles plus `/법령/<name>` routes only; `source_verification_status: OFFICIAL_ROUTE_RECORDED`; several rows say "date verification pending"; inventory `2026-05-v5` | Titles match official titles (VERIFIED for the 12 in scope). Routes resolve (VERIFIED). **No IDs, versions or dates**, so nothing can be checked automatically. The **외국인고용법 trio is missing**, although `law_query_normalizer.py` treats 외국인고용법 as a canonical law. 재한외국인 처우 기본법 rows not checked. |
| `data/source_registry.json:203-216` | One `law_api_placeholder` (`status: not_configured`, version, source_date and last_checked_at all null) | No law identity at all. The unpushed branch `fix/waymaker-qa-2026-10-16` rewrites 36 lines of this file but keeps the same single placeholder (`git show …:data/source_registry.json`), so the conclusion holds for the branch too. VERIFIED |
| `backend/services/law_tools.py:127-129`, `:358-399`, `:890-925` | No hard-coded law IDs. Resolves 법령ID/MST at runtime through DRF `lawSearch.do` / `lawService.do` (needs a registered OC; `LAW_GROUNDING_MODE`) | Nothing stale here. Runtime freshness depends on the API. VERIFIED |
| `backend/services/law_query_normalizer.py:193-210` | Canonical names: 국적법 (+시행령, 시행규칙), 난민법, 재외동포의 출입국과 법적 지위에 관한 법률 (+시행령), 외국인근로자의 고용 등에 관한 법률 (+시행령) | All match official titles exactly. VERIFIED |
| `backend/tests/test_law_tools.py:47,50`, `test_law_cloud_korean_search.py:35-54`, `test_generalized_law_grounding_verification.py:37,106` | Fixture IDs: 출입국관리법 "001386", 시행령 "001387", MST 267581/267999 | **Synthetic.** The real 법령IDs are 001707 and 005256. Fine as mocks, but never promote them into data. [TEST test_law_tools.py + test_generalized_law_grounding_verification.py (ran: pass, 106 passed)] |
| `scripts/status_guidance/author_rules.py:316-318` → generated `data/status-guidance-202609.json:378-586`, `data/guidance-rules-202609.json`, `backend/data/knowledge_deploy/status-guidance-202609.json` (runtime input: `backend/services/knowledge/adapters.py:56`) | Act `mst 272921, effective 2026-01-23`; Decree `mst 289697, effective 2026-09-15`; Rule `mst 289833, effective 2026-09-15`; 법령IDs 001707 / 005256 / 008494 | IDs correct. **Act and Decree versions are stale** (see §6). The Rule version is current, but its 제73조 quote is the 2027 text. |
| `data/form_schemas.json:2959-2968, 3599-3608`; `docs/forms_official/FORM_HELPER_COVERAGE_20260923.md:127` | 출입국관리법 시행규칙 MST 289833 (시행 2026-09-15); 재외동포법 시행규칙 MST 267499 inForceFrom 2025-02-01, pendingAmendment "법무부령 제1124호 (공포 2026-09-15, 시행 2027-09-16)" | **Correct**, including the pending amendment. VERIFIED [verifier addition: the eight 출입국관리법 시행규칙 annex templates (MST 289833 at `data/form_schemas.json:774, 1550, 2325, 4527, 4862, 5142, 5797, 6044`) also carry `pendingAmendment: "법무부령 제1125호 (공포 2026-09-15, 시행 2027-09-16)"`. Waymaker therefore does record the 2027-09-16 date for this rule, although only on the forms and not on 제73조.] |
| `data/nationality_sources.json:341-408`, `data/nationality_service_sources.json:45,61,77` | 국적법 current (2022-09-15 / 2022-10-01); 국적법 개정 lsiSeq 286415 (2026-06-02 / 2026-12-03); 시행령 lsiSeq **243829** (2022-07-11 / 2022-07-12); 시행규칙 lsiSeq **262177** (2024-04-29); all `checkedAt 2026-06-28`, `official_legal_text_identity_verified` | Act and pending amendment correct. **Decree and Rule stale** (see §6). |
| `data/document_help.json:31` | "출입국관리법 시행규칙" link `lsInfoP.do?lsiSeq=266161`, checkedAt 2026-07-02 | **Stale.** 266161 is 법무부령 제1083호 (2024-10-29, two 시행일 rows 2024-10-29 and 2025-01-01) [LIVE h03]. |
| `docs/audit/law_crosscheck_2026_06.md:10-11` | Rule `lsiSeq 283059 (시행 2026-01-23)`; Act `lsiSeq 272921 (시행 2025-07-22)` | Act date **wrong**: 272921's 시행일 is 2026-01-23, and 2025-07-22 is its 공포일. Both superseded. |
| `audits/short-stay-country-checker/b1_b21_not_b22_target_fix_2026_06.md:9-10` | 시행령 lsiSeq 271319; Act lsiSeq 272921 | Superseded (271319 = 대통령령 제35540호, 시행 2025-06-01). |
| `audits/official-external-source-augmentation-2026-06.md:25`, `backend/data/visa_authoring/audit/official_external_source_reconciliation_2026_06.json:84` | 국적법 amendment 286415, effective 2026-12-03, "not treated as current law" | Correct. VERIFIED |
| `visa_data.json:30450, 32712` | 「재외동포의 출입국과 법적지위에 관한 법률」 | Uses the **former** spacing (official since 2008: "법적 지위"). Cosmetic, but it breaks exact-title matching. |
| `visa_data.json:6098, 6374` and others | 「해외투자기업 기술연수생 등에 대한 사증발급인정서 발급 및 관리에 관한 **지침**」 | Official title ends in **훈령** (법무부훈령 제1414호). Waymaker's own manual inventory (`docs/data/2026_06_17_manual_code_inventory.json`) already quotes "…관한 훈령". |
| Manual corpus (`data/manual-corpus/stay_manual_2026_09_18_pdf.json`, `visa_manual_2026_09_01_pdf.json`, `backend/data/sources/manuals/260421_dongpo…`, `260617_*`, `260623_*`; `scripts/extract_dongpo_manual_2026_02.py:7,78`) | "재외동포(F-4) 자격의 취업활동 제한범위 고시 (법무부 고시 제2026-35호, 2026.2.12.)" | law.go.kr shows **제2026-65호**, same date, 폐지제정. This is the manual's own text, so it is not a Waymaker authoring error, but answers that quote the number inherit it. |
| `data/short-stay/rules.json:10432-10437, 10606-10611`; `data/short-stay/fixtures/jeju_b22_notice.json:4-5` | Jeju 고시 "법무부고시 제2022-189호", effective 2022-06-01, from a consular copy dated 2023-09-18, confidence low / needs_refresh | Not on law.go.kr as a 행정규칙. Cannot be refreshed from there. UNVERIFIED |

## 6. Stale or mismatched entries (ranked)

1. **시행규칙 제73조: the quote is future text labelled as current.** The quote at `scripts/status_guidance/author_rules.py:339` and `data/status-guidance-202609.json:561-567` adds 신용카드ㆍ직불카드 everywhere and drops 가목. That is the text effective **2027-09-16**, yet the record carries `mst 289833, effective 2026-09-15, review_state CURRENT_TEXT_READ`. A user-facing line at `data/status-guidance-202609.json:1877` says registration-card fees can be paid "(또는 카드·전자결제)" under 시행규칙 제73조 제1호. The text in force on 2026-10-19 says 외국인등록증 발급·재발급 수수료 are paid "현금 또는 현금 납입을 증명하는 증표". The statute text was VERIFIED; the impact on users is INFERRED. HiKorea or counter practice may already accept cards, but the cited legal basis does not say so before 2027-09-16. This data is read at runtime (`adapters.py:56`, labelled UNREVIEWED). Fix it in `author_rules.py` and regenerate; the data file is generated (`generated_by: scripts/build_status_coverage_manifest.py`).
2. **출입국관리법 stored as `mst 272921 / effective 2026-01-23`; current is 290729 / 2026-10-02** (법률 제21857호, 타법개정). Locations: author_rules.py:316, status-guidance-202609.json (3 article refs: 제35조, 제36조, 제87조), guidance-rules-202609.json and the knowledge_deploy copy. The articles cited are not in the amended list, so their text is probably unchanged (INFERRED), but the version identity is stale. VERIFIED [verifier addition: in the 290729 body, the "2026. 8. 4." markers sit only in 제4조, 제4조의4, 제4조의6, 제29조의2 and 제85조, plus a 부칙 경과조치. The "2025. 7. 22." (20992호) markers sit in 제19조의5, 제94조 and 제99조의3. 제35조 carries only "<개정 2014. 3. 18., 2020. 6. 9.>". On the markers, 제35조, 제36조 and 제87조 are textually the same in 272921 and 290729, so only the version identity is stale. VERIFIED (marker-based). LIVE lsInfoR 290729, 2026-10-19, 200]
3. **출입국관리법 시행령 stored as `mst 289697 / 2026-09-15`; current is 290501 / 2026-10-02** (대통령령 제36728호, 타법개정). Locations: author_rules.py:317 and four article refs (제40, 42, 44, 45조). I did not determine which decree articles the omnibus decree changed, so whether the cited text changed is UNVERIFIED. [corrected by verifier: in the 290501 body, "2026. 9. 29." amendment markers appear only in 제5조의2, 제5조의3 and 제5조의4 (긴급출국금지) and in 제93조 (형사절차와의 관계). The 2026-09-15 (36673호) markers appear in 제48조 and 제88조의12. The cited 제40조, 제42조, 제44조 and 제45조 carry neither, so their text is unchanged and only the version identity is stale. VERIFIED (marker-based). LIVE lsInfoR 290501, 2026-10-19, 200]
4. **국적법 시행령 lsiSeq 243829**, stored with checkedAt 2026-06-28 and marked `official_legal_text_identity_verified`, had already been superseded on **2022-12-20** by 246165 (대통령령 제33082호). It was stale when it was "verified". Locations: `data/nationality_sources.json:371,380-381`, `data/nationality_service_sources.json:45`. VERIFIED
5. **국적법 시행규칙 lsiSeq 262177** (2024-04-29), superseded on **2026-10-02** by 291055 (법무부령 제1161호). Locations: `data/nationality_sources.json:398,407-408`, `data/nationality_service_sources.json:61`. These are the files for the naturalisation forms (별지 서식), so form annex versions may also have moved. VERIFIED (identity); form changes UNVERIFIED.
6. **`data/document_help.json:31`** points at 시행규칙 lsiSeq 266161 (2024-10-29). It was already two versions old when checked on 2026-07-02, and is three versions old now. VERIFIED
7. **`docs/audit/law_crosscheck_2026_06.md:11`** confuses 공포일 with 시행일 for 272921. VERIFIED
8. **F-4 고시 number**: the corpus says 제2026-35호 and law.go.kr says 제2026-65호 (admRulId 2090230). Needs a human check against 관보 or the MOJ notice. VERIFIED (mismatch) [verifier addition: the rule's 연혁-filter search (p6=1) lists predecessors 제2023-187호 (2023-05-01), 제2018-70호, 제2015-29호, 제2010-297호 and 제2009-499호 (제정), all 폐지제정 except the 제정. Before that came "외국국적동포의 취업활동 제한범위에 대한 고시" (제2003-618호, abolished by 제2009-499호). No 제2026-35호 appears anywhere in the rule's history on law.go.kr. LIVE admRulScListR q=취업활동 p6=1 and p6=2,3, 2026-10-19, 200]
9. **Title drift**: "법적지위" (former spacing) and "…관한 지침" (official: 훈령). VERIFIED
10. **Coverage gaps**: the 외국인고용법 trio is absent from `docs/source-laws`. `data/source_registry.json` has no law rows. Waymaker stores nothing at all about the pending **외국인고용법 개정 (2026-12-10 / 2027-06-10)** or **출입국관리법 시행규칙 제73조 (2027-09-16)**. Only the 국적법 and 재외동포법 시행규칙 pending changes are recorded. VERIFIED (grep) [corrected by verifier: partly wrong. `data/form_schemas.json` records the 시행규칙 pending date as `pendingAmendment: "법무부령 제1125호 (공포 2026-09-15, 시행 2027-09-16)"` on eight annex templates (e.g. :780, :1556). What is missing is the link to 제73조: the status-guidance record quotes the 2027 text with `effective 2026-09-15` and has no pending flag. The 외국인고용법 part stands: 0 hits in `docs/source-laws`. The deferred 2027-06-10 articles are 제22조의2 (주거시설의 제공 등) and 제25조 (사업 또는 사업장 변경의 허용), which matters for E-9 workplace-change content (saved `raw/ewa_pend_b.html`, inline "[시행일: 2027. 6. 10.]" markers).]

Not stale (VERIFIED): `form_schemas.json` for both 시행규칙 (289833 and 267499 with the pending 1124호); the 국적법 current-act and amendment rows; the 법령IDs 001707, 005256 and 008494 wherever stored; the canonical titles in `law_query_normalizer.py` and `statute_citation_guard.py`.

## 7. Recommendations

1. Add a law-identity table, for example the seed JSON, to `data/source_registry.json`, keyed by **법령ID + lsiSeq + efYd**. Have the source monitor compare it with `lsHstListR.do` rows, which need no key and are about 20 KB each. That makes "시행예정" and "superseded" checkable without an OC.
2. Make article-level citations carry their own 시행일. A version-level `effective` is wrong for 제73조 now and will be wrong for 외국인고용법 제22조의2 and 제25조 in 2026–27.
3. Fix `author_rules.py:316-318,339` (Act/Decree version, 제73조 quote) and regenerate the status-guidance files. Re-word the `:1877` card-payment line until 2027-09-16, or show both texts with dates.
4. Update `nationality_sources.json`, `nationality_service_sources.json` and `document_help.json` to the current lsiSeq values, and re-verify the 국적법 시행규칙 forms against 291055.
5. Add the 외국인고용법 trio to `docs/source-laws/law_sources_2026_05.json`, and track the 2026-12-10 and 2027-06-10 changes.
6. Record administrative rules with `admRulId` (stable) and `admRulSeq` (version). Correct the 훈령 title. Flag the F-4 고시 number mismatch for manual review. Mark the Jeju 고시 and the 결핵 지침 as "not on law.go.kr; secondary copy only".
7. Do not reuse test-fixture IDs (001386, 001387, 267581) as real identifiers.

## 8. Not verified in this task
- 재한외국인 처우 기본법 (+시행령), which is in the Waymaker inventory; 제주특별법 (lsiSeq 279611 in an audit note); 외국인투자촉진법; HiKorea LawLink. Out of request budget.
- 행정규칙ID for four of the five found rules, their own 연혁 and former titles. [corrected by verifier: the four IDs are now filled (27428, 2109471, 2075585, 2037546; §4). Former titles and 연혁 are filled for the 훈령 and the F-4 고시 (§4, §6 item 8). The 연혁 of the three investment and marriage 고시 is still not checked.]
- English titles ("Immigration Act" vs any official English name) and the content of cited articles beyond 제73조.

## Verification pass

Verifier: adversarial re-check, 2026-10-19. Inline fixes above are tagged `[corrected by verifier: …]` or `[verifier addition: …]`.

**Method.**
- Re-fetch: I sent 39 public GETs to `www.law.go.kr`, spaced 2 s apart, with no key, OC or cookie. All returned 200. The log is `scratchpad/verifier/raw/requests.log`, and small extracts are in `scratchpad/verifier/raw/*_marks.txt`, `v05_v06_art73_extract.txt` and `c_crimproc_extract*.txt`. I deleted the large bodies after extraction because the disk was full.
- Disk incident: the host disk hit ENOSPC after request #4. For several minutes Bash could not start, and no requests were sent in that gap; I re-read local files instead.
- Local checks: I opened every cited `[CODE …]` line in the worktree (0713370, read-only).
- Tests: I re-ran the cited tests. `.venv-check/bin/python -m pytest -q backend/tests/test_law_tools.py backend/tests/test_generalized_law_grounding_verification.py` gave **106 passed** (matches the notes). Adding `test_law_cloud_korean_search.py` gave **111 passed**.

### Verdicts on the 15 headline claims

| # | Claim (short) | Verdict | Primary evidence I checked |
|---|---|---|---|
| 1 | 출입국관리법 001707 = 290729, 법률 제21857호, 공포 2026-08-04, 시행 2026-10-02, 타법개정, no pending version | **confirmed** | LIVE: route `/법령/출입국관리법` iframe → `lsiSeq=290729&efYd=20261002`. lsHstListR 001707: 61 rows; row 1 `('290729','20260804','21857','20261002','Y','타법개정')`, with no "앞으로 시행될 법령" row above it. lsInfoR 290729: ancYd 20260804, ancNo 21857. |
| 2 | 시행령 005256 = 290501, 대통령령 제36728호, 2026-09-29 / 2026-10-02, 타법개정; stored 289697 superseded | **confirmed** | LIVE: lsHstListR 005256 row 1 = 290501 (Y), row 2 = 289697 (36673호, 2026-09-15). lsInfoR 290501 hidden inputs match. CODE `author_rules.py:317` and `status-guidance-202609.json:427` = `"mst": "289697"`. Addition: the cited articles 40, 42, 44 and 45 are unchanged by 36728 (§6 item 3). |
| 3 | 시행규칙 289833 has two 시행일; 제73조 from 2027-09-16; 289833@20270916 listed as 시행예정 | **confirmed** | LIVE: lsHstListR 008494 row 1 = `289833 … 20270916 N` with the "앞으로 시행될 법령" icon, and row 2 = `289833 … 20260915 Y`. 부칙 제1조 of 1125호: "…다만, 제73조의 개정규정은 공포 후 1년이 경과한 날부터 시행한다." |
| 4 | Waymaker's 제73조 quote is the 2027 text but labelled 2026-09-15 / CURRENT_TEXT_READ; a user-facing line says card payment | **confirmed** | LIVE: I compared 제73조 at efYd 20260915 and 20270916. The current text has 1호 = 수입인지 or 전자결제, with 가목 requiring 외국인등록증 fees in 현금/현금 납입 증표; 2호 = 수입증지 or 전자결제; 3호 = 수입인지·현금·증표. The 2027 text moves the 등록증 cash rule into a parenthesis inside 1호, adds 신용카드ㆍ직불카드 to 1호, 2호 and 3호, and makes 가목 "삭제 <2026. 9. 15.>". The quote at `author_rules.py:339` and `status-guidance-202609.json:564` follows the 2027 wording exactly, with `effective 2026-09-15` (:560) and `review_state CURRENT_TEXT_READ` (:567). `:1877` says the 등록증 fee is paid "현금 또는 현금 납입을 증명하는 증표(또는 카드·전자결제)" under 제73조 제1호; the in-force 가목 does not allow card. |
| 5 | Stored Act mst 272921 / 2026-01-23 is superseded by 290729 | **confirmed** | CODE `author_rules.py:316`; `status-guidance-202609.json:379,395` = 272921 (also 3 hits each in `guidance-rules-202609.json` and the knowledge_deploy copy). LIVE 연혁 row 2 = 272921 / 20992호 / 2025-07-22 / 시행 2026-01-23. Addition: the cited articles 35, 36 and 87 are textually unchanged. |
| 6 | 국적법 001435 current 244609; pending 286415 (21725호, 2026-06-02) on 2026-12-03, single date; Waymaker correct | **confirmed** | LIVE: lsHstListR 001435 row 1 = 286415 with the pending icon, a single row; row 2 = 244609 Y. Saved `raw/nata_pend_b.html` 부칙: "공포 후 6개월이 경과한 날부터 시행". CODE `nationality_sources.json:326-327` (2022-09-15 / 2022-10-01) and `:344,353-354` (286415, 2026-06-02 / 2026-12-03). |
| 7 | 국적법 시행령 243829 stored as identity-verified on 2026-06-28, but superseded since 2022-12-20 by 246165 | **confirmed** | LIVE: lsHstListR 002922 row 1 = 246165 (33082호, 2022-12-20, Y), row 2 = 243829 (2022-07-11 / 07-12). CODE `nationality_sources.json:371,380-381,384`; `nationality_service_sources.json:45`. |
| 8 | 국적법 시행규칙 now 291055 (1161호, 2026-10-02); stored 262177 superseded | **confirmed** | LIVE: lsHstListR 006766 row 1 = 291055 Y, row 2 = 262177. lsInfoR 291055 ancNo 01161. CODE `nationality_sources.json:398`; `nationality_service_sources.json:61`. |
| 9 | 외국인고용법 current 276857 (21065호, 타법개정) with an inline 2026-01-02 marker; pending 286817 on 2026-12-10, with 제22조의2 and 제25조 on 2027-06-10; nothing in docs/source-laws | **confirmed** | LIVE: lsHstListR 009542 rows 1–2 = 286817 @20270610 and @20261210 (both pending), row 3 = 276857 Y. lsInfoR 276857: "[시행일: 2026. 1. 2.] 제4조제4항의 개정부분 중 재정경제부에 관한 부분". Saved `ewa_pend_b.html` 부칙 confirms the 6-month / 1-year split. `law_sources_2026_05.json` and the inventory md have 0 hits for 외국인근로자/외국인고용법. |
| 10 | 재외동포법 시행규칙 008011 current 267499 (1087호; 2025-01-01 / 2025-02-01); pending 289831 (1124호) on 2027-09-16; form_schemas matches | **confirmed** | LIVE: lsHstListR 008011 row 1 = 289831 @20270916 (pending, single row), rows 2–3 = 267499 @20250201 (Y) and @20250101. CODE `form_schemas.json:2962-2968, 3602-3608`. |
| 11 | 법령IDs and current versions of the other seven laws, none pending | **confirmed** | LIVE lsHstListR for 011546, 011878, 011885, 001999, 004662, 009657 and 009698: row-1 Y versions are 188376, 273705, 266929, 268553, 284843, 244037 and 271599. No pending icon on any. Row counts 3/10/8/24/29/37/29 match the notes. |
| 12 | F-4 고시 is 법무부고시 제2026-65호 (2026-02-12, 폐지제정, admRulId 2090230, admRulSeq 2100000275060); the corpus says 제2026-35호 | **confirmed** | LIVE: admRulScListR q=취업활동 gives one row, 제2026-65호, 2026.2.12 / 2026.2.12, 폐지제정, 법무부. admRulLsInfoP: `admRulSeq:"2100000275060",admRulId:"2090230"`, `pAncNo='2026-65'`. History filter: no 2026-35 ever. CODE: '제2026-35호' appears in `data/manual-corpus/stay_manual_2026_09_18_pdf.json` (3×), its knowledge_deploy copy and `scripts/extract_dongpo_manual_2026_02.py:7,78`. In all, 31 files carry '2026-35호': manual extracts and corpora under `backend/data/sources/manuals`, `docs/source-manuals/*`, `data/manual-corpus`, `backend/data/knowledge_deploy/manual-corpus`, plus `source_manifest.json` and the script. '2026-65' appears nowhere in the repo. |
| 13 | The trainee rule's official title ends in 훈령 (법무부훈령 제1414호, 2022-04-14); visa_data says 지침 | **confirmed** | LIVE: admRulScListR q=기술연수생 (현행). CODE `visa_data.json:6374` (also :6098 and :6349 in prose). Addition: "…지침" was the former suffix of the older "산업연수생" title (to 2009), renamed in 2012. |
| 14 | The Jeju 고시 (2022-189) and the TB 지침 are not findable on law.go.kr | **confirmed** (OBSERVED absence) | I did not repeat the notes' three Jeju queries. Instead, q=제주 (현행+시행예정) gives 104 rows over 3 pages, none from 법무부/출입국 and none containing 무사증/사증. q=무사증 with the **연혁** filter gives 0 rows. q=결핵환자 gives 2 rows, both 질병관리청/국가데이터처. CODE `short-stay/rules.json:10433-10435`, `visa_data.json:482,37667`. Absence from law.go.kr does not prove the 고시 does not exist; it may sit only in 관보. |
| 15 | source_registry and docs/source-laws hold no law IDs or versions; the branch does not change this | **confirmed** | CODE `source_registry.json:202-216`: one `law_api_placeholder`, `version`/`last_checked_at` null, `status not_configured`. `git show fix/waymaker-qa-2026-10-16:data/source_registry.json`: 16 sources, the same single placeholder; diff 19+/17−. The branch also does not touch author_rules, status-guidance, nationality, document_help, form_schemas or short-stay files. Its visa_data.json keeps "…관한 지침" (3×), "법적지위에" (2×) and no 2026-35/65. |

### Other corrections made inline
- §1: `pEfYd` on admRulLsInfoP is the 발령일, not the 시행일. I also corrected the request-budget itemisation; the total of 60 is right.
- §3 former titles: the 재외동포법 시행령 and 시행규칙 kept "법적지위" spacing until 2016-01-22 and 2009-05-28 respectively.
- §3: the 출입국관리법 2026-10-02 changes have **no** deferred proviso. This was UNVERIFIED and is now VERIFIED via the 형사소송법 21857호 부칙 shown in 290189.
- §5: `law_sources_2026_05.json` has **14** law rows, not 15. `form_schemas.json` also records the 1125호 2027-09-16 pending date.
- §6 items 2 and 3: the cited Act articles (35, 36, 87) and Decree articles (40, 42, 44, 45) are textually unaffected by the newer versions. Only the version identity is stale.
- §6 item 10: partly wrong, as above. The 2027-09-16 date is recorded in form_schemas, but not on 제73조.

### Omissions found and filled
1. admRulId for four rules: 해외투자기업 기술연수생 … 훈령 **27428**; 공익사업 투자이민 기준 고시 **2109471**; 관광·휴양시설 투자이민 대상지역 고시 **2075585**; 국제결혼 안내프로그램 고시 **2037546**. LIVE admRulLsInfoP JS object `admRulSeq:…,admRulId:…`. These are not written into `law_identity_seed.json`: I left the seed unchanged, and its `law_id: null` values for these rows can be filled from this list.
2. Former titles and history for the 훈령 (산업연수생…지침, 2005–2009) and the F-4 고시 (predecessors back to 2003). Seed `former_titles` stays null for now. Suggested values:
   - 훈령: "해외투자기업 산업연수생 등에 대한 사증발급인정서 발급 및 관리에 관한 지침" and "해외투자기업 산업연수생 등에 관한 사증발급인정서 발급 및 관리에 관한 지침".
   - F-4 고시: "외국국적동포의 취업활동 제한범위에 대한 고시".
3. Whether the 출입국관리법 2026-10-02 change has split dates: it does not.
4. Which 시행령 articles 36728호 changed: 제5조의2–4 and 제93조, none of them cited by Waymaker.
5. Stale law snapshots not listed in the notes:
   - `docs/source-manuals/law/crosscheck/lawgokr_act_272921_articles.txt` and `lawgokr_rule_283059_articles.txt` are local law-text copies of superseded versions. A grep of `backend/` and `scripts/` finds no code that reads them.
   - Dated docs `docs/design/ultimate-search-waymaker-audit-20260922.md:15-16`, `docs/audit/immigration-source-conflicts-20260922.md:205` and `audits/trust-phrase-cleanup-2026-06/report.md:12-13` cite 272921/289697/283059. These were correct on their dates and should be read as point-in-time records.
6. The articles deferred to 2027-06-10 in 외국인고용법 286817 are 제22조의2 (주거시설의 제공 등) and 제25조 (사업 또는 사업장 변경의 허용), both relevant to E-9 content.

### Omissions not filled
- 국적법 시행규칙 1161호: which 별지 서식 changed. The 291055 body has no article-level "2026. 10. 2." amendment marker; the date occurs once, inside a 부칙 "제3조(서식에 관한 적용례)". Form-level changes were not determined (UNVERIFIED).
- The 시행령 omnibus decree 36728호's own 단서 (the host view shows `<단서 생략>`). Not checked.
- 시행예정 versions of the four 고시/훈령 other than F-4: still INFERRED from one-row 현행+시행예정 results. I did not fetch any rule-level history endpoint.
- visa_data.json's generic "장관 고시국가" references (`visa_data.json:4791, 4840, 7498`) and "장관고시 21개국" (조기적응프로그램 context) are not mapped to any administrative rule. Not checked (UNVERIFIED).
- 재한외국인 처우 기본법 (+시행령): outside the brief's list of laws and not checked.
- `statute_citation_guard.py` canonical titles (§6 "Not stale"): I did not re-open this file.
