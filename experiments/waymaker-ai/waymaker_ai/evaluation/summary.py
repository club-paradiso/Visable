"""Headline metrics, critical legal errors and performance summaries.

Why a separate layer over ``metrics.aggregate``: the aggregate keeps every
metric with its own counts; the headline picks the ones the methodology names
(12-evaluation-methodology.md §3) and states each as numerator / denominator /
not-scorable, so a reader never sees a rate without its base.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from waymaker_ai.contracts import VerificationLayer

#: Flags that make an item a critical legal error regardless of its label.
CRITICAL_FLAGS: Dict[str, str] = {
    "false_absence_declaration": "false_absence_declaration",
    "accepted_future_not_yet_effective": "accepted_future_not_yet_effective",
    "accepted_wrong_version": "accepted_wrong_version",
    "accepted_source_outdated": "accepted_source_outdated",
}

#: Flags reported next to the critical count (CLE-3 scope mixing, CLE-4 hierarchy).
VIOLATION_FLAGS: Sequence[str] = (
    "procedure_scope_mixed",
    "parent_fallback",
    "parent_in_subcode_field",
    "code_from_non_code_token",
    "unsupported_claim_accepted",
    "forbidden_code_emitted",
    "forbidden_warning_emitted",
    "required_warning_missing",
    "failed_to_abstain",
    "forbidden_assertion_made",
)


#: z for a two-sided 95% interval.
_Z95 = 1.959964


def wilson_interval(successes: int, trials: int) -> Optional[List[float]]:
    """95% Wilson score interval for a proportion, or None without trials.

    Wilson rather than the normal approximation because the benchmark's
    denominators are small and many rates sit at 0 or 1, where the normal
    interval collapses to a width of zero.
    """
    if not trials:
        return None
    p = successes / trials
    z2 = _Z95 * _Z95
    centre = (p + z2 / (2 * trials)) / (1 + z2 / trials)
    half = _Z95 * math.sqrt(p * (1 - p) / trials + z2 / (4 * trials * trials)) / (1 + z2 / trials)
    return [round(max(0.0, centre - half), 6), round(min(1.0, centre + half), 6)]


def _entry(kind: str, numerator: Optional[int], denominator: int, not_scorable: int,
           value: Optional[float] = None) -> Dict[str, Any]:
    if value is None and numerator is not None and kind in ("accuracy", "rate"):
        value = round(numerator / denominator, 6) if denominator else None
    entry = {"kind": kind, "value": value, "numerator": numerator, "denominator": denominator,
             "not_scorable": not_scorable}
    if kind in ("accuracy", "rate", "precision", "recall") and numerator is not None:
        entry["ci95"] = wilson_interval(numerator, denominator)
    return entry


#: Not-scorable reasons that mean "this baseline cannot produce the field at all".
CANNOT_EMIT_REASONS = frozenset({
    "not_scorable:not_emitted", "not_scorable:baseline_emits_coarse_only", "not_scorable:roles_not_emitted",
})


def _with_emission(entry: Dict[str, Any], tally: Mapping[str, Any]) -> Dict[str, Any]:
    """Mark an entry whose every item was not scorable because the baseline cannot emit the field.

    A gate on such an entry is ``not_applicable`` (the baseline was never asked
    to do it), unlike an empty denominator for any other reason, which is
    ``insufficient_evidence``.
    """
    reasons = set((tally.get("reasons") or {}))
    entry["baseline_cannot_emit"] = bool(
        tally["denominator"] == 0 and tally["not_scorable"] and reasons and reasons <= CANNOT_EMIT_REASONS)
    return entry


def _accuracy(agg: Mapping[str, Any], name: str) -> Optional[Dict[str, Any]]:
    tally = (agg.get("metrics") or {}).get(name)
    if tally is None:
        return None
    return _with_emission(_entry("accuracy", tally["correct"], tally["denominator"], tally["not_scorable"]), tally)


def _wrong_count(agg: Mapping[str, Any], name: str, kind: str = "count") -> Optional[Dict[str, Any]]:
    """Wrong outcomes of a 'must not happen' metric: the count of violations over its base."""
    tally = (agg.get("metrics") or {}).get(name)
    if tally is None:
        return None
    entry = _entry("rate" if kind == "rate" else "count", tally["wrong"], tally["denominator"], tally["not_scorable"])
    return _with_emission(entry, tally)


def _pr(agg: Mapping[str, Any], name: str, which: str) -> Optional[Dict[str, Any]]:
    counts = (agg.get("precision_recall") or {}).get(name)
    if counts is None:
        return None
    if which == "precision":
        denominator = counts["tp"] + counts["fp"]
    else:
        denominator = counts["tp"] + counts["fn"]
    return _entry(which, counts["tp"], denominator, 0, counts[which])


def headline(by_task: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """The named metrics for one baseline and one split. Absent tasks give no entries."""
    out: Dict[str, Optional[Dict[str, Any]]] = {}
    cls = by_task.get("status_procedure_classification")
    if cls:
        out["classification.status_exact_accuracy"] = _accuracy(cls, "status_exact")
        out["classification.subcode_exact_accuracy"] = _accuracy(cls, "subcode_exact")
        out["classification.subcode_accuracy_subcode_expected"] = _accuracy(cls, "subcode_expected_present")
        out["classification.subcode_accuracy_no_subcode_expected"] = _accuracy(cls, "subcode_expected_absent")
        out["classification.procedure_fine_accuracy"] = _accuracy(cls, "procedure_fine")
        out["classification.procedure_coarse_accuracy"] = _accuracy(cls, "procedure_coarse")
        out["classification.current_status_accuracy"] = _accuracy(cls, "current_status_exact")
        out["classification.target_status_accuracy"] = _accuracy(cls, "target_status_exact")
        out["classification.clarification_precision"] = _pr(cls, "clarification", "precision")
        out["classification.clarification_recall"] = _pr(cls, "clarification", "recall")
        out["classification.non_code_token_respected"] = _accuracy(cls, "not_status_token_respected")
        out["classification.procedure_scope_violations"] = _wrong_count(cls, "procedure_scope_respected")
        out["classification.hierarchy_violations"] = _hierarchy_violations(cls)
    ent = by_task.get("entity_date_extraction")
    if ent:
        out["dates.value_precision"] = _pr(ent, "dates_value_only", "precision")
        out["dates.value_recall"] = _pr(ent, "dates_value_only", "recall")
        out["dates.value_role_precision"] = _pr(ent, "dates_value_role", "precision")
        out["dates.value_role_recall"] = _pr(ent, "dates_value_role", "recall")
        out["dates.exact_accuracy"] = _accuracy(ent, "dates_exact")
        out["dates.value_exact_accuracy"] = _accuracy(ent, "dates_value_exact")
    cit = by_task.get("citation_verification")
    if cit:
        out["citation.overall_status_accuracy"] = _accuracy(cit, "overall_status")
        for layer in VerificationLayer:
            entry = _accuracy(cit, f"layer_code:{layer.value}")
            if entry is not None:
                out[f"citation.layer_agreement.L{layer.order}_{layer.value}"] = entry
        out["citation.false_absence_declarations"] = _wrong_count(cit, "false_absence")
        out["citation.unlabelled_absence_codes"] = _wrong_count(cit, "unsupported_absence")
        out["citation.wrong_version_detection_rate"] = _accuracy(cit, "wrong_version_detected")
        out["citation.accepted_version_failures"] = _wrong_count(cit, "version_failure_rejected")
        out["citation.accepted_future_not_yet_effective"] = _wrong_count(
            cit, "version_failure_rejected:future_not_yet_effective")
        out["citation.accepted_wrong_version"] = _wrong_count(cit, "version_failure_rejected:wrong_version")
        out["citation.accepted_source_outdated"] = _wrong_count(cit, "version_failure_rejected:source_outdated")
        out["citation.unsupported_claim_acceptance_rate"] = _wrong_count(cit, "unsupported_claim_rejected", "rate")
        out["citation.forbidden_code_violations"] = _wrong_count(cit, "forbidden_codes_absent")
        out["citation.highest_layer_within_bound"] = _accuracy(cit, "highest_layer_within_bound")
        out["citation.injection_flag_accuracy"] = _accuracy(cit, "injection_flagged")
    tmp = by_task.get("temporal_version_selection")
    if tmp:
        out["temporal.candidate_exact_match"] = _accuracy(tmp, "candidates_exact")
        out["temporal.warning_recall"] = _pr(tmp, "warning_recall", "recall")
        out["temporal.all_required_warnings_present"] = _accuracy(tmp, "warnings_all_present")
        out["temporal.forbidden_warning_violations"] = _wrong_count(tmp, "forbidden_warnings_absent")
        out["temporal.candidate_only_determination"] = _accuracy(tmp, "determination_candidate_only")
    abst = by_task.get("abstention")
    if abst:
        out["abstention.withhold_accuracy"] = _accuracy(abst, "withhold_correct")
        out["abstention.withhold_precision"] = _pr(abst, "withhold", "precision")
        out["abstention.withhold_recall"] = _pr(abst, "withhold", "recall")
        out["abstention.required_issue_coverage"] = _pr(abst, "required_issue_coverage", "recall")
        out["abstention.forbidden_assertion_violations"] = _wrong_count(abst, "forbidden_assertions_absent")
    out["model.structured_output_valid_rate"] = _summed_accuracy(by_task, "structured_output_valid")
    return {name: entry for name, entry in sorted(out.items()) if entry is not None}


def _hierarchy_violations(agg: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """Items where a parent stood in for a subcode (CLE-4): parent fallback or a parent in the subcode field."""
    tally = (agg.get("metrics") or {}).get("subcode_exact")
    if tally is None:
        return None
    reasons = tally.get("reasons") or {}
    count = reasons.get("wrong:parent_fallback", 0) + reasons.get("wrong:parent_in_subcode_field", 0)
    return _with_emission(_entry("count", count, tally["denominator"], tally["not_scorable"]), tally)


def _summed_accuracy(by_task: Mapping[str, Mapping[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """One accuracy over every task that carries metric ``name``."""
    tallies = [agg["metrics"][name] for agg in by_task.values() if name in (agg.get("metrics") or {})]
    if not tallies:
        return None
    correct = sum(t["correct"] for t in tallies)
    return _entry("accuracy", correct, sum(t["denominator"] for t in tallies), sum(t["not_scorable"] for t in tallies))


# ---------------------------------------------------------------------------
# Critical legal errors
# ---------------------------------------------------------------------------
def critical_categories(example: Mapping[str, Any], flags: Iterable[str], primary_wrong: Optional[bool]) -> List[str]:
    """Why one scored item is a critical legal error (empty when it is not)."""
    categories = []
    if example.get("critical") and primary_wrong:
        categories.append("critical_example_wrong")
    present = set(flags)
    categories.extend(category for flag, category in CRITICAL_FLAGS.items() if flag in present)
    return sorted(set(categories))


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
def _percentile(values: Sequence[float], q: float) -> Optional[float]:
    """Nearest-rank percentile (no interpolation, so a reported value was observed)."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered)))
    return ordered[rank - 1]


def performance(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Latency, upstream calls, memory and tokens over items that produced an answer."""
    latencies = [float(r["latency_ms"]) for r in records if r.get("latency_ms") is not None]
    calls = [int(r["upstream_calls"]) for r in records if r.get("upstream_calls") is not None]
    memory = [int(r["peak_memory_bytes"]) for r in records if r.get("peak_memory_bytes") is not None]
    kinds = sorted({str(r.get("memory_kind")) for r in records if r.get("peak_memory_bytes") is not None})
    tokens: Dict[str, int] = {}
    token_items = 0
    for record in records:
        if record.get("tokens"):
            token_items += 1
            for key, value in record["tokens"].items():
                tokens[key] = tokens.get(key, 0) + int(value)
    return {
        "latency_ms": {
            "n": len(latencies),
            "mean": round(sum(latencies) / len(latencies), 3) if latencies else None,
            "p50": _percentile(latencies, 0.5),
            "p95": _percentile(latencies, 0.95),
            "max": max(latencies) if latencies else None,
        },
        "upstream_calls": {
            "n": len(calls),
            "total": sum(calls) if calls else None,
            "mean": round(sum(calls) / len(calls), 3) if calls else None,
            "max": max(calls) if calls else None,
        },
        "peak_memory_bytes": {
            "n": len(memory),
            "p50": _percentile([float(m) for m in memory], 0.5),
            "max": max(memory) if memory else None,
            "kind": kinds,
        },
        "tokens": {"items": token_items, **dict(sorted(tokens.items()))} if token_items else None,
    }
