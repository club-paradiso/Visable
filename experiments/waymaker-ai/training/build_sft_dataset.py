"""Build the Artemis SFT file from validated benchmark-format train examples.

Why a build step at all, instead of training on the examples directly: the
trainer must see exactly the bytes the gates passed. This script runs the
gates once and writes a deterministic JSONL file; train_qlora.py rebuilds it in
memory and refuses to train if the file on disk differs by one byte.

What it refuses (the whole build, never one example quietly):

* a train file the dataset validator (``waymaker_ai.dataset.validate``) fails;
* an example that is unreviewed or disputed, or a critical example whose label
  is not ``human_verified`` with a named reviewer and date;
* a ``teacher_generated`` example in an arm that does not allow them, or one
  whose TeacherRecord the teacher gate refuses (unpermitted teacher, reasoning
  text, unverified legal conclusion, missing human review, no legal sign-off);
* a task Artemis is not trained on (citation, temporal and abstention labels
  belong to the deterministic WLIE gate and to Athena);
* a question that lacks one of its two Artemis labels, or whose classification
  label leaves current_status, target_status or needs_clarification unstated
  (the evaluation runner asks one prompt and one 7-key schema for both tasks,
  so a missing key would have to be guessed);
* duplicates inside the train split, and any train question whose word 3-gram
  overlap with a dev, test or adversarial_holdout question is above the
  config's threshold.

Output: one record per question, ``{"question": ..., "prompt": [system,
user], "completion": [assistant], "meta": {...}}``. The prompt is exactly the
runner's ``openai_compatible`` request messages, and the assistant turn is the
runner's 7-key object built from the two labels. Structured labels only: no
reasoning and no legal facts are ever a target. ``question`` sits at the top
level so the runner's ``--contamination-check`` can read the file.

Usage, from experiments/waymaker-ai::

    python training/build_sft_dataset.py --config configs/artemis/exp_b_sft_qlora.json
    python training/build_sft_dataset.py --config configs/artemis/exp_b_sft_qlora.json --check-only

Exit status: 0 built (or would build), 1 refused, 2 command line error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from waymaker_ai.distillation import experiment_config, preflight, sft_dataset  # noqa: E402  (path set above)

REPORT_VERSION = "waymaker-artemis-sft-build/0.2"


def build_report(config: experiment_config.ExperimentConfig, result: sft_dataset.BuildResult) -> Dict[str, Any]:
    text = result.text()
    by_language: Dict[str, int] = {}
    teacher_ids = []
    for record in result.records:
        meta = record["meta"]
        by_language[meta["language"]] = by_language.get(meta["language"], 0) + 1
        teacher_ids.extend(e["teacher_record_id"] for e in meta["examples"] if e["teacher_record_id"])
    return {
        "schema_version": REPORT_VERSION,
        "config_id": config.id,
        "train_examples_file": config.train_examples_file,
        "train_examples": result.train_count,
        "sft_file": config.sft_file,
        "sft_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "records": len(result.records),
        "records_by_language": dict(sorted(by_language.items())),
        "critical_records": sum(1 for record in result.records if record["meta"]["critical"]),
        "eval_examples_compared": result.eval_count,
        "leakage_guard": {"ngram": config.ngram, "max_overlap": config.max_overlap, "pairs_over_threshold": 0},
        "teacher_record_ids": sorted(teacher_ids),
        "prompt_template": sft_dataset.PROMPT_TEMPLATE_ID,
        "prompt_template_sha256": sft_dataset.prompt_sha256(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the Artemis SFT file. Refuses the whole build on any problem.")
    parser.add_argument("--config", type=Path, required=True, help="configs/artemis/<arm>.json")
    parser.add_argument("--check-only", action="store_true", help="run every check, write nothing")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = experiment_config.load_config(args.config)
    except (OSError, experiment_config.ConfigError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    if config.arm == "A":
        print(f"REFUSED: {config.id} is the untuned control; it has no training data to build", file=sys.stderr)
        return 1

    result, problems = preflight.build_from_config(config)
    if problems or result is None or not result.ok:
        problems = problems or ["the build produced no usable records"]
        print(f"REFUSED: {config.id}: nothing was written ({len(problems)} problem(s)):", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    report = build_report(config, result)
    if args.check_only:
        print(f"{config.id}: {report['records']} records would be written to {config.sft_file} (sha256 {report['sft_sha256']})")
        return 0

    out_path = config.resolve(config.sft_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result.text(), encoding="utf-8")
    report_path = out_path.with_name(out_path.name + ".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{config.id}: wrote {report['records']} records to {config.sft_file} (sha256 {report['sft_sha256']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
