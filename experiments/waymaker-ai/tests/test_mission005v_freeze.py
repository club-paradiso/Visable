"""Mission 005-V: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import choice_coverage
import synthetic_safety_gate_v16 as gate16
import synthetic_safety_gate_v17 as gate17
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "ea18b4e8f79bbccd89bd4ccbafd51b103bd414b3a0ca1388de4e8d5c8b67fb23"
ACCEPTANCE_SHA256 = "efae3c9ceb3ab05f59a05d05f995154c176d0fd45414ff4f79e65ca72eed4d4e"
CONFLICT = ["A05V-28", "A05V-29", "A05V-30", "A05V-44", "A05V-56", "A05V-59", "A05V-67"]
NOT_CONFLICT = ["A05V-31", "A05V-32", "A05V-33"]
PARTIAL_TRAP = ["A05V-36", "A05V-42", "A05V-61"]
CHOICE = ["A05V-45", "A05V-62", "A05V-63", "A05V-68", "A05V-70", "A05V-71"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite():
    return {c["id"]: c for c in gate17.load_suite(gate17.ROOT / gate17.load_manifest()["acceptance_suite"]["path"])[0]["cases"]}


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate17.MANIFEST) == MANIFEST_SHA256
    m = gate17.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-V" and m["contract_version"] == "v16"
    assert m["prompt_sha256"] == prompt_sha256("v16") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005u_thresholds_unchanged():
    assert gate17.load_manifest()["thresholds"] == gate16.load_manifest()["thresholds"]


#: Files Mission 005-W changed after the 005-V freeze. The 005-V manifest records them as they were at
#: that freeze; the 005-V decision is re-derived with that run commit's code (test_mission005v_real_run).
CHANGED_AFTER_005V = {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/trusted_evidence_spec.md",
                      "artemis_bootstrap/dev20_v2.py", "artemis_bootstrap/gemma4_runtime.py", "artemis_bootstrap/status_check.py",
                      "waymaker_ai/inference_input.py", "waymaker_ai/response_contract.py",
                      "waymaker_ai/evidence_admissibility.py",
                      # Mission 005-X
                      "artemis_bootstrap/choice_coverage.py"}
FREEZE_COMMIT_005V = "8421c4d27979ac3b0229bc262dbad4dac8d1e59a"


def test_offline_preconditions_pass():
    checks = gate17.offline_preconditions(gate17.load_manifest())
    assert all(c["passed"] for c in checks if c["check"] != "evaluator_files_unchanged"), checks
    files = next(c for c in checks if c["check"] == "evaluator_files_unchanged")
    assert set(files["detail"] or {}) <= CHANGED_AFTER_005V, files


def test_005v_manifest_matches_the_files_at_its_freeze_commit():
    for rel, digest in gate17.load_manifest()["evaluator_files_sha256"].items():
        shown = subprocess.run(["git", "show", f"{FREEZE_COMMIT_005V}:experiments/waymaker-ai/{rel}"],
                               cwd=BOOT, capture_output=True)
        if shown.returncode:
            pytest.skip("needs git history for the 005-V freeze commit")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, rel


def test_the_choice_retry_and_gate_v17_are_frozen():
    files = gate17.load_manifest()["evaluator_files_sha256"]
    assert {"artemis_bootstrap/choice_coverage.py", "artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/status_check.py",
            "artemis_bootstrap/gemma4_runtime.py", "artemis_bootstrap/synthetic_safety_gate_v17.py",
            "waymaker_ai/inference_input.py", "waymaker_ai/response_contract.py", "artemis_bootstrap/dev20_v2.py"} <= set(files)


def test_acceptance_suite_shape_and_the_focus_cases():
    cases = suite()
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases.values()) == 3 for k in gate17.CATEGORIES)
    assert sorted(i for i, c in cases.items() if "conflict" in c["expected"]["model_statuses"]) == CONFLICT
    assert all(cases[i]["expected"]["model_statuses"] == ["answered"] for i in NOT_CONFLICT + PARTIAL_TRAP + CHOICE)
    assert all(cases[i]["expected"]["uncovered_items"] == [] for i in PARTIAL_TRAP)


def test_the_choice_rule_retries_exactly_the_six_choice_cases():
    """An answer naming only one code the evidence names leaves the other out only in the six choice cases."""
    fired = []
    for cid, case in suite().items():
        texts = [e["text"] for e in case["evidence"] if e["id"] in case["expected"]["admissible_ids"]]
        named = [c for c in choice_coverage.choice_codes(case["question"]) if any(c in t for t in texts)]
        if any(choice_coverage.omitted_choices(case["question"], f"{c} 입니다.", texts) for c in named):
            fired.append(cid)
    assert sorted(fired) == CHOICE


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005v_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]
    agreement = review["derived_field_agreement"]
    assert all(v.startswith("81/81") for k, v in agreement.items() if k != "injection_markers")
    assert any("Not applied" in note for note in review["implementer_changes_after_review"])


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_v2_only_through_the_v17_gate():
    nb = BOOT / "notebooks" / "artemis_mission005v_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate17.run(prepared, ACC_DIR)" in text and "dev20_v2.run(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005v_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
