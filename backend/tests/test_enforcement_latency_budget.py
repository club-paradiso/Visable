"""Regression coverage for the bounded enforcement AI path.

Clear cases must stay local, ambiguous cases may use AI, and enforcement model
routing must remain isolated from deploy-wide Fast-tier overrides.
"""

from __future__ import annotations

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
