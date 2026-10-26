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
