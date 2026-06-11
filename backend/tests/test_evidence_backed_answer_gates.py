"""Tests for the evidence-backed answer-synthesis quality gate (Parts A-I).

These cover:

  * Answer-shape contract generation by legal issue type (Part A).
  * The deterministic ``evaluate_answer_shape`` gate catching the production
    "too vague / not based on manual / study-leak" failure mode (Part B).
  * The gate passing a genuinely useful answer.
  * Deterministic-synthesis repair of a weak live model answer via /api/ask
    (Part C) for the H-1 registration, E-7->F-2-99, G-1-5, H-1->F-2-99 change,
    and C-3 paid-work regression cases (Parts D/E).
  * Source-limitation placement, irrelevant-term, overconfidence guards
    (Parts B/G).
  * The new metadata fields appearing on the response (Part F).
  * The smoke harness statically recognizing the quality-gate metadata (Part H).

Run from repo root:

    python3 -m pytest backend/tests/test_evidence_backed_answer_gates.py -q
"""
from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
SMOKE = REPO_ROOT / "scripts" / "smoke_ai_live_quality.py"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import answer_shape as ashape  # noqa: E402
from services import legal_analysis as lanalysis  # noqa: E402

CANDS = ["qwen/qwen3-next-80b-a3b-instruct:free", "google/gemma-4-31b-it:free"]

# The exact production failure mode: vague, confirmation-first, disclaims the
# manual basis, points away without any practical analysis.
WEAK_KO = (
    "정확한 내용은 확인이 필요합니다. 본 답변은 공식 매뉴얼에 근거하지 않습니다. "
    "자세한 사항은 출입국에 문의하시기 바랍니다."
)


def _meta(issues, facts=None, certainty="limited", **extra):
    m = {
        "legal_issue_types": list(issues),
        "immigration_facts": facts or {},
        "legal_analysis_exists": True,
        "answer_certainty_level": certainty,
    }
    m.update(extra)
    return m


def _contract(issues, facts=None, certainty="limited"):
    return ashape.build_answer_shape_contract(
        legal_issue_types=list(issues),
        immigration_facts=facts or {},
        answer_certainty_level=certainty,
    )


# ---------------------------------------------------------------------------
# Part A — contract generation
# ---------------------------------------------------------------------------
class ContractGenerationTests(unittest.TestCase):
    def test_registration_contract_required_slots(self):
        c = _contract(["reporting_duty", "registration_or_residence_report"], {"current_status": "H-1"})
        self.assertEqual(c["contract_key"], ashape.CONTRACT_REGISTRATION)
        for slot in ("trigger_event", "deadline_basis_or_uncertainty", "filing_channel", "source_confidence"):
            self.assertIn(slot, c["required_slots"])

    def test_registration_deadline_contract_uses_registration_shape(self):
        c = _contract(["registration_deadline", "deadline_trigger"], {"current_status": "D-2"})
        self.assertEqual(c["contract_key"], ashape.CONTRACT_REGISTRATION)

    def test_study_contract_selected_for_study_on_non_study(self):
        c = _contract(["activity_scope", "study_on_non_study_status"], {"current_status": "G-1-5"})
        self.assertEqual(c["contract_key"], ashape.CONTRACT_STUDY)
        self.assertIn("study_status_comparison_if_relevant", c["required_slots"])

    def test_status_change_contract_drops_target_slot_when_absent(self):
        c = _contract(["status_change"], {"current_status": "H-1"})
        self.assertEqual(c["contract_key"], ashape.CONTRACT_STATUS_CHANGE)
        self.assertNotIn("target_status", c["required_slots"])
        c2 = _contract(["status_change"], {"current_status": "H-1", "target_status": "F-2-99"})
        self.assertIn("target_status", c2["required_slots"])

    def test_work_restriction_contract_for_c3_paid_work(self):
        c = _contract(["work_on_non_work_status", "employment_restriction"], {"current_status": "C-3"})
        self.assertEqual(c["contract_key"], ashape.CONTRACT_WORK_RESTRICTION)

    def test_residual_duty_uses_workplace_change_contract(self):
        c = _contract(
            ["post_status_change_residual_duty", "status_change", "activity_scope"],
            {"current_status": "F-2-99", "previous_status": "E-7"},
        )
        self.assertEqual(c["contract_key"], ashape.CONTRACT_WORKPLACE_CHANGE)
        self.assertIn("previous_status_comparative_if_changed", c["required_slots"])

    def test_contracts_are_issue_type_not_visa_code_keyed(self):
        # Same issue type -> same contract regardless of visa code.
        a = _contract(["registration_or_residence_report"], {"current_status": "H-1"})
        b = _contract(["registration_or_residence_report"], {"current_status": "F-4"})
        self.assertEqual(a["contract_key"], b["contract_key"])


# ---------------------------------------------------------------------------
# Part B — the gate
# ---------------------------------------------------------------------------
class QualityGateTests(unittest.TestCase):
    def test_gate_catches_weak_h1_registration_answer(self):
        c = _contract(["reporting_duty", "registration_or_residence_report"], {"current_status": "H-1"})
        r = ashape.evaluate_answer_shape(WEAK_KO, _meta(["registration_or_residence_report"], {"current_status": "H-1"}), c)
        self.assertFalse(r["passed"])
        self.assertEqual(r["repair_strategy"], "deterministic_synthesis")
        self.assertIn("claims_not_based_on_manual_despite_context", r["warnings"])

    def test_gate_passes_useful_registration_answer(self):
        good = (
            "H-1 외국인등록은 입국일을 기준으로 정해진 기한 안에 해야 합니다. 본인의 입국일과 "
            "부여받은 체류기간을 먼저 확인해야 합니다. 신고는 하이코리아 또는 관할 출입국·외국인청에서 접수합니다.\n\n"
            "확인할 사실:\n* 입국일\n* 체류기간\n\n"
            "현재 연결된 직접 근거는 제한적이므로, 최종 기한과 제출 방식은 1345/HiKorea/관할 관서에서 확인하세요.\n"
            "공식 확인 질문:\n* 외국인등록 기한이 며칠인가요?"
        )
        c = _contract(["reporting_duty", "registration_or_residence_report"], {"current_status": "H-1"})
        r = ashape.evaluate_answer_shape(good, _meta(["registration_or_residence_report"], {"current_status": "H-1"}), c)
        self.assertTrue(r["passed"], r)
        self.assertEqual(r["missing_slots"], [])

    def test_gate_flags_study_leak_in_registration(self):
        leaky = (
            "H-1 외국인등록은 입국일 기준 기한 내에 하이코리아 또는 관할 관서에서 신고합니다. "
            "확인할 사실: 입국일. 다만 계절학기 수강이나 D-2 변경은 별도입니다. 1345 확인하세요."
        )
        c = _contract(["registration_or_residence_report"], {"current_status": "H-1"})
        r = ashape.evaluate_answer_shape(leaky, _meta(["registration_or_residence_report"], {"current_status": "H-1"}), c)
        self.assertFalse(r["passed"])
        self.assertTrue(any(w.startswith("irrelevant_terms") for w in r["warnings"]))

    def test_gate_flags_source_limitation_first_line(self):
        bad = "본 답변은 공식 매뉴얼에 근거하지 않습니다.\n그래도 H-1 외국인등록은 입국일 기준입니다."
        c = _contract(["registration_or_residence_report"], {"current_status": "H-1"})
        r = ashape.evaluate_answer_shape(bad, _meta(["registration_or_residence_report"], {"current_status": "H-1"}), c)
        self.assertIn("source_limitation_first_line", r["warnings"])

    def test_gate_flags_work_contamination_in_registration_deadline_answer(self):
        bad = (
            "D-2 외국인등록은 입국일 기준입니다. 다만 자격외활동, 근로, 보수, 고용주, 계약형태를 확인하세요. "
            "하이코리아 또는 관할 출입국·외국인청에서 접수합니다."
        )
        facts = {"current_status": "D-2", "entry_date": "2026-02-27", "registration_deadline_date": "2026-05-28"}
        c = _contract(["registration_deadline", "reporting_duty"], facts)
        r = ashape.evaluate_answer_shape(bad, _meta(["registration_deadline", "reporting_duty"], facts), c)
        self.assertFalse(r["passed"])
        self.assertTrue(any(w.startswith("irrelevant_terms") for w in r["warnings"]), r)

    def test_gate_requires_calculated_registration_deadline_when_entry_date_known(self):
        bad = (
            "D-2 외국인등록은 입국일 기준 90일 이내에 해야 합니다. 신고는 하이코리아 또는 관할 관서에서 접수합니다. "
            "현재 연결된 직접 근거는 제한적이므로 확인하세요."
        )
        facts = {"current_status": "D-2", "entry_date": "2026-02-27", "registration_deadline_date": "2026-05-28"}
        c = _contract(["registration_deadline", "reporting_duty"], facts)
        r = ashape.evaluate_answer_shape(bad, _meta(["registration_deadline", "reporting_duty"], facts), c)
        self.assertFalse(r["passed"])
        self.assertIn("missing_calculated_registration_deadline", r["warnings"])

    def test_gate_flags_asking_for_entry_date_already_provided(self):
        bad = (
            "외국인등록 기한은 입국일 기준 90일 이내입니다. 입국일을 알려주시면 계산할 수 있습니다. "
            "하이코리아 또는 관할 관서에서 접수합니다."
        )
        facts = {"current_status": "D-2", "entry_date": "2026-02-27", "registration_deadline_date": "2026-05-28"}
        c = _contract(["registration_deadline", "reporting_duty"], facts)
        r = ashape.evaluate_answer_shape(bad, _meta(["registration_deadline", "reporting_duty"], facts), c)
        self.assertFalse(r["passed"])
        self.assertIn("asks_for_entry_date_already_provided", r["warnings"])

    def test_gate_flags_overconfidence_when_certainty_limited(self):
        over = (
            "F-2-99로 변경되었으므로 이전 E-7 근무처 신고 의무는 더 이상 적용되지 않습니다. "
            "부업은 허용됩니다. 1345 확인하세요."
        )
        c = _contract(
            ["post_status_change_residual_duty"],
            {"current_status": "F-2-99", "previous_status": "E-7"},
            certainty="limited",
        )
        r = ashape.evaluate_answer_shape(
            over,
            _meta(["post_status_change_residual_duty"], {"current_status": "F-2-99", "previous_status": "E-7"}),
            c,
        )
        self.assertFalse(r["passed"])
        self.assertTrue(any(w.startswith("overconfident_language") for w in r["warnings"]))

    def test_gate_allows_definite_wording_when_certainty_direct(self):
        c = _contract(["registration_or_residence_report"], {"current_status": "H-1"}, certainty="direct")
        # A direct-certainty answer is allowed to be definite.
        ans = (
            "H-1 외국인등록은 입국일 기준 90일 이내에 하이코리아 또는 관할 관서에서 신고해야 합니다. "
            "확인할 사실: 입국일. 자세한 내용은 1345 확인하세요. 기한은 언제인가요?"
        )
        r = ashape.evaluate_answer_shape(ans, _meta(["registration_or_residence_report"], {"current_status": "H-1"}, certainty="direct"), c)
        self.assertEqual([w for w in r["warnings"] if w.startswith("overconfident")], [])


# ---------------------------------------------------------------------------
# Part C/D/E/F — deterministic-synthesis repair through /api/ask
# ---------------------------------------------------------------------------
class _AskHarness(unittest.TestCase):
    def setUp(self):
        self._saved_mode = os.environ.get("LAW_GROUNDING_MODE")
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        for key in ("LAW_API_OC", "LAW_API_KEY"):
            os.environ.pop(key, None)

    def tearDown(self):
        if self._saved_mode is None:
            os.environ.pop("LAW_GROUNDING_MODE", None)
        else:
            os.environ["LAW_GROUNDING_MODE"] = self._saved_mode

    def _ask(self, question, *, lang="ko", visa_code=None, model_answer=WEAK_KO):
        import paradiso_backend as pb
        from fastapi.testclient import TestClient

        async def weak(prompt, model=None):
            return model_answer

        pb._reset_visas_cache_for_tests()
        pb._reset_grounding_cache_for_tests()
        pb._reset_openrouter_model_cooldowns_for_tests()
        with patch.object(pb, "OPENROUTER_API_KEY", "or-test-key"), \
                patch.object(pb, "GROQ_API_KEY", None), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", False), \
                patch.object(pb, "ENABLE_OLLAMA_FALLBACK", False), \
                patch.object(pb, "OPENROUTER_MODEL", CANDS[0]), \
                patch.object(pb, "OPENROUTER_MODEL_CANDIDATES", list(CANDS)), \
                patch.object(pb, "OPENROUTER_MODEL_COOLDOWN_SECONDS", 0), \
                patch.object(pb, "_call_openrouter", weak):
            client = TestClient(pb.app)
            payload = {"question": question, "lang": lang}
            if visa_code:
                payload["visa_data"] = {"code": visa_code}
            resp = client.post("/api/ask", json=payload)
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()


class DeterministicRepairIntegrationTests(_AskHarness):
    def test_fabricated_case_citation_is_repaired_out_of_live_answer(self):
        fabricated = (
            "대법원 2099두99999 판결에 따르면 체류 연장 불허 처분은 반드시 취소됩니다. "
            "따라서 바로 인용될 가능성이 높습니다."
        )
        b = self._ask(
            "체류 연장 불허 처분을 받았는데 행정심판으로 다툴 수 있나요?",
            visa_code="D-2",
            model_answer=fabricated,
        )
        self.assertNotIn("2099두99999", b["answer"])
        self.assertIn(b["case_decision_citation_verification_status"], {"verified", "no_citations", "failed"})
        self.assertTrue(
            b["case_decision_citation_repaired"] or b["case_decision_citation_rejected"],
            b,
        )

    def test_weak_h1_registration_answer_is_repaired(self):
        b = self._ask("H-1 외국인등록은 언제 해야 하나요?", visa_code="H-1")
        # Provider/model untouched; this is a quality repair, not an outage.
        self.assertEqual(b["provider"], "openrouter")
        self.assertFalse(b["deterministic_fallback_answer_used"])
        self.assertTrue(b["answer_shape_failed_by_model"])
        self.assertTrue(b["model_answer_repaired_by_deterministic_synthesis"])
        self.assertEqual(b["answer_shape_contract"], ashape.CONTRACT_REGISTRATION)
        answer = b["answer"]
        # Part D: no study drift, registration framing present, honest source note.
        for bad in ("계절학기", "학점", "대학 수업", "D-2", "D-4", "수강", "청강"):
            self.assertNotIn(bad, answer)
        self.assertNotIn("공식 매뉴얼에 근거하지 않", answer)
        self.assertTrue(any(t in answer for t in ("하이코리아", "HiKorea", "1345", "관할")))

    def test_repaired_registration_source_limitation_is_after_practical(self):
        b = self._ask("H-1 외국인등록은 언제 해야 하나요?", visa_code="H-1")
        answer = b["answer"]
        first_line = next((ln.strip() for ln in answer.splitlines() if ln.strip()), "")
        # The first line must be practical, not a source-limitation disclaimer.
        for marker in ("근거하지 않", "직접 근거", "매뉴얼에 근거", "cannot verify"):
            self.assertNotIn(marker, first_line)
        # The concise source-limitation wording should still appear later.
        self.assertIn("직접 근거는 제한", answer)
        idx_practical = answer.find("외국인등록")
        idx_limit = answer.find("직접 근거는 제한")
        self.assertGreater(idx_limit, idx_practical)

    def test_d2_registration_deadline_repair_calculates_date_without_work_contamination(self):
        b = self._ask("d-2 비자로 들어온 학생은 외국인 등록을 언제까지 해야해? 2026년 2월 27일에 입국했어.", visa_code="D-2")
        self.assertEqual(b["answer_shape_contract"], ashape.CONTRACT_REGISTRATION)
        facts = b["immigration_facts"]
        self.assertEqual(facts["current_status"], "D-2")
        self.assertEqual(facts["entry_date"], "2026-02-27")
        self.assertEqual(facts["registration_deadline_date"], "2026-05-28")
        self.assertIn("2026-05-28", b["answer"])
        for bad in ("자격외활동", "근로", "보수", "고용주", "계약형태"):
            self.assertNotIn(bad, b["answer"])

    def test_e7_registration_deadline_repair_is_not_workplace_answer(self):
        b = self._ask("E-7 ARC registration deadline if entered Korea on 2026.3.1?", lang="en", visa_code="E-7")
        self.assertEqual(b["answer_shape_contract"], ashape.CONTRACT_REGISTRATION)
        facts = b["immigration_facts"]
        self.assertEqual(facts["current_status"], "E-7")
        self.assertEqual(facts["entry_date"], "2026-03-01")
        self.assertEqual(facts["registration_deadline_date"], "2026-05-30")
        self.assertIn("2026-05-30", b["answer"])
        for bad in ("workplace", "employer", "contract type", "salary"):
            self.assertNotIn(bad, b["answer"].lower())

    def test_e7_to_f299_residual_duty_not_overconfident(self):
        b = self._ask("E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?")
        answer = b["answer"]
        self.assertEqual(b["answer_shape_contract"], ashape.CONTRACT_WORKPLACE_CHANGE)
        self.assertIn("F-2-99", answer)
        self.assertIn("E-7", answer)
        # No overconfident "no duty / no longer applies" conclusion.
        self.assertNotIn("더 이상 적용되지 않습니다", answer)
        self.assertNotIn("신고 의무는 없습니다", answer)

    def test_g1_5_study_fallback_is_korean_and_natural(self):
        b = self._ask("G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?", visa_code="G-1-5")
        answer = b["answer"]
        self.assertEqual(b["answer_shape_contract"], ashape.CONTRACT_STUDY)
        self.assertIn("G-1-5", answer)
        # D-2 / D-4 only as comparison; no internal snake_case field labels.
        for snake in ("current_status", "proposed_activities", "decisive_facts", "answer_certainty_level"):
            self.assertNotIn(snake, answer)
        # No English official-confirmation question stems in a Korean answer.
        for stem in ("Is the course credit-bearing", "What is your current"):
            self.assertNotIn(stem, answer)

    def test_h1_to_f299_change_preserves_target(self):
        b = self._ask("Can I change status to F-2-99?", lang="en", visa_code="H-1")
        answer = b["answer"]
        self.assertEqual(b["answer_shape_contract"], ashape.CONTRACT_STATUS_CHANGE)
        self.assertIn("H-1", answer)
        self.assertIn("F-2-99", answer)

    def test_c3_paid_work_invents_no_penalties(self):
        b = self._ask("C-3 단기방문으로 paid work를 할 수 있나요?", visa_code="C-3")
        answer = b["answer"]
        self.assertEqual(b["answer_shape_contract"], ashape.CONTRACT_WORK_RESTRICTION)
        self.assertIn("C-3", answer)
        # No invented monetary penalties / fabricated fine amounts.
        self.assertNotIn("벌금", answer)
        self.assertIsNone(re.search(r"\d+\s*만\s*원", answer))

    def test_metadata_includes_answer_quality_gate_fields(self):
        b = self._ask("H-1 외국인등록은 언제 해야 하나요?", visa_code="H-1")
        for field in (
            "answer_shape_contract", "answer_shape_version", "answer_quality_gate_passed",
            "answer_quality_gate_warnings", "missing_answer_slots", "final_model_quality_warning",
            "answer_shape_failed_by_model", "model_answer_repaired_by_deterministic_synthesis",
        ):
            self.assertIn(field, b, f"missing gate field {field}")
        self.assertIsInstance(b["answer_quality_gate_warnings"], list)
        self.assertIsInstance(b["missing_answer_slots"], list)

    def test_good_model_answer_is_not_repaired(self):
        # A genuinely useful live answer must pass and be shown unmodified.
        good = (
            "H-1 외국인등록은 입국일을 기준으로 정해진 기한 안에 해야 합니다. 본인의 입국일과 부여받은 "
            "체류기간을 먼저 확인하세요. 신고는 하이코리아 또는 관할 출입국·외국인청에서 접수합니다.\n\n"
            "확인할 사실: 입국일, 체류기간.\n현재 연결된 직접 근거는 제한적이므로 최종 기한은 1345 확인하세요.\n"
            "외국인등록 기한이 며칠인가요?"
        )
        b = self._ask("H-1 외국인등록은 언제 해야 하나요?", visa_code="H-1", model_answer=good)
        self.assertFalse(b["model_answer_repaired_by_deterministic_synthesis"])
        self.assertTrue(b["answer_quality_gate_passed"])
        self.assertEqual(b["answer"], good)


class RegistrationDeadlineClassifierTests(unittest.TestCase):
    def test_entry_date_extraction_supported_formats_and_plus_90(self):
        for text in (
            "2026년 2월 27일에 입국했어",
            "2026-02-27에 입국했어",
            "2026.2.27에 입국했어",
            "2026/02/27에 입국했어",
        ):
            self.assertEqual(lanalysis.extract_entry_date(text), "2026-02-27")
        self.assertEqual(lanalysis.add_calendar_days("2026-02-27", 90), "2026-05-28")
        self.assertEqual(lanalysis.add_calendar_days("2026-03-01", 90), "2026-05-30")

    def test_registration_deadline_routes_all_representative_statuses_without_work(self):
        fixtures = [
            ("D-2", "d-2 비자로 들어온 학생은 외국인 등록을 언제까지 해야해? 2026년 2월 27일에 입국했어.", "2026-02-27", "2026-05-28"),
            ("H-1", "H-1 외국인등록 기한 알려줘. 2026-02-27 입국.", "2026-02-27", "2026-05-28"),
            ("E-7", "E-7 ARC registration deadline if entered Korea on 2026.3.1?", "2026-03-01", "2026-05-30"),
            ("F-6", "F-6 외국인등록은 언제까지? 2026/02/27 입국", "2026-02-27", "2026-05-28"),
            ("G-1-5", "G-1-5 외국인등록 기한은? 2026년 2월 27일 입국", "2026-02-27", "2026-05-28"),
            ("F-4", "F-4 거소신고 등록 기한은 언제야? 2026-02-27 입국", "2026-02-27", "2026-05-28"),
            ("H-2", "H-2 외국인 등록 기한. 2026.2.27 입국했어", "2026-02-27", "2026-05-28"),
            ("C-3", "C-3 비자로 입국일 기준 90일 이내가 언제야? 2026/02/27 입국", "2026-02-27", "2026-05-28"),
        ]
        for status, question, entry_date, deadline in fixtures:
            with self.subTest(status=status):
                facts = lanalysis.extract_immigration_facts(question)
                issues = lanalysis.classify_legal_issue_types(question, facts)
                self.assertIn("registration_deadline", issues)
                self.assertIn("deadline_trigger", issues)
                self.assertIn("reporting_duty", issues)
                self.assertEqual(facts["current_status"], status)
                if status == "G-1-5":
                    self.assertEqual(facts["current_sub_status"], "G-1-5")
                self.assertEqual(facts["entry_date"], entry_date)
                self.assertEqual(facts["registration_deadline_date"], deadline)
                for work_activity in ("paid_work", "freelance_work", "side_job", "workplace_change", "workplace_addition"):
                    self.assertNotIn(work_activity, facts["proposed_activities"])

    def test_explicit_work_question_still_routes_to_work(self):
        question = "D-2 학생이 아르바이트 근로를 할 수 있어?"
        facts = lanalysis.extract_immigration_facts(question)
        issues = lanalysis.classify_legal_issue_types(question, facts)
        self.assertIn("paid_work", facts["proposed_activities"])
        self.assertIn("work_on_non_work_status", issues)
        self.assertNotIn("registration_deadline", issues)


# ---------------------------------------------------------------------------
# Part H — smoke harness static recognition
# ---------------------------------------------------------------------------
class SmokeStaticRecognitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SMOKE.read_text(encoding="utf-8")

    def test_smoke_reads_gate_metadata_fields(self):
        for field in (
            "answer_shape_contract", "answer_quality_gate_passed",
            "answer_quality_gate_warnings", "missing_answer_slots",
            "final_model_quality_warning", "model_answer_repaired_by_deterministic_synthesis",
            "generic_avoidance_warning", "source_limitation_first_line_warning",
            "irrelevant_term_warning",
        ):
            self.assertIn(field, self.src, f"smoke missing field {field}")

    def test_smoke_has_static_gate_helpers(self):
        for fn in (
            "_generic_avoidance_warning", "_source_limitation_first_line_warning",
            "_registration_missing_slot_warning",
        ):
            self.assertIn("def %s(" % fn, self.src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
