#!/usr/bin/env python3
"""Auditable before/after report from untouched evaluator output; no rescoring."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = {k: json.loads(getattr(args,k).read_text()) for k in ("main","before","after")}
    digest = raw["main"]["benchmark"]["digest"]
    assert all(x["benchmark"]["digest"] == digest for x in raw.values()), "benchmark changed"
    configs = {"B1":("main","b1_python"), "B2":("main","b2_js"),
               "B_fixed_before":("before","b_fixed"), "B_fixed_after":("after","b_fixed")}
    systems = {}
    records = {}
    for name, (run, baseline) in configs.items():
        report = raw[run]
        systems[name] = {
            "headline": report["headline"][baseline],
            "critical_errors": report["critical_legal_errors"][baseline],
            "gates": report["gates"][baseline],
            "scoring_digest": report["scoring_digest"],
            "input_report_sha256": hashlib.sha256(getattr(args,run).read_bytes()).hexdigest(),
        }
        records[name] = {r["id"]:r for r in report["items"][baseline] if r["task"]=="status_procedure_classification"}
        assert all(r["status"]=="ok" for r in records[name].values()), "baseline did not run"
    root = Path(__file__).resolve().parents[1]
    examples = {r["id"]:r for r in map(json.loads,(root/"experiments/waymaker-ai/datasets/benchmark/v0/classification.jsonl").read_text().splitlines())}
    rows = []
    for key in records["B_fixed_after"]:
        item = examples[key]
        views = {n: {"prediction":r[key]["prediction"], "metrics":r[key]["metrics"],
                     "verdict":r[key]["verdict"], "critical_categories":r[key]["critical_categories"]} for n,r in records.items()}
        before = views["B_fixed_before"]["metrics"]["procedure_fine"][0]
        after = views["B_fixed_after"]["metrics"]["procedure_fine"][0]
        rows.append({"id":key,"split":item["split"],"question":item["input"]["question"],
                     "expected":item["expected"],"critical_label":item.get("critical",False),
                     "views":views,"procedure_change":"fixed" if before=="wrong" and after=="correct" else
                        "regression" if before=="correct" and after=="wrong" else "unchanged"})
    report = {
        "schema_version":"phase11-comparison/1","benchmark_digest":digest,
        "reference_main":"0d6171a0df1c3f4f48d3c4dffc8f13b9ab7e0752",
        "before_commit":"631f8575415418888ef0216efb4f1415200dcfd3",
        "splits":["dev","test"],"label_scope":"unreviewed linguistic labels, not legal correctness",
        "post_hoc":True,"systems":systems,
        "implementation_hashes":{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in (
            "backend/services/procedure_classifier.py","backend/data/procedure_classifier_lexicon.json",
            "backend/services/status_code_parser.py","backend/services/knowledge/understanding.py")},
        "procedure_changes":{split:{k:sum(r["split"]==split and r["procedure_change"]==k for r in rows)
            for k in ("fixed","regression","unchanged")} for split in ("dev","test")},
        "items":rows,
    }
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"comparison.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    lines = ["# v0 項目別比較 / 항목별 비교", "",
             "기존 evaluator의 판정을 그대로 옮겼다. 라벨은 사람 검증 전이며 법적 정확성 판정이 아니다.",
             "dev/test는 이미 노출된 사후 비교다. 실패·미출력 항목은 JSON에 모두 남긴다.", "",
             "| 항목 | split | 기대 절차 | 기존 B-fixed | 개선 B-fixed | B2 | 변화 |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        pred=lambda n: r["views"][n]["prediction"].get("procedure_fine") or "—"
        lines.append("| "+" | ".join([r["id"],r["split"],r["expected"].get("procedure") or "—",pred("B_fixed_before"),pred("B_fixed_after"),pred("B2"),r["procedure_change"]])+" |")
    (args.output/"per-item-comparison.ko.md").write_text("\n".join(lines)+"\n")
    print(json.dumps(report["procedure_changes"],ensure_ascii=False))


if __name__ == "__main__":
    main()
