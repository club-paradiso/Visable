"""Go / no-go gates. Every gate is a PROJECT HYPOTHESIS, not a validated threshold.

Why they are written down before any result exists: a threshold chosen after
seeing the scores measures the author, not the system. The gates below are
conservative on purpose (zero tolerance for the errors that would mislead a
user about the law) and are evaluated only on the decision splits (``test``
and ``adversarial_holdout``), never on ``dev``, which is tuned on.

Rules that keep a gate honest:

* a hard gate with an empty denominator is ``insufficient_evidence``, never a
  pass: "zero false absences out of zero unavailable items" proves nothing;
* a gate on a task the baseline does not answer, or on a field it cannot
  emit (B1 has no fine procedure), is ``not_applicable``;
* labels that no person has verified cap the decision at ``PROVISIONAL_GO``:
  any scored item on the decision splits whose label is not ``human_verified``
  (critical or not) is enough.

Definitions and rationale: 12-evaluation-methodology.md §7.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence

DECISION_SPLITS = ("test", "adversarial_holdout")

PASS = "pass"
FAIL = "fail"
INSUFFICIENT = "insufficient_evidence"
NOT_APPLICABLE = "not_applicable"

GO = "GO"
PROVISIONAL_GO = "PROVISIONAL_GO"
HOLD = "HOLD"
NO_GO = "NO_GO"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class Gate:
    id: str
    hard: bool
    metric: str            # headline metric name, or a special source ("_errors", "_critical")
    comparator: str        # "zero" | ">=" | "<="
    threshold: float
    description: str


GATES: Sequence[Gate] = (
    Gate("HG-1", True, "citation.false_absence_declarations", "zero", 0,
         "No source_not_found / citation_not_found where the label says the source could not be checked."),
    Gate("HG-2", True, "citation.accepted_future_not_yet_effective", "zero", 0,
         "No claim relying on a promulgated-but-not-yet-effective version is accepted as verified."),
    Gate("HG-3", True, "citation.accepted_wrong_version", "zero", 0,
         "No claim relying on a later amendment applied to an earlier event is accepted."),
    Gate("HG-4", True, "citation.accepted_source_outdated", "zero", 0,
         "No claim relying on a superseded version is accepted."),
    Gate("HG-5", True, "citation.unsupported_claim_acceptance_rate", "zero", 0,
         "No claim labelled failed / human_review_required is reported verified or verified_partial."),
    Gate("HG-6", True, "temporal.forbidden_warning_violations", "zero", 0,
         "No forbidden temporal warning (e.g. a false 'no future version' state) is emitted."),
    Gate("HG-7", True, "classification.procedure_scope_violations", "zero", 0,
         "No visa-issuance procedure is predicted for a stay question, or the reverse."),
    Gate("HG-8", True, "_critical", "zero", 0,
         "No critical legal error (critical item wrong, false absence, accepted wrong/future version)."),
    Gate("HG-9", True, "_errors", "zero", 0,
         "No crash on an applicable item: a crash is never scored, so it must never pass silently."),
    Gate("HG-10", True, "classification.hierarchy_violations", "zero", 0,
         "No parent code stands in for an expected subcode, and no parent is written into the subcode field "
         "(doc 13 G1-safety; CLE-4)."),
    Gate("SG-1", False, "citation.overall_status_accuracy", ">=", 0.95,
         "Overall verification status matches the label."),
    Gate("SG-2", False, "citation.wrong_version_detection_rate", ">=", 0.90,
         "The exact L2 code is reported for wrong / future / outdated versions."),
    Gate("SG-3", False, "temporal.candidate_exact_match", ">=", 0.95,
         "Candidate version keys match the label exactly, in order."),
    Gate("SG-4", False, "temporal.warning_recall", ">=", 0.95,
         "Required temporal warnings are present (micro recall)."),
    Gate("SG-5", False, "classification.status_exact_accuracy", ">=", 0.90,
         "Parent status code matches the label."),
    Gate("SG-6", False, "classification.subcode_accuracy_subcode_expected", ">=", 0.90,
         "Exact subcode on items whose label has a subcode (a parent answer is wrong)."),
    Gate("SG-7", False, "classification.procedure_fine_accuracy", ">=", 0.85,
         "Fine (16-id) procedure matches the label; the D1 target of doc 13."),
    Gate("SG-8", False, "model.structured_output_valid_rate", ">=", 1.0,
         "Every model answer is exactly the structured-output contract (doc 13 G4)."),
)

#: Timing depends on the machine, so it is checked beside the decision, never
#: inside it: the correctness decision must be reproducible from the same
#: inputs (it is part of the scoring digest), and a timing row cannot be.
PERFORMANCE_GATES: Sequence[Gate] = (
    Gate("PG-1", False, "performance.latency_p95_ms", "<=", 3500.0,
         "p95 per-item latency at most half of the 7 s Quick Answer timeout (doc 13 G6)."),
)


def _evaluate(gate: Gate, headline: Mapping[str, Mapping[str, Any]], extras: Mapping[str, Any]) -> Dict[str, Any]:
    if gate.metric == "_errors":
        numerator, denominator = extras["errors"], extras["applicable"]
    elif gate.metric == "_critical":
        numerator, denominator = extras["critical"], extras["scored"]
    else:
        entry = headline.get(gate.metric)
        if entry is None or entry.get("baseline_cannot_emit"):
            return {"status": NOT_APPLICABLE, "numerator": None, "denominator": None, "value": None}
        numerator, denominator = entry["numerator"], entry["denominator"]
        if gate.comparator in (">=", "<="):
            value = entry["value"]
            if not denominator or value is None:
                return {"status": INSUFFICIENT, "numerator": numerator, "denominator": denominator, "value": value}
            met = value >= gate.threshold if gate.comparator == ">=" else value <= gate.threshold
            return {"status": PASS if met else FAIL, "numerator": numerator, "denominator": denominator,
                    "value": value}
    if not denominator:
        return {"status": INSUFFICIENT, "numerator": numerator, "denominator": denominator, "value": None}
    return {"status": PASS if numerator == 0 else FAIL, "numerator": numerator, "denominator": denominator,
            "value": numerator}


def evaluate_gates(headline: Mapping[str, Mapping[str, Any]], extras: Mapping[str, Any],
                   splits_present: Sequence[str]) -> Dict[str, Any]:
    """Gate table and decision for one baseline over the decision splits it was run on."""
    decision_splits = [s for s in DECISION_SPLITS if s in splits_present]
    rows = _rows(GATES, headline, extras, decision_splits)
    performance_rows = _rows(PERFORMANCE_GATES, headline, extras, decision_splits)
    critical_unverified = _unverified(extras.get("critical_label_review") or {})
    all_unverified = _unverified(extras.get("label_review") or {})
    return {
        "decision_splits": decision_splits,
        "gates": rows,
        "critical_labels_unverified": critical_unverified,
        "labels_unverified": all_unverified,
        "decision": decide(rows, decision_splits, max(critical_unverified, all_unverified)),
        "performance_gates": performance_rows,
        "hypothesis_notice": "Gates are project hypotheses (12-evaluation-methodology.md §7), not validated thresholds.",
    }


def _rows(gates: Sequence[Gate], headline: Mapping[str, Mapping[str, Any]], extras: Mapping[str, Any],
          decision_splits: Sequence[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for gate in gates:
        result = _evaluate(gate, headline, extras) if decision_splits else {
            "status": INSUFFICIENT, "numerator": None, "denominator": None, "value": None}
        rows.append({"id": gate.id, "hard": gate.hard, "metric": gate.metric, "comparator": gate.comparator,
                     "threshold": gate.threshold, "description": gate.description, **result})
    return rows


def _unverified(label_counts: Mapping[str, int]) -> int:
    return sum(count for status, count in label_counts.items() if status != "human_verified")


def decide(rows: Sequence[Mapping[str, Any]], decision_splits: Sequence[str], unverified_labels: int) -> str:
    if not decision_splits:
        return INSUFFICIENT_EVIDENCE
    hard = [r for r in rows if r["hard"] and r["status"] != NOT_APPLICABLE]
    soft = [r for r in rows if not r["hard"] and r["status"] != NOT_APPLICABLE]
    if any(r["status"] == FAIL for r in hard):
        return NO_GO
    if not hard or any(r["status"] == INSUFFICIENT for r in hard):
        return INSUFFICIENT_EVIDENCE
    if any(r["status"] != PASS for r in soft):
        return HOLD
    return PROVISIONAL_GO if unverified_labels else GO
