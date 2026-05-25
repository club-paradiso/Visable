# `visa_data.json` Full Record Audit (PR B, post PR #155)

Branch: `data/rebuild-2026-05-21-manual-crosswalk`
Audit date: 2026-05-25
Generator: `scripts/regenerate_2026_05_21_manual_crosswalk.py`

> **This document is an internal audit artifact. It is not legal advice and is not an official immigration decision.**

> **Supersedes:** This audit supersedes the pre-PR #155 record audit built against the earlier **774-page** stay PDF under the "source_date unresolved / PDFs not accessible" assumptions. PR #155 installed the canonical 2026-05-21 PDFs (visa 484p, stay **777p**); stay page anchors below are re-derived from the committed canonical source.

> **Source note:** Findings refer to the canonical 2026-05-21 PDFs at `docs/source-manuals/2026-05/`. Manual sections record **location** only and do not verify any record.

---

## Summary

| Metric | Count |
|---|---:|
| Total `visa_data.json` records | 58 |
| Helper / non-manual records (`missing`) | 17 |
| Manual-dependent records | 41 |
| `verified=false` (all manual-dependent) | 41 |
| `needsManualReview=true` (all manual-dependent) | 41 |
| Records with stale `2026.3` date marker | 1 (F-6 income note, 3 occurrences) |
| Records with duplicate code `D-4-2K` | 2 (indices 24 and 55) |
| **Changes to `visa_data.json` in this PR** | **0** |

### Classification summary (6-way taxonomy)

| Classification | Count | Records |
|---|---:|---|
| `confirmed` | 30 | Standard manual-dependent records with high-confidence anchors |
| `partial` | 4 | E-2 (stay no-header), E-5/E-6 (visa no-header), F-5 (split §32/§36) |
| `missing` | 17 | Helper / scenario / FAQ / infrastructure records |
| `duplicate` | 2 | D-4-2K indices 24 and 55 |
| `stale` | 3 | F-4, H-2 (Feb-2026 sub-manual), F-6 (2026.3 income note) |
| `unresolved` | 2 | K-STAR, REGION-S (large special sections) |

> `confirmed` = manual section located with high confidence. It does **not** mean data-verified; every manual-dependent record stays `verified=false` / `needsManualReview=true`.

---

## `missing` — Helper Records (indices 0–15, 46)

17 records with no `sourceManualStatus` block; not sourced from the immigration manuals. No changes.

| Index | Code | Name | Type |
|---:|---|---|---|
| 0 | K-ETA | 전자여행허가 (K-ETA) 종합 가이드 | faq |
| 1 | TB-1 | 결핵 고위험 국가 진단서 제출 기준 | scn |
| 2 | SCN-1 | 글로벌 의사결정 매트릭스 | scn |
| 3 | SCN-2 | 실무 변수 체크리스트 | scn |
| 4 | SCN-3 | C-3 (단기) 자격변경 시나리오 | scn |
| 5 | SCN-4 | F-1-6 (혼인단절) 타이밍 시나리오 | scn |
| 6 | SCN-5 | F-4/H-2 (동포) 제약 시나리오 | scn |
| 7 | SCN-6 | 오버스테이 (불법체류) 시나리오 | scn |
| 8 | OVS-1 | 불법체류다발국가 목록 | scn |
| 9 | NHIS-1 | 국외 체류자 건강보험 면제·감면 | nhis |
| 10 | FAQ-1 | 외국인등록 및 체류지 변경 | faq |
| 11 | FAQ-2 | 체류기간 연장·자격 변경 | faq |
| 12 | FAQ-3 | 재입국허가 | faq |
| 13 | FAQ-4 | 전자팩스·오버스테이·국적 | faq |
| 14 | VW-1 | 무사증·사증면제 구분 | faq |
| 15 | COM-1 | 비자 공통 구비서류·팁 | faq |
| 46 | RF-1 | 난민인정신청 제출서류 안내 | scn |

---

## Manual-Dependent Records — record-by-record (41 records)

All have `verified=false`, `needsManualReview=true`. Stay page anchors are re-derived from the 777-page PDF. None changed in this PR.

#### B-1 (16) — 사증면제협정 · `confirmed` · PR C
Visa §4 pp.14–21; Stay §4 p.24. 67개국 treaty list; `dataDate=2026-04-14` (immigration.go.kr, not the manual).

#### B-2 (17) — 관광통과·무사증 · `confirmed` · PR C
Visa §5 pp.22–24; Stay §5 p.25. 45개국 무사증; `dataDate=2026-04-14`.

#### C-3 (18) — 단기방문 · `confirmed` · PR C
Visa §7 pp.27–50 (C-3-1..C-3-8); Stay §7 pp.27–28. visaIssuance=needs_review.

#### C-4 (19) — 단기취업 · `confirmed` · PR C
Visa §8 pp.51–59; Stay §8 pp.29–31.

#### D-1 (20) — 문화예술 · `confirmed` · PR C
Visa §9 pp.60–61; Stay §9 pp.32–34.

#### D-2 (21) — 유학 · `confirmed` · PR C
Visa §10 pp.62–69; Stay §10 pp.35–55. Active grounding `d2_extension_2026_05` cites stay pp.43–44.

#### D-3 (22) — 기술연수 · `confirmed` · PR C
Visa §11 pp.70–72; Stay §11 pp.56–82.

#### D-4 (23) — 일반연수 · `confirmed` · PR C
Visa §12 pp.73–87; Stay §12 pp.83–101. Active grounding `d4_extension_2026_05` cites stay pp.90–91. Parent of the duplicated D-4-2K code (see below).

#### D-4-2K (24) — 한국어연수(K-연수생) · `duplicate` · PR D
Code shared with index 55. K-연수생 어학연수. Visa §12 pp.73–87; Stay §12 pp.83–101. `dataDate` blank.

#### D-7 (25) — 주재 · `confirmed` · PR C
Visa §15 pp.92–101; Stay §15 **pp.108–114** (re-derived).

#### D-8 (26) — 기업투자 · `confirmed` · PR C
Visa §16 pp.102–115; Stay §16 **pp.115–129**. D-8 precedes D-9 in normal page order (pre-#155 swap anomaly does NOT reproduce).

#### D-9 (27) — 무역경영 · `confirmed` · PR C
Visa §17 pp.116–121; Stay §17 **pp.130–141** (re-derived; pre-#155 map had p112–114).

#### D-10 (28) — 구직 · `confirmed` · PR C
Visa §18 pp.122–135; Stay §18 pp.142–165. D-10-1/2/3/T; D-10-T cross-refs §39 탑티어 (stay p670+).

#### E-1 (29) — 교수 · `confirmed` · PR C
Visa §19 pp.136–141; Stay §19 pp.166–175.

#### E-2 (30) — 회화지도 · `partial` · PR C
Visa §20 pp.142–149; Stay §20 ~pp.176–184 (no dedicated stay header).

#### E-3 (31) — 연구 · `confirmed` · PR C
Visa §21 pp.150–156; Stay §21 pp.185–194.

#### E-4 (32) — 기술지도 · `confirmed` · PR C
Visa §22 pp.157–163; Stay §22 pp.195–199.

#### E-5 (33) — 전문직업 · `partial` · PR C
Visa §23 ~pp.164–167 (no dedicated visa header); Stay §23 pp.200–204.

#### E-6 (34) — 예술흥행 · `partial` · PR C
Visa §24 ~pp.164–167 (no dedicated visa header); Stay §24 pp.205–211.

#### E-7 (35) — 특정활동 · `confirmed` · PR C
Visa §25 pp.168–277 (110pp); Stay §25 pp.212–323 (112pp). Active grounding `e7_extension_2026_05` cites stay p.226. E-7-1/2/3/4/S/Y/T/91. `high` risk (length + sub-codes).

#### E-8 (36) — 계절근로 · `confirmed` · PR C
Visa §26 pp.278–283; Stay §26 pp.324–325.

#### E-9 (37) — 비전문취업 · `confirmed` · PR C
Visa §27 pp.284–293; Stay §27 pp.326–335.

#### E-10 (38) — 선원취업 · `confirmed` · PR C
Visa §28 pp.294–296; Stay §28 pp.336–340.

#### F-1 (39) — 방문동거 · `confirmed` · PR C
Visa §29 pp.297–307; Stay §29 pp.341–359.

#### F-2 (40) — 거주 · `confirmed` · PR C
Visa §30 pp.308–312; Stay §30 **pp.360–420** (re-derived). F-2-2/3/7/99/T sub-codes incl. F-2-T.

#### F-3 (41) — 동반 · `confirmed` · PR C
Visa §31 pp.313–317; Stay §31 **pp.421–425** (re-derived).

#### F-4 (42) — 재외동포 · `stale` · PR D
Visa §32 pointer "※ 38.번 참조"; content §38 pp.379–444. Stay §36 외국국적동포 관련 **pp.518–584** (re-derived). `dataDate=2026-02-12` (Feb-2026 sub-manual).

#### F-5 (43) — 영주 · `partial` · PR C
Visa §33 pp.318–323 (+ §38 동포 F-5); Stay §32 **pp.426–473** (re-derived). Stay §32 excludes 동포/난민 (under §36/§34).

#### F-6 (44) — 결혼이민 · `stale` · PR D
Visa §34 pp.324–335; Stay §33 **pp.474–497** (re-derived). **STALE:** F-6 income note still contains `"2026.3"` (3 occurrences). PR #145 blocker, unpatched.

#### G-1 (45) — 기타(난민등) · `confirmed` · PR C
Visa §35 pp.336–342; Stay §34 **pp.498–513** (re-derived).

#### H-1 (47) — 관광취업 · `confirmed` · PR C
Visa §36 pp.343–378 (36pp); Stay §35 **pp.514–517** (re-derived, 4pp).

#### H-2 (48) — 방문취업 (신규발급 중단) · `stale` · PR D
Visa §38 pp.379–444 (same §38 as F-4); Stay §36 **pp.518–584** (re-derived). 신규발급 중단 since 2026-02-12. `dataDate=2026-02-12` (Feb-2026 sub-manual).

#### A-1 (49) — 외교 · `confirmed` · PR C
Visa §1 pp.7–9; Stay §1 pp.14–17.

#### A-2 (50) — 공무 · `confirmed` · PR C
Visa §2 pp.10–12; Stay §2 pp.18–20.

#### A-3 (51) — 협정 · `confirmed` · PR C
Visa §3 p.13 (one page); Stay §3 pp.21–23.

#### C-1 (52) — 일시취재 · `confirmed` · PR C
Visa §6 pp.25–26; Stay §6 p.26.

#### D-5 (53) — 취재 · `confirmed` · PR C
Visa §13 pp.88–89; Stay §13 pp.102–104.

#### D-6 (54) — 종교 · `confirmed` · PR C
Visa §14 pp.90–91; Stay §14 pp.105–107.

#### D-4-2K (55) — 기업맞춤형인턴십(K-Trainee) · `duplicate` · PR D
Code shared with index 24. `dataDate=2025-10-29 (법무부 K-Trainee 체류자격 신설 시행)`; `dataBadge="2025.10.29 신설 (2년 시범운영)"`. Visa §12 pp.73–87; Stay §12 pp.83–101. Needs a distinct code (e.g. D-4-2T).

#### K-STAR (56) — K-STAR 비자트랙 · `unresolved` · PR D
Visa §40 pp.456–484 (29pp); Stay §41 **pp.749–777** (re-derived; was 746–774, +3 pages incl. 우수인재 붙임 7–12 at pp.769–777). All fields `needsManualReview=true`.

#### REGION-S (57) — 지역특화·광역형 비자 시범사업 · `unresolved` · PR D
Stay §37 지역특화형비자 **pp.585–654** + Stay §40 광역형 비자 시범사업 **pp.686–748** (re-derived). No visa section. Models both programs; all fields `needsManualReview=true`.

---

## Follow-up PR queue

### PR C — safe source-grounded metadata / doc-ref updates only (34 records)
All `confirmed` + `partial` records above. Update `sourceManualStatus` manual page citations to the re-derived 484-page visa / 777-page stay anchors, plus the doc_master.json hygiene cleanup (12 corrupted ids + `doc_arc_fee`). **No** eligibility/fee/income/document-content change; no `verified` advance; no `needsManualReview` removal.

### PR D — limited requiredDocuments / content patches, page-cited only (7 records)

| Priority | Record(s) | Issue | Target pages (777-page stay) |
|---:|---|---|---|
| 1 | F-6 | Stale 2026.3 income note; F-6-1 income eligibility | Stay §33 pp.474–497 + Visa §34 pp.324–335 |
| 2 | D-4-2K (24+55) | Duplicate code; K-연수생 vs K-Trainee disambiguation | Visa §12 pp.73–87 + Stay §12 pp.83–101 |
| 3 | F-4 + H-2 | Feb-2026 sub-manual extraction; H-2 신규발급 중단 | Stay §36 pp.518–584 |
| 4 | K-STAR | Full K-STAR sub-manual extraction (incl. 우수인재 붙임 7–12) | Visa §40 pp.456–484 + Stay §41 pp.749–777 |
| 5 | REGION-S | 지역특화형 + 광역형 extraction | Stay §37 pp.585–654 + Stay §40 pp.686–748 |

---

## Legal Disclaimer

Paradiso is reference software. Nothing in this audit, the reviewed JSON records, or any rendered output constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. All records audited here carry `needsManualReview=true` and must be treated as unverified until a human reviewer confirms the source. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
