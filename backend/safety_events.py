"""Waymaker Trust & Safety — minimal, data-minimized safety event logging.

When the guardrail blocks / escalates a request, we record a small internal
event so the team can review patterns of abuse. The design follows strict data
minimization and stays entirely local:

- **No external transmission.** Events are never sent to email, webhooks,
  Slack, Kakao, police, immigration, or any government system. They are only
  appended to a server-controlled JSONL file and kept in a small in-memory ring.
- **No raw conversation.** Only a short, redacted excerpt of the *current*
  request is stored — never the full history.
- **Redaction first.** Likely passport numbers, alien-registration / resident
  numbers, phone numbers, emails, long numeric IDs, and detectable addresses
  are masked before anything is written.
- **Never fatal.** Logging failures (read-only FS, etc.) degrade to the
  in-memory ring and a warning; they never break ``/api/ask``.

The log location is controlled by ``WAYMAKER_SAFETY_LOG_DIR`` (defaults to
``backend/var/safety_events`` which is git-ignored). Reading these records is a
manual, server-side operation — there is intentionally no network endpoint and
no automatic reporting (see docs/safety/WAYMAKER_TRUST_AND_SAFETY.md).
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Sequence

logger = logging.getLogger("paradiso.safety")

SAFETY_EVENTS_VERSION = "waymaker-safety-events-1"

_DEFAULT_LOG_DIR = Path(__file__).resolve().parent / "var" / "safety_events"
_LOG_FILE_NAME = "safety_events.jsonl"
_EXCERPT_MAX_CHARS = 240
_MEMORY_RING_MAX = 200

# Bounded in-memory ring of the most recent events (redacted). Used for tests
# and for a possible future, properly-authenticated admin view. Never holds raw
# input beyond the same redacted excerpt written to disk.
_RECENT_EVENTS: Deque[Dict[str, Any]] = deque(maxlen=_MEMORY_RING_MAX)


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------
# Order matters: structured identifiers (email, resident/alien number, passport)
# are masked before the generic phone / long-number passes so the specific
# label is preferred over a generic [NUMBER].
_REDACTORS = (
    # Emails.
    ("[EMAIL]", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    # Resident registration / alien registration number: 6 digits - 7 digits.
    ("[ID_NUMBER]", re.compile(r"\b\d{6}\s*[-–]\s*\d{7}\b")),
    # Same, without separator (13 consecutive digits).
    ("[ID_NUMBER]", re.compile(r"\b\d{13}\b")),
    # Passport-like: 1-2 letters followed by 7-8 digits (e.g. M12345678).
    ("[PASSPORT]", re.compile(r"\b[A-Za-z]{1,2}\d{7,8}\b")),
    # Korean mobile / landline with separators (010-1234-5678, 02 123 4567).
    ("[PHONE]", re.compile(r"\b0\d{1,2}\s*[-.\s]\s*\d{3,4}\s*[-.\s]\s*\d{4}\b")),
    # International / +country phone forms (+82 10 1234 5678).
    ("[PHONE]", re.compile(r"\+\d{1,3}[\s\-]?\d{1,2}[\s\-]?\d{3,4}[\s\-]?\d{4}\b")),
    # Bare 10-11 digit phone run (01012345678).
    ("[PHONE]", re.compile(r"\b0\d{9,10}\b")),
    # Any remaining long numeric id (8+ digits).
    ("[NUMBER]", re.compile(r"\b\d{8,}\b")),
    # Detectable Korean street addresses: "...로/길 123(-45)" road-name addresses.
    ("[ADDRESS]", re.compile(r"[가-힣A-Za-z0-9]+(?:로|길)\s*\d+(?:[-–]\d+)?(?:번길)?\s*\d*")),
    # Korean administrative address chains: "...시 ...구 ...동".
    ("[ADDRESS]", re.compile(r"[가-힣]+\s*(?:특별시|광역시|시|도)\s*[가-힣]+\s*(?:시|군|구)\s*[가-힣]+\s*(?:읍|면|동|리)")),
    # English street addresses: "123 Main St / Street / Ave / Road".
    ("[ADDRESS]", re.compile(r"\b\d{1,5}\s+[A-Za-z0-9.\s]{2,40}\b(?:Street|St|Avenue|Ave|Road|Rd|Blvd|Lane|Ln|Drive|Dr)\b", re.IGNORECASE)),
)


def redact(text: str) -> str:
    """Mask likely personal identifiers. Conservative and order-sensitive.

    Always returns a string; never raises.
    """
    if not text:
        return ""
    try:
        out = str(text)
        for replacement, pattern in _REDACTORS:
            out = pattern.sub(replacement, out)
        return out
    except Exception:  # pragma: no cover - redaction must never throw
        return "[REDACTION_ERROR]"


def redacted_excerpt(text: str, max_chars: int = _EXCERPT_MAX_CHARS) -> str:
    """Redact, collapse whitespace, and truncate to a short excerpt."""
    cleaned = re.sub(r"\s+", " ", redact(text or "")).strip()
    if len(cleaned) > max_chars:
        return cleaned[:max_chars].rstrip() + "…"
    return cleaned


# ---------------------------------------------------------------------------
# Event recording
# ---------------------------------------------------------------------------
def _log_dir() -> Path:
    configured = os.environ.get("WAYMAKER_SAFETY_LOG_DIR", "").strip()
    return Path(configured) if configured else _DEFAULT_LOG_DIR


def _log_file() -> Path:
    return _log_dir() / _LOG_FILE_NAME


def build_event(
    *,
    action: str,
    category: str,
    severity: int,
    reason: str,
    matched_signals: Sequence[str],
    input_text: str,
    language: str = "",
    route: str = "",
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble a redacted, data-minimized event record (no disk I/O)."""
    return {
        "event_id": uuid.uuid4().hex,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "action": str(action or ""),
        "category": str(category or ""),
        "severity": int(severity or 0),
        "reason": str(reason or ""),
        # Pattern labels only — never raw user text.
        "matched_signals": list(matched_signals or []),
        # Short, redacted excerpt of ONLY the current request.
        "input_excerpt": redacted_excerpt(input_text),
        "language": str(language or ""),
        "route": str(route or ""),
        "request_id": str(request_id) if request_id else "",
        "safety_version": SAFETY_EVENTS_VERSION,
    }


def log_safety_event(
    *,
    action: str,
    category: str,
    severity: int,
    reason: str,
    matched_signals: Sequence[str],
    input_text: str,
    language: str = "",
    route: str = "",
    request_id: Optional[str] = None,
) -> str:
    """Record one safety event. Returns the event_id. Never raises.

    The event is appended to the JSONL log (best effort) and always pushed to
    the in-memory ring so a disk failure still leaves an auditable trace for the
    life of the process.
    """
    event = build_event(
        action=action,
        category=category,
        severity=severity,
        reason=reason,
        matched_signals=matched_signals,
        input_text=input_text,
        language=language,
        route=route,
        request_id=request_id,
    )
    _RECENT_EVENTS.append(event)

    try:
        directory = _log_dir()
        directory.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False)
        with open(directory / _LOG_FILE_NAME, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception as exc:  # pragma: no cover - disk issues must not break /api/ask
        logger.warning("safety event persistence failed (kept in memory): %s", exc)

    # Structured, non-secret log line for ops visibility (excerpt already redacted).
    logger.info(
        "safety_event action=%s category=%s severity=%s id=%s route=%s",
        event["action"], event["category"], event["severity"], event["event_id"], event["route"],
    )
    return event["event_id"]


def recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Most-recent in-memory events (already redacted). For tests/manual review."""
    if limit <= 0:
        return []
    return list(_RECENT_EVENTS)[-limit:]


def _reset_events_for_tests() -> None:
    _RECENT_EVENTS.clear()
