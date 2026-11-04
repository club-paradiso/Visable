"""Employment code keyword extraction: /api/jobcodekeywords.

Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).
The handler bodies are the original text; identifiers that resolve to module globals of
paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,
configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.
No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation
objects (``pb.X`` is a closure variable of the factory, not a module global).
"""

from fastapi import APIRouter


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.post("/api/jobcodekeywords", response_model=pb.JobCodeKeywordsResponse)
    async def job_code_keywords(req: pb.JobCodeKeywordsRequest) -> pb.JobCodeKeywordsResponse:
        keywords = pb._extract_keywords(req.query)
        return pb.JobCodeKeywordsResponse(query=req.query, keywords=keywords)
    return router
