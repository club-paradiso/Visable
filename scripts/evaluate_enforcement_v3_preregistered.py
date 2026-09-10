#!/usr/bin/env python3
"""Offline CLI for preregistered Enforcement Intelligence v3 reporting."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_evaluation_plan import (  # noqa: E402
    EnforcementEvaluationPlanError,
    build_evaluation_plan,
    evaluate_with_plan,
    validate_evaluation_plan,
)
from services.enforcement_outcome_intake import load_json, write_json  # noqa: E402


def _parse_metric(value: str) -> dict:
    name, separator, minimum_raw = value.partition("=")
    if not separator or not name.strip() or not minimum_raw.strip():
        raise argparse.ArgumentTypeError("metric must use METRIC=MINIMUM_ELIGIBLE_CASES")
    try:
        minimum = int(minimum_raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("metric minimum must be an integer") from exc
    if minimum < 1:
        raise argparse.ArgumentTypeError("metric minimum must be at least 1")
    return {"metric": name.strip().upper(), "minimumEligibleCases": minimum}


def _different_paths(output: Path, *inputs: Path) -> None:
    resolved = output.resolve()
    if any(resolved == item.resolve() for item in inputs):
        raise EnforcementEvaluationPlanError("output path must differ from all input paths")


def _cmd_create(args: argparse.Namespace) -> int:
    cases_path = Path(args.cases)
    output_path = Path(args.output)
    _different_paths(output_path, cases_path)
    metrics = sorted(args.metric, key=lambda item: item["metric"])
    plan = build_evaluation_plan(load_json(cases_path), metrics=metrics)
    write_json(output_path, plan)
    print(f"evaluation_plan={plan['planId']} metrics={len(plan['metrics'])} output={output_path}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    plan = validate_evaluation_plan(load_json(Path(args.input)))
    print(f"evaluation_plan_valid plan_id={plan['planId']} metrics={len(plan['metrics'])}")
    return 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    freeze_path = Path(args.freeze)
    intake_path = Path(args.intake)
    output_path = Path(args.output)
    _different_paths(output_path, plan_path, freeze_path, intake_path)
    report = evaluate_with_plan(
        load_json(intake_path),
        load_json(freeze_path),
        load_json(plan_path),
    )
    write_json(output_path, report)
    print(
        f"preregistered_evaluation={report['status']} plan_id={report['planId']} "
        f"cohort={report['cohort']['cohortCases']} output={output_path}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and apply an outcome-blind preregistered Enforcement v3 reporting plan."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser(
        "create-plan",
        help="Bind metric choices and minimum eligible-case counts to an existing blind case set.",
    )
    create.add_argument("--cases", required=True, help="Blind case-set JSON from the freeze protocol.")
    create.add_argument(
        "--metric",
        action="append",
        required=True,
        type=_parse_metric,
        help="Repeatable METRIC=MINIMUM_ELIGIBLE_CASES, e.g. PREDICTION_AVAILABILITY=20.",
    )
    create.add_argument("--output", required=True, help="Evaluation-plan JSON destination.")
    create.set_defaults(func=_cmd_create)

    validate = sub.add_parser("validate-plan", help="Validate a plan and its content-derived planId.")
    validate.add_argument("--input", required=True)
    validate.set_defaults(func=_cmd_validate)

    evaluate = sub.add_parser(
        "evaluate",
        help="Rerun blind evaluation and apply only the preregistered reporting rules.",
    )
    evaluate.add_argument("--plan", required=True)
    evaluate.add_argument("--freeze", required=True)
    evaluate.add_argument("--intake", required=True)
    evaluate.add_argument("--output", required=True)
    evaluate.set_defaults(func=_cmd_evaluate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (EnforcementEvaluationPlanError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
