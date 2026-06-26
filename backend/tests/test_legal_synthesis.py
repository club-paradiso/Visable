"""Tests for the optional source-grounded LLM synthesis layer.

Covers services/legal_synthesis.py (mode resolution, source packet, JSON parse,
citation/safety validator) and the synthesis path of POST /api/legal/research.

No real LLM or LAW_API_OC is used: the provider call
(_openrouter_complete_with_candidates) and the law transport are mocked, so the
deterministic scaffold + synthesis pipeline are exercised fully offline.

Run: python3 backend/tests/test_legal_synthesis.py
"""
from __future__ import annotations

import asyncio
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
from services import legal_synthesis as LS  # noqa: E402
import paradiso_backend as P  # noqa: E402

LAW_JSON = json.dumps({"LawSearch": {"law": [{"법령명한글": "출입국관리법", "법령일련번호": "1", "법령구분명": "법률", "조문번호": "제46조", "조문내용": "강제퇴거 대상", "공포일자": "20240101"}]}})
PREC_JSON = json.dumps({"PrecSearch": {"prec": [{"사건명": "강제퇴거명령취소", "사건번호": "2020두12345", "법원명": "대법원", "판시사항": "재량 일탈", "판례상세링크": "https://www.law.go.kr/p"}]}})


def _law_transport(url, timeout):
    return law_tools.LawHttpResponse(ok=True, status_code=200, text=(PREC_JSON if "target=prec" in url else LAW_JSON))


def _packet():
    laws = [{"title": "출입국관리법", "type": "법률", "articleNo": "제46조", "snippet": "강제퇴거 대상", "sourceUrl": "https://www.law.go.kr/법령/x", "strength": "direct"}]
    precs = [{"title": "강제퇴거명령취소", "court": "대법원", "caseNumber": "2020두12345", "summary": "재량", "sourceUrl": "https://www.law.go.kr/p", "strength": "related"}]
    packet, used = LS.build_source_packet("강제퇴거 다툴 쟁점", mode="memo", depth="pro", locale="ko", laws=laws, precedents=precs)
    return packet, used


GOOD_SYN = {
    "summary": "출처 기반 정리", "issues": ["강제퇴거 쟁점"],
    "sourceBackedRules": [{"text": "출입국관리법 제46조 관련", "sourceIds": ["s1"]}],
    "analysis": [{"text": "2020두12345 참고", "sourceIds": ["s2"], "confidence": "low"}],
    "riskFlags": ["재입국 제한"], "missingFacts": ["송달일"], "nextQuestions": ["q"],
    "nextDocuments": ["d"], "limitations": ["참고용"], "caution": "최종 판단은 기관",
}


class SynthesisModeTests(unittest.TestCase):
    def test_fast_is_always_deterministic(self):
        self.assertEqual(LS.resolve_synthesis_mode(None, "fast", provider_configured=True, has_sources=True), "deterministic")
        self.assertEqual(LS.resolve_synthesis_mode("source_grounded_llm", "fast", provider_configured=True, has_sources=True), "deterministic")

    def test_basic_pro_need_provider_and_sources(self):
        self.assertEqual(LS.resolve_synthesis_mode(None, "basic", provider_configured=True, has_sources=True), "source_grounded_llm")
        self.assertEqual(LS.resolve_synthesis_mode(None, "pro", provider_configured=True, has_sources=True), "source_grounded_llm")
        self.assertEqual(LS.resolve_synthesis_mode(None, "basic", provider_configured=False, has_sources=True), "deterministic")
        self.assertEqual(LS.resolve_synthesis_mode(None, "pro", provider_configured=True, has_sources=False), "deterministic")

    def test_explicit_deterministic_wins(self):
        self.assertEqual(LS.resolve_synthesis_mode("deterministic", "pro", provider_configured=True, has_sources=True), "deterministic")


class SourcePacketTests(unittest.TestCase):
    def test_packet_only_contains_normalized_sources(self):
        packet, used = _packet()
        self.assertEqual([s["type"] for s in packet["sources"]], ["law", "precedent"])
        self.assertEqual(set(used.keys()), {"s1", "s2"})
        for s in packet["sources"]:
            self.assertIn("sourceId", s)
            self.assertIn(s["type"], LS.PACKET_TYPES)

    def test_regulation_type_for_decree(self):
        packet, _ = LS.build_source_packet("x", mode="memo", depth="pro", locale="ko",
                                           laws=[{"title": "출입국관리법 시행령", "snippet": "y"}])
        self.assertEqual(packet["sources"][0]["type"], "regulation")


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.packet, _ = _packet()

    def test_valid_json_passes(self):
        ok, reason, cleaned = LS.validate_synthesis(GOOD_SYN, packet=self.packet, locale="ko")
        self.assertTrue(ok, reason)
        self.assertEqual(cleaned["summary"], "출처 기반 정리")

    def test_unsupported_source_id_fails(self):
        bad = {**GOOD_SYN, "analysis": [{"text": "x", "sourceIds": ["s9"], "confidence": "low"}]}
        ok, reason, _ = LS.validate_synthesis(bad, packet=self.packet, locale="ko")
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("unsupported_source_id"))

    def test_fabricated_article_fails(self):
        bad = {**GOOD_SYN, "sourceBackedRules": [{"text": "출입국관리법 제99조 적용", "sourceIds": ["s1"]}]}
        ok, reason, _ = LS.validate_synthesis(bad, packet=self.packet, locale="ko")
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("fabricated_article"))

    def test_fabricated_case_fails(self):
        bad = {**GOOD_SYN, "analysis": [{"text": "2019두99999 판례 참고", "sourceIds": ["s2"], "confidence": "low"}]}
        ok, reason, _ = LS.validate_synthesis(bad, packet=self.packet, locale="ko")
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("fabricated_case"))

    def test_forbidden_phrase_fails(self):
        for phrase in ("무조건 가능합니다", "guaranteed approval", "변호사 상담입니다"):
            bad = {**GOOD_SYN, "summary": phrase}
            ok, reason, _ = LS.validate_synthesis(bad, packet=self.packet, locale="ko")
            self.assertFalse(ok, phrase)
            self.assertTrue(reason.startswith("forbidden_phrase"), phrase)

    def test_raw_html_fails(self):
        bad = {**GOOD_SYN, "caution": "<script>alert(1)</script>"}
        ok, reason, _ = LS.validate_synthesis(bad, packet=self.packet, locale="ko")
        self.assertFalse(ok)
        self.assertEqual(reason, "raw_html")

    def test_parse_json_tolerates_fences(self):
        self.assertIsNotNone(LS.parse_synthesis_json('```json\n{"summary":"hi"}\n```'))
        self.assertIsNotNone(LS.parse_synthesis_json('prose {"summary":"hi"} more'))
        self.assertIsNone(LS.parse_synthesis_json("no json here"))

    # ---- red-team hardening regressions ----
    def test_forbidden_phrase_spacing_evasion_fails(self):
        for evade in ("반드시  승인", "반 드시 승인", "100 % 가능", "승소 가능합니다"):
            bad = {**GOOD_SYN, "summary": "출처 정리 " + evade}
            ok, reason, _ = LS.validate_synthesis(bad, packet=self.packet, locale="ko")
            self.assertFalse(ok, "should reject: " + evade)

    def test_forbidden_pattern_variants_fail(self):
        for evade in ("승인이 보장됩니다", "you will  win this case", "we guarantee approval", "법률 자문을 제공합니다"):
            bad = {**GOOD_SYN, "analysis": [{"text": evade, "sourceIds": ["s1"], "confidence": "low"}]}
            ok, reason, _ = LS.validate_synthesis(bad, packet=self.packet, locale="ko")
            self.assertFalse(ok, "should reject: " + evade)

    def test_phantom_bracket_source_in_prose_fails(self):
        bad = {**GOOD_SYN, "summary": "출처 [s9] 에 따르면"}
        ok, reason, _ = LS.validate_synthesis(bad, packet=self.packet, locale="ko")
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("unsupported_source_id"))

    def test_broad_case_format_fabrication_fails(self):
        bad = {**GOOD_SYN, "analysis": [{"text": "2021나56789 판례 참고", "sourceIds": ["s2"], "confidence": "low"}]}
        ok, reason, _ = LS.validate_synthesis(bad, packet=self.packet, locale="ko")
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("fabricated_case"))

    def test_plain_date_does_not_false_trigger(self):
        good = {**GOOD_SYN, "missingFacts": ["2024년 3월 출국 여부", "2023년 12월 신청 여부"]}
        ok, reason, _ = LS.validate_synthesis(good, packet=self.packet, locale="ko")
        self.assertTrue(ok, "plain dates must not be flagged as fabricated cases: " + reason)


class SynthesisEndpointTests(unittest.TestCase):
    def setUp(self):
        self._oc = os.environ.get("LAW_API_OC")
        self._key = os.environ.get("LAW_API_KEY")
        self._t = law_tools._default_transport
        self._llm = P._openrouter_complete_with_candidates
        self._provider = P.OPENROUTER_API_KEY
        os.environ["LAW_API_OC"] = "test-oc"
        os.environ.pop("LAW_API_KEY", None)
        law_tools._default_transport = _law_transport
        self.client = TestClient(P.app)

    def tearDown(self):
        law_tools._default_transport = self._t
        P._openrouter_complete_with_candidates = self._llm
        P.OPENROUTER_API_KEY = self._provider
        for name, val in (("LAW_API_OC", self._oc), ("LAW_API_KEY", self._key)):
            if val is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = val

    def _spy(self, answer=None, ok=True, record=None):
        async def fn(prompt, requested_model=None, candidate_models=None, max_tokens=None):
            if record is not None:
                record.append(prompt)
            return {"ok": ok, "answer": answer, "final_model": "test-model"}
        return fn

    def test_llm_not_called_without_provider(self):
        P.OPENROUTER_API_KEY = None
        calls = []
        P._openrouter_complete_with_candidates = self._spy(answer=json.dumps(GOOD_SYN), record=calls)
        r = self.client.post("/api/legal/research", json={"question": "강제퇴거 다툴 쟁점 정리", "depth": "pro"})
        body = r.json()
        self.assertEqual(body["synthesisStatus"], "deterministic")
        self.assertFalse(body["providerConfigured"])
        self.assertEqual(calls, [], "LLM must not be called when no provider is configured")

    def test_llm_not_called_without_sources(self):
        # No LAW_API_OC → no retrieval → no sources → synthesis must not call the LLM.
        os.environ.pop("LAW_API_OC", None)
        os.environ.pop("LAW_API_KEY", None)
        P.OPENROUTER_API_KEY = "k"
        calls = []
        P._openrouter_complete_with_candidates = self._spy(answer=json.dumps(GOOD_SYN), record=calls)
        r = self.client.post("/api/legal/research", json={"question": "강제퇴거 다툴 쟁점 정리", "depth": "pro"})
        self.assertEqual(r.json()["synthesisStatus"], "deterministic")
        self.assertEqual(calls, [], "LLM must not be called when no sources were retrieved")

    def test_valid_synthesis_returned(self):
        P.OPENROUTER_API_KEY = "k"
        P._openrouter_complete_with_candidates = self._spy(answer=json.dumps(GOOD_SYN))
        r = self.client.post("/api/legal/research", json={"question": "강제퇴거 다툴 쟁점 정리", "depth": "pro"})
        body = r.json()
        self.assertEqual(body["synthesisStatus"], "llm")
        self.assertTrue(body["synthesis"])
        self.assertEqual(body["synthesis"]["summary"], "출처 기반 정리")
        self.assertTrue(body["laws"], "deterministic source cards remain present")
        self.assertTrue(body.get("synthesisSources"))

    def test_validation_failure_falls_back(self):
        P.OPENROUTER_API_KEY = "k"
        bad = {**GOOD_SYN, "summary": "출입국관리법 제999조에 따라 무조건 가능합니다"}
        P._openrouter_complete_with_candidates = self._spy(answer=json.dumps(bad))
        r = self.client.post("/api/legal/research", json={"question": "강제퇴거 다툴 쟁점 정리", "depth": "pro"})
        body = r.json()
        self.assertEqual(body["synthesisStatus"], "validation_failed")
        self.assertTrue(body["synthesisWarning"])
        self.assertIsNone(body["synthesis"])
        self.assertTrue(body["laws"], "deterministic content remains on validation failure")

    def test_llm_failure_falls_back(self):
        P.OPENROUTER_API_KEY = "k"
        P._openrouter_complete_with_candidates = self._spy(answer=None, ok=False)
        r = self.client.post("/api/legal/research", json={"question": "강제퇴거 다툴 쟁점 정리", "depth": "pro"})
        self.assertEqual(r.json()["synthesisStatus"], "deterministic")

    def test_explicit_deterministic_skips_llm(self):
        P.OPENROUTER_API_KEY = "k"
        calls = []
        P._openrouter_complete_with_candidates = self._spy(answer=json.dumps(GOOD_SYN), record=calls)
        r = self.client.post("/api/legal/research", json={"question": "강제퇴거 다툴 쟁점 정리", "depth": "pro", "synthesis": "deterministic"})
        self.assertEqual(r.json()["synthesisStatus"], "deterministic")
        self.assertEqual(calls, [])

    def test_oc_never_leaks_with_synthesis(self):
        P.OPENROUTER_API_KEY = "k"
        P._openrouter_complete_with_candidates = self._spy(answer=json.dumps(GOOD_SYN))
        r = self.client.post("/api/legal/research", json={"question": "강제퇴거 다툴 쟁점 정리", "depth": "pro"})
        self.assertNotIn("test-oc", r.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
