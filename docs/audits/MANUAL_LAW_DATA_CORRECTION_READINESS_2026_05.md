# MANUAL/LAW DATA CORRECTION READINESS AUDIT (PR D0, 2026-05)

Date (UTC): 2026-05-26
Branch: `audit/manual-law-data-correction-readiness-2026-05`
Scope: **Audit-only** readiness planning for future PR D1/D2; no production behavior/data edits.

## Executive verdict
- This PR D0 produced a **source-grounded readiness framework**, but **did not authorize any production data correction yet**.
- For the requested focus issues (PDA-001/002/004/005/006/007/009/010/011), repository metadata indicates likely manual anchors (mostly in 2026.5 stay manual page ranges), but these anchors are predominantly tagged as `needs_manual_review` / `auto_extracted_needs_review`.
- In this environment, direct PDF text extraction tooling for the 2026.5 manuals was unavailable (`pdftotext` absent), so issue-level operational requirements could not be independently re-verified from manual body text line-by-line.
- Result: most items are **SOURCE_LOCATED_BUT_AMBIGUOUS** or **NEEDS_MANUAL_REVIEW**. No issue is promoted to `PATCH_READY_SOURCE_CONFIRMED` in this D0 output.
- F/G/H and untested sub-codes remain **DEFER_UNTESTED_COVERAGE** for data-correction readiness because Batch 2 and Batch 2 Rerun had blocked frontend audit coverage (0 statuses tested).

## Source hierarchy used (authority model)
1. `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`
2. `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`
3. Korean statutes/regulations as high-level authority only (출입국관리법 및 관련 하위 규정 등)
4. Official HiKorea/MOJ/KIS pages as supplementary official references

Guardrail applied:
- Repository JSON (`visa_data.json`, `backend/data/visas.json`, manual-grounding JSON) was treated as **implementation state only**, not source authority.

## Files inspected
- `docs/audits/AGENT_MODE_STAY_STATUS_UI_SOURCE_AUDIT_NORMALIZED_2026_05.md`
- `docs/audits/POST_PR_190_MAIN_STATE_AUDIT.md`
- `docs/audits/SEARCH_RESULT_PRECISION_PR_A_2026_05.md`
- `docs/audits/RESULT_CARD_TAB_MODAL_CONSISTENCY_PR_B_2026_05.md`
- `docs/audits/SOURCE_WARNING_LABEL_CONSISTENCY_PR_C_2026_05.md`
- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`
- `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`
- `visa_data.json` (read-only)
- `backend/data/visas.json` (read-only)
- `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` (read-only)
- `data/scenario_help_records.json` (read-only)
- `doc_master.json` (if present; read-only scope)

## Evidence collection constraints
- `pdftotext` is not installed in this environment, and no equivalent PDF text extraction package was preinstalled.
- Therefore, manual page/section evidence below uses repository-side manual reference metadata as a **locator cue only** and remains non-final until human/manual recheck against official PDFs.

## Issue-source matrix

| Issue | Code | Sub-code | Procedure type | Current Paradiso area | Source file checked | Manual page/section found | Short source summary | Law source needed | Confidence | Readiness status | Proposed future patch |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PDA-001 | A-1 | - | extension | `procedures.extension` / result-card extension tab | stay manual PDF + `visa_data.json` locator refs | `p.16` (locator, needs review) | Extension manualRef exists but marked needs manual review. | No | Medium | SOURCE_LOCATED_BUT_AMBIGUOUS | data correction |
| PDA-002 | A-2 | - | extension | `procedures.extension` / result-card extension tab | stay manual PDF + locator refs | `p.20` (locator, needs review) | Extension/registration refs exist; still auto-extracted/manual-review state. | No | Medium | SOURCE_LOCATED_BUT_AMBIGUOUS | data correction |
| PDA-004 | B-1 | - | registration + extension | `procedures.registration`, `procedures.extension` | stay manual PDF + locator refs | `p.24` / `pp.24-24` (locator) | Registration/extension anchors present but not independently re-verified from PDF body. | Yes (high-level duty basis) | Medium | SOURCE_LOCATED_BUT_AMBIGUOUS | data correction + source metadata correction |
| PDA-005 | B-2 | - | registration + extension | `procedures.registration`, `procedures.extension` | stay manual PDF + locator refs | `p.25` / `pp.25-25` (locator) | Similar to B-1; source anchors exist but flagged review-needed. | Yes (high-level duty basis) | Medium | SOURCE_LOCATED_BUT_AMBIGUOUS | data correction + source metadata correction |
| PDA-006 | C-1 | - | initial visa issuance (issue focus) | `documents_initial` + result-card initial tab | visa manual PDF + current locator refs mostly stay-side | No reliable initial-issuance section confirmed in this run | Repository pointers emphasize stay-side registration/extension, not confident initial-issuance proof extracted here. | Yes | Low | NEEDS_MANUAL_REVIEW | no patch yet |
| PDA-007 | C-3 | C-3-* | sub-code coverage (multi-procedure) | sub-code layer + procedure tabs | stay + visa manual PDFs + locator refs | extension `pp.27-28`; others “매뉴얼 확인 필요” | Sub-code families explicitly noted as requiring manual verification; coverage ambiguity remains high. | Yes | Low | NEEDS_MANUAL_REVIEW | manual grounding expansion |
| PDA-009 | D-4 | D-4-2K | document completeness | D-4 card, sub-code detail, registration/extension tabs | stay manual PDF + locator refs | extension `p.90`, registration `pp.83-101` (broad) | Broad registration range suggests ambiguous mapping to D-4-2K detail requirements. | Yes | Medium | SOURCE_LOCATED_BUT_AMBIGUOUS | data correction + source metadata correction |
| PDA-010 | D-10 | - | extension requirement | `procedures.extension` + extension docs tab | stay manual PDF + locator refs | extension `p.155`; registration `pp.142-165` | Source anchors exist but too broad for immediate correction without page-level manual recheck. | Yes | Medium | SOURCE_LOCATED_BUT_AMBIGUOUS | data correction |
| PDA-011 | E-7 | E-7-4 | sub-code detail | E-7 card + E-7-4 sub-code rows/tabs | stay manual PDF + locator refs | extension `p.226`; registration `pp.212-323` (very broad) | Very wide ranges; cannot safely map E-7 vs E-7-4 operational deltas without manual subsection confirmation. | Yes | Low | NEEDS_MANUAL_REVIEW | manual grounding expansion + data correction later |

## Patch-ready candidate list (for future PR D1/D2)
At this D0 checkpoint:
- **No item is elevated to `PATCH_READY_SOURCE_CONFIRMED`.**

Conditional near-ready candidates after manual cross-check:
- A-1 / A-2 extension + registration cues may become D1 candidates once cited pages are manually re-verified directly in the stay manual.
- B-1 / B-2 may become D1 candidates if registration duty + required-doc operational bullets are confirmed from manual body and statutory duty framing is separated cleanly.

## Blocked / deferred issue list

### A) Source located but ambiguous
- PDA-001, PDA-002, PDA-004, PDA-005, PDA-009, PDA-010

### B) Needs manual review (sub-code/initial-path ambiguity)
- PDA-006, PDA-007, PDA-011

### C) Not enough evidence (in this environment)
- Any item requiring direct body-text extraction from the 2026.5 PDF that could not be executed due missing extraction tooling.

### D) Deferred because Batch 2 UI audit failed
- F/G/H family corrections and untested sub-codes: **DEFER_UNTESTED_COVERAGE** until PR G interactive rerun succeeds.

## Risks and guardrails
- Do not convert repository `manualRefs` into “verified truth” without direct manual page checks.
- Keep law/statute use to high-level legal basis only; manual remains operational source for document/procedure checklists.
- Avoid introducing “verified=true” changes until crosswalk evidence is complete.
- Keep D1/D2 split narrow to reduce accidental cross-status regressions.

## Recommended PR D1/D2/D3/G sequence
1. **PR D1** — patch only high-confidence A/B/C-series items after direct page-level manual confirmation.
2. **PR D2** — handle D/E-series and sub-code-sensitive corrections (D-4-2K, E-7-4) after deeper subsection mapping.
3. **PR D3** — manual-grounding expansion only after source crosswalk stability and candidate validation.
4. **PR G** — rerun Batch 2 interactive audit for F/G/H and untested statuses before any F/G/H data corrections.

## Machine-readable JSON issue readiness list
```json
[
  {
    "issueId": "PDA-001",
    "severity": "P1",
    "code": "A-1",
    "subCode": null,
    "procedureType": "extension",
    "currentParadisoArea": "procedures.extension / result-card extension tab",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.16 (locator from repository manualRefs)",
        "findingSummary": "Extension anchor exists in local metadata but remains needs_manual_review; direct manual body verification pending."
      }
    ],
    "lawSourceNeeded": false,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "data correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Do not patch until page-level recheck is completed from official PDF text."
  },
  {
    "issueId": "PDA-002",
    "severity": "P1",
    "code": "A-2",
    "subCode": null,
    "procedureType": "extension",
    "currentParadisoArea": "procedures.extension / result-card extension tab",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.20 (locator from repository manualRefs)",
        "findingSummary": "Operational anchor exists but confidence tag remains auto_extracted_needs_review."
      }
    ],
    "lawSourceNeeded": false,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "data correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Manual body-text recheck required."
  },
  {
    "issueId": "PDA-004",
    "severity": "P1",
    "code": "B-1",
    "subCode": null,
    "procedureType": "foreigner registration",
    "currentParadisoArea": "procedures.registration / registration docs tab",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.24, pp.24-24 (locator refs)",
        "findingSummary": "Registration and extension locators exist, but source confidence remains needs_manual_review."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "data correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Statutory registration duty may be cited in D1 notes, but operational docs must be manual-grounded."
  },
  {
    "issueId": "PDA-005",
    "severity": "P1",
    "code": "B-2",
    "subCode": null,
    "procedureType": "foreigner registration",
    "currentParadisoArea": "procedures.registration / registration docs tab",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.25, pp.25-25 (locator refs)",
        "findingSummary": "Locator exists but still review-pending; no direct text verification completed in this environment."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "data correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Keep separate from B-1 unless both are independently rechecked."
  },
  {
    "issueId": "PDA-006",
    "severity": "P2",
    "code": "C-1",
    "subCode": null,
    "procedureType": "initial visa issuance",
    "currentParadisoArea": "documents_initial / result-card initial tab",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/visa_manual_2026_05.pdf",
        "pageOrSection": "not confidently located in this run",
        "findingSummary": "Insufficient direct source extraction evidence for initial-issuance document deltas."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "NEEDS_MANUAL_REVIEW",
    "confidence": "low",
    "proposedFuturePatch": "no patch yet",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Require direct visa-manual subsection confirmation."
  },
  {
    "issueId": "PDA-007",
    "severity": "P2",
    "code": "C-3",
    "subCode": "C-3-*",
    "procedureType": "other",
    "currentParadisoArea": "sub-code coverage / procedure tabs",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "pp.27-28 (extension locator), multiple 'manual review needed' refs",
        "findingSummary": "Sub-code-specific operational mapping remains unresolved."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "NEEDS_MANUAL_REVIEW",
    "confidence": "low",
    "proposedFuturePatch": "manual grounding expansion",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json", "backend/data/manual_grounding/stay_manual_grounding_2026_05.json"],
    "doNotPatchInThisPR": true,
    "notes": "Requires per-subcode mapping before data edits."
  },
  {
    "issueId": "PDA-009",
    "severity": "P2",
    "code": "D-4",
    "subCode": "D-4-2K",
    "procedureType": "extension",
    "currentParadisoArea": "D-4/D-4-2K docs completeness across tabs",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.90 (extension locator), pp.83-101 (registration locator)",
        "findingSummary": "Ranges are broad; D-4-2K deltas are not independently validated yet."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "source metadata correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Treat as D2 candidate after sub-code-specific manual crosswalk."
  },
  {
    "issueId": "PDA-010",
    "severity": "P2",
    "code": "D-10",
    "subCode": null,
    "procedureType": "extension",
    "currentParadisoArea": "procedures.extension / extension docs",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.155 (extension locator)",
        "findingSummary": "Anchor exists but still review-pending; no direct textual extraction verification in this environment."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "proposedFuturePatch": "data correction",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json"],
    "doNotPatchInThisPR": true,
    "notes": "Candidate for D2 once manual wording is rechecked."
  },
  {
    "issueId": "PDA-011",
    "severity": "P2",
    "code": "E-7",
    "subCode": "E-7-4",
    "procedureType": "extension",
    "currentParadisoArea": "E-7/E-7-4 sub-code detail and document scope",
    "officialSourceChecked": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.226 (extension locator), pp.212-323 (registration locator)",
        "findingSummary": "Locator ranges are too broad for safe E-7 vs E-7-4 split without manual subsection validation."
      }
    ],
    "lawSourceNeeded": true,
    "readinessStatus": "NEEDS_MANUAL_REVIEW",
    "confidence": "low",
    "proposedFuturePatch": "manual grounding expansion",
    "likelyFilesForFuturePatch": ["visa_data.json", "backend/data/visas.json", "backend/data/manual_grounding/stay_manual_grounding_2026_05.json"],
    "doNotPatchInThisPR": true,
    "notes": "Sub-code routing precision must be revalidated before any doc-list edits."
  }
]
```
