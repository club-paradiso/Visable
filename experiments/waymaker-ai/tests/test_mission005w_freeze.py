"""Mission 005-W: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import grounding_guard as guard
import synthetic_safety_gate_v17 as gate17
import synthetic_safety_gate_v18 as gate18
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "0cf8b5a15e4df43c29e5edf788e58851b42bdf2de160ab773691990d8c2d8b88"
ACCEPTANCE_SHA256 = "c62e393964c7690a1181620cee53c94ed8b206db11d422307f933d316406242e"
CONFLICT = ["A05W-28", "A05W-29", "A05W-30", "A05W-44", "A05W-56", "A05W-59", "A05W-67"]
NOT_CONFLICT = ["A05W-31", "A05W-32", "A05W-33"]
PARTIAL_TRAP = ["A05W-36", "A05W-42", "A05W-61"]
CHOICE = ["A05W-02", "A05W-45", "A05W-62", "A05W-68", "A05W-70", "A05W-81"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite():
    return {c["id"]: c for c in gate18.load_suite(gate18.ROOT / gate18.load_manifest()["acceptance_suite"]["path"])[0]["cases"]}


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate18.MANIFEST) == MANIFEST_SHA256
    m = gate18.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-W" and m["contract_version"] == "v17"
    assert m["prompt_sha256"] == prompt_sha256("v17") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005v_thresholds_unchanged():
    assert gate18.load_manifest()["thresholds"] == gate17.load_manifest()["thresholds"]


#: Files Mission 005-X changed after the 005-W freeze. The 005-W manifest records them as they were at
#: that freeze; the 005-W decision is re-derived with that run commit's code (test_mission005w_real_run).
CHANGED_AFTER_005W = {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/choice_coverage.py",
                      "artemis_bootstrap/trusted_evidence_spec.md", "artemis_bootstrap/dev20_v2.py",
                      "artemis_bootstrap/gemma4_runtime.py", "artemis_bootstrap/status_check.py",
                      "waymaker_ai/inference_input.py", "waymaker_ai/response_contract.py"}
FREEZE_COMMIT_005W = "e4464b0c0eedc66cb4bfd2096c97925b107b2e03"


def test_offline_preconditions_pass():
    checks = gate18.offline_preconditions(gate18.load_manifest())
    assert all(c["passed"] for c in checks if c["check"] != "evaluator_files_unchanged"), checks
    files = next(c for c in checks if c["check"] == "evaluator_files_unchanged")
    assert set(files["detail"] or {}) <= CHANGED_AFTER_005W, files


def test_005w_manifest_matches_the_files_at_its_freeze_commit():
    for rel, digest in gate18.load_manifest()["evaluator_files_sha256"].items():
        shown = subprocess.run(["git", "show", f"{FREEZE_COMMIT_005W}:experiments/waymaker-ai/{rel}"],
                               cwd=BOOT, capture_output=True)
        if shown.returncode:
            pytest.skip("needs git history for the 005-W freeze commit")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, rel


def test_the_choice_codes_mark_and_gate_v18_are_frozen():
    files = gate18.load_manifest()["evaluator_files_sha256"]
    assert {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/choice_coverage.py", "artemis_bootstrap/gemma4_runtime.py",
            "artemis_bootstrap/synthetic_safety_gate_v18.py", "waymaker_ai/evidence_admissibility.py",
            "waymaker_ai/inference_input.py", "waymaker_ai/response_contract.py", "artemis_bootstrap/dev20_v2.py"} <= set(files)


def test_acceptance_suite_shape_and_the_focus_cases():
    cases = suite()
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases.values()) == 3 for k in gate18.CATEGORIES)
    assert sorted(i for i, c in cases.items() if "conflict" in c["expected"]["model_statuses"]) == CONFLICT
    assert all(cases[i]["expected"]["model_statuses"] == ["answered"] for i in NOT_CONFLICT + PARTIAL_TRAP + CHOICE)
    assert all(cases[i]["expected"]["uncovered_items"] == [] for i in PARTIAL_TRAP)
    assert len({cases[i]["category"] for i in CHOICE}) == len(CHOICE)    # at most one choice case per category


def test_the_first_call_marks_exactly_the_choice_and_conflict_cases():
    choice, conflict = [], []
    for cid, case in suite().items():
        prepared = guard.prepare(case["question"], case["intake"], case["evidence"], gate18.registry_for(case, "acceptance"),
                                 case.get("as_of") or "2026-11-02")
        if any("choice_codes" in item["system"] for item in prepared["model_items"]):
            choice.append(cid)
        if any("conflict_records" in item["system"] for item in prepared["model_items"]):
            conflict.append(cid)
    assert sorted(choice) == CHOICE and sorted(conflict) == CONFLICT


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005w_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]
    agreement = review["derived_field_agreement"]
    assert all(v.startswith("81/81") for k, v in agreement.items() if k != "injection_markers")


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_v2_only_through_the_v18_gate():
    nb = BOOT / "notebooks" / "artemis_mission005w_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate18.run(prepared, ACC_DIR)" in text and "dev20_v2.run(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005w_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
