"""Regressions from the Waymaker functional QA of 2026-10-16.

  * A planned status change ("D-10 상태인데 E-7로 …") kept the target as the
    current status, so the deterministic answer read "E-7에서 E-7로" (and
    "from D-2 to D-2" in English).
  * "미국 국적" alone added the nationality/refugee issue.
  * Japanese kana and Hanja glued to Hangul ("만료前に", "目的으로") passed
    through Korean answers.

OpenRouter chain availability is covered in test_openrouter_model_candidates.py
and test_ai_runtime.py; the safety paraphrases in test_safety_guardrails.py.

Run from repo root:

    python3 -m pytest backend/tests/test_waymaker_qa_2026_10_16_regressions.py -q
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import paradiso_backend as pb  # noqa: E402
from services import answer_quality as aq  # noqa: E402
from services import answer_shape as ashape  # noqa: E402
from services.legal_analysis import classify_legal_issue_types, extract_immigration_facts  # noqa: E402

CANDS = ["a/one:free", "b/two:free"]


async def _openrouter_all_unavailable(prompt, model=None, max_tokens=None, **kwargs):
    raise HTTPException(
        status_code=502,
        detail={"error": "openrouter_upstream_error", "status": 503, "message": "No healthy upstream"},
    )


def _ask_fallback(question: str, *, lang: str = "ko") -> dict:
    old_mode = os.environ.get("LAW_GROUNDING_MODE")
    os.environ["LAW_GROUNDING_MODE"] = "audit"
    os.environ.pop("LAW_API_OC", None)
    os.environ.pop("LAW_API_KEY", None)
    try:
        pb._reset_visas_cache_for_tests()
        pb._reset_grounding_cache_for_tests()
        pb._reset_openrouter_model_cooldowns_for_tests()
        with patch.object(pb, "OPENROUTER_API_KEY", "or-test-key"), \
                patch.object(pb, "GROQ_API_KEY", None), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", False), \
                patch.object(pb, "ENABLE_OLLAMA_FALLBACK", False), \
                patch.object(pb, "OPENROUTER_MODEL", CANDS[0]), \
                patch.object(pb, "OPENROUTER_MODEL_CANDIDATES", list(CANDS)), \
                patch.object(pb, "_call_openrouter", _openrouter_all_unavailable):
            resp = TestClient(pb.app).post("/api/ask", json={"question": question, "lang": lang})
        assert resp.status_code == 200, resp.text
        return resp.json()
    finally:
        pb._reset_openrouter_model_cooldowns_for_tests()
        if old_mode is None:
            os.environ.pop("LAW_GROUNDING_MODE", None)
        else:
            os.environ["LAW_GROUNDING_MODE"] = old_mode


class PlannedStatusChangeTests(unittest.TestCase):
    PLANNED = (
        ("D-10 상태인데 E-7로 변경해서 취업하고 싶어요", "D-10", "E-7"),
        ("D-10에서 E-7로 변경 가능한가요?", "D-10", "E-7"),
        ("I'm on D-4 and want to change to D-2. What do I need?", "D-4", "D-2"),
        ("Can I change from D-4 to D-2?", "D-4", "D-2"),
    )

    def test_planned_change_keeps_the_source_as_current_status(self):
        for question, current, target in self.PLANNED:
            with self.subTest(question=question):
                facts = extract_immigration_facts(question)
                self.assertEqual(facts["current_status"], current)
                self.assertEqual(facts["target_status"], target)
                self.assertTrue(facts["status_transition_detected"])

    def test_completed_change_still_makes_the_new_status_current(self):
        for question in (
            "E-7에서 F-2-99로 변경 후 부업 신고는?",
            "I changed from E-7 to F-2-99 last month. Do I need to report a side job?",
        ):
            with self.subTest(question=question):
                facts = extract_immigration_facts(question)
                self.assertEqual(facts["previous_status"], "E-7")
                self.assertEqual(facts["current_status"], "F-2-99")

    def test_planned_change_is_not_a_residual_duty_question(self):
        question = "D-10에서 E-7로 변경하고 싶은데 이전 자격 조건이 문제가 되나요?"
        facts = extract_immigration_facts(question)
        self.assertNotIn("post_status_change_residual_duty", classify_legal_issue_types(question, facts))

    def test_korean_fallback_names_the_route_in_the_right_direction(self):
        body = _ask_fallback("D-10 상태인데 E-7로 변경해서 취업하고 싶어요")
        answer = body["answer"]
        self.assertIn("D-10에서 E-7로", answer)
        self.assertNotIn("E-7에서 E-7", answer)
        self.assertNotIn("이전 체류자격 D-10", answer)

    def test_english_fallback_names_the_route_in_the_right_direction(self):
        body = _ask_fallback("I'm on D-4 and want to change to D-2. What do I need?", lang="en")
        answer = body["answer"]
        self.assertIn("from D-4 to D-2", answer)
        self.assertNotIn("D-2 to D-2", answer)


class NationalityMentionTests(unittest.TestCase):
    def test_nationality_as_an_attribute_is_not_a_nationality_issue(self):
        for question in (
            "미국 국적인데 D-2 연장 서류가 궁금합니다",
            "I am a US national on D-2. What do I need for an extension?",
        ):
            with self.subTest(question=question):
                facts = extract_immigration_facts(question)
                self.assertNotIn("nationality_or_refugee_context", classify_legal_issue_types(question, facts))

    def test_nationality_procedures_still_raise_the_issue(self):
        for question in (
            "한국 국적 취득 요건이 궁금해요",
            "이중국적 유지가 가능한가요?",
            "귀화 naturalization 일반 요건은 무엇인가요?",
            "How do I acquire Korean nationality?",
            "난민 신청 후 G-1 체류 연장",
        ):
            with self.subTest(question=question):
                facts = extract_immigration_facts(question)
                self.assertIn("nationality_or_refugee_context", classify_legal_issue_types(question, facts))


class KoreanMixedLanguageTests(unittest.TestCase):
    def test_kana_and_attached_hanja_are_flagged(self):
        self.assertIn("kana_in_korean_answer", aq.scan_mixed_language_artifacts("만료前に 체류기간 연장을 신청하세요", "ko"))
        self.assertIn("hanja_attached_to_hangul", aq.scan_mixed_language_artifacts("일반적 절차 설명을目的으로 합니다", "ko"))

    def test_clean_korean_and_parenthetical_hanja_pass(self):
        for text in ("체류자격 변경 절차를 확인하세요.", "체류자격(滯留資格) 변경 절차", "D-2 연장 서류 4종"):
            with self.subTest(text=text):
                self.assertEqual(aq.scan_mixed_language_artifacts(text, "ko"), [])

    def test_answer_shape_gate_fails_a_korean_answer_with_kana(self):
        good = (
            "H-1 외국인등록은 입국일을 기준으로 정해진 기한 안에 해야 합니다. 본인의 입국일과 "
            "부여받은 체류기간을 먼저 확인해야 합니다. 신고는 하이코리아 또는 관할 출입국·외국인청에서 접수합니다.\n\n"
            "확인할 사실:\n* 입국일\n* 체류기간\n\n"
            "현재 연결된 직접 근거는 제한적이므로, 최종 기한과 제출 방식은 1345/HiKorea/관할 관서에서 확인하세요.\n"
            "공식 확인 질문:\n* 외국인등록 기한이 며칠인가요?"
        )
        facts = {"current_status": "H-1"}
        meta = {
            "legal_issue_types": ["registration_or_residence_report"],
            "immigration_facts": facts,
            "legal_analysis_exists": True,
            "answer_certainty_level": "limited",
        }
        contract = ashape.build_answer_shape_contract(
            legal_issue_types=["reporting_duty", "registration_or_residence_report"],
            immigration_facts=facts,
            answer_certainty_level="limited",
        )
        self.assertTrue(ashape.evaluate_answer_shape(good, meta, contract)["passed"])

        leaked = good.replace("기한 안에 해야", "기한 前に 해야")
        result = ashape.evaluate_answer_shape(leaked, meta, contract)
        self.assertFalse(result["passed"])
        self.assertEqual(result["repair_strategy"], "deterministic_synthesis")
        self.assertTrue(any(w.startswith("mixed_language_artifact:") for w in result["warnings"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
