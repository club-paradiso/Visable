"""Mission 005-X: a choice question is asked one choice code at a time (choice_part, contract v18).

In 005-W the choice_codes mark got both codes into the first answer in two of six choice questions, both
Vietnamese. The pipeline now makes one call per choice code, in question order, and joins the answers as
it joins sub-code parts (005-J), so the raw channel scores a first answer that covers every code. A part
that gives a value the evidence states only for another choice code is asked once more (value_retry) and
withheld if it still does. Fictional fixtures, plus the suites and recorded answers of earlier runs.
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
import synthetic_safety_gate_v18 as gate18
from gemma4_runtime import build_messages
from waymaker_ai.evidence_registry import load_real_world_registry
from waymaker_ai.inference_input import project_inference_item
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS

FEE = ("[I-5 Craft Stay Manual (fictional)] The foreigner registration fee for an I-5-1 holder is 46,000 won. "
       "The foreigner registration fee for an I-5-3 holder is 19,000 won.")
CHOICE_QUESTIONS = ["A05V-45", "A05V-62", "A05V-63", "A05V-68", "A05V-70", "A05V-71",
                    "A05W-02", "A05W-45", "A05W-62", "A05W-68", "A05W-70", "A05W-81",
                    "ARTEMIS-004-DEV-003", "ARTEMIS-004-DEV-004"]


def _questions():
    out = []
    for path in sorted(BOOT.glob("validation/mission005*_synthetic_acceptance.json")):
        if path.name >= "mission005x":
            continue
        for c in json.loads(path.read_text())["cases"]:
            out.append((c["id"], c["question"], c.get("intake"), c["evidence"], gate18.registry_for(c, "acceptance"),
                        c.get("as_of") or "2026-11-02"))
    registry = load_real_world_registry(dev20_v2.REGISTRY_V2)
    out += [(i["id"], i["question"], None, i["evidence"], registry, "2026-11-02") for i in dev20_v2.load_items()[0]]
    return out


QUESTIONS = _questions()


def test_v18_adds_only_the_input_names_and_the_choice_part_line():
    assert CONTRACT_VERSIONS[-1] == "v18" and guard.CONTRACT_VERSION == "v18"
    v17, v18 = SYSTEM_PROMPTS["v17"].splitlines(), SYSTEM_PROMPTS["v18"].splitlines()
    assert len(v18) == len(v17) + 1
    added = [line for line in v18 if line not in v17]
    assert len(added) == 2 and "choice_part" in added[0] and "value_retry" in added[0]
    assert added[1].startswith("If choice_part is given") and "If value_retry is given" in added[1]


def test_choice_part_and_value_retry_are_allowlisted_v18_inputs():
    ev = [{"id": "E-1", "text": FEE}]
    item = {"question": "가상 질문", "evidence": ev, "system": {"reply_language": "ko", "uncovered_items": [],
                                                              "choice_codes": ["I-5-3", "I-5-1"], "choice_part": "I-5-3"}}
    assert project_inference_item(item)["system"]["choice_part"] == "I-5-3"
    assert list(json.loads(build_messages(item, "v18")[1]["content"])) == [
        "question", "reply_language", "uncovered_items", "choice_codes", "choice_part", "evidence"]
    with pytest.raises(ValueError, match="v18 inputs"):
        build_messages(item, "v17")
    with pytest.raises(ValueError, match="choice_part"):
        project_inference_item({**item, "system": {**item["system"], "choice_part": "I-5-2"}})
    no_codes = {k: v for k, v in item["system"].items() if k != "choice_codes"}
    with pytest.raises(ValueError, match="choice_part"):
        project_inference_item({**item, "system": no_codes})
    retry = {**item, "system": {**item["system"], "value_retry": "이번 호출은 I-5-3만 묻습니다."}}
    assert list(json.loads(build_messages(retry, "v18")[1]["content"]))[-2] == "value_retry"
    for bad in ("", "두 줄\n입니다", "x" * 601):
        with pytest.raises(ValueError, match="value_retry"):
            project_inference_item({**item, "system": {**item["system"], "value_retry": bad}})


def test_across_earlier_suites_and_dev20_only_the_fourteen_choice_questions_are_split_per_code():
    split = {}
    for cid, q, intake, ev, reg, date in QUESTIONS:
        prepared = guard.prepare(q, intake, ev, reg, date)
        codes = [p["choice_part"] for p in prepared["parts"] if p.get("choice_part")]
        if codes:
            split[cid] = (codes, prepared)
    assert sorted(split) == sorted(CHOICE_QUESTIONS)
    for cid, (codes, prepared) in split.items():
        assert codes == choice.choice_codes(prepared["selection"]["context_question"])   # question order
        assert all(item["evidence"] == prepared["selection"]["admissible"] for item in prepared["model_items"])
        assert all(item["system"]["choice_codes"] == codes for item in prepared["model_items"])


def test_every_other_question_gets_exactly_the_005w_model_items(monkeypatch):
    now = {cid: guard.prepare(q, intake, ev, reg, date)["model_items"] for cid, q, intake, ev, reg, date in QUESTIONS}
    monkeypatch.setattr(guard, "CHOICE_PARTS", False)
    for cid, q, intake, ev, reg, date in QUESTIONS:
        if cid not in CHOICE_QUESTIONS:
            assert now[cid] == guard.prepare(q, intake, ev, reg, date)["model_items"], cid


@pytest.mark.parametrize("answer, swapped", [
    ("I-5-3 holders pay 46,000 won.", ["46,000"]),
    ("Phí đăng ký của I-5-3 là 46.000 won.", ["46.000"]),             # thousands separator as written
    ("I-5-3 holders pay 19,000 won.", []),
    ("I-5-3 holders pay 19,000 won; I-5-1 holders pay 46,000 won.", []),   # a contrast that names the other code
    ("I-5-3 holders pay 19.000 won.", []),
    ("I-5-3 holders pay forty-six thousand won.", []),                 # words are not seen
])
def test_a_value_of_the_other_code_is_found_in_sentences_about_this_code(answer, swapped):
    found = choice.swapped_values("I-5-3", ["I-5-3", "I-5-1"], answer, [FEE])
    assert [v for f in found for v in f["values"]] == swapped
    if swapped:
        assert found[0]["sentence"] == "The foreigner registration fee for an I-5-3 holder is 19,000 won."


@pytest.mark.parametrize("answer, swapped", [
    ("I-5-3 pays 19,000 won, not 46,000 won.", []),                  # the question's value as a contrast
    ("I-5-3 pays 46,000 won.", ["46,000"]),
    ("I-5-3 is not the one with 46,000 won.", ["46,000"]),            # no own value: asked again to state it
])
def test_a_value_the_question_quotes_counts_only_without_the_codes_own_value(answer, swapped):
    q = "Which of I-5-3 and I-5-1 pays a 46,000 won registration fee?"
    found = choice.swapped_values("I-5-3", ["I-5-3", "I-5-1"], answer, [FEE], q)
    assert [v for f in found for v in f["values"]] == swapped


def test_one_shared_sentence_has_no_value_to_compare():
    shared = "[가상 지침] 전문학사 과정은 D-2-1, 일반학사 과정은 D-2-2에 해당합니다."
    assert choice.own_sentences("D-2-1", ["D-2-1", "D-2-2"], [shared]) == []
    assert choice.swapped_values("D-2-1", ["D-2-1", "D-2-2"], "D-2-1은 2년제입니다.", [shared]) == []


def _case(cid):
    path = {"A05V": "mission005v", "A05W": "mission005w"}[cid[:4]]
    return {c["id"]: c for c in json.loads((BOOT / "validation" / f"{path}_synthetic_acceptance.json").read_text())["cases"]}[cid]


def _ans(text, cite):
    return json.dumps({"status": "answered", "answer": text, "citations": [cite]}, ensure_ascii=False)


def _run(case, outputs):
    seen, outs = [], list(outputs)

    def generate(item):
        seen.append(item)
        build_messages(item, guard.CONTRACT_VERSION)
        return outs.pop(0)
    record = guard.run_case(case["question"], case["intake"], case["evidence"], gate18.registry_for(case, "acceptance"),
                            "2026-11-02", generate)
    assert not outs
    return record, seen


CITE_45 = "I51-I53-REG-FEE-EN"
RIGHT_53 = _ans("I-5-3 자개공예기능원의 외국인등록 수수료는 19,000원이므로 질문이 묻는 쪽이 아닙니다.", CITE_45)
RIGHT_51 = _ans("I-5-1 대나무발제작기능원의 외국인등록 수수료가 46,000원입니다.", CITE_45)
SWAPPED_53 = _ans("I-5-3 자개공예기능원의 외국인등록 수수료는 46,000원입니다.", CITE_45)


def test_two_parts_are_joined_in_question_order_and_no_choice_retry_fires():
    case = _case("A05W-45")
    record, seen = _run(case, [RIGHT_53, RIGHT_51])
    assert [s["system"]["choice_part"] for s in seen] == ["I-5-3", "I-5-1"]
    assert record["choice_retry"] is None and record["value_retry"] is None
    assert record["released_provenance"] == "model_generated"
    assert record["released"]["answer"] == json.loads(RIGHT_53)["answer"] + "\n" + json.loads(RIGHT_51)["answer"]
    assert gate18.score_case(case, record)["raw"]["outcome"] == "pass"     # the joined first answer covers both codes


def test_a_swapped_value_is_asked_once_more_and_the_corrected_answer_is_released():
    case = _case("A05W-45")
    record, seen = _run(case, [SWAPPED_53, RIGHT_51, RIGHT_53])
    assert len(seen) == 3 and "value_retry" in seen[2]["system"] and seen[2]["system"]["choice_part"] == "I-5-3"
    assert "46,000" in seen[2]["system"]["value_retry"] and "19,000 won" in seen[2]["system"]["value_retry"]
    assert record["value_retry"]["parts"] == [0]
    assert record["released_provenance"] == "model_generated" and "19,000원" in record["released"]["answer"]


def test_a_value_still_swapped_after_the_retry_withholds_the_joined_answer():
    case = _case("A05W-45")
    record, _ = _run(case, [SWAPPED_53, RIGHT_51, SWAPPED_53])
    assert record["released_provenance"] == "post_generation_blocked"
    assert any(f["check"] == "choice_value" and f["effect"] == "withhold" for f in record["value_retry"]["guard"]["findings"])


def test_dev20_003_and_004_are_asked_per_code():
    registry = load_real_world_registry(dev20_v2.REGISTRY_V2)
    items = {i["id"]: i for i in dev20_v2.load_items()[0]}
    for cid, codes in (("ARTEMIS-004-DEV-003", ["D-2-1", "D-2-2"]), ("ARTEMIS-004-DEV-004", ["E-7-1", "E-7-4"])):
        prepared = guard.prepare(items[cid]["question"], None, items[cid]["evidence"], registry, "2026-11-02")
        assert [i["system"]["choice_part"] for i in prepared["model_items"]] == codes


def test_recorded_first_answers_of_005v_and_005w_name_no_swapped_value():
    """Every recorded first answer to a choice question named the right code with its own value."""
    for mission, cids in (("mission005v", CHOICE_QUESTIONS[:6]), ("mission005w", CHOICE_QUESTIONS[6:12])):
        rows = {json.loads(l)["case_id"]: json.loads(l) for l in
                (BOOT / "runs" / mission / "synthetic_acceptance" / "pipeline.jsonl").read_text().splitlines()}
        for cid in cids:
            case = _case(cid)
            answer = json.loads(rows[cid]["raw_output"])["answer"]
            codes = choice.choice_codes(case["question"])
            named = [c for c in codes if c in answer]
            texts = [e["text"] for e in case["evidence"]]
            assert all(choice.swapped_values(c, codes, answer, texts) == [] for c in named), cid
