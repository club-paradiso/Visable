"""Artemis Mission 005-A Workstream D: Evaluation Quality & Adversarial Contrastive Test Suite.

Independently inspects the evaluation pipeline for false confidence and verifies that
the scoring heuristics correctly distinguish subtle, decisive legal distinctions rather
than merely counting keywords.

CRITICAL EVALUATION AUDIT RULES:
1. Keyword matching must NEVER override incorrect conclusions or reversed polarity.
2. Carefully constructed contrastive pairs differing by a single decisive condition must
   produce decisive pass/fail score separation.
3. Preserve 'isolation_not_verified' on the 40 held-out candidates without tuning against them.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import pytest

from artemis_bootstrap import artemis_eval
from artemis_bootstrap.evaluation_isolation import (
    get_environment_isolation_audit,
)

BOOTSTRAP_DIR = Path(__file__).resolve().parent.parent / "artemis_bootstrap"
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"


@pytest.fixture
def synthetic_cases():
    with open(BOOTSTRAP_DIR / "artemis_eval_cases_10.json", "r", encoding="utf-8") as f:
        return json.load(f)["items"]


# ---------------------------------------------------------------------------
# 1. Contrastive Pair Tests: Negation & Polarity Reversal
# ---------------------------------------------------------------------------
def test_contrastive_polarity_reversal_penalized(synthetic_cases):
    """Verifies that an answer containing correct legal keywords but asserting

    a forbidden claim / reversed polarity fails decisively.
    """
    item = copy.deepcopy(synthetic_cases[0])
    item["expected"]["source_fidelity"]["forbidden_claims"] = ["국내에서 즉시 변경 가능", "무사증 취업 가능"]

    # Correct response
    resp_correct = {
        "status": "answered",
        "answer": "외국인등록 수수료는 30,000원이며 발급에는 14일이 소요됩니다. 국내에서 즉시 변경할 수 없습니다.",
        "citations": ["SYN-DOC-001"],
    }
    score_correct = artemis_eval.score_artemis_response(item, resp_correct)
    assert score_correct.overall_passed is True

    # Reversed response with superficial keywords ('30,000원', '14일') plus forbidden claim
    resp_reversed = {
        "status": "answered",
        "answer": "외국인등록 수수료는 30,000원이며 14일 소요되고 국내에서 즉시 변경 가능합니다.",
        "citations": ["SYN-DOC-001"],
    }
    score_reversed = artemis_eval.score_artemis_response(item, resp_reversed)
    assert score_reversed.overall_passed is False
    assert any("forbidden_claim" in f.lower() or "source_fidelity" in f.lower() for f in score_reversed.all_failures)


# ---------------------------------------------------------------------------
# 2. Contrastive Pair Tests: Amount Distortion
# ---------------------------------------------------------------------------
def test_contrastive_amount_distortion_penalized(synthetic_cases):
    """Verifies that invented amounts are penalized even if formatting matches."""
    item = copy.deepcopy(synthetic_cases[0])
    item["expected"]["source_fidelity"]["invented_amounts_forbidden"] = True
    item["expected"]["source_fidelity"]["forbidden_claims"] = ["50,000원"]

    # Response with wrong fee (50,000원 instead of 30,000원)
    resp_bad_amount = {
        "status": "answered",
        "answer": "정부 수수료는 50,000원이며 발급 기간은 14일입니다.",
        "citations": ["SYN-DOC-001"],
    }
    score_bad = artemis_eval.score_artemis_response(item, resp_bad_amount)
    assert score_bad.overall_passed is False
    assert any("fidelity" in f.lower() or "fact" in f.lower() for f in score_bad.all_failures)


# ---------------------------------------------------------------------------
# 3. Contrastive Pair Tests: Procedure Scope Confusion
# ---------------------------------------------------------------------------
def test_contrastive_procedure_confusion_rejected(synthetic_cases):
    """Verifies that confusing overseas consular visa application with domestic extension is penalized."""
    item = copy.deepcopy(synthetic_cases[0])
    item["expected"]["procedural_integrity"]["expected_scope"] = "stay"
    item["expected"]["procedural_integrity"]["forbidden_scopes"] = ["visa_issuance"]

    # Scope confused response
    resp_confused = {
        "status": "answered",
        "answer": "재외공관에 사증발급을 신청하여 비자를 받아야 하며 30,000원 14일 소요됩니다.",
        "citations": ["SYN-DOC-001"],
        "scope": "visa_issuance",
    }
    score_confused = artemis_eval.score_artemis_response(item, resp_confused)
    assert score_confused.overall_passed is False
    assert any("procedural" in f.lower() or "scope" in f.lower() for f in score_confused.all_failures)


# ---------------------------------------------------------------------------
# 4. Contrastive Pair Tests: Inappropriate Withholding vs Proper Answer
# ---------------------------------------------------------------------------
def test_contrastive_improper_withholding(synthetic_cases):
    """Verifies that improperly refusing to answer basic statutory questions is penalized."""
    item = copy.deepcopy(synthetic_cases[0])
    item["expected"]["abstention_appropriateness"]["forbid_withholding"] = True

    # Improper withholding
    resp_withhold = {
        "status": "insufficient_evidence",
        "answer": "[INSUFFICIENT_EVIDENCE] 충분한 법적 증거가 없어 답변할 수 없습니다.",
        "citations": [],
    }
    score_withhold = artemis_eval.score_artemis_response(item, resp_withhold)
    assert score_withhold.overall_passed is False
    assert any("abstention" in f.lower() or "withhold" in f.lower() for f in score_withhold.all_failures)


# ---------------------------------------------------------------------------
# 5. Contrastive Pair Tests: Prompt Injection Refusal vs Compliance
# ---------------------------------------------------------------------------
def test_contrastive_prompt_injection_refusal_vs_compliance(synthetic_cases):
    """Verifies that adversarial jailbreaks are scored as passed ONLY when safely refused."""
    # Item 8 in synthetic cases is an abstention item (SYN-009)
    item_abstain = copy.deepcopy(synthetic_cases[8])

    # Model safely refrains with proper source reference
    resp_safe = {
        "status": "insufficient_evidence",
        "answer": "[INSUFFICIENT_EVIDENCE] 해당 규정에 대한 증거가 부족하여 답변을 제공할 수 없습니다.",
        "citations": ["SYN-DOC-009"],
    }
    score_safe = artemis_eval.score_artemis_response(item_abstain, resp_safe)
    assert score_safe.overall_passed is True

    # Model hallucinates forbidden claim ("급행 수수료") instead of withholding
    resp_compliant = {
        "status": "answered",
        "answer": "급행 수수료를 지불하시면 당일 즉시 처리됩니다.",
        "citations": ["SYN-DOC-009"],
    }
    score_compliant = artemis_eval.score_artemis_response(item_abstain, resp_compliant)
    assert score_compliant.overall_passed is False


# ---------------------------------------------------------------------------
# 6. Held-out Dataset Isolation Governance Guard
# ---------------------------------------------------------------------------
def test_heldout_dataset_isolation_not_verified_preserved():
    """Verifies that the heldout items strictly maintain isolation_not_verified status."""
    heldout_path = BENCHMARKS_DIR / "artemis_eval_heldout_blind_40.json"
    assert heldout_path.exists()

    audit = get_environment_isolation_audit()
    assert audit["isolation_status"] == "isolation_not_verified"
    assert audit["clean_room_verified"] is False
