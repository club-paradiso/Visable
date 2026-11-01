"""Mission 005-J: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import synthetic_safety_gate_v4 as gate4
import synthetic_safety_gate_v5 as gate5
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "199eba456a2cb7ecd611c7f1d8fc980a84189a2c21f48cc0ede543cfb008bcb3"
ACCEPTANCE_SHA256 = "6fbfffc9273d1f214ce5437e0a19acb5d3b078bce418c2ad3b7a32da00d595f1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate5.MANIFEST) == MANIFEST_SHA256
    m = gate5.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-J" and m["contract_version"] == "v7"
    assert m["prompt_sha256"] == prompt_sha256("v7") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005i_thresholds_unchanged():
    assert gate5.load_manifest()["thresholds"] == gate4.load_manifest()["thresholds"]


#: Files Mission 005-K changed after the 005-J freeze. The 005-J manifest records them as they
#: were at that freeze; the 005-J decision is re-derived with that run commit's code (test_mission005j_real_run).
CHANGED_AFTER_005J = {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/language_compliance.py",
                      "artemis_bootstrap/gemma4_runtime.py", "waymaker_ai/response_contract.py",
                      "waymaker_ai/inference_input.py", "waymaker_ai/evidence_admissibility.py",
                      "artemis_bootstrap/trusted_evidence_spec.md"}
FREEZE_COMMIT_005J = "9dc34d2f2be44fc898ad193c3821c3cc04154e42"


def test_offline_preconditions_pass():
    checks = gate5.offline_preconditions(gate5.load_manifest())
    assert all(c["passed"] for c in checks if c["check"] != "evaluator_files_unchanged"), checks
    files = next(c for c in checks if c["check"] == "evaluator_files_unchanged")
    assert set(files["detail"] or {}) <= CHANGED_AFTER_005J, files


def test_005j_manifest_matches_the_files_at_its_freeze_commit():
    for rel, digest in gate5.load_manifest()["evaluator_files_sha256"].items():
        shown = subprocess.run(["git", "show", f"{FREEZE_COMMIT_005J}:experiments/waymaker-ai/{rel}"],
                               cwd=BOOT, capture_output=True)
        if shown.returncode:
            pytest.skip("needs git history for the 005-J freeze commit")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, rel


def test_acceptance_suite_shape():
    suite, _ = gate5.load_suite(gate5.ROOT / gate5.load_manifest()["acceptance_suite"]["path"])
    cases = suite["cases"]
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases) == 3 for k in gate5.CATEGORIES)
    assert sum(c["expected"]["end_to_end"] == "release_substantive" for c in cases) >= 38
    assert sum(c["expected"]["expected_language"] != "ko" for c in cases) >= 27


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005j_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_only_through_the_v5_gate():
    nb = BOOT / "notebooks" / "artemis_mission005j_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate5.run(prepared, ACC_DIR)" in text and "gate5.run_dev20(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005j_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
