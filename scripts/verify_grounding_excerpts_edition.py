#!/usr/bin/env python3
"""Re-check every runtime-grounded manual excerpt against a newer PDF edition.

For each grounding in backend/data/manual_grounding/stay_manual_grounding_2026_05.json
and each HIGH entry in structured_requirements_2026_06_01.json, the cited
excerpt must still be there word for word (after whitespace/symbol
normalization) on the NEW edition's pages. The new page range comes from where
the lines actually are, searched in the pages the old range maps to by content
(scripts/crosswalk_manual_pdf_pages.py), never from the old numbers.

Read-only. With --out it writes the JSON verdict; it never edits a data file.

Usage:
  python3 scripts/verify_grounding_excerpts_edition.py stay_manual_2026_09_18_pdf stay_manual_2026_10_19_pdf \
      --hwp-text docs/source-manuals/2026-10-19/extracted/full_text/stay_manual_261019.txt --out audits/manual-refresh-20261019/grounding_excerpt_check.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from crosswalk_manual_pdf_pages import crosswalk, load, norm  # noqa: E402

GROUNDING = ROOT / "backend/data/manual_grounding/stay_manual_grounding_2026_05.json"
STRUCTURED = ROOT / "backend/data/manual_grounding/structured_requirements_2026_06_01.json"
MIN_LINE = 6
WEAK = 14


def excerpt_lines(text: str) -> list[str]:
    out = []
    for line in str(text or "").splitlines():
        n = norm(line)
        if len(n) >= MIN_LINE:
            out.append(line.strip())
    return out


def window_for(old_range: tuple[int, int], cw: dict, new_pages: dict[int, str]) -> set[int]:
    """New pages the old range maps to by content. An old page without a
    content match (a near-empty page) takes the offset of the nearest mapped
    page before it, so it still gets a window; one page of slack on each side
    covers a section that reflowed across a page break."""
    def offset_near(p: int) -> int:
        for q in sorted(cw, key=lambda x: (abs(x - p), x)):
            pages = cw[q].get("pages") or []
            if pages and abs(q - p) <= 6:
                return pages[0] - q
        return 0

    window: set[int] = set()
    for p in range(old_range[0], old_range[1] + 1):
        pages = cw.get(p, {}).get("pages") or []
        window.update(pages if pages else [p + offset_near(p)])
    window |= {min(window) - 1, max(window) + 1}
    return {p for p in window if p in new_pages}


def _spans_break(n: str, page: str, nxt: str) -> bool:
    """True when the line starts at the end of ``page`` and finishes at the
    start of the next page (a line broken by a page break)."""
    if not nxt:
        return False
    for k in range(len(n) - 4, 7, -1):
        if page.endswith(n[:k]) and nxt[: 400].startswith(n[k:]):
            return True
    return False


def _locate(lines: list[str], start: int, window: list[int], normed: dict[int, str],
            hwp_norm: str, joined: str) -> dict:
    missing, interleaved, spans = [], 0, []
    cur = start
    for line in lines:
        n = norm(line)
        # verbatim in the HWP paragraph text, or whole in the PDF text layer (a line
        # the old extraction joined from two HWP paragraphs exists only there)
        if n not in hwp_norm and n not in joined:
            missing.append(line)
            continue
        if len(n) < WEAK:
            # a short generic label ("체류기간 연장허가") matches many pages and,
            # when the PDF interleaves it with a side label, none in order: it must
            # be in the text, but it does not decide the page range
            continue
        head, tail = n[:14], n[-14:]
        located = None
        pages_from_cur = [q for q in window if q >= cur]
        for p in pages_from_cur:
            nxt = normed.get(p + 1, "")
            if n in normed[p]:
                located = (p, p)
                break
            if _spans_break(n, normed[p], nxt):
                located = (p, p + 1)
                break
        if located is None:
            # the PDF interleaves a side label into the line: first and last words
            # sit on the same page or on adjacent pages
            for p in pages_from_cur:
                nxt = normed.get(p + 1, "")
                if head in normed[p] and (tail in normed[p] or tail in nxt):
                    located = (p, p if tail in normed[p] else p + 1)
                    interleaved += 1
                    break
        if located is None:
            missing.append(line)
            continue
        spans.append(located)
        cur = located[1]
    pages = sorted({q for sp in spans for q in range(sp[0], sp[1] + 1)})
    return {"pages": pages, "missing": missing, "interleaved_lines": interleaved, "start": start}


def check(excerpt: str, old_range: tuple[int, int], cw: dict, new_pages: dict[int, str], hwp_norm: str) -> dict:
    """Every excerpt line must be verbatim in the edition's HWP text (the
    document's own paragraph text, free of PDF column interleaving) or whole in
    the PDF text layer, AND be located on the PDF pages: whole on one page or
    across a page break, or, where the PDF text layer interleaves a table's
    side label into the line, by its first and last words on adjacent PDF
    lines. Lines are located in order. A generic first line ("체류기간 연장허가")
    can match many pages, so every window page is tried as the start and the
    first start that places all lines wins (otherwise the one placing most)."""
    window = sorted(window_for(old_range, cw, new_pages))
    normed = {p: norm(new_pages[p]) for p in window}
    joined = "".join(normed[p] for p in window)
    lines = excerpt_lines(excerpt)
    best = None
    for start in window:
        r = _locate(lines, start, window, normed, hwp_norm, joined)
        if best is None or len(r["missing"]) < len(best["missing"]):
            best = r
        if not r["missing"]:
            break
    best = best or {"pages": [], "missing": lines, "interleaved_lines": 0, "start": None}
    return {"window": window, "pages": best["pages"], "missing": best["missing"],
            "interleaved_lines": best["interleaved_lines"], "ok": bool(best["pages"]) and not best["missing"]}


def fmt(pages: list[int]) -> str:
    return f"{pages[0]}-{pages[-1]}" if len(pages) > 1 else str(pages[0])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("old_id")
    ap.add_argument("new_id")
    ap.add_argument("--hwp-text", type=Path, required=True,
                    help="the new edition's HWP extraction (scripts/decrypt_hwp_distribution.py)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    old, new = load(args.old_id), load(args.new_id)
    cw = crosswalk(old, new)
    hwp_norm = norm(args.hwp_text.read_text(encoding="utf-8"))
    results = []
    g = json.loads(GROUNDING.read_text(encoding="utf-8"))
    for item in g["groundings"]:
        a, _, b = str(item["page_range"]).partition("-")
        r = check(item.get("source_excerpt", ""), (int(a), int(b or a)), cw, new, hwp_norm)
        r.update(kind="grounding", id=item["grounding_id"], old_pages=item["page_range"])
        results.append(r)
    s = json.loads(STRUCTURED.read_text(encoding="utf-8"))
    for i, e in enumerate(s["entries"]):
        if e.get("confidence") != "HIGH":
            continue
        ms = e["manualSource"]
        r = check(ms.get("sourceExcerpt", ""), (ms["pageStart"], ms["pageEnd"]), cw, new, hwp_norm)
        r.update(kind="structured", id=f"{e['statusCode']}/{e.get('procedureType')}", index=i,
                 old_pages=f"{ms['pageStart']}-{ms['pageEnd']}")
        results.append(r)
    for r in results:
        r["new_pages"] = fmt(r["pages"]) if r["pages"] else None
        print(("OK  " if r["ok"] else "FAIL"), r["kind"], r["id"], r["old_pages"], "->", r["new_pages"], (r["missing"][:2] if r["missing"] else ""))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({"old": args.old_id, "new": args.new_id, "results": results}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
