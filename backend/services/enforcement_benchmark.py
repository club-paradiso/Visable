"""Deterministic benchmark scoring for Enforcement Intelligence v3.

The benchmark deliberately separates natural-language extraction, the pure
legal rule engine, abstention behavior, and safety invariants. AI outcome
quality remains out of scope until reviewed outcome ground truth exists.
"""

from __future__ import annotations

import json
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from math import ceil
from typing import Any, Dict, Iterable, Optional

from .enforcement_models import StructuredCase
from .enforcement_rules import calculate_legal_baseline
from .enforcement_service import extract_structured_case

_EXPECTED_FACT_FIELDS = {
    "statusOfStay": "status_of_stay",
    "violationCode": "violation_code",
    "durationDays": "duration_days",
    "priorViolations": "prior_violations",
    "voluntaryDisclosure": "voluntary_disclosure",
    "violationStartDate": "violation_start_date",
    "violationEndDate": "violation_end_date",
    "authorizationObtained": "authorization_obtained",
    "workplaceChangeAuthorized": "workplace_change_authorized",
}
_DATE_FIELDS = {"violationStartDate", "violationEndDate"}
_BASELINE_EXPECTATION_KEYS = {
    "deterministicBaselineStatus",
    "baselineAmountKrw",
    "legalRangeMinimumKrw",
    "legalRangeMaximumKrw",
    "boundaryAssumptionExpected",
}
_ALLOWED_DATASET_SCHEMAS = {"1.0.0", "2.0.0"}
_ALLOWED_CASE_KINDS = {"narrative", "structured"}


class EnforcementBenchmarkError(ValueError):
    """Raised when a checked-in benchmark dataset violates its contract."""


@dataclass(frozen=True)
class BenchmarkCaseScore:
    case_id: str
    suite: str
    kind: str
    exact_match: bool
    expected_abstain: Optional[bool]
    actual_abstain: Optional[bool]
    fact_correct: int
    fact_total: int
    violation_correct: bool
    violation_evaluated: bool
    baseline_correct: bool
    baseline_evaluated: bool
    invariant_correct: int
    invariant_total: int
    latency_ms: Optional[float]
    errors: tuple[str, ...]


def validate_benchmark_dataset(payload: Any) -> Dict[str, Any]:
    """Validate benchmark metadata and provenance without judging legal truth.

    Schema 1 is retained for the original ten-case seed. Schema 2 requires
    explicit case kind, suite, and provenance so future corpus growth cannot
    silently turn generated examples into supposed ground truth.
    """

    if not isinstance(payload, dict):
        raise EnforcementBenchmarkError("benchmark dataset must be an object")
    schema = payload.get("schemaVersion")
    if schema not in _ALLOWED_DATASET_SCHEMAS:
        raise EnforcementBenchmarkError("unsupported enforcement benchmark schema")
    if not isinstance(payload.get("datasetVersion"), str) or not payload["datasetVersion"].strip():
        raise EnforcementBenchmarkError("benchmark datasetVersion is required")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise EnforcementBenchmarkError("benchmark dataset must contain cases")

    seen_ids: set[str] = set()
    for row in cases:
        if not isinstance(row, dict):
            raise EnforcementBenchmarkError("benchmark case must be an object")
        case_id = row.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise EnforcementBenchmarkError("benchmark case id is required")
        if case_id in seen_ids:
            raise EnforcementBenchmarkError(f"duplicate benchmark case id: {case_id}")
        seen_ids.add(case_id)

        if schema == "2.0.0":
            kind = row.get("kind")
            if kind not in _ALLOWED_CASE_KINDS:
                raise EnforcementBenchmarkError(f"invalid benchmark case kind for {case_id}")
            suite = row.get("suite")
            if not isinstance(suite, str) or not suite.strip():
                raise EnforcementBenchmarkError(f"benchmark suite is required for {case_id}")
            provenance = row.get("provenance")
            if not isinstance(provenance, dict):
                raise EnforcementBenchmarkError(f"benchmark provenance is required for {case_id}")
            for field in ("sourceFile", "sourceTest"):
                if not isinstance(provenance.get(field), str) or not provenance[field].strip():
                    raise EnforcementBenchmarkError(f"benchmark provenance.{field} is required for {case_id}")
            if kind == "narrative" and not isinstance(row.get("text"), str):
                raise EnforcementBenchmarkError(f"narrative text is required for {case_id}")
            if kind == "structured" and not isinstance(row.get("caseData"), dict):
                raise EnforcementBenchmarkError(f"structured caseData is required for {case_id}")

        expected = row.get("expected")
        if not isinstance(expected, dict) or not expected:
            raise EnforcementBenchmarkError(f"benchmark expected assertions are required for {case_id}")

    return deepcopy(payload)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _normalize_expected_value(field: str, value: Any) -> Any:
    if field in _DATE_FIELDS and isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _row_assessment_date(row: Dict[str, Any], default: date) -> date:
    raw = row.get("assessmentDate")
    if raw:
        return date.fromisoformat(str(raw))
    return default


def _provider_for_row(row: Dict[str, Any]):
    if "providerPayload" in row:
        payload = deepcopy(row["providerPayload"])

        async def fixed_provider(_prompt: str):
            return deepcopy(payload)

        return fixed_provider

    if row.get("providerFailure"):
        message = str(row["providerFailure"])

        async def broken_provider(_prompt: str):
            raise RuntimeError(message)

        return broken_provider

    return None


def _check_collection_assertions(case: StructuredCase, expected: Dict[str, Any], errors: list[str]) -> tuple[int, int]:
    correct = 0
    total = 0

    if "violationCandidates" in expected:
        total += 1
        wanted = list(expected["violationCandidates"])
        if case.violation_candidates == wanted:
            correct += 1
        else:
            errors.append(f"violationCandidates: expected {wanted!r}, got {case.violation_candidates!r}")

    if "violationCandidatesSet" in expected:
        total += 1
        wanted = set(expected["violationCandidatesSet"])
        actual = set(case.violation_candidates)
        if actual == wanted:
            correct += 1
        else:
            errors.append(f"violationCandidatesSet: expected {sorted(wanted)!r}, got {sorted(actual)!r}")

    if "minimumViolationCandidates" in expected:
        total += 1
        minimum = int(expected["minimumViolationCandidates"])
        if len(case.violation_candidates) >= minimum:
            correct += 1
        else:
            errors.append(
                f"minimumViolationCandidates: expected >= {minimum}, got {len(case.violation_candidates)}"
            )

    for key, values, actual_values in (
        ("requiredUnknownFacts", expected.get("requiredUnknownFacts"), case.unknown_facts),
        ("requiredWarningSubstrings", expected.get("requiredWarningSubstrings"), case.extraction_warnings),
    ):
        if values is None:
            continue
        for wanted in values:
            total += 1
            if key == "requiredUnknownFacts":
                matched = wanted in actual_values
            else:
                matched = any(str(wanted) in item for item in actual_values)
            if matched:
                correct += 1
            else:
                errors.append(f"{key}: missing {wanted!r}")

    if "minExtractionWarnings" in expected:
        total += 1
        minimum = int(expected["minExtractionWarnings"])
        if len(case.extraction_warnings) >= minimum:
            correct += 1
        else:
            errors.append(f"minExtractionWarnings: expected >= {minimum}, got {len(case.extraction_warnings)}")

    if "forbiddenPublicSubstrings" in expected:
        public_text = json.dumps(case.public_dict(), ensure_ascii=False, sort_keys=True)
        for forbidden in expected["forbiddenPublicSubstrings"]:
            total += 1
            if str(forbidden) not in public_text:
                correct += 1
            else:
                errors.append(f"forbiddenPublicSubstrings: leaked {forbidden!r}")

    return correct, total


async def score_benchmark_case(row: Dict[str, Any], *, assessment_date: date) -> BenchmarkCaseScore:
    expected = row.get("expected") or {}
    case_id = str(row.get("id") or "unnamed")
    suite = str(row.get("suite") or "seed")
    kind = str(row.get("kind") or "narrative")
    latency_ms: Optional[float] = None

    if kind == "structured":
        case_data = deepcopy(row.get("caseData") or {})
        if "assessmentDate" not in case_data and "assessment_date" not in case_data:
            case_data["assessmentDate"] = _row_assessment_date(row, assessment_date).isoformat()
        case = StructuredCase(**case_data)
    else:
        started = time.perf_counter()
        case = await extract_structured_case(
            str(row.get("text") or ""),
            provider=_provider_for_row(row),
            assessment_date=_row_assessment_date(row, assessment_date),
        )
        latency_ms = (time.perf_counter() - started) * 1000.0

    baseline = calculate_legal_baseline(case)
    errors: list[str] = []
    fact_correct = 0
    fact_total = 0
    violation_evaluated = "violationCode" in expected
    violation_correct = True

    for public_name, attr_name in _EXPECTED_FACT_FIELDS.items():
        if public_name not in expected:
            continue
        fact_total += 1
        expected_value = _normalize_expected_value(public_name, expected[public_name])
        actual_value = getattr(case, attr_name)
        if actual_value == expected_value:
            fact_correct += 1
        else:
            errors.append(f"{public_name}: expected {expected_value!r}, got {actual_value!r}")
        if public_name == "violationCode":
            violation_correct = actual_value == expected_value

    invariant_correct, invariant_total = _check_collection_assertions(case, expected, errors)

    baseline_evaluated = any(key in expected for key in _BASELINE_EXPECTATION_KEYS)
    baseline_correct = True
    expected_status = expected.get("deterministicBaselineStatus")
    if expected_status is not None and baseline.status != expected_status:
        baseline_correct = False
        errors.append(f"baseline.status: expected {expected_status!r}, got {baseline.status!r}")

    if "baselineAmountKrw" in expected:
        expected_amount = expected["baselineAmountKrw"]
        if baseline.status != "AVAILABLE" or baseline.baseline_amount_krw != expected_amount:
            baseline_correct = False
            errors.append(
                f"baseline.amount: expected {expected_amount!r}, got "
                f"{baseline.baseline_amount_krw!r} ({baseline.status})"
            )

    if "legalRangeMinimumKrw" in expected:
        actual = baseline.legally_adjustable_range.minimum_krw if baseline.legally_adjustable_range else None
        if actual != expected["legalRangeMinimumKrw"]:
            baseline_correct = False
            errors.append(f"baseline.range.minimum: expected {expected['legalRangeMinimumKrw']!r}, got {actual!r}")

    if "legalRangeMaximumKrw" in expected:
        actual = baseline.legally_adjustable_range.maximum_krw if baseline.legally_adjustable_range else None
        if actual != expected["legalRangeMaximumKrw"]:
            baseline_correct = False
            errors.append(f"baseline.range.maximum: expected {expected['legalRangeMaximumKrw']!r}, got {actual!r}")

    if expected.get("boundaryAssumptionExpected") and not baseline.assumptions:
        baseline_correct = False
        errors.append("baseline.assumptions: expected at least one disclosed assumption")

    expected_abstain: Optional[bool] = None
    actual_abstain: Optional[bool] = None
    if "classificationState" in expected:
        expected_abstain = expected.get("classificationState") == "AMBIGUOUS"
        actual_abstain = case.violation_code is None
        if expected_abstain != actual_abstain:
            errors.append(f"abstention: expected {expected_abstain}, got {actual_abstain}")

    return BenchmarkCaseScore(
        case_id=case_id,
        suite=suite,
        kind=kind,
        exact_match=not errors,
        expected_abstain=expected_abstain,
        actual_abstain=actual_abstain,
        fact_correct=fact_correct,
        fact_total=fact_total,
        violation_correct=violation_correct,
        violation_evaluated=violation_evaluated,
        baseline_correct=baseline_correct,
        baseline_evaluated=baseline_evaluated,
        invariant_correct=invariant_correct,
        invariant_total=invariant_total,
        latency_ms=latency_ms,
        errors=tuple(errors),
    )


def _safe_accuracy(correct: int, total: int) -> float:
    return (correct / total) if total else 1.0


def _suite_report(items: list[BenchmarkCaseScore]) -> Dict[str, Any]:
    return {
        "cases": len(items),
        "exactCaseAccuracy": _safe_accuracy(sum(item.exact_match for item in items), len(items)),
        "failures": [item.case_id for item in items if not item.exact_match],
    }


async def run_benchmark(
    rows: Iterable[Dict[str, Any]],
    *,
    assessment_date: date,
) -> Dict[str, Any]:
    rows_list = list(rows)
    results = [await score_benchmark_case(row, assessment_date=assessment_date) for row in rows_list]
    total = len(results)
    total_fact_checks = sum(item.fact_total for item in results)
    correct_fact_checks = sum(item.fact_correct for item in results)
    violation_items = [item for item in results if item.violation_evaluated]
    baseline_items = [item for item in results if item.baseline_evaluated]
    abstention_items = [item for item in results if item.expected_abstain is not None]
    expected_abstentions = sum(item.expected_abstain is True for item in abstention_items)
    predicted_abstentions = sum(item.actual_abstain is True for item in abstention_items)
    abstention_true_positive = sum(
        item.expected_abstain is True and item.actual_abstain is True for item in abstention_items
    )
    abstention_false_positive = sum(
        item.expected_abstain is False and item.actual_abstain is True for item in abstention_items
    )
    abstention_false_negative = sum(
        item.expected_abstain is True and item.actual_abstain is False for item in abstention_items
    )
    precision_denominator = abstention_true_positive + abstention_false_positive
    recall_denominator = abstention_true_positive + abstention_false_negative
    latencies = [item.latency_ms for item in results if item.latency_ms is not None]
    invariant_total = sum(item.invariant_total for item in results)
    invariant_correct = sum(item.invariant_correct for item in results)

    suites: Dict[str, list[BenchmarkCaseScore]] = {}
    for item in results:
        suites.setdefault(item.suite, []).append(item)

    provenance_count = sum(isinstance(row.get("provenance"), dict) for row in rows_list)
    kind_counts: Dict[str, int] = {}
    for item in results:
        kind_counts[item.kind] = kind_counts.get(item.kind, 0) + 1

    return {
        "cases": total,
        "exactCaseAccuracy": _safe_accuracy(sum(item.exact_match for item in results), total),
        "materialFactAccuracy": _safe_accuracy(correct_fact_checks, total_fact_checks),
        "violationCodeAccuracy": _safe_accuracy(
            sum(item.violation_correct for item in violation_items), len(violation_items)
        ),
        "deterministicBaselineAccuracy": _safe_accuracy(
            sum(item.baseline_correct for item in baseline_items), len(baseline_items)
        ),
        "securityInvariantAccuracy": _safe_accuracy(invariant_correct, invariant_total),
        "abstention": {
            "evaluated": len(abstention_items),
            "expected": expected_abstentions,
            "predicted": predicted_abstentions,
            "precision": (abstention_true_positive / precision_denominator) if precision_denominator else 1.0,
            "recall": (abstention_true_positive / recall_denominator) if recall_denominator else 1.0,
        },
        "latencyMs": {
            "samples": len(latencies),
            "p50": round(_percentile(latencies, 0.50), 3),
            "p95": round(_percentile(latencies, 0.95), 3),
            "max": round(max(latencies), 3) if latencies else 0.0,
        },
        "coverage": {
            "materialFactChecks": total_fact_checks,
            "violationCodeCases": len(violation_items),
            "deterministicBaselineCases": len(baseline_items),
            "securityInvariantChecks": invariant_total,
            "provenanceCoverage": _safe_accuracy(provenance_count, total),
            "kindCounts": kind_counts,
        },
        "bySuite": {name: _suite_report(items) for name, items in sorted(suites.items())},
        "failures": [
            {"id": item.case_id, "suite": item.suite, "kind": item.kind, "errors": list(item.errors)}
            for item in results
            if not item.exact_match
        ],
    }
