# SOURCE STATUS I18N HOTFIX (PR C1, 2026-05)

## Codex comment addressed
- **P2 Badge Add non-Korean translations for new source-status keys**
- `renderSourceEvidencePanel` introduced new source-status keys in PR C; non-Korean dictionaries were falling back to Korean for those keys.

## Keys added in non-Korean dictionaries
- `sourceStructuredData`
- `sourceManualConfirmed`
- `sourceManualPending`
- `sourceNeedLinking`
- `sourceProvisional`
- `sourceVerifiedNote`
- `sourcePendingReviewNote`
- `sourceNeedLinkingNote`
- `sourceUnverifiedNote`
- `sourceProvisionalNote`

## Languages updated
- `zhHant`
- `ja`
- `fr`
- `id`
- `ru`
- (`zh` already updated in PR C; retained)

## Files changed
- `index.html`
- `docs/audits/SOURCE_STATUS_I18N_HOTFIX_2026_05.md`

## What was NOT changed
- No source-status logic changes.
- No legal/admin/manual content changes.
- No required-document list changes.
- No AI/law grounding behavior changes.
- No edits to `visa_data.json`, `backend/data/visas.json`, or manual-grounding JSON.

## Validation performed
- Repository validation commands were run, including JSON parse/parity checks and `bash scripts/check_repo.sh`.
- Backend regression phase in `check_repo.sh` remained blocked by package-index/proxy restrictions; offline-safe syntax checks still passed.
