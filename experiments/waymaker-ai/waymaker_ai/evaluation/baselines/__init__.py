"""Registry of the systems the runner can evaluate.

Names are the ``--baselines`` values. Each factory returns a fresh instance so
that no baseline shares state with another between runs.
"""
from __future__ import annotations

from typing import Callable, Dict, List

from waymaker_ai.evaluation.baselines.b1_python import B1Python, B1PythonRaw
from waymaker_ai.evaluation.baselines.b2_js import B2Js
from waymaker_ai.evaluation.baselines.base import Baseline
from waymaker_ai.evaluation.baselines.existing_law import ExistingLaw
from waymaker_ai.evaluation.baselines.model import MockModel, OpenAICompatible
from waymaker_ai.evaluation.baselines.wlie import Wlie

BASELINES: Dict[str, Callable[[], Baseline]] = {
    "b1_python": B1Python,
    "b1_python_raw": B1PythonRaw,
    "b2_js": B2Js,
    "existing_law": ExistingLaw,
    "wlie": Wlie,
    "mock_model": MockModel,
    "openai_compatible": OpenAICompatible,
}


def create(names: List[str]) -> List[Baseline]:
    unknown = [name for name in names if name not in BASELINES]
    if unknown:
        raise KeyError(f"unknown baseline(s): {', '.join(unknown)}; known: {', '.join(sorted(BASELINES))}")
    return [BASELINES[name]() for name in names]
