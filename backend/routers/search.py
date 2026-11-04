"""Unified search and AI overview: /api/search/unified*.

Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).
The handler bodies are the original text; identifiers that resolve to module globals of
paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,
configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.
No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation
objects (``pb.X`` is a closure variable of the factory, not a module global).
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.post(
        "/api/search/unified",
        dependencies=[Depends(pb.rate_limit("search_unified", per_minute=60, per_day=2000))],
    )
    async def search_unified(req: pb.UnifiedSearchRequest) -> Any:
        """Deterministic unified search. Local data only — no LLM, no outbound HTTP.

        Returns the organic result set, the detected intent, and an editable
        interpretation. ``aiOverview`` is always ``null`` here and
        ``aiOverviewStatus`` is ``pending``: the overview is fetched separately by
        ``/api/search/unified/ai-overview`` so rendering never waits on it.
        """
        started = pb.time.monotonic()
        request_id = pb.uuid.uuid4().hex[:16]
        query = (req.query or "").strip()[:pb._UNIFIED_SEARCH_MAX_QUERY]

        cached = pb._load_visas()
        visa_data = cached.get("visas") or []

        manual_search_fn = pb._unified_manual_search if (req.includeManualEvidence is not False) else None
        result = pb._unified_search.run_unified_search(
            query,
            visa_data=visa_data,
            valid_main_codes=set(pb._VALID_MAIN_CODES),
            manual_search=manual_search_fn,
            limit=max(1, min(int(req.limit or 10), 20)),
        )

        elapsed_ms = int((pb.time.monotonic() - started) * 1000)
        result.update({
            "requestId": request_id,
            "aiOverview": None,
            "aiOverviewStatus": "pending" if query else "not_applicable",
            "sourceCards": pb._unified_source_cards(result),
            "latency": {"deterministicMs": elapsed_ms},
            "version": pb._unified_search.UNIFIED_SEARCH_VERSION,
        })
        return result


    @router.post(
        "/api/search/unified/ai-overview",
        dependencies=[Depends(pb.rate_limit("search_unified_ai", per_minute=10, per_day=200))],
    )
    async def search_unified_ai_overview(req: pb.UnifiedAiOverviewRequest) -> Any:
        """AI Overview for a unified search result. Optional by construction.

        Failure is a first-class, *quiet* outcome: a provider outage returns
        ``status="unavailable"`` with a friendly reason and no answer text, so the
        frontend hides the overview card and leaves the organic results untouched.

        The model is never allowed to introduce a statute, article, case number or
        visa code that is not already grounded — anything it emits is put through the
        statute-citation guard against the retrieved evidence before it is returned.
        """
        started = pb.time.monotonic()
        request_id = pb.uuid.uuid4().hex[:16]
        query = (req.query or "").strip()[:pb._UNIFIED_SEARCH_MAX_QUERY]
        lang = "en" if str(req.lang or "ko").lower().startswith("en") else "ko"

        if not query:
            return {"status": "not_applicable", "requestId": request_id,
                    "overview": None, "citationVerification": None}

        providers = pb._providers_configured()
        if not any(providers.values()):
            return {
                "status": "unavailable",
                "reason": "no_provider_configured",
                "requestId": request_id,
                "overview": None,
                "fallbackAvailable": True,
                "message": ("AI 요약을 사용할 수 없습니다. 아래 검색 결과와 공식 출처를 확인하세요."
                            if lang == "ko" else
                            "The AI overview is unavailable. Please use the search results "
                            "and official sources below."),
            }

        cached = pb._load_visas()
        visa_data = cached.get("visas") or []
        deterministic = pb._unified_search.run_unified_search(
            query, visa_data=visa_data, valid_main_codes=set(pb._VALID_MAIN_CODES),
            manual_search=pb._unified_manual_search, limit=8,
        )

        # Evidence the model is allowed to speak from. Anything outside this set is a
        # citation failure by definition.
        evidence_lines: List[str] = []
        for card in deterministic.get("organicResults", []):
            if card.get("code"):
                evidence_lines.append(
                    f"- [{card['code']}] {card.get('title', '')}: {card.get('summary', '')[:180]}")
        manual_state = (deterministic.get("manualEvidence") or {}).get("status", "not_queried")

        if not evidence_lines:
            # `blocked` in the design vocabulary: no summary was produced, and the
            # reason is stated rather than left as an empty card.
            return {
                "status": "blocked",
                "reason": ("검색된 근거 0건" if lang == "ko" else "no grounded evidence"),
                "requestId": request_id,
                "overview": None,
                "fallbackAvailable": True,
                "message": ("검색된 근거가 없어 요약을 만들지 않았습니다. 검색어를 바꾸거나 "
                            "공식 출처에서 확인해 주세요." if lang == "ko" else
                            "No grounded evidence was retrieved, so no overview was generated."),
            }

        prompt = pb._unified_overview_prompt(query, deterministic, evidence_lines, lang)

        def _overview_unavailable(reason: str) -> Dict[str, Any]:
            return {
                "status": "unavailable",
                "reason": reason,
                "requestId": request_id,
                "overview": None,
                "fallbackAvailable": True,
                "message": ("AI 요약을 불러오지 못했습니다. 아래 검색 결과는 정상입니다."
                            if lang == "ko" else
                            "The AI overview could not be loaded. The search results below "
                            "are unaffected."),
            }

        # ``_openrouter_complete_with_candidates`` returns a RESULT DICT, never a
        # (text, meta) tuple. Unpacking it into two names raised ValueError on every
        # call, which the bare ``except Exception`` below swallowed into
        # ``provider_error`` — so this endpoint reported "unavailable" even when the
        # provider answered correctly. Read the documented keys instead.
        try:
            attempt_meta = await pb._openrouter_complete_with_candidates(prompt)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            reason, _retryable = pb._classify_openrouter_error(
                detail.get("status", exc.status_code), detail.get("message"), detail.get("error")
            )
            return _overview_unavailable(reason)
        except Exception:
            return _overview_unavailable("provider_error")

        if not attempt_meta.get("ok") or not (attempt_meta.get("answer") or "").strip():
            # Every candidate failed (or all are cooling down). This is the same
            # quiet, organic-results-preserving outcome as a transport failure, but
            # the classified provider reason is reported rather than a generic one.
            return _overview_unavailable(
                str(attempt_meta.get("provider_error_type") or "provider_error")
            )
        text = attempt_meta["answer"]

        # Citation guard: the overview is grounded in visa-data cards, not in fetched
        # statute text, so ANY statute citation it emits is unverifiable here and is
        # marked as such rather than rendered as a confirmed reference.
        verification = pb._statute_guard.verify_statute_citations(text, [], evidence_available=False)
        safe_text = pb._statute_guard.strip_failed_statute_citations(text, verification)

        elapsed_ms = int((pb.time.monotonic() - started) * 1000)
        return {
            "status": "ok",
            "requestId": request_id,
            "overview": safe_text,
            "citationVerification": {
                "status": verification["status"],
                "unverifiableCount": verification["unverifiable_count"],
                "failureCount": verification["failure_count"],
            },
            "evidenceState": {
                "manual": manual_state,
                "directEvidenceCount": len(evidence_lines),
                "law": "not_queried",
            },
            "sources": pb._unified_overview_sources(deterministic),
            "evidenceLabel": pb._unified_evidence_label(deterministic, lang),
            "requiresOfficialConfirmation": True,
            # The result dict names the model that actually answered ``final_model``;
            # there is no "model"/"provider" key on it. Reading the wrong names made
            # both fields silently blank in every successful response.
            "provider": "openrouter",
            "model": attempt_meta.get("final_model") or "",
            "modelFallbackUsed": bool(attempt_meta.get("model_fallback_used")),
            "fallbackAvailable": True,
            "latency": {"totalMs": elapsed_ms},
        }


    @router.post(
        "/api/search/unified/ai-overview/stream",
        dependencies=[Depends(pb.rate_limit("search_unified_ai", per_minute=10, per_day=200))],
    )
    async def search_unified_ai_overview_stream(req: pb.UnifiedAiOverviewRequest) -> Any:
        """SSE variant of the AI Overview — emits `streaming` deltas, then `done`.

        Exists so the design's `Streaming` state (Figma UX-03, node 406:92) is a real
        state and not decoration: without a producer the frontend could render it but
        nothing would ever trigger it.

        The citation guard runs on the ACCUMULATED text at the end, never per delta —
        a half-written statute reference would otherwise be judged incomplete and
        wrongly flagged. Until `done` arrives the client shows the text as provisional.
        """
        query = (req.query or "").strip()[:pb._UNIFIED_SEARCH_MAX_QUERY]
        lang = "en" if str(req.lang or "ko").lower().startswith("en") else "ko"
        request_id = pb.uuid.uuid4().hex[:16]

        async def event_stream():
            if not query:
                yield pb._sse("done", {"status": "not_applicable", "requestId": request_id})
                return
            if not pb._providers_configured().get("openrouter"):
                # Non-streaming providers cannot satisfy this endpoint; the client
                # falls back to the buffered endpoint rather than showing nothing.
                yield pb._sse("done", {
                    "status": "unavailable", "reason": "streaming_not_available",
                    "requestId": request_id, "fallbackAvailable": True,
                    "message": ("실시간 요약을 사용할 수 없습니다. 일반 요약으로 대체합니다."
                                if lang == "ko" else
                                "Live summary is unavailable; falling back to the buffered summary."),
                })
                return

            cached = pb._load_visas()
            deterministic = pb._unified_search.run_unified_search(
                query, visa_data=cached.get("visas") or [],
                valid_main_codes=set(pb._VALID_MAIN_CODES),
                manual_search=pb._unified_manual_search, limit=8,
            )
            evidence_lines = [
                f"- [{c['code']}] {c.get('title', '')}: {c.get('summary', '')[:180]}"
                for c in deterministic.get("organicResults", []) if c.get("code")
            ]
            if not evidence_lines:
                yield pb._sse("done", {
                    "status": "blocked",
                    "reason": ("검색된 근거 0건" if lang == "ko" else "no grounded evidence"),
                    "requestId": request_id, "fallbackAvailable": True,
                })
                return

            prompt = pb._unified_overview_prompt(query, deterministic, evidence_lines, lang)
            yield pb._sse("start", {"status": "streaming", "requestId": request_id})

            accumulated = ""
            try:
                candidates = pb._resolve_openrouter_candidates()
                model = candidates[0] if candidates else pb.OPENROUTER_MODEL
                async for delta in pb._stream_openrouter_text(prompt, model):
                    if not delta:
                        continue
                    accumulated += delta
                    yield pb._sse("delta", {"text": delta})
            except Exception:
                yield pb._sse("done", {
                    "status": "unavailable", "reason": "provider_error",
                    "requestId": request_id, "fallbackAvailable": True,
                    "message": ("AI 요약을 불러오지 못했습니다. 아래 검색 결과는 정상입니다."
                                if lang == "ko" else
                                "The AI overview could not be loaded."),
                })
                return

            verification = pb._statute_guard.verify_statute_citations(
                accumulated, [], evidence_available=False)
            safe_text = pb._statute_guard.strip_failed_statute_citations(accumulated, verification)
            yield pb._sse("done", {
                "status": "ok",
                "requestId": request_id,
                "overview": safe_text,
                "citationVerification": {
                    "status": verification["status"],
                    "unverifiableCount": verification["unverifiable_count"],
                    "failureCount": verification["failure_count"],
                },
                "evidenceState": {
                    "manual": (deterministic.get("manualEvidence") or {}).get("status", "not_queried"),
                    "directEvidenceCount": len(evidence_lines),
                    "law": "not_queried",
                },
                "sources": pb._unified_overview_sources(deterministic),
                "evidenceLabel": pb._unified_evidence_label(deterministic, lang),
                "requiresOfficialConfirmation": True,
                "fallbackAvailable": True,
            })

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return router
