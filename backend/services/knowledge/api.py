"""HTTP surface of the Knowledge Platform (FastAPI router).

Public (anonymous) endpoints — rate-limited, no privileged data:
    POST /api/feedback                     structured answer feedback
    GET  /api/knowledge/published          portable export of PUBLISHED knowledge

Operator endpoints — ``Authorization: Bearer <token>`` required:
    everything under /api/knowledge/studio/...

Authentication
--------------
Operator tokens come from ``WAYMAKER_OPERATOR_TOKENS`` — a comma-separated
list of ``name:token`` pairs (e.g. ``alice:9f2...``). The name becomes the
reviewer of record in the audit log. Tokens are compared in constant time.
When the variable is unset, every operator endpoint answers 503
``operator_auth_not_configured`` — the Studio is closed by default, never open.

The Knowledge Studio page (knowledge-studio.html) holds no data; everything it
shows is fetched through these authenticated endpoints.
"""
from __future__ import annotations

import hmac
import logging
import os
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .adapters import status_guidance_proposals
from .diff import diff_versions, fact_version_history
from .models import (
    EvalCaseIn,
    FactOrigin,
    FactProposal,
    FeedbackIn,
    KnowledgeError,
    PipelineError,
    ReviewActionRequest,
)
from . import conflicts as conflict_mod

logger = logging.getLogger("paradiso.knowledge")

_OPERATOR_ENV = "WAYMAKER_OPERATOR_TOKENS"


# ---------------------------------------------------------------------------
# Operator authentication
# ---------------------------------------------------------------------------
def _operator_tokens() -> Dict[str, str]:
    tokens: Dict[str, str] = {}
    for pair in (os.environ.get(_OPERATOR_ENV) or "").split(","):
        name, sep, token = pair.strip().partition(":")
        if sep and name.strip() and len(token.strip()) >= 16:
            tokens[token.strip()] = name.strip()
    return tokens


def require_operator(request: Request) -> str:
    """FastAPI dependency: returns the operator name or raises 401/503."""
    tokens = _operator_tokens()
    if not tokens:
        raise HTTPException(status_code=503, detail={"error": "operator_auth_not_configured",
                                                     "message": "Knowledge Studio is disabled on this server."})
    header = request.headers.get("authorization") or ""
    scheme, _, supplied = header.partition(" ")
    if scheme.lower() != "bearer" or not supplied.strip():
        raise HTTPException(status_code=401, detail={"error": "operator_auth_required"},
                            headers={"WWW-Authenticate": "Bearer"})
    supplied = supplied.strip()
    for token, name in tokens.items():
        if hmac.compare_digest(token.encode("utf-8"), supplied.encode("utf-8")):
            return name
    logger.warning("knowledge_operator_auth_failed")
    raise HTTPException(status_code=401, detail={"error": "operator_auth_invalid"},
                        headers={"WWW-Authenticate": "Bearer"})


def _err(exc: KnowledgeError) -> HTTPException:
    status = {PipelineError.NOT_FOUND: 404, PipelineError.CONFLICT_DETECTED: 409,
              PipelineError.DUPLICATE_FACT: 409, PipelineError.TRANSITION_FORBIDDEN: 409,
              PipelineError.REVIEW_REQUIRED: 409}.get(exc.code, 422)
    return HTTPException(status_code=status, detail=exc.to_dict())


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------
class IngestRequest(BaseModel):
    adapter: str = Field(pattern=r"^(status_guidance|proposals)$")
    mode: str = Field(default="dry_run", pattern=r"^(dry_run|validate|apply)$")
    statuses: List[str] = Field(default_factory=list, max_length=50)
    procedures: List[str] = Field(default_factory=lambda: ["extension"], max_length=10)
    proposals: List[Dict[str, Any]] = Field(default_factory=list, max_length=500)


class GapUpdate(BaseModel):
    resolution_status: str = Field(pattern=r"^(open|investigating|resolved|wont_fix)$")
    note: str = Field(default="", max_length=2000)
    linked_task_id: Optional[str] = None


class ConflictResolution(BaseModel):
    keep_fact_id: Optional[str] = None
    reason: str = Field(min_length=3, max_length=2000)


class EvalStateUpdate(BaseModel):
    state: str = Field(pattern=r"^(draft|approved|retired)$")
    reason: str = Field(default="", max_length=1000)


class EvalRunRequest(BaseModel):
    selector: str = Field(default="all", max_length=120)


class RefreshStateUpdate(BaseModel):
    refresh_state: str = Field(pattern=r"^(current|refresh_due|superseded|unavailable)$")
    reason: str = Field(default="", max_length=1000)


# ---------------------------------------------------------------------------
def build_knowledge_router(get_platform: Callable[[], Any], feedback_rate_limit=None) -> APIRouter:
    router = APIRouter()
    op = APIRouter(prefix="/api/knowledge/studio", dependencies=[Depends(require_operator)])

    def P():
        return get_platform()

    # ---------------- public ----------------
    deps = [Depends(feedback_rate_limit)] if feedback_rate_limit else []

    @router.post("/api/feedback", dependencies=deps)
    def submit_feedback(body: FeedbackIn) -> Dict[str, Any]:
        try:
            P().learning.record_feedback(body)
        except KnowledgeError as exc:
            raise _err(exc)
        # No ids echoed: the client needs nothing but an acknowledgement.
        return {"ok": True}

    @router.get("/api/knowledge/published")
    def published_export() -> Dict[str, Any]:
        return P().export_published()

    # ---------------- operator: overview ----------------
    @op.get("/overview")
    def overview(operator: str = Depends(require_operator)) -> Dict[str, Any]:
        data = P().overview()
        data["operator"] = operator
        return data

    @op.get("/sources")
    def sources() -> Dict[str, Any]:
        return {"sources": P().repo.list_sources()}

    @op.post("/sources/{source_id}/refresh-state")
    def set_refresh(source_id: str, body: RefreshStateUpdate, operator: str = Depends(require_operator)):
        try:
            P().repo.set_source_refresh_state(source_id, body.refresh_state, actor=operator,
                                              actor_kind="human_operator", reason=body.reason)
        except KnowledgeError as exc:
            raise _err(exc)
        return {"ok": True}

    @op.get("/diff")
    def source_diff(from_version: str, to_version: str, status_code: Optional[str] = None,
                    procedure: Optional[str] = None, include_unchanged: bool = True,
                    property: str = Query(default="required_document", max_length=40)):
        props = None if property == "all" else [property]
        try:
            return diff_versions(P().repo, from_version, to_version, status_code=status_code,
                                 procedure=procedure, properties=props, include_unchanged=include_unchanged)
        except KnowledgeError as exc:
            raise _err(exc)

    # ---------------- operator: facts ----------------
    @op.get("/facts")
    def list_facts(state: str = Query(default="PUBLISHED", max_length=40), status_code: Optional[str] = None,
                   procedure: Optional[str] = None, limit: int = Query(default=200, le=1000)):
        where, params = [], []
        if state != "all":
            where.append("f.lifecycle_state = ?")
            params.append(state)
        if status_code:
            where.append("v.status_code = ?")
            params.append(status_code)
        if procedure:
            where.append("v.procedure = ?")
            params.append(procedure)
        return {"facts": P().repo.facts_where(" AND ".join(where) or "1=1", params, limit=limit)}

    @op.get("/facts/{fact_id}")
    def fact_detail(fact_id: str):
        platform = P()
        try:
            fact = platform.repo.get_fact(fact_id)
        except KnowledgeError as exc:
            raise _err(exc)
        return {"fact": fact, "history": fact_version_history(platform.repo, fact["lineage_id"]),
                "audit": platform.repo.audit_trail("fact", fact_id),
                "conflicts": conflict_mod.open_conflicts_for(platform.repo, fact_id),
                "impact": platform.review.impact(fact)}

    @op.post("/facts")
    def create_manual_fact(body: Dict[str, Any] = Body(...), operator: str = Depends(require_operator)):
        """Manual operator proposal: always origin=operator_manual, enters review."""
        body = dict(body)
        body["origin"] = FactOrigin.OPERATOR_MANUAL.value
        report = P().ingestion.run("operator_manual", [body], mode="apply", actor=operator,
                                   actor_kind="human_operator")
        item = report.items[0]
        if item.action == "invalid":
            raise HTTPException(status_code=422, detail={"error": PipelineError.EXTRACTION_INVALID.value,
                                                         "errors": item.errors})
        return {"result": item.to_dict()}

    @op.post("/facts/{fact_id}/actions")
    def fact_action(fact_id: str, body: ReviewActionRequest, operator: str = Depends(require_operator)):
        try:
            fact = P().review.act(fact_id, body, actor=operator)
        except KnowledgeError as exc:
            raise _err(exc)
        logger.info("knowledge_review_action action=%s fact=%s", body.action.value, fact_id)
        return {"fact": fact}

    # ---------------- operator: review queue ----------------
    @op.get("/review-queue")
    def review_queue(status: str = Query(default="open", pattern=r"^(open|needs_evidence|resolved|rejected|all)$"),
                     status_code: Optional[str] = None, limit: int = Query(default=100, le=500)):
        return {"tasks": P().review.queue(status=status, status_code=status_code, limit=limit)}

    @op.get("/review-queue/{task_id}")
    def review_task(task_id: str):
        try:
            return P().review.task_detail(task_id)
        except KnowledgeError as exc:
            raise _err(exc)

    @op.get("/evidence/{fact_id}")
    def evidence(fact_id: str):
        from .evidence import evidence_for_fact
        try:
            return evidence_for_fact(P().repo, fact_id)
        except KnowledgeError as exc:
            raise _err(exc)

    # ---------------- operator: conflicts ----------------
    @op.get("/conflicts")
    def conflicts(status: str = Query(default="open", pattern=r"^(open|resolved|dismissed)$")):
        return {"conflicts": conflict_mod.list_conflicts(P().repo, status=status)}

    @op.post("/conflicts/{conflict_id}/resolve")
    def resolve_conflict(conflict_id: str, body: ConflictResolution, operator: str = Depends(require_operator)):
        try:
            return {"conflict": P().review.resolve_conflict(conflict_id, keep_fact_id=body.keep_fact_id,
                                                            actor=operator, reason=body.reason)}
        except KnowledgeError as exc:
            raise _err(exc)

    # ---------------- operator: ingestion ----------------
    @op.post("/ingest")
    def ingest(body: IngestRequest, operator: str = Depends(require_operator)):
        platform = P()
        if body.adapter == "status_guidance":
            proposals = status_guidance_proposals(platform.repo, statuses=body.statuses or None,
                                                  procedures=body.procedures)
            actor, kind = f"parser:status_guidance (by {operator})", "parser"
        else:
            proposals = [dict(p, origin=FactOrigin.OPERATOR_MANUAL.value) for p in body.proposals]
            actor, kind = operator, "human_operator"
        report = platform.ingestion.run(body.adapter, proposals, mode=body.mode, actor=actor, actor_kind=kind)
        return report.to_dict()

    # ---------------- operator: gaps / unknown queries ----------------
    @op.get("/gaps")
    def gaps(status: str = Query(default="open", pattern=r"^(open|investigating|resolved|wont_fix|all)$"),
             kind: str = Query(default="all", pattern=r"^(all|unknown|feedback)$")):
        return {"gaps": P().learning.list_gaps(status=status, kind=kind)}

    @op.get("/gaps/{gap_id}")
    def gap_detail(gap_id: str):
        try:
            return P().learning.get_gap(gap_id)
        except KnowledgeError as exc:
            raise _err(exc)

    @op.post("/gaps/{gap_id}")
    def update_gap(gap_id: str, body: GapUpdate, operator: str = Depends(require_operator)):
        try:
            return P().learning.update_gap(gap_id, resolution_status=body.resolution_status, note=body.note,
                                           actor=operator, linked_task_id=body.linked_task_id)
        except KnowledgeError as exc:
            raise _err(exc)

    @op.post("/gaps/{gap_id}/promote")
    def promote_gap(gap_id: str, body: EvalCaseIn, operator: str = Depends(require_operator)):
        platform = P()
        try:
            return platform.learning.promote_gap_to_eval(gap_id, body, actor=operator, evals=platform.evals)
        except KnowledgeError as exc:
            raise _err(exc)

    # ---------------- operator: evals ----------------
    @op.get("/evals")
    def evals(state: Optional[str] = Query(default=None, pattern=r"^(draft|approved|retired)$"),
              tag: Optional[str] = None):
        return {"cases": P().evals.list_cases(state=state, tag=tag)}

    @op.post("/evals")
    def create_eval(body: EvalCaseIn, operator: str = Depends(require_operator)):
        try:
            return P().evals.create_case(body, actor=operator, origin="operator")
        except KnowledgeError as exc:
            raise _err(exc)

    @op.post("/evals/{case_id}/state")
    def eval_state(case_id: str, body: EvalStateUpdate, operator: str = Depends(require_operator)):
        try:
            return P().evals.set_state(case_id, body.state, actor=operator, reason=body.reason)
        except KnowledgeError as exc:
            raise _err(exc)

    @op.post("/evals/run")
    def run_evals(body: EvalRunRequest):
        run = P().evals.run(selector=body.selector)
        for r in run["results"]:
            r.pop("observed", None) if r["passed"] else None
        return run

    @op.get("/audit")
    def audit(limit: int = Query(default=100, le=500)):
        return {"audit": P().repo.recent_audit(limit)}

    @op.get("/export")
    def export_all():
        return P().export_published()

    router.include_router(op)
    return router


__all__ = ["build_knowledge_router", "require_operator"]
