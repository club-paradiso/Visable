# `visa_data.json` Full Record Audit — 2026.5 Manual Update

Branch: `data/audit-2026-05-21-manual-update-json`
Audit date: 2026-05-24

> **This document is an internal audit artifact. It is not legal advice and is not an official immigration decision.**

> **Source-identity caveat:** The user-attached 2026-05-21 PDFs are not accessible from this remote Linux environment. All findings below refer to the repo's committed "2026.5" PDFs (PDF internal creation date 2026-05-07).

---

## Summary

| Metric | Count |
|---|---:|
| Total `visa_data.json` records | 58 |
| Helper / non-manual records | 17 |
| Manual-dependent records | 41 |
| `verified=false` (all manual-dependent) | 41 |
| `needsManualReview=true` (all manual-dependent) | 41 |
| Records with stale `2026.3` date marker | 1 (F-6 income note) |
| Records with duplicate code `D-4-2K` | 2 (indices 24 and 55) |
| **Changes to `visa_data.json` in this PR** | **0** |

### Classification summary

| Classification | Count |
|---|---:|
| `helper-no-manual-status` | 17 |
| `manual-dependent-generic-2026.5-unverified` | 34 |
| `manual-dependent-duplicate-code` | 2 |
| `manual-dependent-feb-sub-manual` | 2 (F-4, H-2) |
| `manual-dependent-stale-income-marker` | 1 (F-6) |
| `manual-dependent-large-special-section` | 2 (K-STAR, REGION-S) |

---

## Helper Records (indices 0–15, RF-1)

The following 17 records have no `sourceManualStatus` block and are not sourced from the immigration manuals. No changes required or made.

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

## Manual-Dependent Records: Full Record-by-Record Audit

All 41 manual-dependent records have `sourceManualStatus.verified=false` and `sourceManualStatus.needsManualReview=true`. None was changed in this PR.

### Records 16–57 (manual-dependent)

#### B-1 (index 16) — 사증면제협정
- `visaManualVersion="2026.5"`, `stayManualVersion="2026.5"`, `dataDate="2026-04-14 (immigration.go.kr 공식 수치)"`
- Visa §4 pp.14–21; Stay §4 p.24.
- 67개국 treaty list. `dataDate` is 2026-04-14 (confirmed from immigration.go.kr, not the manual).
- Extension ref: stay p.24 (auto_extracted_needs_review).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### B-2 (index 17) — 관광통과·무사증
- `dataDate="2026-04-14 (immigration.go.kr 공식 수치)"`
- Visa §5 pp.22–24; Stay §5 p.25.
- 45개국 무사증 list. dataDate confirmed from immigration.go.kr.
- Extension ref: stay p.25 (auto_extracted_needs_review).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### C-3 (index 18) — 단기방문
- Visa §7 pp.27–50 (24 pages, C-3-1 through C-3-8); Stay §7 pp.27–28.
- visaIssuance manualRef = `needs_review`. Extension ref: stay pp.27–28.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### C-4 (index 19) — 단기취업
- Visa §8 pp.51–59; Stay §8 pp.29–31.
- Extension ref: stay p.31; registration: stay pp.29–31.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### D-1 (index 20) — 문화예술
- Visa §9 pp.60–61; Stay §9 pp.32–34.
- Extension ref: stay p.33.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### D-2 (index 21) — 유학
- Visa §10 pp.62–69; Stay §10 pp.35–55.
- **Active grounding**: `d2_extension_2026_05` cites stay pp.43–44 (D-2 extension document list, high confidence).
- Extension ref: stay pp.42–44 (auto_extracted_needs_review).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### D-3 (index 22) — 기술연수
- Visa §11 pp.70–72; Stay §11 pp.56–82.
- Extension ref: stay p.56.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### D-4 (index 23) — 일반연수
- Visa §12 pp.73–87; Stay §12 pp.83–101.
- **Active grounding**: `d4_extension_2026_05` cites stay pp.90–91 (D-4-1/D-4-7 어학연수생 extension, high confidence).
- Extension ref: stay p.90. **D-4-2K code duplication** (see below).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### D-4-2K (index 24) — 한국어연수(K-연수생) **[DUPLICATE CODE]**
- Code `D-4-2K` shared with index 55. This entry = K-연수생 어학연수.
- Visa §12 pp.73–87; Stay §12 pp.83–101.
- `dataDate` is blank. Extension ref: stay p.90.
- **Status**: `needsManualReview=true`. `DUPLICATE CODE` — requires follow-up PR to disambiguate.

#### D-7 (index 25) — 주재
- Visa §15 pp.92–101; Stay §15 pp.108–111.
- Extension ref: stay p.112.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### D-8 (index 26) — 기업투자
- Visa §16 pp.102–115; Stay §16 pp.115–129.
- Extension ref: stay p.122. Body-order anomaly: D-9 (p112–114) prints before D-8 (p115+) in stay.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### D-9 (index 27) — 무역경영
- Visa §17 pp.116–121; Stay §17 pp.112–114.
- Extension ref: stay p.133. Body-order anomaly: stay D-9 (p112–114) before D-8 (p115+).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### D-10 (index 28) — 구직
- Visa §18 pp.122–135; Stay §18 pp.142–165.
- Contains D-10-1, D-10-2, D-10-3, D-10-T sub-codes. D-10-T cross-references §39 탑티어 (stay p.667+).
- Extension ref: stay p.155.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### E-1 (index 29) — 교수
- Visa §19 pp.136–141; Stay §19 pp.166–175.
- Extension ref: stay p.172.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### E-2 (index 30) — 회화지도
- Visa §20 pp.142–149; Stay §20 ~pp.176–184 (no dedicated header in stay).
- Extension ref: stay p.180 (needs_manual_review).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### E-3 (index 31) — 연구
- Visa §21 pp.150–156; Stay §21 pp.185–194.
- Extension ref: stay p.193.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### E-4 (index 32) — 기술지도
- Visa §22 pp.157–163; Stay §22 pp.195–199.
- Extension ref: stay p.199.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### E-5 (index 33) — 전문직업
- Visa §23 ~pp.164–167 (no dedicated header in visa); Stay §23 pp.200–204.
- Extension ref: stay p.203.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### E-6 (index 34) — 예술흥행
- Visa §24 ~pp.164–167 (no dedicated header in visa); Stay §24 pp.205–211.
- Extension ref: stay p.210.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### E-7 (index 35) — 특정활동
- Visa §25 pp.168–277 (110 pp); Stay §25 pp.212–323 (112 pp).
- **Active grounding**: `e7_extension_2026_05` cites stay p.226 (general E-7 extension document list, high confidence).
- Contains E-7-1, E-7-2, E-7-3, E-7-4, E-7-S, E-7-Y, E-7-T, E-7-91 sub-codes.
- **Status**: `needsManualReview=true`. No stale marker. `high` risk due to length and sub-code complexity. Action: `needs-page-review`.

#### E-8 (index 36) — 계절근로
- Visa §26 pp.278–283; Stay §26 pp.324–325.
- Extension ref: stay p.325.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### E-9 (index 37) — 비전문취업
- Visa §27 pp.284–293; Stay §27 pp.326–335.
- Extension ref: stay p.329.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### E-10 (index 38) — 선원취업
- Visa §28 pp.294–296; Stay §28 pp.336–340.
- Extension ref: stay p.337 (needs_manual_review).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### F-1 (index 39) — 방문동거
- Visa §29 pp.297–307; Stay §29 pp.341–359.
- Extension ref: stay p.351 (needs_manual_review).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### F-2 (index 40) — 거주
- Visa §30 pp.308–312; Stay §30 pp.360–424 (65 pp).
- Contains F-2-2, F-2-3, F-2-7, F-2-99, F-2-T sub-codes.
- Extension ref: stay p.394 (needs_manual_review).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### F-3 (index 41) — 동반
- Visa §31 pp.313–317; Stay §31 pp.425–441.
- Extension ref: stay pp.425–428.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### F-4 (index 42) — 재외동포 **[FOLLOW-UP PR REQUIRED]**
- Visa §32: "※ 38.번 참조" (pointer only). Content: §38 외국국적동포 sub-manual pp.379–444.
- Stay §36 외국국적동포 관련 pp.522–588.
- `dataDate="2026-02-12 (법무부 동포체류자격 통합 시행)"`. Content sourced from a Feb 2026 sub-manual.
- Extension ref: stay p.534 (auto_extracted_needs_review).
- **Status**: `needsManualReview=true`. Stale: Feb 2026 sub-manual. Action: `needs-followup-pr`.

#### F-5 (index 43) — 영주
- Visa §33 pp.318–323 (plus §38 동포 F-5 coverage); Stay §32 pp.442–477.
- Stay §32 explicitly excludes 동포 and 난민 (covered under §36 and §34 respectively).
- Extension ref: stay p.429 (auto_extracted_needs_review).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### F-6 (index 44) — 결혼이민 **[FOLLOW-UP PR REQUIRED]**
- Visa §34 pp.324–335; Stay §33 pp.478–501.
- **STALE MARKER**: F-6 income note in `visa_data.json` still contains the string `"2026.3"`. This was the blocker for PR #145.
- Extension docs: stay pp.494–499 (`manual_page_extract_needs_review`).
- visaIssuance, statusChange: `needs_review`.
- **Status**: `needsManualReview=true`. Stale: 2026.3 income note. Action: `needs-followup-pr`.

#### G-1 (index 45) — 기타(난민등)
- Visa §35 pp.336–342; Stay §34 pp.502–517.
- Extension ref: stay p.513 (auto_extracted_needs_review).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### H-1 (index 47) — 관광취업
- Visa §36 pp.343–378 (36 pp); Stay §35 pp.518–521 (4 pp).
- Extension ref: stay p.521 (auto_extracted_needs_review).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### H-2 (index 48) — 방문취업 (신규발급 중단) **[FOLLOW-UP PR REQUIRED]**
- Visa §38 pp.379–444 (same §38 as F-4); Stay §36 pp.522–588.
- **신규발급 중단** since 2026-02-12 (법무부 동포체류자격 통합).
- `dataDate="2026-02-12 (법무부 동포체류자격 통합 시행)"`. Feb 2026 sub-manual.
- Extension ref: stay p.531 (needs_manual_review).
- **Status**: `needsManualReview=true`. Stale: Feb 2026 sub-manual. Action: `needs-followup-pr`.

#### A-1 (index 49) — 외교
- Visa §1 pp.7–9; Stay §1 pp.14–17.
- Extension ref: stay p.16 (needs_manual_review).
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### A-2 (index 50) — 공무
- Visa §2 pp.10–12; Stay §2 pp.18–20.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### A-3 (index 51) — 협정
- Visa §3 p.13 (one page); Stay §3 pp.21–23.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### C-1 (index 52) — 일시취재
- Visa §6 pp.25–26; Stay §6 p.26.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### D-5 (index 53) — 취재
- Visa §13 pp.88–89; Stay §13 pp.102–104.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### D-6 (index 54) — 종교
- Visa §14 pp.90–91; Stay §14 pp.105–107.
- **Status**: `needsManualReview=true`. No stale marker. Action: `needs-page-review`.

#### D-4-2K (index 55) — 기업맞춤형인턴십(K-Trainee) **[DUPLICATE CODE / FOLLOW-UP PR REQUIRED]**
- Code `D-4-2K` shared with index 24. This entry = K-Trainee 기업맞춤형인턴십.
- `dataDate="2025-10-29 (법무부 K-Trainee 체류자격 신설 시행)"`. `dataBadge="2025.10.29 신설 (2년 시범운영)"`.
- Period: "6개월(인턴기간+1개월), 최대 1년 이내 연장".
- Manual section: Visa §12 D-4 pp.73–87; Stay §12 D-4 pp.83–101.
- **Status**: `needsManualReview=true`. `DUPLICATE CODE` — requires follow-up PR.

#### K-STAR (index 56) — K-STAR 비자트랙 **[FOLLOW-UP PR REQUIRED]**
- Visa §40 pp.456–484 (29 pp); Stay §41 pp.746–774 (29 pp).
- Dedicated record exists but all fields `needsManualReview=true`.
- **Status**: `needsManualReview=true`. Large special section. Action: `needs-followup-pr`.

#### REGION-S (index 57) — 지역특화·광역형 비자 시범사업 **[FOLLOW-UP PR REQUIRED]**
- Stay §37 지역특화형비자 pp.589–651 (63 pp) + Stay §40 광역형 비자 시범사업 pp.683–745 (63 pp).
- No visa manual section.
- REGION-S record models both programs.
- **Status**: `needsManualReview=true`. Large special sections. Action: `needs-followup-pr`.

---

## Follow-up PR Queue

| Priority | Record(s) | Issue | Estimated pages to extract |
|---:|---|---|---|
| 1 | F-6 | Stale 2026.3 income note; F-6-1 income eligibility update | Visa §34 pp.324–335 (12 pp) + Stay §33 pp.478–501 (24 pp) |
| 2 | D-4-2K (indices 24+55) | Duplicate code; K-연수생 vs K-Trainee disambiguation | Visa §12 pp.73–87 (15 pp) + Stay §12 pp.83–101 (19 pp) |
| 3 | F-4 + H-2 | Feb 2026 sub-manual extraction; H-2 신규발급 중단 documentation | Stay §36 pp.522–588 (67 pp) |
| 4 | K-STAR | Full K-STAR sub-manual extraction | Visa §40 pp.456–484 + Stay §41 pp.746–774 (29 pp each) |
| 5 | REGION-S | 지역특화형비자 + 광역형 extraction | Stay §37 pp.589–651 (63 pp) + Stay §40 pp.683–745 (63 pp) |

---

## Legal Disclaimer

Paradiso is reference software. Nothing in this audit, the reviewed JSON records, or any rendered output constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. All records audited here carry `needsManualReview=true` and must be treated as unverified until a human reviewer confirms the source. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
