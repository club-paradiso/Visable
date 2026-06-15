"""Regression tests for the 2026-06 AI-answer / source-diagnostics / sub-code fixes.

These lock in the three live-browser regressions and the public-safe
source-diagnostics contract, all driven by mocks/fixtures (no live APIs):

1. H-1 interpreter/work query — paid work on a work-LIMITED status (H-1 Working
   Holiday) must not be framed as an outside-status violation merely because it
   is paid; the repaired answer distinguishes job types and cites agreement /
   duration / job-type facts.
2. H-1 registration query — classified as registration/reporting, practical
   framing leads, source limitation follows, no study drift.
3. G-1-5 study query — the public detected status preserves the exact sub-code
   G-1-5 (not collapsed to G-1); D-2/D-4 only as comparison.
4. Public-safe source diagnostics — raw internal codes never render by default
   in ai.html / index.html, and the public source-status projection is sanitized.
5. Deterministic repair — a weak overbroad answer fails the gate and is replaced
   by deterministic synthesis, with metadata reflecting the repair.

Run from repo root:

    python3 -m pytest backend/tests/test_ai_answer_regression_source_subcode_2026_06.py -q
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
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import answer_shape as ashape  # noqa: E402
from services import legal_analysis as la  # noqa: E402

CANDS = ["qwen/qwen3-next-80b-a3b-instruct:free", "google/gemma-4-31b-it:free"]

AI_HTML = REPO_ROOT / "ai.html"
INDEX_HTML = REPO_ROOT / "index.html"

# Raw internal diagnostic tokens that must never reach the default public UI.
RAW_DIAGNOSTIC_TOKENS = (
    "LAW_API_BAD_RESPONSE", "SOURCE_UNAVAILABLE", "bad_response", "unsupported",
    "not_attempted", "manual: attempted", "statute:", "enforcement_decree:",
    "enforcement_rule:", "administrative_rule:", "legal_interpretation:",
    "precedent:",
)

# The overbroad live-model failure for H-1 interpreter: "it is paid, therefore a
# high risk of violating activity scope / outside-status activity", with no
# job-type / duration / agreement nuance.
WEAK_H1_INTERPRETER = (
    "H-1 비자로 보수를 받는 통역 활동을 하는 것은 자격외활동 위반 위험이 높습니다. "
    "이는 체류자격 범위를 벗어난 활동에 해당할 위험이 큽니다. 반드시 1345에 문의하세요."
)
WEAK_KO = (
    "정확한 내용은 확인이 필요합니다. 본 답변은 공식 매뉴얼에 근거하지 않습니다. "
    "자세한 사항은 출입국에 문의하시기 바랍니다."
)


# ---------------------------------------------------------------------------
# Unit: generalized work-capability model + classifier
# ---------------------------------------------------------------------------
class WorkCapabilityModelTests(unittest.TestCase):
    def test_h1_is_work_limited(self):
        self.assertEqual(la.status_work_capability("H-1"), "work_limited")

    def test_work_authorized_and_prohibited(self):
        self.assertEqual(la.status_work_capability("E-7"), "work_authorized")
        self.assertEqual(la.status_work_capability("F-6"), "work_authorized")
        self.assertEqual(la.status_work_capability("D-2"), "work_prohibited")
        self.assertEqual(la.status_work_capability("C-3"), "work_prohibited")
        self.assertEqual(la.status_work_capability("D-10"), "work_prohibited")
        self.assertEqual(la.status_work_capability(None), "unknown")

    def test_h1_paid_work_is_not_outside_status_activity(self):
        q = "H-1 비자로 한국에 왔는데 혹시 통역사 일을 할 수 있을까?"
        facts = la.extract_immigration_facts(q)
        issues = la.classify_legal_issue_types(q, facts)
        # Work-limited: employment_restriction, NOT outside-status / non-work.
        self.assertIn("employment_restriction", issues)
        self.assertNotIn("outside_status_activity", issues)
        self.assertNotIn("work_on_non_work_status", issues)
        self.assertIn("activity_scope", issues)

    def test_study_status_paid_work_still_outside_status(self):
        # The carve-out is only for work-limited statuses; D-4 keeps the old shape.
        issues = la.classify_legal_issue_types("D-4 어학연수생인데 유급 인턴십을 해도 되나요?")
        self.assertIn("work_on_non_work_status", issues)


# ---------------------------------------------------------------------------
# Unit: answer-shape gate catches the overbroad "paid => outside status" answer
# ---------------------------------------------------------------------------
class OverbroadPaidWorkGateTests(unittest.TestCase):
    def _contract_and_meta(self, q, visa="H-1"):
        facts = la.extract_immigration_facts(q)
        issues = la.classify_legal_issue_types(q, facts)
        contract = ashape.build_answer_shape_contract(
            legal_issue_types=issues, immigration_facts=facts
        )
        meta = {
            "immigration_facts": facts,
            "legal_issue_types": issues,
            "visa_code_detected": visa,
            "answer_certainty_level": "limited",
        }
        return contract, meta

    def test_gate_fails_overbroad_h1_paid_work_answer(self):
        c, m = self._contract_and_meta("H-1 비자로 통역사 일을 할 수 있을까?")
        g = ashape.evaluate_answer_shape(WEAK_H1_INTERPRETER, m, c)
        self.assertFalse(g["passed"])
        self.assertEqual(g["repair_strategy"], "deterministic_synthesis")
        self.assertIn(
            "paid_work_treated_as_outside_status_for_work_permitting_status",
            g["warnings"],
        )

    def test_gate_quiet_when_nuance_present(self):
        c, m = self._contract_and_meta("H-1 비자로 통역사 일을 할 수 있을까?")
        nuanced = (
            "H-1은 체류 목적과 국가별 협정 한도 안에서 단기 취업이 허용될 수 있어, 보수를 받는다는 "
            "사실만으로 자격외활동 위반이 되는 것은 아닙니다. 직종과 근무 기간에 따라 다르므로 1345에 확인하세요."
        )
        g = ashape.evaluate_answer_shape(nuanced, m, c)
        self.assertNotIn(
            "paid_work_treated_as_outside_status_for_work_permitting_status",
            g["warnings"],
        )

    def test_gate_does_not_flag_work_prohibited_status(self):
        # For a study status, honest outside-status framing must NOT be flagged.
        c, m = self._contract_and_meta(
            "D-4 어학연수생인데 유급 인턴십을 해도 되나요?", visa="D-4"
        )
        answer = "D-4에서 보수를 받는 인턴십은 자격외활동 위반 위험이 높습니다."
        g = ashape.evaluate_answer_shape(answer, m, c)
        self.assertNotIn(
            "paid_work_treated_as_outside_status_for_work_permitting_status",
            g["warnings"],
        )


# ---------------------------------------------------------------------------
# Unit: deterministic synthesis quality for the three regressions
# ---------------------------------------------------------------------------
class DeterministicSynthesisQualityTests(unittest.TestCase):
    def _synth(self, q, lang="ko"):
        import paradiso_backend as pb

        facts = la.extract_immigration_facts(q)
        issues = la.classify_legal_issue_types(q, facts)
        legal_analysis = {"immigration_facts": facts, "legal_issue_types": issues}
        meta = {
            "immigration_facts": facts,
            "legal_issue_types": issues,
            "visa_code_detected": facts.get("current_status"),
        }
        answer = pb.build_legal_analysis_fallback_answer(
            prompt=q, lang=lang, base_meta=meta,
            legal_analysis=legal_analysis, intro_mode="quality_repair",
        )
        contract = ashape.build_answer_shape_contract(
            legal_issue_types=issues, immigration_facts=facts
        )
        gate = ashape.evaluate_answer_shape(answer, meta, contract)
        return answer, gate

    def test_h1_interpreter_synthesis_distinguishes_job_types(self):
        answer, gate = self._synth("H-1 비자로 한국에 왔는데 혹시 통역사 일을 할 수 있을까?")
        self.assertTrue(gate["passed"], gate["warnings"])
        # Does NOT say paid work is outside-status simply because paid.
        self.assertIn("단기 취업이 일부 허용될 수 있", answer)
        # Distinguishes the four job-type buckets.
        self.assertIn("통역·번역", answer)
        self.assertIn("전문 통역사", answer)
        self.assertIn("관광통역안내", answer)
        self.assertIn("교습", answer)
        # Mentions nationality agreement / duration / job-type facts.
        self.assertIn("협정", answer)
        self.assertTrue(any(t in answer for t in ("근무 기간", "근무시간")))
        # 1345 / HiKorea is a final-confirmation pointer, not the whole answer.
        self.assertTrue(any(t in answer for t in ("1345", "HiKorea", "관할")))
        self.assertGreater(len(answer), 300)
        for token in RAW_DIAGNOSTIC_TOKENS:
            self.assertNotIn(token, answer)

    def test_h1_registration_synthesis_practical_first(self):
        answer, gate = self._synth("H-1 외국인등록은 언제 해야 하나요?")
        self.assertTrue(gate["passed"], gate["warnings"])
        first_line = next((ln.strip() for ln in answer.splitlines() if ln.strip()), "")
        for marker in ("근거하지 않", "직접 근거", "매뉴얼에 근거", "cannot verify"):
            self.assertNotIn(marker, first_line)
        # Registration framing: trigger + deadline basis with preserved uncertainty.
        self.assertTrue(any(t in answer for t in ("입국일", "부여·변경일", "기산일")))
        self.assertIn("90일", answer)
        self.assertTrue(any(t in answer for t in ("하이코리아", "관할 출입국")))
        # No study drift.
        for bad in ("계절학기", "학점", "대학 수업", "D-2", "D-4", "수강", "청강", "대학교"):
            self.assertNotIn(bad, answer)
        # Source limitation appears AFTER the practical analysis.
        idx_practical = answer.find("외국인등록")
        idx_limit = answer.find("직접 근거는 제한")
        self.assertGreater(idx_limit, idx_practical)

    def test_g1_5_study_synthesis_preserves_subcode(self):
        answer, gate = self._synth(
            "G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?"
        )
        self.assertTrue(gate["passed"], gate["warnings"])
        self.assertIn("G-1-5", answer)
        # No internal snake_case field labels leaked.
        for snake in ("current_status", "proposed_activities", "decisive_facts"):
            self.assertNotIn(snake, answer)


# ---------------------------------------------------------------------------
# Integration: /api/ask repair path + sub-code metadata (mocked LLM)
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

        async def weak(prompt, model=None, max_tokens=None):
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


class H1InterpreterRepairTests(_AskHarness):
    def test_overbroad_h1_interpreter_answer_is_repaired(self):
        b = self._ask(
            "H-1 비자로 한국에 왔는데 혹시 통역사 일을 할 수 있을까?",
            visa_code="H-1", model_answer=WEAK_H1_INTERPRETER,
        )
        self.assertEqual(b["provider"], "openrouter")
        self.assertFalse(b["deterministic_fallback_answer_used"])
        self.assertTrue(b["answer_shape_failed_by_model"])
        self.assertTrue(b["model_answer_repaired_by_deterministic_synthesis"])
        self.assertEqual(b["answer_shape_contract"], ashape.CONTRACT_WORK_RESTRICTION)
        answer = b["answer"]
        # Final answer is the repaired one (nuanced), not the weak overbroad one.
        self.assertNotEqual(answer, WEAK_H1_INTERPRETER)
        self.assertIn("단기 취업이 일부 허용될 수 있", answer)
        self.assertIn("관광통역안내", answer)
        self.assertIn("협정", answer)
        for token in RAW_DIAGNOSTIC_TOKENS:
            self.assertNotIn(token, answer)

    def test_repaired_answer_does_not_treat_paid_as_violation(self):
        b = self._ask(
            "H-1 비자로 한국에 왔는데 혹시 통역사 일을 할 수 있을까?",
            visa_code="H-1", model_answer=WEAK_H1_INTERPRETER,
        )
        self.assertTrue(b["answer_quality_gate_passed"])
        self.assertNotIn(
            "paid_work_treated_as_outside_status_for_work_permitting_status",
            b["answer_quality_gate_warnings"],
        )


class H1RegistrationRepairTests(_AskHarness):
    def test_weak_registration_answer_is_repaired(self):
        b = self._ask("H-1 외국인등록은 언제 해야 하나요?", visa_code="H-1")
        self.assertTrue(b["model_answer_repaired_by_deterministic_synthesis"])
        self.assertEqual(b["answer_shape_contract"], ashape.CONTRACT_REGISTRATION)
        answer = b["answer"]
        self.assertIn("90일", answer)
        for bad in ("계절학기", "학점", "D-2", "D-4", "수강", "청강", "대학교"):
            self.assertNotIn(bad, answer)
        for token in RAW_DIAGNOSTIC_TOKENS:
            self.assertNotIn(token, answer)


class G15SubCodeMetadataTests(_AskHarness):
    def test_public_metadata_preserves_subcode_from_free_text(self):
        # Payload carries only the PARENT code; the question text names G-1-5.
        # The public detected status must still surface the exact sub-code.
        b = self._ask(
            "G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?",
            visa_code="G-1",
        )
        self.assertEqual(b["visa_sub_code_detected"], "G-1-5")
        self.assertEqual(b["visa_code_detected"], "G-1")
        self.assertEqual(b["answer_shape_contract"], ashape.CONTRACT_STUDY)
        answer = b["answer"]
        self.assertIn("G-1-5", answer)
        for token in RAW_DIAGNOSTIC_TOKENS:
            self.assertNotIn(token, answer)

    def test_public_metadata_preserves_subcode_when_explicit(self):
        b = self._ask(
            "G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?",
            visa_code="G-1-5",
        )
        self.assertEqual(b["visa_sub_code_detected"], "G-1-5")


# ---------------------------------------------------------------------------
# Public-safe source diagnostics (backend projection + frontend static guards)
# ---------------------------------------------------------------------------
class PublicSourceStatusProjectionTests(unittest.TestCase):
    def test_malformed_law_response_yields_public_safe_labels_only(self):
        from services import source_grounding as sg

        # Simulate a malformed / failed official-source family set.
        normalized = [
            {"family": "statute", "status": "error", "publicStatus": "temporarily_unavailable",
             "internalCode": "MALFORMED_JSON", "title": "", "sourceName": "", "url": "",
             "versionDate": "", "snippets": []},
            {"family": "enforcement_decree", "status": "not_relevant", "publicStatus": "unavailable",
             "internalCode": "NOT_ATTEMPTED", "title": "", "sourceName": "", "url": "",
             "versionDate": "", "snippets": []},
        ]
        public = sg.project_public_source_status(normalized, lang="ko")
        blob = " ".join(public.get("labels", []))
        for token in RAW_DIAGNOSTIC_TOKENS + ("MALFORMED_JSON", "NOT_ATTEMPTED", "error"):
            self.assertNotIn(token, blob)
        # publicStatus values are sanitized to the public vocabulary only.
        for src in public.get("sources", []):
            self.assertIn(
                src.get("publicStatus"),
                {"available", "temporarily_unavailable", "unavailable", None},
            )


class FrontendPublicSafeDiagnosticsTests(unittest.TestCase):
    def _read(self, path):
        return path.read_text(encoding="utf-8")

    def test_ai_html_gates_dev_diagnostics_and_fixes_newline(self):
        src = self._read(AI_HTML)
        self.assertIn("devDiagnosticsEnabled", src)
        # The developer block must only render when dev mode is enabled.
        self.assertIn("devDiagnosticsEnabled && (lawWarnings.length", src)
        # The literal escaped-newline bug must be gone from the diag render.
        self.assertNotIn("escapeHtml(diagBody.join('\\\\n'))", src)
        self.assertIn("escapeHtml(diagBody.join('\\n'))", src)

    def test_index_html_gates_dev_diagnostics_and_fixes_newline(self):
        src = self._read(INDEX_HTML)
        self.assertIn("devDiagnosticsEnabled", src)
        self.assertIn("devDiagnosticsEnabled && (lawWarnings.length", src)
        self.assertNotIn("escapeHtml(diagLines.join('\\\\n'))", src)
        self.assertIn("escapeHtml(diagLines.join('\\n'))", src)

    def test_context_chip_prefers_subcode(self):
        src = self._read(AI_HTML)
        self.assertIn("visa_sub_code_detected || result.visa_code_detected", src)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
