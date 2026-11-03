"""Mission 005-N: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import synthetic_safety_gate_v8 as gate8
import synthetic_safety_gate_v9 as gate9
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "96343e0ed1468f74d745bc36eda05a50d8ea6e65af8504941602736a60a3755c"
ACCEPTANCE_SHA256 = "0c6e07b507592aee2c4cbd92a26249593d0bc37ed532c6120436572a01122db8"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate9.MANIFEST) == MANIFEST_SHA256
    m = gate9.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-N" and m["contract_version"] == "v11"
    assert m["prompt_sha256"] == prompt_sha256("v11") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005m_thresholds_unchanged():
    assert gate9.load_manifest()["thresholds"] == gate8.load_manifest()["thresholds"]


#: Files Missions 005-O, 005-P and 005-Q changed after the 005-N freeze. The 005-N manifest records them as they
#: were at that freeze; the 005-N decision is re-derived with that run commit's code (test_mission005n_real_run).
CHANGED_AFTER_005N = {"artemis_bootstrap/trusted_evidence_spec.md", "artemis_bootstrap/grounding_guard.py",
                      "artemis_bootstrap/gemma4_runtime.py", "waymaker_ai/response_contract.py", "waymaker_ai/inference_input.py",
                      "artemis_bootstrap/claim_support_validation.py",
                      # Mission 005-T
                      "waymaker_ai/evidence_admissibility.py"}
FREEZE_COMMIT_005N = "b74210c5cc06b059323efe3d27e7ea381f9669b0"


def test_offline_preconditions_pass():
    checks = gate9.offline_preconditions(gate9.load_manifest())
    assert all(c["passed"] for c in checks if c["check"] != "evaluator_files_unchanged"), checks
    files = next(c for c in checks if c["check"] == "evaluator_files_unchanged")
    assert set(files["detail"] or {}) <= CHANGED_AFTER_005N, files


def test_005n_manifest_matches_the_files_at_its_freeze_commit():
    for rel, digest in gate9.load_manifest()["evaluator_files_sha256"].items():
        shown = subprocess.run(["git", "show", f"{FREEZE_COMMIT_005N}:experiments/waymaker-ai/{rel}"],
                               cwd=BOOT, capture_output=True)
        if shown.returncode:
            pytest.skip("needs git history for the 005-N freeze commit")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, rel


def test_acceptance_suite_shape():
    suite, _ = gate9.load_suite(gate9.ROOT / gate9.load_manifest()["acceptance_suite"]["path"])
    cases = suite["cases"]
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases) == 3 for k in gate9.CATEGORIES)
    assert sum(c["expected"]["end_to_end"] == "release_substantive" for c in cases) >= 38
    assert sum(c["expected"]["expected_language"] != "ko" for c in cases) >= 27


def test_suite_has_double_language_requests():
    import language_compliance
    suite, _ = gate9.load_suite(gate9.ROOT / gate9.load_manifest()["acceptance_suite"]["path"])
    double = [c["id"] for c in suite["cases"] if len({lang for lang, p in language_compliance._REQUESTS.items()
                                                      if p.search(language_compliance._nfc(c["question"]).lower())}) > 1]
    assert len(double) >= 3, double


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005n_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_only_through_the_v9_gate():
    nb = BOOT / "notebooks" / "artemis_mission005n_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate9.run(prepared, ACC_DIR)" in text and "gate9.run_dev20(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005n_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256


def test_suite_covers_the_005n_focus():
    import grounding_guard as guard
    suite, _ = gate9.load_suite(gate9.ROOT / gate9.load_manifest()["acceptance_suite"]["path"])
    cases = suite["cases"]
    named = [c["id"] for c in cases if any(isinstance(e.get("source"), dict) and e["source"].get("document_id")
                                            and e["source"]["document_id"] in c["question"] for e in c["evidence"])]
    assert len(named) >= 3, named
    opening = [c["id"] for c in cases
               if any(c["question"].startswith(r + ",") for r in guard.remove_language_requests(c["question"])["removed"])]
    assert len(opening) >= 2, opening   # "Using Korean, list …"
