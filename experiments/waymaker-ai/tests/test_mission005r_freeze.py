"""Mission 005-R: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import branch_coverage as branches
import grounding_guard as guard
import synthetic_safety_gate_v12 as gate12
import synthetic_safety_gate_v13 as gate13
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "7e09d3a17e188f79bd9894199681cb89be173b0ffb17da1e9c2cd29db9ba6ed9"
ACCEPTANCE_SHA256 = "c8189f3d71a19bab3f8b90ea1dde129dd14f84d899350507a7c920177cd6404d"
TWO_CASE = ["A05R-01", "A05R-02", "A05R-03", "A05R-40", "A05R-43", "A05R-61", "A05R-62", "A05R-63", "A05R-67"]
OTHER_CODE = ["A05R-59", "A05R-70", "A05R-71"]
CROSS_LANGUAGE = ["A05R-44", "A05R-45"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite():
    return gate13.load_suite(gate13.ROOT / gate13.load_manifest()["acceptance_suite"]["path"])[0]["cases"]


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate13.MANIFEST) == MANIFEST_SHA256
    m = gate13.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-R" and m["contract_version"] == "v13"
    assert m["prompt_sha256"] == prompt_sha256("v13") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005q_thresholds_unchanged():
    assert gate13.load_manifest()["thresholds"] == gate12.load_manifest()["thresholds"]


def test_offline_preconditions_pass():
    checks = gate13.offline_preconditions(gate13.load_manifest())
    assert all(c["passed"] for c in checks), [c for c in checks if not c["passed"]]


def test_the_branch_rule_gate_v13_and_the_dev20_v2_runner_are_frozen():
    files = gate13.load_manifest()["evaluator_files_sha256"]
    assert {"artemis_bootstrap/branch_coverage.py", "artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/synthetic_safety_gate_v13.py",
            "artemis_bootstrap/dev20_v2.py", "waymaker_ai/response_contract.py", "waymaker_ai/inference_input.py"} <= set(files)


def test_acceptance_suite_shape_and_the_two_case_focus():
    cases = {c["id"]: c for c in suite()}
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases.values()) == 3 for k in gate13.CATEGORIES)
    assert sum(c["expected"]["end_to_end"] == "release_substantive" for c in cases.values()) >= 38
    assert sum(c["expected"]["expected_language"] == "vi" for c in cases.values()) >= 13
    assert sorted(i for i, c in cases.items() if "two-case positive" in c["rationale"]) == TWO_CASE
    assert {cases[i]["expected"]["expected_language"] for i in TWO_CASE} == {"ko", "en", "vi"}


@pytest.mark.parametrize("cid", TWO_CASE + OTHER_CODE)
def test_an_answer_repeating_one_case_is_asked_again_only_where_the_rule_applies(cid):
    case = {c["id"]: c for c in suite()}[cid]
    e = case["expected"]
    texts = [x["text"] for x in case["evidence"] if x["id"] in e["admissible_ids"]]
    first, second = next(branches.split_cases(t) for t in texts if branches.split_cases(t))
    prepared = guard.prepare(case["question"], case["intake"], case["evidence"], gate13.registry_for(case, "acceptance"), "2026-11-02")
    code = (prepared["selection"]["context"] or {}).get("status_code")
    assert bool(branches.omitted_cases(first, texts, code)) is (cid in TWO_CASE)
    assert branches.omitted_cases(first + " " + second, texts, code) == []


def test_role_reversal_is_covered_in_three_languages():
    cases = [c for c in suite() if "role_reversal" in c["expected"]["critical_rules"]]
    assert sorted(c["id"] for c in cases) == ["A05R-14", "A05R-25", "A05R-78"]
    assert {c["expected"]["expected_language"] for c in cases} == {"ko", "en", "vi"}


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005r_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"] and review.get("follow_up_review")


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_v2_only_through_the_v13_gate():
    nb = BOOT / "notebooks" / "artemis_mission005r_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate13.run(prepared, ACC_DIR)" in text and "dev20_v2.run(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005r_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
