"""Mission 005-D harness and scorer, with a synthetic adapter and no GPU.

These test bookkeeping: projection, checkpoint/resume, denominators and integrity
checks. They say nothing about how the model performs.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from waymaker_ai import cuda_policy
from waymaker_ai.inference_input import project_evidence

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import run_dev20_cuda as harness
import score_dev20 as scorer


def test_benchmark_labels_never_reach_the_prompt_but_source_kinds_do():
    base = {"id": "E", "title": "t", "text": "x", "source": {"document_id": "D"}}
    for label in ("injection_probe", "synthetic_fixture", "anything_else"):
        projected = project_evidence({**base, "source": {"document_id": "D", "provenance": label}})
        assert "provenance" not in projected["source"]
    for kind in ("official_manual", "official_notice", "community_post"):
        assert project_evidence({**base, "source": {"provenance": kind}})["source"]["provenance"] == kind


def test_only_the_manifest_recorded_dev_split_can_run(tmp_path):
    items, digest = harness.load_dev_items()
    assert len(items) == 20 and digest == "c204497731b637d31da221a468ca2a4c2537d275a974234f41aefe7da4313c5f"
    with pytest.raises(ValueError, match="development split"):
        harness.load_dev_items(BOOT / "benchmarks" / "artemis_eval_heldout_40.json")


def test_no_rendered_dev_prompt_leaks_rubric_or_evaluator_labels():
    items, _ = harness.load_dev_items()
    assert {i["id"]: scorer.leakage_findings(i) for i in items if scorer.leakage_findings(i)} == {}


def test_leakage_check_catches_a_planted_label():
    items, _ = harness.load_dev_items()
    item = json.loads(json.dumps(items[0]))
    item["evidence"][0]["source"]["page_locator"] = "injection_probe"
    assert "evaluator_label:injection_probe" in scorer.leakage_findings(item)


class FakeAdapter:
    """Stands in for CudaTransformersAdapter; returns the session-shaped telemetry."""

    def __init__(self, outputs=None):
        self.calls = []
        self.outputs = outputs or {}

    def generate(self, item):
        self.calls.append(item["id"])
        raw = self.outputs.get(item["id"], json.dumps({"status": "insufficient_evidence", "answer": "", "citations": []}))
        try:
            response = json.loads(raw)
            status = "completed"
        except ValueError:
            response, status = None, "generated_but_invalid"
        return SimpleNamespace(telemetry={
            "execution_status": status, "raw_output": raw, "response": response,
            "input_messages": harness.prompt_messages(item), "evidence_ids": [e["id"] for e in item["evidence"]],
            "prompt_tokens": 100, "generated_token_count": 20, "finish_reason": "eos",
            "metrics": {"wall_seconds": 3.0, "peak_allocated_bytes": 9_000_000_000, "peak_reserved_bytes": 9_100_000_000},
            "output_validation": {"passed": status == "completed"}})


def test_pilot_then_rest_covers_twenty_without_double_counting(tmp_path):
    items, _ = harness.load_dev_items()
    adapter = FakeAdapter()
    first = harness.generate_cases(adapter, items, list(harness.PILOT), tmp_path, "s1")
    assert first["generated_now"] == 3
    rest = [i["id"] for i in items if i["id"] not in harness.PILOT]
    second = harness.generate_cases(adapter, items, harness.PILOT + tuple(rest), tmp_path, "s1")
    assert second == {"generated_now": 17, "skipped_already_recorded": 3, "completed": 17}
    assert len(adapter.calls) == 20 and len(set(adapter.calls)) == 20
    assert harness.recorded_ids(tmp_path / "generations.jsonl") == {i["id"] for i in items}


def test_resume_after_disconnect_keeps_old_lines_and_marks_the_new_session(tmp_path):
    items, _ = harness.load_dev_items()
    ids = [i["id"] for i in items]
    harness.generate_cases(FakeAdapter(), items, ids[:12], tmp_path, "s1")
    before = (tmp_path / "generations.jsonl").read_text()
    adapter = FakeAdapter()
    harness.generate_cases(adapter, items, ids, tmp_path, "s2")
    after = (tmp_path / "generations.jsonl").read_text()
    assert after.startswith(before) and adapter.calls == ids[12:]
    sessions = {json.loads(line)["case_id"]: json.loads(line)["session_id"] for line in after.splitlines()}
    assert sum(1 for s in sessions.values() if s == "s2") == 8


def test_harness_refuses_output_rendered_from_a_different_input(tmp_path):
    items, _ = harness.load_dev_items()

    class Drifted(FakeAdapter):
        def generate(self, item):
            result = super().generate(item)
            result.telemetry["input_messages"] = [{"role": "user", "content": "changed"}]
            return result
    with pytest.raises(RuntimeError, match="differs"):
        harness.generate_cases(Drifted(), items, [items[0]["id"]], tmp_path, "s1")


def valid_session(session_id="s1"):
    policy = cuda_policy.configuration()
    return {"session_id": session_id, "model_loaded": True, "metadata": {
        "inference_kind": "real_inference", "runtime": "transformers_cuda", "profile": "gemma4_e4b",
        "model_name": policy["model"]["checkpoint"], "model_revision": policy["model"]["revision"],
        "quantization": "bnb_nf4_double_quant_fp16", "quantization_verified": True, "cuda_device": "Tesla T4",
        "checkpoint_metadata_verified": True, "checkpoint_integrity_verified": True,
        "weight_integrity": "sha256_verified",
        "weights_sha256": policy["model"]["artifacts"]["model.safetensors"]["digest"]}}


def write_run(tmp_path, n_cases=20, outputs=None, session=None):
    items, _ = harness.load_dev_items()
    harness.generate_cases(FakeAdapter(outputs), items, [i["id"] for i in items[:n_cases]], tmp_path, "s1")
    (tmp_path / "sessions.jsonl").write_text(json.dumps(session or valid_session()) + "\n")
    return items


def test_unexecuted_cases_stay_in_the_denominator(tmp_path):
    write_run(tmp_path, n_cases=18)
    result = scorer.score(tmp_path)
    m = result["metrics"]
    assert m["executed_cases"] == {"numerator": 18, "denominator": 20, "rate": 0.9}
    assert m["diagnostic_candidate_pass"]["denominator"] == 20
    missing = [c for c in result["cases"] if c["model_status"] == "not_executed"]
    assert len(missing) == 2 and all(c["diagnostic_outcome"] == "fail" for c in missing)
    assert m["official_gold_accuracy"] is None and m["label"] == "Development Candidate Diagnostic Performance"


def test_invalid_json_is_generated_but_never_a_pass(tmp_path):
    items = write_run(tmp_path, outputs={"ARTEMIS-004-DEV-001": '{"status": "answered"'})
    case = next(c for c in scorer.score(tmp_path)["cases"] if c["case_id"] == "ARTEMIS-004-DEV-001")
    assert case["model_status"] == "generated_but_invalid" and case["contract_valid"] is False
    assert case["diagnostic_outcome"] == "fail"


def test_integrity_fails_on_tampered_output_or_unverified_session(tmp_path):
    write_run(tmp_path)
    assert scorer.score(tmp_path)["integrity"]["passed"] is True
    lines = (tmp_path / "generations.jsonl").read_text().splitlines()
    first = json.loads(lines[0])
    first["raw_output"] = first["raw_output"].replace("insufficient", "INSUFFICIENT")
    (tmp_path / "generations.jsonl").write_text("\n".join([json.dumps(first)] + lines[1:]) + "\n")
    integrity = scorer.score(tmp_path)["integrity"]
    assert integrity["raw_output_hash_mismatches"] == [first["case_id"]] and integrity["passed"] is False
    bad = valid_session()
    bad["metadata"]["model_name"] = "google/gemma-4-E2B-it"
    (tmp_path / "sessions.jsonl").write_text(json.dumps(bad) + "\n")
    assert scorer.score(tmp_path)["integrity"]["session_provenance_checks"][0]["passed"] is False


def test_duplicate_case_lines_are_rejected(tmp_path):
    write_run(tmp_path, n_cases=2)
    path = tmp_path / "generations.jsonl"
    path.write_text(path.read_text() + path.read_text().splitlines()[0] + "\n")
    with pytest.raises(ValueError, match="Duplicate"):
        scorer.score(tmp_path)


def test_artifacts_are_written(tmp_path):
    write_run(tmp_path)
    result = scorer.score(tmp_path)
    scorer.write_artifacts(tmp_path, result)
    for name in ("execution_manifest.json", "checkpoint_provenance.json", "raw_inference.json", "run_summary.json",
                 "error_summary.csv", "case_diagnostics.json", "performance_metrics.json", "evaluation_integrity.json"):
        assert (tmp_path / name).exists(), name
    manifest = json.loads((tmp_path / "execution_manifest.json").read_text())
    assert manifest["heldout_used"] is False and manifest["official_gold_accuracy"] is None


def test_pilot_and_rest_in_one_loaded_session_log_one_session(tmp_path):
    class Prepared:
        session = object()
        blocker = None
        header = {"environment": {}, "provenance": {}, "load": {}}

        def metadata(self):
            return valid_session()["metadata"]

    class Adapter(FakeAdapter):
        def __init__(self, max_tokens, prepared):
            super().__init__()

        def check_availability(self):
            return True, None
    import artemis_runner
    prepared = Prepared()
    original = artemis_runner.CudaTransformersAdapter
    artemis_runner.CudaTransformersAdapter = Adapter
    try:
        assert harness.main(["--out-dir", str(tmp_path), "--cases", "pilot"], prepared=prepared) == 0
        assert harness.main(["--out-dir", str(tmp_path), "--cases", "rest"], prepared=prepared) == 0
    finally:
        artemis_runner.CudaTransformersAdapter = original
    assert len((tmp_path / "sessions.jsonl").read_text().splitlines()) == 1
    assert len(harness.recorded_ids(tmp_path / "generations.jsonl")) == 20
