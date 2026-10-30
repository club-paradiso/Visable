"""Mission 005-F: what was frozen before inference stays frozen, and history stays unchanged."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import legal_review_packet
import synthetic_safety_gate as gate
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "1eb24ba83d695b79768be3ecb0a5aeb52ab1c90d8dcd1a74c4f4158905e14a8d"
V3_PROMPT_SHA256 = "9d78fb00d027"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_acceptance_manifest_is_the_frozen_one():
    assert sha(gate.MANIFEST) == MANIFEST_SHA256
    manifest = gate.load_manifest()
    assert manifest["status"] == "frozen_before_inference" and manifest["contract_version"] == "v3"
    assert manifest["prompt_sha256"] == prompt_sha256("v3") and manifest["prompt_sha256"].startswith(V3_PROMPT_SHA256)
    assert manifest["thresholds"]["max_critical_failures"] == 0


def test_offline_preconditions_pass_on_the_frozen_inputs():
    checks = gate.offline_preconditions(gate.load_manifest())
    assert all(c["passed"] for c in checks), [c for c in checks if not c["passed"]]


def test_acceptance_suite_is_balanced_and_multilingual():
    suite, _ = gate.load_suite(gate.ROOT / gate.load_manifest()["acceptance_suite"]["path"])
    cases = suite["cases"]
    assert len(cases) == 48
    assert all(sum(c["category"] == cat for c in cases) == 4 for cat in gate.CATEGORIES)
    assert sum(c["expected_language"] != "ko" for c in cases) >= 16
    assert {c["rule_role"] for c in cases} == {"positive", "negative"}


def test_reference_answers_correct_pass_and_wrong_fail():
    manifest = gate.load_manifest()
    suite, suite_sha = gate.load_suite(gate.ROOT / manifest["acceptance_suite"]["path"])
    ref = json.loads((gate.ROOT / manifest["evaluator_validation"]["reference_answers"]).read_text(encoding="utf-8"))
    assert ref["acceptance_sha256"] == suite_sha
    cases = {c["id"]: c for c in suite["cases"]}
    assert set(ref["answers"]) == set(cases)
    for cid, answers in ref["answers"].items():
        for a in answers:
            gen = {"case_id": cid, "execution_status": "completed", "contract_version": "v3",
                   "raw_output": json.dumps(a["response"], ensure_ascii=False)}
            outcome = gate.score_case(cases[cid], gen)["outcome"]
            assert outcome == ("pass" if a["kind"] == "correct" else "fail"), (cid, a["kind"])


def test_historical_artifacts_are_unchanged():
    freeze = json.loads((BOOT / "runs" / "mission005f" / "baseline_freeze.json").read_text())
    changed = [rel for rel, digest in freeze["artifact_sha256"].items() if sha(BOOT / rel) != digest]
    assert not changed, changed
    assert len(freeze["artifact_sha256"]) == 48


def test_benchmark_files_are_unchanged():
    iso = json.loads((BOOT / "benchmarks" / "BENCHMARK_ISOLATION_MANIFEST.json").read_text())
    assert sha(BOOT / "benchmarks" / "artemis_eval_dev_20.json") == iso["partitions"]["dev_sha256"]
    assert sha(BOOT / "benchmarks" / "artemis_eval_heldout_40.json") == iso["partitions"]["heldout_sha256"]


def test_review_packet_is_valid_unreviewed_and_changes_no_label():
    packet = json.loads((BOOT / "runs" / "mission005f" / "review_packet.json").read_text())
    assert legal_review_packet.validate(packet) == []
    assert len(packet["items"]) == 20 and all(i["review"]["state"] == "not_reviewed" for i in packet["items"])
    assert packet["independent_legal_review"] == "not_verified" and packet["benchmark_labels_changed"] is False


@pytest.mark.parametrize("mutate,problem", [
    (lambda it: it["review"].update(state="agree"), "reviewer name"),
    (lambda it: it["review"].update(state="unknown"), "unknown state"),
    (lambda it: it["review"].update(source_authentic="maybe"), "source_authentic"),
])
def test_review_validation_rejects_unattributed_or_malformed_decisions(mutate, problem):
    packet = json.loads((BOOT / "runs" / "mission005f" / "review_packet.json").read_text())
    mutate(packet["items"][0])
    assert any(problem in p for p in legal_review_packet.validate(packet))


def test_a_complete_disagreement_needs_authority_and_audit():
    packet = json.loads((BOOT / "runs" / "mission005f" / "review_packet.json").read_text())
    it = packet["items"][0]
    it["review"].update(state="disagree", reasoning="r", reviewed_at="2026-11-01",
                        reviewer={"name": "A", "role": "r", "qualification": "q", "organization": "o"})
    problems = legal_review_packet.validate(packet)
    assert any("legal authority" in p for p in problems) and any("audit_trail" in p for p in problems)
    it["review"]["legal_authority"] = [{"citation": "x", "url": "y", "accessed": "2026-11-01"}]
    it["audit_trail"] = [{"at": "t", "actor": "A", "action": "decide", "from_state": "not_reviewed", "to_state": "disagree"}]
    assert legal_review_packet.validate(packet) == []
