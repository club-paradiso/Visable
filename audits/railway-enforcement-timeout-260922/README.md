# Railway live smoke — enforcement AI prediction timeout (2026-09-22)

## What failed

`Railway Live Smoke` has failed on every push to `main` since run #46
(2026-09-10). The failing assertion is always the same one, and it is not a
provider outage:

| run | commit | `/api/enforcement/analyze` | prediction | provider probe |
| --- | --- | --- | --- | --- |
| #46 | `f3d5c4a` | HTTP 200, 12,781 ms | `UNAVAILABLE` | `enforcement_total_timeout` ×2 |
| #50 | `d250769` | HTTP 200, 12,775 ms | `UNAVAILABLE` | `enforcement_total_timeout` ×2 |
| #51 | `6577450` | HTTP 200, 12,698 ms | `UNAVAILABLE` | contract OK in ~3 s (`openai/gpt-oss-20b`) |

Everything else in the smoke is green on all three runs: backend health, Open
Law credential and live search, and the deterministic legal baseline
(`AVAILABLE`, 2,000,000 KRW on the synthetic D-2 fixture). The build fails only
because the AI half of the analysis degraded to `UNAVAILABLE`.

Run #51 is the decisive one. The live analysis produced no prediction, and
seconds later — same deployment, same model policy, same synthetic case — the
standalone provider probe produced a valid structured prediction in about three
seconds. The provider was healthy while the user-facing path gave up.

## Root cause

`_enforcement_ai_provider` bounded the model chain by **wrapping** it:

```python
return await asyncio.wait_for(
    _openrouter_complete_with_candidates(...),   # sizes itself from 45s
    timeout=ENFORCEMENT_AI_BUDGET_SECONDS,       # 8s default, 12s ceiling
)
```

The chain inside never saw that budget. It sized attempt #1 from
`OPENROUTER_CHAIN_BUDGET_SECONDS` (45 s) minus
`OPENROUTER_FALLBACK_RESERVE_SECONDS` (12 s) and bounded it by
`OPENROUTER_TIMEOUT_SECONDS` (60 s) — up to 33 seconds for one model. The
reserve that exists precisely to keep a fallback alive was also inert here: it
is only carved out while `remaining > 12 × 1.5 = 18 s`, and an enforcement
budget never reaches 18 s.

So the wrapper always fired part-way through the **first** candidate. The
coroutine was cancelled, the second candidate was never requested, and the
hard-coded timeout dict reported `attempted_models: []` with no cooldown
marking. One slow first response was enough to lose the whole prediction, which
is exactly the ~12.7 s → `UNAVAILABLE` signature above (≈0.5 s evidence
retrieval plus a 12 s budget spent entirely on one attempt).

## Fix

- `_openrouter_complete_with_candidates` accepts `chain_budget_seconds` and
  sizes the chain from it.
- `_openrouter_candidate_attempt_timeout` caps the fallback reserve at half the
  budget in force instead of at the flat 12 s global. A 12 s budget now runs
  ~6 s + ~6 s; the default 45 s chain is unchanged (`min(12, 22.5) = 12`, same
  gate, same 33 s first attempt).
- The outer `asyncio.wait_for` stays as a backstop only, at
  `ENFORCEMENT_AI_BUDGET_SECONDS + ENFORCEMENT_AI_BUDGET_GRACE_SECONDS`, so the
  chain normally returns its own metadata — attempted models, upstream
  statuses, per-model cooldown — instead of being cancelled blind.

Both env vars are now documented in `backend/README.md`. Production evidently
sets `ENFORCEMENT_AI_BUDGET_SECONDS` at or above the 12 s ceiling; the fix does
not change that value, it changes how the budget is spent.

## Coverage

`backend/tests/test_enforcement_latency_budget.py`:

- the enforcement budget reaches the chain as `chain_budget_seconds`;
- a hanging first candidate still leaves room for the alternate, which answers
  inside the budget;
- budget exhaustion reports which models were actually tried;
- the outer wrapper still backstops a chain that never returns;
- reserve arithmetic: 45 s → 33 s (unchanged), 12 s → 6 s, 8 s → 4 s.

`backend/tests/test_waymaker_production_truth_audit.py::test_buffered_candidate_chain_has_total_budget`
now asserts what the budget actually guarantees — the whole chain finishes
inside it and no single candidate outlives it — rather than that only one
candidate is ever tried.

## Not addressed here

Whether the first live request after a Railway deploy is systematically slower
than later ones is not established by these logs; the smoke only ever issues one
analysis per run. If red runs continue with both candidates now attempted and
reported, the next thing to read is the attempted-model list and upstream
statuses this change preserves.
