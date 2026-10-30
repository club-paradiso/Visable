"""Waymaker Artemis model identity, offline checkpoint and provenance policy.

No ML packages or network access. Inference and training share this policy;
experiment configs retain their hypothesis-specific settings, not defaults.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "artemis_foundation.json"


def configuration() -> dict:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if (data["project"]["name"] != "Waymaker Artemis"
            or data["default_profile"] != "gemma4_e4b"
            or data["allow_implicit_fallback"] is not False):
        raise ValueError("Invalid Waymaker Artemis foundation policy")
    if data["evaluation"] != {
        "separate_model_variants": True, "require_model_provenance": True,
        "official_gold_without_human_review": False,
    }:
        raise ValueError("Evaluation provenance policy cannot be relaxed")
    return data


def profile(name: str = "gemma4_e4b") -> dict:
    profiles = configuration()["profiles"]
    if name not in profiles:
        raise ValueError(f"Unsupported model profile: {name}")
    value = profiles[name]
    size = {"gemma4_e4b": "E4B", "gemma4_e2b": "E2B"}.get(name)
    if (value["family"] != "gemma-4" or value["architecture"] != size
            or value["variant"] != "instruct"
            or value["upstream"] != f"google/gemma-4-{size}-it"
            or value["inference_checkpoint"] != f"mlx-community/gemma-4-{size.lower()}-it-4bit"):
        raise ValueError("Unsupported foundation family or architecture")
    for field in ("upstream_revision", "inference_revision", "conversion_source_revision"):
        if not re.fullmatch(r"[0-9a-f]{40}", value[field]):
            raise ValueError(f"{field} must be an immutable commit SHA")
    return value


def select_profile(name: str, model: str | None, revision: str | None, runtime: str) -> dict:
    selected = profile(name)
    if runtime != configuration()["runtime"]["name"]:
        raise ValueError(f"Unsupported runtime: {runtime}; expected mlx_vlm")
    if model is not None and model != selected["inference_checkpoint"]:
        raise ValueError("Checkpoint does not match explicitly selected Gemma 4 profile")
    if revision is not None and revision != selected["inference_revision"]:
        raise ValueError("Revision is not the audited profile revision; update the foundation configuration first")
    return selected


def find_snapshot(selected: Mapping[str, Any], cache_dir: Path | None = None) -> Path | None:
    """Resolve only the pinned snapshot. Never choose another revision or model."""
    roots = [Path(cache_dir)] if cache_dir is not None else [
        Path.home() / ".cache" / "waymaker-artemis" / "hf",
        Path.home() / ".cache" / "huggingface" / "hub",
    ]
    if cache_dir is None:
        for key in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "HF_HOME"):
            if os.environ.get(key):
                roots.insert(0, Path(os.environ[key]))
    folder = "models--" + selected["inference_checkpoint"].replace("/", "--")
    for root in roots:
        for base in (root, root / "hub"):
            snapshot = base / folder / "snapshots" / selected["inference_revision"]
            if snapshot.is_dir():
                return snapshot
    return None


def validate_architecture(config: Mapping, processor: Mapping, selected: Mapping) -> None:
    if config.get("model_type") != "gemma4" or config.get("architectures") != selected["architectures"]:
        raise ValueError("Incompatible model family/architecture")
    for key, expected in selected["text_config"].items():
        if config.get("text_config", {}).get(key) != expected:
            raise ValueError(f"Incompatible {selected['architecture']} text_config.{key}")
    if config.get("quantization") != selected["quantization"]:
        raise ValueError("Incompatible quantization")
    if processor.get("processor_class") != selected["processor_class"]:
        raise ValueError("Incompatible Gemma 4 processor")


def _file_identity(path: Path) -> tuple:
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


@lru_cache(maxsize=128)
def _stream_digest(resolved_path: str, algorithm: str, identity: tuple) -> str:
    """Cache only unchanged file identities; stream large weights in 1 MiB chunks.

    This avoids rereading 5 GB for each metadata/report call in one process.
    A new process checks again. Size, inode, mtime and ctime changes invalidate
    the cache; this does not protect against a hostile filesystem/kernel.
    """
    path = Path(resolved_path)
    if _file_identity(path) != identity:
        raise ValueError("Checkpoint artifact changed before integrity check")
    digest = hashlib.sha256() if algorithm == "sha256" else hashlib.sha1(usedforsecurity=False)
    if algorithm == "git_blob_sha1":
        digest.update(f"blob {identity[2]}\0".encode())
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    if _file_identity(path) != identity:
        raise ValueError("Checkpoint artifact changed during integrity check")
    return digest.hexdigest()


def verify_artifact(path: Path, reference: Mapping) -> dict:
    algorithm, expected = reference.get("algorithm"), reference.get("digest", "")
    width = {"sha256": 64, "git_blob_sha1": 40}.get(algorithm)
    if not width or not isinstance(expected, str) or not re.fullmatch(f"[0-9a-f]{{{width}}}", expected):
        raise ValueError(f"Missing or unsupported integrity reference: {path.name}")
    identity = _file_identity(path)
    if type(reference.get("size_bytes")) is not int or identity[2] != reference["size_bytes"]:
        raise ValueError(f"Checkpoint artifact size mismatch: {path.name}")
    actual = _stream_digest(str(path.resolve()), algorithm, identity)
    if actual != expected:
        raise ValueError(f"Checkpoint artifact integrity digest mismatch: {path.name}")
    return {"algorithm": algorithm, "digest": actual, "size_bytes": identity[2]}


def validate_snapshot(snapshot: Path, selected: Mapping) -> dict:
    if snapshot.name != selected["inference_revision"]:
        raise ValueError("Snapshot revision mismatch")
    config = json.loads((snapshot / "config.json").read_text())
    processor = json.loads((snapshot / "processor_config.json").read_text())
    validate_architecture(config, processor, selected)
    digests = {}
    for name, expected in selected["metadata_sha256"].items():
        digest = hashlib.sha256((snapshot / name).read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"Pinned checkpoint metadata mismatch: {name}")
        digests[name] = digest
    integrity = selected.get("artifact_integrity", {})
    references = integrity.get("files", {})
    if (not integrity.get("reference_source") or not isinstance(references, dict)
            or not {"tokenizer.json", "model.safetensors.index.json"} <= references.keys()
            or any(Path(name).name != name or name in {".", ".."} for name in references)):
        raise ValueError("Trusted checkpoint integrity references are required")
    artifacts = {name: verify_artifact(snapshot / name, references[name])
                 for name in ("tokenizer.json", "model.safetensors.index.json")}
    index = json.loads((snapshot / "model.safetensors.index.json").read_text())
    shards = sorted(set(index.get("weight_map", {}).values()))
    if not shards or any(Path(s).name != s for s in shards):
        raise ValueError("Invalid weight index")
    trusted_shards = {name for name in references if name.endswith(".safetensors")}
    if (set(shards) != trusted_shards
            or set(references) != trusted_shards | {"tokenizer.json", "model.safetensors.index.json"}
            or any(references[name]["algorithm"] != "sha256" for name in trusted_shards)):
        raise ValueError("Weight index shards do not match trusted SHA-256 integrity references")
    artifacts.update({name: verify_artifact(snapshot / name, references[name]) for name in shards})
    sizes = {s: (snapshot / s).stat().st_size for s in shards}
    if any(size <= 0 for size in sizes.values()):
        raise ValueError("Empty weights")
    return {"checkpoint_metadata_verified": True, "metadata_sha256": digests,
            "checkpoint_integrity_verified": True, "artifact_integrity": artifacts,
            "integrity_reference_source": integrity["reference_source"],
            "weight_files_bytes": sizes, "weight_integrity": "sha256_verified"}


def metric_group(metadata: Mapping) -> str:
    """An aggregation key, never a legal-accuracy certification."""
    kind = metadata.get("inference_kind")
    if kind not in {"real_inference", "mock", "recorded_fixture", "synthetic_regression"}:
        raise ValueError("Missing or unsupported inference provenance")
    fields = (kind, metadata.get("profile"), metadata.get("model_name"),
              metadata.get("model_revision"), metadata.get("runtime"))
    if kind == "real_inference":
        selected = profile(metadata.get("profile", ""))
        if (metadata.get("model_name") != selected["inference_checkpoint"]
                or metadata.get("model_revision") != selected["inference_revision"]
                or metadata.get("runtime") != "mlx_vlm"
                or not metadata.get("checkpoint_metadata_verified")
                or metadata.get("checkpoint_integrity_verified") is not True
                or metadata.get("weight_integrity") != "sha256_verified"):
            raise ValueError("Unverified or cross-model inference provenance")
    return hashlib.sha256(json.dumps(fields).encode()).hexdigest()


def require_same_metric_group(reports: list[Mapping]) -> str:
    if not reports:
        raise ValueError("No reports to aggregate")
    groups = {metric_group(r["model_metadata"]) for r in reports}
    benchmarks = {(r["benchmark_metadata"].get("benchmark_sha256"), r["mode"])
                  for r in reports}
    if len(groups) != 1 or len(benchmarks) != 1:
        raise ValueError("Cross-model, cross-source or cross-benchmark metrics cannot be pooled")
    return groups.pop()
