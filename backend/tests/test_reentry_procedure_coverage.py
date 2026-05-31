"""Protects the 2026-05 re-entry permit (재입국허가) procedure document coverage
added by scripts/populate_reentry_procedure_docs_2026_05.py.

The index.html document tabs render ``procedures.reentry.requiredDocs``; before
this change those groups were empty for most long-stay statuses, so users saw
the "structured document checklist … not verified yet" fallback. These tests
assert that the populated re-entry records are exposed through /api/visas with
their verbatim manual document list and that the conditions (면제 제도, 국적
제한) are preserved — not flattened into the required list.

Run:
    python3 -m pytest backend/tests/test_reentry_procedure_coverage.py -q
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Statuses whose re-entry doc list was populated verbatim from each status's own
# 재입국허가 block in stay_manual_2026_05.pdf (printed page re-verified).
POPULATED = ["D-1", "D-4", "D-6", "D-7", "D-8", "D-9",
             "E-2", "E-3", "E-4", "E-5", "E-6", "F-3", "H-1"]
# The four-item 복수재입국허가 list, in two spacing variants seen in the manual.
EXPECTED_CORE = {"여권", "여권 원본", "외국인등록증", "수수료"}


def _client():
    for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
        os.environ.pop(key, None)
    from fastapi.testclient import TestClient
    import paradiso_backend
    paradiso_backend._reset_visas_cache_for_tests()
    return TestClient(paradiso_backend.app)


class ReentryProcedureCoverageTests(unittest.TestCase):
    def setUp(self):
        self.body = _client().get("/api/visas").json()
        self.recs = {r.get("code"): r for r in self.body["data"]}

    def _reentry(self, code):
        return ((self.recs.get(code) or {}).get("procedures") or {}).get("reentry")

    def test_all_populated_statuses_expose_reentry_docs(self):
        for code in POPULATED:
            pr = self._reentry(code)
            self.assertIsNotNone(pr, f"{code} reentry missing from /api/visas")
            self.assertTrue(pr.get("available"), f"{code} reentry must be available")
            docs = pr["requiredDocs"]["requiredDocs"]
            self.assertTrue(docs, f"{code} reentry required docs empty (fallback)")
            # First item is the application form; the list carries 여권/등록증/수수료.
            joined = " ".join(docs)
            self.assertIn("신청서", joined)
            self.assertIn("외국인등록증", joined)
            self.assertIn("수수료", joined)
            # Page citation present.
            refs = pr.get("manualRefs") or []
            self.assertTrue(refs and refs[0].get("pageRange", "").startswith("p. "))

    def test_conditions_preserved_not_flattened(self):
        # The exemption rule lives in notes; nationality restriction in
        # conditionalDocs — never merged into the required list.
        d7 = self._reentry("D-7")
        self.assertTrue(any("재입국허가 면제" in n for n in d7.get("notes", [])))
        cond = d7["requiredDocs"]["conditionalDocs"]
        self.assertTrue(any("복수재입국" in c for c in cond))
        for d in d7["requiredDocs"]["requiredDocs"]:
            self.assertNotIn("사우디", d)  # not flattened into required docs

    def test_unsourced_reentry_left_empty(self):
        # D-2's re-entry block is the student-specific narrative with no clean
        # 복수재입국 document line; it must remain unpopulated (not fabricated).
        pr = self._reentry("D-2")
        if pr is not None:
            self.assertFalse(
                pr.get("requiredDocs", {}).get("requiredDocs"),
                "D-2 reentry must stay empty (no clean manual list)",
            )

    def test_needs_manual_review_retained(self):
        for code in POPULATED:
            pr = self._reentry(code)
            self.assertTrue(pr["manualRefs"][0].get("needsManualReview") is True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
