"""Offline recovery regressions: identity, provenance and runtime boundaries.

Tiny checkpoint fixtures are explicitly synthetic, never inference evidence.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from waymaker_ai import foundation
from waymaker_ai.distillation import experiment_config

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import artemis_runner as runner
import gemma4_runtime as runtime
import guardrail_shadow


def synthetic_snapshot(tmp_path, name="gemma4_e4b"):
    selected = copy.deepcopy(foundation.profile(name))
    path = tmp_path / ("models--" + selected["inference_checkpoint"].replace("/", "--")) / "snapshots" / selected["inference_revision"]
    path.mkdir(parents=True)
    config = {"model_type": "gemma4", "architectures": selected["architectures"],
              "text_config": selected["text_config"], "quantization": selected["quantization"]}
    files = {"config.json": json.dumps(config), "processor_config.json": json.dumps({"processor_class": "Gemma4Processor"}),
             "tokenizer_config.json": "{}", "chat_template.jinja": "synthetic template", "README.md": "synthetic fixture"}
    for name, value in files.items():
        (path / name).write_text(value)
    selected["metadata_sha256"] = {name: hashlib.sha256((path / name).read_bytes()).hexdigest() for name in files}
    (path / "model.safetensors").write_bytes(b"synthetic-not-weights")
    (path / "tokenizer.json").write_text("{}")
    (path / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {"synthetic": "model.safetensors"}}))
    return path, selected


def test_canonical_foundation_and_runtime():
    cfg = foundation.configuration()
    adapter = runner.LocalModelAdapter()
    assert cfg["project"]["name"] == "Waymaker Artemis"
    assert adapter.profile == "gemma4_e4b"
    assert adapter.model_name == "mlx-community/gemma-4-e4b-it-4bit"
    assert adapter.revision == foundation.profile()["inference_revision"]
    assert adapter.runtime == "mlx_vlm"
    assert cfg["allow_implicit_fallback"] is False


@pytest.mark.parametrize("model", ["mlx-community/gemma-3-270m-it-4bit", "Qwen/Qwen3-4B", "google/gemma-2-9b-it"])
def test_noncanonical_models_are_rejected(model):
    with pytest.raises(ValueError, match="Checkpoint"):
        runner.LocalModelAdapter(model_name=model)


def test_no_runtime_or_revision_fallback():
    with pytest.raises(ValueError, match="runtime"):
        runner.LocalModelAdapter(runtime="mlx_lm")
    with pytest.raises(ValueError, match="Revision"):
        runner.LocalModelAdapter(revision="a" * 40)


def test_exact_snapshot_only(tmp_path):
    snapshot, selected = synthetic_snapshot(tmp_path)
    assert foundation.find_snapshot(selected, tmp_path) == snapshot
    snapshot.rename(snapshot.with_name("b" * 40))
    assert foundation.find_snapshot(selected, tmp_path) is None


@pytest.mark.parametrize("mutation", ["family", "layers", "processor", "quantization", "template", "weights"])
def test_incompatible_checkpoint_is_rejected(tmp_path, mutation):
    snapshot, selected = synthetic_snapshot(tmp_path)
    assert foundation.validate_snapshot(snapshot, selected)["checkpoint_metadata_verified"]
    config = json.loads((snapshot / "config.json").read_text())
    if mutation == "family":
        config["model_type"] = "other"
    elif mutation == "layers":
        config["text_config"]["num_hidden_layers"] = 35
    elif mutation == "quantization":
        config["quantization"]["bits"] = 8
    elif mutation == "processor":
        (snapshot / "processor_config.json").write_text('{"processor_class":"OtherProcessor"}')
    elif mutation == "template":
        (snapshot / "chat_template.jinja").write_text("tampered")
    elif mutation == "weights":
        (snapshot / "model.safetensors").unlink()
    if mutation in {"family", "layers", "quantization"}:
        (snapshot / "config.json").write_text(json.dumps(config))
    with pytest.raises((ValueError, OSError)):
        foundation.validate_snapshot(snapshot, selected)


def test_missing_checkpoint_produces_not_executed(tmp_path, monkeypatch):
    adapter = runner.LocalModelAdapter(cache_dir=tmp_path / "empty")
    monkeypatch.setattr(adapter, "_probe", lambda: {"problems": []})
    monkeypatch.setattr(adapter, "generate", lambda *_: pytest.fail("must not generate"))
    report = runner.ArtemisEvaluationRunner(adapter, out_dir=tmp_path / "run").run()
    assert report.execution_status == runner.ExecutionStatus.NOT_EXECUTED
    assert report.item_results == []
    assert "not found" in report.not_executed_reason
    assert report.suite_summary.official_gold_pass_rate is None
    assert report.model_metadata["model_revision"] == foundation.profile()["inference_revision"]
    assert "N/A (평가 문항 없음)" in (tmp_path / "run" / "report.md").read_text()
    assert b"\r" not in (tmp_path / "run" / "error_summary.csv").read_bytes()


def real_meta(profile):
    selected = foundation.profile(profile)
    return {"inference_kind": "real_inference", "profile": profile, "runtime": "mlx_vlm",
            "model_name": selected["inference_checkpoint"], "model_revision": selected["inference_revision"],
            "checkpoint_metadata_verified": True}


def test_e2b_requires_explicit_profile_and_has_separate_metrics():
    model = foundation.profile("gemma4_e2b")["inference_checkpoint"]
    with pytest.raises(ValueError):
        runner.LocalModelAdapter(model_name=model)
    assert runner.LocalModelAdapter(profile="gemma4_e2b").selected["architecture"] == "E2B"
    assert foundation.metric_group(real_meta("gemma4_e4b")) != foundation.metric_group(real_meta("gemma4_e2b"))


def test_cross_model_and_mock_metrics_rejected():
    reports = [{"model_metadata": real_meta("gemma4_e4b"), "benchmark_metadata": {"benchmark_sha256": "same"}, "mode": "candidate_eval"}]
    assert foundation.require_same_metric_group(reports)
    for meta in (real_meta("gemma4_e2b"), runner.MockModelAdapter().get_metadata()):
        with pytest.raises(ValueError, match="cannot be pooled"):
            foundation.require_same_metric_group(reports + [{**reports[0], "model_metadata": meta}])
    fake = {**real_meta("gemma4_e4b"), "model_revision": "f" * 40}
    with pytest.raises(ValueError):
        foundation.metric_group(fake)


def test_prompt_excludes_answer_keys_and_rubrics():
    messages = runtime.build_messages({"question": "question", "expected": {"secret": "KEY"},
                                       "rubric": "KEY", "evidence": [{"id": "E", "text": "evidence"}]})
    assert "KEY" not in json.dumps(messages)
    assert '"text": "evidence"' in messages[1]["content"]


@pytest.mark.parametrize("raw", ['not json', '{"status":"answered","answer":"x","citations":["unlisted"]}',
                                  '{"status":"answered","answer":1,"citations":[]}'])
def test_structured_response_fails_closed(raw):
    with pytest.raises(ValueError):
        runtime.parse_response(raw, {"allowed"})


def test_shadow_does_not_auto_load_legacy_run(tmp_path):
    report = guardrail_shadow.run_full_shadow_evaluation(output_json=tmp_path / "out.json", output_md=tmp_path / "out.md")
    assert report["groups"]["real_model_inference"] is None
    recorded = tmp_path / "fake.json"
    recorded.write_text(json.dumps({"model_metadata": runner.MockModelAdapter().get_metadata(), "execution_status": "completed"}))
    with pytest.raises(ValueError, match="provenance-verified"):
        guardrail_shadow.run_full_shadow_evaluation(real_run_summary_path=recorded, output_json=tmp_path / "out2.json", output_md=tmp_path / "out2.md")


def test_training_configs_share_audited_identity():
    for path in experiment_config.config_paths():
        config = experiment_config.load_config(path)
        assert config.base_model.repo_id == foundation.profile()["upstream"]
        data = copy.deepcopy(config.data)
        data["base_model"]["repo_id"] = "google/gemma-3-270m-it"
        with pytest.raises(experiment_config.ConfigError):
            experiment_config.parse_config(data)


def test_resource_guard_blocks_disk_and_swap():
    problems = runtime.resource_blockers({"free_disk_gb": 1.0, "swap_used_gb": 8.0})
    assert len(problems) == 2


def test_runtime_worker_receives_offline_environment_and_records_output(tmp_path, monkeypatch):
    adapter = runner.LocalModelAdapter(cache_dir=tmp_path, max_tokens=32)
    monkeypatch.setattr(adapter, "check_availability", lambda: (True, None))
    monkeypatch.setattr(adapter, "_find_snapshot_path", lambda: tmp_path)
    def invoke(cmd, **kwargs):
        assert kwargs["env"]["HF_HUB_OFFLINE"] == "1"
        request = json.loads(kwargs["input"])
        assert request["max_tokens"] == 32 and "expected" not in request["item"]
        assert cmd[1].endswith("gemma4_runtime.py")
        return SimpleNamespace(returncode=0, stderr="warning", stdout=json.dumps({
            "execution_status": "completed", "response": {"status": "insufficient_evidence", "answer": "fixture", "citations": []},
            "raw_output": "fixture raw", "telemetry": {"generation_tokens": 3}}))
    monkeypatch.setattr(runner.subprocess, "run", invoke)
    response = adapter.generate({"question": "q", "expected": "secret"})
    assert response.raw_output == "fixture raw"
    assert response.telemetry["telemetry"]["generation_tokens"] == 3
    assert response.telemetry["stderr"] == "warning"


def test_run_artifacts_cannot_be_overwritten(tmp_path):
    instance = runner.ArtemisEvaluationRunner(runner.MockModelAdapter(), mode=runner.EvaluationMode.INFRA_VALIDATION, out_dir=tmp_path)
    instance.run()
    with pytest.raises(FileExistsError):
        instance.run()


def test_smoke_probes_its_own_interpreter_and_records_blocker(tmp_path, monkeypatch):
    import run_smoke
    monkeypatch.setenv("ARTEMIS_MLX_PYTHON", "/unrelated/python")
    def unavailable(self):
        assert self.python_executable == sys.executable
        return False, "Offline checkpoint not found"
    monkeypatch.setattr(run_smoke.LocalModelAdapter, "check_availability", unavailable)
    monkeypatch.setattr(run_smoke, "free_disk_gb", lambda: 0.5)
    out = tmp_path / "smoke"
    assert run_smoke.main(["--out", str(out)]) == 3
    record = json.loads((out / "run_record.json").read_text())
    assert record["status"] == "not_executed"
    assert "checkpoint not found" in record["reason"]
    assert "disk space" in record["reason"]
    assert record["results"] == []


def test_identity_guard_checks_hidden_launch_configuration(tmp_path):
    import check_model_identity
    boot = tmp_path / "artemis_bootstrap"
    boot.mkdir()
    for entry in ("artemis_runner.py", "run_smoke.py"):
        (boot / entry).write_text("foundation.select_profile\n")
    (boot / ".env.local").write_text("MODEL=mlx-community/gemma-3-270m-it-4bit\n")
    result = check_model_identity.audit(tmp_path)
    assert result["status"] == "FAIL"
    assert "artemis_bootstrap/.env.local" in result["violations"]
