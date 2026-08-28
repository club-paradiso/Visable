"""BM25 search over the built manual FTS index, with approval-state separation.

Reads the SQLite FTS5 index produced by ``scripts/build_manual_search_index.py``.
The index is a *build artifact*, not committed, so every entry point here must
work when it is absent — a missing index degrades to an explicit
``index_unavailable`` state, never to a silent empty result set that would read as
"the manuals say nothing about this".

Approved and unapproved chunks are returned in separate buckets. A caller may show
both, but only ``approved`` may back a direct assertion (see ``manual_registry``).

Read-only, no network, no secrets.
"""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Any, Dict, List, Optional

from . import manual_registry as mr

MANUAL_SEARCH_VERSION = "2026-07-manual-search-v1"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_INDEX_PATH = os.path.join(_REPO_ROOT, "build", "manual_search_index.sqlite3")

STATUS_OK = "ok"
STATUS_NO_RESULTS = "no_results"
STATUS_INDEX_UNAVAILABLE = "index_unavailable"
STATUS_BAD_QUERY = "bad_query"

_MAX_SNIPPET = 320
_MAX_RESULTS = 25

# FTS5 treats these as syntax. A user query is data, not a query language, so they
# are stripped rather than escaped — a stray quote must not become an operator.
_FTS_SYNTAX_RE = re.compile(r'["*():^{}\[\]-]+')


def _sanitize_fts_query(query: str) -> str:
    cleaned = _FTS_SYNTAX_RE.sub(" ", str(query or ""))
    tokens = [t for t in cleaned.split() if t]
    if not tokens:
        return ""
    # Quote each token so it is matched literally; join with AND semantics.
    return " ".join(f'"{token}"' for token in tokens[:12])


def index_path(explicit: Optional[str] = None) -> str:
    return explicit or os.environ.get("MANUAL_SEARCH_INDEX_PATH") or DEFAULT_INDEX_PATH


def index_available(path: Optional[str] = None) -> bool:
    return os.path.exists(index_path(path))


def index_composition(path: Optional[str] = None) -> Dict[str, Any]:
    """What the built index actually CONTAINS, by approval state.

    "The index file exists" and "approved evidence is searchable" are different
    facts, and conflating them is how a readiness probe reports green while the
    strongest evidence in the repository is unreachable. The index can be built
    and complete while holding zero direct-evidence chunks — which is exactly
    the current state, because the approved editions have no sectioned source
    to index yet.

    Returns counts only; no document text. Never raises — a probe must not be
    able to take down the endpoint that reports on it.
    """
    resolved = index_path(path)
    if not os.path.exists(resolved):
        return {"available": False, "totalChunks": 0, "directEvidenceChunks": 0,
                "byApprovalState": {}, "sources": []}
    try:
        con = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
        try:
            by_state = {
                str(state): int(count)
                for state, count in con.execute(
                    "SELECT approval_state, COUNT(*) FROM chunk GROUP BY approval_state"
                )
            }
            direct = int(
                con.execute(
                    "SELECT COUNT(*) FROM chunk WHERE direct_evidence = 1"
                ).fetchone()[0]
            )
            sources = [
                str(row[0])
                for row in con.execute("SELECT DISTINCT source_id FROM chunk ORDER BY source_id")
            ]
        finally:
            con.close()
    except sqlite3.Error:
        return {"available": True, "totalChunks": 0, "directEvidenceChunks": 0,
                "byApprovalState": {}, "sources": [], "error": "index_unreadable"}

    return {
        "available": True,
        "totalChunks": sum(by_state.values()),
        "directEvidenceChunks": direct,
        "byApprovalState": by_state,
        "sources": sources,
    }


def search_manuals(
    query: str,
    *,
    limit: int = 8,
    domain: str = "",
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """BM25 search returning approved and review-pending chunks in separate buckets.

    Never raises. ``status`` distinguishes a missing index from an empty result so
    the caller can render "not searchable right now" rather than "nothing found".
    """
    resolved = index_path(path)
    match_query = _sanitize_fts_query(query)
    if not match_query:
        return {"status": STATUS_BAD_QUERY, "query": query, "approved": [],
                "needs_review": [], "total": 0, "index_available": os.path.exists(resolved)}

    if not os.path.exists(resolved):
        return {"status": STATUS_INDEX_UNAVAILABLE, "query": query, "approved": [],
                "needs_review": [], "total": 0, "index_available": False,
                "hint": "python3 scripts/build_manual_search_index.py"}

    capped = max(1, min(int(limit or 8), _MAX_RESULTS))
    sql = (
        "SELECT c.source_id, c.family_key, c.approval_state, c.direct_evidence,"
        "       c.domain, c.page, c.heading, c.status_codes, c.manual_version,"
        "       snippet(chunk_fts, 1, '', '', '…', 24) AS excerpt,"
        "       bm25(chunk_fts) AS score"
        " FROM chunk_fts JOIN chunk c ON c.chunk_id = chunk_fts.rowid"
        " WHERE chunk_fts MATCH ?"
    )
    params: List[Any] = [match_query]
    if domain:
        sql += " AND c.domain = ?"
        params.append(domain)
    # bm25() returns a negative score where more negative is more relevant.
    sql += " ORDER BY score LIMIT ?"
    params.append(capped * 3)

    try:
        conn = sqlite3.connect(f"file:{resolved}?mode=ro", uri=True)
    except sqlite3.Error:
        return {"status": STATUS_INDEX_UNAVAILABLE, "query": query, "approved": [],
                "needs_review": [], "total": 0, "index_available": False}

    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.Error:
        return {"status": STATUS_INDEX_UNAVAILABLE, "query": query, "approved": [],
                "needs_review": [], "total": 0, "index_available": True}
    finally:
        conn.close()

    approved: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    for row in rows:
        item = {
            "source_id": row["source_id"],
            "family_key": row["family_key"],
            "approval_state": row["approval_state"],
            "usable_as_direct_evidence": bool(row["direct_evidence"]),
            "domain": row["domain"],
            "page": row["page"],
            "heading": (row["heading"] or "")[:160],
            "status_codes": [c for c in (row["status_codes"] or "").split() if c],
            "manual_version": row["manual_version"],
            "excerpt": (row["excerpt"] or "")[:_MAX_SNIPPET],
            "score": round(float(row["score"] or 0.0), 4),
        }
        if item["usable_as_direct_evidence"]:
            approved.append(item)
        else:
            pending.append(item)

    approved = approved[:capped]
    pending = pending[:capped]
    total = len(approved) + len(pending)
    return {
        "status": STATUS_OK if total else STATUS_NO_RESULTS,
        "query": query,
        "approved": approved,
        "needs_review": pending,
        "total": total,
        "index_available": True,
        "direct_evidence_available": bool(approved),
        "review_pending_label_key": "manualEvidenceNeedsReview",
    }


def manual_evidence_state(result: Dict[str, Any]) -> str:
    """Collapse a search result into the answer-metadata evidence state."""
    status = (result or {}).get("status")
    if status == STATUS_INDEX_UNAVAILABLE:
        return "unavailable"
    if status in (STATUS_NO_RESULTS, STATUS_BAD_QUERY):
        return "no_results"
    if (result or {}).get("direct_evidence_available"):
        return "approved_direct"
    if (result or {}).get("needs_review"):
        return "review_pending_only"
    return "no_results"


__all__ = [
    "MANUAL_SEARCH_VERSION", "STATUS_OK", "STATUS_NO_RESULTS",
    "STATUS_INDEX_UNAVAILABLE", "STATUS_BAD_QUERY",
    "index_path", "index_available", "search_manuals", "manual_evidence_state",
    "DEFAULT_INDEX_PATH",
]
