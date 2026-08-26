from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import law_tools as lt  # noqa: E402
from services.grounding_config import GroundingConfig  # noqa: E402
from services.law_cloud_fallback import _PAGE_CACHE  # noqa: E402

ZERO_SHELL = json.dumps({
    "LawSearch": {
        "resultMsg": "success",
        "page": "1",
        "resultCode": "00",
        "target": "law",
        "totalCnt": "0",
        "section": "lawNm",
        "numOfRows": "0",
    }
}, ensure_ascii=False)

NORMAL_RESULT = json.dumps({
    "LawSearch": {
        "totalCnt": "1",
        "law": [{
            "법령명한글": "출입국관리법",
            "법령ID": "001386",
            "법령일련번호": "267581",
            "법령구분명": "법률",
        }],
    }
}, ensure_ascii=False)

DICTIONARY_RESULT = json.dumps({
    "LawSearch": {
        "totalCnt": "2",
        "law": [
            {
                "법령명한글": "출입국관리법",
                "법령ID": "001386",
                "법령일련번호": "267581",
                "법령구분명": "법률",
            },
            {
                "법령명한글": "출입국관리법 시행령",
                "법령ID": "001387",
                "법령일련번호": "267999",
                "법령구분명": "대통령령",
            },
        ],
    }
}, ensure_ascii=False)


class RecordingTransport:
    def __init__(self, *, normal_primary: bool = False):
        self.urls: list[str] = []
        self.normal_primary = normal_primary

    def __call__(self, url: str, timeout: float) -> lt.LawHttpResponse:
        self.urls.append(url)
        qs = parse_qs(urlsplit(url).query)
        if "query" in qs:
            payload = NORMAL_RESULT if self.normal_primary else ZERO_SHELL
        elif qs.get("mobileYn") == ["Y"] and qs.get("gana") == ["cha"]:
            payload = DICTIONARY_RESULT
        else:
            payload = json.dumps({"LawSearch": {"totalCnt": "0"}})
        return lt.LawHttpResponse(ok=True, status_code=200, text=payload)


class EmptyDictionaryTransport(RecordingTransport):
    def __call__(self, url: str, timeout: float) -> lt.LawHttpResponse:
        self.urls.append(url)
        qs = parse_qs(urlsplit(url).query)
        payload = ZERO_SHELL if "query" in qs else json.dumps({"LawSearch": {"totalCnt": "0"}})
        return lt.LawHttpResponse(ok=True, status_code=200, text=payload)


class LawCloudKoreanSearchTests(unittest.TestCase):
    def setUp(self):
        _PAGE_CACHE.clear()
        self.cfg = GroundingConfig(law_api_oc="test-registered-oc", mode="enabled")

    def tearDown(self):
        _PAGE_CACHE.clear()

    def test_normal_primary_result_does_not_use_fallback(self):
        transport = RecordingTransport(normal_primary=True)
        result = lt.search_laws("출입국관리법", config=self.cfg, transport=transport)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["result_count"], 1)
        self.assertEqual(result["results"][0]["law_name"], "출입국관리법")
        self.assertEqual(len(transport.urls), 1)
        self.assertIn("query=", transport.urls[0])
        self.assertNotIn("mobileYn=Y", transport.urls[0])

    def test_cloud_zero_shell_recovers_exact_title_via_ascii_dictionary(self):
        transport = RecordingTransport()
        result = lt.search_laws("출입국관리법", config=self.cfg, transport=transport)
        self.assertEqual(result["status"], "ok")
        self.assertGreaterEqual(result["result_count"], 1)
        self.assertEqual(result["results"][0]["law_name"], "출입국관리법")
        self.assertEqual(result["fallback_mode"], "mobile_gana_local_title_match")
        self.assertEqual(result["fallback_gana"], "cha")
        self.assertTrue(result["cloud_korean_query_recovered"])

        fallback_urls = [url for url in transport.urls if "mobileYn=Y" in url]
        self.assertTrue(fallback_urls)
        self.assertTrue(all("query=" not in url for url in fallback_urls))
        self.assertTrue(all("gana=cha" in url for url in fallback_urls))
        self.assertNotIn("test-registered-oc", json.dumps(result, ensure_ascii=False))

    def test_grounding_style_query_recovers_canonical_law_title(self):
        transport = RecordingTransport()
        result = lt.search_laws(
            "출입국관리법 체류자격외활동 허가",
            config=self.cfg,
            transport=transport,
        )
        self.assertEqual(result["status"], "ok")
        self.assertGreaterEqual(result["result_count"], 1)
        self.assertEqual(result["results"][0]["law_name"], "출입국관리법")

    def test_unknown_korean_law_does_not_false_positive_or_scan_forever(self):
        transport = EmptyDictionaryTransport()
        result = lt.search_laws("존재하지않는법령zzz", config=self.cfg, transport=transport)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], lt.LAW_API_NO_RESULTS)
        self.assertEqual(result["result_count"], 0)
        self.assertEqual(result["results"], [])
        # One primary Korean query + at most the two dictionary directions.
        self.assertLessEqual(len(transport.urls), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
