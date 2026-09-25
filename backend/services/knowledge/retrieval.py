"""Canonical knowledge retrieval: ask by semantics, get evidence with provenance.

    retrieve_knowledge(status="D-2", procedure="extension",
                       intent="required_documents", as_of="2026-09-25")

returns published facts, their conditions, citations, conflicts, missing
knowledge and source currency — never a raw JSON file, never a vector hit.

Sub-code semantics (unchanged from the legacy grounding selector):
  1. a sub-code request prefers the variant scoped to exactly that sub-code;
  2. otherwise a parent-level variant ONLY if it explicitly lists the
     sub-code in ``subcodes_covered`` — a parent list is never silently
     applied to an uncovered sub-code (E-7-4 never inherits E-7);
  3. a parent request uses parent-level variants only.

Temporal semantics:
  * current (``as_of`` omitted or today): PUBLISHED facts whose effective
    window contains today (an unknown effective date counts as in force);
  * historical (``as_of`` in the past): PUBLISHED or SUPERSEDED facts whose
    effective window contains the date, and — when effective dates are
    unknown — whose knowledge window (published_at .. superseded_at) does.
    ``temporal_basis`` reports which basis was used.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .conflicts import open_conflicts_for_slots, version_sort_key
from .models import INTENT_PROPERTY, FactProperty
from .repository import KnowledgeRepository
from .store import today, utc_now

_REVIEWED = ("PUBLISHED", "VERIFIED", "HUMAN_REVIEWED")


@dataclass
class RetrievalResult:
    status_code: Optional[str]
    subcode: Optional[str]
    procedure: Optional[str]
    intent: Optional[str]
    as_of: str
    temporal_basis: str = "current"
    variant: Optional[Dict[str, Any]] = None
    facts: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)          # human-backed on every side
    pending_conflicts: int = 0                                              # involve unreviewed proposals
    missing: List[str] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    freshness: str = "unknown"
    status_known: bool = False
    procedure_known: bool = False
    subcode_uncovered: bool = False
    error: str = ""

    @property
    def document_facts(self) -> List[Dict[str, Any]]:
        return [f for f in self.facts if f["property"] == FactProperty.REQUIRED_DOCUMENT.value]

    @property
    def note_facts(self) -> List[Dict[str, Any]]:
        return [f for f in self.facts if f["property"] == FactProperty.PROCEDURAL_NOTE.value]

    @property
    def fact_ids(self) -> List[str]:
        return [f["fact_id"] for f in self.facts]

    @property
    def has_conditions(self) -> bool:
        return any(f["condition_kind"] != "always" for f in self.document_facts)

    def internal(self) -> Dict[str, Any]:
        """Operator/diagnostic view (includes ids and provenance)."""
        return {
            "status_code": self.status_code, "subcode": self.subcode, "procedure": self.procedure,
            "intent": self.intent, "as_of": self.as_of, "temporal_basis": self.temporal_basis,
            "variant_key": (self.variant or {}).get("variant_key"),
            "fact_ids": self.fact_ids, "conflicts": [c["conflict_id"] for c in self.conflicts],
            "pending_conflicts": self.pending_conflicts, "missing": self.missing,
            "freshness": self.freshness, "sources": self.sources, "error": self.error,
        }

    def public(self) -> Dict[str, Any]:
        """Public projection: what applies, which source — no ids, no states."""
        return {
            "status_code": self.status_code, "subcode": self.subcode, "procedure": self.procedure,
            "facts": [{"property": f["property"], "text": f["value_text"],
                       "requirement_level": (f.get("value_json") or {}).get("requirement_level"),
                       "condition": f.get("condition_text") or ""} for f in self.facts],
            "sources": [{"title": s["title"], "edition": s["edition"], "issuing_body": s["issuing_body"],
                         "pages": s["pages"]} for s in self.sources],
        }


class RetrievalService:
    def __init__(self, repo: KnowledgeRepository, cache_size: int = 256):
        self.repo = repo
        self._cache: "OrderedDict[Tuple, RetrievalResult]" = OrderedDict()
        self._cache_size = cache_size
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def answerable_variants(self, status_code: str, procedure: str,
                            states: Tuple[str, ...] = ("PUBLISHED",)) -> List[Dict[str, Any]]:
        """Variants that hold at least one fact in ``states``.

        A variant created by an unreviewed import (proposals only) is not
        knowledge: it must never be selected, or a pending proposal would
        change what Waymaker says.
        """
        marks = ",".join("?" * len(states))
        return [v for v in self.repo.variants_for(status_code, procedure)
                if self.repo.store.one(
                    f"SELECT 1 FROM knowledge_facts WHERE variant_id = ? AND lifecycle_state IN ({marks}) LIMIT 1",
                    (v["variant_id"], *states))]

    def select_variant(self, status_code: str, subcode: Optional[str], procedure: str,
                       states: Tuple[str, ...] = ("PUBLISHED",)) -> Tuple[Optional[Dict[str, Any]], bool]:
        """Returns (variant, subcode_uncovered)."""
        variants = self.answerable_variants(status_code, procedure, states)
        if subcode:
            exact = [v for v in variants if v.get("subcode") == subcode]
            if exact:
                return _prefer_general(exact), False
            covering = [v for v in variants if v.get("subcode") is None
                        and subcode in (v.get("subcodes_covered") or [])]
            if covering:
                return _prefer_general(covering), False
            return None, bool(variants)
        general = [v for v in variants if v.get("subcode") is None]
        return (_prefer_general(general) if general else None), False

    def retrieve(self, *, status_code: Optional[str], procedure: Optional[str], subcode: Optional[str] = None,
                 intent: Optional[str] = None, as_of: Optional[str] = None) -> RetrievalResult:
        as_of = as_of or today()
        key = (status_code, subcode, procedure, intent, as_of, self.repo.store.revision())
        with self._lock:
            hit = self._cache.get(key)
            if hit is not None:
                self._cache.move_to_end(key)
                return hit
        result = self._retrieve(status_code=status_code, procedure=procedure, subcode=subcode,
                                intent=intent, as_of=as_of)
        with self._lock:
            self._cache[key] = result
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        return result

    def _retrieve(self, *, status_code, procedure, subcode, intent, as_of) -> RetrievalResult:
        result = RetrievalResult(status_code=status_code, subcode=subcode, procedure=procedure,
                                 intent=intent, as_of=as_of)
        if not status_code:
            return result
        known = set(self.repo.known_status_codes())
        result.status_known = status_code in known
        if not procedure:
            return result
        as_of_ts_probe = as_of if "T" in as_of else f"{as_of}T23:59:59Z"
        answer_states = ("PUBLISHED", "SUPERSEDED") if as_of_ts_probe < utc_now() else ("PUBLISHED",)
        variant, uncovered = self.select_variant(status_code, subcode, procedure, answer_states)
        result.subcode_uncovered = uncovered
        result.procedure_known = bool(self.answerable_variants(status_code, procedure, answer_states))
        if variant is None:
            if intent and intent in INTENT_PROPERTY:
                result.missing.append(INTENT_PROPERTY[intent])
            return result
        result.variant = variant
        # ``as_of`` may be a date (end of that day) or a full UTC timestamp.
        as_of_ts = as_of if "T" in as_of else f"{as_of}T23:59:59Z"
        as_of_date = as_of_ts[:10]
        historical = as_of_ts < utc_now()
        states = ("PUBLISHED", "SUPERSEDED") if historical else ("PUBLISHED",)
        rows = self.repo.facts_where(
            "f.variant_id = ? AND f.lifecycle_state IN (%s)" % ",".join("?" * len(states)),
            (variant["variant_id"], *states), order="f.property, f.sort_order, f.created_at")
        facts: List[Dict[str, Any]] = []
        basis = "current"
        for fact in rows:
            eff_from, eff_to = fact.get("effective_from"), fact.get("effective_to")
            if eff_from and eff_from > as_of_date:
                continue
            if eff_to and eff_to <= as_of_date:
                continue
            if historical:
                if eff_from or eff_to:
                    basis = "effective_dates" if basis == "current" else basis
                else:
                    # Effective dates unknown (never invented): answer from the
                    # knowledge window — what Waymaker held as published then.
                    basis = "knowledge_window"
                    if (fact.get("published_at") or "") > as_of_ts:
                        continue
                    if fact.get("superseded_at") and fact["superseded_at"] <= as_of_ts:
                        continue
            facts.append(fact)
        # One fact per slot; if a window edge admits two, keep the later publication.
        by_slot: Dict[str, Dict[str, Any]] = {}
        for fact in facts:
            prev = by_slot.get(fact["slot_key"])
            if prev is None or (fact.get("published_at") or "") > (prev.get("published_at") or ""):
                by_slot[fact["slot_key"]] = fact
        result.facts = sorted(by_slot.values(), key=lambda f: (f["property"], f["sort_order"], f["created_at"]))
        result.temporal_basis = basis if historical else "current"
        if intent and intent in INTENT_PROPERTY and not any(
                f["property"] == INTENT_PROPERTY[intent] for f in result.facts):
            result.missing.append(INTENT_PROPERTY[intent])
        slots = list(by_slot)
        conflicts = open_conflicts_for_slots(self.repo, slots)
        reviewed = []
        pending = 0
        for c in conflicts:
            pair = self.repo.store.all(
                "SELECT lifecycle_state, origin FROM knowledge_facts WHERE fact_id IN (?, ?)",
                (c["fact_a_id"], c["fact_b_id"]))
            # A conflict reaches public coverage only when every side carries a
            # human judgement (reviewed, or an operator-entered proposal).
            # Unreviewed AI / parser proposals are operator-queue signals only,
            # so junk extraction can never degrade a verified answer.
            if all(r["lifecycle_state"] in _REVIEWED or r["origin"] == "operator_manual" for r in pair):
                reviewed.append(c)
            else:
                pending += 1
        result.conflicts = reviewed
        result.pending_conflicts = pending
        result.sources, result.freshness = self._sources(result.facts)
        return result

    def _sources(self, facts: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
        seen: Dict[str, Dict[str, Any]] = {}
        for fact in facts:
            for cit in fact.get("citations") or []:
                vid = cit["source_version_id"]
                entry = seen.setdefault(vid, {
                    "source_version_id": vid, "source_key": cit["source_key"], "title": cit["source_title"],
                    "edition": cit["version_label"], "edition_ref": cit["edition_ref"],
                    "issuing_body": cit["issuing_body"], "authority_type": cit["source_authority"],
                    "version_status": cit["version_status"], "refresh_state": cit["refresh_state"],
                    # INTERNAL provenance (never in ``public()``).
                    "artifact_ref": cit.get("artifact_ref") or "", "revision_date": cit.get("revision_date") or "",
                    "page_min": None, "page_max": None, "pages": "",
                })
                for p in (cit.get("page_start"), cit.get("page_end")):
                    if p:
                        entry["page_min"] = p if entry["page_min"] is None else min(entry["page_min"], p)
                        entry["page_max"] = p if entry["page_max"] is None else max(entry["page_max"], p)
        sources = sorted(seen.values(), key=lambda s: version_sort_key(s["edition"]), reverse=True)
        for s in sources:
            if s["page_min"]:
                s["pages"] = (str(s["page_min"]) if s["page_min"] == s["page_max"]
                              else f"{s['page_min']}-{s['page_max']}")
        freshness = "unknown"
        if sources:
            statuses = {s["version_status"] for s in sources}
            if "withdrawn" in statuses:
                freshness = "cited_edition_withdrawn"
            elif any(s["refresh_state"] == "refresh_due" for s in sources) or "superseded" in statuses:
                freshness = "newer_edition_available"
            else:
                freshness = "current"
        return sources, freshness

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()


def _prefer_general(variants: List[Dict[str, Any]]) -> Dict[str, Any]:
    for v in variants:
        if (v.get("scenario") or "general") == "general":
            return v
    return variants[0]
