#!/usr/bin/env python3
"""Regenerate the Waymaker public /api/ask fixtures used by the browser tests.

The fixtures are the REAL public projection the backend returns for the D-2
document lookup, produced offline with a stubbed model that answers the way
the production free-tier model did (Markdown headings, a re-derived list, an
internal "source file" citation). Browser tests then render exactly what a
normal user's browser would receive. ``backend/tests`` asserts the committed
fixtures still match the backend output (drift guard).

Usage: python3 scripts/build_waymaker_answer_fixtures.py [--check]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
OUT_DIR = REPO / "tests" / "fixtures" / "waymaker"

LEAKY_MODEL_ANSWER = (
    "유학(D-2) 체류기간 연장허가에는 기본 서류와 학업·재정·체류지 관련 증빙이 필요합니다"
    "(외국인체류 안내매뉴얼 2026.6; source file 2026-06-23, pp. 43-44).\n\n"
    "### 필수 서류\n- 신청서\n- 여권\n- 외국인등록증\n- 수수료\n\n"
    "### 조건부·증빙 서류\n- 재정입증 서류\n\n"
    "출처: 외국인체류 안내매뉴얼 (2026.6; source file 2026-06-23)"
)
LEAKY_MODEL_ANSWER_EN = (
    "For a D-2 extension you need the basic application documents plus proof of"
    " your studies, finances and place of stay (Stay Manual 2026.6; source file 2026-06-23).\n\n"
    "### Required documents\n- Application form\n- Passport\n\n"
    "Source: Stay Manual (2026.6; source file 2026-06-23)"
)
CASES = {
    "d2_documents_ko_fast.json": ({"question": "D-2 연장시 필수 서류", "lang": "ko", "answer_mode": "fast"}, LEAKY_MODEL_ANSWER),
    "d2_documents_en_fast.json": ({"question": "What documents do I need to extend a D-2?", "lang": "en", "answer_mode": "fast"}, LEAKY_MODEL_ANSWER_EN),
    # Every Fast candidate failed non-retryably (the production 503 incident):
    # the backend must still return the deterministic structured answer.
    "d2_documents_ko_fast_provider_failed.json": ({"question": "D-2 연장시 필수 서류", "lang": "ko", "answer_mode": "fast"}, None),
}
# answer_ref is a per-request opaque feedback reference (random id).
VOLATILE = ("law_grounding_retrieval_timestamp", "retrievedAt", "retrieval_timestamp", "answer_ref")


def _strip_volatile(value):
    if isinstance(value, dict):
        return {k: ("<volatile>" if k in VOLATILE else _strip_volatile(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_volatile(v) for v in value]
    return value


def build() -> dict:
    os.environ.setdefault("OPENROUTER_API_KEY", "fixture-sentinel")
    # Deterministic knowledge state: the committed seed, never a local DB.
    os.environ.setdefault("WAYMAKER_KNOWLEDGE_DB", ":memory:")
    from fastapi.testclient import TestClient
    import paradiso_backend as pb

    current = {"answer": LEAKY_MODEL_ANSWER}

    async def fake(prompt, requested_model=None, candidate_models=None, max_tokens=None, **kw):
        model = (candidate_models or ["fixture/model"])[0]
        if current["answer"] is None:
            return {
                "ok": False, "answer": None, "primary_model": model, "requested_model": None,
                "model_candidates": list(candidate_models or [model]),
                "attempted_models": list(candidate_models or [model]),
                "skipped_models_due_to_cooldown": [], "cooling_down_models": [], "model_cooldown_seconds": 0,
                "cooldown_enabled": False, "final_model": None, "model_fallback_used": True,
                "provider_error_type": "model_not_found", "upstream_statuses": [404],
                "retryable_provider_error": False, "all_candidates_failed": True,
            }
        return {
            "ok": True, "answer": current["answer"], "primary_model": model, "requested_model": None,
            "model_candidates": list(candidate_models or [model]), "attempted_models": [model],
            "skipped_models_due_to_cooldown": [], "cooling_down_models": [], "model_cooldown_seconds": 0,
            "cooldown_enabled": False, "final_model": model, "model_fallback_used": False,
            "provider_error_type": None, "upstream_statuses": [], "retryable_provider_error": False,
            "all_candidates_failed": False,
        }

    out = {}
    with patch.object(pb, "OPENROUTER_API_KEY", "fixture-sentinel"), \
            patch.object(pb, "_openrouter_complete_with_candidates", fake):
        client = TestClient(pb.app)
        for name, (body, model_answer) in CASES.items():
            current["answer"] = model_answer
            resp = client.post("/api/ask", json={**body, "consent": True, "stream": False})
            resp.raise_for_status()
            out[name] = _strip_volatile(resp.json())
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    built = build()
    stale = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in built.items():
        text = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
        path = OUT_DIR / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.write_text(text, encoding="utf-8")
    if stale:
        print("stale Waymaker fixtures: " + ", ".join(stale) + " (run scripts/build_waymaker_answer_fixtures.py)")
        return 1
    print("Waymaker answer fixtures " + ("up to date" if args.check else "written"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
