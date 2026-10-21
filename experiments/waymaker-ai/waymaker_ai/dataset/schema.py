"""A small JSON Schema interpreter for ``schemas/example.schema.json``.

Why hand-written: the experiment package is standard-library only, so the
``jsonschema`` package is not available. Why an *interpreter* rather than a
list of hard-coded checks: the schema file stays the single source of truth.
If someone edits the schema, the validator follows it without a second copy of
the rules drifting in Python.

Only the keywords the example schema actually uses are supported. Loading a
schema that uses any other keyword raises ``SchemaError`` instead of silently
ignoring it, so the validator fails closed when the schema grows.

Two deliberate differences from a stock JSON Schema validator:

* ``format: date`` is an assertion here, not an annotation. A label dated
  "2026-13-01" or "20261019" is a data error in this dataset.
* ``pattern`` follows JSON Schema search semantics, but a trailing ``$`` means
  end of string. Python's ``$`` also matches before a final newline, which
  would let "abcd\\n" pass an anchored id pattern.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = EXPERIMENT_ROOT / "schemas" / "example.schema.json"

#: Keywords that only describe; they never fail an instance.
ANNOTATION_KEYWORDS = frozenset({"$schema", "$id", "title", "description"})

#: Keywords this interpreter enforces.
ASSERTION_KEYWORDS = frozenset({
    "type",
    "enum",
    "const",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "pattern",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "format",
})

SUPPORTED_FORMATS = frozenset({"date"})

_ISO_DATE_SHAPE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class SchemaError(Exception):
    """The schema itself uses something this interpreter cannot enforce."""


@dataclass(frozen=True)
class SchemaViolation:
    path: str        # dotted path, e.g. "input.claim.citations[0]"; "" is the root
    keyword: str     # the schema keyword that failed
    message: str


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_schema(path: Path = DEFAULT_SCHEMA_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        schema = json.load(handle)
    check_supported(schema)
    return schema


def check_supported(schema: Any, where: str = "#") -> None:
    """Raise SchemaError for any keyword or format the interpreter does not enforce."""
    if not isinstance(schema, dict):
        raise SchemaError(f"{where}: a schema must be an object")
    for keyword, value in schema.items():
        if keyword in ANNOTATION_KEYWORDS:
            continue
        if keyword not in ASSERTION_KEYWORDS:
            raise SchemaError(f"{where}: keyword {keyword!r} is not supported by the dataset validator")
        if keyword == "format" and value not in SUPPORTED_FORMATS:
            raise SchemaError(f"{where}: format {value!r} is not supported")
        if keyword == "pattern":
            re.compile(_anchored(value))
    for name, child in (schema.get("properties") or {}).items():
        check_supported(child, f"{where}/properties/{name}")
    if isinstance(schema.get("additionalProperties"), dict):
        check_supported(schema["additionalProperties"], f"{where}/additionalProperties")
    if "items" in schema:
        check_supported(schema["items"], f"{where}/items")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_instance(instance: Any, schema: Mapping[str, Any], path: str = "") -> List[SchemaViolation]:
    """Return every violation of ``schema`` by ``instance`` (empty list = valid)."""
    violations: List[SchemaViolation] = []
    if "type" in schema and not _type_matches(instance, schema["type"]):
        violations.append(SchemaViolation(path, "type", f"expected {_describe_type(schema['type'])}, got {_json_type(instance)}"))
        return violations  # every other keyword would only repeat this error
    if "const" in schema and not _strict_equal(instance, schema["const"]):
        violations.append(SchemaViolation(path, "const", f"must be {json.dumps(schema['const'], ensure_ascii=False)}"))
    if "enum" in schema and not any(_strict_equal(instance, option) for option in schema["enum"]):
        allowed = ", ".join(json.dumps(option, ensure_ascii=False) for option in schema["enum"])
        violations.append(SchemaViolation(path, "enum", f"must be one of {allowed}"))
    if isinstance(instance, dict):
        violations.extend(_validate_object(instance, schema, path))
    elif isinstance(instance, list):
        violations.extend(_validate_array(instance, schema, path))
    elif isinstance(instance, str):
        violations.extend(_validate_string(instance, schema, path))
    elif _is_number(instance):
        violations.extend(_validate_number(instance, schema, path))
    return violations


def _validate_object(instance: Dict[str, Any], schema: Mapping[str, Any], path: str) -> List[SchemaViolation]:
    violations: List[SchemaViolation] = []
    for name in schema.get("required", ()):
        if name not in instance:
            violations.append(SchemaViolation(_join(path, name), "required", "is required"))
    properties = schema.get("properties") or {}
    extra = schema.get("additionalProperties", True)
    for name in sorted(instance):
        child_path = _join(path, name)
        if name in properties:
            violations.extend(validate_instance(instance[name], properties[name], child_path))
        elif extra is False:
            violations.append(SchemaViolation(child_path, "additionalProperties", "is not an allowed property"))
        elif isinstance(extra, dict):
            violations.extend(validate_instance(instance[name], extra, child_path))
    return violations


def _validate_array(instance: List[Any], schema: Mapping[str, Any], path: str) -> List[SchemaViolation]:
    if "items" not in schema:
        return []
    violations: List[SchemaViolation] = []
    for index, item in enumerate(instance):
        violations.extend(validate_instance(item, schema["items"], f"{path}[{index}]"))
    return violations


def _validate_string(instance: str, schema: Mapping[str, Any], path: str) -> List[SchemaViolation]:
    violations: List[SchemaViolation] = []
    if "minLength" in schema and len(instance) < schema["minLength"]:
        violations.append(SchemaViolation(path, "minLength", f"must have at least {schema['minLength']} characters"))
    if "maxLength" in schema and len(instance) > schema["maxLength"]:
        violations.append(SchemaViolation(path, "maxLength", f"must have at most {schema['maxLength']} characters"))
    if "pattern" in schema and not re.search(_anchored(schema["pattern"]), instance):
        violations.append(SchemaViolation(path, "pattern", f"must match {schema['pattern']}"))
    if schema.get("format") == "date" and not is_iso_date(instance):
        violations.append(SchemaViolation(path, "format", "must be a calendar date written YYYY-MM-DD"))
    return violations


def _validate_number(instance: float, schema: Mapping[str, Any], path: str) -> List[SchemaViolation]:
    violations: List[SchemaViolation] = []
    if "minimum" in schema and instance < schema["minimum"]:
        violations.append(SchemaViolation(path, "minimum", f"must be >= {schema['minimum']}"))
    if "maximum" in schema and instance > schema["maximum"]:
        violations.append(SchemaViolation(path, "maximum", f"must be <= {schema['maximum']}"))
    return violations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_iso_date(value: Any) -> bool:
    """True for a real calendar date written exactly YYYY-MM-DD."""
    if not isinstance(value, str) or not _ISO_DATE_SHAPE.match(value):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _anchored(pattern: str) -> str:
    """Make a trailing ``$`` mean end of string (see module docstring)."""
    if pattern.endswith("$") and not pattern.endswith("\\$"):
        return pattern[:-1] + r"\Z"
    return pattern


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": _is_number,
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "null": lambda v: v is None,
}


def _type_matches(value: Any, expected: Any) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    for name in names:
        if name not in _TYPE_CHECKS:
            raise SchemaError(f"type {name!r} is not supported")
        if _TYPE_CHECKS[name](value):
            return True
    return False


def _describe_type(expected: Any) -> str:
    return " or ".join(expected) if isinstance(expected, list) else str(expected)


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _strict_equal(left: Any, right: Any) -> bool:
    """JSON equality: False is not 0 and 1 is not True."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if left is None or right is None:
        return left is None and right is None
    if type(left) is not type(right) and not (_is_number(left) and _is_number(right)):
        return False
    return left == right


def _join(path: str, name: str) -> str:
    return f"{path}.{name}" if path else name


def describe_path(path: Optional[str]) -> str:
    return path if path else "(root)"
