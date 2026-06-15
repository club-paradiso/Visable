"""Evidence-backed answer-shape contracts and quality gate for Paradiso.

This module is the *final* synthesis-layer guard described in
``docs/data/EVIDENCE_BACKED_ANSWER_SYNTHESIS_GATES_2026_05.md``. The retrieval /
ontology / legal-analysis layers decide *what evidence exists*; this module
decides *whether the produced answer is actually useful* for the detected legal
issue type before it is shown to the user.

Two public concepts:

* ``build_answer_shape_contract(...)`` (Part A) — pick ONE issue-type answer
  shape contract and return the required answer "slots" that a good answer for
  that issue must contain. Contracts are keyed by *legal issue type*, never by a
  specific visa code, so the same contract serves H-1, G-1, E-7, F-2, ...

* ``evaluate_answer_shape(answer, metadata, contract)`` (Part B) — a fully
  deterministic, side-effect-free gate. It inspects the produced answer text
  against the contract + the backend metadata and reports which required slots
  are missing, which generic-avoidance / overconfidence / irrelevant-term /
  source-limitation-placement problems were detected, and a recommended
  ``repair_strategy``.

Nothing here calls an LLM, performs IO, or changes provider/model selection.
Everything is testable offline. The gate is intentionally conservative: it must
catch the production "too vague / confirmation-needed too early / says it is not
based on the manual" failure mode without rewriting genuinely good answers.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

# Bumped when the contract set or gate semantics change in a way the smoke
# harness / frontend should be able to detect.
ANSWER_SHAPE_VERSION = "2026-05-answer-shape-gate-v1"

# ---------------------------------------------------------------------------
# Contract keys (issue-type, NOT visa-code specific)
# ---------------------------------------------------------------------------
CONTRACT_REGISTRATION = "registration_or_residence_report"
CONTRACT_ACTIVITY_SCOPE = "activity_scope"
CONTRACT_WORKPLACE_CHANGE = "workplace_change_addition"
CONTRACT_STATUS_CHANGE = "status_change_route"
CONTRACT_DOCUMENTS = "documents_needed"
CONTRACT_STUDY = "study_on_non_study_status"
CONTRACT_WORK_RESTRICTION = "work_on_non_work_status"
CONTRACT_GENERAL = "legal_general"

# Required answer slots per contract (Part A). Each slot name maps to a
# deterministic detector in ``_SLOT_DETECTORS``. Order is the order we report
# missing slots in.
ANSWER_SHAPE_CONTRACTS: Dict[str, List[str]] = {
    CONTRACT_REGISTRATION: [
        "direct_practical_answer",
        "trigger_event",
        "deadline_basis_or_uncertainty",
        "filing_channel",
        "required_fact_checks",
        "source_confidence",
        "official_confirmation_questions",
    ],
    CONTRACT_ACTIVITY_SCOPE: [
        "practical_risk_posture",
        "current_status_as_primary_basis",
        "proposed_activity_classification",
        "permission_or_change_needed",
        "decisive_facts",
        "source_confidence",
    ],
    CONTRACT_WORKPLACE_CHANGE: [
        "current_status_role",
        "employer_workplace_client_distinction",
        "report_vs_permission_distinction",
        "previous_status_comparative_if_changed",
        "decisive_facts",
        "source_confidence",
    ],
    CONTRACT_STATUS_CHANGE: [
        "current_status",
        "target_status",
        "route_framing",
        "eligibility_without_invented_documents",
        "required_official_confirmation",
        "source_confidence",
    ],
    CONTRACT_DOCUMENTS: [
        "procedure_name",
        "status_or_procedure_target",
        "document_list_or_unavailable_next_action",
        "source_confidence",
    ],
    CONTRACT_STUDY: [
        "current_status_purpose",
        "study_activity_type",
        "study_status_comparison_if_relevant",
        "permission_or_status_change_risk",
        "decisive_facts",
        "source_confidence",
    ],
    CONTRACT_WORK_RESTRICTION: [
        "paid_unpaid_activity_distinction",
        "current_status_allowed_scope",
        "comparison_status_if_relevant",
        "risk_posture",
        "source_confidence",
    ],
    CONTRACT_GENERAL: [
        "direct_practical_answer",
        "source_confidence",
    ],
}

# Issue-type -> contract precedence. The first matching issue (most specific
# first) selects the contract. ``post_status_change_residual_duty`` reuses the
# workplace-change shape because it is fundamentally a "duty after a change"
# question (current status primary, previous status comparative).
_ISSUE_TO_CONTRACT_PRIORITY: Sequence[tuple] = (
    ("post_status_change_residual_duty", CONTRACT_WORKPLACE_CHANGE),
    ("workplace_change_addition", CONTRACT_WORKPLACE_CHANGE),
    ("study_on_non_study_status", CONTRACT_STUDY),
    ("work_on_non_work_status", CONTRACT_WORK_RESTRICTION),
    ("employment_restriction", CONTRACT_WORK_RESTRICTION),
    ("registration_deadline", CONTRACT_REGISTRATION),
    ("deadline_trigger", CONTRACT_REGISTRATION),
    ("registration_or_residence_report", CONTRACT_REGISTRATION),
    ("reporting_duty", CONTRACT_REGISTRATION),
    ("status_change", CONTRACT_STATUS_CHANGE),
    ("documents_needed", CONTRACT_DOCUMENTS),
    ("extension", CONTRACT_DOCUMENTS),
    ("outside_status_activity", CONTRACT_ACTIVITY_SCOPE),
    ("activity_scope", CONTRACT_ACTIVITY_SCOPE),
)

# Contracts whose answers must never drift into study/enrollment wording unless
# the underlying issue/activity is genuinely about study.
_STUDY_FORBIDDEN_FOR = {
    CONTRACT_REGISTRATION,
    CONTRACT_WORKPLACE_CHANGE,
    CONTRACT_WORK_RESTRICTION,
}
# Concrete study terms that are "irrelevant" inside a non-study answer (Part D/E).
_IRRELEVANT_STUDY_TERMS = (
    "계절학기", "여름 계절학기", "학점", "대학 수업", "대학교 수업", "수강", "청강",
    "D-2", "D-4", "summer semester", "summer course", "credit-bearing", "audit course",
)
_IRRELEVANT_WORK_TERMS = (
    "자격외활동", "체류자격외활동", "근로", "보수", "고용주", "계약형태",
    "근무처", "프리랜서", "사업자등록", "paid work", "employer",
    "employment", "contract form", "freelance", "activities outside status",
)


# ---------------------------------------------------------------------------
# Small text helpers
# ---------------------------------------------------------------------------
def _low(text: Optional[str]) -> str:
    return (text or "").lower()


def _has_any(text: str, *needles: str) -> bool:
    low = text.lower()
    return any(n.lower() in low for n in needles)


def _first_nonempty_line(answer: str) -> str:
    for line in (answer or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def _is_korean(answer: str, certainty_meta: Optional[Dict[str, Any]] = None) -> bool:
    return bool(re.search(r"[가-힣]", answer or ""))


def _status_codes_in(text: str) -> List[str]:
    return [m.group(0).upper() for m in re.finditer(r"[A-H]-\d{1,2}(?:-\d{1,3})?", text or "", re.IGNORECASE)]


# Generic-avoidance opening fragments (first line). Multilingual; case-folded.
_AVOIDANCE_OPENINGS = (
    "paradiso cannot verify", "whether you can", "it depends", "this depends",
    "it is difficult to say", "i cannot", "i'm not able", "i am not able",
    "unfortunately", "specific manual guidance was not found",
    "정확히 확인", "정확한 확인", "확인이 필요합니다", "확인이 필요해", "확인하셔야",
    "확인하시기 바랍", "단정하기 어렵", "말씀드리기 어렵", "답변드리기 어렵",
    "경우에 따라 다", "상황에 따라 다", "일률적으로", "정확한 답변을 드리기",
)

# Phrases that explicitly disclaim the manual basis (the production failure mode).
_NOT_BASED_ON_MANUAL = (
    "본 답변은 공식 매뉴얼에 근거하지 않", "공식 매뉴얼에 근거하지 않",
    "검증된 매뉴얼", "매뉴얼에 기반하지 않", "확인된 근거가 없", "근거가 없습니다",
    "not based on verified manual", "not based on the manual",
    "not based on a verified manual", "no verified manual",
    "is not based on verified", "not grounded in",
)

# First-line source-limitation markers (Part G: limitation must not lead).
_SOURCE_LIMITATION_FIRST_MARKERS = (
    "근거하지 않", "매뉴얼에 근거", "직접 근거는 제한", "직접 근거가 제한",
    "직접적인 근거가 없", "출처 조회가 제한", "확인된 직접 근거", "근거가 제한적",
    "cannot verify", "not based on", "source is limited", "source lookup is limited",
    "no direct source", "direct source support",
)

# Confirmation-channel / source-confidence markers.
_CONFIRMATION_CHANNELS = (
    "1345", "hikorea", "하이코리아", "출입국", "관할", "외국인청", "외국인사무소",
    "immigration office", "competent office", "competent immigration",
)
_SOURCE_CONFIDENCE_MARKERS = _CONFIRMATION_CHANNELS + (
    "근거", "source", "confirm", "verify", "official", "확인", "제한적", "limited",
)

# Overconfident wording when certainty is not direct.
_RISKY_CONFIDENCE_EN = (
    "is allowed", "you can", "no need to", "does not require", "guaranteed",
    "will be approved", "will be denied", "automatically", "always", "never",
    "no further", "is permitted",
)
_RISKY_CONFIDENCE_KO = (
    "신고 의무는 없습니다", "신고 의무가 없습니다", "반드시 신고해야 합니다",
    "허용됩니다", "가능합니다", "필요 없습니다", "필요하지 않습니다",
    "더 이상 적용되지 않습니다", "문제되지 않습니다", "걱정하지 않으셔도",
)

# Markers that frame paid work as an outside-status / activity-scope VIOLATION
# (the "it is paid, therefore it is a high-risk outside-status activity" failure
# mode). Multilingual; case-folded for the English markers.
_OUTSIDE_STATUS_VIOLATION_MARKERS = (
    "자격외활동 위반", "자격외활동에 해당", "체류자격 위반", "위반 위험이 높",
    "위반할 위험", "위반에 해당할 위험", "취업활동을 할 수 없", "근로가 허용되지 않",
    "취업이 허용되지 않", "일을 할 수 없",
    "activities outside status", "outside-status activity", "outside status activity",
    "high risk of violating", "violates your status", "not permitted to work",
    "cannot work", "work is not allowed", "not allowed to work",
)
# Nuance acknowledging a work-permitting / work-limited status may allow some
# (short-term, agreement-limited, conditional) paid work. When present alongside
# violation framing, the answer is balanced and the over-broad gate stays quiet.
_WORK_LIMITED_NUANCE_MARKERS = (
    "단기", "협정", "허용될 수", "허용될 수도", "허용되는 범위", "허용 범위",
    "범위 내", "범위 안", "취업이 가능", "조건부", "직종", "근무 기간",
    "may allow", "may permit", "short-term", "agreement", "within the status",
    "within the", "permitted within", "depending on", "job type", "duration",
)


# ---------------------------------------------------------------------------
# Slot detectors (Part A/B). Each takes a context dict and returns bool.
# ---------------------------------------------------------------------------
def _ctx(answer: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    facts = {}
    la = meta.get("legal_analysis") if isinstance(meta.get("legal_analysis"), dict) else {}
    if isinstance(meta.get("immigration_facts"), dict):
        facts = meta.get("immigration_facts")
    elif isinstance(la.get("immigration_facts"), dict):
        facts = la.get("immigration_facts")
    issues = list(meta.get("legal_issue_types") or la.get("legal_issue_types") or [])
    activities = list(meta.get("proposed_activity_type") or facts.get("proposed_activities") or [])
    low = _low(answer)
    return {
        "answer": answer or "",
        "low": low,
        "meta": meta,
        "facts": facts,
        "issues": issues,
        "activities": activities,
        "current": facts.get("current_status") or meta.get("visa_code_detected"),
        "previous": facts.get("previous_status"),
        "target": facts.get("target_status"),
        "is_ko": _is_korean(answer),
        "codes": _status_codes_in(answer),
        "first_line": _first_nonempty_line(answer),
    }


def _slot_direct_practical_answer(c: Dict[str, Any]) -> bool:
    # A direct practical answer means substantive content that does not lead
    # with pure avoidance and is not just a one-line "확인하세요".
    if len(c["answer"].strip()) < 40:
        return False
    if _detect_generic_avoidance(c):
        return False
    return True


def _slot_source_confidence(c: Dict[str, Any]) -> bool:
    return _has_any(c["answer"], *_SOURCE_CONFIDENCE_MARKERS)


def _slot_trigger_event(c: Dict[str, Any]) -> bool:
    return _has_any(
        c["answer"], "입국", "entry", "체류자격 변경", "자격 변경", "status change",
        "주소", "address", "사유", "등록", "발생", "변동",
    )


def _slot_deadline_basis(c: Dict[str, Any]) -> bool:
    if _has_any(c["answer"], "기한", "이내", "유예", "deadline", "days", "within", "마감", "신고 기간", "기간 내"):
        return True
    # Honest uncertainty about the deadline also satisfies the slot.
    return _has_any(c["answer"], "기한은", "기한을", "정확한 기한", "deadline is", "time limit")


def _slot_filing_channel(c: Dict[str, Any]) -> bool:
    return _has_any(c["answer"], *_CONFIRMATION_CHANNELS) or _has_any(c["answer"], "방문", "visit", "신청", "접수")


def _slot_required_fact_checks(c: Dict[str, Any]) -> bool:
    return _has_any(
        c["answer"], "확인할", "확인해야", "확인이 필요", "체류기간", "입국일",
        "fact", "facts to confirm", "사실관계", "확인 사항", "check whether",
    )


def _slot_official_confirmation_questions(c: Dict[str, Any]) -> bool:
    if "?" in c["answer"] or "？" in c["answer"]:
        return True
    return _has_any(c["answer"], "확인 질문", "확인하세요", "문의", "questions to confirm", "ask 1345", "확인하시기")


def _slot_practical_risk_posture(c: Dict[str, Any]) -> bool:
    return _has_any(
        c["answer"], "위험", "risk", "주의", "유의", "자격외활동", "제한", "허가 없이",
        "리스크", "신중", "caution", "may require",
    )


def _parent_code(code: str) -> str:
    m = re.match(r"^([A-H]-\d{1,2})", code or "")
    return m.group(1) if m else (code or "")


def _slot_current_status_primary(c: Dict[str, Any]) -> bool:
    cur = (c["current"] or "").upper()
    if cur and cur in c["answer"].upper():
        return True
    parent = _parent_code(cur)
    if parent and parent in c["answer"].upper():
        return True
    return _has_any(c["answer"], "현재 체류자격", "현재 자격", "current status", "current sojourn")


def _slot_proposed_activity_classification(c: Dict[str, Any]) -> bool:
    return _has_any(
        c["answer"], "활동", "activity", "근로", "취업", "수학", "수강", "사업",
        "인턴", "프리랜서", "부업", "study", "work", "employment", "business",
    )


def _slot_permission_or_change(c: Dict[str, Any]) -> bool:
    return _has_any(
        c["answer"], "자격외활동", "체류자격 변경", "허가", "변경허가", "permission",
        "change of status", "change of sojourn", "prior permission", "사전 허가",
    )


def _slot_decisive_facts(c: Dict[str, Any]) -> bool:
    return _slot_required_fact_checks(c) or _has_any(
        c["answer"], "결정적", "decisive", "좌우", "달라", "depends on", "핵심 사실",
    )


def _slot_current_status_role(c: Dict[str, Any]) -> bool:
    return _slot_current_status_primary(c)


def _slot_employer_distinction(c: Dict[str, Any]) -> bool:
    return _has_any(
        c["answer"], "근무처", "고용주", "사업장", "employer", "workplace", "client",
        "발주처", "거래처", "직장",
    )


def _slot_report_vs_permission(c: Dict[str, Any]) -> bool:
    has_report = _has_any(c["answer"], "신고", "report", "notification")
    has_perm = _has_any(c["answer"], "허가", "permission", "승인", "approval")
    return has_report or has_perm


def _slot_previous_status_comparative(c: Dict[str, Any]) -> bool:
    prev = (c["previous"] or "").upper()
    if not prev:
        return True  # not applicable -> satisfied
    return prev in c["answer"].upper()


def _slot_current_status(c: Dict[str, Any]) -> bool:
    cur = (c["current"] or "").upper()
    if not cur:
        return _has_any(c["answer"], "현재 체류자격", "current status")
    return cur in c["answer"].upper()


def _slot_target_status(c: Dict[str, Any]) -> bool:
    tgt = (c["target"] or "").upper()
    if not tgt:
        return _has_any(c["answer"], "변경", "target", "change to", "전환")
    return tgt in c["answer"].upper()


def _slot_route_framing(c: Dict[str, Any]) -> bool:
    return _has_any(
        c["answer"], "경로", "route", "변경 절차", "절차", "신청", "procedure",
        "체류자격 변경", "change of status", "재외공관", "국내 변경",
    )


def _slot_eligibility_no_invented_docs(c: Dict[str, Any]) -> bool:
    return _has_any(
        c["answer"], "요건", "자격", "조건", "eligibility", "requirement", "서류",
        "documents", "갖추", "충족",
    )


def _slot_required_official_confirmation(c: Dict[str, Any]) -> bool:
    return _slot_filing_channel(c) or _has_any(c["answer"], "확인", "confirm", "문의")


def _slot_procedure_name(c: Dict[str, Any]) -> bool:
    return _has_any(
        c["answer"], "연장", "변경", "신청", "등록", "발급", "재입국",
        "extension", "change", "application", "registration", "issuance", "절차",
    )


def _slot_status_or_procedure_target(c: Dict[str, Any]) -> bool:
    return _slot_current_status(c) or _slot_target_status(c) or _slot_procedure_name(c)


def _slot_document_list_or_unavailable(c: Dict[str, Any]) -> bool:
    if _has_any(c["answer"], "서류", "구비서류", "제출서류", "documents", "checklist", "목록"):
        return True
    # If no document list, an honest "checklist unavailable + next action" works.
    return _has_any(
        c["answer"], "구조화 근거가 제한", "확인하세요", "안내를 확인", "제한적",
        "checklist unavailable", "not available", "확인이 필요",
    )


def _slot_current_status_purpose(c: Dict[str, Any]) -> bool:
    return _slot_current_status_primary(c) or _has_any(c["answer"], "체류 목적", "purpose of stay", "부여 사유")


def _slot_study_activity_type(c: Dict[str, Any]) -> bool:
    return _has_any(
        c["answer"], "학점", "학위", "정규", "청강", "어학", "수강", "계절학기",
        "credit", "degree", "audit", "language", "enrollment", "비학점", "과정",
    )


def _slot_study_status_comparison(c: Dict[str, Any]) -> bool:
    return _has_any(c["answer"], "D-2", "D-4", "유학 체류자격", "study status")


def _slot_permission_or_status_change_risk(c: Dict[str, Any]) -> bool:
    return _slot_permission_or_change(c) or _slot_practical_risk_posture(c)


def _slot_paid_unpaid_distinction(c: Dict[str, Any]) -> bool:
    return _has_any(
        c["answer"], "보수", "유급", "무급", "급여", "임금", "paid", "unpaid",
        "compensation", "wage", "salary", "대가",
    )


def _slot_current_status_allowed_scope(c: Dict[str, Any]) -> bool:
    # Satisfied when the current status is named (scope wording is a bonus, not
    # a hard requirement, so a concise answer still passes).
    return _slot_current_status_primary(c)


def _slot_comparison_status_if_relevant(c: Dict[str, Any]) -> bool:
    # Soft slot: satisfied if the answer mentions ANY comparison status code
    # other than the current one, or explicitly says a different status applies.
    other = [x for x in c["codes"] if x != (c["current"] or "").upper()]
    if other:
        return True
    return _has_any(c["answer"], "다른 체류자격", "별도", "C-4", "단기취업", "different status", "comparison")


def _slot_risk_posture(c: Dict[str, Any]) -> bool:
    return _slot_practical_risk_posture(c)


_SLOT_DETECTORS = {
    "direct_practical_answer": _slot_direct_practical_answer,
    "source_confidence": _slot_source_confidence,
    "trigger_event": _slot_trigger_event,
    "deadline_basis_or_uncertainty": _slot_deadline_basis,
    "filing_channel": _slot_filing_channel,
    "required_fact_checks": _slot_required_fact_checks,
    "official_confirmation_questions": _slot_official_confirmation_questions,
    "practical_risk_posture": _slot_practical_risk_posture,
    "current_status_as_primary_basis": _slot_current_status_primary,
    "proposed_activity_classification": _slot_proposed_activity_classification,
    "permission_or_change_needed": _slot_permission_or_change,
    "decisive_facts": _slot_decisive_facts,
    "current_status_role": _slot_current_status_role,
    "employer_workplace_client_distinction": _slot_employer_distinction,
    "report_vs_permission_distinction": _slot_report_vs_permission,
    "previous_status_comparative_if_changed": _slot_previous_status_comparative,
    "current_status": _slot_current_status,
    "target_status": _slot_target_status,
    "route_framing": _slot_route_framing,
    "eligibility_without_invented_documents": _slot_eligibility_no_invented_docs,
    "required_official_confirmation": _slot_required_official_confirmation,
    "procedure_name": _slot_procedure_name,
    "status_or_procedure_target": _slot_status_or_procedure_target,
    "document_list_or_unavailable_next_action": _slot_document_list_or_unavailable,
    "current_status_purpose": _slot_current_status_purpose,
    "study_activity_type": _slot_study_activity_type,
    "study_status_comparison_if_relevant": _slot_study_status_comparison,
    "permission_or_status_change_risk": _slot_permission_or_status_change_risk,
    "paid_unpaid_activity_distinction": _slot_paid_unpaid_distinction,
    "current_status_allowed_scope": _slot_current_status_allowed_scope,
    "comparison_status_if_relevant": _slot_comparison_status_if_relevant,
    "risk_posture": _slot_risk_posture,
}


# ---------------------------------------------------------------------------
# Cross-cutting detectors (Part B)
# ---------------------------------------------------------------------------
def _detect_generic_avoidance(c: Dict[str, Any]) -> bool:
    first = _low(c["first_line"])
    if not first:
        return True
    for frag in _AVOIDANCE_OPENINGS:
        if first.startswith(frag.lower()):
            return True
    # An answer that is *only* a short "please confirm" line with no analysis.
    stripped = c["answer"].strip()
    if len(stripped) < 60 and _has_any(stripped, "확인하세요", "확인 바랍", "문의하세요", "please confirm"):
        return True
    return False


def _detect_confirmation_overuse(answer: str) -> bool:
    # Overuse of "확인 필요" / "confirm" *without* substantive analysis: a short
    # answer that is essentially a stack of "please confirm" directives. A long,
    # thorough answer that says "확인" several times is fine, so the check is
    # gated on the answer being short and confirm-dominated.
    low = _low(answer)
    confirm_hits = (
        low.count("확인") + low.count("confirm") + low.count("문의")
    )
    if confirm_hits < 3:
        return False
    words = max(1, len(re.findall(r"\S+", answer)))
    return words <= confirm_hits * 6


def _detect_source_limitation_first(answer: str) -> bool:
    first = _low(_first_nonempty_line(answer))
    if not first:
        return False
    return any(marker in first for marker in _SOURCE_LIMITATION_FIRST_MARKERS)


def _detect_says_not_based_on_manual(answer: str, meta: Dict[str, Any]) -> bool:
    has_context = bool(
        meta.get("legal_analysis_exists")
        or meta.get("legal_analysis")
        or meta.get("manual_grounding_status") in {"present", "manual_grounding_available"}
        or (meta.get("direct_evidence_count") or 0) > 0
        or (meta.get("related_evidence_count") or 0) > 0
    )
    if not has_context:
        return False
    return _has_any(answer, *_NOT_BASED_ON_MANUAL)


def _detect_irrelevant_terms(answer: str, contract_key: str, issues: Sequence[str], activities: Sequence[str]) -> List[str]:
    found: List[str] = []
    issue_set = set(issues)
    activity_set = set(activities)
    if contract_key in _STUDY_FORBIDDEN_FOR and not (
        "study_on_non_study_status" in issue_set
        or any(
            a in activity_set
            for a in ("credit_bearing_study", "formal_enrollment", "non_credit_audit", "language_training")
        )
    ):
        found.extend(t for t in _IRRELEVANT_STUDY_TERMS if t in (answer or ""))
    if contract_key == CONTRACT_REGISTRATION and not (
        issue_set & {"work_on_non_work_status", "outside_status_activity", "employment_restriction", "workplace_change_addition"}
        or activity_set & {
            "paid_work", "paid_internship", "freelance_work", "side_job",
            "additional_employment", "business_activity", "workplace_change",
            "workplace_addition",
        }
    ):
        found.extend(t for t in _IRRELEVANT_WORK_TERMS if t in (answer or ""))
    return list(dict.fromkeys(found))


def _korean_date_label(iso_date: str) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", iso_date or "")
    if not m:
        return ""
    return f"{int(m.group(1))}년 {int(m.group(2))}월 {int(m.group(3))}일"


def _detect_missing_registration_deadline_date(c: Dict[str, Any], contract_key: str) -> bool:
    if contract_key != CONTRACT_REGISTRATION:
        return False
    deadline = str((c.get("facts") or {}).get("registration_deadline_date") or "").strip()
    if not deadline:
        return False
    return deadline not in (c["answer"] or "") and _korean_date_label(deadline) not in (c["answer"] or "")


def _detect_asks_for_provided_entry_date(c: Dict[str, Any], contract_key: str) -> bool:
    if contract_key != CONTRACT_REGISTRATION:
        return False
    if not (c.get("facts") or {}).get("entry_date"):
        return False
    answer = c["answer"] or ""
    return bool(re.search(r"(입국일|entry date).{0,16}(알려|제공|필요|입력|언제|provide|needed|required)", answer, re.IGNORECASE))


def _work_capability_for(code: Optional[str]) -> str:
    """Work capability for the current status (parent-level), gate-safe.

    Delegates to the shared ``legal_analysis.status_work_capability`` model so the
    gate and the issue classifier agree on which statuses may permit work. Imports
    lazily and never raises (the gate must never break /api/ask)."""
    try:
        from .legal_analysis import status_work_capability

        parent = _parent_code((code or "").upper())
        return status_work_capability(parent)
    except Exception:  # pragma: no cover - defensive only
        return "unknown"


_WORK_ACTIVITY_NAMES = {
    "paid_work", "paid_internship", "freelance_work", "side_job",
    "additional_employment", "business_activity", "workplace_change",
    "workplace_addition",
}
_WORK_ISSUE_NAMES = {
    "work_on_non_work_status", "outside_status_activity",
    "employment_restriction", "activity_scope",
}


def _detect_overbroad_paid_work_outside_status(c: Dict[str, Any], contract_key: str) -> bool:
    """Catch the "paid => outside-status risk" failure for work-permitting statuses.

    Fires only for work/activity-scope contracts where the current status may
    actually permit work (work_authorized / work_limited, e.g. H-1 Working
    Holiday) AND the answer frames paid work as a high-risk outside-status
    violation WITHOUT the nuance that the status may allow short-term /
    agreement-limited work. Statuses where paid work genuinely is outside status
    (study/visit statuses) are excluded, so honest violation framing is kept.
    """
    if contract_key not in (CONTRACT_WORK_RESTRICTION, CONTRACT_ACTIVITY_SCOPE):
        return False
    is_work_question = bool(
        set(c.get("activities") or []) & _WORK_ACTIVITY_NAMES
        or set(c.get("issues") or []) & _WORK_ISSUE_NAMES
    )
    if not is_work_question:
        return False
    if _work_capability_for(c.get("current")) not in ("work_authorized", "work_limited"):
        return False
    answer = c["answer"]
    if not _has_any(answer, *_OUTSIDE_STATUS_VIOLATION_MARKERS):
        return False
    return not _has_any(answer, *_WORK_LIMITED_NUANCE_MARKERS)


def _detect_overconfidence(answer: str, certainty: str) -> List[str]:
    if str(certainty or "").lower() == "direct":
        return []
    low = _low(answer)
    found: List[str] = []
    for phrase in _RISKY_CONFIDENCE_EN:
        if phrase in low:
            found.append(phrase)
    for phrase in _RISKY_CONFIDENCE_KO:
        if phrase in (answer or ""):
            found.append(phrase)
    return found


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def select_contract_key(legal_issue_types: Sequence[str]) -> str:
    """Pick the single primary answer-shape contract for the detected issues."""
    issues = set(legal_issue_types or [])
    for issue, contract in _ISSUE_TO_CONTRACT_PRIORITY:
        if issue in issues:
            return contract
    return CONTRACT_GENERAL


def build_answer_shape_contract(
    *,
    legal_issue_types: Sequence[str],
    immigration_facts: Optional[Dict[str, Any]] = None,
    answer_certainty_level: str = "",
    question_type: str = "",
) -> Dict[str, Any]:
    """Return the issue-type answer-shape contract (Part A).

    The contract is a small, JSON-serializable description of the required
    answer slots for the detected legal issue type, plus the contract key and
    certainty so the gate and the deterministic synthesizer agree.
    """
    facts = immigration_facts or {}
    contract_key = select_contract_key(legal_issue_types)
    required = list(ANSWER_SHAPE_CONTRACTS.get(contract_key, ANSWER_SHAPE_CONTRACTS[CONTRACT_GENERAL]))

    # Prune slots that genuinely do not apply to this fact pattern so the gate
    # does not demand, e.g., a previous-status comparison when no status change
    # happened, or a target status when none was asked.
    if contract_key == CONTRACT_WORKPLACE_CHANGE and not facts.get("previous_status"):
        required = [s for s in required if s != "previous_status_comparative_if_changed"]
    if contract_key == CONTRACT_STATUS_CHANGE and not facts.get("target_status"):
        required = [s for s in required if s != "target_status"]

    return {
        "contract_key": contract_key,
        "required_slots": required,
        "answer_certainty_level": answer_certainty_level or "",
        "question_type": question_type or "",
        "answer_shape_version": ANSWER_SHAPE_VERSION,
        "study_terms_forbidden": contract_key in _STUDY_FORBIDDEN_FOR,
    }


def evaluate_answer_shape(
    answer: str,
    metadata: Dict[str, Any],
    answer_shape_contract: Dict[str, Any],
) -> Dict[str, Any]:
    """Deterministic answer-shape quality gate (Part B).

    Returns a JSON-serializable dict::

        {
          "passed": bool,
          "warnings": [...],
          "missing_slots": [...],
          "repair_strategy": "retry_model" | "deterministic_synthesis" | "source_limited_note",
          "contract_key": "...",
        }

    The gate never raises and never mutates inputs.
    """
    meta = metadata or {}
    contract = answer_shape_contract or {}
    contract_key = contract.get("contract_key") or CONTRACT_GENERAL
    required = list(contract.get("required_slots") or [])
    certainty = contract.get("answer_certainty_level") or meta.get("answer_certainty_level") or ""

    c = _ctx(answer, meta)
    warnings: List[str] = []
    missing_slots: List[str] = []

    # 1) Required-slot coverage.
    for slot in required:
        detector = _SLOT_DETECTORS.get(slot)
        if detector is None:
            continue
        try:
            present = bool(detector(c))
        except Exception:  # pragma: no cover - detectors must never break the gate
            present = True
        if not present:
            missing_slots.append(slot)

    # 2) Generic avoidance opening / missing direct practical answer.
    if _detect_generic_avoidance(c):
        warnings.append("generic_avoidance_opening")
    if not _slot_direct_practical_answer(c):
        warnings.append("missing_direct_practical_answer")

    # 3) Overuse of "확인 필요" without analysis.
    if _detect_confirmation_overuse(answer):
        warnings.append("confirmation_overuse_without_analysis")

    # 4) Source limitation placed before the practical analysis (Part G).
    if _detect_source_limitation_first(answer):
        warnings.append("source_limitation_first_line")

    # 5) Says "not based on manual" despite structured/manual context existing.
    if _detect_says_not_based_on_manual(answer, meta):
        warnings.append("claims_not_based_on_manual_despite_context")

    # 6) Forbidden irrelevant (study) terms for a non-study contract.
    irrelevant = _detect_irrelevant_terms(answer, contract_key, c["issues"], c["activities"])
    if irrelevant:
        warnings.append("irrelevant_terms:%s" % ",".join(irrelevant))

    # 7) Overconfident language while certainty is limited.
    overconf = _detect_overconfidence(answer, certainty)
    if overconf:
        warnings.append("overconfident_language:%s" % ",".join(overconf[:6]))

    # 7b) Paid work framed as an outside-status violation for a status that may
    #     actually permit work (work-limited / work-authorized). This is the H-1
    #     interpreter failure mode: "it is paid, therefore high risk of violating
    #     activity scope" without distinguishing job type / duration / agreement.
    overbroad_paid_work = _detect_overbroad_paid_work_outside_status(c, contract_key)
    if overbroad_paid_work:
        warnings.append("paid_work_treated_as_outside_status_for_work_permitting_status")

    # 7c) Registration-deadline questions with a known entry date must answer
    #     the calculated date directly and must not ask the user to provide the
    #     same entry date again.
    missing_registration_deadline_date = _detect_missing_registration_deadline_date(c, contract_key)
    if missing_registration_deadline_date:
        warnings.append("missing_calculated_registration_deadline")
    asks_for_entry_date = _detect_asks_for_provided_entry_date(c, contract_key)
    if asks_for_entry_date:
        warnings.append("asks_for_entry_date_already_provided")

    # 8) Missing current status / activity classification / decisive facts /
    #    source confidence (cross-contract minimums, reported as warnings too).
    if c["current"] and not _slot_current_status_primary(c):
        warnings.append("missing_current_status")
    if not _slot_source_confidence(c):
        warnings.append("missing_source_confidence")

    # Decide pass/fail + repair strategy.
    # "Hard" failures mean the answer is a non-answer or unsafe: generic
    # avoidance, no practical answer, wrong framing/ordering, overbroad/unsafe
    # claims, a missing computed deadline, asking for already-provided facts, or
    # off-topic terms. These are legitimately replaced by deterministic synthesis.
    hard_fail = bool(
        "generic_avoidance_opening" in warnings
        or "missing_direct_practical_answer" in warnings
        or "claims_not_based_on_manual_despite_context" in warnings
        or "source_limitation_first_line" in warnings
        or "confirmation_overuse_without_analysis" in warnings
        or overbroad_paid_work
        or missing_registration_deadline_date
        or asks_for_entry_date
        or irrelevant
    )
    # A substantive, on-topic answer that merely misses >= 2 structured template
    # slots is NOT a non-answer. Keep the model's real answer (soft source note)
    # instead of slamming it into the deterministic preparation note — this stops
    # good model answers from being replaced by an alarming "출처 제한 / 준비 메모"
    # template just because they did not hit every slot in our checklist.
    slot_shortfall_only = (len(missing_slots) >= 2) and not hard_fail
    soft_only = bool((overconf or missing_slots) and not hard_fail and not slot_shortfall_only)

    passed = not (hard_fail or slot_shortfall_only or soft_only)

    if hard_fail:
        repair_strategy = "deterministic_synthesis"
    elif slot_shortfall_only or soft_only:
        repair_strategy = "source_limited_note"
    else:
        repair_strategy = "retry_model"

    return {
        "passed": passed,
        "warnings": warnings,
        "missing_slots": missing_slots,
        "repair_strategy": repair_strategy,
        "contract_key": contract_key,
    }
