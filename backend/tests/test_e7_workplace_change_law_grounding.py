"""Regression tests for the E-7 workplace-change / job-transfer reliability and
legal-grounding safety work.

Covers:
  * The exact E-7 job-transfer question triggers law grounding and classifies
    workplace_change_addition / extension / employment_condition /
    status_purpose_alignment.
  * The law-search query is built around official workplace-change anchors
    (never relying on the model to invent article numbers).
  * derive_law_grounding_status_detail maps every runtime state to the six
    user-visible statuses, and only ``verified`` is treated as trustworthy.
  * The unverified-citation guardrail: a hallucinated 조문 citation is flagged
    and a notice is prepended unless grounding is verified or the citation is
    backed by local evidence.
  * Fast mode selects OPENROUTER_FAST_MODEL first; Basic selects OPENROUTER_MODEL
    first; the verifier model is never a default answer primary; Fast fallback is
    explicit and visible.
  * /api/ask surfaces law_grounding_status_detail + selected_model and applies
    the citation guard on the buffered path.

Run:
    python3 -m unittest backend.tests.test_e7_workplace_change_law_grounding
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

E7_QUESTION = (
    "E-7 체류자격자가 퇴사 후 동종업계 다른 회사로 이직하는 경우, 출입국관리법과 "
    "시행령상 근무처 변경허가 또는 신고가 필요한지 법적 근거와 함께 설명해줘."
)

# The kind of confident, fabricated citation the model produced in the bug report.
HALLUCINATED_ANSWER = (
    "출입국관리법 제24조 제1항 및 출입국관리법 시행규칙 제18조의2(별표 1)에 따라 "
    "근무처 변경허가가 필요합니다. 동종업계 이직도 신고 대상입니다."
)

_MODEL_ENV_KEYS = (
    "OPENROUTER_MODEL",
    "OPENROUTER_MODEL_CANDIDATES",
    "OPENROUTER_FAST_MODEL",
    "OPENROUTER_FAST_MODEL_CANDIDATES",
)


class E7IntentAndQueryTests(unittest.TestCase):
    def setUp(self):
        for key in ("LAW_GROUNDING_MODE", "LAW_API_OC", "LAW_API_KEY"):
            os.environ.pop(key, None)

    def test_exact_question_triggers_law_grounding(self):
        from services.law_grounding import should_attempt_law_grounding

        intent = should_attempt_law_grounding(E7_QUESTION)
        self.assertTrue(intent["should_attempt"])
        self.assertIn("근무처변경/이직", intent["reasons"])

    def test_job_transfer_vocabulary_triggers_without_explicit_legal_wording(self):
        from services.law_grounding import should_attempt_law_grounding

        # No 출입국관리법 / 법적 근거 wording — must still trigger off 이직/다른 회사.
        q = "E-7인데 다른 회사로 이직하면 근무처 변경 신고를 해야 하나요?"
        intent = should_attempt_law_grounding(q)
        self.assertTrue(intent["should_attempt"])
        self.assertIn("근무처변경/이직", intent["reasons"])

    def test_each_required_term_triggers(self):
        from services.law_grounding import should_attempt_law_grounding

        for term in ("퇴사", "이직", "전직", "동종업계", "다른 회사", "타 회사",
                     "새 회사", "고용주 변경", "사업주 변경", "근무처 변경",
                     "근무처 추가", "특정활동", "연장허가"):
            with self.subTest(term=term):
                intent = should_attempt_law_grounding(f"E-7 {term} 관련 질문입니다")
                self.assertTrue(intent["should_attempt"], term)

    def test_query_uses_official_workplace_change_anchors(self):
        from services.law_grounding import build_law_search_query, should_attempt_law_grounding

        reasons = should_attempt_law_grounding(E7_QUESTION)["reasons"]
        query = build_law_search_query(E7_QUESTION, reasons)
        for anchor in (
            "출입국관리법 근무처 변경 추가 허가",
            "출입국관리법 근무처 변경 추가 신고",
            "출입국관리법 시행령 근무처 변경 추가",
            "특정활동 E-7 근무처 변경 추가 허가 신고",
            "체류기간 연장허가 근무처 변경",
        ):
            self.assertIn(anchor, query, anchor)


class E7IssueClassificationTests(unittest.TestCase):
    def test_classifies_required_issue_types(self):
        from services.legal_analysis import (
            classify_legal_issue_types,
            extract_immigration_facts,
        )

        facts = extract_immigration_facts(E7_QUESTION, visa_code="E-7")
        issues = set(classify_legal_issue_types(E7_QUESTION, facts))
        for required in (
            "workplace_change_addition",
            "extension",
            "employment_condition",
            "status_purpose_alignment",
        ):
            self.assertIn(required, issues, required)

    def test_employment_condition_is_a_known_ontology_dimension(self):
        # New issue type must be understood by the rest of the pipeline, not a
        # free-floating string (CLAUDE.md: no schema the backend doesn't know).
        from services.evidence_ontology import (
            LEGAL_ISSUE_DIMENSIONS,
            SOURCE_FAMILY_ROUTING,
            ISSUE_CONCEPT_KO,
            ISSUE_CONCEPT_EN,
        )
        from services.legal_analysis import LEGAL_ISSUE_TYPES

        self.assertIn("employment_condition", LEGAL_ISSUE_TYPES)
        self.assertIn("employment_condition", LEGAL_ISSUE_DIMENSIONS)
        self.assertIn("employment_condition", SOURCE_FAMILY_ROUTING)
        self.assertIn("employment_condition", ISSUE_CONCEPT_KO)
        self.assertIn("employment_condition", ISSUE_CONCEPT_EN)


class LawGroundingStatusDetailTests(unittest.TestCase):
    def _detail(self, **kw):
        from services.law_grounding import derive_law_grounding_status_detail

        base = dict(
            configured_mode="enabled",
            effective_mode="enabled",
            intent_attempted=True,
            lookup_attempted=True,
            lookup_used=False,
            error_type="",
            warnings=None,
        )
        base.update(kw)
        return derive_law_grounding_status_detail(**base)

    def test_not_attempted_when_no_intent(self):
        self.assertEqual(
            self._detail(intent_attempted=False), "law_grounding_not_attempted"
        )

    def test_disabled_mode(self):
        self.assertEqual(
            self._detail(configured_mode="disabled", effective_mode="disabled"),
            "law_grounding_disabled",
        )

    def test_enabled_without_credential_is_disabled(self):
        # The enabled-without-credential effective-disabled rule.
        self.assertEqual(
            self._detail(configured_mode="enabled", effective_mode="disabled"),
            "law_grounding_disabled",
        )

    def test_audit_only(self):
        self.assertEqual(
            self._detail(configured_mode="audit", effective_mode="audit", lookup_used=True),
            "law_grounding_audit_only",
        )

    def test_verified_when_used(self):
        self.assertEqual(self._detail(lookup_used=True), "law_grounding_verified")

    def test_attempted_no_results(self):
        self.assertEqual(
            self._detail(lookup_used=False, error_type="law_api_no_results"),
            "law_grounding_attempted_no_results",
        )

    def test_attempted_failed(self):
        self.assertEqual(
            self._detail(lookup_used=False, error_type="LAW_API_BAD_RESPONSE"),
            "law_grounding_attempted_failed",
        )

    def test_only_verified_is_trusted(self):
        from services.law_grounding import (
            law_grounding_status_detail_is_verified,
            LAW_GROUNDING_STATUS_DETAILS,
        )

        for status in LAW_GROUNDING_STATUS_DETAILS:
            trusted = law_grounding_status_detail_is_verified(status)
            self.assertEqual(trusted, status == "law_grounding_verified", status)


class CitationGuardTests(unittest.TestCase):
    def test_detects_article_and_attachment_citations(self):
        from services.law_citation_guard import detect_legal_article_citations

        found = detect_legal_article_citations(HALLUCINATED_ANSWER)
        self.assertIn("제24조제1항", found)
        self.assertIn("제18조의2", found)
        self.assertIn("별표1", found)

    def test_unverified_unsupported_citation_gets_notice(self):
        from services.law_citation_guard import guard_answer_citations

        out = guard_answer_citations(
            HALLUCINATED_ANSWER, law_grounding_verified=False, evidence_texts=[], lang="ko"
        )
        self.assertTrue(out["unverified_law_citation_detected"])
        self.assertEqual(out["law_citation_guard_action"], "notice_prepended")
        self.assertNotEqual(out["answer"], HALLUCINATED_ANSWER)
        self.assertIn("특정 조문 번호는 확정하지 않습니다", out["answer"])

    def test_verified_grounding_allows_citation(self):
        from services.law_citation_guard import guard_answer_citations

        out = guard_answer_citations(
            HALLUCINATED_ANSWER, law_grounding_verified=True, evidence_texts=[], lang="ko"
        )
        self.assertFalse(out["unverified_law_citation_detected"])
        self.assertEqual(out["answer"], HALLUCINATED_ANSWER)

    def test_local_evidence_backed_citation_allowed(self):
        from services.law_citation_guard import guard_answer_citations

        evidence = ["출입국관리법 제24조제1항 시행규칙 제18조의2 별표1 근무처 변경허가"]
        out = guard_answer_citations(
            HALLUCINATED_ANSWER, law_grounding_verified=False, evidence_texts=evidence, lang="ko"
        )
        self.assertFalse(out["unverified_law_citation_detected"])
        self.assertEqual(out["law_citation_guard_action"], "allowed_local_evidence")

    def test_no_citation_no_action(self):
        from services.law_citation_guard import guard_answer_citations

        out = guard_answer_citations(
            "근무처 변경허가 또는 신고가 필요할 수 있습니다.",
            law_grounding_verified=False,
            evidence_texts=[],
            lang="ko",
        )
        self.assertEqual(out["law_citation_guard_action"], "none")
        self.assertFalse(out["unverified_law_citation_detected"])

    def test_safety_directive_strict_when_unverified(self):
        from services.law_citation_guard import build_citation_safety_directive

        strict = build_citation_safety_directive(status_detail="law_grounding_disabled", lang="ko")
        self.assertIn("strict", strict)
        self.assertIn("Do NOT generate", strict)
        verified = build_citation_safety_directive(status_detail="law_grounding_verified", lang="ko")
        self.assertIn("VERIFIED", verified)


class FastBasicModelRoutingTests(unittest.TestCase):
    def setUp(self):
        for key in _MODEL_ENV_KEYS:
            os.environ.pop(key, None)

    def test_fast_uses_openrouter_fast_model_first(self):
        from services.model_policy import resolve_answer_mode_models

        os.environ["OPENROUTER_FAST_MODEL"] = "google/gemma-fast-test:free"
        self.addCleanup(lambda: os.environ.pop("OPENROUTER_FAST_MODEL", None))
        plan = resolve_answer_mode_models("fast")
        self.assertEqual(plan["mode"], "fast")
        self.assertEqual(plan["primary"], "google/gemma-fast-test:free")
        self.assertEqual(plan["candidates"][0], "google/gemma-fast-test:free")

    def test_basic_uses_openrouter_model_first(self):
        from services.model_policy import resolve_answer_mode_models

        os.environ["OPENROUTER_MODEL"] = "nous/basic-test:free"
        self.addCleanup(lambda: os.environ.pop("OPENROUTER_MODEL", None))
        plan = resolve_answer_mode_models("basic")
        self.assertEqual(plan["mode"], "basic")
        self.assertEqual(plan["primary"], "nous/basic-test:free")
        self.assertEqual(plan["candidates"][0], "nous/basic-test:free")

    def test_verifier_model_is_not_a_default_answer_primary(self):
        # The reported bug: both Fast and Basic answered with the verifier model
        # (openai/gpt-oss-120b:free). It must never be a default answer primary.
        from services.model_policy import (
            resolve_answer_mode_models,
            DEFAULT_VERIFIER_MODEL,
        )

        self.assertEqual(DEFAULT_VERIFIER_MODEL, "openai/gpt-oss-120b:free")
        self.assertNotEqual(resolve_answer_mode_models("fast")["primary"], DEFAULT_VERIFIER_MODEL)
        self.assertNotEqual(resolve_answer_mode_models("basic")["primary"], DEFAULT_VERIFIER_MODEL)

    def test_fast_independent_of_basic_model_env(self):
        # Setting OPENROUTER_MODEL (basic) must NOT change the fast primary.
        from services.model_policy import resolve_answer_mode_models, DEFAULT_FAST_ANSWER_MODEL

        os.environ["OPENROUTER_MODEL"] = "openai/gpt-oss-120b:free"
        self.addCleanup(lambda: os.environ.pop("OPENROUTER_MODEL", None))
        self.assertEqual(resolve_answer_mode_models("fast")["primary"], DEFAULT_FAST_ANSWER_MODEL)
        self.assertEqual(resolve_answer_mode_models("basic")["primary"], "openai/gpt-oss-120b:free")


class AskEndpointE7Tests(unittest.TestCase):
    """End-to-end /api/ask behavior with a mocked OpenRouter model."""

    def setUp(self):
        for key in ("LAW_GROUNDING_MODE", "LAW_API_OC", "LAW_API_KEY", *_MODEL_ENV_KEYS):
            os.environ.pop(key, None)

    def _pb_and_client(self):
        import importlib
        import paradiso_backend as pb
        from fastapi.testclient import TestClient

        importlib.reload(pb)  # re-read model env defaults clean
        return pb, TestClient(pb.app)

    def test_status_detail_surfaced_when_no_llm(self):
        # No LLM provider -> 503, but base_meta (incl. the new status detail) is in
        # the error detail. Law grounding defaults to enabled-without-credential
        # => effective disabled => law_grounding_disabled.
        pb, client = self._pb_and_client()
        resp = client.post("/api/ask", json={"question": E7_QUESTION})
        self.assertEqual(resp.status_code, 503, resp.text)
        detail = resp.json()["detail"]
        self.assertEqual(detail["law_grounding_status_detail"], "law_grounding_disabled")
        self.assertFalse(detail["law_grounding_verified"])
        self.assertTrue(detail["law_grounding_user_notice"])

    def test_buffered_answer_guards_hallucinated_citation_and_exposes_model(self):
        pb, client = self._pb_and_client()

        async def fake_complete(prompt, requested_model=None, candidate_models=None, max_tokens=None):
            candidates = list(candidate_models or [])
            return {
                "ok": True,
                "answer": HALLUCINATED_ANSWER,
                "primary_model": candidates[0] if candidates else "x",
                "requested_model": requested_model,
                "model_candidates": candidates,
                "attempted_models": candidates[:1],
                "skipped_models_due_to_cooldown": [],
                "cooling_down_models": [],
                "model_cooldown_seconds": 0,
                "cooldown_enabled": False,
                "final_model": candidates[0] if candidates else "x",
                "model_fallback_used": False,
                "provider_error_type": None,
                "upstream_statuses": [],
                "retryable_provider_error": False,
                "all_candidates_failed": False,
            }

        # Passthrough the shape gate so the hallucinated citation reaches the guard.
        def fake_gate(answer, meta, contract, **kw):
            return answer, {}

        with patch.object(pb, "OPENROUTER_API_KEY", "test-key"), \
             patch.object(pb, "_openrouter_complete_with_candidates", new=fake_complete), \
             patch.object(pb, "_apply_answer_shape_gate", new=fake_gate):
            resp = client.post(
                "/api/ask",
                json={"question": E7_QUESTION, "answer_mode": "basic", "stream": False},
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        # Not verified -> hallucinated citation flagged + notice prepended.
        self.assertEqual(body["law_grounding_status_detail"], "law_grounding_disabled")
        self.assertTrue(body["unverified_law_citation_detected"])
        self.assertIn("특정 조문 번호는 확정하지 않습니다", body["answer"])
        # Model routing is auditable.
        self.assertTrue(body["selected_model"])
        self.assertEqual(body["selected_model"], body["final_model"])
        self.assertEqual(body["answer_mode"], "basic")


if __name__ == "__main__":
    unittest.main()
