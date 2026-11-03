"""Mission 005-S: the real T4 run — gate v14 passed, then DEV-20 v2 through the pipeline with the v2 registry.

One free Colab T4 model load (commit e12f8f5, contract v13) processed the 81 locked acceptance cases;
gate v14 passed, and DEV-20 v2 ran once. The files are stored unmodified; local re-scoring reproduces
the decision and both results files byte for byte. In DEV-20 v2 item 011 the model again gave only one
of its two cases; the branch retry quoted the other case and the retried answer, which states both,
was released and passes every check. Synthetic acceptance and DEV-20 are Development Candidate
Diagnostic, not Official Gold Accuracy.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import dev20_v2
import synthetic_safety_gate_v14 as gate14
from score_dev20_guarded import read_jsonl

RUN = BOOT / "runs" / "mission005s"
ACC, DEV = RUN / "synthetic_acceptance", RUN / "dev20_v2"
RAW_SHA256 = {
    ACC / "gate_decision.json": "038872d44ce0f07b8d814807300ba4e2e77074aab55e8cba2bbaf178590b30e5",
    ACC / "generations.jsonl": "044c81c772787434339d389344ba3ac6eb37e6e442530d484a7e679e47110365",
    ACC / "pipeline.jsonl": "f3f53d4890a5da410c8c92500c0dc6c42345a28fa3c330a4c6bed9a696f71bc9",
    ACC / "sessions.jsonl": "62a1cb8e28a035759092ea86e81d3e12e3794ba875eb408dea10396204997743",
    ACC / "synthetic_acceptance_results.json": "768d9a1bcd801708e236363f3afbb8479a2ade612ef239d01093fa5c94edb210",
    DEV / "dev20_v2_results.json": "65c9ad4caecdd921c9517859f9ca2f770b8d0df13b77819b7c64d2d66f8e6a6b",
    DEV / "generations.jsonl": "3d26996df19a67ca88faab3239637a03cc51f08269ea85bcc9a190d3f3ee4918",
    DEV / "pipeline.jsonl": "8ed64d1967f41005257012f94f1f3ca76304327e6a5ed43f08f5eb6721420eb9",
    DEV / "sessions.jsonl": "60de1139df65da3cb9924ba4bac36e0d61f18058633ca01e92775c4180b8c9ed",
}
CAP = ["A05S-01", "A05S-02", "A05S-03", "A05S-37", "A05S-44", "A05S-59", "A05S-61", "A05S-62", "A05S-63", "A05S-38", "A05S-39", "A05S-45"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.mark.parametrize("path", sorted(RAW_SHA256), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_raw_files_are_the_unmodified_colab_outputs(path):
    assert sha(path) == RAW_SHA256[path]


def test_one_model_load_on_the_frozen_commit_for_both_parts():
    sessions = read_jsonl(ACC / "sessions.jsonl") + read_jsonl(DEV / "sessions.jsonl")
    assert len(sessions) == 2 and len({s["model_load_id"] for s in sessions}) == 1
    for s in sessions:
        assert s["code"]["git_commit"] == "e12f8f5391b164d396415bf0b50188faa1c34c74"
        assert s["code"]["code_files_modified_from_commit"] is False and s["metadata"]["cuda_device"] == "Tesla T4"
    assert read_jsonl(DEV / "sessions.jsonl")[0]["benchmark_sha256"] == dev20_v2.load_items()[1]


def test_recorded_gate_decision_is_intact_and_pass():
    record = json.loads((ACC / "gate_decision.json").read_text())
    assert gate14.seal_ok(record) and record["decision"] == "pass" and record["dev20_permitted"] is True
    assert record["fail_reasons"] == [] and record["blocked_reasons"] == []
    c = record["summary_counts"]
    assert (c["executed"], c["raw_model_called"], c["raw_pass"], c["raw_critical"]) == (81, 63, 60, 0)
    assert (c["end_to_end_correct"], c["critical_unsafe_released"], c["trust_bypass"], c["false_blocks"]) == (79, 0, 0, 0)


def test_decision_and_both_results_reproduce_byte_for_byte(tmp_path):
    acc, dev = tmp_path / "acc", tmp_path / "dev"
    acc.mkdir(), dev.mkdir()
    for name in ("generations.jsonl", "sessions.jsonl", "pipeline.jsonl"):
        shutil.copy(ACC / name, acc / name)
        shutil.copy(DEV / name, dev / name)
    results, record = gate14.score_dir(acc)
    gate14.write(acc, results, record)
    assert sha(acc / "gate_decision.json") == RAW_SHA256[ACC / "gate_decision.json"]
    assert sha(acc / "synthetic_acceptance_results.json") == RAW_SHA256[ACC / "synthetic_acceptance_results.json"]
    assert dev20_v2.main(["--out-dir", str(dev)]) == 0
    assert sha(dev / "dev20_v2_results.json") == RAW_SHA256[DEV / "dev20_v2_results.json"]


def test_the_stored_pass_unlocks_dev20_only_for_contract_v13():
    assert gate14.require_passing_gate(ACC / "gate_decision.json", "v13")["decision"] == "pass"
    with pytest.raises(gate14.GateBlocked, match="not v12"):
        gate14.require_passing_gate(ACC / "gate_decision.json", "v12")


def test_every_cap_case_passed():
    rows = {r["case_id"]: r for r in json.loads((ACC / "synthetic_acceptance_results.json").read_text())["cases"]}
    assert all(rows[c]["raw"]["outcome"] == "pass" and rows[c]["end_to_end"]["correct"] for c in CAP)


def test_dev20_v2_summary_and_failures():
    result = json.loads((DEV / "dev20_v2_results.json").read_text())
    s = result["summary"]
    assert (s["model_called"], s["passed_all_dimensions"], s["passed_among_model_called"]) == (13, 15, 10)
    assert sorted(c["case_id"][-3:] for c in result["cases"] if not c["passed"]) == ["002", "003", "005", "010", "020"]


def test_item_011_was_asked_once_more_and_the_retried_answer_was_released():
    record = {r["case_id"]: r for r in read_jsonl(DEV / "pipeline.jsonl")}["ARTEMIS-004-DEV-011"]
    first = json.loads(record["raw_output"])["answer"]
    assert "15 days" in first and "permission" not in first
    retried = json.loads(record["branch_retry"]["raw_outputs"][0])["answer"]
    assert "Any other foreigner must obtain permission" in retried
    assert record["released"]["answer"] == retried and record["released_provenance"] == "model_generated"
    assert not record["released"].get("system_notice")
