"""Tests for the source-confirmed structured requirements runtime integration.

Covers PR #229 (feat/use-source-confirmed-structured-requirements-2026-05):

  - the structured_requirements helper loads and filters correctly
  - only HIGH / STRUCTURED_EVIDENCE_READY entries are exposed by default
  - needs-review entries are excluded unless an explicit internal option is set
  - /api/visas exposes sourceConfirmedStructuredRequirements only for READY
    statuses and stays backward-compatible
  - the dedicated endpoint returns source-confirmed entries (and gated internal
    candidate evidence only with include_needs_review)
  - the AI prompt includes the source-confirmed block for a READY status and
    NEVER for high-risk needs-review statuses (E-7 docs aside: the E-7 READY
    extension entry is allowed; the high-risk needs-review ones are not)

Run:
    python3 -m pytest backend/tests/test_structured_requirements.py -q
"""
from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Statuses that are known to be candidate-evidence-only (no source-confirmed
# entry) and must therefore NEVER reach user-facing answers.
HIGH_RISK_NEEDS_REVIEW = ["E-9", "F-5", "F-6", "G-1", "H-2", "C-3", "F-1", "F-2"]
READY_STATUSES = ["D-2", "D-4", "E-7"]


def _client():
    for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
        os.environ.pop(key, None)
    from fastapi.testclient import TestClient  # type: ignore

    import paradiso_backend  # noqa: WPS433

    paradiso_backend._reset_visas_cache_for_tests()
    paradiso_backend._reset_grounding_cache_for_tests()
    return TestClient(paradiso_backend.app), paradiso_backend


class StructuredRequirementsHelperTests(unittest.TestCase):
    def setUp(self):
        import structured_requirements as sr  # noqa: WPS433
        sr.reset_cache_for_tests()
        self.sr = sr

    def test_helper_loads_successfully(self):
        # Test 1: helper loads at least the 3 verified groundings.
        codes = self.sr.source_confirmed_status_codes()
        self.assertEqual(codes, ["D-2", "D-4", "E-7"])

    def test_known_ready_status_returns_entries(self):
        # Test 2: a known READY status returns entries.
        for code in READY_STATUSES:
            entries = self.sr.get_source_confirmed_structured_requirements(code)
            self.assertTrue(entries, f"{code} should have source-confirmed entries")
            for e in entries:
                self.assertEqual(e["confidence"], "HIGH")
                self.assertEqual(e["readinessLabel"], "STRUCTURED_EVIDENCE_READY")

    def test_needs_review_excluded_by_default(self):
        # Test 3: needs-review entries excluded by default.
        for code in HIGH_RISK_NEEDS_REVIEW:
            self.assertEqual(
                self.sr.get_structured_requirements(code), [],
                f"{code} must yield no entries by default (all needs-review)",
            )
            self.assertFalse(self.sr.has_source_confirmed_structured_requirements(code))
        # E-7 default returns ONLY the single source-confirmed entry, not the
        # 30+ candidate rows.
        e7_default = self.sr.get_structured_requirements("E-7")
        self.assertEqual(len(e7_default), 1)
        self.assertTrue(self.sr.is_source_confirmed(e7_default[0]))

    def test_needs_review_only_with_internal_option(self):
        # Test 4: needs-review entries only returned with explicit internal flag.
        internal = self.sr.get_structured_requirements(
            "F-5", {"includeNeedsReview": True}
        )
        self.assertTrue(internal, "F-5 should have candidate entries internally")
        self.assertTrue(any(not self.sr.is_source_confirmed(e) for e in internal))
        # The source-confirmed accessor still returns nothing for F-5.
        self.assertEqual(self.sr.get_source_confirmed_structured_requirements("F-5"), [])

    def test_subcode_filter_respects_covered_scope(self):
        covered = self.sr.get_source_confirmed_structured_requirements(
            "D-4", {"subCode": "D-4-1"}
        )
        self.assertTrue(covered)
        not_covered = self.sr.get_source_confirmed_structured_requirements(
            "D-4", {"subCode": "D-4-9"}
        )
        self.assertEqual(not_covered, [])

    def test_public_summary_omits_internal_fields(self):
        e = self.sr.get_source_confirmed_structured_requirements("D-2")[0]
        summary = self.sr.public_summary(e)
        self.assertEqual(summary["confidence"], "HIGH")
        self.assertIn("documents", summary)
        self.assertNotIn("reviewStatus", summary)
        self.assertNotIn("doNotFlatten", summary)
        self.assertNotIn("fieldEvidenceRowCount", summary)


class StructuredRequirementsApiTests(unittest.TestCase):
    def test_api_visas_exposes_only_ready_statuses(self):
        # Test 5 + Test 8: field present only for READY statuses; backward compat.
        client, _ = _client()
        resp = client.get("/api/visas")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # Backward-compatible shape + count unchanged.
        self.assertIn("data", body)
        self.assertIn("visas", body)
        self.assertEqual(body["count"], len(body["data"]))
        by_code = {r.get("code"): r for r in body["data"]}
        for code in READY_STATUSES:
            self.assertIn("sourceConfirmedStructuredRequirements", by_code[code],
                          f"{code} should expose source-confirmed requirements")
            entries = by_code[code]["sourceConfirmedStructuredRequirements"]
            self.assertTrue(entries)
            for e in entries:
                self.assertEqual(e["confidence"], "HIGH")
                self.assertEqual(e["readinessLabel"], "STRUCTURED_EVIDENCE_READY")
        for code in HIGH_RISK_NEEDS_REVIEW:
            rec = by_code.get(code)
            if rec is not None:
                self.assertNotIn(
                    "sourceConfirmedStructuredRequirements", rec,
                    f"{code} must NOT expose structured requirements (needs review)",
                )

    def test_endpoint_returns_source_confirmed_only_by_default(self):
        client, _ = _client()
        resp = client.get("/api/visas/D-4/structured-requirements")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["available"])
        self.assertEqual(body["sourceConfirmedCount"], len(body["sourceConfirmed"]))
        self.assertTrue(body["sourceConfirmed"])
        self.assertNotIn("internalNeedsReview", body)

    def test_endpoint_high_risk_status_has_no_source_confirmed(self):
        client, _ = _client()
        for code in HIGH_RISK_NEEDS_REVIEW:
            body = client.get(f"/api/visas/{code}/structured-requirements").json()
            self.assertEqual(body["sourceConfirmedCount"], 0)
            self.assertEqual(body["sourceConfirmed"], [])

    def test_endpoint_internal_flag_gates_candidate_evidence(self):
        client, _ = _client()
        body = client.get(
            "/api/visas/F-5/structured-requirements?include_needs_review=true"
        ).json()
        self.assertEqual(body["sourceConfirmedCount"], 0)
        self.assertGreater(body["internalNeedsReviewCount"], 0)
        self.assertIn("internalWarning", body)


class StructuredRequirementsGroundingTests(unittest.TestCase):
    """Verify the AI prompt includes the source-confirmed block for READY
    statuses and excludes needs-review evidence for high-risk statuses."""

    def _captured_prompt(self, mod, payload):
        captured = {}

        async def _capture(prompt, model=None):
            captured["prompt"] = prompt
            return "ok"

        os.environ["OPENROUTER_API_KEY"] = "test-key"
        try:
            with patch.object(mod, "OPENROUTER_API_KEY", "test-key"), \
                 patch.object(mod, "_call_openrouter", _capture):
                from fastapi.testclient import TestClient  # type: ignore
                client = TestClient(mod.app)
                resp = client.post("/api/ask", json=payload)
                self.assertEqual(resp.status_code, 200)
        finally:
            os.environ.pop("OPENROUTER_API_KEY", None)
        return captured["prompt"]

    def test_block_builder_includes_ready_excludes_needs_review(self):
        # Test 6 + 7 at the builder level (deterministic, no network).
        _, mod = _client()
        for code in READY_STATUSES:
            blk = mod._build_source_confirmed_structured_requirements_block(code, None)
            self.assertTrue(blk, f"{code} should produce a source-confirmed block")
            self.assertIn(
                "Source-confirmed structured requirements from 2026-05 official manuals",
                blk,
            )
        for code in HIGH_RISK_NEEDS_REVIEW:
            self.assertEqual(
                mod._build_source_confirmed_structured_requirements_block(code, None),
                "",
                f"{code} must not produce a source-confirmed block",
            )

    def test_d4_block_marks_subcode_scope(self):
        _, mod = _client()
        blk = mod._build_source_confirmed_structured_requirements_block("D-4", None)
        self.assertIn("D-4-1", blk)
        self.assertIn("D-4-7", blk)

    def test_ask_prompt_includes_source_confirmed_for_ready_status(self):
        # Test 6: AI prompt includes the block for a READY status.
        _, mod = _client()
        prompt = self._captured_prompt(
            mod, {"message": "D-4 연장 제출서류 알려줘", "visa_code": "D-4"}
        )
        self.assertIn(
            "Source-confirmed structured requirements from 2026-05 official manuals",
            prompt,
        )

    def test_ask_prompt_excludes_for_high_risk_status(self):
        # Test 7: AI prompt excludes structured block for needs-review statuses.
        _, mod = _client()
        for code in ("F-5", "F-6", "G-1", "H-2", "C-3"):
            prompt = self._captured_prompt(
                mod, {"message": f"{code} 관련 질문", "visa_code": code}
            )
            self.assertNotIn(
                "Source-confirmed structured requirements from 2026-05 official manuals",
                prompt,
                f"{code} prompt must not carry the source-confirmed block",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
