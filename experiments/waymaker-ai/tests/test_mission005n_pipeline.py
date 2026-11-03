"""Mission 005-N: document and office names out of the question context, the method question, ages, contract v11.

Fictional fixtures only. A05M-74 read "overseas" in "overseas mission handbook" as the user's location;
A05M-48 did not read "How can a fictional T-5-1 holder apply" as a method question; A05M-38 withheld a
correct answer that wrote "17 years of age"; A05M-45 kept "Using Korean," in the model's question.
Neighbouring cases that must not change are included.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import claim_support_validation as claims
import grounding_guard as guard
from waymaker_ai.evidence_admissibility import question_context, requested_items, without_document_names
from waymaker_ai.evidence_registry import content_sha256, synthetic_registry
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS, parse_response

DATE = "2026-11-01"


def ev(i, text, document_id="가상 문서"):
    return {"id": i, "title": "", "text": text, "source": {"document_id": document_id, "effective_date": "2026-01-01"}}


def rec(e, **o):
    """A verified official fixture record (as in test_mission005m_pipeline), with overrides."""
    return {"evidence_id": e["id"], "source_locator": "가상", "issuing_organization": "가상 이주행정청",
            "document_type": "official_manual", "retrieved_at": "2026-10-01T00:00:00Z", "content_sha256": content_sha256(e["text"]),
            "verification": {"method": "synthetic_fixture", "verified_at": "2026-10-02T00:00:00Z", "result": "verified"},
            "authority": "official", "jurisdiction": ["national"], "subject": "Y-9", "status_scope": ["Y-9-1"],
            "all_subcategories_of": [], "procedures": ["any"], "applicant_scope": ["any"], "published": "2025-12-01",
            "effective_from": "2026-01-01", "effective_until": None, "superseded_by": None, "review_state": "approved",
            "decision_provenance": "test fixture", **o}


def answer(status, text, cites):
    return json.dumps({"status": status, "answer": text, "citations": list(cites)}, ensure_ascii=False)


def location(question, candidates=()):
    return question_context(question, None, None, DATE, context_question=without_document_names(question, candidates))["location"]


# --- location words that name an office or a document ---------------------------------------------
@pytest.mark.parametrize("question", [
    "What is the fee for a fictional Y-9-1 re-entry permit, according to the overseas mission handbook (2nd edition)?",
    "가상 Y-9-1 재입국허가 수수료를 해외 공관 안내서 기준으로 알려 주세요.",
    "Lệ phí giả định Y-9-1 theo hướng dẫn ở nước ngoài là bao nhiêu?",
    "Does the fictional overseas office guide list a Y-9-1 fee?",
])
def test_an_office_or_document_name_gives_no_location(question):
    assert location(question) is None


@pytest.mark.parametrize("question, where", [
    ("I am overseas. What is the fee for a fictional Y-9-1 re-entry permit?", "abroad"),
    ("가상 Y-9-1 체류자가 해외에 있을 때 재입국허가 수수료는?", "abroad"),
    ("Tôi đang ở nước ngoài, lệ phí giả định Y-9-1 là bao nhiêu?", "abroad"),
    ("A fictional Y-9-1 holder in Korea asks about the re-entry fee.", "domestic"),
])
def test_a_location_of_the_user_is_still_read(question, where):
    assert location(question) == where


def test_a_quoted_document_name_is_not_context_but_the_code_is():
    doc = ev("A", "가상 Y-9-1 처리기간은 15일이다.", "가상 국외체류자 연장 안내(2026년판)")
    q = "가상 국외체류자 연장 안내(2026년판)에 나온 Y-9-1 수수료는 얼마인가요?"
    masked = without_document_names(q, [doc])
    assert "국외" not in masked and "연장" not in masked and "Y-9-1" in masked
    ctx = question_context(q, None, None, DATE, context_question=masked)
    assert ctx["location"] is None and ctx["procedure"] is None and ctx["status_code"] == "Y-9-1"
    assert requested_items(masked) == ["fee"]
    # Without the candidate, the same words are read as before.
    assert location(q) == "abroad"


def test_the_overseas_handbook_question_is_split_by_situation_not_narrowed():
    dom = ev("DOM", "국내에 있는 가상 Y-9-1 체류자의 재입국허가 수수료는 30,000원이다.", "가상 Y-9 운영지침(2026년판)")
    abr = ev("ABR", "국외에 있는 가상 Y-9-1 체류자의 재입국허가 관련 수수료는 50,000원이다.", "가상 재외공관 업무편람 제2판")
    reg = synthetic_registry({"DOM": rec(dom, applicant_scope=["domestic"]), "ABR": rec(abr, applicant_scope=["abroad"])}, "t")
    q = "What is the fee for a fictional Y-9-1 re-entry permit, according to the 2026 guideline and the overseas mission handbook (2nd edition)?"
    p = guard.prepare(q, {"question_type": "general"}, [dom, abr], reg, DATE)
    assert p["selection"]["outcome"] == "proceed" and [d["decision"] for d in p["selection"]["decisions"]] == ["admissible"] * 2
    assert [x["location"] for x in p["parts"]] == ["domestic", "abroad"]


# --- the method question ----------------------------------------------------------------------------
@pytest.mark.parametrize("question, asked", [
    ("How can a fictional T-5-1 holder apply for a change of workplace, and what is the fee?", ["fee", "method"]),
    ("How do fictional Y-9-1 family members apply?", ["method"]),
    ("How can I apply?", ["method"]),
    ("How can a fictional Y-9-1 holder who is not registered apply?", []),   # seven words between: past the bound
    ("How long can a fictional Y-9-1 holder stay?", []),
])
def test_how_can_several_words_apply_asks_for_the_method(question, asked):
    assert [i for i in requested_items(question) if i in ("fee", "method")] == asked


# --- ages are not periods -----------------------------------------------------------------------------
AGE = ev("AGE", "가상 Y-9-1 체류자 중 만 17세 이상인 사람은 입국한 날부터 90일 이내에 외국인등록을 하여야 한다.", "가상 운영지침(2026년판)")
AGE_REG = synthetic_registry({"AGE": rec(AGE, procedures=["registration"])}, "t")
AGE_Q = "Must a fictional Y-9-1 holder register as a foreigner?"


@pytest.mark.parametrize("question, text", [
    (AGE_Q, "A fictional Y-9-1 holder who is 17 years of age or older must register within 90 days of entry."),
    (AGE_Q, "Holders aged 17 or over must register within 90 days of entry."),
    ("가상 Y-9-1 체류자는 외국인등록을 해야 하나요?", "만 17세 이상이면 입국한 날부터 90일 이내에 외국인등록을 해야 합니다."),
    ("Người giả định Y-9-1 có phải đăng ký người nước ngoài không?",
     "Người từ 17 tuổi trở lên phải đăng ký trong vòng 90 ngày kể từ ngày nhập cảnh."),
])
def test_an_age_is_not_compared_as_a_period(question, text):
    out = claims.check(text, question, [AGE], ["AGE"], {"AGE": True}, with_source=True, ages_apart=True)
    assert out["result"] == "no_contradiction_found", out
    r = guard.run_case(question, {"question_type": "general"}, [AGE], AGE_REG, DATE, lambda item: answer("answered", text, ["AGE"]))
    assert r["guard"]["decision"] == "release"


def test_the_default_keeps_the_old_reading_and_a_wrong_period_is_still_caught():
    text = "A fictional Y-9-1 holder who is 17 years of age or older must register within 90 days of entry."
    assert claims.check(text, AGE_Q, [AGE], ["AGE"], {"AGE": True}, with_source=True)["result"] == "contradiction"
    wrong = text.replace("90 days", "30 days")
    assert claims.check(wrong, AGE_Q, [AGE], ["AGE"], {"AGE": True}, with_source=True, ages_apart=True)["result"] == "contradiction"
    assert claims.check("Register within 17 years.", AGE_Q, [AGE], ["AGE"], {"AGE": True},
                        with_source=True, ages_apart=True)["result"] == "contradiction"


# --- the opening language request ------------------------------------------------------------------
@pytest.mark.parametrize("question, model_question, removed", [
    ("Using Korean, list the documents a fictional Y-9-1 holder must submit for an extension.",
     "list the documents a fictional Y-9-1 holder must submit for an extension.", ["Using Korean"]),
    ("In Vietnamese, explain how a fictional Y-9-1 holder registers.",
     "explain how a fictional Y-9-1 holder registers.", ["In Vietnamese"]),
])
def test_an_opening_request_before_an_imperative_is_removed(question, model_question, removed):
    out = guard.question_for_model(question, [])
    assert (out["question"], out["language_removed"]) == (model_question, removed)


@pytest.mark.parametrize("question", [
    "In Korean, what is the name of the fictional Y-9-1 registration form?",
    "Documents in Korean, list them if a fictional Y-9-1 holder needs translations?",
    "Is a document in Korean, please note, needed for a hypothetical Y-9-1 extension?",
])
def test_neighbours_keep_their_question(question):
    out = guard.question_for_model(question, [])
    assert out["question"] == question and out["language_removed"] == []


# --- contract v11 and gate v9 ----------------------------------------------------------------------------
def test_v11_changes_only_the_conflict_line():
    assert "v11" in CONTRACT_VERSIONS and guard.CONTRACT_VERSION in ("v11", "v12", "v13", "v14", "v15")   # 005-P: v12, 005-R: v13, 005-T: v14, 005-U: v15
    v10, v11 = SYSTEM_PROMPTS["v10"].splitlines(), SYSTEM_PROMPTS["v11"].splitlines()
    changed = [(a, b) for a, b in zip(v10, v11) if a != b]
    assert len(v10) == len(v11) and len(changed) == 1
    assert changed[0][0].startswith("- conflict:") and changed[0][1] == changed[0][0] + \
        " This is a conflict even when the question asks what each document says."
    assert parse_response(answer("conflict", "x", ["A", "B"]), {"A", "B"}, "v11")["status"] == "conflict"
    with pytest.raises(ValueError):
        parse_response(answer("conflict", "x", ["A"]), {"A", "B"}, "v11")


def test_gate_v9_keeps_the_v8_categories_and_changes_only_claim_support_in_scoring():
    import synthetic_safety_gate_v8 as gate8
    import synthetic_safety_gate_v9 as gate9
    assert gate9.CATEGORIES == gate8.CATEGORIES and gate9.CRITICAL_KINDS == gate8.CRITICAL_KINDS
    assert gate9.MANIFEST.name == "mission005n_acceptance_manifest.json"
    src8 = (BOOT / "synthetic_safety_gate_v8.py").read_text(encoding="utf-8")
    src9 = (BOOT / "synthetic_safety_gate_v9.py").read_text(encoding="utf-8")
    body = lambda s: s[s.index("def raw_channel"):s.index("def offline_preconditions")]
    assert body(src9) == body(src8).replace("with_source=True)", "with_source=True,\n                                           ages_apart=True)")


# --- the four 005-M cases, pre-inference only ---------------------------------------------------------
def test_the_005m_cases_now_read_as_the_spec_says():
    suite = json.loads((BOOT / "validation" / "mission005m_synthetic_acceptance.json").read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in suite["cases"]}
    prepared = {cid: guard.prepare(cases[cid]["question"], cases[cid]["intake"], cases[cid]["evidence"],
                                   synthetic_registry(cases[cid]["registry"], "t"), suite["evaluation_date"])
                for cid in ("A05M-45", "A05M-48", "A05M-74")}
    assert prepared["A05M-45"]["question_language_requests_removed"] == ["Using Korean"]
    assert prepared["A05M-48"]["selection"]["outcome"] == "proceed" and prepared["A05M-48"]["selection"]["uncovered_items"] == ["fee"]
    assert [p["location"] for p in prepared["A05M-74"]["parts"]] == ["domestic", "abroad"]
    for cid, c in cases.items():   # nothing else in the 005-M suite changes before inference
        sel = guard.prepare(c["question"], c["intake"], c["evidence"], synthetic_registry(c["registry"], "t"),
                            suite["evaluation_date"])["selection"]
        assert sel["outcome"] == c["expected"]["pre_inference"], cid
