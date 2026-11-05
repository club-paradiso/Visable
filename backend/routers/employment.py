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
from services.model_policy import EMPLOYMENT_GROQ_FREE_MODEL


def build_router(pb) -> APIRouter:
    """Routes of this group, registered in their original order. ``pb`` is the paradiso_backend module."""
    router = APIRouter()

    @router.post(
        "/api/employment/interpret",
        dependencies=[Depends(pb.rate_limit("employment_interpret", per_minute=8, per_day=120))],
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

        # Employment extraction is Groq-only, independent from OpenRouter's
        # global provider routing. A missing Groq key must NEVER silently use
        # OpenRouter or another potentially billable hosted provider.
        if not pb.GROQ_API_KEY:
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

        # Only send a short, identifier-redacted job description to Groq.
        # The raw input remains local for the deterministic KSCO/KSIC matcher.
        safe_text = pb._employment_nl.redact_personal_identifiers(text)
        prompt = pb._employment_nl.build_extraction_prompt(safe_text, lang=lang)

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

        # Single allow-listed Groq model. Do not retry with OpenRouter, 120B,
        # auto-routing or a paid model when free-tier limits are reached.
        try:
            raw = await pb._call_groq(
                prompt,
                model=EMPLOYMENT_GROQ_FREE_MODEL,
                response_format=pb._employment_nl.groq_strict_response_format(),
                reasoning_effort="low",
                max_tokens=1800,
                timeout_seconds=12,
            )
        except HTTPException as exc:
            upstream = (exc.detail or {}) if isinstance(exc.detail, dict) else {}
            code = upstream.get("status", exc.status_code)
            reason = (
                "rate_limited" if code == 429 else
                "invalid_provider_credentials" if code in (401, 403) else
                "invalid_model" if code == 404 else
                "timeout" if code == 504 else
                "provider_error"
            )
            return _interpret_unavailable(reason)
        except Exception:
            return _interpret_unavailable("provider_error")

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
            "provider": "groq",
            "model": EMPLOYMENT_GROQ_FREE_MODEL,
            "notice": ("직종·업종 코드는 이 단계에서 만들지 않습니다. 아래 후보는 공식 분류표에서 "
                       "검색한 결과이며, 최종 확정은 하이코리아에서 확인하세요."
                       if lang == "ko" else
                       "No classification code is produced at this step. Candidates below are "
                       "retrieved from the official tables; confirm the final code with HiKorea."),
        }
    return router
