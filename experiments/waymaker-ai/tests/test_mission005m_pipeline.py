"""Mission 005-M: source fields in claim support, the uncovered sentence (contract v10), two removal fixes.

Fictional fixtures only. A005L-28/29 were withheld because a correct conflict answer named its
source document ("운영지침(2026년판)", a source field the model is shown) and "2026년" was read as
an unsupported period. A05K-41/47 and A05L-42/48 left uncovered items out of partial answers; the
system now gives the model the sentence that names them. Neighbouring cases that must not change
are included.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import claim_support_validation as claims
import grounding_guard as guard
from gemma4_runtime import build_messages
from waymaker_ai.evidence_registry import content_sha256, synthetic_registry
from waymaker_ai.inference_input import project_inference_item
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS, parse_response, prompt_sha256

DATE = "2026-11-01"


def ev(i, text, document_id="가상 문서", title=""):
    return {"id": i, "title": title, "text": text, "source": {"document_id": document_id, "effective_date": "2026-01-01"}}


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


A = ev("PROC-A", "[가상 고시 제12호] 가상 Y-9-1 체류기간 연장 처리기간은 15일이다.", "가상 고시 제12호")
B = ev("PROC-B", "[가상 운영지침 4장] 가상 Y-9-1 체류기간 연장 처리기간은 25일이다.", "가상 운영지침(2026년판)")
CONFLICT = synthetic_registry({"PROC-A": rec(A), "PROC-B": rec(B)}, "t")
Q = "가상 Y-9-1 체류기간 연장 처리기간은 얼마나 걸리나요?"
ANSWER = "가상 고시 제12호에 따르면 15일이고, 가상 운영지침(2026년판)에는 25일이라고 되어 있습니다."


# --- source fields in claim support -------------------------------------------------------
def test_a_value_from_a_cited_document_name_is_not_an_unsupported_claim():
    admissible = {"PROC-A": True, "PROC-B": True}
    old = claims.check(ANSWER, Q, [A, B], ["PROC-A", "PROC-B"], admissible)
    new = claims.check(ANSWER, Q, [A, B], ["PROC-A", "PROC-B"], admissible, with_source=True)
    assert old["result"] == "contradiction"            # 005-F..005-L behaviour, kept as the default
    assert new["result"] == "no_contradiction_found"


def test_the_guard_releases_the_correct_conflict_answer():
    r = guard.run_case(Q, None, [A, B], CONFLICT, DATE, lambda item: answer("conflict", ANSWER, ["PROC-A", "PROC-B"]))
    assert r["guard"]["decision"] == "release" and r["released_provenance"] == "model_generated"


def test_a_wrong_value_is_still_a_mismatch_with_source_fields():
    wrong = "가상 운영지침(2026년판)에 따르면 처리기간은 40일입니다."
    out = claims.check(wrong, Q, [A, B], ["PROC-B"], {"PROC-A": True, "PROC-B": True}, with_source=True)
    assert out["result"] == "contradiction"
    r = guard.run_case(Q, None, [A, B], CONFLICT, DATE, lambda item: answer("answered", wrong, ["PROC-B"]))
    assert r["guard"]["decision"] == "withhold"


def test_a_value_only_in_an_inadmissible_document_name_stays_inadmissible():
    bad = ev("PROC-C", "[가상 블로그] 가상 Y-9-1 연장 처리기간 안내.", "가상 블로그 30일 처리 후기")
    out = claims.check("처리기간은 30일입니다.", Q, [A, bad], ["PROC-A"], {"PROC-A": True, "PROC-C": False}, with_source=True)
    assert "value_from_inadmissible" in out["critical_kinds"]


# --- uncovered_sentence (contract v10) ----------------------------------------------------------
PLACE = ev("PLACE", "가상 Y-9-1 외국인등록은 가상 KX-4 센터에서 신청한다.")
PLACE_REG = synthetic_registry({"PLACE": rec(PLACE)}, "t")


@pytest.mark.parametrize("question, sentence", [
    ("Where does a hypothetical Y-9-1 holder register, and how long does processing take?",
     "Not covered by the verified evidence: processing time."),
    ("가상 Y-9-1 외국인등록은 어디서 하고 수수료와 처리기간은 얼마인가요?", "확인된 근거에 없는 항목: 수수료, 처리기간."),
    ("Theo quy định giả định, người Y-9-1 đăng ký người nước ngoài ở đâu và thời gian xử lý là bao lâu?",
     "Không có trong căn cứ đã xác minh: thời gian xử lý."),
])
def test_partial_items_come_with_the_sentence_in_the_reply_language(question, sentence):
    item = guard.prepare(question, None, [PLACE], PLACE_REG, DATE)["model_item"]
    assert item["system"]["uncovered_sentence"] == sentence
    payload = json.loads(build_messages(item, "v10")[1]["content"])
    assert list(payload) == ["question", "reply_language", "uncovered_items", "uncovered_sentence", "evidence"]


def test_no_sentence_when_nothing_is_uncovered():
    item = guard.prepare("Where does a hypothetical Y-9-1 holder register?", None, [PLACE], PLACE_REG, DATE)["model_item"]
    assert "uncovered_sentence" not in item["system"]
    assert list(json.loads(build_messages(item, "v10")[1]["content"])) == ["question", "reply_language", "uncovered_items", "evidence"]


def test_a_partial_answer_ending_with_the_sentence_needs_no_system_notice():
    q = "Where does a hypothetical Y-9-1 holder register, and how long does processing take?"
    good = "Registration is at the fictional KX-4 centre. Not covered by the verified evidence: processing time."
    r = guard.run_case(q, None, [PLACE], PLACE_REG, DATE, lambda item: answer("partial", good, ["PLACE"]))
    assert r["guard"]["decision"] == "release" and r["released_provenance"] == "model_generated"
    plain = guard.run_case(q, None, [PLACE], PLACE_REG, DATE,
                           lambda item: answer("partial", "Registration is at the fictional KX-4 centre.", ["PLACE"]))
    assert plain["released_provenance"] == "model_generated_with_system_notice"


def test_only_v10_takes_the_sentence_and_it_is_validated():
    item = guard.prepare("Where does a hypothetical Y-9-1 holder register, and how long does processing take?",
                         None, [PLACE], PLACE_REG, DATE)["model_item"]
    for version in ("v5", "v9"):
        with pytest.raises(ValueError):
            build_messages(item, version)
    for bad in ("", "a\nb", "x" * 301, 7):
        with pytest.raises(ValueError):
            project_inference_item({"question": "q", "evidence": [],
                                    "system": {"reply_language": "en", "uncovered_items": [], "uncovered_sentence": bad}})


def test_v10_changes_only_the_inputs_line_and_the_partial_line():
    assert "v10" in CONTRACT_VERSIONS and guard.CONTRACT_VERSION in ("v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17")   # 005-N: v11, 005-P: v12, 005-R: v13, 005-T: v14, 005-U: v15, 005-V: v16, 005-W: v17
    assert prompt_sha256("v9").startswith("807c2b41914a") and len({prompt_sha256(v) for v in CONTRACT_VERSIONS}) == len(CONTRACT_VERSIONS)
    v9, v10 = SYSTEM_PROMPTS["v9"].splitlines(), SYSTEM_PROMPTS["v10"].splitlines()
    changed = [(a, b) for a, b in zip(v9, v10) if a != b]
    assert len(v9) == len(v10) and len(changed) == 2
    assert "uncovered_sentence" in changed[0][1] and "end the answer with uncovered_sentence exactly as given" in changed[1][1]
    assert parse_response(answer("partial", "x. Not covered by the verified evidence: fee.", ["A"]), {"A"}, "v10")["status"] == "partial"


# --- removal fixes ----------------------------------------------------------------------------------
@pytest.mark.parametrize("question, model_question, removed", [
    ("In Korean or in Vietnamese, please: what documents does a hypothetical Y-9-1 holder need?",
     "what documents does a hypothetical Y-9-1 holder need?", ["In Korean or in Vietnamese, please:"]),
    ("가상 Y-9-1 체류자의 고용주가 해야 하는 일은 무엇인가요? 답은 bằng tiếng Việt로 주세요.",
     "가상 Y-9-1 체류자의 고용주가 해야 하는 일은 무엇인가요?", ["답은 bằng tiếng Việt로 주세요."]),
    ("가상 Y-9-1 수수료를 in English로만 알려 주세요.", "가상 Y-9-1 수수료를 알려 주세요.", ["in English로만"]),
])
def test_comma_please_and_glued_particles_are_removed(question, model_question, removed):
    out = guard.question_for_model(question, [])
    assert (out["question"], out["language_removed"]) == (model_question, removed)


@pytest.mark.parametrize("question", [
    "가상 Y-9-1 서류를 tiếng Việt로 번역해야 하나요?",                  # a translation, not a reply request
    "Tôi học tiếng Anh. Lệ phí giả định Y-9-1 là bao nhiêu?",
    "Is a document in Korean, please note, needed for a hypothetical Y-9-1 extension?",
])
def test_neighbours_keep_their_question(question):
    out = guard.question_for_model(question, [])
    assert out["question"] == question and out["language_removed"] == []


def test_gate_v8_keeps_the_v7_categories_and_changes_only_claim_support_in_scoring():
    import synthetic_safety_gate_v7 as gate7
    import synthetic_safety_gate_v8 as gate8
    assert gate8.CATEGORIES == gate7.CATEGORIES and gate8.CRITICAL_KINDS == gate7.CRITICAL_KINDS
    assert gate8.MANIFEST.name == "mission005m_acceptance_manifest.json"
    src7 = (BOOT / "synthetic_safety_gate_v7.py").read_text(encoding="utf-8")
    src8 = (BOOT / "synthetic_safety_gate_v8.py").read_text(encoding="utf-8")
    body = lambda s: s[s.index("def raw_channel"):s.index("def offline_preconditions")]
    assert body(src8) == body(src7).replace("cites, admissible_map)", "cites, admissible_map, with_source=True)")
