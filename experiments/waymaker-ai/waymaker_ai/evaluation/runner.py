"""Evaluation runner: score baselines on the frozen benchmark splits.

Usage (from experiments/waymaker-ai)::

    python -m waymaker_ai.evaluation.runner --benchmark datasets/benchmark/v0 \\
        --baselines b1_python,b2_js,wlie,existing_law,mock_model \\
        --splits dev,test,adversarial_holdout \\
        --out reports/<name>.json [--markdown reports/<name>.md] \\
        [--backend-root <tree with backend/>] [--fail-on-hard-gates wlie] [--include-raw]

Why it is built this way:

* **One input per example for every baseline** (the equivalent-input rule):
  each baseline reads the same ``input`` fields, converted only into the form
  its interface accepts. An example a baseline cannot receive equivalently is
  ``not_equivalent_input``, never scored.
* **Backend code never runs in this process.** Backend baselines are child
  processes of the backend interpreter (``baselines/base.py``); this module
  and everything it imports are standard-library only.
* **Nothing is hidden in an average.** Each metric reports correct / wrong /
  denominator / not-scorable with reasons, separately per baseline, per split
  and per task. ``train`` is never evaluated.
* **Before/after on the same benchmark.** ``--backend-root`` points the
  subprocess baselines (b1_python, b1_python_raw, existing_law) at another
  ``backend/`` tree, e.g. a ``git archive`` of origin/main, and the report
  records that tree's content digest (and git tree id when it is a checkout).
* **A CI gate that cannot pass by not running.** ``--fail-on-hard-gates``
  exits 1 when a named baseline is unavailable, or any of its hard gates is
  ``fail`` or ``insufficient_evidence`` (12 §7.2: an empty hard gate is never a
  pass).

Method, metric definitions and gates: docs/ai/waymaker-genesis/12-evaluation-methodology.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from waymaker_ai.contracts import normalize_text
from waymaker_ai.evaluation import report as report_mod
from waymaker_ai.evaluation.baselines import create as create_baselines
from waymaker_ai.evaluation.baselines.b1_python import default_backend_python
from waymaker_ai.evaluation.baselines.base import Baseline, EvalItem, ItemResult, RunContext
from waymaker_ai.evaluation.benchmark import (
    DEFAULT_FIXTURES_DIR,
    EVALUATION_SPLITS,
    EXPERIMENT_ROOT,
    BundleStore,
    label_status_of,
    load_benchmark,
    payload_code_of,
)
from waymaker_ai.evaluation.gates import DECISION_SPLITS, evaluate_gates
from waymaker_ai.evaluation.metrics import NOT_SCORABLE, ItemScore, aggregate, score_item
from waymaker_ai.evaluation.summary import critical_categories, headline, performance

REPO_ROOT = EXPERIMENT_ROOT.parents[1]

#: ItemResult.status → not-scorable reason when there is no prediction.
_NO_PREDICTION_REASON = {
    "error": "baseline_error",
    "not_equivalent_input": "not_equivalent_input",
    "unavailable": "baseline_unavailable",
    "not_applicable": "not_applicable",
}

HOLDOUT_NOTICE = ("adversarial_holdout is reported once per frozen benchmark version: do not tune on it, "
                  "and do not re-run it after changing code in response to its result.")


@dataclass
class RunConfig:
    benchmark: Path
    baselines: List[str]
    splits: List[str]
    out: Optional[Path] = None
    markdown: Optional[Path] = None
    fixtures: Path = DEFAULT_FIXTURES_DIR
    repo_root: Path = REPO_ROOT
    backend_python: Optional[Path] = None
    node: Optional[str] = "node"
    timeout_seconds: float = 600.0
    tasks: Optional[List[str]] = None
    contamination_files: List[Path] = field(default_factory=list)
    holdout_ledger: Optional[Path] = None
    argv: List[str] = field(default_factory=list)
    #: Tree whose backend/ the subprocess baselines import (None: repo_root).
    backend_root: Optional[Path] = None
    #: Keep each item's bounded raw payload (default: raw_sha256 only).
    include_raw: bool = False
    #: Baselines whose hard gates decide the exit status (CI).
    fail_on_hard_gates: List[str] = field(default_factory=list)
    #: Why this holdout run is a post-hoc re-scoring (the items were already
    #: looked at under an earlier benchmark digest). None: not declared post hoc.
    holdout_post_hoc: Optional[str] = None


class RunnerError(Exception):
    pass


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
def run_evaluation(config: RunConfig, baselines: Optional[Sequence[Baseline]] = None) -> Dict[str, Any]:
    """Run every baseline on the selected splits and build the report dict."""
    bad = [s for s in config.splits if s not in EVALUATION_SPLITS]
    if bad:
        raise RunnerError(f"split(s) {', '.join(bad)} cannot be evaluated; allowed: {', '.join(EVALUATION_SPLITS)}")
    check_backend_root(config.backend_root)
    bench = load_benchmark(config.benchmark)
    examples = bench.select(config.splits)
    if config.tasks:
        examples = [ex for ex in examples if ex["task"] in set(config.tasks)]
    store = BundleStore(config.fixtures)
    items = [EvalItem(ex, store.get(ex["input"]["fixture_set"]) if ex["input"].get("fixture_set") else None)
             for ex in examples]
    systems = list(baselines) if baselines is not None else create_baselines(config.baselines)
    backend_python = config.backend_python or default_backend_python(config.repo_root)

    with tempfile.TemporaryDirectory(prefix="waymaker-eval-") as scratch:
        ctx = RunContext(repo_root=config.repo_root, backend_python=backend_python, node=config.node,
                         scratch_dir=Path(scratch), timeout_seconds=config.timeout_seconds,
                         backend_root=config.backend_root)
        runs = [(system, *_run_baseline(system, items, ctx, include_raw=config.include_raw)) for system in systems]
        process_info = dict(ctx.process_info)

    report: Dict[str, Any] = {
        "report_schema": report_mod.REPORT_SCHEMA,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "command": _command(config),
        "environment": report_mod.environment(config.repo_root, EXPERIMENT_ROOT, backend_python, config.node,
                                              backend_root=config.backend_root,
                                              hash_backend=any(system.uses_backend for system in systems)),
        "benchmark": _benchmark_section(bench, examples, config),
        "source_bundles": store.describe(),
        "policy": {
            "splits_scored": list(config.splits),
            "decision_splits": list(DECISION_SPLITS),
            "held_out": HOLDOUT_NOTICE,
            "labels": ("Labels are as recorded in label_review; a GO decision requires every scored label on the "
                       "decision splits to be human_verified, otherwise the best decision is PROVISIONAL_GO."),
            "text_similarity": "not used for correctness",
            "fixtures": "Synthetic or recorded source bundles; no live API call is made by any baseline.",
            "raw_payloads": (report_mod.RAW_PAYLOAD_POLICY_INCLUDED if config.include_raw
                             else report_mod.RAW_PAYLOAD_POLICY_OMITTED),
        },
        "baselines": {},
        "results": {},
        "headline": {},
        "headline_by_split": {},
        "headline_text_only": {},
        "by_adversarial_class": {},
        "critical_legal_errors": {},
        "violation_flags": {},
        "not_scorable": {},
        "performance": {},
        "gates": {},
        "items": {},
    }
    for split in config.splits:
        report["headline_by_split"][split] = {}
    for system, available, reason, records in runs:
        _fill_baseline(report, system, available, reason, records, config.splits, process_info.get(system.name))
    if config.contamination_files:
        report["contamination"] = contamination_check(examples, config.contamination_files)
    if config.holdout_ledger and "adversarial_holdout" in config.splits:
        report["holdout_ledger"] = record_holdout_run(config.holdout_ledger, report,
                                                      post_hoc_reason=config.holdout_post_hoc)
    report["scoring_digest"] = report_mod.scoring_digest(report)
    return report


def _run_baseline(system: Baseline, items: Sequence[EvalItem], ctx: RunContext, *, include_raw: bool = False
                  ) -> Tuple[bool, str, List[Dict[str, Any]]]:
    applicable = [item for item in items if item.task in system.tasks]
    try:
        available, reason = system.available(ctx)
    except Exception as exc:  # an availability probe must not take the run down
        available, reason = False, f"availability check failed: {type(exc).__name__}: {exc}"
    if not available:
        results = {item.id: ItemResult(item.id, "unavailable", error=reason) for item in applicable}
    else:
        try:
            results = system.run(applicable, ctx) if applicable else {}
        except Exception as exc:
            results = {item.id: ItemResult(item.id, "error", error=f"{type(exc).__name__}: {exc}"[:500])
                       for item in applicable}
    records = [_score_record(system, item, results.get(item.id), include_raw=include_raw) for item in applicable]
    return available, reason, records


def _score_record(system: Baseline, item: EvalItem, result: Optional[ItemResult], *,
                  include_raw: bool = False) -> Dict[str, Any]:
    result = result or ItemResult(item.id, "error", error="baseline returned no result for this item")
    emits = system.emits.get(item.task, frozenset())
    if result.status == "ok" and result.prediction is not None:
        score = score_item(item.example, result.prediction, emits)
    else:
        score = score_item(item.example, None, emits, error=result.error or None,
                           reason=_NO_PREDICTION_REASON.get(result.status, "baseline_error"))
    primary_wrong = score.primary_wrong()
    verdict = "not_scorable" if primary_wrong is None else ("wrong" if primary_wrong else "correct")
    categories = critical_categories(item.example, score.flags, primary_wrong) if result.status == "ok" else []
    return {
        "id": item.id,
        "split": item.split,
        "task": item.task,
        "critical": bool(item.example.get("critical")),
        "adversarial_class": (item.example.get("scenario") or {}).get("adversarial_class"),
        "label_review": label_status_of(item.example),
        "payload_status_code": payload_code_of(item.example),
        "status": result.status,
        "error": result.error or None,
        "prediction": result.prediction,
        **report_mod.raw_fields(result.raw, include=include_raw),
        "metrics": {name: [outcome, reason] for name, (outcome, reason) in sorted(score.metrics.items())},
        "flags": sorted(set(score.flags)),
        "verdict": verdict,
        "critical_categories": categories,
        "latency_ms": result.latency_ms,
        "upstream_calls": result.upstream_calls,
        "peak_memory_bytes": result.peak_memory_bytes,
        "memory_kind": result.memory_kind,
        "tokens": result.tokens,
        "notes": sorted(result.notes),
        "_score": score,
    }


def _fill_baseline(report: Dict[str, Any], system: Baseline, available: bool, reason: str,
                   records: List[Dict[str, Any]], splits: Sequence[str], process: Optional[Mapping[str, Any]]) -> None:
    name = system.name
    report["baselines"][name] = {**system.describe(), "available": available, "unavailable_reason": reason or None,
                                 "process": dict(process or {})}
    report["results"][name], report["headline"][name] = {}, {}
    report["headline_text_only"][name], report["by_adversarial_class"][name] = {}, {}
    report["performance"][name], report["not_scorable"][name], report["violation_flags"][name] = {}, {}, {}
    for split in splits:
        in_split = [r for r in records if r["split"] == split]
        by_task = _aggregate_by_task(in_split)
        report["results"][name][split] = by_task
        report["headline"][name][split] = headline(by_task)
        report["headline_by_split"][split][name] = report["headline"][name][split]
        # Equivalent-input slice: questions without a UI payload code (doc 13 D1 compares on these).
        report["headline_text_only"][name][split] = headline(
            _aggregate_by_task([r for r in in_split if not r["payload_status_code"]]))
        report["by_adversarial_class"][name][split] = _verdicts_by_class(in_split)
        report["performance"][name][split] = performance([r for r in in_split if r["status"] == "ok"])
        report["not_scorable"][name][split] = _not_scorable_reasons(in_split)
        report["violation_flags"][name][split] = dict(sorted(Counter(
            flag for r in in_split for flag in r["flags"]).items()))
    report["critical_legal_errors"][name] = [
        {"example_id": r["id"], "split": r["split"], "task": r["task"], "categories": r["critical_categories"],
         "critical_label": r["critical"], "adversarial_class": r["adversarial_class"]}
        for r in records if r["critical_categories"]
    ]
    report["gates"][name] = _gates_for(records, splits)
    report["items"][name] = [{k: v for k, v in r.items() if k != "_score"} for r in records]


def _aggregate_by_task(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by_task: Dict[str, List[ItemScore]] = {}
    for record in records:
        by_task.setdefault(record["task"], []).append(record["_score"])
    out = {}
    for task in sorted(by_task):
        task_records = [r for r in records if r["task"] == task]
        errors = sum(1 for r in task_records if r["status"] == "error")
        out[task] = aggregate(by_task[task], errors=errors, items=len(task_records))
        out[task]["item_status"] = dict(sorted(Counter(r["status"] for r in task_records).items()))
        out[task]["verdicts"] = dict(sorted(Counter(r["verdict"] for r in task_records).items()))
    return out


def _verdicts_by_class(records: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, int]]:
    """Item verdicts per adversarial class ("none" for ordinary items)."""
    out: Dict[str, Counter] = {}
    for record in records:
        out.setdefault(record["adversarial_class"] or "none", Counter())[record["verdict"]] += 1
    return {cls: dict(sorted(counts.items())) for cls, counts in sorted(out.items())}


def _not_scorable_reasons(records: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    reasons: Counter = Counter()
    for record in records:
        for _name, (outcome, why) in record["metrics"].items():
            if outcome == NOT_SCORABLE:
                reasons[why or "unspecified"] += 1
    return dict(sorted(reasons.items()))


def _gates_for(records: Sequence[Mapping[str, Any]], splits: Sequence[str]) -> Dict[str, Any]:
    decision = [r for r in records if r["split"] in DECISION_SPLITS]
    by_task = _aggregate_by_task(decision)
    extras = {
        "errors": sum(1 for r in decision if r["status"] == "error"),
        "applicable": len(decision),
        "critical": sum(1 for r in decision if r["critical_categories"]),
        "scored": sum(1 for r in decision if r["verdict"] != "not_scorable"),
        "critical_label_review": dict(Counter(r["label_review"] for r in decision if r["critical"])),
        "label_review": dict(Counter(r["label_review"] for r in decision if r["verdict"] != "not_scorable")),
    }
    head = headline(by_task)
    latency = performance([r for r in decision if r["status"] == "ok"])["latency_ms"]
    if latency["n"]:
        head["performance.latency_p95_ms"] = {"kind": "value", "value": latency["p95"], "numerator": None,
                                              "denominator": latency["n"], "not_scorable": 0}
    return evaluate_gates(head, extras, [s for s in splits if s in DECISION_SPLITS])


def _benchmark_section(bench: Any, examples: Sequence[Mapping[str, Any]], config: RunConfig) -> Dict[str, Any]:
    counts: Dict[str, Dict[str, int]] = {}
    for example in examples:
        counts.setdefault(example["split"], {}).setdefault(example["task"], 0)
        counts[example["split"]][example["task"]] += 1
    files = [{"path": f.path, "sha256": f.sha256, "examples": f.examples} for f in bench.files]
    return {
        "root": _display_path(config.benchmark),
        "digest": benchmark_digest(files, bench.manifest.manifest_files),
        "files": files,
        "manifest": bench.manifest.to_dict(),
        "invalid_examples": [{"path": i.path, "line": i.line, "example_id": i.example_id, "reason": i.reason}
                             for i in bench.invalid],
        # Hashed into the digest above, never read as examples (waymaker_ai.dataset.layout).
        "non_example_files": [{"path": f.path, "reason": f.reason} for f in bench.non_example_files],
        "selected": {"splits": list(config.splits), "tasks": sorted(config.tasks) if config.tasks else None,
                     "counts": {s: dict(sorted(c.items())) for s, c in sorted(counts.items())},
                     "total": len(examples)},
        "label_review": dict(sorted(Counter(label_status_of(ex) for ex in examples).items())),
        "critical_examples": sum(1 for ex in examples if ex.get("critical")),
    }


def _display_path(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(EXPERIMENT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _command(config: RunConfig) -> Dict[str, Any]:
    argv = [sys.executable, "-m", "waymaker_ai.evaluation.runner", *config.argv]
    return {"argv": argv, "cwd": os.getcwd(), "shell": f"cd {shlex.quote(os.getcwd())} && {shlex.join(argv)}"}


# ---------------------------------------------------------------------------
# Another backend tree, and the CI hard-gate check
# ---------------------------------------------------------------------------
def check_backend_root(backend_root: Optional[Path]) -> None:
    """A --backend-root must be a tree that contains backend/paradiso_backend.py."""
    if backend_root is None:
        return
    root = Path(backend_root)
    if (root / "backend" / "paradiso_backend.py").is_file():
        return
    hint = (" (it looks like a backend/ directory itself: pass the directory that contains backend/)"
            if (root / "paradiso_backend.py").is_file() else "")
    raise RunnerError(f"--backend-root {root} has no backend/paradiso_backend.py{hint}")


#: Hard-gate states that fail --fail-on-hard-gates. not_applicable does not:
#: a gate on a task the baseline does not answer cannot be evidence either way.
FAILING_HARD_GATE_STATES = ("fail", "insufficient_evidence")


def hard_gate_failures(report: Mapping[str, Any], names: Sequence[str]) -> Dict[str, List[str]]:
    """For each named baseline, why its hard gates are not shown to pass ([] when they are).

    A baseline that is missing from the report or was unavailable fails: a gate
    that never ran proves nothing. A hard gate fails the check when its status
    is ``fail`` or ``insufficient_evidence`` (an empty denominator is never a
    pass, 12 §7.2). Soft gates and timing rows never enter this check.
    """
    failures: Dict[str, List[str]] = {}
    for name in names:
        info = (report.get("baselines") or {}).get(name)
        gate_report = (report.get("gates") or {}).get(name)
        if info is None or gate_report is None:
            failures[name] = ["baseline was not run"]
            continue
        problems: List[str] = []
        if not info.get("available"):
            problems.append(f"baseline unavailable: {info.get('unavailable_reason')}")
        if not gate_report.get("decision_splits"):
            problems.append("no decision split (test, adversarial_holdout) was scored")
        for gate in gate_report.get("gates") or []:
            if gate.get("hard") and gate.get("status") in FAILING_HARD_GATE_STATES:
                base = "" if gate.get("denominator") is None else f" ({gate.get('numerator')}/{gate.get('denominator')})"
                problems.append(f"{gate['id']} {gate['status']}{base}: {gate.get('metric')}")
        failures[name] = problems
    return failures


# ---------------------------------------------------------------------------
# Contamination: exact overlap of normalized questions with training files
# ---------------------------------------------------------------------------
def _question_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).lower().encode("utf-8")).hexdigest()


def _training_texts(record: Mapping[str, Any]) -> List[str]:
    texts: List[str] = []
    inp = record.get("input")
    if isinstance(inp, dict) and isinstance(inp.get("question"), str):
        texts.append(inp["question"])
    for key in ("question", "prompt"):
        if isinstance(record.get(key), str):
            texts.append(record[key])
    for message in record.get("messages") or []:
        if isinstance(message, dict) and message.get("role") == "user" and isinstance(message.get("content"), str):
            texts.append(message["content"])
    return texts


def contamination_check(examples: Sequence[Mapping[str, Any]], paths: Sequence[Path]) -> Dict[str, Any]:
    """Which evaluated questions appear verbatim (after normalization) in training files.

    Exact hashing only. Near-duplicate detection belongs to the dataset
    pipeline (training-distill §4.6); this check is the cheap last line.
    """
    wanted: Dict[str, List[str]] = {}
    for example in examples:
        wanted.setdefault(_question_hash(str(example["input"].get("question") or "")), []).append(example["id"])
    overlaps: Dict[str, List[str]] = {}
    files = []
    for path in paths:
        lines = 0
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                lines += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for text in _training_texts(record):
                    for example_id in wanted.get(_question_hash(text), []):
                        overlaps.setdefault(example_id, []).append(Path(path).name)
        files.append({"path": str(path), "sha256": report_mod.sha256_path(Path(path)), "records": lines})
    return {"files": files, "overlap_count": len(overlaps),
            "overlaps": {k: sorted(set(v)) for k, v in sorted(overlaps.items())}}


# ---------------------------------------------------------------------------
# Held-out ledger: adversarial_holdout is reported once per benchmark version
# ---------------------------------------------------------------------------
def benchmark_digest(files: Sequence[Mapping[str, Any]], manifest_files: Sequence[Mapping[str, Any]]) -> str:
    """One sha256 naming the exact benchmark bytes (example files plus manifest files)."""
    rows = sorted((str(f["path"]), str(f["sha256"])) for f in list(files) + list(manifest_files))
    return hashlib.sha256(json.dumps(rows).encode("utf-8")).hexdigest()


def record_holdout_run(ledger: Path, report: Mapping[str, Any], *,
                       post_hoc_reason: Optional[str] = None) -> Dict[str, Any]:
    """Append this holdout run to an append-only JSONL ledger and say whether it is a repeat.

    The runner does not refuse a repeat (the person running it decides), but a
    repeat is stated in the report and on stderr, so a second look at the
    holdout cannot pass as a first one.

    A changed label or fixture gives a new benchmark digest, so the digest
    count alone would call a re-scoring of already-seen items a first look.
    ``post_hoc_reason`` declares the run post hoc: the entry and the report
    carry ``post_hoc: true`` with the reason and the number of earlier ledger
    entries under any digest, whatever the digest count says.
    """
    digest = report["benchmark"]["digest"]
    prior = prior_any = 0
    if ledger.is_file():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict):
                continue
            prior_any += 1
            if entry.get("benchmark_digest") == digest:
                prior += 1
    entry = {"benchmark_digest": digest, "generated_at": report["generated_at"],
             "git_commit": (report.get("environment") or {}).get("git_commit"),
             "baselines": sorted(report.get("baselines") or {})}
    result: Dict[str, Any] = {"path": str(ledger), "prior_runs_for_this_benchmark": prior, "repeat": prior > 0}
    if post_hoc_reason is not None:
        reason = " ".join(str(post_hoc_reason).split())
        if not reason:
            raise RunnerError("a post-hoc holdout run needs a reason")
        entry.update({"post_hoc": True, "post_hoc_reason": reason, "prior_ledger_entries": prior_any})
        result.update({"post_hoc": True, "post_hoc_reason": reason, "prior_ledger_entries": prior_any})
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _csv(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_args(argv: Sequence[str]) -> RunConfig:
    parser = argparse.ArgumentParser(prog="python -m waymaker_ai.evaluation.runner",
                                     description="Score baselines on the Waymaker benchmark (offline).")
    parser.add_argument("--benchmark", required=True, type=Path, help="benchmark directory (e.g. datasets/benchmark/v0)")
    parser.add_argument("--baselines", required=True, type=_csv, help="comma-separated baseline names")
    parser.add_argument("--splits", default="dev", type=_csv, help="comma-separated splits (dev, test, adversarial_holdout)")
    parser.add_argument("--out", type=Path, help="report JSON path")
    parser.add_argument("--markdown", type=Path, help="report Markdown path")
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES_DIR, help="source bundle directory")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="repository root (backend/, assets/js)")
    parser.add_argument("--backend-python", type=Path, help="backend interpreter (default: this interpreter)")
    parser.add_argument("--node", default="node", help="node executable for the JS baseline")
    parser.add_argument("--timeout", type=float, default=600.0, help="seconds per baseline subprocess")
    parser.add_argument("--tasks", type=_csv, help="only these tasks")
    parser.add_argument("--contamination-check", type=Path, action="append", default=[],
                        help="JSONL training file to check for exact question overlap (repeatable)")
    parser.add_argument("--holdout-ledger", type=Path,
                        help="append-only JSONL ledger of adversarial_holdout runs (records repeats)")
    parser.add_argument("--holdout-post-hoc", metavar="REASON",
                        help="declare this holdout run a post-hoc re-scoring of items already looked at (for "
                             "example after relabelling); recorded with REASON in the ledger and the report")
    parser.add_argument("--backend-root", type=Path,
                        help="tree containing backend/ for b1_python, b1_python_raw and existing_law "
                             "(e.g. a git archive of origin/main; default: --repo-root)")
    parser.add_argument("--fail-on-hard-gates", type=_csv, default=[], metavar="BASELINE[,BASELINE]",
                        help="exit 1 unless every hard gate of these baselines passes or is not applicable")
    parser.add_argument("--include-raw", action="store_true",
                        help="keep each item's bounded raw baseline output (default: raw_sha256 only)")
    args = parser.parse_args(list(argv))
    gated = list(dict.fromkeys(args.fail_on_hard_gates))
    not_run = [name for name in gated if name not in args.baselines]
    if not_run:
        parser.error(f"--fail-on-hard-gates names baseline(s) not in --baselines: {', '.join(not_run)}")
    if args.holdout_post_hoc is not None and not args.holdout_ledger:
        parser.error("--holdout-post-hoc needs --holdout-ledger: a post-hoc look is recorded, never silent")
    if args.holdout_post_hoc is not None and not args.holdout_post_hoc.strip():
        parser.error("--holdout-post-hoc needs a non-empty reason")
    return RunConfig(
        benchmark=args.benchmark, baselines=list(dict.fromkeys(args.baselines)), splits=list(dict.fromkeys(args.splits)),
        out=args.out, markdown=args.markdown, fixtures=args.fixtures, repo_root=args.repo_root,
        backend_python=args.backend_python or default_backend_python(args.repo_root), node=args.node,
        timeout_seconds=args.timeout, tasks=args.tasks, contamination_files=list(args.contamination_check),
        holdout_ledger=args.holdout_ledger, argv=list(argv), backend_root=args.backend_root,
        include_raw=args.include_raw, fail_on_hard_gates=gated, holdout_post_hoc=args.holdout_post_hoc,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    config = parse_args(argv)
    if "adversarial_holdout" in config.splits:
        print(f"notice: {HOLDOUT_NOTICE}", file=sys.stderr)
    try:
        report = run_evaluation(config)
    except (RunnerError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # BenchmarkError and friends: say what, not a traceback
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if config.out:
        report_mod.write_json(report, config.out)
    if config.markdown:
        config.markdown.parent.mkdir(parents=True, exist_ok=True)
        config.markdown.write_text(report_mod.render_markdown(report), encoding="utf-8")
    if not config.out and not config.markdown:
        sys.stdout.write(report_mod.dumps(report))
    _print_summary(report)
    if config.fail_on_hard_gates:
        failures = hard_gate_failures(report, config.fail_on_hard_gates)
        for name in config.fail_on_hard_gates:
            if failures[name]:
                print(f"hard-gate check: {name} FAILED: " + "; ".join(failures[name]), file=sys.stderr)
            else:
                print(f"hard-gate check: {name} passed", file=sys.stderr)
        if any(failures.values()):
            return 1
    return 0


def _print_summary(report: Mapping[str, Any]) -> None:
    ledger = report.get("holdout_ledger") or {}
    if ledger.get("repeat"):
        print(f"warning: adversarial_holdout was already scored {ledger['prior_runs_for_this_benchmark']} time(s) "
              "for this benchmark version; this run is a repeat and must be reported as one", file=sys.stderr)
    if ledger.get("post_hoc"):
        print(f"warning: this adversarial_holdout run is declared POST-HOC ({ledger['prior_ledger_entries']} earlier "
              f"ledger entr{'y' if ledger['prior_ledger_entries'] == 1 else 'ies'}): {ledger['post_hoc_reason']}",
              file=sys.stderr)
    for name, gate_report in (report.get("gates") or {}).items():
        info = (report.get("baselines") or {}).get(name) or {}
        state = "available" if info.get("available") else f"unavailable ({info.get('unavailable_reason')})"
        criticals = len((report.get("critical_legal_errors") or {}).get(name) or [])
        print(f"{name}: {state}; critical legal errors {criticals}; gates {gate_report['decision']}", file=sys.stderr)
    print(f"scoring digest {report.get('scoring_digest')}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
