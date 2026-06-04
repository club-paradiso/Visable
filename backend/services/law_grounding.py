from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

from .citation_verifier import build_law_evidence_citation_verification, verify_citations
from .grounding_config import load_grounding_config


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
    ("외국인등록", re.compile(r"외국인\s*등록|외국인등록증|등록증|거소\s*신고|국내거소신고|거소신고|alien registration|foreigner registration|domestic residence report|residence report|\bARC\b", re.IGNORECASE)),
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

    # Status-change framing (체류자격 변경 / "A에서 B로" / "B로 변경"). A change of
    # sojourn status is squarely a law/manual question, so attempt grounding.
    ("체류자격 변경/status change", re.compile(
        r"체류자격\s*변경|변경허가|change\s+of\s+status|status\s+change|"
        r"[A-Za-z]\s*-?\s*\d{1,2}\s*[가-힣A-Za-z ]{0,10}?(?:에서|으로|로|to|->|→)\s*"
        r"[가-힣A-Za-z ]{0,10}?(?:[A-Za-z]\s*-?\s*\d{1,2}|변경|바꾸|전환)",
        re.IGNORECASE)),

    # Family / marriage-migrant exceptions (이혼/사망/가정폭력/배우자/결혼이민).
    ("결혼/가족 체류", re.compile(
        r"결혼이민|배우자|이혼|가정폭력|별거|사별|혼인|divorce|domestic\s+violence|"
        r"spouse|marriage\s+migrant", re.IGNORECASE)),

    # Humanitarian / medical / litigation / refugee context (G-1 etc.).
    ("인도적/의료/소송", re.compile(
        r"인도적|치료|소송|난민|humanitarian|medical\s+treatment|litigation|asylum|refugee",
        re.IGNORECASE)),

    # Short-term status limits (사증면제/무비자/단기취업/단기방문).
    ("단기체류/사증면제", re.compile(
        r"사증면제|무비자|단기\s*취업|단기\s*방문|단기\s*알바|visa[-\s]?free|short[-\s]?term",
        re.IGNORECASE)),

    # Nationality / naturalization (국적/귀화).
    ("국적/귀화", re.compile(r"귀화|국적상실|국적\s*취득|국적법|naturaliz|nationality|citizenship", re.IGNORECASE)),

    # Reporting / registration duties not already covered above
    # (근무처 변경/추가, 체류지 변경, 신고의무).
    ("신고/등록 의무", re.compile(r"근무처\s*변경|근무처\s*추가|체류지\s*변경|신고의무|시간제\s*취업", re.IGNORECASE)),

    # Employment / work-activity questions (취업/아르바이트/part-time/internship).
    ("취업/근로 활동", re.compile(
        r"시간제\s*취업|아르바이트|알바|부업|side\s+job|part[-\s]?time|intern(?:ship)?|"
        r"취업활동|취업|근로|freelance|프리랜서|moonlight", re.IGNORECASE)),

    # Penalty / violation exposure (벌금/과태료/범칙금/도과/강제퇴거).
    ("위반/처벌", re.compile(r"벌금|과태료|범칙금|체류기간\s*도과|도과|강제퇴거|출국명령", re.IGNORECASE)),
]

# A status code paired with an activity/permission marker ("can I ...", "가능한가요")
# is an activity-scope question even without explicit statutory wording, so it
# should attempt official grounding. Lookarounds handle trailing Korean particles.
_STATUS_CODE_INTENT_RE = re.compile(r"(?<![A-Za-z0-9])[A-H]\s*-?\s*\d{1,2}(?![0-9])", re.IGNORECASE)
_ACTIVITY_MARKER_RE = re.compile(
    r"가능|되나요|할\s*수\s*있|해도\s*되|can\s+i|may\s+i|am\s+i\s+allowed|able\s+to",
    re.IGNORECASE,
)

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
    # Status-scoped activity/permission question (e.g. "Can I ... on D-4?",
    # "C-3로 ... 가능한가요?") — attempt grounding even without statutory wording.
    if _STATUS_CODE_INTENT_RE.search(text) and _ACTIVITY_MARKER_RE.search(text):
        if "체류자격 활동 질문" not in reasons:
            reasons.append("체류자격 활동 질문")
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
        queries.append("출입국관리법 외국인등록 외국인등록증 국내거소신고 체류자격")

    if "G-1" in reason_set:
        queries.append("출입국관리법 시행령 G-1 기타 난민 인도적 체류")
        queries.append("출입국관리법 재입국허가 체류자격 G-1")

    if "활동범위/자격외활동" in reason_set:
        queries.append("출입국관리법 체류자격외활동 활동범위 체류자격")

    if "유학/수강/계절학기" in reason_set:
        queries.append("출입국관리법 시행령 유학 수강 계절학기 체류자격 활동범위")

    if "관광취업/워킹홀리데이/H-1" in reason_set:
        queries.append("출입국관리법 시행령 관광취업 H-1 체류자격 활동범위 체류자격외활동")

    if "체류자격 변경/status change" in reason_set:
        queries.append("출입국관리법 체류자격 변경허가 체류자격 변경")

    if "결혼/가족 체류" in reason_set:
        queries.append("출입국관리법 결혼이민 체류기간 연장 체류자격 변경 체류자격 유지")

    if "인도적/의료/소송" in reason_set:
        queries.append("출입국관리법 시행령 기타 G-1 인도적 사유 난민 체류")

    if "단기체류/사증면제" in reason_set:
        queries.append("출입국관리법 사증면제 단기방문 단기취업 활동범위")

    if "국적/귀화" in reason_set:
        queries.append("국적법 귀화 요건 절차 국적상실")

    if "신고/등록 의무" in reason_set:
        queries.append("출입국관리법 외국인등록 체류지 변경 근무처 변경 신고의무")

    if {"취업/근로 활동", "체류자격 활동 질문"} & reason_set:
        queries.append("출입국관리법 체류자격외활동 활동범위 취업활동 체류자격")

    if "위반/처벌" in reason_set:
        queries.append("출입국관리법 체류기간 도과 범칙금 과태료 강제퇴거 출국명령")

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
        # Lazy import breaks the module-load cycle (law_tools imports this
        # module for intent detection). The tool layer is the real Open Law
        # API adapter (DRF endpoints + OC); it never exposes the OC value.
        from . import law_tools

        law_result = law_tools.search_laws(law_search_query, config=config)
        if law_result.get("status") == "ok":
            citation_verification = build_law_evidence_citation_verification(
                law_result.get("results", []), query=law_search_query, law_api_attempted=True,
            )
        else:
            citation_verification = build_law_evidence_citation_verification(
                [], query=law_search_query,
                law_error_type=law_result.get("error_type", ""), law_api_attempted=True,
            )
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

    used = law_result.get("status") == "ok"
    tool_warnings: List[str] = []
    if not used:
        tool_warnings.append("SOURCE_UNAVAILABLE")
        error_type = law_result.get("error_type") or ""
        if error_type:
            # Typed, non-secret marker (e.g. LAW_API_NO_RESULTS). Never the OC.
            tool_warnings.append(error_type.upper())
    warnings = [*tool_warnings, *citation_verification.get("warnings", []), *config.warnings]
    return {
        "attempted": True,
        "intent_reasons": intent["reasons"],
        "law_search_query": law_search_query,
        "law_grounding_used": used,
        "law_grounding": law_result.get("results", []) if used else [],
        "citation_verification": citation_verification,
        "grounding_sources": [{"source_type": "law", "status": law_result.get("status"), "query": law_search_query, "error_type": law_result.get("error_type", ""), "parser_status": law_result.get("parser_status", ""), "response_shape_hint": law_result.get("response_shape_hint", ""), "source_url": law_result.get("source_url", "")}],
        "parser_status": law_result.get("parser_status", ""),
        "response_shape_hint": law_result.get("response_shape_hint", ""),
        "source_url": law_result.get("source_url", ""),
        "error_type": law_result.get("error_type", ""),
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

    # ``key_configured`` reflects whether ANY Open Law API credential is
    # present (the preferred LAW_API_OC, or the legacy LAW_API_KEY fallback).
    # Neither value is ever returned — only booleans and the non-secret source.
    key_configured = config.law_api_configured
    # A custom endpoint is "configured" only when explicitly set; the tool layer
    # otherwise falls back to the fixed public DRF endpoints, reported below.
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

    # The tool layer can call the fixed public DRF endpoints with just an OC,
    # so a real external call is possible once a credential is present.
    ready_for_external_calls = config.mode in {"audit", "enabled"} and key_configured

    return {
        "mode": config.mode,
        "external_calls": external_calls,
        # Backward-compatible aggregate flag (any credential present).
        "law_api_key_configured": key_configured,
        # Explicit, granular, non-secret flags (Part A).
        "law_api_configured": config.law_api_configured,
        "law_api_oc_configured": config.law_api_oc_configured,
        "law_api_key_fallback_configured": config.law_api_key_fallback_configured,
        "law_api_credential_source": config.law_api_credential_source,
        "law_api_endpoint_configured": endpoint_configured,
        "law_api_default_endpoint_available": True,
        "ready_for_external_calls": ready_for_external_calls,
        "sample_question": sample,
        "sample_would_trigger": bool(intent.get("should_attempt")),
        "sample_intent_reasons": reasons,
        "sample_law_search_query": query,
        "warnings": list(dict.fromkeys(warnings)),
    }

