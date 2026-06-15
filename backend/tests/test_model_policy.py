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

    def test_default_final_answer_chain_uses_nemotron_then_gpt_oss_then_gemma(self):
        policy = model_policy.resolve_model_role_policy()
        self.assertEqual(policy["final_answer_model"], "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertEqual(
            policy["final_answer_model_candidates"],
            [
                "nvidia/nemotron-3-ultra-550b-a55b:free",
                "nvidia/nemotron-3-super-120b-a12b:free",
                "openai/gpt-oss-120b:free",
                "google/gemma-4-31b-it:free",
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

    def test_basic_mode_uses_full_nemotron_chain(self):
        plan = model_policy.resolve_answer_mode_models("basic")
        self.assertEqual(plan["mode"], "basic")
        self.assertTrue(plan["available"])
        self.assertEqual(plan["primary"], "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.assertEqual(plan["candidates"][0], "nvidia/nemotron-3-ultra-550b-a55b:free")

    def test_fast_mode_uses_light_gemma_first_then_qwen_then_llama(self):
        plan = model_policy.resolve_answer_mode_models("fast")
        self.assertEqual(plan["mode"], "fast")
        self.assertTrue(plan["available"])
        # Lightweight Gemma 4 (MoE) is the fast primary.
        self.assertEqual(plan["primary"], "google/gemma-4-26b-a4b-it:free")
        cands = plan["candidates"]
        # Gemma family leads; Qwen then Llama provide resilient fallbacks.
        self.assertTrue(cands[0].startswith("google/gemma-4"))
        self.assertTrue(any(c.startswith("google/gemma") for c in cands))
        self.assertTrue(any(c.startswith("qwen/") for c in cands))
        self.assertTrue(any(c.startswith("meta-llama/") for c in cands))
        # The slow 550B ultra model must never be in the fast tier.
        self.assertNotIn("nvidia/nemotron-3-ultra-550b-a55b:free", cands)

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
