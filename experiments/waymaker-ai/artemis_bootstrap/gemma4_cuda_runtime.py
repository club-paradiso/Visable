"""Offline Gemma 4 E4B inference on one CUDA GPU (Transformers + bitsandbytes NF4).

A separate path from the MLX-VLM worker (gemma4_runtime.py), which it does not
replace. It loads the official upstream checkpoint at a pinned revision and
quantizes at load time. torch/transformers are imported only after the snapshot
and package checks pass; nothing is downloaded. The prompt and the response
contract are the MLX worker's, so outputs are comparable, but the two runtimes
never share a metric group (cuda_policy).
"""
from __future__ import annotations

import contextlib
import importlib.metadata
import io
import json
import os
import platform
import re
import subprocess
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from waymaker_ai import cuda_policy
from waymaker_ai.inference_input import project_inference_item
from gemma4_runtime import build_messages, parse_response

PACKAGES = ("torch", "transformers", "bitsandbytes", "accelerate", "huggingface-hub", "tokenizers")
QUANTIZATION_LABEL = "bnb_nf4_double_quant_fp16"


def versions() -> dict:
    result = {}
    for name in PACKAGES:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def version_tuple(value: str) -> tuple:
    return tuple(int(p) for p in re.findall(r"\d+", value.split("+")[0])[:3])


def nvidia_smi() -> dict | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,driver_version",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    name, total, used, free, driver = [p.strip() for p in result.stdout.splitlines()[0].split(",")]
    return {"name": name, "memory_total_mib": int(total), "memory_used_mib": int(used),
            "memory_free_mib": int(free), "driver_version": driver}


def probe() -> dict:
    """Package and device checks. Imports torch only when it is installed."""
    policy = cuda_policy.configuration()
    installed = versions()
    problems = []
    for name, minimum in policy["packages"]["minimum"].items():
        found = installed.get(name)
        if found is None:
            problems.append(f"{name} not installed")
        elif version_tuple(found) < version_tuple(minimum):
            problems.append(f"{name} {found} is older than the supported minimum {minimum}")
    device = None
    if installed["torch"] is not None:
        try:
            import torch
            if not torch.cuda.is_available():
                problems.append("No CUDA GPU visible to PyTorch")
            else:
                props = torch.cuda.get_device_properties(0)
                device = {"name": props.name, "total_memory_bytes": props.total_memory,
                          "capability": f"{props.major}.{props.minor}", "torch_cuda": torch.version.cuda}
                if props.total_memory < policy["limits"]["min_total_vram_gib"] * 1024 ** 3:
                    problems.append(f"GPU memory {props.total_memory / 1024 ** 3:.2f} GiB is below "
                                    f"{policy['limits']['min_total_vram_gib']} GiB")
        except Exception as exc:
            problems.append(f"PyTorch CUDA probe failed: {type(exc).__name__}: {exc}")
    return {"packages": installed, "python": sys.version.split()[0], "platform": platform.platform(),
            "cuda_device": device, "nvidia_smi": nvidia_smi(), "problems": problems}


def preflight(cache_dir: Path | None = None, verify_weights: bool = True) -> dict:
    """Everything that can be checked without loading weights onto a GPU."""
    blockers, verified = [], {}
    snapshot = cuda_policy.find_snapshot(cache_dir)
    model = cuda_policy.configuration()["model"]
    if snapshot is None:
        blockers.append(f"Offline checkpoint not found: {model['checkpoint']}@{model['revision']}; no download or fallback")
    else:
        try:
            verified = cuda_policy.validate_snapshot(snapshot, verify_weights=verify_weights)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            blockers.append(f"Incompatible checkpoint: {exc}")
    runtime = probe()
    blockers.extend(runtime["problems"])
    return {"blockers": blockers, "snapshot": str(snapshot) if snapshot else None,
            "verified": verified, "probe": runtime}


def validate_input(item: dict) -> dict:
    projected = project_inference_item(item)
    ids = [e["id"] for e in projected["evidence"]]
    if any(not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Evidence IDs must be non-empty and unique")
    return projected


def quantization_report(model) -> dict:
    """Inspect the loaded modules rather than trusting the requested config."""
    import bitsandbytes as bnb
    import torch
    linear4 = [m for m in model.modules() if isinstance(m, bnb.nn.Linear4bit)]
    plain = sum(1 for m in model.modules() if type(m) is torch.nn.Linear)
    quant_types, nested, compute = set(), set(), set()
    for module in linear4:
        state = getattr(module.weight, "quant_state", None)
        quant_types.add(getattr(state, "quant_type", None) or getattr(module.weight, "quant_type", None))
        nested.add(bool(getattr(state, "nested", False)))
        compute.add(str(getattr(module, "compute_dtype", None)).replace("torch.", ""))
    config = getattr(model.config, "quantization_config", None)
    config = config.to_dict() if hasattr(config, "to_dict") else dict(config or {})
    # hf_device_map is absent for a single-device map; read parameter devices instead.
    devices = sorted({str(p.device) for p in model.parameters()})
    passed = (bool(linear4) and quant_types == {"nf4"} and nested == {True} and compute == {"float16"}
              and config.get("bnb_4bit_quant_type") == "nf4" and config.get("load_in_4bit") is True
              and devices == ["cuda:0"])
    return {"passed": passed, "linear4bit_modules": len(linear4), "unquantized_linear_modules": plain,
            "quant_types": sorted(map(str, quant_types)), "double_quant": sorted(nested),
            "compute_dtypes": sorted(compute), "loaded_quantization_config": config,
            "parameter_devices": devices, "is_loaded_in_4bit": getattr(model, "is_loaded_in_4bit", None)}


class TimingStreamer:
    """generate() calls put() once with the prompt, then once per new token."""

    def __init__(self):
        self.first_token_at = None
        self._calls = 0

    def put(self, _value):
        self._calls += 1
        if self._calls == 2 and self.first_token_at is None:
            self.first_token_at = time.perf_counter()

    def end(self):
        pass


def finish_reason(token_ids: list[int], eos_ids: set[int], max_new_tokens: int) -> str:
    if token_ids and token_ids[-1] in eos_ids:
        return "eos"
    if len(token_ids) >= max_new_tokens:
        return "length"
    return "unknown"


class CudaSession:
    """One loaded model reused across cases; load once per Colab runtime."""

    def __init__(self, snapshot: str):
        self.snapshot = snapshot
        self.model = self.processor = None
        self.load_telemetry = {}

    def load(self) -> dict:
        import torch
        from transformers import AutoModelForMultimodalLM, AutoProcessor, BitsAndBytesConfig
        policy = cuda_policy.configuration()
        processor = AutoProcessor.from_pretrained(self.snapshot, local_files_only=True, trust_remote_code=False)
        if type(processor).__name__ != policy["model"]["processor_class"]:
            raise ValueError(f"Incompatible processor class: {type(processor).__name__}")
        q = policy["quantization"]
        config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type=q["bnb_4bit_quant_type"],
                                    bnb_4bit_use_double_quant=q["bnb_4bit_use_double_quant"],
                                    bnb_4bit_compute_dtype=torch.float16)
        torch.cuda.reset_peak_memory_stats()
        start = time.perf_counter()
        model = AutoModelForMultimodalLM.from_pretrained(
            self.snapshot, local_files_only=True, trust_remote_code=False, quantization_config=config,
            device_map={"": 0}, dtype=torch.float16)
        model.eval()
        torch.cuda.synchronize()
        self.load_telemetry = {
            "load_seconds": time.perf_counter() - start,
            "load_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "load_peak_reserved_bytes": torch.cuda.max_memory_reserved(),
            "model_class": type(model).__name__, "processor_class": type(processor).__name__,
            "tokenizer_class": type(processor.tokenizer).__name__,
            "quantization": quantization_report(model), "nvidia_smi_after_load": nvidia_smi()}
        self.model, self.processor = model, processor
        return self.load_telemetry

    def generate(self, case_id: str, item: dict, max_new_tokens: int) -> dict:
        import torch
        limits = cuda_policy.configuration()["limits"]
        result = {"case_id": case_id, "execution_status": "failed", "raw_output": None,
                  "generated_token_count": None, "output_validation": {"passed": False}}
        stage = "input_validation"
        try:
            if not isinstance(max_new_tokens, int) or not 1 <= max_new_tokens <= limits["max_generation_tokens"]:
                raise ValueError("Generation token limit exceeded")
            projected = validate_input(item)
            messages = build_messages(projected)
            stage = "prompt_preparation"
            inputs = self.processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, enable_thinking=False,
                return_dict=True, return_tensors="pt").to(self.model.device)
            prompt_tokens = int(inputs["input_ids"].shape[-1])
            result.update(input_messages=messages, prompt_tokens=prompt_tokens)
            if prompt_tokens > limits["max_prompt_tokens"]:
                raise ValueError(f"Prompt exceeds {limits['max_prompt_tokens']} tokens; no truncation performed")
            stage = "generation"
            streamer = TimingStreamer()
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
            start = time.perf_counter()
            with torch.inference_mode():
                output = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                                             streamer=streamer)
            torch.cuda.synchronize()
            wall = time.perf_counter() - start
            new_ids = output[0, prompt_tokens:].tolist()
            eos = self.model.generation_config.eos_token_id
            eos_ids = set(eos if isinstance(eos, (list, tuple)) else [eos] if eos is not None else [])
            raw = self.processor.tokenizer.decode(new_ids, skip_special_tokens=True)
            first = streamer.first_token_at - start if streamer.first_token_at else None
            result.update(
                raw_output=raw, generated_token_count=len(new_ids),
                finish_reason=finish_reason(new_ids, eos_ids, max_new_tokens),
                metrics={"wall_seconds": wall, "first_token_seconds_including_prefill": first,
                         "tokens_per_second_including_prefill": len(new_ids) / wall if wall else None,
                         "decode_tokens_per_second": (len(new_ids) - 1) / (wall - first)
                         if first is not None and len(new_ids) > 1 and wall > first else None,
                         "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                         "peak_reserved_bytes": torch.cuda.max_memory_reserved()})
            if not new_ids:
                result.update(failure_category="generation_no_tokens", error="No tokens generated")
                return result
            stage = "output_validation"
            try:
                parsed = parse_response(raw, {e["id"] for e in projected["evidence"]})
            except (ValueError, TypeError) as exc:
                result.update(execution_status="generated_but_invalid",
                              failure_category="successful_generation_invalid_json",
                              error=f"{type(exc).__name__}: {exc}",
                              output_validation={"passed": False, "possible_token_limit_truncation":
                                                 result["finish_reason"] == "length"})
                return result
            result.update(execution_status="completed", response=parsed, output_validation={"passed": True})
            return result
        except Exception as exc:
            oom = type(exc).__name__ == "OutOfMemoryError"
            category = ("memory_resource_rejection" if oom else "input_rejected" if stage == "input_validation"
                        else "prompt_rejected" if stage == "prompt_preparation" and isinstance(exc, ValueError)
                        else "processor_incompatibility" if stage == "prompt_preparation"
                        else "generation_runtime_error")
            result.update(failure_category=category, error=f"{type(exc).__name__}: {exc}", failed_stage=stage)
            return result


def overall_status(cases: list[dict]) -> str:
    statuses = {c["execution_status"] for c in cases}
    if statuses == {"completed"}:
        return "completed"
    if statuses <= {"completed", "generated_but_invalid"}:
        return "generated_but_invalid"
    return "failed"


def new_record(max_new_tokens: int, evidence_kind: str) -> dict:
    policy = cuda_policy.configuration()
    return {
        "schema_version": cuda_policy.RUN_RECORD_SCHEMA, "project": "Waymaker Artemis",
        "runtime": cuda_policy.RUNTIME, "inference_kind": "real_inference", "evidence_kind": evidence_kind,
        "model": {"checkpoint": policy["model"]["checkpoint"], "revision": policy["model"]["revision"],
                  "quantization": QUANTIZATION_LABEL, "quantization_policy": policy["quantization"]},
        "official_gold_accuracy": None, "legal_accuracy_claimed": False,
        "max_new_tokens": max_new_tokens, "execution_status": "not_executed", "not_executed_reason": None,
        "environment": {}, "provenance": {}, "load": {}, "cases": []}


class PreparedRun:
    """Preflight + load once; later batches reuse the loaded session."""

    def __init__(self, cache_dir: Path | None = None, verify_weights: bool = True):
        self.cache_dir, self.verify_weights = cache_dir, verify_weights
        self.session: CudaSession | None = None
        self.header: dict = {}
        self.blocker: dict | None = None

    def prepare(self) -> bool:
        check = preflight(self.cache_dir, self.verify_weights)
        self.header = {
            "environment": {**check["probe"], "cuda_device": (check["probe"]["cuda_device"] or {}).get("name")},
            "provenance": {"snapshot_revision": Path(check["snapshot"]).name if check["snapshot"] else None,
                           **check["verified"]}}
        if check["blockers"]:
            self.blocker = {"execution_status": "not_executed", "not_executed_reason": "; ".join(check["blockers"])}
            return False
        session = CudaSession(check["snapshot"])
        try:
            self.header["load"] = session.load()
        except Exception as exc:
            category = "memory_resource_rejection" if type(exc).__name__ == "OutOfMemoryError" else "model_loading_error"
            self.blocker = {"execution_status": "failed", "failure_category": category,
                            "error": f"{type(exc).__name__}: {exc}"}
            return False
        if not self.header["load"]["quantization"]["passed"]:
            self.blocker = {"execution_status": "failed", "failure_category": "quantization_not_verified",
                            "error": "Loaded model is not NF4 4-bit on cuda:0 as required"}
            return False
        self.session = session
        return True

    def metadata(self) -> dict:
        """Adapter metadata for foundation.metric_group (separate from MLX)."""
        provenance = self.header.get("provenance", {})
        return {"inference_kind": "real_inference", "runtime": cuda_policy.RUNTIME,
                "profile": cuda_policy.configuration()["foundation_profile"],
                "model_name": cuda_policy.configuration()["model"]["checkpoint"],
                "model_revision": provenance.get("snapshot_revision"),
                "quantization": QUANTIZATION_LABEL,
                "quantization_verified": bool(self.session) and self.header["load"]["quantization"]["passed"],
                "cuda_device": self.header.get("environment", {}).get("cuda_device"),
                "checkpoint_metadata_verified": provenance.get("checkpoint_metadata_verified", False),
                "checkpoint_integrity_verified": provenance.get("checkpoint_integrity_verified", False),
                "weight_integrity": provenance.get("weight_integrity")}

    def run(self, cases: list[tuple[str, dict]], max_new_tokens: int, evidence_kind: str) -> dict:
        """Return a cuda_policy run record. Model errors become statuses, not exceptions."""
        record = new_record(max_new_tokens, evidence_kind)
        if self.session is None and self.blocker is None:
            self.prepare()
        record.update(self.header)
        if self.session is None:
            record.update(self.blocker)
            return record
        record["cases"] = [self.session.generate(case_id, item, max_new_tokens) for case_id, item in cases]
        record["execution_status"] = overall_status(record["cases"])
        return record


def main() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result = probe() if "--probe" in sys.argv else preflight()
        except Exception as exc:
            result = {"error": f"{type(exc).__name__}: {exc}"}
    result["warnings"] = [str(w.message) for w in caught]
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
