"""Synthetic API results test execution classification, never model performance."""
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import gemma4_runtime as runtime


@pytest.fixture
def synthetic_worker(monkeypatch, tmp_path):
    mx = ModuleType("mlx.core")
    mx.set_memory_limit = lambda *_: None
    mx.set_cache_limit = lambda *_: None
    mx.eval = lambda *_: None
    mx.get_peak_memory = lambda: 123
    mlx = ModuleType("mlx")
    mlx.core = mx
    vlm = ModuleType("mlx_vlm")
    vlm.snapshot = tmp_path
    (tmp_path / "config.json").write_text('{"model_type":"gemma4"}')
    vlm.generate = lambda *_, **__: output("synthetic")
    processor = type("Gemma4Processor", (SimpleNamespace,), {})(tokenizer=SimpleNamespace(encode=lambda _: [1, 2]),
                                apply_chat_template=lambda *_: "synthetic")
    vlm.processor = processor
    vlm.load = lambda *_, **__: (SimpleNamespace(parameters=lambda: {}), processor)
    prompt_utils = ModuleType("mlx_vlm.prompt_utils")
    prompt_utils.apply_chat_template = lambda *_, **__: "synthetic rendered prompt"
    for name, module in {"mlx": mlx, "mlx.core": mx, "mlx_vlm": vlm,
                         "mlx_vlm.prompt_utils": prompt_utils}.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(runtime.foundation, "validate_snapshot", lambda *_: {"checkpoint_integrity_verified": True})
    monkeypatch.setattr(runtime, "resources", lambda: {"free_disk_gb": 20, "swap_used_gb": 0})
    monkeypatch.setattr(runtime, "probe", lambda: {"problems": [], "packages": {"mlx-vlm": "synthetic"}})
    return vlm


def request(snapshot):
    return {"profile": "gemma4_e4b", "snapshot": str(snapshot),
            "max_tokens": 32, "temperature": 0, "item": {"question": "synthetic", "evidence": []}}


def output(text, tokens=7, finish_reason="length"):
    return SimpleNamespace(text=text, generation_tokens=tokens, prompt_tokens=2,
                           prompt_tps=10, generation_tps=5, finish_reason=finish_reason)


def test_generated_invalid_json_is_distinct_from_load_failure(synthetic_worker):
    synthetic_worker.generate = lambda *_, **__: output('{"status":')
    result = runtime.execute(request(synthetic_worker.snapshot))
    assert result["execution_status"] == "generated_but_invalid"
    assert result["failure_category"] == "successful_generation_invalid_json"
    assert result["highest_completed_stage"] == "tokens_generated"
    assert result["raw_output"] == '{"status":'
    assert result["telemetry"]["generation_tokens"] == 7
    assert result["telemetry"]["finish_reason"] == "length"
    assert result["output_validation"]["passed"] is False


def test_completed_requires_tokens_and_valid_structure(synthetic_worker):
    raw = json.dumps({"status": "insufficient_evidence", "answer": "synthetic", "citations": []})
    synthetic_worker.generate = lambda *_, **__: output(raw, finish_reason="stop")
    result = runtime.execute(request(synthetic_worker.snapshot))
    assert result["execution_status"] == "completed"
    assert result["highest_completed_stage"] == "structured_output_validated"
    assert result["telemetry"]["rendered_prompt"] == "synthetic rendered prompt"
    assert result["output_validation"]["passed"] is True
    assert result["raw_output"] == raw


def test_zero_tokens_cannot_be_completed(synthetic_worker):
    synthetic_worker.generate = lambda *_, **__: output('{"status":"answered","answer":"","citations":[]}', tokens=0)
    result = runtime.execute(request(synthetic_worker.snapshot))
    assert result["execution_status"] == "failed"
    assert result["failure_category"] == "generation_no_tokens"


def test_resources_are_rechecked_after_runtime_imports(synthetic_worker, monkeypatch):
    state = {"free_disk_gb": 20, "swap_used_gb": 0}
    monkeypatch.setattr(runtime, "resources", lambda: dict(state))
    def import_probe():
        state["swap_used_gb"] = 3
        return {"problems": []}
    monkeypatch.setattr(runtime, "probe", import_probe)
    synthetic_worker.load = lambda *_, **__: pytest.fail("Unsafe model load after import pressure")
    result = runtime.execute(request(synthetic_worker.snapshot))
    assert result["execution_status"] == "not_executed"
    assert result["failure_category"] == "memory_resource_rejection"


def test_model_load_error_is_not_generated_output(synthetic_worker):
    def fail(*_, **__):
        raise ValueError("synthetic weight load failure")
    synthetic_worker.load = fail
    result = runtime.execute(request(synthetic_worker.snapshot))
    assert result["execution_status"] == "failed"
    assert result["failure_category"] == "model_loading_error"
    assert result["raw_output"] is None
    assert result["highest_completed_stage"] == "checkpoint_verified"


def test_processor_inspection_uses_path_and_never_loads_weights(synthetic_worker, monkeypatch):
    utils = ModuleType("mlx_vlm.utils")
    def processor_only(path, **kwargs):
        assert isinstance(path, Path)
        assert kwargs["local_files_only"] is True
        return synthetic_worker.processor
    utils.load_processor = processor_only
    gemma = ModuleType("mlx_vlm.models.gemma4")
    gemma.Model = type("SyntheticModelClass", (), {})
    monkeypatch.setitem(sys.modules, "mlx_vlm.utils", utils)
    monkeypatch.setitem(sys.modules, "mlx_vlm.models.gemma4", gemma)
    monkeypatch.setattr(runtime.foundation, "find_snapshot", lambda *_: synthetic_worker.snapshot)
    synthetic_worker.load = lambda *_, **__: pytest.fail("Processor inspection must not load weights")
    result = runtime.inspect_runtime_compatibility()
    assert result["compatibility_status"] == "passed"
    assert result["inference_execution_status"] == "not_executed"


@pytest.mark.parametrize("status,exit_code", [("completed", 0), ("generated_but_invalid", 2), ("failed", 1), ("not_executed", 3)])
def test_probe_preserves_worker_status_and_raw_output(tmp_path, monkeypatch, status, exit_code):
    import probe_gemma4
    class SyntheticAdapter:
        def __init__(self, **kwargs):
            assert kwargs["max_tokens"] == 32
        def get_metadata(self):
            return {"available": status != "not_executed", "not_available_reason": "synthetic blocker",
                    "inference_kind": "mock", "checkpoint_integrity_verified": False}
        def generate(self, item):
            assert item["evidence"] == []
            return SimpleNamespace(raw_output="synthetic unchanged output", error=None, telemetry={
                "execution_status": status, "highest_completed_stage": "synthetic", "output_validation": {"passed": status == "completed"},
                "telemetry": {"generation_tokens": 7}})
    monkeypatch.setattr(probe_gemma4, "LocalModelAdapter", SyntheticAdapter)
    monkeypatch.setattr(probe_gemma4, "resources", lambda: {"free_disk_gb": 20, "swap_used_gb": 0})
    out = tmp_path / "synthetic.json"
    assert probe_gemma4.main(["--out", str(out)]) == exit_code
    record = json.loads(out.read_text())
    assert record["execution_status"] == status
    assert record["official_gold_accuracy"] is None
    assert record["raw_generated_response"] == (None if status == "not_executed" else "synthetic unchanged output")
    if status != "not_executed":
        assert record["not_executed_reason"] is None
