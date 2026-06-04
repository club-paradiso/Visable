"""Deterministic tests for the AI answer-shell source semantics (ai.html).

PR #256 added the answer-quality contract to the backend and index.html. This
suite guards the *ai.html* answer shell: source chips, the answer-basis row, the
friendly law-unavailable display, warning de-duplication, and the four-language
footer disclaimer.

Most behavioral coverage runs through ``scripts/check_ai_shell_semantics.js``
(it extracts and exercises the real ``generateBadges`` logic for the H-1 golden
case). This file invokes that checker as a subprocess and adds a few direct
static assertions so failures are easy to read.

Run from repo root:

    python3 -m pytest backend/tests/test_ai_shell_source_semantics.py -q
"""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_HTML = REPO_ROOT / "ai.html"
CHECKER = REPO_ROOT / "scripts" / "check_ai_shell_semantics.js"


class AiShellSemanticsCheckerTests(unittest.TestCase):
    """Run the node checker that exercises the real ai.html chip logic."""

    def test_node_checker_passes(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not available")
        result = subprocess.run(
            [node, str(CHECKER)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"check_ai_shell_semantics.js failed:\n{result.stdout}\n{result.stderr}",
        )
        self.assertIn("OK", result.stdout)


class AiShellStaticTests(unittest.TestCase):
    """Direct static assertions on ai.html (readable failures)."""

    @classmethod
    def setUpClass(cls):
        cls.html = AI_HTML.read_text(encoding="utf-8")

    # -- Source chip semantics (Part A / F) ---------------------------------
    def test_generate_badges_uses_related_metadata(self):
        self.assertIn("related_statuses_not_sources", self.html)
        # Chips carry a machine-readable kind so direct vs related differ. The
        # checked/manual kind is set via a ternary; the related kind is literal.
        self.assertIn('data-chip-kind="related"', self.html)
        self.assertIn("'manual' : 'checked'", self.html)

    def test_related_and_direct_chips_use_distinct_classes(self):
        self.assertIn("bdg-related", self.html)
        self.assertIn("bdg-checked", self.html)

    def test_checked_and_related_labels_four_languages(self):
        for label in ("Checked status", "확인한 체류자격", "已确认的居留资格", "已確認的居留資格"):
            self.assertIn(label, self.html)
        for label in (
            "Related status to verify", "함께 확인할 관련 체류자격",
            "需一并确认的相关居留资格", "需一併確認的相關居留資格",
        ):
            self.assertIn(label, self.html)

    # -- Answer-basis row (Part B) ------------------------------------------
    def test_answer_basis_row_exists_for_limited_modes(self):
        self.assertIn("buildAnswerBasisRow", self.html)
        self.assertIn("answer-basis-row", self.html)
        for label in (
            "Source-limited guidance", "Source-confirmed manual guidance",
            "General advisory guidance",
        ):
            self.assertIn(label, self.html)
        for label in ("제한적 근거 안내", "공식 매뉴얼 근거 확인", "일반 참고 안내"):
            self.assertIn(label, self.html)

    # -- Law-source unavailable display (Part C) ----------------------------
    def test_law_unavailable_uses_friendly_text(self):
        self.assertIn(
            "Legal source lookup returned an unsupported response format. Paradiso is using limited guidance until this is fixed.",
            self.html,
        )
        self.assertIn("법령 출처 조회가 지원되지 않는 응답 형식을 반환했습니다. 수정 전까지 Paradiso는 제한적 안내를 사용합니다.", self.html)

    def test_raw_source_unavailable_not_default_user_text(self):
        # The raw code may exist only in the warning-code map / details block,
        # never welded into a friendly sentence.
        self.assertNotIn("SOURCE_UNAVAILABLE could not", self.html)
        # The technical-details <details> block is still present for raw codes.
        self.assertIn("기술 세부정보 보기", self.html)

    # -- Warning de-duplication (Part D) ------------------------------------
    def test_warning_dedup_guards_present(self):
        self.assertIn("const hasPanel = Boolean(sourcePanelHtml)", self.html)
        self.assertIn("answerBasisCommunicatesLimit", self.html)
        # The trailing msg-disc is suppressed when the panel renders.
        self.assertIn("const trailingDisc = hasPanel ? ''", self.html)

    # -- Footer i18n (Part E) -----------------------------------------------
    def test_footer_has_id_and_four_language_disclaimer(self):
        self.assertIn('id="referenceDisclaimer"', self.html)
        self.assertIn("SHELL_FOOTER_DISCLAIMER", self.html)
        self.assertIn("applyShellLanguage", self.html)

    def test_english_footer_is_not_korean(self):
        self.assertIn(
            "Paradiso provides public law/manual-based reference information",
            self.html,
        )
        # And the Simplified / Traditional variants exist too.
        self.assertIn("Paradiso 提供基于公开法令与手册的参考信息", self.html)
        self.assertIn("Paradiso 提供基於公開法令與手冊的參考資訊", self.html)


class DocumentationTests(unittest.TestCase):
    def test_quality_gate_doc_exists(self):
        doc = REPO_ROOT / "docs" / "data" / "AI_ANSWER_SHELL_SOURCE_SEMANTICS_2026_05.md"
        self.assertTrue(doc.is_file(), f"Missing: {doc}")
        text = doc.read_text(encoding="utf-8")
        for token in (
            "Related status to verify", "Answer basis", "1345", "HiKorea",
            "answer_quality_mode", "related_statuses_not_sources",
        ):
            self.assertIn(token, text, f"doc missing token: {token}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

class LegalAnalysisSourcePanelStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = AI_HTML.read_text(encoding="utf-8")
        cls.index_html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

    def test_legal_analysis_source_panel_labels_exist(self):
        for label in (
            "Legal analysis basis",
            "Direct official authority found",
            "Related legal context checked",
            "Analogical legal analysis",
            "No direct scenario-specific authority found",
            "Source lookup technical issue",
        ):
            self.assertIn(label, self.html + self.index_html)

    def test_raw_technical_codes_stay_in_details_not_default_labels(self):
        for code in ("SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE", "CITATION_VERIFICATION_NOT_WIRED"):
            self.assertIn(code, self.html + self.index_html)
        self.assertNotIn("SOURCE_UNAVAILABLE could not", self.html + self.index_html)
        self.assertNotIn("LAW_API_BAD_RESPONSE could", self.html + self.index_html)
        self.assertIn("technical details", (self.html + self.index_html).lower())

    def test_no_oc_or_api_key_value_in_source_panel_copy(self):
        panel_slice = (self.html + self.index_html)
        self.assertNotIn("LAW_API_OC", panel_slice)
        self.assertNotIn("OC=paradiso", panel_slice)
