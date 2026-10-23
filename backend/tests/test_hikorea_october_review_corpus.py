"""Basic integrity checks for October review-only manual search data."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    ("visa_manual_2026_10_19_hwp_text", 400),
    ("stay_manual_2026_10_19_hwp_text", 600),
]

class OctoberManualReviewTests(unittest.TestCase):
    def test_source_chunks_are_unapproved(self):
        for sid, min_chunks in SOURCES:
            path = ROOT / "data" / "manual-corpus" / (sid + ".json")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["approval_state"], "needs_review")
            self.assertEqual(data["date_provenance"], "filename_only")
            self.assertGreaterEqual(len(data["sections"]), min_chunks)
            self.assertTrue(all(s["page"] == 0 and not s["direct_evidence"] for s in data["sections"]))

    def test_builder_excludes_review_only_from_direct_evidence(self):
        from scripts.build_manual_search_index import OCTOBER_REVIEW_ONLY
        self.assertEqual(set(OCTOBER_REVIEW_ONLY), {s for s, _ in SOURCES})

if __name__ == "__main__":
    unittest.main()
