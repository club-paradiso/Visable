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

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DOC_MASTER_PATH = os.path.join(_REPO_ROOT, "doc_master.json")

#: A doc_master identifier: lowercase ASCII snake_case. Deliberately narrow so
#: Korean manual prose can never be mistaken for an ID and "resolved" into
#: something else.
_DOC_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

_CACHE: Optional[Dict[str, Dict[str, str]]] = None
_CACHE_PATH: Optional[str] = None


def _doc_master_path(explicit: Optional[str] = None) -> str:
    return explicit or os.environ.get("DOC_MASTER_PATH") or DEFAULT_DOC_MASTER_PATH


def load_document_labels(path: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """``id -> {"ko": ..., "en": ...}``, cached per path.

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
