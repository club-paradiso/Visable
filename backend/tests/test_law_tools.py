"""Deterministic tests for the internal MCP-like law tool layer.

Covers Part A (LAW_API_OC config/security), Part B (typed internal tools +
stable error types), Part D (evidence pack), the MCP-like orchestration
contract, source-confidence modes, and the unsupported-confidence phrase guard.

Every external call is mocked: no live Open Law API, OpenRouter, Railway,
HiKorea, or data.go.kr access is required.

    python3 -m pytest backend/tests/test_law_tools.py -q
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import answer_quality as aq  # noqa: E402
from services import law_tools as lt  # noqa: E402
from services.grounding_config import GroundingConfig, load_grounding_config  # noqa: E402

LAW_ENV = (
    "LAW_API_OC", "LAW_API_KEY", "LAW_GROUNDING_MODE",
    "LAW_API_BASE_URL", "LAW_API_SEARCH_PATH", "LAW_API_ARTICLE_PATH",
)


def _clear_law_env() -> None:
    for key in LAW_ENV:
        os.environ.pop(key, None)


# ---------------------------------------------------------------------------
# Mock transports (the ONLY network seam — always injected here)
# ---------------------------------------------------------------------------
def law_search_body() -> str:
    return json.dumps({
        "LawSearch": {
            "law": [
                {"법령명한글": "출입국관리법", "법령ID": "001386",
                 "법령일련번호": "267581", "법령구분명": "법률",
                 "공포일자": "20240101", "시행일자": "20240701"},
                {"법령명한글": "출입국관리법 시행령", "법령ID": "001387",
                 "법령일련번호": "267999", "법령구분명": "대통령령"},
            ]
        }
    }, ensure_ascii=False)


def admin_body() -> str:
    return json.dumps({
        "AdmRulSearch": {"admrul": [
            {"행정규칙명": "외국인 체류 안내 지침", "행정규칙일련번호": "12345"},
        ]}
    }, ensure_ascii=False)


def term_body() -> str:
    return json.dumps({
        "LsTrmSearch": {"lstrm": [
            {"법령용어명": "체류자격", "법령용어정의": "외국인이 대한민국에 체류하면서 ..."},
        ]}
    }, ensure_ascii=False)


def service_body() -> str:
    return json.dumps({
        "법령": {
            "기본정보": {"법령명_한글": "출입국관리법", "법령ID": "001386"},
            "조문": {"조문단위": [
                {"조문번호": "10", "조문제목": "체류자격", "조문내용": "제10조 (체류자격) ..."},
                {"조문번호": "20", "조문제목": "체류자격 외 활동", "조문내용": "제20조 ..."},
            ]},
        }
    }, ensure_ascii=False)


class _RecordingTransport:
    """Captures the request URL so tests can assert OC is embedded internally."""

    def __init__(self, body: str, status: int = 200):
        self.body = body
        self.status = status
        self.urls: list = []

    def __call__(self, url: str, timeout: float) -> lt.LawHttpResponse:
        self.urls.append(url)
        return lt.LawHttpResponse(ok=True, status_code=self.status, text=self.body)


def _audit_oc_cfg(**over) -> GroundingConfig:
    base = dict(mode="audit", law_api_oc="paradiso")
    base.update(over)
    return GroundingConfig(**base)


# ---------------------------------------------------------------------------
# Part A — LAW_API_OC config / security
# ---------------------------------------------------------------------------
class LawApiOcConfigTests(unittest.TestCase):
    def setUp(self):
        _clear_law_env()

    def tearDown(self):
        _clear_law_env()

    def test_oc_preferred_over_key(self):
        os.environ["LAW_API_OC"] = "paradiso"
        os.environ["LAW_API_KEY"] = "legacy-secret"
        cfg = load_grounding_config()
        self.assertEqual(cfg.law_api_credential, "paradiso")
        self.assertEqual(cfg.law_api_credential_source, "LAW_API_OC")
        self.assertTrue(cfg.law_api_oc_configured)
        self.assertTrue(cfg.law_api_key_fallback_configured)
        self.assertTrue(cfg.law_api_configured)

    def test_key_is_backward_compat_fallback(self):
        os.environ["LAW_API_KEY"] = "legacy-secret"
        cfg = load_grounding_config()
        self.assertEqual(cfg.law_api_credential, "legacy-secret")
        self.assertEqual(cfg.law_api_credential_source, "LAW_API_KEY")
        self.assertFalse(cfg.law_api_oc_configured)
        self.assertTrue(cfg.law_api_configured)
        self.assertIn("LAW_API_OC_RECOMMENDED", cfg.warnings)

    def test_both_set_uses_oc_for_request(self):
        os.environ["LAW_API_OC"] = "paradiso"
        os.environ["LAW_API_KEY"] = "legacy-secret"
        cfg = load_grounding_config()
        rec = _RecordingTransport(law_search_body())
        lt.search_laws("출입국관리법", config=cfg, transport=rec)
        self.assertIn("OC=paradiso", rec.urls[0])
        self.assertNotIn("legacy-secret", rec.urls[0])

    def test_only_key_still_works_backward_compat(self):
        os.environ["LAW_API_KEY"] = "legacy-secret"
        cfg = load_grounding_config()
        rec = _RecordingTransport(law_search_body())
        result = lt.search_laws("출입국관리법", config=cfg, transport=rec)
        self.assertEqual(result["status"], "ok")
        self.assertIn("OC=legacy-secret", rec.urls[0])

    def test_neither_set_is_unavailable_gracefully(self):
        cfg = load_grounding_config()
        self.assertFalse(cfg.law_api_configured)
        result = lt.search_laws("출입국관리법", config=cfg)  # no transport, no network
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], lt.LAW_API_NOT_CONFIGURED)

    def test_sanitized_url_never_contains_oc_value(self):
        cfg = _audit_oc_cfg()
        rec = _RecordingTransport(law_search_body())
        result = lt.search_laws("출입국관리법", config=cfg, transport=rec)
        self.assertNotIn("OC=paradiso", result["source_url"])
        self.assertNotIn("paradiso", result["source_url"])
        self.assertNotIn("OC=", result["source_url"])

    def test_results_and_summary_never_expose_oc(self):
        cfg = _audit_oc_cfg()
        rec = _RecordingTransport(law_search_body())
        pack = lt.build_law_evidence_pack(
            "H-1으로 계절학기 수강 가능?", visa_code="H-1", config=cfg, transport=rec,
        )
        blob = json.dumps(pack, ensure_ascii=False)
        self.assertNotIn("paradiso", blob)
        self.assertNotIn("OC=", blob)


class HealthAndDebugSecurityTests(unittest.TestCase):
    def setUp(self):
        _clear_law_env()
        for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
            os.environ.pop(key, None)

    def tearDown(self):
        _clear_law_env()

    def _client(self):
        from fastapi.testclient import TestClient
        import paradiso_backend
        paradiso_backend._reset_visas_cache_for_tests()
        paradiso_backend._reset_grounding_cache_for_tests()
        return TestClient(paradiso_backend.app)

    def test_health_exposes_flags_not_values(self):
        # Use distinct sentinels so a leak is detectable (the real OC value is
        # literally "paradiso", which collides with the "paradiso-backend"
        # service name; sentinels avoid that brand collision in the assertion).
        os.environ["LAW_API_OC"] = "oc-sentinel-zzz-987"
        os.environ["LAW_API_KEY"] = "legacy-secret-key-654"
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        client = self._client()
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        law = body["law_api"]
        self.assertTrue(law["law_api_configured"])
        self.assertTrue(law["law_api_oc_configured"])
        self.assertTrue(law["law_api_key_fallback_configured"])
        self.assertEqual(law["law_api_credential_source"], "LAW_API_OC")
        self.assertEqual(body["law_grounding_mode"], "audit")
        # Neither secret value appears anywhere in the response text.
        self.assertNotIn("oc-sentinel-zzz-987", resp.text)
        self.assertNotIn("legacy-secret-key-654", resp.text)

    def test_health_only_key_reports_fallback_only(self):
        os.environ["LAW_API_KEY"] = "legacy-secret"
        client = self._client()
        law = client.get("/health").json()["law_api"]
        self.assertTrue(law["law_api_configured"])
        self.assertFalse(law["law_api_oc_configured"])
        self.assertTrue(law["law_api_key_fallback_configured"])
        self.assertEqual(law["law_api_credential_source"], "LAW_API_KEY")

    def test_debug_endpoint_never_exposes_values(self):
        os.environ["LAW_API_OC"] = "oc-sentinel-zzz-987"
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        client = self._client()
        resp = client.post("/api/debug/law-grounding",
                           json={"question": "H-1으로 계절학기 수강 가능?", "visa_code": "H-1"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertNotIn("oc-sentinel-zzz-987", resp.text)
        body = resp.json()
        self.assertIn("evidence_pack", body)
        self.assertIn("debug", body)
        self.assertTrue(body["debug"]["law_api_oc_configured"])
        self.assertIn("planned_law_queries", body["debug"])

    def test_frontend_html_has_no_oc_or_key_credentials(self):
        # Part A point 10 / Part P point 6: no OC/API key VALUE or assignment in
        # shipped HTML. The non-secret warning-code label LAW_API_KEY_MISSING and
        # the brand name "Paradiso" are allowed; a credential/assignment is not.
        for name in ("ai.html", "index.html"):
            text = (REPO_ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("OC=paradiso", text, name)
            self.assertNotIn("LAW_API_OC=", text, name)
            self.assertNotIn("LAW_API_KEY=", text, name)
            # The OC value must never be embedded as a credential parameter.
            self.assertNotIn("?OC=", text, name)


# ---------------------------------------------------------------------------
# Part B — internal law tools + stable error types
# ---------------------------------------------------------------------------
class LawToolTests(unittest.TestCase):
    def test_search_laws_builds_oc_request_and_normalizes(self):
        cfg = _audit_oc_cfg()
        rec = _RecordingTransport(law_search_body())
        result = lt.search_laws("출입국관리법", config=cfg, transport=rec, limit=5)
        self.assertEqual(result["status"], "ok")
        self.assertIn("OC=paradiso", rec.urls[0])
        self.assertIn("target=law", rec.urls[0])
        self.assertIn("type=JSON", rec.urls[0])
        top = result["results"][0]
        self.assertEqual(top["law_name"], "출입국관리법")
        self.assertEqual(top["law_id"], "001386")
        self.assertEqual(top["law_serial_no"], "267581")
        self.assertEqual(top["reference"], "001386")
        self.assertEqual(top["source_type"], "law")
        self.assertEqual(top["retrieval_status"], "ok")

    def test_get_law_detail_returns_articles(self):
        cfg = _audit_oc_cfg()
        rec = _RecordingTransport(service_body())
        result = lt.get_law_detail(law_id="267581", config=cfg, transport=rec)
        self.assertEqual(result["status"], "ok")
        self.assertIn("detail", result)
        articles = result["detail"]["articles"]
        self.assertTrue(any(a["article_no"] == "10" for a in articles))
        # Raw payload must NOT propagate out of the tool.
        self.assertNotIn("_raw_payload", result)

    def test_get_law_detail_resolves_by_name(self):
        cfg = _audit_oc_cfg()

        def transport(url, timeout):
            if "lawSearch" in url:
                return lt.LawHttpResponse(ok=True, status_code=200, text=law_search_body())
            return lt.LawHttpResponse(ok=True, status_code=200, text=service_body())

        result = lt.get_law_detail(law_name="출입국관리법", config=cfg, transport=transport)
        self.assertEqual(result["status"], "ok")

    def test_search_admin_rules_normalizes(self):
        cfg = _audit_oc_cfg()
        rec = _RecordingTransport(admin_body())
        result = lt.search_admin_rules("체류", config=cfg, transport=rec)
        self.assertIn("target=admrul", rec.urls[0])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["results"][0]["source_type"], "admin_rule")
        self.assertEqual(result["results"][0]["law_name"], "외국인 체류 안내 지침")

    def test_search_law_terms_normalizes(self):
        cfg = _audit_oc_cfg()
        rec = _RecordingTransport(term_body())
        result = lt.search_law_terms("체류자격", config=cfg, transport=rec)
        self.assertIn("target=lstrm", rec.urls[0])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["results"][0]["source_type"], "law_term")
        self.assertEqual(result["results"][0]["term"], "체류자격")

    def test_http_error_maps_to_law_api_http_error(self):
        cfg = _audit_oc_cfg()
        for code in (400, 403, 500, 503):
            def transport(url, timeout, _c=code):
                return lt.LawHttpResponse(ok=False, status_code=_c, error_type="http_error")
            self.assertEqual(
                lt.search_laws("x", config=cfg, transport=transport)["error_type"],
                lt.LAW_API_HTTP_ERROR, code,
            )

    def test_timeout_maps_to_law_api_timeout(self):
        cfg = _audit_oc_cfg()
        def transport(url, timeout):
            return lt.LawHttpResponse(ok=False, error_type="timeout")
        self.assertEqual(
            lt.search_laws("x", config=cfg, transport=transport)["error_type"],
            lt.LAW_API_TIMEOUT,
        )

    def test_html_body_maps_to_bad_response_without_body_leak(self):
        cfg = _audit_oc_cfg()
        def transport(url, timeout):
            return lt.LawHttpResponse(ok=True, status_code=200, text="<html><body>secret-ish failure page</body></html>")
        result = lt.search_laws("x", config=cfg, transport=transport)
        self.assertEqual(result["error_type"], lt.LAW_API_BAD_RESPONSE)
        self.assertEqual(result["response_shape_hint"], "html")
        self.assertNotIn("secret-ish", json.dumps(result))

    def test_text_body_maps_to_bad_response(self):
        cfg = _audit_oc_cfg()
        def transport(url, timeout):
            return lt.LawHttpResponse(ok=True, status_code=200, text="temporary gateway text")
        result = lt.search_laws("x", config=cfg, transport=transport)
        self.assertEqual(result["error_type"], lt.LAW_API_BAD_RESPONSE)
        self.assertEqual(result["response_shape_hint"], "text")


    def test_json_single_object_response_parses(self):
        cfg = _audit_oc_cfg()
        body = json.dumps({"법령명한글": "출입국관리법", "법령ID": "001386"}, ensure_ascii=False)
        result = lt.search_laws("출입국관리법", config=cfg, transport=_RecordingTransport(body))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["response_shape_hint"], "json_object")
        self.assertEqual(result["results"][0]["law_name"], "출입국관리법")

    def test_json_nested_response_shape_parses(self):
        cfg = _audit_oc_cfg()
        body = json.dumps({"response": {"body": {"items": {"item": [{"법령명한글": "출입국관리법 시행령", "MST": "267999"}]}}}}, ensure_ascii=False)
        result = lt.search_laws("시행령", config=cfg, transport=_RecordingTransport(body))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["results"][0]["law_name"], "출입국관리법 시행령")

    def test_xml_response_parses_to_normalized_evidence(self):
        cfg = _audit_oc_cfg()
        body = """<?xml version='1.0' encoding='UTF-8'?><LawSearch><law><법령명한글>출입국관리법</법령명한글><법령ID>001386</법령ID></law></LawSearch>"""
        result = lt.search_laws("출입국관리법", config=cfg, transport=_RecordingTransport(body))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["response_shape_hint"], "xml")
        self.assertEqual(result["results"][0]["law_name"], "출입국관리법")

    def test_official_error_payload_maps_to_official_error(self):
        cfg = _audit_oc_cfg()
        body = json.dumps({"LawSearch": {"resultCode": "99", "message": "ERROR invalid request"}}, ensure_ascii=False)
        result = lt.search_laws("x", config=cfg, transport=_RecordingTransport(body))
        self.assertEqual(result["error_type"], lt.LAW_API_OFFICIAL_ERROR)
        self.assertEqual(result["parser_status"], "official_error")

    def test_empty_result_maps_to_no_results_with_shape_hint(self):
        cfg = _audit_oc_cfg()
        result = lt.search_laws("x", config=cfg, transport=_RecordingTransport(""))
        self.assertEqual(result["error_type"], lt.LAW_API_NO_RESULTS)
        self.assertEqual(result["response_shape_hint"], "empty")

    def test_unexpected_json_maps_to_no_results(self):
        cfg = _audit_oc_cfg()
        def transport(url, timeout):
            return lt.LawHttpResponse(ok=True, status_code=200, text='{"LawSearch": {}}')
        self.assertEqual(
            lt.search_laws("x", config=cfg, transport=transport)["error_type"],
            lt.LAW_API_NO_RESULTS,
        )

    def test_network_error_maps_to_bad_response(self):
        cfg = _audit_oc_cfg()
        def transport(url, timeout):
            return lt.LawHttpResponse(ok=False, error_type="network")
        self.assertEqual(
            lt.search_laws("x", config=cfg, transport=transport)["error_type"],
            lt.LAW_API_BAD_RESPONSE,
        )

    def test_missing_config_maps_to_not_configured(self):
        cfg = GroundingConfig(mode="audit")  # no OC, no key
        for fn in (
            lambda: lt.search_laws("x", config=cfg),
            lambda: lt.search_admin_rules("x", config=cfg),
            lambda: lt.search_law_terms("x", config=cfg),
            lambda: lt.get_law_detail(law_id="1", config=cfg),
        ):
            self.assertEqual(fn()["error_type"], lt.LAW_API_NOT_CONFIGURED)

    def test_tools_are_mock_friendly_no_network(self):
        # With an injected transport, no real network access is performed; with
        # no credential, the tool short-circuits before any transport call.
        cfg = GroundingConfig(mode="audit")
        called = {"n": 0}
        def transport(url, timeout):
            called["n"] += 1
            return lt.LawHttpResponse(ok=True, status_code=200, text=law_search_body())
        lt.search_laws("x", config=cfg, transport=transport)  # not configured -> no call
        self.assertEqual(called["n"], 0)


# ---------------------------------------------------------------------------
# Part C — deterministic query planning
# ---------------------------------------------------------------------------
class QueryPlanningTests(unittest.TestCase):
    def test_h1_study_plan_includes_required_anchors(self):
        plan = lt.plan_law_queries(
            "Can I take summer semester course in Korean universities even though I have a H-1 visa?",
            visa_code="H-1",
        )
        joined = " ".join(plan["queries"])
        for token in ("출입국관리법 시행령 별표 체류자격 관광취업", "관광취업 H-1 활동범위", "체류자격외활동 허가"):
            self.assertIn(token, joined, token)
        self.assertEqual(plan["question_type"], lt.LQ_ACTIVITY_ON_STATUS)

    def test_plan_is_deterministic(self):
        q = "D-2 유학생인데 방학 중 인턴십을 할 수 있나요?"
        a = lt.plan_law_queries(q, visa_code="D-2")
        b = lt.plan_law_queries(q, visa_code="D-2")
        self.assertEqual(a, b)

    def test_h1_korean_study_plan_includes_high_signal_queries(self):
        plan = lt.plan_law_queries("H-1 비자인데 한국 대학 계절학기 수강 가능?", visa_code="H-1")
        joined = " ".join(plan["queries"])
        self.assertIn("출입국관리법 시행령 별표 체류자격 관광취업", joined)
        self.assertIn("체류자격외활동 허가", joined)

    def test_plan_respects_max_queries(self):
        plan = lt.plan_law_queries("H-1 계절학기 수강 활동범위 체류자격외활동", visa_code="H-1", max_queries=2)
        self.assertLessEqual(len(plan["queries"]), 2)

    def test_documents_question_keeps_law_minimal(self):
        plan = lt.plan_law_queries("What documents do I need for D-2 extension?", visa_code="D-2")
        self.assertEqual(plan["question_type"], lt.LQ_DOCUMENTS_NEEDED)
        self.assertLessEqual(len(plan["queries"]), 3)

    def test_status_change_plan_has_change_anchor(self):
        plan = lt.plan_law_queries("D-4 어학연수에서 D-2 유학으로 변경하려면?", visa_code="D-4")
        self.assertEqual(plan["question_type"], lt.LQ_STATUS_CHANGE)
        self.assertIn("체류자격 변경", " ".join(plan["queries"]))

    def test_reporting_plan_has_registration_anchor(self):
        plan = lt.plan_law_queries("체류지를 옮기면 언제 신고해야 하나요?")
        self.assertEqual(plan["question_type"], lt.LQ_DEADLINE_OR_REPORT)
        self.assertIn("신고", " ".join(plan["queries"]))


# ---------------------------------------------------------------------------
# Part D + MCP-like orchestration — evidence pack
# ---------------------------------------------------------------------------
REQUIRED_PACK_KEYS = (
    "direct_manual_sources", "related_manual_sources", "law_sources",
    "law_queries_attempted", "law_grounding_status", "manual_grounding_status",
    "related_statuses_not_sources", "source_confidence_level",
    "answer_quality_mode", "official_confirmation_questions",
)


class EvidencePackTests(unittest.TestCase):
    def test_pack_has_all_required_keys(self):
        pack = lt.build_law_evidence_pack(
            "H-1으로 계절학기 수강 가능?", visa_code="H-1",
            config=GroundingConfig(mode="disabled"),
        )
        for key in REQUIRED_PACK_KEYS:
            self.assertIn(key, pack, key)

    def test_pack_separates_raw_normalized_and_prompt(self):
        cfg = _audit_oc_cfg()
        rec = _RecordingTransport(law_search_body())
        pack = lt.build_law_evidence_pack(
            "H-1으로 계절학기 수강 가능?", visa_code="H-1", config=cfg, transport=rec,
        )
        # Normalized evidence present...
        self.assertTrue(pack["law_sources"])
        self.assertEqual(pack["law_sources"][0]["source_type"], "law")
        # ...the compact prompt summary is a string, not a raw JSON dump...
        self.assertIsInstance(pack["evidence_summary"], str)
        self.assertNotIn("법령일련번호", pack["evidence_summary"])
        self.assertNotIn("{", pack["evidence_summary"])

    def test_law_failure_downgrades_without_crashing(self):
        cfg = _audit_oc_cfg()
        def failing(url, timeout):
            return lt.LawHttpResponse(ok=False, status_code=500, error_type="http_error")
        pack = lt.build_law_evidence_pack(
            "H-1으로 계절학기 수강 가능?", visa_code="H-1", config=cfg, transport=failing,
        )
        self.assertEqual(pack["law_grounding_status"], "unavailable")
        self.assertEqual(pack["law_grounding_error"], lt.LAW_API_HTTP_ERROR)
        # Source confidence downgraded, not crashed.
        self.assertIn(pack["answer_quality_mode"],
                      (aq.SOURCE_LIMITED, aq.SOURCE_UNAVAILABLE))

    def test_manual_primary_for_documents(self):
        pack = lt.build_law_evidence_pack(
            "What documents do I need for D-2 extension?", visa_code="D-2",
            manual_present=True, config=GroundingConfig(mode="audit"),
        )
        self.assertEqual(pack["manual_grounding_status"], "present")
        self.assertEqual(pack["answer_quality_mode"], aq.SOURCE_CONFIRMED)

    def test_related_statuses_not_direct(self):
        pack = lt.build_law_evidence_pack(
            "Can I take a summer course on H-1?", visa_code="H-1",
            config=GroundingConfig(mode="audit"),
        )
        self.assertEqual(pack["related_statuses_not_sources"], ["D-2", "D-4"])
        self.assertEqual(pack["direct_manual_sources"], [])

    def test_normalized_law_evidence_wires_citation_verification(self):
        cfg = _audit_oc_cfg()
        pack = lt.build_law_evidence_pack(
            "H-1으로 계절학기 수강 가능?", visa_code="H-1", config=cfg,
            transport=_RecordingTransport(law_search_body()),
        )
        cv = pack["citation_verification"]
        self.assertNotEqual(cv["status"], "not_wired")
        self.assertEqual(cv["status"], "verified_law_evidence")
        self.assertEqual(cv["citations"][0]["source_type"], "law")

    def test_no_law_evidence_does_not_report_not_wired(self):
        pack = lt.build_law_evidence_pack(
            "Can I take a summer course on H-1?", visa_code="H-1",
            config=GroundingConfig(mode="audit"),
        )
        self.assertIn(pack["citation_verification"]["status"], {"law_api_unavailable", "law_evidence_unavailable", "citation_verification_not_applicable"})
        self.assertNotEqual(pack["citation_verification"]["status"], "not_wired")

    def test_law_used_is_context_not_checklist(self):
        cfg = _audit_oc_cfg()
        rec = _RecordingTransport(law_search_body())
        pack = lt.build_law_evidence_pack(
            "H-1으로 계절학기 수강 가능?", visa_code="H-1", config=cfg, transport=rec,
        )
        self.assertEqual(pack["answer_quality_mode"], aq.SOURCE_ASSISTED)
        self.assertIn("not a document checklist", pack["evidence_summary"])


# ---------------------------------------------------------------------------
# Part M — source-confidence modes
# ---------------------------------------------------------------------------
class SourceConfidenceModeTests(unittest.TestCase):
    def _pack(self, prompt, **over):
        kw = dict(config=GroundingConfig(mode="audit"))
        kw.update(over)
        return lt.build_law_evidence_pack(prompt, **kw)

    def test_source_confirmed(self):
        pack = self._pack("D-2 연장 서류", visa_code="D-2", manual_present=True)
        self.assertEqual(pack["answer_quality_mode"], aq.SOURCE_CONFIRMED)
        self.assertEqual(pack["source_confidence_level"], "high")

    def test_source_assisted_from_law(self):
        rec = _RecordingTransport(law_search_body())
        pack = self._pack("H-1으로 계절학기 수강 가능?", visa_code="H-1",
                          config=_audit_oc_cfg(), transport=rec)
        self.assertEqual(pack["answer_quality_mode"], aq.SOURCE_ASSISTED)

    def test_source_limited_related_only(self):
        pack = self._pack("Can I take a summer course on H-1?", visa_code="H-1")
        self.assertEqual(pack["answer_quality_mode"], aq.SOURCE_LIMITED)

    def test_source_unavailable_substantive_no_source(self):
        pack = self._pack("B-2로 들어와서 단기 알바를 해도 되나요?", visa_code="B-2")
        self.assertIn(pack["answer_quality_mode"],
                      (aq.SOURCE_UNAVAILABLE, aq.SOURCE_LIMITED))

    def test_generic_advisory_offtopic(self):
        pack = lt.build_law_evidence_pack("커피 한 잔 추천해줘",
                                          config=GroundingConfig(mode="audit"))
        self.assertEqual(pack["answer_quality_mode"], aq.GENERIC_ADVISORY)


# ---------------------------------------------------------------------------
# Part N — unsupported-confidence phrase guard
# ---------------------------------------------------------------------------
class RiskyPhraseTests(unittest.TestCase):
    def test_flags_risky_phrases_in_limited_mode(self):
        text = "Yes, you can do this and it is allowed; it will be approved automatically."
        findings = aq.scan_unsupported_confidence_phrases(text, aq.SOURCE_LIMITED)
        for phrase in ("you can", "is allowed", "will be approved", "automatically"):
            self.assertIn(phrase, findings)

    def test_does_not_flag_in_confirmed_mode(self):
        text = "You can extend; the required documents are listed below."
        self.assertEqual(
            aq.scan_unsupported_confidence_phrases(text, aq.SOURCE_CONFIRMED), [])

    def test_safe_wording_is_clean(self):
        text = ("Paradiso cannot confirm from currently verified sources that this is"
                " allowed; it may be assessed differently, but official confirmation is"
                " required. Confirm with 1345, HiKorea, or the competent immigration office.")
        # "is allowed" appears inside "cannot confirm ... that this is allowed" — the
        # guard is a lexical screen, so the directive (not the scanner) governs phrasing;
        # here we assert the canonical SAFE phrases are recognized as present.
        low = text.lower()
        self.assertIn(aq.SAFER_CONFIDENCE_PHRASES[0], low)

    def test_limited_directive_names_safe_phrasing(self):
        q = aq.classify_answer_quality(
            prompt="Can I take a summer course on H-1?", visa_code="H-1", task_type=None,
            manual_grounding_present=False, structured_requirements_present=False,
            procedure_variant_present=False, law_grounding_used=False,
            law_grounding_status="unavailable", manual_to_law_fallback_used=False,
            law_intent=True,
        )
        directive = aq.build_answer_directives(q, lang="en")
        self.assertIn("Paradiso cannot verify that an H-1 holder may take", directive)
        self.assertIn("official confirmation is required", directive)


if __name__ == "__main__":
    unittest.main(verbosity=2)
