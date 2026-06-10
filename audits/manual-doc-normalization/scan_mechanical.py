#!/usr/bin/env python3
"""Mechanical (manual-independent) audit scan for visa_data.json.

Detects:
  A  exact-string duplicates within the same document array
  B  cross-section duplicates (same string in commonDocs AND requiredDocs of one scope)
  E  literal '(embedded manual pp. X-XX)' parentheticals in any string field
  N  normalized near-duplicates within the same array (whitespace/punct-only diffs)

Outputs JSON to audits/manual-doc-normalization/mechanical_findings.json
Resume-safe: pure read of visa_data.json, no edits.
"""
import json, re, unicodedata
from pathlib import Path

DATA = json.loads(Path("visa_data.json").read_text(encoding="utf-8"))
SECTIONS = ["commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs"]
ID_ARRAYS = ["newReqDocs", "extReqDocs", "initialReqDocs", "extensionReqDocs", "changeReqDocs"]

PUNCT = r"[\s·•∙‧ㆍ,，.．()\[\]「」『』<>〈〉【】\-‐–—_/:;※*①-⑳❶-❿`‘’“”‥…]+"
def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(PUNCT, "", s).lower()

EMBEDDED = re.compile(r"\(embedded manual pp?\.\s*[0-9].*?\)")

findings = {}  # code -> {A:[], B:[], E:[], N:[]}

def rec(code):
    return findings.setdefault(code, {"A": [], "B": [], "E": [], "N": []})

def scan_array(code, loc, arr, keyfn=lambda x: x):
    """Type A exact dup + Type N normalized near-dup within one array."""
    seen_exact, seen_norm = {}, {}
    for i, e in enumerate(arr):
        k = keyfn(e)
        if k is None:
            continue
        if k in seen_exact:
            rec(code)["A"].append({"loc": loc, "value": k, "first_idx": seen_exact[k], "dup_idx": i})
        else:
            seen_exact[k] = i
        nk = norm(k)
        if nk in seen_norm and seen_norm[nk][1] != k:
            rec(code)["N"].append({"loc": loc, "a": seen_norm[nk][1], "b": k,
                                    "a_idx": seen_norm[nk][0], "b_idx": i})
        elif nk not in seen_norm:
            seen_norm[nk] = (i, k)

def scan_embedded(code, loc, s):
    for m in EMBEDDED.findall(s):
        rec(code)["E"].append({"loc": loc, "full": s, "match": m})

def walk_embedded(code, obj, path):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk_embedded(code, v, path + [k])
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_embedded(code, v, path + [str(i)])
    elif isinstance(obj, str):
        if "embedded manual" in obj:
            scan_embedded(code, ".".join(path), obj)

for v in DATA:
    code = v["code"]
    # ID arrays (doc_master refs) - exact dup only meaningful
    for fld in ID_ARRAYS:
        arr = v.get(fld)
        if isinstance(arr, list):
            scan_array(code, fld, arr)
    for sc in (v.get("subCodes") or []):
        arr = sc.get("addReqDocs")
        if isinstance(arr, list):
            scan_array(code, f"subCodes[{sc.get('code')}].addReqDocs", arr)
    # documents_* label arrays
    for fld in [k for k in v if k.startswith("documents_")]:
        arr = v.get(fld)
        if isinstance(arr, list) and arr and isinstance(arr[0], dict):
            scan_array(code, fld, arr, keyfn=lambda x: x.get("name"))
    # procedures
    procs = v.get("procedures") or {}
    for tab, p in procs.items():
        if not isinstance(p, dict):
            continue
        scopes = []
        rd = p.get("requiredDocs")
        if isinstance(rd, dict):
            scopes.append((f"procedures.{tab}.requiredDocs", rd))
        for vi, var in enumerate(p.get("variants") or []):
            vrd = var.get("requiredDocs")
            if isinstance(vrd, dict):
                scopes.append((f"procedures.{tab}.variants[{vi}|{var.get('id','')}].requiredDocs", vrd))
        for loc, scope in scopes:
            for sect in SECTIONS:
                arr = scope.get(sect)
                if isinstance(arr, list):
                    scan_array(code, f"{loc}.{sect}", arr)
            c = set(scope.get("commonDocs") or [])
            r = set(scope.get("requiredDocs") or [])
            for item in sorted(c & r):
                rec(code)["B"].append({"loc": loc, "value": item})
    # Type E: walk whole record
    walk_embedded(code, v, [code])

# prune empty
findings = {k: val for k, val in findings.items() if any(val.values())}
out = Path("audits/manual-doc-normalization/mechanical_findings.json")
out.write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")

ta = sum(len(x["A"]) for x in findings.values())
tb = sum(len(x["B"]) for x in findings.values())
te = sum(len(x["E"]) for x in findings.values())
tn = sum(len(x["N"]) for x in findings.values())
print(f"codes with findings: {len(findings)}")
print(f"Type A (exact dup):      {ta}")
print(f"Type B (common∩required):{tb}")
print(f"Type E (embedded manual):{te}")
print(f"Type N (norm near-dup):  {tn}")
print()
for code, val in findings.items():
    bits = [f"{k}={len(v)}" for k, v in val.items() if v]
    print(f"  {code}: {', '.join(bits)}")
