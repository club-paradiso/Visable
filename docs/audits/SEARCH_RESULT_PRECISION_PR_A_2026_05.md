# SEARCH_RESULT_PRECISION_PR_A_2026_05

## Scope
- PR A only: search/result availability and exact-code precision.
- Issues addressed: **PDA-003**, **PDA-023**.

## What changed
- Updated `index.html` search logic to normalize code-like queries (e.g., `D2` → `D-2`, `F6` → `F-6`) before scoring.
- Added explicit code-like query detection and exact-match rank handling for:
  - top-level visa/status codes,
  - aliases,
  - detail/sub-codes and their aliases.
- For code-like single-token queries, exact matches are now preferred and isolated when present, preventing broad keyword spillover (e.g., `A-1` no longer bringing unrelated high-noise cards due to generic overlap).
- For non-exact queries, broad discovery remains enabled and ranking still uses existing score behavior.

## What was not changed
- No changes to `visa_data.json` or `backend/data/visas.json`.
- No legal/manual/source-verification flag changes.
- No required-document, modal, tab, card design, or AI grounding changes.
- No backend law-grounding behavior changes.

## Manual QA checklist
- [ ] Search `A-1`; confirm unrelated `K-ETA` does not appear as a noisy top/extraneous result.
- [ ] Search `A-2`.
- [ ] Search `B-1`.
- [ ] Search `B-2`.
- [ ] Search `C-3`.
- [ ] Search `D-2`.
- [ ] Search `D2`.
- [ ] Search `D-4`.
- [ ] Search `D-4-2K`.
- [ ] Search `D-10`.
- [ ] Search `E-7`.
- [ ] Search `E-7-4`.
- [ ] Search `F-1`.
- [ ] Search `F-1-6`.
- [ ] Search `F-6`.
- [ ] Search `F-6-1`.
- [ ] Search `G-1`.
- [ ] Search `H-1`.
- [ ] Search `H-2`.
- [ ] Search Korean keywords: `유학`, `구직`, `특정활동`, `방문동거`, `결혼이민`, `관광`.
- [ ] Click recommendation chips (`관광`, `취업`, `유학`, `가족`, `재외동포` or current equivalents) and confirm broad discovery still works.
- [ ] Confirm exact-code searches remain precise while keyword exploration remains available.

## Deferred work
- PR B: UI tab/modal consistency.
- PR C: source labels and warning consistency.
- PR D: verified data corrections after manual-law source checks.
- PR E: AI grounding fallback and foreign-system leakage prevention.
- PR F: regression/smoke tests.
- PR G: second-pass audit coverage for F/G/H and untested statuses.
