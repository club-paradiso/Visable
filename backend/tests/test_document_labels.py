"""Tests for doc_master ID resolution.

The bug this fixes: the procedure packet builder emitted
``{"nameKo": "doc_fee_generic"}`` — a raw internal identifier in a field named
"Korean name", served by ``/api/procedure-packet`` and rendered to users as the
name of a document to bring to an immigration office.

The bug this does NOT fix, deliberately: ``/api/visas`` still carries raw IDs in
its procedure document arrays. That is an internal key, not a display value, and
``assets/js/complex-status-guide.js`` depends on it to tell audit-safe registry
documents from unverified manual prose. Resolving there empties that checklist.
The last test class pins that reasoning so a future change does not quietly
undo it.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services import document_labels as dl  # noqa: E402
from services.procedure_packet_builder import build_procedure_packet  # noqa: E402


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        dl.reset_cache_for_tests()

    def test_a_known_id_resolves_to_its_registered_korean_label(self):
        self.assertEqual(dl.resolve_document_label("doc_fee_generic"), "수수료")

    def test_english_resolution_uses_the_registered_english_label(self):
        entry = dl.load_document_labels()["doc_purpose"]
        self.assertEqual(dl.resolve_document_label("doc_purpose", lang="en"), entry["en"])

    def test_manual_prose_is_never_touched(self):
        """Korean manual text must not be mistaken for an identifier."""
        for prose in ("통합신청서 (별지 제34호 서식)", "여권 원본", "외국인등록증", "수수료"):
            with self.subTest(prose=prose):
                self.assertEqual(dl.resolve_document_label(prose), prose)

    def test_an_unknown_id_shaped_token_is_left_alone(self):
        """Inventing a label for an undefined ID would fabricate a requirement."""
        self.assertEqual(dl.resolve_document_label("doc_not_in_registry"), "doc_not_in_registry")
        self.assertFalse(dl.is_document_id("doc_not_in_registry"))

    def test_resolution_is_idempotent(self):
        once = dl.resolve_document_label("doc_fee_generic")
        self.assertEqual(dl.resolve_document_label(once), once)

    def test_non_strings_pass_through(self):
        for value in (None, 3, {"a": 1}, ["x"]):
            self.assertEqual(dl.resolve_document_label(value), value)

    def test_every_group_of_a_required_docs_object_is_resolved(self):
        resolved = dl.resolve_required_docs({
            "commonDocs": ["doc_fee_generic"],
            "requiredDocs": ["여권 원본", "doc_purpose"],
            "conditionalDocs": [],
            "additionalDocs": ["doc_standard_photo_one"],
        })
        self.assertEqual(resolved["commonDocs"], ["수수료"])
        self.assertEqual(resolved["requiredDocs"][0], "여권 원본")
        self.assertNotIn("doc_", json.dumps(resolved, ensure_ascii=False))

    def test_the_input_object_is_not_mutated(self):
        """_load_visas caches parsed data; mutating it corrupts later requests."""
        original = {"requiredDocs": ["doc_fee_generic"]}
        dl.resolve_required_docs(original)
        self.assertEqual(original["requiredDocs"], ["doc_fee_generic"])


class RegistryFailureTests(unittest.TestCase):
    def setUp(self):
        dl.reset_cache_for_tests()

    def tearDown(self):
        dl.reset_cache_for_tests()

    def test_a_missing_registry_degrades_to_pass_through(self):
        """Resolution improves a value; it is never a precondition for serving."""
        self.assertEqual(dl.load_document_labels(path="/nonexistent/doc_master.json"), {})
        self.assertEqual(
            dl.resolve_document_label("doc_fee_generic", path="/nonexistent/doc_master.json"),
            "doc_fee_generic",
        )

    def test_a_malformed_registry_degrades_to_pass_through(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write("{ not json")
            bad = handle.name
        try:
            self.assertEqual(dl.load_document_labels(path=bad), {})
        finally:
            os.unlink(bad)

    def test_entries_without_an_id_or_name_are_skipped(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as handle:
            json.dump([{"id": "doc_ok", "ko_name": "라벨"}, {"id": ""}, {"ko_name": "x"},
                       "not-a-dict"], handle)
            path = handle.name
        try:
            labels = dl.load_document_labels(path=path)
            self.assertEqual(set(labels), {"doc_ok"})
        finally:
            os.unlink(path)


class PacketBuilderTests(unittest.TestCase):
    """The actual leak: a raw ID served as a user-facing document name."""

    def test_the_packet_no_longer_names_a_document_by_its_internal_id(self):
        blob = json.dumps(build_procedure_packet("D-1", "reentry"), ensure_ascii=False)
        self.assertNotIn("doc_fee_generic", blob)
        self.assertIn("수수료", blob)

    def test_no_packet_across_the_catalog_exposes_an_id_shaped_name(self):
        import re
        import paradiso_backend as pb

        offenders = []
        for record in pb._load_visas()["visas"]:
            code = record.get("code")
            for proc in (record.get("procedures") or {}):
                try:
                    packet = build_procedure_packet(code, proc)
                except Exception:
                    continue
                for name in re.findall(r'"nameKo":\s*"([^"]+)"',
                                       json.dumps(packet, ensure_ascii=False)):
                    if re.match(r"^[a-z][a-z0-9_]*$", name):
                        offenders.append(f"{code}/{proc}: {name}")
        self.assertEqual(offenders, [], "id-shaped strings served as document names")


class TransportKeepsRawIdsTests(unittest.TestCase):
    """Pin why /api/visas is deliberately NOT resolved.

    complex-status-guide.js renders a checklist ONLY from resolvable doc_master
    IDs — that is how it keeps unverified manual prose out of an audit-safe
    list. Resolving at the transport turns those IDs into prose and empties the
    checklist, so the ID has to survive to the browser.
    """

    def test_api_visas_still_carries_raw_ids_for_the_guide_to_partition(self):
        from fastapi.testclient import TestClient
        import paradiso_backend as pb

        pb._reset_visas_cache_for_tests()
        body = TestClient(pb.app).get("/api/visas").json()
        recs = {r.get("code"): r for r in body["data"]}
        docs = recs["D-1"]["procedures"]["reentry"]["requiredDocs"]["requiredDocs"]
        self.assertIn(
            "doc_fee_generic", docs,
            "the guide's checklist partition needs the raw ID; resolve at the "
            "consumer that renders a name, not at the transport",
        )

    def test_the_id_the_guide_relies_on_is_resolvable(self):
        """A raw ID is only acceptable in transit because every renderer can resolve it."""
        self.assertTrue(dl.is_document_id("doc_fee_generic"))


class DiagnosticTests(unittest.TestCase):
    def test_undefined_ids_are_reported_rather_than_guessed(self):
        record = {"procedures": {"reentry": {"requiredDocs": {
            "requiredDocs": ["doc_fee_generic", "doc_never_defined", "여권 원본"]}}}}
        self.assertEqual(dl.unresolved_document_ids(record), ["doc_never_defined"])

    def test_the_shipped_catalog_has_no_undefined_document_ids(self):
        import paradiso_backend as pb

        offenders = {}
        for record in pb._load_visas()["visas"]:
            missing = dl.unresolved_document_ids(record)
            if missing:
                offenders[record.get("code")] = missing
        self.assertEqual(offenders, {},
                         "these IDs are referenced but not defined in doc_master.json")


if __name__ == "__main__":
    unittest.main()
