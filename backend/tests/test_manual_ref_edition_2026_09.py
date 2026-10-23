"""visa_data.json manualRefs relabelled to the 2026.9 / 2026.10 manuals stay anchored.

Two relabel stages moved refs off the 2026.6 export: 2026-10-19 (2026.9,
audits/manual-ref-edition-2026-09) and 2026-10-23 (2026.10,
audits/manual-ref-edition-2026-10). Each stage checked a ref's section wording
on the cited old page and on the content-matched page of the new edition. These
tests keep that true: a ref may only cite 2026.9 or 2026.10 if its wording is on
its cited page of its own manual, the relabel never crossed the stay/visa
boundary, and refs the audit could not verify were left untouched.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import audit_manual_ref_editions_2026_10 as audit  # noqa: E402


def _refs(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return [(p, ref) for _code, p, ref in audit.iter_refs(data)]


class ManualRefEditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.refs = _refs(REPO_ROOT / "visa_data.json")
        cls.current = [(p, r) for p, r in cls.refs if r.get("manualVersion") == audit.NEW_VERSION]
        cls.previous = [(p, r) for p, r in cls.refs if r.get("manualVersion") == audit.PREVIOUS_VERSION]
        cls.report = json.loads(audit.REPORT_JSON.read_text(encoding="utf-8"))

    def test_relabel_is_present(self):
        self.assertGreaterEqual(len(self.current), 956)

    def test_every_relabelled_ref_is_anchored_on_its_cited_page(self):
        for path, ref in self.current + self.previous:
            with self.subTest(path="/".join(map(str, path))):
                self.assertTrue(audit.anchored_ref(ref), (ref.get("manualVersion"), ref.get("pageRange"), ref.get("section")))

    def test_relabelled_refs_keep_stay_and_visa_apart(self):
        for editions, version in ((self.current, audit.NEW), (self.previous, audit.PREVIOUS)):
            for path, ref in editions:
                where = "/".join(map(str, path))
                with self.subTest(path=where):
                    new = version[ref["manualType"]]
                    self.assertEqual(ref["sourceFile"], new["text"])
                    self.assertEqual(ref["sourceDate"], new["sourceDate"])
                    if "procedures" in path:
                        expected = "visa" if path[path.index("procedures") + 1] == "visaIssuance" else "stay"
                        self.assertEqual(ref["manualType"], expected)

    def test_relabel_kept_review_flags_and_left_unverified_refs_alone(self):
        # The 2026.10 stage changes edition, file and page only. Every verified ref keeps
        # the needsManualReview and section the audit recorded, none becomes "verified",
        # and every ref the audit could not verify is exactly as the audit saw it.
        by_path = {"/".join(map(str, p)): r for p, r in self.refs}
        for row in self.report["refs"]:
            with self.subTest(path=row["path"], status=row["status"]):
                ref = by_path[row["path"]]
                if row["status"] in audit.APPLY_STATUSES:
                    self.assertEqual(ref["manualVersion"], audit.NEW_VERSION)
                    self.assertEqual(ref["needsManualReview"], row["needsManualReview"])
                    self.assertEqual(ref["section"], row["section"])
                    self.assertEqual(ref["pageRange"], row["newPageRange"])
                    self.assertIsNot(ref.get("verified"), True)
                else:
                    self.assertEqual(ref["manualVersion"], row["manualVersion"])
                    self.assertEqual(ref.get("pageRange"), row["pageRange"])
                    self.assertEqual(ref.get("sourceFile"), row["sourceFile"])

    def test_deploy_copy_matches(self):
        self.assertEqual((REPO_ROOT / "visa_data.json").read_bytes(),
                         (REPO_ROOT / "backend" / "data" / "visas.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
