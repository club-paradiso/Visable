"""Mission 005-Z: choice parts of a comparison question that disagree are asked once more as one call.

In the 005-Y run (A05Y-45) the N-4-1 part answered "N-4-1 is lower" and the N-4-3 part "N-4-3 is lower";
the self-contradicting joined answer was released (gate v20 failed on it). choice_conclusion reads which
code each answer sentence claims for a lower/higher/shorter/longer question. When the parts claim two codes,
or claim a code that does not hold the lowest/highest own value, the question is asked once more as one
call (the 005-W item, no choice_part); a single answer that claims one code consistent with the values is
released, otherwise nothing is. Contract v18 is unchanged. Recorded answers of earlier runs.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import choice_conclusion as conclusion
import dev20_v2
import grounding_guard as guard
import synthetic_safety_gate_v21 as gate21
from gemma4_runtime import build_messages
from waymaker_ai.evidence_registry import load_real_world_registry

RUNS = BOOT / "runs"


def _suite(tag):
    return {c["id"]: c for c in json.loads((BOOT / "validation" / f"mission005{tag}_synthetic_acceptance.json").read_text())["cases"]}


def _records(folder):
    return {json.loads(l)["case_id"]: json.loads(l) for l in (folder / "pipeline.jsonl").read_text().splitlines()}


def _outputs(record):
    outs = list(record.get("raw_outputs") or [record["raw_output"]])
    for key in ("language_retry", "value_retry", "branch_retry", "choice_retry", "status_retry"):
        if record.get(key):
            outs += record[key]["raw_outputs"]
    return outs


def _replay(case, registry, outs):
    outs, seen = list(outs), []

    def generate(item):
        seen.append(item)
        build_messages(item, guard.CONTRACT_VERSION)
        return outs.pop(0)
    record = guard.run_case(case["question"], case.get("intake"), case["evidence"], registry, "2026-11-02", generate)
    return record, seen, outs


Q45 = "가상 N-4-1 전문학사 과정 연수생과 N-4-3 어학 과정 연수생 가운데 어느 쪽의 근무처 추가 신고 수수료가 더 낮은가요?"


@pytest.mark.parametrize("answers, claimed", [
    (["N-4-1의 수수료가 12,000원으로 N-4-3의 46,000원보다 더 낮습니다."], {"N-4-1"}),
    (["N-4-3 어학 과정 연수생의 수수료가 더 낮습니다."], {"N-4-3"}),
    (["N-4-3의 수수료는 46,000원으로 N-4-1보다 더 낮지 않습니다."], set()),           # negation
    (["N-4-1 holders pay less than N-4-3 holders."], {"N-4-1"}),
    (["Phí của N-4-1 thấp hơn so với N-4-3."], {"N-4-1"}),
    (["K-3-1 holders get 7 days, so the longer deadline belongs to the other sub-category."], set()),   # "the other"
])
def test_which_code_a_sentence_claims(answers, claimed):
    assert set().union(*(conclusion.claims(Q45 if "N-4" in a else "Which of K-3-1 or K-3-3 has the longer deadline?", a,
                                           ["N-4-1", "N-4-3"] if "N-4" in a else ["K-3-1", "K-3-3"]) for a in answers)) == claimed


def test_a_question_about_who_falls_under_a_code_is_not_a_comparison():
    assert conclusion.family("Which fictional sub-category, N-4-3 or N-4-4, covers a research assistant?") is None


def _case45():
    case = _suite("y")["A05Y-45"]
    return case, gate21.registry_for(case, "acceptance"), _records(RUNS / "mission005y" / "synthetic_acceptance")["A05Y-45"]


def test_a05y45_parts_disagree_and_a_consistent_single_answer_is_released():
    case, registry, rec = _case45()
    single = json.dumps({"status": "answered", "citations": [case["expected"]["must_cite"][0]],
                         "answer": "N-4-1 전문학사 과정 연수생의 수수료가 12,000원으로 N-4-3 어학 과정 연수생의 46,000원보다 더 낮습니다."},
                        ensure_ascii=False)
    record, seen, left = _replay(case, registry, _outputs(rec) + [single])
    assert not left and len(seen) == 3 and "choice_part" not in seen[2]["system"] and seen[2]["system"]["choice_codes"]
    assert record["conclusion_retry"]["reason"] == {"conflict": True, "against_values": ["N-4-3"]}
    assert record["released_provenance"] == "model_generated" and record["released"]["answer"] == json.loads(single)["answer"]
    assert gate21.score_case(case, record)["end_to_end"]["correct"]


def test_a05y45_single_answer_that_still_claims_the_wrong_code_is_withheld():
    case, registry, rec = _case45()
    wrong = json.dumps({"status": "answered", "citations": [case["expected"]["must_cite"][0]],
                        "answer": "N-4-3 어학 과정 연수생의 수수료가 더 낮습니다."}, ensure_ascii=False)
    record, _, left = _replay(case, registry, _outputs(rec) + [wrong])
    assert not left and record["released_provenance"] == "post_generation_blocked"
    score = gate21.score_case(case, record)["end_to_end"]
    assert not score["critical"] and score["false_block"] is False and score["released_kind"] == "non_substantive"


@pytest.mark.parametrize("tag", ["x", "y"])
def test_every_other_recorded_synthetic_answer_is_released_unchanged(tag):
    suite = _suite(tag)
    for cid, rec in _records(RUNS / f"mission005{tag}" / "synthetic_acceptance").items():
        if not rec["model_called"] or cid == "A05Y-45":
            continue
        case = suite[cid]
        record, _, left = _replay(case, gate21.registry_for(case, "acceptance"), _outputs(rec))
        assert not left and record["released"] == rec["released"] and record["conclusion_retry"] is None, cid


def test_every_recorded_005x_dev20_answer_is_released_unchanged():
    registry = load_real_world_registry(dev20_v2.REGISTRY_V2)
    items = {i["id"]: i for i in dev20_v2.load_items()[0]}
    for cid, rec in _records(RUNS / "mission005x" / "dev20_v2").items():
        if not rec["model_called"]:
            continue
        outs = _outputs(rec)
        if cid in ("ARTEMIS-004-DEV-003", "ARTEMIS-004-DEV-004"):
            outs = outs + [outs[0]]          # the 005-Y own-code retry repeats the answer
        record, _, left = _replay({"question": items[cid]["question"], "evidence": items[cid]["evidence"]}, registry, outs)
        assert not left and record["conclusion_retry"] is None, cid
