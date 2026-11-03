"""Mission 005-P: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import synthetic_safety_gate_v10 as gate10
import synthetic_safety_gate_v11 as gate11
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "c80695c0f9d401d6de0ea34fcc0a194369b061ba0618089c81026fc88acf7078"
ACCEPTANCE_SHA256 = "ecfdbe0934e08a9454b1d3d420d075195dab65ab502dad5665c974025117be48"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite():
    return gate11.load_suite(gate11.ROOT / gate11.load_manifest()["acceptance_suite"]["path"])[0]["cases"]


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate11.MANIFEST) == MANIFEST_SHA256
    m = gate11.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-P" and m["contract_version"] == "v12"
    assert m["prompt_sha256"] == prompt_sha256("v12") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005o_thresholds_unchanged():
    assert gate11.load_manifest()["thresholds"] == gate10.load_manifest()["thresholds"]


#: Files Mission 005-Q changed after the 005-P freeze. The 005-P manifest records them as they
#: were at that freeze; the 005-P decision is re-derived with that run commit's code (test_mission005p_real_run).
CHANGED_AFTER_005P = {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/claim_support_validation.py",
                      "artemis_bootstrap/trusted_evidence_spec.md",
                      # Mission 005-R
                      "artemis_bootstrap/gemma4_runtime.py", "waymaker_ai/inference_input.py", "waymaker_ai/response_contract.py"}
FREEZE_COMMIT_005P = "158e797477b456894ca1d98527f7edea275c8eba"


def test_offline_preconditions_pass():
    checks = gate11.offline_preconditions(gate11.load_manifest())
    assert all(c["passed"] for c in checks if c["check"] != "evaluator_files_unchanged"), checks
    files = next(c for c in checks if c["check"] == "evaluator_files_unchanged")
    assert set(files["detail"] or {}) <= CHANGED_AFTER_005P, files


def test_005p_manifest_matches_the_files_at_its_freeze_commit():
    for rel, digest in gate11.load_manifest()["evaluator_files_sha256"].items():
        shown = subprocess.run(["git", "show", f"{FREEZE_COMMIT_005P}:experiments/waymaker-ai/{rel}"],
                               cwd=BOOT, capture_output=True)
        if shown.returncode:
            pytest.skip("needs git history for the 005-P freeze commit")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, rel


def test_the_retry_pipeline_and_gate_v11_are_frozen():
    files = gate11.load_manifest()["evaluator_files_sha256"]
    assert {"artemis_bootstrap/synthetic_safety_gate_v11.py", "artemis_bootstrap/grounding_guard.py",
            "artemis_bootstrap/conflict_resolution.py", "waymaker_ai/inference_input.py"} <= set(files)


def test_acceptance_suite_shape_and_the_vietnamese_focus():
    cases = suite()
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases) == 3 for k in gate11.CATEGORIES)
    assert sum(c["expected"]["end_to_end"] == "release_substantive" for c in cases) >= 38
    assert sum(c["expected"]["expected_language"] != "ko" for c in cases) >= 27
    assert sum(c["expected"]["expected_language"] == "vi" for c in cases) >= 13


def test_true_conflicts_list_one_group_per_value_and_one_asks_per_document():
    conflicts = [c for c in suite() if "conflict" in c["expected"]["model_statuses"]]
    assert len(conflicts) == 3
    for c in conflicts:
        assert len(c["expected"]["required_mentions"]) == 2 and "conflict_treated_as_resolved" in c["expected"]["critical_rules"]
    assert any(re.search(r"\beach\b|각각|mỗi", c["question"], re.IGNORECASE) for c in conflicts)


def test_suite_keeps_the_earlier_coverage():
    import grounding_guard as guard
    import language_compliance
    cases = suite()
    double = [c["id"] for c in cases if len({lang for lang, p in language_compliance._REQUESTS.items()
                                             if p.search(language_compliance._nfc(c["question"]).lower())}) > 1]
    assert len(double) >= 3, double
    named = [c["id"] for c in cases if any(isinstance(e.get("source"), dict) and e["source"].get("document_id")
                                            and e["source"]["document_id"] in c["question"] for e in c["evidence"])]
    assert len(named) >= 3, named
    opening = [c["id"] for c in cases
               if any(c["question"].startswith(r + ",") for r in guard.remove_language_requests(c["question"])["removed"])]
    assert len(opening) >= 2, opening


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005p_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_only_through_the_v11_gate():
    nb = BOOT / "notebooks" / "artemis_mission005p_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate11.run(prepared, ACC_DIR)" in text and "gate11.run_dev20(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005p_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
