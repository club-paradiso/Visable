#!/usr/bin/env python3
"""Validation for the 2026-06-08 source-grounded visa_data/doc_master cleanup.

Implements the task's validation checklist (items 1-8; item 9 "existing tests
pass" is covered by scripts/check_repo.sh). Read-only; exits non-zero on any
failure. Pairs with scripts/cleanup_visa_data_source_grounded_2026_06_08.py.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VISA = ROOT / "visa_data.json"
DOCMASTER = ROOT / "doc_master.json"

SCENARIO_CATS = {"scn", "faq", "nhis"}

ID_ARRAY_FIELDS = {
    "initialReqDocs", "newReqDocs", "extReqDocs", "extensionReqDocs",
    "changeReqDocs", "requiredDocs", "reqDocs", "documents", "cviReqDocs",
    "statusGrantReqDocs", "registrationReqDocs", "activitiesOutsideStatusReqDocs",
    "workplaceChangeReqDocs", "reentryReqDocs", "addReqDocs",
}

PRIORITY_CODES = ["B-1", "B-2", "C-3", "D-2", "D-4", "D-8", "D-10", "E-7", "E-9",
                  "E-10", "F-1", "F-2", "F-4", "F-5", "F-6", "G-1", "H-1", "H-2"]

# User-facing OCR-glue artifacts that must not remain in canonical records.
OCR_ARTIFACTS = ["DATA_MISSING", "및체류기간", "연장허가1.", "연장허가필수서류",
                 "서류필수서류", "필수서류①"]

DOC_NAME_NOTE_PLACEHOLDERS = {"DATA_MISSING", "문서명 미상", "비고 정보 없음"}


def main() -> int:
    failures: list[str] = []
    passes: list[str] = []

    def check(name, ok, detail=""):
        (passes if ok else failures).append(name + (f" — {detail}" if detail and not ok else ""))

    # 1 & 2: both files parse
    try:
        visas = json.loads(VISA.read_text(encoding="utf-8"))
        check("1. visa_data.json parses", isinstance(visas, list))
    except Exception as exc:  # noqa: BLE001
        check("1. visa_data.json parses", False, str(exc))
        print_report(passes, failures)
        return 1
    try:
        docs = json.loads(DOCMASTER.read_text(encoding="utf-8"))
        check("2. doc_master.json parses (array preserved)", isinstance(docs, list))
    except Exception as exc:  # noqa: BLE001
        check("2. doc_master.json parses", False, str(exc))
        print_report(passes, failures)
        return 1

    # 3: doc_master no duplicate IDs
    ids = [d.get("id") for d in docs if isinstance(d, dict)]
    dupes = [i for i, n in Counter(ids).items() if n > 1]
    check("3. doc_master has no duplicate IDs", not dupes, f"dupes={dupes}")
    doc_ids = set(ids)

    # 4: every referenced doc id exists in doc_master
    def iter_refs(node, parent=None):
        if isinstance(node, dict):
            for k, v in node.items():
                yield from iter_refs(v, k)
        elif isinstance(node, list):
            for v in node:
                if isinstance(v, str) and parent in ID_ARRAY_FIELDS:
                    yield v
                elif isinstance(v, (dict, list)):
                    yield from iter_refs(v, parent)

    missing_refs = set()
    for r in visas:
        for ref in iter_refs(r):
            if isinstance(ref, str) and ref.startswith("doc_") and ref not in doc_ids:
                missing_refs.add(ref)
    check("4. every doc_ ref in visa_data exists in doc_master", not missing_refs,
          f"missing={sorted(missing_refs)}")

    # 5: no DATA_MISSING placeholder in user-facing document names/notes
    #    (canonical, user-rendered records). Scenario/help records are retained
    #    byte-for-byte for parity and are not rendered as document tabs.
    name_note_hits = []
    for r in visas:
        if r.get("cat") in SCENARIO_CATS:
            continue
        for field in ("documents_initial", "documents_registration", "documents_extension"):
            v = r.get(field)
            if isinstance(v, list):
                for it in v:
                    if isinstance(it, dict):
                        if it.get("name") in DOC_NAME_NOTE_PLACEHOLDERS:
                            name_note_hits.append(f"{r.get('code')}.{field}.name")
                        if it.get("note") in DOC_NAME_NOTE_PLACEHOLDERS:
                            name_note_hits.append(f"{r.get('code')}.{field}.note")
            elif isinstance(v, str) and v in DOC_NAME_NOTE_PLACEHOLDERS:
                name_note_hits.append(f"{r.get('code')}.{field}")
    check("5. no DATA_MISSING in user-facing doc names/notes (canonical)",
          not name_note_hits, f"hits={name_note_hits[:10]}")

    # 6: no OCR artifact strings remain in canonical records
    ocr_hits = {}
    for r in visas:
        if r.get("cat") in SCENARIO_CATS:
            continue
        blob = json.dumps(r, ensure_ascii=False)
        for art in OCR_ARTIFACTS:
            if art in blob:
                ocr_hits.setdefault(art, []).append(r.get("code"))
    check("6. no OCR artifact strings in canonical records", not ocr_hits,
          f"hits={ocr_hits}")

    # 7: priority status codes still exist
    codes = {r.get("code") for r in visas}
    missing_priority = [c for c in PRIORITY_CODES if c not in codes]
    check("7. all priority status codes present", not missing_priority,
          f"missing={missing_priority}")

    # 8: G-1-5 searchable (direct record / subCode / alias / searchAlias)
    g1 = next((r for r in visas if r.get("code") == "G-1"), None)
    g15_ok = "G-1-5" in codes
    if g1:
        subs = g1.get("subCodes") or g1.get("subcodes") or []
        g15_ok = g15_ok or any(isinstance(s, dict) and s.get("code") == "G-1-5" for s in subs)
        g15_ok = g15_ok or "G-1-5" in (g1.get("searchAliases") or [])
        g15_ok = g15_ok or "G-1-5" in (g1.get("aliases") or [])
    check("8. G-1-5 remains searchable (record/subCode/alias/searchAlias)", g15_ok)

    print_report(passes, failures)
    return 1 if failures else 0


def print_report(passes, failures):
    print("=== Source-grounded cleanup validation (2026-06-08) ===")
    for p in passes:
        print(f"  PASS {p}")
    for f in failures:
        print(f"  FAIL {f}")
    print(f"\n{len(passes)} passed, {len(failures)} failed")


if __name__ == "__main__":
    sys.exit(main())
