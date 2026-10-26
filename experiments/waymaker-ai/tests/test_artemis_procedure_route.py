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
