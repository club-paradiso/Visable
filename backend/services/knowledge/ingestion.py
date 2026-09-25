"""Ingestion contract: proposals in, validated plan out, review queue on apply.

Pipeline (docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md §Ingestion):

    source registered -> artifact referenced -> extraction (adapter)
      -> normalization (FactProposal) -> validation -> duplicate / conflict /
      update classification -> review queue -> human approval -> publication

Nothing here publishes. ``apply`` inserts proposals and opens review tasks;
publication is a separate, human action in ``review.ReviewService``. The one
exception is the legacy seed (``adapters.seed_legacy``), which publishes
repository content that the repository itself records as human-verified, under
its own reviewer kind.

Modes (``--dry-run`` / ``--validate`` / ``--apply``):
    dry_run   validate + classify every proposal, write nothing
    validate  validation only, write nothing
    apply     insert valid proposals, open review tasks, detect conflicts
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from pydantic import ValidationError

from . import conflicts as conflict_mod
from .models import (
    ActorKind,
    FactOrigin,
    FactProposal,
    KnowledgeError,
    LifecycleState,
    PipelineError,
    normalize_item_key,
    procedure_family,
    slot_key,
    variant_key,
)
from .repository import KnowledgeRepository
from .review import ReviewService
from .store import utc_now

logger = logging.getLogger("paradiso.knowledge")

REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS_UNIVERSE_PATH = REPO_ROOT / "data" / "status-guidance-202609.json"

_ORIGIN_INITIAL_STATE = {
    FactOrigin.AI_EXTRACTION: LifecycleState.AI_EXTRACTED,
    FactOrigin.PARSER_EXTRACTION: LifecycleState.HUMAN_REVIEW_REQUIRED,
    FactOrigin.OPERATOR_MANUAL: LifecycleState.HUMAN_REVIEW_REQUIRED,
    FactOrigin.LEGACY_REPOSITORY_VERIFIED: LifecycleState.HUMAN_REVIEW_REQUIRED,
}
_ORIGIN_ACTOR_KIND = {
    FactOrigin.AI_EXTRACTION: ActorKind.AI_EXTRACTOR.value,
    FactOrigin.PARSER_EXTRACTION: ActorKind.PARSER.value,
    FactOrigin.OPERATOR_MANUAL: ActorKind.HUMAN_OPERATOR.value,
    FactOrigin.LEGACY_REPOSITORY_VERIFIED: ActorKind.LEGACY_IMPORT.value,
}


@lru_cache(maxsize=1)
def status_universe() -> frozenset:
    """Every status / sub-code the repository's manual coverage knows about."""
    try:
        data = json.loads(STATUS_UNIVERSE_PATH.read_text(encoding="utf-8"))
        return frozenset(data.get("codes") or {})
    except (OSError, ValueError):
        return frozenset()


@dataclass
class PlanItem:
    index: int
    action: str                      # add | update | reconfirm | duplicate | conflict | invalid
    slot_key: str = ""
    value_text: str = ""
    errors: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    relates_to: List[str] = field(default_factory=list)
    fact_id: Optional[str] = None
    task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v not in (None, [], "")}


@dataclass
class IngestionReport:
    adapter: str
    mode: str
    items: List[PlanItem] = field(default_factory=list)
    started_at: str = field(default_factory=utc_now)

    @property
    def summary(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for item in self.items:
            out[item.action] = out.get(item.action, 0) + 1
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {"adapter": self.adapter, "mode": self.mode, "started_at": self.started_at,
                "summary": self.summary, "items": [i.to_dict() for i in self.items]}


class IngestionService:
    def __init__(self, repo: KnowledgeRepository, review: Optional[ReviewService] = None):
        self.repo = repo
        self.review = review or ReviewService(repo)

    # ------------------------------------------------------------------
    def validate(self, raw: Dict[str, Any] | FactProposal) -> tuple[Optional[FactProposal], List[Dict[str, str]], List[str]]:
        """Schema + referential validation. Never writes."""
        errors: List[Dict[str, str]] = []
        warnings: List[str] = []
        try:
            proposal = raw if isinstance(raw, FactProposal) else FactProposal.model_validate(raw)
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(p) for p in err.get("loc", ()))
                code = PipelineError.MALFORMED_VALUE
                if "procedure" in err.get("msg", "") or loc == "procedure":
                    code = PipelineError.UNKNOWN_PROCEDURE
                elif loc in ("status_code", "subcode") or "subcode" in err.get("msg", ""):
                    code = PipelineError.UNSUPPORTED_STATUS
                elif loc.startswith("location") or "page" in err.get("msg", ""):
                    code = PipelineError.SOURCE_LOCATION_INVALID
                errors.append({"code": code.value, "field": loc, "message": err.get("msg", "")})
            return None, errors, warnings

        universe = status_universe()
        if universe:
            if proposal.status_code not in universe:
                errors.append({"code": PipelineError.UNSUPPORTED_STATUS.value, "field": "status_code",
                               "message": f"{proposal.status_code} is not a known status code"})
            for code in [proposal.subcode, *proposal.subcodes_covered]:
                if code and code not in universe:
                    errors.append({"code": PipelineError.UNSUPPORTED_STATUS.value, "field": "subcode",
                                   "message": f"{code} is not a known sub-code"})

        loc = proposal.location
        version = self.repo.get_source_version(loc.source_version_id)
        if not version:
            errors.append({"code": PipelineError.SOURCE_LOCATION_INVALID.value, "field": "location.source_version_id",
                           "message": "cited source version does not exist"})
        else:
            if version.get("status") == "withdrawn":
                errors.append({"code": PipelineError.SOURCE_LOCATION_INVALID.value, "field": "location",
                               "message": "cited source version is withdrawn"})
            if version.get("page_count") and loc.page_start and (loc.page_end or loc.page_start) > version["page_count"]:
                errors.append({"code": PipelineError.SOURCE_LOCATION_INVALID.value, "field": "location.page_end",
                               "message": f"page beyond the source version ({version['page_count']} pages)"})
            fam = procedure_family(proposal.procedure)
            if version.get("procedure_family") in ("stay", "visa") and version["procedure_family"] != fam:
                errors.append({"code": PipelineError.PROCEDURE_SCOPE_MISMATCH.value, "field": "procedure",
                               "message": f"{fam} procedure cannot cite a {version['procedure_family']} manual"})
            if version.get("authority_type") in ("approved_manual",) and not loc.page_start and not loc.locator:
                errors.append({"code": PipelineError.SOURCE_LOCATION_INVALID.value, "field": "location",
                               "message": "a manual citation needs a page or locator"})
            sections = self.repo.sections_for(loc.source_version_id)
            if sections and loc.page_start and not any(
                    (s["page_start"] or 0) <= loc.page_start <= (s["page_end"] or s["page_start"] or 10 ** 6)
                    for s in sections):
                warnings.append("page is outside every registered section of this source version")
            if version.get("content_review_state") != "approved":
                warnings.append("cited source edition's content is not yet approved in the manual approval index")
        if proposal.origin == FactOrigin.AI_EXTRACTION and not loc.evidence_excerpt:
            errors.append({"code": PipelineError.EXTRACTION_INVALID.value, "field": "location.evidence_excerpt",
                           "message": "AI extraction must carry the raw evidence excerpt it relied on"})
        return (proposal if not errors else None), errors, warnings

    # ------------------------------------------------------------------
    def classify(self, proposal: FactProposal) -> tuple[str, List[str], str]:
        """dry-run classification against existing knowledge (no writes)."""
        vkey = variant_key(proposal.status_code, proposal.subcode, proposal.procedure, proposal.scenario)
        item = proposal.item_key or normalize_item_key(proposal.value_text)
        skey = slot_key(vkey, proposal.property.value, item)
        phash = self.repo.proposal_hash(proposal, vkey, item)
        dup = self.repo.store.one("SELECT fact_id FROM knowledge_facts WHERE proposal_hash = ?", (phash,))
        if dup:
            return "duplicate", [dup["fact_id"]], skey
        version = self.repo.get_source_version(proposal.location.source_version_id)
        pseudo = {
            "value_text": proposal.value_text, "condition_kind": proposal.condition_kind.value,
            "value_json": {"requirement_level": proposal.requirement_level.value if proposal.requirement_level else ""},
            "effective_from": proposal.effective_from, "effective_to": proposal.effective_to,
            "authority_type": proposal.authority_type.value, "lifecycle_state": "PROPOSED",
            "citations": [{"source_key": version.get("source_key"), "version_label": version.get("version_label"),
                           "source_version_id": proposal.location.source_version_id}],
        }
        others = self.repo.facts_where(
            "f.slot_key = ? AND f.lifecycle_state IN ('DRAFT','AI_EXTRACTED','HUMAN_REVIEW_REQUIRED',"
            "'HUMAN_REVIEWED','VERIFIED','PUBLISHED')", (skey,))
        action, related = "add", []
        for other in others:
            rel = conflict_mod.relation(pseudo, other)
            if rel is None:
                continue
            related.append(other["fact_id"])
            if rel == "corroborates":
                if other["lifecycle_state"] == "PUBLISHED":
                    same_version = any(c["source_version_id"] == proposal.location.source_version_id
                                       for c in other.get("citations") or [])
                    action = "duplicate" if same_version else "reconfirm"
                continue
            if rel == "update":
                action = "update" if action == "add" else action
                continue
            action = "conflict"
        return action, related, skey

    # ------------------------------------------------------------------
    def run(self, adapter: str, proposals: Sequence[Dict[str, Any] | FactProposal], *, mode: str = "dry_run",
            actor: str = "ingestion", actor_kind: Optional[str] = None) -> IngestionReport:
        if mode not in ("dry_run", "validate", "apply"):
            raise ValueError("mode must be dry_run, validate or apply")
        report = IngestionReport(adapter=adapter, mode=mode)
        for index, raw in enumerate(proposals):
            proposal, errors, warnings = self.validate(raw)
            if proposal is None:
                report.items.append(PlanItem(index=index, action="invalid", errors=errors, warnings=warnings,
                                             value_text=str((raw or {}).get("value_text", ""))[:120]
                                             if isinstance(raw, dict) else ""))
                continue
            if mode == "validate":
                report.items.append(PlanItem(index=index, action="valid", value_text=proposal.value_text,
                                             warnings=warnings))
                continue
            action, related, skey = self.classify(proposal)
            item = PlanItem(index=index, action=action, slot_key=skey, value_text=proposal.value_text,
                            warnings=warnings, relates_to=related)
            if mode == "apply" and action != "duplicate":
                self._apply_one(proposal, item, actor=actor, actor_kind=actor_kind)
            elif action == "duplicate":
                item.fact_id = related[0] if related else None
            report.items.append(item)
        logger.info("knowledge_ingestion_run adapter=%s mode=%s summary=%s", adapter, mode,
                    json.dumps(report.summary, sort_keys=True))
        return report

    def _apply_one(self, proposal: FactProposal, item: PlanItem, *, actor: str, actor_kind: Optional[str]) -> None:
        kind = actor_kind or _ORIGIN_ACTOR_KIND[proposal.origin]
        state = _ORIGIN_INITIAL_STATE[proposal.origin]
        fact_id, created = self.repo.insert_proposal(proposal, created_by=actor, created_by_kind=kind,
                                                     initial_state=state)
        item.fact_id = fact_id
        if not created:
            item.action = "duplicate"
            return
        found = conflict_mod.detect_for_fact(self.repo, fact_id)
        compare = found["update_of"]
        if compare:
            # Link the version lineage while the proposal is still editable.
            base = self.repo.get_fact(compare)
            self.repo.store.execute(
                "UPDATE knowledge_facts SET lineage_id = ?, version_no = ?, supersedes_fact_id = ? WHERE fact_id = ?",
                (base["lineage_id"], int(base["version_no"]) + 1, compare, fact_id))
        if item.action == "reconfirm":
            published = [f for f in item.relates_to]
            compare = compare or (published[0] if published else None)
        if proposal.origin == FactOrigin.LEGACY_REPOSITORY_VERIFIED:
            return  # the legacy seed publishes directly; no review task
        task_kind = ("conflict" if found["conflicts"] else "update_fact" if item.action == "update"
                     else "source_refresh" if item.action == "reconfirm" else "new_fact")
        if found["conflicts"]:
            item.action = "conflict"
        item.task_id = self.review.open_task(fact_id, kind=task_kind, compare_fact_id=compare)


def as_report_text(report: IngestionReport) -> str:
    lines = [f"adapter={report.adapter} mode={report.mode}",
             "summary: " + ", ".join(f"{k}={v}" for k, v in sorted(report.summary.items()))]
    for item in report.items:
        if item.action in ("invalid", "conflict", "update", "reconfirm") or item.warnings:
            detail = "; ".join(e["code"] + ": " + e["message"] for e in item.errors)
            lines.append(f"  [{item.action}] #{item.index} {item.value_text[:70]} {detail}".rstrip())
    return "\n".join(lines)


def reject_unsupported(repo: KnowledgeRepository, fact_id: str, reason: str) -> None:
    """System rejection of an invalid proposal (auditable)."""
    ReviewService(repo).reject(fact_id, actor="ingestion-validator", actor_kind=ActorKind.SYSTEM.value, reason=reason)


__all__ = ["IngestionService", "IngestionReport", "PlanItem", "as_report_text", "status_universe",
           "KnowledgeError"]
