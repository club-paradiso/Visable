"""Deterministic unit tests for the answer-quality contract.

These exercise ``backend/services/answer_quality.py`` directly (no LLM, no
network), plus prompt-construction integration through ``paradiso_backend``.
They guard:

  * answer-quality mode classification (Part A / C),
  * question-type templates (Part D),
  * related-status semantics (Part F),
  * terminology / mixed-language guardrails (Part I),
  * prompt-directive readability instructions (Part B / H),
  * canonical helper translations (Part B).

Run from repo root:

    python3 -m pytest backend/tests/test_answer_quality_contract.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import answer_quality as aq  # noqa: E402


class LanguageInstructionTests(unittest.TestCase):
    def test_english_forbids_cjk_artifacts(self):
        line = aq.answer_language_instruction("en")
        self.assertIn("natural English", line)
        self.assertIn("sojourn资格", line)  # named as a forbidden artifact

    def test_chinese_modes_distinct(self):
        self.assertIn("简体", aq.answer_language_instruction("zh-CN"))
        self.assertIn("繁體", aq.answer_language_instruction("zh-TW"))

    def test_normalize_lang(self):
        self.assertEqual(aq.normalize_lang("zh"), "zh-CN")
        self.assertEqual(aq.normalize_lang("zh-Hant"), "zh-TW")
        self.assertEqual(aq.normalize_lang("EN"), "en")
        self.assertEqual(aq.normalize_lang("fr"), "")

    def test_glossary_only_in_english(self):
        self.assertTrue(aq.glossary_lines("en"))
        self.assertEqual(aq.glossary_lines("ko"), "")
        # Canonical helper translations are present.
        gloss = aq.glossary_lines("en")
        self.assertIn("sojourn status", gloss)
        self.assertIn("activities outside the scope of status", gloss)
        self.assertIn("domestic residence report", gloss)
        self.assertIn("working holiday / H-1", gloss)


class QuestionTypeTests(unittest.TestCase):
    def test_activity_on_status(self):
        self.assertEqual(
            aq.classify_question_type("Can I study on H-1?", None),
            aq.Q_ACTIVITY_ON_STATUS,
        )

    def test_documents_needed(self):
        self.assertEqual(
            aq.classify_question_type("What documents do I need for F-6?", None),
            aq.Q_DOCUMENTS_NEEDED,
        )

    def test_status_change_from_pattern(self):
        self.assertEqual(
            aq.classify_question_type("Can I change from B-2 to F-4?", None),
            aq.Q_STATUS_CHANGE,
        )

    def test_status_change_korean(self):
        self.assertEqual(
            aq.classify_question_type("D-10에서 E-7로 바꾸려면?", None),
            aq.Q_STATUS_CHANGE,
        )

    def test_deadline_report(self):
        self.assertEqual(
            aq.classify_question_type("국내거소신고 기한이 며칠인가요?", None),
            aq.Q_DEADLINE_REPORT,
        )


class RelatedStatusTests(unittest.TestCase):
    def test_h1_study_surfaces_d2_d4(self):
        self.assertEqual(
            aq.detect_related_statuses(
                "Can I take a summer semester course on H-1?", "H-1", None
            ),
            ["D-2", "D-4"],
        )

    def test_study_status_holder_has_no_related(self):
        # A D-2 holder asking about study needs no comparison statuses.
        self.assertEqual(
            aq.detect_related_statuses("D-2로 계절학기 수강 가능?", "D-2", None),
            [],
        )

    def test_non_study_question_has_no_related(self):
        self.assertEqual(
            aq.detect_related_statuses("H-1으로 아르바이트 가능?", "H-1", None),
            [],
        )


class ClassifyAnswerQualityTests(unittest.TestCase):
    def _base(self, **over):
        kw = dict(
            prompt="x",
            visa_code=None,
            task_type=None,
            manual_grounding_present=False,
            structured_requirements_present=False,
            procedure_variant_present=False,
            law_grounding_used=False,
            law_grounding_status="not_attempted",
            manual_to_law_fallback_used=False,
            law_intent=False,
        )
        kw.update(over)
        return aq.classify_answer_quality(**kw)

    def test_manual_present_is_confirmed(self):
        q = self._base(manual_grounding_present=True)
        self.assertEqual(q["answer_quality_mode"], aq.SOURCE_CONFIRMED)
        self.assertFalse(q["requires_official_confirmation"])
        self.assertFalse(q["grounded_answer_limited"])

    def test_law_used_is_assisted(self):
        q = self._base(law_grounding_used=True)
        self.assertEqual(q["answer_quality_mode"], aq.SOURCE_ASSISTED)

    def test_variant_is_assisted(self):
        q = self._base(procedure_variant_present=True)
        self.assertEqual(q["answer_quality_mode"], aq.SOURCE_ASSISTED)

    def test_related_status_is_limited(self):
        q = self._base(
            prompt="Can I take a summer course on H-1?", visa_code="H-1"
        )
        self.assertEqual(q["answer_quality_mode"], aq.SOURCE_LIMITED)
        self.assertEqual(q["related_statuses_not_sources"], ["D-2", "D-4"])

    def test_generic_for_offtopic(self):
        q = self._base(prompt="hello there")
        self.assertEqual(q["answer_quality_mode"], aq.GENERIC_ADVISORY)

    def test_style_version_present(self):
        self.assertEqual(self._base()["answer_style_version"], aq.ANSWER_STYLE_VERSION)


class DirectiveTests(unittest.TestCase):
    def _dir(self, **over):
        q = aq.classify_answer_quality(
            prompt=over.pop("prompt", "x"),
            visa_code=over.pop("visa_code", None),
            task_type=over.pop("task_type", None),
            manual_grounding_present=over.pop("manual", False),
            structured_requirements_present=False,
            procedure_variant_present=False,
            law_grounding_used=False,
            law_grounding_status="not_attempted",
            manual_to_law_fallback_used=False,
            law_intent=False,
        )
        return aq.build_answer_directives(q, lang=over.pop("lang", "en"))

    def test_directive_leads_with_direct_answer(self):
        text = self._dir()
        self.assertIn("Lead with the direct, practical answer", text)
        # No rigid six-section template forced.
        self.assertNotIn("six section", text.lower())

    def test_directive_controls_warning_duplication(self):
        self.assertIn("State each caution once", self._dir())

    def test_directive_related_status_not_a_source(self):
        text = self._dir(prompt="Can I study on H-1?", visa_code="H-1")
        self.assertIn("Related statuses to verify", text)
        self.assertIn("never label them as a manual source", text)

    def test_directive_includes_glossary_in_english(self):
        self.assertIn("Canonical helper translations", self._dir(lang="en"))
        self.assertNotIn("Canonical helper translations", self._dir(lang="ko"))


class MixedLanguageGuardTests(unittest.TestCase):
    def test_english_flags_cjk_fragment(self):
        findings = aq.scan_mixed_language_artifacts("the sojourn资格 here", "en")
        self.assertIn("资格", findings)

    def test_english_allows_korean_parenthetical(self):
        clean = aq.scan_mixed_language_artifacts(
            "sojourn status (체류자격) is fine", "en"
        )
        self.assertEqual(clean, [])

    def test_chinese_flags_loose_hangul(self):
        findings = aq.scan_mixed_language_artifacts("这是 체류 问题", "zh-CN")
        self.assertIn("hangul_outside_parentheses", findings)

    def test_chinese_allows_parenthetical_hangul(self):
        clean = aq.scan_mixed_language_artifacts(
            "居留资格(체류자격)很重要", "zh-CN"
        )
        self.assertEqual(clean, [])

    def test_korean_text_is_clean_for_korean_mode(self):
        self.assertEqual(
            aq.scan_mixed_language_artifacts("체류자격 변경 절차", "ko"), []
        )


class PromptIntegrationTests(unittest.TestCase):
    """The answer directives must reach the final prompt for ungrounded and
    grounded paths alike (no live LLM needed — we inspect the prompt string)."""

    def setUp(self):
        import paradiso_backend  # noqa: WPS433

        self.mod = paradiso_backend

    def test_ungrounded_prompt_drops_rigid_six_sections(self):
        built = self.mod._build_ungrounded_korea_scoped_prompt(
            "H-1으로 계절학기 수강 가능?", visa_code="H-1", lang="ko"
        )
        # The old rigid "다음 6개 섹션을 순서대로 포함" instruction is gone.
        self.assertNotIn("6개 섹션을 순서대로", built)
        self.assertIn("실용적인 답", built)

    def test_language_instruction_has_artifact_guard(self):
        line = self.mod._answer_language_instruction("en")
        self.assertIn("sojourn资格", line)


if __name__ == "__main__":
    unittest.main(verbosity=2)

class LegalAnalysisFirstFramingTests(unittest.TestCase):
    def test_limited_h1_directive_is_not_failure_first(self):
        quality = aq.classify_answer_quality(
            prompt="Can I take summer semester course in Korean universities even though I have a H-1 visa?",
            visa_code="H-1",
            task_type=None,
            manual_grounding_present=False,
            structured_requirements_present=False,
            procedure_variant_present=False,
            law_grounding_used=False,
            law_grounding_status="unavailable",
            manual_to_law_fallback_used=False,
            law_intent=True,
        )
        directive = aq.build_answer_directives(quality, lang="en")
        self.assertNotIn('use this lead: "Paradiso cannot verify', directive)
        self.assertIn("strongest legally supportable practical posture", directive)
        self.assertIn("Treat a credit-bearing or degree-related university summer course as a high-risk activity under H-1", directive)
        self.assertIn("Source-based analysis", directive)
        self.assertIn("official-confirmation questions", directive)
        self.assertNotIn("may be permissible", directive.split("Do NOT use unsupported certainty wording", 1)[0])
