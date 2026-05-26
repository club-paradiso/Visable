# SEARCH_RESULT_PRECISION_PR_A_2026_05

## Issue IDs addressed
- PDA-003
- PDA-023

## Files changed
- `index.html`
- `docs/audits/SEARCH_RESULT_PRECISION_PR_A_2026_05.md`

## Search behavior before / after
- **Before:** single-token code searches could still include broad keyword spillover, so exact-code intent (for example `A-1`) could surface unrelated/noisy cards.
- **After:** code-like single-token queries now use exact-rank-first behavior (top-level code → alias/searchAlias → subcode/sub-alias), and if exact matches exist they are isolated ahead of broad text matches.

## Exact-code rules improved
- Normalize code-like query input safely:
  - trim + uppercase
  - compact whitespace/underscore variants
  - safe no-hyphen normalization such as `D2` → `D-2`, `F6` → `F-6`, `E7` → `E-7`, `H2` → `H-2`
  - `KETA` normalization to `K-ETA`
- Treat canonical forms such as `A-1`, `D-4-2K`, `E-7-4`, `F-1-6`, `F-6-1` as code-like.
- For code-like single-token searches:
  - exact top-level code match ranks highest,
  - then exact subcode ownership,
  - then exact status-record alias/searchAlias,
  - then exact subcode alias/searchAlias,
  - then exact helper/scenario alias/searchAlias,
  - broad keyword matches are only fallback when no exact match exists.
- Helper/scenario aliases are preserved, but they no longer outrank a status card that carries the same exact code-like alias such as `F-1-6`.

## Recommended chip behavior
- No chip list was deleted or redesigned.
- Broad discovery behavior remains intentionally available.
- Ranking improvements in the shared search path are used so chip-triggered searches still discover broadly while exact-code searches stay precise.
- Existing exact-code chips such as `E-7`, `F-6`, and `F-5` continue to use the shared exact-code ranking path.
- No new legal categories/tags were invented in this PR.

## Explicit non-changes
- No changes to `visa_data.json` or `backend/data/visas.json`.
- No legal/admin/manual-source content changes.
- No edits to required-document lists, fees, deadlines, eligibility, or citations.
- No changes to `verified`, `needsManualReview`, or manual grounding metadata.
- No AI grounding behavior changes.
- No modal/tab/card/document-section redesign.
- No F/G/H data coverage corrections (blocked for separate audit rerun scope).

## Manual QA checklist
- [ ] Search `A-1`; confirm unrelated K-ETA does not appear as a top/noisy result.
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
- [ ] Search Korean keywords: `유학`, `구직`, `특정활동`, `방문동거`, `결혼이민`, `관광`, `재외동포`, `영주`, `방문취업`.
- [ ] Click existing recommended chips and confirm broad discovery still works while exact-code search remains precise.

## Deferred work
- PR B: UI tab/modal consistency.
- PR C: source labels and warning consistency.
- PR D: verified data corrections after manual-law source checks.
- PR E: AI grounding fallback and foreign-system leakage prevention.
- PR F: regression/smoke tests.
- PR G: Batch 2 rerun audit for F/G/H and untested statuses.
