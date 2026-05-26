# BATCH 2 FINAL INTERACTIVE RERUN PROMPT (2026-05)

Date (UTC): 2026-05-26  
Purpose: Final interactive rerun readiness for F/G/H and previously untested statuses.

## Critical reminder
- Prior Batch 2 and Batch 2 rerun runs were blocked and tested **0 statuses**.
- Those blocked outputs are **not valid coverage evidence** for F/G/H or subcode completion.

## Scope targets
- F-1 to F-6
- F-1-6
- F-6-1 / F-6-2 / F-6-3
- G-1
- H-1 / H-2
- C-3 subcodes
- D-2 / D-4 / D-10 subcodes
- E-7 / E-7-4 subcodes
- B-2-2 / 제주 무사증 / regional-special entries
- scenario/helper records linked statuses

## GO/NO-GO preflight gate
Proceed only if all checks pass in **interactive visual browser**:
1. Deployed frontend page loads (no gateway/proxy fallback page).
2. Search input is visible and usable.
3. Search can execute and render results.
4. Result card/detail can be opened.
5. Tabs/buttons can be clicked and state changes are visible.
6. Modal open/close works.
7. AI entry point can be loaded and interacted with.

### NO-GO conditions
- Only raw/static HTML retrieval is possible.
- Visual browser cannot interact with controls.
- Proxy/gateway page prevents normal app use.

If NO-GO: stop test, record environment blocker, and output zero-coverage result.

## Issue ID namespace for this rerun
Use: `PDA-B2R2-001` onward.

## Required output schema
1. Coverage table
2. Code-by-code audit findings
3. Button/control audit
4. AI audit
5. Source mismatch notes
6. Machine-readable JSON issue list

### Coverage table minimum columns
- code
- subCode
- tested (true/false)
- pass/fail/block
- evidence (screenshot/log reference)
- notes

### JSON issue list schema
```json
[
  {
    "issueId": "PDA-B2R2-001",
    "code": "F-6",
    "subCode": "F-6-1",
    "area": "result_card|tabs|modal|ai",
    "status": "PASS|FAIL|BLOCKED",
    "severity": "P1|P2|P3",
    "evidence": ["screenshot_or_log_ref"],
    "sourceMismatch": false,
    "notes": ""
  }
]
```

## Execution checklist
1. Run preflight GO/NO-GO checks.
2. If GO, execute code/subcode test matrix in deterministic order.
3. Capture interactive evidence for every tested status.
4. Mark untested targets explicitly as `BLOCKED` only when genuinely blocked.
5. Produce markdown report + JSON issue list.
6. Do not claim full completion if any target remains untested.
