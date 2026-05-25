#!/usr/bin/env python3
"""Read-only validator for the E-1 scenario/help/AI-grounding data store
(data/scenario_help_records.json). No dependencies; never modifies any file.

Asserts:
  1. The scenario/help file is valid JSON with the expected envelope.
  2. Every duplicated record's code exists in visa_data.json.
  3. Each nested `record` deep-equals its visa_data.json source byte-for-byte.
  4. Migration metadata is present and valid; removalFromVisaDataAllowed is
     False and requiresParityBeforeRemoval is True for ALL E-1 records.
  5. No duplicate codes inside the scenario/help store.
  6. Each record's (primary_type, source_grounding) matches the PR #169
     domain classification.
  7. No visa/status master-only record (keep_in_visa_data == 'keep') was
     duplicated.
  8. All PR #169 candidates (keep_in_visa_data in {migrate-later,maybe-compat})
     are represented.
  9. Any `doc_`-prefixed requiredDocuments id-array refs inside a duplicated
     record still resolve to doc_master.json.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data/scenario_help_records.json"
VISA = ROOT / "visa_data.json"
DOCMASTER = ROOT / "doc_master.json"
CLASS = ROOT / "docs/data/2026_05_21_visa_data_domain_classification.json"

ID_ARRAY_FIELDS = {
    "initialReqDocs", "newReqDocs", "extReqDocs", "extensionReqDocs",
    "changeReqDocs", "requiredDocs", "reqDocs", "documents", "cviReqDocs",
    "statusGrantReqDocs", "registrationReqDocs", "activitiesOutsideStatusReqDocs",
    "workplaceChangeReqDocs", "reentryReqDocs", "addReqDocs",
}


def fail(msg: str) -> None:
    raise SystemExit(f"[check_scenario_help_records] ERROR: {msg}")


def canon(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def iter_doc_refs(node, parent=None):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from iter_doc_refs(v, k)
    elif isinstance(node, list):
        for v in node:
            if isinstance(v, str) and parent in ID_ARRAY_FIELDS:
                yield v
            elif isinstance(v, (dict, list)):
                yield from iter_doc_refs(v, parent)


def main() -> None:
    if not STORE.exists():
        fail(f"store not found: {STORE.relative_to(ROOT)}")
    try:
        doc = json.loads(STORE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"malformed JSON at line {exc.lineno}: {exc.msg}")

    recs = doc.get("records")
    if not isinstance(recs, list) or not recs:
        fail("store.records must be a non-empty list")

    visas = json.loads(VISA.read_text(encoding="utf-8"))
    doc_ids = {d["id"] for d in json.loads(DOCMASTER.read_text(encoding="utf-8")) if isinstance(d, dict)}
    cl = {(r["array_index"], r["code"]): r for r in json.loads(CLASS.read_text(encoding="utf-8"))["records"]}

    # 5. no duplicate codes in the store
    codes = [r.get("sourceVisaDataCode") for r in recs]
    dupes = [c for c, n in Counter(codes).items() if n != 1]
    if dupes:
        fail(f"duplicate codes inside scenario/help store: {dupes}")

    for r in recs:
        code = r.get("sourceVisaDataCode")
        idx = r.get("sourceVisaDataIndex")
        if not isinstance(idx, int) or idx < 0 or idx >= len(visas):
            fail(f"{code}: invalid sourceVisaDataIndex {idx!r}")
        src = visas[idx]
        # 2. code exists in visa_data at that index
        if src.get("code") != code:
            fail(f"index {idx} code mismatch: store={code!r} visa_data={src.get('code')!r}")
        # 3. nested record deep-equals original
        if "record" not in r:
            fail(f"{code}: missing nested 'record'")
        if canon(r["record"]) != canon(src):
            fail(f"{code}: nested record does not match visa_data.json byte-for-byte")
        # 4. migration metadata
        if r.get("removalFromVisaDataAllowed") is not False:
            fail(f"{code}: removalFromVisaDataAllowed must be False in E-1")
        if r.get("requiresParityBeforeRemoval") is not True:
            fail(f"{code}: requiresParityBeforeRemoval must be True in E-1")
        if r.get("migrationStatus") != "duplicated_from_visa_data":
            fail(f"{code}: migrationStatus must be 'duplicated_from_visa_data'")
        if r.get("plannedCanonicalStore") != "scenario_help":
            fail(f"{code}: plannedCanonicalStore must be 'scenario_help'")
        # 6. classification match
        c = cl.get((idx, code))
        if c is None:
            fail(f"{code}: no PR #169 classification entry for (index {idx})")
        if r.get("primary_type") != c["primary_type"] or r.get("source_grounding") != c["source_grounding"]:
            fail(f"{code}: classification mismatch vs PR #169 "
                 f"({r.get('primary_type')}/{r.get('source_grounding')} != "
                 f"{c['primary_type']}/{c['source_grounding']})")
        # 7. not a keep-in-master record
        if c["keep_in_visa_data"] == "keep":
            fail(f"{code}: is a visa/status master record (keep); must NOT be duplicated")
        # 9. doc refs resolve
        for ref in iter_doc_refs(r["record"]):
            if ref.startswith("doc_") and ref not in doc_ids:
                fail(f"{code}: requiredDocuments id {ref!r} does not resolve to doc_master.json")

    # 8. all PR #169 candidates represented
    candidates = {(i, c["code"]) for (i, _), c in cl.items()
                  if c["keep_in_visa_data"] in ("migrate-later", "maybe-compat")}
    represented = {(r["sourceVisaDataIndex"], r["sourceVisaDataCode"]) for r in recs}
    missing = sorted(candidates - represented)
    if missing:
        fail(f"PR #169 candidates missing from store: {missing}")
    extra = sorted(represented - candidates)
    if extra:
        fail(f"store contains non-candidate records: {extra}")

    overstay = sum(1 for r in recs if r.get("overstay_related"))
    print(f"[check_scenario_help_records] OK - {len(recs)} duplicated records "
          f"(overstay-related: {overstay}); all match visa_data.json byte-for-byte; "
          "all PR #169 candidates represented; no dupes; removal gated.")


if __name__ == "__main__":
    main()
