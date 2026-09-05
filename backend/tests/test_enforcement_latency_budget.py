"""Regression coverage for the bounded enforcement AI path.

Clear cases must stay local, ambiguous cases may use AI, and enforcement model
routing must remain isolated from deploy-wide Fast-tier overrides.
"""

from __future__ import annotations

import json
import os
import sys
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
            ["google/gemma-4-26b-a4b-it:free", "openai/gpt-oss-20b:free"],
        )
        self.assertNotIn("stale/example-model:free", plan["candidates"])
        self.assertEqual(len(plan["candidates"]), 2)


if __name__ == "__main__":
    unittest.main()
