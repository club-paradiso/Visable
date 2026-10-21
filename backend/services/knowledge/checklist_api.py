"""VISABLE Content Operations Studio — FastAPI Router.

Provides authenticated REST endpoints under /api/knowledge/studio/checklists/
with server-side Role-Based Access Control (RBAC).
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .api import require_operator
from .checklist_models import (
    DashboardMetricsOut,
    DraftActionIn,
    DraftCreateIn,
    OfficeOverrideIn,
    OperatorRole,
    PublishValidationReport,
    ReleaseRequestIn,
    RollbackRequestIn,
    ScenarioDiffOut,
)
from .checklist_repository import (
    act_on_draft,
    bootstrap_checklist_items,
    compute_draft_diff,
    create_or_update_draft,
    execute_publish_release,
    execute_rollback_release,
    get_active_published_checklists,
    get_dashboard_metrics,
    get_operator_role,
    get_release_preview,
    get_scenario_detail,
    list_offices_status,
    list_releases,
    list_scenarios,
    run_prepublish_validation,
    save_office_override,
)
from .models import KnowledgeError, PipelineError

logger = logging.getLogger("visable.checklists.api")


def _err(exc: KnowledgeError) -> HTTPException:
    status = {
        PipelineError.NOT_FOUND: 404,
        PipelineError.CONFLICT_DETECTED: 409,
        PipelineError.DUPLICATE_FACT: 409,
        PipelineError.TRANSITION_FORBIDDEN: 403,
        PipelineError.REVIEW_REQUIRED: 422,
    }.get(exc.code, 422)
    return HTTPException(status_code=status, detail=exc.to_dict())


def build_checklist_router(get_store: Callable[[], Any]) -> APIRouter:
    """Builds the authenticated Content Operations Studio router."""
    router = APIRouter(prefix="/api/knowledge/studio/checklists")

    def S():
        store = get_store()
        # Ensure bootstrap has run
        bootstrap_checklist_items(store)
        return store

    def require_role(request: Request) -> Tuple[str, OperatorRole]:
        operator = require_operator(request)
        store = S()
        role = get_operator_role(store, operator)
        return operator, role

    # -----------------------------------------------------------------------
    # Auth & Current Session Info
    # -----------------------------------------------------------------------
    @router.get("/auth/me")
    def auth_me(user: Tuple[str, OperatorRole] = Depends(require_role)) -> Dict[str, Any]:
        operator, role = user
        return {"operator": operator, "role": role.value}

    # -----------------------------------------------------------------------
    # Dashboard
    # -----------------------------------------------------------------------
    @router.get("/dashboard")
    def dashboard(user: Tuple[str, OperatorRole] = Depends(require_role)) -> DashboardMetricsOut:
        store = S()
        return get_dashboard_metrics(store)

    # -----------------------------------------------------------------------
    # Scenarios (Visa & Procedure Navigation)
    # -----------------------------------------------------------------------
    @router.get("/scenarios")
    def get_scenarios(
        procedure: Optional[str] = Query(default=None, max_length=20),
        status_code: Optional[str] = Query(default=None, max_length=20),
        query: Optional[str] = Query(default=None, max_length=100),
        review_state: Optional[str] = Query(default=None, max_length=40),
        limit: int = Query(default=50, le=200),
        offset: int = Query(default=0, ge=0),
        user: Tuple[str, OperatorRole] = Depends(require_role),
    ) -> Dict[str, Any]:
        store = S()
        items, total = list_scenarios(
            store,
            procedure=procedure,
            status_code=status_code,
            query=query,
            review_state=review_state,
            limit=limit,
            offset=offset,
        )
        return {"scenarios": [it.model_dump() for it in items], "total": total}

    @router.get("/scenarios/{item_id}")
    def scenario_detail(item_id: str, user: Tuple[str, OperatorRole] = Depends(require_role)) -> Dict[str, Any]:
        store = S()
        try:
            return get_scenario_detail(store, item_id)
        except KnowledgeError as exc:
            raise _err(exc)

    # -----------------------------------------------------------------------
    # Draft Proposals & Review Lifecycle
    # -----------------------------------------------------------------------
    @router.post("/drafts")
    def create_draft(body: DraftCreateIn, user: Tuple[str, OperatorRole] = Depends(require_role)) -> Dict[str, Any]:
        operator, role = user
        store = S()
        try:
            return create_or_update_draft(store, body, actor=operator, actor_role=role)
        except KnowledgeError as exc:
            raise _err(exc)

    @router.post("/drafts/{draft_id}/action")
    def draft_action(
        draft_id: str, body: DraftActionIn, user: Tuple[str, OperatorRole] = Depends(require_role)
    ) -> Dict[str, Any]:
        operator, role = user
        store = S()
        try:
            return act_on_draft(store, draft_id, body, actor=operator, actor_role=role)
        except KnowledgeError as exc:
            raise _err(exc)

    # -----------------------------------------------------------------------
    # Visual Diff & Version History
    # -----------------------------------------------------------------------
    @router.get("/diff/{draft_id}")
    def get_diff(draft_id: str, user: Tuple[str, OperatorRole] = Depends(require_role)) -> ScenarioDiffOut:
        store = S()
        try:
            return compute_draft_diff(store, draft_id)
        except KnowledgeError as exc:
            raise _err(exc)

    # -----------------------------------------------------------------------
    # Office Overrides (26 Immigration Offices)
    # -----------------------------------------------------------------------
    @router.get("/offices")
    def get_offices(user: Tuple[str, OperatorRole] = Depends(require_role)) -> Dict[str, Any]:
        store = S()
        return list_offices_status(store)

    @router.post("/offices/overrides")
    def create_office_override(
        body: OfficeOverrideIn, user: Tuple[str, OperatorRole] = Depends(require_role)
    ) -> Dict[str, Any]:
        operator, role = user
        store = S()
        try:
            return save_office_override(store, body, actor=operator, actor_role=role)
        except KnowledgeError as exc:
            raise _err(exc)

    # -----------------------------------------------------------------------
    # Pre-publish Validation Gate & Safe Release
    # -----------------------------------------------------------------------
    @router.post("/publish/validate")
    def validate_publish(user: Tuple[str, OperatorRole] = Depends(require_role)) -> PublishValidationReport:
        store = S()
        return run_prepublish_validation(store)

    @router.post("/publish/release")
    def release_publish(
        body: ReleaseRequestIn, user: Tuple[str, OperatorRole] = Depends(require_role)
    ) -> Dict[str, Any]:
        operator, role = user
        store = S()
        try:
            return execute_publish_release(
                store, release_in=body, actor=operator, actor_role=role
            )
        except KnowledgeError as exc:
            raise _err(exc)

    # -----------------------------------------------------------------------
    # Release Management & Rollback
    # -----------------------------------------------------------------------
    @router.get("/releases")
    def get_releases_list(user: Tuple[str, OperatorRole] = Depends(require_role)) -> Dict[str, Any]:
        store = S()
        return {"releases": list_releases(store)}

    @router.get("/releases/{release_id}/preview")
    def get_release_preview_endpoint(
        release_id: str, user: Tuple[str, OperatorRole] = Depends(require_role)
    ) -> Dict[str, Any]:
        store = S()
        try:
            return get_release_preview(store, release_id)
        except KnowledgeError as exc:
            raise _err(exc)

    @router.post("/releases/{release_id}/rollback")
    def rollback_release_endpoint(
        release_id: str, body: RollbackRequestIn, user: Tuple[str, OperatorRole] = Depends(require_role)
    ) -> Dict[str, Any]:
        operator, role = user
        store = S()
        try:
            return execute_rollback_release(store, release_id, rollback_in=body, actor=operator, actor_role=role)
        except KnowledgeError as exc:
            raise _err(exc)

    return router


def build_public_checklist_router(get_store: Callable[[], Any]) -> APIRouter:
    """Public read-only endpoints for published checklist data and preview."""
    router = APIRouter(prefix="/api/checklists")

    def S():
        store = get_store()
        bootstrap_checklist_items(store)
        return store

    @router.get("/published")
    def published_checklists(procedure: Optional[str] = Query(default=None)) -> Dict[str, Any]:
        store = S()
        return get_active_published_checklists(store, procedure=procedure)

    @router.get("/preview")
    def preview_checklists(release_id: str = Query(..., min_length=1)) -> Dict[str, Any]:
        store = S()
        try:
            return get_release_preview(store, release_id)
        except KnowledgeError as exc:
            raise _err(exc)

    return router


__all__ = ["build_checklist_router", "build_public_checklist_router"]

