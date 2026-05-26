# AGENT_MODE_STAY_STATUS_UI_SOURCE_AUDIT_NORMALIZED_2026_05

> Normalization target: Agent Mode PDF report titled **"PARADISO FULL STAY-STATUS UI AND SOURCE AUDIT - 2026.5"**.

## Scope and intent
- This document converts the Agent Mode audit into a Codex-ready, repository-grounded audit planning artifact.
- **No production/data/legal patching is included here.**
- This is **PR 0 (normalization + path validation only)**.

## Hard constraints applied
- No edits to `index.html`, `ai.html`, `visa_data.json`, `backend/data/visas.json`, `backend/paradiso_backend.py`, or manual grounding JSON.
- No legal/data source patching in this PR.
- Audit-suggested component paths were treated as untrusted until checked against repository paths.

## Repository path validation summary
Audit-suggested frontend paths mentioned in PDF prompt context:
- `frontend/src/components/VisaCardModal.vue` → **not found**
- `frontend/src/components/DocumentTabs.vue` → **not found**
- `frontend/src/components/SearchBar.jsx` → **not found**
- `frontend/src/pages/HomePage.jsx` → **not found**

Likely active files in this repository architecture:
- `index.html`
- `ai.html`
- `visa_data.json`
- `backend/data/visas.json`
- `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`
- `backend/paradiso_backend.py`
- `backend/tests/test_paradiso_backend.py`
- `scripts/check_repo.sh`

## Coverage limitation (must-carry warning)
- The PDF audit covered only **15 top-level status codes**.
- **F-series, G-1, and H-series** were not fully tested.
- Therefore this is **not** a full all-status audit.

## Do Not Patch Yet warning
Any issue that depends on legal/manual/data truth (citations, status conditions, required documents, fee/source claims, policy labels) is **blocked** until:
1) source manual/law evidence is confirmed in official source files, and
2) manual-grounding crosswalks are re-verified.

---

## Normalized issue register (repository-grounded)

> Note: The PDF body itself is an external artifact. This normalization retains the issue IDs and working intent, but marks source-verification limits when direct evidence is not present in repository files.

### PDA-001
- Severity: P1
- Original code: A-1
- Repository Validation:
  - Audit-suggested path not found in repository.
  - Likely files: `index.html`, `ai.html`, `visa_data.json`, `backend/data/visas.json`.
- Patch status: **Do not patch yet** (requires manual/source re-check).
- Recommended PR batch: **PR A** (search precision / exact-code ordering).

### PDA-002
- Severity: P1
- Original code: UNKNOWN_FROM_PDF
- Repository Validation:
  - Audit-suggested path not found in repository.
  - Likely files: `index.html`, `ai.html`, `backend/paradiso_backend.py`.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR B** (UI tab/modal consistency).

### PDA-003
- Severity: P1
- Original code: UNKNOWN_FROM_PDF
- Repository Validation:
  - Audit-suggested path not found in repository.
  - Likely files: `index.html`, `ai.html`.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR B**.

### PDA-004
- Severity: P1
- Original code: UNKNOWN_FROM_PDF
- Repository Validation:
  - Audit-suggested path not found in repository.
  - Likely files: `index.html`, `ai.html`, `backend/paradiso_backend.py`.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR C** (source label/warning consistency).

### PDA-005
- Severity: P1
- Original code: UNKNOWN_FROM_PDF
- Repository Validation:
  - Audit-suggested path not found in repository.
  - Likely files: `visa_data.json`, `backend/data/visas.json`, `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`.
- Patch status: **Blocked** pending citation verification.
- Recommended PR batch: **PR D**.

### PDA-006
- Severity: P1
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: same as PDA-005.
- Patch status: **Blocked** pending citation verification.
- Recommended PR batch: **PR D**.

### PDA-007
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely UI + source badge wiring in `index.html`/`ai.html`.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR C**.

### PDA-008
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely search/render behavior in `index.html`.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR A**.

### PDA-009
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely modal close/tab behavior in `index.html`.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR B**.

### PDA-010
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely AI answer/source handling in `ai.html`, `backend/paradiso_backend.py`.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR E**.

### PDA-011
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely source-warning consistency in `ai.html`, backend services.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR C / PR E**.

### PDA-012
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely data/manual field mismatch paths.
- Patch status: **Blocked** until manual citation check.
- Recommended PR batch: **PR D**.

### PDA-013
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely fallback/foreign-system leakage guard.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR E**.

### PDA-014
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely UI consistency + warning labels.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR B / PR C**.

### PDA-015
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely result ranking/exact-code signal.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR A**.

### PDA-016
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely backend/source routing logic.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR E**.

### PDA-017
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely regression/test gap.
- Patch status: **Patch only in test PR.**
- Recommended PR batch: **PR F**.

### PDA-023
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely out-of-scope status coverage gap.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR G**.

### PDA-024
- Severity: P2
- Original code: UNKNOWN_FROM_PDF
- Repository Validation: likely out-of-scope status coverage gap.
- Patch status: **Do not patch yet**.
- Recommended PR batch: **PR G**.

---

## PR batch plan

### PR 0 — audit normalization and path validation only
- Issue IDs: PDA-001..017, PDA-023, PDA-024
- Actual likely files: `docs/audits/AGENT_MODE_STAY_STATUS_UI_SOURCE_AUDIT_NORMALIZED_2026_05.md`
- Non-goals: any runtime/data/manual/legal content changes
- Required validation commands:
  - `git status --short`
  - `git diff --check`
  - `bash scripts/check_repo.sh`
- Manual QA:
  - Confirm listed non-existent audit-suggested paths are flagged
  - Confirm all issue IDs are present

### PR A — search precision and exact-code result ordering
- Issue IDs: PDA-001, PDA-008, PDA-015
- Likely files: `index.html`, `backend/paradiso_backend.py`, tests
- Non-goals: data/legal citation patching
- Required validation commands: repo checks + targeted UI smoke
- Manual QA: exact-code query precedence over fuzzy matches

### PR B — UI tab/modal consistency and close-button behavior
- Issue IDs: PDA-002, PDA-003, PDA-009, PDA-014
- Likely files: `index.html`, `ai.html`
- Non-goals: backend model/data changes
- Required validation commands: repo checks + browser smoke
- Manual QA: modal open/close parity, tab-state persistence

### PR C — source label and warning display consistency
- Issue IDs: PDA-004, PDA-007, PDA-011, PDA-014
- Likely files: `index.html`, `ai.html`, backend response formatting
- Non-goals: legal conclusion changes
- Required validation commands: repo checks + golden prompt checks
- Manual QA: warning/source labels appear consistently across surfaces

### PR D — narrow data corrections only where manual citations are verified
- Issue IDs: PDA-005, PDA-006, PDA-012
- Likely files: `visa_data.json`, `backend/data/visas.json`, `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`
- Non-goals: speculative/manual-absent edits
- Required validation commands: data integrity scripts + repo checks
- Manual QA: field-by-field validation against official manual text

### PR E — AI grounding fallback behavior and foreign-system leakage prevention
- Issue IDs: PDA-010, PDA-011, PDA-013, PDA-016
- Likely files: `ai.html`, `backend/paradiso_backend.py`, `backend/services/*.py`
- Non-goals: UI redesign
- Required validation commands: backend tests + AI smoke scripts
- Manual QA: unsupported/uncertain queries produce safe fallback behavior

### PR F — regression tests and smoke checks
- Issue IDs: PDA-017 (+ all resolved issues)
- Likely files: `backend/tests/test_paradiso_backend.py`, `scripts/smoke_ai_payload.js`, `scripts/check_repo.sh`
- Non-goals: feature work
- Required validation commands: `pytest`, smoke scripts
- Manual QA: replay top risk scenarios

### PR G — second-pass audit coverage for F/G/H and untested statuses
- Issue IDs: PDA-023, PDA-024
- Likely files: audit docs + test matrix docs
- Non-goals: first-pass bug triage re-litigation
- Required validation commands: coverage matrix scripts
- Manual QA: include previously untested F-series, G-1, H-series

---

## Machine-readable normalized issue list (JSON)

```json
[
  {"id":"PDA-001","severity":"P1","originalCode":"A-1","component":"Search/Results","issueType":"search_precision_ordering","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":["frontend/src/components/SearchBar.jsx","frontend/src/pages/HomePage.jsx"],"existingLikelyFiles":["index.html","backend/paradiso_backend.py"],"missingSuggestedFiles":["frontend/src/components/SearchBar.jsx","frontend/src/pages/HomePage.jsx"]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Normalization-only PR; no behavior patching","recommendedPR":"PR A","needsManualReview":true},
  {"id":"PDA-002","severity":"P1","originalCode":"UNKNOWN_FROM_PDF","component":"UI Modal","issueType":"modal_consistency","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":["frontend/src/components/VisaCardModal.vue"],"existingLikelyFiles":["index.html"],"missingSuggestedFiles":["frontend/src/components/VisaCardModal.vue"]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Normalization-only PR","recommendedPR":"PR B","needsManualReview":true},
  {"id":"PDA-003","severity":"P1","originalCode":"UNKNOWN_FROM_PDF","component":"UI Tabs","issueType":"tab_consistency","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":["frontend/src/components/DocumentTabs.vue"],"existingLikelyFiles":["index.html"],"missingSuggestedFiles":["frontend/src/components/DocumentTabs.vue"]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Normalization-only PR","recommendedPR":"PR B","needsManualReview":true},
  {"id":"PDA-004","severity":"P1","originalCode":"UNKNOWN_FROM_PDF","component":"Source Label","issueType":"label_warning_consistency","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["index.html","ai.html","backend/paradiso_backend.py"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Needs source policy validation","recommendedPR":"PR C","needsManualReview":true},
  {"id":"PDA-005","severity":"P1","originalCode":"UNKNOWN_FROM_PDF","component":"Data","issueType":"manual_data_mismatch","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["visa_data.json","backend/data/visas.json","backend/data/manual_grounding/stay_manual_grounding_2026_05.json"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Legal/manual citation verification required","recommendedPR":"PR D","needsManualReview":true},
  {"id":"PDA-006","severity":"P1","originalCode":"UNKNOWN_FROM_PDF","component":"Data","issueType":"manual_data_mismatch","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["visa_data.json","backend/data/visas.json","backend/data/manual_grounding/stay_manual_grounding_2026_05.json"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Legal/manual citation verification required","recommendedPR":"PR D","needsManualReview":true},
  {"id":"PDA-007","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"UI Source Badge","issueType":"label_warning_consistency","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["index.html","ai.html"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Normalization-only PR","recommendedPR":"PR C","needsManualReview":true},
  {"id":"PDA-008","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"Search","issueType":"ranking_precision","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":["frontend/src/components/SearchBar.jsx"],"existingLikelyFiles":["index.html"],"missingSuggestedFiles":["frontend/src/components/SearchBar.jsx"]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Normalization-only PR","recommendedPR":"PR A","needsManualReview":true},
  {"id":"PDA-009","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"UI Modal","issueType":"close_behavior","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":["frontend/src/components/VisaCardModal.vue"],"existingLikelyFiles":["index.html"],"missingSuggestedFiles":["frontend/src/components/VisaCardModal.vue"]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Normalization-only PR","recommendedPR":"PR B","needsManualReview":true},
  {"id":"PDA-010","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"AI","issueType":"fallback_behavior","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["ai.html","backend/paradiso_backend.py"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Needs controlled AI fallback verification","recommendedPR":"PR E","needsManualReview":true},
  {"id":"PDA-011","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"AI/Source","issueType":"source_warning_consistency","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["ai.html","backend/paradiso_backend.py"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Needs policy/source verification","recommendedPR":"PR C / PR E","needsManualReview":true},
  {"id":"PDA-012","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"Data","issueType":"citation_integrity","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["visa_data.json","backend/data/manual_grounding/stay_manual_grounding_2026_05.json"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Manual/law evidence required","recommendedPR":"PR D","needsManualReview":true},
  {"id":"PDA-013","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"AI","issueType":"foreign_system_leakage_prevention","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["backend/paradiso_backend.py","backend/services/law_grounding.py"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Needs behavior validation","recommendedPR":"PR E","needsManualReview":true},
  {"id":"PDA-014","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"UI","issueType":"tab_modal_warning_consistency","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":["frontend/src/components/DocumentTabs.vue"],"existingLikelyFiles":["index.html","ai.html"],"missingSuggestedFiles":["frontend/src/components/DocumentTabs.vue"]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Normalization-only PR","recommendedPR":"PR B / PR C","needsManualReview":true},
  {"id":"PDA-015","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"Search","issueType":"exact_code_priority","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":["frontend/src/components/SearchBar.jsx"],"existingLikelyFiles":["index.html","backend/paradiso_backend.py"],"missingSuggestedFiles":["frontend/src/components/SearchBar.jsx"]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Normalization-only PR","recommendedPR":"PR A","needsManualReview":true},
  {"id":"PDA-016","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"Backend/AI","issueType":"grounding_routing","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["backend/paradiso_backend.py","backend/services/grounding_config.py"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Needs AI/runtime verification","recommendedPR":"PR E","needsManualReview":true},
  {"id":"PDA-017","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"QA","issueType":"regression_gap","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["backend/tests/test_paradiso_backend.py","scripts/check_repo.sh"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Reserved for regression PR","recommendedPR":"PR F","needsManualReview":true},
  {"id":"PDA-023","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"Coverage","issueType":"untested_status_family","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["docs/paradiso_ai_coverage_matrix.md","backend/data/eval/paradiso_coverage_matrix.json"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Second-pass coverage needed","recommendedPR":"PR G","needsManualReview":true},
  {"id":"PDA-024","severity":"P2","originalCode":"UNKNOWN_FROM_PDF","component":"Coverage","issueType":"untested_status_family","originalObserved":"See PDF","originalExpected":"See PDF","sourceClaimFromPdf":"See PDF","repoPathValidation":{"auditSuggestedFiles":[],"existingLikelyFiles":["docs/paradiso_ai_coverage_matrix.md","backend/data/eval/paradiso_coverage_matrix.json"],"missingSuggestedFiles":[]},"canPatchNow":false,"reasonPatchBlockedOrAllowed":"Second-pass coverage needed","recommendedPR":"PR G","needsManualReview":true}
]
```
