"""Tests for the Procedure Packet Builder + safe Application Typing Helper.

Covers (Phase 10 + the 통합신청서 official-document correction):

  1. Packet model shape; exact sub-code preserved; missing data -> limited (not fake).
  2. Document grouping (common/required/conditional/additional); placeholders
     and generic "missing data" rows are never shown.
  3. Source lens grading + public-safe labels (no raw developer diagnostics).
  4. Procedure-key -> packet-type mapping.
  5. Application typing helper: typing_guide_only, no personal values, warnings.
  6. Regression fixtures (D-2 / E-7 / F-6 / H-1 / G-1).
  7. 통합신청서 (별지 제34호) is treated as an official PacketDocument when
     source-backed, never suppressed and never replaced by the helper.
  8. API endpoint behavior (deterministic, no personal data, public-safe).

Deterministic + offline: no live API, no LLM, no personal data fixtures.

    python3 -m pytest backend/tests/test_procedure_packet_builder.py -q
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import procedure_packet_builder as ppb  # noqa: E402

# Raw developer diagnostics that must never appear in packet output. ("limited"
# / "unavailable" are part of the PUBLIC source-lens scale and are allowed.)
_FORBIDDEN_RAW_CODES = (
    "bad_response", "not_attempted", "planned_not_wired", "scaffold_only",
    "parse_error", "official_error", "law_api_", "SOURCE_UNAVAILABLE",
    "needs_review", "auto_extracted",
)
_FORBIDDEN_PLACEHOLDER_STRINGS = (
    "문서명 미상", "비고 정보 없음", "매뉴얼 확인 필요", "정보 없음",
)
# Personal-identifier value keys the helper must never carry.
_FORBIDDEN_VALUE_KEYS = (
    "value", "values", "inputValue", "passportNumber", "arcNumber",
    "phoneNumber", "addressValue", "employerName", "schoolId", "filledForm",
    "completedForm", "generatedForm", "pdf",
)
_ALLOWED_FIELD_KEYS = {
    "fieldId", "labelKo", "explanationKo", "requiredness", "doNotStore",
    "userShouldTypeFrom", "cautionKo", "sourceRefs",
}


def _all_doc_rows(packet):
    docs = packet["documents"]
    return [
        d for k in ("commonDocs", "requiredDocs", "conditionalDocs", "additionalDocs")
        for d in docs[k]
    ]


# ---------------------------------------------------------------------------
# 1. Packet model
# ---------------------------------------------------------------------------
class PacketModelTests(unittest.TestCase):
    def test_packet_has_required_top_level_fields(self):
        p = ppb.build_procedure_packet("D-2", "extension")
        for key in ("packetId", "packetType", "titleKo", "sourceLens", "nextActions", "finalAgencyNoteKo", "applicationTypingHelper"):
            self.assertIn(key, p)
        self.assertTrue(p["nextActions"])
        self.assertIn("관할 출입국·외국인관서", p["finalAgencyNoteKo"])
        self.assertEqual(p["packetType"], "extension")

    def test_exact_sub_code_preserved(self):
        p = ppb.build_procedure_packet("D-2-1", "extension")
        self.assertEqual(p["exactStatusCode"], "D-2-1")
        self.assertEqual(p["parentStatusCode"], "D-2")
        # Parent is used to resolve the record, but the exact sub-code is kept.
        self.assertEqual(p["statusCode"], "D-2-1")

    def test_missing_source_data_is_limited_not_fake(self):
        # D-2 status change: procedure available in visa_data but no structured
        # documents -> limited packet, zero fabricated rows.
        p = ppb.build_procedure_packet("D-2", "statusChange")
        self.assertIn(p["sourceLens"]["overallLevel"], ("limited", "unavailable", "contextual"))
        if p["sourceLens"]["overallLevel"] in ("limited", "unavailable"):
            self.assertEqual(len(_all_doc_rows(p)), 0)
            self.assertIn("limitationKo", p["documents"])
            self.assertFalse(p["documents"]["sourceBacked"])

    def test_unknown_procedure_is_public_safe(self):
        p = ppb.build_procedure_packet("D-2", "totally_made_up")
        self.assertEqual(p["packetType"], "unknown")
        self.assertEqual(p["sourceLens"]["overallLevel"], "unavailable")
        self.assertIn("finalAgencyNoteKo", p)


# ---------------------------------------------------------------------------
# 2. Document grouping
# ---------------------------------------------------------------------------
class DocumentGroupingTests(unittest.TestCase):
    def test_source_confirmed_groups_documents(self):
        p = ppb.build_procedure_packet("D-2", "extension")
        docs = p["documents"]
        # Common docs (신청서/여권/외국인등록증/수수료) are grouped as common.
        common_names = " ".join(d["nameKo"] for d in docs["commonDocs"])
        self.assertTrue(any(m in common_names for m in ("신청서", "여권", "외국인등록증", "수수료")))
        # The "(해당자)" document is preserved as conditional, not dropped.
        self.assertTrue(docs["conditionalDocs"])
        self.assertTrue(any("해당자" in d["nameKo"] for d in docs["conditionalDocs"]))

    def test_no_placeholder_rows_anywhere(self):
        # Sweep many codes/procedures; no placeholder string may surface as a doc.
        for code in ("D-2", "E-7", "F-2", "H-2", "F-6", "C-3", "G-1"):
            for proc in ("registration", "extension", "statusChange", "workplaceChange", "reentry"):
                p = ppb.build_procedure_packet(code, proc)
                for d in _all_doc_rows(p):
                    for bad in _FORBIDDEN_PLACEHOLDER_STRINGS:
                        self.assertNotIn(bad, d["nameKo"], f"{code}/{proc}")

    def test_limited_packet_has_single_concise_limitation(self):
        # A code+procedure whose visa_data docs are placeholder-only -> exactly
        # one documents.limitationKo, never repeated placeholder rows.
        p = ppb.build_procedure_packet("H-2", "extension")
        if p["sourceLens"]["overallLevel"] in ("limited", "unavailable"):
            self.assertEqual(len(_all_doc_rows(p)), 0)
            self.assertIsInstance(p["documents"].get("limitationKo"), str)


# ---------------------------------------------------------------------------
# 3. Source lens
# ---------------------------------------------------------------------------
class SourceLensTests(unittest.TestCase):
    def test_source_confirmed_when_structured_requirements_exist(self):
        p = ppb.build_procedure_packet("D-2", "extension")
        self.assertEqual(p["sourceLens"]["overallLevel"], "source_confirmed")
        self.assertEqual(p["sourceLens"]["overallLabelKo"], "공식근거 직접 확인")
        self.assertTrue(p["documents"]["sourceBacked"])
        self.assertTrue(p["sourceLens"]["sources"])

    def test_contextual_when_only_visa_data_docs(self):
        p = ppb.build_procedure_packet("C-3", "extension")
        # C-3 extension docs come from visa_data manual refs (needs-review).
        self.assertIn(p["sourceLens"]["overallLevel"], ("contextual", "limited"))
        self.assertFalse(p["documents"]["sourceBacked"])

    def test_no_raw_diagnostics_in_packet(self):
        for code, proc in (("D-2", "extension"), ("C-3", "extension"), ("G-1", "registration"), ("D-2", "statusChange")):
            p = ppb.build_procedure_packet(code, proc)
            dumped = json.dumps(p, ensure_ascii=False)
            for bad in _FORBIDDEN_RAW_CODES:
                self.assertNotIn(bad, dumped, f"{code}/{proc} leaked {bad}")

    def test_lens_level_is_public_scale(self):
        p = ppb.build_procedure_packet("G-1", "registration")
        self.assertIn(p["sourceLens"]["overallLevel"], ppb.SOURCE_LENS_LEVELS)
        self.assertIn(p["sourceLens"]["overallLabelKo"], ppb.SOURCE_LENS_LABELS_KO.values())


# ---------------------------------------------------------------------------
# 4. Procedure mapping
# ---------------------------------------------------------------------------
class ProcedureMappingTests(unittest.TestCase):
    CASES = [
        ("registration", "foreigner_registration"),
        ("extension", "extension"),
        ("statusChange", "status_change"),
        ("activitiesOutsideStatus", "activities_outside_status"),
        ("workplaceChange", "workplace_change"),
        ("reentry", "reentry_permit"),
        ("statusGrant", "status_grant"),
    ]

    def test_procedure_keys_map_to_packet_types(self):
        for proc_key, expected in self.CASES:
            p = ppb.build_procedure_packet("E-7", proc_key)
            self.assertEqual(p["packetType"], expected, proc_key)

    def test_packet_type_passthrough(self):
        # The public packet type can be passed directly too.
        p = ppb.build_procedure_packet("D-2", "foreigner_registration")
        self.assertEqual(p["packetType"], "foreigner_registration")


# ---------------------------------------------------------------------------
# 5. Application typing helper (privacy-safe)
# ---------------------------------------------------------------------------
class ApplicationTypingHelperTests(unittest.TestCase):
    def helper(self, code="D-2", proc="extension"):
        return ppb.build_procedure_packet(code, proc)["applicationTypingHelper"]

    def test_mode_and_privacy(self):
        h = self.helper()
        self.assertEqual(h["mode"], "typing_guide_only")
        self.assertEqual(h["privacyMode"], "no_storage_no_llm_for_personal_data")
        self.assertTrue(h["warnings"])
        self.assertIn("관할 출입국·외국인관서", h["finalAgencyNoteKo"])

    def test_helper_has_field_guidance_not_values(self):
        h = self.helper()
        self.assertTrue(h["fieldGroups"])
        for group in h["fieldGroups"]:
            for field in group["fields"]:
                # Only guidance keys are allowed — never a value-bearing key.
                self.assertTrue(set(field.keys()).issubset(_ALLOWED_FIELD_KEYS), set(field.keys()))
                self.assertIn("explanationKo", field)
                self.assertIn("doNotStore", field)

    def test_helper_never_carries_personal_value_keys(self):
        h = self.helper()
        dumped = json.dumps(h, ensure_ascii=False)
        for bad in _FORBIDDEN_VALUE_KEYS:
            self.assertNotIn(f'"{bad}"', dumped, f"helper leaked value key {bad}")

    def test_personal_identifier_fields_marked_do_not_store(self):
        h = self.helper("E-7", "extension")
        personal_field_ids = {"passport_no", "registration_no", "address_in_korea", "phone", "full_name"}
        for group in h["fieldGroups"]:
            for field in group["fields"]:
                if field["fieldId"] in personal_field_ids:
                    self.assertTrue(field["doNotStore"], field["fieldId"])

    def test_helper_references_official_form_without_replacing(self):
        h = self.helper()
        ref = h["referencesOfficialForm"]
        self.assertIn("통합신청서", ref["nameKo"])
        self.assertIn("시행규칙", ref["basisKo"])
        self.assertIn("대체하지", ref["noteKo"])  # does not replace the official form

    def test_helper_source_lens_is_public_safe(self):
        h = self.helper()
        self.assertEqual(h["sourceLens"]["overallLevel"], "limited")
        self.assertIn(h["sourceLens"]["overallLabelKo"], ppb.SOURCE_LENS_LABELS_KO.values())

    def test_no_completed_form_generated(self):
        p = ppb.build_procedure_packet("D-2", "extension")
        dumped = json.dumps(p, ensure_ascii=False)
        for bad in ("completedForm", "filledForm", "generatedForm", "submittedForm"):
            self.assertNotIn(bad, dumped)


# ---------------------------------------------------------------------------
# 6. Regression fixtures (concrete cases as tests, not production branches)
# ---------------------------------------------------------------------------
class RegressionFixtureTests(unittest.TestCase):
    def test_d2_registration_and_extension_source_confirmed(self):
        for proc in ("registration", "extension"):
            p = ppb.build_procedure_packet("D-2", proc)
            self.assertEqual(p["sourceLens"]["overallLevel"], "source_confirmed")
            self.assertTrue(_all_doc_rows(p))

    def test_e7_workplace_change_is_valid_packet(self):
        p = ppb.build_procedure_packet("E-7", "workplaceChange")
        self.assertEqual(p["packetType"], "workplace_change")
        self.assertIn(p["sourceLens"]["overallLevel"], ppb.SOURCE_LENS_LEVELS)

    def test_f6_status_change_is_valid_packet(self):
        p = ppb.build_procedure_packet("F-6", "statusChange")
        self.assertEqual(p["packetType"], "status_change")
        self.assertIn(p["sourceLens"]["overallLevel"], ppb.SOURCE_LENS_LEVELS)

    def test_h1_registration_is_valid_packet(self):
        p = ppb.build_procedure_packet("H-1", "registration")
        self.assertEqual(p["packetType"], "foreigner_registration")
        self.assertIn(p["sourceLens"]["overallLevel"], ppb.SOURCE_LENS_LEVELS)

    def test_g1_is_source_limited(self):
        p = ppb.build_procedure_packet("G-1", "registration")
        self.assertIn(p["sourceLens"]["overallLevel"], ("limited", "unavailable"))
        self.assertEqual(len(_all_doc_rows(p)), 0)

    def test_available_packets_summary(self):
        summaries = ppb.build_available_packets_for_status("D-2")
        self.assertTrue(summaries)
        types = {s["packetType"] for s in summaries}
        self.assertIn("extension", types)
        for s in summaries:
            self.assertIn(s["sourceLensLevel"], ppb.SOURCE_LENS_LEVELS)
            self.assertTrue(s["hasApplicationTypingHelper"])


# ---------------------------------------------------------------------------
# 7. 통합신청서 as an official document (correction)
# ---------------------------------------------------------------------------
class UnifiedApplicationFormDocumentTests(unittest.TestCase):
    def test_unified_form_appears_as_packet_document_when_source_backed(self):
        # C-3 extension's visa_data doc list includes 통합신청서(별지 제34호 서식).
        p = ppb.build_procedure_packet("C-3", "extension")
        rows = _all_doc_rows(p)
        form_rows = [d for d in rows if "통합신청서" in d["nameKo"] or "별지 제34호" in d["nameKo"]]
        self.assertTrue(form_rows, "통합신청서 should be a PacketDocument")
        form = form_rows[0]
        self.assertTrue(form.get("isOfficialForm"))
        # It carries the official-form note and source refs (manual-backed).
        self.assertIn("통합신청서", form.get("noteKo", ""))
        self.assertTrue(form.get("sourceRefs"))

    def test_unified_form_not_suppressed_as_placeholder(self):
        p = ppb.build_procedure_packet("C-3", "extension")
        form_rows = [d for d in _all_doc_rows(p) if "통합신청서" in d["nameKo"]]
        for d in form_rows:
            self.assertNotIn("미상", d["nameKo"])
            self.assertNotIn("정보 없음", d["nameKo"])

    def test_unified_form_remains_in_documents_not_only_helper(self):
        # The official form must be in the documents section, not replaced by
        # the typing helper.
        p = ppb.build_procedure_packet("C-3", "extension")
        in_docs = any("통합신청서" in d["nameKo"] for d in _all_doc_rows(p))
        self.assertTrue(in_docs)
        # The helper references the form but is typing-guide-only (no values).
        self.assertEqual(p["applicationTypingHelper"]["mode"], "typing_guide_only")

    def test_unified_form_grouped_as_common_official_document(self):
        p = ppb.build_procedure_packet("C-3", "extension")
        common = " ".join(d["nameKo"] for d in p["documents"]["commonDocs"])
        self.assertIn("통합신청서", common)

    def test_unified_form_source_lens_manual_or_limited(self):
        p = ppb.build_procedure_packet("C-3", "extension")
        form = next(d for d in _all_doc_rows(p) if "통합신청서" in d["nameKo"])
        for ref in form.get("sourceRefs", []):
            self.assertIn(ref["sourceFamily"], ("manual", "enforcement_rule", "statute", "law"))
            self.assertIn(ref["evidenceLevel"], ("source_confirmed", "contextual", "limited"))


# ---------------------------------------------------------------------------
# 8. API endpoint behavior
# ---------------------------------------------------------------------------
class ProcedurePacketEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient  # type: ignore
            import paradiso_backend  # noqa: WPS433
            cls.client = TestClient(paradiso_backend.app)
        except Exception as exc:  # pragma: no cover
            cls.client = None
            cls._skip_reason = str(exc)

    def setUp(self):
        if self.client is None:
            self.skipTest(f"FastAPI TestClient unavailable: {getattr(self, '_skip_reason', '')}")

    def test_valid_status_procedure_returns_packet(self):
        resp = self.client.get("/api/procedure-packet", params={"status": "D-2", "procedure": "extension"})
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["packetType"], "extension")
        self.assertEqual(body["sourceLens"]["overallLevel"], "source_confirmed")

    def test_invalid_procedure_returns_clean_400(self):
        resp = self.client.get("/api/procedure-packet", params={"status": "D-2", "procedure": "nonsense"})
        self.assertEqual(resp.status_code, 400)
        detail = resp.json()["detail"]
        self.assertEqual(detail["error"], "unsupported_procedure")
        # No raw developer diagnostics in the error.
        for bad in _FORBIDDEN_RAW_CODES:
            self.assertNotIn(bad, resp.text)

    def test_missing_params_returns_400(self):
        resp = self.client.get("/api/procedure-packet", params={"status": "D-2"})
        self.assertIn(resp.status_code, (400, 422))

    def test_endpoint_output_has_no_raw_diagnostics(self):
        resp = self.client.get("/api/procedure-packet", params={"status": "C-3", "procedure": "extension"})
        self.assertEqual(resp.status_code, 200)
        for bad in _FORBIDDEN_RAW_CODES:
            self.assertNotIn(bad, resp.text)

    def test_available_packets_endpoint(self):
        resp = self.client.get("/api/visas/D-2/packets")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["available"])
        self.assertTrue(body["packets"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
