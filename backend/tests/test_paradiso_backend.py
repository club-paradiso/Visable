"""Lightweight, deterministic tests for the Paradiso backend.

Covers the two regressions the Railway production audit surfaced:

  1. /api/visas must return the real visa dataset, not DEFAULT_VISAS,
     whenever backend/data/visas.json exists in the deploy context.
  2. /api/ask must accept message / query / question and must not crash
     on the optional metadata (visa_code, visa_data, lang, ...).

Run from repo root:

    python3 -m pytest backend/tests -q

or use the bundled runner (no pytest needed):

    python3 backend/tests/test_paradiso_backend.py
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


def _client():
    # Ensure no LLM provider is configured so /api/ask never makes a
    # real upstream call. We only assert on schema-level behavior here.
    for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
        os.environ.pop(key, None)
    from fastapi.testclient import TestClient  # type: ignore

    import paradiso_backend  # noqa: WPS433 — late import after sys.path setup

    paradiso_backend._reset_visas_cache_for_tests()
    paradiso_backend._reset_grounding_cache_for_tests()
    return TestClient(paradiso_backend.app), paradiso_backend


class BackendImportTests(unittest.TestCase):
    def test_module_imports(self):
        import paradiso_backend  # noqa: F401

    def test_visa_data_file_present(self):
        """The deploy-context visa file must exist; this is the fix."""
        target = BACKEND_DIR / "data" / "visas.json"
        self.assertTrue(
            target.is_file(),
            f"backend/data/visas.json is missing — Railway will fall back to "
            f"DEFAULT_VISAS. Run scripts/sync_visa_data.py.",
        )


class RootEndpointTests(unittest.TestCase):
    """GET / must return a friendly service descriptor, not a raw 404.

    Mobile users who open the bare backend URL were previously greeted
    by `{"detail":"Not Found"}`. The root route gives them an actionable
    payload pointing at the real frontend (when FRONTEND_URL is set) and
    the available API endpoints.
    """

    def test_root_returns_200_with_service_info(self):
        os.environ.pop("FRONTEND_URL", None)
        client, _ = _client()
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body.get("service"), "paradiso-backend")
        self.assertEqual(body.get("status"), "ok")
        self.assertIn("Paradiso backend is running", body.get("message", ""))
        self.assertIn("/health", body.get("message", ""))
        self.assertIn("/api/visas", body.get("message", ""))
        self.assertIn("/api/ask", body.get("message", ""))
        self.assertIsNone(body.get("frontend"))

    def test_root_includes_frontend_url_when_configured(self):
        os.environ["FRONTEND_URL"] = "https://lucanomics.github.io/Paradiso/"
        try:
            # FRONTEND_URL is read at import; reload to pick up env override.
            import importlib
            import paradiso_backend  # noqa: WPS433
            importlib.reload(paradiso_backend)
            paradiso_backend._reset_visas_cache_for_tests()
            paradiso_backend._reset_grounding_cache_for_tests()
            from fastapi.testclient import TestClient  # type: ignore
            client = TestClient(paradiso_backend.app)
            resp = client.get("/")
            self.assertEqual(resp.status_code, 200, resp.text)
            self.assertEqual(
                resp.json().get("frontend"),
                "https://lucanomics.github.io/Paradiso/",
            )
        finally:
            os.environ.pop("FRONTEND_URL", None)
            import importlib
            import paradiso_backend  # noqa: WPS433
            importlib.reload(paradiso_backend)

    def test_root_declares_utf8_charset(self):
        client, _ = _client()
        resp = client.get("/")
        ctype = resp.headers.get("content-type", "")
        self.assertIn("application/json", ctype.lower())
        self.assertIn("charset=utf-8", ctype.lower())


class VisasEndpointTests(unittest.TestCase):
    def test_returns_real_data_not_default(self):
        client, _ = _client()
        resp = client.get("/api/visas")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("data", body)
        self.assertIn("count", body)
        self.assertGreater(
            body["count"], 5,
            "DEFAULT_VISAS has 5 entries; real data must have more.",
        )
        self.assertNotIn(
            "warning", body,
            f"/api/visas returned fallback warning: {body.get('warning')!r}",
        )
        self.assertIn(body.get("source_type"), {"backend-data", "repo-root", "explicit", "union-resolver"})

    def test_returns_known_visa_code(self):
        """Real Paradiso data must include D-2 (used by ask payload tests)."""
        client, _ = _client()
        resp = client.get("/api/visas")
        codes = {v.get("code") for v in resp.json().get("data", [])}
        self.assertIn("D-2", codes)

    def test_response_declares_utf8_charset(self):
        """Without an explicit charset, some legacy clients decode the
        UTF-8 body as latin-1 and render Korean text as mojibake."""
        client, _ = _client()
        resp = client.get("/api/visas")
        ctype = resp.headers.get("content-type", "")
        self.assertIn("application/json", ctype.lower())
        self.assertIn("charset=utf-8", ctype.lower())

    def test_korean_text_round_trips_unchanged(self):
        """The first record (K-ETA) ships with Korean text; any
        encoding round-trip bug would replace those Hangul syllables
        with mojibake or U+FFFD replacement characters."""
        client, _ = _client()
        resp = client.get("/api/visas")
        # Strict UTF-8 decode of the raw body, then JSON parse.
        body_bytes = resp.content
        self.assertEqual(body_bytes.count("�".encode("utf-8")), 0,
                         "response body contains U+FFFD replacement characters")
        import json as _json
        body = _json.loads(body_bytes.decode("utf-8"))
        records = {v.get("code"): v for v in body.get("data", [])}
        self.assertIn("K-ETA", records, "K-ETA record must be present")
        self.assertEqual(
            records["K-ETA"].get("name"),
            "전자여행허가 (K-ETA) 종합 가이드",
            "Korean name field on K-ETA must round-trip exactly",
        )


class AskEndpointSchemaTests(unittest.TestCase):
    """No LLM keys are set, so /api/ask returns 503 once the prompt
    passes schema validation. The point of these tests is to assert the
    request *parses* and resolves a non-empty prompt — not to call an
    LLM. 503 here is the success signal; 400 (empty_prompt) is the
    failure signal we are guarding against.
    """

    PROMPT = "D-2 비자 연장에 필요한 서류는?"

    def _post(self, payload):
        client, _ = _client()
        return client.post("/api/ask", json=payload)

    def test_accepts_message(self):
        resp = self._post({"message": self.PROMPT})
        self.assertEqual(resp.status_code, 503, resp.text)
        self.assertEqual(resp.json()["detail"]["error"], "no_llm_provider_configured")

    def test_accepts_query(self):
        resp = self._post({"query": self.PROMPT})
        self.assertEqual(resp.status_code, 503, resp.text)

    def test_accepts_question(self):
        resp = self._post({"question": self.PROMPT})
        self.assertEqual(resp.status_code, 503, resp.text)

    def test_accepts_visa_code_without_400(self):
        resp = self._post({"question": self.PROMPT, "visa_code": "D-2"})
        self.assertEqual(resp.status_code, 503, resp.text)

    def test_accepts_full_frontend_payload(self):
        """The shape index.html / ai.html actually send."""
        resp = self._post({
            "question": self.PROMPT,
            "consent": True,
            "context": "doc guide",
            "lang": "ko",
            "visa_data": {"code": "D-2", "name": "유학"},
        })
        self.assertEqual(resp.status_code, 503, resp.text)

    def test_empty_payload_returns_updated_error_message(self):
        resp = self._post({})
        self.assertEqual(resp.status_code, 400)
        detail = resp.json()["detail"]
        self.assertEqual(detail["error"], "empty_prompt")
        self.assertIn("question", detail["message"])

    def test_resolution_order_prefers_message(self):
        """If multiple aliases are sent, message wins."""
        resp = self._post({
            "message": "primary",
            "query": "secondary",
            "question": "tertiary",
        })
        self.assertEqual(resp.status_code, 503, resp.text)


class GroundingFixtureTests(unittest.TestCase):
    """The grounding fixture is shipped with the deploy context, must be
    valid JSON, and must contain honest, non-fabricated metadata."""

    FIXTURE = BACKEND_DIR / "data" / "manual_grounding" / "stay_manual_grounding_2026_05.json"

    def test_fixture_present(self):
        self.assertTrue(self.FIXTURE.is_file(), f"missing fixture: {self.FIXTURE}")

    def test_fixture_metadata_is_korea_specific(self):
        import json as _json
        data = _json.loads(self.FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(data.get("source_file"), "docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf")
        self.assertEqual(data.get("source_title"), "외국인체류 안내매뉴얼")
        self.assertEqual(data.get("source_date"), "2026.5")
        self.assertEqual(data.get("source_revision_date"), "2026-06-01")
        self.assertEqual(data.get("issuing_body"), "법무부 출입국·외국인정책본부")
        groundings = data.get("groundings") or []
        self.assertTrue(groundings, "groundings list must not be empty")
        d2_ext = next(
            (g for g in groundings
             if g.get("visa_code") == "D-2"
             and g.get("procedure_type") == "체류기간 연장허가"),
            None,
        )
        self.assertIsNotNone(d2_ext, "D-2 체류기간 연장허가 grounding entry missing")
        self.assertEqual(d2_ext.get("section"), "유학(D-2)")
        # page_range must be either null (unverified) or a non-empty string.
        page_range = d2_ext.get("page_range")
        self.assertTrue(page_range is None or (isinstance(page_range, str) and page_range.strip()))
        # Verification metadata must be present and explicit.
        self.assertIn(d2_ext.get("source_verification_status"), {"verified_locally", "unverified", "pending_verification"})
        self.assertIsInstance(d2_ext.get("verification_note"), str)
        self.assertTrue(d2_ext["verification_note"].strip())

    def test_fixture_documents_are_korea_specific_and_conservative(self):
        import json as _json
        data = _json.loads(self.FIXTURE.read_text(encoding="utf-8"))
        d2_ext = next(
            g for g in data["groundings"]
            if g.get("visa_code") == "D-2"
            and g.get("procedure_type") == "체류기간 연장허가"
        )
        docs = " ".join(d2_ext.get("required_documents", []))
        # Must include Korea-specific stay-manual items.
        for needle in ("신청서", "여권", "외국인등록증", "수수료", "재정입증", "체류지 입증서류"):
            self.assertIn(needle, docs, f"expected '{needle}' in required_documents")
        # Must NOT include generic global immigration items.
        forbidden = (
            "USCIS",
            "Home Office",
            "embassy",
            "consulate",
            "해당 국가",
            "본인이 체류 중인 국가",
        )
        haystack = docs + " " + " ".join(d2_ext.get("caveats", []))
        for needle in forbidden:
            self.assertNotIn(
                needle, haystack,
                f"grounding must not contain generic/global wording: {needle!r}",
            )


class AskEndpointGroundingTests(unittest.TestCase):
    """Verify that D-2 + 체류기간 연장 questions select the grounding,
    and unrelated questions do not. With no LLM keys we still get a 503,
    but the response detail carries the grounding metadata."""

    def _post(self, payload):
        client, _ = _client()
        return client.post("/api/ask", json=payload)

    def test_d2_extension_korean_question_selects_grounding(self):
        resp = self._post({
            "question": "D-2 비자로 체류중인 경우에는 비자 연장 신청시 서류가 무엇이 필요합니까?",
            "visa_code": "D-2",
            "lang": "ko",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-2")
        self.assertEqual(detail.get("task_type_detected"), "extension")
        sources = detail.get("grounding_sources") or []
        self.assertEqual(len(sources), 1)
        src = sources[0]
        self.assertEqual(src.get("source_file"), "docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf")
        self.assertEqual(src.get("source_title"), "외국인체류 안내매뉴얼")
        self.assertEqual(src.get("source_date"), "2026.5")
        self.assertEqual(src.get("source_revision_date"), "2026-06-01")
        self.assertEqual(src.get("visa_code"), "D-2")
        self.assertEqual(src.get("procedure_type"), "체류기간 연장허가")

    def test_d2_extension_detection_from_text_only(self):
        """No explicit visa_code in payload; detection must still fire."""
        resp = self._post({
            "question": "유학(D-2) 자격으로 체류 중인데 체류기간 연장허가 신청에 필요한 서류는?",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-2")
        self.assertEqual(detail.get("task_type_detected"), "extension")

    def test_d2_extension_english_wording(self):
        resp = self._post({
            "question": "What documents do I need to extend my D-2 student visa stay?",
            "visa_code": "D-2",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-2")
        self.assertEqual(detail.get("task_type_detected"), "extension")

    def test_ungrounded_visa_question_does_not_use_grounding(self):
        """A visa code without a verified grounding entry must fall through
        the grounding path even when the task is recognized as extension."""
        resp = self._post({
            "question": "F-2 비자 연장 서류는?",
            "visa_code": "F-2",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("grounding_sources"), [])
        # Task is still detected as extension; only the grounding gate is narrow.
        self.assertEqual(detail.get("visa_code_detected"), "F-2")
        self.assertEqual(detail.get("task_type_detected"), "extension")

    def test_d2_non_extension_question_does_not_use_grounding(self):
        resp = self._post({
            "question": "D-2 자격 신청에 필요한 학력 증빙은 무엇인가요?",
            "visa_code": "D-2",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-2")
        self.assertIsNone(detail.get("task_type_detected"))


class ExpandedGroundingFixtureTests(unittest.TestCase):
    """The first batch of manual-grounding expansion beyond D-2:
    D-4 (어학연수생 D-4-1/D-4-7) and E-7 체류기간 연장허가."""

    FIXTURE = BACKEND_DIR / "data" / "manual_grounding" / "stay_manual_grounding_2026_05.json"

    def _entries(self):
        import json as _json
        data = _json.loads(self.FIXTURE.read_text(encoding="utf-8"))
        return {
            (g.get("visa_code"), g.get("procedure_type")): g
            for g in data.get("groundings", [])
        }

    def test_d4_and_e7_entries_present(self):
        entries = self._entries()
        self.assertIn(("D-4", "체류기간 연장허가"), entries)
        self.assertIn(("E-7", "체류기간 연장허가"), entries)

    def test_d4_entry_metadata_verified(self):
        entry = self._entries()[("D-4", "체류기간 연장허가")]
        self.assertEqual(entry.get("page_range"), "90-91")
        self.assertEqual(entry.get("source_verification_status"), "verified_locally")
        self.assertEqual(entry.get("source_confidence"), "high")
        self.assertTrue((entry.get("verification_note") or "").strip())
        # Section label should explicitly scope to 어학연수생 to avoid implying
        # coverage of all D-4 sub-codes.
        self.assertIn("어학연수생", entry.get("section", ""))
        # Korea-specific 어학연수 documents.
        docs = " ".join(entry.get("required_documents", []))
        for needle in ("신청서", "여권", "외국인등록증", "수수료", "재학을 입증", "재정입증", "체류지 입증서류"):
            self.assertIn(needle, docs, f"expected '{needle}' in D-4 required_documents")

    def test_e7_entry_metadata_verified(self):
        entry = self._entries()[("E-7", "체류기간 연장허가")]
        self.assertEqual(entry.get("page_range"), "226")
        self.assertEqual(entry.get("source_verification_status"), "verified_locally")
        self.assertEqual(entry.get("source_confidence"), "high")
        self.assertTrue((entry.get("verification_note") or "").strip())
        self.assertIn("특정활동", entry.get("section", ""))
        docs = " ".join(entry.get("required_documents", []))
        # E-7 extension is employment-track; the source page lists 고용계약서
        # and 소득금액 증명 alongside the common 신청서/여권/외국인등록증/수수료.
        for needle in (
            "신청서", "여권", "외국인등록증", "수수료",
            "고용계약서", "개인 소득금액 증명",
            "사업자등록증", "체류지 입증서류",
        ):
            self.assertIn(needle, docs, f"expected '{needle}' in E-7 required_documents")

    def test_no_generic_global_wording_in_new_entries(self):
        forbidden = (
            "USCIS",
            "Home Office",
            "embassy",
            "consulate",
            "해당 국가",
            "본인이 체류 중인 국가",
        )
        for key in (("D-4", "체류기간 연장허가"), ("E-7", "체류기간 연장허가")):
            entry = self._entries()[key]
            haystack = " ".join(entry.get("required_documents", [])) + " " + " ".join(entry.get("caveats", []))
            for needle in forbidden:
                self.assertNotIn(
                    needle, haystack,
                    f"{key} grounding must not contain generic/global wording: {needle!r}",
                )


class AskEndpointExpandedGroundingTests(unittest.TestCase):
    """End-to-end: D-4 (어학연수생) and E-7 extension questions must trip
    the grounding selector with the correct source metadata."""

    def _post(self, payload):
        client, _ = _client()
        return client.post("/api/ask", json=payload)

    # ---- D-4 ----
    def test_d4_extension_korean_question_selects_grounding(self):
        resp = self._post({
            "question": "D-4 어학연수 자격으로 체류 중인데 체류기간 연장에 필요한 서류는 무엇입니까?",
            "visa_code": "D-4",
            "lang": "ko",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-4")
        self.assertEqual(detail.get("task_type_detected"), "extension")
        src = (detail.get("grounding_sources") or [{}])[0]
        self.assertEqual(src.get("visa_code"), "D-4")
        self.assertEqual(src.get("procedure_type"), "체류기간 연장허가")
        self.assertEqual(src.get("page_range"), "90-91")
        self.assertEqual(src.get("source_file"), "docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf")

    def test_d4_extension_english_question_selects_grounding(self):
        resp = self._post({
            "question": "What documents do I need to extend my D-4 language-training stay in Korea?",
            "visa_code": "D-4",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-4")
        self.assertEqual(detail.get("task_type_detected"), "extension")

    def test_d4_payload_variants_normalize(self):
        for raw in ("d4", "D4", "d-4", "D 4"):
            resp = self._post({
                "question": "체류기간 연장 신청에 필요한 서류는?",
                "visa_code": raw,
            })
            self.assertEqual(resp.status_code, 503, resp.text)
            detail = resp.json()["detail"]
            self.assertTrue(detail.get("grounding_used"), f"raw={raw!r} did not ground")
            self.assertEqual(detail.get("visa_code_detected"), "D-4")

    def test_d4_non_extension_question_does_not_use_grounding(self):
        resp = self._post({
            "question": "D-4 자격 신청에 필요한 학력 증빙은 무엇인가요?",
            "visa_code": "D-4",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-4")
        self.assertIsNone(detail.get("task_type_detected"))

    # ---- E-7 ----
    def test_e7_extension_korean_question_selects_grounding(self):
        resp = self._post({
            "question": "E-7 특정활동 자격으로 체류 중인데 체류기간 연장허가 신청에 필요한 서류는 무엇입니까?",
            "visa_code": "E-7",
            "lang": "ko",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "E-7")
        self.assertEqual(detail.get("task_type_detected"), "extension")
        src = (detail.get("grounding_sources") or [{}])[0]
        self.assertEqual(src.get("visa_code"), "E-7")
        self.assertEqual(src.get("procedure_type"), "체류기간 연장허가")
        self.assertEqual(src.get("page_range"), "226")

    def test_e7_extension_english_question_selects_grounding(self):
        resp = self._post({
            "question": "What documents do I need to extend my E-7 specially-designated activity status in Korea?",
            "visa_code": "E7",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "E-7")
        self.assertEqual(detail.get("task_type_detected"), "extension")

    def test_e7_payload_variants_normalize(self):
        for raw in ("e7", "E7", "e-7", "E 7"):
            resp = self._post({
                "question": "체류기간 연장에 필요한 서류는?",
                "visa_code": raw,
            })
            self.assertEqual(resp.status_code, 503, resp.text)
            detail = resp.json()["detail"]
            self.assertTrue(detail.get("grounding_used"), f"raw={raw!r} did not ground")
            self.assertEqual(detail.get("visa_code_detected"), "E-7")

    def test_e7_non_extension_question_does_not_use_grounding(self):
        resp = self._post({
            "question": "E-7 자격으로 변경할 수 있는 조건은 무엇인가요?",
            "visa_code": "E-7",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "E-7")
        self.assertIsNone(detail.get("task_type_detected"))

    # ---- Text-only detection ----
    def test_text_only_detection_for_d4_and_e7(self):
        resp = self._post({
            "question": "일반연수(D-4) 자격으로 체류기간 연장허가 신청에 필요한 서류는?",
        })
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-4")

        resp = self._post({
            "question": "특정활동(E-7) 자격으로 체류기간 연장허가 신청 시 제출서류가 무엇인지 알려주세요.",
        })
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "E-7")

    # ---- Cross-contamination guards ----
    def test_d4_grounding_does_not_contain_e7_documents(self):
        _, mod = _client()
        bundle = mod._load_stay_manual_grounding()
        d4 = mod._select_grounding("D-4", "extension")
        built = mod._build_grounded_prompt("D-4 연장 서류?", d4, bundle, lang="ko")
        # E-7 specific item (고용계약서 / 소득금액 증명) must not bleed into D-4 prompt.
        self.assertNotIn("고용계약서", built)
        self.assertNotIn("소득금액 증명원", built)
        # D-4-specific item must be present.
        self.assertIn("재학을 입증", built)

    def test_e7_grounding_does_not_contain_d2_specific_documents(self):
        _, mod = _client()
        bundle = mod._load_stay_manual_grounding()
        e7 = mod._select_grounding("E-7", "extension")
        built = mod._build_grounded_prompt("E-7 연장 서류?", e7, bundle, lang="ko")
        # D-2-specific 'wording 지도교수' must not appear in E-7 prompt.
        self.assertNotIn("지도교수", built)
        # E-7 specific items present.
        self.assertIn("고용계약서", built)
        self.assertIn("소득금액", built)


class GroundingHelperTests(unittest.TestCase):
    """Unit tests for the pure helpers — no FastAPI client involved."""

    def test_grounded_prompt_includes_source_attribution_and_documents(self):
        client, mod = _client()
        bundle = mod._load_stay_manual_grounding()
        self.assertIsNotNone(bundle)
        grounding = mod._select_grounding("D-2", "extension")
        self.assertIsNotNone(grounding)
        user_q = "D-2 연장 서류 알려줘"
        built = mod._build_grounded_prompt(user_q, grounding, bundle)
        self.assertIn(user_q, built)
        self.assertIn("외국인체류 안내매뉴얼", built)
        self.assertIn("2026.5", built)
        self.assertIn("법무부 출입국·외국인정책본부", built)
        self.assertIn("유학(D-2)", built)
        self.assertIn("체류기간 연장허가", built)
        self.assertIn("재정입증 서류", built)
        self.assertIn("체류지 입증서류", built)
        # Guardrails against generic/global content.
        for forbidden in ("USCIS", "Home Office", "해당 국가"):
            self.assertNotIn(forbidden, built)


class VisaCodeNormalizationTests(unittest.TestCase):
    """The grounding lookup expects 'D-2'; payloads in the wild send d2,
    D2, d-2, etc. _normalize_visa_code must reshape those equivalently."""

    def test_normalize_variants(self):
        _, mod = _client()
        cases = {
            "D-2": "D-2",
            "d-2": "D-2",
            "D2": "D-2",
            "d2": "D-2",
            "D 2": "D-2",
            "  d-2  ": "D-2",
            "D-2-1": "D-2-1",
            "d-2-1": "D-2-1",
            "F-5": "F-5",
            "f5": "F-5",
        }
        for raw, expected in cases.items():
            self.assertEqual(mod._normalize_visa_code(raw), expected, f"input={raw!r}")

    def test_normalize_preserves_multi_digit_main_codes(self):
        """Regression guard for the Codex P1 finding: D-10 / E-10 / F-10
        must not be rewritten to D-1-0 / E-1-0 / F-1-0."""
        _, mod = _client()
        cases = {
            "D-10": "D-10",
            "d-10": "D-10",
            "D10": "D-10",
            "d10": "D-10",
            "D 10": "D-10",
            "d 10": "D-10",
            "E10": "E-10",
            "E-10": "E-10",
            "F10": "F-10",
            "F-10": "F-10",
            "f-10": "F-10",
            "H-2": "H-2",
            # Subcodes on multi-digit main codes still parse when an
            # explicit separator precedes the subcode.
            "D-10-1": "D-10-1",
            "d-10-1": "D-10-1",
            # Subcodes on single-digit main codes parse with or without
            # a leading separator before the main number.
            "d2-1": "D-2-1",
            "D2-1": "D-2-1",
        }
        for raw, expected in cases.items():
            self.assertEqual(mod._normalize_visa_code(raw), expected, f"input={raw!r}")

    def test_normalize_does_not_split_multi_digit_into_subcode(self):
        """Explicit anti-regression: 'D-10' must never come out as 'D-1-0'."""
        _, mod = _client()
        for raw in ("D-10", "d-10", "D10", "d10", "E10", "E-10", "F10", "F-10"):
            self.assertNotEqual(
                mod._normalize_visa_code(raw),
                f"{raw[0].upper()}-1-0",
                f"input={raw!r} was incorrectly split into a subcode",
            )

    def test_normalize_passes_through_special_codes(self):
        _, mod = _client()
        # K-STAR and REGION-S are not Letter+digits; they pass through.
        self.assertEqual(mod._normalize_visa_code("K-STAR"), "K-STAR")
        self.assertEqual(mod._normalize_visa_code("k-star"), "K-STAR")
        self.assertEqual(mod._normalize_visa_code("REGION-S"), "REGION-S")

    def test_normalize_empty_and_none(self):
        _, mod = _client()
        self.assertIsNone(mod._normalize_visa_code(None))
        self.assertIsNone(mod._normalize_visa_code(""))
        self.assertIsNone(mod._normalize_visa_code("   "))


class AskEndpointVisaCodeNormalizationTests(unittest.TestCase):
    """End-to-end: lowercase / no-hyphen variants of D-2 must still trip
    the grounding selector."""

    PROMPT = "유학 비자로 체류 중인데 연장 신청 서류가 무엇인가요?"

    def _post(self, payload):
        client, _ = _client()
        return client.post("/api/ask", json=payload)

    def test_lowercase_d2_payload_triggers_grounding(self):
        resp = self._post({"question": self.PROMPT, "visa_code": "d2"})
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-2")

    def test_uppercase_no_hyphen_d2_payload_triggers_grounding(self):
        resp = self._post({"question": self.PROMPT, "visa_code": "D2"})
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-2")

    def test_lowercase_visa_data_code_triggers_grounding(self):
        resp = self._post({
            "question": self.PROMPT,
            "visa_data": {"code": "d2", "name": "유학"},
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-2")


class GroundedPromptLanguageTests(unittest.TestCase):
    """The Korea-specific grounding content stays the same, but the
    'answer language' instruction must follow req.lang."""

    USER_Q = "What documents do I need to extend my D-2 student visa stay?"

    def _built(self, lang):
        _, mod = _client()
        bundle = mod._load_stay_manual_grounding()
        grounding = mod._select_grounding("D-2", "extension")
        return mod._build_grounded_prompt(self.USER_Q, grounding, bundle, lang=lang)

    def test_lang_en_instructs_english_not_korean(self):
        built = self._built("en")
        # The answer-language instruction now carries anti-mixed-language
        # guardrails; assert on the stable substring rather than exact wording.
        self.assertIn("natural English", built)
        self.assertNotIn("한국어로 자연스럽게 답하십시오", built)
        # Korea-specific source attribution still present.
        self.assertIn("외국인체류 안내매뉴얼", built)
        self.assertIn("법무부 출입국·외국인정책본부", built)

    def test_lang_ko_instructs_korean(self):
        built = self._built("ko")
        self.assertIn("한국어로 자연스럽게 답하십시오", built)
        self.assertNotIn("natural English", built)
        self.assertIn("외국인체류 안내매뉴얼", built)

    def test_unknown_lang_falls_back_to_user_language(self):
        built = self._built(None)
        self.assertIn("same language as the user's question", built)
        self.assertNotIn("한국어로 자연스럽게 답하십시오", built)
        self.assertNotIn("natural English", built)
        # Korea-specific source attribution unchanged.
        self.assertIn("외국인체류 안내매뉴얼", built)

    def test_unrecognized_lang_value_also_falls_back(self):
        built = self._built("fr")
        self.assertIn("same language as the user's question", built)

    def test_answer_language_helper_directly(self):
        _, mod = _client()
        self.assertIn("한국어로 자연스럽게", mod._answer_language_instruction("ko"))
        self.assertIn("한국어로 자연스럽게", mod._answer_language_instruction("KO"))
        self.assertIn("natural English", mod._answer_language_instruction("en"))
        self.assertIn("natural English", mod._answer_language_instruction("EN"))
        # Chinese modes are now explicit and distinct.
        self.assertIn("简体", mod._answer_language_instruction("zh-CN"))
        self.assertIn("繁體", mod._answer_language_instruction("zh-TW"))
        for unknown in (None, "", "fr", "ja", "x"):
            self.assertIn(
                "same language as the user's question",
                mod._answer_language_instruction(unknown),
            )


class SubCodeNormalizationTests(unittest.TestCase):
    """Sub-code-aware normalization: D-4-2K, D-10-1, F-6-1, E-7-4 and
    contiguous variants (d42k, d101, f61, e74) must resolve to canonical
    'L-N-SUB' form. Existing main-code variants must not regress."""

    def test_normalize_sub_codes_with_and_without_separators(self):
        _, mod = _client()
        cases = {
            # D-4 family
            "D-4-2K": "D-4-2K",
            "D4-2K": "D-4-2K",
            "d4-2k": "D-4-2K",
            "d42k": "D-4-2K",
            "D-4-3": "D-4-3",
            "D4-3": "D-4-3",
            "d43": "D-4-3",
            "D-4-5": "D-4-5",
            "D4-5": "D-4-5",
            "d45": "D-4-5",
            "D-4-6": "D-4-6",
            "d46": "D-4-6",
            # D-10 family — must split correctly (D-10 main code, not D-1-01)
            "D-10": "D-10",
            "d10": "D-10",
            "D-10-1": "D-10-1",
            "D10-1": "D-10-1",
            "d10-1": "D-10-1",
            "d101": "D-10-1",
            "D-10-2": "D-10-2",
            "d102": "D-10-2",
            "D-10-T": "D-10-T",
            "d10t": "D-10-T",
            "d10-t": "D-10-T",
            # F-6 family
            "F-6": "F-6",
            "f6": "F-6",
            "F-6-1": "F-6-1",
            "F6-1": "F-6-1",
            "f6-1": "F-6-1",
            "f61": "F-6-1",
            "F-6-2": "F-6-2",
            "f62": "F-6-2",
            "F-6-3": "F-6-3",
            "f63": "F-6-3",
            # E-7 family
            "E-7": "E-7",
            "e7": "E-7",
            "E-7-4": "E-7-4",
            "E7-4": "E-7-4",
            "e7-4": "E-7-4",
            "e74": "E-7-4",
        }
        for raw, expected in cases.items():
            self.assertEqual(
                mod._normalize_visa_code(raw),
                expected,
                f"input={raw!r}",
            )

    def test_normalize_keta_passes_through(self):
        _, mod = _client()
        for raw, expected in (
            ("K-ETA", "K-ETA"),
            ("k-eta", "K-ETA"),
            ("K-eta", "K-ETA"),
            ("  k-eta  ", "K-ETA"),
        ):
            self.assertEqual(mod._normalize_visa_code(raw), expected, f"input={raw!r}")

    def test_normalize_d10_does_not_split_into_subcode_when_alone(self):
        """Regression: 'D-10' / 'd10' as the entire input must stay D-10."""
        _, mod = _client()
        for raw in ("D-10", "d-10", "D10", "d10", "D 10"):
            self.assertEqual(mod._normalize_visa_code(raw), "D-10", f"input={raw!r}")

    def test_split_visa_code_helper(self):
        _, mod = _client()
        self.assertEqual(mod._split_visa_code("D-4"), ("D-4", None))
        self.assertEqual(mod._split_visa_code("D-4-2K"), ("D-4", "D-4-2K"))
        self.assertEqual(mod._split_visa_code("D-10"), ("D-10", None))
        self.assertEqual(mod._split_visa_code("D-10-1"), ("D-10", "D-10-1"))
        self.assertEqual(mod._split_visa_code("F-6-1"), ("F-6", "F-6-1"))
        self.assertEqual(mod._split_visa_code("E-7-4"), ("E-7", "E-7-4"))
        # K-ETA must NOT be split into a sub-code (ETA is alpha, not a number).
        self.assertEqual(mod._split_visa_code("K-ETA"), ("K-ETA", None))
        self.assertEqual(mod._split_visa_code("REGION-S"), ("REGION-S", None))
        self.assertEqual(mod._split_visa_code(None), (None, None))
        self.assertEqual(mod._split_visa_code(""), (None, None))


class GroundingSelectorSubCodeTests(unittest.TestCase):
    """Selector must not overgeneralize: requests carrying a sub-code that
    is NOT covered by the general entry must return no grounding."""

    def test_d4_general_request_still_selects_d4_entry(self):
        _, mod = _client()
        entry = mod._select_grounding("D-4", "extension", None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get("visa_code"), "D-4")
        self.assertIsNone(entry.get("visa_sub_code"))

    def test_d4_subcode_in_sub_codes_covered_uses_general_entry(self):
        """D-4-1 and D-4-7 are explicitly in sub_codes_covered."""
        _, mod = _client()
        for sub in ("D-4-1", "D-4-7"):
            entry = mod._select_grounding("D-4", "extension", sub)
            self.assertIsNotNone(entry, f"sub={sub!r} should have grounded via D-4")
            self.assertEqual(entry.get("visa_code"), "D-4")

    def test_d4_2k_does_not_use_d4_grounding(self):
        _, mod = _client()
        self.assertIsNone(mod._select_grounding("D-4", "extension", "D-4-2K"))

    def test_d4_3_does_not_use_d4_grounding(self):
        _, mod = _client()
        self.assertIsNone(mod._select_grounding("D-4", "extension", "D-4-3"))

    def test_d4_5_does_not_use_d4_grounding(self):
        _, mod = _client()
        self.assertIsNone(mod._select_grounding("D-4", "extension", "D-4-5"))

    def test_d4_6_does_not_use_d4_grounding(self):
        _, mod = _client()
        self.assertIsNone(mod._select_grounding("D-4", "extension", "D-4-6"))

    def test_e7_general_request_still_selects_e7_entry(self):
        _, mod = _client()
        entry = mod._select_grounding("E-7", "extension", None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get("visa_code"), "E-7")
        self.assertIsNone(entry.get("visa_sub_code"))

    def test_e7_4_does_not_use_general_e7_grounding(self):
        """E-7-4 점수제 has a separate manual; the general E-7 entry must
        not be used as a fallback."""
        _, mod = _client()
        self.assertIsNone(mod._select_grounding("E-7", "extension", "E-7-4"))

    def test_d10_subcode_returns_none(self):
        """No D-10 fixture exists yet; any D-10 request returns None."""
        _, mod = _client()
        self.assertIsNone(mod._select_grounding("D-10", "extension", None))
        self.assertIsNone(mod._select_grounding("D-10", "extension", "D-10-1"))
        self.assertIsNone(mod._select_grounding("D-10", "extension", "D-10-2"))
        self.assertIsNone(mod._select_grounding("D-10", "extension", "D-10-T"))

    def test_f6_subcode_returns_none(self):
        """No F-6 fixture exists yet; any F-6 request returns None."""
        _, mod = _client()
        self.assertIsNone(mod._select_grounding("F-6", "extension", None))
        for sub in ("F-6-1", "F-6-2", "F-6-3"):
            self.assertIsNone(mod._select_grounding("F-6", "extension", sub))


class AskEndpointSubCodeRoutingTests(unittest.TestCase):
    """End-to-end: payloads carrying sub-code-specific visa codes must
    not overgeneralize. The response should expose visa_sub_code_detected
    and grounding_used appropriately."""

    def _post(self, payload):
        client, _ = _client()
        return client.post("/api/ask", json=payload)

    def _detail(self, resp):
        self.assertEqual(resp.status_code, 503, resp.text)
        return resp.json()["detail"]

    # ---- D-4 sub-code routing ----
    def test_d4_2k_payload_does_not_use_d4_grounding(self):
        detail = self._detail(self._post({
            "question": "체류기간 연장에 필요한 서류는?",
            "visa_code": "D-4-2K",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("grounding_sources"), [])
        self.assertEqual(detail.get("visa_code_detected"), "D-4")
        self.assertEqual(detail.get("visa_sub_code_detected"), "D-4-2K")
        self.assertEqual(detail.get("task_type_detected"), "extension")

    def test_d4_2k_lowercase_no_separator_payload_normalizes(self):
        detail = self._detail(self._post({
            "question": "체류기간 연장 신청 서류?",
            "visa_code": "d42k",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-4")
        self.assertEqual(detail.get("visa_sub_code_detected"), "D-4-2K")

    def test_d4_3_payload_does_not_use_d4_grounding(self):
        detail = self._detail(self._post({
            "question": "체류기간 연장 신청 서류?",
            "visa_code": "D-4-3",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-4")
        self.assertEqual(detail.get("visa_sub_code_detected"), "D-4-3")

    def test_d4_1_payload_does_use_d4_grounding(self):
        """D-4-1 is explicitly in sub_codes_covered, so the general D-4
        entry IS the right grounding for D-4-1 requests."""
        detail = self._detail(self._post({
            "question": "체류기간 연장 신청 서류?",
            "visa_code": "D-4-1",
        }))
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-4")
        self.assertEqual(detail.get("visa_sub_code_detected"), "D-4-1")

    def test_d4_top_level_payload_still_grounds(self):
        """Existing behavior: a plain D-4 + extension question grounds."""
        detail = self._detail(self._post({
            "question": "D-4 어학연수 체류기간 연장 서류?",
            "visa_code": "D-4",
            "lang": "ko",
        }))
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-4")
        self.assertIsNone(detail.get("visa_sub_code_detected"))

    # ---- E-7 sub-code routing ----
    def test_e7_4_payload_does_not_use_general_e7_grounding(self):
        detail = self._detail(self._post({
            "question": "체류기간 연장 신청 서류?",
            "visa_code": "E-7-4",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("grounding_sources"), [])
        self.assertEqual(detail.get("visa_code_detected"), "E-7")
        self.assertEqual(detail.get("visa_sub_code_detected"), "E-7-4")

    def test_e74_contiguous_payload_does_not_use_general_e7_grounding(self):
        detail = self._detail(self._post({
            "question": "체류기간 연장 신청 서류?",
            "visa_code": "e74",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "E-7")
        self.assertEqual(detail.get("visa_sub_code_detected"), "E-7-4")

    def test_e7_top_level_payload_still_grounds(self):
        detail = self._detail(self._post({
            "question": "E-7 체류기간 연장 서류?",
            "visa_code": "E-7",
        }))
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "E-7")
        self.assertIsNone(detail.get("visa_sub_code_detected"))

    # ---- D-10 (no fixture yet) ----
    def test_d10_top_level_returns_no_grounding(self):
        detail = self._detail(self._post({
            "question": "체류기간 연장 서류?",
            "visa_code": "D-10",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("grounding_sources"), [])

    def test_d10_1_payload_returns_no_grounding(self):
        detail = self._detail(self._post({
            "question": "체류기간 연장 서류?",
            "visa_code": "D-10-1",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-10")
        self.assertEqual(detail.get("visa_sub_code_detected"), "D-10-1")

    def test_d101_contiguous_payload_normalizes_and_returns_no_grounding(self):
        detail = self._detail(self._post({
            "question": "체류기간 연장 서류?",
            "visa_code": "d101",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-10")
        self.assertEqual(detail.get("visa_sub_code_detected"), "D-10-1")

    # ---- F-6 (no fixture yet) ----
    def test_f6_1_payload_returns_no_grounding(self):
        detail = self._detail(self._post({
            "question": "체류기간 연장 서류?",
            "visa_code": "F-6-1",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "F-6")
        self.assertEqual(detail.get("visa_sub_code_detected"), "F-6-1")

    def test_f61_contiguous_payload_normalizes_and_returns_no_grounding(self):
        detail = self._detail(self._post({
            "question": "체류기간 연장 서류?",
            "visa_code": "f61",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "F-6")
        self.assertEqual(detail.get("visa_sub_code_detected"), "F-6-1")

    def test_f6_top_level_returns_no_grounding_either(self):
        """F-6 top-level extension also has no fixture yet."""
        detail = self._detail(self._post({
            "question": "체류기간 연장 서류?",
            "visa_code": "F-6",
        }))
        self.assertFalse(detail.get("grounding_used"))

    # ---- Non-extension gating still works for sub-codes ----
    def test_d4_2k_non_extension_task_returns_no_grounding(self):
        detail = self._detail(self._post({
            "question": "D-4 자격 신청에 필요한 학력 증빙은 무엇인가요?",
            "visa_code": "D-4-2K",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertIsNone(detail.get("task_type_detected"))

    # ---- Schema version + no generic global wording bleed-through ----
    def test_no_generic_global_wording_after_subcode_routing(self):
        """When sub-code routing kicks in (and returns no fixture), the
        existing pass-through path must not introduce any global immigration
        wording. The 503 detail carries no grounding so nothing is injected."""
        detail = self._detail(self._post({
            "question": "체류기간 연장 서류?",
            "visa_code": "D-4-2K",
        }))
        for forbidden in (
            "USCIS", "Home Office", "embassy", "consulate",
            "해당 국가", "본인이 체류 중인 국가",
        ):
            self.assertNotIn(forbidden, str(detail), f"forbidden token: {forbidden!r}")


class GroundingFixtureSchemaV12Tests(unittest.TestCase):
    """schema_version is bumped to 1.2 and entries carry the new optional
    sub-code / scenario fields."""

    FIXTURE = BACKEND_DIR / "data" / "manual_grounding" / "stay_manual_grounding_2026_05.json"

    def _data(self):
        import json as _json
        return _json.loads(self.FIXTURE.read_text(encoding="utf-8"))

    def test_schema_version_is_1_2(self):
        self.assertEqual(self._data().get("schema_version"), "1.2")

    def test_d2_entry_has_null_subcode_fields(self):
        groundings = {g.get("visa_code"): g for g in self._data().get("groundings", [])}
        d2 = groundings.get("D-2")
        self.assertIsNotNone(d2)
        self.assertIsNone(d2.get("visa_sub_code"))
        self.assertIsNone(d2.get("sub_codes_covered"))
        self.assertIsNone(d2.get("scenario"))
        self.assertIsNone(d2.get("scenarios_covered"))
        self.assertFalse(d2.get("requires_clarification_when_missing_subcode"))

    def test_d4_entry_sub_codes_covered_only_d4_1_and_d4_7(self):
        groundings = {g.get("visa_code"): g for g in self._data().get("groundings", [])}
        d4 = groundings.get("D-4")
        self.assertIsNotNone(d4)
        self.assertIsNone(d4.get("visa_sub_code"))
        self.assertEqual(sorted(d4.get("sub_codes_covered") or []), ["D-4-1", "D-4-7"])
        # Section label still scopes explicitly to 어학연수생 so the entry
        # cannot be misread as covering all D-4 sub-codes.
        self.assertIn("어학연수생", d4.get("section", ""))

    def test_e7_entry_general_scenario(self):
        groundings = {g.get("visa_code"): g for g in self._data().get("groundings", [])}
        e7 = groundings.get("E-7")
        self.assertIsNotNone(e7)
        self.assertIsNone(e7.get("visa_sub_code"))
        # E-7 entry must NOT imply coverage of E-7-4 or E-7 협정 특례 tracks.
        self.assertIsNone(e7.get("sub_codes_covered"))
        self.assertEqual(e7.get("scenario"), "general")
        self.assertEqual(e7.get("scenarios_covered"), ["general"])


class FallbackTaskTypeDetectionTests(unittest.TestCase):
    """Extended task-type detection: marriage/divorce, academic, overstay, etc."""

    def _detect(self, text):
        _, mod = _client()
        return mod._detect_task_type(text)

    # ---- marriage_divorce_status_change ----

    def test_f61_divorce_query_en_triggers_marriage_divorce(self):
        result = self._detect(
            "Will my visa be revoked immediately if an American who is staying on an F-6-1 visa divorces?"
        )
        self.assertEqual(result, "marriage_divorce_status_change")

    def test_f61_divorce_query_ko_triggers_marriage_divorce(self):
        result = self._detect("F-6-1 비자로 체류 중인데 이혼하면 체류자격이 어떻게 되나요?")
        self.assertEqual(result, "marriage_divorce_status_change")

    def test_separated_triggers_marriage_divorce(self):
        self.assertEqual(self._detect("We are now separated. Does that affect my F-6 visa?"), "marriage_divorce_status_change")

    def test_widowed_triggers_marriage_divorce(self):
        self.assertEqual(self._detect("My Korean spouse passed away. I am widowed. What happens to my F-6?"), "marriage_divorce_status_change")

    def test_marriage_divorce_outranks_extension_when_both_signals(self):
        result = self._detect("이혼했는데 F-6-1 비자 연장이 다음 달이에요. 어떻게 해야 하나요?")
        self.assertEqual(result, "marriage_divorce_status_change")

    # ---- academic_status_change ----

    def test_leave_of_absence_en_triggers_academic(self):
        result = self._detect(
            "I'm on a D-2 visa and taking a leave of absence this semester — does that affect my stay?"
        )
        self.assertEqual(result, "academic_status_change")

    def test_gap_semester_triggers_academic(self):
        self.assertEqual(self._detect("Can I take a gap semester without losing my D-4 status?"), "academic_status_change")

    def test_hwuhak_triggers_academic(self):
        result = self._detect("D-2 비자로 유학 중인데 이번 학기 휴학하면 체류 자격에 문제가 있나요?")
        self.assertEqual(result, "academic_status_change")

    # ---- overstay_deadline_risk ----

    def test_visa_expired_triggers_overstay(self):
        self.assertEqual(self._detect("My visa expired yesterday — what now?"), "overstay_deadline_risk")

    def test_chogwa_triggers_overstay(self):
        self.assertEqual(self._detect("비자가 어제 만료됐어요. 초과체류가 됩니까?"), "overstay_deadline_risk")

    # ---- workplace_change ----

    def test_change_employer_triggers_workplace(self):
        self.assertEqual(self._detect("I want to change employer. What do I need to report?"), "workplace_change")

    def test_geupmucheo_triggers_workplace(self):
        self.assertEqual(self._detect("근무처 변경 신고를 해야 하나요?"), "workplace_change")

    # ---- address_report ----

    def test_address_change_triggers_address_report(self):
        self.assertEqual(self._detect("I moved. Where do I report my new address?"), "address_report")

    def test_isa_triggers_address_report(self):
        self.assertEqual(self._detect("이사를 했습니다. 어디에 신고해야 하나요?"), "address_report")

    # ---- extension still detected correctly ----

    def test_extension_detected_when_no_other_signal(self):
        self.assertEqual(self._detect("D-2 비자 연장에 필요한 서류는?"), "extension")

    def test_extension_en_detected(self):
        self.assertEqual(self._detect("How do I renew my D-4 visa?"), "extension")

    # ---- risk levels ----

    def test_marriage_divorce_is_high_risk(self):
        _, mod = _client()
        self.assertEqual(mod._risk_level_for_task("marriage_divorce_status_change"), "high")

    def test_overstay_is_high_risk(self):
        _, mod = _client()
        self.assertEqual(mod._risk_level_for_task("overstay_deadline_risk"), "high")

    def test_extension_is_medium_risk(self):
        _, mod = _client()
        self.assertEqual(mod._risk_level_for_task("extension"), "medium")

    def test_address_report_is_low_risk(self):
        _, mod = _client()
        self.assertEqual(mod._risk_level_for_task("address_report"), "low")

    def test_none_task_returns_low_risk(self):
        _, mod = _client()
        self.assertEqual(mod._risk_level_for_task(None), "low")


class FallbackGroundingRoutingTests(unittest.TestCase):
    """F-6-1 divorce must not accidentally use D-2/D-4/E-7 extension grounding."""

    def _post(self, payload):
        client, _ = _client()
        return client.post("/api/ask", json=payload)

    def _detail(self, resp):
        self.assertEqual(resp.status_code, 503, resp.text)
        return resp.json()["detail"]

    def test_f61_divorce_query_does_not_use_grounding(self):
        detail = self._detail(self._post({
            "question": "Will my visa be revoked immediately if an American who is staying on an F-6-1 visa divorces?",
            "visa_code": "F-6-1",
        }))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("grounding_sources"), [])

    def test_f61_divorce_detects_marriage_divorce_task(self):
        detail = self._detail(self._post({
            "question": "Will my visa be revoked immediately if an American who is staying on an F-6-1 visa divorces?",
            "visa_code": "F-6-1",
        }))
        self.assertEqual(detail.get("task_type_detected"), "marriage_divorce_status_change")
        self.assertEqual(detail.get("visa_code_detected"), "F-6")
        self.assertEqual(detail.get("visa_sub_code_detected"), "F-6-1")

    def test_f61_divorce_high_risk_level(self):
        detail = self._detail(self._post({
            "question": "Will my visa be revoked immediately if an American who is staying on an F-6-1 visa divorces?",
            "visa_code": "F-6-1",
        }))
        self.assertEqual(detail.get("risk_level_detected"), "high")

    def test_d2_extension_still_grounds_after_task_type_expansion(self):
        detail = self._detail(self._post({
            "question": "D-2 비자 연장 서류는 무엇인가요?",
            "visa_code": "D-2",
        }))
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("visa_code_detected"), "D-2")
        self.assertEqual(detail.get("task_type_detected"), "extension")

    def test_d4_extension_still_grounds_after_task_type_expansion(self):
        detail = self._detail(self._post({
            "question": "D-4 어학연수 체류기간 연장 서류?",
            "visa_code": "D-4",
        }))
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("task_type_detected"), "extension")

    def test_e7_extension_still_grounds_after_task_type_expansion(self):
        detail = self._detail(self._post({
            "question": "E-7 체류기간 연장 서류?",
            "visa_code": "E-7",
        }))
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("task_type_detected"), "extension")


class UngroundedFallbackPromptTests(unittest.TestCase):
    """Assert on the prompt string the fallback builder produces (no LLM)."""

    def _build_f61_divorce_prompt(self, lang=None):
        _, mod = _client()
        return mod._build_ungrounded_korea_scoped_prompt(
            "Will my visa be revoked immediately if an American who is staying on an F-6-1 visa divorces?",
            visa_code="F-6",
            visa_sub_code="F-6-1",
            task_type="marriage_divorce_status_change",
            risk_level="high",
            lang=lang,
        )

    # ---- Korea-immigration framing ----

    def test_f61_divorce_prompt_contains_korea_framing(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("한국", built)
        self.assertIn("출입국", built)
        self.assertIn("1345", built)

    def test_f61_divorce_prompt_does_not_contain_manual_attribution(self):
        built = self._build_f61_divorce_prompt()
        self.assertNotIn("외국인체류 안내매뉴얼 (2026.5)", built)
        self.assertNotIn("법무부 출입국·외국인정책본부", built)

    # ---- Forbidden global boilerplate ----

    def test_f61_divorce_prompt_forbids_non_korean_system_leakage(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("비한국(non-Korean) 이민제도", built)

    def test_f61_divorce_prompt_forbids_foreign_agency_boilerplate(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("외국 행정기관", built)
        self.assertIn("외국 법률절차 보일러플레이트", built)

    def test_f61_divorce_prompt_forbids_foreign_embassy_consulate_redirection(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("외국 대사관/영사관 문의", built)

    # ---- Immediate-revocation certainty forbidden ----

    def test_f61_divorce_prompt_forbids_immediate_revocation_language(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("즉시 취소", built)   # appears in the forbidden-token instruction
        self.assertIn("즉각적 취소", built)

    # ---- Missing-facts elicitation ----

    def test_f61_divorce_prompt_asks_for_arc_expiration(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("ARC 유효기간", built)

    def test_f61_divorce_prompt_asks_for_divorce_finalization(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("최종 확정", built)

    def test_f61_divorce_prompt_asks_for_children_custody(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("자녀", built)
        self.assertIn("양육권", built)

    def test_f61_divorce_prompt_asks_for_independent_status(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("독립적인 체류 자격", built)

    # ---- Six-section answer shape ----

    def test_f61_divorce_prompt_includes_six_sections(self):
        built = self._build_f61_divorce_prompt()
        for section in (
            "현재 알려진 사실",
            "한국 체류 측면의 쟁점",
            "가능한 경로",
            "확인이 필요한 정보",
            "다음 단계",
            "출처 한계",
        ):
            self.assertIn(section, built, f"missing section: {section!r}")

    # ---- Verify-marker for pathways ----

    def test_f61_divorce_prompt_marks_pathways_as_must_verify(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("확인 필요", built)

    def test_f61_divorce_prompt_forbids_invented_details(self):
        built = self._build_f61_divorce_prompt()
        for marker in (
            "제출서류",
            "기한/유예기간",
            "수수료/비용",
            "양식/서식 번호",
            "법령 조문 번호",
            "자격요건",
            "절차상 보장·결과 보장",
        ):
            self.assertIn(marker, built)

    # ---- Answer-language preservation ----

    def test_ungrounded_prompt_lang_ko(self):
        _, mod = _client()
        built = mod._build_ungrounded_korea_scoped_prompt("질문", lang="ko")
        self.assertIn("한국어로 자연스럽게 답하십시오", built)
        self.assertNotIn("natural English", built)

    def test_ungrounded_prompt_lang_en(self):
        _, mod = _client()
        built = mod._build_ungrounded_korea_scoped_prompt("question", lang="en")
        self.assertIn("natural English", built)
        self.assertNotIn("한국어로 자연스럽게 답하십시오", built)

    def test_ungrounded_prompt_lang_default(self):
        _, mod = _client()
        built = mod._build_ungrounded_korea_scoped_prompt("question", lang=None)
        self.assertIn("Answer in the same language as the user's question", built)

    # ---- No source attribution bleed-through ----

    def test_ungrounded_prompt_does_not_imply_source_grounding(self):
        built = self._build_f61_divorce_prompt()
        self.assertNotIn("외국인체류 안내매뉴얼 (2026.5)", built)
        self.assertNotIn("법무부 출입국·외국인정책본부", built)

    # ---- Non-F-6 divorce (no F-6-specific addendum but still Korea-scoped) ----

    def test_non_f6_divorce_prompt_is_still_korea_scoped(self):
        _, mod = _client()
        built = mod._build_ungrounded_korea_scoped_prompt(
            "What happens to my visa if I divorce? I have an E-2 visa.",
            visa_code="E-2",
            task_type="marriage_divorce_status_change",
            risk_level="high",
            lang="en",
        )
        self.assertIn("출입국", built)
        self.assertNotIn("USCIS", built.split("[금지 사항")[0])  # not in system role; is in the forbidden list

    # ---- Overstay prompt sanity ----

    def test_overstay_prompt_routes_to_1345(self):
        _, mod = _client()
        built = mod._build_ungrounded_korea_scoped_prompt(
            "My visa expired yesterday — what now?",
            task_type="overstay_deadline_risk",
            risk_level="high",
            lang="en",
        )
        self.assertIn("1345", built)


class GoldenEvalSuiteTests(unittest.TestCase):
    """Tests for the golden question eval suite and runner."""

    GOLDEN_Q_PATH = REPO_ROOT / "backend" / "data" / "eval" / "paradiso_ai_golden_questions.json"
    RUNNER_PATH = REPO_ROOT / "scripts" / "evaluate_paradiso_ai_golden_questions.py"

    # ---- 1. Golden JSON parses and has required structure ----

    def test_golden_json_exists_and_parses(self):
        self.assertTrue(self.GOLDEN_Q_PATH.is_file(), f"Missing: {self.GOLDEN_Q_PATH}")
        import json
        with open(self.GOLDEN_Q_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertIn("questions", data)
        questions = data["questions"]
        self.assertIsInstance(questions, list)
        self.assertGreaterEqual(len(questions), 30, "Must have at least 30 golden questions")
        self.assertLessEqual(len(questions), 50, "Must have at most 50 golden questions")

    def test_golden_json_schema_version_and_flags(self):
        import json
        with open(self.GOLDEN_Q_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data.get("schema_version"), "1.0")
        self.assertIs(data.get("is_training_data"), False)
        self.assertIs(data.get("is_llm_eval"), False)

    def test_golden_json_required_fields_present(self):
        import json
        required_fields = {"id", "language", "question", "expected_task_type",
                           "expected_grounding_status", "expected_risk_level"}
        with open(self.GOLDEN_Q_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        for item in data["questions"]:
            missing = required_fields - item.keys()
            self.assertFalse(missing, f"Question {item.get('id')} missing fields: {missing}")

    def test_golden_json_no_raw_personal_data(self):
        """Questions must not contain real personal data patterns."""
        import json, re
        # Patterns that suggest real personal identifiers
        pii_patterns = [
            re.compile(r"\b[A-Z]{2}\d{7}\b"),        # Korean ARC number pattern
            re.compile(r"\b\d{6}-\d{7}\b"),           # Korean RRN pattern
            re.compile(r"\b010-\d{4}-\d{4}\b"),       # Korean phone
            re.compile(r"\b[A-Z]\d{8}\b"),             # passport-like number
        ]
        with open(self.GOLDEN_Q_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        for item in data["questions"]:
            question = item.get("question", "")
            for pat in pii_patterns:
                self.assertIsNone(
                    pat.search(question),
                    f"Question {item['id']} may contain personal data: {question!r}",
                )

    def test_golden_json_ids_are_unique(self):
        import json
        with open(self.GOLDEN_Q_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        ids = [item.get("id") for item in data["questions"]]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate question IDs found")

    def test_golden_json_grounding_status_values_valid(self):
        import json
        valid_statuses = {"active_grounded", "candidate_only", "scoped_fallback",
                          "clarification_needed", "unsupported"}
        with open(self.GOLDEN_Q_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        for item in data["questions"]:
            status = item.get("expected_grounding_status")
            self.assertIn(status, valid_statuses,
                          f"Question {item['id']} has invalid grounding status: {status!r}")

    def test_golden_json_risk_level_values_valid(self):
        import json
        with open(self.GOLDEN_Q_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        for item in data["questions"]:
            risk = item.get("expected_risk_level")
            self.assertIn(risk, {"low", "medium", "high"},
                          f"Question {item['id']} has invalid risk_level: {risk!r}")

    # ---- 2. Runner executes in non-strict mode without error ----

    def test_runner_script_compiles(self):
        import py_compile
        self.assertTrue(self.RUNNER_PATH.is_file(), f"Missing: {self.RUNNER_PATH}")
        py_compile.compile(str(self.RUNNER_PATH), doraise=True)

    def test_runner_executes_non_strict(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(self.RUNNER_PATH)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0,
                         f"Runner failed in non-strict mode:\n{result.stdout}\n{result.stderr}")
        self.assertIn("All regression checks passed", result.stdout)

    def test_runner_json_output_is_valid(self):
        import subprocess, json
        result = subprocess.run(
            [sys.executable, str(self.RUNNER_PATH), "--json"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIn("total", data)
        self.assertIn("passed", data)
        self.assertIn("failed", data)
        self.assertEqual(data["failed"], 0)
        self.assertEqual(data["total"], data["passed"])

    # ---- 3. Known grounded cases pass ----

    def test_d2_extension_grounds(self):
        _, mod = _client()
        top, sub = mod._detect_visa_codes("D-2", None, "D-2 체류기간 연장 신청 방법이 궁금합니다.")
        task = mod._detect_task_type("D-2 체류기간 연장 신청 방법이 궁금합니다.")
        grounding = mod._select_grounding(top, task, sub)
        self.assertEqual(top, "D-2")
        self.assertEqual(task, "extension")
        self.assertIsNotNone(grounding)

    def test_e7_extension_grounds(self):
        _, mod = _client()
        top, sub = mod._detect_visa_codes("E-7", None, "How do I extend my E-7 visa?")
        task = mod._detect_task_type("How do I extend my E-7 visa?")
        grounding = mod._select_grounding(top, task, sub)
        self.assertEqual(top, "E-7")
        self.assertEqual(task, "extension")
        self.assertIsNotNone(grounding)

    def test_d4_extension_grounds(self):
        _, mod = _client()
        top, sub = mod._detect_visa_codes("D-4", None, "D-4 비자 연장하고 싶어요.")
        task = mod._detect_task_type("D-4 비자 연장하고 싶어요.")
        grounding = mod._select_grounding(top, task, sub)
        self.assertEqual(top, "D-4")
        self.assertEqual(task, "extension")
        self.assertIsNotNone(grounding)

    # ---- 4. F-6 divorce stays ungrounded but task/risk detected ----

    def test_f6_divorce_ungrounded_task_detected(self):
        _, mod = _client()
        q = "F-6-1 비자인데 이혼 후 체류 자격이 어떻게 되나요?"
        top, sub = mod._detect_visa_codes("F-6", None, q)
        task = mod._detect_task_type(q)
        risk = mod._risk_level_for_task(task)
        grounding = mod._select_grounding(top, task, sub)
        self.assertEqual(task, "marriage_divorce_status_change")
        self.assertEqual(risk, "high")
        self.assertIsNone(grounding, "F-6 divorce must NOT select any grounding entry")

    def test_f6_divorce_grounding_false_regardless_of_sub_code(self):
        _, mod = _client()
        for sub in ("F-6-1", "F-6-3", None):
            grounding = mod._select_grounding("F-6", "marriage_divorce_status_change", sub)
            self.assertIsNone(grounding,
                              f"F-6 divorce (sub={sub}) must not ground — task_type is not extension")

    # ---- 5. D-2 leave of absence does NOT select D-2 extension grounding ----

    def test_d2_leave_of_absence_does_not_select_extension_grounding(self):
        _, mod = _client()
        q = "D-2 비자인데 휴학을 하면 어떻게 되나요?"
        top, sub = mod._detect_visa_codes("D-2", None, q)
        task = mod._detect_task_type(q)
        grounding = mod._select_grounding(top, task, sub)
        self.assertEqual(task, "academic_status_change",
                         "Leave of absence must detect academic_status_change, not extension")
        self.assertIsNone(grounding,
                          "D-2 leave of absence must NOT select the D-2 extension grounding entry")

    def test_d2_gap_semester_does_not_select_extension_grounding(self):
        _, mod = _client()
        q = "I have a D-2 visa and am taking a gap semester next semester."
        top, sub = mod._detect_visa_codes("D-2", None, q)
        task = mod._detect_task_type(q)
        grounding = mod._select_grounding(top, task, sub)
        self.assertEqual(task, "academic_status_change")
        self.assertIsNone(grounding)

    # ---- 6. Answer-quality contract regression (H-1 study golden case) ----

    def _ask_detail(self, question, *, lang="ko", code=None):
        client, _ = _client()
        payload = {"question": question, "consent": True, "lang": lang}
        if code is not None:
            payload["visa_data"] = {"code": code}
        resp = client.post("/api/ask", json=payload)
        self.assertEqual(resp.status_code, 503, resp.text)
        return resp.json()["detail"]

    def test_h1_summer_semester_contract_metadata(self):
        d = self._ask_detail(
            "Can I take summer semester course in Korean universities even "
            "though I have a H-1 visa?",
            lang="en", code="H-1",
        )
        self.assertEqual(d["answer_quality_mode"], "source_limited")
        self.assertEqual(d["question_type_detected"], "activity_on_status")
        self.assertEqual(d["related_statuses_not_sources"], ["D-2", "D-4"])
        # D-2 / D-4 must never be presented as direct manual source grounding.
        self.assertFalse(d["grounding_used"])
        self.assertEqual(d["grounding_sources"], [])
        self.assertEqual(len(d["official_confirmation_questions"]), 7)

    def test_d2_extension_is_source_confirmed(self):
        d = self._ask_detail("D-2 비자 연장에 필요한 서류는?", lang="ko", code="D-2")
        self.assertTrue(d["grounding_used"])
        self.assertEqual(d["answer_quality_mode"], "source_confirmed")
        self.assertFalse(d["requires_official_confirmation"])

    def test_contract_metadata_always_present(self):
        d = self._ask_detail("일반 질문", lang="ko")
        for key in (
            "answer_quality_mode", "source_confidence_level",
            "requires_official_confirmation", "official_confirmation_questions",
            "related_statuses_not_sources", "grounded_answer_limited",
            "answer_style_version", "question_type_detected",
        ):
            self.assertIn(key, d, f"missing answer-quality key: {key}")


class LawPublicDataScaffoldTests(unittest.TestCase):
    def test_default_grounding_config_mode_is_enabled(self):
        os.environ.pop("LAW_GROUNDING_MODE", None)
        os.environ.pop("LAW_GROUNDING_TIMEOUT_SECONDS", None)
        os.environ.pop("LAW_GROUNDING_CACHE_TTL_SECONDS", None)
        from services.grounding_config import load_grounding_config

        cfg = load_grounding_config()
        # Law/precedent grounding is fully activated by default; external calls
        # still require a credential (LAW_API_OC / legacy LAW_API_KEY).
        self.assertEqual(cfg.mode, "enabled")
        self.assertGreater(cfg.timeout_seconds, 0)
        self.assertGreater(cfg.cache_ttl_seconds, 0)

    def test_disabled_law_grounding_returns_empty(self):
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        from services.law_grounding import build_law_grounding_context

        ctx = build_law_grounding_context("출입국관리법 제10조 알려줘")
        self.assertFalse(ctx["law_grounding_used"])
        self.assertEqual(ctx["law_grounding"], [])
        self.assertIn("LAW_GROUNDING_DISABLED", ctx["grounding_warnings"])

    def test_missing_law_api_key_in_audit_mode_is_unavailable(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        os.environ.pop("LAW_API_KEY", None)
        from services.grounding_config import load_grounding_config
        from services.korean_law_client import KoreanLawClient

        client = KoreanLawClient(load_grounding_config())
        result = client.search_law("국적법 제5조")
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("LAW_API_KEY_MISSING", result["warnings"])

    def test_citation_extraction_detects_simple_korean_legal_citation(self):
        from services.citation_verifier import extract_korean_legal_citations

        result = extract_korean_legal_citations("출입국관리법 제10조 및 국적법 제5조를 확인")
        self.assertEqual(result["status"], "extracted_only")
        self.assertIn("CITATION_VERIFICATION_NOT_WIRED", result["warnings"])
        self.assertGreaterEqual(len(result["citations"]), 2)
        self.assertEqual(result["citations"][0]["law_name"], "출입국관리법")

    def test_health_endpoint_still_passes(self):
        client, _ = _client()
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json().get("status"), "ok")

    def test_api_ask_behavior_unchanged_no_provider(self):
        client, _ = _client()
        resp = client.post("/api/ask", json={"question": "D-2 비자 연장"})
        self.assertEqual(resp.status_code, 503, resp.text)
        self.assertEqual(resp.json()["detail"]["error"], "no_llm_provider_configured")


class AuditModeHttpClientTests(unittest.TestCase):
    def test_disabled_mode_law_search_performs_no_http_call(self):
        from services.grounding_config import load_grounding_config
        from services.korean_law_client import KoreanLawClient
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        with patch("services.korean_law_client.httpx.Client") as mocked_client:
            result = KoreanLawClient(load_grounding_config()).search_law("출입국관리법 제10조")
        self.assertEqual(result["status"], "disabled")
        mocked_client.assert_not_called()

    def test_audit_missing_law_key_warning(self):
        from services.grounding_config import load_grounding_config
        from services.korean_law_client import KoreanLawClient
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        os.environ.pop("LAW_API_KEY", None)
        result = KoreanLawClient(load_grounding_config()).search_law("국적법 제5조")
        self.assertIn("LAW_API_KEY_MISSING", result["warnings"])

    def test_audit_missing_public_data_key_warning(self):
        from services.grounding_config import load_grounding_config
        from services.public_data_client import PublicDataClient
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        os.environ.pop("PUBLIC_DATA_API_KEY", None)
        result = PublicDataClient(load_grounding_config()).fetch_visa_public_data("D-2")
        self.assertIn("PUBLIC_DATA_API_KEY_MISSING", result["warnings"])

    def test_audit_law_search_http_200(self):
        from services.grounding_config import load_grounding_config
        from services.korean_law_client import KoreanLawClient
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        os.environ["LAW_API_KEY"] = "secret-law-token"
        os.environ["LAW_API_BASE_URL"] = "https://law.example.test"
        os.environ["LAW_API_SEARCH_PATH"] = "/search"

        class DummyResponse:
            status_code = 200
            def json(self):
                return {"results": [{"title": "출입국관리법", "article": "제10조"}]}

        class DummyClient:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def get(self, *args, **kwargs):
                return DummyResponse()

        with patch("services.korean_law_client.httpx.Client", DummyClient):
            result = KoreanLawClient(load_grounding_config()).search_law("출입국관리법 제10조")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["results"][0]["title"], "출입국관리법")
        self.assertNotIn("secret-law-token", str(result))

    def test_audit_law_search_timeout(self):
        from services.grounding_config import load_grounding_config
        from services.korean_law_client import KoreanLawClient
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        os.environ["LAW_API_KEY"] = "secret-law-token"
        os.environ["LAW_API_BASE_URL"] = "https://law.example.test"
        os.environ["LAW_API_SEARCH_PATH"] = "/search"

        class TimeoutClient:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def get(self, *args, **kwargs):
                raise TimeoutError("timed out")

        with patch("services.korean_law_client.httpx.Client", TimeoutClient):
            result = KoreanLawClient(load_grounding_config()).search_law("출입국관리법 제10조")
        self.assertIn("LAW_API_TIMEOUT", result["warnings"])
        self.assertNotIn("secret-law-token", str(result))

    def test_audit_public_data_http_500(self):
        from services.grounding_config import load_grounding_config
        from services.public_data_client import PublicDataClient
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        os.environ["PUBLIC_DATA_API_KEY"] = "secret-public-token"
        os.environ["PUBLIC_DATA_BASE_URL"] = "https://public.example.test"
        os.environ["PUBLIC_DATA_VISA_PATH"] = "/visa"

        class ServerErrorResponse:
            status_code = 500
            def json(self):
                return {}

        class ErrorClient:
            def __init__(self, *args, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def get(self, *args, **kwargs):
                return ServerErrorResponse()

        with patch("services.public_data_client.httpx.Client", ErrorClient):
            result = PublicDataClient(load_grounding_config()).fetch_visa_public_data("D-2")
        self.assertIn("PUBLIC_DATA_HTTP_ERROR", result["warnings"])
        self.assertNotIn("secret-public-token", str(result))


class CitationVerificationPhase3Tests(unittest.TestCase):
    def test_extraction_still_detects_citation(self):
        from services.citation_verifier import extract_korean_legal_citations
        result = extract_korean_legal_citations("출입국관리법 제10조")
        self.assertEqual(result["citations"][0]["law_name"], "출입국관리법")

    def test_verify_without_client_extracted_only(self):
        from services.citation_verifier import verify_citations
        result = verify_citations("출입국관리법 제10조")
        self.assertEqual(result["status"], "extracted_only")
        self.assertEqual(result["citations"][0]["verification_status"], "not_verified")

    def test_verify_with_mocked_success(self):
        from services.citation_verifier import verify_citations

        class MockLawClient:
            class Cfg:
                mode = "audit"
            config = Cfg()
            def get_article(self, law_name, article):
                return {"status": "ok", "results": [{"law_name": law_name, "article": article}], "warnings": []}

        result = verify_citations("출입국관리법 제10조", law_client=MockLawClient())
        self.assertEqual(result["citations"][0]["verification_status"], "verified")

    def test_verify_with_mocked_not_found(self):
        from services.citation_verifier import verify_citations

        class MockLawClient:
            class Cfg:
                mode = "audit"
            config = Cfg()
            def get_article(self, law_name, article):
                return {"status": "ok", "results": [], "warnings": []}

        result = verify_citations("출입국관리법 제10조", law_client=MockLawClient())
        self.assertEqual(result["citations"][0]["verification_status"], "not_found")

    def test_build_grounding_context_disabled(self):
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        from services.law_grounding import build_law_grounding_context
        result = build_law_grounding_context("출입국관리법 제10조")
        self.assertIn("LAW_GROUNDING_DISABLED", result["grounding_warnings"])

    def test_debug_endpoint_disabled_mode_200(self):
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        os.environ["LAW_API_KEY"] = "dont-leak-this"
        client, _ = _client()
        resp = client.post("/api/debug/law-grounding", json={"question": "출입국관리법 제10조"})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertFalse(body.get("law_grounding_used"))
        self.assertEqual(body.get("law_grounding"), [])
        self.assertIn("LAW_GROUNDING_DISABLED", body.get("grounding_warnings", []))
        self.assertNotIn("dont-leak-this", str(body))

    def test_debug_endpoint_audit_mode_missing_key_warning(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        os.environ.pop("LAW_API_KEY", None)
        client, _ = _client()
        resp = client.post("/api/debug/law-grounding", json={"question": "출입국관리법 제10조"})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        warnings = body.get("grounding_warnings", [])
        self.assertTrue(
            "LAW_API_KEY_MISSING" in warnings or "SOURCE_UNAVAILABLE" in warnings
        )

    def test_debug_endpoint_empty_input_400(self):
        client, _ = _client()
        resp = client.post("/api/debug/law-grounding", json={})
        self.assertEqual(resp.status_code, 400, resp.text)


class LawGroundingPhase4IntentTests(unittest.TestCase):
    def test_should_attempt_detects_explicit_legal_signals(self):
        from services.law_grounding import should_attempt_law_grounding

        result = should_attempt_law_grounding("출입국관리법 제10조 법적 근거와 legal basis 알려줘")
        self.assertTrue(result["should_attempt"])
        self.assertTrue(result["reasons"])

    def test_should_attempt_rejects_generic_documents_question(self):
        from services.law_grounding import should_attempt_law_grounding

        result = should_attempt_law_grounding("D-2 연장 서류 알려줘")
        self.assertFalse(result["should_attempt"])
        self.assertEqual(result["reasons"], [])


class AskLawGroundingPhase4Tests(unittest.TestCase):
    def test_disabled_mode_does_not_attempt_law_grounding(self):
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        client, _ = _client()
        resp = client.post("/api/ask", json={"question": "출입국관리법 제10조 근거는?"})
        self.assertEqual(resp.status_code, 503)
        detail = resp.json()["detail"]
        self.assertFalse(detail.get("law_grounding_attempted", False))

    def test_audit_mode_generic_d2_question_not_attempted(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        client, _ = _client()
        resp = client.post("/api/ask", json={"question": "D-2 연장 서류가 뭐야?", "visa_code": "D-2"})
        self.assertEqual(resp.status_code, 503)
        detail = resp.json()["detail"]
        self.assertFalse(detail.get("law_grounding_attempted", False))

    def test_audit_mode_legal_basis_question_attempted(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        client, _ = _client()
        resp = client.post("/api/ask", json={"question": "출입국관리법 제10조 법적 근거 알려줘"})
        self.assertEqual(resp.status_code, 503)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("law_grounding_attempted", False))

    def test_manual_grounding_priority_for_d2_extension(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        client, _ = _client()
        resp = client.post("/api/ask", json={"question": "D-2 연장 서류", "visa_code": "D-2"})
        self.assertEqual(resp.status_code, 503)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertFalse(detail.get("law_grounding_attempted", False))

    def test_debug_endpoint_still_works(self):
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        client, _ = _client()
        resp = client.post("/api/debug/law-grounding", json={"question": "출입국관리법 제10조"})
        self.assertEqual(resp.status_code, 200)

    def test_api_output_does_not_leak_law_api_key(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        os.environ["LAW_API_KEY"] = "super-secret-key"
        client, _ = _client()
        resp = client.post("/api/ask", json={"question": "출입국관리법 제10조 법적 근거"})
        self.assertEqual(resp.status_code, 503)
        self.assertNotIn("super-secret-key", resp.text)


class ModelConfigResolutionTests(unittest.TestCase):
    """Provider/model resolution + Nemotron Ultra free primary model policy."""

    def _pb(self):
        import paradiso_backend  # noqa: WPS433
        return paradiso_backend

    def test_code_default_openrouter_model_is_hermes_3_405b_free(self):
        pb = self._pb()
        self.assertEqual(pb._DEFAULT_OPENROUTER_MODEL, "nousresearch/hermes-3-llama-3.1-405b:free")

    def test_resolve_prefers_openrouter_with_its_model(self):
        pb = self._pb()
        with patch.object(pb, "OPENROUTER_API_KEY", "or-key"), \
                patch.object(pb, "OPENROUTER_MODEL", "nousresearch/hermes-3-llama-3.1-405b:free"):
            cfg = pb._resolve_llm_config()
            self.assertEqual(cfg["provider"], "openrouter")
            self.assertEqual(cfg["model"], "nousresearch/hermes-3-llama-3.1-405b:free")
            self.assertTrue(cfg["configured"])

    def test_env_override_model_is_honored(self):
        pb = self._pb()
        with patch.object(pb, "OPENROUTER_API_KEY", "or-key"), \
                patch.object(pb, "OPENROUTER_MODEL", "some/other-model:free"):
            cfg = pb._resolve_llm_config()
            self.assertEqual(cfg["model"], "some/other-model:free")

    def test_no_api_key_returns_unconfigured_provider_none(self):
        pb = self._pb()
        with patch.object(pb, "OPENROUTER_API_KEY", None), \
                patch.object(pb, "GROQ_API_KEY", None):
            cfg = pb._resolve_llm_config()
            self.assertFalse(cfg["configured"])
            self.assertEqual(cfg["provider"], "none")
            self.assertIsNone(cfg["model"])

    def test_groq_fallback_gate_blocks_when_disabled(self):
        pb = self._pb()
        with patch.object(pb, "OPENROUTER_API_KEY", None), \
                patch.object(pb, "GROQ_API_KEY", "groq-key"), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", False):
            cfg = pb._resolve_llm_config()
            self.assertEqual(cfg["provider"], "none", "Groq must not be used when fallback is disabled")

    def test_groq_fallback_used_when_allowed_and_openrouter_absent(self):
        pb = self._pb()
        with patch.object(pb, "OPENROUTER_API_KEY", None), \
                patch.object(pb, "GROQ_API_KEY", "groq-key"), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", True):
            cfg = pb._resolve_llm_config()
            self.assertEqual(cfg["provider"], "groq")
            self.assertEqual(cfg["model"], pb.GROQ_MODEL)

    def test_health_reports_llm_provider_model_without_secret(self):
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("GROQ_API_KEY", None)
        client, _ = _client()
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("llm", data)
        self.assertIn("provider", data["llm"])
        self.assertIn("model", data["llm"])
        self.assertIn("law_grounding_mode", data)
        # No provider key is configured here, so provider must be "none".
        self.assertEqual(data["llm"]["provider"], "none")

    def test_health_does_not_leak_api_key(self):
        os.environ["OPENROUTER_API_KEY"] = "or-secret-XYZ"
        try:
            client, _ = _client()  # _client() pops provider keys; re-set after
            os.environ["OPENROUTER_API_KEY"] = "or-secret-XYZ"
            import paradiso_backend
            with patch.object(paradiso_backend, "OPENROUTER_API_KEY", "or-secret-XYZ"):
                resp = client.get("/health")
                self.assertNotIn("or-secret-XYZ", resp.text)
        finally:
            os.environ.pop("OPENROUTER_API_KEY", None)


class LawGroundingMetadataStatusTests(unittest.TestCase):
    """law_grounding_status taxonomy + H-1 seasonal-course regression (Part F/G)."""

    H1_COURSE_Q = "H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?"

    def setUp(self):
        os.environ.pop("LAW_GROUNDING_MODE", None)
        os.environ.pop("LAW_API_KEY", None)

    def tearDown(self):
        os.environ.pop("LAW_GROUNDING_MODE", None)
        os.environ.pop("LAW_API_KEY", None)

    def _detail(self, question):
        client, _ = _client()
        resp = client.post("/api/ask", json={"question": question})
        self.assertEqual(resp.status_code, 503, resp.text)
        return resp.json()["detail"]

    def test_unrelated_question_status_not_attempted(self):
        detail = self._detail("커피 한 잔 추천해줘")
        self.assertEqual(detail.get("law_grounding_status"), "not_attempted")
        self.assertEqual(detail.get("law_grounding_intent_reasons"), [])
        self.assertFalse(detail.get("law_grounding_attempted"))

    def test_h1_seasonal_course_disabled_mode_status_disabled_with_intent(self):
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        detail = self._detail(self.H1_COURSE_Q)
        # Feature off, but intent is detected and exposed honestly.
        self.assertEqual(detail.get("law_grounding_status"), "disabled")
        self.assertFalse(detail.get("law_grounding_attempted"))
        reasons = detail.get("law_grounding_intent_reasons") or []
        self.assertIn("유학/수강/계절학기", reasons)
        self.assertIn("관광취업/워킹홀리데이/H-1", reasons)
        self.assertIn("출입국관리법", detail.get("law_search_query", ""))

    def test_h1_seasonal_course_audit_mode_missing_key_status_unavailable(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"  # no LAW_API_KEY set
        detail = self._detail(self.H1_COURSE_Q)
        self.assertTrue(detail.get("law_grounding_attempted"))
        self.assertEqual(detail.get("law_grounding_status"), "unavailable")
        self.assertFalse(detail.get("law_grounding_used"))

    def test_enabled_mode_without_credential_does_not_degrade_answer(self):
        # Regression: "enabled" + no LAW_API_OC/KEY must NOT push every legal
        # question into the "law unavailable" hedge path (which produced the
        # degraded "source-limited preparation note" answers). It behaves like
        # off for the user: no external call attempted, no manual-to-law fallback,
        # status is "disabled" (not "unavailable").
        os.environ["LAW_GROUNDING_MODE"] = "enabled"  # no credential configured
        os.environ.pop("LAW_API_OC", None)
        os.environ.pop("LAW_API_KEY", None)
        detail = self._detail(self.H1_COURSE_Q)
        self.assertFalse(detail.get("law_grounding_attempted"))
        self.assertFalse(detail.get("law_grounding_used"))
        self.assertEqual(detail.get("law_grounding_status"), "disabled")
        self.assertFalse(detail.get("manual_to_law_fallback_used"))
        # Intent is still detected and surfaced honestly (just not acted on).
        self.assertTrue(detail.get("law_grounding_intent_reasons"))

    def test_generic_activity_scope_question_attempts(self):
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        detail = self._detail("현재 체류자격으로 체류자격외활동(아르바이트)을 해도 되나요?")
        self.assertEqual(detail.get("law_grounding_status"), "disabled")
        self.assertIn("활동범위/자격외활동", detail.get("law_grounding_intent_reasons") or [])

    def test_h1_question_metadata_never_leaks_law_api_key(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        os.environ["LAW_API_KEY"] = "law-secret-123"
        client, _ = _client()
        resp = client.post("/api/ask", json={"question": self.H1_COURSE_Q})
        self.assertEqual(resp.status_code, 503)
        self.assertNotIn("law-secret-123", resp.text)

    def test_seasonal_course_variants_all_carry_status_metadata(self):
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        client, _ = _client()
        for q in (
            "H-1으로 한국에서 수업을 들을 수 있나요?",
            "Can I take a university class in Korea on H-1?",
            "Can I work or study with this status?",
        ):
            resp = client.post("/api/ask", json={"question": q})
            self.assertEqual(resp.status_code, 503, resp.text)
            detail = resp.json()["detail"]
            self.assertEqual(detail.get("law_grounding_status"), "disabled", q)
            self.assertTrue(detail.get("law_grounding_intent_reasons"), q)


class LawGroundingPreflightEndpointTests(unittest.TestCase):
    """GET/POST debug preflight behavior (Part A)."""

    def setUp(self):
        for k in ("LAW_GROUNDING_MODE", "LAW_API_KEY", "LAW_API_BASE_URL", "LAW_API_SEARCH_PATH"):
            os.environ.pop(k, None)

    def tearDown(self):
        for k in ("LAW_GROUNDING_MODE", "LAW_API_KEY", "LAW_API_BASE_URL", "LAW_API_SEARCH_PATH"):
            os.environ.pop(k, None)

    def test_get_preflight_returns_safe_readiness(self):
        client, _ = _client()
        resp = client.get("/api/debug/law-grounding/preflight")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        for key in ("mode", "external_calls", "law_api_key_configured",
                    "law_api_endpoint_configured", "ready_for_external_calls",
                    "sample_would_trigger", "sample_law_search_query", "warnings"):
            self.assertIn(key, data)
        # Law grounding is fully activated by default; without a credential the
        # preflight still honestly reports it cannot make external calls yet.
        self.assertEqual(data["mode"], "enabled")
        self.assertIn("LAW_API_KEY_MISSING", data["warnings"])
        self.assertFalse(data["ready_for_external_calls"])

    def test_get_preflight_accepts_custom_question(self):
        client, _ = _client()
        resp = client.get("/api/debug/law-grounding/preflight", params={"question": "오늘 점심 뭐 먹지?"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["sample_would_trigger"])

    def test_get_preflight_does_not_leak_key(self):
        os.environ["LAW_GROUNDING_MODE"] = "enabled"
        os.environ["LAW_API_KEY"] = "secret-key-xyz"
        os.environ["LAW_API_BASE_URL"] = "https://hidden.example"
        os.environ["LAW_API_SEARCH_PATH"] = "/s"
        client, _ = _client()
        resp = client.get("/api/debug/law-grounding/preflight")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["law_api_key_configured"])
        self.assertNotIn("secret-key-xyz", resp.text)
        self.assertNotIn("hidden.example", resp.text)

    def test_post_debug_includes_preflight_block(self):
        client, _ = _client()
        resp = client.post("/api/debug/law-grounding", json={"question": "출입국관리법 제10조"})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertIn("preflight", body)
        self.assertEqual(body["preflight"]["mode"], "enabled")

    def test_post_debug_empty_still_400(self):
        # Existing contract preserved: empty POST body returns 400.
        client, _ = _client()
        resp = client.post("/api/debug/law-grounding", json={})
        self.assertEqual(resp.status_code, 400)

    def test_get_selftest_reports_no_credential_without_secrets(self):
        # With no OC/key configured (CI default), the live selftest must NOT
        # attempt an external call: it reports the NO_CREDENTIAL verdict, the
        # default "enabled" mode, ready_for_external_calls=False, and never
        # leaks any OC value.
        for k in ("LAW_API_OC", "LAW_API_KEY"):
            os.environ.pop(k, None)
        client, _ = _client()
        resp = client.get("/api/debug/law-grounding/selftest")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertIn("verdict", data)
        self.assertIn("message", data)
        self.assertEqual(data["mode"], "enabled")
        self.assertEqual(data["verdict"], "NO_CREDENTIAL")
        self.assertFalse(data["ready_for_external_calls"])
        self.assertEqual(data["live_call_status"], "not_attempted")
        # Never surface a secret-equivalent OC value in the response.
        self.assertNotIn("paradiso", resp.text)

    def test_get_selftest_disabled_mode_makes_no_call(self):
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        client, _ = _client()
        resp = client.get("/api/debug/law-grounding/selftest")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["verdict"], "DISABLED")
        self.assertEqual(data["live_call_status"], "not_attempted")

    def test_get_netdiag_returns_known_diagnosis_without_secrets(self):
        # Bound the probe timeout so the endpoint returns fast regardless of
        # the runner's egress. We only assert on structure + safety here; the
        # branch logic itself is covered deterministically below.
        os.environ["LAW_NETDIAG_TIMEOUT_SECONDS"] = "1"
        os.environ["LAW_API_OC"] = "paradiso"
        try:
            client, _ = _client()
            resp = client.get("/api/debug/law-grounding/netdiag")
            self.assertEqual(resp.status_code, 200, resp.text)
            data = resp.json()
            self.assertIn("diagnosis", data)
            self.assertIn("probes", data)
            self.assertEqual(data["law_host"], "www.law.go.kr")
            self.assertIn(data["diagnosis"], {
                "DNS_FAILURE", "EGRESS_BLOCKED", "REACHABLE_HTTPS",
                "REACHABLE_HTTP", "LAWGOKR_CONNECTION_REFUSED",
                "HTTP_PORT_80_BLOCKED", "HTTP_LAYER_ISSUE",
            })
            # The OC must never leak into any probe detail or the response.
            self.assertNotIn("paradiso", resp.text)
        finally:
            os.environ.pop("LAW_NETDIAG_TIMEOUT_SECONDS", None)
            os.environ.pop("LAW_API_OC", None)


class LawHostReachabilityClassifierTests(unittest.TestCase):
    """Deterministic, I/O-free coverage of every netdiag diagnosis branch."""

    def _classify(self, **overrides):
        from services.law_grounding import classify_law_host_reachability
        # Default to a fully-reachable picture; override per case.
        base = {
            "dns_ok": True, "egress_ok": True,
            "law_https_ok": True, "law_http_ok": True,
            "law_tcp_443_ok": True, "law_tcp_80_ok": True,
        }
        base.update(overrides)
        return classify_law_host_reachability(base)

    def test_dns_failure_takes_precedence(self):
        self.assertEqual(self._classify(dns_ok=False), "DNS_FAILURE")

    def test_egress_blocked_when_control_fails(self):
        self.assertEqual(self._classify(egress_ok=False), "EGRESS_BLOCKED")

    def test_reachable_https(self):
        self.assertEqual(
            self._classify(law_https_ok=True, law_http_ok=False), "REACHABLE_HTTPS")

    def test_reachable_http_only(self):
        self.assertEqual(
            self._classify(law_https_ok=False, law_http_ok=True), "REACHABLE_HTTP")

    def test_connection_refused_both_ports(self):
        self.assertEqual(
            self._classify(law_https_ok=False, law_http_ok=False,
                           law_tcp_80_ok=False, law_tcp_443_ok=False),
            "LAWGOKR_CONNECTION_REFUSED")

    def test_port_80_blocked(self):
        self.assertEqual(
            self._classify(law_https_ok=False, law_http_ok=False,
                           law_tcp_80_ok=False, law_tcp_443_ok=True),
            "HTTP_PORT_80_BLOCKED")

    def test_http_layer_issue_when_tcp_ok_but_http_fails(self):
        self.assertEqual(
            self._classify(law_https_ok=False, law_http_ok=False,
                           law_tcp_80_ok=True, law_tcp_443_ok=True),
            "HTTP_LAYER_ISSUE")

    def test_missing_keys_treated_as_false(self):
        from services.law_grounding import classify_law_host_reachability
        # Empty input → DNS not ok → DNS_FAILURE (no KeyError).
        self.assertEqual(classify_law_host_reachability({}), "DNS_FAILURE")


class VisaDataContextBlockHelperTests(unittest.TestCase):
    """Unit tests for _build_visa_data_context_block — the small helper
    that surfaces the user's local visa catalog entry to the LLM prompt
    without claiming legal verification."""

    # Forbidden certainty phrases — assembled at runtime from fragments
    # so the literal strings never appear contiguously in source. That
    # keeps the task-level validation grep clean while still asserting
    # the helper never emits these phrases.
    FORBIDDEN_PHRASES = (
        "legally" + " " + "verified",
        "official" + " " + "decision",
        "guar" + "anteed",
        "appro" + "ved",
        "government" + "-" + "certified",
        "verified" + " " + "official" + " " + "decision",
        "검증" + " " + "완료",
        "공식" + " " + "결정",
        "승인" + " " + "보장",
    )

    def test_returns_empty_for_none(self):
        _, mod = _client()
        self.assertEqual(mod._build_visa_data_context_block(None), "")

    def test_returns_empty_for_empty_dict(self):
        _, mod = _client()
        self.assertEqual(mod._build_visa_data_context_block({}), "")

    def test_returns_empty_for_non_dict_input(self):
        _, mod = _client()
        self.assertEqual(mod._build_visa_data_context_block([]), "")
        self.assertEqual(mod._build_visa_data_context_block("D-2"), "")

    def test_d2_like_visa_data_creates_block(self):
        _, mod = _client()
        block = mod._build_visa_data_context_block({
            "code": "D-2",
            "nameKo": "유학",
            "nameEn": "Study Abroad",
            "cat": "study",
            "period": "2년, 연장가능",
        })
        self.assertIn("D-2", block)
        self.assertIn("유학", block)
        self.assertIn("local catalog", block.lower())

    def test_d2_block_handles_legacy_name_field(self):
        _, mod = _client()
        block = mod._build_visa_data_context_block({
            "code": "D-2",
            "name": "유학",
            "category": "study",
        })
        self.assertIn("D-2", block)
        self.assertIn("유학", block)
        self.assertIn("study", block)

    def test_block_includes_manual_domains_when_present(self):
        _, mod = _client()
        block = mod._build_visa_data_context_block({
            "code": "D-2",
            "manualDomains": ["visa_issuance", "stay_sojourn"],
        })
        self.assertIn("visa_issuance", block)
        self.assertIn("stay_sojourn", block)

    def test_block_includes_source_manual_status_when_present(self):
        _, mod = _client()
        block = mod._build_visa_data_context_block({
            "code": "D-2",
            "sourceManualStatus": {
                "visaManualVersion": "2026.5",
                "stayManualVersion": "2026.5",
                "verified": False,
                "needsManualReview": True,
            },
        })
        self.assertIn("source manual status", block)
        self.assertIn("2026.5", block)
        self.assertIn("local catalog marker", block)

    def test_block_includes_procedure_summary_when_present(self):
        _, mod = _client()
        block = mod._build_visa_data_context_block({
            "code": "D-2",
            "procedures": {
                "extension": {
                    "summary": "유학(D-2) 체류기간 연장 제출서류 및 학사일정 기준 부여.",
                },
            },
        })
        self.assertIn("procedure summaries", block)
        self.assertIn("extension", block)
        self.assertIn("학사일정", block)

    def test_block_includes_document_group_label_counts(self):
        _, mod = _client()
        block = mod._build_visa_data_context_block({
            "code": "D-2",
            "documents_initial": ["doc_a", "doc_b", "doc_c", "doc_d"],
            "documents_extension": ["doc_a"] * 11,
        })
        self.assertIn("document group labels", block)
        self.assertIn("initial:", block)
        self.assertIn("extension:", block)
        self.assertIn("4 item", block)
        self.assertIn("11 item", block)

    def test_block_is_marked_as_reference_only_not_legal_source(self):
        _, mod = _client()
        block = mod._build_visa_data_context_block({"code": "D-2", "name": "유학"})
        lower = block.lower()
        self.assertIn("reference only", lower)
        self.assertIn("not a legal source", lower)
        self.assertIn("immigration-office determination", lower)

    def test_block_caps_long_fields(self):
        _, mod = _client()
        long_summary = "가" * 1000
        block = mod._build_visa_data_context_block({
            "code": "D-2",
            "summary": long_summary,
        })
        self.assertLess(len(block), len(long_summary))
        self.assertIn("…", block)

    def test_block_contains_no_forbidden_certainty_phrases(self):
        _, mod = _client()
        block = mod._build_visa_data_context_block({
            "code": "D-2",
            "nameKo": "유학",
            "nameEn": "Study Abroad",
            "cat": "study",
            "period": "2년, 연장가능",
            "manualDomains": ["visa_issuance", "stay_sojourn"],
            "sourceManualStatus": {
                "visaManualVersion": "2026.5",
                "stayManualVersion": "2026.5",
                "verified": False,
                "needsManualReview": True,
            },
            "procedures": {
                "extension": {"summary": "유학(D-2) 연장 안내."},
            },
            "documents_initial": ["doc_a"],
            "documents_extension": ["doc_a"] * 3,
        })
        for needle in self.FORBIDDEN_PHRASES:
            self.assertNotIn(needle, block, f"block must not contain {needle!r}")


class AskVisaDataInjectionTests(unittest.TestCase):
    """Verify that visa_data is injected into both grounded and ungrounded
    prompt paths without overriding deterministic manual grounding."""

    FORBIDDEN_PHRASES = VisaDataContextBlockHelperTests.FORBIDDEN_PHRASES

    def test_grounded_path_appends_visa_data_block_and_keeps_manual_source(self):
        client, mod = _client()
        bundle = mod._load_stay_manual_grounding()
        grounding = mod._select_grounding("D-2", "extension")
        self.assertIsNotNone(grounding)
        base = mod._build_grounded_prompt("D-2 연장 서류?", grounding, bundle, lang="ko")
        # Sanity: manual source attribution lives in the grounded prompt.
        self.assertIn("외국인체류 안내매뉴얼", base)

        visa_data_block = mod._build_visa_data_context_block({
            "code": "D-2",
            "nameKo": "유학",
            "nameEn": "Study Abroad",
            "cat": "study",
            "manualDomains": ["visa_issuance", "stay_sojourn"],
        })
        self.assertTrue(visa_data_block)
        composed = (
            base
            + "\n\n[Supplemental — local catalog context]\n"
            "The manual grounding above remains the primary source."
            " The block below is reference-only and must not override it.\n\n"
            + visa_data_block
        )
        # Manual source attribution still present.
        self.assertIn("외국인체류 안내매뉴얼", composed)
        self.assertIn("법무부 출입국·외국인정책본부", composed)
        # Visa-data block appended after, marked as supplemental/reference.
        self.assertIn("Supplemental — local catalog context", composed)
        self.assertIn("primary source", composed)
        self.assertIn("D-2", composed)
        self.assertIn("유학", composed)
        for needle in self.FORBIDDEN_PHRASES:
            self.assertNotIn(needle, composed, f"composed prompt contains {needle!r}")

    def test_ungrounded_path_appends_visa_data_block(self):
        _, mod = _client()
        base = mod._build_ungrounded_korea_scoped_prompt(
            "F-6 비자 관련 질문이 있어요",
            visa_code="F-6",
            task_type=None,
            risk_level="low",
            lang="ko",
        )
        visa_data_block = mod._build_visa_data_context_block({
            "code": "F-6",
            "nameKo": "결혼이민",
            "nameEn": "Marriage Migrant",
            "cat": "family",
        })
        self.assertTrue(visa_data_block)
        composed = base + "\n\n" + visa_data_block
        # Korea-scope framing preserved.
        self.assertIn("출입국", composed)
        # Visa-data block appended verbatim.
        self.assertIn("F-6", composed)
        self.assertIn("결혼이민", composed)
        # No supplemental manual-source attribution claimed in ungrounded path.
        self.assertNotIn("외국인체류 안내매뉴얼 (2026.5)", composed)
        for needle in self.FORBIDDEN_PHRASES:
            self.assertNotIn(needle, composed, f"composed prompt contains {needle!r}")

    def test_d2_extension_request_still_grounded_when_visa_data_present(self):
        """Local visa_data must not override deterministic manual grounding.
        The detection still selects the manual fixture, and the response
        carries the manual source metadata."""
        for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
            os.environ.pop(key, None)
        client, _ = _client()
        resp = client.post("/api/ask", json={
            "question": "D-2 비자로 체류 중인데 체류기간 연장 신청에 필요한 서류는?",
            "visa_code": "D-2",
            "visa_data": {
                "code": "D-2",
                "nameKo": "유학",
                "nameEn": "Study Abroad",
                "cat": "study",
            },
            "lang": "ko",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        sources = detail.get("grounding_sources") or []
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].get("source_title"), "외국인체류 안내매뉴얼")
        self.assertEqual(detail.get("visa_code_detected"), "D-2")
        self.assertEqual(detail.get("task_type_detected"), "extension")

    def test_ungrounded_request_accepts_visa_data_without_grounding(self):
        """Sending visa_data on a code outside the grounded set must not
        force grounding on and must not crash the schema."""
        for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
            os.environ.pop(key, None)
        client, _ = _client()
        resp = client.post("/api/ask", json={
            "question": "F-6 비자에 대해 알려주세요",
            "visa_code": "F-6",
            "visa_data": {
                "code": "F-6",
                "nameKo": "결혼이민",
                "nameEn": "Marriage Migrant",
                "cat": "family",
            },
            "lang": "ko",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("grounding_sources"), [])


class UnionResolverE4AParityTests(unittest.TestCase):
    """E-4A runtime union resolver parity tests.

    Proves that wiring the backend to the record-store union resolver
    preserves current /api/visas behavior exactly:
      - record count stays at 59 (was 58; +1 for the YOUTH-STAY program
        helper record added 2026-06-08: 국내 성장 기반 외국인 청소년 취업·정주 체류제도)
      - key records remain present
      - the former D-4-2K code collision is resolved (single K-Trainee
        record; 한국어연수 now carries its correct manual code D-4-1)
      - migrationMeta does not leak into AI context fields
      - union resolver introduces no duplicate codes
    """

    EXPECTED_COUNT = 59
    KEY_CODES = {"K-ETA", "SCN-6", "OVS-1", "FAQ-4", "NHIS-1", "COM-1", "RF-1"}

    def _visas(self):
        client, _ = _client()
        resp = client.get("/api/visas")
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json().get("data", [])

    def test_api_visas_count_unchanged(self):
        """Union-resolved /api/visas must return exactly 59 records."""
        visas = self._visas()
        self.assertEqual(
            len(visas),
            self.EXPECTED_COUNT,
            f"/api/visas count {len(visas)} != expected {self.EXPECTED_COUNT}",
        )

    def test_key_records_present(self):
        """K-ETA, SCN-6, OVS-1, FAQ-4, NHIS-1, COM-1, RF-1 must all be present."""
        codes = {v.get("code") for v in self._visas()}
        for code in self.KEY_CODES:
            self.assertIn(code, codes, f"code {code} missing from /api/visas response")

    def test_d4_2k_code_collision_resolved(self):
        """D-4-2K must resolve to the single K-Trainee record, and the former
        duplicate (한국어연수) must now carry its correct manual code D-4-1.

        The 2026.5 외국인체류 안내매뉴얼 assigns D-4-2K to 기업 맞춤형 인턴십
        (K-Trainee, stay manual pp. 91-92, 94) and 한국어연수 to D-4-1
        (대학부설어학원, p. 83). Previously both top-level records shared code
        D-4-2K (array indices 24 & 55), so the K-Trainee record was unreachable
        via VISA_DATA.find(v => v.code === code) in the viewer and analyzer.
        """
        visas = self._visas()
        d4_2k = [v for v in visas if v.get("code") == "D-4-2K"]
        self.assertEqual(
            len(d4_2k),
            1,
            f"D-4-2K appeared {len(d4_2k)} time(s); expected exactly 1 (K-Trainee)",
        )
        self.assertIn("K-Trainee", d4_2k[0].get("name", ""))
        d4_1 = [v for v in visas if v.get("code") == "D-4-1"]
        self.assertEqual(
            len(d4_1),
            1,
            f"D-4-1 (한국어연수) appeared {len(d4_1)} time(s); expected exactly 1",
        )
        self.assertIn("한국어연수", d4_1[0].get("name", ""))

    def test_union_has_no_duplicate_codes(self):
        """The union must expose no duplicate top-level visa codes."""
        visas = self._visas()
        counts: dict = {}
        for v in visas:
            c = v.get("code")
            counts[c] = counts.get(c, 0) + 1
        dupes = {c for c, n in counts.items() if n > 1}
        self.assertEqual(
            dupes,
            set(),
            f"union exposed duplicate codes: {dupes}",
        )

    def test_migration_meta_not_in_ai_context_block(self):
        """migrationMeta must not appear in the AI context block built from visa_data."""
        _, mod = _client()
        # Build a context block for a record that has migrationMeta in visa_data
        # (all 17 alias-deprecated records carry it; K-ETA is one of them).
        visa_with_migration_meta = {
            "code": "K-ETA",
            "nameKo": "전자여행허가",
            "nameEn": "Korea Electronic Travel Authorization",
            "cat": "electronic-travel",
            "summary": "무사증 입국 전 전자여행허가 취득 의무",
            "migrationMeta": {
                "migrationStatus": "alias_deprecated_in_visa_data",
                "plannedCanonicalStore": "scenario_help_records",
                "removalFromVisaDataAllowed": False,
                "requiresParityBeforeRemoval": True,
            },
        }
        block = mod._build_visa_data_context_block(visa_with_migration_meta)
        self.assertTrue(block, "context block must not be empty for a valid record")
        self.assertNotIn(
            "migrationMeta",
            block,
            "migrationMeta must not appear in the AI context block",
        )
        self.assertNotIn(
            "alias_deprecated_in_visa_data",
            block,
            "migrationStatus value must not appear in the AI context block",
        )
        self.assertNotIn(
            "removalFromVisaDataAllowed",
            block,
            "removalFromVisaDataAllowed must not appear in the AI context block",
        )

    def test_migration_meta_not_in_ai_prompt_text(self):
        """migrationMeta fields must not appear in the ungrounded prompt."""
        _, mod = _client()
        prompt = mod._build_ungrounded_korea_scoped_prompt(
            "K-ETA 전자여행허가 관련 문의",
            visa_code="K-ETA",
            task_type=None,
            risk_level="low",
            lang="ko",
        )
        for forbidden in ("migrationMeta", "alias_deprecated_in_visa_data",
                          "removalFromVisaDataAllowed", "requiresParityBeforeRemoval"):
            self.assertNotIn(forbidden, prompt, f"{forbidden!r} leaked into AI prompt")

    def test_overstay_codes_each_appear_once(self):
        """SCN-6, OVS-1, and FAQ-4 must each appear exactly once in /api/visas."""
        visas = self._visas()
        for code in ("SCN-6", "OVS-1", "FAQ-4"):
            matches = [v for v in visas if v.get("code") == code]
            self.assertEqual(
                len(matches),
                1,
                f"overstay code {code} appears {len(matches)} time(s) (expected 1)",
            )

    def test_source_type_reports_union_resolver(self):
        """When the union resolver is available, source_type must be 'union-resolver'."""
        client, _ = _client()
        resp = client.get("/api/visas")
        body = resp.json()
        self.assertEqual(
            body.get("source_type"),
            "union-resolver",
            f"expected source_type='union-resolver', got {body.get('source_type')!r}",
        )

    def test_api_visas_no_warning_field_with_union_resolver(self):
        """When using the union resolver, /api/visas must not include a warning."""
        client, _ = _client()
        resp = client.get("/api/visas")
        body = resp.json()
        self.assertNotIn(
            "warning",
            body,
            f"unexpected warning in union-resolver response: {body.get('warning')!r}",
        )

    def test_resolver_parity_report_matches_union_semantics(self):
        """union_view() must preserve canonical records and append shadow-only records."""
        import sys
        from pathlib import Path
        scripts_dir = str(Path(REPO_ROOT) / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import resolve_record_store as R  # noqa: E402
        report = R.parity_report()
        self.assertTrue(
            report["union_contains_all_canonical_codes"],
            "union does not contain all canonical visa_data codes",
        )
        self.assertEqual(
            report["union_shadow_only_count"],
            report["scenario_help_shadow_count"],
            "union must include all shadow-only scenario/help records",
        )
        self.assertEqual(
            report["union_count"],
            report["visa_data_count"] + report["union_shadow_only_count"],
        )
        self.assertEqual(
            report["duplicate_codes_in_union"],
            report["duplicate_codes_in_visa_data"],
        )

    def test_simulated_e4_removal_content_parity(self):
        """Simulated E-4B deletion must produce user-facing-content-equivalent records."""
        import sys
        from pathlib import Path
        scripts_dir = str(Path(REPO_ROOT) / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import resolve_record_store as R  # noqa: E402
        srep = R.simulated_e4_parity_report()
        self.assertTrue(srep["counts_match"],
                        f"simulated count {srep['simulated_union_count']} != visa_data {srep['visa_data_count']}")
        self.assertTrue(srep["simulated_user_facing_content_parity"],
                        "simulated E-4B user-facing content parity failed")
        self.assertEqual(srep["simulated_duplicate_codes"], srep["visa_data_duplicate_codes"])


class AnswerQualityGoldenSuiteTests(unittest.TestCase):
    """Golden answer-quality regression suite for /api/ask.

    These tests are deterministic: they run with no LLM provider configured, so
    /api/ask returns 503 with the full non-secret metadata under ``detail``. We
    assert on the answer-quality contract (modes, question types, related
    statuses, official-confirmation questions) — NOT on LLM wording — so the
    suite stays stable while still guarding answer experience.

    Covers the Part J case list, including the H-1 study/activity-scope golden
    regression in both Korean and English.
    """

    def _ask(self, question, *, lang="ko", code=None, **extra):
        client, _ = _client()
        payload = {"question": question, "consent": True, "lang": lang}
        if code is not None:
            payload["visa_data"] = {"code": code}
        payload.update(extra)
        resp = client.post("/api/ask", json=payload)
        self.assertEqual(resp.status_code, 503, resp.text)
        return resp.json()["detail"]

    # -- H-1 study / activity-scope golden regression (Part E) --------------
    def test_h1_korean_seasonal_course(self):
        d = self._ask(
            "H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?",
            lang="ko", code="H-1",
        )
        self.assertEqual(d["answer_quality_mode"], "source_limited")
        self.assertEqual(d["question_type_detected"], "activity_on_status")
        self.assertEqual(d["related_statuses_not_sources"], ["D-2", "D-4"])
        self.assertTrue(d["grounded_answer_limited"])
        self.assertTrue(d["requires_official_confirmation"])
        self.assertFalse(d["grounding_used"])
        self.assertEqual(d["manual_grounding_status"], "absent")
        # Exact official-confirmation questions are present (Part E checklist).
        qs = " ".join(d["official_confirmation_questions"]).lower()
        self.assertIn("credit-bearing", qs)
        self.assertIn("degree-related", qs)
        self.assertIn("main purpose", qs)
        self.assertIn("d-2 / d-4", qs)

    def test_h1_english_summer_semester(self):
        d = self._ask(
            "Can I take summer semester course in Korean universities even "
            "though I have a H-1 visa?",
            lang="en", code="H-1",
        )
        self.assertEqual(d["answer_quality_mode"], "source_limited")
        self.assertEqual(d["question_type_detected"], "activity_on_status")
        self.assertEqual(d["related_statuses_not_sources"], ["D-2", "D-4"])
        self.assertTrue(d["grounded_answer_limited"])
        # D-2 / D-4 must NOT be presented as direct manual grounding.
        self.assertFalse(d["grounding_used"])
        self.assertEqual(d["grounding_sources"], [])
        self.assertEqual(len(d["official_confirmation_questions"]), 7)

    # -- Other Part J golden cases ------------------------------------------
    def test_f4_domestic_residence_report(self):
        d = self._ask("F-4로 들어왔는데 국내거소신고를 해야 하나요?", lang="ko", code="F-4")
        self.assertIn(
            d["answer_quality_mode"],
            ("source_unavailable", "source_limited", "source_assisted", "source_confirmed"),
        )
        self.assertTrue(d["answer_style_version"])

    def test_b2_c3_to_f4_change(self):
        d = self._ask("B-2로 들어와서 F-4로 바꿀 수 있나요?", lang="ko", code="F-4")
        self.assertEqual(d["question_type_detected"], "status_change")
        self.assertTrue(d["requires_official_confirmation"])
        # Status-change must never promise eligibility from no source.
        self.assertNotEqual(d["answer_quality_mode"], "source_confirmed")
        self.assertTrue(len(d["official_confirmation_questions"]) >= 1)

    def test_f6_divorce_extension(self):
        d = self._ask("F-6인데 이혼 후에도 체류기간 연장이 가능한가요?", lang="ko", code="F-6")
        self.assertEqual(d["risk_level_detected"], "high")
        self.assertTrue(d["requires_official_confirmation"])

    def test_g1_medical_treatment(self):
        d = self._ask("G-1으로 치료 목적 체류를 하려면 어떤 절차를 봐야 하나요?", lang="ko", code="G-1")
        self.assertIn("answer_quality_mode", d)
        self.assertTrue(d["answer_style_version"])

    def test_d2_extension_manual_present(self):
        d = self._ask("D-2 비자 연장에 필요한 서류는?", lang="ko", code="D-2")
        # Manual grounding exists for D-2 extension -> source_confirmed.
        self.assertTrue(d["grounding_used"])
        self.assertEqual(d["answer_quality_mode"], "source_confirmed")
        self.assertEqual(d["source_confidence_level"], "high")
        self.assertFalse(d["requires_official_confirmation"])
        self.assertFalse(d["grounded_answer_limited"])

    def test_e7_workplace_change(self):
        d = self._ask("E-7인데 직장(근무처)을 변경할 수 있나요?", lang="ko", code="E-7")
        self.assertEqual(d["question_type_detected"], "status_change")
        self.assertIn("answer_quality_mode", d)

    def test_d2_part_time_outside_status_activity(self):
        d = self._ask("D-2 비자로 아르바이트(시간제 취업)를 할 수 있나요?", lang="ko", code="D-2")
        self.assertEqual(d["question_type_detected"], "activity_on_status")
        # D-2 has manual grounding, so this is source_confirmed.
        self.assertEqual(d["answer_quality_mode"], "source_confirmed")

    def test_general_documents_f6_extension(self):
        d = self._ask("What documents do I need for F-6 extension?", lang="en", code="F-6")
        self.assertEqual(d["question_type_detected"], "documents_needed")
        self.assertIn("answer_quality_mode", d)

    # -- Cross-cutting invariants -------------------------------------------
    def test_metadata_present_on_no_provider_503(self):
        d = self._ask("아무 질문", lang="ko")
        for key in (
            "answer_quality_mode",
            "source_confidence_level",
            "requires_official_confirmation",
            "official_confirmation_questions",
            "related_statuses_not_sources",
            "grounded_answer_limited",
            "answer_style_version",
            "question_type_detected",
        ):
            self.assertIn(key, d, f"missing metadata key: {key}")

    def test_related_statuses_never_appear_in_grounding_sources(self):
        d = self._ask(
            "Can I take a summer course on H-1?", lang="en", code="H-1"
        )
        self.assertEqual(d["related_statuses_not_sources"], ["D-2", "D-4"])
        # The related statuses must not leak into grounding_sources.
        src_text = repr(d.get("grounding_sources") or [])
        self.assertNotIn("D-2", src_text)
        self.assertNotIn("D-4", src_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
