from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_service import extract_structured_case  # noqa: E402

ASSESSMENT_DATE = date(2026, 8, 26)


class RailwayEnforcementClassificationParityTests(unittest.IsolatedAsyncioTestCase):
    async def test_c3_unauthorized_work_maps_to_article_18_1(self):
        case = await extract_structured_case(
            "C-3 체류자격인데 취업 허가 없이 음식점에서 18일 일했습니다.",
            assessment_date=ASSESSMENT_DATE,
        )
        self.assertEqual(case.violation_code, "UNAUTHORIZED_STAY_OR_WORK_ART18_1")
        self.assertEqual(case.violation_candidates, ["UNAUTHORIZED_STAY_OR_WORK_ART18_1"])

    async def test_d2_unauthorized_work_maps_to_article_20(self):
        case = await extract_structured_case(
            "D-2 유학생인데 허가 없이 음식점에서 18일 아르바이트했습니다.",
            assessment_date=ASSESSMENT_DATE,
        )
        self.assertEqual(case.violation_code, "STATUS_OUTSIDE_ACTIVITY_ART20")
        self.assertEqual(case.violation_candidates, ["STATUS_OUTSIDE_ACTIVITY_ART20"])

    async def test_e7_outside_designated_workplace_maps_to_article_18_2(self):
        case = await extract_structured_case(
            "E-7 체류자격으로 지정된 근무처가 아닌 다른 사업장에서 허가 없이 20일 근무했습니다.",
            assessment_date=ASSESSMENT_DATE,
        )
        self.assertEqual(case.violation_code, "UNAUTHORIZED_EMPLOYMENT_ART18_2")
        self.assertEqual(case.violation_candidates, ["UNAUTHORIZED_EMPLOYMENT_ART18_2"])

    async def test_workplace_change_without_permission_maps_to_article_21(self):
        case = await extract_structured_case(
            "E-7인데 근무처를 변경하고 변경허가 없이 2개월 근무했습니다.",
            assessment_date=ASSESSMENT_DATE,
        )
        self.assertEqual(case.violation_code, "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1")
        self.assertEqual(case.violation_candidates, ["UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1"])
        self.assertIs(case.workplace_change_authorized, False)

    async def test_f2_bare_unauthorized_work_stays_legally_ambiguous(self):
        case = await extract_structured_case(
            "F-2 체류자격인데 허가 없이 음식점에서 18일 일했습니다.",
            assessment_date=ASSESSMENT_DATE,
        )
        self.assertIsNone(case.violation_code)
        self.assertEqual(set(case.violation_candidates), {
            "UNAUTHORIZED_STAY_OR_WORK_ART18_1",
            "STATUS_OUTSIDE_ACTIVITY_ART20",
            "UNAUTHORIZED_EMPLOYMENT_ART18_2",
            "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1",
        })
        self.assertIn("취업 가능 체류자격인지 및 지정 근무처·근무처 변경 관계", case.unknown_facts)

    async def test_ai_cannot_override_deterministic_article_18_1_mapping(self):
        async def wrong_provider(_prompt: str):
            return {
                "schemaVersion": "1",
                "statusOfStay": "C-3",
                "violationCode": "UNAUTHORIZED_EMPLOYMENT_ART18_2",
                "violationCandidates": ["UNAUTHORIZED_EMPLOYMENT_ART18_2"],
                "authorizationObtained": False,
                "durationDays": 18,
                "assessmentDate": "2026-08-26",
                "unknownFacts": [],
                "extractionWarnings": [],
            }

        case = await extract_structured_case(
            "C-3 체류자격인데 취업 허가 없이 음식점에서 18일 일했습니다.",
            provider=wrong_provider,
            assessment_date=ASSESSMENT_DATE,
        )
        self.assertEqual(case.violation_code, "UNAUTHORIZED_STAY_OR_WORK_ART18_1")
        self.assertEqual(case.violation_candidates, ["UNAUTHORIZED_STAY_OR_WORK_ART18_1"])

    async def test_ai_cannot_force_ambiguous_f2_into_article_18_2(self):
        async def wrong_provider(_prompt: str):
            return {
                "schemaVersion": "1",
                "statusOfStay": "F-2",
                "violationCode": "UNAUTHORIZED_EMPLOYMENT_ART18_2",
                "violationCandidates": ["UNAUTHORIZED_EMPLOYMENT_ART18_2"],
                "authorizationObtained": False,
                "durationDays": 18,
                "assessmentDate": "2026-08-26",
                "unknownFacts": [],
                "extractionWarnings": [],
            }

        case = await extract_structured_case(
            "F-2 체류자격인데 허가 없이 음식점에서 18일 일했습니다.",
            provider=wrong_provider,
            assessment_date=ASSESSMENT_DATE,
        )
        self.assertIsNone(case.violation_code)
        self.assertEqual(len(case.violation_candidates), 4)
        self.assertIn("취업 가능 체류자격인지 및 지정 근무처·근무처 변경 관계", case.unknown_facts)


if __name__ == "__main__":
    unittest.main()
