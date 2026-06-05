"""Runtime accessor for the structured manual-evidence requirements.

This module exposes the structured requirements layer
(`backend/data/manual_grounding/structured_requirements_2026_06_01.json`) to
the backend at runtime.

Safety policy (critical):
  Only entries that are BOTH ``confidence == "HIGH"`` AND
  ``readinessLabel == "STRUCTURED_EVIDENCE_READY"`` are "source-confirmed"
  and may be surfaced to user-facing answers/API. Every other entry is
  candidate evidence pending human review and must stay hidden from
  user-facing paths. The default of every public accessor here is to return
  ONLY source-confirmed entries; needs-review entries are returned only when
  an explicit internal option is passed.

The loader is defensive: if the file is missing or malformed the module
returns empty results rather than raising, so the backend never fails to
start because of this optional data.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_STRUCTURED_FILE = os.path.join(
    _HERE, "data", "manual_grounding", "structured_requirements_2026_06_01.json"
)

# A source-confirmed entry must satisfy BOTH of these.
SOURCE_CONFIRMED_CONFIDENCE = "HIGH"
SOURCE_CONFIRMED_READINESS = "STRUCTURED_EVIDENCE_READY"

_lock = threading.Lock()
_cache: Optional[Dict[str, Any]] = None


def _structured_path() -> str:
    override = os.environ.get("STRUCTURED_REQUIREMENTS_PATH", "").strip()
    return override or _STRUCTURED_FILE


def _load_raw() -> Dict[str, Any]:
    """Load and cache the structured requirements file (defensive)."""
    global _cache
    if _cache is not None:
        return _cache
    with _lock:
        if _cache is not None:
            return _cache
        data: Dict[str, Any]
        try:
            with open(_structured_path(), "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            entries = loaded.get("entries") if isinstance(loaded, dict) else None
            if not isinstance(entries, list):
                entries = []
            data = {"raw": loaded if isinstance(loaded, dict) else {}, "entries": entries}
        except (OSError, json.JSONDecodeError):
            data = {"raw": {}, "entries": []}
        _cache = data
        return _cache


def reset_cache_for_tests() -> None:
    """Clear the module cache (used by tests that swap the data path)."""
    global _cache
    with _lock:
        _cache = None


def is_source_confirmed(entry: Dict[str, Any]) -> bool:
    """True only for HIGH-confidence, STRUCTURED_EVIDENCE_READY entries."""
    return (
        isinstance(entry, dict)
        and entry.get("confidence") == SOURCE_CONFIRMED_CONFIDENCE
        and entry.get("readinessLabel") == SOURCE_CONFIRMED_READINESS
    )


def _normalize_options(options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    opts = {
        "includeNeedsReview": False,
        "procedureType": None,
        "subCode": None,
        "readinessLabel": None,
        "confidence": None,
    }
    if isinstance(options, dict):
        opts.update({k: options.get(k, opts[k]) for k in opts})
    return opts


def _matches_filters(entry: Dict[str, Any], opts: Dict[str, Any]) -> bool:
    if opts["procedureType"] is not None and entry.get("procedureType") != opts["procedureType"]:
        return False
    if opts["readinessLabel"] is not None and entry.get("readinessLabel") != opts["readinessLabel"]:
        return False
    if opts["confidence"] is not None and entry.get("confidence") != opts["confidence"]:
        return False
    if opts["subCode"] is not None:
        sub = opts["subCode"]
        covered = entry.get("subCodesCovered") or []
        if entry.get("subCode") != sub and sub not in covered:
            return False
    return True


def get_structured_requirements(
    status_code: str, options: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Return structured entries for ``status_code``.

    Default (``includeNeedsReview`` False) returns ONLY source-confirmed
    entries — safe for user-facing use. Pass ``{"includeNeedsReview": True}``
    to include candidate/needs-review entries (internal/debug only).
    """
    if not status_code:
        return []
    opts = _normalize_options(options)
    out: List[Dict[str, Any]] = []
    for e in _load_raw()["entries"]:
        if e.get("statusCode") != status_code:
            continue
        if not opts["includeNeedsReview"] and not is_source_confirmed(e):
            continue
        if not _matches_filters(e, opts):
            continue
        out.append(e)
    return out


def get_source_confirmed_structured_requirements(
    status_code: str, options: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Return ONLY source-confirmed (HIGH / STRUCTURED_EVIDENCE_READY) entries.

    ``includeNeedsReview`` is ignored here by design — this accessor never
    returns candidate evidence.
    """
    opts = _normalize_options(options)
    opts["includeNeedsReview"] = False
    out: List[Dict[str, Any]] = []
    for e in _load_raw()["entries"]:
        if e.get("statusCode") != status_code:
            continue
        if not is_source_confirmed(e):
            continue
        if not _matches_filters(e, opts):
            continue
        out.append(e)
    return out


def has_source_confirmed_structured_requirements(status_code: str) -> bool:
    """True if ``status_code`` has at least one source-confirmed entry."""
    return bool(get_source_confirmed_structured_requirements(status_code))


def source_confirmed_status_codes() -> List[str]:
    """Sorted list of status codes that have at least one source-confirmed entry."""
    codes = {
        e.get("statusCode")
        for e in _load_raw()["entries"]
        if is_source_confirmed(e) and e.get("statusCode")
    }
    return sorted(codes)


def public_summary(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Project a source-confirmed entry to the safe, user-facing shape.

    Excludes internal review notes and any field that could confuse users.
    """
    ms = entry.get("manualSource") or {}
    return {
        "statusCode": entry.get("statusCode"),
        "subCode": entry.get("subCode"),
        "subCodesCovered": entry.get("subCodesCovered"),
        "procedureType": entry.get("procedureType"),
        "boundaryType": entry.get("boundaryType"),
        "pageStart": ms.get("pageStart"),
        "pageEnd": ms.get("pageEnd"),
        "sectionTitle": ms.get("sectionTitle"),
        "documents": [
            {
                "textKo": d.get("textKo"),
                "requiredness": d.get("requiredness"),
            }
            for d in (entry.get("documents") or [])
            if isinstance(d, dict) and d.get("textKo")
        ],
        "source": {
            "manualName": ms.get("manualName"),
            "manualVersion": ms.get("manualVersion"),
            "file": ms.get("file"),
        },
        "confidence": entry.get("confidence"),
        "readinessLabel": entry.get("readinessLabel"),
    }
