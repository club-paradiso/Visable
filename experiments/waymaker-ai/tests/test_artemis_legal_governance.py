"""Unit and regression tests for Artemis Legal Review Governance (Mission 004-C).

Verifies:
1. Ledger initialization from candidate benchmark (60 items, Group A: 16, Group B: 44).
2. Controlled review state transitions (unreviewed -> in_review -> verified_by_human / rejected / needs_revision / superseded).
3. Prohibition of AI agent impersonation (AIApprovalForbiddenError).
4. Review integrity constraints (reviewer identity, substantive reasons, cryptographic snapshots).
5. Promotional gating to official gold and integration with artemis_eval scoring.
6. Audit ledger persistence and markdown reporting.
"""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
import pytest

from artemis_bootstrap.legal_review_governance import (
    AIApprovalForbiddenError,
    ArtemisReviewRecord,
    InvalidTransitionError,
    LegalReviewLedger,
    ReviewDecision,
    ReviewIntegrityError,
    ReviewStatus,
    compute_evidence_snapshot_hash,
    is_ai_identifier,
)
from artemis_bootstrap import artemis_eval


BOOTSTRAP_DIR = Path(__file__).resolve().parent.parent / "artemis_bootstrap"
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"


@pytest.fixture
def fresh_ledger(tmp_path):
    ledger_file = tmp_path / "test_ledger.json"
    candidates_file = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    return LegalReviewLedger.load_or_initialize(ledger_path=ledger_file, candidates_path=candidates_file)


# ---------------------------------------------------------------------------
# 1. Ledger Initialization & Partition Tests
# ---------------------------------------------------------------------------
def test_ledger_initialization_and_group_partition(fresh_ledger):
    assert len(fresh_ledger.records) == 60

    counts = fresh_ledger.get_status_counts()
    assert counts[ReviewStatus.UNREVIEWED.value] == 60
    assert counts[ReviewStatus.VERIFIED_BY_HUMAN.value] == 0

    group_a = [r for r in fresh_ledger.records.values() if "Group A" in r.group]
    group_b = [r for r in fresh_ledger.records.values() if "Group B" in r.group]

    assert len(group_a) == 16
    assert len(group_b) == 44

    # All items initially carry is_human_reviewer = False
    assert all(r.is_human_reviewer is False for r in fresh_ledger.records.values())


# ---------------------------------------------------------------------------
# 2. AI Identification & Prohibition Tests
# ---------------------------------------------------------------------------
def test_ai_identifier_detection():
    ai_names = ["gemini-agent", "claude_bot", "chatgpt_reviewer", "artemis_auto", "subsystem_llm"]
    human_names = ["attorney_hong", "minwon_officer_kim", "luca_admin", "legal_counsel_lee"]

    for name in ai_names:
        assert is_ai_identifier(name) is True, f"Failed to identify AI: {name}"

    for name in human_names:
        assert is_ai_identifier(name) is False, f"Falsely identified human as AI: {name}"


def test_ai_actor_cannot_claim_or_approve(fresh_ledger):
    item_id = "ARTEMIS-004-DEV-001"

    # 1. AI cannot claim
    with pytest.raises(AIApprovalForbiddenError):
        fresh_ledger.claim_for_review(item_id, reviewer_id="gemini_agent", is_human=True)

    with pytest.raises(AIApprovalForbiddenError):
        fresh_ledger.claim_for_review(item_id, reviewer_id="human_name", is_human=False)

    # Claim legitimately first
    fresh_ledger.claim_for_review(item_id, reviewer_id="attorney_kim", is_human=True)

    # 2. AI cannot record decision
    with pytest.raises(AIApprovalForbiddenError):
        fresh_ledger.record_decision(
            item_id,
            decision=ReviewDecision.APPROVE,
            reviewer_id="claude_bot",
            reason="AI generated approval",
            is_human=True,
        )


# ---------------------------------------------------------------------------
# 3. State Machine & Controlled Transitions Tests
# ---------------------------------------------------------------------------
def test_legal_review_approval_lifecycle(fresh_ledger):
    item_id = "ARTEMIS-004-DEV-001"

    # Step 1: Claim
    rec = fresh_ledger.claim_for_review(item_id, reviewer_id="attorney_kim", is_human=True)
    assert rec.review_status == ReviewStatus.IN_REVIEW
    assert rec.reviewer_id == "attorney_kim"
    assert rec.is_human_reviewer is True
    assert len(rec.transition_history) == 1

    # Step 2: Approve
    evidence_text = "B-2 관광 자격 소지자는 국내에서 D-2 체류자격으로의 변경이 원칙적으로 제한됩니다."
    rec = fresh_ledger.record_decision(
        item_id,
        decision=ReviewDecision.APPROVE,
        reviewer_id="attorney_kim",
        reason="출입국관리법 시행령 제24조 및 2026 체류관리편람 대조 확인 완료",
        is_human=True,
        evidence_snapshot_text=evidence_text,
    )
    assert rec.review_status == ReviewStatus.VERIFIED_BY_HUMAN
    assert rec.decision == ReviewDecision.APPROVE
    assert rec.evidence_snapshot_sha256 == compute_evidence_snapshot_hash(evidence_text)
    assert len(rec.transition_history) == 2


def test_invalid_transitions_rejected(fresh_ledger):
    item_id = "ARTEMIS-004-DEV-002"

    # Cannot approve directly from UNREVIEWED without claiming first
    with pytest.raises(InvalidTransitionError):
        fresh_ledger.record_decision(
            item_id,
            decision=ReviewDecision.APPROVE,
            reviewer_id="attorney_kim",
            reason="Direct approval attempt",
            is_human=True,
        )


def test_rejection_and_revision_requests(fresh_ledger):
    item_id = "ARTEMIS-004-DEV-003"
    fresh_ledger.claim_for_review(item_id, reviewer_id="attorney_park", is_human=True)

    # Request revision
    rec = fresh_ledger.record_decision(
        item_id,
        decision=ReviewDecision.REQUEST_REVISION,
        reviewer_id="attorney_park",
        reason="해당 조항의 단서 규정(예외 조건)이 답변에 누락됨",
        is_human=True,
    )
    assert rec.review_status == ReviewStatus.NEEDS_REVISION

    # Can be re-claimed after needs_revision
    fresh_ledger.claim_for_review(item_id, reviewer_id="attorney_park", is_human=True)
    assert fresh_ledger.records[item_id].review_status == ReviewStatus.IN_REVIEW

    # Can be rejected
    rec_rej = fresh_ledger.record_decision(
        item_id,
        decision=ReviewDecision.REJECT,
        reviewer_id="attorney_park",
        reason="공식 법령 근거와 불일치하며 폐지된 구 규정임",
        is_human=True,
    )
    assert rec_rej.review_status == ReviewStatus.REJECTED


def test_supersede_lifecycle(fresh_ledger):
    item_id = "ARTEMIS-004-DEV-004"
    fresh_ledger.claim_for_review(item_id, reviewer_id="attorney_lee", is_human=True)
    fresh_ledger.record_decision(
        item_id,
        decision=ReviewDecision.APPROVE,
        reviewer_id="attorney_lee",
        reason="현행 지침 일치 확인",
        is_human=True,
    )

    # Supersede can only happen from VERIFIED_BY_HUMAN
    rec_sup = fresh_ledger.record_decision(
        item_id,
        decision=ReviewDecision.SUPERSEDE,
        reviewer_id="attorney_lee",
        reason="2026년 하반기 직제 개편에 따라 신설 규정으로 대체됨",
        is_human=True,
    )
    assert rec_sup.review_status == ReviewStatus.SUPERSEDED


# ---------------------------------------------------------------------------
# 4. Review Integrity Validations
# ---------------------------------------------------------------------------
def test_review_integrity_constraints(fresh_ledger):
    item_id = "ARTEMIS-004-DEV-005"

    # Empty reviewer id
    with pytest.raises(ReviewIntegrityError):
        fresh_ledger.claim_for_review(item_id, reviewer_id="", is_human=True)

    fresh_ledger.claim_for_review(item_id, reviewer_id="attorney_kim", is_human=True)

    # Reason too short (< 5 chars)
    with pytest.raises(ReviewIntegrityError):
        fresh_ledger.record_decision(
            item_id,
            decision=ReviewDecision.APPROVE,
            reviewer_id="attorney_kim",
            reason="ok",
            is_human=True,
        )


# ---------------------------------------------------------------------------
# 5. Promotional Gating to Official Gold
# ---------------------------------------------------------------------------
def test_promotion_gate_enforces_human_verification(fresh_ledger):
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    candidates = json.loads(cand_path.read_text(encoding="utf-8"))["items"]
    item = candidates[0]
    cid = item["id"]

    # 1. Unreviewed item CANNOT be promoted
    with pytest.raises(ReviewIntegrityError):
        fresh_ledger.promote_to_gold(item)

    # 2. Legitimate human verification
    fresh_ledger.claim_for_review(cid, reviewer_id="independent_attorney", is_human=True)
    ev_text = item["evidence"][0]["text"]
    fresh_ledger.record_decision(
        cid,
        decision=ReviewDecision.APPROVE,
        reviewer_id="independent_attorney",
        reason="법령 조문 및 지침 대조 전수 확인 완료",
        is_human=True,
        evidence_snapshot_text=ev_text,
    )

    # 3. Successful promotion
    promoted = fresh_ledger.promote_to_gold(item)
    assert promoted["metadata"]["candidate_status"] == "official_gold"
    assert promoted["metadata"]["needs_human_review"] is False
    assert promoted["evidence"][0]["source"]["approval_state"] == "approved"
    assert promoted["evidence"][0]["source"]["review_status"] == "verified_by_human"
    assert promoted["evidence"][0]["source"]["reviewed_by"] == "independent_attorney"
    assert bool(promoted["evidence"][0]["source"]["reviewed_at"])

    # 4. Promoted item now passes is_official_gold check in artemis_eval!
    resp = {
        "status": "answered",
        "answer": "B-2 관광 자격 소지자는 국내에서 D-2 체류자격으로의 변경이 원칙적으로 제한됩니다. 재외공관에서 사증을 발급받아야 합니다.",
        "citations": [promoted["evidence"][0]["id"]],
    }
    score = artemis_eval.score_artemis_response(promoted, resp, allow_candidate_sources=False)
    assert score.is_official_gold is True
    assert score.overall_passed is True


# ---------------------------------------------------------------------------
# 6. Persistence and Markdown Audit Reporting
# ---------------------------------------------------------------------------
def test_ledger_persistence_and_markdown(tmp_path, fresh_ledger):
    ledger_path = tmp_path / "saved_ledger.json"
    item_id = "ARTEMIS-004-DEV-001"
    fresh_ledger.claim_for_review(item_id, reviewer_id="attorney_kim", is_human=True)
    fresh_ledger.save(ledger_path)

    # Reload
    reloaded = LegalReviewLedger.load_or_initialize(ledger_path=ledger_path)
    assert reloaded.records[item_id].review_status == ReviewStatus.IN_REVIEW
    assert reloaded.records[item_id].reviewer_id == "attorney_kim"

    # Markdown report
    md = reloaded.generate_markdown_report()
    assert "# Artemis 법률 검토 거버넌스 원장 보고서" in md
    assert "ARTEMIS-004-DEV-001" in md
    assert "attorney_kim" in md
