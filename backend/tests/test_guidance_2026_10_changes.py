"""Authored guidance that cites a 2026.10 change must be backed by the 2026.10 text.

The 2026-10-19 stay manual changed a few passages that the authored guidance
(scripts/status_guidance/author_rules.py) already covers: the F-1-D extension.
Every sentence added from the new text has its source phrase here; the test
fails if the 2026.10 HWP extraction no longer carries it, so the guidance cannot
drift away from the edition it cites. Passages the guidance does not cover (D-2
status change, D-9-1, E-7-4 income, F-1-D change/registration) stay source-only
and are listed in audits/manual-edition-2026-10-promotion/README.md.
"""
from __future__ import annotations

import json
import re
import unittest
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAY_TEXT = ROOT / "docs/source-manuals/2026-10-19/extracted/full_text/stay_manual_261019.txt"
RULES = ROOT / "data/guidance-rules-202609.json"


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


class Guidance2026_10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = norm(STAY_TEXT.read_text(encoding="utf-8"))
        cls.rules = json.loads(RULES.read_text(encoding="utf-8"))
        cls.f1d = next(g for g in cls.rules["guidance"] if g["target"] == "F-1-D" and g["procedure"] == "extension")

    def test_unemployment_condition_is_in_the_2026_10_text(self):
        phrase = "입국 후 중도 실직한 경우 신고 및 출국할 의무는 없으나, 체류기간 연장은 불가"
        self.assertIn(norm(phrase), self.text)
        self.assertTrue(any("중도 실직" in c for c in self.f1d["conditions_ko"]))
        self.assertTrue(any("lose your job" in c for c in self.f1d["conditions_en"]))

    def test_regional_proof_note_is_in_the_2026_10_text(self):
        phrase = "비수도권 지역 등록자는 본인 명의 제출 필요"
        self.assertIn(norm(phrase), self.text)
        item = next(d for d in self.f1d["documents"] if d["ref"] == "regional_stay_proof")
        self.assertIn("본인 명의", item.get("notes_ko", ""))

    def test_both_additions_name_the_edition_they_come_from(self):
        added = [c for c in self.f1d["conditions_ko"] if "중도 실직" in c]
        item = next(d for d in self.f1d["documents"] if d["ref"] == "regional_stay_proof")
        for text in added + [item.get("notes_ko", "")]:
            self.assertIn("2026.10", text)


if __name__ == "__main__":
    unittest.main()
