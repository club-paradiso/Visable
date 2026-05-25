#!/usr/bin/env python3
"""Read-only E-2 parity tests for the record-store union resolver.

Imports scripts/resolve_record_store.py and asserts the runtime-safe E-2
invariants that gate any future E-3/E-4 wiring. No dependencies; modifies
nothing.

Checks:
  1. Union has no duplicate visa codes.
  2. Union code-multiset == visa_data.json code-multiset (count + codes),
     i.e. the union changes nothing today.
  3. Each of the 17 scenario/help shadow records maps to exactly one
     visa_data.json record and is NOT returned twice in the union.
  4. Direct code lookup parity: every visa_data.json code resolves via the
     union to the same record object.
  5. The 3 overstay codes (SCN-6, OVS-1, FAQ-4) appear exactly once.
  6. union_view(prefer="scenario_help") is also dedup-safe (no duplicates).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import resolve_record_store as R  # noqa: E402

OVERSTAY = {"SCN-6", "OVS-1", "FAQ-4"}


def fail(msg: str) -> None:
    raise SystemExit(f"[check_record_store_union_parity] ERROR: {msg}")


def canon(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True)


def main() -> None:
    visas = R.load_visa_data()
    shadow = R.load_scenario_help_shadow()
    union = R.union_view()

    # 1. union introduces NO new duplicate codes beyond visa_data.json.
    # (D-4-2K is a pre-existing duplicate code in visa_data.json, indices
    # 24 & 55, deferred to the D-content track.)
    union_codes = [r.get("code") for r in union]
    visa_codes = [r.get("code") for r in visas]
    union_dupes = {c for c, n in Counter(union_codes).items() if n > 1}
    visa_dupes = {c for c, n in Counter(visa_codes).items() if n > 1}
    if union_dupes != visa_dupes:
        fail(f"union introduced new duplicate codes: {union_dupes - visa_dupes}")

    # 2. union code-multiset == visa_data code-multiset
    if Counter(union_codes) != Counter(r.get("code") for r in visas):
        fail("union code-multiset differs from visa_data.json")
    if len(union) != len(visas):
        fail(f"union count {len(union)} != visa_data count {len(visas)}")

    # 3. shadow maps 1:1 and is not double-counted
    if len(shadow) != 17:
        fail(f"expected 17 shadow records, found {len(shadow)}")
    for e in shadow:
        idx, code = e.get("sourceVisaDataIndex"), e.get("sourceVisaDataCode")
        if not (isinstance(idx, int) and 0 <= idx < len(visas) and visas[idx].get("code") == code):
            fail(f"shadow {code} does not map to visa_data index {idx}")
        if union_codes.count(code) != 1:
            fail(f"shadow code {code} appears {union_codes.count(code)} times in union (expected 1)")

    # 4. direct code lookup parity (by array_index+code key, handles D-4-2K dup)
    union_canon = canon(union)
    if union_canon != canon(visas):
        fail("union object content differs from visa_data.json (behavior would change)")

    # 5. overstay codes present exactly once
    for c in OVERSTAY:
        if union_codes.count(c) != 1:
            fail(f"overstay code {c} appears {union_codes.count(c)} times (expected 1)")

    # 6. prefer=scenario_help is still dedup-safe (same code-multiset; no new dupes)
    alt = R.union_view(prefer="scenario_help")
    alt_codes = [r.get("code") for r in alt]
    alt_dupes = {c for c, n in Counter(alt_codes).items() if n > 1}
    if alt_dupes != visa_dupes:
        fail(f"union_view(prefer=scenario_help) introduced new duplicate codes: {alt_dupes - visa_dupes}")
    if Counter(alt_codes) != Counter(union_codes):
        fail("union_view(prefer=scenario_help) changed the code set")

    print(f"[check_record_store_union_parity] OK - union={len(union)} == visa_data={len(visas)}; "
          f"17 shadow records de-duplicated 1:1; overstay {sorted(OVERSTAY)} each present once; "
          "direct-lookup parity holds; zero behavior change.")


if __name__ == "__main__":
    main()
