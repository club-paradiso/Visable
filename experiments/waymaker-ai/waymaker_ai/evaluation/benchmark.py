"""Load a benchmark directory and the source bundles its examples point at.

Why the loader re-hashes everything it reads: the benchmark is governed
separately from the runner (labels, provenance, frozen splits). A report is
only meaningful if it names the exact bytes it scored, so every example file
and every source bundle is hashed, and the hashes are checked against the
benchmark manifest when the manifest lists them. The loader never edits the
benchmark and never fixes an example; a malformed example is reported and left
out of scoring, never repaired.

Layout it accepts (tolerant on purpose, because the benchmark is written by a
separate component):

* examples: every example file under the benchmark root as
  ``waymaker_ai.dataset.layout`` defines it (the rule the dataset validator
  uses too): ``*.jsonl`` files (one example per line) and ``*.json`` files
  holding a list of examples or ``{"examples": [...]}``, read in sorted path
  order, except files under hidden or evidence directories, rubrics
  (``*_rubric.json``) and files a ``MANIFEST.json`` lists under
  ``non_example_files``;
* hashed: every data file (``layout.data_files``), examples or not, so the
  digest names every byte that can change what a label means (a rubric
  included). Non-example data files are listed in ``non_example_files`` with
  the reason, never read as examples;
* manifest: ``MANIFEST.json`` (any nesting of ``{"path", "sha256"}`` objects
  or a ``{"files": {path: sha256}}`` map) and/or a text manifest
  (``MANIFEST``, ``MANIFEST.sha256``, ``SHA256SUMS``) with
  ``<sha256>  <path>`` lines. Manifest files are never read as examples.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from waymaker_ai.contracts import AnchorKind, RelevantDates, parse_date
from waymaker_ai.dataset import layout
from waymaker_ai.dataset.tasks import TASK_EXPECTED_KEYS

EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURES_DIR = EXPERIMENT_ROOT / "datasets" / "fixtures" / "sources"

#: Splits the runner may score. ``train`` is never evaluated: an example that
#: is (or was) training data says nothing about generalisation.
EVALUATION_SPLITS: Tuple[str, ...] = ("dev", "test", "adversarial_holdout")

#: One definition, shared with the dataset validator and the SFT leakage guard.
MANIFEST_NAMES = layout.MANIFEST_NAMES

_BUNDLE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,120}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class BenchmarkError(Exception):
    """The benchmark cannot be loaded as a whole (not a per-example problem)."""


@dataclass(frozen=True)
class BenchmarkFile:
    path: str          # posix path relative to the benchmark root
    sha256: str
    examples: int


@dataclass(frozen=True)
class InvalidExample:
    path: str
    line: int
    example_id: Optional[str]
    reason: str


@dataclass
class ManifestCheck:
    found: bool = False
    manifest_files: List[Dict[str, str]] = field(default_factory=list)   # [{path, sha256}] of the manifest files
    listed: int = 0
    verified: int = 0
    mismatches: List[Dict[str, str]] = field(default_factory=list)       # [{path, expected, actual|missing}]
    unlisted_example_files: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.found and not self.mismatches and self.listed > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "ok": self.ok,
            "manifest_files": list(self.manifest_files),
            "listed": self.listed,
            "verified": self.verified,
            "mismatches": list(self.mismatches),
            "unlisted_example_files": list(self.unlisted_example_files),
        }


@dataclass(frozen=True)
class NonExampleFile:
    path: str          # posix path relative to the benchmark root
    reason: str        # a waymaker_ai.dataset.layout reason


@dataclass
class Benchmark:
    root: Path
    examples: List[Dict[str, Any]]
    files: List[BenchmarkFile]
    invalid: List[InvalidExample]
    manifest: ManifestCheck
    non_example_files: List[NonExampleFile] = field(default_factory=list)

    def select(self, splits: Sequence[str]) -> List[Dict[str, Any]]:
        wanted = set(splits)
        chosen = [ex for ex in self.examples if ex.get("split") in wanted]
        return sorted(chosen, key=example_sort_key)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def example_sort_key(example: Mapping[str, Any]) -> Tuple[str, str, str]:
    split_rank = str(EVALUATION_SPLITS.index(example["split"])) if example.get("split") in EVALUATION_SPLITS else "9"
    return (split_rank, str(example.get("task") or ""), str(example.get("id") or ""))


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------
def load_benchmark(root: Path) -> Benchmark:
    root = Path(root)
    if not root.is_dir():
        raise BenchmarkError(f"benchmark directory not found: {root}")
    files: List[BenchmarkFile] = []
    examples: List[Dict[str, Any]] = []
    invalid: List[InvalidExample] = []
    seen_ids: Dict[str, str] = {}
    non_examples: List[NonExampleFile] = []
    _, skipped, _ = layout.classify(root)
    reasons = {path: reason for path, reason in skipped}
    for path in _example_files(root):
        rel = path.relative_to(root).as_posix()
        count = 0
        if path in reasons:
            # Hashed (it is part of the benchmark's bytes), never read as examples.
            non_examples.append(NonExampleFile(rel, reasons[path]))
            files.append(BenchmarkFile(rel, sha256_file(path), 0))
            continue
        for line_no, raw in _iter_raw_examples(path, invalid, rel):
            problem = example_problem(raw)
            example_id = raw.get("id") if isinstance(raw, dict) else None
            if problem is None and example_id in seen_ids:
                problem = f"duplicate id (first seen in {seen_ids[example_id]})"
            if problem is not None:
                invalid.append(InvalidExample(rel, line_no, example_id if isinstance(example_id, str) else None, problem))
                continue
            seen_ids[example_id] = rel
            examples.append(raw)
            count += 1
        files.append(BenchmarkFile(rel, sha256_file(path), count))
    manifest = check_manifest(root, files)
    return Benchmark(root=root, examples=examples, files=files, invalid=invalid, manifest=manifest,
                     non_example_files=non_examples)


def _example_files(root: Path) -> List[Path]:
    """Every data file under the root (``layout.data_files``): all of them are hashed."""
    return layout.data_files(root)


def _iter_raw_examples(path: Path, invalid: List[InvalidExample], rel: str) -> Iterable[Tuple[int, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        for line_no, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                yield line_no, json.loads(line)
            except json.JSONDecodeError as exc:
                invalid.append(InvalidExample(rel, line_no, None, f"invalid JSON: {exc.msg}"))
        return
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        invalid.append(InvalidExample(rel, 0, None, f"invalid JSON: {exc.msg}"))
        return
    data = layout.container_examples(data)
    if data is None:
        # A JSON file that is not an example container (e.g. a split index) is
        # not an error; it is simply not examples.
        return
    for index, item in enumerate(data, start=1):
        yield index, item


def example_problem(example: Any) -> Optional[str]:
    """Why an example cannot be scored, or None. Checks only what scoring needs."""
    if not isinstance(example, dict):
        return "example is not an object"
    for key in ("id", "task", "split", "input", "expected", "scenario"):
        if key not in example:
            return f"missing {key}"
    if not isinstance(example["id"], str) or not example["id"]:
        return "id must be a non-empty string"
    task = example["task"]
    if task not in TASK_EXPECTED_KEYS:
        return f"unknown task {task!r}"
    if not isinstance(example["expected"], dict) or not isinstance(example["input"], dict):
        return "input and expected must be objects"
    required, _optional = TASK_EXPECTED_KEYS[task]
    missing = sorted(required - set(example["expected"]))
    if missing:
        return f"expected is missing {', '.join(missing)}"
    if not isinstance(example["input"].get("question"), str):
        return "input.question must be a string"
    if task in ("citation_verification", "temporal_version_selection") and not example["input"].get("fixture_set"):
        return "input.fixture_set is required for this task"
    if task == "citation_verification" and not isinstance(example["input"].get("claim"), dict):
        return "input.claim is required for citation_verification"
    if task == "temporal_version_selection" and not isinstance(example["input"].get("temporal_query"), dict):
        return "input.temporal_query is required for temporal_version_selection"
    return None


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
def check_manifest(root: Path, files: Sequence[BenchmarkFile]) -> ManifestCheck:
    check = ManifestCheck()
    listed: Dict[str, str] = {}
    for name in sorted(MANIFEST_NAMES):
        path = root / name
        if not path.is_file():
            continue
        check.found = True
        check.manifest_files.append({"path": name, "sha256": sha256_file(path)})
        entries = _manifest_entries(path)
        for rel, digest in entries:
            listed.setdefault(rel, digest)
    check.listed = len(listed)
    actual = {f.path: f.sha256 for f in files}
    covered = set()
    for rel in sorted(listed):
        expected = listed[rel]
        local = _benchmark_relative(root, rel)
        target = _resolve_listed(root, rel)
        if local in actual:
            got = actual[local]
            covered.add(local)
        elif target is not None and target.is_file():
            got = sha256_file(target)
        else:
            check.mismatches.append({"path": rel, "expected": expected, "actual": "missing"})
            continue
        if got != expected:
            check.mismatches.append({"path": rel, "expected": expected, "actual": got})
        else:
            check.verified += 1
    if check.found:
        check.unlisted_example_files = sorted(p for p in actual if p not in covered)
    return check


def _benchmark_relative(root: Path, rel: str) -> str:
    """Accept manifest paths written relative to the benchmark or to the experiment root."""
    try:
        prefix = root.resolve().relative_to(EXPERIMENT_ROOT).as_posix() + "/"
    except ValueError:
        return rel
    return rel[len(prefix):] if rel.startswith(prefix) else rel


def _resolve_listed(root: Path, rel: str) -> Optional[Path]:
    """Resolve a listed path, refusing anything outside the experiment directory."""
    for base in (root, EXPERIMENT_ROOT):
        candidate = (base / rel).resolve()
        try:
            candidate.relative_to(EXPERIMENT_ROOT)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate
    return None


def _manifest_entries(path: Path) -> List[Tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        return sorted(_json_manifest_entries(data))
    entries = []
    for line in text.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and _SHA256_RE.match(parts[0].lower()):
            entries.append((parts[1].lstrip("*").strip(), parts[0].lower()))
    return entries


def _json_manifest_entries(node: Any) -> List[Tuple[str, str]]:
    found: List[Tuple[str, str]] = []
    if isinstance(node, dict):
        path, digest = node.get("path"), node.get("sha256")
        if isinstance(path, str) and isinstance(digest, str) and _SHA256_RE.match(digest.lower()):
            found.append((path, digest.lower()))
        files = node.get("files")
        if isinstance(files, dict):
            for key, value in files.items():
                if isinstance(value, dict):
                    value = value.get("sha256")
                if isinstance(value, str) and _SHA256_RE.match(value.lower()):
                    found.append((key, value.lower()))
        for key, value in node.items():
            if key == "files" and isinstance(value, dict):
                continue
            if isinstance(value, (dict, list)):
                found.extend(_json_manifest_entries(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_json_manifest_entries(item))
    return found


# ---------------------------------------------------------------------------
# Source bundles
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LoadedBundle:
    bundle_id: str
    path: Path
    sha256: str
    data: Dict[str, Any]


class BundleStore:
    """Loads ``<fixtures_dir>/<bundle_id>.json`` once and remembers its hash."""

    def __init__(self, fixtures_dir: Path = DEFAULT_FIXTURES_DIR) -> None:
        self.fixtures_dir = Path(fixtures_dir)
        self._cache: Dict[str, LoadedBundle] = {}
        self.errors: Dict[str, str] = {}

    def get(self, bundle_id: str) -> Optional[LoadedBundle]:
        if bundle_id in self._cache:
            return self._cache[bundle_id]
        if bundle_id in self.errors:
            return None
        if not isinstance(bundle_id, str) or not _BUNDLE_ID_RE.match(bundle_id):
            # A bundle id is a file name, never a path: refuse anything that
            # could walk out of the fixtures directory.
            self.errors[str(bundle_id)] = "bundle id is not a plain file name"
            return None
        path = self.fixtures_dir / f"{bundle_id}.json"
        if not path.is_file():
            self.errors[bundle_id] = f"bundle file not found: {path.name}"
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.errors[bundle_id] = f"bundle is not valid JSON: {exc.msg}"
            return None
        if not isinstance(data, dict):
            self.errors[bundle_id] = "bundle is not a JSON object"
            return None
        loaded = LoadedBundle(bundle_id, path, sha256_file(path), data)
        self._cache[bundle_id] = loaded
        return loaded

    def describe(self) -> List[Dict[str, Any]]:
        rows = []
        for bundle_id in sorted(self._cache):
            bundle = self._cache[bundle_id]
            rows.append({
                "bundle_id": bundle_id,
                "file": bundle.path.name,
                "sha256": bundle.sha256,
                "bundle_version": bundle.data.get("bundle_version"),
                "provenance": bundle.data.get("provenance"),
                "attribution": bundle.data.get("attribution"),
                "captured_at": bundle.data.get("captured_at"),
            })
        for bundle_id in sorted(self.errors):
            rows.append({"bundle_id": bundle_id, "error": self.errors[bundle_id]})
        return rows


# ---------------------------------------------------------------------------
# Example accessors shared by every baseline (the equivalent-input rule)
# ---------------------------------------------------------------------------
def question_of(example: Mapping[str, Any]) -> str:
    return str(example["input"].get("question") or "")


def payload_code_of(example: Mapping[str, Any]) -> Optional[str]:
    value = example["input"].get("payload_status_code")
    return str(value) if value else None


def relevant_dates_of(example: Mapping[str, Any]) -> RelevantDates:
    raw = (example.get("scenario") or {}).get("relevant_dates") or {}
    values: Dict[str, dt.date] = {}
    for name in RelevantDates.__dataclass_fields__:
        if raw.get(name):
            values[name] = parse_date(raw[name])
    return RelevantDates(**values)


def anchor_of(example: Mapping[str, Any]) -> Optional[AnchorKind]:
    raw = (example.get("scenario") or {}).get("anchor")
    if not raw:
        return None
    return AnchorKind(raw)


def secondary_anchors_of(example: Mapping[str, Any]) -> Tuple[AnchorKind, ...]:
    query = example["input"].get("temporal_query") or {}
    return tuple(AnchorKind(value) for value in (query.get("secondary_anchors") or []))


def reference_date_of(example: Mapping[str, Any], bundle: Optional[Mapping[str, Any]] = None) -> Optional[dt.date]:
    """The simulated "today" of an example: its question date, else the bundle capture date."""
    dates = relevant_dates_of(example)
    if dates.question_date:
        return dates.question_date
    if bundle and bundle.get("captured_at"):
        return parse_date(bundle["captured_at"])
    return None


def label_status_of(example: Mapping[str, Any]) -> str:
    return str((example.get("label_review") or {}).get("status") or "unreviewed")
