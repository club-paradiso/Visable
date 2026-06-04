"""Deterministic legal-analysis guidance layer for Paradiso.

The LLM may explain this object, but must not invent it. This module builds a
small, secret-free model from extracted immigration facts, issue taxonomy,
planned official source families, manual/law evidence, and deterministic
relevance scoring.
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

LEGAL_ISSUE_TYPES = (
    "activity_scope", "outside_status_activity", "status_change", "extension",
    "documents_needed", "reporting_duty", "workplace_change_addition",
    "registration_or_residence_report", "reentry", "overstay_or_risk",
    "approval_condition", "status_purpose_alignment", "employment_restriction",
    "study_on_non_study_status", "work_on_non_work_status",
    "post_status_change_residual_duty", "nationality_or_refugee_context",
    "legal_general", "non_immigration_adjacent_issue",
)

ACTIVITY_TYPES = (
    "credit_bearing_study", "formal_enrollment", "non_credit_audit",
    "non_credit_cultural_or_hobby", "language_training", "paid_work",
    "unpaid_internship", "paid_internship", "freelance_work", "side_job",
    "additional_employment", "business_activity", "volunteer_activity",
    "workplace_change", "workplace_addition", "medical_treatment",
    "litigation_related_stay", "family_or_marriage_related",
    "refugee_or_humanitarian_context", "registration_or_reporting",
    "reentry_or_departure", "document_preparation", "status_extension",
    "status_change_route",
)

SOURCE_FAMILIES = (
    "manual", "statute", "enforcement_decree", "enforcement_rule",
    "administrative_rule", "legal_interpretation", "precedent",
    "administrative_appeal", "constitutional_decision", "legal_term",
    "intelligent_search",
)

_STATUS_RE = re.compile(r"(?<![A-Za-z0-9])([A-H])\s*-?\s*(\d{1,2})(?:\s*-?\s*(\d{1,3}))?(?![0-9])", re.IGNORECASE)
_TRANSITION_RE = re.compile(
    r"([A-H]\s*-?\s*\d{1,2}(?:\s*-?\s*\d{1,3})?)\s*(?:에서|부터|->|→|to|from)\s*([A-H]\s*-?\s*\d{1,2}(?:\s*-?\s*\d{1,3})?)",
    re.IGNORECASE,
)
_PARENT_STUDY = {"D-2", "D-4"}
_PARENT_WORK = {"E-1", "E-2", "E-3", "E-4", "E-5", "E-6", "E-7", "E-9", "C-4", "H-2"}
_RESTRICTED_WORK = {"C-3", "B-1", "B-2", "D-10", "H-1", "G-1"}


def _norm_code(raw: str) -> str:
    m = _STATUS_RE.search(raw or "")
    if not m:
        return (raw or "").upper()
    base = f"{m.group(1).upper()}-{int(m.group(2))}"
    return f"{base}-{int(m.group(3))}" if m.group(3) else base


def _parent_status(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    m = re.match(r"^([A-H]-\d{1,2})(?:-\d{1,3})?$", code)
    return m.group(1) if m else code


def _sub_status(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    return code if re.match(r"^[A-H]-\d{1,2}-\d{1,3}$", code) else None


def _codes(text: str) -> List[str]:
    out: List[str] = []
    for m in _STATUS_RE.finditer(text or ""):
        code = _norm_code(m.group(0))
        if code not in out:
            out.append(code)
    return out


def _low(text: str) -> str:
    return (text or "").lower()


def _has_any(text: str, *needles: str) -> bool:
    low = _low(text)
    return any(n.lower() in low for n in needles)


def _has_formal_enrollment_context(text: str) -> bool:
    """Detect school enrollment without treating every Korean 등록 as study.

    Bare 등록 also appears in 외국인등록 and 사업자등록. Those must route to
    registration/reporting or business issues, not study-on-non-study-status.
    """
    if _has_any(text, "입학", "정규과정", "enroll", "enrollment", "matriculat", "university program"):
        return True
    if _has_any(text, "대학교 등록", "대학 등록", "학교 등록", "수강 등록", "학기 등록", "학생 등록"):
        return True
    if "등록" in (text or "") and _has_any(text, "대학교", "대학", "학교", "수강", "학기", "정규"):
        return True
    return False


def _asks_status_change_to_target(text: str) -> bool:
    return _has_any(
        text,
        "change status", "change to", "switch to", "status to", "convert to",
        "변경", "전환", "바꾸", "자격변경", "체류자격 변경", "으로 변경", "로 변경",
    )


def detect_question_language(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text or "") and not re.search(r"[가-힣]", text or ""):
        return "zhHant" if re.search(r"[學國臺簽證體]", text or "") else "zh"
    if re.search(r"[가-힣]", text or ""):
        return "ko"
    if re.search(r"[A-Za-z]", text or ""):
        return "en"
    return "unknown"


def classify_activity_types(question: str) -> List[str]:
    """Deterministic multilingual activity classifier; one question may have many."""
    text = question or ""
    activities: List[str] = []

    def add(name: str) -> None:
        if name in ACTIVITY_TYPES and name not in activities:
            activities.append(name)

    if _has_any(text, "학점", "credit-bearing", "credits", "credit course", "계절학기", "summer semester", "summer course"):
        add("credit_bearing_study")
    if _has_formal_enrollment_context(text):
        add("formal_enrollment")
    if _has_any(text, "청강", "audit", "non-credit", "noncredit", "비학점"):
        add("non_credit_audit")
    if _has_any(text, "문화센터", "취미", "hobby", "cultural class", "culture class", "non-credit cultural"):
        add("non_credit_cultural_or_hobby")
    if _has_any(text, "어학", "language school", "language training", "korean class", "한국어 수업"):
        add("language_training")
    if _has_any(text, "유급", "급여", "보수", "paid", "salary", "wage", "compensat"):
        add("paid_work")
    if _has_any(text, "무급 인턴", "unpaid internship"):
        add("unpaid_internship")
    if _has_any(text, "유급 인턴", "paid internship", "paid intern", "인턴") and "unpaid_internship" not in activities:
        add("paid_internship" if _has_any(text, "유급", "paid", "급여") else "unpaid_internship")
    if _has_any(text, "프리랜서", "freelance", "client", "외주"):
        add("freelance_work")
    if _has_any(text, "부업", "side job", "second job", "moonlight"):
        add("side_job")
    if _has_any(text, "추가 고용", "추가 근무처", "additional employer", "additional employment", "second employer"):
        add("additional_employment")
    if _has_any(text, "사업자등록", "개인사업", "창업", "business registration", "business activity", "sole proprietor"):
        add("business_activity")
    if _has_any(text, "자원봉사", "봉사", "volunteer"):
        add("volunteer_activity")
    if _has_any(text, "근무처 변경", "직장 변경", "change workplace", "workplace change", "change employer"):
        add("workplace_change")
    if _has_any(text, "근무처 추가", "직장 추가", "add workplace", "workplace addition", "add employer"):
        add("workplace_addition")
    if _has_any(text, "치료", "medical treatment", "hospital"):
        add("medical_treatment")
    if _has_any(text, "소송", "litigation", "lawsuit", "trial"):
        add("litigation_related_stay")
    if _has_any(text, "결혼", "이혼", "배우자", "marriage", "divorce", "spouse"):
        add("family_or_marriage_related")
    if _has_any(text, "난민", "인도적", "refugee", "asylum", "humanitarian"):
        add("refugee_or_humanitarian_context")
    if _has_any(text, "외국인등록", "거소신고", "신고", "report", "registration", "residence report", "ARC"):
        add("registration_or_reporting")
    if _has_any(text, "재입국", "출국", "re-entry", "reentry", "depart", "leave korea"):
        add("reentry_or_departure")
    if _has_any(text, "서류", "documents", "checklist", "구비서류"):
        add("document_preparation")
    if _has_any(text, "연장", "extension", "extend"):
        add("status_extension")
    if _has_any(text, "변경", "전환", "switch", "change status", "status change") or _TRANSITION_RE.search(text):
        add("status_change_route")
    if not activities and _has_any(text, "일", "근무", "work", "job", "employment", "아르바이트", "알바", "취업"):
        add("paid_work")
    if not activities and _has_any(text, "수업", "강의", "course", "class", "study"):
        add("formal_enrollment")
    return activities


def _tri(question: str, true_terms: Sequence[str], false_terms: Sequence[str] = ()) -> str:
    if _has_any(question, *true_terms):
        return "true"
    if false_terms and _has_any(question, *false_terms):
        return "false"
    return "unknown"


def extract_immigration_facts(question: str, *, visa_code: Optional[str] = None) -> Dict[str, Any]:
    text = question or ""
    codes = _codes(text)
    explicit_hint = _norm_code(visa_code or "") if visa_code else None
    previous_status: Optional[str] = None
    current_status: Optional[str] = explicit_hint or (codes[0] if codes else None)
    target_status: Optional[str] = None
    transition = _TRANSITION_RE.search(text)
    if transition:
        previous_status = _norm_code(transition.group(1))
        target_status = _norm_code(transition.group(2))
        current_status = target_status
    elif explicit_hint and codes and len(codes) < 2 and _asks_status_change_to_target(text):
        target_candidates = [code for code in codes if code != explicit_hint]
        if target_candidates:
            previous_status = explicit_hint
            target_status = target_candidates[-1]
            # The UI often supplies the selected/current visa separately. Preserve
            # that current status and record the in-text code as the target route.
            current_status = explicit_hint
    elif len(codes) >= 2 and _has_any(text, "from", "에서", "->", "→", "to", "변경", "전환"):
        previous_status = codes[0]
        target_status = codes[-1] if _has_any(text, "변경", "전환", "change", "switch") else codes[1]
        current_status = target_status

    acts = classify_activity_types(text)
    paid = "true" if any(a in acts for a in ("paid_work", "paid_internship", "freelance_work", "side_job", "additional_employment", "business_activity")) else _tri(text, ("paid", "유급", "급여", "보수"), ("unpaid", "무급"))
    facts = {
        "current_status": current_status,
        "current_parent_status": _parent_status(current_status),
        "current_sub_status": _sub_status(current_status),
        "previous_status": previous_status,
        "previous_parent_status": _parent_status(previous_status),
        "previous_sub_status": _sub_status(previous_status),
        "target_status": target_status,
        "target_parent_status": _parent_status(target_status),
        "target_sub_status": _sub_status(target_status),
        "status_transition_detected": bool(previous_status and target_status),
        "proposed_activities": acts,
        "activity_facts": {
            "credit_bearing": "true" if "credit_bearing_study" in acts else _tri(text, ("학점", "credit-bearing", "credits"), ("non-credit", "noncredit", "비학점", "청강")),
            "degree_related": _tri(text, ("degree", "학위", "정규과정", "전공"), ("hobby", "취미", "문화", "non-credit", "청강")),
            "paid": paid,
            "formal_enrollment": "true" if "formal_enrollment" in acts else ("false" if _has_any(text, "외국인등록", "사업자등록", "거소신고") else _tri(text, ("enroll", "입학", "정규과정", "대학교 등록", "대학 등록", "학교 등록", "수강 등록"), ("audit", "청강", "non-credit"))),
            "institution_registered": _tri(text, ("registered institution", "인가", "등록된 기관")),
            "duration_known": "true" if re.search(r"\b\d+\s*(?:day|days|week|weeks|month|months|hour|hours)\b|\d+\s*(?:일|주|개월|시간)", text, re.IGNORECASE) else "false",
            "employer_or_client_known": "true" if _has_any(text, "employer", "client", "회사", "고용주", "근무처") else "false",
            "business_registration_issue": "true" if "business_activity" in acts else _tri(text, ("사업자등록", "business registration")),
            "approval_condition_issue": "true" if _has_any(text, "조건", "approval condition", "condition of approval", "허가조건") else "unknown",
        },
        "user_question_language": detect_question_language(text),
    }
    return facts


def classify_legal_issue_types(question: str, immigration_facts: Optional[Dict[str, Any]] = None) -> List[str]:
    facts = immigration_facts or extract_immigration_facts(question)
    text = question or ""
    acts = set(facts.get("proposed_activities") or [])
    current_parent = facts.get("current_parent_status") or facts.get("current_status")
    issues: List[str] = []

    def add(name: str) -> None:
        if name in LEGAL_ISSUE_TYPES and name not in issues:
            issues.append(name)

    if acts & {"document_preparation"}:
        add("documents_needed")
    if acts & {"status_extension"}:
        add("extension")
    if acts & {"status_change_route"} or facts.get("status_transition_detected"):
        add("status_change")
    if acts & {"registration_or_reporting"}:
        add("reporting_duty"); add("registration_or_residence_report")
    if acts & {"workplace_change", "workplace_addition", "additional_employment"}:
        add("reporting_duty"); add("workplace_change_addition")
    if acts & {"reentry_or_departure"}:
        add("reentry")
    if _has_any(text, "overstay", "초과체류", "불법체류", "expired", "one day", "하루", "도과"):
        add("overstay_or_risk")
    if facts.get("activity_facts", {}).get("approval_condition_issue") == "true":
        add("approval_condition")
    if _has_any(text, "귀화", "국적", "naturalization", "nationality", "citizenship", "난민", "refugee", "asylum", "인도적"):
        add("nationality_or_refugee_context")
    study_acts = acts & {"credit_bearing_study", "formal_enrollment", "non_credit_audit", "non_credit_cultural_or_hobby", "language_training"}
    work_acts = acts & {"paid_work", "paid_internship", "freelance_work", "side_job", "additional_employment", "business_activity", "workplace_change", "workplace_addition"}
    if study_acts:
        add("activity_scope"); add("status_purpose_alignment")
        if current_parent not in _PARENT_STUDY:
            add("study_on_non_study_status")
    if work_acts:
        add("activity_scope")
        if current_parent not in _PARENT_WORK and current_parent not in {"F-2", "F-4", "F-5", "F-6"}:
            add("outside_status_activity"); add("work_on_non_work_status")
        if current_parent in _RESTRICTED_WORK or current_parent in {"F-4", "D-4"}:
            add("employment_restriction")
    if facts.get("status_transition_detected") and (acts & {"side_job", "workplace_change", "workplace_addition", "additional_employment"} or _has_any(text, "이전", "previous", "old status", "residual")):
        add("post_status_change_residual_duty")
    if not issues and _has_any(text, "법", "legal", "allowed", "가능", "can i", "may i"):
        add("legal_general")
    if not issues:
        add("non_immigration_adjacent_issue")
    return issues


def build_generalized_source_plan(
    question: str,
    immigration_facts: Optional[Dict[str, Any]] = None,
    legal_issue_types: Optional[Sequence[str]] = None,
    *,
    manual_present: bool = False,
    law_sources: Optional[Sequence[Dict[str, Any]]] = None,
    law_api_attempted: bool = False,
    law_grounding_status: str = "not_attempted",
    max_queries: int = 7,
) -> Dict[str, Any]:
    facts = immigration_facts or extract_immigration_facts(question)
    issues = list(legal_issue_types or classify_legal_issue_types(question, facts))
    families: List[str] = []

    def add(*names: str) -> None:
        for name in names:
            if name in SOURCE_FAMILIES and name not in families:
                families.append(name)

    for issue in issues:
        if issue == "documents_needed":
            add("manual", "statute", "enforcement_rule")
        elif issue in {"activity_scope", "outside_status_activity", "status_purpose_alignment", "employment_restriction", "study_on_non_study_status", "work_on_non_work_status"}:
            add("statute", "enforcement_decree", "enforcement_rule", "administrative_rule", "legal_interpretation", "administrative_appeal", "manual")
        elif issue == "status_change":
            add("manual", "statute", "enforcement_decree", "legal_interpretation", "administrative_appeal")
        elif issue in {"reporting_duty", "workplace_change_addition", "registration_or_residence_report"}:
            add("manual", "statute", "enforcement_rule", "administrative_rule", "legal_interpretation")
        elif issue == "overstay_or_risk":
            add("statute", "enforcement_decree", "enforcement_rule", "administrative_appeal")
        elif issue == "nationality_or_refugee_context":
            add("statute", "enforcement_decree", "enforcement_rule", "legal_interpretation", "manual")
        elif issue == "post_status_change_residual_duty":
            add("manual", "statute", "enforcement_rule", "administrative_rule", "legal_interpretation")
        elif issue in {"reentry", "extension", "approval_condition"}:
            add("manual", "statute", "enforcement_decree", "enforcement_rule", "administrative_rule", "legal_interpretation")
        else:
            add("manual", "statute", "enforcement_decree", "enforcement_rule", "legal_term")
    if not families:
        add("manual", "statute", "legal_term")

    query_bits = [facts.get("current_status"), facts.get("previous_status"), facts.get("target_status"), " ".join(facts.get("proposed_activities") or []), " ".join(issues)]
    queries = []
    for family in families:
        anchor = {
            "manual": "체류자격 매뉴얼 절차 서류 활동범위",
            "statute": "출입국관리법 체류자격 활동범위 신고의무",
            "enforcement_decree": "출입국관리법 시행령 체류자격 별표 활동범위",
            "enforcement_rule": "출입국관리법 시행규칙 체류자격 허가 신고 첨부서류",
            "administrative_rule": "행정규칙 체류자격외활동 근무처 변경 추가 신고",
            "legal_interpretation": "법령해석 체류자격 활동범위 체류자격외활동",
            "administrative_appeal": "행정심판 체류자격외활동 체류자격 취소",
            "precedent": "판례 출입국관리 체류자격",
            "constitutional_decision": "헌법재판소 외국인 체류자격",
            "legal_term": "법령용어 체류자격 체류자격외활동",
            "intelligent_search": "지능형검색 출입국 체류자격",
        }.get(family, "출입국 체류자격")
        query = " ".join(str(x) for x in [anchor, *query_bits] if x)[:240]
        if query not in queries:
            queries.append(query)
        if len(queries) >= max(1, min(max_queries, 8)):
            break

    supported = {"manual", "statute", "enforcement_decree", "enforcement_rule", "administrative_rule", "legal_term"}
    law_sources = list(law_sources or [])
    returned_types = set()
    for src in law_sources:
        st = str(src.get("source_type") or src.get("target") or "law").lower()
        if st in {"law", "statute"}:
            returned_types.update({"statute", "enforcement_decree", "enforcement_rule"})
        elif st in {"admin_rule", "administrative_rule", "admrul"}:
            returned_types.add("administrative_rule")
        elif st in {"law_term", "legal_term", "lstrm"}:
            returned_types.add("legal_term")
    statuses: Dict[str, str] = {}
    for family in SOURCE_FAMILIES:
        if family not in families:
            statuses[family] = "not_attempted"
        elif family == "manual":
            statuses[family] = "results_found" if manual_present else "attempted"
        elif family not in supported:
            statuses[family] = "unsupported"
        elif family in returned_types:
            statuses[family] = "results_found"
        elif law_api_attempted:
            statuses[family] = "unavailable" if law_grounding_status == "unavailable" else "no_results"
        else:
            statuses[family] = "attempted"
    attempted = [f for f in families if statuses.get(f) in {"attempted", "results_found", "no_results", "unavailable", "parse_error"}]
    return {
        "legal_issue_types": issues,
        "immigration_facts": facts,
        "source_types_priority": families,
        "source_types_attempted": attempted,
        "source_types_returned": [f for f in SOURCE_FAMILIES if statuses.get(f) == "results_found"],
        "unsupported_source_types": [f for f in families if statuses.get(f) == "unsupported"],
        "statuses": statuses,
        "queries": queries,
        "max_queries": max(1, min(max_queries, 8)),
    }


def _haystack(item: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("title", "name", "law_name", "term", "reference", "summary", "text", "content", "query", "source_type", "law_division", "rule_type", "section", "procedure_type"):
        value = item.get(key)
        if value is not None:
            parts.append(str(value))
    return " ".join(parts)


def _has_study(text: str) -> bool:
    return _has_any(text, "study", "course", "class", "semester", "enroll", "university", "유학", "수강", "계절학기", "학점", "강의", "수업", "어학", "청강")


def _has_work(text: str) -> bool:
    return _has_any(text, "work", "job", "employment", "part-time", "intern", "freelance", "취업", "근무", "아르바이트", "알바", "인턴", "프리랜서", "부업")


def _has_activity_scope(text: str) -> bool:
    return _has_any(text, "activity scope", "scope of status", "outside status", "activities outside", "활동범위", "체류자격외활동", "자격외활동", "변경허가", "체류자격 변경")


def score_evidence_relevance(evidence: Dict[str, Any], *, question: str, visa_code: Optional[str] = None, question_type: str = "", immigration_facts: Optional[Dict[str, Any]] = None, legal_issue_types: Optional[Sequence[str]] = None) -> str:
    if not isinstance(evidence, dict):
        return RELEVANCE_NOT_RELEVANT
    text = _haystack(evidence)
    if not text.strip():
        return RELEVANCE_NOT_RELEVANT
    facts = immigration_facts or extract_immigration_facts(question, visa_code=visa_code)
    issues = set(legal_issue_types or classify_legal_issue_types(question, facts))
    asked_code = facts.get("current_status") or _norm_code(visa_code or (_codes(question)[0] if _codes(question) else ""))
    previous_code = facts.get("previous_status")
    ev_codes = _codes(text)
    source_type = str(evidence.get("source_type") or evidence.get("target") or "").lower()
    low = text.lower()

    if source_type in {"law_term", "legal_term", "lstrm"} or "법령용어" in text:
        return RELEVANCE_BACKGROUND
    if previous_code and previous_code in ev_codes and asked_code not in ev_codes:
        return RELEVANCE_RELATED if issues & {"post_status_change_residual_duty", "approval_condition", "reporting_duty", "workplace_change_addition"} else RELEVANCE_ANALOGICAL

    status_matches = bool(asked_code and asked_code in ev_codes)
    parent_matches = bool(facts.get("current_parent_status") and facts.get("current_parent_status") in ev_codes)
    concept_matches = (
        _has_activity_scope(text)
        or (issues & {"documents_needed"} and _has_any(text, "document", "documents", "서류", "첨부서류", "구비서류"))
        or (issues & {"status_change"} and _has_any(text, "change of", "status change", "체류자격 변경", "변경허가"))
        or (issues & {"reporting_duty", "workplace_change_addition", "registration_or_residence_report"} and _has_any(text, "deadline", "report", "registration", "신고", "등록", "근무처"))
        or (issues & {"overstay_or_risk"} and _has_any(text, "overstay", "체류기간", "초과체류", "강제퇴거", "출국명령"))
        or (_has_study(question) and _has_study(text))
        or (_has_work(question) and _has_work(text))
    )
    if status_matches and concept_matches:
        return RELEVANCE_DIRECT
    if status_matches or (parent_matches and not facts.get("current_sub_status")):
        return RELEVANCE_RELATED
    if concept_matches:
        return RELEVANCE_RELATED
    if any(term in low for term in ("immigration act", "출입국관리법", "시행령", "시행규칙", "체류자격", "sojourn status", "국적법", "난민법")):
        return RELEVANCE_BACKGROUND
    return RELEVANCE_NOT_RELEVANT


def _authority_stub(item: Dict[str, Any], relevance: str) -> Dict[str, Any]:
    title = item.get("source_title") or item.get("law_name") or item.get("term") or item.get("title") or item.get("reference") or "official source"
    return {"title": str(title)[:160], "source_type": item.get("source_type") or item.get("target") or "source", "relevance": relevance, "query": item.get("query", "")}


def _main_issue(issues: Sequence[str], facts: Dict[str, Any]) -> str:
    code = facts.get("current_status") or "the current status"
    target = facts.get("target_status")
    acts = facts.get("proposed_activities") or []
    if "post_status_change_residual_duty" in issues:
        return f"Whether duties tied to {facts.get('previous_status')} remain relevant after the current {code} status, especially reporting or approval-condition duties."
    if "documents_needed" in issues:
        return "Which required documents are source-confirmed by the official manual, without turning law-only authority into a checklist."
    if "status_change" in issues:
        route = f" from {code} to {target}" if target and target != code else ""
        return f"Whether the requested in-country change of sojourn status{route} is procedurally and legally available on the user's facts."
    if "overstay_or_risk" in issues:
        return "How a possible overstay affects status risk and what immediate official steps should be confirmed without inventing penalties."
    if "nationality_or_refugee_context" in issues:
        return "How nationality/refugee law context affects Korean residence preparation while staying within Paradiso's visa/residence scope."
    if any(i in issues for i in ("activity_scope", "outside_status_activity", "study_on_non_study_status", "work_on_non_work_status")):
        return f"Whether {', '.join(acts) or 'the proposed activity'} fits within {code}'s permitted activity scope or requires activities outside status permission, reporting, or a change of sojourn status."
    return "Identify the controlling Korean immigration issue and strongest official-source basis available."


def _sub_issues(issues: Sequence[str], facts: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    if "activity_scope" in issues:
        out.append("status activity scope versus activities-outside-status permission")
    if "status_purpose_alignment" in issues:
        out.append("activity purpose and duration versus the status purpose")
    if "reporting_duty" in issues or "workplace_change_addition" in issues:
        out.append("event-triggered reporting/workplace change or addition duty")
    if "documents_needed" in issues:
        out.append("manual-confirmed checklist versus law-only background")
    if "approval_condition" in issues:
        out.append("case-specific approval condition as a potentially decisive fact")
    if facts.get("previous_status"):
        out.append("current status authority versus previous-status comparative authority")
    if facts.get("target_status"):
        out.append("target-status route and source family planning")
    return out or ["source-confirmed facts", "case-specific variables", "remaining official uncertainty"]


def _risk_from_issues(issues: Sequence[str], risk: str) -> str:
    if any(i in issues for i in ("overstay_or_risk", "work_on_non_work_status", "outside_status_activity", "approval_condition")):
        return "high"
    if any(i in issues for i in ("activity_scope", "status_change", "reporting_duty", "employment_restriction")):
        return "medium"
    return risk if risk in {"low", "medium", "high"} else "medium"


def _practical_posture(issues: Sequence[str], facts: Dict[str, Any], mode: str, risk: str) -> str:
    code = facts.get("current_status") or "the current status"
    target = facts.get("target_status")
    acts = facts.get("proposed_activities") or []
    if "overstay_or_risk" in issues:
        return "Treat this as time-sensitive status-risk triage; confirm the overstay date and available correction/departure options before assuming any penalty or outcome."
    if "post_status_change_residual_duty" in issues:
        return f"Analyze the current {code} status first, but preserve previous-status approval/reporting conditions as related facts that may still matter."
    if "status_change" in issues and target:
        return f"Analyze the requested change from {code} to {target} as a target-status route, not only as a question about the current status."
    if "study_on_non_study_status" in issues:
        return f"Treat the study activity on {code} as a status-scope and purpose-alignment issue, with higher risk for credit-bearing or formal enrollment."
    if "work_on_non_work_status" in issues:
        return f"Treat paid or business activity on {code} as high-risk unless a source-confirmed work authorization, report, or permission route applies."
    if "workplace_change_addition" in issues:
        return "Treat workplace change/addition as report-or-permission sensitive; identify the exact employer, timing, and current approval conditions."
    if "documents_needed" in issues:
        return "Use manual-confirmed checklist evidence first; do not rely on law-only sources to invent required documents."
    if mode == ANALYSIS_SOURCE_UNAVAILABLE:
        return "Prepare extracted facts and concrete official questions first; source retrieval limits do not turn the answer into a failure-only response."
    return f"Treat {', '.join(acts) or 'the activity'} as a {risk}-risk immigration issue until the competent authority applies the facts."


def _confirmation_questions(issues: Sequence[str], facts: Dict[str, Any], existing: Sequence[str]) -> List[str]:
    questions = [
        f"What exact current status/sub-status and period of stay apply ({facts.get('current_status') or 'unknown'})?",
        "What are the activity start date, duration, hours, location, and compensation or enrollment terms?",
    ]
    if facts.get("target_status"):
        questions.append(f"What exact target status/procedure is being requested ({facts.get('target_status')})?")
    if "study_on_non_study_status" in issues or "status_purpose_alignment" in issues:
        questions.extend([
            "Is the course credit-bearing, degree-related, or part of formal enrollment?",
            "Does the school require D-2 / D-4 or another status independently of immigration's activity-scope assessment?",
        ])
    if "workplace_change_addition" in issues or "reporting_duty" in issues:
        questions.append("Is this a workplace change/addition, side activity, or reportable change under the current approval conditions?")
    if "approval_condition" in issues:
        questions.append("What exact approval condition was written on the prior/current permission notice?")
    if "overstay_or_risk" in issues:
        questions.append("What was the exact expiry date and how many calendar days have passed?")
    questions.append("Does the competent office treat this as within status, reportable, permission-required, or status-change-required?")
    for q in existing or []:
        if isinstance(q, str) and q.strip():
            questions.append(q.strip())
    return list(dict.fromkeys(questions))[:8]


def build_issue_based_answer_template(legal_analysis: Dict[str, Any]) -> str:
    issues = set(legal_analysis.get("legal_issue_types") or [])
    if "study_on_non_study_status" in issues:
        name = "Study/activity on non-study status"
    elif "work_on_non_work_status" in issues or "employment_restriction" in issues:
        name = "Work/activity on non-work or restricted status"
    elif "post_status_change_residual_duty" in issues:
        name = "Post-status-change residual duty"
    elif "workplace_change_addition" in issues:
        name = "Workplace change/addition/reporting duty"
    elif "status_change" in issues:
        name = "Status change route"
    elif "documents_needed" in issues:
        name = "Document checklist"
    elif "extension" in issues:
        name = "Extension/high-risk exception"
    elif "overstay_or_risk" in issues:
        name = "Overstay/risk"
    elif "registration_or_residence_report" in issues:
        name = "Registration/reporting"
    elif "nationality_or_refugee_context" in issues:
        name = "Nationality/refugee context"
    else:
        name = "Non-immigration adjacent issue"
    return (
        f"Issue-based template: {name}. Start with practical legal posture; identify current status/activity/issue; "
        "explain legal analysis from backend-prepared evidence; state source basis later; ask decisive facts; avoid final administrative determination."
    )


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
    immigration_facts: Optional[Dict[str, Any]] = None,
    legal_issue_types: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    facts = immigration_facts or extract_immigration_facts(question, visa_code=visa_code)
    issues = list(legal_issue_types or classify_legal_issue_types(question, facts))
    direct_manual = list(direct_manual_sources or [])
    related_manual = list(related_manual_sources or [])
    laws = list(law_sources or [])

    scored: List[Dict[str, Any]] = []
    for item in direct_manual:
        scored.append({"item": item, "relevance": RELEVANCE_DIRECT})
    for item in related_manual:
        rel = score_evidence_relevance(item, question=question, visa_code=visa_code, question_type=question_type, immigration_facts=facts, legal_issue_types=issues)
        scored.append({"item": item, "relevance": rel if rel != RELEVANCE_NOT_RELEVANT else RELEVANCE_RELATED})
    for item in laws:
        scored.append({"item": item, "relevance": score_evidence_relevance(item, question=question, visa_code=visa_code, question_type=question_type, immigration_facts=facts, legal_issue_types=issues)})

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

    if not source_type_plan:
        source_type_plan = build_generalized_source_plan(question, facts, issues, law_sources=laws, law_grounding_status=law_grounding_status)
    attempted = list(source_type_plan.get("source_types_attempted") or [])
    returned = list(source_type_plan.get("source_types_returned") or [])
    statuses = dict(source_type_plan.get("statuses") or {})
    risk = _risk_from_issues(issues, risk_level)
    concepts = ["체류자격", "활동범위", "체류자격외활동"]
    if "status_change" in issues:
        concepts.append("체류자격 변경")
    if "reporting_duty" in issues:
        concepts.append("신고의무")
    if "nationality_or_refugee_context" in issues:
        concepts.extend(["국적법", "난민법"])
    concepts.extend(issues[:4])
    concepts = list(dict.fromkeys(concepts))
    missing_direct = direct_count == 0
    authority_summary = f"direct={direct_count}, related={related_count}, analogical={analogical_count}, background={background_count}; " + ("no direct scenario-specific authority found" if missing_direct else "direct authority found")
    analysis = {
        "analysis_mode": mode,
        "main_issue": _main_issue(issues, facts),
        "sub_issues": _sub_issues(issues, facts),
        "legal_issue_types": issues,
        "immigration_facts": facts,
        "relevant_legal_concepts": concepts,
        "source_types_attempted": attempted,
        "source_types_returned": returned,
        "source_type_statuses": statuses,
        "source_plan": source_type_plan,
        "direct_authority": [_authority_stub(i, RELEVANCE_DIRECT) for i in buckets[RELEVANCE_DIRECT][:5]],
        "related_authority": [_authority_stub(i, RELEVANCE_RELATED) for i in buckets[RELEVANCE_RELATED][:5]],
        "analogical_authority": [_authority_stub(i, RELEVANCE_ANALOGICAL) for i in buckets[RELEVANCE_ANALOGICAL][:5]],
        "background_authority": [_authority_stub(i, RELEVANCE_BACKGROUND) for i in buckets[RELEVANCE_BACKGROUND][:5]],
        "missing_direct_authority": missing_direct,
        "risk_posture": risk,
        "confidence": _CONFIDENCE_BY_MODE.get(mode, "limited"),
        "practical_posture": _practical_posture(issues, facts, mode, risk),
        "decisive_facts": [
            "current_status/sub_status", "previous_status/approval_conditions", "target_status/route", "activity category", "paid_or_credit_bearing", "duration/employer_or_school",
        ],
        "official_confirmation_questions": _confirmation_questions(issues, facts, official_confirmation_questions or []),
        "direct_evidence_count": direct_count,
        "related_evidence_count": related_count,
        "analogical_evidence_count": analogical_count,
        "background_evidence_count": background_count,
        "authority_summary": authority_summary,
    }
    analysis["answer_template"] = build_issue_based_answer_template(analysis)
    return analysis


def first_sentence_quality_warning(answer: str) -> str:
    first = (answer or "").strip().split(".", 1)[0].strip().lower()
    if not first:
        return "empty_answer"
    for prefix in ("paradiso cannot verify", "whether you can", "it depends", "specific manual guidance was not found"):
        if first.startswith(prefix):
            return "failure_first_framing"
    return ""
