"""Mission 005-E evaluator repairs E1-E3: false positives removed, true positives kept.

Every sentence here is freshly written synthetic text, not taken from the DEV-20
cases, so the repairs are checked against independent counterexamples.
"""
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import artemis_eval
import trust_gate

# --- E1: permission reversal ------------------------------------------------
EV_BAN = "외국인 연수생은 연수 허가를 받은 경우라도 야간 유흥업소에서 근무하는 것이 엄격히 금지됩니다."


@pytest.mark.parametrize("answer", [
    "연수 허가를 받았더라도 야간 유흥업소 근무는 엄격히 금지됩니다.",
    "연수생이 연수 허가를 받은 경우에도 야간 유흥업소에서 근무하는 것은 금지되어 있습니다.",
])
def test_e1_restated_prohibition_is_not_flagged(answer):
    assert trust_gate.permission_flips(answer, EV_BAN) == []


@pytest.mark.parametrize("answer", [
    "연수생은 연수 허가를 받았더라도 야간 유흥업소에서 근무할 수 있습니다.",
    "연수 허가를 받은 연수생은 야간 유흥업소 근무도 가능합니다.",
    "연수생은 야간 유흥업소가 금지 대상이 아니므로 연수 허가를 받아 근무할 수 있습니다.",
])
def test_e1_real_reversals_are_still_flagged(answer):
    assert trust_gate.permission_flips(answer, EV_BAN)


def test_e1_possible_sanction_is_not_a_permission():
    answer = "이를 어기면 연수 허가 취소 및 출국조치 대상이 될 수 있습니다."
    assert trust_gate.permission_flips(answer, EV_BAN) == []


def test_e1_permission_phrased_with_could_is_still_flagged():
    assert trust_gate.permission_flips("연수생은 연수 허가를 받으면 야간 유흥업소에서 일할 수 있습니다.", EV_BAN)


# --- E2: role swap ------------------------------------------------------------
EV_PHOTO = "등록증 재교부 신청 시 신청서와 함께 3개월 이내에 촬영한 사진 1매 및 재발급 수수료 20,000원을 제출하여야 합니다."
EV_ISSUE = "등록증은 신청한 뒤 3개월 이내에 발급됩니다."


def test_e2_fee_name_is_not_the_role_of_a_period():
    answer = "재교부를 신청할 때는 3개월 이내에 촬영한 사진 1매를 제출해야 합니다."
    assert trust_gate.role_mismatches(answer, EV_PHOTO) == []


@pytest.mark.parametrize("answer", [
    "등록증은 3개월 이내에 신청해야 합니다.",
    "등록증 신청은 3개월 이내에 제출해야 합니다.",
])
def test_e2_issue_deadline_read_as_filing_deadline_is_still_flagged(answer):
    assert trust_gate.role_mismatches(answer, EV_ISSUE)


def test_e2_money_still_reads_its_fee_noun():
    assert trust_gate.role_mismatches("재발급 수수료는 20,000원입니다.", EV_PHOTO) == []
    assert trust_gate.role_mismatches("소득 기준은 20,000원입니다.", EV_PHOTO)


# --- E3: required facts -----------------------------------------------------
@pytest.mark.parametrize("fact,answer", [
    ("종전 기준은 폐기", "종전 기준은 완전히 폐기되었습니다."),
    ("서류를 제출", "서류를 반드시 제출해야 합니다."),
    ("사전 허가", "사전 허가가 필요합니다."),
])
def test_e3_harmless_wording_is_accepted(fact, answer):
    present, _ = artemis_eval.required_fact_present(fact, answer)
    assert present


@pytest.mark.parametrize("fact,answer", [
    ("종전 기준은 폐기", "종전 기준은 완전히 폐기되지 않았습니다."),   # negation after normalization
    ("3개월 이내", "6개월 이내에 신청합니다."),                        # wrong number
    ("반드시 제출", "제출하면 됩니다."),                                # obligation dropped
    ("D-2-2", "D-2-1로 신청합니다."),                                  # wrong status code
    ("사전 허가", "사후 신고로 충분합니다."),                            # changed procedure
    ("종전 기준은 폐기", "종전 기준은 즉시 폐기되었습니다."),            # non-whitelisted word stays a miss
])
def test_e3_material_changes_still_fail(fact, answer):
    present, _ = artemis_eval.required_fact_present(fact, answer)
    assert not present


def test_e3_scorer_reports_normalized_matches_transparently():
    item = {"evidence": [], "expected": {"source_fidelity": {"required_facts": ["종전 기준은 폐기"]}}}
    score = artemis_eval.score_source_fidelity(item, {"status": "answered", "answer": "종전 기준은 완전히 폐기되었습니다.",
                                                      "citations": []})
    assert score.passed and score.details["normalized_fact_matches"] == ["종전 기준은 폐기"]
