"""Expanded immigration-scenario grounding coverage (Part H + Part O/P).

The goal is NOT to hard-code final legal answers. These tests verify that
Paradiso, for a broad set of immigration scenarios:

  * detects the status / question type and plans appropriate law retrieval,
  * separates direct evidence from related context,
  * does not invent checklists or overconfident legal conclusions,
  * preserves source-confidence metadata,
  * surfaces useful official-confirmation questions.

All external calls are mocked/offline. Law grounding runs in ``audit`` mode
with NO credential configured, so it is "attempted" but performs no network
call (``law_api_not_configured`` short-circuits before any transport).

    python3 -m pytest backend/tests/test_law_grounding_scenarios.py -q
"""
from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import answer_quality as aq  # noqa: E402
from services import law_tools as lt  # noqa: E402
from services.grounding_config import GroundingConfig  # noqa: E402

AUDIT = GroundingConfig(mode="audit")  # intent-driven, no credential -> no network
_HANGUL = re.compile(r"[가-힣]")


def _pb():
    import paradiso_backend
    return paradiso_backend


class ScenarioBase(unittest.TestCase):
    def setUp(self):
        for key in ("LAW_API_OC", "LAW_API_KEY", "LAW_GROUNDING_MODE"):
            os.environ.pop(key, None)

    def pack(self, question, visa=None):
        pb = _pb()
        task_type = pb._detect_task_type(question)
        detected = visa or pb._detect_visa_codes(None, None, question)[0]
        lang = "ko" if _HANGUL.search(question) else "en"
        return lt.build_law_evidence_pack(
            question, visa_code=detected, task_type=task_type, lang=lang, config=AUDIT,
        )

    # -- shared invariants --------------------------------------------------
    def assert_attempted(self, pack):
        self.assertTrue(pack["law_api_attempted"], "law grounding should be attempted")

    def assert_no_invented_direct_source(self, pack):
        # Without manual grounding, nothing may be presented as a direct source.
        self.assertEqual(pack["direct_manual_sources"], [])
        self.assertNotEqual(pack["answer_quality_mode"], aq.SOURCE_CONFIRMED)

    def assert_anchors(self, pack, *tokens):
        joined = " ".join(pack["planned_law_queries"])
        for token in tokens:
            self.assertIn(token, joined, f"planned queries missing anchor: {token}")

    def assert_has_official_questions(self, pack):
        self.assertTrue(
            pack["official_confirmation_questions"]
            or pack["official_confirmation_questions_localized"],
            "expected official-confirmation questions",
        )


# ---------------------------------------------------------------------------
# A. H-1 / Working Holiday
# ---------------------------------------------------------------------------
class H1WorkingHolidayScenarios(ScenarioBase):
    def test_01_h1_credit_summer_semester(self):
        pack = self.pack(
            "Can I take summer semester course in Korean universities even though I have a H-1 visa?",
            visa="H-1",
        )
        self.assertEqual(pack["visa_code"], "H-1")
        self.assertEqual(pack["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        self.assertIn(pack["risk_level"], ("medium", "high"))
        self.assert_attempted(pack)
        self.assert_anchors(pack, "활동범위", "체류자격외활동", "체류자격 변경", "관광취업")
        # D-2 / D-4 are related, NOT direct H-1 evidence.
        self.assertEqual(pack["related_statuses_not_sources"], ["D-2", "D-4"])
        self.assert_no_invented_direct_source(pack)
        self.assertEqual(pack["answer_quality_mode"], aq.SOURCE_LIMITED)
        self.assertIn("legal_analysis", pack)
        self.assertTrue(pack["legal_analysis"]["missing_direct_authority"])
        self.assertIn("permitted activity scope", pack["legal_analysis"]["main_issue"])
        self.assertIn(pack["legal_analysis"]["confidence"], ("contextual", "analogical", "limited", "unavailable"))

    def test_02_h1_korean_seasonal_semester(self):
        pack = self.pack("H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?", visa="H-1")
        self.assertEqual(pack["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        self.assert_anchors(pack, "활동범위", "체류자격외활동", "관광취업")
        # Korean localized confirmation questions for the H-1 study case.
        q = " ".join(pack["official_confirmation_questions_localized"])
        for token in ("학점 인정", "정규과정 여부", "수업 기간/시간", "체류 목적", "H-1 취업 병행 여부"):
            self.assertIn(token, q, token)

    def test_03_h1_non_credit_cultural_class(self):
        pack = self.pack("H-1으로 단기 비학점 한국문화 수업을 들어도 되나요?", visa="H-1")
        self.assertEqual(pack["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)

    def test_04_h1_side_work(self):
        pack = self.pack("H-1으로 카페에서 일하면서 다른 아르바이트도 추가로 할 수 있나요?", visa="H-1")
        self.assertEqual(pack["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        self.assert_anchors(pack, "관광취업", "활동범위")
        self.assert_has_official_questions(pack)


# ---------------------------------------------------------------------------
# B. D-2 / Student  &  C. D-4 / Language training
# ---------------------------------------------------------------------------
class StudentScenarios(ScenarioBase):
    def test_05_d2_extension_documents(self):
        # Manual grounding exists for D-2 extension -> source_confirmed.
        pack = self.pack("What documents do I need for D-2 extension?", visa="D-2")
        self.assertEqual(pack["question_type"], lt.LQ_DOCUMENTS_NEEDED)
        pack2 = lt.build_law_evidence_pack(
            "What documents do I need for D-2 extension?", visa_code="D-2",
            task_type="extension", manual_present=True, config=AUDIT,
        )
        self.assertEqual(pack2["answer_quality_mode"], aq.SOURCE_CONFIRMED)

    def test_06_d2_part_time(self):
        pack = self.pack("Can I work part-time on a D-2 visa in Korea?", visa="D-2")
        self.assertEqual(pack["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        self.assert_attempted(pack)
        self.assert_has_official_questions(pack)

    def test_07_d2_internship(self):
        pack = self.pack("D-2 유학생인데 방학 중 인턴십을 할 수 있나요?", visa="D-2")
        self.assertEqual(pack["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        self.assert_anchors(pack, "유학", "인턴", "체류자격외활동", "활동범위")

    def test_08_d2_school_transfer_report(self):
        pack = self.pack("D-2 체류 중 학교를 옮기면 출입국에 신고해야 하나요?", visa="D-2")
        self.assertIn(pack["question_type"], (lt.LQ_DEADLINE_OR_REPORT, lt.LQ_STATUS_CHANGE))
        self.assert_attempted(pack)

    def test_09_d2_leave_of_absence(self):
        pack = self.pack("D-2인데 휴학하면 체류자격에 문제가 생기나요?", visa="D-2")
        self.assertEqual(pack["question_type"], lt.LQ_HIGH_RISK_EXCEPTION)
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)

    def test_10_d4_paid_internship(self):
        pack = self.pack("Can I do a paid internship while staying on D-4?", visa="D-4")
        self.assertEqual(pack["visa_code"], "D-4")
        self.assertEqual(pack["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)

    def test_11_d4_to_d2_change(self):
        pack = self.pack("D-4 어학연수에서 D-2 유학으로 변경하려면 어떻게 해야 하나요?")
        self.assertEqual(pack["question_type"], lt.LQ_STATUS_CHANGE)
        self.assertEqual(pack["source_status"], "D-4")
        self.assertEqual(pack["target_status"], "D-2")
        self.assert_anchors(pack, "체류자격 변경")


# ---------------------------------------------------------------------------
# D. D-10  &  E. E-7
# ---------------------------------------------------------------------------
class JobSeekerAndEmploymentScenarios(ScenarioBase):
    def test_12_d10_freelance(self):
        pack = self.pack("D-10 구직비자로 프리랜서 일을 해도 되나요?", visa="D-10")
        self.assertEqual(pack["visa_code"], "D-10")
        self.assertEqual(pack["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        self.assert_anchors(pack, "구직", "취업활동", "체류자격외활동", "활동범위")
        self.assert_no_invented_direct_source(pack)

    def test_13_d10_to_e7(self):
        pack = self.pack("D-10에서 E-7으로 바꾸려면 어떤 절차가 필요한가요?")
        self.assertEqual(pack["question_type"], lt.LQ_STATUS_CHANGE)
        self.assertEqual(pack["source_status"], "D-10")
        self.assertEqual(pack["target_status"], "E-7")

    def test_14_e7_workplace_change(self):
        pack = self.pack("E-7으로 근무처를 바꾸려면 어떤 절차가 필요한가요?", visa="E-7")
        self.assertIn(pack["question_type"],
                      (lt.LQ_DEADLINE_OR_REPORT, lt.LQ_PROCEDURE, lt.LQ_STATUS_CHANGE))
        self.assert_attempted(pack)

    def test_15_e7_side_job(self):
        pack = self.pack("Can I do a side job while on E-7?", visa="E-7")
        self.assertEqual(pack["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        self.assert_has_official_questions(pack)

    def test_16_e7_job_code(self):
        pack = self.pack("E-7 직종코드는 어떻게 확인하나요?", visa="E-7")
        self.assertEqual(pack["question_type"], lt.LQ_PROCEDURE_OR_CODE_LOOKUP)
        # Must not invent occupation eligibility -> no confirmed direct source.
        self.assert_no_invented_direct_source(pack)
        self.assertTrue(pack["official_confirmation_questions_localized"])


# ---------------------------------------------------------------------------
# F. F-4 / Overseas Korean
# ---------------------------------------------------------------------------
class OverseasKoreanScenarios(ScenarioBase):
    def test_17_b2_c3_to_f4(self):
        pack = self.pack("B-2나 C-3로 입국한 뒤 F-4로 변경할 수 있나요?")
        self.assertEqual(pack["question_type"], lt.LQ_STATUS_CHANGE)
        self.assertEqual(pack["target_status"], "F-4")
        # Related/entry statuses must not be presented as direct F-4 sources.
        self.assert_no_invented_direct_source(pack)

    def test_18_h2_to_f4(self):
        pack = self.pack("H-2에서 F-4로 변경하려면 어떤 조건과 서류가 필요한가요?")
        self.assertEqual(pack["source_status"], "H-2")
        self.assertEqual(pack["target_status"], "F-4")
        self.assertIn(pack["question_type"], (lt.LQ_STATUS_CHANGE, lt.LQ_DOCUMENTS_NEEDED))
        self.assert_no_invented_direct_source(pack)

    def test_19_f4_domestic_residence_report(self):
        pack = self.pack("F-4 재외동포는 국내거소신고를 해야 하나요?", visa="F-4")
        self.assertEqual(pack["question_type"], lt.LQ_DEADLINE_OR_REPORT)
        self.assert_anchors(pack, "국내거소신고", "재외동포", "신고")

    def test_20_f4_employment_limitation(self):
        pack = self.pack("F-4도 아무 일이나 취업할 수 있나요?", visa="F-4")
        self.assertEqual(pack["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)


# ---------------------------------------------------------------------------
# G. F-6 / Marriage migrant  (high-risk edge cases)
# ---------------------------------------------------------------------------
class MarriageMigrantScenarios(ScenarioBase):
    def test_21_f6_extension_documents(self):
        pack = self.pack("F-6 체류기간 연장에 필요한 서류는 무엇인가요?", visa="F-6")
        self.assertEqual(pack["question_type"], lt.LQ_DOCUMENTS_NEEDED)
        self.assert_no_invented_direct_source(pack)

    def test_22_f6_divorce_extension(self):
        pack = self.pack("F-6인데 이혼 후에도 체류기간 연장이 가능한가요?", visa="F-6")
        self.assertEqual(pack["question_type"], lt.LQ_HIGH_RISK_EXCEPTION)
        self.assertEqual(pack["risk_level"], "high")
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)
        self.assert_has_official_questions(pack)

    def test_23_f6_spouse_death(self):
        pack = self.pack("F-6 배우자가 사망했는데 체류기간 연장이 가능한가요?", visa="F-6")
        self.assertEqual(pack["question_type"], lt.LQ_HIGH_RISK_EXCEPTION)
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)

    def test_24_f6_domestic_violence(self):
        pack = self.pack("F-6인데 가정폭력 때문에 별거 중이면 체류에 문제가 생기나요?", visa="F-6")
        self.assertEqual(pack["question_type"], lt.LQ_HIGH_RISK_EXCEPTION)
        self.assertEqual(pack["risk_level"], "high")
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)


# ---------------------------------------------------------------------------
# H. G-1 / humanitarian
# ---------------------------------------------------------------------------
class HumanitarianScenarios(ScenarioBase):
    def test_25_g1_medical(self):
        pack = self.pack("G-1으로 치료 목적 체류를 하려면 어떤 절차를 봐야 하나요?", visa="G-1")
        self.assertEqual(pack["question_type"], lt.LQ_HIGH_RISK_EXCEPTION)
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)

    def test_26_g1_litigation(self):
        pack = self.pack("소송 중이면 G-1 체류가 가능한가요?", visa="G-1")
        self.assertEqual(pack["question_type"], lt.LQ_HIGH_RISK_EXCEPTION)
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)

    def test_27_g1_humanitarian(self):
        pack = self.pack("인도적 사유로 G-1 체류를 신청할 수 있나요?", visa="G-1")
        self.assertEqual(pack["question_type"], lt.LQ_HIGH_RISK_EXCEPTION)
        self.assert_attempted(pack)
        self.assertIn(pack["answer_quality_mode"], (aq.SOURCE_LIMITED, aq.SOURCE_UNAVAILABLE))


# ---------------------------------------------------------------------------
# I. Short-term statuses
# ---------------------------------------------------------------------------
class ShortTermScenarios(ScenarioBase):
    def test_28_b2_to_language_school(self):
        pack = self.pack("B-2 무비자로 들어와서 한국어학당을 다닐 수 있나요?", visa="B-2")
        self.assertIn(pack["question_type"], (lt.LQ_ACTIVITY_ON_STATUS, lt.LQ_STATUS_CHANGE))
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)

    def test_29_c3_paid_work(self):
        pack = self.pack("C-3로 한국에 와서 단기 알바를 해도 되나요?", visa="C-3")
        self.assertEqual(pack["visa_code"], "C-3")
        self.assertEqual(pack["question_type"], lt.LQ_ACTIVITY_ON_STATUS)
        self.assert_has_official_questions(pack)
        self.assert_no_invented_direct_source(pack)

    def test_30_c3_business_vs_paid(self):
        pack = self.pack("C-3로 출장 회의는 가능한데 돈 받는 강연도 가능한가요?", visa="C-3")
        self.assertEqual(pack["visa_code"], "C-3")
        self.assert_attempted(pack)

    def test_31_c4_vs_c3(self):
        pack = self.pack("C-4와 C-3는 단기 취업 가능 여부가 어떻게 다른가요?")
        self.assertIn(pack["question_type"], (lt.LQ_COMPARISON, lt.LQ_ACTIVITY_ON_STATUS))
        self.assertIn("C-4", pack["detected_statuses"])
        self.assertIn("C-3", pack["detected_statuses"])
        self.assert_attempted(pack)


# ---------------------------------------------------------------------------
# J. Registration / reporting / deadlines
# ---------------------------------------------------------------------------
class ReportingScenarios(ScenarioBase):
    def test_32_foreigner_registration_deadline(self):
        pack = self.pack("외국인등록은 입국 후 언제까지 해야 하나요?")
        self.assertEqual(pack["question_type"], lt.LQ_DEADLINE_OR_REPORT)
        self.assert_attempted(pack)

    def test_33_address_change_report(self):
        pack = self.pack("체류지를 옮기면 언제 신고해야 하나요?")
        self.assertEqual(pack["question_type"], lt.LQ_DEADLINE_OR_REPORT)
        self.assert_anchors(pack, "체류지 변경", "신고", "외국인등록")

    def test_34_passport_change_report(self):
        pack = self.pack("여권 번호가 바뀌면 출입국에 신고해야 하나요?")
        self.assertEqual(pack["question_type"], lt.LQ_DEADLINE_OR_REPORT)
        self.assert_anchors(pack, "여권", "신고")

    def test_35_workplace_change_report(self):
        pack = self.pack("근무처 변경 신고는 언제 해야 하나요?")
        self.assertEqual(pack["question_type"], lt.LQ_DEADLINE_OR_REPORT)
        self.assert_anchors(pack, "근무처 변경", "신고")

    def test_36_reentry_permit(self):
        pack = self.pack("한국에서 출국했다가 다시 들어오려면 재입국허가가 필요한가요?")
        self.assertIn(pack["question_type"], (lt.LQ_DEADLINE_OR_REPORT, lt.LQ_PROCEDURE))
        self.assert_attempted(pack)
        self.assert_has_official_questions(pack)


# ---------------------------------------------------------------------------
# K. Overstay / urgent risk
# ---------------------------------------------------------------------------
class UrgentRiskScenarios(ScenarioBase):
    def test_37_one_day_overstay(self):
        pack = self.pack("체류기간이 하루 지났는데 어떻게 해야 하나요?")
        self.assertEqual(pack["question_type"], lt.LQ_HIGH_RISK_EXCEPTION)
        self.assertEqual(pack["risk_level"], "high")
        self.assert_attempted(pack)
        # No invented fine/penalty amount and no guaranteed outcome.
        self.assert_no_invented_direct_source(pack)

    def test_38_missed_reporting_deadline(self):
        pack = self.pack("주소 변경 신고를 늦게 했으면 벌금이 나오나요?")
        self.assertIn(pack["question_type"], (lt.LQ_HIGH_RISK_EXCEPTION, lt.LQ_DEADLINE_OR_REPORT))
        self.assert_attempted(pack)

    def test_39_status_cancellation_risk(self):
        pack = self.pack("학교를 그만두면 D-2 체류자격이 취소될 수 있나요?", visa="D-2")
        self.assertEqual(pack["question_type"], lt.LQ_HIGH_RISK_EXCEPTION)
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)


# ---------------------------------------------------------------------------
# L. Nationality / refugee / overseas Korean edge topics
# ---------------------------------------------------------------------------
class NationalityRefugeeScenarios(ScenarioBase):
    def test_40_naturalization_general(self):
        pack = self.pack("귀화 신청은 어떤 절차로 진행되나요?")
        self.assertEqual(pack["question_type"], lt.LQ_NATIONALITY)
        self.assert_anchors(pack, "국적법")
        self.assert_no_invented_direct_source(pack)

    def test_41_refugee_status(self):
        pack = self.pack("난민 신청 중이면 어떤 체류자격으로 머물 수 있나요?")
        self.assertEqual(pack["question_type"], lt.LQ_REFUGEE)
        self.assert_anchors(pack, "난민법")
        self.assert_no_invented_direct_source(pack)

    def test_42_overseas_korean_nationality_loss(self):
        pack = self.pack("국적상실 신고를 안 했는데 F-4 신청이 가능한가요?")
        self.assertEqual(pack["target_status"], "F-4")
        self.assert_attempted(pack)
        self.assert_no_invented_direct_source(pack)


# ---------------------------------------------------------------------------
# Cross-cutting: every scenario attempts grounding, never over-claims
# ---------------------------------------------------------------------------
ALL_SCENARIOS = [
    "Can I take summer semester course in Korean universities even though I have a H-1 visa?",
    "H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?",
    "D-2 유학생인데 방학 중 인턴십을 할 수 있나요?",
    "D-4 어학연수에서 D-2 유학으로 변경하려면 어떻게 해야 하나요?",
    "D-10에서 E-7으로 바꾸려면 어떤 절차가 필요한가요?",
    "F-6인데 이혼 후에도 체류기간 연장이 가능한가요?",
    "G-1으로 치료 목적 체류를 하려면 어떤 절차를 봐야 하나요?",
    "체류기간이 하루 지났는데 어떻게 해야 하나요?",
    "외국인등록은 입국 후 언제까지 해야 하나요?",
    "귀화 신청은 어떤 절차로 진행되나요?",
]


class CrossCuttingInvariants(ScenarioBase):
    def test_all_scenarios_attempt_and_plan(self):
        for q in ALL_SCENARIOS:
            with self.subTest(q=q):
                pack = self.pack(q)
                self.assertTrue(pack["law_api_attempted"], q)
                self.assertTrue(pack["planned_law_queries"], q)
                # Never source_confirmed without manual evidence.
                self.assertNotEqual(pack["answer_quality_mode"], aq.SOURCE_CONFIRMED, q)
                # Evidence summary is normalized text, not a raw API dump.
                self.assertNotIn("{", pack["evidence_summary"], q)

    def test_plans_are_deterministic(self):
        for q in ALL_SCENARIOS:
            with self.subTest(q=q):
                self.assertEqual(self.pack(q)["planned_law_queries"],
                                 self.pack(q)["planned_law_queries"], q)


# ---------------------------------------------------------------------------
# O. Language quality
# ---------------------------------------------------------------------------
class LanguageQualityTests(unittest.TestCase):
    def test_english_answer_has_no_cjk_legal_fragments(self):
        bad = "The sojourn资格 and 签证 status here"
        self.assertTrue(aq.scan_mixed_language_artifacts(bad, "en"))
        good = "Your sojourn status (체류자격) may need a change of status."
        self.assertEqual(aq.scan_mixed_language_artifacts(good, "en"), [])

    def test_korean_answer_is_clean(self):
        self.assertEqual(
            aq.scan_mixed_language_artifacts("체류자격 변경 절차를 확인하세요.", "ko"), [])

    def test_simplified_and_traditional_distinct(self):
        self.assertIn("简体", aq.answer_language_instruction("zh-CN"))
        self.assertIn("繁體", aq.answer_language_instruction("zh-TW"))


# ---------------------------------------------------------------------------
# P. Frontend / source-display compatibility (static checks)
# ---------------------------------------------------------------------------
class FrontendSourceDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai = (REPO_ROOT / "ai.html").read_text(encoding="utf-8")

    def test_friendly_unavailable_text_present(self):
        self.assertIn("Legal source lookup returned an unsupported response format", self.ai)

    def test_related_status_row_is_distinct_from_manual(self):
        self.assertIn("related-status", self.ai)
        self.assertIn("Related status to verify", self.ai)

    def test_copy_answer_uses_visible_answer_not_raw_json(self):
        # Copy path prefers copy_safe_answer / fallback_answer / answer.
        self.assertIn("copy_safe_answer", self.ai)

    def test_no_oc_credential_in_html(self):
        self.assertNotIn("OC=paradiso", self.ai)
        self.assertNotIn("LAW_API_OC=", self.ai)


if __name__ == "__main__":
    unittest.main(verbosity=2)
