"""Mission 005-Y: the acceptance suite, evaluator files and thresholds frozen before inference."""
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
import synthetic_safety_gate_v19 as gate19
import synthetic_safety_gate_v20 as gate20
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "ae43f104683f9da40feb6707f9bb8ca507e4b4d87a3eace99211b437fd91db99"
ACCEPTANCE_SHA256 = "9ad64c39b047f2293d8194bc51f8b9437d47ce8bb2f09d4ca071114e04450ec7"
CONFLICT = ["A05Y-28", "A05Y-29", "A05Y-30", "A05Y-44", "A05Y-56", "A05Y-59", "A05Y-67"]
NOT_CONFLICT = ["A05Y-31", "A05Y-32", "A05Y-33"]
PARTIAL_TRAP = ["A05Y-36", "A05Y-42", "A05Y-61"]
CHOICE = {"A05Y-02": ["N-4-1", "N-4-4"], "A05Y-22": ["N-4-2", "N-4-3"], "A05Y-33": ["N-4-2", "N-4-4"],
          "A05Y-45": ["N-4-1", "N-4-3"], "A05Y-62": ["N-4-3", "N-4-4"], "A05Y-70": ["N-4-1", "N-4-2"]}
NEAR_MISS = ["A05Y-18", "A05Y-58", "A05Y-60", "A05Y-81"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite():
    return {c["id"]: c for c in gate20.load_suite(gate20.ROOT / gate20.load_manifest()["acceptance_suite"]["path"])[0]["cases"]}


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate20.MANIFEST) == MANIFEST_SHA256
    m = gate20.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-Y" and m["contract_version"] == "v18"
    assert m["prompt_sha256"] == prompt_sha256("v18") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005x_thresholds_unchanged():
    assert gate20.load_manifest()["thresholds"] == gate19.load_manifest()["thresholds"]


def test_offline_preconditions_pass():
    checks = gate20.offline_preconditions(gate20.load_manifest())
    assert all(c["passed"] for c in checks), [c for c in checks if not c["passed"]]


def test_the_choice_parts_own_code_check_and_gate_v20_are_frozen():
    files = gate20.load_manifest()["evaluator_files_sha256"]
    assert {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/choice_coverage.py", "artemis_bootstrap/gemma4_runtime.py",
            "artemis_bootstrap/synthetic_safety_gate_v20.py", "artemis_bootstrap/status_check.py",
            "waymaker_ai/inference_input.py", "waymaker_ai/response_contract.py", "artemis_bootstrap/dev20_v2.py",
            "artemis_bootstrap/trusted_evidence_spec.md"} <= set(files)


def test_acceptance_suite_shape_and_the_focus_cases():
    cases = suite()
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases.values()) == 3 for k in gate20.CATEGORIES)
    assert sorted(i for i, c in cases.items() if "conflict" in c["expected"]["model_statuses"]) == CONFLICT
    assert all(cases[i]["expected"]["model_statuses"] == ["answered"] for i in NOT_CONFLICT[:2] + PARTIAL_TRAP)
    assert all(cases[i]["expected"]["model_statuses"] == ["answered", "answered"] for i in CHOICE)
    assert len({cases[i]["category"] for i in CHOICE}) == len(CHOICE)            # one choice case per category
    assert sorted(cases[i]["expected"]["expected_language"] for i in CHOICE) == ["en", "en", "ko", "ko", "vi", "vi"]


def test_the_pipeline_asks_exactly_the_choice_cases_per_code_in_question_order():
    parts, conflict = {}, []
    for cid, case in suite().items():
        prepared = guard.prepare(case["question"], case["intake"], case["evidence"], gate20.registry_for(case, "acceptance"),
                                 case.get("as_of") or "2026-11-02")
        codes = [p["choice_part"] for p in prepared["parts"] if p.get("choice_part")]
        if codes:
            parts[cid] = codes
        if any("conflict_records" in item["system"] for item in prepared["model_items"]):
            conflict.append(cid)
        if cid in NEAR_MISS:
            assert not any("choice_codes" in item["system"] for item in prepared["model_items"]), cid
    assert parts == CHOICE and sorted(conflict) == CONFLICT


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005y_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]
    agreement = review["derived_field_agreement"]
    assert all(v.startswith("81/81") for k, v in agreement.items() if k != "injection_markers")


def test_notebook_is_pinned_to_the_freeze_installs_the_pinned_torch_and_runs_dev20_v2_only_through_the_v20_gate():
    nb = BOOT / "notebooks" / "artemis_mission005y_colab.ipynb"
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    if commit == "0" * 40:
        pytest.skip("the notebook is pinned in the commit after the freeze")
    assert "gate20.run(prepared, ACC_DIR)" in text and "dev20_v2.run(" in text and "if record['decision'] == 'pass'" in text
    assert '"torch==2.11.0+cu130"' in text.replace('\\"', '"')
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005y_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
