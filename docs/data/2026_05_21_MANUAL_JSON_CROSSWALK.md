# Manual → JSON Crosswalk (PR B, post PR #155)

Branch: `data/rebuild-2026-05-21-manual-crosswalk`
Audit date: 2026-05-25
Generator: `scripts/regenerate_2026_05_21_manual_crosswalk.py`

> **This document is an internal audit artifact. It is not legal advice and is not an official immigration decision.**

> **Supersedes:** This crosswalk supersedes the pre-PR #155 crosswalk that was built against the earlier **774-page** stay PDF under the "source_date: unresolved / PDFs not accessible / PDF created 2026-05-07" assumptions. PR #155 installed the canonical 2026-05-21 PDFs (visa 484p sha256 `7fd795…ae11c`; stay **777p** sha256 `dd0d2f…9c3e1`). All stay page anchors here are re-derived from the committed canonical source, and `source_date` is `2026-05-21`. The pre-#155 source-identity caveat no longer applies.

> **Source note:** Page numbers are absolute physical PDF pages in the canonical 2026-05-21 manuals. This crosswalk records manual-section **location** only; it does NOT verify any record. Every manual-dependent record remains `verified=false` / `needsManualReview=true`.

---

## Summary

| Metric | Count |
|---|---:|
| Total `visa_data.json` records | 58 |
| Helper / non-manual records (classification `missing`) | 17 |
| Manual-dependent records | 41 |
| Changes to `visa_data.json` in this PR | **0** |

### Classification taxonomy (every record gets exactly one)

| Classification | Count | Meaning |
|---|---:|---|
| `confirmed` | 30 | Manual section located with a high-confidence page anchor (**location only — NOT data-verified**). |
| `partial` | 4 | Located but no dedicated header / split across sections / approximate range (visa E-5, E-6; stay E-2; F-5). |
| `missing` | 17 | No immigration-manual section maps to this record (helper/scenario/FAQ by design). |
| `duplicate` | 2 | Duplicate visa code `D-4-2K` (array indices 24 and 55). |
| `stale` | 3 | Record carries a stale date marker (F-4, H-2 = Feb-2026 sub-manual; F-6 = 2026.3 income note). |
| `unresolved` | 2 | Large special section / multi-program record needing dedicated extraction (K-STAR, REGION-S). |

> **`confirmed` ≠ verified.** "confirmed" means the manual section was located with a high-confidence page anchor. It does **not** advance `verified`. All 41 manual-dependent records keep `verified=false` and `needsManualReview=true`.

### Follow-up routing

- **PR C candidates (34):** `confirmed` + `partial` records. Safe source-grounded **metadata / doc-ref** updates only (cite the new 484-page visa / 777-page stay sections). No legal/content change.
- **PR D candidates (7):** the `duplicate` (D-4-2K ×2), `stale` (F-4, F-6, H-2), and `unresolved` (K-STAR, REGION-S) records. Limited `requiredDocuments`/content patches **only with exact page/section evidence**.

---

## `missing` — Helper / Infrastructure Records (no manual section)

These 17 records have no `sourceManualStatus` block and are not sourced from the immigration manuals. No action.

| Code | Name | Type |
|---|---|---|
| K-ETA | 전자여행허가 (K-ETA) 종합 가이드 | faq |
| TB-1 | 결핵 고위험 국가 진단서 제출 기준 | scn |
| SCN-1 | 글로벌 의사결정 매트릭스 | scn |
| SCN-2 | 실무 변수 체크리스트 | scn |
| SCN-3 | C-3 (단기) 자격변경 시나리오 | scn |
| SCN-4 | F-1-6 (혼인단절) 타이밍 시나리오 | scn |
| SCN-5 | F-4/H-2 (동포) 제약 시나리오 | scn |
| SCN-6 | 오버스테이 (불법체류) 시나리오 | scn |
| OVS-1 | 불법체류다발국가 목록 | scn |
| NHIS-1 | 국외 체류자 건강보험 면제·감면 | nhis |
| FAQ-1 | 외국인등록 및 체류지 변경 | faq |
| FAQ-2 | 체류기간 연장·자격 변경 | faq |
| FAQ-3 | 재입국허가 | faq |
| FAQ-4 | 전자팩스·오버스테이·국적 | faq |
| VW-1 | 무사증·사증면제 구분 | faq |
| COM-1 | 비자 공통 구비서류·팁 | faq |
| RF-1 | 난민인정신청 제출서류 안내 | scn |

---

## `duplicate` / `stale` / `unresolved` — PR D candidates (page-cited content patches only)

### D-4-2K — Duplicate Code (`duplicate`)

Two records share code `D-4-2K`:

| Index | Name | dataDate | Manual section |
|---|---|---|---|
| 24 | 한국어연수(K-연수생) | (blank) | Visa §12 D-4 pp.73–87 / Stay §12 D-4 pp.83–101 |
| 55 | 기업맞춤형인턴십(K-Trainee) | 2025-10-29 | Visa §12 D-4 pp.73–87 / Stay §12 D-4 pp.83–101 |

K-연수생 어학연수 (index 24) and K-Trainee 기업맞춤형인턴십 (index 55) are distinct programs sharing one code. **PR D** must assign a distinct code (e.g. `D-4-2T` for K-Trainee) or a sub-code structure, with page evidence.

### F-4 — 재외동포 (`stale`, Feb-2026 sub-manual)

- Visa §32 TOC: "※ 38.번 참조"; content in §38 외국국적동포 sub-manual pp.379–444. Stay §36 외국국적동포 관련 **pp.518–584** (re-derived; was 522–588).
- `dataDate=2026-02-12`; sourced from a Feb-2026 sub-manual bound inside the May-2026 outer manual.
- **PR D**: extract F-4 from stay §36 pp.518–584 with page citation.

### F-6 — 결혼이민 (`stale`, 2026.3 income note)

- Visa §34 pp.324–335; Stay §33 **pp.474–497** (re-derived; was 478–501).
- F-6 income note still references `2026.3` (3 occurrences) — PR #145 blocker, unpatched.
- **PR D**: extract F-6-1 income eligibility from stay pp.474–497 / visa pp.324–335 with exact page citation.

### H-2 — 방문취업 (`stale`, Feb-2026 sub-manual, 신규발급 중단)

- Same §38/§36 sub-manual as F-4. `dataDate=2026-02-12`; 신규발급 중단 since 2026-02-12. Stay §36 **pp.518–584**.
- **PR D**: handle jointly with F-4.

### K-STAR — K-STAR 비자트랙 (`unresolved`)

- Visa §40 pp.456–484 (29pp); Stay §41 **pp.749–777** (re-derived; was 746–774, now +3 pages incl. the 우수인재 붙임 7–12 appendix block).
- Dedicated record exists; all fields `needsManualReview=true`.
- **PR D**: extract eligibility, documents, procedures from both sub-manuals.

### REGION-S — 지역특화·광역형 비자 시범사업 (`unresolved`)

- Stay §37 지역특화형비자 **pp.585–654** + Stay §40 광역형 비자 시범사업 **pp.686–748** (re-derived). No visa section.
- Record models both programs; all fields `needsManualReview=true`.
- **PR D**: extract both sections independently.

---

## `confirmed` / `partial` — PR C candidates (metadata / doc-ref updates only)

All records below keep `verified=false`, `needsManualReview=true`, `visaManualVersion="2026.5"`, `stayManualVersion="2026.5"`. No record was changed in this PR. PR C may update their manual page citations to the re-derived anchors below (metadata only).

| Code | Name | Class | Visa pages | Stay pages | Risk | Notes |
|---|---|---|---|---|---|---|
| A-1 | 외교 | confirmed | 7–9 | 14–17 | low | |
| A-2 | 공무 | confirmed | 10–12 | 18–20 | low | |
| A-3 | 협정 | confirmed | 13 | 21–23 | low | Visa section one page. |
| B-1 | 사증면제협정 | confirmed | 14–21 | 24 | medium | 67개국 list; dataDate 2026-04-14 (immigration.go.kr). |
| B-2 | 관광통과·무사증 | confirmed | 22–24 | 25 | medium | 45개국 무사증; dataDate 2026-04-14. |
| C-1 | 일시취재 | confirmed | 25–26 | 26 | low | |
| C-3 | 단기방문 | confirmed | 27–50 | 27–28 | medium | C-3-1..C-3-8; visaIssuance=needs_review. |
| C-4 | 단기취업 | confirmed | 51–59 | 29–31 | low | |
| D-1 | 문화예술 | confirmed | 60–61 | 32–34 | low | |
| D-2 | 유학 | confirmed | 62–69 | 35–55 | medium | Active grounding stay pp.43–44. |
| D-3 | 기술연수 | confirmed | 70–72 | 56–82 | low | |
| D-4 | 일반연수 | confirmed | 73–87 | 83–101 | high | Active grounding stay pp.90–91; parent of duplicated D-4-2K. |
| D-5 | 취재 | confirmed | 88–89 | 102–104 | low | |
| D-6 | 종교 | confirmed | 90–91 | 105–107 | low | |
| D-7 | 주재 | confirmed | 92–101 | 108–114 | low | |
| D-8 | 기업투자 | confirmed | 102–115 | 115–129 | low | D-8 precedes D-9 in normal order. |
| D-9 | 무역경영 | confirmed | 116–121 | 130–141 | low | Stay re-derived to 130–141. |
| D-10 | 구직 | confirmed | 122–135 | 142–165 | medium | D-10-1/2/3/T; D-10-T → §39 탑티어. |
| E-1 | 교수 | confirmed | 136–141 | 166–175 | low | |
| E-2 | 회화지도 | partial | 142–149 | ~176–184 | low | Stay E-2 no dedicated header. |
| E-3 | 연구 | confirmed | 150–156 | 185–194 | low | |
| E-4 | 기술지도 | confirmed | 157–163 | 195–199 | low | |
| E-5 | 전문직업 | partial | ~164–167 | 200–204 | medium | Visa E-5 no dedicated header. |
| E-6 | 예술흥행 | partial | ~164–167 | 205–211 | medium | Visa E-6 no dedicated header. |
| E-7 | 특정활동 | confirmed | 168–277 | 212–323 | high | Active grounding stay p.226; E-7-1/2/3/4/S/Y/T/91. |
| E-8 | 계절근로 | confirmed | 278–283 | 324–325 | low | |
| E-9 | 비전문취업 | confirmed | 284–293 | 326–335 | low | |
| E-10 | 선원취업 | confirmed | 294–296 | 336–340 | low | |
| F-1 | 방문동거 | confirmed | 297–307 | 341–359 | medium | |
| F-2 | 거주 | confirmed | 308–312 | 360–420 | medium | F-2-T sub-code; stay re-derived 360–420. |
| F-3 | 동반 | confirmed | 313–317 | 421–425 | low | Stay re-derived 421–425. |
| F-5 | 영주 | partial | 318–323 + §38 379–444 | 426–473 | medium | Split across stay §32 (excludes 동포/난민) and §36; stay re-derived 426–473. |
| G-1 | 기타(난민등) | confirmed | 336–342 | 498–513 | medium | Stay re-derived 498–513. |
| H-1 | 관광취업 | confirmed | 343–378 | 514–517 | low | Stay re-derived 514–517. |

---

## doc_master.json alignment queue (deferred to PR C)

`doc_master.json` has 79 entries:
- 66 are normal `doc_*`-prefixed IDs referenced by `visa_data.json`.
- **12 are corrupted entries** whose `id` field is a literal Korean phrase (e.g. `"수수료"`, `"여권"`, `"표준규격사진 1매"`, `"통합신청서"`) — almost certainly a CSV/import artifact. These should not be referenced from `visa_data.json`.
- **1 unused** normal entry: `doc_arc_fee`.

**Action (PR C):** remove the 12 corrupted entries and verify `doc_arc_fee` usage (metadata/reference hygiene only, no legal content). No change in this PR.

---

## Legal Disclaimer

Paradiso is reference software. Nothing in this crosswalk, the audited JSON files, or any rendered output constitutes legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Korean immigration law and Ministry of Justice manuals change irregularly. Users must verify any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified Korean immigration professional.
