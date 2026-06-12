#!/usr/bin/env python3
"""Build Colab-ready train/eval JSONL files for the Waymaker Gemma-4 experiment.

Takes one or more JSONL files in the `messages` format (system/user/assistant),
keeps only structurally valid examples, de-duplicates, shuffles with a fixed
seed, splits train/eval, and writes `train.jsonl` / `eval.jsonl`.

Intended use: when real Waymaker evidence_pack examples are exported, point this
script at them to produce the files the Colab notebook consumes. With no
arguments it rebuilds from the bundled placeholder samples.

Usage:
    python scripts/build_colab_dataset.py \
        --input dataset/train.sample.jsonl dataset/eval.sample.jsonl \
        --outdir dataset/build --eval-ratio 0.2 --seed 42
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_INPUTS = [
    HERE.parent / "dataset" / "train.sample.jsonl",
    HERE.parent / "dataset" / "eval.sample.jsonl",
]


def is_valid(rec):
    msgs = rec.get("messages")
    if not isinstance(msgs, list) or [m.get("role") for m in msgs] != ["system", "user", "assistant"]:
        return False
    if any(not isinstance(m.get("content"), str) or not m["content"].strip() for m in msgs):
        return False
    return "[evidence_pack]" in msgs[1]["content"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", nargs="+", default=[str(p) for p in DEFAULT_INPUTS])
    ap.add_argument("--outdir", default=str(HERE.parent / "dataset" / "build"))
    ap.add_argument("--eval-ratio", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-examples", type=int, default=0, help="0 = no limit")
    args = ap.parse_args()

    seen = set()
    examples = []
    skipped = 0
    for path in args.input:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                if not is_valid(rec):
                    skipped += 1
                    continue
                key = json.dumps(rec, ensure_ascii=False, sort_keys=True)
                if key in seen:
                    skipped += 1
                    continue
                seen.add(key)
                examples.append(rec)

    if not examples:
        print("No valid examples found.")
        return 1

    rng = random.Random(args.seed)
    rng.shuffle(examples)
    if args.max_examples > 0:
        examples = examples[: args.max_examples]

    n_eval = max(1, round(len(examples) * args.eval_ratio)) if len(examples) > 1 else 0
    eval_set, train_set = examples[:n_eval], examples[n_eval:]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train.jsonl", train_set), ("eval.jsonl", eval_set)):
        with open(outdir / name, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"wrote {outdir / name} ({len(rows)} examples)")

    print(f"skipped (invalid/duplicate): {skipped}")
    print("Reminder: run scripts/validate_dataset.py on the outputs before training.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
