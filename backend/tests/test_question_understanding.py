"""Provider results must not undo explicit negation or turn plans into facts."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.enforcement_service import extract_structured_case


def test_ai_cannot_turn_planned_report_and_denied_investigation_into_completed_events():
    async def provider(_):
        return {"statusOfStay": "D-2", "voluntaryDisclosure": True, "investigationStarted": True}

    result = asyncio.run(extract_structured_case(
        "D-2로 허가 없이 알바했어요. 자진신고할 예정입니다. 조사는 받지 않았어요.", provider=provider,
    ))
    assert result.voluntary_disclosure is None
    assert result.investigation_started is False
    assert "자진신고 여부" in result.unknown_facts


def test_denied_work_does_not_call_ai_to_invent_a_violation():
    async def provider(_):
        raise AssertionError("explicitly denied work must not be reconstructed by a model")

    result = asyncio.run(extract_structured_case("D-2로 허가 없이 일한 적 없어요.", provider=provider))
    assert result.violation_code is None
    assert result.violation_candidates == []
    assert not result.extraction_warnings


def test_hypothetical_work_is_not_an_actual_violation():
    result = asyncio.run(extract_structured_case("D-2로 허가 없이 알바하면 어떻게 되나요?"))
    assert result.violation_code is None
    assert result.authorization_obtained is None


def test_repeated_status_notation_does_not_create_a_second_status():
    result = asyncio.run(extract_structured_case("D2인데 D-2로 허가 없이 10일 알바했어요."))
    assert result.status_of_stay == "D-2"


def test_model_cannot_silently_join_distinct_violation_periods():
    async def provider(_):
        return {"statusOfStay": "D-2", "durationDays": 30, "violationStartDate": "2026-01-01", "violationEndDate": "2026-01-30"}

    result = asyncio.run(extract_structured_case(
        "D-2 허가 없이 10일 일했고 다른 회사에서 20일 근무했어요.", provider=provider,
    ))
    assert result.duration_days is None
    assert result.violation_start_date is None
    assert result.violation_end_date is None
    assert "위반기간" in result.unknown_facts


def test_model_cannot_choose_an_unstated_offense_time_status():
    async def provider(_):
        return {"statusOfStay": "E-7"}

    result = asyncio.run(extract_structured_case(
        "D-2에서 E-7로 바꿨는데 허가 없이 10일 일한 일로 조사받아요.", provider=provider,
    ))
    assert result.status_of_stay is None
    assert "체류자격" in result.unknown_facts
