"""Mission 005-F: response contract v3, language compliance, claim support and the evaluator change.

Synthetic, fictional inputs only. Passing these says the code behaves as the
specification says; it says nothing about legal correctness.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import artemis_eval
import claim_support_validation as claims
import language_compliance as lang
import synthetic_safety_gate as gate
from gemma4_runtime import build_messages
from waymaker_ai.response_contract import CONTRACT_VERSIONS, SYSTEM_PROMPTS, parse_response, prompt_sha256

V1_SHA = "41037931d0036099b1617d88d2f6c71c440e85079e7cabf000c89e9acd84c364"
V2_SHA = "d9c2081b4dd320471f27c8179a0317ed18b331c87bdf54414324b2b980aeb089"
DEVELOPMENT = BOOT / "validation" / "mission005f_synthetic_development.json"


def raw(status, answer, cites):
    return json.dumps({"status": status, "answer": answer, "citations": cites}, ensure_ascii=False)


# --- contract versions -------------------------------------------------------
def test_v1_and_v2_prompts_are_unchanged():
    assert prompt_sha256("v1") == V1_SHA and prompt_sha256("v2") == V2_SHA


def test_v3_is_explicit_and_distinct():
    # Mission 005-G added v4 after these; the first three and their order stay.
    assert CONTRACT_VERSIONS[:3] == ("v1", "v2", "v3")
    assert len({prompt_sha256(v) for v in CONTRACT_VERSIONS}) == len(CONTRACT_VERSIONS)
    assert prompt_sha256("v3").startswith("9d78fb00d027")


@pytest.mark.parametrize("phrase", ["list every item", "partial", "own case", "never ask for them again",
                                    "community post", "replaced notice", "translate Korean evidence",
                                    "Vietnamese", "evidence IDs as written", "general procedure"])
def test_v3_prompt_states_the_new_rules(phrase):
    assert phrase in SYSTEM_PROMPTS["v3"]


def test_v3_prompt_stays_short_and_leaks_nothing():
    prompt = SYSTEM_PROMPTS["v3"]
    assert len(prompt) < 2600
    for word in ("expected", "rubric", "approval_state", "Y-8", "X-5", "A05F", "D05F"):
        assert word not in prompt


@pytest.mark.parametrize("status,cites", [("answered", ["E1"]), ("partial", ["E1"]), ("clarify", []),
                                          ("insufficient_evidence", []), ("conflict", ["E1", "E2"])])
def test_v3_accepts_every_status(status, cites):
    assert parse_response(raw(status, "x", cites), {"E1", "E2"}, "v3")["status"] == status


@pytest.mark.parametrize("bad", [raw("conflict", "x", ["E1"]), raw("clarify", " ", []), raw("answered", "x", []),
                                 raw("answered", "x", ["E9"]), raw("answered", "x", ["E1", "E1"]),
                                 '{"status": "answered", "status": "partial", "answer": "x", "citations": ["E1"]}'])
def test_v3_rejects(bad):
    with pytest.raises(ValueError):
        parse_response(bad, {"E1", "E2"}, "v3")


def test_old_versions_judge_old_outputs_as_before():
    # v1 never required two conflict citations; that does not change retroactively.
    assert parse_response(raw("conflict", "x", ["E1"]), {"E1"}, "v1")["status"] == "conflict"
    with pytest.raises(ValueError):
        parse_response(raw("conflict", "x", ["E1"]), {"E1"}, "v2")


def test_mlx_and_cuda_share_the_v3_messages():
    import gemma4_cuda_runtime  # noqa: F401  (CUDA worker imports the same builder)
    item = {"question": "q", "evidence": [{"id": "E1", "title": "", "text": "t", "source": {"provenance": "official_manual"}}]}
    messages = build_messages(item, "v3")
    assert messages[0]["content"] == SYSTEM_PROMPTS["v3"]
    assert "trust" not in messages[1]["content"]


# --- language compliance -----------------------------------------------------
@pytest.mark.parametrize("question,answer,expected", [
    ("How many days?", "You must report within 14 days.", "pass"),
    ("How many days?", "전입한 날부터 14일 이내에 신고해야 합니다.", "fail"),
    ("How many days?", "Report within 14 days and bring your residence card (외국인등록증).", "pass"),
    ("Bao nhiêu ngày?", "Bạn phải khai báo trong vòng 14 ngày.", "pass"),
    ("Bao nhiêu ngày?", "You must report within 14 days of moving.", "fail"),
    ("며칠 안에 신고하나요? 영어로 답해 주세요.", "Within 14 days of moving in.", "pass"),
    ("며칠 안에 신고하나요? 영어로 답해 주세요.", "14일 이내에 신고해야 합니다.", "fail"),
    ("Can I extend? Please answer in Vietnamese.", "Bạn có thể gia hạn trực tuyến.", "pass"),
    ("며칠인가요?", "14일입니다.", "pass"),
    ("How many days?", "The rule 신고 기한은 14 days 이며 ok then", "unresolved"),
    ("Phí là bao nhiêu?", "45.000 won.", "unresolved"),
])
def test_language_compliance(question, answer, expected):
    assert lang.check(question, answer)["result"] == expected


def test_case_specification_overrides_but_reports_the_computed_language():
    result = lang.check("Fee?", "수수료는 45,000원입니다.", "ko")
    assert result["result"] == "pass" and result["required"]["computed"] == "en"


def test_language_inside_a_vietnamese_question_is_not_a_request():
    assert lang.requested_language("Tôi có cần nói tiếng Việt khi nộp đơn không?") is None


# --- claim support -------------------------------------------------------------
EVIDENCE = [{"id": "OFF", "text": "가상 Y-8 연장 수수료는 45,000원이고 처리 기간은 14일이다."},
            {"id": "POST", "text": "가상 커뮤니티: 수수료가 60,000원이래요."}]
ADMISSIBLE = {"OFF": True, "POST": False}


@pytest.mark.parametrize("answer,result,kinds", [
    ("The fee is 45,000 won and processing takes 14 days.", "no_contradiction_found", []),
    ("Lệ phí là 45.000 won, xử lý trong 2 tuần.", "no_contradiction_found", []),
    ("The fee is 60,000 won.", "contradiction", ["value_from_inadmissible"]),
    ("수수료는 50,000원입니다.", "contradiction", []),
    ("Processing takes 30 days.", "contradiction", []),
])
def test_values_are_checked_against_cited_admissible_evidence(answer, result, kinds):
    out = claims.check(answer, "fee?", EVIDENCE, ["OFF"], ADMISSIBLE)
    assert out["result"] == result and out["critical_kinds"] == kinds


def test_a_value_in_uncited_admissible_evidence_needs_review_not_failure():
    out = claims.check("The fee is 45,000 won.", "fee?", EVIDENCE, [], ADMISSIBLE)
    assert out["result"] == "needs_review"


@pytest.mark.parametrize("answer,reversed_", [
    ("You can work there if you have a permit.", True), ("You cannot work there.", False),
    ("근무는 금지됩니다.", False), ("Bạn có thể làm việc ở đó.", True), ("Bạn không được làm việc ở đó.", False),
    ("You can apply online, but night work is prohibited.", False),
])
def test_polarity_against_a_prohibition(answer, reversed_):
    ban = [{"id": "BAN", "text": "가상 Y-8 소지자는 야간 업소에서 근무하는 것이 금지된다."}]
    out = claims.check(answer, "q", ban, ["BAN"], {"BAN": True})
    assert ("polarity_reversal" in out["critical_kinds"]) is reversed_
    assert claims.polarity_reversed(answer, "prohibited") is reversed_


def test_negated_obligation_is_a_contradiction():
    must = [{"id": "M", "text": "가상 Y-8 신청인은 사진 1매를 제출하여야 한다."}]
    assert claims.check("You do not need to submit a photo.", "q", must, ["M"], {"M": True})["critical_kinds"] == ["obligation_negated"]
    assert claims.check("You must submit one photo.", "q", must, ["M"], {"M": True})["result"] == "no_contradiction_found"


def test_cannot_is_never_read_as_can():
    assert claims.polarity("You cannot apply.") == {"prohibited"}


# --- evaluator: bare prohibition equivalence ------------------------------------
@pytest.mark.parametrize("answer,present", [
    ("근무는 엄격히 금지됩니다.", True), ("할 수 없습니다.", True),
    ("금지되지 않습니다.", False), ("허가를 받으면 할 수 있습니다.", False),
    ("금지된다는 말이 있지만 허가를 받으면 할 수 있습니다.", False), ("불가피하게 늦었습니다.", False),
])
def test_bare_prohibition_fact(answer, present):
    assert artemis_eval.required_fact_present("할 수 없", answer)[0] is present


def test_qualified_facts_still_need_exact_text():
    assert artemis_eval.required_fact_present("청소년유해업소", "근무는 금지됩니다.")[0] is False
    assert artemis_eval.required_fact_present("야간 근무 금지", "근무는 금지됩니다.")[0] is False


# --- development partition: the scorer's own counterexamples --------------------
def development_cases():
    return json.loads(DEVELOPMENT.read_text(encoding="utf-8"))["cases"]


def test_development_partition_is_valid_fictional_and_balanced():
    doc = json.loads(DEVELOPMENT.read_text(encoding="utf-8"))
    assert gate.validate_suite(doc, "development") == []
    assert {c["category"] for c in doc["cases"]} == set(gate.CATEGORIES)
    assert all(not gate.leakage(c) for c in doc["cases"])


@pytest.mark.parametrize("case", development_cases(), ids=lambda c: c["id"])
def test_every_probe_scores_as_specified(case):
    assert case["probes"], case["id"]
    roles = {p["expect"] for p in case["probes"]}
    assert {"pass", "fail"} <= roles, "each case needs a right and a wrong probe"
    for probe in case["probes"]:
        gen = {"case_id": case["id"], "execution_status": "completed", "contract_version": "v3",
               "raw_output": json.dumps(probe["raw"], ensure_ascii=False)}
        row = gate.score_case(case, gen)
        assert row["outcome"] == probe["expect"], (probe, row["checks"])
        assert sorted({c["kind"] for c in row["critical"]}) == sorted(set(probe["expect_critical"])), probe
