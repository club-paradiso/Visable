"""Privacy-safe intake pipeline for Enforcement Intelligence v3 outcome review.

Private source identifiers and reviewer references are consumed only to derive
HMAC tokens. They are never returned. The runtime validator is intentionally
closed-shape, mirroring the checked-in safe JSON Schema, and only independently
reviewed rows may be promoted into the existing outcome evaluator contract.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
import hashlib
import hmac
import ipaddress
import json
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .enforcement_outcome_evaluation import (
    GROUND_TRUTH_SCHEMA_VERSION,
    EnforcementOutcomeEvaluationError,
    validate_outcome_ground_truth_dataset,
)

INTAKE_SCHEMA_VERSION = "1.0.0"
_ALLOWED_STAGES = {"STAGED", "SOURCE_VERIFIED", "INDEPENDENTLY_REVIEWED", "REJECTED"}
_ALLOWED_TRANSITIONS = {
    None: {"STAGED"},
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
_FORBIDDEN_SOURCE_TYPES = {"SYNTHETIC", "MODEL_GENERATED", "LLM_GENERATED", "PREDICTION_OUTPUT"}
_ALLOWED_REJECTION_CODES = {
    "SOURCE_INELIGIBLE",
    "PII_PRESENT",
    "DUPLICATE",
    "INSUFFICIENT_EVIDENCE",
    "PREDICTION_DERIVED",
    "REVIEW_CONFLICT",
}
_ALLOWED_REVIEWER_ROLES = {
    "AUTHORIZED_ADMINISTRATIVE_REVIEWER",
    "LEGAL_REVIEWER",
    "DATA_QUALITY_REVIEWER",
    "AUTHORIZED_RECORD_REVIEWER",
}
_FORBIDDEN_KEYS = {
    "rawText", "text", "caseText", "narrative", "freeText", "notes",
    "name", "fullName", "passportNumber", "alienRegistrationNumber",
    "registrationNumber", "phone", "phoneNumber", "email", "address",
    "dateOfBirth", "birthDate", "modelOutput", "predictionOutput",
}
_PRIVATE_ONLY_KEYS = {"sourceRecordId", "reviewerReference"}
_DATASET_KEYS = {"schemaVersion", "datasetVersion", "jurisdiction", "records"}
_PRIVATE_RECORD_KEYS = {
    "sourceRecordId", "reviewStage", "caseFacts", "provenance", "outcome",
    "independentFromPrediction", "reviewerRole", "reviewHistory",
}
_SAFE_RECORD_KEYS = {
    "caseId", "reviewStage", "caseFacts", "provenance", "outcome",
    "independentFromPrediction", "reviewerRole", "reviewHistory",
}
_CASE_FACT_KEYS = {
    "statusOfStay", "violationCode", "durationDays", "priorViolations",
    "voluntaryDisclosure", "authorizationObtained", "assessmentDate",
}
_PRIVATE_HISTORY_KEYS = {"stage", "at", "reviewerReference", "reasonCode"}
_SAFE_HISTORY_KEYS = {"stage", "at", "actorToken", "reasonCode"}
_PROVENANCE_KEYS = {"sourceType", "authority", "recordId", "publicUrl"}
_OUTCOME_KEYS = {"decisionDate", "monetaryOutcomeKrw", "dispositionTypes", "primaryDispositionType"}


class EnforcementOutcomeIntakeError(ValueError):
    """Raised when an intake record cannot be normalized or safely exported."""


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnforcementOutcomeIntakeError(f"invalid or missing {field}")
    return value.strip()


def _require_exact_keys(value: Dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise EnforcementOutcomeIntakeError(f"unsupported fields in {field}: {sorted(unknown)}")


def _parse_iso_date(value: Any, field: str) -> str:
    raw = _require_string(value, field)
    try:
        date.fromisoformat(raw)
    except ValueError as exc:
        raise EnforcementOutcomeIntakeError(f"invalid {field}") from exc
    return raw


def _parse_iso_datetime(value: Any, field: str) -> tuple[str, datetime]:
    raw = _require_string(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EnforcementOutcomeIntakeError(f"invalid {field}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EnforcementOutcomeIntakeError(f"{field} must include a timezone offset")
    return raw, parsed


def _reject_forbidden_fields(value: Any, *, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _FORBIDDEN_KEYS:
                raise EnforcementOutcomeIntakeError(f"forbidden field: {path}.{key}")
            _reject_forbidden_fields(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_fields(child, path=f"{path}[{index}]")


def _reject_private_only_fields(value: Any, *, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _PRIVATE_ONLY_KEYS:
                raise EnforcementOutcomeIntakeError(f"private-only field leaked into safe dataset: {path}.{key}")
            _reject_private_only_fields(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_private_only_fields(child, path=f"{path}[{index}]")


def _secret_bytes(secret: str, field: str) -> bytes:
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
        raise EnforcementOutcomeIntakeError(f"{field} must contain at least 32 UTF-8 bytes")
    return secret.encode("utf-8")


def derive_private_token(secret: str, value: str, *, prefix: str) -> str:
    key = _secret_bytes(secret, "secret")
    source = _require_string(value, "token source")
    digest = hmac.new(key, source.encode("utf-8"), hashlib.sha256).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _validate_public_url(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    raw = _require_string(value, "provenance.publicUrl")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise EnforcementOutcomeIntakeError("provenance.publicUrl must be a public https URL")
    host = parsed.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith(".local"):
        raise EnforcementOutcomeIntakeError("provenance.publicUrl must not use a local host")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and (
        address.is_private or address.is_loopback or address.is_link_local
        or address.is_reserved or address.is_unspecified
    ):
        raise EnforcementOutcomeIntakeError("provenance.publicUrl must not use a non-public IP")
    return raw


def _normalize_case_facts(value: Any) -> Dict[str, Any]:
    if value in (None, {}):
        return {}
    if not isinstance(value, dict):
        raise EnforcementOutcomeIntakeError("caseFacts must be an object")
    _require_exact_keys(value, _CASE_FACT_KEYS, "caseFacts")
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


def _normalize_private_provenance(value: Any, *, record_secret: str, required: bool) -> Optional[Dict[str, Any]]:
    if value in (None, {}):
        if required:
            raise EnforcementOutcomeIntakeError("verified/reviewed records require provenance")
        return None
    if not isinstance(value, dict):
        raise EnforcementOutcomeIntakeError("provenance must be an object")
    _require_exact_keys(value, _PROVENANCE_KEYS, "provenance")
    source_type = _require_string(value.get("sourceType"), "provenance.sourceType")
    if source_type in _FORBIDDEN_SOURCE_TYPES or source_type not in _ALLOWED_SOURCE_TYPES:
        raise EnforcementOutcomeIntakeError(f"ineligible provenance.sourceType: {source_type}")
    return {
        "sourceType": source_type,
        "authority": _require_string(value.get("authority"), "provenance.authority"),
        "recordId": derive_private_token(
            record_secret,
            _require_string(value.get("recordId"), "provenance.recordId"),
            prefix="src",
        ),
        "publicUrl": _validate_public_url(value.get("publicUrl")),
    }


def _validate_safe_provenance(value: Dict[str, Any]) -> None:
    _require_exact_keys(value, _PROVENANCE_KEYS, "provenance")
    source_type = _require_string(value.get("sourceType"), "provenance.sourceType")
    if source_type not in _ALLOWED_SOURCE_TYPES:
        raise EnforcementOutcomeIntakeError(f"ineligible provenance.sourceType: {source_type}")
    _require_string(value.get("authority"), "provenance.authority")
    record_id = _require_string(value.get("recordId"), "provenance.recordId")
    if not record_id.startswith("src_") or len(record_id) != 28:
        raise EnforcementOutcomeIntakeError("provenance.recordId must be a derived token")
    _validate_public_url(value.get("publicUrl"))


def _normalize_outcome(value: Any, *, required: bool) -> Optional[Dict[str, Any]]:
    if value in (None, {}):
        if required:
            raise EnforcementOutcomeIntakeError("independently reviewed records require an outcome")
        return None
    if not isinstance(value, dict):
        raise EnforcementOutcomeIntakeError("outcome must be an object")
    _require_exact_keys(value, _OUTCOME_KEYS, "outcome")
    decision_date = _parse_iso_date(value.get("decisionDate"), "outcome.decisionDate")
    monetary = value.get("monetaryOutcomeKrw")
    if monetary is not None and (not isinstance(monetary, int) or isinstance(monetary, bool) or monetary < 0):
        raise EnforcementOutcomeIntakeError("invalid outcome.monetaryOutcomeKrw")
    dispositions = value.get("dispositionTypes", [])
    if not isinstance(dispositions, list) or any(not isinstance(x, str) or not x.strip() for x in dispositions):
        raise EnforcementOutcomeIntakeError("outcome.dispositionTypes must be an array of non-empty strings")
    normalized = [x.strip() for x in dispositions]
    if len(normalized) != len(set(normalized)):
        raise EnforcementOutcomeIntakeError("duplicate outcome.dispositionTypes")
    primary = value.get("primaryDispositionType")
    if primary is not None:
        primary = _require_string(primary, "outcome.primaryDispositionType")
        if primary not in normalized:
            raise EnforcementOutcomeIntakeError("primary disposition must appear in dispositionTypes")
    if required and monetary is None and not normalized:
        raise EnforcementOutcomeIntakeError("reviewed outcome has no scoreable label")
    return {
        "decisionDate": decision_date,
        "monetaryOutcomeKrw": monetary,
        "dispositionTypes": normalized,
        "primaryDispositionType": primary,
    }


def _validated_reviewer_role(value: Any, *, required: bool) -> Optional[str]:
    if value in (None, ""):
        if required:
            raise EnforcementOutcomeIntakeError("reviewed record requires reviewerRole")
        return None
    role = _require_string(value, "reviewerRole")
    if role not in _ALLOWED_REVIEWER_ROLES:
        raise EnforcementOutcomeIntakeError("reviewerRole must be a non-identifying approved role code")
    return role


def _normalize_history(value: Any, *, reviewer_secret: str, current_stage: str) -> list[Dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise EnforcementOutcomeIntakeError("reviewHistory must contain at least one event")
    out: list[Dict[str, Any]] = []
    previous: Optional[str] = None
    previous_at: Optional[datetime] = None
    for index, event in enumerate(value):
        if not isinstance(event, dict):
            raise EnforcementOutcomeIntakeError("reviewHistory event must be an object")
        _require_exact_keys(event, _PRIVATE_HISTORY_KEYS, f"reviewHistory[{index}]")
        stage = _require_string(event.get("stage"), f"reviewHistory[{index}].stage")
        if stage not in _ALLOWED_STAGES or stage not in _ALLOWED_TRANSITIONS[previous]:
            raise EnforcementOutcomeIntakeError(f"invalid review transition: {previous or 'START'} -> {stage}")
        at, parsed_at = _parse_iso_datetime(event.get("at"), f"reviewHistory[{index}].at")
        if previous_at is not None and parsed_at < previous_at:
            raise EnforcementOutcomeIntakeError("reviewHistory timestamps must be chronological")
        reason = event.get("reasonCode")
        if stage == "REJECTED":
            reason = _require_string(reason, f"reviewHistory[{index}].reasonCode")
            if reason not in _ALLOWED_REJECTION_CODES:
                raise EnforcementOutcomeIntakeError(f"unsupported rejection reason: {reason}")
        elif reason is not None:
            raise EnforcementOutcomeIntakeError("reasonCode is allowed only for REJECTED events")
        actor_ref = _require_string(event.get("reviewerReference"), f"reviewHistory[{index}].reviewerReference")
        out.append({
            "stage": stage,
            "at": at,
            "actorToken": derive_private_token(reviewer_secret, actor_ref, prefix="reviewer"),
            **({"reasonCode": reason} if reason else {}),
        })
        previous, previous_at = stage, parsed_at
    if previous != current_stage:
        raise EnforcementOutcomeIntakeError("reviewHistory final stage must equal reviewStage")
    return out


def _validate_safe_history(value: Any, *, current_stage: str) -> None:
    if not isinstance(value, list) or not value:
        raise EnforcementOutcomeIntakeError("reviewHistory must contain at least one event")
    previous: Optional[str] = None
    previous_at: Optional[datetime] = None
    for index, event in enumerate(value):
        if not isinstance(event, dict):
            raise EnforcementOutcomeIntakeError("reviewHistory event must be an object")
        _require_exact_keys(event, _SAFE_HISTORY_KEYS, f"reviewHistory[{index}]")
        stage = _require_string(event.get("stage"), f"reviewHistory[{index}].stage")
        if stage not in _ALLOWED_STAGES or stage not in _ALLOWED_TRANSITIONS[previous]:
            raise EnforcementOutcomeIntakeError(f"invalid review transition: {previous or 'START'} -> {stage}")
        _, parsed_at = _parse_iso_datetime(event.get("at"), f"reviewHistory[{index}].at")
        if previous_at is not None and parsed_at < previous_at:
            raise EnforcementOutcomeIntakeError("reviewHistory timestamps must be chronological")
        actor = _require_string(event.get("actorToken"), f"reviewHistory[{index}].actorToken")
        if not actor.startswith("reviewer_") or len(actor) != 33:
            raise EnforcementOutcomeIntakeError("reviewHistory.actorToken must be a derived token")
        reason = event.get("reasonCode")
        if stage == "REJECTED":
            reason = _require_string(reason, f"reviewHistory[{index}].reasonCode")
            if reason not in _ALLOWED_REJECTION_CODES:
                raise EnforcementOutcomeIntakeError(f"unsupported rejection reason: {reason}")
        elif reason is not None:
            raise EnforcementOutcomeIntakeError("reasonCode is allowed only for REJECTED events")
        previous, previous_at = stage, parsed_at
    if previous != current_stage:
        raise EnforcementOutcomeIntakeError("reviewHistory final stage must equal reviewStage")


def normalize_private_intake_record(raw: Any, *, record_secret: str, reviewer_secret: str) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise EnforcementOutcomeIntakeError("intake record must be an object")
    _reject_forbidden_fields(raw)
    _require_exact_keys(raw, _PRIVATE_RECORD_KEYS, "private record")
    source_record_id = _require_string(raw.get("sourceRecordId"), "sourceRecordId")
    stage = _require_string(raw.get("reviewStage"), "reviewStage")
    if stage not in _ALLOWED_STAGES:
        raise EnforcementOutcomeIntakeError(f"unsupported reviewStage: {stage}")
    provenance = _normalize_private_provenance(
        raw.get("provenance"),
        record_secret=record_secret,
        required=stage in {"SOURCE_VERIFIED", "INDEPENDENTLY_REVIEWED"},
    )
    outcome = _normalize_outcome(raw.get("outcome"), required=stage == "INDEPENDENTLY_REVIEWED")
    independent = raw.get("independentFromPrediction")
    if stage == "INDEPENDENTLY_REVIEWED" and independent is not True:
        raise EnforcementOutcomeIntakeError("reviewed label must be independent from prediction output")
    if independent not in (None, True, False):
        raise EnforcementOutcomeIntakeError("independentFromPrediction must be boolean or null")
    reviewer_role = _validated_reviewer_role(raw.get("reviewerRole"), required=stage == "INDEPENDENTLY_REVIEWED")
    return {
        "caseId": derive_private_token(record_secret, source_record_id, prefix="case"),
        "reviewStage": stage,
        "caseFacts": _normalize_case_facts(raw.get("caseFacts")),
        "provenance": provenance,
        "outcome": outcome,
        "independentFromPrediction": independent,
        "reviewerRole": reviewer_role,
        "reviewHistory": _normalize_history(
            raw.get("reviewHistory"), reviewer_secret=reviewer_secret, current_stage=stage
        ),
    }


def normalize_private_intake_dataset(data: Any, *, record_secret: str, reviewer_secret: str) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise EnforcementOutcomeIntakeError("private intake dataset must be an object")
    _reject_forbidden_fields(data)
    _require_exact_keys(data, _DATASET_KEYS, "dataset")
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
    case_ids = [row["caseId"] for row in normalized]
    if len(case_ids) != len(set(case_ids)):
        raise EnforcementOutcomeIntakeError("duplicate source records detected after de-identification")
    source_ids = [row["provenance"]["recordId"] for row in normalized if row.get("provenance")]
    if len(source_ids) != len(set(source_ids)):
        raise EnforcementOutcomeIntakeError("duplicate provenance records detected after de-identification")
    return validate_safe_intake_dataset({
        "schemaVersion": INTAKE_SCHEMA_VERSION,
        "datasetVersion": dataset_version,
        "jurisdiction": "KR",
        "records": normalized,
    })


def validate_safe_intake_dataset(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise EnforcementOutcomeIntakeError("safe intake dataset must be an object")
    _reject_forbidden_fields(data)
    _reject_private_only_fields(data)
    _require_exact_keys(data, _DATASET_KEYS, "dataset")
    if data.get("schemaVersion") != INTAKE_SCHEMA_VERSION:
        raise EnforcementOutcomeIntakeError("unsupported intake schemaVersion")
    _require_string(data.get("datasetVersion"), "datasetVersion")
    if data.get("jurisdiction") != "KR":
        raise EnforcementOutcomeIntakeError("unsupported jurisdiction")
    rows = data.get("records")
    if not isinstance(rows, list):
        raise EnforcementOutcomeIntakeError("records must be an array")
    seen_cases: set[str] = set()
    seen_sources: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise EnforcementOutcomeIntakeError("safe intake record must be an object")
        _require_exact_keys(row, _SAFE_RECORD_KEYS, "safe record")
        case_id = _require_string(row.get("caseId"), "caseId")
        if not case_id.startswith("case_") or len(case_id) != 29:
            raise EnforcementOutcomeIntakeError("safe intake caseId must be a derived token")
        if case_id in seen_cases:
            raise EnforcementOutcomeIntakeError(f"duplicate caseId: {case_id}")
        seen_cases.add(case_id)
        stage = _require_string(row.get("reviewStage"), f"{case_id}.reviewStage")
        if stage not in _ALLOWED_STAGES:
            raise EnforcementOutcomeIntakeError(f"unsupported reviewStage: {stage}")
        _normalize_case_facts(row.get("caseFacts"))
        provenance = row.get("provenance")
        if stage in {"SOURCE_VERIFIED", "INDEPENDENTLY_REVIEWED"} and not isinstance(provenance, dict):
            raise EnforcementOutcomeIntakeError(f"{case_id} requires provenance")
        if isinstance(provenance, dict):
            _validate_safe_provenance(provenance)
            source_id = provenance["recordId"]
            if source_id in seen_sources:
                raise EnforcementOutcomeIntakeError(f"duplicate provenance recordId: {source_id}")
            seen_sources.add(source_id)
        _validate_safe_history(row.get("reviewHistory"), current_stage=stage)
        _validated_reviewer_role(row.get("reviewerRole"), required=stage == "INDEPENDENTLY_REVIEWED")
        if stage == "INDEPENDENTLY_REVIEWED":
            if row.get("independentFromPrediction") is not True:
                raise EnforcementOutcomeIntakeError(f"{case_id} is not independent from prediction")
            _normalize_outcome(row.get("outcome"), required=True)
        elif row.get("outcome") not in (None, {}):
            _normalize_outcome(row.get("outcome"), required=False)
    return deepcopy(data)


def promote_reviewed_ground_truth(data: Any) -> Dict[str, Any]:
    safe = validate_safe_intake_dataset(data)
    rows: list[Dict[str, Any]] = []
    for row in safe["records"]:
        if row["reviewStage"] != "INDEPENDENTLY_REVIEWED":
            continue
        promoted: Dict[str, Any] = {
            "caseId": row["caseId"],
            "reviewStatus": "INDEPENDENTLY_REVIEWED",
            "reviewedAt": row["reviewHistory"][-1]["at"][:10],
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
