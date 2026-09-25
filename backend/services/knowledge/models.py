"""Waymaker Knowledge Platform — domain vocabulary and boundary schemas.

Every enum here is a stable machine-readable code. None of them is product
copy: public wording lives in the renderer / i18n layer, never in these values.

Authority vocabulary is NOT redefined here: it is
``services.immigration_tools.AuthorityType`` and its ``AUTHORITY_RANK`` — the
canonical source hierarchy documented in
docs/ai/IMMIGRATION_INTELLIGENCE_ARCHITECTURE.md §5.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from services.immigration_tools import AUTHORITY_RANK, AuthorityType

KNOWLEDGE_PLATFORM_VERSION = "2026-09-knowledge-platform-v1"


# ---------------------------------------------------------------------------
# Trust lifecycle
# ---------------------------------------------------------------------------
class LifecycleState(str, Enum):
    DRAFT = "DRAFT"
    AI_EXTRACTED = "AI_EXTRACTED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    VERIFIED = "VERIFIED"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"
    REJECTED = "REJECTED"


#: The only states a fact may be created in.
PROPOSAL_STATES = frozenset({
    LifecycleState.DRAFT, LifecycleState.AI_EXTRACTED, LifecycleState.HUMAN_REVIEW_REQUIRED,
})
#: Pending review (what the review queue shows).
PENDING_STATES = frozenset({
    LifecycleState.DRAFT, LifecycleState.AI_EXTRACTED,
    LifecycleState.HUMAN_REVIEW_REQUIRED, LifecycleState.HUMAN_REVIEWED, LifecycleState.VERIFIED,
})
#: Only this state is production-authoritative for current answers.
AUTHORITATIVE_STATES = frozenset({LifecycleState.PUBLISHED})
#: States a historical (as-of) query may return.
HISTORICAL_STATES = frozenset({LifecycleState.PUBLISHED, LifecycleState.SUPERSEDED})


class SourceVersionStatus(str, Enum):
    ACTIVE = "active"
    STAGED = "staged"                  # registered, content not yet approved
    SUPERSEDED = "superseded"
    FUTURE_EFFECTIVE = "future_effective"
    WITHDRAWN = "withdrawn"


class SourceRefreshState(str, Enum):
    CURRENT = "current"
    REFRESH_DUE = "refresh_due"
    SUPERSEDED = "superseded"
    UNAVAILABLE = "unavailable"


class ReviewerKind(str, Enum):
    HUMAN_OPERATOR = "human_operator"
    # Pre-platform human verification recorded in the repository (e.g. the
    # stay-manual grounding's "verified_locally" page recheck). Shown to
    # operators as distinct from a Knowledge Studio review.
    LEGACY_REPOSITORY_VERIFICATION = "legacy_repository_verification"


class ActorKind(str, Enum):
    HUMAN_OPERATOR = "human_operator"
    LEGACY_IMPORT = "legacy_import"
    PARSER = "parser"
    AI_EXTRACTOR = "ai_extractor"
    SYSTEM = "system"


class FactOrigin(str, Enum):
    LEGACY_REPOSITORY_VERIFIED = "legacy_repository_verified"
    OPERATOR_MANUAL = "operator_manual"
    AI_EXTRACTION = "ai_extraction"
    PARSER_EXTRACTION = "parser_extraction"


class FactProperty(str, Enum):
    REQUIRED_DOCUMENT = "required_document"
    ELIGIBILITY_RULE = "eligibility_rule"
    FEE = "fee"
    DEADLINE = "deadline"
    APPOINTMENT = "appointment"
    ONLINE_SERVICE = "online_service"
    REPORTING_DUTY = "reporting_duty"
    EXCEPTION = "exception"
    CONDITION = "condition"
    PROCEDURAL_NOTE = "procedural_note"


class ConditionKind(str, Enum):
    ALWAYS = "always"
    CONDITIONAL = "conditional"
    APPLICANT_SPECIFIC = "applicant_specific"
    OFFICE_DISCRETION = "office_discretion"


class RequirementLevel(str, Enum):
    """Presentation bucket of a document fact (matches structured_answer buckets)."""

    COMMON = "common"
    REQUIRED = "required"
    CONDITIONAL = "conditional"
    ADDITIONAL = "additional"


# ---------------------------------------------------------------------------
# Procedures (canonical keys). Stay vs visa scope must never mix.
# ---------------------------------------------------------------------------
STAY_PROCEDURES: Dict[str, str] = {
    "extension": "체류기간 연장허가",
    "status_change": "체류자격 변경허가",
    "registration": "외국인등록",
    "reentry": "재입국허가",
    "activities_outside_status": "체류자격외 활동허가",
    "workplace_change": "근무처 변경·추가",
    "status_grant": "체류자격 부여",
    "address_report": "체류지 변경신고",
    "reporting_duty": "신고의무",
}
VISA_PROCEDURES: Dict[str, str] = {
    "visa_issuance": "사증발급",
    "visa_issuance_confirmation": "사증발급인정서",
}
ALL_PROCEDURES: Dict[str, str] = {**STAY_PROCEDURES, **VISA_PROCEDURES}

#: Legacy task types from paradiso_backend._detect_task_type -> canonical procedure.
TASK_TYPE_TO_PROCEDURE: Dict[str, str] = {
    "extension": "extension",
    "status_change": "status_change",
    "foreigner_registration": "registration",
    "workplace_change": "workplace_change",
    "activities_outside_status": "activities_outside_status",
    "address_report": "address_report",
    "passport_info_report": "reporting_duty",
    "family_status_change": "status_grant",
    "marriage_divorce_status_change": "status_change",
    "academic_status_change": "reporting_duty",
    "overstay_deadline_risk": "extension",
}


def procedure_family(procedure: str) -> Optional[str]:
    if procedure in STAY_PROCEDURES:
        return "stay"
    if procedure in VISA_PROCEDURES:
        return "visa"
    return None


# ---------------------------------------------------------------------------
# Question understanding
# ---------------------------------------------------------------------------
class Intent(str, Enum):
    REQUIRED_DOCUMENTS = "required_documents"
    ELIGIBILITY = "eligibility"
    EXTENSION = "extension"
    STATUS_CHANGE = "status_change"
    REGISTRATION = "registration"
    WORKPLACE_CHANGE = "workplace_change"
    ACTIVITIES_OUTSIDE_STATUS = "activities_outside_status"
    DEADLINE = "deadline"
    FEE = "fee"
    ONLINE_APPLICATION = "online_application"
    APPOINTMENT = "appointment"
    REPORTING_DUTY = "reporting_duty"
    REENTRY = "reentry"
    FAMILY_DEPENDENT = "family_dependent"
    LEGAL_BASIS = "legal_basis"
    CASE_RESEARCH = "case_research"
    GENERAL_EXPLANATION = "general_explanation"


#: Which fact property answers an intent directly.
INTENT_PROPERTY: Dict[str, str] = {
    Intent.REQUIRED_DOCUMENTS.value: FactProperty.REQUIRED_DOCUMENT.value,
    Intent.ELIGIBILITY.value: FactProperty.ELIGIBILITY_RULE.value,
    Intent.FEE.value: FactProperty.FEE.value,
    Intent.DEADLINE.value: FactProperty.DEADLINE.value,
    Intent.ONLINE_APPLICATION.value: FactProperty.ONLINE_SERVICE.value,
    Intent.APPOINTMENT.value: FactProperty.APPOINTMENT.value,
    Intent.REPORTING_DUTY.value: FactProperty.REPORTING_DUTY.value,
}


class AmbiguityState(str, Enum):
    CLEAR = "clear"
    MISSING_STATUS = "missing_status"
    MISSING_PROCEDURE = "missing_procedure"
    MISSING_SUBCODE = "missing_subcode"
    MULTIPLE_STATUSES = "multiple_statuses"


# ---------------------------------------------------------------------------
# Coverage decision
# ---------------------------------------------------------------------------
class CoverageState(str, Enum):
    DIRECT_VERIFIED = "DIRECT_VERIFIED"
    VERIFIED_WITH_CONDITIONS = "VERIFIED_WITH_CONDITIONS"
    PARTIAL_VERIFIED = "PARTIAL_VERIFIED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    CONFLICTING_SOURCES = "CONFLICTING_SOURCES"
    OUTDATED_SOURCE = "OUTDATED_SOURCE"
    NO_DIRECT_SOURCE = "NO_DIRECT_SOURCE"
    UNKNOWN = "UNKNOWN"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"        # not a knowledge question (e.g. case research)


class AnswerPath(str, Enum):
    DETERMINISTIC_STRUCTURED = "deterministic_structured"
    DETERMINISTIC_WITH_CONDITIONS = "deterministic_with_conditions"
    BOUNDED_SYNTHESIS = "bounded_synthesis"
    ASK_CLARIFICATION = "ask_clarification"
    EXPLAIN_CONFLICT = "explain_conflict"
    LIMITED_GUIDANCE = "limited_guidance"
    SAFE_FALLBACK = "safe_fallback"
    EXISTING_PIPELINE = "existing_pipeline"   # outside platform scope; unchanged legacy behaviour


class GapReason(str, Enum):
    """Stable coverage-gap reason codes. Not product copy."""

    NO_VERIFIED_KNOWLEDGE = "NO_VERIFIED_KNOWLEDGE"
    NO_DIRECT_AUTHORITY = "NO_DIRECT_AUTHORITY"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    SOURCE_OUTDATED = "SOURCE_OUTDATED"
    UNKNOWN_STATUS = "UNKNOWN_STATUS"
    UNKNOWN_SUBCODE = "UNKNOWN_SUBCODE"
    UNKNOWN_PROCEDURE = "UNKNOWN_PROCEDURE"
    RETRIEVAL_LOW_CONFIDENCE = "RETRIEVAL_LOW_CONFIDENCE"
    RETRIEVAL_FAILED = "RETRIEVAL_FAILED"
    ANSWER_GUARD_FAILURE = "ANSWER_GUARD_FAILURE"
    UNSUPPORTED_CITATION = "UNSUPPORTED_CITATION"
    USER_REPORTED_INCORRECT = "USER_REPORTED_INCORRECT"
    USER_REPORTED_INCOMPLETE = "USER_REPORTED_INCOMPLETE"
    USER_REPORTED_OUTDATED = "USER_REPORTED_OUTDATED"


#: Reasons shown on the "unknown queries" operator surface.
UNKNOWN_QUERY_REASONS = frozenset({
    GapReason.NO_VERIFIED_KNOWLEDGE.value, GapReason.NO_DIRECT_AUTHORITY.value,
    GapReason.UNKNOWN_STATUS.value, GapReason.UNKNOWN_SUBCODE.value,
    GapReason.UNKNOWN_PROCEDURE.value, GapReason.RETRIEVAL_LOW_CONFIDENCE.value,
})


class FeedbackReason(str, Enum):
    INCORRECT = "INCORRECT"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    TOO_LONG = "TOO_LONG"
    HARD_TO_UNDERSTAND = "HARD_TO_UNDERSTAND"
    SOURCE_PROBLEM = "SOURCE_PROBLEM"
    MISUNDERSTOOD_QUESTION = "MISUNDERSTOOD_QUESTION"
    OUTDATED = "OUTDATED"
    OTHER = "OTHER"
    HELPFUL = "HELPFUL"


#: Feedback that points at the knowledge (and therefore feeds the gap queue).
FEEDBACK_GAP_REASON: Dict[str, str] = {
    FeedbackReason.INCORRECT.value: GapReason.USER_REPORTED_INCORRECT.value,
    FeedbackReason.MISSING_INFORMATION.value: GapReason.USER_REPORTED_INCOMPLETE.value,
    FeedbackReason.SOURCE_PROBLEM.value: GapReason.UNSUPPORTED_CITATION.value,
    FeedbackReason.OUTDATED.value: GapReason.USER_REPORTED_OUTDATED.value,
}


class ReviewAction(str, Enum):
    START_REVIEW = "start_review"          # DRAFT/AI_EXTRACTED -> HUMAN_REVIEW_REQUIRED
    APPROVE = "approve"                    # -> HUMAN_REVIEWED
    VERIFY = "verify"                      # HUMAN_REVIEWED -> VERIFIED
    PUBLISH = "publish"                    # VERIFIED -> PUBLISHED (transactional supersede)
    REJECT = "reject"
    NEEDS_EVIDENCE = "needs_evidence"
    EDIT = "edit"                          # new proposal version
    WITHDRAW = "withdraw"                  # PUBLISHED -> WITHDRAWN


class ChangeKind(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    CHANGED = "CHANGED"
    UNCHANGED = "UNCHANGED"


class ConflictKind(str, Enum):
    VALUE_MISMATCH = "value_mismatch"
    AUTHORITY_CONTRADICTION = "authority_contradiction"
    VERSION_CONTRADICTION = "version_contradiction"
    TEMPORAL_OVERLAP = "temporal_overlap"


class PipelineError(str, Enum):
    """Internal pipeline error codes (operator-visible, never public copy)."""

    SOURCE_FETCH_FAILED = "SOURCE_FETCH_FAILED"
    SOURCE_PARSE_FAILED = "SOURCE_PARSE_FAILED"
    EXTRACTION_INVALID = "EXTRACTION_INVALID"
    SOURCE_LOCATION_INVALID = "SOURCE_LOCATION_INVALID"
    UNSUPPORTED_STATUS = "UNSUPPORTED_STATUS"
    UNKNOWN_PROCEDURE = "UNKNOWN_PROCEDURE"
    PROCEDURE_SCOPE_MISMATCH = "PROCEDURE_SCOPE_MISMATCH"
    MALFORMED_VALUE = "MALFORMED_VALUE"
    DUPLICATE_FACT = "DUPLICATE_FACT"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    PUBLISH_FAILED = "PUBLISH_FAILED"
    RETRIEVAL_INCOMPLETE = "RETRIEVAL_INCOMPLETE"
    EVAL_FAILED = "EVAL_FAILED"
    TRANSITION_FORBIDDEN = "TRANSITION_FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"


class KnowledgeError(Exception):
    """A pipeline failure with a stable code (operator-visible)."""

    def __init__(self, code: PipelineError, message: str, *, detail: Optional[Dict[str, Any]] = None):
        super().__init__(f"{code.value}: {message}")
        self.code = code
        self.message = message
        self.detail = detail or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.code.value, "message": self.message, "detail": self.detail}


class EvalAssertionType(str, Enum):
    MUST_INCLUDE_FACT = "MUST_INCLUDE_FACT"
    MUST_NOT_INCLUDE_FACT = "MUST_NOT_INCLUDE_FACT"
    SOURCE_MUST_BE = "SOURCE_MUST_BE"
    SOURCE_MUST_NOT_BE = "SOURCE_MUST_NOT_BE"
    EXPECTED_STATUS = "EXPECTED_STATUS"
    EXPECTED_SUBCODE = "EXPECTED_SUBCODE"
    EXPECTED_PROCEDURE = "EXPECTED_PROCEDURE"
    EXPECTED_INTENT = "EXPECTED_INTENT"
    EXPECTED_COVERAGE_STATE = "EXPECTED_COVERAGE_STATE"
    EXPECTED_BUCKET = "EXPECTED_BUCKET"            # value: {"item": "...", "bucket": "conditional"}
    MUST_CLARIFY = "MUST_CLARIFY"
    MUST_NOT_CLARIFY = "MUST_NOT_CLARIFY"
    MUST_RECORD_GAP = "MUST_RECORD_GAP"
    MUST_NOT_RECORD_GAP = "MUST_NOT_RECORD_GAP"
    MUST_NOT_CLAIM_CERTAINTY = "MUST_NOT_CLAIM_CERTAINTY"
    MUST_NOT_LEAK_INTERNAL_METADATA = "MUST_NOT_LEAK_INTERNAL_METADATA"
    MUST_NOT_LEAK_MODEL_PROVIDER = "MUST_NOT_LEAK_MODEL_PROVIDER"
    LANGUAGE_EXPECTED = "LANGUAGE_EXPECTED"


# ---------------------------------------------------------------------------
# Identity helpers
# ---------------------------------------------------------------------------
_CODE_RE = re.compile(r"^[A-Z]-\d{1,2}(?:-[0-9A-Z]{1,4})*$|^[A-Z]-\d{1,2}-T$")
_PAREN_RE = re.compile(r"\([^()]*\)|（[^（）]*）")
_WS_RE = re.compile(r"\s+")


def is_valid_status_code(code: Optional[str]) -> bool:
    return bool(code) and bool(_CODE_RE.match(str(code)))


def parent_code(code: str) -> str:
    parts = code.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else code


def variant_key(status_code: str, subcode: Optional[str], procedure: str, scenario: str = "general") -> str:
    return f"{status_code}|{subcode or '*'}|{procedure}|{scenario or 'general'}"


def normalize_item_key(text: str) -> str:
    """Identity of a document/rule item independent of its annotations.

    '신청서 (별지 34호 서식)' and '신청서' share the key '신청서', so a wording
    change between manual editions reads as CHANGED rather than REMOVED+ADDED.
    """
    base = _PAREN_RE.sub("", str(text or ""))
    base = base.split("—", 1)[0]
    base = _WS_RE.sub("", base).strip(" .,:;").lower()
    return base or _WS_RE.sub("", str(text or "")).lower()


def slot_key(variant: str, prop: str, item: str) -> str:
    return f"{variant}|{prop}|{item}"


def authority_rank(authority: str) -> int:
    try:
        return AUTHORITY_RANK[AuthorityType(authority)]
    except (ValueError, KeyError):
        return 99


# ---------------------------------------------------------------------------
# Boundary schemas (validated at every API / ingestion boundary)
# ---------------------------------------------------------------------------
class SourceLocation(BaseModel):
    source_version_id: str = Field(min_length=1)
    section_title: str = ""
    page_start: Optional[int] = Field(default=None, gt=0)
    page_end: Optional[int] = Field(default=None, gt=0)
    locator: str = ""
    evidence_excerpt: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def _page_order(self) -> "SourceLocation":
        if self.page_start and self.page_end and self.page_end < self.page_start:
            raise ValueError("page_end must be >= page_start")
        if self.page_end and not self.page_start:
            raise ValueError("page_end requires page_start")
        return self


class FactProposal(BaseModel):
    """A proposed fact from any origin (operator, parser, AI extractor)."""

    status_code: str
    subcode: Optional[str] = None
    subcodes_covered: List[str] = Field(default_factory=list)
    procedure: str
    scenario: str = "general"
    section_title: str = ""
    property: FactProperty
    value_text: str = Field(min_length=1, max_length=2000)
    item_key: Optional[str] = None
    requirement_level: Optional[RequirementLevel] = None
    condition_kind: ConditionKind = ConditionKind.ALWAYS
    condition_text: str = Field(default="", max_length=1000)
    display_translations: Dict[str, str] = Field(default_factory=dict)
    sort_order: int = 0
    authority_type: AuthorityType = AuthorityType.APPROVED_MANUAL
    origin: FactOrigin
    extraction_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    extraction_warnings: List[str] = Field(default_factory=list)
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    location: SourceLocation

    @field_validator("status_code")
    @classmethod
    def _status(cls, v: str) -> str:
        v = str(v or "").strip().upper()
        if not is_valid_status_code(v) or len(v.split("-")) != 2:
            raise ValueError("status_code must be a parent code like 'D-2'")
        return v

    @field_validator("subcode")
    @classmethod
    def _subcode(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return None
        v = str(v).strip().upper()
        if not is_valid_status_code(v) or len(v.split("-")) < 3:
            raise ValueError("subcode must look like 'D-4-1'")
        return v

    @field_validator("value_text")
    @classmethod
    def _value(cls, v: str) -> str:
        v = " ".join(str(v or "").split())
        if not v:
            raise ValueError("value_text is empty")
        if "<" in v and re.search(r"<\s*/?\s*[a-zA-Z]", v):
            raise ValueError("value_text must not contain markup")
        return v

    @field_validator("effective_from", "effective_to")
    @classmethod
    def _date(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return None
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(v)):
            raise ValueError("dates must be YYYY-MM-DD")
        return str(v)

    @model_validator(mode="after")
    def _consistency(self) -> "FactProposal":
        if self.subcode and not self.subcode.startswith(self.status_code + "-"):
            raise ValueError("subcode must belong to status_code (no cross-family sub-codes)")
        for code in self.subcodes_covered:
            if not str(code).startswith(self.status_code + "-"):
                raise ValueError("subcodes_covered must belong to status_code")
        if self.procedure not in ALL_PROCEDURES:
            raise ValueError(f"unknown procedure {self.procedure!r}")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to precedes effective_from")
        if self.condition_kind != ConditionKind.ALWAYS and not self.condition_text and \
                self.property != FactProperty.REQUIRED_DOCUMENT:
            raise ValueError("a conditional fact needs condition_text")
        return self


class ReviewActionRequest(BaseModel):
    action: ReviewAction
    reason: str = Field(default="", max_length=2000)
    # EDIT only: replacement fields (anything omitted keeps the current value).
    value_text: Optional[str] = Field(default=None, max_length=2000)
    condition_kind: Optional[ConditionKind] = None
    condition_text: Optional[str] = Field(default=None, max_length=1000)
    requirement_level: Optional[RequirementLevel] = None
    effective_from: Optional[str] = None
    # PUBLISH only: explicit supersede target (defaults to the slot's current fact).
    supersedes_fact_id: Optional[str] = None


class EvalAssertion(BaseModel):
    type: EvalAssertionType
    value: Any = None


class EvalCaseIn(BaseModel):
    case_key: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9_.:-]+$")
    query: str = Field(min_length=1, max_length=1000)
    language: str = Field(default="ko", max_length=12)
    expected: Dict[str, Any] = Field(default_factory=dict)
    assertions: List[EvalAssertion] = Field(default_factory=list)
    risk_category: str = "standard"
    tags: List[str] = Field(default_factory=list)
    payload_visa_code: Optional[str] = None     # explicit status/sub-code selection, as the UI sends
    depends_on_slots: List[str] = Field(default_factory=list)


class FeedbackIn(BaseModel):
    reason: FeedbackReason
    language: str = Field(default="", max_length=12)
    status_code: Optional[str] = Field(default=None, max_length=16)
    procedure: Optional[str] = Field(default=None, max_length=40)
    intent: Optional[str] = Field(default=None, max_length=40)
    coverage_state: Optional[str] = Field(default=None, max_length=40)
    answer_ref: Optional[str] = Field(default=None, max_length=64)   # public knowledge ref from the answer
    comment: str = Field(default="", max_length=1000)
