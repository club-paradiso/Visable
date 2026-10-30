"""Mission 005-E: regressions anchored on the real contract-v2 T4 generations.

One free Colab T4 model load produced both suites (synthetic, then DEV-20) under
contract v2. The files are stored unmodified. Scores are Development Candidate
Diagnostic Performance and synthetic specification checks, never Official Gold
Accuracy, and they say nothing about legal correctness.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import compare_005e
import score_dev20
from waymaker_ai.response_contract import prompt_sha256

E005 = BOOT / "runs" / "mission005e"
DEV = E005 / "dev20_contract_v2"
SYN = E005 / "synthetic_validation"
RAW_SHA256 = {
    DEV / "generations.jsonl": "158ad2db00d8d63114fbcee14f6a842bca22b84017e1f2aaf198eaa8295b7389",
    DEV / "sessions.jsonl": "b1fff321f364357d257a42cad4e361104178e7661035ec694c8ca83db9f9dad2",
    SYN / "generations.jsonl": "a432d6504249e2de1a8e88cdc7e81f379487f6e26922cb8b48d05c8fd356e689",
    SYN / "sessions.jsonl": "bf57951f875596a9241650ddc108a8d8b9caf9881a16df315b7837909c1d0e33",
}


def committed(path):
    return json.loads(path.read_text())


@pytest.mark.parametrize("path", sorted(RAW_SHA256), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_raw_files_are_the_unmodified_colab_outputs(path):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == RAW_SHA256[path]


def test_both_suites_come_from_one_model_load_under_contract_v2():
    sessions = score_dev20.read_jsonl(DEV / "sessions.jsonl") + score_dev20.read_jsonl(SYN / "sessions.jsonl")
    assert len(sessions) == 2 and len({s["model_load_id"] for s in sessions}) == 1
    for s in sessions:
        assert s["contract_version"] == "v2" and s["prompt_sha256"] == prompt_sha256("v2")
        assert s["code"]["git_commit"] == "f7c751b5172a59155e35ea7750f5ddf75054aaea"
        assert s["code"]["code_files_modified_from_commit"] is False and s["reproduction_pins_matched"] is True
        assert s["metadata"]["cuda_device"] == "Tesla T4" and s["load"]["quantization"]["passed"] is True
    for path in (DEV, SYN):
        gens = score_dev20.read_jsonl(path / "generations.jsonl")
        assert {g["contract_version"] for g in gens} == {"v2"}
        assert {g["finish_reason"] for g in gens} == {"eos"}


def test_v2_dev20_artifacts_reproduce_and_integrity_passes():
    result = score_dev20.score(DEV)
    assert result["integrity"]["passed"] is True and not result["integrity"]["prompt_leakage"]
    assert result["metrics"]["diagnostic_candidate_pass"] == committed(DEV / "performance_metrics.json")["diagnostic_candidate_pass"]
    assert result["metrics"]["official_gold_accuracy"] is None
    assert committed(DEV / "execution_manifest.json")["mission"] == "005-E"


def test_synthetic_results_reproduce_and_every_input_hash_matches():
    result = score_dev20.score_synthetic(SYN)
    assert result == committed(SYN / "synthetic_validation_results.json")
    assert all(c["input_sha256_ok"] for c in result["cases"])
    assert result["summary"]["executed"] == 15


def test_comparison_keeps_the_three_labels_apart():
    comparison = committed(E005 / "score_comparison.json")
    assert comparison["labels"]["A"] == "Original DEV-20 baseline"
    assert comparison["labels"]["B"] == "Evaluator-only rescoring"
    assert comparison["labels"]["C"] == "Contract-v2 model re-evaluation"
    assert comparison["official_gold_accuracy"] is None and comparison["independent_legal_review"] == "not_verified"
    stats = comparison["statistics"]
    attributed = stats["c_pass_attribution"]
    assert len(attributed["passes_with_original_evaluator"]) + len(attributed["passes_only_with_repaired_evaluator"]) \
        == comparison["C"]["diagnostic_candidate_pass"]["numerator"]
    assert any("in-sample" in c for c in stats["caveats"])


def test_b_and_c_in_the_comparison_match_fresh_scoring():
    comparison = committed(E005 / "score_comparison.json")
    b = score_dev20.score(BOOT / "runs" / "mission005d-dev20")
    c = score_dev20.score(DEV)
    assert comparison["B"]["diagnostic_candidate_pass"] == b["metrics"]["diagnostic_candidate_pass"]
    assert comparison["C"]["diagnostic_candidate_pass"] == c["metrics"]["diagnostic_candidate_pass"]
    assert comparison["C"]["dimension_pass"] == c["metrics"]["dimension_pass"]


def _has_baseline_commit():
    return subprocess.run(["git", "cat-file", "-e", f"{compare_005e.BASELINE_COMMIT}^{{commit}}"], cwd=BOOT,
                          capture_output=True).returncode == 0


@pytest.mark.skipif(not _has_baseline_commit(), reason="needs git history for the original evaluator")
def test_c_legacy_reproduces_with_the_original_evaluator():
    comparison = committed(E005 / "score_comparison.json")
    legacy = compare_005e.legacy_score(DEV)
    assert comparison["C_legacy"]["diagnostic_candidate_pass"] == legacy["metrics"]["diagnostic_candidate_pass"]


def test_wilson_and_mcnemar_helpers():
    assert compare_005e.wilson(0, 20) == [0.0, 0.1611]
    assert compare_005e.mcnemar_exact({"a": "fail", "b": "fail"}, {"a": "pass", "b": "fail"}) == \
        {"fail_to_pass": 1, "pass_to_fail": 0, "discordant": 1, "exact_p_two_sided": 1.0}
    thirteen = {str(i): "fail" for i in range(13)}
    assert compare_005e.mcnemar_exact(thirteen, {k: "pass" for k in thirteen})["exact_p_two_sided"] == 0.000244
