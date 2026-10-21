"""Shared baseline types, measurement helpers and the subprocess boundary.

Why a hard process boundary for backend baselines: the backend reads
environment variables (API keys, grounding mode, knowledge DB path) at import
time and keeps module-level caches. Importing it into the runner would let one
baseline's state leak into another's score, and would put real credentials in
reach of an evaluation. Backend baselines therefore run as child processes
with a minimal, explicit environment (no inherited variables, no keys,
``PYTHONHASHSEED=0``, ``WAYMAKER_KNOWLEDGE_DB=:memory:``), speak JSON lines on
stdin/stdout, and have their sockets disabled by the driver itself.
"""
from __future__ import annotations

import json
import subprocess
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

from waymaker_ai.evaluation.benchmark import LoadedBundle

DRIVERS_DIR = Path(__file__).resolve().parents[1] / "drivers"


@dataclass(frozen=True)
class EvalItem:
    example: Dict[str, Any]
    bundle: Optional[LoadedBundle] = None

    @property
    def id(self) -> str:
        return self.example["id"]

    @property
    def task(self) -> str:
        return self.example["task"]

    @property
    def split(self) -> str:
        return self.example["split"]


@dataclass
class ItemResult:
    example_id: str
    status: str                                   # ok | error | not_applicable | not_equivalent_input
    prediction: Optional[Dict[str, Any]] = None
    raw: Any = None
    error: str = ""
    latency_ms: Optional[float] = None
    upstream_calls: Optional[int] = None
    tokens: Optional[Dict[str, int]] = None
    peak_memory_bytes: Optional[int] = None
    memory_kind: str = "tracemalloc_peak"
    notes: List[str] = field(default_factory=list)


@dataclass
class RunContext:
    repo_root: Path
    backend_python: Path
    node: Optional[str]
    scratch_dir: Path
    timeout_seconds: float = 600.0
    cache: Dict[str, Any] = field(default_factory=dict)
    process_info: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    #: Tree whose ``backend/`` the backend baselines import; ``None`` means ``repo_root``.
    #: The JS baseline always reads ``repo_root`` (assets/js, data/).
    backend_root: Optional[Path] = None


class Baseline:
    """A system under evaluation. Subclasses fill the class attributes."""

    name: str = ""
    description: str = ""
    kind: str = "deterministic"                   # deterministic | model
    #: True when the baseline imports backend/ in a child process; the report then
    #: hashes the backend tree it ran against (--backend-root or the repo root).
    uses_backend: bool = False
    #: task -> normalized prediction fields this baseline produces
    emits: Mapping[str, FrozenSet[str]] = {}

    @property
    def tasks(self) -> FrozenSet[str]:
        return frozenset(self.emits)

    def available(self, ctx: RunContext) -> Tuple[bool, str]:
        return True, ""

    def run(self, items: Sequence[EvalItem], ctx: RunContext) -> Dict[str, ItemResult]:
        raise NotImplementedError

    def describe(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "kind": self.kind,
            "tasks": sorted(self.tasks),
            "emits": {task: sorted(fields) for task, fields in sorted(self.emits.items())},
        }


# ---------------------------------------------------------------------------
# In-process measurement
# ---------------------------------------------------------------------------
def measured(call: Callable[[], Any]) -> Tuple[Any, float, int]:
    """Run ``call`` and return (result, latency_ms, tracemalloc peak bytes)."""
    started_here = not tracemalloc.is_tracing()
    if started_here:
        tracemalloc.start()
    tracemalloc.reset_peak()
    t0 = time.perf_counter()
    try:
        result = call()
    finally:
        latency = (time.perf_counter() - t0) * 1000.0
        _current, peak = tracemalloc.get_traced_memory()
        if started_here:
            tracemalloc.stop()
    return result, round(latency, 3), int(peak)


# ---------------------------------------------------------------------------
# Subprocess boundary
# ---------------------------------------------------------------------------
class SubprocessFailure(Exception):
    pass


def child_env(ctx: RunContext, extra: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """The complete environment of a backend child process. Nothing is inherited."""
    safety = ctx.scratch_dir / "safety-log"
    safety.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(ctx.scratch_dir),
        "TMPDIR": str(ctx.scratch_dir),
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "WAYMAKER_KNOWLEDGE_DB": ":memory:",
        "WAYMAKER_SAFETY_LOG_DIR": str(safety),
        "LOG_LEVEL": "ERROR",
    }
    env.update(extra or {})
    return env


def run_jsonl(cmd: Sequence[str], records: Sequence[Mapping[str, Any]], *, env: Mapping[str, str], cwd: Path,
              timeout: float) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Send ``records`` as JSON lines, return (output objects, process info)."""
    payload = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            list(cmd), input=payload.encode("utf-8"), capture_output=True, env=dict(env), cwd=str(cwd),
            timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SubprocessFailure(f"driver timed out after {timeout:.0f}s") from exc
    wall_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    stderr = proc.stderr.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        raise SubprocessFailure(f"driver exited {proc.returncode}: {stderr[-1500:]}")
    outputs: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {}
    for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        obj = json.loads(line)
        if obj.get("_meta"):
            meta = obj
        else:
            outputs.append(obj)
    info = {"wall_ms": wall_ms, "returncode": proc.returncode, "stderr_bytes": len(proc.stderr)}
    info.update({k: v for k, v in meta.items() if k != "_meta"})
    return outputs, info


def results_from_driver(items: Sequence[EvalItem], outputs: Sequence[Mapping[str, Any]],
                        convert: Callable[[EvalItem, Mapping[str, Any]], Dict[str, Any]],
                        memory_kind: str = "tracemalloc_peak") -> Dict[str, ItemResult]:
    """Pair driver outputs with items by id and convert each to a prediction."""
    by_id = {str(o.get("id")): o for o in outputs}
    results: Dict[str, ItemResult] = {}
    for item in items:
        out = by_id.get(item.id)
        if out is None:
            results[item.id] = ItemResult(item.id, "error", error="driver returned no output for this item")
            continue
        if not out.get("ok"):
            results[item.id] = ItemResult(item.id, "error", raw=out.get("raw"), error=str(out.get("error") or "driver error"),
                                          latency_ms=out.get("latency_ms"), memory_kind=memory_kind)
            continue
        try:
            prediction = convert(item, out)
        except Exception as exc:  # a conversion bug must not hide as a wrong answer
            results[item.id] = ItemResult(item.id, "error", raw=out.get("raw"), error=f"conversion failed: {exc!r}")
            continue
        results[item.id] = ItemResult(
            item.id, "ok", prediction=prediction, raw=out.get("raw"),
            latency_ms=out.get("latency_ms"), upstream_calls=out.get("upstream_calls"),
            peak_memory_bytes=out.get("peak_memory_bytes"), memory_kind=memory_kind,
            notes=list(out.get("notes") or []),
        )
    return results
