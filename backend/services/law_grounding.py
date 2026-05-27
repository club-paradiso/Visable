from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

from .citation_verifier import verify_citations
from .grounding_config import load_grounding_config
from .korean_law_client import KoreanLawClient


_INTENT_PATTERNS = [
    # Explicit legal-basis wording.
    ("근거 법령", re.compile(r"근거\s*법령", re.IGNORECASE)),
    ("법적 근거", re.compile(r"법적\s*근거", re.IGNORECASE)),
    ("출입국관리법", re.compile(r"출입국관리법", re.IGNORECASE)),
    ("시행령", re.compile(r"시행령", re.IGNORECASE)),
    ("시행규칙", re.compile(r"시행규칙", re.IGNORECASE)),
    ("제n조", re.compile(r"제\s*\d+\s*조", re.IGNORECASE)),
    ("according to korean law", re.compile(r"according\s+to\s+korean\s+law", re.IGNORECASE)),
    ("legal basis", re.compile(r"legal\s+basis", re.IGNORECASE)),
    ("article", re.compile(r"\barticle\b", re.IGNORECASE)),
    ("immigration act", re.compile(r"immigration\s+act", re.IGNORECASE)),

    # Stay-risk / travel / re-entry wording. These do not prove an answer;
    # they only justify attempting official law grounding before responding.
    ("출국/해외여행", re.compile(r"출국|해외\s*여행|해외여행|일본|재입국|출입국", re.IGNORECASE)),
    ("travel/re-entry", re.compile(r"\b(re-entry|reentry|leave Korea|travel abroad|Japan|depart(?:ure)?|return to Korea)\b", re.IGNORECASE)),
    ("외국인등록", re.compile(r"외국인\s*등록|외국인등록증|등록증|alien registration|foreigner registration|\bARC\b", re.IGNORECASE)),
    ("체류위험", re.compile(r"체류기간|체류자격|불법체류|초과체류|체류\s*만료|취소|overstay|stay period|status", re.IGNORECASE)),
    ("G-1", re.compile(r"\bG\s*-?\s*1(?:\s*-?\s*5)?\b|G-1-5|난민|인도적\s*체류|humanitarian stay|refugee", re.IGNORECASE)),
]

_LEGAL_BASIS_REASON_LABELS = {
    "근거 법령",
    "법적 근거",
    "출입국관리법",
    "시행령",
    "시행규칙",
    "제n조",
    "according to korean law",
    "legal basis",
    "article",
    "immigration act",
}

_STAY_RISK_REASON_LABELS = {
    "출국/해외여행",
    "travel/re-entry",
    "외국인등록",
    "체류위험",
    "G-1",
}


def _dedupe(items: Sequence[str]) -> List[str]:
    seen: List[str] = []
    for item in items:
        clean = (item or "").strip()
        if clean and clean not in seen:
            seen.append(clean)
    return seen


def should_attempt_law_grounding(question: str) -> Dict[str, Any]:
    text = (question or "").strip()
    if not text:
        return {"should_attempt": False, "reasons": []}

    reasons: List[str] = [label for label, pattern in _INTENT_PATTERNS if pattern.search(text)]
    return {"should_attempt": bool(reasons), "reasons": reasons}


def build_law_search_query(question: str, reasons: Sequence[str] | None = None) -> str:
    """Build a compact Korean law-search query from a user question.

    Public/legal-data APIs tend to search better with statutory terms than
    conversational phrasing like "일본 갈 수 있나요". This helper preserves the
    user question while adding conservative immigration-law anchors.
    """
    text = (question or "").strip()
    reason_set = set(reasons or [])
    queries: List[str] = []

    if reason_set & _STAY_RISK_REASON_LABELS:
        queries.append("출입국관리법 체류자격 체류기간 외국인")

    if {"출국/해외여행", "travel/re-entry"} & reason_set:
        queries.append("출입국관리법 출국 재입국 재입국허가 체류자격")

    if "외국인등록" in reason_set:
        queries.append("출입국관리법 외국인등록 외국인등록증 체류자격")

    if "G-1" in reason_set:
        queries.append("출입국관리법 시행령 G-1 기타 난민 인도적 체류")
        queries.append("출입국관리법 재입국허가 체류자격 G-1")

    if reason_set & _LEGAL_BASIS_REASON_LABELS:
        queries.append(text)

    if not queries:
        queries.append(text)

    # Keep the outgoing query compact. The client currently accepts one query
    # string, so join the best anchors rather than issuing multiple requests.
    return " ".join(_dedupe(queries))[:500]


def build_law_grounding_context(question: str) -> Dict[str, Any]:
    intent = should_attempt_law_grounding(question)
    if not intent["should_attempt"]:
        return {
            "attempted": False,
            "intent_reasons": [],
            "law_search_query": "",
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": {"status": "extracted_only", "citations": [], "warnings": []},
            "grounding_sources": [],
            "grounding_warnings": [],
        }

    law_search_query = build_law_search_query(question, intent["reasons"])
    config = load_grounding_config()
    if config.mode == "disabled":
        return {
            "attempted": False,
            "intent_reasons": intent["reasons"],
            "law_search_query": law_search_query,
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": {"status": "extracted_only", "citations": [], "warnings": []},
            "grounding_sources": [],
            "grounding_warnings": ["LAW_GROUNDING_DISABLED", *config.warnings],
        }

    try:
        law_client = KoreanLawClient(config)
        law_result = law_client.search_law(law_search_query)
        citation_verification = verify_citations(question, law_client=law_client)
    except Exception:
        return {
            "attempted": True,
            "intent_reasons": intent["reasons"],
            "law_search_query": law_search_query,
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": {"status": "error", "citations": [], "warnings": ["SOURCE_UNAVAILABLE"]},
            "grounding_sources": [],
            "grounding_warnings": ["SOURCE_UNAVAILABLE"],
        }

    warnings = [*law_result.get("warnings", []), *citation_verification.get("warnings", []), *config.warnings]
    return {
        "attempted": True,
        "intent_reasons": intent["reasons"],
        "law_search_query": law_search_query,
        "law_grounding_used": law_result.get("status") == "ok",
        "law_grounding": law_result.get("results", []),
        "citation_verification": citation_verification,
        "grounding_sources": [{"source_type": "law", "status": law_result.get("status"), "query": law_search_query}],
        "grounding_warnings": list(dict.fromkeys(warnings)),
    }
