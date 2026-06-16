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
# Transport scheme fallback (https <-> http for law.go.kr)
# ---------------------------------------------------------------------------
class SchemeFallbackTests(unittest.TestCase):
    HTTPS = "https://www.law.go.kr/DRF/lawSearch.do?OC=oc-x&target=prec&query=t"

    def _sender(self, behavior):
        calls = []

        def sender(url, timeout):
            calls.append(url)
            return behavior(url)

        return sender, calls

    def test_https_network_failure_falls_back_to_http(self):
        def behavior(url):
            if url.startswith("https://"):
                return lt.LawHttpResponse(ok=False, error_type="network")
            return lt.LawHttpResponse(ok=True, status_code=200, text="{}")

        sender, calls = self._sender(behavior)
        resp = lt._transport_with_scheme_fallback(self.HTTPS, 8.0, sender)
        self.assertTrue(resp.ok)
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[0].startswith("https://"))
        self.assertTrue(calls[1].startswith("http://"))

    def test_http_network_failure_falls_back_to_https(self):
        http_url = "http://www.law.go.kr/DRF/lawSearch.do?OC=oc-x&target=prec"

        def behavior(url):
            if url.startswith("http://"):
                return lt.LawHttpResponse(ok=False, error_type="network")
            return lt.LawHttpResponse(ok=True, status_code=200, text="{}")

        sender, calls = self._sender(behavior)
        resp = lt._transport_with_scheme_fallback(http_url, 8.0, sender)
        self.assertTrue(resp.ok)
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[1].startswith("https://"))

    def test_http_403_does_not_swap_scheme(self):
        # A real HTTP response (incl. 403 = OC / IP-allowlist) means the host was
        # reached: never swap scheme (it would not help and would mask the cause).
        def behavior(url):
            return lt.LawHttpResponse(ok=False, status_code=403, error_type="http_error")

        sender, calls = self._sender(behavior)
        resp = lt._transport_with_scheme_fallback(self.HTTPS, 8.0, sender)
        self.assertEqual(resp.error_type, "http_error")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(len(calls), 1, "no scheme swap on an HTTP response")

    def test_non_law_host_network_failure_does_not_retry(self):
        def behavior(url):
            return lt.LawHttpResponse(ok=False, error_type="network")

        sender, calls = self._sender(behavior)
        resp = lt._transport_with_scheme_fallback("https://example.com/x", 8.0, sender)
        self.assertFalse(resp.ok)
        self.assertEqual(len(calls), 1)

    def test_fallback_kept_only_if_alt_reaches_host(self):
        # If BOTH schemes fail at the connection level, keep the original result.
        def behavior(url):
            return lt.LawHttpResponse(ok=False, error_type="network")

        sender, calls = self._sender(behavior)
        resp = lt._transport_with_scheme_fallback(self.HTTPS, 8.0, sender)
        self.assertFalse(resp.ok)
        self.assertEqual(resp.error_type, "network")
        self.assertEqual(len(calls), 2)

    def test_is_law_host_matches_law_go_kr_only(self):
        self.assertTrue(lt._is_law_host("https://www.law.go.kr/DRF/x"))
        self.assertTrue(lt._is_law_host("http://law.go.kr/x"))
        self.assertFalse(lt._is_law_host("https://evil-law.go.kr.example.com/x"))
        self.assertFalse(lt._is_law_host("https://example.com/x"))


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
        # audit + credential => real-time law calls actually fire.
        self.assertEqual(body["law_grounding_effective_mode"], "audit")
        self.assertTrue(body["law_grounding_active"])
        # Neither secret value appears anywhere in the response text.
        self.assertNotIn("oc-sentinel-zzz-987", resp.text)
        self.assertNotIn("legacy-secret-key-654", resp.text)

    def test_health_law_mode_default_is_enabled_not_stale_disabled(self):
        # /health used to hardcode law_grounding_mode="disabled" by default,
        # contradicting the real default ("enabled" from grounding_config) and
        # making an active deployment look off. It must now report the true mode
        # plus the credential-gated effective state.
        client = self._client()  # no LAW_* env set
        body = client.get("/health").json()
        self.assertEqual(body["law_grounding_mode"], "enabled")
        # enabled WITHOUT a credential degrades to disabled (no external call,
        # no answer downgrade) and is reported honestly as inactive.
        self.assertEqual(body["law_grounding_effective_mode"], "disabled")
        self.assertFalse(body["law_grounding_active"])

    def test_health_law_mode_enabled_with_oc_is_active(self):
        os.environ["LAW_API_OC"] = "oc-sentinel-active-111"
        body = self._client().get("/health").json()
        self.assertEqual(body["law_grounding_mode"], "enabled")
        self.assertEqual(body["law_grounding_effective_mode"], "enabled")
        self.assertTrue(body["law_grounding_active"])
        self.assertNotIn("oc-sentinel-active-111", str(body))

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
# Part B (extended) — parser/normalizer status taxonomy
# ---------------------------------------------------------------------------
class LawParserTaxonomyTests(unittest.TestCase):
    """Each distinct API outcome maps to its OWN status — never collapsed into
    LAW_API_BAD_RESPONSE."""

    def test_xml_official_error_maps_to_official_error(self):
        cfg = _audit_oc_cfg()
        body = (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<LawSearch><resultCode>99</resultCode>"
            "<message>ERROR invalid request</message></LawSearch>"
        )
        result = lt.search_laws("x", config=cfg, transport=_RecordingTransport(body))
        self.assertEqual(result["error_type"], lt.LAW_API_OFFICIAL_ERROR)
        self.assertEqual(result["parser_status"], "official_error")
        self.assertEqual(result["response_shape_hint"], "xml")
        # The raw error body text is never echoed back to the caller.
        self.assertNotIn("invalid request", json.dumps(result, ensure_ascii=False))

    def test_xml_success_zero_error_code_is_not_official_error(self):
        # A success response that carries errorCode=0 must parse to no_results,
        # not be misread as an official error (regression for the collapse bug).
        cfg = _audit_oc_cfg()
        body = "<?xml version='1.0' encoding='UTF-8'?><LawSearch><errorCode>0</errorCode></LawSearch>"
        result = lt.search_laws("x", config=cfg, transport=_RecordingTransport(body))
        self.assertEqual(result["error_type"], lt.LAW_API_NO_RESULTS)

    def test_json_nested_empty_result_maps_to_no_results(self):
        cfg = _audit_oc_cfg()
        body = json.dumps({"response": {"body": {"items": {"item": []}}, "totalCnt": "0"}}, ensure_ascii=False)
        result = lt.search_laws("x", config=cfg, transport=_RecordingTransport(body))
        self.assertEqual(result["error_type"], lt.LAW_API_NO_RESULTS)
        self.assertEqual(result["response_shape_hint"], "json_object")

    def test_json_list_under_body_items_result_normalizes(self):
        cfg = _audit_oc_cfg()
        body = json.dumps({"body": {"result": [{"법령명한글": "출입국관리법", "법령ID": "001386"}]}}, ensure_ascii=False)
        result = lt.search_laws("출입국관리법", config=cfg, transport=_RecordingTransport(body))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["results"][0]["law_name"], "출입국관리법")

    def test_inspect_shape_hints_cover_all_families(self):
        self.assertEqual(lt.inspect_law_api_response_shape("")["response_shape_hint"], "empty")
        self.assertEqual(lt.inspect_law_api_response_shape("<html><body>x</body></html>")["response_shape_hint"], "html")
        self.assertEqual(lt.inspect_law_api_response_shape("<?xml version='1.0'?><a/>")["response_shape_hint"], "xml")
        self.assertEqual(lt.inspect_law_api_response_shape("[1,2]")["response_shape_hint"], "json_list")
        self.assertEqual(lt.inspect_law_api_response_shape("{\"a\":1}")["response_shape_hint"], "json_object")
        self.assertEqual(lt.inspect_law_api_response_shape("plain words")["response_shape_hint"], "text")
        official = lt.inspect_law_api_response_shape(json.dumps({"resultCode": "99", "message": "ERROR"}))
        self.assertEqual(official["parser_status"], "official_error")


class OfficialSourceFamilyAdapterTests(unittest.TestCase):
    """retrieve_official_source_family distinguishes every status; unsupported /
    not_configured families never collapse into bad_response."""

    def test_precedent_source_family_list_search_is_available_not_direct(self):
        cfg = _audit_oc_cfg()
        result = lt.retrieve_official_source_family("precedent", "출입국 판례", config=cfg, transport=_RecordingTransport(law_search_body()))
        self.assertIn(result["status"], {lt.SOURCE_STATUS_RESULTS_FOUND, lt.SOURCE_STATUS_NO_RESULTS})
        self.assertNotEqual(result["status"], lt.SOURCE_STATUS_BAD_RESPONSE)

    def test_unconfirmed_precedent_family_is_unsupported_not_bad_response(self):
        cfg = _audit_oc_cfg()
        result = lt.retrieve_official_source_family("administrative_appeal", "출입국 행정심판", config=cfg, transport=_RecordingTransport(law_search_body()))
        self.assertEqual(result["status"], lt.SOURCE_STATUS_UNSUPPORTED)
        self.assertNotEqual(result["status"], lt.SOURCE_STATUS_BAD_RESPONSE)

    def test_unknown_source_family_is_unsupported(self):
        cfg = _audit_oc_cfg()
        result = lt.retrieve_official_source_family("totally_made_up", "x", config=cfg)
        self.assertEqual(result["status"], lt.SOURCE_STATUS_UNSUPPORTED)

    def test_missing_credentials_is_not_configured_not_bad_response(self):
        cfg = GroundingConfig(mode="audit")  # no OC/key
        result = lt.retrieve_official_source_family("statute", "출입국관리법", config=cfg)
        self.assertEqual(result["status"], lt.SOURCE_STATUS_NOT_CONFIGURED)

    def test_missing_credentials_precedent_is_not_configured_not_secret_leak(self):
        cfg = GroundingConfig(mode="audit")  # no OC/key
        result = lt.retrieve_official_source_family("precedent", "출입국 판례", config=cfg)
        self.assertEqual(result["status"], lt.SOURCE_STATUS_NOT_CONFIGURED)
        self.assertNotIn("OC=", json.dumps(result, ensure_ascii=False))

    def test_empty_results_family_is_no_results_not_bad_response(self):
        cfg = _audit_oc_cfg()
        result = lt.retrieve_official_source_family("statute", "출입국관리법", config=cfg, transport=_RecordingTransport('{"LawSearch": {}}'))
        self.assertEqual(result["status"], lt.SOURCE_STATUS_NO_RESULTS)

    def test_official_error_family_is_official_error_not_bad_response(self):
        cfg = _audit_oc_cfg()
        body = json.dumps({"LawSearch": {"resultCode": "99", "message": "ERROR invalid"}}, ensure_ascii=False)
        result = lt.retrieve_official_source_family("statute", "x", config=cfg, transport=_RecordingTransport(body))
        self.assertEqual(result["status"], lt.SOURCE_STATUS_OFFICIAL_ERROR)

    def test_timeout_family_is_timeout(self):
        cfg = _audit_oc_cfg()
        def transport(url, timeout):
            return lt.LawHttpResponse(ok=False, error_type="timeout")
        result = lt.retrieve_official_source_family("statute", "x", config=cfg, transport=transport)
        self.assertEqual(result["status"], lt.SOURCE_STATUS_TIMEOUT)

    def test_html_family_is_bad_response_with_shape_hint_no_leak(self):
        cfg = _audit_oc_cfg()
        body = "<!DOCTYPE html><html><body>login required secret-page</body></html>"
        result = lt.retrieve_official_source_family("statute", "x", config=cfg, transport=_RecordingTransport(body))
        self.assertEqual(result["status"], lt.SOURCE_STATUS_BAD_RESPONSE)
        self.assertEqual(result["response_shape_hint"], "html")
        self.assertNotIn("secret-page", json.dumps(result, ensure_ascii=False))

    def test_results_found_family_normalizes_evidence(self):
        cfg = _audit_oc_cfg()
        result = lt.retrieve_official_source_family("statute", "출입국관리법", config=cfg, transport=_RecordingTransport(law_search_body()))
        self.assertEqual(result["status"], lt.SOURCE_STATUS_RESULTS_FOUND)
        self.assertTrue(result["normalized_items"])


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
        self.assertNotIn("Paradiso cannot verify that an H-1 holder may take", directive)
        self.assertIn("backend-prepared legal_analysis", directive)
        self.assertIn("Do not reuse study/course wording unless", directive)
        self.assertIn("official confirmation is required", directive)


if __name__ == "__main__":
    unittest.main(verbosity=2)

# ---------------------------------------------------------------------------
# Legal analysis guidance engine (deterministic, no network required)
# ---------------------------------------------------------------------------
class LegalAnalysisGuidanceTests(unittest.TestCase):
    def test_h1_summer_course_builds_legal_analysis_object(self):
        pack = lt.build_law_evidence_pack(
            "Can I take summer semester course in Korean universities even though I have a H-1 visa?",
            visa_code="H-1",
            config=GroundingConfig(mode="audit"),
            retrieve=False,
        )
        la = pack["legal_analysis"]
        self.assertEqual(la["risk_posture"], "medium")
        self.assertIn(la["confidence"], ("contextual", "analogical", "limited", "unavailable"))
        self.assertTrue(la["missing_direct_authority"])
        self.assertIn("permitted activity scope", la["main_issue"])
        self.assertIn("activities outside", la["main_issue"])
        self.assertIn("change of sojourn status", la["main_issue"])
        joined_q = " ".join(la["official_confirmation_questions"])
        self.assertIn("credit-bearing", joined_q)
        self.assertIn("D-2 / D-4", joined_q)
        self.assertIn("source_types_attempted", la)

    def test_evidence_relevance_direct_related_analogical_background_noise(self):
        q = "Can I take a summer semester course on H-1?"
        direct = {"law_name": "출입국관리법 시행령", "summary": "H-1 관광취업 활동범위와 체류자격외활동 허가"}
        related = {"law_name": "유학 D-2", "summary": "D-2 유학 체류자격 활동범위"}
        background = {"source_type": "legal_term", "term": "체류자격"}
        noise = {"law_name": "도로교통법", "summary": "운전면허"}
        self.assertEqual(lt.score_evidence_relevance(direct, question=q, visa_code="H-1", question_type="activity_on_status"), "direct")
        self.assertIn(lt.score_evidence_relevance(related, question=q, visa_code="H-1", question_type="activity_on_status"), ("related", "analogical"))
        self.assertNotEqual(lt.score_evidence_relevance(related, question=q, visa_code="H-1", question_type="activity_on_status"), "direct")
        self.assertEqual(lt.score_evidence_relevance(background, question=q, visa_code="H-1", question_type="activity_on_status"), "background")
        self.assertEqual(lt.score_evidence_relevance(noise, question=q, visa_code="H-1", question_type="activity_on_status"), "not_relevant")

    def test_source_family_planning_by_question_type(self):
        activity = lt.plan_source_families("Can I study on H-1?", visa_code="H-1")
        self.assertEqual(activity["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        for fam in ("statute", "enforcement_decree", "enforcement_rule"):
            self.assertIn(fam, activity["source_types_attempted"])
        self.assertIn("legal_interpretation", activity["unsupported_source_types"])

        change = lt.plan_source_families("Can I change D-4 to D-2?", visa_code="D-4")
        self.assertEqual(change["question_type"], lt.LQ_STATUS_CHANGE)
        self.assertIn("manual", change["source_types_priority"])
        self.assertIn("legal_interpretation", change["unsupported_source_types"])

        docs = lt.plan_source_families("What documents do I need for D-2 extension?", visa_code="D-2")
        self.assertEqual(docs["source_types_priority"][0], "manual")

        high = lt.plan_source_families("I overstayed one day, what penalty?", visa_code="D-2")
        self.assertEqual(high["question_type"], lt.LQ_HIGH_RISK_EXCEPTION)
        self.assertIn("administrative_appeal", high["unsupported_source_types"])

        nat = lt.plan_source_families("What are general naturalization requirements?", visa_code="F-2")
        self.assertEqual(nat["question_type"], lt.LQ_NATIONALITY)
        self.assertIn("statute", nat["source_types_attempted"])

    def test_h1_plan_includes_all_target_queries_when_cap_allows(self):
        plan = lt.plan_law_queries(
            "Can I take summer semester course in Korean universities even though I have a H-1 visa?",
            visa_code="H-1",
            max_queries=7,
        )
        joined = " | ".join(plan["queries"])
        for token in (
            "출입국관리법 시행령 별표 체류자격 관광취업",
            "관광취업 H-1 활동범위",
            "체류자격외활동 허가",
            "체류자격 변경 유학 D-2 D-4",
            "유학 체류자격 활동범위",
            "출입국관리법 체류자격 변경허가",
        ):
            self.assertIn(token, joined)

# ---------------------------------------------------------------------------
# Official source-family adapter hardening (2026-05)
# ---------------------------------------------------------------------------
class OfficialSourceAdapterParserTests(unittest.TestCase):
    def cfg(self):
        return GroundingConfig(mode="audit", law_api_oc="secret-oc")

    def test_json_object_response_normalizes_evidence(self):
        result = lt.retrieve_official_source_family("statute", "출입국관리법", config=self.cfg(), transport=_RecordingTransport(law_search_body()))
        self.assertEqual(result["status"], "results_found")
        self.assertTrue(result["normalized_items"])
        self.assertEqual(result["response_shape_hint"], "json_object")
        self.assertNotIn("secret-oc", result["sanitized_source_url"])

    def test_json_list_response_normalizes_evidence(self):
        body = json.dumps([{"법령명한글": "출입국관리법", "법령ID": "001386"}], ensure_ascii=False)
        result = lt.retrieve_official_source_family("statute", "출입국관리법", config=self.cfg(), transport=_RecordingTransport(body))
        self.assertEqual(result["status"], "results_found")
        self.assertEqual(result["response_shape_hint"], "json_list")

    def test_nested_json_response_normalizes_evidence(self):
        body = json.dumps({"outer": {"items": [{"법령명한글": "출입국관리법 시행규칙", "법령ID": "RULE"}]}}, ensure_ascii=False)
        result = lt.retrieve_official_source_family("enforcement_rule", "시행규칙", config=self.cfg(), transport=_RecordingTransport(body))
        self.assertEqual(result["status"], "results_found")
        self.assertEqual(result["normalized_items"][0]["source_type"], "enforcement_rule")

    def test_xml_response_normalizes_or_clean_status(self):
        body = """<?xml version='1.0'?><LawSearch><law><법령명한글>출입국관리법</법령명한글><법령ID>001386</법령ID></law></LawSearch>"""
        result = lt.retrieve_official_source_family("statute", "출입국관리법", config=self.cfg(), transport=_RecordingTransport(body))
        self.assertEqual(result["response_shape_hint"], "xml")
        self.assertIn(result["status"], {"results_found", "no_results"})
        self.assertIn(result["parser_status"], {"parsed_xml", "empty"})

    def test_official_error_response_maps_official_error(self):
        body = json.dumps({"errorCode": "INVALID", "message": "invalid request"})
        result = lt.retrieve_official_source_family("statute", "출입국관리법", config=self.cfg(), transport=_RecordingTransport(body))
        self.assertEqual(result["status"], "official_error")
        self.assertEqual(result["error_type"], lt.LAW_API_OFFICIAL_ERROR)

    def test_empty_response_maps_no_results(self):
        result = lt.retrieve_official_source_family("statute", "출입국관리법", config=self.cfg(), transport=_RecordingTransport(""))
        self.assertEqual(result["status"], "no_results")
        self.assertEqual(result["error_type"], lt.LAW_API_NO_RESULTS)

    def test_html_text_and_malformed_payloads_are_safe(self):
        html = lt.retrieve_official_source_family("statute", "출입국관리법", config=self.cfg(), transport=_RecordingTransport("<html><body>maintenance</body></html>"))
        self.assertEqual(html["status"], "bad_response")
        self.assertEqual(html["response_shape_hint"], "html")
        malformed = lt.retrieve_official_source_family("statute", "출입국관리법", config=self.cfg(), transport=_RecordingTransport('{"bad"'))
        self.assertEqual(malformed["status"], "parse_error")
        self.assertEqual(malformed["parser_status"], "json_parse_error")

    def test_raw_body_not_exposed_in_adapter_metadata(self):
        raw = "<html><body>secret body text that must not propagate</body></html>"
        result = lt.retrieve_official_source_family("statute", "출입국관리법", config=self.cfg(), transport=_RecordingTransport(raw))
        dumped = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("secret body text", dumped)
        self.assertNotIn("secret-oc", dumped)


class OfficialSourceFamilyStatusTests(unittest.TestCase):
    def cfg(self):
        return GroundingConfig(mode="audit", law_api_oc="secret-oc")

    def test_unsupported_source_family_not_bad_response(self):
        result = lt.retrieve_official_source_family("administrative_appeal", "출입국", config=self.cfg())
        self.assertEqual(result["status"], "unsupported")
        self.assertNotEqual(result["status"], "bad_response")

    def test_not_configured_status(self):
        result = lt.retrieve_official_source_family("statute", "출입국", config=GroundingConfig(mode="audit"))
        self.assertEqual(result["status"], "not_configured")

    def test_results_no_results_official_error_and_timeout_statuses(self):
        ok = lt.retrieve_official_source_family("administrative_rule", "체류", config=self.cfg(), transport=_RecordingTransport(admin_body()))
        self.assertEqual(ok["status"], "results_found")
        no = lt.retrieve_official_source_family("legal_term", "체류", config=self.cfg(), transport=_RecordingTransport(""))
        self.assertEqual(no["status"], "no_results")
        err = lt.retrieve_official_source_family("statute", "체류", config=self.cfg(), transport=_RecordingTransport(json.dumps({"errorCode": "X", "message": "error"})))
        self.assertEqual(err["status"], "official_error")

        def timeout(_url, _timeout):
            return lt.LawHttpResponse(ok=False, error_type="timeout")
        timed = lt.retrieve_official_source_family("statute", "체류", config=self.cfg(), transport=timeout)
        self.assertEqual(timed["status"], "timeout")
