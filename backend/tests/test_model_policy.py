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
            "OPENROUTER_ENFORCEMENT_MODEL",
            "OPENROUTER_ENFORCEMENT_MODEL_CANDIDATES",
            "OPENROUTER_ALLOW_MODEL_ENV_OVERRIDES",
            "AI_ROUTER_MODEL",
            "AI_TRANSLATION_MODEL",
            "AI_VERIFIER_MODEL",
            "AI_CHINESE_MODEL",
            "AI_CHINESE_FALLBACK_MODELS",
        ):
            os.environ.pop(key, None)

    def test_default_final_answer_chain_matches_catalog_reconciled_policy(self):
        policy = model_policy.resolve_model_role_policy()
        # 2026-10-21: Gemma only. The NVIDIA ':free' routes run under the NVIDIA API
        # Trial terms (no production use) and Inkling ':free' under a research tier
        # (no personal data); see model_policy's module docstring.
        self.assertEqual(policy["final_answer_model"], "google/gemma-4-31b-it:free")
        self.assertEqual(policy["final_answer_model_candidates"], ["google/gemma-4-31b-it:free", "google/gemma-4-26b-a4b-it:free"])
        for model in policy["final_answer_model_candidates"]:
            self.assertFalse(model.startswith(("nvidia/", "thinkingmachines/")), model)

    def test_gemma_is_router_and_translation_default(self):
        policy = model_policy.resolve_model_role_policy()
        self.assertEqual(policy["router_model"], "google/gemma-4-31b-it:free")
        self.assertEqual(policy["translation_model"], "google/gemma-4-31b-it:free")

    def test_gemma_31b_is_verifier_default(self):
        policy = model_policy.resolve_model_role_policy()
        self.assertEqual(policy["verifier_model"], "google/gemma-4-31b-it:free")

    def test_chinese_models_are_separate_from_default_final_chain(self):
        policy = model_policy.resolve_model_role_policy()
        final_chain = policy["final_answer_model_candidates"]
        for model in final_chain:
            self.assertFalse(model_policy.model_family_is_chinese_only(model), model)
        self.assertEqual(policy["chinese_model"], "minimax/minimax-m3")
        self.assertIn("inclusionai/ling-3.0-flash-sante:free", policy["chinese_fallback_models"])
        self.assertIn("inclusionai/ling-3.0-flash-fin:free", policy["chinese_fallback_models"])


class AnswerModeTierTests(unittest.TestCase):
    def setUp(self):
        for key in (
            "OPENROUTER_MODEL",
            "OPENROUTER_MODEL_CANDIDATES",
            "OPENROUTER_FAST_MODEL",
            "OPENROUTER_FAST_MODEL_CANDIDATES",
            "OPENROUTER_ALLOW_MODEL_ENV_OVERRIDES",
        ):
            os.environ.pop(key, None)

    def test_basic_mode_uses_catalog_reconciled_chain(self):
        plan = model_policy.resolve_answer_mode_models("basic")
        self.assertEqual(plan["mode"], "basic")
        self.assertTrue(plan["available"])
        self.assertEqual(plan["primary"], "google/gemma-4-31b-it:free")
        self.assertEqual(plan["candidates"], ["google/gemma-4-31b-it:free", "google/gemma-4-26b-a4b-it:free"])

    def test_fast_mode_uses_light_gemma_primary_then_fast_fallback(self):
        plan = model_policy.resolve_answer_mode_models("fast")
        self.assertEqual(plan["mode"], "fast")
        self.assertTrue(plan["available"])
        # Lightweight Gemma 4 (MoE) is the fast primary; every fallback is a
        # current public-catalog identifier.
        self.assertEqual(plan["primary"], "google/gemma-4-26b-a4b-it:free")
        cands = plan["candidates"]
        self.assertEqual(cands, ["google/gemma-4-26b-a4b-it:free", "google/gemma-4-31b-it:free"])
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
        os.environ["OPENROUTER_ALLOW_MODEL_ENV_OVERRIDES"] = "true"
        plan = model_policy.resolve_answer_mode_models("fast")
        self.assertEqual(plan["primary"], "openai/gpt-oss-120b:free")

    def test_fast_model_env_override_is_ignored_without_opt_in(self):
        os.environ["OPENROUTER_FAST_MODEL"] = "stale/example:free"
        plan = model_policy.resolve_answer_mode_models("fast")
        self.assertEqual(plan["primary"], model_policy.DEFAULT_FAST_ANSWER_MODEL)

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
                "OPENROUTER_ALLOW_MODEL_ENV_OVERRIDES": "true",
            },
            clear=False,
        ):
            policy = model_policy.resolve_model_role_policy()
        self.assertEqual(policy["final_answer_model_candidates"], ["x/primary:free", "a/b:free", "c/d:free"])

    def test_stale_final_chain_is_ignored_without_explicit_opt_in(self):
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_MODEL": "stale/primary:free",
                "OPENROUTER_MODEL_CANDIDATES": "stale/one:free,stale/two:free",
            },
            clear=False,
        ):
            policy = model_policy.resolve_model_role_policy()
        self.assertFalse(policy["model_env_overrides_allowed"])
        self.assertEqual(policy["final_answer_model"], model_policy.DEFAULT_FINAL_ANSWER_MODEL)
        self.assertEqual(
            policy["final_answer_model_candidates"],
            model_policy.DEFAULT_FINAL_ANSWER_MODEL_CANDIDATES,
        )

    def test_stale_enforcement_chain_is_ignored_without_explicit_opt_in(self):
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_ENFORCEMENT_MODEL": "stale/enforcement:free",
                "OPENROUTER_ENFORCEMENT_MODEL_CANDIDATES": "stale/enforcement:free",
            },
            clear=False,
        ):
            policy = model_policy.resolve_model_role_policy()
        self.assertEqual(
            policy["enforcement_structured_model"],
            model_policy.DEFAULT_ENFORCEMENT_STRUCTURED_MODEL,
        )
        self.assertEqual(
            policy["enforcement_structured_model_candidates"],
            model_policy.DEFAULT_ENFORCEMENT_STRUCTURED_MODEL_CANDIDATES,
        )


# The Railway variables that were live on 2026-10-23: the pre-#674 chains,
# opted in through OPENROUTER_ALLOW_MODEL_ENV_OVERRIDES.
_STALE_RAILWAY_ENV = {
    "OPENROUTER_ALLOW_MODEL_ENV_OVERRIDES": "true",
    "OPENROUTER_MODEL": "google/gemma-4-31b-it:free",
    "OPENROUTER_MODEL_CANDIDATES": (
        "google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free,"
        "nvidia/nemotron-3-super-120b-a12b:free,nvidia/nemotron-3-ultra-550b-a55b:free"
    ),
    "OPENROUTER_FAST_MODEL": "nvidia/nemotron-3-super-120b-a12b:free",
    "OPENROUTER_FAST_MODEL_CANDIDATES": (
        "nvidia/nemotron-3-super-120b-a12b:free,nvidia/nemotron-3-ultra-550b-a55b:free"
    ),
    "OPENROUTER_ENFORCEMENT_MODEL": "nvidia/nemotron-3-super-120b-a12b:free",
    "OPENROUTER_ENFORCEMENT_MODEL_CANDIDATES": "nvidia/nemotron-3-super-120b-a12b:free",
    "AI_VERIFIER_MODEL": "nvidia/nemotron-3-super-120b-a12b:free",
}


class PolicyBlockedModelTests(unittest.TestCase):
    """Excluded providers must stay out even when an override lists them."""

    def test_blocked_prefix_detection(self):
        for model in (
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "NVIDIA/Nemotron-3-Super:free",
            " thinkingmachines/inkling:free ",
        ):
            self.assertTrue(model_policy.model_is_policy_blocked(model), model)
        for model in ("google/gemma-4-31b-it:free", "openai/gpt-oss-120b:free", "", None):
            self.assertFalse(model_policy.model_is_policy_blocked(model), model)

    def test_drop_policy_blocked_models_keeps_order(self):
        self.assertEqual(
            model_policy.drop_policy_blocked_models(
                ["a/one", "nvidia/x:free", "b/two", "thinkingmachines/y:free"]
            ),
            ["a/one", "b/two"],
        )

    def test_stale_railway_overrides_cannot_reintroduce_blocked_models(self):
        with patch.dict(os.environ, _STALE_RAILWAY_ENV, clear=False):
            self.assertTrue(model_policy.model_env_overrides_allowed())
            policy = model_policy.resolve_model_role_policy()
            basic = model_policy.resolve_answer_mode_models("basic")
            fast = model_policy.resolve_answer_mode_models("fast")
        self.assertEqual(
            policy["final_answer_model_candidates"],
            ["google/gemma-4-31b-it:free", "google/gemma-4-26b-a4b-it:free"],
        )
        self.assertEqual(
            basic["candidates"], ["google/gemma-4-31b-it:free", "google/gemma-4-26b-a4b-it:free"]
        )
        # Every Fast override was blocked, so Fast falls back to the committed chain.
        self.assertEqual(fast["primary"], model_policy.DEFAULT_FAST_ANSWER_MODEL)
        self.assertEqual(fast["candidates"], model_policy.DEFAULT_FAST_ANSWER_MODEL_CANDIDATES)
        self.assertEqual(
            policy["enforcement_structured_model"],
            model_policy.DEFAULT_ENFORCEMENT_STRUCTURED_MODEL,
        )
        self.assertEqual(
            policy["enforcement_structured_model_candidates"],
            model_policy.DEFAULT_ENFORCEMENT_STRUCTURED_MODEL_CANDIDATES,
        )
        self.assertEqual(policy["verifier_model"], model_policy.DEFAULT_VERIFIER_MODEL)
        for chain in (
            policy["final_answer_model_candidates"],
            basic["candidates"],
            fast["candidates"],
            policy["enforcement_structured_model_candidates"],
        ):
            for model in chain:
                self.assertFalse(model_policy.model_is_policy_blocked(model), model)

    def test_allowed_overrides_still_work_next_to_blocked_ones(self):
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_ALLOW_MODEL_ENV_OVERRIDES": "true",
                "OPENROUTER_MODEL": "x/primary:free",
                "OPENROUTER_MODEL_CANDIDATES": "nvidia/blocked:free,a/b:free,x/primary:free",
            },
            clear=False,
        ):
            policy = model_policy.resolve_model_role_policy()
        self.assertEqual(policy["final_answer_model_candidates"], ["x/primary:free", "a/b:free"])

    def test_policy_notes_no_longer_claim_nemotron_defaults(self):
        notes = " ".join(model_policy.resolve_model_role_policy()["policy_notes"]).lower()
        self.assertNotIn("nemotron 3 ultra is the default", notes)
        self.assertNotIn("nemotron 3 super is the default", notes)


if __name__ == "__main__":
    unittest.main()
