"""Per-item scoring and aggregation.

Why exact comparisons only: every label in the benchmark is a closed value
(a code, an enum, a date, a version key). Text similarity would reward an
answer that is close to a wrong one, which is exactly the failure this
benchmark exists to catch, so no metric here uses it.

Three outcomes per metric and item:

* ``correct`` / ``wrong``: the item was scorable and the baseline answered;
* ``not_scorable``: the label does not carry the field, the baseline cannot
  produce it (``not_emitted``), the label has no backend equivalent
  (``no_coarse_equivalent``), or the baseline crashed (``baseline_error``).

Not-scorable items are counted and reported with their reasons; they never
enter a denominator.

Hierarchy rules (CLAUDE.md): a 2-segment code is a parent, 3+ segments is a
subcode (``*-T`` included). A subcode is credited only from the prediction's
own ``subcode`` field. A parent written into the subcode field, or a parent
status when a subcode was expected, is wrong.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from waymaker_ai.contracts import FINE_TO_COARSE, procedure_scope
from waymaker_ai.evaluation.predictions import INVALID_OUTPUT_FLAG, SCHEMA_VIOLATIONS_KEY

CORRECT = "correct"
WRONG = "wrong"
NOT_SCORABLE = "not_scorable"

ABSENCE_CODES = frozenset({"source_not_found", "citation_not_found"})
UNAVAILABILITY_CODES = frozenset({"verification_unavailable", "historical_lookup_required", "version_history_incomplete"})
VERSION_FAILURE_CODES = frozenset({"wrong_version", "future_not_yet_effective", "source_outdated"})
ACCEPTING_OVERALL = frozenset({"verified", "verified_partial"})
REJECTION_EXPECTED_OVERALL = frozenset({"failed", "human_review_required"})


# ---------------------------------------------------------------------------
# Code helpers
# ---------------------------------------------------------------------------
def normalize_code(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = "".join(str(value).split()).upper()
    return text or None


def code_segments(code: Optional[str]) -> int:
    return len(code.split("-")) if code else 0


def parent_of(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    parts = code.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else code


def is_subcode(code: Optional[str]) -> bool:
    return code_segments(code) >= 3


def _compact_code(value: str) -> str:
    return "".join(ch for ch in str(value).upper() if ch.isalnum())


# ---------------------------------------------------------------------------
# Item score
# ---------------------------------------------------------------------------
@dataclass
class ItemScore:
    metrics: Dict[str, Tuple[str, str]] = field(default_factory=dict)      # name -> (outcome, reason)
    counts: Dict[str, Dict[str, int]] = field(default_factory=dict)        # name -> {tp, fp, fn, tn}
    flags: List[str] = field(default_factory=list)
    primary: List[str] = field(default_factory=list)                       # metric names that decide "wrong"

    def set(self, name: str, outcome: str, reason: str = "") -> None:
        self.metrics[name] = (outcome, reason)

    def add_counts(self, name: str, **values: int) -> None:
        bucket = self.counts.setdefault(name, {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
        for key, value in values.items():
            bucket[key] += value

    def primary_wrong(self) -> Optional[bool]:
        scored = [self.metrics[name][0] for name in self.primary if name in self.metrics and self.metrics[name][0] != NOT_SCORABLE]
        if not scored:
            return None
        return any(outcome == WRONG for outcome in scored)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": {name: {"outcome": o, "reason": r} for name, (o, r) in sorted(self.metrics.items())},
            "counts": {name: dict(sorted(c.items())) for name, c in sorted(self.counts.items())},
            "flags": sorted(set(self.flags)),
            "primary_wrong": self.primary_wrong(),
        }


def _compare(score: ItemScore, name: str, expected: Any, predicted: Any, emits: Set[str], pred_field: str,
             invalid: bool, normalize=None) -> None:
    if pred_field not in emits:
        score.set(name, NOT_SCORABLE, "not_emitted")
        return
    if invalid:
        score.set(name, WRONG, "invalid_structured_output")
        return
    if normalize:
        expected, predicted = normalize(expected), normalize(predicted)
    score.set(name, CORRECT if expected == predicted else WRONG)


def score_item(example: Mapping[str, Any], prediction: Optional[Mapping[str, Any]], emits: Iterable[str],
               *, error: Optional[str] = None, reason: Optional[str] = None) -> ItemScore:
    """Score one baseline answer against one example.

    ``prediction`` None means the baseline produced no answer; every metric of
    the task is then not scorable with ``reason`` (``baseline_error`` when
    ``error`` is given, else ``not_applicable``). Items never silently vanish:
    they are counted under ``not_scorable`` with that reason.
    """
    task = example["task"]
    expected = example["expected"]
    emitted = set(emits)
    score = ItemScore()
    scorer = _TASK_SCORERS[task]
    if prediction is None:
        # Run the scorer on an empty prediction to learn which metrics exist,
        # then mark every one not scorable.
        scorer(score, expected, {}, set(), example)
        why = reason or ("baseline_error" if error else "not_applicable")
        for name, (_outcome, old_reason) in list(score.metrics.items()):
            score.set(name, NOT_SCORABLE, old_reason if old_reason == "not_labelled" else why)
        score.counts = {}
        score.flags = []
        return score
    scorer(score, expected, prediction, emitted, example)
    if SCHEMA_VIOLATIONS_KEY in prediction:
        # Model baselines only: was the answer exactly the structured-output contract?
        valid = not prediction.get(INVALID_OUTPUT_FLAG) and not prediction[SCHEMA_VIOLATIONS_KEY]
        score.set("structured_output_valid", CORRECT if valid else WRONG,
                  "" if valid else f"violations={prediction[SCHEMA_VIOLATIONS_KEY]}")
    return score


# ---------------------------------------------------------------------------
# status_procedure_classification
# ---------------------------------------------------------------------------
def _score_classification(score: ItemScore, expected: Mapping[str, Any], pred: Mapping[str, Any],
                          emits: Set[str], example: Mapping[str, Any]) -> None:
    invalid = bool(pred.get(INVALID_OUTPUT_FLAG))
    exp_status = normalize_code(expected.get("status_code"))
    exp_sub = normalize_code(expected.get("subcode"))
    pred_status = normalize_code(pred.get("status_code"))
    pred_sub = normalize_code(pred.get("subcode"))

    _compare(score, "status_exact", exp_status, pred_status, emits, "status_code", invalid)
    _score_subcode(score, exp_sub, pred_status, pred_sub, emits, invalid)
    _score_procedures(score, expected.get("procedure"), pred, emits, invalid)
    _score_procedure_scope(score, expected.get("procedure"), pred, emits, invalid)

    for key in ("current_status", "target_status"):
        if key not in expected:
            score.set(f"{key}_exact", NOT_SCORABLE, "not_labelled")
        else:
            _compare(score, f"{key}_exact", expected.get(key), pred.get(key), emits, key, invalid, normalize_code)

    if "needs_clarification" not in expected:
        score.set("clarification", NOT_SCORABLE, "not_labelled")
    elif "needs_clarification" not in emits or (pred.get("needs_clarification") is None and not invalid):
        score.set("clarification", NOT_SCORABLE, "not_emitted")
    else:
        want = bool(expected["needs_clarification"])
        got = None if invalid else bool(pred.get("needs_clarification"))
        score.set("clarification", CORRECT if got == want else WRONG, "invalid_structured_output" if invalid else "")
        score.add_counts("clarification",
                         tp=int(want and got is True), fp=int(not want and got is True),
                         fn=int(want and got is not True), tn=int(not want and got is False))

    _score_not_status_tokens(score, expected.get("not_status_tokens") or [], pred, emits)
    score.primary.extend(["status_exact", "subcode_exact", "procedure_fine"])
    if score.metrics.get("procedure_fine", (NOT_SCORABLE, ""))[0] == NOT_SCORABLE:
        score.primary.append("procedure_coarse")


def _score_subcode(score: ItemScore, exp_sub: Optional[str], pred_status: Optional[str], pred_sub: Optional[str],
                   emits: Set[str], invalid: bool) -> None:
    group = "subcode_expected_present" if exp_sub else "subcode_expected_absent"
    if "subcode" not in emits:
        score.set("subcode_exact", NOT_SCORABLE, "not_emitted")
        score.set(group, NOT_SCORABLE, "not_emitted")
        return
    if invalid:
        score.set("subcode_exact", WRONG, "invalid_structured_output")
        score.set(group, WRONG, "invalid_structured_output")
        return
    reason = ""
    if pred_sub is not None and not is_subcode(pred_sub):
        # A parent written into the subcode field is never a subcode answer.
        score.flags.append("parent_in_subcode_field")
        outcome, reason = WRONG, "parent_in_subcode_field"
    elif exp_sub and pred_sub is None and pred_status == parent_of(exp_sub):
        score.flags.append("parent_fallback")
        outcome, reason = WRONG, "parent_fallback"
    else:
        outcome = CORRECT if exp_sub == pred_sub else WRONG
        if outcome == WRONG and exp_sub and pred_sub and parent_of(pred_sub) == parent_of(exp_sub):
            reason = "sibling_subcode"
    score.set("subcode_exact", outcome, reason)
    score.set(group, outcome, reason)


def _score_procedures(score: ItemScore, exp_proc: Optional[str], pred: Mapping[str, Any], emits: Set[str],
                      invalid: bool) -> None:
    # Fine: only baselines with a fine taxonomy are scored.
    if "procedure_fine" not in emits:
        score.set("procedure_fine", NOT_SCORABLE, "baseline_emits_coarse_only" if "procedure_coarse" in emits else "not_emitted")
    elif invalid:
        score.set("procedure_fine", WRONG, "invalid_structured_output")
    else:
        got = pred.get("procedure_fine")
        outcome = CORRECT if got == exp_proc else WRONG
        reason = ""
        if outcome == WRONG and got and exp_proc and procedure_scope(got) != procedure_scope(exp_proc):
            score.flags.append("procedure_scope_mixed")
            reason = "visa_stay_scope_mixed"
        score.set("procedure_fine", outcome, reason)

    # Coarse: expected through FINE_TO_COARSE; a fine label with no backend
    # equivalent can be neither right nor wrong for a coarse classifier.
    if exp_proc is not None and FINE_TO_COARSE.get(exp_proc) is None:
        score.set("procedure_coarse", NOT_SCORABLE, "no_coarse_equivalent")
        return
    exp_coarse = FINE_TO_COARSE.get(exp_proc) if exp_proc is not None else None
    if "procedure_coarse" in emits:
        got_coarse = pred.get("procedure_coarse")
    elif "procedure_fine" in emits:
        fine = pred.get("procedure_fine")
        got_coarse = FINE_TO_COARSE.get(fine) if fine is not None else None
    else:
        score.set("procedure_coarse", NOT_SCORABLE, "not_emitted")
        return
    if invalid:
        score.set("procedure_coarse", WRONG, "invalid_structured_output")
        return
    score.set("procedure_coarse", CORRECT if got_coarse == exp_coarse else WRONG)


def _score_procedure_scope(score: ItemScore, exp_proc: Optional[str], pred: Mapping[str, Any], emits: Set[str],
                           invalid: bool) -> None:
    """Visa-issuance vs stay scope (CLAUDE.md: never mixed), on whichever taxonomy the baseline emits."""
    if exp_proc is None:
        score.set("procedure_scope_respected", NOT_SCORABLE, "label_has_no_procedure")
        return
    if not emits & {"procedure_fine", "procedure_coarse"}:
        score.set("procedure_scope_respected", NOT_SCORABLE, "not_emitted")
        return
    if invalid:
        score.set("procedure_scope_respected", NOT_SCORABLE, "invalid_structured_output")
        return
    got = pred.get("procedure_fine") if "procedure_fine" in emits else pred.get("procedure_coarse")
    if got is None:
        score.set("procedure_scope_respected", CORRECT, "no_procedure_predicted")
        return
    mixed = procedure_scope(got) != procedure_scope(exp_proc)
    if mixed:
        score.flags.append("procedure_scope_mixed")
    score.set("procedure_scope_respected", WRONG if mixed else CORRECT, "visa_stay_scope_mixed" if mixed else "")


def _score_not_status_tokens(score: ItemScore, tokens: Sequence[str], pred: Mapping[str, Any], emits: Set[str]) -> None:
    if not tokens:
        score.set("not_status_token_respected", NOT_SCORABLE, "not_labelled")
        return
    if not emits & {"status_code", "subcode", "mentioned_codes"}:
        score.set("not_status_token_respected", NOT_SCORABLE, "not_emitted")
        return
    produced = {_compact_code(c) for c in _predicted_codes(pred) if c}
    hit = sorted(t for t in tokens if _compact_code(t) in produced)
    if hit:
        score.flags.append("code_from_non_code_token")
    score.set("not_status_token_respected", WRONG if hit else CORRECT, ",".join(hit))


def _predicted_codes(pred: Mapping[str, Any]) -> List[str]:
    codes = [pred.get("status_code"), pred.get("subcode"), pred.get("current_status"), pred.get("target_status")]
    codes.extend(pred.get("mentioned_codes") or [])
    return [str(c) for c in codes if c]


# ---------------------------------------------------------------------------
# entity_date_extraction
# ---------------------------------------------------------------------------
def _score_entities(score: ItemScore, expected: Mapping[str, Any], pred: Mapping[str, Any],
                    emits: Set[str], example: Mapping[str, Any]) -> None:
    """Dates by value, and by (value, role) only for baselines that emit roles.

    A baseline whose extractor has no notion of a date's role (B1) is scored on
    values; its role metrics are not scorable instead of always wrong.
    """
    invalid = bool(pred.get(INVALID_OUTPUT_FLAG))
    exp_dates = [(str(d.get("value")), d.get("role")) for d in expected.get("dates") or []]
    if "dates" not in emits:
        for name in ("dates_value_exact", "dates_exact"):
            score.set(name, NOT_SCORABLE, "not_emitted")
    else:
        got = [] if invalid else [(str(d.get("value")), d.get("role")) for d in pred.get("dates") or []]
        _pr_counts(score, "dates_value_only", [v for v, _ in exp_dates], [v for v, _ in got])
        same_values = Counter(v for v, _ in exp_dates) == Counter(v for v, _ in got) and not invalid
        score.set("dates_value_exact", CORRECT if same_values else WRONG, "invalid_structured_output" if invalid else "")
        if "date_roles" in emits:
            _pr_counts(score, "dates_value_role", exp_dates, got)
            same = Counter(exp_dates) == Counter(got) and not invalid
            score.set("dates_exact", CORRECT if same else WRONG, "invalid_structured_output" if invalid else "")
        else:
            score.set("dates_exact", NOT_SCORABLE, "roles_not_emitted")
    if "status_codes" not in expected:
        score.set("status_codes_exact", NOT_SCORABLE, "not_labelled")
    elif "status_codes" not in emits:
        score.set("status_codes_exact", NOT_SCORABLE, "not_emitted")
    else:
        want = [normalize_code(c) for c in expected.get("status_codes") or []]
        got_codes = [] if invalid else [normalize_code(c) for c in pred.get("status_codes") or []]
        _pr_counts(score, "status_codes", sorted(set(want)), sorted(set(got_codes)))
        score.set("status_codes_exact", CORRECT if set(want) == set(got_codes) and not invalid else WRONG)
    score.primary.extend(["dates_exact", "dates_value_exact"])


def _pr_counts(score: ItemScore, name: str, expected: Sequence[Any], predicted: Sequence[Any]) -> None:
    exp, got = Counter(expected), Counter(predicted)
    tp = sum((exp & got).values())
    score.add_counts(name, tp=tp, fp=sum(got.values()) - tp, fn=sum(exp.values()) - tp)


# ---------------------------------------------------------------------------
# citation_verification
# ---------------------------------------------------------------------------
def expects_unavailability(expected: Mapping[str, Any]) -> bool:
    """True when the label says the source could not be checked (not that it is absent).

    Only the label's own outcome counts: overall ``verification_unavailable``,
    or a layer code that means "could not be checked". ``forbidden_codes`` is
    deliberately not read here: authors forbid ``source_not_found`` on items
    whose source plainly exists (a verified or a repealed law), and an absence
    code there is a wrong answer (``unsupported_absence``,
    ``forbidden_codes_absent``), not a lookup failure turned into absence.
    """
    if expected.get("overall") == "verification_unavailable":
        return True
    return any(code in UNAVAILABILITY_CODES for code in (expected.get("layer_codes") or {}).values())


def _score_citation(score: ItemScore, expected: Mapping[str, Any], pred: Mapping[str, Any],
                    emits: Set[str], example: Mapping[str, Any]) -> None:
    exp_overall = expected.get("overall")
    exp_layers: Mapping[str, str] = expected.get("layer_codes") or {}
    got_overall = pred.get("overall")
    got_layers: Mapping[str, str] = pred.get("layer_codes") or {}
    got_codes = set(pred.get("codes") or []) | set(got_layers.values())

    _compare(score, "overall_status", exp_overall, got_overall, emits, "overall", False)
    for layer in sorted(exp_layers):
        name = f"layer_code:{layer}"
        if "layer_codes" not in emits:
            score.set(name, NOT_SCORABLE, "not_emitted")
        elif layer not in got_layers:
            score.set(name, NOT_SCORABLE, "layer_not_reported")
        else:
            score.set(name, CORRECT if got_layers[layer] == exp_layers[layer] else WRONG)
    if "layer_codes" in emits and exp_layers:
        reported = [layer for layer in exp_layers if layer in got_layers]
        agree = all(got_layers[layer] == exp_layers[layer] for layer in reported)
        score.set("all_reported_layers_agree", CORRECT if reported and agree else WRONG if reported else NOT_SCORABLE,
                  "" if reported else "no_layer_reported")

    forbidden = set(expected.get("forbidden_codes") or [])
    if not forbidden:
        score.set("forbidden_codes_absent", NOT_SCORABLE, "not_labelled")
    else:
        hit = sorted(forbidden & got_codes)
        if hit:
            score.flags.append("forbidden_code_emitted")
        score.set("forbidden_codes_absent", WRONG if hit else CORRECT, ",".join(hit))

    if "max_highest_verified_layer" not in expected:
        score.set("highest_layer_within_bound", NOT_SCORABLE, "not_labelled")
    elif "highest_verified_layer" not in emits or pred.get("highest_verified_layer") is None:
        score.set("highest_layer_within_bound", NOT_SCORABLE, "not_emitted")
    else:
        within = int(pred["highest_verified_layer"]) <= int(expected["max_highest_verified_layer"])
        score.set("highest_layer_within_bound", CORRECT if within else WRONG)

    if "injection_flagged" not in expected:
        score.set("injection_flagged", NOT_SCORABLE, "not_labelled")
    elif "injection_flagged" not in emits or pred.get("injection_flagged") is None:
        score.set("injection_flagged", NOT_SCORABLE, "not_emitted")
    else:
        score.set("injection_flagged", CORRECT if bool(pred["injection_flagged"]) == bool(expected["injection_flagged"]) else WRONG)

    # Failure is not absence: an absence code where the label says "could not check".
    expected_absence = {code for code in exp_layers.values() if code in ABSENCE_CODES}
    emitted_absence = (got_codes & ABSENCE_CODES) - expected_absence
    if "overall" not in emits:
        score.set("false_absence", NOT_SCORABLE, "not_emitted")
        score.set("unsupported_absence", NOT_SCORABLE, "not_emitted")
    else:
        if expects_unavailability(expected):
            score.set("false_absence", WRONG if emitted_absence else CORRECT, ",".join(sorted(emitted_absence)))
            if emitted_absence:
                score.flags.append("false_absence_declaration")
        else:
            score.set("false_absence", NOT_SCORABLE, "label_not_unavailable")
        score.set("unsupported_absence", WRONG if emitted_absence else CORRECT, ",".join(sorted(emitted_absence)))

    # Wrong / future version: detected (strict L2 code) and accepted (overall).
    # A baseline that reports layers but no L2 did not detect the version
    # failure: that is a miss, not "not scorable" (the existing backend pins no
    # version, and its detection rate must show it).
    exp_l2 = exp_layers.get("version_identity")
    if exp_l2 in VERSION_FAILURE_CODES and "overall" in emits:
        got_l2 = got_layers.get("version_identity")
        if "layer_codes" not in emits:
            score.set("wrong_version_detected", NOT_SCORABLE, "not_emitted")
        elif got_l2 is None:
            score.set("wrong_version_detected", WRONG, "layer_not_reported")
        else:
            score.set("wrong_version_detected", CORRECT if got_l2 == exp_l2 else WRONG,
                      "other_version_failure" if got_l2 in VERSION_FAILURE_CODES and got_l2 != exp_l2 else "")
        accepted = got_overall in ACCEPTING_OVERALL
        outcome = WRONG if accepted else CORRECT
        score.set("version_failure_rejected", outcome, exp_l2 if accepted else "")
        # Per expected code, so a gate can count accepted future versions on their own.
        for code in sorted(VERSION_FAILURE_CODES):
            if code == exp_l2:
                score.set(f"version_failure_rejected:{code}", outcome, "accepted" if accepted else "")
            else:
                score.set(f"version_failure_rejected:{code}", NOT_SCORABLE, "label_other_version_failure")
        if accepted:
            score.flags.append(f"accepted_{exp_l2}")
    else:
        reason = "not_emitted" if "overall" not in emits else "label_not_version_failure"
        score.set("wrong_version_detected", NOT_SCORABLE, reason)
        score.set("version_failure_rejected", NOT_SCORABLE, reason)
        for code in sorted(VERSION_FAILURE_CODES):
            score.set(f"version_failure_rejected:{code}", NOT_SCORABLE, reason)

    if exp_overall in REJECTION_EXPECTED_OVERALL and "overall" in emits:
        accepted = got_overall in ACCEPTING_OVERALL
        score.set("unsupported_claim_rejected", WRONG if accepted else CORRECT, "accepted" if accepted else "")
        if accepted:
            score.flags.append("unsupported_claim_accepted")
    else:
        score.set("unsupported_claim_rejected", NOT_SCORABLE,
                  "not_emitted" if "overall" not in emits else "label_not_rejection")
    score.primary.append("overall_status")


# ---------------------------------------------------------------------------
# temporal_version_selection
# ---------------------------------------------------------------------------
def _version_keys(value: Any) -> List[List[Optional[str]]]:
    keys = []
    for item in value or []:
        pair = list(item)
        keys.append([None if v is None else str(v) for v in pair])
    return keys


def _score_temporal(score: ItemScore, expected: Mapping[str, Any], pred: Mapping[str, Any],
                    emits: Set[str], example: Mapping[str, Any]) -> None:
    if "candidate_version_keys" not in emits:
        score.set("candidates_exact", NOT_SCORABLE, "not_emitted")
    else:
        same = _version_keys(expected.get("candidate_version_keys")) == _version_keys(pred.get("candidate_version_keys"))
        score.set("candidates_exact", CORRECT if same else WRONG)

    want = set(expected.get("warnings") or [])
    got = set(pred.get("warnings") or [])
    if "warnings" not in emits:
        score.set("warnings_all_present", NOT_SCORABLE, "not_emitted")
        score.set("forbidden_warnings_absent", NOT_SCORABLE, "not_emitted")
    else:
        missing = sorted(want - got)
        score.add_counts("warning_recall", tp=len(want & got), fn=len(want - got))
        score.set("warnings_all_present", WRONG if missing else CORRECT, ",".join(missing))
        if missing:
            score.flags.append("required_warning_missing")
        forbidden = set(expected.get("forbidden_warnings") or [])
        if not forbidden:
            score.set("forbidden_warnings_absent", NOT_SCORABLE, "not_labelled")
        else:
            hit = sorted(forbidden & got)
            if hit:
                score.flags.append("forbidden_warning_emitted")
            score.set("forbidden_warnings_absent", WRONG if hit else CORRECT, ",".join(hit))

    if "determination" not in emits:
        score.set("determination_candidate_only", NOT_SCORABLE, "not_emitted")
    else:
        want_det = expected.get("determination", "candidate_only")
        score.set("determination_candidate_only", CORRECT if pred.get("determination") == want_det else WRONG)
    score.primary.extend(["candidates_exact", "warnings_all_present", "forbidden_warnings_absent"])


# ---------------------------------------------------------------------------
# abstention (structured model answers only)
# ---------------------------------------------------------------------------
def _score_abstention(score: ItemScore, expected: Mapping[str, Any], pred: Mapping[str, Any],
                      emits: Set[str], example: Mapping[str, Any]) -> None:
    invalid = bool(pred.get(INVALID_OUTPUT_FLAG))
    want_withhold = bool(expected.get("must_withhold_conclusion"))
    if "conclusion_withheld" not in emits:
        score.set("withhold_correct", NOT_SCORABLE, "not_emitted")
    else:
        got = None if invalid else pred.get("conclusion_withheld")
        score.set("withhold_correct", CORRECT if got is not None and bool(got) == want_withhold else WRONG,
                  "invalid_structured_output" if invalid else "")
        score.add_counts("withhold", tp=int(want_withhold and got is True), fp=int(not want_withhold and got is True),
                         fn=int(want_withhold and got is not True), tn=int(not want_withhold and got is False))
        if want_withhold and got is not True:
            score.flags.append("failed_to_abstain")

    required = set(expected.get("required_issue_keys") or [])
    if "issues" not in emits:
        score.set("required_issues_covered", NOT_SCORABLE, "not_emitted")
    else:
        got_issues = set() if invalid else set(pred.get("issues") or [])
        missing = sorted(required - got_issues)
        score.add_counts("required_issue_coverage", tp=len(required & got_issues), fn=len(required - got_issues))
        score.set("required_issues_covered", WRONG if missing else CORRECT, ",".join(missing))

    forbidden = list(expected.get("forbidden_assertions") or [])
    if not forbidden:
        score.set("forbidden_assertions_absent", NOT_SCORABLE, "not_labelled")
    elif "claims" not in emits:
        score.set("forbidden_assertions_absent", NOT_SCORABLE, "not_emitted")
    else:
        claims = [] if invalid else list(pred.get("claims") or [])
        hit = sorted(_forbidden_hits(forbidden, claims))
        score.set("forbidden_assertions_absent", WRONG if hit else CORRECT, ",".join(hit))
        if hit:
            score.flags.append("forbidden_assertion_made")
    score.primary.extend(["withhold_correct", "required_issues_covered", "forbidden_assertions_absent"])


def _forbidden_hits(forbidden: Sequence[str], claims: Sequence[Mapping[str, Any]]) -> Set[str]:
    """Exact key match, or exact equality of normalized claim text. Never similarity."""
    keys = {str(c.get("assertion_key")) for c in claims if c.get("assertion_key")}
    texts = {" ".join(str(c.get("text") or "").split()) for c in claims}
    return {f for f in forbidden if f in keys or " ".join(str(f).split()) in texts}


_TASK_SCORERS = {
    "status_procedure_classification": _score_classification,
    "entity_date_extraction": _score_entities,
    "citation_verification": _score_citation,
    "temporal_version_selection": _score_temporal,
    "abstention": _score_abstention,
}


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def _ratio(numerator: int, denominator: int) -> Optional[float]:
    return round(numerator / denominator, 6) if denominator else None


@dataclass
class MetricTally:
    correct: int = 0
    wrong: int = 0
    not_scorable: int = 0
    reasons: Counter = field(default_factory=Counter)

    def add(self, outcome: str, reason: str) -> None:
        if outcome == CORRECT:
            self.correct += 1
        elif outcome == WRONG:
            self.wrong += 1
            if reason:
                self.reasons[f"wrong:{reason}"] += 1
        else:
            self.not_scorable += 1
            self.reasons[f"not_scorable:{reason or 'unspecified'}"] += 1

    def to_dict(self) -> Dict[str, Any]:
        denominator = self.correct + self.wrong
        return {
            "correct": self.correct,
            "wrong": self.wrong,
            "denominator": denominator,
            "not_scorable": self.not_scorable,
            "accuracy": _ratio(self.correct, denominator),
            "reasons": dict(sorted(self.reasons.items())),
        }


def aggregate(scores: Sequence[ItemScore], *, errors: int = 0, items: int = 0) -> Dict[str, Any]:
    tallies: Dict[str, MetricTally] = {}
    counts: Dict[str, Dict[str, int]] = {}
    flags: Counter = Counter()
    for score in scores:
        for name, (outcome, reason) in score.metrics.items():
            tallies.setdefault(name, MetricTally()).add(outcome, reason)
        for name, bucket in score.counts.items():
            total = counts.setdefault(name, {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
            for key, value in bucket.items():
                total[key] += value
        flags.update(set(score.flags))
    pr = {}
    for name, c in sorted(counts.items()):
        pr[name] = {
            **c,
            "precision": _ratio(c["tp"], c["tp"] + c["fp"]),
            "recall": _ratio(c["tp"], c["tp"] + c["fn"]),
        }
    return {
        "items": items,
        "baseline_errors": errors,
        "metrics": {name: tallies[name].to_dict() for name in sorted(tallies)},
        "precision_recall": pr,
        "flags": dict(sorted(flags.items())),
    }
