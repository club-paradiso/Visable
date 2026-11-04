"""Public legal source search and research: /api/legal/*.

Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).
The handler bodies are the original text; identifiers that resolve to module globals of
paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,
configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.
No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation
objects (``pb.X`` is a closure variable of the factory, not a module global).
"""

from typing import Any
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.get("/api/legal/laws/search")
    async def legal_laws_search(q: str = "") -> Any:
        """Search immigration-related statutes / decrees / rules on the Open Law API.

        Read-only proxy. Returns ``{ok, kind, query, count, results}`` (results are
        LegalLawResult objects) or a safe ``{ok:false, error}`` envelope. The OC
        credential is never exposed; upstream URLs are OC-redacted by the adapter.
        """
        cfg = pb.load_grounding_config()
        if not cfg.law_api_configured:
            return pb._legal_not_configured_response()
        query = pb._legal_search_clean_query(q)
        if not query:
            return pb.UTF8JSONResponse(status_code=400, content={"ok": False, "error": "empty_query", "results": []})
        outcome = pb.search_laws(query, limit=pb._LEGAL_SEARCH_MAX_RESULTS, config=cfg)
        if outcome.get("status") != "ok":
            error_type = outcome.get("error_type") or "search_failed"
            if error_type == "law_api_not_configured":
                return pb._legal_not_configured_response()
            if error_type == "law_api_no_results":
                return {"ok": True, "kind": "laws", "query": query, "count": 0, "results": [], "rawSource": "law.go.kr"}
            return pb.UTF8JSONResponse(
                content={"ok": False, "error": "search_failed", "reason": error_type, "query": query, "results": []},
            )
        results = [pb._map_law_result(r) for r in (outcome.get("results") or []) if isinstance(r, dict)]
        return {"ok": True, "kind": "laws", "query": query, "count": len(results), "results": results, "rawSource": "law.go.kr"}


    @router.get("/api/legal/precedents/search")
    async def legal_precedents_search(q: str = "") -> Any:
        """Search court precedent (판례) on the Open Law API (``target=prec``).

        Read-only list search. Returns ``{ok, kind, query, count, results}``
        (LegalPrecedentResult objects) or a safe ``{ok:false, error}`` envelope.
        Body/detail lookup is deferred to the official source link by design.
        """
        cfg = pb.load_grounding_config()
        if not cfg.law_api_configured:
            return pb._legal_not_configured_response()
        query = pb._legal_search_clean_query(q)
        if not query:
            return pb.UTF8JSONResponse(status_code=400, content={"ok": False, "error": "empty_query", "results": []})
        env = pb.precedent_sources.search_precedents(query, limit=pb._LEGAL_SEARCH_MAX_RESULTS, config=cfg)
        status = env.get("status")
        if status == "not_configured":
            return pb._legal_not_configured_response()
        if status == "results_found":
            items = pb.precedent_sources.dedupe_precedent_items(env.get("items") or [])
            results = [
                pb._map_precedent_item(it, query)
                for it in items
                if isinstance(it, dict) and it.get("publicStatus") != "unavailable"
            ]
            return {"ok": True, "kind": "precedents", "query": query, "count": len(results), "results": results, "rawSource": "law.go.kr"}
        if status == "no_results":
            return {"ok": True, "kind": "precedents", "query": query, "count": 0, "results": [], "rawSource": "law.go.kr"}
        # http_error / timeout / bad_response / official_error → graceful, no crash.
        return pb.UTF8JSONResponse(
            content={"ok": False, "error": "search_failed",
                     "reason": env.get("errorType") or status or "unknown", "query": query, "results": []},
        )


    @router.get("/api/legal/precedents/detail")
    async def legal_precedent_detail(id: str = "") -> Any:
        """Return bounded official precedent body fields for one stable source ID."""
        cfg = pb.load_grounding_config()
        if not cfg.law_api_configured:
            return pb._legal_not_configured_response()
        source_id = pb.re.sub(r"[^A-Za-z0-9_-]", "", str(id or ""))[:80]
        if not source_id:
            return pb.UTF8JSONResponse(status_code=400, content={"ok": False, "error": "empty_id", "results": []})
        env = pb.precedent_sources.get_precedent_detail(source_id, config=cfg)
        if env.get("status") == "results_found":
            items = [
                pb._map_precedent_item(item, source_id)
                for item in (env.get("items") or [])
                if isinstance(item, dict) and item.get("resultKind") == "body_result"
            ]
            if items:
                return {"ok": True, "kind": "precedent_detail", "id": source_id, "count": len(items), "results": items, "rawSource": "law.go.kr"}
        if env.get("status") == "no_results":
            return {"ok": True, "kind": "precedent_detail", "id": source_id, "count": 0, "results": [], "rawSource": "law.go.kr"}
        return pb.UTF8JSONResponse(content={
            "ok": False,
            "error": "detail_failed",
            "reason": env.get("errorType") or env.get("status") or "unknown",
            "id": source_id,
            "results": [],
        })


    @router.post(
        "/api/legal/research",
        dependencies=[Depends(pb.rate_limit("legal_research", per_minute=4, per_day=60))],
    )
    async def legal_research_endpoint(req: pb.LegalResearchRequest) -> Any:
        """Deterministic, source-grounded legal research scaffold (no LLM).

        Plans retrieval by research depth (fast / basic / pro), runs the budgeted
        law/precedent searches via the OC-safe adapters, and returns a depth-
        structured result: issues to verify, source-strength-labelled cards (grouped
        by source type in pro), risk flags, missing facts, next checks, limitations,
        and a disclaimer. It never fabricates citations, never states a legal
        conclusion, and never infers facts the user did not provide.
        """
        question = (req.question or "").strip()[:pb._LEGAL_RESEARCH_MAX_QUESTION]
        if not question:
            return pb.UTF8JSONResponse(status_code=400, content={"ok": False, "error": "empty_question"})

        result = None
        async for _rec in pb._legal_research_pipeline(req, question):
            if isinstance(_rec, dict) and "__result__" in _rec:
                result = _rec["__result__"]
        return result


    @router.post(
        "/api/legal/research/stream",
        dependencies=[Depends(pb.rate_limit("legal_research", per_minute=4, per_day=60))],
    )
    async def legal_research_stream_endpoint(req: pb.LegalResearchRequest) -> Any:
        """The same research run as /api/legal/research, reported as it happens.

        Frames: ``start`` -> ``step`` per stage -> ``done`` with the identical
        payload the buffered endpoint returns. Both drain
        `_legal_research_pipeline`, so the two cannot answer the same question
        differently.

        ``status`` separates ``done`` (sources found), ``no_results`` (the search
        ran cleanly), ``failed`` (upstream/parse failure), ``skipped`` (the caller
        turned it off), and ``unavailable`` (the law API is not configured) —
        because "found nothing", "search failed", and "never ran" are different
        claims about our coverage.
        """
        question = (req.question or "").strip()[:pb._LEGAL_RESEARCH_MAX_QUESTION]
        if not question:
            return pb.UTF8JSONResponse(status_code=400, content={"ok": False, "error": "empty_question"})

        async def _gen():
            yield pb._sse("start", {"status": "running", "total": len(pb.LEGAL_RESEARCH_STEPS),
                                 "steps": list(pb.LEGAL_RESEARCH_STEPS)})
            result = None
            try:
                async for rec in pb._legal_research_pipeline(req, question):
                    if isinstance(rec, dict) and "__result__" in rec:
                        result = rec["__result__"]
                    else:
                        yield pb._sse("step", rec)
            except Exception:
                # The buffered endpoint stays available, so report the failure
                # rather than leaving the client on a spinner forever.
                yield pb._sse("done", {"ok": False, "error": "search_failed",
                                    "reason": "pipeline_error"})
                return
            yield pb._sse("done", result if result is not None
                       else {"ok": False, "error": "search_failed", "reason": "no_result"})

        return StreamingResponse(
            _gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return router
