"""Mission 005-D: score recorded dev-20 generations offline and write the evidence artifacts.

Runs after generation, never inside it. Inputs are generations.jsonl and
sessions.jsonl written by run_dev20_cuda.py. The scoring is artemis_eval as it
stands; this script does not change rubrics or expected answers. Results are
Development Candidate Diagnostic Performance, never Official Gold Accuracy.

Root-cause labels are an analyst's judgement, kept in root_cause_annotations.json
and merged in as such; they are not computed here.
"""
import argparse
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

BOOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BOOT.parent))
sys.path.insert(0, str(BOOT))
import artemis_eval
from run_dev20_cuda import input_sha256, load_dev_items, load_synthetic_items, prompt_messages, sha256_text
from waymaker_ai.response_contract import parse_response
import trust_gate
from waymaker_ai import cuda_policy
from waymaker_ai.inference_input import project_inference_item

DIMENSIONS = ("source_fidelity", "citation_accuracy", "procedural_integrity", "abstention_appropriateness")
GENERATED = {"completed", "generated_but_invalid"}
# Keys and values that exist only on the evaluator side of the dataset.
EVALUATOR_ONLY_KEYS = frozenset({"expected", "allowed_statuses", "must_cite", "forbidden_claims", "required_facts",
                                 "legal_review_notes", "candidate_status", "approval_state", "review_status",
                                 "reviewed_by", "reviewed_at", "approved_sha256", "content_sha256", "metadata",
                                 "user_context", "needs_human_review", "dimension", "title_of_case"})
EVALUATOR_ONLY_VALUES = frozenset({"injection_probe", "synthetic_fixture"})
NOT_EXECUTED_RESPONSE = {"status": "error", "answer": "", "citations": []}


def read_jsonl(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def failure_code(text: str) -> str:
    """'[citation_accuracy] missing_citations:EV-1' -> 'missing_citations'."""
    return text.split("] ", 1)[-1].split(":", 1)[0]


def rubric_strings(item: dict) -> list:
    exp = item.get("expected") or {}
    fid, proc = exp.get("source_fidelity") or {}, exp.get("procedural_integrity") or {}
    values = list(fid.get("forbidden_claims") or []) + list(proc.get("forbidden_procedures") or [])
    if proc.get("expected_procedure"):
        values.append(proc["expected_procedure"])
    return [v for v in values if isinstance(v, str) and v]


_VI_RE = __import__("re").compile(r"[ăâđêôơưĂÂĐÊÔƠƯạảãáàặẳẵắằậẩẫấầẹẻẽéèệểễếềịỉĩíìọỏõóòộổỗốồợởỡớờụủũúùựửữứừỳỷỹýỵ]")
_HANGUL_RE = __import__("re").compile(r"[가-힣]")


def text_language(text: str) -> str:
    """Coarse script-based guess: ko, vi, en or unknown. Deterministic, not a classifier."""
    if _HANGUL_RE.search(text):
        return "ko"
    if _VI_RE.search(text):
        return "vi"
    if __import__("re").search(r"[A-Za-z]{3,}", text):
        return "en"
    return "unknown"


def language_review(item: dict, version: str) -> dict | None:
    """E4: flag a rubric whose required facts assume a response language the contract does not ask for.

    Annotation only; it never changes a pass or fail. v1 asks for Korean; v2 asks for the
    question's language.
    """
    facts = (item.get("expected") or {}).get("source_fidelity", {}).get("required_facts") or []
    rubric = {text_language(f) for f in facts} - {"unknown"}
    expected = "ko" if version == "v1" else text_language(item["question"])
    if expected == "unknown":
        expected = "ko"
    if rubric and rubric != {expected}:
        return {"review_required": True, "reason": "rubric_language_mismatch", "contract_version": version,
                "contract_response_language": expected, "rubric_fact_languages": sorted(rubric)}
    return None


def leakage_findings(item: dict, version: str = "v1") -> list:
    """Rubric text or evaluator-only keys/labels that reach the prompt but are not in the item's question/evidence."""
    prompt = json.dumps(prompt_messages(item, version), ensure_ascii=False)
    visible = item["question"] + "".join(e.get("title", "") + e.get("text", "") for e in item["evidence"])
    found = [f"rubric_text:{s}" for s in rubric_strings(item) if s in prompt and s not in visible]
    keys, values = set(), set()

    def walk(node):
        if isinstance(node, dict):
            keys.update(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            values.add(node)
    walk(project_inference_item(item))
    found += [f"evaluator_key:{k}" for k in sorted(keys & EVALUATOR_ONLY_KEYS)]
    found += [f"evaluator_label:{v}" for v in sorted(values & EVALUATOR_ONLY_VALUES)]
    return found


def rate(numerator: int, denominator: int):
    return {"numerator": numerator, "denominator": denominator,
            "rate": round(numerator / denominator, 4) if denominator else None}


def score(out_dir: Path) -> dict:
    items, dataset_sha = load_dev_items()
    by_id = {i["id"]: i for i in items}
    gen_path, ses_path = out_dir / "generations.jsonl", out_dir / "sessions.jsonl"
    generations = read_jsonl(gen_path)
    sessions = read_jsonl(ses_path)
    counts = Counter(g["case_id"] for g in generations)
    if any(n > 1 for n in counts.values()) or not set(counts) <= set(by_id):
        raise ValueError("Duplicate or unknown case IDs in generations.jsonl")
    gens = {g["case_id"]: g for g in generations}
    annotations_path = out_dir / "root_cause_annotations.json"
    annotations = json.loads(annotations_path.read_text(encoding="utf-8")) if annotations_path.exists() else {}

    integrity = {"dataset_sha256": dataset_sha, "dataset_matches_isolation_manifest": True,
                 "heldout_used": False, "generations_sha256": hashlib.sha256(gen_path.read_bytes()).hexdigest(),
                 "sessions_sha256": hashlib.sha256(ses_path.read_bytes()).hexdigest(),
                 "sessions": len(sessions), "model_loads": sum(1 for s in sessions if s.get("model_loaded")),
                 "input_hash_mismatches": [], "raw_output_hash_mismatches": [], "prompt_leakage": {},
                 "session_provenance_checks": []}
    for s in sessions:
        meta = {**(s.get("metadata") or {}), "adapter_type": "cuda_transformers"}
        try:
            cuda_policy.validate_real_inference_metadata(meta)
            integrity["session_provenance_checks"].append({"session_id": s["session_id"], "passed": True})
        except ValueError as exc:
            integrity["session_provenance_checks"].append({"session_id": s["session_id"], "passed": False, "error": str(exc)})

    cases, error_rows = [], []
    for item in items:
        cid = item["id"]
        gen = gens.get(cid)
        version = (gen or {}).get("contract_version", "v1")
        leaks = leakage_findings(item, version)
        if leaks:
            integrity["prompt_leakage"][cid] = leaks
        exp = item["expected"]
        if gen is None:
            status_exec, response = "not_executed", NOT_EXECUTED_RESPONSE
        else:
            status_exec = gen["execution_status"]
            if gen["input_sha256"] != input_sha256(item, version):
                integrity["input_hash_mismatches"].append(cid)
            raw = gen.get("raw_output")
            if isinstance(raw, str) and gen.get("raw_output_sha256") != sha256_text(raw):
                integrity["raw_output_hash_mismatches"].append(cid)
            response = gen["response"] if status_exec == "completed" else NOT_EXECUTED_RESPONSE
        result = artemis_eval.score_artemis_response(item, response, allow_candidate_sources=True)
        dims = {d: {"passed": result.dimension_scores[d].passed,
                    "failures": list(result.dimension_scores[d].failures)} for d in DIMENSIONS}
        failures = [failure_code(f) for f in result.all_failures]
        for f in result.all_failures:
            error_rows.append({"case_id": cid, "dimension": f.split("]", 1)[0].strip("["),
                               "failure_code": failure_code(f), "detail": f.split("] ", 1)[-1]})
        metrics = (gen or {}).get("metrics") or {}
        cases.append({
            "case_id": cid, "title": item.get("title"), "rubric_dimension": item.get("dimension"),
            "model_status": status_exec,
            "contract_valid": status_exec == "completed",
            "diagnostic_outcome": "pass" if result.overall_passed else "fail",
            "expected_candidate_outcome": {"allowed_statuses": exp.get("allowed_statuses"),
                                           "should_withhold": exp["abstention_appropriateness"].get("should_withhold"),
                                           "must_clarify": exp["procedural_integrity"].get("must_clarify"),
                                           "must_cite": exp["citation_accuracy"].get("must_cite")},
            "generated_outcome": {"status": (gen or {}).get("response", {}).get("status") if gen and gen.get("response") else None,
                                  "citations": (gen or {}).get("response", {}).get("citations") if gen and gen.get("response") else None},
            "citation_result": "pass" if dims["citation_accuracy"]["passed"] else "fail",
            "source_fidelity_result": "pass" if dims["source_fidelity"]["passed"] else "fail",
            "dimensions": dims,
            "primary_failure_category": failures[0] if failures else None,
            "failure_codes": failures,
            "latency_seconds": metrics.get("wall_seconds"),
            "first_token_seconds": metrics.get("first_token_seconds_including_prefill"),
            "decode_tokens_per_second": metrics.get("decode_tokens_per_second"),
            "prompt_tokens": (gen or {}).get("prompt_tokens"),
            "generated_tokens": (gen or {}).get("generated_token_count"),
            "finish_reason": (gen or {}).get("finish_reason"),
            "peak_allocated_bytes": metrics.get("peak_allocated_bytes"),
            "peak_reserved_bytes": metrics.get("peak_reserved_bytes"),
            "raw_output_ref": f"raw_inference.json#{cid}" if gen else None,
            "raw_output_sha256": (gen or {}).get("raw_output_sha256"),
            "input_sha256": (gen or {}).get("input_sha256"),
            "session_id": (gen or {}).get("session_id"),
            "root_cause": annotations.get(cid),
            "contract_version": version,
            "review_annotation": language_review(item, version),
        })

    n = len(items)
    executed = [c for c in cases if c["model_status"] in GENERATED]
    scored = [c for c in cases if c["model_status"] != "not_executed"]
    withhold = [c for c in cases if c["expected_candidate_outcome"]["should_withhold"]]
    forbid = [c for c in cases if by_id[c["case_id"]]["expected"]["abstention_appropriateness"].get("forbid_withholding")]
    answered_only = [c for c in cases if c["expected_candidate_outcome"]["allowed_statuses"] == ["answered"]]
    latencies = [c["latency_seconds"] for c in executed if c["latency_seconds"] is not None]
    metrics = {
        "label": "Development Candidate Diagnostic Performance",
        "official_gold_accuracy": None,
        "executed_cases": rate(len(executed), n),
        "inference_completion": rate(sum(1 for c in cases if (c["generated_tokens"] or 0) > 0), n),
        "json_contract_pass": rate(sum(1 for c in cases if c["contract_valid"]), n),
        "json_contract_pass_among_generated": rate(sum(1 for c in executed if c["contract_valid"]), len(executed)),
        "diagnostic_candidate_pass": rate(sum(1 for c in cases if c["diagnostic_outcome"] == "pass"), n),
        "dimension_pass": {d: rate(sum(1 for c in scored if c["dimensions"][d]["passed"]), len(scored)) for d in DIMENSIONS},
        "correct_abstention": rate(sum(1 for c in withhold if c["dimensions"]["abstention_appropriateness"]["passed"]), len(withhold)),
        "unnecessary_abstention": rate(sum(1 for c in forbid if c["generated_outcome"]["status"] == "insufficient_evidence"), len(forbid)),
        "partial_where_only_answered_allowed": rate(sum(1 for c in answered_only if c["generated_outcome"]["status"] == "partial"), len(answered_only)),
        "citation_failure": rate(sum(1 for c in scored if not c["dimensions"]["citation_accuracy"]["passed"]), len(scored)),
        "source_fidelity_failure": rate(sum(1 for c in scored if not c["dimensions"]["source_fidelity"]["passed"]), len(scored)),
        "procedure_confusion": rate(sum(1 for c in scored if not c["dimensions"]["procedural_integrity"]["passed"]), len(scored)),
        "token_limit_truncation": rate(sum(1 for c in executed if c["finish_reason"] == "length"), len(executed)),
        "latency_seconds": {"mean": round(statistics.mean(latencies), 3) if latencies else None,
                            "median": round(statistics.median(latencies), 3) if latencies else None,
                            "max": round(max(latencies), 3) if latencies else None},
        "total_generated_tokens": sum(c["generated_tokens"] or 0 for c in executed),
        "peak_gpu_allocated_bytes": max((c["peak_allocated_bytes"] or 0 for c in executed), default=None),
        "peak_gpu_reserved_bytes": max((c["peak_reserved_bytes"] or 0 for c in executed), default=None),
        "failure_code_frequency": dict(Counter(r["failure_code"] for r in error_rows).most_common()),
        "notes": {"scored_denominator": "cases with a recorded generation attempt; not_executed cases are excluded from dimension rates but count as fails in diagnostic_candidate_pass",
                  "citation_metric_scope": "citation ID overlap with labeled must_cite; not semantic support"},
    }
    integrity["passed"] = (not integrity["input_hash_mismatches"] and not integrity["raw_output_hash_mismatches"]
                           and not integrity["prompt_leakage"]
                           and all(c["passed"] for c in integrity["session_provenance_checks"]))
    return {"cases": cases, "error_rows": error_rows, "metrics": metrics, "integrity": integrity,
            "generations": generations, "sessions": sessions}


def score_synthetic(out_dir: Path) -> dict:
    """Mission 005-E synthetic validation: contract validity, expected status, required and
    forbidden citations, response language, and the permission check where the case asks for it.
    Fictional cases; success is not legal accuracy and is never pooled with DEV-20."""
    items, spec_sha = load_synthetic_items()
    gens = {g["case_id"]: g for g in read_jsonl(out_dir / "generations.jsonl")}
    rows = []
    for item in items:
        gen = gens.get(item["id"])
        row = {"case_id": item["id"], "rule": item["rule"], "expected_statuses": item["expected_statuses"],
               "model_status": (gen or {}).get("execution_status", "not_executed")}
        version = (gen or {}).get("contract_version", "v2")
        parsed = None
        if gen and isinstance(gen.get("raw_output"), str):
            try:
                parsed = parse_response(gen["raw_output"], {e["id"] for e in item["evidence"]}, version)
            except (ValueError, TypeError):
                parsed = None
        cites = set((parsed or {}).get("citations") or [])
        answer = (parsed or {}).get("answer", "")
        checks = {
            "contract_valid": parsed is not None,
            "status": parsed is not None and parsed["status"] in item["expected_statuses"],
            "must_cite": parsed is not None and set(item["must_cite"]) <= cites,
            "must_not_cite": parsed is not None and not (set(item["must_not_cite"]) & cites),
            "language": parsed is not None and (not answer.strip() or text_language(answer) == item["expected_language"]),
        }
        if item.get("evidence_check") == "permission_flips":
            text = "\n".join(e["text"] for e in item["evidence"])
            checks["no_permission_flip"] = parsed is not None and not trust_gate.permission_flips(answer, text)
        row.update(status=(parsed or {}).get("status"), citations=sorted(cites), answer=answer, checks=checks,
                   passed=all(checks.values()), input_sha256_ok=bool(gen) and gen.get("input_sha256") == input_sha256(item, version))
        rows.append(row)
    executed = sum(1 for r in rows if r["model_status"] != "not_executed")
    return {"label": "Mission 005-E synthetic specification validation (not legal accuracy)",
            "spec_sha256": spec_sha, "cases": rows,
            "summary": {"target": len(rows), "executed": executed,
                        "passed": sum(1 for r in rows if r["passed"]),
                        "per_check": {k: {"passed": sum(1 for r in rows if r["checks"].get(k)),
                                          "applicable": sum(1 for r in rows if k in r["checks"])}
                                      for k in dict.fromkeys(k for r in rows for k in r["checks"])}}}


def write_artifacts(out_dir: Path, result: dict, mission: str = "005-D") -> None:
    def dump(name, value):
        (out_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    s0 = result["sessions"][0] if result["sessions"] else {}
    dump("raw_inference.json", {"source": "generations.jsonl", "sha256": result["integrity"]["generations_sha256"],
                                "cases": {g["case_id"]: g for g in result["generations"]}})
    dump("case_diagnostics.json", result["cases"])
    dump("performance_metrics.json", result["metrics"])
    dump("evaluation_integrity.json", result["integrity"])
    dump("checkpoint_provenance.json", {"sessions": [{k: s.get(k) for k in ("session_id", "provenance", "load", "environment", "reproduction_pins_matched")} for s in result["sessions"]]})
    dump("execution_manifest.json", {
        "mission": mission, "label": "Development Candidate Diagnostic Performance",
        "benchmark": "artemis_bootstrap/benchmarks/artemis_eval_dev_20.json",
        "dataset_sha256": result["integrity"]["dataset_sha256"], "target_cases": len(result["cases"]),
        "model": (s0.get("metadata") or {}).get("model_name"), "revision": (s0.get("metadata") or {}).get("model_revision"),
        "runtime": (s0.get("metadata") or {}).get("runtime"), "code": s0.get("code"),
        "sessions": [{k: s.get(k) for k in ("session_id", "started_at", "model_loaded", "previous_sessions")} for s in result["sessions"]],
        "max_new_tokens": 256, "heldout_used": False, "official_gold_accuracy": None,
        "independent_legal_review": "not_verified"})
    m = result["metrics"]
    dump("run_summary.json", {k: m[k] for k in ("label", "official_gold_accuracy", "executed_cases", "json_contract_pass",
                                                 "diagnostic_candidate_pass", "dimension_pass", "token_limit_truncation")}
         | {"evaluation_integrity_passed": result["integrity"]["passed"]})
    with (out_dir / "error_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["case_id", "dimension", "failure_code", "detail"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(result["error_rows"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--mission", default="005-D")
    parser.add_argument("--label", default=None)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args(argv)
    if args.synthetic:
        result = score_synthetic(args.out_dir)
        (args.out_dir / "synthetic_validation_results.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result["summary"], ensure_ascii=False))
        return 0
    result = score(args.out_dir)
    if args.label:
        result["metrics"]["label"] = args.label
    write_artifacts(args.out_dir, result, args.mission)
    print(json.dumps({k: result["metrics"][k] for k in ("executed_cases", "json_contract_pass", "diagnostic_candidate_pass")}
                     | {"integrity_passed": result["integrity"]["passed"]}, ensure_ascii=False))
    return 0 if result["integrity"]["passed"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
