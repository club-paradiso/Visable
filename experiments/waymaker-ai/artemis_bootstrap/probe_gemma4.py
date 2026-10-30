"""Record one bounded Korean inference attempt, or the precise preflight blocker.

This is an execution smoke test, not a legal benchmark. No evidence is supplied;
the response contract therefore asks the model to withhold legal conclusions.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

from artemis_runner import LocalModelAdapter
from gemma4_runtime import resources, resource_blockers, build_messages

QUESTION = "체류기간을 연장하려면 어떤 사항을 확인해야 하나요?"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", help="Explicit interpreter with MLX-VLM")
    parser.add_argument("--profile", choices=["gemma4_e4b", "gemma4_e2b"], default="gemma4_e4b")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-tokens", type=int, choices=[32, 64, 128], default=32,
                        help="32 first; 64/128 only for a safe, explicitly authorized bounded retry")
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error("Refusing to overwrite an existing inference record")
    adapter = LocalModelAdapter(profile=args.profile, python_executable=args.python, max_tokens=args.max_tokens)
    metadata = adapter.get_metadata()
    record = {
        "project": "Waymaker Artemis", "kind": "real_inference_smoke",
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(), "question": QUESTION,
        "input_messages": build_messages({"question": QUESTION, "evidence": []}),
        "max_tokens": args.max_tokens, "highest_completed_stage": "checkpoint_verified" if metadata.get("checkpoint_integrity_verified") else "preflight",
        "model_metadata": metadata, "resources_before": resources(),
        "execution_status": "not_executed", "not_executed_reason": metadata["not_available_reason"],
        "raw_generated_response": None, "generated_token_count": None,
        "load_seconds": None, "prefill_seconds": None, "generation_seconds": None,
        "tokens_per_second": None, "official_gold_accuracy": None,
        "warnings": metadata.get("runtime_probe", {}).get("warnings", []),
        "output_validation": {"passed": None, "reason": "No generation attempted"},
    }
    if not metadata["available"]:
        record["failure_category"] = ("memory_resource_rejection" if resource_blockers(record["resources_before"])
                                      else "dependency_or_checkpoint_failure")
    if metadata["available"]:
        response = adapter.generate({"question": QUESTION, "evidence": []})
        data = response.telemetry or {}
        telemetry = data.get("telemetry", {})
        record.update(
            execution_status=data.get("execution_status", "failed"),
            raw_generated_response=response.raw_output, error=response.error,
            generated_token_count=telemetry.get("generation_tokens"),
            load_seconds=telemetry.get("load_seconds"),
            prefill_seconds=telemetry.get("prefill_seconds_derived"),
            generation_seconds=telemetry.get("generation_wall_seconds"),
            tokens_per_second=telemetry.get("generation_tps"), worker_result=data,
            highest_completed_stage=data.get("highest_completed_stage", "runtime_preflight_passed"),
            output_validation=data.get("output_validation", {"passed": None, "reason": "No generated output available"}),
            failure_category=data.get("failure_category"),
        )
        record["not_executed_reason"] = response.error if record["execution_status"] == "not_executed" else None
        record["warnings"].extend(data.get("warnings", []))
    record["resources_after"] = resources()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": record["execution_status"], "reason": record["not_executed_reason"]}))
    return {"completed": 0, "generated_but_invalid": 2, "failed": 1, "not_executed": 3}[record["execution_status"]]


if __name__ == "__main__":
    raise SystemExit(main())
