import json
import unittest

from services.enforcement_models import EnforcementEvidencePack, LegalBaseline, MoneyRange, StructuredCase
from services.enforcement_prediction import (
    PredictionValidationError,
    build_prediction_prompt,
    validate_ai_prediction,
)


def _fixture():
    case = StructuredCase(
        statusOfStay="D-2",
        violationCode="STATUS_OUTSIDE_ACTIVITY_ART20",
        authorizationObtained=False,
        durationDays=18,
        priorViolations=0,
        assessmentDate="2026-09-04",
        unknownFacts=["자진신고 여부"],
    )
    baseline = LegalBaseline(
        status="AVAILABLE",
        violationCode="STATUS_OUTSIDE_ACTIVITY_ART20",
        violationLabel="체류자격외활동 허가 위반",
        baselineAmountKrw=1000000,
        legallyAdjustableRange=MoneyRange(minimumKrw=500000, maximumKrw=2000000),
        statutoryMaximumKrw=2000000,
        durationDays=18,
        legallyAvailableDispositions=["STAY_PERMISSION_DISADVANTAGE"],
        confidence="HIGH",
    )
    evidence = EnforcementEvidencePack(
        evidence=[],
        similarCases=[],
        retrievalStatus="LIMITED",
        limitations=["현재 확인 가능한 유사 공개사례가 충분하지 않습니다."],
    )
    return case, baseline, evidence


class EnforcementPredictionPromptContractTests(unittest.TestCase):
    def test_prediction_prompt_exposes_real_json_shape_not_python_class_name_only(self):
        case, baseline, evidence = _fixture()
        prompt = build_prediction_prompt(case, baseline, evidence)

        self.assertIn("OUTPUT_JSON_CONTRACT:", prompt)
        self.assertIn('"monetaryPrediction"', prompt)
        self.assertIn('"primaryDisposition"', prompt)
        self.assertIn('"supportingEvidence"', prompt)
        self.assertIn('"evidenceIds"', prompt)
        self.assertIn("Do NOT add summary, reasoning, probability", prompt)
        self.assertIn("INPUT_JSON:", prompt)
        self.assertNotIn("rawText", prompt)

    def test_minimal_bounded_provider_json_survives_server_validation(self):
        case, baseline, evidence = _fixture()
        provider_answer = {
            "status": "LIMITED",
            "monetaryPrediction": None,
            "primaryDisposition": None,
            "alternativeDispositions": [],
            "stayImpact": [],
            "aggravatingFactors": [],
            "mitigatingFactors": [],
            "unresolvedFactors": [],
            "confidence": {"level": "LOW", "reasons": ["공개 근거가 제한적입니다."]},
            "limitations": ["유사 공개사례가 부족합니다."],
        }
        wrapped = {
            "ok": True,
            "answer": json.dumps(provider_answer, ensure_ascii=False),
            "final_model": "google/gemma-4-26b-a4b-it:free",
        }

        prediction = validate_ai_prediction(wrapped, case, baseline, evidence)

        self.assertEqual(prediction.status, "LIMITED")
        self.assertEqual(prediction.model_id, "google/gemma-4-26b-a4b-it:free")
        self.assertEqual(prediction.confidence.level, "LOW")
        self.assertEqual(prediction.evidence, [])
        self.assertEqual(prediction.similar_cases, [])

    def test_probability_field_is_still_rejected_before_schema_projection(self):
        case, baseline, evidence = _fixture()
        bad = {
            "status": "LIMITED",
            "probability": "72%",
            "confidence": {"level": "LOW", "reasons": []},
        }

        with self.assertRaisesRegex(PredictionValidationError, "numeric probabilities"):
            validate_ai_prediction(bad, case, baseline, evidence)


if __name__ == "__main__":
    unittest.main()
