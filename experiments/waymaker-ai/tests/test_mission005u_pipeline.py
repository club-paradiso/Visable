"""Mission 005-U: the first model call names the records in conflict (conflict_records, contract v15).

In 005-T five of the six conflict cases that ask what each record says got status answered on the first
call (A05T-28/29/30/44/67); the status retry corrected every one, but the raw channel scores the first
answer. Two records that differ only in their numbers are visible before inference, so the pipeline now
hands their IDs to the model on the first call. The status retry stays as a second line. Fictional
fixtures, plus the suites and recorded answers of earlier runs.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import dev20_v2
import grounding_guard as guard
import synthetic_safety_gate_v16 as gate16
from gemma4_runtime import build_messages
from waymaker_ai.evidence_registry import load_real_world_registry
from waymaker_ai.inference_input import project_inference_item
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS

N = {"id": "N-1", "text": "[가상 고시 제3호] Y-3-1 체류자의 외국인등록 수수료는 35,000원이다."}
M = {"id": "M-1", "text": "[가상 편람] Y-3-1 체류자의 외국인등록 수수료는 72,000원이다."}


def test_records_that_differ_only_in_their_numbers_are_named():
    assert guard.conflict_records([N, M]) == [["N-1", "M-1"]]
    assert guard.conflict_records([M, N]) == [["M-1", "N-1"]]


@pytest.mark.parametrize("text", [
    "[가상 편람] Y-3-2 체류자의 외국인등록 수수료는 72,000원이다.",         # another sub-code
    "[가상 편람] Y-3-1 체류자의 체류기간 연장 수수료는 72,000원이다.",        # another procedure
    "[가상 편람] Y-3-1 체류자의 외국인등록 수수료는 35,000원이다.",          # the same value
])
def test_records_that_differ_in_more_than_numbers_are_not(text):
    assert guard.conflict_records([N, {"id": "X-1", "text": text}]) == []


def test_v15_adds_only_the_input_name_and_the_conflict_records_line():
    assert "v15" in CONTRACT_VERSIONS and guard.CONTRACT_VERSION in ("v15", "v16")   # 005-V: v16
    v14, v15 = SYSTEM_PROMPTS["v14"].splitlines(), SYSTEM_PROMPTS["v15"].splitlines()
    assert len(v15) == len(v14) + 1
    added = [line for line in v15 if line not in v14]
    assert len(added) == 2 and "conflict_records" in added[0] and added[1].startswith("If conflict_records is given")
    assert "use status conflict" in added[1]


def test_conflict_records_is_an_allowlisted_v15_input_of_this_item_only():
    item = {"question": "가상 질문", "evidence": [N, M],
            "system": {"reply_language": "ko", "uncovered_items": [], "conflict_records": [["N-1", "M-1"]]}}
    assert project_inference_item(item)["system"]["conflict_records"] == [["N-1", "M-1"]]
    assert list(json.loads(build_messages(item, "v15")[1]["content"])) == [
        "question", "reply_language", "uncovered_items", "conflict_records", "evidence"]
    with pytest.raises(ValueError, match=r"v15\+? input"):
        build_messages(item, "v14")
    for bad in ([["N-1", "Z-9"]], [["N-1", "N-1"]], [["N-1"]], [], "N-1, M-1"):
        with pytest.raises(ValueError, match="conflict_records"):
            project_inference_item({**item, "system": {**item["system"], "conflict_records": bad}})


def _suite(mission):
    return {c["id"]: c for c in json.loads((BOOT / "validation" / f"mission005{mission}_synthetic_acceptance.json").read_text())["cases"]}


def test_the_recorded_005t_case_28_now_carries_the_mark_on_the_first_call():
    case = _suite("t")["A05T-28"]
    prepared = guard.prepare(case["question"], case["intake"], case["evidence"], gate16.registry_for(case, "acceptance"), "2026-11-02")
    system = prepared["model_item"]["system"]
    assert system["conflict_records"] == [["J73-REG-FEE-N", "J73-REG-FEE-M"]]
    payload = json.loads(build_messages(prepared["model_item"], guard.CONTRACT_VERSION)[1]["content"])
    assert payload["conflict_records"] == [["J73-REG-FEE-N", "J73-REG-FEE-M"]]


def test_across_earlier_suites_the_mark_falls_only_on_expected_conflicts():
    marked, missed = [], []
    for path in sorted(BOOT.glob("validation/mission005*_synthetic_acceptance.json")):
        mission = path.name[len("mission005")]
        if mission >= "u":
            continue
        for cid, case in _suite(mission).items():
            prepared = guard.prepare(case["question"], case.get("intake"), case["evidence"],
                                     gate16.registry_for(case, "acceptance"), case.get("as_of") or "2026-11-02")
            if any("conflict_records" in item["system"] for item in prepared["model_items"]):
                marked.append(cid)
                assert "conflict" in case["expected"]["model_statuses"], cid
    assert len(marked) == 33
    assert [c for c in marked if c.startswith("A05T")] == [
        "A05T-28", "A05T-29", "A05T-30", "A05T-44", "A05T-56", "A05T-59", "A05T-67"]


def test_no_dev20_v2_item_is_marked():
    registry = load_real_world_registry(dev20_v2.REGISTRY_V2)
    items, _ = dev20_v2.load_items()
    for it in items:
        prepared = guard.prepare(it["question"], None, it["evidence"], registry, "2026-11-02")
        assert not any("conflict_records" in m["system"] for m in prepared["model_items"]), it["id"]


def _recorded_005t(cid):
    rows = [json.loads(l) for l in (BOOT / "runs" / "mission005t" / "synthetic_acceptance" / "pipeline.jsonl").read_text().splitlines()]
    return _suite("t")[cid], {r["case_id"]: r for r in rows}[cid]


def _run(case, outputs):
    seen, outs = [], list(outputs)

    def generate(item):
        seen.append(item)
        build_messages(item, guard.CONTRACT_VERSION)
        return outs.pop(0)
    record = guard.run_case(case["question"], case["intake"], case["evidence"], gate16.registry_for(case, "acceptance"),
                            "2026-11-02", generate)
    return record, seen


def test_the_status_retry_is_still_the_second_line():
    case, rec = _recorded_005t("A05T-28")
    record, seen = _run(case, [rec["raw_output"], rec["status_retry"]["raw_outputs"][0]])
    assert len(seen) == 2 and "conflict_records" in seen[0]["system"] and "conflict_records" in seen[1]["system"]
    assert "use status conflict" in seen[1]["system"]["status_retry"]
    assert record["released"]["status"] == "conflict"
    row = gate16.score_case(case, record)
    assert row["raw"]["checks"]["status"] is False and row["end_to_end"]["correct"] is True


def test_a_conflict_answer_on_the_first_call_is_not_asked_again():
    case, rec = _recorded_005t("A05T-28")
    record, seen = _run(case, [rec["status_retry"]["raw_outputs"][0]])
    assert len(seen) == 1 and record["status_retry"] is None and record["released"]["status"] == "conflict"
    assert gate16.score_case(case, record)["raw"]["outcome"] == "pass"
