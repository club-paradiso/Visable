# Detail-Code Alias and Document UI Fix - 2026.5

## Scope

This patch fixes two related runtime UX/data issues:

1. Detail-code searches such as `F-1-6` should resolve to existing parent/scenario records instead of failing as missing top-level records.
2. Result cards should not show a duplicate top-level `필수서류` summary when the detailed `구비서류` section is already rendered.

## Source/API status

Repository audit indicates law/public-data API integration is declared-only or runtime-inactive, so this patch does not fetch or generate external legal content.

## Manual files checked in repository

- `docs/source-manuals/2026-05/stay_manual_2026_05.pdf`: present
- `docs/source-manuals/2026-05/visa_manual_2026_05.pdf`: present
- `docs/source-manuals/2026-05/체류민원 안내매뉴얼_260521.pdf`: not found
- `docs/source-manuals/2026-05/사증발급 안내매뉴얼_260521.pdf`: not found

## Search alias changes

- Added alias entries: 0
- Records touched: 0

### Watched-code diagnostics

- `F-1-6`
  - found_as_detail_token: `True`
  - source_records: F-1, SCN-4
  - records_with_alias_or_code: F-1, SCN-4
- `E-7-4`
  - found_as_detail_token: `True`
  - source_records: E-7
  - records_with_alias_or_code: E-7
- `F-2-7`
  - found_as_detail_token: `True`
  - source_records: F-2, F-5
  - records_with_alias_or_code: F-2, F-5
- `D-10-T`
  - found_as_detail_token: `True`
  - source_records: D-10
  - records_with_alias_or_code: D-10
- `F-2-R`
  - found_as_detail_token: `False`
  - source_records: none
  - records_with_alias_or_code: none
- `F-4-R`
  - found_as_detail_token: `False`
  - source_records: none
  - records_with_alias_or_code: none
- `F-5-T`
  - found_as_detail_token: `True`
  - source_records: F-5
  - records_with_alias_or_code: F-5

## Index/UI changes

- Added a detail-code resolver shim to `index.html`.
- Added a document-section unification shim to hide duplicate `필수서류` summary sections when `구비서류` is present.
- Added CSS for `.doc-summary-duplicate-collapsed`.

## Guardrails

- No new visa/status records.
- No record deletion.
- No legal requirement text changes.
- No `verified=true` promotion.
- No backend changes.
- No external legal API call.

## Manual QA

- [ ] Search `F-1-6`.
- [ ] Search `f-1-6`.
- [ ] Search `F-1`.
- [ ] Search `E-7-4`.
- [ ] Search `F-2-7`.
- [ ] Search `제주 무사증`.
- [ ] Confirm autocomplete click and Enter search produce a result.
- [ ] Open a result card with document sections.
- [ ] Confirm duplicate top-level `필수서류` summary is hidden when `구비서류` exists.
- [ ] Confirm `구비서류` tabs still render.

