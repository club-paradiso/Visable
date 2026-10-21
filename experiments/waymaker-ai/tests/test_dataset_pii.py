"""The personal-data screen (waymaker_ai.dataset.pii).

Every positive case below is a made-up value in a well-known shape. None of
them belongs to a person.
"""
from __future__ import annotations

import pytest

from waymaker_ai.dataset import pii


def _kinds(text: str):
    return [finding.kind for finding in pii.scan_text(text)]


@pytest.mark.parametrize(
    "text, kind",
    [
        ("외국인등록번호 900101-5234567 입니다", pii.ALIEN_REGISTRATION_NUMBER),
        ("등록번호는 900101 - 6234567", pii.ALIEN_REGISTRATION_NUMBER),
        ("주민번호 9001011234567", pii.RESIDENT_REGISTRATION_NUMBER),
        ("RRN900101-1234567", pii.RESIDENT_REGISTRATION_NUMBER),
        ("full width ９００１０１－７２３４５６７", pii.ALIEN_REGISTRATION_NUMBER),
        ("space separated 900101 5234567", pii.ALIEN_REGISTRATION_NUMBER),
        ("a dash always counts: 123456-1234567", pii.RESIDENT_REGISTRATION_NUMBER),
        ("en dash 900101–8234567", pii.ALIEN_REGISTRATION_NUMBER),
    ],
)
def test_registration_number_shapes_are_flagged(text, kind):
    assert _kinds(text) == [kind]


@pytest.mark.parametrize(
    "text",
    [
        "version_id 2100000275060",                                                # 행정규칙일련번호: month 00
        "https://www.law.go.kr/LSW/admRulLsInfoP.do?admRulSeq=2100000275060",
        "289833 2026091",                                                          # not a birth date, no dash
        "1234567890123",                                                           # month 34
        "900101-52345678",                                                         # 8 digits after the dash
    ],
)
def test_thirteen_digit_ids_that_are_not_registration_numbers(text):
    assert _kinds(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "여권번호 M12345678 로 신청했어요",
        "passport no. M123A4567",
        "My PASSPORT: AB1234567",
        "여권 123456789",
    ],
)
def test_passport_numbers_in_passport_context(text):
    assert _kinds(text) == [pii.PASSPORT_NUMBER]


def test_passport_like_token_without_passport_context_is_not_flagged():
    assert _kinds("주문번호 M12345678") == []


@pytest.mark.parametrize("text", ["010-1234-5678", "연락처 01012345678", "+82 10 1234 5678", "011.123.4567"])
def test_korean_mobile_numbers(text):
    assert _kinds(text) == [pii.MOBILE_NUMBER]


def test_email_addresses():
    assert _kinds("contact: someone.name+tag@example.co.kr") == [pii.EMAIL_ADDRESS]
    assert _kinds("full width ｓｏｍｅｏｎｅ＠ｅｘａｍｐｌｅ．ｃｏｍ") == [pii.EMAIL_ADDRESS]


@pytest.mark.parametrize(
    "text",
    [
        "0c5bc2d195a750ba01bc1a287f0c65915437a146e402202c9bad3a12ca574216",  # sha256
        "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=289833&efYd=20261002",
        "출입국관리법 001707 version 290729, 2026-10-19 시행",
        "E-7-4, D-10-T, F-2-7S, G-1-5",
        "법무부령 제1125호, 대통령령 제36728호",
        "여권 만료일 2027-01-31, 여권 발급일 20250131",
        "수수료 60,000원, 14일 이내",
        "02-2110-4000",  # a landline is out of scope
    ],
)
def test_legal_and_dataset_strings_are_not_flagged(text):
    assert _kinds(text) == []


def test_scan_value_walks_keys_and_nested_values():
    value = {"facts": {"note": ["ok", "mail me at a.b@example.com"]}, "900101-5234567": 1}
    paths = [path for path, _ in pii.scan_value(value)]
    assert "facts.note[1]" in paths
    assert "900101-5234567(key)" in paths


def test_description_never_contains_the_value():
    finding = pii.scan_text("문의 010-1234-5678")[0]
    described = pii.describe(finding)
    assert "1234" not in described and "withheld" in described


def test_redact_replaces_every_finding_and_leaves_clean_text_alone():
    assert pii.redact("version 2100000275060 of 2026-10-19") == "version 2100000275060 of 2026-10-19"
    assert pii.redact("call 010-1234-5678 or mail a.b@example.com") == "call <withheld> or mail <withheld>"
    assert pii.redact("id ９００１０１－５２３４５６７") == "id <withheld>"   # full-width digits are normalized first


def test_redact_replaces_each_separate_finding():
    redacted = pii.redact("여권 M12345678 / 900101-5234567")
    assert "12345678" not in redacted and "5234567" not in redacted
    assert redacted.count(pii.REDACTED) == 2


def test_overlapping_spans_merge_into_one_placeholder():
    findings = [pii.PiiFinding(pii.PASSPORT_NUMBER, 3, 12), pii.PiiFinding(pii.MOBILE_NUMBER, 8, 20), pii.PiiFinding(pii.EMAIL_ADDRESS, 25, 30)]
    assert pii._merged_spans(findings) == [(3, 20), (25, 30)]
