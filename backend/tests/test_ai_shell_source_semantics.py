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
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_HTML = REPO_ROOT / "ai.html"
CHECKER = REPO_ROOT / "scripts" / "check_ai_shell_semantics.js"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_pack_support import pack_blob  # noqa: E402

# Some English answer-shell labels migrated into the external en.json locale pack;
# others remain inline in ai.html/index.html, so assert against both surfaces.


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
        self.assertIn("개발자 진단 정보 보기", self.html)

    def test_public_source_status_chips_are_rendered_safely(self):
        for token in (
            "source-status-chips",
            "source-chip",
            'data-row-kind="public-source-status"',
            "source-name-list",
            "versionDate",
        ):
            self.assertIn(token, self.html)
        self.assertIn("manualSources.length && !publicLabels.length", self.html)
        self.assertIn("@media (max-width: 480px)", self.html)
        self.assertIn(".source-status-chips", self.html)
        self.assertIn("overflow-wrap: anywhere", self.html)

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
        cls.en_blob = pack_blob("en")

    def test_legal_analysis_source_panel_labels_exist(self):
        surfaces = self.html + self.index_html + self.en_blob
        for label in (
            "Legal analysis basis",
            "Direct official authority found",
            "Related legal context checked",
            "Analogical legal analysis",
            "No direct scenario-specific authority found",
            "Source lookup technical issue",
            "Structured legal analysis note",
            "Structured legal analysis used",
            "Related legal context analysis",
            "Show developer diagnostics",
        ):
            self.assertIn(label, surfaces, label)

    def test_raw_technical_codes_stay_in_details_not_default_labels(self):
        for code in ("SOURCE_UNAVAILABLE", "LAW_API_BAD_RESPONSE", "CITATION_VERIFICATION_NOT_WIRED"):
            self.assertIn(code, self.html + self.index_html)
        self.assertNotIn("SOURCE_UNAVAILABLE could not", self.html + self.index_html)
        self.assertNotIn("LAW_API_BAD_RESPONSE could", self.html + self.index_html)
        self.assertIn("developer diagnostics", (self.html + self.index_html).lower())
        self.assertIn("일반 사용자는 확인하지 않아도 됩니다", self.html + self.index_html)
        self.assertIn("실시간 법령 조회 응답을 파싱하지 못했습니다", self.html + self.index_html)
        details_pos = self.html.find("실시간 법령 조회 응답을 파싱하지 못했습니다")
        raw_after_details = self.html.find("raw developer codes", details_pos)
        self.assertGreaterEqual(details_pos, 0)
        self.assertGreater(raw_after_details, details_pos)
        self.assertIn("<details", self.html + self.index_html)
        self.assertNotIn("<details open", (self.html + self.index_html).lower())

    def test_structured_fallback_copy_does_not_use_raw_codes_as_default_label(self):
        combined = self.html + self.index_html
        self.assertIn("구조화된 법률 분석 메모", combined)
        self.assertIn("Structured legal analysis note", combined)
        self.assertIn("구조화된 법률 분석 사용", combined)
        self.assertIn("직접 법령 인용은 제한되지만, 답변은 체류자격·활동유형·쟁점 분석을 기준으로 구성되었습니다.", combined)
        self.assertIn("Structured legal analysis used", combined)
        default_copy_slice = " ".join(line for line in combined.splitlines() if "sourcePanelStructured" in line or "sourcePanelCopyForState" in line or "lawSourcePanelMessage" in line)
        self.assertNotIn("SOURCE_UNAVAILABLE could", default_copy_slice)
        self.assertNotIn("LAW_API_BAD_RESPONSE could", default_copy_slice)

    def test_no_oc_or_api_key_value_in_source_panel_copy(self):
        panel_slice = (self.html + self.index_html)
        self.assertNotIn("LAW_API_OC", panel_slice)
        self.assertNotIn("OC=paradiso", panel_slice)

    # -- Part G: developer diagnostics taxonomy ----------------------------
    def test_developer_diagnostics_use_per_family_statuses(self):
        # The diagnostics block reads per-family statuses, not just a dominant
        # LAW_API_BAD_RESPONSE warning.
        self.assertIn("source_family_statuses", self.html)
        self.assertIn("parser_status_by_family", self.html)
        for label in ("법령군별 상태:", "Per-family status:"):
            self.assertIn(label, self.html)

    def test_developer_diagnostics_only_label_parser_failure_when_parser_failed(self):
        # A neutral "no directly citable result (not a parser failure)" line must
        # exist for the no_results / unsupported case, distinct from the parse-
        # failure line.
        self.assertIn("실시간 법령 조회에서 직접 인용 가능한 결과를 찾지 못했습니다(파서 오류 아님).", self.html)
        self.assertIn("parserFailed", self.html)
        self.assertIn("PARSE_FAIL", self.html)
        # The parse-failure line still exists (shown only when parser truly failed)
        # and the raw codes block stays at the bottom.
        details_pos = self.html.find("실시간 법령 조회 응답을 파싱하지 못했습니다")
        raw_pos = self.html.find("raw developer codes", details_pos)
        self.assertGreaterEqual(details_pos, 0)
        self.assertGreater(raw_pos, details_pos)
