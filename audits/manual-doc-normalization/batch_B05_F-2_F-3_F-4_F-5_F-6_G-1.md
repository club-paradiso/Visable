# Batch B05 — F-2, F-3, F-4, F-5, F-6, G-1

_Authoritative manuals: visaIssuance→visa_hwp_full.txt; 체류 tabs→stay_hwp_full.txt. Generated 2026-06-10._
**Batch totals:** confirmed fixes = 3; ambiguous/skipped = 4.


### F-2
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- No findings; no candidates. Clean.

### F-3
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- No findings; no candidates. Clean.

### F-4
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 3 → FIXED
- Type N (near-dup): 0
- **Confirmed fixes (Type E):**
    - [extension] `procedures.extension.variants[0].manualRefs[0].pageRange`: `PDF pp. 530-531 (embedded manual pp. 10-11)` → `PDF pp. 530-531`
    - [registration] `procedures.registration.variants[0].manualRefs[0].pageRange`: `PDF p. 530 (embedded manual p. 10)` → `PDF p. 530`
    - [statusChange] `procedures.statusChange.variants[0].manualRefs[0].pageRange`: `PDF pp. 528-530 (embedded manual pp. 8-10)` → `PDF pp. 528-530`
- Naming near-miss candidates: 3 (all reviewed → skipped):
    - ⚠️ `통합신청서(별지 제1호 서식)` [registration/commonDocs] → **LESS_SPECIFIC** — Manual prefixes '재외동포'; form number 제1호 already correct. Prepending not 'extremely clear', risk of churn. Flag for review. (evidence: stay L18747 '재외동포 통합신청서(별지 제1호서식)')
    - ⚠️ `통합신청서(별지 제1호 서식)` [statusChange/commonDocs] → **LESS_SPECIFIC** — Manual prefixes '재외동포'; form number 제1호 already correct. Prepending not 'extremely clear', risk of churn. Flag for review. (evidence: stay L18747 '재외동포 통합신청서(별지 제1호서식)')
    - ⚠️ `해외범죄경력증명서` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Exact match present. (evidence: stay L5392)

### F-5
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- No findings; no candidates. Clean.

### F-6
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- No findings; no candidates. Clean.

### G-1
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- Naming near-miss candidates: 1 (all reviewed → skipped):
    - ⚠️ `산재로 인한 병원 진단서 등` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Whitespace-only vs '병원진단서'. (evidence: stay L18052)
