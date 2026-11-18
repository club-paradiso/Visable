"""The guarded DEV-20 scorer grades released responses and keeps withheld items apart."""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import grounding_guard as guard
import real_world_registry as rwr
import score_dev20_guarded as scorer
from waymaker_ai.evidence_registry import load_real_world_registry


def stub_run(tmp_path, reply):
    registry = load_real_world_registry(rwr.REGISTRY)
    lines = []
    for item in rwr.dev20_items():
        rec = guard.run_case(item["question"], None, item["evidence"], registry, rwr.EVALUATION_DATE,
                             lambda model_item, item=item: reply(item, model_item))
        lines.append(json.dumps({"case_id": item["id"], "registry_status": "loaded", **rec}, ensure_ascii=False))
    (tmp_path / "pipeline.jsonl").write_text("\n".join(lines) + "\n")
    return scorer.score(tmp_path)


def test_withheld_and_model_called_items_are_counted_apart(tmp_path):
    result = stub_run(tmp_path, lambda item, m: json.dumps({"status": "insufficient_evidence", "answer": "근거 부족", "citations": []}))
    s = result["summary"]
    assert (s["items"], s["model_called"], s["withheld_before_model"]) == (20, 8, 12)
    by = {c["case_id"]: c for c in result["cases"]}
    assert by["ARTEMIS-004-DEV-005"]["evidence_decisions"] == {"EV-DEV-005-A": "verification_rejected"}
    assert by["ARTEMIS-004-DEV-013"]["passed"] is True   # the attack probe is withheld, as its rubric expects


def test_a_system_notice_is_part_of_what_is_scored():
    rec = {"released": {"status": "partial", "answer": "A.", "citations": ["X"], "system_notice": "Not covered: fee."}}
    assert scorer.released_response(rec) == {"status": "partial", "answer": "A. Not covered: fee.", "citations": ["X"]}


def test_the_scorer_refuses_a_partial_run(tmp_path):
    (tmp_path / "pipeline.jsonl").write_text(json.dumps({"case_id": "ARTEMIS-004-DEV-001"}) + "\n")
    with pytest.raises(ValueError, match="exactly the 20"):
        scorer.score(tmp_path)
