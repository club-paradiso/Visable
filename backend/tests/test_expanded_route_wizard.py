"""Deterministic coverage for the expanded route wizard (F-2/D-10/H-2 + P1).

Static checks against index.html for the route-wizard statuses added on top of
F-4/F-6/G-1: F-2, D-10, H-2 (P0) and E-7, D-4, F-1 (P1). No backend import.
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MAIN_LANGS = 4  # ko / en / zh / zhHant


class ExpandedRouteWizardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

    def _config(self) -> str:
        start = self.html.index("const ROUTE_WIZARD_CONFIG")
        end = self.html.index("function getRouteWizardConfig", start)
        return self.html[start:end]

    def _status_block(self, code: str) -> str:
        cfg = self._config()
        start = cfg.index("'%s'" % code)
        # up to the next top-level status key or the end of the config
        rest = cfg[start + len(code) + 2:]
        nxt = len(rest)
        for other in ("'F-4'", "'F-6'", "'G-1'", "'F-2'", "'D-10'", "'H-2'", "'E-7'", "'D-4'", "'F-1'"):
            i = rest.find(other)
            if i != -1:
                nxt = min(nxt, i)
        return rest[:nxt]

    # --- config membership (Part L #6) ------------------------------------
    def test_config_includes_all_p0_and_p1_statuses(self):
        cfg = self._config()
        for code in ("'F-4'", "'F-6'", "'G-1'", "'F-2'", "'D-10'", "'H-2'", "'E-7'", "'D-4'", "'F-1'"):
            self.assertIn(code + ":", cfg.replace(" ", ""))

    # --- F-2 / D-10 / H-2 titles + labels in four languages (Part L #10) --
    def test_f2_title_and_labels_four_languages(self):
        self.assertIn("f2RouteTitle: 'F-2는 어떤 거주 사유에 해당하시나요?'", self.html)
        self.assertIn("f2RouteTitle: 'Which F-2 residence situation applies to you?'", self.html)
        self.assertIn("f2RouteTitle: '您属于哪一种 F-2 居住事由？'", self.html)
        self.assertIn("f2RouteTitle: '您屬於哪一種 F-2 居住事由？'", self.html)
        for i in range(1, 5):
            self.assertEqual(self.html.count("f2Route%dLabel:" % i), MAIN_LANGS)

    def test_d10_title_and_labels_four_languages(self):
        self.assertIn("d10RouteTitle: 'D-10은 어떤 구직·준비 상황인가요?'", self.html)
        self.assertIn("d10RouteTitle: 'Which D-10 job-seeking situation applies to you?'", self.html)
        self.assertIn("d10RouteTitle: '您属于哪一种 D-10 求职·准备情况？'", self.html)
        self.assertIn("d10RouteTitle: '您屬於哪一種 D-10 求職·準備情況？'", self.html)
        for i in range(1, 5):
            self.assertEqual(self.html.count("d10Route%dLabel:" % i), MAIN_LANGS)

    def test_h2_title_and_labels_four_languages(self):
        self.assertIn("h2RouteTitle: 'H-2는 어떤 절차를 보려 하시나요?'", self.html)
        self.assertIn("h2RouteTitle: 'Which H-2 procedure are you looking for?'", self.html)
        self.assertIn("h2RouteTitle: '您想查看哪一种 H-2 程序？'", self.html)
        self.assertIn("h2RouteTitle: '您想查看哪一種 H-2 程序？'", self.html)
        for i in range(1, 5):
            self.assertEqual(self.html.count("h2Route%dLabel:" % i), MAIN_LANGS)

    # --- P1 statuses implemented (Part L #11) -----------------------------
    def test_p1_statuses_titles_and_labels_four_languages(self):
        for prefix, n in (("e7", 3), ("d4", 4), ("f1", 4)):
            self.assertEqual(self.html.count("%sRouteTitle:" % prefix), MAIN_LANGS, prefix)
            self.assertEqual(self.html.count("%sRouteIntro:" % prefix), MAIN_LANGS, prefix)
            for i in range(1, n + 1):
                self.assertEqual(self.html.count("%sRoute%dLabel:" % (prefix, i)), MAIN_LANGS, "%s %d" % (prefix, i))

    # --- routes map to existing variants where claimed --------------------
    def test_new_routes_map_to_existing_variants(self):
        cfg = self._config()
        for variant_id in (
            "f-2-7-point-based-talent-status-change",
            "f-2-8-tourism-investment-status-change",
            "f-2-permanent-resident-family-status-change",
            "d-10-1-points-status-change",
            "d-10-2-tech-startup-status-change",
            "d-10-3-high-tech-intern-status-change",
            "d-10-1-points-extension",
            "h-2-existing-holder-registration",
            "h-2-employment-start-workplace-change-report",
            "e-7-registered-workplace-change",
            "d-4-1-7-language-training-status-change",
            "d-4-2-graduate-training-status-change",
            "d-4-3-school-student-status-change",
            "f-1-13-status-change",
            "f-1-6-marriage-cleanup-status-change",
            "f-1-16-refugee-family-status-change",
        ):
            self.assertIn("variantId: '%s'" % variant_id, cfg)

    # --- cautious copy: no approval/eligibility implication ----------------
    def test_h2_to_f4_does_not_imply_automatic_approval(self):
        # The H-2 -> F-4 route must explicitly state it is not automatic.
        self.assertIn("This is not automatically approved", self.html)
        self.assertIn("변경이 자동으로 인정되지는 않으며", self.html)

    def test_extension_routes_present_for_new_statuses(self):
        # Each new status exposes an extension route (procedureKey 'extension').
        for code in ("F-2", "D-10", "H-2", "E-7", "D-4", "F-1"):
            block = self._status_block(code)
            self.assertIn("procedureKey: 'extension'", block, "%s has no extension route" % code)

    # --- Part L #24: wizard never exposes raw doc/manual/visa_data --------
    def test_route_wizard_does_not_expose_raw_metadata(self):
        start = self.html.index("function renderF4RouteChooser")
        end = self.html.index("function resetF4Route", start)
        wizard = self.html[start:end]
        for forbidden in ("requiredDocs", "manualRefs", "visa_data", "JSON.stringify"):
            self.assertNotIn(forbidden, wizard)

    # --- Part L #17: route context carried as safe ids only ---------------
    def test_route_chip_carries_only_safe_identifiers(self):
        start = self.html.index("function renderF4RouteChooser")
        end = self.html.index("function selectF4Route", start)
        render = self.html[start:end]
        # Chips carry route id / procedure key / variant id / label+desc keys only.
        for safe in ("data-route-id", "data-procedure-key", "data-variant-id", "data-label-key", "data-desc-key"):
            self.assertIn(safe, render)
        self.assertNotIn("requiredDocs", render)
        self.assertNotIn("manualRefs", render)


if __name__ == "__main__":
    unittest.main()
