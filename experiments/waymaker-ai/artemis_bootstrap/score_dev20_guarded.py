"""Score a DEV-20 run through the guarded pipeline: what a user would receive, item by item.

run_dev20 (gates v2-v12) records pipeline.jsonl: the pre-inference outcome under the real-world registry,
the guard's decision and the released response. This script scores the RELEASED response of every item
with artemis_eval as it stands (the rubrics and expected answers are not changed) and keeps apart
the items the registry or pre-inference withheld before the model and the items the model answered.

The DEV-20 expected answers were written with each item's own evidence text taken as true. Where the
real-world registry rejected or left out that evidence, the system withholds by design, and a rubric
that expects an answer counts it as a miss; the report states why each item was withheld.
Results are Development Candidate Diagnostic Performance, never Official Gold Accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

BOOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BOOT.parent))
sys.path.insert(0, str(BOOT))
import artemis_eval
from run_dev20_cuda import load_dev_items

DIMENSIONS = ("source_fidelity", "citation_accuracy", "procedural_integrity", "abstention_appropriateness")


def read_jsonl(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def released_response(record: dict) -> dict:
    """The released response as the user sees it: the model's answer plus any system notice."""
    released = dict(record["released"])
    if released.get("system_notice"):
        released["answer"] = (released.get("answer") or "") + " " + released["system_notice"]
    return {k: released.get(k) for k in ("status", "answer", "citations")}


def score(out_dir: Path) -> dict:
    items, dataset_sha = load_dev_items()
    pipe_path = Path(out_dir) / "pipeline.jsonl"
    records = {r["case_id"]: r for r in read_jsonl(pipe_path)}
    if set(records) != {i["id"] for i in items}:
        raise ValueError("pipeline.jsonl does not cover exactly the 20 DEV-20 items")
    cases = []
    for item in items:
        rec = records[item["id"]]
        result = artemis_eval.score_artemis_response(item, released_response(rec), allow_candidate_sources=True)
        cases.append({
            "case_id": item["id"], "title": item.get("title"),
            "pre_inference": rec["pre_inference"], "pre_inference_reason": rec.get("pre_inference_reason"),
            "evidence_decisions": {d["evidence_id"]: d["reason"] for d in rec.get("trust_decisions") or []},
            "model_called": rec["model_called"], "guard": (rec.get("guard") or {}).get("decision"),
            "language_retry": bool(rec.get("language_retry")), "released_provenance": rec["released_provenance"],
            "released_status": rec["released"].get("status"), "expected_statuses": item["expected"].get("allowed_statuses"),
            "passed": result.overall_passed,
            "dimensions": {d: result.dimension_scores[d].passed for d in DIMENSIONS},
            "failures": list(result.all_failures),
        })
    called = [c for c in cases if c["model_called"]]
    withheld = [c for c in cases if not c["model_called"]]
    return {
        "label": "DEV-20 through the guarded pipeline with the real-world registry (Development Candidate Diagnostic, "
                 "not Official Gold Accuracy)",
        "dataset_sha256": dataset_sha, "pipeline_sha256": hashlib.sha256(pipe_path.read_bytes()).hexdigest(),
        "summary": {
            "items": len(cases), "model_called": len(called), "withheld_before_model": len(withheld),
            "passed_all_dimensions": sum(c["passed"] for c in cases),
            "passed_among_model_called": sum(c["passed"] for c in called),
            "passed_among_withheld": sum(c["passed"] for c in withheld),
            "released_provenance": dict(Counter(c["released_provenance"] for c in cases)),
            "guard_decisions": dict(Counter(c["guard"] for c in called)),
            "dimension_passes": {d: sum(c["dimensions"][d] for c in cases) for d in DIMENSIONS},
            "withheld_reasons": dict(Counter(c["pre_inference_reason"] for c in withheld)),
        },
        "cases": cases,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    result = score(args.out_dir)
    (args.out_dir / "dev20_guarded_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                                                             encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
