"""B1: the backend's deterministic Python detectors (the /api/ask contract).

Two views of one subprocess run:

* ``b1_python`` scores ``understand()``: what the knowledge plan and the
  backend eval consume. Its status may be a parent filled in from a mentioned
  subcode (understanding.py "single parent family" rule); its subcode comes
  only from a payload, never from text.
* ``b1_python_raw`` scores ``_detect_visa_codes`` + ``_detect_task_type``
  mapped through ``TASK_TYPE_TO_PROCEDURE``: what /api/ask grounding uses.

Procedures are COARSE (the backend taxonomy), so fine-procedure accuracy is
not scorable for B1 by construction. ``current_status`` / ``target_status``
are ``legal_analysis.extract_immigration_facts`` read literally: on main a
planned "D-10에서 E-7-1로" change reports ``current_status = E-7-1``
(research-notes/status-classifier.md §11), and the runner scores what the
backend says, not what it meant. Dates come without a role, so only
value-level date metrics are scorable for B1.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

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

_CACHE_KEY = "b1_python_driver_outputs"
_TASKS = ("status_procedure_classification", "entity_date_extraction")


def backend_dir(ctx: RunContext) -> Path:
    """The ``backend/`` the drivers import: under ``--backend-root`` when given, else under the repo root."""
    return (ctx.backend_root or ctx.repo_root) / "backend"


def backend_available(ctx: RunContext) -> Tuple[bool, str]:
    if not ctx.backend_python.is_file():
        return False, f"backend interpreter not found: {ctx.backend_python}"
    if not (backend_dir(ctx) / "paradiso_backend.py").is_file():
        return False, f"{backend_dir(ctx) / 'paradiso_backend.py'} not found"
    return True, ""


def _driver_outputs(items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, Dict[str, Any]]:
    """Run the driver once per runner invocation and share it between views."""
    cached: Dict[str, Dict[str, Any]] = ctx.cache.setdefault(_CACHE_KEY, {})
    missing = [item for item in items if item.id not in cached]
    if missing:
        records = [{"id": item.id, "question": question_of(item.example),
                    "payload_status_code": payload_code_of(item.example)} for item in missing]
        cmd = [str(ctx.backend_python), "-B", "-s", "-W", "ignore", str(DRIVERS_DIR / "b1_driver.py"),
               str(backend_dir(ctx))]
        env = child_env(ctx, {"LAW_GROUNDING_MODE": "disabled"})
        outputs, info = run_jsonl(cmd, records, env=env, cwd=ctx.scratch_dir, timeout=ctx.timeout_seconds)
        ctx.process_info.setdefault("b1_python", {}).update(info)
        for out in outputs:
            cached[str(out.get("id"))] = out
    return cached


class _B1Base(Baseline):
    kind = "deterministic"
    uses_backend = True

    def available(self, ctx: RunContext) -> Tuple[bool, str]:
        return backend_available(ctx)

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        try:
            outputs = _driver_outputs(items, ctx)
        except SubprocessFailure as exc:
            return {item.id: ItemResult(item.id, "error", error=str(exc)) for item in items}
        return results_from_driver(items, [outputs.get(item.id, {"id": item.id}) for item in items], self.convert)

    def convert(self, item: EvalItem, out: Mapping[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class B1Python(_B1Base):
    name = "b1_python"
    description = ("Backend deterministic detectors: _detect_visa_codes + _detect_task_type + "
                   "knowledge.understanding.understand (status/subcode/coarse procedure), legal_analysis "
                   "facts for current/target, immigration_tools dates (value only).")
    emits = {
        "status_procedure_classification": frozenset({
            "status_code", "subcode", "procedure_coarse", "current_status", "target_status",
            "needs_clarification", "mentioned_codes",
        }),
        "entity_date_extraction": frozenset({"dates", "status_codes"}),
    }

    def convert(self, item: EvalItem, out: Mapping[str, Any]) -> Dict[str, Any]:
        raw = out["raw"]
        if item.task == "entity_date_extraction":
            # immigration_tools extracts calendar dates without a role.
            return {"dates": [{"value": d, "role": None} for d in raw.get("it_dates") or []],
                    "status_codes": list(raw.get("mentioned_statuses") or [])}
        return {
            "status_code": raw.get("status_code"),
            "subcode": raw.get("subcode"),
            "procedure_fine": None,
            "procedure_coarse": raw.get("procedure"),
            "current_status": raw.get("la_current_status"),
            "target_status": raw.get("la_target_status"),
            "needs_clarification": raw.get("ambiguity") not in (None, "clear"),
            "mentioned_codes": list(raw.get("mentioned_statuses") or []),
        }


class B1PythonRaw(_B1Base):
    name = "b1_python_raw"
    description = ("Backend raw detectors only, as /api/ask grounding uses them: _detect_visa_codes "
                   "(text path never yields a subcode) + _detect_task_type via TASK_TYPE_TO_PROCEDURE.")
    emits = {"status_procedure_classification": frozenset({"status_code", "subcode", "procedure_coarse"})}

    def convert(self, item: EvalItem, out: Mapping[str, Any]) -> Dict[str, Any]:
        raw = out["raw"]
        return {
            "status_code": raw.get("raw_status"),
            "subcode": raw.get("raw_subcode"),
            "procedure_fine": None,
            "procedure_coarse": raw.get("raw_procedure"),
            "current_status": None,
            "target_status": None,
            "needs_clarification": None,
            "mentioned_codes": [],
        }


def default_backend_python(repo_root: Path) -> Path:
    """``WAYMAKER_EVAL_BACKEND_PYTHON``, else ``<repo>/.venv-check/bin/python``, else this interpreter.

    The backend interpreter only ever runs a driver in a child process; it is
    never imported into the runner.
    """
    configured = os.environ.get("WAYMAKER_EVAL_BACKEND_PYTHON")
    if configured:
        return Path(configured)
    candidate = repo_root / ".venv-check" / "bin" / "python"
    return candidate if candidate.is_file() else Path(sys.executable)
