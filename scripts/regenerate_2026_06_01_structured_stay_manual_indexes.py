#!/usr/bin/env python3
"""Regenerate structured stay-manual indexes for the 2026-06-01 PDF.

This is a conservative refresh, not a fresh legal extraction pass:

* visa-issuance entries remain tied to the current visa manual;
* stay/residence entries are moved to the 2026-06-01 stay PDF only after their
  cited page text is compared against the prior current stay PDF; and
* changed stay pages are downgraded out of source-confirmed runtime use until a
  human reviewer re-extracts the affected section from the June manual.

The companion HWP is recorded as an official stored artifact, but it is not used
as an extraction source because distribution-mode body extraction is blocked.
"""

from __future__ import annotations

import collections
import copy
import hashlib
import json
import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OLD_STRUCTURED = ROOT / "backend/data/manual_grounding/structured_requirements_2026_05.json"
OLD_INDEX = ROOT / "backend/data/manual_grounding/structured_requirements_index_2026_05.json"
NEW_STRUCTURED = ROOT / "backend/data/manual_grounding/structured_requirements_2026_06_01.json"
NEW_INDEX = ROOT / "backend/data/manual_grounding/structured_requirements_index_2026_06_01.json"
AUDIT_REPORT = ROOT / "docs/data/2026_06_01_structured_stay_manual_refresh_audit.json"

OLD_STAY_FILE = "docs/source-manuals/2026-05/stay_manual_2026_05.pdf"
NEW_STAY_FILE = "docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf"
NEW_STAY_HWP = "docs/source-manuals/2026-06/stay_manual_2026_06_01.hwp"
NEW_STAY_SHA256 = "e25e97c3c2a05b5676ca3648a04226dcdc2433ab7c89a2f5105e6f8be49778b0"
NEW_STAY_SOURCE_DATE = "2026-06-01"
NEW_STAY_MANUAL_VERSION = "2026.5"

SOURCE_CONFIRMED_CONFIDENCE = "HIGH"
SOURCE_CONFIRMED_READINESS = "STRUCTURED_EVIDENCE_READY"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _page_texts(path: Path, pages: set[int]) -> dict[int, str]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise SystemExit(
            "pypdf is required for this audit. Run with the bundled Codex "
            "Python runtime or install pypdf."
        ) from exc

    logging.getLogger("pypdf").setLevel(logging.ERROR)
    reader = PdfReader(str(path))
    out: dict[int, str] = {}
    for page in sorted(pages):
        if page < 1 or page > len(reader.pages):
            out[page] = ""
            continue
        out[page] = _compact_text(reader.pages[page - 1].extract_text() or "")
    return out


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_stay_entry(entry: dict[str, Any]) -> bool:
    source_file = ((entry.get("manualSource") or {}).get("file") or "")
    return "stay_manual" in source_file


def _entry_pages(entry: dict[str, Any]) -> list[int]:
    ms = entry.get("manualSource") or {}
    start, end = ms.get("pageStart"), ms.get("pageEnd")
    if not isinstance(start, int) or not isinstance(end, int):
        return []
    return list(range(start, end + 1))


def _is_source_confirmed(entry: dict[str, Any]) -> bool:
    return (
        entry.get("confidence") == SOURCE_CONFIRMED_CONFIDENCE
        and entry.get("readinessLabel") == SOURCE_CONFIRMED_READINESS
    )


def _compare_pages(stay_entries: list[dict[str, Any]]) -> tuple[dict[int, bool], dict[str, Any]]:
    pages: set[int] = set()
    for entry in stay_entries:
        pages.update(_entry_pages(entry))
    old_text = _page_texts(ROOT / OLD_STAY_FILE, pages)
    new_text = _page_texts(ROOT / NEW_STAY_FILE, pages)
    page_match: dict[int, bool] = {}
    changed: list[dict[str, Any]] = []
    missing: list[int] = []
    for page in sorted(pages):
        old = old_text.get(page, "")
        new = new_text.get(page, "")
        if not old or not new:
            page_match[page] = False
            missing.append(page)
            continue
        same = _sha(old) == _sha(new)
        page_match[page] = same
        if not same:
            changed.append({
                "page": page,
                "oldTextSha256": _sha(old),
                "newTextSha256": _sha(new),
                "oldChars": len(old),
                "newChars": len(new),
                "oldHead": old[:160],
                "newHead": new[:160],
            })
    return page_match, {
        "uniquePagesChecked": len(pages),
        "pagesMatched": sum(1 for ok in page_match.values() if ok),
        "pagesChanged": len(changed),
        "pagesMissingText": missing,
        "changedPages": changed,
    }


def _refresh_entries(data: dict[str, Any], page_match: dict[int, bool]) -> tuple[dict[str, Any], dict[str, Any]]:
    refreshed = copy.deepcopy(data)
    stay_entries_seen = 0
    relabelled = 0
    downgraded_source_confirmed = 0
    changed_entry_ids: list[str] = []

    for entry in refreshed.get("entries", []):
        if not isinstance(entry, dict) or not _is_stay_entry(entry):
            continue
        stay_entries_seen += 1
        pages = _entry_pages(entry)
        pages_ok = bool(pages) and all(page_match.get(page) for page in pages)
        ms = entry.setdefault("manualSource", {})
        ms["file"] = NEW_STAY_FILE
        ms["manualVersion"] = NEW_STAY_MANUAL_VERSION
        ms["sourceRevisionDate"] = NEW_STAY_SOURCE_DATE
        ms["sourceFileSha256"] = NEW_STAY_SHA256
        ms["sourceArtifactHwp"] = NEW_STAY_HWP
        ms["hwpExtractionRole"] = "stored_only"
        note = str(entry.get("verificationNote") or "")
        if note:
            note = note.replace(OLD_STAY_FILE, NEW_STAY_FILE)

        if pages_ok:
            entry["juneRefreshStatus"] = "verified_page_text_match"
            if note and "June refresh audit:" not in note:
                note = (
                    note.rstrip()
                    + " June refresh audit: cited page text was compared against the "
                    "2026-06-01 current stay manual PDF and matched the prior current source."
                )
            relabelled += 1
        else:
            entry["juneRefreshStatus"] = "requires_reextraction_page_text_changed"
            entry["reviewStatus"] = "needs_human_review"
            if note and "June refresh audit:" not in note:
                note = (
                    note.rstrip()
                    + " June refresh audit: cited page text changed in the 2026-06-01 "
                    "current stay manual PDF; this entry is candidate evidence until "
                    "the section is re-extracted and reviewed."
                )
            if _is_source_confirmed(entry):
                entry["confidence"] = "MEDIUM"
                entry["readinessLabel"] = "NEEDS_PAGE_CITATION"
                downgraded_source_confirmed += 1
            changed_entry_ids.append(
                str(entry.get("entryId") or entry.get("statusCode") or "unknown")
                + ":"
                + str(entry.get("procedureType") or "unknown")
            )
        if note:
            entry["verificationNote"] = note

    refreshed["generated"] = str(date.today())
    refreshed["description"] = (
        "Structured manual-evidence requirements layer refreshed for the "
        "2026-06-01 stay/residence PDF. Stay/residence entries were relabelled "
        "only after page-text comparison against the prior current stay PDF; "
        "changed pages are retained as candidate evidence pending re-extraction."
    )
    refreshed["manualSources"] = dict(refreshed.get("manualSources") or {})
    refreshed["manualSources"]["stay"] = NEW_STAY_FILE
    refreshed["manualSourceArtifacts"] = {
        "stayPdf": NEW_STAY_FILE,
        "stayPdfSha256": NEW_STAY_SHA256,
        "stayPdfSourceDate": NEW_STAY_SOURCE_DATE,
        "stayHwp": NEW_STAY_HWP,
        "stayHwpExtractionRole": "stored_only_distribution_mode",
    }
    refreshed["provenance"] = (
        str(refreshed.get("provenance") or "")
        + " + scripts/regenerate_2026_06_01_structured_stay_manual_indexes.py"
    ).strip()
    refreshed["entryCount"] = len(refreshed.get("entries") or [])

    return refreshed, {
        "stayEntriesSeen": stay_entries_seen,
        "stayEntriesRelabelledToJunePdf": relabelled,
        "stayEntriesRequiringReextraction": len(changed_entry_ids),
        "sourceConfirmedEntriesDowngraded": downgraded_source_confirmed,
        "changedEntryKeys": changed_entry_ids[:200],
    }


def _build_index(structured: dict[str, Any]) -> dict[str, Any]:
    index: dict[str, Any] = {}
    for entry in structured.get("entries", []):
        if not isinstance(entry, dict):
            continue
        code = entry.get("statusCode")
        if not code:
            continue
        bucket = index.setdefault(code, {
            "source": str(NEW_STRUCTURED.relative_to(ROOT)),
            "entryCount": 0,
            "documentItemCount": 0,
            "readyCount": 0,
            "hasSubCodeEvidence": False,
            "hasScenarioEvidence": False,
            "requiresHumanReview": False,
            "boundaryTypes": {},
            "procedureTypes": {},
            "confidence": {},
            "mappedProductionCodes": [code],
        })
        bucket["entryCount"] += 1
        bucket["documentItemCount"] += len(entry.get("documents") or [])
        if _is_source_confirmed(entry):
            bucket["readyCount"] += 1
        if entry.get("subCode") or entry.get("subCodesCovered"):
            bucket["hasSubCodeEvidence"] = True
        if entry.get("scenarioId") or entry.get("scenarioNameKo"):
            bucket["hasScenarioEvidence"] = True
        if entry.get("reviewStatus") == "needs_human_review":
            bucket["requiresHumanReview"] = True
        for field, target in (
            ("boundaryType", "boundaryTypes"),
            ("procedureType", "procedureTypes"),
            ("confidence", "confidence"),
        ):
            value = entry.get(field)
            if value:
                bucket[target][value] = bucket[target].get(value, 0) + 1

    return {
        "schemaVersion": "1.0",
        "generated": str(date.today()),
        "description": (
            "Join table from statusCode to summary metrics for "
            "structured_requirements_2026_06_01.json."
        ),
        "structuredLayer": str(NEW_STRUCTURED.relative_to(ROOT)),
        "statusCount": len(index),
        "index": dict(sorted(index.items())),
    }


def main() -> int:
    old = _load_json(OLD_STRUCTURED)
    stay_entries = [
        entry for entry in old.get("entries", [])
        if isinstance(entry, dict) and _is_stay_entry(entry)
    ]
    page_match, page_audit = _compare_pages(stay_entries)
    refreshed, refresh_audit = _refresh_entries(old, page_match)
    index = _build_index(refreshed)

    audit = {
        "generated": str(date.today()),
        "script": "scripts/regenerate_2026_06_01_structured_stay_manual_indexes.py",
        "inputs": {
            "oldStructured": str(OLD_STRUCTURED.relative_to(ROOT)),
            "oldIndex": str(OLD_INDEX.relative_to(ROOT)),
            "oldStayPdf": OLD_STAY_FILE,
            "newStayPdf": NEW_STAY_FILE,
            "newStayHwp": NEW_STAY_HWP,
        },
        "outputs": {
            "structured": str(NEW_STRUCTURED.relative_to(ROOT)),
            "index": str(NEW_INDEX.relative_to(ROOT)),
            "auditReport": str(AUDIT_REPORT.relative_to(ROOT)),
        },
        "pageAudit": page_audit,
        "refreshAudit": refresh_audit,
        "hwpHandling": {
            "path": NEW_STAY_HWP,
            "role": "stored_only_official_artifact",
            "reason": "HWP distribution-mode body extraction is blocked; PDF is the extraction source.",
        },
    }

    _write_json(NEW_STRUCTURED, refreshed)
    _write_json(NEW_INDEX, index)
    _write_json(AUDIT_REPORT, audit)

    print(f"Wrote {NEW_STRUCTURED.relative_to(ROOT)}")
    print(f"Wrote {NEW_INDEX.relative_to(ROOT)}")
    print(f"Wrote {AUDIT_REPORT.relative_to(ROOT)}")
    print(
        "Stay pages checked: {uniquePagesChecked}; matched: {pagesMatched}; changed: {pagesChanged}".format(
            **page_audit
        )
    )
    print(
        "Stay entries relabelled: {stayEntriesRelabelledToJunePdf}; requiring re-extraction: {stayEntriesRequiringReextraction}; source-confirmed downgraded: {sourceConfirmedEntriesDowngraded}".format(
            **refresh_audit
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
