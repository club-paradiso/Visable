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

from services.enforcement_benchmark import (  # noqa: E402
    EnforcementBenchmarkError,
    run_benchmark,
    validate_benchmark_dataset,
)

CORPUS_PATH = Path(__file__).resolve().parent / "fixtures" / "enforcement_v3_benchmark_corpus.json"


class EnforcementBenchmarkCorpusTests(unittest.IsolatedAsyncioTestCase):
    async def test_reviewed_corpus_scores_perfectly(self):
        payload = validate_benchmark_dataset(json.loads(CORPUS_PATH.read_text(encoding="utf-8")))
        report = await run_benchmark(
            payload["cases"],
            assessment_date=date.fromisoformat(payload["assessmentDate"]),
        )

        self.assertEqual(report["cases"], 36)
        self.assertEqual(report["exactCaseAccuracy"], 1.0)
        self.assertEqual(report["materialFactAccuracy"], 1.0)
        self.assertEqual(report["violationCodeAccuracy"], 1.0)
        self.assertEqual(report["deterministicBaselineAccuracy"], 1.0)
        self.assertEqual(report["securityInvariantAccuracy"], 1.0)
        self.assertEqual(report["abstention"]["evaluated"], 6)
        self.assertEqual(report["abstention"]["precision"], 1.0)
        self.assertEqual(report["abstention"]["recall"], 1.0)
        self.assertEqual(report["coverage"]["provenanceCoverage"], 1.0)
        self.assertEqual(report["coverage"]["kindCounts"], {"narrative": 28, "structured": 8})
        self.assertEqual(report["latencyMs"]["samples"], 28)
        self.assertGreaterEqual(report["coverage"]["deterministicBaselineCases"], 19)
        self.assertGreater(report["coverage"]["securityInvariantChecks"], 0)
        self.assertEqual(report["failures"], [])

        self.assertEqual(
            set(report["bySuite"]),
            {"classification-boundary", "colloquial-extraction", "rule-engine", "security-fail-closed"},
        )
        self.assertTrue(all(section["exactCaseAccuracy"] == 1.0 for section in report["bySuite"].values()))

    def test_schema_v2_requires_provenance(self):
        payload = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        payload["cases"][0].pop("provenance")
        with self.assertRaisesRegex(EnforcementBenchmarkError, "provenance is required"):
            validate_benchmark_dataset(payload)

    def test_schema_v2_rejects_duplicate_case_ids(self):
        payload = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        payload["cases"][1]["id"] = payload["cases"][0]["id"]
        with self.assertRaisesRegex(EnforcementBenchmarkError, "duplicate benchmark case id"):
            validate_benchmark_dataset(payload)

    def test_corpus_contains_no_prediction_ground_truth(self):
        payload = validate_benchmark_dataset(json.loads(CORPUS_PATH.read_text(encoding="utf-8")))
        forbidden = {
            "monetaryPrediction",
            "predictedDisposition",
            "pointEstimateKrw",
            "predictedLikelyRange",
            "outcomeGroundTruth",
        }
        for row in payload["cases"]:
            serialized = json.dumps(row, ensure_ascii=False)
            with self.subTest(case=row["id"]):
                self.assertFalse(any(token in serialized for token in forbidden))


if __name__ == "__main__":
    unittest.main()
