"""Privacy-safe intake pipeline for Enforcement Intelligence v3 outcome review.

The intake layer is deliberately separate from prediction and from the evaluator.
It accepts private offline records, derives non-reversible HMAC identifiers, rejects
raw narrative/PII and prediction-derived labels, validates review-state transitions,
and promotes only independently reviewed records into the evaluator contract.

No real outcome data belongs in this repository. The checked-in template is empty.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse

from .enforcement_outcome_evaluation import (
    GROUND_TRUTH_SCHEMA_VERSION,
    EnforcementOutcomeEvaluationError,
    validate_outcome_ground_truth_dataset,
)

INTAKE_SCHEMA_VERSION = "1.0.0"
_ALLOWED_STAGES = (
    "STAGED",
    "SOURCE_VERIFIED",
    "INDEPENDENTLY_REVIEWED",
    "REJECTED",
)
_ALLOWED_TRANSITIONS = {
    None: {"STAGED", "SOURCE_VERIFIED", "INDEPENDENTLY_REVIEWED", "REJECTED"},
    "STAGED": {"SOURCE_VERIFIED", "REJECTED"},
    "SOURCE_VERIFIED": {"INDEPENDENTLY_REVIEWED", "REJECTED"},
    "INDEPENDENTLY_REVIEWED": set(),
    "REJECTED": set(),
}
_ALLOWED_SOURCE_TYPES = {
    "OFFICIAL_ADMINISTRATIVE_DECISION",
    "COURT_DECISION",
    "VERIFIED_ADMINISTRATIVE_RECORD",
}
_FORBIDDEN_SOURCE_TYPES = {
    "SYNTHETIC",
    "MODEL_GENERATED",
    "LLM_GENERATED",
    "PREDICTION_OUTPUT",
}
_ALLOWED_REJECTION_CODES = {
    "SOURCE_INELIGIBLE",
    "PII_PRESENT",
    "DUPLICATE",
    "INSUFFICIENT_EVIDENCE",
    "PREDICTION_DERIVED",
    "REVIEW_CONFLICT",
}
_FORBIDDEN_KEYS = {
    "rawText",
    "text",
    "caseText",
    "narrative",
    "freeText",
    "notes",
    "name",
    "fullName",
    "passportNumber",
    "alienRegistrationNumber",
    "registrationNumber",
    "phone",
    "phoneNumber",
    "email",
    "address",
    "dateOfBirth",
    "birthDate",
    "modelOutput",
    "predictionOutput",
}
_SAFE_CASE_FACT_FIELDS = {
    "statusOfStay",
    "violationCode",
    "durationDays",
    "priorViolations",
    "voluntaryDisclosure",
    "authorizationObtained",
    "assessmentDate",
}


class EnforcementOutcomeIntakeError(ValueError):
    """Raised when a private intake record cannot be safely normalized."""


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnforcementOutcomeIntakeError(f"invalid or missing {field}")
    return value.strip()


def _parse_iso_date(value: Any, field: str) -> str:
    raw = _require_string(value, field)
    try:
        date.fromisoformat(raw)
    except ValueError as exc:
        raise EnforcementOutcomeIntakeError(f"invalid {field}") from exc
    return raw


def _parse_iso_datetime(value: Any, field: str) -> str:
    raw = _require_string(value, field)
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EnforcementOutcomeIntakeError(f"invalid {field}") from exc
    return raw


def _reject_forbidden_fields(value: Any, *, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _FORBIDDEN_KEYS:
                raise EnforcementOutcomeIntakeError(f"forbidden field: {path}.{key}")
            _reject_forbidden_fields(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_fields(child, path=f"{path}[{index}]")


def _secret_bytes(secret: str, field: str) -> bytes:
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 16:
        raise EnforcementOutcomeIntakeError(f"{field} must contain at least 16 UTF-8 bytes")
    return secret.encode("utf-8")


def derive_private_token(secret: str, value: str, *, prefix: str) -> str:
    """Derive a stable non-reversible token without persisting the source value."""
    key = _secret_bytes(secret, "secret")
    source = _require_string(value, "token source")
    digest = hmac.new(key, source.encode("utf-8"), hashlib.sha256).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _validate_public_url(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    raw = _require_string(value, "provenance.publicUrl")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise EnforcementOutcomeIntakeError("provenance.publicUrl must be a public https URL")
    return raw


def _normalize_case_facts(value: Any) -> Dict[str, Any]:
    if value in (None, {}):
        return {}
    if not isinstance(value, dict):
        raise EnforcementOutcomeIntakeError("caseFacts must be an object")
    unknown = set(value) - _SAFE_CASE_FACT_FIELDS
    if unknown:
        raise EnforcementOutcomeIntakeError(f"unsupported caseFacts fields: {sorted(unknown)}")
    out: Dict[str, Any] = {}
    for key, item in value.items():
        if key == "assessmentDate":
            out[key] = _parse_iso_date(item, "caseFacts.assessmentDate")
        elif key in {"durationDays", "priorViolations"}:
            if item is not None and (not isinstance(item, int) or isinstance(item, bool) or item < 0):
                raise EnforcementOutcomeIntakeError(f"invalid caseFacts.{key}")
            out[key] = item
        elif key in {"voluntaryDisclosure", "authorizationObtained"}:
            if item is not None and not isinstance(item, bool):
                raise EnforcementOutcomeIntakeError(f"invalid caseFacts.{key}")
            out[key] = item
        else:
            if item is not None and not isinstance(item, str):
                raise EnforcementOutcomeIntakeError(f"invalid caseFacts.{key}")
            out[key] = item.strip() if isinstance(item, str) else item
    return out


def _normalize_provenance(value: Any, *, record_secret: str, required: bool) -> Optional[Dict[str, Any]]:
    if value in (None, {}):
        if required:
            raise EnforcementOutcomeIntakeError("verified/reviewed records require provenance")
        return None
    if not isinstance(value, dict):
        raise EnforcementOutcomeIntakeError("provenance must be an object")
    source_type = _require_string(value.get("sourceType"), "provenance.sourceType")
    if source_type in _FORBIDDEN_SOURCE_TYPES or source_type not in _ALLOWED_SOURCE_TYPES:
        raise EnforcementOutcomeIntakeError(f"ineligible provenance.sourceType: {source_type}")
    authority = _require_string(value.get("authority"), "provenance.authority")
    source_record_id = _require_string(value.get("recordId"), "provenance.recordId")
    return {
        "sourceType": source_type,
        "authority": authority,
        "recordId": derive_private_token(record_secret, source_record_id, prefix="src"),
        "publicUrl": _validate_public_url(value.get("publicUrl")),
    }


def _normalize_outcome(value: Any, *, required: bool) -> Optional[Dict[str, Any]]:
    if value in (None, {}):
        if required:
            raise EnforcementOutcomeIntakeError("independently reviewed records require an outcome")
        return None
    if not isinstance(value, dict):
        raise EnforcementOutcomeIntakeError("outcome must be an object")
    decision_date = _parse_iso_date(value.get("decisionDate"), "outcome.decisionDate")
    monetary = value.get("monetaryOutcomeKrw")
    if monetary is not None and (not isinstance(monetary, int) or isinstance(monetary, bool) or monetary < 0):
        raise EnforcementOutcomeIntakeError("invalid outcome.monetaryOutcomeKrw")
    dispositions = value.get("dispositionTypes", [])
    if not isinstance(dispositions, list) or any(not isinstance(x, str) or not x.strip() for x in dispositions):
        raise EnforcementOutcomeIntakeError("outcome.dispositionTypes must be an array of non-empty strings")
    normalized_dispositions = [x.strip() for x in dispositions]
    if len(normalized_dispositions) != len(set(normalized_dispositions)):
        raise EnforcementOutcomeIntakeError("duplicate outcome.dispositionTypes")
    primary = value.get("primaryDispositionType")
    if primary is not None:
        primary = _require_string(primary, "outcome.primaryDispositionType")
        if primary not in normalized_dispositions:
            raise EnforcementOutcomeIntakeError("primary disposition must appear in dispositionTypes")
    if required and monetary is None and not normalized_dispositions:
        raise EnforcementOutcomeIntakeError("reviewed outcome has no scoreable label")
    return {
        "decisionDate": decision_date,
        "monetaryOutcomeKrw": monetary,
        "dispositionTypes": normalized_dispositions,
        "primaryDispositionType": primary,
    }


def _normalize_history(value: Any, *, reviewer_secret: str, current_stage: str) -> list[Dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise EnforcementOutcomeIntakeError("reviewHistory must contain at least one event")
    out: list[Dict[str, Any]] = []
    previous: Optional[str] = None
    for index, event in enumerate(value):
        if not isinstance(event, dict):
            raise EnforcementOutcomeIntakeError("reviewHistory event must be an object")
        stage = _require_string(event.get("stage"), f"reviewHistory[{index}].stage")
        if stage not in _ALLOWED_STAGES:
            raise EnforcementOutcomeIntakeError(f"unsupported review stage: {stage}")
        if stage not in _ALLOWED_TRANSITIONS[previous]:
            raise EnforcementOutcomeIntakeError(f"invalid review transition: {previous or 'START'} -> {stage}")
        at = _parse_iso_datetime(event.get("at"), f"reviewHistory[{index}].at")
        actor_ref = _require_string(event.get("reviewerReference"), f"reviewHistory[{index}].reviewerReference")
        reason_code = event.get("reasonCode")
        if stage == "REJECTED":
            reason_code = _require_string(reason_code, f"reviewHistory[{index}].reasonCode")
            if reason_code not in _ALLOWED_REJECTION_CODES:
                raise EnforcementOutcomeIntakeError(f"unsupported rejection reason: {reason_code}")
        elif reason_code is not None:
            raise EnforcementOutcomeIntakeError("reasonCode is allowed only for REJECTED events")
        out.append({
            "stage": stage,
            "at": at,
            "actorToken": derive_private_token(reviewer_secret, actor_ref, prefix="reviewer"),
            **({"reasonCode": reason_code} if reason_code else {}),
        })
        previous = stage
    if previous != current_stage:
        raise EnforcementOutcomeIntakeError("reviewHistory final stage must equal reviewStage")
    return out


def normalize_private_intake_record(
    raw: Any,
    *,
    record_secret: str,
    reviewer_secret: str,
) -> Dict[str, Any]:
    """Convert one private offline record into the de-identified intake shape."""
    if not isinstance(raw, dict):
        raise EnforcementOutcomeIntakeError("intake record must be an object")
    _reject_forbidden_fields(raw)
    source_record_id = _require_string(raw.get("sourceRecordId"), "sourceRecordId")
    stage = _require_string(raw.get("reviewStage"), "reviewStage")
    if stage not in _ALLOWED_STAGES:
        raise EnforcementOutcomeIntakeError(f"unsupported reviewStage: {stage}")
    case_id = derive_private_token(record_secret, source_record_id, prefix="case")
    case_facts = _normalize_case_facts(raw.get("caseFacts"))
    provenance = _normalize_provenance(
        raw.get("provenance"),
        record_secret=record_secret,
        required=stage in {"SOURCE_VERIFIED", "INDEPENDENTLY_REVIEWED"},
    )
    outcome = _normalize_outcome(raw.get("outcome"), required=stage == "INDEPENDENTLY_REVIEWED")
    history = _normalize_history(raw.get("reviewHistory"), reviewer_secret=reviewer_secret, current_stage=stage)
    independent = raw.get("independentFromPrediction")
    if stage == "INDEPENDENTLY_REVIEWED" and independent is not True:
        raise EnforcementOutcomeIntakeError("reviewed label must be independent from prediction output")
    if independent not in (None, True, False):
        raise EnforcementOutcomeIntakeError("independentFromPrediction must be boolean or null")
    reviewer_role = raw.get("reviewerRole")
    if stage == "INDEPENDENTLY_REVIEWED":
        reviewer_role = _require_string(reviewer_role, "reviewerRole")
    elif reviewer_role is not None and (not isinstance(reviewer_role, str) or not reviewer_role.strip()):
        raise EnforcementOutcomeIntakeError("invalid reviewerRole")

    return {
        "caseId": case_id,
        "reviewStage": stage,
        "caseFacts": case_facts,
        "provenance": provenance,
        "outcome": outcome,
        "independentFromPrediction": independent,
        "reviewerRole": reviewer_role.strip() if isinstance(reviewer_role, str) else None,
        "reviewHistory": history,
    }


def normalize_private_intake_dataset(
    data: Any,
    *,
    record_secret: str,
    reviewer_secret: str,
) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise EnforcementOutcomeIntakeError("private intake dataset must be an object")
    _reject_forbidden_fields(data)
    if data.get("schemaVersion") != INTAKE_SCHEMA_VERSION:
        raise EnforcementOutcomeIntakeError("unsupported intake schemaVersion")
    dataset_version = _require_string(data.get("datasetVersion"), "datasetVersion")
    if data.get("jurisdiction") != "KR":
        raise EnforcementOutcomeIntakeError("unsupported jurisdiction")
    records = data.get("records")
    if not isinstance(records, list):
        raise EnforcementOutcomeIntakeError("records must be an array")
    normalized = [
        normalize_private_intake_record(row, record_secret=record_secret, reviewer_secret=reviewer_secret)
        for row in records
    ]
    ids = [row["caseId"] for row in normalized]
    if len(ids) != len(set(ids)):
        raise EnforcementOutcomeIntakeError("duplicate source records detected after de-identification")
    return {
        "schemaVersion": INTAKE_SCHEMA_VERSION,
        "datasetVersion": dataset_version,
        "jurisdiction": "KR",
        "records": normalized,
    }


def validate_safe_intake_dataset(data: Any) -> Dict[str, Any]:
    """Validate an already de-identified intake dataset before persistence/export."""
    if not isinstance(data, dict):
        raise EnforcementOutcomeIntakeError("safe intake dataset must be an object")
    _reject_forbidden_fields(data)
    if data.get("schemaVersion") != INTAKE_SCHEMA_VERSION:
        raise EnforcementOutcomeIntakeError("unsupported intake schemaVersion")
    _require_string(data.get("datasetVersion"), "datasetVersion")
    if data.get("jurisdiction") != "KR":
        raise EnforcementOutcomeIntakeError("unsupported jurisdiction")
    rows = data.get("records")
    if not isinstance(rows, list):
        raise EnforcementOutcomeIntakeError("records must be an array")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise EnforcementOutcomeIntakeError("safe intake record must be an object")
        case_id = _require_string(row.get("caseId"), "caseId")
        if not case_id.startswith("case_"):
            raise EnforcementOutcomeIntakeError("safe intake caseId must be derived")
        if case_id in seen:
            raise EnforcementOutcomeIntakeError(f"duplicate caseId: {case_id}")
        seen.add(case_id)
        stage = _require_string(row.get("reviewStage"), f"{case_id}.reviewStage")
        if stage not in _ALLOWED_STAGES:
            raise EnforcementOutcomeIntakeError(f"unsupported reviewStage: {stage}")
        _normalize_case_facts(row.get("caseFacts"))
        provenance = row.get("provenance")
        if stage in {"SOURCE_VERIFIED", "INDEPENDENTLY_REVIEWED"} and not isinstance(provenance, dict):
            raise EnforcementOutcomeIntakeError(f"{case_id} requires provenance")
        if isinstance(provenance, dict):
            if not str(provenance.get("recordId") or "").startswith("src_"):
                raise EnforcementOutcomeIntakeError(f"{case_id} provenance.recordId must be derived")
            _normalize_provenance_for_safe_record(provenance)
        _validate_safe_history(row.get("reviewHistory"), current_stage=stage)
        if stage == "INDEPENDENTLY_REVIEWED":
            if row.get("independentFromPrediction") is not True:
                raise EnforcementOutcomeIntakeError(f"{case_id} is not independent from prediction")
            _require_string(row.get("reviewerRole"), f"{case_id}.reviewerRole")
            _normalize_outcome(row.get("outcome"), required=True)
    return deepcopy(data)


def _normalize_provenance_for_safe_record(value: Dict[str, Any]) -> None:
    source_type = _require_string(value.get("sourceType"), "provenance.sourceType")
    if source_type not in _ALLOWED_SOURCE_TYPES:
        raise EnforcementOutcomeIntakeError(f"ineligible provenance.sourceType: {source_type}")
    _require_string(value.get("authority"), "provenance.authority")
    _require_string(value.get("recordId"), "provenance.recordId")
    _validate_public_url(value.get("publicUrl"))


def _validate_safe_history(value: Any, *, current_stage: str) -> None:
    if not isinstance(value, list) or not value:
        raise EnforcementOutcomeIntakeError("reviewHistory must contain at least one event")
    previous: Optional[str] = None
    for event in value:
        if not isinstance(event, dict):
            raise EnforcementOutcomeIntakeError("reviewHistory event must be an object")
        stage = _require_string(event.get("stage"), "reviewHistory.stage")
        if stage not in _ALLOWED_STAGES or stage not in _ALLOWED_TRANSITIONS[previous]:
            raise EnforcementOutcomeIntakeError(f"invalid review transition: {previous or 'START'} -> {stage}")
        _parse_iso_datetime(event.get("at"), "reviewHistory.at")
        actor = _require_string(event.get("actorToken"), "reviewHistory.actorToken")
        if not actor.startswith("reviewer_"):
            raise EnforcementOutcomeIntakeError("reviewHistory.actorToken must be derived")
        reason = event.get("reasonCode")
        if stage == "REJECTED":
            reason = _require_string(reason, "reviewHistory.reasonCode")
            if reason not in _ALLOWED_REJECTION_CODES:
                raise EnforcementOutcomeIntakeError(f"unsupported rejection reason: {reason}")
        elif reason is not None:
            raise EnforcementOutcomeIntakeError("reasonCode is allowed only for REJECTED events")
        previous = stage
    if previous != current_stage:
        raise EnforcementOutcomeIntakeError("reviewHistory final stage must equal reviewStage")


def promote_reviewed_ground_truth(data: Any) -> Dict[str, Any]:
    """Export only independently reviewed records to the evaluator schema."""
    safe = validate_safe_intake_dataset(data)
    rows: list[Dict[str, Any]] = []
    for row in safe["records"]:
        if row["reviewStage"] != "INDEPENDENTLY_REVIEWED":
            continue
        history = row["reviewHistory"]
        reviewed_at = history[-1]["at"][:10]
        promoted: Dict[str, Any] = {
            "caseId": row["caseId"],
            "reviewStatus": "INDEPENDENTLY_REVIEWED",
            "reviewedAt": reviewed_at,
            "reviewerRole": row["reviewerRole"],
            "independentFromPrediction": True,
            "provenance": deepcopy(row["provenance"]),
            "outcome": deepcopy(row["outcome"]),
        }
        if row.get("caseFacts"):
            promoted["caseFacts"] = deepcopy(row["caseFacts"])
        rows.append(promoted)
    ground_truth = {
        "schemaVersion": GROUND_TRUTH_SCHEMA_VERSION,
        "datasetVersion": safe["datasetVersion"],
        "jurisdiction": "KR",
        "records": rows,
    }
    try:
        return validate_outcome_ground_truth_dataset(ground_truth)
    except EnforcementOutcomeEvaluationError as exc:
        raise EnforcementOutcomeIntakeError(str(exc)) from exc


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EnforcementOutcomeIntakeError(f"unable to read JSON: {path}") from exc


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
