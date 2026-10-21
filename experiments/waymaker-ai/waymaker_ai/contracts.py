"""Waymaker Legal Intelligence (WLIE) — core contracts.

This module is the single vocabulary shared by the WLIE reference
implementation, the benchmark and the evaluation runner. It is deliberately
standard-library only so that the experiment can run without the backend
environment.

Design rules (see docs/ai/waymaker-genesis/05-legal-intelligence-architecture.md):

* A law title is never an identity. ``SourceIdentity.stable_id`` (법령ID,
  행정규칙ID, or a manual lineage id) is the identity; a *version* is the pair
  ``(version_id, effective_date)`` because one promulgation (one 법령일련번호)
  can carry several effective dates.
* Lookup failure is not absence. Only ``LookupStatus.NOT_FOUND`` from a lookup
  whose coverage is complete may ever become ``SOURCE_NOT_FOUND`` or
  ``CITATION_NOT_FOUND``; every other failure becomes
  ``VERIFICATION_UNAVAILABLE``.
* Verification is layered. Passing a lower layer (an article exists) says
  nothing about a higher one (the claim drawn from it is supported).
* A selected candidate version is a *candidate*, never a legal determination.

Vocabulary that already exists in the backend is mirrored, not redefined:
``AUTHORITY_TYPES`` mirrors ``services.immigration_tools.AuthorityType`` and
``CONDITION_KINDS`` mirrors ``services.knowledge.models.ConditionKind``. A
parity test (tests/test_contracts.py) fails if they drift.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import unicodedata
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

WLIE_CONTRACT_VERSION = "wlie/0.1"

# ---------------------------------------------------------------------------
# Mirrored backend vocabulary (do not edit without editing the backend)
# ---------------------------------------------------------------------------
#: services.immigration_tools.AuthorityType values, strongest first.
AUTHORITY_TYPES: Tuple[str, ...] = (
    "statute",
    "approved_manual",
    "official_guidance",
    "consular_guidance",
    "administrative_source",
    "precedent",
    "structured_data",
    "unapproved_extraction",
)

#: services.knowledge.models.ConditionKind values.
CONDITION_KINDS: Tuple[str, ...] = (
    "always",
    "conditional",
    "applicant_specific",
    "office_discretion",
)

#: Hosts an official-source URL may point at. Anything else is rejected before
#: a request is built (no URL is ever constructed from raw user input).
OFFICIAL_SOURCE_HOSTS: Tuple[str, ...] = (
    "law.go.kr",
    "www.law.go.kr",
    "open.law.go.kr",
    "hikorea.go.kr",
    "www.hikorea.go.kr",
    "immigration.go.kr",
    "www.immigration.go.kr",
    "moj.go.kr",
    "www.moj.go.kr",
)


# ---------------------------------------------------------------------------
# Source identity
# ---------------------------------------------------------------------------
class SourceFamily(str, Enum):
    """What kind of document a source is. Finer than ``AUTHORITY_TYPES``."""

    STATUTE = "statute"                                  # 법률
    ENFORCEMENT_DECREE = "enforcement_decree"            # 시행령 (대통령령)
    ENFORCEMENT_RULE = "enforcement_rule"                # 시행규칙 (부령)
    ADMINISTRATIVE_RULE = "administrative_rule"          # 고시·훈령·예규·지침
    OFFICIAL_FORM = "official_form"                      # 별표·별지 서식
    IMMIGRATION_MANUAL = "immigration_manual"            # published 체류/사증 manual edition
    PUBLIC_GUIDANCE = "public_guidance"                  # HiKorea / MOJ web guidance
    OFFICIAL_INTERPRETATION = "official_interpretation"  # 법령해석례
    JUDICIAL_DECISION = "judicial_decision"              # 판례
    ADMINISTRATIVE_APPEAL = "administrative_appeal"      # 행정심판 재결
    CONSTITUTIONAL_DECISION = "constitutional_decision"  # 헌재 결정
    SECONDARY = "secondary"                              # commentary, translations


#: Default mapping onto the backend authority vocabulary. It is a default for
#: display and routing only. WLIE never resolves a conflict by rank: two
#: inconsistent sources always produce a ConflictRecord (see verification).
DEFAULT_AUTHORITY: Dict[SourceFamily, str] = {
    SourceFamily.STATUTE: "statute",
    SourceFamily.ENFORCEMENT_DECREE: "statute",
    SourceFamily.ENFORCEMENT_RULE: "statute",
    SourceFamily.ADMINISTRATIVE_RULE: "administrative_source",
    SourceFamily.OFFICIAL_FORM: "statute",
    SourceFamily.IMMIGRATION_MANUAL: "approved_manual",
    SourceFamily.PUBLIC_GUIDANCE: "official_guidance",
    SourceFamily.OFFICIAL_INTERPRETATION: "administrative_source",
    SourceFamily.JUDICIAL_DECISION: "precedent",
    SourceFamily.ADMINISTRATIVE_APPEAL: "precedent",
    SourceFamily.CONSTITUTIONAL_DECISION: "precedent",
    SourceFamily.SECONDARY: "unapproved_extraction",
}

#: Families whose text is the legal obligation itself (법규명령 and the Act).
LEGISLATIVE_FAMILIES = frozenset({
    SourceFamily.STATUTE,
    SourceFamily.ENFORCEMENT_DECREE,
    SourceFamily.ENFORCEMENT_RULE,
})


class ProvenanceStatus(str, Enum):
    """How a source record itself was obtained."""

    VERIFIED_API = "verified_api"            # read from the official Open API in a recorded session
    VERIFIED_WEB = "verified_web"            # read from the official public web page in a recorded session
    REPOSITORY_RECORD = "repository_record"  # copied from a Waymaker data file, not re-checked
    SYNTHETIC_FIXTURE = "synthetic_fixture"  # invented for a test; must never reach a user
    UNVERIFIED = "unverified"


class ParseStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"          # e.g. tables flattened, annex images not read
    FAILED = "failed"
    NOT_PARSED = "not_parsed"


@dataclass(frozen=True)
class SourceIdentity:
    """A legal document lineage, independent of its title and of any version."""

    provider: str                 # e.g. "law.go.kr"
    family: SourceFamily
    stable_id: str                # 법령ID / 행정규칙ID / manual lineage id
    official_title: str
    former_titles: Tuple[str, ...] = ()
    short_titles: Tuple[str, ...] = ()   # 약칭 printed by the official source
    competent_ministry: Optional[str] = None

    @property
    def authority_type(self) -> str:
        return DEFAULT_AUTHORITY[self.family]

    def all_titles(self) -> Tuple[str, ...]:
        return (self.official_title,) + tuple(self.former_titles) + tuple(self.short_titles)


@dataclass(frozen=True)
class SourceVersion:
    """One effective-dated version of a source.

    ``version_id`` alone is not unique: law.go.kr lists one 법령일련번호 once per
    effective date when a promulgation defers some provisions.
    ``provision_effective_dates`` records provisions whose 시행일 differs from
    ``effective_date`` (key = ``ProvisionRef.key()``).
    """

    stable_id: str
    version_id: str
    effective_date: Optional[dt.date]
    promulgation_date: Optional[dt.date] = None
    promulgation_no: Optional[str] = None
    amendment_type: Optional[str] = None      # 제개정구분 as printed (일부개정, 전부개정, 타법개정, 폐지 …)
    end_date: Optional[dt.date] = None        # only when established by a later version or repeal
    provision_effective_dates: Mapping[str, dt.date] = field(default_factory=dict)
    official_url: Optional[str] = None
    retrieved_at: Optional[str] = None        # ISO-8601 timestamp
    content_sha256: Optional[str] = None
    parse_status: ParseStatus = ParseStatus.NOT_PARSED
    provenance: ProvenanceStatus = ProvenanceStatus.UNVERIFIED
    has_transitional_provisions: Optional[bool] = None   # None = 부칙 not read
    is_repeal: bool = False
    #: Provisions this version changed (ProvisionRef.article_key() values).
    #: None = unknown, which makes every pending version relevant to every provision.
    changed_provisions: Optional[Tuple[str, ...]] = None

    @property
    def key(self) -> Tuple[str, Optional[str]]:
        return (self.version_id, self.effective_date.isoformat() if self.effective_date else None)

    def effective_date_for(self, provision_key: Optional[str]) -> Optional[dt.date]:
        if provision_key and provision_key in self.provision_effective_dates:
            return self.provision_effective_dates[provision_key]
        return self.effective_date


@dataclass(frozen=True)
class ProvisionRef:
    """A point inside a source. All numbers are the printed numbers."""

    article: Optional[int] = None          # 제N조
    article_branch: int = 0                # 제N조의M → M
    paragraph: Optional[int] = None        # 제N항 / ①
    item: Optional[int] = None             # 제N호
    item_branch: int = 0                   # 제N호의M → M
    subitem: Optional[str] = None          # 가목 → "가"
    annex: Optional[str] = None            # "별표 5의2"
    form: Optional[str] = None             # "별지 제34호서식"
    addendum: bool = False                 # 부칙

    def key(self) -> str:
        if self.annex:
            return self.annex.replace(" ", "")
        if self.form:
            return self.form.replace(" ", "")
        parts: List[str] = []
        if self.addendum:
            parts.append("부칙")
        if self.article is not None:
            parts.append(f"제{self.article}조" + (f"의{self.article_branch}" if self.article_branch else ""))
        if self.paragraph is not None:
            parts.append(f"제{self.paragraph}항")
        if self.item is not None:
            parts.append(f"제{self.item}호" + (f"의{self.item_branch}" if self.item_branch else ""))
        if self.subitem:
            parts.append(f"{self.subitem}목")
        return "".join(parts)

    def article_key(self) -> str:
        """The article-level key used for version and effective-date lookups."""
        if self.article is None:
            return self.key()
        return ("부칙" if self.addendum else "") + f"제{self.article}조" + (
            f"의{self.article_branch}" if self.article_branch else ""
        )

    def is_empty(self) -> bool:
        return self.article is None and not self.annex and not self.form and not self.addendum


@dataclass(frozen=True)
class Citation:
    """A legal reference as written in a question or an answer."""

    raw: str
    law_title_as_written: Optional[str]
    provision: ProvisionRef
    claimed_heading: Optional[str] = None   # text in parentheses after the article, e.g. 제73조(수수료의 납부방법)
    quoted_text: Optional[str] = None
    resolved_stable_id: Optional[str] = None
    span: Optional[Tuple[int, int]] = None


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
class AnchorKind(str, Enum):
    """Which date a legal question turns on. Chosen by issue type, never guessed."""

    QUESTION_DATE = "question_date"
    CONDUCT_DATE = "conduct_date"
    APPLICATION_DATE = "application_date"
    FILING_DATE = "filing_date"
    DECISION_DATE = "decision_date"
    DEPARTURE_DATE = "departure_date"
    RETURN_DATE = "return_date"
    STAY_EXPIRY_DATE = "stay_expiry_date"


class TemporalWarning(str, Enum):
    """Warnings the temporal resolver attaches to a candidate-version selection."""

    ANCHOR_MISSING = "anchor_missing"                                  # the decisive date is not known
    FUTURE_VERSION_PENDING = "future_version_pending"                  # promulgated, effective after the anchor
    PROVISION_EFFECTIVE_DATE_DIFFERS = "provision_effective_date_differs"  # deferred 시행일 for the cited provision
    ANCHOR_BEFORE_KNOWN_HISTORY = "anchor_before_known_history"        # history loaded does not reach the anchor
    VERSION_HISTORY_UNAVAILABLE = "version_history_unavailable"        # lookup failed; nothing about absence
    TRANSITIONAL_PROVISIONS_UNREVIEWED = "transitional_provisions_unreviewed"  # 부칙 not read or not assessed
    ANCHORS_SELECT_DIFFERENT_VERSIONS = "anchors_select_different_versions"    # e.g. conduct vs decision date
    SOURCE_REPEALED_BEFORE_ANCHOR = "source_repealed_before_anchor"


@dataclass(frozen=True)
class RelevantDates:
    question_date: Optional[dt.date] = None
    conduct_date: Optional[dt.date] = None
    application_date: Optional[dt.date] = None
    filing_date: Optional[dt.date] = None
    decision_date: Optional[dt.date] = None
    departure_date: Optional[dt.date] = None
    return_date: Optional[dt.date] = None
    stay_expiry_date: Optional[dt.date] = None
    manual_edition_date: Optional[dt.date] = None

    def get(self, anchor: AnchorKind) -> Optional[dt.date]:
        return getattr(self, anchor.value)

    def present(self) -> Dict[str, dt.date]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ---------------------------------------------------------------------------
# Lookup results (adapter boundary)
# ---------------------------------------------------------------------------
class LookupStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"                          # authoritative empty answer
    UNAVAILABLE_NETWORK = "unavailable_network"
    UNAVAILABLE_TIMEOUT = "unavailable_timeout"
    UNAVAILABLE_AUTH = "unavailable_auth"            # missing / rejected credential, IP not registered
    UNAVAILABLE_RATE_LIMITED = "unavailable_rate_limited"
    UNAVAILABLE_PARSE = "unavailable_parse"          # HTML, empty body, malformed XML/JSON
    UNAVAILABLE_BUDGET = "unavailable_budget"        # request budget exhausted before the call
    UPSTREAM_ERROR = "upstream_error"                # official error payload / HTTP 5xx

    @property
    def is_absence(self) -> bool:
        return self is LookupStatus.NOT_FOUND

    @property
    def is_failure(self) -> bool:
        return self not in (LookupStatus.FOUND, LookupStatus.NOT_FOUND)


class Coverage(str, Enum):
    COMPLETE = "complete"     # the lookup could have returned the item if it existed
    PARTIAL = "partial"       # e.g. current-title index only, page limit hit, history not loaded


@dataclass(frozen=True)
class LookupResult:
    status: LookupStatus
    coverage: Coverage = Coverage.COMPLETE
    detail: str = ""
    calls: int = 0            # upstream calls this lookup spent (for budget metrics)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
class VerificationLayer(str, Enum):
    SOURCE_IDENTITY = "source_identity"            # L1 does the cited document exist, is the id right
    VERSION_IDENTITY = "version_identity"          # L2 is it the version for the relevant date
    CITATION_IDENTITY = "citation_identity"        # L3 does the article/항/호/별표 exist in that version
    TEXT_CORRESPONDENCE = "text_correspondence"    # L4 does the quoted text / heading match
    CLAIM_SUPPORT = "claim_support"                # L5 does the statement follow from the evidence
    APPLICABILITY = "applicability"                # L6 are status/subcode/procedure/date conditions met
    CONFLICT_UNCERTAINTY = "conflict_uncertainty"  # L7 does other evidence conflict, is it stale

    @property
    def order(self) -> int:
        return _LAYER_ORDER.index(self) + 1


_LAYER_ORDER: List[VerificationLayer] = [
    VerificationLayer.SOURCE_IDENTITY,
    VerificationLayer.VERSION_IDENTITY,
    VerificationLayer.CITATION_IDENTITY,
    VerificationLayer.TEXT_CORRESPONDENCE,
    VerificationLayer.CLAIM_SUPPORT,
    VerificationLayer.APPLICABILITY,
    VerificationLayer.CONFLICT_UNCERTAINTY,
]


class LayerOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"                      # the check ran to completion on retrieved evidence and the claim did not pass
    UNAVAILABLE = "unavailable"        # could not be checked; never evidence of absence
    NEEDS_REVIEW = "needs_review"      # checkable only by a person (transitional rule, discretion …)
    NOT_APPLICABLE = "not_applicable"  # e.g. no quote to compare


class VerificationCode(str, Enum):
    # L1
    SOURCE_VERIFIED = "source_verified"
    SOURCE_NOT_FOUND = "source_not_found"
    SOURCE_AMBIGUOUS = "source_ambiguous"                  # similar-title substitution risk
    HISTORICAL_LOOKUP_REQUIRED = "historical_lookup_required"  # absent from current index; may be renamed/repealed
    SOURCE_REPEALED = "source_repealed"
    # L2
    VERSION_VERIFIED = "version_verified"
    WRONG_VERSION = "wrong_version"
    FUTURE_NOT_YET_EFFECTIVE = "future_not_yet_effective"
    SOURCE_OUTDATED = "source_outdated"
    VERSION_HISTORY_INCOMPLETE = "version_history_incomplete"
    # L3
    CITATION_VERIFIED = "citation_verified"
    CITATION_NOT_FOUND = "citation_not_found"
    # L4
    TEXT_MATCH_VERIFIED = "text_match_verified"
    TEXT_MISMATCH = "text_mismatch"
    # L5
    CLAIM_SUPPORTED = "claim_supported"
    CLAIM_PARTIALLY_SUPPORTED = "claim_partially_supported"
    CLAIM_UNSUPPORTED = "claim_unsupported"
    # L6
    APPLICABILITY_ESTABLISHED = "applicability_established"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    SUBCODE_APPLICABILITY_UNPROVEN = "subcode_applicability_unproven"
    PROCEDURE_SCOPE_MISMATCH = "procedure_scope_mismatch"
    TRANSITIONAL_RULE_UNRESOLVED = "transitional_rule_unresolved"
    # L7
    NO_CONFLICT_DETECTED = "no_conflict_detected"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    MANUAL_PREDATES_LAW_CHANGE = "manual_predates_law_change"
    # any layer
    VERIFICATION_UNAVAILABLE = "verification_unavailable"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    NOT_CHECKED = "not_checked"


@dataclass(frozen=True)
class LayerResult:
    layer: VerificationLayer
    outcome: LayerOutcome
    code: VerificationCode
    detail: str = ""
    evidence_ids: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer.value,
            "outcome": self.outcome.value,
            "code": self.code.value,
            "detail": self.detail,
            "evidence_ids": list(self.evidence_ids),
        }


class OverallStatus(str, Enum):
    FAILED = "failed"
    VERIFICATION_UNAVAILABLE = "verification_unavailable"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    VERIFIED_PARTIAL = "verified_partial"     # passed some layers, later layers not checked
    VERIFIED = "verified"                     # every layer passed or not applicable


@dataclass(frozen=True)
class ClaimVerification:
    claim_id: str
    layers: Tuple[LayerResult, ...]

    def layer(self, layer: VerificationLayer) -> Optional[LayerResult]:
        for result in self.layers:
            if result.layer is layer:
                return result
        return None

    def overall(self) -> OverallStatus:
        outcomes = [r.outcome for r in self.layers]
        if LayerOutcome.FAIL in outcomes:
            return OverallStatus.FAILED
        if LayerOutcome.UNAVAILABLE in outcomes:
            return OverallStatus.VERIFICATION_UNAVAILABLE
        if LayerOutcome.NEEDS_REVIEW in outcomes:
            return OverallStatus.HUMAN_REVIEW_REQUIRED
        checked = {r.layer for r in self.layers}
        if all(layer in checked for layer in _LAYER_ORDER):
            return OverallStatus.VERIFIED
        return OverallStatus.VERIFIED_PARTIAL

    def highest_verified_layer(self) -> int:
        """Number of consecutive layers (from L1) that passed or were not applicable."""
        by_layer = {r.layer: r.outcome for r in self.layers}
        count = 0
        for layer in _LAYER_ORDER:
            if by_layer.get(layer) in (LayerOutcome.PASS, LayerOutcome.NOT_APPLICABLE):
                count += 1
            else:
                break
        return count

    def codes(self) -> List[str]:
        return [r.code.value for r in self.layers]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "overall": self.overall().value,
            "highest_verified_layer": self.highest_verified_layer(),
            "layers": [r.to_dict() for r in self.layers],
        }


# ---------------------------------------------------------------------------
# Applicability scope and conflicts
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Scope:
    """Which statuses / procedures a piece of evidence speaks to.

    ``subcodes`` empty with ``status_codes`` set means "stated for the parent";
    that does NOT establish a rule for any particular subcode.
    ``all_subcodes_explicit`` is True only when the source itself says the rule
    applies to every subcode of the parent.
    """

    status_codes: Tuple[str, ...] = ()
    subcodes: Tuple[str, ...] = ()
    procedures: Tuple[str, ...] = ()
    all_subcodes_explicit: bool = False
    condition_kind: str = "always"        # one of CONDITION_KINDS
    note: str = ""


@dataclass(frozen=True)
class ConflictRecord:
    topic: str
    evidence_ids: Tuple[str, ...]
    kind: str            # "value_mismatch" | "manual_predates_law_change" | "scope_mismatch"
    detail: str
    requires_review: bool = True


# ---------------------------------------------------------------------------
# Adapter boundary payloads
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProvisionText:
    """Text of one article (or annex/addendum unit) in one version.

    ``paragraphs`` maps a printed paragraph number to its text, ``items`` maps
    "paragraph:item" (paragraph 0 when the article has no paragraphs) to text.
    Heading units (조문여부 = 전문, e.g. "제1장 총칙") are never returned as a
    provision: adapters must filter them.

    ``structure_complete`` is True only when every 항 / 호 / 목 of this
    provision was parsed. Only then is the absence of a cited sub-unit
    authoritative (L3 ``citation_not_found``); otherwise it is unavailable.
    """

    evidence_id: str
    stable_id: str
    version_key: Tuple[str, Optional[str]]
    provision_key: str
    heading: Optional[str]
    text: str
    paragraphs: Mapping[int, str] = field(default_factory=dict)
    items: Mapping[str, str] = field(default_factory=dict)
    scope: Optional[Scope] = None
    official_url: Optional[str] = None
    provenance: ProvenanceStatus = ProvenanceStatus.UNVERIFIED
    structure_complete: bool = False

    def full_text(self) -> str:
        parts = [self.text] + [self.paragraphs[k] for k in sorted(self.paragraphs)] + [
            self.items[k] for k in sorted(self.items)
        ]
        return "\n".join(p for p in parts if p)


@dataclass(frozen=True)
class Addendum:
    """One 부칙 clause of a version, as read from the source."""

    stable_id: str
    version_key: Tuple[str, Optional[str]]
    text: str
    kind: str = "other"          # "effective_date" | "transitional" | "application" | "other"
    mentions: Tuple[str, ...] = ()   # provision article keys the clause names


@dataclass(frozen=True)
class GuidanceItem:
    """Operational guidance (manual edition, HiKorea page) on one topic."""

    evidence_id: str
    family: SourceFamily
    topic: str
    text: str
    value: Optional[str] = None          # normalized comparable value, e.g. "cash_only"
    edition_date: Optional[dt.date] = None
    review_state: str = "unreviewed"     # manual approval state as recorded by the registry
    scope: Optional[Scope] = None


@dataclass(frozen=True)
class ClaimInput:
    """A statement to verify, as produced by a model or written in a test."""

    claim_id: str
    text: str
    citations: Tuple[str, ...] = ()
    quoted_text: Optional[str] = None
    numbers: Tuple[str, ...] = ()        # numeric expressions the claim asserts, e.g. ("14일",)
    scope: Optional[Scope] = None        # what the claim says it applies to
    topic: Optional[str] = None          # comparable topic key for conflict checks
    value: Optional[str] = None          # normalized value the claim asserts on that topic
    asserted_version_key: Optional[Tuple[str, Optional[str]]] = None
    context_title: Optional[str] = None  # law that 같은 법 / 영 / 규칙 refer to


@dataclass(frozen=True)
class TemporalAssessment:
    candidates: Tuple[SourceVersion, ...]
    warnings: Tuple[TemporalWarning, ...]
    anchor: Optional[AnchorKind]
    anchor_date: Optional[dt.date]
    determination: str = "candidate_only"   # never a final legal determination
    detail: str = ""

    def candidate_keys(self) -> List[List[Optional[str]]]:
        return [list(v.key) for v in self.candidates]


try:  # typing.Protocol is available on every supported Python (3.8+)
    from typing import Protocol
except ImportError:  # pragma: no cover
    Protocol = object  # type: ignore[assignment,misc]


class LegalSourceAdapter(Protocol):
    """What WLIE needs from a legal source. Every method reports a LookupResult.

    Implementations: a fixture adapter over source bundles (offline, tests and
    benchmark) and, later, an adapter over the backend law_tools client.
    """

    def resolve_title(self, title: str, *, as_of: Optional[dt.date] = None) -> Tuple[LookupResult, List[SourceIdentity]]:
        ...

    def list_versions(self, stable_id: str) -> Tuple[LookupResult, List[SourceVersion]]:
        ...

    def get_provision(
        self, stable_id: str, version_key: Tuple[str, Optional[str]], provision: ProvisionRef
    ) -> Tuple[LookupResult, Optional[ProvisionText]]:
        ...

    def get_addenda(self, stable_id: str, version_key: Tuple[str, Optional[str]]) -> Tuple[LookupResult, List[Addendum]]:
        ...

    def guidance(self, topic: str) -> Tuple[LookupResult, List[GuidanceItem]]:
        ...


# ---------------------------------------------------------------------------
# Procedures
# ---------------------------------------------------------------------------
#: Fine-grained procedure ids: the 16 ids of data/status-guidance-202609.json.
FINE_PROCEDURES: Tuple[str, ...] = (
    "visa_issuance",
    "visa_issuance_confirmation",
    "electronic_visa",
    "status_grant",
    "status_change",
    "extension",
    "registration",
    "card_reissue",
    "activities_outside_status",
    "part_time_work",
    "workplace_change",
    "workplace_report",
    "reentry",
    "residence_report",
    "registration_info_report",
    "program_condition_change",
)

#: The backend knowledge canonical keys (services.knowledge.models.ALL_PROCEDURES).
COARSE_PROCEDURES: Tuple[str, ...] = (
    "extension",
    "status_change",
    "registration",
    "reentry",
    "activities_outside_status",
    "workplace_change",
    "status_grant",
    "address_report",
    "reporting_duty",
    "visa_issuance",
    "visa_issuance_confirmation",
)

#: Fine → coarse. None means the backend taxonomy has no equivalent, so a
#: backend classifier can never be scored correct or wrong on that item's
#: coarse label (the runner reports it as "not scorable").
FINE_TO_COARSE: Dict[str, Optional[str]] = {
    "visa_issuance": "visa_issuance",
    "visa_issuance_confirmation": "visa_issuance_confirmation",
    "electronic_visa": None,
    "status_grant": "status_grant",
    "status_change": "status_change",
    "extension": "extension",
    "registration": "registration",
    "card_reissue": None,
    "activities_outside_status": "activities_outside_status",
    "part_time_work": None,
    "workplace_change": "workplace_change",
    "workplace_report": None,
    "reentry": "reentry",
    "residence_report": "address_report",
    "registration_info_report": "reporting_duty",
    "program_condition_change": None,
}

VISA_SCOPE_PROCEDURES = frozenset({"visa_issuance", "visa_issuance_confirmation", "electronic_visa"})


def procedure_scope(procedure: Optional[str]) -> Optional[str]:
    """'visa' (visa manual scope) or 'stay' (stay manual scope). Never mixed."""
    if procedure is None:
        return None
    return "visa" if procedure in VISA_SCOPE_PROCEDURES else "stay"


# ---------------------------------------------------------------------------
# Text helpers shared by every component
# ---------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    """NFC, collapse whitespace, unify the interpunct variants used in statutes."""
    value = unicodedata.normalize("NFC", text or "")
    value = value.replace("ㆍ", "·").replace("・", "·").replace("‧", "·")
    return " ".join(value.split())


def compact(text: str) -> str:
    """Whitespace-free, interpunct-free form used for containment checks."""
    return normalize_text(text).replace(" ", "").replace("·", "")


def sha256_text(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def parse_date(value: Any) -> Optional[dt.date]:
    """Accept 'YYYY-MM-DD', 'YYYYMMDD', a date, or None."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.date):
        return value
    raw = str(value).strip()
    if len(raw) == 8 and raw.isdigit():
        return dt.date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
    return dt.date.fromisoformat(raw)


def iter_layer_order() -> Iterable[VerificationLayer]:
    return iter(_LAYER_ORDER)


__all__: Sequence[str] = [name for name in dir() if not name.startswith("_")]
