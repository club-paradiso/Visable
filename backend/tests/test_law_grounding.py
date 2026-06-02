from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class LawGroundingIntentTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("LAW_GROUNDING_MODE", None)
        os.environ.pop("LAW_API_KEY", None)

    def test_g1_japan_reentry_question_attempts_law_grounding(self):
        from services.law_grounding import build_law_grounding_context, should_attempt_law_grounding

        question = "G-1-5 비자로 제주에 입국한지 2달차인데, 일본을 갈 수 있나요?"
        intent = should_attempt_law_grounding(question)

        self.assertTrue(intent["should_attempt"])
        self.assertIn("G-1", intent["reasons"])
        self.assertIn("출국/해외여행", intent["reasons"])

        context = build_law_grounding_context(question)
        self.assertFalse(context["attempted"], "disabled mode should not call external law API")
        self.assertIn("LAW_GROUNDING_DISABLED", context["grounding_warnings"])
        self.assertIn("출입국관리법", context["law_search_query"])
        self.assertIn("재입국허가", context["law_search_query"])
        self.assertIn("G-1", context["law_search_query"])

    def test_foreigner_registration_question_attempts_law_grounding(self):
        from services.law_grounding import build_law_grounding_context, should_attempt_law_grounding

        question = "E-7로 입국했는데 외국인등록 전 고용계약이 해지되면 어떻게 되나요?"
        intent = should_attempt_law_grounding(question)

        self.assertTrue(intent["should_attempt"])
        self.assertIn("외국인등록", intent["reasons"])

        context = build_law_grounding_context(question)
        self.assertIn("외국인등록", context["law_search_query"])
        self.assertIn("체류자격", context["law_search_query"])

    def test_existing_explicit_legal_basis_trigger_still_works(self):
        from services.law_grounding import build_law_search_query, should_attempt_law_grounding

        question = "출입국관리법상 재입국허가의 법적 근거는 무엇인가요?"
        intent = should_attempt_law_grounding(question)

        self.assertTrue(intent["should_attempt"])
        self.assertIn("출입국관리법", intent["reasons"])
        self.assertIn("법적 근거", intent["reasons"])
        self.assertIn(question, build_law_search_query(question, intent["reasons"]))

    def test_unrelated_question_does_not_attempt_law_grounding(self):
        from services.law_grounding import should_attempt_law_grounding

        intent = should_attempt_law_grounding("오늘 점심 뭐 먹지?")
        self.assertFalse(intent["should_attempt"])
        self.assertEqual(intent["reasons"], [])


class LawGroundingActivityScopeIntentTests(unittest.TestCase):
    """Activity-scope / study / H-1 intent and query-anchor coverage."""

    def setUp(self):
        os.environ.pop("LAW_GROUNDING_MODE", None)
        os.environ.pop("LAW_API_KEY", None)

    def test_h1_seasonal_course_question_attempts_with_study_and_h1_context(self):
        from services.law_grounding import build_law_grounding_context, should_attempt_law_grounding

        question = "H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?"
        intent = should_attempt_law_grounding(question)

        self.assertTrue(intent["should_attempt"])
        self.assertIn("유학/수강/계절학기", intent["reasons"])
        self.assertIn("관광취업/워킹홀리데이/H-1", intent["reasons"])

        context = build_law_grounding_context(question)
        # Disabled by default: no external call, but the anchored query is built.
        self.assertFalse(context["attempted"], "disabled mode must not call external law API")
        self.assertIn("LAW_GROUNDING_DISABLED", context["grounding_warnings"])
        for anchor in ("출입국관리법", "활동범위", "체류자격외활동", "관광취업", "H-1", "유학", "계절학기"):
            self.assertIn(anchor, context["law_search_query"], anchor)

    def test_generic_activity_scope_question_attempts_law_grounding(self):
        from services.law_grounding import build_law_search_query, should_attempt_law_grounding

        question = "지금 체류자격으로 체류자격외활동(아르바이트)이 가능한가요?"
        intent = should_attempt_law_grounding(question)
        self.assertTrue(intent["should_attempt"])
        self.assertIn("활동범위/자격외활동", intent["reasons"])
        query = build_law_search_query(question, intent["reasons"])
        self.assertIn("체류자격외활동", query)
        self.assertIn("활동범위", query)

    def test_english_study_question_attempts_law_grounding(self):
        from services.law_grounding import should_attempt_law_grounding

        intent = should_attempt_law_grounding("Can I take a university course / study with this status?")
        self.assertTrue(intent["should_attempt"])
        self.assertIn("유학/수강/계절학기", intent["reasons"])

    def test_gwanggwang_chwieop_working_holiday_terms_trigger(self):
        from services.law_grounding import should_attempt_law_grounding

        for q in ("관광취업 비자 활동 범위", "working holiday visa scope of activity", "워킹홀리데이 아르바이트"):
            self.assertTrue(should_attempt_law_grounding(q)["should_attempt"], q)

    def test_existing_generic_documents_question_still_does_not_trigger(self):
        # Regression guard: adding study/activity patterns must not make a
        # plain "what documents" question trigger law grounding.
        from services.law_grounding import should_attempt_law_grounding

        self.assertFalse(should_attempt_law_grounding("D-2 연장 서류가 뭐야?")["should_attempt"])
        self.assertFalse(should_attempt_law_grounding("오늘 점심 뭐 먹지?")["should_attempt"])


if __name__ == "__main__":
    unittest.main()
