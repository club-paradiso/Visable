from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import check_source_updates as csu  # noqa: E402


class CatalogDryRunTests(unittest.TestCase):
    def _write_catalog(self, path: str, sources: list[dict]) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"sources": sources}, fh)

    def test_catalog_loading(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "catalog.json")
            self._write_catalog(p, [{"source_id": "x", "source_type": "notice", "url": "https://a", "domain": "a", "monitor_enabled": True, "scrape_allowed": True, "requires_login": False}])
            loaded = csu._load_catalog(p)
            self.assertIn("sources", loaded)

    def test_required_field_validation(self):
        errors = csu._validate_catalog_record({"source_id": "x"}, 0, "test")
        self.assertTrue(any("missing required field" in e for e in errors))

    def test_all_disabled_records_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            h = os.path.join(td, "h.json")
            i = os.path.join(td, "i.json")
            disabled = [{"source_id": "x", "source_type": "notice", "url": "https://a", "domain": "a", "monitor_enabled": False, "scrape_allowed": True, "requires_login": False}]
            self._write_catalog(h, disabled)
            self._write_catalog(i, disabled)
            rc = csu.main(["--catalog-dry-run", "--hikorea-catalog", h, "--immigration-catalog", i])
            self.assertEqual(rc, 0)

    def test_no_network_default_behavior(self):
        with tempfile.TemporaryDirectory() as td:
            reg = os.path.join(td, "registry.json")
            with open(reg, "w", encoding="utf-8") as fh:
                json.dump({"sources": [{"id": "n1", "type": "law_api", "title": "t", "status": "active", "url": "https://example.com"}]}, fh)
            rc = csu.main(["--registry", reg, "--json"])
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
