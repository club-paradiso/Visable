"""Visable's immigration tool layer — capabilities, not call sites.

What this is
------------
A provider-neutral, model-neutral, transport-neutral registry of the things
Visable can *find out* about Korean immigration. Each tool wraps a deterministic
service that already exists and returns a normalized :class:`EvidenceItem`.

    AI orchestration
          |
    ImmigrationToolRegistry   <- this module: stable names, stable evidence shape
          |
    existing manual / law / status / employment / enforcement services

Why it exists
-------------
Before this, an AI feature that wanted a fact had to know which service to
call, what shape it returned, and how to decide whether the result was
trustworthy. That knowledge got copied per feature and drifted, and the
trustworthiness judgement in particular is not something to leave to a caller
— or to a model.

So the invariant this module enforces is:

    **The LLM never decides whether evidence is approved.**

``approval_state`` and ``verification_state`` are set here, deterministically,
from the registry and the retrieval outcome. A model may read, summarize,
translate and reason over evidence. It may not promote it.

Two states that must never collapse
-----------------------------------
``RETRIEVAL_FAILED`` ("we could not look") and ``NO_RESULTS`` ("we looked and
found nothing") are different facts about the world. Flattening them lets
"our index is down" reach a user as "there is no such rule" — which, for
immigration guidance, is the most dangerous sentence this system could emit.
Every tool here keeps them apart, and :meth:`EvidencePack.unavailable_reasons`
makes the difference reportable.

Deliberate constraints
----------------------
* No FastAPI, no request objects, no HTTP of its own, no provider SDK. A tool
  is a plain callable over plain data, so the same registry can back the HTTP
  API today and an MCP server tomorrow without either owning it.
* No secrets. Credentials stay inside the services being wrapped; nothing here
  reads or forwards one.
* Nothing is duplicated. Every tool delegates; where a deterministic
  implementation exists it is the implementation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence

TOOL_LAYER_VERSION = "2026-08-immigration-tools-v1"


# ---------------------------------------------------------------------------
# Evidence vocabulary
# ---------------------------------------------------------------------------


class AuthorityType(str, Enum):
    """Where a fact comes from, ordered by how much weight it can carry.

    The ordering is the evidence hierarchy from Visable's operating rules. It is
    encoded rather than described so that ranking is a property of the system
    instead of a habit of whoever wrote the last prompt.
    """

    STATUTE = "statute"                      # 법률 / 시행령 / 시행규칙
    APPROVED_MANUAL = "approved_manual"      # human-approved official manual edition
    OFFICIAL_GUIDANCE = "official_guidance"  # MOJ / HiKorea / government notice
    CONSULAR_GUIDANCE = "consular_guidance"  # embassy / consulate, jurisdictional
    ADMINISTRATIVE_SOURCE = "administrative_source"
    PRECEDENT = "precedent"                  # 판례 / 재결례 — contextual, not statute
    STRUCTURED_DATA = "structured_data"      # Visable data traceable to official sources
    UNAPPROVED_EXTRACTION = "unapproved_extraction"  # research context, clearly labelled


#: Rank order for evidence weighting. Lower is stronger.
AUTHORITY_RANK: Dict[AuthorityType, int] = {
    AuthorityType.STATUTE: 1,
    AuthorityType.APPROVED_MANUAL: 2,
    AuthorityType.OFFICIAL_GUIDANCE: 3,
    AuthorityType.CONSULAR_GUIDANCE: 4,
    AuthorityType.ADMINISTRATIVE_SOURCE: 5,
    AuthorityType.PRECEDENT: 6,
    AuthorityType.STRUCTURED_DATA: 7,
    AuthorityType.UNAPPROVED_EXTRACTION: 8,
}

#: Authority types that may back a direct factual assertion. Everything else is
#: context: displayable, citable as "we also found", never the basis of "you
#: must". Precedent is excluded deliberately — a decision describes how a rule
#: was applied to one case, which is not the same as the rule being in force.
DIRECT_ASSERTION_AUTHORITIES = frozenset({
    AuthorityType.STATUTE,
    AuthorityType.APPROVED_MANUAL,
    AuthorityType.OFFICIAL_GUIDANCE,
    AuthorityType.STRUCTURED_DATA,
})


class ApprovalState(str, Enum):
    APPROVED = "approved"          # a human reviewed this edition
    NEEDS_REVIEW = "needs_review"  # parsed, not yet reviewed
    NOT_APPLICABLE = "not_applicable"  # approval is not the relevant gate
    REJECTED = "rejected"


class VerificationState(str, Enum):
    VERIFIED = "verified"              # retrieved and confirmed against the source
    RETRIEVED_UNVERIFIED = "retrieved_unverified"  # we have it, not confirmed current
    AUDIT_ONLY = "audit_only"          # retrieved under audit posture; never citable
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"


class ToolStatus(str, Enum):
    """The outcome of a lookup.

    ``NO_RESULTS`` and ``RETRIEVAL_FAILED`` are the pair that must never merge:
    "we searched and there is nothing" versus "we could not search". Only the
    first says anything about Korean immigration law.
    """

    OK = "ok"
    NO_RESULTS = "no_results"
    RETRIEVAL_FAILED = "retrieval_failed"
    NOT_CONFIGURED = "not_configured"
    NOT_AVAILABLE = "not_available"
    BAD_REQUEST = "bad_request"


#: Statuses where the absence of evidence says nothing about the law.
INCONCLUSIVE_STATUSES = frozenset({
    ToolStatus.RETRIEVAL_FAILED,
    ToolStatus.NOT_CONFIGURED,
    ToolStatus.NOT_AVAILABLE,
})


@dataclass
class EvidenceItem:
    """One normalized piece of immigration evidence."""

    id: str
    source_family: str
    authority_type: AuthorityType
    title: str = ""
    status: str = ""                 # current / repealed / superseded / unknown
    jurisdiction: str = "KR"
    effective_date: str = ""
    retrieved_at: str = ""
    version: str = ""
    locator: str = ""                # article number, page, section
    url: str = ""
    excerpt: str = ""
    structured_fact: Dict[str, Any] = field(default_factory=dict)
    approval_state: ApprovalState = ApprovalState.NOT_APPLICABLE
    relevance: str = "background"    # direct / supporting / background
    confidence: float = 0.0
    verification_state: VerificationState = VerificationState.UNVERIFIED

    @property
    def authority_rank(self) -> int:
        return AUTHORITY_RANK.get(self.authority_type, 99)

    @property
    def usable_for_direct_assertion(self) -> bool:
        """Whether this item may back a "you must / you may" statement.

        Deterministic and deliberately strict. A model cannot influence this:
        an unapproved manual extraction stays context no matter how confidently
        it reads, and an audit-posture law retrieval is never citable as
        current law.
        """
        if self.authority_type not in DIRECT_ASSERTION_AUTHORITIES:
            return False
        if self.authority_type == AuthorityType.APPROVED_MANUAL:
            if self.approval_state is not ApprovalState.APPROVED:
                return False
        if self.verification_state in (VerificationState.AUDIT_ONLY,
                                       VerificationState.CONFLICTING):
            return False
        if self.status == "repealed":
            return False
        return True

    def public_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sourceFamily": self.source_family,
            "authorityType": self.authority_type.value,
            "authorityRank": self.authority_rank,
            "title": self.title,
            "status": self.status,
            "jurisdiction": self.jurisdiction,
            "effectiveDate": self.effective_date,
            "retrievedAt": self.retrieved_at,
            "version": self.version,
            "locator": self.locator,
            "url": self.url,
            "excerpt": self.excerpt,
            "structuredFact": dict(self.structured_fact),
            "approvalState": self.approval_state.value,
            "relevance": self.relevance,
            "confidence": round(float(self.confidence), 3),
            "verificationState": self.verification_state.value,
            "usableForDirectAssertion": self.usable_for_direct_assertion,
        }


@dataclass
class ToolResult:
    """What one tool call produced, including why it produced nothing."""

    tool: str
    status: ToolStatus
    evidence: List[EvidenceItem] = field(default_factory=list)
    reason: str = ""
    query: str = ""
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status is ToolStatus.OK

    @property
    def is_inconclusive(self) -> bool:
        """True when the absence of evidence says nothing about the law."""
        return self.status in INCONCLUSIVE_STATUSES

    def public_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "status": self.status.value,
            "reason": self.reason,
            "query": self.query,
            "isInconclusive": self.is_inconclusive,
            "evidence": [item.public_dict() for item in self.evidence],
            "diagnostics": dict(self.diagnostics),
        }


@dataclass
class EvidencePack:
    """Everything retrieved for one question, with its gaps kept visible."""

    question: str = ""
    results: List[ToolResult] = field(default_factory=list)

    def add(self, result: ToolResult) -> "EvidencePack":
        self.results.append(result)
        return self

    @property
    def evidence(self) -> List[EvidenceItem]:
        """All evidence, strongest authority first."""
        items = [item for result in self.results for item in result.evidence]
        return sorted(items, key=lambda i: (i.authority_rank, -i.confidence))

    @property
    def direct_evidence(self) -> List[EvidenceItem]:
        return [item for item in self.evidence if item.usable_for_direct_assertion]

    @property
    def contextual_evidence(self) -> List[EvidenceItem]:
        return [item for item in self.evidence if not item.usable_for_direct_assertion]

    def unavailable_reasons(self) -> List[Dict[str, str]]:
        """Lookups that could not run — the honest reason an answer is thin.

        Reported separately from empty results so a caller can say "we could
        not check the statute" instead of implying there is no statute.
        """
        return [
            {"tool": r.tool, "status": r.status.value, "reason": r.reason}
            for r in self.results if r.is_inconclusive
        ]

    def empty_result_tools(self) -> List[str]:
        """Lookups that ran successfully and genuinely found nothing."""
        return [r.tool for r in self.results if r.status is ToolStatus.NO_RESULTS]

    def public_dict(self) -> Dict[str, Any]:
        return {
            "version": TOOL_LAYER_VERSION,
            "question": self.question,
            "directEvidenceCount": len(self.direct_evidence),
            "contextualEvidenceCount": len(self.contextual_evidence),
            "evidence": [item.public_dict() for item in self.evidence],
            "unavailable": self.unavailable_reasons(),
            "emptyResults": self.empty_result_tools(),
            "results": [r.public_dict() for r in self.results],
        }


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _clean(value: Any, limit: int = 600) -> str:
    return " ".join(str(value or "").split())[:limit]


def lookup_status(
    code: str,
    *,
    visa_records: Optional[Sequence[Dict[str, Any]]] = None,
) -> ToolResult:
    """Resolve one 체류자격 code from Visable's structured data.

    Parent and sub-status stay structurally distinct: a query for ``D-2``
    returns the parent record and lists its subcodes, but never merges a
    subcode's rules into the parent. Presenting a subcode rule as a universal
    parent requirement is the single most consequential rendering error this
    dataset can make.
    """
    query = _clean(code, 40).upper()
    if not query:
        return ToolResult("lookup_status", ToolStatus.BAD_REQUEST, reason="empty code")
    if visa_records is None:
        return ToolResult("lookup_status", ToolStatus.NOT_AVAILABLE,
                          reason="visa records not supplied", query=query)

    matched = None
    subcodes: List[str] = []
    for record in visa_records:
        if not isinstance(record, dict):
            continue
        rec_code = str(record.get("code") or "").strip().upper()
        if not rec_code:
            continue
        if rec_code == query:
            matched = record
        elif rec_code.startswith(query + "-"):
            subcodes.append(rec_code)

    if matched is None:
        return ToolResult("lookup_status", ToolStatus.NO_RESULTS, query=query,
                          reason=f"no record for {query}")

    segments = query.split("-")
    item = EvidenceItem(
        id=f"status:{query}",
        source_family="visable_structured_status",
        authority_type=AuthorityType.STRUCTURED_DATA,
        title=f"{query} {_clean(matched.get('title') or matched.get('name'), 120)}".strip(),
        retrieved_at=_now_iso(),
        locator=query,
        excerpt=_clean(matched.get("summary") or matched.get("description"), 400),
        structured_fact={
            "code": query,
            # 2 segments are a parent code; 3+ is a subcode classified under it.
            "isSubcode": len(segments) >= 3,
            "parentCode": "-".join(segments[:2]) if len(segments) >= 3 else "",
            "subcodes": sorted(subcodes),
            # Named so a renderer cannot accidentally treat subcode rules as the
            # parent's own requirements.
            "subcodeRulesAreNotParentRules": True,
        },
        relevance="direct",
        confidence=1.0,
        verification_state=VerificationState.RETRIEVED_UNVERIFIED,
    )
    return ToolResult("lookup_status", ToolStatus.OK, [item], query=query)


def search_manual(
    query: str,
    *,
    domain: str = "",
    limit: int = 8,
    search_fn: Optional[Callable[..., Dict[str, Any]]] = None,
) -> ToolResult:
    """Search the official manuals, keeping approval state deterministic.

    Approved and review-pending chunks come back as different authority types,
    decided here from the registry — never from how convincing the text reads.
    A missing index is ``RETRIEVAL_FAILED``, never an empty result, because
    "the manuals are not searchable right now" and "the manuals say nothing
    about this" are opposite messages.
    """
    q = _clean(query, 200)
    if not q:
        return ToolResult("search_manual", ToolStatus.BAD_REQUEST, reason="empty query")

    if search_fn is None:
        from . import manual_search as _manual_search
        search_fn = _manual_search.search_manuals

    try:
        raw = search_fn(q, domain=domain, limit=limit)
    except Exception as exc:  # a search backend fault is not a legal finding
        return ToolResult("search_manual", ToolStatus.RETRIEVAL_FAILED, query=q,
                          reason=f"manual search raised {exc.__class__.__name__}")

    status = str(raw.get("status") or "")
    if status == "index_unavailable":
        return ToolResult(
            "search_manual", ToolStatus.RETRIEVAL_FAILED, query=q,
            reason="manual search index is not built on this deployment",
            diagnostics={"hint": raw.get("hint", "")},
        )
    if status == "bad_query":
        return ToolResult("search_manual", ToolStatus.BAD_REQUEST, query=q,
                          reason="query contained no searchable tokens")

    evidence: List[EvidenceItem] = []
    for bucket, authority, approval in (
        ("approved", AuthorityType.APPROVED_MANUAL, ApprovalState.APPROVED),
        ("needs_review", AuthorityType.UNAPPROVED_EXTRACTION, ApprovalState.NEEDS_REVIEW),
    ):
        for chunk in raw.get(bucket) or []:
            if not isinstance(chunk, dict):
                continue
            page = chunk.get("page")
            evidence.append(EvidenceItem(
                id=f"manual:{chunk.get('source_id', '')}:{page or ''}:{bucket}",
                source_family=str(chunk.get("family_key") or "manual"),
                authority_type=authority,
                title=_clean(chunk.get("heading") or chunk.get("source_id"), 160),
                version=_clean(chunk.get("manual_version"), 40),
                locator=f"p.{page}" if page else "",
                excerpt=_clean(chunk.get("excerpt"), 320),
                retrieved_at=_now_iso(),
                approval_state=approval,
                relevance="direct" if bucket == "approved" else "background",
                confidence=0.9 if bucket == "approved" else 0.4,
                verification_state=(
                    VerificationState.VERIFIED if bucket == "approved"
                    else VerificationState.RETRIEVED_UNVERIFIED
                ),
                structured_fact={
                    "domain": chunk.get("domain", ""),
                    "statusCodes": chunk.get("status_codes", ""),
                    # Flattened table text cannot be read as cell relationships.
                    "extractionCaveat": "table structure may be flattened; do not infer cell relationships",
                },
            ))

    if not evidence:
        return ToolResult("search_manual", ToolStatus.NO_RESULTS, query=q,
                          reason="the manual index was searched and matched nothing")
    return ToolResult("search_manual", ToolStatus.OK, evidence, query=q)


def search_law(
    query: str,
    *,
    limit: int = 5,
    search_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    grounding_mode: str = "",
) -> ToolResult:
    """Search Korean statutes via the Open Law API.

    Under ``audit`` grounding mode the retrieval still runs but every item is
    marked ``AUDIT_ONLY`` and cannot back a direct assertion. That posture
    exists precisely so specific article numbers are not trusted before the
    pipeline has been proven end to end; encoding it here means a caller
    cannot forget it.
    """
    q = _clean(query, 200)
    if not q:
        return ToolResult("search_law", ToolStatus.BAD_REQUEST, reason="empty query")

    if search_fn is None:
        from . import law_tools as _law_tools
        search_fn = _law_tools.search_laws_ranked

    try:
        raw = search_fn(q, limit=limit)
    except Exception as exc:
        return ToolResult("search_law", ToolStatus.RETRIEVAL_FAILED, query=q,
                          reason=f"law search raised {exc.__class__.__name__}")

    if not isinstance(raw, dict):
        return ToolResult("search_law", ToolStatus.RETRIEVAL_FAILED, query=q,
                          reason="law search returned an unexpected payload")

    if raw.get("error_type") or raw.get("status") in {"error", "failed"}:
        error_type = str(raw.get("error_type") or "unknown")
        # "Not configured" is an operator problem, not a legal finding, and the
        # user-facing wording differs — so it stays a distinct status.
        status = (ToolStatus.NOT_CONFIGURED if "not_configured" in error_type
                  or "no_credential" in error_type else ToolStatus.RETRIEVAL_FAILED)
        return ToolResult("search_law", status, query=q,
                          reason=f"law lookup failed ({error_type})",
                          diagnostics={"errorType": error_type})

    items = raw.get("items") or raw.get("normalized_items") or raw.get("results") or []
    audit_only = str(grounding_mode or "").strip().lower() == "audit"
    evidence: List[EvidenceItem] = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        law_name = _clean(entry.get("law_name") or entry.get("title"), 160)
        if not law_name:
            continue
        repealed = bool(entry.get("repealed")) or "폐지" in str(entry.get("status") or "")
        evidence.append(EvidenceItem(
            id=f"law:{law_name}:{entry.get('article', '')}",
            source_family="korean_statute",
            authority_type=AuthorityType.STATUTE,
            title=law_name,
            # A repealed statute stays visible; hiding it would let a caller
            # believe the current rule was never found.
            status="repealed" if repealed else _clean(entry.get("status") or "current", 40),
            effective_date=_clean(entry.get("effective_date") or entry.get("시행일자"), 40),
            locator=_clean(entry.get("article"), 60),
            url=_clean(entry.get("source_url") or entry.get("url"), 400),
            excerpt=_clean(entry.get("summary") or entry.get("excerpt"), 400),
            retrieved_at=_now_iso(),
            approval_state=ApprovalState.NOT_APPLICABLE,
            relevance="direct",
            confidence=0.85 if not audit_only else 0.5,
            verification_state=(VerificationState.AUDIT_ONLY if audit_only
                                else VerificationState.VERIFIED),
        ))

    if not evidence:
        return ToolResult("search_law", ToolStatus.NO_RESULTS, query=q,
                          reason="the statute database was searched and matched nothing")
    return ToolResult("search_law", ToolStatus.OK, evidence, query=q,
                      diagnostics={"auditOnly": audit_only})


def search_precedent(
    query: str,
    *,
    limit: int = 5,
    search_fn: Optional[Callable[..., Any]] = None,
) -> ToolResult:
    """Search 판례 / 재결례.

    Precedent is contextual by construction: :data:`DIRECT_ASSERTION_AUTHORITIES`
    excludes it, so no amount of relevance lets a decision stand in for the rule
    it applied. A case shows how a provision was read once; it is not the
    provision.
    """
    q = _clean(query, 200)
    if not q:
        return ToolResult("search_precedent", ToolStatus.BAD_REQUEST, reason="empty query")
    if search_fn is None:
        return ToolResult("search_precedent", ToolStatus.NOT_AVAILABLE, query=q,
                          reason="no precedent adapter supplied")
    try:
        raw = search_fn(q, limit=limit)
    except Exception as exc:
        return ToolResult("search_precedent", ToolStatus.RETRIEVAL_FAILED, query=q,
                          reason=f"precedent search raised {exc.__class__.__name__}")

    entries = raw if isinstance(raw, list) else (raw or {}).get("items") or []
    evidence: List[EvidenceItem] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        case_number = _clean(entry.get("case_number") or entry.get("사건번호"), 80)
        evidence.append(EvidenceItem(
            id=f"precedent:{case_number or len(evidence)}",
            source_family="korean_precedent",
            authority_type=AuthorityType.PRECEDENT,
            title=_clean(entry.get("case_name") or entry.get("사건명"), 200),
            locator=case_number,
            effective_date=_clean(entry.get("decision_date") or entry.get("선고일자"), 40),
            url=_clean(entry.get("source_url") or entry.get("url"), 400),
            excerpt=_clean(entry.get("summary"), 400),
            retrieved_at=_now_iso(),
            approval_state=ApprovalState.NOT_APPLICABLE,
            relevance="supporting",
            confidence=0.6,
            verification_state=VerificationState.RETRIEVED_UNVERIFIED,
        ))
    if not evidence:
        return ToolResult("search_precedent", ToolStatus.NO_RESULTS, query=q,
                          reason="the case database was searched and matched nothing")
    return ToolResult("search_precedent", ToolStatus.OK, evidence, query=q)


#: Deadlines Visable can compute from a statutory period. Each entry records the
#: period and the provision it comes from — a calculated date with no cited basis
#: is a guess wearing a calendar.
_STATUTORY_PERIODS: Dict[str, Dict[str, Any]] = {
    "foreign_resident_registration": {
        "days": 90,
        "basis": "출입국관리법 제31조 (외국인등록)",
        "label_ko": "외국인등록 기한",
        "label_en": "Foreign resident registration deadline",
    },
    "workplace_change_report": {
        "days": 15,
        "basis": "출입국관리법 제19조 (외국인을 고용한 자 등의 신고의무) 관련 신고기한",
        "label_ko": "근무처 변경·추가 신고 기한",
        "label_en": "Workplace change/addition report deadline",
    },
    "domestic_residence_report": {
        "days": 30,
        "basis": "재외동포의 출입국과 법적 지위에 관한 법률 제6조 (국내거소신고)",
        "label_ko": "국내거소신고 기한",
        "label_en": "Domestic residence report deadline",
    },
}


def calculate_deadline(
    trigger_date: Any,
    *,
    period: str = "",
    days: Optional[int] = None,
) -> ToolResult:
    """Compute a preparation deadline from a known statutory period.

    Deterministic arithmetic over a period Visable can cite. An arbitrary
    ``days`` value is accepted for scenario work but is returned with no
    statutory basis and a lower confidence, so a caller can never present a
    made-up interval as a legal deadline.

    The result is explicitly a *preparation* date. Official deadline handling
    involves holiday rules and office practice this does not model, so the
    evidence item says so rather than implying an authoritative date.
    """
    if isinstance(trigger_date, str):
        try:
            parsed = date.fromisoformat(trigger_date.strip()[:10])
        except ValueError:
            return ToolResult("calculate_deadline", ToolStatus.BAD_REQUEST,
                              reason="trigger_date must be an ISO date (YYYY-MM-DD)")
    elif isinstance(trigger_date, datetime):
        parsed = trigger_date.date()
    elif isinstance(trigger_date, date):
        parsed = trigger_date
    else:
        return ToolResult("calculate_deadline", ToolStatus.BAD_REQUEST,
                          reason="trigger_date is required")

    known = _STATUTORY_PERIODS.get(str(period or "").strip())
    if known:
        interval, basis, label = known["days"], known["basis"], known["label_ko"]
        confidence = 0.9
    elif days is not None and int(days) > 0:
        interval, basis, label = int(days), "", "기간 계산"
        confidence = 0.3
    else:
        return ToolResult(
            "calculate_deadline", ToolStatus.NO_RESULTS,
            reason=f"no statutory period is encoded for {period!r}",
            diagnostics={"knownPeriods": sorted(_STATUTORY_PERIODS)},
        )

    due = parsed + timedelta(days=interval)
    item = EvidenceItem(
        id=f"deadline:{period or 'custom'}:{parsed.isoformat()}",
        source_family="visable_deadline_calculation",
        authority_type=(AuthorityType.STATUTE if basis else AuthorityType.STRUCTURED_DATA),
        title=label,
        locator=basis,
        retrieved_at=_now_iso(),
        structured_fact={
            "triggerDate": parsed.isoformat(),
            "periodDays": interval,
            "preparationDeadline": due.isoformat(),
            "statutoryBasis": basis,
            "isOfficialDeadline": False,
            "caution": (
                "준비용 계산입니다. 공휴일·관서 운영 등은 반영되지 않으므로 "
                "공식 기한은 HiKorea·1345·관할 출입국·외국인관서에서 확인하세요."
            ),
        },
        relevance="direct",
        confidence=confidence,
        # Arithmetic is not retrieval: never claim the date was verified.
        verification_state=VerificationState.RETRIEVED_UNVERIFIED,
    )
    return ToolResult("calculate_deadline", ToolStatus.OK, [item], query=period)


def analyze_enforcement_rules(case: Any, *, calculate_fn: Optional[Callable] = None) -> ToolResult:
    """Deterministic statutory baseline for an enforcement scenario.

    Wraps the existing rule calculator. Whatever the baseline says, no
    probability is produced here: the AI layer explains a rule range and its
    uncertainty, and never manufactures a likelihood that an officer will act
    a particular way.
    """
    if calculate_fn is None:
        from .enforcement_rules import calculate_legal_baseline as calculate_fn  # type: ignore
    try:
        baseline = calculate_fn(case)
    except Exception as exc:
        return ToolResult("analyze_enforcement_rules", ToolStatus.RETRIEVAL_FAILED,
                          reason=f"baseline calculation raised {exc.__class__.__name__}")

    status = getattr(baseline, "status", "")
    if status != "AVAILABLE":
        return ToolResult(
            "analyze_enforcement_rules", ToolStatus.NO_RESULTS,
            reason="no verified statutory basis is encoded for this violation",
            diagnostics={"baselineStatus": status},
        )

    item = EvidenceItem(
        id="enforcement:baseline",
        source_family="visable_enforcement_rules",
        authority_type=AuthorityType.STATUTE,
        title="법령상 처분 기준",
        retrieved_at=_now_iso(),
        structured_fact={
            "legallyAdjustableRange": getattr(baseline, "legally_adjustable_range", None),
            "availableDispositions": list(getattr(baseline, "available_dispositions", []) or []),
            "isPrediction": False,
            "isDeterministicRuleOutput": True,
        },
        relevance="direct",
        confidence=1.0,
        verification_state=VerificationState.VERIFIED,
    )
    return ToolResult("analyze_enforcement_rules", ToolStatus.OK, [item])


# ---------------------------------------------------------------------------
# Fact extraction (deterministic — the model does not get to invent these)
# ---------------------------------------------------------------------------

_STATUS_CODE_RE = re.compile(r"(?<![A-Z0-9])([A-HKM]-\d{1,2}(?:-\d{1,2})?(?:-T)?)(?![A-Z0-9])", re.I)


def extract_immigration_facts(text: str) -> Dict[str, Any]:
    """Pull the facts a question actually states — and nothing more.

    Only surface facts are extracted (status codes, dates, paid/unpaid signals,
    procedure intent). Anything absent stays absent: a missing fact must reach
    the orchestrator as missing so it can ask, rather than be quietly guessed
    into an answer that sounds specific and is not.
    """
    raw = str(text or "")
    facts: Dict[str, Any] = {
        "statusCodes": [],
        "dates": [],
        "paidActivity": None,
        "workplaceChange": False,
        "statusChange": False,
        "extension": False,
        "registration": False,
        "reentry": False,
        "overstay": False,
    }

    seen: List[str] = []
    for match in _STATUS_CODE_RE.finditer(raw):
        code = match.group(1).upper()
        if code not in seen:
            seen.append(code)
    facts["statusCodes"] = seen

    for match in re.finditer(r"(\d{4})\s*[.년/-]\s*(\d{1,2})\s*[.월/-]\s*(\d{1,2})", raw):
        try:
            facts["dates"].append(
                date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
            )
        except ValueError:
            continue

    if re.search(r"유급|급여|월급|시급|보수|아르바이트|알바|paid|salary|wage", raw, re.I):
        facts["paidActivity"] = True
    elif re.search(r"무급|봉사|자원봉사|unpaid|volunteer", raw, re.I):
        facts["paidActivity"] = False

    facts["workplaceChange"] = bool(re.search(
        r"근무처\s*(?:변경|추가)|직장\s*(?:변경|옮)|change\s+(?:of\s+)?(?:employer|workplace)", raw, re.I))
    facts["statusChange"] = bool(re.search(
        r"체류자격\s*변경|자격\s*변경|change\s+of\s+status", raw, re.I))
    facts["extension"] = bool(re.search(r"체류기간\s*연장|연장|extension|extend", raw, re.I))
    facts["registration"] = bool(re.search(
        r"외국인등록|거소신고|registration|register", raw, re.I))
    facts["reentry"] = bool(re.search(r"재입국|re-?entry", raw, re.I))
    facts["overstay"] = bool(re.search(
        r"초과\s*체류|오버스테이|불법\s*체류|기간\s*(?:을\s*)?넘|overstay", raw, re.I))
    return facts


#: Facts whose absence changes the answer enough to be worth asking about,
#: keyed by the procedure they matter to. Asking one focused question beats
#: producing a confident answer to a question the user did not ask.
DECISIVE_FACTS: Dict[str, Sequence[str]] = {
    "workplaceChange": ("statusCodes",),
    "statusChange": ("statusCodes",),
    "extension": ("statusCodes", "dates"),
    "registration": ("dates",),
    "overstay": ("dates",),
}


def missing_decisive_facts(facts: Dict[str, Any]) -> List[str]:
    """Which decisive facts the question did not supply."""
    missing: List[str] = []
    for procedure, required in DECISIVE_FACTS.items():
        if not facts.get(procedure):
            continue
        for key in required:
            if not facts.get(key) and key not in missing:
                missing.append(key)
    return missing


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolSpec:
    """A tool's stable, transport-neutral description.

    ``mcp_name`` is reserved now so that exposing the registry over MCP later
    is an adapter, not a rename — callers, logs and tests keep their identifiers.
    """

    name: str
    mcp_name: str
    description: str
    handler: Callable[..., ToolResult]
    reads_network: bool = False
    requires_credential: bool = False


class ImmigrationToolRegistry:
    """The tools an orchestrator may call, by name.

    Kept free of FastAPI and of any provider SDK so the same registry can back
    the HTTP API today and an MCP server tomorrow without either owning it.
    """

    def __init__(self, specs: Optional[Sequence[ToolSpec]] = None) -> None:
        self._specs: Dict[str, ToolSpec] = {}
        for spec in specs if specs is not None else default_tool_specs():
            self.register(spec)

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"tool {spec.name!r} is already registered")
        self._specs[spec.name] = spec

    def names(self) -> List[str]:
        return sorted(self._specs)

    def spec(self, name: str) -> Optional[ToolSpec]:
        return self._specs.get(name)

    def describe(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": s.name,
                "mcpName": s.mcp_name,
                "description": s.description,
                "readsNetwork": s.reads_network,
                "requiresCredential": s.requires_credential,
            }
            for s in sorted(self._specs.values(), key=lambda s: s.name)
        ]

    def call(self, name: str, **kwargs: Any) -> ToolResult:
        """Invoke a tool. An unknown name is a bad request, never an exception.

        A model choosing a tool that does not exist is a routing mistake, not a
        crash, and the orchestrator should be able to recover from it the same
        way it recovers from a lookup that found nothing.
        """
        spec = self._specs.get(name)
        if spec is None:
            return ToolResult(name, ToolStatus.BAD_REQUEST,
                              reason=f"unknown tool {name!r}",
                              diagnostics={"available": self.names()})
        try:
            return spec.handler(**kwargs)
        except TypeError as exc:
            return ToolResult(name, ToolStatus.BAD_REQUEST,
                              reason=f"invalid arguments for {name}: {exc}")
        except Exception as exc:  # a tool fault must not become a legal claim
            return ToolResult(name, ToolStatus.RETRIEVAL_FAILED,
                              reason=f"{name} raised {exc.__class__.__name__}")


def default_tool_specs() -> List[ToolSpec]:
    return [
        ToolSpec("lookup_status", "visable.get_status",
                 "Resolve one 체류자격 code from Visable structured data, keeping "
                 "parent and sub-status distinct.",
                 lookup_status),
        ToolSpec("search_manual", "visable.search_manual",
                 "Search official immigration manuals; approved and review-pending "
                 "content are returned as different authority types.",
                 search_manual),
        ToolSpec("search_law", "visable.search_law",
                 "Search Korean statutes via the Open Law API; audit posture marks "
                 "results non-citable.",
                 search_law, reads_network=True, requires_credential=True),
        ToolSpec("search_precedent", "visable.search_precedent",
                 "Search 판례 / 재결례 as contextual legal evidence, never as "
                 "current statutory authority.",
                 search_precedent, reads_network=True, requires_credential=True),
        ToolSpec("calculate_deadline", "visable.calculate_deadline",
                 "Compute a preparation deadline from an encoded statutory period.",
                 calculate_deadline),
        ToolSpec("analyze_enforcement_rules", "visable.analyze_enforcement",
                 "Deterministic statutory baseline for an enforcement scenario; "
                 "produces no probability.",
                 analyze_enforcement_rules),
    ]


def build_registry() -> ImmigrationToolRegistry:
    return ImmigrationToolRegistry()
