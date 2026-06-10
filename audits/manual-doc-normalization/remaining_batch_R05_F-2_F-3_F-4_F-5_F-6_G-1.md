# Remaining Batch R05 — F-2, F-3, F-4, F-5, F-6, G-1

_Run: data/manual-doc-normalization-remaining · 2026-06-10_
_Authoritative manuals chosen per tab: visaIssuance → visa_hwp_full.txt; 체류 tabs → stay_hwp_full.txt._

**Pre-edit plan:** 0 intended changes in this batch (all candidates fail the CONFIRMED_* evidence bar — see per-code entries). Estimated diff size: 0 lines. Files that would change: none.

### F-2
- Procedure tabs inspected: extension, registration, statusChange
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (4 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- `documents_extension` (8 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- Confirmed fixes this run: **0**.

### F-3
- Procedure tabs inspected: activitiesOutsideStatus, extension, reentry, registration, statusChange, statusGrant
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (4 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- `documents_extension` (6 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- Confirmed fixes this run: **0**.

### F-4
- Procedure tabs inspected: extension, registration, statusChange
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (4 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- `documents_extension` (3 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- Confirmed fixes this run: **0**.

### F-5
- Procedure tabs inspected: extension, registration
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (4 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- `documents_extension` (8 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- Confirmed fixes this run: **0**.

### F-6
- Procedure tabs inspected: activitiesOutsideStatus, extension, reentry, registration, statusChange, statusGrant, visaIssuance, workplaceChange
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (9 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- `documents_extension` (15 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- Confirmed fixes this run: **0**.

### G-1
- Procedure tabs inspected: extension, registration, statusChange
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (4 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- `documents_extension` (5 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- Confirmed fixes this run: **0**.

**Batch totals:** confirmed fixes = 0; ambiguous/skip entries recorded = 0; validation = JSON valid, no diff produced.
**documents_extension/registration template-label audit (this batch's codes included):**
All `documents_extension` entries were additionally checked against each code's stay-manual
section (extension = 체류기간연장 tab → stay manual authoritative by tab rule). Result:
besides the D-10/E-8 결핵진단서 fixes, all non-verbatim labels are the app's standardized
display template (e.g. `여권 원본 및 인적사항면 사본`, `외국인등록증 원본 및 사본(거소증
해당자 포함)`, `통합신청서(별지 제34호 서식)`, fee-caution entries, 체류지 guidance entry)
or umbrella/compressed display forms (`기타 체류목적 입증서류`, `점수제 자기평가표 및
증빙서류`(0 manual hits — cannot confirm, cannot remove), `부가가치세 과세표준증명`
(whitespace-only vs manual `부가가치세과세표준증명`) 등) — none 'clearly wrong' →
skip per 'do not normalize merely for style' / AMBIGUOUS rules. No documents added/removed.
