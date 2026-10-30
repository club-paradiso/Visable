"""CUDA path regressions with synthetic torch/bitsandbytes stand-ins and no GPU.

These test classification, provenance and the response contract. They never
show that a model runs; that needs a real CUDA GPU and a new run record.
"""
import contextlib
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from waymaker_ai import cuda_policy, foundation

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import artemis_runner as runner
import gemma4_cuda_runtime as cuda
import probe_gemma4_cuda

ROOT = Path(__file__).resolve().parents[1]
REVISION = "ee0ef6023621cff504d758262d4e04895a5af4a2"


# --- policy and checkpoint provenance ---------------------------------------

def test_policy_pins_official_upstream_revision_and_nf4():
    policy = cuda_policy.configuration()
    upstream = foundation.profile("gemma4_e4b")
    assert policy["model"]["checkpoint"] == upstream["upstream"] == "google/gemma-4-E4B-it"
    assert policy["model"]["revision"] == upstream["upstream_revision"] == REVISION
    assert policy["quantization"]["bnb_4bit_quant_type"] == "nf4"
    assert policy["quantization"]["bnb_4bit_compute_dtype"] == "float16"


@pytest.mark.parametrize("path,value", [
    (("quantization", "bnb_4bit_quant_type"), "fp4"),
    (("quantization", "load_in_4bit"), False),
    (("model", "revision"), "main"),
    (("model", "checkpoint"), "mlx-community/gemma-4-e4b-it-4bit"),
    (("allow_implicit_fallback",), True),
])
def test_policy_rejects_relaxed_or_cross_model_config(tmp_path, monkeypatch, path, value):
    data = json.loads(cuda_policy.CONFIG_PATH.read_text())
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    config = tmp_path / "cuda.json"
    config.write_text(json.dumps(data))
    monkeypatch.setattr(cuda_policy, "CONFIG_PATH", config)
    with pytest.raises(ValueError):
        cuda_policy.configuration()


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    """Synthetic files with digests written into a patched policy; not weights."""
    policy = copy.deepcopy(cuda_policy.configuration())
    model = policy["model"]
    path = tmp_path / "models--google--gemma-4-E4B-it" / "snapshots" / REVISION
    path.mkdir(parents=True)
    files = {"config.json": json.dumps({"model_type": "gemma4", "architectures": model["architectures"],
                                        "text_config": model["text_config"]}),
             "processor_config.json": json.dumps({"processor_class": "Gemma4Processor"}),
             "tokenizer_config.json": "{}", "chat_template.jinja": "synthetic", "generation_config.json": "{}"}
    for name, value in files.items():
        (path / name).write_text(value)
    model["metadata_sha256"] = {n: hashlib.sha256((path / n).read_bytes()).hexdigest() for n in files}
    (path / "model.safetensors").write_bytes(b"synthetic-not-weights")
    (path / "tokenizer.json").write_text("{}")
    model["artifacts"] = {n: {"algorithm": "sha256", "digest": hashlib.sha256((path / n).read_bytes()).hexdigest(),
                              "size_bytes": (path / n).stat().st_size}
                          for n in ("model.safetensors", "tokenizer.json")}
    monkeypatch.setattr(cuda_policy, "configuration", lambda: policy)
    return path


def test_snapshot_found_only_at_pinned_revision(snapshot, tmp_path):
    assert cuda_policy.find_snapshot(tmp_path) == snapshot
    (snapshot.parent / ("0" * 40)).mkdir()
    assert cuda_policy.find_snapshot(tmp_path) == snapshot


def test_snapshot_weights_sha256_verified(snapshot):
    verified = cuda_policy.validate_snapshot(snapshot)
    assert verified["weight_integrity"] == "sha256_verified"
    assert verified["checkpoint_integrity_verified"] is True


def test_size_only_weights_are_recorded_but_not_integrity_verified(snapshot):
    verified = cuda_policy.validate_snapshot(snapshot, verify_weights=False)
    assert verified["weight_integrity"] == "size_only"
    assert verified["checkpoint_integrity_verified"] is False


def test_tampered_weights_and_prequantized_config_are_rejected(snapshot):
    (snapshot / "model.safetensors").write_bytes(b"synthetic-not-weightz")
    with pytest.raises(ValueError, match="digest mismatch"):
        cuda_policy.validate_snapshot(snapshot)
    config = json.loads((snapshot / "config.json").read_text())
    config["quantization_config"] = {"quant_method": "bitsandbytes"}
    (snapshot / "config.json").write_text(json.dumps(config))
    with pytest.raises(ValueError):
        cuda_policy.validate_snapshot(snapshot, verify_weights=False)


# --- separate aggregation ---------------------------------------------------

def cuda_metadata(**overrides):
    value = {"adapter_type": "cuda_transformers", "inference_kind": "real_inference",
             "runtime": "transformers_cuda", "profile": "gemma4_e4b",
             "weights_sha256": cuda_policy.configuration()["model"]["artifacts"]["model.safetensors"]["digest"],
             "model_name": "google/gemma-4-E4B-it", "model_revision": REVISION,
             "quantization": "bnb_nf4_double_quant_fp16", "quantization_verified": True,
             "cuda_device": "Tesla T4", "checkpoint_metadata_verified": True,
             "checkpoint_integrity_verified": True, "weight_integrity": "sha256_verified"}
    value.update(overrides)
    return value


def mlx_metadata():
    selected = foundation.profile("gemma4_e4b")
    return {"inference_kind": "real_inference", "runtime": "mlx_vlm", "profile": "gemma4_e4b",
            "model_name": selected["inference_checkpoint"], "model_revision": selected["inference_revision"],
            "checkpoint_metadata_verified": True, "checkpoint_integrity_verified": True,
            "weight_integrity": "sha256_verified"}


def test_cuda_and_mlx_never_share_a_metric_group():
    assert foundation.metric_group(cuda_metadata()) != foundation.metric_group(mlx_metadata())
    report = {"benchmark_metadata": {"benchmark_sha256": "x"}, "mode": "candidate_eval"}
    with pytest.raises(ValueError, match="cannot be pooled"):
        foundation.require_same_metric_group([{**report, "model_metadata": cuda_metadata()},
                                              {**report, "model_metadata": mlx_metadata()}])


@pytest.mark.parametrize("override", [
    {"quantization_verified": False}, {"weight_integrity": "size_only"},
    {"checkpoint_integrity_verified": False}, {"cuda_device": None},
    {"model_name": "mlx-community/gemma-4-e4b-it-4bit"}, {"quantization": "4bit"},
])
def test_unverified_cuda_provenance_cannot_be_aggregated(override):
    with pytest.raises(ValueError):
        foundation.metric_group(cuda_metadata(**override))


def test_mlx_runtime_still_requires_mlx_checkpoint():
    with pytest.raises(ValueError):
        foundation.metric_group({**mlx_metadata(), "model_name": "google/gemma-4-E4B-it"})


# --- preflight without a GPU ------------------------------------------------

def test_missing_checkpoint_is_not_executed_and_valid_record(tmp_path):
    record = cuda.PreparedRun(cache_dir=tmp_path).run(probe_gemma4_cuda.CASES, 32, "synthetic")
    assert record["execution_status"] == "not_executed"
    assert "no download" in record["not_executed_reason"]
    assert record["cases"] == []
    assert record["official_gold_accuracy"] is None
    cuda_policy.validate_run_record(record)


def test_probe_reports_old_packages(monkeypatch):
    monkeypatch.setattr(cuda, "versions", lambda: {"torch": None, "transformers": "4.57.0",
                                                    "bitsandbytes": "0.50.2", "accelerate": None,
                                                    "huggingface-hub": None, "tokenizers": None})
    problems = cuda.probe()["problems"]
    assert "torch not installed" in problems
    assert any("transformers 4.57.0 is older" in p for p in problems)


# --- synthetic loaded session -----------------------------------------------

class Ids:
    def __init__(self, values):
        self.values = values
        self.shape = (1, len(values))

    def __getitem__(self, key):
        return Ids(self.values[key[1]])

    def tolist(self):
        return list(self.values)


class Inputs(dict):
    def to(self, _device):
        return self


@pytest.fixture
def fake_torch(monkeypatch):
    torch = ModuleType("torch")
    torch.cuda = SimpleNamespace(reset_peak_memory_stats=lambda: None, synchronize=lambda: None, empty_cache=lambda: None,
                                 max_memory_allocated=lambda: 9_000_000_000, max_memory_reserved=lambda: 9_400_000_000)
    torch.inference_mode = contextlib.nullcontext
    torch.nn = SimpleNamespace(Linear=type("Linear", (), {}))
    monkeypatch.setitem(sys.modules, "torch", torch)
    return torch


def make_session(raw, new_ids=(5, 6, 1), prompt_len=4, prompts=None):
    session = cuda.CudaSession("synthetic")

    def apply_chat_template(messages, **kwargs):
        assert kwargs["enable_thinking"] is False and kwargs["add_generation_prompt"] is True
        if prompts is not None:
            prompts.append(messages)
        return Inputs(input_ids=Ids(list(range(prompt_len))))

    def generate(**kwargs):
        assert kwargs["do_sample"] is False
        streamer = kwargs["streamer"]
        streamer.put("prompt")
        for _ in new_ids:
            streamer.put("token")
        return Ids(list(range(prompt_len)) + list(new_ids))

    session.processor = SimpleNamespace(apply_chat_template=apply_chat_template,
                                        tokenizer=SimpleNamespace(decode=lambda ids, **_: raw))
    session.model = SimpleNamespace(device="cuda:0", generate=generate,
                                    generation_config=SimpleNamespace(eos_token_id=[1, 106]))
    return session


EVIDENCE_CASE = {"question": "synthetic", "evidence": [{"id": "SYN-1", "text": "synthetic"}]}


def test_completed_requires_tokens_and_valid_listed_citation(fake_torch):
    raw = json.dumps({"status": "partial", "answer": "synthetic", "citations": ["SYN-1"]})
    result = make_session(raw).generate("c", EVIDENCE_CASE, 96)
    assert result["execution_status"] == "completed"
    assert result["finish_reason"] == "eos"
    assert result["generated_token_count"] == 3
    assert result["metrics"]["peak_allocated_bytes"] == 9_000_000_000
    assert result["metrics"]["first_token_seconds_including_prefill"] is not None


def test_unlisted_citation_is_generated_but_invalid(fake_torch):
    raw = json.dumps({"status": "answered", "answer": "synthetic", "citations": ["SYN-9"]})
    result = make_session(raw).generate("c", EVIDENCE_CASE, 96)
    assert result["execution_status"] == "generated_but_invalid"
    assert result["failure_category"] == "successful_generation_invalid_json"
    assert result["raw_output"] == raw


def test_length_cutoff_is_flagged_as_possible_truncation(fake_torch):
    result = make_session('{"status": "ans', new_ids=(5, 6, 7)).generate("c", EVIDENCE_CASE, 3)
    assert result["finish_reason"] == "length"
    assert result["execution_status"] == "generated_but_invalid"
    assert result["output_validation"]["possible_token_limit_truncation"] is True


def test_zero_tokens_cannot_be_completed(fake_torch):
    result = make_session('{"status":"answered","answer":"","citations":[]}', new_ids=()).generate("c", EVIDENCE_CASE, 32)
    assert result["execution_status"] == "failed"
    assert result["failure_category"] == "generation_no_tokens"


def test_long_prompt_is_rejected_without_truncation(fake_torch):
    session = make_session("{}", prompt_len=2049)
    session.model.generate = lambda **_: pytest.fail("Must not generate past the prompt limit")
    result = session.generate("c", EVIDENCE_CASE, 32)
    assert result["failure_category"] == "prompt_rejected"


def test_duplicate_evidence_ids_are_rejected_before_prompting(fake_torch):
    session = make_session("{}")
    session.processor.apply_chat_template = lambda *_, **__: pytest.fail("Must not render rejected input")
    case = {"question": "q", "evidence": [{"id": "SYN-1", "text": "a"}, {"id": "SYN-1", "text": "b"}]}
    assert session.generate("c", case, 32)["failure_category"] == "input_rejected"


def test_answer_keys_never_reach_the_prompt(fake_torch):
    prompts = []
    item = {**EVIDENCE_CASE, "expected_status": "answered", "gold_answer": "SECRET-KEY",
            "evidence": [{"id": "SYN-1", "text": "synthetic", "review": {"approved": True}}]}
    make_session('{"status":"clarify","answer":"","citations":[]}', prompts=prompts).generate("c", item, 32)
    assert "SECRET-KEY" not in json.dumps(prompts, ensure_ascii=False)
    assert "approved" not in json.dumps(prompts, ensure_ascii=False)


def test_out_of_memory_is_a_resource_failure(fake_torch):
    session = make_session("{}")

    def oom(**_):
        raise type("OutOfMemoryError", (RuntimeError,), {})("synthetic")
    session.model.generate = oom
    result = session.generate("c", EVIDENCE_CASE, 32)
    assert result["execution_status"] == "failed"
    assert result["failure_category"] == "memory_resource_rejection"


# --- loaded-module quantization check ---------------------------------------

def fake_model(quant_type="nf4", nested=True, compute="torch.float16", device="cuda:0"):
    bnb = ModuleType("bitsandbytes")
    Linear4bit = type("Linear4bit", (), {})
    bnb.nn = SimpleNamespace(Linear4bit=Linear4bit)
    named = []
    for i in range(42):  # one 4-bit MLP projection per E4B decoder layer
        layer = Linear4bit()
        layer.weight = SimpleNamespace(quant_state=SimpleNamespace(quant_type=quant_type, nested=nested))
        layer.compute_dtype = compute
        named.append((f"model.language_model.layers.{i}.mlp.down_proj", layer))
    config = {"load_in_4bit": True, "bnb_4bit_quant_type": quant_type, "bnb_4bit_use_double_quant": nested,
              "bnb_4bit_compute_dtype": compute.replace("torch.", "")}
    model = SimpleNamespace(named_modules=lambda: named, parameters=lambda: [SimpleNamespace(device=device)],
                            buffers=lambda: [SimpleNamespace(device=device)],
                            config=SimpleNamespace(quantization_config=config), is_loaded_in_4bit=True)
    return bnb, model


@pytest.mark.parametrize("kwargs,passed", [
    ({}, True), ({"quant_type": "fp4"}, False), ({"nested": False}, False),
    ({"compute": "torch.float32"}, False), ({"device": "cpu"}, False),
])
def test_quantization_is_read_from_loaded_modules(fake_torch, monkeypatch, kwargs, passed):
    bnb, model = fake_model(**kwargs)
    monkeypatch.setitem(sys.modules, "bitsandbytes", bnb)
    report = cuda.quantization_report(model)
    assert report["passed"] is passed
    assert report["parameter_devices"] == [kwargs.get("device", "cuda:0")]


# --- run records, probe CLI and runner adapter ------------------------------

def executed_record(**case):
    from tests.test_cuda_provenance_hardening import valid_record
    record = valid_record()
    record["cases"][0].update(case)
    return record


@pytest.mark.parametrize("mutate", [
    lambda r: r["cases"][0].update(generated_token_count=0),
    lambda r: r["cases"][0].update(output_validation={"passed": False}),
    lambda r: r.update(official_gold_accuracy=1.0),
    lambda r: r.update(environment={}),
    lambda r: r.update(evidence_kind="gold"),
])
def test_run_record_rejects_overclaims(mutate):
    record = executed_record()
    cuda_policy.validate_run_record(record)
    mutate(record)
    with pytest.raises(ValueError):
        cuda_policy.validate_run_record(record)


class SyntheticPrepared:
    def __init__(self, status):
        self.status = status

    def run(self, cases, max_new_tokens, evidence_kind):
        if self.status == "not_executed":
            record = cuda.new_record(max_new_tokens, evidence_kind)
            record["not_executed_reason"] = "synthetic blocker"
            return record
        record = executed_record(case_id="no_evidence")
        if self.status == "generated_but_invalid":
            record["cases"][0].update(execution_status=self.status, output_validation={"passed": False},
                                      raw_output='{"status": "partial"')
            del record["cases"][0]["response"]
        elif self.status == "failed":
            record["cases"][0].update(execution_status=self.status, output_validation={"passed": False},
                                      generated_token_count=None, raw_output=None)
        record["execution_status"] = self.status
        return record


@pytest.mark.parametrize("status,code", [("completed", 0), ("generated_but_invalid", 2),
                                         ("failed", 1), ("not_executed", 3)])
def test_probe_cli_exit_codes_and_no_overwrite(tmp_path, status, code):
    out = tmp_path / "record.json"
    assert probe_gemma4_cuda.main(["--out", str(out)], prepared=SyntheticPrepared(status)) == code
    record = json.loads(out.read_text())
    assert record["execution_status"] == status and record["official_gold_accuracy"] is None
    with pytest.raises(SystemExit):
        probe_gemma4_cuda.main(["--out", str(out)], prepared=SyntheticPrepared(status))


def test_runner_adapter_without_gpu_is_not_executed(tmp_path):
    adapter = runner.CudaTransformersAdapter(max_tokens=32, cache_dir=tmp_path)
    metadata = adapter.get_metadata()
    assert metadata["adapter_type"] == "cuda_transformers" and metadata["available"] is False
    assert metadata["quantization_verified"] is False
    response = adapter.generate({"id": "x", "question": "q", "evidence": []})
    assert response.telemetry["execution_status"] == "not_executed"


def test_runner_adapter_uses_loaded_session(fake_torch):
    raw = json.dumps({"status": "insufficient_evidence", "answer": "", "citations": []})
    prepared = cuda.PreparedRun()
    prepared.session = make_session(raw)
    adapter = runner.CudaTransformersAdapter(max_tokens=32, prepared=prepared)
    response = adapter.generate({"id": "x", "question": "q", "evidence": []})
    assert response.status == "insufficient_evidence" and response.raw_output == raw


# --- reproducible notebook and Colab audit evidence -------------------------

NOTEBOOK = ROOT / "artemis_bootstrap" / "notebooks" / "artemis_gemma4_e4b_cuda_colab.ipynb"
AUDIT = ROOT / "artemis_bootstrap" / "runs" / "colab-t4-20261030"


def test_reproducible_notebook_is_clean_and_pinned():
    text = NOTEBOOK.read_text(encoding="utf-8")
    notebook = json.loads(text)
    assert notebook["nbformat"] == 4
    code = [c for c in notebook["cells"] if c["cell_type"] == "code"]
    assert code and all(not c.get("outputs") and c.get("execution_count") is None for c in code)
    assert REVISION in text and "probe_gemma4_cuda" in text
    # Mission 005-C.1: pinned to an immutable code commit and exact package versions, never a moving branch.
    meta = notebook["metadata"]["waymaker_artemis"]
    assert meta["execution_status"] == "not_reexecuted"
    assert re.fullmatch(r"[0-9a-f]{40}", meta["code_commit"]) and f"CODE_COMMIT = '{meta['code_commit']}'" in text
    assert "--branch" not in text and "feat/" not in text
    for name, version in cuda_policy.configuration()["packages"]["reproduction_pins"].items():
        assert version in text, name
    assert "FREE_TIER_CONFIRMED = False" in text
    assert not re.search(r"hf_[A-Za-z0-9]{20,}", text)
    for forbidden in ("HF_TOKEN=", "/Users/", "@gmail", "userdata.get"):
        assert forbidden not in text


def test_colab_source_notebook_matches_audit_digest():
    audit = json.loads((AUDIT / "colab_execution_audit.json").read_text())
    source = (AUDIT / "source_notebook.ipynb").read_bytes()
    assert hashlib.sha256(source).hexdigest() == audit["source_notebook"]["sha256"]
    assert audit["independently_verified"] is False
    assert audit["official_gold_accuracy"] is None
