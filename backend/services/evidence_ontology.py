"""Generalized official-evidence retrieval ontology for Paradiso.

This module is the single, reusable ontology + query-planning layer for the
official-evidence retrieval pipeline. It exists so the system reasons over
structured *issue dimensions* (status roles, activities, procedures, legal
issues, source families, evidence goals) rather than memorizing individual
scenarios such as H-1, G-1-5, E-7, F-2-99, C-3 or D-2.

It deliberately holds NO per-visa-code business logic. Visa codes only enter as
*values* of status-role dimensions (current / previous / target), never as
branch conditions. The example questions in the test suite are regression and
evaluation cases — they must not become special cases here.

Pipeline position::

    question
      → immigration fact extraction        (legal_analysis.extract_immigration_facts)
      → activity / procedure classification (legal_analysis.classify_activity_types)
      → legal issue classification          (legal_analysis.classify_legal_issue_types)
      → source family routing               (this module: route_source_families)
      → query generation                    (this module: plan_evidence_queries)
      → official source retrieval           (law_tools.retrieve_planned_official_sources)
      → evidence normalization              (law_tools._normalize_candidate)
      → relevance scoring                   (legal_analysis.score_evidence_relevance)
      → answer confidence level             (answer_quality / legal_analysis)
      → source panel state                  (paradiso_backend._derive_source_panel_metadata)

Design rules:
  * Deterministic and secret-free (no network, no OC/API-key handling).
  * Korean official terms are preferred for Korean-source retrieval.
  * Unsupported source families are reported as ``unsupported`` /
    ``planned_not_wired``, never as a parser ``bad_response``.
  * Related / analogical / background goals are never promoted to ``direct``.

This module avoids importing ``legal_analysis`` at module load time (it is
imported lazily inside the functions that need the classifiers) so that
``legal_analysis`` can import the routing table from here without a cycle.

See docs/data/GENERALIZED_OFFICIAL_EVIDENCE_RETRIEVAL_SYSTEM_2026_05.md.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

ONTOLOGY_VERSION = "2026-05-generalized-official-evidence-retrieval-v1"

# ---------------------------------------------------------------------------
# Part A — ontology dimensions
# ---------------------------------------------------------------------------

# Status roles. Visa codes are VALUES of these roles, never branch conditions.
STATUS_ROLES: Tuple[str, ...] = (
    "current_status", "current_parent_status", "current_sub_status",
    "previous_status", "previous_parent_status", "previous_sub_status",
    "target_status", "target_parent_status", "target_sub_status",
    "status_transition_detected",
)

# Status families — generalized groupings used for routing/query expansion.
# Membership is by parent code only; no scenario-specific behavior.
STATUS_FAMILIES: Tuple[str, ...] = (
    "study", "work", "residence", "short_term", "humanitarian",
    "jobseeking", "diplomatic_official", "other",
)
_STATUS_FAMILY_BY_PARENT: Dict[str, str] = {
    "D-2": "study", "D-4": "study",
    "E-1": "work", "E-2": "work", "E-3": "work", "E-4": "work", "E-5": "work",
    "E-6": "work", "E-7": "work", "E-9": "work", "E-10": "work",
    "C-4": "short_term", "H-2": "work", "H-1": "work",
    "F-2": "residence", "F-4": "residence", "F-5": "residence", "F-6": "residence",
    "F-1": "residence", "F-3": "residence",
    "C-1": "short_term", "C-3": "short_term", "B-1": "short_term", "B-2": "short_term",
    "D-10": "jobseeking",
    "G-1": "humanitarian",
    "A-1": "diplomatic_official", "A-2": "diplomatic_official", "A-3": "diplomatic_official",
}

# Korean status-family names for query expansion (official phrasing).
STATUS_FAMILY_TERMS_KO: Dict[str, str] = {
    "study": "유학 체류자격",
    "work": "취업 체류자격",
    "residence": "거주 체류자격",
    "short_term": "단기 체류자격",
    "humanitarian": "인도적 체류자격",
    "jobseeking": "구직 체류자격",
    "diplomatic_official": "외교 공무 체류자격",
    "other": "체류자격",
}
STATUS_FAMILY_TERMS_EN: Dict[str, str] = {
    "study": "study status",
    "work": "work status",
    "residence": "residence status",
    "short_term": "short-term status",
    "humanitarian": "humanitarian status",
    "jobseeking": "job-seeking status",
    "diplomatic_official": "diplomatic/official status",
    "other": "sojourn status",
}

# Activity dimensions (canonical) — mirror legal_analysis.ACTIVITY_TYPES.
ACTIVITY_DIMENSIONS: Tuple[str, ...] = (
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

# Procedure dimensions — official Korean immigration procedures.
PROCEDURE_DIMENSIONS: Tuple[str, ...] = (
    "extension", "status_change", "activities_outside_status",
    "workplace_change_addition", "foreigner_registration",
    "address_or_residence_report", "reentry_permit", "status_grant",
    "document_checklist", "deadline_or_reporting_duty", "overstay_or_risk",
)

# Legal issue dimensions — mirror legal_analysis.LEGAL_ISSUE_TYPES plus the
# deadline_trigger dimension named in the ontology spec.
#
# The three adjudicative-leaning dimensions at the end (denial/remedy,
# constitutional rights, ambiguous interpretation) are the only issues that
# route precedent-family / constitutional-decision sources. They are detected
# with high-precision signals so ordinary document/registration/work questions
# never over-query case law.
LEGAL_ISSUE_DIMENSIONS: Tuple[str, ...] = (
    "activity_scope", "outside_status_activity", "status_purpose_alignment",
    "reporting_duty", "registration_or_residence_report", "registration_deadline",
    "workplace_change_addition", "status_change", "documents_needed",
    "employment_restriction", "study_on_non_study_status",
    "work_on_non_work_status", "post_status_change_residual_duty",
    "approval_condition", "deadline_trigger", "overstay_or_risk",
    "nationality_or_refugee_context", "extension", "reentry",
    "denial_revocation_or_remedy", "constitutional_or_fundamental_rights",
    "discretionary_or_ambiguous_interpretation",
    "legal_general", "non_immigration_adjacent_issue",
)

# Source families. ``wired`` means an adapter actually retrieves them today.
SOURCE_FAMILIES: Tuple[str, ...] = (
    "manual", "statute", "enforcement_decree", "enforcement_rule",
    "administrative_rule", "legal_term", "legal_interpretation",
    "administrative_appeal", "precedent", "constitutional_decision",
    "intelligent_search",
)
WIRED_SOURCE_FAMILIES: frozenset = frozenset({
    "manual", "statute", "enforcement_decree", "enforcement_rule",
    "administrative_rule", "legal_term",
})
UNWIRED_SOURCE_FAMILIES: frozenset = frozenset(
    f for f in SOURCE_FAMILIES if f not in WIRED_SOURCE_FAMILIES
)

# Evidence goals — the *intended* role of a planned query / retrieved item.
EVIDENCE_GOALS: Tuple[str, ...] = (
    "direct", "contextual", "analogical", "background", "not_relevant",
)

# ---------------------------------------------------------------------------
# Part B2 — authority hierarchy + public grounding-item schema
#
# A single, reusable place that ranks official sources by binding authority and
# projects internal retrieval fields onto the compact, public structured
# evidence item the answer prompt / source panel consume. This is additive: it
# never replaces the internal normalized-candidate shape, it only *views* it.
#
# Authority levels (1 = strongest binding authority, 7 = non-source inference):
#   1  Statutes / binding legal provisions
#   2  Enforcement decrees and rules, official legal regulations
#   3  Ministry of Justice / HiKorea official manuals and public guidance
#   4  Official notices, forms, administrative guidance, official glossaries
#   5  Case law, administrative adjudication, precedent-like materials
#   6  Paradiso internal explanatory data
#   7  LLM inference (NOT official source material)
# ---------------------------------------------------------------------------
AUTHORITY_LEVEL_LABELS: Dict[int, str] = {
    1: "statute / binding legal provision",
    2: "enforcement decree or rule / official regulation",
    3: "Ministry of Justice / HiKorea manual or public guidance",
    4: "official notice, form, administrative guidance, or glossary",
    5: "case law / administrative adjudication / precedent",
    6: "Paradiso internal explanatory data",
    7: "LLM inference (not official source material)",
}

# Map every internal source_type / source_family token to an authority level.
# Unknown tokens default to 6 (treated as internal explanatory data, never as
# binding authority) so a mislabeled source can never be over-ranked.
_AUTHORITY_LEVEL_BY_SOURCE_TYPE: Dict[str, int] = {
    "statute": 1, "law": 1,
    "enforcement_decree": 2, "enforcement_rule": 2, "regulation": 2,
    "administrative_rule": 2, "admin_rule": 2,
    "manual": 3, "hikorea": 3,
    "notice": 4, "form": 4, "administrative_guidance": 4,
    "legal_term": 4, "law_term": 4, "lstrm": 4,
    "legal_interpretation": 5, "administrative_appeal": 5,
    "precedent": 5, "constitutional_decision": 5, "case_law": 5,
    "internal": 6, "visa_data": 6, "doc_master": 6,
    "inference": 7,
}

# Project fine-grained internal source types onto the public source-type
# vocabulary used by the structured evidence item / source panel.
_PUBLIC_SOURCE_TYPE_BY_SOURCE_TYPE: Dict[str, str] = {
    "statute": "statute", "law": "statute",
    "enforcement_decree": "regulation", "enforcement_rule": "regulation",
    "administrative_rule": "regulation", "admin_rule": "regulation",
    "regulation": "regulation",
    "manual": "manual", "hikorea": "hikorea",
    "notice": "notice", "form": "notice", "administrative_guidance": "notice",
    "legal_term": "internal", "law_term": "internal", "lstrm": "internal",
    "legal_interpretation": "case_law", "administrative_appeal": "case_law",
    "precedent": "case_law", "constitutional_decision": "case_law",
    "case_law": "case_law",
    "internal": "internal", "visa_data": "internal", "doc_master": "internal",
    "inference": "inference",
}

# Map the internal relevance vocabulary (legal_analysis.RELEVANCE_*) onto the
# public directness vocabulary the task / source panel use. Anything unknown
# degrades to NOT_FOUND so the answer never over-claims a match.
PUBLIC_DIRECTNESS_BY_RELEVANCE: Dict[str, str] = {
    "direct": "DIRECT",
    "related": "PARTIAL",
    "background": "GENERAL",
    "analogical": "ANALOGICAL",
    "not_relevant": "NOT_FOUND",
    "": "NOT_FOUND",
}


def authority_level_for(source_type: Optional[str]) -> int:
    """Return the binding-authority level (1-7) for an internal source type."""
    return _AUTHORITY_LEVEL_BY_SOURCE_TYPE.get(str(source_type or "").strip().lower(), 6)


def public_source_type_for(source_type: Optional[str]) -> str:
    """Project an internal source type onto the public source-type vocabulary."""
    return _PUBLIC_SOURCE_TYPE_BY_SOURCE_TYPE.get(str(source_type or "").strip().lower(), "internal")


def public_directness_for(relevance: Optional[str]) -> str:
    """Project the internal relevance label onto the public directness label."""
    return PUBLIC_DIRECTNESS_BY_RELEVANCE.get(str(relevance or "").strip().lower(), "NOT_FOUND")


def _first_nonempty(item: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value not in (None, "", [], {}):
            return str(value)
    return ""


def to_grounding_item(
    item: Dict[str, Any],
    *,
    relevance: str = "",
    relevance_reason: str = "",
    excerpt_chars: int = 400,
) -> Dict[str, Any]:
    """Project one internal evidence dict onto the public structured schema.

    The output is the compact, secret-free grounding item the answer prompt and
    source panel consume. It preserves whatever the internal item actually has
    and never fabricates fields: missing values stay empty rather than guessed.
    ``directness`` defaults to NOT_FOUND and ``authority_level`` to 6 so an
    under-described item can never be presented as binding direct authority.
    """
    if not isinstance(item, dict):
        item = {}
    raw_type = str(item.get("source_type") or item.get("target") or "").strip().lower()
    rel = relevance or str(item.get("relevance") or "")
    excerpt = _first_nonempty(item, "excerpt", "summary", "definition", "snippet", "holdingSummary")
    return {
        "source_id": _first_nonempty(
            item, "source_id", "law_id", "law_serial_no", "reference",
            "case_number", "serialNumber", "decisionNumber",
        ),
        "source_title": _first_nonempty(
            item, "source_title", "law_name", "title", "term", "case_name",
            "sourceName",
        ) or "official source",
        "source_type": public_source_type_for(raw_type),
        "version_or_date": _first_nonempty(
            item, "version_or_date", "enforcement_date", "promulgation_date",
            "decision_date", "decisionDate", "source_date", "source_revision_date",
        ),
        "authority_level": authority_level_for(raw_type),
        "excerpt": excerpt[:excerpt_chars],
        "page_or_section": _first_nonempty(
            item, "page_or_section", "article", "section", "page_range",
        ),
        "url": _first_nonempty(item, "url", "source_url", "sanitized_source_url"),
        "directness": public_directness_for(rel),
        "relevance_reason": (relevance_reason or _first_nonempty(item, "relevance_reason")),
    }


# ---------------------------------------------------------------------------
# Part C — generalized source-family routing (single source of truth)
#
# Keyed by legal issue dimension. Each value is an ordered priority list of
# source families. legal_analysis.build_generalized_source_plan consumes this
# table so routing lives in exactly one place. Manual leads for procedure /
# document / registration issues; statute family leads for activity-scope /
# authority issues.
# ---------------------------------------------------------------------------
_ACTIVITY_AUTHORITY_ROUTE = (
    "statute", "enforcement_decree", "enforcement_rule", "administrative_rule",
    "legal_interpretation", "administrative_appeal", "manual",
)
_REGISTRATION_ROUTE = (
    "manual", "statute", "enforcement_decree", "enforcement_rule",
    "administrative_rule", "legal_interpretation",
)
_PROCEDURE_ROUTE = (
    "manual", "statute", "enforcement_decree", "enforcement_rule",
    "administrative_rule", "legal_interpretation",
)
# Adjudicative-leaning routes. These are the ONLY routes that pull court
# precedent / constitutional-decision families. They lead with the controlling
# statute/decree (the binding rule) and only then add analogical adjudicative
# sources (administrative appeal decisions, court precedent, constitutional
# decisions, legal interpretations). The manual is included for remedy/denial
# questions because the official manual documents objection/appeal procedure.
_DENIAL_REMEDY_ROUTE = (
    "manual", "statute", "enforcement_decree", "enforcement_rule",
    "administrative_appeal", "precedent", "legal_interpretation",
)
_CONSTITUTIONAL_RIGHTS_ROUTE = (
    "statute", "enforcement_decree", "constitutional_decision",
    "precedent", "legal_interpretation",
)
_AMBIGUOUS_INTERPRETATION_ROUTE = (
    "statute", "enforcement_decree", "enforcement_rule",
    "legal_interpretation", "administrative_appeal", "precedent",
)

SOURCE_FAMILY_ROUTING: Dict[str, Tuple[str, ...]] = {
    "documents_needed": ("manual", "statute", "enforcement_rule"),
    "activity_scope": _ACTIVITY_AUTHORITY_ROUTE,
    "outside_status_activity": _ACTIVITY_AUTHORITY_ROUTE,
    "status_purpose_alignment": _ACTIVITY_AUTHORITY_ROUTE,
    "employment_restriction": _ACTIVITY_AUTHORITY_ROUTE,
    "study_on_non_study_status": _ACTIVITY_AUTHORITY_ROUTE,
    "work_on_non_work_status": _ACTIVITY_AUTHORITY_ROUTE,
    "status_change": ("manual", "statute", "enforcement_decree", "legal_interpretation", "administrative_appeal"),
    "reporting_duty": _REGISTRATION_ROUTE,
    "workplace_change_addition": _REGISTRATION_ROUTE,
    "registration_or_residence_report": _REGISTRATION_ROUTE,
    "registration_deadline": _REGISTRATION_ROUTE,
    "deadline_trigger": _REGISTRATION_ROUTE,
    # Overstay / removal / departure-order / sanction questions are adjudicative:
    # add administrative-appeal and court-precedent (analogical) sources.
    "overstay_or_risk": ("statute", "enforcement_decree", "enforcement_rule", "administrative_appeal", "precedent"),
    # Refugee/humanitarian procedural disputes can hinge on appeal/precedent.
    "nationality_or_refugee_context": ("statute", "enforcement_decree", "enforcement_rule", "legal_interpretation", "administrative_appeal", "precedent", "manual"),
    "post_status_change_residual_duty": ("manual", "statute", "enforcement_rule", "administrative_rule", "legal_interpretation"),
    "reentry": _PROCEDURE_ROUTE,
    "extension": _PROCEDURE_ROUTE,
    "approval_condition": _PROCEDURE_ROUTE,
    # Adjudicative dimensions (high-precision detection in legal_analysis).
    "denial_revocation_or_remedy": _DENIAL_REMEDY_ROUTE,
    "constitutional_or_fundamental_rights": _CONSTITUTIONAL_RIGHTS_ROUTE,
    "discretionary_or_ambiguous_interpretation": _AMBIGUOUS_INTERPRETATION_ROUTE,
}
# Default route for issues without an explicit rule (legal_general,
# non_immigration_adjacent_issue, ...).
DEFAULT_ROUTING: Tuple[str, ...] = (
    "manual", "statute", "enforcement_decree", "enforcement_rule", "legal_term",
)
# Used only when no issue produced any family at all.
FALLBACK_WHEN_EMPTY: Tuple[str, ...] = ("manual", "statute", "legal_term")


def source_families_for_issue(issue: str) -> Tuple[str, ...]:
    """Generalized routing for a single legal issue dimension."""
    return SOURCE_FAMILY_ROUTING.get(str(issue), DEFAULT_ROUTING)


def route_source_families(issues: Sequence[str]) -> List[str]:
    """Ordered, deduped, validated source-family plan for a set of issues.

    Iterates issues in order, expanding each via the routing table, and keeps
    the first occurrence of each family. The result is filtered to known
    SOURCE_FAMILIES. Returns ``[]`` when ``issues`` is empty (callers apply
    FALLBACK_WHEN_EMPTY).
    """
    families: List[str] = []
    for issue in issues or []:
        for fam in source_families_for_issue(issue):
            if fam in SOURCE_FAMILIES and fam not in families:
                families.append(fam)
    return families


def is_source_family_wired(family: str) -> bool:
    return family in WIRED_SOURCE_FAMILIES


def source_family_support_status(family: str) -> str:
    """Coarse, non-error support state for a family ('wired'/'planned_not_wired').

    Never returns a parser error code — an unwired family is a planning state,
    not a bad response (Part C).
    """
    return "wired" if family in WIRED_SOURCE_FAMILIES else "planned_not_wired"


# ---------------------------------------------------------------------------
# Part B — composable query templates and the deterministic query planner
# ---------------------------------------------------------------------------
SOURCE_FAMILY_TERMS_KO: Dict[str, str] = {
    "manual": "체류자격별 안내매뉴얼",
    "statute": "출입국관리법",
    "enforcement_decree": "출입국관리법 시행령",
    "enforcement_rule": "출입국관리법 시행규칙",
    "administrative_rule": "행정규칙",
    "legal_interpretation": "법령해석",
    "administrative_appeal": "행정심판",
    "precedent": "판례",
    "constitutional_decision": "헌법재판소 결정",
    "legal_term": "법령용어",
    "intelligent_search": "지능형 검색",
}
SOURCE_FAMILY_TERMS_EN: Dict[str, str] = {
    "manual": "residence guidance manual",
    "statute": "Immigration Control Act",
    "enforcement_decree": "Immigration Control Act Enforcement Decree",
    "enforcement_rule": "Immigration Control Act Enforcement Rule",
    "administrative_rule": "administrative rule",
    "legal_interpretation": "legal interpretation",
    "administrative_appeal": "administrative appeal",
    "precedent": "court precedent",
    "constitutional_decision": "constitutional court decision",
    "legal_term": "legal term",
    "intelligent_search": "intelligent search",
}

# ---------------------------------------------------------------------------
# Source-family definitions (Phase 4 scaffold)
#
# Additive metadata layer over SOURCE_FAMILIES. This does NOT change the coarse
# ``source_family_support_status`` contract (wired / planned_not_wired); it adds
# a richer, public-safe definition per family for the precedent-family scaffold:
# stable id, KO/EN public labels, citation-grade capability, a baseline live
# adapter status, and the public-safe "not connected / unavailable" wording.
# ---------------------------------------------------------------------------
LIVE_ADAPTER_STATUSES: Tuple[str, ...] = (
    "wired", "scaffold_only", "not_configured", "temporarily_unavailable",
)

# Families whose retrieval interface is scaffolded — normalizers, routing, and
# (for precedent) a target=prec list-search builder + optional shape-capture
# hook — but which are NOT yet verified live citation-grade adapters. In this
# scaffold PR they never auto-fire a live call in the production retrieval
# fan-out; they surface as public-safe "not yet connected" source limitations.
SCAFFOLD_ONLY_SOURCE_FAMILIES: frozenset = frozenset({
    "legal_interpretation", "administrative_appeal", "precedent",
    "constitutional_decision", "intelligent_search",
})

# Families that, when fully wired, can anchor a *direct* citation: a statute /
# decree / rule article, an official manual section, an issued interpretation,
# or a case / decision identity. legal_term is background; intelligent_search is
# an aggregator. Capability here means "may produce citation-grade evidence",
# not "is wired today".
CITATION_GRADE_CAPABLE_FAMILIES: frozenset = frozenset({
    "manual", "statute", "enforcement_decree", "enforcement_rule",
    "administrative_rule", "legal_interpretation", "administrative_appeal",
    "precedent", "constitutional_decision",
})

# The four adjudicative precedent-family sources (case law / decisions /
# interpretations). Court precedent + administrative appeal + constitutional
# decision are decision-bodies; legal interpretation is an authoritative
# reading. Used for public-safe labelling and citation grading.
ADJUDICATIVE_SOURCE_FAMILIES: frozenset = frozenset({
    "precedent", "administrative_appeal", "constitutional_decision",
    "legal_interpretation",
})

# Public-safe "direct grounding not available" wording per family. These never
# expose raw adapter codes (unsupported / planned_not_wired / scaffold_only).
SOURCE_FAMILY_PUBLIC_UNAVAILABLE_KO: Dict[str, str] = {
    "precedent": "판례 직접 근거는 아직 연결되지 않았습니다.",
    "administrative_appeal": "행정심판례 직접 근거는 현재 사용할 수 없습니다.",
    "legal_interpretation": "법령해석례 직접 근거는 현재 사용할 수 없습니다.",
    "constitutional_decision": "헌재결정례 직접 근거는 현재 사용할 수 없습니다.",
}
SOURCE_FAMILY_PUBLIC_UNAVAILABLE_EN: Dict[str, str] = {
    "precedent": "Direct court-precedent grounding is not connected yet.",
    "administrative_appeal": "Direct administrative-appeal grounding is currently unavailable.",
    "legal_interpretation": "Direct legal-interpretation grounding is currently unavailable.",
    "constitutional_decision": "Direct constitutional-decision grounding is currently unavailable.",
}


def source_family_live_adapter_status(family: str) -> str:
    """Baseline live-adapter status for a family (Phase 4 enum).

    Returns one of ``LIVE_ADAPTER_STATUSES``. This is the *static* baseline:
    ``wired`` for families with a verified live adapter, ``scaffold_only`` for
    families with a scaffolded-but-unverified interface, and ``not_configured``
    for an unknown family with no adapter at all. The runtime
    ``not_configured`` (LAW_API_OC missing) and ``temporarily_unavailable``
    (API error) states are layered on at retrieval time, not here.
    """
    fam = str(family or "")
    if fam in WIRED_SOURCE_FAMILIES:
        return "wired"
    if fam in SOURCE_FAMILIES:
        return "scaffold_only"
    return "not_configured"


def is_citation_grade_capable(family: str) -> bool:
    """Whether a family can (when wired) anchor a direct citation."""
    return str(family or "") in CITATION_GRADE_CAPABLE_FAMILIES


def source_family_public_unavailable_label(family: str, *, lang: str = "ko") -> str:
    """Public-safe 'direct grounding unavailable' label for a family.

    Falls back to a generic stored-official-sources message for families
    without a specific adjudicative label. Never returns a raw status code.
    """
    fam = str(family or "")
    if str(lang or "").lower().startswith("en"):
        return SOURCE_FAMILY_PUBLIC_UNAVAILABLE_EN.get(
            fam, "Direct grounding for this source is currently unavailable."
        )
    return SOURCE_FAMILY_PUBLIC_UNAVAILABLE_KO.get(
        fam, "해당 출처의 직접 근거는 현재 사용할 수 없습니다."
    )


def source_family_definition(family: str) -> Dict[str, Any]:
    """Public-safe normalized definition for one source family."""
    fam = str(family or "")
    return {
        "family": fam,
        "labelKo": SOURCE_FAMILY_TERMS_KO.get(fam, fam),
        "labelEn": SOURCE_FAMILY_TERMS_EN.get(fam, fam),
        "supportStatus": source_family_support_status(fam),
        "liveAdapterStatus": source_family_live_adapter_status(fam),
        "citationGradeCapable": is_citation_grade_capable(fam),
        "adjudicative": fam in ADJUDICATIVE_SOURCE_FAMILIES,
        "publicUnavailableLabelKo": source_family_public_unavailable_label(fam, lang="ko"),
        "publicUnavailableLabelEn": source_family_public_unavailable_label(fam, lang="en"),
    }


def all_source_family_definitions() -> Dict[str, Dict[str, Any]]:
    """Definitions for every known source family (stable, deterministic)."""
    return {fam: source_family_definition(fam) for fam in SOURCE_FAMILIES}


# Issue → Korean concept phrase (official wording) + English concept keywords.
ISSUE_CONCEPT_KO: Dict[str, str] = {
    "activity_scope": "체류자격 활동범위",
    "outside_status_activity": "체류자격외활동 허가",
    "status_purpose_alignment": "체류자격 목적 부합",
    "reporting_duty": "신고의무",
    "registration_or_residence_report": "외국인등록 국내거소신고",
    "workplace_change_addition": "근무처 변경 추가 신고",
    "status_change": "체류자격 변경허가",
    "documents_needed": "구비서류 첨부서류",
    "employment_restriction": "취업활동 제한",
    "study_on_non_study_status": "체류자격외활동 유학 수학",
    "work_on_non_work_status": "체류자격외활동 취업",
    "post_status_change_residual_duty": "종전 체류자격 신고의무",
    "approval_condition": "허가조건 부관",
    "deadline_trigger": "신고 기한",
    "overstay_or_risk": "체류기간 초과 강제퇴거 출국명령",
    "nationality_or_refugee_context": "국적 난민 인도적체류",
    "extension": "체류기간 연장허가",
    "reentry": "재입국허가",
    "denial_revocation_or_remedy": "불허가 취소 처분 행정심판 구제",
    "constitutional_or_fundamental_rights": "기본권 위헌 헌법소원",
    "discretionary_or_ambiguous_interpretation": "재량 법령해석 유권해석",
    "legal_general": "체류자격",
    "non_immigration_adjacent_issue": "체류자격",
}
ISSUE_CONCEPT_EN: Dict[str, str] = {
    "activity_scope": "activity scope of status",
    "outside_status_activity": "activities outside status permission",
    "status_purpose_alignment": "status purpose alignment",
    "reporting_duty": "reporting duty",
    "registration_or_residence_report": "foreigner registration residence report",
    "workplace_change_addition": "workplace change or addition report",
    "status_change": "change of sojourn status",
    "documents_needed": "required documents checklist",
    "employment_restriction": "employment restriction",
    "study_on_non_study_status": "study on non-study status",
    "work_on_non_work_status": "work on non-work status",
    "post_status_change_residual_duty": "post status change residual duty",
    "approval_condition": "approval condition",
    "deadline_trigger": "reporting deadline",
    "overstay_or_risk": "overstay removal departure order",
    "nationality_or_refugee_context": "nationality refugee humanitarian",
    "extension": "extension of stay",
    "reentry": "re-entry permit",
    "denial_revocation_or_remedy": "denial revocation remedy administrative appeal",
    "constitutional_or_fundamental_rights": "fundamental rights constitutional decision",
    "discretionary_or_ambiguous_interpretation": "discretion legal interpretation",
    "legal_general": "sojourn status",
    "non_immigration_adjacent_issue": "sojourn status",
}

# Issue → procedure term (Korean) appended for procedure/registration issues.
ISSUE_PROCEDURE_TERM_KO: Dict[str, str] = {
    "documents_needed": "첨부서류",
    "status_change": "변경허가 신청",
    "registration_or_residence_report": "등록 신고",
    "reporting_duty": "신고",
    "workplace_change_addition": "변경 추가 신고",
    "extension": "연장 신청",
    "reentry": "재입국 허가",
    "overstay_or_risk": "출국 신고",
    "deadline_trigger": "기한",
    "approval_condition": "허가조건",
    "denial_revocation_or_remedy": "행정심판 청구",
    "discretionary_or_ambiguous_interpretation": "법령해석 요청",
}

_PRIMARY_AUTHORITY_FAMILIES = frozenset(
    {"manual", "statute", "enforcement_decree", "enforcement_rule"}
)
_ADJUDICATIVE_FAMILIES = frozenset(
    {"administrative_appeal", "precedent", "constitutional_decision"}
)


def status_family(parent_code: Optional[str]) -> str:
    """Generalized status-family for a parent code (e.g. D-2 -> 'study')."""
    if not parent_code:
        return "other"
    return _STATUS_FAMILY_BY_PARENT.get(str(parent_code).upper(), "other")


def evidence_goal_for(
    family: str,
    *,
    status_role: str,
    issue: str,
    status_transition_detected: bool,
) -> str:
    """Intended evidence goal for a planned query (Part B/D).

    Roles map to goals so a previous-status query is never planned as direct
    authority for a current-status issue, and legal terms stay background.
    """
    if family == "legal_term":
        return "background"
    if status_role == "previous_status" and status_transition_detected:
        # Previous-status authority is comparative once a transition exists.
        return "contextual"
    if status_role == "target_status" and issue == "status_change":
        # Target-route evidence is the direct goal of a status-change query.
        return "direct" if family in _PRIMARY_AUTHORITY_FAMILIES else "contextual"
    if family in _ADJUDICATIVE_FAMILIES:
        return "analogical"
    if status_role == "current_status" and family in _PRIMARY_AUTHORITY_FAMILIES:
        return "direct"
    if status_role in {"current_parent_status"} and family in _PRIMARY_AUTHORITY_FAMILIES:
        return "contextual"
    if family in {"administrative_rule", "legal_interpretation"}:
        return "contextual"
    return "contextual"


def _status_anchor_roles(facts: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Ordered (status_role, code) anchors for query generation.

    current first (the controlling status), then target (route), then previous
    (comparative). Parent codes are used only when no sub-status anchor exists.
    """
    anchors: List[Tuple[str, str]] = []

    def add(role: str, code: Optional[str]) -> None:
        if code and (role, code) not in anchors:
            anchors.append((role, code))

    add("current_status", facts.get("current_status"))
    add("target_status", facts.get("target_status"))
    add("previous_status", facts.get("previous_status"))
    if not anchors:
        add("current_parent_status", facts.get("current_parent_status"))
    return anchors


def plan_evidence_queries(
    immigration_facts: Dict[str, Any],
    legal_issue_types: Sequence[str],
    *,
    activity_types: Optional[Sequence[str]] = None,
    max_queries: int = 8,
) -> List[Dict[str, Any]]:
    """Deterministically map ontology dimensions to structured query objects.

    Returns a capped, de-duplicated list of query objects of the form::

        {
          "source_family": str,
          "priority": int,            # 1-based
          "query_ko": str,
          "query_en": str,
          "expected_status_codes": [str, ...],
          "expected_concepts": [str, ...],
          "evidence_goal": "direct|contextual|analogical|background",
          "reason": str,
        }

    No network calls. Korean official terms lead for Korean-source retrieval.
    Status roles (current / previous / target) are preserved per query.
    """
    facts = immigration_facts or {}
    issues = [i for i in (legal_issue_types or []) if i] or ["legal_general"]
    transition = bool(facts.get("status_transition_detected"))
    cap = max(1, min(int(max_queries or 8), 12))

    families = route_source_families(issues)
    if not families:
        families = list(FALLBACK_WHEN_EMPTY)

    anchors = _status_anchor_roles(facts)
    status_fam = status_family(
        facts.get("current_parent_status") or facts.get("current_status")
    )

    # Primary issue per family: the first routed issue that lists this family.
    def issue_for_family(family: str) -> str:
        for issue in issues:
            if family in source_families_for_issue(issue):
                return issue
        return issues[0]

    queries: List[Dict[str, Any]] = []
    seen_keys: set = set()
    seen_ko: set = set()

    def emit(family: str, role: str, code: Optional[str], issue: str) -> None:
        if len(queries) >= cap:
            return
        fam_ko = SOURCE_FAMILY_TERMS_KO.get(family, "출입국 체류자격")
        fam_en = SOURCE_FAMILY_TERMS_EN.get(family, "sojourn status")
        concept_ko = ISSUE_CONCEPT_KO.get(issue, "체류자격")
        concept_en = ISSUE_CONCEPT_EN.get(issue, "sojourn status")
        proc_ko = ISSUE_PROCEDURE_TERM_KO.get(issue, "")
        status_term_ko = STATUS_FAMILY_TERMS_KO.get(status_fam, "체류자격")
        status_term_en = STATUS_FAMILY_TERMS_EN.get(status_fam, "sojourn status")
        key = (family, role, code or "", issue)
        if key in seen_keys:
            return
        parts_ko = [fam_ko, code or status_term_ko, concept_ko]
        if proc_ko:
            parts_ko.append(proc_ko)
        query_ko = " ".join(p for p in parts_ko if p).strip()[:240]
        if query_ko in seen_ko:
            seen_keys.add(key)
            return
        parts_en = [fam_en, code or status_term_en, concept_en]
        query_en = " ".join(p for p in parts_en if p).strip()[:240]
        expected_codes = [code] if code else []
        expected_concepts = [c for c in (concept_ko, issue) if c]
        goal = evidence_goal_for(
            family, status_role=role, issue=issue,
            status_transition_detected=transition,
        )
        reason = (
            f"Issue '{issue}' routes to '{family}' "
            f"({source_family_support_status(family)}); "
            f"anchored on {role}={code or status_term_en}; goal={goal}."
        )
        seen_keys.add(key)
        seen_ko.add(query_ko)
        queries.append({
            "source_family": family,
            "priority": len(queries) + 1,
            "query_ko": query_ko,
            "query_en": query_en,
            "status_role": role,
            "expected_status_codes": expected_codes,
            "expected_concepts": expected_concepts,
            "evidence_goal": goal,
            "reason": reason,
        })

    # Generate in family-priority order, anchoring each family on the most
    # relevant status role first (current, then target/previous as applicable).
    for family in families:
        if len(queries) >= cap:
            break
        issue = issue_for_family(family)
        if anchors:
            primary_role, primary_code = anchors[0]
            emit(family, primary_role, primary_code, issue)
        else:
            emit(family, "current_status", None, issue)

    # Second pass: add target-route and previous-status (comparative) anchors
    # for the strongest wired families, preserving status roles.
    for role, code in anchors[1:]:
        for family in families:
            if len(queries) >= cap:
                break
            if family in _PRIMARY_AUTHORITY_FAMILIES:
                issue = "status_change" if role == "target_status" and "status_change" in issues else issue_for_family(family)
                emit(family, role, code, issue)

    return queries[:cap]


# ---------------------------------------------------------------------------
# Ontology snapshot — a single structured view of a question (for smoke/debug)
# ---------------------------------------------------------------------------
def build_evidence_ontology(
    question: str,
    *,
    visa_code: Optional[str] = None,
    max_queries: int = 8,
) -> Dict[str, Any]:
    """Full deterministic ontology snapshot for a question.

    Imports the classifiers lazily to avoid an import cycle with
    legal_analysis. Returns the detected dimensions, the planned source
    families (with wired/unwired support state), the structured query plan, and
    the per-query evidence goals.
    """
    from .legal_analysis import (  # lazy import (cycle-safe)
        classify_activity_types,
        classify_legal_issue_types,
        extract_immigration_facts,
    )

    facts = extract_immigration_facts(question, visa_code=visa_code)
    activities = classify_activity_types(question)
    issues = classify_legal_issue_types(question, facts)
    families = route_source_families(issues) or list(FALLBACK_WHEN_EMPTY)
    query_plan = plan_evidence_queries(
        facts, issues, activity_types=activities, max_queries=max_queries,
    )
    return {
        "ontology_version": ONTOLOGY_VERSION,
        "immigration_facts": facts,
        "status_family": status_family(
            facts.get("current_parent_status") or facts.get("current_status")
        ),
        "activity_types": activities,
        "legal_issue_types": issues,
        "source_families_planned": families,
        "source_family_support": {f: source_family_support_status(f) for f in families},
        "wired_families_planned": [f for f in families if is_source_family_wired(f)],
        "unwired_families_planned": [f for f in families if not is_source_family_wired(f)],
        "evidence_query_plan": query_plan,
        "evidence_goal_by_query": [q["evidence_goal"] for q in query_plan],
    }


# ---------------------------------------------------------------------------
# Part F — capture batch generated from the same ontology/planner
# ---------------------------------------------------------------------------
# Representative (non-personal) probes covering issue types + source families.
# Each probe is run through the real planner so the capture batch is generated
# from the ontology, not a disconnected hardcoded list.
IMMIGRATION_CORE_PROBES: Tuple[Dict[str, Any], ...] = (
    {"id": "registration_reporting", "question": "외국인등록은 언제 해야 하나요?", "visa_code": "H-1"},
    {"id": "activity_outside_status", "question": "체류자격외활동 허가 없이 다른 일을 할 수 있나요?", "visa_code": "D-10"},
    {"id": "workplace_change_addition", "question": "근무처 변경 또는 추가 신고는 어떻게 하나요?", "visa_code": "E-7"},
    {"id": "status_change", "question": "체류자격을 F-2-99로 변경할 수 있나요?", "visa_code": "H-1"},
    {"id": "study_on_non_study_status", "question": "유학 체류자격이 아닌데 대학교 수업을 들을 수 있나요?", "visa_code": "G-1-5"},
    {"id": "paid_work_short_term", "question": "단기방문으로 유급 근무를 할 수 있나요?", "visa_code": "C-3"},
    {"id": "document_checklist", "question": "체류기간 연장 구비서류는 무엇인가요?", "visa_code": "D-2"},
    {"id": "legal_term_lookup", "question": "체류자격외활동의 법령상 정의는 무엇인가요?"},
)


def build_immigration_core_batch(max_queries: int = 6) -> List[Dict[str, Any]]:
    """Build the 'immigration-core' capture batch from the ontology planner.

    Returns one entry per (probe, planned source family) so the capture helper
    can exercise representative families and issue types. No network, no secrets.
    """
    batch: List[Dict[str, Any]] = []
    for probe in IMMIGRATION_CORE_PROBES:
        snapshot = build_evidence_ontology(
            probe["question"], visa_code=probe.get("visa_code"),
            max_queries=max_queries,
        )
        seen_families: set = set()
        for query in snapshot["evidence_query_plan"]:
            family = query["source_family"]
            if family in seen_families:
                continue
            seen_families.add(family)
            batch.append({
                "probe_id": probe["id"],
                "source_family": family,
                "support_status": source_family_support_status(family),
                "query_ko": query["query_ko"],
                "query_en": query["query_en"],
                "evidence_goal": query["evidence_goal"],
                "legal_issue_types": snapshot["legal_issue_types"],
                "expected_status_codes": query["expected_status_codes"],
            })
    return batch
