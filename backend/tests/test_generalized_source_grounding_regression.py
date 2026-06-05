"""Regression tests for the generalized legal/source grounding pipeline.

These tests lock in the *public-safe degradation* guarantees of the merged
source-grounding system (``services/source_grounding.py`` +
``build_law_evidence_pack``). They are deliberately generalized — keyed by
procedure / source-family / status behavior, not by individual visa codes.

The concrete visa codes used below (H-1, G-1-5, D-2, C-3, F-6, E-7) appear
ONLY as regression *fixtures* that exercise the generalized pipeline. They
assert structural / public-safe properties, never hardcoded legal answers, so
they cannot turn into per-visa production branches.

No live network: the law side is driven through the ``law_context`` reuse seam
with ``retrieve=False`` so a malformed law response is simulated with a fixture.
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

from services.law_tools import build_law_evidence_pack  # noqa: E402
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

# Raw developer codes that must never reach the public projection or the
# LLM-facing grounding prompt (Phase 6 regression requirement).
BANNED_PUBLIC_TOKENS = [
    "LAW_API_BAD_RESPONSE",
    "SOURCE_UNAVAILABLE",
    "bad_response",
    "unsupported",
    "not_attempted",
    "parse_error",
    "stack",
    "Traceback",
]


def _manual_fixture() -> dict:
    return {
        "direct": [
            {
                "source_title": "외국인체류 안내매뉴얼",
                "source_date": "2026-06-01",
                "section": "체류자격 외 활동",
                "excerpt": "체류자격 외 활동허가를 받으면 본래 체류자격 외의 활동을 할 수 있다.",
                "issuing_body": "법무부 출입국·외국인정책본부",
            }
        ]
    }


def _bad_law_context() -> dict:
    """A malformed/garbage live-law response reused via the law_context seam."""
    return {
        "attempted": True,
        "law_grounding_used": False,
        "law_grounding": [],
        "law_search_query": "출입국관리법 체류자격 외 활동",
        "grounding_warnings": ["LAW_API_BAD_RESPONSE"],
        "error_type": "LAW_API_BAD_RESPONSE",
        "parser_status": "bad_response",
        "response_shape_hint": "html",
    }


def _build_pack(question: str, *, visa_code: str, task_type: str,
                manual_evidence=None, manual_present=False, law_context=None) -> dict:
    return build_law_evidence_pack(
        question,
        visa_code=visa_code,
        task_type=task_type,
        lang="ko",
        manual_evidence=manual_evidence,
        manual_present=manual_present,
        law_context=law_context,
        retrieve=False,
    )


class MalformedLawDegradationTests(unittest.TestCase):
    """Phase 3/6: a malformed law response degrades gracefully and stays clean."""

    def test_malformed_law_keeps_manual_and_hides_raw_codes(self) -> None:
        pack = _build_pack(
            "Can I do paid part-time work on my D-2 student status?",
            visa_code="D-2",
            task_type="activities_outside_status",
            manual_evidence=_manual_fixture(),
            manual_present=True,
            law_context=_bad_law_context(),
        )
        public = pack["public_source_status"]
        prompt = pack["grounding_context_prompt"]

        # Failed law family must NOT erase the available manual snippet.
        self.assertIn("외국인체류 안내매뉴얼", prompt)
        self.assertIn("체류자격 외 활동허가", prompt)
        self.assertTrue(public.get("hasAvailableOfficialSource"))

        # Public projection shows human-readable labels, not raw codes.
        self.assertIn("공식 매뉴얼 확인됨", public["labels"])
        self.assertIn("실시간 법령 일시 확인 불가", public["labels"])

        # No banned developer code leaks into public output or the LLM prompt.
        public_blob = json.dumps(public, ensure_ascii=False)
        for token in BANNED_PUBLIC_TOKENS:
            self.assertNotIn(token, public_blob, f"{token} leaked into public_source_status")
            self.assertNotIn(token, prompt, f"{token} leaked into grounding prompt")

    def test_developer_diagnostics_still_retain_raw_codes(self) -> None:
        # Raw codes must remain available for developers (logs / opt-in panel),
        # only hidden from the *public* projection — not deleted.
        pack = _build_pack(
            "Can I do paid work on my D-2 status?",
            visa_code="D-2",
            task_type="activities_outside_status",
            manual_evidence=_manual_fixture(),
            manual_present=True,
            law_context=_bad_law_context(),
        )
        dev = json.dumps(pack["developer_source_diagnostics"], ensure_ascii=False)
        self.assertIn("LAW_API_BAD_RESPONSE", dev)

    def test_no_duplicate_empty_manual_source(self) -> None:
        # Regression: the law-side normalizer must not re-emit the "manual"
        # family as an empty ``manual: available`` row alongside the real one.
        pack = _build_pack(
            "What documents do I need to extend my stay?",
            visa_code="F-6",
            task_type="document_requirement_inquiry",
            manual_evidence=_manual_fixture(),
            manual_present=True,
            law_context=_bad_law_context(),
        )
        manuals = [s for s in pack["normalized_official_sources"] if s.get("family") == "manual"]
        self.assertEqual(len(manuals), 1)
        self.assertTrue(manuals[0].get("title"))
        self.assertTrue(manuals[0].get("snippets"))
        # No empty available source name should reach the public list.
        available = [s for s in pack["public_official_sources"] if s.get("publicStatus") == "available"]
        for src in available:
            self.assertTrue(src.get("title") or src.get("sourceName"))


class ParserSchemaTests(unittest.TestCase):
    """Phase 3: parser hardening across response shapes (no exceptions)."""

    def test_unexpected_json_schema_is_no_results_not_crash(self) -> None:
        # Valid JSON, but no recognizable law/term content → not_relevant shape,
        # surfaced as a clean unavailable status (never a thrown parser error).
        body = json.dumps({"unexpected": {"foo": ["bar", 1, 2]}}, ensure_ascii=False)
        normalized = normalize_http_source_response(family="statute", body=body)
        self.assertEqual(normalized["status"], "temporarily_unavailable")
        self.assertEqual(normalized["publicStatus"], "temporarily_unavailable")
        self.assertEqual(normalized["internalCode"], "UNEXPECTED_SCHEMA")
        self.assertEqual(normalized["snippets"], [])

    def test_all_response_shapes_normalize_without_raising(self) -> None:
        valid_json = json.dumps(
            {"LawSearch": {"law": [{"법령명한글": "출입국관리법", "조문내용": "체류자격 관련 조문"}]}},
            ensure_ascii=False,
        )
        shapes = [
            valid_json,
            "{not json",
            "<root><law>출입국관리법 시행령</law></root>",
            "<not<valid<xml",
            "<html><body>portal</body></html>",
            "just a plain banner",
            "",
            "[]",
        ]
        for body in shapes:
            normalized = normalize_http_source_response(family="statute", body=body)
            # Never exposes a raw body/stack and always has a public status.
            self.assertIn(normalized["publicStatus"],
                          {"available", "temporarily_unavailable", "unavailable"})
            self.assertIsInstance(normalized["snippets"], list)


class PublicProjectionSafetyTests(unittest.TestCase):
    """Phase 6: public projection is never contaminated by internal codes."""

    def test_mixed_error_families_project_to_clean_public_labels(self) -> None:
        law = normalize_law_source_attempts(
            law_sources=[],
            source_family_statuses={
                "statute": "bad_response",
                "enforcement_rule": "official_error",
                "administrative_rule": "unsupported",
                "precedent": "not_attempted",
            },
            law_error_type_by_family={"statute": "LAW_API_BAD_RESPONSE"},
        )
        public = project_public_source_status(law, lang="ko")
        public_blob = json.dumps(public, ensure_ascii=False)
        for token in BANNED_PUBLIC_TOKENS:
            self.assertNotIn(token, public_blob)
        # With no available source the projection falls back to limited guidance.
        self.assertIn("출처 제한으로 일반 안내만 가능", public["labels"])
        self.assertIn("관할기관 최종 확인 필요", public["labels"])
        self.assertFalse(public.get("hasAvailableOfficialSource"))

    def test_english_projection_also_public_safe(self) -> None:
        manual = normalize_manual_source_attempts(_manual_fixture()["direct"], manual_present=True)
        public = project_public_source_status(manual, lang="en")
        self.assertIn("Official manual checked", public["labels"])
        for token in BANNED_PUBLIC_TOKENS:
            self.assertNotIn(token, json.dumps(public, ensure_ascii=False))


class AnswerPolicyShapeTests(unittest.TestCase):
    """Phase 5: answer policy adapts to procedure, not to visa code."""

    def test_eligibility_activity_policy_has_restriction_and_fact_sections(self) -> None:
        classified = classify_query_for_grounding("Can I do paid work on my status?", visa_code="C-3")
        policy = select_answer_policy(classified)
        self.assertEqual(policy["policy"], "eligibility_activity")
        self.assertIn("제한/주의", policy["sectionLabels"])
        self.assertIn("확인할 사실", policy["sectionLabels"])

    def test_document_policy_separates_required_and_conditional(self) -> None:
        classified = classify_query_for_grounding(
            "What documents are needed for this application?", visa_code="D-2"
        )
        policy = select_answer_policy(classified)
        self.assertEqual(policy["policy"], "document_requirement")
        self.assertIn("필요한 서류", policy["sectionLabels"])
        self.assertIn("조건부 서류", policy["sectionLabels"])

    def test_same_policy_for_different_visa_codes(self) -> None:
        # The policy must depend on procedure, not on the visa code: an identical
        # document question yields the same policy across unrelated statuses.
        for code in ("A-1", "E-7", "F-6", "G-1-5"):
            classified = classify_query_for_grounding(
                "What documents are required?", visa_code=code
            )
            self.assertEqual(select_answer_policy(classified)["policy"], "document_requirement")


class ConcreteVisaRegressionFixtures(unittest.TestCase):
    """Generalized regression fixtures using concrete visa codes.

    Each case asserts only structural / public-safe properties so the codes
    never become hardcoded production legal branches.
    """

    CASES = [
        ("H-1", "Can I take on paid employment on my H-1 status?", "activities_outside_status"),
        ("G-1-5", "Can I enroll in a degree program on my G-1-5 status?", "activities_outside_status"),
        ("D-2", "What documents do I need for the next procedure on D-2?", "document_requirement_inquiry"),
        ("C-3", "Can I do paid work while on C-3?", "activities_outside_status"),
        ("F-6", "What documents are needed for my F-6 case?", "document_requirement_inquiry"),
        ("E-7", "Can I add a second workplace on my E-7 status?", "workplace_change_addition"),
    ]

    def test_each_fixture_degrades_publicly_safe_with_manual_only(self) -> None:
        for code, question, task_type in self.CASES:
            with self.subTest(code=code):
                pack = _build_pack(
                    question,
                    visa_code=code,
                    task_type=task_type,
                    manual_evidence=_manual_fixture(),
                    manual_present=True,
                    law_context=_bad_law_context(),
                )
                public = json.dumps(pack["public_source_status"], ensure_ascii=False)
                prompt = pack["grounding_context_prompt"]
                # Classification carries the code without deciding the legal answer.
                self.assertEqual(pack["query_classification"]["statusCode"], code)
                self.assertTrue(pack["query_classification"]["doesNotDecideFinalAnswer"])
                # Public-safe: no raw codes anywhere a user could read them.
                for token in BANNED_PUBLIC_TOKENS:
                    self.assertNotIn(token, public, f"{token} leaked for {code}")
                    self.assertNotIn(token, prompt, f"{token} leaked for {code}")
                # Manual evidence still grounds the answer despite law failure.
                self.assertIn("외국인체류 안내매뉴얼", prompt)


class GroundingContextAssemblyTests(unittest.TestCase):
    """Phase 4: assembled context surfaces source metadata + uncertainty."""

    def test_partial_coverage_records_uncertainty_without_codes(self) -> None:
        manual = normalize_manual_source_attempts(_manual_fixture()["direct"], manual_present=True)
        law = normalize_law_source_attempts(
            law_sources=[],
            source_family_statuses={"statute": "bad_response"},
            law_error_type_by_family={"statute": "LAW_API_BAD_RESPONSE"},
        )
        classified = classify_query_for_grounding("Can I do paid work?", visa_code="D-2")
        context = build_official_grounding_context(
            query_classification=classified,
            normalized_sources=[*manual, *law],
        )
        prompt = render_grounding_context_for_prompt(context)
        self.assertTrue(context["uncertaintyBoundaries"])
        # The version/date metadata from the manual is carried into the prompt.
        self.assertIn("version/date: 2026-06-01", prompt)
        for token in BANNED_PUBLIC_TOKENS:
            self.assertNotIn(token, prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
