#!/usr/bin/env python3
"""Promote readable 2026 HiKorea PDF manual source metadata.

This script rewrites provenance fields only. It does not change eligibility,
document, fee, period, or other legal guidance text in authoring records.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_URL = (
    "https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?"
    "BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1"
)
REVIEWED_AT = "2026-06-26T00:00:00+09:00"
AUTHORITY = "법무부 출입국·외국인정책본부"

MANUALS = {
    "visa": {
        "source_id": "visa_manual_2026_06_17_pdf",
        "manual_name": "사증민원",
        "manual_type": "visa",
        "title": "사증발급 안내매뉴얼 (2026.6; 2026-06-17 source PDF export)",
        "title_en": "Visa Issuance Guide Manual (2026.6; 2026-06-17 source PDF export)",
        "source_date": "2026-06-17",
        "pdf": "backend/data/sources/manuals/260617_visa_manual_exported.pdf",
        "txt": "backend/data/sources/manuals/260617_visa_manual_readable.txt",
        "sections": "backend/data/sources/manuals/260617_visa_manual_sections.json",
        "sha256": "c54e3b739b54e19e64e2ea6ee5bc49228194b5f164b51efa6b461534561e9fd1",
        "txt_sha256": "c4fa08b49350fc672176760868d68237d063abe03290dd490c10a28f495f6653",
        "size": 13189698,
        "pages": 487,
        "pdf_version": "1.3",
        "pdf_creation_date": "2026-06-25T14:48:48Z",
        "pdf_creation_date_source": "pdfinfo CreationDate Thu Jun 25 23:48:48 2026 KST",
        "original_filename": "260617 사증민원 자격별 안내 매뉴얼.pdf",
        "domain": "visa_issuance",
    },
    "stay": {
        "source_id": "stay_manual_2026_06_23_pdf",
        "manual_name": "체류민원",
        "manual_type": "stay",
        "title": "외국인체류 안내매뉴얼 (2026.6; 2026-06-23 source PDF export)",
        "title_en": "Foreigner Stay/Residence Guide Manual (2026.6; 2026-06-23 source PDF export)",
        "source_date": "2026-06-23",
        "pdf": "backend/data/sources/manuals/260623_stay_manual_exported.pdf",
        "txt": "backend/data/sources/manuals/260623_stay_manual_readable.txt",
        "sections": "backend/data/sources/manuals/260623_stay_manual_sections.json",
        "sha256": "00375f44b6245337813a5c36f53671f642b52c6006a65f1fcf3eb808f93fb51f",
        "txt_sha256": "18a754fe7aeba8f4701034b2818646ef631a8a7ea45d625996ad2b10ccef70da",
        "size": 14962255,
        "pages": 780,
        "pdf_version": "1.4",
        "pdf_creation_date": "2026-06-25T14:47:44Z",
        "pdf_creation_date_source": "pdfinfo CreationDate Thu Jun 25 23:47:44 2026 KST",
        "original_filename": "260623 체류민원 자격별 안내 매뉴얼.pdf",
        "domain": "stay_residence",
    },
}

OLD_SOURCE_FILES = {
    "docs/source-manuals/2026-06-17/extracted/full_text/visa_issue_manual_260617.txt": MANUALS["visa"],
    "docs/source-manuals/2026-06-17/extracted/full_text/stay_manual_260617.txt": MANUALS["stay"],
    "docs/source-manuals/2026-05/visa_manual_2026_05.pdf": MANUALS["visa"],
    "docs/source-manuals/2026-05/stay_manual_2026_05.pdf": MANUALS["stay"],
    "docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf": MANUALS["stay"],
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def registry_record(kind: str) -> dict[str, Any]:
    m = MANUALS[kind]
    return {
        "id": m["source_id"],
        "type": "pdf_manual",
        "title": m["title"],
        "title_en": m["title_en"],
        "authority": AUTHORITY,
        "version": "2026.6",
        "source_date": m["source_date"],
        "local_path": m["pdf"],
        "url": OFFICIAL_URL,
        "last_known_hash": f"sha256:{m['sha256']}",
        "last_checked_at": REVIEWED_AT,
        "language": ["ko"],
        "confidence": "high",
        "update_frequency": "irregular",
        "status": "active",
        "notes": (
            f"Readable PDF export acquired from desktop Downloads and verified by file type, "
            f"hash, pdfinfo page count ({m['pages']} pages), rendered cover, and full text "
            f"extraction. Downstream legal wording remains under manual review unless a field "
            f"was separately line-by-line certified."
        ),
    }


def update_registry() -> None:
    path = ROOT / "data/source_registry.json"
    data = load_json(path)
    new_ids = {m["source_id"] for m in MANUALS.values()}
    sources = [src for src in data["sources"] if src.get("id") not in new_ids]

    superseded = {
        "visa_manual_2026_05_pdf": "visa_manual_2026_06_17_pdf",
        "stay_manual_2026_06_01_pdf": "stay_manual_2026_06_23_pdf",
    }
    for src in sources:
        sid = src.get("id")
        if sid in superseded:
            src["status"] = "deprecated"
            src["superseded_by"] = superseded[sid]
            src["notes"] = (
                str(src.get("notes") or "").rstrip()
                + f" Superseded by {superseded[sid]} after readable 2026.6 PDF exports were verified."
            ).strip()
        if sid in {"stay_manual_2026_06_17_txt", "visa_manual_2026_06_17_txt"}:
            src["status"] = "deprecated"
            src["superseded_by"] = (
                "stay_manual_2026_06_23_pdf"
                if sid.startswith("stay_")
                else "visa_manual_2026_06_17_pdf"
            )
            src["notes"] = (
                "Deprecated reference-only text route. The active source is now the "
                f"readable PDF export {src['superseded_by']}; this text entry remains only "
                "for historical audit continuity."
            )
        if sid == "hikorea_latest_manual_notice_260623":
            src["last_checked_at"] = REVIEWED_AT
            src["notes"] = (
                "Canonical HiKorea notice for the latest official manuals. Desktop-readable "
                "PDF exports of the 260617 visa manual and 260623 stay manual were acquired "
                "and installed as active PDF manual sources in this branch. HWP/HWPX body "
                "extraction is not used as production evidence."
            )

    data["sources"] = [registry_record("visa"), registry_record("stay"), *sources]
    dump_json(path, data)


def archived_current(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": entry.get("version"),
        "source_date": entry.get("source_date"),
        "source_label": entry.get("source_label"),
        "file": entry.get("file"),
        "file_sha256": entry.get("file_sha256"),
        "file_size_bytes": entry.get("file_size_bytes"),
        "pages": entry.get("pages"),
        "verification_status": entry.get("verification_status"),
    }


def manifest_record(kind: str, old_current: dict[str, Any]) -> dict[str, Any]:
    m = MANUALS[kind]
    title_ko = "사증발급 안내매뉴얼" if kind == "visa" else "외국인체류 안내매뉴얼"
    title_en = "Visa Issuance Guide Manual" if kind == "visa" else "Foreigner Stay/Residence Guide Manual"
    role = "visa_issuance_manual" if kind == "visa" else "stay_residence_manual"
    return {
        "title_ko": title_ko,
        "title_en": title_en,
        "version": "2026.6",
        "source_date": m["source_date"],
        "source_label": f"{m['source_date']} {title_ko} (2026.6; readable PDF export installed)",
        "supersedes": old_current.get("file"),
        "authority": AUTHORITY,
        "pages": m["pages"],
        "file": m["pdf"],
        "file_sha256": m["sha256"],
        "file_size_bytes": m["size"],
        "pdf_internal_creation_date": m["pdf_creation_date"],
        "pdf_internal_title": "무제",
        "pdf_internal_producer": "macOS 버전 15.6.1(빌드 24G90) Quartz PDFContext",
        "pdf_version": m["pdf_version"],
        "role": role,
        "status": "current",
        "verification_status": "source_file_received_pdf_text_sampled",
        "verification_note": (
            f"User-provided desktop PDF export was installed at {m['pdf']}. "
            f"Identity was checked by PDF file type, SHA-256 {m['sha256']}, pdfinfo "
            f"page count ({m['pages']} pages), unencrypted status, rendered cover text, "
            f"and full pypdf text extraction into {m['txt']} with section inventory "
            f"{m['sections']}. This promotes source metadata and readable extraction "
            "availability only; existing structured legal guidance remains marked for "
            "manual review where line-by-line field certification is incomplete."
        ),
        "extraction_primary_format": "pdf",
        "extracted_text_file": m["txt"],
        "sections_file": m["sections"],
        "extracted_text_sha256": m["txt_sha256"],
        "original_filename": m["original_filename"],
        "official_notice_url": OFFICIAL_URL,
        "archived_previous_current": archived_current(old_current),
    }


def update_manifest() -> None:
    path = ROOT / "docs/source-manuals/source_manifest.json"
    data = load_json(path)
    current = data["current"]
    old_visa = deepcopy(current["visa_issuance_manual"])
    old_stay = deepcopy(current["stay_residence_manual"])
    current["visa_issuance_manual"] = manifest_record("visa", old_visa)
    current["stay_residence_manual"] = manifest_record("stay", old_stay)
    history = data.setdefault("audit_history", [])
    if not any(item.get("branch") == "data/refresh-all-statuses-from-2026-pdf-manuals" for item in history):
        history.append(
            {
                "audit_date": "2026-06-26",
                "branch": "data/refresh-all-statuses-from-2026-pdf-manuals",
                "scope": (
                    "Install readable desktop PDF exports for the 2026.6 visa and stay manuals; "
                    "extract full page-level text and promote source metadata without claiming "
                    "field-level legal certification for every structured record."
                ),
                "files_installed": [MANUALS["visa"]["pdf"], MANUALS["stay"]["pdf"]],
                "extracted_text": [MANUALS["visa"]["txt"], MANUALS["stay"]["txt"]],
                "hashes": {
                    "visa_pdf": MANUALS["visa"]["sha256"],
                    "stay_pdf": MANUALS["stay"]["sha256"],
                },
                "page_count_check": "passed (487 visa / 780 stay)",
                "decision": (
                    "advance current manual source metadata to readable 2026.6 PDFs; preserve "
                    "needsManualReview flags until line-by-line legal field certification."
                ),
            }
        )
    notes = data.setdefault("schema_notes", [])
    note = (
        "The 2026-06-26 PDF refresh uses readable desktop PDF exports as the primary extraction "
        "format; HWP/HWPX distribution-mode diagnostics are not used as readable production text."
    )
    if note not in notes:
        notes.append(note)
    dump_json(path, data)


def update_schema_invariants() -> None:
    path = ROOT / "data/schemas/source_grounding_schema.json"
    data = load_json(path)
    inv = data["manual_version_invariants"]
    inv["visa_issuance_manual"].update(
        {"version_label": "2026.6", "published_or_updated_at": "2026-06-17"}
    )
    inv["stay_residence_manual"].update(
        {"version_label": "2026.6", "published_or_updated_at": "2026-06-23"}
    )
    dump_json(path, data)


def update_manual_ref(ref: dict[str, Any]) -> bool:
    manual_type = ref.get("manualType")
    source_file = ref.get("sourceFile")
    target = None
    if source_file in OLD_SOURCE_FILES:
        target = OLD_SOURCE_FILES[source_file]
    elif manual_type == "visa":
        target = MANUALS["visa"]
    elif manual_type == "stay":
        target = MANUALS["stay"]
    else:
        return False

    ref["manualVersion"] = "2026.6"
    ref["sourceDate"] = target["source_date"]
    ref["sourceFile"] = target["txt"]
    ref["sourcePdf"] = target["pdf"]
    ref["sourceId"] = target["source_id"]
    if "confidence" in ref:
        if target["manual_type"] == "stay":
            ref["confidence"] = ref["confidence"].replace("260617", "260623_pdf")
        else:
            ref["confidence"] = ref["confidence"].replace("260617", "260617_pdf")
    return True


def walk_refs(obj: Any) -> int:
    changed = 0
    if isinstance(obj, dict):
        if {"manualType", "sourceFile"} & set(obj):
            if update_manual_ref(obj):
                changed += 1
        for value in obj.values():
            changed += walk_refs(value)
    elif isinstance(obj, list):
        for item in obj:
            changed += walk_refs(item)
    return changed


def update_status_authoring() -> None:
    statuses = sorted((ROOT / "backend/data/visa_authoring/statuses").glob("*.json"))
    for path in statuses:
        data = load_json(path)
        manual_refs_changed = walk_refs(data)
        status = data.setdefault("sourceManualStatus", {})
        status.update(
            {
                "visaManualVersion": "2026.6",
                "stayManualVersion": "2026.6",
                "verified": False,
                "needsManualReview": True,
                "stayManualSourceDate": MANUALS["stay"]["source_date"],
                "stayManualSourceFile": MANUALS["stay"]["txt"],
                "stayManualSourcePdf": MANUALS["stay"]["pdf"],
                "visaManualSourceFile": MANUALS["visa"]["txt"],
                "visaManualSourcePdf": MANUALS["visa"]["pdf"],
                "sourceDate": MANUALS["stay"]["source_date"],
            }
        )
        notes = status.setdefault("reviewNotes", [])
        note = (
            "2026-06-26 PDF refresh: readable 260617 visa and 260623 stay PDF exports "
            "are installed and full text/section inventories generated; legal fields remain "
            "needsManualReview unless separately line-by-line certified."
        )
        if isinstance(notes, list) and note not in notes:
            notes.append(note)
        status["manualRefresh2026Pdf"] = {
            "reviewed": True,
            "reviewedAt": REVIEWED_AT,
            "reviewMethod": "desktop_pdf_full_text_extraction_and_status_inventory",
            "changedFields": ["sourceMetadata", "manualRefs.sourceFile", "manualRefs.sourceDate"],
            "manualRefsUpdated": manual_refs_changed,
            "stayManualSourceId": MANUALS["stay"]["source_id"],
            "visaManualSourceId": MANUALS["visa"]["source_id"],
            "stayManualReadableText": MANUALS["stay"]["txt"],
            "visaManualReadableText": MANUALS["visa"]["txt"],
            "statusInventory": "backend/data/audits/manual_status_inventory_2026.json",
            "statusMatrix": "backend/data/audits/status_matrix_2026_pdf_refresh.json",
            "needsManualReview": True,
            "reviewReason": (
                "This refresh verifies readable source acquisition, extraction, and code inventory. "
                "It does not certify every structured eligibility/document/applicant-condition field."
            ),
        }
        dump_json(path, data)


def main() -> int:
    update_registry()
    update_manifest()
    update_schema_invariants()
    update_status_authoring()
    print("Updated 2026 PDF source metadata and authoring provenance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
