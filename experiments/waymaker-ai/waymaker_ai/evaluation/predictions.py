"""Normalized prediction shapes and the model structured-output contract.

Why one normalized shape per task: the baselines speak different vocabularies
(backend task types, JS step kinds, WLIE layer results, model JSON). Metrics
must compare like with like, so every baseline converts its native output into
the dict shapes below *before* scoring, and keeps its native output under
``raw`` for audit. A field a baseline cannot produce is simply absent from its
``emits`` set; the scorer then reports it as not scorable instead of wrong.

The model contract is deliberately small and closed: a model either returns a
JSON object with exactly these keys or its answer is invalid. An invalid answer
is scored wrong on every field (it is never treated as "no opinion").
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Tuple

from waymaker_ai.contracts import AnchorKind, FINE_PROCEDURES

# ---------------------------------------------------------------------------
# Normalized prediction fields per task
# ---------------------------------------------------------------------------
CLASSIFICATION_FIELDS: Tuple[str, ...] = (
    "status_code",          # parent (2-segment) code or None
    "subcode",              # exact subcode or None; never filled from a parent field
    "procedure_fine",       # contracts.FINE_PROCEDURES value or None
    "procedure_coarse",     # contracts.COARSE_PROCEDURES value or None
    "current_status",
    "target_status",
    "needs_clarification",  # bool or None
    "mentioned_codes",      # list of codes the baseline recognised in the text
)
ENTITY_FIELDS: Tuple[str, ...] = ("dates", "status_codes")
CITATION_FIELDS: Tuple[str, ...] = ("overall", "layer_codes", "codes", "highest_verified_layer", "injection_flagged")
TEMPORAL_FIELDS: Tuple[str, ...] = ("candidate_version_keys", "warnings", "determination")
ABSTENTION_FIELDS: Tuple[str, ...] = ("conclusion_withheld", "issues", "claims")

TASK_FIELDS: Dict[str, Tuple[str, ...]] = {
    "status_procedure_classification": CLASSIFICATION_FIELDS,
    "entity_date_extraction": ENTITY_FIELDS,
    "citation_verification": CITATION_FIELDS,
    "temporal_version_selection": TEMPORAL_FIELDS,
    "abstention": ABSTENTION_FIELDS,
}

#: Set on a prediction whose whole answer was unusable (e.g. not JSON). Every
#: emitted field is then scored wrong.
INVALID_OUTPUT_FLAG = "_invalid_output"

#: Set by model baselines only: how many contract violations the raw answer had
#: (``parse_model_output``). Scored as ``structured_output_valid`` (doc 13 G4).
SCHEMA_VIOLATIONS_KEY = "_schema_violations"


def empty_prediction(task: str) -> Dict[str, Any]:
    return {name: None for name in TASK_FIELDS[task]}


# ---------------------------------------------------------------------------
# Model structured-output contract
# ---------------------------------------------------------------------------
MODEL_CLASSIFICATION_KEYS: FrozenSet[str] = frozenset({
    "status_code", "subcode", "procedure", "current_status", "target_status", "dates", "needs_clarification",
})
MODEL_ABSTENTION_KEYS: FrozenSet[str] = frozenset({"conclusion_withheld", "issues", "claims"})

#: Tasks a model baseline answers. Citation and temporal tasks are answered by
#: deterministic code; a model is never asked to verify a citation.
MODEL_TASKS: FrozenSet[str] = frozenset({"status_procedure_classification", "entity_date_extraction", "abstention"})

_PARENT_CODE_RE = re.compile(r"[A-Z]-\d{1,2}\Z")
_SUBCODE_RE = re.compile(r"[A-Z]-\d{1,2}(-[0-9A-Z]{1,4})+\Z")
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_ROLES = frozenset(kind.value for kind in AnchorKind)


def model_keys_for(task: str) -> FrozenSet[str]:
    return MODEL_ABSTENTION_KEYS if task == "abstention" else MODEL_CLASSIFICATION_KEYS


def model_output_schema(task: str) -> Dict[str, Any]:
    """JSON Schema handed to a model server for constrained decoding."""
    nullable_string = {"type": ["string", "null"]}
    if task == "abstention":
        return {
            "type": "object",
            "additionalProperties": False,
            "required": sorted(MODEL_ABSTENTION_KEYS),
            "properties": {
                "conclusion_withheld": {"type": "boolean"},
                "issues": {"type": "array", "items": {"type": "string"}},
                "claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["text"],
                        "properties": {"text": {"type": "string"}, "assertion_key": nullable_string},
                    },
                },
            },
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(MODEL_CLASSIFICATION_KEYS),
        "properties": {
            "status_code": nullable_string,
            "subcode": nullable_string,
            "procedure": {"type": ["string", "null"], "enum": list(FINE_PROCEDURES) + [None]},
            "current_status": nullable_string,
            "target_status": nullable_string,
            "dates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["value", "role"],
                    "properties": {"value": {"type": "string"}, "role": {"type": ["string", "null"], "enum": sorted(_ROLES) + [None]}},
                },
            },
            "needs_clarification": {"type": "boolean"},
        },
    }


def parse_model_output(answer: Any, task: str) -> Tuple[Dict[str, Any], List[str]]:
    """Validate a model answer and convert it to the normalized prediction.

    Returns ``(prediction, violations)``. Field-level violations keep the raw
    value (so it is scored wrong, never silently dropped); an answer that is not
    a JSON object sets ``INVALID_OUTPUT_FLAG``.
    """
    violations: List[str] = []
    obj = answer
    if isinstance(answer, str):
        try:
            obj = json.loads(answer)
        except json.JSONDecodeError:
            obj = None
    if not isinstance(obj, dict):
        prediction = empty_prediction(task)
        prediction[INVALID_OUTPUT_FLAG] = True
        return prediction, ["answer is not a JSON object"]

    expected_keys = model_keys_for(task)
    for key in sorted(set(obj) - expected_keys):
        violations.append(f"unexpected key {key}")
    for key in sorted(expected_keys - set(obj)):
        violations.append(f"missing key {key}")

    if task == "abstention":
        return _abstention_prediction(obj, violations), violations
    return _classification_prediction(obj, task, violations), violations


def _classification_prediction(obj: Mapping[str, Any], task: str, violations: List[str]) -> Dict[str, Any]:
    status = _nullable_string(obj, "status_code", violations)
    if status is not None and not _PARENT_CODE_RE.match(status):
        violations.append("status_code is not a 2-segment parent code")
    subcode = _nullable_string(obj, "subcode", violations)
    if subcode is not None and not _SUBCODE_RE.match(subcode):
        violations.append("subcode is not a 3+-segment code")
    procedure = _nullable_string(obj, "procedure", violations)
    if procedure is not None and procedure not in FINE_PROCEDURES:
        violations.append("procedure is not a fine procedure id")
    clarification = obj.get("needs_clarification")
    if clarification is not None and not isinstance(clarification, bool):
        violations.append("needs_clarification is not a boolean")
        clarification = None
    dates = _model_dates(obj.get("dates"), violations)
    if task == "entity_date_extraction":
        codes = [c for c in (status, subcode) if c]
        return {"dates": dates, "status_codes": codes}
    return {
        "status_code": status,
        "subcode": subcode,
        "procedure_fine": procedure,
        "procedure_coarse": None,
        "current_status": _nullable_string(obj, "current_status", violations),
        "target_status": _nullable_string(obj, "target_status", violations),
        "needs_clarification": clarification,
        "mentioned_codes": [c for c in (status, subcode) if c],
    }


def _abstention_prediction(obj: Mapping[str, Any], violations: List[str]) -> Dict[str, Any]:
    withheld = obj.get("conclusion_withheld")
    if not isinstance(withheld, bool):
        violations.append("conclusion_withheld is not a boolean")
        withheld = None
    issues = []
    for issue in obj.get("issues") or []:
        key = issue.get("key") if isinstance(issue, dict) else issue
        if isinstance(key, str) and key:
            issues.append(key)
        else:
            violations.append("issue without a string key")
    claims = []
    for claim in obj.get("claims") or []:
        if isinstance(claim, str):
            claims.append({"text": claim, "assertion_key": None})
        elif isinstance(claim, dict) and isinstance(claim.get("text"), str):
            claims.append({"text": claim["text"], "assertion_key": claim.get("assertion_key") or claim.get("key")})
        else:
            violations.append("claim without text")
    return {"conclusion_withheld": withheld, "issues": issues, "claims": claims}


def _nullable_string(obj: Mapping[str, Any], key: str, violations: List[str]) -> Optional[str]:
    value = obj.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        violations.append(f"{key} is not a string")
        return str(value)
    value = value.strip()
    return value or None


def _model_dates(raw: Any, violations: List[str]) -> List[Dict[str, Optional[str]]]:
    dates: List[Dict[str, Optional[str]]] = []
    if raw is None:
        return dates
    if not isinstance(raw, list):
        violations.append("dates is not an array")
        return dates
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("value"), str):
            violations.append("date without a string value")
            continue
        value = item["value"].strip()
        role = item.get("role")
        if not _ISO_DATE_RE.match(value):
            violations.append("date value is not YYYY-MM-DD")
        if role is not None and role not in _ROLES:
            violations.append("date role is not an anchor kind")
        dates.append({"value": value, "role": role})
    return dates
