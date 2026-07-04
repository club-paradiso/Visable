"""Offline tests for the PreView MOFA mission proxy.

Covers GET /api/preview/mission plus services/mofa_public_data.py:

- missing service key returns the safe fallback envelope
- invalid country queries are rejected with 400 (no upstream call)
- a mocked successful MOFA response is normalized into PreViewMission fields
- upstream timeout / non-200 / malformed payloads return safe fallbacks
- the service key never leaks into any response body
- source metadata is present on every envelope

No network access: the module-level ``_default_transport`` seam is swapped
for in-memory fakes, mirroring backend/tests/test_legal_source_search_api.py.

Run standalone:  python3 backend/tests/test_preview_mofa_proxy.py
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

from fastapi.testclient import TestClient  # noqa: E402

import paradiso_backend  # noqa: E402
from services import mofa_public_data  # noqa: E402

client = TestClient(paradiso_backend.app)

SECRET_KEY = "PREVIEW-TEST-SECRET-KEY-12345"

# All contact values below are OBVIOUSLY SYNTHETIC fixture data (TEST markers,
# zeroed digits, round coordinates). They exercise field mapping only and must
# never be mistaken for real embassy contact facts.
SAMPLE_UPSTREAM_FLAT = {
    "resultCode": 0,
    "resultMsg": "NORMAL SERVICE",
    "currentCount": 2,
    "numOfRows": 50,
    "pageNo": 1,
    "totalCount": 2,
    "data": [
        {
            "country_nm": "베트남",
            "country_eng_nm": "Vietnam",
            "country_iso_alp2": "VN",
            "embassy_kor_nm": "주베트남 대한민국 대사관",
            "embassy_ty_cd_nm": "대사관",
            "embassy_manage_ty_cd_nm": "직할",
            "emblgbd_addr": "테스트 픽스처 샘플 주소 1 (실제 주소 아님)",
            "embassy_lat": "10.5",
            "embassy_lng": "100.25",
            "tel_no": "+00-TEST-0000-0001",
            "urgency_tel_no": "+00-TEST-0000-0002",
            "center_tel_no": "+00-TEST-0000-0003",
            "free_tel_no": "",
        },
        {
            "country_nm": "몽골",
            "country_eng_nm": "Mongolia",
            "country_iso_alp2": "MN",
            "embassy_kor_nm": "주몽골 대한민국 대사관",
            "embassy_ty_cd_nm": "대사관",
            "emblgbd_addr": "테스트 픽스처 샘플 주소 2 (실제 주소 아님)",
            "tel_no": "+00-TEST-0000-0004",
        },
    ],
}

SAMPLE_UPSTREAM_WRAPPED = {
    "response": {
        "header": {"resultCode": "00", "resultMsg": "OK"},
        "body": {
            "items": {
                "item": [
                    {
                        "country_nm": "우즈베키스탄",
                        "country_iso_alp2": "UZ",
                        "embassy_kor_nm": "주우즈베키스탄 대한민국 대사관",
                        "embassy_ty_cd_nm": "대사관",
                    }
                ]
            }
        },
    }
}


class _EnvGuardTestCase(unittest.TestCase):
    """Save/restore key env vars and the transport seam around each test."""

    _ENV_NAMES = ("MOFA_EMBASSY_SERVICE_KEY", "PUBLIC_DATA_SERVICE_KEY")

    def setUp(self) -> None:
        self._saved_env = {name: os.environ.get(name) for name in self._ENV_NAMES}
        for name in self._ENV_NAMES:
            os.environ.pop(name, None)
        self._saved_transport = mofa_public_data._default_transport
        mofa_public_data._reset_cache()

    def tearDown(self) -> None:
        for name, value in self._saved_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        mofa_public_data._default_transport = self._saved_transport
        mofa_public_data._reset_cache()


class MissingKeyTests(_EnvGuardTestCase):
    def test_missing_key_returns_safe_fallback_envelope(self) -> None:
        def _must_not_be_called(url, params, timeout):  # pragma: no cover
            raise AssertionError("transport must not be called without a key")

        mofa_public_data._default_transport = _must_not_be_called
        response = client.get("/api/preview/mission", params={"country": "VN"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["mode"], "fallback_required")
        self.assertEqual(payload["reason"], "missing_service_key")
        self.assertIn("MVP 샘플 데이터", payload["safeMessageKo"])
        self.assertIn("source", payload)
        self.assertEqual(payload["source"]["provider"], "외교부")


class InvalidQueryTests(_EnvGuardTestCase):
    def test_empty_query_rejected_with_400(self) -> None:
        response = client.get("/api/preview/mission")
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "invalid_query")

    def test_malformed_country_rejected(self) -> None:
        for bad in ("V1", "VNM", "<script>", "V", "베트남<img>"):
            response = client.get("/api/preview/mission", params={"country": bad})
            self.assertEqual(response.status_code, 400, msg=f"country={bad!r}")

    def test_malformed_country_name_rejected(self) -> None:
        response = client.get(
            "/api/preview/mission", params={"countryName": "<script>alert(1)</script>"}
        )
        self.assertEqual(response.status_code, 400)

    def test_valid_korean_country_name_accepted(self) -> None:
        os.environ["PUBLIC_DATA_SERVICE_KEY"] = SECRET_KEY
        seen = {}

        def _fake(url, params, timeout):
            seen["params"] = dict(params)
            return 200, json.dumps(SAMPLE_UPSTREAM_FLAT, ensure_ascii=False)

        mofa_public_data._default_transport = _fake
        response = client.get("/api/preview/mission", params={"countryName": "베트남"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(seen["params"]["cond[country_nm::EQ]"], "베트남")


class SuccessNormalizationTests(_EnvGuardTestCase):
    def test_flat_envelope_normalized_and_filtered(self) -> None:
        os.environ["MOFA_EMBASSY_SERVICE_KEY"] = SECRET_KEY

        def _fake(url, params, timeout):
            return 200, json.dumps(SAMPLE_UPSTREAM_FLAT, ensure_ascii=False)

        mofa_public_data._default_transport = _fake
        response = client.get("/api/preview/mission", params={"country": "vn"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "live_api")
        self.assertEqual(payload["itemCount"], 1)
        item = payload["items"][0]
        self.assertEqual(item["missionNameKo"], "주베트남 대한민국 대사관")
        self.assertEqual(item["missionTypeKo"], "대사관")
        self.assertEqual(item["countryIso2"], "VN")
        self.assertEqual(item["countryNameEn"], "Vietnam")
        self.assertEqual(item["phone"], "+00-TEST-0000-0001")
        self.assertEqual(item["emergencyPhone"], "+00-TEST-0000-0002")
        self.assertAlmostEqual(item["latitude"], 10.5)
        self.assertIsNone(item["freePhone"])
        source = payload["source"]
        self.assertEqual(source["datasetName"], "외교부_국가·지역별 재외공관 정보")
        self.assertEqual(source["sourceType"], "mofa_public_data_portal_api")
        self.assertTrue(source["fetchedAt"])

    def test_wrapped_envelope_supported(self) -> None:
        os.environ["PUBLIC_DATA_SERVICE_KEY"] = SECRET_KEY

        def _fake(url, params, timeout):
            return 200, json.dumps(SAMPLE_UPSTREAM_WRAPPED, ensure_ascii=False)

        mofa_public_data._default_transport = _fake
        response = client.get("/api/preview/mission", params={"country": "UZ"})
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["items"][0]["missionNameKo"], "주우즈베키스탄 대한민국 대사관")

    def test_upstream_html_is_stripped(self) -> None:
        os.environ["PUBLIC_DATA_SERVICE_KEY"] = SECRET_KEY
        dirty = {
            "data": [
                {
                    "country_iso_alp2": "VN",
                    "embassy_kor_nm": "<b>주베트남 대한민국 대사관</b>",
                    "emblgbd_addr": "addr &amp; more<script>x()</script>",
                }
            ]
        }

        def _fake(url, params, timeout):
            return 200, json.dumps(dirty, ensure_ascii=False)

        mofa_public_data._default_transport = _fake
        payload = client.get("/api/preview/mission", params={"country": "VN"}).json()
        item = payload["items"][0]
        self.assertNotIn("<", item["missionNameKo"])
        self.assertNotIn("<script>", item["addressKo"])
        self.assertIn("addr & more", item["addressKo"])

    def test_no_matching_record_returns_ok_with_empty_items(self) -> None:
        os.environ["PUBLIC_DATA_SERVICE_KEY"] = SECRET_KEY

        def _fake(url, params, timeout):
            return 200, json.dumps(SAMPLE_UPSTREAM_FLAT, ensure_ascii=False)

        mofa_public_data._default_transport = _fake
        payload = client.get("/api/preview/mission", params={"country": "FR"}).json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["items"], [])
        self.assertIn("noteKo", payload)


class UpstreamFailureTests(_EnvGuardTestCase):
    def _set_key(self) -> None:
        os.environ["PUBLIC_DATA_SERVICE_KEY"] = SECRET_KEY

    def test_timeout_returns_safe_fallback(self) -> None:
        self._set_key()

        def _fake(url, params, timeout):
            import httpx

            raise httpx.ConnectTimeout("simulated timeout")

        mofa_public_data._default_transport = _fake
        response = client.get("/api/preview/mission", params={"country": "VN"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["mode"], "fallback_required")
        self.assertEqual(payload["reason"], "upstream_timeout")
        self.assertNotIn("Traceback", response.text)

    def test_non_200_returns_safe_fallback(self) -> None:
        self._set_key()

        def _fake(url, params, timeout):
            return 500, "internal error"

        mofa_public_data._default_transport = _fake
        payload = client.get("/api/preview/mission", params={"country": "VN"}).json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "upstream_http_500")

    def test_auth_error_xml_returns_service_error(self) -> None:
        self._set_key()
        xml_error = (
            "<OpenAPI_ServiceResponse><cmmMsgHeader>"
            "<returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg>"
            "</cmmMsgHeader></OpenAPI_ServiceResponse>"
        )

        def _fake(url, params, timeout):
            return 200, xml_error

        mofa_public_data._default_transport = _fake
        payload = client.get("/api/preview/mission", params={"country": "VN"}).json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "upstream_service_error")

    def test_malformed_json_returns_parse_error(self) -> None:
        self._set_key()

        def _fake(url, params, timeout):
            return 200, "definitely not json {"

        mofa_public_data._default_transport = _fake
        payload = client.get("/api/preview/mission", params={"country": "VN"}).json()
        self.assertFalse(payload["ok"])
        self.assertIn(payload["reason"], ("upstream_parse_error", "upstream_service_error"))


class KeyHygieneTests(_EnvGuardTestCase):
    def test_key_never_leaks_in_any_response(self) -> None:
        os.environ["MOFA_EMBASSY_SERVICE_KEY"] = SECRET_KEY

        scenarios = [
            lambda url, params, timeout: (200, json.dumps(SAMPLE_UPSTREAM_FLAT)),
            lambda url, params, timeout: (500, "server exploded"),
            lambda url, params, timeout: (200, "not json {"),
        ]
        for fake in scenarios:
            mofa_public_data._default_transport = fake
            response = client.get("/api/preview/mission", params={"country": "VN"})
            self.assertNotIn(SECRET_KEY, response.text)

        # Even when the upstream echoes the key back, it must not be forwarded.
        def _echoing(url, params, timeout):
            return 500, f"bad key: {params.get('serviceKey', '')}"

        mofa_public_data._default_transport = _echoing
        response = client.get("/api/preview/mission", params={"country": "VN"})
        self.assertNotIn(SECRET_KEY, response.text)

    def test_key_resolution_order_prefers_specific_alias(self) -> None:
        os.environ["MOFA_EMBASSY_SERVICE_KEY"] = "SPECIFIC-KEY"
        os.environ["PUBLIC_DATA_SERVICE_KEY"] = "UNIFIED-KEY"
        seen = {}

        def _fake(url, params, timeout):
            seen["key"] = params.get("serviceKey")
            return 200, json.dumps(SAMPLE_UPSTREAM_FLAT)

        mofa_public_data._default_transport = _fake
        client.get("/api/preview/mission", params={"country": "VN"})
        self.assertEqual(seen["key"], "SPECIFIC-KEY")

    def test_unified_key_used_when_alias_absent(self) -> None:
        os.environ["PUBLIC_DATA_SERVICE_KEY"] = "UNIFIED-KEY"
        seen = {}

        def _fake(url, params, timeout):
            seen["key"] = params.get("serviceKey")
            return 200, json.dumps(SAMPLE_UPSTREAM_FLAT)

        mofa_public_data._default_transport = _fake
        client.get("/api/preview/mission", params={"country": "VN"})
        self.assertEqual(seen["key"], "UNIFIED-KEY")

    def test_percent_encoded_key_is_decoded_once(self) -> None:
        os.environ["PUBLIC_DATA_SERVICE_KEY"] = "abc%2Bdef%3D%3D"
        seen = {}

        def _fake(url, params, timeout):
            seen["key"] = params.get("serviceKey")
            return 200, json.dumps(SAMPLE_UPSTREAM_FLAT)

        mofa_public_data._default_transport = _fake
        client.get("/api/preview/mission", params={"country": "VN"})
        self.assertEqual(seen["key"], "abc+def==")

    def test_key_echoed_inside_success_body_is_redacted(self) -> None:
        os.environ["PUBLIC_DATA_SERVICE_KEY"] = SECRET_KEY
        dirty = {
            "data": [
                {
                    "country_iso_alp2": "VN",
                    "embassy_kor_nm": f"주베트남 대한민국 대사관 {SECRET_KEY}",
                }
            ]
        }

        def _fake(url, params, timeout):
            return 200, json.dumps(dirty, ensure_ascii=False)

        mofa_public_data._default_transport = _fake
        response = client.get("/api/preview/mission", params={"country": "VN"})
        self.assertNotIn(SECRET_KEY, response.text)
        self.assertIn("[redacted]", response.json()["items"][0]["missionNameKo"])


class CacheBehaviorTests(_EnvGuardTestCase):
    def test_successful_lookup_is_cached_and_marked(self) -> None:
        os.environ["PUBLIC_DATA_SERVICE_KEY"] = SECRET_KEY
        calls = {"n": 0}

        def _fake(url, params, timeout):
            calls["n"] += 1
            return 200, json.dumps(SAMPLE_UPSTREAM_FLAT, ensure_ascii=False)

        mofa_public_data._default_transport = _fake
        first = client.get("/api/preview/mission", params={"country": "VN"}).json()
        second = client.get("/api/preview/mission", params={"country": "VN"}).json()
        self.assertEqual(calls["n"], 1)
        self.assertNotIn("servedFromCache", first)
        self.assertTrue(second.get("servedFromCache"))
        self.assertEqual(second["items"], first["items"])

    def test_failures_are_not_cached(self) -> None:
        os.environ["PUBLIC_DATA_SERVICE_KEY"] = SECRET_KEY
        calls = {"n": 0}

        def _fake(url, params, timeout):
            calls["n"] += 1
            return 500, "boom"

        mofa_public_data._default_transport = _fake
        client.get("/api/preview/mission", params={"country": "VN"})
        client.get("/api/preview/mission", params={"country": "VN"})
        self.assertEqual(calls["n"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
