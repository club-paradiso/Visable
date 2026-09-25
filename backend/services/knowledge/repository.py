"""Knowledge repository: the only module that writes knowledge rows.

Every mutation goes through a transaction and leaves an audit record. Callers
(ingestion, review, API) never write SQL of their own.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .lifecycle import assert_transition, reviewer_kind_for
from .models import (
    ALL_PROCEDURES,
    ActorKind,
    FactProposal,
    KnowledgeError,
    LifecycleState,
    PipelineError,
    SourceVersionStatus,
    normalize_item_key,
    procedure_family,
    slot_key,
    variant_key,
)
from .store import KnowledgeStore, new_id, row_dict, stable_hash, today, utc_now

FACT_JSON_FIELDS = ("value_json", "display_translations", "extraction_warnings")


class KnowledgeRepository:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    # =========================================================================
    # Sources and versions
    # =========================================================================
    def upsert_source(
        self,
        *,
        source_key: str,
        title_ko: str,
        authority_type: str,
        procedure_family: str,
        title_en: str = "",
        issuing_body: str = "",
        official_url: str = "",
        registry_ref: str = "",
        actor: str = "system",
        actor_kind: str = ActorKind.SYSTEM.value,
    ) -> Tuple[str, bool]:
        existing = self.store.one("SELECT * FROM sources WHERE source_key = ?", (source_key,))
        if existing:
            return existing["source_id"], False
        source_id = new_id("src")
        now = utc_now()
        with self.store.transaction():
            self.store.execute(
                "INSERT INTO sources(source_id, source_key, title_ko, title_en, issuing_body, authority_type,"
                " procedure_family, official_url, registry_ref, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (source_id, source_key, title_ko, title_en, issuing_body, authority_type,
                 procedure_family, official_url, registry_ref, now, now),
            )
            self.store.audit(actor=actor, actor_kind=actor_kind, entity_type="source",
                             entity_id=source_id, action="register",
                             after={"source_key": source_key, "authority_type": authority_type})
        return source_id, True

    def upsert_source_version(
        self,
        *,
        source_id: str,
        edition_ref: str,
        version_label: str,
        status: str,
        content_review_state: str = "needs_review",
        revision_date: Optional[str] = None,
        published_date: Optional[str] = None,
        effective_from: Optional[str] = None,
        content_sha256: Optional[str] = None,
        artifact_ref: str = "",
        page_count: Optional[int] = None,
        supersedes_version_id: Optional[str] = None,
        official_url: str = "",
        notes: str = "",
        actor: str = "system",
        actor_kind: str = ActorKind.SYSTEM.value,
    ) -> Tuple[str, bool]:
        """Idempotent on (source, edition_ref). Status/review drift is updated + audited."""
        SourceVersionStatus(status)  # validate
        existing = self.store.one(
            "SELECT * FROM source_versions WHERE source_id = ? AND edition_ref = ?", (source_id, edition_ref)
        )
        if existing:
            changes = {}
            if existing["status"] != status:
                changes["status"] = status
            if existing["content_review_state"] != content_review_state:
                changes["content_review_state"] = content_review_state
            if supersedes_version_id and existing["supersedes_version_id"] != supersedes_version_id:
                changes["supersedes_version_id"] = supersedes_version_id
            if changes:
                with self.store.transaction():
                    sets = ", ".join(f"{k} = ?" for k in changes)
                    self.store.execute(
                        f"UPDATE source_versions SET {sets} WHERE source_version_id = ?",
                        (*changes.values(), existing["source_version_id"]),
                    )
                    self.store.audit(actor=actor, actor_kind=actor_kind, entity_type="source_version",
                                     entity_id=existing["source_version_id"], action="update_status",
                                     before={k: existing[k] for k in changes}, after=changes)
            return existing["source_version_id"], False
        version_id = new_id("srv")
        with self.store.transaction():
            self.store.execute(
                "INSERT INTO source_versions(source_version_id, source_id, version_label, edition_ref,"
                " revision_date, published_date, effective_from, imported_at, content_sha256, artifact_ref,"
                " page_count, status, content_review_state, supersedes_version_id, official_url, notes)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (version_id, source_id, version_label, edition_ref, revision_date, published_date,
                 effective_from, utc_now(), content_sha256, artifact_ref, page_count, status,
                 content_review_state, supersedes_version_id, official_url, notes),
            )
            self.store.audit(actor=actor, actor_kind=actor_kind, entity_type="source_version",
                             entity_id=version_id, action="register",
                             after={"edition_ref": edition_ref, "version_label": version_label, "status": status})
        return version_id, True

    def add_section(self, *, source_version_id: str, section_key: str, title: str,
                    page_start: Optional[int], page_end: Optional[int]) -> str:
        row = self.store.one(
            "SELECT section_id FROM source_sections WHERE source_version_id = ? AND section_key = ?",
            (source_version_id, section_key),
        )
        if row:
            return row["section_id"]
        section_id = new_id("sec")
        self.store.execute(
            "INSERT INTO source_sections(section_id, source_version_id, section_key, title, page_start, page_end)"
            " VALUES (?,?,?,?,?,?)",
            (section_id, source_version_id, section_key, title, page_start, page_end),
        )
        return section_id

    def set_source_refresh_state(self, source_id: str, state: str, *, actor: str, actor_kind: str,
                                 reason: str = "") -> None:
        row = self.store.one("SELECT refresh_state FROM sources WHERE source_id = ?", (source_id,))
        if not row:
            raise KnowledgeError(PipelineError.NOT_FOUND, f"source {source_id} not found")
        if row["refresh_state"] == state:
            return
        with self.store.transaction():
            self.store.execute("UPDATE sources SET refresh_state = ?, updated_at = ? WHERE source_id = ?",
                               (state, utc_now(), source_id))
            self.store.audit(actor=actor, actor_kind=actor_kind, entity_type="source", entity_id=source_id,
                             action="refresh_state", reason=reason,
                             before={"refresh_state": row["refresh_state"]}, after={"refresh_state": state})

    def get_source_version(self, source_version_id: str) -> Dict[str, Any]:
        row = self.store.one(
            "SELECT v.*, s.source_key, s.title_ko, s.title_en, s.issuing_body, s.authority_type,"
            " s.procedure_family, s.refresh_state FROM source_versions v JOIN sources s USING(source_id)"
            " WHERE v.source_version_id = ?",
            (source_version_id,),
        )
        return row_dict(row)

    def find_source_version(self, source_key: str, edition_ref: str) -> Dict[str, Any]:
        row = self.store.one(
            "SELECT v.source_version_id FROM source_versions v JOIN sources s USING(source_id)"
            " WHERE s.source_key = ? AND v.edition_ref = ?",
            (source_key, edition_ref),
        )
        return self.get_source_version(row["source_version_id"]) if row else {}

    def list_sources(self) -> List[Dict[str, Any]]:
        sources = [row_dict(r) for r in self.store.all("SELECT * FROM sources ORDER BY source_key")]
        for src in sources:
            src["versions"] = [
                row_dict(v) for v in self.store.all(
                    "SELECT v.*, (SELECT COUNT(*) FROM fact_citations c JOIN knowledge_facts f USING(fact_id)"
                    "   WHERE c.source_version_id = v.source_version_id AND f.lifecycle_state = 'PUBLISHED')"
                    "   AS published_fact_count,"
                    " (SELECT COUNT(*) FROM fact_citations c JOIN knowledge_facts f USING(fact_id)"
                    "   WHERE c.source_version_id = v.source_version_id AND f.lifecycle_state IN"
                    "   ('DRAFT','AI_EXTRACTED','HUMAN_REVIEW_REQUIRED','HUMAN_REVIEWED','VERIFIED'))"
                    "   AS pending_fact_count"
                    " FROM source_versions v WHERE v.source_id = ? ORDER BY v.version_label DESC, v.edition_ref",
                    (src["source_id"],),
                )
            ]
        return sources

    def sections_for(self, source_version_id: str) -> List[Dict[str, Any]]:
        return [row_dict(r) for r in self.store.all(
            "SELECT * FROM source_sections WHERE source_version_id = ? ORDER BY page_start", (source_version_id,))]

    # =========================================================================
    # Procedure variants
    # =========================================================================
    def ensure_variant(
        self,
        *,
        status_code: str,
        subcode: Optional[str],
        procedure: str,
        scenario: str = "general",
        subcodes_covered: Sequence[str] = (),
        section_title: str = "",
        legacy_ref: str = "",
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        family = procedure_family(procedure)
        if family is None:
            raise KnowledgeError(PipelineError.UNKNOWN_PROCEDURE, f"unknown procedure {procedure!r}")
        key = variant_key(status_code, subcode, procedure, scenario)
        row = self.store.one("SELECT * FROM procedure_variants WHERE variant_key = ?", (key,))
        if row:
            return self._variant(row)
        variant_id = new_id("pv")
        self.store.execute(
            "INSERT INTO procedure_variants(variant_id, variant_key, status_code, subcode, subcodes_covered,"
            " procedure, procedure_label_ko, procedure_family, scenario, section_title, legacy_ref, attributes,"
            " created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (variant_id, key, status_code, subcode, json.dumps(sorted(set(subcodes_covered))), procedure,
             ALL_PROCEDURES.get(procedure, ""), family, scenario or "general", section_title, legacy_ref,
             json.dumps(attributes or {}, ensure_ascii=False, sort_keys=True), utc_now()),
        )
        return self._variant(self.store.one("SELECT * FROM procedure_variants WHERE variant_id = ?", (variant_id,)))

    @staticmethod
    def _variant(row) -> Dict[str, Any]:
        return row_dict(row, json_fields=("subcodes_covered", "attributes"))

    def get_variant(self, variant_id: str) -> Dict[str, Any]:
        return self._variant(self.store.one("SELECT * FROM procedure_variants WHERE variant_id = ?", (variant_id,)))

    def variants_for(self, status_code: str, procedure: str) -> List[Dict[str, Any]]:
        return [self._variant(r) for r in self.store.all(
            "SELECT * FROM procedure_variants WHERE status_code = ? AND procedure = ? ORDER BY variant_key",
            (status_code, procedure))]

    def known_status_codes(self) -> List[str]:
        return [r["status_code"] for r in self.store.all(
            "SELECT DISTINCT status_code FROM procedure_variants ORDER BY status_code")]

    # =========================================================================
    # Facts
    # =========================================================================
    @staticmethod
    def proposal_hash(proposal: FactProposal, variant_key_: str, item_key: str) -> str:
        loc = proposal.location
        return stable_hash(
            variant_key_, proposal.property.value, item_key, proposal.value_text,
            proposal.condition_kind.value, proposal.condition_text,
            proposal.requirement_level.value if proposal.requirement_level else None,
            proposal.effective_from, proposal.effective_to,
            loc.source_version_id, loc.page_start, loc.page_end, loc.locator,
        )

    def insert_proposal(
        self,
        proposal: FactProposal,
        *,
        created_by: str,
        created_by_kind: str,
        initial_state: LifecycleState,
        locator_verified: bool = False,
        verification_note: str = "",
        lineage_id: Optional[str] = None,
        version_no: int = 1,
        supersedes_fact_id: Optional[str] = None,
        variant_attributes: Optional[Dict[str, Any]] = None,
        legacy_ref: str = "",
        extra_value: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, bool]:
        """Insert a proposal + its citation. Idempotent on proposal content.

        Returns ``(fact_id, created)``. Re-importing the same proposal returns
        the existing fact id with ``created=False`` — no duplicate fact, no
        duplicate review task.
        """
        variant = self.ensure_variant(
            status_code=proposal.status_code, subcode=proposal.subcode, procedure=proposal.procedure,
            scenario=proposal.scenario, subcodes_covered=proposal.subcodes_covered,
            section_title=proposal.section_title, legacy_ref=legacy_ref, attributes=variant_attributes,
        )
        item_key = proposal.item_key or normalize_item_key(proposal.value_text)
        skey = slot_key(variant["variant_key"], proposal.property.value, item_key)
        phash = self.proposal_hash(proposal, variant["variant_key"], item_key)
        existing = self.store.one("SELECT fact_id FROM knowledge_facts WHERE proposal_hash = ?", (phash,))
        if existing:
            return existing["fact_id"], False
        fact_id = new_id("kf")
        value_json = {"label": proposal.value_text}
        if proposal.requirement_level:
            value_json["requirement_level"] = proposal.requirement_level.value
        value_json.update(extra_value or {})
        now = utc_now()
        loc = proposal.location
        with self.store.transaction():
            self.store.execute(
                "INSERT INTO knowledge_facts(fact_id, lineage_id, version_no, variant_id, property, item_key,"
                " slot_key, value_text, value_json, condition_kind, condition_text, display_translations,"
                " sort_order, authority_type, origin, extraction_confidence, extraction_warnings,"
                " lifecycle_state, effective_from, effective_to, supersedes_fact_id, created_by,"
                " created_by_kind, created_at, proposal_hash)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (fact_id, lineage_id or new_id("kl"), version_no, variant["variant_id"],
                 proposal.property.value, item_key, skey, proposal.value_text,
                 json.dumps(value_json, ensure_ascii=False, sort_keys=True), proposal.condition_kind.value,
                 proposal.condition_text,
                 json.dumps(proposal.display_translations, ensure_ascii=False, sort_keys=True),
                 proposal.sort_order, proposal.authority_type.value, proposal.origin.value,
                 proposal.extraction_confidence,
                 json.dumps(proposal.extraction_warnings, ensure_ascii=False),
                 initial_state.value, proposal.effective_from, proposal.effective_to, supersedes_fact_id,
                 created_by, created_by_kind, now, phash),
            )
            self.store.execute(
                "INSERT INTO fact_citations(citation_id, fact_id, source_version_id, section_title, page_start,"
                " page_end, locator, evidence_excerpt, locator_verified, verification_note, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (new_id("cit"), fact_id, loc.source_version_id, loc.section_title or proposal.section_title,
                 loc.page_start, loc.page_end, loc.locator, loc.evidence_excerpt, int(locator_verified),
                 verification_note, now),
            )
            self.store.audit(actor=created_by, actor_kind=created_by_kind, entity_type="fact", entity_id=fact_id,
                             action="propose", after={"slot_key": skey, "value_text": proposal.value_text,
                                                      "state": initial_state.value, "origin": proposal.origin.value})
        return fact_id, True

    def get_fact(self, fact_id: str) -> Dict[str, Any]:
        row = self.store.one(
            "SELECT f.*, v.variant_key, v.status_code, v.subcode, v.subcodes_covered, v.procedure,"
            " v.procedure_family, v.scenario, v.section_title AS variant_section"
            " FROM knowledge_facts f JOIN procedure_variants v USING(variant_id) WHERE f.fact_id = ?",
            (fact_id,),
        )
        if not row:
            raise KnowledgeError(PipelineError.NOT_FOUND, f"fact {fact_id} not found")
        fact = row_dict(row, json_fields=FACT_JSON_FIELDS + ("subcodes_covered",))
        fact["citations"] = self.citations_for(fact_id)
        return fact

    def citations_for(self, fact_id: str) -> List[Dict[str, Any]]:
        return [row_dict(r) for r in self.store.all(
            "SELECT c.*, v.version_label, v.edition_ref, v.status AS version_status, v.content_review_state,"
            " v.artifact_ref, v.revision_date,"
            " v.official_url AS version_url, s.source_key, s.title_ko AS source_title, s.issuing_body,"
            " s.authority_type AS source_authority, s.procedure_family AS source_family, s.refresh_state"
            " FROM fact_citations c JOIN source_versions v USING(source_version_id)"
            " JOIN sources s USING(source_id) WHERE c.fact_id = ? ORDER BY c.page_start",
            (fact_id,))]

    def facts_where(self, where: str = "1=1", params: Sequence[Any] = (), *, order: str = "",
                    limit: int = 500, with_citations: bool = True) -> List[Dict[str, Any]]:
        rows = self.store.all(
            "SELECT f.*, v.variant_key, v.status_code, v.subcode, v.subcodes_covered, v.procedure,"
            " v.procedure_family, v.scenario, v.section_title AS variant_section"
            f" FROM knowledge_facts f JOIN procedure_variants v USING(variant_id) WHERE {where}"
            f" ORDER BY {order or 'v.variant_key, f.property, f.sort_order, f.created_at'} LIMIT ?",
            (*params, int(limit)),
        )
        facts = [row_dict(r, json_fields=FACT_JSON_FIELDS + ("subcodes_covered",)) for r in rows]
        if with_citations:
            for fact in facts:
                fact["citations"] = self.citations_for(fact["fact_id"])
        return facts

    def published_for_slot(self, slot: str) -> List[Dict[str, Any]]:
        return self.facts_where("f.slot_key = ? AND f.lifecycle_state = 'PUBLISHED'", (slot,))

    # -------------------------------------------------------------------------
    def transition(
        self,
        fact_id: str,
        target: LifecycleState,
        *,
        actor: str,
        actor_kind: str,
        reason: str = "",
        at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Move one fact along the lifecycle (validated twice: here and in SQL).

        Must be called inside the caller's transaction when it is one step of a
        larger unit (e.g. publish + supersede).
        """
        fact = self.get_fact(fact_id)
        current = fact["lifecycle_state"]
        assert_transition(current, target.value, actor_kind)
        if actor_kind == ActorKind.LEGACY_IMPORT.value and fact["origin"] != "legacy_repository_verified":
            # The pre-platform verification record can only vouch for the
            # repository content it describes — never for new extractions.
            raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN,
                                 "legacy import may only review legacy-verified repository facts",
                                 detail={"fact_id": fact_id, "origin": fact["origin"]})
        now = at or utc_now()
        sets: Dict[str, Any] = {"lifecycle_state": target.value}
        if target == LifecycleState.HUMAN_REVIEWED:
            sets.update(reviewed_by=actor, reviewed_at=now, reviewer_kind=reviewer_kind_for(actor_kind))
        elif target == LifecycleState.VERIFIED:
            if actor_kind == ActorKind.HUMAN_OPERATOR.value and fact.get("reviewer_kind") != "human_operator":
                sets["reviewer_kind"] = "human_operator"
            sets.update(verified_by=actor, verified_at=now)
        elif target == LifecycleState.PUBLISHED:
            sets["published_at"] = now
        elif target == LifecycleState.SUPERSEDED:
            sets["superseded_at"] = now
        elif target == LifecycleState.HUMAN_REVIEW_REQUIRED and current in ("HUMAN_REVIEWED", "VERIFIED"):
            # Sent back: the earlier review no longer stands.
            sets.update(reviewed_by=None, reviewed_at=None, reviewer_kind=None, verified_by=None, verified_at=None)
        with self.store.transaction():
            cols = ", ".join(f"{k} = ?" for k in sets)
            self.store.execute(f"UPDATE knowledge_facts SET {cols} WHERE fact_id = ?", (*sets.values(), fact_id))
            self.store.audit(actor=actor, actor_kind=actor_kind, entity_type="fact", entity_id=fact_id,
                             action=f"transition:{target.value}", reason=reason,
                             before={"lifecycle_state": current}, after={"lifecycle_state": target.value})
        return self.get_fact(fact_id)

    def set_fact_links(self, fact_id: str, **fields: Any) -> None:
        allowed = {"superseded_by_fact_id", "effective_to", "supersedes_fact_id"}
        bad = set(fields) - allowed
        if bad:
            raise ValueError(f"not link fields: {bad}")
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.store.execute(f"UPDATE knowledge_facts SET {cols} WHERE fact_id = ?", (*fields.values(), fact_id))

    # =========================================================================
    # Aggregates for the operator overview
    # =========================================================================
    def state_counts(self) -> Dict[str, int]:
        return {r["lifecycle_state"]: r["n"] for r in self.store.all(
            "SELECT lifecycle_state, COUNT(*) AS n FROM knowledge_facts GROUP BY lifecycle_state")}

    def audit_trail(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        return [row_dict(r, json_fields=("before_json", "after_json")) for r in self.store.all(
            "SELECT * FROM audit_log WHERE entity_type = ? AND entity_id = ? ORDER BY at, rowid",
            (entity_type, entity_id))]

    def recent_audit(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [row_dict(r, json_fields=("before_json", "after_json")) for r in self.store.all(
            "SELECT * FROM audit_log ORDER BY at DESC, rowid DESC LIMIT ?", (int(limit),))]


def as_of_ok(value: Optional[str]) -> str:
    return value or today()


def ids(rows: Iterable[Dict[str, Any]], key: str = "fact_id") -> List[str]:
    return [r[key] for r in rows]
