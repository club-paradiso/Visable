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
