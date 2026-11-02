"""Mission 005-M: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import synthetic_safety_gate_v7 as gate7
import synthetic_safety_gate_v8 as gate8
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "2ba9dbfa3c704eb0492deceba75c6cb5ae018388a883cf86e4cfa817f16d5e90"
ACCEPTANCE_SHA256 = "e6f6e836e82cc4589ba0e39a0e2472f5d256cb3776e3c4bf19c15a1ebb5d3d25"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate8.MANIFEST) == MANIFEST_SHA256
    m = gate8.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-M" and m["contract_version"] == "v10"
    assert m["prompt_sha256"] == prompt_sha256("v10") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005l_thresholds_unchanged():
    assert gate8.load_manifest()["thresholds"] == gate7.load_manifest()["thresholds"]


#: Files Missions 005-N and 005-P changed after the 005-M freeze. The 005-M manifest records them as they
#: were at that freeze; the 005-M decision is re-derived with that run commit's code (test_mission005m_real_run).
CHANGED_AFTER_005M = {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/gemma4_runtime.py",
                      "artemis_bootstrap/claim_support_validation.py", "waymaker_ai/response_contract.py",
                      "waymaker_ai/evidence_admissibility.py", "artemis_bootstrap/trusted_evidence_spec.md",
                      "waymaker_ai/inference_input.py"}
FREEZE_COMMIT_005M = "824e0912b268f87f10db5f0beccabda8b8253889"


def test_offline_preconditions_pass():
    checks = gate8.offline_preconditions(gate8.load_manifest())
    assert all(c["passed"] for c in checks if c["check"] != "evaluator_files_unchanged"), checks
    files = next(c for c in checks if c["check"] == "evaluator_files_unchanged")
    assert set(files["detail"] or {}) <= CHANGED_AFTER_005M, files


def test_005m_manifest_matches_the_files_at_its_freeze_commit():
    for rel, digest in gate8.load_manifest()["evaluator_files_sha256"].items():
        shown = subprocess.run(["git", "show", f"{FREEZE_COMMIT_005M}:experiments/waymaker-ai/{rel}"],
                               cwd=BOOT, capture_output=True)
        if shown.returncode:
            pytest.skip("needs git history for the 005-M freeze commit")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, rel


def test_acceptance_suite_shape():
    suite, _ = gate8.load_suite(gate8.ROOT / gate8.load_manifest()["acceptance_suite"]["path"])
    cases = suite["cases"]
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases) == 3 for k in gate8.CATEGORIES)
    assert sum(c["expected"]["end_to_end"] == "release_substantive" for c in cases) >= 38
    assert sum(c["expected"]["expected_language"] != "ko" for c in cases) >= 27


def test_suite_has_double_language_requests():
    import language_compliance
    suite, _ = gate8.load_suite(gate8.ROOT / gate8.load_manifest()["acceptance_suite"]["path"])
    double = [c["id"] for c in suite["cases"] if len({lang for lang, p in language_compliance._REQUESTS.items()
                                                      if p.search(language_compliance._nfc(c["question"]).lower())}) > 1]
    assert len(double) >= 3, double


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005m_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_only_through_the_v8_gate():
    nb = BOOT / "notebooks" / "artemis_mission005m_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate8.run(prepared, ACC_DIR)" in text and "gate8.run_dev20(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005m_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
