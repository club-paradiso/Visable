"""Regression coverage for the bounded enforcement AI path.

Clear cases must stay local, ambiguous cases may use AI, and enforcement model
routing must remain isolated from deploy-wide Fast-tier overrides.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import ai_runtime
from services.enforcement_service import extract_structured_case


class EnforcementLatencyBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_clear_heuristic_case_skips_ai_provider(self):
        calls = 0

        async def provider(_prompt):
            nonlocal calls
            calls += 1
            raise AssertionError("provider should not be called for a complete local parse")

        case = await extract_structured_case(
            "D-2 유학생인데 시간제취업 허가 없이 음식점에서 18일 아르바이트했습니다. 이번이 처음입니다.",
            provider=provider,
            assessment_date=date(2026, 9, 4),
        )
        self.assertEqual(calls, 0)
        self.assertEqual(case.violation_code, "STATUS_OUTSIDE_ACTIVITY_ART20")
        self.assertEqual(case.duration_days, 18)
        self.assertEqual(case.prior_violations, 0)

    async def test_ambiguous_case_still_uses_ai_provider(self):
        calls = 0

        async def provider(_prompt):
            nonlocal calls
            calls += 1
            return {"ok": False, "answer": None}

        await extract_structured_case(
            "F-2인데 다른 곳에서 허가 없이 10일 일했습니다.",
            provider=provider,
            assessment_date=date(2026, 9, 4),
        )
        self.assertEqual(calls, 1)


    async def test_enforcement_provider_requests_json_mode(self):
        import paradiso_backend as pb

        captured = {}

        async def fake_complete(prompt, **kwargs):
            captured.update(kwargs)
            return {"ok": False, "answer": None, "provider_error_type": "test"}

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake_complete):
            await pb._enforcement_ai_provider("synthetic prompt")

        self.assertEqual(captured["response_format"], {"type": "json_object"})
        self.assertEqual(captured["temperature"], 0.1)
        self.assertEqual(captured["max_tokens"], 900)
        self.assertEqual(captured["system_prompt"], pb.ENFORCEMENT_STRUCTURED_SYSTEM_PROMPT)
        self.assertIn("exactly one JSON object", captured["system_prompt"])

    async def test_general_candidate_path_preserves_legacy_transport_signature(self):
        import paradiso_backend as pb

        calls = []

        async def legacy_transport(prompt, model=None, max_tokens=None):
            calls.append((prompt, model, max_tokens))
            return "{}"

        with patch.object(pb, "_call_openrouter", new=legacy_transport):
            result = await pb._openrouter_complete_with_candidates(
                "synthetic prompt",
                requested_model="google/gemma-4-26b-a4b-it:free",
                candidate_models=["google/gemma-4-26b-a4b-it:free"],
                max_tokens=100,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(calls, [("synthetic prompt", "google/gemma-4-26b-a4b-it:free", 100)])

    async def test_provider_probe_returns_metadata_without_completion_content(self):
        import paradiso_backend as pb

        async def fake_complete(prompt, **kwargs):
            return {
                "ok": False,
                "answer": "SHOULD_NEVER_BE_EXPOSED",
                "attempted_models": ["model-a"],
                "skipped_models_due_to_cooldown": ["model-b"],
                "cooling_down_models": ["model-b"],
                "final_model": None,
                "provider_error_type": "invalid_request",
                "upstream_statuses": [400],
                "all_candidates_failed": False,
            }

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake_complete):
            payload = await pb._run_enforcement_provider_probe()

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["attemptedModels"], ["model-a"])
        self.assertEqual(payload["providerErrorType"], "invalid_request")
        self.assertEqual(payload["upstreamStatuses"], [400])
        self.assertNotIn("answer", payload)
        self.assertNotIn("SHOULD_NEVER_BE_EXPOSED", str(payload))

    async def test_provider_probe_recognizes_exact_json_contract(self):
        import paradiso_backend as pb

        async def fake_complete(prompt, **kwargs):
            return {
                "ok": True,
                "answer": json.dumps({"status":"UNAVAILABLE","monetaryPrediction":None,"primaryDisposition":None,"alternativeDispositions":[],"stayImpact":[],"aggravatingFactors":[],"mitigatingFactors":[],"unresolvedFactors":[],"confidence":{"level":"INSUFFICIENT","reasons":[]},"limitations":[]}),
                "attempted_models": ["model-a"],
                "skipped_models_due_to_cooldown": [],
                "cooling_down_models": [],
                "final_model": "model-a",
                "provider_error_type": None,
                "upstream_statuses": [],
                "all_candidates_failed": False,
            }

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake_complete):
            payload = await pb._run_enforcement_provider_probe()

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["jsonObjectReturned"])
        self.assertTrue(payload["predictionContractOk"])
        self.assertEqual(payload["finalModel"], "model-a")

    def test_enforcement_role_isolated_from_fast_env_overrides(self):
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_FAST_MODEL": "stale/example-model:free",
                "OPENROUTER_FAST_MODEL_CANDIDATES": "stale/example-model:free",
            },
            clear=False,
        ):
            plan = ai_runtime.resolve_task_models(ai_runtime.TaskRole.ENFORCEMENT_STRUCTURED)
        self.assertEqual(plan["primary"], "google/gemma-4-26b-a4b-it:free")
        self.assertEqual(
            plan["candidates"],
            ["google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3-super-120b-a12b:free"],
        )
        self.assertNotIn("stale/example-model:free", plan["candidates"])
        self.assertEqual(len(plan["candidates"]), 2)



class EnforcementChainBudgetTests(unittest.IsolatedAsyncioTestCase):
    """The enforcement budget must bound the CHAIN, not just wrap it.

    Production symptom this pins: /api/enforcement/analyze returned HTTP 200
    with prediction UNAVAILABLE after ~12.7s, while a standalone provider probe
    on the same deployment produced a valid structured prediction in ~3s. The
    wrapper fired during candidate #1 — sized from the 45s general chain budget
    — so the alternate candidate was never requested.
    """

    def setUp(self):
        import paradiso_backend as pb

        pb._reset_openrouter_model_cooldowns_for_tests()
        self.addCleanup(pb._reset_openrouter_model_cooldowns_for_tests)

    async def test_enforcement_budget_is_passed_into_the_candidate_chain(self):
        import paradiso_backend as pb

        captured = {}

        async def fake_complete(prompt, **kwargs):
            captured.update(kwargs)
            return {"ok": False, "answer": None, "provider_error_type": "test"}

        with patch.object(pb, "_openrouter_complete_with_candidates", new=fake_complete):
            await pb._enforcement_ai_provider("synthetic prompt")

        self.assertEqual(
            captured["chain_budget_seconds"], pb.ENFORCEMENT_AI_BUDGET_SECONDS
        )

    async def test_slow_first_candidate_still_leaves_room_for_the_fallback(self):
        import paradiso_backend as pb

        async def transport(prompt, model=None, max_tokens=None, **kwargs):
            if model == "slow/model:free":
                await asyncio.sleep(30)
                raise AssertionError("the slow candidate must be bounded well below the budget")
            return '{"ok": 1}'

        started = time.monotonic()
        with patch.object(pb, "_call_openrouter", new=transport), \
                patch.object(pb, "OPENROUTER_MIN_CANDIDATE_ATTEMPT_SECONDS", 0.5):
            result = await pb._openrouter_complete_with_candidates(
                "synthetic prompt",
                candidate_models=["slow/model:free", "fast/model:free"],
                chain_budget_seconds=4.0,
            )
        elapsed = time.monotonic() - started

        self.assertTrue(result["ok"])
        self.assertEqual(result["final_model"], "fast/model:free")
        self.assertEqual(result["attempted_models"], ["slow/model:free", "fast/model:free"])
        self.assertEqual(result["chain_budget_seconds"], 4.0)
        self.assertLess(elapsed, 4.0)

    async def test_budget_exhaustion_still_reports_which_models_were_tried(self):
        import paradiso_backend as pb

        async def transport(prompt, model=None, max_tokens=None, **kwargs):
            await asyncio.sleep(30)
            raise AssertionError("every candidate must be bounded by the budget")

        with patch.object(pb, "_call_openrouter", new=transport), \
                patch.object(pb, "OPENROUTER_MIN_CANDIDATE_ATTEMPT_SECONDS", 0.2):
            result = await pb._openrouter_complete_with_candidates(
                "synthetic prompt",
                candidate_models=["slow-a/model:free", "slow-b/model:free"],
                chain_budget_seconds=2.0,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["attempted_models"], ["slow-a/model:free", "slow-b/model:free"]
        )
        self.assertTrue(result["all_candidates_failed"])
        self.assertTrue(result["chain_budget_exhausted"])

    async def test_outer_wrapper_remains_a_backstop_for_a_chain_that_never_returns(self):
        import paradiso_backend as pb

        async def never_returns(prompt, **kwargs):
            await asyncio.sleep(30)
            raise AssertionError("the backstop must fire")

        with patch.object(pb, "_openrouter_complete_with_candidates", new=never_returns), \
                patch.object(pb, "ENFORCEMENT_AI_BUDGET_SECONDS", 0.2), \
                patch.object(pb, "ENFORCEMENT_AI_BUDGET_GRACE_SECONDS", 0.3):
            result = await pb._enforcement_ai_provider("synthetic prompt")

        self.assertFalse(result["ok"])
        self.assertIsNone(result["final_model"])
        self.assertEqual(result["provider_error_type"], "enforcement_total_timeout")


class CandidateAttemptTimeoutTests(unittest.TestCase):
    """The fallback reserve must scale with the budget actually in force."""

    def setUp(self):
        import paradiso_backend as pb

        for name, value in (
            ("OPENROUTER_TIMEOUT_SECONDS", 60.0),
            ("OPENROUTER_CHAIN_BUDGET_SECONDS", 45.0),
            ("OPENROUTER_FALLBACK_RESERVE_SECONDS", 12.0),
            ("OPENROUTER_MIN_CANDIDATE_ATTEMPT_SECONDS", 3.5),
        ):
            patcher = patch.object(pb, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.pb = pb

    def test_default_chain_behaviour_is_unchanged(self):
        attempt = self.pb._openrouter_candidate_attempt_timeout(45.0, has_fallback=True)
        self.assertAlmostEqual(attempt, 33.0)
        # Below the reserve's usefulness gate the next candidate still gets the
        # whole remainder rather than subdividing an already-small tail.
        self.assertAlmostEqual(
            self.pb._openrouter_candidate_attempt_timeout(15.0, has_fallback=True), 15.0
        )
        self.assertAlmostEqual(
            self.pb._openrouter_candidate_attempt_timeout(45.0, has_fallback=False), 45.0
        )

    def test_short_budget_keeps_a_reserve_for_the_alternate_candidate(self):
        attempt = self.pb._openrouter_candidate_attempt_timeout(
            12.0, has_fallback=True, budget=12.0
        )
        self.assertAlmostEqual(attempt, 6.0)
        self.assertLess(attempt, 12.0)
        # The tail candidate is bounded by what is left, not by the 60s ceiling.
        self.assertAlmostEqual(
            self.pb._openrouter_candidate_attempt_timeout(6.0, has_fallback=False, budget=12.0),
            6.0,
        )

    def test_default_enforcement_budget_is_also_two_shot(self):
        attempt = self.pb._openrouter_candidate_attempt_timeout(
            8.0, has_fallback=True, budget=8.0
        )
        self.assertAlmostEqual(attempt, 4.0)

    def test_a_supplied_budget_is_shared_across_every_remaining_candidate(self):
        """Successes cluster around three seconds and failures hang to their cap,
        so what raises the hit rate on a short deadline is more independent
        tries, not a longer wait on one model."""
        first = self.pb._openrouter_candidate_attempt_timeout(
            12.0, has_fallback=True, budget=12.0, remaining_candidates=3
        )
        self.assertAlmostEqual(first, 4.0)
        second = self.pb._openrouter_candidate_attempt_timeout(
            8.0, has_fallback=True, budget=12.0, remaining_candidates=2
        )
        self.assertAlmostEqual(second, 4.0)
        third = self.pb._openrouter_candidate_attempt_timeout(
            4.0, has_fallback=False, budget=12.0, remaining_candidates=1
        )
        self.assertAlmostEqual(third, 4.0)

    def test_slicing_stops_at_the_floor_instead_of_handing_out_slivers(self):
        # A slice under the floor would cut off a model that was going to
        # answer, which is worse than not asking it. The remainder goes to this
        # candidate whole.
        attempt = self.pb._openrouter_candidate_attempt_timeout(
            6.0, has_fallback=True, budget=12.0, remaining_candidates=4
        )
        self.assertAlmostEqual(attempt, 6.0)

    def test_the_floor_never_exceeds_what_is_left(self):
        attempt = self.pb._openrouter_candidate_attempt_timeout(
            1.0, has_fallback=True, budget=12.0, remaining_candidates=3
        )
        self.assertAlmostEqual(attempt, 1.0)


if __name__ == "__main__":
    unittest.main()
