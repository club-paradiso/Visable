"""Stage 2 approval ledger: real manual pages, hashed per page, resolved into evidence.

The ledger test is a deliberate tripwire: if the corpus text of an approved
2026.10 manual page changes, ``verify`` lists it and this test fails until the
ledger is rebuilt on purpose (``python manual_ledger.py build``).
"""
from __future__ import annotations

import importlib.util
import json
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


ml = load_module("manual_ledger")
tg = load_module("trust_gate")
LEDGER = ml.load_ledger()


def test_ledger_covers_both_approved_editions_and_still_matches_the_corpus():
    sources = {r["source_id"] for r in LEDGER.values()}
    assert sources == set(ml.SOURCE_IDS)
    assert len(LEDGER) == 519 + 812
    assert ml.verify() == []


def test_sources_are_approved_and_their_files_match_the_approval_record():
    for s in ml.approved_sources():
        assert s["approval_state"] == "approved" and len(s["sha256"]) == 64


def test_a_resolved_page_passes_the_gate_and_integrity():
    item = ml.resolve_evidence({"id": "visa_manual_2026_10_19_pdf#p43",
                                "source_id": "visa_manual_2026_10_19_pdf", "page": 43}, LEDGER)
    assert item["source"]["domain"] == "visa_issuance" and "C-3-4" in item["text"]
    assert tg.is_trusted(item, integrity=True)
    tampered = {**item, "text": item["text"].replace("90일", "180일")}
    assert not tg.is_trusted(tampered, integrity=True)


def test_a_page_missing_from_the_ledger_is_not_approved():
    item = ml.resolve_evidence({"id": "visa_manual_2026_10_19_pdf#p43",
                                "source_id": "visa_manual_2026_10_19_pdf", "page": 43}, {})
    assert item["source"]["approval_state"] == "needs_review" and not tg.is_trusted(item)


@pytest.mark.parametrize("path", sorted(p for p in BOOTSTRAP_DIR.glob("*_cases.json")
                                        if any("text" not in e for c in json.loads(p.read_text(encoding="utf-8"))["cases"]
                                               for e in c["evidence"])), ids=lambda p: p.name)
def test_real_manual_case_files_resolve_and_quote_their_pages(path):
    cases = ml.resolve_cases(json.loads(path.read_text(encoding="utf-8"))["cases"])
    for case in cases:
        ev = {e["id"]: e for e in case["evidence"]}
        assert all(tg.is_trusted(e, integrity=True) for e in ev.values()), case["id"]
        cited = " ".join(ev[i]["text"] for i in case["expect"].get("must_cite", []))
        for needle in case["expect"].get("answer_must_contain", []):
            assert needle in cited, (case["id"], needle)
        for group in case["expect"].get("answer_must_contain_any_of_each", []):
            assert any(n in cited for n in group), (case["id"], group)
