#!/usr/bin/env python3
"""Build a SQLite FTS5 search index over the extracted manual sections.

Why SQLite FTS and not a vector store: statute names, 체류자격 codes (D-2-1, E-7-4)
and 별표 numbers are *exact tokens*. A nearest-neighbour embedding search will
happily return E-7-1 for an E-7-4 query, which is precisely the failure mode this
codebase must not have. BM25 over an inverted index keeps exact-token queries
exact; semantic search can be layered on later for prose, never for codes.

The index carries each chunk's approval state (from
``data/manual_approval_index.json`` via ``backend/services/manual_registry.py``)
so a consumer can separate approved evidence from 검토 전 candidates in one query
instead of re-deriving it.

Safety properties:

* Build is atomic — the new database is written to a temp path and only swapped
  into place after a successful integrity check. A failed rebuild therefore
  cannot damage a working index (Phase 2 requirement).
* Read-only with respect to every source file. Nothing under ``data/`` or
  ``backend/data/`` is modified.
* No network access, no secrets, stdlib only.

Usage:
    python3 scripts/build_manual_search_index.py
    python3 scripts/build_manual_search_index.py --out build/manual_index.sqlite3
    python3 scripts/build_manual_search_index.py --check     # verify only
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import manual_registry as mr  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "build" / "manual_search_index.sqlite3"

# Extracted section dumps, paired with the registry source they were derived FROM
# (not the newest edition of that family). The stay sections come from the
# 2026-06-17 extraction, which the registry marks superseded by the 2026-06-23
# edition — the newer edition ships as a PDF with no section extraction in-repo.
# Labelling these chunks 'superseded' is the honest state; silently attributing
# them to the current edition would misdate every stay-manual search hit.
SECTION_SOURCES: Tuple[Tuple[str, str], ...] = (
    ("visa_manual_2026_06_17_pdf", "backend/data/sources/manuals/260617_visa_manual_sections.json"),
    ("stay_manual_2026_06_17_txt", "backend/data/sources/manuals/260617_stay_manual_sections.json"),
    ("dongpo_manual_2026_04_21", "backend/data/sources/manuals/260421_dongpo_manual_sections.json"),
)

SCHEMA = """
PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE chunk (
    chunk_id        INTEGER PRIMARY KEY,
    source_id       TEXT NOT NULL,
    family_key      TEXT NOT NULL,
    approval_state  TEXT NOT NULL,
    direct_evidence INTEGER NOT NULL,
    domain          TEXT NOT NULL DEFAULT '',
    page            INTEGER NOT NULL DEFAULT 0,
    heading         TEXT NOT NULL DEFAULT '',
    status_codes    TEXT NOT NULL DEFAULT '',
    subcodes        TEXT NOT NULL DEFAULT '',
    source_file     TEXT NOT NULL DEFAULT '',
    manual_version  TEXT NOT NULL DEFAULT ''
);

CREATE INDEX idx_chunk_source   ON chunk(source_id);
CREATE INDEX idx_chunk_approval ON chunk(approval_state);
CREATE INDEX idx_chunk_domain   ON chunk(domain);

-- Body text lives in the FTS table; 'chunk' holds the filterable metadata.
CREATE VIRTUAL TABLE chunk_fts USING fts5(
    heading,
    body,
    status_codes,
    content=''
);
"""


def _load_sections(path: Path) -> List[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError) as exc:
        print(f"  ! skipped {path.relative_to(REPO_ROOT)}: {exc}", file=sys.stderr)
        return []
    if isinstance(payload, dict):
        payload = payload.get("sections") or []
    return [row for row in payload if isinstance(row, dict)]


def _normalize_section(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize the two in-repo section schemas into one chunk shape.

    Schema A (visa / dongpo): ``{heading, text, page, domain, status_codes_detected}``
    Schema B (stay):          ``{title, paragraphs:[{text}], pdf_page, section_index}``
    An unrecognized row yields ``None`` rather than an empty chunk.
    """
    body = str(row.get("text") or "").strip()
    heading = str(row.get("heading") or row.get("title") or "").strip()
    page = row.get("page") or row.get("pdf_page") or row.get("section_index") or 0

    if not body:
        paragraphs = row.get("paragraphs")
        if isinstance(paragraphs, list):
            body = "\n".join(
                str(p.get("text") or "").strip()
                for p in paragraphs
                if isinstance(p, dict) and str(p.get("text") or "").strip()
            ).strip()

    if not body:
        return None

    status_codes = row.get("status_codes_detected") or []
    if isinstance(row.get("paragraphs"), list):
        # Roll paragraph-level code detections up to the section.
        for para in row["paragraphs"]:
            if isinstance(para, dict):
                status_codes = list(status_codes) + list(para.get("status_codes_detected") or [])

    try:
        page_int = int(page)
    except (TypeError, ValueError):
        page_int = 0

    return {
        "body": body,
        "heading": heading,
        "page": page_int,
        "domain": str(row.get("domain") or ""),
        "status_codes": " ".join(sorted({str(c) for c in status_codes if c})),
        "subcodes": " ".join(str(c) for c in (row.get("subcodes_detected") or [])),
        "source_file": str(row.get("source_file") or ""),
    }


def _version_lookup() -> Dict[str, mr.ManualDocumentVersion]:
    return {v.source_id: v for v in mr.load_manual_versions()}


def _iter_chunks(versions: Dict[str, mr.ManualDocumentVersion]) -> Iterable[Dict[str, Any]]:
    for source_id, rel_path in SECTION_SOURCES:
        path = REPO_ROOT / rel_path
        if not path.exists():
            print(f"  - {rel_path}: not present, skipping")
            continue
        version = versions.get(source_id)
        if version is None:
            # A section dump with no registry entry has no provenance, so it is
            # indexed at the most restrictive state rather than dropped silently.
            approval_state = mr.STATE_NEEDS_REVIEW
            family_key, _ = mr.derive_family(source_id)
            manual_version = ""
        else:
            approval_state = version.approval_state
            family_key = version.family_key
            manual_version = version.version

        direct = 1 if approval_state in mr.DIRECT_EVIDENCE_STATES else 0
        rows = _load_sections(path)
        print(f"  - {rel_path}: {len(rows)} sections "
              f"[{approval_state}{'' if direct else ' · not direct evidence'}]")
        skipped = 0
        for row in rows:
            section = _normalize_section(row)
            if section is None:
                skipped += 1
                continue
            yield {
                "source_id": source_id,
                "family_key": family_key,
                "approval_state": approval_state,
                "direct_evidence": direct,
                "domain": section["domain"],
                "page": section["page"],
                "heading": section["heading"],
                "status_codes": section["status_codes"],
                "subcodes": section["subcodes"],
                "source_file": section["source_file"] or rel_path,
                "manual_version": manual_version,
                "body": section["body"],
            }
        if skipped:
            print(f"    ({skipped} sections had no extractable body text)")


def build(out_path: Path) -> Dict[str, Any]:
    versions = _version_lookup()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build into a temp file next to the target so the swap is atomic and stays
    # on the same filesystem. A crash mid-build leaves the previous index intact.
    handle, tmp_name = tempfile.mkstemp(
        prefix=".manual_index.", suffix=".sqlite3", dir=str(out_path.parent))
    os.close(handle)
    tmp_path = Path(tmp_name)

    stats = {"chunks": 0, "by_state": {}, "by_source": {}}
    try:
        conn = sqlite3.connect(str(tmp_path))
        try:
            conn.executescript(SCHEMA)
            chunk_id = 0
            for chunk in _iter_chunks(versions):
                chunk_id += 1
                conn.execute(
                    "INSERT INTO chunk (chunk_id, source_id, family_key, approval_state,"
                    " direct_evidence, domain, page, heading, status_codes, subcodes,"
                    " source_file, manual_version)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (chunk_id, chunk["source_id"], chunk["family_key"],
                     chunk["approval_state"], chunk["direct_evidence"], chunk["domain"],
                     chunk["page"], chunk["heading"], chunk["status_codes"],
                     chunk["subcodes"], chunk["source_file"], chunk["manual_version"]),
                )
                conn.execute(
                    "INSERT INTO chunk_fts (rowid, heading, body, status_codes)"
                    " VALUES (?,?,?,?)",
                    (chunk_id, chunk["heading"], chunk["body"], chunk["status_codes"]),
                )
                stats["chunks"] += 1
                stats["by_state"][chunk["approval_state"]] = \
                    stats["by_state"].get(chunk["approval_state"], 0) + 1
                stats["by_source"][chunk["source_id"]] = \
                    stats["by_source"].get(chunk["source_id"], 0) + 1

            conn.executemany(
                "INSERT INTO meta (key, value) VALUES (?,?)",
                [
                    ("registry_version", mr.MANUAL_REGISTRY_VERSION),
                    ("chunk_count", str(stats["chunks"])),
                    ("approval_states", json.dumps(stats["by_state"], ensure_ascii=False)),
                    ("note", "Only approval_state='approved' rows may back a direct "
                             "assertion. Everything else is a 검토 전 candidate."),
                ],
            )
            conn.commit()

            # Integrity gate: a corrupt or empty build must never replace a good index.
            if stats["chunks"] == 0:
                raise RuntimeError("no chunks indexed — refusing to replace the existing index")
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise RuntimeError(f"integrity check failed: {integrity}")
            probe = conn.execute(
                "SELECT count(*) FROM chunk_fts WHERE chunk_fts MATCH ?", ("체류",)).fetchone()[0]
            stats["probe_hits"] = probe
        finally:
            conn.close()

        os.replace(str(tmp_path), str(out_path))
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    stats["out"] = str(out_path.relative_to(REPO_ROOT))
    return stats


def check(out_path: Path) -> int:
    if not out_path.exists():
        print(f"ERROR: index not found at {out_path}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(f"file:{out_path}?mode=ro", uri=True)
    try:
        count = conn.execute("SELECT count(*) FROM chunk").fetchone()[0]
        states = dict(conn.execute(
            "SELECT approval_state, count(*) FROM chunk GROUP BY approval_state").fetchall())
        print(f"chunks: {count}")
        print(f"approval states: {states}")
        approved = states.get(mr.STATE_APPROVED, 0)
        print(f"direct-evidence chunks: {approved}")
        return 0
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="output sqlite path")
    parser.add_argument("--check", action="store_true", help="inspect an existing index only")
    args = parser.parse_args()
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path

    if args.check:
        return check(out_path)

    print("Building manual FTS index...")
    stats = build(out_path)
    print(f"\nindexed {stats['chunks']} chunks -> {stats['out']}")
    print(f"by approval state: {stats['by_state']}")
    print(f"by source: {stats['by_source']}")
    print(f"FTS probe ('체류'): {stats.get('probe_hits', 0)} hits")
    approved = stats["by_state"].get(mr.STATE_APPROVED, 0)
    if approved == 0:
        print("\nNOTE: 0 chunks are approved for direct evidence. Every indexed chunk is a"
              "\n      검토 전 candidate until a human review record is added to"
              "\n      data/manual_approval_index.json. This is the intended default.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
