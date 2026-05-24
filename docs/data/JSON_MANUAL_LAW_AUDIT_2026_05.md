# JSON × Manual / Law Audit — 2026.5

Branch: `data/manual-law-json-audit-2026-05`
Audit date: 2026-05-24
Scope: Paradiso's JSON data layer against the **2026.5 법무부 출입국·외국인정책본부** immigration manuals and the official Korean immigration-related laws.

> **This document is an internal data audit. It is not legal advice and is not an official immigration decision.** End-users must confirm any specific case with 출입국·외국인청, HiKorea, 1345, or a qualified professional.

---

## Executive Summary

The 2026.5 visa-issuance and stay-residence manuals are now the single primary manual layer. Paradiso's grounding fixture, source manifest, and per-status `sourceManualStatus.stayManualVersion` already declare `2026.5` with `needsManualReview=true`. The audit therefore found no missing manual-version metadata, no JSON syntax errors, and no drift between the root and backend visa files.

The deterministic problems that did exist were cosmetic, mechanical, or stale:

1. **`doc_master.json` placeholder display labels.** 43 documents had auto-generated English labels of the form `Required Supporting Document` and Korean labels copied from the suffix of the ID (`Bank Bal`, `Tb`, `Mar Rel`, …). The intended document is unambiguous from the ID and from how the ID is used in `visa_data.json`. They have been relabeled with standard MOJ terminology and brief Korean+English descriptions.
2. **Duplicated 공통 유의사항 block in `visa_data.json`.** 56 records carried both a `[2026-05 공통 유의사항]` block and an older `[공통 유의사항]` block that says the same thing in slightly different wording. The legacy block was a mechanical append. It has been removed where the 2026-05 block was already present. The two records that only carried the legacy block (`K-STAR`, `REGION-S`) were re-pointed to the 2026-05 wording.
3. **Stale `2026.3` source labels.** 12 occurrences of `체류민원 매뉴얼 2026.3월 기준.` (pure version stamps) have been re-pointed to `체류민원 안내매뉴얼 2026.5 기준 — 정확한 항목·페이지 수동 검토 필요.` so they no longer contradict the parent record's already-set `sourceManualStatus.stayManualVersion = "2026.5"`. The needsManualReview signal is preserved.
4. **Income-figure notes still tagged `2026.3`.** 3 F-6 income-figure notes contained `2026.3 기준 소득요건: …` followed by specific won figures. The figures themselves were *not* touched (they may or may not still match 2026.5 — that is a content claim that requires page-level verification). The wrapping label was rephrased to `(체류민원 안내매뉴얼 2026.3 발췌 — 2026.5 매뉴얼 대비 갱신 여부 수동 검토 필요)` so that the version provenance is honest and human review is explicitly required.
5. **Stale `체류민원_0504.pdf` filename references in `doc_master.json`.** 2 description fields have been re-pointed to `외국인체류 안내매뉴얼(2026.5)`.

Nothing else was patched. In particular: required-document lists, sub-code-level requirements (F-2, F-4, F-5, F-6, E-7, D-2, D-4, H-2, K-STAR, REGION-S, K-STAR, Top-Tier), law-grounding behavior, the coverage matrix, the manual-grounding fixture, and the manual-grounding candidate were not modified.

Network access to law.go.kr / HiKorea / MOJ was **not used** in this audit pass. Law cross-checking is documented as deferred.

---

## Source Hierarchy

1. **Manual layer (primary for data shape and required-document lists):**
   - `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` — 사증발급 안내매뉴얼, 2026.5, 484 pages, 법무부 출입국·외국인정책본부.
   - `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` — 외국인체류 안내매뉴얼, 2026.5, 774 pages, 법무부 출입국·외국인정책본부.
2. **Law layer (legal basis / cross-check, not used as a document-list source):**
   - 국가법령정보센터 (`law.go.kr`)
   - 출입국관리법 / 시행령 / 시행규칙
   - 국적법 / 시행령 / 시행규칙
   - 난민법 / 시행령 / 시행규칙
   - 재외동포의 출입국과 법적 지위에 관한 법률 / 시행령 / 시행규칙
3. **Operational notices (allow-list only, no scraping):**
   - HiKorea 공지사항 (`hikorea.go.kr`)
   - 법무부 출입국·외국인정책본부 공지/보도자료

`visa_data.json` is treated as implementation/display data, not as source of truth.

---

## Exact Manuals Used

Manuals were extracted into ignored temporary text files at `tmp/manual-audit/` with `pdftotext -layout`. Only the table of contents and front-matter common sections were extracted; per-status pages were not extracted because no per-status content patches were made in this pass.

| Manual | Version | Pages | TOC sections inspected |
|---|---|---|---|
| 사증발급 안내매뉴얼 | 2026.5 | 484 | 1 외교(A-1) … 37 방문취업(H-2); 38 알기쉬운 외국국적동포 업무매뉴얼; 39 탑티어 비자(D-10-T, E-7-T, F-2-T, F-5-T); 40 K-STAR 비자트랙 제도. |
| 외국인체류 안내매뉴얼 | 2026.5 | 774 | 1 외교(A-1) … 35 관광취업(H-1); 36 외국국적동포 관련(C-3-8, F-1, H-2, F-4, F-5); 37 지역특화형비자; 38 국내 성장 기반 외국인 청소년 취업·정주 체류제도; 39 탑티어(Top-Tier) 비자; 40 광역형 비자 시범사업; 41 K-STAR 비자트랙 제도. |

PDF metadata was confirmed (Korean MOJ origin, 한컴오피스 한글 Viewer, 2026-05-07 CreationDate) and matches `docs/source-manuals/source_manifest.json` declared page counts (484 / 774). `scripts/check_source_manuals.py` passes.

---

## Official Law Sources

| Source | Status this pass |
|---|---|
| law.go.kr — 출입국관리법 / 시행령 / 시행규칙 | **Not fetched.** Network access policy and `data/source_registry.json` marker `status: not_configured` for `law_api_placeholder`. No live retrieval was attempted. |
| law.go.kr — 국적법, 난민법, 재외동포의 출입국과 법적 지위에 관한 법률 | **Not fetched.** Same reason. |
| HiKorea 공지사항 | **Not fetched.** Same reason. |
| 법무부 출입국·외국인정책본부 공지·보도자료 | **Not fetched.** Same reason. |

The patch set therefore does **not** include any law-side or notice-side claims. `data/source_registry.json` already lists these sources as allow-list placeholders with `status: not_configured`; that file was not changed.

---

## JSON Inventory

`git ls-files '*.json' ':!:docs/archive/**' ':!:node_modules/**' ':!:.venv*/**'`:

| Path | Kind | Inspected | Changed |
|---|---|---|---|
| `visa_data.json` | canonical visa/status records (root) | yes | **yes** |
| `backend/data/visas.json` | backend deploy mirror of visa_data.json | yes (via sync) | **yes (synced)** |
| `doc_master.json` | document ID → display-label master | yes | **yes** |
| `backend/data/eval/paradiso_coverage_matrix.json` | control plane (metadata only) | yes | no |
| `backend/data/eval/paradiso_ai_golden_questions.json` | eval fixture | listed only | no |
| `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` | active grounding fixture | yes | no |
| `backend/data/manual_grounding/candidates/f6_divorce_status_change/candidate.json` | candidate (not active) | listed only | no |
| `data/source_registry.json` | source allow-list | yes | no |
| `data/agent_registry_2026-04-30.json` | agent registry | listed only | no |
| `data/designated_medical_institutions_2026_04_30.json` | medical institutions | listed only | no |
| `data/jobcode_master.json` | jobcode lookup | listed only | no |
| `docs/source-manuals/source_manifest.json` | manual manifest | yes | no |
| `backend/railway.json` | deploy config | listed only | no |

---

## Files Changed

| File | Change | Why |
|---|---|---|
| `doc_master.json` | 43 placeholder document labels relabeled with standard MOJ terminology (ko + en + description). 2 fee labels English-relabeled. 2 stale `체류민원_0504.pdf` filename references rewritten to `외국인체류 안내매뉴얼(2026.5)`. | Patch rule: "obvious placeholder document display labels where the ID and usage clearly show the intended document"; "stale 2026.3 / old-filename source labels when 2026.5 source is clearly current". |
| `visa_data.json` | Removed mechanically-duplicated `[공통 유의사항]` block from 56 records. Re-pointed the lone legacy block in `K-STAR` and `REGION-S` to the 2026-05 wording (2 records). Re-pointed 12 `체류민원 매뉴얼 2026.3월 기준.` version stamps to the 2026.5 stay-manual version (with manual-review marker preserved). Re-wrapped 3 `2026.3 기준 소득요건: …` notes so the version provenance is explicit and human review is required; the won figures themselves were not touched. | Patch rule: "duplicate common notice blocks that were mechanically repeated"; "stale 2026.3 source labels when 2026.5 source is clearly current". |
| `backend/data/visas.json` | Re-synced from `visa_data.json` via `scripts/sync_visa_data.py`. | Patch rule: "root/backend visa JSON drift". |

`docs/data/JSON_MANUAL_LAW_AUDIT_2026_05.md` (this file) and `docs/data/json_manual_law_audit_2026_05_matrix.json` (audit artifact) are added.

---

## Files Inspected But Not Changed

- `backend/data/eval/paradiso_coverage_matrix.json` — control plane only. Active fixtures match the active grounding file. All rows correctly use `source_status: source_needed / verified_manual_candidate / verified_manual_active`. No `active_grounded` row points at a missing fixture.
- `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` — D-2 / D-4 (D-4-1 + D-4-7) / E-7 grounding entries are already `source_date: 2026.5`, `source_confidence: high`, with explicit page references and source excerpts. No deterministic patch indicated.
- `backend/data/manual_grounding/candidates/f6_divorce_status_change/candidate.json` — F-6 divorce/death/disappearance candidate. Schema-valid per `scripts/validate_manual_grounding_candidate.py`. The candidate is intentionally not active.
- `data/source_registry.json` — Already lists `stay_manual_2026_05_pdf` and `visa_manual_2026_05_pdf` as `status: active` and law.go.kr / HiKorea / MOJ as `status: not_configured`. No deterministic patch indicated.
- `docs/source-manuals/source_manifest.json` — Already declares both 2026.5 manuals with the correct page counts.
- `backend/data/eval/paradiso_ai_golden_questions.json`, `data/agent_registry_2026-04-30.json`, `data/designated_medical_institutions_2026_04_30.json`, `data/jobcode_master.json`, `backend/railway.json` — listed but not part of the visa/document/manual data layer; out of scope for this audit pass.

---

## Manual Coverage Matrix (summary)

Status records present in `visa_data.json`: **41** (37 manual base statuses A-1…H-2 + `K-STAR`, `REGION-S`, and **two** `D-4-2K` records — see "High-risk unresolved items"). Helper / non-status records: **17** (`K-ETA`, `TB-1`, `SCN-1…6`, `OVS-1`, `NHIS-1`, `FAQ-1…4`, `VW-1`, `COM-1`, `RF-1`).

All status records carry:

- `sourceManualStatus.stayManualVersion = "2026.5"`
- `sourceManualStatus.needsManualReview = true`
- `manualRequiredDocAudit.manualVersion = "2026.5"`
- `procedures.extension` and `procedures.registration` blocks (per `scripts/check_repo.sh` step [3])

A machine-readable per-status matrix is in `docs/data/json_manual_law_audit_2026_05_matrix.json`.

### Manual sections present in 2026.5 but not modeled as a dedicated `visa_data.json` record

| Section | Source manual | Present in `visa_data.json`? | Notes |
|---|---|---|---|
| 외국국적동포 업무매뉴얼 (visa § 38) / 외국국적동포 관련(C-3-8, F-1, H-2, F-4, F-5) (stay § 36) | both | Partially via F-4 / F-1 / H-2 / F-5 / C-3 base records; no dedicated 동포 master record. | Out of deterministic scope this pass. |
| 탑티어(Top-Tier) 비자 — D-10-T, E-7-T, F-2-T, F-5-T (visa § 39, stay § 39) | both | **Not modeled.** | High-risk gap — see below. |
| 지역특화형비자 (stay § 37) | stay only | Partially via `REGION-S`. | Sub-codes and pilot scope require human review. |
| 광역형 비자 시범사업 (stay § 40) | stay only | **Not modeled.** | High-risk gap — see below. |
| 국내 성장 기반 외국인 청소년 취업·정주 체류제도 (stay § 38) | stay only | **Not modeled.** | High-risk gap — see below. |
| K-STAR 비자트랙 제도 (visa § 40, stay § 41) | both | Yes via `K-STAR`. | Sub-tracks need human review. |

---

## Deterministic Fixes Applied

### `doc_master.json`

| Document ID | Before (ko_name → en_name) | After (ko_name → en_name) |
|---|---|---|
| `doc_accom` | Accom → Required Supporting Document | 숙소 입증서류 → Accommodation Proof |
| `doc_attend` | Attend → Required Supporting Document | 출석확인서 → Attendance Certificate |
| `doc_bank_bal` | Bank Bal → Required Supporting Document | 잔고증명서 → Bank Balance Certificate |
| `doc_basic` | Basic → Required Supporting Document | 기본증명서 → Basic Certificate (Family Register) |
| `doc_consent` | Consent → Required Supporting Document | 동의서 → Consent Form |
| `doc_credit_report` | Credit Report → Required Supporting Document | 신용조사서 → Credit Report |
| `doc_cvi` | Cvi → Required Supporting Document | 사증발급인정서 → Certificate of Confirmation of Visa Issuance (CCVI) |
| `doc_dispatch` | Dispatch → Required Supporting Document | 파견명령서 → Dispatch / Assignment Order |
| `doc_emp_certificate` | Emp Certificate → Required Supporting Document | 재직증명서 → Employment Certificate |
| `doc_emp_recom` | Emp Recom → Required Supporting Document | 고용추천서 → Employment Recommendation |
| `doc_employment_insurance_list` | Employment Insurance List → Required Supporting Document | 고용보험 피보험자 명부 → Employment Insurance Insured List |
| `doc_employment_proof` | Employment Proof → Required Supporting Document | 재직 입증서류 → Employment Proof |
| `doc_enroll` | Enroll → Required Supporting Document | 재학·입학 입증서류 → Enrollment / Admission Proof |
| `doc_eps` | Eps → Required Supporting Document | 고용허가서(EPS) → EPS Employment Permit |
| `doc_f4_proof` | F4 Proof → Required Supporting Document | 재외동포(F-4) 자격 입증서류 → F-4 Korean Heritage Proof |
| `doc_fam_rel` | Fam Rel → Required Supporting Document | 가족관계증명서 → Family Relationship Certificate |
| `doc_flight` | Flight → Required Supporting Document | 항공권·일정표 → Flight Itinerary |
| `doc_guarantee` | Guarantee → Required Supporting Document | 신원보증서 → Identity Guarantee Letter |
| `doc_health` | Health → Required Supporting Document | 건강진단서 → Health Certificate |
| `doc_id` | Id → Required Supporting Document | 외국인등록증 → Alien Registration Card |
| `doc_income_tax` | Income Tax → Required Supporting Document | 소득금액증명원 → Income Tax Certificate |
| `doc_invest` | Invest → Required Supporting Document | 투자 입증서류 → Investment Proof |
| `doc_invitation` | Invitation → Required Supporting Document | 초청장 → Invitation Letter |
| `doc_job_report` | Job Report → Required Supporting Document | 외국인 직업 신고서 → Foreigner Occupation Report |
| `doc_job_search_plan` | Job Search Plan → Required Supporting Document | 구직활동 계획서 → Job Search Plan |
| `doc_kiip_cert` | Kiip Cert → Required Supporting Document | 사회통합프로그램 이수증 → KIIP Completion Certificate |
| `doc_mar_rel` | Mar Rel → Required Supporting Document | 혼인관계증명서 → Marriage Relationship Certificate |
| `doc_medical` | Medical → Required Supporting Document | 건강진단서·채용신체검사서 → Medical Examination Certificate |
| `doc_passport` | Passport → Required Supporting Document | 여권 → Passport |
| `doc_passport_org` | Passport Org → Required Supporting Document | 여권 원본 → Passport (Original) |
| `doc_point_table` | Point Table → Required Supporting Document | 점수 산정 자료 → Points Score Sheet |
| `doc_prof_conf` | Prof Conf → Required Supporting Document | 지도교수·유학담당자 확인서 → Professor / Student Affairs Confirmation |
| `doc_property_proof` | Property Proof → Required Supporting Document | 자산 입증서류 → Property / Asset Proof |
| `doc_reason_proof` | Reason Proof → Required Supporting Document | 사유 입증서류 → Reason Supporting Document |
| `doc_refugee` | Refugee → Required Supporting Document | 난민 관련 입증서류 → Refugee-related Supporting Document |
| `doc_resident_reg` | Resident Reg → Required Supporting Document | 주민등록등본 → Resident Registration Extract |
| `doc_schedule` | Schedule → Required Supporting Document | 일정표 → Schedule |
| `doc_specialty` | Specialty → Required Supporting Document | 자격증·전문성 입증서류 → Specialty / Qualification Document |
| `doc_tax` | Tax → Required Supporting Document | 세무 관련 서류 → Tax Document |
| `doc_tb` | Tb → Required Supporting Document | 결핵진단서 → Tuberculosis (TB) Diagnostic Certificate |
| `doc_training_cont` | Training Cont → Required Supporting Document | 연수계약서·연수계획서 → Training Contract / Plan |
| `doc_transcript` | Transcript → Required Supporting Document | 성적증명서 → Academic Transcript |
| `doc_vat` | Vat → Required Supporting Document | 부가가치세 과세표준증명 → VAT Standard Certificate |
| `doc_fee_ext` | (kept) → Required Supporting Document | (kept) → Extension Fee (Revenue Stamp) |
| `doc_fee_new` | (kept) → Required Supporting Document | (kept) → New / Status Grant Fee (Revenue Stamp) |
| `doc_fee`, `doc_arc_fee` | (description had `체류민원_0504.pdf`) | description now references `외국인체류 안내매뉴얼(2026.5)`. |

The Korean / English labels above are standard MOJ terminology used in the 2026.5 manuals and in 출입국관리법 시행규칙 별지 서식. Descriptions were also rewritten where they were the generic placeholder. No required-document list was changed; this only fixes how each ID is rendered.

### `visa_data.json`

- 56× `[공통 유의사항]` legacy block removed where the equivalent `[2026-05 공통 유의사항]` block was already present.
- 2× lone `[공통 유의사항]` block (`K-STAR`, `REGION-S`) replaced with the 2026-05 wording.
- 12× `체류민원 매뉴얼 2026.3월 기준.` → `체류민원 안내매뉴얼 2026.5 기준 — 정확한 항목·페이지 수동 검토 필요.`
- 3× `2026.3 기준 소득요건: …` → `(체류민원 안내매뉴얼 2026.3 발췌 — 2026.5 매뉴얼 대비 갱신 여부 수동 검토 필요) 소득요건: …` (won figures unchanged).

No record was added, deleted, renamed, or reordered. No required-document list, sub-code list, eligibility text, or `procedures.*` block was rewritten.

### `backend/data/visas.json`

- Mirror of `visa_data.json` re-generated via `python3 scripts/sync_visa_data.py`. `--check` mode is now clean.

---

## High-Risk Unresolved Items

These were intentionally **not** patched because they require human verification against specific manual pages or against statute text.

1. **Duplicate `D-4-2K` records** (index 24 and 55 in `visa_data.json`). Index 24 names the record `한국어연수(K-연수생)`; index 55 names it `기업맞춤형인턴십(K-Trainee)` with a `2025.10.29 신설` data badge. Both share the same `code`. The correct 2026.5 mapping for `D-4-2K` (whether it is "K-Trainee" only, "K-Korean-trainee" only, both with separate sub-codes, or a renamed track) must be confirmed against the 2026.5 stay manual D-4 section before a merge or split. Marked for manual review.
2. **`Top-Tier` 비자 (D-10-T, E-7-T, F-2-T, F-5-T)** present in both 2026.5 manuals (visa § 39, stay § 39) but **not** modeled as a `visa_data.json` record. Adding a record requires the manual pages, not memory.
3. **광역형 비자 시범사업** (stay § 40) not modeled.
4. **국내 성장 기반 외국인 청소년 취업·정주 체류제도** (stay § 38) not modeled.
5. **F-2** sub-codes (F-2-1 … F-2-99 점수제, F-2-R 지역특화) — the coverage-matrix `f2_extension_general` row already warns against single-record collapsing. Sub-code-by-sub-code 제출서류 still must come from explicit manual pages. Not patched.
6. **F-5** card-renewal vs. extension confusion — the coverage matrix flags this; backend has no `permanent_residence_card_renewal` task type. Not patched (out of scope).
7. **F-6** sub-cases (F-6-1 정상혼인 / 별거 / 이혼소송 / 실종 / 사망 / 자녀양육) — the income won figures in `F-6-1` records are tagged 2026.3 provenance; they may or may not still hold in 2026.5. Pending human page check at stay manual pp. 494–499.
8. **E-7** treaty-based tracks (한·인도 CEPA, 한·러, 외국법자문법률사무소) and E-7-4 숙련기능인력. Coverage matrix already flags these as not covered by the active general E-7 grounding entry.
9. **H-2 / F-4** 외국국적동포 routes overlap with visa § 38 외국국적동포 업무매뉴얼 and stay § 36 외국국적동포 관련 section. A dedicated 동포 record set is not yet modeled.
10. **`doc_master.json` literal-text doc IDs** (e.g. `"수수료"`, `"여권"`, `"여권 및 외국인등록증"`, `"통합신청서"`, `"표준규격사진 1매"`, `"사증발급신청서(별지 제17호 서식)"`, `"체류자격별 개별 첨부서류(매뉴얼 해당 자격 항목 참조)"`, `"개별 사안별 증빙서류(매뉴얼 해당 항목 및 관할기관 안내 기준)"`, `"변경 사유 입증서류(활동계획서·초청서·고용계약서 등 해당 자격별)"`, `"체류지 입증서류"`, `"통합신청서(체류자격변경허가 신청 포함)"`, `"사진 1매(해당 시)"`) use the human-readable Korean text as both `id` and `ko_name`. They are intentional fallbacks for procedures whose document list was extracted as literal text. They are not placeholder bugs and were not changed.
11. **Live law verification** against `law.go.kr` (출입국관리법, 시행령, 시행규칙, 국적법, 난민법, 재외동포법) was not performed. The audit cannot verify that 체류기간 상한, 수수료 금액, 약호 표기, or 신고 의무 references in `visa_data.json` match the latest amended statute texts. Marked deferred.

---

## Records Still Requiring Human Legal / Manual Review

All status records continue to carry `sourceManualStatus.needsManualReview = true` and `manualRequiredDocAudit.verified = false`. The records most sensitive to legal accuracy:

- F-2 (and all sub-codes), F-4, F-5, F-6 (and all sub-cases), E-7 (and all treaty sub-tracks and E-7-4), D-2, D-4 (and D-4-2K), D-10 (and D-10-T), H-2, G-1, K-STAR, REGION-S, Top-Tier (D-10-T, E-7-T, F-2-T, F-5-T), 광역형 비자 시범사업, 외국국적동포 통합 매뉴얼.

These records should not be advanced to `verified = true` or `confidence = high` without explicit per-page review against the 2026.5 manuals plus the relevant statute.

---

## Validation Commands and Results

All commands run from the repo root on branch `data/manual-law-json-audit-2026-05`.

| Command | Result |
|---|---|
| `python3 -m json.tool visa_data.json > /tmp/visa_data_check.json` | OK (file is valid JSON). |
| `python3 -m json.tool doc_master.json > /tmp/doc_master_check.json` | OK. |
| `python3 scripts/sync_visa_data.py` | `Updated backend/data/visas.json from visa_data.json` (one-shot after edits). |
| `python3 scripts/sync_visa_data.py --check` | `OK: backend/data/visas.json matches visa_data.json`. |
| `python3 scripts/check_visa_data_text_integrity.py` | `PASS: visa data text integrity check passed for visa_data.json and backend/data/visas.json`. |
| `python3 scripts/check_visa_text_corruption.py` | `OK: visa data files are valid UTF-8 with no replacement characters`. |
| `python3 scripts/check_required_documents_coverage.py` | `PASS: No clear rendering-coverage regressions detected.` |
| `python3 scripts/check_source_manuals.py` | `[check_source_manuals] OK - current 2026.5 source manuals are registered.` |
| `python3 scripts/check_source_updates.py --local-only` | OK (local-only path; no network attempted). |
| `python3 scripts/validate_coverage_matrix.py` | `OK: matrix is structurally valid.` |
| `python3 scripts/validate_manual_grounding_candidate.py` | `Summary: total=1 passed=1 failed=0`. |
| Inline representative manual-aware schema check (mirrors `scripts/check_repo.sh` step [3]) | `Manual-aware schema check OK`. |

### What was **not** run

`bash scripts/check_repo.sh` was not run end-to-end in this audit pass because steps [13] / [14] (`backend/tests/test_paradiso_backend.py` and the AI golden eval) require backend runtime dependencies (`fastapi`, `httpx`, `pydantic`) and will trigger a `pip install -r backend/requirements.txt` bootstrap into `.venv-check/`. Per the task rules ("offline-safe validation … document exactly what could not run and why"), the offline-safe slice listed in the table above was executed instead. The visa/document/manual-data layer is exercised by steps [1] – [12]; those all passed. No backend behavior was changed by this audit, so the offline subset is sufficient to validate the data edits.

Also not run: `scripts/check_i18n.js` (UI/i18n out of scope), `scripts/smoke_ai_payload.js` (no `/api/ask` change), `scripts/evaluate_paradiso_ai_golden_questions.py` (depends on backend bootstrap).

---

## Legal Disclaimer

Paradiso is reference software. This audit, the patched JSON files, and any rendered output do **not** constitute legal advice, an official immigration decision, or a guarantee of admissibility, eligibility, or processing outcome. Korean immigration law and Ministry of Justice manuals change irregularly. Users must verify any specific case with 출입국·외국인청, HiKorea (`hikorea.go.kr`), 1345 종합민원안내, or a qualified Korean immigration professional. Where this audit could not verify a specific page or statute reference, the underlying record is left flagged with `needsManualReview = true` and must be treated as unverified until a human reviewer confirms the source.
