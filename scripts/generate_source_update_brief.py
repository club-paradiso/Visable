#!/usr/bin/env python3
"""Generate human-readable source update briefs from monitor JSON output.

This script is preview-only. It reads saved output from
``scripts/check_source_updates.py`` and writes or prints a Markdown brief. It
does not perform network requests and does not create GitHub Issues.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

_CHANGE_STATES = {"changed", "missing"}
_BLOCKED_REASONS = {
    "blocked_host",
    "requires_login",
    "scrape_not_allowed",
    "unsupported_domain",
    "unsupported_source_type",
    "response_too_large",
}
_INFORMATIONAL_REASONS = {
    "network_disabled",
    "monitor_disabled",
    "candidate_disabled",
    "not_configured",
    "no_url",
}


def _load_input(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: failed to read {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {path} must contain a JSON object")
    results = data.get("results", [])
    if not isinstance(results, list):
        raise SystemExit(f"ERROR: {path} field 'results' must be a list")
    return data


def _source_key(rec: Dict[str, Any]) -> str:
    return str(rec.get("source_id") or rec.get("id") or "unknown_source")


def _source_type(rec: Dict[str, Any]) -> str:
    return str(rec.get("source_type") or rec.get("type") or "unknown")


def _legal_sensitivity(rec: Dict[str, Any]) -> str:
    return str(rec.get("legal_sensitivity") or "").lower()


def _state(rec: Dict[str, Any]) -> str:
    return str(rec.get("state") or "unknown")


def _reason(rec: Dict[str, Any]) -> str:
    return str(rec.get("reason") or "")


def _brief_date(data: Dict[str, Any], override: Optional[str] = None) -> str:
    if override:
        return override
    for key in ("checked_at", "generated_at", "created_at"):
        value = data.get(key)
        if isinstance(value, str) and value[:10]:
            return value[:10]
    for rec in data.get("results", []):
        if isinstance(rec, dict):
            value = rec.get("checked_at") or rec.get("fetched_at")
            if isinstance(value, str) and value[:10]:
                return value[:10]
    return date.today().isoformat()


def _summarize_counts(results: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {"total": 0}
    for rec in results:
        counts["total"] += 1
        state = _state(rec)
        counts[state] = counts.get(state, 0) + 1
    return counts


def _classify_record(rec: Dict[str, Any]) -> str:
    state = _state(rec)
    reason = _reason(rec)
    source_type = _source_type(rec)
    legal_sensitivity = _legal_sensitivity(rec)

    if state == "no_baseline":
        return "review"
    if state in _CHANGE_STATES:
        if legal_sensitivity == "high":
            return "high"
        if source_type == "notice_index":
            return "high" if legal_sensitivity == "high" else "medium"
        return "medium"
    if reason in _BLOCKED_REASONS or state == "blocked":
        return "blocked"
    if reason in _INFORMATIONAL_REASONS or state in {"skipped", "network_skipped"}:
        return "informational"
    if state in {"unchanged", "fetched"}:
        return "low"
    return "review"


def _bucket_results(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    buckets = {
        "high": [],
        "medium": [],
        "low": [],
        "blocked": [],
        "informational": [],
        "review": [],
    }
    for rec in results:
        buckets[_classify_record(rec)].append(rec)
    return buckets


def _summary_line(rec: Dict[str, Any]) -> str:
    parts = [
        f"`{_source_key(rec)}`",
        f"state=`{_state(rec)}`",
    ]
    if _reason(rec):
        parts.append(f"reason=`{_reason(rec)}`")
    if rec.get("title"):
        parts.append(f"title=\"{rec['title']}\"")
    if rec.get("url"):
        parts.append(f"url={rec['url']}")
    if rec.get("content_hash"):
        parts.append(f"hash=`{rec['content_hash']}`")
    return "- " + " ".join(parts)


def _append_section(
    lines: List[str],
    title: str,
    records: List[Dict[str, Any]],
    empty_text: str,
) -> None:
    lines.append(f"## {title}")
    if records:
        for rec in sorted(records, key=_source_key):
            lines.append(_summary_line(rec))
    else:
        lines.append(empty_text)
    lines.append("")


def _recommended_action(buckets: Dict[str, List[Dict[str, Any]]]) -> str:
    if buckets["high"]:
        return (
            "Review high-priority source changes before preparing any downstream "
            "briefing or data update."
        )
    if buckets["medium"]:
        return (
            "Review medium-priority source changes and decide whether a manual "
            "operator note is needed."
        )
    if buckets["review"]:
        return (
            "Create or confirm baselines for review-needed records before "
            "treating future changes as meaningful."
        )
    if buckets["blocked"]:
        return (
            "Resolve blocked or safety-related source checks before enabling any "
            "manual smoke test."
        )
    return "No source-change action is needed from this report."


def generate_markdown(
    data: Dict[str, Any],
    *,
    issue_preview: bool = False,
    brief_date: Optional[str] = None,
) -> str:
    results = [rec for rec in data.get("results", []) if isinstance(rec, dict)]
    counts = _summarize_counts(results)
    buckets = _bucket_results(results)
    changed_total = len(buckets["high"]) + len(buckets["medium"])
    review_records = buckets["high"] + buckets["medium"] + buckets["review"]
    review_records += buckets["blocked"]

    lines: List[str] = []
    if issue_preview:
        lines.append("<!-- GitHub Issue preview only: no issue was created. -->")
        lines.append("")
    lines.append(f"# Paradiso Source Update Brief - {_brief_date(data, brief_date)}")
    lines.append("")
    lines.append(
        "Detected source changes are not automatically user-facing legal updates. "
        "Human review is required before any production data or guidance changes."
    )
    lines.append("")
    lines.append("## Summary Counts")
    lines.append(f"- Total records: {counts.get('total', 0)}")
    lines.append(f"- High-priority changes: {len(buckets['high'])}")
    lines.append(f"- Medium-priority changes: {len(buckets['medium'])}")
    lines.append(f"- Review-needed records: {len(buckets['review'])}")
    lines.append(f"- Blocked or safety-skipped records: {len(buckets['blocked'])}")
    lines.append(f"- Informational skipped records: {len(buckets['informational'])}")
    lines.append(f"- Low-priority/no-op records: {len(buckets['low'])}")
    lines.append(f"- Changed records requiring review: {changed_total}")
    lines.append("")
    _append_section(
        lines,
        "High-Priority Changes",
        buckets["high"],
        "No high-priority changes detected.",
    )
    _append_section(
        lines,
        "Medium-Priority Changes",
        buckets["medium"],
        "No medium-priority changes detected.",
    )
    _append_section(
        lines,
        "Low-Priority / No-Op",
        buckets["low"],
        "No low-priority or no-op records reported.",
    )
    blocked_and_skipped = buckets["blocked"] + buckets["informational"]
    _append_section(
        lines,
        "Blocked / Skipped Sources",
        blocked_and_skipped,
        "No blocked or skipped sources reported.",
    )
    _append_section(
        lines,
        "Records Requiring Human Review",
        review_records,
        "No records require human review from this report.",
    )
    lines.append("## Recommended Next Action")
    lines.append(_recommended_action(buckets))
    lines.append("")
    if issue_preview:
        lines.append("## Issue Preview Status")
        lines.append(
            "Preview only. This script does not create GitHub Issues or require "
            "a GitHub token."
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_output(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown source update brief from monitor JSON."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to source monitor JSON output.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the Markdown brief. Prints to stdout if omitted.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown",),
        default="markdown",
        help="Output format (default: %(default)s).",
    )
    parser.add_argument(
        "--issue-preview",
        action="store_true",
        help="Format as a GitHub Issue preview without creating an issue.",
    )
    parser.add_argument(
        "--brief-date",
        help="Override brief date as YYYY-MM-DD for deterministic output.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    data = _load_input(args.input)
    markdown = generate_markdown(
        data,
        issue_preview=args.issue_preview,
        brief_date=args.brief_date,
    )
    if args.output:
        _write_output(args.output, markdown)
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
