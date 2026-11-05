"""Registry of laws covered by the Visable Legal Corpus.

Identifiers are the official National Law Information Center identifiers:

* ``law_id`` — the DRF Open API ``ID`` (법령ID), e.g. ``001707``.
* ``mst`` — the DRF Open API ``MST`` (법령일련번호 / lsiSeq) of one specific
  promulgation. A new MST is issued for every promulgation, so an MST
  identifies exactly one version of a law.

The ``known_versions`` entries were verified live against law.go.kr on
2026-11-04. The sync tool re-discovers the *current* MST from the official
site on every run and never assumes a registered MST is still current.
"""

from __future__ import annotations

from typing import Any, Dict, List

LAW_GO_KR = "https://www.law.go.kr"

# ---------------------------------------------------------------------------
# P0 laws
# ---------------------------------------------------------------------------

IMMIGRATION_ACT: Dict[str, Any] = {
    "slug": "immigration-act",
    "lawId": "001707",
    "titleKo": "출입국관리법",
    "titleEn": "IMMIGRATION ACT",
    "jurisdiction": "KR",
    "lawType": "ACT",
    "priority": "P0",
    # Verified live 2026-11-04 (newest first).
    "known_versions": [
        {"mst": "290729", "effectiveFrom": "2026-10-02"},
        {"mst": "272921", "effectiveFrom": "2026-01-23"},
    ],
    # Articles the enforcement calculator and citation features depend on.
    "priority_articles": ["18", "20", "21", "25", "46", "67", "68", "94", "95", "100"],
}

IMMIGRATION_DECREE: Dict[str, Any] = {
    "slug": "immigration-decree",
    "lawId": "005256",
    "titleKo": "출입국관리법 시행령",
    "titleEn": "ENFORCEMENT DECREE OF THE IMMIGRATION ACT",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_DECREE",
    "priority": "P0",
    "known_versions": [
        {"mst": "290501", "effectiveFrom": "2026-10-02"},
        {"mst": "271319", "effectiveFrom": "2025-06-01"},
    ],
    "priority_articles": ["23", "26", "26-2"],
}

IMMIGRATION_RULE: Dict[str, Any] = {
    "slug": "immigration-rule",
    "lawId": "008494",
    "titleKo": "출입국관리법 시행규칙",
    "titleEn": "ENFORCEMENT RULE OF THE IMMIGRATION ACT",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_RULE",
    "priority": "P0",
    "known_versions": [
        {"mst": "291289", "effectiveFrom": "2026-10-23"},
        {"mst": "283059", "effectiveFrom": "2026-01-23"},
    ],
    "priority_articles": ["86"],
}

P0_LAWS: List[Dict[str, Any]] = [IMMIGRATION_ACT, IMMIGRATION_DECREE, IMMIGRATION_RULE]

# ---------------------------------------------------------------------------
# P1 laws (added 2026-11-05, after the P0 corpus was completed and merged)
#
# Identifiers and current versions verified live against law.go.kr on
# 2026-11-05. Only the current version is registered initially; the sync
# tool re-discovers the current MST on every run. Older versions are added
# here only when an official English translation is anchored to them, so
# alignment pairs always join same-promulgation versions.
# ---------------------------------------------------------------------------

FOREIGNERS_TREATMENT_ACT: Dict[str, Any] = {
    "slug": "foreigners-treatment-framework-act",
    "lawId": "010445",
    "titleKo": "재한외국인 처우 기본법",
    "titleEn": "FRAMEWORK ACT ON TREATMENT OF FOREIGNERS RESIDING IN THE REPUBLIC OF KOREA",
    "jurisdiction": "KR",
    "lawType": "ACT",
    "priority": "P1",
    "known_versions": [
        {"mst": "268701", "effectiveFrom": "2025-01-31"},
    ],
    "priority_articles": ["10", "13", "14"],
}

REFUGEE_ACT: Dict[str, Any] = {
    "slug": "refugee-act",
    "lawId": "011546",
    "titleKo": "난민법",
    "titleEn": "REFUGEE ACT",
    "jurisdiction": "KR",
    "lawType": "ACT",
    "priority": "P1",
    "known_versions": [
        {"mst": "188376", "effectiveFrom": "2016-12-20"},
    ],
    "priority_articles": ["3", "5", "18", "21"],
}

REFUGEE_DECREE: Dict[str, Any] = {
    "slug": "refugee-decree",
    "lawId": "011878",
    "titleKo": "난민법 시행령",
    "titleEn": "ENFORCEMENT DECREE OF THE REFUGEE ACT",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_DECREE",
    "priority": "P1",
    "known_versions": [
        {"mst": "273705", "effectiveFrom": "2025-09-19"},
    ],
    "priority_articles": ["2", "18"],
}

REFUGEE_RULE: Dict[str, Any] = {
    "slug": "refugee-rule",
    "lawId": "011885",
    "titleKo": "난민법 시행규칙",
    "titleEn": "ENFORCEMENT RULE OF THE REFUGEE ACT",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_RULE",
    "priority": "P1",
    "known_versions": [
        {"mst": "266929", "effectiveFrom": "2024-12-03"},
    ],
    "priority_articles": ["2", "10"],
}

NATIONALITY_ACT: Dict[str, Any] = {
    "slug": "nationality-act",
    "lawId": "001435",
    "titleKo": "국적법",
    "titleEn": "NATIONALITY ACT",
    "jurisdiction": "KR",
    "lawType": "ACT",
    "priority": "P1",
    "known_versions": [
        {"mst": "244609", "effectiveFrom": "2022-10-01"},
    ],
    "priority_articles": ["5", "6", "7", "10"],
}

NATIONALITY_DECREE: Dict[str, Any] = {
    "slug": "nationality-decree",
    "lawId": "002922",
    "titleKo": "국적법 시행령",
    "titleEn": "ENFORCEMENT DECREE OF THE NATIONALITY ACT",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_DECREE",
    "priority": "P1",
    "known_versions": [
        {"mst": "246165", "effectiveFrom": "2022-12-20"},
    ],
    "priority_articles": ["3", "4"],
}

NATIONALITY_RULE: Dict[str, Any] = {
    "slug": "nationality-rule",
    "lawId": "006766",
    "titleKo": "국적법 시행규칙",
    "titleEn": "ENFORCEMENT RULE OF THE NATIONALITY ACT",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_RULE",
    "priority": "P1",
    "known_versions": [
        {"mst": "291055", "effectiveFrom": "2026-10-02"},
    ],
    "priority_articles": ["3", "4", "5"],
}

FOREIGN_WORKERS_ACT: Dict[str, Any] = {
    "slug": "foreign-workers-act",
    "lawId": "009542",
    "titleKo": "외국인근로자의 고용 등에 관한 법률",
    "titleEn": "ACT ON THE EMPLOYMENT OF FOREIGN WORKERS",
    "jurisdiction": "KR",
    "lawType": "ACT",
    "priority": "P1",
    "known_versions": [
        {"mst": "276857", "effectiveFrom": "2025-10-01"},
    ],
    "priority_articles": ["8", "18", "25"],
}

FOREIGN_WORKERS_DECREE: Dict[str, Any] = {
    "slug": "foreign-workers-decree",
    "lawId": "009657",
    "titleKo": "외국인근로자의 고용 등에 관한 법률 시행령",
    "titleEn": "ENFORCEMENT DECREE OF THE ACT ON THE EMPLOYMENT OF FOREIGN WORKERS",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_DECREE",
    "priority": "P1",
    "known_versions": [
        {"mst": "244037", "effectiveFrom": "2023-02-03"},
    ],
    "priority_articles": ["13-4", "14"],
}

FOREIGN_WORKERS_RULE: Dict[str, Any] = {
    "slug": "foreign-workers-rule",
    "lawId": "009698",
    "titleKo": "외국인근로자의 고용 등에 관한 법률 시행규칙",
    "titleEn": "ENFORCEMENT RULE OF THE ACT ON THE EMPLOYMENT OF FOREIGN WORKERS",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_RULE",
    "priority": "P1",
    "known_versions": [
        {"mst": "271599", "effectiveFrom": "2025-06-02"},
    ],
    "priority_articles": ["5", "9", "14"],
}

P1_LAWS: List[Dict[str, Any]] = [
    FOREIGNERS_TREATMENT_ACT,
    REFUGEE_ACT,
    REFUGEE_DECREE,
    REFUGEE_RULE,
    NATIONALITY_ACT,
    NATIONALITY_DECREE,
    NATIONALITY_RULE,
    FOREIGN_WORKERS_ACT,
    FOREIGN_WORKERS_DECREE,
    FOREIGN_WORKERS_RULE,
]

# ---------------------------------------------------------------------------
# P2 laws (added 2026-11-05 on the user's request, same pipeline)
#
# Identifiers and current versions verified live against law.go.kr on
# 2026-11-05. For both Enforcement Decrees the site's current pointer is a
# promulgated but not-yet-effective version (재외동포법 시행령: effective
# 2026-03-24; 다문화가족지원법 시행령: effective 2026-01-02), so the
# currently-in-force version is registered alongside it — otherwise the
# corpus would hold no decree text that applies today.
# ---------------------------------------------------------------------------

OVERSEAS_KOREANS_ACT: Dict[str, Any] = {
    "slug": "overseas-koreans-act",
    "lawId": "001999",
    "titleKo": "재외동포의 출입국과 법적 지위에 관한 법률",
    "titleEn": "ACT ON THE IMMIGRATION AND LEGAL STATUS OF OVERSEAS KOREANS",
    "jurisdiction": "KR",
    "lawType": "ACT",
    "priority": "P2",
    "known_versions": [
        {"mst": "268553", "effectiveFrom": "2025-07-22"},
    ],
    "priority_articles": ["5", "6", "10"],
}

OVERSEAS_KOREANS_DECREE: Dict[str, Any] = {
    "slug": "overseas-koreans-decree",
    "lawId": "004662",
    "titleKo": "재외동포의 출입국과 법적 지위에 관한 법률 시행령",
    "titleEn": "ENFORCEMENT DECREE OF THE ACT ON THE IMMIGRATION AND LEGAL STATUS OF OVERSEAS KOREANS",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_DECREE",
    "priority": "P2",
    "known_versions": [
        {"mst": "256767", "effectiveFrom": "2023-12-14"},
        {"mst": "284843", "effectiveFrom": "2026-03-24"},
    ],
    "priority_articles": ["4", "7"],
}

OVERSEAS_KOREANS_RULE: Dict[str, Any] = {
    "slug": "overseas-koreans-rule",
    "lawId": "008011",
    "titleKo": "재외동포의 출입국과 법적 지위에 관한 법률 시행규칙",
    "titleEn": "ENFORCEMENT RULE OF THE ACT ON THE IMMIGRATION AND LEGAL STATUS OF OVERSEAS KOREANS",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_RULE",
    "priority": "P2",
    "known_versions": [
        {"mst": "267499", "effectiveFrom": "2025-02-01"},
    ],
    "priority_articles": ["2", "3"],
}

MULTICULTURAL_FAMILIES_ACT: Dict[str, Any] = {
    "slug": "multicultural-families-act",
    "lawId": "010718",
    "titleKo": "다문화가족지원법",
    "titleEn": "MULTICULTURAL FAMILIES SUPPORT ACT",
    "jurisdiction": "KR",
    "lawType": "ACT",
    "priority": "P2",
    "known_versions": [
        {"mst": "281953", "effectiveFrom": "2025-12-30"},
    ],
    "priority_articles": ["6", "11-2", "12"],
}

MULTICULTURAL_FAMILIES_DECREE: Dict[str, Any] = {
    "slug": "multicultural-families-decree",
    "lawId": "010842",
    "titleKo": "다문화가족지원법 시행령",
    "titleEn": "ENFORCEMENT DECREE OF THE MULTICULTURAL FAMILIES SUPPORT ACT",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_DECREE",
    "priority": "P2",
    "known_versions": [
        {"mst": "277439", "effectiveFrom": "2025-10-01"},
        {"mst": "281629", "effectiveFrom": "2026-01-02"},
    ],
    "priority_articles": ["11", "12"],
}

MULTICULTURAL_FAMILIES_RULE: Dict[str, Any] = {
    "slug": "multicultural-families-rule",
    "lawId": "010840",
    "titleKo": "다문화가족지원법 시행규칙",
    "titleEn": "ENFORCEMENT RULE OF THE MULTICULTURAL FAMILIES SUPPORT ACT",
    "jurisdiction": "KR",
    "lawType": "ENFORCEMENT_RULE",
    "priority": "P2",
    "known_versions": [
        {"mst": "278829", "effectiveFrom": "2025-10-01"},
    ],
    "priority_articles": ["3", "5"],
}

P2_LAWS: List[Dict[str, Any]] = [
    OVERSEAS_KOREANS_ACT,
    OVERSEAS_KOREANS_DECREE,
    OVERSEAS_KOREANS_RULE,
    MULTICULTURAL_FAMILIES_ACT,
    MULTICULTURAL_FAMILIES_DECREE,
    MULTICULTURAL_FAMILIES_RULE,
]

ALL_LAWS: List[Dict[str, Any]] = P0_LAWS + P1_LAWS + P2_LAWS

# ---------------------------------------------------------------------------
# P0 administrative notice (행정규칙 / 법무부 고시)
# ---------------------------------------------------------------------------

MOJ_NOTICE_WORKPLACE_REPORT: Dict[str, Any] = {
    "slug": "moj-notice-2020-212-workplace-report-eligibility",
    "admRulSeq": "2100000190656",
    "titleKo": "출입국관리법시행령 제26조의2제1항에 따라 신고만으로 근무처 변경·추가를 할 수 있는 외국인의 요건",
    "noticeNo": "법무부고시 제2020-212호",
    "issuer": "법무부",
    "effectiveFrom": "2020-06-22",
    "priority": "P0",
    "related": ["immigration-act:21", "immigration-decree:26-2"],
}

P0_NOTICES: List[Dict[str, Any]] = [MOJ_NOTICE_WORKPLACE_REPORT]

# ---------------------------------------------------------------------------
# Annex 7 of the Enforcement Rule (범칙금의 양정기준, Rule Art. 86(1))
# ---------------------------------------------------------------------------

ANNEX7: Dict[str, Any] = {
    "slug": "immigration-rule-annex-7",
    "titleKo": "출입국관리법 시행규칙 별표 7 — 범칙금의 양정기준 (제86조제1항 관련)",
    "parentLawSlug": "immigration-rule",
    "annexNo": "7",
    # File sequences (flSeq) are version-specific; the sync tool re-reads
    # them from the parent Rule version page on every run. The values below
    # are the ones verified live on 2026-11-04 for Rule MST 291289 and are
    # only a fallback hint, never a source of truth.
    "fallback_fl_seq": {"pdf": "170813013", "hwp": "170813011"},
    "bylClsCd": "110201",
}
