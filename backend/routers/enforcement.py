"""Enforcement disposition tools: /api/enforcement/*.

Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).
The handler bodies are the original text; identifiers that resolve to module globals of
paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,
configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.
No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation
objects (``pb.X`` is a closure variable of the factory, not a module global).
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.get(
        "/api/enforcement/provider-probe",
        dependencies=[Depends(pb.rate_limit("enforcement_provider_probe", per_minute=2, per_day=20))],
    )
    async def enforcement_provider_probe() -> Any:
        """Fixed synthetic probe. Accepts no case input and never returns model text."""
        if not pb.OPENROUTER_API_KEY:
            return {
                "service": "visable-enforcement-provider-probe",
                "diagnosticOnly": True,
                "configured": False,
                "ok": False,
                "providerErrorType": "provider_not_configured",
            }
        return await pb._run_enforcement_provider_probe()


    @router.post(
        "/api/enforcement/extract",
        dependencies=[Depends(pb.rate_limit("enforcement_extract", per_minute=10, per_day=200))],
    )
    async def enforcement_extract(req: pb.EnforcementExtractRequest) -> Any:
        """Convert a sensitive narrative into non-identifying structured facts."""
        if not (req.text or "").strip():
            raise HTTPException(status_code=422, detail="case text is required")
        provider = pb._enforcement_ai_provider if pb.OPENROUTER_API_KEY else None
        case = await pb.extract_structured_case(
            req.text,
            provider=provider,
            assessment_date=req.assessment_date,
        )
        return {"schemaVersion": "1", "case": case.public_dict()}


    @router.post(
        "/api/enforcement/analyze",
        dependencies=[Depends(pb.rate_limit("enforcement_analyze", per_minute=8, per_day=160))],
    )
    async def enforcement_analyze(req: pb.EnforcementAnalyzeRequest) -> Any:
        """Calculate the law first, then request a bounded outcome prediction."""
        try:
            case = pb.StructuredCase.model_validate(req.case_data)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid structured enforcement case") from exc
        provider = pb._enforcement_ai_provider if pb.OPENROUTER_API_KEY else None
        analysis = await pb.analyze_enforcement_case(case, prediction_provider=provider)
        return analysis.public_dict()
    return router
