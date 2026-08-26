"""Manual document-family / version / approval layer tests.

Enforces the Phase 2 invariants: unapproved content is never direct evidence, a
missing approval index fails closed, superseded editions are retained for
point-in-time questions, and a missing FTS index is distinguishable from an empty
result set.

    python3 -m pytest backend/tests/test_manual_registry.py -q
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import manual_registry as mr  # noqa: E402
from services import manual_search as ms  # noqa: E402


def _write(tmpdir, name, payload):
    path = Path(tmpdir) / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(path)


REGISTRY = {
    "sources": [
        {"id": "stay_manual_2026_06_23_pdf", "title": "외국인체류 안내매뉴얼",
         "authority": "법무부", "version": "2026.6", "source_date": "2026-06-23",
         "local_path": "a.pdf", "last_known_hash": "sha256:aaa", "status": "active",
         "confidence": "high"},
        {"id": "stay_manual_2026_05_pdf", "title": "외국인체류 안내매뉴얼 (2026.5)",
         "authority": "법무부", "version": "2026.5", "source_date": "2026-05-01",
         "local_path": "b.pdf", "status": "deprecated",
         "superseded_by": "stay_manual_2026_06_23_pdf"},
        {"id": "visa_manual_2026_06_17_pdf", "title": "사증발급 안내매뉴얼",
         "authority": "법무부", "version": "2026.6", "source_date": "2026-06-17",
         "local_path": "c.pdf", "status": "active"},
    ]
}


class FamilyDerivationTests(unittest.TestCase):
    def test_editions_of_the_same_manual_share_a_family(self):
        self.assertEqual(mr.derive_family("stay_manual_2026_06_23_pdf")[0],
                         mr.derive_family("stay_manual_2026_05_pdf")[0])

    def test_visa_and_stay_manuals_are_different_families(self):
        self.assertNotEqual(mr.derive_family("visa_manual_2026_06_17_pdf")[0],
                            mr.derive_family("stay_manual_2026_06_23_pdf")[0])

    def test_unknown_id_falls_back_to_other(self):
        self.assertEqual(mr.derive_family("something_else")[0], "other")


class ApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = _write(self.tmp.name, "registry.json", REGISTRY)

    def tearDown(self):
        self.tmp.cleanup()

    def _versions(self, approvals):
        approval_path = _write(self.tmp.name, "approvals.json", approvals)
        return mr.load_manual_versions(registry_path=self.registry_path,
                                       approval_path=approval_path)

    def test_document_with_no_review_record_is_needs_review(self):
        versions = self._versions({"documents": {}})
        stay = next(v for v in versions if v.source_id == "stay_manual_2026_06_23_pdf")
        self.assertEqual(stay.approval_state, mr.STATE_NEEDS_REVIEW)
        self.assertFalse(stay.usable_as_direct_evidence)

    def test_parsed_content_is_searchable_but_not_direct_evidence(self):
        versions = self._versions({"documents": {
            "stay_manual_2026_06_23_pdf": {"approval_state": "parsed"}}})
        stay = next(v for v in versions if v.source_id == "stay_manual_2026_06_23_pdf")
        gate = mr.evidence_gate(stay)
        self.assertFalse(gate["usable_as_direct_evidence"])
        self.assertTrue(gate["searchable"])
        self.assertEqual(gate["reason"], "review_pending")

    def test_approved_content_is_direct_evidence(self):
        versions = self._versions({"documents": {
            "stay_manual_2026_06_23_pdf": {"approval_state": "approved",
                                           "reviewer": "reviewer-a",
                                           "reviewed_at": "2026-07-01"}}})
        stay = next(v for v in versions if v.source_id == "stay_manual_2026_06_23_pdf")
        self.assertTrue(stay.usable_as_direct_evidence)
        self.assertEqual(mr.evidence_gate(stay)["reason"], "approved")

    def test_rejected_content_is_not_even_searchable(self):
        versions = self._versions({"documents": {
            "stay_manual_2026_06_23_pdf": {"approval_state": "rejected"}}})
        stay = next(v for v in versions if v.source_id == "stay_manual_2026_06_23_pdf")
        gate = mr.evidence_gate(stay)
        self.assertFalse(gate["searchable"])

    def test_unknown_state_string_degrades_to_needs_review(self):
        versions = self._versions({"documents": {
            "stay_manual_2026_06_23_pdf": {"approval_state": "totally_fine_trust_me"}}})
        stay = next(v for v in versions if v.source_id == "stay_manual_2026_06_23_pdf")
        self.assertEqual(stay.approval_state, mr.STATE_NEEDS_REVIEW)

    def test_deprecated_edition_cannot_stay_approved(self):
        versions = self._versions({"documents": {
            "stay_manual_2026_05_pdf": {"approval_state": "approved"}}})
        old = next(v for v in versions if v.source_id == "stay_manual_2026_05_pdf")
        self.assertEqual(old.approval_state, mr.STATE_SUPERSEDED)
        self.assertFalse(old.usable_as_direct_evidence)

    def test_missing_approval_index_fails_closed(self):
        versions = mr.load_manual_versions(
            registry_path=self.registry_path,
            approval_path=str(Path(self.tmp.name) / "does-not-exist.json"))
        self.assertTrue(versions)
        self.assertTrue(all(not v.usable_as_direct_evidence for v in versions))

    def test_corrupt_approval_index_fails_closed(self):
        bad = Path(self.tmp.name) / "bad.json"
        bad.write_text("{ this is not json", encoding="utf-8")
        versions = mr.load_manual_versions(registry_path=self.registry_path,
                                           approval_path=str(bad))
        self.assertTrue(all(not v.usable_as_direct_evidence for v in versions))

    def test_evidence_gate_of_missing_version_is_unavailable(self):
        gate = mr.evidence_gate(None)
        self.assertFalse(gate["usable_as_direct_evidence"])
        self.assertFalse(gate["searchable"])
        self.assertEqual(gate["reason"], "no_version_available")


class VersionSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = _write(self.tmp.name, "registry.json", REGISTRY)
        self.approval_path = _write(self.tmp.name, "approvals.json", {"documents": {
            "stay_manual_2026_06_23_pdf": {"approval_state": "approved",
                                           "effective_date": "2026-06-23"},
            "stay_manual_2026_05_pdf": {"approval_state": "superseded",
                                        "effective_date": "2026-05-01",
                                        "superseded_date": "2026-06-23"},
        }})
        self.versions = mr.load_manual_versions(registry_path=self.registry_path,
                                                approval_path=self.approval_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_current_version_is_the_newest_approved_edition(self):
        current = mr.current_version(self.versions, "stay_guide_manual")
        self.assertIsNotNone(current)
        self.assertEqual(current.source_id, "stay_manual_2026_06_23_pdf")

    def test_older_edition_is_retained_not_deleted(self):
        families = mr.group_by_family(self.versions)
        ids = [v.source_id for v in families["stay_guide_manual"]]
        self.assertIn("stay_manual_2026_05_pdf", ids)

    def test_point_in_time_lookup_returns_the_edition_then_in_force(self):
        older = mr.version_effective_on(self.versions, "stay_guide_manual", date(2026, 5, 15))
        self.assertIsNotNone(older)
        self.assertEqual(older.source_id, "stay_manual_2026_05_pdf")

    def test_point_in_time_lookup_after_supersession_returns_new_edition(self):
        newer = mr.version_effective_on(self.versions, "stay_guide_manual", date(2026, 7, 1))
        self.assertEqual(newer.source_id, "stay_manual_2026_06_23_pdf")

    def test_date_before_any_edition_returns_nothing(self):
        self.assertIsNone(
            mr.version_effective_on(self.versions, "stay_guide_manual", date(2020, 1, 1)))

    def test_current_version_is_none_when_family_has_no_approved_edition(self):
        self.assertIsNone(mr.current_version(self.versions, "visa_issuance_manual"))


class RealRegistryTests(unittest.TestCase):
    """The committed registry + approval index must load and stay fail-closed."""

    def test_real_registry_loads(self):
        versions = mr.load_manual_versions()
        self.assertTrue(versions, "the committed source registry must parse")

    def test_every_approved_edition_carries_a_recorded_human_review(self):
        """Content approval is a human action; nothing may ship pre-approved.

        This used to assert `approved == []`, which was true only while the
        evidence gate had never been opened. Editions have since been approved
        by a named reviewer, so the literal assertion had become a statement
        about history rather than about safety — and it failed on a deliberate,
        correctly-recorded approval.

        The invariant that actually matters is unchanged and is now asserted
        directly: an edition may back a direct factual assertion only if a
        human is on the record as having reviewed it. An edition that reached
        `approved` with no reviewer and no review date is auto-approval, and
        that is what must never ship.
        """
        unattested = [
            v.source_id
            for v in mr.load_manual_versions()
            if v.usable_as_direct_evidence and not (v.reviewer.strip() and v.reviewed_at.strip())
        ]
        self.assertEqual(
            unattested, [],
            "these editions may back direct assertions but record no human reviewer")

    def test_summary_reports_families_and_counts(self):
        summary = mr.registry_summary()
        self.assertGreater(summary["document_count"], 0)
        self.assertIn("stay_guide_manual", summary["families"])


class ManualSearchTests(unittest.TestCase):
    def test_missing_index_is_distinct_from_empty_results(self):
        result = ms.search_manuals("체류자격", path="/nonexistent/index.sqlite3")
        self.assertEqual(result["status"], ms.STATUS_INDEX_UNAVAILABLE)
        self.assertFalse(result["index_available"])
        self.assertEqual(ms.manual_evidence_state(result), "unavailable")

    def test_empty_query_is_rejected_before_touching_the_index(self):
        result = ms.search_manuals("   ", path="/nonexistent/index.sqlite3")
        self.assertEqual(result["status"], ms.STATUS_BAD_QUERY)

    def test_fts_operators_in_user_input_are_neutralized(self):
        # A stray quote/asterisk must be treated as text, never as FTS syntax.
        result = ms.search_manuals('"체류" OR *', path="/nonexistent/index.sqlite3")
        self.assertIn(result["status"], {ms.STATUS_INDEX_UNAVAILABLE, ms.STATUS_BAD_QUERY})

    def test_built_index_separates_approved_from_review_pending(self):
        built = REPO_ROOT / "build" / "manual_search_index.sqlite3"
        if not built.exists():
            self.skipTest("index not built in this environment")
        result = ms.search_manuals("체류자격", path=str(built))
        self.assertEqual(result["status"], ms.STATUS_OK)
        self.assertEqual(result["approved"], [],
                         "nothing is approved yet, so the approved bucket must be empty")
        self.assertTrue(result["needs_review"])
        self.assertEqual(ms.manual_evidence_state(result), "review_pending_only")


if __name__ == "__main__":
    unittest.main()
