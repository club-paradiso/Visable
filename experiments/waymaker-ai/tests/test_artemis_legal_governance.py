"""Unit and regression tests for Artemis Legal Review Governance (Mission 004-C Prototype).

Verifies:
1. Ledger initialization from candidate benchmark (60 items, Group A: 16, Group B: 44).
2. Controlled review state transitions (unreviewed -> in_review -> verified_by_human / rejected / needs_revision / superseded).
3. Prohibition of AI agent claiming and decision recording (AIApprovalForbiddenError).
4. Review integrity constraints (reviewer identity, substantive reasons, cryptographic snapshots).
5. Protection against spoofed human identity: caller-supplied names and is_human=True flags cannot authorize official gold.
6. Rejection of missing, empty, or mismatched official evidence snapshots.
7. Rejection of candidate items whose evidence was modified after review (tamper detection).
8. Rejection of mismatched source content hashes and non-official evidence provenance.
9. Fail-closed authoritative gold promotion gating (AuthoritativeGoldPromotionDisabledError).
10. Preservation of all 60 candidate items as unreviewed in the repository ledger.
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
    AuthoritativeGoldPromotionDisabledError,
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
    ev_text = fresh_ledger.records[item_id].evidence_references[0]["text_excerpt"]
    with pytest.raises(AIApprovalForbiddenError):
        fresh_ledger.record_decision(
            item_id,
            decision=ReviewDecision.APPROVE,
            reviewer_id="claude_bot",
            reason="AI generated approval",
            is_human=True,
            evidence_snapshot_text=ev_text,
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

    # Step 2: Approve with authentic matching official evidence text
    evidence_text = fresh_ledger.records[item_id].evidence_references[0]["text_excerpt"]
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
    ev_text = fresh_ledger.records[item_id].evidence_references[0]["text_excerpt"]

    # Cannot approve directly from UNREVIEWED without claiming first
    with pytest.raises(InvalidTransitionError):
        fresh_ledger.record_decision(
            item_id,
            decision=ReviewDecision.APPROVE,
            reviewer_id="attorney_kim",
            reason="Direct approval attempt",
            is_human=True,
            evidence_snapshot_text=ev_text,
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
    ev_text = fresh_ledger.records[item_id].evidence_references[0]["text_excerpt"]
    fresh_ledger.record_decision(
        item_id,
        decision=ReviewDecision.APPROVE,
        reviewer_id="attorney_lee",
        reason="현행 지침 일치 확인",
        is_human=True,
        evidence_snapshot_text=ev_text,
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
# 4. Review Integrity Validations: Evidence Snapshots & Required Grounds
# ---------------------------------------------------------------------------
def test_review_integrity_constraints(fresh_ledger):
    item_id = "ARTEMIS-004-DEV-005"

    # Empty reviewer id
    with pytest.raises(ReviewIntegrityError):
        fresh_ledger.claim_for_review(item_id, reviewer_id="", is_human=True)

    fresh_ledger.claim_for_review(item_id, reviewer_id="attorney_kim", is_human=True)
    ev_text = fresh_ledger.records[item_id].evidence_references[0]["text_excerpt"]

    # Reason too short (< 5 chars)
    with pytest.raises(ReviewIntegrityError):
        fresh_ledger.record_decision(
            item_id,
            decision=ReviewDecision.APPROVE,
            reviewer_id="attorney_kim",
            reason="ok",
            is_human=True,
            evidence_snapshot_text=ev_text,
        )


def test_missing_evidence_snapshot_strictly_rejected(fresh_ledger):
    item_id = "ARTEMIS-004-DEV-002"
    fresh_ledger.claim_for_review(item_id, reviewer_id="attorney_kim", is_human=True)

    # 1. Missing snapshot text (None)
    with pytest.raises(ReviewIntegrityError, match="Official evidence snapshot text is strictly required"):
        fresh_ledger.record_decision(
            item_id,
            decision=ReviewDecision.APPROVE,
            reviewer_id="attorney_kim",
            reason="Approval without evidence snapshot",
            is_human=True,
            evidence_snapshot_text=None,
        )

    # 2. Whitespace snapshot text
    with pytest.raises(ReviewIntegrityError, match="Official evidence snapshot text is strictly required"):
        fresh_ledger.record_decision(
            item_id,
            decision=ReviewDecision.APPROVE,
            reviewer_id="attorney_kim",
            reason="Approval with blank snapshot",
            is_human=True,
            evidence_snapshot_text="   \n\t  ",
        )


def test_mismatched_evidence_snapshot_rejected(fresh_ledger):
    item_id = "ARTEMIS-004-DEV-002"
    fresh_ledger.claim_for_review(item_id, reviewer_id="attorney_kim", is_human=True)

    # Completely unrelated snapshot text that does not match the item's official evidence
    fabricated_text = "임의로 날조된 근거 문장입니다. 이 텍스트는 공식 출처 어디에도 존재하지 않습니다."
    with pytest.raises(ReviewIntegrityError, match="Provided evidence snapshot text does not match"):
        fresh_ledger.record_decision(
            item_id,
            decision=ReviewDecision.APPROVE,
            reviewer_id="attorney_kim",
            reason="Approval with mismatched evidence text",
            is_human=True,
            evidence_snapshot_text=fabricated_text,
        )


# ---------------------------------------------------------------------------
# 5. Reviewer Identity Spoofing & Fail-Closed Gold Promotion
# ---------------------------------------------------------------------------
def test_spoofed_reviewer_identity_fails_closed(fresh_ledger):
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    candidates = json.loads(cand_path.read_text(encoding="utf-8"))["items"]
    item = candidates[0]
    cid = item["id"]

    # An automated caller provides a legitimate-sounding human name and is_human=True
    spoofed_name = "Hong Gil-dong (Certified Public Administrative Attorney)"
    fresh_ledger.claim_for_review(cid, reviewer_id=spoofed_name, is_human=True)
    ev_text = item["evidence"][0]["text"]
    fresh_ledger.record_decision(
        cid,
        decision=ReviewDecision.APPROVE,
        reviewer_id=spoofed_name,
        reason="공식 편람 대조 확인 완료 (사칭 시도)",
        is_human=True,
        evidence_snapshot_text=ev_text,
    )
    assert fresh_ledger.records[cid].review_status == ReviewStatus.VERIFIED_BY_HUMAN

    # Calling promote_to_gold without independent cryptographic attestation MUST fail-closed
    with pytest.raises(AuthoritativeGoldPromotionDisabledError, match="Authoritative promotion to official_gold is strictly disabled"):
        fresh_ledger.promote_to_gold(item)


def test_modified_evidence_after_review_detected_and_rejected(fresh_ledger):
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    candidates = json.loads(cand_path.read_text(encoding="utf-8"))["items"]
    item = copy.deepcopy(candidates[0])
    cid = item["id"]

    # Legitimate review recorded in ledger with original text hash
    ev_text = item["evidence"][0]["text"]
    fresh_ledger.claim_for_review(cid, reviewer_id="independent_attorney", is_human=True)
    fresh_ledger.record_decision(
        cid,
        decision=ReviewDecision.APPROVE,
        reviewer_id="independent_attorney",
        reason="원문 일치 확인",
        is_human=True,
        evidence_snapshot_text=ev_text,
    )

    # Attack Case A: Candidate item text is tampered with after review
    item_tampered = copy.deepcopy(item)
    item_tampered["evidence"][0]["text"] += "\n[위조된 법률 단서 규정 삽입]"

    with pytest.raises(ReviewIntegrityError, match="does not match evidence text hash"):
        fresh_ledger.validate_item_evidence_integrity(item_tampered)

    # Attack Case B: Attacker updates content_sha256 to hide text tampering,
    # but ledger evidence_snapshot_sha256 detects the modification
    new_hash = compute_evidence_snapshot_hash(item_tampered["evidence"][0]["text"])
    item_tampered["evidence"][0]["source"]["content_sha256"] = new_hash

    with pytest.raises(ReviewIntegrityError, match="Evidence integrity mismatch"):
        fresh_ledger.validate_item_evidence_integrity(item_tampered)

    with pytest.raises(ReviewIntegrityError, match="Evidence integrity mismatch"):
        fresh_ledger.promote_to_gold(item_tampered)


def test_mismatched_source_content_hash_rejected(fresh_ledger):
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    candidates = json.loads(cand_path.read_text(encoding="utf-8"))["items"]
    item = copy.deepcopy(candidates[0])
    cid = item["id"]

    ev_text = item["evidence"][0]["text"]
    fresh_ledger.claim_for_review(cid, reviewer_id="independent_attorney", is_human=True)
    fresh_ledger.record_decision(
        cid,
        decision=ReviewDecision.APPROVE,
        reviewer_id="independent_attorney",
        reason="원문 일치 확인",
        is_human=True,
        evidence_snapshot_text=ev_text,
    )

    # Modify content_sha256 in source metadata to contradict actual text
    item["evidence"][0]["source"]["content_sha256"] = "0" * 64

    with pytest.raises(ReviewIntegrityError, match="Source content_sha256 .* does not match evidence text hash"):
        fresh_ledger.validate_item_evidence_integrity(item)


def test_missing_official_evidence_rejected(fresh_ledger):
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    candidates = json.loads(cand_path.read_text(encoding="utf-8"))["items"]
    item = copy.deepcopy(candidates[0])
    cid = item["id"]

    ev_text = item["evidence"][0]["text"]
    fresh_ledger.claim_for_review(cid, reviewer_id="independent_attorney", is_human=True)
    fresh_ledger.record_decision(
        cid,
        decision=ReviewDecision.APPROVE,
        reviewer_id="independent_attorney",
        reason="원문 일치 확인",
        is_human=True,
        evidence_snapshot_text=ev_text,
    )

    # Empty evidence list
    empty_item = copy.deepcopy(item)
    empty_item["evidence"] = []
    with pytest.raises(ReviewIntegrityError, match="official evidence list is missing or empty"):
        fresh_ledger.validate_item_evidence_integrity(empty_item)

    # Non-official provenance
    non_official = copy.deepcopy(item)
    non_official["evidence"][0]["source"]["provenance"] = "community"
    with pytest.raises(ReviewIntegrityError, match="is not official"):
        fresh_ledger.validate_item_evidence_integrity(non_official)


def test_authoritative_gold_promotion_gating_and_test_simulation(fresh_ledger):
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    candidates = json.loads(cand_path.read_text(encoding="utf-8"))["items"]
    item = copy.deepcopy(candidates[0])
    cid = item["id"]

    # 1. Unreviewed item CANNOT be promoted
    with pytest.raises(ReviewIntegrityError, match="must be 'verified_by_human'"):
        fresh_ledger.promote_to_gold(item)

    # 2. Local review record created
    ev_text = item["evidence"][0]["text"]
    fresh_ledger.claim_for_review(cid, reviewer_id="independent_attorney", is_human=True)
    fresh_ledger.record_decision(
        cid,
        decision=ReviewDecision.APPROVE,
        reviewer_id="independent_attorney",
        reason="법령 조문 및 지침 대조 전수 확인 완료",
        is_human=True,
        evidence_snapshot_text=ev_text,
    )

    # 3. Without external attestation, promotion fails closed
    with pytest.raises(AuthoritativeGoldPromotionDisabledError):
        fresh_ledger.promote_to_gold(item)

    # 4. With external attestation, but in production prototype without connected PKI service
    ev_hash = compute_evidence_snapshot_hash(ev_text)
    test_attestation = {
        "signer_identity": "independent_attorney",
        "attestation_token": "attest_pki_signature_mock_token_20261029",
        "signature_sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "signed_at": "2026-10-29T16:00:00Z",
        "evidence_snapshot_sha256": ev_hash,
    }

    with pytest.raises(AuthoritativeGoldPromotionDisabledError, match="External cryptographic PKI authority verification service is not connected"):
        fresh_ledger.promote_to_gold(item, external_attestation=test_attestation)

    # 5. There is no caller-controlled test override: no code path can
    # turn an unauthenticated local approval into an official gold item.
    assert item["metadata"]["candidate_status"] != "official_gold"
    assert item["evidence"][0]["source"]["approval_state"] == "under_review"


def test_external_attestation_mismatch_rejected(fresh_ledger):
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    candidates = json.loads(cand_path.read_text(encoding="utf-8"))["items"]
    item = copy.deepcopy(candidates[0])
    cid = item["id"]

    ev_text = item["evidence"][0]["text"]
    fresh_ledger.claim_for_review(cid, reviewer_id="attorney_lee", is_human=True)
    fresh_ledger.record_decision(
        cid,
        decision=ReviewDecision.APPROVE,
        reviewer_id="attorney_lee",
        reason="원문 일치 확인",
        is_human=True,
        evidence_snapshot_text=ev_text,
    )

    ev_hash = compute_evidence_snapshot_hash(ev_text)

    # Mismatched signer identity
    mismatched_signer = {
        "signer_identity": "attorney_different_person",
        "attestation_token": "token123",
        "signature_sha256": "sig123",
        "signed_at": "2026-10-29T16:00:00Z",
        "evidence_snapshot_sha256": ev_hash,
    }
    with pytest.raises(ReviewIntegrityError, match="does not match ledger reviewer"):
        fresh_ledger.promote_to_gold(item, external_attestation=mismatched_signer)

    # AI identifier in attestation signer
    ai_signer = {
        "signer_identity": "gemini_agent",
        "attestation_token": "token123",
        "signature_sha256": "sig123",
        "signed_at": "2026-10-29T16:00:00Z",
        "evidence_snapshot_sha256": ev_hash,
    }
    with pytest.raises(AIApprovalForbiddenError):
        fresh_ledger.promote_to_gold(item, external_attestation=ai_signer)

    # Mismatched evidence snapshot hash
    mismatched_hash = {
        "signer_identity": "attorney_lee",
        "attestation_token": "token123",
        "signature_sha256": "sig123",
        "signed_at": "2026-10-29T16:00:00Z",
        "evidence_snapshot_sha256": "0" * 64,
    }
    with pytest.raises(ReviewIntegrityError, match="does not match ledger snapshot"):
        fresh_ledger.promote_to_gold(item, external_attestation=mismatched_hash)


# ---------------------------------------------------------------------------
# 6. Repository State Verification: All 60 Items Unverified
# ---------------------------------------------------------------------------
def test_all_60_candidate_items_remain_unverified_in_repo():
    ledger_path = BOOTSTRAP_DIR / "reviews" / "legal_review_ledger.json"
    data = json.loads(ledger_path.read_text(encoding="utf-8"))

    assert data["total_items"] == 60
    assert data["status_counts"]["unreviewed"] == 60
    assert data["status_counts"]["verified_by_human"] == 0

    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    candidates = json.loads(cand_path.read_text(encoding="utf-8"))["items"]
    assert len(candidates) == 60

    # Every item must have needs_human_review = True and candidate_status != official_gold
    for item in candidates:
        meta = item.get("metadata", {})
        assert meta.get("needs_human_review") is True
        assert meta.get("candidate_status") != "official_gold"


# ---------------------------------------------------------------------------
# 7. Persistence and Markdown Audit Reporting
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


def test_no_callable_gold_promotion_test_bypass(fresh_ledger):
    """External callers cannot enable test-only gold promotion using a flag."""
    import inspect
    signature = inspect.signature(fresh_ledger.promote_to_gold)
    assert "_allow_test_promotion" not in signature.parameters
    assert "test_mode" not in signature.parameters
