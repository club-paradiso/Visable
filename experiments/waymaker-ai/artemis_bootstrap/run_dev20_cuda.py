"""Mission 005-D: generate the 20 development-candidate responses with one loaded model.

Generation only. Each item goes through inference_input.project_inference_item
inside the CUDA session, so answer keys, rubrics and review metadata never reach
the prompt. Scoring happens afterwards, offline, in score_dev20.py.

Every finished case is appended to generations.jsonl and fsynced, so a dropped
Colab session keeps what it finished. A rerun skips recorded case IDs (no
overwrite, no double count, no automatic retry) and logs a new session in
sessions.jsonl, which shows whether the model was loaded again.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

BOOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BOOT.parent))
sys.path.insert(0, str(BOOT))
from waymaker_ai import cuda_policy
from waymaker_ai.inference_input import project_inference_item
from waymaker_ai.response_contract import CONTRACT_VERSIONS, prompt_sha256
from gemma4_runtime import build_messages

BENCHMARK = BOOT / "benchmarks" / "artemis_eval_dev_20.json"
ISOLATION_MANIFEST = BOOT / "benchmarks" / "BENCHMARK_ISOLATION_MANIFEST.json"
SYNTHETIC = BOOT / "validation" / "mission005e_synthetic_validation.json"
PILOT = ("ARTEMIS-004-DEV-001", "ARTEMIS-004-DEV-002", "ARTEMIS-004-DEV-003")
MAX_NEW_TOKENS = 256


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prompt_messages(item: dict, version: str = "v1") -> list:
    """The exact chat messages the session renders, rebuilt from the item alone."""
    return build_messages(project_inference_item(item), version)


def input_sha256(item: dict, version: str = "v1") -> str:
    return sha256_text(json.dumps(prompt_messages(item, version), ensure_ascii=False, sort_keys=True))


def load_synthetic_items(path: Path = SYNTHETIC) -> tuple[list, str]:
    """Mission 005-E synthetic validation cases: fictional, kept apart from DEV-20."""
    raw = path.read_bytes()
    items = json.loads(raw)["cases"]
    if len({i["id"] for i in items}) != len(items):
        raise ValueError("Duplicate synthetic case IDs")
    return items, hashlib.sha256(raw).hexdigest()


def load_dev_items(path: Path = BENCHMARK) -> tuple[list, str]:
    """Only the development split whose digest the isolation manifest records."""
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    manifest = json.loads(ISOLATION_MANIFEST.read_text(encoding="utf-8"))
    if digest != manifest["partitions"]["dev_sha256"]:
        raise ValueError("Benchmark is not the manifest-recorded development split; refusing to run")
    items = json.loads(raw)["items"]
    ids = [i["id"] for i in items]
    if len(ids) != 20 or len(set(ids)) != 20:
        raise ValueError("Expected 20 unique development case IDs")
    return items, digest


def recorded_ids(path: Path) -> set:
    if not path.exists():
        return set()
    return {json.loads(line)["case_id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def append_line(path: Path, value: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def start_session(out_dir: Path, prepared, benchmark_sha256: str, label: str) -> str:
    """Log one model session. A second entry in sessions.jsonl means a reload."""
    import gemma4_cuda_runtime
    session_id = f"{label}-{uuid.uuid4().hex[:8]}"
    if not getattr(prepared, "dev20_load_id", None):
        prepared.dev20_load_id = uuid.uuid4().hex  # same value in every session that reuses this load
    header = prepared.header
    append_line(out_dir / "sessions.jsonl", {
        "session_id": session_id, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "benchmark_sha256": benchmark_sha256, "previous_sessions": len(recorded_lines(out_dir / "sessions.jsonl")),
        "model_loaded": prepared.session is not None, "blocker": prepared.blocker,
        "metadata": prepared.metadata(), "environment": header.get("environment"),
        "provenance": header.get("provenance"), "load": header.get("load"),
        "reproduction_pins_matched": header.get("reproduction_pins_matched"),
        "model_load_id": prepared.dev20_load_id,
        "contract_version": getattr(prepared, "dev20_contract_version", "v1"),
        "prompt_sha256": prompt_sha256(getattr(prepared, "dev20_contract_version", "v1")),
        "code": gemma4_cuda_runtime.code_provenance()})
    return session_id


def recorded_lines(path: Path) -> list:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def generate_cases(adapter, items: list, case_ids, out_dir: Path, session_id: str) -> dict:
    """Generate the named cases not yet recorded. Returns per-status counts for this call."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "generations.jsonl"
    done = recorded_ids(path)
    wanted = [i for i in items if i["id"] in set(case_ids)]
    version = getattr(adapter, "contract_version", "v1")
    counts = {"generated_now": 0, "skipped_already_recorded": 0}
    for item in wanted:
        if item["id"] in done:
            counts["skipped_already_recorded"] += 1
            continue
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        response = adapter.generate(item)
        data = dict(response.telemetry or {})
        raw = data.get("raw_output")
        if data.get("input_messages") is not None and data["input_messages"] != prompt_messages(item, version):
            raise RuntimeError(f"Rendered input differs from the projection for {item['id']}")
        record = {
            "case_id": item["id"], "session_id": session_id, "contract_version": version, "generated_at": started,
            "input_sha256": input_sha256(item, version),
            "execution_status": data.get("execution_status", "failed"),
            "raw_output": raw, "raw_output_sha256": sha256_text(raw) if isinstance(raw, str) else None,
            "response": data.get("response"),
            **{k: data.get(k) for k in ("evidence_ids", "prompt_tokens", "generated_token_count", "finish_reason",
                                        "metrics", "output_validation", "failure_category", "error")},
        }
        append_line(path, record)
        counts["generated_now"] += 1
        counts[record["execution_status"]] = counts.get(record["execution_status"], 0) + 1
    return counts


def main(argv=None, prepared=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--cases", choices=["pilot", "rest", "all"], default="all",
                        help="pilot = DEV-001..003, rest = DEV-004..020")
    parser.add_argument("--session-label", default="colab-t4")
    parser.add_argument("--contract", choices=CONTRACT_VERSIONS, default="v1")
    parser.add_argument("--suite", choices=["dev20", "synthetic"], default="dev20",
                        help="synthetic = Mission 005-E fictional validation cases, never mixed with DEV-20")
    args = parser.parse_args(argv)
    import artemis_runner
    import gemma4_cuda_runtime
    items, digest = load_dev_items() if args.suite == "dev20" else load_synthetic_items()
    ids = [i["id"] for i in items]
    selected = ids if args.suite == "synthetic" else \
        {"pilot": list(PILOT), "rest": [i for i in ids if i not in PILOT], "all": ids}[args.cases]
    prepared = prepared or gemma4_cuda_runtime.PreparedRun()
    adapter = artemis_runner.CudaTransformersAdapter(max_tokens=MAX_NEW_TOKENS, prepared=prepared,
                                                     contract_version=args.contract)
    available, reason = adapter.check_availability()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    # Runs that share one loaded model share one logged session per output directory.
    logged = getattr(prepared, "dev20_sessions", {})
    session_id = logged.get(str(args.out_dir))
    if session_id is None:
        prepared.dev20_contract_version = args.contract
        session_id = start_session(args.out_dir, prepared, digest, args.session_label)
        prepared.dev20_sessions = {**logged, str(args.out_dir): session_id}
    if not available:
        print(json.dumps({"status": adapter.unavailable_status(), "reason": reason}))
        return 3 if adapter.unavailable_status() == "not_executed" else 1
    counts = generate_cases(adapter, items, selected, args.out_dir, session_id)
    print(json.dumps({"session_id": session_id, **counts,
                      "recorded_total": len(recorded_ids(args.out_dir / "generations.jsonl"))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
