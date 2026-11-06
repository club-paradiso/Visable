"""Mission 005-W: the first model call names the codes a choice question asks between (choice_codes, contract v17).

In 005-V all six choice questions got a first answer naming only the right code; the choice retry added
the other code in two and the raw channel scores the first answer. The codes are visible before inference,
so the pipeline now hands them to the model on the first call. The choice retry stays as a second line.
Fictional fixtures, plus the suites and recorded answers of earlier runs.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import dev20_v2
import grounding_guard as guard
import synthetic_safety_gate_v18 as gate18
from gemma4_runtime import build_messages
from waymaker_ai.evidence_registry import load_real_world_registry
from waymaker_ai.inference_input import project_inference_item
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS

EV = [{"id": "E-1", "text": "[가상 지침] 가상 연수 과정은 X-4-1, 가상 현장 과정은 X-4-2에 해당한다."}]
MARKED = ["A05V-45", "A05V-62", "A05V-63", "A05V-68", "A05V-70", "A05V-71", "ARTEMIS-004-DEV-003", "ARTEMIS-004-DEV-004"]


@pytest.mark.parametrize("question, codes", [
    ("가상 현장 과정 수료자는 X-4-1과 X-4-2 중 어느 코드로 신청하나요?", ["X-4-1", "X-4-2"]),
    ("Should a field-course graduate apply under X-4-2 or X-4-1?", ["X-4-2", "X-4-1"]),      # question order
    ("가상 현장 과정 수료자는 X-4-1과 X-4-3 중 어느 코드로 신청하나요?", []),               # X-4-3 is in no evidence
    ("X-4 또는 X-4-2 규정을 따르나요?", []),                                               # a code and its parent
    ("X-4-1 수수료와 X-4-2 수수료를 알려 주세요.", []),                                     # no choosing word
])
def test_the_mark_names_the_choice_codes_the_evidence_names(question, codes):
    assert guard.choice_marks(question, EV) == codes


def test_v17_adds_only_the_input_name_and_the_choice_codes_line():
    assert CONTRACT_VERSIONS[-1] == "v17" and guard.CONTRACT_VERSION == "v17"
    v16, v17 = SYSTEM_PROMPTS["v16"].splitlines(), SYSTEM_PROMPTS["v17"].splitlines()
    assert len(v17) == len(v16) + 1
    added = [line for line in v17 if line not in v16]
    assert len(added) == 2 and "choice_codes" in added[0] and added[1].startswith("If choice_codes is given")


def test_choice_codes_is_an_allowlisted_v17_input_of_this_item_only():
    item = {"question": "가상 질문", "evidence": EV,
            "system": {"reply_language": "ko", "uncovered_items": [], "choice_codes": ["X-4-1", "X-4-2"]}}
    assert project_inference_item(item)["system"]["choice_codes"] == ["X-4-1", "X-4-2"]
    assert list(json.loads(build_messages(item, "v17")[1]["content"])) == [
        "question", "reply_language", "uncovered_items", "choice_codes", "evidence"]
    with pytest.raises(ValueError, match="v17 input"):
        build_messages(item, "v16")
    for bad in (["X-4-1"], ["X-4-1", "X-4-1"], ["X-4-1", "X-4-3"], ["X-4-1", "x-4-2"], "X-4-1, X-4-2"):
        with pytest.raises(ValueError, match="choice_codes"):
            project_inference_item({**item, "system": {**item["system"], "choice_codes": bad}})


def _marked(question, intake, evidence, registry, date):
    prepared = guard.prepare(question, intake, evidence, registry, date)
    return any("choice_codes" in item["system"] for item in prepared["model_items"]), prepared


def test_across_earlier_suites_and_dev20_the_mark_falls_on_exactly_the_eight_choice_questions():
    marked = []
    for path in sorted(BOOT.glob("validation/mission005*_synthetic_acceptance.json")):
        if path.name >= "mission005w":
            continue
        for case in json.loads(path.read_text())["cases"]:
            if _marked(case["question"], case.get("intake"), case["evidence"], gate18.registry_for(case, "acceptance"),
                       case.get("as_of") or "2026-11-02")[0]:
                marked.append(case["id"])
    registry = load_real_world_registry(dev20_v2.REGISTRY_V2)
    marked += [i["id"] for i in dev20_v2.load_items()[0]
               if _marked(i["question"], None, i["evidence"], registry, "2026-11-02")[0]]
    assert sorted(marked) == sorted(MARKED)


def test_dev20_003_carries_the_mark_on_the_first_call():
    registry = load_real_world_registry(dev20_v2.REGISTRY_V2)
    item = {i["id"]: i for i in dev20_v2.load_items()[0]}["ARTEMIS-004-DEV-003"]
    _, prepared = _marked(item["question"], None, item["evidence"], registry, "2026-11-02")
    payload = json.loads(build_messages(prepared["model_item"], guard.CONTRACT_VERSION)[1]["content"])
    assert payload["choice_codes"] == ["D-2-1", "D-2-2"]


def _recorded_005v(cid):
    suite = {c["id"]: c for c in json.loads((BOOT / "validation" / "mission005v_synthetic_acceptance.json").read_text())["cases"]}
    rows = [json.loads(l) for l in (BOOT / "runs" / "mission005v" / "synthetic_acceptance" / "pipeline.jsonl").read_text().splitlines()]
    return suite[cid], {r["case_id"]: r for r in rows}[cid]


def _run(case, outputs):
    seen, outs = [], list(outputs)

    def generate(item):
        seen.append(item)
        build_messages(item, guard.CONTRACT_VERSION)
        return outs.pop(0)
    record = guard.run_case(case["question"], case["intake"], case["evidence"], gate18.registry_for(case, "acceptance"),
                            "2026-11-02", generate)
    return record, seen


def test_the_choice_retry_is_still_the_second_line():
    case, rec = _recorded_005v("A05V-63")
    record, seen = _run(case, [rec["raw_output"], rec["choice_retry"]["raw_outputs"][0]])
    assert len(seen) == 2 and seen[0]["system"]["choice_codes"] == ["X-4-1", "X-4-4"] and "choice_retry" in seen[1]["system"]
    assert record["released_provenance"] == "model_generated" and "X-4-4" in record["released"]["answer"]


def test_a_first_answer_covering_both_codes_is_not_asked_again():
    case, rec = _recorded_005v("A05V-63")
    record, seen = _run(case, [rec["choice_retry"]["raw_outputs"][0]])
    assert len(seen) == 1 and record["choice_retry"] is None
    assert gate18.score_case(case, record)["raw"]["outcome"] == "pass"


@pytest.mark.parametrize("question, personal", [
    ("가상 I-5-1 대나무발제작기능원이 근무처를 추가하여 신고할 때 어떤 서류를 내야 하나요?", False),   # A05W-74
    ("Can I-5-2 holders take a part-time job?", False),
    ("Should I-5-1 holders report a new address?", False),
    ("I hold a fictional Y-3 status. Can I take a part-time job?", True),
    ("May I apply for an extension?", True),
])
def test_a_status_code_letter_is_not_the_pronoun_i(question, personal):
    from waymaker_ai.evidence_admissibility import _DECISION, _FIRST_PERSON
    assert bool(_FIRST_PERSON.search(question) and _DECISION.search(question)) is personal
