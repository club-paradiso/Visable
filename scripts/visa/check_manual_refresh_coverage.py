#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUSES_DIR = ROOT / "backend/data/visa_authoring/statuses"
MATRIX = ROOT / "docs/data/2026_06_17_status_review_matrix.json"
COVERAGE = ROOT / "docs/data/2026_06_17_subcode_coverage_report.json"

REQUIRED_FIELDS = {
    "identity",
    "period",
    "activityScope",
    "manualDomains",
    "subcodes",
    "procedures",
    "documents",
    "summaries",
    "sourceMetadata",
    "searchAliases",
}


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    errors: list[str] = []
    matrix = load_json(MATRIX)
    coverage = load_json(COVERAGE)

    status_files = sorted(str(path.relative_to(ROOT)) for path in STATUSES_DIR.glob("*.json"))
    entries = matrix.get("entries") or []
    by_file = {entry.get("file"): entry for entry in entries}

    missing_files = sorted(set(status_files) - set(by_file))
    extra_files = sorted(set(by_file) - set(status_files))
    if missing_files:
        errors.append(f"status files missing from matrix: {missing_files}")
    if extra_files:
        errors.append(f"matrix references non-status files: {extra_files}")
    if len(entries) != len(status_files):
        errors.append(f"matrix entry count {len(entries)} != status file count {len(status_files)}")

    for file in status_files:
        entry = by_file.get(file)
        if not entry:
            continue
        code = entry.get("code", file)
        if not entry.get("reviewed"):
            errors.append(f"{code}: reviewed is not true")
        fields = entry.get("fieldsReviewed") or {}
        missing_fields = sorted(REQUIRED_FIELDS - set(fields))
        false_fields = sorted(field for field in REQUIRED_FIELDS if fields.get(field) is not True)
        if missing_fields:
            errors.append(f"{code}: fieldsReviewed missing fields {missing_fields}")
        if false_fields:
            errors.append(f"{code}: fields not marked reviewed {false_fields}")
        if entry.get("changed") and not entry.get("changeSummary"):
            errors.append(f"{code}: changed=true without changeSummary")
        if entry.get("unresolvedIssues") and not entry.get("needsManualReview"):
            errors.append(f"{code}: unresolvedIssues present but needsManualReview is not true")

    issue_counts = (coverage.get("summary") or {}).get("issueCounts") or {}
    blocking = {key: value for key, value in issue_counts.items() if value}
    if blocking:
        errors.append(f"subcode coverage report still has blocking issues: {blocking}")
    if not (coverage.get("summary") or {}).get("passes"):
        errors.append("subcode coverage report summary.passes is not true")

    # Generated files must match the authoring layer and each other. This does
    # not prove intent, but it catches manual edits that were not regenerated.
    build_check = subprocess.run(
        [sys.executable, "scripts/visa/build_visa_data.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if build_check.returncode != 0:
        errors.append("visa_data.json is not generated from authoring; run scripts/visa/build_visa_data.py")
    sync_check = subprocess.run(
        [sys.executable, "scripts/sync_visa_data.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if sync_check.returncode != 0:
        errors.append("backend/data/visas.json is not synchronized with visa_data.json")

    if errors:
        print(f"[manual-refresh-coverage] FAIL — {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        "[manual-refresh-coverage] OK — "
        f"{len(status_files)} status files reviewed; required fields reviewed; "
        "coverage report passes; generated files are deterministic and synced."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
