"""Regression coverage for user-facing scenario/sub-code procedure variants."""
from __future__ import annotations

import copy
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
SCRIPTS_DIR = REPO_ROOT / "scripts"

for path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from check_required_documents_coverage import validate_procedure_variants  # noqa: E402

SEEDS = {
    ("D-9", "statusChange"): "d-9-1-status-change",
    ("E-9", "workplaceChange"): "e-9-3-agriculture-workplace-addition",
    ("F-1", "statusChange"): "f-1-13-status-change",
}

EXPANSION_VARIANTS = {
    ("D-4", "statusChange"): {
        "d-4-1-7-language-training-status-change",
        "d-4-2-graduate-training-status-change",
        "d-4-3-school-student-status-change",
    },
    ("D-8", "statusChange"): {
        "d-8-1-corporate-investment-status-change",
        "d-8-2-venture-investment-status-change",
        "d-8-3-individual-enterprise-status-change",
        "d-8-4-tech-startup-status-change",
    },
    ("D-9", "statusChange"): {
        "d-9-equipment-specialist-status-change",
        "d-9-foreign-sole-proprietor-status-change",
    },
    ("E-4", "statusChange"): {"e-4-d2-d10-status-change"},
    ("E-4", "workplaceChange"): {"e-4-registered-workplace-change"},
    ("E-5", "statusChange"): {"e-5-d2-d10-status-change"},
    ("E-5", "workplaceChange"): {"e-5-registered-workplace-change"},
    ("E-6", "activitiesOutsideStatus"): {"e-6-broadcast-film-model-activities-outside-status"},
    ("E-6", "statusChange"): {"e-6-d2-d10-status-change"},
    ("E-6", "workplaceChange"): {
        "e-6-1-3-workplace-change",
        "e-6-2-employer-workplace-change",
    },
    ("E-9", "workplaceChange"): {"e-9-standard-workplace-change"},
    ("F-1", "statusGrant"): {
        "f-1-employment-parent-born-child-status-grant",
        "f-1-refugee-born-child-status-grant",
    },
    ("F-1", "statusChange"): {
        "f-1-6-marriage-cleanup-status-change",
        "f-1-nationality-procedure-status-change",
        "f-1-16-refugee-family-status-change",
        "f-1-52-prior-marriage-child-status-change",
    },
}


def _client():
    for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
        os.environ.pop(key, None)
    from fastapi.testclient import TestClient
    import paradiso_backend

    paradiso_backend._reset_visas_cache_for_tests()
    return TestClient(paradiso_backend.app)


def _records():
    return {record.get("code"): record for record in _client().get("/api/visas").json()["data"]}


def _good_record():
    return {
        "code": "TEST",
        "procedures": {
            "statusChange": {
                "variants": [
                    {
                        "id": "test-status-change",
                        "labelKo": "테스트 체류자격 변경",
                        "requiredDocs": {
                            "commonDocs": [],
                            "requiredDocs": ["신청서"],
                            "additionalDocs": [],
                            "conditionalDocs": [],
                        },
                        "manualRefs": [
                            {
                                "manualName": "체류민원",
                                "manualVersion": "2026.5",
                                "pageRange": "p. 1",
                                "confidence": "manual_extracted_needs_review",
                                "needsManualReview": True,
                            }
                        ],
                    }
                ]
            }
        },
    }


class ScenarioProcedureVariantApiTests(unittest.TestCase):
    def test_api_preserves_seed_variants(self):
        records = _records()
        for (code, procedure_key), variant_id in SEEDS.items():
            procedure = records[code]["procedures"][procedure_key]
            self.assertTrue(procedure["available"])
            self.assertEqual(procedure["requiredDocs"]["requiredDocs"], [])
            variants = {variant["id"]: variant for variant in procedure["variants"]}
            self.assertIn(variant_id, variants)
            self.assertTrue(variants[variant_id]["requiredDocs"]["requiredDocs"])
            self.assertTrue(variants[variant_id]["manualRefs"][0]["needsManualReview"])

    def test_api_preserves_expansion_variants(self):
        records = _records()
        exposed_count = 0
        for (code, procedure_key), expected_ids in EXPANSION_VARIANTS.items():
            procedure = records[code]["procedures"][procedure_key]
            self.assertTrue(procedure["available"])
            variants = {variant["id"]: variant for variant in procedure["variants"]}
            self.assertTrue(expected_ids.issubset(variants))
            for variant_id in expected_ids:
                variant = variants[variant_id]
                groups = variant["requiredDocs"]
                self.assertTrue(any(groups[group] for group in groups), variant_id)
                self.assertTrue(variant["manualRefs"], variant_id)
                for manual_ref in variant["manualRefs"]:
                    self.assertEqual(manual_ref["sourceFile"], "docs/source-manuals/2026-05/stay_manual_2026_05.pdf")
                    self.assertTrue(manual_ref["needsManualReview"])
                    self.assertIsNot(manual_ref.get("verified"), True)
                exposed_count += 1
        self.assertEqual(exposed_count, 24)

    def test_parent_level_procedure_checklist_still_exposed(self):
        records = _records()
        d2_registration = records["D-2"]["procedures"]["registration"]
        self.assertTrue(d2_registration["requiredDocs"]["requiredDocs"])
        self.assertNotIn("variants", d2_registration)

    def test_reentry_coverage_from_pr_232_still_exposed(self):
        records = _records()
        d9_reentry = records["D-9"]["procedures"]["reentry"]
        self.assertEqual(
            d9_reentry["requiredDocs"]["requiredDocs"],
            ["신청서(별지 34호서식)", "여권 원본", "외국인등록증", "수수료"],
        )


class ScenarioProcedureVariantFrontendTests(unittest.TestCase):
    def test_variants_render_before_generic_fallback_when_parent_docs_empty(self):
        html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("variants: normalizeProcedureVariants(raw?.variants)", html)
        self.assertIn("docsHtml || variantsHtml || reviewFallback", html)
        self.assertIn("세부 자격 또는 신청 사유에 따라 제출서류가 달라질 수 있습니다.", html)
        self.assertIn('data-procedure-variant="${escapeHtml(variant.id)}"', html)


class ScenarioProcedureVariantValidationTests(unittest.TestCase):
    def test_seed_variants_pass_validation(self):
        import json

        records = json.loads((REPO_ROOT / "visa_data.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_procedure_variants(records), [])

    def test_validator_rejects_missing_id(self):
        record = _good_record()
        del record["procedures"]["statusChange"]["variants"][0]["id"]
        self.assertTrue(any("missing/invalid id" in error for error in validate_procedure_variants([record])))

    def test_validator_rejects_missing_label(self):
        record = _good_record()
        del record["procedures"]["statusChange"]["variants"][0]["labelKo"]
        self.assertTrue(any("missing labelKo or label" in error for error in validate_procedure_variants([record])))

    def test_validator_rejects_malformed_required_docs_shape(self):
        record = _good_record()
        record["procedures"]["statusChange"]["variants"][0]["requiredDocs"] = []
        self.assertTrue(any("requiredDocs: must be an object" in error for error in validate_procedure_variants([record])))

    def test_validator_rejects_empty_available_variant(self):
        record = _good_record()
        record["procedures"]["statusChange"]["variants"][0]["requiredDocs"]["requiredDocs"] = []
        self.assertTrue(any("must not be empty" in error for error in validate_procedure_variants([record])))

    def test_validator_allows_empty_explicitly_unavailable_variant(self):
        record = _good_record()
        variant = record["procedures"]["statusChange"]["variants"][0]
        variant["requiredDocs"]["requiredDocs"] = []
        variant["available"] = False
        self.assertEqual(validate_procedure_variants([record]), [])

    def test_validator_rejects_missing_manual_refs(self):
        record = copy.deepcopy(_good_record())
        del record["procedures"]["statusChange"]["variants"][0]["manualRefs"]
        self.assertTrue(any("must include manualRefs" in error for error in validate_procedure_variants([record])))


class ScenarioProcedureVariantSyncTests(unittest.TestCase):
    def test_sync_check_remains_clean(self):
        result = subprocess.run(
            [sys.executable, "scripts/sync_visa_data.py", "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_population_check_remains_clean(self):
        result = subprocess.run(
            [sys.executable, "scripts/populate_scenario_procedure_variants_2026_05.py", "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
