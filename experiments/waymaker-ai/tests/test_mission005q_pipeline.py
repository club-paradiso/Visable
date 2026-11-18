"""Mission 005-Q: Vietnamese dates are read as dates in claim support (guard and gate v12).

Fictional fixtures only. A05P-24 withheld a correct Vietnamese answer that wrote
"ngày 1 tháng 6 năm 2026": "1 tháng" and "6 năm" were read as periods against the evidence's 18일.
Real periods ("trong vòng 1 tháng", "6 năm") and wrong dates are still caught.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import claim_support_validation as claims
import grounding_guard as guard
import synthetic_safety_gate_v11 as gate11
import synthetic_safety_gate_v12 as gate12

EVIDENCE = [{"id": "E", "title": "", "text": "[가상 고시 제35호] 2026년 6월 1일부터 Y-9-1 체류자의 재입국허가는 신청일부터 18일 이내에 처리한다."}]
CASES_P = {c["id"]: c for c in json.loads((BOOT / "validation" / "mission005p_synthetic_acceptance.json").read_text())["cases"]}
PIPELINE_P = {json.loads(l)["case_id"]: json.loads(l)
              for l in (BOOT / "runs" / "mission005p" / "synthetic_acceptance" / "pipeline.jsonl").read_text().splitlines()}


def check(answer, **flags):
    return claims.check(answer, "가상 질문", EVIDENCE, {"E"}, {"E": True}, with_source=True, ages_apart=True, **flags)


@pytest.mark.parametrize("answer", [
    "Thời gian xử lý là trong vòng 18 ngày, áp dụng từ ngày 1 tháng 6 năm 2026.",
    "Áp dụng từ 1 tháng 6 năm 2026, xử lý trong 18 ngày.",
    "Từ ngày 1 tháng 6, giấy phép được xử lý trong 18 ngày.",
    "Từ tháng 6 năm 2026, giấy phép được xử lý trong 18 ngày.",
    "NGÀY 1 THÁNG 6 NĂM 2026: 18 ngày.",
])
def test_a_vietnamese_date_is_not_two_periods(answer):
    assert check(answer)["result"] == "contradiction"   # the 005-P reading
    assert check(answer, vi_dates=True)["result"] == "no_contradiction_found"


@pytest.mark.parametrize("answer, kind", [
    ("Giấy phép được xử lý trong vòng 1 tháng.", "period_mismatch"),
    ("Giấy phép được xử lý trong 6 năm.", "period_mismatch"),
    ("Áp dụng từ ngày 2 tháng 7 năm 2026, xử lý trong 18 ngày.", "date_mismatch"),
    ("Áp dụng từ ngày 1 tháng 6 năm 2026, xử lý trong 20 ngày.", "period_mismatch"),
])
def test_real_periods_and_wrong_dates_are_still_caught(answer, kind):
    result = check(answer, vi_dates=True)
    assert result["result"] == "contradiction" and kind in [f["kind"] for f in result["findings"]]


def test_the_default_keeps_the_005p_reading():
    answer = "Áp dụng từ ngày 1 tháng 6 năm 2026, xử lý trong 18 ngày."
    assert [f["kind"] for f in check(answer)["findings"]] == ["period_mismatch", "period_mismatch"]


def test_a05p_24_is_released_by_the_005q_guard_and_correct_under_gate_v12():
    case, recorded = CASES_P["A05P-24"], PIPELINE_P["A05P-24"]
    assert recorded["released_provenance"] == "post_generation_blocked"
    record = guard.run_case(case["question"], case["intake"], case["evidence"], gate12.registry_for(case, "acceptance"),
                            case.get("as_of") or "2026-11-02", lambda item: recorded["raw_output"])
    assert record["released_provenance"] == "model_generated" and record["guard"]["findings"] == []
    assert gate12.score_case(case, record)["end_to_end"]["correct"] is True
    assert gate11.score_case(case, record)["raw"]["checks"]["claim_support"] is False   # v11 still read two periods
    assert gate12.score_case(case, record)["raw"]["outcome"] == "pass"
