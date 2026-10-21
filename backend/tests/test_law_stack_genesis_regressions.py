"""Regression tests for the Waymaker Genesis law-stack fixes (F1-F12).

Each test pins one defect from the adversarially verified audit in
``docs/ai/waymaker-genesis/research-notes/law-stack.md`` (F1-F8) or from the
security note ``docs/ai/waymaker-genesis/15-security-and-deployment.md`` (F9-F12).
The tests were written and run against the unmodified code first; the recorded
failures are in ``docs/ai/waymaker-genesis/research-notes/law-stack-fixes.md``.

Everything runs offline. The only real-shape body is the sanitized fixture
``fixtures/law_api_shapes/genesis_law_detail_sample.json``: five 조문단위 units
(the "제1장 총칙" heading and four articles) copied verbatim from the documented
Open API sample for 건강가정기본법 (출처: 법제처 국가법령정보센터, law.go.kr). Its search-list counterpart is built in this
file from the fixture's own 기본정보 values, so no law data is invented here.
``fixtures/law_api_shapes/genesis_missing_oc_envelope.json`` is the HTTP-200
error envelope law.go.kr returned to a request without OC, as recorded in the
research notes. Every other body is a minimal synthetic shape, and every OC
value is a dummy. The F12 tests serve redirects from an in-process urllib
handler; sockets are patched to refuse any real connection.

    python3 -m pytest backend/tests/test_law_stack_genesis_regressions.py -q
"""
from __future__ import annotations

import email.message
import io
import json
import logging
import os
import sys
import time
import unittest
import urllib.request
import urllib.response
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Tuple
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import paradiso_backend as pb  # noqa: E402
from services import law_cloud_fallback  # noqa: E402
from services import law_grounding as lg  # noqa: E402
from services import law_tools as lt  # noqa: E402
from services import legal_evidence as le  # noqa: E402
from services.grounding_config import GroundingConfig  # noqa: E402
from services.law_citation_guard import guard_answer_citations  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "law_api_shapes"
DETAIL_FIXTURE = FIXTURE_DIR / "genesis_law_detail_sample.json"
DUMMY_OC = "genesis-dummy-oc"
LAW_NAME = "건강가정기본법"
EMPTY_LAW_SEARCH = json.dumps(
    {"LawSearch": {"totalCnt": "0", "resultCode": "00", "resultMsg": "success"}}
)


def _cfg(**over: Any) -> GroundingConfig:
    base: Dict[str, Any] = {
        "law_api_oc": DUMMY_OC,
        "mode": "enabled",
        "timeout_seconds": 1.0,
        "total_budget_seconds": 10.0,
    }
    base.update(over)
    return GroundingConfig(**base)


def _fixture() -> Dict[str, Any]:
    return json.loads(DETAIL_FIXTURE.read_text(encoding="utf-8"))


def _fixture_mst() -> str:
    query = dict(parse_qsl(urlsplit(_fixture()["_provenance"]["official_url"]).query))
    return query["MST"]


def _search_body_from_detail() -> str:
    """A lawSearch list body built only from the fixture's 기본정보 values."""
    basic = _fixture()["response"]["법령"]["기본정보"]
    row = {
        "법령일련번호": _fixture_mst(),
        "법령명한글": basic["법령명_한글"],
        "법령ID": basic["법령ID"],
        "공포일자": basic["공포일자"],
        "공포번호": basic["공포번호"],
        "시행일자": basic["시행일자"],
        "법령구분명": basic["법종구분"]["content"],
        "제개정구분명": basic["제개정구분"],
        "소관부처명": basic["소관부처"]["content"],
    }
    return json.dumps({"LawSearch": {"law": [row], "totalCnt": "1", "resultCode": "00"}}, ensure_ascii=False)


def _forget_logged_warnings() -> None:
    """law_tools logs each operator warning once per process; a test that
    asserts on the log must start from an empty registry."""
    lt._WARNINGS_LOGGED.clear()


def _ok(text: str) -> lt.LawHttpResponse:
    return lt.LawHttpResponse(ok=True, status_code=200, text=text)


def _real_shape_transport(calls: List[str]) -> Callable[[str, float], lt.LawHttpResponse]:
    """Serve the fixture for lawService and its list row for the law-name search."""
    detail_body = json.dumps(_fixture()["response"], ensure_ascii=False)
    search_body = _search_body_from_detail()

    def transport(url: str, timeout: float) -> lt.LawHttpResponse:
        calls.append(url)
        parts = urlsplit(url)
        params = dict(parse_qsl(parts.query))
        if parts.path.endswith("lawService.do") and params.get("target") == "law":
            return _ok(detail_body)
        if parts.path.endswith("lawSearch.do") and params.get("query") == LAW_NAME:
            return _ok(search_body)
        return _ok(EMPTY_LAW_SEARCH)

    return transport


def _real_shape_context(question: str, calls: List[str]) -> Dict[str, Any]:
    cfg = _cfg()
    with patch.object(lg, "load_grounding_config", return_value=cfg), \
         patch.object(lt, "_default_transport", _real_shape_transport(calls)):
        return lg.build_law_grounding_context(question)


def _real_shape_pack(question: str) -> Dict[str, Any]:
    calls: List[str] = []
    context = _real_shape_context(question, calls)
    pack = lt.build_law_evidence_pack(
        question, law_context=context, config=_cfg(), transport=_real_shape_transport(calls),
    )
    return {"context": context, "pack": pack, "calls": calls}


def _search_outcome(error_type: str = "", rows: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    return {
        "status": "ok" if rows else "error",
        "error_type": "" if rows else error_type,
        "results": list(rows or []),
        "result_count": len(rows or []),
        "parser_status": "parsed_json",
        "response_shape_hint": "json_object",
        "source_url": "https://www.law.go.kr/DRF/lawSearch.do?target=law",
    }


def _status_detail(context: Dict[str, Any]) -> str:
    verification = context.get("citation_verification") or {}
    return lg.derive_law_grounding_status_detail(
        configured_mode="enabled",
        effective_mode="enabled",
        intent_attempted=True,
        lookup_attempted=bool(context.get("attempted")),
        lookup_used=bool(context.get("law_grounding_used")),
        citation_specific=bool(verification.get("citation_specific")),
        citation_verified=verification.get("status") == "verified",
        error_type=context.get("error_type", ""),
        warnings=context.get("grounding_warnings", []),
    )


class _CleanEnvMixin:
    _ENV_KEYS = ("LAW_API_OC", "LAW_OC", "OPEN_LAW_ID", "LAW_API_KEY", "LAW_GROUNDING_MODE", "LAW_API_BASE_URL")

    def setUp(self) -> None:  # noqa: D401 - unittest hook
        self._saved_env = {key: os.environ.pop(key, None) for key in self._ENV_KEYS}
        law_cloud_fallback._PAGE_CACHE.clear()
        le.reset_legal_evidence_cache_for_tests()

    def tearDown(self) -> None:
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        law_cloud_fallback._PAGE_CACHE.clear()
        le.reset_legal_evidence_cache_for_tests()


# ---------------------------------------------------------------------------
# F1 (R1) + F2 (R2): a successful real-shape lookup reaches the evidence pack,
# and the verified flag alone no longer authorizes article numbers.
# ---------------------------------------------------------------------------
class F1EvidencePackTests(_CleanEnvMixin, unittest.TestCase):
    QUESTION = f"{LAW_NAME} 제4조의 근거 법령을 알려주세요"

    def test_f1_successful_real_shape_context_populates_pack(self) -> None:
        run = _real_shape_pack(self.QUESTION)
        context, pack = run["context"], run["pack"]
        self.assertTrue(context["law_grounding_used"])
        self.assertEqual(context["citation_verification"]["status"], "verified")

        names = {source.get("law_name") for source in pack["law_sources"]}
        self.assertIn(LAW_NAME, names)
        self.assertGreaterEqual(pack["law_evidence_count"], 1)
        self.assertEqual(pack["source_family_statuses"].get("statute"), "results_found")
        self.assertNotIn("attempted but unavailable", pack["evidence_summary"])
        article_rows = [s for s in pack["law_sources"] if s.get("article_verification_status") == "verified"]
        self.assertEqual([row.get("article") for row in article_rows], ["제4조"])
        self.assertNotIn(DUMMY_OC, json.dumps(pack, ensure_ascii=False))

        # The owner's fail-closed reconcile must keep the verified state now.
        truth = pb._reconcile_law_verification_with_evidence(
            law_grounding_verified=True,
            law_grounding_status_detail="law_grounding_verified",
            law_evidence_pack=pack,
            citation_verification=pack["citation_verification"],
            law_grounding_warnings=context["grounding_warnings"],
        )
        self.assertTrue(truth["law_grounding_verified"])
        self.assertEqual(truth["law_grounding_status_detail"], "law_grounding_verified")

    def test_f1_lone_statute_row_does_not_claim_decree_or_rule(self) -> None:
        # Side effect of F1: the source plan marks 시행령/시행규칙 results_found
        # for any law row, which listed them as available with no title.
        pack = _real_shape_pack(self.QUESTION)["pack"]
        self.assertEqual(pack["source_family_statuses"].get("enforcement_decree"), "no_results")
        self.assertEqual(pack["source_family_statuses"].get("enforcement_rule"), "no_results")
        available = [s.get("family") for s in pack["public_official_sources"] if s.get("publicStatus") == "available"]
        self.assertIn("statute", available)
        self.assertNotIn("enforcement_decree", available)
        self.assertNotIn("enforcement_rule", available)

    def test_f1_returned_decree_row_keeps_its_family(self) -> None:
        context = {
            "attempted": True,
            "law_grounding_used": True,
            "law_grounding": [
                {"source_type": "law", "law_name": "가상체류관리법", "title": "가상체류관리법",
                 "law_division": "법률", "retrieval_status": "ok", "provenance": "synthetic_fixture"},
                {"source_type": "law", "law_name": "가상체류관리법 시행령", "title": "가상체류관리법 시행령",
                 "law_division": "대통령령", "retrieval_status": "ok", "provenance": "synthetic_fixture"},
            ],
        }
        pack = lt.build_law_evidence_pack(
            "가상체류관리법 제4조의 근거 법령을 알려주세요", law_context=context, config=_cfg(), retrieve=False,
        )
        self.assertEqual(pack["source_family_statuses"].get("enforcement_decree"), "results_found")
        self.assertEqual(pack["source_family_statuses"].get("enforcement_rule"), "no_results")
        self.assertEqual(len(pack["law_sources"]), 2)

    def test_f1_raw_rows_in_context_are_still_normalized(self) -> None:
        context = {
            "attempted": True,
            "law_grounding_used": True,
            "law_grounding": [{"법령명한글": "가상체류관리법", "법령ID": "999999", "법령일련번호": "1"}],
        }
        pack = lt.build_law_evidence_pack(self.QUESTION, law_context=context, config=_cfg(), retrieve=False)
        self.assertEqual([s.get("law_name") for s in pack["law_sources"]], ["가상체류관리법"])

    def test_f2_backend_guard_does_not_blanket_allow_after_f1(self) -> None:
        pack = _real_shape_pack(self.QUESTION)["pack"]
        answer = f"{LAW_NAME} 제4조에 따라 가정생활을 영위할 권리가 있습니다. 같은 법 제9조도 확인하세요."
        guarded, meta = pb._apply_law_citation_guard(
            answer,
            law_grounding_verified=True,
            law_evidence_pack=pack,
            grounding_sources=[],
            structured_block="",
            lang="ko",
        )
        self.assertEqual(meta["law_citation_guard_action"], "notice_prepended")
        self.assertEqual(meta["unsupported_law_citations"], ["제9조"])
        self.assertNotEqual(guarded, answer)

    def test_f2_article_evidence_from_pack_authorizes_only_fetched_articles(self) -> None:
        from services.law_citation_guard import article_evidence_from_law_pack

        pack = _real_shape_pack(self.QUESTION)["pack"]
        evidence = article_evidence_from_law_pack(pack)
        self.assertEqual([(e["law_name"], e["article"]) for e in evidence], [(LAW_NAME, "제4조")])

        fetched = guard_answer_citations(
            f"{LAW_NAME} 제4조에 따라 권리가 있습니다.",
            law_grounding_verified=True, evidence_texts=[], article_evidence=evidence, lang="ko",
        )
        self.assertEqual(fetched["law_citation_guard_action"], "allowed_verified")
        other_law = guard_answer_citations(
            "가상노동법 제4조에 따라 권리가 있습니다.",
            law_grounding_verified=True, evidence_texts=[], article_evidence=evidence, lang="ko",
        )
        self.assertEqual(other_law["law_citation_guard_action"], "notice_prepended")


class F2CitationGuardTests(unittest.TestCase):
    # Synthetic: fictional law names only, no law ids, no statute text.
    ANSWER = "가상체류관리법 제24조 제1항에 따라 근무처 변경허가가 필요할 수 있습니다."
    ARTICLE_EVIDENCE = [{"law_name": "가상체류관리법", "article": "제24조", "article_verification_status": "verified"}]

    def test_f2_verified_flag_alone_no_longer_authorizes_article_numbers(self) -> None:
        out = guard_answer_citations(self.ANSWER, law_grounding_verified=True, evidence_texts=[], lang="ko")
        self.assertEqual(out["law_citation_guard_action"], "notice_prepended")
        self.assertTrue(out["unverified_law_citation_detected"])
        self.assertEqual(out["unsupported_law_citations"], ["제24조제1항"])

    def test_f2_article_level_evidence_for_the_same_law_is_required(self) -> None:
        cases = {
            self.ANSWER: "allowed_verified",
            "「가상체류관리법」 제24조에 따릅니다. 같은 법 제24조 제2항도 보세요.": "allowed_verified",
            "가상노동법 제24조에 따라 신고가 필요합니다.": "notice_prepended",
            "가상체류관리법 시행령 제24조에 따라 신고가 필요합니다.": "notice_prepended",
            "가상체류관리법 제24조 및 가상체류관리법 시행규칙 제18조의2에 따릅니다.": "notice_prepended",
            "가상체류관리법 제24조와 별표 1을 보세요.": "notice_prepended",
            # A bare article number names no law, so it cannot be bound to evidence.
            "제24조에 따라 신고가 필요합니다.": "notice_prepended",
            # A 시행령 named without its act, a multi-word "… 법률" title and a
            # back-reference to a decree all end the act's reach: fail closed.
            "가상체류관리법에 따른 신고는 시행령 제24조에 따릅니다.": "notice_prepended",
            "가상체류관리법과 가상 외국인의 체류 등에 관한 법률 제24조를 보세요.": "notice_prepended",
            "가상체류관리법 제24조와 같은 법 시행령 제24조를 보세요.": "notice_prepended",
            # A law named in an earlier sentence does not govern this one.
            "가상체류관리법을 확인하세요. 제24조에 따라 신고가 필요합니다.": "notice_prepended",
        }
        for answer, expected in cases.items():
            with self.subTest(answer=answer):
                out = guard_answer_citations(
                    answer, law_grounding_verified=True, evidence_texts=[],
                    article_evidence=self.ARTICLE_EVIDENCE, lang="ko",
                )
                self.assertEqual(out["law_citation_guard_action"], expected)

    def test_f2_mixed_article_and_local_evidence_is_local(self) -> None:
        out = guard_answer_citations(
            "가상체류관리법 제24조와 별표 1을 보세요.", law_grounding_verified=True,
            evidence_texts=["가상체류관리법 시행규칙 별표 1"],
            article_evidence=self.ARTICLE_EVIDENCE, lang="ko",
        )
        self.assertEqual(out["law_citation_guard_action"], "allowed_local_evidence")
        self.assertEqual(out["unsupported_law_citations"], [])

    def test_f2_article_evidence_needs_the_verified_flag(self) -> None:
        out = guard_answer_citations(
            self.ANSWER, law_grounding_verified=False, evidence_texts=[],
            article_evidence=self.ARTICLE_EVIDENCE, lang="ko",
        )
        self.assertEqual(out["law_citation_guard_action"], "notice_prepended")

    def test_f2_return_shape_is_unchanged(self) -> None:
        out = guard_answer_citations(self.ANSWER, law_grounding_verified=True, evidence_texts=[self.ANSWER])
        self.assertEqual(
            set(out),
            {"answer", "law_citations_detected", "unsupported_law_citations",
             "unverified_law_citation_detected", "law_citation_guard_action"},
        )
        self.assertEqual(out["law_citation_guard_action"], "allowed_local_evidence")


# ---------------------------------------------------------------------------
# F3 (R4 D1/D2): a failed cited-law search is "unavailable", not "not found".
# ---------------------------------------------------------------------------
class F3CitedLawFailureTests(_CleanEnvMixin, unittest.TestCase):
    # "체류기간 연장" adds planner anchor queries next to the cited law's own search.
    CITED_LAW = "가상노동법"
    QUESTION = "가상노동법 제18조에 따른 체류기간 연장의 법적 근거를 알려주세요"

    def _context(self, outcome_for: Callable[[str], Dict[str, Any]]) -> Dict[str, Any]:
        with patch.object(lg, "load_grounding_config", return_value=_cfg()), \
             patch.object(lt, "search_laws", side_effect=lambda query, **_: outcome_for(query)) as search, \
             patch.object(lt, "get_law_detail", return_value=_search_outcome("law_api_timeout")) as detail:
            context = lg.build_law_grounding_context(self.QUESTION)
        self.assertGreater(search.call_count, 1, "the plan must hold more than the cited-law search")
        context["_detail_calls"] = detail.call_count
        return context

    def test_f3_cited_law_timeout_is_error_not_cited_law_not_found(self) -> None:
        context = self._context(
            lambda q: _search_outcome("law_api_timeout" if q == self.CITED_LAW else "law_api_no_results")
        )
        verification = context["citation_verification"]
        citation = verification["citations"][0]
        self.assertEqual(citation["verification_status"], "error")
        self.assertNotIn("CITED_LAW_NOT_FOUND", citation["warnings"])
        self.assertIn("SOURCE_UNAVAILABLE", citation["warnings"])
        self.assertIn("LAW_API_TIMEOUT", citation["warnings"])
        self.assertEqual(verification["status"], "error")
        self.assertEqual(_status_detail(context), "law_grounding_attempted_failed")

    def test_f3_cited_law_timeout_while_another_law_was_found(self) -> None:
        other = {"source_type": "law", "law_name": "가상체류관리법", "title": "가상체류관리법",
                 "law_id": "", "law_serial_no": "", "retrieval_status": "ok"}
        context = self._context(
            lambda q: _search_outcome("law_api_timeout") if q == self.CITED_LAW else _search_outcome(rows=[other])
        )
        citation = context["citation_verification"]["citations"][0]
        self.assertEqual(citation["verification_status"], "error")
        self.assertNotIn("CITED_LAW_NOT_FOUND", citation["warnings"])
        self.assertIn("LAW_API_PARTIAL_FAILURE", context["grounding_warnings"])
        self.assertEqual(context["_detail_calls"], 0)

    def test_f3_authoritative_no_results_still_reports_not_found(self) -> None:
        context = self._context(lambda q: _search_outcome("law_api_no_results"))
        citation = context["citation_verification"]["citations"][0]
        self.assertEqual(citation["verification_status"], "failed_verification")
        self.assertIn("CITED_LAW_NOT_FOUND", citation["warnings"])
        self.assertEqual(_status_detail(context), "law_grounding_attempted_no_results")

    def test_f3_real_errors_outrank_no_results_in_status_detail(self) -> None:
        def detail(error_type: str, warnings: List[str]) -> str:
            return lg.derive_law_grounding_status_detail(
                configured_mode="enabled", effective_mode="enabled", intent_attempted=True,
                lookup_attempted=True, lookup_used=False, error_type=error_type, warnings=warnings,
            )

        self.assertEqual(
            detail("law_api_timeout", ["SOURCE_UNAVAILABLE", "LAW_API_TIMEOUT", "LAW_API_NO_RESULTS"]),
            "law_grounding_attempted_failed",
        )
        self.assertEqual(
            detail("law_grounding_budget_exhausted", ["LAW_GROUNDING_BUDGET_EXHAUSTED", "LAW_API_NO_RESULTS"]),
            "law_grounding_attempted_failed",
        )
        self.assertEqual(
            detail("law_api_no_results", ["SOURCE_UNAVAILABLE", "LAW_API_NO_RESULTS"]),
            "law_grounding_attempted_no_results",
        )


# ---------------------------------------------------------------------------
# F4 (R4 D3): budget exhaustion and unknown errors are an unavailable family.
# ---------------------------------------------------------------------------
class F4FamilyStatusTests(_CleanEnvMixin, unittest.TestCase):
    QUESTION = "E-7 근무처를 변경할 때 신고와 허가의 법적 근거를 알려주세요"

    def _statute_status(self, error_type: str) -> str:
        context = {
            "attempted": True,
            "law_grounding_used": False,
            "law_grounding": [],
            "error_type": error_type,
            "grounding_warnings": ["SOURCE_UNAVAILABLE"],
        }
        pack = lt.build_law_evidence_pack(self.QUESTION, law_context=context, config=_cfg(), retrieve=False)
        return pack["source_family_statuses"]["statute"]

    def test_f4_budget_exhausted_maps_to_timeout(self) -> None:
        self.assertEqual(self._statute_status("law_grounding_budget_exhausted"), "timeout")

    def test_f4_unknown_error_maps_to_unavailable(self) -> None:
        self.assertEqual(self._statute_status("law_api_unrecognized_failure"), "unavailable")

    def test_f4_known_errors_and_no_results_keep_their_status(self) -> None:
        self.assertEqual(self._statute_status("law_api_timeout"), "timeout")
        self.assertEqual(self._statute_status("law_api_no_results"), "no_results")
        self.assertEqual(self._statute_status(""), "no_results")


# ---------------------------------------------------------------------------
# F5 (R4 D5): the ranked ladder keeps the first infrastructure error.
# ---------------------------------------------------------------------------
class F5RankedSearchTests(_CleanEnvMixin, unittest.TestCase):
    def _ranked(self, outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        with patch.object(lt, "search_laws", side_effect=outcomes):
            return lt.search_laws_ranked("출입국법", config=_cfg())

    def test_f5_primary_timeout_then_empty_expansion_is_timeout(self) -> None:
        outcome = self._ranked([_search_outcome("law_api_timeout"), _search_outcome("law_api_no_results")])
        self.assertEqual(outcome["status"], "timeout")
        self.assertEqual(outcome["error_type"], "law_api_timeout")
        self.assertEqual([a["error_type"] for a in outcome["attempts"]], ["law_api_timeout", "law_api_no_results"])

    def test_f5_every_attempt_no_results_is_not_found(self) -> None:
        outcome = self._ranked([_search_outcome("law_api_no_results"), _search_outcome("law_api_no_results")])
        self.assertEqual(outcome["status"], "not_found")


# ---------------------------------------------------------------------------
# F6 (D8): legal_evidence caches parsed successes only.
# ---------------------------------------------------------------------------
class F6LegalEvidenceCacheTests(_CleanEnvMixin, unittest.TestCase):
    SUCCESS = json.dumps({"PrecSearch": {"prec": [{
        "판례정보일련번호": "990001", "사건명": "가상체류관리법 위반 가상사건",
        "사건번호": "2099두99999", "법원명": "가상법원", "선고일자": "20990101",
    }]}}, ensure_ascii=False)

    def _transport_calls(self, body: str) -> int:
        calls = {"n": 0}

        def transport(url: str, timeout: float) -> lt.LawHttpResponse:
            calls["n"] += 1
            return _ok(body)

        client = le.LawOpenDataClient(
            config=GroundingConfig(law_api_oc=DUMMY_OC, mode="enabled", cache_ttl_seconds=600),
            transport=transport, sleep=lambda _s: None,
        )
        client.search_cases("가상 체류 질의")
        client.search_cases("가상 체류 질의")
        return calls["n"]

    def test_f6_official_error_body_is_not_cached(self) -> None:
        body = (FIXTURE_DIR / "statute_json_official_error.txt").read_text(encoding="utf-8")
        self.assertEqual(self._transport_calls(body), 2)

    def test_f6_empty_and_zero_record_bodies_are_not_cached(self) -> None:
        self.assertEqual(self._transport_calls(""), 2)
        self.assertEqual(self._transport_calls(json.dumps({"PrecSearch": {"totalCnt": "0"}})), 2)

    def test_f6_parsed_success_is_still_cached(self) -> None:
        self.assertEqual(self._transport_calls(self.SUCCESS), 1)


# ---------------------------------------------------------------------------
# F7 (R5): heading units are not articles; 항/호 text reaches the snippet.
# ---------------------------------------------------------------------------
class F7ArticleExtractionTests(_CleanEnvMixin, unittest.TestCase):
    def _articles(self, article: str) -> List[Dict[str, Any]]:
        calls: List[str] = []
        detail = lt.get_law_detail(
            law_id=_fixture_mst(), law_name=LAW_NAME, article=article,
            config=_cfg(), transport=_real_shape_transport(calls),
        )
        self.assertEqual(detail["status"], "ok")
        return detail["detail"]["articles"]

    def test_f7_heading_unit_with_same_number_is_skipped(self) -> None:
        articles = self._articles("제1조")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["article_title"], "목적")
        self.assertTrue(articles[0]["text"].startswith("제1조(목적)"))
        labels = [a["article_label"] for a in self._articles("")]
        self.assertEqual(labels, ["제1조", "제3조", "제4조", "제21조의2"])

    def test_f7_paragraph_and_item_text_is_in_the_snippet(self) -> None:
        article_4 = self._articles("제4조")[0]["text"]
        self.assertIn("①모든 국민은", article_4)
        self.assertIn("②모든 국민은", article_4)
        article_3 = self._articles("제3조")[0]["text"]  # 항 is a dict that holds only 호
        self.assertIn('1. "가족"이라 함은', article_3)
        self.assertIn('2의2. "1인가구"', article_3)
        branch = self._articles("제21조의2")
        self.assertEqual(branch[0]["article_label"], "제21조의2")
        self.assertIn("② 위기가족긴급지원의 종류", branch[0]["text"])
        self.assertIn("1. 아이돌봄지원", branch[0]["text"])

    def test_f7_cited_article_snippet_is_the_article_not_the_heading(self) -> None:
        context = _real_shape_context(f"{LAW_NAME} 제1조의 근거 법령을 알려주세요", [])
        citation = context["citation_verification"]["citations"][0]
        self.assertEqual(citation["verification_status"], "verified")
        self.assertTrue(citation["snippet"].startswith("제1조(목적)"), citation["snippet"])

    def test_f7_fixture_carries_attribution_and_no_credential(self) -> None:
        text = DETAIL_FIXTURE.read_text(encoding="utf-8")
        provenance = _fixture()["_provenance"]
        self.assertEqual(provenance["attribution"], "출처: 법제처 국가법령정보센터 (law.go.kr)")
        self.assertEqual(len(provenance["capture_sha256"]), 64)
        self.assertNotIn("OC", text)


# ---------------------------------------------------------------------------
# F8 (R7): the OC is only ever sent to an https law.go.kr host.
# ---------------------------------------------------------------------------
class F8HostTrustTests(_CleanEnvMixin, unittest.TestCase):
    UNTRUSTED = (
        "https://korean-law-mcp.fly.dev",
        "http://www.law.go.kr",
        "https://www.law.go.kr.attacker.example",
        "https://user:pw@www.law.go.kr",
        "https://www.law.go.kr:8443",
        "ftp://www.law.go.kr",
    )

    def test_f8_untrusted_base_url_falls_back_to_default_host(self) -> None:
        for base in self.UNTRUSTED:
            with self.subTest(base=base):
                cfg = _cfg(law_api_base_url=base)
                url = lt._build_request_url(cfg, lt._SEARCH_PATH, {"target": "law"})
                self.assertTrue(url.startswith("https://www.law.go.kr/DRF/lawSearch.do?"), url)
                self.assertEqual(lt.law_api_base_url_warning(cfg), "LAW_API_BASE_URL_IGNORED")

    def test_f8_https_law_go_kr_override_is_kept(self) -> None:
        for base, expected in (("https://www.law.go.kr", "https://www.law.go.kr"),
                               ("https://law.go.kr/", "https://law.go.kr")):
            with self.subTest(base=base):
                cfg = _cfg(law_api_base_url=base)
                url = lt._build_request_url(cfg, lt._SEARCH_PATH, {"target": "law"})
                self.assertTrue(url.startswith(expected + "/DRF/lawSearch.do?"), url)
                self.assertEqual(lt.law_api_base_url_warning(cfg), "")

    def test_f8_oc_never_reaches_an_untrusted_host(self) -> None:
        sent: List[str] = []

        def transport(url: str, timeout: float) -> lt.LawHttpResponse:
            sent.append(url)
            return _ok(EMPTY_LAW_SEARCH)

        lt.search_laws("가상체류관리법", config=_cfg(law_api_base_url="https://korean-law-mcp.fly.dev"),
                       transport=transport)
        self.assertTrue(sent)
        self.assertTrue(all(urlsplit(url).hostname == "www.law.go.kr" for url in sent), sent)

    def test_f8_scheme_fallback_is_unchanged_and_stays_on_law_go_kr(self) -> None:
        # Decision recorded in research-notes/law-stack-fixes.md (F8): the
        # https->http retry on a connection failure is kept as it is, and with
        # the host allowlist it can only ever target the law.go.kr host.
        sent: List[str] = []

        def unreachable(url: str, timeout: float) -> lt.LawHttpResponse:
            sent.append(url)
            return lt.LawHttpResponse(ok=False, error_type="network")

        url = lt._build_request_url(
            _cfg(law_api_base_url="https://korean-law-mcp.fly.dev"), lt._SEARCH_PATH, {"target": "law"},
        )
        _forget_logged_warnings()
        with self.assertLogs("paradiso.law_tools", level="WARNING") as logs:
            lt._transport_with_scheme_fallback(url, 1.0, unreachable)
        self.assertEqual([urlsplit(u).scheme for u in sent], ["https", "http"])
        self.assertTrue(all(urlsplit(u).hostname == "www.law.go.kr" for u in sent), sent)
        self.assertTrue(any("LAW_API_PLAINTEXT_RETRY_FAILED" in line for line in logs.output), logs.output)

    def test_f8_plaintext_retry_that_reaches_the_host_is_logged_without_the_url(self) -> None:
        def https_blocked(url: str, timeout: float) -> lt.LawHttpResponse:
            if url.startswith("https://"):
                return lt.LawHttpResponse(ok=False, error_type="network")
            return _ok(EMPTY_LAW_SEARCH)

        url = lt._build_request_url(_cfg(), lt._SEARCH_PATH, {"target": "law"})
        _forget_logged_warnings()
        with self.assertLogs("paradiso.law_tools", level="WARNING") as logs:
            resp = lt._transport_with_scheme_fallback(url, 1.0, https_blocked)
            lt._transport_with_scheme_fallback(url, 1.0, https_blocked)
        self.assertTrue(resp.ok)
        joined = "\n".join(logs.output)
        self.assertIn("LAW_API_PLAINTEXT_RETRY_REACHED", joined)
        self.assertEqual(len(logs.output), 1, "logged once per process, not per request")
        self.assertNotIn(DUMMY_OC, joined)
        self.assertNotIn("lawSearch.do", joined)

    def test_f8_warning_is_logged_and_preflighted_without_the_value(self) -> None:
        base = "https://genesis-unique-proxy.example"
        _forget_logged_warnings()
        with self.assertLogs("paradiso.law_tools", level="WARNING") as logs:
            lt._build_request_url(_cfg(law_api_base_url=base), lt._SEARCH_PATH, {"target": "law"})
        joined = "\n".join(logs.output)
        self.assertIn("LAW_API_BASE_URL_IGNORED", joined)
        self.assertNotIn("genesis-unique-proxy", joined)

        with patch.dict(os.environ, {"LAW_API_BASE_URL": base, "LAW_API_OC": DUMMY_OC}):
            preflight = lg.law_grounding_preflight()
        self.assertIn("LAW_API_BASE_URL_IGNORED", preflight["warnings"])
        self.assertNotIn("genesis-unique-proxy", repr(preflight))
        self.assertNotIn(DUMMY_OC, repr(preflight))


# ---------------------------------------------------------------------------
# F9 (SEC-05b, audit D6): failure is not absence in the DRF parser.
# ---------------------------------------------------------------------------
MISSING_OC_FIXTURE = FIXTURE_DIR / "genesis_missing_oc_envelope.json"


def _missing_oc_body() -> str:
    """The HTTP-200 envelope law.go.kr returned to a request without OC."""
    return json.dumps(
        json.loads(MISSING_OC_FIXTURE.read_text(encoding="utf-8"))["body"], ensure_ascii=False,
    )


# Well-formed bodies with no result list and no totalCnt, or with rows or a
# count that contradict "zero rows parsed". All synthetic.
_NO_RESULT_LIST_BODIES = {
    "empty family wrapper": '{"LawSearch": {}}',
    "wrapper without list or count": '{"LawSearch": {"target": "law", "page": "1"}}',
    "unknown envelope": '{"unexpected": {"shape": true}}',
    "empty json list": "[]",
    "xml without list or count": "<?xml version='1.0' encoding='UTF-8'?><LawSearch><target>law</target></LawSearch>",
    "count says rows exist": '{"LawSearch": {"target": "law", "totalCnt": "3"}}',
    "rows no normalizer reads": '{"LawSearch": {"totalCnt": "0", "law": [{"unknown": "x"}]}}',
}

# Positive evidence of an empty answer. All synthetic except that totalCnt is
# the documented count field of the DRF list responses.
_EXPLICIT_EMPTY_BODIES = {
    "totalCnt 0 and empty list": '{"LawSearch": {"target": "law", "totalCnt": "0", "law": []}}',
    "totalCnt 0 with success envelope": EMPTY_LAW_SEARCH,
    "xml totalCnt 0": "<?xml version='1.0' encoding='UTF-8'?><LawSearch><target>law</target><totalCnt>0</totalCnt></LawSearch>",
    "empty law list without count": '{"LawSearch": {"law": []}}',
}


class F9FailureIsNotAbsenceTests(_CleanEnvMixin, unittest.TestCase):
    CITED_LAW = "가상노동법"
    QUESTION = "가상노동법 제18조에 따른 체류기간 연장의 법적 근거를 알려주세요"

    def _search(self, body: str) -> Dict[str, Any]:
        return lt.search_laws(self.CITED_LAW, config=_cfg(), transport=lambda url, timeout: _ok(body))

    def test_f9_empty_body_is_a_bad_response(self) -> None:
        for body in ("", "  \n  "):
            with self.subTest(body=repr(body)):
                parsed = lt.parse_law_search_response(body)
                self.assertEqual(parsed["error_type"], lt.LAW_API_BAD_RESPONSE)
                self.assertEqual(parsed["parser_status"], "empty")
                result = self._search(body)
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["error_type"], lt.LAW_API_BAD_RESPONSE)

    def test_f9_missing_oc_envelope_is_an_official_error(self) -> None:
        body = _missing_oc_body()
        parsed = lt.parse_law_search_response(body)
        self.assertEqual(parsed["error_type"], lt.LAW_API_OFFICIAL_ERROR)
        self.assertEqual(parsed["parser_status"], "official_error")
        result = self._search(body)
        self.assertEqual(result["error_type"], lt.LAW_API_OFFICIAL_ERROR)
        dumped = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("필수 입력값", dumped, "the upstream message is not echoed")
        self.assertNotIn(DUMMY_OC, dumped)
        fixture_text = MISSING_OC_FIXTURE.read_text(encoding="utf-8")
        self.assertIn("출처: 법제처 국가법령정보센터 (law.go.kr)", fixture_text)
        self.assertNotIn("OC=", fixture_text)

    def test_f9_other_official_error_envelopes(self) -> None:
        envelopes = {
            # resultCode 01 / resultMsg fail is the documented failure pair
            # (research-notes/official-api.md §1, "Status envelope").
            "documented resultCode 01": '{"LawSearch": {"resultCode": "01", "resultMsg": "fail"}}',
            # Synthetic, not observed upstream.
            "resultMsg fail without a code": '{"LawSearch": {"resultMsg": "fail", "totalCnt": "0"}}',
            "result and msg under the family wrapper": json.dumps(
                {"LawSearch": json.loads(_missing_oc_body())}, ensure_ascii=False,
            ),
            "result and msg as xml": (
                "<?xml version='1.0' encoding='UTF-8'?><LawSearch>"
                "<result>필수입력요소 검증에 실패하였습니다.</result>"
                "<msg>필수 입력값이 존재하지 않습니다.</msg></LawSearch>"
            ),
        }
        for name, body in envelopes.items():
            with self.subTest(envelope=name):
                self.assertEqual(lt.parse_law_search_response(body)["error_type"], lt.LAW_API_OFFICIAL_ERROR)

    def test_f9_well_formed_body_without_result_list_is_a_parse_error(self) -> None:
        for name, body in _NO_RESULT_LIST_BODIES.items():
            with self.subTest(body=name):
                parsed = lt.parse_law_search_response(body)
                self.assertEqual(parsed["error_type"], lt.LAW_API_PARSE_ERROR)
                self.assertEqual(parsed["parser_status"], "unexpected_shape")
                family = lt.retrieve_official_source_family(
                    "statute", self.CITED_LAW, config=_cfg(), transport=lambda url, timeout, b=body: _ok(b),
                )
                self.assertEqual(family["status"], lt.SOURCE_STATUS_PARSE_ERROR)

    def test_f9_explicit_empty_result_is_still_no_results(self) -> None:
        for name, body in _EXPLICIT_EMPTY_BODIES.items():
            with self.subTest(body=name):
                self.assertEqual(lt.parse_law_search_response(body)["error_type"], lt.LAW_API_NO_RESULTS)
                self.assertEqual(self._search(body)["error_type"], lt.LAW_API_NO_RESULTS)

    def test_f9_cited_law_failure_body_is_unavailable_not_not_found(self) -> None:
        # The F3 path: an unreadable answer for the cited law's own search is
        # "could not check", never CITED_LAW_NOT_FOUND.
        bodies = {
            "empty body": ("", "LAW_API_BAD_RESPONSE"),
            "html page": ("<!DOCTYPE html><html><body>사용자인증에 실패하였습니다</body></html>", "LAW_API_BAD_RESPONSE"),
            "missing-OC envelope": (_missing_oc_body(), "LAW_API_OFFICIAL_ERROR"),
            "no result list": ('{"LawSearch": {"target": "law"}}', "LAW_API_PARSE_ERROR"),
        }
        for name, (body, marker) in bodies.items():
            with self.subTest(body=name):
                law_cloud_fallback._PAGE_CACHE.clear()
                with patch.object(lg, "load_grounding_config", return_value=_cfg()), \
                     patch.object(lt, "_default_transport", lambda url, timeout, b=body: _ok(b)):
                    context = lg.build_law_grounding_context(self.QUESTION)
                citation = context["citation_verification"]["citations"][0]
                self.assertEqual(citation["law_name"], self.CITED_LAW)
                self.assertEqual(citation["verification_status"], "error")
                self.assertIn("SOURCE_UNAVAILABLE", citation["warnings"])
                self.assertIn(marker, citation["warnings"])
                self.assertNotIn("CITED_LAW_NOT_FOUND", citation["warnings"])
                self.assertEqual(_status_detail(context), "law_grounding_attempted_failed")

    def test_f9_legal_evidence_failure_bodies_are_unavailable(self) -> None:
        cases = {
            "empty body": ("", "unavailable", lt.LAW_API_BAD_RESPONSE),
            "no result list": ('{"PrecSearch": {"target": "prec"}}', "unavailable", lt.LAW_API_PARSE_ERROR),
            "missing-OC envelope": (_missing_oc_body(), "unavailable", lt.LAW_API_OFFICIAL_ERROR),
            # Control: an explicit empty answer stays no_results.
            "totalCnt 0": ('{"PrecSearch": {"target": "prec", "totalCnt": "0"}}', "no_results", ""),
        }
        for name, (body, status, error_type) in cases.items():
            with self.subTest(body=name):
                # Every case sends the same query; start each from an empty
                # response cache so no case can replay another's body.
                le.reset_legal_evidence_cache_for_tests()
                client = le.LawOpenDataClient(
                    config=GroundingConfig(law_api_oc=DUMMY_OC, mode="enabled"),
                    transport=lambda url, timeout, b=body: _ok(b), sleep=lambda _s: None,
                )
                envelope = client.search_cases("가상 체류 질의")
                self.assertEqual(envelope["status"], status)
                self.assertEqual(envelope["error_type"], error_type)

    def test_f9_unqueried_precedent_family_carries_no_unavailable_item(self) -> None:
        # Control for the law_tools call site that used to build this envelope
        # by parsing an empty body.
        result = lt.retrieve_official_source_family(
            "legal_interpretation", "가상 체류 질의", config=_cfg(),
            transport=lambda url, timeout: _ok(EMPTY_LAW_SEARCH),
        )
        self.assertEqual(result["status"], lt.SOURCE_STATUS_UNSUPPORTED)
        self.assertEqual(result["precedent_evidence_items"], [])
        self.assertEqual(result["normalized_items"], [])


# ---------------------------------------------------------------------------
# F10: "verified" means a cited article was fetched and matched, nothing less.
# ---------------------------------------------------------------------------
def _title_hit_transport(calls: List[str]) -> Callable[[str, float], lt.LawHttpResponse]:
    """Every law-title search returns the fixture's list row (a title-level hit);
    lawService serves the fixture; anything else gets an explicit empty answer."""
    detail_body = json.dumps(_fixture()["response"], ensure_ascii=False)
    search_body = _search_body_from_detail()

    def transport(url: str, timeout: float) -> lt.LawHttpResponse:
        calls.append(url)
        parts = urlsplit(url)
        params = dict(parse_qsl(parts.query))
        if parts.path.endswith("lawService.do") and params.get("target") == "law":
            return _ok(detail_body)
        if parts.path.endswith("lawSearch.do") and params.get("target") == "law" and params.get("query"):
            return _ok(search_body)
        return _ok(EMPTY_LAW_SEARCH)

    return transport


class F10HonestVerifiedFlagTests(_CleanEnvMixin, unittest.TestCase):
    TITLE_QUESTION = f"{LAW_NAME}의 법적 근거를 알려주세요"
    CITED_QUESTION = f"{LAW_NAME} 제4조의 근거 법령을 알려주세요"
    NOTICE = "특정 조문 번호는 확정하지 않습니다"

    def _context(self, question: str) -> Tuple[Dict[str, Any], List[str]]:
        calls: List[str] = []
        with patch.object(lg, "load_grounding_config", return_value=_cfg()), \
             patch.object(lt, "_default_transport", _title_hit_transport(calls)):
            context = lg.build_law_grounding_context(question)
        return context, calls

    def _ask(self, question: str, answer: str) -> Dict[str, Any]:
        from fastapi.testclient import TestClient

        async def fake_complete(prompt, requested_model=None, candidate_models=None, max_tokens=None):
            candidates = list(candidate_models or []) or ["genesis/fake-model"]
            return {
                "ok": True, "answer": answer, "primary_model": candidates[0],
                "requested_model": requested_model, "model_candidates": candidates,
                "attempted_models": candidates[:1], "skipped_models_due_to_cooldown": [],
                "cooling_down_models": [], "model_cooldown_seconds": 0, "cooldown_enabled": False,
                "final_model": candidates[0], "model_fallback_used": False, "provider_error_type": None,
                "upstream_statuses": [], "retryable_provider_error": False, "all_candidates_failed": False,
            }

        def passthrough_gate(answer_text, meta, contract, **_kw):
            return answer_text, {}

        def refuse(*_args, **_kwargs):
            raise OSError("a real connection was attempted")

        # No diagnostics header: this is the public projection ai.html reads.
        client = TestClient(pb.app)
        with patch.dict(os.environ, {"LAW_GROUNDING_MODE": "enabled", "LAW_API_OC": DUMMY_OC}), \
             patch.object(lt, "_default_transport", _title_hit_transport([])), \
             patch.object(pb, "OPENROUTER_API_KEY", "test-key"), \
             patch.object(pb, "_openrouter_complete_with_candidates", new=fake_complete), \
             patch.object(pb, "_apply_answer_shape_gate", new=passthrough_gate), \
             patch("socket.create_connection", side_effect=refuse):
            resp = client.post("/api/ask", json={"question": question, "answer_mode": "basic", "stream": False})
        self.assertEqual(resp.status_code, 200, resp.text[:500])
        body = resp.json()
        self.assertNotIn(DUMMY_OC, json.dumps(body, ensure_ascii=False))
        return body

    def test_f10_rows_without_a_fetched_article_are_not_verified(self) -> None:
        def detail(**kwargs: Any) -> str:
            return lg.derive_law_grounding_status_detail(
                configured_mode="enabled", effective_mode="enabled", intent_attempted=True,
                lookup_attempted=True, lookup_used=True, **kwargs,
            )

        for kwargs in ({}, {"citation_specific": False, "citation_verified": True},
                       {"citation_specific": True, "citation_verified": False}):
            with self.subTest(**kwargs):
                self.assertEqual(detail(**kwargs), "law_grounding_source_linked_unverified")
                self.assertFalse(lg.law_grounding_status_detail_is_verified(detail(**kwargs)))
        self.assertEqual(detail(citation_specific=True, citation_verified=True), "law_grounding_verified")

    def test_f10_title_level_hit_reaches_the_pack_but_is_not_verified(self) -> None:
        context, calls = self._context(self.TITLE_QUESTION)
        self.assertTrue(context["law_grounding_used"])
        self.assertFalse(any("lawService.do" in url for url in calls), "no article text was fetched")
        self.assertEqual(_status_detail(context), "law_grounding_source_linked_unverified")
        pack = lt.build_law_evidence_pack(
            self.TITLE_QUESTION, law_context=context, config=_cfg(), transport=_title_hit_transport([]),
        )
        self.assertIn(LAW_NAME, {source.get("law_name") for source in pack["law_sources"]})
        self.assertFalse([s for s in pack["law_sources"] if s.get("article_verification_status") == "verified"])

    def test_f10_fetched_and_matched_article_is_still_verified(self) -> None:
        context, calls = self._context(self.CITED_QUESTION)
        self.assertTrue(any("lawService.do" in url for url in calls))
        self.assertEqual(context["citation_verification"]["status"], "verified")
        self.assertEqual(_status_detail(context), "law_grounding_verified")

    def test_f10_citation_past_the_lookup_cap_is_not_verified(self) -> None:
        # Only the first three cited provisions are fetched. A fourth, distinct
        # one was never checked, so "verified" (which drops the notice) would
        # overstate it. The four articles are the fixture's own article units.
        question = (
            f"{LAW_NAME} 제1조, {LAW_NAME} 제3조, {LAW_NAME} 제4조와 "
            f"{LAW_NAME} 제21조의2의 법적 근거를 알려주세요"
        )
        context, calls = self._context(question)
        verification = context["citation_verification"]
        by_article = {item["article"]: item["verification_status"] for item in verification["citations"]}
        self.assertEqual(
            by_article,
            {"제1조": "verified", "제3조": "verified", "제4조": "verified", "제21조의2": "extracted_only"},
        )
        self.assertEqual(sum("lawService.do" in url for url in calls), 3, "the cap itself is unchanged")
        self.assertNotEqual(verification["status"], "verified")
        self.assertEqual(_status_detail(context), "law_grounding_source_linked_unverified")
        self.assertEqual(len(verification["article_evidence"]), 3, "fetched articles still reach the pack")

    def test_f10_repeated_citation_does_not_count_against_the_cap(self) -> None:
        # Control: a provision mentioned again is not a new, unchecked citation.
        question = (
            f"{LAW_NAME} 제4조, {LAW_NAME} 제1조, {LAW_NAME} 제3조를 보면 "
            f"{LAW_NAME} 제4조의 법적 근거가 무엇인가요"
        )
        context, _calls = self._context(question)
        self.assertEqual(context["citation_verification"]["status"], "verified")
        self.assertEqual(_status_detail(context), "law_grounding_verified")

    def test_f10_ask_public_fields_keep_the_notice_for_a_title_hit(self) -> None:
        body = self._ask(self.TITLE_QUESTION, f"{LAW_NAME}은 가정생활의 보호를 위한 법률입니다.")
        self.assertEqual(body["law_grounding_status_detail"], "law_grounding_source_linked_unverified")
        self.assertFalse(body["law_grounding_verified"])
        self.assertIn(self.NOTICE, body["law_grounding_user_notice"])
        display = body["law_grounding_display"]
        self.assertFalse(display["verified"])
        self.assertEqual(display["sources"], [])
        self.assertIn(self.NOTICE, display["notice"])
        # The title row still reaches the evidence the user can inspect.
        self.assertIn(LAW_NAME, {source.get("law_name") for source in body["law_sources"]})

    def test_f10_ask_public_fields_for_a_fetched_article(self) -> None:
        body = self._ask(self.CITED_QUESTION, f"{LAW_NAME} 제4조에 따라 가정생활을 영위할 권리가 있습니다.")
        self.assertEqual(body["law_grounding_status_detail"], "law_grounding_verified")
        self.assertTrue(body["law_grounding_verified"])
        self.assertEqual(body["law_grounding_user_notice"], "")
        self.assertIn(LAW_NAME, {source.get("law_name") for source in body["law_grounding_display"]["sources"]})


# ---------------------------------------------------------------------------
# F11 (SEC-10, T5): the parser never raises and never burns seconds of CPU.
# ---------------------------------------------------------------------------
def _stack_depth() -> int:
    frame, depth = sys._getframe(), 0
    while frame is not None:
        depth += 1
        frame = frame.f_back
    return depth


class F11ParserBoundsTests(_CleanEnvMixin, unittest.TestCase):
    def test_f11_deep_xml_never_raises_out_of_the_parser(self) -> None:
        # The RecursionError window is a few levels wide and moves with the
        # caller's stack depth (security note 15 §5), so sweep every depth up to
        # just past a recursion limit set relative to this frame.
        headroom = 300
        old_limit = sys.getrecursionlimit()
        escaped: List[Tuple[str, int]] = []
        outcomes: Dict[str, set] = {"parse": set(), "search": set()}
        sys.setrecursionlimit(_stack_depth() + headroom)
        try:
            for depth in range(headroom - 140, headroom + 10):
                body = "<a>" * depth + "x" + "</a>" * depth
                try:
                    outcomes["parse"].add(lt.parse_law_search_response(body)["error_type"])
                except RecursionError:
                    escaped.append(("parse_law_search_response", depth))
                try:
                    result = lt.search_laws(
                        "가상체류관리법", config=_cfg(), transport=lambda url, timeout, b=body: _ok(b),
                    )
                    outcomes["search"].add(result["error_type"])
                except RecursionError:
                    escaped.append(("search_laws", depth))
        finally:
            sys.setrecursionlimit(old_limit)
        self.assertEqual(escaped, [])
        self.assertEqual(outcomes, {"parse": {lt.LAW_API_PARSE_ERROR}, "search": {lt.LAW_API_PARSE_ERROR}})

    def test_f11_deep_json_is_typed_and_cheap(self) -> None:
        node: Any = "x"
        for _ in range(600):
            node = {"k": node, "p": "y" * 1600}
        body = json.dumps(node)  # about 0.95 MB, 600 objects deep
        started = time.perf_counter()
        payload, error, parser_status, _shape = lt._parse_payload(body)
        elapsed = time.perf_counter() - started
        self.assertIsNone(payload)
        self.assertEqual((error, parser_status), (lt.LAW_API_PARSE_ERROR, "nesting_too_deep"))
        # The old error walk stringified every subtree at every level: about
        # 3.4 s for this body on the pristine code (law-stack-fixes.md, F11).
        self.assertLess(elapsed, 0.5)

    def test_f11_error_like_keys_inside_rows_are_data_not_an_envelope(self) -> None:
        body = json.dumps({"LawSearch": {"totalCnt": "1", "law": [{
            "법령명한글": "가상체류관리법", "법령ID": "999999", "법령일련번호": "1",
            "부가정보": {"code": "X1", "message": "invalid"},
        }]}}, ensure_ascii=False)
        parsed = lt.parse_law_search_response(body)
        self.assertEqual(parsed["error_type"], "")
        self.assertEqual([row["law_name"] for row in parsed["results"]], ["가상체류관리법"])
        # An envelope at the root or under the family wrapper still counts.
        for envelope in ({"resultCode": "99", "message": "ERROR"},
                         {"LawSearch": {"resultCode": "99", "message": "ERROR"}}):
            with self.subTest(envelope=envelope):
                self.assertEqual(
                    lt.parse_law_search_response(json.dumps(envelope))["error_type"], lt.LAW_API_OFFICIAL_ERROR,
                )


# ---------------------------------------------------------------------------
# F12 (SEC-06b, T10): OC-bearing requests follow redirects only within law.go.kr.
# ---------------------------------------------------------------------------
class _FakeLawHost(urllib.request.BaseHandler):
    """In-process http(s) handler: answers from ``routes`` and records each URL.

    ``handler_order`` 1 runs it before the proxy and the real HTTP(S) handlers,
    so no request leaves the process.
    """

    handler_order = 1

    def __init__(self, routes: Callable[[str], Tuple[int, str, str]]) -> None:
        self.routes = routes
        self.seen: List[str] = []

    def _serve(self, req: urllib.request.Request) -> Any:
        self.seen.append(req.full_url)
        code, location, body = self.routes(req.full_url)
        headers = email.message.Message()
        headers["Content-Type"] = "application/json;charset=UTF-8"
        if location:
            headers["Location"] = location
        response = urllib.response.addinfourl(io.BytesIO(body.encode("utf-8")), headers, req.full_url, code)
        response.msg = "Found" if location else "OK"
        return response

    http_open = _serve
    https_open = _serve


@contextmanager
def _captured_warnings() -> Iterator[List[str]]:
    """Formatted WARNING lines of the ``paradiso.law_tools`` logger."""
    lines: List[str] = []

    class _Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            lines.append(record.getMessage())

    handler = _Collect(level=logging.WARNING)
    law_logger = logging.getLogger("paradiso.law_tools")
    previous_level = law_logger.level
    law_logger.setLevel(logging.WARNING)
    law_logger.addHandler(handler)
    try:
        yield lines
    finally:
        law_logger.removeHandler(handler)
        law_logger.setLevel(previous_level)


@contextmanager
def _served_by(routes: Callable[[str], Tuple[int, str, str]]) -> Iterator[_FakeLawHost]:
    """Route every urllib opener built in the block through ``_FakeLawHost``."""
    host = _FakeLawHost(routes)
    real_build_opener = urllib.request.build_opener

    def build_opener(*handlers: Any) -> urllib.request.OpenerDirector:
        return real_build_opener(*handlers, host)

    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("a real connection was attempted")

    with patch("urllib.request.build_opener", build_opener), \
         patch("urllib.request._opener", None), \
         patch("socket.create_connection", side_effect=refuse):
        yield host


class F12RedirectTests(_CleanEnvMixin, unittest.TestCase):
    START = f"https://www.law.go.kr/DRF/lawSearch.do?OC={DUMMY_OC}&target=law&type=JSON&query=x"
    REFUSED = (
        f"https://attacker.example/collect?OC={DUMMY_OC}",
        f"https://www.law.go.kr.attacker.example/DRF/lawSearch.do?OC={DUMMY_OC}",
        f"http://www.law.go.kr/DRF/lawSearch.do?OC={DUMMY_OC}",  # https -> http downgrade
        f"https://www.law.go.kr:8443/DRF/lawSearch.do?OC={DUMMY_OC}",
        f"https://user@www.law.go.kr/DRF/lawSearch.do?OC={DUMMY_OC}",
        f"//attacker.example/collect?OC={DUMMY_OC}",  # scheme-relative: resolves to https://attacker.example
    )

    @staticmethod
    def _routes(start: str, location: str, code: int = 302) -> Callable[[str], Tuple[int, str, str]]:
        def routes(url: str) -> Tuple[int, str, str]:
            if url == start:
                return code, location, ""
            return 200, "", EMPTY_LAW_SEARCH
        return routes

    def test_f12_redirect_off_law_go_kr_is_not_followed(self) -> None:
        for location in self.REFUSED:
            with self.subTest(location=location):
                with _served_by(self._routes(self.START, location)) as host:
                    resp = lt._http_get_once(self.START, 1.0)
                self.assertEqual(host.seen, [self.START])
                self.assertFalse(resp.ok)
                self.assertEqual((resp.status_code, resp.error_type), (302, "http_error"))

    def test_f12_every_hop_of_a_chain_is_checked(self) -> None:
        hop = "https://law.go.kr/DRF/lawSearch.do?target=law&page=2"

        def routes(url: str) -> Tuple[int, str, str]:
            if url == self.START:
                return 301, hop, ""
            if url == hop:
                return 302, f"https://attacker.example/collect?OC={DUMMY_OC}", ""
            return 200, "", EMPTY_LAW_SEARCH

        with _served_by(routes) as host:
            resp = lt._http_get_once(self.START, 1.0)
        self.assertEqual(host.seen, [self.START, hop])
        self.assertEqual((resp.ok, resp.status_code, resp.error_type), (False, 302, "http_error"))

    def test_f12_redirect_within_law_go_kr_is_followed(self) -> None:
        plain_start = "http://" + self.START[len("https://"):]
        cases = (
            (self.START, "https://law.go.kr/DRF/lawSearch.do?target=law&page=2"),
            (self.START, "/DRF/lawSearch.do?target=law&page=2"),
            (plain_start, "https://www.law.go.kr/DRF/lawSearch.do?target=law&page=2"),  # upgrade
        )
        for start, location in cases:
            with self.subTest(start=start[:8], location=location):
                with _served_by(self._routes(start, location, code=301)) as host:
                    resp = lt._http_get_once(start, 1.0)
                self.assertEqual(len(host.seen), 2, host.seen)
                self.assertTrue(resp.ok)
                self.assertEqual(resp.text, EMPTY_LAW_SEARCH)

    def test_f12_refused_redirect_is_typed_logged_once_and_not_retried_over_http(self) -> None:
        location = f"https://attacker.example/collect?OC={DUMMY_OC}"

        def routes(url: str) -> Tuple[int, str, str]:
            if urlsplit(url).hostname == "www.law.go.kr":
                return 302, location, ""
            return 200, "", EMPTY_LAW_SEARCH

        getattr(lt, "_WARNINGS_LOGGED", set()).clear()  # logged once per process
        with _served_by(routes) as host, _captured_warnings() as lines:
            result = lt.search_laws("가상체류관리법", config=_cfg())
            lt.search_laws("가상체류관리법", config=_cfg())
        self.assertEqual(len(host.seen), 2, host.seen)
        self.assertTrue(all(urlsplit(u).hostname == "www.law.go.kr" and urlsplit(u).scheme == "https"
                            for u in host.seen), host.seen)
        self.assertEqual(result["error_type"], lt.LAW_API_HTTP_ERROR)
        self.assertEqual(result["raw_status"], 302)
        self.assertNotIn(DUMMY_OC, json.dumps(result, ensure_ascii=False))
        joined = "\n".join(lines)
        self.assertEqual(sum("LAW_API_REDIRECT_REFUSED" in line for line in lines), 1, lines)
        self.assertNotIn(DUMMY_OC, joined)
        self.assertNotIn("attacker.example", joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
