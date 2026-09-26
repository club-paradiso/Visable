"""Verified structured answers must survive AI summary failure.

Production incident (after #641): ``POST /api/ask`` with
``{"question": "D-2 연장시 필수 서류", "visa_code": "D-2", "answer_mode": "fast"}``
returned HTTP 503 (``structured_answer: false``) while the same D-2 question on
Basic returned 200. ``_ask_internal`` had already built the source-confirmed
structured document answer, in which the model only contributes an optional
short summary; the non-retryable provider-error branch then raised 503 and
discarded it.

These tests run the REAL candidate chain (only ``_call_openrouter`` is stubbed)
so the non-retryable classification path that raised the 503 is exercised,
and pin that model-dependent questions keep their existing failure semantics.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import paradiso_backend as pb  # noqa: E402

D2_FAST_REQUEST = {
    "question": "D-2 연장시 필수 서류",
    "visa_code": "D-2",
    "answer_mode": "fast",
    "stream": False,
}
# Complex question: no structured answer is built (model-dependent).
MODEL_DEPENDENT_QUESTION = "D-2 연장 서류랑 체류자격 변경 가능한지도 알려줘"
VENDOR_TERMS = ("openrouter", "groq", "ollama", "nemotron", "gemma", "nvidia", "inkling", "thinkingmachines")
PUBLIC_FORBIDDEN_KEYS = (
    "provider", "model", "final_model", "selected_model", "attempted_models",
    "llm_provider", "primary_model", "model_candidates", "provider_error_type",
    "summary_generation_status", "summary_generation_failed", "fallback_answer_reason",
)
INTERNAL_METADATA_TERMS = ("source file", "source_file", "source_revision_date")
MODEL_SUMMARY = "유학(D-2) 체류기간 연장허가에는 기본 서류와 학업·재정·체류지 관련 증빙이 필요합니다."


def _model_not_found(model: str) -> HTTPException:
    return HTTPException(status_code=502, detail={
        "error": "openrouter_http_error", "status": 404,
        "message": f"No endpoints found for {model}.",
    })


def _rate_limited(model: str) -> HTTPException:
    return HTTPException(status_code=502, detail={
        "error": "openrouter_http_error", "status": 429,
        "message": "Rate limit exceeded: free-models-per-min.",
    })


def _bad_request(model: str) -> HTTPException:
    return HTTPException(status_code=502, detail={
        "error": "openrouter_http_error", "status": 400,
        "message": "Invalid request: malformed parameter.",
    })


class _Harness(unittest.TestCase):
    def setUp(self) -> None:
        pb._reset_openrouter_model_cooldowns_for_tests()
        self.calls: List[str] = []

    def tearDown(self) -> None:
        pb._reset_openrouter_model_cooldowns_for_tests()

    def _post(self, body: Dict[str, Any], *, raise_for=None, answer: Optional[str] = MODEL_SUMMARY,
              api_key: Optional[str] = "sk-test-sentinel", diagnostics: bool = False):
        async def fake_call(prompt, model=None, max_tokens=None, **kw):
            self.calls.append(model)
            if raise_for is not None:
                exc = raise_for(model)
                if exc is not None:
                    raise exc
            return answer

        headers = {"x-paradiso-diagnostics": "1"} if diagnostics else {}
        with patch.object(pb, "OPENROUTER_API_KEY", api_key), \
                patch.object(pb, "GROQ_API_KEY", None), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", False), \
                patch.object(pb, "ENABLE_OLLAMA_FALLBACK", False), \
                patch.object(pb, "_call_openrouter", fake_call):
            return TestClient(pb.app, headers=headers).post("/api/ask", json={"consent": True, "lang": "ko", **body})

    def _canonical_d2(self) -> List[str]:
        bundle = pb._load_stay_manual_grounding() or {}
        return next(g for g in bundle["groundings"] if g["visa_code"] == "D-2")["required_documents"]

    def assert_canonical_structured(self, body: Dict[str, Any], *, summary_source: str) -> None:
        structured = body["structured_answer"]
        self.assertIsInstance(structured, dict)
        self.assertEqual(structured["kind"], "documents")
        self.assertEqual(structured["short_answer_source"], summary_source)
        docs = structured["required_documents"]
        self.assertEqual([d["label"] for d in docs["common"]], ["신청서", "여권", "외국인등록증", "수수료"])
        self.assertEqual(len(docs["conditional"]), 1)
        self.assertIn("재정입증 서류", [d["label"] for d in docs["required"]])
        rendered = [d["source_text"] for bucket in docs.values() for d in bucket]
        self.assertEqual(sorted(rendered), sorted(self._canonical_d2()))
        self.assertEqual(structured["source"]["title"], "외국인체류 안내매뉴얼")
        self.assertEqual(structured["source"]["edition"], "2026.6")
        self.assertEqual(structured["source"]["page_range"], "43-44")
        self.assertEqual(body["answer_mode_requested"], "fast")
        self.assertEqual(body["answer_mode"], "fast")
        self.assertFalse(body["answer_mode_auto_escalated"])
        for doc in ("신청서", "여권", "외국인등록증", "수수료"):
            self.assertIn(doc, body["answer"])

    def assert_public(self, resp) -> None:
        body = resp.json()
        for key in PUBLIC_FORBIDDEN_KEYS:
            self.assertNotIn(key, body)
        lowered = resp.text.lower()
        for term in VENDOR_TERMS + INTERNAL_METADATA_TERMS:
            self.assertNotIn(term, lowered)
        self.assertNotIn("###", body["answer"])
        self.assertNotIn("###", json.dumps(body["structured_answer"], ensure_ascii=False))


class StructuredAnswerSurvivesModelFailureTests(_Harness):
    def test_a_fast_model_success(self):
        resp = self._post(D2_FAST_REQUEST)
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assert_canonical_structured(body, summary_source="model_summary")
        self.assertFalse(body.get("deterministic_fallback_answer_used"))
        self.assert_public(resp)

    def test_b_all_fast_models_fail_retryably(self):
        resp = self._post(D2_FAST_REQUEST, raise_for=_rate_limited)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertGreaterEqual(len(self.calls), 1)
        body = resp.json()
        self.assert_canonical_structured(body, summary_source="deterministic")
        self.assertTrue(body["deterministic_fallback_answer_used"])
        self.assert_public(resp)

    def test_c_all_fast_models_fail_non_retryably(self):
        # Invalid / unavailable Fast model ids: each is skipped, the chain ends
        # with retryable_provider_error=False — the branch that raised 503.
        resp = self._post(D2_FAST_REQUEST, raise_for=_model_not_found)
        self.assertEqual(resp.status_code, 200, resp.text)
        fast_chain = pb.resolve_answer_mode_models("fast")["candidates"] if hasattr(pb, "resolve_answer_mode_models") else None
        if fast_chain:
            self.assertEqual(self.calls, list(fast_chain))
        body = resp.json()
        self.assert_canonical_structured(body, summary_source="deterministic")
        self.assertEqual(body["fallback_answer_kind"], "structured_document_checklist")
        self.assert_public(resp)

    def test_c_mixed_retryable_then_non_retryable_chain(self):
        # First candidate rate-limited, the rest unavailable: the chain reports
        # the LAST error (non-retryable), which also used to become a 503.
        seen: List[str] = []

        def mixed(model):
            seen.append(model)
            return _rate_limited(model) if len(seen) == 1 else _model_not_found(model)

        resp = self._post(D2_FAST_REQUEST, raise_for=mixed)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assert_canonical_structured(resp.json(), summary_source="deterministic")

    def test_c_account_wide_bad_request(self):
        resp = self._post(D2_FAST_REQUEST, raise_for=_bad_request)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(len(self.calls), 1)  # fatal error: chain stops early
        self.assert_canonical_structured(resp.json(), summary_source="deterministic")
        self.assert_public(resp)

    def test_d_provider_not_configured(self):
        # The structured answer is built from grounding before any provider is
        # consulted, so it is fully answerable without one.
        resp = self._post(D2_FAST_REQUEST, api_key=None)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(self.calls, [])
        self.assert_canonical_structured(resp.json(), summary_source="deterministic")
        self.assert_public(resp)


class StreamPathTests(_Harness):
    """The SSE path (unused by ai.html, which forces stream:false) must also
    deliver the canonical checklist when every model fails non-retryably."""

    def _stream(self, raise_for):
        async def fake_stream(prompt, model=None, max_tokens=None):
            self.calls.append(model)
            raise raise_for(model)
            yield ""  # pragma: no cover - makes this an async generator

        with patch.object(pb, "OPENROUTER_API_KEY", "sk-test-sentinel"), \
                patch.object(pb, "_stream_openrouter_text", fake_stream):
            return TestClient(pb.app).post("/api/ask", json={**D2_FAST_REQUEST, "stream": True})

    def _events(self, text):
        out = []
        for frame in text.split("\n\n"):
            ev = next((ln[6:].strip() for ln in frame.splitlines() if ln.startswith("event:")), None)
            data = "".join(ln[5:].strip() for ln in frame.splitlines() if ln.startswith("data:"))
            if ev and data:
                out.append((ev, json.loads(data)))
        return out

    def test_non_retryable_stream_failure_ends_in_structured_fallback(self):
        resp = self._stream(_model_not_found)
        self.assertEqual(resp.status_code, 200)
        events = self._events(resp.text)
        kinds = [e for e, _ in events]
        self.assertEqual(kinds[0], "meta")
        self.assertEqual(kinds[-1], "fallback")
        meta = events[0][1]
        docs = meta["structured_answer"]["required_documents"]
        self.assertEqual([d["label"] for d in docs["common"]], ["신청서", "여권", "외국인등록증", "수수료"])
        fallback = events[-1][1]
        for doc in ("신청서", "여권", "외국인등록증", "수수료"):
            self.assertIn(doc, fallback["answer"])
        lowered = resp.text.lower()
        for term in VENDOR_TERMS:
            self.assertNotIn(term, lowered)


class ModelDependentQuestionsKeepFailureSemanticsTests(_Harness):
    def test_e_non_retryable_provider_error_still_503(self):
        resp = self._post({"question": MODEL_DEPENDENT_QUESTION, "answer_mode": "fast", "stream": False},
                          raise_for=_model_not_found)
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertFalse(detail.get("structured_answer"))
        for term in VENDOR_TERMS:
            self.assertNotIn(term, resp.text.lower())

    def test_e_no_provider_configured_still_503(self):
        resp = self._post({"question": MODEL_DEPENDENT_QUESTION, "stream": False}, api_key=None)
        self.assertEqual(resp.status_code, 503, resp.text)
        self.assertEqual(resp.json()["detail"]["error"], "no_llm_provider_configured")


class DiagnosticContractTests(_Harness):
    def test_success_keeps_routing_observable(self):
        resp = self._post(D2_FAST_REQUEST, diagnostics=True)
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["llm_provider"], "openrouter")
        self.assertTrue(body["final_model"])
        self.assertTrue(body["attempted_models"])
        self.assertIsNone(body.get("summary_generation_status"))

    def test_failure_is_discoverable_without_becoming_an_error(self):
        resp = self._post(D2_FAST_REQUEST, raise_for=_model_not_found, diagnostics=True)
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["summary_generation_status"], "failed")
        self.assertTrue(body["summary_generation_failed"])
        self.assertEqual(body["provider_error_type"], "model_not_found")
        self.assertFalse(body["retryable_provider_error"])
        self.assertTrue(body["attempted_models"])
        self.assertIsNone(body["final_model"])
        self.assertEqual(body["fallback_answer_reason"], "structured_answer_summary_provider_error")
        self.assertEqual(body["structured_answer"]["short_answer_source"], "deterministic")

    def test_failure_is_logged_server_side(self):
        with self.assertLogs("paradiso.backend", level="INFO") as logs:
            resp = self._post(D2_FAST_REQUEST, raise_for=_model_not_found)
        self.assertEqual(resp.status_code, 200)
        record = next(line for line in logs.output if "ask_routing" in line)
        data = json.loads(record.split("ask_routing ", 1)[1])
        self.assertEqual(data["status_code"], 200)
        self.assertEqual(data["summary_generation_status"], "failed")
        self.assertEqual(data["provider_error_type"], "model_not_found")
        self.assertTrue(data["structured_answer"])


if __name__ == "__main__":
    unittest.main()
