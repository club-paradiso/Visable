from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_service import build_extraction_prompt, extract_structured_case  # noqa: E402


class EnforcementExtractionQualityTests(unittest.IsolatedAsyncioTestCase):
    async def test_colloquial_overstay_extracts_status_duration_first_offense_and_voluntary_visit(self):
        result = await extract_structured_case(
            "D10인데 체류기간 만료 후 엿새 지났어요. 첫 위반이고 오늘 바로 출입국에 자진 방문했습니다.",
            assessment_date=date(2026, 8, 27),
        )
        self.assertEqual(result.status_of_stay, "D-10")
        self.assertEqual(result.violation_code, "OVERSTAY_ART25")
        self.assertEqual(result.duration_days, 6)
        self.assertEqual(result.prior_violations, 0)
        self.assertTrue(result.voluntary_disclosure)
        self.assertEqual(result.assessment_date, date(2026, 8, 27))

    async def test_compound_duration_and_status_subtype_are_normalized(self):
        result = await extract_structured_case(
            "E7-4 비자인데 다른 회사로 옮긴 뒤 변경허가 안 받고 2개월 3일 근무했습니다.",
            assessment_date=date(2026, 8, 27),
        )
        self.assertEqual(result.status_of_stay, "E-7-4")
        self.assertEqual(result.violation_code, "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1")
        self.assertEqual(result.duration_days, 63)
        self.assertFalse(result.authorization_obtained)
        self.assertFalse(result.workplace_change_authorized)

    async def test_designated_workplace_wording_maps_to_article_18_2(self):
        result = await extract_structured_case(
            "E-7인데 지정된 근무처가 아닌 다른 사업장에서 허가 없이 20일 근무했습니다.",
            assessment_date=date(2026, 8, 27),
        )
        self.assertEqual(result.violation_code, "UNAUTHORIZED_EMPLOYMENT_ART18_2")
        self.assertEqual(result.duration_days, 20)

    async def test_bare_other_workplace_wording_stays_unresolved(self):
        result = await extract_structured_case(
            "F-2인데 다른 곳에서 허가 없이 10일 일했습니다.",
            assessment_date=date(2026, 8, 27),
        )
        self.assertIsNone(result.violation_code)
        self.assertGreaterEqual(len(result.violation_candidates), 2)

    async def test_ai_extraction_accepts_extra_commentary_keys_and_preserves_assessment_date(self):
        async def provider(_prompt: str):
            return {
                "ok": True,
                "answer": json.dumps({
                    "schemaVersion": "1",
                    "statusOfStay": "F-2",
                    "violationCode": None,
                    "violationCandidates": [],
                    "durationDays": 10,
                    "priorViolations": 0,
                    "voluntaryDisclosure": True,
                    "unknownFacts": [],
                    "extractionWarnings": [],
                    "explanation": "this key must be ignored",
                }, ensure_ascii=False),
            }

        result = await extract_structured_case(
            "F-2이고 열흘 정도 일했어요. 처음이고 자진 신고했습니다.",
            provider=provider,
            assessment_date=date(2026, 8, 27),
        )
        self.assertEqual(result.status_of_stay, "F-2")
        self.assertEqual(result.duration_days, 10)
        self.assertEqual(result.assessment_date, date(2026, 8, 27))
        self.assertEqual(result.prior_violations, 0)
        self.assertTrue(result.voluntary_disclosure)

    async def test_ai_failure_falls_back_with_visible_confirmation_warning(self):
        async def broken(_prompt: str):
            raise RuntimeError("provider unavailable")

        result = await extract_structured_case(
            "C3로 들어와서 허가 없이 12일 알바했습니다.",
            provider=broken,
            assessment_date=date(2026, 8, 27),
        )
        self.assertEqual(result.status_of_stay, "C-3")
        self.assertEqual(result.violation_code, "UNAUTHORIZED_STAY_OR_WORK_ART18_1")
        self.assertTrue(any("로컬 추출 결과" in item for item in result.extraction_warnings))

    def test_prompt_defines_schema_codes_and_reference_date(self):
        prompt = build_extraction_prompt("D-2 허가 없이 알바", assessment_date=date(2026, 8, 27))
        self.assertIn('"statusOfStay"', prompt)
        self.assertIn("OVERSTAY_ART25", prompt)
        self.assertIn("UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1", prompt)
        self.assertIn("assessmentDate=2026-08-27", prompt)
        self.assertIn("2개월 3일", prompt)


if __name__ == "__main__":
    unittest.main()
