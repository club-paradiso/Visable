#!/usr/bin/env python3
"""Exact-code search coverage check.

Re-implements the frontend's exact-match resolution (normalizeVisaCode +
getExactQueryMatchRank sources: top-level code, subCodes[].code,
searchAliases[], subcode searchAliases[], procedures.*.variants[].statusCode)
in Python and asserts:

  1. Every non-helper top-level code resolves (to itself at top rank).
  2. Every ACTIVE subCode resolves to its parent record.
  3. A required smoke list of exact codes resolves.
  4. Deprecated/suspended/reference-only/legacy subcodes carry a `status`
     field so the UI never presents them as active options.

Exit non-zero on any violation.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HELPER_CATS = {"faq", "scn", "nhis"}
INACTIVE = {"deprecated", "suspended", "reference_only", "legacy", "abolished"}

SMOKE = [
    "D-2", "D-4", "D-10", "E-7", "E-8", "E-9",
    "F-1", "F-2", "F-4", "F-6", "G-1", "H-2",
    "C-3", "B-1", "B-2",
    "G-1-2", "G-1-3", "G-1-4", "G-1-5", "G-1-6", "G-1-7", "G-1-9",
    "G-1-10", "G-1-11", "G-1-12", "G-1-99",
    "C-3-7", "C-4-1", "C-4-5", "E-8-1", "E-8-2", "E-8-5", "E-8-7", "E-8-99",
    "D-8-4S", "D-9-5", "E-7-S1", "E-7-S2", "F-1-D", "F-2-7S", "F-3-18",
    "F-5-S1", "F-5-S2", "H-2-7", "D-10-T", "E-7-T", "F-2-T", "F-5-T",
    "A-3-99", "F-4-R", "F-5-6R", "E-7-4R",
    "K-STAR", "REGION-S",
    # compact code forms (PARADISO_SEARCH_QUERY_FIX_20260702: the frontend now
    # resolves these via dash-less compact equality; keep them covered here)
    "G15", "D21", "E74", "F442", "D10T", "E7M", "D42K", "H27", "C38",
    # natural-language program queries
    "국내 성장 기반 외국인 청소년", "디지털노마드",
]
# Codes the manuals do not surface as active user-facing exact codes; absence
# of an exact hit is acceptable for these (documented in the audit).
SMOKE_SOFT = {"F-3-18"}


def norm(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def get_subcodes(rec):
    if isinstance(rec.get("subcodes"), list):
        return rec["subcodes"]
    if isinstance(rec.get("subCodes"), list):
        return rec["subCodes"]
    return []


def rank(rec, query):
    q = norm(query)
    if not q:
        return 0
    helper = rec.get("cat") in HELPER_CATS
    if norm(rec.get("code")) == q:
        return 10000
    for s in get_subcodes(rec):
        if norm(s.get("code")) == q:
            return 5000
    aliases = list(rec.get("aliases") or []) + list(rec.get("searchAliases") or [])
    if any(norm(a) == q for a in aliases):
        return 200 if helper else 4000
    for s in get_subcodes(rec):
        sub_aliases = list(s.get("aliases") or []) + list(s.get("searchAliases") or [])
        if any(norm(a) == q for a in sub_aliases):
            return 3000
    procs = rec.get("procedures") if isinstance(rec.get("procedures"), dict) else {}
    for proc in procs.values():
        for v in (proc.get("variants") or []) if isinstance(proc, dict) else []:
            codes = []
            if v.get("statusCode"):
                codes.append(v["statusCode"])
            codes += v.get("statusCodes") or []
            if any(norm(c) == q for c in codes):
                return 3000
    return 0


def resolve(data, query):
    hits = [(r.get("code"), rank(r, query)) for r in data]
    hits = [h for h in hits if h[1] > 0]
    hits.sort(key=lambda h: -h[1])
    return hits


def textual_resolve(data, query):
    """Fallback for natural-language program queries (searchAlias contains the
    phrase)."""
    q = query.strip()
    for r in data:
        for a in (r.get("searchAliases") or []):
            if q and q in a:
                return r.get("code")
    return None


def main():
    data = json.loads((REPO / "visa_data.json").read_text(encoding="utf-8"))
    failures = []

    # 1. top-level codes
    for r in data:
        if r.get("cat") in HELPER_CATS or r.get("isProgram"):
            continue
        if rank(r, r.get("code")) < 10000:
            failures.append(f"top-level code not self-resolving: {r.get('code')}")

    # 2. active subcodes
    for r in data:
        for s in get_subcodes(r):
            if (s.get("status") or "active") in INACTIVE:
                continue
            hits = resolve(data, s.get("code"))
            if not hits:
                failures.append(f"active subcode not searchable: {s.get('code')} (parent {r.get('code')})")

    # 3. smoke list
    for q in SMOKE:
        hits = resolve(data, q)
        if not hits:
            if re.match(r"^[A-Za-z]+-?\d", q) or "-" in q:  # code or compact code
                if q in SMOKE_SOFT:
                    print(f"  soft-miss (documented): {q}")
                    continue
                failures.append(f"smoke code did not resolve: {q}")
            else:
                # natural-language program query
                if textual_resolve(data, q) is None:
                    failures.append(f"smoke program query did not resolve: {q}")

    # 4. inactive subcodes must carry a status field
    for r in data:
        for s in get_subcodes(r):
            st = s.get("status")
            name = (s.get("name") or "")
            looks_inactive = any(w in name for w in ["폐지", "발급중단", "발급 중단", "레거시"])
            if looks_inactive and (st is None or st == "active"):
                failures.append(f"subcode looks inactive but status not set: {s.get('code')}")

    # 5. ALIAS_MAP targets in index.html must resolve to real records.
    #    (PARADISO_SEARCH_QUERY_FIX_20260702: the old RF-1/OVS-1 targets pointed
    #    at removed records, silently zeroing "난민"/"불법체류" searches.)
    index_html = (REPO / "index.html").read_text(encoding="utf-8")
    m = re.search(r"const ALIAS_MAP = \{(.*?)\};", index_html, re.S)
    if not m:
        failures.append("ALIAS_MAP not found in index.html")
    else:
        # FAQ-0 is injected at runtime by injectLocalData(); accept it.
        runtime_codes = {"FAQ-0", "K-ETA"}
        targets = set(re.findall(r':\s*"([A-Z0-9-]+)"', m.group(1)))
        for t in sorted(targets):
            if t in runtime_codes:
                continue
            if not resolve(data, t):
                failures.append(f"ALIAS_MAP target does not resolve to any record: {t}")

    print("exact-code search coverage check:")
    print(f"  records: {len(data)}; smoke queries: {len(SMOKE)}")
    if failures:
        for f in failures:
            print("  FAIL " + f)
        return 1
    print("  PASS every required code/subcode resolves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
