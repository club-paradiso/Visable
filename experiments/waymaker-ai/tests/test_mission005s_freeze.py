"""Mission 005-S: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import claim_support_validation as claims
import synthetic_safety_gate_v13 as gate13
import synthetic_safety_gate_v14 as gate14
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "17aac0f4664897a97f73499390249c5494d92ae1bb9683bf674f3f26a6b2d246"
ACCEPTANCE_SHA256 = "ccd785f3a18ac1756c4a63a93f98c6bdc1011d7084c8613e95653a29a18b4d72"
CAP = ["A05S-01", "A05S-02", "A05S-03", "A05S-37", "A05S-44", "A05S-59", "A05S-61", "A05S-62", "A05S-63"]
CAP_NEGATIVE = ["A05S-38", "A05S-39", "A05S-45"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite():
    return {c["id"]: c for c in gate14.load_suite(gate14.ROOT / gate14.load_manifest()["acceptance_suite"]["path"])[0]["cases"]}


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate14.MANIFEST) == MANIFEST_SHA256
    m = gate14.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-S" and m["contract_version"] == "v13"
    assert m["prompt_sha256"] == prompt_sha256("v13") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005r_thresholds_unchanged():
    assert gate14.load_manifest()["thresholds"] == gate13.load_manifest()["thresholds"]


def test_offline_preconditions_pass():
    checks = gate14.offline_preconditions(gate14.load_manifest())
    assert all(c["passed"] for c in checks), [c for c in checks if not c["passed"]]


def test_the_cap_reading_and_gate_v14_are_frozen():
    files = gate14.load_manifest()["evaluator_files_sha256"]
    assert {"artemis_bootstrap/claim_support_validation.py", "artemis_bootstrap/grounding_guard.py",
            "artemis_bootstrap/synthetic_safety_gate_v14.py", "artemis_bootstrap/branch_coverage.py", "artemis_bootstrap/dev20_v2.py"} <= set(files)


def test_acceptance_suite_shape_and_the_cap_focus():
    cases = suite()
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases.values()) == 3 for k in gate14.CATEGORIES)
    assert sum(c["expected"]["end_to_end"] == "release_substantive" for c in cases.values()) >= 38
    assert {cases[i]["expected"]["expected_polarity"] for i in CAP} == {"permitted"}
    assert {cases[i]["expected"]["expected_polarity"] for i in CAP_NEGATIVE} == {"prohibited"}
    assert {cases[i]["expected"]["expected_language"] for i in CAP} == {"ko", "en", "vi"}
    assert sorted(i for i, c in cases.items() if "role_reversal" in c["expected"]["critical_rules"]) == ["A05S-14", "A05S-25", "A05S-72", "A05S-78"]


@pytest.mark.parametrize("cid", CAP + CAP_NEGATIVE)
def test_cap_evidence_keeps_its_permission_or_prohibition(cid):
    case = suite()[cid]
    text = " ".join(e["text"] for e in case["evidence"] if e["id"] in case["expected"]["admissible_ids"])
    want = case["expected"]["expected_polarity"]
    assert "prohibited" not in claims.polarity(text, caps_apart=True) if want == "permitted" else claims.polarity(text, caps_apart=True) == {"prohibited"}


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005s_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_v2_only_through_the_v14_gate():
    nb = BOOT / "notebooks" / "artemis_mission005s_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate14.run(prepared, ACC_DIR)" in text and "dev20_v2.run(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005s_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
