# Document Term and Fee Display Fix

## Issue

Mobile visual QA on `F-6` showed inconsistent document terminology and missing fee amount display.

## Change

- Normalized common document terms in `visa_data.json`.
- Synced `backend/data/visas.json`.
- Synced scenario/help shadow copies for resolver parity.
- Added fee-display metadata under `feeInfo.paradisoDefault202605`.
- Added an `index.html` UI shim to show procedure-specific fee notices and normalize visible document labels.

## Manual QA

- [ ] Search `F-6`.
- [ ] Check `외국인등록`.
- [ ] Check `체류기간 연장`.
- [ ] Check `체류자격 변경`.
- [ ] Confirm fee amounts are visible.
- [ ] Confirm document terminology is consistent.
- [ ] Confirm prior detail-code searches still work.
