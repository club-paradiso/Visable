"""Mission 005-E measurement decomposition: keep evaluator effects apart from contract effects.

  A  Original DEV-20 baseline       005-D outputs, original evaluator (frozen numbers)
  B  Evaluator-only rescoring       005-D outputs, repaired evaluator (no regeneration)
  C  Contract-v2 model re-evaluation  005-E v2 outputs, repaired evaluator
  C_legacy                           005-E v2 outputs, original evaluator (separates the
                                     contract effect from the evaluator effect)

The original evaluator is loaded from the baseline commit in a separate process so
the two evaluators never share module state. Needs git history; the outputs are
committed and checked by tests. Development candidate diagnostics only.
"""
import argparse
import csv
import json
import math
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

BOOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BOOT.parent))
sys.path.insert(0, str(BOOT))
import score_dev20

BASELINE_COMMIT = "80445349d6a9820998e3ef9b17f7d73a9eaec125"
LEGACY_FILES = ("artemis_bootstrap/artemis_eval.py", "artemis_bootstrap/trust_gate.py")
LABELS = {"A": "Original DEV-20 baseline", "B": "Evaluator-only rescoring",
          "C": "Contract-v2 model re-evaluation", "C_legacy": "Contract-v2 outputs, original evaluator"}
CITATION_CODES = ("unlisted_citations", "forbidden_citations", "unapproved_citations", "missing_citations",
                  "unknown_citation_ids")


def legacy_score(run_dir: Path) -> dict:
    """Score run_dir with artemis_eval/trust_gate as of BASELINE_COMMIT, in a subprocess."""
    repo = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=BOOT, capture_output=True,
                               text=True, check=True).stdout.strip())
    with tempfile.TemporaryDirectory() as tmp:
        for rel in LEGACY_FILES:
            blob = subprocess.run(["git", "show", f"{BASELINE_COMMIT}:experiments/waymaker-ai/{rel}"], cwd=repo,
                                  capture_output=True, check=True).stdout
            (Path(tmp) / Path(rel).name).write_bytes(blob)
        code = ("import sys, json; sys.path[:0] = [sys.argv[1], sys.argv[2], sys.argv[3]]; "
                "import artemis_eval, score_dev20; assert artemis_eval.__file__.startswith(sys.argv[1]); "
                "r = score_dev20.score(__import__('pathlib').Path(sys.argv[4])); "
                "print(json.dumps({'metrics': r['metrics'], 'cases': r['cases'], 'integrity': r['integrity']}, default=str))")
        out = subprocess.run([sys.executable, "-c", code, tmp, str(BOOT), str(BOOT.parent), str(run_dir)],
                             capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def summarize(cases: list, metrics: dict) -> dict:
    statuses = Counter(c["generated_outcome"]["status"] for c in cases)
    codes = Counter(f for c in cases for f in c["failure_codes"])
    return {"diagnostic_candidate_pass": metrics["diagnostic_candidate_pass"], "dimension_pass": metrics["dimension_pass"],
            "json_contract_pass": metrics["json_contract_pass"], "status_distribution": dict(statuses),
            "partial_where_only_answered_allowed": metrics["partial_where_only_answered_allowed"],
            "cases_with_citation_failure_codes": sum(1 for c in cases if set(c["failure_codes"]) & set(CITATION_CODES)),
            "citation_failure_code_counts": {k: codes[k] for k in CITATION_CODES if codes[k]},
            "failure_code_frequency": dict(codes.most_common()),
            "token_limit_truncation": metrics["token_limit_truncation"],
            "review_annotations": {c["case_id"]: c["review_annotation"]["reason"] for c in cases if c.get("review_annotation")}}


def paired(before: dict, after: dict) -> str:
    """Per case: improved / regressed / unchanged / indeterminate (failure sets overlap both ways)."""
    if before is None or after is None:
        return "indeterminate"
    b, a = set(before["failure_codes"]), set(after["failure_codes"])
    if before["diagnostic_outcome"] == "fail" and after["diagnostic_outcome"] == "pass":
        return "improved"
    if before["diagnostic_outcome"] == "pass" and after["diagnostic_outcome"] == "fail":
        return "regressed"
    if a == b:
        return "unchanged"
    if a < b:
        return "improved_fewer_failures"
    if b < a:
        return "regressed_more_failures"
    return "indeterminate_changed_failures"


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list:
    """95% Wilson score interval for k successes out of n."""
    if n == 0:
        return [None, None]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(centre - half, 4), round(centre + half, 4)]


def mcnemar_exact(before: dict, after: dict) -> dict:
    """Exact two-sided McNemar test on pass/fail pairs (binomial on the discordant cases)."""
    keys = sorted(set(before) & set(after))
    gained = sum(1 for k in keys if before[k] == "fail" and after[k] == "pass")
    lost = sum(1 for k in keys if before[k] == "pass" and after[k] == "fail")
    n = gained + lost
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(gained, lost) + 1)) / 2 ** n)
    return {"fail_to_pass": gained, "pass_to_fail": lost, "discordant": n, "exact_p_two_sided": round(p, 6)}


def statistics(outcomes: dict) -> dict:
    """Intervals and paired tests over per-case pass/fail maps keyed by label."""
    n = len(outcomes["A"])
    passes = {k: sum(1 for v in o.values() if v == "pass") for k, o in outcomes.items()}
    c_pass = [k for k, v in outcomes["C"].items() if v == "pass"]
    return {"n": n, "wilson_95": {k: {"passed": passes[k], "interval": wilson(passes[k], n)} for k in outcomes},
            "mcnemar_A_to_B": mcnemar_exact(outcomes["A"], outcomes["B"]),
            "mcnemar_B_to_C": mcnemar_exact(outcomes["B"], outcomes["C"]),
            "mcnemar_C_legacy_to_C": mcnemar_exact(outcomes["C_legacy"], outcomes["C"]),
            "c_pass_attribution": {
                "passes_with_original_evaluator": sorted(k for k in c_pass if outcomes["C_legacy"][k] == "pass"),
                "passes_only_with_repaired_evaluator": sorted(k for k in c_pass if outcomes["C_legacy"][k] != "pass")},
            "caveats": ["20 development cases; intervals are wide and the cases are not a random sample.",
                        "Contract v2 was written after reading the Mission 005-D DEV-20 failures, so C on DEV-20 is "
                        "an optimistic, in-sample estimate; the synthetic set is the out-of-sample check.",
                        "Exact tests assume independent cases; DEV-20 items share templates and evidence styles."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    freeze = json.loads((BOOT / "runs" / "mission005e" / "baseline_freeze.json").read_text())
    b = score_dev20.score(BOOT / "runs" / "mission005d-dev20")
    c = score_dev20.score(args.v2_dir)
    cl = legacy_score(args.v2_dir)
    a_cases = {cid: {"diagnostic_outcome": v["diagnostic"], "failure_codes": v["failure_codes"]}
               for cid, v in freeze["case_outcomes"].items()}
    b_cases = {x["case_id"]: x for x in b["cases"]}
    c_cases = {x["case_id"]: x for x in c["cases"]}
    l_cases = {x["case_id"]: x for x in cl["cases"]}
    comparison = {
        "schema_version": "waymaker-artemis-005e-comparison/1.0", "labels": LABELS,
        "official_gold_accuracy": None, "independent_legal_review": "not_verified",
        "A": {"label": LABELS["A"], "source": "baseline_freeze.json", "metrics": freeze["metrics"],
              "status_distribution": freeze["status_distribution"]},
        "B": {"label": LABELS["B"], **summarize(b["cases"], b["metrics"]), "integrity_passed": b["integrity"]["passed"]},
        "C": {"label": LABELS["C"], **summarize(c["cases"], c["metrics"]), "integrity_passed": c["integrity"]["passed"]},
        "C_legacy": {"label": LABELS["C_legacy"], **summarize(cl["cases"], cl["metrics"])},
        "paired_A_to_B": dict(Counter(paired(a_cases[k], b_cases.get(k)) for k in a_cases)),
        "paired_B_to_C": dict(Counter(paired(b_cases[k], c_cases.get(k)) for k in b_cases)),
        "paired_A_to_C": dict(Counter(paired(a_cases[k], c_cases.get(k)) for k in a_cases)),
        "statistics": statistics({
            "A": {k: v["diagnostic_outcome"] for k, v in a_cases.items()},
            "B": {k: v["diagnostic_outcome"] for k, v in b_cases.items()},
            "C": {k: v["diagnostic_outcome"] for k, v in c_cases.items()},
            "C_legacy": {k: v["diagnostic_outcome"] for k, v in l_cases.items()}}),
        "notes": ["B differs from A only by evaluator repairs E1-E3; the model outputs are identical.",
                  "C differs from B by the contract (prompt v2) on the same checkpoint and dataset.",
                  "C_legacy scores C's outputs with the original evaluator to separate the two effects.",
                  "A diagnostic score change is not evidence of legal accuracy."]}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "score_comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n")
    with (args.out_dir / "case_level_comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        w = csv.writer(stream, lineterminator="\n")
        w.writerow(["case_id", "A_status", "A_outcome", "A_failures", "B_outcome", "B_failures", "C_status",
                    "C_outcome", "C_failures", "C_legacy_outcome", "A_to_B", "B_to_C", "A_to_C"])
        for cid in sorted(a_cases):
            bb, cc, ll = b_cases.get(cid), c_cases.get(cid), l_cases.get(cid)
            w.writerow([cid, bb["generated_outcome"]["status"] if bb else "", a_cases[cid]["diagnostic_outcome"],
                        "|".join(a_cases[cid]["failure_codes"]), bb["diagnostic_outcome"] if bb else "",
                        "|".join(bb["failure_codes"]) if bb else "",
                        cc["generated_outcome"]["status"] if cc else "", cc["diagnostic_outcome"] if cc else "",
                        "|".join(cc["failure_codes"]) if cc else "", ll["diagnostic_outcome"] if ll else "",
                        paired(a_cases[cid], bb), paired(bb, cc), paired(a_cases[cid], cc)])
    print(json.dumps({k: comparison[k]["diagnostic_candidate_pass"] if k != "A" else comparison["A"]["metrics"]["diagnostic_candidate_pass"]
                      for k in ("A", "B", "C", "C_legacy")}))


if __name__ == "__main__":
    main()
