# HiKorea Employment-Information Reporting — Occupation/Industry Code Source Audit (2026)

- **Scope:** Verify the *current, correct* classification sources behind Paradiso's
  HiKorea employment-information reporting helper (직종 / 업종 / 연간소득), and decide
  the source-of-truth for the runtime occupation/industry code tables.
- **Retrieval date:** 2026-06-14 (UTC).
- **Author tooling:** Public web search/fetch. Direct access to every `*.go.kr`
  host (kssc, kostat, data.go.kr, law.go.kr) was **network-blocked (HTTP 403)** in
  the build sandbox; findings below rely on public search-result summaries and
  source titles, plus repository-internal verified files. No login-protected
  HiKorea screen was accessed, automated, or scraped.

---

## 1. What HiKorea employment-information reporting requires

A foreign resident engaged in profit-making activity reports three things on
HiKorea: **직종 (occupation)**, **업종 (industry)**, and **연간소득 (annual income band)**.

| Fact | Finding | Confidence |
| --- | --- | --- |
| Effective date | Online 취업정보 신고제 expanded from **2026-01-02** (pilot 2026-01~06, online-only after). | Primary (MOJ/KIS notices) |
| Target statuses | **E-1 ~ E-10, F-2, F-4, F-6, H-2, D-7, D-8, D-9** doing profit activity (incl. self-employed). | Primary |
| Excluded | **F-5** permanent residents; people not engaged in profit activity. | Primary |
| Change deadline | Report a change of 직종/업종 or annual-income **band** within **15 days**. | Primary |
| Income bands | 7 bands: 소득없음 / 1천만 미만 / 1~2천만 / 2~3천만 / 3~4천만 / 4~5천만 / 5천만 이상. **과세 전 소득** 기준, 구간 변경 시에만 신고 (FAQ Q2). | Primary |
| Filing paths | (a) auto-shown during 방문예약, (b) 전자민원 → 취업정보(변경)신고 (FAQ Q5, 붙임2/3). | Primary |
| Multi-job | Report the **one main job** = 주된 영리활동 (most work hours), incl. 부업·겸업 (FAQ Q8). | Primary |
| Legal basis | 출입국관리법 시행규칙 **제47조 및 제49조의2** (붙임1). | Primary |
| Penalty | Late/no report → 과태료 up to **₩1,000,000**; not automatic — 관할관서장 discretion (FAQ Q4). | Primary |
| **List source** | "직종·업종은 **국가데이터처가 공표하는 표준분류(한국표준직업분류 / 한국표준산업분류)**를 참고" — 붙임2: 직종조회 = **국가데이터처 표준직업분류표**, 업종조회 = **국가데이터처 표준산업분류표**; 확인 = **국가데이터처 통계분류포털 kssc.mods.go.kr** (FAQ Q7, 붙임2). | Primary |

> **This confirms the task premise:** the HiKorea 직종 list is the **한국표준직업분류
> (KSCO)** and the 업종 list is the **한국표준산업분류 (KSIC)** — *not* E-7 visa
> occupation codes, *not* 한국고용직업분류(KECO), *not* NTS business codes. The
> reporting screen requires **both** a 직종 and a 업종, so the helper shows both.

**Sources:**
- **Official MOJ announcement attachments (committed, retrieved 2026-06-15):**
  `data/sources/hikorea_employment_reporting_overview.hwpx` (붙임1 개요),
  `…_procedure_visit.hwpx` (붙임2 신고 절차: 직종조회/업종조회/연간소득),
  `…_faq.docx` (붙임4 FAQ Q1–Q8).
- 법무부 보도자료 / 재외동포신문 (2026-06-14): https://www.dongponews.net/news/articleView.html?idxno=55810
- 아시아한인회총연합회 공지: https://asia.korean.net/bbs/board.php?bo_table=notice&wr_id=484
- EKW 동포세계신문, "새해 달라지는 '외국인 취업정보 온라인 신고제' 이해하기": https://www.ekw.co.kr/news/articleView.html?idxno=20145

---

## 2. Occupation classification — current effective version

| Field | Value |
| --- | --- |
| Classification | **제8차 한국표준직업분류 (KSCO 8th revision)** |
| Short name | **KSCO8** |
| Announcement no. | **통계청 고시 제2024-328호** |
| Announcement date | **2024-07-01** |
| Effective date | **2025-01-01** |
| Predecessor | 제7차 (통계청 고시 제2017-191호, 시행 2018) |
| Structure | **대분류 10 / 중분류 57 / 소분류 167 / 세분류 495 / 세세분류 1,270 = 1,999 항목** |
| Official table | 국가법령정보센터 행정규칙 + 국가데이터처(통계청) 통계분류포털 (HWP/PDF downloads) |

**What the sources prove:** KSCO8 is the *current* occupation classification
(effective 2025-01-01), so any HiKorea reporting helper must use the 8th — not the
7th — revision. The structural item counts (10/57/167/495/1270 = 1,999) were
returned consistently by official-portal-derived search summaries.

**Sources (retrieved 2026-06-14):**
- 국가법령정보센터 행정규칙 "제8차 한국표준직업분류": https://www.law.go.kr/admRulLsInfoP.do?admRulSeq=2100000243058 *(primary; 403 to fetcher, title/metadata via search)*
- 통계청 고시 제2024-328호 게시: https://kostat.go.kr/board.es?mid=a10403040000&bid=107&act=view&list_no=431582
- 국가데이터처 동일 고시 미러: https://mods.go.kr/board.es?mid=a10403040000&bid=107&act=view&list_no=431582
- 정책브리핑 보도자료, "제8차 한국표준직업분류 개정·고시": https://www.korea.kr/briefing/pressReleaseView.do?newsId=156638717

---

## 3. Industry classification — current effective version

| Field | Value |
| --- | --- |
| Classification | **제11차 한국표준산업분류 (KSIC 11th revision)** |
| Short name | **KSIC11** |
| Announcement no. | **통계청 고시 제2024-2호** (부칙개정 **제2024-203호**) |
| Announcement date | **2024-01-01** |
| Effective date | **2024-07-01** |
| Predecessor | 제10차 (2017) |
| Structure | **대분류 21 / 중분류 77 / 소분류 234 / 세분류 501 / 세세분류 1,205 = 2,038 항목** |
| Official table | 국가데이터처(통계청) 통계분류포털: "한국표준산업분류 제11차 개정 해설서(신구연계표 포함)" PDF |

**What the sources prove:** KSIC11 is the current industry classification
(effective 2024-07-01). The repository's existing runtime *industry* rows already
match KSIC11 (see §5).

**Sources (retrieved 2026-06-14):**
- 통계청 고시 제2024-2호: https://mods.go.kr/board.es?mid=a10403040000&bid=107&act=view&list_no=428660
- 부칙개정 제2024-203호: https://kostat.go.kr/board.es?mid=a10403040000&bid=107&act=view&list_no=430619
- 제11차 해설서(신구연계표 포함) PDF (kssc): http://kssc.kostat.go.kr/ksscNew_web/upload/4.한국표준산업분류%20제11차%20개정%20해설서(신구연계표%20포함)_20240102092345.pdf
- KDI 경제교육·정보센터 요약: https://eiec.kdi.re.kr/policy/materialView.do?num=246562

---

## 4. Is there a public HiKorea code-lookup endpoint?

- The actual 직종조회/업종조회 widgets live inside the **login-protected** HiKorea
  reporting flow. No stable *public, unauthenticated* JSON endpoint or HTML code
  list was found.
- The underlying lists are the **국가데이터처 통계분류포털** classifications, which are
  the public, citable source. We therefore key the helper off the published
  KSCO8/KSIC11 tables, not off any HiKorea-internal endpoint.
- **Boundary respected:** no authentication bypass, no automated access to private
  user screens. Where login-walled data could not be independently retrieved, it
  is documented as a limitation (see §7).

---

## 5. Runtime audit summary (see also `data/audits/jobcode_runtime_audit.json`)

| Table | Before (runtime) | Edition detected | After |
| --- | --- | --- | --- |
| 직종 (occupation) | 1,899 rows | **제7차 (WRONG)** — `42 = 돌봄·보건 및 개인 생활 서비스직`, no code 45 | **제8차 KSCO8** from the official KSCO8↔ISCO08 linkage: 대분류10/중분류57/소분류167/세분류494 = **728 rows** (+ EN names at 세분류). 세세분류(5-digit, 1,270) pending the KSCO-only 분류항목표 |
| 업종 (industry) | 2,038 rows | **제11차 KSIC11 (CORRECT)** | KSIC11 2,038 rows, enriched (level/parent/path/search terms/metadata) |

> **Update (2026-06-15):** the maintainer supplied the official **KSCO8↔ISCO08
> 연계표** Excel (`data/sources/ksco8_isco08_linkage_2026.xlsx`). Its KSCO side was
> extracted (`scripts/convert_ksco8_isco_linkage.py`) to 728 rows across 4 levels —
> the upper 3 levels (10/57/167) match the official structure **exactly**, and
> 세분류 is 494 (both linkage sheets agree; one KSCO-only unit has no ISCO match —
> not fabricated). This replaces the earlier 67-row 대·중분류 seed. The 5-digit
> 세세분류 layer does not exist in an ISCO linkage and still needs the KSCO-only
> 분류항목표; the pipeline auto-upgrades to the full 1,999 rows when that file is
> dropped at `data/generated/employment_reporting_ksco8_full_candidate.csv`.

**Key proof the old occupation table was 제7차, not KSCO8:** the previous runtime
had only 4 service middles (41–44) with `42 = 돌봄·보건 및 개인 생활 서비스직`, whereas
KSCO8 splits these into 5 middles — `42 돌봄 및 보건`, `43 개인 생활`, `44 운송 및 여가`,
`45 조리 및 음식`. The previous `source` string ("공공데이터포털 …_20250901") was a
public-data-portal label that did not reflect the actual 7th-edition content.

### 5a. User-provided "KSCO8" text was 제7차

During this work the maintainer supplied a plain-text occupation table believed to
be KSCO8. Cross-check (authorized) showed it is **제7차**, not 제8차:

- Parses to **1,900 lines / 1,899 unique codes** with level shape **10/52/156/451/1231**
  (≈ 7th edition), **not** the KSCO8 shape 10/57/167/495/1270 = 1,999.
- **99.4 %** identical to the existing (7th-edition) runtime — 1,898 shared codes,
  1,882 identical names; the 16 "differences" are only a middle-dot glyph variation
  (`·` U+00B7 vs `∙` U+2219).
- Service sector has 4 middles (41–44), `42 = 돌봄·보건 및 개인 생활 서비스직`, **no code 45**.
- Contains one duplicate code (`2722` used for both 행정사 and 자산 운용가).

It is preserved for reference as
`data/sources/ksco7th_provided_text_2026-06-14.txt` and is **not** used as the
runtime occupation source. It is a viable input for a future 7th→8th crosswalk.

---

## 6. Source-of-truth decision

1. **직종 (occupation) = 제8차 한국표준직업분류 (KSCO8).** Runtime is built from the
   official **KSCO8↔ISCO08 linkage** Excel (`data/sources/ksco8_isco08_linkage_2026.xlsx`)
   via `scripts/convert_ksco8_isco_linkage.py` → 728 rows (대/중/소/세분류, service
   sector correctly split 42–45, EN at 세분류). The repo's 67-row 대·중분류 seed
   remains a fallback. When the official KSCO-only full table is extracted to
   `data/generated/employment_reporting_ksco8_full_candidate.csv` (1,999 rows incl.
   세세분류), the build script picks it up automatically — **no code change required.**
2. **업종 (industry) = 제11차 한국표준산업분류 (KSIC11).** Runtime uses the full,
   already-correct 2,038-row table, snapshotted to
   `data/sources/ksic11_full_2038.csv` and enriched.
3. Build is reproducible via `python3 scripts/build_employment_reporting_dataset.py`.
4. Metadata in `data/jobcode_master.json` records classification, short name,
   announcement number/date, effective date, expected full-table counts, and the
   actual runtime counts/coverage.

---

## 7. Known limitations

- **Sandbox network policy blocks every `*.go.kr` host (HTTP 403)** (also namu.wiki
  and Wikipedia); WebFetch egress here is effectively limited to `raw.githubusercontent.com`.
  Official tables can't be downloaded in-sandbox. The maintainer supplied the
  official **KSCO8↔ISCO08 linkage** Excel, which yields 4 of 5 KSCO levels (728 rows).
  The remaining **세세분류 (5-digit, 1,270)** layer does not exist in any ISCO linkage
  and still needs the **KSCO-only 분류항목표** (kssc 통계분류포털). The reproducible
  pipeline closes that last gap the moment the file is supplied — no code change.
- Web *search summaries* (not raw official pages) were the practical channel for
  some facts; structural counts were corroborated across multiple summaries but
  should be re-confirmed against the raw 고시 when network access allows.
- The helper deliberately stops at **reference search**. Final codes must be
  confirmed on the live HiKorea screen or via **1345**.
- English names (`name_en`) are populated at **세분류(unit)** level from the ISCO
  linkage's 영문명; 대/중/소분류 EN remain `null`.

---

## 8. "Not this" — what these codes are NOT

| Not this | Why it matters |
| --- | --- |
| **E-7 visa 직종코드** | E-7 eligibility uses a separate MOJ occupation list with its own permitted-occupation logic. KSCO8 here is only for *reporting* what you do; it does not判定 visa eligibility or suitability. |
| **한국고용직업분류 (KECO)** | KECO is a different classification (employment/job-seeking oriented, 4-digit). HiKorea reporting uses 한국표준직업분류 (KSCO), not KECO. |
| **국세청 업종코드 (NTS business codes)** | NTS codes are for tax filing and differ structurally from KSIC. 업종 here = 한국표준산업분류 (KSIC11). |
| **Eligibility / 자격외활동 screening** | This dataset never determines stay-status permission, E-7 suitability, or whether 자격외활동 허가 is required. It is a reporting-aid lookup only. |

`data/jobcode_master.json → not_this` encodes this boundary for runtime consumers.
