#!/usr/bin/env python3
"""Chunk the owner-supplied HWP→Markdown texts of the 2026.9 manuals and pin
every chunk to the approved PDF page(s) it came from.

Why this exists:
  The approved 2026.9 editions are page-anchored PDFs (519 / 810 pages,
  data/manual-corpus/*_pdf.json). Their text layer flattens tables: cells of
  one row are interleaved line by line, so a 별표 or 제출서류 table reads as
  word salad. The owner supplied a Markdown conversion of the same editions'
  HWP (2026-10-19) that keeps headings and HTML <table>s, but it has no page
  numbers. A citation without a page is not a citation, so this script gives
  each Markdown chunk a PDF page by matching its text against the approved
  page text, and records how sure that match is.

What it does, deterministically and offline:
  1. Verifies each Markdown file against the SHA-256 pinned in
     docs/source-manuals/source_manifest.json (current.*.derived_texts).
  2. Splits it into lines: paragraphs, headings, and table rows rendered as
     readable "열이름: 값" text (nested tables in place, rowspans carried).
  3. Maps every line to PDF page(s) by 10-character shingles that occur on at
     most 3 pages (rarer text votes; boilerplate does not), breaking ties by
     document order. Only text inside one line or one table cell forms a
     shingle, because the PDF interleaves cells and the Markdown does not.
  4. Groups lines into chunks of at most ~1,200 characters that never cross a
     heading, a top-level table boundary or a PDF page change.
  5. Scores each chunk: coverage = the share of its shingles (or, for short
     lines, its whole normalized text) found on the chunk's own page(s).

Confidence and evidence:
  high    coverage >= 0.85, on at most 2 adjacent pages, no unresolved tie
  medium  coverage >= 0.70, on at most 3 adjacent pages
  low     coverage >= 0.30
  none    otherwise, or no line long enough to match
  Only high/medium chunks are direct_evidence: they inherit the approval of
  the PDF edition for that page. low/none chunks are kept and searchable but
  are never direct evidence. Nothing here is a human review: the Markdown is
  machine-verified against the approved text, not read line by line.

It never edits a source file, the registry or the approval index. Outputs:
  data/manual-corpus/<source_id>.json   (meta + summary + sections)

Usage:
  python3 scripts/build_manual_markdown_corpus.py           # rebuild
  python3 scripts/build_manual_markdown_corpus.py --check   # rebuild in memory, compare
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_current_manual_corpus import CODE_RE, DASHES, write_json  # noqa: E402

MANIFEST = ROOT / "docs/source-manuals/source_manifest.json"
SCHEMA_VERSION = 1
SHINGLE = 10
RARE = 3
SHORT_MIN = 4          # shorter normalized lines are not checked at all
CHUNK_CHARS = 1200
HIGH, MEDIUM, LOW = 0.85, 0.70, 0.30
DIRECT = ("high", "medium")
#: Lines this short or shorter (normalized) are matched as a whole substring
#: of the candidate page rather than by shingles.
SHORT_MAX = SHINGLE + 4

_DASH_CHARS = "‐‑‒–—―−－─﹣"
_KEEP = re.compile(r"[^0-9A-Za-z\-가-힣一-鿿]+")


def norm(text: str) -> str:
    """Same normalization as scripts/audit_manual_ref_editions_2026_09.py."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate({ord(c): "-" for c in _DASH_CHARS})
    return _KEEP.sub("", text)


def shingles(t: str) -> list[str]:
    return list(dict.fromkeys(t[i:i + SHINGLE] for i in range(len(t) - SHINGLE + 1)))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Markdown / HTML table parsing
# ---------------------------------------------------------------------------
_INLINE_TAG = re.compile(r"</?(?:u|b|i|strong|em|sup|sub|span|p|div)\b[^>]*>", re.I)
_IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img\b[^>]*>", re.I)
_MD_ESC = re.compile(r"\\([\\`*_{}\[\]()#+\-.!~|<>])")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
#: A stand-alone status title line in the stay manual ("외교(A-1)"), used as heading context.
_STATUS_TITLE = re.compile(r"^[가-힣·ㆍ\s]{1,20}\((?:[A-H]-\d{1,2}(?:-[0-9A-Z]+)*)\)$")


def clean_inline(text: str) -> str:
    text = _IMG.sub("", text)
    text = _INLINE_TAG.sub("", text)
    text = text.replace("**", "")
    text = _MD_ESC.sub(r"\1", text)
    text = html.unescape(text)
    return re.sub(r"[ \t ]+", " ", text).strip()


class Cell:
    def __init__(self, header: bool, colspan: int, rowspan: int):
        self.header, self.colspan, self.rowspan = header, colspan, rowspan
        self.items: list = []      # str lines and Table objects, in order
        self._buf: list[str] = []

    def text(self, s: str) -> None:
        self._buf.append(s)

    def br(self) -> None:
        line = clean_inline("".join(self._buf))
        if line:
            self.items.append(line)
        self._buf = []

    def close(self) -> None:
        self.br()

    @property
    def lines(self) -> list[str]:
        return [i for i in self.items if isinstance(i, str)]

    @property
    def has_table(self) -> bool:
        return any(isinstance(i, Table) for i in self.items)

    @property
    def flat(self) -> str:
        return " ".join(self.lines)


class Table:
    def __init__(self):
        self.rows: list[list[Cell]] = []


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack: list[Table] = []
        self.cells: list[Cell] = []
        self.root: Table | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            t = Table()
            if self.cells:
                self.cells[-1].br()
                self.cells[-1].items.append(t)
            elif self.root is None:
                self.root = t
            self.stack.append(t)
        elif tag == "tr" and self.stack:
            self.stack[-1].rows.append([])
        elif tag in ("td", "th") and self.stack:
            if not self.stack[-1].rows:
                self.stack[-1].rows.append([])
            def span(k):
                try:
                    return max(1, int(a.get(k) or 1))
                except ValueError:
                    return 1
            c = Cell(tag == "th", span("colspan"), span("rowspan"))
            self.stack[-1].rows[-1].append(c)
            self.cells.append(c)
        elif tag == "br" and self.cells:
            self.cells[-1].br()
        elif self.cells and tag not in ("img",):
            self.cells[-1].text(self.get_starttag_text() or "")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cells:
            self.cells.pop().close()
        elif tag == "table" and self.stack:
            self.stack.pop()
        elif self.cells and tag not in ("tr", "img", "br"):
            self.cells[-1].text(f"</{tag}>")

    def handle_data(self, data):
        if self.cells:
            self.cells[-1].text(data)

    def handle_entityref(self, name):
        if self.cells:
            self.cells[-1].text(f"&{name};")

    def handle_charref(self, name):
        if self.cells:
            self.cells[-1].text(f"&#{name};")


def is_short(cell: Cell) -> bool:
    return not cell.has_table and len(cell.lines) <= 2 and 0 < len(cell.flat) <= 40


def grid(table: Table) -> list[list[tuple[Cell, bool]]]:
    """Expand rowspans: each row becomes [(cell, carried_from_above)] in column order."""
    carry: dict[int, list] = {}
    out = []
    for row in table.rows:
        cols, col, pending = [], 0, list(row)
        while pending or col in carry:
            if col in carry:
                cell, left = carry[col]
                cols.append((cell, True))
                if left <= 1:
                    del carry[col]
                else:
                    carry[col] = [cell, left - 1]
            else:
                cell = pending.pop(0)
                cols.append((cell, False))
                if cell.rowspan > 1:
                    carry[col] = [cell, cell.rowspan - 1]
            col += cell.colspan
        out.append(cols)
    return out


_NUMBERED = re.compile(r"^\s*\d+\s*\.")


def column_headers(rows: list[list[tuple[Cell, bool]]]) -> tuple[int, list[str]]:
    """Leading all-<th> rows that read as column labels (short, not a numbered list)."""
    n = 0
    for cols in rows:
        cells = [c for c, _ in cols]
        if len(cells) >= 2 and all(c.header for c in cells) and all(is_short(c) for c in cells):
            n += 1
        else:
            break
    if not n or n >= len(rows):
        return 0, []
    head = [c for c, carried in rows[0] if not carried] if n == 1 else None
    if head is not None and sum(bool(_NUMBERED.match(c.flat)) for c in head) >= 2:
        return 0, []
    labels: dict[int, list[str]] = defaultdict(list)
    for cols in rows[:n]:
        col = 0
        for cell, _ in cols:
            for k in range(cell.colspan):
                if cell.flat not in labels[col + k]:
                    labels[col + k].append(cell.flat)
            col += cell.colspan
    width = max(labels) + 1 if labels else 0
    return n, [" ".join(labels.get(i, [])) for i in range(width)]


def table_lines(table: Table, outer: str, depth: int) -> list[dict]:
    """Render a table as readable lines. Each line keeps its match segments
    (the original cell texts) separately from its display text."""
    lines: list[dict] = []
    rows = grid(table)
    nhead, headers = column_headers(rows)
    if nhead:
        for cols in rows[:nhead]:
            texts = [c.flat for c, carried in cols if not carried]
            lines.append({"text": " | ".join(texts), "segments": texts, "label": outer, "depth": depth})

    def emit_cell(cell: Cell, label: str):
        for item in cell.items:
            if isinstance(item, Table):
                lines.extend(table_lines(item, label, depth + 1))
            else:
                lines.append({"text": item, "segments": [item], "label": label, "depth": depth})

    def join(*parts):
        return " › ".join(p for p in parts if p)[:120]

    for cols in rows[nhead:]:
        own = [(c, carried) for c, carried in cols]
        if nhead:
            col, pairs = 0, []
            for cell, carried in own:
                pairs.append((headers[col] if col < len(headers) else "", cell, carried))
                col += cell.colspan
            mine = [(h, c) for h, c, carried in pairs if not carried and c.flat]
            if all(is_short(c) or (not c.has_table and len(c.lines) <= 1) for _, c in mine):
                text = " / ".join(f"{h}: {c.flat}" if h else c.flat for h, c in mine)
                if text:
                    lines.append({"text": text, "segments": [c.flat for _, c in mine],
                                  "label": outer, "depth": depth})
                continue
            rowkey = pairs[0][1].flat if is_short(pairs[0][1]) else ""
            first = len(lines)
            for k, (h, cell, carried) in enumerate(pairs):
                if carried or (rowkey and k == 0):
                    continue
                emit_cell(cell, join(outer, rowkey, h))
            if rowkey and not pairs[0][2]:
                if len(lines) > first:
                    lines[first]["segments"] = [rowkey] + lines[first]["segments"]
                else:
                    lines.append({"text": rowkey, "segments": [rowkey], "label": outer, "depth": depth})
            continue
        cells = [c for c, _ in own]
        if len(cells) == 1:
            if not own[0][1]:
                emit_cell(cells[0], outer)
            continue
        if all(is_short(c) for c in cells):
            texts = [c.flat for c, carried in own if not carried and c.flat]
            if texts:
                lines.append({"text": " | ".join(texts), "segments": texts, "label": outer, "depth": depth})
            continue
        # Key/value row: leading short cells (including rowspan-carried ones)
        # label the content cells that follow them.
        keys, k = [], 0
        while k < len(own) - 1 and is_short(own[k][0]):
            keys.append(own[k])
            k += 1
        label = join(outer, " / ".join(c.flat for c, _ in keys))
        new_keys = [c.flat for c, carried in keys if not carried and c.flat]
        first = len(lines)
        for cell, carried in own[k:]:
            if not carried:
                emit_cell(cell, label)
        if new_keys:
            # The key text is document text too; it is matched with the first content line.
            if len(lines) > first:
                lines[first]["segments"] = new_keys + lines[first]["segments"]
            else:
                lines.append({"text": " / ".join(new_keys), "segments": new_keys,
                              "label": outer, "depth": depth})
    return lines


_PIPE_SPLIT = re.compile(r"(?<!\\)\|")
_PIPE_RULE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-*:?\s*$")


def pipe_table_html(rows: list[str]) -> str:
    """A Markdown pipe table as the same HTML the converter emits elsewhere."""
    rule = next((k for k, r in enumerate(rows) if _PIPE_RULE.match(r)), None)
    parts = ["<table>"]
    for k, r in enumerate(rows):
        if k == rule:
            continue
        cells = _PIPE_SPLIT.split(r.strip())
        if cells and not cells[0].strip():
            cells = cells[1:]
        if cells and not cells[-1].strip():
            cells = cells[:-1]
        tag = "th" if rule is not None and k < rule else "td"
        parts.append("<tr>" + "".join(f"<{tag}>{c.strip()}</{tag}>" for c in cells) + "</tr>")
    parts.append("</table>")
    return "\n".join(parts)


def parse_markdown(raw: str) -> list[dict]:
    """Markdown → ordered lines with heading context and table identity."""
    out: list[dict] = []
    path: list[tuple[int, str]] = []
    status_title = ""
    lines = raw.splitlines()
    i, table_no = 0, 0

    def context():
        # A stand-alone status title ("외교(A-1)") opens a chapter: only the
        # headings that came after it describe the text that follows.
        return ([status_title] if status_title else []) + [t for _, t in path]

    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("|"):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                buf.append(lines[i])
                i += 1
            parser = TableParser()
            parser.feed(pipe_table_html(buf))
            parser.close()
            table_no += 1
            if parser.root is not None:
                for row in table_lines(parser.root, "", 0):
                    row.update(kind="table", table=table_no, headings=context())
                    out.append(row)
            continue
        if "<table" in line.lower():
            depth, buf = 0, []
            while i < len(lines):
                l = lines[i]
                depth += len(re.findall(r"<table\b", l, re.I)) - len(re.findall(r"</table>", l, re.I))
                buf.append(l)
                i += 1
                if depth <= 0:
                    break
            parser = TableParser()
            parser.feed("\n".join(buf))
            parser.close()
            table_no += 1
            if parser.root is not None:
                for row in table_lines(parser.root, "", 0):
                    row.update(kind="table", table=table_no, headings=context())
                    out.append(row)
            continue
        i += 1
        m = _HEADING.match(line)
        if m:
            text = clean_inline(m.group(2))
            if not text:
                continue
            level = len(m.group(1))
            path[:] = [p for p in path if p[0] < level] + [(level, text)]
            if level <= 2:
                status_title = ""
            out.append({"text": text, "segments": [text], "label": "", "kind": "heading",
                        "headings": context(), "depth": 0})
            continue
        text = clean_inline(line)
        if not text:
            continue
        if _STATUS_TITLE.match(text):
            status_title = text
            path.clear()
            out.append({"text": text, "segments": [text], "label": "", "kind": "heading",
                        "headings": context(), "depth": 0})
            continue
        out.append({"text": text, "segments": [text], "label": "", "kind": "text",
                    "headings": context(), "depth": 0})
    return out


# ---------------------------------------------------------------------------
# Page mapping
# ---------------------------------------------------------------------------
class PageIndex:
    def __init__(self, rows: list[dict]):
        self.text = {r["page"]: norm(r["text"]) for r in rows}
        self.grams = {p: set(shingles(t)) for p, t in self.text.items()}
        where: dict[str, list[int]] = defaultdict(list)
        for p, gs in self.grams.items():
            for g in gs:
                where[g].append(p)
        self.where = where
        self.last = max(self.text)


def map_line(idx: PageIndex, line: dict, cursor: int) -> dict:
    """Pick the page(s) holding this line's text; return weight/matched/pages."""
    segs = [norm(s) for s in line["segments"]]
    segs = [s for s in segs if len(s) >= SHORT_MIN]
    if not segs:
        return {"weight": 0, "matched": 0, "pages": [], "anchored": False, "tie": False, "by_order": False,
                "best": None, "grams": [], "short": []}
    grams = [g for s in segs if len(s) > SHORT_MAX for g in shingles(s)]
    votes: Counter = Counter()
    for g in grams:
        pages = idx.where.get(g)
        if pages and len(pages) <= RARE:
            for p in pages:
                votes[p] += 1.0 / len(pages)
    short = [s for s in segs if len(s) <= SHORT_MAX]
    tie = by_order = False
    good: list[int] = []
    if votes:
        top, total = max(votes.values()), sum(votes.values())
        near = lambda p: cursor - 1 <= p <= cursor + 8  # noqa: E731
        cands = sorted(p for p, v in votes.items() if v >= 0.3 * top or near(p))

        def span(c):
            return sorted([c] + [nb for nb in (c - 1, c + 1) if votes.get(nb, 0) >= 0.15 * total])

        def cover(c):
            pool = set().union(*(idx.grams.get(q, set()) for q in span(c)))
            return sum(1 for g in grams if g in pool) / len(grams)

        scored = {c: cover(c) for c in cands}
        best_cov = max(scored.values())
        # Identical text can sit on several pages (a chapter repeated in
        # another chapter, shared boilerplate). Among the pages that hold the
        # line equally well, document order decides: prefer the one at or just
        # after the cursor.
        good = [c for c, v in scored.items() if v >= best_cov - 0.05]
        best = min(good, key=lambda p: (0 if near(p) else 1, abs(p - cursor), p))
        rivals = [c for c in good if abs(c - best) > 2]
        by_order = bool(rivals) and near(best)
        tie = bool(rivals) and not near(best)
        pages = span(best)
        best_page = best
        anchored = True
    else:
        pages, anchored = [cursor + d for d in (0, 1) if 1 <= cursor + d <= idx.last], False
    pageset = set().union(*(idx.grams.get(p, set()) for p in pages)) if pages else set()
    weight = len(grams) + sum(len(s) for s in short)
    matched = sum(1 for g in grams if g in pageset)
    joined = "".join(idx.text.get(p, "") for p in pages)
    matched += sum(len(s) for s in short if s in joined)
    if not anchored:
        # A short line with no shingle votes is placed at the cursor; it is
        # only counted as found if it literally occurs on that page.
        hits = [p for p in pages if any(s in idx.text.get(p, "") for s in short)]
        pages = hits[:1] or pages[:1]
    return {"weight": weight, "matched": matched, "pages": pages, "anchored": anchored, "tie": tie,
            "by_order": by_order, "best": pages[0] if not anchored else best_page,
            "grams": grams, "short": short, "cands": good if anchored else []}


def confidence(coverage: float, pages: list[int], tie: bool, anchored: bool) -> str:
    span = (pages[-1] - pages[0] + 1) if pages else 99
    if not pages:
        return "none"
    if not anchored:
        # Only short lines, placed by document order and found literally on
        # that page: a plausible location, never strong enough to cite.
        return "low" if coverage >= HIGH else "none"
    if tie:
        # Equally good matches on distant pages: the text is real, its page is not settled.
        return "low" if coverage >= LOW else "none"
    if coverage >= HIGH and span <= 2:
        return "high"
    if coverage >= MEDIUM and span <= 3:
        return "medium"
    if coverage >= LOW:
        return "low"
    return "none"


def build_chunks(lines: list[dict], idx: PageIndex) -> list[dict]:
    cursor = 1
    for line in lines:
        m = map_line(idx, line, cursor)
        line["map"] = m
        if m["anchored"] and m["weight"] >= 20 and not m["tie"] and m["matched"] >= 0.6 * m["weight"]:
            cursor = m["pages"][0]

    chunks: list[dict] = []
    cur: list[dict] = []

    def page_of(line):
        return line["map"]["best"]

    def flush():
        if cur:
            chunks.append(make_chunk(cur, len(chunks) + 1, idx))
            cur.clear()

    for line in lines:
        if cur:
            prev = cur[-1]
            size = sum(len(l["text"]) + len(l["label"]) for l in cur)
            same_block = (line["kind"] == "table") == (prev["kind"] == "table") and \
                line.get("table") == prev.get("table")
            page_now = page_of(line) if line["map"]["anchored"] else None
            pages_cur = [p for l in cur if l["map"]["anchored"] for p in l["map"]["pages"]]
            new_page = page_now is not None and pages_cur and page_now > max(pages_cur)
            if line["kind"] == "heading" or not same_block or new_page or \
                    size + len(line["text"]) > CHUNK_CHARS or line["headings"] != prev["headings"]:
                # Keep a heading with the text it introduces.
                if not (prev["kind"] == "heading" and line["kind"] != "heading"
                        and size + len(line["text"]) <= CHUNK_CHARS and not new_page):
                    flush()
        cur.append(line)
    flush()
    return sequence_check(chunks)


#: A direct chunk whose page is this far from BOTH neighbouring direct chunks,
#: while those neighbours agree with each other, contradicts document order.
SEQ_GAP = 10


def sequence_check(chunks: list[dict]) -> list[dict]:
    """Demote chunks whose page contradicts the pages around them.

    The Markdown follows the document's order, so a chunk mapped 150 pages
    away from the chunks before and after it has almost always matched the
    same wording somewhere else (repeated boilerplate). It is kept, flagged
    out_of_sequence, and is not direct evidence.
    """
    direct = [c for c in chunks if c["direct_evidence"]]
    for k, c in enumerate(direct):
        prev = direct[k - 1]["pages"][0] if k else None
        nxt = direct[k + 1]["pages"][0] if k + 1 < len(direct) else None
        here = c["pages"][0]
        if prev is None or nxt is None or abs(prev - nxt) > SEQ_GAP:
            continue
        if abs(here - prev) > SEQ_GAP and abs(here - nxt) > SEQ_GAP:
            c["match"]["out_of_sequence"] = True
            c["match"]["confidence"] = "low"
            c["direct_evidence"] = False
            c["page"] = 0
    return chunks


def found_on(idx: "PageIndex", lines: list[dict], pages: list[int]) -> int:
    """How much of the lines' text is on the given pages (shingles + short lines)."""
    pool = set().union(*(idx.grams.get(p, set()) for p in pages)) if pages else set()
    joined = "".join(idx.text.get(p, "") for p in pages)
    return sum(sum(1 for g in l["map"]["grams"] if g in pool) +
               sum(len(x) for x in l["map"]["short"] if x in joined) for l in lines)


PROBE_SPLIT = re.compile(r"\n| \| | / ")


def probe_result(text: str, is_table: bool, pages: list[int], idx: "PageIndex"):
    """None when the chunk has too few probe-able fragments; else whether enough
    of them start with text that is literally on the mapped page(s). Mirrors the
    independent per-line probe in scripts/check_current_manual_corpus.mjs."""
    probes = [norm(t.split(": ")[-1])[:8] for t in PROBE_SPLIT.split(text)]
    probes = [t for t, raw in zip(probes, PROBE_SPLIT.split(text)) if len(norm(raw.split(": ")[-1])) >= 12]
    if len(probes) < 3 or not pages:
        return None
    hay = "".join(idx.text.get(p, "") for p in pages)
    found = sum(1 for t in probes if t in hay)
    return found / len(probes) >= (0.25 if is_table else 0.5)


def make_chunk(lines: list[dict], number: int, idx: "PageIndex") -> dict:
    out, last_label = [], None
    for k, l in enumerate(lines):
        label = l["label"]
        if label and (label != last_label or k == 0) and not l.get("key_only"):
            out.append(f"{label}: {l['text']}")
        else:
            out.append(l["text"])
        last_label = label
    weight = sum(l["map"]["weight"] for l in lines)
    anchored = [l for l in lines if l["map"]["anchored"]]
    pages = sorted({p for l in (anchored or lines) for p in l["map"]["pages"]})
    # A chunk is on a contiguous run of pages; outliers (a single line that
    # voted elsewhere) are reported rather than silently widening the range.
    weights = Counter()
    for l in anchored:
        for p in l["map"]["pages"]:
            weights[p] += l["map"]["weight"]
    if weights:
        core = max(weights, key=lambda p: (weights[p], -p))
        keep = {core}
        for direction in (-1, 1):
            p = core + direction
            while p in weights and weights[p] >= 0.05 * sum(weights.values()):
                keep.add(p)
                p += direction
        outliers = sorted(set(weights) - keep)
        pages = sorted(keep)
    else:
        outliers = []
    # The chunk's page is unsettled when lines that tied between distant pages
    # (and were not resolved by document order) carry much of its text.
    tie_weight = sum(l["map"]["weight"] for l in anchored
                     if l["map"]["tie"] and set(l["map"]["pages"]) & set(pages))
    tie = tie_weight > 0.2 * weight if weight else False
    # Coverage is measured against the chunk's final page(s) only, so text
    # that matched on some other page does not count for this one.
    matched = found_on(idx, lines, pages)
    coverage = (matched / weight) if weight else 0.0
    # Line-level ties were settled by document order; the whole chunk's text
    # is more telling than any one line. If another page the lines pointed at
    # holds the chunk clearly better, the chunk moves there.
    repaged = False
    if anchored and weight:
        cands = sorted({c for l in anchored for c in l["map"]["cands"]} - set(pages))
        windows = [w for c in cands for w in ([c], [c, c + 1], [c - 1, c]) if w[0] >= 1 and w[-1] <= idx.last]
        scored = [(found_on(idx, lines, w) / weight, w) for w in windows]
        if scored:
            best_cov, best_w = max(scored, key=lambda x: (x[0], -len(x[1]), -x[1][0]))
            if best_cov > coverage + 0.02:
                pages, coverage, repaged, outliers = best_w, best_cov, True, []
                tie_weight = sum(l["map"]["weight"] for l in anchored
                                 if l["map"]["tie"] and set(l["map"]["pages"]) & set(pages))
                tie = tie_weight > 0.2 * weight
    conf = confidence(coverage, pages, tie, bool(anchored))
    text = "\n".join(out)
    probe = probe_result(text, any(l["kind"] == "table" for l in lines), pages, idx)
    if conf in DIRECT and probe is not None and not probe:
        # The text probe (the same independent check scripts/check_current_manual_corpus.mjs
        # runs) found too little of this chunk's wording on its mapped page(s): repeated
        # bilingual form text can fool the shingle vote. Such a chunk is not direct evidence.
        conf = "low"
    heads = lines[0]["headings"]
    heading = " › ".join(heads[-2:]) if heads else ""
    first = next((l["text"] for l in lines if l["kind"] != "heading"), lines[0]["text"])
    if not heading:
        heading = first
    return {
        "chunk": number, "kind": "table" if any(l["kind"] == "table" for l in lines) else "text",
        # Document-order cell/line text without the rendered labels; used by
        # audits that need contiguous wording, never written to the corpus.
        "_raw": "\n".join(seg for l in lines for seg in l["segments"]),
        "heading": heading[:140], "heading_path": heads, "text": text,
        "pages": pages, "page": pages[0] if pages and conf in DIRECT else 0,
        "candidate_pages": pages, "outlier_pages": outliers,
        "match": {"coverage": round(coverage, 4), "confidence": conf,
                  "weight": weight, "lines": len(lines), "unresolved_tie": tie,
                  "tie_resolved_by_order": any(l["map"]["by_order"] for l in anchored),
                  "out_of_sequence": False, "repaged_by_chunk_text": repaged},
        "direct_evidence": conf in DIRECT,
    }


def overlap(segments: list[str], b: str, n: int = 12) -> float:
    """Share of the Markdown's n-grams (normalized, within one line or cell)
    that also occur in the other text."""
    ga = {t[i:i + n] for t in map(norm, segments) for i in range(len(t) - n + 1)}
    tb = norm(b)
    gb = {tb[i:i + n] for i in range(len(tb) - n + 1)}
    return round(len(ga & gb) / len(ga), 4) if ga else 0.0


def derived_entries(manifest: dict):
    for role, entry in manifest["current"].items():
        for d in entry.get("derived_texts") or []:
            yield role, entry, d


def build_one(role: str, entry: dict, d: dict, keep_raw: bool = False) -> dict:
    md_path = ROOT / d["file"]
    digest = sha256(md_path)
    if digest != d["file_sha256"]:
        raise SystemExit(f"{d['file']}: sha256 {digest} != manifest {d['file_sha256']}")
    parent = d["page_source_id"]
    pdf_rows = json.loads((ROOT / f"data/manual-corpus/{parent}.json").read_text(encoding="utf-8"))
    domain = pdf_rows[0]["domain"]
    raw = md_path.read_text(encoding="utf-8")
    lines = parse_markdown(raw)
    idx = PageIndex(pdf_rows)
    chunks = build_chunks(lines, idx)
    sections = []
    for c in chunks:
        raw = c.pop("_raw")
        if keep_raw:
            c["raw_text"] = raw
        codes = sorted(set(CODE_RE.findall(c["text"].upper().translate(DASHES))))
        sections.append({
            "source_id": d["id"], "source_file": d["file"], "page_source_id": parent,
            "domain": domain, **c,
            "status_codes_detected": codes,
            "subcodes_detected": [x for x in codes if x.count("-") >= 2],
        })
    conf = Counter(s["match"]["confidence"] for s in sections)
    direct = [s for s in sections if s["direct_evidence"]]
    chars = Counter()
    for s in sections:
        chars[s["match"]["confidence"]] += len(s["text"])
    hwp_text = (ROOT / d["compare_text_file"]).read_text(encoding="utf-8")
    pdf_text = "\n".join(r["text"] for r in pdf_rows)
    body = [seg for line in lines for seg in line["segments"]]
    summary = {
        "chunks": len(sections),
        "table_chunks": sum(s["kind"] == "table" for s in sections),
        "lines": len(lines),
        "by_confidence": {k: conf.get(k, 0) for k in ("high", "medium", "low", "none")},
        "characters_by_confidence": {k: chars.get(k, 0) for k in ("high", "medium", "low", "none")},
        "direct_evidence_chunks": len(direct),
        "pdf_pages_covered_by_direct_chunks": len({p for s in direct for p in s["pages"]}),
        "pdf_pages": len(pdf_rows),
        "ngram12_containment_in_hwp_extraction": overlap(body, hwp_text),
        "ngram12_containment_in_pdf_text": overlap(body, pdf_text),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "source_id": d["id"], "source_file": d["file"], "source_sha256": digest,
        "page_source_id": parent, "page_source_file": entry["file"],
        "domain": domain, "manual_version": entry["version"], "source_date": entry["source_date"],
        "role": role, "builder": "scripts/build_manual_markdown_corpus.py",
        "method": {"shingle": SHINGLE, "rare_pages": RARE, "chunk_chars": CHUNK_CHARS,
                   "thresholds": {"high": HIGH, "medium": MEDIUM, "low": LOW},
                   "direct_evidence_confidence": list(DIRECT)},
        "evidence_rule": ("A chunk is direct evidence only when its text was matched to the approved "
                          "PDF page(s) with high or medium confidence; it then cites that PDF page. "
                          "Other chunks are search candidates (needs_review). Machine-verified, not "
                          "human-reviewed line by line."),
        "summary": summary,
        "sections": sections,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if the committed output is stale")
    args = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    stale = 0
    for role, entry, d in derived_entries(manifest):
        result = build_one(role, entry, d)
        out = ROOT / d["page_map"]
        if args.check:
            current = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
            if current != result:
                print(f"STALE: {d['page_map']}", file=sys.stderr)
                stale += 1
        else:
            write_json(out, result)
        print(d["id"], json.dumps(result["summary"], ensure_ascii=False))
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
