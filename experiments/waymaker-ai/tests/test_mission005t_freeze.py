"""Mission 005-T: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import status_check
import synthetic_safety_gate_v14 as gate14
import synthetic_safety_gate_v15 as gate15
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "b70672e157abadb7de3a217029c50d725f7544fb7bd80544f7667505aae9608c"
ACCEPTANCE_SHA256 = "a9548b90c6ad341fcf51d95e39b9f55c2e70291da2d3a3c25a969d0aa20938df"
CONFLICT = ["A05T-28", "A05T-29", "A05T-30", "A05T-44", "A05T-56", "A05T-59", "A05T-67"]
NOT_CONFLICT = ["A05T-31", "A05T-32", "A05T-33"]
PARTIAL_TRAP = ["A05T-36", "A05T-42", "A05T-61"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite():
    return {c["id"]: c for c in gate15.load_suite(gate15.ROOT / gate15.load_manifest()["acceptance_suite"]["path"])[0]["cases"]}


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate15.MANIFEST) == MANIFEST_SHA256
    m = gate15.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-T" and m["contract_version"] == "v14"
    assert m["prompt_sha256"] == prompt_sha256("v14") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005s_thresholds_unchanged():
    assert gate15.load_manifest()["thresholds"] == gate14.load_manifest()["thresholds"]


#: Files Mission 005-U changed after the 005-T freeze. The 005-T manifest records them as they were at
#: that freeze; the 005-T decision is re-derived with that run commit's code (test_mission005t_real_run).
CHANGED_AFTER_005T = {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/trusted_evidence_spec.md",
                      "artemis_bootstrap/dev20_v2.py", "artemis_bootstrap/gemma4_runtime.py",
                      "waymaker_ai/inference_input.py", "waymaker_ai/response_contract.py",
                      # Mission 005-V
                      "artemis_bootstrap/status_check.py",
                      # Mission 005-W
                      "waymaker_ai/evidence_admissibility.py"}
FREEZE_COMMIT_005T = "83f5f274828fd98c4bed8710c04cf7989ed60752"


def test_offline_preconditions_pass():
    checks = gate15.offline_preconditions(gate15.load_manifest())
    assert all(c["passed"] for c in checks if c["check"] != "evaluator_files_unchanged"), checks
    files = next(c for c in checks if c["check"] == "evaluator_files_unchanged")
    assert set(files["detail"] or {}) <= CHANGED_AFTER_005T, files


def test_005t_manifest_matches_the_files_at_its_freeze_commit():
    for rel, digest in gate15.load_manifest()["evaluator_files_sha256"].items():
        shown = subprocess.run(["git", "show", f"{FREEZE_COMMIT_005T}:experiments/waymaker-ai/{rel}"],
                               cwd=BOOT, capture_output=True)
        if shown.returncode:
            pytest.skip("needs git history for the 005-T freeze commit")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, rel


def test_the_status_retry_and_gate_v15_are_frozen():
    files = gate15.load_manifest()["evaluator_files_sha256"]
    assert {"artemis_bootstrap/status_check.py", "artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/synthetic_safety_gate_v15.py",
            "waymaker_ai/evidence_admissibility.py", "waymaker_ai/response_contract.py", "artemis_bootstrap/dev20_v2.py"} <= set(files)


def test_acceptance_suite_shape_and_the_status_focus():
    cases = suite()
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases.values()) == 3 for k in gate15.CATEGORIES)
    assert sorted(i for i, c in cases.items() if "conflict" in c["expected"]["model_statuses"]) == CONFLICT
    assert all(cases[i]["expected"]["model_statuses"] == ["answered"] for i in NOT_CONFLICT + PARTIAL_TRAP)
    assert all(cases[i]["expected"]["uncovered_items"] == [] for i in PARTIAL_TRAP)


@pytest.mark.parametrize("cid", CONFLICT + NOT_CONFLICT)
def test_the_conflict_rule_matches_the_suite(cid):
    case = suite()[cid]
    texts = [e["text"] for e in case["evidence"] if e["id"] in case["expected"]["admissible_ids"]]
    assert bool(status_check.conflicting_values(texts)) is (cid in CONFLICT)


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005t_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_v2_only_through_the_v15_gate():
    nb = BOOT / "notebooks" / "artemis_mission005t_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate15.run(prepared, ACC_DIR)" in text and "dev20_v2.run(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005t_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
