"""Waymaker answer endpoint: /api/ask.

Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).
The handler bodies are the original text; identifiers that resolve to module globals of
paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,
configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.
No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation
objects (``pb.X`` is a closure variable of the factory, not a module global).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.post(
        "/api/ask",
        # The response is AskResponse projected by _public_ask_payload (or the full
        # AskResponse in explicit diagnostics mode), so FastAPI must not re-validate
        # it against the internal model.
        response_model=None,
        # Per-client sliding-window limit (H-1a); covers stream AND buffered paths.
        dependencies=[Depends(pb.rate_limit("ask", per_minute=8, per_day=300))],
    )
    async def ask(req: pb.AskRequest, request: Request):
        diagnostics = pb._ask_diagnostics_requested(req, request)
        started = pb.time.monotonic()
        pb._KNOWLEDGE_PLAN_CTX.set(None)
        prompt_text = (req.message or req.query or req.question or "").strip()
        try:
            result = await pb._ask_internal(req)
        except HTTPException as exc:
            pb._record_knowledge_observation(prompt_text)
            detail = exc.detail if isinstance(exc.detail, dict) else None
            pb._log_ask_routing_telemetry(
                detail, req=req, status_code=exc.status_code,
                latency_ms=int((pb.time.monotonic() - started) * 1000),
            )
            if detail is not None and not diagnostics:
                raise HTTPException(
                    status_code=exc.status_code,
                    detail=pb._public_ask_payload(detail),
                    headers=getattr(exc, "headers", None),
                ) from None
            raise
        latency_ms = int((pb.time.monotonic() - started) * 1000)
        answer_ref = pb._record_knowledge_observation(prompt_text)
        if isinstance(result, StreamingResponse):
            pb._log_ask_routing_telemetry(
                {"answer_mode": req.answer_mode}, req=req, status_code=200,
                latency_ms=latency_ms, streamed=True,
            )
            if not diagnostics:
                result.body_iterator = pb._public_sse_stream(result.body_iterator)
            return result
        payload = result.model_dump() if isinstance(result, pb.BaseModel) else dict(result or {})
        if answer_ref:
            payload["answer_ref"] = answer_ref
        pb._log_ask_routing_telemetry(payload, req=req, status_code=200, latency_ms=latency_ms)
        return JSONResponse(payload if diagnostics else pb._public_ask_payload(payload))
    return router
