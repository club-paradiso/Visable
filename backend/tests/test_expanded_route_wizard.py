"""Deterministic coverage for the remaining E-7/D-4/F-1 P1 route wizard config."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_pack_support import SUPPORTED_LOCALES, load_packs, localized  # noqa: E402

# Localized route copy now lives in external per-locale JSON packs (data/i18n/*.json);
# supported display locales are ko, en, zh-CN (zh-Hant aliases to zh-CN).


class ExpandedRouteWizardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        cls.config = cls._slice("const ROUTE_WIZARD_CONFIG", "function getRouteWizardConfig")
        cls.packs = load_packs()
        visas = json.loads((REPO_ROOT / "visa_data.json").read_text(encoding="utf-8"))
        cls.visas = {visa["code"]: visa for visa in visas}

    @classmethod
    def _slice(cls, start_marker: str, end_marker: str) -> str:
        start = cls.html.index(start_marker)
        end = cls.html.index(end_marker, start)
        return cls.html[start:end]

    def _status_config(self, code: str, next_code: str | None = None) -> str:
        block = self.config.split("    '%s':" % code, 1)[1]
        if next_code:
            block = block.split("    '%s':" % next_code, 1)[0]
        return block

    def _route_entry(self, code: str, route_id: str, next_code: str | None = None) -> str:
        block = self._status_config(code, next_code)
        start = block.index("{ id: '%s'" % route_id)
        return block[start:block.index("}", start)]

    def test_config_includes_only_the_remaining_p1_statuses_after_existing_routes(self):
        for code in ("E-7", "D-4", "F-1"):
            self.assertIn("    '%s':" % code, self.config)

    def test_route_titles_and_labels_exist_in_supported_languages(self):
        for prefix, english_title, route_count in (
            ("e7", "Which E-7 procedure do you need?", 3),
            ("d4", "Which D-4 route applies to you?", 4),
            ("f1", "Which F-1 route applies to you?", 8),
        ):
            self.assertEqual(localized(self.packs, "en", "%sRouteTitle" % prefix), english_title)
            keys = ["%sRoute%s" % (prefix, suffix) for suffix in ("Title", "Intro", "ChooserAria")]
            for idx in range(1, route_count + 1):
                keys.append("%sRoute%dLabel" % (prefix, idx))
                keys.append("%sRoute%dDesc" % (prefix, idx))
            for key in keys:
                for locale in SUPPORTED_LOCALES:
                    self.assertIn(key, self.packs[locale], "%s missing from %s pack" % (key, locale))

    def test_routes_use_existing_procedure_keys(self):
        expected = {
            "E-7": {"registration", "workplaceChange", "extension"},
            "D-4": {"statusChange", "extension"},
            "F-1": {"statusChange", "statusGrant", "extension"},
        }
        boundaries = {"E-7": "D-4", "D-4": "F-1", "F-1": None}
        for code, procedure_keys in expected.items():
            procedures = self.visas[code]["procedures"]
            block = self._status_config(code, boundaries[code])
            for procedure_key in procedure_keys:
                self.assertIn(procedure_key, procedures)
                self.assertIn("procedureKey: '%s'" % procedure_key, block)

    def test_every_specific_variant_id_is_source_backed(self):
        boundaries = {"E-7": "D-4", "D-4": "F-1", "F-1": None}
        for code, next_code in boundaries.items():
            available = {
                variant["id"]
                for procedure in self.visas[code]["procedures"].values()
                for variant in procedure.get("variants", [])
            }
            block = self._status_config(code, next_code)
            configured = {
                chunk.split("'", 1)[0]
                for chunk in block.split("variantId: '")[1:]
            }
            self.assertTrue(configured, "%s should expose at least one exact source-backed route" % code)
            self.assertLessEqual(configured, available)

    def test_broad_routes_do_not_preselect_a_single_subtype(self):
        for code, route_id, next_code in (
            ("E-7", "e7-1", "D-4"),
            ("E-7", "e7-3", "D-4"),
            ("D-4", "d4-4", "F-1"),
            ("F-1", "f1-8", None),
        ):
            self.assertNotIn("variantId", self._route_entry(code, route_id, next_code))

    def test_broad_route_behavior_keeps_pr252_show_all_reset(self):
        handler = self._slice("function selectF4Route", "function resetF4Route")
        # The route wizard reuses the in-screen scenario picker model: specific
        # routes select their mapped variant, while broad routes (empty
        # variantId) reset the picker to its empty / unselected state.
        self.assertIn("applyScenarioSelection(selector, variantId || '')", handler)

    def test_route_chooser_does_not_expose_raw_metadata(self):
        chooser = self._slice("function renderF4RouteChooser", "function selectF4Route")
        for raw_key in ("manualRefs", "requiredDocs", "sourceManualStatus", "structuredRequirementsRef"):
            self.assertNotIn(raw_key, chooser)


if __name__ == "__main__":
    unittest.main()
