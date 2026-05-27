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


if __name__ == "__main__":
    unittest.main()
