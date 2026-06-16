"""Tests for the legal evidence service (Korean case law 판례 + 재결례).

All tests are offline: the HTTP boundary is the injectable ``transport`` callable
and ``LAW_API_OC`` is a non-secret sentinel. No real network, no real OC, no
secrets in fixtures. Covers: API client (mocked), LAW_API_OC-as-OC, missing-OC
graceful degradation, normalization, ranking, query expansion, chunking, safety
refusal for asylum-gaming, caching, and retry/backoff.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import legal_evidence as le  # noqa: E402
from services.grounding_config import GroundingConfig  # noqa: E402
from services import law_tools as lt  # noqa: E402

ST = le.LegalEvidenceSourceType


def _cfg(*, oc: str = "oc-sentinel-zzz", mode: str = "enabled", ttl: int = 0) -> GroundingConfig:
    return GroundingConfig(law_api_oc=oc, mode=mode, cache_ttl_seconds=ttl)


def _no_oc_cfg(mode: str = "enabled") -> GroundingConfig:
    return GroundingConfig(mode=mode)


def _resp(text: str, *, ok: bool = True, status: int = 200, error_type: str = "") -> lt.LawHttpResponse:
    return lt.LawHttpResponse(ok=ok, status_code=status, text=text, error_type=error_type)


_PREC_LIST = json.dumps({"PrecSearch": {"prec": [
    {"판례정보일련번호": "228541", "사건명": "체류기간연장불허가처분취소",
     "사건번호": "2019두12345", "법원명": "대법원", "법원종류코드": "400201",
     "사건종류명": "행정", "선고일자": "20210311", "판결요지": "체류기간 연장 불허가 처분의 재량 한계..."},
    {"판례정보일련번호": "111", "사건명": "기타사건", "사건번호": "2005구합1",
     "법원명": "서울행정법원", "선고일자": "20050101", "판결요지": "..."},
]}}, ensure_ascii=False)

_PREC_BODY = json.dumps({"PrecService": {
    "판례정보일련번호": "228541", "사건명": "체류기간연장불허가처분취소", "사건번호": "2019두12345",
    "선고일자": "20210311", "선고": "선고", "법원명": "대법원", "법원종류코드": "400201",
    "사건종류명": "행정", "사건종류코드": "2", "판결유형": "판결",
    "판시사항": "체류기간 연장허가 여부는 행정청의 재량에 속한다.",
    "판결요지": "재량권의 일탈·남용이 없는 한 위법하지 않다.",
    "참조조문": "출입국관리법 제25조", "참조판례": "대법원 2016두1234",
    "판례내용": (
        "원고는 D-2 체류자격으로 입국하여 학업을 수행하던 중 체류기간 연장을 신청하였다. "
        "피고는 원고의 학업 실태와 체류 목적의 변경 가능성 등을 종합적으로 고려하여 이를 불허가하였다. "
        "원고는 이 사건 처분이 재량권을 일탈·남용한 것으로서 위법하다고 주장하며 그 취소를 구하였다. "
        "법원은 체류기간 연장허가 여부가 출입국관리행정의 특수성에 비추어 행정청의 광범위한 재량에 속한다고 보았다. "
        "외국인의 입국과 체류 허가 여부는 주권국가의 고유한 권한에 속하는 사항이라는 점도 함께 설시하였다. "
        "다만 그러한 재량권의 행사에도 한계가 있어 재량권의 일탈·남용이 인정되는 경우에는 처분이 위법할 수 있다고 판단하였다. "
        "이 사건에서 원고가 제출한 자료만으로는 학업을 정상적으로 수행하였다고 보기 어려운 사정이 확인되었다. "
        "또한 체류 목적이 사실상 변경되었을 가능성을 배제하기 어렵다고 보았다. "
        "이러한 사정을 종합하면 피고의 이 사건 처분에 재량권의 일탈·남용이 있다고 인정되지 아니한다. "
        "한편 원고는 동일한 사안에 관한 다른 사건의 결론을 들어 평등원칙 위반을 주장하나, 그 사건과 이 사건은 사실관계가 달라 그대로 적용하기 어렵다. "
        "또한 원고는 신뢰보호원칙 위반도 주장하였으나, 피고가 연장을 보장하는 공적인 견해를 표명하였다고 볼 자료가 없다. "
        "체류기간 연장 불허가로 인하여 원고가 입게 되는 불이익이 공익에 비하여 현저히 크다고 보기도 어렵다. "
        "그 밖에 원고가 주장하는 여러 사정을 모두 고려하더라도 이 사건 처분이 위법하다고 보기는 어렵다. "
        "따라서 원고의 주장은 모두 이유 없으므로 원고의 청구를 기각하기로 하여 주문과 같이 판결한다."
    ),
}}, ensure_ascii=False)

# The full reasoning body (collapsed whitespace), used to assert it is reduced
# to a few bounded windows and never emitted whole.
_PREC_BODY_FULL = " ".join(json.loads(_PREC_BODY)["PrecService"]["판례내용"].split())

_ADMIN_LIST = json.dumps({"DeccSearch": {"decc": [
    {"재결례일련번호": "9001", "사건명": "체류기간연장불허가처분 취소청구",
     "사건번호": "2021행심123", "재결청": "중앙행정심판위원회", "의결일자": "20211201",
     "처분청": "서울출입국·외국인청", "처분일자": "20210901",
     "재결요지": "처분에 재량 일탈·남용이 없어 청구를 기각한다.",
     "주문": "청구를 기각한다.", "청구취지": "처분의 취소를 구한다.", "관계법령": "출입국관리법 제25조",
     "원본다운로드URL": "https://www.law.go.kr/download?OC=oc-sentinel-zzz&id=9001",
     "데이터기준일시": "2026-06-01 00:00:00"},
]}}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Config / OC handling
# ---------------------------------------------------------------------------
class ConfigAndOcTests(unittest.TestCase):
    def setUp(self):
        le.reset_legal_evidence_cache_for_tests()

    def test_missing_oc_does_not_crash_and_reports_not_configured(self):
        r = le.retrieve_legal_evidence("체류기간 연장 불허가 판례", config=_no_oc_cfg())
        self.assertEqual(r.status, "not_configured")
        self.assertEqual(r.cases, [])
        self.assertIn("LAW_API_OC_MISSING_LEGAL_EVIDENCE_DISABLED", r.warnings)

    def test_disabled_mode_reports_disabled(self):
        r = le.retrieve_legal_evidence("체류기간 연장 불허가 판례", config=_cfg(mode="disabled"))
        self.assertEqual(r.status, "disabled")

    def test_client_is_available_only_with_oc_and_enabled(self):
        self.assertTrue(le.LawOpenDataClient(config=_cfg()).is_available)
        self.assertFalse(le.LawOpenDataClient(config=_no_oc_cfg()).is_available)
        self.assertFalse(le.LawOpenDataClient(config=_cfg(mode="disabled")).is_available)

    def test_law_api_oc_is_used_as_the_oc_query_value(self):
        captured = {}

        def capture(url, timeout):
            captured["url"] = url
            return _resp(_PREC_LIST)

        cli = le.LawOpenDataClient(config=_cfg(oc="oc-sentinel-zzz"), transport=capture)
        env = cli.search_cases("체류기간 연장", source_type=ST.PRECEDENT)
        # The OC reaches the outbound URL as the OC= param ...
        self.assertIn("OC=oc-sentinel-zzz", captured["url"])
        self.assertIn("target=prec", captured["url"])
        # ... but is NEVER exposed in the normalized envelope / sanitized url.
        self.assertNotIn("oc-sentinel-zzz", env["sanitized_url"])
        self.assertNotIn("oc-sentinel-zzz", json.dumps(env, default=str, ensure_ascii=False))

    def test_no_new_env_var_introduced(self):
        # The service must rely on LAW_API_OC (via grounding_config), never a new
        # LAW_OPEN_API_OC-style variable.
        src = (BACKEND_DIR / "services" / "legal_evidence.py").read_text(encoding="utf-8")
        self.assertNotIn("LAW_OPEN_API_OC", src)
        self.assertIn("law_api_credential", " ".join([
            (BACKEND_DIR / "services" / "law_tools.py").read_text(encoding="utf-8"),
        ]))

    def test_preflight_is_secret_free(self):
        pf = le.legal_evidence_preflight(config=_cfg(oc="top-secret-oc"))
        self.assertTrue(pf["available"])
        self.assertTrue(pf["law_api_configured"])
        self.assertNotIn("top-secret-oc", json.dumps(pf, ensure_ascii=False))


# ---------------------------------------------------------------------------
# API client (mocked transport)
# ---------------------------------------------------------------------------
class ClientSearchTests(unittest.TestCase):
    def setUp(self):
        le.reset_legal_evidence_cache_for_tests()

    def _cli(self, transport):
        return le.LawOpenDataClient(config=_cfg(), transport=transport)

    def test_search_precedent_success_normalizes_cases(self):
        env = self._cli(lambda u, t: _resp(_PREC_LIST)).search_cases("체류기간 연장", source_type=ST.PRECEDENT)
        self.assertEqual(env["status"], "available")
        self.assertEqual(len(env["cases"]), 2)
        top = env["cases"][0]
        self.assertEqual(top.case_name, "체류기간연장불허가처분취소")
        self.assertEqual(top.case_number, "2019두12345")
        self.assertEqual(top.court, "대법원")
        self.assertEqual(top.source_type, ST.PRECEDENT)
        self.assertEqual(top.result_kind, "list_result")

    def test_search_no_results(self):
        empty = json.dumps({"PrecSearch": {"totalCnt": "0"}}, ensure_ascii=False)
        env = self._cli(lambda u, t: _resp(empty)).search_cases("zzz", source_type=ST.PRECEDENT)
        self.assertEqual(env["status"], "no_results")
        self.assertEqual(env["cases"], [])

    def test_search_http_error_is_unavailable_not_crash(self):
        env = self._cli(lambda u, t: _resp("", ok=False, status=403, error_type="http_error")).search_cases(
            "x", source_type=ST.PRECEDENT)
        self.assertEqual(env["status"], "unavailable")
        self.assertEqual(env["error_type"], lt.LAW_API_HTTP_ERROR)

    def test_search_blank_query_is_no_results(self):
        env = self._cli(lambda u, t: _resp(_PREC_LIST)).search_cases("  ", source_type=ST.PRECEDENT)
        self.assertEqual(env["status"], "no_results")

    def test_special_admin_appeal_without_target_is_unavailable(self):
        # No documented default target -> unavailable, not a crash, not invented.
        env = self._cli(lambda u, t: _resp(_PREC_LIST)).search_cases(
            "x", source_type=ST.SPECIAL_ADMINISTRATIVE_APPEAL)
        self.assertEqual(env["status"], "unavailable")
        self.assertIn("LEGAL_EVIDENCE_TARGET_NOT_CONFIGURED", env["warnings"])
        self.assertFalse(env["target_confirmed"])

    def test_two_step_body_fetch_parses_all_fields_and_chunks(self):
        cli = self._cli(lambda u, t: _resp(_PREC_BODY))
        case = cli.get_case_body("228541", source_type=ST.PRECEDENT)
        self.assertIsNotNone(case)
        self.assertEqual(case.result_kind, "body_result")
        self.assertEqual(case.holding, "체류기간 연장허가 여부는 행정청의 재량에 속한다.")
        self.assertEqual(case.summary, "재량권의 일탈·남용이 없는 한 위법하지 않다.")
        self.assertEqual(case.reference_statutes, "출입국관리법 제25조")
        self.assertEqual(case.reference_cases, "대법원 2016두1234")
        self.assertEqual(case.case_type_code, "2")
        self.assertEqual(case.decision_type, "판결")
        # Chunks prefer 판시사항/판결요지/참조조문 and include bounded reasoning windows.
        chunk_types = {c.chunk_type for c in case.chunks}
        self.assertIn("holding", chunk_types)
        self.assertIn("summary", chunk_types)
        self.assertIn("reference_statutes", chunk_types)
        self.assertIn("reasoning", chunk_types)
        # Reasoning is reduced to a few bounded windows (never the whole body).
        reasoning = [c for c in case.chunks if c.chunk_type == "reasoning"]
        self.assertTrue(reasoning)
        self.assertLessEqual(len(reasoning), 3)
        for c in case.chunks:
            self.assertLessEqual(len(c.text), 320)
        # The long body is genuinely reduced: the kept reasoning text is shorter
        # than the full body, and the full body never appears verbatim.
        joined_reasoning = " ".join(c.text for c in reasoning)
        self.assertLess(len(joined_reasoning), len(_PREC_BODY_FULL))
        self.assertNotIn(_PREC_BODY_FULL, " ".join(c.text for c in case.chunks))
        # The private reasoning_text is excluded from the public/LLM-facing projection.
        pub = json.dumps(case.to_public_dict(), ensure_ascii=False)
        self.assertNotIn(_PREC_BODY_FULL, pub)
        self.assertNotIn("reasoningText", pub)
        self.assertNotIn("reasoning_text", pub)

    def test_admin_appeal_body_fields_parse(self):
        # Admin-appeal target is env-overridable best-effort; with a mocked
        # response the normalizer still extracts the adjudication fields.
        cli = self._cli(lambda u, t: _resp(_ADMIN_LIST))
        env = cli.search_cases("체류기간 연장 불허가", source_type=ST.ADMINISTRATIVE_APPEAL)
        self.assertEqual(env["status"], "available")
        c = env["cases"][0]
        self.assertEqual(c.case_number, "2021행심123")
        self.assertEqual(c.ruling_authority, "중앙행정심판위원회")
        self.assertEqual(c.disposition_authority, "서울출입국·외국인청")
        self.assertEqual(c.order, "청구를 기각한다.")
        self.assertEqual(c.claim, "처분의 취소를 구한다.")
        self.assertEqual(c.reference_statutes, "출입국관리법 제25조")
        self.assertEqual(c.data_reference_datetime, "2026-06-01 00:00:00")
        # The download URL is sanitized (OC stripped).
        self.assertNotIn("oc-sentinel-zzz", c.source_download_url)

    def test_retry_with_backoff_recovers_from_transient_then_succeeds(self):
        calls = {"n": 0}

        def flaky(url, timeout):
            calls["n"] += 1
            if calls["n"] < 3:
                return _resp("", ok=False, status=0, error_type="timeout")
            return _resp(_PREC_LIST)

        cli = le.LawOpenDataClient(config=_cfg(), transport=flaky, max_retries=2, sleep=lambda s: None)
        env = cli.search_cases("x", source_type=ST.PRECEDENT)
        self.assertEqual(env["status"], "available")
        self.assertEqual(calls["n"], 3)

    def test_retry_exhausted_returns_unavailable(self):
        cli = le.LawOpenDataClient(
            config=_cfg(), transport=lambda u, t: _resp("", ok=False, status=0, error_type="timeout"),
            max_retries=1, sleep=lambda s: None,
        )
        env = cli.search_cases("x", source_type=ST.PRECEDENT)
        self.assertEqual(env["status"], "unavailable")
        self.assertEqual(env["error_type"], lt.LAW_API_TIMEOUT)

    def test_cache_avoids_repeat_calls(self):
        calls = {"n": 0}

        def counting(url, timeout):
            calls["n"] += 1
            return _resp(_PREC_LIST)

        cli = le.LawOpenDataClient(config=_cfg(ttl=600), transport=counting)
        cli.search_cases("동일질의", source_type=ST.PRECEDENT)
        cli.search_cases("동일질의", source_type=ST.PRECEDENT)
        self.assertEqual(calls["n"], 1)
        le.reset_legal_evidence_cache_for_tests()


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------
class NormalizationTests(unittest.TestCase):
    def test_normalize_requires_identity(self):
        self.assertIsNone(le.normalize_case({"무관": "값"}, source_type=ST.PRECEDENT, result_kind="list_result"))

    def test_normalize_list_item(self):
        c = le.normalize_case(
            {"사건명": "사건", "사건번호": "2020두1", "법원명": "대법원", "선고일자": "20200101"},
            source_type=ST.PRECEDENT, result_kind="list_result",
        )
        self.assertIsNotNone(c)
        self.assertEqual(c.case_name, "사건")
        self.assertEqual(c.result_kind, "list_result")

    def test_to_public_dict_excludes_raw_body_and_keeps_citation(self):
        c = le.normalize_case(
            {"사건명": "사건", "사건번호": "2020두1", "법원명": "대법원", "선고일자": "20200101",
             "판시사항": "쟁점", "판결요지": "요지"},
            source_type=ST.PRECEDENT, result_kind="body_result",
        )
        pub = c.to_public_dict()
        self.assertEqual(pub["citation"]["case_number"], "2020두1")
        self.assertIn("holding", pub)
        self.assertNotIn("판례내용", json.dumps(pub, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------
class RankingTests(unittest.TestCase):
    def _case(self, **kw):
        base = dict(source_type=ST.PRECEDENT)
        base.update(kw)
        return le.LegalCase(**base)

    def test_supreme_court_recent_outranks_district_old(self):
        a = self._case(case_name="체류기간 연장 불허가", court="대법원", decision_date="20210311",
                       summary="체류기간 연장 재량", reference_statutes="출입국관리법 제25조")
        b = self._case(case_name="무관", court="서울지방법원", decision_date="20030101", summary="기타")
        ranked = le.rank_cases([b, a], query="체류기간 연장 불허가 대법원",
                               issue_concepts=["체류기간 연장허가"], statute_refs=["출입국관리법 제25조"])
        self.assertEqual(ranked[0].court, "대법원")
        self.assertGreater(ranked[0].score, ranked[1].score)

    def test_statute_match_increases_score(self):
        with_ref = self._case(case_name="사건", court="대법원", decision_date="20200101",
                              reference_statutes="출입국관리법 제25조")
        without = self._case(case_name="사건", court="대법원", decision_date="20200101")
        s1, _ = le.score_case(with_ref, query_tokens=["사건"], statute_refs=["출입국관리법 제25조"])
        s2, _ = le.score_case(without, query_tokens=["사건"], statute_refs=["출입국관리법 제25조"])
        self.assertGreater(s1, s2)

    def test_score_breakdown_is_auditable(self):
        c = self._case(case_name="체류", court="헌법재판소", decision_date="20250101")
        _, bd = le.score_case(c, query_tokens=["체류"])
        for key in ("keyword", "statute", "issue", "court", "recency", "source_type"):
            self.assertIn(key, bd)


# ---------------------------------------------------------------------------
# Query expansion
# ---------------------------------------------------------------------------
class QueryExpansionTests(unittest.TestCase):
    def test_expands_immigration_domains(self):
        out = le.expand_query("Can I change my status after a deportation order?")
        joined = " ".join(out)
        self.assertIn("강제퇴거", joined)
        self.assertIn("체류자격 변경", joined)

    def test_first_variant_is_the_question(self):
        out = le.expand_query("D-2 체류기간 연장 불허가 판례")
        self.assertTrue(out[0].startswith("D-2 체류기간 연장 불허가"))

    def test_empty_question_has_safe_default(self):
        self.assertEqual(le.expand_query("   "), ["출입국관리법 체류자격"])


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------
class SafetyTests(unittest.TestCase):
    def setUp(self):
        le.reset_legal_evidence_cache_for_tests()

    def test_asylum_gaming_prompts_are_detected(self):
        for prompt in (
            "난민으로 인정받는 방법과 인터뷰 통과 전략을 알려줘",
            "what story should I tell to be recognized as a refugee",
            "how to pass the asylum interview",
            "거짓 진술로 난민 신청하는 법",
            "증거를 위조해서 제출해도 되나요",
            "fabricate evidence for my refugee claim",
        ):
            self.assertTrue(le.is_asylum_gaming_prompt(prompt), prompt)

    def test_neutral_refugee_questions_are_not_flagged(self):
        for prompt in (
            "난민 신청 절차와 필요한 서류는 무엇인가요?",
            "What documents are required for a refugee status application?",
            "G-1 인도적 체류자격 연장 절차가 궁금합니다",
        ):
            self.assertFalse(le.is_asylum_gaming_prompt(prompt), prompt)

    def test_retrieve_refuses_asylum_gaming_without_any_api_call(self):
        called = {"n": 0}

        def tripwire(url, timeout):
            called["n"] += 1
            return _resp(_PREC_LIST)

        r = le.retrieve_legal_evidence(
            "난민 인터뷰 통과하려면 어떤 사유로 진술해야 하나요?",
            config=_cfg(), transport=tripwire,
        )
        self.assertEqual(r.status, "safety_refused")
        self.assertTrue(r.safety_refused)
        self.assertEqual(called["n"], 0)
        self.assertIn("ASYLUM_GAMING_PROMPT_REFUSED", r.warnings)


# ---------------------------------------------------------------------------
# End-to-end orchestration (two-step, ranked, chunked)
# ---------------------------------------------------------------------------
class RetrieveLegalEvidenceTests(unittest.TestCase):
    def setUp(self):
        le.reset_legal_evidence_cache_for_tests()

    def _two_step_transport(self):
        def transport(url, timeout):
            if lt._SERVICE_PATH in url:  # body fetch
                return _resp(_PREC_BODY)
            return _resp(_PREC_LIST)     # list search
        return transport

    def test_full_retrieval_returns_ranked_body_cases_with_citations(self):
        r = le.retrieve_legal_evidence(
            "D-2 체류기간 연장 불허가 처분이 정당한가요?",
            source_types=[ST.PRECEDENT], config=_cfg(), transport=self._two_step_transport(),
            issue_concepts=["체류기간 연장허가"], statute_refs=["출입국관리법 제25조"], max_cases=2,
        )
        self.assertEqual(r.status, "available")
        self.assertTrue(r.cases)
        top = r.cases[0]
        self.assertEqual(top.result_kind, "body_result")  # body fetched for top case
        self.assertEqual(top.case_number, "2019두12345")
        self.assertTrue(r.citations)
        self.assertEqual(r.citations[0]["source_type"], ST.PRECEDENT)
        # Public projection never leaks the raw OC or the full body verbatim.
        blob = json.dumps(r.to_dict(), ensure_ascii=False)
        self.assertNotIn("oc-sentinel", blob)

    def test_retrieval_unavailable_degrades_gracefully(self):
        r = le.retrieve_legal_evidence(
            "체류기간 연장 불허가",
            config=_cfg(), transport=lambda u, t: _resp("", ok=False, status=500, error_type="http_error"),
        )
        self.assertIn(r.status, {"unavailable", "no_results"})
        self.assertEqual(r.cases, [])


# ---------------------------------------------------------------------------
# Integration: /api/ask distinguishes manuals/statutes vs case law, Fast-mode
# skip, and graceful degradation without LAW_API_OC.
# ---------------------------------------------------------------------------
import os  # noqa: E402
from unittest.mock import patch  # noqa: E402


def _pb():
    import paradiso_backend
    return paradiso_backend


def _client(pb):
    from fastapi.testclient import TestClient
    pb._reset_visas_cache_for_tests()
    pb._reset_grounding_cache_for_tests()
    return TestClient(pb.app)


def _fake_pack():
    # Deterministic stand-in for the (separately unit-tested) manual/statute
    # pipeline: a statute source + a case-law-warranted issue classification. No
    # network. Every consumer reads it via .get(), so a minimal dict is safe.
    return {
        "legal_issue_types": ["status_change", "denial_revocation_or_remedy"],
        "law_sources": [{"law_name": "출입국관리법", "source_type": "law"}],
        "law_api_attempted": True,
        "immigration_facts": {},
        "legal_analysis": {"analysis_mode": "source_assisted", "legal_issue_types": ["status_change"]},
    }


def _fake_case_law_result():
    case = le.LegalCase(
        source_type=ST.PRECEDENT, source_id="228541", case_name="체류자격변경불허가처분취소",
        case_number="2019두12345", court="대법원", decision_date="20210311",
        holding="체류자격 변경허가 여부는 행정청의 재량에 속한다.", summary="재량 일탈·남용이 없으면 적법.",
        reference_statutes="출입국관리법 제24조", result_kind="body_result",
    )
    case.chunks = le.build_chunks(case)
    r = le.LegalEvidenceResult(query="체류자격 변경 불허가", source_types=[ST.PRECEDENT, ST.ADMINISTRATIVE_APPEAL])
    r.cases = [case]
    r.citations = [case.citation()]
    r.status = "available"
    return r


class WaymakerIntegrationTests(unittest.TestCase):
    QUESTION = "체류자격 변경 불허가 처분을 행정심판으로 다툴 수 있나요? 판례가 궁금합니다."

    def setUp(self):
        le.reset_legal_evidence_cache_for_tests()
        self._saved = {k: os.environ.get(k) for k in ("LAW_GROUNDING_MODE", "LAW_API_OC", "LAW_API_KEY")}
        os.environ["LAW_GROUNDING_MODE"] = "audit"  # active without a credential -> no law-pack network
        for k in ("LAW_API_OC", "LAW_API_KEY"):
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _ask(self, pb, *, answer_mode="basic", retrieve_fake=None, capture=None):
        async def fake_or(prompt, model=None, max_tokens=None):
            if capture is not None:
                capture["prompt"] = prompt
            return "체류자격 변경 불허가 처분은 행정청의 재량에 속하며, 행정심판으로 다툴 수 있습니다."

        patches = [
            patch.object(pb, "OPENROUTER_API_KEY", "or-sentinel"),
            patch.object(pb, "GROQ_API_KEY", None),
            patch.object(pb, "ALLOW_GROQ_FALLBACK", False),
            patch.object(pb, "_call_openrouter", fake_or),
            patch.object(pb, "build_law_evidence_pack", lambda *a, **k: _fake_pack()),
        ]
        if retrieve_fake is not None:
            patches.append(patch.object(pb.legal_evidence, "retrieve_legal_evidence", retrieve_fake))
        for p in patches:
            p.__enter__()
        try:
            client = _client(pb)
            return client.post("/api/ask", json={"question": self.QUESTION, "answer_mode": answer_mode})
        finally:
            for p in reversed(patches):
                p.__exit__(None, None, None)

    def test_response_distinguishes_manual_statute_vs_case_law(self):
        pb = _pb()
        capture = {}
        resp = self._ask(pb, retrieve_fake=lambda *a, **k: _fake_case_law_result(), capture=capture)
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        # Statute pipeline (separate field).
        self.assertEqual(body["law_sources"][0]["law_name"], "출입국관리법")
        # Case-law pipeline (separate field, tagged precedent — never merged into
        # law_sources / precedent_evidence_items).
        self.assertTrue(body["legal_evidence_used"])
        self.assertEqual(body["legal_evidence_cases"][0]["source_type"], ST.PRECEDENT)
        self.assertEqual(body["legal_evidence_cases"][0]["case_number"], "2019두12345")
        self.assertEqual(body["legal_evidence"]["status"], "available")
        self.assertIn(ST.PRECEDENT, body["legal_evidence_source_types"])
        # The two evidence channels are distinct keys.
        self.assertIn("law_evidence_pack", body)
        self.assertIn("legal_evidence", body)
        # The prompt carried the supplementary case-law directive + caution + case.
        self.assertIn("Supplementary case-law", capture["prompt"])
        self.assertIn("개별 사건 판단", capture["prompt"])
        self.assertIn("체류자격변경불허가처분취소", capture["prompt"])
        # No OC leaks anywhere in the response.
        self.assertNotIn("oc-", resp.text.lower().replace("or-sentinel", ""))

    def test_fast_mode_also_retrieves_case_law(self):
        # Fast mode now performs real-time case-law lookup too (lighter budget),
        # so the retrieval IS called and the evidence is surfaced.
        pb = _pb()
        calls = {"n": 0, "max_cases": None}

        def fake(*a, **k):
            calls["n"] += 1
            calls["max_cases"] = k.get("max_cases")
            return _fake_case_law_result()

        resp = self._ask(pb, answer_mode="fast", retrieve_fake=fake)
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["legal_evidence_status"], "available")
        self.assertTrue(body["legal_evidence_used"])
        self.assertEqual(calls["n"], 1, "case law MUST be retrieved in Fast mode")
        # Fast mode uses the lighter budget.
        self.assertEqual(calls["max_cases"], 2)

    def test_missing_oc_degrades_without_breaking_request(self):
        pb = _pb()
        # No retrieve_legal_evidence patch: the REAL service runs with no OC.
        resp = self._ask(pb, answer_mode="basic")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["legal_evidence_status"], "not_configured")
        self.assertFalse(body["legal_evidence_used"])


if __name__ == "__main__":
    unittest.main()
