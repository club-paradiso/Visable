#!/usr/bin/env python3
"""Rebuild searchable, page-addressable originals without authoring legal rules.

Install the extraction dependency with `pip install pymupdf==1.28.2`.
Input PDFs are immutable, hash-pinned user-supplied exports. Text is an aid to
finding the original page, never an automatic approval of a legal requirement.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/manual-corpus/sources.json"
NOTICE = "https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1"
CODE_RE = re.compile(r"(?<![A-Z0-9-])(?:[A-H]-\d{1,2}(?:-[A-Z0-9]+)*|K-STAR|REGION-S|YOUTH-STAY)(?![A-Z0-9-])")
DASHES = str.maketrans({c: "-" for c in "‐‑‒–—−－"})


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def extract_page_text(page) -> tuple[str, int]:
    """Remove duplicate PDF paint operations, never repeated prose by content.

    These exports paint some bold words twice at the exact same coordinates.
    Text-only de-duplication would alter legitimate wording. The geometry key
    instead retains identical words at every distinct position on the page.
    """
    seen, words, duplicates = set(), [], 0
    for word in page.get_text("words", sort=True):
        key = (word[4], *(round(value, 3) for value in word[:4]))
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        words.append(word)
    if not duplicates:
        raw = page.get_text(sort=True)
    else:
        lines, line, top = [], [], None
        for word in words:
            if top is not None and abs(word[1] - top) > 3:
                lines.append(" ".join(line))
                line = []
            if not line:
                top = word[1]
            line.append(word[4])
        if line:
            lines.append(" ".join(line))
        raw = "\n".join(lines)
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip()
                     for line in raw.splitlines()).strip(), duplicates


def build() -> dict:
    import pymupdf

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    catalog, all_sections = [], []
    # Validate ALL inputs before writing any output.
    for source in config["sources"]:
        pdf = ROOT / source["file"]
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"Source checksum mismatch: {pdf}")
        with pymupdf.open(pdf) as document:
            if len(document) != source["pages"]:
                raise ValueError(f"Source page count mismatch: {pdf}")
            sections = []
            for number, page in enumerate(document, 1):
                text, duplicate_words = extract_page_text(page)
                if not text or "\ufffd" in text:
                    raise ValueError(f"Unreadable text layer: {pdf}, page {number}")
                codes = sorted(set(CODE_RE.findall(text.upper().translate(DASHES))))
                heading = next((line for line in text.splitlines()
                                if line and not re.fullmatch(r"[-\s\d]+", line)), source["title"])
                sections.append({
                    "source_id": source["id"], "source_file": source["file"],
                    "page": number, "heading": heading[:140], "text": text,
                    "status_codes_detected": codes,
                    "subcodes_detected": [c for c in codes if c.count("-") >= 2],
                    "domain": source["domain"],
                    "has_images": bool(page.get_images()),
                    "duplicate_paint_words_removed": duplicate_words,
                })
            all_sections.append((source, sections))

    registry_path = ROOT / "data/source_registry.json"
    approval_path = ROOT / "data/manual_approval_index.json"
    manifest_path = ROOT / "docs/source-manuals/source_manifest.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for source, sections in all_sections:
        sid = source["id"]
        section_file = f"data/manual-corpus/{sid}.json"
        text_file = f"docs/source-manuals/2026-09/extracted/{sid}.txt"
        raw = "\n\n".join(f"===== PDF page {s['page']} =====\n{s['text']}" for s in sections) + "\n"
        (ROOT / text_file).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / text_file).write_text(raw, encoding="utf-8")
        write_json(ROOT / section_file, sections)
        warnings = ["PDF text layer only; image content and table cell relationships require checking the original page."]
        catalog.append({**source, "sections": section_file, "approval_state": "needs_review",
                        "official_url": NOTICE, "image_pages": sum(s["has_images"] for s in sections),
                        "characters": sum(len(s["text"]) for s in sections)})
        record = {
            "id": sid, "type": "pdf_manual", "title": source["title"],
            "title_en": source["title_en"], "authority": "법무부 출입국·외국인정책본부",
            "version": source["version"], "source_date": source["date"],
            "local_path": source["file"], "url": NOTICE,
            "last_known_hash": "sha256:" + source["sha256"],
            "last_checked_at": config["updated_at"] + "T00:00:00+09:00",
            "language": ["ko"], "confidence": "high", "update_frequency": "irregular",
            "status": "needs_manual_review", "notes": "User-supplied PDF; searchable original, pending human content approval."
        }
        registry["sources"] = [r for r in registry["sources"] if r["id"] != sid] + [record]
        # Rebuilding must never erase a review or manufacture one.
        approval["documents"].setdefault(sid, {
            "approval_state": "needs_review", "effective_date": "",
            "parser": "scripts/build_current_manual_corpus.py / PyMuPDF 1.28.2",
            "reviewer": "", "reviewed_at": "", "source_confidence": "high",
            "has_tables_or_annexes": True, "section_locator": "pdf_page",
            "source_path": source["file"], "source_sha256": source["sha256"],
            "extracted_text_path": text_file, "extraction_warnings": warnings,
            "table_extraction_warnings": warnings,
        })
        pending = {
            "role": "visa_issuance_manual" if source["domain"] == "visa_issuance" else "stay_residence_manual",
            "title_ko": source["title"], "title_en": source["title_en"],
            "version": source["version"], "source_date": source["date"],
            "status": "pending_review", "registry_id_when_promoted": sid,
            "file": source["file"], "file_sha256": source["sha256"],
            "file_size_bytes": (ROOT / source["file"]).stat().st_size,
            "pages": source["pages"], "extraction_primary_format": "pdf",
            "extracted_text_file": text_file,
            "extracted_text_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "verification_status": "source_file_pinned_page_text_extracted_pending_content_approval",
            "verification_note": warnings[0], "official_notice_url": NOTICE,
            "change_review_artifact": f"audits/manual-refresh-260921/{'visa' if source['domain'] == 'visa_issuance' else 'stay'}_pdf_comparison.md",
        }
        entries = manifest.setdefault("pending_review_editions", [])
        entries[:] = [e for e in entries if e.get("registry_id_when_promoted") != sid] + [pending]
    write_json(registry_path, registry)
    write_json(approval_path, approval)
    write_json(manifest_path, manifest)
    result = {"schema_version": 1, "updated_at": config["updated_at"], "sources": catalog,
              "total_pages": sum(s["pages"] for s in catalog)}
    write_json(ROOT / "data/manual-corpus/catalog.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
