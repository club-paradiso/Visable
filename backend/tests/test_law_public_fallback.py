"""Public-transport fallback for DRF law grounding (Task 1, 2026-11-05).

DRF requires the OC to be registered for the caller's egress IP/domain.
Where that registration fails, ``services.law_public`` serves the same
official current text from the credential-free law.go.kr pages.  These tests
pin the contract with fully mocked HTTP on both transports:

* DRF stays primary — the public path only fires after a DRF failure.
* "not configured" stays "not configured" (no credential, no fallback).
* An injected (test/offline) transport disables the fallback entirely, so
  hermetic suites never reach the live site.
* A citation only verifies when the public body actually contains the
  requested article text — no label inflation.
"""

from __future__ import annotations

import pytest

from services import law_public, law_tools as lt
from services.grounding_config import GroundingConfig

LAW_NAME = "출입국관리법"
DISCOVERY_HTML = (
    '<html><body><iframe src="/LSW/lsInfoP.do?lsiSeq=290729&amp;efYd=20260102">'
    "</iframe></body></html>"
)
BODY_HTML = """<html><body>
<div>[시행 2026. 1. 2.] [법률 제21000호, 2025. 12. 30., 일부개정]</div>
<p class="pty1_p4"><input type="checkbox" name="joNoList" value="1:0:000100:1" /> <label>제1조(목적)</label> 이 법은 대한민국에 입출국하는 모든 국민 및 대한민국에 체류하는 외국인의 출입국관리에 관한 사항을 규정함을 목적으로 한다.</p>
<p class="pty1_p4"><input type="checkbox" name="joNoList" value="1:0:002100:1" /> <label>제21조(근무처의 변경ㆍ추가)</label> 대한민국에 체류하는 외국인이 그 체류자격의 범위에서 근무처를 변경하거나 추가하려면 미리 법무부장관의 허가를 받아야 한다.</p>
</body></html>"""


def _cfg(**over) -> GroundingConfig:
    base = dict(mode="enabled", law_api_oc="test-oc")
    base.update(over)
    return GroundingConfig(**base)


class FakePublicFetch:
    """law_public fetch seam: serves the two public pages, records calls."""

    def __init__(self, *, discovery_status: int = 200, body_status: int = 200):
        self.urls: list = []
        self.discovery_status = discovery_status
        self.body_status = body_status

    def __call__(self, url: str, timeout: float):
        self.urls.append(url)
        if "lsInfoR.do" in url:
            return self.body_status, BODY_HTML if self.body_status == 200 else ""
        return self.discovery_status, DISCOVERY_HTML if self.discovery_status == 200 else ""


@pytest.fixture(autouse=True)
def _reset_cache():
    law_public.reset_public_cache_for_tests()
    yield
    law_public.reset_public_cache_for_tests()


@pytest.fixture()
def public_fetch(monkeypatch):
    fetch = FakePublicFetch()
    monkeypatch.setattr(law_public, "_default_fetch", fetch)
    return fetch


@pytest.fixture()
def drf_down(monkeypatch):
    """Make the default DRF transport fail at the network level."""

    def _down(url: str, timeout: float):
        return lt.LawHttpResponse(ok=False, status_code=0, text="", error_type="network")

    monkeypatch.setattr(lt, "_default_transport", _down)
    return _down


# ---------------------------------------------------------------------------
# law_public unit behavior
# ---------------------------------------------------------------------------

def test_discover_current_parses_iframe_pointer(public_fetch):
    found = law_public.discover_current(LAW_NAME)
    assert found == ("290729", "20260102")
    # Success-only cache: a second lookup must not re-fetch.
    assert law_public.discover_current(LAW_NAME) == found
    assert len(public_fetch.urls) == 1


def test_discovery_failure_is_not_cached(monkeypatch):
    fetch = FakePublicFetch(discovery_status=404)
    monkeypatch.setattr(law_public, "_default_fetch", fetch)
    assert law_public.discover_current(LAW_NAME) is None
    fetch.discovery_status = 200
    assert law_public.discover_current(LAW_NAME) == ("290729", "20260102")


def test_fetch_law_document_parses_articles(public_fetch):
    doc = law_public.fetch_law_document(LAW_NAME)
    assert doc is not None
    assert doc["law_serial_no"] == "290729"
    assert doc["enforcement_date"] == "20260102"
    labels = [a["article_label"] for a in doc["articles"]]
    assert labels == ["제1조", "제21조"]
    article21 = doc["articles"][1]
    assert article21["article_title"] == "근무처의 변경ㆍ추가"
    assert "근무처를 변경하거나 추가하려면" in article21["text"]


def test_law_name_candidates_prefers_longest_law_name_prefix():
    candidates = law_public.law_name_candidates("출입국관리법 시행령 제26조의2 근무처 변경")
    assert candidates[0] == "출입국관리법 시행령"
    assert law_public.law_name_candidates("출입국관리법") == ["출입국관리법"]
    assert law_public.law_name_candidates("출입국관리법 제21조 근무처 변경 허가")[0] == "출입국관리법"


def test_search_law_rows_returns_normalized_candidate(public_fetch):
    rows = law_public.search_law_rows("출입국관리법 제21조 근무처 변경 허가")
    assert len(rows) == 1
    row = rows[0]
    assert row["law_name"] == LAW_NAME
    assert row["law_serial_no"] == "290729"
    assert row["retrieval_status"] == "ok"
    assert row["transport"] == "public"
    assert "OC=" not in row["source_url"]


def test_detail_for_law_filters_to_requested_article(public_fetch):
    found = law_public.detail_for_law(LAW_NAME, "제21조")
    assert found is not None
    assert [a["article_label"] for a in found["articles"]] == ["제21조"]
    missing = law_public.detail_for_law(LAW_NAME, "제99조")
    assert missing is not None
    assert missing["articles"] == []


# ---------------------------------------------------------------------------
# law_tools wiring
# ---------------------------------------------------------------------------

def test_search_laws_falls_back_to_public_when_drf_down(drf_down, public_fetch):
    result = lt.search_laws("출입국관리법 제21조 근무처 변경", config=_cfg())
    assert result["status"] == "ok"
    assert result["transport"] == "public_fallback"
    assert result["fallback_from"] == lt.LAW_API_BAD_RESPONSE
    assert result["results"][0]["law_name"] == LAW_NAME


def test_search_laws_no_fallback_with_injected_transport(public_fetch):
    def _failing(url: str, timeout: float):
        return lt.LawHttpResponse(ok=False, status_code=0, text="", error_type="network")

    result = lt.search_laws("출입국관리법", config=_cfg(), transport=_failing)
    assert result["status"] == "error"
    assert public_fetch.urls == []  # hermetic: public path never consulted


def test_search_laws_not_configured_never_falls_back(drf_down, public_fetch):
    cfg = GroundingConfig(mode="enabled")  # no OC, no key
    result = lt.search_laws("출입국관리법", config=cfg)
    assert result["error_type"] == lt.LAW_API_NOT_CONFIGURED
    assert public_fetch.urls == []


def test_search_laws_drf_ok_skips_public(monkeypatch, public_fetch):
    body = (
        '{"LawSearch": {"law": [{"법령명한글": "출입국관리법", "법령일련번호": "290729",'
        ' "법령ID": "001386"}]}}'
    )

    def _ok(url: str, timeout: float):
        return lt.LawHttpResponse(ok=True, status_code=200, text=body)

    monkeypatch.setattr(lt, "_default_transport", _ok)
    result = lt.search_laws("출입국관리법", config=_cfg())
    assert result["status"] == "ok"
    assert result.get("transport") != "public_fallback"
    assert public_fetch.urls == []


def test_search_laws_public_miss_keeps_drf_error(drf_down, monkeypatch):
    fetch = FakePublicFetch(discovery_status=404)
    monkeypatch.setattr(law_public, "_default_fetch", fetch)
    result = lt.search_laws("출입국관리법", config=_cfg())
    assert result["status"] == "error"
    assert result["error_type"] == lt.LAW_API_BAD_RESPONSE


def test_get_law_detail_falls_back_to_public(drf_down, public_fetch):
    result = lt.get_law_detail(law_name=LAW_NAME, article="제21조", config=_cfg())
    assert result["status"] == "ok"
    assert result["transport"] == "public_fallback"
    detail = result["detail"]
    assert detail["law_name"] == LAW_NAME
    assert [a["article_label"] for a in detail["articles"]] == ["제21조"]
    assert "근무처를 변경하거나 추가하려면" in detail["articles"][0]["text"]


def test_article_verification_uses_public_fallback(drf_down, public_fetch):
    """End-to-end honesty check: with DRF down, a cited article verifies only
    because the public official body actually contains its text."""
    from services.law_grounding import _verify_requested_articles

    search = lt.search_laws("출입국관리법", config=_cfg())
    assert search["status"] == "ok"
    outcome = _verify_requested_articles(
        "출입국관리법 제21조에 따라 근무처 변경 허가를 받아야 하나요?",
        search["results"],
        law_tools=lt,
        config=_cfg(),
    )
    verified = [c for c in outcome["citations"] if c["verification_status"] == "verified"]
    assert verified, outcome
    assert "근무처를 변경하거나 추가하려면" in verified[0]["snippet"]
