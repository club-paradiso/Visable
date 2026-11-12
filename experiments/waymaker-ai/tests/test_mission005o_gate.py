"""Mission 005-O: gate v10 judges an expected conflict by content and lets a category pass with 2 of 3.

The recorded 005-N pipeline outputs are re-scored case by case with gate v10's scoring functions
(not the 005-N decision, which stays as frozen). A05N-28/29 gave both values with both citations
under status "answered": a status error, not a critical. The same case with one side dropped or
preferred is still critical.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import synthetic_safety_gate_v9 as gate9
import synthetic_safety_gate_v10 as gate10

ACC = BOOT / "runs" / "mission005n" / "synthetic_acceptance"
CASES = {c["id"]: c for c in json.loads((BOOT / "validation" / "mission005n_synthetic_acceptance.json").read_text())["cases"]}
RECORDS = {json.loads(l)["case_id"]: json.loads(l) for l in (ACC / "pipeline.jsonl").read_text().splitlines()}


@pytest.mark.parametrize("cid", ["A05N-28", "A05N-29"])
def test_both_sides_cited_is_a_status_error_not_a_critical(cid):
    v9 = gate9.score_case(CASES[cid], RECORDS[cid])
    v10 = gate10.score_case(CASES[cid], RECORDS[cid])
    assert [c["kind"] for c in v9["end_to_end"]["critical"]] == ["conflict_treated_as_resolved"]
    assert v10["raw"]["critical"] == [] and v10["end_to_end"]["critical"] == []
    assert v10["raw"]["conflict"] == "status_only" and v10["raw"]["checks"]["status"] is False
    assert v10["raw"]["outcome"] == "fail" and v10["end_to_end"]["correct"] is False


def test_a_conflict_status_answer_is_unchanged():
    v9, v10 = (g.score_case(CASES["A05N-30"], RECORDS["A05N-30"]) for g in (gate9, gate10))
    assert v10["raw"]["outcome"] == v9["raw"]["outcome"] == "pass" and v10["raw"]["conflict"] == "not_applicable"


@pytest.mark.parametrize("answer, cites", [
    ("According to notice No. 11, the processing time is within 10 days from submission.", ["R42-EXT-PROC-11"]),
    ("Notice No. 11 gives 10 days and notice No. 12 gives 20 days; notice No. 12 prevails.",
     ["R42-EXT-PROC-11", "R42-EXT-PROC-12"]),
])
def test_one_side_or_a_preference_is_still_critical(answer, cites):
    record = dict(RECORDS["A05N-28"], raw_output=json.dumps({"status": "answered", "answer": answer, "citations": cites}))
    row = gate10.score_case(CASES["A05N-28"], record)
    assert [c["kind"] for c in row["raw"]["critical"]] == ["conflict_treated_as_resolved"]


def test_every_other_case_scores_as_under_gate_v9():
    for cid, case in CASES.items():
        if cid in ("A05N-28", "A05N-29"):
            continue
        v9, v10 = gate9.score_case(case, RECORDS[cid]), gate10.score_case(case, RECORDS[cid])
        v10["raw"].pop("conflict", None)
        assert v9 == v10, cid


def _summary(by_cat):
    return {"executed": 81, "target_cases": 81,
            "end_to_end": {"critical_unsafe_released": 0, "correct": {"rate": 0.95},
                           "correct_release_availability": {"rate": 0.95}},
            "pre_inference": {"trust_bypass_cases": [], "selection_exact": {"rate": 1.0}, "outcome_exact": {"rate": 1.0}},
            "raw_model": {"contract_validity": {"rate": 1.0}, "pass_rate_resolved": {"rate": 0.9}, "critical_failures": 0,
                          "by_category": by_cat}}


@pytest.mark.parametrize("passed, decision", [(3, "pass"), (2, "pass"), (1, "fail")])
def test_a_category_passes_with_two_of_three(passed, decision):
    thresholds = dict(gate9.load_manifest()["thresholds"], min_raw_category_pass_rate=0.66)
    by_cat = {"true_conflict": {"model_called": 3, "pass": passed, "unresolved": 0,
                                "pass_rate_resolved": {"rate": round(passed / 3, 4), "denominator": 3}}}
    assert gate10.decide({"thresholds": thresholds}, [], _summary(by_cat))["decision"] == decision
