from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_evaluation_plan import (  # noqa: E402
    EnforcementEvaluationPlanError,
    build_evaluation_plan,
    evaluate_with_plan,
    validate_evaluation_plan,
)
from services.enforcement_models import EnforcementPrediction, PredictionConfidence  # noqa: E402
from services.enforcement_outcome_intake import normalize_private_intake_dataset  # noqa: E402
from services.enforcement_prediction_freeze import build_blind_case_set, freeze_predictions  # noqa: E402

RECORD_SECRET = "evaluation-plan-record-secret-1234567890"
REVIEWER_SECRET = "evaluation-plan-reviewer-secret-1234567890"


def _facts(status: str = "D-2") -> dict:
    return {
        "statusOfStay": status,
        "violationCode": "STATUS_OUTSIDE_ACTIVITY_ART20",
        "durationDays": 18,
        "priorViolations": 0,
        "voluntaryDisclosure": True,
        "authorizationObtained": False,
        "assessmentDate": "2026-08-19",
    }


def _record(source_id: str, *, reviewed: bool = False, status: str = "D-2") -> dict:
    history = [
        {
            "stage": "STAGED",
            "at": "2026-08-20T08:00:00+09:00",
            "reviewerReference": f"{source_id}-intake",
        },
        {
            "stage": "SOURCE_VERIFIED",
            "at": "2026-08-20T08:10:00+09:00",
            "reviewerReference": f"{source_id}-source-reviewer",
        },
    ]
    if reviewed:
        history.append(
            {
                "stage": "INDEPENDENTLY_REVIEWED",
                "at": "2026-08-20T10:00:00+09:00",
                "reviewerReference": f"{source_id}-outcome-reviewer",
            }
        )
    return {
        "sourceRecordId": source_id,
        "reviewStage": "INDEPENDENTLY_REVIEWED" if reviewed else "SOURCE_VERIFIED",
        "caseFacts": _facts(status),
        "provenance": {
            "sourceType": "VERIFIED_ADMINISTRATIVE_RECORD",
            "authority": "Test administrative authority",
            "recordId": f"official-{source_id}",
            "publicUrl": None,
        },
        "outcome": (
            {
                "decisionDate": "2026-08-20",
                "monetaryOutcomeKrw": 2000000,
                "dispositionTypes": ["ADMINISTRATIVE_FINE"],
                "primaryDispositionType": "ADMINISTRATIVE_FINE",
            }
            if reviewed
            else None
        ),
        "independentFromPrediction": True if reviewed else None,
        "reviewerRole": "AUTHORIZED_ADMINISTRATIVE_REVIEWER" if reviewed else None,
        "reviewHistory": history,
    }


def _dataset(*records: dict) -> dict:
    return {
        "schemaVersion": "1.0.0",
        "datasetVersion": "evaluation-plan-test-v1",
        "jurisdiction": "KR",
        "records": list(records),
    }


def _safe(*records: dict) -> dict:
    return normalize_private_intake_dataset(
        _dataset(*records),
        record_secret=RECORD_SECRET,
        reviewer_secret=REVIEWER_SECRET,
    )


def _prediction() -> EnforcementPrediction:
    return EnforcementPrediction(
        status="UNAVAILABLE",
        confidence=PredictionConfidence(level="INSUFFICIENT", reasons=["test fixture"]),
        limitations=["test fixture"],
    )


def _setup() -> tuple[dict, dict, dict]:
    pre = _safe(_record("case-a"), _record("case-b", status="F-2"))
    cases = build_blind_case_set(
        pre,
        generated_at=datetime.fromisoformat("2026-08-19T23:30:00+00:00"),
    )
    predictions = {row["caseId"]: _prediction() for row in cases["records"]}
    frozen = freeze_predictions(
        cases,
        predictions,
        frozen_at=datetime.fromisoformat("2026-08-20T00:30:00+00:00"),
    )
    reviewed = _safe(_record("case-a", reviewed=True), _record("case-b", status="F-2"))
    return cases, frozen, reviewed


def _metrics(minimum: int = 1) -> list[dict]:
    return [
        {"metric": "PREDICTION_AVAILABILITY", "minimumEligibleCases": minimum},
    ]


def test_plan_is_bound_to_case_set_and_content_addressed():
    cases, _, _ = _setup()
    plan = build_evaluation_plan(
        cases,
        metrics=_metrics(),
        created_at=datetime.fromisoformat("2026-08-20T00:00:00+00:00"),
    )
    validated = validate_evaluation_plan(plan)
    assert validated["caseSetId"] == cases["caseSetId"]
    assert validated["caseSetGeneratedAt"] == cases["generatedAt"]
    assert validated["planId"].startswith("plan_")
    assert validated["reportingPolicy"]["allowPerformanceVerdict"] is False


def test_plan_rejects_backdating_duplicate_metrics_and_nonpositive_minimum():
    cases, _, _ = _setup()
    with pytest.raises(EnforcementEvaluationPlanError, match="cannot predate"):
        build_evaluation_plan(
            cases,
            metrics=_metrics(),
            created_at=datetime.fromisoformat("2026-08-19T23:29:59+00:00"),
        )

    duplicate = [
        {"metric": "PREDICTION_AVAILABILITY", "minimumEligibleCases": 1},
        {"metric": "PREDICTION_AVAILABILITY", "minimumEligibleCases": 2},
    ]
    with pytest.raises(EnforcementEvaluationPlanError, match="duplicate metric"):
        build_evaluation_plan(
            cases,
            metrics=duplicate,
            created_at=datetime.fromisoformat("2026-08-20T00:00:00+00:00"),
        )

    with pytest.raises(EnforcementEvaluationPlanError, match="positive integer"):
        build_evaluation_plan(
            cases,
            metrics=[{"metric": "PREDICTION_AVAILABILITY", "minimumEligibleCases": 0}],
            created_at=datetime.fromisoformat("2026-08-20T00:00:00+00:00"),
        )


def test_plan_id_and_reporting_policy_detect_posthoc_tampering():
    cases, _, _ = _setup()
    plan = build_evaluation_plan(
        cases,
        metrics=_metrics(),
        created_at=datetime.fromisoformat("2026-08-20T00:00:00+00:00"),
    )
    tampered = deepcopy(plan)
    tampered["metrics"][0]["minimumEligibleCases"] = 2
    with pytest.raises(EnforcementEvaluationPlanError, match="planId"):
        validate_evaluation_plan(tampered)

    weakened = deepcopy(plan)
    weakened["reportingPolicy"]["allowPerformanceVerdict"] = True
    with pytest.raises(EnforcementEvaluationPlanError, match="weakens"):
        validate_evaluation_plan(weakened)


def test_plan_must_exist_no_later_than_prediction_freeze():
    cases, frozen, reviewed = _setup()
    late_plan = build_evaluation_plan(
        cases,
        metrics=_metrics(),
        created_at=datetime.fromisoformat("2026-08-20T00:31:00+00:00"),
    )
    with pytest.raises(EnforcementEvaluationPlanError, match="no later than prediction freeze"):
        evaluate_with_plan(reviewed, frozen, late_plan)


def test_preregistered_minimum_suppresses_small_sample_without_hiding_attrition():
    cases, frozen, reviewed = _setup()
    plan = build_evaluation_plan(
        cases,
        metrics=_metrics(minimum=2),
        created_at=datetime.fromisoformat("2026-08-20T00:00:00+00:00"),
    )
    report = evaluate_with_plan(reviewed, frozen, plan)
    metric = report["metrics"]["PREDICTION_AVAILABILITY"]
    assert report["status"] == "PREREGISTERED_REPORT"
    assert metric["status"] == "SUPPRESSED_MINIMUM_SAMPLE"
    assert metric["eligibleCases"] == 1
    assert metric["value"] is None
    assert report["cohort"] == {
        "cohortCases": 2,
        "reviewedCases": 1,
        "rejectedCases": 0,
        "pendingCases": 1,
    }
    assert report["performanceVerdict"] is None
    assert report["probabilityCalibrationClaim"] is None


def test_preregistered_metric_reports_when_minimum_is_met():
    cases, frozen, reviewed = _setup()
    plan = build_evaluation_plan(
        cases,
        metrics=_metrics(minimum=1),
        created_at=datetime.fromisoformat("2026-08-20T00:00:00+00:00"),
    )
    report = evaluate_with_plan(reviewed, frozen, plan)
    metric = report["metrics"]["PREDICTION_AVAILABILITY"]
    assert metric["status"] == "REPORTED"
    assert metric["eligibleCases"] == 1
    assert metric["value"] == 0.0


def test_checked_in_evaluation_plan_schema_is_closed_and_forbids_verdicts():
    schema = json.loads(
        (REPO_ROOT / "backend/data/enforcement/evaluation_plan.schema.json").read_text(encoding="utf-8")
    )
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["metric"]["additionalProperties"] is False
    assert schema["$defs"]["reportingPolicy"]["properties"]["allowPerformanceVerdict"]["const"] is False
    assert schema["$defs"]["reportingPolicy"]["properties"]["allowProbabilityCalibrationClaim"]["const"] is False


def test_cli_validates_plan_and_generates_preregistered_report(tmp_path: Path):
    cases, frozen, reviewed = _setup()
    plan = build_evaluation_plan(
        cases,
        metrics=_metrics(),
        created_at=datetime.fromisoformat("2026-08-20T00:00:00+00:00"),
    )
    plan_path = tmp_path / "plan.json"
    freeze_path = tmp_path / "freeze.json"
    intake_path = tmp_path / "intake.json"
    output_path = tmp_path / "report.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    freeze_path.write_text(json.dumps(frozen), encoding="utf-8")
    intake_path.write_text(json.dumps(reviewed), encoding="utf-8")

    script = REPO_ROOT / "scripts/evaluate_enforcement_v3_preregistered.py"
    run = subprocess.run(
        [
            sys.executable,
            str(script),
            "evaluate",
            "--plan",
            str(plan_path),
            "--freeze",
            str(freeze_path),
            "--intake",
            str(intake_path),
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    assert "preregistered_evaluation=PREREGISTERED_REPORT" in run.stdout
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["performanceVerdict"] is None
