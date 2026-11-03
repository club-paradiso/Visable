"""Mission 005-Q: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import synthetic_safety_gate_v11 as gate11
import synthetic_safety_gate_v12 as gate12
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "b7aab532c445042320eea82be16341f30f19aeded93c10ac58af207a5b51d3ec"
ACCEPTANCE_SHA256 = "2d7eb0f94b39452fc1e02fe845951ab8875cdbb5b0cdbb8e0631b521c2de7551"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite():
    return gate12.load_suite(gate12.ROOT / gate12.load_manifest()["acceptance_suite"]["path"])[0]["cases"]


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate12.MANIFEST) == MANIFEST_SHA256
    m = gate12.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-Q" and m["contract_version"] == "v12"
    assert m["prompt_sha256"] == prompt_sha256("v12") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005p_thresholds_unchanged():
    assert gate12.load_manifest()["thresholds"] == gate11.load_manifest()["thresholds"]


#: Files Mission 005-R changed after the 005-Q freeze. The 005-Q manifest records them as they were at
#: that freeze; the 005-Q decision is re-derived with that run commit's code (test_mission005q_real_run).
CHANGED_AFTER_005Q = {"artemis_bootstrap/grounding_guard.py", "artemis_bootstrap/trusted_evidence_spec.md",
                      "artemis_bootstrap/gemma4_runtime.py", "waymaker_ai/inference_input.py", "waymaker_ai/response_contract.py",
                      # Mission 005-S
                      "artemis_bootstrap/claim_support_validation.py"}
FREEZE_COMMIT_005Q = "541cee6257c39cddb7b1bc85e6c58ed0be59b9e2"


def test_offline_preconditions_pass():
    checks = gate12.offline_preconditions(gate12.load_manifest())
    assert all(c["passed"] for c in checks if c["check"] != "evaluator_files_unchanged"), checks
    files = next(c for c in checks if c["check"] == "evaluator_files_unchanged")
    assert set(files["detail"] or {}) <= CHANGED_AFTER_005Q, files


def test_005q_manifest_matches_the_files_at_its_freeze_commit():
    for rel, digest in gate12.load_manifest()["evaluator_files_sha256"].items():
        shown = subprocess.run(["git", "show", f"{FREEZE_COMMIT_005Q}:experiments/waymaker-ai/{rel}"],
                               cwd=BOOT, capture_output=True)
        if shown.returncode:
            pytest.skip("needs git history for the 005-Q freeze commit")
        assert hashlib.sha256(shown.stdout).hexdigest() == digest, rel


def test_the_date_reading_and_gate_v12_are_frozen():
    files = gate12.load_manifest()["evaluator_files_sha256"]
    assert {"artemis_bootstrap/synthetic_safety_gate_v12.py", "artemis_bootstrap/claim_support_validation.py",
            "artemis_bootstrap/grounding_guard.py"} <= set(files)


def test_acceptance_suite_shape_and_the_date_focus():
    cases = suite()
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases) == 3 for k in gate12.CATEGORIES)
    assert sum(c["expected"]["end_to_end"] == "release_substantive" for c in cases) >= 38
    assert sum(c["expected"]["expected_language"] != "ko" for c in cases) >= 27
    assert sum(c["expected"]["expected_language"] == "vi" for c in cases) >= 13
    dated = [c["id"] for c in cases if c["expected"]["expected_language"] == "vi" and c["expected"]["end_to_end"] == "release_substantive"
             and any(re.search(r"\d{4}년 \d{1,2}월 \d{1,2}일", e["text"]) for e in c["evidence"] if e["id"] in c["expected"]["admissible_ids"])]
    assert len(dated) >= 4, dated


def test_true_conflicts_list_one_group_per_value_and_one_asks_per_document():
    conflicts = [c for c in suite() if "conflict" in c["expected"]["model_statuses"]]
    assert len(conflicts) == 3
    for c in conflicts:
        assert len(c["expected"]["required_mentions"]) == 2 and "conflict_treated_as_resolved" in c["expected"]["critical_rules"]
    assert any(re.search(r"\beach\b|각각|mỗi", c["question"], re.IGNORECASE) for c in conflicts)


def test_suite_keeps_the_earlier_coverage():
    import grounding_guard as guard
    import language_compliance
    cases = suite()
    double = [c["id"] for c in cases if len({lang for lang, p in language_compliance._REQUESTS.items()
                                             if p.search(language_compliance._nfc(c["question"]).lower())}) > 1]
    assert len(double) >= 3, double
    named = [c["id"] for c in cases if any(isinstance(e.get("source"), dict) and e["source"].get("document_id")
                                            and e["source"]["document_id"] in c["question"] for e in c["evidence"])]
    assert len(named) >= 3, named
    opening = [c["id"] for c in cases
               if any(c["question"].startswith(r + ",") for r in guard.remove_language_requests(c["question"])["removed"])]
    assert len(opening) >= 2, opening


def test_expected_result_review_is_recorded_with_its_limits():
    review = json.loads((BOOT / "validation" / "mission005q_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_only_through_the_v12_gate():
    nb = BOOT / "notebooks" / "artemis_mission005q_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate12.run(prepared, ACC_DIR)" in text and "gate12.run_dev20(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005q_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
