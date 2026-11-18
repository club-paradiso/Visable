"""Owner decision after Mission 005-N: an expected conflict counts as resolved by content.

The four answers gates v8/v9 counted as `conflict_treated_as_resolved` gave both values with
both citations; under the content rule they are status errors. Answers that drop a side, cite
one record or say one record applies stay critical. The re-score of 005-M and 005-N is not
binding: their frozen gate decisions stand.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import conflict_resolution

RUNS = {"005-M": ("mission005m", "mission005m_synthetic_acceptance.json"),
        "005-N": ("mission005n", "mission005n_synthetic_acceptance.json")}


def load(mission):
    run, suite = RUNS[mission]
    cases = {c["id"]: c for c in json.loads((BOOT / "validation" / suite).read_text())["cases"]}
    gens = {}
    for line in (BOOT / "runs" / run / "synthetic_acceptance" / "generations.jsonl").read_text().splitlines():
        record = json.loads(line)
        gens[record["case_id"]] = json.loads(record["raw_output"])
    results = json.loads((BOOT / "runs" / run / "synthetic_acceptance" / "synthetic_acceptance_results.json").read_text())
    return cases, gens, results


def verdict(mission, case_id, out=None):
    cases, gens, _ = load(mission)
    out = out or gens[case_id]
    return conflict_resolution.judge(out["status"], out["answer"], out["citations"], cases[case_id]["expected"])


@pytest.mark.parametrize("mission,case_id", [("005-M", "A05M-28"), ("005-M", "A05M-29"),
                                             ("005-N", "A05N-28"), ("005-N", "A05N-29")])
def test_both_values_with_both_citations_is_a_status_error(mission, case_id):
    assert verdict(mission, case_id) == {"result": "status_only", "reasons": []}


@pytest.mark.parametrize("mission,case_id", [("005-M", "A05M-30"), ("005-N", "A05N-30")])
def test_status_conflict_is_not_judged(mission, case_id):
    assert verdict(mission, case_id)["result"] == "not_applicable"


def test_no_conflict_expected_is_not_judged():
    assert conflict_resolution.judge("answered", "10 days.", ["X"],
                                     {"model_statuses": ["answered"], "required_mentions": [], "must_cite": []})["result"] == "not_applicable"


A28 = ["R42-EXT-PROC-11", "R42-EXT-PROC-12"]


@pytest.mark.parametrize("answer,cites,kind", [
    ("The processing time for an R-4-2 extension is within 10 days.", A28, "side_missing"),
    ("Notice 11 gives 10 days and Notice 12 gives 20 days.", A28[:1], "side_uncited"),
    ("Notice 11 gives 10 days and Notice 12 gives 20 days. Notice 12 takes precedence.", A28, "side_preferred"),
    ("Notice 11 gives 10 days, but it was superseded by Notice 12, which gives 20 days.", A28, "side_preferred"),
    ("Notice 11 gives 10 days; Notice 12 gives 20 days. You should use the 20-day period.", A28, "side_preferred"),
    ("고시 제11호는 10일, 고시 제12호는 20일입니다. 고시 제12호가 우선 적용됩니다.", A28, "side_preferred"),
    ("고시 제11호는 10일, 고시 제12호는 20일입니다. 제11호는 더 이상 적용되지 않습니다.", A28, "side_preferred"),
    ("Thông báo số 11 là 10 ngày, số 12 là 20 ngày. Thông báo số 11 không còn hiệu lực.", A28, "side_preferred"),
])
def test_picking_a_side_stays_critical(answer, cites, kind):
    out = {"status": "answered", "answer": answer, "citations": cites}
    v = verdict("005-N", "A05N-28", out)
    assert v["result"] == "resolved" and kind in [r["kind"] for r in v["reasons"]]


def test_uncertain_preference_wording_is_not_a_side():
    out = {"status": "partial", "citations": A28,
           "answer": "Notice 11 gives 10 days and Notice 12 gives 20 days. It is unclear which notice prevails."}
    assert verdict("005-N", "A05N-28", out)["result"] == "status_only"


def test_a_case_without_two_sides_fails_closed():
    v = conflict_resolution.judge("answered", "10 days and 20 days.", ["A", "B"],
                                  {"model_statuses": ["conflict"], "required_mentions": [["10"]], "must_cite": ["A", "B"]})
    assert v["result"] == "resolved" and v["reasons"][0]["kind"] == "sides_not_specified"


@pytest.mark.parametrize("mission,left", [("005-M", ["A05M-62"]), ("005-N", ["A05N-61"])])
def test_non_binding_rescore_both_missions_still_fail_on_a_suite_pattern(mission, left):
    """Applying the content rule removes only the status criticals; one suite-pattern critical remains,
    so neither frozen decision would have passed. The recorded decisions are not changed."""
    cases, gens, results = load(mission)
    remaining = []
    for row in results["cases"]:
        if not row.get("executed"):
            continue
        kinds = [c for c in row["end_to_end"]["critical"]
                 if not (c["kind"] == "conflict_treated_as_resolved" and c["detail"] in ("answered", "partial"))]
        if len(kinds) < len(row["end_to_end"]["critical"]):
            out = gens[row["case_id"]]
            v = conflict_resolution.judge(out["status"], out["answer"], out["citations"], cases[row["case_id"]]["expected"])
            if v["result"] == "resolved":
                kinds.append({"kind": "conflict_treated_as_resolved", "detail": v["reasons"]})
        if kinds:
            remaining.append(row["case_id"])
    assert remaining == left
