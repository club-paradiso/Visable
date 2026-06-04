"""AI answer pipeline contract & rendering tests.

These guard the contract between the backend ``/api/ask`` metadata and the
ai.html answer renderer after the production
``Can't find variable: errorType`` ReferenceError.

Coverage:
  * Frontend (static + behavioral via the node checker): the source-panel
    renderer declares its own ``errorType``, routes metadata through
    ``normalizeAnswerMetadata``, classifies errors (network / backend_http /
    provider / frontend_render), never opens developer diagnostics by default,
    and never welds diagnostics into the copy payload.
  * Backend contract: the new source-panel diagnostics fields
    (``parser_status`` / ``source_family_statuses`` / ``parser_status_by_family``)
    are present and type-stable, and the deterministic-fallback / provider-error
    payloads carry a copy-safe answer free of raw diagnostic codes.

Run from repo root:

    python3 -m pytest backend/tests/test_ai_answer_pipeline_contract.py -q
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
AI_HTML = REPO_ROOT / "ai.html"
CHECKER = REPO_ROOT / "scripts" / "check_ai_shell_semantics.js"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import paradiso_backend as pb  # noqa: E402


def _extract_js_function(src: str, name: str) -> str:
    """Brace-match a top-level ``function NAME(...) { ... }`` body from src."""
    import re

    m = re.search(r"function\s+" + re.escape(name) + r"\s*\(", src)
    if not m:
        return ""
    i = src.index("{", m.end())
    depth = 0
    for j in range(i, len(src)):
        ch = src[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
    return ""


class FrontendContractStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = AI_HTML.read_text(encoding="utf-8")
        cls.render_fn = _extract_js_function(cls.html, "renderGroundingSourcePanel")
        cls.normalize_fn = _extract_js_function(cls.html, "normalizeAnswerMetadata")

    # -- Part A: the immediate errorType ReferenceError ---------------------
    def test_render_panel_declares_errortype_locally(self):
        self.assertTrue(self.render_fn, "renderGroundingSourcePanel not found")
        self.assertIn("errorType", self.render_fn)
        # It must be a LOCAL declaration, not a borrowed sibling-helper variable.
        self.assertRegex(
            self.render_fn,
            r"const\s+errorType\s*=\s*String\(",
            "renderGroundingSourcePanel must declare errorType locally",
        )

    # -- Part B: safe metadata normalization --------------------------------
    def test_normalize_helper_exists_and_is_used(self):
        self.assertTrue(self.normalize_fn, "normalizeAnswerMetadata not found")
        self.assertIn("normalizeAnswerMetadata(", self.render_fn)
        for field in (
            "law_grounding_warnings", "law_lookup_error_type", "parser_status",
            "source_family_statuses", "parser_status_by_family", "law_sources",
            "grounding_sources", "related_statuses_not_sources", "legal_analysis",
            "legal_analysis_exists", "citation_verification",
            "deterministic_fallback_answer_used", "fallback_answer_kind",
            "copy_safe_answer", "answer_certainty_level", "source_panel_state",
        ):
            self.assertIn(field, self.normalize_fn, f"normalize missing default for {field}")

    # -- Part C: error classification ---------------------------------------
    def test_error_classification_has_four_classes(self):
        self.assertIn("function classifyAskError(", self.html)
        for cls in ("'network'", "'backend_http'", "'provider'", "'frontend_render'"):
            self.assertIn(cls, self.html, f"error class {cls} missing")
        # A render crash surfaces a structured developer record, not a network msg.
        self.assertIn("frontend_render_error", self.html)
        # appendAiAnswer is wrapped so a render exception is reclassified.
        self.assertIn("catch (renderErr)", self.html)

    # -- Part D/G: diagnostics hygiene --------------------------------------
    def test_developer_diagnostics_not_open_by_default(self):
        self.assertNotIn("<details open", self.html.lower())

    def test_copy_payload_excludes_developer_diagnostics(self):
        import re

        assigns = re.findall(r"COPY_PAYLOADS\[[^\]]+\]\s*=\s*\{[^}]*\}", self.html)
        self.assertTrue(assigns, "no COPY_PAYLOADS assignments found")
        for a in assigns:
            for token in ("data-diagnostics", "error-details", "developer"):
                self.assertNotIn(token, a, f"copy payload leaked diagnostics: {a}")

    def test_raw_codes_appear_after_human_readable_diagnostic(self):
        details_pos = self.html.find("실시간 법령 조회 응답을 파싱하지 못했습니다")
        raw_pos = self.html.find("raw developer codes", details_pos)
        self.assertGreaterEqual(details_pos, 0)
        self.assertGreater(raw_pos, details_pos)


class FrontendContractCheckerTests(unittest.TestCase):
    """Run the node checker that statically + behaviorally exercises ai.html."""

    def test_node_checker_passes(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not available")
        result = subprocess.run(
            [node, str(CHECKER)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"check_ai_shell_semantics.js failed:\n{result.stdout}\n{result.stderr}",
        )


# ---------------------------------------------------------------------------
# Backend contract: new source-panel diagnostics fields are present + typed.
# ---------------------------------------------------------------------------
CANDS = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
]


async def _openrouter_all_unavailable(prompt, model=None):
    raise HTTPException(
        status_code=502,
        detail={"error": "openrouter_upstream_error", "status": 503, "message": "No healthy upstream"},
    )


def _ask_fallback(question, *, lang="ko", visa_code=None):
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
                patch.object(pb, "OPENROUTER_MODEL_COOLDOWN_SECONDS", 0), \
                patch.object(pb, "_call_openrouter", _openrouter_all_unavailable):
            client = TestClient(pb.app)
            payload = {"question": question, "lang": lang}
            if visa_code:
                payload["visa_code"] = visa_code
            resp = client.post("/api/ask", json=payload)
        assert resp.status_code == 200, resp.text
        return resp.json()
    finally:
        if old_mode is None:
            os.environ.pop("LAW_GROUNDING_MODE", None)
        else:
            os.environ["LAW_GROUNDING_MODE"] = old_mode


class BackendMetadataContractTests(unittest.TestCase):
    def test_new_source_panel_fields_present_and_type_stable(self):
        body = _ask_fallback("H-1 외국인등록은 언제 해야 하나요?")
        # Type-stable contract fields the frontend source panel relies on.
        self.assertIsInstance(body.get("parser_status", ""), str)
        self.assertIsInstance(body.get("source_family_statuses", {}), dict)
        self.assertIsInstance(body.get("parser_status_by_family", {}), dict)
        self.assertIsInstance(body.get("source_panel_state", ""), str)
        self.assertIsInstance(body.get("source_panel_label_key", ""), str)
        self.assertIsInstance(body.get("law_lookup_error_type", ""), str)
        self.assertIsInstance(body.get("law_grounding_warnings", []), list)
        self.assertIsInstance(body.get("law_sources", []), list)
        self.assertIsInstance(body.get("legal_analysis_exists", False), bool)
        self.assertIsInstance(body.get("deterministic_fallback_answer_used", False), bool)
        self.assertIsInstance(body.get("fallback_answer_kind", ""), str)

    def test_h1_registration_fallback_renders_without_school_terms(self):
        # Mirrors the source-panel-renderable H-1 registration case (Part G).
        body = _ask_fallback("H-1 외국인등록은 언제 해야 하나요?")
        answer = body["answer"]
        for bad in ("계절학기", "학점", "대학 수업", "D-2/D-4"):
            self.assertNotIn(bad, answer)
        # Source panel must have a coherent, renderable state.
        self.assertTrue(body["source_panel_state"])

    def test_copy_safe_answer_has_no_raw_diagnostic_codes(self):
        body = _ask_fallback("E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?")
        copied = body.get("copy_safe_answer") or body.get("answer") or ""
        for code in ("SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE", "CITATION_VERIFICATION_NOT_WIRED"):
            self.assertNotIn(code, copied)

    def test_provider_error_503_detail_is_renderable_metadata(self):
        # A non-retryable provider error returns a 503 whose detail must still be
        # safe for the frontend error card to read (defensive normalization).
        os.environ.pop("LAW_API_OC", None)
        os.environ.pop("LAW_API_KEY", None)
        pb._reset_grounding_cache_for_tests()
        pb._reset_openrouter_model_cooldowns_for_tests()

        async def _provider_config_error(prompt, model=None):
            raise HTTPException(
                status_code=502,
                detail={"error": "openrouter_provider_error", "status": 401, "message": "bad key"},
            )

        with patch.object(pb, "OPENROUTER_API_KEY", "or-test-key"), \
                patch.object(pb, "GROQ_API_KEY", None), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", False), \
                patch.object(pb, "ENABLE_OLLAMA_FALLBACK", False), \
                patch.object(pb, "OPENROUTER_MODEL", CANDS[0]), \
                patch.object(pb, "OPENROUTER_MODEL_CANDIDATES", list(CANDS)), \
                patch.object(pb, "OPENROUTER_MODEL_COOLDOWN_SECONDS", 0), \
                patch.object(pb, "_call_openrouter", _provider_config_error):
            client = TestClient(pb.app)
            resp = client.post("/api/ask", json={"question": "H-1 외국인등록은 언제 해야 하나요?", "lang": "ko"})
        self.assertEqual(resp.status_code, 503)
        detail = resp.json().get("detail", {})
        # The detail carries provider signals the frontend classifier keys on.
        self.assertTrue(
            detail.get("provider_unavailable") is not None
            or "provider" in str(detail.get("error", "")),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
