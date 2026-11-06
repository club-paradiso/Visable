"""Mission 005-K: per-situation model calls, the question's date as input, name-aware language checks, contract v8.

Fictional fixtures only. A general question whose evidence splits between people in Korea
and people abroad is asked once per situation; Korean names copied from the admissible
evidence do not count against an English or Vietnamese reply (unless they are most of it);
the date a user gives reaches the model. Neighbouring cases that must not change are included.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import grounding_guard as guard
import language_compliance
from gemma4_runtime import build_messages
from waymaker_ai import evidence_admissibility as adm
from waymaker_ai.evidence_registry import content_sha256, synthetic_registry
from waymaker_ai.inference_input import project_inference_item
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS, prompt_sha256

DATE = "2026-11-01"


def ev(i, text, title=""):
    return {"id": i, "title": title, "text": text, "source": {"document_id": "가상 문서"}}


def rec(e, **o):
    """A verified official fixture record (as in test_mission005g_trust), with overrides."""
    return {"evidence_id": e["id"], "source_locator": "가상", "issuing_organization": "가상 이주행정청",
            "document_type": "official_manual", "retrieved_at": "2026-10-01T00:00:00Z", "content_sha256": content_sha256(e["text"]),
            "verification": {"method": "synthetic_fixture", "verified_at": "2026-10-02T00:00:00Z", "result": "verified"},
            "authority": "official", "jurisdiction": ["national"], "subject": "Y-9", "status_scope": ["Y-9-1"],
            "all_subcategories_of": [], "procedures": ["any"], "applicant_scope": ["any"], "published": "2025-12-01",
            "effective_from": "2026-01-01", "effective_until": None, "superseded_by": None, "review_state": "approved",
            "decision_provenance": "test fixture", **o}


def answer(status, text, cites):
    return json.dumps({"status": status, "answer": text, "citations": list(cites)}, ensure_ascii=False)


DOM = ev("DOM", "가상 Y-9-1 국내 체류자는 가상 솔뫼 사무소에 연장을 신청한다.", "가상 운영지침 3쪽")
ABR = ev("ABR", "가상 Y-9-1 국외 체류자는 가상 재외공관에 연장을 신청한다.", "가상 운영지침 4쪽")
ANY = ev("ANY", "가상 Y-9-1 연장 서류는 가상 서식 KV31 신청서이다.", "가상 운영지침 5쪽")


def registry(*pairs):
    return synthetic_registry({e["id"]: rec(e, **o) for e, o in pairs}, "t")


SPLIT = registry((DOM, {"applicant_scope": ["domestic"]}), (ABR, {"applicant_scope": ["abroad"]}), (ANY, {}))
Q = "Where does a hypothetical Y-9-1 holder apply for an extension?"


# --- per-situation parts ---------------------------------------------------------------
def test_general_question_split_between_korea_and_abroad_is_asked_per_situation():
    prep = guard.prepare(Q, None, [DOM, ABR, ANY], SPLIT, DATE)
    assert [p["location"] for p in prep["parts"]] == ["domestic", "abroad"]
    assert [[e["id"] for e in i["evidence"]] for i in prep["model_items"]] == [["DOM", "ANY"], ["ABR", "ANY"]]
    assert [i["system"]["scope_location"] for i in prep["model_items"]] == ["domestic", "abroad"]


@pytest.mark.parametrize("question, intake", [
    ("Where does a hypothetical Y-9-1 holder in Korea apply for an extension?", None),   # location given in text
    (Q, {"location": "abroad"}),                                                           # location given in intake
    ("제가 가상 Y-9-1 체류자인데 연장은 어디에 신청해야 하나요?", None),                       # personal: clarification
])
def test_no_situation_split(question, intake):
    prep = guard.prepare(question, intake, [DOM, ABR, ANY], SPLIT, DATE)
    assert len(prep["model_items"]) <= 1


def test_sub_code_split_takes_precedence_and_situations_need_both_sides():
    only_dom = registry((DOM, {"applicant_scope": ["domestic"]}), (ANY, {}))
    assert guard.prepare(Q, None, [DOM, ANY], only_dom, DATE)["selection"]["situation_parts"] == []


def test_parts_are_joined_and_guarded_per_situation():
    raws = iter([answer("answered", "In Korea: the fictional Solmoe office (가상 솔뫼 사무소).", ["DOM"]),
                 answer("answered", "Abroad: the fictional overseas mission.", ["ABR"])])
    r = guard.run_case(Q, None, [DOM, ABR, ANY], SPLIT, DATE, lambda item: next(raws))
    assert r["guard"]["decision"] == "release" and r["released"]["citations"] == ["DOM", "ABR"]
    bad = iter([answer("answered", "In Korea: the Solmoe office.", ["DOM"]), answer("answered", "Abroad: the Solmoe office.", ["DOM"])])
    assert guard.run_case(Q, None, [DOM, ABR, ANY], SPLIT, DATE, lambda item: next(bad))["guard"]["decision"] == "invalid_response"


# --- the question's date ---------------------------------------------------------------
def test_a_date_the_user_gives_reaches_the_model_and_the_evaluation_date_does_not():
    reg = registry((ANY, {}))
    dated = guard.prepare("2026년 3월에 가상 Y-9-1 연장 서류는 무엇이었나요?", None, [ANY], reg, DATE)
    plain = guard.prepare("가상 Y-9-1 연장 서류는 무엇인가요?", None, [ANY], reg, DATE)
    assert dated["model_items"][0]["system"]["as_of"] == "2026-03-01"
    assert "as_of" not in plain["model_items"][0]["system"]


# --- names copied from the evidence -----------------------------------------------------
NAMES = ["가상 한별출입국처 고시 제2026-51호", "가상 한별출입국처 고시 제2026-51호: R-7-2 연장 처리기간은 20일이다."]


@pytest.mark.parametrize("reply, result", [
    ("The processing time is 20 days according to 가상 한별출입국처 고시 제2026-51호.", "pass"),
    ("Thời gian xử lý là 20 ngày theo 가상 한별출입국처 고시 제2026-51호.", "pass"),
    ("가상 한별출입국처 고시 제2026-51호: R-7-2 연장 처리기간은 20일이다.", "fail"),       # copied Korean is still Korean
    ("The time is 20 days, 처리기간은 길지 않습니다.", "unresolved"),                      # Korean not from the evidence still counts
])
def test_language_check_skips_names_copied_from_the_evidence(reply, result):
    lang = "vi" if "Thời" in reply else "en"
    assert language_compliance.check("What is the processing time?", reply, lang, protected_texts=NAMES)["result"] == result


def test_without_evidence_the_language_check_is_unchanged():
    reply = "The processing time is 20 days according to 가상 한별출입국처 고시 제2026-51호."
    assert language_compliance.check("What is the processing time?", reply, "en")["result"] == "unresolved"


# --- contract v8 ------------------------------------------------------------------------
def test_v8_is_new_and_earlier_prompts_are_unchanged():
    # Mission 005-L added v9 after these; the first eight, their order and v8's prompt stay.
    assert CONTRACT_VERSIONS[:8] == ("v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8") and prompt_sha256("v8").startswith("d87b7e40120a")
    assert len({prompt_sha256(v) for v in CONTRACT_VERSIONS}) == len(CONTRACT_VERSIONS)
    for phrase in ("scope_location", "answer only for that situation", "If as_of is given", "exactly three keys"):
        assert phrase in SYSTEM_PROMPTS["v8"]


def test_v8_message_carries_situation_and_date_and_only_v8_accepts_them():
    prep = guard.prepare(Q, None, [DOM, ABR, ANY], SPLIT, DATE)
    payload = json.loads(build_messages(prep["model_items"][1], "v8")[1]["content"])
    assert list(payload) == ["question", "reply_language", "uncovered_items", "scope_location", "evidence"]
    with pytest.raises(ValueError):
        build_messages(prep["model_items"][1], "v7")


@pytest.mark.parametrize("system", [{"scope_location": "everywhere"}, {"as_of": "March 2026"}])
def test_new_system_fields_are_validated(system):
    with pytest.raises(ValueError):
        project_inference_item({"question": "q", "evidence": [], "system": {"reply_language": "en", "uncovered_items": [], **system}})


def test_gate_v6_keeps_the_v5_categories():
    import synthetic_safety_gate_v5 as gate5
    import synthetic_safety_gate_v6 as gate6
    assert gate6.CATEGORIES == gate5.CATEGORIES
