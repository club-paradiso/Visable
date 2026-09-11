"""Preregistered reporting contract for Enforcement Intelligence v3.

The plan fixes metric selection and minimum-sample disclosure rules after a
blind case set exists but no later than the prediction freeze. It deliberately
does not define performance pass/fail thresholds or a production-readiness
verdict.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, Optional

from .enforcement_prediction_freeze import (
    EnforcementPredictionFreezeError,
    evaluate_frozen_outcomes,
    validate_blind_case_set,
    validate_prediction_freeze,
)

EVALUATION_PLAN_SCHEMA_VERSION = "1.0.0"
EVALUATION_PLAN_PROTOCOL_VERSION = "enforcement-v3-evaluation-plan-v1"

_ALLOWED_METRICS = {
    "PREDICTION_AVAILABILITY",
    "MONETARY_INTERVAL_COVERAGE",
    "MONETARY_POINT_MAE_KRW",
    "DISPOSITION_TOP1_ACCURACY",
    "DISPOSITION_TOPK_RECALL",
    "QUALITATIVE_CONFIDENCE_OBSERVED_SUCCESS",
}
_PLAN_KEYS = {
    "schemaVersion",
    "protocolVersion",
    "datasetVersion",
    "jurisdiction",
    "caseSetId",
    "caseSetGeneratedAt",
    "createdAt",
    "planId",
    "metrics",
    "reportingPolicy",
}
_METRIC_KEYS = {"metric", "minimumEligibleCases"}
_REPORTING_KEYS = {
    "suppressBelowMinimum",
    "reportCohortAttrition",
    "allowPerformanceVerdict",
    "allowProbabilityCalibrationClaim",
}
_REQUIRED_REPORTING_POLICY = {
    "suppressBelowMinimum": True,
    "reportCohortAttrition": True,
    "allowPerformanceVerdict": False,
    "allowProbabilityCalibrationClaim": False,
}


class EnforcementEvaluationPlanError(ValueError):
    """Raised when a preregistered evaluation plan is invalid."""


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnforcementEvaluationPlanError(f"invalid or missing {field}")
    return value.strip()


def _require_exact_keys(value: Dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = set(value) - allowed
    missing = allowed - set(value)
    if unknown:
        raise EnforcementEvaluationPlanError(f"unsupported fields in {field}: {sorted(unknown)}")
    if missing:
        raise EnforcementEvaluationPlanError(f"missing fields in {field}: {sorted(missing)}")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _parse_timestamp(value: Any, field: str) -> datetime:
    raw = _require_string(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EnforcementEvaluationPlanError(f"invalid {field}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EnforcementEvaluationPlanError(f"{field} must include a timezone offset")
    return parsed


def _iso_timestamp(value: Optional[datetime] = None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise EnforcementEvaluationPlanError("createdAt must include a timezone offset")
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_case_set_id(value: Any) -> str:
    raw = _require_string(value, "caseSetId")
    if not raw.startswith("cases_") or len(raw) != 30:
        raise EnforcementEvaluationPlanError("invalid caseSetId")
    suffix = raw[6:]
    if any(ch not in "0123456789abcdef" for ch in suffix):
        raise EnforcementEvaluationPlanError("invalid caseSetId")
    return raw


def _plan_identity(payload_without_id: Dict[str, Any]) -> str:
    return f"plan_{_sha256(payload_without_id)[:24]}"


def _canonical_metrics(metrics: Any) -> list[Dict[str, Any]]:
    if not isinstance(metrics, list):
        raise EnforcementEvaluationPlanError("metrics must be a non-empty array")
    copied = deepcopy(metrics)
    if any(not isinstance(item, dict) for item in copied):
        raise EnforcementEvaluationPlanError("metric entry must be an object")
    return sorted(copied, key=lambda item: str(item.get("metric", "")))


def build_evaluation_plan(
    blind_case_set: Any,
    *,
    metrics: list[Dict[str, Any]],
    created_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Create a content-addressed plan bound to one already-fixed blind cohort.

    Callers must explicitly choose each metric's minimum eligible-case count.
    The library therefore locks policy choices without inventing a statistical
    threshold on the caller's behalf.
    """

    try:
        cases = validate_blind_case_set(blind_case_set)
    except EnforcementPredictionFreezeError as exc:
        raise EnforcementEvaluationPlanError(str(exc)) from exc

    generated_at = _parse_timestamp(cases["generatedAt"], "caseSet.generatedAt")
    created_at_raw = _iso_timestamp(created_at)
    plan_created = _parse_timestamp(created_at_raw, "createdAt")
    if plan_created < generated_at:
        raise EnforcementEvaluationPlanError("evaluation plan cannot predate blind case-set generation")

    payload_without_id: Dict[str, Any] = {
        "schemaVersion": EVALUATION_PLAN_SCHEMA_VERSION,
        "protocolVersion": EVALUATION_PLAN_PROTOCOL_VERSION,
        "datasetVersion": cases["datasetVersion"],
        "jurisdiction": "KR",
        "caseSetId": cases["caseSetId"],
        "caseSetGeneratedAt": cases["generatedAt"],
        "createdAt": created_at_raw,
        "metrics": _canonical_metrics(metrics),
        "reportingPolicy": deepcopy(_REQUIRED_REPORTING_POLICY),
    }
    plan = {**payload_without_id, "planId": _plan_identity(payload_without_id)}
    return validate_evaluation_plan(plan)


def validate_evaluation_plan(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise EnforcementEvaluationPlanError("evaluation plan must be an object")
    _require_exact_keys(data, _PLAN_KEYS, "evaluation plan")
    if data.get("schemaVersion") != EVALUATION_PLAN_SCHEMA_VERSION:
        raise EnforcementEvaluationPlanError("unsupported evaluation plan schemaVersion")
    if data.get("protocolVersion") != EVALUATION_PLAN_PROTOCOL_VERSION:
        raise EnforcementEvaluationPlanError("unsupported evaluation plan protocolVersion")
    _require_string(data.get("datasetVersion"), "datasetVersion")
    if data.get("jurisdiction") != "KR":
        raise EnforcementEvaluationPlanError("unsupported evaluation plan jurisdiction")
    _require_case_set_id(data.get("caseSetId"))
    generated_at = _parse_timestamp(data.get("caseSetGeneratedAt"), "caseSetGeneratedAt")
    created_at = _parse_timestamp(data.get("createdAt"), "createdAt")
    if created_at < generated_at:
        raise EnforcementEvaluationPlanError("evaluation plan cannot predate blind case-set generation")

    metrics = data.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise EnforcementEvaluationPlanError("metrics must be a non-empty array")
    seen: set[str] = set()
    previous_metric: Optional[str] = None
    for index, entry in enumerate(metrics):
        if not isinstance(entry, dict):
            raise EnforcementEvaluationPlanError("metric entry must be an object")
        _require_exact_keys(entry, _METRIC_KEYS, f"metrics[{index}]")
        metric = _require_string(entry.get("metric"), f"metrics[{index}].metric")
        if metric not in _ALLOWED_METRICS:
            raise EnforcementEvaluationPlanError(f"unsupported metric: {metric}")
        if metric in seen:
            raise EnforcementEvaluationPlanError(f"duplicate metric: {metric}")
        if previous_metric is not None and metric < previous_metric:
            raise EnforcementEvaluationPlanError("metrics must be sorted by metric name")
        seen.add(metric)
        previous_metric = metric
        minimum = entry.get("minimumEligibleCases")
        if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
            raise EnforcementEvaluationPlanError(
                f"metrics[{index}].minimumEligibleCases must be a positive integer"
            )

    policy = data.get("reportingPolicy")
    if not isinstance(policy, dict):
        raise EnforcementEvaluationPlanError("reportingPolicy must be an object")
    _require_exact_keys(policy, _REPORTING_KEYS, "reportingPolicy")
    if policy != _REQUIRED_REPORTING_POLICY:
        raise EnforcementEvaluationPlanError("reportingPolicy weakens the fixed safety contract")

    payload_without_id = {key: deepcopy(value) for key, value in data.items() if key != "planId"}
    expected = _plan_identity(payload_without_id)
    plan_id = _require_string(data.get("planId"), "planId")
    if plan_id != expected:
        raise EnforcementEvaluationPlanError("planId does not match evaluation plan content")
    return deepcopy(data)


def _gate(value: Any, *, eligible_cases: int, minimum_cases: int) -> Dict[str, Any]:
    if eligible_cases < minimum_cases:
        return {
            "status": "SUPPRESSED_MINIMUM_SAMPLE",
            "eligibleCases": eligible_cases,
            "minimumEligibleCases": minimum_cases,
            "value": None,
        }
    return {
        "status": "REPORTED",
        "eligibleCases": eligible_cases,
        "minimumEligibleCases": minimum_cases,
        "value": value,
    }


def _apply_plan_to_blind_report(plan: Dict[str, Any], blind_report: Dict[str, Any]) -> Dict[str, Any]:
    evaluation = blind_report.get("evaluation")
    if not isinstance(evaluation, dict):
        raise EnforcementEvaluationPlanError("blind report is missing evaluation")

    counts = {
        "cohortCases": blind_report.get("cohortCases"),
        "reviewedCases": blind_report.get("reviewedCases"),
        "rejectedCases": blind_report.get("rejectedCases"),
        "pendingCases": blind_report.get("pendingCases"),
    }
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts.values()):
        raise EnforcementEvaluationPlanError("invalid cohort counts in blind report")
    if counts["reviewedCases"] + counts["rejectedCases"] + counts["pendingCases"] != counts["cohortCases"]:
        raise EnforcementEvaluationPlanError("blind report cohort counts do not reconcile")

    if evaluation.get("status") != "EVALUATED":
        return {
            "schemaVersion": EVALUATION_PLAN_SCHEMA_VERSION,
            "status": "NOT_EVALUABLE",
            "reason": evaluation.get("reason") or "BLIND_EVALUATION_NOT_EVALUABLE",
            "planId": plan["planId"],
            "freezeId": blind_report.get("freezeId"),
            "caseSetId": plan["caseSetId"],
            "datasetVersion": plan["datasetVersion"],
            "cohort": counts,
            "metrics": {},
            "performanceVerdict": None,
            "probabilityCalibrationClaim": None,
        }

    monetary = evaluation.get("monetary") if isinstance(evaluation.get("monetary"), dict) else {}
    disposition = evaluation.get("disposition") if isinstance(evaluation.get("disposition"), dict) else {}
    confidence = evaluation.get("qualitativeConfidence") if isinstance(evaluation.get("qualitativeConfidence"), dict) else {}

    candidates: Dict[str, tuple[Any, Any]] = {
        "PREDICTION_AVAILABILITY": (
            evaluation.get("predictionAvailability"),
            evaluation.get("matchedPredictions", 0),
        ),
        "MONETARY_INTERVAL_COVERAGE": (
            monetary.get("intervalCoverage"),
            monetary.get("rangePredictions", 0),
        ),
        "MONETARY_POINT_MAE_KRW": (
            monetary.get("pointEstimateMaeKrw"),
            monetary.get("pointEstimateCases", 0),
        ),
        "DISPOSITION_TOP1_ACCURACY": (
            disposition.get("top1Accuracy"),
            disposition.get("primaryGroundTruthCases", 0),
        ),
        "DISPOSITION_TOPK_RECALL": (
            disposition.get("topKRecall"),
            disposition.get("primaryGroundTruthCases", 0),
        ),
    }

    metrics_out: Dict[str, Any] = {}
    for entry in plan["metrics"]:
        metric = entry["metric"]
        minimum = entry["minimumEligibleCases"]
        if metric == "QUALITATIVE_CONFIDENCE_OBSERVED_SUCCESS":
            buckets: Dict[str, Any] = {}
            for level, values in sorted(confidence.items()):
                if not isinstance(values, dict):
                    continue
                eligible = values.get("evaluatedCases", 0)
                if not isinstance(eligible, int) or isinstance(eligible, bool) or eligible < 0:
                    raise EnforcementEvaluationPlanError("invalid qualitative confidence bucket count")
                buckets[level] = _gate(
                    values.get("observedSuccessRate"),
                    eligible_cases=eligible,
                    minimum_cases=minimum,
                )
            metrics_out[metric] = {"status": "BUCKETED", "buckets": buckets}
            continue

        value, eligible = candidates[metric]
        if not isinstance(eligible, int) or isinstance(eligible, bool) or eligible < 0:
            raise EnforcementEvaluationPlanError(f"invalid eligible case count for {metric}")
        metrics_out[metric] = _gate(value, eligible_cases=eligible, minimum_cases=minimum)

    return {
        "schemaVersion": EVALUATION_PLAN_SCHEMA_VERSION,
        "status": "PREREGISTERED_REPORT",
        "planId": plan["planId"],
        "freezeId": blind_report.get("freezeId"),
        "caseSetId": plan["caseSetId"],
        "datasetVersion": plan["datasetVersion"],
        "cohort": counts,
        "metrics": metrics_out,
        "performanceVerdict": None,
        "probabilityCalibrationClaim": None,
        "limitations": [
            "Metrics below their preregistered minimum sample are suppressed rather than interpreted.",
            "This report does not establish production readiness or legal validity.",
            "Qualitative confidence labels are not numeric probabilities.",
        ],
    }


def evaluate_with_plan(
    safe_intake: Any,
    prediction_freeze: Any,
    evaluation_plan: Any,
) -> Dict[str, Any]:
    """Validate plan chronology, rerun blind evaluation, then apply disclosure gates."""

    plan = validate_evaluation_plan(evaluation_plan)
    try:
        frozen = validate_prediction_freeze(prediction_freeze)
        blind_report = evaluate_frozen_outcomes(safe_intake, frozen)
    except EnforcementPredictionFreezeError as exc:
        raise EnforcementEvaluationPlanError(str(exc)) from exc

    if plan["datasetVersion"] != frozen["datasetVersion"]:
        raise EnforcementEvaluationPlanError("evaluation plan datasetVersion does not match prediction freeze")
    if plan["caseSetId"] != frozen["caseSetId"]:
        raise EnforcementEvaluationPlanError("evaluation plan caseSetId does not match prediction freeze")
    if plan["caseSetGeneratedAt"] != frozen["caseSetGeneratedAt"]:
        raise EnforcementEvaluationPlanError("evaluation plan case-set timestamp does not match prediction freeze")

    plan_created = _parse_timestamp(plan["createdAt"], "createdAt")
    frozen_at = _parse_timestamp(frozen["frozenAt"], "predictionFreeze.frozenAt")
    if plan_created > frozen_at:
        raise EnforcementEvaluationPlanError("evaluation plan must be created no later than prediction freeze")

    return _apply_plan_to_blind_report(plan, blind_report)
