"""Employment interpretation: /api/employment/interpret.

Moved from backend/paradiso_backend.py in Phase 6 of the rebuild (docs/rebuild/DECISIONS.md ADR-013).
The handler bodies are the original text; identifiers that resolve to module globals of
paradiso_backend are qualified as ``pb.<name>`` so the facade stays the single owner of state,
configuration and helpers, and tests that monkeypatch ``paradiso_backend.<name>`` keep working.
No ``from __future__ import annotations`` here on purpose: FastAPI must see the real annotation
objects (``pb.X`` is a closure variable of the factory, not a module global).
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.post(
        "/api/employment/interpret",
        dependencies=[Depends(pb.rate_limit("employment_interpret", per_minute=12, per_day=300))],
    )
    async def employment_interpret(req: pb.EmploymentInterpretRequest) -> Any:
        """Extract structured job facts from free text for the 취업정보 신고 helper.

        This endpoint NEVER returns a KSCO8 직종 code or a KSIC11 업종 code and never
        decides whether reporting is required. It returns validated *facts* which the
        frontend feeds into the existing deterministic analyzer — the only component
        that may produce a code, because it retrieves codes from the official tables.

        Anything the model emits outside the fixed schema is dropped, and every
        removal is reported in ``warnings`` so the sanitization is auditable.
        """
        text = (req.text or "").strip()[:600]
        lang = "en" if str(req.lang or "ko").lower().startswith("en") else "ko"

        if not text:
            return {"status": "empty_input", "extraction": pb._employment_nl.empty_extraction(),
                    "analyzerInput": None, "interpretation": "", "warnings": []}

        if not any(pb._providers_configured().values()):
            # The guided/deterministic flow in the UI is unaffected; only the
            # free-sentence convenience layer is unavailable.
            return {
                "status": "unavailable",
                "reason": "no_provider_configured",
                "extraction": pb._employment_nl.empty_extraction(),
                "analyzerInput": {"text": text, "locale": "", "visaStatus": "", "employmentType": ""},
                "interpretation": "",
                "warnings": [],
                "fallbackAvailable": True,
            }

        prompt = pb._employment_nl.build_extraction_prompt(text, lang=lang)

        def _interpret_unavailable(reason: str) -> Dict[str, Any]:
            # The deterministic analyzer is the fallback, so the raw sentence still
            # reaches it: this layer is a convenience, never a gate.
            return {
                "status": "unavailable",
                "reason": reason,
                "extraction": pb._employment_nl.empty_extraction(),
                "analyzerInput": {"text": text, "locale": "", "visaStatus": "", "employmentType": ""},
                "interpretation": "",
                "warnings": [],
                "fallbackAvailable": True,
            }

        # Same defect as the AI Overview endpoint: the helper returns a RESULT DICT,
        # not a (text, meta) tuple, so this unpack raised ValueError on every call
        # and the bare ``except Exception`` reported a provider failure that had not
        # happened. Employment interpretation never once ran in production.
        try:
            attempt_meta = await pb._openrouter_complete_with_candidates(prompt)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            reason, _retryable = pb._classify_openrouter_error(
                detail.get("status", exc.status_code), detail.get("message"), detail.get("error")
            )
            return _interpret_unavailable(reason)
        except Exception:
            return _interpret_unavailable("provider_error")

        if not attempt_meta.get("ok") or not (attempt_meta.get("answer") or "").strip():
            return _interpret_unavailable(
                str(attempt_meta.get("provider_error_type") or "provider_error")
            )
        raw = attempt_meta["answer"]

        try:
            known_codes = {
                str(r.get("code")).strip().upper()
                for r in (pb._load_visas().get("visas") or [])
                if isinstance(r, dict) and r.get("code")
            }
        except Exception:
            known_codes = set()

        validated = pb._employment_nl.validate_extraction(raw, allowed_visa_codes=known_codes or None)
        if not validated["ok"]:
            return {
                "status": "extraction_failed",
                "reason": validated["reason"],
                "extraction": validated["data"],
                "analyzerInput": {"text": text, "locale": "", "visaStatus": "", "employmentType": ""},
                "interpretation": "",
                "warnings": validated["warnings"],
                "fallbackAvailable": True,
            }

        data = validated["data"]
        return {
            "status": "ok",
            "extraction": data,
            "analyzerInput": pb._employment_nl.to_analyzer_input(data, original_text=text),
            "interpretation": pb._employment_nl.build_interpretation_sentence(data, lang=lang),
            "needsClarification": bool(data.get("needsClarification")),
            "clarificationQuestion": data.get("clarificationQuestion", ""),
            "warnings": validated["warnings"],
            "fallbackAvailable": True,
            "provider": "openrouter",
            "model": attempt_meta.get("final_model") or "",
            "notice": ("직종·업종 코드는 이 단계에서 만들지 않습니다. 아래 후보는 공식 분류표에서 "
                       "검색한 결과이며, 최종 확정은 하이코리아에서 확인하세요."
                       if lang == "ko" else
                       "No classification code is produced at this step. Candidates below are "
                       "retrieved from the official tables; confirm the final code with HiKorea."),
        }
    return router
