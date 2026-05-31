#!/usr/bin/env python3
"""Validator for the 2026-05 structured manual-evidence requirements layer.

Usage:
    python3 scripts/validate_structured_requirements.py \
        backend/data/manual_grounding/structured_requirements_2026_05.json

Exits non-zero on any structural violation. Prints summary counts by
statusCode, procedureType, boundaryType, confidence, and readinessLabel.

This layer is candidate manual evidence, NOT user-facing production data.
The validator enforces the structural and boundary-safety invariants that
keep sub-code / scenario / conditional evidence from being mislabelled as
universal, and that keep visa-issuance evidence from being merged with
stay/residence procedure evidence.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ALLOWED_PROCEDURE_TYPES = {
    "visa_issuance",
    "registration",
    "extension",
    "change_of_status",
    "activity_outside_status",
    "workplace_change_or_addition",
    "status_grant",
    "reentry",
    "reporting_duty",
    "other",
}

ALLOWED_BOUNDARY_TYPES = {
    "parent_code_level",
    "universal",
    "sub_code_specific",
    "scenario_specific",
    "conditional",
    "procedure_specific",
    "unclear",
}

ALLOWED_CONFIDENCE = {"LOW", "MEDIUM", "HIGH"}

ALLOWED_READINESS = {
    "STRUCTURED_EVIDENCE_READY",
    "NEEDS_PAGE_CITATION",
    "NEEDS_SUBCODE_REVIEW",
    "NEEDS_SCENARIO_REVIEW",
    "SCHEMA_GAP",
    "DO_NOT_USE",
}

# Procedure types that belong to the stay/residence manual (post-entry
# in-country procedures). visa_issuance belongs to the visa manual.
STAY_RESIDENCE_PROCEDURES = {
    "registration",
    "extension",
    "change_of_status",
    "activity_outside_status",
    "workplace_change_or_addition",
    "status_grant",
    "reentry",
    "reporting_duty",
}

# Document-level boundaries that contradict a universal/parent claim.
NON_UNIVERSAL_DOC_BOUNDARIES = {"sub_code_specific", "scenario_specific", "conditional"}


def _is_visa_manual(path: str) -> bool:
    return "visa_manual" in (path or "")


def _is_stay_manual(path: str) -> bool:
    return "stay_manual" in (path or "")


def validate(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: invalid JSON syntax: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []

    # Required top-level fields.
    for field in ("schemaVersion", "entryCount", "entries"):
        if field not in data:
            errors.append(f"top-level: missing required field '{field}'")
    entries = data.get("entries")
    if not isinstance(entries, list):
        print("FAIL: 'entries' must be a list", file=sys.stderr)
        return 1
    if isinstance(data.get("entryCount"), int) and data["entryCount"] != len(entries):
        errors.append(
            f"top-level: entryCount ({data['entryCount']}) != len(entries) ({len(entries)})"
        )

    by_status = collections.Counter()
    by_proc = collections.Counter()
    by_boundary = collections.Counter()
    by_conf = collections.Counter()
    by_ready = collections.Counter()
    doc_item_total = 0

    for i, e in enumerate(entries):
        tag = f"entries[{i}]"
        if not isinstance(e, dict):
            errors.append(f"{tag}: entry must be an object")
            continue

        status = e.get("statusCode")
        if not status or not isinstance(status, str):
            errors.append(f"{tag}: missing/invalid statusCode")
        else:
            by_status[status] += 1

        proc = e.get("procedureType")
        if proc not in ALLOWED_PROCEDURE_TYPES:
            errors.append(f"{tag} ({status}): invalid procedureType '{proc}'")
        else:
            by_proc[proc] += 1

        boundary = e.get("boundaryType")
        if boundary not in ALLOWED_BOUNDARY_TYPES:
            errors.append(f"{tag} ({status}): invalid boundaryType '{boundary}'")
        else:
            by_boundary[boundary] += 1

        conf = e.get("confidence")
        if conf not in ALLOWED_CONFIDENCE:
            errors.append(f"{tag} ({status}): invalid confidence '{conf}'")
        else:
            by_conf[conf] += 1

        ready = e.get("readinessLabel")
        if ready not in ALLOWED_READINESS:
            errors.append(f"{tag} ({status}): invalid readinessLabel '{ready}'")
        else:
            by_ready[ready] += 1

        # manualSource + page consistency.
        ms = e.get("manualSource") or {}
        ps, pe = ms.get("pageStart"), ms.get("pageEnd")
        if ps is not None and pe is not None:
            if not isinstance(ps, int) or not isinstance(pe, int):
                errors.append(f"{tag} ({status}): pageStart/pageEnd must be ints when present")
            elif ps > pe:
                errors.append(f"{tag} ({status}): pageStart {ps} > pageEnd {pe}")

        # Documents must have textKo.
        docs = e.get("documents")
        if not isinstance(docs, list):
            errors.append(f"{tag} ({status}): documents must be a list")
            docs = []
        for j, d in enumerate(docs):
            doc_item_total += 1
            if not isinstance(d, dict) or not d.get("textKo"):
                errors.append(f"{tag} ({status}).documents[{j}]: missing textKo")

        # Boundary-safety: an entry claiming universal/parent must not carry
        # sub-code/scenario/conditional document boundaries or review labels.
        if boundary in ("universal", "parent_code_level"):
            bad = [d.get("boundary") for d in docs
                   if isinstance(d, dict) and d.get("boundary") in NON_UNIVERSAL_DOC_BOUNDARIES]
            if bad:
                errors.append(
                    f"{tag} ({status}): boundaryType={boundary} but document boundaries "
                    f"include {sorted(set(bad))} (would over-generalize)"
                )
            if ready in ("NEEDS_SUBCODE_REVIEW", "NEEDS_SCENARIO_REVIEW"):
                errors.append(
                    f"{tag} ({status}): boundaryType={boundary} contradicts readinessLabel={ready}"
                )

        # Visa-issuance vs stay/residence separation.
        detected = e.get("procedureTypesDetected") or [proc]
        f = ms.get("file", "")
        if proc == "visa_issuance" and _is_stay_manual(f):
            errors.append(f"{tag} ({status}): visa_issuance entry sourced from stay manual")
        if proc in STAY_RESIDENCE_PROCEDURES and _is_visa_manual(f):
            errors.append(
                f"{tag} ({status}): stay/residence procedure '{proc}' sourced from visa manual"
            )
        # An entry must derive from a single manual file (never both manuals).
        if _is_visa_manual(f) and _is_stay_manual(f):
            errors.append(f"{tag} ({status}): manualSource.file references both manuals")

    if errors:
        print(f"FAIL: {len(errors)} structural error(s):", file=sys.stderr)
        for msg in errors[:200]:
            print(f"  - {msg}", file=sys.stderr)
        return 1

    print(f"PASS: {path}")
    print(f"  entries: {len(entries)}")
    print(f"  document items: {doc_item_total}")
    print(f"  statuses represented: {len(by_status)}")
    print(f"  by procedureType: {dict(by_proc)}")
    print(f"  by boundaryType: {dict(by_boundary)}")
    print(f"  by confidence: {dict(by_conf)}")
    print(f"  by readinessLabel: {dict(by_ready)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to structured_requirements_*.json")
    args = parser.parse_args(argv)
    return validate(Path(args.path))


if __name__ == "__main__":
    raise SystemExit(main())
