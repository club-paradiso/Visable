"""Regression tests for legal_analysis-driven deterministic fallback answers."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import paradiso_backend as pb  # noqa: E402

CANDS = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
    "moonshotai/kimi-k2.6:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]
BAD_H1_STUDY_TEMPLATE_TERMS = ("H-1의 허용 활동범위", "계절학기", "학점 인정", "대학 수업", "D-2/D-4")
BAD_FIRST_SENTENCE_PREFIXES = (
    "Paradiso cannot verify",
    "Whether you can",
    "It depends",
    "Specific manual guidance was not found",
)


async def _openrouter_all_unavailable(prompt: str, model: str | None = None) -> str:
    raise HTTPException(
        status_code=502,
        detail={"error": "openrouter_upstream_error", "status": 503, "message": "No healthy upstream"},
    )


def _ask_fallback(question: str, *, lang: str = "ko", visa_code: str | None = None) -> dict:
    old_mode = os.environ.get("LAW_GROUNDING_MODE")
    os.environ["LAW_GROUNDING_MODE"] = "audit"
    os.environ.pop("LAW_API_OC", None)
    os.environ.pop("LAW_API_KEY", None)
    try:
        pb._reset_visas_cache_for_tests()
        pb._reset_grounding_cache_for_tests()
        pb._reset_openrouter_model_cooldowns_for_tests()
        with patch.object(pb, "OPENROUTER_API_KEY", "or-test-key"), \
                patch.object(pb, "GROQ_API_KEY", None), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", False), \
                patch.object(pb, "ENABLE_OLLAMA_FALLBACK", False), \
                patch.object(pb, "OPENROUTER_MODEL", CANDS[0]), \
                patch.object(pb, "OPENROUTER_MODEL_CANDIDATES", list(CANDS)), \
                patch.object(pb, "OPENROUTER_MODEL_COOLDOWN_SECONDS", 0), \
                patch.object(pb, "_call_openrouter", _openrouter_all_unavailable):
            client = TestClient(pb.app)
            payload = {"question": question, "lang": lang}
            if visa_code:
                payload["visa_code"] = visa_code
            resp = client.post("/api/ask", json=payload)
        assert resp.status_code == 200, resp.text
        return resp.json()
    finally:
        if old_mode is None:
            os.environ.pop("LAW_GROUNDING_MODE", None)
        else:
            os.environ["LAW_GROUNDING_MODE"] = old_mode


def _assert_legal_analysis_fallback(body: dict) -> None:
    assert body["deterministic_fallback_answer_used"] is True
    assert body["llm_unavailable"] is True
    assert body["provider_unavailable"] is True
    assert body["legal_analysis_exists"] is True
    assert body["fallback_answer_kind"] == "legal_analysis_preparation_note"
    assert body["legal_analysis"]
    first = (body["answer"] or "").strip()
    assert first
    assert not first.startswith(BAD_FIRST_SENTENCE_PREFIXES)


def test_e7_to_f299_side_job_fallback_does_not_leak_h1_study_template() -> None:
    body = _ask_fallback("E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?")
    _assert_legal_analysis_fallback(body)
    answer = body["answer"]
    assert "F-2-99" in answer
    assert "E-7" in answer
    assert ("부업" in answer) or ("근무처" in answer) or ("신고" in answer)
    assert "H-1" not in answer
    assert "계절학기" not in answer
    assert "학점 인정" not in answer
    assert "D-2/D-4" not in answer
    assert {"post_status_change_residual_duty", "reporting_duty"} & set(body["legal_issue_types"])
    assert body["immigration_facts"]["current_status"] == "F-2-99"
    assert body["immigration_facts"]["previous_status"] == "E-7"
    assert body["related_statuses_not_sources"] == []
    assert "H-1" not in " ".join(body.get("related_statuses_not_sources") or [])


def test_h1_summer_course_fallback_works_through_legal_analysis() -> None:
    body = _ask_fallback("H-1으로 한국 대학 계절학기 학점 수업을 들어도 되나요?")
    _assert_legal_analysis_fallback(body)
    answer = body["answer"]
    assert "H-1" in answer
    assert ("계절학기" in answer) or ("학점" in answer)
    assert ("활동범위" in answer) or ("체류 목적" in answer)
    assert "study_on_non_study_status" in body["legal_issue_types"]
    assert "credit_bearing_study" in body["proposed_activity_type"]
    assert "F-2" not in answer
    assert "E-7" not in answer


def test_g15_study_audit_fallback_is_g15_specific() -> None:
    body = _ask_fallback("G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?")
    _assert_legal_analysis_fallback(body)
    answer = body["answer"]
    assert "G-1-5" in answer
    assert any(term in answer for term in ("등록", "청강", "계절학기"))
    assert "H-1" not in answer
    assert "study_on_non_study_status" in body["legal_issue_types"]


def test_registration_fallback_does_not_become_school_enrollment() -> None:
    body = _ask_fallback("H-1 외국인등록은 언제 해야 하나요?")
    _assert_legal_analysis_fallback(body)
    answer = body["answer"]
    for bad in ("계절학기", "학점", "대학 수업", "D-2/D-4"):
        assert bad not in answer
    assert {"registration_or_residence_report", "reporting_duty"} & set(body["legal_issue_types"])
    assert "registration_or_reporting" in body["proposed_activity_type"]
    assert "formal_enrollment" not in body["proposed_activity_type"]
    assert body["immigration_facts"]["activity_facts"]["formal_enrollment"] == "false"


def test_target_status_fallback_preserves_target_route() -> None:
    body = _ask_fallback("Can I change status to F-2-99?", lang="en", visa_code="H-1")
    _assert_legal_analysis_fallback(body)
    facts = body["immigration_facts"]
    answer = body["answer"]
    assert facts["current_status"] == "H-1"
    assert facts["target_status"] == "F-2-99"
    assert facts["status_transition_detected"] is True
    assert "F-2-99" in answer
    assert "change" in answer.lower()
    assert any("F-2-99" in query for query in body["planned_law_queries"])
    assert "H-1 permitted activity scope" not in answer


def test_first_sentence_guard_for_deterministic_fallback_answers() -> None:
    questions = [
        ("E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?", "ko", None),
        ("H-1으로 한국 대학 계절학기 학점 수업을 들어도 되나요?", "ko", None),
        ("Can I change status to F-2-99?", "en", "H-1"),
    ]
    for question, lang, visa_code in questions:
        body = _ask_fallback(question, lang=lang, visa_code=visa_code)
        first = body["answer"].strip().split(".", 1)[0]
        assert not first.startswith(BAD_FIRST_SENTENCE_PREFIXES)


def test_e7_fallback_source_panel_metadata_has_no_unrelated_h1_study_chips() -> None:
    body = _ask_fallback("E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?")
    _assert_legal_analysis_fallback(body)
    default_chip_text = " ".join(body.get("related_statuses_not_sources") or []) + " " + " ".join(
        src.get("law_name", "") for src in body.get("law_sources") or []
    )
    assert "H-1" not in default_chip_text
    assert "D-2" not in default_chip_text
    assert "D-4" not in default_chip_text
    assert body["source_state"] == "legal_analysis_preparation_note"
