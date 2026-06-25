# PDF Refresh Validation Report

## Commands Run
- `/Users/seonjaekim/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/visa/extract_2026_pdf_manuals.py`
- `python3 scripts/visa/extract_manual_status_inventory.py`
- `python3 scripts/check_source_grounding_metadata.py`
- `python3 scripts/check_source_updates.py --local-only`
- `python3 scripts/visa/validate_visa_authoring.py`
- `python3 scripts/visa/build_visa_data.py --check`
- `python3 scripts/check_visa_data_domain_classification.py`
- `python3 scripts/sync_visa_data.py --check`
- `python3 backend/tests/test_paradiso_backend.py`
- `python3 backend/tests/test_scenario_procedure_variants.py`
- `python3 backend/tests/test_structured_requirements.py`
- `python3 backend/tests/test_source_grounding_metadata_schema.py`
- `node scripts/check_ai_shell_semantics.js`
- `node scripts/check_static_visa_result_cards.js`
- `node scripts/check_waymaker_navigator.mjs`
- `node scripts/check_waymaker_navigator_dom.mjs`
- `node scripts/check_i18n.js`
- `node scripts/smoke_static_i18n.mjs`
- `python3 scripts/populate_scenario_procedure_variants_2026_05.py --check`
- `python3 scripts/populate_scenario_procedure_variants_batch2_2026_05.py --check`
- `python3 scripts/populate_hard_case_scenario_procedure_variants_2026_05.py --check`
- `python3 scripts/populate_remaining_complex_subtype_scenario_variants_2026_05.py --check`
- `git diff --check`
- `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh`

## Result
- Repository validation passed.
- `scripts/check_repo.sh` passed with `ALLOW_BACKEND_TEST_SKIP=1`.
- `scripts/check_source_manuals.py` emitted warnings that `pdfinfo` was not found on shell PATH during the full check, then validated manifest registration. Page counts were separately verified with the Codex bundled Poppler `pdfinfo`.
- `node scripts/check_waymaker_navigator_dom.mjs` skipped DOM smoke because local `jsdom` was not installed; non-DOM Waymaker checks passed.
- System Python did not have `pytest`; unittest entry points were run directly.

## Warnings And Non-Blocking Notes
- `check_i18n` reported reference-only glossary terms without docIds links as visibility warnings; schema and Unicode/credential scans passed.
- Backend tests emitted existing Pydantic protected-namespace warnings for model-prefixed fields.
- Golden eval was skipped by `check_repo.sh` because backend dependency bootstrap was allowed to skip.

## Final Validation Assessment
- PASS: PDF source extraction.
- PASS: source registry/manifest/schema parity.
- PASS: authoring schema validation.
- PASS: generated data sync.
- PASS: backend Waymaker/source-grounding tests.
- PASS: scenario variant and complex-status checks.
- PASS: static UI/i18n checks.
- PARTIAL: browser screenshot QA was not available in this checkout.

