"""Mission 005-S: a cap on an amount is read as a cap, not a prohibition (guard and gate v14).

The 005-R T4 run withheld a correct answer, A05R-37: "must obtain permission … which must not exceed
18 hours per week" for evidence "…주 18시간을 넘지 않는 범위에서 시간제 취업을 할 수 있다". The polarity
reader took "must not" for a prohibition. With caps_apart=True the cap is left out before polarity is read.
Fictional fixtures, plus the recorded answers of earlier runs.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import claim_support_validation as claims
import grounding_guard as guard
import synthetic_safety_gate_v13 as gate13
import synthetic_safety_gate_v14 as gate14

R37 = "A Q-4-3 resident must obtain permission for activities outside their residency status to engage in part-time employment, which must not exceed 18 hours per week."


@pytest.mark.parametrize("answer", [
    R37,
    "You may work part-time, but not more than 18 hours a week.",
    "With permission you can work part-time; the hours may not exceed 18 per week.",
    "Part-time work is fine as long as it is no more than 18 hours a week.",
    "허가를 받으면 주 18시간을 넘지 않는 범위에서 시간제 취업을 할 수 있습니다.",
    "주 20시간을 초과할 수 없습니다만 허가를 받으면 일할 수 있습니다.",
    "Bạn có thể làm thêm nhưng không được vượt quá 18 giờ mỗi tuần.",
])
def test_a_cap_is_not_a_reversal_of_a_permission(answer):
    assert claims.polarity_reversed(answer, "permitted", caps_apart=True) is False


@pytest.mark.parametrize("answer, expected", [
    ("You cannot take part-time work.", "permitted"),
    ("Part-time work is not allowed for this status.", "permitted"),
    ("시간제 취업을 할 수 없습니다.", "permitted"),
    ("Bạn không được làm thêm.", "permitted"),
    ("You can take part-time work up to 18 hours.", "prohibited"),
    ("주 18시간까지 일할 수 있습니다.", "prohibited"),
])
def test_real_reversals_are_still_caught(answer, expected):
    assert claims.polarity_reversed(answer, expected, caps_apart=True) is True


def test_the_default_keeps_the_005r_reading():
    assert claims.polarity_reversed(R37, "permitted") is True


def test_recorded_answers_of_earlier_runs_change_only_a05r_37():
    changed = []
    for run in sorted(BOOT.glob("runs/mission005*/synthetic_acceptance/pipeline.jsonl")):
        mission = run.parts[-3][-1]
        suite = BOOT / "validation" / f"mission005{mission}_synthetic_acceptance.json"
        cases = {c["id"]: c for c in json.loads(suite.read_text())["cases"]}
        for line in run.read_text().splitlines():
            r = json.loads(line)
            case = cases.get(r["case_id"])
            if not case or not r.get("model_called"):
                continue
            for raw in [r.get("raw_output"), *(r.get("raw_outputs") or []), (r.get("language_retry") or {}).get("raw_output")]:
                try:
                    out = json.loads(raw) if raw else None
                except ValueError:
                    continue
                if not isinstance(out, dict) or not isinstance(out.get("answer"), str):
                    continue
                ids = set(r.get("admissible_ids") or [])
                admissible = {e["id"]: e["id"] in ids for e in case["evidence"]}
                cites = set(out.get("citations") or []) & ids
                args = (out["answer"], case["question"], case["evidence"], cites, admissible, True, True, True)
                before = {f["kind"] for f in claims.check(*args)["findings"]}
                after = {f["kind"] for f in claims.check(*args, caps_apart=True)["findings"]}
                polarity = case["expected"].get("expected_polarity")
                if before != after or (polarity and claims.polarity_reversed(out["answer"], polarity)
                                       != claims.polarity_reversed(out["answer"], polarity, caps_apart=True)):
                    changed.append(r["case_id"])
    assert sorted(set(changed)) == ["A05R-37"]


def test_a05r_37_is_released_by_the_005s_guard_and_correct_under_gate_v14():
    cases = {c["id"]: c for c in json.loads((BOOT / "validation" / "mission005r_synthetic_acceptance.json").read_text())["cases"]}
    recorded = {json.loads(l)["case_id"]: json.loads(l) for l in
                (BOOT / "runs" / "mission005r" / "synthetic_acceptance" / "pipeline.jsonl").read_text().splitlines()}["A05R-37"]
    case = cases["A05R-37"]
    assert recorded["released_provenance"] == "post_generation_blocked"
    record = guard.run_case(case["question"], case["intake"], case["evidence"], gate14.registry_for(case, "acceptance"),
                            "2026-11-02", lambda item: recorded["raw_output"])
    assert record["released_provenance"] == "model_generated" and record["guard"]["findings"] == []
    assert gate14.score_case(case, record)["raw"]["outcome"] == "pass"
    assert gate14.score_case(case, record)["end_to_end"]["correct"] is True
    assert [c["kind"] for c in gate13.score_case(case, record)["raw"]["critical"]] == ["polarity_reversal"]   # the 005-R reading
