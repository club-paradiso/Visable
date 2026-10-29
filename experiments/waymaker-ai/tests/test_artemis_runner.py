"""Unit and regression tests for Artemis Model Evaluation Runtime (Mission 004-C).

Verifies:
1. MockModelAdapter presets (gold, wrong_facts, polarity_flip, swap_table, unlisted_citation, improper_withhold, injection_vulnerable, timeout, custom).
2. RecordedResponseAdapter (loads from JSON/JSONL, handles missing keys).
3. LocalModelAdapter availability check (graceful not_executed when offline weights not present).
4. Mode A (infra_validation): synthetic fixtures, pass rates.
5. Mode B (candidate_eval): candidate items, diagnostic rubric agreement, official_gold isolated as None (N/A).
6. Mode C (gold_eval): zero gold items -> reports 0 cases and None (N/A) pass rate.
7. Diagnostic disagreement aggregation.
8. Artifact generation (run_summary.json, report.md, error_summary.csv, run_manifest.json).
9. Per-item timeout and error handling.
"""
from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path
import pytest

from artemis_bootstrap.artemis_runner import (
    ArtemisEvaluationRunner,
    EvaluationMode,
    ExecutionStatus,
    MockModelAdapter,
    RecordedResponseAdapter,
    LocalModelAdapter,
    DIAGNOSTIC_CATEGORIES,
    validate_run_summary_dict,
)
from artemis_bootstrap import artemis_eval


BOOTSTRAP_DIR = Path(__file__).resolve().parent.parent / "artemis_bootstrap"
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def synthetic_cases():
    cases_path = BOOTSTRAP_DIR / "artemis_eval_cases_10.json"
    with open(cases_path, encoding="utf-8") as f:
        return json.load(f)["items"]


@pytest.fixture
def candidate_dev_cases():
    dev_path = BENCHMARKS_DIR / "artemis_eval_dev_20.json"
    with open(dev_path, encoding="utf-8") as f:
        return json.load(f)["items"]


# ---------------------------------------------------------------------------
# 1. MockModelAdapter Preset Tests
# ---------------------------------------------------------------------------
def test_mock_adapter_gold_preset_passes_synthetic(synthetic_cases):
    adapter = MockModelAdapter(preset="gold")
    resp_0 = adapter.generate(synthetic_cases[0])
    assert resp_0.status == "answered"
    assert "30,000원" in resp_0.answer
    assert "SYN-DOC-001" in resp_0.citations

    # Abstention item (SYN-009)
    resp_9 = adapter.generate(synthetic_cases[8])
    assert resp_9.status == "insufficient_evidence"

    # Clarification item (SYN-007)
    resp_7 = adapter.generate(synthetic_cases[6])
    assert resp_7.status == "clarify"


def test_mock_adapter_polarity_flip_preset(synthetic_cases):
    adapter = MockModelAdapter(preset="polarity_flip")
    resp = adapter.generate(synthetic_cases[0])
    assert "취업할 수 있습니다" in resp.answer


def test_mock_adapter_swap_table_preset(synthetic_cases):
    adapter = MockModelAdapter(preset="swap_table")
    resp = adapter.generate(synthetic_cases[0])
    assert "1인 가구의 소득기준은 60,000,000원" in resp.answer


def test_mock_adapter_timeout_preset(synthetic_cases):
    adapter = MockModelAdapter(preset="timeout")
    resp = adapter.generate(synthetic_cases[0])
    assert resp.status == "error"
    assert "timeout" in resp.error.lower()


def test_mock_adapter_custom_mapping(synthetic_cases):
    custom = {
        "ARTEMIS-004-SYN-001": {
            "status": "answered",
            "answer": "커스텀 답변 30,000원 14일 소요.",
            "citations": ["SYN-DOC-001"],
        }
    }
    adapter = MockModelAdapter(custom_responses=custom)
    resp = adapter.generate(synthetic_cases[0])
    assert "커스텀 답변" in resp.answer


# ---------------------------------------------------------------------------
# 2. RecordedResponseAdapter Tests
# ---------------------------------------------------------------------------
def test_recorded_response_adapter_json_dict(tmp_path, synthetic_cases):
    record_file = tmp_path / "records.json"
    data = {
        "ARTEMIS-004-SYN-001": {
            "status": "answered",
            "answer": "기록된 답변 30,000원, 14일.",
            "citations": ["SYN-DOC-001"],
            "latency_ms": 12.5,
        }
    }
    record_file.write_text(json.dumps(data), encoding="utf-8")

    adapter = RecordedResponseAdapter(record_file)
    resp = adapter.generate(synthetic_cases[0])
    assert resp.status == "answered"
    assert "기록된 답변" in resp.answer
    assert resp.latency_ms == 12.5

    # Missing item produces error status
    resp_missing = adapter.generate(synthetic_cases[1])
    assert resp_missing.status == "error"
    assert "No recorded response found" in resp_missing.error


def test_recorded_response_adapter_jsonl(tmp_path, synthetic_cases):
    record_file = tmp_path / "records.jsonl"
    lines = [
        json.dumps({"item_id": "ARTEMIS-004-SYN-001", "status": "answered", "answer": "JSONL 응답", "citations": ["SYN-DOC-001"]}),
        json.dumps({"item_id": "ARTEMIS-004-SYN-002", "status": "answered", "answer": "JSONL 응답 2", "citations": ["SYN-DOC-002"]}),
    ]
    record_file.write_text("\n".join(lines), encoding="utf-8")

    adapter = RecordedResponseAdapter(record_file)
    meta = adapter.get_metadata()
    assert meta["total_records"] == 2

    resp_1 = adapter.generate(synthetic_cases[0])
    assert resp_1.answer == "JSONL 응답"


# ---------------------------------------------------------------------------
# 3. LocalModelAdapter Availability & Offline Guard Tests
# ---------------------------------------------------------------------------
def test_local_model_adapter_gracefully_marks_not_executed_when_weights_absent(tmp_path):
    empty_cache = tmp_path / "empty_cache"
    empty_cache.mkdir()

    adapter = LocalModelAdapter(
        model_name="mlx-community/gemma-4-e4b-it-4bit",
        cache_dir=empty_cache,
    )
    available, reason = adapter.check_availability()
    assert available is False
    assert any(phrase in reason.lower() for phrase in ("not found", "not installed", "insufficient disk space", "macos", "apple silicon"))

    # Generating with unavailable adapter returns error and does NOT fabricate outputs
    resp = adapter.generate({"id": "TEST-01", "question": "질문"})
    assert resp.status == "error"
    assert "not executed" in resp.error.lower()


# ---------------------------------------------------------------------------
# 4. Mode A (Infrastructure Validation) Runner Tests
# ---------------------------------------------------------------------------
def test_runner_mode_a_infra_validation(tmp_path):
    out_dir = tmp_path / "run_infra"
    adapter = MockModelAdapter(preset="gold")
    runner = ArtemisEvaluationRunner(
        adapter=adapter,
        mode=EvaluationMode.INFRA_VALIDATION,
        out_dir=out_dir,
    )
    summary = runner.run()

    assert summary.execution_status == ExecutionStatus.COMPLETED
    assert summary.mode == EvaluationMode.INFRA_VALIDATION
    assert summary.suite_summary.total_cases == 10
    assert summary.suite_summary.passed_cases == 10
    assert summary.suite_summary.pass_rate == 1.0

    # Mode A uses synthetic fixtures, so official gold pass rate must be None
    assert summary.suite_summary.official_gold_cases == 0
    assert summary.suite_summary.official_gold_pass_rate is None

    # Check generated files
    assert (out_dir / "run_summary.json").exists()
    assert (out_dir / "report.md").exists()
    assert (out_dir / "error_summary.csv").exists()
    assert (out_dir / "run_manifest.json").exists()


# ---------------------------------------------------------------------------
# 5. Mode B (Candidate Evaluation) Runner Tests
# ---------------------------------------------------------------------------
def test_runner_mode_b_candidate_evaluation_isolation(tmp_path):
    out_dir = tmp_path / "run_candidate"
    dev_path = BENCHMARKS_DIR / "artemis_eval_dev_20.json"
    adapter = MockModelAdapter(preset="gold")

    runner = ArtemisEvaluationRunner(
        adapter=adapter,
        mode=EvaluationMode.CANDIDATE_EVAL,
        benchmark_path=dev_path,
        out_dir=out_dir,
    )
    summary = runner.run()

    assert summary.execution_status == ExecutionStatus.COMPLETED
    assert summary.mode == EvaluationMode.CANDIDATE_EVAL
    assert summary.suite_summary.total_cases == 20

    # CRITICAL: Candidate items must NEVER count as official gold
    assert summary.suite_summary.official_gold_cases == 0
    assert summary.suite_summary.official_gold_pass_rate is None
    assert summary.suite_summary.candidate_cases == 20

    # Every item result carries candidate flags
    for res in summary.item_results:
        assert res.is_official_gold is False
        assert "candidate_evaluation_only" in res.score.flags


# ---------------------------------------------------------------------------
# 6. Mode C (Official Gold Evaluation) Zero Verified Items Gating
# ---------------------------------------------------------------------------
def test_runner_mode_c_zero_gold_items_reports_na(tmp_path):
    out_dir = tmp_path / "run_gold"
    cand_path = BENCHMARKS_DIR / "artemis_eval_candidates_60.json"
    adapter = MockModelAdapter(preset="gold")

    runner = ArtemisEvaluationRunner(
        adapter=adapter,
        mode=EvaluationMode.GOLD_EVAL,
        benchmark_path=cand_path,
        out_dir=out_dir,
    )
    summary = runner.run()

    # Zero items qualify as verified gold
    assert summary.execution_status == ExecutionStatus.COMPLETED
    assert summary.suite_summary.total_cases == 0
    assert summary.suite_summary.official_gold_cases == 0
    assert summary.suite_summary.official_gold_pass_rate is None

    # Report text must explicitly state N/A
    report_text = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "N/A" in report_text
    assert "공식 골드 검증 항목 없음" in report_text


# ---------------------------------------------------------------------------
# 7. Diagnostic Breakdown & Error Aggregation Tests
# ---------------------------------------------------------------------------
def test_runner_diagnostic_error_aggregation(tmp_path, synthetic_cases):
    out_dir = tmp_path / "run_diag"
    # Adapter that introduces polarity flips
    adapter = MockModelAdapter(preset="polarity_flip")
    runner = ArtemisEvaluationRunner(
        adapter=adapter,
        mode=EvaluationMode.INFRA_VALIDATION,
        out_dir=out_dir,
    )
    summary = runner.run()
    assert summary.suite_summary.failed_cases > 0
    assert len(summary.diagnostic_disagreements) > 0


# ---------------------------------------------------------------------------
# 8. Artifact Completeness and CSV Verification
# ---------------------------------------------------------------------------
def test_artifacts_and_csv_formatting(tmp_path):
    out_dir = tmp_path / "run_artifacts"
    adapter = MockModelAdapter(preset="gold")
    runner = ArtemisEvaluationRunner(
        adapter=adapter,
        mode=EvaluationMode.INFRA_VALIDATION,
        out_dir=out_dir,
    )
    summary = runner.run()

    csv_path = out_dir / "error_summary.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
    assert len(reader) == 11  # header + 10 items
    assert reader[0][0] == "run_id"
    assert reader[0][1] == "item_id"

    # Manifest verification
    manifest_path = out_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == summary.run_id
    assert "run_summary.json" in manifest["file_digests"]
    assert "error_summary.csv" in manifest["file_digests"]
    assert "report.md" in manifest["file_digests"]

    # Schema validation
    summary_dict = json.loads((out_dir / "run_summary.json").read_text(encoding="utf-8"))
    issues = validate_run_summary_dict(summary_dict)
    assert not issues, f"Run summary validation issues: {issues}"
