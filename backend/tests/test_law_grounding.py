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

        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        self.addCleanup(lambda: os.environ.pop("LAW_GROUNDING_MODE", None))
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

        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        self.addCleanup(lambda: os.environ.pop("LAW_GROUNDING_MODE", None))
        context = build_law_grounding_context(question)
        # Disabled mode: no external call, but the anchored query is built.
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


class H1ActivityScopeRegressionTests(unittest.TestCase):
    """The four required H-1 / activity-scope regression questions."""

    CASES = [
        "H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?",
        "H-1으로 한국에서 수업을 들을 수 있나요?",
        "Can I take a university class in Korea on H-1?",
        "Can I work or study with this status?",
    ]

    def setUp(self):
        os.environ.pop("LAW_GROUNDING_MODE", None)
        os.environ.pop("LAW_API_KEY", None)

    def test_all_cases_trigger_grounding_intent(self):
        from services.law_grounding import should_attempt_law_grounding

        for q in self.CASES:
            self.assertTrue(should_attempt_law_grounding(q)["should_attempt"], q)

    def test_study_class_term_detected(self):
        from services.law_grounding import should_attempt_law_grounding

        # "수업" (class/lesson) is now a study-intent term.
        reasons = should_attempt_law_grounding("H-1으로 한국에서 수업을 들을 수 있나요?")["reasons"]
        self.assertIn("유학/수강/계절학기", reasons)

    def test_disabled_mode_reports_intent_and_query_without_external_call(self):
        from services.law_grounding import build_law_grounding_context

        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        self.addCleanup(lambda: os.environ.pop("LAW_GROUNDING_MODE", None))
        ctx = build_law_grounding_context(self.CASES[0])
        self.assertFalse(ctx["attempted"], "disabled mode must not call external API")
        self.assertIn("LAW_GROUNDING_DISABLED", ctx["grounding_warnings"])
        self.assertTrue(ctx["intent_reasons"])
        self.assertIn("출입국관리법", ctx["law_search_query"])


class LawGroundingPreflightTests(unittest.TestCase):
    def setUp(self):
        for k in ("LAW_GROUNDING_MODE", "LAW_API_KEY", "LAW_API_BASE_URL", "LAW_API_SEARCH_PATH"):
            os.environ.pop(k, None)

    def tearDown(self):
        for k in ("LAW_GROUNDING_MODE", "LAW_API_KEY", "LAW_API_BASE_URL", "LAW_API_SEARCH_PATH"):
            os.environ.pop(k, None)

    def test_disabled_preflight_reports_safe_defaults(self):
        from services.law_grounding import law_grounding_preflight

        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        pf = law_grounding_preflight()
        self.assertEqual(pf["mode"], "disabled")
        self.assertEqual(pf["external_calls"], "disabled")
        self.assertFalse(pf["law_api_key_configured"])
        self.assertFalse(pf["law_api_endpoint_configured"])
        self.assertFalse(pf["ready_for_external_calls"])
        self.assertTrue(pf["sample_would_trigger"])  # default sample is the H-1 case
        self.assertIn("출입국관리법", pf["sample_law_search_query"])
        self.assertIn("LAW_GROUNDING_DISABLED", pf["warnings"])

    def test_audit_missing_key_and_endpoint_warnings(self):
        from services.law_grounding import law_grounding_preflight

        os.environ["LAW_GROUNDING_MODE"] = "audit"
        pf = law_grounding_preflight("출입국관리법 제10조 법적 근거")
        self.assertEqual(pf["external_calls"], "audit_only")
        self.assertIn("LAW_GROUNDING_AUDIT_ONLY", pf["warnings"])
        self.assertIn("LAW_API_KEY_MISSING", pf["warnings"])
        self.assertIn("LAW_API_ENDPOINT_MISSING", pf["warnings"])
        self.assertFalse(pf["ready_for_external_calls"])

    def test_preflight_never_returns_secret_value(self):
        from services.law_grounding import law_grounding_preflight

        os.environ["LAW_GROUNDING_MODE"] = "enabled"
        os.environ["LAW_API_KEY"] = "super-secret-law-key"
        os.environ["LAW_API_BASE_URL"] = "https://example.test"
        os.environ["LAW_API_SEARCH_PATH"] = "/search"
        pf = law_grounding_preflight()
        # The key is reported as a boolean only; its value never appears.
        self.assertTrue(pf["law_api_key_configured"])
        self.assertTrue(pf["law_api_endpoint_configured"])
        self.assertTrue(pf["ready_for_external_calls"])
        self.assertNotIn("super-secret-law-key", repr(pf))
        self.assertNotIn("example.test", repr(pf))

    def test_custom_sample_question_used(self):
        from services.law_grounding import law_grounding_preflight

        pf = law_grounding_preflight("오늘 점심 뭐 먹지?")
        self.assertEqual(pf["sample_question"], "오늘 점심 뭐 먹지?")
        self.assertFalse(pf["sample_would_trigger"])


if __name__ == "__main__":
    unittest.main()
