"""PreView MOFA public-data proxy: /api/preview/mission.

Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).
The handler bodies are the original text; identifiers that resolve to module globals of
paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,
configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.
No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation
objects (``pb.X`` is a closure variable of the factory, not a module global).
"""

from typing import Any
from fastapi import APIRouter, Depends


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.get(
        "/api/preview/mission",
        dependencies=[Depends(pb.rate_limit("preview_mission", per_minute=20))],
    )
    def preview_mission(country: str = "", countryName: str = "") -> Any:
        """Pre-arrival mission lookup for PreView (외교부_국가·지역별 재외공관 정보).

        Read-only proxy: validates the query, resolves the portal service key
        (MOFA_EMBASSY_SERVICE_KEY -> PUBLIC_DATA_SERVICE_KEY), and returns a safe
        envelope in every case. The frontend falls back to labeled MVP sample
        data whenever ``ok`` is false or ``items`` is empty.

        Deliberately a sync route: the upstream call uses a blocking httpx
        client, so FastAPI must run it in the threadpool instead of stalling
        the event loop while data.go.kr responds.
        """
        outcome = pb.mofa_public_data.fetch_mission_directory(
            country_iso2=country or None,
            country_name=countryName or None,
        )
        if outcome.get("error") == "invalid_query":
            return pb.UTF8JSONResponse(status_code=400, content=outcome)
        return outcome
    return router
