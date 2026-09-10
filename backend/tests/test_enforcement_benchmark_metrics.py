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

from services.enforcement_benchmark import run_benchmark  # noqa: E402

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "enforcement_v3_benchmark_seed.json"


class EnforcementBenchmarkMetricsTests(unittest.IsolatedAsyncioTestCase):
    async def test_checked_in_seed_scores_perfectly(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        report = await run_benchmark(
            payload["cases"],
            assessment_date=date.fromisoformat(payload["assessmentDate"]),
        )

        self.assertEqual(report["cases"], 10)
        self.assertEqual(report["exactCaseAccuracy"], 1.0)
        self.assertEqual(report["materialFactAccuracy"], 1.0)
        self.assertEqual(report["violationCodeAccuracy"], 1.0)
        self.assertEqual(report["deterministicBaselineAccuracy"], 1.0)
        self.assertEqual(report["abstention"]["expected"], 2)
        self.assertEqual(report["abstention"]["predicted"], 2)
        self.assertEqual(report["abstention"]["precision"], 1.0)
        self.assertEqual(report["abstention"]["recall"], 1.0)
        self.assertEqual(report["failures"], [])
        self.assertGreaterEqual(report["latencyMs"]["p50"], 0.0)
        self.assertGreaterEqual(report["latencyMs"]["p95"], report["latencyMs"]["p50"])

    async def test_metric_report_exposes_failures_without_hiding_them_in_average(self):
        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        broken = json.loads(json.dumps(payload["cases"][:1], ensure_ascii=False))
        broken[0]["expected"]["violationCode"] = "OVERSTAY_ART25"

        report = await run_benchmark(
            broken,
            assessment_date=date.fromisoformat(payload["assessmentDate"]),
        )

        self.assertLess(report["exactCaseAccuracy"], 1.0)
        self.assertLess(report["violationCodeAccuracy"], 1.0)
        self.assertEqual(len(report["failures"]), 1)
        self.assertEqual(report["failures"][0]["id"], "nl-001")
        self.assertTrue(any("violationCode" in item for item in report["failures"][0]["errors"]))


if __name__ == "__main__":
    unittest.main()
