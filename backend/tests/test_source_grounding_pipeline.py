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

    # The previous version of this pinned the 2026-06-01 stay PDF by exact path,
    # date, SHA-256 and page count, plus an alternate_source_files[0] HWP entry.
    # PR #562 superseded that edition with the 2026-07-31 distribution HWP: the
    # HWP became the source itself rather than an alternate, so
    # alternate_source_files is now null and the June PDF moved to
    # archived_previous_current. Every one of those assertions described a
    # retired shape.
    #
    # Pinning a literal SHA-256 here was also redundant: scripts/check_source_manuals.py
    # recomputes the digest of every manifest file on each run and fails on a
    # mismatch, so identity is enforced against the real bytes rather than
    # against a copy of the hash that rots at each new edition.
    #
    # What is asserted instead is what must hold for WHATEVER edition is current:
    # it exists, it is pinned, it is human-approved, and the edition it replaced
    # is archived rather than dropped.
    def _manifest(self) -> dict:
        path = REPO_ROOT / "docs" / "source-manuals" / "source_manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_current_manuals_are_pinned_present_and_human_approved(self) -> None:
        import re

        current = self._manifest()["current"]
        self.assertIn("stay_residence_manual", current)
        self.assertIn("visa_issuance_manual", current)
        for role, entry in current.items():
            with self.subTest(role=role):
                self.assertEqual(entry["status"], "current")
                self.assertRegex(
                    str(entry["file_sha256"]), r"^[0-9a-f]{64}$",
                    "every current manual is pinned by digest; "
                    "scripts/check_source_manuals.py verifies it against the bytes",
                )
                self.assertTrue(
                    (REPO_ROOT / entry["file"]).is_file(),
                    "manifest names %s but the file is not in the repository"
                    % entry["file"],
                )
                self.assertIn(
                    "approved", str(entry["verification_status"]),
                    "an edition may back direct legal evidence only after the "
                    "human approval gate; an unapproved edition must not be "
                    "recorded as current",
                )

    def test_the_stored_file_matches_the_format_extraction_read(self) -> None:
        """"We extracted from X" and "we stored Y" must not drift apart."""
        for role, entry in self._manifest()["current"].items():
            with self.subTest(role=role):
                fmt = entry.get("extraction_primary_format")
                self.assertTrue(fmt, "%s declares no extraction_primary_format" % role)
                self.assertTrue(
                    str(entry["file"]).lower().endswith("." + str(fmt).lower()),
                    "%s stores %s but claims extraction from %s"
                    % (role, entry["file"], fmt),
                )

    def test_a_superseded_edition_is_archived_never_dropped(self) -> None:
        """An edition change must stay auditable after the fact."""
        stay = self._manifest()["current"]["stay_residence_manual"]
        archived = stay.get("archived_previous_current")
        self.assertIsInstance(
            archived, dict,
            "replacing the current stay manual must record the edition it "
            "replaced, so a swap cannot happen silently",
        )
        for field in ("file", "file_sha256", "source_date", "source_label"):
            self.assertIn(field, archived)
        self.assertTrue(str(stay.get("supersedes") or "").strip(),
                        "the entry must name what it supersedes")

    def test_the_2026_06_stay_pdf_is_still_accounted_for(self) -> None:
        """The edition this test used to pin is retired, not forgotten.

        Keeping this specific assertion means the June PDF cannot quietly vanish
        from the audit trail just because a newer edition arrived.
        """
        blob = json.dumps(self._manifest(), ensure_ascii=False)
        self.assertIn("docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf", blob)


if __name__ == "__main__":
    unittest.main(verbosity=2)
