# SOURCE WARNING LABEL CONSISTENCY — PR C (2026-05)

## Issue IDs addressed
- PDA-016
- Related source-warning consistency concerns from normalized audit (UI label/state clarity)

## Files changed
- `index.html`
- `docs/audits/SOURCE_WARNING_LABEL_CONSISTENCY_PR_C_2026_05.md`

## Label states before/after
- Manual-backed state now explicitly labeled as **공식 매뉴얼 확인됨** (EN: Manual-backed) only when `verified===true && needsManualReview===false`.
- Pending review state now explicitly labeled as **매뉴얼 검토 필요** (EN: Manual review needed) when `needsManualReview===true`.
- Local structured-catalog baseline badge wording changed to **구조화 데이터 기준** (EN: Structured-data guidance).
- Source clue but incomplete linkage state exposed as **출처 확인 필요** / **Source linkage needed** when page/source hints exist but item-level linkage is incomplete.
- No structured-document data message now uses explicit **구조화 서류 데이터 없음** warning wording in document-tab empty notices.
- Provisional state label/warning added as **준용/임시 안내** / **Provisional guidance** when note text indicates 준용 context.

## Metadata fields used (read-only)
- `sourceManualStatus.verified`
- `sourceManualStatus.needsManualReview`
- `manualDomains` / inferred manual domain flags
- `manualRefs.pageRange|page|section` as source-hint signals
- status note/procedure note text for provisional(준용) hinting

## What was NOT changed
- No required-document list items were added/removed/edited.
- No legal/manual/admin content was edited.
- No `verified=true` promotions were made.
- No `needsManualReview` flags were removed.
- No AI grounding behavior or law-grounding behavior changes.
- No search ranking changes.
- No F/G/H data coverage patches.
- No changes to `visa_data.json`, `backend/data/visas.json`, or manual-grounding JSON.

## Manual QA checklist
- [ ] Open/search A-1 and inspect source/warning labels.
- [ ] Open/search B-2 and inspect empty document/source warnings.
- [ ] Open/search C-3 and inspect page/source labels.
- [ ] Open/search D-2 and inspect manual-backed or local-catalog labels.
- [ ] Open/search D-4 and inspect sub-code/source labels.
- [ ] Open/search D-10 and inspect provisional/준용 or pending-review labels.
- [ ] Open/search E-7 and inspect source labels.
- [ ] Open/search F-6 if available and inspect pending-review labels.
- [ ] Open AI page/modal if applicable and inspect AI warning text.
- [ ] Confirm no document list items changed.
- [ ] Confirm no `verified` or `needsManualReview` metadata changed.
- [ ] Confirm source warnings are clearer and do not overclaim official status.

## Deferred work
- PR D0: manual-law data correction readiness audit.
- PR E: AI grounding fallback and foreign-system leakage prevention.
- PR F: regression/smoke tests.
- PR G: Batch 2 interactive audit for F/G/H and untested statuses once frontend access is reliable.
