"""Continuous-improvement loop: observations, coverage gaps, feedback, promotion.

    production query -> structured observation -> coverage decision
      -> knowledge gap (deduplicated) / user feedback
      -> human review -> new or corrected knowledge (review.py)
      -> regression eval (promote_gap_to_eval) -> re-evaluation (evals.py)

What this module deliberately does NOT do:
* it never writes a knowledge fact — an answer, a gap or a feedback item is
  never evidence (no self-training loop; facts need an external source);
* it never records a user-fact gap (missing status, ambiguous question) as a
  knowledge gap;
* it never stores raw text (see ``privacy``).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from . import privacy
from .coverage import CoverageDecision, gap_dedupe_key
from .models import (
    FEEDBACK_GAP_REASON,
    UNKNOWN_QUERY_REASONS,
    EvalCaseIn,
    FeedbackIn,
    KnowledgeError,
    PipelineError,
)
from .store import KnowledgeStore, new_id, row_dict, utc_now
from .understanding import QueryUnderstanding

logger = logging.getLogger("paradiso.knowledge")


class LearningService:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    # ------------------------------------------------------------------
    def record_observation(self, u: QueryUnderstanding, decision: CoverageDecision, *, raw_query: str,
                           guard_outcome: str = "not_run", fact_ids: Optional[List[str]] = None) -> Dict[str, Optional[str]]:
        """Persist one minimized observation; upsert a gap for knowledge gaps.

        Never raises (the learning loop must not break an answer).
        """
        if not privacy.observations_enabled():
            return {"observation_id": None, "gap_id": None}
        try:
            obs_id = new_id("obs")
            with self.store.transaction():
                self.store.execute(
                    "INSERT INTO query_observations(observation_id, observed_at, expires_at, language, status_code,"
                    " subcode, procedure, intent, coverage_state, answer_path, gap_reason, guard_outcome,"
                    " sanitized_query, query_fingerprint, fact_ids) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (obs_id, utc_now(), privacy.expiry(), u.query_language, u.status_code, u.subcode, u.procedure,
                     u.intent, decision.state, decision.answer_path, decision.gap_reason, guard_outcome,
                     privacy.stored_excerpt(raw_query), privacy.fingerprint(raw_query),
                     json.dumps(fact_ids or [])),
                )
                gap_id = None
                if decision.gap_reason:
                    gap_id = self._upsert_gap(u, decision.gap_reason, raw_query)
            logger.info("knowledge_coverage_decision state=%s path=%s reason=%s status=%s procedure=%s intent=%s",
                        decision.state, decision.answer_path, decision.gap_reason or "-", u.status_code or "-",
                        u.procedure or "-", u.intent)
            return {"observation_id": obs_id, "gap_id": gap_id}
        except Exception as exc:  # pragma: no cover - persistence must never break /api/ask
            logger.warning("knowledge_observation_failed error=%s", type(exc).__name__)
            return {"observation_id": None, "gap_id": None}

    def _upsert_gap(self, u: QueryUnderstanding, reason: str, raw_query: str, *, feedback: bool = False) -> str:
        key = gap_dedupe_key(u, reason)
        now = utc_now()
        example = privacy.stored_excerpt(raw_query)
        row = self.store.one("SELECT gap_id, resolution_status FROM coverage_gaps WHERE dedupe_key = ?", (key,))
        if row:
            reopened = row["resolution_status"] == "resolved"
            self.store.execute(
                "UPDATE coverage_gaps SET occurrence_count = occurrence_count + ?, feedback_count = feedback_count + ?,"
                " last_seen = ?, example_query = CASE WHEN ? <> '' THEN ? ELSE example_query END"
                + (", resolution_status = 'open', resolved_at = NULL" if reopened else "") + " WHERE gap_id = ?",
                (0 if feedback else 1, 1 if feedback else 0, now, example, example, row["gap_id"]))
            if reopened:
                self.store.audit(actor="learning-loop", actor_kind="system", entity_type="gap",
                                 entity_id=row["gap_id"], action="reopen", reason="recurred after resolution")
            return row["gap_id"]
        gap_id = new_id("gap")
        self.store.execute(
            "INSERT INTO coverage_gaps(gap_id, dedupe_key, reason_code, status_code, subcode, procedure, intent,"
            " occurrence_count, feedback_count, first_seen, last_seen, example_query)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (gap_id, key, reason, u.status_code, u.subcode, u.procedure, u.intent,
             1, 1 if feedback else 0, now, now, example))
        logger.info("knowledge_gap_created reason=%s status=%s procedure=%s intent=%s",
                    reason, u.status_code or "-", u.procedure or "-", u.intent)
        return gap_id

    # ------------------------------------------------------------------
    def record_feedback(self, fb: FeedbackIn) -> Dict[str, Optional[str]]:
        obs = None
        if fb.answer_ref:
            obs = self.store.one("SELECT * FROM query_observations WHERE observation_id = ?", (fb.answer_ref,))
        status_code = (obs["status_code"] if obs else fb.status_code) or None
        procedure = (obs["procedure"] if obs else fb.procedure) or None
        intent = (obs["intent"] if obs else fb.intent) or None
        coverage = (obs["coverage_state"] if obs else fb.coverage_state) or ""
        fact_ids = obs["fact_ids"] if obs else "[]"
        gap_id = None
        reason = FEEDBACK_GAP_REASON.get(fb.reason.value)
        feedback_id = new_id("fb")
        with self.store.transaction():
            if reason:
                u = QueryUnderstanding(query_language=fb.language or "", status_code=status_code,
                                       subcode=obs["subcode"] if obs else None, procedure=procedure,
                                       task_type=None, intent=intent or "general_explanation")
                gap_id = self._upsert_gap(u, reason, obs["sanitized_query"] if obs else "", feedback=True)
            self.store.execute(
                "INSERT INTO user_feedback(feedback_id, created_at, reason, language, status_code, procedure, intent,"
                " coverage_state, fact_ids, comment_sanitized, gap_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (feedback_id, utc_now(), fb.reason.value, fb.language, status_code, procedure, intent, coverage,
                 fact_ids, privacy.sanitize(fb.comment, 300) if privacy.text_retention_enabled() else "", gap_id))
        logger.info("knowledge_feedback_recorded reason=%s gap=%s", fb.reason.value, bool(gap_id))
        return {"feedback_id": feedback_id, "gap_id": gap_id}

    # ------------------------------------------------------------------
    def list_gaps(self, *, status: str = "open", kind: str = "all", limit: int = 200) -> List[Dict[str, Any]]:
        where, params = [], []
        if status != "all":
            where.append("resolution_status = ?")
            params.append(status)
        if kind == "unknown":
            where.append("reason_code IN (%s)" % ",".join("?" * len(UNKNOWN_QUERY_REASONS)))
            params.extend(sorted(UNKNOWN_QUERY_REASONS))
        elif kind == "feedback":
            where.append("feedback_count > 0")
        sql = "SELECT * FROM coverage_gaps" + (" WHERE " + " AND ".join(where) if where else "")
        sql += " ORDER BY occurrence_count + 3 * feedback_count DESC, last_seen DESC LIMIT ?"
        return [row_dict(r) for r in self.store.all(sql, (*params, int(limit)))]

    def get_gap(self, gap_id: str) -> Dict[str, Any]:
        row = row_dict(self.store.one("SELECT * FROM coverage_gaps WHERE gap_id = ?", (gap_id,)))
        if not row:
            raise KnowledgeError(PipelineError.NOT_FOUND, f"gap {gap_id} not found")
        row["feedback"] = [row_dict(r) for r in self.store.all(
            "SELECT feedback_id, created_at, reason, language, comment_sanitized FROM user_feedback WHERE gap_id = ?"
            " ORDER BY created_at DESC LIMIT 20", (gap_id,))]
        row["audit"] = [row_dict(r, json_fields=("before_json", "after_json")) for r in self.store.all(
            "SELECT * FROM audit_log WHERE entity_type = 'gap' AND entity_id = ? ORDER BY at", (gap_id,))]
        return row

    def update_gap(self, gap_id: str, *, resolution_status: str, note: str, actor: str,
                   linked_task_id: Optional[str] = None) -> Dict[str, Any]:
        if resolution_status not in ("open", "investigating", "resolved", "wont_fix"):
            raise KnowledgeError(PipelineError.MALFORMED_VALUE, "unknown resolution status")
        before = self.get_gap(gap_id)
        with self.store.transaction():
            self.store.execute(
                "UPDATE coverage_gaps SET resolution_status = ?, resolution_note = ?,"
                " linked_task_id = COALESCE(?, linked_task_id), resolved_at = CASE WHEN ? = 'resolved' THEN ? ELSE NULL END"
                " WHERE gap_id = ?", (resolution_status, note, linked_task_id, resolution_status, utc_now(), gap_id))
            self.store.audit(actor=actor, actor_kind="human_operator", entity_type="gap", entity_id=gap_id,
                             action=f"status:{resolution_status}", reason=note,
                             before={"resolution_status": before["resolution_status"]},
                             after={"resolution_status": resolution_status, "linked_task_id": linked_task_id})
        return self.get_gap(gap_id)

    def purge_expired(self, now: Optional[str] = None) -> int:
        cur = self.store.execute("DELETE FROM query_observations WHERE expires_at <= ?", (now or utc_now(),))
        return cur.rowcount or 0

    def metrics(self) -> Dict[str, int]:
        one = lambda sql, p=(): (self.store.one(sql, p) or [0])[0]  # noqa: E731
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        marks = ",".join("?" * len(UNKNOWN_QUERY_REASONS))
        return {
            "unresolved_gaps": one("SELECT COUNT(*) FROM coverage_gaps WHERE resolution_status IN ('open','investigating')"),
            "new_unknown_clusters_7d": one(
                f"SELECT COUNT(*) FROM coverage_gaps WHERE first_seen >= ? AND reason_code IN ({marks})",
                (week_ago, *sorted(UNKNOWN_QUERY_REASONS))),
            "feedback_7d": one("SELECT COUNT(*) FROM user_feedback WHERE created_at >= ?", (week_ago,)),
            "observations_retained": one("SELECT COUNT(*) FROM query_observations"),
        }

    def promote_gap_to_eval(self, gap_id: str, case: EvalCaseIn, *, actor: str, evals) -> Dict[str, Any]:
        """Resolved gap -> draft regression case (approved separately by a human)."""
        gap = self.get_gap(gap_id)
        created = evals.create_case(case, actor=actor, origin="promoted_gap", source_gap_id=gap_id)
        with self.store.transaction():
            self.store.execute("UPDATE coverage_gaps SET linked_eval_case_id = ? WHERE gap_id = ?",
                               (created["case_id"], gap_id))
            self.store.audit(actor=actor, actor_kind="human_operator", entity_type="gap", entity_id=gap_id,
                             action="promote_to_eval", after={"case_key": created["case_key"],
                                                             "gap_status": gap["resolution_status"]})
        return created
