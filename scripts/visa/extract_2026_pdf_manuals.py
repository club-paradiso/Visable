#!/usr/bin/env python3
"""Extract page-level text and section records from readable 2026 PDF manuals.

The official HWP/HWPX files may be distribution/protected. This script is for
the user-provided readable PDF exports only, and preserves page traceability for
later data review.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANUALS = {
    "visa": {
        "source_id": "visa_manual_2026_06_17_pdf",
        "domain": "visa_issuance",
        "title": "사증발급 안내매뉴얼 2026.6",
        "pdf": ROOT / "backend/data/sources/manuals/260617_visa_manual_exported.pdf",
        "txt": ROOT / "backend/data/sources/manuals/260617_visa_manual_readable.txt",
        "json": ROOT / "backend/data/sources/manuals/260617_visa_manual_sections.json",
    },
    "stay": {
        "source_id": "stay_manual_2026_06_23_pdf",
        "domain": "stay",
        "title": "외국인체류 안내매뉴얼 2026.6",
        "pdf": ROOT / "backend/data/sources/manuals/260623_stay_manual_exported.pdf",
        "txt": ROOT / "backend/data/sources/manuals/260623_stay_manual_readable.txt",
        "json": ROOT / "backend/data/sources/manuals/260623_stay_manual_sections.json",
    },
}

CODE_RE = re.compile(r"\b[A-H]-\d{1,2}(?:-[0-9A-Z]+)?\b|\bK-STAR\b|\bREGION-S\b|\bYOUTH-STAY\b")
HIDDEN_CHARS = dict.fromkeys(map(ord, "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u200b\u200c\u200d\ufeff\u202f\u00a0"), " ")

logging.getLogger("pypdf").setLevel(logging.ERROR)


def code_sort_key(code: str) -> tuple:
    if code in {"K-STAR", "REGION-S", "YOUTH-STAY"}:
        return ("Z", code)
    parts = code.split("-")
    out: list[object] = [parts[0]]
    for part in parts[1:]:
        match = re.match(r"(\d+)(.*)", part)
        if match:
            out.extend([int(match.group(1)), match.group(2)])
        else:
            out.extend([999, part])
    return tuple(out)


def is_subcode(code: str) -> bool:
    if code in {"K-STAR", "REGION-S", "YOUTH-STAY"}:
        return False
    parts = code.split("-")
    return len(parts) > 2


def normalize_line(line: str) -> str:
    line = line.translate(HIDDEN_CHARS)
    line = re.sub(r"[ \t\r\f\v]+", " ", line).strip()
    return line


def normalize_text(text: str) -> str:
    lines = [normalize_line(line) for line in text.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def extract_with_pdfplumber(path: Path) -> list[str]:
    try:
        import pdfplumber  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pdfplumber is not available") from exc

    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text(x_tolerance=1, y_tolerance=3) or "")
    return pages


def extract_with_pypdf(path: Path) -> list[str]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pypdf is not available") from exc

    reader = PdfReader(str(path))
    return [(page.extract_text() or "") for page in reader.pages]


def first_heading(text: str) -> str:
    for line in text.splitlines():
        clean = normalize_line(line)
        if not clean or re.fullmatch(r"-?\s*\d+\s*-?", clean):
            continue
        if len(clean) <= 140:
            return clean
    return ""


def extract_manual(name: str, use_pdfplumber: bool = False) -> dict:
    meta = MANUALS[name]
    pdf_path = meta["pdf"]
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    if use_pdfplumber:
        try:
            raw_pages = extract_with_pdfplumber(pdf_path)
            method = "pdfplumber"
        except RuntimeError:
            raw_pages = extract_with_pypdf(pdf_path)
            method = "pypdf"
    else:
        raw_pages = extract_with_pypdf(pdf_path)
        method = "pypdf"

    total = len(raw_pages)
    sections: list[dict] = []
    txt_parts: list[str] = []
    for idx, raw in enumerate(raw_pages, start=1):
        text = normalize_text(raw)
        codes = sorted(set(CODE_RE.findall(text)), key=code_sort_key)
        subcodes = [code for code in codes if is_subcode(code)]
        title = f"{meta['title']} / PDF page {idx} of {total}"
        txt_parts.append(f"===== {title} =====")
        txt_parts.append(text)
        txt_parts.append("")
        sections.append(
            {
                "source_id": meta["source_id"],
                "source_file": str(pdf_path.relative_to(ROOT)),
                "page": idx,
                "heading": first_heading(text),
                "text": text,
                "status_codes_detected": codes,
                "subcodes_detected": subcodes,
                "domain": meta["domain"],
            }
        )

    meta["txt"].parent.mkdir(parents=True, exist_ok=True)
    meta["txt"].write_text("\n".join(txt_parts), encoding="utf-8")
    meta["json"].write_text(json.dumps(sections, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "manual": name,
        "method": method,
        "pages": total,
        "txt": str(meta["txt"].relative_to(ROOT)),
        "json": str(meta["json"].relative_to(ROOT)),
        "chars": sum(len(s["text"]) for s in sections),
        "distinct_codes": len({c for s in sections for c in s["status_codes_detected"]}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual", choices=["visa", "stay", "all"], default="all")
    parser.add_argument(
        "--pdfplumber",
        action="store_true",
        help="use pdfplumber for higher-fidelity page layout; slower on full manuals",
    )
    args = parser.parse_args(argv)

    names = ["visa", "stay"] if args.manual == "all" else [args.manual]
    results = []
    try:
        for name in names:
            results.append(extract_manual(name, use_pdfplumber=args.pdfplumber))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
