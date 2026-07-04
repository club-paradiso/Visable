from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import model_policy


class ModelRolePolicyTests(unittest.TestCase):
    def setUp(self):
        for key in (
            "OPENROUTER_MODEL",
            "OPENROUTER_MODEL_CANDIDATES",
            "AI_ROUTER_MODEL",
            "AI_TRANSLATION_MODEL",
            "AI_VERIFIER_MODEL",
            "AI_CHINESE_MODEL",
            "AI_CHINESE_FALLBACK_MODELS",
        ):
            os.environ.pop(key, None)

    def test_default_final_answer_chain_uses_hermes_then_gemma(self):
        policy = model_policy.resolve_model_role_policy()
        self.assertEqual(policy["final_answer_model"], "nousresearch/hermes-3-llama-3.1-405b:free")
        self.assertEqual(
            policy["final_answer_model_candidates"],
            [
                "nousresearch/hermes-3-llama-3.1-405b:free",
                "google/gemma-4-26b-a4b-it:free",
                "meta-llama/llama-3.3-70b-instruct:free",
                "meta-llama/llama-4-scout:free",
            ],
        )

    def test_gemma_is_router_and_translation_default(self):
        policy = model_policy.resolve_model_role_policy()
        self.assertEqual(policy["router_model"], "google/gemma-4-31b-it:free")
        self.assertEqual(policy["translation_model"], "google/gemma-4-31b-it:free")

    def test_gpt_oss_is_verifier_default(self):
        policy = model_policy.resolve_model_role_policy()
        self.assertEqual(policy["verifier_model"], "openai/gpt-oss-120b:free")

    def test_chinese_models_are_separate_from_default_final_chain(self):
        policy = model_policy.resolve_model_role_policy()
        final_chain = policy["final_answer_model_candidates"]
        for model in final_chain:
            self.assertFalse(model_policy.model_family_is_chinese_only(model), model)
        self.assertEqual(policy["chinese_model"], "deepseek/deepseek-r1-0528:free")
        self.assertIn("qwen/qwen3-next-80b-a3b-instruct:free", policy["chinese_fallback_models"])
        self.assertIn("moonshotai/kimi-k2.6:free", policy["chinese_fallback_models"])


class AnswerModeTierTests(unittest.TestCase):
    def setUp(self):
        for key in (
            "OPENROUTER_MODEL",
            "OPENROUTER_MODEL_CANDIDATES",
            "OPENROUTER_FAST_MODEL",
            "OPENROUTER_FAST_MODEL_CANDIDATES",
        ):
            os.environ.pop(key, None)

    def test_basic_mode_uses_hermes_then_gemma_chain(self):
        plan = model_policy.resolve_answer_mode_models("basic")
        self.assertEqual(plan["mode"], "basic")
        self.assertTrue(plan["available"])
        self.assertEqual(plan["primary"], "nousresearch/hermes-3-llama-3.1-405b:free")
        self.assertEqual(
            plan["candidates"],
            [
                "nousresearch/hermes-3-llama-3.1-405b:free",
                "google/gemma-4-26b-a4b-it:free",
                "meta-llama/llama-3.3-70b-instruct:free",
                "meta-llama/llama-4-scout:free",
            ],
        )

    def test_fast_mode_uses_light_gemma_primary_then_fast_fallback(self):
        plan = model_policy.resolve_answer_mode_models("fast")
        self.assertEqual(plan["mode"], "fast")
        self.assertTrue(plan["available"])
        # Lightweight Gemma 4 (MoE) is the fast primary; gpt-oss-20b is the first
        # fallback, then Gemma 4 31B and Llama 3.3 70B as deeper fallbacks.
        self.assertEqual(plan["primary"], "google/gemma-4-26b-a4b-it:free")
        cands = plan["candidates"]
        self.assertEqual(cands, [
            "google/gemma-4-26b-a4b-it:free",
            "openai/gpt-oss-20b:free",
            "google/gemma-4-31b-it:free",
            "meta-llama/llama-3.3-70b-instruct:free",
        ])
        # The fast primary is also the basic fallback, so the two tiers share a
        # proven model and the fast tier can never be left without a reachable
        # model while basic-mode models are answering fine.
        basic = model_policy.resolve_answer_mode_models("basic")["candidates"]
        self.assertTrue(
            any(c in basic for c in cands),
            "fast chain must share at least one model with the basic chain",
        )
        # qwen/* is reserved for Chinese-language routes (not a fast fallback).
        self.assertFalse(any(c.startswith("qwen/") for c in cands))

    def test_pro_mode_is_coming_soon_and_falls_back_to_basic_chain(self):
        plan = model_policy.resolve_answer_mode_models("pro")
        self.assertEqual(plan["mode"], "basic")
        self.assertFalse(plan["available"])
        self.assertEqual(plan["requested_mode"], "pro")

    def test_unknown_mode_defaults_to_basic(self):
        self.assertEqual(model_policy.normalize_answer_mode("nonsense"), "basic")
        self.assertEqual(model_policy.normalize_answer_mode(None), "basic")

    def test_fast_model_env_override(self):
        os.environ["OPENROUTER_FAST_MODEL"] = "openai/gpt-oss-120b:free"
        plan = model_policy.resolve_answer_mode_models("fast")
        self.assertEqual(plan["primary"], "openai/gpt-oss-120b:free")

    def test_simple_fast_question_stays_fast(self):
        route = model_policy.resolve_question_answer_mode(
            "fast", question="F-4가 뭐예요?", legal_issue_types=[]
        )
        self.assertEqual(route["effective_mode"], "fast")
        self.assertFalse(route["auto_escalated"])

    def test_source_heavy_fast_question_auto_escalates_to_basic(self):
        route = model_policy.resolve_question_answer_mode(
            "fast",
            question="E-7 근무처 변경허가와 관련 판례를 근거로 위험을 설명해 주세요.",
            legal_issue_types=["workplace_change_addition", "activity_scope"],
            risk_level="medium",
        )
        self.assertEqual(route["requested_mode"], "fast")
        self.assertEqual(route["effective_mode"], "basic")
        self.assertTrue(route["auto_escalated"])
        self.assertIn("source_heavy_question", route["escalation_reasons"])
        self.assertIn("complex_legal_issue", route["escalation_reasons"])

    def test_basic_is_never_downgraded(self):
        route = model_policy.resolve_question_answer_mode("basic", question="F-4가 뭐예요?")
        self.assertEqual(route["effective_mode"], "basic")
        self.assertFalse(route["auto_escalated"])

    def test_env_overrides_keep_primary_first_and_deduped(self):
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_MODEL": "x/primary:free",
                "OPENROUTER_MODEL_CANDIDATES": "a/b:free,x/primary:free,c/d:free,a/b:free",
            },
            clear=False,
        ):
            policy = model_policy.resolve_model_role_policy()
        self.assertEqual(policy["final_answer_model_candidates"], ["x/primary:free", "a/b:free", "c/d:free"])


if __name__ == "__main__":
    unittest.main()
