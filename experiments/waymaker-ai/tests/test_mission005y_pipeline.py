"""Mission 005-Y: a choice part that leaves out its own code is asked once more, then gets a notice.

In the 005-X run DEV-20 v2 items 003 and 004 got the same answer from both choice parts, naming only the
right code; the part asked about the other code (D-2-1, E-7-1) did not name it. 005-X had switched the
005-V choice check off for choice parts, so nothing repaired it and 003 lost the notice it passed with in
005-W. Each choice part is now checked for its own code (choice_retry, then the quoting notice), and an
answer text two parts both gave is joined once. Contract v18 is unchanged. Recorded answers of earlier runs.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import dev20_v2
import grounding_guard as guard
import synthetic_safety_gate_v19 as gate19
from dev20_v2 import released_response, score_response
from gemma4_runtime import build_messages
from waymaker_ai.evidence_registry import load_real_world_registry

RUN_X = BOOT / "runs" / "mission005x"


def _records(folder):
    return {json.loads(l)["case_id"]: json.loads(l) for l in (folder / "pipeline.jsonl").read_text().splitlines()}


def _outputs(record):
    """The recorded model outputs of a record, in call order."""
    outs = list(record.get("raw_outputs") or [record["raw_output"]])
    for key in ("language_retry", "value_retry", "branch_retry", "choice_retry", "status_retry"):
        if record.get(key):
            outs += record[key]["raw_outputs"]
    return outs


def _replay(question, intake, evidence, registry, outs):
    outs, seen = list(outs), []

    def generate(item):
        seen.append(item)
        build_messages(item, guard.CONTRACT_VERSION)
        return outs.pop(0)
    record = guard.run_case(question, intake, evidence, registry, "2026-11-02", generate)
    return record, seen, outs


def test_the_contract_is_unchanged():
    assert guard.CONTRACT_VERSION == "v18"


@pytest.mark.parametrize("cid, asked, term", [("ARTEMIS-004-DEV-003", "D-2-1", "전문학사"),
                                               ("ARTEMIS-004-DEV-004", "E-7-1", "전문인력")])
def test_dev20_part_that_left_out_its_code_is_asked_again_and_then_quoted(cid, asked, term):
    registry = load_real_world_registry(dev20_v2.REGISTRY_V2)
    item = {i["id"]: i for i in dev20_v2.load_items()[0]}[cid]
    rec = _records(RUN_X / "dev20_v2")[cid]
    first = rec["raw_outputs"]
    # worst case: the retried part answers exactly as before
    record, seen, left = _replay(item["question"], None, item["evidence"], registry, first + [first[0]])
    assert not left and len(seen) == 3
    assert seen[2]["system"]["choice_part"] == asked and asked in seen[2]["system"]["choice_retry"]
    assert record["choice_retry"]["parts"] == [0]
    assert record["released_provenance"] == "model_generated_with_system_notice"
    assert record["released"]["answer"] == json.loads(first[0])["answer"]          # the identical part answer once
    assert asked in record["released"]["system_notice"] and term in record["released"]["system_notice"]
    assert score_response(item, released_response(record)).overall_passed


def test_a_retried_part_that_names_its_code_is_released_without_a_notice():
    registry = load_real_world_registry(dev20_v2.REGISTRY_V2)
    item = {i["id"]: i for i in dev20_v2.load_items()[0]}["ARTEMIS-004-DEV-003"]
    first = _records(RUN_X / "dev20_v2")["ARTEMIS-004-DEV-003"]["raw_outputs"]
    fixed = json.dumps({"status": "answered", "citations": ["EV-DEV-003-A"],
                        "answer": "D-2-1은 전문학사 과정에 해당하므로 4년제 학사과정 신입학에는 해당하지 않습니다."}, ensure_ascii=False)
    record, _, left = _replay(item["question"], None, item["evidence"], registry, first + [fixed])
    assert not left and record["released_provenance"] == "model_generated"
    assert record["released"]["answer"].startswith("D-2-1은 전문학사") and not record["released"].get("system_notice")


def test_every_other_recorded_dev20_answer_of_005x_is_released_unchanged():
    registry = load_real_world_registry(dev20_v2.REGISTRY_V2)
    items = {i["id"]: i for i in dev20_v2.load_items()[0]}
    for cid, rec in _records(RUN_X / "dev20_v2").items():
        if not rec["model_called"] or cid in ("ARTEMIS-004-DEV-003", "ARTEMIS-004-DEV-004"):
            continue
        record, _, left = _replay(items[cid]["question"], None, items[cid]["evidence"], registry, _outputs(rec))
        assert not left and record["released"] == rec["released"], cid


def test_every_recorded_005x_synthetic_answer_is_released_unchanged():
    suite = {c["id"]: c for c in json.loads((BOOT / "validation" / "mission005x_synthetic_acceptance.json").read_text())["cases"]}
    for cid, rec in _records(RUN_X / "synthetic_acceptance").items():
        if not rec["model_called"]:
            continue
        case = suite[cid]
        record, _, left = _replay(case["question"], case["intake"], case["evidence"], gate19.registry_for(case, "acceptance"),
                                  _outputs(rec))
        assert not left and record["released"] == rec["released"] and record["choice_retry"] is None, cid


def test_identical_part_answers_are_joined_once_and_different_ones_in_order():
    a = {"decision": "release", "findings": [], "parsed": {"status": "answered", "answer": "같은 답", "citations": ["E-1"]}}
    b = {"decision": "release", "findings": [], "parsed": {"status": "answered", "answer": "다른 답", "citations": ["E-2"]}}
    raws = [json.dumps(x["parsed"], ensure_ascii=False) for x in (a, a, b)]
    out, composed = guard._join_parts([a, a, b], raws)
    assert out["parsed"]["answer"] == "같은 답\n다른 답" and json.loads(composed)["answer"] == "같은 답\n다른 답"
    assert out["parsed"]["citations"] == ["E-1", "E-2"]
