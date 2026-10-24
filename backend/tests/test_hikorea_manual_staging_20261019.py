"""2026-10-19 HiKorea manual staging must not silently change approved sources."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class TestManualStaging(unittest.TestCase):
    def test_review_only_contract(self):
        registry = json.loads((ROOT / "data/source_registry.json").read_text(encoding="utf-8"))
        approval = json.loads((ROOT / "data/manual_approval_index.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "docs/source-manuals/source_manifest.json").read_text(encoding="utf-8"))
        expected = {
            "visa": ("visa_manual_2026_10_19_hwp_text", "visa_issuance_manual", "visa_manual_261019.txt", 250000),
            "stay": ("stay_manual_2026_10_19_hwp_text", "stay_residence_manual", "stay_manual_261019.txt", 500000),
        }
        by_id = {r["id"]: r for r in registry["sources"]}
        for kind, (source_id, role, filename, min_chars) in expected.items():
            with self.subTest(kind=kind):
                entry = by_id[source_id]
                self.assertEqual(entry["status"], "needs_manual_review")
                self.assertEqual(approval["documents"][source_id]["approval_state"], "needs_review")
                self.assertFalse(approval["documents"][source_id]["reviewer"])
                self.assertEqual(next(x["registry_id_when_promoted"] for x in manifest["pending_review_editions"] if x["role"] == role), source_id)
                text_path = ROOT / entry["local_path"]
                self.assertEqual(text_path.name, filename)
                self.assertGreater(len(text_path.read_text(encoding="utf-8")), min_chars)
                # The staged connector text itself never becomes the current edition. The
                # 2026-10-19 edition is current only through the owner-approved PDF (decision
                # recorded 2026-10-23): its approval record names a reviewer and a date.
                current = manifest["current"][role]
                self.assertNotEqual(current["file"], entry["local_path"])
                if current["source_date"] == "2026-10-19":
                    pdf_id = source_id.replace("_hwp_text", "_pdf")
                    self.assertEqual(approval["documents"][pdf_id]["approval_state"], "approved")
                    self.assertTrue(approval["documents"][pdf_id]["reviewer"])
                    self.assertTrue(approval["documents"][pdf_id]["reviewed_at"])
                    self.assertTrue(current["approved_by"] and current["approved_at"])

if __name__ == "__main__":
    unittest.main()
