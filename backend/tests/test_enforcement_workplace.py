"""Regression tests for the deterministic workplace regime determination.

The 22 shared cases in fixtures/workplace_regime_cases.json are the standard
case library: the same file is replayed against the JS mirror
(lib/enforcement-workplace.js) by scripts/check_enforcement_workplace.mjs,
which is what keeps the frontend fallback and the backend from diverging
(brief case 17). Case numbers in docstrings refer to the mission brief's
23 mandatory regression cases.
"""

from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from services.enforcement_models import StructuredCase
from services.enforcement_rules import calculate_legal_baseline
from services.enforcement_service import _parse_ai_case, extract_structured_case
from services.enforcement_workplace import determine_workplace_regime

FIXTURES = Path(__file__).parent / "fixtures" / "workplace_regime_cases.json"


def _load_cases():
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return data["cases"]


class WorkplaceFixtureTests(unittest.TestCase):
    def test_shared_fixtures(self):
        for entry in _load_cases():
            with self.subTest(case=entry["id"]):
                case = StructuredCase.model_validate(entry["case"])
                det = determine_workplace_regime(case)
                self.assertEqual(det.regime, entry["regime"], entry["description"])
                if "dutyBreach" in entry:
                    self.assertEqual(det.duty_breach, entry["dutyBreach"])
                if "reportTimeliness" in entry:
                    self.assertEqual(det.report_timeliness, entry["reportTimeliness"])
                baseline = calculate_legal_baseline(case)
                self.assertEqual(baseline.status, entry["baselineStatus"])
                self.assertEqual(baseline.baseline_amount_krw, entry["baselineAmountKrw"])
                if entry["regime"] == "REPORT" and entry["baselineStatus"] == "ADMINISTRATIVE_FINE_TRACK":
                    # The criminal-fine table must never price a report case.
                    self.assertIsNone(baseline.baseline_amount_krw)
                    self.assertEqual(baseline.statutory_maximum_krw, 2_000_000)

    def test_no_fixture_ever_guesses_an_amount_when_unresolved(self):
        for entry in _load_cases():
            if entry["regime"] in {"UNRESOLVED", "NOT_APPLICABLE"}:
                case = StructuredCase.model_validate(entry["case"])
                self.assertIsNone(calculate_legal_baseline(case).baseline_amount_krw, entry["id"])


class WorkplaceFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_mission_example_narrative_needs_facts_not_a_guess(self):
        """Brief example: E-7-4 worker moved jobs, never reported, worked 2 months."""
        case = await extract_structured_case(
            "E-7-4 비자로 근무하던 외국인이 기존 회사를 그만두고 다른 회사에 취업했습니다. "
            "출입국에는 별도로 신고하지 않았고 새 회사에서 두 달 동안 일했습니다. 범칙금이 얼마나 나올까요?",
            assessment_date=date(2026, 11, 4),
        )
        self.assertEqual(case.status_of_stay, "E-7-4")
        baseline = calculate_legal_baseline(case)
        self.assertIsNone(baseline.baseline_amount_krw)
        self.assertIsNotNone(baseline.workplace_determination)
        self.assertEqual(baseline.workplace_determination.regime, "UNRESOLVED")
        self.assertIn("실제 직종(직종코드)", baseline.workplace_determination.missing_facts)

    async def test_editing_an_answer_reevaluates_immediately(self):
        """Brief case 16: no cached determination survives an edited fact."""
        case = StructuredCase.model_validate(
            {
                "statusOfStay": "E-7-4",
                "violationCode": "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1",
                "occupationCode": "1234",
                "alienRegistered": True,
                "meetsNewWorkplaceQualifications": True,
                "previousEmploymentEndReason": "RESIGNED_MID_CONTRACT",
                "assessmentDate": "2026-11-04",
            }
        )
        self.assertEqual(determine_workplace_regime(case).regime, "UNRESOLVED")
        case.employer_consent = False
        self.assertEqual(determine_workplace_regime(case).regime, "PERMIT")
        case.employer_consent = True
        self.assertEqual(determine_workplace_regime(case).regime, "REPORT")

    async def test_ai_cannot_set_the_regime(self):
        """Brief case 21: an extractor hallucination cannot classify the case."""
        case = _parse_ai_case(
            {
                "schemaVersion": "1",
                "statusOfStay": "E-7-4",
                "violationCode": "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1",
                "workplaceRegime": "REPORT",
                "workplaceRegimeSource": "ENGINE",
            }
        )
        self.assertIsNone(case.workplace_regime)
        self.assertIsNone(case.workplace_regime_source)

    async def test_pii_in_narrative_is_flagged_and_not_structured(self):
        """Brief case 22: identifiers in the input never reach the case."""
        case = await extract_structured_case(
            "E-2인데 근무처 변경 신고 없이 다른 학원에서 30일 일했습니다. 연락처는 010-1234-5678이고 여권번호는 M12345678입니다.",
            assessment_date=date(2026, 11, 4),
        )
        self.assertTrue(any("개인식별정보" in w for w in case.extraction_warnings))
        dumped = json.dumps(case.public_dict(), ensure_ascii=False)
        self.assertNotIn("010-1234-5678", dumped)
        self.assertNotIn("M12345678", dumped)

    async def test_engine_is_fully_local(self):
        """Brief case 18: determination works from the verified local store
        alone — the engine performs no network access, so a law-API outage
        cannot change or block a determination inside its proven scope."""
        import services.enforcement_workplace as engine

        self.assertFalse(hasattr(engine, "urllib"))
        self.assertFalse(hasattr(engine, "requests"))
        det = determine_workplace_regime(
            StructuredCase.model_validate(
                {"statusOfStay": "E-6-2", "violationCode": "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1"}
            )
        )
        self.assertEqual(det.regime, "PERMIT")
        self.assertEqual(det.evidence[0].url, "https://www.law.go.kr/LSW/admRulLsInfoP.do?admRulSeq=2100000190656")

    async def test_report_statement_variants_extract_procedure(self):
        """'신고했어요' without an object particle still records REPORT_FILED."""
        case = await extract_structured_case(
            "E-2인데 근무처를 옮기고 10일 안에 출입국에 신고했어요.",
            assessment_date=date(2026, 11, 4),
        )
        self.assertEqual(case.procedure_status, "REPORT_FILED")

    async def test_unknown_is_never_coerced_to_false(self):
        """Brief case 15: 'do not know' answers stay None end to end."""
        case = StructuredCase.model_validate(
            {"violationCode": "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1", "assessmentDate": "2026-11-04"}
        )
        det = determine_workplace_regime(case)
        self.assertEqual(det.regime, "UNRESOLVED")
        self.assertIsNone(case.employer_consent)
        self.assertIsNone(case.alien_registered)
        self.assertIn("체류자격", det.missing_facts)


if __name__ == "__main__":
    unittest.main()
