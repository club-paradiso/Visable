"""Deterministic coverage for the i18n sweep + F-6/G-1 route wizard extension.

Static checks against index.html, the provider-aware smoke harness source, and
the PR documentation. No backend import, so these stay fast and runnable without
the FastAPI stack.
"""
from __future__ import annotations

import subprocess
import sys
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE = REPO_ROOT / "scripts" / "smoke_ai_live_quality.py"
DOC = REPO_ROOT / "docs" / "data" / "I18N_SWEEP_ROUTE_WIZARD_F6_G1_2026_05.md"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_pack_support import SUPPORTED_LOCALES, load_packs, localized, pack_blobs  # noqa: E402

# Localized UI copy now lives in external per-locale JSON packs (data/i18n/*.json);
# Traditional Chinese (zh-Hant) aliases to zh-CN, so the actively supported display
# locales are ko, en, zh-CN and Simplified Chinese is validated against zh-CN.


class I18nSweepRouteWizardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        cls.packs = load_packs()
        cls.blobs = pack_blobs()

    def _slice(self, start_marker: str, end_marker: str) -> str:
        start = self.html.index(start_marker)
        end = self.html.index(end_marker, start)
        return self.html[start:end]

    # --- Part A: AI modal i18n --------------------------------------------
    def test_ai_modal_action_labels_in_supported_languages(self):
        # aiActionLabels arrays exist for every supported locale.
        self.assertIn("✨ 종합 상황 분석 요청", localized(self.packs, "ko", "aiActionLabels"))
        self.assertIn("✨ Request full situation analysis", localized(self.packs, "en", "aiActionLabels"))
        self.assertIn("✨ 请求综合情况分析", localized(self.packs, "zh-CN", "aiActionLabels"))

    def test_ai_modal_description_routed_through_tx(self):
        modal = self._slice("function openAiModal", "function openDocModal")
        # The description is no longer a ko/en-only ternary; it goes through tx().
        self.assertIn("tx('aiDescSpecial')", modal)
        self.assertIn("tx('aiDescGeneral')", modal)
        self.assertNotIn("currentLanguage === 'en'", modal)

    def test_ai_modal_descriptions_present_in_supported_languages(self):
        self.assertIn("현재 국적", localized(self.packs, "ko", "aiDescGeneral"))
        self.assertIn("Enter nationality", localized(self.packs, "en", "aiDescGeneral"))
        self.assertIn("请详细输入国籍", localized(self.packs, "zh-CN", "aiDescGeneral"))

    def test_ai_no_provider_message_localized(self):
        submit = self._slice("async function submitAiAnalysis", "function renderGroundingSourcePanel"
                             ) if "function renderGroundingSourcePanel" in self.html.split(
                                 "async function submitAiAnalysis", 1)[1] else self.html
        self.assertIn("tx('aiNoProvider')", self.html)
        self.assertIn("response.status === 503", self.html)
        # Localized in all supported locales.
        self.assertIn("AI 분석 서비스가 현재 설정되어 있지 않습니다.", localized(self.packs, "ko", "aiNoProvider"))
        self.assertIn("The AI analysis service is not currently configured.", localized(self.packs, "en", "aiNoProvider"))
        self.assertIn("AI 分析服务当前尚未配置。", localized(self.packs, "zh-CN", "aiNoProvider"))

    def test_ai_modal_error_and_empty_states_localized(self):
        submit = self.html.split("async function submitAiAnalysis", 1)[1].split("function ", 1)[0]
        self.assertIn("tx('aiEmptyInput')", submit)
        self.assertIn("tx('aiNoResult')", submit)
        self.assertIn("tx('aiError')", submit)

    # --- Part B: document-tab / procedure-stage label i18n ----------------
    def test_document_tab_labels_in_supported_languages(self):
        for s in ("최초 신청 (입국 전)", "외국인등록", "체류기간 연장"):
            self.assertIn(s, localized(self.packs, "ko", "documentTabLabels"), s)
        for s in ("Initial application (before entry)", "Foreigner registration", "Extension of stay"):
            self.assertIn(s, localized(self.packs, "en", "documentTabLabels"), s)
        for s in ("初次申请（入境前）", "外国人登记", "停留期间延期"):
            self.assertIn(s, localized(self.packs, "zh-CN", "documentTabLabels"), s)

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
        # Localized procedureLabels arrays exist for every supported locale.
        self.assertIn("사증발급", localized(self.packs, "ko", "procedureLabels"))
        self.assertIn("Visa issuance", localized(self.packs, "en", "procedureLabels"))
        self.assertIn("签证签发", localized(self.packs, "zh-CN", "procedureLabels"))

    def test_unknown_procedure_key_has_localized_fallback(self):
        fn = self._slice("function getProcedureLabelByKey", "function getProcedureLabel(")
        # Falls back to txAt(...) / the provided fallback rather than crashing.
        self.assertIn("txAt('procedureLabels'", fn)
        self.assertIn("fallback || key", fn)

    def test_domestic_residence_report_distinct_from_registration(self):
        # The F-4 domestic residence report wording is distinct from the generic
        # foreigner-registration document-tab label.
        self.assertIn("F-4 domestic residence report", self.blobs["en"])
        self.assertIn("distinct from a general foreigner registration", self.blobs["en"])
        self.assertIn("Foreigner registration", self.blobs["en"])

    # --- Part C/D/E: route wizard config ----------------------------------
    def test_route_wizard_config_includes_existing_and_remaining_p1_statuses(self):
        cfg = self._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        self.assertIn("'F-4'", cfg)
        self.assertIn("'F-6'", cfg)
        self.assertIn("'G-1'", cfg)
        self.assertIn("'F-2'", cfg)
        self.assertIn("'D-10'", cfg)
        self.assertIn("'H-2'", cfg)
        self.assertIn("'E-7'", cfg)
        self.assertIn("'D-4'", cfg)
        self.assertIn("'F-1'", cfg)
        for code in ("F-4", "F-6", "G-1", "F-2", "D-10", "H-2", "E-7", "D-4", "F-1"):
            self.assertRegex(cfg, r"(?m)^    '%s':" % code)

    def test_route_wizard_not_shown_for_unconfigured_status(self):
        cfg = self._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        # Statuses without an explicit route configuration remain excluded.
        for unconfigured in ("'D-2'", "'H-1'", "'F-3'"):
            self.assertNotIn(unconfigured + ":", cfg.replace(" ", ""))
        # Render returns nothing when there is no config for the record.
        render = self._slice("function renderF4RouteChooser", "function selectF4Route")
        self.assertIn("if (!cfg) return ''", render)

    def test_f6_route_title_and_labels_in_supported_languages(self):
        self.assertEqual(localized(self.packs, "ko", "f6RouteTitle"), "F-6는 어떤 상황에 해당하시나요?")
        self.assertEqual(localized(self.packs, "en", "f6RouteTitle"), "Which F-6 situation applies to you?")
        self.assertEqual(localized(self.packs, "zh-CN", "f6RouteTitle"), "您属于哪一种 F-6 情况？")
        for key in ("f6Route1Label", "f6Route2Label", "f6Route3Label", "f6Route4Label", "f6Route5Label"):
            for loc in SUPPORTED_LOCALES:
                self.assertIn(key, self.packs[loc], "%s missing from %s pack" % (key, loc))

    def test_g1_route_title_and_labels_in_supported_languages(self):
        self.assertEqual(localized(self.packs, "ko", "g1RouteTitle"), "G-1은 어떤 사유에 해당하시나요?")
        self.assertEqual(localized(self.packs, "en", "g1RouteTitle"), "Which G-1 reason applies to you?")
        self.assertEqual(localized(self.packs, "zh-CN", "g1RouteTitle"), "您属于哪一种 G-1 事由？")
        for key in ("g1Route1Label", "g1Route2Label", "g1Route3Label", "g1Route4Label", "g1Route5Label", "g1Route6Label"):
            for loc in SUPPORTED_LOCALES:
                self.assertIn(key, self.packs[loc], "%s missing from %s pack" % (key, loc))

    def test_f4_route_behavior_preserved(self):
        cfg = self._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        f4 = cfg.split("'F-4'", 1)[1].split("'F-6'", 1)[0]
        for key in ("f4Route1Label", "f4Route4Label", "f4Route5Label"):
            self.assertIn(key, f4)
        for proc in ("visaIssuance", "statusChange", "registration", "extension"):
            self.assertIn("procedureKey: '%s'" % proc, f4)

    def test_show_all_reset_label_in_supported_languages(self):
        self.assertIn('data-action="show-all-f4-routes"', self.html)
        self.assertEqual(localized(self.packs, "ko", "routeShowAll"), "전체 경로 보기")
        self.assertEqual(localized(self.packs, "en", "routeShowAll"), "Show all routes")
        self.assertEqual(localized(self.packs, "zh-CN", "routeShowAll"), "查看全部路径")

    def test_route_selection_does_not_imply_approval(self):
        # F-6/G-1 route copy must avoid implying approval/eligibility.
        self.assertIn("Child-rearing alone is not automatically approved", self.blobs["en"])
        self.assertIn("not every breakdown case qualifies", self.blobs["en"])
        self.assertIn("does not guarantee recognition", self.blobs["en"])
        self.assertIn("is not guaranteed", self.blobs["en"])

    def test_route_maps_to_existing_variants(self):
        cfg = self._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        for variant_id in (
            "f-6-2-child-rearing-status-change",
            "f-6-3-marriage-terminated-status-change",
            "g-1-3-litigation-status-change",
            "g-1-5-6-refugee-humanitarian-status-change",
            "f-2-7-point-based-talent-status-change",
            "d-10-2-tech-startup-extension",
            "h-2-employment-start-workplace-change-report",
        ):
            self.assertIn("variantId: '%s'" % variant_id, cfg)

    def test_f2_d10_h2_route_titles_and_labels_in_supported_languages(self):
        for key, title, count in (
            ("f2RouteTitle", "Which F-2 route applies to you?", 7),
            ("d10RouteTitle", "Which D-10 route applies to you?", 7),
            ("h2RouteTitle", "Which H-2 procedure do you need?", 3),
        ):
            self.assertEqual(localized(self.packs, "en", key), title)
            for idx in range(1, count + 1):
                label_key = "%sRoute%dLabel" % (key[:-10], idx)
                for loc in SUPPORTED_LOCALES:
                    self.assertIn(label_key, self.packs[loc], "%s missing from %s pack" % (label_key, loc))

    def test_h2_workplace_report_uses_existing_procedure_key(self):
        cfg = self._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        h2 = cfg.split("'H-2'", 1)[1]
        self.assertIn("procedureKey: 'workplaceChange'", h2)
        self.assertIn("variantId: 'h-2-employment-start-workplace-change-report'", h2)

    def test_broad_routes_do_not_preselect_a_single_subtype(self):
        cfg = self._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        for route_id in ("'f6-4'", "'g1-4'", "'g1-5'"):
            start = cfg.index(route_id)
            entry = cfg[start:cfg.index("}", start)]
            self.assertNotIn("variantId", entry, "%s should not preselect a subtype" % route_id)

    def test_broad_route_resets_scenario_selector_to_show_all(self):
        # The logic moved out of selectF4Route — now a back-compat shim that
        # resolves the wizard from the clicked control — into the shared
        # applyRouteSelection, which the in-screen popup path (chooseRoute) also
        # uses. Pinning the old inline call text asserted the shim's body rather
        # than the behaviour, so it failed on a refactor that changed nothing a
        # user can see.
        handler = self._slice("function applyRouteSelection", "function openRoutePicker")
        # The picker is resolved from its unselected state...
        self.assertIn(".scenario-needs-pick", handler)
        # ...a specific route's own variant always wins...
        call = re.search(
            r"applyScenarioSelection\(\s*selector\s*,\s*variantId\s*\|\|\s*(\w+)\s*\)",
            handler,
        )
        self.assertIsNotNone(
            call,
            "applyRouteSelection must hand the mapped variantId to the scenario "
            "picker, falling back for a broad route",
        )
        fallback = call.group(1)
        # ...and the broad-route fallback resolves to EMPTY unless the procedure
        # has exactly one scenario, which is auto-revealed instead of showing an
        # empty picker. That is what keeps a previously chosen subtype from
        # leaking into a broad route (PR #252) — the part that matters.
        self.assertRegex(
            handler,
            r"const\s+%s\s*=\s*\(\s*!variantId\s*&&\s*\w+\.length\s*===\s*1\s*\)" % fallback,
            "the broad-route fallback must be conditional on there being exactly "
            "one scenario",
        )
        self.assertRegex(
            handler, r"%s\s*=[^;]*:\s*''\s*;" % fallback,
            "a broad route onto a multi-scenario procedure must reset the picker "
            "to its empty state, not inherit the previous subtype",
        )

    # --- Part G: integration with checklist / AI --------------------------
    def test_selected_scenario_checklist_behavior_intact(self):
        self.assertIn("SCENARIO_CHECKLIST_STORAGE_PREFIX = 'paradiso:scenario-checklist:'", self.html)
        self.assertIn("function renderScenarioChecklist", self.html)

    def test_selected_variant_ai_payload_still_present(self):
        self.assertIn("selected_procedure_key: currentAiSelectedProcedureKey", self.html)
        self.assertIn("selected_procedure_variant_id: currentAiSelectedProcedureVariantId", self.html)

    def test_checklist_reminder_state_not_sent_to_ai(self):
        # Anchor on the actual /api/ask fetch literal specifically — other POSTs
        # (e.g. the jobcode keyword helper) also use body: JSON.stringify({...})
        # and the /api/ask comments would otherwise pull in unrelated code that
        # mentions "checklist".
        ask_region = self.html.split("${API_BASE}/api/ask`", 1)[1]
        body = ask_region.split("body: JSON.stringify({", 1)[1].split("}),", 1)[0]
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
