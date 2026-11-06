"""Mission 005-U: the acceptance suite, evaluator files and thresholds frozen before inference."""
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
import synthetic_safety_gate_v15 as gate15
import synthetic_safety_gate_v16 as gate16
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "dd433c1bb420f10b4e6f4e1e8de6ccc0befe82440dac993b91906b7e083a4c14"
ACCEPTANCE_SHA256 = "accd6b025dd1bd331f6088976ba5404b236d95f44ba965e050fa818b4d6794a8"
CONFLICT = ["A05U-28", "A05U-29", "A05U-30", "A05U-44", "A05U-56", "A05U-59", "A05U-67"]
NOT_CONFLICT = ["A05U-31", "A05U-32", "A05U-33"]
PARTIAL_TRAP = ["A05U-36", "A05U-42", "A05U-61"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite():
    return {c["id"]: c for c in gate16.load_suite(gate16.ROOT / gate16.load_manifest()["acceptance_suite"]["path"])[0]["cases"]}


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate16.MANIFEST) == MANIFEST_SHA256
    m = gate16.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-U" and m["contract_version"] == "v15"
    assert m["prompt_sha256"] == prompt_sha256("v15") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005t_thresholds_unchanged():
    assert gate16.load_manifest()["thresholds"] == gate15.load_manifest()["thresholds"]


#: Files Mission 005-V changed after the 005-U freeze. The 005-U manifest records them as they were at
#: that freeze; the 005-U decision is re-derived with that run commit's code (test_mission005u_real_run).
CHANGED_AFTER_005U = {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/trusted_evidence_spec.md",
                      "artemis_bootstrap/dev20_v2.py", "artemis_bootstrap/gemma4_runtime.py", "artemis_bootstrap/status_check.py",
                      "waymaker_ai/inference_input.py", "waymaker_ai/response_contract.py",
                      # Mission 005-W
                      "waymaker_ai/evidence_admissibility.py"}
FREEZE_COMMIT_005U = "829de8d41c3e7097ac3db317a5fab9ea43b4b59e"


def test_offline_preconditions_pass():
    checks = gate16.offline_preconditions(gate16.load_manifest())
    assert all(c["passed"] for c in checks if c["check"] != "evaluator_files_unchanged"), checks
    files = next(c for c in checks if c["check"] == "evaluator_files_unchanged")
    assert set(files["detail"] or {}) <= CHANGED_AFTER_005U, files


def test_005u_manifest_matches_the_files_at_its_freeze_commit():
    for rel, digest in gate16.load_manifest()["evaluator_files_sha256"].items():
        shown = subprocess.run(["git", "show", f"{FREEZE_COMMIT_005U}:experiments/waymaker-ai/{rel}"],
                               cwd=BOOT, capture_output=True)
        if shown.returncode:
            pytest.skip("needs git history for the 005-U freeze commit")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, rel


def test_the_conflict_mark_and_gate_v16_are_frozen():
    files = gate16.load_manifest()["evaluator_files_sha256"]
    assert {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/status_check.py", "artemis_bootstrap/gemma4_runtime.py",
            "artemis_bootstrap/synthetic_safety_gate_v16.py", "waymaker_ai/inference_input.py", "waymaker_ai/response_contract.py",
            "artemis_bootstrap/dev20_v2.py"} <= set(files)


def test_acceptance_suite_shape_and_the_conflict_focus():
    cases = suite()
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases.values()) == 3 for k in gate16.CATEGORIES)
    assert sorted(i for i, c in cases.items() if "conflict" in c["expected"]["model_statuses"]) == CONFLICT
    assert all(cases[i]["expected"]["model_statuses"] == ["answered"] for i in NOT_CONFLICT + PARTIAL_TRAP)
    assert all(cases[i]["expected"]["uncovered_items"] == [] for i in PARTIAL_TRAP)


def test_the_first_call_marks_exactly_the_conflict_cases():
    marked = []
    for cid, case in suite().items():
        prepared = guard.prepare(case["question"], case["intake"], case["evidence"], gate16.registry_for(case, "acceptance"),
                                 case.get("as_of") or "2026-11-02")
        if any("conflict_records" in item["system"] for item in prepared["model_items"]):
            marked.append(cid)
    assert sorted(marked) == CONFLICT


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005u_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]
    agreement = review["derived_field_agreement"]
    assert all(v == "81/81" for k, v in agreement.items() if k != "injection_markers")
    # 52..54 take their markers from the evidence, as A05T-52..54 did; recorded and kept.
    assert agreement["injection_markers"].startswith("78/81 (52, 53, 54")


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_v2_only_through_the_v16_gate():
    nb = BOOT / "notebooks" / "artemis_mission005u_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate16.run(prepared, ACC_DIR)" in text and "dev20_v2.run(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005u_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
