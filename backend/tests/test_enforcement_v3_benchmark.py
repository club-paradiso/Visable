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

from services.enforcement_rules import calculate_legal_baseline  # noqa: E402
from services.enforcement_service import extract_structured_case  # noqa: E402


FIXTURE = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "enforcement_v3_benchmark_seed.json")
    .read_text(encoding="utf-8")
)

_FIELD_MAP = {
    "statusOfStay": "status_of_stay",
    "violationCode": "violation_code",
    "durationDays": "duration_days",
    "priorViolations": "prior_violations",
    "voluntaryDisclosure": "voluntary_disclosure",
    "violationStartDate": "violation_start_date",
    "violationEndDate": "violation_end_date",
}


class EnforcementV3BenchmarkSeedTests(unittest.IsolatedAsyncioTestCase):
    async def test_seed_cases_pin_extraction_and_deterministic_baseline(self):
        assessment_date = date.fromisoformat(FIXTURE["assessmentDate"])
        self.assertGreaterEqual(len(FIXTURE["cases"]), 10)

        for row in FIXTURE["cases"]:
            with self.subTest(case=row["id"]):
                case = await extract_structured_case(row["text"], assessment_date=assessment_date)
                expected = row["expected"]

                for public_name, attr_name in _FIELD_MAP.items():
                    if public_name not in expected:
                        continue
                    value = expected[public_name]
                    if public_name in {"violationStartDate", "violationEndDate"} and value:
                        value = date.fromisoformat(value)
                    self.assertEqual(getattr(case, attr_name), value, f"{row['id']}: {public_name}")

                baseline = calculate_legal_baseline(case)
                if "deterministicBaselineStatus" in expected:
                    self.assertEqual(baseline.status, expected["deterministicBaselineStatus"])
                if "baselineAmountKrw" in expected:
                    self.assertEqual(baseline.status, "AVAILABLE")
                    self.assertEqual(baseline.baseline_amount_krw, expected["baselineAmountKrw"])
                if expected.get("boundaryAssumptionExpected"):
                    self.assertTrue(baseline.assumptions)


if __name__ == "__main__":
    unittest.main()
