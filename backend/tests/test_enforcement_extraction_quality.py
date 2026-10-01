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


PARITY_FIXTURE = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "enforcement_extraction_parity.json")
    .read_text(encoding="utf-8")
)

_CAMEL_TO_SNAKE = {
    "statusOfStay": "status_of_stay",
    "violationCode": "violation_code",
    "violationCandidates": "violation_candidates",
    "durationDays": "duration_days",
    "violationStartDate": "violation_start_date",
    "violationEndDate": "violation_end_date",
    "priorViolations": "prior_violations",
    "voluntaryDisclosure": "voluntary_disclosure",
    "workplaceChangeAuthorized": "workplace_change_authorized",
}


class EnforcementExtractionParityTests(unittest.IsolatedAsyncioTestCase):
    """Runs the fixture shared with scripts/check_enforcement_extraction_quality.mjs.

    The Python service is the primary extractor and the JS module is the
    same-origin fallback. Driving both from one fixture keeps them from
    drifting, so a user never gets a different provision depending on which
    path served the request.
    """

    async def test_shared_parity_fixture(self):
        assessment_date = date.fromisoformat(PARITY_FIXTURE["assessmentDate"])
        ambiguous = PARITY_FIXTURE["ambiguousWorkCodes"]
        overlap = PARITY_FIXTURE["workplaceOverlapCodes"]
        for case in PARITY_FIXTURE["cases"]:
            with self.subTest(case=case["name"]):
                result = await extract_structured_case(
                    case["text"], assessment_date=assessment_date
                )
                for key, expected in case["expect"].items():
                    actual = getattr(result, _CAMEL_TO_SNAKE[key])
                    if expected == "AMBIGUOUS":
                        expected = ambiguous
                    elif expected == "WORKPLACE_OVERLAP":
                        expected = overlap
                    elif key in ("violationStartDate", "violationEndDate") and expected:
                        expected = date.fromisoformat(expected)
                    self.assertEqual(actual, expected, f"{case['name']}: {key}")
                self.assertEqual(result.assessment_date, assessment_date)


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

        # Keep this case materially ambiguous so the extractor genuinely needs
        # the AI provider. Complete local parses now intentionally skip AI for
        # latency, and therefore must not pretend that an unattempted provider
        # "failed" or force a fake confirmation warning on the user.
        result = await extract_structured_case(
            "F-2인데 다른 곳에서 허가 없이 10일 일했습니다.",
            provider=broken,
            assessment_date=date(2026, 8, 27),
        )
        self.assertEqual(result.status_of_stay, "F-2")
        self.assertIsNone(result.violation_code)
        self.assertGreaterEqual(len(result.violation_candidates), 2)
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


class WorkplaceOverlapBaselineTests(unittest.IsolatedAsyncioTestCase):
    """Issue #587: 제18조제2항 / 제21조제1항 overlap.

    별표 7 (시행규칙, 2026-01-23) gives 더목 (18②) and 저목 (21① 본문) the same
    tiers, so an unresolved overlap still has a baseline. E-1~E-7 신고 대상자
    (21① 단서, 시행령 제26조의2) are excluded from 18② (21③) and face a 과태료
    (제100조①3호) instead; that branch must be disclosed, never silently priced.
    """

    async def test_unresolved_overlap_still_has_the_shared_baseline(self):
        from services.enforcement_rules import REPORT_PROVISO_NOTE, SHARED_TIER_NOTE, calculate_legal_baseline

        case = await extract_structured_case(
            "E-7인데 지정된 근무처가 아닌 다른 회사로 옮겨서 변경허가 없이 30일 일했습니다.",
            assessment_date=date(2026, 8, 28),
        )
        self.assertIsNone(case.violation_code)
        baseline = calculate_legal_baseline(case)
        self.assertEqual(baseline.status, "AVAILABLE")
        self.assertIsNone(baseline.violation_code)
        self.assertEqual(baseline.baseline_amount_krw, 1_000_000)
        self.assertIn("조문 미확정", baseline.violation_label)
        self.assertIn(SHARED_TIER_NOTE, baseline.assumptions)
        self.assertIn(REPORT_PROVISO_NOTE, baseline.assumptions)
        self.assertIn("출입국관리법 제18조제2항", baseline.applied_rules)
        self.assertIn("출입국관리법 제21조제1항", baseline.applied_rules)

    async def test_proviso_note_is_limited_to_e1_to_e7_or_unknown_status(self):
        from services.enforcement_rules import REPORT_PROVISO_NOTE, calculate_legal_baseline

        e9 = await extract_structured_case(
            "E-9인데 사업장 변경 허가 없이 다른 공장에서 40일 일했습니다.",
            assessment_date=date(2026, 8, 28),
        )
        self.assertEqual(e9.violation_code, "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1")
        self.assertNotIn(REPORT_PROVISO_NOTE, calculate_legal_baseline(e9).assumptions)
        e7 = await extract_structured_case(
            "E-7인데 근무처를 변경하고 변경허가 없이 2개월 근무했습니다.",
            assessment_date=date(2026, 8, 28),
        )
        self.assertIn(REPORT_PROVISO_NOTE, calculate_legal_baseline(e7).assumptions)

    async def test_candidates_with_different_tables_stay_missing_facts(self):
        from services.enforcement_rules import calculate_legal_baseline

        case = await extract_structured_case(
            "F-2인데 다른 곳에서 허가 없이 10일 일했습니다.", assessment_date=date(2026, 8, 28)
        )
        self.assertEqual(calculate_legal_baseline(case).status, "MISSING_FACTS")
