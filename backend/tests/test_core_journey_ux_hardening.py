"""Deterministic frontend coverage for the core-journey UX hardening pass.

These tests read index.html statically (no backend import) so they stay fast and
runnable even without the FastAPI stack. They lock in the polish changes made in
the "polish core journeys and deployed UX" PR:

  * the "What you can do now" next-action panel is fully localized (no Korean-only
    chrome) across the four main languages;
  * the F-4 route chooser surfaces the selected route as a labelled banner and
    keeps a show-all/reset affordance, distinct domestic-residence wording, and
    no approval implication;
  * the AI source / law-grounding panel has a plain-language lead and a
    reassurance note for disabled/unavailable law grounding;
  * the AI modal shows a safe selected-context banner and never sends local
    checklist/reminder state;
  * narrow-screen hardening CSS exists for the new action surfaces.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_pack_support import load_packs, localized, pack_blobs  # noqa: E402

# Localized UI copy now lives in external per-locale JSON packs (data/i18n/*.json);
# the actively supported display locales are ko, en, zh-CN (zh-Hant aliases to
# zh-CN), so Simplified Chinese is validated against zh-CN.


class CoreJourneyUxHardeningFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        cls.packs = load_packs()
        cls.blobs = pack_blobs()

    def _slice(self, start_marker: str, end_marker: str) -> str:
        start = self.html.index(start_marker)
        end = self.html.index(end_marker, start)
        return self.html[start:end]

    # --- Next-action panel i18n (Part F / Part G) --------------------------
    def test_next_action_panel_routed_through_translation_helper(self):
        panel = self._slice("function renderNextActionArea", "function renderCardSummary")
        # Title, kicker, and descriptions must all go through tx(), not hardcoded.
        for key in (
            "nextActionTitle",
            "nextActionHikoreaKicker",
            "nextActionHikoreaTitle",
            "nextActionHikoreaDesc",
            "nextActionDocsKicker",
            "nextActionDocsTitle",
            "nextActionDocsDesc",
            "nextActionAiKicker",
            "nextActionAiDesc",
        ):
            self.assertIn("tx('%s')" % key, panel, "%s not wired through tx()" % key)
        # The previously hardcoded Korean chrome must no longer be inline literals.
        self.assertNotIn(">지금 할 수 있는 일<", panel)
        self.assertNotIn("HiKorea 예약 도우미</strong>", panel)
        self.assertNotIn("구비서류 확인</strong>", panel)

    def test_next_action_labels_present_in_supported_languages(self):
        self.assertEqual(localized(self.packs, "ko", "nextActionTitle"), "지금 할 수 있는 일")
        self.assertEqual(localized(self.packs, "en", "nextActionTitle"), "What you can do now")
        self.assertEqual(localized(self.packs, "zh-CN", "nextActionTitle"), "现在可以做的事")
        # HiKorea action title localized across supported locales (Part G visibility).
        self.assertEqual(localized(self.packs, "en", "nextActionHikoreaTitle"), "HiKorea reservation helper")
        self.assertEqual(localized(self.packs, "zh-CN", "nextActionHikoreaTitle"), "HiKorea 预约助手")

    # --- F-4 route chooser hardening (Part B) ------------------------------
    def test_f4_selected_route_banner_present(self):
        chooser = self._slice("function selectF4Route", "function resetF4Route")
        self.assertIn("f4-route-selected", chooser)
        self.assertIn("tx('f4RouteSelectedPrefix')", chooser)
        # The route label is echoed back (now via the generalized data-* keys) so
        # the choice is obvious in text.
        self.assertIn("labelKey ? tx(labelKey)", chooser)

    def test_f4_show_all_reset_action_exists(self):
        self.assertIn("data-action=\"show-all-f4-routes\"", self.html)
        self.assertEqual(localized(self.packs, "ko", "f4RouteShowAll"), "전체 경로 보기")
        self.assertEqual(localized(self.packs, "en", "f4RouteShowAll"), "Show all F-4 routes")

    def test_f4_route_titles_present_in_supported_languages(self):
        self.assertEqual(localized(self.packs, "ko", "f4RouteTitle"), "F-4는 어떤 경로로 진행하시나요?")
        self.assertEqual(localized(self.packs, "en", "f4RouteTitle"), "Which F-4 route applies to you?")
        self.assertEqual(localized(self.packs, "zh-CN", "f4RouteTitle"), "您属于哪一种 F-4 办理路径？")

    def test_f4_domestic_residence_report_wording_distinct(self):
        # Route 4 must read as a domestic residence report, distinct from a
        # generic foreigner registration.
        self.assertIn("F-4 domestic residence report", self.blobs["en"])
        self.assertIn("distinct from a general foreigner registration", self.blobs["en"])

    def test_f4_route_selection_does_not_imply_approval(self):
        # H-2 -> F-4 route must not imply automatic approval.
        self.assertIn("Selecting a route does not imply eligibility or approval", self.blobs["en"])
        self.assertIn("Confirm eligibility and required documents", self.blobs["en"])
        self.assertNotIn("automatic approval", self.blobs["en"])

    def test_f4_route_to_procedure_mapping_present(self):
        config = self._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        f4 = config.split("'F-4'", 1)[1].split("'F-6'", 1)[0]
        for proc_key in ("visaIssuance", "statusChange", "registration", "extension"):
            self.assertIn("procedureKey: '%s'" % proc_key, f4)

    # --- Source / law-grounding panel readability (Part D) -----------------
    def test_source_panel_has_plain_language_lead(self):
        panel = self._slice("function renderGroundingSourcePanel", "async function submitAiAnalysis")
        self.assertIn("gp-lead", panel)
        self.assertIn("tx('aiSourcePanelLead')", panel)
        # Plain-language lead present in the localized packs.
        self.assertEqual(
            localized(self.packs, "en", "aiSourcePanelLead"),
            "Below is a summary of what this answer is based on. It is not a final confirmation.",
        )

    def test_law_grounding_unavailable_has_reassurance_note(self):
        panel = self._slice("function renderGroundingSourcePanel", "async function submitAiAnalysis")
        self.assertIn("tx('lawGroundingReassure')", panel)
        self.assertIn("gp-subnote", panel)
        # Reassurance only attaches to unavailable/disabled states (not "used").
        self.assertIn("lawStatusKey === 'unavailable' || lawStatusKey === 'disabled'", panel)
        self.assertIn("lawGroundingReassure: 'If statutory search was not used, it does not mean the answer is wrong — only that grounding sources were limited.'", self.html)

    def test_source_panel_still_carries_scenario_and_source_labels(self):
        panel = self._slice("function renderGroundingSourcePanel", "async function submitAiAnalysis")
        self.assertIn("tx('aiManualGroundingLabel')", panel)
        self.assertIn("tx('aiScenarioGroundingLabel')", panel)
        self.assertIn("tx('aiSelectedScenarioLabel')", panel)

    def test_source_panel_only_uses_safe_variant_fields(self):
        panel = self._slice("function renderGroundingSourcePanel", "async function submitAiAnalysis")
        # The panel must never read raw requiredDocs / manualRefs / full visa_data
        # off a source object (the words may still appear in explanatory comments).
        self.assertNotIn("src.requiredDocs", panel)
        self.assertNotIn("src.manualRefs", panel)
        self.assertNotIn(".requiredDocs", panel)
        self.assertNotIn(".manualRefs", panel)
        # Only the safe metadata fields are read off each source object.
        for field in ("visa_code", "procedure_key", "page_range"):
            self.assertIn("src.%s" % field, panel)

    # --- AI modal selected-context clarity (Part H) ------------------------
    def test_ai_modal_has_selected_context_element(self):
        self.assertIn('id="aiModalContext"', self.html)
        # The element id is declared exactly once (no duplicate IDs).
        self.assertEqual(self.html.count('id="aiModalContext"'), 1)

    def test_ai_modal_populates_safe_selected_context(self):
        modal = self._slice("function openAiModal", "function openDocModal")
        self.assertIn("getElementById('aiModalContext')", modal)
        self.assertIn("tx('aiModalContextLabel')", modal)
        self.assertIn("tx('aiModalContextNote')", modal)
        # Context banner is hidden again when no scenario is selected.
        self.assertIn("contextEl.hidden = true", modal)
        # Labels present across the supported locales.
        self.assertEqual(localized(self.packs, "en", "aiModalContextLabel"), "Selected context")
        self.assertEqual(localized(self.packs, "zh-CN", "aiModalContextLabel"), "已选背景")

    def test_ai_payload_sends_only_safe_identifiers(self):
        # The request body must still send the selected scenario identifiers...
        self.assertIn("selected_procedure_key: currentAiSelectedProcedureKey", self.html)
        self.assertIn("selected_procedure_variant_id: currentAiSelectedProcedureVariantId", self.html)
        # ...but never local checklist / reminder state.
        body = self.html.split("body: JSON.stringify({", 1)[1].split("}),", 1)[0]
        self.assertNotIn("checklist", body)
        self.assertNotIn("reminder", body)
        self.assertNotIn("scenario-checklist", body)

    # --- Mobile / accessibility hardening (Part E) -------------------------
    def test_narrow_screen_action_surface_css_present(self):
        self.assertIn("@media (max-width: 480px) {", self.html)
        for rule in (
            ".next-action-grid { grid-template-columns: 1fr; }",
            ".scenario-choice { width: 100%; min-height: 44px; }",
            ".deadline-inputs { grid-template-columns: 1fr; }",
        ):
            self.assertIn(rule, self.html)

    def test_new_surface_focus_visible_styles_exist(self):
        # Route chips, scenario choices, and deadline buttons remain keyboard
        # focusable with a visible focus ring (not color-only state).
        self.assertIn(".f4-route-chip:focus-visible", self.html)
        self.assertIn(".scenario-choice:focus-visible", self.html)
        self.assertIn(".deadline-cal-btn:focus-visible", self.html)

    # --- HiKorea / official confirmation visibility (Part G) ---------------
    def test_hikorea_action_is_not_gated_by_blocking_checkbox(self):
        guide = self._slice("function openHikoreaGuide", "function renderHikoreaGuide"
                           ) if "function renderHikoreaGuide" in self.html else self._slice(
                               "function openHikoreaGuide", "function ")
        # Opening the guide leads straight to the modal — no acknowledgement gate.
        self.assertIn("openModal('hikoreaGuideOverlay')", guide)
        self.assertNotIn("hikoreaGate", self.html)
        self.assertNotIn("hikoreaAck", self.html)

    def test_external_calendar_links_use_safe_attributes(self):
        row = self._slice("function deadlineRowHtml", "function computeDeadlines")
        self.assertIn('target="_blank" rel="noopener noreferrer"', row)


if __name__ == "__main__":
    unittest.main()
