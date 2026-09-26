"""Data-file locations for the knowledge platform, deploy-context aware.

The Railway service is deployed with Root Directory = backend, so files at the
repository root (``data/…``, ``doc_master.json``) are NOT in the production
build context. Resolving them as ``<repo root>/data/…`` works in CI and
locally but fails in production, where the platform bootstrap then raised
``FileNotFoundError`` on every request and ``/api/ask`` silently lost its
manual grounding (no structured D-2 checklist).

Rule: prefer the canonical repository-root file; fall back to the
byte-identical deploy-context copy under ``backend/data/`` that
``scripts/sync_visa_data.py`` maintains (drift-gated in CI).
"""
from __future__ import annotations

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
DEPLOY_DATA_DIR = BACKEND_DIR / "data"


def repo_data_path(canonical_rel: str, deploy_rel: str) -> Path:
    """``<repo root>/<canonical_rel>`` when present, else ``backend/data/<deploy_rel>``.

    Returns the canonical path when neither exists, so callers keep their
    existing missing-file behaviour and error messages.
    """
    canonical = REPO_ROOT / canonical_rel
    if canonical.exists():
        return canonical
    deploy_copy = DEPLOY_DATA_DIR / deploy_rel
    return deploy_copy if deploy_copy.exists() else canonical
