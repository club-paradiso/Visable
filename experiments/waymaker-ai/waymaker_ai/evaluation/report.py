"""Report assembly: provenance, deterministic JSON and the human-readable Markdown.

Why the report carries so much provenance: a score is only comparable with
another score when both name the same benchmark bytes, the same code under
test and the same interpreters. The JSON therefore records the benchmark file
and manifest hashes, the source bundle hashes, the git commit and dirty paths,
sha256 of the backend and JS files the baselines exercised, the Python / Node
versions and the exact command.

Ordering is deterministic (sorted keys, items in benchmark order, baselines in
command order). Timing, memory and the generation timestamp necessarily vary
between runs; they are kept out of ``scoring_digest``, so two runs over the
same inputs can be compared by that one hash.

Size: a baseline's raw per-item output (driver payloads, call logs) is not part
of the score. By default an item keeps only ``raw_sha256``, the sha256 of the
canonical JSON of that output, so a re-run can be compared byte for byte; the
runner's ``--include-raw`` keeps the bounded payload as well. The JSON file
writes one item per line (``dumps``), which keeps it small and makes a change in
one item's verdict a one-line diff.

``python -m waymaker_ai.evaluation.report compact IN --out OUT`` applies the
same rule to a report written before raw payloads were omitted, and refuses
unless the recomputed ``scoring_digest`` equals the recorded one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REPORT_SCHEMA = "waymaker-eval-report/0.1"

#: Files whose bytes decide a baseline's behaviour (relative to the repo root).
MEASURED_FILES: Sequence[str] = (
    "backend/paradiso_backend.py",
    "backend/services/law_grounding.py",
    "backend/services/law_tools.py",
    "backend/services/law_cloud_fallback.py",
    "backend/services/citation_verifier.py",
    "backend/services/grounding_config.py",
    "backend/services/legal_analysis.py",
    "backend/services/immigration_tools.py",
    "backend/services/knowledge/understanding.py",
    "backend/services/knowledge/models.py",
    "assets/js/status-guidance.js",
    "assets/js/search-router.js",
    "data/status-guidance-202609.json",
    "data/local-practice-202609.json",
)

#: Experiment code under test (relative to the experiment root), hashed by glob.
MEASURED_EXPERIMENT_GLOBS: Sequence[str] = ("waymaker_ai/contracts.py", "waymaker_ai/legal/*.py",
                                            "waymaker_ai/evaluation/**/*.py", "waymaker_ai/evaluation/**/*.mjs")

MAX_RAW_JSON = 4000


def sha256_path(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(cmd: Sequence[str], cwd: Optional[Path] = None) -> Optional[str]:
    try:
        proc = subprocess.run(list(cmd), capture_output=True, timeout=30, check=False, cwd=str(cwd) if cwd else None)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    # rstrip, not strip: ``git status --porcelain`` lines start with a status
    # column that may be a space (" M path"), and stripping it would shift
    # every path by one character.
    return proc.stdout.decode("utf-8", errors="replace").rstrip()


def environment(repo_root: Path, experiment_root: Path, backend_python: Path, node: Optional[str],
                backend_root: Optional[Path] = None, *, hash_backend: bool = True) -> Dict[str, Any]:
    """Provenance of the code under test.

    ``backend_root`` is the tree whose ``backend/`` the subprocess baselines
    (b1_python, b1_python_raw, existing_law) import; ``None`` means the repo
    root. When it is a separate tree, the repo's own ``backend/`` is neither
    hashed nor listed as dirty, because it is not what was measured.
    ``hash_backend`` is false when no baseline of the run imports the backend:
    the tree is then named but not hashed (about 90 MB that nothing ran).
    """
    git = shutil.which("git")
    separate = backend_root is not None and not _same_path(backend_root, repo_root)
    tree_root = Path(backend_root) if separate else Path(repo_root)
    scanned = (["backend"] if not separate else []) + ["assets/js", "data", "experiments/waymaker-ai/waymaker_ai"]
    commit = _run([git, "-C", str(repo_root), "rev-parse", "HEAD"]) if git else None
    dirty_raw = _run([git, "-C", str(repo_root), "status", "--porcelain", "--", *scanned]) if git else None
    dirty = sorted(line[3:] for line in (dirty_raw or "").splitlines() if len(line) > 3)
    node_path = shutil.which(node) if node else None
    experiment_files = sorted({p for pattern in MEASURED_EXPERIMENT_GLOBS for p in experiment_root.glob(pattern)
                               if p.is_file() and "__pycache__" not in p.parts})
    return {
        "git_commit": commit,
        "git_dirty_paths": dirty[:200],
        "git_dirty": bool(dirty),
        "python": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "backend_python": str(backend_python),
        "backend_python_version": _run([str(backend_python), "-c", "import sys; print(sys.version.split()[0])"])
        if backend_python.is_file() else None,
        "node": node_path,
        "node_version": _run([node_path, "--version"]) if node_path else None,
        "platform": platform.platform(),
        "backend": backend_tree(tree_root, separate=separate, hash_files=hash_backend),
        "measured_files": {rel: sha256_path((tree_root if rel.startswith("backend/") else repo_root) / rel)
                           for rel in MEASURED_FILES},
        "experiment_files": {p.relative_to(experiment_root).as_posix(): sha256_path(p) for p in experiment_files},
    }


def _same_path(left: Path, right: Path) -> bool:
    try:
        return Path(left).resolve() == Path(right).resolve()
    except OSError:
        return False


#: Directory names never hashed into the backend digest: bytecode, runtime state
#: (``backend/var`` is gitignored and holds safety logs), tooling.
BACKEND_SKIPPED_DIRS = frozenset({"__pycache__", "var", "node_modules"})


def backend_tree(root: Path, *, separate: bool, hash_files: bool = True) -> Dict[str, Any]:
    """Identity of the ``backend/`` tree the subprocess baselines import.

    ``content_sha256`` is a sha256 over the sorted ``[path, sha256]`` rows of
    every regular file under ``<root>/backend``, skipping ``__pycache__``,
    ``var`` and ``node_modules`` directories, ``*.pyc`` and every dot-named file
    or directory (so a ``.env`` is never read). The same tree gives the same
    digest whether it is a checkout or a ``git archive`` extraction. When the
    root is a git work tree, the HEAD commit, the tree id of ``HEAD:backend``
    and whether ``backend/`` has uncommitted changes are recorded as well.
    """
    root = Path(root)
    backend = root / "backend"
    rows: List[Tuple[str, str]] = []
    total = 0
    if not hash_files:
        return {"root": str(root.resolve()), "separate_from_repo_root": separate, "content_sha256": None,
                "files": None, "bytes": None, "git": None,
                "not_hashed": "no baseline in this run imports the backend"}
    if backend.is_dir():
        for directory, dirnames, filenames in os.walk(backend):
            dirnames[:] = sorted(d for d in dirnames if d not in BACKEND_SKIPPED_DIRS and not d.startswith("."))
            for name in sorted(filenames):
                if name.startswith(".") or name.endswith(".pyc"):
                    continue
                path = Path(directory) / name
                rel = path.relative_to(root).as_posix()
                if path.is_symlink():
                    rows.append((rel, "symlink:" + os.readlink(path)))
                elif path.is_file():
                    rows.append((rel, sha256_path(path) or ""))
                    total += path.stat().st_size
    rows.sort()
    info: Dict[str, Any] = {
        "root": str(root.resolve()),
        "separate_from_repo_root": separate,
        "content_sha256": hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode("utf-8")).hexdigest() if rows else None,
        "files": len(rows),
        "bytes": total,
        "git": _git_tree(root),
    }
    return info


def _git_tree(root: Path) -> Optional[Dict[str, Any]]:
    """HEAD commit, ``HEAD:backend`` tree id and dirty flag, when ``root`` is the top of a git work tree."""
    git = shutil.which("git")
    if not git:
        return None
    top = _run([git, "-C", str(root), "rev-parse", "--show-toplevel"])
    if not top or not _same_path(Path(top), root):
        return None
    dirty = _run([git, "-C", str(root), "status", "--porcelain", "--", "backend"])
    return {
        "commit": _run([git, "-C", str(root), "rev-parse", "HEAD"]),
        "backend_tree": _run([git, "-C", str(root), "rev-parse", "HEAD:backend"]),
        "backend_dirty": bool(dirty),
    }


def raw_sha256(value: Any) -> Optional[str]:
    """sha256 of the canonical JSON of a baseline's raw item output (None when there is none)."""
    if value is None:
        return None
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def bounded(value: Any) -> Any:
    """Keep per-item raw output small: anything over MAX_RAW_JSON is replaced by its hash."""
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if len(text) <= MAX_RAW_JSON:
        return value
    return {"_truncated": True, "chars": len(text), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def raw_fields(value: Any, *, include: bool) -> Dict[str, Any]:
    """The per-item raw-output fields: always ``raw_sha256``; ``raw`` (bounded) only when asked for."""
    fields: Dict[str, Any] = {"raw_sha256": raw_sha256(value)}
    if include:
        fields["raw"] = bounded(value)
    return fields


RAW_PAYLOAD_POLICY_OMITTED = ("Per-item raw baseline output is omitted; each item keeps raw_sha256, the sha256 of the "
                              "canonical JSON of that output. Run with --include-raw to keep the bounded payload.")
RAW_PAYLOAD_POLICY_INCLUDED = ("Per-item raw baseline output is kept, bounded to 4,000 characters (larger payloads are "
                               "replaced by their sha256); raw_sha256 is the sha256 of the full output.")


def scoring_digest(report: Mapping[str, Any]) -> str:
    """sha256 over everything a re-run must reproduce exactly (no timings, no timestamps)."""
    items = {}
    for baseline, records in (report.get("items") or {}).items():
        items[baseline] = [
            {key: record.get(key) for key in ("id", "split", "task", "status", "prediction", "metrics", "flags",
                                              "verdict", "critical_categories")}
            for record in records
        ]
    stable = {
        "benchmark_files": (report.get("benchmark") or {}).get("files"),
        "source_bundles": report.get("source_bundles"),
        "results": report.get("results"),
        "headline": report.get("headline"),
        "headline_text_only": report.get("headline_text_only"),
        "by_adversarial_class": report.get("by_adversarial_class"),
        "critical_legal_errors": report.get("critical_legal_errors"),
        # Timing rows are machine-dependent: everything about a gate report except them.
        "gates": {name: {k: v for k, v in gate_report.items() if k != "performance_gates"}
                  for name, gate_report in (report.get("gates") or {}).items()},
        "items": items,
    }
    text = json.dumps(stable, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dumps(report: Mapping[str, Any]) -> str:
    """The report as JSON: sorted keys, indented, and one line per item record.

    ``json.loads(dumps(r)) == json.loads(json.dumps(r, default=str))`` for every
    report. Only the layout differs from a plain indented dump: each record in
    ``items[<baseline>]`` is one compact line, so a 1,000-item report is not
    30,000 lines of indentation, and a changed verdict is a one-line diff.
    """
    items = report.get("items")
    if not isinstance(items, Mapping) or not items:
        return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n"
    names = sorted(items)
    tokens = {name: f"@@waymaker-items-{index}@@" for index, name in enumerate(names)}
    shell = {key: value for key, value in report.items() if key != "items"}
    shell["items"] = {name: tokens[name] for name in names}
    text = json.dumps(shell, ensure_ascii=False, sort_keys=True, indent=2, default=str)
    for name in names:
        records = items[name] or []
        if records:
            body = ",\n".join("      " + json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
                              for record in records)
            block = "[\n" + body + "\n    ]"
        else:
            block = "[]"
        quoted_token = json.dumps(tokens[name])
        if text.count(quoted_token) != 1:   # a token can only collide with report content by design error
            raise ValueError("report serialization token collision")
        text = text.replace(quoted_token, block)
    return text + "\n"


def write_json(report: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(report), encoding="utf-8")


def compact_report(report: Mapping[str, Any], *, source_sha256: Optional[str] = None,
                   source_bytes: Optional[int] = None) -> Dict[str, Any]:
    """A report with per-item raw payloads replaced by ``raw_sha256``. Nothing else changes.

    For a payload that ``bounded`` had already replaced by its hash, that hash
    is ``raw_sha256`` (both hash the same canonical JSON). The scoring digest
    covers no raw payload, so it is unchanged; ``main`` checks that.
    """
    out = json.loads(json.dumps(report, ensure_ascii=False, default=str))
    removed = 0
    for records in (out.get("items") or {}).values():
        for record in records or []:
            if "raw" not in record:
                continue
            raw = record.pop("raw")
            removed += 1
            if "raw_sha256" not in record:
                truncated = isinstance(raw, dict) and raw.get("_truncated") is True and isinstance(raw.get("sha256"), str)
                record["raw_sha256"] = raw["sha256"] if truncated else raw_sha256(raw)
    policy = out.setdefault("policy", {})
    policy["raw_payloads"] = RAW_PAYLOAD_POLICY_OMITTED
    out["compaction"] = {
        "tool": "python -m waymaker_ai.evaluation.report compact",
        "removed_raw_payloads": removed,
        "source_sha256": source_sha256,
        "source_bytes": source_bytes,
        "scoring_digest_recomputed": scoring_digest(out),
    }
    return out


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------
def _fmt(entry: Optional[Mapping[str, Any]]) -> str:
    """``0.750 (3/4, 2 n/s) [0.301, 0.954]``: value, base, not-scorable count, 95% Wilson interval."""
    if not entry:
        return "–"
    if entry.get("baseline_cannot_emit"):
        return "not emitted"
    ns = f", {entry['not_scorable']} n/s" if entry.get("not_scorable") else ""
    if entry["kind"] == "count":
        return f"{entry['numerator']} of {entry['denominator']}{ns}"
    value = entry.get("value")
    shown = "n/a" if value is None else f"{value:.3f}"
    ci = entry.get("ci95")
    interval = f" [{ci[0]:.3f}, {ci[1]:.3f}]" if ci else ""
    return f"{shown} ({entry['numerator']}/{entry['denominator']}{ns}){interval}"


def _headline_tables(by_split: Mapping[str, Mapping[str, Any]], splits: Sequence[str], title: str) -> List[str]:
    lines: List[str] = []
    for split in splits:
        by_baseline = by_split.get(split) or {}
        lines += ["", f"## {title}: `{split}`", ""]
        names = list(by_baseline)
        metrics = sorted({metric for entries in by_baseline.values() for metric in entries})
        if not metrics:
            lines.append("No scorable items.")
            continue
        lines += _table(["metric"] + names, [[metric] + [_fmt(by_baseline[n].get(metric)) for n in names]
                                             for metric in metrics])
    return lines


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> List[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines.extend("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |" for row in rows)
    return lines


def render_markdown(report: Mapping[str, Any]) -> str:
    env = report.get("environment") or {}
    bench = report.get("benchmark") or {}
    lines: List[str] = [
        "# Waymaker evaluation report",
        "",
        f"- Report schema: `{report.get('report_schema')}`; scoring digest `{report.get('scoring_digest')}`",
        f"- Command: `{(report.get('command') or {}).get('shell')}`",
        f"- Git commit: `{env.get('git_commit')}`" + (" (working tree has changes in measured paths)" if env.get("git_dirty") else ""),
        f"- Python {env.get('python')}, backend Python {env.get('backend_python_version')}, Node {env.get('node_version')}",
        f"- Benchmark: `{bench.get('root')}` digest `{bench.get('digest')}`; manifest "
        f"{'verified' if (bench.get('manifest') or {}).get('ok') else 'NOT verified'}"
        f"; {len(bench.get('invalid_examples') or [])} invalid example(s) left out",
        f"- Label review of scored examples: {json.dumps(bench.get('label_review') or {}, sort_keys=True)}",
    ]
    dirty = env.get("git_dirty_paths") or []
    if dirty:
        shown = ", ".join(f"`{path}`" for path in dirty[:20]) + (f" and {len(dirty) - 20} more" if len(dirty) > 20 else "")
        lines.append(f"- Uncommitted changes in measured paths (scores describe the working tree, not the commit): {shown}")
    backend = env.get("backend") or {}
    if backend:
        git_info = backend.get("git") or {}
        where = "a tree separate from the repo root" if backend.get("separate_from_repo_root") else "the repo root"
        git_text = (f"; git commit `{git_info.get('commit')}`, `HEAD:backend` tree `{git_info.get('backend_tree')}`"
                    + (" (backend has uncommitted changes)" if git_info.get("backend_dirty") else "")) if git_info else ""
        lines.append(f"- Backend for b1_python, b1_python_raw and existing_law: `{backend.get('root')}` ({where}); "
                     f"content sha256 `{backend.get('content_sha256')}` over {backend.get('files')} files{git_text}")
    for manifest in (bench.get("manifest") or {}).get("manifest_files") or []:
        lines.append(f"- Manifest `{manifest['path']}` sha256 `{manifest['sha256']}`")
    for bundle in report.get("source_bundles") or []:
        lines.append(f"- Source bundle `{bundle['bundle_id']}` "
                     + (f"sha256 `{bundle['sha256']}`, provenance {bundle.get('provenance')}"
                        if "sha256" in bundle else f"NOT LOADED: {bundle.get('error')}"))
    lines += [
        "",
        "> Labels are not human-verified unless the line above says so. Source bundles are synthetic fixtures "
        "or recorded captures; no live API was called. Gates are project hypotheses. No metric uses text similarity.",
        "",
        "## Baselines",
        "",
    ]
    baselines = report.get("baselines") or {}
    lines += _table(["baseline", "kind", "available", "tasks", "note"], [
        [name, info.get("kind", ""), "yes" if info.get("available") else "no", ", ".join(info.get("tasks") or []),
         info.get("unavailable_reason") or ""]
        for name, info in baselines.items()
    ])
    by_split = report.get("headline_by_split") or {}
    splits = (report.get("policy") or {}).get("splits_scored") or sorted(by_split)
    lines += ["", "Cells: value (numerator/denominator, not-scorable items) [95% Wilson interval]. "
              "\"not emitted\" = the baseline cannot produce that field."]
    lines += _headline_tables(by_split, splits, "Results")
    text_only: Dict[str, Dict[str, Any]] = {}
    for name, per_split in (report.get("headline_text_only") or {}).items():
        for split, entries in per_split.items():
            text_only.setdefault(split, {})[name] = {k: v for k, v in entries.items() if k.startswith("classification.")}
    lines += _headline_tables(text_only, splits, "Classification, text-only items (no payload code)")
    lines += ["", "## Verdicts per adversarial class", ""]
    class_rows = []
    for name, per_split in (report.get("by_adversarial_class") or {}).items():
        for split, classes in sorted(per_split.items()):
            for cls, counts in classes.items():
                class_rows.append([name, split, cls, counts.get("correct", 0), counts.get("wrong", 0),
                                   counts.get("not_scorable", 0)])
    lines += _table(["baseline", "split", "class", "correct", "wrong", "not scorable"], class_rows) \
        if class_rows else ["None."]
    lines += ["", "## Critical legal errors", ""]
    rows = []
    for name, errors in (report.get("critical_legal_errors") or {}).items():
        rows.extend([name, e["split"], e["example_id"], e["task"], ", ".join(e["categories"])] for e in errors)
    lines += _table(["baseline", "split", "example", "task", "categories"], rows) if rows else ["None."]
    lines += ["", "## Gates (project hypotheses; decision splits only)", ""]
    for name, gate_report in (report.get("gates") or {}).items():
        lines += [f"### {name}: **{gate_report['decision']}**",
                  f"Decision splits: {', '.join(gate_report['decision_splits']) or 'none run'}; "
                  f"scored labels not human-verified: {gate_report.get('labels_unverified', 0)} "
                  f"(critical: {gate_report['critical_labels_unverified']})", ""]
        rows = list(gate_report["gates"]) + list(gate_report.get("performance_gates") or [])
        lines += _table(["gate", "hard", "metric", "rule", "result", "value", "base"], [
            [g["id"], "hard" if g["hard"] else ("timing" if g["id"].startswith("PG-") else "soft"), g["metric"],
             "= 0" if g["comparator"] == "zero" else f"{g['comparator']} {g['threshold']}", g["status"],
             "–" if g["value"] is None else g["value"], "–" if g["denominator"] is None else g["denominator"]]
            for g in rows
        ])
        lines += ["", "Timing rows (PG-*) depend on the machine; they are reported but do not enter the decision.", ""]
    lines += ["## Performance", ""]
    perf_rows = []
    for name, by_split in (report.get("performance") or {}).items():
        for split, perf in sorted(by_split.items()):
            lat, calls, mem = perf["latency_ms"], perf["upstream_calls"], perf["peak_memory_bytes"]
            tokens = perf.get("tokens")
            perf_rows.append([name, split, lat["n"], lat["p50"], lat["p95"], calls["total"], calls["max"],
                              mem["max"], "/".join(mem["kind"]) or "–",
                              json.dumps(tokens, sort_keys=True) if tokens else "–"])
    lines += _table(["baseline", "split", "items", "latency p50 ms", "latency p95 ms", "upstream calls",
                     "max calls/item", "peak memory B", "memory kind", "tokens"], perf_rows) if perf_rows else ["None."]
    lines += ["", "## Not-scorable reasons", ""]
    reason_rows = []
    for name, by_split in (report.get("not_scorable") or {}).items():
        for split, reasons in sorted(by_split.items()):
            reason_rows.extend([name, split, reason, count] for reason, count in sorted(reasons.items()))
    lines += _table(["baseline", "split", "reason", "metric outcomes"], reason_rows) if reason_rows else ["None."]
    invalid = bench.get("invalid_examples") or []
    if invalid:
        lines += ["", "## Invalid examples (not scored, not repaired)", ""]
        lines += _table(["file", "line", "id", "reason"], [[i["path"], i["line"], i.get("example_id") or "", i["reason"]]
                                                           for i in invalid])
    ledger = report.get("holdout_ledger")
    if ledger:
        lines += ["", "## Held-out ledger", "",
                  f"Prior adversarial_holdout runs for this benchmark version: {ledger['prior_runs_for_this_benchmark']}"
                  + (" (THIS RUN IS A REPEAT)" if ledger.get("repeat") else "")]
        if ledger.get("post_hoc"):
            lines += ["", f"**THIS RUN IS A POST-HOC RE-SCORING** of adversarial_holdout items already looked at "
                          f"({ledger.get('prior_ledger_entries')} earlier ledger entries under any benchmark digest). "
                          f"Reason: {ledger.get('post_hoc_reason')}. Its holdout numbers are not first-look numbers."]
    contamination = report.get("contamination")
    if contamination:
        lines += ["", "## Contamination check", "",
                  f"Exact normalized-question overlaps with training files: {contamination['overlap_count']}", ""]
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI: compact an existing report
# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m waymaker_ai.evaluation.report",
                                     description="Report utilities (offline, standard library only).")
    sub = parser.add_subparsers(dest="command", required=True)
    compact = sub.add_parser("compact", help="replace per-item raw payloads by raw_sha256; the scores must not change")
    compact.add_argument("report", type=Path, help="report JSON written by the runner")
    compact.add_argument("--out", type=Path, help="output path (default: rewrite the input)")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    data = args.report.read_bytes()
    report = json.loads(data.decode("utf-8"))
    compacted = compact_report(report, source_sha256=hashlib.sha256(data).hexdigest(), source_bytes=len(data))
    recorded = report.get("scoring_digest")
    if compacted["compaction"]["scoring_digest_recomputed"] != recorded:
        print(f"refused: the recomputed scoring digest {compacted['compaction']['scoring_digest_recomputed']} "
              f"differs from the recorded {recorded}", file=sys.stderr)
        return 1
    write_json(compacted, args.out or args.report)
    print(f"compacted {compacted['compaction']['removed_raw_payloads']} raw payload(s); scoring digest {recorded} "
          "unchanged", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
