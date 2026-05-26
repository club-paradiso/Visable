# BATCH_2_FINAL_INTERACTIVE_RERUN_NORMALIZED_2026_05

Normalization target: PDF/report titled **PARADISO FULL STAY-STATUS UI AND SOURCE AUDIT - BATCH 2 FINAL INTERACTIVE RERUN - 2026.5**.

Related tracker: <https://github.com/lucanomics/Paradiso/issues/199>

## Executive summary

- Verdict: **PARTIALLY_READY**.
- This audit is valid interactive partial coverage. The deployed frontend loaded with the cache-busting URL `https://lucanomics.github.io/Paradiso/?audit_b2_final=2026-05-26`.
- This report supersedes prior blocked Batch 2 attempts only for the items that were actually tested interactively.
- It does **not** complete all F/G/H/H-2/C/D/E/scenario coverage.
- The report is audit evidence. It is not the official legal/manual source of truth and does not authorize direct data, document-list, verification metadata, or runtime patches.

## Normalization rules applied

- No production data or runtime behavior is changed by this document.
- The audit report's `likelyFiles` paths are treated as untrusted suggestions until validated against this repository.
- `sourceChecked` values from the audit are not patch authorization unless they include exact official manual page/section evidence and a repository crosswalk.
- Source confidence is conservative when only broad manual-section labels are available.
- `needsManualReviewNormalized` remains `true` for source, data, sub-code, and requirement issues without an exact official source crosswalk.
- No issue below should be patched directly from the audit report.

## Repository path validation

The audit report reportedly suggested these paths:

| Audit likelyFile | Repository validation |
| --- | --- |
| `frontend/data/f-series.json` | Not found. No `frontend/` directory exists in the current repository. |
| `frontend/data/g-series.json` | Not found. No `frontend/` directory exists in the current repository. |
| `frontend/data/h-series.json` | Not found. No `frontend/` directory exists in the current repository. |
| `frontend/components/DocsModal.vue` | Not found. No Vue component tree exists in the current repository. |
| `frontend/components/StayCard.vue` | Not found. No Vue component tree exists in the current repository. |

Validated repository files that may own future follow-up work:

- `index.html`
- `ai.html`
- `visa_data.json`
- `backend/data/visas.json`
- `backend/paradiso_backend.py`
- `docs/audits/AGENT_MODE_STAY_STATUS_UI_SOURCE_AUDIT_NORMALIZED_2026_05.md`
- `docs/audits/BATCH_2_FINAL_INTERACTIVE_RERUN_PROMPT_2026_05.md`
- `docs/audits/DATA_FGH_LAW_GROUNDING_ROADMAP_2026_05.md`
- `docs/audits/AI_FALLBACK_AND_REGRESSION_SMOKE_PR_EF_2026_05.md`

When an exact target is not confirmed below, the normalized issue says: **actual path requires follow-up inspection**.

## Coverage boundaries

Covered by this interactive partial audit:

| Area | Normalized status |
| --- | --- |
| F-1 | Covered only as an interactive tested top-level item. Not a full sub-code/source correction pass. |
| F-2 | Covered only as an interactive tested top-level item. Not a full sub-code/source correction pass. |
| F-3 | Covered only as an interactive tested top-level item. Not a full sub-code/source correction pass. |
| F-4 | Covered only as an interactive tested top-level item. Not a full sub-code/source correction pass. |
| F-5 | Covered only as an interactive tested top-level item. Not a full sub-code/source correction pass. |
| F-6 | Covered only as an interactive tested top-level item. F-6 sub-code data still requires exact source crosswalk. |
| G-1 | Covered for selected UI/control behavior and result inspection. G-1 data corrections still require exact source crosswalk. |
| H-1 | Covered only as a selected tested item. H-series is not complete. |
| Representative AI questions for F/G categories | Covered only for the representative questions documented by the audit. Not a complete AI answer-quality matrix. |

Not fully covered and must remain incomplete:

- H-2 and H-2 sub-categories.
- C-3-1 through C-3-9.
- D-2 sub-codes.
- D-4 sub-codes including D-4-2K.
- D-10 variants.
- E-7 variants including E-7-4.
- B-2-2 / Jeju visa exemption / regional entries.
- Scenario/helper records.
- Rare F/G/H sub-codes not surfaced by the UI.

## Source evidence posture

Repository context confirms the official manual files are present:

- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`
- `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`

Repository context also contains broad manual table-of-contents mapping for F/G/H sections in `docs/data/2026_05_21_MANUAL_TOC_MAP.md`, including F-1 through F-6, G-1, H-1, and the special H-2-related foreign-national Korean section. Those broad ranges are useful for planning, but they are not enough to authorize field-level data corrections or metadata promotion.

## Safety gates from issue #199

The tracker requires these gates for this normalization and all follow-up PRs:

- No bulk F/G/H data correction.
- No `needsManualReview` removal.
- No `verified=true` promotion.
- No trusting audit `likelyFiles` without repository path validation.
- No marking H-2, C-3, D/E sub-codes, B-2-2 / Jeju, or scenario/helper records as audit-complete.

This document preserves those gates.

## Normalized issue register

### PDA-B2R2-001

- id: `PDA-B2R2-001`
- severity: `P1`
- code: `G-1`
- subCode: `G-1 selected controls`
- component: `result_card|tabs|modal|copy_controls`
- issueType: `ui_control_routing`
- observed: Issue #199 records that the audit reported broken or mis-routed controls for G-1, including change-of-status, FAQ, and result-copy behavior.
- expected: G-1 controls should reproducibly route to the correct G-1 content and copy the correct G-1 result text without changing legal/data content.
- sourceCheckedFromAudit: Interactive frontend audit evidence. No official manual source authority is needed for the UI routing observation, but any content/data fix still requires official source crosswalk.
- sourceConfidence: `low`
- needsManualReviewNormalized: `true`
- repoPathValidation: audit likelyFiles are untrusted. `frontend/components/DocsModal.vue` and `frontend/components/StayCard.vue` are not present. Likely actual files are `index.html` and possibly `ai.html`; actual path requires follow-up inspection.
- recommendedNextPR: `G2: G-1 UI/button reproduction and fix`
- doNotPatchDirectlyFromAudit: `true`

### PDA-B2R2-002

- id: `PDA-B2R2-002`
- severity: `P1`
- code: `F-series`
- subCode: `F-1 through F-6 top-level tested records`
- component: `data_source_crosswalk`
- issueType: `source_confidence_gap`
- observed: The audit treated F-series records as interactively tested, but the available repository context does not include exact issue-level manual page/section excerpts for field-level corrections.
- expected: F-series corrections should be made only after an exact official manual crosswalk for each affected field and sub-code.
- sourceCheckedFromAudit: Report-level references to `stay_manual_2026_05.pdf` F-series sections, without exact normalized page/section evidence in this repository context.
- sourceConfidence: `medium`
- needsManualReviewNormalized: `true`
- repoPathValidation: audit likelyFiles are untrusted. `frontend/data/f-series.json` is not present. Potential future data targets are `visa_data.json` and `backend/data/visas.json`; actual patch paths require follow-up inspection and parity checks.
- recommendedNextPR: `D3C-Prep: F/G/H source correction crosswalk`
- doNotPatchDirectlyFromAudit: `true`

### PDA-B2R2-003

- id: `PDA-B2R2-003`
- severity: `P1`
- code: `F-6`
- subCode: `F-6-1|F-6-2|F-6-3 and related F-1-6 scenario boundary`
- component: `data_requirements`
- issueType: `subcode_specific_requirement_risk`
- observed: F-6 and related family-status paths are easy to conflate with F-1-6/G-1 scenario handling. The audit is not sufficient to authorize direct required-document or eligibility edits.
- expected: F-6 sub-code requirements and adjacent F-1-6/G-1 routing should be crosswalked against exact official manual pages before any data correction.
- sourceCheckedFromAudit: Report-level F-series/F-6 audit evidence plus repository candidate context for F-6 divorce/status-change review; no complete normalized crosswalk for all affected sub-codes is present here.
- sourceConfidence: `medium`
- needsManualReviewNormalized: `true`
- repoPathValidation: audit likelyFiles are untrusted. Potential future targets are `visa_data.json`, `backend/data/visas.json`, and candidate review docs under `backend/data/manual_grounding/candidates/`; actual path requires follow-up inspection.
- recommendedNextPR: `D3C-Prep: F/G/H source correction crosswalk`
- doNotPatchDirectlyFromAudit: `true`

### PDA-B2R2-004

- id: `PDA-B2R2-004`
- severity: `P1`
- code: `G-1`
- subCode: `G-1-1|G-1-5|G-1-6|G-1-10|G-1-11|G-1-12`
- component: `data_requirements`
- issueType: `source_confidence_gap`
- observed: The audit tested G-1 interactively, but G-1 sub-code-specific requirement corrections are not source-confirmed in this normalized artifact.
- expected: G-1 data changes should wait for exact manual page/section evidence and field-level mapping.
- sourceCheckedFromAudit: Report-level `stay_manual_2026_05.pdf` G-1 section reference; exact issue-level crosswalk not available in repository context.
- sourceConfidence: `medium`
- needsManualReviewNormalized: `true`
- repoPathValidation: audit likelyFiles are untrusted. `frontend/data/g-series.json` is not present. Potential future data targets are `visa_data.json` and `backend/data/visas.json`; actual path requires follow-up inspection.
- recommendedNextPR: `D3C-Prep: F/G/H source correction crosswalk`
- doNotPatchDirectlyFromAudit: `true`

### PDA-B2R2-005

- id: `PDA-B2R2-005`
- severity: `P2`
- code: `F/G representative AI`
- subCode: `representative audit prompts only`
- component: `ai_response`
- issueType: `ai_source_framing_and_coverage_limit`
- observed: The audit covered representative AI questions for F/G categories, but that is not a complete AI answer-quality or source-grounding matrix.
- expected: AI answers should keep uncertainty/source caveats where exact manual grounding is absent, and future tests should expand coverage without enabling law grounding by default.
- sourceCheckedFromAudit: Interactive AI audit evidence for selected F/G prompts. No complete official source crosswalk for every answer claim is present.
- sourceConfidence: `low`
- needsManualReviewNormalized: `true`
- repoPathValidation: audit likelyFiles are untrusted. Potential future targets are `ai.html`, `backend/paradiso_backend.py`, and backend evaluation fixtures; actual path requires follow-up inspection.
- recommendedNextPR: `D3C-Prep: F/G/H source correction crosswalk`
- doNotPatchDirectlyFromAudit: `true`

### PDA-B2R2-006

- id: `PDA-B2R2-006`
- severity: `P2`
- code: `Coverage boundary`
- subCode: `H-2|C-3-1..C-3-9|D/E variants|B-2-2|scenario/helper`
- component: `audit_coverage`
- issueType: `remaining_coverage_gap`
- observed: The final interactive rerun still did not complete H-2, C-3 sub-codes, D/E sub-codes, B-2-2 / Jeju, scenario/helper records, or rare F/G/H sub-codes not surfaced by UI.
- expected: These categories must remain explicitly incomplete until a future audit tests them interactively and records evidence.
- sourceCheckedFromAudit: Audit coverage table and issue #199 tracker context.
- sourceConfidence: `medium`
- needsManualReviewNormalized: `true`
- repoPathValidation: audit likelyFiles are untrusted. Potential future files include `index.html`, `ai.html`, `visa_data.json`, `backend/data/visas.json`, `data/scenario_help_records.json`, and follow-up audit docs; actual path requires follow-up inspection.
- recommendedNextPR: `Remaining coverage audit: C-3, D/E sub-codes, B-2-2/Jeju, scenarios`
- doNotPatchDirectlyFromAudit: `true`

### PDA-B2R2-007

- id: `PDA-B2R2-007`
- severity: `P1`
- code: `H-1`
- subCode: `H-1 requirements and extension handling`
- component: `data_requirements`
- issueType: `incomplete_requirement_source_crosswalk`
- observed: Issue #199 records that the audit flags H-1 incomplete requirements and unclear extension handling.
- expected: H-1 requirements and extension handling should be confirmed directly against the 2026.5 manuals before any data correction. H-series must not be considered complete until H-2 and H-2 sub-categories are separately audited.
- sourceCheckedFromAudit: Report-level `stay_manual_2026_05.pdf` H-1 section reference; no exact issue-level page/section crosswalk is present in this normalized repository context.
- sourceConfidence: `low`
- needsManualReviewNormalized: `true`
- repoPathValidation: audit likelyFiles are untrusted. `frontend/data/h-series.json` is not present. Potential future data targets are `visa_data.json` and `backend/data/visas.json`; actual path requires follow-up inspection.
- recommendedNextPR: `H-series audit: H-2 and H-1 source crosswalk`
- doNotPatchDirectlyFromAudit: `true`

## Recommended PR sequence

1. G1: normalize Batch 2 final audit.
2. G2: G-1 UI/button reproduction and fix.
3. D3C-Prep: F/G/H source correction crosswalk.
4. H-series audit: H-2 and H-1 source crosswalk.
5. Remaining coverage audit: C-3, D/E sub-codes, B-2-2/Jeju, scenarios.
6. D3C: source-confirmed F/G/H data corrections only.
7. Metadata PR: `verified`/`needsManualReview` updates only after strict criteria are met.

## Machine-readable normalized issues

```json
[
  {
    "id": "PDA-B2R2-001",
    "severity": "P1",
    "code": "G-1",
    "subCode": "G-1 selected controls",
    "component": "result_card|tabs|modal|copy_controls",
    "issueType": "ui_control_routing",
    "observed": "Issue #199 records that the audit reported broken or mis-routed controls for G-1, including change-of-status, FAQ, and result-copy behavior.",
    "expected": "G-1 controls should reproducibly route to the correct G-1 content and copy the correct G-1 result text without changing legal/data content.",
    "sourceCheckedFromAudit": "Interactive frontend audit evidence; not official manual authority for content/data changes.",
    "sourceConfidence": "low",
    "needsManualReviewNormalized": true,
    "repoPathValidation": {
      "auditLikelyFiles": "untrusted",
      "missingAuditPaths": [
        "frontend/components/DocsModal.vue",
        "frontend/components/StayCard.vue"
      ],
      "likelyActualFiles": [
        "index.html",
        "ai.html"
      ],
      "status": "actual path requires follow-up inspection"
    },
    "recommendedNextPR": "G2: G-1 UI/button reproduction and fix",
    "doNotPatchDirectlyFromAudit": true
  },
  {
    "id": "PDA-B2R2-002",
    "severity": "P1",
    "code": "F-series",
    "subCode": "F-1 through F-6 top-level tested records",
    "component": "data_source_crosswalk",
    "issueType": "source_confidence_gap",
    "observed": "The audit treated F-series records as interactively tested, but exact issue-level manual page/section excerpts are not available in repository context.",
    "expected": "F-series corrections should be made only after an exact official manual crosswalk for each affected field and sub-code.",
    "sourceCheckedFromAudit": "Report-level references to stay_manual_2026_05.pdf F-series sections; exact normalized page/section evidence not present.",
    "sourceConfidence": "medium",
    "needsManualReviewNormalized": true,
    "repoPathValidation": {
      "auditLikelyFiles": "untrusted",
      "missingAuditPaths": [
        "frontend/data/f-series.json"
      ],
      "likelyActualFiles": [
        "visa_data.json",
        "backend/data/visas.json"
      ],
      "status": "actual path requires follow-up inspection"
    },
    "recommendedNextPR": "D3C-Prep: F/G/H source correction crosswalk",
    "doNotPatchDirectlyFromAudit": true
  },
  {
    "id": "PDA-B2R2-003",
    "severity": "P1",
    "code": "F-6",
    "subCode": "F-6-1|F-6-2|F-6-3 and related F-1-6 scenario boundary",
    "component": "data_requirements",
    "issueType": "subcode_specific_requirement_risk",
    "observed": "F-6 and related family-status paths are easy to conflate with F-1-6/G-1 scenario handling; audit evidence is not sufficient to authorize direct data edits.",
    "expected": "F-6 sub-code requirements and adjacent F-1-6/G-1 routing should be crosswalked against exact official manual pages before any data correction.",
    "sourceCheckedFromAudit": "Report-level F-series/F-6 audit evidence plus repository candidate context; complete normalized crosswalk for all affected sub-codes not present.",
    "sourceConfidence": "medium",
    "needsManualReviewNormalized": true,
    "repoPathValidation": {
      "auditLikelyFiles": "untrusted",
      "missingAuditPaths": [
        "frontend/data/f-series.json"
      ],
      "likelyActualFiles": [
        "visa_data.json",
        "backend/data/visas.json",
        "backend/data/manual_grounding/candidates/"
      ],
      "status": "actual path requires follow-up inspection"
    },
    "recommendedNextPR": "D3C-Prep: F/G/H source correction crosswalk",
    "doNotPatchDirectlyFromAudit": true
  },
  {
    "id": "PDA-B2R2-004",
    "severity": "P1",
    "code": "G-1",
    "subCode": "G-1-1|G-1-5|G-1-6|G-1-10|G-1-11|G-1-12",
    "component": "data_requirements",
    "issueType": "source_confidence_gap",
    "observed": "The audit tested G-1 interactively, but G-1 sub-code-specific requirement corrections are not source-confirmed in this normalized artifact.",
    "expected": "G-1 data changes should wait for exact manual page/section evidence and field-level mapping.",
    "sourceCheckedFromAudit": "Report-level stay_manual_2026_05.pdf G-1 section reference; exact issue-level crosswalk not available in repository context.",
    "sourceConfidence": "medium",
    "needsManualReviewNormalized": true,
    "repoPathValidation": {
      "auditLikelyFiles": "untrusted",
      "missingAuditPaths": [
        "frontend/data/g-series.json"
      ],
      "likelyActualFiles": [
        "visa_data.json",
        "backend/data/visas.json"
      ],
      "status": "actual path requires follow-up inspection"
    },
    "recommendedNextPR": "D3C-Prep: F/G/H source correction crosswalk",
    "doNotPatchDirectlyFromAudit": true
  },
  {
    "id": "PDA-B2R2-005",
    "severity": "P2",
    "code": "F/G representative AI",
    "subCode": "representative audit prompts only",
    "component": "ai_response",
    "issueType": "ai_source_framing_and_coverage_limit",
    "observed": "The audit covered representative AI questions for F/G categories, but that is not a complete AI answer-quality or source-grounding matrix.",
    "expected": "AI answers should keep uncertainty/source caveats where exact manual grounding is absent, and future tests should expand coverage without enabling law grounding by default.",
    "sourceCheckedFromAudit": "Interactive AI audit evidence for selected F/G prompts; no complete official source crosswalk for every answer claim is present.",
    "sourceConfidence": "low",
    "needsManualReviewNormalized": true,
    "repoPathValidation": {
      "auditLikelyFiles": "untrusted",
      "missingAuditPaths": [],
      "likelyActualFiles": [
        "ai.html",
        "backend/paradiso_backend.py",
        "backend/data/eval/"
      ],
      "status": "actual path requires follow-up inspection"
    },
    "recommendedNextPR": "D3C-Prep: F/G/H source correction crosswalk",
    "doNotPatchDirectlyFromAudit": true
  },
  {
    "id": "PDA-B2R2-006",
    "severity": "P2",
    "code": "Coverage boundary",
    "subCode": "H-2|C-3-1..C-3-9|D/E variants|B-2-2|scenario/helper",
    "component": "audit_coverage",
    "issueType": "remaining_coverage_gap",
    "observed": "The final interactive rerun still did not complete H-2, C-3 sub-codes, D/E sub-codes, B-2-2 / Jeju, scenario/helper records, or rare F/G/H sub-codes not surfaced by UI.",
    "expected": "These categories must remain explicitly incomplete until a future audit tests them interactively and records evidence.",
    "sourceCheckedFromAudit": "Audit coverage table and issue #199 tracker context.",
    "sourceConfidence": "medium",
    "needsManualReviewNormalized": true,
    "repoPathValidation": {
      "auditLikelyFiles": "untrusted",
      "missingAuditPaths": [],
      "likelyActualFiles": [
        "index.html",
        "ai.html",
        "visa_data.json",
        "backend/data/visas.json",
        "data/scenario_help_records.json",
        "docs/audits/"
      ],
      "status": "actual path requires follow-up inspection"
    },
    "recommendedNextPR": "Remaining coverage audit: C-3, D/E sub-codes, B-2-2/Jeju, scenarios",
    "doNotPatchDirectlyFromAudit": true
  },
  {
    "id": "PDA-B2R2-007",
    "severity": "P1",
    "code": "H-1",
    "subCode": "H-1 requirements and extension handling",
    "component": "data_requirements",
    "issueType": "incomplete_requirement_source_crosswalk",
    "observed": "Issue #199 records that the audit flags H-1 incomplete requirements and unclear extension handling.",
    "expected": "H-1 requirements and extension handling should be confirmed directly against the 2026.5 manuals before any data correction; H-series must not be complete until H-2 is separately audited.",
    "sourceCheckedFromAudit": "Report-level stay_manual_2026_05.pdf H-1 section reference; no exact issue-level page/section crosswalk is present in repository context.",
    "sourceConfidence": "low",
    "needsManualReviewNormalized": true,
    "repoPathValidation": {
      "auditLikelyFiles": "untrusted",
      "missingAuditPaths": [
        "frontend/data/h-series.json"
      ],
      "likelyActualFiles": [
        "visa_data.json",
        "backend/data/visas.json"
      ],
      "status": "actual path requires follow-up inspection"
    },
    "recommendedNextPR": "H-series audit: H-2 and H-1 source crosswalk",
    "doNotPatchDirectlyFromAudit": true
  }
]
```

## Non-goals

- No F/G/H data corrections.
- No required-document changes.
- No `verified=true` promotion.
- No `needsManualReview` removal.
- No G-1 button fix.
- No law-grounding enablement.
- No UI redesign.
