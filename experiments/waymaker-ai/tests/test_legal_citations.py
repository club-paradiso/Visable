"""Citation scanner: every accepted form, the no-substitution title rule, short forms, spans."""
from __future__ import annotations

import unicodedata

import pytest

from waymaker_ai.legal.citations import (
    article_key_of,
    parse_citation_string,
    parse_citation_strings,
    parse_citations,
    provision_ref_from_key,
)

TITLES = (
    "가상체류관리법", "가상체류관리법 시행령", "가상체류관리법 시행규칙", "가상외국인체류법", "가상체류법",
)


def one(text, **kwargs):
    found = parse_citations(text, known_titles=kwargs.pop("known_titles", TITLES), **kwargs)
    assert len(found) == 1, found
    return found[0]


@pytest.mark.parametrize("text, key", [
    ("가상체류관리법 제5조", "제5조"),
    ("가상체류관리법 제6조의2", "제6조의2"),
    ("가상체류관리법 제5조제1항", "제5조제1항"),
    ("가상체류관리법 제5조 ② 에 따라", "제5조제2항"),
    ("가상체류관리법 제5조제2항제1호", "제5조제2항제1호"),
    ("가상체류관리법 제5조제2항제1호의2", "제5조제2항제1호의2"),
    ("가상체류관리법 제5조제2항제1호가목", "제5조제2항제1호가목"),
    ("가상체류관리법 제5조 제 2 항", "제5조제2항"),
])
def test_article_paragraph_item_subitem(text, key):
    assert one(text).provision.key() == key


def test_dotted_item_form_after_a_paragraph_only():
    assert one("가상체류관리법 제5조② 1. 가상 신고서").provision.key() == "제5조제2항제1호"
    assert one("가상체류관리법 제5조 1. 가상").provision.key() == "제5조"


def test_a_date_after_a_paragraph_is_not_an_item():
    assert one("가상체류관리법 제5조① 2026. 9. 15.").provision.key() == "제5조제1항"


@pytest.mark.parametrize("text, key", [
    ("가상체류관리법 시행규칙 별표 1", "별표1"),
    ("가상체류관리법 시행규칙 별표 5의2", "별표5의2"),
    ("가상체류관리법 시행규칙 별지 제34호서식", "별지제34호서식"),
    ("가상체류관리법 시행규칙 별지 제34호의2서식", "별지제34호의2서식"),
    ("가상체류관리법 부칙", "부칙"),
    ("가상체류관리법 부칙 제2조", "부칙제2조"),
    ("가상체류관리법 부칙 <가상법률 제1003호, 2026. 8. 4.> 제2조", "부칙제2조"),
])
def test_annex_form_and_addendum(text, key):
    citation = one(text)
    assert citation.provision.key() == key
    assert citation.law_title_as_written in ("가상체류관리법", "가상체류관리법 시행규칙")


def test_bracketed_annex_keeps_its_brackets_in_raw():
    citation = one("가상체류관리법 시행규칙 [별표 1]")
    assert citation.raw == "가상체류관리법 시행규칙 [별표 1]"
    assert citation.law_title_as_written == "가상체류관리법 시행규칙"


def test_title_is_the_longest_known_match():
    assert one("가상체류관리법 시행규칙 제73조").law_title_as_written == "가상체류관리법 시행규칙"
    assert one("가상체류관리법 시행령 제3조").law_title_as_written == "가상체류관리법 시행령"
    assert one("가상체류관리법 제3조").law_title_as_written == "가상체류관리법"


def test_former_and_short_titles_are_known_titles():
    assert one("가상외국인체류법 제5조").law_title_as_written == "가상외국인체류법"
    assert one("가상체류법 제5조").law_title_as_written == "가상체류법"


def test_unknown_title_is_none_never_a_substitute():
    citation = one("신가상체류관리법 제3조")
    assert citation.law_title_as_written is None
    assert citation.raw == "제3조"
    # no generic "anything ending in 법" rule
    assert one("가상무역법 제3조").law_title_as_written is None


def test_unknown_title_inside_brackets_is_taken_as_written():
    assert one("「가상무역법」 제3조").law_title_as_written == "가상무역법"


def test_title_spacing_and_interpuncts_do_not_matter():
    assert one("가상체류관리법시행규칙 제73조").law_title_as_written == "가상체류관리법시행규칙"


@pytest.mark.parametrize("text, title", [
    ("법 제5조", "가상체류관리법"),
    ("이 법 제5조", "가상체류관리법"),
    ("영 제3조", "가상체류관리법 시행령"),
    ("규칙 제73조", "가상체류관리법 시행규칙"),
])
def test_short_forms_resolve_relative_to_the_context(text, title):
    assert one(text, context_title="가상체류관리법").law_title_as_written == title


def test_short_forms_from_a_decree_context_resolve_to_its_act():
    assert one("법 제5조", context_title="가상체류관리법 시행령").law_title_as_written == "가상체류관리법"
    assert one("규칙 제73조", context_title="가상체류관리법 시행령").law_title_as_written == "가상체류관리법 시행규칙"


def test_short_form_without_context_is_none():
    citation = one("영 제3조")
    assert citation.law_title_as_written is None
    assert citation.raw == "영 제3조"


def test_same_act_and_same_decree_follow_the_last_cited_title():
    found = parse_citations("가상체류관리법 시행령 제3조, 같은 영 제4조 및 같은 법 제5조", known_titles=TITLES)
    assert [(c.law_title_as_written, c.provision.key()) for c in found] == [
        ("가상체류관리법 시행령", "제3조"), ("가상체류관리법 시행령", "제4조"), ("가상체류관리법", "제5조"),
    ]


def test_claimed_heading_in_parentheses():
    citation = one("가상체류관리법 시행규칙 제73조(수수료의 납부방법) ①")
    assert citation.claimed_heading == "수수료의 납부방법"
    assert citation.provision.key() == "제73조제1항"


@pytest.mark.parametrize("suffix", ["(개정 2020. 1. 1.)", "(제2항)", "(법률 제123호)", "(이하 \"신고\"라 한다)"])
def test_parenthesized_notes_are_not_headings(suffix):
    assert one(f"가상체류관리법 제5조{suffix}").claimed_heading is None


def test_spans_index_the_text():
    text = "근거는 가상체류관리법 제5조제1항이고, 「가상무역법」 제3조도 본다."
    for citation in parse_citations(text, known_titles=TITLES):
        start, end = citation.span
        assert text[start:end] == citation.raw


def test_connectors_carry_the_title_but_prose_does_not():
    found = parse_citations("가상체류관리법 제5조 및 제7조", known_titles=TITLES)
    assert [c.law_title_as_written for c in found] == ["가상체류관리법", "가상체류관리법"]
    found = parse_citations("가상체류관리법 제5조에 따른 신고는 제7조와 다르다", known_titles=TITLES)
    assert [c.law_title_as_written for c in found] == ["가상체류관리법", None]


def test_bare_paragraph_after_a_connector_continues_the_article():
    found = parse_citations("가상체류관리법 제5조제1항 및 제2항", known_titles=TITLES)
    assert [c.provision.key() for c in found] == ["제5조제1항", "제5조제2항"]
    found = parse_citations("가상체류관리법 제5조제2항제1호 및 제2호", known_titles=TITLES)
    assert [c.provision.key() for c in found] == ["제5조제2항제1호", "제5조제2항제2호"]


def test_same_article_reference():
    found = parse_citations("가상체류관리법 제5조제1항, 같은 조 제2항", known_titles=TITLES)
    assert [c.provision.key() for c in found] == ["제5조제1항", "제5조제2항"]
    assert found[1].law_title_as_written == "가상체류관리법"


@pytest.mark.parametrize("text", ["서류를 제출한다", "제3자가 신청한다", "가상법률 제123호로 공포", "별표 없음"])
def test_words_that_look_like_references_are_not(text):
    assert parse_citations(text, known_titles=TITLES) == []


def test_decomposed_hangul_is_normalized():
    citation = one(unicodedata.normalize("NFD", "가상체류관리법 제5조"))
    assert citation.law_title_as_written == "가상체류관리법"


def test_standalone_string_takes_its_leading_text_as_the_title():
    [citation] = parse_citation_string("가상체류관리볍 제3조")
    assert citation.law_title_as_written == "가상체류관리볍"
    [title_only] = parse_citation_string("가상체류관리법")
    assert title_only.law_title_as_written == "가상체류관리법"
    assert title_only.provision.is_empty()
    assert parse_citation_string("") == []


def test_standalone_strings_share_one_title_context():
    found = parse_citation_strings(["가상체류관리법 제5조", "같은 법 시행령 제3조", "같은 법 제7조"])
    assert [(c.law_title_as_written, c.provision.key()) for c in found] == [
        ("가상체류관리법", "제5조"), ("가상체류관리법 시행령", "제3조"), ("가상체류관리법", "제7조"),
    ]


def test_bare_article_in_a_standalone_string_has_no_title():
    [citation] = parse_citation_string("제10조")
    assert citation.law_title_as_written is None


@pytest.mark.parametrize("key, provision, article", [
    ("제73조", "제73조", "제73조"),
    ("제4조제4항", "제4조제4항", "제4조"),
    ("제4조 제4항", "제4조제4항", "제4조"),
    ("별표 1", "별표1", "별표1"),
    ("부칙제1조", "부칙제1조", "부칙제1조"),
])
def test_provision_keys_round_trip(key, provision, article):
    assert provision_ref_from_key(key).key() == provision
    assert article_key_of(key) == article


def test_unreadable_key_is_kept_without_spaces():
    assert provision_ref_from_key("가상 키") is None
    assert article_key_of("가상 키") == "가상키"


@pytest.mark.parametrize("text", ["가상부칙장애법 제2조", "「가상부칙장애법」 제2조"])
def test_a_keyword_inside_a_title_is_not_a_reference(text):
    found = parse_citations(text, known_titles=TITLES + ("가상부칙장애법",))
    assert [(c.law_title_as_written, c.provision.key()) for c in found] == [("가상부칙장애법", "제2조")]
    [standalone] = parse_citation_string("가상부칙장애법 제2조")
    assert (standalone.law_title_as_written, standalone.provision.key()) == ("가상부칙장애법", "제2조")


@pytest.mark.parametrize("text", ["경제5조원 규모", "경제 5조 원 규모", "특별표시 1개", "개별지 제3호"])
def test_a_reference_inside_a_word_is_not_a_reference(text):
    assert parse_citations(text, known_titles=TITLES) == []


def test_an_article_written_straight_after_a_title_is_still_read():
    citation = one("가상체류관리법제5조제1항")
    assert (citation.law_title_as_written, citation.provision.key()) == ("가상체류관리법", "제5조제1항")
    assert one("가상체류관리법 시행규칙제73조").law_title_as_written == "가상체류관리법 시행규칙"


def test_bracketed_annex_without_a_title_keeps_both_brackets():
    [citation] = parse_citations("[별표 1]에 따른 서류", known_titles=TITLES)
    assert citation.raw == "[별표 1]" and citation.law_title_as_written is None


def test_dongbeop_is_the_older_spelling_of_the_same_act():
    found = parse_citations("가상체류관리법 제5조 및 동법 시행령 제3조, 동법 제7조", known_titles=TITLES)
    assert [(c.law_title_as_written, c.provision.key()) for c in found] == [
        ("가상체류관리법", "제5조"), ("가상체류관리법 시행령", "제3조"), ("가상체류관리법", "제7조"),
    ]
    assert one("가상노동법 제5조").law_title_as_written is None   # 동법 inside a word is not the short form


def test_standalone_strings_use_known_titles_but_never_shorten_an_unknown_one():
    [led] = parse_citation_string("근거: 가상체류관리법 제5조", known_titles=TITLES)
    assert led.law_title_as_written == "가상체류관리법"
    [longer] = parse_citation_string("신가상체류관리법 제5조", known_titles=TITLES)
    assert longer.law_title_as_written == "신가상체류관리법"
