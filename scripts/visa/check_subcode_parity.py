#!/usr/bin/env python3
"""Validate subcode parity between canonical `subcodes` and legacy `subCodes`.

Phase 2 of the "consume normalized subcodes" work. Read-only.

During the compatibility phase the generated visa_data.json may carry BOTH a
canonical normalized `subcodes` array and a legacy compatibility `subCodes`
array. Runtime consumers now prefer `subcodes` (with a `subCodes` fallback), so
this validator makes the relationship between the two explicit and loud.

It reports, for the generated visa_data.json:
  * records with only legacy `subCodes`
  * records with only canonical `subcodes`
  * records with both and a matching subcode-code set
  * records with both but a MISMATCHED subcode-code set
  * subcode codes only reachable via legacy `subCodes` (these would be lost for
    exact-code search if `subCodes` were removed before `subcodes` is updated)

It FAILS on:
  * an undocumented both-but-mismatched record (a NEW divergence)
  * an authoring status file that puts `subCodes` at the top level
    (legacy camelCase must live under `_generated`, not the editable surface)

Known, documented legacy exceptions (see KNOWN_LEGACY_EXCEPTIONS) warn loudly
but do not fail, so this can run green in CI while still surfacing the drift.

Usage:
  python3 scripts/visa/check_subcode_parity.py [--strict]
    --strict  also fail on documented legacy exceptions
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _visa_pipeline_common as C  # noqa: E402

# Documented legacy exceptions: code -> reason. These are records where the
# generated lowercase `subcodes` is a known legacy/divergent copy and the
# camelCase `subCodes` remains authoritative. Reconciling the CONTENT is a
# deliberate data decision deferred to a follow-up PR (it may touch
# subcode names/eligibility), so it is intentionally NOT auto-resolved here.
KNOWN_LEGACY_EXCEPTIONS = {
    "C-3": "legacy lowercase `subcodes` is an 11-code subset; camelCase "
           "`subCodes` (13) is authoritative and includes the search stub "
           "C-3-91 and cross-ref C-2. Canonical `subcodes` must be enriched "
           "before `subCodes` can be removed.",
}


def _codes(arr):
    if not isinstance(arr, list):
        return None
    return [s.get("code") for s in arr if isinstance(s, dict)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true",
                    help="fail even on documented legacy exceptions")
    args = ap.parse_args()

    data = C.load_json(C.VISA_DATA)
    only_legacy, only_canonical, both_match, both_mismatch, neither = [], [], [], [], []
    legacy_only_codes = {}   # code -> [subcodes reachable only via subCodes]
    content_differs = []

    for r in data:
        code = r.get("code")
        sc_canon = _codes(r.get("subcodes"))      # canonical lowercase
        sc_legacy = _codes(r.get("subCodes"))     # legacy camelCase
        has_canon = sc_canon is not None
        has_legacy = sc_legacy is not None

        if has_canon and has_legacy:
            set_canon, set_legacy = set(sc_canon), set(sc_legacy)
            if set_canon == set_legacy:
                both_match.append(code)
                if C.json.dumps(r["subcodes"], ensure_ascii=False, sort_keys=True) != \
                        C.json.dumps(r["subCodes"], ensure_ascii=False, sort_keys=True):
                    content_differs.append(code)
            else:
                both_mismatch.append(code)
            missing = set_legacy - set_canon
            if missing:
                legacy_only_codes[code] = sorted(missing)
        elif has_legacy:
            only_legacy.append(code)
            legacy_only_codes[code] = sorted(set(sc_legacy))
        elif has_canon:
            only_canonical.append(code)
        else:
            neither.append(code)

    # ---- authoring surface check: no top-level subCodes ----
    authoring_violations = []
    for p in sorted(C.STATUSES_DIR.glob("*.json")):
        a = C.load_json(p)
        if "subCodes" in a:
            authoring_violations.append(p.name)

    # ---- report ----
    print("=" * 72)
    print("Subcode parity (generated visa_data.json)")
    print("=" * 72)
    print(f"records total              : {len(data)}")
    print(f"only legacy subCodes       : {len(only_legacy)}  {only_legacy}")
    print(f"only canonical subcodes    : {len(only_canonical)} {only_canonical}")
    print(f"both, matching code-set    : {len(both_match)}  {both_match}")
    print(f"both, MISMATCHED code-set  : {len(both_mismatch)} {both_mismatch}")
    print(f"neither (no subcodes)      : {len(neither)}")
    if content_differs:
        print(f"both match codes but field content differs (compat-ok): {content_differs}")
    if legacy_only_codes:
        print("\nSubcodes reachable ONLY via legacy subCodes (would be lost for "
              "exact search if subCodes removed before subcodes is enriched):")
        for code, codes in legacy_only_codes.items():
            print(f"  {code}: {codes}")

    errors, warnings = [], []
    for code in both_mismatch:
        if code in KNOWN_LEGACY_EXCEPTIONS and not args.strict:
            warnings.append(f"{code}: documented legacy subcode divergence — {KNOWN_LEGACY_EXCEPTIONS[code]}")
        else:
            errors.append(f"{code}: subcodes/subCodes code-sets differ and this is "
                          f"{'forced strict' if code in KNOWN_LEGACY_EXCEPTIONS else 'an UNDOCUMENTED divergence'}")
    for name in authoring_violations:
        errors.append(f"authoring/{name}: `subCodes` at top level — legacy camelCase "
                      f"must live under `_generated`, the editable surface uses `subcodes`")

    print()
    for w in warnings:
        print(f"[subcode-parity] WARN: {w}")
    if errors:
        print(f"[subcode-parity] FAIL — {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"[subcode-parity] OK — canonical `subcodes` preferred; legacy `subCodes` "
          f"is compatibility-only; {len(warnings)} documented exception(s); "
          f"no undocumented divergence; authoring surface clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
