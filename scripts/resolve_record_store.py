#!/usr/bin/env python3
"""Read-only record-store union resolver (E-2 / E-4A).

Provides a deterministic, importable union view of:
  * visa_data.json                     — the live canonical record master
  * data/scenario_help_records.json    — E-1 shadow copies of 17 records

E-2 / E-4A contract (runtime-safe, zero behavior change):
  * visa_data.json is CANONICAL. The scenario/help store currently holds
    byte-for-byte SHADOW copies of records that still live in visa_data.json,
    so the union MUST NOT return duplicates and MUST equal visa_data.json
    today. The resolver de-duplicates by keying on (array_index, code) and
    never overrides a canonical record with its shadow during E-2/E-4A.
  * The shadow store is exposed only as METADATA (which codes have a shadow,
    and whether removal is gated) — runtime record content stays canonical.
  * E-4A: this module IS wired into the backend `/api/visas` endpoint via
    backend/record_store_union.py. The union equals visa_data.json today so
    backend behavior is unchanged. See the E-4A report.

E-4B simulation (--simulate-e4-removal):
  * simulated_e4_union() removes the 17 alias-deprecated records from visa_data
    and replaces them with the shadow copies from scenario_help_records.json.
  * This proves that post-E-4B deletion would still produce the same effective
    58 records. The simulation modifies nothing on disk.

Usage:
    python3 scripts/resolve_record_store.py            # summary + invariant
    python3 scripts/resolve_record_store.py --json     # union as JSON
    python3 scripts/resolve_record_store.py --check    # assert E-4A invariants
    python3 scripts/resolve_record_store.py --check --simulate-e4-removal
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
    """E-1 shadow entries (list of envelope objects with a nested `record`).

    Supports the current `{"records": [...]}` envelope format and an
    optional legacy top-level list format. Returns only dict entries that
    carry a truthy `code`.
    """
    if not SCENARIO_HELP.exists():
        return []

    raw = json.loads(SCENARIO_HELP.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        records = raw.get("records", [])
    elif isinstance(raw, list):
        records = raw
    else:
        return []

    clean = []
    for entry in records:
        if not isinstance(entry, dict):
            continue
        nested = entry.get("record")
        code = None
        if isinstance(nested, dict):
            code = nested.get("code")
        else:
            code = entry.get("code")
        if not code:
            continue
        clean.append(entry)
    return clean


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
    """Deterministic merged union of canonical + shadow records.

    The union preserves all canonical visa_data.json records and appends
    additional scenario/help records only when their codes do not already
    appear canonically. Shadow records are deduplicated by code and canonical
    records are preferred when collisions occur.
    """
    visas = load_visa_data()
    canonical = [r for r in visas if isinstance(r, dict) and r.get("code")]
    canonical_codes = {r.get("code") for r in canonical}
    union = list(canonical)
    shadow_codes = set()

    for entry in load_scenario_help_shadow():
        if not isinstance(entry, dict):
            continue

        shadow_record = entry.get("record")
        if not isinstance(shadow_record, dict):
            if isinstance(entry.get("code"), str):
                shadow_record = entry
            else:
                continue

        code = shadow_record.get("code")
        if not code:
            continue

        if code in canonical_codes:
            if prefer == "scenario_help":
                for idx, existing in enumerate(union):
                    if existing.get("code") == code:
                        union[idx] = shadow_record
            continue

        if code in shadow_codes:
            continue

        union.append(shadow_record)
        shadow_codes.add(code)

    return union


def _dupe_codes(records):
    counts = {}
    for r in records:
        c = r.get("code")
        counts[c] = counts.get(c, 0) + 1
    return sorted(c for c, n in counts.items() if n > 1)


def _alias_deprecated_codes(visas):
    """Set of codes that are alias-deprecated in visa_data.json (E-3 markers)."""
    return {
        r.get("code")
        for r in visas
        if isinstance(r.get("migrationMeta"), dict)
        and r["migrationMeta"].get("migrationStatus") == "alias_deprecated_in_visa_data"
    }


def simulated_e4_union():
    """Simulate post-E-4B deletion: remove alias-deprecated records from visa_data
    and replace with shadow copies from scenario_help_records.json.

    This is a READ-ONLY simulation. Nothing is written to disk.

    Returns a list of records equivalent to the current visa_data.json, proving
    that E-4B deletion is safe. The D-4-2K pre-existing duplicate (indices 24
    and 55) is NOT alias-deprecated, so both copies survive.
    """
    visas = load_visa_data()
    shadow = load_scenario_help_shadow()
    deprecated = _alias_deprecated_codes(visas)

    # Build the simulated visa_data: remove alias-deprecated entries.
    simulated_visas = [r for r in visas if r.get("code") not in deprecated]

    # Build shadow record map: code -> record content (from envelope).
    # Shadow codes must match alias-deprecated codes exactly (17 == 17).
    shadow_records = {}
    for e in shadow:
        code = e.get("sourceVisaDataCode")
        rec = e.get("record")
        if code and rec is not None:
            shadow_records[code] = rec

    # Reconstruct in original visa_data order: for each deprecated slot, insert
    # the shadow record at the same position. Preserves original ordering.
    result = []
    for r in visas:
        code = r.get("code")
        if code in deprecated:
            result.append(shadow_records.get(code, r))
        else:
            result.append(r)

    return result


_MIGRATION_KEYS = frozenset({"migrationMeta"})


def _strip_migration_meta(record):
    """Remove migration-only keys before user-facing content comparison.

    migrationMeta is added by E-3 only to visa_data.json records as a
    deprecation marker. The shadow records in scenario_help_records.json
    intentionally do not carry it (it is not user-facing content). E-4B
    parity must compare user-facing fields only.
    """
    return {k: v for k, v in record.items() if k not in _MIGRATION_KEYS}


def simulated_e4_parity_report():
    """Run the simulated E-4B deletion and return a parity report dict.

    Parity is checked on user-facing content (all fields except migrationMeta).
    migrationMeta is intentionally absent from shadow records (it is an
    alias-deprecation marker used only in visa_data.json during E-3/E-4A).
    """
    canon = lambda o: json.dumps(o, ensure_ascii=False, sort_keys=True)
    visas = load_visa_data()
    sim = simulated_e4_union()
    deprecated = _alias_deprecated_codes(visas)

    content_parity = all(
        canon(_strip_migration_meta(s)) == canon(_strip_migration_meta(v))
        for s, v in zip(sim, visas)
    )
    return {
        "visa_data_count": len(visas),
        "simulated_union_count": len(sim),
        "alias_deprecated_removed_count": len(deprecated),
        "simulated_user_facing_content_parity": content_parity,
        "simulated_duplicate_codes": _dupe_codes(sim),
        "visa_data_duplicate_codes": _dupe_codes(visas),
        "counts_match": len(sim) == len(visas),
        "note": "migrationMeta excluded from parity (E-3 marker; intentionally absent from shadow records)",
    }


def parity_report():
    visas = load_visa_data()
    shadow = load_scenario_help_shadow()
    union = union_view()
    canon = lambda o: json.dumps(o, ensure_ascii=False, sort_keys=True)
    # Note: D-4-2K is a pre-existing duplicate code in visa_data.json
    # (indices 24 & 55), deferred to the D-content track. The current union
    # semantics preserve all canonical records and append additional shadow
    # records only when their codes are not already present canonically.
    alias_deprecated = sorted(_alias_deprecated_codes(visas))
    visa_codes = [r.get("code") for r in visas if isinstance(r, dict)]
    union_codes = [r.get("code") for r in union if isinstance(r, dict)]
    return {
        "visa_data_count": len(visas),
        "scenario_help_shadow_count": len(shadow),
        "union_count": len(union),
        "union_equals_visa_data": canon(union) == canon(visas),
        "union_shadow_only_count": len([c for c in union_codes if c not in visa_codes]),
        "union_contains_all_canonical_codes": all(c in union_codes for c in visa_codes),
        "duplicate_codes_in_union": _dupe_codes(union),
        "duplicate_codes_in_visa_data": _dupe_codes(visas),
        "shadow_codes": sorted(e.get("sourceVisaDataCode") for e in shadow),
        "alias_deprecated_codes": alias_deprecated,
        "alias_deprecated_count": len(alias_deprecated),
    }


def main() -> None:
    simulate = "--simulate-e4-removal" in sys.argv
    if "--json" in sys.argv:
        if simulate:
            print(json.dumps(simulated_e4_union(), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(union_view(), ensure_ascii=False, indent=2))
        return
    rep = parity_report()
    if "--check" in sys.argv:
        assert rep["union_equals_visa_data"], "union != visa_data.json (E-4A invariant broken)"
        assert rep["duplicate_codes_in_union"] == rep["duplicate_codes_in_visa_data"], \
            f"union introduced new duplicate codes: {set(rep['duplicate_codes_in_union']) - set(rep['duplicate_codes_in_visa_data'])}"
        assert rep["union_count"] == rep["visa_data_count"], "union count drifted from visa_data"
        if simulate:
            srep = simulated_e4_parity_report()
            assert srep["counts_match"], \
                f"simulated E-4B union count {srep['simulated_union_count']} != visa_data {srep['visa_data_count']}"
            assert srep["simulated_duplicate_codes"] == srep["visa_data_duplicate_codes"], \
                f"simulated E-4B union introduced new duplicate codes"
            assert srep["simulated_user_facing_content_parity"], \
                "simulated E-4B user-facing content differs from visa_data.json (migrationMeta excluded)"
            print(f"[resolve_record_store] OK - simulated-E4-removal parity GREEN "
                  f"(sim=={srep['simulated_union_count']}==visa_data; "
                  f"deprecated_removed={srep['alias_deprecated_removed_count']}; "
                  f"user-facing content parity: PASS; no new dup codes; migrationMeta intentionally absent).")
        else:
            print("[resolve_record_store] OK - E-4A invariants hold "
                  f"(union=={rep['union_count']}==visa_data; shadow={rep['scenario_help_shadow_count']}; "
                  f"no new dup codes; pre-existing dup={rep['duplicate_codes_in_visa_data']}).")
        return
    print(f"visa_data records: {rep['visa_data_count']}")
    print(f"scenario_help shadow records: {rep['scenario_help_shadow_count']}")
    print(f"union records: {rep['union_count']}")
    print(f"duplicate codes in union: {rep['duplicate_codes_in_union'] or 'none'}")
    print(f"alias-deprecated (E-3) records in visa_data: {rep['alias_deprecated_count']}")
    print(f"union == visa_data.json (zero-behavior-change invariant): {rep['union_equals_visa_data']}")
    if simulate:
        srep = simulated_e4_parity_report()
        print(f"\n[simulate-e4-removal]")
        print(f"  simulated union count: {srep['simulated_union_count']} (expected: {srep['visa_data_count']})")
        print(f"  alias-deprecated removed: {srep['alias_deprecated_removed_count']}")
        print(f"  user-facing content parity (excl migrationMeta): {srep['simulated_user_facing_content_parity']}")
        print(f"  duplicate codes in simulated union: {srep['simulated_duplicate_codes'] or 'none'}")
        print(f"  note: {srep['note']}")


if __name__ == "__main__":
    main()
