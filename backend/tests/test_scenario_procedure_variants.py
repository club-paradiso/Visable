"""Regression coverage for user-facing scenario/sub-code procedure variants."""
from __future__ import annotations

import copy
import json
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_pack_support import load_packs, localized, pack_blobs  # noqa: E402
from check_required_documents_coverage import validate_procedure_variants  # noqa: E402

# Localized scenario/checklist copy now lives in external per-locale JSON packs
# (data/i18n/*.json); supported display locales are ko, en, zh-CN (zh-Hant aliases
# to zh-CN), so Simplified Chinese is validated against the zh-CN pack.

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
        blobs = pack_blobs()
        # Wiring stays inline in index.html...
        self.assertIn("variants: normalizeProcedureVariants(raw?.variants)", html)
        self.assertIn("selected_procedure_key: currentAiSelectedProcedureKey", html)
        self.assertIn("selected_procedure_variant_id: currentAiSelectedProcedureVariantId", html)
        self.assertIn('title.closest(".procedure-panel, .procedure-variant-list, .doc-group-grid, .docs-section")', html)
        self.assertIn('data-procedure-variant="${escapeHtml(variant.id)}"', html)
        self.assertIn("procedures: visa.procedures || null", html)
        # ...while the localized selector/handoff copy lives in the locale packs.
        self.assertIn("내 상황에 맞는 시나리오 선택", blobs["ko"])
        self.assertIn("세부 자격·사유에 따라 제출서류가 달라질 수 있습니다. 아래에서 가장 가까운 상황을 선택해 확인하세요.", blobs["ko"])
        self.assertIn("이 시나리오로 AI에게 질문하기", blobs["ko"])
        self.assertIn("시나리오별 서류 근거", blobs["ko"])

    def test_multilingual_selector_source_panel_and_handoff_copy_is_present(self):
        html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        blobs = pack_blobs()
        # Selector + handoff + source-panel copy now lives in the locale packs.
        self.assertIn("Choose the scenario closest to your situation", blobs["en"])
        self.assertIn("选择最符合您情况的情形", blobs["zh-CN"])
        self.assertIn("Ask AI about this scenario", blobs["en"])
        self.assertIn("就此情形询问 AI", blobs["zh-CN"])
        self.assertIn("Official document names are shown in Korean to match the immigration manual.", blobs["en"])
        self.assertIn("为与出入境手册一致，正式材料名称以韩文显示。", blobs["zh-CN"])
        self.assertIn("행정 매뉴얼 근거", blobs["ko"])
        self.assertIn("Administrative manual source", blobs["en"])
        self.assertIn("行政手册依据", blobs["zh-CN"])
        self.assertIn("Scenario-specific document source", blobs["en"])
        self.assertIn("分情形材料依据", blobs["zh-CN"])
        self.assertIn("For {visaCode}, based on this selected scenario ({label}), explain the required documents and key cautions. Keep official document names in Korean where relevant.", blobs["en"])
        self.assertIn("请根据所选情形（{label}）说明 {visaCode} 所需材料和注意事项。必要时请保留韩文正式材料名称。", blobs["zh-CN"])
        # Wiring stays inline in index.html.
        self.assertIn("lang: currentLanguage", html)
        self.assertIn("selected_procedure_key: currentAiSelectedProcedureKey", html)
        self.assertIn("selected_procedure_variant_id: currentAiSelectedProcedureVariantId", html)
        self.assertIn("getProcedureLabelByKey(String(src.procedure_key)", html)
        self.assertIn("--lang-gp-source-supported", html)
        self.assertIn("--lang-gp-needs-review", html)


class SelectedScenarioActionChecklistFrontendTests(unittest.TestCase):
    """Frontend coverage for the selected-scenario action checklist (PR #245)."""

    @classmethod
    def setUpClass(cls):
        cls.html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        cls.packs = load_packs()
        cls.blobs = pack_blobs()

    def test_checklist_section_label_present_in_all_target_languages(self):
        self.assertIn("선택한 시나리오 준비 체크리스트", self.blobs["ko"])
        self.assertIn("Preparation checklist for the selected scenario", self.blobs["en"])
        self.assertIn("所选情形准备清单", self.blobs["zh-CN"])

    def test_copy_checklist_labels_present_in_all_target_languages(self):
        self.assertIn("체크리스트 복사", self.blobs["ko"])
        self.assertIn("Copy checklist", self.blobs["en"])
        self.assertIn("复制清单", self.blobs["zh-CN"])

    def test_print_view_labels_present_in_all_target_languages(self):
        self.assertIn("인쇄용 보기", self.blobs["ko"])
        self.assertIn("Print view", self.blobs["en"])
        self.assertIn("打印视图", self.blobs["zh-CN"])

    def test_reset_check_labels_present_in_all_target_languages(self):
        self.assertIn("체크 초기화", self.blobs["ko"])
        self.assertIn("Reset checks", self.blobs["en"])
        self.assertIn("重置勾选", self.blobs["zh-CN"])

    def test_confirmation_guidance_copy_present_in_all_target_languages(self):
        self.assertIn(
            "제출 전 HiKorea, 1345 또는 관할 출입국·외국인관서에서 실제 적용 여부와 추가서류를 확인하세요.",
            self.blobs["ko"],
        )
        self.assertIn(
            "Before submitting, confirm applicability and any additional documents with HiKorea, 1345, or the competent immigration office.",
            self.blobs["en"],
        )
        self.assertIn(
            "提交前，请向 HiKorea、1345 或管辖出入境外国人机构确认实际适用与追加材料。",
            self.blobs["zh-CN"],
        )

    def test_safety_note_present_and_does_not_imply_approval(self):
        self.assertIn(
            "이 체크리스트는 개인 준비용 도구이며, 항목을 체크해도 접수나 허가가 보장되지 않습니다.",
            self.blobs["ko"],
        )
        self.assertIn(
            "This checklist is a personal preparation aid only. Checking items does not guarantee acceptance or approval.",
            self.blobs["en"],
        )

    def test_secondary_ai_checklist_prompt_present_in_all_target_languages(self):
        # Button labels (localized in every supported locale).
        self.assertIn("체크리스트 기준으로 누락 가능성 물어보기", self.blobs["ko"])
        self.assertIn("Ask AI what might be missing from this checklist", self.blobs["en"])
        self.assertIn("询问 AI 这份清单可能缺少什么", self.blobs["zh-CN"])
        # Prompt template (cautious; must not imply final sufficiency).
        self.assertIn(
            "For {visaCode}, based on the selected scenario ({label}), what documents might be missing from this preparation checklist",
            localized(self.packs, "en", "scenarioChecklistMissingPrompt"),
        )
        self.assertNotIn("guarantee", localized(self.packs, "en", "scenarioChecklistMissingPrompt"))
        # Wired through the existing handoff with the checklist prompt key.
        self.assertIn("scenarioChecklistMissingPrompt", self.html)
        self.assertIn(
            "'ask-checklist-missing': () => openAiModal(actionBtn.dataset.visaCode, actionBtn.dataset.procedureKey, actionBtn.dataset.variantId, actionBtn.dataset.variantLabel, 'scenarioChecklistMissingPrompt')",
            self.html,
        )

    def test_localstorage_is_scoped_to_visa_procedure_variant_group_item(self):
        self.assertIn("const SCENARIO_CHECKLIST_STORAGE_PREFIX = 'paradiso:scenario-checklist:'", self.html)
        # Scope prefix is built from visa/status code, procedure key and variant id.
        self.assertIn(
            "[visaCode, procedureKey, variantId].map(part => encodeURIComponent(String(part || ''))).join(':')",
            self.html,
        )
        # Item key is further scoped by document group and a stable item hash.
        self.assertIn(
            "scenarioChecklistScopePrefix(visaCode, procedureKey, variantId) + group + ':' + hashScenarioChecklistItem(itemText)",
            self.html,
        )
        # Each rendered checkbox carries its own scoped storage key.
        self.assertIn('data-scenario-checklist-item data-storage-key="${escapeHtml(storageKey)}"', self.html)
        # State is persisted locally on change, not posted anywhere.
        self.assertIn("function persistScenarioChecklistItem(checkbox)", self.html)
        self.assertIn("if (checklistItem) persistScenarioChecklistItem(checklistItem);", self.html)

    def test_checklist_does_not_send_checkbox_state_to_api_ask(self):
        # Isolate the /api/ask request body and assert it carries no checklist
        # / checkbox state of any kind.
        start = self.html.index("await fetch(`${API_BASE}/api/ask`")
        end = self.html.index("signal: currentAiController.signal", start)
        body = self.html[start:end]
        for forbidden in (
            "checklist",
            "checkbox",
            "data-storage-key",
            "scenarioChecklist",
            "checkedItems",
            "checkedState",
        ):
            self.assertNotIn(forbidden, body, f"/api/ask body unexpectedly references {forbidden!r}")

    def test_selected_ai_payload_still_includes_required_fields(self):
        start = self.html.index("await fetch(`${API_BASE}/api/ask`")
        end = self.html.index("signal: currentAiController.signal", start)
        body = self.html[start:end]
        self.assertIn("lang: currentLanguage", body)
        self.assertIn("visa_data:", body)
        self.assertIn("selected_procedure_key: currentAiSelectedProcedureKey", body)
        self.assertIn("selected_procedure_variant_id: currentAiSelectedProcedureVariantId", body)

    def test_source_panel_scenario_wording_unchanged(self):
        self.assertIn("시나리오별 서류 근거", self.blobs["ko"])
        self.assertIn("선택한 시나리오 기준", self.blobs["ko"])
        self.assertIn("Scenario-specific document source", self.blobs["en"])
        self.assertIn("Based on selected scenario", self.blobs["en"])

    def test_official_korean_document_name_note_remains_in_non_korean_modes(self):
        self.assertIn("officialDocumentNamesKoNote", self.html)
        self.assertIn("Official document names are shown in Korean to match the immigration manual.", self.blobs["en"])
        self.assertIn("为与出入境手册一致，正式材料名称以韩文显示。", self.blobs["zh-CN"])
        self.assertIn(
            "currentLanguage === 'ko' || (!docsHtml && !variantsHtml) ? '' : `<p class=\"official-korean-terms-note\">",
            self.html,
        )

    def test_checklist_renders_grouped_items_with_accessible_labels(self):
        self.assertIn("function renderScenarioChecklist(visaCode, procedureKey, variant)", self.html)
        self.assertIn("renderScenarioChecklist(visaCode, procedureKey, variant)", self.html)
        # Grouped by the four localized document groups via existing labels.
        self.assertIn("{ key: 'commonDocs', labelIndex: 0", self.html)
        self.assertIn("{ key: 'conditionalDocs', labelIndex: 3", self.html)
        self.assertIn("txAt('docGroupLabels', group.labelIndex, group.fallback)", self.html)
        # Each checkbox sits inside a <label> (usable label) and is keyboard focusable.
        self.assertIn('<label class="scenario-checklist-label">', self.html)
        self.assertIn('class="scenario-checklist-checkbox"', self.html)
        # Checked state is reflected without relying on colour alone.
        self.assertIn(".scenario-checklist-itemtext { color: var(--t3); text-decoration: line-through; }", self.html)

    def test_clipboard_and_print_resilience_paths_present(self):
        # Clipboard fallback + localized failure message.
        self.assertIn("async function scenarioChecklistCopyText(text)", self.html)
        self.assertIn("scenarioChecklistCopyFailed", self.html)
        self.assertIn("document.execCommand && document.execCommand('copy')", self.html)
        # Print uses a print-friendly host + window.print(), no heavy dependency.
        self.assertIn("function printScenarioChecklist(button)", self.html)
        self.assertIn("body.printing-scenario-checklist", self.html)
        self.assertIn("window.print()", self.html)

    def test_cloned_drawer_checkboxes_rehydrate_from_storage(self):
        # openVisaDrawer() clones the rendered result card, so cloned checklist
        # checkboxes carry render-time markup that can be stale vs localStorage.
        # They must be re-hydrated from storage (the source of truth) on open,
        # and co-mounted checkboxes (source card + drawer clone) kept in sync.
        self.assertIn("function hydrateScenarioChecklistState(container)", self.html)
        self.assertIn("hydrateScenarioChecklistState(clone);", self.html)
        self.assertIn("function syncScenarioChecklistCheckboxes(key, checked, origin)", self.html)
        self.assertIn("syncScenarioChecklistCheckboxes(key, checkbox.checked, checkbox);", self.html)
        # Reset also propagates to any co-mounted copy of the same item.
        self.assertIn("syncScenarioChecklistCheckboxes(key, false, cb);", self.html)


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

    def test_outside_status_mapping_and_foreigner_registration_detector_are_ready(self):
        mod = _module()
        block = mod._build_procedure_variant_context_block(
            _record("E-6"),
            "activities_outside_status",
            user_text="E-6 체류자격외활동 서류는?",
        )
        self.assertIn("e-6-broadcast-film-model-activities-outside-status", block)
        self.assertEqual(mod._detect_task_type("D-2 외국인등록 신청 서류는?"), "foreigner_registration")

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
        self.assertEqual(registration["task_type_detected"], "foreigner_registration")
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


class SelectedProcedureVariantHandoffTests(unittest.TestCase):
    """Explicit frontend scenario selections narrow needs-review AI context."""

    def _assert_selected_helper_narrows(self, code, procedure_key, variant_id):
        mod = _module()
        record = _record(code)
        kwargs = {
            "user_text": f"{code} 선택한 시나리오 기준 서류 알려줘",
            "selected_procedure_key": procedure_key,
            "selected_procedure_variant_id": variant_id,
        }
        sources = mod._procedure_variant_context_sources(record, None, None, **kwargs)
        block = mod._build_procedure_variant_context_block(record, None, None, **kwargs)
        self.assertEqual([source["variant_id"] for source in sources], [variant_id])
        self.assertTrue(all(source["procedure_key"] == procedure_key for source in sources))
        self.assertTrue(all(source["needs_manual_review"] is True for source in sources))
        self.assertIn(variant_id, block)
        for source in sources:
            self.assertEqual(set(source), SAFE_VARIANT_FIELDS)

    def test_selected_f6_variant_narrows_context_to_only_selected_variant(self):
        self._assert_selected_helper_narrows(
            "F-6", "statusChange", "f-6-3-marriage-terminated-status-change"
        )

    def test_selected_g1_variant_narrows_context_to_only_selected_variant(self):
        self._assert_selected_helper_narrows(
            "G-1", "statusChange", "g-1-10-medical-patient-status-change"
        )

    def test_selected_f2_variant_narrows_context_to_only_selected_variant(self):
        self._assert_selected_helper_narrows(
            "F-2", "statusChange", "f-2-2-national-minor-child-status-change"
        )

    def test_invalid_selected_variant_id_does_not_crash_or_leak_raw_metadata(self):
        client = _client()
        resp = client.post("/api/ask", json={
            "question": "G-1 선택한 시나리오 기준 서류 알려줘",
            "visa_data": _record("G-1"),
            "selected_procedure_key": "statusChange",
            "selected_procedure_variant_id": "missing-variant-id",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertFalse(detail["procedure_variant_context_used"])
        self.assertEqual(detail["procedure_variant_context_sources"], [])
        self.assertFalse(detail["grounding_used"])
        raw = json.dumps(detail, ensure_ascii=False)
        for forbidden in ("requiredDocs", "manualRefs", '"documents"', '"raw"', '"visa_data"'):
            self.assertNotIn(forbidden, raw)

    def test_selected_variant_context_never_sets_grounding_used(self):
        client = _client()
        resp = client.post("/api/ask", json={
            "question": "F-6 혼인단절자(F-6-3) 체류자격 변경허가 기준으로 필요한 서류와 주의사항 알려줘",
            "visa_data": _record("F-6"),
            "selected_procedure_key": "statusChange",
            "selected_procedure_variant_id": "f-6-3-marriage-terminated-status-change",
        })
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertFalse(detail["grounding_used"])
        self.assertEqual(detail["grounding_sources"], [])
        self.assertTrue(detail["procedure_variant_context_used"])
        self.assertEqual(
            [source["variant_id"] for source in detail["procedure_variant_context_sources"]],
            ["f-6-3-marriage-terminated-status-change"],
        )

    def test_generic_questions_still_do_not_force_variants_without_selection(self):
        mod = _module()
        cases = [
            ("E-7", "Can I work in Korea with my current status?"),
            ("F-1", "가족 관련 절차 알려줘"),
            ("F-2", "F-2 체류 관련 주의사항 알려줘"),
        ]
        for code, question in cases:
            with self.subTest(code=code):
                task = mod._detect_task_type(question)
                self.assertEqual(
                    mod._procedure_variant_context_sources(
                        _record(code), task, None, user_text=question
                    ),
                    [],
                )

    def test_existing_no_selection_variant_routing_still_works(self):
        mod = _module()
        question = "G-1 체류자격 변경 서류 알려줘"
        task = mod._detect_task_type(question)
        sources = mod._procedure_variant_context_sources(
            _record("G-1"), task, None, user_text=question
        )
        self.assertEqual(len(sources), 3)
        self.assertTrue(all(source["procedure_key"] == "statusChange" for source in sources))

    def test_selected_procedure_key_alone_prefers_variants_under_that_key(self):
        mod = _module()
        sources = mod._procedure_variant_context_sources(
            _record("F-3"),
            None,
            None,
            user_text="F-3 관련 서류 알려줘",
            selected_procedure_key="statusGrant",
        )
        self.assertEqual(
            [source["variant_id"] for source in sources],
            ["f-3-born-child-status-grant"],
        )


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


HARD_CASE_VARIANTS = {
    ("F-6", "statusChange"): {
        "f-6-2-child-rearing-status-change",
        "f-6-3-marriage-terminated-status-change",
    },
    ("G-1", "statusChange"): {
        "g-1-1-industrial-accident-status-change",
        "g-1-2-illness-treatment-status-change",
        "g-1-3-litigation-status-change",
        "g-1-4-wage-claim-status-change",
        "g-1-5-6-refugee-humanitarian-status-change",
        "g-1-9-pregnancy-status-change",
        "g-1-10-medical-patient-status-change",
        "g-1-11-rights-protection-status-change",
    },
    ("F-2", "statusChange"): {
        "f-2-2-national-minor-child-status-change",
        "f-2-permanent-resident-family-status-change",
    },
}


class HardCaseScenarioVariantTests(unittest.TestCase):
    """Coverage for the hard-case (F-6 / G-1 / F-2) scenario procedure variants."""

    def test_hard_case_variants_exposed_through_api(self):
        records = _records()
        exposed = 0
        for (code, procedure_key), expected_ids in HARD_CASE_VARIANTS.items():
            self.assertIn(code, records, code)
            procedure = records[code]["procedures"][procedure_key]
            self.assertTrue(procedure["available"], f"{code}.{procedure_key}")
            # Parent-level checklist must stay empty — variants are scenario-scoped.
            self.assertEqual(procedure["requiredDocs"]["requiredDocs"], [], f"{code}.{procedure_key}")
            variants = {variant["id"]: variant for variant in procedure["variants"]}
            self.assertTrue(expected_ids.issubset(variants), f"{code}.{procedure_key}: {expected_ids - set(variants)}")
            exposed += len(expected_ids)
        self.assertEqual(exposed, 12)

    def test_hard_case_variants_have_docs_refs_and_needs_review(self):
        records = _records()
        for (code, procedure_key), expected_ids in HARD_CASE_VARIANTS.items():
            procedure = records[code]["procedures"][procedure_key]
            variants = {variant["id"]: variant for variant in procedure["variants"]}
            for variant_id in expected_ids:
                variant = variants[variant_id]
                groups = variant["requiredDocs"]
                # Non-empty grouped requiredDocs (at least one populated group).
                self.assertTrue(any(groups[group] for group in groups), variant_id)
                # requiredDocs.requiredDocs specifically carries the scenario list.
                self.assertTrue(groups["requiredDocs"], variant_id)
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

    def test_hard_case_f6_preserves_existing_statuschange_shell(self):
        # The pre-existing F-6 statusChange parent record must be preserved,
        # not overwritten, when variants are layered on.
        records = _records()
        f6 = records["F-6"]["procedures"]["statusChange"]
        self.assertIn("매뉴얼 확인 필요", json.dumps(f6, ensure_ascii=False))
        self.assertEqual(f6["requiredDocs"]["requiredDocs"], [])

    def test_prior_batch_variants_unchanged(self):
        records = _records()
        for table in (SEEDS,):
            for (code, procedure_key), variant_id in table.items():
                variants = {v["id"] for v in records[code]["procedures"][procedure_key]["variants"]}
                self.assertIn(variant_id, variants)
        for table in (EXPANSION_VARIANTS, BATCH2_VARIANTS):
            for (code, procedure_key), expected_ids in table.items():
                variants = {v["id"] for v in records[code]["procedures"][procedure_key]["variants"]}
                self.assertTrue(expected_ids.issubset(variants), f"{code}.{procedure_key}")

    def test_hard_case_population_check_remains_clean(self):
        result = subprocess.run(
            [sys.executable, "scripts/populate_hard_case_scenario_procedure_variants_2026_05.py", "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_smoke_discovers_hard_case_routable_targets(self):
        records = json.loads((REPO_ROOT / "visa_data.json").read_text(encoding="utf-8"))
        routable = {"statusChange", "workplaceChange", "activitiesOutsideStatus", "statusGrant"}
        discovered = set()
        for record in records:
            procedures = record.get("procedures") or {}
            for procedure_key, procedure in procedures.items():
                if procedure_key in routable and (procedure.get("variants") or []):
                    discovered.add((record.get("code"), procedure_key))
        for key in HARD_CASE_VARIANTS:
            self.assertIn(key, discovered, key)

    def test_hard_case_status_change_routes_only_on_matching_wording(self):
        mod = _module()
        for code in ("F-6", "G-1", "F-2"):
            record = _record(code)
            # Matching change-of-status wording surfaces needs-review variants.
            match_q = f"{code} 체류자격 변경 서류 알려줘"
            task = mod._detect_task_type(match_q)
            sources = mod._procedure_variant_context_sources(record, task, None, user_text=match_q)
            self.assertTrue(sources, code)
            self.assertTrue(all(s["procedure_key"] == "statusChange" for s in sources), code)
            self.assertTrue(all(s["needs_manual_review"] is True for s in sources), code)
            self.assertLessEqual(set().union(*[set(s) for s in sources]), SAFE_VARIANT_FIELDS, code)
            # Deterministic grounding is never asserted for these.
            top, sub = mod._detect_visa_codes(code, record, match_q)
            self.assertIsNone(mod._select_grounding(top, task, sub), code)
            # Generic wording must not force scenario variants.
            generic_q = f"{code} 비자 절차에서 주의할 점 알려줘"
            g_task = mod._detect_task_type(generic_q)
            self.assertEqual(
                mod._procedure_variant_context_sources(record, g_task, None, user_text=generic_q),
                [],
                code,
            )

    def test_hard_case_f6_divorce_wording_stays_conservative(self):
        # A divorce-worded F-6 question still routes to the high-risk
        # marriage/divorce path with no grounding and no auto-determination,
        # exactly as before this batch (variants surface on change wording, not
        # on the sensitive divorce path).
        mod = _module()
        q = "F-6 비자인데 이혼 후 체류 자격이 어떻게 되나요?"
        task = mod._detect_task_type(q)
        self.assertEqual(task, "marriage_divorce_status_change")
        self.assertEqual(mod._risk_level_for_task(task), "high")
        top, sub = mod._detect_visa_codes("F-6", _record("F-6"), q)
        self.assertIsNone(mod._select_grounding(top, task, sub))
        self.assertEqual(
            mod._procedure_variant_context_sources(_record("F-6"), task, sub, user_text=q),
            [],
        )


SAFE_VARIANT_FIELDS = {
    "visa_code", "procedure_key", "variant_id", "label", "status_code",
    "page_range", "manual_name", "manual_version", "needs_manual_review",
}

REMAINING_COMPLEX_SUBTYPE_VARIANTS = {
    ("F-6", "extension"): {
        "f-6-1-marriage-maintenance-extension",
        "f-6-1-separated-extension",
        "f-6-1-divorce-lawsuit-extension",
        "f-6-1-spouse-missing-extension",
    },
    ("F-2", "statusChange"): {
        "f-2-7-point-based-talent-status-change",
        "f-2-7s-potential-talent-status-change",
        "f-2-8-tourism-investment-status-change",
        "f-2-12-13-14-public-interest-investment-status-change",
    },
    ("H-2", "registration"): {"h-2-existing-holder-registration"},
    ("H-2", "workplaceChange"): {"h-2-employment-start-workplace-change-report"},
    ("D-10", "statusChange"): {
        "d-10-1-points-status-change",
        "d-10-1-first-graduate-status-change",
        "d-10-2-tech-startup-status-change",
        "d-10-3-high-tech-intern-status-change",
    },
    ("D-10", "extension"): {
        "d-10-1-points-extension",
        "d-10-2-tech-startup-extension",
        "d-10-3-high-tech-intern-extension",
    },
    ("F-4", "statusChange"): {"f-4-overseas-korean-status-change"},
    ("F-4", "registration"): {"f-4-domestic-residence-report"},
    ("F-4", "extension"): {"f-4-overseas-korean-extension"},
}

NEW_ROUTABLE_COMPLEX_TARGETS = {
    ("D-10", "statusChange"),
    ("H-2", "workplaceChange"),
    ("F-4", "statusChange"),
}


class RemainingComplexSubtypeScenarioVariantTests(unittest.TestCase):
    """Coverage for the remaining complex-subtype scenario cards."""

    def test_variants_are_exposed_with_grouped_docs_and_needs_review_refs(self):
        records = _records()
        exposed = 0
        for (code, procedure_key), expected_ids in REMAINING_COMPLEX_SUBTYPE_VARIANTS.items():
            procedure = records[code]["procedures"][procedure_key]
            self.assertTrue(procedure["available"], f"{code}.{procedure_key}")
            variants = {variant["id"]: variant for variant in procedure["variants"]}
            self.assertTrue(expected_ids.issubset(variants), f"{code}.{procedure_key}")
            for variant_id in expected_ids:
                variant = variants[variant_id]
                groups = variant["requiredDocs"]
                self.assertTrue(any(groups[group] for group in groups), variant_id)
                self.assertTrue(groups["requiredDocs"], variant_id)
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
                    self.assertIsNot(manual_ref.get("verified"), True, variant_id)
                exposed += 1
        self.assertEqual(exposed, 20)

    def test_population_check_remains_clean(self):
        result = subprocess.run(
            [sys.executable, "scripts/populate_remaining_complex_subtype_scenario_variants_2026_05.py", "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_prior_batches_remain_present(self):
        records = _records()
        for (code, procedure_key), variant_id in SEEDS.items():
            variants = {v["id"] for v in records[code]["procedures"][procedure_key]["variants"]}
            self.assertIn(variant_id, variants)
        for table in (EXPANSION_VARIANTS, BATCH2_VARIANTS, HARD_CASE_VARIANTS):
            for (code, procedure_key), expected_ids in table.items():
                variants = {v["id"] for v in records[code]["procedures"][procedure_key]["variants"]}
                self.assertTrue(expected_ids.issubset(variants), f"{code}.{procedure_key}")

    def test_smoke_discovery_increases_by_three_routable_targets(self):
        from smoke_ai_variant_grounding import discover_targets

        records = json.loads((REPO_ROOT / "visa_data.json").read_text(encoding="utf-8"))
        targets = discover_targets(records)
        discovered = {(target["visa_code"], target["procedure_key"]) for target in targets}
        self.assertEqual(len(targets), 28)
        self.assertTrue(NEW_ROUTABLE_COMPLEX_TARGETS.issubset(discovered))

    def test_every_new_variant_is_eligible_for_explicit_selected_handoff(self):
        mod = _module()
        for (code, procedure_key), variant_ids in REMAINING_COMPLEX_SUBTYPE_VARIANTS.items():
            for variant_id in variant_ids:
                with self.subTest(code=code, procedure_key=procedure_key, variant_id=variant_id):
                    kwargs = {
                        "user_text": f"{code} 선택한 시나리오 기준 서류 알려줘",
                        "selected_procedure_key": procedure_key,
                        "selected_procedure_variant_id": variant_id,
                    }
                    sources = mod._procedure_variant_context_sources(_record(code), None, None, **kwargs)
                    block = mod._build_procedure_variant_context_block(_record(code), None, None, **kwargs)
                    self.assertEqual([source["variant_id"] for source in sources], [variant_id])
                    self.assertEqual(sources[0]["procedure_key"], procedure_key)
                    self.assertIs(sources[0]["needs_manual_review"], True)
                    self.assertEqual(set(sources[0]), SAFE_VARIANT_FIELDS)
                    self.assertIn(variant_id, block)

    def test_generic_complex_questions_do_not_force_variants_or_grounding(self):
        mod = _module()
        cases = [
            ("F-6", "F-6 국민의 배우자인데 자동 승인되나요?"),
            ("F-2", "F-2 점수제 또는 투자 거주 자격이 자동으로 되나요?"),
            ("H-2", "H-2이면 아무 사업장에서 바로 취업할 수 있나요?"),
            ("D-10", "D-10이면 인턴 활동이 자동으로 허용되나요?"),
            ("F-4", "F-4 재외동포 비자 절차 알려줘"),
        ]
        for code, question in cases:
            with self.subTest(code=code):
                task = mod._detect_task_type(question)
                top, sub = mod._detect_visa_codes(code, _record(code), question)
                self.assertIsNone(mod._select_grounding(top, task, sub))
                self.assertEqual(
                    mod._procedure_variant_context_sources(_record(code), task, sub, user_text=question),
                    [],
                )

# Table-driven scenario-family regression matrix.
#
# Each row asserts deterministic routing/safety expectations only — no live
# LLM prose. Columns:
#   id          : stable case id
#   code        : explicit visa/sub code handed to _detect_visa_codes
#   record_code : which visa_data.json record supplies visa_data (defaults to code)
#   prompt      : the user question
#   task        : expected _detect_task_type result (or None)
#   route_key   : expected _procedure_variant_key_for_task result (or None)
#   sources     : whether scenario variants should actually surface
#
# Invariants enforced for every row (in the test body):
#   - deterministic grounding is never selected (these are not grounded paths)
#   - generic wording never forces scenario variants
#   - surfaced variants are needs-review only, shape-safe, key-matched
SCENARIO_FAMILY_MATRIX = [
    # --- A. short-stay / diplomatic / temporary ---
    {"id": "a1_generic", "code": "A-1", "prompt": "A-1 비자 절차에서 주의할 점이 있나요?",
     "task": None, "route_key": None, "sources": False},
    {"id": "b1_short", "code": "B-1", "prompt": "B-1 단기 체류 관련 절차 알려줘",
     "task": None, "route_key": None, "sources": False},
    {"id": "c3_visit", "code": "C-3", "prompt": "C-3 단기방문으로 관광하려는데 주의사항이 있나요?",
     "task": None, "route_key": None, "sources": False},
    {"id": "c4_short_emp", "code": "C-4", "prompt": "C-4 단기취업 비자 절차가 궁금합니다",
     "task": None, "route_key": None, "sources": False},
    # --- B. D-series study / training / job-seeking ---
    {"id": "d2_leave", "code": "D-2", "prompt": "D-2 비자인데 휴학하면 체류는 어떻게 되나요?",
     "task": "academic_status_change", "route_key": None, "sources": False},
    {"id": "d2_parttime", "code": "D-2", "prompt": "D-2 시간제취업 허가 받을 수 있나요?",
     "task": "activities_outside_status", "route_key": "activitiesOutsideStatus", "sources": False},
    {"id": "d4_status_change", "code": "D-4", "prompt": "D-4 체류자격 변경 서류 알려줘",
     "task": "status_change", "route_key": "statusChange", "sources": True},
    {"id": "d8_status_change", "code": "D-8", "prompt": "D-8 체류자격 변경 서류 알려줘",
     "task": "status_change", "route_key": "statusChange", "sources": True},
    {"id": "d9_status_change", "code": "D-9", "prompt": "D-9 체류자격 변경 서류는?",
     "task": "status_change", "route_key": "statusChange", "sources": True},
    {"id": "d10_jobseek", "code": "D-10", "prompt": "D-10 구직비자로 E-7 취업 전환이 자동으로 되나요?",
     "task": None, "route_key": None, "sources": False},
    {"id": "d10_status_change", "code": "D-10", "prompt": "D-10 체류자격 변경 서류 알려줘",
     "task": "status_change", "route_key": "statusChange", "sources": True},
    # --- C. E-series employment ---
    {"id": "e2_workplace", "code": "E-2", "prompt": "E-2 근무처 변경 서류 알려줘",
     "task": "workplace_change", "route_key": "workplaceChange", "sources": True},
    {"id": "e6_activities", "code": "E-6", "prompt": "E-6 체류자격외활동 허가 서류 알려줘",
     "task": "activities_outside_status", "route_key": "activitiesOutsideStatus", "sources": True},
    {"id": "e7_workplace", "code": "E-7", "prompt": "E-7 근무처 변경 서류 알려줘",
     "task": "workplace_change", "route_key": "workplaceChange", "sources": True},
    {"id": "e74_workplace", "code": "E-7-4", "record_code": "E-7",
     "prompt": "E-7-4 근무처 변경 서류 알려줘",
     "task": "workplace_change", "route_key": "workplaceChange", "sources": True},
    {"id": "e8_seasonal", "code": "E-8", "prompt": "E-8 계절근로 비자 절차 알려줘",
     "task": None, "route_key": None, "sources": False},
    {"id": "e9_workplace", "code": "E-9", "prompt": "E-9 근무처 변경 서류는?",
     "task": "workplace_change", "route_key": "workplaceChange", "sources": True},
    {"id": "e10_seafarer", "code": "E-10", "prompt": "E-10 선원 취업 비자 절차 알려줘",
     "task": None, "route_key": None, "sources": False},
    # --- D. F-series family / residence / permanent residence ---
    {"id": "f1_statusgrant", "code": "F-1", "prompt": "F-1 국내출생 자녀 체류자격 부여 서류 알려줘",
     "task": "family_status_change", "route_key": "statusGrant", "sources": True},
    {"id": "f1_generic", "code": "F-1", "prompt": "F-1 가족 관련 절차 알려줘",
     "task": None, "route_key": None, "sources": False},
    {"id": "f2_residence", "code": "F-2", "prompt": "F-2 거주비자 연장 점수제 자격이 되나요?",
     "task": "extension", "route_key": None, "sources": False},
    {"id": "f3_activities", "code": "F-3", "prompt": "F-3 동반가족이 시간제취업 허가를 받을 수 있나요?",
     "task": "activities_outside_status", "route_key": "activitiesOutsideStatus", "sources": True},
    {"id": "f3_statusgrant", "code": "F-3", "prompt": "F-3 자녀 출생 체류자격 부여 서류 알려줘",
     "task": "family_status_change", "route_key": "statusGrant", "sources": True},
    {"id": "f4_overseas", "code": "F-4", "prompt": "F-4 재외동포 비자 절차 알려줘",
     "task": None, "route_key": None, "sources": False},
    {"id": "f4_status_change", "code": "F-4", "prompt": "F-4 체류자격 변경 서류 알려줘",
     "task": "status_change", "route_key": "statusChange", "sources": True},
    {"id": "f5_pr", "code": "F-5", "prompt": "F-5 영주증 재발급 신고 절차 알려줘",
     "task": None, "route_key": None, "sources": False},
    {"id": "f6_divorce", "code": "F-6", "prompt": "F-6 비자인데 이혼했어요. 체류 자격은 어떻게 되나요?",
     "task": "marriage_divorce_status_change", "route_key": None, "sources": False},
    # --- E. G-series humanitarian / refugee ---
    {"id": "g1_humanitarian", "code": "G-1", "prompt": "G-1 인도적 체류 절차 알려줘",
     "task": None, "route_key": None, "sources": False},
    {"id": "g1_work", "code": "G-1", "prompt": "G-1 비자로 일할 수 있나요?",
     "task": None, "route_key": None, "sources": False},
    # --- F. H-series working holiday / visit employment ---
    {"id": "h1_wh", "code": "H-1", "prompt": "H-1 워킹홀리데이로 한국에서 일할 수 있나요?",
     "task": None, "route_key": None, "sources": False},
    {"id": "h2_workplace", "code": "H-2", "prompt": "H-2 근무처 변경 신고 절차 알려줘",
     "task": "workplace_change", "route_key": "workplaceChange", "sources": True},
    # --- G. cross-cutting negative routing (even variant-bearing records must not route) ---
    {"id": "cross_work", "code": "E-7", "record_code": "E-7",
     "prompt": "Can I work in Korea with my current status?",
     "task": None, "route_key": None, "sources": False},
    {"id": "cross_family", "code": "F-1", "record_code": "F-1",
     "prompt": "My family situation changed. What should I do?",
     "task": None, "route_key": None, "sources": False},
    {"id": "cross_generic", "code": "E-9", "record_code": "E-9",
     "prompt": "What should I watch out for with this visa?",
     "task": None, "route_key": None, "sources": False},
]


class ScenarioFamilyRegressionMatrixTests(unittest.TestCase):
    """Deterministic A–H scenario-family routing + safety matrix."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _module()

    def _row(self, row):
        mod = self.mod
        record = _record(row.get("record_code", row["code"]))
        prompt = row["prompt"]
        top, sub = mod._detect_visa_codes(row["code"], record, prompt)
        task = mod._detect_task_type(prompt)
        route_key = mod._procedure_variant_key_for_task(task, prompt)
        grounding = mod._select_grounding(top, task, sub)
        sources = mod._procedure_variant_context_sources(record, task, sub, user_text=prompt)
        block = mod._build_procedure_variant_context_block(record, task, sub, user_text=prompt)
        return task, route_key, grounding, sources, block

    def test_scenario_family_matrix(self):
        for row in SCENARIO_FAMILY_MATRIX:
            with self.subTest(case=row["id"]):
                task, route_key, grounding, sources, block = self._row(row)
                self.assertEqual(task, row["task"], f"{row['id']}: task")
                self.assertEqual(route_key, row["route_key"], f"{row['id']}: route_key")
                # Needs-review scenario variants never imply deterministic grounding.
                self.assertIsNone(grounding, f"{row['id']}: must not select grounding")
                if row["sources"]:
                    self.assertTrue(sources, f"{row['id']}: expected scenario variants")
                    self.assertTrue(block, f"{row['id']}: expected variant block")
                    for src in sources:
                        self.assertLessEqual(set(src), SAFE_VARIANT_FIELDS, f"{row['id']}: safe fields")
                        self.assertEqual(src.get("procedure_key"), row["route_key"], row["id"])
                        self.assertIs(src.get("needs_manual_review"), True, f"{row['id']}: needs review")
                else:
                    self.assertEqual(sources, [], f"{row['id']}: must not fabricate variants")
                    self.assertEqual(block, "", f"{row['id']}: must not build variant block")

    def test_matrix_covers_all_families(self):
        families = {row["code"][0] for row in SCENARIO_FAMILY_MATRIX if row["code"][0].isalpha()}
        for fam in "ABCDEFGH":
            self.assertIn(fam, families, f"matrix must cover status family {fam}")


class HighRiskScenarioRegressionTests(unittest.TestCase):
    """Deeper assertions for F-6, G-1, D-10, E-7/E-7-4, F-2, F-3, H-2."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _module()

    def test_f6_divorce_high_risk_no_grounding_no_variant(self):
        mod = self.mod
        for sub in ("F-6-1", "F-6-3", None):
            code = sub or "F-6"
            q = f"{code} 비자인데 이혼/별거 후 자녀 양육 중입니다. 체류 자격은?"
            top, detected_sub = mod._detect_visa_codes(code, _record("F-6"), q)
            task = mod._detect_task_type(q)
            self.assertEqual(task, "marriage_divorce_status_change")
            self.assertEqual(mod._risk_level_for_task(task), "high")
            self.assertIsNone(mod._select_grounding(top, task, detected_sub))
            self.assertEqual(
                mod._procedure_variant_context_sources(_record("F-6"), task, detected_sub, user_text=q),
                [],
            )

    def test_g1_humanitarian_and_work_no_fabricated_pathway(self):
        mod = self.mod
        for q in (
            "G-1 인도적 체류 / 난민 신청 중인데 절차 알려줘",
            "G-1 비자로 일할 수 있나요? 활동 허가가 자동으로 되나요?",
        ):
            task = mod._detect_task_type(q)
            self.assertIsNone(mod._select_grounding("G-1", task, None))
            self.assertEqual(
                mod._procedure_variant_context_sources(_record("G-1"), task, None, user_text=q),
                [],
            )

    def test_d10_jobseeking_not_auto_transition(self):
        mod = self.mod
        q = "D-10 구직비자인데 E-7/E-9 취업으로 자동 전환되나요?"
        task = mod._detect_task_type(q)
        # Generic destination-status wording must not force D-10-side variants.
        self.assertEqual(
            mod._procedure_variant_context_sources(_record("D-10"), task, None, user_text=q),
            [],
        )
        self.assertIsNone(mod._select_grounding("D-10", task, None))

    def test_e7_and_e74_workplace_change_needs_review_only(self):
        mod = self.mod
        record = _record("E-7")
        for code in ("E-7", "E-7-4"):
            q = f"{code} 근무처 변경 서류 알려줘 (직종/고용주/계약 정보 없음)"
            top, sub = mod._detect_visa_codes(code, record, q)
            task = mod._detect_task_type(q)
            self.assertEqual(task, "workplace_change")
            self.assertIsNone(mod._select_grounding(top, task, sub))
            sources = mod._procedure_variant_context_sources(record, task, sub, user_text=q)
            self.assertTrue(sources, code)
            for src in sources:
                self.assertEqual(src.get("procedure_key"), "workplaceChange")
                self.assertIs(src.get("needs_manual_review"), True)

    def test_f2_residence_extension_no_grounding_no_eligibility_variant(self):
        mod = self.mod
        q = "F-2 거주비자 연장하려는데 점수제/투자 자격이 되나요?"
        top, sub = mod._detect_visa_codes("F-2", _record("F-2"), q)
        task = mod._detect_task_type(q)
        self.assertEqual(task, "extension")
        # F-2 is not a deterministically grounded code, so no grounding is asserted.
        self.assertIsNone(mod._select_grounding(top, task, sub))
        self.assertEqual(
            mod._procedure_variant_context_sources(_record("F-2"), task, sub, user_text=q),
            [],
        )

    def test_f3_dependent_activities_vs_statusgrant_routing(self):
        mod = self.mod
        record = _record("F-3")
        activities_q = "F-3 동반가족 시간제취업 허가 받을 수 있나요?"
        a_task = mod._detect_task_type(activities_q)
        a_sources = mod._procedure_variant_context_sources(record, a_task, None, user_text=activities_q)
        self.assertTrue(a_sources)
        self.assertTrue(all(s.get("procedure_key") == "activitiesOutsideStatus" for s in a_sources))

        grant_q = "F-3 자녀 출생 체류자격 부여 서류 알려줘"
        g_task = mod._detect_task_type(grant_q)
        g_sources = mod._procedure_variant_context_sources(record, g_task, None, user_text=grant_q)
        self.assertTrue(g_sources)
        self.assertTrue(all(s.get("procedure_key") == "statusGrant" for s in g_sources))

        # Generic F-3 family wording must not pull child/status-grant checklists.
        generic_q = "F-3 가족 관련 절차 알려줘"
        gen_task = mod._detect_task_type(generic_q)
        self.assertEqual(
            mod._procedure_variant_context_sources(record, gen_task, None, user_text=generic_q),
            [],
        )

    def test_h2_workplace_report_stays_needs_review_and_not_f4(self):
        mod = self.mod
        q = "H-2 근무처 변경/신고 절차 알려줘"
        task = mod._detect_task_type(q)
        self.assertEqual(task, "workplace_change")
        sources = mod._procedure_variant_context_sources(_record("H-2"), task, None, user_text=q)
        self.assertEqual([source["variant_id"] for source in sources], ["h-2-employment-start-workplace-change-report"])
        self.assertTrue(all(source["procedure_key"] == "workplaceChange" for source in sources))
        self.assertTrue(all(source["needs_manual_review"] is True for source in sources))
        self.assertNotIn("F-4", json.dumps(sources, ensure_ascii=False))
        self.assertIsNone(mod._select_grounding("H-2", task, None))

    def test_multiple_variants_under_one_key_are_capped(self):
        mod = self.mod
        # F-1 statusChange holds 5 variants; selection must cap to <= 3 and stay safe.
        record = _record("F-1")
        sources = mod._procedure_variant_context_sources(
            record, "status_change", user_text="F-1 체류자격 변경 서류 알려줘"
        )
        self.assertTrue(sources)
        self.assertLessEqual(len(sources), 3)
        for src in sources:
            self.assertLessEqual(set(src), SAFE_VARIANT_FIELDS)
            self.assertIs(src.get("needs_manual_review"), True)

    def test_missing_payload_does_not_crash_or_fabricate(self):
        mod = self.mod
        for bad in (None, {}, {"code": "E-7", "procedures": "oops"}):
            task = mod._detect_task_type("Can I work? change workplace")
            sources = mod._procedure_variant_context_sources(bad, task, None, user_text="x")
            self.assertEqual(sources, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
