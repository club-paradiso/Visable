"""Non-existent status symbols must not be routed as real statuses.

Source: Enforcement Decree of the Immigration Act (MST 290501, in force
2026-10-02), Annexes 1, 1-2 and 1-3. There is no F-10 status.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.knowledge.coverage import decide  # noqa: E402
from services.knowledge.models import OFFICIAL_STATUS_PARENTS  # noqa: E402
from services.knowledge.understanding import understand  # noqa: E402


class StatusExistenceGateTest(unittest.TestCase):
    def test_f10_requires_confirmation_and_no_retrieval(self):
        for q in ("F-10 비자 연장하고 싶어요", "How do I apply for an F-10 visa?"):
            u = understand(q, status_code="F-10", subcode=None, task_type="extension")
            self.assertEqual(u.ambiguity, "unrecognized_status", q)
            self.assertIn("status_code_confirmation", u.missing_decisive_facts, q)
            self.assertIsNone(u.retrieval_procedure, q)
            self.assertEqual(decide(u, None).state, "NEEDS_CLARIFICATION", q)

    def test_real_two_digit_statuses_are_untouched(self):
        for code in ("D-10", "E-10", "F-5", "C-4"):
            u = understand(f"{code} 체류기간 연장 서류", status_code=code, subcode=None, task_type="extension")
            self.assertNotEqual(u.ambiguity, "unrecognized_status", code)
            self.assertNotIn("status_code_confirmation", u.missing_decisive_facts, code)

    def test_official_set_matches_decree_annexes(self):
        self.assertNotIn("F-10", OFFICIAL_STATUS_PARENTS)
        self.assertNotIn("C-2", OFFICIAL_STATUS_PARENTS)
        self.assertEqual(len(OFFICIAL_STATUS_PARENTS), 37)


if __name__ == "__main__":
    unittest.main()
