"""Artemis Evaluation Isolation & Blind Benchmark Protocol Subsystem (Mission 004-D).

Addresses benchmark contamination, data leakage, and separation of model inputs
from grading labels.

CRITICAL GOVERNANCE RULES:
1. Held-out Contamination Honesty: The existing 40 held-out items have had their ground
   truth answers accessible in this repository. They must NOT be described as a genuinely
   unseen independent blind benchmark.
2. If the runtime cannot provide a genuinely isolated clean-room environment, it must
   report 'isolation_not_verified' rather than claiming clean-room compliance.
3. Blind Input Projection: The model inference adapter must receive ONLY the user question,
   context, and metadata. Expected answers, required facts, and forbidden claims must be
   strictly stripped out during inference.
4. Partition Integrity: Guarantees zero ID overlap between dev and held-out candidate splits.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime as dt
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

BOOTSTRAP_DIR = Path(__file__).resolve().parent
EXPERIMENT_ROOT = BOOTSTRAP_DIR.parent
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"
ISOLATION_MANIFEST_PATH = BENCHMARKS_DIR / "BENCHMARK_ISOLATION_MANIFEST.json"


class DataLeakageContaminationWarning(UserWarning):
    """Raised or logged when potential target label contamination is detected in model inputs."""
    pass


class EvaluationIsolationError(ValueError):
    """Raised when benchmark partition or integrity verification fails."""
    pass


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_text_sha256(text: str) -> str:
    norm = unicodedata.normalize("NFC", text or "").strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def project_blind_item(item: Dict[str, Any], include_evidence_for_rag: bool = True) -> Dict[str, Any]:
    """Projects a benchmark item into a strictly blind inference input.
    
    Strips ALL:
    - 'expected' dictionary (allowed_statuses, required_facts, forbidden_claims, rubrics)
    - Ground-truth evaluation directives
    - Legal review decision notes or gold labels
    """
    blind = {
        "id": item["id"],
        "title": item.get("title", ""),
        "dimension": item.get("dimension", ""),
        "question": item.get("question", ""),
        "user_context": copy.deepcopy(item.get("user_context", {})),
        "metadata": {
            "split": item.get("metadata", {}).get("split", "unknown"),
            "domain": item.get("metadata", {}).get("domain", "immigration"),
            "blind_projected": True,
            "blind_timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
    }

    if include_evidence_for_rag and "evidence" in item:
        # Provide evidence text and citation ID, but strip approval state or review status
        blind_evidence = []
        for ev in item.get("evidence", []):
            blind_evidence.append({
                "id": ev.get("id"),
                "title": ev.get("title"),
                "text": ev.get("text"),
                "source": {
                    "document_id": ev.get("source", {}).get("document_id"),
                    "provision": ev.get("source", {}).get("provision"),
                    "effective_date": ev.get("source", {}).get("effective_date"),
                    "source_url": ev.get("source", {}).get("source_url"),
                }
            })
        blind["evidence"] = blind_evidence

    return blind


def detect_prompt_leakage(
    prompt_or_input: str | Dict[str, Any],
    ground_truth_item: Dict[str, Any],
) -> List[str]:
    """Detects if expected answers or forbidden claims were leaked into the model input."""
    leakages = []
    text_to_search = (
        json.dumps(prompt_or_input, ensure_ascii=False)
        if isinstance(prompt_or_input, dict)
        else str(prompt_or_input)
    )

    exp = ground_truth_item.get("expected", {})

    # Check required facts leakage
    req_facts = exp.get("source_fidelity", {}).get("required_facts", [])
    for fact in req_facts:
        if len(fact) > 6 and fact in text_to_search:
            # Check if this fact was already part of the question
            q = ground_truth_item.get("question", "")
            if fact not in q:
                leakages.append(f"Required fact '{fact}' appeared in model prompt outside question")

    # Check forbidden claims leakage
    forb = exp.get("source_fidelity", {}).get("forbidden_claims", [])
    for claim in forb:
        if len(claim) > 6 and claim in text_to_search:
            q = ground_truth_item.get("question", "")
            if claim not in q:
                leakages.append(f"Forbidden claim label '{claim}' found in prompt input")

    return leakages


def verify_benchmark_partitions(
    dev_path: Optional[Path] = None,
    heldout_path: Optional[Path] = None,
    candidates_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Verifies that development and held-out candidate partitions have zero overlap."""
    d_path = dev_path or (BENCHMARKS_DIR / "artemis_eval_dev_20.json")
    h_path = heldout_path or (BENCHMARKS_DIR / "artemis_eval_heldout_40.json")
    c_path = candidates_path or (BENCHMARKS_DIR / "artemis_eval_candidates_60.json")

    if not d_path.exists() or not h_path.exists():
        raise FileNotFoundError(f"Partition files not found: {d_path} or {h_path}")

    dev_data = json.loads(d_path.read_text(encoding="utf-8"))
    heldout_data = json.loads(h_path.read_text(encoding="utf-8"))

    dev_items = dev_data.get("items", [])
    heldout_items = heldout_data.get("items", [])

    dev_ids = {it["id"] for it in dev_items}
    heldout_ids = {it["id"] for it in heldout_items}

    # Check 1: Counts
    if len(dev_items) != 20:
        raise EvaluationIsolationError(f"Expected 20 dev items, got {len(dev_items)}")
    if len(heldout_items) != 40:
        raise EvaluationIsolationError(f"Expected 40 heldout items, got {len(heldout_items)}")

    # Check 2: Zero Overlap
    overlap = dev_ids.intersection(heldout_ids)
    if overlap:
        raise EvaluationIsolationError(f"Data contamination: {len(overlap)} overlapping item IDs: {overlap}")

    # Check 3: Candidate file consistency if present
    if c_path.exists():
        cand_data = json.loads(c_path.read_text(encoding="utf-8"))
        cand_items = cand_data.get("items", [])
        cand_ids = {it["id"] for it in cand_items}
        if len(cand_items) != 60:
            raise EvaluationIsolationError(f"Expected 60 candidate items, got {len(cand_items)}")
        if cand_ids != (dev_ids | heldout_ids):
            raise EvaluationIsolationError("Candidate items set does not match dev + heldout union")

    return {
        "status": "valid",
        "dev_items_count": len(dev_items),
        "heldout_items_count": len(heldout_items),
        "total_items_count": len(dev_items) + len(heldout_items),
        "overlap_count": 0,
        "dev_sha256": compute_file_sha256(d_path),
        "heldout_sha256": compute_file_sha256(h_path),
    }


def get_environment_isolation_audit() -> Dict[str, Any]:
    """Assesses whether the execution environment provides true blind isolation."""
    # Check if we are running in an unisolated local dev workspace
    return {
        "isolation_status": "isolation_not_verified",
        "clean_room_verified": False,
        "environment_type": "local_development_workspace",
        "heldout_blind_integrity": "compromised_by_repo_visibility",
        "warning": (
            "The 40 held-out candidate items are stored in git alongside evaluation code. "
            "Model developers and agents have full read access to expected answers. "
            "Therefore, this benchmark MUST NOT be described as a clean-room blind evaluation."
        ),
        "mitigation_implemented": (
            "Blind Input Projection (project_blind_item) strips expected answers and grading "
            "criteria prior to passing inputs to model adapters."
        ),
        "future_protocol_required": (
            "True blind evaluation requires encrypting held-out items into an external enclave "
            "or clean-room container accessible only by an independent third-party auditor."
        ),
    }


def generate_blind_benchmarks(
    output_dir: Path = BENCHMARKS_DIR,
) -> Dict[str, Any]:
    """Extracts and saves blind benchmark views with expected answers stripped."""
    partition_res = verify_benchmark_partitions()

    dev_data = json.loads((BENCHMARKS_DIR / "artemis_eval_dev_20.json").read_text(encoding="utf-8"))
    heldout_data = json.loads((BENCHMARKS_DIR / "artemis_eval_heldout_40.json").read_text(encoding="utf-8"))

    blind_dev = {
        "version": "artemis-blind-dev/1.0",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_items": len(dev_data["items"]),
        "split": "dev_blind",
        "isolation_note": "Expected answers and rubrics stripped for unassisted inference.",
        "items": [project_blind_item(it) for it in dev_data["items"]],
    }
    blind_heldout = {
        "version": "artemis-blind-heldout/1.0",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_items": len(heldout_data["items"]),
        "split": "heldout_blind",
        "isolation_status": "isolation_not_verified",
        "isolation_warning": "Candidate heldout set; answers were accessible in git repository.",
        "items": [project_blind_item(it) for it in heldout_data["items"]],
    }

    dev_out = output_dir / "artemis_eval_dev_blind_20.json"
    hld_out = output_dir / "artemis_eval_heldout_blind_40.json"

    dev_out.write_text(json.dumps(blind_dev, indent=2, ensure_ascii=False), encoding="utf-8")
    hld_out.write_text(json.dumps(blind_heldout, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write isolation manifest
    manifest = {
        "manifest_version": "artemis-isolation-manifest/1.0",
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "environment_audit": get_environment_isolation_audit(),
        "partitions": partition_res,
        "files": {
            "artemis_eval_dev_20.json": compute_file_sha256(BENCHMARKS_DIR / "artemis_eval_dev_20.json"),
            "artemis_eval_heldout_40.json": compute_file_sha256(BENCHMARKS_DIR / "artemis_eval_heldout_40.json"),
            "artemis_eval_candidates_60.json": compute_file_sha256(BENCHMARKS_DIR / "artemis_eval_candidates_60.json"),
            "artemis_eval_dev_blind_20.json": compute_file_sha256(dev_out),
            "artemis_eval_heldout_blind_40.json": compute_file_sha256(hld_out),
        }
    }
    manifest_path = output_dir / ISOLATION_MANIFEST_PATH.name
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "dev_blind_file": str(dev_out),
        "heldout_blind_file": str(hld_out),
        "manifest_file": str(manifest_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Artemis Evaluation Isolation & Blind Benchmark CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # verify
    subparsers.add_parser("verify", help="Verify benchmark partitions and partition zero-overlap")

    # blind
    subparsers.add_parser("generate-blind", help="Generate blind benchmark files with stripped answers")

    # audit
    subparsers.add_parser("audit", help="Audit clean-room isolation status and leakage risks")

    args = parser.parse_args()

    if args.subcommand == "verify":
        res = verify_benchmark_partitions()
        print(f"[SUCCESS] Partition verification passed. 0 overlap. Dev: {res['dev_items_count']}, Heldout: {res['heldout_items_count']}")

    elif args.subcommand == "generate-blind":
        res = generate_blind_benchmarks()
        print(f"[SUCCESS] Blind benchmarks generated:\n - Dev: {res['dev_blind_file']}\n - Heldout: {res['heldout_blind_file']}\n - Manifest: {res['manifest_file']}")

    elif args.subcommand == "audit":
        audit = get_environment_isolation_audit()
        print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
