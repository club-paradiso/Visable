"""Unit tests for Artemis Review Workbench (Mission 004-D).

Verifies:
1. Workbench browsing and filtering (Group A: 16 items, Group B: 44 items, total: 60).
2. Side-by-side detail retrieval (Question, Proposed Answer, Evidence References, History).
3. Draft annotations and non-authoritative review recording.
4. Audit trail preservation (no silent overwrites).
5. Review package export and import workflows with schema verification.
6. Fail-closed governance (official gold promotion strictly disabled).
7. Security regression: Stored XSS defense, URL scheme restriction.
8. Security regression: Rejection of forged approval / gold import claims.
9. Security regression: Prevention of arbitrary-path HTTP imports and directory traversal.
10. Security regression: Write token CSRF defense, loopback/origin enforcement, and body size limits.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from artemis_bootstrap.review_workbench import (
    MAX_PAYLOAD_SIZE,
    WORKBENCH_WRITE_TOKEN,
    ReviewWorkbench,
    ReviewerDraftNote,
    WorkbenchHTTPHandler,
    escape_html,
    sanitize_url,
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

    # Verify transition was preserved in fresh workbench with import provenance
    imported_detail = fresh_wb.get_item_detail(item_id)
    assert len(imported_detail["transition_history"]) >= 2
    # 1st entry: the imported transition with [IMPORTED] prefix and is_human=False
    t0 = imported_detail["transition_history"][0]
    assert "[IMPORTED] security_officer_lee" in t0["actor_id"]
    assert t0["is_human"] is False
    # 2nd entry: the server-derived import audit entry
    t1 = imported_detail["transition_history"][1]
    assert t1["actor_id"] == "workbench_import_system"
    assert t1["is_human"] is False


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


# ---------------------------------------------------------------------------
# Security Regression Tests
# ---------------------------------------------------------------------------

def test_xss_sanitization_and_escaping(workbench):
    """Verifies that malicious HTML/JS payloads are sanitized and escaped in detail rendering."""
    xss_payload = "<script>alert('XSS')</script><img src=x onerror=alert(1)>"
    escaped = escape_html(xss_payload)

    assert "<script>" not in escaped
    assert "</script>" not in escaped
    assert "&lt;script&gt;" in escaped
    assert "&lt;img src=x onerror=alert(1)&gt;" in escaped

    # URL sanitization blocks javascript:, data:, vbscript:
    assert sanitize_url("javascript:alert(1)") == "#"
    assert sanitize_url("JAVASCRIPT:void(0)") == "#"
    assert sanitize_url("data:text/html,<script>alert(1)</script>") == "#"
    assert sanitize_url("vbscript:msgbox") == "#"
    assert sanitize_url("") == "#"

    # Legitimate HTTP/HTTPS URLs are allowed
    assert sanitize_url("https://www.law.go.kr/DRF/lawService.do") == "https://www.law.go.kr/DRF/lawService.do"
    assert sanitize_url("http://127.0.0.1:8420") == "http://127.0.0.1:8420"

    # Stored XSS roundtrip verification
    item_id = "ARTEMIS-004-DEV-013"
    updated = workbench.record_draft_annotation(
        item_id=item_id,
        author='reviewer"<script>alert(1)</script>',
        notes='<img src=x onerror=alert("hacked")>',
        statutory_conflicts='conflict<b onmouseover=alert(1)>bold</b>',
        action_type="draft_note",
    )
    detail = workbench.get_item_detail(item_id)
    t = detail["transition_history"][-1]

    # Verify that escaping escapes all fields properly
    assert "&lt;script&gt;" in escape_html(t["actor_id"])
    assert "&lt;img" in escape_html(t["reason"])
    assert "&lt;b onmouseover" in escape_html(t["notes"])
    assert "<script>" not in escape_html(t["actor_id"])
    assert "<img" not in escape_html(t["reason"])


def test_forged_history_import_rejected(workbench):
    """Verifies that external packages asserting official_gold or approved status are rejected."""
    item_id = "ARTEMIS-004-DEV-013"

    # Forged package attempting to claim official_gold
    forged_package = {
        "package_version": "artemis-workbench-export/1.0",
        "items": [
            {
                "item_id": item_id,
                "review_status": "official_gold",  # Prohibited!
                "transition_history": [
                    {
                        "timestamp": "2026-10-29T00:00:00Z",
                        "from_status": "unreviewed",
                        "to_status": "official_gold",
                        "actor_id": "forged_judge",
                        "is_human": True,
                    }
                ],
            }
        ],
    }

    with pytest.raises(ReviewIntegrityError, match="Prohibited approval/gold status"):
        workbench.import_review_package_data(forged_package)

    # Forged package attempting approved transition
    forged_transition = {
        "package_version": "artemis-workbench-export/1.0",
        "items": [
            {
                "item_id": item_id,
                "review_status": "in_review",
                "transition_history": [
                    {
                        "timestamp": "2026-10-29T00:00:00Z",
                        "from_status": "in_review",
                        "to_status": "approved",  # Prohibited!
                        "actor_id": "forged_judge",
                        "is_human": True,
                    }
                ],
            }
        ],
    }

    with pytest.raises(ReviewIntegrityError, match="Prohibited status transition"):
        workbench.import_review_package_data(forged_transition)


def test_imported_history_cannot_claim_is_human(workbench):
    """Verifies that imported draft transitions never retain is_human=True."""
    item_id = "ARTEMIS-004-DEV-014"
    package = {
        "package_version": "artemis-workbench-export/1.0",
        "items": [
            {
                "item_id": item_id,
                "review_status": "in_review",
                "transition_history": [
                    {
                        "timestamp": "2026-10-29T01:00:00Z",
                        "from_status": "unreviewed",
                        "to_status": "in_review",
                        "actor_id": "external_reviewer_99",
                        "is_human": True,  # Attempting to assert is_human
                        "reason": "검토 진행 중",
                    }
                ],
            }
        ],
    }

    res = workbench.import_review_package_data(package)
    assert res["status"] == "success"

    detail = workbench.get_item_detail(item_id)
    imported_t = detail["transition_history"][0]
    assert imported_t["is_human"] is False  # Must be enforced False
    assert "[IMPORTED] external_reviewer_99" in imported_t["actor_id"]


def test_http_write_protection_and_token(workbench):
    """Tests Workbench HTTP request security: tokens, origin, and payload size."""
    handler = WorkbenchHTTPHandler
    handler.workbench = workbench

    # Helper mock to invoke handler logic
    class MockRequest:
        def __init__(self, method: str, path: str, headers: dict, body: bytes = b""):
            self.method = method
            self.path = path
            self.headers = headers
            self.rfile = io.BytesIO(body)
            self.wfile = io.BytesIO()
            self.status_code = None
            self.response_headers = {}

    def run_handler_post(path: str, headers: dict, body: bytes):
        req = MockRequest("POST", path, headers, body)
        h = handler.__new__(handler)
        h.rfile = req.rfile
        h.wfile = req.wfile
        h.headers = req.headers
        h.path = path
        h.send_response = lambda code: setattr(req, "status_code", code)
        h.send_header = lambda k, v: req.response_headers.setdefault(k, v)
        h.end_headers = lambda: None
        h.do_POST()
        return req

    # 1. POST without X-Workbench-Token -> 403 Forbidden
    req1 = run_handler_post(
        "/api/item/ARTEMIS-004-DEV-013/draft",
        {"Host": "127.0.0.1:8420", "Content-Length": "10"},
        b'{"notes":"x"}',
    )
    assert req1.status_code == 403
    assert b"invalid or missing X-Workbench-Token" in req1.wfile.getvalue()

    # 2. Untrusted Origin header -> 403 Forbidden
    req2 = run_handler_post(
        "/api/item/ARTEMIS-004-DEV-013/draft",
        {
            "Host": "127.0.0.1:8420",
            "Origin": "http://malicious-site.com",
            "X-Workbench-Token": WORKBENCH_WRITE_TOKEN,
            "Content-Length": "10",
        },
        b'{"notes":"x"}',
    )
    assert req2.status_code == 403
    assert b"untrusted Origin header" in req2.wfile.getvalue()

    # 3. Non-loopback Host header -> 403 Forbidden
    req3 = run_handler_post(
        "/api/item/ARTEMIS-004-DEV-013/draft",
        {
            "Host": "malicious-site.com",
            "X-Workbench-Token": WORKBENCH_WRITE_TOKEN,
            "Content-Length": "10",
        },
        b'{"notes":"x"}',
    )
    assert req3.status_code == 403

    # 4. Oversized payload (> 128KB) -> 413 Payload Too Large
    req4 = run_handler_post(
        "/api/item/ARTEMIS-004-DEV-013/draft",
        {
            "Host": "127.0.0.1:8420",
            "X-Workbench-Token": WORKBENCH_WRITE_TOKEN,
            "Content-Length": str(MAX_PAYLOAD_SIZE + 100),
        },
        b"x" * 10,
    )
    assert req4.status_code == 413
    assert b"Payload Too Large" in req4.wfile.getvalue()

    # 5. Path traversal attempt in HTTP import -> 400 Bad Request
    req5 = run_handler_post(
        "/api/import",
        {
            "Host": "127.0.0.1:8420",
            "X-Workbench-Token": WORKBENCH_WRITE_TOKEN,
            "Content-Length": "35",
        },
        b'{"filename":"../../etc/passwd"}',
    )
    assert req5.status_code == 400
    assert b"Path traversal prohibited" in req5.wfile.getvalue()

    # 6. Valid POST with token -> 200 OK
    valid_body = json.dumps({"author": "auditor_sec", "notes": "보안 테스트 완료"}).encode("utf-8")
    req6 = run_handler_post(
        "/api/item/ARTEMIS-004-DEV-013/draft",
        {
            "Host": "127.0.0.1:8420",
            "X-Workbench-Token": WORKBENCH_WRITE_TOKEN,
            "Content-Length": str(len(valid_body)),
        },
        valid_body,
    )
    assert req6.status_code == 200
    assert b"auditor_sec" in req6.wfile.getvalue()
    # Confirm Access-Control-Allow-Origin is NOT set
    assert "Access-Control-Allow-Origin" not in req6.response_headers
