"""Mission 005-T: an answer whose status or form is visibly wrong is asked once more (status_retry, contract v14).

Recorded habits: A05M/N-28·29 and A05Q/R/S-28 gave both values of two records that differ only in their
numbers but used status answered; A05P/R/S-60 used partial with nothing uncovered, and A05K-41 and
A05R/S-60 wrote an input field name into the answer. status_check finds these from the pipeline's own
inputs. Fictional fixtures, plus the recorded answers of earlier runs.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import grounding_guard as guard
import status_check
import synthetic_safety_gate_v15 as gate15
from gemma4_runtime import build_messages
from waymaker_ai.inference_input import project_inference_item
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS

N = "[가상 고시 제3호] Y-3-1 체류자의 외국인등록 수수료는 35,000원이다."
M = "[가상 편람] Y-3-1 체류자의 외국인등록 수수료는 72,000원이다."


def test_two_records_differing_only_in_their_numbers_are_a_conflict():
    assert status_check.conflicting_values([N, M]) == [(["35000"], ["72000"])]
    found = status_check.problems("answered", "35,000원과 72,000원입니다.", [N, M], [])
    assert [f["kind"] for f in found] == ["conflict_not_labelled"]
    assert status_check.problems("conflict", "35,000원과 72,000원입니다.", [N, M], []) == []


@pytest.mark.parametrize("other", [
    "[가상 편람] Y-3-2 체류자의 외국인등록 수수료는 72,000원이다.",         # another sub-code
    "[가상 편람] Y-3-1 체류자의 체류기간 연장 수수료는 72,000원이다.",        # another procedure
    "[가상 편람] Y-3-1 체류자의 외국인등록 수수료는 35,000원이다.",          # the same value
])
def test_records_that_differ_in_more_than_numbers_are_not(other):
    assert status_check.conflicting_values([N, other]) == []


def test_partial_with_nothing_uncovered_and_input_field_names():
    assert [f["kind"] for f in status_check.problems("partial", "32일입니다.", [], [])] == ["partial_without_uncovered"]
    assert status_check.problems("partial", "32일입니다.", [], ["fee"]) == []
    found = status_check.problems("partial", "32 ngày. uncovered_sentence: …", [], [])
    assert [f["kind"] for f in found] == ["partial_without_uncovered", "input_field_named"]
    assert found[1]["detail"] == ["uncovered_sentence"]


def test_recorded_answers_of_earlier_runs_fire_only_on_the_known_habits():
    fired = {}
    for run in sorted(BOOT.glob("runs/mission005*/synthetic_acceptance/pipeline.jsonl")):
        mission = run.parts[-3][-1]
        if mission >= "t":   # runs made with the status retry itself
            continue
        suite = BOOT / "validation" / f"mission005{mission}_synthetic_acceptance.json"
        cases = {c["id"]: c for c in json.loads(suite.read_text())["cases"]}
        for line in run.read_text().splitlines():
            r = json.loads(line)
            if not r.get("model_called") or r["case_id"] not in cases or r.get("subcode_parts") or r.get("situation_parts"):
                continue
            try:
                out = json.loads(r["raw_output"])
            except (TypeError, ValueError):
                continue
            if not isinstance(out, dict) or not isinstance(out.get("answer"), str):
                continue
            texts = {e["id"]: e["text"] for e in cases[r["case_id"]]["evidence"]}
            cited = [texts[i] for i in out.get("citations") or [] if i in texts and i in r["admissible_ids"]]
            for f in status_check.problems(out.get("status"), out["answer"], cited, r["uncovered_items"]):
                fired.setdefault(f["kind"], []).append(r["case_id"])
    assert sorted(fired["conflict_not_labelled"]) == ["A05M-28", "A05M-29", "A05N-28", "A05N-29", "A05Q-28", "A05R-28", "A05S-28"]
    assert sorted(fired["partial_without_uncovered"]) == ["A05P-60", "A05R-60", "A05S-60"]
    assert sorted(fired["input_field_named"]) == ["A05K-41", "A05R-60", "A05S-60"]


def test_v14_adds_only_the_input_name_and_the_retry_line():
    assert "v14" in CONTRACT_VERSIONS and guard.CONTRACT_VERSION in ("v14", "v15", "v16", "v17")   # 005-U: v15, 005-V: v16, 005-W: v17
    v13, v14 = SYSTEM_PROMPTS["v13"].splitlines(), SYSTEM_PROMPTS["v14"].splitlines()
    assert len(v14) == len(v13) + 1
    added = [line for line in v14 if line not in v13]
    assert len(added) == 2 and "status_retry" in added[0] and added[1].startswith("If status_retry is given")


def test_status_retry_is_an_allowlisted_one_line_v14_input():
    note = guard.status_note([{"kind": "partial_without_uncovered", "detail": None}], "en")
    item = {"question": "가상 질문", "evidence": [], "system": {"reply_language": "en", "uncovered_items": [], "status_retry": note}}
    assert project_inference_item(item)["system"]["status_retry"] == note
    assert list(json.loads(build_messages(item, "v14")[1]["content"])) == [
        "question", "reply_language", "uncovered_items", "status_retry", "evidence"]
    with pytest.raises(ValueError, match=r"v14\+? input"):
        build_messages(item, "v13")


def _recorded(cid):
    suite = json.loads((BOOT / "validation" / "mission005s_synthetic_acceptance.json").read_text())
    case = {c["id"]: c for c in suite["cases"]}[cid]
    raw = {json.loads(l)["case_id"]: json.loads(l) for l in
           (BOOT / "runs" / "mission005s" / "synthetic_acceptance" / "pipeline.jsonl").read_text().splitlines()}[cid]["raw_output"]
    return case, raw


def _run(case, outputs):
    seen, outs = [], list(outputs)

    def generate(item):
        seen.append(item)
        build_messages(item, guard.CONTRACT_VERSION)   # 005-U: the first call also carries conflict_records (v15)
        return outs.pop(0)
    record = guard.run_case(case["question"], case["intake"], case["evidence"], gate15.registry_for(case, "acceptance"),
                            "2026-11-02", generate)
    return record, seen


CONFLICT = json.dumps({"status": "conflict", "citations": ["M82-REG-FEE-N", "M82-REG-FEE-M"],
                       "answer": "The agency notice says 33,000 KRW and the operations handbook says 61,000 KRW; they conflict."})


def test_an_unlabelled_conflict_is_asked_again_and_the_conflict_answer_is_released_and_correct():
    case, first = _recorded("A05S-28")
    record, seen = _run(case, [first, CONFLICT])
    assert len(seen) == 2 and "use status conflict" in seen[1]["system"]["status_retry"]
    assert "33000" in seen[1]["system"]["status_retry"] and "61000" in seen[1]["system"]["status_retry"]
    assert record["released"]["status"] == "conflict" and record["status_retry"]["raw_output"] == CONFLICT
    row = gate15.score_case(case, record)
    assert row["raw"]["checks"]["status"] is False and row["end_to_end"]["correct"] is True
    assert row["end_to_end"]["status_retry"] is True


def test_partial_with_nothing_uncovered_is_asked_again():
    case, first = _recorded("A05S-60")
    answered = json.dumps({"status": "answered", "citations": ["M81-EXT-PROC-DOM"],
                           "answer": "Thời gian xử lý gia hạn lưu trú cho người M-8-1 ở trong nước là trong vòng 32 ngày kể từ ngày nộp hồ sơ."})
    record, seen = _run(case, [first, answered])
    note = seen[1]["system"]["status_retry"]
    assert "uncovered_items trống" in note and "uncovered_sentence" in note
    assert record["released"]["status"] == "answered" and gate15.score_case(case, record)["end_to_end"]["correct"] is True


def test_a_retry_the_guard_holds_back_keeps_the_earlier_answer():
    case, first = _recorded("A05S-28")
    wrong = json.dumps({"status": "conflict", "citations": ["M82-REG-FEE-N", "M82-REG-FEE-M"],
                        "answer": "The notice says 33,000 KRW and the handbook says 99,000 KRW."})
    record, _ = _run(case, [first, wrong])
    assert record["status_retry"]["raw_output"] == first and record["released"]["status"] == "answered"


def test_a_correct_first_answer_is_not_asked_again():
    case, _ = _recorded("A05S-28")
    record, seen = _run(case, [CONFLICT])
    assert len(seen) == 1 and record["status_retry"] is None


@pytest.mark.parametrize("question, kind", [
    ("I'm on a fictional Y-3 status — am I permitted to do part-time work?", "personal"),
    ("I hold a fictional Y-3 status. Am I able to take a part-time job?", "personal"),
    ("I hold a fictional Y-3 status. Am I allowed to take a part-time job?", "personal"),
    ("Is a fictional Y-3 holder permitted to do part-time work?", "general"),
])
def test_am_i_permitted_is_a_request_for_a_decision(question, kind):
    from waymaker_ai.evidence_admissibility import _DECISION, _FIRST_PERSON
    assert ("personal" if (_FIRST_PERSON.search(question) and _DECISION.search(question)) else "general") == kind
