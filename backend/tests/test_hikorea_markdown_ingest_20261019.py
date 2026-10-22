"""Offline integrity tests for the October Markdown importer."""
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/ingest_hikorea_markdown_261019.py"
spec = importlib.util.spec_from_file_location("ingest_hikorea_md", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MarkdownImportTests(unittest.TestCase):
    def test_pinned_sources(self):
        self.assertEqual(len(module.SPEC), 2)
        for item in module.SPEC.values():
            self.assertRegex(item["sha256"], r"^[a-f0-9]{64}$")
            self.assertIn(item["role"], ("visa_issuance_manual", "stay_residence_manual"))

    def test_unexpected_zip_members_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.zip"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("../../path-traversal.md", "test")
            with self.assertRaises(ValueError):
                module.inspect_zip(p)

    def test_modified_manuals_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.zip"
            with zipfile.ZipFile(p, "w") as z:
                for source in module.SPEC.values():
                    z.writestr(source["member"], "wrong bytes")
            with self.assertRaises(ValueError):
                module.stage(p, Path(d))


if __name__ == "__main__":
    unittest.main()
