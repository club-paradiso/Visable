"""Mission 005-F: the real T4 acceptance run, the failed gate, and the DEV-20 run that did not happen.

One free Colab T4 model load (commit 9332333, contract v3) generated the 48 locked
acceptance cases and then the 24 development cases. The files are stored unmodified.
The gate failed, so DEV-20 was not executed; missing DEV-20 output is not zero accuracy.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import synthetic_safety_gate as gate

RUN = BOOT / "runs" / "mission005f"
ACC = RUN / "synthetic_acceptance"
DEVP = RUN / "development_diagnostic"
RAW_SHA256 = {
    ACC / "generations.jsonl": "a7a7248dd9e506553b7a3c42f37822ce2db3b0d08b9d106aa5f830d38651b133",
    ACC / "sessions.jsonl": "8cd2318fe7cc52de9f2c5f44a74b83e8e2c5d0ff04244fadb761b9d6ee3ae4a7",
    DEVP / "generations.jsonl": "6f55d8d1de095b2e04b52c5c583b2dac5fa2c09c0d5804f211d41be0db81d93e",
    DEVP / "sessions.jsonl": "d8ecc3c8ea6b2fc0ef1d6e08c9a4dc12541d1687fc91c79416f85da6269467de",
}
#: The decision record Colab wrote; re-scoring here reproduces it byte for byte.
COLAB_DECISION_SHA256 = "c3300769645eb049dbc8fa57ffef91180a9f1a8f8acc449c2431495426e7bb13"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.mark.parametrize("path", sorted(RAW_SHA256), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_raw_files_are_the_unmodified_colab_outputs(path):
    assert sha(path) == RAW_SHA256[path]


def test_one_model_load_frozen_commit_and_contract():
    acc = [json.loads(l) for l in (ACC / "sessions.jsonl").read_text().splitlines()]
    dev = [json.loads(l) for l in (DEVP / "sessions.jsonl").read_text().splitlines()]
    assert len(acc) == 1 and len(dev) == 1 and acc[0]["model_load_id"] == dev[0]["model_load_id"]
    s = acc[0]
    assert s["code"]["git_commit"] == "93323339ae5276a14dd858aed9d74e43326ccccb"
    assert s["code"]["code_files_modified_from_commit"] is False
    assert s["contract_version"] == "v3" and s["metadata"]["cuda_device"] == "Tesla T4"
    assert s["load"]["quantization"]["quantized_decoder_layers"] == 42


RUN_COMMIT_005F = "6f41d0b1b03edbe1ce521e7a0b0622e4db3d6de0"


def test_recorded_gate_decision_is_intact_and_fail():
    record = json.loads((ACC / "gate_decision.json").read_text())
    assert sha(ACC / "gate_decision.json") == COLAB_DECISION_SHA256
    assert gate.seal_ok(record) and record["decision"] == "fail" and record["dev20_permitted"] is False
    assert all(c["passed"] for c in record["preconditions"])


def test_gate_decision_reproduces_byte_for_byte_with_the_005f_code(tmp_path):
    """Mission 005-G later changed files the 005-F manifest froze, so the decision is
    re-derived with the code of the 005-F run commit, extracted from git."""
    import shutil
    import subprocess
    repo = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=BOOT, capture_output=True, text=True).stdout.strip() or "/nonexistent")
    if not (repo / ".git").exists() or shutil.which("tar") is None or subprocess.run(
            ["git", "cat-file", "-e", f"{RUN_COMMIT_005F}^{{commit}}"], cwd=repo, capture_output=True).returncode:
        pytest.skip("needs git history for the 005-F run commit")
    archive = subprocess.run(["git", "archive", RUN_COMMIT_005F, "experiments/waymaker-ai"], cwd=repo,
                             capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(tmp_path)], input=archive, check=True)
    root = tmp_path / "experiments" / "waymaker-ai"
    run = root / "artemis_bootstrap" / "runs" / "mission005f" / "synthetic_acceptance"
    (run / "gate_decision.json").unlink()
    result = subprocess.run([sys.executable, "-I", "artemis_bootstrap/synthetic_safety_gate.py", "score", "--out-dir", str(run)],
                            cwd=root, capture_output=True, text=True)
    assert result.returncode == 6, result.stderr[-800:]
    assert sha(run / "gate_decision.json") == COLAB_DECISION_SHA256


def test_current_scoring_logic_gives_the_same_005f_results():
    results, _ = gate.score_dir(ACC)
    committed = json.loads((ACC / "synthetic_acceptance_results.json").read_text())
    assert results["summary"] == committed["summary"]
    s = results["summary"]
    assert (s["executed"], s["passed"], s["failed"], s["unresolved"], s["critical_failures"]) == (48, 28, 20, 0, 12)
    assert s["critical_by_kind"] == {"inadmissible_citation": 4, "failed_to_withhold": 2, "value_from_inadmissible": 6}


def test_critical_failures_are_listed_case_by_case_not_averaged():
    record = json.loads((ACC / "gate_decision.json").read_text())
    assert any(r.startswith("critical_failures 12") for r in record["fail_reasons"])
    results = json.loads((ACC / "synthetic_acceptance_results.json").read_text())
    assert {c["case_id"] for c in results["summary"]["critical_failure_list"]} == {"A05F-10", "A05F-12", "A05F-34", "A05F-42"}


def test_dev20_was_not_executed_and_the_failed_decision_cannot_unlock_it():
    assert not (RUN / "dev20_v3").exists()
    with pytest.raises(gate.GateBlocked, match="not permitted"):
        gate.require_passing_gate(ACC / "gate_decision.json", "v3")
    analysis = json.loads((RUN / "analysis_005f.json").read_text())
    assert analysis["D"]["status"] == "not_executed" and analysis["C"]["decision"] == "fail"


def test_development_diagnostic_is_reported_apart_and_reproduces():
    doc, _ = gate.load_suite(BOOT / "validation" / "mission005f_synthetic_development.json")
    gens = {json.loads(l)["case_id"]: json.loads(l) for l in (DEVP / "generations.jsonl").read_text().splitlines()}
    summary = gate.summarize(gate.score_rows(doc["cases"], gens), gens)
    committed = json.loads((DEVP / "development_results.json").read_text())
    assert committed["summary"]["passed"] == summary["passed"] == 15
    assert "never the gate" in committed["label"]
