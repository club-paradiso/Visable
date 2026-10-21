"""Fixture adapter: bundle loading and validation, coverage, heading units, scripted faults, call counting."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from waymaker_ai.contracts import Coverage, LookupStatus, ProvisionRef
from waymaker_ai.legal import adapters
from waymaker_ai.legal.adapters import BundleError, FixtureAdapter, load_bundle, validate_bundle

SOURCES = Path(__file__).resolve().parents[1] / "datasets" / "fixtures" / "sources"
CORE = SOURCES / "synthetic_core.json"
ACT = "SYN-ACT-0001"
A1_2026 = ("SYN-A1-1003", "2026-10-02")


@pytest.fixture()
def bundle():
    return json.loads(CORE.read_text(encoding="utf-8"))


@pytest.fixture()
def adapter(bundle):
    return FixtureAdapter.from_bundle(bundle)


# -- loading -------------------------------------------------------------------
def test_load_bundle_by_id_and_from_file_agree():
    by_id = load_bundle("synthetic_core", SOURCES)
    assert by_id["bundle_id"] == "synthetic_core"
    assert FixtureAdapter.from_file(CORE).bundle_id == FixtureAdapter.from_id("synthetic_core").bundle_id


@pytest.mark.parametrize("bundle_id", ["../synthetic_core", "Synthetic", "", ".hidden", "a/b"])
def test_bundle_ids_cannot_leave_the_fixture_directory(bundle_id):
    with pytest.raises(BundleError):
        load_bundle(bundle_id, SOURCES)


def test_a_file_whose_bundle_id_differs_from_its_name_is_rejected(tmp_path, bundle):
    (tmp_path / "other.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(BundleError, match="does not match"):
        load_bundle("other", tmp_path)


def test_the_synthetic_core_bundle_is_valid_and_synthetic_only(bundle):
    assert validate_bundle(bundle) == []
    assert bundle["provenance"] == "synthetic_fixture"
    for key in ("versions", "provisions"):
        assert {r["provenance"] for r in bundle[key]} == {"synthetic_fixture"}
        assert all(not r.get("official_url") for r in bundle[key])


def test_the_synthetic_core_bundle_scripts_one_fault_of_each_raw_body_kind(bundle):
    kinds = sorted(f["raw_body_kind"] for f in bundle["faults"])
    assert kinds == sorted(adapters.RAW_BODY_KINDS)


def test_the_synthetic_core_bundle_has_the_shapes_the_unit_tests_need(bundle):
    versions = bundle["versions"]
    assert any(r["unit_kind"] == "heading" for r in bundle["provisions"])
    assert any(v["provision_effective_dates"] for v in versions)                     # deferred provision
    assert any(v["is_repeal"] for v in versions)                                     # repeal
    assert any(i["former_titles"] for i in bundle["identities"])                     # renamed law
    assert any(a["kind"] == "transitional" for a in bundle["addenda"])               # 경과조치
    keys = [(v["stable_id"], v["version_id"]) for v in versions]
    assert len(keys) != len(set(keys))                                               # one 일련번호, two dates
    scopes = [p["scope"] for p in bundle["provisions"] if p.get("scope")]
    assert any(s["status_codes"] and not s["subcodes"] and not s["all_subcodes_explicit"] for s in scopes)
    assert any(s["subcodes"] for s in scopes)
    with_units = [p for p in bundle["provisions"] if p.get("paragraphs")]
    assert any(p.get("structure_complete") is True for p in with_units)       # authoritative sub-unit absence
    assert any("structure_complete" not in p for p in with_units)             # and the default (unavailable)


# -- validation ------------------------------------------------------------------
def _errors_after(bundle, mutate):
    changed = copy.deepcopy(bundle)
    mutate(changed)
    return validate_bundle(changed)


def test_a_synthetic_bundle_may_not_carry_an_official_url(bundle):
    def mutate(b):
        b["provisions"][1]["official_url"] = "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=1"
    assert any("official URL" in e for e in _errors_after(bundle, mutate))


def test_a_verified_bundle_may_not_hold_synthetic_records(bundle):
    def mutate(b):
        b["provenance"] = "verified_web"
    assert any("synthetic_fixture" in e for e in _errors_after(bundle, mutate))


def test_a_failed_raw_body_can_never_report_not_found(bundle):
    def mutate(b):
        b["faults"][0]["status"] = "not_found"
    assert any("failed response" in e for e in _errors_after(bundle, mutate))


def test_duplicate_version_keys_and_dangling_provisions_are_rejected(bundle):
    def duplicate(b):
        b["versions"].append(copy.deepcopy(b["versions"][0]))
    assert any("duplicate version key" in e for e in _errors_after(bundle, duplicate))

    def dangling(b):
        b["provisions"][1]["effective_date"] = "2021-01-01"
    assert any("no version" in e for e in _errors_after(bundle, dangling))


def test_returnable_units_need_unique_evidence_ids_but_heading_units_may_share_one(bundle):
    headings = [p for p in bundle["provisions"] if p["unit_kind"] == "heading"]

    def two_headings_one_number(b):   # 제4장 and 제1절 both printed before one article
        extra = copy.deepcopy(headings[0])
        extra["text"] = extra["heading"] = "제1절 가상 통칙"
        b["provisions"].append(extra)
    assert _errors_after(bundle, two_headings_one_number) == []

    def duplicate_article(b):
        b["provisions"].append(copy.deepcopy(b["provisions"][1]))
    assert any("duplicate" in e for e in _errors_after(bundle, duplicate_article))


def test_unknown_fault_match_keys_are_rejected(bundle):
    def mutate(b):
        b["faults"][0]["match"] = {"law": "가상체류관리법"}
    assert any("unknown keys" in e for e in _errors_after(bundle, mutate))


# -- titles and coverage -------------------------------------------------------------
@pytest.mark.parametrize("title", ["가상체류관리법", "가상외국인체류법", "가상체류법", "가상 체류관리법"])
def test_titles_resolve_by_official_former_and_short_title(adapter, title):
    lookup, found = adapter.resolve_title(title)
    assert lookup.status is LookupStatus.FOUND and lookup.coverage is Coverage.COMPLETE
    assert [i.stable_id for i in found] == [ACT]


def test_a_near_title_is_not_found_and_only_named_in_detail(adapter):
    lookup, found = adapter.resolve_title("가상체류관리")
    assert lookup.status is LookupStatus.NOT_FOUND and found == []
    assert "가상체류관리법" in lookup.detail


def test_a_partial_title_index_knows_current_titles_only(bundle):
    bundle["title_index_coverage"] = "partial"
    adapter = FixtureAdapter.from_bundle(bundle)
    lookup, found = adapter.resolve_title("가상외국인체류법")   # former title
    assert lookup.status is LookupStatus.NOT_FOUND and lookup.coverage is Coverage.PARTIAL and found == []
    assert adapter.resolve_title("가상체류법")[1][0].stable_id == ACT   # short title is current
    assert "가상외국인체류법" not in adapter.known_titles()


def test_history_coverage_comes_from_the_bundle_and_defaults_to_partial(adapter, bundle):
    assert adapter.list_versions(ACT)[0].coverage is Coverage.COMPLETE
    assert adapter.list_versions("SYN-ACT-0008")[0].coverage is Coverage.PARTIAL
    del bundle["history_coverage"][ACT]
    assert FixtureAdapter.from_bundle(bundle).list_versions(ACT)[0].coverage is Coverage.PARTIAL


def test_versions_are_listed_oldest_first_with_one_entry_per_effective_date(adapter):
    _, versions = adapter.list_versions("SYN-RUL-0001")
    assert [v.key for v in versions] == [
        ("SYN-R1-3001", "2020-01-01"), ("SYN-R1-3002", "2026-09-15"), ("SYN-R1-3002", "2027-09-16"),
    ]


# -- provisions ----------------------------------------------------------------------
def test_a_heading_unit_sharing_an_article_number_is_never_returned(adapter):
    lookup, text = adapter.get_provision(ACT, A1_2026, ProvisionRef(article=1))
    assert lookup.status is LookupStatus.FOUND
    assert text.heading == "목적" and "총칙" not in text.full_text()


def test_an_article_that_exists_only_as_a_heading_unit_is_not_found(adapter):
    lookup, text = adapter.get_provision(ACT, A1_2026, ProvisionRef(article=9))   # "제2장 보칙"
    assert lookup.status is LookupStatus.NOT_FOUND and lookup.coverage is Coverage.COMPLETE and text is None


def test_paragraph_and_item_references_fetch_their_article(adapter):
    lookup, text = adapter.get_provision(ACT, A1_2026, ProvisionRef(article=5, paragraph=2, item=1))
    assert lookup.status is LookupStatus.FOUND and text.provision_key == "제5조"
    assert sorted(text.paragraphs) == [1, 2] and "2:1" in text.items


def test_annexes_are_fetched_by_their_key(adapter):
    lookup, text = adapter.get_provision("SYN-RUL-0001", ("SYN-R1-3002", "2026-09-15"), ProvisionRef(annex="별표 1"))
    assert lookup.status is LookupStatus.FOUND and text.scope.subcodes == ("E-7-1", "E-7-T")


def test_a_missing_article_of_a_partly_parsed_version_is_not_an_authoritative_absence(adapter):
    lookup, _ = adapter.get_provision(ACT, ("SYN-A1-1004", "2027-06-01"), ProvisionRef(article=7))
    assert lookup.status is LookupStatus.NOT_FOUND and lookup.coverage is Coverage.PARTIAL


def test_structure_complete_is_read_per_provision_and_defaults_to_false(adapter, bundle):
    lookup, text = adapter.get_provision(ACT, A1_2026, ProvisionRef(article=5, paragraph=3))
    assert lookup.status is LookupStatus.FOUND and text.structure_complete is True       # marked in the bundle
    assert adapter.get_provision(ACT, A1_2026, ProvisionRef(article=6))[1].structure_complete is False   # omitted
    pending = adapter.get_provision(ACT, ("SYN-A1-1004", "2027-06-01"), ProvisionRef(article=5))[1]
    assert pending.structure_complete is False    # same article, another version: its own record decides
    record = next(p for p in bundle["provisions"] if p["evidence_id"].endswith("SYN-A1-1003@2026-10-02:제5조"))
    assert adapters.provision_from_record({**record, "structure_complete": False}).structure_complete is False
    without = {k: v for k, v in record.items() if k != "structure_complete"}
    assert adapters.provision_from_record(without).structure_complete is False


@pytest.mark.parametrize("value", ["true", 1, None, []])
def test_a_non_boolean_structure_complete_is_rejected(bundle, value):
    def mutate(b):
        b["provisions"][1]["structure_complete"] = value
    assert any("structure_complete" in e for e in _errors_after(bundle, mutate))


def test_an_unknown_version_is_not_an_authoritative_absence(adapter):
    lookup, _ = adapter.get_provision(ACT, ("SYN-A1-1003", "2026-10-03"), ProvisionRef(article=5))
    assert lookup.status is LookupStatus.NOT_FOUND and lookup.coverage is Coverage.PARTIAL


# -- addenda and guidance ------------------------------------------------------------
def test_addenda_coverage_depends_on_whether_the_부칙_was_read(adapter):
    lookup, addenda = adapter.get_addenda(ACT, A1_2026)
    assert lookup.status is LookupStatus.FOUND and lookup.coverage is Coverage.COMPLETE
    assert {a.kind for a in addenda} == {"effective_date", "transitional"}
    read_none = adapter.get_addenda(ACT, ("SYN-A1-1002", "2024-03-01"))[0]
    assert read_none.status is LookupStatus.NOT_FOUND and read_none.coverage is Coverage.COMPLETE
    unread = adapter.get_addenda(ACT, ("SYN-A1-1004", "2027-06-01"))[0]   # has_transitional_provisions: null
    assert unread.status is LookupStatus.NOT_FOUND and unread.coverage is Coverage.PARTIAL


def test_guidance_by_topic(adapter):
    lookup, items = adapter.guidance("syn_fee_payment_method")
    assert lookup.status is LookupStatus.FOUND and [i.value for i in items] == ["cash_only"]
    assert adapter.guidance("syn_no_such_topic")[0].status is LookupStatus.NOT_FOUND


# -- faults --------------------------------------------------------------------------
FAULT_CALLS = [
    ("html", lambda a: a.resolve_title("가상응답장애법")),
    ("empty", lambda a: a.resolve_title("가상빈응답법")),
    ("official_error", lambda a: a.resolve_title("가상인증장애법")),
    ("malformed_json", lambda a: a.list_versions("SYN-ACT-0004")),
    ("malformed_xml", lambda a: a.get_provision(ACT, A1_2026, ProvisionRef(article=8))),
    ("http_429", lambda a: a.get_provision(ACT, A1_2026, ProvisionRef(article=9, article_branch=2))),
    ("timeout", lambda a: a.get_addenda("SYN-ACT-0005", ("SYN-A5-8001", "2020-01-01"))),
    ("http_500", lambda a: a.guidance("syn_guidance_outage")),
]


@pytest.mark.parametrize("kind, call", FAULT_CALLS, ids=[k for k, _ in FAULT_CALLS])
def test_every_scripted_fault_is_a_failure_with_no_payload(adapter, kind, call):
    lookup, payload = call(adapter)
    assert lookup.status.is_failure, kind
    assert lookup.status is not LookupStatus.NOT_FOUND
    assert payload in (None, [])
    assert kind in lookup.detail


def test_a_fault_only_fits_the_call_it_matches(adapter):
    assert adapter.get_provision(ACT, A1_2026, ProvisionRef(article=8))[0].status.is_failure
    assert adapter.get_provision(ACT, A1_2026, ProvisionRef(article=5))[0].status is LookupStatus.FOUND


def test_every_call_is_counted_and_spends_one_upstream_call(adapter):
    results = [
        adapter.resolve_title("가상체류관리법")[0],
        adapter.list_versions(ACT)[0],
        adapter.get_provision(ACT, A1_2026, ProvisionRef(article=5))[0],
        adapter.get_addenda(ACT, A1_2026)[0],
        adapter.guidance("syn_report_deadline")[0],
        adapter.resolve_title("가상응답장애법")[0],   # a fault is counted too
    ]
    assert [r.calls for r in results] == [1] * 6
    assert dict(adapter.call_counts) == {
        "resolve_title": 2, "list_versions": 1, "get_provision": 1, "get_addenda": 1, "guidance": 1,
    }
    assert adapter.total_calls == 6
    adapter.reset_counts()
    assert adapter.total_calls == 0
