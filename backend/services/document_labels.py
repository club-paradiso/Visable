"""Resolve doc_master document IDs to their official Korean/English labels.

The problem
-----------
``visa_data.json`` procedure document arrays are heterogeneous: most entries are
already human-readable manual text, but 67 of them across the dataset are
``doc_master`` **IDs** (``doc_fee_generic``, ``doc_residence_proof_generic``, …).
Every one of those IDs is valid in ``doc_master.json`` — this was never a data
integrity problem, only a resolution gap.

Two consumers resolved them and one did not:

* ``index.html`` resolves via its inline ``DOC_DICT``.
* ``assets/js/complex-status-guide.js`` resolves via a fetched doc_master map.
* The **procedure packet builder** did not, so ``/api/procedure-packet`` and
  ``/api/visas/{code}/packets`` emitted ``{"nameKo": "doc_fee_generic"}`` — a
  raw internal identifier in a field named "Korean name", rendered to users as
  a document they are supposed to bring to an immigration office.

An unresolved ID reaching a user-facing document list is exactly the misleading
rendering CLAUDE.md guards against, so this fixes the resolver rather than the
data: ``visa_data.json`` and ``doc_master.json`` are untouched.

Why doc_master.json and not DOC_DICT
------------------------------------
``DOC_DICT`` is a hand-maintained copy of the same mapping, carrying a comment
asking future editors to "keep DOC_DICT in sync with doc_master.json". A second
copy of a mapping is a second thing to forget. ``doc_master.json`` is the
committed registry, so it is the authority here; nothing new is invented and no
label is written that a reviewer did not already approve into that file.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

DOCUMENT_LABELS_VERSION = "2026-08-document-labels-v1"

#: ``backend/`` — the directory that IS the Railway build context (the service
#: is deployed with Root Directory = backend). Anchoring to this package rather
#: than to a computed repo root is what makes resolution work in production.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_BACKEND_DIR)

#: In-context copy, kept byte-identical to the canonical registry by
#: ``scripts/sync_visa_data.py`` and drift-gated in CI.
BACKEND_DOC_MASTER_PATH = os.path.join(_BACKEND_DIR, "data", "doc_master.json")
#: The canonical registry. Present for local dev and any deploy built from the
#: repository root; absent when Root Directory = backend.
REPO_ROOT_DOC_MASTER_PATH = os.path.join(_REPO_ROOT, "doc_master.json")

#: Retained for callers that want a single default. Prefer
#: :func:`candidate_doc_master_paths`, which is what resolution actually uses.
DEFAULT_DOC_MASTER_PATH = REPO_ROOT_DOC_MASTER_PATH


def candidate_doc_master_paths(explicit: Optional[str] = None) -> List[str]:
    """Search order for the document registry.

    1. ``explicit`` argument, or the ``DOC_MASTER_PATH`` env var.
    2. ``backend/data/doc_master.json`` — the committed copy that ships inside
       the backend deploy context.
    3. ``<repo-root>/doc_master.json`` — the canonical file, used for local dev
       and any deploy whose build context includes the repository root.

    Order 2 before 3 deliberately mirrors ``_candidate_visa_paths`` in
    ``paradiso_backend``. The Railway service sets Root Directory = backend, so
    the repo-root file is simply not on disk there; resolving only against it
    meant ``load_document_labels`` returned an empty map in production and every
    document ID passed through unresolved — the packet fix worked in CI and did
    nothing for users.

    An explicit path is the ONLY candidate when given. Falling back from an
    operator's ``DOC_MASTER_PATH`` to a different registry would silently serve
    labels from a file they did not choose, turning a visible misconfiguration
    into wrong document names.
    """
    chosen = (explicit or os.environ.get("DOC_MASTER_PATH") or "").strip()
    if chosen:
        return [chosen]
    return [BACKEND_DOC_MASTER_PATH, REPO_ROOT_DOC_MASTER_PATH]

#: A doc_master identifier: lowercase ASCII snake_case. Deliberately narrow so
#: Korean manual prose can never be mistaken for an ID and "resolved" into
#: something else.
_DOC_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

_CACHE: Optional[Dict[str, Dict[str, str]]] = None
_CACHE_PATH: Optional[str] = None


def _doc_master_path(explicit: Optional[str] = None) -> str:
    """First candidate that exists on disk; the last candidate if none do.

    Returning a non-existent path when nothing is found is deliberate: the
    caller degrades to an empty map, and the returned path is what diagnostics
    report as "where we looked".
    """
    candidates = candidate_doc_master_paths(explicit)
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[-1]


def load_document_labels(path: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """``id -> {"ko": ..., "en": ...}``, cached per resolved path.

    A missing or malformed registry yields an empty map rather than raising:
    resolution is an improvement on the raw value, never a precondition for
    serving a record. Degrading to the current (unresolved) behaviour is the
    correct failure mode.
    """
    global _CACHE, _CACHE_PATH
    resolved = _doc_master_path(path)
    if _CACHE is not None and _CACHE_PATH == resolved:
        return _CACHE

    labels: Dict[str, Dict[str, str]] = {}
    try:
        with open(resolved, encoding="utf-8") as handle:
            entries = json.load(handle)
    except (OSError, ValueError):
        entries = []

    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        doc_id = str(entry.get("id") or "").strip()
        ko = str(entry.get("ko_name") or "").strip()
        en = str(entry.get("en_name") or "").strip()
        if doc_id and (ko or en):
            labels[doc_id] = {"ko": ko or en, "en": en or ko}

    _CACHE, _CACHE_PATH = labels, resolved
    return labels


def reset_cache_for_tests() -> None:
    global _CACHE, _CACHE_PATH
    _CACHE, _CACHE_PATH = None, None


def is_document_id(value: Any, *, path: Optional[str] = None) -> bool:
    """True only for a string that is a KNOWN doc_master id.

    Shape alone is not enough. An unknown snake_case token is left exactly as it
    is: inventing a label for an ID this repository does not define would be
    fabricating a document requirement.
    """
    if not isinstance(value, str):
        return False
    text = value.strip()
    return bool(_DOC_ID_RE.match(text)) and text in load_document_labels(path)


def resolve_document_label(
    value: Any, *, lang: str = "ko", path: Optional[str] = None
) -> Any:
    """Resolve one entry. Non-IDs and unknown IDs pass through untouched.

    Idempotent: resolving an already-resolved label returns it unchanged, so it
    is safe to apply at more than one layer.
    """
    if not isinstance(value, str):
        return value
    text = value.strip()
    entry = load_document_labels(path).get(text)
    if entry is None or not _DOC_ID_RE.match(text):
        return value
    key = "en" if str(lang or "ko").lower().startswith("en") else "ko"
    return entry.get(key) or entry.get("ko") or value


def resolve_document_list(
    values: Any, *, lang: str = "ko", path: Optional[str] = None
) -> List[Any]:
    if not isinstance(values, list):
        return values
    return [resolve_document_label(v, lang=lang, path=path) for v in values]


#: The document-group keys used throughout visa_data procedure objects.
DOC_GROUP_KEYS = ("commonDocs", "requiredDocs", "conditionalDocs", "additionalDocs")


def resolve_required_docs(
    required_docs: Any, *, lang: str = "ko", path: Optional[str] = None
) -> Any:
    """Resolve every group inside one ``requiredDocs`` object.

    Returns a new object; the input is never mutated, so a cached visa record
    cannot be corrupted by a caller that resolves for a different language.
    """
    if not isinstance(required_docs, dict):
        return required_docs
    out = dict(required_docs)
    for key in DOC_GROUP_KEYS:
        if isinstance(out.get(key), list):
            out[key] = resolve_document_list(out[key], lang=lang, path=path)
    return out


def unresolved_document_ids(record: Any) -> List[str]:
    """ID-shaped strings in a record's document arrays that doc_master lacks.

    Diagnostics for the data owner: a token that looks like an ID but resolves
    to nothing is either a typo or a document the registry has not defined yet.
    Neither is safe to guess at, so both are reported rather than rendered.
    """
    known = load_document_labels()
    found: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, str):
                    text = item.strip()
                    if _DOC_ID_RE.match(text) and text not in known and text not in found:
                        found.append(text)
                else:
                    walk(item)

    walk((record or {}).get("procedures") if isinstance(record, dict) else record)
    return found


def display_path(path: str) -> str:
    """Repo-relative when inside the tree, otherwise unchanged.

    Public because readiness reporting elsewhere presents filesystem paths the
    same way: enough to diagnose where a lookup searched, without publishing
    absolute container paths on an endpoint anyone can call.
    """
    for base in (_REPO_ROOT, _BACKEND_DIR):
        try:
            rel = os.path.relpath(path, base)
        except ValueError:
            continue
        if not rel.startswith(os.pardir):
            return rel
    return path


def registry_source(path: Optional[str] = None) -> Dict[str, Any]:
    """Where the registry was loaded from, for readiness reporting.

    ``resolved: false`` with a non-empty ``searched`` list is the production
    failure Codex caught on #582: the file is simply not in the deploy context,
    which is a packaging problem, not a data problem.
    """
    resolved = _doc_master_path(path)
    exists = os.path.isfile(resolved)
    if not exists:
        source = "missing"
    elif resolved == BACKEND_DOC_MASTER_PATH:
        source = "backend-data"
    elif resolved == REPO_ROOT_DOC_MASTER_PATH:
        source = "repo-root"
    else:
        source = "explicit"
    return {
        "resolved": exists,
        "source": source,
        "entries": len(load_document_labels(path)),
        # Relative to the repo/deploy root: enough to diagnose "where did it
        # look", without publishing absolute container paths on a public
        # endpoint. An operator-set path outside the tree is shown as given.
        "searched": [display_path(c) for c in candidate_doc_master_paths(path)],
    }
