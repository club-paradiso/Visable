"""Existing law grounding: the backend's question-cited article verification.

The backend runs in a subprocess (drivers/existing_law_driver.py) against a
fake law.go.kr built from the item's source bundle. This module builds the
driver input and maps the backend's statuses onto WLIE codes with the table in
07-evidence-verification-design.md §4.

Mapping rule: the runner maps what the backend *declares*, never what it
should have declared. The §4 row for ``CITED_LAW_NOT_FOUND`` says it means
``source_not_found`` "only if the search succeeded with complete coverage";
that condition is exactly what the benchmark labels encode, so the metric
applies it (a declared absence on an item labelled unavailable is a false
absence declaration). Applying it inside the mapping would credit the backend
with WLIE's rule and hide the defect being measured.

=================================  ==============================================
backend citation status            WLIE layers (outcome, code)
=================================  ==============================================
``verified``                       L1 pass source_verified, L3 pass citation_verified
                                   (L2 is never reported: the backend pins no version)
``failed_verification`` +          L1 fail source_not_found
``CITED_LAW_NOT_FOUND``
``failed_verification`` (detail    L1 pass source_verified, L3 unavailable
lookup error)                      verification_unavailable
``source_linked_unverified`` /     L1 pass source_verified, L3 unavailable
``ARTICLE_TEXT_NOT_FOUND``         verification_unavailable (the backend does not
                                   tell a parser miss from an authoritative miss and
                                   calls the state "unverified", not "absent")
``error`` (+ SOURCE_UNAVAILABLE)   L1 unavailable verification_unavailable
``extracted_only`` / no lookup     L1 unavailable not_checked
=================================  ==============================================

When the backend extracted no citation at all, the claim-level status maps as
``verified_law_evidence`` → L1 pass source_verified (§4: "L1 source_verified
only"), ``law_evidence_unavailable`` / ``law_api_unavailable`` /
``law_evidence_present_unverified`` / ``error`` → L1 unavailable, anything
else → L1 not_checked. Layers are combined per spec 07 §3: the worst outcome
per layer over all citations.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from waymaker_ai.contracts import (
    ClaimVerification,
    LayerOutcome,
    LayerResult,
    VerificationCode,
    VerificationLayer,
    compact,
)
from waymaker_ai.evaluation.baselines.b1_python import backend_available, backend_dir
from waymaker_ai.evaluation.baselines.base import (
    DRIVERS_DIR,
    Baseline,
    EvalItem,
    ItemResult,
    RunContext,
    SubprocessFailure,
    child_env,
    results_from_driver,
    run_jsonl,
)
from waymaker_ai.evaluation.benchmark import EXPERIMENT_ROOT, reference_date_of

L1 = VerificationLayer.SOURCE_IDENTITY
L3 = VerificationLayer.CITATION_IDENTITY

#: Worst first (spec 07 §3).
_OUTCOME_ORDER: Tuple[LayerOutcome, ...] = (
    LayerOutcome.FAIL,
    LayerOutcome.UNAVAILABLE,
    LayerOutcome.NEEDS_REVIEW,
    LayerOutcome.PASS,
    LayerOutcome.NOT_APPLICABLE,
)

_SOURCE_VERIFIED = LayerResult(L1, LayerOutcome.PASS, VerificationCode.SOURCE_VERIFIED, "backend: law found by title search")
_UNAVAILABLE_L1 = LayerResult(L1, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE, "backend: law lookup failed")
_NOT_CHECKED_L1 = LayerResult(L1, LayerOutcome.UNAVAILABLE, VerificationCode.NOT_CHECKED, "backend: nothing was looked up")

_UNAVAILABLE_CLAIM_STATUSES = frozenset({
    "law_evidence_unavailable", "law_api_unavailable", "law_evidence_present_unverified", "error",
})


def citation_layers(citation: Mapping[str, Any]) -> List[LayerResult]:
    """WLIE layer results for one backend citation (see the module table)."""
    status = str(citation.get("verification_status") or "")
    warnings = {str(w).upper() for w in citation.get("warnings") or []}
    if status == "verified":
        return [_SOURCE_VERIFIED,
                LayerResult(L3, LayerOutcome.PASS, VerificationCode.CITATION_VERIFIED, "backend: article text matched")]
    if status == "failed_verification" and "CITED_LAW_NOT_FOUND" in warnings:
        return [LayerResult(L1, LayerOutcome.FAIL, VerificationCode.SOURCE_NOT_FOUND, "backend: CITED_LAW_NOT_FOUND")]
    if status in ("failed_verification", "source_linked_unverified"):
        detail = "backend: " + (",".join(sorted(warnings)) or status)
        return [_SOURCE_VERIFIED,
                LayerResult(L3, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE, detail)]
    if status == "error":
        return [_UNAVAILABLE_L1]
    if status in ("extracted_only", "not_verified", ""):
        return [_NOT_CHECKED_L1]
    return [LayerResult(L1, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                        f"backend: unmapped citation status {status}")]


def claim_status_layers(status: str) -> List[LayerResult]:
    """Layer results when the backend extracted no citation from the claim."""
    if status == "verified_law_evidence":
        return [_SOURCE_VERIFIED]
    if status in _UNAVAILABLE_CLAIM_STATUSES:
        return [_UNAVAILABLE_L1]
    return [_NOT_CHECKED_L1]


def worst_per_layer(results: Sequence[LayerResult]) -> Tuple[LayerResult, ...]:
    by_layer: Dict[VerificationLayer, LayerResult] = {}
    for result in results:
        current = by_layer.get(result.layer)
        if current is None or _OUTCOME_ORDER.index(result.outcome) < _OUTCOME_ORDER.index(current.outcome):
            by_layer[result.layer] = result
    return tuple(by_layer[layer] for layer in sorted(by_layer, key=lambda layer: layer.order))


def map_backend_verification(raw: Mapping[str, Any], claim_id: str = "") -> Dict[str, Any]:
    """Normalized citation prediction from the driver's trimmed grounding context."""
    verification = raw.get("citation_verification") or {}
    citations = list(verification.get("citations") or [])
    results: List[LayerResult] = []
    if citations:
        for citation in citations:
            results.extend(citation_layers(citation))
    else:
        results.extend(claim_status_layers(str(verification.get("status") or "")))
    claim = ClaimVerification(claim_id, worst_per_layer(results))
    return {
        "overall": claim.overall().value,
        "layer_codes": {r.layer.value: r.code.value for r in claim.layers},
        "codes": sorted(set(claim.codes())),
        "highest_verified_layer": claim.highest_verified_layer(),
    }


def backend_question(claim: Mapping[str, Any]) -> Tuple[str, List[str]]:
    """The claim text, plus any cited string it does not already contain.

    The backend's only input channel is the question text. Appending a missing
    citation gives it the same information WLIE receives in ``citations``
    (equivalent-input rule); the quoted text and the context law
    (``context_title``, what 같은 법 refers to) are already part of the claim
    text or have no channel at all, and that is recorded, not repaired.
    """
    text = str(claim.get("text") or "")
    notes: List[str] = []
    missing = [c for c in claim.get("citations") or [] if c and compact(str(c)) not in compact(text)]
    if missing:
        text = text + " (" + ", ".join(str(c) for c in missing) + ")"
        notes.append(f"citations_appended={len(missing)}")
    if claim.get("quoted_text") and compact(str(claim["quoted_text"])) not in compact(text):
        notes.append("quoted_text_has_no_backend_channel")
    if claim.get("context_title") and compact(str(claim["context_title"])) not in compact(text):
        notes.append("context_title_has_no_backend_channel")
    return text, notes


class ExistingLaw(Baseline):
    name = "existing_law"
    kind = "deterministic"
    uses_backend = True
    description = ("Existing backend law grounding: services.law_grounding.build_law_grounding_context on the claim "
                   "text (search_laws + cloud fallback + _verify_requested_articles + get_law_detail) against a fake "
                   "law.go.kr DRF server built from the source bundle; statuses mapped by spec 07 §4.")
    emits = {"citation_verification": frozenset({"overall", "layer_codes", "codes", "highest_verified_layer"})}

    def available(self, ctx: RunContext) -> Tuple[bool, str]:
        ok, reason = backend_available(ctx)
        if not ok:
            return ok, reason
        if not (backend_dir(ctx) / "services" / "law_grounding.py").is_file():
            return False, "backend/services/law_grounding.py not found"
        return True, ""

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        results: Dict[str, ItemResult] = {}
        records = []
        notes_by_id: Dict[str, List[str]] = {}
        runnable = []
        for item in items:
            if item.bundle is None:
                results[item.id] = ItemResult(item.id, "error", error="source bundle not loaded")
                continue
            question, notes = backend_question(item.example["input"]["claim"])
            reference = reference_date_of(item.example, item.bundle.data)
            if reference is None:
                # Without a simulated "today" every dated version counts as in force,
                # so the fake would serve the latest one, future versions included.
                notes.append("no_reference_date:latest_version_served")
            records.append({"id": item.id, "question": question, "bundle_path": str(item.bundle.path),
                            "reference_date": reference.isoformat() if reference else None})
            notes_by_id[item.id] = notes
            runnable.append(item)
        if not runnable:
            return results
        cmd = [str(ctx.backend_python), "-B", "-s", "-W", "ignore", str(DRIVERS_DIR / "existing_law_driver.py"),
               str(backend_dir(ctx)), str(EXPERIMENT_ROOT)]
        try:
            outputs, info = run_jsonl(cmd, records, env=child_env(ctx), cwd=ctx.scratch_dir, timeout=ctx.timeout_seconds)
        except SubprocessFailure as exc:
            results.update({item.id: ItemResult(item.id, "error", error=str(exc)) for item in runnable})
            return results
        ctx.process_info.setdefault(self.name, {}).update(info)
        driven = results_from_driver(runnable, outputs, self.convert)
        by_id = {str(o.get("id")): o for o in outputs}
        for item_id, result in driven.items():
            result.notes.extend(notes_by_id.get(item_id, []))
            raw = (by_id.get(item_id) or {}).get("raw") or {}
            for operation in raw.get("unexercised_fault_operations") or []:
                result.notes.append(f"fault_not_exercised:{operation}")
            for version in raw.get("fixture_partial_versions") or []:
                result.notes.append(f"fixture_partial_version:{version}")
            unchecked = unchecked_citations(raw) if raw else None
            if unchecked:
                result.notes.append(f"unchecked_extracted_citations={unchecked}")
            blocked = raw.get("blocked_network_attempts") if raw else None
            if blocked and result.status == "ok":
                # A lookup that missed the fake hit the disabled socket: the "unavailable"
                # the backend then reports is the harness, not the backend's answer.
                result.status, result.prediction = "error", None
                result.error = (f"the backend attempted {blocked} network connection(s) that bypassed the fake "
                                "law.go.kr transport; the item is not scored")
            calls = (by_id.get(item_id) or {}).get("calls")
            if calls is not None and isinstance(result.raw, dict):
                result.raw = {**result.raw, "calls": calls}
        results.update(driven)
        return results

    def convert(self, item: EvalItem, out: Mapping[str, Any]) -> Dict[str, Any]:
        return map_backend_verification(out["raw"], item.id)


def unchecked_citations(raw: Mapping[str, Any]) -> Optional[int]:
    """Citations the backend extracted but never checked (it checks the first three)."""
    extracted = raw.get("extracted_citations")
    checked = len((raw.get("citation_verification") or {}).get("citations") or [])
    if extracted is None:
        return None
    return max(0, int(extracted) - checked)
