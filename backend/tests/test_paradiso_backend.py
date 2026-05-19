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
        self.assertIn(body.get("source_type"), {"backend-data", "repo-root", "explicit"})

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
        self.assertEqual(data.get("source_file"), "docs/source-manuals/2026-05/stay_manual_2026_05.pdf")
        self.assertEqual(data.get("source_title"), "외국인체류 안내매뉴얼")
        self.assertEqual(data.get("source_date"), "2026.5")
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
        self.assertEqual(src.get("source_file"), "docs/source-manuals/2026-05/stay_manual_2026_05.pdf")
        self.assertEqual(src.get("source_title"), "외국인체류 안내매뉴얼")
        self.assertEqual(src.get("source_date"), "2026.5")
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
        self.assertEqual(src.get("source_file"), "docs/source-manuals/2026-05/stay_manual_2026_05.pdf")

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
        self.assertIn("Answer in English.", built)
        self.assertNotIn("한국어로 답하십시오.", built)
        # Korea-specific source attribution still present.
        self.assertIn("외국인체류 안내매뉴얼", built)
        self.assertIn("법무부 출입국·외국인정책본부", built)

    def test_lang_ko_instructs_korean(self):
        built = self._built("ko")
        self.assertIn("한국어로 답하십시오.", built)
        self.assertNotIn("Answer in English.", built)
        self.assertIn("외국인체류 안내매뉴얼", built)

    def test_unknown_lang_falls_back_to_user_language(self):
        built = self._built(None)
        self.assertIn("Answer in the same language as the user's question.", built)
        self.assertNotIn("한국어로 답하십시오.", built)
        self.assertNotIn("Answer in English.", built)
        # Korea-specific source attribution unchanged.
        self.assertIn("외국인체류 안내매뉴얼", built)

    def test_unrecognized_lang_value_also_falls_back(self):
        built = self._built("fr")
        self.assertIn("Answer in the same language as the user's question.", built)

    def test_answer_language_helper_directly(self):
        _, mod = _client()
        self.assertEqual(mod._answer_language_instruction("ko"), "- 한국어로 답하십시오.")
        self.assertEqual(mod._answer_language_instruction("KO"), "- 한국어로 답하십시오.")
        self.assertEqual(mod._answer_language_instruction("en"), "- Answer in English.")
        self.assertEqual(mod._answer_language_instruction("EN"), "- Answer in English.")
        for unknown in (None, "", "fr", "ja", "x"):
            self.assertEqual(
                mod._answer_language_instruction(unknown),
                "- Answer in the same language as the user's question.",
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

    def test_f61_divorce_prompt_forbids_uscis(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("USCIS", built)  # appears in the forbidden-token instruction

    def test_f61_divorce_prompt_forbids_home_office(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("Home Office", built)  # appears in the forbidden-token instruction

    def test_f61_divorce_prompt_forbids_embassy(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("embassy", built)  # appears in the forbidden-token instruction

    def test_f61_divorce_prompt_forbids_consulate(self):
        built = self._build_f61_divorce_prompt()
        self.assertIn("consulate", built)  # appears in the forbidden-token instruction

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

    # ---- Answer-language preservation ----

    def test_ungrounded_prompt_lang_ko(self):
        _, mod = _client()
        built = mod._build_ungrounded_korea_scoped_prompt("질문", lang="ko")
        self.assertIn("한국어로 답하십시오", built)
        self.assertNotIn("Answer in English", built)

    def test_ungrounded_prompt_lang_en(self):
        _, mod = _client()
        built = mod._build_ungrounded_korea_scoped_prompt("question", lang="en")
        self.assertIn("Answer in English", built)
        self.assertNotIn("한국어로 답하십시오", built)

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


class LawPublicDataScaffoldTests(unittest.TestCase):
    def test_default_grounding_config_mode_is_disabled(self):
        os.environ.pop("LAW_GROUNDING_MODE", None)
        os.environ.pop("LAW_GROUNDING_TIMEOUT_SECONDS", None)
        os.environ.pop("LAW_GROUNDING_CACHE_TTL_SECONDS", None)
        from services.grounding_config import load_grounding_config

        cfg = load_grounding_config()
        self.assertEqual(cfg.mode, "disabled")
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

    def test_debug_endpoint_empty_input_400(self):
        client, _ = _client()
        resp = client.post("/api/debug/law-grounding", json={})
        self.assertEqual(resp.status_code, 400, resp.text)


class ControlledAskLawGroundingPhase4Tests(unittest.TestCase):
    def test_legal_intent_detector_positive_and_negative(self):
        from services.law_grounding import should_attempt_law_grounding
        self.assertTrue(should_attempt_law_grounding("출입국관리법 제10조 근거 법령 알려줘")["should_attempt"])
        self.assertFalse(should_attempt_law_grounding("D-2 연장 서류 뭐야")["should_attempt"])

    def test_ask_disabled_mode_not_attempted(self):
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        client, _ = _client()
        resp = client.post("/api/ask", json={"question": "출입국관리법 제10조 근거 법령 알려줘"})
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertFalse(detail.get("law_grounding_attempted"))

    def test_ask_audit_non_legal_not_attempted(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        client, _ = _client()
        resp = client.post("/api/ask", json={"question": "D-2 연장 서류 뭐야"})
        self.assertEqual(resp.status_code, 503, resp.text)
        self.assertFalse(resp.json()["detail"].get("law_grounding_attempted"))

    def test_ask_audit_legal_attempted_with_mocked_unavailable(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        with patch("paradiso_backend.build_law_grounding_context") as mocked_ctx:
            mocked_ctx.return_value = {
                "attempted": True,
                "law_grounding_used": False,
                "law_grounding": [],
                "citation_verification": {"status": "unavailable", "citations": []},
                "grounding_warnings": ["LAW_API_KEY_MISSING"],
                "grounding_sources": [],
            }
            client, _ = _client()
            resp = client.post("/api/ask", json={"question": "법적 근거와 article 기준 알려줘"})
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("law_grounding_attempted"))
        self.assertIn("LAW_API_KEY_MISSING", detail.get("law_grounding_warnings", []))

    def test_manual_grounding_still_priority(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        with patch("paradiso_backend.build_law_grounding_context") as mocked_ctx:
            mocked_ctx.return_value = {
                "attempted": True,
                "law_grounding_used": True,
                "law_grounding": [{"title": "출입국관리법"}],
                "citation_verification": {"status": "ok", "citations": []},
                "grounding_warnings": [],
                "grounding_sources": [{"source_type": "law", "status": "ok"}],
            }
            client, _ = _client()
            resp = client.post("/api/ask", json={"question": "D-2 비자 연장에 필요한 서류는?", "visa_code": "D-2"})
        detail = resp.json()["detail"]
        self.assertTrue(detail.get("grounding_used"))
        self.assertTrue(detail.get("grounding_sources"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
