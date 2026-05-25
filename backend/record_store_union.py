"""Importable union resolver adapter for the Paradiso backend (E-4A).

Bridges backend/paradiso_backend.py to scripts/resolve_record_store.py so
the backend can load the union view of visa_data.json + scenario_help_records
without duplicating resolver logic.

During E-4A:
  - union_view() returns the same records as visa_data.json (zero behavior
    change), because the 17 alias-deprecated records still exist in both stores.
  - This module is intentionally thin; all resolver logic lives in
    scripts/resolve_record_store.py (single source of truth).
  - If the scripts module or either data file is unavailable (e.g. in a
    stripped deploy context), load_union_view() raises ImportError so the
    caller can fall back to existing path-based loading.

E-4B prerequisite: after the 17 alias-deprecated records are removed from
visa_data.json, this module will keep returning the same effective records
(sourced from scenario_help_records.json), proving removal safety.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

_HERE = Path(__file__).resolve().parent          # backend/
_REPO_ROOT = _HERE.parent                        # repo root
_SCRIPTS = str(_REPO_ROOT / "scripts")

if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

try:
    import resolve_record_store as _resolver  # noqa: E402
except ImportError as exc:
    raise ImportError(
        f"record_store_union: cannot import resolve_record_store from {_SCRIPTS}. "
        f"Original error: {exc}"
    ) from exc


def load_union_view(prefer: str = "visa_data") -> List[Dict[str, Any]]:
    """Return the deterministic union of visa_data.json + scenario_help_records.

    During E-4A `prefer` is always "visa_data" (canonical wins). The union is
    de-duplicated so the 17 shadow records do not appear twice.

    Raises RuntimeError if the union is empty (guards against silent failure).
    """
    records = _resolver.union_view(prefer=prefer)
    if not records:
        raise RuntimeError("record_store_union: union_view returned an empty list")
    return records


def union_parity_report() -> Dict[str, Any]:
    """Return the E-4A parity metrics dict (used by backend tests)."""
    return _resolver.parity_report()
