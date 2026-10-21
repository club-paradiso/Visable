"""Deterministic validator for Waymaker benchmark and training examples.

Usage (from experiments/waymaker-ai)::

    python -m waymaker_ai.dataset.validate <files or dirs> [--registry DIR]
        [--sources DIR] [--inventory FILE] [--manual-index FILE]
        [--teacher-policy FILE] [--schema FILE] [--json OUT]

Exit status 0 means no errors (warnings may remain), 1 means at least one error,
2 means the command line or the example schema itself was unusable.

Why a validator and not a reviewer's eye: a label set for legal questions fails
in ways that look fine on screen. A subcode filed as its own parent, a law id
that points at a different version than the label assumes, a synthetic fixture
quietly backing a "human authored" example, a near-copy of a test question in
the training split. Each of those turns a benchmark score into a false claim.
Every rule below is deterministic, so two runs over the same files print the
same report, and a CI job can gate on it.

Separation of concerns (docs/ai/waymaker-genesis/11-dataset-governance.md):

* factual legal evidence lives in source bundles (datasets/fixtures/sources)
  and in the law identity registry (datasets/registry); an example only
  *references* it;
* the example carries the label, its provenance and its review state.

The validator never edits a file and never makes a network request. It reads
``visa_data.json`` and ``data/manual_approval_index.json`` read-only. It reads
example files in the shapes the benchmark loader reads (JSONL, a JSON list, or
``{"examples": [...]}``), so what passes here is what the runner scores. Every
report string goes through the personal-data redactor (``Issue.__post_init__``).
Every rule id used below is listed, with its severity, in the governance
document; tests/test_dataset_governance_doc.py fails if the two drift.
"""
from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Type
from urllib.parse import urlsplit

from waymaker_ai.contracts import (
    FINE_PROCEDURES,
    OFFICIAL_SOURCE_HOSTS,
    AnchorKind,
    ClaimVerification,
    LayerOutcome,
    LayerResult,
    LookupStatus,
    OverallStatus,
    ParseStatus,
    ProvenanceStatus,
    RelevantDates,
    SourceFamily,
    TemporalWarning,
    VerificationCode,
    VerificationLayer,
    compact,
    iter_layer_order,
    normalize_text,
    procedure_scope,
)
from waymaker_ai.dataset import layout, pii
from waymaker_ai.dataset.inventory import (
    DEFAULT_INVENTORY_PATH,
    REPO_ROOT,
    CodeInventory,
    InventoryError,
    load_inventory,
)
from waymaker_ai.dataset.schema import (
    DEFAULT_SCHEMA_PATH,
    EXPERIMENT_ROOT,
    SchemaError,
    describe_path,
    is_iso_date,
    load_schema,
    validate_instance,
)
from waymaker_ai.dataset.tasks import ADVERSARIAL_CLASSES, SCHEMA_VERSION, TASK_EXPECTED_KEYS, TASK_SUITE

REPORT_SCHEMA_VERSION = "waymaker-dataset-report/0.1"

DEFAULT_REGISTRY_DIR = EXPERIMENT_ROOT / "datasets" / "registry"
DEFAULT_SOURCES_DIR = EXPERIMENT_ROOT / "datasets" / "fixtures" / "sources"
DEFAULT_MANUAL_INDEX_PATH = REPO_ROOT / "data" / "manual_approval_index.json"
DEFAULT_TEACHER_POLICY_PATH = EXPERIMENT_ROOT / "configs" / "teacher_policy.json"

ERROR = "error"
WARNING = "warning"

#: Character-3-gram Jaccard at or above this is a near duplicate. Kept as a
#: fraction so the comparison is exact integer arithmetic, not float rounding.
CONTAMINATION_THRESHOLD = Fraction(85, 100)
EVAL_SPLITS: Tuple[str, ...] = ("dev", "test", "adversarial_holdout")
HARD_NEGATIVE_SPLITS: Tuple[str, ...] = ("test", "adversarial_holdout")

CLASSIFICATION_TASK = "status_procedure_classification"
CITATION_TASK = "citation_verification"
TEMPORAL_TASK = "temporal_version_selection"
ABSTENTION_TASK = "abstention"

#: Tasks whose answer depends on a date, so the question date must be stated.
DATED_TASKS: Tuple[str, ...] = (CITATION_TASK, TEMPORAL_TASK)
#: Tasks that are scored against a source bundle.
BUNDLE_TASKS: Tuple[str, ...] = (CITATION_TASK, TEMPORAL_TASK)

#: Mirrors backend/services/manual_registry.py DIRECT_EVIDENCE_STATES.
APPROVED_MANUAL_STATES = frozenset({"approved"})
#: Manual edition ids name their procedure scope (CLAUDE.md: never mixed).
MANUAL_SCOPE_MARKERS: Tuple[Tuple[str, str], ...] = (("visa_manual", "visa"), ("stay_manual", "stay"))

#: open.law.go.kr names omission of the source as a 저작권법 제137조/제138조 matter
#: (research-notes/official-api.md §6); every law.go.kr bundle must carry it.
LAW_GO_KR_ATTRIBUTION = "법제처 국가법령정보센터"
SYNTHETIC_FIXTURE = ProvenanceStatus.SYNTHETIC_FIXTURE.value
VERIFIED_PROVENANCE: FrozenSet[str] = frozenset({ProvenanceStatus.VERIFIED_WEB.value, ProvenanceStatus.VERIFIED_API.value})
BUNDLE_PROVENANCE: FrozenSet[str] = VERIFIED_PROVENANCE | {SYNTHETIC_FIXTURE}
#: Words that mark a synthetic law title as obviously fictional.
FICTIONAL_TITLE_MARKERS: Tuple[str, ...] = ("가상", "synthetic", "fictional")

BUNDLE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,120}\Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")

#: Which files under a directory are examples: one rule set, shared with the
#: benchmark loader and the SFT leakage guard (waymaker_ai/dataset/layout.py).
#: Re-exported under their old names for callers of this module.
NON_EXAMPLE_DIRS = layout.NON_EXAMPLE_DIRS
EXAMPLE_SUFFIXES = layout.EXAMPLE_SUFFIXES
MANIFEST_NAMES = layout.MANIFEST_NAMES
#: A JSON example file holds a list of examples or {"examples": [...]}, the two
#: shapes the benchmark loader reads. Anything else would be validated here and
#: then silently never scored, so it is not treated as an example.
EXAMPLE_CONTAINER_KEY = layout.EXAMPLE_CONTAINER_KEY

RELEVANT_DATE_KEYS: FrozenSet[str] = frozenset(f.name for f in dataclasses.fields(RelevantDates))
COUNT_FIELDS: Tuple[str, ...] = ("suite", "task", "language", "split", "adversarial_class", "label_status", "authoring")

VersionKey = Tuple[Optional[str], Optional[str]]


def _values(enum_type: Type[Enum]) -> FrozenSet[str]:
    return frozenset(member.value for member in enum_type)


ANCHOR_KINDS = _values(AnchorKind)
OVERALL_STATUSES = _values(OverallStatus)
TEMPORAL_WARNINGS = _values(TemporalWarning)
VERIFICATION_CODES = _values(VerificationCode)
VERIFICATION_LAYERS = _values(VerificationLayer)
LOOKUP_STATUSES = _values(LookupStatus)
SOURCE_FAMILIES = _values(SourceFamily)
PARSE_STATUSES = _values(ParseStatus)
PROVENANCE_STATUSES = _values(ProvenanceStatus)
PROCEDURES = frozenset(FINE_PROCEDURES)

BUNDLE_COVERAGE = frozenset({"complete", "partial"})
BUNDLE_UNIT_KINDS = frozenset({"article", "heading", "annex", "addendum"})
BUNDLE_ADDENDUM_KINDS = frozenset({"effective_date", "transitional", "application", "other"})
BUNDLE_FAULT_OPERATIONS = frozenset({"resolve_title", "list_versions", "get_provision", "get_addenda", "guidance"})
BUNDLE_RAW_BODY_KINDS = frozenset({
    "html", "empty", "malformed_json", "malformed_xml", "http_429", "timeout", "http_500", "official_error",
})
#: Top-level bundle keys and the JSON type each must have (the shared source bundle format).
BUNDLE_KEY_TYPES: Tuple[Tuple[str, Tuple[type, ...]], ...] = (
    ("bundle_id", (str,)),
    ("bundle_version", (int,)),
    ("provenance", (str,)),
    ("attribution", (str,)),
    ("captured_at", (str, type(None))),
    ("title_index_coverage", (str,)),
    ("history_coverage", (dict,)),
    ("identities", (list,)),
    ("versions", (list,)),
    ("provisions", (list,)),
    ("addenda", (list,)),
    ("guidance", (list,)),
    ("faults", (list,)),
)


# ---------------------------------------------------------------------------
# Issues and records
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Issue:
    severity: str            # ERROR or WARNING
    rule: str                # stable rule id, listed in 11-dataset-governance.md
    file: str
    ordinal: int             # line (jsonl), index (json array) or -1 (whole file)
    style: str               # "line" | "index" | "file"
    example_id: Optional[str]
    path: str
    message: str

    def __post_init__(self) -> None:
        """Every report string passes through the personal-data redactor, whatever rule built it.

        Messages already avoid echoing values (``quoted``), but an id such as
        "900101-5123456" matches the id pattern and an object key can be
        anything, and both travel into ``example_id`` and ``path``. Redacting
        here, at the one place every issue is made, keeps a report or CI log
        from becoming the leak it reports.
        """
        if self.example_id is not None:
            object.__setattr__(self, "example_id", pii.redact(self.example_id))
        object.__setattr__(self, "path", pii.redact(self.path))
        object.__setattr__(self, "message", pii.redact(self.message))

    @property
    def location(self) -> str:
        return _format_location(self.file, self.ordinal, self.style)

    def sort_key(self) -> Tuple[Any, ...]:
        return (self.file, self.ordinal, self.rule, self.path, self.message, self.severity)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "rule": self.rule,
            "location": self.location,
            "example_id": self.example_id,
            "path": self.path,
            "message": self.message,
        }

    def render(self) -> str:
        return f"{self.severity.upper():7} [{self.rule}] {self.location} {self.example_id or '-'} {describe_path(self.path)}: {self.message}"


@dataclass(frozen=True)
class Record:
    file: str
    ordinal: int
    style: str
    data: Any

    @property
    def location(self) -> str:
        return _format_location(self.file, self.ordinal, self.style)

    @property
    def example_id(self) -> Optional[str]:
        value = self.data.get("id") if isinstance(self.data, dict) else None
        return value if isinstance(value, str) else None

    @property
    def name(self) -> str:
        """How other messages refer to this record: its id, else its location."""
        return self.example_id or self.location

    def get(self, *keys: str) -> Any:
        """Nested lookup that returns None instead of raising on malformed data."""
        value: Any = self.data
        for key in keys:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    def mapping(self, *keys: str) -> Dict[str, Any]:
        """Nested lookup that returns {} unless the value is an object."""
        value = self.get(*keys)
        return value if isinstance(value, dict) else {}


def _format_location(file: str, ordinal: int, style: str) -> str:
    if style == "line":
        return f"{file}:{ordinal}"
    if style == "index":
        return f"{file}[{ordinal}]"
    return file


class Findings:
    """Collects issues for one record (or one file) with its location filled in."""

    def __init__(self, file: str, ordinal: int = -1, style: str = "file", example_id: Optional[str] = None) -> None:
        self.file = file
        self.ordinal = ordinal
        self.style = style
        self.example_id = example_id
        self.issues: List[Issue] = []

    @classmethod
    def for_record(cls, record: Record) -> "Findings":
        return cls(record.file, record.ordinal, record.style, record.example_id)

    def error(self, rule: str, path: str, message: str) -> None:
        self._add(ERROR, rule, path, message)

    def warning(self, rule: str, path: str, message: str) -> None:
        self._add(WARNING, rule, path, message)

    def _add(self, severity: str, rule: str, path: str, message: str) -> None:
        self.issues.append(Issue(severity, rule, self.file, self.ordinal, self.style, self.example_id, path, message))


def file_issue(severity: str, rule: str, file: str, message: str, path: str = "") -> Issue:
    return Issue(severity, rule, file, -1, "file", None, path, message)


def quoted(value: Any) -> str:
    """Echo a value from an example into a message, unless it looks like personal data."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if pii.scan_text(text):
        return "<value withheld: looks like personal data>"
    return json.dumps(value, ensure_ascii=False)


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _opt_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def _is_official_url(url: Any) -> bool:
    """True for an http(s) URL whose parsed host is an allowlisted official host (no userinfo)."""
    if not isinstance(url, str) or not url:
        return False
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or "@" in parts.netloc:
        return False
    return (parts.hostname or "").lower() in OFFICIAL_SOURCE_HOSTS


def _starts_with_iso_date(value: Any) -> bool:
    return isinstance(value, str) and is_iso_date(value[:10]) and (len(value) == 10 or value[10] in "T ")


def shown(path: Path) -> str:
    """A path as reports print it: relative to the working directory when inside it.

    Reports are compared across machines and CI runs, so they should not carry
    the absolute checkout location when a relative one says the same.
    """
    try:
        return Path(path).resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


# ---------------------------------------------------------------------------
# The law identity registry
# ---------------------------------------------------------------------------
@dataclass
class RegistryRecord:
    law_id: str
    titles: Tuple[str, ...]
    #: (version_id, effective_date) pairs: the record's own version, its
    #: pending_versions and any explicit versions list.
    versions: FrozenSet[VersionKey]
    files: Tuple[str, ...]


@dataclass
class Registry:
    directory: Path
    exists: bool
    records: Dict[str, RegistryRecord] = field(default_factory=dict)
    #: compact(title) -> law_id, for "a title is never an identity" hints
    title_to_id: Dict[str, str] = field(default_factory=dict)
    #: compact(title) of records without a law_id (e.g. 행정규칙 whose ID was not captured)
    unaddressable_titles: Set[str] = field(default_factory=set)
    problems: List[Tuple[str, str]] = field(default_factory=list)   # (file, message)

    def is_real_title(self, title: str) -> bool:
        key = compact(title)
        return key in self.title_to_id or key in self.unaddressable_titles


def load_registry(directory: Path) -> Registry:
    """Read every *.json file in the registry directory (a list of records or {"records": [...]}).

    Several records may share a law_id (one record per version, or a lineage
    split across files); they are merged. Records without a law_id cannot be
    cited by identity and are kept only as titles.
    """
    registry = Registry(directory=directory, exists=directory.is_dir())
    if not registry.exists:
        return registry
    for path in sorted(directory.glob("*.json")):
        try:
            data = _read_json(path)
        except (OSError, ValueError) as exc:
            registry.problems.append((shown(path), f"registry file is not valid JSON: {exc}"))
            continue
        records = data.get("records") if isinstance(data, dict) else data
        if not isinstance(records, list):
            registry.problems.append((shown(path), "registry file must be a list of records or {\"records\": [...]}"))
            continue
        for position, raw in enumerate(records):
            _add_registry_record(registry, path, position, raw)
    return registry


def _add_registry_record(registry: Registry, path: Path, position: int, raw: Any) -> None:
    if not isinstance(raw, dict):
        registry.problems.append((shown(path), f"record {position} is not an object"))
        return
    titles = _registry_titles(raw)
    law_id = _opt_str(raw.get("law_id")) or _opt_str(raw.get("stable_id"))
    if law_id is None:
        registry.unaddressable_titles.update(compact(title) for title in titles)
        return
    versions = set(_registry_versions(raw))
    existing = registry.records.get(law_id)
    if existing is not None:
        titles = tuple(dict.fromkeys(existing.titles + titles))
        versions |= existing.versions
        files = tuple(dict.fromkeys(existing.files + (path.as_posix(),)))
    else:
        files = (path.as_posix(),)
    registry.records[law_id] = RegistryRecord(law_id, titles, frozenset(versions), files)
    for title in titles:
        registry.title_to_id.setdefault(compact(title), law_id)


def _registry_titles(raw: Mapping[str, Any]) -> Tuple[str, ...]:
    titles: List[str] = []
    for key in ("title", "official_title"):
        if isinstance(raw.get(key), str) and raw[key]:
            titles.append(raw[key])
    for key in ("former_titles", "short_titles"):
        titles.extend(t for t in raw.get(key) or [] if isinstance(t, str) and t)
    return tuple(dict.fromkeys(titles))


def _registry_versions(raw: Mapping[str, Any]) -> Iterable[VersionKey]:
    candidates = [raw]
    for key in ("pending_versions", "versions"):
        candidates.extend(v for v in raw.get(key) or [] if isinstance(v, dict))
    for version in candidates:
        key = (_opt_str(version.get("version_id")), _opt_str(version.get("effective_date")))
        if key != (None, None):
            yield key


# ---------------------------------------------------------------------------
# Source bundles
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BundleInfo:
    """What the example rules need to know about one source bundle."""

    bundle_id: str
    path: str
    provenance: Optional[str]
    identities: FrozenSet[str]                        # stable ids
    versions: Mapping[str, FrozenSet[VersionKey]]     # stable_id -> version keys
    provisions: Mapping[VersionKey, FrozenSet[str]]   # version key -> provision keys (heading units excluded)
    #: stable ids whose list_versions lookup is faulted with a failure status; "*" = every identity
    history_failures: FrozenSet[str]
    problems: Tuple[str, ...]
    notices: Tuple[str, ...] = ()                     # bundle-level warnings

    @property
    def is_synthetic(self) -> bool:
        return self.provenance == SYNTHETIC_FIXTURE

    def all_version_keys(self) -> FrozenSet[VersionKey]:
        keys: Set[VersionKey] = set()
        for stable_keys in self.versions.values():
            keys |= stable_keys
        return frozenset(keys)

    def history_unavailable(self, stable_id: str) -> bool:
        return "*" in self.history_failures or stable_id in self.history_failures


def load_bundle(sources_dir: Path, bundle_id: str, registry: Registry) -> Optional[BundleInfo]:
    """Load one bundle. None when the file does not exist."""
    path = sources_dir / f"{bundle_id}.json"
    if not path.is_file():
        return None
    try:
        data = _read_json(path)
    except (OSError, ValueError) as exc:
        return _broken_bundle(bundle_id, path, f"bundle is not valid JSON: {exc}")
    return summarize_bundle(bundle_id, shown(path), data, registry)


def _broken_bundle(bundle_id: str, path: Path, problem: str) -> BundleInfo:
    return BundleInfo(bundle_id, shown(path), None, frozenset(), {}, {}, frozenset(), (problem,))


def summarize_bundle(bundle_id: str, path: str, data: Any, registry: Registry) -> BundleInfo:
    """Index a bundle and list its problems. Separate from loading so tests can pass a dict."""
    if not isinstance(data, dict):
        return BundleInfo(bundle_id, path, None, frozenset(), {}, {}, frozenset(), ("bundle must be a JSON object",))
    problems: List[str] = _bundle_shape_problems(data, bundle_id)
    identities = _objects(data.get("identities"))
    stable_ids = frozenset(i["stable_id"] for i in identities if isinstance(i.get("stable_id"), str))
    versions, version_problems = _index_versions(_objects(data.get("versions")), stable_ids)
    provisions, provision_problems = _index_provisions(_objects(data.get("provisions")), versions)
    history_failures, fault_problems = _index_faults(_objects(data.get("faults")))
    problems += version_problems + provision_problems + fault_problems
    problems += _identity_problems(identities)
    problems += _addendum_problems(_objects(data.get("addenda")), versions)
    provenance = data.get("provenance") if isinstance(data.get("provenance"), str) else None
    notices: List[str] = []
    if provenance == SYNTHETIC_FIXTURE:
        problems += _synthetic_bundle_problems(data, identities, registry, notices)
    elif provenance in VERIFIED_PROVENANCE:
        problems += _verified_bundle_problems(data)
    for where, finding in pii.scan_value(data):
        problems.append(f"personal data in the bundle at {where}: {pii.describe(finding)}")
    return BundleInfo(
        bundle_id=bundle_id,
        path=path,
        provenance=provenance,
        identities=stable_ids,
        versions={k: frozenset(v) for k, v in versions.items()},
        provisions={k: frozenset(v) for k, v in provisions.items()},
        history_failures=history_failures,
        problems=tuple(problems),
        notices=tuple(notices),
    )


def _objects(value: Any) -> List[Dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _bundle_shape_problems(data: Mapping[str, Any], bundle_id: str) -> List[str]:
    problems: List[str] = []
    for key, types in BUNDLE_KEY_TYPES:
        if key not in data:
            problems.append(f"missing key {key!r} (source bundle format)")
        elif not isinstance(data[key], types) or (int in types and isinstance(data[key], bool)):
            problems.append(f"{key} has the wrong type")
    if isinstance(data.get("bundle_id"), str) and data["bundle_id"] != bundle_id:
        problems.append(f"bundle_id {data['bundle_id']!r} does not match the file name {bundle_id!r}")
    if isinstance(data.get("bundle_version"), int) and data["bundle_version"] < 1:
        problems.append("bundle_version must be >= 1")
    if "provenance" in data and data.get("provenance") not in BUNDLE_PROVENANCE:
        problems.append(f"provenance must be one of {sorted(BUNDLE_PROVENANCE)}, got {data.get('provenance')!r}")
    if isinstance(data.get("attribution"), str) and not data["attribution"].strip():
        problems.append("attribution must not be empty")
    if isinstance(data.get("captured_at"), str) and not is_iso_date(data["captured_at"]):
        problems.append("captured_at must be YYYY-MM-DD or null")
    if "title_index_coverage" in data and data.get("title_index_coverage") not in BUNDLE_COVERAGE:
        problems.append("title_index_coverage must be \"complete\" or \"partial\"")
    coverage_by_id = data.get("history_coverage") if isinstance(data.get("history_coverage"), dict) else {}
    for stable_id in sorted(coverage_by_id):
        if coverage_by_id[stable_id] not in BUNDLE_COVERAGE:
            problems.append(f"history_coverage.{stable_id} must be \"complete\" or \"partial\"")
    return problems


def _identity_problems(identities: List[Dict[str, Any]]) -> List[str]:
    problems: List[str] = []
    seen: Set[str] = set()
    for index, identity in enumerate(identities):
        stable_id = identity.get("stable_id")
        if not isinstance(stable_id, str) or not stable_id:
            problems.append(f"identities[{index}] has no stable_id")
            continue
        if stable_id in seen:
            problems.append(f"identities[{index}]: duplicate stable_id {stable_id!r}")
        seen.add(stable_id)
        if not isinstance(identity.get("official_title"), str) or not identity["official_title"]:
            problems.append(f"identities[{index}] ({stable_id}) has no official_title")
        if identity.get("family") not in SOURCE_FAMILIES:
            problems.append(f"identities[{index}] ({stable_id}): family {identity.get('family')!r} is not a contracts.SourceFamily value")
    return problems


def _index_versions(
    versions: List[Dict[str, Any]], stable_ids: FrozenSet[str]
) -> Tuple[Dict[str, Set[VersionKey]], List[str]]:
    index: Dict[str, Set[VersionKey]] = {}
    problems: List[str] = []
    for position, version in enumerate(versions):
        where = f"versions[{position}]"
        stable_id = version.get("stable_id")
        key = (_opt_str(version.get("version_id")), version.get("effective_date"))
        if stable_id not in stable_ids:
            problems.append(f"{where}: stable_id {stable_id!r} is not one of the bundle identities")
            continue
        if key[0] is None:
            problems.append(f"{where}: version_id is required")
            continue
        if key[1] is not None and not is_iso_date(key[1]):
            problems.append(f"{where}: effective_date must be YYYY-MM-DD or null")
            continue
        if key in index.get(stable_id, set()):
            problems.append(f"{where}: duplicate version [{key[0]}, {key[1]}] for {stable_id}")
        index.setdefault(stable_id, set()).add(key)
        if version.get("parse_status") not in PARSE_STATUSES:
            problems.append(f"{where}: parse_status {version.get('parse_status')!r} is not a contracts.ParseStatus value")
        if version.get("provenance") not in PROVENANCE_STATUSES:
            problems.append(f"{where}: provenance {version.get('provenance')!r} is not a contracts.ProvenanceStatus value")
    return index, problems


def _index_provisions(
    provisions: List[Dict[str, Any]], versions: Mapping[str, Set[VersionKey]]
) -> Tuple[Dict[VersionKey, Set[str]], List[str]]:
    index: Dict[VersionKey, Set[str]] = {}
    problems: List[str] = []
    evidence_ids: Set[str] = set()
    for position, provision in enumerate(provisions):
        where = f"provisions[{position}]"
        evidence_id = provision.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            problems.append(f"{where}: evidence_id is required")
        elif provision.get("unit_kind") == "heading":
            # Same rule as the fixture adapter (legal/adapters.py): a heading unit
            # is never returned, so its id names no evidence. The official JSON
            # puts a chapter and a section heading on one article number (제4장
            # and 제1절 both before 난민법 제30조), so ids built from the number
            # collide; that is the source's shape, not a bundle defect.
            pass
        elif evidence_id in evidence_ids:
            problems.append(f"{where}: duplicate evidence_id {evidence_id!r}")
        else:
            evidence_ids.add(evidence_id)
        key = (_opt_str(provision.get("version_id")), provision.get("effective_date"))
        if key not in versions.get(str(provision.get("stable_id")), set()):
            problems.append(f"{where}: no version [{key[0]}, {key[1]}] of {provision.get('stable_id')!r} in the bundle")
            continue
        unit_kind = provision.get("unit_kind")
        if unit_kind not in BUNDLE_UNIT_KINDS:
            problems.append(f"{where}: unit_kind {unit_kind!r} is not one of {sorted(BUNDLE_UNIT_KINDS)}")
        if not isinstance(provision.get("provision_key"), str) or not provision["provision_key"]:
            problems.append(f"{where}: provision_key is required")
            continue
        if unit_kind != "heading":   # heading units exist only to prove adapters filter them out
            index.setdefault(key, set()).add(provision["provision_key"])
    return index, problems


def _addendum_problems(addenda: List[Dict[str, Any]], versions: Mapping[str, Set[VersionKey]]) -> List[str]:
    problems: List[str] = []
    for position, addendum in enumerate(addenda):
        key = (_opt_str(addendum.get("version_id")), addendum.get("effective_date"))
        if key not in versions.get(str(addendum.get("stable_id")), set()):
            problems.append(f"addenda[{position}]: no version [{key[0]}, {key[1]}] of {addendum.get('stable_id')!r} in the bundle")
        if addendum.get("kind") not in BUNDLE_ADDENDUM_KINDS:
            problems.append(f"addenda[{position}]: kind {addendum.get('kind')!r} is not one of {sorted(BUNDLE_ADDENDUM_KINDS)}")
    return problems


def _index_faults(faults: List[Dict[str, Any]]) -> Tuple[FrozenSet[str], List[str]]:
    failures: Set[str] = set()
    problems: List[str] = []
    for position, fault in enumerate(faults):
        where = f"faults[{position}]"
        operation, status = fault.get("operation"), fault.get("status")
        if operation not in BUNDLE_FAULT_OPERATIONS:
            problems.append(f"{where}: operation {operation!r} is not one of {sorted(BUNDLE_FAULT_OPERATIONS)}")
        if status not in LOOKUP_STATUSES:
            problems.append(f"{where}: status {status!r} is not a contracts.LookupStatus value")
            continue
        if fault.get("raw_body_kind") is not None and fault.get("raw_body_kind") not in BUNDLE_RAW_BODY_KINDS:
            problems.append(f"{where}: raw_body_kind {fault.get('raw_body_kind')!r} is not one of {sorted(BUNDLE_RAW_BODY_KINDS)}")
        if operation == "list_versions" and LookupStatus(status).is_failure:
            match = fault.get("match") if isinstance(fault.get("match"), dict) else {}
            failures.add(match["stable_id"] if isinstance(match.get("stable_id"), str) else "*")
    return frozenset(failures), problems


def _record_provenances(data: Mapping[str, Any]) -> List[str]:
    return sorted({
        str(item.get("provenance"))
        for key in ("versions", "provisions")
        for item in _objects(data.get(key))
        if item.get("provenance") is not None
    })


def _official_urls(data: Mapping[str, Any]) -> List[str]:
    return [
        str(item.get("official_url"))
        for key in ("versions", "provisions")
        for item in _objects(data.get(key))
        if _is_official_url(item.get("official_url"))
    ]


def _identity_titles(identity: Mapping[str, Any]) -> List[str]:
    titles = [identity.get("official_title")] + list(identity.get("former_titles") or []) + list(identity.get("short_titles") or [])
    return [title for title in titles if isinstance(title, str) and title]


def _synthetic_bundle_problems(
    data: Mapping[str, Any], identities: List[Dict[str, Any]], registry: Registry, notices: List[str]
) -> List[str]:
    """Synthetic text must never sit next to a real law id, a real title or an official URL."""
    problems: List[str] = []
    foreign = [p for p in _record_provenances(data) if p != SYNTHETIC_FIXTURE]
    if foreign:
        problems.append(f"synthetic_fixture bundle contains records with provenance {foreign}")
    if _official_urls(data):
        problems.append("synthetic_fixture bundle carries official law URLs; a fictional record must not point at a real source")
    for identity in identities:
        stable_id = identity.get("stable_id")
        if isinstance(stable_id, str) and stable_id in registry.records:
            problems.append(f"synthetic_fixture bundle reuses the real law id {stable_id!r} from the registry")
        elif isinstance(stable_id, str) and stable_id.isdigit():
            problems.append(f"synthetic stable_id {stable_id!r} is shaped like a real 법령ID/행정규칙ID; use a prefix such as SYN-")
        if "law.go.kr" in str(identity.get("provider") or ""):
            problems.append(f"synthetic identity {stable_id!r} names law.go.kr as its provider")
        for title in _identity_titles(identity):
            if registry.is_real_title(title):
                problems.append(f"synthetic_fixture bundle reuses the real law title {title!r}; use an obviously fictional name")
            elif not any(marker in title.casefold() for marker in FICTIONAL_TITLE_MARKERS):
                notices.append(f"synthetic law title {title!r} carries no fictional marker ({', '.join(FICTIONAL_TITLE_MARKERS)})")
    return problems


def _verified_bundle_problems(data: Mapping[str, Any]) -> List[str]:
    """Real evidence must be attributed and traceable to a recorded capture."""
    problems: List[str] = []
    record_provenance = _record_provenances(data)
    if SYNTHETIC_FIXTURE in record_provenance:
        problems.append("a bundle of real evidence contains synthetic_fixture records; synthetic text must never sit next to a real law id")
    unverified = [p for p in record_provenance if p not in VERIFIED_PROVENANCE and p != SYNTHETIC_FIXTURE]
    if unverified:
        problems.append(f"a verified bundle contains records with provenance {unverified}")
    if not is_iso_date(data.get("captured_at")):
        problems.append("captured_at must be the capture date (YYYY-MM-DD) for verified evidence")
    if _mentions_law_go_kr(data) and LAW_GO_KR_ATTRIBUTION not in str(data.get("attribution") or ""):
        problems.append(f"law.go.kr evidence must carry the attribution \"출처: {LAW_GO_KR_ATTRIBUTION} (law.go.kr)\"")
    capture_problems, has_capture_list = _capture_list_problems(data)
    problems += capture_problems
    for position, version in enumerate(_objects(data.get("versions"))):
        where = f"versions[{position}]"
        if not _is_official_url(version.get("official_url")):
            problems.append(f"{where}: official_url must point at an official host ({', '.join(sorted(OFFICIAL_SOURCE_HOSTS))})")
        if not _starts_with_iso_date(version.get("retrieved_at")):
            problems.append(f"{where}: retrieved_at must record when the capture was made (ISO date or timestamp)")
        sha = version.get("content_sha256")
        if sha is None and not has_capture_list:
            problems.append(f"{where}: content_sha256 is null and the bundle has no captures list; record the sha256 of the capture file")
        elif sha is not None and not (isinstance(sha, str) and SHA256_PATTERN.match(sha)):
            problems.append(f"{where}: content_sha256 must be the lowercase sha256 of the capture file")
    for position, provision in enumerate(_objects(data.get("provisions"))):
        url = provision.get("official_url")
        if url is not None and not _is_official_url(url):
            problems.append(f"provisions[{position}]: official_url must point at an official host")
    return problems


def _capture_list_problems(data: Mapping[str, Any]) -> Tuple[List[str], bool]:
    """A bundle may record its raw captures once, at bundle level, instead of per version.

    Then a history row that was listed but never parsed carries
    ``content_sha256: null`` and is traced through ``captures`` (each entry: a
    file or url plus the sha256 of the bytes that were read).
    """
    captures = data.get("captures")
    if captures is None:
        return [], False
    if not isinstance(captures, list) or not captures:
        return ["captures must be a non-empty list when present"], False
    problems: List[str] = []
    for position, capture in enumerate(captures):
        if not isinstance(capture, dict):
            problems.append(f"captures[{position}] must be an object")
            continue
        if not (isinstance(capture.get("sha256"), str) and SHA256_PATTERN.match(capture["sha256"])):
            problems.append(f"captures[{position}]: sha256 must be the lowercase sha256 of the capture file")
        if not (_opt_str(capture.get("file")) or _opt_str(capture.get("url"))):
            problems.append(f"captures[{position}]: name the capture file or url")
    return problems, not problems


def _mentions_law_go_kr(data: Mapping[str, Any]) -> bool:
    for identity in _objects(data.get("identities")):
        if "law.go.kr" in str(identity.get("provider") or ""):
            return True
    return any("law.go.kr" in (urlsplit(url).hostname or "") for url in _official_urls(data))


# ---------------------------------------------------------------------------
# The manual approval index
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ManualEdition:
    state: str                      # approval_state, normalized like manual_registry.py
    effective_date: Optional[str]


def load_manual_index(path: Path) -> Tuple[Dict[str, ManualEdition], Optional[str]]:
    """edition id -> ManualEdition, from data/manual_approval_index.json (read-only)."""
    try:
        data = _read_json(path)
    except FileNotFoundError:
        return {}, f"manual approval index not found: {shown(path)}"
    except (OSError, ValueError) as exc:
        return {}, f"manual approval index is not valid JSON: {exc}"
    documents = data.get("documents") if isinstance(data, dict) else None
    if not isinstance(documents, dict):
        return {}, "manual approval index has no documents object"
    editions = {
        edition: ManualEdition(
            state=str(entry.get("approval_state") or "").strip().lower(),
            effective_date=_opt_str(entry.get("effective_date")),
        )
        for edition, entry in documents.items()
        if isinstance(entry, dict)
    }
    return editions, None


def manual_scope(edition: str) -> Optional[str]:
    """'visa' or 'stay' when the edition id names its manual, else None."""
    for marker, scope in MANUAL_SCOPE_MARKERS:
        if marker in edition:
            return scope
    return None


# ---------------------------------------------------------------------------
# Options and shared resources
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Options:
    registry_dir: Path = DEFAULT_REGISTRY_DIR
    sources_dir: Path = DEFAULT_SOURCES_DIR
    inventory_path: Path = DEFAULT_INVENTORY_PATH
    manual_index_path: Path = DEFAULT_MANUAL_INDEX_PATH
    teacher_policy_path: Path = DEFAULT_TEACHER_POLICY_PATH
    schema_path: Path = DEFAULT_SCHEMA_PATH


class Resources:
    """Everything the per-record rules look up, loaded once per run."""

    def __init__(self, options: Options) -> None:
        self.options = options
        self.file_issues: List[Issue] = []
        self.inventory = self._load_inventory()
        self.registry = load_registry(options.registry_dir)
        self.manual_editions, self.manual_problem = load_manual_index(options.manual_index_path)
        self._bundles: Dict[str, Optional[BundleInfo]] = {}
        self._teacher: Optional[Tuple[Any, Optional[str]]] = None
        for file, message in self.registry.problems:
            self.file_issues.append(file_issue(ERROR, "registry", file, message))

    def _load_inventory(self) -> Optional[CodeInventory]:
        try:
            return load_inventory(self.options.inventory_path)
        except InventoryError as exc:
            self.file_issues.append(file_issue(ERROR, "inventory", shown(self.options.inventory_path), str(exc)))
            return None

    def bundle(self, bundle_id: str) -> Optional[BundleInfo]:
        """The bundle with this id (loaded once; its problems are reported once, at file level)."""
        if bundle_id not in self._bundles:
            self.add_bundle(bundle_id, load_bundle(self.options.sources_dir, bundle_id, self.registry))
        return self._bundles[bundle_id]

    def add_bundle(self, bundle_id: str, info: Optional[BundleInfo]) -> None:
        self._bundles[bundle_id] = info
        if info is None:
            return
        for problem in info.problems:
            self.file_issues.append(file_issue(ERROR, "source_bundle", info.path, problem))
        for notice in info.notices:
            self.file_issues.append(file_issue(WARNING, "source_bundle", info.path, notice))

    def teacher_policy(self) -> Tuple[Any, Optional[str]]:
        """(policy, problem). Loaded lazily: only teacher_generated examples need it."""
        if self._teacher is None:
            self._teacher = _load_teacher_policy(self.options.teacher_policy_path)
        return self._teacher


def _load_teacher_policy(path: Path) -> Tuple[Any, Optional[str]]:
    """Reuse the distillation policy loader, so the dataset and the distillation gate read one rule set.

    Imported here, not at module level: only teacher_generated examples need it,
    and a dataset without teacher output must stay checkable on its own.
    """
    if not path.is_file():
        return None, f"teacher policy missing: {shown(path)} does not exist, so no teacher output may be used"
    try:
        from waymaker_ai.distillation.teacher_policy import PolicyError, load_policy
    except ImportError as exc:
        return None, f"teacher policy unreadable: the policy loader cannot be imported ({exc})"
    try:
        return load_policy(path), None
    except PolicyError as exc:
        return None, f"teacher policy invalid: {'; '.join(exc.problems)}"
    except (OSError, ValueError) as exc:
        return None, f"teacher policy unreadable: {exc}"


# ---------------------------------------------------------------------------
# Reading example files
# ---------------------------------------------------------------------------
def discover(paths: Sequence[Path]) -> Tuple[List[Path], List[Issue]]:
    """Expand directories into example files, sorted; report paths that do not exist.

    Which files under a directory are examples is decided by
    ``waymaker_ai.dataset.layout``, the rule the benchmark loader uses too. A
    file named on the command line is always read as an example file.
    """
    files: Dict[str, Path] = {}
    issues: List[Issue] = []
    for given in paths:
        if given.is_dir():
            examples, skipped, index = layout.classify(given)
            for candidate in examples:
                files.setdefault(str(candidate.resolve()), candidate)
            issues.extend(layout_issues(skipped, index))
        elif given.is_file():
            files.setdefault(str(given.resolve()), given)
        else:
            issues.append(file_issue(ERROR, "parse", given.as_posix(), "path does not exist"))
    # A directory given twice, or together with one of its subdirectories, is
    # walked twice: report each layout problem once.
    issues = list(dict.fromkeys(issues))
    ordered = sorted(files.values(), key=lambda p: p.as_posix())
    if not ordered and not issues:
        issues.append(file_issue(ERROR, "parse", ",".join(p.as_posix() for p in paths), "no example files found"))
    return ordered, issues


def _is_example_file(candidate: Path, root: Path) -> bool:
    """Kept for callers of this module; the rule lives in waymaker_ai.dataset.layout."""
    return layout.is_example_file(candidate, root)


def layout_issues(skipped: Sequence[Tuple[Path, str]], index: layout.LayoutIndex) -> List[Issue]:
    """Problems with how a directory declares its non-example files (rule ``layout``).

    A rubric or a declared non-example file is neither validated nor scored,
    so one that holds example records would hide them from both: an error. A
    malformed declaration is an error; a declaration naming no file is a
    warning (stale, but it hides nothing).
    """
    issues: List[Issue] = []
    for declaration in sorted(index.declarations.values(), key=lambda d: d.manifest.as_posix()):
        for problem in declaration.problems:
            issues.append(file_issue(ERROR, "layout", declaration.manifest.as_posix(), problem, layout.NON_EXAMPLE_FILES_KEY))
    for manifest, rel in index.missing_declarations():
        issues.append(file_issue(WARNING, "layout", manifest.as_posix(), f"declares {quoted(rel)} as a non-example file, but no such file exists", layout.NON_EXAMPLE_FILES_KEY))
    for path, reason in skipped:
        if not layout.is_declared_or_rubric(reason):
            continue
        count = _example_like_records(path)
        if count:
            issues.append(file_issue(
                ERROR, "layout", path.as_posix(),
                f"is a non-example file ({reason}) but holds {count} example record(s) (objects with id and task); "
                "they would be neither validated nor scored: move them to an example file",
            ))
    return issues


def _example_like_records(path: Path) -> int:
    """How many objects with both ``id`` and ``task`` a (non-example) data file holds; 0 if unreadable."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    if path.suffix == ".jsonl":
        values: List[Any] = []
        for line in text.splitlines():
            try:
                values.append(json.loads(line))
            except ValueError:
                continue
    else:
        try:
            values = layout.container_examples(json.loads(text)) or []
        except ValueError:
            return 0
    return sum(1 for value in values if isinstance(value, dict) and "id" in value and "task" in value)


def load_records(files: Sequence[Path], explicit: Iterable[Path] = ()) -> Tuple[List[Record], List[Issue]]:
    """Read every example in ``files``.

    ``explicit`` names the files given on the command line (as opposed to found
    by walking a directory). A JSON file that is not an example container is an
    error when it was named explicitly and a skipped-file warning when it was
    only found next to examples, where a split index or note may legitimately
    live (the benchmark loader skips it too).
    """
    named = {str(Path(path).resolve()) for path in explicit}
    records: List[Record] = []
    issues: List[Issue] = []
    for path in files:
        name = path.as_posix()
        if path.suffix == ".jsonl":
            _load_jsonl(path, name, records, issues)
        else:
            _load_json(path, name, records, issues, explicit=str(path.resolve()) in named)
    return records, issues


def _load_jsonl(path: Path, name: str, records: List[Record], issues: List[Issue]) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        issues.append(file_issue(ERROR, "parse", name, f"cannot read file: {exc}"))
        return
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            records.append(Record(name, number, "line", _loads(line)))
        except ValueError as exc:
            issues.append(Issue(ERROR, "parse", name, number, "line", None, "", f"invalid JSON: {exc}"))


def _load_json(path: Path, name: str, records: List[Record], issues: List[Issue], *, explicit: bool = True) -> None:
    try:
        data = _read_json(path)
    except (OSError, ValueError) as exc:
        issues.append(file_issue(ERROR, "parse", name, f"invalid JSON: {exc}"))
        return
    examples = layout.container_examples(data)
    if examples is not None:
        records.extend(Record(name, index, "index", item) for index, item in enumerate(examples))
        return
    message = (
        "is not an example container: a JSON example file holds a list of examples or "
        "{\"examples\": [...]} (the shapes the benchmark loader reads)"
    )
    if explicit:
        issues.append(file_issue(ERROR, "parse", name, message))
    else:
        issues.append(file_issue(WARNING, "parse", name, message + "; skipped"))


def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return _loads(handle.read())


def _loads(text: str) -> Any:
    """json.loads that rejects duplicate keys and NaN/Infinity, which make a label ambiguous."""
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant)


def _reject_duplicate_keys(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _reject_constant(name: str) -> Any:
    raise ValueError(f"{name} is not valid JSON")


# ---------------------------------------------------------------------------
# Per-record rules
# ---------------------------------------------------------------------------
Rule = Callable[[Record, Findings, Resources], None]


def check_record(record: Record, schema: Mapping[str, Any], resources: Resources) -> List[Issue]:
    out = Findings.for_record(record)
    if not isinstance(record.data, dict):
        out.error("parse", "", "an example must be a JSON object")
        return out.issues
    for violation in validate_instance(record.data, schema):
        out.error("schema", violation.path, violation.message)
    for rule in RECORD_RULES:
        rule(record, out, resources)
    return out.issues


def rule_suite_matches_task(record: Record, out: Findings, resources: Resources) -> None:
    task, suite = record.get("task"), record.get("suite")
    if task in TASK_SUITE and isinstance(suite, str) and TASK_SUITE[task] != suite:
        out.error("suite_task", "suite", f"task {task} belongs to suite {TASK_SUITE[task]}, not {suite}")


def rule_expected_keys(record: Record, out: Findings, resources: Resources) -> None:
    task, expected = record.get("task"), record.get("expected")
    if task not in TASK_EXPECTED_KEYS or not isinstance(expected, dict):
        return
    required, optional = TASK_EXPECTED_KEYS[task]
    for key in sorted(required - set(expected)):
        out.error("expected_keys", f"expected.{key}", f"is required for task {task}")
    for key in sorted(set(expected) - required - optional):
        out.error("expected_keys", f"expected.{key}", f"is not an expected key of task {task} (allowed: {', '.join(sorted(required | optional))})")
    EXPECTED_VALUE_CHECKS[task](expected, out)


# -- expected value checks per task -----------------------------------------
def _check_optional_string(expected: Mapping[str, Any], key: str, out: Findings) -> None:
    if key in expected and expected[key] is not None and not isinstance(expected[key], str):
        out.error("expected_value", f"expected.{key}", "must be a string or null")


def _check_bool(container: Mapping[str, Any], key: str, out: Findings, prefix: str = "expected", rule: str = "expected_value") -> None:
    if key in container and not isinstance(container[key], bool):
        out.error(rule, f"{prefix}.{key}", "must be true or false")


def _check_string_list(container: Mapping[str, Any], key: str, out: Findings, prefix: str = "expected", rule: str = "expected_value") -> None:
    if key in container and not _is_string_list(container[key]):
        out.error(rule, f"{prefix}.{key}", "must be a list of strings")


def _check_enum_list(
    container: Mapping[str, Any], key: str, allowed: FrozenSet[str], what: str, out: Findings,
    prefix: str = "expected", rule: str = "expected_value",
) -> None:
    if key not in container:
        return
    value = container[key]
    if not _is_string_list(value):
        out.error(rule, f"{prefix}.{key}", f"must be a list of {what} values")
        return
    for index, item in enumerate(value):
        if item not in allowed:
            out.error(rule, f"{prefix}.{key}[{index}]", f"{quoted(item)} is not a {what} value")


def _check_classification(expected: Mapping[str, Any], out: Findings) -> None:
    for key in ("status_code", "subcode", "current_status", "target_status"):
        _check_optional_string(expected, key, out)
    procedure = expected.get("procedure")
    if procedure is not None and procedure not in PROCEDURES:
        out.error("expected_value", "expected.procedure", f"{quoted(procedure)} is not one of contracts.FINE_PROCEDURES")
    _check_bool(expected, "needs_clarification", out)
    _check_string_list(expected, "not_status_tokens", out)


def _check_extraction(expected: Mapping[str, Any], out: Findings) -> None:
    dates = expected.get("dates")
    if "dates" in expected and not isinstance(dates, list):
        out.error("expected_value", "expected.dates", "must be a list of {value, role} objects")
    for index, item in enumerate(dates if isinstance(dates, list) else []):
        path = f"expected.dates[{index}]"
        if not isinstance(item, dict):
            out.error("expected_value", path, "must be an object {value, role}")
            continue
        if not is_iso_date(item.get("value")):
            out.error("expected_value", f"{path}.value", "must be a date written YYYY-MM-DD")
        if item.get("role") not in ANCHOR_KINDS:
            out.error("expected_value", f"{path}.role", f"{quoted(item.get('role'))} is not a contracts.AnchorKind value")
    _check_string_list(expected, "status_codes", out)


def _check_citation(expected: Mapping[str, Any], out: Findings) -> None:
    if "overall" in expected and expected["overall"] not in OVERALL_STATUSES:
        out.error("expected_value", "expected.overall", f"{quoted(expected['overall'])} is not a contracts.OverallStatus value")
    layer_codes = expected.get("layer_codes")
    if "layer_codes" in expected and not isinstance(layer_codes, dict):
        out.error("expected_value", "expected.layer_codes", "must be an object {layer: code}")
        layer_codes = None
    for layer, code in sorted((layer_codes or {}).items()):
        if layer not in VERIFICATION_LAYERS:
            out.error("expected_value", f"expected.layer_codes.{layer}", "is not a contracts.VerificationLayer value")
        if code not in VERIFICATION_CODES:
            out.error("expected_value", f"expected.layer_codes.{layer}", f"{quoted(code)} is not a contracts.VerificationCode value")
    _check_enum_list(expected, "forbidden_codes", VERIFICATION_CODES, "contracts.VerificationCode", out)
    forbidden = set(expected["forbidden_codes"]) if _is_string_list(expected.get("forbidden_codes")) else set()
    for layer, code in sorted((layer_codes or {}).items()):
        if code in forbidden:
            out.error("expected_value", f"expected.layer_codes.{layer}", f"{quoted(code)} is both expected and forbidden")
    highest = expected.get("max_highest_verified_layer")
    if "max_highest_verified_layer" in expected and not (
        isinstance(highest, int) and not isinstance(highest, bool) and 0 <= highest <= len(VERIFICATION_LAYERS)
    ):
        out.error("expected_value", "expected.max_highest_verified_layer", f"must be an integer from 0 to {len(VERIFICATION_LAYERS)}")
    _check_bool(expected, "injection_flagged", out)


def _check_temporal(expected: Mapping[str, Any], out: Findings) -> None:
    keys = expected.get("candidate_version_keys")
    if "candidate_version_keys" in expected and not isinstance(keys, list):
        out.error("expected_value", "expected.candidate_version_keys", "must be a list of [version_id, effective_date] pairs")
    for index, key in enumerate(keys if isinstance(keys, list) else []):
        if not _is_version_key(key):
            out.error("expected_value", f"expected.candidate_version_keys[{index}]", "must be [version_id, YYYY-MM-DD or null]")
    _check_enum_list(expected, "warnings", TEMPORAL_WARNINGS, "contracts.TemporalWarning", out)
    _check_enum_list(expected, "forbidden_warnings", TEMPORAL_WARNINGS, "contracts.TemporalWarning", out)
    if _is_string_list(expected.get("warnings")) and _is_string_list(expected.get("forbidden_warnings")):
        for warning in sorted(set(expected["warnings"]) & set(expected["forbidden_warnings"])):
            out.error("expected_value", "expected.forbidden_warnings", f"{quoted(warning)} is both required and forbidden")
    if "determination" in expected and expected["determination"] != "candidate_only":
        out.error("expected_value", "expected.determination", "must be \"candidate_only\": the resolver never makes a legal determination")


def _check_abstention(expected: Mapping[str, Any], out: Findings) -> None:
    _check_bool(expected, "must_withhold_conclusion", out)
    _check_string_list(expected, "required_issue_keys", out)
    _check_string_list(expected, "forbidden_assertions", out)


def _is_version_key(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and bool(value[0])
        and (value[1] is None or is_iso_date(value[1]))
    )


# -- layer codes and the overall roll-up (citation_verification) ----------------
#: Codes that 07 §3 can report at any layer.
ANY_LAYER_CODES: FrozenSet[str] = frozenset({
    VerificationCode.VERIFICATION_UNAVAILABLE.value,
    VerificationCode.HUMAN_REVIEW_REQUIRED.value,
    VerificationCode.NOT_CHECKED.value,
})

#: Layer -> the codes 07 §3 ("Rules per layer") assigns at that layer, besides
#: ANY_LAYER_CODES. Labels are written from the specification, so a code the
#: specification never reports at a layer is a labelling error, not a style
#: choice. Note the two cross-layer uses 07 makes: L2 reports
#: insufficient_context (anchor date unknown) and L1 reports source_repealed.
LAYER_CODES: Dict[str, FrozenSet[str]] = {
    VerificationLayer.SOURCE_IDENTITY.value: frozenset({
        "source_verified", "source_not_found", "source_ambiguous", "historical_lookup_required", "source_repealed",
    }),
    VerificationLayer.VERSION_IDENTITY.value: frozenset({
        "version_verified", "wrong_version", "future_not_yet_effective", "source_outdated",
        "version_history_incomplete", "insufficient_context",
    }),
    VerificationLayer.CITATION_IDENTITY.value: frozenset({"citation_verified", "citation_not_found"}),
    VerificationLayer.TEXT_CORRESPONDENCE.value: frozenset({"text_match_verified", "text_mismatch"}),
    VerificationLayer.CLAIM_SUPPORT.value: frozenset({"claim_supported", "claim_partially_supported", "claim_unsupported"}),
    VerificationLayer.APPLICABILITY.value: frozenset({
        "applicability_established", "insufficient_context", "subcode_applicability_unproven",
        "procedure_scope_mismatch", "transitional_rule_unresolved",
    }),
    VerificationLayer.CONFLICT_UNCERTAINTY.value: frozenset({
        "no_conflict_detected", "contradictory_evidence", "manual_predates_law_change",
    }),
}

#: Code -> the LayerOutcome values 07 §3 pairs it with. Only
#: subcode_applicability_unproven has two (fail when the evidence lists other
#: subcodes, needs_review when it speaks only for the parent).
CODE_OUTCOMES: Dict[str, FrozenSet[str]] = {
    code: frozenset({outcome.value for outcome in outcomes})
    for code, outcomes in {
        "source_verified": (LayerOutcome.PASS,),
        "source_not_found": (LayerOutcome.FAIL,),
        "source_ambiguous": (LayerOutcome.NEEDS_REVIEW,),
        "historical_lookup_required": (LayerOutcome.UNAVAILABLE,),
        "source_repealed": (LayerOutcome.FAIL,),
        "version_verified": (LayerOutcome.PASS,),
        "wrong_version": (LayerOutcome.FAIL,),
        "future_not_yet_effective": (LayerOutcome.FAIL,),
        "source_outdated": (LayerOutcome.FAIL,),
        "version_history_incomplete": (LayerOutcome.UNAVAILABLE,),
        "citation_verified": (LayerOutcome.PASS,),
        "citation_not_found": (LayerOutcome.FAIL,),
        "text_match_verified": (LayerOutcome.PASS,),
        "text_mismatch": (LayerOutcome.FAIL,),
        "claim_supported": (LayerOutcome.PASS,),
        "claim_partially_supported": (LayerOutcome.NEEDS_REVIEW,),
        "claim_unsupported": (LayerOutcome.FAIL,),
        "applicability_established": (LayerOutcome.PASS,),
        "insufficient_context": (LayerOutcome.NEEDS_REVIEW,),
        "subcode_applicability_unproven": (LayerOutcome.FAIL, LayerOutcome.NEEDS_REVIEW),
        "procedure_scope_mismatch": (LayerOutcome.FAIL,),
        "transitional_rule_unresolved": (LayerOutcome.NEEDS_REVIEW,),
        "no_conflict_detected": (LayerOutcome.PASS,),
        "contradictory_evidence": (LayerOutcome.NEEDS_REVIEW,),
        "manual_predates_law_change": (LayerOutcome.NEEDS_REVIEW,),
        "verification_unavailable": (LayerOutcome.UNAVAILABLE,),
        "human_review_required": (LayerOutcome.NEEDS_REVIEW,),
        "not_checked": (LayerOutcome.NOT_APPLICABLE,),
    }.items()
}

#: OverallStatus values from worst to best, the order ClaimVerification.overall() applies.
OVERALL_ORDER: Tuple[str, ...] = (
    OverallStatus.FAILED.value,
    OverallStatus.VERIFICATION_UNAVAILABLE.value,
    OverallStatus.HUMAN_REVIEW_REQUIRED.value,
    OverallStatus.VERIFIED_PARTIAL.value,
    OverallStatus.VERIFIED.value,
)


def achievable_overalls(layer_codes: Mapping[str, str]) -> FrozenSet[str]:
    """Every expected.overall that contracts.ClaimVerification.overall() could produce from these layer codes.

    The roll-up itself is the contract's own function, not a copy of it. When
    every layer is listed the answer is exact. When some layers are not listed
    the label says nothing about them, and an unlisted layer can only make the
    roll-up worse (or complete it to ``verified``), so every status at or below
    the listed layers' roll-up is achievable.
    """
    layers = [layer for layer in iter_layer_order() if layer.value in layer_codes]
    options = [sorted(CODE_OUTCOMES[layer_codes[layer.value]]) for layer in layers]
    complete = len(layers) == len(VERIFICATION_LAYERS)
    achievable: Set[str] = set()
    for outcomes in itertools.product(*options):
        results = tuple(
            LayerResult(layer, LayerOutcome(outcome), VerificationCode(layer_codes[layer.value]))
            for layer, outcome in zip(layers, outcomes)
        )
        rolled = ClaimVerification("label", results).overall().value
        if complete:
            achievable.add(rolled)
            continue
        achievable.update(OVERALL_ORDER[: OVERALL_ORDER.index(rolled) + 1])
        if rolled == OverallStatus.VERIFIED_PARTIAL.value:
            achievable.add(OverallStatus.VERIFIED.value)
    return frozenset(achievable)


def rule_layer_codes(record: Record, out: Findings, resources: Resources) -> None:
    """A citation label's layer codes must be ones 07 §3 reports at that layer and must roll up to its overall."""
    expected = record.mapping("expected")
    layer_codes = expected.get("layer_codes")
    if record.get("task") != CITATION_TASK or not isinstance(layer_codes, dict):
        return
    usable: Dict[str, str] = {}
    for layer, code in sorted(layer_codes.items()):
        if layer not in VERIFICATION_LAYERS or code not in VERIFICATION_CODES:
            continue  # reported by the expected_value rule
        if code not in LAYER_CODES[layer] | ANY_LAYER_CODES:
            out.error(
                "layer_codes",
                f"expected.layer_codes.{layer}",
                f"{quoted(code)} is never reported at {layer} by 07 §3 (allowed: {', '.join(sorted(LAYER_CODES[layer] | ANY_LAYER_CODES))})",
            )
            continue
        usable[layer] = code
    overall = expected.get("overall")
    if not usable or overall not in OVERALL_STATUSES:
        return
    achievable = achievable_overalls(usable)
    if overall not in achievable:
        out.error(
            "layer_codes",
            "expected.overall",
            f"{quoted(overall)} cannot follow from these layer codes under contracts.ClaimVerification.overall() "
            f"(achievable: {', '.join(s for s in OVERALL_ORDER if s in achievable)})",
        )


EXPECTED_VALUE_CHECKS: Dict[str, Callable[[Mapping[str, Any], Findings], None]] = {
    CLASSIFICATION_TASK: _check_classification,
    "entity_date_extraction": _check_extraction,
    CITATION_TASK: _check_citation,
    TEMPORAL_TASK: _check_temporal,
    ABSTENTION_TASK: _check_abstention,
}


# -- input and scenario -----------------------------------------------------
def rule_task_input(record: Record, out: Findings, resources: Resources) -> None:
    task = record.get("task")
    inputs = record.get("input")
    if not isinstance(inputs, dict) or task not in TASK_SUITE:
        return
    if task != CITATION_TASK and "claim" in inputs:
        out.error("input_shape", "input.claim", "is only used by citation_verification examples")
    if task != TEMPORAL_TASK and "temporal_query" in inputs:
        out.error("input_shape", "input.temporal_query", "is only used by temporal_version_selection examples")
    if task in BUNDLE_TASKS and not isinstance(inputs.get("fixture_set"), str):
        out.error("input_shape", "input.fixture_set", f"{task} examples must name the source bundle they are scored against")
    if task == CITATION_TASK:
        _check_claim(inputs.get("claim"), out)
    if task == TEMPORAL_TASK:
        _check_temporal_query(inputs.get("temporal_query"), out)


def _check_claim(claim: Any, out: Findings) -> None:
    if not isinstance(claim, dict):
        out.error("input_shape", "input.claim", "citation_verification examples need input.claim {text, citations, ...}")
        return
    for key in ("topic", "value", "quoted_text", "context_title"):
        if claim.get(key) is not None and not isinstance(claim.get(key), str):
            out.error("input_shape", f"input.claim.{key}", "must be a string or null")
    context_title = claim.get("context_title")
    if isinstance(context_title, str) and not context_title.strip():
        # contracts.ClaimInput.context_title names the law that 같은 법 / 영 / 규칙
        # refer to; an empty title would silently mean "no context law".
        out.error("input_shape", "input.claim.context_title", "must be a non-empty law title or null")
    if claim.get("asserted_version_key") is not None and not _is_version_key(claim.get("asserted_version_key")):
        out.error("input_shape", "input.claim.asserted_version_key", "must be [version_id, YYYY-MM-DD or null] or null")
    scope = claim.get("scope")
    if scope is None:
        return
    if not isinstance(scope, dict):
        out.error("input_shape", "input.claim.scope", "must be an object")
        return
    prefix = "input.claim.scope"
    for key in ("status_codes", "subcodes"):
        _check_string_list(scope, key, out, prefix=prefix, rule="input_shape")
    _check_enum_list(scope, "procedures", PROCEDURES, "contracts.FINE_PROCEDURES", out, prefix=prefix, rule="input_shape")
    _check_bool(scope, "all_subcodes_explicit", out, prefix=prefix, rule="input_shape")


def _check_temporal_query(query: Any, out: Findings) -> None:
    if not isinstance(query, dict):
        out.error("input_shape", "input.temporal_query", "temporal_version_selection examples need input.temporal_query {stable_id, provision, anchor}")
        return
    if "anchor" in query and query["anchor"] not in ANCHOR_KINDS:
        out.error("input_shape", "input.temporal_query.anchor", f"{quoted(query['anchor'])} is not a contracts.AnchorKind value")
    _check_enum_list(query, "secondary_anchors", ANCHOR_KINDS, "contracts.AnchorKind", out, prefix="input.temporal_query", rule="input_shape")


def rule_scenario(record: Record, out: Findings, resources: Resources) -> None:
    scenario = record.get("scenario")
    if not isinstance(scenario, dict):
        return
    anchor = scenario.get("anchor")
    if anchor is not None and anchor not in ANCHOR_KINDS:
        out.error("scenario", "scenario.anchor", f"{quoted(anchor)} is not a contracts.AnchorKind value (or null)")
    dates = scenario.get("relevant_dates")
    if isinstance(dates, dict):
        for key in sorted(set(dates) - RELEVANT_DATE_KEYS):
            out.error("scenario", f"scenario.relevant_dates.{key}", f"is not a contracts.RelevantDates field ({', '.join(sorted(RELEVANT_DATE_KEYS))})")
    if record.get("task") in DATED_TASKS and not (isinstance(dates, dict) and dates.get("question_date")):
        out.error("scenario", "scenario.relevant_dates.question_date", "is required: temporal and verification labels depend on the date the question is asked")
    template = scenario.get("case_template")
    if isinstance(template, str) and (not template.strip() or template != template.strip()):
        # Splits are compared by exact template id; " t1" and "t1" would be two templates.
        out.error("scenario", "scenario.case_template", "must be a non-empty identifier without surrounding whitespace, or null")


def rule_temporal_label(record: Record, out: Findings, resources: Resources) -> None:
    """A temporal label must agree with the normative resolver (06 §3) and with its bundle."""
    query, expected = record.mapping("input", "temporal_query"), record.mapping("expected")
    if record.get("task") != TEMPORAL_TASK or not query or not expected:
        return
    scenario_anchor, query_anchor = record.get("scenario", "anchor"), query.get("anchor")
    if isinstance(scenario_anchor, str) and isinstance(query_anchor, str) and scenario_anchor != query_anchor:
        out.error("temporal_label", "input.temporal_query.anchor", f"is {quoted(query_anchor)} but scenario.anchor is {quoted(scenario_anchor)}")
    candidates = expected.get("candidate_version_keys")
    warnings = expected.get("warnings") if _is_string_list(expected.get("warnings")) else []
    stable_id = query.get("stable_id")
    fixture_set = record.get("input", "fixture_set")
    bundle = resources.bundle(fixture_set) if isinstance(fixture_set, str) and _valid_bundle_id(fixture_set) else None
    if bundle is not None and isinstance(stable_id, str) and bundle.history_unavailable(stable_id):
        _require_no_candidates(candidates, warnings, TemporalWarning.VERSION_HISTORY_UNAVAILABLE, "the bundle faults list_versions", out)
    elif query_anchor in ANCHOR_KINDS and not record.mapping("scenario", "relevant_dates").get(query_anchor):
        _require_no_candidates(candidates, warnings, TemporalWarning.ANCHOR_MISSING, f"scenario.relevant_dates has no {query_anchor}", out)
    if bundle is None or not isinstance(stable_id, str):
        return
    if stable_id not in bundle.identities:
        out.error("temporal_label", "input.temporal_query.stable_id", f"{quoted(stable_id)} is not an identity in source bundle {bundle.bundle_id}")
        return
    known = bundle.versions.get(stable_id, frozenset())
    for index, key in enumerate(candidates if isinstance(candidates, list) else []):
        if _is_version_key(key) and (key[0], key[1]) not in known:
            out.error(
                "temporal_label",
                f"expected.candidate_version_keys[{index}]",
                f"[{key[0]}, {key[1]}] is not a version of {stable_id} in source bundle {bundle.bundle_id}",
            )


def _require_no_candidates(candidates: Any, warnings: List[str], warning: TemporalWarning, reason: str, out: Findings) -> None:
    if isinstance(candidates, list) and candidates:
        out.error("temporal_label", "expected.candidate_version_keys", f"must be empty: {reason}, so the resolver returns no candidate (06 §3)")
    if warning.value not in warnings:
        out.error("temporal_label", "expected.warnings", f"must include {warning.value}: {reason} (06 §3)")


def rule_hard_negative(record: Record, out: Findings, resources: Resources) -> None:
    adversarial = record.get("scenario", "adversarial_class")
    if adversarial is None:
        return
    split = record.get("split")
    if split not in HARD_NEGATIVE_SPLITS:
        out.error("hard_negative", "split", f"adversarial class {quoted(adversarial)} examples belong in {' or '.join(HARD_NEGATIVE_SPLITS)}, not {quoted(split)}")
    task, expected = record.get("task"), record.get("expected")
    required = HARD_NEGATIVE_SIGNALS.get(task) if isinstance(task, str) else None
    if required is None or not isinstance(expected, dict):
        return
    if not hard_negative_signals(task, expected):
        out.error("hard_negative", "expected", f"an adversarial {task} example must expect something other than a clean pass: {required[1]}")


#: task -> (signal fields, human description). Classification and extraction
#: examples have no "clean pass" to avoid: their adversarial value is the
#: confusable input, and the correct label is the test, so only the split rule applies.
HARD_NEGATIVE_SIGNALS: Dict[str, Tuple[Tuple[str, ...], str]] = {
    CITATION_TASK: (("overall", "forbidden_codes"), "an overall other than \"verified\", or non-empty forbidden_codes"),
    TEMPORAL_TASK: (("warnings", "forbidden_warnings"), "non-empty warnings or forbidden_warnings"),
    ABSTENTION_TASK: (("must_withhold_conclusion", "forbidden_assertions"), "must_withhold_conclusion true, or non-empty forbidden_assertions"),
}


def hard_negative_signals(task: str, expected: Mapping[str, Any]) -> List[str]:
    """Which expected fields make this label a hard negative (empty = it expects a clean pass)."""
    signals: List[str] = []
    for key in HARD_NEGATIVE_SIGNALS.get(task, ((), ""))[0]:
        value = expected.get(key)
        if key == "overall":
            if isinstance(value, str) and value != OverallStatus.VERIFIED.value:
                signals.append(key)
        elif value is True or (isinstance(value, list) and value):
            signals.append(key)
    return signals


def rule_split_policy(record: Record, out: Findings, resources: Resources) -> None:
    if record.get("split") == "adversarial_holdout" and record.get("scenario", "adversarial_class") is None:
        out.warning("split_policy", "scenario.adversarial_class", "is null in the adversarial_holdout split; name the class or move the example to test")
    if record.get("provenance", "authoring") == "teacher_generated" and record.get("split") in EVAL_SPLITS:
        if record.get("label_review", "status") != "human_verified":
            out.error(
                "split_policy",
                "split",
                f"a teacher_generated example in {record.get('split')} must be human_verified; a teacher's conclusion is a candidate label, never gold",
            )


# -- status codes ------------------------------------------------------------
def rule_inventory_codes(record: Record, out: Findings, resources: Resources) -> None:
    inventory = resources.inventory
    if inventory is None:
        return  # reported once as a file-level error
    for path, code in _codes_to_check(record):
        if not inventory.contains(code):
            out.error("inventory", path, f"{quoted(code)} is not a status or subcode code in visa_data.json")


def _codes_to_check(record: Record) -> List[Tuple[str, str]]:
    codes: List[Tuple[str, str]] = []
    expected = record.mapping("expected")
    for key in ("status_code", "subcode", "current_status", "target_status"):
        if isinstance(expected.get(key), str):
            codes.append((f"expected.{key}", expected[key]))
    listed = expected.get("status_codes")
    for index, code in enumerate(listed if isinstance(listed, list) else []):
        if isinstance(code, str):
            codes.append((f"expected.status_codes[{index}]", code))
    for index, ref in enumerate(_source_refs(record)):
        value = ref.get("ref")
        if not isinstance(value, str):
            continue
        if ref.get("kind") == "visa_data":
            codes.append((f"source_refs[{index}].ref", value))
        elif ref.get("kind") == "status_guidance":
            # status-guidance targets are "<code>" or "<code>~<scenario>" (data/status-guidance-202609.json)
            codes.append((f"source_refs[{index}].ref", value.split("~", 1)[0]))
    return codes


def rule_subcode_hierarchy(record: Record, out: Findings, resources: Resources) -> None:
    inventory = resources.inventory
    expected = record.mapping("expected")
    if inventory is None or record.get("task") != CLASSIFICATION_TASK or not expected:
        return
    status, subcode = expected.get("status_code"), expected.get("subcode")
    if isinstance(status, str) and inventory.contains(status):
        _check_status_is_parent(inventory, status, out)
    if not isinstance(subcode, str):
        return
    if subcode == status:
        out.error("subcode_hierarchy", "expected.subcode", "repeats status_code; a parent is never its own subcode (use null)")
    elif status is None:
        out.error("subcode_hierarchy", "expected.subcode", "is set but status_code is null; a subcode is always classified under its parent")
    elif inventory.contains(subcode) and isinstance(status, str):
        _check_subcode_parent(inventory, status, subcode, out)


def _check_status_is_parent(inventory: CodeInventory, status: str, out: Findings) -> None:
    if inventory.is_subcode(status):
        parents = sorted(inventory.status_parents_of(status)) or [p for p in [inventory.structural_parent(status)] if p]
        where = f" (parent {', '.join(parents)})" if parents else ""
        out.error("subcode_hierarchy", "expected.status_code", f"{status} is a subcode{where}; put it in expected.subcode and its parent in status_code")
    elif inventory.is_program(status):
        out.warning("subcode_hierarchy", "expected.status_code", f"{status} is a program record in visa_data.json, not a status of stay")
    elif inventory.irregular_placements(status):
        listed = ", ".join(sorted(inventory.irregular_placements(status)))
        out.warning(
            "subcode_hierarchy",
            "expected.status_code",
            f"{status} has 2 segments (a parent by the repository rule) but visa_data.json lists it under {listed}; review",
        )


def _check_subcode_parent(inventory: CodeInventory, status: str, subcode: str, out: Findings) -> None:
    placements = inventory.parents_of(subcode)
    if not inventory.is_subcode(subcode):
        if status in inventory.irregular_placements(subcode):
            out.warning(
                "subcode_hierarchy",
                "expected.subcode",
                f"{subcode} has 2 segments (a parent by the repository rule) but visa_data.json lists it under {status}; review",
            )
        else:
            out.error("subcode_hierarchy", "expected.subcode", f"{subcode} is a parent code, not a subcode")
        return
    structural = inventory.structural_parent(subcode)
    if status in placements or status == structural:
        return
    status_parents = sorted(inventory.status_parents_of(subcode) | ({structural} if structural else set()))
    if status_parents:
        out.error("subcode_hierarchy", "expected.subcode", f"{subcode} belongs to {', '.join(status_parents)}, not {status}")
        return
    # Listed only under a program (REGIONAL-D-2 under REGION-S): there is no status parent to hold the label to.
    listed = ", ".join(sorted(placements)) or "no parent"
    out.warning(
        "subcode_hierarchy",
        "expected.subcode",
        f"{subcode} is listed only under the program {listed}; status_code {status} cannot be checked against a status parent, review",
    )


def rule_not_status_tokens(record: Record, out: Findings, resources: Resources) -> None:
    tokens = record.get("expected", "not_status_tokens")
    question = record.get("input", "question")
    if not _is_string_list(tokens) or not isinstance(question, str):
        return
    haystack = normalize_question(question)
    for index, token in enumerate(tokens):
        if normalize_question(token) not in haystack:
            out.error("expected_value", f"expected.not_status_tokens[{index}]", f"{quoted(token)} does not occur in input.question")


def rule_procedure_scope(record: Record, out: Findings, resources: Resources) -> None:
    """A visa-issuance label is never backed by a stay manual edition, and vice versa (CLAUDE.md)."""
    procedure = record.get("expected", "procedure")
    if record.get("task") != CLASSIFICATION_TASK or not isinstance(procedure, str) or procedure not in PROCEDURES:
        return
    scope = procedure_scope(procedure)
    for index, ref in enumerate(_source_refs(record)):
        edition = ref.get("ref")
        if ref.get("kind") != "manual" or not isinstance(edition, str):
            continue
        edition_scope = manual_scope(edition)
        if edition_scope is not None and edition_scope != scope:
            out.error(
                "procedure_scope",
                f"source_refs[{index}].ref",
                f"{procedure} is a {scope}-scope procedure but {edition} is a {edition_scope} manual edition; visa issuance and stay procedures never share evidence",
            )


# -- evidence references -------------------------------------------------------
def _source_refs(record: Record) -> List[Dict[str, Any]]:
    refs = record.get("source_refs")
    return [ref for ref in refs if isinstance(ref, dict)] if isinstance(refs, list) else []


def rule_source_refs_shape(record: Record, out: Findings, resources: Resources) -> None:
    refs = _source_refs(record)
    if len(refs) > 1 and any(ref.get("kind") == "none" for ref in refs):
        out.error("source_refs", "source_refs", "kind \"none\" says the label has no source; it cannot be combined with other refs")


def rule_law_identity_refs(record: Record, out: Findings, resources: Resources) -> None:
    registry = resources.registry
    for index, ref in enumerate(_source_refs(record)):
        if ref.get("kind") != "law_identity":
            continue
        path = f"source_refs[{index}]"
        law_id = ref.get("ref")
        if not registry.exists:
            out.error("law_identity", path, f"law identity registry not found at {shown(registry.directory)}")
            continue
        if not isinstance(law_id, str) or law_id not in registry.records:
            out.error("law_identity", f"{path}.ref", _unknown_law_id_message(registry, law_id))
            continue
        _check_registry_version(registry.records[law_id], ref, path, out)


def _unknown_law_id_message(registry: Registry, law_id: Any) -> str:
    message = f"{quoted(law_id)} is not a law_id in the registry"
    if not isinstance(law_id, str):
        return message
    hint = registry.title_to_id.get(compact(law_id))
    if hint:
        return message + f"; a title is never an identity, use law_id {hint}"
    if compact(law_id) in registry.unaddressable_titles:
        return message + "; the registry knows this title but has no law_id for it, so it cannot be cited by identity yet"
    return message


def _check_registry_version(entry: RegistryRecord, ref: Mapping[str, Any], path: str, out: Findings) -> None:
    version_id, effective_date = _opt_str(ref.get("version_id")), _opt_str(ref.get("effective_date"))
    if version_id is None and effective_date is None:
        return
    if _version_matches(entry.versions, version_id, effective_date):
        return
    known = ", ".join(f"[{v}, {d}]" for v, d in sorted(entry.versions, key=lambda pair: (pair[0] or "", pair[1] or "")))
    out.error(
        "law_identity",
        path,
        f"version [{version_id}, {effective_date}] does not match the registry record for {entry.law_id} (known: {known or 'none'})",
    )


def _version_matches(known: Iterable[VersionKey], version_id: Optional[str], effective_date: Optional[str]) -> bool:
    """A ref may give the version id, the effective date or both; whatever it gives must match one version."""
    return any(
        (version_id is None or version_id == known_id) and (effective_date is None or effective_date == known_date)
        for known_id, known_date in known
    )


def _valid_bundle_id(bundle_id: str) -> bool:
    """Bundle ids become file names; refuse anything that could leave the sources directory."""
    return bool(BUNDLE_ID_PATTERN.match(bundle_id)) and ".." not in bundle_id


def rule_source_bundles(record: Record, out: Findings, resources: Resources) -> None:
    authoring = record.get("provenance", "authoring")
    synthetic: Set[str] = set()
    for path, bundle_id, ref in _bundle_refs(record):
        if not _valid_bundle_id(bundle_id):
            out.error("source_bundle", path, f"{quoted(bundle_id)} is not a valid bundle id (letters, digits, '.', '_', '-')")
            continue
        bundle = resources.bundle(bundle_id)
        if bundle is None:
            out.error("source_bundle", path, f"source bundle {quoted(bundle_id)} not found at {shown(resources.options.sources_dir / (bundle_id + '.json'))}")
            continue
        if bundle.is_synthetic:
            synthetic.add(bundle.bundle_id)
            if authoring != "synthetic_authored":
                out.error(
                    "source_bundle",
                    path,
                    f"synthetic_fixture bundle {bundle_id} may only back synthetic_authored examples (authoring is {quoted(authoring)})",
                )
        if ref is not None:
            _check_bundle_ref_version(bundle, ref, path.rsplit(".", 1)[0], out)
    if synthetic and any(ref.get("kind") == "law_identity" for ref in _source_refs(record)):
        out.error(
            "source_bundle",
            "source_refs",
            f"mixes synthetic_fixture bundle(s) {', '.join(sorted(synthetic))} with real law_identity refs; synthetic text never backs a real law id",
        )


def _bundle_refs(record: Record) -> List[Tuple[str, str, Optional[Dict[str, Any]]]]:
    """(path, bundle id, the source_ref or None for input.fixture_set)."""
    refs: List[Tuple[str, str, Optional[Dict[str, Any]]]] = []
    fixture_set = record.get("input", "fixture_set")
    if isinstance(fixture_set, str):
        refs.append(("input.fixture_set", fixture_set, None))
    for index, ref in enumerate(_source_refs(record)):
        if ref.get("kind") == "source_bundle" and isinstance(ref.get("ref"), str):
            refs.append((f"source_refs[{index}].ref", ref["ref"], ref))
    return refs


def _check_bundle_ref_version(bundle: BundleInfo, ref: Mapping[str, Any], path: str, out: Findings) -> None:
    version_id, effective_date = _opt_str(ref.get("version_id")), _opt_str(ref.get("effective_date"))
    provision = _opt_str(ref.get("provision"))
    if version_id is None and effective_date is None:
        return
    matching = [
        key for key in bundle.all_version_keys()
        if (version_id is None or key[0] == version_id) and (effective_date is None or key[1] == effective_date)
    ]
    if not matching:
        out.error("source_bundle", path, f"version [{version_id}, {effective_date}] is not in source bundle {bundle.bundle_id}")
        return
    if provision is not None and not any(provision in bundle.provisions.get(key, frozenset()) for key in matching):
        out.warning(
            "source_bundle",
            f"{path}.provision",
            f"{quoted(provision)} is not a provision of that version in source bundle {bundle.bundle_id}; "
            "a deliberately missing article belongs in the claim, not in source_refs",
        )


def rule_manual_refs(record: Record, out: Findings, resources: Resources) -> None:
    for index, ref in enumerate(_source_refs(record)):
        if ref.get("kind") != "manual":
            continue
        path = f"source_refs[{index}].ref"
        if resources.manual_problem:
            out.error("manual_edition", path, resources.manual_problem)
            continue
        edition_id = ref.get("ref")
        edition = resources.manual_editions.get(edition_id) if isinstance(edition_id, str) else None
        if edition is None:
            out.error("manual_edition", path, f"{quoted(edition_id)} is not an edition in data/manual_approval_index.json")
            continue
        if edition.state not in APPROVED_MANUAL_STATES:
            out.warning("manual_edition", path, f"label backed by unapproved manual edition {edition_id} (approval_state {edition.state or 'missing'})")
        stated = _opt_str(ref.get("effective_date"))
        if stated and edition.effective_date and stated != edition.effective_date:
            out.error(
                "manual_edition",
                f"source_refs[{index}].effective_date",
                f"is {stated} but the approval index records {edition.effective_date} for {edition_id}",
            )


# -- provenance and review ---------------------------------------------------
#: Keys a teacher block must name: the policy decides per (provider, model, serving channel).
TEACHER_IDENTITY_KEYS: Tuple[str, ...] = ("provider", "model", "channel")


def rule_teacher(record: Record, out: Findings, resources: Resources) -> None:
    """Teacher output only as configs/teacher_policy.json permits (11 §4.3).

    The block's shape is checked before the policy is consulted, so a block
    without ``channel`` is reported whatever state the policy file is in:
    a missing or pending policy must not hide an incomplete record.
    """
    teacher = record.get("provenance", "teacher")
    if record.get("provenance", "authoring") != "teacher_generated":
        if teacher is not None:
            out.error("teacher", "provenance.teacher", "is only for teacher_generated examples (use null or leave it out)")
        return
    if not isinstance(teacher, dict):
        out.error("teacher", "provenance.teacher", "teacher_generated examples need {provider, model, channel, terms_ref, permitted}")
        return
    missing = [key for key in TEACHER_IDENTITY_KEYS if not _opt_str(teacher.get(key))]
    for key in missing:
        out.error("teacher", f"provenance.teacher.{key}", "is required: the teacher policy decides per provider, model and serving channel")
    if teacher.get("permitted") is not True:
        out.error("teacher", "provenance.teacher.permitted", "must be true; only a teacher the policy permits may produce examples")
    policy, problem = resources.teacher_policy()
    if problem:
        out.error("teacher", "provenance.teacher", problem)
        return
    if not policy.signoff.approved:
        out.error(
            "teacher",
            "provenance.authoring",
            f"teacher policy legal_signoff is {policy.signoff.status!r}; no teacher output may enter a dataset before counsel approves it",
        )
    if missing:
        return
    decision = policy.is_permitted(teacher["provider"], teacher["model"], teacher["channel"])
    if not decision.permitted:
        out.error("teacher", "provenance.teacher", "teacher policy does not permit this teacher: " + "; ".join(decision.reasons))


def rule_derived_from(record: Record, out: Findings, resources: Resources) -> None:
    if record.get("provenance", "authoring") != "derived_from_repository_data":
        return
    derived = record.get("provenance", "derived_from")
    if not (_is_string_list(derived) and derived):
        out.warning("provenance", "provenance.derived_from", "derived_from_repository_data examples should name the repository files they were derived from")


def rule_label_review(record: Record, out: Findings, resources: Resources) -> None:
    review = record.mapping("label_review")
    if review.get("status") == "human_verified":
        for key in ("reviewer", "reviewed_at"):
            value = review.get(key)
            if not isinstance(value, str) or not value.strip():
                out.error("label_review", f"label_review.{key}", "is required when status is human_verified")
    reviewed, created = review.get("reviewed_at"), record.get("provenance", "created_at")
    if is_iso_date(reviewed) and is_iso_date(created) and reviewed < created:
        out.error("label_review", "label_review.reviewed_at", f"{reviewed} is before provenance.created_at {created}")


def rule_revision(record: Record, out: Findings, resources: Resources) -> None:
    history = record.get("revision_history")
    revision = record.get("revision")
    if not isinstance(history, list) or not history or not isinstance(revision, int) or isinstance(revision, bool):
        return
    numbers = [entry.get("revision") for entry in history if isinstance(entry, dict)]
    if not numbers or not all(isinstance(n, int) and not isinstance(n, bool) for n in numbers):
        return  # reported by the schema
    if any(later <= earlier for earlier, later in zip(numbers, numbers[1:])):
        out.error("revision", "revision_history", "revisions must increase strictly")
    if numbers[-1] != revision:
        out.error("revision", "revision", f"is {revision} but revision_history ends at {numbers[-1]}")


def rule_personal_data(record: Record, out: Findings, resources: Resources) -> None:
    for path, finding in pii.scan_value(record.data):
        out.error("pii", path, pii.describe(finding))


RECORD_RULES: Tuple[Rule, ...] = (
    rule_suite_matches_task,
    rule_expected_keys,
    rule_layer_codes,
    rule_task_input,
    rule_scenario,
    rule_temporal_label,
    rule_hard_negative,
    rule_split_policy,
    rule_inventory_codes,
    rule_subcode_hierarchy,
    rule_not_status_tokens,
    rule_procedure_scope,
    rule_source_refs_shape,
    rule_law_identity_refs,
    rule_source_bundles,
    rule_manual_refs,
    rule_teacher,
    rule_derived_from,
    rule_label_review,
    rule_revision,
    rule_personal_data,
)


# ---------------------------------------------------------------------------
# Cross-record rules
# ---------------------------------------------------------------------------
def check_cross_records(records: Sequence[Record]) -> List[Issue]:
    examples = [r for r in records if isinstance(r.data, dict)]
    issues: List[Issue] = []
    issues.extend(check_duplicate_ids(examples))
    issues.extend(check_duplicate_questions(examples))
    issues.extend(check_contamination(examples))
    issues.extend(check_case_templates(examples))
    return issues


#: Splits that must not share a case template with ``dev``, which is tuned on.
DEV_SEPARATED_SPLITS: Tuple[str, ...] = ("test", "adversarial_holdout")


def check_case_templates(records: Sequence[Record]) -> List[Issue]:
    """Splits are assigned per case template, never per example (11 §6.1).

    Near-identical variants written from one template (the same facts with a
    different date or code) defeat the character-3-gram contamination check
    when their wording differs enough. ``scenario.case_template`` names the
    template, and the rule is on the id, not on the text:

    * a template used in ``train`` and in ``dev``, ``test`` or
      ``adversarial_holdout``: error on each eval example (``case_template``);
    * a template used in ``dev`` and in ``test`` or ``adversarial_holdout``:
      warning on each of those examples (``case_template_dev_eval``). The task
      brief names dev/test; dev/adversarial_holdout is included as the more
      conservative reading, because dev is tuned on and the holdout must not be.

    Examples without a template (null or absent) are not compared.
    """
    by_template: Dict[str, Dict[str, List[Record]]] = {}
    for record in records:
        template, split = record.get("scenario", "case_template"), record.get("split")
        if isinstance(template, str) and template.strip() and isinstance(split, str):
            by_template.setdefault(template, {}).setdefault(split, []).append(record)
    issues: List[Issue] = []
    for template in sorted(by_template):
        splits = by_template[template]
        train, dev = splits.get("train", []), splits.get("dev", [])
        for split in EVAL_SPLITS:
            for record in splits.get(split, []) if train else []:
                out = Findings.for_record(record)
                out.error(
                    "case_template",
                    "scenario.case_template",
                    f"case template {quoted(template)} is also used by train example {train[0].name}; "
                    f"a template is assigned to one side of the train/eval boundary, never to train and {split}",
                )
                issues.extend(out.issues)
        for split in DEV_SEPARATED_SPLITS:
            for record in splits.get(split, []) if dev else []:
                out = Findings.for_record(record)
                out.warning(
                    "case_template_dev_eval",
                    "scenario.case_template",
                    f"case template {quoted(template)} is also used by dev example {dev[0].name}; "
                    f"dev is tuned on, so a template it shares with {split} weakens {split}",
                )
                issues.extend(out.issues)
    return issues


def check_duplicate_ids(records: Sequence[Record]) -> List[Issue]:
    issues: List[Issue] = []
    first: Dict[str, Record] = {}
    for record in records:
        example_id = record.example_id
        if example_id is None:
            continue
        if example_id in first:
            out = Findings.for_record(record)
            out.error("duplicate_id", "id", f"duplicate id (first used at {first[example_id].location})")
            issues.extend(out.issues)
        else:
            first[example_id] = record
    return issues


def normalize_question(text: Any) -> str:
    """contracts.normalize_text (NFC, whitespace, interpuncts), then casefold."""
    return normalize_text(text if isinstance(text, str) else "").casefold()


def input_context(record: Record) -> str:
    """Everything else the system under test sees besides the question, canonicalized.

    Two examples with the same question but a different claim, bundle, temporal
    query or relevant date are different items: the 제73조 fee question asked on
    2026-10-19 and on 2027-10-01 has two correct answers (06 §4).
    """
    context = {
        "input": {key: value for key, value in record.mapping("input").items() if key != "question"},
        "relevant_dates": record.get("scenario", "relevant_dates"),
        "anchor": record.get("scenario", "anchor"),
        "facts": record.get("scenario", "facts"),
    }
    return _canonical(context)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def check_duplicate_questions(records: Sequence[Record]) -> List[Issue]:
    """Exact duplicates, contradictions and question reuse within one task.

    * same task + normalized question + rest of the input: a duplicate (error),
      or a contradiction (error) when the language matches and expected differs;
    * same task + normalized question, different rest of the input: allowed,
      reported as a warning so the reuse is deliberate.
    """
    issues: List[Issue] = []
    by_question: Dict[Tuple[str, str], List[Record]] = {}
    for record in records:
        task, question = record.get("task"), record.get("input", "question")
        if isinstance(task, str) and isinstance(question, str):
            by_question.setdefault((task, normalize_question(question)), []).append(record)
    for (task, _), members in sorted(by_question.items(), key=lambda item: (item[0][0], item[1][0].location)):
        seen_contexts: Dict[str, List[Record]] = {}
        for record in members:
            context = input_context(record)
            same_input = seen_contexts.get(context)
            if same_input:
                issues.extend(_duplicate_or_contradiction(task, record, same_input))
            elif seen_contexts:
                first = next(iter(seen_contexts.values()))[0]
                out = Findings.for_record(record)
                out.warning(
                    "question_reuse",
                    "input.question",
                    f"same question text as {first.name} within task {task} but a different input or scenario; confirm the variants are intended",
                )
                issues.extend(out.issues)
            seen_contexts.setdefault(context, []).append(record)
    return issues


def _duplicate_or_contradiction(task: str, record: Record, earlier: Sequence[Record]) -> List[Issue]:
    out = Findings.for_record(record)
    language = record.get("language")
    expected = _canonical(record.get("expected"))
    conflicting = [other for other in earlier if other.get("language") == language and _canonical(other.get("expected")) != expected]
    if conflicting:
        out.error(
            "contradiction",
            "expected",
            f"same question, input, task ({task}) and language as {conflicting[0].name} but a different expected label",
        )
    else:
        out.error("duplicate_question", "input.question", f"duplicates {earlier[0].name} within task {task}")
    return out.issues


def contamination_text(record: Record) -> str:
    """The text a model would memorise: the question plus the claim being verified."""
    parts = [record.get("input", "question"), record.get("input", "claim", "text")]
    return normalize_question(" ".join(p for p in parts if isinstance(p, str)))


def char_trigrams(text: str) -> FrozenSet[str]:
    if len(text) < 3:
        return frozenset({text}) if text else frozenset()
    return frozenset(text[i:i + 3] for i in range(len(text) - 2))


def jaccard(left: FrozenSet[str], right: FrozenSet[str]) -> float:
    if not left and not right:
        return 1.0
    union = len(left | right)
    return len(left & right) / union if union else 0.0


def is_near_duplicate(left: FrozenSet[str], right: FrozenSet[str]) -> bool:
    """Jaccard >= CONTAMINATION_THRESHOLD, compared exactly in integers."""
    if not left and not right:
        return True
    union = len(left | right)
    return len(left & right) * CONTAMINATION_THRESHOLD.denominator >= CONTAMINATION_THRESHOLD.numerator * union


def check_contamination(records: Sequence[Record]) -> List[Issue]:
    grams = {id(record): char_trigrams(contamination_text(record)) for record in records}
    by_split: Dict[str, List[Record]] = {}
    for record in records:
        split = record.get("split")
        if isinstance(split, str):
            by_split.setdefault(split, []).append(record)
    finder = NearDuplicateFinder(grams)
    issues: List[Issue] = []
    train = by_split.get("train", [])
    for split in EVAL_SPLITS:
        issues.extend(_report_pairs(finder.pairs(train, by_split.get(split, [])), grams, ERROR, "contamination", f"train/{split}"))
    issues.extend(_report_pairs(finder.pairs(by_split.get("dev", []), by_split.get("test", [])), grams, WARNING, "contamination_dev_test", "dev/test"))
    return issues


class NearDuplicateFinder:
    """All (source, target) pairs with trigram Jaccard >= the threshold, without comparing every pair.

    Prefix filtering: order every gram set by global gram frequency (rarest
    first). If J(A, B) >= t then |A ∩ B| >= ceil(t * |A|), so the first
    |A| - ceil(t * |A|) + 1 grams of A and the matching prefix of B must share a
    gram. Only pairs that share a prefix gram are compared exactly. The result
    is identical to the all-pairs comparison; it is just faster on large splits.
    """

    def __init__(self, grams: Mapping[int, FrozenSet[str]]) -> None:
        self.grams = grams
        frequency: Counter = Counter()
        for gram_set in grams.values():
            frequency.update(gram_set)
        self.frequency = frequency

    def prefix(self, gram_set: FrozenSet[str]) -> List[str]:
        if not gram_set:
            return []
        ordered = sorted(gram_set, key=lambda gram: (self.frequency[gram], gram))
        overlap = math.ceil(CONTAMINATION_THRESHOLD * len(ordered))   # exact: Fraction * int
        return ordered[: len(ordered) - overlap + 1]

    def pairs(self, sources: Sequence[Record], targets: Sequence[Record]) -> List[Tuple[Record, Record]]:
        index: Dict[str, List[int]] = {}
        for position, source in enumerate(sources):
            for gram in self.prefix(self.grams[id(source)]):
                index.setdefault(gram, []).append(position)
        empty_sources = [p for p, source in enumerate(sources) if not self.grams[id(source)]]
        found: List[Tuple[Record, Record]] = []
        for target in targets:
            target_grams = self.grams[id(target)]
            candidates = set(empty_sources) if not target_grams else set()
            for gram in self.prefix(target_grams):
                candidates.update(index.get(gram, ()))
            for position in sorted(candidates):
                source = sources[position]
                if is_near_duplicate(self.grams[id(source)], target_grams):
                    found.append((source, target))
        return found


def _report_pairs(
    pairs: Sequence[Tuple[Record, Record]], grams: Mapping[int, FrozenSet[str]], severity: str, rule: str, label: str
) -> List[Issue]:
    issues: List[Issue] = []
    for source, target in pairs:
        score = jaccard(grams[id(source)], grams[id(target)])
        out = Findings.for_record(target)
        message = (
            f"{label} near duplicate of {source.name} "
            f"(character-3-gram Jaccard {score:.3f} >= {float(CONTAMINATION_THRESHOLD)})"
        )
        (out.error if severity == ERROR else out.warning)(rule, "input.question", message)
        issues.extend(out.issues)
    return issues


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
@dataclass
class Report:
    files: List[str]
    example_count: int
    counts: Dict[str, Dict[str, int]]
    issues: List[Issue]

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def rules(self, severity: Optional[str] = None) -> List[str]:
        """Sorted distinct rule ids that fired (optionally of one severity)."""
        return sorted({i.rule for i in self.issues if severity is None or i.severity == severity})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "example_schema_version": SCHEMA_VERSION,
            "result": "pass" if self.ok else "fail",
            "files": self.files,
            "example_count": self.example_count,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "counts": self.counts,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def render_text(self) -> str:
        lines = [
            f"Waymaker dataset validation ({SCHEMA_VERSION})",
            f"files: {len(self.files)}  examples: {self.example_count}  errors: {len(self.errors)}  warnings: {len(self.warnings)}",
        ]
        for name in COUNT_FIELDS:
            lines.append("")
            lines.append(f"by {name.replace('_', ' ')}:")
            bucket = self.counts.get(name, {})
            width = max([len(key) for key in bucket] + [8])
            lines.extend(f"  {key:<{width}}  {bucket[key]:>5}" for key in sorted(bucket))
        for title, issues in (("errors", self.errors), ("warnings", self.warnings)):
            lines.append("")
            lines.append(f"{title} ({len(issues)}):")
            lines.extend(f"  {issue.render()}" for issue in issues)
        lines.append("")
        lines.append("result: " + ("PASS" if self.ok else "FAIL"))
        return "\n".join(lines) + "\n"


def count_examples(records: Sequence[Record]) -> Dict[str, Dict[str, int]]:
    counters: Dict[str, Counter] = {name: Counter() for name in COUNT_FIELDS}
    for record in records:
        if not isinstance(record.data, dict):
            continue
        counters["suite"][_label(record.get("suite"))] += 1
        counters["task"][_label(record.get("task"))] += 1
        counters["language"][_label(record.get("language"))] += 1
        counters["split"][_label(record.get("split"))] += 1
        counters["adversarial_class"][_adversarial_label(record.get("scenario", "adversarial_class"))] += 1
        counters["label_status"][_label(record.get("label_review", "status"))] += 1
        counters["authoring"][_label(record.get("provenance", "authoring"))] += 1
    return {name: dict(sorted(counter.items())) for name, counter in counters.items()}


def _label(value: Any) -> str:
    """A count bucket name. Values come from the examples, so they are redacted like issue text."""
    return pii.redact(value) if isinstance(value, str) and value else "(missing)"


def _adversarial_label(value: Any) -> str:
    if value is None:
        return "(none)"
    if isinstance(value, str) and value in ADVERSARIAL_CLASSES:
        return f"{value} {ADVERSARIAL_CLASSES[value]}"
    return _label(value)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def validate_records(
    records: Sequence[Record],
    options: Optional[Options] = None,
    *,
    schema: Optional[Mapping[str, Any]] = None,
    resources: Optional[Resources] = None,
    files: Sequence[str] = (),
    extra_issues: Sequence[Issue] = (),
) -> Report:
    """Validate records already in memory (the CLI and the tests share this path)."""
    options = options or Options()
    resources = resources or Resources(options)
    schema = schema if schema is not None else load_schema(options.schema_path)
    issues: List[Issue] = list(extra_issues)
    for record in records:
        issues.extend(check_record(record, schema, resources))
    issues.extend(check_cross_records(records))
    issues.extend(resources.file_issues)
    return Report(
        files=list(files),
        example_count=sum(1 for record in records if isinstance(record.data, dict)),
        counts=count_examples(records),
        issues=sorted(set(issues), key=Issue.sort_key),
    )


def validate_paths(paths: Sequence[Path], options: Optional[Options] = None, *, schema: Optional[Mapping[str, Any]] = None) -> Report:
    files, issues = discover(paths)
    records, parse_issues = load_records(files, explicit=[path for path in paths if path.is_file()])
    return validate_records(
        records,
        options,
        schema=schema,
        files=[path.as_posix() for path in files],
        extra_issues=issues + parse_issues,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m waymaker_ai.dataset.validate",
        description="Validate Waymaker dataset examples (schema, cross-record and provenance rules). Exit 1 on any error.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="example files (.json, .jsonl) or directories")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_DIR, help="law identity registry directory")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES_DIR, help="source bundle directory")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY_PATH, help="visa_data.json (read-only)")
    parser.add_argument("--manual-index", type=Path, default=DEFAULT_MANUAL_INDEX_PATH, help="manual_approval_index.json (read-only)")
    parser.add_argument("--teacher-policy", type=Path, default=DEFAULT_TEACHER_POLICY_PATH, help="teacher_policy.json")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH, help="example schema (default: schemas/example.schema.json)")
    parser.add_argument("--json", type=Path, dest="json_out", help="also write the report as JSON to this path")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    options = Options(
        registry_dir=args.registry,
        sources_dir=args.sources,
        inventory_path=args.inventory,
        manual_index_path=args.manual_index,
        teacher_policy_path=args.teacher_policy,
        schema_path=args.schema,
    )
    try:
        schema = load_schema(options.schema_path)
    except (SchemaError, OSError, ValueError) as exc:
        sys.stderr.write(f"cannot validate: the example schema is unusable: {exc}\n")
        return 2
    report = validate_paths(args.paths, options, schema=schema)
    sys.stdout.write(report.render_text())
    if args.json_out:
        args.json_out.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
