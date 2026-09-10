#!/usr/bin/env python3
"""Offline CLI for de-identifying and promoting Enforcement v3 outcome corpora.

Secrets are read from environment variables, never command-line values, so they
are less likely to be persisted in shell history. The command never prints
record contents or secret material.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_outcome_intake import (  # noqa: E402
    EnforcementOutcomeIntakeError,
    load_json,
    normalize_private_intake_dataset,
    promote_reviewed_ground_truth,
    validate_safe_intake_dataset,
    write_json,
)

DEFAULT_RECORD_SECRET_ENV = "VISABLE_ENFORCEMENT_RECORD_HMAC_SECRET"
DEFAULT_REVIEWER_SECRET_ENV = "VISABLE_ENFORCEMENT_REVIEWER_HMAC_SECRET"


def _different_paths(input_path: Path, output_path: Path) -> None:
    if input_path.resolve() == output_path.resolve():
        raise EnforcementOutcomeIntakeError("input and output paths must differ")


def _required_secret(env_name: str) -> str:
    value = os.environ.get(env_name, "")
    if not value:
        raise EnforcementOutcomeIntakeError(f"required secret environment variable is unset: {env_name}")
    return value


def _cmd_deidentify(args: argparse.Namespace) -> int:
    src = Path(args.input)
    dst = Path(args.output)
    _different_paths(src, dst)
    private_data = load_json(src)
    safe = normalize_private_intake_dataset(
        private_data,
        record_secret=_required_secret(args.record_secret_env),
        reviewer_secret=_required_secret(args.reviewer_secret_env),
    )
    write_json(dst, safe)
    print(f"deidentified_records={len(safe['records'])} output={dst}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    src = Path(args.input)
    safe = validate_safe_intake_dataset(load_json(src))
    counts: dict[str, int] = {}
    for row in safe["records"]:
        stage = row["reviewStage"]
        counts[stage] = counts.get(stage, 0) + 1
    summary = ",".join(f"{key}={counts[key]}" for key in sorted(counts)) or "empty=0"
    print(f"safe_intake_valid records={len(safe['records'])} {summary}")
    return 0


def _cmd_promote(args: argparse.Namespace) -> int:
    src = Path(args.input)
    dst = Path(args.output)
    _different_paths(src, dst)
    ground_truth = promote_reviewed_ground_truth(load_json(src))
    write_json(dst, ground_truth)
    print(f"promoted_reviewed_records={len(ground_truth['records'])} output={dst}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare a private, reviewed Enforcement Intelligence v3 outcome corpus offline."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    deidentify = sub.add_parser(
        "deidentify",
        help="Convert private source/reviewer identifiers to HMAC tokens and validate review workflow.",
    )
    deidentify.add_argument("--input", required=True, help="Private input JSON. Keep outside the repository.")
    deidentify.add_argument("--output", required=True, help="De-identified intake JSON destination.")
    deidentify.add_argument("--record-secret-env", default=DEFAULT_RECORD_SECRET_ENV)
    deidentify.add_argument("--reviewer-secret-env", default=DEFAULT_REVIEWER_SECRET_ENV)
    deidentify.set_defaults(func=_cmd_deidentify)

    validate = sub.add_parser("validate-safe", help="Validate a de-identified intake dataset.")
    validate.add_argument("--input", required=True)
    validate.set_defaults(func=_cmd_validate)

    promote = sub.add_parser(
        "promote-reviewed",
        help="Export only INDEPENDENTLY_REVIEWED records to the v3 evaluator ground-truth contract.",
    )
    promote.add_argument("--input", required=True, help="De-identified intake JSON.")
    promote.add_argument("--output", required=True, help="Evaluator-compatible ground-truth JSON.")
    promote.set_defaults(func=_cmd_promote)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except EnforcementOutcomeIntakeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
