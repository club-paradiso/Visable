"""Regression coverage for user-facing scenario/sub-code procedure variants."""
from __future__ import annotations

import copy
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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


def _module():
    import paradiso_backend

    return paradiso_backend


def _record(code):
    import json

    records = json.loads((REPO_ROOT / "visa_data.json").read_text(encoding="utf-8"))
    return next(record for record in records if record.get("code") == code)


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
        self.assertIn("procedures: visa.procedures || null", html)


class ScenarioProcedureVariantAiContextTests(unittest.TestCase):
    def test_d9_status_change_helper_includes_only_d9_status_change_variants(self):
        mod = _module()
        block = mod._build_procedure_variant_context_block(
            _record("D-9"),
            "status_change",
            user_text="D-9 체류자격 변경 서류는?",
        )
        self.assertIn("[Manual-backed local procedure variant context — needs review]", block)
        self.assertIn("d-9-1-status-change", block)
        self.assertIn("d-9-equipment-specialist-status-change", block)
        self.assertIn("d-9-foreign-sole-proprietor-status-change", block)
        self.assertNotIn("e-9-3-agriculture-workplace-addition", block)
        self.assertIn("Do not generalize", block)
        self.assertIn("HiKorea, 1345", block)

    def test_e9_workplace_change_helper_includes_only_workplace_variants(self):
        mod = _module()
        block = mod._build_procedure_variant_context_block(
            _record("E-9"),
            "workplace_change",
            user_text="E-9 근무처 변경 서류는?",
        )
        self.assertIn("e-9-3-agriculture-workplace-addition", block)
        self.assertIn("e-9-standard-workplace-change", block)
        self.assertNotIn("d-9-1-status-change", block)

    def test_exact_sub_code_prefers_matching_variant(self):
        mod = _module()
        sources = mod._procedure_variant_context_sources(
            _record("D-8"),
            "status_change",
            "D-8-4",
            user_text="D-8-4 체류자격 변경 서류는?",
        )
        self.assertEqual(
            [source["variant_id"] for source in sources],
            ["d-8-4-tech-startup-status-change"],
        )

    def test_family_status_grant_requires_explicit_birth_or_grant_signal(self):
        mod = _module()
        vague = mod._build_procedure_variant_context_block(
            _record("F-1"),
            "family_status_change",
            user_text="가족관계 변동이 있습니다.",
        )
        birth = mod._build_procedure_variant_context_block(
            _record("F-1"),
            "family_status_change",
            user_text="국내 출생 자녀의 체류자격 부여 서류는?",
        )
        self.assertEqual(vague, "")
        self.assertIn("f-1-employment-parent-born-child-status-grant", birth)
        self.assertIn("f-1-refugee-born-child-status-grant", birth)

    def test_outside_status_mapping_is_ready_without_changing_existing_detector(self):
        mod = _module()
        block = mod._build_procedure_variant_context_block(
            _record("E-6"),
            "activities_outside_status",
            user_text="E-6 체류자격외활동 서류는?",
        )
        self.assertIn("e-6-broadcast-film-model-activities-outside-status", block)
        self.assertIsNone(mod._detect_task_type("D-2 외국인등록 신청 서류는?"))

    def test_api_reports_d9_variant_context_without_claiming_grounding(self):
        client = _client()
        resp = client.post("/api/ask", json={
            "question": "D-9 체류자격 변경 서류는?",
            "visa_data": _record("D-9"),
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertFalse(detail["grounding_used"])
        self.assertEqual(detail["grounding_sources"], [])
        self.assertTrue(detail["procedure_variant_context_used"])
        sources = detail["procedure_variant_context_sources"]
        self.assertEqual(len(sources), 3)
        safe_keys = {
            "visa_code", "procedure_key", "variant_id", "label", "status_code",
            "page_range", "manual_name", "manual_version", "needs_manual_review",
        }
        for source in sources:
            self.assertEqual(set(source), safe_keys)
            self.assertEqual(source["visa_code"], "D-9")
            self.assertEqual(source["procedure_key"], "statusChange")
            self.assertTrue(source["needs_manual_review"])
            self.assertNotIn("requiredDocs", source)
            self.assertNotIn("notes", source)

    def test_api_reports_e9_workplace_context(self):
        client = _client()
        resp = client.post("/api/ask", json={
            "question": "E-9 근무처 변경 서류는?",
            "visa_data": _record("E-9"),
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertFalse(detail["grounding_used"])
        self.assertTrue(detail["procedure_variant_context_used"])
        self.assertEqual(
            {source["variant_id"] for source in detail["procedure_variant_context_sources"]},
            {"e-9-3-agriculture-workplace-addition", "e-9-standard-workplace-change"},
        )

    def test_unrelated_question_and_parent_registration_do_not_use_variant_context(self):
        client = _client()
        unrelated = client.post("/api/ask", json={
            "question": "D-9 체류기간은 얼마나 되나요?",
            "visa_data": _record("D-9"),
        }).json()["detail"]
        registration = client.post("/api/ask", json={
            "question": "D-2 외국인등록 신청 서류는?",
            "visa_data": _record("D-2"),
        }).json()["detail"]
        self.assertFalse(unrelated["procedure_variant_context_used"])
        self.assertEqual(unrelated["procedure_variant_context_sources"], [])
        self.assertIsNone(registration["task_type_detected"])
        self.assertFalse(registration["procedure_variant_context_used"])
        self.assertEqual(registration["procedure_variant_context_sources"], [])

    def test_existing_d2_extension_grounding_remains_independent(self):
        client = _client()
        detail = client.post("/api/ask", json={
            "question": "D-2 체류기간 연장 서류는?",
            "visa_data": _record("D-2"),
        }).json()["detail"]
        self.assertTrue(detail["grounding_used"])
        self.assertFalse(detail["procedure_variant_context_used"])

    def test_variant_context_is_appended_to_provider_prompt(self):
        client = _client()
        mod = _module()
        captured = []

        async def fake_call(prompt, model=None):
            captured.append(prompt)
            return "ok"

        with (
            patch.object(mod, "OPENROUTER_API_KEY", "test-key"),
            patch.object(mod, "_call_openrouter", side_effect=fake_call),
        ):
            resp = client.post("/api/ask", json={
                "question": "D-9 체류자격 변경 서류는?",
                "visa_data": _record("D-9"),
            })
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(len(captured), 1)
        self.assertIn("[Manual-backed local procedure variant context — needs review]", captured[0])
        self.assertIn("d-9-1-status-change", captured[0])
        body = resp.json()
        self.assertFalse(body["grounding_used"])
        self.assertTrue(body["procedure_variant_context_used"])


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



class AiVariantGroundingPostMergeSmokeTests(unittest.TestCase):
    """Post-merge smoke coverage for AI scenario-variant grounding."""

    @staticmethod
    def _visa_record(code):
        import json

        records = json.loads((REPO_ROOT / "visa_data.json").read_text(encoding="utf-8"))
        for record in records:
            if record.get("code") == code:
                return record
        raise AssertionError(f"Missing visa record: {code}")

    def test_detects_activities_outside_status_signals(self):
        import paradiso_backend as backend

        self.assertEqual(
            backend._detect_task_type("E-6 체류자격외활동허가에 필요한 서류가 뭐야?"),
            "activities_outside_status",
        )
        self.assertEqual(
            backend._detect_task_type("Can I get part-time work permission as E-6?"),
            "activities_outside_status",
        )
        self.assertEqual(
            backend._procedure_variant_key_for_task(
                "activities_outside_status",
                "E-6 체류자격외활동허가",
            ),
            "activitiesOutsideStatus",
        )

    def test_e6_activities_outside_status_variant_context_is_built(self):
        import paradiso_backend as backend

        record = self._visa_record("E-6")
        block = backend._build_procedure_variant_context_block(
            record,
            "activities_outside_status",
            user_text="E-6 체류자격외활동허가 서류 알려줘",
        )
        sources = backend._procedure_variant_context_sources(
            record,
            "activities_outside_status",
            user_text="E-6 체류자격외활동허가 서류 알려줘",
        )

        self.assertIn("Manual-backed local procedure variant context", block)
        self.assertIn("activitiesOutsideStatus", block)
        self.assertIn("e-6-broadcast-film-model-activities-outside-status", block)
        self.assertTrue(sources)
        self.assertEqual(sources[0]["procedure_key"], "activitiesOutsideStatus")
        self.assertEqual(
            sources[0]["variant_id"],
            "e-6-broadcast-film-model-activities-outside-status",
        )
        self.assertTrue(sources[0]["needs_manual_review"])

    def test_f1_status_grant_routes_only_for_explicit_status_grant_question(self):
        import paradiso_backend as backend

        record = self._visa_record("F-1")

        explicit_task = backend._detect_task_type("국내출생 자녀 체류자격 부여 서류 알려줘")
        self.assertEqual(explicit_task, "family_status_change")
        self.assertEqual(
            backend._procedure_variant_key_for_task(
                explicit_task,
                "국내출생 자녀 체류자격 부여 서류 알려줘",
            ),
            "statusGrant",
        )

        block = backend._build_procedure_variant_context_block(
            record,
            explicit_task,
            user_text="국내출생 자녀 체류자격 부여 서류 알려줘",
        )
        self.assertIn("statusGrant", block)
        self.assertIn("f-1-employment-parent-born-child-status-grant", block)

        generic_task = backend._detect_task_type("가족관계 변동이 있는데 뭘 해야 해?")
        self.assertEqual(generic_task, "family_status_change")
        self.assertIsNone(
            backend._procedure_variant_key_for_task(
                generic_task,
                "가족관계 변동이 있는데 뭘 해야 해?",
            )
        )

    def test_unrelated_question_does_not_use_variant_context(self):
        import paradiso_backend as backend

        record = self._visa_record("D-9")
        block = backend._build_procedure_variant_context_block(
            record,
            None,
            user_text="한국 생활 정보 알려줘",
        )
        sources = backend._procedure_variant_context_sources(
            record,
            None,
            user_text="한국 생활 정보 알려줘",
        )

        self.assertEqual(block, "")
        self.assertEqual(sources, [])

    def test_variant_context_safe_metadata_shape(self):
        import paradiso_backend as backend

        record = self._visa_record("E-9")
        sources = backend._procedure_variant_context_sources(
            record,
            "workplace_change",
            user_text="E-9 근무처 변경 서류 알려줘",
        )

        self.assertTrue(sources)
        allowed = {
            "visa_code",
            "procedure_key",
            "variant_id",
            "label",
            "status_code",
            "page_range",
            "manual_name",
            "manual_version",
            "needs_manual_review",
        }
        for source in sources:
            self.assertLessEqual(set(source), allowed)
            self.assertEqual(source["procedure_key"], "workplaceChange")
            self.assertTrue(source["needs_manual_review"])
            self.assertNotIn("requiredDocs", source)
            self.assertNotIn("manualRefs", source)

    def test_grounding_used_semantics_are_not_changed_by_variant_context(self):
        import paradiso_backend as backend

        record = self._visa_record("D-9")
        self.assertTrue(
            backend._build_procedure_variant_context_block(
                record,
                "status_change",
                user_text="D-9 체류자격 변경 서류 알려줘",
            )
        )
        self.assertIsNone(backend._select_grounding("D-9", "status_change", None))

    def test_existing_parent_level_and_reentry_paths_still_available(self):
        records = _records()

        d2_registration = records["D-2"]["procedures"]["registration"]
        self.assertTrue(d2_registration["requiredDocs"]["requiredDocs"])

        d9_reentry = records["D-9"]["procedures"]["reentry"]
        self.assertEqual(
            d9_reentry["requiredDocs"]["requiredDocs"],
            ["신청서(별지 34호서식)", "여권 원본", "외국인등록증", "수수료"],
        )


class StatusGrantAliasRoutingHotfixTests(unittest.TestCase):
    def test_status_grant_aliases_route_to_status_grant(self):
        import paradiso_backend as backend

        examples = [
            "What documents are needed for grant of status for a child born in Korea?",
            "Which checklist applies for child status grant?",
            "출생 자녀 체류 관련 체류자격 부여 서류 알려줘",
            "국내출생 자녀 체류자격 부여 서류 알려줘",
        ]

        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(backend._detect_task_type(text), "family_status_change")
                self.assertEqual(
                    backend._procedure_variant_key_for_task("family_status_change", text),
                    "statusGrant",
                )

    def test_generic_family_change_still_does_not_route_to_status_grant(self):
        import paradiso_backend as backend

        text = "가족관계 변동이 있는데 뭘 해야 해?"
        self.assertEqual(backend._detect_task_type(text), "family_status_change")
        self.assertIsNone(
            backend._procedure_variant_key_for_task("family_status_change", text)
        )


# Batch-2 scenario variants added from the 2026-05 stay manual
# (scripts/populate_scenario_procedure_variants_batch2_2026_05.py). Every id
# here must be exposed through /api/visas, carry non-empty grouped
# requiredDocs and source manualRefs, and remain needs-review.
BATCH2_VARIANTS = {
    ("E-1", "statusChange"): {
        "e-1-d2-d10-status-change",
        "e-1-professional-spouse-status-change",
        "e-1-science-graduate-status-change",
    },
    ("E-2", "workplaceChange"): {"e-2-registered-workplace-change"},
    ("E-2", "statusChange"): {
        "e-2-registered-status-change",
        "e-2-education-office-instructor-status-change",
        "e-2-d2-d10-status-change",
    },
    ("E-3", "workplaceChange"): {"e-3-registered-workplace-change"},
    ("E-3", "statusChange"): {
        "e-3-d2-d10-status-change",
        "e-3-a3-sofa-status-change",
    },
    ("E-7", "workplaceChange"): {"e-7-registered-workplace-change"},
    ("F-3", "activitiesOutsideStatus"): {
        "f-3-language-proofreader-activities-outside-status",
        "f-3-instructor-teacher-activities-outside-status",
    },
    ("F-3", "statusChange"): {"f-3-humanitarian-status-change"},
    ("F-3", "statusGrant"): {"f-3-born-child-status-grant"},
}


class ScenarioProcedureVariantBatch2Tests(unittest.TestCase):
    """Coverage for the batch-2 scenario/sub-code procedure variants."""

    def test_batch2_variants_exposed_through_api(self):
        records = _records()
        exposed_count = 0
        for (code, procedure_key), expected_ids in BATCH2_VARIANTS.items():
            self.assertIn(code, records, code)
            procedure = records[code]["procedures"][procedure_key]
            self.assertTrue(procedure["available"], f"{code}.{procedure_key}")
            # Parent-level checklist must stay empty — variants are scenario-scoped.
            self.assertEqual(procedure["requiredDocs"]["requiredDocs"], [], f"{code}.{procedure_key}")
            variants = {variant["id"]: variant for variant in procedure["variants"]}
            self.assertTrue(expected_ids.issubset(variants), f"{code}.{procedure_key}: {expected_ids - set(variants)}")
            exposed_count += len(expected_ids)
        self.assertEqual(exposed_count, 15)

    def test_batch2_variants_have_docs_refs_and_needs_review(self):
        records = _records()
        for (code, procedure_key), expected_ids in BATCH2_VARIANTS.items():
            procedure = records[code]["procedures"][procedure_key]
            variants = {variant["id"]: variant for variant in procedure["variants"]}
            for variant_id in expected_ids:
                variant = variants[variant_id]
                groups = variant["requiredDocs"]
                # Non-empty grouped requiredDocs (at least one populated group).
                self.assertTrue(any(groups[group] for group in groups), variant_id)
                # Source manualRefs present and provably needs-review.
                self.assertTrue(variant["manualRefs"], variant_id)
                for manual_ref in variant["manualRefs"]:
                    self.assertEqual(
                        manual_ref["sourceFile"],
                        "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
                        variant_id,
                    )
                    self.assertEqual(manual_ref["manualVersion"], "2026.5", variant_id)
                    self.assertTrue(manual_ref.get("pageRange"), variant_id)
                    self.assertTrue(manual_ref["needsManualReview"], variant_id)
                    # Never source-confirmed: verified must not be true.
                    self.assertIsNot(manual_ref.get("verified"), True, variant_id)

    def test_batch1_expansion_count_unchanged(self):
        # Adding batch-2 variants must not disturb the batch-1 set.
        records = _records()
        batch1_count = 0
        for (code, procedure_key), expected_ids in EXPANSION_VARIANTS.items():
            variants = {variant["id"]: variant for variant in records[code]["procedures"][procedure_key]["variants"]}
            self.assertTrue(expected_ids.issubset(variants))
            batch1_count += len(expected_ids)
        self.assertEqual(batch1_count, 24)

    def test_batch2_population_check_remains_clean(self):
        result = subprocess.run(
            [sys.executable, "scripts/populate_scenario_procedure_variants_batch2_2026_05.py", "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_smoke_discovers_expanded_routable_targets(self):
        # The exhaustive smoke script discovers routable (visa_code, procedure_key)
        # targets from the visa catalog. Batch-2 must enlarge that discovery set.
        import json

        records = json.loads((REPO_ROOT / "visa_data.json").read_text(encoding="utf-8"))
        routable = {"statusChange", "workplaceChange", "activitiesOutsideStatus", "statusGrant"}
        discovered = set()
        for record in records:
            procedures = record.get("procedures") or {}
            for procedure_key, procedure in procedures.items():
                if procedure_key in routable and (procedure.get("variants") or []):
                    discovered.add((record.get("code"), procedure_key))
        for key in BATCH2_VARIANTS:
            self.assertIn(key, discovered, key)


if __name__ == "__main__":
    unittest.main(verbosity=2)
