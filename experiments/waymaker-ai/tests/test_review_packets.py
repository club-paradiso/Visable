"""Unit tests for Artemis Group A Legal Review Packets (Mission 004-D).

Verifies:
1. 16 Group A review packets exist in review_packets/ (both JSON and Markdown).
2. All 4 batches conform to required partition (4 batches x 4 items).
3. All packets remain in 'unreviewed' status with unchecked checklists.
4. Evidence text SHA-256 digests match actual normalized content.
5. Mandatory fields (question, legal basis, provision, source URL, effective date) are non-empty.
6. Group A Index manifest is well-formed.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from artemis_bootstrap.review_packets_generator import (
    GROUP_A_BATCHES,
    GROUP_A_METADATA_CATALOG,
    compute_sha256,
    generate_group_a_packets,
    validate_review_packet,
    build_packet_for_item,
)


BOOTSTRAP_DIR = Path(__file__).resolve().parent.parent / "artemis_bootstrap"
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"
PACKETS_DIR = BOOTSTRAP_DIR / "review_packets"


def test_group_a_batches_partition():
    assert len(GROUP_A_BATCHES) == 4
    total_items = sum(len(b["items"]) for b in GROUP_A_BATCHES)
    assert total_items == 16
    assert len(GROUP_A_METADATA_CATALOG) == 16

    # Verify all items in catalog are unique
    all_item_ids = [item_id for b in GROUP_A_BATCHES for item_id in b["items"]]
    assert len(set(all_item_ids)) == 16


def test_packets_generation_and_validation(tmp_path):
    # Test generation into a temporary directory
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    manifest = generate_group_a_packets(candidates_path=cand_path, output_dir=tmp_path)

    assert manifest["total_packets"] == 16
    assert manifest["total_batches"] == 4
    assert manifest["status"] == "review_ready"

    # Check each file exists
    for b in GROUP_A_BATCHES:
        for cid in b["items"]:
            json_file = tmp_path / f"{cid}.json"
            md_file = tmp_path / f"{cid}.md"
            assert json_file.exists(), f"Missing JSON packet for {cid}"
            assert md_file.exists(), f"Missing Markdown packet for {cid}"

            data = json.loads(json_file.read_text(encoding="utf-8"))
            assert data["item_id"] == cid
            assert data["current_status"] == "unreviewed"
            assert len(data["reviewer_checklist"]) >= 4

            # Verify no checklist item is prematurely checked
            for chk in data["reviewer_checklist"]:
                assert chk["checked"] is False, f"Checklist {chk['check_id']} was prematurely checked in {cid}"

            # Verify legal basis
            lb = data["legal_basis"]
            assert bool(lb["claimed_basis"])
            assert bool(lb["document_id"])
            assert bool(lb["provision"])
            assert bool(lb["source_url"])
            assert bool(lb["effective_date"])

            # Verify evidence integrity
            for ev in data["evidence_items"]:
                assert compute_sha256(ev["text"]) == ev["sha256"]


def test_existing_review_packets_in_repo():
    manifest_file = PACKETS_DIR / "index.json"
    assert manifest_file.exists(), "review_packets/index.json does not exist"

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["total_packets"] == 16

    for b in GROUP_A_BATCHES:
        for cid in b["items"]:
            json_file = PACKETS_DIR / f"{cid}.json"
            md_file = PACKETS_DIR / f"{cid}.md"
            assert json_file.exists(), f"Missing repo JSON packet {cid}.json"
            assert md_file.exists(), f"Missing repo Markdown packet {cid}.md"
