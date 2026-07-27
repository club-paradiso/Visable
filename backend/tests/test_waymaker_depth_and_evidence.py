"""Waymaker depth escalation + evidence-state metadata tests (Phase 3).

Rules under test:
  * exact-code / simple lookups stay fast;
  * deadlines, reporting duties, permission questions, status changes and
    activity-scope questions are promoted to at least basic, however terse;
  * precedent / administrative-litigation / refugee / deportation / refusal
    questions are promoted to pro.

    python3 -m pytest backend/tests/test_waymaker_depth_and_evidence.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import legal_research as lr  # noqa: E402


class ProEscalationTests(unittest.TestCase):
    def test_precedent_question_escalates_to_pro(self):
        self.assertEqual(lr.auto_select_depth("관련 판례가 있나요"), "pro")

    def test_administrative_litigation_escalates_to_pro(self):
        self.assertEqual(lr.auto_select_depth("행정심판을 청구할 수 있나요"), "pro")

    def test_refugee_question_escalates_to_pro(self):
        self.assertEqual(lr.auto_select_depth("난민 불인정 이의신청"), "pro")

    def test_deportation_escalates_to_pro(self):
        self.assertEqual(lr.auto_select_depth("강제퇴거"), "pro")

    def test_refusal_cancellation_escalates_to_pro(self):
        self.assertEqual(lr.auto_select_depth("불허 처분 취소"), "pro")

    def test_english_appeal_escalates_to_pro(self):
        self.assertEqual(lr.auto_select_depth("Can I appeal this denial"), "pro")

    def test_long_narrative_escalates_to_pro(self):
        long_question = (
            "저는 지금 D-10 상태이고, 작년에 학교를 졸업했으며, 지금 회사에서 인턴을 하고 "
            "있는데 정규직 제안을 받았고 동시에 배우자도 함께 체류 중입니다"
        )
        self.assertEqual(lr.auto_select_depth(long_question), "pro")


class BasicPromotionTests(unittest.TestCase):
    """Consequential topics must never be answered at fast depth."""

    def test_status_change_is_promoted_even_though_it_is_short(self):
        self.assertEqual(len("체류자격 변경") <= 22, True, "fixture must be short")
        self.assertEqual(lr.auto_select_depth("체류자격 변경"), "basic")

    def test_deadline_question_is_promoted(self):
        self.assertEqual(lr.auto_select_depth("신고 기한"), "basic")

    def test_reporting_duty_is_promoted(self):
        self.assertEqual(lr.auto_select_depth("신고해야 하나요"), "basic")

    def test_permission_question_is_promoted(self):
        self.assertEqual(lr.auto_select_depth("아르바이트 해도 되나요"), "basic")

    def test_activity_scope_is_promoted(self):
        self.assertEqual(lr.auto_select_depth("활동범위"), "basic")

    def test_workplace_change_is_promoted(self):
        self.assertEqual(lr.auto_select_depth("근무처 변경"), "basic")

    def test_english_deadline_is_promoted(self):
        self.assertEqual(lr.auto_select_depth("What is the deadline"), "basic")

    def test_english_permission_is_promoted(self):
        self.assertEqual(lr.auto_select_depth("Am I allowed to work"), "basic")


class FastPathTests(unittest.TestCase):
    def test_a_bare_code_stays_fast(self):
        self.assertEqual(lr.auto_select_depth("D-2-1"), "fast")

    def test_a_short_neutral_lookup_stays_fast(self):
        self.assertEqual(lr.auto_select_depth("유학 비자 종류"), "fast")

    def test_medium_length_question_defaults_to_basic(self):
        self.assertEqual(lr.auto_select_depth("한국에서 대학 졸업 후 어떤 준비가 필요한가요"), "basic")


class EscalationReasonTests(unittest.TestCase):
    """The reason must explain the depth actually chosen."""

    def test_reason_is_reported_for_each_rule(self):
        cases = {
            "관련 판례가 있나요": "pro_trigger_keyword",
            "체류자격 변경": "consequential_topic",
            "D-2-1": "short_simple_question",
        }
        for question, expected in cases.items():
            self.assertEqual(lr.depth_escalation_reason(question), expected, question)

    def test_reason_and_depth_never_disagree(self):
        questions = [
            "관련 판례가 있나요", "체류자격 변경", "D-2-1", "신고 기한",
            "강제퇴거", "한국에서 대학 졸업 후 어떤 준비가 필요한가요", "활동범위",
        ]
        for question in questions:
            depth = lr.auto_select_depth(question)
            reason = lr.depth_escalation_reason(question)
            if reason == "pro_trigger_keyword" or reason == "complex_narrative":
                self.assertEqual(depth, "pro", question)
            elif reason == "consequential_topic":
                self.assertEqual(depth, "basic", question)
            elif reason == "short_simple_question":
                self.assertEqual(depth, "fast", question)
            else:
                self.assertEqual(depth, "basic", question)

    def test_normalize_depth_rejects_unknown_values(self):
        self.assertEqual(lr.normalize_depth("turbo"), lr.DEFAULT_DEPTH)
        self.assertEqual(lr.normalize_depth(None), lr.DEFAULT_DEPTH)
        self.assertEqual(lr.normalize_depth("pro"), "pro")


class LawCardAnnotationTests(unittest.TestCase):
    """Ranked-search annotations must reach the frontend law card shape."""

    def test_law_card_carries_lifecycle_and_hierarchy(self):
        import paradiso_backend as pb
        card = pb._map_law_result({
            "law_name": "출입국관리법",
            "law_serial_no": "267581",
            "lifecycle_status": "repealed",
            "hierarchy_level": "statute",
            "name_match": True,
        })
        self.assertEqual(card["lifecycleStatus"], "repealed")
        self.assertEqual(card["hierarchyLevel"], "statute")
        self.assertTrue(card["nameMatch"])

    def test_law_card_source_url_is_public_and_secret_free(self):
        import paradiso_backend as pb
        card = pb._map_law_result({"law_name": "출입국관리법"})
        self.assertTrue(card["sourceUrl"].startswith("https://"))
        self.assertNotIn("OC=", card["sourceUrl"])


if __name__ == "__main__":
    unittest.main()
