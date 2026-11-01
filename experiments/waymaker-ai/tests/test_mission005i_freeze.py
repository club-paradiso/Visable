"""Mission 005-I: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import synthetic_safety_gate_v3 as gate3
import synthetic_safety_gate_v4 as gate4
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "fa1bff6567981a190e001b3d9abdab8b6eff2ae8e71400fc76cc38ef04d5df45"
ACCEPTANCE_SHA256 = "2b99e457056e1f49f30b49a13dc8ca3a274096161944b6b55eee57319cb79527"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate4.MANIFEST) == MANIFEST_SHA256
    m = gate4.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-I" and m["contract_version"] == "v6"
    assert m["prompt_sha256"] == prompt_sha256("v6") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005h_thresholds_unchanged():
    assert gate4.load_manifest()["thresholds"] == gate3.load_manifest()["thresholds"]


#: Files Mission 005-J changed after the 005-I freeze. The 005-I manifest records them as they
#: were at that freeze; the 005-I decision is re-derived with that run commit's code (test_mission005i_real_run).
CHANGED_AFTER_005I = {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/language_compliance.py",
                      "artemis_bootstrap/gemma4_runtime.py",
                      "waymaker_ai/response_contract.py", "waymaker_ai/inference_input.py",
                      "waymaker_ai/evidence_admissibility.py", "artemis_bootstrap/trusted_evidence_spec.md"}
FREEZE_COMMIT_005I = "de1502da4e8a14b2b0d46642f67bfab99c211ea9"


def test_offline_preconditions_pass():
    checks = gate4.offline_preconditions(gate4.load_manifest())
    assert all(c["passed"] for c in checks if c["check"] != "evaluator_files_unchanged"), checks
    files = next(c for c in checks if c["check"] == "evaluator_files_unchanged")
    assert set(files["detail"] or {}) <= CHANGED_AFTER_005I, files


def test_005i_manifest_matches_the_files_at_its_freeze_commit():
    for rel, digest in gate4.load_manifest()["evaluator_files_sha256"].items():
        shown = subprocess.run(["git", "show", f"{FREEZE_COMMIT_005I}:experiments/waymaker-ai/{rel}"],
                               cwd=BOOT, capture_output=True)
        if shown.returncode:
            pytest.skip("needs git history for the 005-I freeze commit")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, rel


def test_acceptance_suite_shape():
    suite, _ = gate4.load_suite(gate4.ROOT / gate4.load_manifest()["acceptance_suite"]["path"])
    cases = suite["cases"]
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases) == 3 for k in gate4.CATEGORIES)
    assert sum(c["expected"]["end_to_end"] == "release_substantive" for c in cases) >= 38
    assert sum(c["expected"]["expected_language"] != "ko" for c in cases) >= 27


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005i_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_only_through_the_v4_gate():
    nb = BOOT / "notebooks" / "artemis_mission005i_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate4.run(prepared, ACC_DIR)" in text and "gate4.run_dev20(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005i_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
