"""Mission 005-D: regressions anchored on the real dev-20 T4 generations, and the evaluator defects they exposed.

The generations are model output from one free Colab T4 session, stored
unmodified. Scores are Development Candidate Diagnostic Performance, never
Official Gold Accuracy. The xfail tests pin evaluator defects found in this run
without changing any expected answer; they turn into failures once fixed so the
fix gets reviewed.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import artemis_eval
import score_dev20
import trust_gate
from gemma4_runtime import build_messages

RUN = BOOT / "runs" / "mission005d-dev20"
ITEMS = {i["id"]: i for i in json.loads((BOOT / "benchmarks" / "artemis_eval_dev_20.json").read_text())["items"]}


def generations():
    return {g["case_id"]: g for g in score_dev20.read_jsonl(RUN / "generations.jsonl")}


def trusted_text(case_id):
    return "\n".join(f"{e['title']}\n{e['text']}" for e in ITEMS[case_id]["evidence"]
                     if e["source"]["approval_state"] in ("approved", "under_review"))


def test_raw_generations_are_the_unmodified_colab_files():
    assert hashlib.sha256((RUN / "generations.jsonl").read_bytes()).hexdigest() == \
        "f9a319848946da108f0b85b0d0da344a73193340822d07b14daf9c71f1238949"
    assert hashlib.sha256((RUN / "sessions.jsonl").read_bytes()).hexdigest() == \
        "ed0d87dbd0cb4ef158b52abe6d8e0d68f875a46a4858b3f687022bd6140ef797"


def test_twenty_real_generations_from_one_verified_session():
    gens = generations()
    assert sorted(gens) == sorted(ITEMS) and {g["session_id"] for g in gens.values()} == {"colab-t4-90759d24"}
    sessions = score_dev20.read_jsonl(RUN / "sessions.jsonl")
    assert len(sessions) == 1 and sessions[0]["load"]["quantization"]["quantized_decoder_layers"] == 42
    assert sessions[0]["code"]["git_commit"] == "6dfe161165852922db592e6a1a76578c07e7fada"


def test_scoring_the_real_run_reproduces_the_committed_artifacts():
    result = score_dev20.score(RUN)
    assert result["integrity"]["passed"] is True
    committed = json.loads((RUN / "performance_metrics.json").read_text())
    assert result["metrics"] == committed
    assert result["metrics"]["official_gold_accuracy"] is None
    assert result["metrics"]["executed_cases"]["numerator"] == 20


def test_every_case_has_an_analyst_root_cause():
    annotations = json.loads((RUN / "root_cause_annotations.json").read_text())
    assert set(ITEMS) <= set(annotations)


# --- evaluator defects found in this run (expected answers untouched) --------

@pytest.mark.xfail(strict=True, reason="E1: permission_flips flags '엄격히 금지됩니다' though the evidence also prohibits")
def test_e1_prohibition_restated_is_not_a_permission_flip():
    answer = generations()["ARTEMIS-004-DEV-009"]["response"]["answer"]
    assert trust_gate.permission_flips(answer, trusted_text("ARTEMIS-004-DEV-009")) == []


@pytest.mark.xfail(strict=True, reason="E2: role_mismatches reads '재발급' in evidence as role 'issue' against '제출'")
def test_e2_submitting_a_photo_for_reissue_is_not_a_role_swap():
    answer = generations()["ARTEMIS-004-DEV-020"]["response"]["answer"]
    assert trust_gate.role_mismatches(answer, trusted_text("ARTEMIS-004-DEV-020")) == []


@pytest.mark.xfail(strict=True, reason="E3: required_facts are exact substrings; an inserted adverb fails them")
def test_e3_required_fact_survives_an_inserted_adverb():
    item = ITEMS["ARTEMIS-004-DEV-007"]
    answer = generations()["ARTEMIS-004-DEV-007"]["response"]["answer"]
    assert "2,000명 쿼터 기준은 완전히 폐기" in answer
    score = artemis_eval.score_source_fidelity(item, {"status": "answered", "answer": answer, "citations": []},
                                               allow_candidate_sources=True)
    assert not any(f.startswith("required_fact_missing") for f in score.failures)


def test_e4_language_instruction_contradicts_an_english_rubric():
    """Not xfail: documents a contract conflict to resolve in 005-E, not a scoring bug."""
    system = build_messages({"question": "", "evidence": []})[0]["content"]
    facts = ITEMS["ARTEMIS-004-DEV-011"]["expected"]["source_fidelity"]["required_facts"]
    assert "in Korean" in system and all(f.isascii() for f in facts)
