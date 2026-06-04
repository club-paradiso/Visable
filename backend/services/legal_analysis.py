"""Deterministic legal-analysis guidance layer for Paradiso.

The LLM may explain this object, but must not invent it.  This module builds a
small, secret-free model from detected question intent, planned official source
families, manual/law evidence, and deterministic relevance scoring.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

RELEVANCE_DIRECT = "direct"
RELEVANCE_RELATED = "related"
RELEVANCE_ANALOGICAL = "analogical"
RELEVANCE_BACKGROUND = "background"
RELEVANCE_NOT_RELEVANT = "not_relevant"

ANALYSIS_DIRECT = "direct_authority"
ANALYSIS_CONTEXTUAL = "contextual_authority"
ANALYSIS_ANALOGICAL = "analogical_analysis"
ANALYSIS_LIMITED = "limited_authority"
ANALYSIS_SOURCE_UNAVAILABLE = "source_unavailable"
ANALYSIS_NOT_APPLICABLE = "not_applicable"

_CONFIDENCE_BY_MODE = {
    ANALYSIS_DIRECT: "direct",
    ANALYSIS_CONTEXTUAL: "contextual",
    ANALYSIS_ANALOGICAL: "analogical",
    ANALYSIS_LIMITED: "limited",
    ANALYSIS_SOURCE_UNAVAILABLE: "unavailable",
    ANALYSIS_NOT_APPLICABLE: "unavailable",
}

_STATUS_RE = re.compile(r"(?<![A-Za-z0-9])([A-H])\s*-?\s*(\d{1,2})(?![0-9])", re.IGNORECASE)


def _norm_code(raw: str) -> str:
    m = _STATUS_RE.search(raw or "")
    if not m:
        return (raw or "").upper()
    return f"{m.group(1).upper()}-{int(m.group(2))}"


def _codes(text: str) -> List[str]:
    out: List[str] = []
    for m in _STATUS_RE.finditer(text or ""):
        code = f"{m.group(1).upper()}-{int(m.group(2))}"
        if code not in out:
            out.append(code)
    return out


def _haystack(item: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "title", "name", "law_name", "term", "reference", "summary", "text",
        "content", "query", "source_type", "law_division", "rule_type", "section",
        "procedure_type",
    ):
        value = item.get(key)
        if value is not None:
            parts.append(str(value))
    return " ".join(parts)


def _has_study(text: str) -> bool:
    low = (text or "").lower()
    return any(s in low for s in ("study", "course", "class", "semester", "enroll", "university", "유학", "수강", "계절학기", "학점", "강의", "수업", "어학"))


def _has_work(text: str) -> bool:
    low = (text or "").lower()
    return any(s in low for s in ("work", "job", "employment", "part-time", "intern", "freelance", "취업", "근무", "아르바이트", "알바", "인턴", "프리랜서"))


def _has_activity_scope(text: str) -> bool:
    low = (text or "").lower()
    return any(s in low for s in ("activity scope", "scope of status", "outside status", "activities outside", "활동범위", "체류자격외활동", "자격외활동", "변경허가", "체류자격 변경"))


def score_evidence_relevance(
    evidence: Dict[str, Any],
    *,
    question: str,
    visa_code: Optional[str] = None,
    question_type: str = "",
) -> str:
    """Classify one evidence item as direct/related/analogical/background/noise.

    Direct evidence must match the asked status and the activity/procedure
    concept.  Related/analogical evidence is intentionally never promoted to
    direct authority merely because it mentions an adjacent status such as D-2/D-4.
    """
    if not isinstance(evidence, dict):
        return RELEVANCE_NOT_RELEVANT
    text = _haystack(evidence)
    if not text.strip():
        return RELEVANCE_NOT_RELEVANT
    low = text.lower()
    q = question or ""
    qlow = q.lower()
    asked_code = _norm_code(visa_code or (_codes(q)[0] if _codes(q) else ""))
    ev_codes = _codes(text)
    source_type = str(evidence.get("source_type") or evidence.get("target") or "").lower()

    if source_type in {"law_term", "legal_term", "lstrm"} or "법령용어" in text:
        return RELEVANCE_BACKGROUND

    # Hard guard: D-2/D-4 evidence in an H-1 study question is comparison
    # context only, never direct H-1 authority.
    if asked_code == "H-1" and _has_study(q) and any(c in {"D-2", "D-4"} for c in ev_codes):
        if _has_activity_scope(text) or _has_study(text):
            return RELEVANCE_RELATED
        return RELEVANCE_ANALOGICAL

    status_matches = bool(asked_code and asked_code in ev_codes)
    scenario_matches = False
    if question_type == "activity_on_status" or _has_activity_scope(q):
        scenario_matches = _has_activity_scope(text) or (_has_study(q) and _has_study(text)) or (_has_work(q) and _has_work(text))
    elif question_type == "documents_needed":
        scenario_matches = any(s in low for s in ("document", "documents", "서류", "첨부서류", "구비서류"))
    elif question_type == "status_change":
        scenario_matches = any(s in low for s in ("change of", "status change", "체류자격 변경", "변경허가"))
    elif question_type == "deadline_or_report":
        scenario_matches = any(s in low for s in ("deadline", "report", "registration", "신고", "등록", "기한"))
    else:
        scenario_matches = _has_activity_scope(text) or _has_study(text) or _has_work(text)

    if status_matches and scenario_matches:
        return RELEVANCE_DIRECT
    if status_matches:
        return RELEVANCE_RELATED
    if scenario_matches:
        # Adjacent legal concept without the exact asked status.
        return RELEVANCE_RELATED
    if any(term in low for term in ("immigration act", "출입국관리법", "시행령", "시행규칙", "체류자격", "sojourn status")):
        return RELEVANCE_BACKGROUND
    return RELEVANCE_NOT_RELEVANT


def _authority_stub(item: Dict[str, Any], relevance: str) -> Dict[str, Any]:
    title = item.get("source_title") or item.get("law_name") or item.get("term") or item.get("title") or item.get("reference") or "official source"
    return {
        "title": str(title)[:160],
        "source_type": item.get("source_type") or item.get("target") or "source",
        "relevance": relevance,
        "query": item.get("query", ""),
    }


def _main_issue(question_type: str, question: str, visa_code: Optional[str]) -> str:
    code = visa_code or (_codes(question)[0] if _codes(question) else "the current status")
    if question_type == "activity_on_status" and _has_study(question):
        return (
            f"Whether immigration treats the course as within {code}'s permitted activity scope "
            "(활동범위) or as activities outside the scope of status (체류자격외활동) requiring separate permission or a change of sojourn status (체류자격 변경)."
        )
    if question_type == "activity_on_status":
        return (
            f"Whether the proposed activity fits within {code}'s permitted activity scope or requires permission for activities outside the scope of status / a change of sojourn status."
        )
    if question_type == "documents_needed":
        return "Which required documents are source-confirmed by the official manual for the exact procedure, and which items remain case-specific."
    if question_type == "status_change":
        return "Whether the requested in-country change of sojourn status is legally/procedurally available on the user's facts."
    if question_type == "deadline_or_report":
        return "Which event triggers the reporting or deadline duty and what official procedure applies."
    if question_type in {"nationality_or_naturalization", "refugee_context"}:
        return "How the adjacent official legal framework affects residence/visa preparation while recognizing Paradiso's visa/residence focus."
    return "Identify the controlling Korean immigration issue and the strongest official-source basis available."


def _practical_posture(question_type: str, question: str, visa_code: Optional[str], mode: str, risk: str) -> str:
    code = visa_code or (_codes(question)[0] if _codes(question) else "the current status")
    if question_type == "activity_on_status" and code == "H-1" and _has_study(question):
        if any(s in (question or "").lower() for s in ("non-credit", "noncredit", "문화", "취미", "cultural")):
            return (
                "Treat a short non-credit cultural class as lower risk than degree-related enrollment, but still confirm whether immigration views it as within H-1's activity scope before relying on it."
            )
        return (
            "Treat a credit-bearing or degree-related university summer course as a high-risk activity under H-1 until immigration confirms otherwise."
        )
    if question_type == "activity_on_status":
        return f"Treat the proposed activity as a {risk}-risk status-scope issue until the competent immigration office confirms it."
    if question_type == "documents_needed":
        return "Use a checklist only from source-confirmed manual evidence; if the manual source is incomplete, prepare facts for official confirmation instead of relying on a law-only checklist."
    if question_type == "status_change":
        return "Treat this as a case-specific status-change analysis, not an automatic eligibility answer."
    if question_type == "deadline_or_report":
        return "Treat the reporting/deadline question as time-sensitive and confirm the trigger date and filing channel before acting."
    if mode == ANALYSIS_SOURCE_UNAVAILABLE:
        return "Prepare the facts and official questions first; Paradiso can give only limited risk posture without retrieved official authority."
    return "Use the strongest official-source context available while reserving final determination for the competent authority."


def _confirmation_questions(question_type: str, question: str, visa_code: Optional[str], existing: Sequence[str]) -> List[str]:
    if existing:
        return list(existing)
    code = visa_code or (_codes(question)[0] if _codes(question) else "current status")
    if question_type == "activity_on_status" and code == "H-1" and _has_study(question):
        return [
            "Is the course credit-bearing or degree-related?",
            "Does the course count toward a degree, exchange, or regular university enrollment?",
            "What are the syllabus, weekly hours, enrollment period, and campus/online format?",
            "Will study become the main purpose of stay, or will H-1 work/travel continue?",
            "Does immigration treat this as within H-1's permitted activity scope, activities outside status (체류자격외활동), or a required change to D-2/D-4?",
            "Does the university require D-2/D-4 independently of immigration's activity-scope assessment?",
        ]
    return [
        "What exact status, sub-code, and current period of stay apply?",
        "Which activity/procedure, start date, duration, hours, and compensation/document facts should the office assess?",
        "Does the competent office treat this as within status, reportable, permission-required, or status-change-required?",
    ]


def build_legal_analysis(
    *,
    question: str,
    question_type: str,
    visa_code: Optional[str],
    risk_level: str,
    source_type_plan: Optional[Dict[str, Any]] = None,
    direct_manual_sources: Optional[Sequence[Dict[str, Any]]] = None,
    related_manual_sources: Optional[Sequence[Dict[str, Any]]] = None,
    law_sources: Optional[Sequence[Dict[str, Any]]] = None,
    official_confirmation_questions: Optional[Sequence[str]] = None,
    law_grounding_status: str = "",
) -> Dict[str, Any]:
    direct_manual = list(direct_manual_sources or [])
    related_manual = list(related_manual_sources or [])
    laws = list(law_sources or [])

    scored: List[Dict[str, Any]] = []
    for item in direct_manual:
        scored.append({"item": item, "relevance": RELEVANCE_DIRECT})
    for item in related_manual:
        rel = score_evidence_relevance(item, question=question, visa_code=visa_code, question_type=question_type)
        scored.append({"item": item, "relevance": rel if rel != RELEVANCE_NOT_RELEVANT else RELEVANCE_RELATED})
    for item in laws:
        scored.append({"item": item, "relevance": score_evidence_relevance(item, question=question, visa_code=visa_code, question_type=question_type)})

    buckets = {k: [] for k in [RELEVANCE_DIRECT, RELEVANCE_RELATED, RELEVANCE_ANALOGICAL, RELEVANCE_BACKGROUND, RELEVANCE_NOT_RELEVANT]}
    for row in scored:
        buckets.setdefault(row["relevance"], []).append(row["item"])

    direct_count = len(buckets[RELEVANCE_DIRECT])
    related_count = len(buckets[RELEVANCE_RELATED])
    analogical_count = len(buckets[RELEVANCE_ANALOGICAL])
    background_count = len(buckets[RELEVANCE_BACKGROUND])

    if question_type in {"general", "procedure_or_code_lookup"} and not (direct_count or related_count or analogical_count or background_count):
        mode = ANALYSIS_NOT_APPLICABLE
    elif direct_count:
        mode = ANALYSIS_DIRECT
    elif related_count:
        mode = ANALYSIS_CONTEXTUAL
    elif analogical_count:
        mode = ANALYSIS_ANALOGICAL
    elif background_count:
        mode = ANALYSIS_LIMITED
    elif law_grounding_status in {"unavailable", "disabled"}:
        mode = ANALYSIS_SOURCE_UNAVAILABLE
    else:
        mode = ANALYSIS_LIMITED

    missing_direct = direct_count == 0
    concepts = ["체류자격", "활동범위", "체류자격외활동", "체류자격 변경"] if question_type == "activity_on_status" else ["체류자격", "official-source confirmation"]
    if _has_study(question):
        concepts.extend(["유학(D-2)", "일반연수(D-4)"])
    concepts = list(dict.fromkeys(concepts))

    attempted = []
    returned = []
    statuses = {}
    if isinstance(source_type_plan, dict):
        statuses = dict(source_type_plan.get("statuses") or {})
        attempted = list(source_type_plan.get("source_types_attempted") or [])
        returned = list(source_type_plan.get("source_types_returned") or [])

    authority_summary = (
        f"direct={direct_count}, related={related_count}, analogical={analogical_count}, background={background_count}; "
        + ("no direct scenario-specific authority found" if missing_direct else "direct scenario-specific authority found")
    )

    return {
        "analysis_mode": mode,
        "main_issue": _main_issue(question_type, question, visa_code),
        "sub_issues": [
            "status activity scope versus permission/change requirement",
            "university enrollment rules versus immigration authorization",
            "credit-bearing or degree-related course versus short non-credit class",
        ] if question_type == "activity_on_status" and _has_study(question) else ["source-confirmed facts", "case-specific variables", "remaining official uncertainty"],
        "relevant_legal_concepts": concepts,
        "source_types_attempted": attempted,
        "source_types_returned": returned,
        "source_type_statuses": statuses,
        "direct_authority": [_authority_stub(i, RELEVANCE_DIRECT) for i in buckets[RELEVANCE_DIRECT][:5]],
        "related_authority": [_authority_stub(i, RELEVANCE_RELATED) for i in buckets[RELEVANCE_RELATED][:5]],
        "analogical_authority": [_authority_stub(i, RELEVANCE_ANALOGICAL) for i in buckets[RELEVANCE_ANALOGICAL][:5]],
        "background_authority": [_authority_stub(i, RELEVANCE_BACKGROUND) for i in buckets[RELEVANCE_BACKGROUND][:5]],
        "missing_direct_authority": missing_direct,
        "risk_posture": risk_level if risk_level in {"low", "medium", "high"} else "medium",
        "confidence": _CONFIDENCE_BY_MODE.get(mode, "limited"),
        "practical_posture": _practical_posture(question_type, question, visa_code, mode, risk_level if risk_level in {"low", "medium", "high"} else "medium"),
        "official_confirmation_questions": _confirmation_questions(question_type, question, visa_code, official_confirmation_questions or []),
        "direct_evidence_count": direct_count,
        "related_evidence_count": related_count,
        "analogical_evidence_count": analogical_count,
        "background_evidence_count": background_count,
        "authority_summary": authority_summary,
    }


def first_sentence_quality_warning(answer: str) -> str:
    first = (answer or "").strip().split(".", 1)[0].strip().lower()
    if not first:
        return "empty_answer"
    for prefix in ("paradiso cannot verify", "whether you can", "it depends", "specific manual guidance was not found"):
        if first.startswith(prefix):
            return "failure_first_framing"
    return ""
