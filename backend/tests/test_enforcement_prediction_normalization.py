from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_evidence import retrieve_enforcement_evidence  # noqa: E402
from services.enforcement_models import StructuredCase  # noqa: E402
from services.enforcement_prediction import PredictionValidationError, validate_ai_prediction  # noqa: E402
from services.enforcement_rules import calculate_legal_baseline  # noqa: E402


class NoPrecedents:
    @staticmethod
    def search_precedents(query, limit=3):
        return {"status": "no_results", "items": []}


def sample_case() -> StructuredCase:
    return StructuredCase(
        status_of_stay="D-2",
        violation_code="STATUS_OUTSIDE_ACTIVITY_ART20",
        authorization_obtained=False,
        duration_days=18,
        assessment_date=date(2026, 9, 8),
        prior_violations=0,
        unknown_facts=[],
    )


def base_payload() -> dict:
    return {
        "status": "LIMITED",
        "monetaryPrediction": {
            "predictedLikelyRange": {
                "minimumKrw": 1_000_000,
                "maximumKrw": 3_000_000,
            },
            "pointEstimateKrw": None,
            "predictedDirection": "UNCERTAIN",
        },
        "primaryDisposition": None,
    }


class EnforcementPredictionNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.case = sample_case()
        self.baseline = calculate_legal_baseline(self.case)
        self.evidence = retrieve_enforcement_evidence(
            self.case,
            self.baseline,
            precedent_adapter=NoPrecedents,
        )

    def test_harmless_extra_fields_and_missing_empty_fields_are_normalized(self):
        payload = base_payload()
        payload["commentary"] = "This field is transport noise and must not reach the public model."

        result = validate_ai_prediction(payload, self.case, self.baseline, self.evidence)

        self.assertEqual(result.status, "LIMITED")
        self.assertIsNotNone(result.monetary_prediction)
        self.assertEqual(result.monetary_prediction.predicted_likely_range.minimum_krw, 1_000_000)
        self.assertEqual(result.monetary_prediction.predicted_likely_range.maximum_krw, 3_000_000)
        self.assertEqual(result.monetary_prediction.predicted_likely_range.currency, "KRW")
        self.assertIsNone(result.monetary_prediction.point_estimate_krw)
        self.assertIn(result.confidence.level, {"LOW", "VERY_LOW"})
        self.assertFalse(hasattr(result, "commentary"))

    def test_out_of_range_money_is_still_rejected(self):
        payload = base_payload()
        payload["monetaryPrediction"]["predictedLikelyRange"]["maximumKrw"] = 4_000_000
        with self.assertRaises(PredictionValidationError):
            validate_ai_prediction(payload, self.case, self.baseline, self.evidence)

    def test_numeric_probability_is_still_rejected_before_normalization(self):
        payload = base_payload()
        payload["probability"] = "72%"
        with self.assertRaises(PredictionValidationError):
            validate_ai_prediction(payload, self.case, self.baseline, self.evidence)

    def test_invented_evidence_id_is_still_rejected(self):
        payload = base_payload()
        payload["alternativeDispositions"] = [{
            "type": "STAY_PERMISSION_DISADVANTAGE",
            "likelihood": "LOW",
            "rank": 1,
            "supportingEvidence": ["invented-evidence-id"],
        }]
        with self.assertRaises(PredictionValidationError):
            validate_ai_prediction(payload, self.case, self.baseline, self.evidence)


if __name__ == "__main__":
    unittest.main()
