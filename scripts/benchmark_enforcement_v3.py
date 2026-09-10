#!/usr/bin/env python3
"""Run the deterministic Enforcement Intelligence v3 benchmark seed."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.enforcement_benchmark import run_benchmark  # noqa: E402

DEFAULT_FIXTURE = BACKEND / "tests" / "fixtures" / "enforcement_v3_benchmark_seed.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument(
        "--require-perfect",
        action="store_true",
        help="Exit non-zero unless all deterministic seed metrics are perfect.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    payload = json.loads(args.fixture.read_text(encoding="utf-8"))
    assessment_date = date.fromisoformat(payload["assessmentDate"])
    report = await run_benchmark(payload["cases"], assessment_date=assessment_date)
    report["datasetVersion"] = payload.get("datasetVersion")
    report["assessmentDate"] = payload["assessmentDate"]
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))

    if args.require_perfect:
        required = (
            report["exactCaseAccuracy"],
            report["materialFactAccuracy"],
            report["violationCodeAccuracy"],
            report["deterministicBaselineAccuracy"],
            report["abstention"]["precision"],
            report["abstention"]["recall"],
        )
        if any(value != 1.0 for value in required):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
