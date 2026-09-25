"""Deterministic question-understanding contract.

This is NOT a second router. It composes the classifiers Waymaker already
trusts and fills in only the facets they do not produce:

* status / sub-code  <- ``paradiso_backend._detect_visa_codes`` (passed in)
* procedure          <- ``paradiso_backend._detect_task_type`` (passed in),
                        mapped onto canonical procedure keys
* documents intent   <- ``services.legal_analysis.classify_legal_issue_types``
                        (``documents_needed``)
* multiple statuses  <- ``services.immigration_tools.extract_immigration_facts``
* fee / deadline / online / appointment / legal-basis / precedent facets:
  small keyword table below (those facets are not classified anywhere else).

The output is a plain dataclass, so the same object feeds retrieval, the
coverage decision, the query observation and the eval runner.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .models import TASK_TYPE_TO_PROCEDURE, AmbiguityState, Intent

_FACETS = (
    (Intent.CASE_RESEARCH, r"판례|재결|판결|precedent|case\s*law|court\s+decision"),
    (Intent.LEGAL_BASIS, r"법적\s*근거|근거\s*조항|조문|시행령|시행규칙|출입국관리법\s*제|legal\s+basis|which\s+article|statute"),
    (Intent.FEE, r"수수료|비용|얼마|fee|cost|how\s+much"),
    (Intent.DEADLINE, r"언제까지|기한|마감|며칠\s*(?:이내|안)|deadline|by\s+when|how\s+many\s+days"),
    (Intent.ONLINE_APPLICATION, r"온라인|전자민원|인터넷\s*(?:으로|신청)|하이코리아\s*(?:로|에서)\s*신청|online|e-?application"),
    (Intent.APPOINTMENT, r"방문\s*예약|예약|appointment|reservation"),
    (Intent.REENTRY, r"재입국|re-?entry"),
)
_DOCUMENT_RE = re.compile(r"서류|준비물|제출물|구비|document|paperwork|what\s+do\s+i\s+need\s+to\s+(?:submit|bring)", re.I)
_FAMILY_RE = re.compile(r"가족|배우자|자녀|동반|부양|dependent|spouse|child(?:ren)?", re.I)
_ELIGIBILITY_RE = re.compile(r"자격이\s*되|가능한가요|가능해요|할\s*수\s*있나|되나요|eligib|am\s+i\s+allowed|can\s+i\b", re.I)

_PROCEDURE_INTENT = {
    "extension": Intent.EXTENSION, "status_change": Intent.STATUS_CHANGE,
    "registration": Intent.REGISTRATION, "workplace_change": Intent.WORKPLACE_CHANGE,
    "activities_outside_status": Intent.ACTIVITIES_OUTSIDE_STATUS, "reentry": Intent.REENTRY,
    "reporting_duty": Intent.REPORTING_DUTY, "address_report": Intent.REPORTING_DUTY,
    "status_grant": Intent.FAMILY_DEPENDENT,
}
_HIGH_RISK_TASKS = {"status_change", "marriage_divorce_status_change", "overstay_deadline_risk"}
#: Procedures whose document lists a knowledge variant can answer.
GROUNDABLE_TASKS = {"extension": "extension", "status_change": "status_change",
                    "foreigner_registration": "registration", "workplace_change": "workplace_change",
                    "activities_outside_status": "activities_outside_status"}

_HANGUL_RE = re.compile(r"[가-힣]")
_HAN_RE = re.compile(r"[一-鿿]")


@dataclass
class QueryUnderstanding:
    query_language: str
    status_code: Optional[str]
    subcode: Optional[str]
    procedure: Optional[str]
    task_type: Optional[str]
    intent: str
    # Procedure a knowledge variant may answer directly. ``None`` for high-risk
    # task types (overstay, divorce) even when ``procedure`` is set: those must
    # never be answered with a plain procedure checklist.
    retrieval_procedure: Optional[str] = None
    intents: List[str] = field(default_factory=list)
    risk_level: str = "low"
    needs_current_source: bool = False
    needs_law_source: bool = False
    missing_decisive_facts: List[str] = field(default_factory=list)
    ambiguity: str = AmbiguityState.CLEAR.value
    source_requirement: str = "official_manual"
    mentioned_statuses: List[str] = field(default_factory=list)
    legal_issue_types: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def detect_language(text: str, hint: Optional[str] = None) -> str:
    hint = str(hint or "").strip().lower()
    if hint:
        return "zh" if hint.startswith("zh") else hint.split("-")[0]
    if _HANGUL_RE.search(text or ""):
        return "ko"
    if _HAN_RE.search(text or ""):
        return "zh"
    return "en"


def understand(
    text: str,
    *,
    status_code: Optional[str],
    subcode: Optional[str],
    task_type: Optional[str],
    risk_level: str = "low",
    lang: Optional[str] = None,
    legal_issue_types: Optional[Sequence[str]] = None,
) -> QueryUnderstanding:
    """Build the understanding contract from existing detectors' outputs."""
    raw = str(text or "")
    issues = list(legal_issue_types) if legal_issue_types is not None else _classify_issues(raw)
    intents: List[str] = []
    if "documents_needed" in issues or _DOCUMENT_RE.search(raw):
        intents.append(Intent.REQUIRED_DOCUMENTS.value)
    for intent, pattern in _FACETS:
        if re.search(pattern, raw, re.I) and intent.value not in intents:
            intents.append(intent.value)
    if _FAMILY_RE.search(raw):
        intents.append(Intent.FAMILY_DEPENDENT.value)
    procedure = TASK_TYPE_TO_PROCEDURE.get(task_type or "")
    if procedure is None and Intent.REENTRY.value in intents:
        # The backend task detector has no re-entry branch; the facet does.
        procedure = "reentry"
    if procedure and _PROCEDURE_INTENT.get(procedure) and _PROCEDURE_INTENT[procedure].value not in intents:
        intents.append(_PROCEDURE_INTENT[procedure].value)
    if _ELIGIBILITY_RE.search(raw) and Intent.ELIGIBILITY.value not in intents:
        intents.append(Intent.ELIGIBILITY.value)
    primary = intents[0] if intents else Intent.GENERAL_EXPLANATION.value

    mentioned = _mentioned_statuses(raw)
    parents = {_parent(c) for c in mentioned}
    if not status_code and len(parents) == 1:
        # The backend text detector misses codes glued to Korean particles
        # ("D-2에서") and free-text sub-codes ("F-6-3"). Use the single parent
        # family the user named; a sub-code is still never guessed from text
        # (sub-code routing stays a payload-only declaration).
        status_code = next(iter(parents))
    missing: List[str] = []
    ambiguity = AmbiguityState.CLEAR.value
    needs_status = primary in (Intent.REQUIRED_DOCUMENTS.value, Intent.FEE.value, Intent.DEADLINE.value,
                               Intent.ONLINE_APPLICATION.value, Intent.ELIGIBILITY.value) or procedure is not None
    if len(parents) > 1 and not status_code:
        ambiguity = AmbiguityState.MULTIPLE_STATUSES.value
        missing.append("status_code")
    elif needs_status and not status_code:
        ambiguity = AmbiguityState.MISSING_STATUS.value
        missing.append("status_code")
    if primary == Intent.REQUIRED_DOCUMENTS.value and status_code and not procedure:
        ambiguity = AmbiguityState.MISSING_PROCEDURE.value if ambiguity == AmbiguityState.CLEAR.value else ambiguity
        missing.append("procedure")

    return QueryUnderstanding(
        query_language=detect_language(raw, lang),
        status_code=status_code,
        subcode=subcode,
        procedure=procedure,
        task_type=task_type,
        retrieval_procedure=GROUNDABLE_TASKS.get(task_type or "") or ("reentry" if procedure == "reentry" else None),
        intent=primary,
        intents=intents,
        risk_level="high" if task_type in _HIGH_RISK_TASKS else (risk_level or "low"),
        needs_current_source=primary in (Intent.FEE.value, Intent.DEADLINE.value, Intent.ONLINE_APPLICATION.value,
                                         Intent.APPOINTMENT.value),
        needs_law_source=primary in (Intent.LEGAL_BASIS.value,) or task_type in _HIGH_RISK_TASKS,
        missing_decisive_facts=missing,
        ambiguity=ambiguity,
        source_requirement=("law" if primary == Intent.LEGAL_BASIS.value
                            else "precedent_context" if primary == Intent.CASE_RESEARCH.value
                            else "official_manual"),
        mentioned_statuses=mentioned,
        legal_issue_types=issues,
    )


def _parent(code: str) -> str:
    parts = code.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else code


def _classify_issues(text: str) -> List[str]:
    try:
        from services.legal_analysis import classify_legal_issue_types
        return list(classify_legal_issue_types(text) or [])
    except Exception:  # pragma: no cover - classifier is optional context here
        return []


def _mentioned_statuses(text: str) -> List[str]:
    try:
        from services.immigration_tools import extract_immigration_facts
        return list(extract_immigration_facts(text).get("statusCodes") or [])
    except Exception:  # pragma: no cover
        return []
