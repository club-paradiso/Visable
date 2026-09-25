#!/usr/bin/env python3
"""Execute the Railway live-smoke script against canned backend responses.

Why this exists
---------------
The smoke's readiness loop used to accept any healthy process as a ready one.
Railway deploys asynchronously, so for minutes after a merge the PREVIOUS
deploy is the healthy process, and the smoke exercised the code the merge had
just replaced — a backend fix could neither fail nor pass it. The loop now
waits for the commit under test, which only works if the loop actually gates on
it, so the loop is executed here rather than described.

Stdlib only and offline: ``urllib.request.urlopen`` is replaced with a canned
responder and ``time.sleep`` with a counter, so no network call and no real
waiting happen.
"""

from __future__ import annotations

import io
import json
import re
import sys
import time
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/railway-live-smoke.yml"

OUR_COMMIT = "a" * 40
PREVIOUS_COMMIT = "b" * 40


def load_embedded_script() -> str:
    """Return the python heredoc the workflow step runs, de-indented."""
    text = WORKFLOW.read_text(encoding="utf-8")
    try:
        body = text.split("python3 -u - <<'PY'\n", 1)[1].rsplit("          PY\n", 1)[0]
    except IndexError:  # pragma: no cover - the workflow shape changed
        raise AssertionError("could not locate the embedded python heredoc")
    lines = [line[10:] if line.startswith(" " * 10) else line for line in body.splitlines()]
    return "\n".join(lines)


def health_payload(commit: str | None) -> dict:
    """A fully healthy /health body, optionally reporting a build commit."""
    build = (
        {"commit": commit, "commit_source": "RAILWAY_GIT_COMMIT_SHA", "commit_reported": True}
        if commit
        else {"commit": "", "commit_source": "", "commit_reported": False}
    )
    return {
        "status": "ok",
        "service": "paradiso-backend",
        "build": build,
        "providers": {"openrouter": True},
        "provider_status": {"legal_evidence": {"configured": True}},
        "law_api": {
            "law_api_configured": True,
            "law_api_oc_configured": True,
            "law_api_key_fallback_configured": True,
            "law_api_credential_source": "LAW_API_OC",
        },
        "law_grounding_mode": "enabled",
        "law_grounding_effective_mode": "enabled",
        "law_grounding_active": True,
    }


LAW_OK = {"ok": True, "count": 3}
WAYMAKER_LIVE = {
    "answer": "synthetic live model answer",
    "provider": "openrouter",
    "final_model": "vendor/model:free",
    "selected_model": "vendor/model:free",
    "attempted_models": ["vendor/model:free"],
    "upstream_statuses": [],
    "deterministic_fallback_answer_used": False,
    "visa_code_detected": "D-2",
    "task_type_detected": "extension",
    "manual_grounding_status": "present",
}
WAYMAKER_DETERMINISTIC_FALLBACK = {
    "answer": "synthetic deterministic preparation note",
    "provider": "deterministic_fallback",
    "final_model": None,
    "selected_model": None,
    "attempted_models": ["vendor/model:free"],
    "upstream_statuses": [504],
    "deterministic_fallback_answer_used": True,
    "provider_error_type": "openrouter_chain_budget_exhausted",
    "chain_budget_exhausted": True,
    "visa_code_detected": "D-2",
    "task_type_detected": "extension",
    "manual_grounding_status": "present",
}
# The ordinary (non-diagnostics) projection a browser receives.
WAYMAKER_PUBLIC = {
    "answer": "유학(D-2) 체류기간 연장허가\n\n기본 서류\n• 신청서",
    "answer_mode": "fast",
    "answer_mode_requested": "fast",
    "answer_mode_auto_escalated": False,
    "deterministic_fallback_answer_used": False,
    "visa_code_detected": "D-2",
    "structured_answer": {
        "kind": "documents",
        "required_documents": {
            "common": [{"label": "신청서"}],
            "required": [{"label": "재정입증 서류"}],
            "conditional": [{"label": "수료증명서, 지도교수 및 유학담당자 확인서"}],
        },
    },
}
WAYMAKER_PUBLIC_LEAKY = {
    **WAYMAKER_PUBLIC,
    "provider": "openrouter",
    "answer": "### 필수 서류\n- 신청서 (외국인체류 안내매뉴얼 2026.6; source file 2026-06-23)",
}

ENFORCEMENT_LIVE = {
    "legalBaseline": {"status": "AVAILABLE", "baselineAmountKrw": 2_000_000},
    "prediction": {
        "status": "LIMITED",
        "modelId": "vendor/model:free",
        "monetaryPrediction": {"legalBaselineAmountKrw": 2_000_000},
    },
}
ENFORCEMENT_DEGRADED = {
    "legalBaseline": {"status": "AVAILABLE", "baselineAmountKrw": 2_000_000},
    "prediction": {"status": "UNAVAILABLE"},
}


class _FakeResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class SmokeRun:
    """One scripted execution of the embedded smoke script."""

    def __init__(self, health_sequence, enforcement=ENFORCEMENT_LIVE, waymaker=WAYMAKER_LIVE, public=WAYMAKER_PUBLIC, public_status=200):
        # health_sequence: the commit each successive /health call reports.
        # The last entry repeats once exhausted.
        self.health_sequence = list(health_sequence)
        self.enforcement = enforcement
        self.waymaker = waymaker
        self.public = public
        self.public_status = public_status
        self.health_calls = 0
        self.slept = 0.0
        self.stdout = ""
        self.stderr = ""
        self.exit_code = 0

    def _respond(self, request, timeout=None):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if "/health" in url:
            index = min(self.health_calls, len(self.health_sequence) - 1)
            self.health_calls += 1
            return _FakeResponse(json.dumps(health_payload(self.health_sequence[index])).encode())
        if "/api/legal/laws/search" in url:
            return _FakeResponse(json.dumps(LAW_OK).encode())
        if "/api/ask" in url:
            body = json.loads((getattr(request, "data", None) or b"{}").decode("utf-8"))
            if self.public_status != 200 and body.get("answer_mode") == "fast":
                detail = {"error": "answer_generation_unavailable", "message": "The answer could not be generated right now."}
                if body.get("diagnostics"):
                    detail.update({"error": "openrouter_provider_error", "provider_error_type": "invalid_request",
                                   "attempted_models": ["vendor/fast:free"], "upstream_statuses": [400]})
                raise urllib.error.HTTPError(url, self.public_status, "error", {},
                                             io.BytesIO(json.dumps({"detail": detail}).encode()))
            payload = self.waymaker if body.get("diagnostics") else self.public
            return _FakeResponse(json.dumps(payload).encode())
        if "/api/enforcement/analyze" in url:
            return _FakeResponse(json.dumps(self.enforcement).encode())
        if "/api/enforcement/provider-probe" in url:
            # A healthy provider contract on the synthetic case. This is the
            # production shape that matters: the standalone probe succeeds
            # while the real analysis path degrades, so the script must report
            # the degraded ANALYSIS rather than blame the provider.
            return _FakeResponse(json.dumps({
                "configured": True,
                "ok": True,
                "jsonObjectReturned": True,
                "predictionContractOk": True,
                "finalModel": "vendor/model:free",
            }).encode())
        raise AssertionError(f"unexpected request: {url}")

    def run(self):
        code = load_embedded_script()
        env = {"BACKEND_URL": "https://backend.example", "EXPECTED_COMMIT": OUR_COMMIT}
        out, err = io.StringIO(), io.StringIO()

        def fake_sleep(seconds):
            self.slept += seconds

        with patch.dict("os.environ", env, clear=False), \
                patch.object(urllib.request, "urlopen", self._respond), \
                patch.object(time, "sleep", fake_sleep), \
                redirect_stdout(out), redirect_stderr(err):
            try:
                exec(compile(code, "railway-live-smoke", "exec"), {"__name__": "__main__"})
            except SystemExit as exc:
                self.exit_code = int(exc.code or 0)
        self.stdout = out.getvalue()
        self.stderr = err.getvalue()
        return self


class RailwayLiveSmokeReadinessTests(unittest.TestCase):
    def test_waits_for_our_commit_instead_of_testing_the_previous_deploy(self):
        # The previous deploy answers healthily three times before ours lands.
        run = SmokeRun([PREVIOUS_COMMIT, PREVIOUS_COMMIT, PREVIOUS_COMMIT, OUR_COMMIT]).run()

        self.assertEqual(run.exit_code, 0, run.stderr)
        self.assertIn("waiting for " + OUR_COMMIT[:12], run.stdout)
        self.assertGreaterEqual(run.health_calls, 4)
        self.assertGreater(run.slept, 0)
        self.assertIn("matches this commit", run.stdout)
        self.assertIn('"deployed_commit_verified": true', run.stdout)
        # The law route must not be consulted while a stale deploy is serving:
        # that is what made a stale run look like a real one.
        self.assertEqual(run.stdout.count("law_ok=True"), 1)

    def test_a_backend_that_reports_no_commit_is_not_waited_on(self):
        run = SmokeRun([None]).run()

        self.assertEqual(run.exit_code, 0, run.stderr)
        self.assertEqual(run.slept, 0)
        self.assertIn("deploy verification: UNVERIFIED", run.stdout)
        self.assertIn("does not report a build commit", run.stdout)
        self.assertIn('"deployed_commit_verified": false', run.stdout)

    def test_a_verified_deploy_reports_no_caveat(self):
        run = SmokeRun([OUR_COMMIT]).run()

        self.assertEqual(run.exit_code, 0, run.stderr)
        self.assertEqual(run.slept, 0)
        self.assertNotIn("UNVERIFIED", run.stdout)
        self.assertIn("matches this commit", run.stdout)
        self.assertIn("waymaker_d2:", run.stdout)
        self.assertIn('"live_model_answer": true', run.stdout)

    def test_an_unverified_failure_says_the_result_may_be_a_previous_deploy(self):
        run = SmokeRun([None], enforcement=ENFORCEMENT_DEGRADED).run()

        self.assertEqual(run.exit_code, 1)
        self.assertIn("unavailable AI prediction", run.stderr)
        self.assertIn("may describe a previous deploy", run.stderr)

    def test_a_verified_failure_is_reported_without_the_caveat(self):
        run = SmokeRun([OUR_COMMIT], enforcement=ENFORCEMENT_DEGRADED).run()

        self.assertEqual(run.exit_code, 1)
        self.assertIn("unavailable AI prediction", run.stderr)
        self.assertNotIn("may describe a previous deploy", run.stderr)

    def test_public_waymaker_response_must_not_leak_provider_or_markdown(self):
        run = SmokeRun([OUR_COMMIT], public=WAYMAKER_PUBLIC_LEAKY).run()
        self.assertEqual(run.exit_code, 1, run.stdout + run.stderr)
        self.assertIn("waymaker_public_d2:", run.stdout)
        self.assertIn("leaks internal routing/source metadata", run.stderr)

    def test_public_waymaker_http_error_is_reported_with_diagnostics(self):
        run = SmokeRun([OUR_COMMIT], public=None, public_status=503).run()
        self.assertEqual(run.exit_code, 1, run.stdout + run.stderr)
        self.assertIn("waymaker_public_d2_diagnostics:", run.stdout)
        self.assertIn("returned HTTP 503", run.stderr)
        self.assertNotIn("leaks internal", run.stderr)

    def test_public_waymaker_response_must_carry_structured_checklist(self):
        no_structure = {k: v for k, v in WAYMAKER_PUBLIC.items() if k != "structured_answer"}
        run = SmokeRun([OUR_COMMIT], public=no_structure).run()
        self.assertEqual(run.exit_code, 1, run.stdout + run.stderr)
        self.assertIn("structured D-2 checklist", run.stderr)

    def test_waymaker_d2_requires_a_real_model_completion(self):
        run = SmokeRun([OUR_COMMIT], waymaker=WAYMAKER_DETERMINISTIC_FALLBACK).run()

        self.assertEqual(run.exit_code, 1)
        self.assertIn("did not produce a live model answer", run.stderr)
        self.assertIn('"deterministic_fallback": true', run.stdout)
        self.assertIn('"visa_code_detected": "D-2"', run.stdout)
        self.assertNotIn("enforcement:", run.stdout)


class RailwayLiveSmokeBudgetTests(unittest.TestCase):
    def test_the_deploy_wait_outlasts_a_real_build_and_fits_the_job_timeout(self):
        code = load_embedded_script()
        attempts = int(re.search(r"deploy_attempts = (\d+)", code).group(1))
        sleep_seconds = float(re.search(r"deploy_sleep_seconds = ([\d.]+)", code).group(1))
        timeout_minutes = int(
            re.search(r"timeout-minutes: (\d+)", WORKFLOW.read_text(encoding="utf-8")).group(1)
        )

        wait_budget = attempts * sleep_seconds
        # A Railway build of this backend takes minutes; 30 seconds never
        # covered it, which is how every post-merge run tested the old deploy.
        self.assertGreaterEqual(wait_budget, 240)
        # The wait plus the probes it guards must still fit the job timeout.
        self.assertLess(wait_budget, timeout_minutes * 60 * 0.6)


if __name__ == "__main__":
    unittest.main()
