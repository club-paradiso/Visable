from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import run_hikorea_monitor_smoke as smoke  # noqa: E402


class HikoreaMonitorSmokeHelperTests(unittest.TestCase):
    def _fake_runner(self, calls):
        def fake_run(cmd):
            calls.append(cmd)
            if any(part.endswith("check_source_updates.py") for part in cmd):
                payload = {
                    "mode": "catalog_dry_run",
                    "allow_network": "--allow-network" in cmd,
                    "results": [
                        {
                            "source_id": "hikorea_notice_index",
                            "state": "skipped",
                            "reason": "network_disabled",
                        }
                    ],
                }
                return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
            if any(part.endswith("generate_source_update_brief.py") for part in cmd):
                output_path = cmd[cmd.index("--output") + 1]
                with open(output_path, "w", encoding="utf-8") as fh:
                    fh.write("# Preview\n")
                return subprocess.CompletedProcess(cmd, 0, "", "")
            raise AssertionError(f"unexpected command: {cmd}")

        return fake_run

    def test_helper_defaults_to_no_network_and_writes_outputs(self):
        calls = []
        with tempfile.TemporaryDirectory() as td:
            buf = io.StringIO()
            with mock.patch.object(smoke, "_run_command", self._fake_runner(calls)):
                with redirect_stdout(buf):
                    rc = smoke.main(
                        [
                            "--output-dir",
                            td,
                            "--run-label",
                            "test-run",
                            "--python",
                            "python3",
                        ]
                    )

            json_path = os.path.join(td, "test-run_source_monitor.json")
            brief_path = os.path.join(td, "test-run_source_update_brief.md")
            self.assertTrue(os.path.isfile(json_path))
            self.assertTrue(os.path.isfile(brief_path))
            with open(json_path, "r", encoding="utf-8") as fh:
                saved = json.load(fh)

        self.assertEqual(rc, 0)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("--allow-network", calls[0])
        self.assertIn("--catalog-dry-run", calls[0])
        self.assertIn("--json", calls[0])
        self.assertFalse(saved["allow_network"])
        self.assertIn("Network: disabled", buf.getvalue())
        self.assertIn("GitHub Issues: disabled", buf.getvalue())

    def test_helper_allows_network_only_with_explicit_flag(self):
        calls = []
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(smoke, "_run_command", self._fake_runner(calls)):
                with redirect_stdout(io.StringIO()):
                    rc = smoke.main(
                        [
                            "--allow-network",
                            "--output-dir",
                            td,
                            "--run-label",
                            "allow-test",
                            "--python",
                            "python3",
                        ]
                    )

        self.assertEqual(rc, 0)
        self.assertIn("--allow-network", calls[0])

    def test_issue_preview_only_forwards_preview_flag(self):
        calls = []
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(smoke, "_run_command", self._fake_runner(calls)):
                with redirect_stdout(io.StringIO()):
                    rc = smoke.main(
                        [
                            "--issue-preview",
                            "--output-dir",
                            td,
                            "--run-label",
                            "preview-test",
                            "--python",
                            "python3",
                        ]
                    )

        self.assertEqual(rc, 0)
        self.assertIn("--issue-preview", calls[1])
        self.assertNotIn("gh", calls[1])


if __name__ == "__main__":
    unittest.main()
