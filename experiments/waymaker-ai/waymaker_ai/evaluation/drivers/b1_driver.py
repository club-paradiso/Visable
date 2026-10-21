"""B1 baseline driver: the backend's deterministic detectors, one question per line.

Runs in the BACKEND interpreter as a child of the evaluation runner, never
inside the runner's process. Reads JSON lines ``{"id", "question",
"payload_status_code"}`` on stdin and writes one JSON line per item on stdout.

Recipe (docs/ai/waymaker-genesis/research-notes/status-classifier.md §9):
``paradiso_backend._detect_visa_codes(payload, None, q)`` +
``_detect_task_type(q)`` + ``services.knowledge.understanding.understand``.
Also recorded, because they are part of the same deterministic stack:
``legal_analysis.extract_immigration_facts`` (current / previous / target
status) and ``immigration_tools.extract_immigration_facts`` (dates).

Sockets are disabled before the backend is imported, so a code path that
tried to reach the network fails loudly instead of silently. Anything the
backend prints goes to stderr: stdout carries only the JSON lines.
"""
from __future__ import annotations

import contextlib
import json
import os
import socket
import sys
import time
import tracemalloc
from typing import Any, Dict

#: Run once before the first item and never scored. Its only job is to pay
#: the backend's lazy initialisation outside every item's latency.
WARMUP_QUESTION = "warm-up: D-2 체류기간 연장"


def _block_network() -> None:
    def refuse(*_args, **_kwargs):
        raise OSError("network disabled by the evaluation driver")

    socket.socket.connect = refuse  # type: ignore[assignment]
    socket.socket.connect_ex = refuse  # type: ignore[assignment]
    socket.create_connection = refuse  # type: ignore[assignment]


def main() -> int:
    backend_dir = sys.argv[1]
    _block_network()
    sys.path.insert(0, backend_dir)
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(sys.stderr):  # stdout carries only JSON lines
        import paradiso_backend as pb  # noqa: E402  (registers the detectors)
        from services import immigration_tools as it  # noqa: E402
        from services import legal_analysis as la  # noqa: E402
        from services.knowledge.models import TASK_TYPE_TO_PROCEDURE  # noqa: E402
        from services.knowledge.understanding import understand  # noqa: E402
    import_ms = round((time.perf_counter() - t0) * 1000.0, 1)

    def detect(question: str, payload: Any) -> Dict[str, Any]:
        top, sub = pb._detect_visa_codes(payload, None, question)
        task = pb._detect_task_type(question)
        risk = pb._risk_level_for_task(task)
        understood = understand(question, status_code=top, subcode=sub, task_type=task, risk_level=risk).to_dict()
        facts = la.extract_immigration_facts(question)
        tool_facts = it.extract_immigration_facts(question)
        return {
            "raw_status": top,
            "raw_subcode": sub,
            "raw_task_type": task,
            "raw_procedure": TASK_TYPE_TO_PROCEDURE.get(task or ""),
            "risk_level": risk,
            "status_code": understood.get("status_code"),
            "subcode": understood.get("subcode"),
            "procedure": understood.get("procedure"),
            "intent": understood.get("intent"),
            "ambiguity": understood.get("ambiguity"),
            "missing_decisive_facts": understood.get("missing_decisive_facts"),
            "mentioned_statuses": understood.get("mentioned_statuses"),
            "la_current_status": facts.get("current_status"),
            "la_previous_status": facts.get("previous_status"),
            "la_target_status": facts.get("target_status"),
            "la_transition_detected": facts.get("status_transition_detected"),
            "it_dates": tool_facts.get("dates"),
            "it_status_codes": tool_facts.get("statusCodes"),
        }

    # One fixed warm-up call (not a benchmark item) so that lazy initialisation
    # inside the backend is not charged to whichever item happens to come first.
    t1 = time.perf_counter()
    with contextlib.redirect_stdout(sys.stderr):
        detect(WARMUP_QUESTION, None)
    warmup_ms = round((time.perf_counter() - t1) * 1000.0, 1)

    tracemalloc.start()
    for line in sys.stdin:
        if not line.strip():
            continue
        record = json.loads(line)
        tracemalloc.reset_peak()
        started = time.perf_counter()
        try:
            with contextlib.redirect_stdout(sys.stderr):
                raw = detect(record["question"], record.get("payload_status_code"))
            latency = (time.perf_counter() - started) * 1000.0
            _cur, peak = tracemalloc.get_traced_memory()
            out = {"id": record["id"], "ok": True, "raw": raw, "latency_ms": round(latency, 3),
                   "peak_memory_bytes": int(peak), "upstream_calls": 0}
        except Exception as exc:  # report, never crash the batch
            out = {"id": record["id"], "ok": False, "error": f"{type(exc).__name__}: {exc}"[:500]}
        sys.stdout.write(json.dumps(out, ensure_ascii=False, default=str) + "\n")
    sys.stdout.write(json.dumps({
        "_meta": True,
        "import_ms": import_ms,
        "warmup_ms": warmup_ms,
        "python": sys.version.split()[0],
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "hash_randomization": sys.flags.hash_randomization,
    }) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
