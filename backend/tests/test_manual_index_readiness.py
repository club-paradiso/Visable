"""Manual grounding readiness must reflect what the index CONTAINS.

The bug these pin: the first version of ``/api/health/ai`` computed
``manual.ready`` as "an edition is approved AND the index file exists". Both can
be true while the index holds **zero** chunks from an approved edition — which
is the actual current state, because the approved 2026-07-31 manuals are
extracted to full text only and have no ``*_sections.json`` for the builder to
read.

That is the same class of false green the endpoint was written to prevent, so
readiness now requires the third fact: approved chunks are actually indexed.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient  # noqa: E402

import paradiso_backend as pb  # noqa: E402
from services import manual_search as ms  # noqa: E402


def _make_index(path: str, rows) -> None:
    """A minimal index with the columns index_composition reads."""
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE chunk (chunk_id INTEGER PRIMARY KEY, source_id TEXT, "
        "approval_state TEXT, direct_evidence INTEGER)"
    )
    con.executemany(
        "INSERT INTO chunk (source_id, approval_state, direct_evidence) VALUES (?, ?, ?)",
        rows,
    )
    con.commit()
    con.close()


class IndexCompositionTests(unittest.TestCase):
    def test_a_missing_index_reports_unavailable_not_empty(self):
        comp = ms.index_composition(path="/nonexistent/manual_index.sqlite3")
        self.assertFalse(comp["available"])
        self.assertEqual(comp["directEvidenceChunks"], 0)

    def test_composition_counts_approved_chunks_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "idx.sqlite3")
            _make_index(path, [
                ("approved_src", "approved", 1),
                ("approved_src", "approved", 1),
                ("old_src", "superseded", 0),
                ("draft_src", "needs_review", 0),
            ])
            comp = ms.index_composition(path=path)
        self.assertEqual(comp["totalChunks"], 4)
        self.assertEqual(comp["directEvidenceChunks"], 2)
        self.assertEqual(comp["byApprovalState"]["superseded"], 1)
        self.assertEqual(sorted(comp["sources"]), ["approved_src", "draft_src", "old_src"])

    def test_a_built_index_with_no_approved_chunks_is_reported_as_such(self):
        """"Built" and "approved evidence is searchable" are different facts."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "idx.sqlite3")
            _make_index(path, [("old_src", "superseded", 0)] * 50)
            comp = ms.index_composition(path=path)
        self.assertTrue(comp["available"])
        self.assertEqual(comp["totalChunks"], 50)
        self.assertEqual(comp["directEvidenceChunks"], 0)

    def test_an_unreadable_index_never_raises(self):
        """A probe must not be able to take down the endpoint reporting on it."""
        with tempfile.NamedTemporaryFile("w", suffix=".sqlite3", delete=False) as handle:
            handle.write("this is not a database")
            path = handle.name
        try:
            comp = ms.index_composition(path=path)
            self.assertTrue(comp["available"])
            self.assertEqual(comp["directEvidenceChunks"], 0)
        finally:
            os.unlink(path)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(pb.app)

    def _manual(self):
        return self.client.get("/api/health/ai").json()["grounding"]["manual"]

    def test_readiness_reports_indexed_composition_not_just_file_presence(self):
        manual = self._manual()
        for key in ("approvedEditions", "indexAvailable", "indexedChunks",
                    "indexedDirectEvidenceChunks", "ready", "blocker"):
            self.assertIn(key, manual)

    def test_ready_is_false_while_no_approved_chunk_is_indexed(self):
        manual = self._manual()
        if manual["indexedDirectEvidenceChunks"] == 0:
            self.assertFalse(
                manual["ready"],
                "approved manual evidence is not searchable, so readiness must be false",
            )

    def test_a_false_readiness_always_names_its_blocker(self):
        manual = self._manual()
        if not manual["ready"]:
            self.assertTrue(manual["blocker"], "an unready state must say why")

    def test_the_blocker_distinguishes_a_missing_index_from_an_unapproved_one(self):
        """Two different operator actions; conflating them wastes the operator's time."""
        manual = self._manual()
        if manual["indexAvailable"] and manual["indexedDirectEvidenceChunks"] == 0:
            blocker = manual["blocker"]
            self.assertIn("0 from an approved edition", blocker)
            # Must not tell an operator to run a build step that would not help.
            self.assertNotIn("the FTS index is not built", blocker)


class DeployConfigTests(unittest.TestCase):
    """The index is a build artifact; nothing built it at deploy time."""

    def test_the_railway_build_runs_the_index_builder(self):
        import json
        from pathlib import Path

        config = json.loads(
            (Path(__file__).resolve().parents[2] / "backend" / "railway.json").read_text()
        )
        build_command = config["build"].get("buildCommand", "")
        self.assertIn("build_manual_search_index.py", build_command)

    def test_a_failed_index_build_does_not_fail_the_deploy(self):
        """The app degrades to index_unavailable, which is the designed fallback.

        Killing a deploy over a search index would trade a weaker answer for no
        service at all.
        """
        import json
        from pathlib import Path

        config = json.loads(
            (Path(__file__).resolve().parents[2] / "backend" / "railway.json").read_text()
        )
        self.assertIn("||", config["build"].get("buildCommand", ""))


if __name__ == "__main__":
    unittest.main()
