"""Page text with the tables kept, for the pages whose PDF text lost them (opt-in).

Why: on the six real-manual sets (v2, r3) six of the fifteen wrong answers came from
PDF text in which a table had been flattened: a column header sat inside a list
("사증발급인정서 ③ 학위증"), a note was glued to the rule it excludes, a country row
was read across ("캐나다 H-1 체류기간 40시간"), or "15" and "일 이내" were split by a
blank line. The approved HWP original of the same edition keeps those tables; its
conversion (docs/source-manuals/2026-10-19/markdown/*.md) has them as HTML.

How: every paragraph line and table row of the HWP markdown is assigned, in order, to
the PDF page whose text it overlaps most (4-character shingles, a small window around
the current page). A page's layout text is its lines in HWP order, a table row as
"| cell | cell |". It is used only when it carries the same content as the approved
PDF page: at most ``MAX_MISSING_LINES`` of the page's lines missing (those are appended,
so nothing is lost) and at most ``MAX_FOREIGN`` of its shingles from elsewhere.
Otherwise the PDF text stays.

Approval: the markdown is registered as needs_review (data/manual_approval_index.json).
A layout page is accepted here because its content was checked against the approved
PDF page, the way that index lets derived chunks inherit a page's approval; it is
not a human review. The layout text gets its own approval hash, so the integrity check
still holds. Runs use it only with ``run_smoke.py --layout``; the facts, their quotes
and every earlier run keep the PDF text.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import trust_gate

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
MARKDOWN = {
    "visa_manual_2026_10_19_pdf": REPO_ROOT / "docs/source-manuals/2026-10-19/markdown/visa_manual_261019.md",
    "stay_manual_2026_10_19_pdf": REPO_ROOT / "docs/source-manuals/2026-10-19/markdown/stay_manual_261019.md",
}
LAYOUT_LEDGER = HERE / "ledgers" / "manual_2026_10_19_layout.jsonl"
MAX_MISSING_LINES = 0.2 # share of the PDF page's lines the HWP lines may lack
MAX_FOREIGN = 0.10      # share of the layout text's shingles the PDF page does not have
_MATCH = 0.5            # a line goes to a page when this share of its shingles is there
_FOOTER_RE = re.compile(r"^\s*-\s*\d+\s*-\s*$")   # "- 27 -"


def _grams(text: str, n: int = 4) -> set:
    s = re.sub(r"[^가-힣0-9A-Za-z]", "", text)
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def _cell_grams(lines: List[str]) -> set:
    """Shingles within each table cell or line part, so a row whose cells the PDF prints
    in another order is not counted as text from elsewhere."""
    out: set = set()
    for line in lines:
        for part in re.split(r" \| | / ", line):
            out |= _grams(part)
    return out


def _carried(line: str, lay: set, flat: str) -> bool:
    """The layout text has this PDF line: most of its words (the PDF may merge a table
    row's cells into one line, so word by word, not shingle by shingle) and every
    number in it."""
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", line)
    if words and sum(w in flat for w in words) / len(words) < 0.8:
        return False
    if not words and re.sub(r"[^가-힣0-9A-Za-z]", "", line) not in flat:
        return False
    return all(n.replace(",", "") in flat for n in re.findall(r"\d[\d,]*", line))


def _cell(raw: str) -> str:
    raw = re.sub(r"<br\s*/?>", " / ", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def markdown_units(text: str) -> List[str]:
    """Paragraph lines and table rows of the HWP markdown, in order. A very long table
    row (a whole section in one cell) is split at its line breaks."""
    units: List[str] = []
    pos = 0
    for m in re.finditer(r"<table>.*?</table>", text, re.S):
        units += _lines(text[pos:m.start()])
        for row in re.findall(r"<tr>(.*?)</tr>", m.group(0), re.S):
            cells = [_cell(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)]
            line = "| " + " | ".join(cells) + " |"
            if len(line) > 400:
                units += [_cell(part) for part in re.split(r"<br\s*/?>", row) if _cell(part)]
            else:
                units.append(line)
        pos = m.end()
    units += _lines(text[pos:])
    return [u for u in units if u.strip()]


def _lines(chunk: str) -> List[str]:
    chunk = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", chunk)
    out = []
    for part in re.split(r"<br\s*/?>|\n", chunk):
        line = _cell(part).lstrip("#").strip()
        if line:
            out.append(line)
    return out


def assign(units: List[str], pages: Dict[int, str]) -> Dict[int, List[str]]:
    """Each line goes to the page that holds most of its shingles. A line that several
    pages hold about equally (a heading the overview repeats, boilerplate) follows the
    next line whose page is clear; failing that, the page nearest the previous line.
    A line found nowhere stays with the previous line."""
    index: Dict[str, List[int]] = {}
    for p, t in pages.items():
        for gram in _grams(t):
            index.setdefault(gram, []).append(p)
    numbers = sorted(pages)
    candidates: List[Optional[List[int]]] = []
    for unit in units:
        g = _grams(unit)
        near = None
        if len(g) >= 3:
            counts: Dict[int, int] = {}
            for gram in g:
                for p in index.get(gram, ()):
                    counts[p] = counts.get(p, 0) + 1
            top = max(counts.values(), default=0)
            if top / len(g) >= _MATCH:
                near = sorted(p for p, c in counts.items() if c >= 0.9 * top)
        candidates.append(near)
    following: List[Optional[int]] = [None] * len(units)
    clear = None
    for i in range(len(units) - 1, -1, -1):
        following[i] = clear
        if candidates[i] and len(candidates[i]) == 1:
            clear = candidates[i][0]
    out: Dict[int, List[str]] = {p: [] for p in numbers}
    current = numbers[0]
    for unit, near, nxt in zip(units, candidates, following):
        if near:
            if len(near) == 1:
                current = near[0]
            elif nxt in near and nxt >= current:
                current = nxt
            else:
                current = min(near, key=lambda p: (abs(p - current) if p >= current - 1 else 10_000 + current - p))
        out[current].append(unit)
    return out


def build(path: Path = LAYOUT_LEDGER) -> Dict[str, Any]:
    import manual_ledger
    ledger = manual_ledger.load_ledger()
    rows, stats = [], {}
    for source_id, md_path in MARKDOWN.items():
        pages = {int(r["page"]): manual_ledger._page_text(source_id, int(r["page"]))["text"]
                 for r in ledger.values() if r["source_id"] == source_id}
        assigned = assign(markdown_units(md_path.read_text(encoding="utf-8")), pages)
        accepted = 0
        for page, lines in assigned.items():
            # Every line with a word or a number counts: "1년" alone in a table cell is a value.
            pdf_lines = [ln for ln in pages[page].splitlines()
                         if (len(_grams(ln)) >= 3 or re.search(r"\d", ln)) and not _FOOTER_RE.match(ln)]
            lay = _cell_grams(lines)
            flat = re.sub(r"[^가-힣0-9A-Za-z]", "", "".join(lines))
            if not pdf_lines or not lay:
                continue
            # PDF lines the HWP lines do not carry (a title, a header the PDF merged):
            # kept, appended at the end, so the page loses nothing.
            missing = [ln.strip() for ln in pdf_lines if not _carried(ln, lay, flat)]
            # A heading the HWP put on the previous page goes on top, the rest at the end.
            top = [ln for ln in missing if ln in [x.strip() for x in pdf_lines[:3]]]
            missing = [ln for ln in missing if ln not in top]
            foreign = len(lay - _grams(pages[page])) / len(lay)
            if (len(missing) + len(top)) / len(pdf_lines) > MAX_MISSING_LINES or foreign > MAX_FOREIGN:
                continue
            layout = "\n".join(top + lines + (["[PDF 쪽에만 있는 줄]"] + missing if missing else []))
            missing = top + missing
            accepted += 1
            rows.append({"id": manual_ledger.page_id(source_id, page), "text": layout,
                         "layout_sha256": trust_gate.approval_hash(layout),
                         "pdf_sha256": ledger[manual_ledger.page_id(source_id, page)]["approved_sha256"],
                         "missing_lines": len(missing), "pdf_lines": len(pdf_lines), "foreign": round(foreign, 4)})
        stats[source_id] = {"pages": len(pages), "accepted": accepted}
    header = {"kind": "artemis_manual_layout_pages", "markdown_sha256": {k: manual_ledger._sha256_file(v) for k, v in MARKDOWN.items()},
              "rule": f"HWP markdown lines assigned to PDF pages; kept when at most {MAX_MISSING_LINES} of the PDF lines are missing (appended) and foreign <= {MAX_FOREIGN}",
              "meaning": "content-checked against the approved PDF page; not a human review", "stats": stats}
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(header, ensure_ascii=False) + "\n")
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return stats


def load(path: Path = LAYOUT_LEDGER) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()[1:])}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
