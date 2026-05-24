from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
FIXTURES_DIR = os.path.join(THIS_DIR, "fixtures")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import generate_source_update_brief as brief  # noqa: E402


def _fixture_path(name: str) -> str:
    return os.path.join(FIXTURES_DIR, name)


class SourceUpdateBriefTests(unittest.TestCase):
    def _render_fixture(self, name: str, *, issue_preview: bool = False) -> str:
        data = brief._load_input(_fixture_path(name))
        return brief.generate_markdown(data, issue_preview=issue_preview)

    def test_markdown_contains_expected_sections(self):
        markdown = self._render_fixture("source_monitor_changed_notice.json")

        self.assertIn("# Paradiso Source Update Brief - 2026-05-24", markdown)
        self.assertIn("## Summary Counts", markdown)
        self.assertIn("## High-Priority Changes", markdown)
        self.assertIn("## Medium-Priority Changes", markdown)
        self.assertIn("## Low-Priority / No-Op", markdown)
        self.assertIn("## Blocked / Skipped Sources", markdown)
        self.assertIn("## Records Requiring Human Review", markdown)
        self.assertIn("## Recommended Next Action", markdown)
        self.assertIn("not automatically user-facing legal updates", markdown)

    def test_notice_index_change_is_medium_priority_by_default(self):
        markdown = self._render_fixture("source_monitor_changed_notice.json")

        self.assertIn("No high-priority changes detected.", markdown)
        self.assertIn("`hikorea_notice_index` state=`changed`", markdown)
        self.assertIn("- Medium-priority changes: 1", markdown)

    def test_high_sensitivity_change_is_high_priority(self):
        markdown = self._render_fixture(
            "source_monitor_high_sensitivity_changed.json"
        )

        self.assertIn("- High-priority changes: 1", markdown)
        high_section = markdown.split("## High-Priority Changes", 1)[1]
        high_section = high_section.split("## Medium-Priority Changes", 1)[0]
        self.assertIn("moj_seasonal_worker_notice_stream", high_section)

    def test_skipped_and_blocked_records_are_not_treated_as_changes(self):
        markdown = self._render_fixture("source_monitor_blocked_skipped.json")

        self.assertIn("- High-priority changes: 0", markdown)
        self.assertIn("- Medium-priority changes: 0", markdown)
        self.assertIn("- Blocked or safety-skipped records: 1", markdown)
        self.assertIn("- Informational skipped records: 1", markdown)
        blocked_section = markdown.split("## Blocked / Skipped Sources", 1)[1]
        blocked_section = blocked_section.split(
            "## Records Requiring Human Review", 1
        )[0]
        self.assertIn("blocked_host", blocked_section)
        self.assertIn("network_disabled", blocked_section)

    def test_no_baseline_is_review_needed_not_high_priority(self):
        markdown = self._render_fixture("source_monitor_no_baseline.json")

        self.assertIn("- High-priority changes: 0", markdown)
        self.assertIn("- Review-needed records: 1", markdown)
        review_section = markdown.split("## Records Requiring Human Review", 1)[1]
        self.assertIn("hikorea_materials_index", review_section)

    def test_issue_preview_does_not_create_issue(self):
        markdown = self._render_fixture(
            "source_monitor_changed_notice.json",
            issue_preview=True,
        )

        self.assertIn("GitHub Issue preview only", markdown)
        self.assertIn("Preview only. This script does not create GitHub Issues", markdown)
        self.assertNotIn("created issue", markdown.lower())

    def test_generator_exits_cleanly_on_empty_results(self):
        with tempfile.TemporaryDirectory() as td:
            input_path = os.path.join(td, "empty.json")
            with open(input_path, "w", encoding="utf-8") as fh:
                json.dump({"checked_at": "2026-05-24T12:00:00+00:00", "results": []}, fh)

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = brief.main(["--input", input_path])

        self.assertEqual(rc, 0)
        self.assertIn("- Total records: 0", buf.getvalue())
        self.assertIn("No source-change action is needed", buf.getvalue())

    def test_output_file_is_written(self):
        with tempfile.TemporaryDirectory() as td:
            output_path = os.path.join(td, "generated", "brief.md")
            rc = brief.main(
                [
                    "--input",
                    _fixture_path("source_monitor_no_changes.json"),
                    "--output",
                    output_path,
                ]
            )

            self.assertEqual(rc, 0)
            with open(output_path, "r", encoding="utf-8") as fh:
                markdown = fh.read()
            self.assertIn("No source-change action is needed", markdown)


if __name__ == "__main__":
    unittest.main()
