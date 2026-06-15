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


async def _openrouter_all_unavailable(prompt: str, model: str | None = None, max_tokens: int | None = None) -> str:
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
    assert body["source_panel_state"] == "structured_fallback_available"
    assert body["source_panel_label_key"] == "structured_fallback"
    assert body["default_source_panel_should_show_raw_codes"] is False
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


_INTERNAL_SNAKE_LABELS = (
    "current_status/sub_status", "previous_status/approval_conditions",
    "target_status/route", "paid_or_credit_bearing", "duration/employer_or_school",
)
_ENGLISH_QUESTION_STEMS = (
    "What exact current status", "What is your current sojourn",
    "Is the course credit-bearing", "Does the school require",
    "What event starts the deadline", "Where and how must the report",
)


def test_g15_korean_fallback_has_no_internal_field_names() -> None:
    # Part D / Part E: no internal snake_case labels leak into the Korean memo.
    body = _ask_fallback("G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?")
    _assert_legal_analysis_fallback(body)
    answer = body["answer"]
    for label in _INTERNAL_SNAKE_LABELS:
        assert label not in answer, label


def test_g15_korean_fallback_has_no_english_official_questions() -> None:
    body = _ask_fallback("G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?")
    answer = body["answer"]
    for stem in _ENGLISH_QUESTION_STEMS:
        assert stem not in answer, stem


def test_g15_korean_fallback_has_no_unrelated_deadline_address_questions() -> None:
    # Part D: a study/audit question must not carry deadline/address-change Qs.
    body = _ask_fallback("G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?")
    answer = body["answer"]
    for unrelated in ("주소변경", "신고 기한은 며칠", "입국한 날짜", "address change"):
        assert unrelated not in answer, unrelated


def test_g15_korean_fallback_includes_g15_specific_confirmation_questions() -> None:
    # Part D: the exact G-1-5 study confirmation set should be present.
    body = _ask_fallback("G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?")
    answer = body["answer"]
    assert "G-1-5 부여 사유" in answer
    assert "등록/청강/계절학기 중 어떤 활동인지" in answer
    assert "학점 인정 또는 학위 과정 관련성" in answer
    assert "D-2/D-4 등 유학 체류자격을 요구하는지" in answer
    assert "자격외활동허가 또는 체류자격 변경이 필요한지" in answer


def test_h1_registration_korean_fallback_asks_registration_facts() -> None:
    # Part C / Part D: entry date, stay period, registration deadline, channel.
    body = _ask_fallback("H-1 외국인등록은 언제 해야 하나요?")
    _assert_legal_analysis_fallback(body)
    answer = body["answer"]
    assert "입국" in answer        # entry date
    assert "체류기간" in answer     # stay period
    assert "기한" in answer         # registration deadline
    assert "하이코리아" in answer or "출입국·외국인청" in answer  # filing channel
    for bad in ("계절학기", "학점", "대학 수업", "D-2/D-4"):
        assert bad not in answer, bad
    for label in _INTERNAL_SNAKE_LABELS:
        assert label not in answer, label


def test_english_fallback_stays_english() -> None:
    # Part E: English mode confirmation questions/facts remain English (no Hangul
    # confirmation labels), while official Korean term references may still appear
    # inside the legal-analysis wording.
    body = _ask_fallback("Can I change status to F-2-99?", lang="en", visa_code="H-1")
    _assert_legal_analysis_fallback(body)
    answer = body["answer"]
    assert "change" in answer.lower()
    # The localized confirmation block should be English questions.
    assert ("Questions to confirm" in answer) or ("requirements to change" in answer)
    for label in _INTERNAL_SNAKE_LABELS:
        assert label not in answer, label


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
    assert body["source_panel_state"] == "structured_fallback_available"
    assert body["source_panel_label_key"] == "structured_fallback"
    assert "H-1" not in body["answer"]


def test_copy_safe_answer_does_not_include_raw_diagnostics() -> None:
    body = _ask_fallback("E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?")
    _assert_legal_analysis_fallback(body)
    copied = body.get("copy_safe_answer") or body.get("answer") or ""
    for code in ("SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE", "CITATION_VERIFICATION_NOT_WIRED"):
        assert code not in copied


def test_legal_analysis_with_bad_law_response_uses_structured_analysis_state() -> None:
    pack = {
        "legal_analysis": {"analysis_mode": "limited_authority"},
        "law_grounding_warnings": ["SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE"],
    }
    meta = pb._derive_source_panel_metadata(
        law_evidence_pack=pack,
        citation_verification={"status": "not_wired"},
        law_grounding_used=False,
        law_grounding_attempted=True,
        law_grounding_status="unavailable",
        law_grounding_warnings=["SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE"],
        manual_grounding_status="manual_grounding_missing",
    )
    assert meta["source_panel_state"] == "structured_legal_analysis_available"
    assert meta["source_panel_label_key"] == "structured_legal_analysis_law_lookup_issue"
    assert meta["law_lookup_error_type"] == "LAW_API_BAD_RESPONSE"
    assert meta["default_source_panel_should_show_raw_codes"] is False


def test_pure_no_source_no_legal_analysis_maps_to_source_unavailable() -> None:
    meta = pb._derive_source_panel_metadata(
        law_evidence_pack={},
        citation_verification=None,
        law_grounding_used=False,
        law_grounding_attempted=False,
        law_grounding_status="not_attempted",
        law_grounding_warnings=[],
        manual_grounding_status="manual_grounding_missing",
    )
    assert meta["source_panel_state"] == "source_unavailable"
    assert meta["source_panel_label_key"] == "source_unavailable"


def test_e7_side_job_low_direct_authority_confidence_gates_answer() -> None:
    body = _ask_fallback("E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?")
    _assert_legal_analysis_fallback(body)
    answer = body["answer"]
    assert "원칙적으로 이전 자격인 E-7에 묶여 있던 근무처 변경·추가 신고 의무는 더 이상 적용되지 않습니다" not in answer
    assert "신고 의무는 없습니다" not in answer
    assert "반드시 신고해야 합니다" not in answer
    assert "현재 F-2-99" in answer
    assert "이전 E-7 기준만으로 판단할 사안은 아니" in answer
    assert "개별 승인 조건" in answer
    assert "부업의 형태" in answer
    assert body["missing_direct_authority"] is True
    assert body["direct_evidence_count"] == 0
    assert body["direct_authority_available"] is False
    assert body["answer_certainty_level"] in {"limited", "unavailable"}


def test_direct_mocked_authority_allows_direct_certainty() -> None:
    pack = {
        "legal_analysis": {"analysis_mode": "direct_authority"},
        "direct_evidence_count": 1,
        "related_evidence_count": 0,
        "analogical_evidence_count": 0,
        "law_evidence_count": 1,
        "law_sources": [{"law_name": "mock direct authority"}],
        "missing_direct_authority": False,
    }
    meta = pb._derive_source_panel_metadata(
        law_evidence_pack=pack,
        citation_verification={"status": "verified", "warnings": []},
        law_grounding_used=True,
        law_grounding_attempted=True,
        law_grounding_status="used",
        law_grounding_warnings=[],
        manual_grounding_status="absent",
    )
    assert meta["direct_authority_available"] is True
    assert meta["direct_citation_available"] is True
    assert meta["answer_certainty_level"] == "direct"
    strong = "신고 의무는 없습니다"
    assert pb._confidence_gate_answer_text(strong, meta) == strong


def test_h1_study_low_authority_avoids_definitive_permission_or_denial() -> None:
    body = _ask_fallback("H-1으로 한국 대학 계절학기 학점 수업을 들어도 되나요?")
    answer = body["answer"]
    for phrase in ("허용됩니다", "가능합니다", "반드시 불가능", "금지됩니다"):
        assert phrase not in answer
    assert "활동범위" in answer or "체류 목적" in answer
    assert body["answer_certainty_level"] in {"limited", "unavailable"}


def test_c3_paid_work_source_limited_no_invented_penalty_or_overconfident_conclusion() -> None:
    body = _ask_fallback("C-3로 한국에서 유급 일을 하면 벌금이 얼마인가요?", visa_code="C-3")
    answer = body["answer"]
    assert "벌금" not in answer or "확인" in answer or "단정" in answer
    assert "신고 의무는 없습니다" not in answer
    assert "허용됩니다" not in answer
    assert body["answer_certainty_level"] in {"limited", "unavailable"}


def test_source_panel_contract_for_legal_analysis_bad_law_response() -> None:
    pack = {
        "legal_analysis": {"analysis_mode": "source_unavailable"},
        "law_grounding_warnings": ["SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE"],
        "direct_evidence_count": 0,
    }
    meta = pb._derive_source_panel_metadata(
        law_evidence_pack=pack,
        citation_verification={"status": "law_api_unavailable", "warnings": ["SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE"]},
        law_grounding_used=False,
        law_grounding_attempted=True,
        law_grounding_status="unavailable",
        law_grounding_warnings=["SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE"],
        manual_grounding_status="absent",
    )
    assert meta["source_panel_state"] == "structured_legal_analysis_available"
    assert meta["source_panel_label_key"] == "structured_legal_analysis_law_lookup_issue"
    assert meta["law_lookup_error_type"] == "LAW_API_BAD_RESPONSE"
    assert meta["source_panel_confidence"] == "low"
    assert meta["law_lookup_failed"] is True
