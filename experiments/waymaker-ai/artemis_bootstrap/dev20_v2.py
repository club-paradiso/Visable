"""DEV-20 v2: load, run through the 005-Q guarded pipeline, and score, without touching frozen code.

The 005-Q gate freezes the evaluator files (run_dev20_cuda.py, the gates, the trust code) and its pass
re-scores byte for byte with artemis_eval as it stands, so v2 lives here instead:

  - `load_items` reads benchmarks/artemis_eval_dev_20_v2.json only when its digest matches
    DEV20_V2_MANIFEST.json (built by build_dev20_v2.py).
  - `run` is the gate's run_dev20 with the v2 items and registry/real_world_registry_v2.json. It refuses to
    run without a passing decision of that gate. The 2026-11-03 run used gate v12 (code 5f25f18); since
    Mission 005-R changed files the 005-Q gate froze, a newer gate's pass is needed: gate v13 (005-R, failed) and
    gate v14 (005-S, passed; run 299ddf8) and then gate v15 (005-T), the default.
  - `score` scores every released response with artemis_eval unchanged. artemis_eval reads
    must_clarify=false as "a clarification is wrong"; a v2 rubric that lists clarify among its allowed
    statuses (DEV-001, 011, 015, 016) accepts one, so when the released status is clarify such an item is
    scored with must_clarify=true. Nothing else about the rubric changes.

Development Candidate Diagnostic, not Official Gold Accuracy. No legal review.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

BOOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BOOT.parent))
sys.path.insert(0, str(BOOT))
import artemis_eval
import build_dev20_v2
from score_dev20_guarded import DIMENSIONS, read_jsonl, released_response

REGISTRY_V2 = BOOT / "registry" / "real_world_registry_v2.json"


def load_items(path: Path = build_dev20_v2.DEV20_V2) -> tuple[list, str]:
    """The v2 development split, only with the digest its manifest records."""
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    manifest = json.loads(build_dev20_v2.V2_MANIFEST.read_text(encoding="utf-8"))
    if digest != manifest["dev20_v2_sha256"]:
        raise ValueError("Benchmark is not the manifest-recorded DEV-20 v2 split; refusing to run")
    items = json.loads(raw)["items"]
    ids = [i["id"] for i in items]
    if len(ids) != 20 or len(set(ids)) != 20:
        raise ValueError("Expected 20 unique development case IDs")
    return items, digest


def run(prepared, out_dir: Path, decision_path: Path, registry_path: Path = REGISTRY_V2,
        session_label: str = "colab-t4", gate_version: str = "v15") -> dict:
    """DEV-20 v2 through the guarded pipeline, only after a passing decision of the named gate (its run_dev20 steps)."""
    import importlib
    import artemis_runner
    import grounding_guard
    import run_dev20_cuda
    gate = importlib.import_module({"v12": "synthetic_safety_gate_v12", "v13": "synthetic_safety_gate_v13",
                                   "v14": "synthetic_safety_gate_v14", "v15": "synthetic_safety_gate_v15"}[gate_version])
    from waymaker_ai.evidence_registry import load_real_world_registry
    gate.require_passing_gate(decision_path, gate.load_manifest(gate.MANIFEST)["contract_version"], prepared, gate.MANIFEST)
    items, digest = load_items()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        registry = load_real_world_registry(registry_path)
        registry_status = "loaded"
    except gate.RegistryUnavailable as exc:
        registry, registry_status = None, f"unavailable: {exc}"
    adapter = artemis_runner.CudaTransformersAdapter(max_tokens=run_dev20_cuda.MAX_NEW_TOKENS, prepared=prepared,
                                                     contract_version=grounding_guard.CONTRACT_VERSION)
    session_id = run_dev20_cuda.start_session(out_dir, prepared, digest, session_label)
    manifest = gate.load_manifest(gate.MANIFEST)
    for item in items:
        def generate(model_item, item=item):
            response = adapter.generate({**model_item, "id": item["id"]})
            data = dict(response.telemetry or {})
            run_dev20_cuda.append_line(out_dir / "generations.jsonl", {
                "case_id": item["id"], "session_id": session_id, "contract_version": grounding_guard.CONTRACT_VERSION,
                "execution_status": data.get("execution_status", "failed"), "raw_output": data.get("raw_output"),
                **{k: data.get(k) for k in ("prompt_tokens", "generated_token_count", "finish_reason", "metrics", "error")}})
            return data.get("raw_output")
        record = grounding_guard.run_case(item["question"], None, item["evidence"], registry,
                                          manifest["evaluation_date"], generate)
        run_dev20_cuda.append_line(out_dir / "pipeline.jsonl", {"case_id": item["id"], "registry_status": registry_status,
                                                                 **record})
    return {"registry_status": registry_status, "cases": len(items), "dev20_version": "v2", "gate": gate_version}


def scoring_item(item: dict, status: str | None) -> dict:
    """The item artemis_eval scores: a clarification is expected when the rubric allows one and one was given."""
    exp = item["expected"]
    if status == "clarify" and "clarify" in exp["allowed_statuses"] and not exp["procedural_integrity"]["must_clarify"]:
        item = copy.deepcopy(item)
        item["expected"]["procedural_integrity"]["must_clarify"] = True
    return item


def score_response(item: dict, response: dict):
    return artemis_eval.score_artemis_response(scoring_item(item, response.get("status")), response,
                                               allow_candidate_sources=True)


def score(out_dir: Path) -> dict:
    items, dataset_sha = load_items()
    pipe_path = Path(out_dir) / "pipeline.jsonl"
    records = {r["case_id"]: r for r in read_jsonl(pipe_path)}
    if set(records) != {i["id"] for i in items}:
        raise ValueError("pipeline.jsonl does not cover exactly the 20 DEV-20 items")
    cases = []
    for item in items:
        rec = records[item["id"]]
        result = score_response(item, released_response(rec))
        cases.append({
            "case_id": item["id"], "title": item.get("title"),
            "rubric_option": (item["metadata"].get("rubric_revision") or {}).get("option"),
            "pre_inference": rec["pre_inference"], "pre_inference_reason": rec.get("pre_inference_reason"),
            "model_called": rec["model_called"], "guard": (rec.get("guard") or {}).get("decision"),
            "released_provenance": rec["released_provenance"], "released_status": rec["released"].get("status"),
            "expected_statuses": item["expected"].get("allowed_statuses"), "passed": result.overall_passed,
            "dimensions": {d: result.dimension_scores[d].passed for d in DIMENSIONS},
            "failures": list(result.all_failures),
        })
    called = [c for c in cases if c["model_called"]]
    return {
        "label": "DEV-20 v2 through the guarded pipeline with the v2 real-world registry (Development Candidate "
                 "Diagnostic, not Official Gold Accuracy)",
        "dataset_sha256": dataset_sha, "pipeline_sha256": hashlib.sha256(pipe_path.read_bytes()).hexdigest(),
        "summary": {
            "items": len(cases), "model_called": len(called), "withheld_before_model": len(cases) - len(called),
            "passed_all_dimensions": sum(c["passed"] for c in cases),
            "passed_among_model_called": sum(c["passed"] for c in called),
            "released_provenance": dict(Counter(c["released_provenance"] for c in cases)),
            "dimension_passes": {d: sum(c["dimensions"][d] for c in cases) for d in DIMENSIONS},
        },
        "cases": cases,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    result = score(args.out_dir)
    (args.out_dir / "dev20_v2_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                                                        encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
