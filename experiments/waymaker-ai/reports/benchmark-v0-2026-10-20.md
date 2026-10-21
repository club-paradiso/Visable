# Waymaker evaluation report

- Report schema: `waymaker-eval-report/0.1`; scoring digest `c83cb11009d746ba7c10e0c5b2e2737f4738f57beb5f6c103b51460e25dbfa1c`
- Command: `cd <repo>/experiments/waymaker-ai && <python3.11-venv>/bin/python -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 --baselines b1_python,b1_python_raw,b2_js,wlie,existing_law,mock_model --splits dev,test,adversarial_holdout --out reports/benchmark-v0-2026-10-20.json --markdown reports/benchmark-v0-2026-10-20.md --holdout-ledger reports/holdout-ledger.jsonl --holdout-post-hoc 'final integration re-scoring on the clean stage-A snapshot 1481605 (spec 06/07 decisions of 2026-10-20, align-bench revision-2 labels, WLIE blocked-layer fix, wlie baseline context_title, law-stack F9-F12); the blind-label audit of this pass changed no label and no code; adversarial_holdout first scored 2026-10-19 (ledger entries 1-2, benchmark digest db882bf2), so these are not first-look numbers'`
- Git commit: `1481605875ad93b83292a852adc6d30aa1afd6aa`
- Python 3.11.15, backend Python 3.11.15, Node v24.14.0
- Benchmark: `datasets/benchmark/v0` digest `2452851415eebc7a2b23edea7e281bc5645228f149c90feb1b1d614e5bd94ff3`; manifest verified; 0 invalid example(s) left out
- Label review of scored examples: {"machine_checked": 151, "unreviewed": 37}
- Backend for b1_python, b1_python_raw and existing_law: `<repo>` (the repo root); content sha256 `111031fcac67b07381f0963c23cf0dbe94630b318258d1e5f8f1553175fd7bd1` over 331 files; git commit `1481605875ad93b83292a852adc6d30aa1afd6aa`, `HEAD:backend` tree `d8c7f64940d43bac87bb9671c685ed9d079bdf11`
- Manifest `MANIFEST.json` sha256 `3656c2bd72c623833ce04a07ad6ae102a5fc42049053d63b51abadbde4cff0ba`
- Source bundle `law_go_kr_capture_2026_10_19` sha256 `a14bb6c0569e93bc4b367d96627fbca6f4ebffb1988e0884b974c91015ed7781`, provenance verified_web
- Source bundle `synthetic_adversarial` sha256 `d8f0845375fe3193a7db5f9476f23c2a44bddf0176bd439e02fdf45506962704`, provenance synthetic_fixture
- Source bundle `synthetic_core` sha256 `45a72bcd005cf9013ff27fbeeb6ac8d4ecdd7ad6e163d551b61ddb9dd44c9935`, provenance synthetic_fixture

> Labels are not human-verified unless the line above says so. Source bundles are synthetic fixtures or recorded captures; no live API was called. Gates are project hypotheses. No metric uses text similarity.

## Baselines

| baseline | kind | available | tasks | note |
|---|---|---|---|---|
| b1_python | deterministic | yes | entity_date_extraction, status_procedure_classification |  |
| b1_python_raw | deterministic | yes | status_procedure_classification |  |
| b2_js | deterministic | yes | entity_date_extraction, status_procedure_classification |  |
| wlie | deterministic | yes | citation_verification, temporal_version_selection |  |
| existing_law | deterministic | yes | citation_verification |  |
| mock_model | model | yes | abstention, entity_date_extraction, status_procedure_classification |  |

Cells: value (numerator/denominator, not-scorable items) [95% Wilson interval]. "not emitted" = the baseline cannot produce that field.

## Results: `dev`

| metric | b1_python | b1_python_raw | b2_js | wlie | existing_law | mock_model |
|---|---|---|---|---|---|---|
| abstention.forbidden_assertion_violations | – | – | – | – | – | 0 of 2 |
| abstention.required_issue_coverage | – | – | – | – | – | 0.000 (0/8) [0.000, 0.324] |
| abstention.withhold_accuracy | – | – | – | – | – | 1.000 (2/2) [0.342, 1.000] |
| abstention.withhold_precision | – | – | – | – | – | 1.000 (2/2) [0.342, 1.000] |
| abstention.withhold_recall | – | – | – | – | – | 1.000 (2/2) [0.342, 1.000] |
| citation.accepted_future_not_yet_effective | – | – | – | 0 of 0, 10 n/s | 0 of 0, 10 n/s | – |
| citation.accepted_source_outdated | – | – | – | 0 of 0, 10 n/s | 0 of 0, 10 n/s | – |
| citation.accepted_version_failures | – | – | – | 0 of 0, 10 n/s | 0 of 0, 10 n/s | – |
| citation.accepted_wrong_version | – | – | – | 0 of 0, 10 n/s | 0 of 0, 10 n/s | – |
| citation.false_absence_declarations | – | – | – | 0 of 0, 10 n/s | 0 of 0, 10 n/s | – |
| citation.forbidden_code_violations | – | – | – | 0 of 10 | 1 of 10 | – |
| citation.highest_layer_within_bound | – | – | – | n/a (0/0, 10 n/s) | n/a (0/0, 10 n/s) | – |
| citation.injection_flag_accuracy | – | – | – | n/a (0/0, 10 n/s) | n/a (0/0, 10 n/s) | – |
| citation.layer_agreement.L1_source_identity | – | – | – | 1.000 (10/10) [0.722, 1.000] | 0.600 (6/10) [0.313, 0.832] | – |
| citation.layer_agreement.L2_version_identity | – | – | – | 1.000 (10/10) [0.722, 1.000] | n/a (0/0, 10 n/s) | – |
| citation.layer_agreement.L3_citation_identity | – | – | – | 1.000 (10/10) [0.722, 1.000] | 1.000 (6/6, 4 n/s) [0.610, 1.000] | – |
| citation.layer_agreement.L4_text_correspondence | – | – | – | 1.000 (10/10) [0.722, 1.000] | n/a (0/0, 10 n/s) | – |
| citation.layer_agreement.L5_claim_support | – | – | – | 1.000 (10/10) [0.722, 1.000] | n/a (0/0, 10 n/s) | – |
| citation.layer_agreement.L7_conflict_uncertainty | – | – | – | 1.000 (10/10) [0.722, 1.000] | n/a (0/0, 10 n/s) | – |
| citation.overall_status_accuracy | – | – | – | 1.000 (10/10) [0.722, 1.000] | 0.000 (0/10) [0.000, 0.278] | – |
| citation.unlabelled_absence_codes | – | – | – | 0 of 10 | 2 of 10 | – |
| citation.unsupported_claim_acceptance_rate | – | – | – | 0.000 (0/1, 9 n/s) [0.000, 0.793] | 1.000 (1/1, 9 n/s) [0.207, 1.000] | – |
| citation.wrong_version_detection_rate | – | – | – | n/a (0/0, 10 n/s) | n/a (0/0, 10 n/s) | – |
| classification.clarification_precision | n/a (0/0) | – | 1.000 (1/1) [0.207, 1.000] | – | – | 1.000 (1/1) [0.207, 1.000] |
| classification.clarification_recall | 0.000 (0/1) [0.000, 0.793] | – | 1.000 (1/1) [0.207, 1.000] | – | – | 1.000 (1/1) [0.207, 1.000] |
| classification.current_status_accuracy | 0.333 (1/3, 21 n/s) [0.061, 0.792] | n/a (0/0, 24 n/s) | 0.667 (2/3, 21 n/s) [0.208, 0.939] | – | – | 0.000 (0/3, 21 n/s) [0.000, 0.561] |
| classification.hierarchy_violations | 11 of 24 | 0 of 24 | 0 of 24 | – | – | 0 of 24 |
| classification.non_code_token_respected | 0.000 (0/1, 23 n/s) [0.000, 0.793] | 1.000 (1/1, 23 n/s) [0.207, 1.000] | 0.000 (0/1, 23 n/s) [0.000, 0.793] | – | – | 1.000 (1/1, 23 n/s) [0.207, 1.000] |
| classification.procedure_coarse_accuracy | 0.368 (7/19, 5 n/s) [0.191, 0.590] | 0.316 (6/19, 5 n/s) [0.154, 0.540] | 0.789 (15/19, 5 n/s) [0.567, 0.915] | – | – | 0.000 (0/19, 5 n/s) [0.000, 0.168] |
| classification.procedure_fine_accuracy | not emitted | not emitted | 0.792 (19/24) [0.595, 0.908] | – | – | 0.000 (0/24) [0.000, 0.138] |
| classification.procedure_scope_violations | 0 of 24 | 0 of 24 | 0 of 24 | – | – | 0 of 24 |
| classification.status_exact_accuracy | 0.875 (21/24) [0.690, 0.957] | 0.417 (10/24) [0.245, 0.612] | 0.875 (21/24) [0.690, 0.957] | – | – | 0.083 (2/24) [0.023, 0.258] |
| classification.subcode_accuracy_no_subcode_expected | 1.000 (11/11) [0.741, 1.000] | 1.000 (11/11) [0.741, 1.000] | 1.000 (11/11) [0.741, 1.000] | – | – | 1.000 (11/11) [0.741, 1.000] |
| classification.subcode_accuracy_subcode_expected | 0.000 (0/13) [0.000, 0.228] | 0.000 (0/13) [0.000, 0.228] | 0.923 (12/13) [0.667, 0.986] | – | – | 0.000 (0/13) [0.000, 0.228] |
| classification.subcode_exact_accuracy | 0.458 (11/24) [0.279, 0.649] | 0.458 (11/24) [0.279, 0.649] | 0.958 (23/24) [0.798, 0.993] | – | – | 0.458 (11/24) [0.279, 0.649] |
| classification.target_status_accuracy | 0.667 (2/3, 21 n/s) [0.208, 0.939] | n/a (0/0, 24 n/s) | 0.667 (2/3, 21 n/s) [0.208, 0.939] | – | – | 0.000 (0/3, 21 n/s) [0.000, 0.561] |
| dates.exact_accuracy | not emitted | – | not emitted | – | – | 0.000 (0/7) [0.000, 0.354] |
| dates.value_exact_accuracy | 0.714 (5/7) [0.359, 0.918] | – | not emitted | – | – | 0.000 (0/7) [0.000, 0.354] |
| dates.value_precision | 1.000 (9/9) [0.701, 1.000] | – | – | – | – | n/a (0/0) |
| dates.value_recall | 0.692 (9/13) [0.424, 0.873] | – | – | – | – | 0.000 (0/13) [0.000, 0.228] |
| dates.value_role_precision | – | – | – | – | – | n/a (0/0) |
| dates.value_role_recall | – | – | – | – | – | 0.000 (0/13) [0.000, 0.228] |
| model.structured_output_valid_rate | – | – | – | – | – | 1.000 (33/33) [0.896, 1.000] |
| temporal.all_required_warnings_present | – | – | – | 1.000 (6/6) [0.610, 1.000] | – | – |
| temporal.candidate_exact_match | – | – | – | 1.000 (6/6) [0.610, 1.000] | – | – |
| temporal.candidate_only_determination | – | – | – | 1.000 (6/6) [0.610, 1.000] | – | – |
| temporal.forbidden_warning_violations | – | – | – | 0 of 6 | – | – |
| temporal.warning_recall | – | – | – | 1.000 (1/1) [0.207, 1.000] | – | – |

## Results: `test`

| metric | b1_python | b1_python_raw | b2_js | wlie | existing_law | mock_model |
|---|---|---|---|---|---|---|
| abstention.forbidden_assertion_violations | – | – | – | – | – | 0 of 1 |
| abstention.required_issue_coverage | – | – | – | – | – | 0.000 (0/4) [0.000, 0.490] |
| abstention.withhold_accuracy | – | – | – | – | – | 1.000 (1/1) [0.207, 1.000] |
| abstention.withhold_precision | – | – | – | – | – | 1.000 (1/1) [0.207, 1.000] |
| abstention.withhold_recall | – | – | – | – | – | 1.000 (1/1) [0.207, 1.000] |
| citation.accepted_future_not_yet_effective | – | – | – | 0 of 0, 3 n/s | 0 of 0, 3 n/s | – |
| citation.accepted_source_outdated | – | – | – | 0 of 0, 3 n/s | 0 of 0, 3 n/s | – |
| citation.accepted_version_failures | – | – | – | 0 of 0, 3 n/s | 0 of 0, 3 n/s | – |
| citation.accepted_wrong_version | – | – | – | 0 of 0, 3 n/s | 0 of 0, 3 n/s | – |
| citation.false_absence_declarations | – | – | – | 0 of 0, 3 n/s | 0 of 0, 3 n/s | – |
| citation.forbidden_code_violations | – | – | – | 0 of 3 | 0 of 3 | – |
| citation.highest_layer_within_bound | – | – | – | n/a (0/0, 3 n/s) | n/a (0/0, 3 n/s) | – |
| citation.injection_flag_accuracy | – | – | – | n/a (0/0, 3 n/s) | n/a (0/0, 3 n/s) | – |
| citation.layer_agreement.L1_source_identity | – | – | – | 1.000 (3/3) [0.439, 1.000] | 1.000 (3/3) [0.439, 1.000] | – |
| citation.layer_agreement.L2_version_identity | – | – | – | 1.000 (3/3) [0.439, 1.000] | n/a (0/0, 3 n/s) | – |
| citation.layer_agreement.L3_citation_identity | – | – | – | 1.000 (3/3) [0.439, 1.000] | 1.000 (3/3) [0.439, 1.000] | – |
| citation.layer_agreement.L4_text_correspondence | – | – | – | 1.000 (3/3) [0.439, 1.000] | n/a (0/0, 3 n/s) | – |
| citation.layer_agreement.L5_claim_support | – | – | – | 1.000 (3/3) [0.439, 1.000] | n/a (0/0, 3 n/s) | – |
| citation.layer_agreement.L7_conflict_uncertainty | – | – | – | 1.000 (3/3) [0.439, 1.000] | n/a (0/0, 3 n/s) | – |
| citation.overall_status_accuracy | – | – | – | 1.000 (3/3) [0.439, 1.000] | 0.000 (0/3) [0.000, 0.561] | – |
| citation.unlabelled_absence_codes | – | – | – | 0 of 3 | 0 of 3 | – |
| citation.unsupported_claim_acceptance_rate | – | – | – | 0.000 (0/1, 2 n/s) [0.000, 0.793] | 1.000 (1/1, 2 n/s) [0.207, 1.000] | – |
| citation.wrong_version_detection_rate | – | – | – | n/a (0/0, 3 n/s) | n/a (0/0, 3 n/s) | – |
| classification.clarification_precision | 1.000 (3/3) [0.439, 1.000] | – | 1.000 (3/3) [0.439, 1.000] | – | – | 1.000 (3/3) [0.439, 1.000] |
| classification.clarification_recall | 1.000 (3/3) [0.439, 1.000] | – | 1.000 (3/3) [0.439, 1.000] | – | – | 1.000 (3/3) [0.439, 1.000] |
| classification.current_status_accuracy | 0.200 (1/5, 50 n/s) [0.036, 0.624] | n/a (0/0, 55 n/s) | 0.600 (3/5, 50 n/s) [0.231, 0.882] | – | – | 0.000 (0/5, 50 n/s) [0.000, 0.434] |
| classification.hierarchy_violations | 26 of 55 | 6 of 55 | 0 of 55 | – | – | 0 of 55 |
| classification.non_code_token_respected | 0.000 (0/3, 52 n/s) [0.000, 0.561] | 0.000 (0/3, 52 n/s) [0.000, 0.561] | 0.667 (2/3, 52 n/s) [0.208, 0.939] | – | – | 1.000 (3/3, 52 n/s) [0.439, 1.000] |
| classification.procedure_coarse_accuracy | 0.524 (22/42, 13 n/s) [0.377, 0.666] | 0.500 (21/42, 13 n/s) [0.355, 0.645] | 0.786 (33/42, 13 n/s) [0.641, 0.883] | – | – | 0.000 (0/42, 13 n/s) [0.000, 0.084] |
| classification.procedure_fine_accuracy | not emitted | not emitted | 0.800 (44/55) [0.676, 0.884] | – | – | 0.000 (0/55) [0.000, 0.065] |
| classification.procedure_scope_violations | 0 of 55 | 0 of 55 | 0 of 55 | – | – | 0 of 55 |
| classification.status_exact_accuracy | 0.855 (47/55) [0.738, 0.924] | 0.491 (27/55) [0.364, 0.619] | 0.891 (49/55) [0.782, 0.949] | – | – | 0.145 (8/55) [0.076, 0.262] |
| classification.subcode_accuracy_no_subcode_expected | 1.000 (26/26) [0.871, 1.000] | 1.000 (26/26) [0.871, 1.000] | 1.000 (26/26) [0.871, 1.000] | – | – | 1.000 (26/26) [0.871, 1.000] |
| classification.subcode_accuracy_subcode_expected | 0.000 (0/29) [0.000, 0.117] | 0.000 (0/29) [0.000, 0.117] | 1.000 (29/29) [0.883, 1.000] | – | – | 0.000 (0/29) [0.000, 0.117] |
| classification.subcode_exact_accuracy | 0.473 (26/55) [0.347, 0.602] | 0.473 (26/55) [0.347, 0.602] | 1.000 (55/55) [0.935, 1.000] | – | – | 0.473 (26/55) [0.347, 0.602] |
| classification.target_status_accuracy | 0.667 (4/6, 49 n/s) [0.300, 0.903] | n/a (0/0, 55 n/s) | 0.667 (4/6, 49 n/s) [0.300, 0.903] | – | – | 0.000 (0/6, 49 n/s) [0.000, 0.390] |
| dates.exact_accuracy | not emitted | – | not emitted | – | – | 0.000 (0/5) [0.000, 0.434] |
| dates.value_exact_accuracy | 0.800 (4/5) [0.376, 0.964] | – | not emitted | – | – | 0.000 (0/5) [0.000, 0.434] |
| dates.value_precision | 1.000 (8/8) [0.676, 1.000] | – | – | – | – | n/a (0/0) |
| dates.value_recall | 0.800 (8/10) [0.490, 0.943] | – | – | – | – | 0.000 (0/10) [0.000, 0.278] |
| dates.value_role_precision | – | – | – | – | – | n/a (0/0) |
| dates.value_role_recall | – | – | – | – | – | 0.000 (0/10) [0.000, 0.278] |
| model.structured_output_valid_rate | – | – | – | – | – | 1.000 (61/61) [0.941, 1.000] |
| temporal.all_required_warnings_present | – | – | – | 1.000 (1/1) [0.207, 1.000] | – | – |
| temporal.candidate_exact_match | – | – | – | 1.000 (1/1) [0.207, 1.000] | – | – |
| temporal.candidate_only_determination | – | – | – | 1.000 (1/1) [0.207, 1.000] | – | – |
| temporal.forbidden_warning_violations | – | – | – | 0 of 1 | – | – |
| temporal.warning_recall | – | – | – | n/a (0/0) | – | – |

## Results: `adversarial_holdout`

| metric | b1_python | b1_python_raw | b2_js | wlie | existing_law | mock_model |
|---|---|---|---|---|---|---|
| abstention.forbidden_assertion_violations | – | – | – | – | – | 0 of 8 |
| abstention.required_issue_coverage | – | – | – | – | – | 0.000 (0/39) [0.000, 0.090] |
| abstention.withhold_accuracy | – | – | – | – | – | 1.000 (8/8) [0.676, 1.000] |
| abstention.withhold_precision | – | – | – | – | – | 1.000 (8/8) [0.676, 1.000] |
| abstention.withhold_recall | – | – | – | – | – | 1.000 (8/8) [0.676, 1.000] |
| citation.accepted_future_not_yet_effective | – | – | – | 0 of 3, 42 n/s | 2 of 3, 42 n/s | – |
| citation.accepted_source_outdated | – | – | – | 0 of 1, 44 n/s | 1 of 1, 44 n/s | – |
| citation.accepted_version_failures | – | – | – | 0 of 5, 40 n/s | 4 of 5, 40 n/s | – |
| citation.accepted_wrong_version | – | – | – | 0 of 1, 44 n/s | 1 of 1, 44 n/s | – |
| citation.false_absence_declarations | – | – | – | 0 of 14, 31 n/s | 2 of 14, 31 n/s | – |
| citation.forbidden_code_violations | – | – | – | 0 of 45 | 5 of 45 | – |
| citation.highest_layer_within_bound | – | – | – | 1.000 (29/29, 16 n/s) [0.883, 1.000] | 1.000 (29/29, 16 n/s) [0.883, 1.000] | – |
| citation.injection_flag_accuracy | – | – | – | 1.000 (2/2, 43 n/s) [0.342, 1.000] | n/a (0/0, 45 n/s) | – |
| citation.layer_agreement.L1_source_identity | – | – | – | 1.000 (44/44) [0.920, 1.000] | 0.841 (37/44) [0.706, 0.921] | – |
| citation.layer_agreement.L2_version_identity | – | – | – | 1.000 (43/43) [0.918, 1.000] | n/a (0/0, 43 n/s) | – |
| citation.layer_agreement.L3_citation_identity | – | – | – | 1.000 (44/44) [0.920, 1.000] | 0.844 (27/32, 12 n/s) [0.682, 0.931] | – |
| citation.layer_agreement.L4_text_correspondence | – | – | – | 1.000 (43/43) [0.918, 1.000] | n/a (0/0, 43 n/s) | – |
| citation.layer_agreement.L5_claim_support | – | – | – | 1.000 (20/20) [0.839, 1.000] | n/a (0/0, 20 n/s) | – |
| citation.layer_agreement.L6_applicability | – | – | – | 1.000 (20/20) [0.839, 1.000] | n/a (0/0, 20 n/s) | – |
| citation.layer_agreement.L7_conflict_uncertainty | – | – | – | 1.000 (45/45) [0.921, 1.000] | n/a (0/0, 45 n/s) | – |
| citation.overall_status_accuracy | – | – | – | 1.000 (45/45) [0.921, 1.000] | 0.267 (12/45) [0.160, 0.410] | – |
| citation.unlabelled_absence_codes | – | – | – | 0 of 45 | 6 of 45 | – |
| citation.unsupported_claim_acceptance_rate | – | – | – | 0.000 (0/26, 19 n/s) [0.000, 0.129] | 0.731 (19/26, 19 n/s) [0.539, 0.863] | – |
| citation.wrong_version_detection_rate | – | – | – | 1.000 (5/5, 40 n/s) [0.566, 1.000] | 0.000 (0/5, 40 n/s) [0.000, 0.434] | – |
| model.structured_output_valid_rate | – | – | – | – | – | 1.000 (8/8) [0.676, 1.000] |
| temporal.all_required_warnings_present | – | – | – | 1.000 (21/21) [0.845, 1.000] | – | – |
| temporal.candidate_exact_match | – | – | – | 1.000 (21/21) [0.845, 1.000] | – | – |
| temporal.candidate_only_determination | – | – | – | 1.000 (21/21) [0.845, 1.000] | – | – |
| temporal.forbidden_warning_violations | – | – | – | 0 of 12, 9 n/s | – | – |
| temporal.warning_recall | – | – | – | 1.000 (30/30) [0.886, 1.000] | – | – |

## Classification, text-only items (no payload code): `dev`

| metric | b1_python | b1_python_raw | b2_js | wlie | existing_law | mock_model |
|---|---|---|---|---|---|---|
| classification.clarification_precision | n/a (0/0) | – | 1.000 (1/1) [0.207, 1.000] | – | – | 1.000 (1/1) [0.207, 1.000] |
| classification.clarification_recall | 0.000 (0/1) [0.000, 0.793] | – | 1.000 (1/1) [0.207, 1.000] | – | – | 1.000 (1/1) [0.207, 1.000] |
| classification.current_status_accuracy | 0.333 (1/3, 21 n/s) [0.061, 0.792] | n/a (0/0, 24 n/s) | 0.667 (2/3, 21 n/s) [0.208, 0.939] | – | – | 0.000 (0/3, 21 n/s) [0.000, 0.561] |
| classification.hierarchy_violations | 11 of 24 | 0 of 24 | 0 of 24 | – | – | 0 of 24 |
| classification.non_code_token_respected | 0.000 (0/1, 23 n/s) [0.000, 0.793] | 1.000 (1/1, 23 n/s) [0.207, 1.000] | 0.000 (0/1, 23 n/s) [0.000, 0.793] | – | – | 1.000 (1/1, 23 n/s) [0.207, 1.000] |
| classification.procedure_coarse_accuracy | 0.368 (7/19, 5 n/s) [0.191, 0.590] | 0.316 (6/19, 5 n/s) [0.154, 0.540] | 0.789 (15/19, 5 n/s) [0.567, 0.915] | – | – | 0.000 (0/19, 5 n/s) [0.000, 0.168] |
| classification.procedure_fine_accuracy | not emitted | not emitted | 0.792 (19/24) [0.595, 0.908] | – | – | 0.000 (0/24) [0.000, 0.138] |
| classification.procedure_scope_violations | 0 of 24 | 0 of 24 | 0 of 24 | – | – | 0 of 24 |
| classification.status_exact_accuracy | 0.875 (21/24) [0.690, 0.957] | 0.417 (10/24) [0.245, 0.612] | 0.875 (21/24) [0.690, 0.957] | – | – | 0.083 (2/24) [0.023, 0.258] |
| classification.subcode_accuracy_no_subcode_expected | 1.000 (11/11) [0.741, 1.000] | 1.000 (11/11) [0.741, 1.000] | 1.000 (11/11) [0.741, 1.000] | – | – | 1.000 (11/11) [0.741, 1.000] |
| classification.subcode_accuracy_subcode_expected | 0.000 (0/13) [0.000, 0.228] | 0.000 (0/13) [0.000, 0.228] | 0.923 (12/13) [0.667, 0.986] | – | – | 0.000 (0/13) [0.000, 0.228] |
| classification.subcode_exact_accuracy | 0.458 (11/24) [0.279, 0.649] | 0.458 (11/24) [0.279, 0.649] | 0.958 (23/24) [0.798, 0.993] | – | – | 0.458 (11/24) [0.279, 0.649] |
| classification.target_status_accuracy | 0.667 (2/3, 21 n/s) [0.208, 0.939] | n/a (0/0, 24 n/s) | 0.667 (2/3, 21 n/s) [0.208, 0.939] | – | – | 0.000 (0/3, 21 n/s) [0.000, 0.561] |

## Classification, text-only items (no payload code): `test`

| metric | b1_python | b1_python_raw | b2_js | wlie | existing_law | mock_model |
|---|---|---|---|---|---|---|
| classification.clarification_precision | 1.000 (3/3) [0.439, 1.000] | – | 1.000 (3/3) [0.439, 1.000] | – | – | 1.000 (3/3) [0.439, 1.000] |
| classification.clarification_recall | 1.000 (3/3) [0.439, 1.000] | – | 1.000 (3/3) [0.439, 1.000] | – | – | 1.000 (3/3) [0.439, 1.000] |
| classification.current_status_accuracy | 0.200 (1/5, 50 n/s) [0.036, 0.624] | n/a (0/0, 55 n/s) | 0.600 (3/5, 50 n/s) [0.231, 0.882] | – | – | 0.000 (0/5, 50 n/s) [0.000, 0.434] |
| classification.hierarchy_violations | 26 of 55 | 6 of 55 | 0 of 55 | – | – | 0 of 55 |
| classification.non_code_token_respected | 0.000 (0/3, 52 n/s) [0.000, 0.561] | 0.000 (0/3, 52 n/s) [0.000, 0.561] | 0.667 (2/3, 52 n/s) [0.208, 0.939] | – | – | 1.000 (3/3, 52 n/s) [0.439, 1.000] |
| classification.procedure_coarse_accuracy | 0.524 (22/42, 13 n/s) [0.377, 0.666] | 0.500 (21/42, 13 n/s) [0.355, 0.645] | 0.786 (33/42, 13 n/s) [0.641, 0.883] | – | – | 0.000 (0/42, 13 n/s) [0.000, 0.084] |
| classification.procedure_fine_accuracy | not emitted | not emitted | 0.800 (44/55) [0.676, 0.884] | – | – | 0.000 (0/55) [0.000, 0.065] |
| classification.procedure_scope_violations | 0 of 55 | 0 of 55 | 0 of 55 | – | – | 0 of 55 |
| classification.status_exact_accuracy | 0.855 (47/55) [0.738, 0.924] | 0.491 (27/55) [0.364, 0.619] | 0.891 (49/55) [0.782, 0.949] | – | – | 0.145 (8/55) [0.076, 0.262] |
| classification.subcode_accuracy_no_subcode_expected | 1.000 (26/26) [0.871, 1.000] | 1.000 (26/26) [0.871, 1.000] | 1.000 (26/26) [0.871, 1.000] | – | – | 1.000 (26/26) [0.871, 1.000] |
| classification.subcode_accuracy_subcode_expected | 0.000 (0/29) [0.000, 0.117] | 0.000 (0/29) [0.000, 0.117] | 1.000 (29/29) [0.883, 1.000] | – | – | 0.000 (0/29) [0.000, 0.117] |
| classification.subcode_exact_accuracy | 0.473 (26/55) [0.347, 0.602] | 0.473 (26/55) [0.347, 0.602] | 1.000 (55/55) [0.935, 1.000] | – | – | 0.473 (26/55) [0.347, 0.602] |
| classification.target_status_accuracy | 0.667 (4/6, 49 n/s) [0.300, 0.903] | n/a (0/0, 55 n/s) | 0.667 (4/6, 49 n/s) [0.300, 0.903] | – | – | 0.000 (0/6, 49 n/s) [0.000, 0.390] |

## Classification, text-only items (no payload code): `adversarial_holdout`

No scorable items.

## Verdicts per adversarial class

| baseline | split | class | correct | wrong | not scorable |
|---|---|---|---|---|---|
| b1_python | dev | none | 11 | 20 | 0 |
| b1_python | test | none | 17 | 43 | 0 |
| b1_python_raw | dev | none | 5 | 19 | 0 |
| b1_python_raw | test | none | 12 | 43 | 0 |
| b2_js | dev | none | 17 | 7 | 7 |
| b2_js | test | none | 39 | 16 | 5 |
| wlie | adversarial_holdout | A | 5 | 0 | 0 |
| wlie | adversarial_holdout | B | 4 | 0 | 0 |
| wlie | adversarial_holdout | C | 3 | 0 | 0 |
| wlie | adversarial_holdout | D | 8 | 0 | 0 |
| wlie | adversarial_holdout | E | 15 | 0 | 0 |
| wlie | adversarial_holdout | F | 4 | 0 | 0 |
| wlie | adversarial_holdout | G | 5 | 0 | 0 |
| wlie | adversarial_holdout | H | 10 | 0 | 0 |
| wlie | adversarial_holdout | I | 5 | 0 | 0 |
| wlie | adversarial_holdout | J | 3 | 0 | 0 |
| wlie | adversarial_holdout | K | 1 | 0 | 0 |
| wlie | adversarial_holdout | M | 1 | 0 | 0 |
| wlie | adversarial_holdout | N | 2 | 0 | 0 |
| wlie | dev | none | 16 | 0 | 0 |
| wlie | test | none | 4 | 0 | 0 |
| existing_law | adversarial_holdout | A | 3 | 2 | 0 |
| existing_law | adversarial_holdout | B | 1 | 3 | 0 |
| existing_law | adversarial_holdout | C | 0 | 3 | 0 |
| existing_law | adversarial_holdout | D | 0 | 2 | 0 |
| existing_law | adversarial_holdout | E | 1 | 3 | 0 |
| existing_law | adversarial_holdout | F | 0 | 3 | 0 |
| existing_law | adversarial_holdout | G | 1 | 3 | 0 |
| existing_law | adversarial_holdout | H | 6 | 3 | 0 |
| existing_law | adversarial_holdout | I | 0 | 5 | 0 |
| existing_law | adversarial_holdout | J | 0 | 3 | 0 |
| existing_law | adversarial_holdout | M | 0 | 1 | 0 |
| existing_law | adversarial_holdout | N | 0 | 2 | 0 |
| existing_law | dev | none | 0 | 10 | 0 |
| existing_law | test | none | 0 | 3 | 0 |
| mock_model | adversarial_holdout | K | 0 | 3 | 0 |
| mock_model | adversarial_holdout | L | 0 | 3 | 0 |
| mock_model | adversarial_holdout | M | 0 | 2 | 0 |
| mock_model | dev | none | 0 | 33 | 0 |
| mock_model | test | none | 0 | 61 | 0 |

## Critical legal errors

| baseline | split | example | task | categories |
|---|---|---|---|---|
| b1_python | dev | cls-en-d10-to-e7 | status_procedure_classification | critical_example_wrong |
| b1_python | dev | cls-en-d84s-visa-issuance | status_procedure_classification | critical_example_wrong |
| b1_python | dev | cls-en-e7-visa-issuance | status_procedure_classification | critical_example_wrong |
| b1_python | dev | cls-en-e71-cvi | status_procedure_classification | critical_example_wrong |
| b1_python | dev | cls-en-g15-register | status_procedure_classification | critical_example_wrong |
| b1_python | dev | cls-ko-c39-visa-issuance | status_procedure_classification | critical_example_wrong |
| b1_python | dev | cls-ko-d41-to-d21 | status_procedure_classification | critical_example_wrong |
| b1_python | dev | cls-ko-d42k-registration | status_procedure_classification | critical_example_wrong |
| b1_python | dev | cls-ko-e74r-condition-change | status_procedure_classification | critical_example_wrong |
| b1_python | dev | cls-ko-e74r-extension | status_procedure_classification | critical_example_wrong |
| b1_python | dev | cls-ko-work-visa-issuance | status_procedure_classification | critical_example_wrong |
| b1_python | dev | cls-zh-d10-to-e71 | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-en-a3-month-trap | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-en-d2-switch-d101 | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-en-e74r-card-reissue | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-en-e7s1-extension | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-en-f10-visa-application | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-en-f2r-condition-change | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ja-e7-cvi | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ja-e74r-card-reissue | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-d10-to-e71 | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-d10t-extension | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-d21-glued-extension | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-e7-cvi-employer | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-e71-evisa | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-e7t-cvi | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-e9-to-e74 | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-f10-nonexistent | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-f27s-extension | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-f2t-card-reissue | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-f6-to-e9 | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-g15-extension | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-ko-to-f5t | status_procedure_classification | critical_example_wrong |
| b1_python | test | cls-vi-f6-to-f5 | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-en-d10-to-e7 | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-en-d84s-visa-issuance | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-en-e7-visa-issuance | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-en-e71-cvi | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-en-g15-register | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-ko-c39-visa-issuance | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-ko-d41-to-d21 | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-ko-d42k-registration | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-ko-e74r-condition-change | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-ko-e74r-extension | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-ko-work-visa-issuance | status_procedure_classification | critical_example_wrong |
| b1_python_raw | dev | cls-zh-d10-to-e71 | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-en-a3-month-trap | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-en-d2-switch-d101 | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-en-e74r-card-reissue | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-en-e7s1-extension | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-en-f10-visa-application | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-en-f2r-condition-change | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ja-e7-cvi | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ja-e74r-card-reissue | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-d10-to-e71 | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-d10t-extension | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-d21-glued-extension | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-e7-cvi-employer | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-e71-evisa | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-e7t-cvi | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-e9-to-e74 | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-f10-nonexistent | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-f27s-extension | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-f2t-card-reissue | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-f6-to-e9 | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-g15-extension | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-ko-to-f5t | status_procedure_classification | critical_example_wrong |
| b1_python_raw | test | cls-vi-f6-to-f5 | status_procedure_classification | critical_example_wrong |
| b2_js | dev | cls-en-2nd-year-trap | status_procedure_classification | critical_example_wrong |
| b2_js | dev | cls-ko-d2-evisa | status_procedure_classification | critical_example_wrong |
| b2_js | dev | cls-zh-d10-to-e71 | status_procedure_classification | critical_example_wrong |
| b2_js | test | cls-en-a3-month-trap | status_procedure_classification | critical_example_wrong |
| b2_js | test | cls-en-f10-visa-application | status_procedure_classification | critical_example_wrong |
| b2_js | test | cls-ja-e7-cvi | status_procedure_classification | critical_example_wrong |
| b2_js | test | cls-ja-e74r-card-reissue | status_procedure_classification | critical_example_wrong |
| b2_js | test | cls-ko-f10-nonexistent | status_procedure_classification | critical_example_wrong |
| b2_js | test | cls-vi-f6-to-f5 | status_procedure_classification | critical_example_wrong |
| existing_law | adversarial_holdout | ver-real-nationality-outdated-quote | citation_verification | accepted_source_outdated, critical_example_wrong |
| existing_law | adversarial_holdout | ver-real-nationality-pending-quote | citation_verification | accepted_future_not_yet_effective, critical_example_wrong |
| existing_law | adversarial_holdout | ver-real-r73-card-asserted-current | citation_verification | critical_example_wrong |
| existing_law | adversarial_holdout | ver-real-r73-card-quote-future | citation_verification | accepted_future_not_yet_effective, critical_example_wrong |
| existing_law | adversarial_holdout | ver-real-title-outside-capture | citation_verification | critical_example_wrong, false_absence_declaration |
| existing_law | adversarial_holdout | ver-syn-decree-text-cited-as-act | citation_verification | critical_example_wrong |
| existing_law | adversarial_holdout | ver-syn-fault-addenda-timeout | citation_verification | critical_example_wrong |
| existing_law | adversarial_holdout | ver-syn-fault-history-malformed-json | citation_verification | critical_example_wrong |
| existing_law | adversarial_holdout | ver-syn-former-title-partial-index | citation_verification | critical_example_wrong, false_absence_declaration |
| existing_law | adversarial_holdout | ver-syn-injection-claim-from-instruction | citation_verification | critical_example_wrong |
| existing_law | adversarial_holdout | ver-syn-later-amendment-past-event | citation_verification | accepted_wrong_version, critical_example_wrong |
| existing_law | adversarial_holdout | ver-syn-manual-conflicts-and-predates | citation_verification | critical_example_wrong |
| existing_law | adversarial_holdout | ver-syn-no-source-at-all | citation_verification | critical_example_wrong |
| existing_law | adversarial_holdout | ver-syn-stay-rule-for-visa-claim | citation_verification | critical_example_wrong |
| existing_law | adversarial_holdout | ver-syn-subcode-other-listed | citation_verification | critical_example_wrong |
| existing_law | adversarial_holdout | ver-syn-subcode-parent-only | citation_verification | critical_example_wrong |
| existing_law | adversarial_holdout | ver-syn-visa-rule-for-stay-claim | citation_verification | critical_example_wrong |
| mock_model | dev | cls-en-2nd-year-trap | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-en-d10-to-e7 | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-en-d84s-visa-issuance | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-en-e7-evisa | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-en-e7-visa-issuance | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-en-e71-cvi | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-en-g15-register | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-ko-c39-visa-issuance | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-ko-d2-evisa | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-ko-d41-to-d21 | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-ko-d42k-registration | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-ko-e74r-condition-change | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-ko-e74r-extension | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-ko-work-visa-issuance | status_procedure_classification | critical_example_wrong |
| mock_model | dev | cls-zh-d10-to-e71 | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-en-a3-month-trap | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-en-d2-switch-d101 | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-en-e74r-card-reissue | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-en-e7s1-extension | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-en-f10-visa-application | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-en-f2r-condition-change | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-en-student-visa-extension | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ja-e7-cvi | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ja-e74r-card-reissue | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-d10-to-e71 | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-d10t-extension | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-d21-glued-extension | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-e7-cvi-employer | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-e71-evisa | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-e7t-cvi | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-e9-to-e74 | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-f10-nonexistent | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-f27s-extension | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-f2t-card-reissue | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-f6-to-e9 | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-g15-extension | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-spouse-visa-extension | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-student-visa-extension | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-ko-to-f5t | status_procedure_classification | critical_example_wrong |
| mock_model | test | cls-vi-f6-to-f5 | status_procedure_classification | critical_example_wrong |
| mock_model | adversarial_holdout | abs-k-depart-before-return-after-expiry | abstention | critical_example_wrong |
| mock_model | adversarial_holdout | abs-k-en-return-after-expiry | abstention | critical_example_wrong |
| mock_model | adversarial_holdout | abs-k-extension-from-abroad | abstention | critical_example_wrong |
| mock_model | adversarial_holdout | abs-l-agent-visa-to-stay | abstention | critical_example_wrong |
| mock_model | adversarial_holdout | abs-l-employer-files-extension | abstention | critical_example_wrong |
| mock_model | adversarial_holdout | abs-l-en-spouse-two-procedures | abstention | critical_example_wrong |
| mock_model | adversarial_holdout | abs-m-discretionary-condition | abstention | critical_example_wrong |
| mock_model | adversarial_holdout | abs-m-en-related-field | abstention | critical_example_wrong |

## Gates (project hypotheses; decision splits only)

### b1_python: **NO_GO**
Decision splits: test, adversarial_holdout; scored labels not human-verified: 60 (critical: 25)

| gate | hard | metric | rule | result | value | base |
|---|---|---|---|---|---|---|
| HG-1 | hard | citation.false_absence_declarations | = 0 | not_applicable | – | – |
| HG-2 | hard | citation.accepted_future_not_yet_effective | = 0 | not_applicable | – | – |
| HG-3 | hard | citation.accepted_wrong_version | = 0 | not_applicable | – | – |
| HG-4 | hard | citation.accepted_source_outdated | = 0 | not_applicable | – | – |
| HG-5 | hard | citation.unsupported_claim_acceptance_rate | = 0 | not_applicable | – | – |
| HG-6 | hard | temporal.forbidden_warning_violations | = 0 | not_applicable | – | – |
| HG-7 | hard | classification.procedure_scope_violations | = 0 | pass | 0 | 55 |
| HG-8 | hard | _critical | = 0 | fail | 22 | 60 |
| HG-9 | hard | _errors | = 0 | pass | 0 | 60 |
| HG-10 | hard | classification.hierarchy_violations | = 0 | fail | 26 | 55 |
| SG-1 | soft | citation.overall_status_accuracy | >= 0.95 | not_applicable | – | – |
| SG-2 | soft | citation.wrong_version_detection_rate | >= 0.9 | not_applicable | – | – |
| SG-3 | soft | temporal.candidate_exact_match | >= 0.95 | not_applicable | – | – |
| SG-4 | soft | temporal.warning_recall | >= 0.95 | not_applicable | – | – |
| SG-5 | soft | classification.status_exact_accuracy | >= 0.9 | fail | 0.854545 | 55 |
| SG-6 | soft | classification.subcode_accuracy_subcode_expected | >= 0.9 | fail | 0.0 | 29 |
| SG-7 | soft | classification.procedure_fine_accuracy | >= 0.85 | not_applicable | – | – |
| SG-8 | soft | model.structured_output_valid_rate | >= 1.0 | not_applicable | – | – |
| PG-1 | timing | performance.latency_p95_ms | <= 3500.0 | pass | 1.324 | 60 |

Timing rows (PG-*) depend on the machine; they are reported but do not enter the decision.

### b1_python_raw: **NO_GO**
Decision splits: test, adversarial_holdout; scored labels not human-verified: 55 (critical: 25)

| gate | hard | metric | rule | result | value | base |
|---|---|---|---|---|---|---|
| HG-1 | hard | citation.false_absence_declarations | = 0 | not_applicable | – | – |
| HG-2 | hard | citation.accepted_future_not_yet_effective | = 0 | not_applicable | – | – |
| HG-3 | hard | citation.accepted_wrong_version | = 0 | not_applicable | – | – |
| HG-4 | hard | citation.accepted_source_outdated | = 0 | not_applicable | – | – |
| HG-5 | hard | citation.unsupported_claim_acceptance_rate | = 0 | not_applicable | – | – |
| HG-6 | hard | temporal.forbidden_warning_violations | = 0 | not_applicable | – | – |
| HG-7 | hard | classification.procedure_scope_violations | = 0 | pass | 0 | 55 |
| HG-8 | hard | _critical | = 0 | fail | 22 | 55 |
| HG-9 | hard | _errors | = 0 | pass | 0 | 55 |
| HG-10 | hard | classification.hierarchy_violations | = 0 | fail | 6 | 55 |
| SG-1 | soft | citation.overall_status_accuracy | >= 0.95 | not_applicable | – | – |
| SG-2 | soft | citation.wrong_version_detection_rate | >= 0.9 | not_applicable | – | – |
| SG-3 | soft | temporal.candidate_exact_match | >= 0.95 | not_applicable | – | – |
| SG-4 | soft | temporal.warning_recall | >= 0.95 | not_applicable | – | – |
| SG-5 | soft | classification.status_exact_accuracy | >= 0.9 | fail | 0.490909 | 55 |
| SG-6 | soft | classification.subcode_accuracy_subcode_expected | >= 0.9 | fail | 0.0 | 29 |
| SG-7 | soft | classification.procedure_fine_accuracy | >= 0.85 | not_applicable | – | – |
| SG-8 | soft | model.structured_output_valid_rate | >= 1.0 | not_applicable | – | – |
| PG-1 | timing | performance.latency_p95_ms | <= 3500.0 | pass | 1.279 | 55 |

Timing rows (PG-*) depend on the machine; they are reported but do not enter the decision.

### b2_js: **NO_GO**
Decision splits: test, adversarial_holdout; scored labels not human-verified: 55 (critical: 25)

| gate | hard | metric | rule | result | value | base |
|---|---|---|---|---|---|---|
| HG-1 | hard | citation.false_absence_declarations | = 0 | not_applicable | – | – |
| HG-2 | hard | citation.accepted_future_not_yet_effective | = 0 | not_applicable | – | – |
| HG-3 | hard | citation.accepted_wrong_version | = 0 | not_applicable | – | – |
| HG-4 | hard | citation.accepted_source_outdated | = 0 | not_applicable | – | – |
| HG-5 | hard | citation.unsupported_claim_acceptance_rate | = 0 | not_applicable | – | – |
| HG-6 | hard | temporal.forbidden_warning_violations | = 0 | not_applicable | – | – |
| HG-7 | hard | classification.procedure_scope_violations | = 0 | pass | 0 | 55 |
| HG-8 | hard | _critical | = 0 | fail | 6 | 55 |
| HG-9 | hard | _errors | = 0 | pass | 0 | 60 |
| HG-10 | hard | classification.hierarchy_violations | = 0 | pass | 0 | 55 |
| SG-1 | soft | citation.overall_status_accuracy | >= 0.95 | not_applicable | – | – |
| SG-2 | soft | citation.wrong_version_detection_rate | >= 0.9 | not_applicable | – | – |
| SG-3 | soft | temporal.candidate_exact_match | >= 0.95 | not_applicable | – | – |
| SG-4 | soft | temporal.warning_recall | >= 0.95 | not_applicable | – | – |
| SG-5 | soft | classification.status_exact_accuracy | >= 0.9 | fail | 0.890909 | 55 |
| SG-6 | soft | classification.subcode_accuracy_subcode_expected | >= 0.9 | pass | 1.0 | 29 |
| SG-7 | soft | classification.procedure_fine_accuracy | >= 0.85 | fail | 0.8 | 55 |
| SG-8 | soft | model.structured_output_valid_rate | >= 1.0 | not_applicable | – | – |
| PG-1 | timing | performance.latency_p95_ms | <= 3500.0 | pass | 0.109 | 60 |

Timing rows (PG-*) depend on the machine; they are reported but do not enter the decision.

### wlie: **PROVISIONAL_GO**
Decision splits: test, adversarial_holdout; scored labels not human-verified: 70 (critical: 49)

| gate | hard | metric | rule | result | value | base |
|---|---|---|---|---|---|---|
| HG-1 | hard | citation.false_absence_declarations | = 0 | pass | 0 | 14 |
| HG-2 | hard | citation.accepted_future_not_yet_effective | = 0 | pass | 0 | 3 |
| HG-3 | hard | citation.accepted_wrong_version | = 0 | pass | 0 | 1 |
| HG-4 | hard | citation.accepted_source_outdated | = 0 | pass | 0 | 1 |
| HG-5 | hard | citation.unsupported_claim_acceptance_rate | = 0 | pass | 0 | 27 |
| HG-6 | hard | temporal.forbidden_warning_violations | = 0 | pass | 0 | 13 |
| HG-7 | hard | classification.procedure_scope_violations | = 0 | not_applicable | – | – |
| HG-8 | hard | _critical | = 0 | pass | 0 | 70 |
| HG-9 | hard | _errors | = 0 | pass | 0 | 70 |
| HG-10 | hard | classification.hierarchy_violations | = 0 | not_applicable | – | – |
| SG-1 | soft | citation.overall_status_accuracy | >= 0.95 | pass | 1.0 | 48 |
| SG-2 | soft | citation.wrong_version_detection_rate | >= 0.9 | pass | 1.0 | 5 |
| SG-3 | soft | temporal.candidate_exact_match | >= 0.95 | pass | 1.0 | 22 |
| SG-4 | soft | temporal.warning_recall | >= 0.95 | pass | 1.0 | 30 |
| SG-5 | soft | classification.status_exact_accuracy | >= 0.9 | not_applicable | – | – |
| SG-6 | soft | classification.subcode_accuracy_subcode_expected | >= 0.9 | not_applicable | – | – |
| SG-7 | soft | classification.procedure_fine_accuracy | >= 0.85 | not_applicable | – | – |
| SG-8 | soft | model.structured_output_valid_rate | >= 1.0 | not_applicable | – | – |
| PG-1 | timing | performance.latency_p95_ms | <= 3500.0 | pass | 2.435 | 70 |

Timing rows (PG-*) depend on the machine; they are reported but do not enter the decision.

### existing_law: **NO_GO**
Decision splits: test, adversarial_holdout; scored labels not human-verified: 48 (critical: 29)

| gate | hard | metric | rule | result | value | base |
|---|---|---|---|---|---|---|
| HG-1 | hard | citation.false_absence_declarations | = 0 | fail | 2 | 14 |
| HG-2 | hard | citation.accepted_future_not_yet_effective | = 0 | fail | 2 | 3 |
| HG-3 | hard | citation.accepted_wrong_version | = 0 | fail | 1 | 1 |
| HG-4 | hard | citation.accepted_source_outdated | = 0 | fail | 1 | 1 |
| HG-5 | hard | citation.unsupported_claim_acceptance_rate | = 0 | fail | 20 | 27 |
| HG-6 | hard | temporal.forbidden_warning_violations | = 0 | not_applicable | – | – |
| HG-7 | hard | classification.procedure_scope_violations | = 0 | not_applicable | – | – |
| HG-8 | hard | _critical | = 0 | fail | 17 | 48 |
| HG-9 | hard | _errors | = 0 | pass | 0 | 48 |
| HG-10 | hard | classification.hierarchy_violations | = 0 | not_applicable | – | – |
| SG-1 | soft | citation.overall_status_accuracy | >= 0.95 | fail | 0.25 | 48 |
| SG-2 | soft | citation.wrong_version_detection_rate | >= 0.9 | fail | 0.0 | 5 |
| SG-3 | soft | temporal.candidate_exact_match | >= 0.95 | not_applicable | – | – |
| SG-4 | soft | temporal.warning_recall | >= 0.95 | not_applicable | – | – |
| SG-5 | soft | classification.status_exact_accuracy | >= 0.9 | not_applicable | – | – |
| SG-6 | soft | classification.subcode_accuracy_subcode_expected | >= 0.9 | not_applicable | – | – |
| SG-7 | soft | classification.procedure_fine_accuracy | >= 0.85 | not_applicable | – | – |
| SG-8 | soft | model.structured_output_valid_rate | >= 1.0 | not_applicable | – | – |
| PG-1 | timing | performance.latency_p95_ms | <= 3500.0 | pass | 11.897 | 48 |

Timing rows (PG-*) depend on the machine; they are reported but do not enter the decision.

### mock_model: **NO_GO**
Decision splits: test, adversarial_holdout; scored labels not human-verified: 69 (critical: 33)

| gate | hard | metric | rule | result | value | base |
|---|---|---|---|---|---|---|
| HG-1 | hard | citation.false_absence_declarations | = 0 | not_applicable | – | – |
| HG-2 | hard | citation.accepted_future_not_yet_effective | = 0 | not_applicable | – | – |
| HG-3 | hard | citation.accepted_wrong_version | = 0 | not_applicable | – | – |
| HG-4 | hard | citation.accepted_source_outdated | = 0 | not_applicable | – | – |
| HG-5 | hard | citation.unsupported_claim_acceptance_rate | = 0 | not_applicable | – | – |
| HG-6 | hard | temporal.forbidden_warning_violations | = 0 | not_applicable | – | – |
| HG-7 | hard | classification.procedure_scope_violations | = 0 | pass | 0 | 55 |
| HG-8 | hard | _critical | = 0 | fail | 33 | 69 |
| HG-9 | hard | _errors | = 0 | pass | 0 | 69 |
| HG-10 | hard | classification.hierarchy_violations | = 0 | pass | 0 | 55 |
| SG-1 | soft | citation.overall_status_accuracy | >= 0.95 | not_applicable | – | – |
| SG-2 | soft | citation.wrong_version_detection_rate | >= 0.9 | not_applicable | – | – |
| SG-3 | soft | temporal.candidate_exact_match | >= 0.95 | not_applicable | – | – |
| SG-4 | soft | temporal.warning_recall | >= 0.95 | not_applicable | – | – |
| SG-5 | soft | classification.status_exact_accuracy | >= 0.9 | fail | 0.145455 | 55 |
| SG-6 | soft | classification.subcode_accuracy_subcode_expected | >= 0.9 | fail | 0.0 | 29 |
| SG-7 | soft | classification.procedure_fine_accuracy | >= 0.85 | fail | 0.0 | 55 |
| SG-8 | soft | model.structured_output_valid_rate | >= 1.0 | pass | 1.0 | 69 |
| PG-1 | timing | performance.latency_p95_ms | <= 3500.0 | pass | 0.018 | 69 |

Timing rows (PG-*) depend on the machine; they are reported but do not enter the decision.

## Performance

| baseline | split | items | latency p50 ms | latency p95 ms | upstream calls | max calls/item | peak memory B | memory kind | tokens |
|---|---|---|---|---|---|---|---|---|---|
| b1_python | adversarial_holdout | 0 | None | None | None | None | None | – | – |
| b1_python | dev | 31 | 1.119 | 4.686 | 0 | 0 | 168569 | tracemalloc_peak | – |
| b1_python | test | 60 | 1.092 | 1.324 | 0 | 0 | 55318 | tracemalloc_peak | – |
| b1_python_raw | adversarial_holdout | 0 | None | None | None | None | None | – | – |
| b1_python_raw | dev | 24 | 1.083 | 1.273 | 0 | 0 | 168569 | tracemalloc_peak | – |
| b1_python_raw | test | 55 | 1.089 | 1.279 | 0 | 0 | 55318 | tracemalloc_peak | – |
| b2_js | adversarial_holdout | 0 | None | None | None | None | None | – | – |
| b2_js | dev | 31 | 0.115 | 1.278 | 0 | 0 | 11229504 | js_heap_used | – |
| b2_js | test | 60 | 0.077 | 0.109 | 0 | 0 | 12471456 | js_heap_used | – |
| wlie | adversarial_holdout | 66 | 0.78 | 2.435 | 175 | 6 | 33558 | tracemalloc_peak | – |
| wlie | dev | 16 | 1.118 | 2.229 | 46 | 4 | 33056 | tracemalloc_peak | – |
| wlie | test | 4 | 1.686 | 1.938 | 13 | 4 | 19191 | tracemalloc_peak | – |
| existing_law | adversarial_holdout | 45 | 6.553 | 11.818 | 168 | 7 | 2290521 | tracemalloc_peak | – |
| existing_law | dev | 10 | 11.897 | 38.025 | 38 | 8 | 1988882 | tracemalloc_peak | – |
| existing_law | test | 3 | 7.671 | 11.897 | 14 | 5 | 2141790 | tracemalloc_peak | – |
| mock_model | adversarial_holdout | 8 | 0.012 | 0.013 | 8 | 1 | 1018 | tracemalloc_peak_client | – |
| mock_model | dev | 33 | 0.017 | 0.021 | 33 | 1 | 1694 | tracemalloc_peak_client | – |
| mock_model | test | 61 | 0.017 | 0.018 | 61 | 1 | 1694 | tracemalloc_peak_client | – |

## Not-scorable reasons

| baseline | split | reason | metric outcomes |
|---|---|---|---|
| b1_python | dev | baseline_emits_coarse_only | 24 |
| b1_python | dev | no_coarse_equivalent | 5 |
| b1_python | dev | not_labelled | 93 |
| b1_python | dev | roles_not_emitted | 7 |
| b1_python | test | baseline_emits_coarse_only | 55 |
| b1_python | test | no_coarse_equivalent | 13 |
| b1_python | test | not_labelled | 207 |
| b1_python | test | roles_not_emitted | 5 |
| b1_python_raw | dev | baseline_emits_coarse_only | 24 |
| b1_python_raw | dev | no_coarse_equivalent | 5 |
| b1_python_raw | dev | not_emitted | 7 |
| b1_python_raw | dev | not_labelled | 88 |
| b1_python_raw | test | baseline_emits_coarse_only | 55 |
| b1_python_raw | test | no_coarse_equivalent | 13 |
| b1_python_raw | test | not_emitted | 14 |
| b1_python_raw | test | not_labelled | 203 |
| b2_js | dev | no_coarse_equivalent | 5 |
| b2_js | dev | not_emitted | 14 |
| b2_js | dev | not_labelled | 93 |
| b2_js | test | no_coarse_equivalent | 13 |
| b2_js | test | not_emitted | 10 |
| b2_js | test | not_labelled | 207 |
| wlie | adversarial_holdout | label_not_rejection | 19 |
| wlie | adversarial_holdout | label_not_unavailable | 31 |
| wlie | adversarial_holdout | label_not_version_failure | 200 |
| wlie | adversarial_holdout | label_other_version_failure | 10 |
| wlie | adversarial_holdout | not_labelled | 68 |
| wlie | dev | label_not_rejection | 9 |
| wlie | dev | label_not_unavailable | 10 |
| wlie | dev | label_not_version_failure | 50 |
| wlie | dev | not_labelled | 20 |
| wlie | test | label_not_rejection | 2 |
| wlie | test | label_not_unavailable | 3 |
| wlie | test | label_not_version_failure | 15 |
| wlie | test | not_labelled | 6 |
| existing_law | adversarial_holdout | label_not_rejection | 19 |
| existing_law | adversarial_holdout | label_not_unavailable | 31 |
| existing_law | adversarial_holdout | label_not_version_failure | 200 |
| existing_law | adversarial_holdout | label_other_version_failure | 10 |
| existing_law | adversarial_holdout | layer_not_reported | 183 |
| existing_law | adversarial_holdout | no_layer_reported | 1 |
| existing_law | adversarial_holdout | not_emitted | 2 |
| existing_law | adversarial_holdout | not_labelled | 59 |
| existing_law | dev | label_not_rejection | 9 |
| existing_law | dev | label_not_unavailable | 10 |
| existing_law | dev | label_not_version_failure | 50 |
| existing_law | dev | layer_not_reported | 44 |
| existing_law | dev | not_labelled | 20 |
| existing_law | test | label_not_rejection | 2 |
| existing_law | test | label_not_unavailable | 3 |
| existing_law | test | label_not_version_failure | 15 |
| existing_law | test | layer_not_reported | 12 |
| existing_law | test | not_labelled | 6 |
| mock_model | dev | no_coarse_equivalent | 5 |
| mock_model | dev | not_labelled | 93 |
| mock_model | test | no_coarse_equivalent | 13 |
| mock_model | test | not_labelled | 207 |

## Held-out ledger

Prior adversarial_holdout runs for this benchmark version: 4 (THIS RUN IS A REPEAT)

**THIS RUN IS A POST-HOC RE-SCORING** of adversarial_holdout items already looked at (7 earlier ledger entries under any benchmark digest). Reason: final integration re-scoring on the clean stage-A snapshot 1481605 (spec 06/07 decisions of 2026-10-20, align-bench revision-2 labels, WLIE blocked-layer fix, wlie baseline context_title, law-stack F9-F12); the blind-label audit of this pass changed no label and no code; adversarial_holdout first scored 2026-10-19 (ledger entries 1-2, benchmark digest db882bf2), so these are not first-look numbers. Its holdout numbers are not first-look numbers.
