"""Versioned semantic registry for Enforcement Intelligence.

The ontology describes *what a violation concept is* and which facts materially
characterize it. It deliberately does not contain monetary tiers or predicted
outcomes; those remain in the separately versioned deterministic rule database.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

ONTOLOGY_PATH = Path(__file__).resolve().parents[1] / "data" / "enforcement" / "ontology.v1.json"
SUPPORTED_SCHEMA_VERSION = "1.0.0"
_ALLOWED_LIFECYCLES = {"ACTIVE", "DEPRECATED", "PLANNED"}


class EnforcementOntologyError(ValueError):
    """Raised when the checked-in ontology or a rule adapter violates its contract."""


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnforcementOntologyError(f"invalid or missing {field}")
    return value.strip()


def _require_unique_strings(values: Any, field: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise EnforcementOntologyError(f"invalid or missing {field}")
    cleaned = [_require_nonempty_string(item, field) for item in values]
    if len(cleaned) != len(set(cleaned)):
        raise EnforcementOntologyError(f"duplicate values in {field}")
    return cleaned


def validate_ontology_data(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise EnforcementOntologyError("ontology must be an object")
    if data.get("schemaVersion") != SUPPORTED_SCHEMA_VERSION:
        raise EnforcementOntologyError("unsupported enforcement ontology schema")
    _require_nonempty_string(data.get("ontologyVersion"), "ontologyVersion")
    if data.get("jurisdiction") != "KR":
        raise EnforcementOntologyError("unsupported enforcement ontology jurisdiction")

    fact_dimensions = set(_require_unique_strings(data.get("factDimensions"), "factDimensions"))
    violations = data.get("violations")
    if not isinstance(violations, list) or not violations:
        raise EnforcementOntologyError("ontology must contain violations")

    seen_codes: set[str] = set()
    for row in violations:
        if not isinstance(row, dict):
            raise EnforcementOntologyError("violation definition must be an object")
        code = _require_nonempty_string(row.get("code"), "violation.code")
        if code in seen_codes:
            raise EnforcementOntologyError(f"duplicate violation code: {code}")
        seen_codes.add(code)
        _require_nonempty_string(row.get("labelKo"), f"{code}.labelKo")
        _require_nonempty_string(row.get("category"), f"{code}.category")

        legal_basis = row.get("legalBasis")
        if not isinstance(legal_basis, dict):
            raise EnforcementOntologyError(f"invalid legalBasis for {code}")
        _require_nonempty_string(legal_basis.get("lawName"), f"{code}.legalBasis.lawName")
        _require_nonempty_string(legal_basis.get("article"), f"{code}.legalBasis.article")

        material = _require_unique_strings(row.get("materialFactDimensions"), f"{code}.materialFactDimensions")
        unknown_dimensions = sorted(set(material) - fact_dimensions)
        if unknown_dimensions:
            raise EnforcementOntologyError(
                f"unknown material fact dimension for {code}: {', '.join(unknown_dimensions)}"
            )

        if row.get("lifecycle") not in _ALLOWED_LIFECYCLES:
            raise EnforcementOntologyError(f"invalid lifecycle for {code}")
        if not isinstance(row.get("supportedByDeterministicRules"), bool):
            raise EnforcementOntologyError(f"invalid supportedByDeterministicRules for {code}")

    return deepcopy(data)


def load_enforcement_ontology(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or ONTOLOGY_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EnforcementOntologyError(f"unable to load enforcement ontology: {target}") from exc
    return validate_ontology_data(raw)


def violation_map(data: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    ontology = validate_ontology_data(data) if data is not None else load_enforcement_ontology()
    return {row["code"]: deepcopy(row) for row in ontology["violations"]}


def deterministic_violation_codes(data: Optional[Dict[str, Any]] = None) -> set[str]:
    return {
        code
        for code, row in violation_map(data).items()
        if row["supportedByDeterministicRules"] and row["lifecycle"] == "ACTIVE"
    }


def validate_legal_rule_database(
    rule_database: Dict[str, Any],
    *,
    ontology: Optional[Dict[str, Any]] = None,
) -> None:
    """Ensure deterministic legal rules cannot drift outside the semantic registry.

    This adapter is intentionally one-way: the ontology may contain PLANNED or
    non-deterministic concepts without forcing a monetary rule to exist. Any rule
    that *does* exist, however, must resolve to one active ontology definition and
    must agree on its public label and primary statute article.
    """

    definitions = violation_map(ontology)
    observed: set[str] = set()
    for snapshot in rule_database.get("snapshots") or []:
        for rule in snapshot.get("rules") or []:
            code = _require_nonempty_string(rule.get("violationCode"), "rule.violationCode")
            definition = definitions.get(code)
            if not definition:
                raise EnforcementOntologyError(f"deterministic rule missing from ontology: {code}")
            if definition.get("lifecycle") != "ACTIVE":
                raise EnforcementOntologyError(f"deterministic rule is not active in ontology: {code}")
            if not definition.get("supportedByDeterministicRules"):
                raise EnforcementOntologyError(f"ontology forbids deterministic rule for: {code}")
            if rule.get("label") != definition.get("labelKo"):
                raise EnforcementOntologyError(f"rule label drift for {code}")
            if rule.get("statuteArticle") != definition.get("legalBasis", {}).get("article"):
                raise EnforcementOntologyError(f"rule statute drift for {code}")
            observed.add(code)

    missing = deterministic_violation_codes(ontology) - observed
    if missing:
        raise EnforcementOntologyError(
            "ontology marks violations deterministic but no legal rule exists: " + ", ".join(sorted(missing))
        )
