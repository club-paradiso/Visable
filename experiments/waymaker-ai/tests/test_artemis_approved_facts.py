"""Approved-facts pilot: candidates come from the pilot pages and are never trusted as
facts; export writes only reviewed facts whose quote, page hash and value still check
out. Nothing here checks legal correctness."""
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


af = load_module("approved_facts")
CANDIDATES = af.load_candidates()


def test_candidate_file_is_a_fresh_extraction_of_the_pilot_pages():
    assert af.check()
    pages = af.pilot_pages()
    assert len(pages) == 180
    assert {c["source"]["page_id"] for c in CANDIDATES} <= set(pages)


def test_every_candidate_quotes_its_page_and_is_marked_as_a_candidate():
    pages = af.pilot_pages()
    ledger = af.manual_ledger.load_ledger()
    for c in CANDIDATES:
        assert c["status"] == "candidate"
        assert c["source"]["quote"] in pages[c["source"]["page_id"]]["text"]
        assert c["source"]["page_approval_hash"] == ledger[c["source"]["page_id"]]["approved_sha256"]
        assert c["role"] in (None, *af.ROLES)
        assert not (c["value"]["kind"] == "period" and c["value"]["unit"] == "year" and c["value"]["amount"] >= 100)


def test_post_check_never_reads_candidates():
    source = (BOOTSTRAP_DIR / "trust_gate.py").read_text(encoding="utf-8")
    assert "fact_candidates" not in source and "approved_facts" not in source


def _review(tmp_path: Path, rows):
    folder = tmp_path / "facts_review"
    folder.mkdir(parents=True)
    for row in rows:
        (folder / f"{row['candidate_id']}.json").write_text(json.dumps({"data": row}, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def _approved(candidate, **change):
    row = {"candidate_id": candidate["candidate_id"], "decision": "approved", "subject": candidate["subject"],
           "role": candidate["role"] or "other", "value": candidate["value"], "source": candidate["source"],
           "note": "", "reviewer": "u_test", "updated_at": "2026-10-28T00:00:00Z"}
    row.update(change)
    return row


@pytest.fixture
def ledger_path(tmp_path, monkeypatch):
    path = tmp_path / "facts.jsonl"
    monkeypatch.setattr(af, "FACTS", path)
    return path


def test_export_writes_only_approved_and_rechecked_facts(tmp_path, ledger_path):
    money = next(c for c in CANDIDATES if c["value"]["kind"] == "money" and c["role"])
    period = next(c for c in CANDIDATES if c["value"]["kind"] == "period" and c["role"])
    held = next(c for c in CANDIDATES if c not in (money, period))
    review = _review(tmp_path / "r", [_approved(money), _approved(period, decision="approved_edited", role="validity"),
                                       {**_approved(held), "decision": "held"}])
    result = af.export(review)
    assert result == {"written": 2, "rejected": []}
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()[1:]]
    assert {r["fact_id"] for r in rows} == {money["candidate_id"].replace("fc-", "f-"), period["candidate_id"].replace("fc-", "f-")}
    assert all(r["status"] == "approved" and r["review"]["by"] == "u_test" for r in rows)
    # Exporting the same decisions again writes nothing new.
    assert af.export(review)["written"] == 0


@pytest.mark.parametrize("tamper, problem", [
    (lambda r: r["source"].update(quote=r["source"]["quote"] + " 그리고 다른 말"), "quote is not on the page"),
    (lambda r: r["source"].update(page_approval_hash="0" * 64), "fact names a different page hash than the ledger"),
    (lambda r: r["value"].update(amount=r["value"]["amount"] * 1000 + 7), "value is not in the quote"),
    (lambda r: r.update(role="not-a-role"), "role 'not-a-role' is not in the role list"),
    (lambda r: r["subject"].update(procedure="abroad"), "subject.procedure must be visa or stay"),
])
def test_export_refuses_facts_that_do_not_check_out(tmp_path, ledger_path, tamper, problem):
    candidate = next(c for c in CANDIDATES if c["role"])
    row = json.loads(json.dumps(_approved(candidate)))
    tamper(row)
    result = af.export(_review(tmp_path / "r", [row]))
    assert result["written"] == 0 and problem in result["rejected"][0]["problems"]
    assert not ledger_path.exists()


def test_ai_first_pass_is_an_opinion_on_every_candidate_and_passes_the_export_checks():
    data = json.loads(af.AI_FIRST_PASS.read_text(encoding="utf-8"))
    assert "not a human review" in data["reviewer"] and "not an approval" in data["reviewer"]
    ops = data["opinions"]
    assert [o["candidate_id"] for o in ops] == [c["candidate_id"] for c in CANDIDATES]
    pages, ledger = af.pilot_pages(), af.manual_ledger.load_ledger()
    by_id = {c["candidate_id"]: c for c in CANDIDATES}
    for o in ops:
        assert o["ai_decision"] in ("approve", "reject", "hold")
        if o["ai_decision"] != "reject":
            fact = {"subject": o["subject"], "role": o["role"], "value": o["value"], "source": by_id[o["candidate_id"]]["source"]}
            assert af._verify(fact, pages, ledger) == [], o["candidate_id"]


def test_export_ignores_ai_opinions(tmp_path, ledger_path):
    """Only human decisions in facts_review reach the ledger; the AI file is never read by export."""
    assert "AI_FIRST_PASS" not in af.export.__code__.co_names
    result = af.export(_review(tmp_path / "r", []))
    assert result == {"written": 0, "rejected": []} and not ledger_path.exists()
