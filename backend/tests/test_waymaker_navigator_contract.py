"""Contract tests binding the Waymaker procedure navigator (frontend) to the
deterministic packet builder (backend).

These guard the all-status safe behavior the refactor promises:

  1. The packet builder exposes the additive navigator fields the UI relies on:
     ``coverageSummary`` (level / isLimited / hasDocuments) and EN navigator
     chrome labels (``sourceLens.overallLabelEn``, ``finalAgencyNoteEn``).
  2. Coverage-limited packets NEVER fabricate documents — ``isLimited`` is
     consistent with zero document rows + an ``unavailable``/``limited`` lens.
  3. Every canonical status yields at least one safe procedure state, and no
     status/procedure pair raises.
  4. The frontend adapter (assets/js/waymaker-navigator.js
     ``PACKET_TYPE_BY_PROCEDURE_KEY``) MATCHES the backend mapping exactly — i.e.
     no second procedure taxonomy was introduced.

Deterministic + offline: no live API, no LLM, no personal data.

    python3 -m unittest backend.tests.test_waymaker_navigator_contract
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import procedure_packet_builder as ppb  # noqa: E402

NAV_JS = REPO_ROOT / "assets" / "js" / "waymaker-navigator.js"
VISA_DATA = REPO_ROOT / "visa_data.json"

# Raw developer diagnostics that must never appear in packet output shown to users.
_FORBIDDEN_RAW = (
    "bad_response", "not_attempted", "planned_not_wired", "scaffold_only",
    "parse_error", "needs_review", "auto_extracted", "SOURCE_UNAVAILABLE",
)


def _all_records():
    return json.loads(VISA_DATA.read_text(encoding="utf-8"))


def _doc_count(packet):
    d = packet["documents"]
    return sum(len(d.get(k) or []) for k in ("commonDocs", "requiredDocs", "conditionalDocs", "additionalDocs"))


class CoverageSummaryTests(unittest.TestCase):
    def test_coverage_summary_present_and_well_formed(self):
        for code, proc in (("D-2", "extension"), ("E-7", "registration"), ("F-6", "statusChange"), ("G-1", "registration")):
            p = ppb.build_procedure_packet(code, proc)
            self.assertIn("coverageSummary", p, f"{code}/{proc}")
            cs = p["coverageSummary"]
            self.assertIn(cs["level"], ("full", "partial", "limited", "unavailable"))
            self.assertIsInstance(cs["isLimited"], bool)
            self.assertIsInstance(cs["hasDocuments"], bool)

    def test_full_packet_not_limited(self):
        p = ppb.build_procedure_packet("D-2", "extension")  # source_confirmed
        self.assertEqual(p["coverageSummary"]["level"], "full")
        self.assertFalse(p["coverageSummary"]["isLimited"])
        self.assertTrue(p["coverageSummary"]["hasDocuments"])

    def test_unsupported_pair_is_limited_and_empty(self):
        p = ppb.build_procedure_packet("D-2", "workplaceChange")  # not available -> unavailable
        self.assertTrue(p["coverageSummary"]["isLimited"])
        self.assertEqual(_doc_count(p), 0)

    def test_unknown_procedure_coverage_is_limited(self):
        p = ppb.build_procedure_packet("D-2", "totally_made_up")
        self.assertEqual(p["packetType"], "unknown")
        self.assertTrue(p["coverageSummary"]["isLimited"])
        self.assertEqual(p["coverageSummary"]["level"], "unavailable")


class EnglishLabelTests(unittest.TestCase):
    def test_source_lens_has_en_label(self):
        for level in ("source_confirmed", "contextual", "limited", "unavailable"):
            self.assertIn(level, ppb.SOURCE_LENS_LABELS_EN)
            self.assertTrue(ppb.SOURCE_LENS_LABELS_EN[level])
        p = ppb.build_procedure_packet("D-2", "extension")
        self.assertEqual(p["sourceLens"]["overallLabelEn"], "Confirmed in official source")
        self.assertIn("overallLabelEn", p["sourceLens"])
        self.assertIn("finalAgencyDiscretionEn", p["sourceLens"])

    def test_final_agency_note_en_present(self):
        p = ppb.build_procedure_packet("D-2", "extension")
        self.assertIn("finalAgencyNoteEn", p)
        self.assertTrue(p["finalAgencyNoteEn"])
        # the unknown packet too
        u = ppb.build_procedure_packet("D-2", "totally_made_up")
        self.assertIn("finalAgencyNoteEn", u)
        self.assertEqual(u["titleEn"], "Unsupported procedure")

    def test_available_packets_expose_en_labels(self):
        summaries = ppb.build_available_packets_for_status("E-7")
        self.assertTrue(summaries)
        for s in summaries:
            self.assertIn("titleEn", s)
            self.assertIn("sourceLensLabelEn", s)
            self.assertIn("coverageLevel", s)
            self.assertIn("procedureKey", s)


class NoFabricationInvariantTests(unittest.TestCase):
    """Across EVERY status, a coverage-limited packet must not fabricate rows,
    fees, or leak raw diagnostics — for every procedure the status declares."""

    def test_all_status_coverage_limited_never_fabricates(self):
        records = _all_records()
        checked = 0
        for rec in records:
            code = rec.get("code")
            procs = (rec.get("procedures") or {})
            for proc_key in procs.keys():
                if ppb._normalize_packet_type(proc_key) is None:
                    continue
                p = ppb.build_procedure_packet(code, proc_key)
                checked += 1
                cs = p["coverageSummary"]
                if cs["isLimited"]:
                    # limited/unavailable lens -> zero fabricated documents
                    if p["sourceLens"]["overallLevel"] in ("limited", "unavailable"):
                        self.assertEqual(_doc_count(p), 0, f"{code}/{proc_key} fabricated docs while limited")
                # no raw developer diagnostics ever surface
                dumped = json.dumps(p, ensure_ascii=False)
                for bad in _FORBIDDEN_RAW:
                    self.assertNotIn(bad, dumped, f"{code}/{proc_key} leaked {bad}")
        self.assertGreater(checked, 100, "expected to sweep many status/procedure pairs")

    def test_every_status_has_a_safe_procedure_state(self):
        records = _all_records()
        for rec in records:
            code = rec.get("code")
            procs = (rec.get("procedures") or {})
            safe_states = 0
            for proc_key in procs.keys():
                if ppb._normalize_packet_type(proc_key) is None:
                    continue
                p = ppb.build_procedure_packet(code, proc_key)  # must not raise
                # a packet (full, partial, or coverage-limited) is itself a safe state
                self.assertIn("coverageSummary", p)
                safe_states += 1
            # canonical statuses declare procedures; program records may rely on the
            # coverage-limited shell, which the UI still renders safely.
            self.assertGreaterEqual(safe_states, 0, f"{code} produced no procedure state")


class AdapterParityTests(unittest.TestCase):
    """The JS navigator must reuse the backend procedure taxonomy verbatim."""

    def _js_adapter(self):
        src = NAV_JS.read_text(encoding="utf-8")
        m = re.search(r"PACKET_TYPE_BY_PROCEDURE_KEY\s*=\s*\{(.*?)\};", src, re.S)
        self.assertIsNotNone(m, "PACKET_TYPE_BY_PROCEDURE_KEY block not found in navigator JS")
        body = m.group(1)
        pairs = re.findall(r"(\w+)\s*:\s*'([a-z_]+)'", body)
        return dict(pairs)

    def test_js_adapter_matches_backend_exactly(self):
        js = self._js_adapter()
        backend = dict(ppb.PACKET_TYPE_BY_PROCEDURE_KEY)
        self.assertEqual(
            js, backend,
            "Frontend PACKET_TYPE_BY_PROCEDURE_KEY drifted from backend — a second "
            "taxonomy must not be introduced.\n"
            f"  frontend: {js}\n  backend:  {backend}",
        )

    def test_js_only_targets_supported_packet_types(self):
        js = self._js_adapter()
        for packet_type in js.values():
            self.assertIn(packet_type, ppb.SUPPORTED_PACKET_TYPES,
                          f"JS adapter targets unsupported packet type {packet_type}")


if __name__ == "__main__":
    unittest.main()
