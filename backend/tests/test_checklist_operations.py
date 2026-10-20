import json
import os
import sys
import unittest

os.environ.setdefault("WAYMAKER_KNOWLEDGE_DB", ":memory:")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.knowledge.api import build_knowledge_router
from services.knowledge.checklist_models import (
    ChecklistReviewState,
    DraftActionIn,
    DraftCreateIn,
    OfficeOverrideIn,
    OperatorRole,
    ReleaseRequestIn,
    can_edit,
    can_publish,
    can_review,
)
from services.knowledge.checklist_repository import (
    act_on_draft,
    bootstrap_checklist_items,
    compute_draft_diff,
    create_or_update_draft,
    execute_publish_release,
    get_dashboard_metrics,
    get_operator_role,
    get_scenario_detail,
    list_offices_status,
    list_scenarios,
    run_prepublish_validation,
    save_office_override,
)
from services.knowledge.models import KnowledgeError
from services.knowledge.runtime import KnowledgePlatform
from services.knowledge.store import KnowledgeStore


class TestChecklistOperations(unittest.TestCase):
    def setUp(self):
        os.environ["WAYMAKER_OPERATOR_TOKENS"] = (
            "admin:test_publisher_token_12345678,"
            "reviewer_lead:test_reviewer_token_12345678,"
            "editor_staff:test_editor_token_12345678,"
            "auditor:test_viewer_token_12345678"
        )
        self.store = KnowledgeStore(":memory:")
        bootstrap_checklist_items(self.store)

        self.platform = KnowledgePlatform(self.store)
        self.app = FastAPI()
        self.app.include_router(build_knowledge_router(lambda: self.platform))
        self.client = TestClient(self.app)

        self.headers_viewer = {"Authorization": "Bearer test_viewer_token_12345678"}
        self.headers_editor = {"Authorization": "Bearer test_editor_token_12345678"}
        self.headers_reviewer = {"Authorization": "Bearer test_reviewer_token_12345678"}
        self.headers_publisher = {"Authorization": "Bearer test_publisher_token_12345678"}

    def test_bootstrap_preserves_647_items(self):
        """Verifies that the bootstrap seeds exactly 647 items without data loss."""
        metrics = get_dashboard_metrics(self.store)
        self.assertEqual(metrics.total_scenarios, 647)
        self.assertEqual(metrics.extension_count, 224)
        self.assertEqual(metrics.change_count, 251)
        self.assertEqual(metrics.registration_count, 172)

    def test_role_resolution(self):
        """Verifies that operator roles are correctly mapped from operator_roles table."""
        self.assertEqual(get_operator_role(self.store, "admin"), OperatorRole.PUBLISHER)
        self.assertEqual(get_operator_role(self.store, "reviewer_lead"), OperatorRole.REVIEWER)
        self.assertEqual(get_operator_role(self.store, "editor_staff"), OperatorRole.EDITOR)
        self.assertEqual(get_operator_role(self.store, "auditor"), OperatorRole.VIEWER)

    def test_rbac_write_restrictions(self):
        """Verifies that viewers cannot create drafts, and editors cannot approve."""
        first_item = list_scenarios(self.store, limit=1)[0][0]

        draft_body = {
            "item_id": first_item.id,
            "required_text": "임의 수정 서류",
            "editor_note": "뷰어 수정 시도",
            "evidence_url": "https://www.hikorea.go.kr/test.pdf",
        }
        # Viewer attempting to create draft -> 403
        r_viewer = self.client.post("/api/knowledge/studio/checklists/drafts", json=draft_body, headers=self.headers_viewer)
        self.assertEqual(r_viewer.status_code, 403)

        # Editor can create draft -> 200
        r_editor = self.client.post("/api/knowledge/studio/checklists/drafts", json=draft_body, headers=self.headers_editor)
        self.assertEqual(r_editor.status_code, 200)
        draft_id = r_editor.json()["draft_id"]

        # Editor attempting to approve -> 403
        r_approve_editor = self.client.post(
            f"/api/knowledge/studio/checklists/drafts/{draft_id}/action",
            json={"action": "approve", "comment": "승인 시도"},
            headers=self.headers_editor,
        )
        self.assertEqual(r_approve_editor.status_code, 403)

    def test_evidence_gate_blocks_unsubstantiated_approval(self):
        """Evidence gate must block approval if evidence_url is missing or invalid."""
        first_item = list_scenarios(self.store, limit=1)[0][0]

        # Create draft without evidence
        draft_in = DraftCreateIn(
            item_id=first_item.id,
            required_text="출처 미확인 서류",
            editor_note="근거 없는 수정안",
            evidence_url="",
        )
        draft_res = create_or_update_draft(self.store, draft_in, actor="editor_staff", actor_role=OperatorRole.EDITOR)
        draft_id = draft_res["draft_id"]

        # Submit draft
        act_on_draft(self.store, draft_id, DraftActionIn(action="submit"), actor="editor_staff", actor_role=OperatorRole.EDITOR)

        # Reviewer attempts to approve without evidence -> must raise KnowledgeError
        with self.assertRaises(KnowledgeError) as ctx:
            act_on_draft(self.store, draft_id, DraftActionIn(action="approve"), actor="reviewer_lead", actor_role=OperatorRole.REVIEWER)
        self.assertIn("Evidence Gate Failed", str(ctx.exception))

    def test_pilot_vertical_slice_d2_e7_f4_workflow(self):
        """Tests complete vertical slice for D-2, E-7-1, and F-4 from draft to approval."""
        targets = [
            ("D-2", "extension"),
            ("E-7-1", "change"),
            ("F-4", "registration"),
        ]

        for code, proc in targets:
            items, total = list_scenarios(self.store, status_code=code, procedure=proc, limit=5)
            self.assertGreater(total, 0, f"Must find scenarios for {code} {proc}")
            target_item = items[0]

            # 1. Editor creates draft
            draft_in = DraftCreateIn(
                item_id=target_item.id,
                required_text=f"{target_item.required_text} (2026.10 지침 보완)",
                conditional_text=target_item.conditional_text,
                application_text=target_item.application_text,
                note_text=target_item.note_text,
                editor_note=f"{code} {proc} 공식 지침 대조 확인 완료",
                evidence_url=f"https://www.hikorea.go.kr/notice/{code}.pdf",
                evidence_title=f"2026.10 {code} 공식 매뉴얼",
                evidence_issuer="법무부 출입국·외국인정책본부",
            )
            d_res = create_or_update_draft(self.store, draft_in, actor="editor_staff", actor_role=OperatorRole.EDITOR)
            draft_id = d_res["draft_id"]

            # 2. Editor submits draft
            s_res = act_on_draft(self.store, draft_id, DraftActionIn(action="submit"), actor="editor_staff", actor_role=OperatorRole.EDITOR)
            self.assertEqual(s_res["lifecycle_state"], "SUBMITTED")

            # 3. Diff calculation
            diff = compute_draft_diff(self.store, draft_id)
            self.assertEqual(diff.draft_id, draft_id)
            self.assertTrue(any(f.changed for f in diff.fields if f.field_name == "required_text"))

            # 4. Reviewer approves
            a_res = act_on_draft(
                self.store,
                draft_id,
                DraftActionIn(action="approve", comment="공식 공고 대조 검증 완료"),
                actor="reviewer_lead",
                actor_role=OperatorRole.REVIEWER,
            )
            self.assertEqual(a_res["lifecycle_state"], "APPROVED")

        # 5. Prepublish validation passes
        val_report = run_prepublish_validation(self.store)
        self.assertTrue(val_report.valid)
        self.assertEqual(val_report.approved_drafts_count, 3)

    def test_jeju_office_override_workflow(self):
        """Verifies Jeju immigration office override management and HTTPS validation."""
        jeju_item = list_scenarios(self.store, procedure="extension", status_code="D-2", limit=1)[0][0]

        ov_in = OfficeOverrideIn(
            office_id="jeju",
            item_id=jeju_item.id,
            procedure="extension",
            status_code=jeju_item.status_code,
            diff_type="additional_required",
            override_text="제주출입국 특별 관리 지침: 현장 출석 확인서 추가",
            evidence_url="https://www.hikorea.go.kr/notice/jeju_d2_2026.pdf",
            evidence_title="제주출입국·외국인청 2026년도 유학생 관리 공지",
            evidence_issuer="제주출입국·외국인청",
            confirmed_date="2026-10-19",
        )
        res = save_office_override(self.store, ov_in, actor="editor_staff", actor_role=OperatorRole.EDITOR)
        self.assertEqual(res["status"], "saved")

        offices_data = list_offices_status(self.store)
        jeju_entry = next((o for o in offices_data["offices"] if o["id"] == "jeju"), None)
        self.assertIsNotNone(jeju_entry)
        self.assertGreater(jeju_entry["total_overrides"], 0)

    def test_release_endpoint_contract_and_p0_fix(self):
        """Validates that execute_publish_release via HTTP endpoint handles ReleaseRequestIn without TypeError."""
        payload = {
            "release_tag": "rel-20261020-01",
            "release_note": "VISABLE R3.1 safe release verification",
            "target_procedure": "all",
        }
        # Non-publisher gets 403
        r_ed = self.client.post("/api/knowledge/studio/checklists/publish/release", json=payload, headers=self.headers_editor)
        self.assertEqual(r_ed.status_code, 403)

        # Publisher succeeds
        r_pub = self.client.post("/api/knowledge/studio/checklists/publish/release", json=payload, headers=self.headers_publisher)
        self.assertEqual(r_pub.status_code, 200, f"Failed: {r_pub.text}")
        res_data = r_pub.json()
        self.assertEqual(res_data["release_tag"], "rel-20261020-01")
        self.assertEqual(res_data["status"], "PUBLISHED")
        self.assertEqual(res_data["total_scenario_count"], 647)

        # Duplicate release tag is rejected with 409
        r_dup = self.client.post("/api/knowledge/studio/checklists/publish/release", json=payload, headers=self.headers_publisher)
        self.assertEqual(r_dup.status_code, 409)

    def test_prepublish_validation_report_fields(self):
        """Verifies report structure including passed, procedure_counts, durable_storage, and dataset_checksum."""
        r = self.client.post("/api/knowledge/studio/checklists/publish/validate", headers=self.headers_viewer)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["passed"])
        self.assertTrue(data["valid"])
        self.assertEqual(data["total_items"], 647)
        self.assertEqual(data["total_scenarios"], 647)
        self.assertIn("procedure_counts", data)
        self.assertEqual(data["procedure_counts"]["extension"], 224)
        self.assertEqual(data["procedure_counts"]["change"], 251)
        self.assertEqual(data["procedure_counts"]["registration"], 172)
        self.assertIn("dataset_checksum", data)
        self.assertEqual(len(data["dataset_checksum"]), 64)
        self.assertFalse(data["durable_storage"])

    def test_canonical_ids_strict_preservation(self):
        """Ensures that all 647 records follow canonical e-XXXX, c-XXXX, r-XXXX patterns."""
        report = run_prepublish_validation(self.store)
        self.assertTrue(report.valid)
        patterns_check = next((c for c in report.checks if c.get("name") == "id_format_integrity"), None)
        self.assertIsNotNone(patterns_check)
        self.assertEqual(patterns_check.get("status"), "PASS")

    def test_self_approval_prevention_and_emergency_override(self):
        """Four-eyes principle: authors cannot approve their own drafts unless explicit emergency override is passed."""
        item = list_scenarios(self.store, limit=1)[0][0]
        d_in = DraftCreateIn(
            item_id=item.id,
            required_text="제3자 승인 필요 서류",
            editor_note="자가 승인 방지 테스트",
            evidence_url="https://www.hikorea.go.kr/test-self.pdf",
            evidence_title="자가승인방지 고시",
            evidence_issuer="법무부",
        )
        draft_res = create_or_update_draft(self.store, d_in, actor="reviewer_lead", actor_role=OperatorRole.REVIEWER)
        draft_id = draft_res["draft_id"]
        act_on_draft(self.store, draft_id, DraftActionIn(action="submit"), actor="reviewer_lead", actor_role=OperatorRole.REVIEWER)

        # Attempting self-approval without override -> raises KnowledgeError
        with self.assertRaises(KnowledgeError) as ctx:
            act_on_draft(self.store, draft_id, DraftActionIn(action="approve"), actor="reviewer_lead", actor_role=OperatorRole.REVIEWER)
        self.assertIn("Self-approval forbidden", str(ctx.exception))

        # Attempting self-approval WITH override -> succeeds
        res = act_on_draft(
            self.store,
            draft_id,
            DraftActionIn(action="approve", comment="긴급 예외 승인", allow_self_approval=True),
            actor="reviewer_lead",
            actor_role=OperatorRole.REVIEWER,
        )
        self.assertEqual(res["lifecycle_state"], "APPROVED")

    def test_least_privilege_viewer_default(self):
        """Unknown operator tokens fallback to VIEWER role."""
        role = get_operator_role(self.store, "unknown_user_123")
        self.assertEqual(role, OperatorRole.VIEWER)

    def test_rollback_execution_and_snapshot_restore(self):
        """Verifies that publishing a release takes a snapshot and rollback restores the exact baseline state."""
        item = list_scenarios(self.store, procedure="extension", limit=1)[0][0]
        original_text = item.required_text

        # Create draft and approve
        d_in = DraftCreateIn(
            item_id=item.id,
            required_text=original_text + " [ROLLBACK_TEST_MARKER]",
            editor_note="롤백 복원 테스트용 수정",
            evidence_url="https://www.hikorea.go.kr/rollback-test.pdf",
            evidence_title="롤백 테스트 공문",
            evidence_issuer="법무부",
        )
        d_res = create_or_update_draft(self.store, d_in, actor="editor_staff", actor_role=OperatorRole.EDITOR)
        act_on_draft(self.store, d_res["draft_id"], DraftActionIn(action="submit"), actor="editor_staff", actor_role=OperatorRole.EDITOR)
        act_on_draft(self.store, d_res["draft_id"], DraftActionIn(action="approve"), actor="reviewer_lead", actor_role=OperatorRole.REVIEWER)

        # Publish release
        rel_req = {
            "release_tag": "rel-rollback-test-01",
            "release_note": "Before rollback",
            "target_procedure": "all",
        }
        r_pub = self.client.post("/api/knowledge/studio/checklists/publish/release", json=rel_req, headers=self.headers_publisher)
        self.assertEqual(r_pub.status_code, 200)
        rel_id = r_pub.json()["release_id"]

        # Verify item was updated in store
        detail = get_scenario_detail(self.store, item.id)
        self.assertIn("[ROLLBACK_TEST_MARKER]", detail["item"]["required_text"])

        # Rollback release
        rb_payload = {"reason": "테스트 롤백: 이전 스냅샷으로 정상 복원 검증"}
        r_rb = self.client.post(f"/api/knowledge/studio/checklists/releases/{rel_id}/rollback", json=rb_payload, headers=self.headers_publisher)
        self.assertEqual(r_rb.status_code, 200)
        rb_data = r_rb.json()
        self.assertEqual(rb_data["status"], "ROLLED_BACK")

        # Verify item is restored to original text
        detail_after = get_scenario_detail(self.store, item.id)
        self.assertEqual(detail_after["item"]["required_text"], original_text)
        self.assertNotIn("[ROLLBACK_TEST_MARKER]", detail_after["item"]["required_text"])

    def test_public_published_and_preview_endpoints(self):
        """Anonymous callers can view published checklists and release previews without authentication."""
        # Public published checklists
        r_pub = self.client.get("/api/checklists/published")
        self.assertEqual(r_pub.status_code, 200)
        pub_data = r_pub.json()
        self.assertEqual(pub_data["total_items"], 647)
        self.assertEqual(len(pub_data["extension"]["items"]), 224)
        self.assertEqual(len(pub_data["change"]["items"]), 251)
        self.assertEqual(len(pub_data["registration"]["items"]), 172)

        # Publish a release for preview test
        rel_req = {
            "release_tag": "rel-preview-test-01",
            "release_note": "Preview verification",
            "target_procedure": "all",
        }
        r_create_rel = self.client.post("/api/knowledge/studio/checklists/publish/release", json=rel_req, headers=self.headers_publisher)
        self.assertEqual(r_create_rel.status_code, 200)
        rel_id = r_create_rel.json()["release_id"]

        # Public preview
        r_prev = self.client.get(f"/api/checklists/preview?release_id={rel_id}")
        self.assertEqual(r_prev.status_code, 200)
        prev_data = r_prev.json()
        self.assertTrue(prev_data["is_preview"])
        self.assertEqual(prev_data["release_tag"], "rel-preview-test-01")
        self.assertEqual(prev_data["total_items"], 647)


if __name__ == "__main__":
    unittest.main()

