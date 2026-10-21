"""Offline legal-source adapter over source bundles.

Why a fixture adapter: the verifier and the temporal resolver must be testable
and benchmarkable without the network, and the benchmark must be able to
script *failures* (an HTML body, an HTTP 429, a timeout) as precisely as it
scripts statute text. A source bundle (``datasets/fixtures/sources/<id>.json``,
format documented in ``schemas/source_bundle.schema.json``) holds both.

What the adapter guarantees, because the verifier relies on it:

* Every method returns a ``LookupResult`` and spends exactly one simulated
  upstream call (``LookupResult.calls == 1``); ``call_counts`` counts them per
  operation.
* A scripted fault is returned with its status and no payload. A fault that
  describes a failed response (``raw_body_kind`` set) can never carry
  ``found`` or ``not_found``: failure is not absence (spec 07 §2, invariant 1).
* ``not_found`` carries ``Coverage.COMPLETE`` only when the bundle says the
  lookup could have returned the item: ``title_index_coverage`` for titles,
  ``history_coverage`` for version lists, ``parse_status == "complete"`` of the
  version for provisions (a bundle that captured three articles of a law marks
  that version ``partial``), and a read 부칙 (``has_transitional_provisions`` not
  null) for addenda.
* A provision's ``structure_complete`` is read from the bundle record and is
  False unless the record says ``true``. It is the only thing that makes the
  absence of a cited 항 / 호 / 목 authoritative (spec 07 §3 L3): a complete
  version can still hold an article whose sub-units were only partly parsed.
* Heading units (조문여부 = 전문, ``unit_kind == "heading"``) are never returned,
  even when they share an article number with a real article, as they do in
  the official JSON.
* Titles resolve only by exact ``compact()`` match. A ``partial`` title index
  knows current titles only (official and short titles), not former ones.

``load_bundle`` validates a bundle before anything reads it, so a malformed
fixture fails loudly at load time instead of producing a plausible result.
"""
from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from waymaker_ai.contracts import (
    CONDITION_KINDS,
    Addendum,
    Coverage,
    GuidanceItem,
    LookupResult,
    LookupStatus,
    ParseStatus,
    ProvenanceStatus,
    ProvisionRef,
    ProvisionText,
    Scope,
    SourceFamily,
    SourceIdentity,
    SourceVersion,
    compact,
    normalize_text,
    parse_date,
)
from waymaker_ai.legal.identity import (
    exact_matches,
    identity_from_record,
    is_official_url,
    near_matches,
    provision_key_of,
    sort_versions,
    version_from_record,
)

OPERATIONS: Tuple[str, ...] = ("resolve_title", "list_versions", "get_provision", "get_addenda", "guidance")

#: How the raw upstream body of a scripted fault looked.
RAW_BODY_KINDS: Tuple[str, ...] = (
    "html", "empty", "malformed_json", "malformed_xml", "http_429", "timeout", "http_500", "official_error",
)

#: The status each raw failure normally maps to. A fault may name another
#: *failure* status (an official error payload can be a rejected credential,
#: i.e. ``unavailable_auth``), never ``found`` or ``not_found``.
RAW_BODY_DEFAULT_STATUS: Dict[str, LookupStatus] = {
    "html": LookupStatus.UNAVAILABLE_PARSE,
    "empty": LookupStatus.UNAVAILABLE_PARSE,
    "malformed_json": LookupStatus.UNAVAILABLE_PARSE,
    "malformed_xml": LookupStatus.UNAVAILABLE_PARSE,
    "http_429": LookupStatus.UNAVAILABLE_RATE_LIMITED,
    "timeout": LookupStatus.UNAVAILABLE_TIMEOUT,
    "http_500": LookupStatus.UPSTREAM_ERROR,
    "official_error": LookupStatus.UPSTREAM_ERROR,
}

UNIT_KINDS: Tuple[str, ...] = ("article", "heading", "annex", "addendum")
ADDENDUM_KINDS: Tuple[str, ...] = ("effective_date", "transitional", "application", "other")
BUNDLE_PROVENANCE: Tuple[str, ...] = ("synthetic_fixture", "verified_web", "verified_api")
COVERAGE_VALUES: Tuple[str, ...] = tuple(c.value for c in Coverage)

#: Keys a bundle must have. ``captured_at``, ``addenda``, ``guidance`` and
#: ``faults`` may be omitted (null / empty).
REQUIRED_BUNDLE_KEYS: Tuple[str, ...] = (
    "bundle_id", "bundle_version", "provenance", "attribution", "title_index_coverage",
    "history_coverage", "identities", "versions", "provisions",
)
OPTIONAL_BUNDLE_KEYS: Tuple[str, ...] = ("captured_at", "addenda", "guidance", "faults")

#: Keys a fault's ``match`` may use. ``topic`` is for the guidance operation.
FAULT_MATCH_KEYS: Tuple[str, ...] = ("title", "stable_id", "provision_key", "topic")

#: Bundle ids are file names; nothing that could walk out of the directory.
BUNDLE_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-_.")

DEFAULT_SOURCES_DIR = Path(__file__).resolve().parents[2] / "datasets" / "fixtures" / "sources"

VersionKey = Tuple[str, Optional[str]]


class BundleError(ValueError):
    """A source bundle that does not follow the bundle format."""


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------
def bundle_path(bundle_id: str, root: Optional[Path] = None) -> Path:
    if not bundle_id or not set(bundle_id) <= BUNDLE_ID_CHARS or bundle_id.startswith("."):
        raise BundleError(f"bundle id {bundle_id!r} is not a plain file name")
    return Path(root or DEFAULT_SOURCES_DIR) / f"{bundle_id}.json"


def load_bundle(bundle_id: str, root: Optional[Path] = None) -> Dict[str, Any]:
    """Read and validate ``<root>/<bundle_id>.json`` (root defaults to the fixture directory)."""
    path = bundle_path(bundle_id, root)
    bundle = read_bundle_file(path)
    if bundle.get("bundle_id") != bundle_id:
        raise BundleError(f"{path.name}: bundle_id {bundle.get('bundle_id')!r} does not match the file name")
    return bundle


def read_bundle_file(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        bundle = json.load(handle)
    if not isinstance(bundle, dict):
        raise BundleError(f"{Path(path).name}: a bundle is a JSON object")
    errors = validate_bundle(bundle)
    if errors:
        raise BundleError(f"{Path(path).name}: " + "; ".join(errors))
    return bundle


def _version_key_of_record(record: Mapping[str, Any]) -> Tuple[str, str, Optional[str]]:
    effective = parse_date(record.get("effective_date"))
    return (str(record.get("stable_id")), str(record.get("version_id")), effective.isoformat() if effective else None)


def _check_enum(errors: List[str], where: str, value: Any, allowed: Sequence[str]) -> None:
    if value not in allowed:
        errors.append(f"{where}: {value!r} is not one of {list(allowed)}")


def _check_date(errors: List[str], where: str, value: Any) -> None:
    try:
        parse_date(value)
    except (TypeError, ValueError):
        errors.append(f"{where}: {value!r} is not a YYYY-MM-DD date")


def _check_provenance(errors: List[str], where: str, record: Mapping[str, Any], synthetic: bool) -> None:
    """Synthetic text never sits in a record that looks real, and the reverse."""
    value = record.get("provenance")
    if value is None:
        return
    _check_enum(errors, f"{where}.provenance", value, [p.value for p in ProvenanceStatus])
    if synthetic and value != ProvenanceStatus.SYNTHETIC_FIXTURE.value:
        errors.append(f"{where}: a synthetic bundle may only hold synthetic_fixture records")
    if not synthetic and value == ProvenanceStatus.SYNTHETIC_FIXTURE.value:
        errors.append(f"{where}: a verified bundle may not hold synthetic_fixture records")
    url = record.get("official_url")
    if url and synthetic and is_official_url(url):
        errors.append(f"{where}: a synthetic record may not carry an official URL")
    if url and not synthetic and not is_official_url(url):
        errors.append(f"{where}: official_url is not on an allowlisted official host")


def validate_bundle(bundle: Mapping[str, Any]) -> List[str]:
    """Every format violation in ``bundle`` (empty list = valid)."""
    errors: List[str] = []
    for key in REQUIRED_BUNDLE_KEYS:
        if key not in bundle:
            errors.append(f"missing key {key!r}")
    if errors:
        return errors
    _check_enum(errors, "provenance", bundle["provenance"], BUNDLE_PROVENANCE)
    _check_enum(errors, "title_index_coverage", bundle["title_index_coverage"], COVERAGE_VALUES)
    if bundle.get("captured_at") is not None:
        _check_date(errors, "captured_at", bundle["captured_at"])
    synthetic = bundle["provenance"] == ProvenanceStatus.SYNTHETIC_FIXTURE.value

    stable_ids = set()
    for i, record in enumerate(bundle["identities"]):
        where = f"identities[{i}]"
        try:
            identity_from_record(record)
        except (KeyError, ValueError) as exc:
            errors.append(f"{where}: {exc}")
            continue
        if record["stable_id"] in stable_ids:
            errors.append(f"{where}: duplicate stable_id {record['stable_id']!r}")
        stable_ids.add(record["stable_id"])

    for stable_id, value in (bundle["history_coverage"] or {}).items():
        _check_enum(errors, f"history_coverage[{stable_id}]", value, COVERAGE_VALUES)

    version_keys = set()
    for i, record in enumerate(bundle["versions"]):
        where = f"versions[{i}]"
        try:
            version_from_record(record)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{where}: {exc}")
            continue
        if record["stable_id"] not in stable_ids:
            errors.append(f"{where}: unknown stable_id {record['stable_id']!r}")
        key = _version_key_of_record(record)
        if key in version_keys:
            errors.append(f"{where}: duplicate version key {key[1:]}")
        version_keys.add(key)
        _check_provenance(errors, where, record, synthetic)

    evidence_ids = set()
    for i, record in enumerate(bundle["provisions"]):
        where = f"provisions[{i}]"
        _check_enum(errors, f"{where}.unit_kind", record.get("unit_kind"), UNIT_KINDS)
        _check_date(errors, f"{where}.effective_date", record.get("effective_date"))
        if not record.get("provision_key") or not isinstance(record.get("text"), str):
            errors.append(f"{where}: provision_key and text are required")
        if _version_key_of_record(record) not in version_keys:
            errors.append(f"{where}: no version {_version_key_of_record(record)[1:]} for {record.get('stable_id')!r}")
        evidence_id = record.get("evidence_id")
        if record.get("unit_kind") == "heading":
            # Heading units are never returned, so their id names no evidence. The
            # official JSON puts a chapter and a section heading on one article
            # number (제4장 and 제1절 both before 제30조), so ids built from the
            # number collide; that is the source's shape, not a bundle defect.
            if not evidence_id:
                errors.append(f"{where}: evidence_id missing")
        elif not evidence_id or evidence_id in evidence_ids:
            errors.append(f"{where}: evidence_id missing or duplicate ({evidence_id!r})")
        else:
            evidence_ids.add(evidence_id)
        if "structure_complete" in record and not isinstance(record["structure_complete"], bool):
            errors.append(f"{where}.structure_complete: {record['structure_complete']!r} is not true or false")
        if record.get("scope") is not None:
            _check_scope(errors, f"{where}.scope", record["scope"])
        _check_provenance(errors, where, record, synthetic)

    for i, record in enumerate(bundle.get("addenda") or ()):
        where = f"addenda[{i}]"
        _check_enum(errors, f"{where}.kind", record.get("kind", "other"), ADDENDUM_KINDS)
        if _version_key_of_record(record) not in version_keys:
            errors.append(f"{where}: no version {_version_key_of_record(record)[1:]} for {record.get('stable_id')!r}")

    for i, record in enumerate(bundle.get("guidance") or ()):
        where = f"guidance[{i}]"
        _check_enum(errors, f"{where}.family", record.get("family"), [f.value for f in SourceFamily])
        if record.get("edition_date") is not None:
            _check_date(errors, f"{where}.edition_date", record["edition_date"])
        if not record.get("evidence_id") or record.get("evidence_id") in evidence_ids:
            errors.append(f"{where}: evidence_id missing or duplicate ({record.get('evidence_id')!r})")
        evidence_ids.add(record.get("evidence_id"))
        if record.get("scope") is not None:
            _check_scope(errors, f"{where}.scope", record["scope"])

    for i, record in enumerate(bundle.get("faults") or ()):
        errors.extend(f"faults[{i}]: {message}" for message in _fault_errors(record))
    return errors


def _check_scope(errors: List[str], where: str, scope: Any) -> None:
    if not isinstance(scope, Mapping):
        errors.append(f"{where}: a scope is an object")
        return
    _check_enum(errors, f"{where}.condition_kind", scope.get("condition_kind", "always"), CONDITION_KINDS)


def _fault_errors(record: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    _check_enum(errors, "operation", record.get("operation"), OPERATIONS)
    _check_enum(errors, "status", record.get("status"), [s.value for s in LookupStatus])
    raw = record.get("raw_body_kind")
    if raw is not None:
        _check_enum(errors, "raw_body_kind", raw, RAW_BODY_KINDS)
        if record.get("status") in (LookupStatus.FOUND.value, LookupStatus.NOT_FOUND.value):
            errors.append(f"raw_body_kind {raw!r} describes a failed response, so status cannot be {record.get('status')!r}")
    unknown = set(record.get("match") or {}) - set(FAULT_MATCH_KEYS)
    if unknown:
        errors.append(f"match uses unknown keys {sorted(unknown)}")
    return errors


# ---------------------------------------------------------------------------
# Record conversion
# ---------------------------------------------------------------------------
def scope_from_record(record: Optional[Mapping[str, Any]]) -> Optional[Scope]:
    if record is None:
        return None
    return Scope(
        status_codes=tuple(record.get("status_codes") or ()),
        subcodes=tuple(record.get("subcodes") or ()),
        procedures=tuple(record.get("procedures") or ()),
        all_subcodes_explicit=bool(record.get("all_subcodes_explicit", False)),
        condition_kind=str(record.get("condition_kind") or "always"),
        note=str(record.get("note") or ""),
    )


def _iso(value: Any) -> Optional[str]:
    date = parse_date(value)
    return date.isoformat() if date else None


def provision_from_record(record: Mapping[str, Any]) -> ProvisionText:
    return ProvisionText(
        evidence_id=str(record["evidence_id"]),
        stable_id=str(record["stable_id"]),
        version_key=(str(record["version_id"]), _iso(record.get("effective_date"))),
        provision_key=provision_key_of(record["provision_key"]),
        heading=record.get("heading"),
        text=str(record.get("text") or ""),
        paragraphs={int(k): str(v) for k, v in (record.get("paragraphs") or {}).items()},
        items={str(k): str(v) for k, v in (record.get("items") or {}).items()},
        scope=scope_from_record(record.get("scope")),
        official_url=record.get("official_url"),
        provenance=ProvenanceStatus(record.get("provenance") or ProvenanceStatus.UNVERIFIED.value),
        structure_complete=record.get("structure_complete") is True,
    )


def addendum_from_record(record: Mapping[str, Any]) -> Addendum:
    return Addendum(
        stable_id=str(record["stable_id"]),
        version_key=(str(record["version_id"]), _iso(record.get("effective_date"))),
        text=str(record.get("text") or ""),
        kind=str(record.get("kind") or "other"),
        mentions=tuple(provision_key_of(m) for m in record.get("mentions") or ()),
    )


def guidance_from_record(record: Mapping[str, Any]) -> GuidanceItem:
    return GuidanceItem(
        evidence_id=str(record["evidence_id"]),
        family=SourceFamily(record["family"]),
        topic=str(record["topic"]),
        text=str(record.get("text") or ""),
        value=record.get("value"),
        edition_date=parse_date(record.get("edition_date")),
        review_state=str(record.get("review_state") or "unreviewed"),
        scope=scope_from_record(record.get("scope")),
    )


@dataclass(frozen=True)
class Fault:
    """One scripted failure: the first fault whose operation and match fit a call wins."""

    operation: str
    match: Mapping[str, str]
    status: LookupStatus
    raw_body_kind: Optional[str] = None
    detail: str = ""

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Fault":
        return cls(
            operation=str(record["operation"]),
            match=dict(record.get("match") or {}),
            status=LookupStatus(record["status"]),
            raw_body_kind=record.get("raw_body_kind"),
            detail=str(record.get("detail") or ""),
        )

    def matches(self, operation: str, call: Mapping[str, Optional[str]]) -> bool:
        if operation != self.operation:
            return False
        for key, expected in self.match.items():
            actual = call.get(key)
            if actual is None or _match_form(key, actual) != _match_form(key, expected):
                return False
        return True


def _match_form(key: str, value: str) -> str:
    if key == "title":
        return compact(value)
    if key == "provision_key":
        return provision_key_of(value)
    return normalize_text(value)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------
@dataclass
class _Index:
    identities: List[SourceIdentity] = field(default_factory=list)
    versions: Dict[str, List[SourceVersion]] = field(default_factory=dict)
    version_by_key: Dict[Tuple[str, VersionKey], SourceVersion] = field(default_factory=dict)
    provisions: Dict[Tuple[str, VersionKey, str], ProvisionText] = field(default_factory=dict)
    addenda: Dict[Tuple[str, VersionKey], List[Addendum]] = field(default_factory=dict)
    guidance: Dict[str, List[GuidanceItem]] = field(default_factory=dict)


class FixtureAdapter:
    """``contracts.LegalSourceAdapter`` over one validated source bundle."""

    def __init__(self, bundle: Mapping[str, Any], *, path: Optional[Path] = None) -> None:
        errors = validate_bundle(bundle)
        if errors:
            raise BundleError("; ".join(errors))
        self.bundle_id: str = str(bundle["bundle_id"])
        self.provenance = ProvenanceStatus(bundle["provenance"])
        self.attribution: str = str(bundle.get("attribution") or "")
        self.captured_at: Optional[dt.date] = parse_date(bundle.get("captured_at"))
        self.path = path
        self.title_coverage = Coverage(bundle["title_index_coverage"])
        self.history_coverage: Dict[str, Coverage] = {
            str(k): Coverage(v) for k, v in (bundle.get("history_coverage") or {}).items()
        }
        self.faults: Tuple[Fault, ...] = tuple(Fault.from_record(r) for r in bundle.get("faults") or ())
        self.call_counts: Counter = Counter()
        self._index = self._build_index(bundle)

    # -- construction -------------------------------------------------------
    @classmethod
    def from_file(cls, path: Any) -> "FixtureAdapter":
        return cls(read_bundle_file(Path(path)), path=Path(path))

    @classmethod
    def from_bundle(cls, bundle: Mapping[str, Any]) -> "FixtureAdapter":
        return cls(bundle)

    @classmethod
    def from_id(cls, bundle_id: str, root: Optional[Path] = None) -> "FixtureAdapter":
        return cls(load_bundle(bundle_id, root), path=bundle_path(bundle_id, root))

    @staticmethod
    def _build_index(bundle: Mapping[str, Any]) -> _Index:
        index = _Index(identities=[identity_from_record(r) for r in bundle["identities"]])
        for record in bundle["versions"]:
            version = version_from_record(record)
            index.versions.setdefault(version.stable_id, []).append(version)
            index.version_by_key[(version.stable_id, version.key)] = version
        for stable_id, versions in index.versions.items():
            index.versions[stable_id] = sort_versions(versions)
        for record in bundle["provisions"]:
            if record.get("unit_kind") == "heading":
                continue  # 조문여부 = 전문: a chapter heading, never a provision
            provision = provision_from_record(record)
            index.provisions[(provision.stable_id, provision.version_key, provision.provision_key)] = provision
        for record in bundle.get("addenda") or ():
            addendum = addendum_from_record(record)
            index.addenda.setdefault((addendum.stable_id, addendum.version_key), []).append(addendum)
        for record in bundle.get("guidance") or ():
            item = guidance_from_record(record)
            index.guidance.setdefault(normalize_text(item.topic), []).append(item)
        return index

    # -- bookkeeping --------------------------------------------------------
    @property
    def identities(self) -> Tuple[SourceIdentity, ...]:
        return tuple(self._index.identities)

    @property
    def total_calls(self) -> int:
        return sum(self.call_counts.values())

    def reset_counts(self) -> None:
        self.call_counts.clear()

    def known_titles(self) -> Tuple[str, ...]:
        """Every title the bundle's index answers to (for citation scanning of free text)."""
        current_only = self.title_coverage is Coverage.PARTIAL
        titles: List[str] = []
        for identity in self._index.identities:
            titles.extend((identity.official_title,) + identity.short_titles)
            if not current_only:
                titles.extend(identity.former_titles)
        return tuple(titles)

    def _begin(self, operation: str, **call: Optional[str]) -> Optional[LookupResult]:
        """Count the call; return the scripted fault result if one applies."""
        self.call_counts[operation] += 1
        for fault in self.faults:
            if fault.matches(operation, call):
                detail = f"scripted fault ({fault.raw_body_kind or 'status'}): {fault.detail}".strip()
                return LookupResult(status=fault.status, coverage=Coverage.PARTIAL, detail=detail, calls=1)
        return None

    # -- LegalSourceAdapter -------------------------------------------------
    def resolve_title(self, title: str, *, as_of: Optional[dt.date] = None) -> Tuple[LookupResult, List[SourceIdentity]]:
        """Exact title resolution. ``as_of`` is accepted for the protocol; a bundle index is not dated."""
        fault = self._begin("resolve_title", title=title)
        if fault is not None:
            return fault, []
        current_only = self.title_coverage is Coverage.PARTIAL
        found = exact_matches(self._index.identities, title, current_only=current_only)
        if found:
            return LookupResult(LookupStatus.FOUND, self.title_coverage, calls=1), found
        near = near_matches(self._index.identities, title, current_only=current_only)
        detail = ("near matches (not used): " + ", ".join(near)) if near else "no exact title match"
        return LookupResult(LookupStatus.NOT_FOUND, self.title_coverage, detail=detail, calls=1), []

    def list_versions(self, stable_id: str) -> Tuple[LookupResult, List[SourceVersion]]:
        fault = self._begin("list_versions", stable_id=stable_id)
        if fault is not None:
            return fault, []
        coverage = self.history_coverage.get(stable_id, Coverage.PARTIAL)
        versions = list(self._index.versions.get(stable_id, ()))
        if not versions:
            return LookupResult(LookupStatus.NOT_FOUND, coverage, detail="no versions in bundle", calls=1), []
        return LookupResult(LookupStatus.FOUND, coverage, calls=1), versions

    def get_provision(
        self, stable_id: str, version_key: VersionKey, provision: ProvisionRef
    ) -> Tuple[LookupResult, Optional[ProvisionText]]:
        key = provision_key_of(provision.article_key())
        fault = self._begin("get_provision", stable_id=stable_id, provision_key=key)
        if fault is not None:
            return fault, None
        version_key = (str(version_key[0]), version_key[1])
        found = self._index.provisions.get((stable_id, version_key, key))
        version = self._index.version_by_key.get((stable_id, version_key))
        if found is not None:
            coverage = Coverage.COMPLETE if version and version.parse_status is ParseStatus.COMPLETE else Coverage.PARTIAL
            return LookupResult(LookupStatus.FOUND, coverage, calls=1), found
        if version is None:
            return LookupResult(LookupStatus.NOT_FOUND, Coverage.PARTIAL, detail="version not in bundle", calls=1), None
        if version.parse_status is ParseStatus.COMPLETE:
            return LookupResult(LookupStatus.NOT_FOUND, Coverage.COMPLETE, detail=f"{key} not in version", calls=1), None
        detail = f"{key} not captured; version parse_status is {version.parse_status.value}"
        return LookupResult(LookupStatus.NOT_FOUND, Coverage.PARTIAL, detail=detail, calls=1), None

    def get_addenda(self, stable_id: str, version_key: VersionKey) -> Tuple[LookupResult, List[Addendum]]:
        fault = self._begin("get_addenda", stable_id=stable_id)
        if fault is not None:
            return fault, []
        version_key = (str(version_key[0]), version_key[1])
        version = self._index.version_by_key.get((stable_id, version_key))
        read = version is not None and version.has_transitional_provisions is not None
        coverage = Coverage.COMPLETE if read else Coverage.PARTIAL
        addenda = list(self._index.addenda.get((stable_id, version_key), ()))
        if not addenda:
            detail = "no addenda recorded" if read else "부칙 not read for this version"
            return LookupResult(LookupStatus.NOT_FOUND, coverage, detail=detail, calls=1), []
        return LookupResult(LookupStatus.FOUND, coverage, calls=1), addenda

    def guidance(self, topic: str) -> Tuple[LookupResult, List[GuidanceItem]]:
        fault = self._begin("guidance", topic=topic, title=topic)
        if fault is not None:
            return fault, []
        items = list(self._index.guidance.get(normalize_text(topic), ()))
        if not items:
            return LookupResult(LookupStatus.NOT_FOUND, Coverage.COMPLETE, detail="no guidance on topic", calls=1), []
        return LookupResult(LookupStatus.FOUND, Coverage.COMPLETE, calls=1), items

    # -- convenience for tests and the evidence package --------------------
    def identity(self, stable_id: str) -> Optional[SourceIdentity]:
        for identity in self._index.identities:
            if identity.stable_id == stable_id:
                return identity
        return None

    def version(self, stable_id: str, version_key: VersionKey) -> Optional[SourceVersion]:
        return self._index.version_by_key.get((stable_id, (str(version_key[0]), version_key[1])))


__all__ = [
    "ADDENDUM_KINDS",
    "BUNDLE_PROVENANCE",
    "BundleError",
    "DEFAULT_SOURCES_DIR",
    "FAULT_MATCH_KEYS",
    "Fault",
    "FixtureAdapter",
    "OPERATIONS",
    "OPTIONAL_BUNDLE_KEYS",
    "RAW_BODY_DEFAULT_STATUS",
    "RAW_BODY_KINDS",
    "REQUIRED_BUNDLE_KEYS",
    "UNIT_KINDS",
    "addendum_from_record",
    "bundle_path",
    "guidance_from_record",
    "load_bundle",
    "provision_from_record",
    "read_bundle_file",
    "scope_from_record",
    "validate_bundle",
]
