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
from waymaker_ai.response_contract import parse_response

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "artemis_cuda_runtime.json"
RUNTIME = "transformers_cuda"
RUN_RECORD_SCHEMA = "waymaker-artemis-cuda-run/1.0"
EXECUTION_STATUSES = ("completed", "generated_but_invalid", "failed", "not_executed")
QUANTIZATION_LABEL = "bnb_nf4_double_quant_fp16"
# Source files whose digests a run record carries (paths relative to experiments/waymaker-ai).
CODE_FILES = ("artemis_bootstrap/gemma4_cuda_runtime.py", "artemis_bootstrap/probe_gemma4_cuda.py",
              "waymaker_ai/cuda_policy.py", "waymaker_ai/response_contract.py",
              "waymaker_ai/inference_input.py", "configs/artemis_cuda_runtime.json")
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
    if (metadata.get("adapter_type") != "cuda_transformers"
            or metadata.get("profile") != data["foundation_profile"]
            or metadata.get("model_name") != data["model"]["checkpoint"]
            or metadata.get("model_revision") != data["model"]["revision"]
            or metadata.get("quantization") != QUANTIZATION_LABEL
            or metadata.get("weights_sha256") != data["model"]["artifacts"]["model.safetensors"]["digest"]
            or metadata.get("checkpoint_metadata_verified") is not True
            or metadata.get("checkpoint_integrity_verified") is not True
            or metadata.get("weight_integrity") != "sha256_verified"
            or metadata.get("quantization_verified") is not True
            or not _text(metadata.get("cuda_device"))):
        raise ValueError("Unverified or cross-model CUDA inference provenance")


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def overall_status(cases: list[Mapping[str, Any]]) -> str:
    statuses = {c.get("execution_status") for c in cases}
    if statuses == {"completed"}:
        return "completed"
    if statuses <= {"completed", "generated_but_invalid"}:
        return "generated_but_invalid"
    return "failed"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_model_provenance(record: Mapping[str, Any], data: Mapping[str, Any]) -> None:
    """Everything a generated output needs before it counts as this model's output."""
    model, pinned = record.get("model") or {}, data["model"]
    _require(record.get("inference_kind") == "real_inference", "Only real inference can be a CUDA run record")
    _require(model.get("checkpoint") == pinned["checkpoint"] and model.get("revision") == pinned["revision"],
             "Run record names a different model or revision")
    _require(model.get("quantization") == QUANTIZATION_LABEL and model.get("quantization_policy") == data["quantization"],
             "Run record quantization differs from the NF4 policy")
    provenance = record.get("provenance") or {}
    _require(provenance.get("snapshot_revision") == pinned["revision"], "Snapshot revision mismatch")
    _require(provenance.get("checkpoint_metadata_verified") is True
             and provenance.get("metadata_sha256") == pinned["metadata_sha256"], "Checkpoint metadata not verified")
    _require(provenance.get("checkpoint_integrity_verified") is True
             and provenance.get("weight_integrity") == "sha256_verified", "Weights not SHA-256 verified")
    _require(provenance.get("integrity_reference_source") == pinned["reference_source"],
             "Integrity reference is not the pinned Hub reference")
    artifacts = provenance.get("artifact_integrity") or {}
    for name, reference in pinned["artifacts"].items():
        found = artifacts.get(name) or {}
        _require(found.get("algorithm") == "sha256" and found.get("digest") == reference["digest"]
                 and found.get("size_bytes") == reference["size_bytes"], f"Artifact not verified: {name}")
    quantization = (record.get("load") or {}).get("quantization") or {}
    _require(quantization.get("passed") is True and quantization.get("quant_types") == ["nf4"]
             and quantization.get("double_quant") == [True] and quantization.get("compute_dtypes") == ["float16"]
             and quantization.get("parameter_devices") == ["cuda:0"]
             and quantization.get("quantized_decoder_layers") == pinned["text_config"]["num_hidden_layers"],
             "Loaded-module NF4 verification missing or failed")
    load_seconds = (record.get("load") or {}).get("load_seconds")
    _require(isinstance(load_seconds, (int, float)) and not isinstance(load_seconds, bool) and load_seconds > 0,
             "Model load was not recorded")
    files = (record.get("code") or {}).get("files_sha256") or {}
    _require(set(files) == set(CODE_FILES) and all(_text(v) for v in files.values()),
             "Code provenance (source file digests) missing")


def _validate_case(case: Mapping[str, Any]) -> None:
    name, status = case.get("case_id"), case.get("execution_status")
    _require(status in EXECUTION_STATUSES, f"Unknown case status: {name}")
    passed = (case.get("output_validation") or {}).get("passed")
    if status not in {"completed", "generated_but_invalid"}:
        _require(passed is not True, f"Only completed output can pass validation: {name}")
        return
    tokens = case.get("generated_token_count")
    _require(type(tokens) is int and tokens > 0, f"Generated case without tokens: {name}")
    _require(isinstance(case.get("raw_output"), str), f"Generated case without raw output: {name}")
    ids = case.get("evidence_ids")
    _require(isinstance(ids, list) and all(isinstance(i, str) for i in ids), f"Evidence IDs not recorded: {name}")
    try:
        # Judge each case by the contract it was generated under; records before 005-E are v1.
        parsed = parse_response(case["raw_output"], set(ids), case.get("contract_version", "v1"))
    except (ValueError, TypeError):
        parsed = None
    # Re-judge the raw text: a stored flag alone cannot make output valid.
    if status == "completed":
        _require(parsed is not None and passed is True and case.get("response") == parsed,
                 f"Completed must mean the raw output passes the contract: {name}")
    else:
        _require(parsed is None and passed is not True,
                 f"generated_but_invalid output actually passes the contract: {name}")


def validate_run_record(record: Mapping[str, Any]) -> None:
    """Structural and consistency check of a run record written by our own code.

    Not an external attestation: it cannot detect a consistent forgery of every
    field. It rejects mislabeled models, partial provenance and overclaims.
    """
    data = configuration()
    _require(record.get("schema_version") == RUN_RECORD_SCHEMA and record.get("runtime") == RUNTIME
             and record.get("project") == "Waymaker Artemis", "Not a Waymaker Artemis CUDA run record")
    _require(record.get("inference_kind") == "real_inference", "A CUDA run record must be real inference")
    status = record.get("execution_status")
    _require(status in EXECUTION_STATUSES, "Unknown execution status")
    _require(record.get("official_gold_accuracy") is None and record.get("legal_accuracy_claimed") is False,
             "A CUDA smoke record cannot claim gold or legal accuracy")
    _require(record.get("evidence_kind") in {"none", "synthetic", "candidate_unreviewed"},
             "Evidence kind must be declared")
    cases = record.get("cases")
    _require(isinstance(cases, list), "Cases must be a list")
    if status == "not_executed":
        _require(_text(record.get("not_executed_reason")) and not cases,
                 "A not_executed record needs a reason and cannot contain cases")
        return
    environment = record.get("environment") or {}
    _require(_text(environment.get("cuda_device")) and isinstance(environment.get("packages"), dict)
             and bool(environment["packages"]), "An executed record must name its CUDA device and package versions")
    drift = environment.get("version_drift") or []
    _require(record.get("reproduction_pins_matched", not drift) == (not drift),
             "Version drift contradicts reproduction_pins_matched")
    if not cases:
        _require(status == "failed" and _text(record.get("failure_category")) and _text(record.get("error")),
                 "A record without cases must be a failure with a category and error")
        return
    _require(status == overall_status(cases), "Record status does not match the overall case statuses")
    for case in cases:
        _validate_case(case)
    if any(c.get("execution_status") in {"completed", "generated_but_invalid"} for c in cases):
        _validate_model_provenance(record, data)
