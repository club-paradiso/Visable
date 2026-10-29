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
