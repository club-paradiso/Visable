"""Mission 005-C.1: a CUDA run record is accepted only with full, consistent provenance.

These are structural checks on JSON written by our own code. They are not an
external attestation: a forger who rewrites every field consistently can still
produce an accepted record. They stop accidental mislabeling and partial edits.
"""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from waymaker_ai import cuda_policy, foundation, response_contract

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import artemis_runner as runner
import gemma4_cuda_runtime as cuda

POLICY = cuda_policy.configuration()
MODEL = POLICY["model"]
REVISION = MODEL["revision"]


def artifact(name):
    ref = MODEL["artifacts"][name]
    return {"algorithm": "sha256", "digest": ref["digest"], "size_bytes": ref["size_bytes"]}


def valid_case(case_id="synthetic_citation", status="completed"):
    raw = json.dumps({"status": "partial", "answer": "가상 답변", "citations": ["SYN-1"]}, ensure_ascii=False)
    return {"case_id": case_id, "execution_status": status, "evidence_ids": ["SYN-1"], "raw_output": raw,
            "generated_token_count": 38, "finish_reason": "eos",
            "response": json.loads(raw), "output_validation": {"passed": True}}


def valid_record():
    record = cuda.new_record(96, "synthetic")
    record.update(
        execution_status="completed",
        environment={"cuda_device": "Tesla T4", "packages": {"torch": "2.11.0+cu130"}, "version_drift": []},
        provenance={"snapshot_revision": REVISION, "checkpoint_metadata_verified": True,
                    "metadata_sha256": dict(MODEL["metadata_sha256"]), "checkpoint_integrity_verified": True,
                    "artifact_integrity": {"model.safetensors": artifact("model.safetensors"),
                                           "tokenizer.json": artifact("tokenizer.json")},
                    "integrity_reference_source": MODEL["reference_source"], "weight_integrity": "sha256_verified"},
        load={"load_seconds": 70.0, "model_class": "Gemma4ForConditionalGeneration",
              "quantization": {"passed": True, "quant_types": ["nf4"], "double_quant": [True],
                               "compute_dtypes": ["float16"], "parameter_devices": ["cuda:0"],
                               "linear4bit_modules": 400, "quantized_decoder_layers": 42}},
        code={"git_commit": "0" * 40, "files_sha256": {name: "0" * 64 for name in cuda.CODE_FILES}},
        cases=[valid_case()])
    return record


def test_valid_record_is_accepted():
    cuda_policy.validate_run_record(valid_record())


def set_path(record, path, value):
    target = record
    for key in path[:-1]:
        target = target[key]
    if value is DELETE:
        del target[path[-1]]
    else:
        target[path[-1]] = value


DELETE = object()
FORGERIES = {
    "gemma3_disguised": (("model", "checkpoint"), "google/gemma-3-4b-it"),
    "e2b_disguised": (("model", "checkpoint"), "google/gemma-4-E2B-it"),
    "wrong_revision": (("model", "revision"), "0" * 40),
    "wrong_snapshot_revision": (("provenance", "snapshot_revision"), "main"),
    "runtime_not_cuda": (("runtime",), "mlx_vlm"),
    "mock_as_real": (("inference_kind",), "mock"),
    "metadata_unverified": (("provenance", "checkpoint_metadata_verified"), False),
    "weight_sha_missing": (("provenance", "artifact_integrity", "model.safetensors"), DELETE),
    "weight_sha_wrong": (("provenance", "artifact_integrity", "model.safetensors", "digest"), "f" * 64),
    "size_only_as_verified": (("provenance", "artifact_integrity", "model.safetensors", "algorithm"), "size_only"),
    "weight_integrity_size_only": (("provenance", "weight_integrity"), "size_only"),
    "untrusted_reference": (("provenance", "integrity_reference_source"), "https://example.invalid/sha"),
    "tokenizer_sha_wrong": (("provenance", "artifact_integrity", "tokenizer.json", "digest"), "e" * 64),
    "quantization_passed_missing": (("load", "quantization", "passed"), DELETE),
    "nf4_check_failed": (("load", "quantization", "passed"), False),
    "fp4_with_passed_flag": (("load", "quantization", "quant_types"), ["fp4"]),
    "cpu_offload_with_passed_flag": (("load", "quantization", "parameter_devices"), ["cpu", "cuda:0"]),
    "load_missing": (("load",), {}),
    "gpu_missing": (("environment", "cuda_device"), None),
    "packages_missing": (("environment", "packages"), {}),
    "code_provenance_missing": (("code",), {}),
    "quantization_label_changed": (("model", "quantization"), "4bit"),
    "gold_accuracy_claimed": (("official_gold_accuracy",), 1.0),
    "legal_accuracy_claimed": (("legal_accuracy_claimed",), True),
}


@pytest.mark.parametrize("name", sorted(FORGERIES))
def test_forged_or_incomplete_success_record_is_rejected(name):
    record = valid_record()
    path, value = FORGERIES[name]
    set_path(record, path, value)
    with pytest.raises(ValueError):
        cuda_policy.validate_run_record(record)


CASE_FORGERIES = {
    "zero_tokens_completed": lambda c: c.update(generated_token_count=0),
    "bool_tokens": lambda c: c.update(generated_token_count=True),
    "invalid_json_completed": lambda c: c.update(raw_output='{"status": "partial"'),
    "unlisted_citation_completed": lambda c: c.update(raw_output=json.dumps(
        {"status": "partial", "answer": "x", "citations": ["SYN-9"]})),
    "response_differs_from_raw": lambda c: c.update(response={"status": "answered", "answer": "x", "citations": ["SYN-1"]}),
    "raw_output_missing": lambda c: c.update(raw_output=None),
    "evidence_ids_missing": lambda c: c.pop("evidence_ids"),
    "validation_flag_false": lambda c: c.update(output_validation={"passed": False}),
}


@pytest.mark.parametrize("name", sorted(CASE_FORGERIES))
def test_case_level_overclaims_are_rejected(name):
    record = valid_record()
    CASE_FORGERIES[name](record["cases"][0])
    with pytest.raises(ValueError):
        cuda_policy.validate_run_record(record)


def test_overall_status_must_match_cases():
    record = valid_record()
    record["cases"].append({**valid_case("c2"), "execution_status": "failed", "raw_output": None,
                            "generated_token_count": None, "output_validation": {"passed": False}})
    with pytest.raises(ValueError, match="overall"):
        cuda_policy.validate_run_record(record)


def test_generated_but_invalid_case_must_really_fail_the_contract():
    record = valid_record()
    record["execution_status"] = "generated_but_invalid"
    record["cases"][0].update(execution_status="generated_but_invalid", output_validation={"passed": False})
    with pytest.raises(ValueError, match="contract"):
        cuda_policy.validate_run_record(record)
    record["cases"][0]["raw_output"] = '{"status": "partial"'
    record["cases"][0].pop("response")
    cuda_policy.validate_run_record(record)


def test_failed_load_record_needs_no_model_provenance_but_cannot_hold_tokens():
    record = cuda.new_record(96, "synthetic")
    record.update(execution_status="failed", failure_category="model_loading_error", error="synthetic",
                  environment={"cuda_device": "Tesla T4", "packages": {"torch": "x"}})
    cuda_policy.validate_run_record(record)
    record["cases"] = [valid_case()]
    with pytest.raises(ValueError):
        cuda_policy.validate_run_record(record)


# --- response contract (shared with MLX) ------------------------------------

@pytest.mark.parametrize("raw", [
    '{"status": "answered", "status": "insufficient_evidence", "answer": "", "citations": []}',
    '{"status": "answered", "answer": "근거 없는 답", "citations": []}',
    '{"status": "partial", "answer": "x", "citations": []}',
    '{"status": "conflict", "answer": "x", "citations": []}',
    '{"status": "answered", "answer": "", "citations": ["SYN-1"]}',
    '{"status": "partial", "answer": "x", "citations": ["SYN-1", "SYN-1"]}',
    '{"status": "partial", "answer": "x", "citations": ["syn-1"]}',
    '```json\n{"status": "insufficient_evidence", "answer": "", "citations": []}\n```',
    '{"status": "insufficient_evidence", "answer": "", "citations": []} trailing',
])
def test_contract_rejects_ungrounded_or_ambiguous_output(raw):
    with pytest.raises(ValueError):
        response_contract.parse_response(raw, {"SYN-1"})


def test_contract_accepts_the_three_audited_colab_outputs():
    audit = json.loads((BOOT / "runs" / "colab-t4-20261030" / "colab_execution_audit.json").read_text())
    ids = {"no_evidence": set(), "synthetic_citation": {"SYN-1"}, "synthetic_conflict": {"SYN-1", "SYN-2"}}
    for case in audit["observed"]["cases"]:
        response_contract.parse_response(case["raw_output"], ids[case["case"]])


def test_mlx_worker_uses_the_shared_contract():
    import gemma4_runtime
    assert gemma4_runtime.parse_response is response_contract.parse_response
    assert cuda.parse_response is response_contract.parse_response


# --- aggregation ------------------------------------------------------------

def cuda_metadata(**overrides):
    value = {"adapter_type": "cuda_transformers", "inference_kind": "real_inference", "runtime": "transformers_cuda",
             "profile": "gemma4_e4b", "model_name": MODEL["checkpoint"], "model_revision": REVISION,
             "quantization": "bnb_nf4_double_quant_fp16", "quantization_verified": True, "cuda_device": "Tesla T4",
             "checkpoint_metadata_verified": True, "checkpoint_integrity_verified": True,
             "weight_integrity": "sha256_verified", "weights_sha256": MODEL["artifacts"]["model.safetensors"]["digest"]}
    value.update(overrides)
    return value


@pytest.mark.parametrize("override", [
    {"adapter_type": "mock"}, {"weights_sha256": "f" * 64}, {"weights_sha256": None},
    {"model_name": "google/gemma-3-4b-it"}, {"model_name": "google/gemma-4-E2B-it"},
    {"model_revision": "main"}, {"profile": "gemma4_e2b"},
])
def test_metric_group_rejects_cross_model_or_mock_cuda_metadata(override):
    with pytest.raises(ValueError):
        foundation.metric_group(cuda_metadata(**override))


def test_mock_with_cuda_runtime_label_is_its_own_group():
    mock = {"inference_kind": "mock", "runtime": "transformers_cuda", "profile": "gemma4_e4b",
            "model_name": MODEL["checkpoint"], "model_revision": REVISION}
    assert foundation.metric_group(mock) != foundation.metric_group(cuda_metadata())


def test_cuda_groups_split_by_quantization_label():
    a = foundation.metric_group(cuda_metadata())
    report = {"benchmark_metadata": {"benchmark_sha256": "x"}, "mode": "candidate_eval"}
    fixture = {"inference_kind": "recorded_fixture", "runtime": "transformers_cuda", "profile": "gemma4_e4b",
               "model_name": MODEL["checkpoint"], "model_revision": REVISION}
    with pytest.raises(ValueError, match="cannot be pooled"):
        foundation.require_same_metric_group([{**report, "model_metadata": cuda_metadata()},
                                              {**report, "model_metadata": fixture}])
    assert a == foundation.metric_group(cuda_metadata())


# --- runner and adapter status flow -----------------------------------------

class FailedLoadPrepared:
    session = None
    blocker = {"execution_status": "failed", "failure_category": "model_loading_error", "error": "synthetic OOM"}
    header = {"environment": {"cuda_device": "Tesla T4"}}

    def prepare(self):
        return False

    def metadata(self):
        return {"inference_kind": "real_inference", "runtime": "transformers_cuda", "quantization_verified": False}


def benchmark(tmp_path):
    path = tmp_path / "bench.json"
    path.write_text(json.dumps({"items": [{"id": "SYN-ITEM", "question": "q", "evidence": []}]}))
    return path


def test_load_failure_is_failed_not_not_executed(tmp_path):
    adapter = runner.CudaTransformersAdapter(max_tokens=32, prepared=FailedLoadPrepared())
    summary = runner.ArtemisEvaluationRunner(adapter=adapter, mode=runner.EvaluationMode.CANDIDATE_EVAL,
                                             benchmark_path=benchmark(tmp_path), out_dir=tmp_path / "out").run()
    assert summary.execution_status == runner.ExecutionStatus.FAILED
    assert summary.not_executed_reason is None
    assert summary.model_metadata["not_available_reason"] == "synthetic OOM"


def test_missing_prerequisites_stay_not_executed(tmp_path):
    adapter = runner.CudaTransformersAdapter(max_tokens=32, cache_dir=tmp_path / "empty")
    summary = runner.ArtemisEvaluationRunner(adapter=adapter, mode=runner.EvaluationMode.CANDIDATE_EVAL,
                                             benchmark_path=benchmark(tmp_path), out_dir=tmp_path / "out").run()
    assert summary.execution_status == runner.ExecutionStatus.NOT_EXECUTED


class InvalidOutputSession:
    def generate(self, case_id, item, max_new_tokens, contract_version="v1"):
        return {"case_id": case_id, "execution_status": "generated_but_invalid", "raw_output": '{"status": "answered"',
                "generated_token_count": 5, "error": "JSONDecodeError", "output_validation": {"passed": False}}


def test_generated_but_invalid_is_never_scored_as_a_pass(tmp_path):
    prepared = cuda.PreparedRun()
    prepared.session = InvalidOutputSession()
    adapter = runner.CudaTransformersAdapter(max_tokens=32, prepared=prepared)
    summary = runner.ArtemisEvaluationRunner(adapter=adapter, mode=runner.EvaluationMode.CANDIDATE_EVAL,
                                             benchmark_path=benchmark(tmp_path), out_dir=tmp_path / "out").run()
    assert summary.suite_summary.passed_cases == 0
    assert summary.execution_status == runner.ExecutionStatus.FAILED
    assert summary.item_results[0].model_output["raw_output"] == '{"status": "answered"'


# --- GPU memory release and placement ---------------------------------------

def test_load_failure_releases_gpu_memory(monkeypatch):
    calls = []
    torch = SimpleNamespace(float16="float16", cuda=SimpleNamespace(
        reset_peak_memory_stats=lambda: None, synchronize=lambda: None,
        empty_cache=lambda: calls.append("empty_cache")))
    transformers = SimpleNamespace(
        AutoProcessor=SimpleNamespace(from_pretrained=lambda *_, **__: type("Gemma4Processor", (), {})()),
        BitsAndBytesConfig=lambda **kw: kw,
        AutoModelForMultimodalLM=SimpleNamespace(from_pretrained=lambda *_, **__: (_ for _ in ()).throw(
            type("OutOfMemoryError", (RuntimeError,), {})("synthetic"))))
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    session = cuda.CudaSession("synthetic")
    with pytest.raises(RuntimeError):
        session.load()
    assert "empty_cache" in calls and session.model is None


def test_decoder_layers_must_all_be_quantized(monkeypatch):
    import contextlib
    from types import ModuleType
    bnb = ModuleType("bitsandbytes")
    Linear4bit = type("Linear4bit", (), {})
    bnb.nn = SimpleNamespace(Linear4bit=Linear4bit)
    torch = ModuleType("torch")
    torch.nn = SimpleNamespace(Linear=type("Linear", (), {}))
    monkeypatch.setitem(sys.modules, "bitsandbytes", bnb)
    monkeypatch.setitem(sys.modules, "torch", torch)

    def layer():
        m = Linear4bit()
        m.weight = SimpleNamespace(quant_state=SimpleNamespace(quant_type="nf4", nested=True))
        m.compute_dtype = "torch.float16"
        return m
    config = {"load_in_4bit": True, "bnb_4bit_quant_type": "nf4", "bnb_4bit_use_double_quant": True,
              "bnb_4bit_compute_dtype": "float16"}

    def model(layers):
        named = [(f"model.language_model.layers.{i}.mlp.down_proj", layer()) for i in layers]
        return SimpleNamespace(named_modules=lambda: named, modules=lambda: [m for _, m in named],
                               parameters=lambda: [SimpleNamespace(device="cuda:0")],
                               buffers=lambda: [SimpleNamespace(device="cuda:0")],
                               config=SimpleNamespace(quantization_config=config))
    assert cuda.quantization_report(model(range(42)))["passed"] is True
    partial = cuda.quantization_report(model(range(41)))
    assert partial["passed"] is False and partial["quantized_decoder_layers"] == 41


def test_probe_keeps_an_inconsistent_record_and_exits_4(tmp_path):
    import probe_gemma4_cuda

    class Inconsistent:
        def run(self, cases, max_new_tokens, evidence_kind):
            record = valid_record()
            record["model"]["checkpoint"] = "google/gemma-4-E2B-it"
            return record
    out = tmp_path / "record.json"
    assert probe_gemma4_cuda.main(["--out", str(out)], prepared=Inconsistent()) == 4
    saved = json.loads(out.read_text())
    assert saved["record_validation"]["passed"] is False
    assert saved["cases"][0]["raw_output"]


def test_committed_local_preflight_record_is_still_valid():
    path = BOOT / "runs" / "mission005c-cuda-20261030" / "local_macos_preflight_not_executed.json"
    record = json.loads(path.read_text())
    assert record["execution_status"] == "not_executed"
    cuda_policy.validate_run_record(record)


def test_nested_source_memos_and_answers_never_reach_the_prompt():
    item = {"question": "q", "expected": {"answer": "SECRET-EXPECTED"}, "rubric": "SECRET-RUBRIC",
            "evidence": [{"id": "SYN-1", "text": "synthetic", "reviewer_note": "SECRET-NOTE",
                          "source": {"document_id": "D1", "memo": "SECRET-MEMO",
                                     "review": {"answer": "SECRET-NESTED"}, "provenance": "synthetic"}}]}
    prompt = json.dumps(cuda.build_messages(cuda.validate_input(item)), ensure_ascii=False)
    assert "SECRET" not in prompt and "D1" in prompt
