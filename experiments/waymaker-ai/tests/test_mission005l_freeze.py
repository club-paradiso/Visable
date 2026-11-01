"""Mission 005-L: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import synthetic_safety_gate_v6 as gate6
import synthetic_safety_gate_v7 as gate7
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "75a49c77e7d7674aaea0697f38a8d2dd95526fb38ebc9c0111b57fff87758ee7"
ACCEPTANCE_SHA256 = "fd3d55bfa6c85b7d0a9ef9d51739e0dd3186da8af2dd151fc487d4b5316cc0db"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate7.MANIFEST) == MANIFEST_SHA256
    m = gate7.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-L" and m["contract_version"] == "v9"
    assert m["prompt_sha256"] == prompt_sha256("v9") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005k_thresholds_unchanged():
    assert gate7.load_manifest()["thresholds"] == gate6.load_manifest()["thresholds"]


#: Files Mission 005-M changed after the 005-L freeze. The 005-L manifest records them as they
#: were at that freeze; the 005-L decision is re-derived with that run commit's code (test_mission005l_real_run).
CHANGED_AFTER_005L = {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/gemma4_runtime.py",
                      "artemis_bootstrap/claim_support_validation.py", "waymaker_ai/response_contract.py",
                      "waymaker_ai/inference_input.py", "artemis_bootstrap/trusted_evidence_spec.md"}
FREEZE_COMMIT_005L = "be4726a25c4d52234678d821f925ceb30e93600c"


def test_offline_preconditions_pass():
    checks = gate7.offline_preconditions(gate7.load_manifest())
    assert all(c["passed"] for c in checks if c["check"] != "evaluator_files_unchanged"), checks
    files = next(c for c in checks if c["check"] == "evaluator_files_unchanged")
    assert set(files["detail"] or {}) <= CHANGED_AFTER_005L, files


def test_005l_manifest_matches_the_files_at_its_freeze_commit():
    for rel, digest in gate7.load_manifest()["evaluator_files_sha256"].items():
        shown = subprocess.run(["git", "show", f"{FREEZE_COMMIT_005L}:experiments/waymaker-ai/{rel}"],
                               cwd=BOOT, capture_output=True)
        if shown.returncode:
            pytest.skip("needs git history for the 005-L freeze commit")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, rel


def test_acceptance_suite_shape():
    suite, _ = gate7.load_suite(gate7.ROOT / gate7.load_manifest()["acceptance_suite"]["path"])
    cases = suite["cases"]
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases) == 3 for k in gate7.CATEGORIES)
    assert sum(c["expected"]["end_to_end"] == "release_substantive" for c in cases) >= 38
    assert sum(c["expected"]["expected_language"] != "ko" for c in cases) >= 27


def test_suite_has_double_language_requests():
    import language_compliance
    suite, _ = gate7.load_suite(gate7.ROOT / gate7.load_manifest()["acceptance_suite"]["path"])
    double = [c["id"] for c in suite["cases"] if len({lang for lang, p in language_compliance._REQUESTS.items()
                                                      if p.search(language_compliance._nfc(c["question"]).lower())}) > 1]
    assert len(double) >= 3, double


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005l_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_only_through_the_v7_gate():
    nb = BOOT / "notebooks" / "artemis_mission005l_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate7.run(prepared, ACC_DIR)" in text and "gate7.run_dev20(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005l_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
