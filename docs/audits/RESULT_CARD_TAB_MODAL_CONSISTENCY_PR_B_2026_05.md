# RESULT CARD TAB/MODAL CONSISTENCY — PR B (2026-05)

## Scope
- PR type: UI behavior consistency fix (result card / modal)
- Primary target: `index.html`
- Related baseline audits:
  - `docs/audits/AGENT_MODE_STAY_STATUS_UI_SOURCE_AUDIT_NORMALIZED_2026_05.md`
  - `docs/audits/POST_PR_190_MAIN_STATE_AUDIT.md`

## Issue IDs addressed
- PDA-008: tabs require double click or intermittently fail to switch content
- PDA-012: modal close button clickability/hit target weakness
- PDA-013: empty structured-tab message vs bottom modal affordance mismatch
- PDA-017: sub-code “더 보기” interaction can cause user context loss (scroll/focus)

## Files changed
- `index.html`
- `docs/audits/RESULT_CARD_TAB_MODAL_CONSISTENCY_PR_B_2026_05.md`

## Before / After behavior

### 1) Document tabs (single click)
- Before: tab switching depended on inline section toggling logic that could be brittle during repeated interactions.
- After: tab activation is centralized in `activateDocsTab(section, targetKey)` and consistently updates:
  - active tab class
  - `aria-selected`
  - active panel visibility
  - section-level active tab marker (`data-active-docs-tab`)

### 2) Modal close button hit target
- Before: base `.modal-close` style allowed smaller effective click area depending on cascade/context.
- After: base close control now guarantees minimum interactive target (`min-width/min-height: 40px`) and click reliability helpers (`touch-action: manipulation`, `z-index: 2`) while preserving existing keyboard/focus behavior and ESC flow.

### 3) Empty-tab message consistency
- Before: empty tab wording emphasized “not registered” and could read as hard absence even when bottom modal/manual channels were still available.
- After: empty notice wording is aligned to safe guidance without adding/changing legal content:
  - "이 항목의 구조화 데이터는 아직 정리 중입니다. 하단 서류 모달 또는 공식 매뉴얼 확인이 필요합니다."

### 4) Sub-code “더 보기” context retention
- Before: expanding sub-code detail blocks could feel like a jump and reduce context continuity.
- After: opening `.manual-subcode-more` details now re-anchors view to the summary row (`scrollIntoView`, nearest block) to preserve local context and keep downstream action controls reachable.

## What was NOT changed
- No edits to legal/admin/manual source content.
- No required-document list corrections or additions.
- No changes to `visa_data.json`.
- No changes to `backend/data/visas.json`.
- No manual-grounding JSON changes.
- No AI grounding or law-grounding behavior changes.
- No search ranking logic changes.
- No F/G/H coverage claims or data patches.

## Manual QA checklist
- [ ] Open/search A-1 and click all document tabs once.
- [ ] Open/search B-2 and click all document tabs once.
- [ ] Open/search C-3 and test sub-code "더 보기".
- [ ] Open/search D-2 and click all document tabs once.
- [ ] Open/search D-4 and test sub-code expansion.
- [ ] Open/search D-10 and click document buttons.
- [ ] Open/search E-7 and test sub-code expansion.
- [ ] Open/search F-6 if available.
- [ ] Open and close each modal using the close button.
- [ ] Press ESC to close modal if supported.
- [ ] Confirm no document content was added, removed, or legally changed.
- [ ] Confirm broad search behavior still works.

## Deferred / remaining issues
- PR C: source labels and warning consistency.
- PR D0: manual-law data correction readiness audit.
- PR E: AI grounding fallback and foreign-system leakage prevention.
- PR F: regression/smoke tests.
- PR G: Batch 2 interactive audit for F/G/H and untested statuses once frontend access is reliable.
