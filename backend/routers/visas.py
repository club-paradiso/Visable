"""Static visa catalog and procedure packets: /api/visas*, /api/procedure-packet.

Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).
The handler bodies are the original text; identifiers that resolve to module globals of
paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,
configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.
No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation
objects (``pb.X`` is a closure variable of the factory, not a module global).
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.get("/api/visas")
    async def list_visas() -> Dict[str, Any]:
        """Return the visa catalog.

        Response shape preserves backwards-compatibility with frontend
        consumers that read either a bare array or `{data: [...]}`:

        - `data`: list of visa records (frontend's `parse()` reads this)
        - `visas`: same list under the explicit name used by newer code
        - `count`: convenience integer
        - `warning`: present only when DEFAULT_VISAS fallback is in use

        Records for statuses with source-confirmed (HIGH / STRUCTURED_EVIDENCE_READY)
        structured requirements carry an additive
        ``sourceConfirmedStructuredRequirements`` field; all other records are
        unchanged. Needs-review candidate evidence is never exposed here.
        """
        cached = pb._load_visas()
        visas = pb._enrich_with_source_confirmed_requirements(cached["visas"])
        payload: Dict[str, Any] = {
            "count": len(visas),
            "data": visas,
            "visas": visas,
            "source": cached.get("source", "unknown"),
            "source_type": cached.get("source_type", "unknown"),
        }
        if "warning" in cached:
            payload["warning"] = cached["warning"]
        return payload


    @router.get("/api/visas/{status_code}/structured-requirements")
    async def get_structured_requirements_endpoint(
        status_code: str, include_needs_review: bool = False
    ) -> Dict[str, Any]:
        """Return structured requirements for a status.

        Default: ONLY source-confirmed (HIGH / STRUCTURED_EVIDENCE_READY) entries,
        projected to the safe user-facing shape. ``include_needs_review=1`` is an
        INTERNAL/debug flag that returns raw candidate entries too — these must not
        be shown to end users.
        """
        if pb._structured_requirements is None:
            return {"statusCode": status_code, "sourceConfirmed": [], "available": False}
        confirmed = pb._structured_requirements.get_source_confirmed_structured_requirements(status_code)
        payload: Dict[str, Any] = {
            "statusCode": status_code,
            "available": True,
            "sourceConfirmedCount": len(confirmed),
            "sourceConfirmed": [pb._structured_requirements.public_summary(e) for e in confirmed],
        }
        if include_needs_review:
            all_entries = pb._structured_requirements.get_structured_requirements(
                status_code, {"includeNeedsReview": True}
            )
            needs_review = [e for e in all_entries if not pb._structured_requirements.is_source_confirmed(e)]
            payload["internalNeedsReviewCount"] = len(needs_review)
            payload["internalNeedsReview"] = needs_review
            payload["internalWarning"] = (
                "Entries under internalNeedsReview are unverified candidate evidence "
                "and must not be shown to end users."
            )
        return payload


    @router.get("/api/procedure-packet")
    async def get_procedure_packet_endpoint(
        status: str, procedure: str, locale: str = "ko"
    ) -> Dict[str, Any]:
        """Build a source-graded procedure preparation packet (deterministic).

        Inputs are non-personal only: ``status`` (a status/visa code, parent or
        exact sub-code) and ``procedure`` (a procedure key such as
        ``registration``/``extension``/``statusChange`` or a public packet type such
        as ``foreigner_registration``). No personal field values are accepted or
        stored, no LLM is called, and the output carries only public-safe source
        labels (never raw developer diagnostics). The packet's
        ``applicationTypingHelper`` is typing-guide-only and never holds values.
        """
        if pb._build_procedure_packet is None:
            raise HTTPException(
                status_code=503,
                detail={"error": "packet_builder_unavailable",
                        "message": "Procedure packet builder is not available."},
            )
        status_code = (status or "").strip()
        procedure_key = (procedure or "").strip()
        if not status_code or not procedure_key:
            raise HTTPException(
                status_code=400,
                detail={"error": "missing_parameters",
                        "message": "Provide non-empty 'status' and 'procedure'."},
            )
        packet = pb._build_procedure_packet(status_code, procedure_key, locale=locale or "ko")
        if packet.get("packetType") == "unknown":
            raise HTTPException(
                status_code=400,
                detail={"error": "unsupported_procedure",
                        "message": "요청한 절차 유형을 인식할 수 없습니다.",
                        "supportedPacketTypes": list(pb._SUPPORTED_PACKET_TYPES)},
            )
        return packet


    @router.get("/api/visas/{status_code}/packets")
    async def get_available_packets_endpoint(
        status_code: str, locale: str = "ko"
    ) -> Dict[str, Any]:
        """List preparation packets buildable for a status (deterministic, no LLM)."""
        if pb._build_available_packets_for_status is None:
            return {"statusCode": status_code, "available": False, "packets": []}
        summaries = pb._build_available_packets_for_status(status_code, locale=locale or "ko")
        return {
            "statusCode": status_code,
            "available": bool(summaries),
            "packetCount": len(summaries),
            "packets": summaries,
        }
    return router
