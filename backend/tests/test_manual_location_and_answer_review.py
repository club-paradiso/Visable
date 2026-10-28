"""Manual routing by where the person is, and review flags for generated answers.

* services/procedure_location.py reads whether the foreigner a question is about is
  abroad (a visa matter) or in Korea (a stay matter); manual_evidence.procedure_scopes
  uses it only where the procedure words leave the manual open.
* services/manual_answer_checks.py flags an answer that counts a period from a start
  the manual excerpt does not use, or lifts a limit the excerpt sets. Flags only.

Both were measured in experiments/waymaker-ai/artemis_bootstrap on held-out sets that
agents wrote without seeing the code (see the module docstrings).

    python3 -m unittest backend.tests.test_manual_location_and_answer_review
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import manual_answer_checks as checks  # noqa: E402
from services import manual_evidence as me  # noqa: E402
from services import procedure_location as loc  # noqa: E402


class LocationTests(unittest.TestCase):
    def test_where_the_person_is(self):
        cases = [
            ("지금 필리핀 마닐라에서 지내는데 한국 대학원에 합격했어요. 유학 비자 받으면 체류기간은 얼마나 나오나요?", "abroad"),
            ("I'm in Lagos and just got an offer from a lab in Daejeon. How do I apply for the research visa?", "abroad"),
            ("한국에 있는 회사가 저를 뽑겠다는데 저는 아직 하노이에 있어요. 회사 쪽에서 뭘 해 줘야 하나요?", "abroad"),
            ("체류기간이 다음 주에 끝나는데 연장 신청은 어디서 하나요? 지금 인천에 살아요.", "korea"),
            ("I came to Korea visa-free for a health check-up and the hospital now says I need long-term treatment.", "korea"),
            ("저는 하노이에 있고요, 한국에서 일하는 동생이 외국인등록증을 잃어버렸대요. 동생은 어떻게 해야 하나요?", "korea"),
        ]
        for question, where in cases:
            with self.subTest(question=question):
                self.assertEqual(loc.location(question), where)

    def test_no_location_is_said(self):
        for question in ("E-7 비자 요건이 어떻게 되나요?",
                         "C-4로 계절근로 와서 농장에서 일하고 있어요. 다른 농장에서도 같이 일할 수 있나요?",
                         "D-2로 한국에서 공부하려면 어떤 서류가 필요해요?",
                         "오늘 서울 날씨 어때요?"):
            with self.subTest(question=question):
                self.assertEqual(loc.location(question), "")


class ScopeTests(unittest.TestCase):
    def test_location_settles_what_the_procedure_words_leave_open(self):
        abroad_d4 = "베트남에 살고 있는데 한국 대학 어학당에서 한국어를 배우고 싶어요. D-4로 가면 체류기간은 얼마나 받을 수 있어요?"
        self.assertEqual(me.procedure_scopes(abroad_d4, None, has_code=True), [(me.SCOPE_VISA, "사증발급")])
        in_korea = "I came to Korea visa-free for a health check-up and the hospital now says I need long-term treatment."
        self.assertEqual(me.procedure_scopes(in_korea, None, has_code=False), [(me.SCOPE_STAY, "체류 관리")])

    def test_a_named_stay_procedure_is_never_overridden(self):
        relative = "필리핀에 사는 엄마예요. 한국에서 유학 중인 딸 비자가 곧 끝나는데 딸이 연장하려면 뭐가 필요해요?"
        self.assertEqual([s for s, _ in me.procedure_scopes(relative, "extension", has_code=False)], [me.SCOPE_STAY])
        workplace = "E-7 비자로 일하고 있는데 회사를 옮기려고 합니다. 근무처 변경은 어떻게 하나요?"
        self.assertEqual([s for s, _ in me.procedure_scopes(workplace, "workplace_change", has_code=True)], [me.SCOPE_STAY])
        self.assertEqual(me.procedure_scopes("오늘 서울 날씨 어때요?", None, has_code=False), [])

    def test_the_cues_can_be_turned_off(self):
        abroad_d4 = "베트남에 살고 있는데 한국 대학 어학당에서 한국어를 배우고 싶어요. D-4로 가면 체류기간은 얼마나 받을 수 있어요?"
        with patch.dict(os.environ, {"VISABLE_MANUAL_LOCATION_CUES": "0"}):
            self.assertNotEqual(me.procedure_scopes(abroad_d4, None, has_code=True), [(me.SCOPE_VISA, "사증발급")])


class AnswerReviewTests(unittest.TestCase):
    START = [{"text": "어학연수(D-4-1)자격은 변경일(사증소지자는 입국일)로부터 6개월이 경과된 사람"}]
    AGENCY = [{"text": "출국 중에 있는 외국인에 대한 출입국민원 대행기관의 대행신청은 할 수 없음."}]

    def test_start_point_not_in_the_excerpt(self):
        wrong = checks.review("활동을 하려는 시점으로부터 6개월이 지나야 합니다.", self.START)
        right = checks.review("입국일로부터 6개월이 지나야 합니다.", self.START)
        self.assertEqual([f["kind"] for f in wrong["flags"]], ["start_point"])
        self.assertEqual(right, {"checked": True, "flags": []})

    def test_lifted_limit(self):
        wrong = checks.review("출국 중이어도 출입국민원 대행기관이 대행신청을 할 수 있습니다.", self.AGENCY)
        right = checks.review("출국 중이면 대행기관이 대행신청을 할 수 없습니다.", self.AGENCY)
        self.assertEqual([f["kind"] for f in wrong["flags"]], ["permission_flip"])
        self.assertEqual(right["flags"], [])

    def test_an_exception_the_excerpt_grants_is_not_flagged(self):
        excerpt = [{"text": "사우디아라비아, 이란, 리비아는 복수재입국제한. 단, 동 국가의 국민 중 결혼이민(F-6), 유학(D-2), 일반연수(D-4)는 가능"}]
        answer = "사우디아라비아, 이란, 리비아 국민 중 결혼이민(F-6), 유학(D-2), 일반연수(D-4)는 복수재입국이 가능합니다."
        self.assertEqual(checks.review(answer, excerpt)["flags"], [])

    def test_nothing_to_check_against(self):
        self.assertEqual(checks.review("어떤 답", []), {"checked": False, "flags": []})


class WiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import paradiso_backend as pb
        cls.pb = pb

    def test_review_meta_never_raises_and_needs_excerpts(self):
        self.assertEqual(self.pb._manual_answer_review_meta("답", None), {})
        self.assertEqual(self.pb._manual_answer_review_meta("답", {"excerpts": []}), {})
        meta = self.pb._manual_answer_review_meta("활동을 하려는 시점으로부터 6개월이 지나야 합니다.",
                                                  {"excerpts": AnswerReviewTests.START})
        self.assertTrue(meta["checked"] and meta["flags"])

    def test_review_is_diagnostics_only(self):
        payload = {"answer": "x", "manual_answer_review": {"checked": True, "flags": [{"kind": "start_point"}]}}
        self.assertNotIn("manual_answer_review", self.pb._public_ask_payload(payload))
        self.assertIn("manual_answer_review", self.pb.AskResponse.model_fields)


class TelemetryAndStreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import paradiso_backend as pb
        cls.pb = pb

    def test_counts_carry_no_text(self):
        review = {"checked": True, "flags": [{"kind": "start_point", "detail": "답 문장"},
                                             {"kind": "permission_flip", "detail": "x"},
                                             {"kind": "start_point", "detail": "y"}]}
        self.assertEqual(self.pb._manual_review_counts(review), {"checked": True, "start_point": 2, "permission_flip": 1})
        self.assertEqual(self.pb._manual_review_counts(None), {"checked": False})

    def test_routing_log_has_scopes_and_flag_counts(self):
        req = self.pb.AskRequest(message="질문")
        payload = {"manual_evidence_scopes": ["stay"],
                   "manual_answer_review": {"checked": True, "flags": [{"kind": "start_point", "detail": "비밀 아님"}]}}
        with self.assertLogs("paradiso.backend", level="INFO") as logs:
            self.pb._log_ask_routing_telemetry(payload, req=req, status_code=200, latency_ms=1)
        line = next(m for m in logs.output if "ask_routing" in m)
        self.assertIn('"manual_evidence_scopes": ["stay"]', line)
        self.assertIn('"start_point": 1', line)
        self.assertNotIn("비밀 아님", line)

    def test_stream_done_frame_is_public_without_the_review(self):
        import asyncio
        import json as _json
        frame = self.pb._sse("done", {"final_model": "m", "manual_answer_review": {"checked": True, "flags": []}})

        async def collect():
            async def gen():
                yield frame
            return [chunk async for chunk in self.pb._public_sse_stream(gen())]
        out = asyncio.run(collect())[0]
        self.assertTrue(out.startswith("event: done"))
        data = _json.loads(out.split("data: ", 1)[1])
        self.assertNotIn("manual_answer_review", data)


if __name__ == "__main__":
    unittest.main()
