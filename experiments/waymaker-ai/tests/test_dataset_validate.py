"""Per-record, evidence and cross-record rules of the dataset validator.

Every test starts from one example of tests/fixtures_dataset/examples/
minimal_valid.jsonl (which passes with no issue at all), changes one thing, and
asserts that exactly the expected rule fires. The examples run in memory; the
only files read are the fixtures, visa_data.json (read-only) and, where a test
says so, data/manual_approval_index.json (read-only).
"""
from __future__ import annotations

import copy
import functools
from dataclasses import replace
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import pytest

from waymaker_ai.dataset import validate as v
from waymaker_ai.dataset.validate import (
    ERROR,
    WARNING,
    Options,
    Record,
    Registry,
    Report,
    Resources,
    summarize_bundle,
    validate_paths,
    validate_records,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures_dataset"
OPTIONS = Options(
    registry_dir=FIXTURES / "registry",
    sources_dir=FIXTURES / "sources",
    manual_index_path=FIXTURES / "config" / "manual_approval_index.json",
    teacher_policy_path=FIXTURES / "config" / "teacher_policy.json",
)
DELETE = object()

CLASSIFY = "fx-class-e74-extension"
EXTRACT = "fx-extract-dates-en"
CITE = "fx-cite-syn-article3"
CITE_TIMEOUT = "fx-cite-syn-timeout"
TEMPORAL = "fx-temporal-syn-article3"
TEMPORAL_REAL = "fx-temporal-rule73-pending"
ABSTAIN = "fx-abstain-missing-annex"
LAW_REF = "fx-class-rule73-no-status"
TEACHER = "fx-class-teacher-d21-reissue"
GUIDANCE = "fx-class-f1-guidance"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def _base_examples() -> Dict[str, Dict[str, Any]]:
    lines = (FIXTURES / "examples" / "minimal_valid.jsonl").read_text(encoding="utf-8").splitlines()
    examples = [json.loads(line) for line in lines if line.strip()]
    return {example["id"]: example for example in examples}


def example(example_id: str, changes: Optional[Mapping[str, Any]] = None, **renamed: Any) -> Dict[str, Any]:
    """A deep copy of a base example with dotted-path changes applied ("expected.subcode": "E-7-1")."""
    data = copy.deepcopy(_base_examples()[example_id])
    for path, value in {**(changes or {}), **renamed}.items():
        _set(data, path, value)
    return data


def _set(data: Dict[str, Any], path: str, value: Any) -> None:
    *parents, last = path.split(".")
    target: Any = data
    for key in parents:
        target = target.setdefault(key, {})
    if value is DELETE:
        target.pop(last, None)
    else:
        target[last] = value


def run(*examples: Mapping[str, Any], options: Options = OPTIONS, bundles: Optional[Mapping[str, Any]] = None,
        registry: Optional[Registry] = None) -> Report:
    records = [Record("mem.jsonl", index + 1, "line", data) for index, data in enumerate(examples)]
    resources = Resources(options)
    if registry is not None:
        resources.registry = registry
    for bundle_id, data in (bundles or {}).items():
        resources.add_bundle(bundle_id, summarize_bundle(bundle_id, f"mem/{bundle_id}.json", data, resources.registry))
    return validate_records(records, options, resources=resources)


def fired(report: Report, severity: str = ERROR) -> List[str]:
    return report.rules(severity)


def messages(report: Report, rule: str, severity: Optional[str] = None) -> List[str]:
    return [i.message for i in report.issues if i.rule == rule and (severity is None or i.severity == severity)]


def paths(report: Report, rule: str) -> List[str]:
    return [i.path for i in report.issues if i.rule == rule]


def assert_only(report: Report, rule: str, severity: str = ERROR) -> None:
    """Exactly this rule fired (at this severity) and nothing else at all."""
    assert report.rules() == [rule], [i.render() for i in report.issues]
    assert all(i.severity == severity for i in report.issues), [i.render() for i in report.issues]


def assert_clean(report: Report) -> None:
    assert report.issues == [], [i.render() for i in report.issues]


def load_bundle_data(bundle_id: str) -> Dict[str, Any]:
    return json.loads((FIXTURES / "sources" / f"{bundle_id}.json").read_text(encoding="utf-8"))


def bundle_problems(data: Mapping[str, Any], bundle_id: Optional[str] = None, registry: Optional[Registry] = None) -> List[str]:
    registry = registry or v.load_registry(FIXTURES / "registry")
    info = summarize_bundle(bundle_id or str(data.get("bundle_id")), "mem.json", data, registry)
    return list(info.problems)


# ---------------------------------------------------------------------------
# The passing fixture
# ---------------------------------------------------------------------------
def test_minimal_fixture_file_passes_without_any_issue():
    report = validate_paths([FIXTURES / "examples"], OPTIONS)
    assert_clean(report)
    assert report.ok and report.example_count == 10
    assert report.counts["task"] == {
        "abstention": 1,
        "citation_verification": 2,
        "entity_date_extraction": 1,
        "status_procedure_classification": 4,
        "temporal_version_selection": 2,
    }


@pytest.mark.parametrize("example_id", sorted(_base_examples()))
def test_every_base_example_passes_on_its_own(example_id):
    assert_clean(run(example(example_id)))


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "changes, path",
    [
        ({"split": DELETE}, "split"),
        ({"surprise": 1}, "surprise"),
        ({"schema_version": "waymaker-example/0.2"}, "schema_version"),
        ({"id": "UPPER-case"}, "id"),
        ({"id": "abc"}, "id"),
        ({"language": "korean"}, "language"),
        ({"provenance.created_at": "20261019"}, "provenance.created_at"),
        ({"provenance.contains_personal_data": True}, "provenance.contains_personal_data"),
        ({"revision": 0, "revision_history": [{"revision": 0, "date": "2026-10-19", "change": "x"}]}, "revision"),
        ({"scenario.adversarial_class": "Z"}, "scenario.adversarial_class"),
        ({"source_refs": [{"kind": "wiki", "ref": "x"}]}, "source_refs[0].kind"),
        ({"critical": "no"}, "critical"),
    ],
)
def test_schema_violations(changes, path):
    report = run(example(CLASSIFY, changes))
    assert "schema" in fired(report)
    assert path in paths(report, "schema")


def test_relevant_date_values_must_be_dates():
    report = run(example(CITE, {"scenario.relevant_dates.question_date": "2026-10-32"}))
    assert "scenario.relevant_dates.question_date" in paths(report, "schema")


def test_suite_must_match_task():
    assert_only(run(example(CLASSIFY, suite="temporal")), "suite_task")


# ---------------------------------------------------------------------------
# Expected keys and values (TASK_EXPECTED_KEYS and contracts.py enums)
# ---------------------------------------------------------------------------
def test_missing_required_expected_key():
    report = run(example(CLASSIFY, {"expected.procedure": DELETE}))
    assert_only(report, "expected_keys")
    assert paths(report, "expected_keys") == ["expected.procedure"]


def test_unknown_expected_key_for_the_task():
    report = run(example(CLASSIFY, {"expected.overall": "verified"}))
    assert_only(report, "expected_keys")


@pytest.mark.parametrize(
    "example_id, changes",
    [
        (CLASSIFY, {"expected.procedure": "visa_extension"}),
        (CLASSIFY, {"expected.needs_clarification": "yes"}),
        (CLASSIFY, {"expected.status_code": 7}),
        (EXTRACT, {"expected.dates": [{"value": "2026-10-19", "role": "today"}]}),
        (EXTRACT, {"expected.dates": [{"value": "19/10/2026", "role": "question_date"}]}),
        (EXTRACT, {"expected.dates": "2026-10-19"}),
        (CITE, {"expected.overall": "mostly_verified"}),
        (CITE, {"expected.layer_codes": {"source_identity": "looks_fine"}}),
        (CITE, {"expected.layer_codes": {"layer_9": "source_verified"}}),
        (CITE, {"expected.forbidden_codes": ["source_missing"]}),
        (CITE, {"expected.forbidden_codes": ["citation_verified"]}),
        (CITE, {"expected.max_highest_verified_layer": 8}),
        (CITE, {"expected.injection_flagged": "no"}),
        (TEMPORAL, {"expected.warnings": ["maybe_stale"]}),
        (TEMPORAL, {"expected.forbidden_warnings": ["transitional_provisions_unreviewed"]}),
        (TEMPORAL, {"expected.determination": "final"}),
        (TEMPORAL, {"expected.candidate_version_keys": [["SYN-V1"]]}),
        (TEMPORAL, {"expected.candidate_version_keys": [["SYN-V1", "2026/01/01"]]}),
        (ABSTAIN, {"expected.must_withhold_conclusion": "true"}),
        (ABSTAIN, {"expected.required_issue_keys": "source_not_in_evidence"}),
    ],
)
def test_expected_values_are_checked_against_the_contracts(example_id, changes):
    assert "expected_value" in fired(run(example(example_id, changes)))


ALL_PASS_CODES = {
    "source_identity": "source_verified",
    "version_identity": "version_verified",
    "citation_identity": "citation_verified",
    "text_correspondence": "not_checked",
    "claim_support": "claim_supported",
    "applicability": "applicability_established",
    "conflict_uncertainty": "no_conflict_detected",
}


def test_layer_code_tables_cover_the_whole_contract():
    from waymaker_ai.contracts import VerificationCode, VerificationLayer

    assert set(v.CODE_OUTCOMES) == {code.value for code in VerificationCode}
    assert set(v.LAYER_CODES) == {layer.value for layer in VerificationLayer}
    placed = set().union(*v.LAYER_CODES.values()) | v.ANY_LAYER_CODES
    assert placed == {code.value for code in VerificationCode}


@pytest.mark.parametrize(
    "layer_codes",
    [
        {"citation_identity": "source_verified"},
        {"source_identity": "citation_not_found"},
        {"conflict_uncertainty": "text_mismatch"},
    ],
)
def test_a_code_must_belong_to_its_layer(layer_codes):
    report = run(example(CITE, {"expected.overall": "failed", "expected.layer_codes": layer_codes}))
    assert_only(report, "layer_codes")
    assert paths(report, "layer_codes") == [f"expected.layer_codes.{next(iter(layer_codes))}"]


def test_cross_layer_codes_that_07_uses_are_accepted():
    # 07 §3: L2 reports insufficient_context when the anchor date is unknown; any layer may report the generic codes.
    layer_codes = {"source_identity": "source_verified", "version_identity": "insufficient_context", "claim_support": "not_checked"}
    assert_clean(run(example(CITE, {"expected.overall": "human_review_required", "expected.layer_codes": layer_codes})))


@pytest.mark.parametrize(
    "layer_codes, overall",
    [
        ({"citation_identity": "citation_not_found"}, "verified"),
        ({"citation_identity": "citation_not_found"}, "verification_unavailable"),
        ({"source_identity": "historical_lookup_required"}, "human_review_required"),
        ({"claim_support": "claim_partially_supported"}, "verified_partial"),
        (ALL_PASS_CODES, "verified_partial"),
        (dict(ALL_PASS_CODES, applicability="subcode_applicability_unproven"), "verification_unavailable"),
    ],
)
def test_overall_must_follow_from_the_layer_codes(layer_codes, overall):
    report = run(example(CITE, {"expected.overall": overall, "expected.layer_codes": layer_codes}))
    assert_only(report, "layer_codes")
    assert paths(report, "layer_codes") == ["expected.overall"]


@pytest.mark.parametrize(
    "layer_codes, overall",
    [
        (ALL_PASS_CODES, "verified"),
        ({"source_identity": "source_verified"}, "verified"),            # unlisted layers may complete it
        ({"source_identity": "source_verified"}, "verified_partial"),
        ({"claim_support": "claim_partially_supported"}, "failed"),      # an unlisted layer may fail
        (dict(ALL_PASS_CODES, applicability="subcode_applicability_unproven"), "failed"),
        (dict(ALL_PASS_CODES, applicability="subcode_applicability_unproven"), "human_review_required"),
    ],
)
def test_overall_consistent_with_the_layer_codes_passes(layer_codes, overall):
    assert_clean(run(example(CITE, {"expected.overall": overall, "expected.layer_codes": layer_codes})))


def test_achievable_overalls_uses_the_contract_roll_up():
    assert v.achievable_overalls(ALL_PASS_CODES) == {"verified"}
    assert v.achievable_overalls({"citation_identity": "verification_unavailable"}) == {"failed", "verification_unavailable"}


def test_not_status_tokens_must_occur_in_the_question():
    ok = example(CLASSIFY, {"expected.not_status_tokens": ["체류기간"]})
    assert_clean(run(ok))
    bad = example(CLASSIFY, {"expected.not_status_tokens": ["a 3"]})
    assert_only(run(bad), "expected_value")


# ---------------------------------------------------------------------------
# Input shape and scenario
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "example_id, changes, path",
    [
        (CLASSIFY, {"input.claim": {"text": "x", "citations": []}}, "input.claim"),
        (CITE, {"input.temporal_query": {"stable_id": "SYN-LAW-0001", "anchor": "question_date"}}, "input.temporal_query"),
        (CITE, {"input.claim": DELETE}, "input.claim"),
        (CITE, {"input.claim.scope": {"procedures": ["visa"]}}, "input.claim.scope.procedures[0]"),
        (CITE, {"input.claim.scope": {"status_codes": "E-7"}}, "input.claim.scope.status_codes"),
        (CITE, {"input.claim.scope": {"all_subcodes_explicit": "yes"}}, "input.claim.scope.all_subcodes_explicit"),
        (CITE, {"input.claim.asserted_version_key": ["SYN-V1", "soon"]}, "input.claim.asserted_version_key"),
        (TEMPORAL, {"input.temporal_query.secondary_anchors": ["birthday"]}, "input.temporal_query.secondary_anchors[0]"),
    ],
)
def test_input_shape(example_id, changes, path):
    report = run(example(example_id, changes))
    assert path in paths(report, "input_shape"), [i.render() for i in report.issues]


def test_bundle_tasks_must_name_their_fixture_set():
    report = run(example(CITE, {"input.fixture_set": DELETE}))
    assert "input.fixture_set" in paths(report, "input_shape")


def test_temporal_query_anchor_must_be_an_anchor_kind():
    report = run(example(TEMPORAL, {"input.temporal_query.anchor": "today"}))
    assert "input.temporal_query.anchor" in paths(report, "input_shape")


@pytest.mark.parametrize(
    "example_id, changes, path",
    [
        (CLASSIFY, {"scenario.anchor": "today"}, "scenario.anchor"),
        (CLASSIFY, {"scenario.relevant_dates": {"birth_date": "2000-01-01"}}, "scenario.relevant_dates.birth_date"),
        (CITE, {"scenario.relevant_dates": {}}, "scenario.relevant_dates.question_date"),
        (TEMPORAL, {"scenario.relevant_dates": {"conduct_date": "2026-01-02"}}, "scenario.relevant_dates.question_date"),
    ],
)
def test_scenario_rules(example_id, changes, path):
    assert path in paths(run(example(example_id, changes)), "scenario")


# ---------------------------------------------------------------------------
# Temporal labels against the normative resolver (06 §3) and the bundle
# ---------------------------------------------------------------------------
def test_temporal_anchor_must_agree_with_the_scenario_anchor():
    report = run(example(TEMPORAL, {"scenario.anchor": "conduct_date", "scenario.relevant_dates.conduct_date": "2026-03-01"}))
    assert_only(report, "temporal_label")


def test_missing_anchor_date_means_no_candidate_and_anchor_missing():
    changes = {"input.temporal_query.anchor": "conduct_date", "scenario.anchor": "conduct_date"}
    report = run(example(TEMPORAL, changes))
    assert sorted(paths(report, "temporal_label")) == ["expected.candidate_version_keys", "expected.warnings"]
    fixed = example(TEMPORAL, {**changes, "expected.candidate_version_keys": [], "expected.warnings": ["anchor_missing"]})
    assert_clean(run(fixed))


def test_history_fault_means_no_candidate_and_version_history_unavailable():
    bundle = load_bundle_data("syn-basic")
    bundle["bundle_id"] = "syn-history-down"
    bundle["faults"] = [{"operation": "list_versions", "match": {"stable_id": "SYN-LAW-0001"}, "status": "unavailable_rate_limited",
                         "raw_body_kind": "http_429", "detail": "synthetic 429"}]
    report = run(example(TEMPORAL, {"input.fixture_set": "syn-history-down"}), bundles={"syn-history-down": bundle})
    assert sorted(paths(report, "temporal_label")) == ["expected.candidate_version_keys", "expected.warnings"]
    assert all("version_history_unavailable" in m or "list_versions" in m for m in messages(report, "temporal_label"))


def test_not_found_history_is_not_a_failure():
    bundle = load_bundle_data("syn-basic")
    bundle["bundle_id"] = "syn-history-empty"
    bundle["faults"] = [{"operation": "list_versions", "match": {"stable_id": "SYN-LAW-0001"}, "status": "not_found",
                         "raw_body_kind": None, "detail": "authoritative empty answer"}]
    assert_clean(run(example(TEMPORAL, {"input.fixture_set": "syn-history-empty"}), bundles={"syn-history-empty": bundle}))


def test_temporal_stable_id_and_candidates_must_exist_in_the_bundle():
    report = run(example(TEMPORAL, {"input.temporal_query.stable_id": "SYN-LAW-0002"}))
    assert paths(report, "temporal_label") == ["input.temporal_query.stable_id"]
    report = run(example(TEMPORAL, {"expected.candidate_version_keys": [["SYN-V2", "2027-01-01"]]}))
    assert paths(report, "temporal_label") == ["expected.candidate_version_keys[0]"]


# ---------------------------------------------------------------------------
# Hard negatives and split policy
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("split", ["train", "dev"])
def test_adversarial_examples_belong_in_test_or_holdout(split):
    assert_only(run(example(CITE_TIMEOUT, split=split)), "hard_negative")


@pytest.mark.parametrize(
    "example_id, changes",
    [
        (CITE, {"scenario.adversarial_class": "C"}),
        (CITE_TIMEOUT, {"expected.overall": "verified", "expected.forbidden_codes": []}),
        (TEMPORAL, {"scenario.adversarial_class": "D", "expected.warnings": []}),
        (ABSTAIN, {"expected.must_withhold_conclusion": False}),
    ],
)
def test_adversarial_examples_must_not_expect_a_clean_pass(example_id, changes):
    report = run(example(example_id, changes))
    assert "hard_negative" in fired(report)
    assert "expected" in paths(report, "hard_negative")


def test_adversarial_classification_needs_only_the_split_rule():
    report = run(example(CLASSIFY, {"scenario.adversarial_class": "I", "split": "test"}))
    assert_clean(report)


def test_holdout_without_adversarial_class_is_a_warning():
    assert_only(run(example(CITE, split="adversarial_holdout")), "split_policy", WARNING)


def test_teacher_output_in_an_eval_split_must_be_human_verified():
    assert_only(run(example(TEACHER, split="test")), "split_policy")
    verified = example(TEACHER, {
        "split": "test",
        "label_review.status": "human_verified",
        "label_review.reviewer": "fixture-reviewer",
        "label_review.reviewed_at": "2026-10-19",
    })
    assert_clean(run(verified))


# ---------------------------------------------------------------------------
# Status codes: inventory and hierarchy (visa_data.json, read-only)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "example_id, changes, path",
    [
        (CLASSIFY, {"expected.subcode": "E-7-04"}, "expected.subcode"),
        (CLASSIFY, {"expected.current_status": "Z-9"}, "expected.current_status"),
        (CLASSIFY, {"source_refs": [{"kind": "visa_data", "ref": "E-7-99"}]}, "source_refs[0].ref"),
        (GUIDANCE, {"source_refs": [{"kind": "status_guidance", "ref": "F-9~relative-visit"}]}, "source_refs[0].ref"),
        (EXTRACT, {"expected.status_codes": ["D-2", "d-2"]}, "expected.status_codes[1]"),
    ],
)
def test_codes_must_exist_in_the_inventory(example_id, changes, path):
    report = run(example(example_id, changes))
    assert paths(report, "inventory") == [path]


def test_inventory_messages_never_echo_personal_data():
    report = run(example(CLASSIFY, {"expected.current_status": "010-1234-5678"}))
    inventory_messages = messages(report, "inventory")
    assert inventory_messages and all("withheld" in m and "1234" not in m for m in inventory_messages)


@pytest.mark.parametrize(
    "status, subcode, message_part",
    [
        ("E-7", "E-7", "repeats status_code"),
        (None, "E-7-4", "status_code is null"),
        ("E-7-4", None, "is a subcode"),
        ("G-1-5", None, "is a subcode"),
        ("E-7", "D-2", "is a parent code"),
        ("E-7", "D-2-1", "belongs to D-2"),
        ("F-2", "F-3-3R", "belongs to F-3"),  # structural parent F-3, listed only under the REGION-S program
        ("F-2", "E-7-4R", "belongs to E-7"),  # listed under E-7 and the REGION-S program
    ],
)
def test_subcode_hierarchy_errors(status, subcode, message_part):
    report = run(example(CLASSIFY, {"expected.status_code": status, "expected.subcode": subcode}))
    found = messages(report, "subcode_hierarchy", ERROR)
    assert any(message_part in m for m in found), [i.render() for i in report.issues]


def test_subcode_only_under_a_program_is_a_review_warning():
    # REGIONAL-D-2 sits only under the REGION-S program and has no status parent to compare with.
    report = run(example(CLASSIFY, {"expected.status_code": "D-2", "expected.subcode": "REGIONAL-D-2"}))
    assert_only(report, "subcode_hierarchy", WARNING)


@pytest.mark.parametrize("status", ["K-STAR", "C-2"])
def test_program_or_irregular_status_code_is_a_warning(status):
    report = run(example(CLASSIFY, {"expected.status_code": status, "expected.subcode": None, "source_refs": [{"kind": "none", "ref": "none"}]}))
    assert_only(report, "subcode_hierarchy", WARNING)


def test_c_2_listed_under_c_3_is_a_review_warning_not_an_error():
    report = run(example(CLASSIFY, {"expected.status_code": "C-3", "expected.subcode": "C-2", "source_refs": [{"kind": "none", "ref": "none"}]}))
    assert_only(report, "subcode_hierarchy", WARNING)


@pytest.mark.parametrize(
    "status, subcode",
    [("E-7", "E-7-T"), ("D-10", "D-10-T"), ("F-5", "F-5-T1"), ("D-4", "D-4-1"), ("G-1", "G-1-5"), ("F-3", "F-3-3R"), ("E-7", "E-7-4R")],
)
def test_valid_hierarchies_pass(status, subcode):
    report = run(example(CLASSIFY, {"expected.status_code": status, "expected.subcode": subcode, "source_refs": [{"kind": "none", "ref": "none"}]}))
    assert_clean(report)


def test_visa_procedure_label_backed_by_a_stay_manual_is_a_scope_error():
    report = run(example(CLASSIFY, {"expected.procedure": "visa_issuance"}))
    assert_only(report, "procedure_scope")


def test_none_source_ref_cannot_be_combined():
    report = run(example(CLASSIFY, {"source_refs": [{"kind": "none", "ref": "none"}, {"kind": "visa_data", "ref": "E-7-4"}]}))
    assert_only(report, "source_refs")


# ---------------------------------------------------------------------------
# Law identity registry
# ---------------------------------------------------------------------------
def test_law_identity_needs_the_registry():
    report = run(example(LAW_REF), options=replace(OPTIONS, registry_dir=FIXTURES / "no-such-registry"))
    assert_only(report, "law_identity")


def test_unknown_law_id():
    assert_only(run(example(LAW_REF, {"source_refs": [{"kind": "law_identity", "ref": "999999"}]})), "law_identity")


def test_a_title_is_never_an_identity():
    report = run(example(LAW_REF, {"source_refs": [{"kind": "law_identity", "ref": "출입국관리법 시행규칙"}]}))
    assert any("use law_id 008494" in m for m in messages(report, "law_identity"))


def test_law_identity_version_must_match_the_registry():
    bad = [{"kind": "law_identity", "ref": "008494", "version_id": "289833", "effective_date": "2026-10-19"}]
    report = run(example(LAW_REF, {"source_refs": bad}))
    assert_only(report, "law_identity")
    assert "[289833, 2026-09-15]" in messages(report, "law_identity")[0]


@pytest.mark.parametrize(
    "ref",
    [
        {"kind": "law_identity", "ref": "008494"},
        {"kind": "law_identity", "ref": "008494", "version_id": "289833"},
        {"kind": "law_identity", "ref": "008494", "effective_date": "2027-09-16"},
        {"kind": "law_identity", "ref": "008494", "version_id": "289833", "effective_date": "2026-09-15"},
    ],
)
def test_law_identity_partial_and_pending_versions_match(ref):
    assert_clean(run(example(LAW_REF, {"source_refs": [ref]})))


def test_registry_merges_records_and_keeps_titles_without_an_id():
    registry = Registry(directory=FIXTURES, exists=True)
    v._add_registry_record(registry, Path("a.json"), 0, {"title": "가상법", "law_id": "SYN-1", "version_id": "1", "effective_date": "2026-01-01"})
    v._add_registry_record(registry, Path("b.json"), 0, {"title": "가상법", "law_id": "SYN-1", "version_id": "2", "effective_date": "2027-01-01"})
    v._add_registry_record(registry, Path("b.json"), 1, {"title": "가상 고시", "law_id": None, "version_id": None})
    assert registry.records["SYN-1"].versions == frozenset({("1", "2026-01-01"), ("2", "2027-01-01")})
    assert registry.problems == []
    report = run(example(LAW_REF, {"source_refs": [{"kind": "law_identity", "ref": "가상 고시"}]}), registry=registry)
    assert any("has no law_id" in m for m in messages(report, "law_identity"))


def test_registry_file_problems_are_reported(tmp_path):
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    (tmp_path / "shape.json").write_text("{\"law_id\": \"1\"}", encoding="utf-8")
    report = run(example(CLASSIFY), options=replace(OPTIONS, registry_dir=tmp_path))
    assert fired(report) == ["registry"]
    assert len(messages(report, "registry")) == 2


# ---------------------------------------------------------------------------
# Source bundles referenced by examples
# ---------------------------------------------------------------------------
def test_missing_bundle():
    assert "source_bundle" in fired(run(example(CITE, {"input.fixture_set": "syn-nowhere"})))


def test_bundle_id_cannot_leave_the_sources_directory():
    report = run(example(CITE, {"input.fixture_set": "../registry/law_identity"}))
    assert any("not a valid bundle id" in m for m in messages(report, "source_bundle"))


@pytest.mark.parametrize("authoring", ["human_authored", "derived_from_repository_data"])
def test_synthetic_bundle_backs_only_synthetic_authored_examples(authoring):
    changes = {"provenance.authoring": authoring}
    if authoring == "derived_from_repository_data":
        changes["provenance.derived_from"] = ["tests/fixtures_dataset/sources/syn-basic.json"]
    report = run(example(CITE, changes))
    assert_only(report, "source_bundle")


def test_synthetic_bundle_never_sits_next_to_a_real_law_id():
    refs = _base_examples()[CITE]["source_refs"] + [{"kind": "law_identity", "ref": "008494"}]
    report = run(example(CITE, {"source_refs": refs}))
    assert any("mixes synthetic_fixture" in m for m in messages(report, "source_bundle"))


def test_verified_bundle_backs_derived_examples():
    assert_clean(run(example(TEMPORAL_REAL)))


def test_bundle_ref_version_must_exist_and_provision_should():
    report = run(example(CITE, {"source_refs": [{"kind": "source_bundle", "ref": "syn-basic", "version_id": "SYN-V9"}]}))
    assert_only(report, "source_bundle")
    report = run(example(CITE, {"source_refs": [{"kind": "source_bundle", "ref": "syn-basic", "version_id": "SYN-V1", "provision": "제4조"}]}))
    assert_only(report, "source_bundle", WARNING)


def test_heading_units_are_not_provisions():
    bundle = load_bundle_data("syn-basic")
    bundle["bundle_id"] = "syn-heading"
    heading = dict(bundle["provisions"][0], evidence_id="syn-heading:h1", provision_key="제1장", unit_kind="heading", text="제1장 총칙")
    bundle["provisions"].append(heading)
    refs = [{"kind": "source_bundle", "ref": "syn-heading", "version_id": "SYN-V1", "effective_date": "2026-01-01", "provision": "제1장"}]
    report = run(example(CITE, {"input.fixture_set": "syn-heading", "source_refs": refs}), bundles={"syn-heading": bundle})
    assert_only(report, "source_bundle", WARNING)


# ---------------------------------------------------------------------------
# Bundle-level rules (reported once per bundle, at file level)
# ---------------------------------------------------------------------------
def test_fixture_bundles_have_no_problems():
    for bundle_id in ("syn-basic", "v-rule-008494-history"):
        assert bundle_problems(load_bundle_data(bundle_id)) == [], bundle_id


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda b: b.update(bundle_id="other"), "does not match the file name"),
        (lambda b: b.pop("faults"), "missing key 'faults'"),
        (lambda b: b.update(bundle_version=True), "bundle_version has the wrong type"),
        (lambda b: b.update(provenance="repository_record"), "provenance must be one of"),
        (lambda b: b.update(title_index_coverage="most"), "title_index_coverage"),
        (lambda b: b["identities"][0].update(family="law"), "is not a contracts.SourceFamily value"),
        (lambda b: b["versions"][0].update(parse_status="done"), "parse_status"),
        (lambda b: b["versions"].append(dict(b["versions"][0])), "duplicate version"),
        (lambda b: b["provisions"][0].update(version_id="SYN-V7"), "no version [SYN-V7, 2026-01-01]"),
        (lambda b: b["provisions"][0].update(unit_kind="chapter"), "unit_kind"),
        (lambda b: b["faults"][0].update(status="timeout"), "is not a contracts.LookupStatus value"),
        (lambda b: b["faults"][0].update(operation="search"), "operation 'search'"),
        (lambda b: b["addenda"].append({"stable_id": "SYN-LAW-0001", "version_id": "SYN-V1", "effective_date": "2026-01-01", "text": "부칙", "kind": "misc", "mentions": []}), "kind 'misc'"),
    ],
)
def test_bundle_shape_problems(mutate, fragment):
    bundle = load_bundle_data("syn-basic")
    mutate(bundle)
    problems = bundle_problems(bundle, "syn-basic")
    assert any(fragment in p for p in problems), problems


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda b: b["identities"][0].update(stable_id="008494"), "reuses the real law id"),
        (lambda b: b["identities"][0].update(official_title="출입국관리법 시행규칙"), "reuses the real law title"),
        (lambda b: b["identities"][0].update(stable_id="123456"), "shaped like a real"),
        (lambda b: b["identities"][0].update(provider="law.go.kr"), "names law.go.kr"),
        (lambda b: b["versions"][0].update(official_url="https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=1"), "official law URLs"),
        (lambda b: b["provisions"][0].update(provenance="verified_web"), "contains records with provenance ['verified_web']"),
    ],
)
def test_synthetic_bundle_rules(mutate, fragment):
    bundle = load_bundle_data("syn-basic")
    mutate(bundle)
    if bundle["identities"][0]["stable_id"] != "SYN-LAW-0001":
        new_id = bundle["identities"][0]["stable_id"]
        for key in ("versions", "provisions"):
            for item in bundle[key]:
                item["stable_id"] = new_id
    problems = bundle_problems(bundle, "syn-basic")
    assert any(fragment in p for p in problems), problems


def test_synthetic_title_without_fictional_marker_is_a_warning():
    bundle = load_bundle_data("syn-basic")
    bundle["bundle_id"] = "syn-plain-title"
    bundle["identities"][0]["official_title"] = "체류관리법"
    report = run(example(CITE, {"input.fixture_set": "syn-plain-title", "source_refs": [{"kind": "none", "ref": "none"}]}),
                 bundles={"syn-plain-title": bundle})
    assert_only(report, "source_bundle", WARNING)


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda b: b.update(attribution="law.go.kr capture"), "must carry the attribution"),
        (lambda b: b.update(captured_at=None), "captured_at must be the capture date"),
        (lambda b: b["versions"][0].update(content_sha256=None), "content_sha256"),
        (lambda b: b["versions"][0].update(content_sha256="ABC"), "content_sha256"),
        (lambda b: b["versions"][0].update(retrieved_at=None), "retrieved_at"),
        (lambda b: b["versions"][0].update(official_url=None), "official_url"),
        (lambda b: b["versions"][0].update(official_url="https://law.go.kr.example.com/LSW/x"), "official_url"),
        (lambda b: b["versions"][0].update(official_url="https://law.go.kr@example.com/LSW/x"), "official_url"),
        (lambda b: b["versions"][0].update(provenance="synthetic_fixture"), "contains synthetic_fixture records"),
        (lambda b: b["versions"][0].update(provenance="unverified"), "records with provenance ['unverified']"),
    ],
)
def test_verified_bundle_rules(mutate, fragment):
    bundle = load_bundle_data("v-rule-008494-history")
    mutate(bundle)
    problems = bundle_problems(bundle, "v-rule-008494-history")
    assert any(fragment in p for p in problems), problems


def test_bundle_level_capture_list_can_trace_unparsed_history_rows():
    bundle = load_bundle_data("v-rule-008494-history")
    for version in bundle["versions"]:
        version.update(content_sha256=None, parse_status="not_parsed")
    assert any("no captures list" in p for p in bundle_problems(bundle, "v-rule-008494-history"))
    bundle["captures"] = [{
        "capture_id": "v04_hst_008494.html",
        "file": "scratchpad/verifier/raw/v04_hst_008494.html",
        "url": "https://www.law.go.kr/LSW/lsHstListR.do?lsId=008494&chrClsCd=010202",
        "sha256": "9ab640c0e1e6bf684d80cad61284bb9ee30f362a5984abf28ad14c498fb9c2c8",
    }]
    assert bundle_problems(bundle, "v-rule-008494-history") == []
    bundle["captures"][0]["sha256"] = "not-a-hash"
    assert any("captures[0]: sha256" in p for p in bundle_problems(bundle, "v-rule-008494-history"))


def test_addressable_units_need_unique_evidence_ids():
    bundle = load_bundle_data("syn-basic")
    article = next(p for p in bundle["provisions"] if p["unit_kind"] == "article")
    bundle["provisions"].append(dict(article, provision_key="제99조"))
    assert any("duplicate evidence_id" in p for p in bundle_problems(bundle, "syn-basic"))


def test_heading_units_may_share_an_evidence_id_like_the_fixture_adapter_allows():
    # 제4장 and 제1절 both sit before one article in the official JSON; heading units name no evidence.
    bundle = load_bundle_data("syn-basic")
    heading = dict(bundle["provisions"][0], evidence_id="syn:heading:제3조", provision_key="제3조", unit_kind="heading", text="제1장 가상 총칙")
    bundle["provisions"] += [heading, dict(heading, text="제1절 가상 통칙")]
    assert bundle_problems(bundle, "syn-basic") == []
    bundle["provisions"].append(dict(heading, evidence_id=""))
    assert any("evidence_id is required" in p for p in bundle_problems(bundle, "syn-basic"))


def test_personal_data_in_a_bundle_is_reported():
    bundle = load_bundle_data("syn-basic")
    bundle["provisions"][0]["text"] += " 문의 010-1234-5678"
    problems = bundle_problems(bundle, "syn-basic")
    assert any("mobile_number" in p and "1234" not in p for p in problems), problems


def test_bundle_problems_reach_the_report_once():
    bundle = load_bundle_data("syn-basic")
    bundle["bundle_id"] = "syn-broken"
    bundle["identities"][0]["family"] = "law"
    first = example(CITE, {"input.fixture_set": "syn-broken", "source_refs": [{"kind": "none", "ref": "none"}]})
    second = example(TEMPORAL, {"input.fixture_set": "syn-broken"})
    report = run(first, second, bundles={"syn-broken": bundle})
    assert len(messages(report, "source_bundle")) == 1


def test_unreadable_bundle_file(tmp_path):
    (tmp_path / "syn-bad.json").write_text("{\"bundle_id\": ", encoding="utf-8")
    report = run(example(CITE, {"input.fixture_set": "syn-bad", "source_refs": [{"kind": "none", "ref": "none"}]}),
                 options=replace(OPTIONS, sources_dir=tmp_path))
    assert any("not valid JSON" in m for m in messages(report, "source_bundle"))


# ---------------------------------------------------------------------------
# Manual editions (approval index)
# ---------------------------------------------------------------------------
def _manual(ref: Mapping[str, Any]) -> Dict[str, Any]:
    return example(CLASSIFY, {"source_refs": [{"kind": "visa_data", "ref": "E-7-4"}, dict(ref, kind="manual")]})


def test_unknown_manual_edition():
    assert_only(run(_manual({"ref": "stay_manual_2099_01_01_hwp"})), "manual_edition")


def test_unapproved_manual_edition_is_a_warning():
    report = run(_manual({"ref": "fixture_stay_manual_pending"}))
    assert_only(report, "manual_edition", WARNING)
    assert "label backed by unapproved manual edition" in messages(report, "manual_edition")[0]


def test_manual_effective_date_must_match_the_index():
    assert_only(run(_manual({"ref": "fixture_stay_manual_approved", "effective_date": "2026-03-01"})), "manual_edition")


def test_missing_manual_index_is_an_error():
    report = run(_manual({"ref": "fixture_stay_manual_approved"}), options=replace(OPTIONS, manual_index_path=FIXTURES / "nope.json"))
    assert_only(report, "manual_edition")


def test_real_manual_index_states_are_read_only_and_respected():
    real = replace(OPTIONS, manual_index_path=v.DEFAULT_MANUAL_INDEX_PATH)
    assert_clean(run(_manual({"ref": "stay_manual_2026_07_31_hwp"}), options=real))
    assert_only(run(_manual({"ref": "stay_manual_2026_06_01_pdf"}), options=real), "manual_edition", WARNING)


# ---------------------------------------------------------------------------
# Teacher output, provenance and review
# ---------------------------------------------------------------------------
def test_teacher_policy_missing():
    report = run(example(TEACHER), options=replace(OPTIONS, teacher_policy_path=FIXTURES / "no-policy.json"))
    assert_only(report, "teacher")
    assert messages(report, "teacher")[0].startswith("teacher policy missing")


def test_repository_policy_without_legal_signoff_refuses_every_teacher():
    report = run(example(TEACHER), options=replace(OPTIONS, teacher_policy_path=v.DEFAULT_TEACHER_POLICY_PATH))
    assert "teacher" in fired(report)
    assert any("legal_signoff" in m for m in messages(report, "teacher"))


@pytest.mark.parametrize(
    "changes, path",
    [
        ({"provenance.teacher": DELETE}, "provenance.teacher"),
        ({"provenance.teacher.permitted": False}, "provenance.teacher.permitted"),
        ({"provenance.teacher.channel": DELETE}, "provenance.teacher.channel"),
        ({"provenance.teacher.channel": "fixture_api"}, "provenance.teacher"),
        ({"provenance.teacher.model": "fixture-lab/teacher-2"}, "provenance.teacher"),
    ],
)
def test_teacher_must_be_permitted_by_the_policy(changes, path):
    report = run(example(TEACHER, changes))
    assert path in paths(report, "teacher"), [i.render() for i in report.issues]


def test_teacher_block_on_a_non_teacher_example():
    teacher = _base_examples()[TEACHER]["provenance"]["teacher"]
    assert_only(run(example(CLASSIFY, {"provenance.teacher": teacher})), "teacher")


def test_derived_examples_should_name_their_sources():
    assert_only(run(example(GUIDANCE, {"provenance.derived_from": DELETE})), "provenance", WARNING)


@pytest.mark.parametrize("missing", ["reviewer", "reviewed_at"])
def test_human_verified_needs_reviewer_and_date(missing):
    review = {"status": "human_verified", "checks": [], "reviewer": "fixture-reviewer", "reviewed_at": "2026-10-19"}
    assert_clean(run(example(CLASSIFY, {"label_review": review})))
    review[missing] = None
    assert_only(run(example(CLASSIFY, {"label_review": review})), "label_review")


def test_review_cannot_predate_the_example():
    review = {"status": "machine_checked", "checks": [], "reviewed_at": "2026-10-01"}
    assert_only(run(example(CLASSIFY, {"label_review": review})), "label_review")


def test_revision_history_must_increase_and_end_at_the_revision():
    history = [{"revision": 1, "date": "2026-10-19", "change": "a"}, {"revision": 1, "date": "2026-10-19", "change": "b"}]
    assert_only(run(example(CLASSIFY, {"revision_history": history})), "revision")
    assert_only(run(example(CLASSIFY, {"revision": 2})), "revision")


# ---------------------------------------------------------------------------
# Personal data
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "token, kind",
    [
        ("900101-5234567", "alien_registration_number"),
        ("9001011234567", "resident_registration_number"),
        ("M12345678", "passport_number"),
        ("010-1234-5678", "mobile_number"),
        ("someone@example.com", "email_address"),
    ],
)
def test_personal_data_in_any_string_is_an_error_and_is_never_echoed(token, kind):
    report = run(example(CLASSIFY, {"input.question": f"여권 갱신 문의입니다. 제 정보는 {token} 입니다"}))
    assert [m.split(" ")[0] for m in messages(report, "pii")] == [kind]
    assert all("withheld" in m for m in messages(report, "pii"))
    assert token not in report.render_text()
    assert token not in json.dumps(report.to_dict(), ensure_ascii=False)


def test_personal_data_in_nested_values_and_keys():
    report = run(example(CLASSIFY, {"scenario.facts": {"contact": ["ok", "a.b@example.com"], "900101-5234567": "x"}}))
    # The key itself is personal data, so the reported path names it only as withheld.
    assert sorted(paths(report, "pii")) == ["scenario.facts.<withheld>(key)", "scenario.facts.contact[1]"]


def test_reports_never_carry_personal_data_from_ids_keys_or_count_buckets():
    leaky = example(CLASSIFY, {"id": "900101-5234567", "language": "010-1234-5678", "scenario.facts": {"a.b@example.com": 1}})
    report = run(leaky)
    assert "pii" in fired(report)
    text = report.render_text() + json.dumps(report.to_dict(), ensure_ascii=False)
    for fragment in ("5234567", "1234-5678", "a.b@example.com"):
        assert fragment not in text, fragment
    assert {i.example_id for i in report.issues} == {"<withheld>"}
    assert report.counts["language"] == {"<withheld>": 1}


def test_administrative_rule_ids_are_not_personal_data():
    ref = {"kind": "law_identity", "ref": "2090230", "version_id": "2100000275060"}
    report = run(example(LAW_REF, {"source_refs": [ref]}))
    assert "pii" not in report.rules()


# ---------------------------------------------------------------------------
# Cross-record rules
# ---------------------------------------------------------------------------
def test_duplicate_ids():
    report = run(example(CLASSIFY), example(CLASSIFY, {"input.question": "전혀 다른 질문입니다"}))
    assert fired(report) == ["duplicate_id"]


def test_duplicate_question_after_normalization():
    first = example(CLASSIFY)
    second = example(CLASSIFY, {"id": "fx-class-e74-extension-copy", "input.question": "  e-7-4   체류기간 연장 신청하려고 해요 "})
    assert_only(run(first, second), "duplicate_question")


def test_same_question_in_another_task_is_not_a_duplicate():
    other = example(ABSTAIN, {"id": "fx-abstain-e74", "input.question": _base_examples()[CLASSIFY]["input"]["question"], "split": "test"})
    assert "duplicate_question" not in run(example(CLASSIFY, split="dev"), other).rules()


def test_contradiction_same_input_and_language_different_label():
    first = example(CLASSIFY)
    second = example(CLASSIFY, {"id": "fx-class-e74-other-label", "expected.subcode": "E-7-1"})
    report = run(first, second)
    assert fired(report) == ["contradiction"]


def test_same_input_in_another_language_is_a_duplicate_not_a_contradiction():
    first = example(CLASSIFY)
    second = example(CLASSIFY, {"id": "fx-class-e74-en-tag", "language": "en", "expected.subcode": "E-7-1"})
    assert fired(run(first, second)) == ["duplicate_question"]


def test_same_question_with_a_different_date_is_reuse_not_duplicate():
    first = example(TEMPORAL_REAL)
    second = example(TEMPORAL_REAL, {
        "id": "fx-temporal-rule73-effective",
        "scenario.relevant_dates.question_date": "2027-10-01",
        "expected.candidate_version_keys": [["289833", "2027-09-16"]],
        "expected.warnings": ["transitional_provisions_unreviewed"],
    })
    report = run(first, second)
    assert_only(report, "question_reuse", WARNING)


@pytest.mark.parametrize("split, severity, rule", [
    ("test", ERROR, "contamination"),
    ("dev", ERROR, "contamination"),
    ("adversarial_holdout", ERROR, "contamination"),
])
def test_train_eval_contamination(split, severity, rule):
    train = example(CLASSIFY)
    near = example(EXTRACT, {"id": "fx-extract-near", "split": split, "input.question": "E-7-4 체류기간 연장 신청하려고 해요!",
                             "expected.dates": [], "scenario.adversarial_class": "L" if split == "adversarial_holdout" else None})
    report = run(train, near)
    assert rule in report.rules(severity)
    assert all(i.example_id == "fx-extract-near" for i in report.issues if i.rule == rule)


def test_dev_test_overlap_is_a_warning():
    dev = example(EXTRACT)
    test = example(EXTRACT, {"id": "fx-extract-dates-en-2", "split": "test", "input.question": "Today is 2026-10-19 and my stay expires on 2026-11-30!"})
    report = run(dev, test)
    assert report.rules() == ["contamination_dev_test"]
    assert report.rules(WARNING) == ["contamination_dev_test"]


def test_dissimilar_questions_are_not_contamination():
    assert_clean(run(example(CLASSIFY), example(EXTRACT, split="test")))


def test_threshold_is_exact_at_the_boundary():
    left = frozenset(f"g{i:02d}" for i in range(20))
    seventeen = frozenset(list(sorted(left))[:17])
    sixteen = frozenset(list(sorted(left))[:16])
    assert v.is_near_duplicate(left, seventeen)          # 17/20 = 0.85
    assert not v.is_near_duplicate(left, sixteen)        # 16/20 = 0.80


def test_prefix_filter_finds_exactly_the_brute_force_pairs():
    rng = random.Random(20261019)
    alphabet = "가나다라마바사아자차카타파하 E-7"
    base = ["".join(rng.choice(alphabet) for _ in range(rng.randint(5, 40))) for _ in range(60)]
    texts = base + [t[:-1] + "!" for t in base[:20]] + [t + t[:2] for t in base[20:30]]
    records = [Record("mem", i, "line", {"id": f"r{i}", "input": {"question": t}}) for i, t in enumerate(texts)]
    grams = {id(r): v.char_trigrams(v.contamination_text(r)) for r in records}
    finder = v.NearDuplicateFinder(grams)
    sources, targets = records[::2], records[1::2]
    expected = [(s, t) for t in targets for s in sources if v.is_near_duplicate(grams[id(s)], grams[id(t)])]
    found = finder.pairs(sources, targets)
    assert sorted((s.ordinal, t.ordinal) for s, t in found) == sorted((s.ordinal, t.ordinal) for s, t in expected)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def test_report_is_deterministic_and_sorted():
    examples: Sequence[Dict[str, Any]] = [example(i) for i in sorted(_base_examples())] + [
        example(CLASSIFY, {"id": "fx-bad-subcode", "expected.subcode": "E-7", "expected.status_code": "E-7"}),
        example(CITE, {"id": "fx-bad-bundle", "input.fixture_set": "syn-nowhere"}),
    ]
    first = run(*examples).render_text()
    second = run(*reversed(examples)).render_text()
    assert first == run(*examples).render_text()
    assert first.splitlines()[:2] == second.splitlines()[:2]
    report = run(*examples)
    assert report.issues == sorted(report.issues, key=v.Issue.sort_key)
    for bucket in report.counts.values():
        assert list(bucket) == sorted(bucket)


def test_report_json_shape():
    report = run(example(CLASSIFY, {"expected.subcode": "E-7", "expected.status_code": "E-7"}))
    data = report.to_dict()
    assert data["result"] == "fail" and data["error_count"] == 1 and data["warning_count"] == 0
    assert data["issues"][0]["rule"] == "subcode_hierarchy"
    assert set(data["counts"]) == set(v.COUNT_FIELDS)
    json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Schema fields added on 2026-10-20: case_template, context_title, teacher.channel
# ---------------------------------------------------------------------------
def _templated(example_id: str, template: Optional[str], split: str, **changes: Any) -> Dict[str, Any]:
    adversarial = "L" if split == "adversarial_holdout" else None
    return example(example_id, {"scenario.case_template": template, "split": split,
                                "scenario.adversarial_class": adversarial, **changes})


@pytest.mark.parametrize("split", ["dev", "test", "adversarial_holdout"])
def test_a_case_template_in_train_and_an_eval_split_is_an_error(split):
    train = _templated(CLASSIFY, "tpl-e74-extension", "train")
    other = _templated(EXTRACT, "tpl-e74-extension", split, id="fx-extract-same-template")
    report = run(train, other)
    assert report.rules(ERROR) == ["case_template"], [i.render() for i in report.issues]
    flagged = [i for i in report.issues if i.rule == "case_template"]
    assert [(i.example_id, i.path) for i in flagged] == [("fx-extract-same-template", "scenario.case_template")]
    assert CLASSIFY in flagged[0].message and split in flagged[0].message


@pytest.mark.parametrize("split", ["test", "adversarial_holdout"])
def test_a_case_template_shared_by_dev_and_a_decision_split_is_a_warning(split):
    dev = _templated(EXTRACT, "tpl-dates", "dev")
    other = _templated(CLASSIFY, "tpl-dates", split, id="fx-class-same-template")
    report = run(dev, other)
    assert report.rules() == ["case_template_dev_eval"] and report.ok, [i.render() for i in report.issues]
    assert report.rules(WARNING) == ["case_template_dev_eval"]


def test_case_templates_shared_inside_one_side_are_allowed():
    pairs = [("test", "adversarial_holdout"), ("train", "train"), ("test", "test")]
    for left, right in pairs:
        report = run(_templated(CLASSIFY, "tpl-shared", left), _templated(EXTRACT, "tpl-shared", right, id="fx-extract-2"))
        assert not {"case_template", "case_template_dev_eval"} & set(report.rules()), (left, right, [i.render() for i in report.issues])


def test_examples_without_a_case_template_are_not_compared():
    for template in (None, DELETE):
        report = run(_templated(CLASSIFY, template, "train"), _templated(EXTRACT, template, "test", id="fx-extract-2"))
        assert_clean(report)


def test_different_case_templates_across_train_and_test_are_fine():
    assert_clean(run(_templated(CLASSIFY, "tpl-a", "train"), _templated(EXTRACT, "tpl-b", "test")))


@pytest.mark.parametrize("template, rule", [("", "scenario"), ("  ", "scenario"), (" tpl-a", "scenario"), (7, "schema")])
def test_case_template_must_be_an_identifier_or_null(template, rule):
    report = run(example(CLASSIFY, {"scenario.case_template": template}))
    assert "scenario.case_template" in paths(report, rule), [i.render() for i in report.issues]
    assert report.rules(ERROR) == [rule]


def test_claim_context_title_is_accepted():
    for title in ("가상체류관리법", None):
        assert_clean(run(example(CITE, {"input.claim.context_title": title})))


@pytest.mark.parametrize("title, rules", [("", ["input_shape"]), ("   ", ["input_shape"]), (12, ["input_shape", "schema"])])
def test_claim_context_title_must_be_a_title_or_null(title, rules):
    report = run(example(CITE, {"input.claim.context_title": title}))
    assert report.rules(ERROR) == sorted(rules), [i.render() for i in report.issues]
    assert "input.claim.context_title" in paths(report, "input_shape")


def test_teacher_channel_is_required_even_when_the_policy_file_is_missing():
    report = run(example(TEACHER, {"provenance.teacher.channel": DELETE}),
                 options=replace(OPTIONS, teacher_policy_path=FIXTURES / "no-policy.json"))
    assert_only(report, "teacher")
    assert "provenance.teacher.channel" in paths(report, "teacher")
    assert any(m.startswith("teacher policy missing") for m in messages(report, "teacher"))


@pytest.mark.parametrize("channel", ["", None, 3])
def test_teacher_channel_must_be_named(channel):
    report = run(example(TEACHER, {"provenance.teacher.channel": channel}))
    assert "provenance.teacher.channel" in paths(report, "teacher"), [i.render() for i in report.issues]


def test_teacher_block_with_a_channel_the_policy_permits_passes():
    assert_clean(run(example(TEACHER)))
