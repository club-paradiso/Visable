# MANUAL/LAW DATA CORRECTION READINESS AUDIT (PR D0, 2026-05)

Date (UTC): 2026-05-26
Branch: `audit/manual-law-data-correction-readiness-2026-05`
Scope: Audit-only readiness planning for future PR D1/D2; no production behavior/data edits.

## Executive verdict
- Prepared a source-grounded readiness matrix for PDA-001/002/004/005/006/007/009/010/011.
- No production data/UI/AI/grounding behavior changes were made in this PR.
- In this environment, direct manual body extraction from PDF could not be completed (`pdftotext` unavailable), so manual evidence remains locator-level for most issues.
- Therefore, items are classified as `SOURCE_LOCATED_BUT_AMBIGUOUS`, `NEEDS_MANUAL_REVIEW`, or `NOT_ENOUGH_EVIDENCE`; none is promoted to `PATCH_READY_SOURCE_CONFIRMED` yet.
- F/G/H and untested sub-codes remain deferred for correction readiness pending successful Batch 2 interactive audit rerun.

## Source hierarchy used
1. `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`
2. `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`
3. Korean laws/regulations (high-level legal basis only)
4. Official HiKorea/MOJ/KIS pages (supplementary)

Guardrail: repository JSON files were treated as implementation targets only, not source authority.

## Files inspected
- `docs/audits/AGENT_MODE_STAY_STATUS_UI_SOURCE_AUDIT_NORMALIZED_2026_05.md`
- `docs/audits/POST_PR_190_MAIN_STATE_AUDIT.md`
- `docs/audits/SEARCH_RESULT_PRECISION_PR_A_2026_05.md`
- `docs/audits/RESULT_CARD_TAB_MODAL_CONSISTENCY_PR_B_2026_05.md`
- `docs/audits/SOURCE_WARNING_LABEL_CONSISTENCY_PR_C_2026_05.md`
- `docs/audits/SOURCE_STATUS_I18N_HOTFIX_2026_05.md`
- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`
- `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`
- `visa_data.json` (read-only)
- `backend/data/visas.json` (read-only)
- `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` (read-only)
- `data/scenario_help_records.json` (read-only)
- `doc_master.json` (read-only if present)

## Issue-source matrix

| issueId | code | subCode | procedureType | currentParadisoArea | source file checked | manual page/section | short source summary | law source needed | confidence | readinessStatus | proposed future patch |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PDA-001 | A-1 | null | extension | documents_extension / result-card extension tab | stay manual + local locator refs | p.16 (locator) | Extension anchor exists but flagged manual review in current metadata. | false | medium | SOURCE_LOCATED_BUT_AMBIGUOUS | data correction |
| PDA-002 | A-2 | null | extension | documents_extension / result-card extension tab | stay manual + local locator refs | p.20 (locator) | Anchor exists; extraction confidence still review-pending. | false | medium | SOURCE_LOCATED_BUT_AMBIGUOUS | data correction |
| PDA-004 | B-1 | null | foreigner registration | documents_registration / registration tab | stay manual + local locator refs | p.24 / pp.24-24 (locator) | Registration/extension cues exist but not independently re-verified from official PDF body. | true | medium | SOURCE_LOCATED_BUT_AMBIGUOUS | data correction |
| PDA-005 | B-2 | null | foreigner registration | documents_registration / registration tab | stay manual + local locator refs | p.25 / pp.25-25 (locator) | Similar to B-1; still manual-review state. | true | medium | SOURCE_LOCATED_BUT_AMBIGUOUS | data correction |
| PDA-006 | C-1 | null | initial visa issuance | documents_initial / initial tab | visa manual (target) + local state | exact section not confidently located | Initial-issuance source section not confidently pinned in this run. | true | low | NEEDS_MANUAL_REVIEW | no patch yet |
| PDA-007 | C-3 | C-3-* | other | sub-code coverage + procedure tabs | stay/visa manuals + local refs | pp.27-28 for some flows; others unresolved | Sub-code-level mapping remains incomplete/ambiguous. | true | low | NEEDS_MANUAL_REVIEW | manual grounding expansion |
| PDA-009 | D-4 | D-4-2K | extension | D-4 + D-4-2K document completeness | stay manual + local refs | p.90, pp.83-101 (broad) | Broad range; cannot safely map D-4 vs D-4-2K details yet. | true | medium | SOURCE_LOCATED_BUT_AMBIGUOUS | source metadata correction |
| PDA-010 | D-10 | null | extension | D-10 extension docs | stay manual + local refs | p.155 (locator) | Source cue exists but needs direct manual text confirmation. | true | medium | SOURCE_LOCATED_BUT_AMBIGUOUS | data correction |
| PDA-011 | E-7 | E-7-4 | extension | E-7 / E-7-4 sub-code detail | stay manual + local refs | p.226, pp.212-323 (very broad) | E-7 vs E-7-4 operational split not safely confirmed yet. | true | low | NEEDS_MANUAL_REVIEW | manual grounding expansion |

## Patch-ready candidate list
A. Patch-ready after source confirmation
- None in this D0 run.

B. Source located but ambiguous
- PDA-001, PDA-002, PDA-004, PDA-005, PDA-009, PDA-010

C. Needs manual review
- PDA-006, PDA-007, PDA-011

D. Blocked due to missing official source certainty
- Any issue requiring exact manual subsection proof not extracted in this environment.

E. Deferred because Batch 2 UI audit failed
- F/G/H family and untested sub-codes: `DEFER_UNTESTED_COVERAGE` until Batch 2 interactive rerun succeeds.

## Risks and guardrails
- Do not convert local `manualRefs` into authoritative truth without direct manual page verification.
- Keep statute use high-level; operational document lists must come from official manuals.
- Do not set `verified=true` or remove `needsManualReview` until source crosswalk is complete.

## Recommended PR sequence
1. PR D1: high-confidence A/B/C-series corrections only after direct manual page confirmation.
2. PR D2: D/E-series and sub-code-sensitive corrections after deeper subsection verification.
3. PR D3: manual-grounding expansion after stable source crosswalk.
4. PR G: Batch 2 interactive audit rerun for F/G/H and untested statuses before any F/G/H data edits.

## Machine-readable JSON issue readiness list
```json
[
  {
    "issueId": "PDA-001",
    "severity": "P1",
    "code": "A-1",
    "subCode": null,
    "procedureType": "extension",
    "currentParadisoArea": "documents_extension / result-card extension tab",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.16 (locator)",
        "findingSummary": "Anchor exists but remains review-pending in current metadata."
      }
    ],
    "lawSourceNeeded": false,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "data correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Needs direct manual text-level confirmation before D1."
  },
  {
    "issueId": "PDA-002",
    "severity": "P1",
    "code": "A-2",
    "subCode": null,
    "procedureType": "extension",
    "currentParadisoArea": "documents_extension / result-card extension tab",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.20 (locator)",
        "findingSummary": "Anchor exists; still review-pending."
      }
    ],
    "lawSourceNeeded": false,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "data correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Manual subsection confirmation required."
  },
  {
    "issueId": "PDA-004",
    "severity": "P1",
    "code": "B-1",
    "subCode": null,
    "procedureType": "foreigner registration",
    "currentParadisoArea": "documents_registration / registration tab",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.24 / pp.24-24 (locator)",
        "findingSummary": "Registration-related locator exists, but not independently proven from manual body in this run."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "data correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Use law only for high-level duty framing, not document list construction."
  },
  {
    "issueId": "PDA-005",
    "severity": "P1",
    "code": "B-2",
    "subCode": null,
    "procedureType": "foreigner registration",
    "currentParadisoArea": "documents_registration / registration tab",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.25 / pp.25-25 (locator)",
        "findingSummary": "Source cue exists but remains needs-manual-review state."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "data correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Separate verification from B-1 recommended."
  },
  {
    "issueId": "PDA-006",
    "severity": "P2",
    "code": "C-1",
    "subCode": null,
    "procedureType": "initial visa issuance",
    "currentParadisoArea": "documents_initial / initial tab",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/visa_manual_2026_05.pdf",
        "pageOrSection": "not confidently located in this run",
        "findingSummary": "Insufficient evidence to map initial document issue confidently."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "NEEDS_MANUAL_REVIEW",
    "confidence": "low",
    "proposedFuturePatch": "no patch yet",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Requires explicit visa-manual section confirmation."
  },
  {
    "issueId": "PDA-007",
    "severity": "P2",
    "code": "C-3",
    "subCode": "C-3-*",
    "procedureType": "other",
    "currentParadisoArea": "sub-code coverage + procedure tabs",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "pp.27-28 for some extension references",
        "findingSummary": "Sub-code-level source mapping remains incomplete."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "NEEDS_MANUAL_REVIEW",
    "confidence": "low",
    "proposedFuturePatch": "manual grounding expansion",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json", "backend/data/manual_grounding/stay_manual_grounding_2026_05.json"],
    "doNotPatchInThisPR": true,
    "notes": "Per-subcode verification required before data edits."
  },
  {
    "issueId": "PDA-009",
    "severity": "P2",
    "code": "D-4",
    "subCode": "D-4-2K",
    "procedureType": "extension",
    "currentParadisoArea": "D-4 / D-4-2K document completeness",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.90; pp.83-101 (locator)",
        "findingSummary": "Range too broad for safe sub-code-specific correction now."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "source metadata correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "D2 candidate after deeper sub-code source split."
  },
  {
    "issueId": "PDA-010",
    "severity": "P2",
    "code": "D-10",
    "subCode": null,
    "procedureType": "extension",
    "currentParadisoArea": "D-10 extension docs",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.155 (locator)",
        "findingSummary": "Anchor present but needs direct manual proof before correction."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "data correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Keep in D2 unless section-level confidence rises."
  },
  {
    "issueId": "PDA-011",
    "severity": "P2",
    "code": "E-7",
    "subCode": "E-7-4",
    "procedureType": "extension",
    "currentParadisoArea": "E-7 / E-7-4 sub-code detail",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.226; pp.212-323 (locator)",
        "findingSummary": "Very broad ranges; sub-code distinction still ambiguous."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "NEEDS_MANUAL_REVIEW",
    "confidence": "low",
    "proposedFuturePatch": "manual grounding expansion",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json", "backend/data/manual_grounding/stay_manual_grounding_2026_05.json"],
    "doNotPatchInThisPR": true,
    "notes": "Requires explicit E-7 vs E-7-4 source partitioning first."
  }
]
```
