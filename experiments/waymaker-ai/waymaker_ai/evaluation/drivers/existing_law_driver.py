"""Existing-law baseline driver: the backend's own law grounding, one claim per line.

Runs in the BACKEND interpreter as a child of the evaluation runner, never in
the runner's process. Reads JSON lines ``{"id", "question", "bundle_path",
"reference_date"}`` on stdin and writes one JSON line per item on stdout.

What is measured: ``services.law_grounding.build_law_grounding_context`` with
the claim text as the question, i.e. the same path ``/api/ask`` takes to verify
question-cited articles (search planning, ``law_tools.search_laws``,
``_verify_requested_articles`` → ``law_tools.get_law_detail``).

How the source bundle reaches it: ``urllib.request.urlopen`` and
``urllib.request.OpenerDirector.open`` (which every ``build_opener()`` opener
uses) are replaced by a fake that answers from
``waymaker_ai.evaluation.fake_drf.FakeDrfServer``. The backend's real transport
(``_default_transport`` → scheme fallback → ``_http_get_once``) and its real
parsers stay in the call path, so a timeout is a raised
``URLError(socket.timeout)``, HTTP 429 is a raised ``HTTPError``, and an HTML or
malformed body is a 200 the backend must parse. The grounding config is
replaced by one with a placeholder credential (never a real key) so the
lookups run at all; sockets are disabled before the backend is imported.

Why both hooks, and why blocked connections are counted: a backend that moves
from ``urlopen`` to its own opener would otherwise bypass the fake, hit the
disabled socket, and report every law as unavailable, which looks like a
backend that never declares a false absence. Every blocked connection attempt
is counted per item (``blocked_network_attempts``); the baseline turns an item
with any into an ``error``, so a harness gap is never scored as an answer.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import io
import json
import os
import socket
import sys
import time
import tracemalloc
from typing import Any, Dict, List

#: Not a credential: the fake transport answers every request, and sockets are off.
PLACEHOLDER_OC = "offline-evaluation-placeholder"

#: Request parameters copied into the per-call log. ``OC`` is never among them.
_RECORDED_PARAMS = ("target", "query", "MST", "ID", "gana", "sort", "page")


#: One entry per socket connection the backend attempted while sockets are disabled.
_BLOCKED_ATTEMPTS: List[str] = []


def _block_network() -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        _BLOCKED_ATTEMPTS.append("connect")
        raise OSError("network disabled by the evaluation driver")

    socket.socket.connect = refuse  # type: ignore[assignment]
    socket.socket.connect_ex = refuse  # type: ignore[assignment]
    socket.create_connection = refuse  # type: ignore[assignment]


class _FakeHttpResponse:
    def __init__(self, body: str, status: int) -> None:
        self._raw = body.encode("utf-8")
        self.status = status
        self.code = status

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, *_exc: Any) -> None:
        return None


class _Recorder:
    """The fake urlopen for one item. Each call is one upstream call."""

    def __init__(self, server: Any) -> None:
        self.server = server
        self.calls: List[Dict[str, Any]] = []

    def urlopen(self, request: Any, timeout: float = 0.0, **_kwargs: Any) -> Any:
        import urllib.error

        from urllib.parse import parse_qsl, urlsplit

        url = request.full_url if hasattr(request, "full_url") else str(request)
        reply = self.server.respond(url)
        params = dict(parse_qsl(urlsplit(url).query))
        # Only non-secret request parameters are recorded (never OC).
        shown = {key: params[key] for key in _RECORDED_PARAMS if params.get(key)}
        self.calls.append({"operation": reply.operation, "event": reply.event, "status": reply.status,
                           "fault": reply.fault, "params": shown})
        if reply.event == "http_error":
            raise urllib.error.HTTPError(url, reply.status, "evaluation fault", None, io.BytesIO(b""))
        if reply.event == "timeout":
            raise urllib.error.URLError(socket.timeout("timed out"))
        if reply.event == "network":
            raise urllib.error.URLError(ConnectionRefusedError(61, "Connection refused"))
        return _FakeHttpResponse(reply.body, reply.status)


def _trim(context: Dict[str, Any]) -> Dict[str, Any]:
    """Keep the verification outcome; replace law text by its hash (the report stays small)."""
    verification = context.get("citation_verification") or {}
    citations = []
    for item in verification.get("citations") or []:
        snippet = str(item.get("snippet") or "")
        citations.append({
            "raw": item.get("raw"),
            "law_name": item.get("law_name"),
            "article": item.get("article") or item.get("article_or_clause"),
            "verification_status": item.get("verification_status"),
            "warnings": list(item.get("warnings") or []),
            "article_title": item.get("article_title"),
            "snippet_sha256": hashlib.sha256(snippet.encode("utf-8")).hexdigest() if snippet else None,
        })
    return {
        "attempted": bool(context.get("attempted")),
        "intent_reasons": list(context.get("intent_reasons") or []),
        "law_search_queries": list(context.get("law_search_queries") or []),
        "law_grounding_used": bool(context.get("law_grounding_used")),
        "law_grounding_names": sorted({str(r.get("law_name") or "") for r in context.get("law_grounding") or []}),
        "citation_verification": {
            "status": verification.get("status"),
            "citation_specific": bool(verification.get("citation_specific")),
            "warnings": list(verification.get("warnings") or []),
            "citations": citations,
        },
        "grounding_warnings": list(context.get("grounding_warnings") or []),
        "error_type": context.get("error_type") or "",
    }


class _ArticleTracker:
    """Tells the fake server which article the backend is looking up.

    The backend fetches a whole law and filters the cited article locally, so
    the article never appears in a request URL. Wrapping
    ``law_tools.get_law_detail`` (keyword-only) is the one place the article is
    visible; the fake uses it to serve a provision-specific bundle fault.
    """

    def __init__(self, original: Any) -> None:
        self.original = original
        self.server: Any = None

    def __call__(self, **kwargs: Any) -> Any:
        if self.server is not None:
            self.server.requested_article = str(kwargs.get("article") or "") or None
        try:
            return self.original(**kwargs)
        finally:
            if self.server is not None:
                self.server.requested_article = None


def main() -> int:
    backend_dir, experiment_root = sys.argv[1], sys.argv[2]
    _block_network()
    sys.path.insert(0, backend_dir)
    sys.path.append(experiment_root)  # appended: never shadows a backend module
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(sys.stderr):  # stdout carries only JSON lines
        import urllib.request  # noqa: E402

        from services import law_cloud_fallback as lcf  # noqa: E402
        from services import law_grounding as lg  # noqa: E402
        from services import law_tools as lt  # noqa: E402
        from services.citation_verifier import extract_korean_legal_citations  # noqa: E402
        from services.grounding_config import GroundingConfig  # noqa: E402
        from waymaker_ai.evaluation.fake_drf import FakeDrfServer  # noqa: E402
    import_ms = round((time.perf_counter() - t0) * 1000.0, 1)

    config = GroundingConfig(law_api_oc=PLACEHOLDER_OC, mode="enabled", timeout_seconds=5.0,
                             total_budget_seconds=120.0)
    lg.load_grounding_config = lambda: config  # type: ignore[assignment]
    lt.load_grounding_config = lambda: config  # type: ignore[assignment]
    tracker = _ArticleTracker(lt.get_law_detail)
    lt.get_law_detail = tracker  # type: ignore[assignment]

    current: Dict[str, Any] = {"recorder": None}

    def routed_open(_opener: Any, fullurl: Any, data: Any = None, timeout: Any = None, **_kwargs: Any) -> Any:
        """Any urllib opener (``build_opener().open``) is answered by the current item's fake."""
        recorder = current["recorder"]
        if recorder is None:
            raise OSError("network disabled by the evaluation driver (no item in progress)")
        return recorder.urlopen(fullurl, timeout=timeout or 0.0)

    urllib.request.OpenerDirector.open = routed_open  # type: ignore[assignment]

    bundles: Dict[str, Any] = {}
    tracemalloc.start()
    for line in sys.stdin:
        if not line.strip():
            continue
        record = json.loads(line)
        try:
            path = record["bundle_path"]
            if path not in bundles:
                with open(path, encoding="utf-8") as handle:
                    bundles[path] = json.load(handle)
            reference = dt.date.fromisoformat(record["reference_date"]) if record.get("reference_date") else None
            server = FakeDrfServer(bundles[path], reference)
            tracker.server = server
            recorder = _Recorder(server)
            current["recorder"] = recorder
            _BLOCKED_ATTEMPTS.clear()
            # The cloud fallback caches listing pages per process for 15 minutes;
            # without this, one item would be answered from another item's bundle.
            page_cache = getattr(lcf, "_PAGE_CACHE", None)
            if hasattr(page_cache, "clear"):
                page_cache.clear()
            urllib.request.urlopen = recorder.urlopen  # type: ignore[assignment]
            tracemalloc.reset_peak()
            started = time.perf_counter()
            with contextlib.redirect_stdout(sys.stderr):
                context = lg.build_law_grounding_context(record["question"])
            latency = (time.perf_counter() - started) * 1000.0
            _cur, peak = tracemalloc.get_traced_memory()
            raw = _trim(context)
            raw["extracted_citations"] = len(extract_korean_legal_citations(record["question"]).get("citations") or [])
            raw["unexercised_fault_operations"] = server.unexercised_faults()
            raw["fixture_partial_versions"] = sorted(server.partial_versions)
            raw["blocked_network_attempts"] = len(_BLOCKED_ATTEMPTS)
            out = {"id": record["id"], "ok": True, "raw": raw, "latency_ms": round(latency, 3),
                   "peak_memory_bytes": int(peak), "upstream_calls": len(recorder.calls), "calls": recorder.calls}
        except Exception as exc:  # report, never crash the batch
            out = {"id": record.get("id"), "ok": False, "error": f"{type(exc).__name__}: {exc}"[:500]}
        sys.stdout.write(json.dumps(out, ensure_ascii=False, default=str) + "\n")
    sys.stdout.write(json.dumps({
        "_meta": True,
        "import_ms": import_ms,
        "python": sys.version.split()[0],
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "law_tool_layer_version": getattr(lt, "LAW_TOOL_LAYER_VERSION", None),
    }) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
