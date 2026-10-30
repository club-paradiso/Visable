"""Waymaker Artemis CUDA (Transformers + bitsandbytes NF4) model identity policy.

A separate path from the MLX-VLM foundation: the CUDA runtime loads the official
upstream checkpoint and quantizes at load time, while MLX loads a pre-converted
community checkpoint. Different weights, chat templates and kernels mean the two
never share a metric group. No ML packages or network access here.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

from waymaker_ai import foundation

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "artemis_cuda_runtime.json"
RUNTIME = "transformers_cuda"
RUN_RECORD_SCHEMA = "waymaker-artemis-cuda-run/1.0"
EXECUTION_STATUSES = ("completed", "generated_but_invalid", "failed", "not_executed")
REQUIRED_QUANTIZATION = {
    "method": "bitsandbytes", "load_in_4bit": True, "bnb_4bit_quant_type": "nf4",
    "bnb_4bit_use_double_quant": True, "bnb_4bit_compute_dtype": "float16",
    "non_quantized_dtype": "float16",
}


def configuration() -> dict:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    model = data["model"]
    upstream = foundation.profile(data["foundation_profile"])
    if (data["project"] != "Waymaker Artemis" or data["runtime"] != RUNTIME
            or data["allow_implicit_fallback"] is not False
            or model["checkpoint"] != upstream["upstream"]
            or model["revision"] != upstream["upstream_revision"]
            or not re.fullmatch(r"[0-9a-f]{40}", model["revision"])):
        raise ValueError("CUDA runtime must load the pinned official upstream checkpoint")
    if data["quantization"] != REQUIRED_QUANTIZATION:
        raise ValueError("CUDA quantization policy must be explicit NF4 4-bit with FP16 compute")
    if set(model["artifacts"]) != {"model.safetensors", "tokenizer.json"}:
        raise ValueError("CUDA integrity references must cover the weights and tokenizer")
    return data


def find_snapshot(cache_dir: Path | None = None) -> Path | None:
    """Resolve only the pinned upstream snapshot. Never another revision or model."""
    model = configuration()["model"]
    roots = [Path(cache_dir)] if cache_dir is not None else [Path.home() / ".cache" / "huggingface" / "hub"]
    if cache_dir is None:
        for key in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "HF_HOME"):
            if os.environ.get(key):
                roots.insert(0, Path(os.environ[key]))
    folder = "models--" + model["checkpoint"].replace("/", "--")
    for root in roots:
        for base in (root, root / "hub"):
            snapshot = base / folder / "snapshots" / model["revision"]
            if snapshot.is_dir():
                return snapshot
    return None


def validate_snapshot(snapshot: Path, verify_weights: bool = True) -> dict:
    """Check revision, architecture and pinned digests.

    verify_weights=False hashes only the tokenizer and records the weights as
    size_only; such runs are kept but cannot enter a real_inference metric group.
    """
    model = configuration()["model"]
    if snapshot.name != model["revision"]:
        raise ValueError("Snapshot revision mismatch")
    config = json.loads((snapshot / "config.json").read_text())
    processor = json.loads((snapshot / "processor_config.json").read_text())
    if config.get("model_type") != model["model_type"] or config.get("architectures") != model["architectures"]:
        raise ValueError("Incompatible model family/architecture")
    for key, expected in model["text_config"].items():
        if config.get("text_config", {}).get(key) != expected:
            raise ValueError(f"Incompatible E4B text_config.{key}")
    if "quantization_config" in config or "quantization" in config:
        raise ValueError("Expected the unquantized upstream checkpoint")
    if processor.get("processor_class") != model["processor_class"]:
        raise ValueError("Incompatible Gemma 4 processor")
    digests = {}
    for name, expected in model["metadata_sha256"].items():
        digest = hashlib.sha256((snapshot / name).read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"Pinned checkpoint metadata mismatch: {name}")
        digests[name] = digest
    artifacts = {"tokenizer.json": foundation.verify_artifact(snapshot / "tokenizer.json",
                                                              model["artifacts"]["tokenizer.json"])}
    weights = model["artifacts"]["model.safetensors"]
    if verify_weights:
        artifacts["model.safetensors"] = foundation.verify_artifact(snapshot / "model.safetensors", weights)
        weight_integrity = "sha256_verified"
    else:
        size = (snapshot / "model.safetensors").stat().st_size
        if size != weights["size_bytes"]:
            raise ValueError("Checkpoint artifact size mismatch: model.safetensors")
        artifacts["model.safetensors"] = {"algorithm": "size_only", "size_bytes": size}
        weight_integrity = "size_only"
    return {"checkpoint_metadata_verified": True, "metadata_sha256": digests,
            "checkpoint_integrity_verified": verify_weights, "artifact_integrity": artifacts,
            "integrity_reference_source": model["reference_source"], "weight_integrity": weight_integrity}


def validate_real_inference_metadata(metadata: Mapping[str, Any]) -> None:
    """Called by foundation.metric_group for runtime == transformers_cuda."""
    data = configuration()
    if (metadata.get("profile") != data["foundation_profile"]
            or metadata.get("model_name") != data["model"]["checkpoint"]
            or metadata.get("model_revision") != data["model"]["revision"]
            or metadata.get("quantization") != "bnb_nf4_double_quant_fp16"
            or not metadata.get("checkpoint_metadata_verified")
            or metadata.get("checkpoint_integrity_verified") is not True
            or metadata.get("weight_integrity") != "sha256_verified"
            or metadata.get("quantization_verified") is not True
            or not isinstance(metadata.get("cuda_device"), str) or not metadata["cuda_device"].strip()):
        raise ValueError("Unverified or cross-model CUDA inference provenance")


def validate_run_record(record: Mapping[str, Any]) -> None:
    """Structural check of a run record; says nothing about legal accuracy."""
    if record.get("schema_version") != RUN_RECORD_SCHEMA or record.get("runtime") != RUNTIME:
        raise ValueError("Not a Waymaker Artemis CUDA run record")
    if record.get("execution_status") not in EXECUTION_STATUSES:
        raise ValueError("Unknown execution status")
    if record.get("official_gold_accuracy") is not None:
        raise ValueError("A CUDA smoke record cannot carry official gold accuracy")
    if record.get("evidence_kind") not in {"none", "synthetic", "candidate_unreviewed"}:
        raise ValueError("Evidence kind must be declared")
    cases = record.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Cases must be a list")
    if record["execution_status"] == "not_executed":
        if not record.get("not_executed_reason") or any(c.get("generated_token_count") for c in cases):
            raise ValueError("A not_executed record needs a reason and cannot contain generated tokens")
        return
    environment = record.get("environment", {})
    if not environment.get("cuda_device") or not environment.get("packages"):
        raise ValueError("An executed record must name its CUDA device and package versions")
    for case in cases:
        status = case.get("execution_status")
        if status not in EXECUTION_STATUSES:
            raise ValueError(f"Unknown case status: {case.get('case_id')}")
        if status in {"completed", "generated_but_invalid"}:
            if not isinstance(case.get("generated_token_count"), int) or case["generated_token_count"] <= 0:
                raise ValueError(f"Generated case without tokens: {case.get('case_id')}")
            if not isinstance(case.get("raw_output"), str):
                raise ValueError(f"Generated case without raw output: {case.get('case_id')}")
        if (status == "completed") != bool(case.get("output_validation", {}).get("passed")):
            raise ValueError(f"Completed must mean schema-valid output: {case.get('case_id')}")
