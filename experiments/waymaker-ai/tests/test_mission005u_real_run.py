"""Mission 005-U: the real T4 run — gate v16 passed, every conflict answered as a conflict on the first call.

One free Colab T4 model load (commit 829de8d, contract v15) processed the 81 locked acceptance cases;
gate v16 passed and DEV-20 v2 ran once. The files are stored unmodified; local re-scoring reproduces
the decision and both results files byte for byte. All seven conflict cases carried conflict_records and
the first answer of each was status conflict, so the status retry never fired. DEV-20 v2 scored 14/20:
item 004 received the same input as in 005-S under the longer v15 instructions and dropped the sentence
naming E-7-1. Synthetic acceptance and DEV-20 are Development Candidate Diagnostic, not Official Gold
Accuracy.
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
import synthetic_safety_gate_v16 as gate16
from score_dev20_guarded import read_jsonl

RUN = BOOT / "runs" / "mission005u"
ACC, DEV = RUN / "synthetic_acceptance", RUN / "dev20_v2"
RAW_SHA256 = {
    ACC / "gate_decision.json": "45790031db5252309719f86571583e4dce96be8b6f64901fe7bd98cff074c650",
    ACC / "generations.jsonl": "c99457b2655935b8f046ab07d634b6476ad50d9bf6252e0fe27f40c23f62b37b",
    ACC / "pipeline.jsonl": "32a11f8013ceaf75edc9a142ba283a4ee4749c7fdbdb0c0ba23b019f916d438d",
    ACC / "sessions.jsonl": "b2d0d20852415b1d19c405b0b538003ee2672ab165339458735f54b9d49b264c",
    ACC / "synthetic_acceptance_results.json": "5680fa2392ee149c2cb94d4be7221b1556fa9f30882387646c9caa0ac72a7816",
    DEV / "dev20_v2_results.json": "6c295abdec9d3b4a1e174975659479e1f408c44b77791cfbbef12fa4f8b27788",
    DEV / "generations.jsonl": "0ee7a5691f01b1ba523c6d7fd1d40aac4c515d4426bf957b273719b1118b793d",
    DEV / "pipeline.jsonl": "b8ce91ba6d33dacc7f40691b83a594d2df739ab2b7c5784291e8d893b46e89f9",
    DEV / "sessions.jsonl": "dc2d0010fd5783b8d148b2e39704b6957dabaff7d60b7ed90fca7e3534442bd1",
}
CONFLICT = ["A05U-28", "A05U-29", "A05U-30", "A05U-44", "A05U-56", "A05U-59", "A05U-67"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.mark.parametrize("path", sorted(RAW_SHA256), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_raw_files_are_the_unmodified_colab_outputs(path):
    assert sha(path) == RAW_SHA256[path]


def test_one_model_load_on_the_frozen_commit_and_contract_v15_for_both_parts():
    sessions = read_jsonl(ACC / "sessions.jsonl") + read_jsonl(DEV / "sessions.jsonl")
    assert len(sessions) == 2 and len({s["model_load_id"] for s in sessions}) == 1
    for s in sessions:
        assert s["code"]["git_commit"] == "829de8d41c3e7097ac3db317a5fab9ea43b4b59e"
        assert s["code"]["code_files_modified_from_commit"] is False and s["metadata"]["cuda_device"] == "Tesla T4"
        assert s["contract_version"] == "v15"
    assert read_jsonl(DEV / "sessions.jsonl")[0]["benchmark_sha256"] == dev20_v2.load_items()[1]


def test_recorded_gate_decision_is_intact_and_pass():
    record = json.loads((ACC / "gate_decision.json").read_text())
    assert gate16.seal_ok(record) and record["decision"] == "pass" and record["dev20_permitted"] is True
    assert record["fail_reasons"] == [] and record["blocked_reasons"] == []
    c = record["summary_counts"]
    assert (c["executed"], c["raw_model_called"], c["raw_pass"], c["raw_critical"]) == (81, 63, 62, 0)
    assert (c["end_to_end_correct"], c["critical_unsafe_released"], c["trust_bypass"], c["status_retries"]) == (81, 0, 0, 0)


def test_decision_and_both_results_reproduce_byte_for_byte(tmp_path):
    acc, dev = tmp_path / "acc", tmp_path / "dev"
    acc.mkdir()
    dev.mkdir()
    for name in ("generations.jsonl", "sessions.jsonl", "pipeline.jsonl"):
        shutil.copy(ACC / name, acc / name)
        shutil.copy(DEV / name, dev / name)
    results, record = gate16.score_dir(acc)
    gate16.write(acc, results, record)
    assert sha(acc / "gate_decision.json") == RAW_SHA256[ACC / "gate_decision.json"]
    assert sha(acc / "synthetic_acceptance_results.json") == RAW_SHA256[ACC / "synthetic_acceptance_results.json"]
    assert dev20_v2.main(["--out-dir", str(dev)]) == 0
    assert sha(dev / "dev20_v2_results.json") == RAW_SHA256[DEV / "dev20_v2_results.json"]


def test_the_stored_pass_unlocks_dev20_only_for_contract_v15():
    assert gate16.require_passing_gate(ACC / "gate_decision.json", "v15")["decision"] == "pass"
    with pytest.raises(gate16.GateBlocked, match="not v14"):
        gate16.require_passing_gate(ACC / "gate_decision.json", "v14")


def test_every_conflict_case_was_marked_and_answered_as_a_conflict_on_the_first_call():
    pipe = {r["case_id"]: r for r in read_jsonl(ACC / "pipeline.jsonl")}
    assert not any(r.get("status_retry") for r in pipe.values())
    for k in CONFLICT:
        first = json.loads(pipe[k]["raw_output"])
        assert first["status"] == "conflict" and len(first["citations"]) == 2
        assert pipe[k]["released"]["status"] == "conflict" and pipe[k]["released_provenance"] == "model_generated"
    rows = {r["case_id"]: r for r in json.loads((ACC / "synthetic_acceptance_results.json").read_text())["cases"]}
    assert all(rows[k]["raw"]["outcome"] == "pass" for k in CONFLICT)


def test_the_one_raw_miss_is_a_partial_without_the_uncovered_item_repaired_by_the_notice():
    rows = {r["case_id"]: r for r in json.loads((ACC / "synthetic_acceptance_results.json").read_text())["cases"]}
    assert [k for k, r in rows.items() if r["raw"]["outcome"] == "fail"] == ["A05U-48"]
    r = rows["A05U-48"]
    assert r["raw"]["checks"]["required_mentions"] is False and r["raw"]["status"] == "partial"
    assert r["end_to_end"]["correct"] is True and r["end_to_end"]["notice_repair"] is True


def test_dev20_v2_summary_and_item_004():
    result = json.loads((DEV / "dev20_v2_results.json").read_text())
    s = result["summary"]
    assert (s["model_called"], s["passed_all_dimensions"], s["passed_among_model_called"]) == (13, 14, 9)
    assert sorted(c["case_id"][-3:] for c in result["cases"] if not c["passed"]) == ["002", "003", "004", "005", "010", "020"]
    now = {r["case_id"]: r for r in read_jsonl(DEV / "pipeline.jsonl")}["ARTEMIS-004-DEV-004"]
    before = {r["case_id"]: r for r in read_jsonl(BOOT / "runs" / "mission005s" / "dev20_v2" / "pipeline.jsonl")}["ARTEMIS-004-DEV-004"]
    assert now["model_input_sha256s"] == before["model_input_sha256s"]   # same user input; only the instructions changed
    assert "E-7-1" in json.loads(before["raw_output"])["answer"] and "E-7-1" not in json.loads(now["raw_output"])["answer"]
