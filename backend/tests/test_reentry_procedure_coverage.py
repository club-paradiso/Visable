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
    """Re-pointed at the 2026.6 re-sourcing pass.

    This suite was written against scripts/populate_reentry_procedure_docs_2026_05.py
    and its 2026-05 manual. A later pass re-derived these records from the
    2026.6 체류민원 안내매뉴얼 with a per-status source map, which changed four
    surface details without weakening anything:

      * documents are carried as doc_master IDs where the registry defines one
        (doc_fee_generic), because /api/visas is a transport of internal keys —
        see test_document_labels.TransportKeepsRawIdsTests for why resolving
        there breaks the complex-status guide's audit-safe checklist;
      * page citations are ranges ("pp. 32-34") rather than single pages;
      * the 복수재입국 condition and the 국적 제한 moved from conditionalDocs into
        notes — the prose relocation CLAUDE.md explicitly sanctions, since a
        document array is not the place for a rule;
      * needsManualReview cleared on the source-mapped pass.

    The assertions below therefore test the properties that must hold for ANY
    sourcing pass — provenance, no fabrication, no flattening, and a caution the
    user actually sees — instead of the shape of one retired extraction.
    """

    def setUp(self):
        self.body = _client().get("/api/visas").json()
        self.recs = {r.get("code"): r for r in self.body["data"]}

    def _reentry(self, code):
        return ((self.recs.get(code) or {}).get("procedures") or {}).get("reentry")

    @staticmethod
    def _resolve(doc):
        from services import document_labels as dl
        return dl.resolve_document_label(doc)

    def test_all_populated_statuses_expose_reentry_docs(self):
        for code in POPULATED:
            with self.subTest(code=code):
                pr = self._reentry(code)
                self.assertIsNotNone(pr, f"{code} reentry missing from /api/visas")
                self.assertTrue(pr.get("available"), f"{code} reentry must be available")
                docs = pr["requiredDocs"]["requiredDocs"]
                self.assertTrue(docs, f"{code} reentry required docs empty (fallback)")
                # 신청서 · 여권(원본) · 외국인등록증 [· 수수료]. The fee line is absent
                # for statuses whose manual block does not print one, so the count
                # is 3 or 4 — but nothing outside that set may appear.
                self.assertIn(len(docs), (3, 4),
                              f"{code} reentry should have 3-4 docs, got {docs}")
                labels = [str(self._resolve(d)) for d in docs]
                joined = " ".join(labels)
                self.assertIn("신청서", joined)
                self.assertIn("외국인등록증", joined)
                self.assertTrue(any("여권" in x for x in labels),
                                f"{code} has no passport item: {labels}")
                # A fee line, when present, terminates the list and must be clean
                # (no section text leaked past 수수료 from the next page block).
                if any("수수료" in x for x in labels):
                    self.assertIn(labels[-1], ("수수료", "수수료 없음", "수수료면제"),
                                  f"{code} fee item not clean: {labels[-1]!r}")
                for raw, label in zip(docs, labels):
                    self.assertLessEqual(len(label), 22,
                                         f"{code} doc item too long (leak?): {label!r}")
                    for leak in ("목차", "신청서류", "제출서류", "외국인등록 "):
                        self.assertNotIn(leak, label,
                                         f"{code} doc item has section leak: {label!r}")
                    if raw != label:
                        self.assertTrue(
                            self._resolve(label) == label,
                            f"{code} label {label!r} must itself be final, not another id",
                        )

    def test_every_populated_status_cites_a_manual_page(self):
        """Documents without a citation are indistinguishable from invented ones."""
        for code in POPULATED:
            with self.subTest(code=code):
                refs = self._reentry(code).get("manualRefs") or []
                self.assertTrue(refs, f"{code} reentry has documents but no manual reference")
                page = str(refs[0].get("pageRange") or "")
                self.assertRegex(
                    page, r"^pp?\. \d",
                    f"{code} manual reference has no page citation: {page!r}",
                )

    def test_conditions_preserved_not_flattened(self):
        """The exemption rule and the nationality restriction survive as prose.

        Which field holds them is a rendering decision; that they are NOT merged
        into the required-document list is the safety property, because a
        conditional rule rendered as a required document tells the user to bring
        something that may not apply to them.
        """
        d7 = self._reentry("D-7")
        prose = " ".join((d7.get("notes") or [])
                         + list(d7["requiredDocs"].get("conditionalDocs") or []))
        self.assertIn("재입국허가 면제", prose,
                      "the exemption rule must be preserved somewhere the user reads")
        self.assertIn("복수재입국", prose,
                      "the multiple-re-entry condition must be preserved")
        for d in d7["requiredDocs"]["requiredDocs"]:
            label = str(self._resolve(d))
            self.assertNotIn("사우디", label)
            self.assertNotIn("복수재입국", label)

    def test_no_status_exposes_reentry_documents_without_provenance(self):
        """Generalizes the old D-2 rule.

        D-2 used to be pinned as EMPTY because the 2026-05 manual carried no
        clean 복수재입국 line for it. The 2026.6 pass sourced it (pp. 35-55,
        유학(D-2)), so "D-2 must be empty" now asserts the absence of real data.
        The rule that actually prevents fabrication is not status-specific:
        documents may exist only where a manual reference does.
        """
        offenders = []
        for code, rec in self.recs.items():
            pr = ((rec.get("procedures") or {}).get("reentry")) or {}
            docs = (pr.get("requiredDocs") or {}).get("requiredDocs") or []
            if docs and not (pr.get("manualRefs") or []):
                offenders.append(code)
        self.assertEqual(offenders, [],
                         "these statuses list re-entry documents with no manual "
                         "reference to back them")

    def test_user_facing_confirmation_caution_is_retained(self):
        """What protects the user is the caution they read, not a metadata flag.

        This replaces an assertion that manualRefs[0].needsManualReview is True.
        The source-mapped 2026.6 pass cleared that provenance flag, but every
        record still tells the reader the list can differ by subcode,
        nationality, school type or residence history and must be confirmed
        before applying. That sentence is the protection, and it is what this
        now guards — a record may not drop it.
        """
        for code in POPULATED + ["D-2"]:
            with self.subTest(code=code):
                pr = self._reentry(code)
                if not pr:
                    continue
                notes = " ".join(pr.get("notes") or [])
                self.assertTrue(
                    any(k in notes for k in ("확인이 필요", "확인해야", "달라질 수 있")),
                    f"{code} reentry lost its confirm-before-relying caution",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
