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


def test_candidate_file_is_an_intact_snapshot_of_the_pilot_pages():
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


# --- AI-confirmed facts (owner-delegated) and the post-check's subject check ------

FACTS = af.load_facts()
tg = sys.modules["trust_gate"]


def test_ai_confirmed_facts_are_marked_delegated_and_pass_the_export_checks():
    final = json.loads((BOOTSTRAP_DIR / "reviews" / "facts_ai_final_2026-10-28.json").read_text(encoding="utf-8"))
    recheck = json.loads(af.STATUTE_RECHECK.read_text(encoding="utf-8"))
    for review in (final, recheck):
        assert "owner-delegated" in review["reviewer"] and "not a human approval" in review["reviewer"]
    confirmed = {d["candidate_id"].replace("fc-", "f-") for r in (final, recheck) for d in r["decisions"] if d["final"] == "confirm"}
    assert {f["fact_id"] for f in FACTS} == confirmed and len(FACTS) == 198
    pages, ledger = af.pilot_pages(), af.manual_ledger.load_ledger()
    for f in FACTS:
        assert f["tier"] == "ai_delegated" and "웬만하면 너가 검토 해" in f["review"]["delegation"]
        assert af._verify(f, pages, ledger) == [], f["fact_id"]
    # The final pass never confirms a "differs". The three it sent to the owner became facts
    # only through the re-check, which names the owner's rule and the decision it replaces.
    differs = {d["candidate_id"] for d in final["decisions"] if (d.get("legal_check") or {}).get("result") == "differs"}
    assert differs and all(d["final"] == "owner" for d in final["decisions"] if d["candidate_id"] in differs)
    assert {d["candidate_id"] for d in recheck["decisions"]} == differs
    assert all("B-16" in d["owner_rule"] and d["supersedes_decision"]["legal_result"] == "differs" for d in recheck["decisions"])


def test_subject_check_marks_a_value_taken_from_another_household():
    def fact(fid, house, amount):
        return {"fact_id": fid, "role": "deposit", "source": {"page_id": "P"},
                "subject": {"status_code": "M-2", "sub_code": None, "procedure": "stay",
                            "qualifiers": {"household_size": house, "row_label": None}},
                "value": {"kind": "money", "amount": amount, "unit": "krw"}}
    facts = [fact("f1", 1, 4000000), fact("f2", 2, 6500000)]
    page = [{"id": "P", "title": "t", "text": "(단위: 원)\n| 가구원 수 | 예치금 |\n|---|---|\n| 1인 | 4,000,000 |\n| 2인 | 6,500,000 |",
             "source": {"approval_state": "approved"}}]
    ask = "M-2 2인 가구 예치금은?"
    wrong = tg.post_check({"status": "answered", "answer": "2인 가구 예치금은 4,000,000원입니다.", "citations": ["P"]}, page, facts=facts, question=ask)
    right = tg.post_check({"status": "answered", "answer": "2인 가구 예치금은 6,500,000원입니다.", "citations": ["P"]}, page, facts=facts, question=ask)
    vague = tg.post_check({"status": "answered", "answer": "예치금은 4,000,000원입니다.", "citations": ["P"]}, page, facts=facts, question="예치금은?")
    assert wrong["verdict"] == "pass" and wrong["subject_mismatches"]          # review, never withheld
    assert not right["subject_mismatches"] and not vague["subject_mismatches"]


def test_subject_check_reads_a_yearly_household_income_row_without_the_word_yearly():
    """F-6 income rows carry per "연간". A question saying only "2인 가구 소득기준" used to
    drop every row, so a 3인 가구 value passed unmarked (found in the premise audit)."""
    def fact(fid, house, amount, per):
        return {"fact_id": fid, "role": "income_threshold", "source": {"page_id": "P"},
                "subject": {"status_code": "F-6", "sub_code": None, "procedure": "visa",
                            "qualifiers": {"household_size": house, "row_label": "소득기준", "per": per}},
                "value": {"kind": "money", "amount": amount, "unit": "krw"}}
    facts = [fact("f2", 2, 32154216, "연간"), fact("f3", 3, 38968428, "연간"), fact("fh", None, 5755188, "가구원 1인당")]
    page = [{"id": "P", "title": "t", "text": "소득기준 32,154,216 38,968,428 / 가구원 1인당 5,755,188", "source": {"approval_state": "approved"}}]
    ask = "F-6 2인 가구 소득기준이 얼마인가요?"
    def marked(answer):
        return tg.post_check({"status": "answered", "answer": answer, "citations": ["P"]}, page, facts=facts, question=ask)["subject_mismatches"]
    assert marked("F-6 2인 가구 소득기준은 38,968,428원입니다.")
    assert not marked("F-6 2인 가구 소득기준은 32,154,216원입니다.")


def _probe_counts(probes):
    pages = af.pilot_pages()
    right_marked = wrong_marked = 0
    for p in probes:
        page = [{**pages[p["page_id"]], "id": p["page_id"]}]
        for kind in ("right", "wrong"):
            res = tg.post_check({"status": "answered", "answer": p[kind], "citations": [p["page_id"]]}, page, facts=FACTS, question=p["question"])
            marked = res["verdict"] == "withheld" or bool(res["subject_mismatches"] or res["role_mismatches"])
            right_marked += kind == "right" and marked
            wrong_marked += kind == "wrong" and marked
    return len(probes), right_marked, wrong_marked


def test_subject_probes_from_the_facts():
    """Built from the facts themselves (not an unseen set). Questions name what a person
    would (status code, household size): no right answer is marked, about half of the
    mixed-up ones are. Household mix-ups are all caught; a code alone often fits several
    rows, and row mix-ups cannot be told apart without the row named."""
    # 53 until a row for the named status beat the general row (2026-10-28, after v10 W-07).
    assert _probe_counts(af.subject_probes(FACTS)) == (113, 0, 88)


def test_pasting_the_ai_row_label_into_the_question_inflates_the_probe_score():
    """The first measurement (261/326) put the AI's row label in the question word for word;
    the check matches labels by exact substring, which no real question does. (Some
    labels carry a number, "③ 1년 복수사증"; since the answer-wide right-value rule such a
    pasted label counts as the right value, so this score fell from 98% to 94%.)"""
    n, right, wrong = _probe_counts(af.subject_probes(FACTS, row_labels=True))
    assert right == 0 and wrong / n > 0.9 > 53 / 113


def test_facts_do_not_mark_any_recorded_correct_real_manual_answer():
    import glob
    lv = load_module("label_v2")
    g = sys.modules["smoke_grader"]
    moved = []
    for rp in sorted(glob.glob(str(BOOTSTRAP_DIR / "runs" / "2026-10-2*" / "run_record.json"))):
        rec = json.loads(Path(rp).read_text(encoding="utf-8"))
        cf = rec.get("cases_file") or ""
        if not rec.get("source_gate") or rec.get("status") != "completed" or not cf.endswith(".v2.json"):
            continue
        path = lv.OUT / cf if (lv.OUT / cf).exists() else lv.OUT / "rerun" / cf
        cases = {c["id"]: c for c in af.manual_ledger.resolve_cases(json.loads(path.read_text(encoding="utf-8"))["cases"])}
        for r in rec["results"]:
            c = cases.get(r["case"])
            if c is None or r.get("clarified") or not r.get("post_check"):
                continue
            trusted = [e for e in c["evidence"] if tg.is_trusted(e, rec.get("integrity")) and e["id"] not in (r.get("route_withheld") or [])]
            res = tg.post_check(r.get("parsed"), trusted, facts=FACTS, question=c["question"])
            plain = {k: v for k, v in res["final"].items() if k != "review_flags"}
            if g.classify(g.grade(c, json.dumps(plain, ensure_ascii=False))) == "correct" and \
                    g.classify(g.grade(c, json.dumps(res["final"], ensure_ascii=False))) != "correct":
                moved.append((rp, r["case"]))
    assert moved == []


def test_facts_change_no_outcome_on_the_six_real_manual_sets():
    """The six real-manual sets on label v2 (E4B, r3 runs). --facts only feeds the
    post-check (run_smoke.py), and E4B at temperature 0 reproduced these outputs byte for
    byte, so re-checking the recorded outputs is what a facts-on run would give. With the
    current post-check, the facts move no answer at all: 0 correct answers to review or
    withheld, and none of the 15 wrong ones caught. Those 15 are procedure, document and
    scope errors, a wrong sub-code or count, or (N-06) weekly hours, which no fact holds."""
    import glob
    from collections import Counter
    lv = load_module("label_v2")
    g = sys.modules["smoke_grader"]
    seen = Counter()
    for rp in sorted(glob.glob(str(BOOTSTRAP_DIR / "runs" / "2026-10-28-*-v2-*-r3" / "run_record.json"))):
        rec = json.loads(Path(rp).read_text(encoding="utf-8"))
        cf = rec["cases_file"]
        path = lv.OUT / cf if (lv.OUT / cf).exists() else lv.OUT / "rerun" / cf
        cases = {c["id"]: c for c in af.manual_ledger.resolve_cases(json.loads(path.read_text(encoding="utf-8"))["cases"])}
        for r in rec["results"]:
            c = cases[r["case"]]
            if (r.get("clarified") and (r.get("parsed") or {}).get("status") == "clarify") or r.get("parsed") is None:
                continue
            trusted = [e for e in c["evidence"] if tg.is_trusted(e, rec.get("integrity")) and e["id"] not in (r.get("route_withheld") or [])]
            if not trusted:
                continue
            with_facts, without = (g.classify(g.grade(c, json.dumps(tg.post_check(r["parsed"], trusted, facts=f, question=c["question"])["final"], ensure_ascii=False)))
                                   for f in (FACTS, None))
            assert with_facts == without, (rp, r["case"], without, with_facts)
            seen[with_facts] += 1
    # Since the three checks of 2026-10-28 (after the analysis of these fifteen): Q-11's
    # flipped "수 없음" is withheld (harmful -> safe_abstain) and N-02 gets its p105 citation
    # (other -> correct).
    assert seen == {"correct": 79, "harmful": 5, "other": 8, "safe_abstain": 8, "needs_review": 4}, seen
