"""Deterministic 2026.10 manual-reference promotion during compatibility builds.

Second stage after scripts/visa/manual_ref_promotion_2026_09.py. The owner made
the 2026-10-19 stay and visa manuals (2026.10) the reference editions on
2026-10-23. Apply ONLY the page-verified, metadata-only promotions documented
in the frozen pre-promotion audit manifest
(audits/manual-ref-edition-2026-10/manual_ref_verification.json, written by
scripts/audit_manual_ref_editions_2026_10.py before this stage existed).

Identity guards fail closed: a ref is only touched when its record, path,
edition, source file, page range and section are exactly what the audit saw.
Refs the audit could not verify (wording missing on the cited old page, page
not matched by content, wording not verbatim on the 2026.10 page, no page
layer) keep their previous edition and are listed in the audit README.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AUDIT_FILE = ROOT / "audits/manual-ref-edition-2026-10/manual_ref_verification.json"
PROMOTABLE = {"verified", "verified_alt_pagination"}
EXPECTED_PROMOTIONS = 956
EDITION = "2026.10"


def promote_verified_manual_refs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    manifest = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    promoted = 0

    for row in manifest["refs"]:
        if row["status"] not in PROMOTABLE:
            continue

        parts = row["path"].split("/")
        node: Any = records
        for part in parts:
            node = node[int(part)] if isinstance(node, list) else node[part]
        if not isinstance(node, dict):
            raise ValueError(f"manualRef is not an object: {row['path']}")
        record_index = int(parts[0])
        source = manifest["newSources"][row["manualType"]]
        if records[record_index].get("code") != row["record"]:
            raise ValueError(f"record identity drift at {row['path']}")

        # subCodes and subcodes are compatibility aliases of the SAME list
        # object during reconstruction: a second path may revisit a ref that
        # was already promoted through its alias, and only an exact match is
        # accepted.
        if node.get("manualVersion") == EDITION:
            already_current = (
                node.get("sourceDate") == source["sourceDate"]
                and node.get("sourceFile") == source["text"]
                and node.get("pageRange") == row["newPageRange"]
                and ("sourceId" not in node or node["sourceId"] == source["sourceId"])
                and ("sourcePdf" not in node or node["sourcePdf"] == source["pdf"])
            )
            if not already_current:
                raise ValueError(f"conflicting promoted alias at {row['path']}")
            promoted += 1
            continue

        expected = {
            "manualType": row["manualType"],
            "manualVersion": row["manualVersion"],
            "sourceFile": row["sourceFile"],
            "pageRange": row["pageRange"],
            "section": row["section"],
        }
        for key, value in expected.items():
            if node.get(key) != value:
                raise ValueError(
                    f"source manualRef drift at {row['path']} ({key}): "
                    f"{node.get(key)!r} != {value!r}"
                )

        node["manualVersion"] = EDITION
        node["sourceDate"] = source["sourceDate"]
        node["sourceFile"] = source["text"]
        if "sourcePdf" in node:
            node["sourcePdf"] = source["pdf"]
        if "sourceId" in node:
            node["sourceId"] = source["sourceId"]
        if "confidence" in node:
            node["confidence"] = source["confidence"]
        node["pageRange"] = row["newPageRange"]
        promoted += 1

    if promoted != EXPECTED_PROMOTIONS:
        raise ValueError(
            f"2026.10 promotion count drift: {promoted}, expected {EXPECTED_PROMOTIONS}"
        )
    return records
