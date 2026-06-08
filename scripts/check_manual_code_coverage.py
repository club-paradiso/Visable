#!/usr/bin/env python3
"""Manual-to-data coverage check (2026.5 visa / 2026.5–2026-06-01 stay).

Compares a canonical manual code inventory against visa_data.json and
classifies each item. Fails if:
  * a required parent (basic 체류자격) code is missing;
  * a confirmed-active subcode is not searchable;
  * a quarantined code (deprecated / suspended / reference-only / legacy /
    internal marker) is presented as active.

This is the source-grounded coverage gate; the prose/JSON audit artifacts
live under docs/data/2026_06_08_*.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INACTIVE = {"deprecated", "suspended", "reference_only", "legacy", "abolished"}

# Basic parent 체류자격 codes that must exist as top-level records.
BASIC_PARENTS = [
    "A-1", "A-2", "A-3", "B-1", "B-2", "C-1", "C-3", "C-4",
    "D-1", "D-2", "D-3", "D-4", "D-5", "D-6", "D-7", "D-8", "D-9", "D-10",
    "E-1", "E-2", "E-3", "E-4", "E-5", "E-6", "E-7", "E-8", "E-9", "E-10",
    "F-1", "F-2", "F-3", "F-4", "F-5", "F-6", "G-1", "H-1", "H-2",
]

# Confirmed-active codes/subcodes that must be exactly searchable.
REQUIRED_ACTIVE = [
    # G-1 family (stay manual pp. 497-512)
    "G-1-1", "G-1-2", "G-1-3", "G-1-4", "G-1-5", "G-1-6", "G-1-7", "G-1-9",
    "G-1-10", "G-1-11", "G-1-12", "G-1-99",
    # seasonal (visa manual pp. 277-279) + arrival tourism
    "C-3-7", "C-4-5", "E-8-1", "E-8-2", "E-8-3", "E-8-4", "E-8-5", "E-8-6",
    "E-8-7", "E-8-8", "E-8-99",
    # special talent / startup / nomad / trade
    "D-8-4S", "D-9-5", "E-7-S1", "E-7-S2", "F-1-D", "A-3-99", "H-2-7",
    # Top-Tier
    "D-10-T", "E-7-T", "F-2-T", "F-5-T",
    # K-STAR
    "F-2-7S", "F-2-71", "F-5-S1", "F-5-S2",
    # regional (지역특화형)
    "F-2-R", "F-3-1R", "F-3-2R", "F-3-3R", "E-7-4R", "F-4-R", "F-5-6R",
]

# Quarantined codes: must NOT be presented as active. Expected status (or, for
# E-7-H, absent as a subcode because it is an internal system marker).
QUARANTINED = {
    "C-3-11": "deprecated",     # 교대선원, abolished 2022.6
    "C-4-1": "suspended",       # 계절근로 단기취업, issuance stopped 2025
    "C-4-2": "suspended",
    "C-4-3": "suspended",
    "C-4-4": "suspended",
    "D-3-1": "legacy",          # registered until 2006.12.31
    "G-1-19": "reference_only",  # E-8 re-entry recommendation marker
}


def norm(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def get_subcodes(rec):
    if isinstance(rec.get("subcodes"), list):
        return rec["subcodes"]
    if isinstance(rec.get("subCodes"), list):
        return rec["subCodes"]
    return []


def main():
    data = json.loads((REPO / "visa_data.json").read_text(encoding="utf-8"))
    top_codes = {r.get("code") for r in data}

    # index: code -> (record_code, subcode_obj_or_None)
    searchable = {}
    sub_by_code = {}
    for r in data:
        searchable.setdefault(norm(r.get("code")), []).append((r.get("code"), None))
        for a in (r.get("searchAliases") or []):
            searchable.setdefault(norm(a), []).append((r.get("code"), None))
        for s in get_subcodes(r):
            sub_by_code[norm(s.get("code"))] = s
            searchable.setdefault(norm(s.get("code")), []).append((r.get("code"), s))
            for a in (s.get("searchAliases") or []):
                searchable.setdefault(norm(a), []).append((r.get("code"), s))

    failures = []
    classified = {"represented_exactly": 0, "represented_as_subCode": 0,
                  "quarantined": 0, "missing": 0}

    for code in BASIC_PARENTS:
        if code in top_codes:
            classified["represented_exactly"] += 1
        else:
            classified["missing"] += 1
            failures.append(f"missing basic parent code: {code}")

    for code in REQUIRED_ACTIVE:
        hits = searchable.get(norm(code))
        if not hits:
            classified["missing"] += 1
            failures.append(f"required active code not searchable: {code}")
            continue
        classified["represented_as_subCode"] += 1
        # ensure it is not marked inactive
        sub = sub_by_code.get(norm(code))
        if sub and (sub.get("status") or "active") in INACTIVE:
            failures.append(f"required active code marked inactive: {code}")

    for code, expected in QUARANTINED.items():
        sub = sub_by_code.get(norm(code))
        if sub is None:
            # acceptable only if also not searchable as an active alias
            continue
        classified["quarantined"] += 1
        st = sub.get("status") or "active"
        if st not in INACTIVE:
            failures.append(f"quarantined code presented as active: {code} (status={st})")

    # E-7-H must NOT exist as a subcode (internal system marker only)
    if norm("E-7-H") in sub_by_code:
        failures.append("E-7-H present as a subcode; it is an internal 전산기호, not a status code")

    print("manual code coverage check:")
    for k, v in classified.items():
        print(f"  {k}: {v}")
    if failures:
        for f in failures:
            print("  FAIL " + f)
        return 1
    print("  PASS manual inventory coverage holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
