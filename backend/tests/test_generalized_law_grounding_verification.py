"""Regression coverage for generalized law fan-out and article verification."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import answer_quality as aq  # noqa: E402
from services import law_grounding as lg  # noqa: E402
from services.grounding_config import GroundingConfig  # noqa: E402
import paradiso_backend as backend  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


QUESTION = "E-7 체류자가 근무처를 변경하려면 출입국관리법 제21조에 따라 사전허가가 필요한가요?"


def _law_result(name: str = "출입국관리법") -> dict:
    return {
        "status": "ok",
        "results": [{
            "source_type": "law",
            "title": name,
            "law_name": name,
            "law_id": "001386",
            "law_serial_no": "267581",
            "reference": "267581",
            "retrieval_status": "ok",
            "source_url": "https://www.law.go.kr/DRF/lawSearch.do?target=law",
        }],
        "error_type": "",
        "parser_status": "parsed_json",
        "response_shape_hint": "json_object",
        "source_url": "https://www.law.go.kr/DRF/lawSearch.do?target=law",
    }


class GeneralizedQueryPlanTests(unittest.TestCase):
    CASES = {
        "D-2 유학생 수강과 체류기간 연장, 시간제취업": ("유학", "연장허가", "체류자격외활동"),
        "D-4 어학연수 수강 체류기간 연장 자격외활동": ("유학", "연장허가", "체류자격외활동"),
        "E-7 근무처 변경 추가와 체류기간 연장": ("근무처 변경", "연장허가"),
        "F-6 결혼이민 체류기간 연장 중 이혼·별거": ("결혼이민", "연장허가"),
        "F-4 국내거소신고와 활동범위": ("외국인등록", "체류자격외활동"),
        "G-1-5 난민 인도적 체류 재입국 위험": ("난민법", "재입국"),
        "H-1 관광취업 활동범위와 취업 제한": ("관광취업",),
        "C-3 단기방문으로 취업 활동 가능한가요?": ("단기방문",),
        "B-1 사증면제로 취업 활동 가능한가요?": ("사증면제",),
        "귀화 요건과 면접, KIIP 기본소양을 국적법으로 확인": ("국적법", "사회통합프로그램"),
    }

    def test_issue_based_plan_generalizes_across_status_families(self):
        for question, anchors in self.CASES.items():
            with self.subTest(question=question):
                intent = lg.should_attempt_law_grounding(question)
                self.assertTrue(intent["should_attempt"])
                queries = lg.build_law_search_queries(question, intent["reasons"])
                self.assertGreater(len(queries), 0)
                self.assertLessEqual(len(queries), 6)
                joined = " ".join(queries)
                for anchor in anchors:
                    self.assertIn(anchor, joined)

    def test_live_plan_never_sends_joined_user_sentence(self):
        intent = lg.should_attempt_law_grounding(QUESTION)
        queries = lg.build_law_search_queries(QUESTION, intent["reasons"])
        self.assertNotIn(QUESTION, queries)
        self.assertIn("출입국관리법", queries)
        self.assertGreater(len(queries), 1)

    def test_workplace_synonyms_share_issue_plan(self):
        for phrase in ("근무처 변경", "근무처를 변경", "다른 회사로 이직", "고용주 변경"):
            with self.subTest(phrase=phrase):
                intent = lg.should_attempt_law_grounding(phrase)
                self.assertIn("근무처변경/이직", intent["reasons"])
                self.assertTrue(any("근무처 변경" in q for q in lg.build_law_search_queries(phrase, intent["reasons"])))


class ArticleVerificationFlowTests(unittest.TestCase):
    def setUp(self):
        self.cfg = GroundingConfig(mode="enabled", law_api_oc="secret-oc")

    def _context(self, detail: dict, search: dict | None = None) -> dict:
        with patch.object(lg, "load_grounding_config", return_value=self.cfg), \
             patch("services.law_tools.search_laws", return_value=search or _law_result()) as search_mock, \
             patch("services.law_tools.get_law_detail", return_value=detail) as detail_mock:
            context = lg.build_law_grounding_context(QUESTION)
        self.assertGreater(search_mock.call_count, 1, "queries must be executed independently")
        return context | {"_detail_calls": detail_mock.call_count}

    def test_article_verified_only_after_matching_detail_body(self):
        context = self._context({
            "status": "ok",
            "source_url": "https://www.law.go.kr/DRF/lawService.do?target=law&MST=267581",
            "detail": {
                "law_name": "출입국관리법",
                "articles": [{"article_no": "002100", "article_label": "제21조", "article_title": "근무처의 변경ㆍ추가", "text": "외국인은 미리 허가를 받아야 한다."}],
            },
        })
        self.assertEqual(context["citation_verification"]["status"], "verified")
        self.assertEqual(context["citation_verification"]["citations"][0]["verification_status"], "verified")
        self.assertEqual(context["_detail_calls"], 1)
        self.assertTrue(any(item.get("article") == "제21조" for item in context["law_grounding"]))

    def test_detail_failure_never_verifies_list_hit(self):
        context = self._context({"status": "error", "error_type": "law_api_timeout", "results": []})
        self.assertEqual(context["citation_verification"]["status"], "failed_verification")
        self.assertNotEqual(context["citation_verification"]["citations"][0]["verification_status"], "verified")

    def test_law_found_but_article_absent_is_source_linked_unverified(self):
        context = self._context({
            "status": "ok",
            "detail": {"law_name": "출입국관리법", "articles": []},
        })
        self.assertEqual(context["citation_verification"]["status"], "source_linked_unverified")

    def test_empty_or_timeout_search_degrades_safely(self):
        for error_type in ("law_api_no_results", "law_api_timeout", "law_api_bad_response"):
            with self.subTest(error_type=error_type), \
                 patch.object(lg, "load_grounding_config", return_value=self.cfg), \
                 patch("services.law_tools.search_laws", return_value={
                     "status": "error", "results": [], "error_type": error_type,
                     "parser_status": "unsupported_html" if error_type == "law_api_bad_response" else "",
                     "response_shape_hint": "html" if error_type == "law_api_bad_response" else "empty",
                     "source_url": "https://www.law.go.kr/DRF/lawSearch.do?target=law",
                 }), \
                 patch("services.law_tools.get_law_detail") as detail_mock:
                context = lg.build_law_grounding_context(QUESTION)
                self.assertFalse(context["law_grounding_used"])
                self.assertNotEqual(context["citation_verification"]["status"], "verified")
                detail_mock.assert_not_called()

    def test_secret_never_appears_in_context(self):
        context = self._context({"status": "error", "error_type": "law_api_timeout", "results": []})
        self.assertNotIn("secret-oc", repr(context))


class ConfidenceInvariantTests(unittest.TestCase):
    def _base(self) -> dict:
        return aq.classify_answer_quality(
            prompt="E-7 근무처 변경",
            visa_code="E-7",
            task_type="workplace_change",
            manual_grounding_present=False,
            structured_requirements_present=True,
            procedure_variant_present=False,
            law_grounding_used=False,
            law_grounding_status="unavailable",
            manual_to_law_fallback_used=False,
            law_intent=True,
        )

    def test_zero_direct_evidence_cannot_remain_high_or_confirmed(self):
        result = aq.enforce_source_confidence_invariants(
            self._base(), prompt="E-7 근무처 변경", visa_code="E-7", task_type="workplace_change",
            direct_evidence_count=0, missing_direct_authority=True,
        )
        self.assertNotEqual(result["answer_quality_mode"], "source_confirmed")
        self.assertNotEqual(result["source_confidence_level"], "high")
        self.assertTrue(result["requires_official_confirmation"])

    def test_unverified_specific_citation_forces_downgrade(self):
        result = aq.enforce_source_confidence_invariants(
            self._base(), prompt=QUESTION, visa_code="E-7", task_type="workplace_change",
            direct_evidence_count=1, missing_direct_authority=False,
            citation_specific=True, citation_verification_status="source_linked_unverified",
        )
        self.assertEqual(result["source_confidence_level"], "low")
        self.assertIn("CITATION_NOT_VERIFIED", result["source_confidence_invariant_reasons"])

    def test_zero_direct_evidence_invariant_is_status_agnostic(self):
        for visa_code, task_type, prompt in (
            ("D-2", "outside_status_activity", "D-2 시간제취업"),
            ("F-6", "marriage_divorce", "F-6 이혼 후 연장"),
            ("G-1", "reentry", "G-1 재입국"),
            ("H-1", "activity_scope", "H-1 취업 제한"),
        ):
            with self.subTest(visa_code=visa_code):
                optimistic = aq.classify_answer_quality(
                    prompt=prompt,
                    visa_code=visa_code,
                    task_type=task_type,
                    manual_grounding_present=False,
                    structured_requirements_present=True,
                    procedure_variant_present=False,
                    law_grounding_used=False,
                    law_grounding_status="unavailable",
                    manual_to_law_fallback_used=False,
                    law_intent=True,
                )
                result = aq.enforce_source_confidence_invariants(
                    optimistic,
                    prompt=prompt,
                    visa_code=visa_code,
                    task_type=task_type,
                    direct_evidence_count=0,
                    missing_direct_authority=True,
                    structured_procedure_mismatch=True,
                )
                self.assertNotEqual(result["answer_quality_mode"], "source_confirmed")
                self.assertEqual(result["source_confidence_level"], "low")
                self.assertTrue(result["requires_official_confirmation"])

    def test_citation_specific_list_hit_has_distinct_unverified_status(self):
        status = lg.derive_law_grounding_status_detail(
            configured_mode="enabled", effective_mode="enabled",
            intent_attempted=True, lookup_attempted=True, lookup_used=True,
            citation_specific=True, citation_verified=False,
        )
        self.assertEqual(status, "law_grounding_source_linked_unverified")
        self.assertFalse(lg.law_grounding_status_detail_is_verified(status))


class StructuredProcedureMatchTests(unittest.TestCase):
    def test_same_status_wrong_procedure_is_not_direct_evidence(self):
        self.assertEqual(
            backend._build_source_confirmed_structured_requirements_block(
                "E-7", None, "workplace_change"
            ),
            "",
        )
        self.assertTrue(
            backend._build_source_confirmed_structured_requirements_block(
                "E-7", None, "extension"
            )
        )

    def test_registration_and_extension_do_not_cross_confirm(self):
        registration = backend._build_source_confirmed_structured_requirements_block(
            "D-2", None, "foreigner_registration"
        )
        extension = backend._build_source_confirmed_structured_requirements_block(
            "D-2", None, "extension"
        )
        self.assertIn("registration", registration)
        self.assertNotIn("extension", registration)
        self.assertIn("extension", extension)
        self.assertNotIn("registration", extension)


class AskMetadataInvariantTests(unittest.TestCase):
    def test_e7_workplace_change_cannot_borrow_extension_or_registration_confidence(self):
        old_mode = os.environ.get("LAW_GROUNDING_MODE")
        old_key = os.environ.get("OPENROUTER_API_KEY")
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        os.environ["OPENROUTER_API_KEY"] = "test-key"

        async def fake_answer(prompt, model=None, max_tokens=None):
            return "공식 확인이 필요합니다."

        try:
            with patch.object(backend, "OPENROUTER_API_KEY", "test-key"), \
                 patch.object(backend, "_call_openrouter", fake_answer):
                response = TestClient(backend.app).post(
                    "/api/ask",
                    json={"message": QUESTION, "visa_code": "E-7", "lang": "ko"},
                )
        finally:
            if old_mode is None:
                os.environ.pop("LAW_GROUNDING_MODE", None)
            else:
                os.environ["LAW_GROUNDING_MODE"] = old_mode
            if old_key is None:
                os.environ.pop("OPENROUTER_API_KEY", None)
            else:
                os.environ["OPENROUTER_API_KEY"] = old_key

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertNotEqual(body["answer_quality_mode"], "source_confirmed")
        self.assertNotEqual(body["source_confidence_level"], "high")
        self.assertTrue(body["requires_official_confirmation"])
        self.assertTrue(body["law_evidence_pack"]["requires_official_confirmation"])
        self.assertEqual(body["direct_evidence_count"], 0)
        self.assertTrue(body["missing_direct_authority"])
        self.assertIn("STRUCTURED_PROCEDURE_MISMATCH", body["source_confidence_invariant_reasons"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
