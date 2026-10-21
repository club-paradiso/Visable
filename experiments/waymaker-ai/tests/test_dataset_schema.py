"""The hand-written JSON Schema interpreter (waymaker_ai.dataset.schema)."""
from __future__ import annotations

import pytest

from waymaker_ai.dataset.schema import (
    SchemaError,
    check_supported,
    is_iso_date,
    load_schema,
    validate_instance,
)


def _keywords(violations):
    return {(v.path, v.keyword) for v in violations}


def test_example_schema_loads_and_uses_only_supported_keywords():
    schema = load_schema()
    assert schema["properties"]["schema_version"]["const"] == "waymaker-example/0.1"


def test_unsupported_keyword_fails_closed():
    with pytest.raises(SchemaError):
        check_supported({"type": "object", "oneOf": []})
    with pytest.raises(SchemaError):
        check_supported({"type": "string", "format": "email"})


def test_type_required_and_additional_properties():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["a"],
        "properties": {"a": {"type": "integer"}, "b": {"type": ["string", "null"]}},
    }
    assert validate_instance({"a": 1, "b": None}, schema) == []
    found = _keywords(validate_instance({"b": 3, "c": True}, schema))
    assert ("a", "required") in found
    assert ("b", "type") in found
    assert ("c", "additionalProperties") in found


def test_booleans_are_not_integers_and_zero_is_not_false():
    assert validate_instance(True, {"type": "integer"})
    assert validate_instance(0, {"const": False})
    assert validate_instance(False, {"enum": [0, 1]})


def test_enum_with_null_member():
    schema = {"enum": [None, "A", "B"]}
    assert validate_instance(None, schema) == []
    assert validate_instance("A", schema) == []
    assert validate_instance("Z", schema)


def test_pattern_dollar_means_end_of_string():
    schema = {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]{3,80}$"}
    assert validate_instance("abcd", schema) == []
    assert validate_instance("abcd\n", schema), "a trailing newline must not pass an anchored id pattern"
    assert validate_instance("Abcd", schema)


def test_date_format_is_an_assertion():
    schema = {"type": "string", "format": "date"}
    assert validate_instance("2026-10-19", schema) == []
    for bad in ("2026-13-01", "20261019", "2026-02-30", "2026-10-19T00:00:00"):
        assert validate_instance(bad, schema), bad
    assert is_iso_date("2024-02-29") and not is_iso_date("2025-02-29")


def test_length_and_minimum():
    assert validate_instance("", {"type": "string", "minLength": 1})
    assert validate_instance("abc", {"type": "string", "maxLength": 2})
    assert validate_instance(0, {"type": "integer", "minimum": 1})


def test_nested_paths_are_reported():
    schema = load_schema()
    violations = validate_instance({"input": {"claim": {"citations": [3]}}}, schema)
    paths = {v.path for v in violations}
    assert "input.claim.citations[0]" in paths
    assert "input.question" in paths
