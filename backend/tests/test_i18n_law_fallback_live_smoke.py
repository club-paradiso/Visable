"""Deterministic coverage for the i18n + law-grounding-fallback + provider/Groq
strictness + provider-aware live-smoke hardening pass (2026-05).

Mix of:
  * backend behavior tests (FastAPI TestClient, no provider configured so
    /api/ask returns its safe 503 with metadata in `detail`);
  * provider/model resolution + /health tests;
  * static checks against index.html, scripts/check_i18n.js (run as a
    subprocess against a fixture), scripts/smoke_ai_live_quality.py, and the
    PR documentation.

No live LLM/law-API calls are made; no secrets are read or printed.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
INDEX = REPO_ROOT / "index.html"
CHECK_I18N = REPO_ROOT / "scripts" / "check_i18n.js"
CHECK_I18N_COVERAGE = REPO_ROOT / "scripts" / "check_i18n_coverage.mjs"
CHECK_I18N_HARDCODED = REPO_ROOT / "scripts" / "check_index_hardcoded_text.mjs"
SMOKE = REPO_ROOT / "scripts" / "smoke_ai_live_quality.py"
DOC = REPO_ROOT / "docs" / "data" / "I18N_LAW_FALLBACK_LIVE_SMOKE_2026_05.md"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_pack_support import SUPPORTED_LOCALES, load_packs, localized, pack_blobs  # noqa: E402

# Localized UI copy now lives in external per-locale JSON packs (data/i18n/*.json);
# the inline check_i18n guard was split into scripts/check_i18n_coverage.mjs (strict
# cross-locale parity) and scripts/check_index_hardcoded_text.mjs (inline-leak
# scanner). Supported display locales are ko, en, zh-CN (zh-Hant aliases to zh-CN).


def _client():
    """A TestClient with no LLM provider configured (so /api/ask returns 503)."""
    for key in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
        os.environ.pop(key, None)
    from fastapi.testclient import TestClient  # type: ignore

    import paradiso_backend  # noqa: WPS433

    paradiso_backend._reset_visas_cache_for_tests()
    paradiso_backend._reset_grounding_cache_for_tests()
    return TestClient(paradiso_backend.app), paradiso_backend


def _node_available() -> bool:
    try:
        subprocess.run(["node", "--version"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Part B — manual-to-law fallback backend behavior
# ---------------------------------------------------------------------------

class ManualToLawFallbackTests(unittest.TestCase):
    H1_KO = "H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?"
    H1_EN = "Can I take a university class in Korea on H-1?"
    F4_RESIDENCE = "F-4로 들어왔는데 국내거소신고를 해야 하나요?"

    def setUp(self):
        for k in ("LAW_GROUNDING_MODE", "LAW_API_KEY"):
            os.environ.pop(k, None)

    def tearDown(self):
        for k in ("LAW_GROUNDING_MODE", "LAW_API_KEY"):
            os.environ.pop(k, None)

    def _detail(self, question, **extra):
        client, _ = _client()
        payload = {"question": question}
        payload.update(extra)
        resp = client.post("/api/ask", json=payload)
        self.assertEqual(resp.status_code, 503, resp.text)
        return resp.json()["detail"]

    def test_metadata_fields_present(self):
        detail = self._detail("커피 추천해줘")
        for key in ("manual_grounding_status", "manual_to_law_fallback_used",
                    "manual_to_law_fallback_reason"):
            self.assertIn(key, detail)

    def test_manual_missing_audit_attempts_law_and_uses_fallback(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        detail = self._detail(self.H1_KO, visa_code="H-1")
        self.assertEqual(detail.get("manual_grounding_status"), "absent")
        self.assertTrue(detail.get("law_grounding_attempted"))
        self.assertTrue(detail.get("manual_to_law_fallback_used"))
        self.assertEqual(detail.get("manual_to_law_fallback_reason"),
                         "manual_grounding_absent_law_intent")

    def test_english_h1_class_question_triggers_fallback(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        detail = self._detail(self.H1_EN, visa_code="H-1", lang="en")
        self.assertTrue(detail.get("law_grounding_attempted"))
        self.assertTrue(detail.get("manual_to_law_fallback_used"))

    def test_manual_missing_disabled_exposes_safe_status_without_using_fallback(self):
        os.environ["LAW_GROUNDING_MODE"] = "disabled"
        detail = self._detail(self.H1_KO, visa_code="H-1")
        self.assertEqual(detail.get("law_grounding_status"), "disabled")
        self.assertFalse(detail.get("law_grounding_attempted"))
        # Fallback is "wanted" but not "used" because grounding is disabled.
        self.assertFalse(detail.get("manual_to_law_fallback_used"))
        self.assertEqual(detail.get("manual_to_law_fallback_reason"),
                         "manual_grounding_absent_law_intent_grounding_disabled")

    def test_manual_present_does_not_over_trigger_fallback(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        detail = self._detail("D-2 연장 서류", visa_code="D-2")
        self.assertTrue(detail.get("grounding_used"))
        self.assertEqual(detail.get("manual_grounding_status"), "present")
        self.assertFalse(detail.get("manual_to_law_fallback_used"))

    def test_f4_domestic_residence_report_triggers_fallback(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        detail = self._detail(self.F4_RESIDENCE, visa_code="F-4")
        self.assertTrue(detail.get("law_grounding_attempted"))
        self.assertTrue(detail.get("manual_to_law_fallback_used"))

    def test_law_fallback_does_not_create_document_checklist(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        detail = self._detail(self.H1_KO, visa_code="H-1")
        # Fallback used, but no manual document grounding sources are fabricated.
        self.assertTrue(detail.get("manual_to_law_fallback_used"))
        self.assertFalse(detail.get("grounding_used"))
        self.assertEqual(detail.get("grounding_sources"), [])
        self.assertFalse(detail.get("procedure_variant_context_used"))

    def test_fallback_metadata_never_leaks_law_api_key(self):
        os.environ["LAW_GROUNDING_MODE"] = "audit"
        os.environ["LAW_API_KEY"] = "fallback-secret-999"
        client, _ = _client()
        resp = client.post("/api/ask", json={"question": self.H1_KO, "visa_code": "H-1"})
        self.assertEqual(resp.status_code, 503)
        self.assertNotIn("fallback-secret-999", resp.text)


# ---------------------------------------------------------------------------
# Part D — Groq fallback control / Gemma strictness
# ---------------------------------------------------------------------------

class GroqFallbackControlTests(unittest.TestCase):
    def _pb(self):
        import paradiso_backend
        return paradiso_backend

    def test_default_is_strict_false_when_unset(self):
        """With ALLOW_GROQ_FALLBACK unset, the resolved default is False."""
        import paradiso_backend as pb
        saved = os.environ.pop("ALLOW_GROQ_FALLBACK", None)
        try:
            importlib.reload(pb)
            self.assertFalse(pb.ALLOW_GROQ_FALLBACK)
        finally:
            if saved is not None:
                os.environ["ALLOW_GROQ_FALLBACK"] = saved
            importlib.reload(pb)  # restore clean (default-false) module state

    def test_explicit_true_token_enables_fallback(self):
        import paradiso_backend as pb
        os.environ["ALLOW_GROQ_FALLBACK"] = "true"
        try:
            importlib.reload(pb)
            self.assertTrue(pb.ALLOW_GROQ_FALLBACK)
        finally:
            os.environ.pop("ALLOW_GROQ_FALLBACK", None)
            importlib.reload(pb)

    def test_fallback_disabled_means_groq_not_used(self):
        pb = self._pb()
        with patch.object(pb, "OPENROUTER_API_KEY", None), \
                patch.object(pb, "GROQ_API_KEY", "groq-key"), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", False):
            cfg = pb._resolve_llm_config()
            self.assertEqual(cfg["provider"], "none")
            self.assertNotIn("GROQ_FALLBACK_ENABLED", cfg["warnings"])

    def test_fallback_enabled_is_explicit_and_warned(self):
        pb = self._pb()
        with patch.object(pb, "OPENROUTER_API_KEY", None), \
                patch.object(pb, "GROQ_API_KEY", "groq-key"), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", True):
            cfg = pb._resolve_llm_config()
            self.assertEqual(cfg["provider"], "groq")
            self.assertIn("GROQ_FALLBACK_ENABLED", cfg["warnings"])
            self.assertIn("GROQ_FALLBACK_ACTIVE", cfg["warnings"])

    def test_openrouter_precedence_unaffected_by_flag(self):
        pb = self._pb()
        with patch.object(pb, "OPENROUTER_API_KEY", "or-key"), \
                patch.object(pb, "GROQ_API_KEY", "groq-key"), \
                patch.object(pb, "ALLOW_GROQ_FALLBACK", True):
            cfg = pb._resolve_llm_config()
            self.assertEqual(cfg["provider"], "openrouter")
            # Fallback armed but NOT active (OpenRouter is the provider).
            self.assertIn("GROQ_FALLBACK_ENABLED", cfg["warnings"])
            self.assertNotIn("GROQ_FALLBACK_ACTIVE", cfg["warnings"])

    def test_no_provider_returns_safe_503_without_secret(self):
        os.environ["OPENROUTER_API_KEY"] = "or-secret-abc"
        try:
            client, pb = _client()  # _client() pops provider keys
            with patch.object(pb, "OPENROUTER_API_KEY", None), \
                    patch.object(pb, "GROQ_API_KEY", None), \
                    patch.object(pb, "ALLOW_GROQ_FALLBACK", False):
                resp = client.post("/api/ask", json={"question": "D-2 연장"})
            self.assertEqual(resp.status_code, 503)
            self.assertEqual(resp.json()["detail"]["error"], "no_llm_provider_configured")
            self.assertNotIn("or-secret-abc", resp.text)
        finally:
            os.environ.pop("OPENROUTER_API_KEY", None)

    def test_health_reports_fallback_setting_and_warnings(self):
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("GROQ_API_KEY", None)
        client, pb = _client()
        # Disabled -> groq_fallback_allowed False, no warning.
        with patch.object(pb, "ALLOW_GROQ_FALLBACK", False):
            data = client.get("/health").json()
        self.assertIn("groq_fallback_allowed", data["llm"])
        self.assertFalse(data["llm"]["groq_fallback_allowed"])
        self.assertIn("warnings", data["llm"])
        self.assertNotIn("GROQ_FALLBACK_ENABLED", data["llm"]["warnings"])
        # Enabled -> warning surfaced.
        with patch.object(pb, "ALLOW_GROQ_FALLBACK", True):
            data2 = client.get("/health").json()
        self.assertTrue(data2["llm"]["groq_fallback_allowed"])
        self.assertIn("GROQ_FALLBACK_ENABLED", data2["llm"]["warnings"])

    def test_health_never_leaks_api_key(self):
        os.environ["OPENROUTER_API_KEY"] = "or-health-secret"
        try:
            client, _ = _client()
            os.environ["OPENROUTER_API_KEY"] = "or-health-secret"
            resp = client.get("/health")
            self.assertNotIn("or-health-secret", resp.text)
        finally:
            os.environ.pop("OPENROUTER_API_KEY", None)


# ---------------------------------------------------------------------------
# Part A/G — i18n leak guard + translated chrome
# ---------------------------------------------------------------------------

class I18nLeakGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8")
        cls.guard_src = CHECK_I18N.read_text(encoding="utf-8")
        cls.packs = load_packs()
        cls.blobs = pack_blobs()

    @unittest.skipUnless(_node_available(), "node not available")
    def test_guard_passes_on_current_index(self):
        rc = subprocess.call(["node", str(CHECK_I18N)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertEqual(rc, 0)

    @unittest.skipUnless(_node_available(), "node not available")
    def test_guard_catches_injected_korean_ui_leak(self):
        # Inject a Korean UI string literal into the i18n runtime region of
        # index.html and confirm the inline hardcoded-text scanner flags it.
        marker = "const LANGUAGE_STORAGE_KEY = 'paradiso:language';"
        self.assertIn(marker, self.html, "i18n runtime marker not found in index.html")
        leaked = self.html.replace(
            marker,
            marker + "\nconst __leakProbe = '관할 관서 정보가 누락되었습니다.';",
            1,
        )
        self.assertNotEqual(leaked, self.html, "fixture replacement did not apply")
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(leaked)
            fixture = fh.name
        try:
            proc = subprocess.run(
                ["node", str(CHECK_I18N)],
                env={**os.environ, "CHECK_I18N_INDEX": fixture},
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("Suspicious inline UI strings", proc.stdout + proc.stderr)
        finally:
            os.unlink(fixture)

    def test_i18n_guard_enforces_parity_allowlist_and_official_korean_notes(self):
        # Strict cross-locale parity guard: covers every supported locale and
        # fails on missing/extra/shape-mismatched keys (replaces the old inline
        # REQUIRED_UI_KEYS / checkRequiredKeysAcrossLanguages logic).
        #
        # This used to require each locale to appear as a LITERAL in the script.
        # The guard has since been changed to derive its locale list from
        # manifest.supportedLocales, which is strictly better — a new pack is
        # gated automatically instead of only when someone remembers to edit the
        # script — but it made the literal assertion fail on locales the guard
        # does in fact cover. Assert the derivation instead.
        coverage = CHECK_I18N_COVERAGE.read_text(encoding="utf-8")
        self.assertIn("manifest.supportedLocales", coverage)
        self.assertIn("supported.filter", coverage)
        for locale in ("ko", "en", "zh-CN"):
            self.assertIn("'%s'" % locale, coverage,
                          "core locales must stay hard-guaranteed, not manifest-dependent")
        for token in ("requiredLocales", "missing", "extra", "shape mismatch"):
            self.assertIn(token, coverage)
        # Inline hardcoded-text scanner keeps an allowlist of intentionally
        # retained strings (replaces INTENTIONAL_KOREAN_ALLOWLIST).
        hardcoded = CHECK_I18N_HARDCODED.read_text(encoding="utf-8")
        self.assertIn("allowlist", hardcoded)
        # Official Korean source-term notes remain present (intentionally Korean
        # even in non-Korean packs) in every supported pack.
        for key in ("scenarioOfficialLabelsKoNote", "officialDocumentNamesKoNote",
                    "partialLanguageNotice"):
            for locale in SUPPORTED_LOCALES:
                self.assertIn(key, self.packs[locale], f"{key} missing from {locale} pack")

    def test_manual_to_law_fallback_labels_in_supported_languages(self):
        self.assertEqual(localized(self.packs, "ko", "manualToLawFallbackLabel"), "매뉴얼 근거 부족")
        self.assertEqual(localized(self.packs, "en", "manualToLawFallbackLabel"), "Manual guidance insufficient")
        self.assertEqual(localized(self.packs, "zh-CN", "manualToLawFallbackLabel"), "手册依据不足")
        self.assertEqual(localized(self.packs, "ko", "manualToLawFallbackChecked"), "법령 근거로 보완 확인")
        self.assertEqual(localized(self.packs, "en", "manualToLawFallbackChecked"), "Checked supporting legal grounding")
        self.assertEqual(localized(self.packs, "zh-CN", "manualToLawFallbackChecked"), "已尝试以法令依据补充确认")

    def test_doc_modal_titles_routed_through_tx(self):
        # openDocModal no longer uses a ko/en-only ternary for stage titles.
        modal = self.html.split("function openDocModal", 1)[1].split("function ", 1)[0]
        for key in ("docModalTitleNew", "docModalTitleExt", "docModalTitleChange",
                    "docModalTitleSub", "docModalTitleSubGeneric", "docStageReference"):
            self.assertIn("tx('%s'" % key, modal)
        self.assertNotIn("currentLanguage === 'en' ? 'Visa / new application documents'", self.html)
        # Present in all supported packs.
        for key in ("docModalTitleNew", "docModalTitleExt", "docModalTitleChange",
                    "docStageReference"):
            for locale in SUPPORTED_LOCALES:
                self.assertIn(key, self.packs[locale], f"{key} missing from {locale} pack")

    def test_jurisdiction_chrome_routed_through_tx(self):
        for key in ("jurSidoPlaceholder", "jurSigunguPlaceholder", "jurMissingInfo", "jurResultMsg"):
            self.assertIn("tx('%s'" % key, self.html)
            for locale in SUPPORTED_LOCALES:
                self.assertIn(key, self.packs[locale], f"{key} missing from {locale} pack")
        # No longer hard-codes the Korean placeholders/messages.
        self.assertNotIn("'<option value=\"\">시/도 선택</option>'", self.html)
        self.assertNotIn('showToast("관할 관서 정보가 누락되었습니다.")', self.html)

    def test_source_panel_labels_present_in_supported_languages(self):
        self.assertEqual(localized(self.packs, "ko", "sourceStatusTitle"), "출처 및 검증 상태")
        self.assertEqual(localized(self.packs, "en", "sourceStatusTitle"), "Source and verification status")
        self.assertEqual(localized(self.packs, "zh-CN", "sourceStatusTitle"), "来源及核实状态")
        # Action-label arrays remain localized per supported locale.
        self.assertIn("签证/新申请材料", localized(self.packs, "zh-CN", "manualActionLabels"))
        self.assertIn("✨ 请求综合情况分析", localized(self.packs, "zh-CN", "aiActionLabels"))

    def test_source_panel_renders_manual_to_law_fallback_row(self):
        fn = self.html.split("function renderGroundingSourcePanel", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("m.manual_to_law_fallback_used", fn)
        self.assertIn("tx('manualToLawFallbackLabel')", fn)
        self.assertIn("tx('manualToLawFallbackChecked')", fn)
        self.assertIn("tx('manualToLawFallbackNote')", fn)
        # Distinct styling from source-confirmed manual grounding.
        self.assertIn("gp-row-law-fallback", fn)


# ---------------------------------------------------------------------------
# Part C/G — provider-aware live smoke harness
# ---------------------------------------------------------------------------

class ProviderAwareSmokeHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SMOKE.read_text(encoding="utf-8")

    def test_smoke_compiles_and_help_runs(self):
        self.assertEqual(subprocess.call([sys.executable, "-m", "py_compile", str(SMOKE)]), 0)
        self.assertEqual(
            subprocess.call([sys.executable, str(SMOKE), "--help"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
            0,
        )

    def test_smoke_supports_deployed_url_and_no_provider_skip(self):
        self.assertIn("--backend-url", self.src)
        self.assertIn("BACKEND_URL", self.src)
        self.assertIn("--require-live", self.src)
        self.assertIn("no_llm_provider_configured", self.src)
        self.assertIn("live answer skipped", self.src)

    def test_smoke_reports_groq_fallback_and_manual_to_law(self):
        self.assertIn("groq_fallback_allowed", self.src)
        self.assertIn("manual_to_law_fallback_used", self.src)
        self.assertIn("manual_grounding_status", self.src)

    def test_smoke_never_prints_secrets(self):
        # Must not read or print raw provider key values.
        self.assertNotIn("OPENROUTER_API_KEY", self.src)
        self.assertNotIn("GROQ_API_KEY", self.src)
        self.assertIn("never prints api keys", self.src.lower())

    def test_smoke_no_provider_run_exits_zero(self):
        # Unreachable backend -> recorded as skipped, exit 0 (safe by default).
        proc = subprocess.run(
            [sys.executable, str(SMOKE)],
            env={**os.environ, "BACKEND_URL": "http://127.0.0.1:59998"},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("SKIPPED", proc.stdout + proc.stderr)


# ---------------------------------------------------------------------------
# Part F — documentation
# ---------------------------------------------------------------------------

class DocumentationTests(unittest.TestCase):
    def test_doc_exists_and_covers_required_sections(self):
        self.assertTrue(DOC.exists())
        doc = DOC.read_text(encoding="utf-8")
        for token in (
            "web-production-14f9a.up.railway.app",
            "BACKEND_URL",
            "smoke_ai_live_quality.py",
            "ALLOW_GROQ_FALLBACK",
            "manual_to_law_fallback_used",
            "OPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free",
            "LAW_GROUNDING_MODE=audit",
            "preparation aids only",
        ):
            self.assertIn(token, doc)


if __name__ == "__main__":
    unittest.main()
