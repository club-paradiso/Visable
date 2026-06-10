# Batch B02 — D-3, D-4, D-4-1, D-7, D-8, D-9

_Authoritative manuals: visaIssuance→visa_hwp_full.txt; 체류 tabs→stay_hwp_full.txt. Generated 2026-06-10._
**Batch totals:** confirmed fixes = 0; ambiguous/skipped = 8.


### D-3
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- No findings; no candidates. Clean.

### D-4
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- Naming near-miss candidates: 2 (all reviewed → skipped):
    - ⚠️ `표준입학허가서(대학 총·학장 발행)` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Matches manual modulo dot-char/space. (evidence: stay L3103 '③ 표준입학허가서* (대학 총․학장 발행)')
    - ⚠️ `부·모 잔고증명서 제출 시 가족관계증명서 추가 제출` [statusChange/conditionalDocs] → **ALREADY_FAITHFUL** — Conditional note, faithful to manual. (evidence: stay L3106)

### D-4-1
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- No findings; no candidates. Clean.

### D-7
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- No findings; no candidates. Clean.

### D-8
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- Naming near-miss candidates: 5 (all reviewed → skipped):
    - ⚠️ `수수료 면제` [reentry/requiredDocs] → **FEE_NOTE** — Fee note, not a document name; fees are protected. (evidence: stay L582)
    - ⚠️ `사업장 존재 입증서류` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Whitespace-only diff ('입증 서류'); appears in 2 different variants (not a dup). (evidence: stay L4260)
    - ⚠️ `공동사업자인 국민의 사업자금 사용내역 입증서류` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Flattened '(사용 내역)' parens; same doc. (evidence: stay L4306)
    - ⚠️ `사업장 존재 입증서류` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Whitespace-only diff ('입증 서류'); appears in 2 different variants (not a dup). (evidence: stay L4260)
    - ⚠️ `신청서, 여권, 표준규격사진, 체류지 입증서류` [statusChange/requiredDocs] → **MULTI_DOC_ELEMENT** — Comma-joined multi-doc element; splitting = restructuring, out of scope. (evidence: stay L4332)

### D-9
- Type A (exact dup): 0
- Type B (공통∩필수): 0
- Type E (embedded manual): 0
- Type N (near-dup): 0
- Naming near-miss candidates: 1 (all reviewed → skipped):
    - ⚠️ `체류자격 변경 사유서` [statusChange/requiredDocs] → **ALREADY_FAITHFUL** — Whitespace-only vs '체류자격변경 사유서'. (evidence: stay L4658)
