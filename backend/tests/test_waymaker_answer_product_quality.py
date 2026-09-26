"""Waymaker answer product-quality regressions (D-2 document lookup).

Production showed, for "D-2 연장시 필수 서류" with Fast selected:

* the provider and exact model id in the answer header,
* ``source file 2026-06-23`` (internal revision metadata) in the answer prose,
  because ``_build_grounded_prompt`` told the model to cite it,
* raw ``### 필수 서류`` Markdown,
* a free-form model checklist instead of the canonical manual list.

These tests pin the repaired contract: the checklist comes from canonical
grounding data (the model may only phrase a short summary), the ordinary
``/api/ask`` response is a public projection without provider/model/routing
fields or internal source metadata, diagnostics stay available through an
explicit opt-in, and a simple document question stays on Fast.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any, Dict, List
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import paradiso_backend as pb  # noqa: E402
from services import structured_answer as sa  # noqa: E402
from services.model_policy import resolve_answer_mode_models  # noqa: E402

D2_QUERIES = ("D-2 연장시 필수 서류", "D-2 연장에 필요한 서류는?", "D-2 체류기간 연장 시 필수 서류는 무엇인가요?")
VENDOR_TERMS = ("openrouter", "groq", "ollama", "nemotron", "gemma", "nvidia", "inkling", "thinkingmachines")
INTERNAL_METADATA_TERMS = ("source file", "source_file", "source_revision_date", "grounding packet", "fixture")

# What a real free-tier model produced in production: headings, a re-derived
# checklist, the internal source-file citation and an invented document.
LEAKY_MODEL_ANSWER = (
    "유학(D-2) 체류기간 연장허가 신청 시 제출해야 할 서류는 아래와 같습니다"
    "(외국인체류 안내매뉴얼 2026.6; source file 2026-06-23, pp. 43-44).\n\n"
    "### 필수 서류\n- 신청서\n- 여권\n- 외국인등록증\n- 수수료\n- 건강진단서\n\n"
    "### 조건부·증빙 서류\n- 재정입증 서류\n\n"
    "출처: 외국인체류 안내매뉴얼 (2026.6; source file 2026-06-23)"
)


def _provider_ok(answer: str, candidates: List[str]) -> Dict[str, Any]:
    model = candidates[0]
    return {
        "ok": True, "answer": answer, "primary_model": model, "requested_model": None,
        "model_candidates": list(candidates), "attempted_models": [model],
        "skipped_models_due_to_cooldown": [], "cooling_down_models": [],
        "model_cooldown_seconds": 0, "cooldown_enabled": False, "final_model": model,
        "model_fallback_used": False, "provider_error_type": None, "upstream_statuses": [],
        "retryable_provider_error": False, "all_candidates_failed": False,
    }


class _AskHarness(unittest.TestCase):
    answer_text = LEAKY_MODEL_ANSWER

    def _ask(self, question: str, *, mode: str = "fast", lang: str = "ko", headers=None, **extra):
        calls: List[Dict[str, Any]] = []

        async def fake(prompt, requested_model=None, candidate_models=None, max_tokens=None, **kw):
            calls.append({"prompt": prompt, "candidates": list(candidate_models or [])})
            return _provider_ok(self.answer_text, list(candidate_models or ["test/model"]))

        with patch.object(pb, "OPENROUTER_API_KEY", "sk-test-sentinel"), \
                patch.object(pb, "_openrouter_complete_with_candidates", fake):
            client = TestClient(pb.app, headers=headers or {})
            resp = client.post("/api/ask", json={
                "question": question, "consent": True, "lang": lang,
                "answer_mode": mode, "stream": False, **extra,
            })
        return resp, calls


class D2StructuredDocumentAnswerTests(_AskHarness):
    def _canonical_d2(self):
        bundle = pb._load_stay_manual_grounding() or {}
        return next(g for g in bundle["groundings"] if g["visa_code"] == "D-2")

    def test_d2_document_answer_is_structured_from_canonical_data(self):
        canonical = self._canonical_d2()["required_documents"]
        for question in D2_QUERIES:
            with self.subTest(question=question):
                resp, _ = self._ask(question)
                self.assertEqual(resp.status_code, 200, resp.text)
                body = resp.json()
                self.assertEqual(body["visa_code_detected"], "D-2")
                self.assertEqual(body["task_type_detected"], "extension")
                self.assertIn("documents_needed", body["legal_issue_types"])
                self.assertEqual(body["answer_quality_mode"], "source_confirmed")
                structured = body["structured_answer"]
                self.assertEqual(structured["kind"], "documents")
                docs = structured["required_documents"]
                self.assertEqual([d["label"] for d in docs["common"]], ["신청서", "여권", "외국인등록증", "수수료"])
                self.assertEqual(len(docs["conditional"]), 1)
                self.assertIn("수료증명서", docs["conditional"][0]["label"])
                self.assertIn("재정입증 서류", [d["label"] for d in docs["required"]])
                # Every rendered document comes from the canonical list, in
                # full, with nothing added (the model's "건강진단서" is gone).
                rendered = [d["source_text"] for bucket in docs.values() for d in bucket]
                self.assertEqual(sorted(rendered), sorted(canonical))
                self.assertNotIn("건강진단서", json.dumps(structured, ensure_ascii=False))
                self.assertNotIn("건강진단서", body["answer"])
                # Canonical public citation.
                self.assertEqual(structured["source"]["title"], "외국인체류 안내매뉴얼")
                self.assertEqual(structured["source"]["edition"], "2026.6")
                self.assertEqual(structured["source"]["page_range"], "43-44")
                self.assertTrue(structured["source"]["verified"])

    def test_model_summary_is_prose_only_and_cleaned(self):
        resp, _ = self._ask("D-2 연장시 필수 서류")
        structured = resp.json()["structured_answer"]
        self.assertEqual(structured["short_answer_source"], "model_summary")
        summary = structured["short_answer"]
        self.assertTrue(summary.startswith("유학(D-2) 체류기간 연장허가"))
        self.assertNotIn("###", summary)
        self.assertNotIn("source file", summary)
        self.assertNotIn("안내매뉴얼", summary)  # citation lives in the source card

    def test_heading_only_model_answer_falls_back_to_deterministic_summary(self):
        self.answer_text = "### 필수 서류\n- 신청서\n- 여권"
        try:
            resp, _ = self._ask("D-2 연장시 필수 서류")
        finally:
            self.answer_text = LEAKY_MODEL_ANSWER
        structured = resp.json()["structured_answer"]
        self.assertEqual(structured["short_answer_source"], "deterministic")
        self.assertIn("기본 서류 4종", structured["short_answer"])

    def test_structured_answer_localizes_product_copy(self):
        for lang, needle in (("en", "basic documents"), ("zh-CN", "基本材料"), ("zh-TW", "基本材料")):
            with self.subTest(lang=lang):
                self.answer_text = "### Documents\n- 신청서"
                try:
                    resp, _ = self._ask("D-2 연장시 필수 서류", lang=lang)
                finally:
                    self.answer_text = LEAKY_MODEL_ANSWER
                self.assertIn(needle, resp.json()["structured_answer"]["short_answer"])

    def test_complex_question_keeps_free_form_answer(self):
        resp, _ = self._ask("D-2 연장 서류랑 체류자격 변경 가능한지도 알려줘")
        self.assertIsNone(resp.json().get("structured_answer"))

    def test_all_candidates_failed_still_shows_canonical_checklist(self):
        async def failing(prompt, requested_model=None, candidate_models=None, max_tokens=None, **kw):
            return {**_provider_ok("", list(candidate_models or ["x"])), "ok": False, "answer": None,
                    "final_model": None, "provider_error_type": "rate_limited",
                    "retryable_provider_error": True, "all_candidates_failed": True}

        with patch.object(pb, "OPENROUTER_API_KEY", "sk-test-sentinel"), \
                patch.object(pb, "ENABLE_OLLAMA_FALLBACK", False), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", False), \
                patch.object(pb, "_openrouter_complete_with_candidates", failing):
            resp = TestClient(pb.app).post("/api/ask", json={"question": "D-2 연장시 필수 서류", "answer_mode": "fast", "stream": False})
        body = resp.json()
        self.assertTrue(body["deterministic_fallback_answer_used"])
        self.assertEqual(body["fallback_answer_kind"], "structured_document_checklist")
        self.assertIn("외국인등록증", body["answer"])
        lowered = resp.text.lower()
        for term in VENDOR_TERMS + ("fallback_answer_reason",):
            self.assertNotIn(term, lowered)


class StructuredBucketingTests(unittest.TestCase):
    """Deterministic bucketing over every source-confirmed manual grounding."""

    @classmethod
    def setUpClass(cls):
        cls.bundle = pb._load_stay_manual_grounding() or {}
        cls.by_code = {g["visa_code"]: g for g in cls.bundle["groundings"]}

    def _build(self, code):
        return sa.build_document_answer(grounding=self.by_code[code], bundle=self.bundle, lang="ko")

    def test_every_grounding_keeps_exact_canonical_membership(self):
        for code, grounding in self.by_code.items():
            with self.subTest(code=code):
                docs = self._build(code)["required_documents"]
                rendered = [d["source_text"] for bucket in docs.values() for d in bucket]
                self.assertEqual(sorted(rendered), sorted(" ".join(x.split()) for x in grounding["required_documents"]))

    def test_subcode_scoped_list_always_carries_its_scope(self):
        d4 = self._build("D-4")
        self.assertIn("D-4-1", d4["source"]["scope"])
        self.assertIn("D-4-7", d4["source"]["scope"])
        self.assertEqual(self._build("D-2")["source"]["scope"], "")

    def test_form_numbered_application_is_a_basic_document(self):
        e7 = self._build("E-7")["required_documents"]
        self.assertIn("신청서 (별지 34호 서식)", [d["label"] for d in e7["common"]])
        self.assertTrue(any("신원보증서" in d["label"] for d in e7["conditional"]))


class InternalMetadataLeakTests(_AskHarness):
    def test_grounded_prompt_never_hands_the_model_internal_revision_metadata(self):
        _, calls = self._ask("D-2 연장시 필수 서류")
        prompt = calls[0]["prompt"]
        self.assertNotIn("source file", prompt)
        self.assertNotIn("2026-06-23", prompt)
        self.assertIn("외국인체류 안내매뉴얼", prompt)

    def test_public_answer_has_no_internal_metadata(self):
        resp, _ = self._ask("D-2 연장시 필수 서류")
        body = resp.json()
        for field in ("answer", "copy_safe_answer"):
            for term in INTERNAL_METADATA_TERMS:
                self.assertNotIn(term, body[field].lower(), f"{field} leaks {term!r}")
        lowered = resp.text.lower()
        for term in ("source_file", "source_revision_date", "source file", "pypdf", ".pdf", "law_evidence_pack"):
            self.assertNotIn(term, lowered)

    def test_scrubber_removes_free_form_source_file_citations(self):
        cleaned = sa.scrub_internal_metadata("안내(외국인체류 안내매뉴얼 2026.6; source file 2026-06-23).\n출처 파일: source_file=x.pdf")
        self.assertEqual(cleaned, "안내(외국인체류 안내매뉴얼 2026.6).")
        self.assertFalse(sa.contains_internal_metadata(cleaned))


class PublicProjectionTests(_AskHarness):
    def test_ordinary_response_has_no_provider_or_model_identity(self):
        resp, _ = self._ask("D-2 연장시 필수 서류")
        body = resp.json()
        for key in pb.ASK_INTERNAL_ROUTING_FIELDS:
            self.assertNotIn(key, body)
        lowered = resp.text.lower()
        for term in VENDOR_TERMS:
            self.assertNotIn(term, lowered)

    def test_copy_safe_answer_is_clean_plain_text(self):
        body = self._ask("D-2 연장시 필수 서류")[0].json()
        copy = body["copy_safe_answer"]
        self.assertNotRegex(copy, r"(?m)^\s*#{1,6}\s")
        self.assertNotIn("**", copy)
        self.assertIn("기본 서류\n• 신청서", copy)
        self.assertIn("출처\n외국인체류 안내매뉴얼 2026.6", copy)

    def test_explicit_diagnostics_keep_engineering_observability(self):
        resp, _ = self._ask("D-2 연장시 필수 서류", headers={"X-Paradiso-Diagnostics": "1"})
        body = resp.json()
        fast = resolve_answer_mode_models("fast")
        self.assertEqual(body["provider"], "openrouter")
        self.assertEqual(body["final_model"], fast["primary"])
        self.assertEqual(body["model_candidates"], fast["candidates"])
        self.assertIn("law_evidence_pack", body)

    def test_body_flag_also_opts_into_diagnostics(self):
        resp, _ = self._ask("D-2 연장시 필수 서류", diagnostics=True)
        self.assertIn("final_model", resp.json())

    def test_operator_can_refuse_client_diagnostics(self):
        with patch.dict(os.environ, {"PARADISO_CLIENT_DIAGNOSTICS": "0"}):
            resp, _ = self._ask("D-2 연장시 필수 서류", headers={"X-Paradiso-Diagnostics": "1"})
        self.assertNotIn("final_model", resp.json())

    def test_routing_telemetry_is_logged_server_side(self):
        with self.assertLogs("paradiso.backend", level="INFO") as logs:
            self._ask("D-2 연장시 필수 서류")
        record = next(line for line in logs.output if "ask_routing" in line)
        data = json.loads(record.split("ask_routing ", 1)[1])
        fast = resolve_answer_mode_models("fast")
        self.assertEqual(data["answer_mode_requested"], "fast")
        self.assertEqual(data["answer_mode_effective"], "fast")
        self.assertFalse(data["answer_mode_auto_escalated"])
        self.assertEqual(data["final_model"], fast["primary"])
        self.assertTrue(data["structured_answer"])
        self.assertNotIn("sk-test-sentinel", record)

    def test_error_envelope_does_not_name_a_vendor(self):
        # A model-dependent question (no structured answer): the D-2 document
        # lookup itself is answerable without a provider (see
        # test_waymaker_structured_answer_provider_failure.py).
        with patch.object(pb, "OPENROUTER_API_KEY", None), patch.object(pb, "GROQ_API_KEY", None):
            resp = TestClient(pb.app).post("/api/ask", json={"question": "D-4 자격 신청에 필요한 학력 증빙은 무엇인가요?"})
        self.assertEqual(resp.status_code, 503)
        detail = resp.json()["detail"]
        self.assertEqual(detail["error"], "no_llm_provider_configured")
        for term in VENDOR_TERMS:
            self.assertNotIn(term, resp.text.lower())

    def test_stream_frames_are_projected(self):
        async def fake_stream(prompt, model, max_tokens=None):
            yield "D-2 연장에는 기본 서류가 필요합니다."

        with patch.object(pb, "OPENROUTER_API_KEY", "sk-test-sentinel"), \
                patch.object(pb, "_stream_openrouter_text", fake_stream):
            resp = TestClient(pb.app).post("/api/ask", json={"question": "D-2 연장시 필수 서류", "answer_mode": "fast", "stream": True})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("event: model", resp.text)
        lowered = resp.text.lower()
        for term in VENDOR_TERMS + ("final_model", "selected_model", "attempted_models"):
            self.assertNotIn(term, lowered)


class FastRoutingTests(_AskHarness):
    SIMPLE_DOCUMENT_QUESTIONS = D2_QUERIES + (
        "What documents do I need to extend a D-2?",
        "D-2 延期需要哪些材料？",
        "D-4 연장 서류",
        "E-7 연장에 필요한 서류는?",
    )

    def test_simple_document_questions_stay_fast(self):
        fast = resolve_answer_mode_models("fast")
        for question in self.SIMPLE_DOCUMENT_QUESTIONS:
            with self.subTest(question=question):
                resp, calls = self._ask(question, mode="fast")
                body = resp.json()
                self.assertEqual(body["answer_mode_requested"], "fast")
                self.assertEqual(body["answer_mode"], "fast")
                self.assertFalse(body["answer_mode_auto_escalated"])
                self.assertEqual(body["answer_mode_escalation_reasons"], [])
                # The Fast candidate chain was used (policy-agnostic check).
                self.assertEqual(calls[0]["candidates"], fast["candidates"])

    def test_basic_stays_basic_and_uses_basic_chain(self):
        resp, calls = self._ask("D-2 연장시 필수 서류", mode="basic")
        body = resp.json()
        self.assertEqual((body["answer_mode_requested"], body["answer_mode"]), ("basic", "basic"))
        self.assertEqual(calls[0]["candidates"], resolve_answer_mode_models("basic")["candidates"])

    def test_genuinely_complex_fast_question_still_escalates_with_public_reason(self):
        resp, _ = self._ask("D-2인데 체류자격 변경 불허 처분을 받았습니다. 행정심판 판례가 있나요?", mode="fast")
        body = resp.json()
        self.assertTrue(body["answer_mode_auto_escalated"])
        self.assertEqual(body["answer_mode"], "basic")
        self.assertTrue(body["answer_mode_escalation_reasons"])


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FrontendContractTests(unittest.TestCase):
    """Static guards on the public Waymaker surfaces (ai.html, index.html)."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO_ROOT, "ai.html"), encoding="utf-8") as fh:
            cls.ai = fh.read()
        with open(os.path.join(REPO_ROOT, "index.html"), encoding="utf-8") as fh:
            cls.index = fh.read()

    def test_no_public_model_label_renderers(self):
        for html in (self.ai, self.index):
            self.assertNotIn("function getModelLabel", html)
            self.assertNotIn("function getModelBadge", html)
            self.assertNotIn("function buildModelBadgeHtml", html)
            self.assertNotIn("`OpenRouter · ${", html)
            self.assertNotIn("`Groq · ${", html)

    def test_structured_template_is_wired_to_the_answer_renderer(self):
        self.assertIn('<template id="pa-answer-card-shell">', self.ai)
        self.assertIn("getElementById('pa-answer-card-shell')", self.ai)
        render = self.ai.split("function appendAiAnswer(", 1)[1].split("// Client-side error classification", 1)[0]
        self.assertIn("renderStructuredAnswer(structured, lang)", render)
        self.assertIn("structuredAnswerPlainText(structured, lang)", render)
        self.assertNotIn("model_resolved", render)

    def test_diagnostics_are_requested_only_in_developer_mode(self):
        self.assertIn("diagnostics: isDevDiagnosticsEnabled() || undefined", self.ai)
        self.assertIn("diagnostics: isAiDevDiagnosticsEnabled() || undefined", self.index)

    def test_mode_selector_uses_product_labels_not_models(self):
        selector = self.ai.split('id="aiModeSelector"', 1)[1].split("</div>", 1)[0]
        self.assertIn("빠른 답변", selector)
        self.assertIn("정밀 답변", selector)
        self.assertIn('data-mode="fast"', selector)
        self.assertIn('data-mode="basic"', selector)
        for term in VENDOR_TERMS:
            self.assertNotIn(term, selector.lower())


class BrowserFixtureDriftTests(unittest.TestCase):
    def test_committed_waymaker_fixtures_match_the_backend(self):
        import subprocess
        script = os.path.join(REPO_ROOT, "scripts", "build_waymaker_answer_fixtures.py")
        run = subprocess.run([sys.executable, script, "--check"], capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
