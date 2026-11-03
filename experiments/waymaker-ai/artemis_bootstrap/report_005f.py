"""Mission 005-F analysis: keep every measurement apart.

  A  Mission 005-D v1 baseline           005-D outputs, 005-E evaluator (frozen numbers)
  B  Mission 005-E v2 baseline           005-E outputs, 005-E evaluator (frozen numbers)
  B' Evaluator-only (005-F evaluator)    the same 005-D / 005-E outputs, rescored now
  C  Mission 005-F synthetic acceptance  the locked synthetic cases, the gate decision
  D  Mission 005-F v3 DEV-20             only if the gate passed; otherwise not_executed

Language compliance and claim-support consistency are separate, versioned metrics.
They are never folded into the historical four-dimension diagnostic score. For
DEV-20, admissible evidence means approval_state approved or under_review (the
evaluator-side record); supersession is not encoded there.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BOOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BOOT.parent))
sys.path.insert(0, str(BOOT))
import claim_support_validation
import language_compliance
import score_dev20

ADMISSIBLE_STATES = ("approved", "under_review")
RUNS = {"mission005d_v1": BOOT / "runs" / "mission005d-dev20",
        "mission005e_v2": BOOT / "runs" / "mission005e" / "dev20_contract_v2"}


def supplementary(run_dir: Path) -> dict:
    """Language compliance and claim support per DEV-20 case, reported apart from the diagnostic score."""
    items = {i["id"]: i for i in score_dev20.load_dev_items()[0]}
    rows = []
    for g in score_dev20.read_jsonl(run_dir / "generations.jsonl"):
        item = items[g["case_id"]]
        resp = g.get("response") or {}
        answer, cites = resp.get("answer") or "", resp.get("citations") or []
        admissible = {e["id"]: e["source"].get("approval_state") in ADMISSIBLE_STATES for e in item["evidence"]}
        version = g.get("contract_version", "v1")
        # v1 asked for Korean whatever the question; v2 and v3 ask for the question's language.
        required = "ko" if version == "v1" else None
        lang = language_compliance.check(item["question"], answer, required)
        support = claim_support_validation.check(answer, item["question"], item["evidence"], cites, admissible)
        rows.append({"case_id": g["case_id"], "contract_version": version, "language": lang["result"],
                     "required_language": lang["required"]["language"], "language_reason": lang["reason"],
                     "claim_support": support["result"], "claim_support_findings": support["findings"]})
    return {"cases": rows,
            "language_compliance": dict(Counter(r["language"] for r in rows)),
            "claim_support": dict(Counter(r["claim_support"] for r in rows)),
            "claim_support_contradictions": [r["case_id"] for r in rows if r["claim_support"] == "contradiction"]}


def evaluator_only(run_dir: Path, frozen: dict) -> dict:
    result = score_dev20.score(run_dir)
    m = result["metrics"]
    now = {"diagnostic_candidate_pass": m["diagnostic_candidate_pass"], "dimension_pass": m["dimension_pass"]}
    codes = {c["case_id"]: c["failure_codes"] for c in result["cases"]}
    return {"frozen_005e_evaluator": {k: frozen[k] for k in ("diagnostic_candidate_pass", "dimension_pass")},
            "evaluator_005f": now, "failure_codes_005f": codes,
            "outcome_changed": now["diagnostic_candidate_pass"] != frozen["diagnostic_candidate_pass"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--acceptance-dir", type=Path, default=None)
    parser.add_argument("--v3-dev20-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    freeze = json.loads((BOOT / "runs" / "mission005f" / "baseline_freeze.json").read_text())
    report = {"schema_version": "waymaker-artemis-005f-analysis/1.0",
              "labels": {"A": "Mission 005-D v1 baseline", "B": "Mission 005-E v2 baseline",
                         "B_prime": "Evaluator-only rescoring with the 005-F evaluator",
                         "C": "Mission 005-F synthetic acceptance", "D": "Mission 005-F v3 DEV-20"},
              "A": freeze["metrics"]["mission005d_v1_dev20_evaluator_005e"],
              "B": freeze["metrics"]["mission005e_v2_dev20_evaluator_005e"],
              "B_prime": {"mission005d_v1": evaluator_only(RUNS["mission005d_v1"], freeze["metrics"]["mission005d_v1_dev20_evaluator_005e"]),
                          "mission005e_v2": evaluator_only(RUNS["mission005e_v2"], freeze["metrics"]["mission005e_v2_dev20_evaluator_005e"])},
              "supplementary_metrics_dev20": {name: supplementary(path) for name, path in RUNS.items()},
              "official_gold_accuracy": None, "independent_legal_review": "not_verified"}
    if args.acceptance_dir:
        acc = json.loads((args.acceptance_dir / "synthetic_acceptance_results.json").read_text())
        decision = json.loads((args.acceptance_dir / "gate_decision.json").read_text())
        report["C"] = {"summary": acc["summary"], "decision": decision["decision"],
                       "fail_reasons": decision["fail_reasons"], "blocked_reasons": decision["blocked_reasons"]}
    if args.v3_dev20_dir and (args.v3_dev20_dir / "generations.jsonl").exists():
        result = score_dev20.score(args.v3_dev20_dir)
        report["D"] = {"metrics": result["metrics"], "integrity_passed": result["integrity"]["passed"],
                       "supplementary": supplementary(args.v3_dev20_dir)}
    else:
        report["D"] = {"status": "not_executed",
                       "reason": "DEV-20 runs only after a passing synthetic acceptance gate. Missing output is not zero accuracy."}
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"C": (report.get("C") or {}).get("decision"), "D": report["D"].get("status", "executed"),
                      "supp": {k: (v["language_compliance"], v["claim_support"]) for k, v in report["supplementary_metrics_dev20"].items()}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
