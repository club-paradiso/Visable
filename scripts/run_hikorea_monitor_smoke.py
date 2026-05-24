#!/usr/bin/env python3
"""Run a local HiKorea/KIS source-monitor smoke test.

This helper chains the catalog source monitor and Markdown brief generator. It
is intentionally local-only by default, writes under ``tmp/``, and never creates
GitHub Issues or mutates production data.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import List, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_OUTPUT_DIR = os.path.join(REPO_ROOT, "tmp", "source-monitor-smoke")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _display_command(cmd: List[str]) -> str:
    return " ".join(cmd)


def _run_command(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def _build_monitor_command(args: argparse.Namespace) -> List[str]:
    cmd = [
        args.python,
        "scripts/check_source_updates.py",
        "--catalog-dry-run",
        "--json",
        "--list-disabled",
        "--fetch-timeout-seconds",
        str(args.fetch_timeout_seconds),
        "--fetch-max-bytes",
        str(args.fetch_max_bytes),
    ]
    if args.allow_network:
        cmd.append("--allow-network")
    return cmd


def _build_brief_command(
    args: argparse.Namespace,
    json_path: str,
    brief_path: str,
) -> List[str]:
    cmd = [
        args.python,
        "scripts/generate_source_update_brief.py",
        "--input",
        json_path,
        "--output",
        brief_path,
        "--format",
        "markdown",
    ]
    if args.issue_preview:
        cmd.append("--issue-preview")
    return cmd


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local HiKorea/KIS source-monitor smoke pipeline."
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Explicitly allow the source monitor's tightly allowlisted fetch path.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for JSON and Markdown outputs (default: %(default)s).",
    )
    parser.add_argument(
        "--run-label",
        default=None,
        help="Optional output filename label. Defaults to a UTC timestamp.",
    )
    parser.add_argument(
        "--issue-preview",
        action="store_true",
        help="Add issue-preview framing to Markdown without creating an issue.",
    )
    parser.add_argument(
        "--fetch-timeout-seconds",
        type=float,
        default=5.0,
        help="Timeout forwarded to check_source_updates.py (default: %(default)s).",
    )
    parser.add_argument(
        "--fetch-max-bytes",
        type=int,
        default=512 * 1024,
        help="Response-size cap forwarded to check_source_updates.py.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used for chained scripts (default: current Python).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    run_label = args.run_label or _timestamp()
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, f"{run_label}_source_monitor.json")
    brief_path = os.path.join(output_dir, f"{run_label}_source_update_brief.md")
    monitor_cmd = _build_monitor_command(args)
    brief_cmd = _build_brief_command(args, json_path, brief_path)

    print("Paradiso HiKorea/KIS source monitor smoke test")
    print("=" * 60)
    print(f"Network: {'explicitly allowed' if args.allow_network else 'disabled'}")
    print("GitHub Issues: disabled; this helper only writes local files")
    print("Scheduled monitoring: disabled")
    print("Production data mutation: disabled")
    print(f"Output directory: {output_dir}")
    print("")
    print("Running source monitor:")
    print(f"  {_display_command(monitor_cmd)}")
    monitor_result = _run_command(monitor_cmd)
    with open(json_path, "w", encoding="utf-8") as fh:
        fh.write(monitor_result.stdout)

    print("Running brief generator:")
    print(f"  {_display_command(brief_cmd)}")
    _run_command(brief_cmd)

    print("")
    print("Smoke-test outputs:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {brief_path}")
    print("")
    print(
        "Review both files manually before considering any workflow_dispatch "
        "proposal or downstream update."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
