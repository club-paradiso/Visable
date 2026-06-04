from __future__ import annotations

import pytest

from services.grounding_config import GroundingConfig
from services.law_tools import build_law_evidence_pack
from services.legal_analysis import build_generalized_source_plan, classify_activity_types, classify_legal_issue_types, extract_immigration_facts, score_evidence_relevance

CFG = GroundingConfig(mode="audit")

SCENARIOS = [
    ("Can I take a credit-bearing summer course on H-1?", "H-1", {"credit_bearing_study"}, {"study_on_non_study_status", "activity_scope"}),
    ("H-1으로 비학점 문화센터 취미 수업을 청강해도 되나요?", "H-1", {"non_credit_audit", "non_credit_cultural_or_hobby"}, {"study_on_non_study_status"}),
    ("G-1-5 난민소송 중 대학 정규 등록이나 계절학기 청강 가능한가요?", "G-1-5", {"formal_enrollment", "credit_bearing_study", "non_credit_audit"}, {"study_on_non_study_status", "nationality_or_refugee_context"}),
    ("G-1 치료 목적 체류인데 대학 청강 수업을 들어도 되나요?", "G-1", {"medical_treatment", "non_credit_audit"}, {"study_on_non_study_status"}),
    ("E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?", None, {"side_job"}, {"post_status_change_residual_duty", "reporting_duty"}),
    ("F-2-99로 프리랜서 외주 일을 해도 되나요?", "F-2-99", {"freelance_work"}, {"activity_scope"}),
    ("F-2-99에서 사업자등록을 내고 사업 활동이 가능한가요?", "F-2-99", {"business_activity"}, {"activity_scope"}),
    ("F-2-99인데 E-7 이력 없이 추가 고용주를 둘 수 있나요?", "F-2-99", {"additional_employment"}, {"workplace_change_addition", "reporting_duty"}),
    ("현재 E-7인데 근무처 추가를 신고해야 하나요?", "E-7", {"workplace_addition"}, {"workplace_change_addition", "reporting_duty"}),
    ("D-2 유학생인데 시간제 아르바이트를 할 수 있나요?", "D-2", {"paid_work"}, {"activity_scope"}),
    ("D-4 어학연수생인데 유급 인턴십을 해도 되나요?", "D-4", {"paid_internship"}, {"work_on_non_work_status", "employment_restriction"}),
    ("D-10 구직비자로 프리랜서 일을 해도 되나요?", "D-10", {"freelance_work"}, {"work_on_non_work_status"}),
    ("E-7인데 본업 외 부업을 해도 되나요?", "E-7", {"side_job"}, {"activity_scope"}),
    ("F-4 재외동포의 취업 제한은 어떻게 확인하나요?", "F-4", {"paid_work"}, {"employment_restriction"}),
    ("F-4 국내거소신고는 언제 해야 하나요?", "F-4", {"registration_or_reporting"}, {"registration_or_residence_report"}),
    ("F-6인데 이혼 후 체류기간 연장이 가능한가요?", "F-6", {"family_or_marriage_related", "status_extension"}, {"extension"}),
    ("B-2 무비자로 어학당 language school 수업을 들어도 되나요?", "B-2", {"language_training"}, {"study_on_non_study_status"}),
    ("C-3 단기방문으로 paid work를 할 수 있나요?", "C-3", {"paid_work"}, {"work_on_non_work_status"}),
    ("C-4와 C-3의 paid activity 차이는 무엇인가요?", "C-3", {"paid_work"}, {"activity_scope"}),
    ("체류기간이 하루 overstay 됐습니다.", None, set(), {"overstay_or_risk"}),
    ("재입국허가 re-entry permit이 필요한가요?", None, {"reentry_or_departure"}, {"reentry"}),
    ("귀화 naturalization 일반 요건은 무엇인가요?", None, set(), {"nationality_or_refugee_context"}),
    ("난민 신청 후 G-1 체류 context에서 연장해야 하나요?", "G-1", {"refugee_or_humanitarian_context", "status_extension"}, {"nationality_or_refugee_context"}),
]


@pytest.mark.parametrize("question,visa,activities,issues", SCENARIOS)
def test_generalized_regression_scenarios(question, visa, activities, issues):
    pack = build_law_evidence_pack(question, visa_code=visa, config=CFG, retrieve=False)
    facts = pack["immigration_facts"]
    legal_analysis = pack["legal_analysis"]
    assert facts["activity_facts"]
    assert activities.issubset(set(pack["proposed_activity_type"]))
    assert issues.issubset(set(pack["legal_issue_types"]))
    assert pack["source_plan"]["source_types_priority"]
    assert len(pack["planned_law_queries"]) <= 7
    assert legal_analysis["analysis_mode"]
    assert legal_analysis["risk_posture"] in {"low", "medium", "high"}
    assert legal_analysis["official_confirmation_questions"]
    assert not legal_analysis["practical_posture"].lower().startswith(("paradiso cannot", "it depends", "whether you can"))
    if facts.get("previous_status"):
        direct_titles = " ".join(a.get("title", "") for a in legal_analysis.get("direct_authority", []))
        assert facts["previous_status"] not in direct_titles


def test_status_transition_preserves_current_and_previous_substatus():
    facts = extract_immigration_facts("E-7에서 F-2-99로 변경 후 부업 신고는?")
    assert facts["previous_status"] == "E-7"
    assert facts["current_status"] == "F-2-99"
    assert facts["current_parent_status"] == "F-2"
    assert facts["current_sub_status"] == "F-2-99"
    assert facts["status_transition_detected"] is True


def test_visa_hint_preserves_in_text_target_status_for_status_change():
    pack = build_law_evidence_pack("Can I change status to F-2-99?", visa_code="H-1", config=CFG, retrieve=False)
    facts = pack["immigration_facts"]
    assert facts["current_status"] == "H-1"
    assert facts["previous_status"] == "H-1"
    assert facts["target_status"] == "F-2-99"
    assert facts["target_parent_status"] == "F-2"
    assert facts["target_sub_status"] == "F-2-99"
    assert facts["status_transition_detected"] is True
    assert "status_change" in pack["legal_issue_types"]
    assert any("F-2-99" in query for query in pack["planned_law_queries"])
    assert "F-2-99" in pack["legal_analysis"]["main_issue"]


def test_registration_phrases_are_not_school_enrollment():
    for question in [
        "H-1 외국인등록은 언제 해야 하나요?",
        "H-1에서 사업자등록을 내고 부업을 해도 되나요?",
        "F-4 국내거소신고와 외국인등록 차이는 무엇인가요?",
    ]:
        activities = set(classify_activity_types(question))
        issues = set(classify_legal_issue_types(question))
        assert "formal_enrollment" not in activities
        assert "study_on_non_study_status" not in issues


@pytest.mark.parametrize("status", ["H-1", "G-1", "F-2-99", "D-2", "D-4", "D-10", "E-7", "F-4", "F-6", "B-2", "C-3"])
def test_matrix_credit_study_non_study_statuses(status):
    issues = classify_legal_issue_types(f"I am on {status}. Can I take a credit-bearing course?")
    if status not in {"D-2", "D-4"}:
        assert {"activity_scope", "status_purpose_alignment"} & set(issues)


@pytest.mark.parametrize("status", ["H-1", "G-1", "F-2-99", "D-2", "D-4", "D-10", "E-7", "F-4", "F-6", "B-2", "C-3"])
def test_matrix_paid_work_restricted_statuses(status):
    issues = classify_legal_issue_types(f"I am on {status}. Can I do paid work?")
    if status not in {"E-7", "F-2-99", "F-4", "F-6"}:
        assert {"activity_scope", "outside_status_activity", "work_on_non_work_status"} & set(issues)


def test_matrix_workplace_addition_and_approval_condition():
    issues = classify_legal_issue_types("E-7 근무처 추가와 허가조건 신고가 필요한가요?")
    assert "workplace_change_addition" in issues
    assert "reporting_duty" in issues
    assert "approval_condition" in issues


def test_official_source_family_plans_for_required_scenarios() -> None:
    cases = [
        ("E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?", {"statute", "enforcement_rule", "administrative_rule"}, "F-2-99"),
        ("G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?", {"statute", "enforcement_decree", "enforcement_rule"}, "G-1-5"),
        ("H-1 외국인등록은 언제 해야 하나요?", {"statute", "enforcement_rule", "administrative_rule"}, "H-1"),
        ("Can I change status to F-2-99?", {"manual", "statute", "enforcement_decree"}, "H-1"),
        ("D-2 유학생인데 시간제 아르바이트를 할 수 있나요?", {"statute", "enforcement_decree", "enforcement_rule"}, "D-2"),
        ("C-3 단기방문으로 paid work를 할 수 있나요?", {"statute", "enforcement_decree", "enforcement_rule"}, "C-3"),
    ]
    for question, expected, visa in cases:
        facts = extract_immigration_facts(question, visa_code=visa)
        issues = classify_legal_issue_types(question, facts)
        plan = build_generalized_source_plan(question, facts, issues)
        planned = set(plan["source_families_planned"])
        assert expected <= planned
        assert plan["source_family_statuses"].get("precedent", "not_attempted") in {"not_attempted", "unsupported"}


def test_status_change_target_query_preserves_target_status() -> None:
    question = "Can I change status to F-2-99?"
    facts = extract_immigration_facts(question, visa_code="H-1")
    issues = classify_legal_issue_types(question, facts)
    plan = build_generalized_source_plan(question, facts, issues)
    assert facts["target_status"] == "F-2-99"
    assert any("F-2-99" in q for q in plan["queries"])


def test_previous_status_evidence_is_related_not_direct_after_change() -> None:
    question = "E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?"
    facts = extract_immigration_facts(question)
    issues = classify_legal_issue_types(question, facts)
    evidence = {"source_type": "statute", "law_name": "E-7 근무처 변경 신고", "summary": "근무처 신고의무"}
    rel = score_evidence_relevance(evidence, question=question, immigration_facts=facts, legal_issue_types=issues)
    assert rel == "related"
