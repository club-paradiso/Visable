"""Mission 005-P: one retry when the reply language is the guard's only objection, contract v12 and gate v11.

Fictional fixtures only. In 005-O the model answered three Vietnamese questions with the Korean
evidence sentence (A05O-36/39/45); the guard held them back and the user got a review notice. The
pipeline now asks that answer once more with a language_retry note; the first answer stays the raw
output, and what is released is decided by the guard on the retried answer.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import grounding_guard as guard
import synthetic_safety_gate_v10 as gate10
import synthetic_safety_gate_v11 as gate11
from gemma4_runtime import build_messages
from waymaker_ai.inference_input import project_inference_item
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS, parse_response

CASES = {c["id"]: c for c in json.loads((BOOT / "validation" / "mission005o_synthetic_acceptance.json").read_text())["cases"]}
DATE = "2026-11-02"


def answer(status, text, cites):
    return json.dumps({"status": status, "answer": text, "citations": list(cites)}, ensure_ascii=False)


KO_45 = answer("answered", "V-3-2 체류자는 입국한 날부터 60일 이내에 외국인등록을 하여야 합니다.", ["V32-REG-DL60"])
VI_45 = answer("answered", "Nghệ sĩ V-3-2 phải đăng ký người nước ngoài trong vòng 60 ngày kể từ ngày nhập cảnh.", ["V32-REG-DL60"])


def run(cid, replies):
    """Run a 005-O case with scripted replies; returns the record and the items the model received."""
    case, seen = CASES[cid], []

    def generate(item):
        seen.append(item)
        return replies(item, len(seen)) if callable(replies) else replies[len(seen) - 1]
    record = guard.run_case(case["question"], case["intake"], case["evidence"], gate11.registry_for(case, "acceptance"),
                            case.get("as_of") or DATE, generate)
    return record, seen


# --- contract v12 ---------------------------------------------------------------------------------
def test_v12_adds_only_the_input_name_and_the_retry_line():
    assert "v12" in CONTRACT_VERSIONS and guard.CONTRACT_VERSION in ("v12", "v13", "v14", "v15", "v16")   # 005-R: v13, 005-T: v14, 005-U: v15, 005-V: v16
    v11, v12 = SYSTEM_PROMPTS["v11"].splitlines(), SYSTEM_PROMPTS["v12"].splitlines()
    assert len(v12) == len(v11) + 1
    added = [line for line in v12 if line not in v11]
    assert len(added) == 2 and "language_retry" in added[0] and added[1].startswith("If language_retry is given")
    assert parse_response(VI_45, {"V32-REG-DL60"}, "v12")["status"] == "answered"


def test_language_retry_is_an_allowlisted_one_line_v12_input():
    item = {"question": "가상 질문", "evidence": [], "system": {"reply_language": "vi", "uncovered_items": [],
                                                              "language_retry": guard.LANGUAGE_RETRY["vi"]}}
    assert project_inference_item(item)["system"]["language_retry"] == guard.LANGUAGE_RETRY["vi"]
    payload = json.loads(build_messages(item, "v12")[1]["content"])
    assert list(payload) == ["question", "reply_language", "uncovered_items", "language_retry", "evidence"]
    with pytest.raises(ValueError, match="v12"):
        build_messages(item, "v11")
    with pytest.raises(ValueError):
        project_inference_item({**item, "system": {**item["system"], "language_retry": "a\nb"}})


# --- the retry --------------------------------------------------------------------------------------
def test_a_korean_answer_to_a_vietnamese_question_is_asked_once_more_and_the_retry_is_released():
    record, seen = run("A05O-45", [KO_45, VI_45])
    assert len(seen) == 2 and "language_retry" not in seen[0]["system"]
    assert seen[1]["system"]["language_retry"] == guard.LANGUAGE_RETRY["vi"]
    assert {k: v for k, v in seen[1]["system"].items() if k != "language_retry"} == seen[0]["system"]
    assert record["raw_output"] == KO_45 and record["guard"]["decision"] == "review_required"
    assert record["language_retry"]["parts"] == [0] and record["language_retry"]["raw_output"] == VI_45
    assert record["released_provenance"] == "model_generated" and record["released"]["answer"].startswith("Nghệ sĩ")
    assert len(record["model_input_sha256s"]) == 2


def test_a_second_wrong_language_is_held_back_and_there_is_no_third_call():
    record, seen = run("A05O-45", [KO_45, KO_45])
    assert len(seen) == 2 and record["released_provenance"] == "review_required"
    assert record["language_retry"]["guard"]["decision"] == "review_required"


def test_an_answer_in_the_right_language_is_not_asked_again():
    record, seen = run("A05O-45", [VI_45])
    assert len(seen) == 1 and record["language_retry"] is None and record["released_provenance"] == "model_generated"


def test_other_findings_are_not_retried():
    wrong_value = answer("answered", "V-3-2 체류자는 입국한 날부터 90일 이내에 외국인등록을 하여야 합니다.", ["V32-REG-DL60"])
    record, seen = run("A05O-45", [wrong_value])
    assert len(seen) == 1 and record["language_retry"] is None
    assert record["released_provenance"] == "post_generation_blocked"


def test_a_retried_answer_is_guarded_from_scratch():
    wrong_value_vi = answer("answered", "Nghệ sĩ V-3-2 phải đăng ký trong vòng 90 ngày kể từ ngày nhập cảnh.", ["V32-REG-DL60"])
    record, seen = run("A05O-45", [KO_45, wrong_value_vi])
    assert len(seen) == 2 and record["released_provenance"] == "post_generation_blocked"


def test_only_the_part_held_back_for_language_is_asked_again():
    values = {"V-3-1": ("6", "V31-REE-PROC6"), "V-3-2": ("9", "V32-REE-PROC9"), "V-3-4": ("3", "V34-REE-PROC3S")}

    def replies(item, n):
        code = item["system"]["scope_status_code"]
        days, cite = values[code]
        if code == "V-3-2" and "language_retry" not in item["system"]:
            return answer("answered", f"{code} 체류자의 재입국허가는 신청일부터 {days}일 이내에 처리합니다.", [cite])
        return answer("answered", f"For {code}, a re-entry permit is processed within {days} days of the application.", [cite])
    record, seen = run("A05O-79", replies)
    codes = [i["system"]["scope_status_code"] for i in seen]
    assert codes == ["V-3-1", "V-3-2", "V-3-4", "V-3-2"] and "language_retry" in seen[3]["system"]
    assert record["language_retry"]["parts"] == [1] and record["released_provenance"] == "model_generated"
    assert record["released"]["answer"].splitlines()[1].startswith("For V-3-2")
    assert json.loads(record["raw_output"])["answer"].splitlines()[1].startswith("V-3-2 체류자의")


# --- gate v11 ---------------------------------------------------------------------------------------
def test_gate_v11_scores_the_first_answer_raw_and_the_released_retry_end_to_end():
    record, _ = run("A05O-45", [KO_45, VI_45])
    row = gate11.score_case(CASES["A05O-45"], record)
    assert row["raw"]["outcome"] == "fail" and row["raw"]["checks"]["language"] == "fail"
    assert row["end_to_end"]["correct"] is True and row["end_to_end"]["language_retry"] is True
    assert row["end_to_end"]["retry_outcome"] == "pass" and row["end_to_end"]["critical"] == []
    assert gate10.score_case(CASES["A05O-45"], record)["end_to_end"]["correct"] is False   # v10 read the first answer


def test_gate_v11_replays_the_retry_from_recorded_parts(tmp_path):
    """score_dir re-runs the pipeline from generations.jsonl; the retry is the next recorded part."""
    record, seen = run("A05O-45", [KO_45, VI_45])
    gens = [{"case_id": "A05O-45", "part": i, "raw_output": r} for i, r in enumerate([KO_45, VI_45])]
    records = gate11.recompute_records([CASES["A05O-45"]], {"A05O-45": gens}, DATE, "acceptance")
    assert records["A05O-45"]["released"] == record["released"]
    assert records["A05O-45"]["model_input_sha256s"] == [guard._input_sha(i) for i in seen]
