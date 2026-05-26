# DATA CORRECTION NEXT ROADMAP (2026-05)

Date (UTC): 2026-05-26  
Scope: Planning/readiness only (no production data patching)

## Executive summary
- PR D0 and PR D1D2 did **not** authorize any production data patch because there were no entries with `PATCH_READY_SOURCE_CONFIRMED` + `high` confidence.
- Current blockers are source ambiguity, per-subcode crosswalk instability, and unresolved F/G/H + untested-status UI/source coverage due to blocked interactive Batch 2 runs.
- This roadmap defines D3A/D3B/D3C/D3D sequencing and strict patchability gates.

## Why D1D2 made no data patch
1. No D0 issue met patch gate (`PATCH_READY_SOURCE_CONFIRMED` and `high`).
2. Many items stayed at `SOURCE_LOCATED_BUT_AMBIGUOUS` with locator-only page references.
3. C/D/E subcodes still need exact subsection-level source crosswalk.
4. F/G/H family remains deferred until successful interactive Batch 2 rerun (blocked runs tested 0 statuses).

## Patchability policy (must all be true)
A data patch is allowed only if all conditions are satisfied:
1. Official source confirmation at text level (not just broad page locator).
2. Correct code + subcode mapping confirmed (where subcode exists).
3. No conflict between stay/visa manual references.
4. Corresponding UI/source audit path is covered or explicitly non-UI dependent.
5. Mirror update parity is included (`visa_data.json` ↔ `backend/data/visas.json`) in the same PR.
6. No hard-constraint violations (`verified=true`, `needsManualReview` removals, required-doc list edits) unless explicitly source-confirmed and scoped for that future PR.

## Correction roadmap matrix

| issueId | code/status | subCode | current readiness | blocker | exact source needed | next action | future PR target |
|---|---|---:|---|---|---|---|---|
| PDA-001 | A-1 | - | SOURCE_LOCATED_BUT_AMBIGUOUS | locator-only confidence | stay manual exact subsection text for A-1 extension docs | re-extract + dual-review source snippet | D3A |
| PDA-002 | A-2 | - | SOURCE_LOCATED_BUT_AMBIGUOUS | locator-only confidence | stay manual exact subsection text for A-2 extension docs | re-extract + candidate diff draft | D3A |
| PDA-004 | B-1 | - | SOURCE_LOCATED_BUT_AMBIGUOUS | registration detail ambiguity | stay manual exact B-1 registration document list + law high-level basis | source cross-check + law/manual split note | D3A |
| PDA-005 | B-2 | - | SOURCE_LOCATED_BUT_AMBIGUOUS | registration detail ambiguity | stay manual exact B-2 registration document list + law high-level basis | source cross-check + candidate diff draft | D3A |
| PDA-006 | C-1 | - | NEEDS_MANUAL_REVIEW | visa manual section unresolved | visa manual exact C-1 issuance section | resolve location map first | D3A |
| PDA-007 | C-3 | C-3-* | NEEDS_MANUAL_REVIEW | subcode crosswalk incomplete | per-subcode C-3 source table from manuals | build subcode crosswalk matrix | D3B |
| PDA-009 | D-4 | D-4-2K | SOURCE_LOCATED_BUT_AMBIGUOUS | broad page range | exact D-4 vs D-4-2K subsection split | build side-by-side requirement matrix | D3B |
| PDA-010 | D-10 | D-10-* | SOURCE_LOCATED_BUT_AMBIGUOUS | subcode-level evidence missing | exact D-10 subcode subsection proofs | complete D-10 subtype crosswalk | D3B |
| PDA-011 | E-7 | E-7-4 | NEEDS_MANUAL_REVIEW | E-7 vs E-7-4 split unresolved | exact E-7/E-7-4 operational difference sections | map per-subcode with ambiguity tags | D3B |
| UNTESTED-FGH-SET | F/G/H + untested codes | many | DEFER_UNTESTED_COVERAGE | interactive audit blocked (0 statuses tested) | successful Batch 2 interactive output + source notes | run Batch 2 final rerun prompt first | D3C |

## Future PR sequencing
- **D3A**: A/B/C-series source extraction + correction candidates (no subcode-heavy edits unless fully proven).
- **D3B**: C-3 / D-4 / D-10 / E-7 subcode crosswalk stabilization + correction candidates.
- **D3C**: F/G/H extraction and correction candidates only after successful interactive Batch 2 coverage.
- **D3D**: manual-grounding JSON expansion after D3B/D3C crosswalks are stable.

## Source blockers
- Manual text extraction reliability and subsection pinpointing still limited in previous runs.
- Some entries rely on broad locator pages that are not safe for direct required-document edits.
- Batch 2 frontend-interaction blockage invalidates coverage claims for F/G/H and many subcodes.

## Machine-readable roadmap JSON
```json
[
  {
    "issueId": "PDA-001",
    "code": "A-1",
    "subCode": null,
    "readiness": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "blocker": "locator_only_source_confidence",
    "exactSourceNeeded": "stay_manual_2026_05.pdf exact A-1 extension subsection",
    "nextAction": "source_snippet_recheck_and_candidate_diff",
    "futurePr": "D3A"
  },
  {
    "issueId": "PDA-007",
    "code": "C-3",
    "subCode": "C-3-*",
    "readiness": "NEEDS_MANUAL_REVIEW",
    "blocker": "subcode_crosswalk_incomplete",
    "exactSourceNeeded": "manual per-subcode C-3 requirement table",
    "nextAction": "build_subcode_crosswalk",
    "futurePr": "D3B"
  },
  {
    "issueId": "UNTESTED-FGH-SET",
    "code": "F/G/H",
    "subCode": "multiple",
    "readiness": "DEFER_UNTESTED_COVERAGE",
    "blocker": "batch2_interactive_blocked_zero_statuses",
    "exactSourceNeeded": "completed Batch 2 interactive coverage outputs",
    "nextAction": "execute_batch2_final_interactive_rerun_prompt",
    "futurePr": "D3C"
  }
]
```
