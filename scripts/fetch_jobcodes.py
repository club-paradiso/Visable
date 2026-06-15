#!/usr/bin/env python3
"""DEPRECATED shim — superseded by scripts/build_employment_reporting_dataset.py.

The employment-reporting runtime (data/jobcode_master.json) is now an enriched,
type-scoped KSCO8/KSIC11 dataset with per-row metadata. The canonical, reproducible
builder is:

    python3 scripts/build_employment_reporting_dataset.py

This shim delegates to it so existing invocations / docs keep working and never
re-emit the old flat schema. To ship the full 1,999-row KSCO8 occupation table,
drop data/generated/employment_reporting_ksco8_full_candidate.csv (produced by
scripts/extract_employment_reporting_full_tables.py) and re-run the builder.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_employment_reporting_dataset as builder  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    print("NOTE: scripts/fetch_jobcodes.py is deprecated; delegating to "
          "scripts/build_employment_reporting_dataset.py", file=sys.stderr)
    return builder.main()


if __name__ == "__main__":
    raise SystemExit(main())
