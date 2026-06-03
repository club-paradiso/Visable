"""Deterministic coverage for OpenRouter model-candidate fallback + provider
error classification + provider error UX (2026-05).

Backend tests use the FastAPI TestClient with OPENROUTER_API_KEY patched to a
non-secret sentinel and `_call_openrouter` patched to simulate per-model
provider failures — no real network calls, no secrets. Frontend/i18n checks are
static against index.html; smoke checks are static against the harness source.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
INDEX = REPO_ROOT / "index.html"
CHECK_I18N = REPO_ROOT / "scripts" / "check_i18n.js"
SMOKE = REPO_ROOT / "scripts" / "smoke_ai_live_quality.py"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

CANDS = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
    "moonshotai/kimi-k2.6:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]
H1_Q = "H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?"


def _pb():
    import paradiso_backend
    return paradiso_backend


def _client(pb):
    from fastapi.testclient import TestClient  # type: ignore
    pb._reset_visas_cache_for_tests()
    pb._reset_grounding_cache_for_tests()
    if hasattr(pb, "_reset_openrouter_model_cooldowns_for_tests"):
        pb._reset_openrouter_model_cooldowns_for_tests()
    return TestClient(pb.app)


def _fake_openrouter(behaviors):
    """Return (fake_call, calls). behaviors: model -> "ok" | (status, message)."""
    calls = []

    async def fake(prompt, model=None):
        calls.append(model)
        b = behaviors.get(model, "ok")
        if b == "ok":
            return "ANSWER from %s" % model
        status, message = b
        raise HTTPException(
            status_code=502,
            detail={"error": "openrouter_upstream_error", "status": status, "message": message},
        )

    return fake, calls


def _node_available():
    try:
        subprocess.run(["node", "--version"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Candidate list parsing + policy
# ---------------------------------------------------------------------------

class CandidateListParsingTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("OPENROUTER_MODEL_CANDIDATES", None)

    def tearDown(self):
        os.environ.pop("OPENROUTER_MODEL_CANDIDATES", None)

    def test_parses_comma_separated_list_primary_first(self):
        pb = _pb()
        os.environ["OPENROUTER_MODEL_CANDIDATES"] = "a/b:free, c/d:free , e/f:free"
        with patch.object(pb, "OPENROUTER_MODEL", "a/b:free"):
            cands = pb._resolve_openrouter_candidates()
        self.assertEqual(cands[0], "a/b:free")
        self.assertEqual(cands, ["a/b:free", "c/d:free", "e/f:free"])

    def test_dedupes_preserving_order(self):
        pb = _pb()
        os.environ["OPENROUTER_MODEL_CANDIDATES"] = "a/b:free,c/d:free,a/b:free,c/d:free"
        with patch.object(pb, "OPENROUTER_MODEL", "a/b:free"):
            cands = pb._resolve_openrouter_candidates()
        self.assertEqual(cands, ["a/b:free", "c/d:free"])

    def test_primary_model_is_first_even_if_not_in_candidates(self):
        pb = _pb()
        os.environ["OPENROUTER_MODEL_CANDIDATES"] = "c/d:free,e/f:free"
        with patch.object(pb, "OPENROUTER_MODEL", "google/gemma-4-31b-it:free"):
            cands = pb._resolve_openrouter_candidates()
        self.assertEqual(cands[0], "google/gemma-4-31b-it:free")
        self.assertIn("c/d:free", cands)

    def test_default_candidate_list_matches_approved_policy(self):
        pb = _pb()
        os.environ.pop("OPENROUTER_MODEL_CANDIDATES", None)
        with patch.object(pb, "OPENROUTER_MODEL", CANDS[0]):
            cands = pb._resolve_openrouter_candidates()
        self.assertEqual(cands, CANDS)

    def test_default_candidate_list_excludes_random_routing(self):
        pb = _pb()
        with patch.object(pb, "OPENROUTER_MODEL", CANDS[0]):
            cands = pb._resolve_openrouter_candidates()
        for c in cands:
            self.assertNotIn("auto", c.lower())
        self.assertEqual(pb._validate_model_candidates(cands), [])


# ---------------------------------------------------------------------------
# Provider error classification
# ---------------------------------------------------------------------------

class ProviderErrorClassifierTests(unittest.TestCase):
    def test_observed_503_no_healthy_upstream_is_retryable(self):
        pb = _pb()
        etype, retryable = pb._classify_openrouter_error(503, "No healthy upstream")
        self.assertEqual(etype, "upstream_unavailable")
        self.assertTrue(retryable)

    def test_google_ai_studio_429_is_retryable_rate_limit(self):
        pb = _pb()
        etype, retryable = pb._classify_openrouter_error(429, "Google AI Studio rate limit (429)")
        self.assertEqual(etype, "rate_limited")
        self.assertTrue(retryable)

    def test_invalid_api_key_not_retryable(self):
        pb = _pb()
        etype, retryable = pb._classify_openrouter_error(401, "Invalid API key")
        self.assertEqual(etype, "invalid_provider_config")
        self.assertFalse(retryable)

    def test_bad_request_not_retryable(self):
        pb = _pb()
        etype, retryable = pb._classify_openrouter_error(400, "Bad request: invalid payload")
        self.assertEqual(etype, "invalid_request")
        self.assertFalse(retryable)

    def test_model_not_found_not_retryable(self):
        pb = _pb()
        etype, retryable = pb._classify_openrouter_error(404, "Model not found")
        self.assertFalse(retryable)

    def test_safety_rejection_not_retryable(self):
        pb = _pb()
        etype, retryable = pb._classify_openrouter_error(451, "flagged by content policy")
        self.assertEqual(etype, "policy_or_safety_rejection")
        self.assertFalse(retryable)


# ---------------------------------------------------------------------------
# Candidate fallback behavior via /api/ask
# ---------------------------------------------------------------------------

class CandidateFallbackBehaviorTests(unittest.TestCase):
    def setUp(self):
        for k in ("GROQ_API_KEY", "OPENROUTER_MODEL_CANDIDATES"):
            os.environ.pop(k, None)
        os.environ["LAW_GROUNDING_MODE"] = "audit"

    def tearDown(self):
        os.environ.pop("LAW_GROUNDING_MODE", None)

    def _ask(self, pb, behaviors, question="D-2 연장 서류", **extra):
        fake, calls = _fake_openrouter(behaviors)
        with patch.object(pb, "OPENROUTER_API_KEY", "or-sentinel-key"), \
                patch.object(pb, "GROQ_API_KEY", None), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", False), \
                patch.object(pb, "OPENROUTER_MODEL", CANDS[0]), \
                patch.object(pb, "OPENROUTER_MODEL_CANDIDATES", list(CANDS)), \
                patch.object(pb, "_call_openrouter", fake):
            client = _client(pb)
            payload = {"question": question}
            payload.update(extra)
            resp = client.post("/api/ask", json=payload)
        return resp, calls

    def test_primary_qwen_used_first(self):
        pb = _pb()
        resp, calls = self._ask(pb, {})  # all ok
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["final_model"], CANDS[0])
        self.assertFalse(body["model_fallback_used"])
        self.assertEqual(calls, [CANDS[0]])

    def test_qwen_429_triggers_gemma(self):
        pb = _pb()
        resp, calls = self._ask(pb, {CANDS[0]: (429, "rate limit")})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["final_model"], CANDS[1])
        self.assertTrue(body["model_fallback_used"])
        self.assertEqual(calls, [CANDS[0], CANDS[1]])
        self.assertEqual(body["upstream_statuses"], [429])

    def test_gemma_failure_triggers_kimi(self):
        pb = _pb()
        resp, calls = self._ask(pb, {CANDS[0]: (429, "rate limit"), CANDS[1]: (503, "No healthy upstream")})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["final_model"], CANDS[2])
        self.assertEqual(calls, [CANDS[0], CANDS[1], CANDS[2]])

    def test_kimi_failure_triggers_llama(self):
        pb = _pb()
        resp, calls = self._ask(pb, {
            CANDS[0]: (429, "rate limit"),
            CANDS[1]: (503, "No healthy upstream"),
            CANDS[2]: (503, "overloaded"),
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["final_model"], CANDS[3])
        self.assertEqual(calls, CANDS)

    def test_all_candidates_fail_returns_safe_provider_unavailable(self):
        pb = _pb()
        resp, calls = self._ask(pb, {c: (503, "No healthy upstream") for c in CANDS})
        self.assertEqual(resp.status_code, 200, resp.text)
        detail = resp.json()
        self.assertTrue(detail["deterministic_fallback_answer_used"])
        self.assertEqual(detail["fallback_answer_kind"], "source_aware_preparation_note")
        self.assertTrue(detail["all_candidates_failed"])
        self.assertTrue(detail["retryable_provider_error"])
        self.assertEqual(detail["attempted_models"], CANDS)
        self.assertFalse(detail["provider_family_fallback_used"])
        self.assertIn("copy_safe_answer", detail)
        # No raw provider JSON keys leak through.
        self.assertNotIn("choices", resp.text)

    def test_non_retryable_invalid_key_does_not_retry_blindly(self):
        pb = _pb()
        resp, calls = self._ask(pb, {c: (401, "Invalid API key") for c in CANDS})
        self.assertEqual(resp.status_code, 200, resp.text)
        detail = resp.json()
        self.assertEqual(detail["provider_error_type"], "invalid_provider_config")
        self.assertEqual(calls, [CANDS[0]], "must stop after first non-retryable error")
        self.assertFalse(detail["all_candidates_failed"])

    def test_bad_request_does_not_retry_blindly(self):
        pb = _pb()
        resp, calls = self._ask(pb, {c: (400, "Bad request") for c in CANDS})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(calls, [CANDS[0]])
        self.assertEqual(resp.json()["provider_error_type"], "invalid_request")

    def test_grounding_metadata_survives_model_retries(self):
        pb = _pb()
        resp, calls = self._ask(pb, {CANDS[0]: (429, "rate limit")}, question=H1_Q, visa_code="H-1")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["final_model"], CANDS[1])
        self.assertTrue(body["law_grounding_attempted"])
        self.assertTrue(body["manual_to_law_fallback_used"])
        self.assertEqual(body["manual_grounding_status"], "absent")

    def test_no_api_key_appears_in_response_metadata(self):
        pb = _pb()
        resp, calls = self._ask(pb, {c: (503, "No healthy upstream") for c in CANDS})
        self.assertNotIn("or-sentinel-key", resp.text)


class ProviderFamilyFallbackTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("OPENROUTER_MODEL_CANDIDATES", None)

    def _ask_all_fail(self, pb, allow_groq, groq_key="groq-key"):
        fake, _ = _fake_openrouter({c: (503, "No healthy upstream") for c in CANDS})

        async def groq_ok(prompt, model=None):
            return "GROQ ANSWER"

        with patch.object(pb, "OPENROUTER_API_KEY", "or-key"), \
                patch.object(pb, "GROQ_API_KEY", groq_key), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", allow_groq), \
                patch.object(pb, "OPENROUTER_MODEL", CANDS[0]), \
                patch.object(pb, "OPENROUTER_MODEL_CANDIDATES", list(CANDS)), \
                patch.object(pb, "_call_openrouter", fake), \
                patch.object(pb, "_call_groq", groq_ok):
            client = _client(pb)
            return client.post("/api/ask", json={"question": "D-2 연장 서류"})

    def test_provider_family_fallback_not_used_when_disabled(self):
        pb = _pb()
        resp = self._ask_all_fail(pb, allow_groq=False)
        self.assertEqual(resp.status_code, 200, resp.text)
        detail = resp.json()
        self.assertFalse(detail["provider_family_fallback_used"])
        self.assertTrue(detail["deterministic_fallback_answer_used"])

    def test_provider_family_fallback_explicit_when_enabled(self):
        pb = _pb()
        resp = self._ask_all_fail(pb, allow_groq=True)
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["provider"], "groq")
        self.assertTrue(body["provider_family_fallback_used"])
        self.assertEqual(body["answer"], "GROQ ANSWER")
        # Candidate attempt metadata is preserved for audit.
        self.assertEqual(body["attempted_models"], CANDS)

class CooldownAndFallbackBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pb = _pb()
        self.pb._reset_openrouter_model_cooldowns_for_tests()

    async def asyncTearDown(self):
        self.pb._reset_openrouter_model_cooldowns_for_tests()

    async def test_429_marks_model_cooling_down(self):
        fake, calls = _fake_openrouter({CANDS[0]: (429, "rate limit"), CANDS[1]: "ok"})
        with patch.object(self.pb, "OPENROUTER_MODEL", CANDS[0]), \
                patch.object(self.pb, "OPENROUTER_MODEL_CANDIDATES", list(CANDS)), \
                patch.object(self.pb, "OPENROUTER_MODEL_COOLDOWN_SECONDS", 300), \
                patch.object(self.pb, "_call_openrouter", fake):
            result = await self.pb._openrouter_complete_with_candidates("x")
        self.assertEqual(calls, [CANDS[0], CANDS[1]])
        self.assertIn(CANDS[0], result["cooling_down_models"])

    async def test_503_marks_model_cooling_down_and_skips_next_request(self):
        fake, calls = _fake_openrouter({CANDS[0]: (503, "No healthy upstream"), CANDS[1]: "ok"})
        with patch.object(self.pb, "OPENROUTER_MODEL", CANDS[0]), \
                patch.object(self.pb, "OPENROUTER_MODEL_CANDIDATES", list(CANDS)), \
                patch.object(self.pb, "OPENROUTER_MODEL_COOLDOWN_SECONDS", 300), \
                patch.object(self.pb, "_call_openrouter", fake):
            first = await self.pb._openrouter_complete_with_candidates("x")
            second = await self.pb._openrouter_complete_with_candidates("x")
        self.assertIn(CANDS[0], first["cooling_down_models"])
        self.assertEqual(second["skipped_models_due_to_cooldown"], [CANDS[0]])
        self.assertEqual(calls, [CANDS[0], CANDS[1], CANDS[1]])

    async def test_all_cooling_down_skips_to_deterministic_path_metadata(self):
        fake, calls = _fake_openrouter({c: (503, "No healthy upstream") for c in CANDS})
        with patch.object(self.pb, "OPENROUTER_MODEL", CANDS[0]), \
                patch.object(self.pb, "OPENROUTER_MODEL_CANDIDATES", list(CANDS)), \
                patch.object(self.pb, "OPENROUTER_MODEL_COOLDOWN_SECONDS", 300), \
                patch.object(self.pb, "_call_openrouter", fake):
            await self.pb._openrouter_complete_with_candidates("x")
            result = await self.pb._openrouter_complete_with_candidates("x")
        self.assertEqual(calls, CANDS)
        self.assertEqual(result["attempted_models"], [])
        self.assertEqual(result["skipped_models_due_to_cooldown"], CANDS)
        self.assertEqual(result["provider_error_type"], "all_candidates_cooling_down")


class DeterministicFallbackAndOllamaTests(unittest.TestCase):
    def _ask(self, *, enable_ollama=False, ollama=None, question="Can I take summer semester course in Korean universities even though I have a H-1 visa?", lang="en"):
        pb = _pb()
        fake, calls = _fake_openrouter({c: (503, '{"error":"No healthy upstream"}') for c in CANDS})
        patches = [
            patch.object(pb, "OPENROUTER_API_KEY", "or-key"),
            patch.object(pb, "GROQ_API_KEY", None),
            patch.object(pb, "ALLOW_GROQ_FALLBACK", False),
            patch.object(pb, "OPENROUTER_MODEL", CANDS[0]),
            patch.object(pb, "OPENROUTER_MODEL_CANDIDATES", list(CANDS)),
            patch.object(pb, "OPENROUTER_MODEL_COOLDOWN_SECONDS", 0),
            patch.object(pb, "ENABLE_OLLAMA_FALLBACK", enable_ollama),
            patch.object(pb, "OLLAMA_MODEL", "qwen3:8b"),
            patch.object(pb, "_call_openrouter", fake),
        ]
        if ollama is not None:
            patches.append(patch.object(pb, "_call_ollama", ollama))
        exits = [p.__enter__() for p in patches]
        try:
            client = _client(pb)
            resp = client.post("/api/ask", json={"question": question, "lang": lang})
        finally:
            for p in reversed(patches):
                p.__exit__(None, None, None)
        return resp, calls

    def test_openrouter_all_fail_ollama_disabled_returns_fallback_answer(self):
        resp, calls = self._ask()
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertTrue(body["deterministic_fallback_answer_used"])
        self.assertTrue(body["llm_unavailable"])
        self.assertEqual(body["visa_code_detected"], "H-1")
        self.assertEqual(body["question_type_detected"], "activity_on_status")
        self.assertIn("credit-bearing", body["fallback_answer"])
        self.assertEqual(body["copy_safe_answer"], body["fallback_answer"])
        self.assertNotIn("No healthy upstream", body["fallback_answer"])
        self.assertNotIn("documents", body["fallback_answer"].lower())
        self.assertNotIn("you may", body["fallback_answer"].lower())
        self.assertEqual(calls, CANDS)

    def test_h1_korean_all_fail_preserves_status_and_confirmation_questions(self):
        resp, _ = self._ask(question=H1_Q, lang="ko")
        body = resp.json()
        self.assertEqual(body["visa_code_detected"], "H-1")
        self.assertTrue(body["official_confirmation_questions"])
        self.assertIn("AI 모델이 일시적으로 응답하지", body["answer"])

    def test_ollama_enabled_mocked_success_returns_ollama_answer(self):
        async def ollama_ok(prompt, model=None):
            return "OLLAMA ANSWER"
        resp, _ = self._ask(enable_ollama=True, ollama=ollama_ok)
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["provider"], "ollama")
        self.assertTrue(body["ollama_fallback_used"])
        self.assertFalse(body["deterministic_fallback_answer_used"])
        self.assertEqual(body["answer"], "OLLAMA ANSWER")
        self.assertEqual(body["copy_safe_answer"], "OLLAMA ANSWER")

    def test_ollama_enabled_timeout_returns_deterministic_fallback(self):
        async def ollama_timeout(prompt, model=None):
            raise HTTPException(status_code=503, detail={"error": "ollama_timeout"})
        resp, _ = self._ask(enable_ollama=True, ollama=ollama_timeout)
        body = resp.json()
        self.assertTrue(body["deterministic_fallback_answer_used"])
        self.assertEqual(body["ollama_error_type"], "ollama_timeout")
        self.assertNotIn("or-key", resp.text)

    def test_law_manual_metadata_survives_fallback(self):
        resp, _ = self._ask(question=H1_Q, lang="ko")
        body = resp.json()
        self.assertTrue(body["law_grounding_attempted"])
        self.assertIn(body["manual_grounding_status"], {"absent", "present"})


# ---------------------------------------------------------------------------
# /health candidate exposure
# ---------------------------------------------------------------------------

class HealthCandidateExposureTests(unittest.TestCase):
    def test_health_exposes_candidates_and_posture_without_secrets(self):
        os.environ["OPENROUTER_API_KEY"] = "or-health-secret"
        try:
            pb = _pb()
            client = _client(pb)
            data = client.get("/health").json()
            llm = data["llm"]
            self.assertIn("model_candidates", llm)
            self.assertIn("primary_model", llm)
            self.assertIn("provider_family_fallback_allowed", llm)
            self.assertIn("candidate_warnings", llm)
            self.assertIsInstance(llm["model_candidates"], list)
            self.assertNotIn("or-health-secret", client.get("/health").text)
        finally:
            os.environ.pop("OPENROUTER_API_KEY", None)

    def test_health_flags_random_routing_and_family_fallback(self):
        pb = _pb()
        with patch.object(pb, "OPENROUTER_MODEL_CANDIDATES", ["openrouter/auto"]), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", True):
            client = _client(pb)
            llm = client.get("/health").json()["llm"]
        self.assertIn("MODEL_CANDIDATES_RANDOM_ROUTING", llm["candidate_warnings"])
        self.assertIn("PROVIDER_FAMILY_FALLBACK_ENABLED", llm["candidate_warnings"])


# ---------------------------------------------------------------------------
# Frontend / i18n provider error UX
# ---------------------------------------------------------------------------

class ProviderErrorUxFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8")

    def test_provider_error_helper_does_not_render_raw_json(self):
        fn = self.html.split("function buildProviderErrorHtml", 1)[1].split("\nfunction ", 1)[0]
        # Friendly copy + collapsed disclosure; sanitized hints only.
        self.assertIn("tx('aiProviderBusy')", fn)
        self.assertIn("tx('aiAllCandidatesFailed')", fn)
        self.assertIn("tx('aiShowTechnicalDetails')", fn)
        self.assertIn("<details", fn)
        # Must NOT dump the whole response body / raw provider JSON.
        self.assertNotIn("JSON.stringify(detail)", fn)
        self.assertNotIn("JSON.stringify(body)", fn)

    def test_submit_uses_provider_error_helper_for_503(self):
        submit = self.html.split("async function submitAiAnalysis", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("buildProviderErrorHtml(detail)", submit)
        self.assertIn("response.status === 503", submit)
        # Subtle fallback note on success.
        self.assertIn("tx('aiFallbackSucceeded')", submit)
        self.assertIn("model_fallback_used", submit)

    def test_provider_busy_message_in_four_languages(self):
        self.assertIn("aiProviderBusy: 'AI 모델이 일시적으로 혼잡합니다.'", self.html)
        self.assertIn("aiProviderBusy: 'The AI model is temporarily busy.'", self.html)
        self.assertIn("aiProviderBusy: 'AI 模型暂时繁忙。'", self.html)
        self.assertIn("aiProviderBusy: 'AI 模型暫時繁忙。'", self.html)

    def test_all_candidates_failed_message_in_four_languages(self):
        self.assertIn("aiAllCandidatesFailed: '다른 모델 후보로 재시도했지만 현재 응답을 생성하지 못했습니다. 잠시 후 다시 시도하세요.'", self.html)
        self.assertIn("aiAllCandidatesFailed: 'Paradiso retried the configured model candidates but could not generate a response. Please try again shortly.'", self.html)
        self.assertEqual(self.html.count("aiAllCandidatesFailed:"), 4)

    def test_fallback_success_and_response_model_labels_in_four_languages(self):
        self.assertIn("aiFallbackSucceeded: '다른 모델 후보로 재시도하여 응답했습니다.'", self.html)
        self.assertIn("aiFallbackSucceeded: 'Paradiso retried with another configured model candidate and generated a response.'", self.html)
        self.assertEqual(self.html.count("aiFallbackSucceeded:"), 4)
        self.assertIn("aiResponseModel: '응답 모델'", self.html)
        self.assertIn("aiResponseModel: 'Response model'", self.html)
        self.assertEqual(self.html.count("aiResponseModel:"), 4)
        self.assertEqual(self.html.count("aiShowTechnicalDetails:"), 4)

    def test_model_badge_uses_localized_response_model_label(self):
        fn = self.html.split("function buildModelBadgeHtml", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("tx('aiResponseModel')", fn)
        self.assertNotIn("응답 모델:", fn)

    @unittest.skipUnless(_node_available(), "node not available")
    def test_i18n_leak_guard_still_passes(self):
        rc = subprocess.call(["node", str(CHECK_I18N)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertEqual(rc, 0)


# ---------------------------------------------------------------------------
# Smoke harness
# ---------------------------------------------------------------------------

class SmokeCandidateReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SMOKE.read_text(encoding="utf-8")

    def test_smoke_reports_candidate_list_and_fallback_fields(self):
        self.assertIn("model_candidates", self.src)
        self.assertIn("attempted_models", self.src)
        self.assertIn("final_model", self.src)
        self.assertIn("provider_error_type", self.src)
        self.assertIn("model_fallback_used", self.src)
        self.assertIn("provider_family_fallback_used", self.src)

    def test_smoke_supports_no_provider_skip(self):
        self.assertIn("no_llm_provider_configured", self.src)
        self.assertIn("--require-live", self.src)
        self.assertIn("live answer skipped", self.src)

    def test_smoke_never_prints_secrets(self):
        self.assertNotIn("OPENROUTER_API_KEY", self.src)
        self.assertNotIn("GROQ_API_KEY", self.src)
        self.assertIn("never prints api keys", self.src.lower())

    def test_smoke_no_provider_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, str(SMOKE)],
            env={**os.environ, "BACKEND_URL": "http://127.0.0.1:59997"},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
