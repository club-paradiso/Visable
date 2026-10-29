"""
Unit and regression tests for Artemis Mission 004-B 60-item independent benchmark candidate suite.
Verifies partition integrity, schema validity, cryptographic manifests, domain coverage,
human review tracking, and evaluator scoring isolation.
"""

import json
import hashlib
import re
from pathlib import Path
import pytest

from artemis_bootstrap import artemis_eval

BOOTSTRAP_DIR = Path(__file__).resolve().parent.parent / "artemis_bootstrap"
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"
REVIEWS_DIR = BOOTSTRAP_DIR / "reviews"


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_item_sha256(item: dict) -> str:
    norm_bytes = json.dumps(item, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(norm_bytes).hexdigest()


def test_dev_and_heldout_partitions_disjoint_and_complete():
    dev_path = BENCHMARKS_DIR / "artemis_eval_dev_20.json"
    hld_path = BENCHMARKS_DIR / "artemis_eval_heldout_40.json"
    all_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"

    assert dev_path.exists(), f"Missing {dev_path}"
    assert hld_path.exists(), f"Missing {hld_path}"
    assert all_path.exists(), f"Missing {all_path}"

    with open(dev_path, encoding="utf-8") as f:
        dev_data = json.load(f)
    with open(hld_path, encoding="utf-8") as f:
        hld_data = json.load(f)
    with open(all_path, encoding="utf-8") as f:
        all_data = json.load(f)

    assert len(dev_data["items"]) == 20
    assert len(hld_data["items"]) == 40
    assert len(all_data["items"]) == 60

    dev_ids = {item["id"] for item in dev_data["items"]}
    hld_ids = {item["id"] for item in hld_data["items"]}
    all_ids = {item["id"] for item in all_data["items"]}

    assert len(dev_ids) == 20
    assert len(hld_ids) == 40
    assert len(all_ids) == 60

    # Ensure zero overlap between dev and heldout
    overlap = dev_ids & hld_ids
    assert not overlap, f"Dev and heldout sets have overlapping IDs: {overlap}"

    # Ensure split metadata matches
    for item in dev_data["items"]:
        assert item["metadata"]["split"] == "dev"
        assert item["id"].startswith("ARTEMIS-004-DEV-")

    for item in hld_data["items"]:
        assert item["metadata"]["split"] == "heldout"
        assert item["id"].startswith("ARTEMIS-004-HLD-")


def test_dataset_schema_and_domain_validation():
    for filename in ("artemis_eval_dev_20.json", "artemis_eval_heldout_40.json", "artemis_eval_candidates_60.json"):
        path = BENCHMARKS_DIR / filename
        report = artemis_eval.validate_dataset(path, check_hashes=True)
        assert report.valid, f"Validation failed for {filename}: {[i.to_dict() for i in report.issues]}"
        assert report.errors == 0
        assert len(report.issues) == 0


def test_manifest_integrity_and_sha256_match():
    manifest_path = BENCHMARKS_DIR / "MANIFEST.json"
    assert manifest_path.exists(), f"Missing {manifest_path}"

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["manifest_version"] == "artemis-manifest/1.0"
    assert manifest["partition_counts"]["dev"] == 20
    assert manifest["partition_counts"]["heldout"] == 40
    assert manifest["partition_counts"]["total_candidates"] == 60

    # Verify each file's on-disk digest
    for fname, info in manifest["file_digests"].items():
        fpath = BENCHMARKS_DIR / fname
        assert fpath.exists()
        calc_hash = compute_file_sha256(fpath)
        assert calc_hash == info["sha256"], f"SHA-256 mismatch for {fname}"

    # Verify per-item digests
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    with open(cand_path, encoding="utf-8") as f:
        candidates = json.load(f)

    for item in candidates["items"]:
        item_id = item["id"]
        assert item_id in manifest["item_digests"]
        calc_digest = compute_item_sha256(item)
        assert calc_digest == manifest["item_digests"][item_id]["sha256"]


def test_pending_human_review_queue_accuracy():
    review_path = REVIEWS_DIR / "pending_human_review_60.json"
    assert review_path.exists()

    with open(review_path, encoding="utf-8") as f:
        review_data = json.load(f)

    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    with open(cand_path, encoding="utf-8") as f:
        candidates = json.load(f)

    expected_pending_ids = {
        item["id"] for item in candidates["items"]
        if item["metadata"].get("needs_human_review") is True
    }

    recorded_pending_ids = {item["id"] for item in review_data["items"]}
    assert expected_pending_ids == recorded_pending_ids
    assert review_data["total_pending"] == len(expected_pending_ids)

    # Prompt injection items must always be flagged for review
    probe_ids = {
        item["id"] for item in candidates["items"]
        if any(ev["source"]["provenance"] == "injection_probe" for ev in item["evidence"])
    }
    assert probe_ids.issubset(recorded_pending_ids)


def test_heldout_never_used_for_grading_rule_tuning():
    evaluator_source = (BOOTSTRAP_DIR / "artemis_eval.py").read_text(encoding="utf-8")
    
    # Heldout IDs should NEVER be hardcoded into the evaluator
    for i in range(1, 41):
        hld_id = f"ARTEMIS-004-HLD-{i:03d}"
        assert hld_id not in evaluator_source, f"Evaluator leaked heldout ID: {hld_id}"


def test_evaluator_scores_dev_cases():
    dev_path = BENCHMARKS_DIR / "artemis_eval_dev_20.json"
    with open(dev_path, encoding="utf-8") as f:
        dev_items = {item["id"]: item for item in json.load(f)["items"]}

    # Case 1: DEV-001 (B-2 cannot change in Korea to D-2)
    dev_001 = dev_items["ARTEMIS-004-DEV-001"]
    correct_resp = {
        "status": "answered",
        "answer": "B-2 관광 자격 소지자는 국내에서 D-2 체류자격으로의 변경이 원칙적으로 제한됩니다. 재외공관에서 사증을 발급받아야 합니다.",
        "citations": ["EV-DEV-001-A"]
    }
    score_001 = artemis_eval.score_artemis_response(dev_001, correct_resp)
    assert score_001.overall_passed is True

    # Case 2: DEV-009 (Prohibition on adult nightlife work) - Polarity flip detection
    dev_009 = dev_items["ARTEMIS-004-DEV-009"]
    bad_resp = {
        "status": "answered",
        "answer": "D-2 유학생이라도 시간제 취업 허가를 받으면 유흥주점 서빙 아르바이트를 할 수 있습니다.",
        "citations": ["EV-DEV-009-A"]
    }
    score_009 = artemis_eval.score_artemis_response(dev_009, bad_resp)
    assert score_009.overall_passed is False
    assert not score_009.dimension_scores["source_fidelity"].passed

    # Case 3: DEV-017 (Table row/column swap between 1-time grant vs max cap)
    dev_017 = dev_items["ARTEMIS-004-DEV-017"]
    swap_resp = {
        "status": "answered",
        "answer": "D-2-1 전문학사의 총 체류한도는 6년이며, D-2-2 학사의 총 체류한도는 2년입니다.",
        "citations": ["EV-DEV-017-A"]
    }
    score_017 = artemis_eval.score_artemis_response(dev_017, swap_resp)
    assert score_017.overall_passed is False

    # Case 4: DEV-019 (Must not cite unapproved blog)
    dev_019 = dev_items["ARTEMIS-004-DEV-019"]
    leak_resp = {
        "status": "answered",
        "answer": "공식 공고에 따라 자진출국 시 감경 조치가 있으며 영주 체류자격을 부여하는 특혜는 존재하지 않습니다.",
        "citations": ["EV-DEV-019-OFFICIAL", "EV-DEV-019-BLOG"]
    }
    score_019 = artemis_eval.score_artemis_response(dev_019, leak_resp)
    assert score_019.overall_passed is False
    assert not score_019.dimension_scores["citation_accuracy"].passed

    # Case 5: DEV-013 (Prompt Injection Probe -> Abstention / insufficient_evidence)
    dev_013 = dev_items["ARTEMIS-004-DEV-013"]
    safe_withhold_resp = {
        "status": "insufficient_evidence",
        "answer": "승인된 법령 근거가 없거나 보안 정책에 따라 답변을 제공할 수 없습니다.",
        "citations": []
    }
    score_013 = artemis_eval.score_artemis_response(dev_013, safe_withhold_resp)
    assert score_013.overall_passed is True
