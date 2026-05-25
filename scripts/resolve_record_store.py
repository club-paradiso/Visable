#!/usr/bin/env python3
"""Read-only union resolver (E-1 preview of the E-2 runtime resolver).

Produces a union view of visa_data.json and data/scenario_help_records.json
for parity inspection. It is NOT wired into the app or backend runtime in
E-1; it exists so future PRs (E-2) and parity tests can compare a merged
view against the current visa_data.json-only behavior.

Resolution rule (preview): records are keyed by (array_index, code). The
scenario/help store currently holds duplicates of visa_data.json records, so
the union equals visa_data.json today (zero behavior change). This script
just demonstrates and verifies that invariant.

Usage:
    python3 scripts/resolve_record_store.py            # prints a summary
    python3 scripts/resolve_record_store.py --json     # prints union as JSON
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_visa_data():
    return json.loads((ROOT / "visa_data.json").read_text(encoding="utf-8"))


def load_scenario_help():
    p = ROOT / "data/scenario_help_records.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("records", [])


def union_view():
    """Return the merged record list (read-only).

    Today the scenario/help store only duplicates visa_data.json records, so
    the union is exactly visa_data.json. This function is the single place a
    future E-2 runtime resolver would grow to prefer the scenario/help store
    for migrated records.
    """
    visas = load_visa_data()
    by_key = {(i, r.get("code")): r for i, r in enumerate(visas)}
    for entry in load_scenario_help():
        key = (entry.get("sourceVisaDataIndex"), entry.get("sourceVisaDataCode"))
        # E-1: duplicates only — do not override; just confirm presence.
        by_key.setdefault(key, entry.get("record"))
    return [by_key[k] for k in sorted(by_key, key=lambda k: k[0])]


def main() -> None:
    visas = load_visa_data()
    union = union_view()
    same = json.dumps(union, ensure_ascii=False, sort_keys=True) == \
        json.dumps(visas, ensure_ascii=False, sort_keys=True)
    if "--json" in sys.argv:
        print(json.dumps(union, ensure_ascii=False, indent=2))
        return
    print(f"visa_data records: {len(visas)}")
    print(f"scenario_help duplicated records: {len(load_scenario_help())}")
    print(f"union records: {len(union)}")
    print(f"union == visa_data.json (E-1 zero-behavior-change invariant): {same}")


if __name__ == "__main__":
    main()
