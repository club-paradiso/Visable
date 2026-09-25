"""Privacy-minimized representation of production questions.

What the learning loop keeps about a question, by default:

* normalized features (status, sub-code, procedure, intent, coverage, reason);
* a SANITIZED, truncated excerpt (<= 200 chars) — identifiers masked with the
  same redactor the Trust & Safety log uses (``safety_events.redact``), plus
  names and health / financial narrative markers masked here;
* a fingerprint of the sanitized text (dedup / counting without re-reading).

Never kept: raw text, conversation history, the generated answer, IP or any
client identifier. Retention is bounded (``expires_at``) and purgeable.

Environment:
    WAYMAKER_QUERY_TEXT_RETENTION   'sanitized' (default) | 'none'
    WAYMAKER_OBSERVATION_RETENTION_DAYS   default 90
    WAYMAKER_KNOWLEDGE_OBSERVATIONS  '1' (default) | '0' disables recording
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timedelta, timezone

from safety_events import redact

EXCERPT_MAX = 200

_EXTRA_REDACTORS = (
    ("[NAME]", re.compile(r"(?:제\s*이름은|저는|본인은)\s*[가-힣]{2,4}(?:입니다|이고|이며|이에요|예요)")),
    ("[NAME]", re.compile(r"\b(?:my name is|i am|i'm)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", re.IGNORECASE)),
    ("[HEALTH]", re.compile(r"HIV|에이즈|암\s*진단|정신과|우울증|임신\s*\d+\s*주|진단명|병명|disease|diagnos\w+|pregnan\w+",
                            re.IGNORECASE)),
    ("[AMOUNT]", re.compile(r"\d[\d,]*\s*(?:만\s*)?원|\$\s?\d[\d,]*|\d[\d,]*\s*(?:won|krw|usd)", re.IGNORECASE)),
    ("[ACCOUNT]", re.compile(r"\b\d{2,6}-\d{2,6}-\d{2,8}\b")),
)


def text_retention_enabled() -> bool:
    return os.environ.get("WAYMAKER_QUERY_TEXT_RETENTION", "sanitized").strip().lower() != "none"


def observations_enabled() -> bool:
    return os.environ.get("WAYMAKER_KNOWLEDGE_OBSERVATIONS", "1").strip().lower() not in ("0", "false", "off", "no")


def retention_days() -> int:
    try:
        return max(1, int(os.environ.get("WAYMAKER_OBSERVATION_RETENTION_DAYS", "90")))
    except ValueError:
        return 90


def sanitize(text: str, max_chars: int = EXCERPT_MAX) -> str:
    """Redact identifiers, then collapse and truncate. Never raises."""
    try:
        out = redact(str(text or ""))
        for token, pattern in _EXTRA_REDACTORS:
            out = pattern.sub(token, out)
        out = re.sub(r"\s+", " ", out).strip()
        if len(out) > max_chars:
            out = out[:max_chars].rstrip() + "…"
        return out
    except Exception:  # pragma: no cover
        return ""


def stored_excerpt(text: str) -> str:
    return sanitize(text) if text_retention_enabled() else ""


def fingerprint(text: str) -> str:
    norm = re.sub(r"\s+", " ", sanitize(text, 1000)).strip().lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:24] if norm else ""


def expiry(now: datetime | None = None) -> str:
    base = now or datetime.now(timezone.utc)
    return (base + timedelta(days=retention_days())).strftime("%Y-%m-%dT%H:%M:%SZ")
