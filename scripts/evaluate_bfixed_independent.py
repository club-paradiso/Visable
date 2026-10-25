#!/usr/bin/env python3
"""Separate frozen synthetic validation; exits 1 on any mismatch."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from services.procedure_classifier import classify_procedure


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    fixture=ROOT/"audits/mission-002-phase-1-1/independent-procedure-cases.json"
    data=json.loads(fixture.read_text())
    results=[]
    for row in data["cases"]:
        d=classify_procedure(row["question"])
        results.append(dict(row,prediction=d.fine,candidates=list(d.candidates),reason=d.reason,correct=d.fine==row["fine"]))
    report={"fixture_sha256":hashlib.sha256(fixture.read_bytes()).hexdigest(),
            "classifier_sha256":hashlib.sha256((ROOT/"backend/services/procedure_classifier.py").read_bytes()).hexdigest(),
            "total":len(results),"passed":sum(r["correct"] for r in results),
            "label_review":data["label_review"],"results":results}
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    errors=[r["id"] for r in results if not r["correct"]]
    print(f"{report['passed']}/{report['total']} passed; mismatches: {', '.join(errors) or 'none'}")
    return bool(errors)


if __name__=="__main__":
    raise SystemExit(main())
