"""Tests for the public legal source search endpoints.

Covers the Waymaker "법령·판례 근거 검색 / Legal source search" proxy:
  * empty query is rejected
  * missing LAW_API_OC returns a safe, exact config-error envelope
  * law search normalizes upstream results into LegalLawResult cards
  * precedent search normalizes upstream results into LegalPrecedentResult cards
  * upstream failure / timeout returns safe JSON and never crashes
  * the OC credential is never echoed in any response body
  * the query is length-capped

All upstream HTTP is replaced with an in-memory transport, so these tests run
fully offline with no real LAW_API_OC. Run:

    python3 backend/tests/test_legal_source_search_api.py
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
import services.law_tools as law_tools  # noqa: E402
import paradiso_backend as P  # noqa: E402


LAW_JSON = json.dumps({
    "LawSearch": {"law": [{
        "법령명한글": "출입국관리법",
        "법령일련번호": "001234",
        "법령구분명": "법률",
        "공포일자": "20240101",
        "시행일자": "20240701",
        "소관부처명": "법무부",
        "조문내용": "외국인의 입국과 체류에 관한 사항",
    }]},
})
PREC_JSON = json.dumps({
    "PrecSearch": {"prec": [{
        "사건명": "체류기간연장불허처분취소",
        "사건번호": "2020두12345",
        "법원명": "대법원",
        "선고일자": "20210115",
        "판시사항": "재량권 일탈·남용 여부",
        "판례상세링크": "https://www.law.go.kr/precInfoP.do?precSeq=999",
    }]},
})
PREC_RELATIVE_DUP_JSON = json.dumps({
    "PrecSearch": {"prec": [
        {
            "사건명": "출입국관리법위반", "사건번호": "2021도404", "법원명": "대법원",
            "선고일자": "20211028", "판례일련번호": "231051",
            "판시사항": "목록 응답의 판시사항은 본문이 아니다",
            "판례상세링크": "/DRF/lawService.do?target=prec&ID=231051&type=HTML",
        },
        {
            "사건명": "출입국관리법위반", "사건번호": "2021도404", "법원명": "대법원",
            "선고일자": "2021.10.28", "판례일련번호": "231052",
            "판례상세링크": "/DRF/lawService.do?target=prec&ID=231052&type=HTML",
        },
    ]},
}, ensure_ascii=False)
PREC_BODY_JSON = json.dumps({
    "PrecService": {"prec": {
        "사건명": "출입국관리법위반", "사건번호": "2021도404", "법원명": "대법원",
        "선고일자": "20211028", "판례일련번호": "231051",
        "판시사항": "쟁점", "판결요지": "공식 상세 본문에서 확인된 요지",
        "판례상세링크": "/DRF/lawService.do?target=prec&ID=231051&type=HTML",
    }},
}, ensure_ascii=False)


def _transport(payload, *, ok=True, status=200, err=""):
    def send(url, timeout):  # signature: (url, timeout) -> LawHttpResponse
        return law_tools.LawHttpResponse(ok=ok, status_code=status, text=payload, error_type=err)
    return send


class LegalSourceSearchApiTests(unittest.TestCase):
    def setUp(self):
        self._saved_oc = os.environ.get("LAW_API_OC")
        self._saved_key = os.environ.get("LAW_API_KEY")
        self._saved_transport = law_tools._default_transport
        os.environ["LAW_API_OC"] = "test-oc-secret"
        os.environ.pop("LAW_API_KEY", None)
        self.client = TestClient(P.app)

    def tearDown(self):
        law_tools._default_transport = self._saved_transport
        for name, value in (("LAW_API_OC", self._saved_oc), ("LAW_API_KEY", self._saved_key)):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    # ---- empty query --------------------------------------------------
    def test_empty_law_query_rejected(self):
        r = self.client.get("/api/legal/laws/search", params={"q": "   "})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["ok"], False)
        self.assertEqual(r.json()["error"], "empty_query")

    def test_empty_precedent_query_rejected(self):
        r = self.client.get("/api/legal/precedents/search", params={"q": ""})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "empty_query")

    # ---- missing credential -------------------------------------------
    def test_missing_oc_returns_safe_config_error(self):
        os.environ.pop("LAW_API_OC", None)
        os.environ.pop("LAW_API_KEY", None)
        for path in ("/api/legal/laws/search", "/api/legal/precedents/search"):
            r = self.client.get(path, params={"q": "출입국관리법"})
            self.assertEqual(r.status_code, 200, path)
            body = r.json()
            self.assertEqual(body["ok"], False, path)
            self.assertEqual(body["error"], "LAW_API_OC is not configured", path)
            self.assertEqual(body["results"], [], path)

    # ---- law search normalization -------------------------------------
    def test_law_search_normalizes_results(self):
        law_tools._default_transport = _transport(LAW_JSON)
        r = self.client.get("/api/legal/laws/search", params={"q": "출입국관리법"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["kind"], "laws")
        self.assertEqual(body["count"], 1)
        card = body["results"][0]
        for field in ("id", "title", "type", "snippet", "promulgationDate", "effectiveDate", "sourceUrl", "rawSource"):
            self.assertIn(field, card)
        self.assertEqual(card["title"], "출입국관리법")
        self.assertEqual(card["rawSource"], "law.go.kr")
        self.assertTrue(card["sourceUrl"].startswith("https://www.law.go.kr/"))

    # ---- precedent search normalization -------------------------------
    def test_precedent_search_normalizes_results(self):
        law_tools._default_transport = _transport(PREC_JSON)
        r = self.client.get("/api/legal/precedents/search", params={"q": "체류기간 연장 불허"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["kind"], "precedents")
        self.assertEqual(body["count"], 1)
        card = body["results"][0]
        for field in ("id", "title", "court", "decisionDate", "caseNumber", "summary", "sourceUrl", "rawSource"):
            self.assertIn(field, card)
        self.assertEqual(card["court"], "대법원")
        self.assertEqual(card["caseNumber"], "2020두12345")
        self.assertEqual(card["summary"], "", "list-only results must not expose holding text")

    def test_relative_precedent_url_is_clickable_and_duplicate_removed(self):
        law_tools._default_transport = _transport(PREC_RELATIVE_DUP_JSON)
        r = self.client.get("/api/legal/precedents/search", params={"q": "출입국관리법"})
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["count"], 1)
        card = body["results"][0]
        self.assertEqual(
            card["sourceUrl"],
            "https://www.law.go.kr/DRF/lawService.do?target=prec&ID=231051&type=HTML",
        )
        self.assertEqual(card["summary"], "")

    def test_precedent_detail_exposes_bounded_body_only_after_detail_lookup(self):
        law_tools._default_transport = _transport(PREC_BODY_JSON)
        r = self.client.get("/api/legal/precedents/detail", params={"id": "231051"})
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["count"], 1)
        self.assertIn("공식 상세 본문", body["results"][0]["summary"])

    # ---- credential never leaks ---------------------------------------
    def test_oc_never_appears_in_response_body(self):
        law_tools._default_transport = _transport(LAW_JSON)
        r = self.client.get("/api/legal/laws/search", params={"q": "출입국관리법"})
        self.assertNotIn("test-oc-secret", r.text)

    # ---- upstream failure is graceful ---------------------------------
    def test_upstream_timeout_is_safe(self):
        law_tools._default_transport = _transport("", ok=False, status=0, err="timeout")
        for path in ("/api/legal/laws/search", "/api/legal/precedents/search"):
            r = self.client.get(path, params={"q": "국적법"})
            self.assertEqual(r.status_code, 200, path)
            body = r.json()
            self.assertFalse(body["ok"], path)
            self.assertEqual(body["error"], "search_failed", path)
            self.assertEqual(body["results"], [], path)

    def test_upstream_http_error_is_safe(self):
        law_tools._default_transport = _transport("<html>500</html>", ok=False, status=500, err="http_error")
        r = self.client.get("/api/legal/laws/search", params={"q": "난민법"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["ok"])

    # ---- no results is a successful empty search ----------------------
    def test_no_results_is_ok_empty(self):
        law_tools._default_transport = _transport(json.dumps({"LawSearch": {}}))
        r = self.client.get("/api/legal/laws/search", params={"q": "존재하지않는법령zzz"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["results"], [])

    # ---- query length cap ---------------------------------------------
    def test_query_is_length_capped(self):
        law_tools._default_transport = _transport(json.dumps({"LawSearch": {}}))
        long_q = "출" * 500
        r = self.client.get("/api/legal/laws/search", params={"q": long_q})
        self.assertEqual(r.status_code, 200)
        self.assertLessEqual(len(r.json()["query"]), 150)


if __name__ == "__main__":
    unittest.main(verbosity=2)
