"""WLIE: the reference verifier and temporal resolver over the fixture adapter.

Calls, exactly as specs 06 / 07 and ``waymaker_ai.legal`` define them::

    adapter = FixtureAdapter(bundle, path=path)
    verify_claim(claim, adapter, dates=..., anchor=..., question_date=..., secondary_anchors=...)
    lookup, versions = adapter.list_versions(stable_id)
    select_candidate_versions(versions, history=lookup, dates=..., anchor=..., secondary_anchors=...,
                              provision_key=..., question_date=...)

Every argument is passed by keyword, so a renamed parameter fails loudly as a
baseline error instead of being guessed. Tests inject stub modules with the
same signatures.

Every adapter call goes through ``CountingAdapter`` so the report can show how
many lookups and upstream calls (``LookupResult.calls``) one item cost.
"""
from __future__ import annotations

import importlib
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from waymaker_ai.contracts import AnchorKind, ClaimInput, LookupResult, Scope, TemporalAssessment
from waymaker_ai.evaluation.baselines.base import Baseline, EvalItem, ItemResult, RunContext, measured
from waymaker_ai.evaluation.benchmark import anchor_of, relevant_dates_of, secondary_anchors_of

#: The flag ``legal.injection`` puts on instruction-like source text (spec 07 §2.5).
INJECTION_TOKEN = "untrusted_instruction_like_text"


class CountingAdapter:
    """Pass-through adapter wrapper that counts lookups and upstream calls."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.lookups = 0
        self.upstream_calls = 0
        self.statuses: List[str] = []

    def _wrap(self, name: str):
        method = getattr(self._inner, name)

        def counted(*args: Any, **kwargs: Any) -> Any:
            result = method(*args, **kwargs)
            self.lookups += 1
            lookup = result[0] if isinstance(result, tuple) and result else None
            if isinstance(lookup, LookupResult):
                self.upstream_calls += int(lookup.calls or 0)
                self.statuses.append(f"{name}:{lookup.status.value}")
            return result

        return counted

    def resolve_title(self, *args: Any, **kwargs: Any) -> Any:
        return self._wrap("resolve_title")(*args, **kwargs)

    def list_versions(self, *args: Any, **kwargs: Any) -> Any:
        return self._wrap("list_versions")(*args, **kwargs)

    def get_provision(self, *args: Any, **kwargs: Any) -> Any:
        return self._wrap("get_provision")(*args, **kwargs)

    def get_addenda(self, *args: Any, **kwargs: Any) -> Any:
        return self._wrap("get_addenda")(*args, **kwargs)

    def guidance(self, *args: Any, **kwargs: Any) -> Any:
        return self._wrap("guidance")(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def claim_input_of(example: Mapping[str, Any]) -> ClaimInput:
    claim = example["input"]["claim"]
    scope = None
    if isinstance(claim.get("scope"), dict):
        raw = claim["scope"]
        scope = Scope(
            status_codes=tuple(raw.get("status_codes") or ()),
            subcodes=tuple(raw.get("subcodes") or ()),
            procedures=tuple(raw.get("procedures") or ()),
            all_subcodes_explicit=bool(raw.get("all_subcodes_explicit", False)),
            condition_kind=str(raw.get("condition_kind") or "always"),
            note=str(raw.get("note") or ""),
        )
    asserted = claim.get("asserted_version_key")
    return ClaimInput(
        claim_id=example["id"],
        text=str(claim.get("text") or ""),
        citations=tuple(claim.get("citations") or ()),
        quoted_text=claim.get("quoted_text"),
        numbers=tuple(claim.get("numbers") or ()),
        scope=scope,
        topic=claim.get("topic"),
        value=claim.get("value"),
        asserted_version_key=(str(asserted[0]), asserted[1]) if asserted else None,
        # The law that 같은 법 / 영 / 규칙 refer to (schema input.claim.context_title).
        context_title=claim.get("context_title"),
    )


def citation_prediction(verification: Any) -> Dict[str, Any]:
    """Normalized prediction from a ``ClaimVerification`` (or its ``VerificationReport`` subclass)."""
    layers = {r.layer.value: r.code.value for r in verification.layers}
    flagged = getattr(verification, "injection_flagged", None)
    if flagged is None:  # a plain ClaimVerification carries no flag field; fall back to layer details
        flagged = any(INJECTION_TOKEN in str(r.detail or "") for r in verification.layers)
    return {
        "overall": verification.overall().value,
        "layer_codes": layers,
        "codes": sorted(set(verification.codes())),
        "highest_verified_layer": verification.highest_verified_layer(),
        "injection_flagged": bool(flagged),
    }


def temporal_prediction(assessment: TemporalAssessment) -> Dict[str, Any]:
    return {
        "candidate_version_keys": assessment.candidate_keys(),
        "warnings": [w.value for w in assessment.warnings],
        "determination": assessment.determination,
    }


class Wlie(Baseline):
    name = "wlie"
    kind = "deterministic"
    description = ("WLIE reference implementation: legal.verification.verify_claim (L1-L7) and "
                   "legal.temporal.select_candidate_versions over legal.adapters.FixtureAdapter.")
    emits = {
        "citation_verification": frozenset({"overall", "layer_codes", "codes", "highest_verified_layer", "injection_flagged"}),
        "temporal_version_selection": frozenset({"candidate_version_keys", "warnings", "determination"}),
    }

    def __init__(self, modules: Optional[Mapping[str, Any]] = None) -> None:
        # Tests inject stub modules; the runner imports the real ones.
        self._modules = dict(modules or {})

    def _module(self, name: str) -> Any:
        if name not in self._modules:
            self._modules[name] = importlib.import_module(f"waymaker_ai.legal.{name}")
        return self._modules[name]

    def available(self, ctx: RunContext) -> Tuple[bool, str]:
        try:
            ok = (hasattr(self._module("adapters"), "FixtureAdapter")
                  and hasattr(self._module("verification"), "verify_claim")
                  and hasattr(self._module("temporal"), "select_candidate_versions"))
        except Exception as exc:  # an import error is "not available", not a crash
            return False, f"waymaker_ai.legal is not importable: {type(exc).__name__}: {exc}"
        return (True, "") if ok else (False, "waymaker_ai.legal lacks FixtureAdapter / verify_claim / select_candidate_versions")

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        results: Dict[str, ItemResult] = {}
        for item in items:
            if item.bundle is None:
                results[item.id] = ItemResult(item.id, "error", error="source bundle not loaded")
                continue
            try:
                inner = self._module("adapters").FixtureAdapter(item.bundle.data, path=item.bundle.path)
                adapter = CountingAdapter(inner)
                call = self._citation_call if item.task == "citation_verification" else self._temporal_call
                prediction, latency, peak = measured(lambda: call(item, adapter))
            except Exception as exc:  # a crash is a baseline error, never a wrong answer
                results[item.id] = ItemResult(item.id, "error", error=f"{type(exc).__name__}: {exc}"[:500])
                continue
            results[item.id] = ItemResult(
                item.id, "ok", prediction=prediction, raw={"adapter_statuses": adapter.statuses},
                latency_ms=latency, upstream_calls=adapter.upstream_calls, peak_memory_bytes=peak,
                notes=[f"adapter_lookups={adapter.lookups}"],
            )
        return results

    def _citation_call(self, item: EvalItem, adapter: "CountingAdapter") -> Dict[str, Any]:
        dates = relevant_dates_of(item.example)
        verification = self._module("verification").verify_claim(
            claim_input_of(item.example),
            adapter,
            dates=dates,
            anchor=anchor_of(item.example),
            question_date=dates.question_date,
            secondary_anchors=secondary_anchors_of(item.example),
        )
        return citation_prediction(verification)

    def _temporal_call(self, item: EvalItem, adapter: "CountingAdapter") -> Dict[str, Any]:
        query = item.example["input"]["temporal_query"]
        lookup, versions = adapter.list_versions(query["stable_id"])
        dates = relevant_dates_of(item.example)
        anchor_raw = query.get("anchor") or (item.example.get("scenario") or {}).get("anchor")
        assessment = self._module("temporal").select_candidate_versions(
            list(versions),
            history=lookup,
            dates=dates,
            anchor=AnchorKind(anchor_raw) if anchor_raw else None,
            secondary_anchors=secondary_anchors_of(item.example),
            provision_key=query.get("provision"),
            question_date=dates.question_date,
        )
        return temporal_prediction(assessment)
