# 2026-06-17 Manual Refresh Website QA

## Scope

- Reviewed all 42 canonical authoring status files under `backend/data/visa_authoring/statuses/`.
- Classified all 217 manual-derived code-like items from the 2026-06-17 extracted manuals.
- Handled 154 active subcodes, 37 parent statuses, 22 special tracks, 1 policy/multiple-entry code, and 3 abolished codes.
- Rebuilt generated `visa_data.json` and `backend/data/visas.json` from authoring data.

## Source Artifacts

- Source manual version/date: 2026.6 / 2026-06-17.
- Extracted source text is committed under `docs/source-manuals/2026-06-17/extracted/`.
- Inventory: `docs/data/2026_06_17_manual_code_inventory.json`.
- Coverage report: `docs/data/2026_06_17_subcode_coverage_report.json`.
- Review matrix: `docs/data/2026_06_17_status_review_matrix.json`.
- Full audit: `docs/data/2026_06_17_full_manual_refresh_audit.json`.

## Code Handling

- Active subcodes handled: 154.
- Special tracks handled: 22, including Top-Tier, regional, K-STAR, and suffix tracks such as `D-4-2K`, `D-8-4S`, `E-7-S1`, `E-7-S2`, `F-2-7S`, `F-5-S1`, and `F-5-S2`.
- Policy/multiple-entry code handled: `C-3-91`, retained as searchable and marked for manual review rather than ordinary active-subcode treatment.
- Abolished codes handled:
  - `C-3-11`
  - `F-1-72`
  - `F-2-6`
- Abolished codes remain searchable only with non-active status metadata and warning/status notes.

## Status Changes

- Status files changed: 42.
- Status files unchanged: 0.
- Source-ref/review-flag gaps resolved: 112 before, 0 after.
- Generated `subcodes`/`subCodes` parity issues resolved: 27 before, 0 after.
- Stale source refs resolved: 42 statuses with stale refs before evidence pass, 0 stale refs after implementation.

## Website-Facing Issues Addressed

- Exact-code search aliases were preserved or added for parent codes and canonical subcodes.
- Canonical `subcodes` and legacy `subCodes` now emit matching code sets.
- Abolished/deprecated codes are no longer represented as ordinary active subcodes.
- Source metadata now points to 2026-06-17 extracted manuals instead of stale 2026.5 / 2026-06-01 references.
- Procedure refs remain conservatively marked `needsManualReview: true`.
- No `DATA_MISSING` summary regression was introduced by the refresh.

## Validation Summary

- `python3 scripts/visa/validate_visa_authoring.py`: pass.
- `python3 scripts/visa/build_visa_data.py`: pass; generated 42 records and synced backend mirror.
- `python3 scripts/visa/check_260617_subcode_inventory_coverage.py`: pass.
- `python3 scripts/visa/check_manual_refresh_coverage.py`: pass.
- `python3 scripts/visa/check_subcode_parity.py`: pass.
- `python3 scripts/check_required_documents_coverage.py`: pass.
- `node scripts/smoke_ai_payload.js`: pass.
- `node scripts/check_exact_code_search.js`: pass.
- `node scripts/check_static_visa_result_cards.js`: pass.
- Custom all-status/subcode data smoke: pass for 42 parents, 216 canonical subcode codes, and the explicit seed set.

## Known Limitations

- All statuses remain conservatively marked `needsManualReview` because the refresh normalized source metadata and code coverage, but did not certify every legal/document/procedure wording claim as fully verified.
- `python3 scripts/check_scenario_help_records.py` and `python3 scripts/check_record_store_union_parity.py --simulate-e4-removal` fail because scenario/help shadow records are index/content-coupled to the prior generated `visa_data.json`; those helper shadows need a separate refresh after generated source metadata and subcode fields changed.
- `bash scripts/check_repo.sh` was stopped at the long-running `git diff --check` step; targeted syntax, JSON, data, frontend static, and smoke checks above were run instead.

## Follow-Up Recommendations

- Refresh `data/scenario_help_records.json` shadow records against the rebuilt generated data in a follow-up or dedicated commit.
- Perform human legal review of high-impact procedures/documents before clearing `needsManualReview`.
- Consider a smaller CI-safe diff/whitespace check path for large extracted manual/evidence artifacts.
