"""Per-task contract for benchmark examples.

``TASK_EXPECTED_KEYS`` is the part of the example schema a JSON Schema cannot
express cleanly: which ``expected`` keys each task needs. The validator, the
benchmark authors and the evaluation runner all read it from here.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Tuple

SCHEMA_VERSION = "waymaker-example/0.1"

SUITES: Tuple[str, ...] = ("classification", "legal_verification", "temporal", "abstention")

TASK_SUITE: Dict[str, str] = {
    "status_procedure_classification": "classification",
    "entity_date_extraction": "classification",
    "citation_verification": "legal_verification",
    "temporal_version_selection": "temporal",
    "abstention": "abstention",
}

#: task -> (required expected keys, optional expected keys)
TASK_EXPECTED_KEYS: Dict[str, Tuple[FrozenSet[str], FrozenSet[str]]] = {
    # status_code: parent code or null; subcode: exact subcode or null (never the
    # parent repeated); procedure: one of contracts.FINE_PROCEDURES or null.
    # current_status / target_status: for "from A to B" questions.
    # not_status_tokens: substrings that look like codes but are not (e.g. "a 3").
    "status_procedure_classification": (
        frozenset({"status_code", "subcode", "procedure"}),
        frozenset({"current_status", "target_status", "needs_clarification", "not_status_tokens"}),
    ),
    # dates: [{"value": "YYYY-MM-DD", "role": contracts.AnchorKind value}]
    "entity_date_extraction": (
        frozenset({"dates"}),
        frozenset({"status_codes"}),
    ),
    # overall: contracts.OverallStatus value; layer_codes: {layer value: code value}
    # forbidden_codes: codes that must not appear anywhere (e.g. source_not_found on a timeout).
    "citation_verification": (
        frozenset({"overall", "layer_codes"}),
        frozenset({"forbidden_codes", "max_highest_verified_layer", "injection_flagged"}),
    ),
    # candidate_version_keys: [[version_id, effective_date]] in preference order.
    # warnings: contracts.TemporalWarning values that must be present.
    "temporal_version_selection": (
        frozenset({"candidate_version_keys", "warnings"}),
        frozenset({"forbidden_warnings", "determination"}),
    ),
    # Scored on a structured model answer only (no deterministic baseline).
    "abstention": (
        frozenset({"must_withhold_conclusion", "required_issue_keys"}),
        frozenset({"forbidden_assertions"}),
    ),
}

ADVERSARIAL_CLASSES: Dict[str, str] = {
    "A": "wrong_law_substitution",
    "B": "correct_law_wrong_article",
    "C": "correct_article_wrong_content",
    "D": "current_vs_past_law",
    "E": "promulgated_not_effective",
    "F": "supplementary_provisions",
    "G": "renamed_or_repealed_statute",
    "H": "upstream_failure",
    "I": "subcode_confusion",
    "J": "manual_vs_statute",
    "K": "real_world_dates",
    "L": "representation",
    "M": "missing_legal_source",
    "N": "source_injection",
}
