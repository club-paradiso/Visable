"""Deterministic coverage for the i18n sweep + F-6/G-1 route wizard extension.

Static checks against index.html, the provider-aware smoke harness source, and
the PR documentation. No backend import, so these stay fast and runnable without
the FastAPI stack.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE = REPO_ROOT / "scripts" / "smoke_ai_live_quality.py"
DOC = REPO_ROOT / "docs" / "data" / "I18N_SWEEP_ROUTE_WIZARD_F6_G1_2026_05.md"

MAIN_LANGS = ("ko", "en", "zh", "zhHant")


class I18nSweepRouteWizardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

    def _slice(self, start_marker: str, end_marker: str) -> str:
        start = self.html.index(start_marker)
        end = self.html.index(end_marker, start)
        return self.html[start:end]

    # --- Part A: AI modal i18n --------------------------------------------
    def test_ai_modal_action_labels_in_four_languages(self):
        # aiActionLabels arrays exist for the four main languages.
        self.assertIn("aiActionLabels: ['✨ 종합 상황 분석 요청'", self.html)
        self.assertIn("aiActionLabels: ['✨ Request full situation analysis'", self.html)
        self.assertIn("aiActionLabels: ['✨ 请求综合情况分析'", self.html)
        self.assertIn("aiActionLabels: ['✨ 綜合情況分析請求'", self.html)

    def test_ai_modal_description_routed_through_tx(self):
        modal = self._slice("function openAiModal", "function openDocModal")
        # The description is no longer a ko/en-only ternary; it goes through tx().
        self.assertIn("tx('aiDescSpecial')", modal)
        self.assertIn("tx('aiDescGeneral')", modal)
        self.assertNotIn("currentLanguage === 'en'", modal)

    def test_ai_modal_descriptions_present_in_four_languages(self):
        for token in (
            "aiDescGeneral: '현재 국적",
            "aiDescGeneral: 'Enter nationality",
            "aiDescGeneral: '请详细输入国籍",
            "aiDescGeneral: '請詳細輸入國籍",
        ):
            self.assertIn(token, self.html)

    def test_ai_no_provider_message_localized(self):
        submit = self._slice("async function submitAiAnalysis", "function renderGroundingSourcePanel"
                             ) if "function renderGroundingSourcePanel" in self.html.split(
                                 "async function submitAiAnalysis", 1)[1] else self.html
        self.assertIn("tx('aiNoProvider')", self.html)
        self.assertIn("response.status === 503", self.html)
        # Localized in all four main languages.
        self.assertIn("aiNoProvider: 'AI 분석 서비스가 현재 설정되어 있지 않습니다.", self.html)
        self.assertIn("aiNoProvider: 'The AI analysis service is not currently configured.", self.html)
        self.assertIn("aiNoProvider: 'AI 分析服务当前尚未配置。", self.html)
        self.assertIn("aiNoProvider: 'AI 分析服務目前尚未配置。", self.html)

    def test_ai_modal_error_and_empty_states_localized(self):
        submit = self.html.split("async function submitAiAnalysis", 1)[1].split("function ", 1)[0]
        self.assertIn("tx('aiEmptyInput')", submit)
        self.assertIn("tx('aiNoResult')", submit)
        self.assertIn("tx('aiError')", submit)

    # --- Part B: document-tab / procedure-stage label i18n ----------------
    def test_document_tab_labels_in_four_languages(self):
        self.assertIn("documentTabLabels: ['최초 신청 (입국 전)', '외국인등록', '체류기간 연장']", self.html)
        self.assertIn("documentTabLabels: ['Initial application (before entry)', 'Foreigner registration', 'Extension of stay']", self.html)
        self.assertIn("documentTabLabels: ['初次申请（入境前）', '外国人登记', '停留期间延期']", self.html)
        self.assertIn("documentTabLabels: ['初次申請（入境前）', '外國人登錄', '停留期間延期']", self.html)

    def test_document_tabs_use_localized_helper(self):
        tabs = self._slice("function renderDocumentTabs", "function activateDocsTab")
        self.assertIn("getDocumentTabLabel(cfg)", tabs)
        self.assertIn("tx('documentSectionTitle')", tabs)
        # No longer hardcodes the Korean section heading.
        self.assertNotIn('aria-label="구비서류"', tabs)

    def test_known_procedure_keys_map_to_localized_labels(self):
        idx = self._slice("const PROCEDURE_LABEL_INDEX", "}")
        for key in ("visaIssuance", "statusChange", "extension", "registration"):
            self.assertIn("%s:" % key, idx)
        # Localized procedureLabels arrays exist for the four main languages.
        self.assertIn("procedureLabels: ['사증발급'", self.html)
        self.assertIn("procedureLabels: ['Visa issuance'", self.html)
        self.assertIn("procedureLabels: ['签证签发'", self.html)
        self.assertIn("procedureLabels: ['簽證核發'", self.html)

    def test_unknown_procedure_key_has_localized_fallback(self):
        fn = self._slice("function getProcedureLabelByKey", "function getProcedureLabel(")
        # Falls back to txAt(...) / the provided fallback rather than crashing.
        self.assertIn("txAt('procedureLabels'", fn)
        self.assertIn("fallback || key", fn)

    def test_domestic_residence_report_distinct_from_registration(self):
        # The F-4 domestic residence report wording is distinct from the generic
        # foreigner-registration document-tab label.
        self.assertIn("F-4 domestic residence report", self.html)
        self.assertIn("distinct from a general foreigner registration", self.html)
        self.assertIn("'Foreigner registration'", self.html)

    # --- Part C/D/E: route wizard config ----------------------------------
    def test_route_wizard_config_includes_f4_f6_g1(self):
        cfg = self._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        self.assertIn("'F-4'", cfg)
        self.assertIn("'F-6'", cfg)
        self.assertIn("'G-1'", cfg)

    def test_route_wizard_not_shown_for_unconfigured_status(self):
        cfg = self._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        # Genuinely route-simple / unconfigured statuses must not appear as keys.
        for unconfigured in ("'A-1'", "'B-2'", "'E-9'", "'D-8'", "'H-1'"):
            self.assertNotIn(unconfigured + ":", cfg.replace(" ", ""))
        # Render returns nothing when there is no config for the record.
        render = self._slice("function renderF4RouteChooser", "function selectF4Route")
        self.assertIn("if (!cfg) return ''", render)

    def test_f6_route_title_and_labels_in_four_languages(self):
        self.assertIn("f6RouteTitle: 'F-6는 어떤 상황에 해당하시나요?'", self.html)
        self.assertIn("f6RouteTitle: 'Which F-6 situation applies to you?'", self.html)
        self.assertIn("f6RouteTitle: '您属于哪一种 F-6 情况？'", self.html)
        self.assertIn("f6RouteTitle: '您屬於哪一種 F-6 情況？'", self.html)
        for key in ("f6Route1Label", "f6Route2Label", "f6Route3Label", "f6Route4Label", "f6Route5Label"):
            self.assertEqual(self.html.count("%s:" % key), 4, "%s should exist in 4 main languages" % key)

    def test_g1_route_title_and_labels_in_four_languages(self):
        self.assertIn("g1RouteTitle: 'G-1은 어떤 사유에 해당하시나요?'", self.html)
        self.assertIn("g1RouteTitle: 'Which G-1 reason applies to you?'", self.html)
        self.assertIn("g1RouteTitle: '您属于哪一种 G-1 事由？'", self.html)
        self.assertIn("g1RouteTitle: '您屬於哪一種 G-1 事由？'", self.html)
        for key in ("g1Route1Label", "g1Route2Label", "g1Route3Label", "g1Route4Label", "g1Route5Label", "g1Route6Label"):
            self.assertEqual(self.html.count("%s:" % key), 4, "%s should exist in 4 main languages" % key)

    def test_f4_route_behavior_preserved(self):
        cfg = self._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        f4 = cfg.split("'F-4'", 1)[1].split("'F-6'", 1)[0]
        for key in ("f4Route1Label", "f4Route4Label", "f4Route5Label"):
            self.assertIn(key, f4)
        for proc in ("visaIssuance", "statusChange", "registration", "extension"):
            self.assertIn("procedureKey: '%s'" % proc, f4)

    def test_show_all_reset_label_in_four_languages(self):
        self.assertIn('data-action="show-all-f4-routes"', self.html)
        self.assertIn("routeShowAll: '전체 경로 보기'", self.html)
        self.assertIn("routeShowAll: 'Show all routes'", self.html)
        self.assertIn("routeShowAll: '查看全部路径'", self.html)
        self.assertIn("routeShowAll: '查看全部路徑'", self.html)

    def test_route_selection_does_not_imply_approval(self):
        # F-6/G-1 route copy must avoid implying approval/eligibility.
        self.assertIn("Child-rearing alone is not automatically approved", self.html)
        self.assertIn("not every breakdown case qualifies", self.html)
        self.assertIn("does not guarantee recognition", self.html)
        self.assertIn("is not guaranteed", self.html)

    def test_route_maps_to_existing_variants(self):
        cfg = self._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        for variant_id in (
            "f-6-2-child-rearing-status-change",
            "f-6-3-marriage-terminated-status-change",
            "g-1-3-litigation-status-change",
            "g-1-5-6-refugee-humanitarian-status-change",
        ):
            self.assertIn("variantId: '%s'" % variant_id, cfg)

    # --- Part G: integration with checklist / AI --------------------------
    def test_selected_scenario_checklist_behavior_intact(self):
        self.assertIn("SCENARIO_CHECKLIST_STORAGE_PREFIX = 'paradiso:scenario-checklist:'", self.html)
        self.assertIn("function renderScenarioChecklist", self.html)

    def test_selected_variant_ai_payload_still_present(self):
        self.assertIn("selected_procedure_key: currentAiSelectedProcedureKey", self.html)
        self.assertIn("selected_procedure_variant_id: currentAiSelectedProcedureVariantId", self.html)

    def test_checklist_reminder_state_not_sent_to_ai(self):
        body = self.html.split("body: JSON.stringify({", 1)[1].split("}),", 1)[0]
        self.assertNotIn("checklist", body)
        self.assertNotIn("reminder", body)
        self.assertNotIn("scenario-checklist", body)

    def test_source_panel_labels_present(self):
        self.assertIn("tx('aiSourcePanelTitle')", self.html)
        self.assertIn("tx('lawGroundingStatusLabel')", self.html)

    def test_partial_language_fallback_notice_present(self):
        self.assertIn("partialLanguageNotice", self.html)
        self.assertIn("language-partial-notice", self.html)

    # --- Part H: provider-aware smoke harness ------------------------------
    def test_smoke_harness_exists_and_compiles(self):
        self.assertTrue(SMOKE.exists())
        rc = subprocess.call([sys.executable, "-m", "py_compile", str(SMOKE)])
        self.assertEqual(rc, 0)

    def test_smoke_help_runs(self):
        rc = subprocess.call(
            [sys.executable, str(SMOKE), "--help"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.assertEqual(rc, 0)

    def test_smoke_supports_no_provider_skip_without_failing(self):
        src = SMOKE.read_text(encoding="utf-8")
        # No-provider path is handled and returns 0 by default (require-live off).
        self.assertIn("no_llm_provider_configured", src)
        self.assertIn("--require-live", src)
        self.assertIn("live answer skipped", src)
        # Sample questions include the route-relevant prompts.
        for token in ("계절학기", "국내거소신고", "이혼", "치료 목적"):
            self.assertIn(token, src)

    def test_smoke_never_prints_secrets(self):
        src = SMOKE.read_text(encoding="utf-8")
        # The harness must never read or print raw provider key values. It only
        # reads non-secret booleans (llm.configured / providers) and the model id.
        self.assertNotIn("OPENROUTER_API_KEY", src)
        self.assertNotIn("GROQ_API_KEY", src)
        self.assertIn("never prints api keys", src.lower())

    # --- Part K: documentation -------------------------------------------
    def test_documentation_includes_exact_user_run_command(self):
        self.assertTrue(DOC.exists())
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn("smoke_ai_live_quality.py", doc)
        self.assertIn("up.railway.app", doc)
        self.assertIn("BACKEND_URL", doc)


if __name__ == "__main__":
    unittest.main()
