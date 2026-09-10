"""Blind prediction freeze protocol for Enforcement Intelligence v3.

The protocol creates a fixed evaluation cohort before independently reviewed
outcomes exist, freezes one prediction for every cohort case, and later joins
that immutable-by-digest snapshot to the privacy-safe reviewed intake corpus.
It is tamper-evident, not an external timestamping/notarization service.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, Mapping, Optional

from .enforcement_models import EnforcementPrediction
from .enforcement_outcome_evaluation import evaluate_outcome_predictions
from .enforcement_outcome_intake import (
    EnforcementOutcomeIntakeError,
    promote_reviewed_ground_truth,
    validate_safe_intake_dataset,
)

BLIND_CASE_SCHEMA_VERSION = "1.0.0"
PREDICTION_FREEZE_SCHEMA_VERSION = "1.0.0"
PREDICTION_FREEZE_PROTOCOL_VERSION = "enforcement-v3-blind-freeze-v1"

_BLIND_DATASET_KEYS = {
    "schemaVersion",
    "datasetVersion",
    "jurisdiction",
    "generatedAt",
    "caseSetId",
    "records",
}
_BLIND_RECORD_KEYS = {"caseId", "caseFacts", "caseFactsDigest"}
_FREEZE_DATASET_KEYS = {
    "schemaVersion",
    "protocolVersion",
    "datasetVersion",
    "jurisdiction",
    "caseSetId",
    "frozenAt",
    "freezeId",
    "predictionContract",
    "records",
}
_FREEZE_RECORD_KEYS = {"caseId", "caseFactsDigest", "predictionDigest", "prediction"}
_CONTRACT_KEYS = {"schemaVersion", "engineVersion", "promptVersion"}
_PRE_OUTCOME_STAGES = {"STAGED", "SOURCE_VERIFIED"}


class EnforcementPredictionFreezeError(ValueError):
    """Raised when a blind evaluation cohort or prediction freeze is invalid."""


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnforcementPredictionFreezeError(f"invalid or missing {field}")
    return value.strip()


def _require_exact_keys(value: Dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise EnforcementPredictionFreezeError(f"unsupported fields in {field}: {sorted(unknown)}")
    missing = allowed - set(value)
    if missing:
        raise EnforcementPredictionFreezeError(f"missing fields in {field}: {sorted(missing)}")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _parse_timestamp(value: Any, field: str) -> datetime:
    raw = _require_string(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EnforcementPredictionFreezeError(f"invalid {field}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EnforcementPredictionFreezeError(f"{field} must include a timezone offset")
    return parsed


def _iso_timestamp(value: Optional[datetime] = None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise EnforcementPredictionFreezeError("timestamp must include a timezone offset")
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _case_facts_digest(case_facts: Any) -> str:
    if not isinstance(case_facts, dict) or not case_facts:
        raise EnforcementPredictionFreezeError("blind evaluation requires non-empty caseFacts")
    return _sha256(case_facts)


def _case_set_identity(dataset_version: str, records: list[Dict[str, Any]]) -> str:
    payload = {
        "datasetVersion": dataset_version,
        "jurisdiction": "KR",
        "records": records,
    }
    return f"cases_{_sha256(payload)[:24]}"


def _freeze_identity(payload_without_id: Dict[str, Any]) -> str:
    return f"freeze_{_sha256(payload_without_id)[:24]}"


def build_blind_case_set(
    safe_intake: Any,
    *,
    generated_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Export the complete active cohort before any reviewed outcome exists.

    Every record must still be in STAGED or SOURCE_VERIFIED state and must not
    contain an outcome. Refusing mixed/post-outcome datasets prevents creating a
    supposedly blind cohort after labels are already visible.
    """

    try:
        safe = validate_safe_intake_dataset(safe_intake)
    except EnforcementOutcomeIntakeError as exc:
        raise EnforcementPredictionFreezeError(str(exc)) from exc

    records: list[Dict[str, Any]] = []
    for row in safe["records"]:
        case_id = _require_string(row.get("caseId"), "caseId")
        stage = row.get("reviewStage")
        if stage not in _PRE_OUTCOME_STAGES:
            raise EnforcementPredictionFreezeError(
                f"blind case export requires a pre-outcome cohort; {case_id} is {stage}"
            )
        if row.get("outcome") not in (None, {}):
            raise EnforcementPredictionFreezeError(
                f"blind case export refuses outcome-bearing record: {case_id}"
            )
        case_facts = deepcopy(row.get("caseFacts"))
        records.append(
            {
                "caseId": case_id,
                "caseFacts": case_facts,
                "caseFactsDigest": _case_facts_digest(case_facts),
            }
        )

    if not records:
        raise EnforcementPredictionFreezeError("blind evaluation cohort must contain at least one case")
    records.sort(key=lambda item: item["caseId"])
    dataset_version = _require_string(safe.get("datasetVersion"), "datasetVersion")
    result = {
        "schemaVersion": BLIND_CASE_SCHEMA_VERSION,
        "datasetVersion": dataset_version,
        "jurisdiction": "KR",
        "generatedAt": _iso_timestamp(generated_at),
        "caseSetId": _case_set_identity(dataset_version, records),
        "records": records,
    }
    return validate_blind_case_set(result)


def validate_blind_case_set(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise EnforcementPredictionFreezeError("blind case set must be an object")
    _require_exact_keys(data, _BLIND_DATASET_KEYS, "blind case set")
    if data.get("schemaVersion") != BLIND_CASE_SCHEMA_VERSION:
        raise EnforcementPredictionFreezeError("unsupported blind case schemaVersion")
    dataset_version = _require_string(data.get("datasetVersion"), "datasetVersion")
    if data.get("jurisdiction") != "KR":
        raise EnforcementPredictionFreezeError("unsupported blind case jurisdiction")
    _parse_timestamp(data.get("generatedAt"), "generatedAt")
    rows = data.get("records")
    if not isinstance(rows, list) or not rows:
        raise EnforcementPredictionFreezeError("blind case records must be a non-empty array")

    seen: set[str] = set()
    previous_case_id: Optional[str] = None
    normalized: list[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise EnforcementPredictionFreezeError("blind case record must be an object")
        _require_exact_keys(row, _BLIND_RECORD_KEYS, "blind case record")
        case_id = _require_string(row.get("caseId"), "record.caseId")
        if not case_id.startswith("case_") or len(case_id) != 29:
            raise EnforcementPredictionFreezeError("blind caseId must be a derived case token")
        if case_id in seen:
            raise EnforcementPredictionFreezeError(f"duplicate blind caseId: {case_id}")
        if previous_case_id is not None and case_id < previous_case_id:
            raise EnforcementPredictionFreezeError("blind case records must be sorted by caseId")
        seen.add(case_id)
        previous_case_id = case_id
        facts = row.get("caseFacts")
        expected_digest = _case_facts_digest(facts)
        digest = _require_string(row.get("caseFactsDigest"), f"{case_id}.caseFactsDigest")
        if digest != expected_digest:
            raise EnforcementPredictionFreezeError(f"caseFactsDigest mismatch for {case_id}")
        normalized.append(deepcopy(row))

    expected_case_set_id = _case_set_identity(dataset_version, normalized)
    if data.get("caseSetId") != expected_case_set_id:
        raise EnforcementPredictionFreezeError("caseSetId does not match blind cohort content")
    return deepcopy(data)


def _as_prediction(value: Any) -> EnforcementPrediction:
    if isinstance(value, EnforcementPrediction):
        return value
    try:
        return EnforcementPrediction.model_validate(value)
    except Exception as exc:
        raise EnforcementPredictionFreezeError("invalid prediction supplied for freeze") from exc


def freeze_predictions(
    blind_case_set: Any,
    predictions_by_case_id: Mapping[str, Any],
    *,
    frozen_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Freeze exactly one prediction for every case in the blind cohort."""

    cases = validate_blind_case_set(blind_case_set)
    if not isinstance(predictions_by_case_id, Mapping):
        raise EnforcementPredictionFreezeError("predictions must be an object keyed by caseId")

    normalized_predictions = {str(key): _as_prediction(value) for key, value in predictions_by_case_id.items()}
    cohort_ids = {row["caseId"] for row in cases["records"]}
    prediction_ids = set(normalized_predictions)
    missing = sorted(cohort_ids - prediction_ids)
    extra = sorted(prediction_ids - cohort_ids)
    if missing or extra:
        raise EnforcementPredictionFreezeError(
            f"prediction cohort mismatch: missing={missing} extra={extra}"
        )

    records: list[Dict[str, Any]] = []
    contract: Optional[Dict[str, str]] = None
    for row in cases["records"]:
        case_id = row["caseId"]
        prediction = normalized_predictions[case_id]
        prediction_json = prediction.public_dict(exclude_none=False)
        prediction_contract = {
            "schemaVersion": prediction.schema_version,
            "engineVersion": prediction.engine_version,
            "promptVersion": prediction.prompt_version,
        }
        if contract is None:
            contract = prediction_contract
        elif prediction_contract != contract:
            raise EnforcementPredictionFreezeError("all frozen predictions must use the same prediction contract")
        records.append(
            {
                "caseId": case_id,
                "caseFactsDigest": row["caseFactsDigest"],
                "predictionDigest": _sha256(prediction_json),
                "prediction": prediction_json,
            }
        )

    assert contract is not None
    payload_without_id: Dict[str, Any] = {
        "schemaVersion": PREDICTION_FREEZE_SCHEMA_VERSION,
        "protocolVersion": PREDICTION_FREEZE_PROTOCOL_VERSION,
        "datasetVersion": cases["datasetVersion"],
        "jurisdiction": "KR",
        "caseSetId": cases["caseSetId"],
        "frozenAt": _iso_timestamp(frozen_at),
        "predictionContract": contract,
        "records": records,
    }
    frozen = {
        **payload_without_id,
        "freezeId": _freeze_identity(payload_without_id),
    }
    return validate_prediction_freeze(frozen)


def validate_prediction_freeze(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise EnforcementPredictionFreezeError("prediction freeze must be an object")
    _require_exact_keys(data, _FREEZE_DATASET_KEYS, "prediction freeze")
    if data.get("schemaVersion") != PREDICTION_FREEZE_SCHEMA_VERSION:
        raise EnforcementPredictionFreezeError("unsupported prediction freeze schemaVersion")
    if data.get("protocolVersion") != PREDICTION_FREEZE_PROTOCOL_VERSION:
        raise EnforcementPredictionFreezeError("unsupported prediction freeze protocolVersion")
    _require_string(data.get("datasetVersion"), "datasetVersion")
    if data.get("jurisdiction") != "KR":
        raise EnforcementPredictionFreezeError("unsupported prediction freeze jurisdiction")
    case_set_id = _require_string(data.get("caseSetId"), "caseSetId")
    if not case_set_id.startswith("cases_") or len(case_set_id) != 30:
        raise EnforcementPredictionFreezeError("invalid caseSetId")
    _parse_timestamp(data.get("frozenAt"), "frozenAt")

    contract = data.get("predictionContract")
    if not isinstance(contract, dict):
        raise EnforcementPredictionFreezeError("predictionContract must be an object")
    _require_exact_keys(contract, _CONTRACT_KEYS, "predictionContract")
    for key in _CONTRACT_KEYS:
        _require_string(contract.get(key), f"predictionContract.{key}")

    rows = data.get("records")
    if not isinstance(rows, list) or not rows:
        raise EnforcementPredictionFreezeError("prediction freeze records must be a non-empty array")
    seen: set[str] = set()
    previous_case_id: Optional[str] = None
    for row in rows:
        if not isinstance(row, dict):
            raise EnforcementPredictionFreezeError("prediction freeze record must be an object")
        _require_exact_keys(row, _FREEZE_RECORD_KEYS, "prediction freeze record")
        case_id = _require_string(row.get("caseId"), "record.caseId")
        if not case_id.startswith("case_") or len(case_id) != 29:
            raise EnforcementPredictionFreezeError("frozen caseId must be a derived case token")
        if case_id in seen:
            raise EnforcementPredictionFreezeError(f"duplicate frozen caseId: {case_id}")
        if previous_case_id is not None and case_id < previous_case_id:
            raise EnforcementPredictionFreezeError("prediction freeze records must be sorted by caseId")
        seen.add(case_id)
        previous_case_id = case_id
        facts_digest = _require_string(row.get("caseFactsDigest"), f"{case_id}.caseFactsDigest")
        if len(facts_digest) != 64 or any(ch not in "0123456789abcdef" for ch in facts_digest):
            raise EnforcementPredictionFreezeError(f"invalid caseFactsDigest for {case_id}")
        prediction = _as_prediction(row.get("prediction"))
        prediction_json = prediction.public_dict(exclude_none=False)
        digest = _require_string(row.get("predictionDigest"), f"{case_id}.predictionDigest")
        if digest != _sha256(prediction_json):
            raise EnforcementPredictionFreezeError(f"predictionDigest mismatch for {case_id}")
        actual_contract = {
            "schemaVersion": prediction.schema_version,
            "engineVersion": prediction.engine_version,
            "promptVersion": prediction.prompt_version,
        }
        if actual_contract != contract:
            raise EnforcementPredictionFreezeError(f"prediction contract mismatch for {case_id}")

    payload_without_id = {key: deepcopy(value) for key, value in data.items() if key != "freezeId"}
    expected_id = _freeze_identity(payload_without_id)
    if data.get("freezeId") != expected_id:
        raise EnforcementPredictionFreezeError("freezeId does not match frozen content")
    return deepcopy(data)


def evaluate_frozen_outcomes(safe_intake: Any, prediction_freeze: Any) -> Dict[str, Any]:
    """Join reviewed outcomes to a previously frozen, unchanged cohort.

    The cohort must remain identical, case facts must remain unchanged, and the
    freeze timestamp must strictly precede the independent-review event for each
    scored outcome. The existing outcome evaluator then computes the metrics.
    """

    try:
        safe = validate_safe_intake_dataset(safe_intake)
    except EnforcementOutcomeIntakeError as exc:
        raise EnforcementPredictionFreezeError(str(exc)) from exc
    frozen = validate_prediction_freeze(prediction_freeze)

    if safe["datasetVersion"] != frozen["datasetVersion"]:
        raise EnforcementPredictionFreezeError("datasetVersion changed after prediction freeze")

    frozen_rows = {row["caseId"]: row for row in frozen["records"]}
    current_ids = {row["caseId"] for row in safe["records"]}
    frozen_ids = set(frozen_rows)
    if current_ids != frozen_ids:
        missing = sorted(frozen_ids - current_ids)
        extra = sorted(current_ids - frozen_ids)
        raise EnforcementPredictionFreezeError(
            f"evaluation cohort changed after freeze: missing={missing} extra={extra}"
        )

    frozen_at = _parse_timestamp(frozen["frozenAt"], "frozenAt")
    reviewed_count = 0
    rejected_count = 0
    pending_count = 0
    predictions: Dict[str, Any] = {}
    for row in safe["records"]:
        case_id = row["caseId"]
        frozen_row = frozen_rows[case_id]
        current_facts_digest = _case_facts_digest(row.get("caseFacts"))
        if current_facts_digest != frozen_row["caseFactsDigest"]:
            raise EnforcementPredictionFreezeError(f"caseFacts changed after freeze: {case_id}")

        stage = row["reviewStage"]
        if stage == "INDEPENDENTLY_REVIEWED":
            reviewed_count += 1
            final_event = row["reviewHistory"][-1]
            reviewed_at = _parse_timestamp(final_event.get("at"), f"{case_id}.reviewedAt")
            if frozen_at >= reviewed_at:
                raise EnforcementPredictionFreezeError(
                    f"prediction freeze must precede independent review: {case_id}"
                )
        elif stage == "REJECTED":
            rejected_count += 1
            if row.get("outcome") not in (None, {}):
                raise EnforcementPredictionFreezeError(f"rejected case contains an outcome label: {case_id}")
        else:
            pending_count += 1
            if row.get("outcome") not in (None, {}):
                raise EnforcementPredictionFreezeError(f"pre-review case contains an outcome label: {case_id}")
        predictions[case_id] = frozen_row["prediction"]

    try:
        ground_truth = promote_reviewed_ground_truth(safe)
    except EnforcementOutcomeIntakeError as exc:
        raise EnforcementPredictionFreezeError(str(exc)) from exc
    evaluation = evaluate_outcome_predictions(ground_truth, predictions)
    return {
        "protocolStatus": "VALID",
        "protocolVersion": PREDICTION_FREEZE_PROTOCOL_VERSION,
        "freezeId": frozen["freezeId"],
        "caseSetId": frozen["caseSetId"],
        "datasetVersion": frozen["datasetVersion"],
        "frozenAt": frozen["frozenAt"],
        "cohortCases": len(frozen_rows),
        "reviewedCases": reviewed_count,
        "rejectedCases": rejected_count,
        "pendingCases": pending_count,
        "evaluation": evaluation,
    }
