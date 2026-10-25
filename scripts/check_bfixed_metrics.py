#!/usr/bin/env python3
"""Engineering non-regression gate. Never a legal or deployment approval."""
import json
import sys
from pathlib import Path


def failures(current, previous):
    out = []
    if current["benchmark"]["digest"] != previous["benchmark_digest"]:
        return ["benchmark digest changed; review the gate against the new dataset"]
    fixed = current["headline"].get("b_fixed", {})
    b2 = current["headline"].get("b2_js", {})
    floor = previous["systems"]["B_fixed_before"]["headline"]
    for split in ("dev","test"):
        comparisons = [("procedure_fine_accuracy", b2.get(split, {}))]
        comparisons += [(k, floor.get(split, {})) for k in (
            "status_exact_accuracy","subcode_accuracy_subcode_expected",
            "current_status_accuracy","target_status_accuracy")]
        for key, reference in comparisons:
            key = "classification."+key
            a, b = fixed.get(split,{}).get(key,{}), reference.get(key,{})
            if not a.get("denominator") or a.get("denominator") != b.get("denominator"):
                out.append(f"{split} {key}: unavailable or denominator mismatch")
            elif a["numerator"] < b["numerator"]:
                out.append(f"{split} {key}: regression {a['numerator']} < {b['numerator']}")
    for name in ("b_fixed","b2_js"):
        if not current.get("baselines",{}).get(name,{}).get("available"):
            out.append(f"{name}: baseline unavailable")
        rows = [r for r in current.get("items",{}).get(name,[]) if r["task"]=="status_procedure_classification"]
        if not rows:
            out.append(f"{name}: no classification items")
        for row in rows:
            if row["task"]=="status_procedure_classification" and row["status"]!="ok":
                out.append(f"{name} {row['id']}: baseline did not run")
    return out


if __name__ == "__main__":
    current=json.loads(Path(sys.argv[1]).read_text())
    previous=json.loads(Path(sys.argv[2]).read_text())
    errors=failures(current,previous)
    print("\n".join(errors) if errors else "PASS: fine procedure >= B2; code and transition metrics preserved. Legal/release gate remains separate.")
    sys.exit(bool(errors))
