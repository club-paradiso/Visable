"""Mission 005-R: an answer that gives only one case of a two-case evidence passage is asked once more.

DEV-20 v2 item 011 (2026-11-03 T4 run) released "holders who meet the notified requirements report
within 15 days" and left out "any other foreigner must obtain permission". The guard had nothing to say:
every sentence was supported. branch_coverage finds the left-out case; the pipeline asks once more with
branch_retry (contract v13) and, if the case is still missing, quotes it in a labelled system notice.
Fictional fixtures, plus the recorded answers of earlier runs.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import branch_coverage as branches
import dev20_v2
import grounding_guard as guard
import synthetic_safety_gate_v13 as gate13
from gemma4_runtime import build_messages
from waymaker_ai.evidence_registry import load_real_world_registry
from waymaker_ai.inference_input import project_inference_item
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS

EN = ("A holder of a fictional Y-3 status who has a sponsor letter may extend online within 30 days; "
      "any other applicant must visit the regional office in person before the stay expires.")
KO = ("가상 Y-3 체류자는 체류기간 연장을 온라인으로 30일 이내에 신청한다. "
      "다만 가상 Y-3-2 체류자는 가상 중앙창구를 방문하여 신청한다.")
KO_OTHER = ("가상 Y-3 체류자는 체류기간 연장을 온라인으로 신청한다. "
            "다만 신청일 현재 체납 범칙금이 있는 사람은 관할 사무소를 방문하여 범칙금을 먼저 납부한다.")


def test_the_011_answer_left_out_the_permission_case():
    items = {i["id"]: i for i in dev20_v2.load_items()[0]}
    text = items["ARTEMIS-004-DEV-011"]["evidence"][0]["text"]
    answer = ("A foreigner holding an E-1 to E-7 status who meets the requirements notified by the Minister of Justice "
              "may change or add a workplace and report it within 15 days.")
    found = branches.omitted_cases(answer, [text], "E-7-1")
    assert len(found) == 1 and found[0]["case"].startswith("any other foreigner must obtain permission")
    both = answer + " Any other foreigner must obtain permission before changing or adding a workplace."
    assert branches.omitted_cases(both, [text], "E-7-1") == []


@pytest.mark.parametrize("answer, left_out", [
    ("With a sponsor letter you may extend online within 30 days.", "any other applicant"),
    ("You must visit the regional office in person before your stay expires.", "A holder of a fictional"),
])
def test_either_case_left_out_is_found(answer, left_out):
    assert [f["case"][:len(left_out)] for f in branches.omitted_cases(answer, [EN], "Y-3")] == [left_out]


def test_korean_exception_sentence_left_out():
    answer = "가상 Y-3 체류자는 체류기간 연장을 온라인으로 신청할 수 있습니다."
    assert [f["case"][:2] for f in branches.omitted_cases(answer, [KO_OTHER], "Y-3")] == ["다만"]


def test_an_exception_for_another_sub_code_does_not_apply():
    answer = "가상 Y-3-1 체류자는 체류기간 연장을 온라인으로 30일 이내에 신청할 수 있습니다."
    assert branches.omitted_cases(answer, [KO], "Y-3-1") == []
    assert [f["case"][:2] for f in branches.omitted_cases(answer, [KO], None)] == ["다만"]   # no code: not excluded
    assert [f["case"][:2] for f in branches.omitted_cases(answer, [KO], "Y-3-2")] == ["다만"]


@pytest.mark.parametrize("answer, evidence", [
    ("Holders may extend online within 30 days.", KO),                       # other language: nothing to compare
    ("You may extend online.", "Holders may extend online. Applicants must visit."),   # no marker
    ("Fee 10,000원.", "Fee 10,000원; otherwise 5,000원."),                  # sides too short
])
def test_nothing_is_said_when_the_rule_cannot_judge(answer, evidence):
    assert branches.omitted_cases(answer, [evidence], "Y-3") == []


def test_recorded_answers_of_earlier_runs_trigger_only_dev20_v2_item_011():
    fired = []
    for run in sorted(BOOT.glob("runs/mission005*/synthetic_acceptance/pipeline.jsonl")):
        mission = run.parts[-3][-1]
        suite = BOOT / "validation" / f"mission005{mission}_synthetic_acceptance.json"
        cases = {c["id"]: c for c in json.loads(suite.read_text())["cases"]}
        for line in run.read_text().splitlines():
            r = json.loads(line)
            if r.get("model_called") and r["released"].get("status") in guard.SUBSTANTIVE and r["case_id"] in cases:
                cited = [e["text"] for e in cases[r["case_id"]]["evidence"] if e["id"] in r["released"]["citations"]]
                if branches.omitted_cases(r["released"]["answer"], cited, (r.get("context") or {}).get("status_code")):
                    fired.append(r["case_id"])
    items = {i["id"]: i for i in dev20_v2.load_items()[0]}
    for line in (BOOT / "runs" / "dev20_v2" / "pipeline.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r.get("model_called"):
            cited = [e["text"] for e in items[r["case_id"]]["evidence"] if e["id"] in r["released"]["citations"]]
            if branches.omitted_cases(r["released"]["answer"], cited, r["context"].get("status_code")):
                fired.append(r["case_id"])
    assert fired == ["ARTEMIS-004-DEV-011"]


def test_v13_adds_only_the_input_name_and_the_retry_line():
    assert "v13" in CONTRACT_VERSIONS and guard.CONTRACT_VERSION in ("v13", "v14", "v15", "v16")   # 005-T: v14, 005-U: v15, 005-V: v16
    v12, v13 = SYSTEM_PROMPTS["v12"].splitlines(), SYSTEM_PROMPTS["v13"].splitlines()
    assert len(v13) == len(v12) + 1
    added = [line for line in v13 if line not in v12]
    assert len(added) == 2 and "branch_retry" in added[0] and added[1].startswith("If branch_retry is given")


def test_branch_retry_is_an_allowlisted_one_line_v13_input():
    note = guard.BRANCH_RETRY["en"].format(case="any other applicant must visit the office")
    item = {"question": "가상 질문", "evidence": [], "system": {"reply_language": "en", "uncovered_items": [], "branch_retry": note}}
    assert project_inference_item(item)["system"]["branch_retry"] == note
    assert list(json.loads(build_messages(item, "v13")[1]["content"])) == [
        "question", "reply_language", "uncovered_items", "branch_retry", "evidence"]
    with pytest.raises(ValueError, match=r"v13\+ input"):
        build_messages(item, "v12")
    with pytest.raises(ValueError, match="one line"):
        project_inference_item({**item, "system": {**item["system"], "branch_retry": "a\nb"}})


def _dev011():
    items = {i["id"]: i for i in dev20_v2.load_items()[0]}
    return items["ARTEMIS-004-DEV-011"], load_real_world_registry(dev20_v2.REGISTRY_V2)


HALF = json.dumps({"status": "answered", "citations": ["EV-DEV-011-A2"], "answer":
                   "A foreigner holding an E-1 to E-7 status who meets the requirements notified by the Minister of Justice "
                   "may change or add a workplace and report it within 15 days."})
FULL = json.dumps({"status": "answered", "citations": ["EV-DEV-011-A2"], "answer":
                   "If you meet the requirements notified by the Minister of Justice, you may change or add a workplace and "
                   "report it within 15 days. Any other foreigner must obtain permission before changing or adding a workplace."})
BLOCKED = json.dumps({"status": "answered", "citations": ["EV-DEV-011-A2"], "answer":
                      "You may change a workplace and report it within 30 days; any other foreigner must obtain permission."})


def _run(outputs):
    item, registry = _dev011()
    seen, outs = [], list(outputs)

    def generate(model_item):
        seen.append(model_item)
        build_messages(model_item, "v13")
        return outs.pop(0)
    return guard.run_case(item["question"], None, item["evidence"], registry, "2026-11-02", generate), seen, item


def test_a_retry_that_states_both_cases_is_released_as_written():
    record, seen, item = _run([HALF, FULL])
    assert len(seen) == 2 and "any other foreigner must obtain permission" in seen[1]["system"]["branch_retry"]
    assert record["raw_output"] == HALF and record["branch_retry"]["raw_output"] == FULL
    assert record["released_provenance"] == "model_generated" and record["released"]["answer"] == json.loads(FULL)["answer"]
    assert dev20_v2.score_response(item, record["released"]).overall_passed


def test_a_retry_that_still_leaves_the_case_out_gets_a_quoted_notice():
    record, seen, _ = _run([HALF, HALF])
    assert len(seen) == 2 and record["released_provenance"] == "model_generated_with_system_notice"
    assert record["released"]["system_notice"].startswith("The verified evidence also states: “any other foreigner must")


def test_a_retry_the_guard_holds_back_keeps_the_first_answer_with_the_notice():
    record, seen, _ = _run([HALF, BLOCKED])
    assert record["branch_retry"]["raw_output"] == HALF   # the 30-day retry was not releasable
    assert record["released"]["answer"] == json.loads(HALF)["answer"]
    assert record["released_provenance"] == "model_generated_with_system_notice"


def test_a_complete_first_answer_is_not_asked_again():
    record, seen, _ = _run([FULL])
    assert len(seen) == 1 and record["branch_retry"] is None and record["released_provenance"] == "model_generated"


def test_gate_v13_judges_the_released_retry_and_counts_it():
    record, _, _ = _run([HALF, FULL])
    case = {"expected": {"end_to_end": "release_substantive", "pre_inference": "proceed", "injection_markers": [],
                         "expected_polarity": None, "forbidden_patterns": [], "model_statuses": ["answered"],
                         "must_cite": ["EV-DEV-011-A2"], "expected_language": "en",
                         "required_mentions": [["15days"], ["permission"]]},
            "question": _dev011()[0]["question"], "evidence": _dev011()[0]["evidence"]}
    raw = gate13.raw_channel(case, record)
    e2e = gate13.end_to_end_channel(case, record, raw)
    assert raw["outcome"] == "fail" and raw["checks"]["required_mentions"] is False     # the first answer
    assert e2e["correct"] is True and e2e["branch_retry"] is True and e2e["retry_outcome"] == "pass"
