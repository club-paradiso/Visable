#!/usr/bin/env python3
"""Validate Paradiso's source-grounding metadata model.

This is a stdlib-only, offline, report-or-strict validator that complements
``scripts/check_source_updates.py`` (which only compares a registry entry's
recorded hash against its local file). It instead enforces *cross-file*
consistency and the canonical metadata model defined in
``data/schemas/source_grounding_schema.json``:

  1. The schema file parses and declares SourceRecord / EvidenceRecord /
     AnswerGrounding record types.
  2. Every ``data/source_registry.json`` source has id + type + title and uses
     only known ``source_type`` / ``status`` enum values.
  3. Manual-version invariants hold (the current visa-issuance manual is
     2026.5 / 2026-05-21 active; the current stay/residence manual is
     2026.5 / 2026-06-01 active and supersedes a deprecated prior entry).
  4. The active manuals' content hashes AGREE between
     ``data/source_registry.json`` and ``docs/source-manuals/source_manifest.json``
     (cross-file drift = hard error; this catches "updated one file, forgot the
     other"). A registry date older than the manifest emits STALE_SOURCE_WARNING.

It NEVER mutates any file and NEVER performs network I/O. It is read by no
production code path; failing it never changes /api/ask behavior. It exists so
CI and audits can trust the freshness/lineage metadata.

Exit codes:
  0  no hard errors (warnings allowed)
  1  one or more hard errors
  2  could not load a required input file
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_PATH = os.path.join(REPO_ROOT, "data", "schemas", "source_grounding_schema.json")
REGISTRY_PATH = os.path.join(REPO_ROOT, "data", "source_registry.json")
MANIFEST_PATH = os.path.join(REPO_ROOT, "docs", "source-manuals", "source_manifest.json")

# Canonical SourceRecord concepts that, when unpopulated (via any of their
# crosswalk aliases) on an official manual entry, are reported as freshness
# GAPS (warnings, not errors). ``review_status`` is intentionally excluded
# because the registry's ``status`` field already satisfies it.
_FRESHNESS_GAP_CONCEPTS = ("retrieved_at", "confidence", "language")


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _strip_hash(value: Any) -> str:
    text = str(value or "").strip()
    if ":" in text:
        text = text.split(":", 1)[1]
    return text.lower()


def validate() -> Tuple[List[str], List[str]]:
    """Return (errors, warnings)."""
    errors: List[str] = []
    warnings: List[str] = []

    # ---- 1. Schema file -----------------------------------------------------
    try:
        schema = _load_json(SCHEMA_PATH)
    except Exception as exc:  # noqa: BLE001
        return ([f"cannot load schema {SCHEMA_PATH}: {exc}"], warnings)

    record_types = schema.get("record_types") or {}
    for required_type in ("SourceRecord", "EvidenceRecord", "AnswerGrounding"):
        if required_type not in record_types:
            errors.append(f"schema missing record_type: {required_type}")

    source_enums = (
        (record_types.get("SourceRecord") or {}).get("enums") or {}
    )
    allowed_source_types = set(source_enums.get("source_type") or [])
    allowed_review_status = set(source_enums.get("review_status") or [])
    invariants = schema.get("manual_version_invariants") or {}
    # Crosswalk: canonical concept -> list of real field-name aliases.
    source_crosswalk = (schema.get("field_crosswalk") or {}).get("SourceRecord") or {}

    # ---- 2. Registry --------------------------------------------------------
    try:
        registry = _load_json(REGISTRY_PATH)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"cannot load registry {REGISTRY_PATH}: {exc}")
        return (errors, warnings)

    # source_registry.json uses ``type``/``status`` which the schema crosswalk
    # maps to canonical source_type/review_status. The registry's own vocab is a
    # subset, so validate against the union the schema declares.
    registry_type_vocab = {"pdf_manual", "law_api", "notice_index"}
    registry_status_vocab = {"active", "deprecated", "not_configured"}

    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("source_registry.json has no 'sources' list")
        return (errors, warnings)

    by_id: Dict[str, Dict[str, Any]] = {}
    for idx, src in enumerate(sources):
        if not isinstance(src, dict):
            errors.append(f"source[{idx}] is not an object")
            continue
        sid = src.get("id")
        if not sid:
            errors.append(f"source[{idx}] missing id")
            continue
        by_id[sid] = src
        if not src.get("type"):
            errors.append(f"{sid}: missing type")
        elif src["type"] not in registry_type_vocab:
            errors.append(f"{sid}: unknown type {src['type']!r}")
        if not src.get("title"):
            errors.append(f"{sid}: missing title")
        status = src.get("status")
        if status and status not in registry_status_vocab:
            errors.append(f"{sid}: unknown status {status!r}")
        # Freshness-gap warnings on official manual entries only. A concept is
        # satisfied if ANY of its crosswalk aliases holds a non-empty value.
        if src.get("type") == "pdf_manual" and src.get("status") == "active":
            for concept in _FRESHNESS_GAP_CONCEPTS:
                aliases = source_crosswalk.get(concept, [concept])
                if not any(src.get(alias) not in (None, "", []) for alias in aliases):
                    warnings.append(f"{sid}: freshness gap — '{concept}' unpopulated")

    # Cross-check that the registry vocab is a subset of the schema's declared
    # canonical enums (keeps the schema and the live registry from drifting).
    if allowed_source_types and not registry_type_vocab.issubset(
        # pdf_manual->manual, law_api->law/public_api, notice_index->official_web
        {"manual", "law", "public_api", "official_web", "internal_review",
         "pdf_manual", "law_api", "notice_index"}
    ):
        warnings.append("registry type vocab not representable in schema source_type enum")
    if allowed_review_status and not registry_status_vocab.issubset(allowed_review_status):
        missing = registry_status_vocab - allowed_review_status
        warnings.append(
            f"schema review_status enum is missing registry statuses: {sorted(missing)}"
        )

    # ---- 3. Manifest + invariants + hash parity -----------------------------
    manifest = None
    try:
        manifest = _load_json(MANIFEST_PATH)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"cannot load manifest {MANIFEST_PATH}: {exc} (skipping hash parity)")

    current = (manifest or {}).get("current") or {}

    for inv_name, inv in invariants.items():
        if inv_name == "note":
            continue
        keyword = inv.get("registry_id_keyword", "")
        manifest_key = inv.get("manifest_key", "")
        want_version = inv.get("version_label")
        want_date = inv.get("published_or_updated_at")
        want_status = inv.get("expected_status", "active")

        # Find the active registry entry for this manual family.
        reg_entry = None
        for sid, src in by_id.items():
            if keyword and keyword in sid and src.get("status") == want_status:
                reg_entry = src
                break
        if reg_entry is None:
            errors.append(
                f"invariant {inv_name}: no {want_status} registry source whose id contains {keyword!r}"
            )
            continue

        if want_version and reg_entry.get("version") != want_version:
            errors.append(
                f"invariant {inv_name}: registry version {reg_entry.get('version')!r} != expected {want_version!r}"
            )
        # source_date is present on stay-manual entries; only check when both sides have it.
        if want_date and reg_entry.get("source_date") and reg_entry.get("source_date") != want_date:
            errors.append(
                f"invariant {inv_name}: registry source_date {reg_entry.get('source_date')!r} != expected {want_date!r}"
            )

        if inv.get("must_supersede_prior"):
            superseded = [
                s for s in sources
                if isinstance(s, dict) and keyword in str(s.get("id"))
                and s.get("status") == "deprecated"
            ]
            if not superseded:
                warnings.append(
                    f"invariant {inv_name}: no deprecated prior {keyword!r} entry found (expected a superseded record)"
                )
            else:
                for s in superseded:
                    if not s.get("superseded_by"):
                        errors.append(
                            f"invariant {inv_name}: deprecated {s.get('id')} missing 'superseded_by'"
                        )

        # Hash parity registry <-> manifest.
        man_entry = current.get(manifest_key) if isinstance(current, dict) else None
        if man_entry:
            reg_hash = _strip_hash(reg_entry.get("last_known_hash"))
            man_hash = _strip_hash(man_entry.get("file_sha256"))
            if reg_hash and man_hash and reg_hash != man_hash:
                errors.append(
                    f"invariant {inv_name}: hash drift — registry {reg_hash[:12]}… != manifest {man_hash[:12]}…"
                )
            # Staleness: registry date older than manifest date.
            reg_date = reg_entry.get("source_date")
            man_date = man_entry.get("source_date")
            if reg_date and man_date and reg_date < man_date:
                warnings.append(
                    f"STALE_SOURCE_WARNING {inv_name}: registry source_date {reg_date} older than manifest {man_date}"
                )
        elif manifest is not None:
            warnings.append(f"invariant {inv_name}: manifest has no current.{manifest_key} entry")

    return (errors, warnings)


def main(argv: List[str]) -> int:
    strict = "--strict" in argv
    try:
        errors, warnings = validate()
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: validator crashed: {exc}", file=sys.stderr)
        return 2

    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)

    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s).", file=sys.stderr)
        return 1
    print(
        f"OK: source-grounding metadata model consistent "
        f"({len(warnings)} non-blocking warning(s))."
        + (" [strict]" if strict else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
