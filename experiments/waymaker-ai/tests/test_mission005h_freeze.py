"""Mission 005-H: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import synthetic_safety_gate_v2 as gate2
import synthetic_safety_gate_v3 as gate3
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "3c1cc7c6d1232fc2821d8f35aea79d4b3a7b9eb62fbab64dd1e5050d070cf17c"
ACCEPTANCE_SHA256 = "82fe75e4ab378295e3a70cfedad42a2da4bb622712c21980f852d1bb63fadd34"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate3.MANIFEST) == MANIFEST_SHA256
    m = gate3.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-H" and m["contract_version"] == "v5"
    assert m["prompt_sha256"] == prompt_sha256("v5") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005g_thresholds_unchanged():
    assert gate3.load_manifest()["thresholds"] == gate2.load_manifest()["thresholds"]


def test_offline_preconditions_pass():
    checks = gate3.offline_preconditions(gate3.load_manifest())
    assert all(c["passed"] for c in checks), [c for c in checks if not c["passed"]]


def test_acceptance_suite_shape():
    suite, _ = gate3.load_suite(gate3.ROOT / gate3.load_manifest()["acceptance_suite"]["path"])
    cases = suite["cases"]
    assert len(cases) == 75 and all(sum(c["category"] == k for c in cases) == 3 for k in gate3.CATEGORIES)
    assert sum(c["expected"]["end_to_end"] == "release_substantive" for c in cases) >= 35
    assert sum(c["expected"]["expected_language"] != "ko" for c in cases) >= 25


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005h_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_only_through_the_v3_gate():
    nb = BOOT / "notebooks" / "artemis_mission005h_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate3.run(prepared, ACC_DIR)" in text and "gate3.run_dev20(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005h_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
