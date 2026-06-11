"""Tests for the Law Open Data precedent-family source adapter scaffold.

Covers (Phase 10 of the scaffold task):

  1. LAW_API_OC is the canonical Law Open Data credential.
  2. Source-family definitions exist for the precedent-related families.
  3. precedent uses the confirmed target=prec; unconfirmed families stay
     scaffold_only / not_configured (no fake production adapters).
  4. Retrieval routing requests precedent-like families only for relevant
     issue types; routine document / interpreter questions do not.
  5. Fixture-based normalizers map list/body shapes into evidence items.
  6. API error / HTML responses normalize to public-safe unavailable.
  7. The citation verifier rejects fabricated case/decision citations and
     accepts fixture-backed ones (and never over-claims contextual evidence).
  8. Public source-status projection hides raw codes for these families.

Everything is deterministic and offline: no live API, no real LAW_API_OC.

    python3 -m pytest backend/tests/test_law_open_data_precedent_scaffold.py -q
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import evidence_ontology as onto  # noqa: E402
from services import law_tools as lt  # noqa: E402
from services import precedent_sources as ps  # noqa: E402
from services.citation_verifier import (  # noqa: E402
    extract_case_decision_citations,
    verify_case_decision_citations,
)
from services.evidence_ontology import (  # noqa: E402
    LIVE_ADAPTER_STATUSES,
    route_source_families,
    source_family_definition,
    source_family_live_adapter_status,
    source_family_support_status,
)
from services.grounding_config import GroundingConfig, load_grounding_config  # noqa: E402
from services.legal_analysis import (  # noqa: E402
    LEGAL_ISSUE_TYPES,
    build_generalized_source_plan,
    classify_legal_issue_types,
    extract_immigration_facts,
)
from services.source_grounding import (  # noqa: E402
    normalize_law_source_attempts,
    project_public_source_status,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "precedent_sources"
PRECEDENT_FAMILIES = ("precedent", "administrative_appeal", "legal_interpretation", "constitutional_decision")
_RAW_CODES = (
    "unsupported", "not_attempted", "bad_response", "planned_not_wired",
    "scaffold_only", "parse_error", "official_error", "http_error",
    "LAW_API_BAD_RESPONSE", "SOURCE_UNAVAILABLE",
)


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _audit_oc_cfg() -> GroundingConfig:
    return GroundingConfig(mode="audit", law_api_oc="secret-oc")


def _transport(body: str, status: int = 200):
    def send(url: str, timeout: float) -> lt.LawHttpResponse:
        return lt.LawHttpResponse(ok=True, status_code=status, text=body)
    return send


# ---------------------------------------------------------------------------
# 1. LAW_API_OC canonical credential convention
# ---------------------------------------------------------------------------
class LawApiOcCredentialTests(unittest.TestCase):
    _KEYS = ("LAW_API_OC", "LAW_API_KEY", "LAW_GROUNDING_MODE")

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in self._KEYS}
        for k in self._KEYS:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_law_api_oc_is_canonical_credential(self):
        os.environ["LAW_API_OC"] = "oc-value"
        cfg = load_grounding_config()
        self.assertEqual(cfg.law_api_credential, "oc-value")
        self.assertEqual(cfg.law_api_credential_source, "LAW_API_OC")
        self.assertTrue(cfg.law_api_oc_configured)
        self.assertTrue(cfg.law_api_configured)

    def test_law_api_oc_preferred_over_legacy_key(self):
        os.environ["LAW_API_OC"] = "oc-value"
        os.environ["LAW_API_KEY"] = "legacy-key"
        cfg = load_grounding_config()
        self.assertEqual(cfg.law_api_credential, "oc-value")
        self.assertEqual(cfg.law_api_credential_source, "LAW_API_OC")

    def test_legacy_key_only_recommends_oc(self):
        os.environ["LAW_API_KEY"] = "legacy-key"
        cfg = load_grounding_config()
        self.assertEqual(cfg.law_api_credential, "legacy-key")
        self.assertEqual(cfg.law_api_credential_source, "LAW_API_KEY")
        self.assertIn("LAW_API_OC_RECOMMENDED", cfg.warnings)

    def test_no_credential_is_not_configured(self):
        cfg = load_grounding_config()
        self.assertFalse(cfg.law_api_configured)
        self.assertEqual(cfg.law_api_credential, "")

    def test_precedent_scaffold_never_exposes_oc(self):
        captured = {}

        def send(url, timeout):
            captured["url"] = url  # the real URL embeds OC=secret-oc internally
            return lt.LawHttpResponse(ok=True, status_code=200, text=fixture("precedent_list.json"))

        result = ps.search_precedents("판례", config=_audit_oc_cfg(), transport=send)
        self.assertIn("OC=secret-oc", captured["url"])  # embedded internally only
        self.assertNotIn("secret-oc", json.dumps(result, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 2. Source-family definitions
# ---------------------------------------------------------------------------
class SourceFamilyDefinitionTests(unittest.TestCase):
    def test_definitions_exist_for_precedent_families(self):
        for fam in PRECEDENT_FAMILIES:
            d = source_family_definition(fam)
            self.assertTrue(d["labelKo"])
            self.assertTrue(d["labelEn"])
            self.assertIn(d["liveAdapterStatus"], LIVE_ADAPTER_STATUSES)
            self.assertTrue(d["adjudicative"])
            self.assertTrue(d["citationGradeCapable"])

    def test_precedent_families_are_scaffold_only(self):
        for fam in PRECEDENT_FAMILIES:
            self.assertEqual(source_family_live_adapter_status(fam), "scaffold_only")

    def test_wired_families_report_wired(self):
        for fam in ("statute", "enforcement_decree", "enforcement_rule", "administrative_rule", "legal_term", "manual"):
            self.assertEqual(source_family_live_adapter_status(fam), "wired")

    def test_support_status_contract_preserved(self):
        # Regression guard: the coarse helper must NOT start returning the new
        # richer enum — existing callers/tests depend on wired/planned_not_wired.
        for fam in onto.SOURCE_FAMILIES:
            self.assertIn(source_family_support_status(fam), ("wired", "planned_not_wired"))

    def test_public_unavailable_labels_are_safe(self):
        for fam in PRECEDENT_FAMILIES:
            for lang in ("ko", "en"):
                label = onto.source_family_public_unavailable_label(fam, lang=lang)
                self.assertTrue(label)
                for code in _RAW_CODES:
                    self.assertNotIn(code, label)


# ---------------------------------------------------------------------------
# 3. Endpoint / target scaffold
# ---------------------------------------------------------------------------
class TargetScaffoldTests(unittest.TestCase):
    def test_precedent_target_is_prec(self):
        self.assertEqual(ps.PRECEDENT_LIST_TARGET, "prec")
        self.assertEqual(ps.SOURCE_FAMILY_LIST_TARGETS["precedent"], "prec")

    def test_unconfirmed_targets_remain_none(self):
        for fam in ("administrative_appeal", "legal_interpretation", "constitutional_decision"):
            self.assertIsNone(ps.SOURCE_FAMILY_LIST_TARGETS[fam])

    def test_search_precedents_uses_target_prec(self):
        captured = {}

        def send(url, timeout):
            captured["url"] = url
            return lt.LawHttpResponse(ok=True, status_code=200, text=fixture("precedent_list.json"))

        ps.search_precedents("출입국 판례", config=_audit_oc_cfg(), transport=send)
        self.assertIn("target=prec", captured["url"])
        self.assertIn("lawSearch.do", captured["url"])

    def test_capture_script_precedent_target_prec_others_none(self):
        scripts_dir = REPO_ROOT / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import capture_law_api_shape as cap  # noqa: E402
        self.assertEqual(cap.FAMILY_TARGETS["precedent"], "prec")
        for fam in ("administrative_appeal", "legal_interpretation", "constitutional_decision"):
            self.assertIsNone(cap.FAMILY_TARGETS[fam])

    def test_retrieve_official_source_family_uses_confirmed_precedent_list_target(self):
        # Only the confirmed list endpoint is live-wired. List results remain
        # contextual and cannot be treated as holdings/body authority.
        res = lt.retrieve_official_source_family("precedent", "판례", config=_audit_oc_cfg(), transport=_transport(fixture("precedent_list.json")))
        self.assertEqual(res["status"], lt.SOURCE_STATUS_RESULTS_FOUND)
        self.assertEqual(res["normalized_items"][0]["result_kind"], "list_result")
        self.assertEqual(res["normalized_items"][0]["citation_grade"], "contextual")


# ---------------------------------------------------------------------------
# 4. Source routing rules
# ---------------------------------------------------------------------------
class RoutingTests(unittest.TestCase):
    def families(self, question: str):
        facts = extract_immigration_facts(question)
        issues = classify_legal_issue_types(question, facts)
        return set(route_source_families(issues)), set(issues)

    def test_denial_remedy_routes_precedent_and_appeal(self):
        fams, issues = self.families("체류 연장 불허 처분을 행정심판으로 다툴 수 있나요?")
        self.assertIn("denial_revocation_or_remedy", issues)
        self.assertIn("precedent", fams)
        self.assertIn("administrative_appeal", fams)

    def test_constitutional_routes_constitutional_decision(self):
        fams, issues = self.families("외국인 강제퇴거가 기본권을 침해하는지 헌재 결정이 있나요?")
        self.assertIn("constitutional_or_fundamental_rights", issues)
        self.assertIn("constitutional_decision", fams)

    def test_ambiguous_interpretation_routes_legal_interpretation(self):
        fams, issues = self.families("체류자격외활동 허가 범위 법령해석이 모호한데 유권해석 사례가 있나요?")
        self.assertIn("discretionary_or_ambiguous_interpretation", issues)
        self.assertIn("legal_interpretation", fams)

    def test_document_checklist_does_not_route_precedent(self):
        fams, _ = self.families("D-2 연장 구비서류는 무엇인가요?")
        self.assertNotIn("precedent", fams)
        self.assertNotIn("constitutional_decision", fams)

    def test_routine_h1_interpreter_does_not_route_precedent(self):
        fams, issues = self.families("H-1 비자로 통역 아르바이트를 할 수 있나요?")
        self.assertNotIn("precedent", fams)
        self.assertNotIn("denial_revocation_or_remedy", issues)
        self.assertNotIn("constitutional_or_fundamental_rights", issues)

    def test_c3_paid_work_violation_remedy_routes_statute_appeal_precedent(self):
        fams, issues = self.families("C-3 단기방문으로 유급 근무를 하다 적발되면 행정심판으로 구제받을 수 있나요?")
        self.assertIn("denial_revocation_or_remedy", issues)
        self.assertIn("statute", fams)
        self.assertIn("administrative_appeal", fams)
        self.assertIn("precedent", fams)

    def test_every_issue_still_routes_to_a_family(self):
        for issue in LEGAL_ISSUE_TYPES:
            self.assertTrue(route_source_families([issue]), issue)

    def test_simple_registration_does_not_route_case_law(self):
        fams, _ = self.families("H-1 외국인등록은 언제 해야 하나요?")
        self.assertNotIn("precedent", fams)
        self.assertNotIn("constitutional_decision", fams)


# ---------------------------------------------------------------------------
# 5. Fixture-based normalizers
# ---------------------------------------------------------------------------
class NormalizerTests(unittest.TestCase):
    def test_precedent_list_fixture_normalizes(self):
        env = ps.normalize_precedent_list_response(fixture("precedent_list.json"))
        self.assertEqual(env["status"], "results_found")
        self.assertEqual(env["publicStatus"], "available")
        self.assertGreaterEqual(env["itemCount"], 2)
        item = env["items"][0]
        self.assertEqual(item["sourceFamily"], "precedent")
        self.assertEqual(item["resultKind"], "list_result")
        self.assertEqual(item["caseNumber"], "2018두12345")
        self.assertEqual(item["courtOrAgency"], "대법원")
        # A list result (no body) is contextual, never a direct citation.
        self.assertEqual(item["citationGrade"], "contextual")
        self.assertFalse(item["quoteSafe"])

    def test_precedent_body_fixture_is_direct_and_quotable(self):
        env = ps.normalize_precedent_body_response(fixture("precedent_body.json"))
        self.assertEqual(env["status"], "results_found")
        item = env["items"][0]
        self.assertEqual(item["resultKind"], "body_result")
        self.assertEqual(item["citationGrade"], "direct")
        self.assertTrue(item["quoteSafe"])
        self.assertTrue(item["holdingSummary"])

    def test_admin_appeal_fixture_normalizes(self):
        env = ps.normalize_source_family_response("administrative_appeal", fixture("administrative_appeal_list.json"))
        self.assertEqual(env["status"], "results_found")
        item = env["items"][0]
        self.assertEqual(item["sourceFamily"], "administrative_appeal")
        self.assertEqual(item["decisionNumber"], "2021-09876")
        self.assertEqual(item["courtOrAgency"], "중앙행정심판위원회")

    def test_legal_interpretation_fixture_normalizes(self):
        env = ps.normalize_source_family_response("legal_interpretation", fixture("legal_interpretation_list.json"))
        self.assertEqual(env["status"], "results_found")
        item = env["items"][0]
        self.assertEqual(item["sourceFamily"], "legal_interpretation")
        self.assertEqual(item["courtOrAgency"], "법제처")

    def test_constitutional_decision_fixture_normalizes(self):
        env = ps.normalize_source_family_response("constitutional_decision", fixture("constitutional_decision_list.json"))
        self.assertEqual(env["status"], "results_found")
        item = env["items"][0]
        self.assertEqual(item["sourceFamily"], "constitutional_decision")
        self.assertEqual(item["caseNumber"], "2015헌마1234")
        self.assertEqual(item["courtOrAgency"], "헌법재판소 전원재판부")

    def test_unidentified_text_is_not_citation_grade(self):
        # An object with only a title (no case number, no court) cannot be a
        # citation-grade precedent — it downgrades to background.
        item = ps.normalize_precedent_list_item({"사건명": "제목만 있는 항목"})
        self.assertIsNotNone(item)
        self.assertEqual(item["citationGrade"], "background")
        self.assertFalse(item["quoteSafe"])


# ---------------------------------------------------------------------------
# 6. Public-safe unavailable status
# ---------------------------------------------------------------------------
class PublicSafeStatusTests(unittest.TestCase):
    def test_official_error_fixture_is_public_safe(self):
        env = ps.normalize_precedent_list_response(fixture("official_error.json"))
        self.assertEqual(env["status"], "official_error")
        self.assertEqual(env["publicStatus"], "temporarily_unavailable")
        self.assertEqual(env["items"][0]["resultKind"], "unavailable")

    def test_html_response_is_public_safe_no_leak(self):
        env = ps.normalize_precedent_list_response(fixture("html_service_page.txt"))
        self.assertEqual(env["status"], "bad_response")
        self.assertEqual(env["publicStatus"], "unavailable")
        dumped = json.dumps(env, ensure_ascii=False)
        self.assertNotIn("secret-session-token", dumped)
        self.assertNotIn("<html", dumped.lower())

    def test_not_configured_when_no_credential(self):
        env = ps.search_precedents("판례", config=GroundingConfig(mode="audit"))
        self.assertEqual(env["status"], "not_configured")
        self.assertEqual(env["publicStatus"], "unavailable")

    def test_timeout_is_temporarily_unavailable(self):
        def boom(url, timeout):
            return lt.LawHttpResponse(ok=False, error_type="timeout")
        env = ps.search_precedents("판례", config=_audit_oc_cfg(), transport=boom)
        self.assertEqual(env["publicStatus"], "temporarily_unavailable")

    def test_routed_precedent_projects_public_safe_no_raw_codes(self):
        q = "체류 연장 불허 처분을 행정심판으로 다툴 수 있나요?"
        facts = extract_immigration_facts(q)
        issues = classify_legal_issue_types(q, facts)
        plan = build_generalized_source_plan(q, facts, issues, law_api_attempted=True)
        self.assertIn("precedent", plan["source_families_planned"])
        attempts = normalize_law_source_attempts(
            law_sources=[], source_family_statuses=plan["source_family_statuses"],
        )
        pub = project_public_source_status(attempts, lang="ko")
        dumped = json.dumps(pub, ensure_ascii=False)
        for code in _RAW_CODES:
            self.assertNotIn(code, dumped)
        prec = [s for s in pub["sources"] if s["family"] == "precedent"]
        self.assertTrue(prec)
        self.assertEqual(prec[0]["publicStatus"], "unavailable")


# ---------------------------------------------------------------------------
# 7. Citation verifier hardening
# ---------------------------------------------------------------------------
class CitationVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prec_direct = ps.normalize_precedent_body_response(fixture("precedent_body.json"))["items"][0]
        cls.prec_list = ps.normalize_precedent_list_response(fixture("precedent_list.json"))["items"][0]
        cls.appeal = ps.normalize_source_family_response("administrative_appeal", fixture("administrative_appeal_list.json"))["items"][0]
        cls.interp = ps.normalize_source_family_response("legal_interpretation", fixture("legal_interpretation_list.json"))["items"][0]
        cls.const = ps.normalize_source_family_response("constitutional_decision", fixture("constitutional_decision_list.json"))["items"][0]

    # ---- fabricated citations fail ----
    def test_fake_precedent_citation_fails(self):
        r = verify_case_decision_citations("대법원 2099두99999 판결에 따르면 가능합니다.", [])
        self.assertEqual(r["status"], "failed")
        self.assertIn("FABRICATED_CASE_CITATION", r["warnings"])

    def test_fake_admin_appeal_citation_fails(self):
        r = verify_case_decision_citations("행정심판 재결(2099-99999)에서 인용 판단되었습니다.", [])
        self.assertEqual(r["status"], "failed")

    def test_fake_constitutional_citation_fails(self):
        r = verify_case_decision_citations("헌법재판소 2099헌마9999 결정에 따르면 위헌입니다.", [])
        self.assertEqual(r["status"], "failed")

    def test_fake_legal_interpretation_citation_fails(self):
        r = verify_case_decision_citations("법령해석례에 따르면 반드시 허용됩니다.", [])
        self.assertEqual(r["status"], "failed")
        self.assertIn("UNSUPPORTED_ADJUDICATIVE_AUTHORITY", r["warnings"])

    # ---- fixture-backed citations pass ----
    def test_verified_precedent_passes(self):
        r = verify_case_decision_citations("관련 판례(2018두12345, 대법원)를 참고할 수 있습니다.", [self.prec_list])
        self.assertEqual(r["status"], "verified")

    def test_verified_admin_appeal_passes(self):
        r = verify_case_decision_citations("행정심판 재결(2021-09876)에서 인용 판단된 사례가 있습니다.", [self.appeal])
        self.assertEqual(r["status"], "verified")

    def test_verified_constitutional_passes(self):
        r = verify_case_decision_citations("헌법재판소 2015헌마1234 결정이 참고됩니다.", [self.const])
        self.assertEqual(r["status"], "verified")

    # ---- quote handling ----
    def test_quote_mismatch_fails(self):
        r = verify_case_decision_citations(
            "대법원 2018두12345 판결은 \"실제로 존재하지 않는 인용 문장입니다\"라고 판시하였습니다.",
            [self.prec_direct],
        )
        self.assertEqual(r["status"], "failed")
        self.assertIn("QUOTE_MISMATCH", r["warnings"])

    def test_quote_match_passes(self):
        r = verify_case_decision_citations(
            "대법원 2018두12345 판결은 \"재량권을 일탈·남용한 경우에는 위법하다\" 부분을 판시.",
            [self.prec_direct],
        )
        self.assertEqual(r["status"], "verified")

    # ---- contextual cannot support direct/binding wording ----
    def test_contextual_only_cannot_support_binding_wording(self):
        r = verify_case_decision_citations("확립된 판례 2018두12345에 따르면 반드시 취소됩니다.", [self.prec_list])
        self.assertEqual(r["status"], "failed")
        self.assertIn("CONTEXTUAL_EVIDENCE_OVERCLAIMED", r["warnings"])

    # ---- procedure mentions are not authority claims ----
    def test_procedure_mention_is_not_flagged(self):
        r = verify_case_decision_citations("불허 처분을 받으면 행정심판을 청구할 수 있습니다.", [])
        self.assertEqual(r["status"], "no_citations")
        self.assertEqual(r["warnings"], [])

    def test_extract_only_when_evidence_is_none(self):
        r = verify_case_decision_citations("대법원 2099두99999", None)
        self.assertEqual(r["status"], "extracted_only")

    # ---- invented citation in a model-style answer is rejected ----
    def test_invented_case_in_model_answer_is_rejected(self):
        answer = (
            "결론: 가능합니다.\n"
            "근거: 대법원 2099두12345 판결과 헌법재판소 2099헌마1 결정에 따르면 허용됩니다."
        )
        r = verify_case_decision_citations(answer, [])  # no evidence retrieved
        self.assertEqual(r["status"], "failed")
        self.assertIn("FABRICATED_CASE_CITATION", r["warnings"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
