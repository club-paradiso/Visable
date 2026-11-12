"""Mission 005-Z: the acceptance suite, evaluator files and thresholds frozen before inference."""
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
import synthetic_safety_gate_v20 as gate20
import synthetic_safety_gate_v21 as gate21
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "657765c32b03cbfef690ea4bb4c42e9b5622fc69b746efe40c93670c2d4faef9"
ACCEPTANCE_SHA256 = "8c0f6dc66bb389f4b55a3f4f0a21f03f772fcee2bc4492a4885299211d0ed2cb"
CONFLICT = ["A05Z-28", "A05Z-29", "A05Z-30", "A05Z-44", "A05Z-56", "A05Z-59", "A05Z-67"]
NOT_CONFLICT = ["A05Z-31", "A05Z-32", "A05Z-33"]
PARTIAL_TRAP = ["A05Z-36", "A05Z-42", "A05Z-61"]
CHOICE = {"A05Z-02": ["P-2-2", "P-2-3"], "A05Z-22": ["P-2-1", "P-2-4"], "A05Z-33": ["P-2-2", "P-2-4"],
          "A05Z-45": ["P-2-1", "P-2-3"], "A05Z-62": ["P-2-1", "P-2-2"], "A05Z-70": ["P-2-2", "P-2-3"]}
NEAR_MISS = ["A05Z-18", "A05Z-58", "A05Z-60", "A05Z-81"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite():
    return {c["id"]: c for c in gate21.load_suite(gate21.ROOT / gate21.load_manifest()["acceptance_suite"]["path"])[0]["cases"]}


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate21.MANIFEST) == MANIFEST_SHA256
    m = gate21.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-Z" and m["contract_version"] == "v18"
    assert m["prompt_sha256"] == prompt_sha256("v18") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005y_thresholds_unchanged():
    assert gate21.load_manifest()["thresholds"] == gate20.load_manifest()["thresholds"]


def test_offline_preconditions_pass():
    checks = gate21.offline_preconditions(gate21.load_manifest())
    assert all(c["passed"] for c in checks), [c for c in checks if not c["passed"]]


def test_the_conclusion_check_and_gate_v21_are_frozen():
    files = gate21.load_manifest()["evaluator_files_sha256"]
    assert {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/choice_coverage.py", "artemis_bootstrap/choice_conclusion.py", "artemis_bootstrap/gemma4_runtime.py",
            "artemis_bootstrap/synthetic_safety_gate_v21.py", "artemis_bootstrap/status_check.py",
            "waymaker_ai/inference_input.py", "waymaker_ai/response_contract.py", "artemis_bootstrap/dev20_v2.py",
            "artemis_bootstrap/trusted_evidence_spec.md"} <= set(files)


def test_acceptance_suite_shape_and_the_focus_cases():
    cases = suite()
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases.values()) == 3 for k in gate21.CATEGORIES)
    assert sorted(i for i, c in cases.items() if "conflict" in c["expected"]["model_statuses"]) == CONFLICT
    assert all(cases[i]["expected"]["model_statuses"] == ["answered"] for i in NOT_CONFLICT[:2] + PARTIAL_TRAP)
    assert all(cases[i]["expected"]["model_statuses"] == ["answered", "answered"] for i in CHOICE)
    assert len({cases[i]["category"] for i in CHOICE}) == len(CHOICE)            # one choice case per category
    assert sorted(cases[i]["expected"]["expected_language"] for i in CHOICE) == ["en", "en", "ko", "ko", "vi", "vi"]


def test_the_pipeline_asks_exactly_the_choice_cases_per_code_in_question_order():
    parts, conflict = {}, []
    for cid, case in suite().items():
        prepared = guard.prepare(case["question"], case["intake"], case["evidence"], gate21.registry_for(case, "acceptance"),
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
    review = json.loads((BOOT / "validation" / "mission005z_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]
    agreement = review["derived_field_agreement"]
    assert all(v.startswith("81/81") for k, v in agreement.items() if k != "injection_markers")


def test_notebook_is_pinned_to_the_freeze_installs_the_pinned_torch_and_runs_dev20_v2_only_through_the_v21_gate():
    nb = BOOT / "notebooks" / "artemis_mission005z_colab.ipynb"
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    if commit == "0" * 40:
        pytest.skip("the notebook is pinned in the commit after the freeze")
    assert "gate21.run(prepared, ACC_DIR)" in text and "dev20_v2.run(" in text and "if record['decision'] == 'pass'" in text
    assert '"torch==2.11.0+cu130"' in text.replace('\\"', '"')
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005z_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
