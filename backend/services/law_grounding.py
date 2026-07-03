from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

from .citation_verifier import (
    build_law_evidence_citation_verification,
    extract_korean_legal_citations,
    verify_citations,
)
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
    ("KIIP", re.compile(r"사회통합프로그램|귀화\s*면접|기본소양|\bKIIP\b", re.IGNORECASE)),

    # Reporting / registration duties not already covered above
    # (근무처 변경/추가, 체류지 변경, 신고의무).
    ("신고/등록 의무", re.compile(r"근무처(?:를|을)?\s*변경|근무처(?:를|을)?\s*추가|체류지\s*변경|신고의무|시간제\s*취업", re.IGNORECASE)),

    # Workplace change / job transfer (근무처 변경·추가, 이직/전직/퇴사, 고용주 변경).
    # E-7 (특정활동) holders changing employers is the canonical case: a move to a
    # *different* company — even in the same industry — can trigger a 근무처
    # 변경허가 or 변경신고 duty, so attempt official grounding before answering.
    ("근무처변경/이직", re.compile(
        r"근무처(?:를|을)?\s*변경|근무처(?:를|을)?\s*추가|직장\s*변경|직장\s*이동|이직|전직|퇴사|퇴직|"
        r"동종\s*업계|동종업종|같은\s*업종|다른\s*회사|타\s*회사|타사|새\s*회사|새로운\s*회사|"
        r"회사를?\s*옮|회사\s*이동|고용주\s*변경|사업주\s*변경|특정활동|"
        r"change\s+(?:of\s+)?(?:employer|workplace|jobs?|companies)|switch(?:ing)?\s+(?:employer|company|companies|jobs?)|"
        r"new\s+(?:employer|company|workplace)|job\s+transfer|change\s+jobs|"
        r"move\s+to\s+(?:a\s+)?(?:another|new|different)\s+(?:company|employer)",
        re.IGNORECASE)),

    # Extension of stay (체류기간 연장 / 연장허가). A job transfer near the end of a
    # permit often raises an extension question too, so recognize it explicitly.
    ("체류기간연장/연장허가", re.compile(
        r"체류기간\s*연장|연장허가|기간\s*연장|연장\s*신청|체류\s*연장|"
        r"extension\s+of\s+stay|extend\s+(?:my\s+)?stay|stay\s+extension",
        re.IGNORECASE)),

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


_MAX_LAW_SEARCH_QUERIES = 6
_MAX_LAW_RESULTS = 12

_QUERY_ANCHORS_BY_REASON: Dict[str, Sequence[str]] = {
    "근무처변경/이직": (
        "출입국관리법 근무처 변경 추가 허가",
        "출입국관리법 근무처 변경 추가 신고",
        "출입국관리법 시행령 근무처 변경 추가",
        "특정활동 근무처 변경 추가 허가 신고",
        "체류기간 연장허가 근무처 변경",
    ),
    "체류기간연장/연장허가": ("출입국관리법 체류기간 연장허가",),
    "체류자격 변경/status change": ("출입국관리법 체류자격 변경허가",),
    "활동범위/자격외활동": ("출입국관리법 체류자격외활동 허가",),
    "취업/근로 활동": ("출입국관리법 체류자격외활동 취업 활동범위",),
    "신고/등록 의무": ("출입국관리법 외국인등록 체류지 변경 신고",),
    "외국인등록": ("출입국관리법 외국인등록 국내거소신고 체류자격",),
    "출국/해외여행": ("출입국관리법 재입국허가",),
    "travel/re-entry": ("출입국관리법 재입국허가",),
    "국적/귀화": ("국적법 귀화 국적회복 국적판정",),
    "KIIP": ("국적법 귀화 기본소양 사회통합프로그램",),
    "G-1": ("난민법 난민신청 인도적 체류", "출입국관리법 G-1 재입국"),
    "인도적/의료/소송": ("난민법 인도적 체류 난민신청",),
    "단기체류/사증면제": ("출입국관리법 사증면제 단기방문 단기취업 활동범위",),
    "관광취업/워킹홀리데이/H-1": ("출입국관리법 시행령 관광취업 활동범위 체류자격외활동",),
    "유학/수강/계절학기": ("출입국관리법 시행령 유학 수강 계절학기 시간제취업",),
    "결혼/가족 체류": ("출입국관리법 결혼이민 체류기간 연장허가",),
    "위반/처벌": ("출입국관리법 과태료 범칙금 강제퇴거 출국명령",),
    "체류위험": ("출입국관리법 체류자격 체류기간",),
}


def _status_codes(text: str) -> List[str]:
    return _dedupe(
        re.sub(r"\s+", "", match.group(0)).upper()
        for match in re.finditer(r"(?<![A-Za-z0-9])[A-H]\s*-\s*\d{1,2}(?:\s*-\s*[A-Za-z0-9]+)?", text or "", re.IGNORECASE)
    )


def build_law_search_queries(
    question: str,
    reasons: Sequence[str] | None = None,
    *,
    max_queries: int = _MAX_LAW_SEARCH_QUERIES,
) -> List[str]:
    """Plan bounded, discrete Open Law searches for a legal issue.

    Each returned string is one API call.  The planner is issue-based; status
    codes are optional context and never select a status-specific fixture.
    Conversational user text is intentionally excluded from the live plan so
    unrelated words cannot turn several useful searches into one overlong
    zero-result query.
    """
    text = (question or "").strip()
    reason_list = list(reasons or [])
    queries: List[str] = []
    extracted = extract_korean_legal_citations(text)
    for citation in extracted.get("citations", []):
        law_name = str(citation.get("law_name") or "").strip()
        if law_name:
            queries.append(law_name)

    # Open Law title search is materially more reliable than a single long
    # natural-language phrase for workplace-change questions.  Seed the three
    # controlling immigration instruments first; the issue-specific searches
    # below then narrow the context.  The cap still keeps the request bounded.
    if "근무처변경/이직" in reason_list:
        # Reserve one highly reliable title lookup without crowding out the
        # first query for every other detected issue (extension, reporting,
        # employment conditions, etc.).
        queries.append("출입국관리법")
    anchor_groups = [list(_QUERY_ANCHORS_BY_REASON.get(reason, ())) for reason in reason_list]
    anchor_groups = [group for group in anchor_groups if group]
    # Balance issue coverage before spending remaining calls on synonyms for a
    # single issue (notably workplace-change). This keeps extension/registration
    # anchors from being crowded out by five variants of the first issue.
    depth = 0
    while any(depth < len(group) for group in anchor_groups):
        for group in anchor_groups:
            if depth < len(group):
                queries.append(group[depth])
        depth += 1

    codes = _status_codes(text)
    if codes and any(r not in _LEGAL_BASIS_REASON_LABELS for r in reason_list):
        queries.append("출입국관리법 시행령 " + codes[0])

    if not queries:
        # Last-resort live query: keep only a short, whitespace-normalized
        # phrase. Explicit citations have already been reduced to law names.
        compact = " ".join(text.split())[:120]
        if compact:
            queries.append(compact)
    cap = max(1, min(int(max_queries or 1), _MAX_LAW_SEARCH_QUERIES))
    return _dedupe(queries)[:cap]


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
    """Backward-compatible diagnostic string; not used for live retrieval."""
    text = (question or "").strip()
    reason_set = set(reasons or [])
    queries = build_law_search_queries(text, reasons, max_queries=_MAX_LAW_SEARCH_QUERIES)
    for reason in reasons or []:
        queries.extend(_QUERY_ANCHORS_BY_REASON.get(reason, ()))
    # Historic diagnostics/tests expect the original explicit legal question to
    # be visible. Keep it here only; ``build_law_grounding_context`` executes the
    # discrete plan above and never sends this concatenation to law.go.kr.
    if text and reason_set & _LEGAL_BASIS_REASON_LABELS:
        queries = [*queries, text]
    return " ".join(_dedupe(queries))[:500]


def _law_result_key(item: Dict[str, Any]) -> tuple:
    return (
        str(item.get("source_type") or "law").strip().lower(),
        re.sub(r"\s+", "", str(item.get("law_name") or item.get("title") or "")).lower(),
        str(item.get("law_id") or "").strip(),
        str(item.get("law_serial_no") or item.get("reference") or "").strip(),
        str(item.get("article") or "").strip(),
    )


def _dedupe_law_results(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = _law_result_key(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out[:_MAX_LAW_RESULTS]


def _verify_requested_articles(
    question: str,
    law_results: Sequence[Dict[str, Any]],
    *,
    law_tools: Any,
    config: Any,
    detail_cache: Dict[tuple, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    extracted = extract_korean_legal_citations(question)
    requested = extracted.get("citations", [])
    if not requested:
        return build_law_evidence_citation_verification(
            list(law_results), law_api_attempted=True,
        )

    citations: List[Dict[str, Any]] = []
    article_evidence: List[Dict[str, Any]] = []
    cache = detail_cache if detail_cache is not None else {}
    cache_hits = 0
    for requested_item in requested[:3]:
        law_name = str(requested_item.get("law_name") or "").strip()
        article = str(requested_item.get("article") or "").strip()
        normalized_name = re.sub(r"\s+", "", law_name).lower()
        candidate = next((
            item for item in law_results
            if re.sub(r"\s+", "", str(item.get("law_name") or item.get("title") or "")).lower() == normalized_name
        ), None)
        citation: Dict[str, Any] = {
            "raw": requested_item.get("matched_text") or f"{law_name} {article}",
            "law_name": law_name,
            "article": article,
            "source_type": "law",
            "verification_status": "extracted_only",
            "warnings": [],
        }
        if not candidate:
            citation["verification_status"] = "failed_verification"
            citation["warnings"].append("CITED_LAW_NOT_FOUND")
            citations.append(citation)
            continue
        citation["source_url"] = candidate.get("source_url") or ""
        detail_key = (
            str(candidate.get("law_serial_no") or candidate.get("law_id") or ""),
            law_name,
            article,
        )
        if detail_key in cache:
            detail = cache[detail_key]
            cache_hits += 1
        else:
            detail = law_tools.get_law_detail(
                law_id=detail_key[0], law_name=law_name, article=article, config=config,
            )
            cache[detail_key] = detail
        if detail.get("status") != "ok":
            citation["verification_status"] = "failed_verification"
            citation["warnings"].append(str(detail.get("error_type") or "LAW_DETAIL_UNAVAILABLE").upper())
            citations.append(citation)
            continue
        detail_item = detail.get("detail") or {}
        detail_name = re.sub(r"\s+", "", str(detail_item.get("law_name") or detail_item.get("title") or "")).lower()
        articles = detail_item.get("articles") or []
        matched_article = next((
            item for item in articles
            if str(item.get("article_label") or item.get("article_no") or "").replace(" ", "") == article.replace(" ", "")
            and str(item.get("text") or "").strip()
        ), None)
        if detail_name != normalized_name or not matched_article:
            citation["verification_status"] = "source_linked_unverified"
            citation["warnings"].append("ARTICLE_TEXT_NOT_FOUND")
            citations.append(citation)
            continue
        snippet = " ".join(str(matched_article.get("text") or "").split())[:600]
        citation.update({
            "verification_status": "verified",
            "article_title": str(matched_article.get("article_title") or "")[:200],
            "snippet": snippet,
            "source_url": detail.get("source_url") or candidate.get("source_url") or "",
        })
        article_evidence.append({
            **candidate,
            "article": article,
            "summary": snippet,
            "query": law_name,
            "relevance": "direct",
            "article_verification_status": "verified",
        })
        citations.append(citation)

    statuses = {item.get("verification_status") for item in citations}
    if statuses == {"verified"}:
        overall = "verified"
    elif "failed_verification" in statuses:
        overall = "failed_verification"
    elif "source_linked_unverified" in statuses:
        overall = "source_linked_unverified"
    else:
        overall = "extracted_only"
    warnings = _dedupe([
        warning
        for item in citations
        for warning in (item.get("warnings") or [])
    ])
    return {
        "status": overall,
        "citation_specific": True,
        "citations": citations,
        "article_evidence": article_evidence,
        "request_cache_hits": cache_hits,
        "warnings": warnings,
    }


def build_law_grounding_context(question: str) -> Dict[str, Any]:
    intent = should_attempt_law_grounding(question)
    law_search_queries = build_law_search_queries(question, intent.get("reasons", []))
    law_search_query = build_law_search_query(question, intent.get("reasons", []))
    if not intent["should_attempt"]:
        return {
            "attempted": False,
            "intent_reasons": [],
            "law_search_query": "",
            "law_search_queries": [],
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": {"status": "extracted_only", "citations": [], "warnings": []},
            "grounding_sources": [],
            "grounding_warnings": [],
        }

    config = load_grounding_config()
    if config.mode == "disabled":
        return {
            "attempted": False,
            "intent_reasons": intent["reasons"],
            "law_search_query": law_search_query,
            "law_search_queries": law_search_queries,
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": extract_korean_legal_citations(question),
            "grounding_sources": [],
            "grounding_warnings": ["LAW_GROUNDING_DISABLED", *config.warnings],
        }

    try:
        # Lazy import breaks the module-load cycle (law_tools imports this
        # module for intent detection). The tool layer is the real Open Law
        # API adapter (DRF endpoints + OC); it never exposes the OC value.
        from . import law_tools

        outcomes: List[Dict[str, Any]] = []
        aggregate_results: List[Dict[str, Any]] = []
        search_cache: Dict[str, Dict[str, Any]] = {}
        request_cache_hits = 0
        for query in law_search_queries[:_MAX_LAW_SEARCH_QUERIES]:
            if query in search_cache:
                outcome = search_cache[query]
                request_cache_hits += 1
            else:
                outcome = law_tools.search_laws(query, config=config)
                search_cache[query] = outcome
            outcomes.append(outcome)
            if outcome.get("status") == "ok":
                for item in outcome.get("results", []):
                    if isinstance(item, dict):
                        aggregate_results.append({**item, "query": query})
        aggregate_results = _dedupe_law_results(aggregate_results)
        citation_verification = _verify_requested_articles(
            question,
            aggregate_results,
            law_tools=law_tools,
            config=config,
            detail_cache={},
        )
        request_cache_hits += int(citation_verification.get("request_cache_hits") or 0)
        aggregate_results = _dedupe_law_results([
            *(citation_verification.get("article_evidence") or []),
            *aggregate_results,
        ])
    except Exception:
        return {
            "attempted": True,
            "intent_reasons": intent["reasons"],
            "law_search_query": law_search_query,
            "law_search_queries": law_search_queries,
            "law_grounding_used": False,
            "law_grounding": [],
            "citation_verification": {"status": "error", "citations": [], "warnings": ["SOURCE_UNAVAILABLE"]},
            "grounding_sources": [],
            "grounding_warnings": ["SOURCE_UNAVAILABLE"],
        }

    used = bool(aggregate_results)
    tool_warnings: List[str] = []
    failed_outcomes = [outcome for outcome in outcomes if outcome.get("status") != "ok"]
    if failed_outcomes:
        if used:
            tool_warnings.append("LAW_API_PARTIAL_FAILURE")
        else:
            tool_warnings.append("SOURCE_UNAVAILABLE")
        for outcome in failed_outcomes:
            error_type = outcome.get("error_type") or ""
            if error_type:
                tool_warnings.append(str(error_type).upper())
    if not used and not failed_outcomes:
        tool_warnings.append("SOURCE_UNAVAILABLE")
    warnings = [*tool_warnings, *citation_verification.get("warnings", []), *config.warnings]
    source_attempts = [
        {
            "source_type": "law",
            "status": outcome.get("status"),
            "query": query,
            "error_type": outcome.get("error_type", ""),
            "parser_status": outcome.get("parser_status", ""),
            "response_shape_hint": outcome.get("response_shape_hint", ""),
            "source_url": outcome.get("source_url", ""),
        }
        for query, outcome in zip(law_search_queries, outcomes)
    ]
    representative = next((o for o in outcomes if o.get("status") == "ok"), outcomes[0] if outcomes else {})
    overall_error = ""
    if not used and failed_outcomes:
        non_empty = [str(o.get("error_type") or "") for o in failed_outcomes if o.get("error_type")]
        overall_error = next((e for e in non_empty if e.lower() != "law_api_no_results"), non_empty[0] if non_empty else "")
    return {
        "attempted": True,
        "intent_reasons": intent["reasons"],
        "law_search_query": law_search_query,
        "law_search_queries": law_search_queries,
        "law_grounding_used": used,
        "law_grounding": aggregate_results if used else [],
        "citation_verification": citation_verification,
        "grounding_sources": source_attempts,
        "parser_status": representative.get("parser_status", ""),
        "response_shape_hint": representative.get("response_shape_hint", ""),
        "source_url": representative.get("source_url", ""),
        "error_type": overall_error,
        "request_cache_hits": request_cache_hits,
        "grounding_warnings": list(dict.fromkeys(warnings)),
    }


# ---------------------------------------------------------------------------
# Granular, user-visible law-grounding status (single source of truth)
# ---------------------------------------------------------------------------
# The legacy ``law_grounding_status`` field is coarse (not_attempted / disabled /
# unavailable / used). The frontend "실시간 법령 확인" panel and operators need a
# more honest, mutually-exclusive status so an answer is never presented as if it
# were grounded on verified real-time law when it was not. These six values are
# the contract surfaced as ``law_grounding_status_detail``.
LAW_GROUNDING_STATUS_NOT_ATTEMPTED = "law_grounding_not_attempted"
LAW_GROUNDING_STATUS_ATTEMPTED_NO_RESULTS = "law_grounding_attempted_no_results"
LAW_GROUNDING_STATUS_ATTEMPTED_FAILED = "law_grounding_attempted_failed"
LAW_GROUNDING_STATUS_SOURCE_LINKED_UNVERIFIED = "law_grounding_source_linked_unverified"
LAW_GROUNDING_STATUS_VERIFIED = "law_grounding_verified"
LAW_GROUNDING_STATUS_AUDIT_ONLY = "law_grounding_audit_only"
LAW_GROUNDING_STATUS_DISABLED = "law_grounding_disabled"

LAW_GROUNDING_STATUS_DETAILS = (
    LAW_GROUNDING_STATUS_NOT_ATTEMPTED,
    LAW_GROUNDING_STATUS_ATTEMPTED_NO_RESULTS,
    LAW_GROUNDING_STATUS_ATTEMPTED_FAILED,
    LAW_GROUNDING_STATUS_SOURCE_LINKED_UNVERIFIED,
    LAW_GROUNDING_STATUS_VERIFIED,
    LAW_GROUNDING_STATUS_AUDIT_ONLY,
    LAW_GROUNDING_STATUS_DISABLED,
)

# Transport markers that mean "the lookup ran but found nothing to cite" rather
# than "the lookup failed". Anything else (timeouts, bad responses, transport
# errors, not-configured) is a genuine failure.
_NO_RESULT_MARKERS = {"LAW_API_NO_RESULTS", "NO_RESULTS"}


def derive_law_grounding_status_detail(
    *,
    configured_mode: str,
    effective_mode: str,
    intent_attempted: bool,
    lookup_attempted: bool,
    lookup_used: bool,
    citation_specific: bool = False,
    citation_verified: bool = False,
    error_type: str = "",
    warnings: Sequence[str] | None = None,
) -> str:
    """Map the runtime law-grounding state to one mutually-exclusive status.

    Semantics (these are what the UI/operators rely on):

    * ``law_grounding_not_attempted`` — the question had no legal intent.
    * ``law_grounding_disabled`` — LAW_GROUNDING_MODE=disabled, or ``enabled``
      with no credential (the effective-disabled rule): no external call is made
      and the answer is NOT treated as real-time-law-grounded.
    * ``law_grounding_audit_only`` — LAW_GROUNDING_MODE=audit: the lookup runs as
      a diagnostic / citation-verifier posture, NOT as enabled grounding, so its
      output must never be presented as verified real-time law.
    * ``law_grounding_verified`` — ``enabled`` (credentialed) and the lookup
      returned usable law results.
    * ``law_grounding_attempted_no_results`` — ``enabled`` lookup ran, found
      nothing citable.
    * ``law_grounding_attempted_failed`` — ``enabled`` lookup ran but errored
      (timeout / bad response / transport / not-configured).
    """
    if not intent_attempted:
        return LAW_GROUNDING_STATUS_NOT_ATTEMPTED
    if configured_mode == "disabled" or effective_mode == "disabled":
        return LAW_GROUNDING_STATUS_DISABLED
    if configured_mode == "audit":
        # Audit is the diagnostics/verifier posture; never "verified" grounding.
        return LAW_GROUNDING_STATUS_AUDIT_ONLY
    # configured/effective enabled (credentialed) from here on.
    if lookup_used and citation_specific and not citation_verified:
        return LAW_GROUNDING_STATUS_SOURCE_LINKED_UNVERIFIED
    if lookup_used:
        return LAW_GROUNDING_STATUS_VERIFIED
    error_u = str(error_type or "").upper()
    warnings_u = {str(w or "").upper() for w in (warnings or [])}
    if error_u in _NO_RESULT_MARKERS or (warnings_u & _NO_RESULT_MARKERS):
        return LAW_GROUNDING_STATUS_ATTEMPTED_NO_RESULTS
    if error_u or (warnings_u - {""}):
        return LAW_GROUNDING_STATUS_ATTEMPTED_FAILED
    if lookup_attempted:
        return LAW_GROUNDING_STATUS_ATTEMPTED_NO_RESULTS
    return LAW_GROUNDING_STATUS_ATTEMPTED_FAILED


def law_grounding_status_detail_is_verified(status_detail: str) -> bool:
    """True only when real-time law grounding produced verified, usable law."""
    return str(status_detail or "") == LAW_GROUNDING_STATUS_VERIFIED


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


# ---------------------------------------------------------------------------
# Network reachability diagnosis (pure logic — testable without any sockets)
#
# When the live selftest reports a connection-level failure (HTTP status 0,
# error_type ``law_api_bad_response``), the cause is *below* HTTP and cannot be
# inferred from the answer path alone. The debug ``netdiag`` endpoint gathers a
# small set of layered probes (DNS, a control egress connect, raw TCP to the
# law host on :80/:443, and HTTP(S) GETs without the OC) and feeds the boolean
# outcomes here. This function maps those outcomes to one stable diagnosis
# code. It performs NO I/O so every branch is unit-testable.
# ---------------------------------------------------------------------------

# Stable diagnosis codes (consumed by the debug endpoint + tests).
NETDIAG_DNS_FAILURE = "DNS_FAILURE"
NETDIAG_EGRESS_BLOCKED = "EGRESS_BLOCKED"
NETDIAG_REACHABLE_HTTPS = "REACHABLE_HTTPS"
NETDIAG_REACHABLE_HTTP = "REACHABLE_HTTP"
NETDIAG_LAWGOKR_CONNECTION_REFUSED = "LAWGOKR_CONNECTION_REFUSED"
NETDIAG_HTTP_PORT_80_BLOCKED = "HTTP_PORT_80_BLOCKED"
NETDIAG_HTTP_LAYER_ISSUE = "HTTP_LAYER_ISSUE"


def classify_law_host_reachability(probes: Dict[str, bool]) -> str:
    """Classify Open Law API host reachability from layered probe outcomes.

    ``probes`` keys (all booleans; missing keys treated as False):
      * ``dns_ok``        — the law host resolved via DNS
      * ``egress_ok``     — a control connection to a neutral host succeeded
      * ``law_https_ok``  — an HTTPS GET to the law host got an HTTP response
      * ``law_http_ok``   — an HTTP GET to the law host got an HTTP response
      * ``law_tcp_443_ok``— a raw TCP connect to the law host :443 succeeded
      * ``law_tcp_80_ok`` — a raw TCP connect to the law host :80 succeeded

    Order matters: DNS and general egress are ruled out first; a successful
    HTTP(S) response (even a 4xx) proves end-to-end reachability; otherwise a
    TCP-level result distinguishes a refused host (likely foreign/cloud-IP
    blocking by the Korean government server) from a port-80-only block or an
    HTTP-layer problem.
    """
    dns_ok = bool(probes.get("dns_ok"))
    egress_ok = bool(probes.get("egress_ok"))
    law_https_ok = bool(probes.get("law_https_ok"))
    law_http_ok = bool(probes.get("law_http_ok"))
    law_tcp_443_ok = bool(probes.get("law_tcp_443_ok"))
    law_tcp_80_ok = bool(probes.get("law_tcp_80_ok"))

    if not dns_ok:
        return NETDIAG_DNS_FAILURE
    if not egress_ok:
        return NETDIAG_EGRESS_BLOCKED
    if law_https_ok:
        return NETDIAG_REACHABLE_HTTPS
    if law_http_ok:
        return NETDIAG_REACHABLE_HTTP
    if not law_tcp_80_ok and not law_tcp_443_ok:
        return NETDIAG_LAWGOKR_CONNECTION_REFUSED
    if law_tcp_443_ok and not law_tcp_80_ok:
        return NETDIAG_HTTP_PORT_80_BLOCKED
    return NETDIAG_HTTP_LAYER_ISSUE
