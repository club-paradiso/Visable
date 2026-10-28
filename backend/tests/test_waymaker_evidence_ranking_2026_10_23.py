"""Waymaker live re-check 2026-10-23: everyday wording and sub-code-only pages.

After the 2026.9 manual excerpts went live, two faults remained:

* "E-7 비자로 일하고 있는데 회사를 옮기려면 …" was not detected as 근무처 변경, so
  retrieval fell back to a generic activity-scope search and cited unrelated
  pages (p.722, p.507, p.524) instead of the 근무처 변경·추가 pages (p.221-222).
* For that E-7 question an E-7-H-only page was sent too, and the model wrote it
  up as an E-7-wide rule despite the "E-7-H 전용" label.

Assertions are about task types, page ranges and applicability labels, never
about excerpt text (the index is rebuilt from the manuals).

    python3 -m pytest backend/tests/test_waymaker_evidence_ranking_2026_10_23.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import paradiso_backend as pb  # noqa: E402
from services import manual_evidence as me  # noqa: E402


def _retrieve(question: str, sub_code=None):
    code = pb._detect_visa_code(None, None, question)
    task = pb._detect_task_type(question)
    return code, task, me.retrieve_manual_evidence(
        question, visa_code=code, visa_sub_code=sub_code, task_type=task,
    )


class EverydayWorkplaceWordingTests(unittest.TestCase):
    def test_everyday_job_change_wording_is_workplace_change(self):
        for text in (
            "E-7 비자로 일하고 있는데 회사를 옮기려면 어떤 절차가 필요한가요?",
            "E-7인데 직장 바꾸고 싶어요",
            "E-9인데 다른 회사로 옮길 수 있나요?",
            "회사를 변경하려고 합니다",
        ):
            with self.subTest(text=text):
                self.assertEqual(pb._detect_task_type(text), "workplace_change")

    def test_unrelated_company_wording_is_not_workplace_change(self):
        for text in ("회사 근처로 이사를 했어요", "회사에서 재직증명서를 받았어요"):
            with self.subTest(text=text):
                self.assertNotEqual(pb._detect_task_type(text), "workplace_change")

    def test_e7_job_change_cites_workplace_change_pages(self):
        _, task, ev = _retrieve("E-7 비자로 일하고 있는데 회사를 옮기려면 어떤 절차가 필요한가요?")
        self.assertEqual(task, "workplace_change")
        self.assertEqual(ev["status"], me.STATUS_USED)
        pages = [e["page"] for e in ev["excerpts"]]
        # the E-7 근무처의 변경·추가 section opens at the foot of p.222 and runs to p.224 (documents)
        self.assertTrue(set(pages) & {222, 223, 224}, pages)
        self.assertTrue(all(e["scope"] == me.SCOPE_STAY for e in ev["excerpts"]))


class SubcodeOnlyPagesTests(unittest.TestCase):
    def test_parent_question_with_parent_evidence_gets_no_subcode_only_pages(self):
        for text in (
            "E-7 비자로 일하고 있는데 회사를 옮기려면 어떤 절차가 필요한가요?",
            "E-7 근무처 변경 절차",
        ):
            with self.subTest(text=text):
                _, _, ev = _retrieve(text)
                self.assertTrue(ev["excerpts"])
                levels = {e["applicability"] for e in ev["excerpts"]}
                self.assertNotIn("subcode_specific", levels)

    def test_subcode_only_family_keeps_its_labelled_pages(self):
        # F-6 extension rules exist only per F-6-1/2/3; dropping them left only
        # generic F-6 pages (table of contents and the like).
        _, task, ev = _retrieve("F-6 결혼이민 체류기간 연장 준비는 어떻게 하나요?")
        self.assertEqual(task, "extension")
        pages = [e["page"] for e in ev["excerpts"]]
        # The F-6 extension section (F-6-1 연장 … F-6-3 "최초 기간연장 후
        # 혼인단절") is pp.500-505 in the 2026.10 stay manual (pp.498-503 in 2026.9).
        self.assertTrue(pages and all(500 <= p <= 505 for p in pages), pages)
        self.assertTrue(all(e["applicability"] == "subcode_specific" for e in ev["excerpts"]))

    def test_exact_subcode_question_is_unchanged(self):
        _, _, ev = _retrieve("G-1-5 자격으로 체류 중인데 취업할 수 있나요?", sub_code="G-1-5")
        levels = [e["applicability"] for e in ev["excerpts"]]
        self.assertIn("exact_subcode", levels)


class D10ToE7Tests(unittest.TestCase):
    def test_d10_to_e7_still_gets_stay_manual_d10_pages(self):
        # Deliberately not a status_change task (test_scenario_procedure_variants
        # and the D-10 golden case keep D-10-1 variants from being forced), but
        # the work wording still retrieves D-10 stay-manual pages.
        _, _, ev = _retrieve("D-10 비자 상태인데 E-7 취업을 희망합니다. 변경 가능한가요?")
        self.assertTrue(ev["excerpts"])
        self.assertTrue(all(e["scope"] == me.SCOPE_STAY for e in ev["excerpts"]))
        self.assertTrue(all("D-10" in (e["applies_to"] or ["D-10"])[0] for e in ev["excerpts"]))


if __name__ == "__main__":
    unittest.main()
