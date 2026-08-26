"""Contract tests for /api/nationality-coach.

This endpoint shipped with no backend tests at all, which is how it kept its
own private Groq-first provider routing — a single model per provider, no
candidate chain, no cooldown, no error taxonomy, and no regard for the
deployment's `ALLOW_GROQ_FALLBACK` posture — long after the rest of the
platform moved to a governed chain.

The safety rules matter more here than anywhere else in Visable: naturalization
practice feedback must never fabricate the user's biography or claim to know an
adjudication outcome. Those invariants are asserted directly rather than left
to prompt text.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any, Dict, Optional
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient  # noqa: E402

import paradiso_backend as pb  # noqa: E402
from services import ai_runtime as rt  # noqa: E402

GOOD_FEEDBACK = {
    "strengths": ["질문에 바로 답했습니다."],
    "improvements": ["구체적인 예시를 덧붙이면 좋겠습니다."],
    "revisedAnswer": "저는 한국에서 5년간 일하며 지역 사회와 함께해 왔습니다.",
    "riskyExpressions": [],
    "followUpQuestion": "그 경험에서 가장 기억에 남는 일은 무엇인가요?",
    "studyTip": "이유 → 예시 → 결론 순서로 연습해 보세요.",
    "caution": "이 피드백은 연습용이며 실제 심사 결과를 보장하지 않습니다.",
}


class _CoachTestCase(unittest.TestCase):
    def setUp(self):
        self._saved = {k: getattr(pb, k) for k in ("OPENROUTER_API_KEY", "GROQ_API_KEY")}
        self.client = TestClient(pb.app)
        pb._MODEL_COOLDOWNS.clear()

    def tearDown(self):
        for key, value in self._saved.items():
            setattr(pb, key, value)
        pb._MODEL_COOLDOWNS.clear()

    def post(self, **kwargs: Any):
        payload = {
            "mode": "naturalization_interview_prep",
            "question": "귀화를 신청한 이유는 무엇입니까?",
            "answer": "한국에서 오래 살았고 계속 살고 싶습니다.",
            **kwargs,
        }
        return self.client.post("/api/nationality-coach", json=payload)


class CoachRuntimeRoutingTests(_CoachTestCase):
    def test_openrouter_is_preferred_when_configured(self):
        """Was Groq-first, so a strict-OpenRouter deploy still answered on Groq."""
        pb.OPENROUTER_API_KEY = "test-key"
        pb.GROQ_API_KEY = "test-groq"
        groq_called = []

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            return json.dumps(GOOD_FEEDBACK, ensure_ascii=False)

        async def fake_groq(prompt, model=None, system_prompt=None):
            groq_called.append(model)
            return "{}"

        with patch.object(pb, "_call_openrouter", new=fake_openrouter), \
             patch.object(pb, "_call_groq", new=fake_groq):
            body = self.post().json()

        self.assertEqual(body["provider"], "openrouter")
        self.assertEqual(groq_called, [], "Groq must not be called when OpenRouter answers")

    def test_the_coach_uses_the_governed_candidate_chain(self):
        pb.OPENROUTER_API_KEY = "test-key"
        pb.GROQ_API_KEY = None
        seen = []

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            seen.append(model)
            return json.dumps(GOOD_FEEDBACK, ensure_ascii=False)

        with patch.object(pb, "_call_openrouter", new=fake_openrouter):
            self.post()

        expected = rt.resolve_task_models(rt.TaskRole.NATIONALITY_COACH)["candidates"]
        self.assertEqual(seen[0], expected[0])

    def test_a_rate_limited_model_falls_through_to_the_next_candidate(self):
        """The old routing had no chain: one 429 meant no feedback at all."""
        pb.OPENROUTER_API_KEY = "test-key"
        pb.GROQ_API_KEY = None
        calls = []

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            calls.append(model)
            if len(calls) == 1:
                raise pb.HTTPException(
                    status_code=502,
                    detail={"error": "openrouter_upstream_error", "status": 429,
                            "message": "rate limit exceeded"},
                )
            return json.dumps(GOOD_FEEDBACK, ensure_ascii=False)

        with patch.object(pb, "_call_openrouter", new=fake_openrouter):
            body = self.post().json()

        self.assertEqual(len(calls), 2)
        self.assertTrue(body["ai_available"])
        self.assertTrue(body["modelFallbackUsed"])

    def test_a_groq_only_deployment_still_answers(self):
        """Ordering changed; a Groq-only deploy must not lose the feature."""
        pb.OPENROUTER_API_KEY = None
        pb.GROQ_API_KEY = "test-groq"

        async def fake_groq(prompt, model=None, system_prompt=None):
            return json.dumps(GOOD_FEEDBACK, ensure_ascii=False)

        with patch.object(pb, "_call_groq", new=fake_groq):
            body = self.post().json()

        self.assertEqual(body["provider"], "groq")
        self.assertTrue(body["ai_available"])

    def test_groq_rescues_a_fully_failed_openrouter_chain(self):
        pb.OPENROUTER_API_KEY = "test-key"
        pb.GROQ_API_KEY = "test-groq"

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            raise pb.HTTPException(
                status_code=502,
                detail={"error": "openrouter_upstream_error", "status": 503,
                        "message": "no healthy upstream"},
            )

        async def fake_groq(prompt, model=None, system_prompt=None):
            return json.dumps(GOOD_FEEDBACK, ensure_ascii=False)

        with patch.object(pb, "_call_openrouter", new=fake_openrouter), \
             patch.object(pb, "_call_groq", new=fake_groq):
            body = self.post().json()

        self.assertEqual(body["provider"], "groq")

    def test_bad_credentials_stop_the_chain_instead_of_burning_it(self):
        pb.OPENROUTER_API_KEY = "expired-key"
        pb.GROQ_API_KEY = None
        calls = []

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            calls.append(model)
            raise pb.HTTPException(
                status_code=502,
                detail={"error": "openrouter_upstream_error", "status": 401,
                        "message": "No auth credentials found"},
            )

        with patch.object(pb, "_call_openrouter", new=fake_openrouter):
            resp = self.post()

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(len(calls), 1, "an expired key must not be retried per-model")

    def test_no_provider_is_a_clean_503_the_hub_can_fall_back_from(self):
        pb.OPENROUTER_API_KEY = None
        pb.GROQ_API_KEY = None
        resp = self.post()
        self.assertEqual(resp.status_code, 503)
        # The hub renders local heuristic feedback on 503 — it must never hang.
        self.assertIn("coach_unavailable", json.dumps(resp.json()))

    def test_a_failure_reports_the_classified_provider_reason(self):
        pb.OPENROUTER_API_KEY = "test-key"
        pb.GROQ_API_KEY = None

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            raise pb.HTTPException(
                status_code=502,
                detail={"error": "openrouter_upstream_error", "status": 429,
                        "message": "rate limit exceeded"},
            )

        with patch.object(pb, "_call_openrouter", new=fake_openrouter):
            resp = self.post()

        detail = resp.json()["detail"]
        self.assertEqual(detail["provider_error_type"], "rate_limited")


class CoachSafetyTests(_CoachTestCase):
    """The coach may improve an answer's clarity; it may not invent the answer."""

    def _feedback_with(self, **overrides) -> Dict[str, Any]:
        pb.OPENROUTER_API_KEY = "test-key"
        pb.GROQ_API_KEY = None
        payload = {**GOOD_FEEDBACK, **overrides}

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            return json.dumps(payload, ensure_ascii=False)

        with patch.object(pb, "_call_openrouter", new=fake_openrouter):
            return self.post().json()

    def test_the_practice_only_caution_is_always_present(self):
        body = self._feedback_with(caution="")
        self.assertTrue(body["caution"], "the practice-only caution is not optional")
        self.assertIn("보장하지 않습니다", body["caution"])

    def test_the_coach_uses_its_own_governance_prompt_not_the_answer_prompt(self):
        """Waymaker's answer-shape directives do not apply to practice feedback."""
        pb.OPENROUTER_API_KEY = "test-key"
        pb.GROQ_API_KEY = None
        seen = {}

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            seen["system"] = system_prompt
            return json.dumps(GOOD_FEEDBACK, ensure_ascii=False)

        with patch.object(pb, "_call_openrouter", new=fake_openrouter):
            self.post()

        self.assertTrue(seen["system"], "a system prompt must always be sent")
        self.assertNotEqual(seen["system"], pb.WAYMAKER_SYSTEM_PROMPT)
        self.assertEqual(seen["system"], pb.NATURALIZATION_INTERVIEW_PREP_SYSTEM_PROMPT)

    def test_the_nationality_services_mode_uses_its_own_prompt(self):
        pb.OPENROUTER_API_KEY = "test-key"
        pb.GROQ_API_KEY = None
        seen = {}

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            seen["system"] = system_prompt
            return json.dumps({"summary": "일반 안내입니다."}, ensure_ascii=False)

        with patch.object(pb, "_call_openrouter", new=fake_openrouter):
            self.post(mode="nationality_services", message="귀화 절차가 궁금합니다")

        self.assertEqual(seen["system"], pb.NATIONALITY_SERVICES_SYSTEM_PROMPT)

    def test_unparseable_model_output_is_a_502_not_a_fabricated_answer(self):
        pb.OPENROUTER_API_KEY = "test-key"
        pb.GROQ_API_KEY = None

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            return "Sorry, I cannot help with that."

        with patch.object(pb, "_call_openrouter", new=fake_openrouter):
            resp = self.post()

        self.assertEqual(resp.status_code, 502)

    def test_the_response_never_leaks_a_credential_or_a_raw_provider_body(self):
        pb.OPENROUTER_API_KEY = "sk-or-v1-secret-value-here"
        pb.GROQ_API_KEY = None

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            raise pb.HTTPException(
                status_code=502,
                detail={"error": "openrouter_upstream_error", "status": 401,
                        "message": "Authorization: Bearer sk-or-v1-secret-value-here rejected"},
            )

        with patch.object(pb, "_call_openrouter", new=fake_openrouter):
            resp = self.post()

        blob = resp.text
        self.assertNotIn("sk-or-v1-secret-value-here", blob)
        self.assertNotIn("Bearer", blob)


class CoachSharedCooldownTests(_CoachTestCase):
    """The coach shares ONE circuit breaker with every other AI feature."""

    def test_a_model_cooling_down_from_another_feature_is_skipped(self):
        pb.OPENROUTER_API_KEY = "test-key"
        pb.GROQ_API_KEY = None
        chain = rt.resolve_task_models(rt.TaskRole.NATIONALITY_COACH)["candidates"]
        pb._MODEL_COOLDOWNS.mark(chain[0])
        seen = []

        async def fake_openrouter(prompt, model=None, max_tokens=None, system_prompt=None):
            seen.append(model)
            return json.dumps(GOOD_FEEDBACK, ensure_ascii=False)

        with patch.object(pb, "_call_openrouter", new=fake_openrouter):
            self.post()

        self.assertNotIn(chain[0], seen,
                         "a model already known to be failing must not be retried at full cost")


if __name__ == "__main__":
    unittest.main()
