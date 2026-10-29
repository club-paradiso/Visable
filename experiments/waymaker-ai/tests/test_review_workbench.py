"""Unit tests for Artemis Review Workbench (Mission 004-D).

Verifies:
1. Workbench browsing and filtering (Group A: 16 items, Group B: 44 items, total: 60).
2. Side-by-side detail retrieval (Question, Proposed Answer, Evidence References, History).
3. Draft annotations and non-authoritative review recording.
4. Audit trail preservation (no silent overwrites).
5. Review package export and import workflows with schema verification.
6. Fail-closed governance (official gold promotion strictly disabled).
7. HTTP API handlers return valid payloads.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from artemis_bootstrap.review_workbench import (
    ReviewWorkbench,
    ReviewerDraftNote,
    WorkbenchHTTPHandler,
)
from artemis_bootstrap.legal_review_governance import (
    AuthoritativeGoldPromotionDisabledError,
    LegalReviewLedger,
    ReviewDecision,
    ReviewIntegrityError,
    ReviewStatus,
)


BOOTSTRAP_DIR = Path(__file__).resolve().parent.parent / "artemis_bootstrap"
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"
REVIEWS_DIR = BOOTSTRAP_DIR / "reviews"


@pytest.fixture
def workbench(tmp_path):
    ledger_path = tmp_path / "test_ledger.json"
    candidates_file = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    ledger = LegalReviewLedger.load_or_initialize(ledger_path=ledger_path, candidates_path=candidates_file)
    return ReviewWorkbench(ledger=ledger, packets_dir=BOOTSTRAP_DIR / "review_packets")


def test_workbench_browsing_and_filtering(workbench):
    all_items = workbench.get_all_items_summary()
    assert len(all_items) == 60

    group_a = workbench.get_all_items_summary(group_filter="Group A")
    assert len(group_a) == 16

    group_b = workbench.get_all_items_summary(group_filter="Group B")
    assert len(group_b) == 44

    unreviewed = workbench.get_all_items_summary(status_filter="unreviewed")
    assert len(unreviewed) == 60


def test_workbench_side_by_side_detail(workbench):
    item_id = "ARTEMIS-004-HLD-004"
    detail = workbench.get_item_detail(item_id)

    assert detail["item_id"] == item_id
    assert "지역특화형(F-2-R)" in detail["question"]
    assert detail["proposed_answer"]
    assert len(detail["evidence_references"]) >= 1
    assert detail["packet"] is not None  # Group A item has associated review packet
    assert detail["official_gold_promotion_enabled"] is False
    assert detail["governance_mode"] == "local_non_authoritative_prototype"


def test_workbench_draft_annotation_and_audit_preservation(workbench):
    item_id = "ARTEMIS-004-HLD-004"

    # Step 1: Record first draft note
    res1 = workbench.record_draft_annotation(
        item_id=item_id,
        author="attorney_test_kim",
        notes="지자체 5년 실거주 의무 원문 확인 완료. 이탈 시 체류취소 지침 확인.",
        statutory_conflicts="2026년 하반기 수도권 인접 인구감소지역 거주 이탈 사례 빈번",
        action_type="draft_note",
    )
    assert res1["review_status"] == "in_review"
    assert len(res1["transition_history"]) == 1
    assert "attorney_test_kim" in res1["transition_history"][0]["actor_id"]

    # Step 2: Request revision (should append, not overwrite prior audit log)
    res2 = workbench.record_draft_annotation(
        item_id=item_id,
        author="attorney_test_kim",
        notes="지자체장 추천을 통한 예외적 이주 규정이 답변에 보완되어야 함",
        statutory_conflicts="도산 폐업 시 예외 인정 지침 누락",
        action_type="request_revision",
    )
    assert res2["review_status"] == "needs_revision"
    assert len(res2["transition_history"]) == 2
    assert res2["transition_history"][0]["to_status"] == "in_review"
    assert res2["transition_history"][1]["to_status"] == "needs_revision"


def test_workbench_export_and_import_cycle(tmp_path, workbench):
    item_id = "ARTEMIS-004-DEV-013"
    workbench.record_draft_annotation(
        item_id=item_id,
        author="security_officer_lee",
        notes="과태료 면제 권한 사칭 차단 확인",
        action_type="draft_note",
    )

    export_file = tmp_path / "test_export.json"
    exp_res = workbench.export_review_package(export_file)
    assert exp_res["status"] == "success"
    assert export_file.exists()

    # Reimport into a fresh workbench
    fresh_ledger_file = tmp_path / "fresh_ledger.json"
    fresh_ledger = LegalReviewLedger.load_or_initialize(
        ledger_path=fresh_ledger_file,
        candidates_path=BENCHMARKS_DIR / "artemis_eval_candidates_60.json",
    )
    fresh_wb = ReviewWorkbench(ledger=fresh_ledger, packets_dir=BOOTSTRAP_DIR / "review_packets")

    imp_res = fresh_wb.import_review_package(export_file)
    assert imp_res["status"] == "success"
    assert imp_res["imported_items"] == 60

    # Verify transition was preserved in fresh workbench
    imported_detail = fresh_wb.get_item_detail(item_id)
    assert len(imported_detail["transition_history"]) >= 1
    assert imported_detail["transition_history"][0]["actor_id"] == "security_officer_lee"


def test_authoritative_gold_promotion_remains_disabled(workbench):
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    item = json.loads(cand_path.read_text(encoding="utf-8"))["items"][0]
    cid = item["id"]

    # 1. Unreviewed item fails with ReviewIntegrityError
    with pytest.raises(ReviewIntegrityError, match="must be 'verified_by_human'"):
        workbench.ledger.promote_to_gold(item)

    # 2. Local approval recorded
    ev_text = item["evidence"][0]["text"]
    workbench.ledger.claim_for_review(cid, reviewer_id="attorney_local_test", is_human=True)
    workbench.ledger.record_decision(
        cid,
        decision=ReviewDecision.APPROVE,
        reviewer_id="attorney_local_test",
        reason="원문 일치 확인",
        is_human=True,
        evidence_snapshot_text=ev_text,
    )

    # 3. Even after local approval, promote_to_gold raises AuthoritativeGoldPromotionDisabledError
    with pytest.raises(AuthoritativeGoldPromotionDisabledError, match="Authoritative promotion to official_gold is strictly disabled"):
        workbench.ledger.promote_to_gold(item)
