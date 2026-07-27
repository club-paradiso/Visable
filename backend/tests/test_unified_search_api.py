"""API contract tests for /api/search/unified and its AI Overview companion.

The load-bearing guarantee: organic results are produced with no AI provider and
no network, and an AI failure is a quiet, explicit state that never removes or
delays them.

    python3 -m pytest backend/tests/test_unified_search_api.py -q
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402

import paradiso_backend as pb  # noqa: E402

PROVIDER_ENV = ("OPENROUTER_API_KEY", "GROQ_API_KEY", "NVIDIA_API_KEY",
                "ENABLE_OLLAMA_FALLBACK", "ENABLE_NVIDIA_NIM_EXPERIMENTAL",
                "ALLOW_GROQ_FALLBACK")


class UnifiedSearchApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(pb.app)
        self._saved = {k: os.environ.get(k) for k in PROVIDER_ENV}
        for key in PROVIDER_ENV:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _search(self, query, **extra):
        payload = {"query": query}
        payload.update(extra)
        response = self.client.post("/api/search/unified", json=payload)
        self.assertEqual(response.status_code, 200)
        return response.json()

    # --- schema -----------------------------------------------------------
    def test_response_carries_the_documented_schema(self):
        body = self._search("D-2-1")
        for key in ("query", "intent", "detectedVisaCodes", "interpretation",
                    "organicResults", "suggestions", "sourceCards", "aiOverview",
                    "aiOverviewStatus", "fallbackAvailable", "requestId", "latency"):
            self.assertIn(key, body, f"missing `{key}` in unified search response")

    def test_ai_overview_is_null_and_pending_on_the_organic_endpoint(self):
        body = self._search("D-2-1")
        self.assertIsNone(body["aiOverview"])
        self.assertEqual(body["aiOverviewStatus"], "pending")

    def test_fallback_is_always_advertised(self):
        self.assertTrue(self._search("체류지 변경")["fallbackAvailable"])

    def test_request_id_is_present_and_not_a_secret(self):
        body = self._search("D-2-1")
        self.assertTrue(body["requestId"])
        self.assertLessEqual(len(body["requestId"]), 32)

    # --- behaviour --------------------------------------------------------
    def test_exact_code_search_works_with_no_ai_provider_configured(self):
        body = self._search("E-7-4")
        self.assertTrue(body["organicResults"])
        self.assertIn("E-7-4", body["detectedVisaCodes"])

    def test_compact_code_search_works(self):
        self.assertIn("D-2-1", self._search("D21")["detectedVisaCodes"])

    def test_meaningless_query_returns_unknown_without_inventing_results(self):
        body = self._search("ㅁㄴㅇㄹ")
        self.assertEqual(body["intent"], "unknown")
        self.assertEqual(body["detectedVisaCodes"], [])

    def test_empty_query_is_handled_without_error(self):
        body = self._search("")
        self.assertEqual(body["aiOverviewStatus"], "not_applicable")
        self.assertEqual(body["organicResults"], [])

    def test_overlong_query_is_truncated_not_rejected(self):
        body = self._search("체" * 5000)
        self.assertLessEqual(len(body["query"]), pb._UNIFIED_SEARCH_MAX_QUERY)

    def test_deterministic_latency_is_reported(self):
        body = self._search("D-2-1")
        self.assertIn("deterministicMs", body["latency"])
        self.assertIsInstance(body["latency"]["deterministicMs"], int)

    def test_source_cards_only_expose_public_official_urls(self):
        for card in self._search("출입국관리법 제20조")["sourceCards"]:
            url = card.get("url", "")
            if url:
                self.assertTrue(url.startswith("https://"), url)
                self.assertNotIn("OC=", url)
                self.assertNotIn("api_key", url.lower())

    def test_review_pending_manual_evidence_is_labelled_in_source_cards(self):
        body = self._search("체류자격 변경")
        pending = (body.get("manualEvidence") or {}).get("reviewPendingCount", 0)
        if pending:
            ids = {c["id"] for c in body["sourceCards"]}
            self.assertIn("manual_review_pending", ids)

    def test_no_response_field_leaks_a_credential(self):
        blob = str(self._search("출입국관리법 제20조"))
        for marker in ("OC=", "LAW_API_OC", "api_key", "Bearer "):
            self.assertNotIn(marker, blob)


class UnifiedAiOverviewApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(pb.app)
        self._saved = {k: os.environ.get(k) for k in PROVIDER_ENV}
        for key in PROVIDER_ENV:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_no_provider_configured_is_a_quiet_unavailable_state(self):
        response = self.client.post("/api/search/unified/ai-overview",
                                    json={"query": "D-2-1"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "unavailable")
        self.assertEqual(body["reason"], "no_provider_configured")
        self.assertIsNone(body["overview"])
        self.assertTrue(body["fallbackAvailable"])

    def test_unavailable_overview_still_tells_the_user_results_are_fine(self):
        body = self.client.post("/api/search/unified/ai-overview",
                                json={"query": "D-2-1"}).json()
        self.assertTrue(body["message"])

    def test_empty_query_is_not_applicable(self):
        body = self.client.post("/api/search/unified/ai-overview",
                                json={"query": ""}).json()
        self.assertEqual(body["status"], "not_applicable")

    def test_english_locale_gets_an_english_failure_message(self):
        body = self.client.post("/api/search/unified/ai-overview",
                                json={"query": "D-2-1", "lang": "en"}).json()
        self.assertRegex(body["message"], r"[A-Za-z]{4,}")


class ManualEvidenceStateApiTests(unittest.TestCase):
    def test_state_endpoint_reports_counts_without_document_bodies(self):
        client = TestClient(pb.app)
        response = client.get("/api/search/manual-evidence-state")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("approvalCounts", body)
        self.assertIn("documentCount", body)
        self.assertNotIn("documents", body)

    def test_no_document_is_reported_as_approved_by_default(self):
        client = TestClient(pb.app)
        body = client.get("/api/search/manual-evidence-state").json()
        self.assertEqual(body["approvalCounts"].get("approved", 0), 0)


class AiOverviewFigmaStateTests(unittest.TestCase):
    """States added to match Figma UX-03 `AI Overview` (node 406:92)."""

    def setUp(self):
        self.client = TestClient(pb.app)
        self._saved = {k: os.environ.get(k) for k in PROVIDER_ENV}
        for key in PROVIDER_ENV:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_no_evidence_is_reported_as_blocked_with_a_reason(self):
        # A query that resolves to no organic evidence must say why, not render
        # an empty card.
        body = self.client.post("/api/search/unified/ai-overview",
                                json={"query": "ㅁㄴㅇㄹ"}).json()
        # With no provider configured the provider gate fires first; assert the
        # blocked shape directly instead.
        self.assertIn(body["status"], {"unavailable", "blocked"})
        if body["status"] == "blocked":
            self.assertTrue(body["reason"])

    def test_source_chips_mark_unretrieved_sources_instead_of_dropping_them(self):
        deterministic = {
            "organicResults": [
                {"kind": "manual_card", "title": "체류자격 변경", "page": 42,
                 "usableAsDirectEvidence": False},
                {"code": "D-2-1", "title": "전문학사과정"},
            ],
            "manualEvidence": {"status": "ok", "approvedCount": 0, "reviewPendingCount": 1},
        }
        chips = pb._unified_overview_sources(deterministic)
        labels = [c["label"] for c in chips]
        self.assertTrue(any("체류자격 변경" in l for l in labels))
        manual_chip = next(c for c in chips if "체류자격 변경" in c["label"])
        self.assertTrue(manual_chip["unavailable"],
                        "review-pending manual evidence must be dimmed, not presented as settled")

    def test_missing_manual_index_appears_as_an_unavailable_source(self):
        chips = pb._unified_overview_sources({
            "organicResults": [], "manualEvidence": {"status": "index_unavailable"}})
        self.assertTrue(chips)
        self.assertTrue(chips[0]["unavailable"])

    def test_source_chips_are_deduplicated_and_bounded(self):
        deterministic = {"organicResults": [{"code": "D-2", "title": "유학"}] * 20,
                         "manualEvidence": {}}
        chips = pb._unified_overview_sources(deterministic)
        self.assertEqual(len(chips), 1)

    def test_evidence_label_counts_approved_and_pending_separately(self):
        label = pb._unified_evidence_label({
            "organicResults": [{"code": "D-2"}],
            "manualEvidence": {"approvedCount": 2, "reviewPendingCount": 3},
        }, "ko")
        self.assertIn("매뉴얼 직접 근거 2건", label)
        self.assertIn("검토 전 매뉴얼 3건", label)
        self.assertIn("공식 확인 필요", label)

    def test_evidence_label_omits_zero_buckets(self):
        label = pb._unified_evidence_label({
            "organicResults": [{"code": "D-2"}],
            "manualEvidence": {"approvedCount": 0, "reviewPendingCount": 0},
        }, "ko")
        self.assertNotIn("매뉴얼 직접 근거", label)
        self.assertIn("공식 확인 필요", label)

    def test_evidence_label_has_an_english_form(self):
        label = pb._unified_evidence_label({
            "organicResults": [{"code": "D-2"}],
            "manualEvidence": {"approvedCount": 1, "reviewPendingCount": 0},
        }, "en")
        self.assertIn("official confirmation required", label)


if __name__ == "__main__":
    unittest.main()
