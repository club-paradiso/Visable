"""Verify the pinned offline checkpoint without loading an ML model or downloading.

This records file integrity only. It cannot certify runtime compatibility,
model behavior, independent evaluation or legal accuracy.
"""
import argparse
import datetime as dt
import json
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from waymaker_ai import foundation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["gemma4_e4b", "gemma4_e2b"], default="gemma4_e4b")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Refusing to overwrite existing verification evidence")
    selected = foundation.profile(args.profile)
    snapshot = foundation.find_snapshot(selected, args.cache_dir)
    start = time.perf_counter()
    record = {"kind": "checkpoint_integrity_only_no_inference", "profile": args.profile,
              "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
              "model": selected["inference_checkpoint"], "revision": selected["inference_revision"],
              "snapshot": str(snapshot) if snapshot else None, "status": "failed", "verification": None,
              "inference_execution_status": "not_executed", "official_gold_accuracy": None}
    try:
        if snapshot is None:
            raise FileNotFoundError("Pinned offline checkpoint missing; no download or fallback")
        record["verification"] = foundation.validate_snapshot(snapshot, selected)
        record["status"] = "verified"
    except (OSError, ValueError, TypeError, KeyError) as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    record.update(elapsed_seconds=time.perf_counter() - start,
                  peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                  * (1 if sys.platform == "darwin" else 1024))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": record["status"], "error": record.get("error")}))
    return 0 if record["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
