"""The fake law.go.kr DRF server the existing-law baseline is measured against.

It must answer in the documented response shapes (``LawSearch.law`` rows,
``법령.기본정보`` / ``조문.조문단위``), keep heading units (조문여부 = 전문) in the
article list as the real API does, serve the version in force on the
simulated "today", and turn every bundle fault into the transport event urllib
would produce. Whether the backend's own parser accepts these bodies is tested
in test_evaluation_subprocess.py, where the backend may run.
"""
from __future__ import annotations

import datetime as dt
import json
from urllib.parse import urlencode

from waymaker_ai.evaluation import fake_drf
from waymaker_ai.evaluation.fake_drf import FakeDrfServer, gana_group

from tests.test_evaluation_runner import ACT, make_bundle

TODAY = dt.date(2026, 10, 19)


def search(server: FakeDrfServer, **params: str) -> fake_drf.DrfReply:
    return server.respond("https://www.law.go.kr/DRF/lawSearch.do?" + urlencode({"target": "law", "type": "JSON",
                                                                                  "OC": "x", **params}))


def service(server: FakeDrfServer, **params: str) -> fake_drf.DrfReply:
    return server.respond("https://www.law.go.kr/DRF/lawService.do?" + urlencode({"target": "law", "type": "JSON",
                                                                                   "OC": "x", **params}))


def test_search_rows_use_the_documented_fields_and_the_version_in_force():
    reply = search(FakeDrfServer(make_bundle(), TODAY), query="가상체류관리법")
    assert (reply.event, reply.status, reply.operation) == ("body", 200, "search")
    rows = json.loads(reply.body)["LawSearch"]["law"]
    assert len(rows) == 1
    row = rows[0]
    for key in ("법령명한글", "법령ID", "법령일련번호", "공포일자", "시행일자", "법령구분명", "현행연혁코드"):
        assert key in row, key
    assert (row["법령ID"], row["법령일련번호"], row["시행일자"], row["법령구분명"]) == (ACT, "EVAL-V1", "20200101", "법률")


def test_a_future_version_becomes_current_only_after_its_effective_date():
    later = json.loads(search(FakeDrfServer(make_bundle(), dt.date(2027, 7, 1)), query="가상체류관리법").body)
    assert later["LawSearch"]["law"][0]["법령일련번호"] == "EVAL-V2"


def test_former_titles_are_not_searchable_and_short_titles_match_exactly():
    bundle = make_bundle()
    bundle["identities"][0]["former_titles"] = ["가상외국인체류법"]
    bundle["identities"][0]["short_titles"] = ["가상체류법"]
    server = FakeDrfServer(bundle, TODAY)
    assert "law" not in json.loads(search(server, query="가상외국인체류법").body)["LawSearch"]
    assert json.loads(search(server, query="가상체류법").body)["LawSearch"]["law"][0]["법령ID"] == ACT


def test_service_payload_shape_keeps_heading_units_like_the_real_api():
    reply = service(FakeDrfServer(make_bundle(), TODAY), MST="EVAL-V1")
    law = json.loads(reply.body)["법령"]
    assert list(law)[0] == "기본정보"   # the backend's candidate walk stops at the first dict with a name
    assert law["기본정보"]["법령명_한글"] == "가상체류관리법" and law["기본정보"]["시행일자"] == "20200101"
    units = law["조문"]["조문단위"]
    assert [(u["조문여부"], u["조문번호"]) for u in units] == [("전문", "5"), ("조문", "5")]
    article = units[1]
    assert article["조문제목"] == "가상 신고" and article["조문내용"].startswith("제5조(가상 신고)")
    assert article["조문키"] == "0005001" and units[0]["조문키"] == "0005000"


def test_paragraphs_and_items_render_with_printed_numbers():
    bundle = make_bundle()
    bundle["provisions"][1]["paragraphs"] = {"1": "① 첫째 항", "2": "② 둘째 항"}
    bundle["provisions"][1]["items"] = {"2:1": "1. 첫째 호"}
    article = json.loads(service(FakeDrfServer(bundle, TODAY), MST="EVAL-V1").body)["법령"]["조문"]["조문단위"][1]
    assert [p["항번호"] for p in article["항"]] == ["①", "②"]
    assert article["항"][1]["호"] == [{"호번호": "1.", "호내용": "1. 첫째 호"}]


def test_unknown_law_gets_the_official_no_match_body():
    reply = service(FakeDrfServer(make_bundle(), TODAY), MST="999999")
    assert reply.event == "body" and "기본정보" not in reply.body


def _with_fault(**fault) -> dict:
    bundle = make_bundle()
    bundle["faults"] = [fault]
    return bundle


def test_faults_become_transport_events():
    cases = {
        "html": ("body", 200, "<!DOCTYPE html>"),
        "empty": ("body", 200, ""),
        "malformed_json": ("body", 200, '{"LawSearch"'),
        "http_429": ("http_error", 429, ""),
        "http_500": ("http_error", 500, ""),
        "timeout": ("timeout", 0, ""),
        "official_error": ("body", 200, '{"result"'),
    }
    for kind, (event, status, prefix) in cases.items():
        server = FakeDrfServer(_with_fault(operation="resolve_title", match={"title": "가상체류관리법"},
                                           status="unavailable_parse", raw_body_kind=kind, detail=kind), TODAY)
        reply = search(server, query="가상체류관리법")
        assert (reply.event, reply.status) == (event, status), kind
        assert reply.body.startswith(prefix), kind
        assert reply.fault.startswith("resolve_title:"), kind


def test_status_only_fault_uses_the_status_event():
    server = FakeDrfServer(_with_fault(operation="resolve_title", match={"title": "가상체류관리법"},
                                       status="unavailable_network", raw_body_kind=None, detail="refused"), TODAY)
    assert search(server, query="가상체류관리법").event == "network"


def test_a_provision_fault_applies_only_while_that_article_is_requested():
    server = FakeDrfServer(_with_fault(operation="get_provision", match={"stable_id": ACT, "provision_key": "제5조"},
                                       status="unavailable_rate_limited", raw_body_kind="http_429", detail="429"), TODAY)
    assert service(server, MST="EVAL-V1").event == "body"          # no article known: no match
    server.requested_article = "제7조"
    assert service(server, MST="EVAL-V1").event == "body"          # another article
    server.requested_article = "제 5조"
    reply = service(server, MST="EVAL-V1")
    assert (reply.event, reply.status) == ("http_error", 429)


def test_a_law_wide_provision_fault_applies_to_every_detail_request():
    server = FakeDrfServer(_with_fault(operation="get_provision", match={"stable_id": ACT},
                                       status="unavailable_parse", raw_body_kind="malformed_xml", detail="xml"), TODAY)
    reply = service(server, MST="EVAL-V1")
    assert reply.event == "body" and reply.body.startswith("<?xml")


def test_not_found_title_fault_is_an_authoritative_empty_answer_and_hides_the_listing_row():
    server = FakeDrfServer(_with_fault(operation="resolve_title", match={"title": "가상체류관리법"},
                                       status="not_found", raw_body_kind=None, detail="gone"), TODAY)
    body = json.loads(search(server, query="가상체류관리법").body)["LawSearch"]
    assert body["totalCnt"] == "0" and "law" not in body
    listing = json.loads(search(server, gana=gana_group("가상체류관리법"), sort="lasc").body)["LawSearch"]
    assert "law" not in listing


def test_dictionary_listing_filters_by_gana_group():
    assert gana_group("가상체류관리법") == "ga" and gana_group("출입국관리법") == "cha" and gana_group("abc") == ""
    server = FakeDrfServer(make_bundle(), TODAY)
    assert json.loads(search(server, gana="ga").body)["LawSearch"]["law"][0]["법령ID"] == ACT
    assert "law" not in json.loads(search(server, gana="cha").body)["LawSearch"]


def test_partially_parsed_versions_and_untouched_faults_are_recorded_for_the_report():
    bundle = make_bundle()
    bundle["versions"][0]["parse_status"] = "partial"
    bundle["faults"] = [{"operation": "list_versions", "match": {"stable_id": ACT}, "status": "unavailable_timeout",
                         "raw_body_kind": "timeout", "detail": "t"},
                        {"operation": "get_addenda", "match": {"stable_id": "OTHER"}, "status": "unavailable_timeout",
                         "raw_body_kind": "timeout", "detail": "t"}]
    server = FakeDrfServer(bundle, TODAY)
    assert server.unexercised_faults() == []
    search(server, query="가상체류관리법")
    service(server, MST="EVAL-V1")
    assert server.partial_versions == {f"{ACT}@EVAL-V1:2020-01-01"}
    assert server.unexercised_faults() == [f"list_versions:{ACT}"]   # the other law was never touched


def test_the_server_never_records_or_needs_the_credential():
    reply = search(FakeDrfServer(make_bundle(), TODAY), query="가상체류관리법", OC="must-not-leak")
    assert "must-not-leak" not in reply.body
