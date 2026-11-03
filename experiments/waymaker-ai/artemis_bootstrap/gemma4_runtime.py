"""Bounded offline MLX-VLM worker. JSON on stdin/stdout; no model downloads.

MLX is imported only after checkpoint and resource checks. The parent can kill
this process during a blocked load; the disk/swap guard also runs during load.
"""
from __future__ import annotations

import contextlib
import importlib.metadata
import inspect
import io
import json
import os
import platform
import re
import resource
import shutil
import subprocess
import sys
import threading
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from waymaker_ai import foundation
from waymaker_ai.inference_input import project_inference_item
from waymaker_ai.response_contract import DEFAULT_CONTRACT_VERSION, SYSTEM_PROMPTS, parse_response  # shared with CUDA

PACKAGES = ("mlx", "mlx-metal", "mlx-vlm", "transformers", "tokenizers", "huggingface-hub")


def versions() -> dict:
    result = {}
    for name in PACKAGES:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def resources() -> dict:
    state = {"free_disk_gb": shutil.disk_usage(Path.home()).free / 1e9,
             "swap_used_gb": None, "swap_raw": None, "memory_bytes": None}
    if platform.system() == "Darwin":
        for key, cmd in (("swap_raw", ["sysctl", "-n", "vm.swapusage"]),
                         ("memory_bytes", ["sysctl", "-n", "hw.memsize"])):
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                state[key] = result.stdout.strip()
        match = re.search(r"used = ([\d.]+)M", state["swap_raw"] or "")
        if match:
            state["swap_used_gb"] = float(match.group(1)) * 1024 ** 2 / 1e9
        if state["memory_bytes"]:
            state["memory_bytes"] = int(state["memory_bytes"])
    return state


def resource_blockers(state: dict) -> list[str]:
    limits = foundation.configuration()["runtime"]
    result = []
    if state["free_disk_gb"] < limits["min_free_disk_gb"]:
        result.append(f"Insufficient disk space: {state['free_disk_gb']:.2f} GB; need {limits['min_free_disk_gb']} GB")
    if state["swap_used_gb"] is None:
        result.append("Swap pressure could not be measured")
    elif state["swap_used_gb"] > limits["max_swap_used_gb"]:
        result.append(f"Swap pressure: {state['swap_used_gb']:.2f} GB used; limit {limits['max_swap_used_gb']} GB")
    return result


def probe() -> dict:
    installed = versions()
    problems = []
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        problems.append("MLX-VLM requires macOS Apple Silicon")
    expected = foundation.configuration()["runtime"]["package_version"]
    if installed["mlx-vlm"] != expected:
        problems.append(f"mlx-vlm {expected} not installed (found {installed['mlx-vlm']})")
    if not problems:
        try:
            from mlx_vlm import load, generate  # noqa: F401
            from mlx_vlm.prompt_utils import apply_chat_template  # noqa: F401
            from mlx_vlm.models.gemma4 import Model  # noqa: F401
        except Exception as exc:
            problems.append(f"Runtime import failed: {type(exc).__name__}: {exc}")
    return {"packages": installed, "python": sys.version, "problems": problems}


def build_messages(item: dict, version: str = DEFAULT_CONTRACT_VERSION) -> list[dict]:
    projected = project_inference_item(item)
    return [
        {"role": "system", "content": SYSTEM_PROMPTS[version]},
        {"role": "user", "content": json.dumps(projected, ensure_ascii=False)},
    ]


def inspect_runtime_compatibility() -> dict:
    """Initialize only the real processor/tokenizer, never model weights."""
    from mlx_vlm import load, generate
    from mlx_vlm.models.gemma4 import Model
    from mlx_vlm.utils import load_processor
    from mlx_vlm.prompt_utils import apply_chat_template
    import mlx.core as mx

    selected = foundation.profile("gemma4_e4b")
    snapshot = foundation.find_snapshot(selected)
    if snapshot is None:
        raise FileNotFoundError("Pinned E4B checkpoint missing; no download")
    started = time.perf_counter()
    verified = foundation.validate_snapshot(snapshot, selected)
    before = resources()
    processor = load_processor(snapshot, local_files_only=True, trust_remote_code=False)
    if type(processor).__name__ != selected["processor_class"]:
        raise ValueError("Incompatible processor class")
    config = json.loads((snapshot / "config.json").read_text())
    messages = build_messages({"question": "체류기간을 연장하려면 어떤 사항을 확인해야 하나요?", "evidence": []})
    prompt = apply_chat_template(processor, config, messages, num_images=0, num_audios=0, enable_thinking=False)
    limits = foundation.configuration()["runtime"]
    mx.set_memory_limit(int(limits["memory_limit_gb"] * 1e9))
    mx.set_cache_limit(256 * 1024 ** 2)
    return {"kind": "processor_and_api_compatibility_only_no_model_weights", "compatibility_status": "passed",
            "inference_execution_status": "not_executed", "highest_completed_stage": "processor_and_template_initialized",
            "model": selected["inference_checkpoint"], "revision": selected["inference_revision"],
            "checkpoint_verification": verified, "runtime_probe": probe(),
            "processor_class": type(processor).__name__, "tokenizer_class": type(processor.tokenizer).__name__,
            "gemma4_model_class": f"{Model.__module__}.{Model.__name__}",
            "signatures": {"load": str(inspect.signature(load)), "generate": str(inspect.signature(generate)),
                           "apply_chat_template": str(inspect.signature(apply_chat_template))},
            "memory_control_apis": ["set_memory_limit", "set_cache_limit", "get_peak_memory"],
            "input_messages": messages, "rendered_prompt": prompt, "input_tokens": len(processor.tokenizer.encode(prompt)),
            "elapsed_seconds": time.perf_counter() - started,
            "resources_before": before, "resources_after": resources(),
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def execute(request: dict) -> dict:
    selected = foundation.profile(request["profile"])
    snapshot = Path(request["snapshot"])
    verified = foundation.validate_snapshot(snapshot, selected)
    limits = foundation.configuration()["runtime"]
    max_tokens = request["max_tokens"]
    if not isinstance(max_tokens, int) or not 1 <= max_tokens <= limits["max_generation_tokens"]:
        raise ValueError("Generation token limit exceeded")
    before = resources()
    blockers = resource_blockers(before)
    runtime = probe()
    after_imports = resources()
    blockers.extend(resource_blockers(after_imports))
    blockers.extend(runtime["problems"])
    if blockers:
        return {"execution_status": "not_executed", "error": "; ".join(blockers),
                "failure_category": "memory_resource_rejection" if resource_blockers(before) or resource_blockers(after_imports) else "dependency_or_import_failure",
                "highest_completed_stage": "checkpoint_verified",
                "resources_before": before, "resources_after_imports": after_imports, **runtime, **verified}

    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    import mlx.core as mx

    mx.set_memory_limit(int(limits["memory_limit_gb"] * 1e9))
    mx.set_cache_limit(256 * 1024 ** 2)
    stop = threading.Event()

    def guard() -> None:
        while not stop.wait(2):
            if resource_blockers(resources()):
                # Parent records this exit code and the post-abort resources.
                os._exit(75)

    threading.Thread(target=guard, daemon=True).start()
    telemetry = {"resources_before": before, "resources_after_imports": after_imports, **runtime, **verified}
    raw = None
    stage, highest = "model_loading", "checkpoint_verified"
    try:
        start = time.perf_counter()
        model, processor = load(str(snapshot), lazy=False, strict=True, trust_remote_code=False)
        mx.eval(model.parameters())
        telemetry["load_seconds"] = time.perf_counter() - start
        highest, stage = "model_loaded", "processor_initialization"
        if not hasattr(processor, "tokenizer") or not callable(getattr(processor, "apply_chat_template", None)):
            raise ValueError("Runtime did not return a compatible processor/tokenizer")
        telemetry["processor_class"] = type(processor).__name__
        telemetry["tokenizer_class"] = type(processor.tokenizer).__name__
        highest, stage = "processor_initialized", "prompt_preparation"
        config = json.loads((snapshot / "config.json").read_text())
        version = request.get("contract_version", DEFAULT_CONTRACT_VERSION)
        prompt = apply_chat_template(processor, config, build_messages(request["item"], version),
                                     num_images=0, num_audios=0, enable_thinking=False)
        prompt_tokens = len(processor.tokenizer.encode(prompt))
        telemetry.update(rendered_prompt=prompt, input_messages=build_messages(request["item"], version),
                         contract_version=version,
                         input_token_count_before_generation=prompt_tokens)
        if prompt_tokens > limits["max_prompt_tokens"]:
            raise ValueError(f"Prompt exceeds {limits['max_prompt_tokens']} tokens; no truncation performed")
        highest, stage = "prompt_prepared", "generation"
        start = time.perf_counter()
        output = generate(model, processor, prompt, max_tokens=max_tokens,
                          temperature=request["temperature"], enable_thinking=False, verbose=False)
        telemetry["generation_wall_seconds"] = time.perf_counter() - start
        raw = output.text
        for key in ("prompt_tokens", "generation_tokens", "prompt_tps", "generation_tps", "finish_reason"):
            telemetry[key] = getattr(output, key, None)
        if not isinstance(telemetry["generation_tokens"], int) or telemetry["generation_tokens"] <= 0:
            return {"execution_status": "failed", "failure_category": "generation_no_tokens",
                    "highest_completed_stage": highest, "error": "Runtime reported no generated tokens",
                    "raw_output": raw, "telemetry": telemetry}
        highest, stage = "tokens_generated", "output_validation"
        telemetry["prefill_seconds_derived"] = (
            output.prompt_tokens / output.prompt_tps if output.prompt_tps else None)
        telemetry["decode_seconds_derived"] = (
            output.generation_tokens / output.generation_tps if output.generation_tps else None)
        try:
            parsed = parse_response(raw, {e["id"] for e in request["item"].get("evidence", [])}, version)
        except (ValueError, TypeError) as exc:
            return {"execution_status": "generated_but_invalid", "failure_category": "successful_generation_invalid_json",
                    "highest_completed_stage": highest, "error": f"{type(exc).__name__}: {exc}",
                    "output_validation": {"passed": False, "possible_token_limit_truncation":
                        telemetry["generation_tokens"] >= max_tokens or telemetry["finish_reason"] in {"length", "max_tokens"}},
                    "raw_output": raw, "telemetry": telemetry}
        return {"execution_status": "completed", "response": parsed, "raw_output": raw,
                "highest_completed_stage": "structured_output_validated", "output_validation": {"passed": True},
                "telemetry": telemetry}
    except Exception as exc:
        categories = {"model_loading": "model_loading_error", "processor_initialization": "processor_incompatibility",
                      "prompt_preparation": "processor_incompatibility", "generation": "generation_runtime_error"}
        category = ("runtime_crash_or_timeout" if isinstance(exc, TimeoutError) else "memory_resource_rejection"
                    if isinstance(exc, MemoryError) else "generation_api_incompatibility"
                    if stage == "generation" and isinstance(exc, TypeError) else categories.get(stage, "runtime_error"))
        return {"execution_status": "failed", "error": f"{type(exc).__name__}: {exc}",
                "failure_category": category, "highest_completed_stage": highest,
                "raw_output": raw, "telemetry": telemetry}
    finally:
        stop.set()
        telemetry.update(resources_after=resources(), peak_mlx_memory_bytes=mx.get_peak_memory(),
                         peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def main() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result = (probe() if "--probe" in sys.argv else inspect_runtime_compatibility()
                      if "--inspect-runtime" in sys.argv else execute(json.load(sys.stdin)))
        except Exception as exc:
            result = {"execution_status": "failed", "error": f"{type(exc).__name__}: {exc}"}
    result["warnings"] = [str(w.message) for w in caught]
    result["runtime_stdout"] = captured.getvalue()[-4000:]
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
