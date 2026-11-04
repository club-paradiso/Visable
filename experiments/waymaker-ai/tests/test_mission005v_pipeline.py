"""Mission 005-V: a choice question answered with only one of its codes is asked once more (choice_retry, contract v16).

DEV-20 v2 items 003 (D-2-1 or D-2-2) and 004 (E-7-1 or E-7-4) ask which of two sibling sub-codes applies;
the cited evidence names both. The model named the right code and left out the other in all six recorded
runs of 003 and in three of 004. choice_coverage finds this from the pipeline's own inputs. Fictional
fixtures, plus the questions and recorded answers of earlier runs.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import choice_coverage as choice
import dev20_v2
import grounding_guard as guard
from gemma4_runtime import build_messages
from waymaker_ai.evidence_registry import load_real_world_registry
from waymaker_ai.inference_input import project_inference_item
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS

EV = "[가상 지침] 가상 연수 과정은 X-4-1, 가상 현장 과정은 X-4-2에 해당한다. 현장 과정 수료자는 X-4-2로 신청한다."


@pytest.mark.parametrize("question, codes", [
    ("가상 현장 과정 수료자는 X-4-1과 X-4-2 중 어느 코드로 신청하나요?", ["X-4-1", "X-4-2"]),
    ("Should a field-course graduate apply under X-4-1 or X-4-2?", ["X-4-1", "X-4-2"]),
    ("Người học khóa thực địa nộp theo X-4-1 hay X-4-2?", ["X-4-1", "X-4-2"]),
    ("X-4 체류자 가운데 X-4-2 연수생은 X-4 또는 X-4-2 규정을 따르나요?", []),       # a code and its parent
    ("X-4-1 체류자의 수수료와 X-4-2 체류자의 수수료를 알려 주세요.", []),          # no choosing word
    ("가상 X-4-2 체류자는 어느 쪽 창구에 신청하나요?", []),                      # one code
])
def test_choice_questions_are_two_sibling_codes_with_a_choosing_word(question, codes):
    assert choice.choice_codes(question) == codes


def test_the_parent_pair_of_005n_is_not_a_choice():
    case = {c["id"]: c for c in json.loads((BOOT / "validation" / "mission005n_synthetic_acceptance.json").read_text())["cases"]}["A05N-01"]
    assert choice.choice_codes(case["question"]) == []


def test_a_code_is_missing_only_when_the_evidence_names_it_and_the_answer_names_another():
    q = "가상 현장 과정 수료자는 X-4-1과 X-4-2 중 어느 코드로 신청하나요?"
    left = choice.omitted_choices(q, "X-4-2로 신청합니다.", [EV])
    assert [(c["code"], c["codes"], c["named"]) for c in left] == [("X-4-1", ["X-4-1", "X-4-2"], ["X-4-2"])]
    assert left[0]["sentence"] == "가상 연수 과정은 X-4-1, 가상 현장 과정은 X-4-2에 해당한다."
    assert choice.omitted_choices(q, "X-4-1은 연수 과정이고 현장 과정은 X-4-2입니다.", [EV]) == []
    assert choice.omitted_choices(q, "현장 과정으로 신청합니다.", [EV]) == []          # names neither code
    only_one = "[가상 지침] 현장 과정 수료자는 X-4-2로 신청한다."
    assert choice.omitted_choices(q, "X-4-2로 신청합니다.", [only_one]) == []         # the evidence never names X-4-1


def test_v16_adds_only_the_input_name_and_the_choice_retry_line():
    assert CONTRACT_VERSIONS[-1] == "v16" and guard.CONTRACT_VERSION == "v16"
    v15, v16 = SYSTEM_PROMPTS["v15"].splitlines(), SYSTEM_PROMPTS["v16"].splitlines()
    assert len(v16) == len(v15) + 1
    added = [line for line in v16 if line not in v15]
    assert len(added) == 2 and "choice_retry" in added[0] and added[1].startswith("If choice_retry is given")


def test_choice_retry_is_an_allowlisted_one_line_v16_input():
    note = guard.choice_note([{"code": "X-4-1", "codes": ["X-4-1", "X-4-2"], "named": ["X-4-2"], "sentence": "가상 연수 과정은 X-4-1."}], "ko")
    assert note.startswith("질문은 X-4-1, X-4-2 가운데 어느 쪽인지 묻습니다.") and "X-4-1에 관한 내용이 없습니다" in note
    item = {"question": "가상 질문", "evidence": [], "system": {"reply_language": "ko", "uncovered_items": [], "choice_retry": note}}
    assert project_inference_item(item)["system"]["choice_retry"] == note
    assert list(json.loads(build_messages(item, "v16")[1]["content"])) == [
        "question", "reply_language", "uncovered_items", "choice_retry", "evidence"]
    with pytest.raises(ValueError, match="v16 input"):
        build_messages(item, "v15")


def _dev20(cid):
    items = {i["id"]: i for i in dev20_v2.load_items()[0]}
    return items[cid], load_real_world_registry(dev20_v2.REGISTRY_V2)


def _recorded_answers(cid):
    out = []
    for path in sorted(BOOT.glob("runs/**/generations.jsonl")):
        for line in path.read_text().splitlines():
            x = json.loads(line)
            if x.get("case_id") == cid:
                try:
                    out.append(json.loads(x["raw_output"]))
                except (TypeError, ValueError):
                    continue
    return out


@pytest.mark.parametrize("cid, fired", [("ARTEMIS-004-DEV-003", 6), ("ARTEMIS-004-DEV-004", 3)])
def test_recorded_dev20_answers_fire_exactly_where_the_other_code_was_left_out(cid, fired):
    item, _ = _dev20(cid)
    texts = [e["text"] for e in item["evidence"]]
    answers = _recorded_answers(cid)
    assert len(answers) == 6
    assert sum(bool(choice.omitted_choices(item["question"], a["answer"], texts)) for a in answers) == fired


def test_no_other_recorded_question_is_a_choice():
    items, _ = dev20_v2.load_items()
    found = [i["id"] for i in items if choice.choice_codes(i["question"])]
    for path in sorted(BOOT.glob("validation/mission005*_synthetic_acceptance.json")):
        if path.name >= "mission005v":
            continue
        found += [c["id"] for c in json.loads(path.read_text())["cases"] if choice.choice_codes(c["question"])]
    assert found == ["ARTEMIS-004-DEV-003", "ARTEMIS-004-DEV-004"]


def _run(cid, outputs):
    item, registry = _dev20(cid)
    seen, outs = [], list(outputs)

    def generate(model_item):
        seen.append(model_item)
        build_messages(model_item, guard.CONTRACT_VERSION)
        return outs.pop(0)
    return guard.run_case(item["question"], None, item["evidence"], registry, "2026-11-02", generate), seen


FIRST_003 = json.dumps({"status": "answered", "citations": ["EV-DEV-003-A"],
                        "answer": "4년제 일반대학교 학부(학사) 과정에 신입학하는 유학생은 D-2-2 세부코드로 신청해야 합니다."}, ensure_ascii=False)
BOTH_003 = json.dumps({"status": "answered", "citations": ["EV-DEV-003-A"],
                       "answer": "4년제 학사과정 입학자는 D-2-2로 신청해야 합니다. D-2-1은 전문학사 과정에 해당합니다."}, ensure_ascii=False)


def test_the_retried_answer_naming_both_codes_is_released_without_a_notice():
    record, seen = _run("ARTEMIS-004-DEV-003", [FIRST_003, BOTH_003])
    assert len(seen) == 2 and "D-2-1" in seen[1]["system"]["choice_retry"] and "전문학사" in seen[1]["system"]["choice_retry"]
    assert record["choice_retry"]["parts"] == [0] and record["choice_retry"]["raw_output"] == BOTH_003
    assert record["released"]["answer"].endswith("D-2-1은 전문학사 과정에 해당합니다.")
    assert record["released_provenance"] == "model_generated" and not record["released"].get("system_notice")


def test_a_retry_that_still_leaves_the_code_out_gets_a_quoting_notice():
    record, _ = _run("ARTEMIS-004-DEV-003", [FIRST_003, FIRST_003])
    assert record["released_provenance"] == "model_generated_with_system_notice"
    assert "D-2-1" in record["released"]["system_notice"] and "전문학사" in record["released"]["system_notice"]


def test_a_retry_the_guard_holds_back_keeps_the_earlier_answer_with_the_notice():
    unlisted = json.dumps({"status": "answered", "citations": ["EV-NOT-GIVEN"],
                           "answer": "D-2-2로 신청해야 합니다. D-2-1은 전문학사 과정에 해당합니다."}, ensure_ascii=False)
    record, _ = _run("ARTEMIS-004-DEV-003", [FIRST_003, unlisted])
    assert record["choice_retry"]["raw_output"] == FIRST_003
    assert record["released"]["answer"] == json.loads(FIRST_003)["answer"]
    assert record["released_provenance"] == "model_generated_with_system_notice" and "D-2-1" in record["released"]["system_notice"]


def test_a_first_answer_naming_both_codes_is_not_asked_again():
    record, seen = _run("ARTEMIS-004-DEV-003", [BOTH_003])
    assert len(seen) == 1 and record["choice_retry"] is None
