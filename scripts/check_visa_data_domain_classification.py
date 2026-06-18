#!/usr/bin/env python3
"""Read-only validator for the visa_data domain classification artifact
(PR E-0). No dependencies; never modifies any file.

Fails only on:
  * malformed / missing classification file
  * a visa_data.json code missing from the classification
  * an extra/duplicate code in the classification
  * an unknown primary_type or source_grounding label

It does NOT enforce any particular classification value per record, and it
does NOT touch production data — it only checks that the classification file
stays structurally consistent with visa_data.json so the future migration
plan cannot silently drift.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VISA = ROOT / "visa_data.json"
# Refreshed for the post-PR #440 generated 42-record master. The prior
# 2026_05_21 snapshot classified the old 58/59-record file (17 scenario/help
# records still inside the master) and no longer lines up by (array_index, code).
# See scripts/visa/refresh_domain_classification.py.
CLASS = ROOT / "docs/data/2026_06_18_visa_data_domain_classification.json"

VALID_PRIMARY = {
    "visa_status", "stay_status", "visa_track", "special_program",
    "procedure_helper", "faq", "scenario", "risk_warning",
    "insurance_or_utility", "ai_grounding_helper", "unknown",
}
VALID_GROUNDING = {
    "manual_grounded", "partially_manual_grounded", "non_manual_operational",
    "scenario_policy_sensitive", "needs_separate_source",
    "should_not_be_in_visa_master", "unresolved",
}
REQUIRED_FIELDS = {
    "array_index", "code", "primary_type", "source_grounding",
    "keep_in_visa_data", "future_destination",
}


def fail(msg: str) -> None:
    raise SystemExit(f"[check_visa_data_domain_classification] ERROR: {msg}")


def main() -> None:
    if not CLASS.exists():
        fail(f"classification file not found: {CLASS.relative_to(ROOT)}")
    try:
        doc = json.loads(CLASS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"malformed classification JSON at line {exc.lineno}: {exc.msg}")

    records = doc.get("records")
    if not isinstance(records, list) or not records:
        fail("classification.records must be a non-empty list")

    # field + label validity
    for r in records:
        missing = sorted(REQUIRED_FIELDS - set(r))
        if missing:
            fail(f"record {r.get('code')!r} missing field(s): {', '.join(missing)}")
        if r["primary_type"] not in VALID_PRIMARY:
            fail(f"record {r['code']!r}: unknown primary_type {r['primary_type']!r}")
        if r["source_grounding"] not in VALID_GROUNDING:
            fail(f"record {r['code']!r}: unknown source_grounding {r['source_grounding']!r}")

    # coverage vs visa_data.json — match on (array_index, code) so the
    # duplicate D-4-2K code (indices 24 & 55) is handled correctly.
    visas = json.loads(VISA.read_text(encoding="utf-8"))
    vd_keys = {(i, r.get("code")) for i, r in enumerate(visas)}
    cl_pairs = [(r["array_index"], r["code"]) for r in records]
    cl_keys = set(cl_pairs)

    dupes = [k for k, n in Counter(cl_pairs).items() if n != 1]
    if dupes:
        fail(f"duplicate (array_index, code) entries in classification: {dupes}")

    missing_from_class = sorted(vd_keys - cl_keys)
    if missing_from_class:
        fail(f"visa_data.json codes missing from classification: {missing_from_class}")
    extra_in_class = sorted(cl_keys - vd_keys)
    if extra_in_class:
        fail(f"classification has codes not in visa_data.json: {extra_in_class}")

    print(f"[check_visa_data_domain_classification] OK - {len(records)} records "
          "classified; every visa_data.json code covered; no duplicates; "
          "all primary_type/source_grounding labels valid.")


if __name__ == "__main__":
    main()
