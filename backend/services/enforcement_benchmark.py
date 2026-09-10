"""Deterministic benchmark scoring for Enforcement Intelligence v3.

This module scores extraction and legal-baseline behavior only. It deliberately
excludes AI outcome quality until reviewed outcome ground truth exists.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from math import ceil
from typing import Any, Dict, Iterable, Optional

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
}
_DATE_FIELDS = {"violationStartDate", "violationEndDate"}


@dataclass(frozen=True)
class BenchmarkCaseScore:
    case_id: str
    exact_match: bool
    expected_abstain: bool
    actual_abstain: bool
    fact_correct: int
    fact_total: int
    violation_correct: bool
    baseline_correct: bool
    latency_ms: float
    errors: tuple[str, ...]


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


async def score_benchmark_case(row: Dict[str, Any], *, assessment_date: date) -> BenchmarkCaseScore:
    expected = row.get("expected") or {}
    case_id = str(row.get("id") or "unnamed")
    started = time.perf_counter()
    case = await extract_structured_case(str(row.get("text") or ""), assessment_date=assessment_date)
    latency_ms = (time.perf_counter() - started) * 1000.0
    baseline = calculate_legal_baseline(case)

    errors: list[str] = []
    fact_correct = 0
    fact_total = 0
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

    if expected.get("boundaryAssumptionExpected") and not baseline.assumptions:
        baseline_correct = False
        errors.append("baseline.assumptions: expected at least one disclosed assumption")

    expected_abstain = expected.get("classificationState") == "AMBIGUOUS"
    actual_abstain = case.violation_code is None
    if expected_abstain != actual_abstain:
        errors.append(f"abstention: expected {expected_abstain}, got {actual_abstain}")

    return BenchmarkCaseScore(
        case_id=case_id,
        exact_match=not errors,
        expected_abstain=expected_abstain,
        actual_abstain=actual_abstain,
        fact_correct=fact_correct,
        fact_total=fact_total,
        violation_correct=violation_correct,
        baseline_correct=baseline_correct,
        latency_ms=latency_ms,
        errors=tuple(errors),
    )


async def run_benchmark(
    rows: Iterable[Dict[str, Any]],
    *,
    assessment_date: date,
) -> Dict[str, Any]:
    results = [await score_benchmark_case(row, assessment_date=assessment_date) for row in rows]
    total = len(results)
    total_fact_checks = sum(item.fact_total for item in results)
    correct_fact_checks = sum(item.fact_correct for item in results)
    expected_abstentions = sum(item.expected_abstain for item in results)
    predicted_abstentions = sum(item.actual_abstain for item in results)
    abstention_true_positive = sum(item.expected_abstain and item.actual_abstain for item in results)
    abstention_false_positive = sum((not item.expected_abstain) and item.actual_abstain for item in results)
    abstention_false_negative = sum(item.expected_abstain and (not item.actual_abstain) for item in results)
    precision_denominator = abstention_true_positive + abstention_false_positive
    recall_denominator = abstention_true_positive + abstention_false_negative
    latencies = [item.latency_ms for item in results]

    return {
        "cases": total,
        "exactCaseAccuracy": (sum(item.exact_match for item in results) / total) if total else 0.0,
        "materialFactAccuracy": (correct_fact_checks / total_fact_checks) if total_fact_checks else 0.0,
        "violationCodeAccuracy": (sum(item.violation_correct for item in results) / total) if total else 0.0,
        "deterministicBaselineAccuracy": (sum(item.baseline_correct for item in results) / total) if total else 0.0,
        "abstention": {
            "expected": expected_abstentions,
            "predicted": predicted_abstentions,
            "precision": (abstention_true_positive / precision_denominator) if precision_denominator else 1.0,
            "recall": (abstention_true_positive / recall_denominator) if recall_denominator else 1.0,
        },
        "latencyMs": {
            "p50": round(_percentile(latencies, 0.50), 3),
            "p95": round(_percentile(latencies, 0.95), 3),
            "max": round(max(latencies), 3) if latencies else 0.0,
        },
        "failures": [
            {"id": item.case_id, "errors": list(item.errors)}
            for item in results
            if not item.exact_match
        ],
    }
