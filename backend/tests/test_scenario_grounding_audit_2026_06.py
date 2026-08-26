"""Regression QA for nuanced scenario AI answers (grounding audit 2026-06).

These tests lock in the behavior the grounding audit improved:

  * ambiguous scenario questions (study/work/family/refugee on a status, and
    pure legal-concept questions) classify to the right activity, legal issue,
    and answer-shape contract — generalized by signal, never hard-coded per
    visa code;
  * the structured grounding-item schema (source_id, source_title, source_type,
    version_or_date, authority_level, excerpt, page_or_section, url, directness,
    relevance_reason) is well-formed, authority-ranked, and directness-labeled;
  * the answer-directive layer adds an explicit scenario/risk-variant +
    key-dividing-line instruction for ambiguous, not-directly-confirmed
    questions, and never weakens the uncertainty/disclaimer posture.

All assertions are deterministic (no live LLM). Scenario expectations are
tolerant "any-of" intersections so they stay robust as the model layer evolves
while still catching real classification regressions.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

# The suite imports `services.*` directly, which only resolves when backend/ is
# on sys.path. Without this the module raised ModuleNotFoundError at import
# time and reported as a single "failed test" — invisible while the repository
# check ran only 5 of the 47 backend modules.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import answer_quality as aq  # noqa: E402
from services import answer_shape as ash  # noqa: E402
from services import evidence_ontology as eo  # noqa: E402
from services import legal_analysis as la  # noqa: E402

_FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "data" / "eval" / "scenario_grounding_audit_cases_2026_06.json"
)

# The public structured grounding-item schema the audit standardized on.
_GROUNDING_ITEM_KEYS = {
    "source_id", "source_title", "source_type", "version_or_date",
    "authority_level", "excerpt", "page_or_section", "url", "directness",
    "relevance_reason",
}
_PUBLIC_DIRECTNESS = {"DIRECT", "PARTIAL", "GENERAL", "ANALOGICAL", "NOT_FOUND"}
_PUBLIC_SOURCE_TYPES = {
    "statute", "regulation", "manual", "hikorea", "notice", "case_law",
    "internal", "inference",
}


def _load_cases():
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return data["cases"]


class ScenarioClassificationTests(unittest.TestCase):
    """Each nuanced scenario routes to a sensible activity/issue/contract."""

    def test_every_case_classifies_to_expected_issue_and_contract(self):
        for case in _load_cases():
            with self.subTest(case=case["id"]):
                facts = la.extract_immigration_facts(
                    case["question"], visa_code=case.get("visa_code")
                )
                issues = la.classify_legal_issue_types(case["question"], facts)
                acts = facts.get("proposed_activities") or []
                contract = ash.build_answer_shape_contract(
                    legal_issue_types=issues,
                    immigration_facts=facts,
                    answer_certainty_level="",
                    question_type="",
                )

                # Status detection (when the scenario names a code).
                want_status = case.get("expect_status_contains")
                if want_status:
                    detected = " ".join(
                        str(facts.get(k) or "")
                        for k in ("current_status", "current_parent_status", "target_status")
                    )
                    self.assertIn(
                        want_status, detected,
                        f"{case['id']}: expected status {want_status} in {detected!r}",
                    )

                # Activity classification (any-of intersection).
                want_acts = case.get("expect_activities_any") or []
                if want_acts:
                    self.assertTrue(
                        set(want_acts) & set(acts),
                        f"{case['id']}: none of {want_acts} in detected activities {acts}",
                    )

                # Legal issue classification (any-of intersection).
                want_issues = case.get("expect_issues_any") or []
                self.assertTrue(
                    set(want_issues) & set(issues),
                    f"{case['id']}: none of {want_issues} in classified issues {issues}",
                )

                # Answer-shape contract routing.
                want_contracts = case.get("expect_contracts_any") or []
                self.assertIn(
                    contract["contract_key"], want_contracts,
                    f"{case['id']}: contract {contract['contract_key']} not in {want_contracts}",
                )

    def test_no_scenario_falls_through_to_non_immigration_only(self):
        """A scenario should never be classified *only* as non-immigration."""
        for case in _load_cases():
            with self.subTest(case=case["id"]):
                facts = la.extract_immigration_facts(
                    case["question"], visa_code=case.get("visa_code")
                )
                issues = la.classify_legal_issue_types(case["question"], facts)
                self.assertNotEqual(
                    issues, ["non_immigration_adjacent_issue"],
                    f"{case['id']}: classified only as non_immigration_adjacent_issue",
                )


class GroundingItemSchemaTests(unittest.TestCase):
    """The structured grounding schema is well-formed and authority-ranked."""

    def test_to_grounding_item_shape_and_defaults(self):
        item = eo.to_grounding_item({}, relevance="")
        self.assertEqual(set(item.keys()), _GROUNDING_ITEM_KEYS)
        # An under-described item must never look like binding direct authority.
        self.assertEqual(item["directness"], "NOT_FOUND")
        self.assertEqual(item["authority_level"], 6)
        self.assertIn(item["source_type"], _PUBLIC_SOURCE_TYPES)

    def test_authority_hierarchy_is_monotonic_by_source_type(self):
        self.assertEqual(eo.authority_level_for("statute"), 1)
        self.assertEqual(eo.authority_level_for("enforcement_decree"), 2)
        self.assertEqual(eo.authority_level_for("manual"), 3)
        self.assertEqual(eo.authority_level_for("precedent"), 5)
        self.assertEqual(eo.authority_level_for("inference"), 7)
        # Statute outranks (lower number than) manual which outranks case law.
        self.assertLess(eo.authority_level_for("statute"), eo.authority_level_for("manual"))
        self.assertLess(eo.authority_level_for("manual"), eo.authority_level_for("precedent"))

    def test_directness_projection_is_complete(self):
        self.assertEqual(eo.public_directness_for("direct"), "DIRECT")
        self.assertEqual(eo.public_directness_for("related"), "PARTIAL")
        self.assertEqual(eo.public_directness_for("background"), "GENERAL")
        self.assertEqual(eo.public_directness_for("analogical"), "ANALOGICAL")
        self.assertEqual(eo.public_directness_for("not_relevant"), "NOT_FOUND")
        self.assertEqual(eo.public_directness_for("garbage"), "NOT_FOUND")

    def test_grounding_item_preserves_real_fields_without_fabrication(self):
        raw = {
            "source_type": "statute",
            "law_name": "출입국관리법",
            "article": "제20조",
            "law_id": "001234",
            "summary": "체류자격외활동에 관한 규정",
            "enforcement_date": "2024.1.1",
            "source_url": "https://www.law.go.kr/example",
        }
        item = eo.to_grounding_item(raw, relevance="direct", relevance_reason="exact match")
        self.assertEqual(item["source_title"], "출입국관리법")
        self.assertEqual(item["source_type"], "statute")
        self.assertEqual(item["authority_level"], 1)
        self.assertEqual(item["directness"], "DIRECT")
        self.assertEqual(item["page_or_section"], "제20조")
        self.assertEqual(item["source_id"], "001234")
        self.assertEqual(item["version_or_date"], "2024.1.1")
        self.assertEqual(item["url"], "https://www.law.go.kr/example")
        self.assertEqual(item["relevance_reason"], "exact match")

    def test_build_legal_analysis_emits_wellformed_grounding_items(self):
        law_sources = [
            {
                "source_type": "statute",
                "law_name": "출입국관리법",
                "article": "제20조",
                "summary": "체류자격외활동 허가",
                "reference": "LAW-1",
            },
            {
                "source_type": "enforcement_decree",
                "law_name": "출입국관리법 시행령",
                "summary": "활동 범위",
                "reference": "DEC-1",
            },
        ]
        analysis = la.build_legal_analysis(
            question="G-1-5인데 제주대학교에서 청강이 가능할까?",
            question_type="activity_on_status",
            visa_code="G-1-5",
            risk_level="medium",
            law_sources=law_sources,
        )
        items = analysis.get("grounding_items")
        self.assertIsInstance(items, list)
        for it in items:
            self.assertEqual(set(it.keys()), _GROUNDING_ITEM_KEYS)
            self.assertIn(it["directness"], _PUBLIC_DIRECTNESS)
            self.assertIn(it["source_type"], _PUBLIC_SOURCE_TYPES)
            self.assertIn(it["authority_level"], range(1, 8))
            self.assertTrue(it["relevance_reason"])
        # NOT_FOUND items are excluded from the surfaced list.
        self.assertNotIn("NOT_FOUND", [it["directness"] for it in items])

    def test_authority_stub_carries_level_and_directness(self):
        analysis = la.build_legal_analysis(
            question="G-1-5 아르바이트 가능?",
            question_type="activity_on_status",
            visa_code="G-1-5",
            risk_level="high",
            direct_manual_sources=[{"source_type": "manual", "title": "체류 매뉴얼"}],
        )
        for stub in analysis.get("direct_authority") or []:
            self.assertIn("authority_level", stub)
            self.assertIn("directness", stub)
            self.assertIn(stub["directness"], _PUBLIC_DIRECTNESS)


class AmbiguousScenarioDirectiveTests(unittest.TestCase):
    """The answer-directive layer adds risk-variant + dividing-line guidance."""

    def _directives(self, *, qtype, mode):
        quality = {
            "answer_quality_mode": mode,
            "question_type": qtype,
            "related_statuses_not_sources": [],
            "official_confirmation_questions": [],
        }
        return aq.build_answer_directives(quality, lang="ko")

    def test_ambiguous_uncertain_scenario_requests_risk_variants(self):
        text = self._directives(qtype=aq.Q_ACTIVITY_ON_STATUS, mode=aq.SOURCE_LIMITED)
        self.assertIn("risk level", text.lower())
        self.assertIn("dividing line", text.lower())
        self.assertIn("copy-ready", text.lower())

    def test_source_confirmed_question_does_not_force_variant_breakdown(self):
        text = self._directives(qtype=aq.Q_ACTIVITY_ON_STATUS, mode=aq.SOURCE_CONFIRMED)
        # Confirmed answers should stay concise, not be forced into variant prose.
        self.assertNotIn("Split the user's scenario into", text)

    def test_directives_keep_uncertainty_and_no_fake_citation_posture(self):
        text = self._directives(qtype=aq.Q_ACTIVITY_ON_STATUS, mode=aq.SOURCE_UNAVAILABLE)
        lowered = text.lower()
        # Disclaimer/uncertainty posture preserved (not weakened).
        self.assertIn("official confirmation is required", lowered)
        self.assertIn("invent", lowered)  # forbids invented document lists/citations


if __name__ == "__main__":
    unittest.main()
