# Search Detail-Code and Document UI Fix

## Issue

- Exact detail-code queries such as `F-1-6` can fail because they are not always top-level `visa_data.json[].code` records.
- Result cards can show a duplicate top-level `필수서류` summary above the detailed `구비서류` tabbed section.

## Change

- Adds conservative `searchAliases` metadata to existing `visa_data.json` records.
- Adds a detail-code resolver shim in `index.html`.
- Adds a document-section unification shim in `index.html`.
- Keeps underlying document data intact while hiding the duplicate summary in the UI.

## Guardrails

- No backend changes.
- No new visa/status records.
- No record deletion.
- No legal requirement text changes.
- No `verified=true` promotion.
- No external legal API call.

## Manual QA

- [ ] Search `F-1-6`.
- [ ] Search `f-1-6`.
- [ ] Search `F-1`.
- [ ] Search `E-7-4`.
- [ ] Search `F-2-7`.
- [ ] Search `제주 무사증`.
- [ ] Open a result card with document sections.
- [ ] Confirm duplicate top-level `필수서류` summary is hidden when `구비서류` exists.
- [ ] Confirm `구비서류` tabs still render.
