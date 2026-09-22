"""/health must say which commit is actually serving.

A post-deploy smoke cannot distinguish a finished deploy from the previous one
still answering: both report ``status: ok``. Reporting the build commit is what
lets the caller wait for its own commit instead of testing whatever happened to
be running, so the field's presence, its precedence and its validation are
pinned here rather than left to the deploy environment.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import paradiso_backend as pb  # noqa: E402

COMMIT = "0123456789abcdef0123456789abcdef01234567"
OTHER_COMMIT = "fedcba9876543210fedcba9876543210fedcba98"

_BUILD_ENV_NAMES = (
    "PARADISO_BUILD_COMMIT",
    "RAILWAY_GIT_COMMIT_SHA",
    "SOURCE_COMMIT",
    "GIT_COMMIT",
)


def _clean_env(**overrides):
    values = {name: "" for name in _BUILD_ENV_NAMES}
    values.update(overrides)
    return patch.dict(os.environ, values, clear=False)


class DeployedBuildMetadataTests(unittest.TestCase):
    def test_reports_the_railway_commit(self):
        with _clean_env(RAILWAY_GIT_COMMIT_SHA=COMMIT):
            build = pb._deployed_build_metadata()
        self.assertEqual(build["commit"], COMMIT)
        self.assertEqual(build["commit_source"], "RAILWAY_GIT_COMMIT_SHA")
        self.assertTrue(build["commit_reported"])

    def test_explicit_override_wins_over_the_platform_variable(self):
        with _clean_env(PARADISO_BUILD_COMMIT=COMMIT, RAILWAY_GIT_COMMIT_SHA=OTHER_COMMIT):
            build = pb._deployed_build_metadata()
        self.assertEqual(build["commit"], COMMIT)
        self.assertEqual(build["commit_source"], "PARADISO_BUILD_COMMIT")

    def test_absent_commit_is_reported_as_absent_not_guessed(self):
        with _clean_env():
            build = pb._deployed_build_metadata()
        self.assertEqual(build["commit"], "")
        self.assertEqual(build["commit_source"], "")
        self.assertFalse(build["commit_reported"])

    def test_a_malformed_value_is_never_echoed(self):
        # /health is public. A misconfigured env var must not become arbitrary
        # text in the response, and must not be mistaken for a real commit.
        for bad in ("not a sha", "../../etc/passwd", "<script>", "abc", "g" * 40, COMMIT + "0"):
            with self.subTest(value=bad), _clean_env(RAILWAY_GIT_COMMIT_SHA=bad):
                build = pb._deployed_build_metadata()
                self.assertFalse(build["commit_reported"])
                self.assertEqual(build["commit"], "")

    def test_a_short_sha_is_accepted_and_normalized(self):
        with _clean_env(PARADISO_BUILD_COMMIT="  ABCDEF1  "):
            build = pb._deployed_build_metadata()
        self.assertEqual(build["commit"], "abcdef1")
        self.assertTrue(build["commit_reported"])

    def test_falls_through_to_the_next_source_when_one_is_malformed(self):
        with _clean_env(PARADISO_BUILD_COMMIT="not-a-sha", RAILWAY_GIT_COMMIT_SHA=COMMIT):
            build = pb._deployed_build_metadata()
        self.assertEqual(build["commit"], COMMIT)
        self.assertEqual(build["commit_source"], "RAILWAY_GIT_COMMIT_SHA")


class HealthBuildFieldTests(unittest.TestCase):
    def test_health_exposes_the_build_block(self):
        from fastapi.testclient import TestClient

        with _clean_env(RAILWAY_GIT_COMMIT_SHA=COMMIT):
            with TestClient(pb.app) as client:
                payload = client.get("/health").json()

        self.assertEqual(payload["status"], "ok")
        build = payload["build"]
        self.assertEqual(build["commit"], COMMIT)
        self.assertEqual(build["commit_source"], "RAILWAY_GIT_COMMIT_SHA")
        self.assertTrue(build["commit_reported"])

    def test_health_never_leaks_a_credential_through_the_build_block(self):
        from fastapi.testclient import TestClient

        with _clean_env(RAILWAY_GIT_COMMIT_SHA=COMMIT), \
                patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-should-never-appear"}, clear=False):
            with TestClient(pb.app) as client:
                payload = client.get("/health").json()

        self.assertNotIn("sk-should-never-appear", str(payload))
        self.assertEqual(set(payload["build"]), {"commit", "commit_source", "commit_reported"})


if __name__ == "__main__":
    unittest.main()
