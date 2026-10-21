"""Deterministic 2026.9 manual-reference promotion during compatibility builds.

The status authoring source still retains the previous reference fields. Apply
ONLY the 955 page-verified, metadata-only promotions documented in the frozen
pre-promotion audit manifest. Identity guards fail closed if the authoring layer
has changed; never trust a positional path without checking the original ref.
Unverified references remain on their previous editions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AUDIT_FILE = ROOT / "audits/manual-ref-edition-2026-09/manual_ref_verification.json"
PROMOTABLE = {"verified", "verified_alt_pagination"}
EXPECTED_PROMOTIONS = 955
EDITION = "2026.9"


def promote_verified_manual_refs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    manifest = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    promoted = 0

    for row in manifest["refs"]:
        if row["status"] not in PROMOTABLE:
            continue

        # The documented path addresses the post-reconstruction JSON array,
        # including compatibility aliases like subCodes/subcodes.
        parts = row["path"].split("/")
        node: Any = records
        for part in parts:
            node = node[int(part)] if isinstance(node, list) else node[part]

        if not isinstance(node, dict):
            raise ValueError(f"manualRef is not an object: {row['path']}")

        record_index = int(parts[0])
        expected = {
            "manualType": row["manualType"],
            "manualVersion": row["manualVersion"],
            "sourceFile": row["sourceFile"],
            "pageRange": row["pageRange"],
            "section": row["section"],
        }
        if records[record_index].get("code") != row["record"]:
            raise ValueError(f"record identity drift at {row['path']}")
        for key, value in expected.items():
            if node.get(key) != value:
                raise ValueError(
                    f"source manualRef drift at {row['path']} ({key}): "
                    f"{node.get(key)!r} != {value!r}"
                )

        domain = row["manualType"]
        source = manifest["newSources"][domain]
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
            f"2026.9 promotion count drift: {promoted}, expected {EXPECTED_PROMOTIONS}"
        )
    return records
