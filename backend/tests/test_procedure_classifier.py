"""Procedure contrasts authored from the public taxonomy, separate from v0."""
import unittest

from services.procedure_classifier import classify_procedure, FINE_TO_COARSE
from services.knowledge.understanding import understand


class FineProcedureTests(unittest.TestCase):
    def test_object_action_contrasts(self):
        cases = [
            ("residence card replacement", "card_reissue"),
            ("my passport is lost", None),
            ("report the renewed passport", "registration_info_report"),
            ("여권 재발급", None),
            ("여권 재발급 후 정보 변경 신고", "registration_info_report"),
            ("stay extension documents include a passport copy", "extension"),
            ("외국인등록증을 분실했습니다", "card_reissue"),
            ("외국인등록 처음 신청", "registration"),
            ("외국인등록증", None),
            ("주소 변경 신고", "residence_report"),
            ("체류기간 연장 때 체류지 입증서류", "extension"),
            ("소속 학교 변경 신고", "registration_info_report"),
            ("이름 변경 신고", "registration_info_report"),
            ("근무처 변경 허가", "workplace_change"),
            ("근무처 추가", "workplace_change"),
            ("근무처 신고", "workplace_report"),
            ("시간제취업 허가", "part_time_work"),
            ("체류자격외 활동허가", "activities_outside_status"),
            ("사증발급인정서 신청", "visa_issuance_confirmation"),
            ("전자사증 발급", "electronic_visa"),
            ("사증 발급", "visa_issuance"),
            ("체류자격 변경", "status_change"),
            ("허가조건 변경", "program_condition_change"),
            ("재입국 허가", "reentry"),
            ("체류자격 부여", "status_grant"),
        ]
        for text, fine in cases:
            with self.subTest(text=text):
                self.assertEqual(classify_procedure(text).fine, fine)

    def test_language_is_not_status_specific(self):
        for text, fine in [
            ("在留カードを紛失して再発行", "card_reissue"),
            ("外国人登录证丢失补办", "card_reissue"),
            ("thẻ cư trú bị mất, cấp lại", "card_reissue"),
            ("D-6からE-2-1に在留資格変更", "status_change"),
            ("G-1-6 转为 F-3-1", "status_change"),
            ("продлить пребывание D-6", "extension"),
            ("F-3-1 re-entry permit", "reentry"),
        ]:
            with self.subTest(text=text):
                self.assertEqual(classify_procedure(text).fine, fine)

    def test_coarse_is_derived_only_when_equivalent_exists(self):
        self.assertIsNone(FINE_TO_COARSE["card_reissue"])
        self.assertIsNone(FINE_TO_COARSE["part_time_work"])
        for text, task in [
            ("D-2-3 part-time work permission", "activities_outside_status"),
            ("D-2-3 residence card reissue", "extension"),
            ("D-2-3 electronic visa", "visa_issuance"),
        ]:
            with self.subTest(text=text):
                u = understand(text, status_code="D-2", subcode="D-2-3", task_type=task)
                self.assertIsNotNone(u.procedure_fine)
                self.assertIsNone(u.retrieval_procedure)
                self.assertEqual(u.subcode, "D-2-3")
        u = understand("D-2-3 stay extension", status_code="D-2", subcode="D-2-3", task_type="extension")
        self.assertEqual(u.retrieval_procedure, "extension")


if __name__ == "__main__":
    unittest.main()
