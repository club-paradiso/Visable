"""Check 2026.10 source-backed structured eligibility and document corrections."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "visa_data.json"
VISA = ROOT / "docs/source-manuals/2026-10-19/extracted/visa_manual_261019.txt"
STAY = ROOT / "docs/source-manuals/2026-10-19/extracted/stay_manual_261019.txt"

class OctoberRequirementsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.visas = {r["code"]: r for r in json.loads(DATA.read_text(encoding="utf-8"))}
        cls.visa_original = VISA.read_text(encoding="utf-8")
        cls.stay_original = STAY.read_text(encoding="utf-8")

    def test_d2_financial_evidence_validity_and_holder(self):
        self.assertIn("신청일 기준 30일 이내 발급된 증명서", self.stay_original)
        self.assertIn("체류허가기간 동안 유지", self.stay_original)
        docs = self.visas["D-2"]["procedures"]["statusChange"]["requiredDocs"]["conditionalDocs"]
        self.assertTrue(any("30일 이내" in x and "부모 사망" in x for x in docs))
        visa_docs = self.visas["D-2"]["procedures"]["visaIssuance"]["requiredDocs"]["conditionalDocs"]
        self.assertTrue(any("1년 등록금" in x and "30일 이내" in x for x in visa_docs))

    def test_nomad_requires_substatus_specific_documents(self):
        # F-1-D stay checklists live in the F-1 parent's procedures.extension.variants[]
        # (statusCode "F-1-D") so the subcode modal renders them.
        variant = next(
            v for v in self.visas["F-1"]["procedures"]["extension"]["variants"]
            if v.get("statusCode") == "F-1-D"
        )
        self.assertIn("1회 1년씩 최장 3년", self.stay_original)
        self.assertIn("체류기간 연장은 불가", self.stay_original)
        self.assertIn("3년", variant["scenarioKo"])
        docs=variant["requiredDocs"]["conditionalDocs"]
        self.assertTrue(all(r["manualType"] == "stay" for r in variant["manualRefs"]))
        self.assertTrue(any("숙소 이용기록" in x and "본인 명의" in x for x in docs))
        self.assertEqual(self.visas["F-1"]["procedures"]["statusChange"]["requiredDocs"]["requiredDocs"], [])

    def test_e74_salary_and_income_history(self):
        self.assertIn("2,589만원", self.stay_original)
        self.assertIn("‘21년~’25년", self.stay_original)
        sub=next(s for s in self.visas["E-7"]["subCodes"] if s["code"]=="E-7-4")
        self.assertIn("2,589만원",sub["addReq"])
        self.assertIn("2021년~2025년",sub["addReq"])
        self.assertTrue(sub["needsManualReview"])

    def test_f6_topik_ibt_is_conditional(self):
        self.assertIn("TOPIK IBT 성적증명서 포함",self.visa_original)
        docs=self.visas["F-6"]["procedures"]["visaIssuance"]["requiredDocs"]["conditionalDocs"]
        self.assertTrue(any("TOPIK IBT" in x for x in docs))

    def test_d91_disqualification_not_global(self):
        self.assertIn("범칙금 처분을 받은 자",self.stay_original)
        docs=self.visas["D-9"]["procedures"]["statusChange"]["requiredDocs"]["conditionalDocs"]
        self.assertTrue(any("D-9-1" in x for x in docs))
        self.assertTrue(any("D-9-1" in x for x in self.visas["D-9"]["procedures"]["statusChange"]["notes"]))

    def test_change_provenance_does_not_claim_approval(self):
        for code in ("D-2","F-1","E-7","F-2","F-6","D-9"):
            change=self.visas[code]["manual202610StructuredUpdate"]
            self.assertEqual(change["edition"],"2026.10")
            self.assertEqual(change["status"],"source_text_integrated_conditional_review")
            self.assertTrue(change["source_refs"])
            self.assertTrue(all(x["verification"].endswith("not_independently_approved") for x in change["source_refs"]))

if __name__=="__main__":
    unittest.main()
