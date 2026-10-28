"""Label version 2: frozen originals preserved, 140 ids and order kept, and every
changed label tested against correct paraphrases, swapped or reversed answers,
answers that quote an error to correct it, and the recorded model answers.

None of this checks legal correctness. It checks that the v2 labels say what
the supplied manual page says, and that they fail and pass the answers they
claim to.
"""
from __future__ import annotations

import hashlib
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


lv = load_module("label_v2")
grader = load_module("smoke_grader")
ml = load_module("manual_ledger")

V2 = BOOTSTRAP_DIR / "label_v2"
LEDGER = json.loads((V2 / "decisions.v2.json").read_text(encoding="utf-8"))
#: SHA-256 of the frozen case files, as recorded when they were frozen and in the review sheet bundle.
FROZEN_SHA256 = {
    "manual_oracle": "405d9dd5f3a331ae846c583b610924031ad20100714724cb7159ee117c3f9741",
    "manual_routing": "4acdc57a53f945b87f9996a27d628a5a0367b61766d77fdb72df2053448dd0d1",
    "manual_clarify": "410798edef4ecab2dd37a5ad5e85065c81e721815577c2e0d41514969ccbdc1b",
    "manual_buttons": "2994b8126848d777918b13dd1eef0033fc93524063fc6011736b5941438dd42a",
    "manual_always_ask": "28bf2fefbcb1c267de62b611d0b83cbecaf377227275e7e4056b17b265e34bba",
    "manual_misclick": "b04bb7f932884d8f16dc41463aecf3055b26be7fc7222af4c1135c157d357166",
}


def frozen(set_name):
    return json.loads((BOOTSTRAP_DIR / f"{set_name}_cases.json").read_text(encoding="utf-8"))["cases"]


def v2(set_name):
    return json.loads((V2 / f"{set_name}_cases.v2.json").read_text(encoding="utf-8"))


def v2_case(key):
    set_name, cid = key.split("/")
    return next(c for c in v2(set_name)["cases"] if c["id"] == cid)


def answer(text, cites, status="answered"):
    return json.dumps({"status": status, "answer": text, "citations": cites}, ensure_ascii=False)


# --- preservation -----------------------------------------------------------

@pytest.mark.parametrize("set_name", lv.SETS)
def test_frozen_originals_are_untouched(set_name):
    path = BOOTSTRAP_DIR / f"{set_name}_cases.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == FROZEN_SHA256[set_name]
    assert v2(set_name)["derived_from"] == {"file": path.name, "sha256": FROZEN_SHA256[set_name]}


@pytest.mark.parametrize("set_name", lv.SETS)
def test_v2_keeps_ids_order_and_every_unchanged_case(set_name):
    old, new = frozen(set_name), v2(set_name)["cases"]
    assert [c["id"] for c in old] == [c["id"] for c in new]
    changed = {d["id"] for d in LEDGER["decisions"] if d["set"] == f"{set_name}_cases.json" and d["changed"]}
    for o, n in zip(old, new):
        if o["id"] not in changed:
            assert o == n, o["id"]
        else:
            assert o["question"] == n["question"] and o.get("group") == n.get("group")


def test_ledger_has_one_row_per_case_in_order_and_claims_no_verification():
    keys = [f"{s}/{c['id']}" for s in lv.SETS for c in frozen(s)]
    assert [d["key"] for d in LEDGER["decisions"]] == keys and len(keys) == 140
    for d in LEDGER["decisions"]:
        assert d["verification"].startswith("검증 보류")
        assert d["decision"] in lv.DECISION_VALUES
        assert d["changed"] == (d["decision"] in lv.CHANGING)
        if not d["changed"]:
            assert d["v2"] is None
    assert len(lv.DECISIONS) == 10
    round3_changes = sum(1 for d in LEDGER["decisions"] if d["decision"] in ("ai_review_changed", "owner_decided"))
    assert LEDGER["counts"]["changed"] == len(lv.DECISIONS) + round3_changes


def test_committed_v2_files_match_a_fresh_build():
    assert lv.check() == []


def test_every_v2_page_reference_resolves_and_passes_integrity():
    for set_name in lv.SETS:
        for case in ml.resolve_cases(v2(set_name)["cases"]):
            for e in case["evidence"]:
                assert e["source"]["approval_state"] == "approved", (case["id"], e["id"])
            cited = " ".join(e["text"] for e in case["evidence"] if e["id"] in case["expect"].get("must_cite", []))
            for needle in case["expect"].get("answer_must_contain", []):
                assert needle in cited, (case["id"], needle)


def test_saved_review_verdicts_are_preserved_in_the_snapshot_and_linked():
    live = json.loads((BOOTSTRAP_DIR / "reviews" / "live_review_export_2026-10-27.json").read_text(encoding="utf-8"))
    keys = [f"{s}/{c['id']}" for s in lv.SETS for c in frozen(s)]
    assert sorted(r["data"]["key"] for r in live["reviews"]) == sorted(keys)
    human = {r["data"]["case_id"] for r in live["reviews"] if r["provenance_per_handoff_index"] == "existing_human"}
    assert human == {"M-01-stay-extension-fee", "M-10-d10t-stay-cap"}
    by_key = {d["key"]: d for d in LEDGER["decisions"]}
    for r in live["reviews"]:
        assert by_key[r["data"]["key"]]["sources"]["saved_verdict"]["verdict"] == r["data"]["verdict"]


# --- structural checks on the changed labels -----------------------------------

P5, P37, P160 = "stay_manual_2026_10_19_pdf#p5", "stay_manual_2026_10_19_pdf#p37", "stay_manual_2026_10_19_pdf#p160"
P328, P313, P108 = "stay_manual_2026_10_19_pdf#p328", "visa_manual_2026_10_19_pdf#p313", "visa_manual_2026_10_19_pdf#p108"
P524 = "stay_manual_2026_10_19_pdf#p524"
N06 = "manual_routing/N-06-h1-canada-weekly-hours"
#: The recorded N-06 answer (routing run): 25 hours as the general cap, then 40 hours as a "stay period".
N06_RECORDED = ("H-1 비자 소지자의 경우, 상대 국가에서 우리 국민 대상 취업 기간을 변동한 경우 상호주의에 따라 동일하게 취업 기간을 변동하며, "
                "1주당 최대 취업 가능 시간은 25시간 이내입니다. 캐나다의 경우 H-1 체류 기간은 40시간으로 2,080시간(40시간×52주)입니다.")

CONTROLS = [
    # (case key, answer, citations, should pass, flagged)
    ("manual_oracle/M-10-d10t-stay-cap", "최우수인재(D-10-T)의 체류기간은 최대 3년이며, 1회 부여 기간은 1년입니다.", [P160], True, False),
    ("manual_oracle/M-10-d10t-stay-cap", "체류기간 상한은 3년(1회 1년)입니다.", [P160], True, False),
    ("manual_oracle/M-10-d10t-stay-cap", "한 번에 1년씩 받고, 총 3년까지 머물 수 있습니다.", [P160], True, False),
    ("manual_oracle/M-10-d10t-stay-cap", "1회 1년씩, 최대 3년까지입니다.", [P160], True, False),
    ("manual_oracle/M-10-d10t-stay-cap", "1회 3년이 아니라 1회 1년이고, 총 3년까지입니다.", [P160], True, False),
    ("manual_oracle/M-10-d10t-stay-cap", "최대 1년이고, 1회 3년씩 받을 수 있습니다.", [P160], False, False),
    ("manual_oracle/M-10-d10t-stay-cap", "총 1년까지 머물 수 있고 한 번에 3년을 받습니다.", [P160], False, False),
    ("manual_oracle/M-10-d10t-stay-cap", "체류기간은 최대 3년입니다.", [P160], False, False),
    ("manual_oracle/M-01-stay-extension-fee", "일반 체류기간 연장 수수료는 60,000원입니다.", [P5], True, False),
    ("manual_oracle/M-01-stay-extension-fee", "6만원입니다.", [P5], True, False),
    ("manual_oracle/M-01-stay-extension-fee", "6만 원입니다.", [P5], True, False),
    ("manual_oracle/M-01-stay-extension-fee", "16만원입니다.", [P5], False, False),
    ("manual_oracle/M-01-stay-extension-fee", "3만원입니다.", [P5], False, False),
    ("manual_oracle/M-04-d4-parttime-wait", "D-4-1은 변경일(사증소지자는 입국일)로부터 6개월이 경과해야 허가를 받을 수 있습니다.", [P37], True, False),
    ("manual_oracle/M-04-d4-parttime-wait", "입국일부터 6개월이 지나면 신청할 수 있습니다.", [P37], True, False),
    ("manual_oracle/M-04-d4-parttime-wait", "해당 활동을 하려는 시점으로부터 6개월이 경과된 경우 가능합니다.", [P37], False, True),
    ("manual_oracle/M-04-d4-parttime-wait", "아르바이트를 시작하는 날부터 6개월 뒤에 가능합니다.", [P37], False, True),
    ("manual_oracle/M-04-d4-parttime-wait", "활동을 하려는 시점부터 6개월이 아니라, 입국일부터 6개월이 경과해야 합니다.", [P37], True, True),
    ("manual_oracle/M-04-d4-parttime-wait", "6개월이 지나면 됩니다.", [P37], False, False),
    ("manual_clarify/Q-11-e9-change-jobs-count", "최초 3년 동안은 원칙적으로 3회를 초과할 수 없고, 연장된 기간에는 2회를 초과할 수 없습니다.", [P328], True, False),
    ("manual_clarify/Q-11-e9-change-jobs-count", "원칙적으로 3회까지 사업장을 바꿀 수 있습니다.", [P328], True, False),
    ("manual_clarify/Q-11-e9-change-jobs-count", "최대 3회 변경할 수 있어요.", [P328], True, False),
    ("manual_clarify/Q-11-e9-change-jobs-count", "원칙적으로 3회, 연장 기간에는 2회를 초과하여 사업장을 변경할 수 있습니다.", [P328], False, True),
    ("manual_clarify/Q-11-e9-change-jobs-count", "3회 이상 자유롭게 변경 가능합니다.", [P328], False, False),
    ("manual_clarify/Q-11-e9-change-jobs-count", "'3회를 초과하여 변경할 수 있다'는 말은 틀립니다. 원칙적으로 3회를 초과할 수 없습니다.", [P328], True, True),
    ("manual_misclick/K-05-f2-2-child-of-national", "공관장 재량으로 5년간 유효한 체류기간 1년 이하의 F-2-2 복수사증을 받을 수 있습니다.", [P313], True, False),
    ("manual_misclick/K-05-f2-2-child-of-national", "F-2-2 복수사증(5년간 유효한)을 받을 수 있습니다. 다만 병역을 이행하지 않고 국적을 이탈한 남성 등 제외대상자에게는 발급되지 않습니다.", [P313], True, False),
    ("manual_misclick/K-05-f2-2-child-of-national", "F-2-2 사증은 5년간 유효한 복수사증이며, 제외대상자에 해당하면 발급이 제한됩니다.", [P313], True, False),
    ("manual_misclick/K-05-f2-2-child-of-national", "공관장 재량으로 5년간 유효한 F-2-2 복수사증을 받을 수 있습니다. 다만, 이는 사증발급 제외대상자에게 적용되는 사항입니다.", [P313], False, False),
    ("manual_misclick/K-05-f2-2-child-of-national", "F-2-2, 5년간 유효한 사증은 제외 대상자만 받을 수 있습니다.", [P313], False, False),
]


@pytest.mark.parametrize("key, text, cites, should_pass, flagged", CONTROLS)
def test_structural_label_controls(key, text, cites, should_pass, flagged):
    case = ml.resolve_cases([v2_case(key)])[0]
    g = grader.grade(case, answer(text, cites))
    assert g["passed"] is should_pass, g["failures"]
    assert bool(g["flags"]) is flagged, g["flags"]


def test_original_labels_got_these_controls_wrong():
    """The point of v2: the frozen labels passed the reversed answers and failed a right one."""
    cases = {f"{s}/{c['id']}": c for s in ("manual_oracle", "manual_clarify", "manual_misclick", "manual_routing") for c in ml.resolve_cases(frozen(s))}
    wrong = [
        ("manual_clarify/Q-11-e9-change-jobs-count", "원칙적으로 3회, 연장 기간에는 2회를 초과하여 사업장을 변경할 수 있습니다.", [P328], True),
        ("manual_misclick/K-05-f2-2-child-of-national", "공관장 재량으로 5년간 유효한 F-2-2 복수사증을 받을 수 있습니다. 다만, 이는 사증발급 제외대상자에게 적용되는 사항입니다.", [P313], True),
        ("manual_oracle/M-04-d4-parttime-wait", "해당 활동을 하려는 시점으로부터 6개월이 경과된 경우 가능합니다.", [P37], True),
        ("manual_oracle/M-10-d10t-stay-cap", "최우수인재(D-10-T)의 체류기간은 최대 3년이며, 1회 부여 기간은 1년입니다.", [P160], False),
        (N06, N06_RECORDED, [P524], True),
    ]
    for key, text, cites, old_passes in wrong:
        assert grader.grade(cases[key], answer(text, cites))["passed"] is old_passes, key


# --- regressions found after the first v2 (96eb71c) ------------------------------
# Outcome is what the grader's classify() reports: "correct" is counted as right
# automatically, "needs_review" passed every check but goes to a person, "harmful"
# contradicts the page, "other" is wrong without a contradiction.

OUTCOME_CONTROLS = [
    # Owner's independent check of 96eb71c: these passed (Q-11 with no flag, M-04 with only a flag).
    ("manual_clarify/Q-11-e9-change-jobs-count", "최초에는 최대 3회까지, 재고용 기간에는 2회 넘게 변경할 수 있습니다.", [P328], "harmful"),
    ("manual_oracle/M-04-d4-parttime-wait", "입국일과는 무관하며 시간제 취업을 시작하려는 날부터 6개월이 경과하면 됩니다.", [P37], "harmful"),
    # Q-11: both limits right, either wording; the 2-time limit left out while 재고용 is mentioned goes to a person.
    ("manual_clarify/Q-11-e9-change-jobs-count", "취업가능기간 중에는 원칙적으로 3회까지, 재고용으로 연장된 기간에는 2회까지 변경할 수 있습니다.", [P328], "correct"),
    ("manual_clarify/Q-11-e9-change-jobs-count", "원칙적으로 3회를 초과할 수 없고, 재고용 연장 기간 중에는 2회를 초과할 수 없습니다.", [P328], "correct"),
    ("manual_clarify/Q-11-e9-change-jobs-count", "3회까지 변경할 수 있고, 재고용 기간에도 변경할 수 있습니다.", [P328], "needs_review"),
    ("manual_clarify/Q-11-e9-change-jobs-count", "3회까지 가능하며 3회 이상 변경은 불가능합니다.", [P328], "correct"),
    ("manual_clarify/Q-11-e9-change-jobs-count", "'2회를 초과하여 변경할 수 있다'는 설명은 틀렸습니다. 원칙적으로 3회까지이고 재고용 기간에는 2회를 넘을 수 없습니다.", [P328], "needs_review"),
    # M-04: the start point has to be in the start-point position, not just named.
    ("manual_oracle/M-04-d4-parttime-wait", "입국일로부터 6개월이 지나면 됩니다.", [P37], "correct"),
    ("manual_oracle/M-04-d4-parttime-wait", "입국한 날부터 6개월이 지나야 합니다.", [P37], "correct"),
    ("manual_oracle/M-04-d4-parttime-wait", "입국일과 무관하다는 안내는 잘못입니다. 입국일로부터 6개월이 지나야 합니다.", [P37], "correct"),
    ("manual_oracle/M-04-d4-parttime-wait", "시작하려는 날부터 6개월이라는 설명은 틀렸고, 변경일 또는 입국일로부터 6개월이 경과해야 합니다.", [P37], "needs_review"),
    ("manual_oracle/M-04-d4-parttime-wait", "입국일은 참고만 하고, 시간제 취업을 시작하려는 날부터 6개월이 지나면 됩니다.", [P37], "other"),
    # N-06: 40 hours must be per week; 40 hours as a stay period fails; a bare 25-hour cap goes to a person.
    (N06, N06_RECORDED, [P524], "harmful"),
    (N06, "캐나다 참가자는 1주당 최대 40시간까지 일할 수 있습니다.", [P524], "correct"),
    (N06, "다른 나라는 1주당 25시간이지만 캐나다는 1주당 최대 40시간입니다.", [P524], "correct"),
    (N06, "Canadian participants may work up to 40 hours per week.", [P524], "correct"),
    (N06, "캐나다: 취업기간 H-1 체류기간, 1주당 최대 40시간, 최대 2,080시간입니다.", [P524], "correct"),
    (N06, "1주당 최대 25시간입니다. 캐나다는 주 40시간입니다.", [P524], "needs_review"),
    (N06, "40시간입니다.", [P524], "other"),
    (N06, "'캐나다 체류기간이 40시간'이라는 설명은 잘못이며, 캐나다는 1주당 40시간까지 일할 수 있습니다.", [P524], "correct"),
]


@pytest.mark.parametrize("key, text, cites, outcome", OUTCOME_CONTROLS)
def test_regression_controls_by_outcome(key, text, cites, outcome):
    case = ml.resolve_cases([v2_case(key)])[0]
    g = grader.grade(case, answer(text, cites))
    assert grader.classify(g) == outcome, (g["failures"], g["flags"])


def test_imported_adversarial_examples_are_never_counted_correct():
    """Owner's regression evidence (copied unmodified): each example answer must fail
    or go to a person under v2, never be an automatic correct."""
    root = BOOTSTRAP_DIR / "reviews" / "regression_evidence_2026-10-27"
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    for f in manifest["files"]:
        assert hashlib.sha256((root / f["path"]).read_bytes()).hexdigest() == f["sha256"], f["path"]
    keys = {c["id"]: f"{s}/{c['id']}" for s in lv.SETS for c in frozen(s)}
    gold = {"Q-11-e9-change-jobs-count": [P328], "M-04-d4-parttime-wait": [P37], "M-10-d10t-stay-cap": [P160]}
    examples = json.loads((root / "adversarial_examples.json").read_text(encoding="utf-8"))
    assert len(examples) == 3
    for ex in examples:
        case = ml.resolve_cases([v2_case(keys[ex["record_id"]])])[0]
        g = grader.grade(case, answer(ex["answer"], gold[ex["record_id"]]))
        assert grader.classify(g) != "correct", ex["record_id"]


def test_flagged_answers_are_kept_out_of_the_automatic_correct_count():
    case = ml.resolve_cases([v2_case("manual_oracle/M-04-d4-parttime-wait")])[0]
    g = grader.grade(case, answer("활동을 하려는 시점부터 6개월이 아니라, 입국일부터 6개월이 경과해야 합니다.", [P37]))
    assert g["passed"] and g["flags"] and g["needs_review"]
    assert grader.classify(g) == "needs_review"
    assert grader.summarize([g, {"passed": True, "flags": []}]) == {
        "cases": 2, "passed": 2, "failed": 0, "needs_review": 1, "auto_correct": 1}
    s = lv.regrade(write=False)["summary"]
    assert s["auto_correct_v2"] + s["needs_review_v2"] + s["failed_v2"] == s["comparable"] == 139
    assert "passed_v2" not in s


def test_n06_recorded_answer_is_not_confirmed_as_safe():
    row = next(d for d in LEDGER["decisions"] if d["key"] == N06)
    assert row["decision"] == "adopted_modified" and row["verification"].startswith("검증 보류")
    assert "whic.mofa.go.kr" in row["not_adopted"]  # the guide is noted, not used as label evidence
    graded = next(r for r in lv.regrade(write=False)["rows"] if r["key"] == N06)
    assert graded["original"]["passed"] is True and graded["v2"]["outcome"] == "harmful"


def test_k14_moves_the_gold_page_and_marks_recorded_answers_not_comparable():
    case = v2_case("manual_misclick/K-14-d8-4-where-to-apply-misclick")
    assert case["expect"]["must_cite"] == [P108]
    assert P108 in [e["id"] for e in case["evidence"]] and "visa_manual_2026_10_19_pdf#p107" in [e["id"] for e in case["evidence"]]
    row = next(d for d in LEDGER["decisions"] if d["id"] == case["id"])
    assert row["recorded_answer_comparable"] is False and row["open_issues"]


def test_partial_v2_proposals_are_recorded_but_not_adopted_verbatim():
    rows = {d["key"]: d for d in LEDGER["decisions"]}
    for key in ("manual_oracle/M-04-d4-parttime-wait", "manual_clarify/Q-11-e9-change-jobs-count", "manual_misclick/K-05-f2-2-child-of-national", "manual_oracle/M-10-d10t-stay-cap"):
        proposal = rows[key]["sources"]["chatgpt_partial_v2"]["proposed_expect"]
        assert proposal != rows[key]["v2"]["expect"], key
        assert rows[key]["decision"] == "adopted_modified"
    for key in ("manual_routing/N-10-d5-consular-visa-bureau-docs", "manual_misclick/K-06-c3-3-medical-docs", "manual_misclick/K-10-f1-ethnic-korean-activity"):
        assert rows[key]["sources"]["chatgpt_partial_v2"]["proposed_expect"] == rows[key]["v2"]["expect"], key


def test_regrade_report_matches_a_fresh_regrade():
    committed = json.loads((V2 / "regrade_recorded_answers.v2.json").read_text(encoding="utf-8"))
    fresh = lv.regrade(write=False)
    assert committed["summary"] == fresh["summary"] and committed["post_hoc"] is True
    assert fresh["summary"]["not_comparable"] == ["manual_misclick/K-14-d8-4-where-to-apply-misclick"]


def test_imported_second_opinion_files_match_their_manifest():
    root = BOOTSTRAP_DIR / "reviews" / "second_opinion_chatgpt_2026-10-27"
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    for f in manifest["files"]:
        assert hashlib.sha256((root / f["path"]).read_bytes()).hexdigest() == f["sha256"], f["path"]
    originals = next(n for n in manifest["not_copied"] if n["path"] == "originals/*.json")
    assert originals["equal_to_repo_frozen"] is True
    for name, sha in originals["sha256"].items():
        assert FROZEN_SHA256[name.replace("_cases.json", "")] == sha


def test_review_sheet_bundle_links_every_case_to_label_v2_in_order(tmp_path):
    rs = load_module("build_review_sheet")
    data = rs.build()
    keys = [f"{s}/{c['id']}" for s in lv.SETS for c in frozen(s)]
    assert [c["key"] for c in data["cases"]] == keys
    assert data["version"] == "artemis-label-review-v2" and data["label_version_available"] is True
    assert all(c["label_v2"] is not None for c in data["cases"])
    changed = [c["key"] for c in data["cases"] if c["label_v2"]["changed"]]
    assert sorted(changed) == sorted(d["key"] for d in LEDGER["decisions"] if d["changed"])
    assert set(lv.DECISIONS) <= set(changed)
    assert "visa_manual_2026_10_19_pdf#p108" in data["pages"]
    for s in data["sets"]:
        assert s["v2_file"] and len(s["v2_sha256"]) == 64


def test_review_sheet_page_never_writes_the_legacy_reviews_collection():
    page = (BOOTSTRAP_DIR / "review_sheet" / "index.html").read_text(encoding="utf-8")
    assert 'collection("reviews_v2").doc(' in page
    assert 'collection("reviews").doc(' not in page


# --- round 3: AI review of every case, statutes as a cross-check -----------------

ROUND3 = json.loads(lv.ROUND3.read_text(encoding="utf-8"))


def test_round3_review_file_passes_its_own_verification():
    """Every row quotes its page exactly, every pattern compiles, and every control
    in the file grades as the reviewer said under the real grader."""
    assert lv.check_round3() == []


def test_round3_covers_all_140_cases_in_order_and_claims_no_human_or_legal_verification():
    keys = [f"{s}/{c['id']}" for s in lv.SETS for c in frozen(s)]
    assert [r["key"] for r in ROUND3["cases"]] == keys
    assert "not a human review" in ROUND3["reviewer"] and "not a legal verification" in ROUND3["reviewer"]
    for d in LEDGER["decisions"]:
        assert d["verification"].startswith("검증 보류")
        assert d["ai_review_round3"] is not None


def test_round3_never_relabels_to_a_statute_and_leaves_needs_human_cases_untouched():
    for r in ROUND3["cases"]:
        row = next(d for d in LEDGER["decisions"] if d["key"] == r["key"])
        if r["legal_check"]["result"] == "differs":
            assert r["verdict"] == "needs_human" or r.get("owner_decision"), r["key"]
        if r["verdict"] == "needs_human":
            assert row["decision"] in ("needs_human",) + lv.CHANGING[:2]
            if r["key"] not in lv.DECISIONS:
                assert row["changed"] is False and row["v2"] is None
                assert any(i.startswith("사람이 정할 것:") for i in row["open_issues"])
        if r["key"] in lv.DECISIONS:
            assert r["verdict"] != "change"
            assert row["decision"] == lv.DECISIONS[r["key"]]["decision"]


def test_round3_needs_human_set_and_statute_conflicts_are_the_reviewed_ones():
    """After the lead cross-check only B-16 stays with a person; every case the lead
    settled records what it was before and why."""
    needs = sorted(r["key"].split("/")[1][:4] for r in ROUND3["cases"] if r["verdict"] == "needs_human")
    assert needs == []
    differs = sorted(r["key"].split("/")[1][:4] for r in ROUND3["cases"] if r["legal_check"]["result"] == "differs")
    assert differs == ["B-16"]  # kept on record although the owner decided the label
    settled = sorted(r["key"].split("/")[1][:4] for r in ROUND3["cases"] if r.get("lead_override"))
    assert settled == ["B-18", "B-19", "B-21", "B-22", "B-23", "K-08", "N-03", "N-14", "Q-22"]
    for r in ROUND3["cases"]:
        if r.get("lead_override"):
            assert r["lead_override"]["was"]["verdict"] == "needs_human" and r["lead_override"]["why"]
    b16 = next(d for d in LEDGER["decisions"] if d["key"].endswith("B-16-h1-job-change"))
    assert b16["decision"] == "owner_decided" and b16["changed"]
    assert b16["ai_review_round3"]["owner_decision"]["decision"] == "매뉴얼을 기준으로 판단해서 결정짓자"
    assert b16["ai_review_round3"]["legal_check"]["result"] == "differs"


def test_if_answered_checks_apply_only_to_direct_answers():
    case = ml.resolve_cases([v2_case("manual_buttons/B-23-e9-going-home-briefly")])[0]
    ask = grader.grade(case, answer("어떤 절차를 물으시는지 먼저 확인할게요.", [], status="clarify"))
    assert grader.classify(ask) == "correct"
    vague = grader.grade(case, answer("가족 방문은 가능합니다.", ["stay_manual_2026_10_19_pdf#p332"], status="partial"))
    assert not vague["passed"] and any(f.startswith("answer_missing_pattern:") for f in vague["failures"])


# --- the v2 re-measurement (2026-10-28) ---------------------------------------

V2_RUNS = {
    "manual_oracle": "2026-10-28-e4b-it-4bit-m1-8gb-v2-oracle-r3",
    "manual_routing": "2026-10-28-e4b-it-4bit-m1-8gb-v2-routing-routed-r3",
    "manual_clarify": "2026-10-28-e4b-it-4bit-m1-8gb-v2-clarify-route-clarify-r3",
    "manual_buttons": "2026-10-28-e4b-it-4bit-m1-8gb-v2-buttons-buttons-r3",
    "manual_always_ask": "2026-10-28-e4b-it-4bit-m1-8gb-v2-always-ask-r3",
    "manual_misclick": "2026-10-28-e4b-it-4bit-m1-8gb-v2-misclick-label-r3",
}


def test_v2_rerun_reproduces_the_post_hoc_regrade():
    """E4B at temperature 0 with the original settings, re-run on the v2 files: every
    comparable case lands on the outcome the post-hoc regrade predicted, and every
    model-written answer is byte-identical to the earlier run."""
    regrade = {r["key"]: r for r in lv.regrade(write=False)["rows"]}
    for set_name, run in V2_RUNS.items():
        record = json.loads((BOOTSTRAP_DIR / "runs" / run / "run_record.json").read_text(encoding="utf-8"))
        assert record["status"] == "completed" and record["cases_file"] == f"{set_name}_cases.v2.json"
        old = {r["case"]: r for r in json.loads((BOOTSTRAP_DIR / "runs" / lv.RUNS[set_name] / "run_record.json").read_text(encoding="utf-8"))["results"]}
        assert [r["case"] for r in record["results"]] == [c["id"] for c in frozen(set_name)]
        for r in record["results"]:
            key = f"{set_name}/{r['case']}"
            if regrade[key]["comparable"]:
                assert r["outcome_checked"] == regrade[key]["v2"]["outcome"], key
            model_written = not (r.get("clarified") and (r.get("parsed") or {}).get("status") == "clarify")
            if model_written and regrade[key]["comparable"]:
                assert r["output"] == old[r["case"]]["output"], key


def test_premise_audit_covers_every_case_and_changes_no_label():
    """The 2026-10-28 premise audit is a record: one verdict per case, every flagged
    case carries the lead session's check, and no label or question was edited for it."""
    audit = json.loads((BOOTSTRAP_DIR / "reviews" / "premise_audit_2026-10-28.json").read_text(encoding="utf-8"))
    assert "not a human review" in audit["reviewer"]
    keys = [f"{s}/{c['id']}" for s in lv.RUNS for c in frozen(s)]
    assert sorted(a["key"] for a in audit["audits"]) == sorted(keys)
    assert all("lead" in a for a in audit["audits"] if a["verdict"] != "ok")
    assert "premise" not in json.dumps(lv.DECISIONS, ensure_ascii=False)
