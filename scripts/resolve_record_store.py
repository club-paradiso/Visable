#!/usr/bin/env python3
"""Read-only record-store union resolver (E-2).

Provides a deterministic, importable union view of:
  * visa_data.json                     — the live canonical record master
  * data/scenario_help_records.json    — E-1 shadow copies of 17 records

E-2 contract (runtime-safe, zero behavior change):
  * visa_data.json is CANONICAL. The scenario/help store currently holds
    byte-for-byte SHADOW copies of records that still live in visa_data.json,
    so the union MUST NOT return duplicates and MUST equal visa_data.json
    today. The resolver de-duplicates by keying on (array_index, code) and
    never overrides a canonical record with its shadow during E-2.
  * The shadow store is exposed only as METADATA (which codes have a shadow,
    and whether removal is gated) — runtime record content stays canonical.
  * This module is NOT wired into the backend `/api/visas` endpoint or the
    frontend in E-2 (see the E-2 report). It exists so E-2 parity tests and a
    future E-3 runtime resolver can rely on one deterministic implementation.

Usage:
    python3 scripts/resolve_record_store.py            # summary + invariant
    python3 scripts/resolve_record_store.py --json     # union as JSON
    python3 scripts/resolve_record_store.py --check    # assert E-2 invariants
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VISA_DATA = ROOT / "visa_data.json"
SCENARIO_HELP = ROOT / "data/scenario_help_records.json"


def load_visa_data():
    """Canonical live records (list, in file order)."""
    return json.loads(VISA_DATA.read_text(encoding="utf-8"))


def load_scenario_help_shadow():
    """E-1 shadow entries (list of envelope objects with a nested `record`)."""
    if not SCENARIO_HELP.exists():
        return []
    return json.loads(SCENARIO_HELP.read_text(encoding="utf-8")).get("records", [])


def shadow_index():
    """Map (array_index, code) -> shadow metadata (no record content)."""
    out = {}
    for e in load_scenario_help_shadow():
        key = (e.get("sourceVisaDataIndex"), e.get("sourceVisaDataCode"))
        out[key] = {
            "migrationStatus": e.get("migrationStatus"),
            "plannedCanonicalStore": e.get("plannedCanonicalStore"),
            "removalFromVisaDataAllowed": e.get("removalFromVisaDataAllowed"),
            "requiresParityBeforeRemoval": e.get("requiresParityBeforeRemoval"),
            "overstay_related": e.get("overstay_related"),
        }
    return out


def union_view(prefer: str = "visa_data"):
    """Deterministic de-duplicated union of canonical + shadow records.

    During E-2 `prefer` is always "visa_data": the canonical record wins and
    shadow copies (which duplicate canonical records) are NOT appended, so the
    union is exactly visa_data.json. The `prefer` arg is a seam for the future
    E-3/E-4 resolver, where shadow records may become authoritative.
    """
    visas = load_visa_data()
    by_key = {(i, r.get("code")): r for i, r in enumerate(visas)}
    order = [(i, r.get("code")) for i, r in enumerate(visas)]

    for e in load_scenario_help_shadow():
        key = (e.get("sourceVisaDataIndex"), e.get("sourceVisaDataCode"))
        if key in by_key:
            # Shadow duplicates a canonical record -> de-dup; keep canonical.
            if prefer == "scenario_help":
                by_key[key] = e.get("record")
            continue
        # Not present canonically (would only happen post E-4): include it.
        by_key[key] = e.get("record")
        order.append(key)

    return [by_key[k] for k in order]


def _dupe_codes(records):
    counts = {}
    for r in records:
        c = r.get("code")
        counts[c] = counts.get(c, 0) + 1
    return sorted(c for c, n in counts.items() if n > 1)


def parity_report():
    visas = load_visa_data()
    shadow = load_scenario_help_shadow()
    union = union_view()
    canon = lambda o: json.dumps(o, ensure_ascii=False, sort_keys=True)
    # Note: D-4-2K is a pre-existing duplicate code in visa_data.json
    # (indices 24 & 55), deferred to the D-content track. The E-2 invariant
    # is that the union introduces NO new duplicate codes beyond visa_data.
    return {
        "visa_data_count": len(visas),
        "scenario_help_shadow_count": len(shadow),
        "union_count": len(union),
        "union_equals_visa_data": canon(union) == canon(visas),
        "duplicate_codes_in_union": _dupe_codes(union),
        "duplicate_codes_in_visa_data": _dupe_codes(visas),
        "shadow_codes": sorted(e.get("sourceVisaDataCode") for e in shadow),
    }


def main() -> None:
    if "--json" in sys.argv:
        print(json.dumps(union_view(), ensure_ascii=False, indent=2))
        return
    rep = parity_report()
    if "--check" in sys.argv:
        assert rep["union_equals_visa_data"], "union != visa_data.json (E-2 invariant broken)"
        assert rep["duplicate_codes_in_union"] == rep["duplicate_codes_in_visa_data"], \
            f"union introduced new duplicate codes: {set(rep['duplicate_codes_in_union']) - set(rep['duplicate_codes_in_visa_data'])}"
        assert rep["union_count"] == rep["visa_data_count"], "union count drifted from visa_data"
        print("[resolve_record_store] OK - E-2 invariants hold "
              f"(union=={rep['union_count']}==visa_data; shadow={rep['scenario_help_shadow_count']}; "
              f"no new dup codes; pre-existing dup={rep['duplicate_codes_in_visa_data']}).")
        return
    print(f"visa_data records: {rep['visa_data_count']}")
    print(f"scenario_help shadow records: {rep['scenario_help_shadow_count']}")
    print(f"union records: {rep['union_count']}")
    print(f"duplicate codes in union: {rep['duplicate_codes_in_union'] or 'none'}")
    print(f"union == visa_data.json (E-2 zero-behavior-change invariant): {rep['union_equals_visa_data']}")


if __name__ == "__main__":
    main()
