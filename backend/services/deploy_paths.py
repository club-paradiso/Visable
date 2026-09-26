"""Resolve repository-root data files in the Railway deploy context.

Railway builds the backend with Root Directory = ``backend``, so files at the
repository root (``data/``, ``doc_master.json``) are not in the container.
Loaders that read them silently degrade there: the knowledge platform came up
as an empty in-memory store, manual grounding returned ``None``, and the D-2
document lookup lost its source-confirmed checklist in production while every
repo-checkout test passed.

Each file below is committed twice: the canonical copy at the repository root
(the single source of truth) and a byte-identical deploy copy under
``backend/data`` kept in sync by ``scripts/sync_visa_data.py`` (``--check``
fails CI on drift). ``repo_path`` prefers the canonical file and falls back to
the deploy copy only when the canonical one is absent.
"""
from __future__ import annotations

from pathlib import Path

#: ``backend/``
BACKEND_ROOT = Path(__file__).resolve().parents[1]
#: Repository root (does not exist as such in the Railway container).
REPO_ROOT = BACKEND_ROOT.parent
#: Deploy copies of repository-root ``data/`` files, mirrored by relative path.
DEPLOY_DATA_DIR = BACKEND_ROOT / "data" / "repo_data"

# Root-level files whose deploy copy lives elsewhere (pre-existing layout).
_ROOT_FILE_COPIES = {
    "doc_master.json": BACKEND_ROOT / "data" / "doc_master.json",
}


def repo_path(relative: str) -> Path:
    """Path of a repository-root file, e.g. ``"data/source_registry.json"``.

    Returns the canonical path when it exists, else the backend deploy copy
    (also for a missing file, so callers keep their own "missing" handling).
    """
    canonical = REPO_ROOT / relative
    if canonical.exists():
        return canonical
    if relative in _ROOT_FILE_COPIES:
        return _ROOT_FILE_COPIES[relative]
    rel = Path(relative)
    if rel.parts and rel.parts[0] == "data":
        return DEPLOY_DATA_DIR.joinpath(*rel.parts[1:])
    return canonical
