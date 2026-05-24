# Manual → JSON Crosswalk — 2026.5 Manual Update Audit

Branch: `data/audit-2026-05-21-manual-update-json`
Audit date: 2026-05-24

> **This document is an internal audit artifact. It is not legal advice and is not an official immigration decision.**

> **Source-identity caveat:** Page numbers are from the repo's committed 2026.5 PDFs (PDF internal creation date 2026-05-07, cover label "2026. 5."). The user-attached 2026-05-21 source PDFs are not accessible from this remote Linux execution environment. All page anchors are subject to revision if the PDFs are replaced.

---

## Summary

| Metric | Count |
|---|---:|
| Total `visa_data.json` records (including helpers and duplicate D-4-2K) | 58 |
| Helper / non-manual records (`no-change`) | 17 |
| Manual-dependent records needing page-level review | 34 |
| Records requiring dedicated follow-up PR | 7 |
| Records with stale date markers | 2 (F-4/H-2 Feb sub-manual, F-6 income note 2026.3) |
| Records with `high` risk classification | 7 |
| `verified=false` in all manual-dependent records | Yes |
| `needsManualReview=true` in all manual-dependent records | Yes |
| Changes to `visa_data.json` in this PR | **0** |

### Action legend

- `no-change` — Helper / scenario / FAQ record; not sourced from immigration manuals; no change required.
- `needs-page-review` — Manual sections located; human page-level review required before `verified` can be advanced.
- `needs-followup-pr` — Complex gap (duplicate code, stale marker, or 50+ page special section); requires a dedicated follow-up PR with targeted page-level extraction.

### Risk legend

- `high` — Content touches high-risk fields (income, eligibility, duplicate code, large special section) or was explicitly flagged in prior PRs.
- `medium` — Country lists, long sections, or auto-extracted refs that need review.
- `low` — Routine section; no known stale markers or special complexity.

---

## Helper / Infrastructure Records (no-change)

These records are not sourced from the immigration manuals. No action required by this audit.

| Code | Name | Type | Notes |
|---|---|---|---|
| K-ETA | 전자여행허가 (K-ETA) 종합 가이드 | faq | k-eta.go.kr sourced. |
| TB-1 | 결핵 고위험 국가 진단서 제출 기준 | scn | Scenario card. |
| SCN-1 | 글로벌 의사결정 매트릭스 | scn | Scenario card. |
| SCN-2 | 실무 변수 체크리스트 | scn | Scenario card. |
| SCN-3 | C-3 (단기) 자격변경 시나리오 | scn | Scenario card. |
| SCN-4 | F-1-6 (혼인단절) 타이밍 시나리오 | scn | Scenario card. |
| SCN-5 | F-4/H-2 (동포) 제약 시나리오 | scn | Scenario card. |
| SCN-6 | 오버스테이 (불법체류) 시나리오 | scn | Scenario card. |
| OVS-1 | 불법체류다발국가 목록 | scn | Scenario card. |
| NHIS-1 | 국외 체류자 건강보험 면제·감면 | nhis | NHIS record. |
| FAQ-1 | 외국인등록 및 체류지 변경 | faq | FAQ record. |
| FAQ-2 | 체류기간 연장·자격 변경 | faq | FAQ record. |
| FAQ-3 | 재입국허가 | faq | FAQ record. |
| FAQ-4 | 전자팩스·오버스테이·국적 | faq | FAQ record. |
| VW-1 | 무사증·사증면제 구분 | faq | FAQ record. |
| COM-1 | 비자 공통 구비서류·팁 | faq | FAQ record. |
| RF-1 | 난민인정신청 제출서류 안내 | scn | Refugee scenario card; G-1 section indirectly relevant but RF-1 is a helper. |

---

## Follow-up PR Required (high-risk gaps)

These records have issues that cannot be resolved in this audit PR. Each requires a dedicated follow-up PR with targeted page-level extraction.

### D-4-2K — Duplicate Code

Two `visa_data.json` records share the code `D-4-2K`:

| Array index | Name | dataDate | Manual section |
|---|---|---|---|
| 24 | 한국어연수(K-연수생) | (blank) | Visa §12 D-4 pp.73-87 / Stay §12 D-4 pp.83-101 |
| 55 | 기업맞춤형인턴십(K-Trainee) | 2025-10-29 | Visa §12 D-4 pp.73-87 / Stay §12 D-4 pp.83-101 |

The K-연수생 어학연수 sub-code `D-4-2K` (index 24) and the K-Trainee 기업맞춤형인턴십 track (index 55) are distinct programs occupying the same `D-4-2K` code. A follow-up PR must assign a distinct code (e.g., D-4-2T for K-Trainee) or convert one to a sub-code entry under the other, with exact page evidence.

### F-4 — 재외동포 (Feb 2026 sub-manual)

- Visa manual: §32 TOC says "※ 38.번 참조". Content lives in §38 알기쉬운 외국국적동포 업무매뉴얼 pp.379–444.
- Stay manual: §36 외국국적동포 관련 pp.522–588.
- The §38/§36 content is a separate Feb 2026 sub-manual bundled inside the May 2026 outer. The repo record carries `dataDate=2026-02-12 (법무부 동포체류자격 통합 시행)`.
- Extension manual ref: stay p.534 (auto_extracted_needs_review).
- **Action**: dedicated follow-up PR; extract F-4 sections from stay §36 pp.522–588.

### F-6 — 결혼이민 (stale income note)

- Visa manual §34 pp.324–335; Stay manual §33 pp.478–501.
- F-6 income note in `visa_data.json` still references `2026.3`. This was the blocker for PR #145 and remains unpatched.
- Extension docs: stay pp.494–499 (`manual_page_extract_needs_review`).
- visaIssuance and statusChange: `needs_review`.
- **Action**: dedicated follow-up PR; extract F-6-1 income eligibility table from stay pp.478–501 and visa pp.324–335 with exact page citation.

### H-2 — 방문취업 (Feb 2026 sub-manual, 신규발급 중단)

- Same §38/§36 sub-manual as F-4. dataDate=2026-02-12.
- 신규발급 중단 since 2026-02-12.
- Extension manual ref: stay p.531 (needs_manual_review).
- **Action**: dedicated follow-up PR jointly with F-4.

### K-STAR — K-STAR 비자트랙

- Visa §40 pp.456–484 (29 pages); Stay §41 pp.746–774 (29 pages).
- Full dedicated sub-manual sections for both manuals.
- The K-STAR record exists in `visa_data.json` but all fields are `needsManualReview=true`.
- **Action**: dedicated follow-up PR; extract K-STAR eligibility, documents, procedures from both sub-manuals.

### REGION-S — 지역특화·광역형 비자 시범사업

- Stay §37 지역특화형비자 pp.589–651 (63 pages).
- Stay §40 광역형 비자 시범사업 pp.683–745 (63 pages).
- No visa manual section (stay-management only).
- The REGION-S record in `visa_data.json` models both programs.
- **Action**: dedicated follow-up PR; extract both sections independently.

---

## Manual-Dependent Records: Page-Level Review Required

All 34 records below have:
- `sourceManualStatus.verified = false`
- `sourceManualStatus.needsManualReview = true`
- `visaManualVersion = "2026.5"` and `stayManualVersion = "2026.5"`
- No stale date markers (except where noted)

No changes were made to any of these records in this PR.

| Code | Name | Visa manual section | Visa pages | Stay manual section | Stay pages | Risk | Notes |
|---|---|---|---|---|---|---|---|
| A-1 | 외교 | §1 외 교(A-1) | 7–9 | §1 외 교(A-1) | 14–17 | low | — |
| A-2 | 공무 | §2 공 무(A-2) | 10–12 | §2 공 무(A-2) | 18–20 | low | — |
| A-3 | 협정 | §3 협 정(A-3) | 13 | §3 협 정(A-3) | 21–23 | low | Visa section is one page. |
| B-1 | 사증면제협정 | §4 사증면제(B-1) | 14–21 | §4 사증면제(B-1) | 24 | medium | 67개국 treaty list; dataDate 2026-04-14. |
| B-2 | 관광통과·무사증 | §5 관광통과(B-2) | 22–24 | §5 관광통과(B-2) | 25 | medium | 45개국 무사증 list; dataDate 2026-04-14. |
| C-1 | 일시취재 | §6 일시취재(C-1) | 25–26 | §6 일시취재(C-1) | 26 | low | — |
| C-3 | 단기방문 | §7 단기방문(C-3) | 27–50 | §7 단기방문(C-3) | 27–28 | medium | Long visa section (24 pp); C-3-1 through C-3-8. visaIssuance=needs_review. |
| C-4 | 단기취업 | §8 단기취업(C-4) | 51–59 | §8 단기취업(C-4) | 29–31 | low | — |
| D-1 | 문화예술 | §9 문화예술(D-1) | 60–61 | §9 문화예술(D-1) | 32–34 | low | — |
| D-2 | 유학 | §10 유 학(D-2) | 62–69 | §10 유 학(D-2) | 35–55 | medium | Active grounding `d2_extension_2026_05` cites stay pp.43–44. Extension ref pp.42–44. |
| D-3 | 기술연수 | §11 기술연수(D-3) | 70–72 | §11 기술연수(D-3) | 56–82 | low | — |
| D-4 | 일반연수 | §12 일반연수(D-4) | 73–87 | §12 일반연수(D-4) | 83–101 | high | Active grounding `d4_extension_2026_05` cites stay pp.90–91. D-4-2K code duplication issue. |
| D-5 | 취재 | §13 취 재(D-5) | 88–89 | §13 취 재(D-5) | 102–104 | low | — |
| D-6 | 종교 | §14 종 교(D-6) | 90–91 | §14 종 교(D-6) | 105–107 | low | — |
| D-7 | 주재 | §15 주 재(D-7) | 92–101 | §15 주 재(D-7) | 108–111 | low | — |
| D-8 | 기업투자 | §16 기업투자(D-8) | 102–115 | §16 기업투자(D-8) | 115–129 | low | Stay body-order anomaly: D-9 prints before D-8 in page order. |
| D-9 | 무역경영 | §17 무역경영(D-9) | 116–121 | §17 무역경영(D-9) | 112–114 | low | Stay body-order anomaly: D-9 (p112–114) before D-8 (p115+). |
| D-10 | 구직 | §18 구 직(D-10) | 122–135 | §18 구 직(D-10) | 142–165 | medium | Contains D-10-1/2/3/T. D-10-T cross-refs §39 탑티어. |
| E-1 | 교수 | §19 교 수(E-1) | 136–141 | §19 교 수(E-1) | 166–175 | low | — |
| E-2 | 회화지도 | §20 회화지도(E-2) | 142–149 | §20 회화지도(E-2) | ~176–184 | low | Stay: E-2 lacks dedicated header; ~176–184 estimated. |
| E-3 | 연구 | §21 연 구(E-3) | 150–156 | §21 연 구(E-3) | 185–194 | low | — |
| E-4 | 기술지도 | §22 기술지도(E-4) | 157–163 | §22 기술지도(E-4) | 195–199 | low | — |
| E-5 | 전문직업 | §23 전문직업(E-5) | ~164–167 | §23 전문직업(E-5) | 200–204 | medium | Visa: no dedicated header (low confidence). Stay confident at p.200. |
| E-6 | 예술흥행 | §24 예술흥행(E-6) | ~164–167 | §24 예술흥행(E-6) | 205–211 | medium | Visa: no dedicated header (low confidence). Stay confident at p.205. |
| E-7 | 특정활동 | §25 특정활동(E-7) | 168–277 | §25 특정활동(E-7) | 212–323 | high | Active grounding `e7_extension_2026_05` cites stay p.226. 110 pp visa / 112 pp stay. E-7-1/2/3/4/S/Y/T/91. |
| E-8 | 계절근로 | §26 계절근로(E-8) | 278–283 | §26 계절근로(E-8) | 324–325 | low | — |
| E-9 | 비전문취업 | §27 비전문취업(E-9) | 284–293 | §27 비전문취업(E-9) | 326–335 | low | — |
| E-10 | 선원취업 | §28 선원취업(E-10) | 294–296 | §28 선원취업(E-10) | 336–340 | low | — |
| F-1 | 방문동거 | §29 방문동거(F-1) | 297–307 | §29 방문동거(F-1) | 341–359 | medium | Extension ref stay p.351:needs_manual_review. |
| F-2 | 거주 | §30 거 주(F-2) | 308–312 | §30 거 주(F-2) | 360–424 | medium | 65 pp stay. F-2-T (Top-Tier) sub-code. Extension ref stay p.394. |
| F-3 | 동반 | §31 동 반(F-3) | 313–317 | §31 동 반(F-3) | 425–441 | low | — |
| F-5 | 영주 | §33 영 주(F-5) + §38 동포 F-5 | 318–323 + 379–444 | §32 영주(F-5):동포,난민제외 | 442–477 | medium | §38 also covers 동포 F-5. Main stay section excludes 동포 and 난민. |
| G-1 | 기타(난민등) | §35 기 타(G-1) | 336–342 | §34 기 타(G-1) | 502–517 | medium | Refugee-adjacent statuses. Extension ref stay p.513. |
| H-1 | 관광취업 | §36 관광취업(H-1) | 343–378 | §35 관광취업(H-1) | 518–521 | low | Long visa section (36 pp). Stay section is 4 pages. |

---

## doc_master.json Cleanup Queue

The `doc_master.json` has 79 entries:
- 66 are referenced by `visa_data.json`.
- 12 are corrupted entries with literal Korean phrases as the `id` field (e.g., `"수수료"`, `"여권"`, `"표준규격사진 1매"`). These should not be referenced from `visa_data.json` and likely resulted from a CSV import error.
- 1 entry (`doc_arc_fee`) is a normal `doc_*`-prefixed ID that is currently unused.

**Action**: Follow-up PR to remove the 12 corrupted entries and verify `doc_arc_fee` usage. No change in this PR.

---

## Legal Disclaimer

Paradiso is reference software. Nothing in this crosswalk, the audited JSON files, or any rendered output constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Korean immigration law and Ministry of Justice manuals change irregularly. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
