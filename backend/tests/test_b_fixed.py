"""Lossless classification of explicit public, synthetic status questions."""
import unittest

from services.status_code_parser import explicit_codes, supplemental_task, transition_pair
from services.immigration_tools import extract_immigration_facts
from services.legal_analysis import extract_immigration_facts as legal_facts
from paradiso_backend import _detect_visa_codes, _detect_task_type


class BFixedTests(unittest.TestCase):
    def test_subcodes_remain_exact_across_extraction_stacks(self):
        for code in ("D-2-1", "D-4-2K", "F-2-7S", "E-7-1A", "D-2-T1"):
            with self.subTest(code=code):
                self.assertEqual(explicit_codes(code + "비자"), [code])
                self.assertEqual(extract_immigration_facts(code)["statusCodes"], [code])
                self.assertEqual(legal_facts(code)["current_status"], code)
                parent = "-".join(code.split("-")[:2])
                self.assertEqual(_detect_visa_codes(None, None, code + "비자"), (parent, code))

    def test_false_positives_do_not_truncate_a_longer_token(self):
        for text in ("D-4-2KX", "E-7-1ABC", "D 2", "FD-2", "D-2-unknown"):
            with self.subTest(text=text):
                self.assertEqual(explicit_codes(text), [])
                self.assertEqual(_detect_visa_codes(None, None, text), (None, None))

    def test_directional_transitions(self):
        for text in (
            "D-10에서 E-7-1로 체류자격 변경",
            "change status from D-10 to E-7-1",
            "D-10转为E-7-1签证",
            "D-10からE-7-1に在留資格変更",
            "đổi D-10 sang E-7-1",
            "сменить D-10 на E-7-1 статус",
        ):
            with self.subTest(text=text):
                self.assertEqual(transition_pair(text), ("D-10", "E-7-1"))
                self.assertEqual(supplemental_task(text), "status_change")
                self.assertEqual(_detect_visa_codes(None, None, text), ("E-7", "E-7-1"))
                facts = legal_facts(text)
                self.assertEqual((facts["current_status"], facts["target_status"]), ("D-10", "E-7-1"))

    def test_distinct_procedures(self):
        for text, task in (
            ("D-2 재입국허가", "reentry"),
            ("D-2 re-entry permit", "reentry"),
            ("E-7 사증발급인정서", "visa_issuance_confirmation"),
            ("E-7 visa issuance", "visa_issuance"),
            ("E-7 전자사증", "visa_issuance"),
        ):
            with self.subTest(text=text):
                self.assertEqual(supplemental_task(text), task)
                self.assertEqual(_detect_task_type(text), task)

    def test_multiple_codes_without_direction_abstains(self):
        self.assertEqual(_detect_visa_codes(None, None, "D-2 및 E-7 서류"), (None, None))
        self.assertEqual(_detect_visa_codes("F-2-7S", None, "D-2 및 E-7 서류"), ("F-2", "F-2-7S"))


if __name__ == "__main__":
    unittest.main()
