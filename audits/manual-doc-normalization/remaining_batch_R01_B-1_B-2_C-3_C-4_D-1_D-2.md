# Remaining Batch R01 — B-1, B-2, C-3, C-4, D-1, D-2

_Run: data/manual-doc-normalization-remaining · 2026-06-10_
_Authoritative manuals chosen per tab: visaIssuance → visa_hwp_full.txt; 체류 tabs → stay_hwp_full.txt._

**Pre-edit plan:** 0 intended changes in this batch (all candidates fail the CONFIRMED_* evidence bar — see per-code entries). Estimated diff size: 0 lines. Files that would change: none.

### B-1
- Procedure tabs inspected: extension, registration
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (1 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- Confirmed fixes this run: **0**.

### B-2
- Procedure tabs inspected: extension, registration
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (2 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- Confirmed fixes this run: **0**.

### C-3
- Procedure tabs inspected: activitiesOutsideStatus, extension, reentry, registration, statusChange, statusGrant, visaIssuance, workplaceChange
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (8 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- `documents_extension` (3 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- Confirmed fixes this run: **0**.

### C-4
- Procedure tabs inspected: extension, registration
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (5 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- Confirmed fixes this run: **0**.

### D-1
- Procedure tabs inspected: extension, reentry, registration
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (5 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- `documents_extension` (4 entries): **no `_source_notes` provenance** → governing manual undeterminable → Type C/D = `AMBIGUOUS_MANUAL_MISMATCH` (skip); Type A checked = 0.
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- Confirmed fixes this run: **0**.

### D-2
- Procedure tabs inspected: extension, partTimeWork, reentry, registration, schoolChange, statusChange
- Mechanical re-scan (procedure arrays, ID arrays, subCodes, documents_*): 0 Type A, 0 Type B, 0 Type E, 0 Type N
- `documents_initial` (5 entries): provenance = stay manual (_source_notes) → deep-checked against stay manual D-2 section. Result: 0 confirmed fixes (see detail below).
- `documents_registration` (6 entries): provenance = stay manual (_source_notes) → deep-checked against stay manual D-2 section. Result: 0 confirmed fixes (see detail below).
- `documents_extension` (8 entries): provenance = stay manual (_source_notes) → deep-checked against stay manual D-2 section. Result: 0 confirmed fixes (see detail below).
- ID-array rendered-label duplicate scan (two doc ids → same ko_name): 0.
- **D-2 deep-check detail (attributed arrays vs stay manual L1162–2255):**
    - ⚠️ `학력요건 입증서류` [documents_initial] → **SKIP/ALREADY_FAITHFUL** — Manual L1487: '학력요건 및 재정능력 입증서류' — data faithfully splits the composite into two entries.
    - ⚠️ `체류민원 기준 주의` [documents_initial] → **SKIP/PROTECTED_CAUTION** — Caution note stored as document entry; removing/moving would weaken an official-source warning (forbidden). Data-hygiene follow-up only.
    - ⚠️ `통합신청서(별지 제34호 서식)` [documents_registration] → **SKIP/MORE_SPECIFIC_OFFICIAL** — Manual D-2 section uses shorthand '신청서'; 별지 제34호 IS the 통합신청서 (official label verbatim elsewhere in same manual, L11254). Data is more specific, not wrong.
    - ⚠️ `여권 원본 및 사본 1부` [documents_registration] → **SKIP/ALREADY_FAITHFUL** — Manual L1483: '여권 및 사본 1부' — data adds clarifying '원본'; same requirement.
    - ⚠️ `외국인등록증 발급 수수료` [documents_registration] → **SKIP/FEE_PROTECTED** — Fee item; fee amounts/labels protected.
    - ⚠️ `재학증명서 또는 연구생증명서` [documents_registration] → **SKIP/ALREADY_FAITHFUL** — Manual L1661: '재학(연구생)증명서' — data expands parenthetical to '또는' form; same document.
    - ⚠️ `체류지 입증서류(예: …)` [documents_registration] → **SKIP/GUIDANCE_PROSE** — Label head '체류지 입증서류' exact in manual; long parenthetical is applicant guidance — removal would weaken guidance.
    - ⚠️ `통합신청서(별지 제34호 서식)` [documents_extension] → **SKIP/MORE_SPECIFIC_OFFICIAL** — Same as registration case.
    - ⚠️ `정상 학업 수행 입증서류` [documents_extension] → **SKIP/STYLE_PARAPHRASE** — Manual phrase '학업을 정상적으로 수행하고 있음을 입증하는 서류' (used verbatim in procedures.extension.requiredDocs). documents_extension uses compressed display form — not clearly wrong; 'do not normalize merely for style'.
    - ⚠️ `체류지 입증서류(예: …)` [documents_extension] → **SKIP/GUIDANCE_PROSE** — Same as registration case.
- Confirmed fixes this run: **0**.

**Batch totals:** confirmed fixes = 0; ambiguous/skip entries recorded = 10; validation = JSON valid, no diff produced.
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
