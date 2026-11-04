"""Nationality services coach: /api/nationality-coach.

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
        "/api/nationality-coach",
        dependencies=[Depends(pb.rate_limit("nationality_coach", per_minute=6, per_day=100))],
    )
    async def nationality_coach(req: pb.NationalityCoachRequest) -> Dict[str, Any]:
        mode = (req.mode or "naturalization_interview_prep").strip()
        lang = "en" if str(req.lang or "ko").lower().startswith("en") else "ko"
        lang_line = (
            "Write all string values in natural English."
            if lang == "en"
            else "Write all string values in natural Korean (자연스러운 한국어)."
        )

        if mode == "nationality_services":
            system_prompt = pb.NATIONALITY_SERVICES_SYSTEM_PROMPT
            question = (req.message or req.question or "").strip()
            user_prompt = (
                f"{lang_line}\n"
                "The user asks about Korean nationality civil affairs. Give general, "
                "source-aware guidance. Do not state final eligibility. Prefer hedged "
                "phrasing (일반적으로는 / 공식 안내 기준으로는 / 개별 사안은 관할 "
                "출입국외국인관서 확인이 필요합니다). Do not invent article numbers or "
                "source URLs.\n\n"
                f"User question: {question}\n\n"
                "Return ONLY this JSON object:\n"
                "{\n"
                '  "summary": "",\n'
                '  "relevantCategory": "",\n'
                '  "generalFlow": [],\n'
                '  "documentsNote": "",\n'
                '  "sourceBasedPoints": [],\n'
                '  "cautions": [],\n'
                '  "relatedSources": [],\n'
                '  "nextBestAction": ""\n'
                "}"
            )
        else:
            mode = "naturalization_interview_prep"
            system_prompt = pb.NATURALIZATION_INTERVIEW_PREP_SYSTEM_PROMPT
            question = (req.question or "").strip()
            answer = (req.answer or "").strip()
            user_prompt = (
                f"{lang_line}\n"
                "This is naturalization-interview PRACTICE, not official adjudication. "
                "The question is practice material, not an official past question. "
                "Review the user's typed answer. Never predict pass/fail, never say "
                "the answer guarantees approval, never claim the question is official.\n"
                "Evaluate the answer along these practice dimensions (do NOT score or "
                "grade): 직접성(질문에 바로 답했는가), 구체성(경험·예시가 있는가), "
                "구조(이유→예시→결론), 태도·안전성(혜택·금전·의무회피만 강조하지 않는가). "
                "Put concrete, dimension-aware points in strengths/improvements.\n\n"
                f"Practice question (category={req.category or ''}, difficulty={req.difficulty or ''}):\n{question}\n\n"
                f"User's typed answer:\n{answer}\n\n"
                "Return ONLY this JSON object:\n"
                "{\n"
                '  "strengths": [],\n'
                '  "improvements": [],\n'
                '  "revisedAnswer": "",\n'
                '  "riskyExpressions": [],\n'
                '  "followUpQuestion": "",\n'
                '  "studyTip": "",\n'
                '  "caution": "이 피드백은 연습용이며 실제 심사 결과를 보장하지 않습니다."\n'
                "}"
            )

        result = await pb._coach_complete(system_prompt, user_prompt)
        parsed = pb._coach_extract_json(result["content"])
        if not isinstance(parsed, dict):
            raise HTTPException(
                status_code=502,
                detail={"error": "coach_unparseable", "message": "Model did not return valid JSON."},
            )
        if mode == "naturalization_interview_prep":
            if not parsed.get("caution"):
                parsed["caution"] = "이 피드백은 연습용이며 실제 심사 결과를 보장하지 않습니다."
        parsed["mode"] = mode
        parsed["provider"] = result["provider"]
        # Which model actually answered is non-secret routing metadata; surfacing it
        # keeps the coach as auditable as every other AI surface.
        parsed["model"] = result.get("model", "")
        parsed["modelFallbackUsed"] = bool(result.get("model_fallback_used"))
        parsed["ai_available"] = True
        return parsed
    return router
