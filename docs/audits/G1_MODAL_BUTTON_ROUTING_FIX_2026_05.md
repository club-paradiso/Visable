# G1_MODAL_BUTTON_ROUTING_FIX_2026_05

Date: 2026-05-27

## Issue addressed

- `PDA-B2R2-001`

## Source audit reference

- `docs/audits/BATCH_2_FINAL_INTERACTIVE_RERUN_NORMALIZED_2026_05.md`
- Issue #199: Batch 2 final audit follow-ups and safety gates.

## Repository path validation

The normalized Batch 2 final audit marked the original audit `likelyFiles` as untrusted. PR G2 validated the active repository shape before patching:

- Active UI implementation: `index.html`
- `frontend/data/g-series.json`: not present
- `frontend/components/StayCard.vue`: not present
- `frontend/components/DocsModal.vue`: not present

No guessed frontend component or data path was created.

## Files changed

- `index.html`
- `docs/audits/G1_MODAL_BUTTON_ROUTING_FIX_2026_05.md`

## Root cause

The G-1 result card renders the generic document action row from `index.html`. The change-of-status action opened `openDocModal(..., "change")`. When no structured `statusChange` document list existed, that modal reused extension/new-application document lists as a conservative fallback.

That fallback was too easy to misread as actual G-1 change-of-status content. For G-1, the safer behavior is to open the modal with a clear unavailable-data notice instead of showing extension content.

The FAQ and result-copy handlers also had silent-return paths when a record or FAQ/copy payload was missing. PR G2 hardens those paths so visible controls show either content, confirmation, or a clear warning.

## Behavior before

- G-1 new/visa document button opened the normal document modal.
- G-1 extension document button opened extension content.
- G-1 change-of-status document button could show fallback extension/new content when structured change data was missing.
- FAQ handler returned silently when FAQ data was absent.
- Result-copy handler returned silently when the record was not found and reported success after fallback copy without checking whether the fallback succeeded.

## Behavior after

- G-1 new/visa document button still opens the normal new/visa document modal.
- G-1 extension document button still opens extension content.
- G-1 change-of-status document button opens the document modal with this safe notice when structured change data is missing:
  - `이 항목의 자격 변경 서류는 아직 구조화 데이터에 충분히 정리되어 있지 않습니다. 최신 체류민원 안내매뉴얼 또는 관할 출입국·외국인관서를 확인하세요.`
- FAQ opens the FAQ modal when FAQ content exists, and shows an unavailable-data notice if content is missing.
- Result-copy copies the result summary when possible, shows a success toast on confirmed copy, and shows a warning if the record/content is unavailable or copy fails.

## Data/legal non-goals

- No G-1 document-list corrections.
- No F/G/H data patches.
- No required-document changes.
- No legal citations added to production data.
- No `verified=true` promotion.
- No `needsManualReview` removal.
- No law-grounding enablement.
- No AI grounding changes.
- No search-ranking changes.
- No UI redesign.

## Manual QA checklist

- [ ] Search G-1.
- [ ] Open the G-1 card.
- [ ] Click new/visa document button.
- [ ] Click extension document button.
- [ ] Click change-of-status document button.
- [ ] Click FAQ button.
- [ ] Click result-copy button.
- [ ] Confirm each button either opens correct content or a clear safe unavailable-data notice.
- [ ] Confirm no button silently does nothing.
- [ ] Confirm change-of-status does not incorrectly masquerade as extension content unless clearly labelled as unavailable/fallback.
- [ ] Confirm modal close still works.
- [ ] Search F-6 and confirm its document buttons still work.
- [ ] Search H-1 and confirm its document buttons still work.
- [ ] Confirm no document/legal data was changed.

## Deferred work

- `D3C-Prep`: build F/G/H official manual source crosswalk.
- `PR-G-FOLLOWUP` / `D3C`: patch G-1 documents only after official source crosswalk.
- H-series follow-up: audit H-2 and H-1 details.
- Remaining coverage audit: C-3, D/E sub-codes, B-2-2/Jeju, scenario/helper records.
- Metadata PR: `verified` / `needsManualReview` updates only after strict source-confirmed criteria are met.
