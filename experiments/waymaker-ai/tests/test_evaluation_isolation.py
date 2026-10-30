"""Unit tests for Artemis Evaluation Isolation and Blind Benchmark Protocol (Mission 004-D).

Verifies:
1. Blind input projection completely strips expected answers and grading directives.
2. Prompt leakage detector identifies injected answer targets and forbidden claims.
3. Benchmark partition integrity: zero overlap between dev (20) and heldout (40) sets.
4. Local environment isolation audit accurately reports 'isolation_not_verified'.
5. Generated blind benchmark files have 0 expected labels and valid manifests.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from artemis_bootstrap.evaluation_isolation import (
    EvaluationIsolationError,
    compute_file_sha256,
    detect_prompt_leakage,
    generate_blind_benchmarks,
    get_environment_isolation_audit,
    project_blind_item,
    verify_benchmark_partitions,
)


BOOTSTRAP_DIR = Path(__file__).resolve().parent.parent / "artemis_bootstrap"
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"


def test_blind_input_projection_strips_expected_labels():
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    raw_item = json.loads(cand_path.read_text(encoding="utf-8"))["items"][0]

    assert "expected" in raw_item

    blind_item = project_blind_item(raw_item)

    # 1. 'expected' must be completely absent
    assert "expected" not in blind_item

    # 2. Key question fields must be preserved
    assert blind_item["id"] == raw_item["id"]
    assert blind_item["question"] == raw_item["question"]
    assert blind_item["user_context"] == raw_item["user_context"]
    assert blind_item["metadata"]["blind_projected"] is True


def test_prompt_leakage_detection():
    gt_item = {
        "id": "TEST-ITEM-001",
        "question": "F-2-R 비자 소지자가 수도권으로 이전할 수 있나요?",
        "expected": {
            "source_fidelity": {
                "required_facts": ["인구감소지역 실거주의무", "체류자격 취소"],
                "forbidden_claims": ["수도권 이주 전면 자유 허용"],
            }
        }
    }

    # Case A: Clean prompt without target labels
    clean_prompt = "질문: F-2-R 비자 소지자가 수도권으로 이전할 수 있나요? 관련 규정에 따라 답변하십시오."
    assert len(detect_prompt_leakage(clean_prompt, gt_item)) == 0

    # Case B: Prompt leaked secret required fact
    leaked_prompt = f"질문: {gt_item['question']} (힌트: 반드시 '인구감소지역 실거주의무'를 명시하시오)"
    leaks = detect_prompt_leakage(leaked_prompt, gt_item)
    assert len(leaks) >= 1
    assert "인구감소지역 실거주의무" in leaks[0]

    # Case C: Prompt leaked forbidden claim
    leaked_forb = f"질문: {gt_item['question']} 주의: '수도권 이주 전면 자유 허용'이라고 답하지 마시오."
    leaks_forb = detect_prompt_leakage(leaked_forb, gt_item)
    assert len(leaks_forb) >= 1
    assert "수도권 이주 전면 자유 허용" in leaks_forb[0]


def test_benchmark_partition_integrity_zero_overlap():
    res = verify_benchmark_partitions()
    assert res["status"] == "valid"
    assert res["dev_items_count"] == 20
    assert res["heldout_items_count"] == 40
    assert res["total_items_count"] == 60
    assert res["overlap_count"] == 0


def test_partition_detects_artificial_overlap(tmp_path):
    # Create fake overlapping sets
    dev_file = tmp_path / "dev.json"
    hld_file = tmp_path / "hld.json"

    item_shared = {"id": "SHARED-001", "question": "q"}
    dev_file.write_text(json.dumps({"items": [item_shared] + [{"id": f"DEV-{i}", "question": "q"} for i in range(19)]}))
    hld_file.write_text(json.dumps({"items": [item_shared] + [{"id": f"HLD-{i}", "question": "q"} for i in range(39)]}))

    with pytest.raises(EvaluationIsolationError, match="Data contamination: 1 overlapping"):
        verify_benchmark_partitions(dev_path=dev_file, heldout_path=hld_file, candidates_path=tmp_path / "dummy.json")


def test_environment_isolation_audit_reports_honest_status():
    audit = get_environment_isolation_audit()
    assert audit["isolation_status"] == "isolation_not_verified"
    assert audit["clean_room_verified"] is False
    assert "The 40 held-out candidate items are stored in git" in audit["warning"]


def test_blind_benchmark_files_contain_zero_labels(tmp_path):
    committed_manifest = BENCHMARKS_DIR / "BENCHMARK_ISOLATION_MANIFEST.json"
    original_bytes = committed_manifest.read_bytes()
    res = generate_blind_benchmarks(output_dir=tmp_path)
    dev_blind = json.loads(Path(res["dev_blind_file"]).read_text(encoding="utf-8"))
    hld_blind = json.loads(Path(res["heldout_blind_file"]).read_text(encoding="utf-8"))

    assert len(dev_blind["items"]) == 20
    assert len(hld_blind["items"]) == 40

    # Ensure zero items have 'expected'
    assert all("expected" not in it for it in dev_blind["items"])
    assert all("expected" not in it for it in hld_blind["items"])

    # Manifest exists
    manifest_file = Path(res["manifest_file"])
    assert manifest_file.exists()
    assert manifest_file.parent == tmp_path
    assert committed_manifest.read_bytes() == original_bytes
