"""Split one CUDA run record into review-friendly evidence views. Never edits the record.

Each view carries the source record's SHA-256 so it can be traced back to the
unmodified file, which is stored next to the views as raw_record.json.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from waymaker_ai import cuda_policy


def views(record: dict, digest: str) -> dict:
    source = {"source_record": "raw_record.json", "source_record_sha256": digest}
    try:
        cuda_policy.validate_run_record(record)
        check = {"passed": True, "error": None}
    except ValueError as exc:
        check = {"passed": False, "error": str(exc)}
    load = record.get("load") or {}
    cases = record.get("cases") or []
    return {
        "execution_manifest.json": {**source, "schema_version": record.get("schema_version"),
                                    "kind": record.get("kind"), "started_at": record.get("started_at"),
                                    "finished_at": record.get("finished_at"), "runtime": record.get("runtime"),
                                    "inference_kind": record.get("inference_kind"),
                                    "evidence_kind": record.get("evidence_kind"),
                                    "execution_status": record.get("execution_status"),
                                    "code": record.get("code"), "model": record.get("model"),
                                    "reproduction_pins_matched": record.get("reproduction_pins_matched"),
                                    "official_gold_accuracy": record.get("official_gold_accuracy"),
                                    "legal_accuracy_claimed": record.get("legal_accuracy_claimed")},
        "raw_inference.json": {**source, "cases": [
            {k: c.get(k) for k in ("case_id", "execution_status", "evidence_ids", "prompt_tokens",
                                   "generated_token_count", "finish_reason", "raw_output", "response",
                                   "output_validation", "failure_category", "error")} for c in cases]},
        "gpu_performance.json": {**source, "environment": record.get("environment"),
                                 "load": {k: v for k, v in load.items() if k != "quantization"},
                                 "cases": [{"case_id": c.get("case_id"), **(c.get("metrics") or {})} for c in cases]},
        "checkpoint_provenance.json": {**source, "model": record.get("model"), "provenance": record.get("provenance"),
                                       "loaded_quantization": load.get("quantization")},
        "validation_summary.json": {**source, "record_validation_in_record": record.get("record_validation"),
                                    "record_validation_recomputed": check,
                                    "scope": "Structural self-check of our own JSON; not external attestation",
                                    "execution_status": record.get("execution_status"),
                                    "cases": {c.get("case_id"): c.get("execution_status") for c in cases},
                                    "official_gold_accuracy": None, "independent_legal_review": "not_verified"},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    raw = args.record.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    (args.out_dir / "raw_record.json").write_bytes(raw)
    for name, value in views(json.loads(raw), digest).items():
        (args.out_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(digest)


if __name__ == "__main__":
    main()
