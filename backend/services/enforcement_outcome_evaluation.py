"""Reviewed outcome-ground-truth contract for Enforcement Intelligence v3.

This module does not create, infer, or label enforcement outcomes. It only
validates independently reviewed, de-identified outcome records and scores
predictions against records that satisfy that contract. Empty or unmatched
datasets return NOT_EVALUABLE instead of fabricating quality metrics.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlparse
import json

from .enforcement_models import EnforcementPrediction

GROUND_TRUTH_SCHEMA_VERSION = "1.0.0"
_ALLOWED_SOURCE_TYPES = {
    "OFFICIAL_ADMINISTRATIVE_DECISION",
    "COURT_DECISION",
    "VERIFIED_ADMINISTRATIVE_RECORD",
}
_FORBIDDEN_SOURCE_TYPES = {"SYNTHETIC", "MODEL_GENERATED", "LLM_GENERATED", "PREDICTION_OUTPUT"}
_FORBIDDEN_KEYS = {
    "rawText",
    "text",
    "caseText",
    "narrative",
    "name",
    "passportNumber",
    "alienRegistrationNumber",
    "registrationNumber",
    "phone",
    "phoneNumber",
    "email",
    "address",
    "modelOutput",
    "predictionOutput",
}


class EnforcementOutcomeEvaluationError(ValueError):
    """Raised when outcome ground truth is not independently reviewable."""


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnforcementOutcomeEvaluationError(f"invalid or missing {field}")
    return value.strip()


def _parse_iso_date(value: Any, field: str) -> date:
    raw = _require_string(value, field)
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise EnforcementOutcomeEvaluationError(f"invalid {field}") from exc


def _reject_sensitive_or_prediction_fields(value: Any, *, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _FORBIDDEN_KEYS:
                raise EnforcementOutcomeEvaluationError(f"forbidden field in ground truth: {path}.{key}")
            _reject_sensitive_or_prediction_fields(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive_or_prediction_fields(child, path=f"{path}[{index}]")


def _validate_public_url(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = _require_string(value, "provenance.publicUrl")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc:
        raise EnforcementOutcomeEvaluationError("provenance.publicUrl must be an https URL")
    return raw


def validate_outcome_ground_truth_dataset(data: Any) -> Dict[str, Any]:
    """Validate privacy, provenance and reviewer-independence requirements.

    Ground truth may be empty while the collection workflow is being built.
    Once a record exists, it must be independently reviewed and tied to a
    verifiable official/administrative record. Model-generated or prediction-
    derived labels are explicitly ineligible.
    """

    if not isinstance(data, dict):
        raise EnforcementOutcomeEvaluationError("outcome ground truth must be an object")
    _reject_sensitive_or_prediction_fields(data)
    if data.get("schemaVersion") != GROUND_TRUTH_SCHEMA_VERSION:
        raise EnforcementOutcomeEvaluationError("unsupported outcome ground-truth schema")
    _require_string(data.get("datasetVersion"), "datasetVersion")
    if data.get("jurisdiction") != "KR":
        raise EnforcementOutcomeEvaluationError("unsupported outcome ground-truth jurisdiction")

    records = data.get("records")
    if not isinstance(records, list):
        raise EnforcementOutcomeEvaluationError("outcome ground truth records must be an array")

    seen_ids: set[str] = set()
    for row in records:
        if not isinstance(row, dict):
            raise EnforcementOutcomeEvaluationError("outcome ground-truth record must be an object")
        case_id = _require_string(row.get("caseId"), "record.caseId")
        if case_id in seen_ids:
            raise EnforcementOutcomeEvaluationError(f"duplicate outcome caseId: {case_id}")
        seen_ids.add(case_id)

        if row.get("reviewStatus") != "INDEPENDENTLY_REVIEWED":
            raise EnforcementOutcomeEvaluationError(f"outcome record is not independently reviewed: {case_id}")
        _parse_iso_date(row.get("reviewedAt"), f"{case_id}.reviewedAt")
        _require_string(row.get("reviewerRole"), f"{case_id}.reviewerRole")
        if row.get("independentFromPrediction") is not True:
            raise EnforcementOutcomeEvaluationError(
                f"outcome record must be independent from prediction output: {case_id}"
            )

        provenance = row.get("provenance")
        if not isinstance(provenance, dict):
            raise EnforcementOutcomeEvaluationError(f"missing provenance for outcome record: {case_id}")
        source_type = _require_string(provenance.get("sourceType"), f"{case_id}.provenance.sourceType")
        if source_type in _FORBIDDEN_SOURCE_TYPES or source_type not in _ALLOWED_SOURCE_TYPES:
            raise EnforcementOutcomeEvaluationError(f"ineligible outcome source type for {case_id}: {source_type}")
        _require_string(provenance.get("authority"), f"{case_id}.provenance.authority")
        _require_string(provenance.get("recordId"), f"{case_id}.provenance.recordId")
        _validate_public_url(provenance.get("publicUrl"))

        outcome = row.get("outcome")
        if not isinstance(outcome, dict):
            raise EnforcementOutcomeEvaluationError(f"missing outcome for {case_id}")
        _parse_iso_date(outcome.get("decisionDate"), f"{case_id}.outcome.decisionDate")
        monetary = outcome.get("monetaryOutcomeKrw")
        if monetary is not None and (not isinstance(monetary, int) or isinstance(monetary, bool) or monetary < 0):
            raise EnforcementOutcomeEvaluationError(f"invalid monetaryOutcomeKrw for {case_id}")
        dispositions = outcome.get("dispositionTypes")
        if not isinstance(dispositions, list):
            raise EnforcementOutcomeEvaluationError(f"dispositionTypes must be an array for {case_id}")
        if any(not isinstance(item, str) or not item.strip() for item in dispositions):
            raise EnforcementOutcomeEvaluationError(f"invalid dispositionTypes for {case_id}")
        if len(dispositions) != len(set(dispositions)):
            raise EnforcementOutcomeEvaluationError(f"duplicate dispositionTypes for {case_id}")
        primary = outcome.get("primaryDispositionType")
        if primary is not None:
            primary = _require_string(primary, f"{case_id}.outcome.primaryDispositionType")
            if primary not in dispositions:
                raise EnforcementOutcomeEvaluationError(
                    f"primaryDispositionType must appear in dispositionTypes for {case_id}"
                )
        if monetary is None and not dispositions:
            raise EnforcementOutcomeEvaluationError(f"outcome has no scoreable label for {case_id}")

    return deepcopy(data)


def load_outcome_ground_truth(path: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EnforcementOutcomeEvaluationError(f"unable to load outcome ground truth: {path}") from exc
    return validate_outcome_ground_truth_dataset(raw)


def _as_prediction(value: Any) -> EnforcementPrediction:
    if isinstance(value, EnforcementPrediction):
        return value
    try:
        return EnforcementPrediction.model_validate(value)
    except Exception as exc:
        raise EnforcementOutcomeEvaluationError("invalid prediction supplied for outcome evaluation") from exc


def _safe_rate(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return numerator / denominator


def evaluate_outcome_predictions(
    ground_truth: Dict[str, Any],
    predictions_by_case_id: Mapping[str, Any],
) -> Dict[str, Any]:
    """Score reviewed outcomes without pretending an empty dataset is evidence.

    Metrics are descriptive and component-specific. The function intentionally
    does not emit a production-readiness verdict, probability calibration score,
    or synthetic overall accuracy. Qualitative confidence is reported by bucket
    only for matched cases with at least one scoreable predicted component.
    """

    dataset = validate_outcome_ground_truth_dataset(ground_truth)
    records = dataset["records"]
    if not records:
        return {
            "status": "NOT_EVALUABLE",
            "reason": "NO_REVIEWED_OUTCOME_GROUND_TRUTH",
            "datasetVersion": dataset["datasetVersion"],
            "groundTruthCases": 0,
            "matchedPredictions": 0,
        }

    normalized_predictions = {str(key): _as_prediction(value) for key, value in predictions_by_case_id.items()}
    matched = [(row, normalized_predictions[row["caseId"]]) for row in records if row["caseId"] in normalized_predictions]
    if not matched:
        return {
            "status": "NOT_EVALUABLE",
            "reason": "NO_MATCHED_PREDICTIONS",
            "datasetVersion": dataset["datasetVersion"],
            "groundTruthCases": len(records),
            "matchedPredictions": 0,
        }

    prediction_available = 0
    monetary_truth = 0
    monetary_range_predictions = 0
    monetary_interval_hits = 0
    point_estimate_errors: list[int] = []
    disposition_primary_truth = 0
    disposition_top1_hits = 0
    disposition_topk_hits = 0
    confidence_buckets: Dict[str, Dict[str, int]] = {}
    case_details: list[Dict[str, Any]] = []

    for row, prediction in matched:
        outcome = row["outcome"]
        if prediction.status != "UNAVAILABLE":
            prediction_available += 1

        component_results: list[bool] = []
        detail: Dict[str, Any] = {"caseId": row["caseId"], "predictionStatus": prediction.status}

        actual_money = outcome.get("monetaryOutcomeKrw")
        if actual_money is not None:
            monetary_truth += 1
            monetary = prediction.monetary_prediction
            predicted_range = monetary.predicted_likely_range if monetary else None
            if predicted_range is not None:
                monetary_range_predictions += 1
                hit = predicted_range.minimum_krw <= actual_money <= predicted_range.maximum_krw
                monetary_interval_hits += int(hit)
                component_results.append(hit)
                detail["monetaryIntervalHit"] = hit
                if monetary.point_estimate_krw is not None:
                    error = abs(monetary.point_estimate_krw - actual_money)
                    point_estimate_errors.append(error)
                    detail["pointAbsoluteErrorKrw"] = error
            else:
                detail["monetaryIntervalHit"] = None

        primary_truth = outcome.get("primaryDispositionType")
        if primary_truth is not None:
            disposition_primary_truth += 1
            primary_prediction = prediction.primary_disposition.type if prediction.primary_disposition else None
            top1_hit = primary_prediction == primary_truth
            disposition_top1_hits += int(top1_hit)
            ranked = []
            if prediction.primary_disposition:
                ranked.append(prediction.primary_disposition.type)
            ranked.extend(item.type for item in prediction.alternative_dispositions)
            topk_hit = primary_truth in ranked
            disposition_topk_hits += int(topk_hit)
            component_results.append(top1_hit)
            detail["dispositionTop1Hit"] = top1_hit
            detail["dispositionTopKHit"] = topk_hit

        if component_results:
            level = prediction.confidence.level
            bucket = confidence_buckets.setdefault(level, {"evaluatedCases": 0, "allLabeledComponentsCorrect": 0})
            bucket["evaluatedCases"] += 1
            success = all(component_results)
            bucket["allLabeledComponentsCorrect"] += int(success)
            detail["allLabeledComponentsCorrect"] = success

        case_details.append(detail)

    confidence_report = {
        level: {
            **counts,
            "observedSuccessRate": _safe_rate(counts["allLabeledComponentsCorrect"], counts["evaluatedCases"]),
        }
        for level, counts in sorted(confidence_buckets.items())
    }

    return {
        "status": "EVALUATED",
        "datasetVersion": dataset["datasetVersion"],
        "groundTruthCases": len(records),
        "matchedPredictions": len(matched),
        "predictionCoverage": _safe_rate(len(matched), len(records)),
        "predictionAvailability": _safe_rate(prediction_available, len(matched)),
        "monetary": {
            "groundTruthCases": monetary_truth,
            "rangePredictions": monetary_range_predictions,
            "intervalCoverage": _safe_rate(monetary_interval_hits, monetary_range_predictions),
            "pointEstimateCases": len(point_estimate_errors),
            "pointEstimateMaeKrw": (
                sum(point_estimate_errors) / len(point_estimate_errors) if point_estimate_errors else None
            ),
        },
        "disposition": {
            "primaryGroundTruthCases": disposition_primary_truth,
            "top1Accuracy": _safe_rate(disposition_top1_hits, disposition_primary_truth),
            "topKRecall": _safe_rate(disposition_topk_hits, disposition_primary_truth),
        },
        "qualitativeConfidence": confidence_report,
        "cases": case_details,
        "limitations": [
            "These metrics describe only independently reviewed matched records; they are not a production-readiness verdict.",
            "Qualitative confidence levels are not numeric probabilities and no ECE/Brier-style probability calibration is computed.",
        ],
    }
