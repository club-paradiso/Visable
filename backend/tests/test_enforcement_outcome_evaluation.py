from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_outcome_evaluation import (  # noqa: E402
    EnforcementOutcomeEvaluationError,
    evaluate_outcome_predictions,
    validate_outcome_ground_truth_dataset,
)

TEMPLATE_PATH = BACKEND_DIR / "data" / "enforcement" / "outcome_ground_truth.template.json"
SCHEMA_PATH = BACKEND_DIR / "data" / "enforcement" / "outcome_ground_truth.schema.json"


def reviewed_ground_truth() -> dict:
    # TEST_ONLY in-memory data exercises scoring mechanics. It is not a checked-in
    # outcome corpus and therefore cannot be mistaken for real enforcement truth.
    return {
        "schemaVersion": "1.0.0",
        "datasetVersion": "test-only-v1",
        "jurisdiction": "KR",
        "purpose": "TEST_ONLY evaluator contract fixture",
        "records": [
            {
                "caseId": "test-case-001",
                "reviewStatus": "INDEPENDENTLY_REVIEWED",
                "reviewedAt": "2026-08-21",
                "reviewerRole": "TEST_ONLY_REVIEWER",
                "independentFromPrediction": True,
                "provenance": {
                    "sourceType": "VERIFIED_ADMINISTRATIVE_RECORD",
                    "authority": "TEST_ONLY_AUTHORITY",
                    "recordId": "TEST-001",
                },
                "outcome": {
                    "decisionDate": "2026-08-20",
                    "monetaryOutcomeKrw": 1_800_000,
                    "dispositionTypes": ["STAY_PERMISSION_DISADVANTAGE"],
                    "primaryDispositionType": "STAY_PERMISSION_DISADVANTAGE",
                },
            }
        ],
    }


def matching_prediction() -> dict:
    return {
        "schemaVersion": "1",
        "engineVersion": "enforcement-prediction-v1",
        "promptVersion": "enforcement-prediction-prompt-v1",
        "status": "LIMITED",
        "monetaryPrediction": {
            "legalBaselineAmountKrw": 2_000_000,
            "legalRange": {"minimumKrw": 1_000_000, "maximumKrw": 3_000_000, "currency": "KRW"},
            "predictedLikelyRange": {"minimumKrw": 1_500_000, "maximumKrw": 2_000_000, "currency": "KRW"},
            "pointEstimateKrw": 1_700_000,
            "predictedDirection": "MITIGATED",
            "confidence": {"level": "LOW", "reasons": ["TEST_ONLY"]},
            "rationale": [],
        },
        "primaryDisposition": {
            "type": "STAY_PERMISSION_DISADVANTAGE",
            "likelihood": "MODERATE",
            "rank": 1,
            "confidence": {"level": "LOW", "reasons": ["TEST_ONLY"]},
            "rationale": [],
            "supportingEvidence": [],
        },
        "alternativeDispositions": [],
        "stayImpact": [],
        "evidence": [],
        "similarCases": [],
        "aggravatingFactors": [],
        "mitigatingFactors": [],
        "unresolvedFactors": [],
        "confidence": {"level": "LOW", "reasons": ["TEST_ONLY"]},
        "limitations": ["TEST_ONLY"],
    }


class OutcomeGroundTruthContractTests(unittest.TestCase):
    def test_checked_in_template_is_empty_and_not_evaluable(self):
        payload = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        validated = validate_outcome_ground_truth_dataset(payload)
        self.assertEqual(validated["records"], [])
        report = evaluate_outcome_predictions(validated, {})
        self.assertEqual(report["status"], "NOT_EVALUABLE")
        self.assertEqual(report["reason"], "NO_REVIEWED_OUTCOME_GROUND_TRUTH")
        self.assertEqual(report["groundTruthCases"], 0)

    def test_schema_and_runtime_contract_share_version(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schemaVersion"]["const"], "1.0.0")
        self.assertEqual(schema["properties"]["jurisdiction"]["const"], "KR")

    def test_unreviewed_record_is_rejected(self):
        payload = reviewed_ground_truth()
        payload["records"][0]["reviewStatus"] = "DRAFT"
        with self.assertRaisesRegex(EnforcementOutcomeEvaluationError, "not independently reviewed"):
            validate_outcome_ground_truth_dataset(payload)

    def test_prediction_derived_ground_truth_is_rejected(self):
        payload = reviewed_ground_truth()
        payload["records"][0]["independentFromPrediction"] = False
        with self.assertRaisesRegex(EnforcementOutcomeEvaluationError, "independent from prediction"):
            validate_outcome_ground_truth_dataset(payload)

    def test_synthetic_source_type_is_rejected(self):
        payload = reviewed_ground_truth()
        payload["records"][0]["provenance"]["sourceType"] = "SYNTHETIC"
        with self.assertRaisesRegex(EnforcementOutcomeEvaluationError, "ineligible outcome source type"):
            validate_outcome_ground_truth_dataset(payload)

    def test_raw_narrative_and_prediction_output_fields_are_rejected(self):
        for key in ("rawText", "predictionOutput"):
            payload = reviewed_ground_truth()
            payload["records"][0][key] = "must never be accepted"
            with self.subTest(key=key):
                with self.assertRaisesRegex(EnforcementOutcomeEvaluationError, "forbidden field"):
                    validate_outcome_ground_truth_dataset(payload)

    def test_primary_disposition_must_be_in_actual_dispositions(self):
        payload = reviewed_ground_truth()
        payload["records"][0]["outcome"]["primaryDispositionType"] = "DEPORTATION"
        with self.assertRaisesRegex(EnforcementOutcomeEvaluationError, "must appear in dispositionTypes"):
            validate_outcome_ground_truth_dataset(payload)

    def test_reviewed_pair_scores_components_without_fake_overall_accuracy(self):
        payload = reviewed_ground_truth()
        report = evaluate_outcome_predictions(payload, {"test-case-001": matching_prediction()})
        self.assertEqual(report["status"], "EVALUATED")
        self.assertEqual(report["groundTruthCases"], 1)
        self.assertEqual(report["matchedPredictions"], 1)
        self.assertEqual(report["predictionCoverage"], 1.0)
        self.assertEqual(report["predictionAvailability"], 1.0)
        self.assertEqual(report["monetary"]["intervalCoverage"], 1.0)
        self.assertEqual(report["monetary"]["pointEstimateMaeKrw"], 100_000)
        self.assertEqual(report["disposition"]["top1Accuracy"], 1.0)
        self.assertEqual(report["disposition"]["topKRecall"], 1.0)
        self.assertEqual(report["qualitativeConfidence"]["LOW"]["observedSuccessRate"], 1.0)
        self.assertNotIn("overallAccuracy", report)
        self.assertNotIn("calibrationScore", report)

    def test_reviewed_truth_without_matching_prediction_is_not_evaluable(self):
        report = evaluate_outcome_predictions(reviewed_ground_truth(), {})
        self.assertEqual(report["status"], "NOT_EVALUABLE")
        self.assertEqual(report["reason"], "NO_MATCHED_PREDICTIONS")


if __name__ == "__main__":
    unittest.main()
