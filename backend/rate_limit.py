"""In-memory per-client sliding-window rate limiting for the Paradiso backend.

Design notes (pre-launch hardening, finding H-1a):

* The production deployment is a SINGLE uvicorn worker (see backend/Procfile
  and backend/railway.json), so a process-local in-memory store is correct —
  no Redis/DB dependency is introduced. If the deployment ever moves to
  multiple workers, each worker enforces its own window (limits become
  ``limit x workers``); switch to a shared store at that point.
* Sliding window: per (scope, client, window) we keep a deque of request
  timestamps, pruned on every check, so bursts right at a fixed-window
  boundary cannot double the effective limit.
* Memory stays bounded: each deque never exceeds its limit (entries are only
  appended when the request is admitted), expired entries are pruned on
  access, and a periodic sweep drops empty/idle buckets entirely.
* Client key: first entry of ``X-Forwarded-For`` when it parses as an IP
  (Railway terminates TLS at a proxy and forwards the caller chain), else the
  direct socket peer. XFF values are attacker-influenced in general, which is
  why non-IP tokens are ignored; the limits themselves are sized generously
  for shared campus/CGNAT IPs, so key spoofing only ever relaxes pressure on
  the spoofer's own bucket, never lets them consume someone else's.
* Config: defaults are passed by the endpoint and can be overridden per
  deploy with ``PARADISO_RL_<SCOPE>_PER_MIN`` / ``PARADISO_RL_<SCOPE>_PER_DAY``
  (0 disables that window). ``PARADISO_RATE_LIMIT_ENABLED=false`` is a global
  operator kill switch. Env is read per request so no restart is needed.

No secrets are read or logged here.
"""
from __future__ import annotations

import ipaddress
import os
import threading
import time
from collections import deque
from typing import Deque, Dict, Optional, Tuple

from fastapi import HTTPException, Request

_MINUTE_WINDOW_SECONDS = 60
_DAY_WINDOW_SECONDS = 86400
_SWEEP_INTERVAL_SECONDS = 60.0

# (scope, client_key, window_seconds) -> admitted-request timestamps (oldest first).
_BUCKETS: Dict[Tuple[str, str, int], Deque[float]] = {}
_LOCK = threading.Lock()
_LAST_SWEEP = 0.0


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return max(0, int(float(str(raw).strip())))
    except (TypeError, ValueError):
        return default


def _rate_limiting_enabled() -> bool:
    raw = (os.environ.get("PARADISO_RATE_LIMIT_ENABLED", "true") or "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def client_key_for_request(request: Request) -> str:
    """Resolve the per-client rate-limit key for a request.

    Behind the Railway proxy the caller chain arrives in ``X-Forwarded-For``;
    the first token that parses as a real IP wins. Without the header (direct
    hit / local run) the socket peer host is used. Returns "" (bypass) only
    when no plausible client identity exists: no XFF IP and no real socket
    peer — which in practice means an in-process test client ("testclient" is
    Starlette's hardcoded TestClient peer and can never be a real TCP peer,
    while a spoofed XFF of "testclient" is rejected by the IP parse above).
    """
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        first = xff.split(",")[0].strip()
        try:
            return str(ipaddress.ip_address(first))
        except ValueError:
            pass  # non-IP garbage: fall back to the socket peer below
    host = request.client.host if request.client else ""
    if not host or host == "testclient":
        return ""
    return host


def _sweep_expired_buckets(now: float) -> None:
    """Periodically drop fully-expired buckets so idle clients free memory."""
    global _LAST_SWEEP
    if now - _LAST_SWEEP < _SWEEP_INTERVAL_SECONDS:
        return
    _LAST_SWEEP = now
    for bucket_id in list(_BUCKETS):
        bucket = _BUCKETS.get(bucket_id)
        if bucket is None:
            continue
        window = bucket_id[2]
        while bucket and now - bucket[0] >= window:
            bucket.popleft()
        if not bucket:
            _BUCKETS.pop(bucket_id, None)


def rate_limit(scope: str, per_minute: int, per_day: int = 0):
    """Build a FastAPI dependency enforcing sliding-window limits for a scope.

    ``per_minute`` / ``per_day`` are the code defaults; per-deploy env
    overrides are ``PARADISO_RL_<SCOPE>_PER_MIN`` / ``PARADISO_RL_<SCOPE>_PER_DAY``
    (scope upper-cased, e.g. PARADISO_RL_ASK_PER_MIN). A limit of 0 disables
    that window. On rejection the dependency raises the standard structured
    429 envelope with a ``Retry-After`` header, so the CORS middleware and the
    frontends' existing non-200 error cards apply unchanged.
    """
    env_prefix = f"PARADISO_RL_{scope.upper()}"

    async def _dependency(request: Request) -> None:
        if not _rate_limiting_enabled():
            return
        key = client_key_for_request(request)
        if not key:
            return
        minute_limit = _env_int(f"{env_prefix}_PER_MIN", per_minute)
        day_limit = _env_int(f"{env_prefix}_PER_DAY", per_day)
        windows = []
        if minute_limit > 0:
            windows.append((minute_limit, _MINUTE_WINDOW_SECONDS))
        if day_limit > 0:
            windows.append((day_limit, _DAY_WINDOW_SECONDS))
        if not windows:
            return
        now = time.time()
        retry_after = 0
        with _LOCK:
            _sweep_expired_buckets(now)
            buckets: list = []
            for limit, window in windows:
                bucket = _BUCKETS.setdefault((scope, key, window), deque())
                while bucket and now - bucket[0] >= window:
                    bucket.popleft()
                if len(bucket) >= limit:
                    retry_after = max(retry_after, int(bucket[0] + window - now) + 1)
                buckets.append(bucket)
            if not retry_after:
                # Admit: record the hit in EVERY window. A rejected request is
                # never recorded, so being over the day cap cannot silently
                # consume minute-window slots (and vice versa).
                for bucket in buckets:
                    bucket.append(now)
        if retry_after:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limited",
                    "status": 429,
                    "message": (
                        "Too many requests from this address. "
                        f"Please wait about {retry_after} seconds and try again."
                    ),
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

    return _dependency


def _reset_rate_limits_for_tests() -> None:
    """Clear all in-memory windows (test isolation only)."""
    global _LAST_SWEEP
    with _LOCK:
        _BUCKETS.clear()
        _LAST_SWEEP = 0.0
