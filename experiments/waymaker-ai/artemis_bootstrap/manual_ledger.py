"""Approval ledger for the official manual pages Artemis may read (stage 2, 라 on real data).

Why a ledger: approvals in ``data/manual_approval_index.json`` are edition
decisions ("not a line-by-line certification of every structured extract"),
and the page texts in ``data/manual-corpus`` are build outputs that can be
regenerated. The integrity check (``trust_gate.integrity_ok``) needs a hash per
unit of evidence, recorded when that unit was accepted. This module records
one per page of an approved edition, and only when:

* the catalog and the approval index both say ``approved`` for the source, and
* the source file on disk still has the SHA-256 both of them recorded.

A page hash here means "this is the text extracted from the approved edition
when the ledger was built". It inherits the owner's edition approval; it is
not a human review of that page. Pages whose text later changes (a rebuilt
corpus, a hand edit, a tampered file) fail integrity and stop being evidence.

The ledger holds hashes and locators only; page text is read from the corpus.

Usage, from experiments/waymaker-ai/artemis_bootstrap::

    python manual_ledger.py build     # writes ledgers/manual_2026_10_19_pages.jsonl
    python manual_ledger.py verify    # exit 1 if any page no longer matches
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trust_gate  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG = REPO_ROOT / "data" / "manual-corpus" / "catalog.json"
APPROVAL_INDEX = REPO_ROOT / "data" / "manual_approval_index.json"
LEDGER = Path(__file__).resolve().parent / "ledgers" / "manual_2026_10_19_pages.jsonl"
SOURCE_IDS = ("visa_manual_2026_10_19_pdf", "stay_manual_2026_10_19_pdf")


def page_id(source_id: str, page: int) -> str:
    return f"{source_id}#p{page}"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def approved_sources(source_ids: Iterable[str] = SOURCE_IDS) -> List[Dict[str, Any]]:
    """Catalog entries that are approved in both records and whose file hash still matches."""
    catalog = {s["id"]: s for s in json.loads(CATALOG.read_text(encoding="utf-8"))["sources"]}
    index = json.loads(APPROVAL_INDEX.read_text(encoding="utf-8"))["documents"]
    out = []
    for sid in source_ids:
        entry, record = catalog.get(sid), index.get(sid)
        if not entry or not record:
            raise SystemExit(f"{sid}: missing from catalog or approval index")
        if entry.get("approval_state") != "approved" or record.get("approval_state") not in trust_gate.DIRECT_EVIDENCE_STATES:
            raise SystemExit(f"{sid}: not approved (catalog {entry.get('approval_state')}, index {record.get('approval_state')})")
        actual = _sha256_file(REPO_ROOT / entry["file"])
        if not (actual == entry["sha256"] == record.get("source_sha256")):
            raise SystemExit(f"{sid}: source file hash {actual[:12]} does not match the approval record")
        out.append({**entry, "reviewed_at": record.get("reviewed_at"), "reviewer_recorded": bool(record.get("reviewer"))})
    return out


def _pages(source: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return json.loads((REPO_ROOT / source["sections"]).read_text(encoding="utf-8"))


def build(path: Path = LEDGER) -> Dict[str, Any]:
    sources = approved_sources()
    header = {
        "kind": "artemis_manual_page_ledger",
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hash_rule": "trust_gate.approval_hash: sha256(NFC(text).strip())",
        "meaning": "text extracted from an approved edition at build time; inherits the edition approval, not a per-page review",
        "sources": [{k: s[k] for k in ("id", "domain", "version", "file", "sha256", "sections", "reviewed_at")} for s in sources],
    }
    rows = []
    for s in sources:
        for p in _pages(s):
            rows.append({"id": page_id(s["id"], p["page"]), "source_id": s["id"], "page": p["page"],
                         "domain": s["domain"], "approved_sha256": trust_gate.approval_hash(p.get("text", ""))})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(header, ensure_ascii=False) + "\n")
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"pages": len(rows), "sources": [s["id"] for s in sources]}


def load_ledger(path: Path = LEDGER) -> Dict[str, Dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return {r["id"]: r for r in map(json.loads, lines[1:])}


_PAGE_CACHE: Dict[str, Dict[int, Dict[str, Any]]] = {}


def _page_text(source_id: str, page: int) -> Optional[Dict[str, Any]]:
    if source_id not in _PAGE_CACHE:
        catalog = {s["id"]: s for s in json.loads(CATALOG.read_text(encoding="utf-8"))["sources"]}
        _PAGE_CACHE[source_id] = {p["page"]: p for p in _pages(catalog[source_id])}
    return _PAGE_CACHE[source_id].get(page)


def resolve_evidence(item: Mapping[str, Any], ledger: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """A case's page reference turned into an evidence item the gate and the post-check understand.
    A page missing from the ledger is ``needs_review`` with no hash: the gate withholds it."""
    page = _page_text(item["source_id"], int(item["page"]))
    if page is None:
        raise ValueError(f"{item['id']}: no such page in the corpus")
    entry = ledger.get(item["id"])
    return {
        "id": item["id"],
        "title": f"{item['source_id']} p.{item['page']} {page.get('heading') or ''}".strip(),
        "text": page.get("text", ""),
        "source": {
            "kind": "official_manual",
            "approval_state": "approved" if entry else "needs_review",
            "approved_sha256": entry["approved_sha256"] if entry else None,
            "source_id": item["source_id"], "page": int(item["page"]), "domain": page.get("domain"),
        },
    }


def resolve_cases(cases: List[Dict[str, Any]], path: Path = LEDGER) -> List[Dict[str, Any]]:
    """Cases whose evidence are page references (no ``text``) get their text and approval
    record from the corpus and the ledger; other cases are returned unchanged."""
    if not any("text" not in e for c in cases for e in c["evidence"]):
        return cases
    ledger = load_ledger(path)
    return [{**c, "evidence": [e if "text" in e else resolve_evidence(e, ledger) for e in c["evidence"]]} for c in cases]


def verify(path: Path = LEDGER) -> List[str]:
    """Ids whose current corpus text no longer has the ledger hash."""
    bad = []
    for pid, entry in load_ledger(path).items():
        page = _page_text(entry["source_id"], entry["page"])
        if page is None or trust_gate.approval_hash(page.get("text", "")) != entry["approved_sha256"]:
            bad.append(pid)
    return bad


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("command", choices=("build", "verify"))
    args = p.parse_args(argv)
    if args.command == "build":
        print(json.dumps(build(), ensure_ascii=False))
        return 0
    bad = verify()
    print(json.dumps({"pages_changed_since_ledger": bad[:20], "count": len(bad)}, ensure_ascii=False))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
