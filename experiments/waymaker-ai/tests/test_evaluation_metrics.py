"""Metric math, hierarchy scoring, not-scorable handling, critical errors and gates.

Every example here is written inline. Nothing reads the real benchmark.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from waymaker_ai.evaluation import gates
from waymaker_ai.evaluation.metrics import CORRECT, NOT_SCORABLE, WRONG, aggregate, parent_of, score_item
from waymaker_ai.evaluation.predictions import INVALID_OUTPUT_FLAG, parse_model_output
from waymaker_ai.evaluation.summary import critical_categories, headline, performance

CLS_ALL = {"status_code", "subcode", "procedure_fine", "current_status", "target_status", "needs_clarification",
           "mentioned_codes"}
CLS_COARSE = {"status_code", "subcode", "procedure_coarse"}
CIT_ALL = {"overall", "layer_codes", "codes", "highest_verified_layer", "injection_flagged"}


def example(task: str, expected: Dict[str, Any], *, critical: bool = False, split: str = "test",
            ident: str = "ex-0001") -> Dict[str, Any]:
    return {"id": ident, "task": task, "split": split, "critical": critical, "input": {"question": "q"},
            "expected": expected, "scenario": {"relevant_dates": {}, "anchor": None}}


def cls_pred(status: Optional[str] = None, subcode: Optional[str] = None, fine: Optional[str] = None,
             coarse: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    pred = {"status_code": status, "subcode": subcode, "procedure_fine": fine, "procedure_coarse": coarse,
            "current_status": None, "target_status": None, "needs_clarification": None, "mentioned_codes": []}
    pred.update(extra)
    return pred


def outcome(score, name: str):
    return score.metrics[name]


# ---------------------------------------------------------------------------
# Parent vs subcode
# ---------------------------------------------------------------------------
E74 = {"status_code": "E-7", "subcode": "E-7-4", "procedure": "extension"}


def test_exact_subcode_is_correct():
    score = score_item(example("status_procedure_classification", E74), cls_pred("E-7", "E-7-4", "extension"), CLS_ALL)
    assert outcome(score, "status_exact") == (CORRECT, "")
    assert outcome(score, "subcode_exact") == (CORRECT, "")
    assert outcome(score, "subcode_expected_present") == (CORRECT, "")
    assert score.primary_wrong() is False


def test_parent_answer_when_subcode_expected_is_wrong():
    score = score_item(example("status_procedure_classification", E74), cls_pred("E-7", None, "extension"), CLS_ALL)
    assert outcome(score, "status_exact")[0] == CORRECT
    assert outcome(score, "subcode_exact") == (WRONG, "parent_fallback")
    assert "parent_fallback" in score.flags
    assert score.primary_wrong() is True


def test_parent_written_into_subcode_field_is_wrong_even_when_no_subcode_expected():
    expected = {"status_code": "E-7", "subcode": None, "procedure": "extension"}
    score = score_item(example("status_procedure_classification", expected), cls_pred("E-7", "E-7", "extension"), CLS_ALL)
    assert outcome(score, "subcode_exact") == (WRONG, "parent_in_subcode_field")
    assert outcome(score, "subcode_expected_absent")[0] == WRONG


def test_subcode_is_never_credited_from_the_status_field():
    # The subcode appears only in status_code: status is wrong AND subcode is wrong.
    score = score_item(example("status_procedure_classification", E74), cls_pred("E-7-4", None, "extension"), CLS_ALL)
    assert outcome(score, "status_exact")[0] == WRONG
    assert outcome(score, "subcode_exact")[0] == WRONG


def test_sibling_subcode_is_wrong_with_reason():
    score = score_item(example("status_procedure_classification", E74), cls_pred("E-7", "E-7-1", "extension"), CLS_ALL)
    assert outcome(score, "subcode_exact") == (WRONG, "sibling_subcode")


def test_t_variant_is_a_subcode_of_its_parent():
    assert parent_of("F-2-T") == "F-2"
    expected = {"status_code": "F-2", "subcode": "F-2-T", "procedure": "extension"}
    score = score_item(example("status_procedure_classification", expected), cls_pred("F-2", None, "extension"), CLS_ALL)
    assert outcome(score, "subcode_exact") == (WRONG, "parent_fallback")


def test_subcode_not_emitted_is_not_scorable_not_wrong():
    score = score_item(example("status_procedure_classification", E74), cls_pred("E-7"), {"status_code"})
    assert outcome(score, "subcode_exact") == (NOT_SCORABLE, "not_emitted")
    assert outcome(score, "procedure_fine") == (NOT_SCORABLE, "not_emitted")


# ---------------------------------------------------------------------------
# Procedures: fine, coarse, scope
# ---------------------------------------------------------------------------
def test_coarse_only_baseline_is_not_scored_on_fine_procedure():
    score = score_item(example("status_procedure_classification", E74), cls_pred("E-7", coarse="extension"), CLS_COARSE)
    assert outcome(score, "procedure_fine") == (NOT_SCORABLE, "baseline_emits_coarse_only")
    assert outcome(score, "procedure_coarse") == (CORRECT, "")
    assert "procedure_coarse" in score.primary


def test_label_without_coarse_equivalent_is_not_scorable_for_coarse():
    expected = {"status_code": "D-2", "subcode": None, "procedure": "part_time_work"}
    score = score_item(example("status_procedure_classification", expected),
                       cls_pred("D-2", coarse="activities_outside_status"), CLS_COARSE)
    assert outcome(score, "procedure_coarse") == (NOT_SCORABLE, "no_coarse_equivalent")


def test_fine_prediction_is_mapped_to_coarse_for_the_coarse_metric():
    expected = {"status_code": "F-6", "subcode": None, "procedure": "residence_report"}
    score = score_item(example("status_procedure_classification", expected), cls_pred("F-6", fine="residence_report"),
                       CLS_ALL)
    assert outcome(score, "procedure_fine")[0] == CORRECT
    assert outcome(score, "procedure_coarse")[0] == CORRECT  # residence_report -> address_report


def test_visa_procedure_for_a_stay_question_is_flagged_as_scope_mixing():
    expected = {"status_code": "D-2", "subcode": None, "procedure": "extension"}
    score = score_item(example("status_procedure_classification", expected), cls_pred("D-2", fine="visa_issuance"),
                       CLS_ALL)
    assert outcome(score, "procedure_fine") == (WRONG, "visa_stay_scope_mixed")
    assert outcome(score, "procedure_scope_respected") == (WRONG, "visa_stay_scope_mixed")
    assert "procedure_scope_mixed" in score.flags


def test_invalid_structured_output_is_wrong_on_every_emitted_field():
    prediction, violations = parse_model_output("not json at all", "status_procedure_classification")
    assert prediction[INVALID_OUTPUT_FLAG] is True and violations
    score = score_item(example("status_procedure_classification", E74), prediction, CLS_ALL)
    assert outcome(score, "status_exact") == (WRONG, "invalid_structured_output")
    assert outcome(score, "subcode_exact") == (WRONG, "invalid_structured_output")


def test_clarification_precision_recall_counts():
    expected = {"status_code": None, "subcode": None, "procedure": None, "needs_clarification": True}
    asked = score_item(example("status_procedure_classification", expected),
                       cls_pred(needs_clarification=True), CLS_ALL)
    silent = score_item(example("status_procedure_classification", dict(expected, needs_clarification=False)),
                        cls_pred(needs_clarification=True), CLS_ALL)
    agg = aggregate([asked, silent], items=2)
    pr = agg["precision_recall"]["clarification"]
    assert (pr["tp"], pr["fp"], pr["fn"]) == (1, 1, 0)
    assert pr["precision"] == 0.5 and pr["recall"] == 1.0


def test_non_code_token_must_not_become_a_status():
    expected = {"status_code": None, "subcode": None, "procedure": "extension", "not_status_tokens": ["a 3"]}
    score = score_item(example("status_procedure_classification", expected), cls_pred("A-3", coarse="extension"),
                       CLS_COARSE)
    assert outcome(score, "not_status_token_respected")[0] == WRONG
    assert "code_from_non_code_token" in score.flags


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
DATES = {"dates": [{"value": "2026-03-02", "role": "conduct_date"}, {"value": "2026-09-30", "role": "stay_expiry_date"}]}


def test_dates_without_roles_are_scored_on_values_only():
    pred = {"dates": [{"value": "2026-03-02", "role": None}, {"value": "2026-01-01", "role": None}], "status_codes": []}
    score = score_item(example("entity_date_extraction", DATES), pred, {"dates", "status_codes"})
    assert outcome(score, "dates_exact") == (NOT_SCORABLE, "roles_not_emitted")
    assert outcome(score, "dates_value_exact")[0] == WRONG
    counts = score.counts["dates_value_only"]
    assert (counts["tp"], counts["fp"], counts["fn"]) == (1, 1, 1)
    assert "dates_value_role" not in score.counts


def test_dates_with_roles_need_value_and_role():
    pred = {"dates": [{"value": "2026-03-02", "role": "conduct_date"}, {"value": "2026-09-30", "role": "decision_date"}]}
    score = score_item(example("entity_date_extraction", DATES), pred, {"dates", "date_roles"})
    assert outcome(score, "dates_value_exact")[0] == CORRECT
    assert outcome(score, "dates_exact")[0] == WRONG
    assert score.counts["dates_value_role"]["tp"] == 1


# ---------------------------------------------------------------------------
# Citation verification
# ---------------------------------------------------------------------------
UNAVAILABLE = {"overall": "verification_unavailable", "layer_codes": {"source_identity": "verification_unavailable"},
               "forbidden_codes": ["source_not_found"]}


def cit_pred(overall: str, layers: Dict[str, str]) -> Dict[str, Any]:
    return {"overall": overall, "layer_codes": layers, "codes": sorted(set(layers.values())),
            "highest_verified_layer": 0, "injection_flagged": False}


def test_absence_on_an_unavailable_item_is_a_false_absence_declaration():
    score = score_item(example("citation_verification", UNAVAILABLE),
                       cit_pred("failed", {"source_identity": "source_not_found"}), CIT_ALL)
    assert outcome(score, "false_absence") == (WRONG, "source_not_found")
    assert outcome(score, "forbidden_codes_absent") == (WRONG, "source_not_found")
    assert "false_absence_declaration" in score.flags
    assert critical_categories({"critical": False}, score.flags, score.primary_wrong()) == ["false_absence_declaration"]


def test_unavailable_answer_on_an_unavailable_item_is_not_a_false_absence():
    score = score_item(example("citation_verification", UNAVAILABLE),
                       cit_pred("verification_unavailable", {"source_identity": "verification_unavailable"}), CIT_ALL)
    assert outcome(score, "false_absence")[0] == CORRECT
    assert outcome(score, "overall_status")[0] == CORRECT
    assert "false_absence_declaration" not in score.flags


def test_forbidding_an_absence_code_does_not_make_an_item_an_unavailability_item():
    # The source exists (repealed); declaring it absent is wrong, but it is not
    # a lookup failure presented as absence.
    expected = {"overall": "failed", "layer_codes": {"source_identity": "source_repealed"},
                "forbidden_codes": ["source_verified", "source_not_found"]}
    score = score_item(example("citation_verification", expected),
                       cit_pred("failed", {"source_identity": "source_not_found"}), CIT_ALL)
    assert outcome(score, "false_absence") == (NOT_SCORABLE, "label_not_unavailable")
    assert outcome(score, "unsupported_absence") == (WRONG, "source_not_found")
    assert outcome(score, "forbidden_codes_absent") == (WRONG, "source_not_found")
    assert "false_absence_declaration" not in score.flags


def test_partial_index_label_makes_an_absence_a_false_absence():
    expected = {"overall": "verification_unavailable",
                "layer_codes": {"source_identity": "historical_lookup_required"}}
    score = score_item(example("citation_verification", expected),
                       cit_pred("failed", {"source_identity": "source_not_found"}), CIT_ALL)
    assert outcome(score, "false_absence") == (WRONG, "source_not_found")


def test_absence_the_label_itself_asserts_is_not_false():
    expected = {"overall": "failed", "layer_codes": {"source_identity": "source_not_found"}}
    score = score_item(example("citation_verification", expected),
                       cit_pred("failed", {"source_identity": "source_not_found"}), CIT_ALL)
    assert outcome(score, "false_absence") == (NOT_SCORABLE, "label_not_unavailable")
    assert outcome(score, "unsupported_absence")[0] == CORRECT


def test_accepting_a_future_version_is_counted_per_code():
    expected = {"overall": "failed", "layer_codes": {"source_identity": "source_verified",
                                                     "version_identity": "future_not_yet_effective"}}
    score = score_item(example("citation_verification", expected),
                       cit_pred("verified_partial", {"source_identity": "source_verified",
                                                     "citation_identity": "citation_verified"}),
                       {"overall", "layer_codes", "codes"})
    assert outcome(score, "version_failure_rejected") == (WRONG, "future_not_yet_effective")
    assert outcome(score, "version_failure_rejected:future_not_yet_effective") == (WRONG, "accepted")
    assert outcome(score, "version_failure_rejected:wrong_version")[0] == NOT_SCORABLE
    assert outcome(score, "wrong_version_detected") == (WRONG, "layer_not_reported")   # no L2 = not detected
    assert outcome(score, "unsupported_claim_rejected") == (WRONG, "accepted")
    assert set(critical_categories({"critical": True}, score.flags, score.primary_wrong())) == {
        "accepted_future_not_yet_effective", "critical_example_wrong"}


def test_layer_agreement_counts_only_reported_layers():
    expected = {"overall": "failed", "layer_codes": {"source_identity": "source_verified",
                                                     "citation_identity": "citation_not_found"}}
    score = score_item(example("citation_verification", expected),
                       cit_pred("verified_partial", {"source_identity": "source_verified"}), CIT_ALL)
    assert outcome(score, "layer_code:source_identity")[0] == CORRECT
    assert outcome(score, "layer_code:citation_identity") == (NOT_SCORABLE, "layer_not_reported")


def test_baseline_crash_makes_every_metric_not_scorable_with_reason():
    score = score_item(example("citation_verification", UNAVAILABLE), None, CIT_ALL, error="boom")
    assert {o for o, _ in score.metrics.values()} == {NOT_SCORABLE}
    assert outcome(score, "overall_status") == (NOT_SCORABLE, "baseline_error")
    assert score.primary_wrong() is None and score.flags == []


def test_not_equivalent_input_reason_is_kept():
    score = score_item(example("status_procedure_classification", E74), None, CLS_ALL, reason="not_equivalent_input")
    assert outcome(score, "status_exact") == (NOT_SCORABLE, "not_equivalent_input")


# ---------------------------------------------------------------------------
# Temporal and abstention
# ---------------------------------------------------------------------------
def test_temporal_candidates_and_warnings():
    expected = {"candidate_version_keys": [["289833", "2026-09-15"]], "warnings": ["future_version_pending"],
                "forbidden_warnings": ["anchor_missing"]}
    good = score_item(example("temporal_version_selection", expected),
                      {"candidate_version_keys": [("289833", "2026-09-15")], "warnings": ["future_version_pending"],
                       "determination": "candidate_only"},
                      {"candidate_version_keys", "warnings", "determination"})
    assert good.primary_wrong() is False
    bad = score_item(example("temporal_version_selection", expected),
                     {"candidate_version_keys": [], "warnings": ["anchor_missing"], "determination": "candidate_only"},
                     {"candidate_version_keys", "warnings", "determination"})
    assert outcome(bad, "candidates_exact")[0] == WRONG
    assert outcome(bad, "warnings_all_present") == (WRONG, "future_version_pending")
    assert outcome(bad, "forbidden_warnings_absent") == (WRONG, "anchor_missing")
    agg = aggregate([good, bad], items=2)
    assert agg["precision_recall"]["warning_recall"]["recall"] == 0.5


def test_forbidden_assertion_needs_exact_match_never_similarity():
    expected = {"must_withhold_conclusion": True, "required_issue_keys": ["anchor_missing"],
                "forbidden_assertions": ["허가를 받을 수 있습니다"]}
    near = {"conclusion_withheld": True, "issues": ["anchor_missing"],
            "claims": [{"text": "허가를 받을 수 있습니다!", "assertion_key": None}]}
    score = score_item(example("abstention", expected), near, {"conclusion_withheld", "issues", "claims"})
    assert outcome(score, "forbidden_assertions_absent")[0] == CORRECT  # punctuation differs: not a hit
    exact = dict(near, claims=[{"text": "허가를 받을 수  있습니다", "assertion_key": None}])
    score = score_item(example("abstention", expected), exact, {"conclusion_withheld", "issues", "claims"})
    assert outcome(score, "forbidden_assertions_absent")[0] == WRONG  # whitespace-normalized equality


# ---------------------------------------------------------------------------
# Aggregation, headline, performance
# ---------------------------------------------------------------------------
def test_not_scorable_items_never_enter_a_denominator():
    scorable = score_item(example("status_procedure_classification", E74), cls_pred("E-7", "E-7-4", "extension"), CLS_ALL)
    crashed = score_item(example("status_procedure_classification", E74), None, CLS_ALL, error="x")
    agg = aggregate([scorable, crashed], errors=1, items=2)
    tally = agg["metrics"]["status_exact"]
    assert (tally["correct"], tally["wrong"], tally["denominator"], tally["not_scorable"]) == (1, 0, 1, 1)
    assert tally["accuracy"] == 1.0
    assert tally["reasons"] == {"not_scorable:baseline_error": 1}
    entry = headline({"status_procedure_classification": agg})["classification.status_exact_accuracy"]
    assert (entry["numerator"], entry["denominator"], entry["not_scorable"]) == (1, 1, 1)


def test_zero_denominator_gives_no_rate():
    crashed = score_item(example("status_procedure_classification", E74), None, CLS_ALL, error="x")
    agg = aggregate([crashed], errors=1, items=1)
    assert agg["metrics"]["status_exact"]["accuracy"] is None


def test_performance_uses_nearest_rank_percentiles():
    perf = performance([{"latency_ms": v, "upstream_calls": 1, "peak_memory_bytes": 10, "memory_kind": "k"}
                        for v in (5.0, 1.0, 3.0, 2.0, 4.0)])
    assert perf["latency_ms"]["p50"] == 3.0 and perf["latency_ms"]["p95"] == 5.0
    assert perf["upstream_calls"]["total"] == 5 and perf["tokens"] is None


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------
def _gate(report, gate_id):
    return next(row for row in report["gates"] if row["id"] == gate_id)


def _extras(**over):
    base = {"errors": 0, "applicable": 4, "critical": 0, "scored": 4, "critical_label_review": {"human_verified": 2}}
    base.update(over)
    return base


def test_hard_gate_with_empty_denominator_is_insufficient_not_pass():
    head = {"citation.false_absence_declarations": {"kind": "count", "value": None, "numerator": 0,
                                                    "denominator": 0, "not_scorable": 3}}
    report = gates.evaluate_gates(head, _extras(), ["test"])
    assert _gate(report, "HG-1")["status"] == gates.INSUFFICIENT
    assert report["decision"] == gates.INSUFFICIENT_EVIDENCE


def test_one_false_absence_is_no_go():
    head = {"citation.false_absence_declarations": {"kind": "count", "value": None, "numerator": 1,
                                                    "denominator": 5, "not_scorable": 0}}
    report = gates.evaluate_gates(head, _extras(), ["test", "adversarial_holdout"])
    assert _gate(report, "HG-1")["status"] == gates.FAIL
    assert report["decision"] == gates.NO_GO


def test_dev_only_run_cannot_decide():
    report = gates.evaluate_gates({}, _extras(), ["dev"])
    assert report["decision_splits"] == [] and report["decision"] == gates.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize("labels, decision", [({"human_verified": 2}, gates.GO),
                                              ({"machine_checked": 1, "human_verified": 1}, gates.PROVISIONAL_GO)])
def test_unverified_critical_labels_cap_the_decision(labels, decision):
    head = {"classification.procedure_scope_violations": {"kind": "count", "value": None, "numerator": 0,
                                                          "denominator": 4, "not_scorable": 0},
            "classification.status_exact_accuracy": {"kind": "accuracy", "value": 1.0, "numerator": 4,
                                                     "denominator": 4, "not_scorable": 0},
            "classification.subcode_accuracy_subcode_expected": {"kind": "accuracy", "value": 1.0, "numerator": 2,
                                                                 "denominator": 2, "not_scorable": 0}}
    report = gates.evaluate_gates(head, _extras(critical_label_review=labels), ["test"])
    assert report["decision"] == decision


def test_soft_gate_failure_holds():
    head = {"classification.procedure_scope_violations": {"kind": "count", "value": None, "numerator": 0,
                                                          "denominator": 4, "not_scorable": 0},
            "classification.status_exact_accuracy": {"kind": "accuracy", "value": 0.5, "numerator": 2,
                                                     "denominator": 4, "not_scorable": 0}}
    report = gates.evaluate_gates(head, _extras(), ["test"])
    assert _gate(report, "SG-5")["status"] == gates.FAIL
    assert report["decision"] == gates.HOLD


# ---------------------------------------------------------------------------
# Intervals, hierarchy count, emission, model format, timing gates
# ---------------------------------------------------------------------------
def test_wilson_interval_is_never_zero_width_at_the_extremes():
    from waymaker_ai.evaluation.summary import wilson_interval

    assert wilson_interval(0, 0) is None
    low, high = wilson_interval(10, 10)
    assert high == 1.0 and 0.65 < low < 0.75   # 10/10 is not proof of 100%
    low, high = wilson_interval(0, 10)
    assert low == 0.0 and 0.25 < high < 0.35
    low, high = wilson_interval(5, 10)
    assert low < 0.5 < high


def test_headline_accuracy_carries_its_interval():
    good = score_item(example("status_procedure_classification", E74), cls_pred("E-7", "E-7-4", "extension"), CLS_ALL)
    entry = headline({"status_procedure_classification": aggregate([good], items=1)})[
        "classification.status_exact_accuracy"]
    assert entry["value"] == 1.0 and entry["ci95"][1] == 1.0 and entry["ci95"][0] < 1.0


def test_hierarchy_violations_count_parent_fallback_and_parent_in_subcode_field():
    fallback = score_item(example("status_procedure_classification", E74), cls_pred("E-7", None, "extension"), CLS_ALL)
    in_field = score_item(example("status_procedure_classification",
                                  {"status_code": "G-1", "subcode": None, "procedure": "extension"}, ident="ex-0002"),
                          cls_pred("G-1", "G-1", "extension"), CLS_ALL)
    sibling = score_item(example("status_procedure_classification", E74, ident="ex-0003"),
                         cls_pred("E-7", "E-7-1", "extension"), CLS_ALL)
    entry = headline({"status_procedure_classification": aggregate([fallback, in_field, sibling], items=3)})[
        "classification.hierarchy_violations"]
    assert (entry["numerator"], entry["denominator"]) == (2, 3)   # a sibling subcode is wrong, not a hierarchy error
    report = gates.evaluate_gates({"classification.hierarchy_violations": entry}, _extras(), ["test"])
    assert _gate(report, "HG-10")["status"] == gates.FAIL and report["decision"] == gates.NO_GO


def test_a_field_the_baseline_cannot_emit_is_not_applicable_for_gates():
    coarse_only = score_item(example("status_procedure_classification", E74),
                             cls_pred("E-7", coarse="extension"), CLS_COARSE)
    head = headline({"status_procedure_classification": aggregate([coarse_only], items=1)})
    assert head["classification.procedure_fine_accuracy"]["baseline_cannot_emit"] is True
    report = gates.evaluate_gates(head, _extras(), ["test"])
    assert _gate(report, "SG-7")["status"] == gates.NOT_APPLICABLE


def test_empty_denominator_for_another_reason_is_still_insufficient():
    crashed = score_item(example("status_procedure_classification", E74), None, CLS_ALL, error="boom")
    head = headline({"status_procedure_classification": aggregate([crashed], errors=1, items=1)})
    assert head["classification.procedure_fine_accuracy"]["baseline_cannot_emit"] is False
    assert _gate(gates.evaluate_gates(head, _extras(), ["test"]), "SG-7")["status"] == gates.INSUFFICIENT


def test_model_answers_are_scored_for_contract_validity():
    from waymaker_ai.evaluation.predictions import SCHEMA_VIOLATIONS_KEY

    prediction, violations = parse_model_output('{"status_code": "E-7-4", "extra": 1}', "status_procedure_classification")
    prediction[SCHEMA_VIOLATIONS_KEY] = len(violations)
    score = score_item(example("status_procedure_classification", E74), prediction, CLS_ALL)
    assert outcome(score, "structured_output_valid")[0] == WRONG
    assert "status_code is not a 2-segment parent code" in violations and "unexpected key extra" in violations
    # Deterministic baselines never carry the key, so the metric does not exist for them.
    plain = score_item(example("status_procedure_classification", E74), cls_pred("E-7", "E-7-4", "extension"), CLS_ALL)
    assert "structured_output_valid" not in plain.metrics


def test_timing_gates_are_reported_but_never_decide():
    head = {"classification.procedure_scope_violations": {"kind": "count", "value": None, "numerator": 0,
                                                          "denominator": 4, "not_scorable": 0},
            "performance.latency_p95_ms": {"kind": "value", "value": 99999.0, "numerator": None,
                                           "denominator": 4, "not_scorable": 0}}
    report = gates.evaluate_gates(head, _extras(), ["test"])
    assert report["performance_gates"][0]["status"] == gates.FAIL
    assert report["decision"] == gates.GO


def test_any_unverified_scored_label_caps_go_even_when_critical_labels_are_verified():
    head = {"classification.procedure_scope_violations": {"kind": "count", "value": None, "numerator": 0,
                                                          "denominator": 4, "not_scorable": 0}}
    extras = _extras(label_review={"human_verified": 3, "machine_checked": 1})
    report = gates.evaluate_gates(head, extras, ["test"])
    assert report["labels_unverified"] == 1 and report["decision"] == gates.PROVISIONAL_GO
