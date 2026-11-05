"""Precedent grounding follow-up (Task 2, 2026-11-05).

Production diagnosis (measured on the live Railway backend): DRF
``target=prec`` works from Railway — the product's own
``/api/legal/precedents/search`` returns 9 rows for ``출입국관리법`` and 6 for
``강제퇴거``.  /api/ask still surfaced zero precedents because

* the evidence pack searched with the planner's long phrase
  (``출입국관리법 체류자격 신고의무 신고``), which the case-name search
  cannot match (0 rows), and
* ``legal_evidence`` stopped at the first variant returning *anything* —
  the broad statute-name variant returns criminal-title cases, which the
  topic gate then rejected wholesale (``no_relevant_results``).

These tests pin the fixes with mocked HTTP only: bare issue keywords are
tried, variants are collected across until one passes the (unchanged)
relevance gate, and precedent *detail* falls back to the credential-free
public ``precInfoR.do`` page (same serial space as DRF) when DRF fails.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from services import law_public, law_tools as lt, legal_evidence as le, precedent_sources as ps
from services.citation_verifier import precedent_keyword_queries
from services.grounding_config import GroundingConfig


def _cfg(**over) -> GroundingConfig:
    base = dict(mode="enabled", law_api_oc="test-oc")
    base.update(over)
    return GroundingConfig(**base)


DEPORTATION_QUESTION = "강제퇴거 취소소송에서 출입국관리법 제60조 재량권 일탈 남용에 대한 대법원 판례를 알려주세요"

PREC_INFO_HTML = """<html><head><title>강제퇴거명령처분취소</title></head><body>
<div>강제퇴거명령처분취소</div>
<div>[대법원 2020. 1. 16. 선고 2019두12345 판결]</div>
<div>【판시사항】 강제퇴거명령이 재량권을 일탈·남용한 것으로 볼 수 있는 경우에 대한 판단 기준</div>
<div>【판결요지】 출입국관리법 제60조에 따른 강제퇴거명령은 재량행위이나, 그 행사에 재량권의 일탈·남용이 있으면 위법하다.</div>
<div>【참조조문】 출입국관리법 제60조</div>
<div>【전문】 주문 이유</div>
</body></html>"""

ERROR_PAGE_HTML = "<html><head><title>국가법령정보센터 | 오류페이지</title></head><body>오류</body></html>"


# ---------------------------------------------------------------------------
# Keyword derivation
# ---------------------------------------------------------------------------

def test_keyword_queries_for_deportation_question():
    assert precedent_keyword_queries(DEPORTATION_QUESTION) == ["강제퇴거", "출국명령"]


def test_keyword_queries_for_naturalization_and_visa_issuance():
    assert precedent_keyword_queries("귀화 허가 요건을 알려주세요") == ["귀화"]
    assert precedent_keyword_queries("사증발급 거부 처분을 다투고 싶어요") == ["사증발급"]
    assert precedent_keyword_queries("오늘 날씨 어때요") == []


def test_expand_query_puts_keywords_before_statute_anchor():
    variants = le.expand_query(DEPORTATION_QUESTION, statute_anchors=["출입국관리법"], max_variants=6)
    assert "강제퇴거" in variants and "출국명령" in variants
    assert variants.index("강제퇴거") < variants.index("출입국관리법")


# ---------------------------------------------------------------------------
# legal_evidence: collect across variants until one is on-topic
# ---------------------------------------------------------------------------

def _case(name: str, *, source_id: str, refs: str = "출입국관리법", date: str = "20200116") -> le.LegalCase:
    return le.LegalCase(
        source_type=le.LegalEvidenceSourceType.PRECEDENT,
        source_id=source_id,
        case_name=name,
        case_number="2019두12345",
        court="대법원",
        decision_date=date,
        reference_statutes=refs,
    )


CRIMINAL_CASE = _case("위계공무집행방해·출입국관리법위반", source_id="234321", date="20230313")
DEPORTATION_CASE = _case("강제퇴거명령처분취소", source_id="228541", refs="출입국관리법 제60조")


class _FakeCaseClient:
    """DRF-shaped case client: statute name -> criminal titles only,
    keyword -> the on-topic deportation case, everything else empty."""

    is_available = True

    def __init__(self, mapping):
        self.mapping = mapping
        self.queries: list = []

    def search_cases(self, query, *, source_type="precedent", search=1, display=5, **kw):
        self.queries.append(query)
        cases = self.mapping.get(query) or []
        if cases:
            return {"status": "available", "cases": list(cases), "warnings": []}
        return {"status": "no_results", "cases": [], "warnings": []}

    def get_case_body(self, case_id, *, source_type="precedent"):
        for cases in self.mapping.values():
            for case in cases:
                if case.source_id == case_id:
                    return case
        return None


def test_retrieve_legal_evidence_survives_poison_statute_variant():
    client = _FakeCaseClient({
        "출입국관리법": [CRIMINAL_CASE],
        "강제퇴거": [DEPORTATION_CASE],
    })
    result = le.retrieve_legal_evidence(
        DEPORTATION_QUESTION,
        statute_refs=["출입국관리법"],
        client=client,
    )
    assert result.status == "available", result.warnings
    assert [c.case_name for c in result.cases] == ["강제퇴거명령처분취소"]


def test_retrieve_legal_evidence_gate_still_rejects_off_topic_only_pool():
    client = _FakeCaseClient({"출입국관리법": [CRIMINAL_CASE], "강제퇴거": [CRIMINAL_CASE]})
    result = le.retrieve_legal_evidence(
        DEPORTATION_QUESTION,
        statute_refs=["출입국관리법"],
        client=client,
    )
    assert result.status == "no_relevant_results"
    assert result.cases == []


# ---------------------------------------------------------------------------
# Evidence pack: keyword retry after the planner phrase misses
# ---------------------------------------------------------------------------

_LAW_BODY = json.dumps({"LawSearch": {"law": [
    {"법령명한글": "출입국관리법", "법령일련번호": "290729", "법령ID": "001386"},
]}}, ensure_ascii=False)

_PREC_BODY = json.dumps({"PrecSearch": {"target": "prec", "totalCnt": "1", "prec": [
    {
        "판례일련번호": "228541", "사건명": "강제퇴거명령처분취소", "사건번호": "2019두12345",
        "법원명": "대법원", "법원종류코드": "400201", "선고일자": "20200116",
        "사건종류명": "행정", "판결유형": "판결", "선고": "선고", "데이터출처명": "대법원",
        "판례상세링크": "https://www.law.go.kr/DRF/lawService.do?target=prec&ID=228541&type=HTML",
    },
]}}, ensure_ascii=False)

_PREC_EMPTY = json.dumps({"PrecSearch": {"target": "prec", "totalCnt": "0", "prec": []}}, ensure_ascii=False)


def _pack_transport(url: str, timeout: float) -> lt.LawHttpResponse:
    params = parse_qs(urlsplit(url).query)
    target = (params.get("target") or [""])[0]
    query = (params.get("query") or [""])[0]
    if target == "prec":
        body = _PREC_BODY if query == "강제퇴거" else _PREC_EMPTY
        return lt.LawHttpResponse(ok=True, status_code=200, text=body)
    if target == "law":
        return lt.LawHttpResponse(ok=True, status_code=200, text=_LAW_BODY)
    return lt.LawHttpResponse(ok=True, status_code=200, text="{}")


def test_evidence_pack_keyword_retry_finds_deportation_precedent():
    pack = lt.build_law_evidence_pack(DEPORTATION_QUESTION, config=_cfg(), transport=_pack_transport)
    items = pack.get("precedent_evidence_items") or []
    assert items, pack.get("source_family_statuses")
    assert any("강제퇴거" in (item.get("title") or "") for item in items)
    assert (pack.get("source_family_statuses") or {}).get("precedent") == lt.SOURCE_STATUS_RESULTS_FOUND


# ---------------------------------------------------------------------------
# Public precedent detail fallback
# ---------------------------------------------------------------------------

@pytest.fixture()
def public_prec_page(monkeypatch):
    calls: list = []

    def _fetch(url: str, timeout: float):
        calls.append(url)
        if "precSeq=228541" in url:
            return 200, PREC_INFO_HTML
        return 200, ERROR_PAGE_HTML

    monkeypatch.setattr(law_public, "_default_fetch", _fetch)
    return calls


def _drf_down(url: str, timeout: float) -> lt.LawHttpResponse:
    return lt.LawHttpResponse(ok=False, status_code=0, text="", error_type="network")


def test_parse_public_precedent_html():
    item = ps.parse_public_precedent_html(PREC_INFO_HTML, "228541")
    assert item is not None
    assert item["caseNumber"] == "2019두12345"
    assert item["courtOrAgency"] == "대법원"
    assert item["decisionDate"] == "20200116"
    assert item["resultKind"] == "body_result"
    assert item["quoteSafe"] is True
    assert "재량권" in item["holdingSummary"]
    assert item["url"].endswith("precSeq=228541")
    assert ps.parse_public_precedent_html(ERROR_PAGE_HTML, "999999") is None


def test_get_precedent_detail_public_fallback(monkeypatch, public_prec_page):
    monkeypatch.setattr(lt, "_default_transport", _drf_down)
    envelope = ps.get_precedent_detail("228541", config=_cfg())
    assert envelope["status"] == "results_found"
    assert envelope["parserStatus"] == "public_html"
    item = envelope["items"][0]
    assert item["title"] == "강제퇴거명령처분취소"
    assert public_prec_page, "public page was never fetched"


def test_get_precedent_detail_public_miss_keeps_drf_error(monkeypatch, public_prec_page):
    monkeypatch.setattr(lt, "_default_transport", _drf_down)
    envelope = ps.get_precedent_detail("999999", config=_cfg())
    assert envelope["status"] == "bad_response"


def test_get_precedent_detail_no_fallback_with_injected_transport(public_prec_page):
    envelope = ps.get_precedent_detail("228541", config=_cfg(), transport=_drf_down)
    assert envelope["status"] == "bad_response"
    assert public_prec_page == []
