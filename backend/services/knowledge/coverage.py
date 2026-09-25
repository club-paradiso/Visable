"""Coverage decision: what Waymaker is entitled to say, decided before generation.

Inputs are the deterministic understanding and the retrieval result — never
the model's confidence. Output is one :class:`CoverageState`, the answer path
it licenses, and (only for genuine KNOWLEDGE gaps) a gap reason.

The key distinction the engine protects:

    user fact gap   the question omitted something decisive (which status?)
                    -> ask for it; NOT a knowledge gap, nothing is queued
    knowledge gap   Waymaker lacks verified knowledge for a well-formed question
                    -> limited guidance + a deduplicated coverage-gap record

and the two failure states that must never merge (see
docs/ai/IMMIGRATION_INTELLIGENCE_ARCHITECTURE.md §3):

    RETRIEVAL_FAILED  we could not look  -> UNKNOWN, never "no such rule"
    no knowledge      we looked, found nothing verified -> NO_DIRECT_SOURCE
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .ingestion import status_universe
from .models import INTENT_PROPERTY, AmbiguityState, AnswerPath, CoverageState, GapReason, Intent
from .retrieval import RetrievalResult
from .understanding import QueryUnderstanding

C, P, G = CoverageState, AnswerPath, GapReason

VERIFIED_STATES = frozenset({C.DIRECT_VERIFIED.value, C.VERIFIED_WITH_CONDITIONS.value})


@dataclass
class CoverageDecision:
    state: str
    answer_path: str
    gap_reason: Optional[str] = None          # set ONLY for knowledge gaps
    clarify: List[str] = field(default_factory=list)   # decisive user facts to ask for
    reasons: List[str] = field(default_factory=list)   # machine-readable trace
    scope_subcodes: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)  # e.g. statuses that do have knowledge

    @property
    def verified(self) -> bool:
        return self.state in VERIFIED_STATES

    @property
    def is_knowledge_gap(self) -> bool:
        return self.gap_reason is not None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def decide(u: QueryUnderstanding, r: Optional[RetrievalResult], *, retrieval_failed: bool = False,
           statuses_with_knowledge: Optional[List[str]] = None) -> CoverageDecision:
    if retrieval_failed:
        return CoverageDecision(C.UNKNOWN.value, P.SAFE_FALLBACK.value, G.RETRIEVAL_FAILED.value,
                                reasons=["retrieval_failed"])
    if u.intent == Intent.CASE_RESEARCH.value:
        return CoverageDecision(C.OUT_OF_SCOPE.value, P.EXISTING_PIPELINE.value,
                                reasons=["case_research_is_contextual_not_knowledge"])

    # --- user fact gaps (never queued as knowledge gaps) -------------------
    if u.missing_decisive_facts:
        return CoverageDecision(
            C.NEEDS_CLARIFICATION.value, P.ASK_CLARIFICATION.value, None,
            clarify=list(u.missing_decisive_facts),
            reasons=[f"user_fact_missing:{m}" for m in u.missing_decisive_facts] + [f"ambiguity:{u.ambiguity}"],
            alternatives=sorted(statuses_with_knowledge or []),
        )

    fact_intent = u.intent in INTENT_PROPERTY or u.intent == Intent.REQUIRED_DOCUMENTS.value
    if not u.status_code:
        return CoverageDecision(C.OUT_OF_SCOPE.value, P.EXISTING_PIPELINE.value,
                                reasons=["no_status_general_question"])

    universe = status_universe()
    if universe and u.status_code not in universe:
        return CoverageDecision(C.UNKNOWN.value, P.LIMITED_GUIDANCE.value, G.UNKNOWN_STATUS.value,
                                reasons=["status_not_in_manual_universe"])
    if u.subcode and universe and u.subcode not in universe:
        return CoverageDecision(C.UNKNOWN.value, P.LIMITED_GUIDANCE.value, G.UNKNOWN_SUBCODE.value,
                                reasons=["subcode_not_in_manual_universe"])

    if not u.retrieval_procedure:
        if u.procedure and (fact_intent or u.risk_level == "high"):
            # A real procedure question the knowledge layer cannot answer directly
            # (e.g. divorce -> status change, overstay): limited guidance + gap.
            return CoverageDecision(C.NO_DIRECT_SOURCE.value, P.LIMITED_GUIDANCE.value,
                                    G.NO_VERIFIED_KNOWLEDGE.value,
                                    reasons=[f"task_not_directly_groundable:{u.task_type}"])
        return CoverageDecision(C.OUT_OF_SCOPE.value, P.EXISTING_PIPELINE.value,
                                reasons=["no_procedure"])

    if r is None or r.variant is None:
        if r is not None and r.subcode_uncovered:
            return CoverageDecision(C.NO_DIRECT_SOURCE.value, P.LIMITED_GUIDANCE.value, G.UNKNOWN_SUBCODE.value,
                                    reasons=["subcode_not_covered_by_parent_list"])
        return CoverageDecision(C.NO_DIRECT_SOURCE.value, P.LIMITED_GUIDANCE.value, G.NO_VERIFIED_KNOWLEDGE.value,
                                reasons=["no_published_variant"])

    if not r.facts:
        # Never claim verified coverage without verified facts in hand.
        return CoverageDecision(C.NO_DIRECT_SOURCE.value, P.LIMITED_GUIDANCE.value, G.NO_VERIFIED_KNOWLEDGE.value,
                                reasons=["no_facts_in_force"])
    if r.conflicts:
        return CoverageDecision(C.CONFLICTING_SOURCES.value, P.EXPLAIN_CONFLICT.value, G.SOURCE_CONFLICT.value,
                                reasons=[f"conflict:{c['conflict_id']}" for c in r.conflicts])
    if r.freshness == "cited_edition_withdrawn":
        return CoverageDecision(C.OUTDATED_SOURCE.value, P.LIMITED_GUIDANCE.value, G.SOURCE_OUTDATED.value,
                                reasons=["cited_edition_withdrawn"])

    scope = list((r.variant or {}).get("subcodes_covered") or []) if not u.subcode else []
    reasons = [f"freshness:{r.freshness}"]
    if u.intent == Intent.REQUIRED_DOCUMENTS.value:
        if not r.document_facts:
            return CoverageDecision(C.NO_DIRECT_SOURCE.value, P.LIMITED_GUIDANCE.value,
                                    G.NO_VERIFIED_KNOWLEDGE.value, reasons=reasons + ["no_document_facts"])
        if r.has_conditions or scope:
            if scope:
                reasons.append("scope_limited_to_subcodes")
            if r.has_conditions:
                reasons.append("conditional_documents_present")
            return CoverageDecision(C.VERIFIED_WITH_CONDITIONS.value, P.DETERMINISTIC_WITH_CONDITIONS.value,
                                    reasons=reasons, scope_subcodes=scope)
        return CoverageDecision(C.DIRECT_VERIFIED.value, P.DETERMINISTIC_STRUCTURED.value, reasons=reasons)

    if u.intent in INTENT_PROPERTY:
        # Asked for a property (fee, deadline, ...) the variant has no fact for.
        missing_prop = INTENT_PROPERTY[u.intent]
        if missing_prop in r.missing:
            return CoverageDecision(C.PARTIAL_VERIFIED.value, P.BOUNDED_SYNTHESIS.value,
                                    G.NO_VERIFIED_KNOWLEDGE.value,
                                    reasons=reasons + [f"property_missing:{missing_prop}"], scope_subcodes=scope)
        return CoverageDecision(C.DIRECT_VERIFIED.value, P.DETERMINISTIC_STRUCTURED.value,
                                reasons=reasons, scope_subcodes=scope)

    # Procedural question with verified facts in hand: verified facts plus a
    # clearly bounded explanation.
    return CoverageDecision(C.PARTIAL_VERIFIED.value, P.BOUNDED_SYNTHESIS.value,
                            reasons=reasons + ["procedural_explanation"], scope_subcodes=scope)


def gap_dedupe_key(u: QueryUnderstanding, reason: str) -> str:
    return "|".join([u.status_code or "-", u.subcode or "-", u.procedure or "-", u.intent or "-", reason])


__all__ = ["CoverageDecision", "decide", "gap_dedupe_key", "VERIFIED_STATES", "AmbiguityState"]
