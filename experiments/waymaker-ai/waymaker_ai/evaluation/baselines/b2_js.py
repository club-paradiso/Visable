"""B2: the JS status-guidance resolver used by the search page and quick answer.

The subcode is read only from an exact code the resolver itself marked
(``displayCode``, or the first interpreted code when ``exact`` is true). The
parent is taken from the guidance bundle's own ``kind`` / ``parent`` records,
never from the shape of the string, so ``*-T`` and letter-suffixed variants
(D-4-2K, F-2-7S) are classified by data, as CLAUDE.md requires. A ``target``
that the resolver inherited from a parent is never credited as a subcode.

The JS resolver cannot receive a UI payload code, so an example that carries
``payload_status_code`` is reported as ``not_equivalent_input`` for B2.
"""
from __future__ import annotations

import shutil
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

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
from waymaker_ai.evaluation.benchmark import payload_code_of, question_of

CLARIFYING_STEP_KINDS = frozenset({"question", "unresolved", "no-status", "need-status"})


def top_status(code: Optional[str], index: Mapping[str, Any]) -> Optional[str]:
    """Walk the bundle's parent chain to the record whose kind is ``status``."""
    seen = set()
    while code and code not in seen:
        seen.add(code)
        info = index.get(code)
        if not info:
            return None
        if info.get("kind") == "status":
            return code
        code = info.get("parent")
    return None


def derive_classification(raw: Mapping[str, Any], index: Mapping[str, Any]) -> Dict[str, Any]:
    codes: List[Mapping[str, Any]] = list(raw.get("codes") or [])
    first = codes[0] if codes else None
    explicit = raw.get("displayCode") or (first.get("code") if first and first.get("exact") else None)
    status: Optional[str] = None
    subcode: Optional[str] = None
    if explicit:
        info = index.get(explicit) or {}
        if info.get("kind") == "substatus":
            subcode = explicit
        status = top_status(explicit, index)
    if status is None:
        fallback = raw.get("target") or (first.get("code") if first else None)
        if isinstance(fallback, str):
            status = top_status(fallback.split("~")[0], index)
    target_status = first.get("code") if first and first.get("role") == "target" else None
    return {
        "status_code": status,
        "subcode": subcode,
        "procedure_fine": raw.get("procedure") or raw.get("stepProcedure") or None,
        "procedure_coarse": None,
        "current_status": raw.get("transitionFrom"),
        "target_status": target_status,
        "needs_clarification": raw.get("stepKind") in CLARIFYING_STEP_KINDS,
        "mentioned_codes": [c.get("code") for c in codes if c.get("code")],
    }


class B2Js(Baseline):
    name = "b2_js"
    kind = "deterministic"
    description = ("JS resolver: VisableStatusGuidance.interpret + search-router route + nextStep over "
                   "data/status-guidance-202609.json (fine 16-procedure taxonomy).")
    emits = {
        "status_procedure_classification": frozenset({
            "status_code", "subcode", "procedure_fine", "current_status", "target_status",
            "needs_clarification", "mentioned_codes",
        }),
        "entity_date_extraction": frozenset({"status_codes"}),
    }

    def available(self, ctx: RunContext) -> Tuple[bool, str]:
        if not ctx.node or not shutil.which(ctx.node):
            return False, "node not found"
        for rel in ("assets/js/status-guidance.js", "assets/js/search-router.js", "data/status-guidance-202609.json"):
            if not (ctx.repo_root / rel).is_file():
                return False, f"{rel} not found"
        return True, ""

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        results: Dict[str, ItemResult] = {}
        runnable = []
        for item in items:
            if payload_code_of(item.example):
                results[item.id] = ItemResult(item.id, "not_equivalent_input",
                                              error="the JS resolver cannot receive a payload status code")
            else:
                runnable.append(item)
        if not runnable:
            return results
        records = [{"id": item.id, "question": question_of(item.example)} for item in runnable]
        cmd = [str(shutil.which(ctx.node)), str(DRIVERS_DIR / "b2_driver.mjs"), str(ctx.repo_root)]
        try:
            outputs, info = run_jsonl(cmd, records, env=child_env(ctx), cwd=ctx.scratch_dir, timeout=ctx.timeout_seconds)
        except SubprocessFailure as exc:
            results.update({item.id: ItemResult(item.id, "error", error=str(exc)) for item in runnable})
            return results
        ctx.process_info.setdefault(self.name, {}).update(info)
        for out in outputs:
            out.setdefault("peak_memory_bytes", out.get("js_heap_used_bytes"))
        results.update(results_from_driver(runnable, outputs, self.convert, memory_kind="js_heap_used"))
        return results

    def convert(self, item: EvalItem, out: Mapping[str, Any]) -> Dict[str, Any]:
        derived = derive_classification(out["raw"], out.get("code_index") or {})
        if item.task == "entity_date_extraction":
            return {"dates": None, "status_codes": derived["mentioned_codes"]}
        return derived
