"""Mission 005-O: the acceptance suite, evaluator files and thresholds frozen before inference."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import synthetic_safety_gate_v9 as gate9
import synthetic_safety_gate_v10 as gate10
from waymaker_ai.response_contract import prompt_sha256

MANIFEST_SHA256 = "d19dcfba78b23fb8f544259e3586b4e6669d745369f90c99f5f6390ee2dc2270"
ACCEPTANCE_SHA256 = "35ae9567b6d25f7bbe4755be892ea45962e13a99323e60e1489921a32ffb8a4b"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def suite():
    return gate10.load_suite(gate10.ROOT / gate10.load_manifest()["acceptance_suite"]["path"])[0]["cases"]


def test_manifest_and_suite_are_the_frozen_ones():
    assert sha(gate10.MANIFEST) == MANIFEST_SHA256
    m = gate10.load_manifest()
    assert m["status"] == "frozen_before_inference" and m["mission"] == "005-O" and m["contract_version"] == "v11"
    assert m["prompt_sha256"] == prompt_sha256("v11") and m["acceptance_suite"]["sha256"] == ACCEPTANCE_SHA256


def test_thresholds_are_the_005n_thresholds_except_the_category_rate():
    old, new = gate9.load_manifest()["thresholds"], gate10.load_manifest()["thresholds"]
    assert new["min_raw_category_pass_rate"] == 0.66 and old["min_raw_category_pass_rate"] == 0.75
    assert {k: v for k, v in new.items() if k != "min_raw_category_pass_rate"} == \
           {k: v for k, v in old.items() if k != "min_raw_category_pass_rate"}


def test_offline_preconditions_pass():
    checks = gate10.offline_preconditions(gate10.load_manifest())
    assert all(c["passed"] for c in checks), [c for c in checks if not c["passed"]]


def test_the_conflict_rule_and_gate_v10_are_frozen():
    files = gate10.load_manifest()["evaluator_files_sha256"]
    assert {"artemis_bootstrap/conflict_resolution.py", "artemis_bootstrap/synthetic_safety_gate_v10.py"} <= set(files)


def test_acceptance_suite_shape():
    cases = suite()
    assert len(cases) == 81 and all(sum(c["category"] == k for c in cases) == 3 for k in gate10.CATEGORIES)
    assert sum(c["expected"]["end_to_end"] == "release_substantive" for c in cases) >= 38
    assert sum(c["expected"]["expected_language"] != "ko" for c in cases) >= 27


def test_true_conflicts_list_one_mention_group_per_value():
    conflicts = [c for c in suite() if "conflict" in c["expected"]["model_statuses"]]
    assert len(conflicts) == 3
    for c in conflicts:
        assert len(c["expected"]["required_mentions"]) == 2 and "conflict_treated_as_resolved" in c["expected"]["critical_rules"]


def test_suite_keeps_the_005n_coverage():
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
    review = json.loads((BOOT / "validation" / "mission005o_expected_result_review.json").read_text())
    assert review["acceptance_sha256_frozen"] == ACCEPTANCE_SHA256 and review["no_model_output_existed"] is True
    assert "not independent expert review" in review["independence_limit"]


def test_notebook_is_pinned_to_the_freeze_and_runs_dev20_only_through_the_v10_gate():
    nb = BOOT / "notebooks" / "artemis_mission005o_colab.ipynb"
    if not nb.exists():
        pytest.skip("notebook is added in the commit after the freeze")
    text = nb.read_text(encoding="utf-8")
    commit = re.search(r"CODE_COMMIT = '([0-9a-f]{40})'", text).group(1)
    assert "gate10.run(prepared, ACC_DIR)" in text and "gate10.run_dev20(" in text and "if record['decision'] == 'pass'" in text
    shown = subprocess.run(["git", "show", f"{commit}:experiments/waymaker-ai/artemis_bootstrap/validation/mission005o_acceptance_manifest.json"],
                           cwd=BOOT, capture_output=True)
    if shown.returncode:
        pytest.skip("needs git history for the pinned commit")
    assert hashlib.sha256(shown.stdout).hexdigest() == MANIFEST_SHA256
