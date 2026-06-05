"""Tests for the generalized official-evidence retrieval ontology + planner.

These assert GENERALIZED behavior of the ontology / query planner / routing /
relevance layer — never hardcoded answer strings and never per-visa special
cases. The example questions (H-1, G-1-5, E-7→F-2-99, C-3) are used only as
regression / evaluation cases proving the general pipeline works.

Run from repo root:

    python3 -m pytest backend/tests/test_generalized_evidence_ontology.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest

from services import evidence_ontology as onto
from services.evidence_ontology import (
    EVIDENCE_GOALS,
    SOURCE_FAMILIES,
    WIRED_SOURCE_FAMILIES,
    build_evidence_ontology,
    plan_evidence_queries,
    route_source_families,
    source_families_for_issue,
    source_family_support_status,
)
from services.legal_analysis import (
    LEGAL_ISSUE_TYPES,
    RELEVANCE_BACKGROUND,
    RELEVANCE_DIRECT,
    RELEVANCE_RELATED,
    RELEVANCE_ANALOGICAL,
    build_generalized_source_plan,
    extract_immigration_facts,
    classify_legal_issue_types,
    score_evidence_relevance,
)
from services.law_tools import build_law_evidence_pack


# --- Test 1: every legal issue routes to at least one source-family query ----
class PlannerCoverageTests:
    pass


@pytest.mark.parametrize("issue", [i for i in LEGAL_ISSUE_TYPES])
def test_every_issue_routes_to_a_source_family(issue):
    families = route_source_families([issue])
    assert families, f"issue {issue} produced no source families"
    assert all(f in SOURCE_FAMILIES for f in families)


@pytest.mark.parametrize("issue", [i for i in LEGAL_ISSUE_TYPES])
def test_every_issue_emits_at_least_one_query(issue):
    facts = {"current_status": "X-1", "current_parent_status": "X-1"}
    plan = plan_evidence_queries(facts, [issue], max_queries=8)
    assert plan, f"issue {issue} produced no query"
    # Each query object has the full structured contract.
    for q in plan:
        for key in (
            "source_family", "priority", "query_ko", "query_en",
            "expected_status_codes", "expected_concepts", "evidence_goal",
            "reason", "status_role",
        ):
            assert key in q, f"query object missing key {key}"
        assert q["evidence_goal"] in EVIDENCE_GOALS
        assert q["source_family"] in SOURCE_FAMILIES


# --- Test 2: registration questions do not become formal_enrollment ----------
def test_registration_question_is_not_study_enrollment():
    # Contains 등록 (registration) but is foreigner registration, not enrollment.
    facts = extract_immigration_facts("외국인등록은 언제 해야 하나요?", visa_code="H-1")
    issues = classify_legal_issue_types("외국인등록은 언제 해야 하나요?", facts)
    assert "registration_or_residence_report" in issues
    assert "reporting_duty" in issues
    assert "formal_enrollment" not in facts["proposed_activities"]
    assert "study_on_non_study_status" not in issues
    assert facts["activity_facts"]["formal_enrollment"] == "false"


def test_business_registration_is_not_study_enrollment():
    facts = extract_immigration_facts("사업자등록을 하고 사업을 할 수 있나요?", visa_code="D-10")
    assert "formal_enrollment" not in facts["proposed_activities"]


# --- Test 3: previous/current/target status roles preserved ------------------
def test_status_roles_preserved_in_transition():
    facts = extract_immigration_facts(
        "E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?"
    )
    assert facts["previous_status"] == "E-7"
    assert facts["current_status"] == "F-2-99"
    assert facts["target_status"] == "F-2-99"
    assert facts["status_transition_detected"] is True


def test_status_roles_preserved_when_current_supplied_separately():
    # "Can I change status to F-2-99?" with H-1 supplied separately.
    facts = extract_immigration_facts("Can I change status to F-2-99?", visa_code="H-1")
    assert facts["current_status"] == "H-1"
    assert facts["target_status"] == "F-2-99"


# --- Test 4: unsupported source families never become bad_response -----------
def test_unsupported_families_are_unsupported_not_bad_response():
    plan = build_generalized_source_plan(
        "체류자격외활동 허가 없이 일할 수 있나요?", law_api_attempted=True,
    )
    statuses = plan["source_family_statuses"]
    for family in SOURCE_FAMILIES:
        if family not in WIRED_SOURCE_FAMILIES and statuses.get(family) not in (None, "not_attempted"):
            assert statuses[family] != "bad_response"
            assert statuses[family] != "parse_error"
    # Unwired families that were planned are flagged unsupported.
    for family in plan["source_families_planned"]:
        if family not in WIRED_SOURCE_FAMILIES:
            assert statuses[family] == "unsupported"


def test_support_status_helper_never_returns_error_code():
    for family in SOURCE_FAMILIES:
        status = source_family_support_status(family)
        assert status in ("wired", "planned_not_wired")
        assert status not in ("bad_response", "parse_error")


# --- Test 5: empty official responses become no_results ----------------------
def test_empty_official_response_is_no_results():
    plan = build_generalized_source_plan(
        "체류자격 변경 절차를 알려주세요",
        law_api_attempted=True,
        law_sources=[],            # nothing came back
        law_grounding_status="used",
    )
    statuses = plan["source_family_statuses"]
    wired_planned = [f for f in plan["source_families_planned"] if f in WIRED_SOURCE_FAMILIES and f != "manual"]
    assert wired_planned, "expected at least one wired law family planned"
    for family in wired_planned:
        assert statuses[family] in ("no_results", "results_found", "unavailable")
    # With sources absent and status not 'unavailable', it must be no_results.
    assert any(statuses[f] == "no_results" for f in wired_planned)


# --- Test 6: legal terms are background unless tied to the direct issue ------
def test_legal_term_is_background_without_issue_match():
    facts = extract_immigration_facts("D-2 활동범위를 알려주세요", visa_code="D-2")
    item = {"source_type": "legal_term", "law_name": "법령용어", "term": "재외동포", "summary": "definition"}
    rel = score_evidence_relevance(
        item, question="D-2 활동범위를 알려주세요", visa_code="D-2",
        immigration_facts=facts,
    )
    assert rel == RELEVANCE_BACKGROUND


def test_legal_term_with_exact_issue_and_status_is_related_not_direct():
    facts = extract_immigration_facts("D-2 활동범위", visa_code="D-2")
    issues = classify_legal_issue_types("D-2 활동범위", facts)
    item = {"source_type": "legal_term", "term": "활동범위 D-2", "summary": "활동범위 정의"}
    rel = score_evidence_relevance(
        item, question="D-2 활동범위", visa_code="D-2",
        immigration_facts=facts, legal_issue_types=issues,
    )
    # Legal terms never become direct authority.
    assert rel in (RELEVANCE_RELATED, RELEVANCE_BACKGROUND)
    assert rel != RELEVANCE_DIRECT


# --- Test 7: law-only evidence does not create a document checklist ----------
def test_documents_issue_routes_manual_first():
    families = source_families_for_issue("documents_needed")
    assert families[0] == "manual", "manual must lead for document checklist authority"


def test_law_only_evidence_is_not_checklist_authority():
    # A statute item without document terms must not score as direct checklist
    # authority for a documents question.
    facts = extract_immigration_facts("D-2 연장 구비서류는 무엇인가요?", visa_code="D-2")
    issues = classify_legal_issue_types("D-2 연장 구비서류는 무엇인가요?", facts)
    law_item = {"source_type": "law", "law_name": "출입국관리법", "summary": "체류자격 일반 규정"}
    rel = score_evidence_relevance(
        law_item, question="D-2 연장 구비서류는 무엇인가요?", visa_code="D-2",
        immigration_facts=facts, legal_issue_types=issues,
    )
    assert rel in (RELEVANCE_BACKGROUND, RELEVANCE_RELATED)


# --- Test 8: previous-status evidence is comparative after a transition ------
def test_previous_status_evidence_is_comparative_not_direct():
    q = "E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?"
    facts = extract_immigration_facts(q)
    issues = classify_legal_issue_types(q, facts)
    # Evidence mentioning ONLY the previous status (E-7), not the current one.
    item = {"source_type": "law", "law_name": "출입국관리법", "summary": "E-7 근무처 변경 신고"}
    rel = score_evidence_relevance(
        item, question=q, immigration_facts=facts, legal_issue_types=issues,
    )
    assert rel in (RELEVANCE_RELATED, RELEVANCE_ANALOGICAL)
    assert rel != RELEVANCE_DIRECT


def test_previous_status_query_goal_is_not_direct():
    facts = extract_immigration_facts(
        "E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?"
    )
    issues = classify_legal_issue_types(
        "E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?", facts
    )
    plan = plan_evidence_queries(facts, issues, max_queries=10)
    for q in plan:
        if q["status_role"] == "previous_status":
            assert q["evidence_goal"] != "direct"


# --- Test 9: target-status evidence is route evidence in status change -------
def test_target_status_is_route_evidence_in_status_change():
    facts = extract_immigration_facts("Can I change status to F-2-99?", visa_code="H-1")
    issues = classify_legal_issue_types("Can I change status to F-2-99?", facts)
    assert "status_change" in issues
    plan = plan_evidence_queries(facts, issues, max_queries=10)
    target_queries = [q for q in plan if "F-2-99" in q["expected_status_codes"]]
    assert target_queries, "no target-route query for F-2-99"
    assert any(q["status_role"] == "target_status" for q in target_queries)
    # Current status is still preserved in the plan.
    assert any("H-1" in q["expected_status_codes"] for q in plan)


def test_target_status_evidence_scores_direct_for_primary_authority():
    facts = extract_immigration_facts("Can I change status to F-2-99?", visa_code="H-1")
    issues = classify_legal_issue_types("Can I change status to F-2-99?", facts)
    item = {"source_type": "statute", "law_name": "출입국관리법", "summary": "F-2-99 체류자격 변경허가"}
    rel = score_evidence_relevance(
        item, question="Can I change status to F-2-99?", visa_code="H-1",
        immigration_facts=facts, legal_issue_types=issues,
    )
    assert rel == RELEVANCE_DIRECT


# --- Test 10: evidence counts are deterministic ------------------------------
def test_evidence_counts_are_deterministic():
    q = "G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?"
    pack_a = build_law_evidence_pack(q, visa_code="G-1-5", retrieve=False)
    pack_b = build_law_evidence_pack(q, visa_code="G-1-5", retrieve=False)
    for key in (
        "direct_evidence_count", "related_evidence_count",
        "analogical_evidence_count", "background_evidence_count",
    ):
        assert pack_a[key] == pack_b[key]
    assert pack_a["evidence_goal_by_query"] == pack_b["evidence_goal_by_query"]
    assert pack_a["evidence_ontology"]["source_families_planned"] == \
        pack_b["evidence_ontology"]["source_families_planned"]


def test_no_direct_evidence_keeps_certainty_below_direct():
    # With retrieval off there is no direct law evidence, so the analysis mode
    # must not claim direct authority.
    pack = build_law_evidence_pack(
        "C-3 단기방문으로 paid work를 할 수 있나요?", visa_code="C-3", retrieve=False,
    )
    assert pack["direct_evidence_count"] == 0
    assert pack["legal_analysis"]["analysis_mode"] != "direct_authority"
    assert pack["legal_analysis"]["confidence"] in ("contextual", "analogical", "limited", "unavailable")


# --- Routing single-source-of-truth consistency -----------------------------
def test_build_generalized_source_plan_matches_routing_table():
    # The legal_analysis plan must equal the ontology routing for the issues.
    for q in (
        "외국인등록은 언제 해야 하나요?",
        "E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?",
        "Can I change status to F-2-99?",
        "C-3 단기방문으로 paid work를 할 수 있나요?",
    ):
        facts = extract_immigration_facts(q)
        issues = classify_legal_issue_types(q, facts)
        plan = build_generalized_source_plan(q, facts, issues)
        expected = route_source_families(issues) or ["manual", "statute", "legal_term"]
        assert plan["source_families_planned"] == expected


# --- Ontology snapshot is well-formed ---------------------------------------
def test_build_evidence_ontology_snapshot_shape():
    snap = build_evidence_ontology("외국인등록은 언제 해야 하나요?", visa_code="H-1")
    assert snap["ontology_version"]
    assert isinstance(snap["legal_issue_types"], list)
    assert isinstance(snap["source_families_planned"], list)
    assert isinstance(snap["evidence_query_plan"], list)
    assert snap["evidence_goal_by_query"] == [q["evidence_goal"] for q in snap["evidence_query_plan"]]
    # support map covers every planned family with a non-error state.
    for fam in snap["source_families_planned"]:
        assert snap["source_family_support"][fam] in ("wired", "planned_not_wired")


# --- Regression cases (generalized outputs only, NOT answer strings) ---------
def test_regression_h1_registration_generalized():
    snap = build_evidence_ontology("H-1 외국인등록은 언제 해야 하나요?", visa_code="H-1")
    assert "registration_or_residence_report" in snap["legal_issue_types"]
    assert "study_on_non_study_status" not in snap["legal_issue_types"]
    assert "manual" in snap["source_families_planned"]
    # No study/comparison statuses leak into the planned status codes.
    codes = [c for q in snap["evidence_query_plan"] for c in q["expected_status_codes"]]
    assert "D-2" not in codes and "D-4" not in codes


def test_regression_g15_study_generalized():
    snap = build_evidence_ontology(
        "G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?",
        visa_code="G-1-5",
    )
    assert snap["immigration_facts"]["current_status"] == "G-1-5"
    assert "study_on_non_study_status" in snap["legal_issue_types"]
    # D-2/D-4 are comparison statuses, never planned as the queried status.
    codes = [c for q in snap["evidence_query_plan"] for c in q["expected_status_codes"]]
    assert "G-1-5" in codes
    assert "D-2" not in codes and "D-4" not in codes


def test_regression_c3_paid_work_generalized():
    snap = build_evidence_ontology("C-3 단기방문으로 paid work를 할 수 있나요?", visa_code="C-3")
    assert snap["immigration_facts"]["current_status"] == "C-3"
    assert "paid_work" in snap["activity_types"]
    assert any(
        i in snap["legal_issue_types"]
        for i in ("work_on_non_work_status", "outside_status_activity", "activity_scope")
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
