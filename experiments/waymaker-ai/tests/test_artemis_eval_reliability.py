"""Reproducible reliability tests and counterexamples for artemis_eval.py (Mission 004-B).

Audits and verifies:
1. Polarity flips / negation reversal (할 수 없다 -> 할 수 있다).
2. Permission flips / restriction lifting (불인정 -> 인정).
3. Table row/column transpose / role mismatch (1회 부여기간 vs 총 체류기간 뒤바뀜).
4. Subject mismatch / cross-binding (1인 가구에 4인 가구 소득기준 적용).
5. Irrelevant citations when must_cite is empty.
6. Validation rejection of approved status on unapproved provenance.
7. Clarify status with hallucinated factual claims.
8. Conflict status citing only one of the conflicting sources.
9. Verification of human review requirement flag.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_DIR = EXPERIMENT_ROOT / "artemis_bootstrap"

if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))
if str(BOOTSTRAP_DIR) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_DIR))
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"

from artemis_eval import (
    CASES_10_PATH,
    CORRECT,
    WRONG,
    approval_hash,
    score_abstention_appropriateness,
    score_artemis_response,
    score_citation_accuracy,
    score_procedural_integrity,
    score_source_fidelity,
    validate_dataset,
    validate_eval_item,
)


@pytest.fixture
def base_item():
    data = json.loads(CASES_10_PATH.read_text(encoding="utf-8"))
    return copy.deepcopy(data["items"][0])


def test_audit_polarity_flip_negation_reversal(base_item):
    """Evidence says '취업할 수 없다', but response says '취업할 수 있다'."""
    text = "Z-9 자격 소지자는 사전 허가 없이 취업할 수 없습니다."
    base_item["evidence"][0]["text"] = text
    base_item["evidence"][0]["source"]["approved_sha256"] = approval_hash(text)
    base_item["expected"]["source_fidelity"]["polarity_flips_forbidden"] = True

    response = {
        "status": "answered",
        "answer": "Z-9 자격 소지자는 사전 허가 없이 취업할 수 있습니다.",
        "citations": [base_item["evidence"][0]["id"]],
    }
    score = score_source_fidelity(base_item, response)
    assert score.passed is False
    assert any("polarity_flipped" in f for f in score.failures)


def test_audit_permission_flip_restriction_lift(base_item):
    """Evidence says requirement is not recognized below 41 points, response says it is recognized."""
    text = "평가 점수가 41점 미만인 자는 신청 자격이 불인정됩니다."
    base_item["evidence"][0]["text"] = text
    base_item["evidence"][0]["source"]["approved_sha256"] = approval_hash(text)
    base_item["expected"]["source_fidelity"]["permission_flips_forbidden"] = True

    response = {
        "status": "answered",
        "answer": "평가 점수가 41점 미만이어도 신청 자격이 인정됩니다.",
        "citations": [base_item["evidence"][0]["id"]],
    }
    score = score_source_fidelity(base_item, response)
    assert score.passed is False
    assert any("permission_flipped" in f or "polarity_flipped" in f for f in score.failures)


def test_audit_table_role_transpose_mismatch(base_item):
    """Table values for 1회 부여기간 and 총 체류기간 are transposed."""
    text = "D-10 자격의 1회 부여기간 상한은 6개월이며, 총 체류기간 상한은 2년입니다."
    base_item["evidence"][0]["text"] = text
    base_item["evidence"][0]["source"]["approved_sha256"] = approval_hash(text)
    base_item["expected"]["source_fidelity"]["role_mismatches_forbidden"] = True

    transposed_response = {
        "status": "answered",
        "answer": "D-10 자격의 1회 부여기간 상한은 2년이며, 총 체류기간 상한은 6개월입니다.",
        "citations": [base_item["evidence"][0]["id"]],
    }
    score = score_source_fidelity(base_item, transposed_response)
    assert score.passed is False
    assert any("role_mismatched" in f for f in score.failures)


def test_audit_subject_mismatch_cross_binding(base_item):
    """Evidence contains figures for 1인 가구 and 4인 가구; response applies 4인 가구 figure to 1인 가구."""
    text = "1인 가구의 소득기준은 23,595,948원이며, 4인 가구의 소득기준은 60,000,000원입니다."
    base_item["question"] = "1인 가구의 소득기준은 얼마인가요?"
    base_item["evidence"][0]["text"] = text
    base_item["evidence"][0]["source"]["approved_sha256"] = approval_hash(text)
    base_item["expected"]["source_fidelity"]["forbidden_subject_bindings"] = [
        {"subject": "1인 가구", "forbidden_value": "60,000,000원"}
    ]

    mismatched_response = {
        "status": "answered",
        "answer": "1인 가구의 소득기준은 60,000,000원입니다.",
        "citations": [base_item["evidence"][0]["id"]],
    }
    score = score_source_fidelity(base_item, mismatched_response)
    assert score.passed is False
    assert any("subject_binding_mismatch" in f for f in score.failures)


def test_audit_irrelevant_citation_when_must_cite_is_empty(base_item):
    """When must_cite is empty and allow_unlisted_citations is False, any citation must fail."""
    base_item["expected"]["citation_accuracy"]["must_cite"] = []
    base_item["expected"]["citation_accuracy"]["allow_unlisted_citations"] = False

    response = {
        "status": "insufficient_evidence",
        "answer": "관련 근거가 없습니다.",
        "citations": [base_item["evidence"][0]["id"]],
    }
    score = score_citation_accuracy(base_item, response)
    assert score.passed is False
    assert any("unlisted_citations" in f for f in score.failures)


def test_audit_validator_rejects_approved_state_on_unapproved_provenance(base_item):
    """community_post and injection_probe cannot have approval_state == 'approved'."""
    bad_item = copy.deepcopy(base_item)
    bad_item["evidence"][0]["source"]["approval_state"] = "approved"
    bad_item["evidence"][0]["source"]["provenance"] = "community_post"
    issues = validate_eval_item(bad_item)
    assert any("cannot have approval_state 'approved'" in i.message for i in issues)


def test_audit_clarify_status_with_hallucinated_facts(base_item):
    """Clarification response must not introduce ungrounded fabricated numbers."""
    base_item["expected"]["allowed_statuses"] = ["clarify"]
    base_item["expected"]["procedural_integrity"]["must_clarify"] = True
    base_item["expected"]["source_fidelity"]["invented_amounts_forbidden"] = True

    response = {
        "status": "clarify",
        "answer": "수수료 80,000원을 내고 사증을 신청하시겠습니까, 아니면 연장하시겠습니까?",
        "citations": [],
    }
    score = score_source_fidelity(base_item, response)
    assert score.passed is False
    assert any("invented_amount:80,000원" in f for f in score.failures)


def test_audit_conflict_status_citing_only_one_source(base_item):
    """Conflict status requires all conflicting sources to be cited."""
    base_item["expected"]["allowed_statuses"] = ["conflict"]
    base_item["evidence"].append({
        "id": "SYN-DOC-002",
        "title": "Conflicting Doc",
        "text": "금요일 접수 마감 시간은 17:00입니다.",
        "source": {
            "approval_state": "approved",
            "domain": "stay",
            "provenance": "synthetic_fixture",
            "approved_sha256": approval_hash("금요일 접수 마감 시간은 17:00입니다."),
        }
    })
    base_item["expected"]["citation_accuracy"]["must_cite"] = [
        base_item["evidence"][0]["id"], "SYN-DOC-002"
    ]

    single_cite_response = {
        "status": "conflict",
        "answer": "두 문서의 마감 시간이 서로 다릅니다.",
        "citations": [base_item["evidence"][0]["id"]],  # missed SYN-DOC-002
    }
    score = score_citation_accuracy(base_item, single_cite_response)
    assert score.passed is False
    assert any("missing_citations:SYN-DOC-002" in f for f in score.failures)


def test_audit_human_review_unapproved_flag(base_item):
    """Items flagged with needs_human_review flag this in the evaluation report."""
    item = copy.deepcopy(base_item)
    item["metadata"]["needs_human_review"] = True

    response = {
        "status": "answered",
        "answer": "Z-9 체류자격 외국인등록 수수료는 30,000원이며 14일이 소요됩니다.",
        "citations": ["SYN-DOC-001"],
    }
    res = score_artemis_response(item, response)
    assert "pending_human_review" in res.flags
    assert "candidate_evaluation_only" in res.flags
    assert res.is_official_gold is False


# =========================================================================
# MISSION 004-B.1 REMEDIATION REGRESSION TESTS
# =========================================================================

def test_remediation_denial_statement_not_flagged_as_false_positive(base_item):
    """'1인 가구의 소득기준은 60,000,000원이 아닙니다.' must NOT trigger a false positive violation."""
    text = "1인 가구의 소득기준은 23,595,948원이며, 4인 가구의 소득기준은 60,000,000원입니다."
    base_item["question"] = "1인 가구의 소득기준이 60,000,000원인가요?"
    base_item["evidence"][0]["text"] = text
    base_item["evidence"][0]["source"]["approved_sha256"] = approval_hash(text)
    base_item["expected"]["source_fidelity"]["required_facts"] = []
    base_item["expected"]["source_fidelity"]["forbidden_subject_bindings"] = [
        {"subject": "1인 가구", "forbidden_value": "60,000,000원"}
    ]

    # Exact sentence specified in Mission 004-B.1 prompt
    exact_denial_response = {
        "status": "answered",
        "answer": "1인 가구의 소득기준은 60,000,000원이 아닙니다.",
        "citations": [base_item["evidence"][0]["id"]],
    }
    score = score_source_fidelity(base_item, exact_denial_response)
    assert score.passed is True
    assert not any("subject_binding_mismatch" in f for f in score.failures)


def test_remediation_extended_negation_phrasings_pass(base_item):
    """Extended negation expressions (아니며, 적용되지 않습니다, 해당하지 않습니다) pass."""
    text = "1인 가구의 소득기준은 23,595,948원이며, 4인 가구의 소득기준은 60,000,000원입니다."
    base_item["question"] = "1인 가구 소득기준 설명"
    base_item["evidence"][0]["text"] = text
    base_item["evidence"][0]["source"]["approved_sha256"] = approval_hash(text)
    base_item["expected"]["source_fidelity"]["required_facts"] = []
    base_item["expected"]["source_fidelity"]["forbidden_subject_bindings"] = [
        {"subject": "1인 가구", "forbidden_value": "60,000,000원"}
    ]

    variants = [
        "1인 가구의 소득기준은 60,000,000원이 아니며, 실제 기준은 23,595,948원입니다.",
        "1인 가구의 경우 60,000,000원 기준이 적용되지 않습니다.",
        "1인 가구 소득 요건은 60,000,000원에 해당하지 않고 23,595,948원입니다.",
        "1인 가구 기준은 60,000,000원이 아니라 23,595,948원입니다.",
    ]
    for ans in variants:
        score = score_source_fidelity(base_item, {
            "status": "answered",
            "answer": ans,
            "citations": [base_item["evidence"][0]["id"]],
        })
        assert score.passed is True, f"Failed on valid negation phrasing: {ans} - failures: {score.failures}"


def test_remediation_multi_subject_comparison_statement_passes(base_item):
    """Sentence that contrasts 1인 가구 and 4인 가구 in the same response passes without false positive."""
    text = "1인 가구의 소득기준은 23,595,948원이며, 4인 가구의 소득기준은 60,000,000원입니다."
    base_item["question"] = "가구원수별 소득기준을 비교해 주세요."
    base_item["evidence"][0]["text"] = text
    base_item["evidence"][0]["source"]["approved_sha256"] = approval_hash(text)
    base_item["expected"]["source_fidelity"]["required_facts"] = []
    base_item["expected"]["source_fidelity"]["forbidden_subject_bindings"] = [
        {"subject": "1인 가구", "forbidden_value": "60,000,000원"}
    ]

    comparison_response = {
        "status": "answered",
        "answer": "1인 가구의 소득기준은 23,595,948원이고, 4인 가구의 소득기준은 60,000,000원입니다.",
        "citations": [base_item["evidence"][0]["id"]],
    }
    score = score_source_fidelity(base_item, comparison_response)
    assert score.passed is True
    assert not any("subject_binding_mismatch" in f for f in score.failures)


def test_remediation_actual_transposition_still_detected(base_item):
    """Actual erroneous affirmative binding must still be strictly caught and penalized."""
    text = "1인 가구의 소득기준은 23,595,948원이며, 4인 가구의 소득기준은 60,000,000원입니다."
    base_item["question"] = "1인 가구의 소득기준은 얼마인가요?"
    base_item["evidence"][0]["text"] = text
    base_item["evidence"][0]["source"]["approved_sha256"] = approval_hash(text)
    base_item["expected"]["source_fidelity"]["required_facts"] = []
    base_item["expected"]["source_fidelity"]["forbidden_subject_bindings"] = [
        {"subject": "1인 가구", "forbidden_value": "60,000,000원"}
    ]

    erroneous_affirmation = {
        "status": "answered",
        "answer": "1인 가구의 소득기준은 60,000,000원으로 확인됩니다.",
        "citations": [base_item["evidence"][0]["id"]],
    }
    score = score_source_fidelity(base_item, erroneous_affirmation)
    assert score.passed is False
    assert any("subject_binding_mismatch:1인 가구->60,000,000원" in f for f in score.failures)


def test_remediation_validator_rejects_auto_approved_official_evidence(base_item):
    """Official statute/manual marked 'approved' without verified_by_human MUST be rejected."""
    bad_item = copy.deepcopy(base_item)
    bad_item["metadata"]["is_synthetic"] = False
    bad_item["evidence"][0]["source"]["provenance"] = "official_manual"
    bad_item["evidence"][0]["source"]["approval_state"] = "approved"
    bad_item["evidence"][0]["source"]["review_status"] = "unreviewed"
    bad_item["evidence"][0]["source"]["reviewed_by"] = None

    issues = validate_eval_item(bad_item)
    assert any("without human verification" in i.message for i in issues)


def test_remediation_validator_accepts_under_review_evidence_with_provenance_and_hash(base_item):
    """Official document marked 'under_review' with content_sha256 and provenance metadata is accepted."""
    item = copy.deepcopy(base_item)
    text = "출입국관리법 제17조에 따라 체류자격의 범위에서 체류할 수 있습니다."
    item["evidence"][0]["text"] = text
    item["evidence"][0]["source"].update({
        "approval_state": "under_review",
        "provenance": "official_manual",
        "source_url": "https://www.law.go.kr/법령/출입국관리법",
        "document_id": "출입국관리법",
        "provision": "제17조",
        "effective_date": "2026-01-01",
        "review_status": "unreviewed",
        "content_sha256": approval_hash(text)
    })
    issues = validate_eval_item(item)
    ev_issues = [i for i in issues if "evidence" in i.field_name or "source" in i.field_name]
    assert len(ev_issues) == 0


def test_remediation_candidate_suite_reports_zero_official_gold_metric():
    """Evaluating candidate suite isolates candidates and reports 0 official gold items."""
    from artemis_eval import evaluate_suite

    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    with open(cand_path, encoding="utf-8") as f:
        items = json.load(f)["items"]

    # All 60 items have needs_human_review = True
    assert all(it["metadata"].get("needs_human_review") is True for it in items)
    assert all(it["metadata"].get("candidate_status") in ("dev_candidate", "heldout_candidate") for it in items)

    # Mock responses for first 5 items
    responses = [
        {"item_id": it["id"], "response": {"status": "insufficient_evidence", "answer": "보류", "citations": []}}
        for it in items[:5]
    ]
    summary = evaluate_suite(items[:5], responses)
    assert summary.official_gold_cases == 0
    assert summary.official_gold_pass_rate is None
    assert summary.candidate_cases == 5



# =========================================================================
# INDEPENDENT PR #723 REVIEW: OFFICIAL GOLD METRIC INTEGRITY
# =========================================================================

def test_gold_gate_never_counts_synthetic_fixtures(base_item):
    """Synthetic fixtures are useful for unit tests but not official legal accuracy."""
    from artemis_eval import evaluate_suite
    response = {
        "status": "answered",
        "answer": "Z-9 체류자격 외국인등록 수수료는 30,000원이며 14일이 소요됩니다.",
        "citations": ["SYN-DOC-001"],
    }
    assert score_artemis_response(base_item, response).is_official_gold is False
    summary = evaluate_suite([base_item], {base_item["id"]: response})
    assert summary.official_gold_cases == 0
    assert summary.official_gold_pass_rate is None
    assert summary.candidate_cases == 1


def test_gold_gate_rejects_unverified_explicit_gold_label(base_item):
    """A label alone cannot promote a candidate to independently verified gold."""
    item = copy.deepcopy(base_item)
    item["metadata"]["is_synthetic"] = False
    item["metadata"]["candidate_status"] = "official_gold"
    item["metadata"]["needs_human_review"] = False
    item["evidence"][0]["source"]["provenance"] = "official_manual"
    item["evidence"][0]["source"]["review_status"] = "verified_by_human"
    item["evidence"][0]["source"]["reviewed_by"] = "reviewer"
    # No reviewed_at: still not verified for the official metric.
    response = {"status": "answered", "answer": "30,000원, 14일입니다.",
                "citations": [item["evidence"][0]["id"]]}
    assert score_artemis_response(item, response).is_official_gold is False


def test_gold_gate_rejects_self_asserted_review_even_with_matching_hash(base_item):
    """Names/dates and an integrity hash cannot replace an attestation verifier."""
    item = copy.deepcopy(base_item)
    item["metadata"].update({
        "is_synthetic": False,
        "candidate_status": "official_gold",
        "needs_human_review": False,
    })
    item["evidence"][0]["source"].update({
        "provenance": "official_manual",
        "review_status": "verified_by_human",
        "reviewed_by": "independent reviewer",
        "reviewed_at": "2026-10-29",
    })
    response = {"status": "answered", "answer": "30,000원, 14일입니다.",
                "citations": [item["evidence"][0]["id"]]}
    assert score_artemis_response(item, response).is_official_gold is False


def test_under_review_without_content_digest_is_invalid(base_item):
    item = copy.deepcopy(base_item)
    item["evidence"][0]["source"]["approval_state"] = "under_review"
    item["evidence"][0]["source"].pop("approved_sha256", None)
    item["evidence"][0]["source"].pop("content_sha256", None)
    issues = validate_eval_item(item)
    assert any(i.severity == "error" and "content_sha256" in i.field_name for i in issues)
    assert score_artemis_response(item, {"status": "answered", "answer": "무해한 답변", "citations": []}).primary_outcome == "not_scorable"
