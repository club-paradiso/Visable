"""Identity helpers: exact titles only, near matches as display strings, the official-host allowlist."""
from __future__ import annotations

import datetime as dt

import pytest

from waymaker_ai.contracts import SourceFamily, SourceIdentity, SourceVersion
from waymaker_ai.legal.identity import (
    act_title_of,
    decree_title_of,
    exact_matches,
    is_official_url,
    matches_title,
    near_matches,
    public_official_url,
    rule_title_of,
    sort_versions,
    title_kind,
)

ACT = SourceIdentity("synthetic", SourceFamily.STATUTE, "SYN-ACT-0001", "가상체류관리법",
                     former_titles=("가상외국인체류법",), short_titles=("가상체류법",))
DECREE = SourceIdentity("synthetic", SourceFamily.ENFORCEMENT_DECREE, "SYN-DEC-0001", "가상체류관리법 시행령")
SPECIAL_A = SourceIdentity("synthetic", SourceFamily.STATUTE, "SYN-ACT-0003", "가상체류관리특례법", short_titles=("가상특례법",))
SPECIAL_B = SourceIdentity("synthetic", SourceFamily.STATUTE, "SYN-ACT-0007", "가상체류지원특례법", short_titles=("가상특례법",))
ALL = (ACT, DECREE, SPECIAL_A, SPECIAL_B)


@pytest.mark.parametrize("title", ["가상체류관리법", "가상 체류 관리법", "가상외국인체류법", "가상체류법"])
def test_exact_match_after_compact_on_official_former_and_short_titles(title):
    assert exact_matches(ALL, title) == [ACT]


def test_current_only_leaves_out_former_titles():
    assert not matches_title(ACT, "가상외국인체류법", current_only=True)
    assert matches_title(ACT, "가상체류법", current_only=True)


@pytest.mark.parametrize("title", ["가상체류관리", "가상체류관리법 시행령 ", "가상체류관리볍", "신가상체류관리법"])
def test_nothing_looser_than_compact_matches_the_act(title):
    assert ACT not in exact_matches(ALL, title)


def test_a_shared_short_title_is_two_matches_not_a_choice():
    assert exact_matches(ALL, "가상특례법") == [SPECIAL_A, SPECIAL_B]


def test_near_matches_are_display_strings_never_identities():
    near = near_matches(ALL, "가상체류관리")
    assert near and all(isinstance(entry, str) for entry in near)
    assert near[0] == "가상체류관리법 (SYN-ACT-0001)"
    assert "가상체류관리법 시행령 (SYN-DEC-0001)" in near_matches(ALL, "가상체류관리법 시행규칙")
    assert near_matches(ALL, "") == []


def test_title_kind_and_short_form_targets():
    assert [title_kind(t) for t in ("가상체류관리법", "가상체류관리법 시행령", "가상체류관리법시행규칙")] == [
        "act", "decree", "rule"]
    assert act_title_of("가상체류관리법 시행규칙") == "가상체류관리법"
    assert decree_title_of("가상체류관리법 시행규칙") == "가상체류관리법 시행령"
    assert rule_title_of("가상체류관리법") == "가상체류관리법 시행규칙"


@pytest.mark.parametrize("url", [
    "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=289833&efYd=20260915",
    "http://law.go.kr/x",
    "https://WWW.LAW.GO.KR/x",
    "https://www.hikorea.go.kr/info",
    "https://www.law.go.kr:443/x",
])
def test_official_hosts_are_accepted(url):
    assert is_official_url(url)


@pytest.mark.parametrize("url", [
    None, "", "law.go.kr/x", "//law.go.kr/x", "ftp://law.go.kr/x", "javascript:alert(1)",
    "https://law.go.kr.example.com/x", "https://law.go.kr@example.com/x", "https://user:pw@law.go.kr/x",
    "https://example.com/?u=https://law.go.kr", "https://evil-law.go.kr/x", "https://law.go.kr:8443/x",
    "https://law.go.kr./x", "https://law.go.kr /x", "https://law.go.kr\\@example.com", "https://lаw.go.kr/x",
])
def test_everything_else_is_rejected(url):
    assert not is_official_url(url)


def test_public_url_keeps_only_public_query_keys():
    url = "https://www.law.go.kr/DRF/lawService.do?OC=secret-user&target=law&MST=289833&type=JSON"
    public = public_official_url(url)
    assert "OC=" not in public and "secret-user" not in public
    assert "MST=289833" in public and public.startswith("https://www.law.go.kr/DRF/lawService.do?")
    assert public_official_url("https://example.com/?MST=1") is None


def test_versions_sort_by_effective_date_with_undated_last():
    versions = [
        SourceVersion("S", "B", dt.date(2027, 9, 16)),
        SourceVersion("S", "U", None),
        SourceVersion("S", "B", dt.date(2026, 9, 15)),
        SourceVersion("S", "A", dt.date(2020, 1, 1)),
    ]
    assert [v.key for v in sort_versions(versions)] == [
        ("A", "2020-01-01"), ("B", "2026-09-15"), ("B", "2027-09-16"), ("U", None),
    ]
