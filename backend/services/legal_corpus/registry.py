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
