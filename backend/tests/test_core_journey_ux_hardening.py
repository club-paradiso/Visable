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
        # ...but never local checklist / reminder state. Anchor on the actual
        # /api/ask fetch literal so other POSTs (e.g. the jobcode keyword helper)
        # and the /api/ask comments are not picked up.
        ask_region = self.html.split("${API_BASE}/api/ask`", 1)[1]
        body = ask_region.split("body: JSON.stringify({", 1)[1].split("}),", 1)[0]
        self.assertNotIn("checklist", body)
        self.assertNotIn("reminder", body)
        self.assertNotIn("scenario-checklist", body)

    # --- Mobile / accessibility hardening (Part E) -------------------------
    #
    # These assert the narrow-screen BEHAVIOUR, not three literal CSS strings.
    # The literal form broke on a real improvement: the next-action rule was
    # deliberately re-scoped to `.next-action-panel .next-action-grid` so it
    # would beat the wider max-width:640px two-column rule on source order,
    # which had been collapsing the "구비서류 확인" card to a ~34px column of
    # vertical text. The single-column behaviour was never lost, only the exact
    # selector text, and a test that pins selector text fails on a fix.
    def _phone_media_block(self) -> str:
        """Every @media (max-width: 480px) body, brace-matched and joined.

        There is more than one such block in index.html, and which one carries a
        given rule is an authoring detail, not a contract. Joining them asks the
        question that actually matters: at a phone width, does this rule apply?
        """
        marker = "@media (max-width: 480px) {"
        blocks, cursor = [], 0
        while True:
            found = self.html.find(marker, cursor)
            if found < 0:
                break
            start = found + len(marker)
            depth, end = 1, None
            for i in range(start, len(self.html)):
                if self.html[i] == "{":
                    depth += 1
                elif self.html[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            self.assertIsNotNone(end, "unterminated @media (max-width: 480px) block")
            blocks.append(self.html[start:end])
            cursor = end
        self.assertTrue(blocks, "no @media (max-width: 480px) block in index.html")
        return "\n".join(blocks)

    def test_next_action_grid_collapses_to_one_column_on_phones(self):
        """Three side-by-side action cards do not fit a phone width.

        Scoped to the panel on purpose. renderNextActionArea() emits the grid
        inside <section class="next-action-panel">, and only a selector carrying
        that ancestor outranks the max-width:640px two-column rule that would
        otherwise win on source order. An unscoped `.next-action-grid` rule
        elsewhere in the stylesheet does not protect this surface, so matching
        one would pass the test while the phone layout stayed broken.
        """
        import re

        rules = [
            (selector, body)
            for selector, body in re.findall(
                r"([^{}]*\.next-action-grid[^{}]*)\{([^}]*)\}",
                self._phone_media_block(), re.S)
            if ".next-action-panel" in selector
        ]
        self.assertTrue(
            rules,
            "the phone breakpoint has no `.next-action-panel .next-action-grid` "
            "rule; without that ancestor the 640px two-column rule wins and the "
            "document card collapses to a sliver of vertical text",
        )
        self.assertTrue(
            any(re.search(r"grid-template-columns:\s*1fr\s*;", body)
                for _selector, body in rules),
            "the panel-scoped rule must collapse to a single column; found: "
            + "; ".join(b.strip() for _s, b in rules),
        )

    def test_scenario_choice_is_full_width_with_a_real_touch_target(self):
        """44px is the documented minimum; the base rule may exceed it."""
        import re

        self.assertIn("width: 100%", self._phone_media_block())
        base = re.search(r"\.scenario-choice\s*\{([^}]*)\}", self.html, re.S)
        self.assertIsNotNone(base, "no base .scenario-choice rule")
        height = re.search(r"min-height:\s*(\d+)px", base.group(1))
        self.assertIsNotNone(height, ".scenario-choice needs an explicit min-height")
        self.assertGreaterEqual(
            int(height.group(1)), 44,
            "tap targets below 44px fail the touch-target guidance this "
            "hardening pass introduced",
        )

    def test_deadline_inputs_stack_on_phones(self):
        import re

        self.assertTrue(
            re.search(r"\.deadline-inputs\s*\{[^}]*grid-template-columns:\s*1fr",
                      self._phone_media_block(), re.S),
            "date inputs must stack rather than sit side by side on a phone",
        )

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
