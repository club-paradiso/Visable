"""Contract tests: the shared vocabulary behaves as the specs describe, and the
mirrored backend vocabulary has not drifted from the backend."""
from __future__ import annotations

import datetime as dt
import importlib
import json
import sys
from pathlib import Path

import pytest

from waymaker_ai import contracts as c
from waymaker_ai.legal import adapters

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = EXPERIMENT_ROOT.parents[1] / "backend"


def _backend_module(name: str):
    """Import a backend module if the backend and its dependencies are available."""
    if not BACKEND_ROOT.is_dir():
        pytest.skip("backend directory not present")
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    try:
        return importlib.import_module(name)
    except Exception as exc:  # missing optional dependency: skip, do not fail
        pytest.skip(f"backend module {name} not importable here: {type(exc).__name__}: {exc}")


# -- parity with the backend -------------------------------------------------
def test_authority_types_mirror_backend():
    module = _backend_module("services.immigration_tools")
    assert list(c.AUTHORITY_TYPES) == [e.value for e in module.AuthorityType]


def test_condition_kinds_mirror_backend():
    module = _backend_module("services.knowledge.models")
    assert list(c.CONDITION_KINDS) == [e.value for e in module.ConditionKind]


def test_default_authority_covers_every_family_with_known_values():
    assert set(c.DEFAULT_AUTHORITY) == set(c.SourceFamily)
    assert set(c.DEFAULT_AUTHORITY.values()) <= set(c.AUTHORITY_TYPES)


# -- lookups -----------------------------------------------------------------
def test_only_not_found_is_absence_and_only_found_or_not_found_are_not_failures():
    for status in c.LookupStatus:
        assert status.is_absence == (status is c.LookupStatus.NOT_FOUND)
        assert status.is_failure == (status not in (c.LookupStatus.FOUND, c.LookupStatus.NOT_FOUND))


# -- layers and roll-up ------------------------------------------------------
def _layers(outcomes):
    return tuple(
        c.LayerResult(layer, outcome, c.VerificationCode.NOT_CHECKED)
        for layer, outcome in zip(c.iter_layer_order(), outcomes)
    )


def test_layer_order_is_l1_to_l7():
    assert [layer.order for layer in c.iter_layer_order()] == list(range(1, 8))


@pytest.mark.parametrize("outcomes, expected", [
    (["pass"] * 6 + ["fail"], c.OverallStatus.FAILED),
    (["unavailable"] + ["needs_review"] * 6, c.OverallStatus.VERIFICATION_UNAVAILABLE),
    (["pass"] * 4 + ["needs_review"] + ["pass"] * 2, c.OverallStatus.HUMAN_REVIEW_REQUIRED),
    (["pass"] * 3 + ["not_applicable"] * 4, c.OverallStatus.VERIFIED),
])
def test_overall_rolls_up_in_spec_order(outcomes, expected):
    verification = c.ClaimVerification("x", _layers([c.LayerOutcome(o) for o in outcomes]))
    assert verification.overall() is expected


def test_missing_layers_make_verified_partial():
    verification = c.ClaimVerification("x", _layers([c.LayerOutcome.PASS] * 3))
    assert verification.overall() is c.OverallStatus.VERIFIED_PARTIAL


def test_highest_verified_layer_stops_at_first_non_pass():
    outcomes = [c.LayerOutcome.PASS, c.LayerOutcome.NOT_APPLICABLE, c.LayerOutcome.PASS,
                c.LayerOutcome.NEEDS_REVIEW, c.LayerOutcome.PASS, c.LayerOutcome.PASS, c.LayerOutcome.PASS]
    assert c.ClaimVerification("x", _layers(outcomes)).highest_verified_layer() == 3


# -- identity and versions ---------------------------------------------------
def test_version_key_and_provision_effective_date():
    version = c.SourceVersion(
        stable_id="SYN", version_id="V1", effective_date=dt.date(2026, 9, 15),
        provision_effective_dates={"제73조": dt.date(2027, 9, 16)},
    )
    assert version.key == ("V1", "2026-09-15")
    assert version.effective_date_for("제73조") == dt.date(2027, 9, 16)
    assert version.effective_date_for("제1조") == dt.date(2026, 9, 15)
    assert version.effective_date_for(None) == dt.date(2026, 9, 15)


def test_provision_ref_keys():
    ref = c.ProvisionRef(article=10, article_branch=2, paragraph=1, item=3, item_branch=1, subitem="가")
    assert ref.key() == "제10조의2제1항제3호의1가목"
    assert ref.article_key() == "제10조의2"
    assert c.ProvisionRef(annex="별표 5의2").key() == "별표5의2"
    assert c.ProvisionRef(form="별지 제34호서식").article_key() == "별지제34호서식"
    assert c.ProvisionRef(article=1, addendum=True).article_key() == "부칙제1조"
    assert c.ProvisionRef().is_empty()


def test_text_helpers():
    assert c.compact("가상 체류ㆍ관리 법") == "가상체류관리법"
    assert c.sha256_text("a  b") == c.sha256_text("a b")
    assert c.parse_date("20260915") == dt.date(2026, 9, 15)
    assert c.parse_date("2026-09-15") == dt.date(2026, 9, 15)
    assert c.parse_date(None) is None


def test_procedure_scope_never_mixes_visa_and_stay():
    assert {c.procedure_scope(p) for p in c.VISA_SCOPE_PROCEDURES} == {"visa"}
    stay = set(c.FINE_PROCEDURES) - c.VISA_SCOPE_PROCEDURES
    assert {c.procedure_scope(p) for p in stay} == {"stay"}
    assert set(c.FINE_TO_COARSE) == set(c.FINE_PROCEDURES)
    assert {v for v in c.FINE_TO_COARSE.values() if v} <= set(c.COARSE_PROCEDURES)


# -- the bundle schema documents what the adapter enforces --------------------
def test_bundle_schema_matches_adapter_vocabulary():
    schema = json.loads((EXPERIMENT_ROOT / "schemas" / "source_bundle.schema.json").read_text(encoding="utf-8"))
    assert set(schema["required"]) == set(adapters.REQUIRED_BUNDLE_KEYS)
    assert set(schema["properties"]) == set(adapters.REQUIRED_BUNDLE_KEYS) | set(adapters.OPTIONAL_BUNDLE_KEYS)
    fault = schema["properties"]["faults"]["items"]["properties"]
    assert fault["operation"]["enum"] == list(adapters.OPERATIONS)
    assert fault["status"]["enum"] == [s.value for s in c.LookupStatus]
    assert [k for k in fault["raw_body_kind"]["enum"] if k] == list(adapters.RAW_BODY_KINDS)
    assert set(fault["match"]["properties"]) == set(adapters.FAULT_MATCH_KEYS)
    provision = schema["properties"]["provisions"]["items"]["properties"]
    assert provision["unit_kind"]["enum"] == list(adapters.UNIT_KINDS)
    assert provision["structure_complete"]["type"] == "boolean"           # ProvisionText.structure_complete
    assert provision["structure_complete"]["default"] is False
    assert "citation_not_found" in provision["structure_complete"]["description"]
    identity = schema["properties"]["identities"]["items"]["properties"]
    assert identity["family"]["enum"] == [f.value for f in c.SourceFamily]
    scope = schema["$defs"]["scope"]["properties"]
    assert scope["condition_kind"]["enum"] == list(c.CONDITION_KINDS)


def test_every_raw_body_kind_defaults_to_a_failure_status():
    assert set(adapters.RAW_BODY_DEFAULT_STATUS) == set(adapters.RAW_BODY_KINDS)
    assert all(status.is_failure for status in adapters.RAW_BODY_DEFAULT_STATUS.values())


# -- payload helpers -----------------------------------------------------------
def test_identity_titles_and_authority():
    identity = c.SourceIdentity("synthetic", c.SourceFamily.ENFORCEMENT_RULE, "SYN-RUL-0001", "가상체류관리법 시행규칙",
                                former_titles=("가상체류관리법시행규칙",), short_titles=("가상규칙",))
    assert identity.all_titles() == ("가상체류관리법 시행규칙", "가상체류관리법시행규칙", "가상규칙")
    assert identity.authority_type == "statute"


def test_relevant_dates_get_and_present():
    dates = c.RelevantDates(question_date=dt.date(2026, 10, 19), conduct_date=dt.date(2025, 5, 1))
    assert dates.get(c.AnchorKind.CONDUCT_DATE) == dt.date(2025, 5, 1)
    assert dates.get(c.AnchorKind.DECISION_DATE) is None
    assert dates.present() == {"question_date": dt.date(2026, 10, 19), "conduct_date": dt.date(2025, 5, 1)}
    assert {a.value for a in c.AnchorKind} <= set(c.RelevantDates.__dataclass_fields__)


def test_structure_completeness_and_claim_context_default_to_unknown():
    text = c.ProvisionText("e", "S", ("V", "2026-10-02"), "제5조", None, "제5조")
    assert text.structure_complete is False          # a missing sub-unit is not authoritative by default
    claim = c.ClaimInput(claim_id="x", text="t")
    assert claim.context_title is None
    assert c.ClaimInput(claim_id="x", text="t", context_title="가상체류관리법").context_title == "가상체류관리법"


def test_provision_full_text_reads_text_paragraphs_then_items():
    text = c.ProvisionText("e", "S", ("V", "2026-10-02"), "제5조", "가상", "제5조(가상)",
                           paragraphs={2: "② 둘", 1: "① 하나"}, items={"2:1": "1. 가"})
    assert text.full_text() == "제5조(가상)\n① 하나\n② 둘\n1. 가"


def test_verification_and_assessment_serialize_to_plain_values():
    verification = c.ClaimVerification("x", _layers([c.LayerOutcome.PASS] * 7))
    data = json.loads(json.dumps(verification.to_dict()))
    assert data["overall"] == "verified" and data["highest_verified_layer"] == 7
    assert [layer["layer"] for layer in data["layers"]] == [layer.value for layer in c.iter_layer_order()]
    version = c.SourceVersion("S", "V", dt.date(2026, 10, 2))
    assessment = c.TemporalAssessment((version,), (), c.AnchorKind.QUESTION_DATE, dt.date(2026, 10, 19))
    assert assessment.candidate_keys() == [["V", "2026-10-02"]]
    assert assessment.determination == "candidate_only"
