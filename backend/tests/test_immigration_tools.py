"""Contract tests for the immigration tool + evidence layer.

The assertions here are safety properties, not implementation details. Three
matter more than the rest:

  1. "We could not look" never becomes "there is no rule". A retrieval failure
     and an empty result are different facts about the world, and only one of
     them says anything about Korean immigration law.

  2. The model never promotes evidence. `approval_state` and
     `verification_state` are set deterministically from the registry and the
     retrieval outcome; no path lets a caller mark unapproved content usable.

  3. Sub-status rules never become parent rules. A D-2-1 requirement rendered
     as a universal D-2 requirement is the most consequential rendering error
     this dataset can produce.

Fully offline: every network-backed tool is exercised through an injected
callable.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services import immigration_tools as it  # noqa: E402


VISA_RECORDS = [
    {"code": "D-2", "title": "유학", "summary": "정규 교육과정 수학"},
    {"code": "D-2-1", "title": "전문학사", "summary": "전문대학 유학"},
    {"code": "D-2-2", "title": "학사유학", "summary": "대학 유학"},
    {"code": "E-7", "title": "특정활동", "summary": "특정활동 취업"},
]


class RetrievalFailureVsNoResultsTests(unittest.TestCase):
    """The distinction that protects users from a fabricated absence of law."""

    def test_a_missing_manual_index_is_a_retrieval_failure_not_an_empty_result(self):
        def index_missing(query, **kwargs):
            return {"status": "index_unavailable", "approved": [], "needs_review": []}

        result = it.search_manual("체류자격 변경", search_fn=index_missing)
        self.assertIs(result.status, it.ToolStatus.RETRIEVAL_FAILED)
        self.assertTrue(result.is_inconclusive)

    def test_an_empty_manual_search_is_a_real_finding(self):
        def nothing_found(query, **kwargs):
            return {"status": "no_results", "approved": [], "needs_review": []}

        result = it.search_manual("존재하지않는질의어", search_fn=nothing_found)
        self.assertIs(result.status, it.ToolStatus.NO_RESULTS)
        self.assertFalse(result.is_inconclusive,
                         "a completed search that matched nothing IS conclusive")

    def test_a_law_lookup_failure_is_inconclusive(self):
        def failing(query, **kwargs):
            return {"error_type": "law_api_transport_error"}

        result = it.search_law("출입국관리법", search_fn=failing)
        self.assertIs(result.status, it.ToolStatus.RETRIEVAL_FAILED)
        self.assertTrue(result.is_inconclusive)

    def test_a_missing_credential_is_reported_as_not_configured(self):
        """An operator problem must not read as a legal finding."""
        def unconfigured(query, **kwargs):
            return {"error_type": "law_api_not_configured"}

        result = it.search_law("출입국관리법", search_fn=unconfigured)
        self.assertIs(result.status, it.ToolStatus.NOT_CONFIGURED)
        self.assertTrue(result.is_inconclusive)

    def test_an_empty_law_search_is_conclusive(self):
        result = it.search_law("xyzzy", search_fn=lambda q, **kw: {"items": []})
        self.assertIs(result.status, it.ToolStatus.NO_RESULTS)
        self.assertFalse(result.is_inconclusive)

    def test_a_raising_backend_never_becomes_a_legal_claim(self):
        def exploding(query, **kwargs):
            raise RuntimeError("index corrupted")

        result = it.search_manual("체류", search_fn=exploding)
        self.assertIs(result.status, it.ToolStatus.RETRIEVAL_FAILED)
        self.assertEqual(result.evidence, [])

    def test_the_pack_reports_why_a_lookup_could_not_run(self):
        pack = it.EvidencePack(question="D-2 아르바이트")
        pack.add(it.search_manual("q", search_fn=lambda q, **kw: {"status": "index_unavailable"}))
        pack.add(it.search_law("q", search_fn=lambda q, **kw: {"items": []}))

        reasons = pack.unavailable_reasons()
        self.assertEqual(len(reasons), 1)
        self.assertEqual(reasons[0]["tool"], "search_manual")
        # The law search DID run and found nothing — reported separately.
        self.assertEqual(pack.empty_result_tools(), ["search_law"])


class ApprovalIsDeterministicTests(unittest.TestCase):
    """The LLM must never be able to promote evidence."""

    MANUAL_HIT = {
        "status": "ok",
        "approved": [{"source_id": "visa_manual_2026_07_31_hwp", "family_key": "visa_issuance_manual",
                      "heading": "사증발급 일반", "page": 12, "excerpt": "…", "manual_version": "2026.7"}],
        "needs_review": [{"source_id": "draft_manual", "family_key": "stay_guide_manual",
                          "heading": "체류 안내", "page": 5, "excerpt": "…"}],
    }

    def _search(self):
        return it.search_manual("사증발급", search_fn=lambda q, **kw: self.MANUAL_HIT)

    def test_approved_manual_content_may_back_a_direct_assertion(self):
        approved = [e for e in self._search().evidence
                    if e.approval_state is it.ApprovalState.APPROVED]
        self.assertTrue(approved)
        self.assertTrue(all(e.usable_for_direct_assertion for e in approved))

    def test_review_pending_content_is_searchable_but_never_direct_evidence(self):
        pending = [e for e in self._search().evidence
                   if e.approval_state is it.ApprovalState.NEEDS_REVIEW]
        self.assertTrue(pending, "unapproved content stays retrievable as context")
        self.assertFalse(any(e.usable_for_direct_assertion for e in pending))

    def test_unapproved_content_cannot_be_promoted_by_setting_confidence(self):
        """Confidence is a ranking signal, never an approval mechanism."""
        item = it.EvidenceItem(
            id="x", source_family="manual",
            authority_type=it.AuthorityType.UNAPPROVED_EXTRACTION,
            confidence=1.0, relevance="direct",
            verification_state=it.VerificationState.VERIFIED,
        )
        self.assertFalse(item.usable_for_direct_assertion)

    def test_an_approved_authority_without_approval_state_is_still_blocked(self):
        item = it.EvidenceItem(
            id="x", source_family="manual",
            authority_type=it.AuthorityType.APPROVED_MANUAL,
            approval_state=it.ApprovalState.NEEDS_REVIEW,
        )
        self.assertFalse(item.usable_for_direct_assertion)

    def test_extraction_caveats_travel_with_manual_evidence(self):
        """Flattened tables must not be read as cell relationships."""
        for item in self._search().evidence:
            self.assertIn("extractionCaveat", item.structured_fact)


class LawGroundingPostureTests(unittest.TestCase):
    LAW_HIT = {"items": [{"law_name": "출입국관리법", "article": "제19조",
                          "effective_date": "2026-01-01", "summary": "신고의무"}]}

    def test_audit_mode_retrieves_but_never_permits_a_direct_citation(self):
        result = it.search_law("출입국관리법", search_fn=lambda q, **kw: self.LAW_HIT,
                               grounding_mode="audit")
        self.assertTrue(result.ok, "audit posture still retrieves")
        self.assertTrue(result.evidence)
        for item in result.evidence:
            self.assertIs(item.verification_state, it.VerificationState.AUDIT_ONLY)
            self.assertFalse(item.usable_for_direct_assertion)

    def test_enabled_mode_permits_a_direct_citation(self):
        result = it.search_law("출입국관리법", search_fn=lambda q, **kw: self.LAW_HIT,
                               grounding_mode="enabled")
        self.assertTrue(all(e.usable_for_direct_assertion for e in result.evidence))

    def test_a_repealed_statute_stays_visible_but_cannot_back_an_assertion(self):
        """Hiding it would suggest the current rule was never found."""
        repealed = {"items": [{"law_name": "구 출입국관리법", "status": "폐지", "repealed": True}]}
        result = it.search_law("구법", search_fn=lambda q, **kw: repealed,
                               grounding_mode="enabled")
        self.assertTrue(result.evidence, "a repealed law is still reported")
        self.assertEqual(result.evidence[0].status, "repealed")
        self.assertFalse(result.evidence[0].usable_for_direct_assertion)


class PrecedentIsContextualTests(unittest.TestCase):
    def test_precedent_is_never_direct_statutory_authority(self):
        cases = [{"case_name": "대법원 2020두1234", "case_number": "2020두1234",
                  "decision_date": "2020-05-01", "summary": "…"}]
        result = it.search_precedent("체류자격 변경 불허", search_fn=lambda q, **kw: cases)
        self.assertTrue(result.ok)
        for item in result.evidence:
            self.assertIs(item.authority_type, it.AuthorityType.PRECEDENT)
            self.assertFalse(item.usable_for_direct_assertion)

    def test_precedent_outranks_nothing_that_is_actual_authority(self):
        pack = it.EvidencePack()
        pack.add(it.search_precedent("q", search_fn=lambda q, **kw: [{"case_number": "1"}]))
        pack.add(it.search_law("q", search_fn=lambda q, **kw: {"items": [{"law_name": "출입국관리법"}]},
                               grounding_mode="enabled"))
        self.assertIs(pack.evidence[0].authority_type, it.AuthorityType.STATUTE)

    def test_no_precedent_adapter_is_not_available_rather_than_empty(self):
        result = it.search_precedent("q")
        self.assertIs(result.status, it.ToolStatus.NOT_AVAILABLE)
        self.assertTrue(result.is_inconclusive)


class StatusHierarchyTests(unittest.TestCase):
    def test_a_parent_lists_its_subcodes_without_absorbing_their_rules(self):
        result = it.lookup_status("D-2", visa_records=VISA_RECORDS)
        fact = result.evidence[0].structured_fact
        self.assertFalse(fact["isSubcode"])
        self.assertEqual(fact["subcodes"], ["D-2-1", "D-2-2"])
        self.assertTrue(fact["subcodeRulesAreNotParentRules"])

    def test_a_subcode_is_classified_under_its_parent(self):
        result = it.lookup_status("D-2-1", visa_records=VISA_RECORDS)
        fact = result.evidence[0].structured_fact
        self.assertTrue(fact["isSubcode"])
        self.assertEqual(fact["parentCode"], "D-2")

    def test_an_unknown_code_is_no_results_not_an_invented_record(self):
        result = it.lookup_status("Z-9", visa_records=VISA_RECORDS)
        self.assertIs(result.status, it.ToolStatus.NO_RESULTS)
        self.assertEqual(result.evidence, [])

    def test_missing_visa_records_is_not_available_not_no_results(self):
        result = it.lookup_status("D-2")
        self.assertIs(result.status, it.ToolStatus.NOT_AVAILABLE)
        self.assertTrue(result.is_inconclusive)


class DeadlineTests(unittest.TestCase):
    def test_a_known_statutory_period_is_computed_with_its_basis(self):
        result = it.calculate_deadline("2026-03-01", period="foreign_resident_registration")
        fact = result.evidence[0].structured_fact
        self.assertEqual(fact["preparationDeadline"], "2026-05-30")
        self.assertIn("제31조", fact["statutoryBasis"])

    def test_a_computed_date_is_never_presented_as_an_official_deadline(self):
        result = it.calculate_deadline(date(2026, 3, 1), period="workplace_change_report")
        fact = result.evidence[0].structured_fact
        self.assertFalse(fact["isOfficialDeadline"])
        self.assertIn("공식 기한", fact["caution"])

    def test_an_arbitrary_interval_carries_no_statutory_basis(self):
        """A made-up interval must never look like a legal deadline."""
        result = it.calculate_deadline("2026-03-01", days=45)
        item = result.evidence[0]
        self.assertEqual(item.structured_fact["statutoryBasis"], "")
        self.assertLess(item.confidence, 0.5)
        self.assertIsNot(item.authority_type, it.AuthorityType.STATUTE)

    def test_an_unknown_period_name_is_refused_rather_than_guessed(self):
        result = it.calculate_deadline("2026-03-01", period="invented_period")
        self.assertIs(result.status, it.ToolStatus.NO_RESULTS)
        self.assertIn("knownPeriods", result.diagnostics)

    def test_a_malformed_date_is_a_bad_request(self):
        self.assertIs(it.calculate_deadline("not-a-date").status, it.ToolStatus.BAD_REQUEST)


class EnforcementTests(unittest.TestCase):
    class _Baseline:
        status = "AVAILABLE"
        legally_adjustable_range = {"min": 100000, "max": 300000}
        available_dispositions = ["과태료"]

    def test_the_baseline_is_rule_output_and_carries_no_probability(self):
        result = it.analyze_enforcement_rules(object(), calculate_fn=lambda c: self._Baseline())
        fact = result.evidence[0].structured_fact
        self.assertTrue(fact["isDeterministicRuleOutput"])
        self.assertFalse(fact["isPrediction"])
        blob = str(result.public_dict())
        for banned in ("probability", "likelihood", "확률"):
            self.assertNotIn(banned, blob.lower())

    def test_no_encoded_rule_is_no_results_not_a_fabricated_range(self):
        class Unavailable:
            status = "UNAVAILABLE"
            legally_adjustable_range = None
            available_dispositions = []

        result = it.analyze_enforcement_rules(object(), calculate_fn=lambda c: Unavailable())
        self.assertIs(result.status, it.ToolStatus.NO_RESULTS)


class FactExtractionTests(unittest.TestCase):
    def test_status_codes_and_intent_are_read_from_the_question(self):
        facts = it.extract_immigration_facts("D-2-1 인데 근무처 변경 신고를 해야 하나요?")
        self.assertEqual(facts["statusCodes"], ["D-2-1"])
        self.assertTrue(facts["workplaceChange"])

    def test_paid_and_unpaid_are_distinguished_not_assumed(self):
        self.assertTrue(it.extract_immigration_facts("아르바이트로 급여를 받아요")["paidActivity"])
        self.assertFalse(it.extract_immigration_facts("무급 자원봉사입니다")["paidActivity"])

    def test_an_unstated_fact_stays_unstated(self):
        """The orchestrator must be able to tell 'not said' from 'said no'."""
        facts = it.extract_immigration_facts("체류자격 변경이 궁금합니다")
        self.assertIsNone(facts["paidActivity"])
        self.assertEqual(facts["statusCodes"], [])

    def test_a_date_in_the_question_is_normalized(self):
        facts = it.extract_immigration_facts("2026년 3월 1일에 입국했습니다")
        self.assertIn("2026-03-01", facts["dates"])

    def test_a_decisive_missing_fact_is_reported_for_clarification(self):
        facts = it.extract_immigration_facts("근무처 변경 신고 기한이 언제인가요?")
        self.assertIn("statusCodes", it.missing_decisive_facts(facts))

    def test_nothing_is_missing_when_the_question_supplies_it(self):
        facts = it.extract_immigration_facts("E-7 인데 근무처 변경 신고 기한이 언제인가요?")
        self.assertEqual(it.missing_decisive_facts(facts), [])


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = it.build_registry()

    def test_every_documented_tool_is_registered(self):
        for name in ("lookup_status", "search_manual", "search_law",
                     "search_precedent", "calculate_deadline",
                     "analyze_enforcement_rules"):
            self.assertIn(name, self.registry.names())

    def test_an_unknown_tool_is_a_bad_request_not_a_crash(self):
        """A model picking a nonexistent tool is a routing mistake, not a fault."""
        result = self.registry.call("make_up_the_answer")
        self.assertIs(result.status, it.ToolStatus.BAD_REQUEST)
        self.assertIn("available", result.diagnostics)

    def test_invalid_arguments_are_a_bad_request_not_a_crash(self):
        result = self.registry.call("lookup_status", nonsense=True)
        self.assertIs(result.status, it.ToolStatus.BAD_REQUEST)

    def test_a_tool_fault_never_surfaces_as_evidence(self):
        registry = it.ImmigrationToolRegistry([
            it.ToolSpec("boom", "visable.boom", "always fails",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("x"))),
        ])
        result = registry.call("boom")
        self.assertIs(result.status, it.ToolStatus.RETRIEVAL_FAILED)
        self.assertEqual(result.evidence, [])

    def test_every_tool_declares_a_stable_mcp_name(self):
        """Exposing this over MCP later must be an adapter, not a rename."""
        for entry in self.registry.describe():
            self.assertTrue(entry["mcpName"].startswith("visable."))

    def test_network_and_credential_requirements_are_declared(self):
        by_name = {e["name"]: e for e in self.registry.describe()}
        self.assertTrue(by_name["search_law"]["requiresCredential"])
        self.assertFalse(by_name["lookup_status"]["readsNetwork"])

    def test_registering_a_duplicate_name_is_refused(self):
        registry = it.ImmigrationToolRegistry([])
        spec = it.ToolSpec("t", "visable.t", "d", lambda **kw: it.ToolResult("t", it.ToolStatus.OK))
        registry.register(spec)
        with self.assertRaises(ValueError):
            registry.register(spec)


class EvidenceOrderingTests(unittest.TestCase):
    def test_the_authority_hierarchy_is_encoded_not_described(self):
        ranks = [it.AUTHORITY_RANK[a] for a in (
            it.AuthorityType.STATUTE,
            it.AuthorityType.APPROVED_MANUAL,
            it.AuthorityType.OFFICIAL_GUIDANCE,
            it.AuthorityType.PRECEDENT,
            it.AuthorityType.UNAPPROVED_EXTRACTION,
        )]
        self.assertEqual(ranks, sorted(ranks), "the hierarchy must be strictly ordered")

    def test_a_pack_separates_direct_from_contextual_evidence(self):
        pack = it.EvidencePack()
        pack.add(it.search_law("q", search_fn=lambda q, **kw: {"items": [{"law_name": "출입국관리법"}]},
                               grounding_mode="enabled"))
        pack.add(it.search_precedent("q", search_fn=lambda q, **kw: [{"case_number": "1"}]))
        self.assertEqual(len(pack.direct_evidence), 1)
        self.assertEqual(len(pack.contextual_evidence), 1)

    def test_the_public_pack_never_hides_what_could_not_be_checked(self):
        pack = it.EvidencePack(question="q")
        pack.add(it.search_manual("q", search_fn=lambda q, **kw: {"status": "index_unavailable"}))
        public = pack.public_dict()
        self.assertTrue(public["unavailable"])
        self.assertEqual(public["directEvidenceCount"], 0)


if __name__ == "__main__":
    unittest.main()
