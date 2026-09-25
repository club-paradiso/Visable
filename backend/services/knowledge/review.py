"""Human review workflow: queue, actions, transactional publish, impact.

Every action here is performed by a named operator (``actor``) with
``actor_kind='human_operator'``. The only other publisher is the legacy seed,
which can only vouch for repository facts the repository already recorded as
human-verified (see ``lifecycle`` and ``repository.transition``).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import conflicts as conflict_mod
from .models import (
    ActorKind,
    ConditionKind,
    FactOrigin,
    FactProposal,
    KnowledgeError,
    LifecycleState,
    PipelineError,
    RequirementLevel,
    ReviewAction,
    ReviewActionRequest,
    SourceLocation,
    authority_rank,
)
from .repository import KnowledgeRepository
from .store import new_id, row_dict, today, utc_now

HUMAN = ActorKind.HUMAN_OPERATOR.value
S = LifecycleState

_PROCEDURE_RISK = {"status_change": 3, "extension": 2, "registration": 2, "workplace_change": 2,
                   "reentry": 1, "activities_outside_status": 1}


class ReviewService:
    def __init__(self, repo: KnowledgeRepository):
        self.repo = repo
        self.store = repo.store

    # =========================================================================
    # Tasks
    # =========================================================================
    def open_task(self, fact_id: str, *, kind: str, compare_fact_id: Optional[str] = None,
                  note: str = "") -> str:
        """Open (or return the existing open) review task for a fact."""
        existing = self.store.one(
            "SELECT task_id FROM review_tasks WHERE fact_id = ? AND status IN ('open','needs_evidence')",
            (fact_id,))
        if existing:
            if compare_fact_id:
                self.store.execute("UPDATE review_tasks SET compare_fact_id = COALESCE(compare_fact_id, ?)"
                                   " WHERE task_id = ?", (compare_fact_id, existing["task_id"]))
            return existing["task_id"]
        task_id = new_id("rt")
        now = utc_now()
        self.store.execute(
            "INSERT INTO review_tasks(task_id, fact_id, task_kind, status, compare_fact_id, note, created_at,"
            " updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (task_id, fact_id, kind, "open", compare_fact_id, note, now, now),
        )
        self.refresh_priority(task_id)
        return task_id

    def _close_task(self, fact_id: str, status: str) -> None:
        self.store.execute(
            "UPDATE review_tasks SET status = ?, resolved_at = ?, updated_at = ? WHERE fact_id = ?"
            " AND status IN ('open','needs_evidence')",
            (status, utc_now(), utc_now(), fact_id))

    def refresh_priority(self, task_id: str) -> Dict[str, Any]:
        """Transparent priority: each factor is stored alongside the score."""
        task = self.store.one("SELECT * FROM review_tasks WHERE task_id = ?", (task_id,))
        if not task:
            return {}
        fact = self.repo.get_fact(task["fact_id"])
        gap = self.store.one(
            "SELECT COALESCE(SUM(occurrence_count),0) AS occ, COALESCE(SUM(feedback_count),0) AS fb"
            " FROM coverage_gaps WHERE resolution_status IN ('open','investigating')"
            " AND status_code = ? AND procedure = ?",
            (fact["status_code"], fact["procedure"]))
        evals = self.store.one(
            "SELECT COUNT(DISTINCT case_id) AS n FROM eval_case_dependencies WHERE slot_key = ?",
            (fact["slot_key"],))
        conflicts = len(conflict_mod.open_conflicts_for(self.repo, fact["fact_id"]))
        age_days = _age_days(task["created_at"])
        factors = {
            "gap_frequency": int(gap["occ"] or 0),
            "user_feedback": int(gap["fb"] or 0),
            "procedure_risk": _PROCEDURE_RISK.get(fact["procedure"], 1),
            "source_authority_rank": authority_rank(fact["authority_type"]),
            "affected_evals": int(evals["n"] or 0),
            "open_conflicts": conflicts,
            "age_days": age_days,
            "is_update_of_published": int(bool(task["compare_fact_id"])),
        }
        score = (
            min(factors["gap_frequency"], 50) * 2
            + factors["user_feedback"] * 5
            + factors["procedure_risk"] * 10
            + max(0, 9 - factors["source_authority_rank"]) * 2
            + factors["affected_evals"] * 5
            + factors["open_conflicts"] * 20
            + min(age_days, 60)
            + factors["is_update_of_published"] * 15
        )
        self.store.execute("UPDATE review_tasks SET priority_score = ?, priority_factors = ? WHERE task_id = ?",
                           (score, json.dumps(factors, sort_keys=True), task_id))
        return {"score": score, "factors": factors}

    def queue(self, *, status: str = "open", limit: int = 100, status_code: Optional[str] = None) -> List[Dict[str, Any]]:
        where = ["t.status = ?"] if status != "all" else ["1=1"]
        params: List[Any] = [status] if status != "all" else []
        if status_code:
            where.append("v.status_code = ?")
            params.append(status_code)
        rows = self.store.all(
            "SELECT t.*, f.value_text, f.lifecycle_state, f.property, f.origin, f.condition_kind,"
            " v.status_code, v.subcode, v.procedure, v.variant_key"
            " FROM review_tasks t JOIN knowledge_facts f USING(fact_id) JOIN procedure_variants v USING(variant_id)"
            f" WHERE {' AND '.join(where)} ORDER BY t.priority_score DESC, t.created_at LIMIT ?",
            (*params, int(limit)))
        return [row_dict(r, json_fields=("priority_factors",)) for r in rows]

    def task_detail(self, task_id: str) -> Dict[str, Any]:
        task = row_dict(self.store.one("SELECT * FROM review_tasks WHERE task_id = ?", (task_id,)),
                        json_fields=("priority_factors",))
        if not task:
            raise KnowledgeError(PipelineError.NOT_FOUND, f"task {task_id} not found")
        fact = self.repo.get_fact(task["fact_id"])
        compare = self.repo.get_fact(task["compare_fact_id"]) if task.get("compare_fact_id") else None
        if compare is None:
            current = self.repo.published_for_slot(fact["slot_key"])
            compare = current[0] if current else None
        return {
            "task": task,
            "proposed": fact,
            "current_published": compare,
            "diff": field_diff(compare, fact) if compare else None,
            "conflicts": conflict_mod.open_conflicts_for(self.repo, fact["fact_id"]),
            "impact": self.impact(fact),
            "audit": self.repo.audit_trail("fact", fact["fact_id"]),
        }

    # =========================================================================
    # Impact analysis
    # =========================================================================
    def impact(self, fact: Dict[str, Any]) -> Dict[str, Any]:
        cases = [dict(r) for r in self.store.all(
            "SELECT c.case_id, c.case_key, c.state FROM eval_case_dependencies d JOIN eval_cases c USING(case_id)"
            " WHERE d.slot_key = ? ORDER BY c.case_key", (fact["slot_key"],))]
        published = self.repo.published_for_slot(fact["slot_key"])
        return {
            "status_code": fact["status_code"],
            "subcode": fact.get("subcode"),
            "procedure": fact["procedure"],
            "variant_key": fact["variant_key"],
            "affected_eval_cases": cases,
            "affected_eval_count": len(cases),
            "would_supersede": [p["fact_id"] for p in published if p["fact_id"] != fact["fact_id"]],
            "requires_regression_rerun": bool(cases) or bool(published),
        }

    # =========================================================================
    # Actions
    # =========================================================================
    def act(self, fact_id: str, request: ReviewActionRequest, *, actor: str,
            actor_kind: str = HUMAN) -> Dict[str, Any]:
        if not actor or actor in ("anonymous", "system"):
            raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "review actions need a named operator")
        action = request.action
        if action == ReviewAction.START_REVIEW:
            return self.start_review(fact_id, actor=actor, actor_kind=actor_kind, reason=request.reason)
        if action == ReviewAction.APPROVE:
            return self._step(fact_id, S.HUMAN_REVIEWED, actor, actor_kind, request.reason)
        if action == ReviewAction.VERIFY:
            return self._step(fact_id, S.VERIFIED, actor, actor_kind, request.reason)
        if action == ReviewAction.PUBLISH:
            return self.publish(fact_id, actor=actor, actor_kind=actor_kind, reason=request.reason,
                                supersedes_fact_id=request.supersedes_fact_id)
        if action == ReviewAction.REJECT:
            return self.reject(fact_id, actor=actor, actor_kind=actor_kind, reason=request.reason)
        if action == ReviewAction.NEEDS_EVIDENCE:
            return self.needs_evidence(fact_id, actor=actor, actor_kind=actor_kind, reason=request.reason)
        if action == ReviewAction.EDIT:
            return self.edit(fact_id, request, actor=actor, actor_kind=actor_kind)
        if action == ReviewAction.WITHDRAW:
            return self._step(fact_id, S.WITHDRAWN, actor, actor_kind, request.reason, close_task=None)
        raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, f"unsupported action {action}")

    def start_review(self, fact_id: str, *, actor: str, actor_kind: str, reason: str = "") -> Dict[str, Any]:
        fact = self.repo.get_fact(fact_id)
        with self.store.transaction():
            if fact["lifecycle_state"] in (S.DRAFT.value, S.AI_EXTRACTED.value):
                fact = self.repo.transition(fact_id, S.HUMAN_REVIEW_REQUIRED, actor=actor,
                                            actor_kind=actor_kind, reason=reason)
            self.open_task(fact_id, kind="new_fact")
        return fact

    def _step(self, fact_id: str, target: S, actor: str, actor_kind: str, reason: str,
              close_task: Optional[str] = "keep") -> Dict[str, Any]:
        with self.store.transaction():
            if target in (S.HUMAN_REVIEWED, S.VERIFIED):
                self._assert_no_open_conflicts(fact_id)
            fact = self.repo.transition(fact_id, target, actor=actor, actor_kind=actor_kind, reason=reason)
        return fact

    def _assert_no_open_conflicts(self, fact_id: str) -> None:
        open_c = conflict_mod.open_conflicts_for(self.repo, fact_id)
        if open_c:
            raise KnowledgeError(
                PipelineError.CONFLICT_DETECTED,
                "resolve the open conflict(s) on this fact before approving or publishing it",
                detail={"conflicts": [c["conflict_id"] for c in open_c]},
            )

    def publish(self, fact_id: str, *, actor: str, actor_kind: str = HUMAN, reason: str = "",
                supersedes_fact_id: Optional[str] = None, _fail_after_supersede: bool = False) -> Dict[str, Any]:
        """VERIFIED -> PUBLISHED, superseding the slot's current fact atomically.

        Either the new fact is published AND the old one is superseded (or
        end-dated, for a future-effective successor), or nothing changes.
        """
        fact = self.repo.get_fact(fact_id)
        if fact["lifecycle_state"] != S.VERIFIED.value:
            raise KnowledgeError(PipelineError.REVIEW_REQUIRED,
                                 f"only VERIFIED facts can be published (state={fact['lifecycle_state']})")
        if not fact["citations"]:
            raise KnowledgeError(PipelineError.PUBLISH_FAILED, "a published fact needs provenance")
        for cit in fact["citations"]:
            if cit.get("version_status") == "withdrawn":
                raise KnowledgeError(PipelineError.PUBLISH_FAILED, "cited source version is withdrawn")
            if cit.get("source_family") in ("stay", "visa") and cit["source_family"] != fact["procedure_family"]:
                raise KnowledgeError(PipelineError.PROCEDURE_SCOPE_MISMATCH,
                                     "visa-issuance and stay procedures must not cite each other's manuals")
        self._assert_no_open_conflicts(fact_id)
        targets = ([self.repo.get_fact(supersedes_fact_id)] if supersedes_fact_id
                   else [p for p in self.repo.published_for_slot(fact["slot_key"]) if p["fact_id"] != fact_id])
        now = utc_now()
        future = bool(fact.get("effective_from") and fact["effective_from"] > today())
        with self.store.transaction():
            for old in targets:
                if old["slot_key"] != fact["slot_key"]:
                    raise KnowledgeError(PipelineError.PUBLISH_FAILED, "supersede target is a different slot")
                if old["lifecycle_state"] != S.PUBLISHED.value:
                    raise KnowledgeError(PipelineError.PUBLISH_FAILED, "supersede target is not published")
                if future:
                    self.repo.set_fact_links(old["fact_id"], effective_to=fact["effective_from"],
                                             superseded_by_fact_id=fact_id)
                    self.store.audit(actor=actor, actor_kind=actor_kind, entity_type="fact",
                                     entity_id=old["fact_id"], action="end_date", reason=reason,
                                     before={"effective_to": old.get("effective_to")},
                                     after={"effective_to": fact["effective_from"], "successor": fact_id})
                else:
                    self.repo.transition(old["fact_id"], S.SUPERSEDED, actor=actor, actor_kind=actor_kind,
                                         reason=f"superseded by {fact_id}", at=now)
                    self.repo.set_fact_links(old["fact_id"], superseded_by_fact_id=fact_id)
                if _fail_after_supersede:  # test hook: prove rollback
                    raise KnowledgeError(PipelineError.PUBLISH_FAILED, "injected failure")
            if targets:
                self.repo.set_fact_links(fact_id, supersedes_fact_id=targets[0]["fact_id"])
            published = self.repo.transition(fact_id, S.PUBLISHED, actor=actor, actor_kind=actor_kind,
                                             reason=reason, at=now)
            self._close_task(fact_id, "resolved")
        return published

    def reject(self, fact_id: str, *, actor: str, actor_kind: str = HUMAN, reason: str = "") -> Dict[str, Any]:
        if not reason.strip():
            raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "a rejection needs a reason")
        with self.store.transaction():
            fact = self.repo.transition(fact_id, S.REJECTED, actor=actor, actor_kind=actor_kind, reason=reason)
            self._close_task(fact_id, "rejected")
            for c in conflict_mod.open_conflicts_for(self.repo, fact_id):
                self.store.execute("UPDATE knowledge_conflicts SET status='resolved', resolved_at=?, resolution=?"
                                   " WHERE conflict_id = ?", (utc_now(), f"rejected {fact_id}: {reason}",
                                                              c["conflict_id"]))
                self.store.audit(actor=actor, actor_kind=actor_kind, entity_type="conflict",
                                 entity_id=c["conflict_id"], action="resolve", reason=f"rejected {fact_id}")
        return fact

    def needs_evidence(self, fact_id: str, *, actor: str, actor_kind: str = HUMAN, reason: str = "") -> Dict[str, Any]:
        fact = self.repo.get_fact(fact_id)
        with self.store.transaction():
            if fact["lifecycle_state"] in (S.DRAFT.value, S.AI_EXTRACTED.value):
                self.repo.transition(fact_id, S.HUMAN_REVIEW_REQUIRED, actor=actor, actor_kind=actor_kind)
            elif fact["lifecycle_state"] in (S.HUMAN_REVIEWED.value, S.VERIFIED.value):
                self.repo.transition(fact_id, S.HUMAN_REVIEW_REQUIRED, actor=actor, actor_kind=actor_kind,
                                     reason="sent back: needs more evidence")
            task_id = self.open_task(fact_id, kind="new_fact")
            self.store.execute("UPDATE review_tasks SET status='needs_evidence', note=?, updated_at=? WHERE task_id=?",
                               (reason, utc_now(), task_id))
            self.store.audit(actor=actor, actor_kind=actor_kind, entity_type="fact", entity_id=fact_id,
                             action="needs_evidence", reason=reason)
        return self.repo.get_fact(fact_id)

    def edit(self, fact_id: str, request: ReviewActionRequest, *, actor: str,
             actor_kind: str = HUMAN) -> Dict[str, Any]:
        """An edit is a NEW proposal version; the edited proposal is retired.

        Published/verified content is never mutated in place (DB trigger).
        """
        fact = self.repo.get_fact(fact_id)
        if fact["lifecycle_state"] in (S.REJECTED.value, S.SUPERSEDED.value, S.WITHDRAWN.value):
            raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "cannot edit a retired fact")
        cit = fact["citations"][0]
        value = fact.get("value_json") or {}
        level = request.requirement_level or (RequirementLevel(value["requirement_level"])
                                              if value.get("requirement_level") else None)
        proposal = FactProposal(
            status_code=fact["status_code"], subcode=fact.get("subcode"),
            subcodes_covered=fact.get("subcodes_covered") or [], procedure=fact["procedure"],
            scenario=fact["scenario"], section_title=fact.get("variant_section") or "",
            property=fact["property"], item_key=fact["item_key"],
            value_text=request.value_text if request.value_text is not None else fact["value_text"],
            requirement_level=level,
            condition_kind=request.condition_kind or ConditionKind(fact["condition_kind"]),
            condition_text=request.condition_text if request.condition_text is not None else fact["condition_text"],
            display_translations=fact.get("display_translations") or {}, sort_order=fact["sort_order"],
            authority_type=fact["authority_type"], origin=FactOrigin.OPERATOR_MANUAL,
            effective_from=request.effective_from or fact.get("effective_from"),
            effective_to=fact.get("effective_to"),
            location=SourceLocation(
                source_version_id=cit["source_version_id"], section_title=cit.get("section_title") or "",
                page_start=cit.get("page_start"), page_end=cit.get("page_end"), locator=cit.get("locator") or "",
                evidence_excerpt=cit.get("evidence_excerpt") or ""),
        )
        pending = fact["lifecycle_state"] not in (S.PUBLISHED.value,)
        with self.store.transaction():
            new_fact_id, created = self.repo.insert_proposal(
                proposal, created_by=actor, created_by_kind=actor_kind,
                initial_state=S.HUMAN_REVIEW_REQUIRED, lineage_id=fact["lineage_id"],
                version_no=int(fact["version_no"]) + 1,
                supersedes_fact_id=None if pending else fact_id,
            )
            if not created:
                raise KnowledgeError(PipelineError.DUPLICATE_FACT, "the edited fact is identical to an existing one")
            if pending:
                self.repo.transition(fact_id, S.REJECTED, actor=actor, actor_kind=actor_kind,
                                     reason=f"replaced by edited version {new_fact_id}")
                self._close_task(fact_id, "rejected")
            compare = fact_id if not pending else (self._published_id(fact["slot_key"]))
            self.open_task(new_fact_id, kind="update_fact" if compare else "new_fact", compare_fact_id=compare,
                           note=request.reason)
            self.store.audit(actor=actor, actor_kind=actor_kind, entity_type="fact", entity_id=new_fact_id,
                             action="edit", reason=request.reason, before={"from_fact": fact_id},
                             after={"value_text": proposal.value_text})
        conflict_mod.detect_for_fact(self.repo, new_fact_id)
        return self.repo.get_fact(new_fact_id)

    def _published_id(self, slot: str) -> Optional[str]:
        rows = self.repo.published_for_slot(slot)
        return rows[0]["fact_id"] if rows else None

    def resolve_conflict(self, conflict_id: str, *, keep_fact_id: Optional[str], actor: str,
                         reason: str, actor_kind: str = HUMAN) -> Dict[str, Any]:
        row = self.store.one("SELECT * FROM knowledge_conflicts WHERE conflict_id = ?", (conflict_id,))
        if not row:
            raise KnowledgeError(PipelineError.NOT_FOUND, f"conflict {conflict_id} not found")
        if not reason.strip():
            raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "resolving a conflict needs a reason")
        pair = (row["fact_a_id"], row["fact_b_id"])
        if keep_fact_id and keep_fact_id not in pair:
            raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "keep_fact_id must be one of the two facts")
        with self.store.transaction():
            status = "resolved" if keep_fact_id else "dismissed"
            self.store.execute("UPDATE knowledge_conflicts SET status=?, resolved_at=?, resolution=? WHERE conflict_id=?",
                               (status, utc_now(), reason, conflict_id))
            self.store.audit(actor=actor, actor_kind=actor_kind, entity_type="conflict", entity_id=conflict_id,
                             action=status, reason=reason, after={"keep": keep_fact_id})
            if keep_fact_id:
                loser = pair[1] if keep_fact_id == pair[0] else pair[0]
                loser_fact = self.repo.get_fact(loser)
                if loser_fact["lifecycle_state"] in ("DRAFT", "AI_EXTRACTED", "HUMAN_REVIEW_REQUIRED",
                                                     "HUMAN_REVIEWED", "VERIFIED"):
                    self.repo.transition(loser, S.REJECTED, actor=actor, actor_kind=actor_kind,
                                         reason=f"conflict {conflict_id} resolved in favour of {keep_fact_id}")
                    self._close_task(loser, "rejected")
        return dict(self.store.one("SELECT * FROM knowledge_conflicts WHERE conflict_id = ?", (conflict_id,)))


def field_diff(current: Optional[Dict[str, Any]], proposed: Dict[str, Any]) -> Dict[str, Any]:
    """Before/after view for the review screen ("Current published: X / Proposed: Y")."""
    def view(f):
        if not f:
            return None
        cit = (f.get("citations") or [{}])[0]
        return {
            "value_text": f.get("value_text"),
            "condition_kind": f.get("condition_kind"),
            "condition_text": f.get("condition_text"),
            "requirement_level": (f.get("value_json") or {}).get("requirement_level"),
            "effective_from": f.get("effective_from"),
            "source": f"{cit.get('source_title', '')} {cit.get('version_label', '')}".strip(),
            "pages": conflict_mod._pages(cit),
        }
    before, after = view(current), view(proposed)
    changed = [k for k in (after or {}) if (before or {}).get(k) != (after or {}).get(k)]
    return {"current": before, "proposed": after, "changed_fields": changed}


def _age_days(created_at: str) -> int:
    try:
        created = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return 0
    return max(0, (datetime.now(timezone.utc) - created).days)
