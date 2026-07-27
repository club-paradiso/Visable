"""Employment free-text extraction guard tests.

The single load-bearing invariant: the LLM layer can describe a job but can never
produce a KSCO8/KSIC11 code, an unknown visa code, or a reporting determination.
Everything it emits passes through validate_extraction, and every removal is
recorded rather than silent.

    python3 -m pytest backend/tests/test_employment_nl.py -q
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402

import paradiso_backend as pb  # noqa: E402
from services import employment_nl as enl  # noqa: E402

ALLOWED = {"D-2", "D-10", "E-7", "F-6", "F-2", "E-9", "H-2"}

PROVIDER_ENV = ("OPENROUTER_API_KEY", "GROQ_API_KEY", "NVIDIA_API_KEY",
                "ENABLE_OLLAMA_FALLBACK", "ENABLE_NVIDIA_NIM_EXPERIMENTAL",
                "ALLOW_GROQ_FALLBACK")


def _validate(payload, allowed=ALLOWED):
    return enl.validate_extraction(payload, allowed_visa_codes=allowed)


class SchemaTests(unittest.TestCase):
    def test_empty_extraction_has_every_field(self):
        data = enl.empty_extraction()
        self.assertEqual(set(data), set(enl.EXTRACTION_FIELDS))

    def test_unknown_keys_are_dropped_and_reported(self):
        result = _validate({"role": "바리스타", "recommendedCode": "5321",
                            "isReportRequired": True})
        self.assertNotIn("recommendedCode", result["data"])
        self.assertNotIn("isReportRequired", result["data"])
        self.assertTrue(any(w.startswith("DROPPED_UNKNOWN_FIELDS") for w in result["warnings"]))

    def test_non_json_model_output_fails_closed(self):
        result = enl.validate_extraction("I think you are a barista!")
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"], enl.empty_extraction())

    def test_json_inside_a_code_fence_is_parsed(self):
        raw = '```json\n{"role": "바리스타"}\n```'
        result = enl.validate_extraction(raw, allowed_visa_codes=ALLOWED)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["role"], "바리스타")

    def test_strings_are_length_capped(self):
        result = _validate({"role": "가" * 5000})
        self.assertLessEqual(len(result["data"]["role"]), 200)

    def test_lists_are_bounded_and_deduplicated(self):
        result = _validate({"tasks": ["음료 제조"] * 50 + ["설거지"]})
        self.assertLessEqual(len(result["data"]["tasks"]), 12)
        self.assertEqual(len(set(result["data"]["tasks"])), len(result["data"]["tasks"]))


class CodeInventionGuardTests(unittest.TestCase):
    def test_ksco8_style_code_is_stripped(self):
        result = _validate({"role": "바리스타 5321"})
        self.assertNotIn("5321", result["data"]["role"])
        self.assertTrue(any("STRIPPED_CLASSIFICATION_CODE" in w for w in result["warnings"]))

    def test_ksic11_style_code_is_stripped(self):
        result = _validate({"employerMainBusiness": "커피 전문점 I5622"})
        self.assertNotIn("I5622", result["data"]["employerMainBusiness"])

    def test_codes_inside_list_items_are_stripped(self):
        result = _validate({"tasks": ["음료 제조 5321", "청소"]})
        joined = " ".join(result["data"]["tasks"])
        self.assertNotIn("5321", joined)
        self.assertIn("청소", joined)

    def test_no_field_of_the_response_can_contain_a_classification_code(self):
        noisy = {field: ("코드 5321 입니다" if kind == "str" else ["코드 5321"])
                 for field, kind in enl.EXTRACTION_FIELDS.items() if kind != "bool"}
        result = _validate(noisy)
        blob = json.dumps(result["data"], ensure_ascii=False)
        self.assertNotIn("5321", blob)

    def test_ordinary_numbers_in_prose_are_not_mistaken_for_codes(self):
        result = _validate({"role": "주 2회 근무하는 바리스타"})
        self.assertIn("바리스타", result["data"]["role"])


class VisaCodeAllowListTests(unittest.TestCase):
    def test_known_visa_code_is_kept(self):
        self.assertEqual(_validate({"visaStatus": "D-2"})["data"]["visaStatus"], "D-2")

    def test_unknown_visa_code_is_rejected(self):
        result = _validate({"visaStatus": "Z-9"})
        self.assertEqual(result["data"]["visaStatus"], "")
        self.assertIn("REJECTED_UNKNOWN_VISA_CODE", result["warnings"])

    def test_unknown_subcode_degrades_to_its_known_parent(self):
        result = _validate({"visaStatus": "D-2-99"})
        self.assertEqual(result["data"]["visaStatus"], "D-2")

    def test_free_text_visa_status_without_a_code_is_dropped(self):
        self.assertEqual(_validate({"visaStatus": "학생 비자"})["data"]["visaStatus"], "")


class DeterminationGuardTests(unittest.TestCase):
    def test_reporting_determination_in_clarification_is_removed(self):
        result = _validate({"needsClarification": True,
                            "clarificationQuestion": "이 경우 신고 대상입니다"})
        self.assertEqual(result["data"]["clarificationQuestion"], "")
        self.assertIn("REMOVED_DETERMINATION_IN_CLARIFICATION", result["warnings"])

    def test_deadline_claim_is_treated_as_a_determination(self):
        self.assertTrue(enl.contains_determination("15일 이내에 신고해야 합니다"))

    def test_work_permission_verdict_is_a_determination(self):
        self.assertTrue(enl.contains_determination("이 활동은 취업이 가능합니다"))

    def test_a_genuine_question_survives(self):
        result = _validate({"needsClarification": True,
                            "clarificationQuestion": "사업장이 카페인가요, 아니면 제과점인가요?"})
        self.assertTrue(result["data"]["needsClarification"])
        self.assertIn("카페", result["data"]["clarificationQuestion"])

    def test_clarification_flag_without_a_question_is_cleared(self):
        result = _validate({"needsClarification": True, "clarificationQuestion": ""})
        self.assertFalse(result["data"]["needsClarification"])
        self.assertIn("CLARIFICATION_FLAG_WITHOUT_QUESTION", result["warnings"])


class OccupationIndustrySeparationTests(unittest.TestCase):
    def test_role_and_employer_business_stay_separate_fields(self):
        result = _validate({"role": "바리스타", "employerMainBusiness": "커피 전문점"})
        self.assertEqual(result["data"]["role"], "바리스타")
        self.assertEqual(result["data"]["employerMainBusiness"], "커피 전문점")
        self.assertNotEqual(result["data"]["role"], result["data"]["employerMainBusiness"])

    def test_prompt_explicitly_forbids_copying_one_into_the_other(self):
        prompt = enl.build_extraction_prompt("카페에서 음료를 만들어요")
        self.assertIn("never copy one into the other", prompt)

    def test_prompt_forbids_classification_codes_and_verdicts(self):
        prompt = enl.build_extraction_prompt("카페에서 음료를 만들어요")
        self.assertIn("NEVER output a KSCO8", prompt)
        self.assertIn("NEVER decide whether reporting is required", prompt)


class AnalyzerHandoffTests(unittest.TestCase):
    def test_structured_fields_become_analyzer_input(self):
        data = _validate({"role": "바리스타", "workplace": "카페",
                          "employerMainBusiness": "커피 전문점",
                          "tasks": ["음료 제조"]})["data"]
        analyzer_input = enl.to_analyzer_input(data, original_text="카페에서 음료를 만들어요")
        self.assertIn("바리스타", analyzer_input["text"])
        self.assertIn("커피 전문점", analyzer_input["text"])
        self.assertIn("음료", analyzer_input["text"])

    def test_original_text_is_preserved_when_extraction_is_thin(self):
        data = enl.empty_extraction()
        analyzer_input = enl.to_analyzer_input(data, original_text="귤 농장에서 열매 따요")
        self.assertIn("귤", analyzer_input["text"])

    def test_analyzer_input_carries_only_the_four_accepted_keys(self):
        analyzer_input = enl.to_analyzer_input(enl.empty_extraction(), original_text="x")
        self.assertEqual(set(analyzer_input), {"text", "locale", "visaStatus", "employmentType"})

    def test_interpretation_sentence_is_built_from_validated_fields_only(self):
        data = _validate({"role": "바리스타 5321", "workplace": "카페"})["data"]
        sentence = enl.build_interpretation_sentence(data)
        self.assertNotIn("5321", sentence)
        self.assertIn("카페", sentence)

    def test_english_interpretation_is_english(self):
        data = _validate({"role": "barista", "workplace": "a cafe"})["data"]
        self.assertIn("cafe", enl.build_interpretation_sentence(data, lang="en"))

    def test_empty_extraction_yields_an_honest_sentence(self):
        sentence = enl.build_interpretation_sentence(enl.empty_extraction())
        self.assertTrue(sentence)


class MultilingualInputTests(unittest.TestCase):
    def test_english_extraction_survives_validation(self):
        result = _validate({"detectedLanguage": "en", "role": "barista",
                            "workplace": "cafe"})
        self.assertEqual(result["data"]["detectedLanguage"], "en")
        self.assertEqual(result["data"]["role"], "barista")

    def test_chinese_extraction_survives_validation(self):
        result = _validate({"detectedLanguage": "zh", "role": "客房清洁",
                            "workplace": "酒店"})
        self.assertEqual(result["data"]["workplace"], "酒店")

    def test_mixed_language_is_a_valid_detected_language(self):
        self.assertEqual(_validate({"detectedLanguage": "mixed"})["data"]["detectedLanguage"],
                         "mixed")

    def test_bogus_language_value_is_dropped(self):
        self.assertEqual(_validate({"detectedLanguage": "klingon"})["data"]["detectedLanguage"],
                         "")


class EmploymentInterpretApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(pb.app)
        self._saved = {k: os.environ.get(k) for k in PROVIDER_ENV}
        for key in PROVIDER_ENV:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_empty_input_is_handled(self):
        body = self.client.post("/api/employment/interpret", json={"text": ""}).json()
        self.assertEqual(body["status"], "empty_input")

    def test_no_provider_degrades_without_breaking_the_guided_flow(self):
        body = self.client.post("/api/employment/interpret",
                                json={"text": "카페에서 음료를 만들어요"}).json()
        self.assertEqual(body["status"], "unavailable")
        self.assertTrue(body["fallbackAvailable"])
        # The raw text still reaches the deterministic analyzer.
        self.assertIn("카페", body["analyzerInput"]["text"])

    def test_response_never_contains_a_classification_code(self):
        body = self.client.post("/api/employment/interpret",
                                json={"text": "카페에서 음료를 만들어요 5321"}).json()
        self.assertEqual(body["extraction"], pb._employment_nl.empty_extraction())


if __name__ == "__main__":
    unittest.main()
