#!/usr/bin/env python3
"""doc_master.json integrity + raw-doc-id leak guard.

Invariants:
  1. Every doc id referenced by visa_data.json exists in doc_master.json.
  2. Every referenced doc id is resolvable by the frontend DOC_DICT
     (index.html) — otherwise the checklist UI would leak a raw machine id.
  3. doc_master.json has no duplicate ids.
  4. renderDocTags has a user-friendly fallback (no raw id in visible text).

Exit non-zero on any violation.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_referenced_ids():
    text = (REPO / "visa_data.json").read_text(encoding="utf-8")
    return set(re.findall(r"doc_[a-z0-9_]+", text))


def load_doc_master():
    return json.loads((REPO / "doc_master.json").read_text(encoding="utf-8"))


def load_doc_dict_keys():
    html = (REPO / "index.html").read_text(encoding="utf-8")
    m = re.search(r"const DOC_DICT = \{(.*?)\n\};", html, re.S)
    if not m:
        return None, html
    return set(re.findall(r'"(doc_[a-z0-9_]+)"\s*:', m.group(1))), html


def main():
    failures = []
    referenced = load_referenced_ids()
    dm = load_doc_master()
    dm_ids = [d["id"] for d in dm]
    dm_set = set(dm_ids)
    dd_keys, html = load_doc_dict_keys()

    # 1. referenced ⊆ doc_master
    missing_dm = sorted(referenced - dm_set)
    if missing_dm:
        failures.append(f"referenced doc ids missing from doc_master.json: {missing_dm}")

    # 2. referenced ⊆ DOC_DICT (frontend resolver)
    if dd_keys is None:
        failures.append("could not locate DOC_DICT in index.html")
    else:
        missing_dd = sorted(referenced - dd_keys)
        if missing_dd:
            failures.append(
                "referenced doc ids missing from index.html DOC_DICT "
                f"(would render raw id in UI): {missing_dd}")

    # 3. no duplicate ids in doc_master
    dupes = sorted({i for i in dm_ids if dm_ids.count(i) > 1})
    if dupes:
        failures.append(f"duplicate ids in doc_master.json: {dupes}")

    # 4. friendly fallback present (no raw-id-derived label)
    if html is not None:
        if "문서요건(" in html and "key.replace('doc_','')" in html:
            failures.append("renderDocTags still derives a visible label from the raw doc id")
        if "docDefinitionNeeded" not in html and "문서 정의 필요" not in html:
            failures.append("renderDocTags has no user-friendly unresolved-id fallback")

    print("doc_master integrity check:")
    print(f"  referenced ids: {len(referenced)}")
    print(f"  doc_master ids: {len(dm_set)}")
    print(f"  DOC_DICT keys: {len(dd_keys) if dd_keys else 'N/A'}")
    if failures:
        for f in failures:
            print("  FAIL " + f)
        return 1
    print("  PASS all invariants hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
