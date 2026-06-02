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

    # Activity-scope / status-permission wording. A status holder asking
    # whether a specific activity (a course, part-time work, a class) is
    # allowed is really asking about 활동범위 / 체류자격외활동 — squarely a
    # law/manual question — so attempt official grounding before answering.
    ("활동범위/자격외활동", re.compile(r"활동\s*범위|체류자격\s*외\s*활동|자격\s*외\s*활동|체류자격외활동|자격외활동|activit(?:y|ies)\s+outside|out-?of-?status\s+activit|activity\s+scope|scope\s+of\s+(?:activity|stay|status)", re.IGNORECASE)),

    # Study / course-taking wording (유학, 수강, 수업, 계절학기, study, course, class, ...).
    ("유학/수강/계절학기", re.compile(r"계절\s*학기|학기\s*수강|수강|청강|수업|강의|강좌|유학|휴학|복학|university\s+(?:class|course)|\bcours(?:e|es)\b|\bclass(?:es)?\b|\blectures?\b|seasonal\s+(?:semester|term|session)|summer\s+session|winter\s+session|enroll(?:ment|ed)?|\bstud(?:y|ies|ying)\b", re.IGNORECASE)),

    # Tourism-working-holiday (관광취업 / 워킹홀리데이 / H-1) context.
    ("관광취업/워킹홀리데이/H-1", re.compile(r"관광\s*취업|워킹\s*홀리데이|워홀|working\s+holiday|\bH\s*-?\s*1\b", re.IGNORECASE)),
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

# Activity-scope / study / tourism-working-holiday intent. These ask whether
# a status permits a specific activity (a course, a class, part-time work),
# i.e. 활동범위 / 체류자격외활동 questions.
_ACTIVITY_SCOPE_REASON_LABELS = {
    "활동범위/자격외활동",
    "유학/수강/계절학기",
    "관광취업/워킹홀리데이/H-1",
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

    if "활동범위/자격외활동" in reason_set:
        queries.append("출입국관리법 체류자격외활동 활동범위 체류자격")

    if "유학/수강/계절학기" in reason_set:
        queries.append("출입국관리법 시행령 유학 수강 계절학기 체류자격 활동범위")

    if "관광취업/워킹홀리데이/H-1" in reason_set:
        queries.append("출입국관리법 시행령 관광취업 H-1 체류자격 활동범위 체류자격외활동")

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


_DEFAULT_PREFLIGHT_SAMPLE = "H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?"


def law_grounding_preflight(sample_question: str = "") -> Dict[str, Any]:
    """Non-secret readiness report for law grounding.

    Safe to call in any mode: it performs NO external call and NEVER returns
    API keys or raw API bodies — only booleans, the resolved mode, the intent
    decision for a sample question, and the statutory query that would be
    issued. Designed for operators/CI to confirm deployed configuration and
    for the debug endpoint, without exposing secrets or crashing.
    """
    config = load_grounding_config()
    sample = (sample_question or "").strip() or _DEFAULT_PREFLIGHT_SAMPLE
    intent = should_attempt_law_grounding(sample)
    reasons = intent.get("reasons", [])
    query = build_law_search_query(sample, reasons) if intent.get("should_attempt") else ""

    key_configured = bool(config.law_api_key)
    endpoint_configured = bool(config.law_api_base_url and config.law_api_search_path)

    if config.mode == "disabled":
        external_calls = "disabled"
    elif config.mode == "audit":
        external_calls = "audit_only"
    else:
        external_calls = "enabled"

    warnings: List[str] = []
    if config.mode == "disabled":
        warnings.append("LAW_GROUNDING_DISABLED")
    elif config.mode == "audit":
        warnings.append("LAW_GROUNDING_AUDIT_ONLY")
    if config.mode in {"audit", "enabled"}:
        if not key_configured:
            warnings.append("LAW_API_KEY_MISSING")
        if not endpoint_configured:
            warnings.append("LAW_API_ENDPOINT_MISSING")
    warnings.extend(config.warnings)

    # Whether a real external law-API call could actually happen.
    ready_for_external_calls = (
        config.mode in {"audit", "enabled"} and key_configured and endpoint_configured
    )

    return {
        "mode": config.mode,
        "external_calls": external_calls,
        "law_api_key_configured": key_configured,
        "law_api_endpoint_configured": endpoint_configured,
        "ready_for_external_calls": ready_for_external_calls,
        "sample_question": sample,
        "sample_would_trigger": bool(intent.get("should_attempt")),
        "sample_intent_reasons": reasons,
        "sample_law_search_query": query,
        "warnings": list(dict.fromkeys(warnings)),
    }

