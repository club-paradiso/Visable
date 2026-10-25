"""Fail-closed pre-provider guard for uncertain immigration classification.

Only syntactic status identity and user-intent ambiguity are checked here.
This module neither determines legal eligibility nor publishes a rule.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Optional

from .knowledge.models import OFFICIAL_STATUS_PARENTS
from .procedure_classifier import classify_procedure
from .status_code_parser import explicit_codes, normalize_explicit, transition_pair


@dataclass(frozen=True)
class ClassificationBlock:
    reason: str
    message: str


_MESSAGES = {
    "unknown_status": (
        "입력된 체류자격 코드를 공식 상위 자격 목록과 대조할 수 없습니다. "
        "체류자격·세부 약호를 확인해 주세요. 확인 전에는 자격별 요건이나 제출서류를 안내하지 않습니다.",
        "I cannot match the status code to a recognized parent category. "
        "Please confirm the status and subcode. Status-specific requirements are withheld until then.",
    ),
    "multiple_statuses": (
        "여러 체류자격이 언급됐지만 어느 자격의 절차를 문의하는지 명확하지 않습니다. "
        "현재 자격과 문의 대상 자격, 신청하려는 절차를 구분해 알려주세요.",
        "Several status codes were mentioned without a clear procedure target. "
        "Please distinguish your current status, target status, and intended procedure.",
    ),
    "conflicting_status_context": (
        "선택된 체류자격과 질문에 적힌 체류자격이 다릅니다. "
        "어느 자격에 대한 안내가 필요한지 확인해 주세요.",
        "The selected status conflicts with the code in the question. "
        "Please confirm which status your question concerns.",
    ),
    "transition_requires_review": (
        "현재 자격과 변경하려는 자격은 구분했지만, 자격변경 가능 여부와 제출서류는 "
        "별도로 확인된 법령·매뉴얼 근거가 있어야 판단할 수 있습니다. "
        "정확한 현재 자격·목표 자격과 신청 상황을 확인해 주세요.",
        "The current and target statuses are distinct, but eligibility and documents for changing "
        "status require separately verified legal and manual evidence. Please confirm the case details.",
    ),
    "passport_service": (
        "여권 발급·갱신 자체와 한국 출입국관서에 하는 여권정보 변경신고는 다른 절차입니다. "
        "어느 쪽을 문의하시는지 알려주세요. 여권 발급 절차를 출입국 신고로 간주하지 않습니다.",
        "Passport issuance or renewal and reporting changed passport information to Korean immigration "
        "are different procedures. Please specify which one you mean.",
    ),
    "card_action_missing": (
        "외국인등록증을 처음 신청하는 건지, 기존 등록증을 재발급받는 건지 확인해 주세요. "
        "두 절차의 서류를 섞어 안내하지 않습니다.",
        "Please clarify whether this is an initial foreigner registration or a replacement card. "
        "The two checklists must not be combined.",
    ),
}


def assess_classification(
    question: str,
    *,
    payload_code: Optional[str] = None,
    visa_data: Optional[Mapping] = None,
    lang: Optional[str] = None,
) -> Optional[ClassificationBlock]:
    """Return a conservative clarification, or None for the normal pipeline.

    This is an interim NO_GO barrier, not an accuracy claim. Valid code syntax
    is not proof that the subcode or status-specific requirement exists.
    """
    codes = explicit_codes(question)
    declared = []
    for value in (payload_code, (visa_data or {}).get("detected_code"), (visa_data or {}).get("code")):
        if isinstance(value, str):
            normalized = normalize_explicit(value)
            if normalized and normalized not in declared:
                declared.append(normalized)
    all_codes = list(dict.fromkeys([*codes, *declared]))
    parents = {"-".join(code.split("-")[:2]) for code in all_codes}
    reason = None
    if any(parent not in OFFICIAL_STATUS_PARENTS for parent in parents):
        reason = "unknown_status"
    elif len(codes) > 1:
        pair = transition_pair(question)
        # Unambiguous changes must keep the existing source-limited fallback
        # and its directional metadata. Only unresolved comparisons are gated.
        directional = bool(len(codes) == 2 and (
            (pair and set(codes) == set(pair))
            or re.search(r"(?:상태인데|현재|체류\s*중).{0,45}(?:로|으로)\s*(?:변경|전환|바꾸|바꿔)", question, re.I)
            # "I'm on D-4 and want to change to D-2" conveys a clear
            # current/target direction even though codes are not adjacent.
            # Require both a current-status cue and an explicit change-to
            # target so mere two-code comparisons stay gated.
            or re.search(
                r"\b(?:on|have|hold|holding|currently\s+on|my\s+(?:current\s+)?(?:visa|status)\s+is)\s+"
                r"(?:an?\s+)?[A-HKM]-?\d{1,2}(?:-[0-9A-Z]{1,4})?\b"
                r".{0,90}?\b(?:change|switch|convert|transition)\s+(?:my\s+(?:visa|status)\s+)?"
                r"to\s+[A-HKM]-?\d{1,2}(?:-[0-9A-Z]{1,4})?\b",
                question, re.I,
            )
        ))
        if not directional:
            reason = "multiple_statuses"
    elif codes and declared and any(
        code != selected and "-".join(code.split("-")[:2]) != "-".join(selected.split("-")[:2])
        for code in codes for selected in declared
    ):
        # A selected parent G-1 and an explicit child G-1-5 are compatible.
        # The caller may also declare the *current* status H-1 while the
        # question explicitly names a *target* F-2-99 ("change to ...").
        # Preserve the existing source-limited transition analysis for that
        # case; do not mislabel it as a conflicting user selection.
        target_clause = bool(re.search(
            r"\b(?:change|switch|convert|transition)\b.{0,25}\bto\b"
            r"|\bto\s+[A-HKM]-?\d"
            r"|(?:로|으로)\s*(?:체류자격\s*)?(?:변경|전환|바꾸|바꿔)",
            question, re.I,
        ))
        if not target_clause:
            reason = "conflicting_status_context"
    else:
        fine = classify_procedure(question)
        if fine.reason == "passport_service_not_immigration":
            reason = "passport_service"
        elif fine.reason == "card_action_missing":
            reason = "card_action_missing"
    if reason is None:
        return None
    ko = str(lang or "").lower().startswith("ko") or (not lang and any("\uac00" <= ch <= "\ud7a3" for ch in question))
    return ClassificationBlock(reason=reason, message=_MESSAGES[reason][0 if ko else 1])
