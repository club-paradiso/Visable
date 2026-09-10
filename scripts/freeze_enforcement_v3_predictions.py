#!/usr/bin/env python3
"""Offline CLI for blind Enforcement Intelligence v3 outcome evaluation.

The CLI deliberately has no option for user-supplied freeze timestamps. A
freeze uses the current UTC clock and records canonical digests for the whole
cohort. This is tamper-evident local evidence, not external notarization.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_outcome_intake import load_json, write_json  # noqa: E402
from services.enforcement_prediction_freeze import (  # noqa: E402
    EnforcementPredictionFreezeError,
    build_blind_case_set,
    evaluate_frozen_outcomes,
    freeze_predictions,
    validate_blind_case_set,
    validate_prediction_freeze,
)


def _different_paths(input_path: Path, output_path: Path) -> None:
    if input_path.resolve() == output_path.resolve():
        raise EnforcementPredictionFreezeError("input and output paths must differ")


def _cmd_export_cases(args: argparse.Namespace) -> int:
    src = Path(args.input)
    dst = Path(args.output)
    _different_paths(src, dst)
    cases = build_blind_case_set(load_json(src))
    write_json(dst, cases)
    print(f"blind_cases={len(cases['records'])} case_set_id={cases['caseSetId']} output={dst}")
    return 0


def _cmd_validate_cases(args: argparse.Namespace) -> int:
    cases = validate_blind_case_set(load_json(Path(args.input)))
    print(f"blind_case_set_valid records={len(cases['records'])} case_set_id={cases['caseSetId']}")
    return 0


def _cmd_freeze(args: argparse.Namespace) -> int:
    cases_path = Path(args.cases)
    predictions_path = Path(args.predictions)
    dst = Path(args.output)
    if dst.resolve() in {cases_path.resolve(), predictions_path.resolve()}:
        raise EnforcementPredictionFreezeError("freeze output path must differ from all input paths")
    cases = load_json(cases_path)
    predictions = load_json(predictions_path)
    frozen = freeze_predictions(cases, predictions)
    write_json(dst, frozen)
    print(
        f"frozen_predictions={len(frozen['records'])} freeze_id={frozen['freezeId']} "
        f"frozen_at={frozen['frozenAt']} output={dst}"
    )
    return 0


def _cmd_validate_freeze(args: argparse.Namespace) -> int:
    frozen = validate_prediction_freeze(load_json(Path(args.input)))
    print(f"prediction_freeze_valid records={len(frozen['records'])} freeze_id={frozen['freezeId']}")
    return 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    report = evaluate_frozen_outcomes(
        load_json(Path(args.intake)),
        load_json(Path(args.freeze)),
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        if output_path.resolve() in {Path(args.intake).resolve(), Path(args.freeze).resolve()}:
            raise EnforcementPredictionFreezeError("evaluation output path must differ from input paths")
        write_json(output_path, report)
        print(
            f"blind_evaluation={report['evaluation']['status']} reviewed={report['reviewedCases']} "
            f"cohort={report['cohortCases']} output={output_path}"
        )
    else:
        print(rendered)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Freeze and evaluate a complete outcome-blind Enforcement Intelligence v3 cohort."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser(
        "export-blind-cases",
        help="Export all pre-outcome cases from a safe intake dataset without provenance or review metadata.",
    )
    export.add_argument("--input", required=True, help="De-identified safe intake JSON.")
    export.add_argument("--output", required=True, help="Blind case-set JSON destination.")
    export.set_defaults(func=_cmd_export_cases)

    validate_cases = sub.add_parser("validate-cases", help="Validate a blind case-set file and its digests.")
    validate_cases.add_argument("--input", required=True)
    validate_cases.set_defaults(func=_cmd_validate_cases)

    freeze = sub.add_parser(
        "freeze",
        help="Freeze exactly one public EnforcementPrediction per blind case using the current UTC clock.",
    )
    freeze.add_argument("--cases", required=True, help="Blind case-set JSON.")
    freeze.add_argument("--predictions", required=True, help="JSON object mapping every caseId to one prediction.")
    freeze.add_argument("--output", required=True, help="Frozen prediction bundle destination.")
    freeze.set_defaults(func=_cmd_freeze)

    validate_freeze = sub.add_parser("validate-freeze", help="Validate frozen predictions and all content digests.")
    validate_freeze.add_argument("--input", required=True)
    validate_freeze.set_defaults(func=_cmd_validate_freeze)

    evaluate = sub.add_parser(
        "evaluate",
        help="Join a frozen cohort to the later safe reviewed intake corpus and run the existing evaluator.",
    )
    evaluate.add_argument("--intake", required=True, help="Current de-identified intake JSON with review history.")
    evaluate.add_argument("--freeze", required=True, help="Previously frozen prediction bundle.")
    evaluate.add_argument("--output", help="Optional JSON report destination; stdout is used when omitted.")
    evaluate.set_defaults(func=_cmd_evaluate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (EnforcementPredictionFreezeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
