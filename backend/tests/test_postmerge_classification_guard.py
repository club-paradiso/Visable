"""Post-merge Mission 002 NO_GO: live ask path must fail closed on ambiguous routing."""
import asyncio
import unittest
from unittest.mock import patch

import paradiso_backend as pb
from services.classification_safety import assess_classification
from services.procedure_classifier import classify_procedure


class PostMergeClassificationGuardTests(unittest.TestCase):
    def test_unknown_status_and_conflicting_payload(self):
        self.assertEqual(assess_classification("Can I extend F-10?").reason, "unknown_status")
        self.assertEqual(assess_classification("F-10 visa application", payload_code="F-10").reason,
                         "unknown_status")
        self.assertEqual(assess_classification("D-2 연장", payload_code="E-7", lang="ko").reason,
                         "conflicting_status_context")
        self.assertIsNone(assess_classification("D-2 연장", payload_code="D-2", lang="ko"))

    def test_multiple_codes_and_directional_transition(self):
        self.assertEqual(assess_classification("D-2 및 E-7 서류", lang="ko").reason, "multiple_statuses")
        self.assertEqual(assess_classification("D-2 또는 E-7 가능?", payload_code="D-2").reason,
                         "multiple_statuses")
        self.assertEqual(assess_classification("F-6에서 E-9으로 체류자격 변경", lang="ko").reason,
                         "transition_requires_review")
        self.assertEqual(assess_classification("D-2 -> E-7 -> F-2 switch").reason,
                         "multiple_statuses")

    def test_passport_service_is_not_registration_report(self):
        for text in (
            "I renewed my passport at the embassy",
            "대사관에서 여권을 갱신했어요",
            "여권 재발급",
            "my passport is lost",
        ):
            with self.subTest(text=text):
                self.assertEqual(classify_procedure(text).reason, "passport_service_not_immigration")
                self.assertEqual(assess_classification(text).reason, "passport_service")
        for text in ("report the renewed passport to Korean immigration", "여권 재발급 후 정보 변경 신고"):
            with self.subTest(text=text):
                self.assertEqual(classify_procedure(text).fine, "registration_info_report")
                self.assertIsNone(assess_classification(text))
        self.assertEqual(classify_procedure("stay extension documents include a passport copy").fine,
                         "extension")
        self.assertIsNone(pb._detect_task_type("I renewed my passport at the embassy"))

    def test_card_initial_vs_reissue(self):
        for text in ("apply for my first residence card", "외국인등록증 처음 발급 신청"):
            with self.subTest(text=text):
                self.assertEqual(classify_procedure(text).fine, "registration")
                self.assertIsNone(assess_classification(text))
        self.assertEqual(classify_procedure("residence card replacement").fine, "card_reissue")
        self.assertEqual(classify_procedure("외국인등록증을 분실했습니다").fine, "card_reissue")
        self.assertEqual(assess_classification("my new residence card").reason, "card_action_missing")

    def test_real_ask_path_does_not_generate_or_retrieve_unverified_lists(self):
        samples = (
            ("F-10 연장 가능한가요?", "unknown_status"),
            ("D-2 및 E-7 제출서류", "multiple_statuses"),
            ("F-6에서 E-9으로 변경 가능할까요?", "transition_requires_review"),
            ("대사관에서 여권을 갱신했습니다", "passport_service"),
            ("외국인등록증 처음인가 재발급인가", "card_action_missing"),
        )
        for question, reason in samples:
            with self.subTest(reason=reason), \
                 patch.object(pb, "_select_grounding", side_effect=AssertionError("no grounding")), \
                 patch.object(pb, "_openrouter_complete_with_candidates",
                              side_effect=AssertionError("no model")):
                response = asyncio.run(pb._ask_internal(pb.AskRequest(
                    question=question, lang="ko", stream=True,
                )))
                self.assertEqual(response.provider, "deterministic")
                self.assertEqual(response.model, "classification_guard")
                self.assertFalse(response.grounding_used)
                self.assertEqual(response.source_confidence_level, "none")
                self.assertTrue(response.requires_official_confirmation)
                self.assertTrue(response.answer)
                self.assertIsNone(response.visa_code_detected)


if __name__ == "__main__":
    unittest.main()
