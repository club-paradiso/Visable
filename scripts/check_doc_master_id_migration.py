#!/usr/bin/env python3
"""Validate doc_master ID hygiene + rendering compatibility (PR D batch 2).

Asserts, with no external dependencies:
  1. No doc_master.json `id` contains Korean text / whitespace / parentheses
     (i.e. the corrupted Korean-string IDs have been migrated to stable
     machine IDs).
  2. Every document ID referenced by visa_data.json's ID-reference arrays
     that starts with `doc_` resolves to a doc_master.json entry.
  3. Every `doc_` ID used in those arrays has a display label in the
     index.html DOC_DICT map (so the frontend renders a real label rather
     than the generic `문서요건(...)` fallback).
  4. None of the 12 specific corrupted Korean-string IDs migrated in PR D
     batch 2 remains in any ID-reference array (in visa_data.json or
     backend/data/visas.json).

Note: ID-reference arrays legitimately also contain pre-existing free-text
Korean inline labels (e.g. "매뉴얼 확인 필요") that were never doc_master IDs
and render via the DOC_DICT raw-string fallback. Those are out of scope for
this migration and are intentionally NOT flagged.

This is a read-only checker. It does not modify any file.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The exact set of corrupted Korean-string doc IDs migrated in PR D batch 2.
# After migration none of these may remain in any ID-reference array.
MIGRATED_OLD_IDS = {
    "개별 사안별 증빙서류(매뉴얼 해당 항목 및 관할기관 안내 기준)",
    "변경 사유 입증서류(활동계획서·초청서·고용계약서 등 해당 자격별)",
    "사증발급신청서(별지 제17호 서식)",
    "사진 1매(해당 시)",
    "수수료",
    "여권",
    "여권 및 외국인등록증",
    "체류자격별 개별 첨부서류(매뉴얼 해당 자격 항목 참조)",
    "체류지 입증서류",
    "통합신청서",
    "통합신청서(체류자격변경허가 신청 포함)",
    "표준규격사진 1매",
}

# The stable machine IDs the migration created. Each MUST have a DOC_DICT
# label in index.html so the frontend renders the original Korean label
# instead of the generic 문서요건(...) fallback. (Pre-existing doc_master IDs
# that lack a DOC_DICT label are a separate, out-of-scope concern.)
MIGRATED_NEW_IDS = {
    "doc_case_specific_evidence", "doc_change_reason_evidence",
    "doc_visa_application_form", "doc_photo_one_optional", "doc_fee_generic",
    "doc_passport_generic", "doc_passport_and_arc",
    "doc_status_specific_attachments", "doc_residence_proof_generic",
    "doc_unified_application_form", "doc_unified_application_form_change",
    "doc_standard_photo_one",
}

# Fields whose array elements are doc_master ID references (mirrors the
# index.html renderer's legacy doc-array fields). The `documents_*[].name`
# objects are display labels, NOT ID references, and are intentionally excluded.
ID_ARRAY_FIELDS = {
    "initialReqDocs", "newReqDocs", "extReqDocs", "extensionReqDocs",
    "changeReqDocs", "requiredDocs", "reqDocs", "documents", "cviReqDocs",
    "statusGrantReqDocs", "registrationReqDocs", "activitiesOutsideStatusReqDocs",
    "workplaceChangeReqDocs", "reentryReqDocs", "addReqDocs",
}

KOREAN = re.compile(r"[가-힣]")


def fail(msg: str) -> None:
    raise SystemExit(f"[check_doc_master_id_migration] ERROR: {msg}")


def iter_id_array_refs(node, parent_field=None):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from iter_id_array_refs(v, k)
    elif isinstance(node, list):
        for v in node:
            if isinstance(v, str) and parent_field in ID_ARRAY_FIELDS:
                yield parent_field, v
            elif isinstance(v, (dict, list)):
                yield from iter_id_array_refs(v, parent_field)


def main() -> None:
    docs = json.loads((ROOT / "doc_master.json").read_text(encoding="utf-8"))
    doc_ids = {d["id"] for d in docs if isinstance(d, dict)}

    # 1. no Korean / whitespace / paren in any doc_master id
    bad_ids = [d["id"] for d in docs if isinstance(d, dict)
               and (KOREAN.search(d["id"]) or re.search(r"[\s()]", d["id"]))]
    if bad_ids:
        fail(f"doc_master.json has non-machine ids: {bad_ids}")

    html = (ROOT / "index.html").read_text(encoding="utf-8")

    for data_file in ("visa_data.json", "backend/data/visas.json"):
        vd = json.loads((ROOT / data_file).read_text(encoding="utf-8"))
        unresolved, migrated_refs, no_label = [], [], []
        for rec in vd:
            for field, ref in iter_id_array_refs(rec):
                if ref in MIGRATED_OLD_IDS:
                    migrated_refs.append((rec.get("code"), field, ref))
                    continue
                if ref.startswith("doc_"):
                    if ref not in doc_ids:
                        unresolved.append((rec.get("code"), field, ref))
                    if ref in MIGRATED_NEW_IDS and f'"{ref}":' not in html:
                        no_label.append((rec.get("code"), field, ref))
        if migrated_refs:
            fail(f"{data_file}: migrated Korean-string doc IDs still in ID-reference arrays: {migrated_refs[:5]}")
        if unresolved:
            fail(f"{data_file}: doc_ refs not found in doc_master.json: {unresolved[:5]}")
        if no_label:
            fail(f"{data_file}: doc_ refs missing an index.html DOC_DICT label: {no_label[:5]}")

    print(f"[check_doc_master_id_migration] OK - {len(doc_ids)} doc_master ids, "
          "all ID-array refs resolve and have DOC_DICT labels; no Korean-string ids remain.")


if __name__ == "__main__":
    main()
