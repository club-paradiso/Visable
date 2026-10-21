"""Benchmark directory layout: which files are examples, manifests or neither.

Why one module: three components read a benchmark directory. The dataset
validator checks examples, the evaluation runner scores them, and the SFT
leakage guard compares a train split with them. When each kept its own copy of
"which files are examples", they drifted: the validator skipped evidence
directories that the runner still scored, so an example could be scored that
no rule had ever checked. All three now import the rules below, and
``tests/test_dataset_layout.py`` builds one tree with every kind of file and
checks that they agree.

Two file sets, on purpose:

* **data files** (``data_files``): every ``.json`` / ``.jsonl`` file under the
  root except manifests and dot-named files. The runner hashes all of them,
  because they are the benchmark's bytes (a rubric changes what a label means),
  and the leakage guard reads all of them by content, because a guard must read
  at least what the runner scores.
* **example files** (``example_files``): the data files the validator checks
  and the runner reads examples from. A data file is not an example file when
  it sits under a hidden or evidence directory (``NON_EXAMPLE_DIRS``), is a
  rubric (``*_rubric.json``), or is listed under ``non_example_files`` in a
  ``MANIFEST.json`` of an enclosing directory (paths relative to that
  manifest's directory).

Standard library only. Nothing here edits a file or opens a network
connection.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

#: Hash manifests that sit next to the examples and are never examples themselves.
MANIFEST_NAMES: FrozenSet[str] = frozenset({"MANIFEST", "MANIFEST.json", "MANIFEST.sha256", "SHA256SUMS", "MANIFEST.txt"})
#: The one manifest that can declare non-example files.
MANIFEST_JSON = "MANIFEST.json"
#: Key of the MANIFEST.json list of non-example files: paths relative to the manifest's directory.
NON_EXAMPLE_FILES_KEY = "non_example_files"
#: Directory names that hold evidence or configuration, not examples.
NON_EXAMPLE_DIRS: FrozenSet[str] = frozenset({"fixtures", "registry", "sources", "config", "configs", "schemas", "reports"})
#: File-name endings of files that describe examples without being examples.
NON_EXAMPLE_FILE_SUFFIXES: Tuple[str, ...] = ("_rubric.json",)
EXAMPLE_SUFFIXES: Tuple[str, ...] = (".json", ".jsonl")
#: A JSON example file holds a list of examples or {"examples": [...]}.
EXAMPLE_CONTAINER_KEY = "examples"

# Reasons a data file is not an example file (stable strings: reports print them).
REASON_HIDDEN_DIR = "hidden directory"
REASON_NON_EXAMPLE_DIR = "non-example directory"
REASON_RUBRIC = "rubric file (*_rubric.json)"
REASON_DECLARED = "declared in MANIFEST.json non_example_files"


def is_data_file(path: Path) -> bool:
    """A .json / .jsonl file that is neither a manifest nor dot-named (by name only)."""
    path = Path(path)
    return path.suffix in EXAMPLE_SUFFIXES and path.name not in MANIFEST_NAMES and not path.name.startswith(".")


def data_files(root: Path) -> List[Path]:
    """Every data file at any depth under ``root``, in sorted path order."""
    root = Path(root)
    if not root.is_dir():
        return []
    return [path for path in sorted(root.rglob("*")) if path.is_file() and is_data_file(path)]


def container_examples(data: Any) -> Optional[List[Any]]:
    """The examples a parsed JSON file holds (a list, or {"examples": [...]}), else None."""
    if isinstance(data, dict) and isinstance(data.get(EXAMPLE_CONTAINER_KEY), list):
        return list(data[EXAMPLE_CONTAINER_KEY])
    if isinstance(data, list):
        return list(data)
    return None


# ---------------------------------------------------------------------------
# MANIFEST.json non_example_files declarations
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Declaration:
    """The non_example_files of one MANIFEST.json."""

    manifest: Path
    paths: FrozenSet[str]                    # posix paths relative to the manifest's directory
    problems: Tuple[str, ...] = ()           # malformed entries (each one ignored)


def read_declaration(manifest: Path) -> Declaration:
    """Parse ``non_example_files`` from one MANIFEST.json. A malformed entry is a problem, never a guess."""
    manifest = Path(manifest)
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return Declaration(manifest, frozenset(), (f"is not readable JSON ({type(exc).__name__}), so its {NON_EXAMPLE_FILES_KEY} cannot be read",))
    if not isinstance(data, dict) or NON_EXAMPLE_FILES_KEY not in data:
        return Declaration(manifest, frozenset())
    entries = data[NON_EXAMPLE_FILES_KEY]
    if not isinstance(entries, list):
        return Declaration(manifest, frozenset(), (f"{NON_EXAMPLE_FILES_KEY} must be a list of relative paths",))
    paths: List[str] = []
    problems: List[str] = []
    for index, entry in enumerate(entries):
        raw = entry.get("path") if isinstance(entry, dict) else entry
        normalized = normalize_declared_path(raw)
        if normalized is None:
            problems.append(f"{NON_EXAMPLE_FILES_KEY}[{index}] must be a relative path inside the manifest's directory (a string, or an object with a \"path\" string)")
        else:
            paths.append(normalized)
    return Declaration(manifest, frozenset(paths), tuple(problems))


def normalize_declared_path(raw: Any) -> Optional[str]:
    """A declared path as a clean relative posix path, or None when it is not one."""
    if not isinstance(raw, str) or not raw.strip() or raw != raw.strip() or "\\" in raw:
        return None
    pure = PurePosixPath(raw)
    if pure.is_absolute() or any(part in ("..", "") for part in pure.parts):
        return None
    parts = [part for part in pure.parts if part != "."]
    return "/".join(parts) if parts else None


@dataclass
class LayoutIndex:
    """Every MANIFEST.json declaration found under one walk root."""

    root: Path
    declarations: Dict[Path, Declaration] = field(default_factory=dict)   # manifest directory -> declaration

    @classmethod
    def scan(cls, root: Path) -> "LayoutIndex":
        root = Path(root)
        index = cls(root=root)
        if root.is_dir():
            for manifest in sorted(root.rglob(MANIFEST_JSON)):
                if manifest.is_file() and not _under_hidden_dir(manifest, root):
                    index.declarations[manifest.parent] = read_declaration(manifest)
        return index

    def declared(self, path: Path) -> bool:
        """True when a MANIFEST.json in an enclosing directory (within the root) lists ``path``."""
        path = Path(path)
        for directory, declaration in self.declarations.items():
            try:
                rel = path.relative_to(directory).as_posix()
            except ValueError:
                continue
            if rel in declaration.paths:
                return True
        return False

    def missing_declarations(self) -> List[Tuple[Path, str]]:
        """(manifest, declared path) pairs that name no existing file."""
        missing = []
        for directory, declaration in sorted(self.declarations.items(), key=lambda item: item[0].as_posix()):
            for rel in sorted(declaration.paths):
                if not (directory / rel).is_file():
                    missing.append((declaration.manifest, rel))
        return missing


def _under_hidden_dir(path: Path, root: Path) -> bool:
    return any(part.startswith(".") for part in path.relative_to(root).parts[:-1])


def non_example_reason(path: Path, root: Path, index: Optional[LayoutIndex] = None) -> Optional[str]:
    """Why a data file under ``root`` is not an example file, or None when it is one.

    ``path`` must be a data file (``is_data_file``) under ``root``.
    """
    path, root = Path(path), Path(root)
    parents = path.relative_to(root).parts[:-1]
    if any(part.startswith(".") for part in parents):
        return REASON_HIDDEN_DIR
    blocked = [part for part in parents if part in NON_EXAMPLE_DIRS]
    if blocked:
        return f"{REASON_NON_EXAMPLE_DIR} {blocked[0]}/"
    if path.name.endswith(NON_EXAMPLE_FILE_SUFFIXES):
        return REASON_RUBRIC
    index = index if index is not None else LayoutIndex.scan(root)
    if index.declared(path):
        return REASON_DECLARED
    return None


def is_example_file(path: Path, root: Path, index: Optional[LayoutIndex] = None) -> bool:
    path = Path(path)
    return path.is_file() and is_data_file(path) and non_example_reason(path, root, index) is None


def classify(root: Path) -> Tuple[List[Path], List[Tuple[Path, str]], LayoutIndex]:
    """(example files, [(non-example data file, reason)], index) under ``root``, sorted."""
    root = Path(root)
    index = LayoutIndex.scan(root)
    examples: List[Path] = []
    skipped: List[Tuple[Path, str]] = []
    for path in data_files(root):
        reason = non_example_reason(path, root, index)
        if reason is None:
            examples.append(path)
        else:
            skipped.append((path, reason))
    return examples, skipped, index


def example_files(root: Path) -> List[Path]:
    """The files under ``root`` the validator checks and the runner scores, in sorted path order."""
    return classify(root)[0]


def is_declared_or_rubric(reason: Optional[str]) -> bool:
    """True for files that sit next to examples by design (a rubric or a declared file)."""
    return reason in (REASON_RUBRIC, REASON_DECLARED)
