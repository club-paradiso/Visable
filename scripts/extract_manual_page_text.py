#!/usr/bin/env python3
"""Deterministic per-page text extraction + footer verification for the
current official manuals (stay / visa) PDFs.

This is the repeatable evidence helper used by the source-confirmed
procedure-coverage work. It extracts the text of one or more *printed*
pages from a committed manual PDF using PyMuPDF and asserts that the
printed footer ("- N -") matches the requested printed page number, so a
citation of "p. N" is provably the page whose footer reads "- N -".

The current committed PDFs are 1:1 — printed page N == 1-based PDF page N —
but this tool re-verifies that on every call rather than assuming it.

Usage:
    python3 scripts/extract_manual_page_text.py stay 44
    python3 scripts/extract_manual_page_text.py stay 43 44 --chars 1200
    python3 scripts/extract_manual_page_text.py visa 226

Requires: PyMuPDF (``pip install pymupdf``). If unavailable the tool exits
non-zero with a clear message rather than guessing.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_MANUALS = {
    "stay": os.path.join(
        _REPO, "docs", "source-manuals", "2026-06", "stay_manual_2026_06_01.pdf"
    ),
    "visa": os.path.join(
        _REPO, "docs", "source-manuals", "2026-05", "visa_manual_2026_05.pdf"
    ),
}

_FOOTER_RE = re.compile(r"-\s*(\d+)\s*-")


def verify_footer(page_text: str, printed_page: int) -> bool:
    """True if the page's leading footer token equals ``printed_page``."""
    head = page_text[:40]
    found = _FOOTER_RE.findall(head)
    return bool(found) and int(found[0]) == printed_page


def extract(manual: str, pages: list[int], chars: int) -> int:
    try:
        import fitz  # type: ignore  # PyMuPDF
    except ImportError:
        print(
            "ERROR: PyMuPDF is required (pip install pymupdf).",
            file=sys.stderr,
        )
        return 2

    path = _MANUALS.get(manual)
    if not path or not os.path.exists(path):
        print(f"ERROR: unknown/missing manual '{manual}' ({path})", file=sys.stderr)
        return 2

    doc = fitz.open(path)
    rc = 0
    for printed in pages:
        idx = printed - 1  # 1:1 mapping; re-verified below.
        if idx < 0 or idx >= doc.page_count:
            print(f"ERROR: printed page {printed} out of range", file=sys.stderr)
            rc = 1
            continue
        text = doc[idx].get_text()
        ok = verify_footer(text, printed)
        flag = "OK" if ok else "FOOTER-MISMATCH"
        if not ok:
            rc = 1
        print(f"===== {manual} printed page {printed} (PDF index {idx}) [{flag}] =====")
        print(text[:chars])
        print()
    return rc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manual", choices=sorted(_MANUALS), help="stay or visa")
    parser.add_argument("pages", type=int, nargs="+", help="printed page number(s)")
    parser.add_argument("--chars", type=int, default=2000, help="chars per page")
    args = parser.parse_args(argv)
    return extract(args.manual, args.pages, args.chars)


if __name__ == "__main__":
    raise SystemExit(main())
