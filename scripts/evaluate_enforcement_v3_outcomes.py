#!/usr/bin/env python3
"""Evaluate Enforcement v3 predictions against independently reviewed outcomes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.enforcement_outcome_evaluation import (  # noqa: E402
    evaluate_outcome_predictions,
    load_outcome_ground_truth,
)

DEFAULT_GROUND_TRUTH = BACKEND / "data" / "enforcement" / "outcome_ground_truth.template.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=DEFAULT_GROUND_TRUTH,
        help="Reviewed, de-identified outcome dataset. The checked-in default is intentionally empty.",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        help="JSON object mapping caseId to EnforcementPrediction public objects.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ground_truth = load_outcome_ground_truth(args.ground_truth)
    predictions = {}
    if args.predictions:
        predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
        if not isinstance(predictions, dict):
            raise ValueError("predictions file must be an object keyed by caseId")
    report = evaluate_outcome_predictions(ground_truth, predictions)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
