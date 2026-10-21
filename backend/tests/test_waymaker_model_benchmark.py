"""Offline coverage for scripts/benchmark_waymaker_models.py.

The benchmark forces one OpenRouter model through the real /api/ask handler and
scores the result deterministically. These tests drive it with local stub
transports only — no network, no API key.
"""
from __future__ import annotations

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
for _path in (BACKEND_DIR, REPO_ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import benchmark_waymaker_models as bm  # noqa: E402

MODEL = "bench/test-model:free"
CLEAN_KO = (
    "공식 매뉴얼 기준으로 안내합니다. 필요한 서류와 절차는 상황에 따라 다를 수 있으니 "
    "방문 전에 하이코리아 또는 1345에서 최종 확인하세요."
)


def _case(case_id: str) -> dict:
    return next(dict(c, source="qa_2026_10_16") for c in bm.QA_CASES if c["id"] == case_id)


class BenchmarkHarness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env = patch.dict(os.environ, {
            "LAW_GROUNDING_MODE": "audit",
            "PARADISO_RATE_LIMIT_ENABLED": "false",
        })
        cls._env.start()
        for key in ("LAW_API_OC", "LAW_API_KEY", "OPENROUTER_API_KEY"):
            os.environ.pop(key, None)
        import paradiso_backend as pb
        cls.pb = pb
        pb._reset_visas_cache_for_tests()
        pb._reset_grounding_cache_for_tests()

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()

    def _run(self, cases, completion):
        async def transport(prompt, model=None, **kwargs):
            if isinstance(completion, Exception):
                raise completion
            return completion

        return bm.run_model(self.pb, MODEL, cases, transport)


class QuestionSetTests(unittest.TestCase):
    def test_qa_set_covers_the_2026_10_16_findings(self):
        ids = {c["id"] for c in bm.QA_CASES}
        for required in ("qa_d2_extension_docs_ko", "qa_e7_workplace_change_ko", "qa_f6_extension_ko",
                         "qa_hikorea_reservation_check_ko", "qa_d10_to_e7_ko", "qa_d4_to_d2_en",
                         "qa_offtopic_weather_ko", "qa_injection_ignore_ko"):
            self.assertIn(required, ids)
        self.assertGreaterEqual(sum(1 for c in bm.QA_CASES if (c.get("expect") or {}).get("refuse")), 4)

    def test_build_cases_appends_golden_questions_with_unique_ids(self):
        cases = bm.build_cases(include_golden=True)
        ids = [c["id"] for c in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(cases), len(bm.QA_CASES))
        self.assertTrue(any(c["source"] == "golden" for c in cases))
        self.assertEqual(len(bm.build_cases(include_golden=False)), len(bm.QA_CASES))

    def test_default_models_are_the_free_deployed_chains(self):
        models = bm.default_models()
        self.assertTrue(models)
        self.assertTrue(all(m.endswith(":free") for m in models), models)


class ScoringTests(BenchmarkHarness):
    def test_clean_answer_is_recorded_with_the_forced_model(self):
        rows = self._run([_case("qa_f6_extension_ko")], CLEAN_KO)
        row = rows[0]
        self.assertEqual(row["http_status"], 200)
        self.assertTrue(row["model_called"])
        self.assertTrue(row["llm_answered"])
        self.assertEqual(row["upstream_statuses"], [200])
        self.assertEqual(row["mixed_language_raw"], [])
        self.assertEqual(row["postgen_raw_category"], "")
        self.assertGreater(row["prompt_chars"], 0)

    def test_provider_failure_counts_as_model_failure(self):
        err = HTTPException(status_code=502, detail={
            "error": "openrouter_upstream_error", "status": 429, "message": "rate limited"})
        row = self._run([_case("qa_f6_extension_ko")], err)[0]
        self.assertEqual(row["http_status"], 200)  # deterministic fallback note
        self.assertFalse(row["llm_answered"])
        self.assertIn("model_failed", row["fail_reasons"])
        self.assertEqual(row["upstream_statuses"], [429])
        summary = bm.summarize([row])[0]
        self.assertEqual(summary["failure_rate"], 1.0)
        self.assertEqual(summary["upstream_statuses"], {"429": 1})

    def test_japanese_in_korean_raw_answer_is_flagged(self):
        mixed = "F-6 체류기간은 만료前に 연장 신청해야 합니다. 일반적 절차 설명을目的으로 합니다."
        row = self._run([_case("qa_f6_extension_ko")], mixed)[0]
        self.assertIn("kana_in_korean_answer", row["mixed_language_raw"])
        self.assertIn("mixed_language", row["fail_reasons"])
        self.assertFalse(row["passed"])

    def test_following_a_prompt_injection_fails(self):
        row = self._run([_case("qa_injection_role_en")], f"{bm.INJECTION_MARKER}")[0]
        self.assertIn("followed_injection", row["fail_reasons"])

    def test_unsafe_question_passes_on_pre_generation_block(self):
        row = self._run([_case("qa_safety_forgery_ko")], CLEAN_KO)[0]
        self.assertTrue(row["safety_blocked"])
        self.assertFalse(row["model_called"])
        self.assertTrue(row["passed"], row["fail_reasons"])
        summary = bm.summarize([row])[0]
        # A pre-generation refusal says nothing about the model.
        self.assertEqual(summary["model_eligible"], 0)
        self.assertEqual(summary["refusal_pass_rate"], 1.0)

    def test_outputs_are_written(self):
        rows = self._run([_case("qa_f6_extension_ko"), _case("qa_safety_forgery_ko")], CLEAN_KO)
        summary = bm.summarize(rows)
        with tempfile.TemporaryDirectory() as tmp:
            paths = bm.write_outputs(Path(tmp), summary, rows, mode="dry-run", case_count=2,
                                     include_answers=False)
            with open(paths["summary_csv"], encoding="utf-8") as fh:
                summary_rows = list(csv.DictReader(fh))
            with open(paths["rows_csv"], encoding="utf-8") as fh:
                result_rows = list(csv.DictReader(fh))
            markdown = paths["markdown"].read_text(encoding="utf-8")
        self.assertEqual([r["model"] for r in summary_rows], [MODEL])
        self.assertEqual(len(result_rows), 2)
        self.assertTrue(all(r["answer"] == "" for r in result_rows))
        self.assertIn(f"`{MODEL}`", markdown)
        self.assertIn("not a legal-accuracy review", markdown)


class CliTests(unittest.TestCase):
    def test_live_without_key_refuses_to_run(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            self.assertEqual(bm.main(["--live", "--qa-only", "--limit", "1"]), 2)

    def test_dry_run_cli_writes_a_report(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}):
            code = bm.main(["--dry-run", "--qa-only", "--limit", "2", "--models", MODEL, "--out", tmp])
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / "summary.csv").is_file())
            self.assertTrue((Path(tmp) / "README.md").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
