"""The proposed deterministic B-fixed view of the actual backend subprocess."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from waymaker_ai.evaluation.baselines.b1_python import B1Python
from waymaker_ai.evaluation.baselines.base import EvalItem, ItemResult, RunContext


class BFixed(B1Python):
    name = "b_fixed"
    description = "Lossless explicit status and procedure detectors in the backend; no model calls."
    emits = {
        "status_procedure_classification": frozenset({
            "status_code", "subcode", "procedure_fine", "procedure_coarse",
            "current_status", "target_status", "needs_clarification", "mentioned_codes",
        }),
        "entity_date_extraction": frozenset({"dates", "status_codes"}),
    }

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        result = super().run(items, ctx)
        ctx.process_info.setdefault(self.name, {}).update(ctx.process_info.get("b1_python", {}))
        return result

    def convert(self, item: EvalItem, out: Mapping[str, Any]) -> Dict[str, Any]:
        prediction = super().convert(item, out)
        if item.task == "status_procedure_classification":
            # The backend emits the actual fine decision. A coarse label cannot
            # reconstruct card reissue, part-time work, or the kind of report.
            from waymaker_ai.contracts import FINE_TO_COARSE
            prediction["procedure_fine"] = out["raw"].get("procedure_fine")
            prediction["procedure_coarse"] = FINE_TO_COARSE.get(prediction["procedure_fine"])
        return prediction
