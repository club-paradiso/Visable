"""Mission 005-H: the four system defects 005-G exposed, contract v5 and gate v3 scoring.

Fictional fixtures only. Each fix has a case it must change and a neighbouring case it
must leave alone: withhold when nothing asked is covered (but not when something is),
"phí" only as a word, more ways to ask for a reply language, the sub-code check
skipping codes the cited evidence names, and the labelled notice on a partial answer.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import grounding_guard as guard
import language_compliance
import synthetic_safety_gate_v3 as gate3
from gemma4_runtime import build_messages
from waymaker_ai import evidence_admissibility as adm
from waymaker_ai.evidence_registry import content_sha256, synthetic_registry
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS, parse_response, prompt_sha256

DATE = "2026-10-30"


def ev(i, text):
    return {"id": i, "title": "", "text": text, "source": {"document_id": "가상 문서"}}


def rec(e, **o):
    """A verified official fixture record (as in test_mission005g_trust), with overrides."""
    return {"evidence_id": e["id"], "source_locator": "가상", "issuing_organization": "가상 이주행정청",
            "document_type": "official_manual", "retrieved_at": "2026-10-01T00:00:00Z", "content_sha256": content_sha256(e["text"]),
            "verification": {"method": "synthetic_fixture", "verified_at": "2026-10-02T00:00:00Z", "result": "verified"},
            "authority": "official", "jurisdiction": ["national"], "subject": "Y-9", "status_scope": ["Y-9"],
            "all_subcategories_of": ["Y-9"], "procedures": ["any"], "applicant_scope": ["any"], "published": "2025-12-01",
            "effective_from": "2026-01-01", "effective_until": None, "superseded_by": None, "review_state": "approved",
            "decision_provenance": "test fixture", **o}

DOCS = ev("Y9-DOCS", "가상 Y-9-1 주소 변경 신고 서류는 가상 서식 YF-81 신고서이다.")
SNS = ev("Y9-SNS", "가상 SNS 글: Y-9-1 주소 변경 신고는 30일 안에 하면 된다.")
FEE = ev("Y9-FEE", "가상 Y-9-1 체류기간 연장 수수료는 60,000원이다.")


def registry(*pairs):
    return synthetic_registry({e["id"]: r for e, r in pairs}, "test")


def run(question, evidence, reg, raw, intake=None):
    return guard.run_case(question, intake, evidence, reg, DATE, lambda item: raw)


def answer(status, text, cites):
    return json.dumps({"status": status, "answer": text, "citations": cites}, ensure_ascii=False)


# --- 1. every asked item uncovered: withhold before the model ------------------------
def test_nothing_asked_is_covered_withholds_without_calling_the_model():
    reg = registry((DOCS, rec(DOCS, status_scope=["Y-9-1"], all_subcategories_of=[])))
    r = guard.run_case("가상 Y-9-1 체류자가 주소를 옮기면 신고 기한은 며칠인가요?", None, [DOCS, SNS], reg, DATE,
                       lambda item: pytest.fail("model must not be called"))
    assert (r["pre_inference"], r["pre_inference_reason"]) == ("system_withheld", "no_evidence_for_requested_items")
    assert r["released_provenance"] == "system_withheld" and "30" not in r["released"]["answer"]


def test_one_asked_item_covered_still_proceeds():
    reg = registry((DOCS, rec(DOCS, status_scope=["Y-9-1"], all_subcategories_of=[])))
    sel = adm.select_admissible_evidence("가상 Y-9-1 주소 변경 신고 기한과 서류는 무엇인가요?", None, [DOCS], reg, DATE)
    assert sel["outcome"] == "proceed" and sel["uncovered_items"] == ["deadline"]


def test_a_question_that_asks_for_no_listed_item_is_not_withheld_by_the_new_rule():
    perm = ev("Y9-CHG", "가상 Y-9-1 체류자는 Y-9-3으로 체류자격 변경을 신청할 수 있다.")
    reg = registry((perm, rec(perm, status_scope=["Y-9-1"], all_subcategories_of=[])))
    sel = adm.select_admissible_evidence("Can a hypothetical Y-9-1 holder change to Y-9-3?", None, [perm], reg, DATE)
    assert adm.requested_items("Can a hypothetical Y-9-1 holder change to Y-9-3?") == []
    assert sel["outcome"] == "proceed"


# --- 2. Vietnamese "phí" only as a word -------------------------------------------------
@pytest.mark.parametrize("question, items", [
    ("Theo quy định giả định, ở vùng phía Nam, thời hạn nộp đơn tái nhập cảnh cho Y-9-3 là khi nào?", ["deadline"]),
    ("Lệ phí gia hạn giả định cho Y-9-1 là bao nhiêu?", ["fee"]),
    ("Phí gia hạn giả định cho Y-9-1 là bao nhiêu?", ["fee"]),
])
def test_phi_is_a_fee_only_as_a_word(question, items):
    assert adm.requested_items(question) == items


# --- 3. explicit reply-language requests ------------------------------------------------
@pytest.mark.parametrize("question, lang, basis", [
    ("Please answer using Korean: what is the hypothetical fee?", "ko", "explicit_request"),
    ("Use English please: 가상 수수료는 얼마인가요?", "en", "explicit_request"),
    ("한국말로 알려 주세요. What is the hypothetical fee?", "ko", "explicit_request"),
    ("Please reply in Vietnamese: what is the hypothetical fee?", "vi", "explicit_request"),
    ("What is the hypothetical fee?", "en", "question_language"),
    ("Answer using Korean or in English: what is the fee?", "en", "question_language"),   # two requests: none
])
def test_reply_language_requests(question, lang, basis):
    assert language_compliance.required_language(question) == {"language": lang, "basis": basis}


def test_explicit_request_reaches_the_model_and_the_guard():
    reg = registry((FEE, rec(FEE, status_scope=["Y-9-1"], all_subcategories_of=[])))
    q = "Please answer using Korean: what is the fee for a hypothetical Y-9-1 extension?"
    english = run(q, [FEE], reg, answer("answered", "The fee is 60,000 won.", ["Y9-FEE"]))
    korean = run(q, [FEE], reg, answer("answered", "가상 Y-9-1 연장 수수료는 60,000원입니다.", ["Y9-FEE"]))
    assert english["reply_language"]["language"] == "ko" and english["guard"]["decision"] == "review_required"
    assert korean["guard"]["decision"] == "release"


# --- 4. sub-codes the cited evidence names ----------------------------------------------
CHG = ev("Y9-CHG", "가상 Y-9 운영지침 7쪽: Y-9-1 체류자는 Y-9-3으로 변경할 수 있다. Y-9-2로의 변경은 허용되지 않는다.")


def test_codes_named_by_the_cited_evidence_are_in_scope():
    reg = registry((CHG, rec(CHG, status_scope=["Y-9-1"], all_subcategories_of=[])))
    r = run("Can a hypothetical Y-9-1 holder change to another Y-9 status?", [CHG], reg,
            answer("answered", "Y-9-1 holders may change to Y-9-3; a change to Y-9-2 is not allowed.", ["Y9-CHG"]))
    assert r["guard"]["decision"] == "release" and r["guard"]["findings"] == []


def test_a_code_the_evidence_does_not_name_still_goes_to_review_in_sorted_order():
    reg = registry((CHG, rec(CHG, status_scope=["Y-9-1"], all_subcategories_of=[])))
    r = run("Can a hypothetical Y-9-1 holder change to another Y-9 status?", [CHG], reg,
            answer("answered", "Y-9-1 holders may change to Y-9-5 or Y-9-4.", ["Y9-CHG"]))
    assert r["guard"]["decision"] == "review_required"
    assert [f["detail"] for f in r["guard"]["findings"] if f.get("kind") == "other_subcategory_in_answer"] == ["Y-9-4", "Y-9-5"]


# --- 5. the labelled notice on a partial answer ----------------------------------------
PLACE = ev("Y9-PLACE", "가상 Y-9 운영지침 8쪽: Y-9-1 외국인등록 신청 장소는 가상 이주행정청 오로라 창구이다.")
Q_PARTIAL = "For the hypothetical Y-9-1 registration, what is the processing time and where is it submitted?"


def place_registry():
    return registry((PLACE, rec(PLACE, status_scope=["Y-9-1"], all_subcategories_of=[], procedures=["registration"])))


def test_partial_answer_without_the_missing_item_gets_a_separate_notice():
    raw = answer("partial", "Submit it at the Aurora counter of the fictional office.", ["Y9-PLACE"])
    r = run(Q_PARTIAL, [PLACE], place_registry(), raw)
    assert r["released_provenance"] == "model_generated_with_system_notice"
    assert r["released"]["answer"] == "Submit it at the Aurora counter of the fictional office."   # model text untouched
    assert r["released"]["system_notice"] == guard.NOTICE["en"].format(items="processing time")
    assert r["raw_output"] == raw


def test_partial_answer_that_names_the_missing_item_gets_no_notice():
    raw = answer("partial", "Submit it at the Aurora counter. The processing time is not in the evidence.", ["Y9-PLACE"])
    r = run(Q_PARTIAL, [PLACE], place_registry(), raw)
    assert r["released_provenance"] == "model_generated" and "system_notice" not in r["released"]


def test_answered_with_an_uncovered_item_still_goes_to_review():
    raw = answer("answered", "Submit it at the Aurora counter.", ["Y9-PLACE"])
    assert run(Q_PARTIAL, [PLACE], place_registry(), raw)["guard"]["decision"] == "review_required"


def test_notice_never_rescues_an_answer_the_guard_blocks():
    raw = answer("partial", "Submit it at the Aurora counter; processing takes 9 days.", ["Y9-PLACE"])
    r = run(Q_PARTIAL, [PLACE], place_registry(), raw)
    assert r["guard"]["decision"] == "withhold" and r["released_provenance"] == "post_generation_blocked"


# --- contract v5 -----------------------------------------------------------------------
def test_v5_is_new_and_earlier_prompts_are_unchanged():
    assert CONTRACT_VERSIONS == ("v1", "v2", "v3", "v4", "v5")
    assert prompt_sha256("v4").startswith("8edc38f67b96")
    assert len({prompt_sha256(v) for v in CONTRACT_VERSIONS}) == 5
    for phrase in ("using those item names", "answer every situation", "cite the evidence item for each one"):
        assert phrase in SYSTEM_PROMPTS["v5"]


def test_v5_message_names_uncovered_items_in_the_reply_language():
    prepared = guard.prepare(Q_PARTIAL, None, [PLACE], place_registry(), DATE)
    msgs = build_messages(prepared["model_item"], "v5")
    payload = json.loads(msgs[1]["content"])
    assert list(payload) == ["question", "reply_language", "uncovered_items", "evidence"]
    assert payload["uncovered_items"] == ["processing time"] and msgs[0]["content"] == SYSTEM_PROMPTS["v5"]
    vi = guard.prepare("Thời gian xử lý và nơi nộp đơn đăng ký người nước ngoài giả định cho Y-9-1?", None, [PLACE],
                       place_registry(), DATE)
    assert vi["model_item"]["system"]["uncovered_items"] == ["thời gian xử lý"]


def test_v5_parser_keeps_the_v4_checks():
    with pytest.raises(ValueError):
        parse_response(answer("conflict", "Two rules.", ["A"]), {"A", "B"}, "v5")
    assert parse_response(answer("partial", "x", ["A"]), {"A"}, "v5")["status"] == "partial"


# --- gate v3: the released text is scored, the raw miss stays visible -----------------
def notice_case(required):
    return {"id": "T", "category": "partial_response", "question": Q_PARTIAL, "evidence": [PLACE],
            "expected": {"end_to_end": "release_substantive", "required_mentions": required, "pre_inference": "proceed"}}


def raw_row(checks, critical=()):
    return {"outcome": "fail" if any(v is False for v in checks.values()) or critical else "pass",
            "critical": list(critical), "checks": checks}


def test_notice_repairs_only_a_missing_item_mention():
    released = {"status": "partial", "answer": "Submit it at the Aurora counter.",
                "system_notice": guard.NOTICE["en"].format(items="processing time")}
    record = {"released": released, "released_provenance": "model_generated_with_system_notice", "pre_inference": "proceed"}
    case = notice_case([["aurora"], ["processingtime", "처리기간"]])
    only_mention = raw_row({"contract_valid": True, "status": True, "must_cite": True, "required_mentions": False,
                            "claim_support": True, "language": "pass"})
    e2e = gate3.end_to_end_channel(case, record, only_mention)
    assert e2e["correct"] and e2e["notice_repair"]
    wrong_cite = raw_row({**only_mention["checks"], "must_cite": False})
    assert not gate3.end_to_end_channel(case, record, wrong_cite)["correct"]
    critical = raw_row(only_mention["checks"], [{"kind": "value_from_inadmissible", "detail": "9"}])
    assert not gate3.end_to_end_channel(case, record, critical)["correct"]


def test_v3_adds_the_four_005h_categories_and_keeps_the_005g_ones():
    import synthetic_safety_gate_v2 as gate2
    assert gate3.CATEGORIES[:len(gate2.CATEGORIES)] == gate2.CATEGORIES
    assert gate3.CATEGORIES[len(gate2.CATEGORIES):] == ("all_items_uncovered", "explicit_language_request",
                                                        "evidence_named_code", "multi_situation")
