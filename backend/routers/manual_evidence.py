"""Manual evidence state: /api/search/manual-evidence-state.

Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).
The handler bodies are the original text; identifiers that resolve to module globals of
paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,
configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.
No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation
objects (``pb.X`` is a closure variable of the factory, not a module global).
"""

from typing import Any, Dict
from fastapi import APIRouter


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.get("/api/search/manual-evidence-state")
    async def manual_evidence_state_endpoint() -> Dict[str, Any]:
        """Operator-safe snapshot of the manual approval layer. No secrets, no bodies."""
        summary = pb._manual_registry.registry_summary()
        return {
            "registryVersion": summary["registry_version"],
            "documentCount": summary["document_count"],
            "familyCount": summary["family_count"],
            "approvalCounts": summary["approval_counts"],
            "indexAvailable": pb._manual_search.index_available(),
            "note": "Only approval_state='approved' content may back a direct assertion.",
        }
    return router
