"""Stage 2 routing: pages from the other manual never reach the model.

Uses the backend's own procedure detection (manual_evidence, read-only). The
cases here pin the behaviour this experiment relies on, including the
deliberate over-abstention on questions that name no procedure.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

BOOTSTRAP_DIR = Path(__file__).resolve().parents[1] / "artemis_bootstrap"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, BOOTSTRAP_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pr = load_module("procedure_route")


@pytest.mark.parametrize("question, domains", [
    ("E-8 사증발급인정서 처리 기간은 얼마나 걸려요?", {"visa_issuance"}),
    ("D-2 체류기간 연장 신청 서류가 뭐예요?", {"stay"}),
    ("F-6 재입국허가가 면제되나요?", {"stay"}),
    ("How do I extend my stay on D-4?", {"stay"}),
    ("How do I apply for a visa as an E-7 worker?", {"visa_issuance"}),
    ("한국에 더 있으려면 어떻게 해요?", set()),
])
def test_route_follows_the_named_procedure(question, domains):
    assert {d for d, _ in pr.route(question)} == domains


def test_route_gate_keeps_only_the_routed_manual():
    def page(i, domain):
        return {"id": i, "title": "t", "text": "x", "source": {"domain": domain, "approval_state": "approved"}}
    case = {"question": "D-2 체류기간 연장 신청 서류", "evidence": [page("v1", "visa_issuance"), page("s1", "stay")]}
    kept, withheld, scopes = pr.route_gate(case)
    assert [e["id"] for e in kept["evidence"]] == ["s1"] and withheld == ["v1"]
    none = {"question": "한국에 더 있으려면?", "evidence": [page("s1", "stay")]}
    assert pr.route_gate(none)[0]["evidence"] == []


def test_scope_names_are_the_corpus_domains():
    assert (pr.SCOPE_STAY, pr.SCOPE_VISA) == ("stay", "visa_issuance")


def test_clarify_output_is_fixed_and_carries_no_claims():
    tg = load_module("trust_gate")
    out = pr.clarify_output()
    assert out["status"] == "clarify" and out["citations"] == []
    assert tg.extract_claims(out["answer"]) == []
    assert "사증" in out["answer"] and "체류기간 연장" in out["answer"]


def test_a_reply_that_names_the_procedure_routes_the_second_turn():
    q = "가족을 한국으로 데려오려면 어떻게 하나요?"
    assert pr.route(q) == []
    assert {d for d, _ in pr.route(pr.with_reply(q, "아직 해외에 있고 사증발급인정서를 받아야 해요"))} == {"visa_issuance"}
    assert {d for d, _ in pr.route(pr.with_reply(q, "지금 한국에 있고 체류기간을 연장하려고요"))} == {"stay"}


def test_grader_counts_a_clarifying_question_as_its_own_outcome():
    import json
    grader = load_module("smoke_grader")
    case = {"evidence": [{"id": "s1", "title": "t", "text": "x"}],
            "expect": {"status": ["answered"], "must_cite": ["s1"]}}
    g = grader.grade(case, json.dumps(pr.clarify_output(), ensure_ascii=False))
    assert grader.classify(g) == "clarify"
    ok = {"evidence": case["evidence"], "expect": {"status": ["clarify", "insufficient_evidence"]}}
    assert grader.classify(grader.grade(ok, json.dumps(pr.clarify_output(), ensure_ascii=False))) == "correct"


def test_runner_refuses_clarify_without_route(tmp_path):
    runner = load_module("run_smoke")
    with pytest.raises(SystemExit):
        runner.main(["--model", "x/y", "--revision", "0" * 40, "--out", str(tmp_path / "r"), "--clarify"])
    assert not (tmp_path / "r").exists()


def test_clarify_offers_exactly_two_buttons_that_route_exactly():
    out = pr.clarify_output()
    assert [c["id"] for c in out["choices"]] == ["visa_abroad", "stay_in_korea"]
    assert [c["label"] for c in out["choices"]] == ["해외에서 비자 받기", "한국에서 체류 절차"]
    assert pr.route_choice("visa_abroad")[0][0] == "visa_issuance"
    assert pr.route_choice("stay_in_korea")[0][0] == "stay"
    assert pr.route_choice("something_else") == []


def test_gate_to_a_button_route_withholds_the_other_manual():
    def page(i, domain):
        return {"id": i, "title": "t", "text": "x", "source": {"domain": domain}}
    case = {"question": "q", "evidence": [page("v1", "visa_issuance"), page("s1", "stay")]}
    kept, withheld = pr.gate_to(case, pr.route_choice("visa_abroad"))
    assert [e["id"] for e in kept["evidence"]] == ["v1"] and withheld == ["s1"]


def test_runner_always_ask_cannot_be_combined_with_route(tmp_path):
    runner = load_module("run_smoke")
    with pytest.raises(SystemExit):
        runner.main(["--model", "x/y", "--revision", "0" * 40, "--out", str(tmp_path / "r"), "--always-ask", "--route"])
    assert not (tmp_path / "r").exists()


def test_cross_check_disagrees_only_on_a_confident_single_other_manual():
    assert pr.cross_check("D-2 체류기간 연장 서류가 뭐예요?", "visa_abroad")["disagrees"] is True
    assert pr.cross_check("D-2 체류기간 연장 서류가 뭐예요?", "stay_in_korea")["disagrees"] is False
    assert pr.cross_check("한국에 더 있으려면?", "visa_abroad")["disagrees"] is False  # no route: user stands


def test_confirm_and_label_name_both_buttons_and_carry_no_claims():
    tg = load_module("trust_gate")
    c = pr.confirm_output("visa_abroad")
    assert c["status"] == "clarify" and "해외에서 비자 받기" in c["answer"] and "한국에서 체류 절차" in c["answer"]
    assert tg.extract_claims(c["answer"]) == []
    labelled = pr.label_answer({"status": "answered", "answer": "x", "citations": ["p1"]}, "stay_in_korea")
    assert labelled["basis"]["label"] == "한국에서 체류 절차 기준 안내"
    assert labelled["switch"]["id"] == "visa_abroad" and labelled["citations"] == ["p1"]
    assert pr.other_choice("visa_abroad") == "stay_in_korea"


def test_runner_guards_need_always_ask(tmp_path):
    runner = load_module("run_smoke")
    for flag in ("--cross-check", "--label-switch"):
        with pytest.raises(SystemExit):
            runner.main(["--model", "x/y", "--revision", "0" * 40, "--out", str(tmp_path / "r"), flag])
    assert not (tmp_path / "r").exists()


@pytest.mark.parametrize("question, domains", [
    # B-09 / B-12 (real-manual sets): a stay route on "체류기간" or on a code plus "work",
    # for someone abroad.
    ("베트남에 살고 있는데 한국 대학 어학당에서 한국어를 배우고 싶어요. D-4로 가면 체류기간은 얼마나 받을 수 있어요?", {"visa_issuance"}),
    ("I work remotely for a company abroad and I'd like to come to Korea as a digital nomad (F-1-D). What kind of visa would I get?", {"visa_issuance"}),
    # A-17: nothing named, but the person says they are in Korea.
    ("I came to Korea visa-free for a health check-up and the hospital now says I need long-term treatment.", {"stay"}),
    # Not the person's location: the church is in Korea; "stay in Korea on H-2" says nothing.
    ("본국 교단에서 선교사를 한국에 보내려고 하는데, 한국에 있는 개별 교회 담임목사님 이름으로 초청해도 되나요?", set()),
    ("My father is an ethnic Korean from Uzbekistan. How long can he stay in Korea on H-2?", set()),
    # A strong stay word keeps its route whatever the location cue.
    ("한국에 살고 있는데 체류기간 연장허가 수수료가 얼마예요?", {"stay"}),
])
def test_route_reads_where_the_person_is(question, domains):
    assert {d for d, _ in pr.route(question)} == domains
