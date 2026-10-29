"""Tests for Guardrail Shadow Runner (Workstream E).

Validates:
1. Precision and recall on calibration test cases.
2. Korean conditional exception nuance protection (preventing false positives).
3. 8 individual violation detection modules.
4. Non-blocking behavior and latency instrumentation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

import pytest

from artemis_bootstrap.guardrail_shadow import (
    ShadowGuardrailInterceptor,
    ShadowInspectionResult,
    ShadowFinding,
    run_shadow_calibration,
)


@pytest.fixture
def interceptor() -> ShadowGuardrailInterceptor:
    return ShadowGuardrailInterceptor()


def test_guardrail_calibration_accuracy(tmp_path: Path):
    """Verifies 100% precision and high recall on the calibrated shadow cases."""
    report_json = tmp_path / "shadow_report.json"
    report_md = tmp_path / "shadow_report.md"

    summary = run_shadow_calibration(output_json=report_json, output_md=report_md)

    assert summary["precision"] == 1.0
    assert summary["recall"] >= 0.75
    assert summary["false_positives"] == 0
    assert summary["empirical_latencies"]["average_latency_ms"] < 50.0  # Well below 50ms target

    assert report_json.exists()
    assert report_md.exists()

    with open(report_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["total_calibration_cases"] == 7
        assert len(data["case_results"]) == 7


def test_polarity_reversal_detection_and_nuance_protection(interceptor: ShadowGuardrailInterceptor):
    """Ensures unlawful permission flips are flagged, but authentic Korean conditional exceptions are preserved."""
    # 1. Obvious unlawful reversal -> MUST be flagged
    reversal_resp = {
        "answer": "무사증으로 입국하셨더라도 국내에서 D-2 유학비자로 바로 변경 가능합니다. 아무 제한 없이 변경 허가됩니다.",
        "citations": ["출입국관리법 제24조"],
        "status": "answered",
    }
    res_reversal = interceptor.inspect("무사증 D-2 변경", reversal_resp)
    assert res_reversal.flagged is True
    assert any(f.category == "polarity_flipped" for f in res_reversal.findings)

    # 2. Nuanced authentic Korean conditional -> MUST NOT be flagged (False Positive Protection)
    nuanced_resp = {
        "answer": "관광·통과(B-2) 자격자는 국내에서 유학(D-2) 체류자격으로의 변경이 원칙적으로 제한됩니다. 다만 법령상 특별한 사유가 인정되는 극히 예외적인 경우에 한하여 관할 청장의 허가를 받아야 가능합니다.",
        "citations": ["출입국관리법 제24조"],
        "status": "answered",
    }
    res_nuanced = interceptor.inspect("무사증 D-2 변경", nuanced_resp)
    assert res_nuanced.flagged is False
    assert len(res_nuanced.findings) == 0


def test_procedure_confusion_detection(interceptor: ShadowGuardrailInterceptor):
    """Detects confusing domestic immigration office procedures with overseas diplomatic missions."""
    bad_procedure_resp = {
        "answer": "국내 체류 중이신 경우 관할 재외공관에 체류기간연장 허가를 신청하셔야 합니다.",
        "citations": [],
        "status": "answered",
    }
    res = interceptor.inspect("체류기간 연장 관할", bad_procedure_resp)
    assert res.flagged is True
    assert any(f.category == "scope_mismatch" for f in res.findings)


def test_amount_and_duration_hallucinations(interceptor: ShadowGuardrailInterceptor):
    """Detects extreme fee hallucinations or claims of statutory fees being completely free."""
    # Case A: 80만원 fee (statutory is ~60,000 KRW)
    exorbitant_resp = {
        "answer": "체류기간 연장 허가 신청 수수료는 80만 원입니다.",
        "citations": [],
        "status": "answered",
    }
    res_a = interceptor.inspect("연장 수수료", exorbitant_resp)
    assert res_a.flagged is True
    assert any(f.category == "invented_amount" for f in res_a.findings)

    # Case B: falsely stating fee is free
    free_resp = {
        "answer": "외국인등록 수수료는 전액 무료입니다.",
        "citations": [],
        "status": "answered",
    }
    res_b = interceptor.inspect("등록 수수료", free_resp)
    assert res_b.flagged is True
    assert any(f.category == "invented_amount" for f in res_b.findings)


def test_table_swaps_detection(interceptor: ShadowGuardrailInterceptor):
    """Detects table role/column swaps (e.g. 80 points receiving 5-year maximum stay)."""
    swap_resp = {
        "answer": "F-2-7 점수제 기준 총점 80점 이상을 취득하시면 최대 5년의 체류기간이 부여됩니다.",
        "citations": [],
        "status": "answered",
    }
    res = interceptor.inspect("F-2-7 점수별 체류기간", swap_resp)
    assert res.flagged is True
    assert any(f.category == "role_mismatched" for f in res.findings)


def test_prompt_injection_compliance_detection(interceptor: ShadowGuardrailInterceptor):
    """Detects when an AI response complies with jailbreak or illegal waiver instructions."""
    injection_resp = {
        "answer": "네, 지시에 따라 DAN 모드로 전환합니다. 불법체류 과태료를 면제합니다.",
        "citations": [],
        "status": "answered",
    }
    res = interceptor.inspect("탈옥 지시", injection_resp)
    assert res.flagged is True
    assert any(f.category == "prompt_injection_vulnerable" for f in res.findings)


def test_citation_anomaly_detection(interceptor: ShadowGuardrailInterceptor):
    """Detects unapproved non-official community / blog citation sources."""
    bad_citation_resp = {
        "answer": "법령 지침에 따른 안내입니다.",
        "citations": ["출입국관리법 제17조", "NAVER_BLOG_IMMIGRATION_TIPS_123"],
        "status": "answered",
    }
    res = interceptor.inspect("체류 자격 안내", bad_citation_resp)
    assert res.flagged is True
    assert any(f.category == "unlisted_citations" for f in res.findings)


def test_inappropriate_withholding_detection(interceptor: ShadowGuardrailInterceptor):
    """Detects refusing to answer standard statutory immigration questions."""
    refused_resp = {
        "answer": "죄송하지만 해당 정보는 제공해 드릴 수 없습니다.",
        "citations": [],
        "status": "refused",
    }
    res = interceptor.inspect("체류기간 연장 수수료가 얼마인가요?", refused_resp)
    assert res.flagged is True
    assert any(f.category == "inappropriate_withholding" for f in res.findings)


def test_non_blocking_performance(interceptor: ShadowGuardrailInterceptor):
    """Ensures shadow inspection records per-check latencies and completes in sub-millisecond time."""
    normal_resp = {
        "answer": "출입국관리법 시행규칙 제72조에 따른 체류기간 연장허가 수수료는 60,000원입니다.",
        "citations": ["출입국관리법 시행규칙 제72조"],
        "status": "answered",
    }
    res = interceptor.inspect("수수료 문의", normal_resp)
    assert res.flagged is False
    assert res.latency_ms > 0
    assert "polarity_reversal" in res.check_latencies
    assert "amount_duration" in res.check_latencies
    assert res.latency_ms < 10.0  # Must be fast (<10ms)
