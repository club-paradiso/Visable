# Batch B03 — D-10, E-1, E-2, E-3, E-4, E-5

_Authoritative manuals: visaIssuance→visa_hwp_full.txt; 체류 tabs→stay_hwp_full.txt. Generated 2026-06-10._
**Batch totals:** confirmed fixes = 0; ambiguous/skipped = 11.


### D-10
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): `구직활동계획서` vs `구직활동 계획서` @ procedures.extension.requiredDocs.requiredDocs → **AMBIGUOUS/skip** (flattened array; the two spellings map to different applicant sub-categories in the manual, 점수제 적용 vs 점수제 면제 특례).
- Naming near-miss candidates: 6 (all reviewed → skipped):
    - ⚠️ `체류지 입증서류 ⅱ) 국내 성장 기반 외국인 청소년` [extension/requiredDocs] → **FLATTENED_ARTIFACT** — Doc + section heading mashed by extraction. (evidence: D-10 stay sec)
    - ⚠️ `체류지 입증서류 ⅲ) 유망인재` [extension/requiredDocs] → **FLATTENED_ARTIFACT** — Doc + section heading mashed by extraction. (evidence: D-10 stay sec)
    - ⚠️ `기술창업 활동계획서` [extension/requiredDocs] → **ALREADY_FAITHFUL** — Whitespace vs '기술창업활동계획서'. (evidence: stay L5816)
    - ⚠️ `학력 입증서류` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Generic faithful label; manual '최종학력입증서류'. (evidence: stay L3107/L3172)
    - ⚠️ `학력 입증서류` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Generic faithful label; manual '최종학력입증서류'. (evidence: stay L3107/L3172)
    - ⚠️ `인턴활동계획서` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Whitespace vs '인턴활동 계획서'. (evidence: stay L5436)

### E-1
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- Naming near-miss candidates: 1 (all reviewed → skipped):
    - ⚠️ `고용계약서(원본 및 사본)` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Paren-wrapped vs '고용계약서 원본 및 사본'; same doc. (evidence: stay L3817)

### E-2
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- Naming near-miss candidates: 1 (all reviewed → skipped):
    - ⚠️ `공적확인을 받은 학력증명서` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Exact modulo '*' marker. (evidence: stay L6596)

### E-3
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- Naming near-miss candidates: 2 (all reviewed → skipped):
    - ⚠️ `국내·외 은행 잔고증명서(해당자)` [extension/requiredDocs] → **ALREADY_FAITHFUL** — Whitespace/dot-char diff. (evidence: stay L7077)
    - ⚠️ `통합신청서(별지 제34호 서식)` [reentry/requiredDocs] → **ALREADY_FAITHFUL** — Standard official form; exact match present. (evidence: stay L11254)

### E-4
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- No findings; no candidates. Clean.

### E-5
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- No findings; no candidates. Clean.
