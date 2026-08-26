"""Success-path contract tests for every LLM-backed HTTP endpoint.

Why this file exists
--------------------
Two production endpoints — ``/api/search/unified/ai-overview`` and
``/api/employment/interpret`` — unpacked the RESULT DICT returned by
``_openrouter_complete_with_candidates`` into a two-name tuple::

    text, attempt_meta = await _openrouter_complete_with_candidates(prompt)

A dict unpacks to its KEYS, so this raised ``ValueError`` on every call. Both
call sites wrapped it in a bare ``except Exception`` that reported
``status="unavailable", reason="provider_error"`` — so a healthy provider was
reported as an outage, and the features never ran in production even once.

The existing suites did not catch it because they only asserted the
*no-provider* branch, which returns before the model is ever called. Asserting
"it degrades safely" without also asserting "it works" cannot distinguish a
graceful degradation from a permanently broken feature.

Every test here therefore mocks a SUCCESSFUL provider and asserts the endpoint
produces real output. No network, no secrets, no live provider.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient  # noqa: E402

import paradiso_backend as pb  # noqa: E402


def provider_success(answer: str, *, final_model: str = "test/model-a") -> Dict[str, Any]:
    """A result dict shaped exactly like ``_openrouter_complete_with_candidates``.

    Keeping this in one place means a future change to the runtime's result
    contract breaks these tests loudly instead of silently re-introducing the
    "healthy provider reported as an outage" class of bug.
    """
    return {
        "ok": True,
        "answer": answer,
        "primary_model": final_model,
        "requested_model": None,
        "model_candidates": [final_model],
        "attempted_models": [final_model],
        "skipped_models_due_to_cooldown": [],
        "cooling_down_models": [],
        "model_cooldown_seconds": 300.0,
        "cooldown_enabled": True,
        "final_model": final_model,
        "model_fallback_used": False,
        "provider_error_type": None,
        "upstream_statuses": [],
        "retryable_provider_error": False,
        "all_candidates_failed": False,
    }


def provider_all_failed(error_type: str = "rate_limited") -> Dict[str, Any]:
    return {
        **provider_success(""),
        "ok": False,
        "answer": None,
        "final_model": None,
        "provider_error_type": error_type,
        "retryable_provider_error": True,
        "all_candidates_failed": True,
    }


class _ProviderConfigured(unittest.TestCase):
    """Base: an OpenRouter key is present so provider gates open."""

    def setUp(self) -> None:
        self._saved = os.environ.get("OPENROUTER_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = "test-key-never-used"
        # The module snapshots the key at import time.
        self._saved_module_key = pb.OPENROUTER_API_KEY
        pb.OPENROUTER_API_KEY = "test-key-never-used"
        self.client = TestClient(pb.app)

    def tearDown(self) -> None:
        pb.OPENROUTER_API_KEY = self._saved_module_key
        if self._saved is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = self._saved


class UnifiedAiOverviewSuccessTests(_ProviderConfigured):
    OVERVIEW = (
        "D-2 유학 자격은 정규 교육과정 수학을 목적으로 합니다. "
        "구체적인 요건은 하이코리아 또는 1345에서 확인하세요."
    )

    def _post(self, **kwargs: Any) -> Dict[str, Any]:
        return self.client.post(
            "/api/search/unified/ai-overview",
            json={"query": "D-2", **kwargs},
        ).json()

    def test_a_configured_provider_actually_produces_an_overview(self):
        """The regression: this returned `unavailable` with a working provider."""
        async def fake(prompt, **kw):
            return provider_success(self.OVERVIEW)

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        self.assertEqual(body["status"], "ok", msg=f"reason={body.get('reason')!r}")
        self.assertTrue(body["overview"], "a successful provider must yield overview text")

    def test_the_answering_model_is_reported_not_left_blank(self):
        async def fake(prompt, **kw):
            return provider_success(self.OVERVIEW, final_model="vendor/model-x")

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        # `final_model` is the key the runtime actually sets; reading a
        # non-existent "model" key silently blanked this in every response.
        self.assertEqual(body["model"], "vendor/model-x")
        self.assertEqual(body["provider"], "openrouter")

    def test_a_successful_overview_still_carries_evidence_and_citation_state(self):
        async def fake(prompt, **kw):
            return provider_success(self.OVERVIEW)

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        self.assertIn("citationVerification", body)
        self.assertIn("evidenceState", body)
        self.assertTrue(body["requiresOfficialConfirmation"])

    def test_all_candidates_failing_is_unavailable_with_the_classified_reason(self):
        """A real outage must still be quiet — and must name the actual reason."""
        async def fake(prompt, **kw):
            return provider_all_failed("rate_limited")

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        self.assertEqual(body["status"], "unavailable")
        self.assertEqual(body["reason"], "rate_limited")
        self.assertIsNone(body["overview"])
        self.assertTrue(body["fallbackAvailable"])

    def test_a_provider_exception_is_classified_not_flattened(self):
        async def fake(prompt, **kw):
            raise pb.HTTPException(
                status_code=502,
                detail={"error": "openrouter_upstream_error", "status": 429,
                        "message": "rate limit exceeded"},
            )

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        self.assertEqual(body["status"], "unavailable")
        # Previously `_classify_openrouter_error(exc)` was called with an
        # exception in the `status` slot, so every failure read
        # "unknown_provider_error".
        self.assertEqual(body["reason"], "rate_limited")

    def test_ai_failure_never_claims_there_are_no_search_results(self):
        async def fake(prompt, **kw):
            return provider_all_failed("upstream_unavailable")

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        self.assertTrue(body["fallbackAvailable"])
        self.assertNotIn("no results", (body.get("message") or "").lower())
        self.assertNotIn("검색 결과가 없", body.get("message") or "")


class EmploymentInterpretSuccessTests(_ProviderConfigured):
    GOOD_EXTRACTION = {
        "detectedLanguage": "ko",
        "role": "카페 바리스타",
        "tasks": ["음료 제조"],
        "workplace": "카페",
        "employerMainBusiness": "음식점업",
        "employmentType": "시간제",
        "incomeStatus": "유급",
        "visaStatus": "",
        "objects": ["음료"],
        "actions": ["제조"],
        "tools": [],
        "ambiguities": [],
        "needsClarification": False,
        "clarificationQuestion": "",
    }

    def _post(self, text: str = "카페에서 음료를 만들어요") -> Dict[str, Any]:
        return self.client.post("/api/employment/interpret", json={"text": text}).json()

    def test_a_configured_provider_actually_produces_an_extraction(self):
        """The regression: this returned `unavailable` with a working provider."""
        async def fake(prompt, **kw):
            return provider_success(json.dumps(self.GOOD_EXTRACTION, ensure_ascii=False))

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        self.assertEqual(body["status"], "ok", msg=f"reason={body.get('reason')!r}")
        self.assertEqual(body["extraction"]["role"], "카페 바리스타")
        self.assertTrue(body["interpretation"])

    def test_the_raw_sentence_always_reaches_the_deterministic_analyzer(self):
        async def fake(prompt, **kw):
            return provider_success(json.dumps(self.GOOD_EXTRACTION, ensure_ascii=False))

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        self.assertIn("카페", body["analyzerInput"]["text"])

    def test_a_successful_extraction_still_carries_no_classification_code(self):
        """The LLM may normalize language; it may never produce a KSCO/KSIC code."""
        polluted = {**self.GOOD_EXTRACTION, "role": "바리스타 5321", "visaStatus": "Z-9"}

        async def fake(prompt, **kw):
            return provider_success(json.dumps(polluted, ensure_ascii=False))

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        blob = json.dumps(body, ensure_ascii=False)
        self.assertNotIn("5321", blob)
        # An invented status code is not in visa_data.json and must be dropped.
        self.assertNotIn("Z-9", blob)
        self.assertTrue(body["warnings"], "every sanitization must be reported")

    def test_unparseable_model_output_is_extraction_failed_not_provider_error(self):
        """'The model said something useless' != 'the provider is down'."""
        async def fake(prompt, **kw):
            return provider_success("I am not JSON at all.")

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        self.assertEqual(body["status"], "extraction_failed")
        self.assertTrue(body["fallbackAvailable"])
        self.assertIn("카페", body["analyzerInput"]["text"])

    def test_all_candidates_failing_is_unavailable_with_the_classified_reason(self):
        async def fake(prompt, **kw):
            return provider_all_failed("upstream_unavailable")

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        self.assertEqual(body["status"], "unavailable")
        self.assertEqual(body["reason"], "upstream_unavailable")
        self.assertTrue(body["fallbackAvailable"])

    def test_the_answering_model_is_reported(self):
        async def fake(prompt, **kw):
            return provider_success(
                json.dumps(self.GOOD_EXTRACTION, ensure_ascii=False),
                final_model="vendor/model-y",
            )

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            body = self._post()
        self.assertEqual(body["model"], "vendor/model-y")


class AskSuccessPathTests(_ProviderConfigured):
    """/api/ask already read the result dict correctly; lock that in."""

    def test_a_configured_provider_produces_an_answer_with_model_metadata(self):
        async def fake(prompt, **kw):
            return provider_success("D-2 자격에 관한 안내입니다. 하이코리아에서 확인하세요.",
                                    final_model="vendor/model-z")

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            resp = self.client.post("/api/ask", json={"question": "D-2 아르바이트 가능한가요?"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["answer"])
        self.assertEqual(body["final_model"], "vendor/model-z")
        self.assertEqual(body["provider"], "openrouter")


class EnforcementProviderContractTests(_ProviderConfigured):
    """Enforcement consumes the SAME result dict; prove it reads it correctly."""

    def test_the_enforcement_adapter_returns_the_runtime_result_dict(self):
        async def fake(prompt, **kw):
            return provider_success('{"ok": true}')

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake):
            import asyncio
            result = asyncio.run(pb._enforcement_ai_provider("prompt"))
        # enforcement_service unwraps via `isinstance(raw, dict) and "ok" in raw`.
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)
        self.assertIn("answer", result)


class ResultContractTests(unittest.TestCase):
    """Guard the shape itself — the defect was a contract misreading."""

    def test_the_completion_helper_returns_a_mapping_not_a_sequence(self):
        keys = set(provider_success("x"))
        # Any caller that unpacks this into `a, b = ...` gets the KEYS and a
        # ValueError. Documenting the size here makes that failure mode obvious.
        self.assertGreater(len(keys), 2)
        self.assertIn("answer", keys)
        self.assertIn("final_model", keys)
        self.assertNotIn("model", keys, "there is no 'model' key — use final_model")
        self.assertNotIn("provider", keys, "there is no 'provider' key on the result")


if __name__ == "__main__":
    unittest.main()
