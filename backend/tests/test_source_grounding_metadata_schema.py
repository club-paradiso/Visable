"""Tests for the source-grounding metadata model.

Pure-stdlib (no fastapi/pydantic/pytest required) so it runs in any
environment, including the restricted CI path used by scripts/check_repo.sh.

Covered by the task's validation requirements:
  - source metadata schema validation
  - manual version metadata
  - no hash drift between the registry and the manifest (stale-source guard)
  - the AnswerGrounding crosswalk targets actually exist on AskResponse
    (so the per-answer grounding lineage the audit relies on is real)
"""
from __future__ import annotations

import json
import os
import re
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import check_source_grounding_metadata as validator  # noqa: E402

SCHEMA_PATH = os.path.join(REPO_ROOT, "data", "schemas", "source_grounding_schema.json")
BACKEND_PATH = os.path.join(REPO_ROOT, "backend", "paradiso_backend.py")


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class SchemaShapeTests(unittest.TestCase):
    def setUp(self):
        self.schema = _load(SCHEMA_PATH)

    def test_declares_three_record_types(self):
        rt = self.schema.get("record_types") or {}
        for name in ("SourceRecord", "EvidenceRecord", "AnswerGrounding"):
            self.assertIn(name, rt, f"schema must declare {name}")

    def test_crosswalk_present_for_each_record_type(self):
        cw = self.schema.get("field_crosswalk") or {}
        for name in ("SourceRecord", "EvidenceRecord", "AnswerGrounding"):
            self.assertIn(name, cw, f"crosswalk must cover {name}")

    def test_source_type_enum_matches_task_spec(self):
        enums = (self.schema["record_types"]["SourceRecord"]).get("enums") or {}
        self.assertEqual(
            set(enums.get("source_type") or []),
            {"manual", "law", "public_api", "official_web", "internal_review"},
        )

    def test_manual_version_invariants_present(self):
        inv = self.schema.get("manual_version_invariants") or {}
        self.assertIn("visa_issuance_manual", inv)
        self.assertIn("stay_residence_manual", inv)
        # Bumped when a new official edition is installed — the schema's own
        # note says to update these intentionally. 2026-09-01 is the 배포용 HWP
        # pair that superseded the 2026-07-31 pair.
        self.assertEqual(inv["visa_issuance_manual"]["published_or_updated_at"], "2026-09-01")
        self.assertEqual(inv["stay_residence_manual"]["published_or_updated_at"], "2026-09-01")


class RegistryConsistencyTests(unittest.TestCase):
    def test_validator_reports_no_hard_errors(self):
        errors, _warnings = validator.validate()
        self.assertEqual(errors, [], f"metadata validator found errors: {errors}")

    def test_no_hash_drift_between_registry_and_manifest(self):
        errors, _warnings = validator.validate()
        drift = [e for e in errors if "hash drift" in e]
        self.assertEqual(drift, [], f"registry/manifest hash drift: {drift}")

    def test_current_manuals_recognized(self):
        registry = _load(os.path.join(REPO_ROOT, "data", "source_registry.json"))
        by_kw = {}
        # The ministry publishes 배포용 HWP; the PDF editions are exports of it.
        # Both count as the active manual for this check.
        for src in registry["sources"]:
            if src.get("status") == "active" and src.get("type") in ("pdf_manual", "hwp_manual"):
                if "stay_manual" in src["id"]:
                    by_kw["stay"] = src
                elif "visa_manual" in src["id"]:
                    by_kw["visa"] = src
        self.assertIn("stay", by_kw, "active stay manual must be registered")
        self.assertIn("visa", by_kw, "active visa manual must be registered")
        self.assertEqual(by_kw["stay"]["version"], "2026.9")
        self.assertEqual(by_kw["stay"]["source_date"], "2026-09-01")
        self.assertEqual(by_kw["visa"]["version"], "2026.9")
        self.assertEqual(by_kw["visa"]["source_date"], "2026-09-01")


class AnswerGroundingFieldTests(unittest.TestCase):
    """AnswerGrounding is computed at runtime on AskResponse. Verify the
    crosswalk targets actually exist as declared fields (static check, so no
    fastapi import is required)."""

    def setUp(self):
        with open(BACKEND_PATH, encoding="utf-8") as fh:
            self.backend_src = fh.read()
        m = re.search(r"class AskResponse\(BaseModel\):(.*?)\nclass ", self.backend_src, re.DOTALL)
        self.assertIsNotNone(m, "AskResponse class block not found")
        self.ask_block = m.group(1)

    def test_grounding_lineage_fields_declared(self):
        # Targets named in data/schemas/source_grounding_schema.json ->
        # field_crosswalk.AnswerGrounding. If any is renamed/removed, the audit's
        # per-answer lineage mapping is stale and this fails on purpose.
        for field in (
            "grounding_used",
            "grounding_sources",
            "law_sources",
            "law_grounding_status",
            "citation_verification",
            "requires_official_confirmation",
            "source_confidence_level",
            "answer_quality_mode",
            "missing_direct_authority",
            "grounded_answer_limited",
        ):
            self.assertRegex(
                self.ask_block,
                rf"\n\s*{re.escape(field)}\s*[:=]",
                f"AskResponse must declare '{field}' (AnswerGrounding crosswalk target)",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
