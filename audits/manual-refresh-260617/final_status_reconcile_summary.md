# 2026-06-17 Status Manual Reconcile Summary

## Scope

- Reviewed all 42 JSON files under `backend/data/visa_authoring/statuses/`.
- Used the attached 2026-06-17 manuals through the repo-extracted full text:
  - `docs/source-manuals/2026-06-17/extracted/full_text/stay_manual_260617.txt`
  - `docs/source-manuals/2026-06-17/extracted/full_text/visa_issue_manual_260617.txt`
- No web sources were used.

## Artifacts

- `phase0_repository_audit.md`: repository/data-pipeline inspection.
- `status_source_map.json`: per-status source ranges for stay and visa manuals.
- `batch_01_all_status_source_metadata_*`: all-status manualRef/source-status cleanup.
- `batch_02_targeted_content_cleanup_*`: A-series and special-track content cleanup.
- `batch_03_manual_review_reason_*`: explicit reasons for retained review flags.
- `batch_04_subcode_source_gap_correction_*`: removed broad parent fallback refs from 32 subcodes so source gaps remain honest.
- `batch_05_variant_review_flag_restore_*`: restored variant-level `needsManualReview: true` with precise reasons.

## Changes Made

- Replaced human-editable TOC-only `p. 2` manual refs with substantive source ranges from `status_source_map.json`.
- Assigned procedure manual refs by procedure type:
  - `visaIssuance` uses visa manual ranges.
  - stay-side procedures use stay manual ranges.
- Updated all status-level source metadata to the 2026-06-17 manuals while leaving `verified: false`.
- Added precise `reviewReason` / `manualReviewReason` text where review flags remain true.
- Cleaned targeted content:
  - `A-1` extension summary no longer includes adjacent re-entry text.
  - `A-1`, `A-2`, and `A-3` registration documents are split into structured items.
  - `A-3` Fulbright extension documents are structured from the A-3 section.
  - `D-4-1`, `E-8`, `F-6`, `K-STAR`, and `REGION-S` replace vague "manual check needed" placeholders with exact unresolved reasons.
- Regenerated `visa_data.json` and `backend/data/visas.json` using `scripts/visa/build_visa_data.py`.

## Validation

Passed:

- `scripts/visa/validate_visa_authoring.py`
- `scripts/visa/build_visa_data.py --check`
- `scripts/sync_visa_data.py --check`
- `scripts/visa/check_manual_refresh_coverage.py`
- `scripts/visa/check_subcode_parity.py --strict`
- `scripts/visa/check_260617_subcode_inventory_coverage.py`
- `scripts/check_required_documents_coverage.py`
- `scripts/audit_duplicate_render_content.py --check`
- `scripts/check_visa_text_corruption.py` through repo validation
- i18n, employment-helper, F-4 hub, subcode-modal, route-guide, visa-issuance, dummy-text, and branding checks from `scripts/check_repo.sh`
- `backend/tests/test_paradiso_backend.py` — 251 tests OK
- `backend/tests/test_e7_workplace_change_law_grounding.py` — 26 tests OK
- `scripts/evaluate_paradiso_ai_golden_questions.py` — 50/50 passed

Notes:

- `npm run validate` was interrupted at its broad `git diff --check` step because broad git diff operations hang in this worktree. The same check was replaced with a direct whitespace/conflict-marker scan over the touched files, which passed.
- `scripts/visa/diff_visa_data.py --git` exited non-zero because it detected expected runtime-visible changes against `HEAD`; those differences are the purpose of this branch and were reviewed.
- Raw string scans still find `2026.5` / `2026-06-01` in protected `_generated.compat` and runtime compatibility/audit fields. These are historical compatibility fields generated/preserved by the authoring pipeline, and repo validation still requires at least `manualRequiredDocAudit.manualVersion == "2026.5"`. Human-editable source refs, review notes, and manual status metadata were reconciled to 2026-06-17.
