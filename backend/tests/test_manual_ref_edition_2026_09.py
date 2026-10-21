"""visa_data.json manualRefs relabelled to the 2026.9 manuals stay anchored.

The 2026-10-19 relabel (audits/manual-ref-edition-2026-09) moved 955 refs to
the 2026.9 editions after checking each one's section wording on the cited old
page and on the content-matched 2026.9 page. These tests keep that true: a ref
may only cite 2026.9 if its wording is on the cited 2026.9 page of its own
manual, and the relabel never crossed the stay/visa boundary.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import audit_manual_ref_editions_2026_09 as audit  # noqa: E402


def _refs(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return [(p, ref) for _code, p, ref in audit.iter_refs(data)]


class ManualRefEdition2026_09Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.refs = _refs(REPO_ROOT / "visa_data.json")
        cls.current = [(p, r) for p, r in cls.refs if r.get("manualVersion") == audit.NEW_VERSION]

    def test_relabel_is_present(self):
        self.assertGreaterEqual(len(self.current), 955)

    def test_every_2026_9_ref_is_anchored_on_its_cited_page(self):
        for path, ref in self.current:
            with self.subTest(path="/".join(map(str, path))):
                self.assertTrue(audit.anchored_2026_09(ref), (ref.get("pageRange"), ref.get("section")))

    def test_2026_9_refs_keep_stay_and_visa_apart(self):
        for path, ref in self.current:
            where = "/".join(map(str, path))
            with self.subTest(path=where):
                new = audit.NEW[ref["manualType"]]
                self.assertEqual(ref["sourceFile"], new["text"])
                self.assertEqual(ref["sourceDate"], new["sourceDate"])
                if "procedures" in path:
                    expected = "visa" if path[path.index("procedures") + 1] == "visaIssuance" else "stay"
                    self.assertEqual(ref["manualType"], expected)

    def test_relabel_kept_review_flags(self):
        # The relabel changes edition, file and page only. Every ref keeps the
        # needsManualReview it had in the pre-relabel audit record, and none
        # becomes "verified".
        report = json.loads(audit.REPORT_JSON.read_text(encoding="utf-8"))
        by_path = {"/".join(map(str, p)): r for p, r in self.refs}
        for row in report["refs"]:
            if row["status"] not in audit.APPLY_STATUSES:
                continue
            with self.subTest(path=row["path"]):
                ref = by_path[row["path"]]
                self.assertEqual(ref["needsManualReview"], row["needsManualReview"])
                self.assertEqual(ref["section"], row["section"])
                self.assertEqual(ref["pageRange"], row["newPageRange"])
                self.assertIsNot(ref.get("verified"), True)

    def test_deploy_copy_matches(self):
        self.assertEqual((REPO_ROOT / "visa_data.json").read_bytes(),
                         (REPO_ROOT / "backend" / "data" / "visas.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
