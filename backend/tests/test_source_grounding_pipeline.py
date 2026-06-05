from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.source_grounding import (  # noqa: E402
    build_official_grounding_context,
    classify_query_for_grounding,
    normalize_http_source_response,
    normalize_law_source_attempts,
    normalize_manual_source_attempts,
    project_public_source_status,
    render_grounding_context_for_prompt,
    select_answer_policy,
)


class SourceGroundingPipelineTests(unittest.TestCase):
    def test_classifier_structures_query_without_final_legal_conclusion(self) -> None:
        classified = classify_query_for_grounding(
            "I am already in Korea and want to do paid freelance work while changing status. What should I check?",
            visa_code="D-10",
        )
        self.assertEqual(classified["statusCode"], "D-10")
        self.assertIn(classified["procedureType"], {
            "change_of_status",
            "activities_outside_status",
            "employment_work_activity_inquiry",
        })
        self.assertIn("freelancing", classified["actionActivity"])
        self.assertNotIn("paid_unpaid", classified["missingMaterialFacts"])
        self.assertTrue(classified["doesNotDecideFinalAnswer"])
        self.assertNotIn("finalConclusion", classified)

    def test_classifier_identifies_material_missing_facts_for_activity_question(self) -> None:
        classified = classify_query_for_grounding(
            "Can I work on my current Korean status?",
            visa_code="C-3",
        )
        self.assertEqual(classified["statusCode"], "C-3")
        self.assertIn("employer_type", classified["missingMaterialFacts"])
        self.assertIn("work_duration_or_hours", classified["missingMaterialFacts"])

    def test_parser_normalization_accepts_json_xml_and_rejects_bad_shapes_safely(self) -> None:
        valid_json = json.dumps({
            "LawSearch": {"law": [{"법령명한글": "출입국관리법", "조문내용": "체류자격 관련 조문"}]}
        }, ensure_ascii=False)
        cases = [
            (valid_json, 200, "available", "available", ""),
            ("{bad json", 200, "error", "temporarily_unavailable", "MALFORMED_JSON"),
            ("<root><law>출입국관리법 시행령</law><text>활동범위</text></root>", 200, "available", "available", ""),
            ("<html><body>service page</body></html>", 200, "error", "temporarily_unavailable", "HTML_RESPONSE"),
            ("plain service banner", 200, "error", "temporarily_unavailable", "PLAIN_TEXT_RESPONSE"),
            ("", 200, "temporarily_unavailable", "temporarily_unavailable", "EMPTY_BODY"),
            (valid_json, 503, "error", "temporarily_unavailable", "HTTP_ERROR"),
        ]
        for body, status_code, status, public_status, internal in cases:
            normalized = normalize_http_source_response(
                family="statute",
                body=body,
                http_status=status_code,
                title="source",
            )
            self.assertEqual(normalized["status"], status)
            self.assertEqual(normalized["publicStatus"], public_status)
            if internal:
                self.assertEqual(normalized["internalCode"], internal)

    def test_normalized_sources_feed_grounding_context_and_public_projection(self) -> None:
        manual = normalize_manual_source_attempts(
            [{
                "source_title": "외국인체류 안내매뉴얼",
                "source_date": "2026-05-21",
                "section": "체류자격 변경",
                "excerpt": "체류자격 변경 신청 시 절차별 안내를 확인한다.",
            }],
            manual_present=True,
        )
        law = normalize_law_source_attempts(
            law_sources=[{
                "source_type": "law",
                "law_name": "출입국관리법",
                "article": "제20조",
                "summary": "체류자격 외 활동은 허가가 필요할 수 있다.",
                "reference": "001386",
            }],
            source_family_statuses={"statute": "results_found", "enforcement_rule": "no_results"},
            parser_status_by_family={"enforcement_rule": "parsed_json"},
            law_error_type_by_family={"enforcement_rule": "LAW_API_NO_RESULTS"},
        )
        classified = classify_query_for_grounding("Can I do paid work on my status?", visa_code="D-4")
        context = build_official_grounding_context(
            query_classification=classified,
            normalized_sources=[*manual, *law],
            source_plan={"source_families_planned": ["manual", "statute", "enforcement_rule"]},
        )
        prompt = render_grounding_context_for_prompt(context)
        public = project_public_source_status([*manual, *law])

        self.assertIn("외국인체류 안내매뉴얼", prompt)
        self.assertIn("출입국관리법", prompt)
        self.assertIn("version/date: 2026-05-21", prompt)
        self.assertNotIn("LAW_API_NO_RESULTS", prompt)
        self.assertIn("공식 매뉴얼 확인됨", public["labels"])
        self.assertIn("실시간 법령 확인됨", public["labels"])
        self.assertNotIn("LAW_API_NO_RESULTS", json.dumps(public, ensure_ascii=False))

    def test_answer_policy_is_procedure_based_not_status_based(self) -> None:
        docs = classify_query_for_grounding("What documents are needed for this extension?", visa_code="A-1")
        work = classify_query_for_grounding("Can I do paid work for a second employer?", visa_code="A-1")
        risk = classify_query_for_grounding("I overstayed by one day. What is the risk?", visa_code="A-1")
        self.assertEqual(select_answer_policy(docs)["policy"], "document_requirement")
        self.assertEqual(select_answer_policy(work)["policy"], "eligibility_activity")
        self.assertEqual(select_answer_policy(risk)["policy"], "law_risk")

    def test_manual_manifest_points_to_current_june_stay_pdf_and_stored_only_hwp(self) -> None:
        manifest_path = REPO_ROOT / "docs" / "source-manuals" / "source_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        stay = manifest["current"]["stay_residence_manual"]
        self.assertEqual(stay["file"], "docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf")
        self.assertEqual(stay["source_date"], "2026-06-01")
        self.assertEqual(
            stay["file_sha256"],
            "e25e97c3c2a05b5676ca3648a04226dcdc2433ab7c89a2f5105e6f8be49778b0",
        )
        self.assertEqual(stay["pages"], 777)
        hwp = stay["alternate_source_files"][0]
        self.assertEqual(hwp["format"], "hwp")
        self.assertEqual(hwp["extraction_primary_format"], "pdf")
        self.assertIn("blocks_text_extraction", hwp["verification_status"])
        self.assertIn("not parsed", hwp["verification_note"].lower())
        self.assertIn("indexed", hwp["verification_note"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
