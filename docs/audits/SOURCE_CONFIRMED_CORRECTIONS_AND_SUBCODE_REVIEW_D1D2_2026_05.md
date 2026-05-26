# SOURCE-CONFIRMED CORRECTIONS AND SUB-CODE REVIEW (PR D1D2, 2026-05)

Date (UTC): 2026-05-26  
Branch: `fix/source-confirmed-data-and-subcode-review-2026-05`

## 1) Executive verdict
- PR D0 contains **no** issues with `readinessStatus == PATCH_READY_SOURCE_CONFIRMED` and `confidence == high`.
- Therefore, this PR applies **no data patch** to `visa_data.json`, `backend/data/visas.json`, or manual-grounding JSON.
- This PR performs D2-style review documentation only for ambiguous/sub-code-sensitive issues and keeps all such items deferred.

## 2) D0 source used
Primary readiness source:
- `docs/audits/MANUAL_LAW_DATA_CORRECTION_READINESS_2026_05.md`

Official manual hierarchy referenced by D0:
1. `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`
2. `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`

## 3) D1 patch list
Internal extraction result for entries matching:
- `readinessStatus == PATCH_READY_SOURCE_CONFIRMED`
- `confidence == high`

Result:
- **No matching entries found in D0.**

## 4) D1 actual data changes
- No data fields were changed.
- No metadata changes were made (`verified`, `needsManualReview`, source notes, or grounding pointers).
- Visa mirror parity remains unchanged.

## 5) Items intentionally not patched
All below remain unpatched because D0 does not authorize patching with high-confidence source-confirmed readiness:
- `PDA-001` (A-1): `SOURCE_LOCATED_BUT_AMBIGUOUS`
- `PDA-002` (A-2): `SOURCE_LOCATED_BUT_AMBIGUOUS`
- `PDA-004` (B-1): `SOURCE_LOCATED_BUT_AMBIGUOUS`
- `PDA-005` (B-2): `SOURCE_LOCATED_BUT_AMBIGUOUS`
- `PDA-006` (C-1): `NEEDS_MANUAL_REVIEW`
- `PDA-007` (C-3 / C-3-*): `NEEDS_MANUAL_REVIEW`
- `PDA-009` (D-4 / D-4-2K): `SOURCE_LOCATED_BUT_AMBIGUOUS`
- `PDA-010` (D-10): `SOURCE_LOCATED_BUT_AMBIGUOUS`
- `PDA-011` (E-7 / E-7-4): `NEEDS_MANUAL_REVIEW`

## 6) D2 sub-code review matrix (audit-only)

| code | subCode | manual section/page from D0 | current Paradiso representation (high level) | mismatch/missing coverage summary | confidence | patch readiness | recommended next step |
|---|---|---|---|---|---|---|---|
| C-3 | C-3-* | stay manual pp.27-28 (partial locator only) | Base `C-3` entry present; granular sub-code partition not source-confirmed in D0 | Sub-code-level mapping remains incomplete (C-3-1/2/3/4/5/6/8/9 not confirmed for direct patch) | low | NEEDS_MANUAL_REVIEW | D2a only after per-sub-code source confirmation |
| D-4 | D-4-2K | stay manual p.90; pp.83-101 broad locator | `D-4` and `D-4-2K` entries exist | Broad range does not safely resolve D-4 vs D-4-2K document deltas | medium | SOURCE_LOCATED_BUT_AMBIGUOUS | D2a after sub-code document-level split confirmation |
| D-10 | D-10-1/2/T | stay manual p.155 locator | Base `D-10` entry present; sub-code detail not confirmed in D0 | Extension requirement details remain locator-level only | medium | SOURCE_LOCATED_BUT_AMBIGUOUS | D2a after subsection proof |
| E-7 | E-7-1/2/3/4 | stay manual p.226; pp.212-323 broad locator | Base `E-7` entry present; E-7-4 sensitivity noted | E-7 vs E-7-4 operational split unresolved | low | NEEDS_MANUAL_REVIEW | D3-oriented source partition/manual-grounding follow-up |

## 7) Blocked/deferred issues
- Any item needing exact PDF body extraction remains deferred where D0 confidence is not high.
- No `NOT_ENOUGH_EVIDENCE` promotion actions were attempted.

## 8) F/G/H deferred note (Batch 2 blocked)
- F/G/H family and many untested statuses/sub-codes remain deferred.
- Batch 2 and Batch 2 rerun were blocked by frontend/visual-browser 502, with 0 tested statuses in those runs.
- This PR does not use blocked Batch 2 outputs as correction evidence.

## 9) Risks and guardrails
- No data patching without D0 high-confidence source-confirmed readiness.
- No legal/document additions inferred from non-authoritative summaries.
- No `verified=true` promotion unless explicitly source-confirmed for the exact metadata change.
- No `needsManualReview` removal unless explicitly authorized by source-confirmed readiness.
- No AI grounding, law grounding behavior, UI, or search logic changes.

## 10) Recommended future PR sequence
1. **PR D2a**: Patch newly source-confirmed sub-code items only (if/when D0-equivalent readiness exists).
2. **PR D3**: Manual-grounding expansion after stable source crosswalk.
3. **PR E**: AI grounding fallback safety.
4. **PR F**: Regression/smoke tests.
5. **PR G**: Batch 2 interactive audit rerun for F/G/H and currently untested statuses.

## Machine-readable JSON action log
```json
[
  {
    "issueId": "PDA-007",
    "code": "C-3",
    "subCode": "C-3-*",
    "actionTaken": "REVIEWED_NOT_PATCHED",
    "readinessStatusFromD0": "NEEDS_MANUAL_REVIEW",
    "confidence": "low",
    "filesChanged": [],
    "sourceBasis": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "pp.27-28 (locator)",
        "summary": "Sub-code-level mapping remains incomplete."
      }
    ],
    "notes": "Deferred to D2a after explicit per-sub-code source confirmation."
  },
  {
    "issueId": "PDA-009",
    "code": "D-4",
    "subCode": "D-4-2K",
    "actionTaken": "REVIEWED_NOT_PATCHED",
    "readinessStatusFromD0": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "filesChanged": [],
    "sourceBasis": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.90; pp.83-101 (locator)",
        "summary": "Range too broad for safe D-4 vs D-4-2K correction."
      }
    ],
    "notes": "Requires follow-up sub-code review before data patch."
  },
  {
    "issueId": "PDA-010",
    "code": "D-10",
    "subCode": null,
    "actionTaken": "REVIEWED_NOT_PATCHED",
    "readinessStatusFromD0": "SOURCE_LOCATED_BUT_AMBIGUOUS",
    "confidence": "medium",
    "filesChanged": [],
    "sourceBasis": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.155 (locator)",
        "summary": "Anchor exists but not text-level confirmed for direct patch."
      }
    ],
    "notes": "Keep deferred until subsection-level confirmation."
  },
  {
    "issueId": "PDA-011",
    "code": "E-7",
    "subCode": "E-7-4",
    "actionTaken": "REVIEWED_NOT_PATCHED",
    "readinessStatusFromD0": "NEEDS_MANUAL_REVIEW",
    "confidence": "low",
    "filesChanged": [],
    "sourceBasis": [
      {
        "file": "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
        "pageOrSection": "p.226; pp.212-323 (locator)",
        "summary": "E-7 versus E-7-4 distinction remains unresolved."
      }
    ],
    "notes": "Defer to D3-oriented source partition before patching."
  }
]
```
