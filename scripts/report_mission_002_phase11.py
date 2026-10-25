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
    risk_lines = [
        "# 중요 라벨 사례별 잠재 위험 검토", "",
        "v0 라벨의 오류이며 실제 법적 오답이나 위해 발생을 인적으로 확정한 표가 아니다.",
        "모든 기준선에서 중요 오류로 표시된 사례의 합집합을 포함한다. B1의 fine 미출력은 오류로 추가하지 않는다.", "",
        "| 분류 | 잠재 영향 |",
        "|---|---|",
        "| H-identity | 잘못된 자격·세부 자격·존재성으로 요건과 서류를 선택할 위험 |",
        "| H-direction | 현재·목표 자격을 혼동해 전환 경로를 잘못 안내할 위험 |",
        "| H-domain | 체류와 사증발급 절차를 섞어 담당 기관·신청 경로를 잘못 안내할 위험 |",
        "| M-procedure | 같은 도메인에서 절차나 신고 유형을 놓쳐 서류·기한·접수 흐름을 잘못 제시할 위험 |",
        "| M-clarify | 필요한 확인을 생략하거나 불필요한 확인을 요구할 위험 |", "",
        "| 사례 | 기준선별 틀린 항목 | 위험 분류 | 개선판 잔여 중요 오류 |",
        "|---|---|---|---|",
    ]
    for r in rows:
        if not any(v["critical_categories"] for v in r["views"].values()):
            continue
        failures_by_system=[]
        risks=set()
        for name, v in r["views"].items():
            if not v["critical_categories"]:
                continue
            wrong=[k for k,m in v["metrics"].items() if m[0]=="wrong"]
            failures_by_system.append(name+": "+", ".join(wrong))
            if set(wrong)&{"status_exact","subcode_exact","subcode_expected_absent","not_status_token_respected"}: risks.add("H-identity")
            if set(wrong)&{"current_status_exact","target_status_exact"}: risks.add("H-direction")
            if "procedure_scope_respected" in wrong: risks.add("H-domain")
            if set(wrong)&{"procedure_fine","procedure_coarse"}: risks.add("M-procedure")
            if "clarification" in wrong: risks.add("M-clarify")
        residual="잔여" if r["views"]["B_fixed_after"]["critical_categories"] else "해소(v0 라벨 기준)"
        risk_lines.append("| "+" | ".join([r["id"],"; ".join(failures_by_system),", ".join(sorted(risks)),residual])+" |")
    (args.output/"critical-risk-review.ko.md").write_text("\n".join(risk_lines)+"\n")
    print(json.dumps(report["procedure_changes"],ensure_ascii=False))


if __name__ == "__main__":
    main()
