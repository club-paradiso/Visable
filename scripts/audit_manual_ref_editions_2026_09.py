#!/usr/bin/env python3
"""Check every visa_data.json manualRef against the 2026.9 manual text.

Why this exists:
  The owner made the 2026-09-18 stay manual and the 2026-09-01 visa manual the
  reference editions (audits/manual-edition-2026-09-promotion/README.md §4.3),
  but visa_data.json is a protected file and its manualRefs still cite the
  2026.6/2026.7 editions. A ref may only be relabelled once it is shown that
  the wording it cites is still in the 2026.9 text, and on which page. This
  script settles that deterministically; it never edits visa_data.json unless
  --apply is passed, and --apply touches only refs it verified.

What a ref cites:
  manualRefs carry no excerpt. The cited wording is the `section` string
  (sometimes several headings joined by " — "), anchored by `pageRange`.
  Many sections are bare codes such as "D-4-7" that occur on dozens of pages,
  so "the wording is somewhere in the 2026.9 manual" proves nothing. A ref is
  VERIFIED only when all of these hold:

  1. Domain: stay refs are checked only against the stay manual, visa refs
     only against the visa manual (CLAUDE.md "Procedure scope").
  2. Old anchor: every part of the section appears verbatim on the cited
     pages of the old page-split PDF text the ref names in sourceFile.
  3. Page crosswalk: each cited old page is matched to 2026.9 pages by shared
     text (character shingles), not by wording search, so the new page range
     comes from page content, independent of the section string.
  4. New anchor: every part of the section appears verbatim on the
     crosswalked 2026.9 pages.

  Verbatim means after normalization: NFKC, every dash folded to "-", and
  everything except Hangul, CJK, ASCII letters/digits and "-" removed. Codes
  are boundary-checked so "F-5-1" does not match inside "F-5-13".

  Refs whose old source is not page-split (the 2026.7 HWP extractions), whose
  pageRange is not a page number, or whose manualType is not stay/visa are
  reported and left unchanged.

Usage:
  scripts/audit_manual_ref_editions_2026_09.py            # print the summary (read-only)
  scripts/audit_manual_ref_editions_2026_09.py --apply    # write the report, relabel VERIFIED refs
                                                          # (owner-approved 2026-10-19; done once)
  scripts/audit_manual_ref_editions_2026_09.py --check    # every 2026.9 ref is on its cited page
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VISA_DATA = REPO / "visa_data.json"
OUT_DIR = REPO / "audits" / "manual-ref-edition-2026-09"
REPORT_JSON = OUT_DIR / "manual_ref_verification.json"
REVIEW_MD = OUT_DIR / "manual_review_list.md"

NEW = {
    "stay": {
        "text": "docs/source-manuals/2026-09/extracted/stay_manual_2026_09_18_pdf.txt",
        "pdf": "docs/source-manuals/2026-09/stay_manual_260918.pdf",
        "sourceId": "stay_manual_2026_09_18_pdf",
        "sourceDate": "2026-09-18",
        "confidence": "section_anchor_verified_260918_pdf",
    },
    "visa": {
        "text": "docs/source-manuals/2026-09/extracted/visa_manual_2026_09_01_pdf.txt",
        "pdf": "docs/source-manuals/2026-09/visa_manual_260901.pdf",
        "sourceId": "visa_manual_2026_09_01_pdf",
        "sourceDate": "2026-09-01",
        "confidence": "section_anchor_verified_260901_pdf",
    },
}
NEW_VERSION = "2026.9"
#: Statuses --apply relabels.
APPLY_STATUSES = ("verified", "verified_alt_pagination")

#: Old page-split sources a ref can be anchored in, by sourceFile.
OLD_PAGED = {
    "backend/data/sources/manuals/260623_stay_manual_readable.txt": "stay",
    "backend/data/sources/manuals/260617_visa_manual_readable.txt": "visa",
}
#: Many stay refs name the 260623 export but carry page numbers from the
#: 260617 export of the same edition (778 vs 780 pages, so later chapters sit
#: two pages apart). When the wording is not on the named page, the same page
#: number is tried in this file; such refs are reported separately.
ALT_PAGINATION = {
    "backend/data/sources/manuals/260623_stay_manual_readable.txt":
        "backend/data/sources/manuals/260617_stay_manual_readable.txt",
}
OLD_DOMAIN = {**OLD_PAGED, **{alt: OLD_PAGED[src] for src, alt in ALT_PAGINATION.items()}}

PAGE_MARK = re.compile(r"^=====.*?PDF page (\d+)(?: of \d+)? =====\s*$", re.M)
DASHES = "‐‑‒–—―−－─﹣"
SECTION_JOINERS = re.compile(r"\s+[—–]\s+")
SHINGLE = 10
#: A 2026.9 page belongs to an old page's crosswalk when it holds at least this
#: share of the old page's shingles ...
MAP_SHARE = 0.25
#: ... and the mapped pages together must cover this share of the old page.
MAP_COVER = 0.6
#: Pages with fewer distinctive shingles than this (covers, blank pages) are not mapped.
MIN_SHINGLES = 40
#: A shingle on more pages than this (in either edition) is boilerplate.
RARE = 3
#: How far to look for an unambiguously mapped neighbour page.
NEIGHBOUR = 3


#: Stands in for whitespace and punctuation that normalization drops, so a code
#: at the end of a line ("C-4-5)" + "1회") is not read as "C-4-51".
SEP = "\x00"
SEP_RUN = re.compile(r"[^0-9A-Za-z\-\uac00-\ud7a3\u4e00-\u9fff]+")


def norm_sep(text: str) -> str:
    """Normalized text with each dropped run of characters marked by SEP."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate({ord(c): "-" for c in DASHES})
    return SEP_RUN.sub(SEP, text).strip(SEP)


def norm(text: str) -> str:
    return norm_sep(text).replace(SEP, "")


def _ascii_alnum(c: str) -> bool:
    return c.isascii() and c.isalnum()


_PATTERNS: dict[str, re.Pattern] = {}


#: The boundary check applies only where the wording starts or ends with a
#: status code; prose cut mid-number ("‘22. 12.") is matched as is.
CODE_HEAD = re.compile(r"^[A-Z]{1,2}-[0-9A-Z]")
CODE_TAIL = re.compile(r"[A-Z]{1,2}-[0-9A-Z]+(?:-[0-9A-Z]+)*$")


def find_bounded(hay: str, needle: str) -> bool:
    """Find a normalized needle in SEP-marked text, ignoring SEPs inside the
    match but refusing to split a status code ("F-5-1" inside "F-5-13")."""
    pat = _PATTERNS.get(needle)
    if pat is None:
        pat = _PATTERNS[needle] = re.compile(
            "(?=(" + (re.escape(SEP) + "?").join(re.escape(c) for c in needle) + "))")
    check_head, check_tail = bool(CODE_HEAD.match(needle)), bool(CODE_TAIL.search(needle))
    for m in pat.finditer(hay):
        i, j = m.start(1), m.end(1)
        before, after, after2 = hay[i - 1: i], hay[j: j + 1], hay[j + 1: j + 2]
        if check_head and before and before != SEP:
            # "1D-2" (a list number glued to a code) is fine; "ED-2" or "-D-2" is not.
            if before == "-" or (before.isascii() and before.isalpha()):
                continue
        if check_tail and after and after != SEP:
            if _ascii_alnum(after) or (after == "-" and _ascii_alnum(after2)):
                continue
        return True
    return False


def load_pages(path: Path) -> dict[int, str]:
    raw = path.read_text(encoding="utf-8")
    marks = list(PAGE_MARK.finditer(raw))
    pages: dict[int, str] = {}
    for k, m in enumerate(marks):
        end = marks[k + 1].start() if k + 1 < len(marks) else len(raw)
        pages[int(m.group(1))] = raw[m.end():end]
    return pages


def shingles(text: str) -> set[str]:
    t = norm(text)
    return {t[i:i + SHINGLE] for i in range(max(0, len(t) - SHINGLE + 1))}


def _clusters(pages: list[int]) -> list[list[int]]:
    """Group sorted page numbers into runs of adjacent pages."""
    runs: list[list[int]] = []
    for q in sorted(pages):
        if runs and q - runs[-1][-1] == 1:
            runs[-1].append(q)
        else:
            runs.append([q])
    return runs


def crosswalk(old: dict[int, str], new: dict[int, str]) -> dict[int, dict]:
    """Map each old page to the 2026.9 page(s) that carry its text.

    Only shingles that are rare in both editions (on at most RARE pages) are
    used, so running headers, tables of contents and repeated notices cannot
    pull a page towards an unrelated one. Candidate pages are those holding at
    least MAP_SHARE of the old page's distinctive text, plus the best page;
    adjacent candidates form one cluster (a page that reflowed over a break).

    The visa manual repeats some pages verbatim in two chapters, in both
    editions, so a page can have two clusters. Such a page is resolved by its
    neighbours: the cluster that keeps the page offset of the nearest
    unambiguously mapped old page (within NEIGHBOUR pages) wins; if none or
    both do, the page stays unmapped.
    """
    new_sh = {p: shingles(t) for p, t in new.items()}
    old_sh = {p: shingles(t) for p, t in old.items()}
    new_df: collections.Counter = collections.Counter(s for sh in new_sh.values() for s in sh)
    old_df: collections.Counter = collections.Counter(s for sh in old_sh.values() for s in sh)
    index: dict[str, list[int]] = collections.defaultdict(list)
    for p, sh in new_sh.items():
        for s in sh:
            if new_df[s] <= RARE:
                index[s].append(p)

    def cover(own: list[str], picked: list[int]) -> float:
        return sum(1 for s in own if any(q in picked for q in index.get(s, ()))) / len(own)

    out: dict[int, dict] = {}
    pending: dict[int, tuple[list[str], list[list[int]]]] = {}
    for p, sh in old_sh.items():
        own = [s for s in sh if old_df[s] <= RARE and new_df[s] <= RARE]
        if len(own) < MIN_SHINGLES:
            out[p] = {"pages": [], "cover": 0.0, "reason": "page has too little distinctive text to match"}
            continue
        counts: collections.Counter = collections.Counter()
        for s in own:
            for q in index.get(s, ()):
                counts[q] += 1
        if not counts:
            out[p] = {"pages": [], "cover": 0.0, "reason": "no 2026.9 page shares its text"}
            continue
        best, best_n = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))
        # A neighbour of the best page joins on MAP_SHARE alone (reflow); a
        # distant page must also rival the best page to count as a duplicate.
        cands = {best} | {q for q, n in counts.items()
                          if n / len(own) >= MAP_SHARE and (abs(q - best) == 1 or n >= best_n / 2)}
        clusters = _clusters(list(cands))
        if len(clusters) > 1:
            pending[p] = (own, clusters)
            continue
        c = cover(own, clusters[0])
        out[p] = {"pages": clusters[0] if c >= MAP_COVER else [], "cover": round(c, 3),
                  "reason": "" if c >= MAP_COVER else
                  f"only {c:.0%} of its distinctive text is on 2026.9 p. {clusters[0]}"}

    for p, (own, clusters) in sorted(pending.items()):
        offsets = set()
        for step in range(1, NEIGHBOUR + 1):
            for n in (p - step, p + step):
                if out.get(n, {}).get("pages"):
                    offsets.add(out[n]["pages"][0] - n)
            if offsets:
                break
        fits = [c for c in clusters if any(abs(c[0] - (p + d)) <= 1 for d in offsets)]
        if len(fits) != 1:
            out[p] = {"pages": [], "cover": 0.0,
                      "reason": f"text matches non-adjacent 2026.9 pages {clusters} and neighbours do not decide"}
            continue
        c = cover(own, fits[0])
        out[p] = {"pages": fits[0] if c >= MAP_COVER else [], "cover": round(c, 3),
                  "resolvedByNeighbours": True,
                  "reason": "" if c >= MAP_COVER else
                  f"only {c:.0%} of its distinctive text is on 2026.9 p. {fits[0]}"}
    return out


def parse_pages(page_range: str | None) -> list[int] | None:
    if not page_range:
        return None
    m = re.fullmatch(r"pp?\.\s*([\d,\s\-–]+)", page_range.strip())
    if not m:
        return None
    pages: list[int] = []
    for part in m.group(1).split(","):
        part = part.strip()
        if not part:
            continue
        ab = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", part)
        if ab:
            a, b = int(ab.group(1)), int(ab.group(2))
            if b < a:
                return None
            pages.extend(range(a, b + 1))
        elif part.isdigit():
            pages.append(int(part))
        else:
            return None
    return pages or None


def format_pages(pages: list[int]) -> str:
    pages = sorted(set(pages))
    runs, start, prev = [], pages[0], pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
            continue
        runs.append((start, prev))
        start = prev = p
    runs.append((start, prev))
    if len(runs) == 1 and runs[0][0] == runs[0][1]:
        return f"p. {runs[0][0]}"
    return "pp. " + ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in runs)


def section_parts(section: str | None) -> list[str]:
    if not section:
        return []
    return [p for p in (norm(x) for x in SECTION_JOINERS.split(section)) if p]


def iter_refs(data):
    """Yield (record code, json path, ref dict) for every manualRef."""
    def walk(node, path):
        if isinstance(node, dict):
            refs = node.get("manualRefs")
            if isinstance(refs, list):
                for i, ref in enumerate(refs):
                    if isinstance(ref, dict):
                        yield path + ["manualRefs", i], ref
            for k, v in node.items():
                yield from walk(v, path + [k])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, path + [i])
    for r, record in enumerate(data):
        for path, ref in walk(record, []):
            yield record.get("code"), [r] + path, ref


def procedure_domain(path: list) -> str | None:
    """Which manual a procedure's refs must come from, by procedure key."""
    if "procedures" not in path:
        return None
    key = path[path.index("procedures") + 1]
    return "visa" if key == "visaIssuance" else "stay"


_ANCHOR_PAGES: dict[str, dict[int, str]] = {}


def anchored_2026_09(ref: dict) -> bool:
    """True when a ref cites 2026.9 in its own domain's text and its section
    wording is verbatim on the cited 2026.9 page(s). The populate scripts and
    tests use this to accept the 2026-10-19 relabel without loosening their
    2026.6 pins for refs that were not relabelled."""
    mtype = ref.get("manualType") or "stay"
    new = NEW.get(mtype)
    if not new or ref.get("manualVersion") != NEW_VERSION or ref.get("sourceFile") != new["text"]:
        return False
    if "sourceId" in ref and ref["sourceId"] != new["sourceId"]:
        return False
    if "sourceDate" in ref and ref["sourceDate"] != new["sourceDate"]:
        return False
    if mtype not in _ANCHOR_PAGES:
        _ANCHOR_PAGES[mtype] = {p: norm_sep(t) for p, t in load_pages(REPO / new["text"]).items()}
    pages = _ANCHOR_PAGES[mtype]
    cited = parse_pages(ref.get("pageRange"))
    parts = section_parts(ref.get("section"))
    if not cited or not parts:
        return False
    text = SEP.join(pages.get(p, "") for p in cited)
    return all(find_bounded(text, x) for x in parts)


def run() -> dict:
    data = json.loads(VISA_DATA.read_text(encoding="utf-8"))
    old_files = sorted(set(OLD_PAGED) | set(ALT_PAGINATION.values()))
    old_pages = {f: load_pages(REPO / f) for f in old_files}
    new_pages = {dom: load_pages(REPO / NEW[dom]["text"]) for dom in NEW}
    new_norm = {dom: {p: norm_sep(t) for p, t in pages.items()} for dom, pages in new_pages.items()}
    old_norm = {f: {p: norm_sep(t) for p, t in pages.items()} for f, pages in old_pages.items()}
    walks = {f: crosswalk(old_pages[f], new_pages[OLD_DOMAIN[f]]) for f in old_files}

    def on_pages(texts: dict[int, str], pages: list[int], parts: list[str]) -> list[str]:
        """The parts that are NOT on the given pages."""
        text = SEP.join(texts.get(p, "") for p in pages)
        return [x for x in parts if not find_bounded(text, x)]

    results = []
    for code, path, ref in iter_refs(data):
        mtype = ref.get("manualType")
        src = ref.get("sourceFile")
        row = {
            "record": code,
            "path": "/".join(str(p) for p in path),
            "manualType": mtype,
            "manualVersion": ref.get("manualVersion"),
            "sourceFile": src,
            "pageRange": ref.get("pageRange"),
            "section": ref.get("section"),
            "needsManualReview": ref.get("needsManualReview"),
        }

        def done(status, reason, **extra):
            row.update(status=status, reason=reason, **extra)
            results.append(row)

        if mtype not in NEW:
            done("out_of_scope", f"manualType {mtype!r} is not the stay or visa manual")
            continue
        expected = procedure_domain(path)
        if expected and expected != mtype:
            done("domain_mismatch", f"{mtype} ref under a {expected} procedure; left for manual review")
            continue
        parts = section_parts(ref.get("section"))
        texts = new_norm[mtype]
        if ref.get("manualVersion") == NEW_VERSION:
            if anchored_2026_09(ref):
                done("current_verified", "cites 2026.9 and the wording is on the cited 2026.9 page(s)")
            else:
                done("current_unanchored", "cites 2026.9 but the wording is not on the cited 2026.9 page(s)")
            continue
        hits = sorted(p for p, t in texts.items() if parts and not on_pages(texts, [p], parts))
        found = {"wordingPageCount": len(hits), "wordingPages2026_9": hits[:12]}
        if src not in OLD_PAGED:
            done("unpaged_source", "old source is not page-split, so the cited page cannot be crosswalked", **found)
            continue
        if OLD_DOMAIN[src] != mtype:
            done("domain_mismatch", f"{mtype} ref names a {OLD_DOMAIN[src]} source file")
            continue
        if not parts:
            done("no_wording", "ref has no section wording to check")
            continue
        old_list = parse_pages(ref.get("pageRange"))
        if not old_list:
            done("unparsed_page", "pageRange is not a page number")
            continue

        # Which old pagination does the cited page number belong to?
        anchor = src
        missing_old = on_pages(old_norm[src], old_list, parts)
        alt = ALT_PAGINATION.get(src)
        if missing_old and alt and not on_pages(old_norm[alt], old_list, parts):
            anchor, missing_old = alt, []
        if missing_old:
            elsewhere = {f: [p for p in old_norm[f] if not on_pages(old_norm[f], [p], parts)][:12]
                         for f in filter(None, (src, alt))}
            done("old_anchor_missing",
                 "cited wording is not on the cited old page(s), so what was cited cannot be confirmed",
                 missingParts=missing_old, oldWordingPages=elsewhere, **found)
            continue
        row["oldAnchorFile"] = anchor
        cw = walks[anchor]

        def mapped(page: int) -> list[int]:
            return cw.get(page, {}).get("pages") or []

        inferred: list[str] = []
        contiguous = old_list == list(range(old_list[0], old_list[-1] + 1))
        if contiguous and len(old_list) > 3:
            # A chapter range. Its first or last page is often a cover or a
            # near-blank page with too little text to match; then the bound is
            # taken from the page just outside the range (the chapter ends
            # where the next page's text begins).
            first, last = old_list[0], old_list[-1]
            lo = min(mapped(first)) if mapped(first) else None
            hi = max(mapped(last)) if mapped(last) else None
            if lo is None and mapped(first - 1):
                lo = max(mapped(first - 1)) + 1
                inferred.append(f"start from old p. {first - 1}")
            if hi is None and mapped(last + 1):
                hi = min(mapped(last + 1)) - 1
                inferred.append(f"end from old p. {last + 1}")
            unmapped = {p: cw.get(p, {}).get("reason", "page not in old source")
                        for p, b in ((first, lo), (last, hi)) if b is None}
            if not unmapped and (hi < lo or abs((hi - lo) - (last - first)) > max(5, (last - first) * 0.3)):
                unmapped = {first: f"crosswalked range p. {lo}-{hi} does not fit the old range"}
            window = [] if unmapped else list(range(lo, hi + 1))
        else:
            unmapped = {p: cw.get(p, {}).get("reason", "page not in old source")
                        for p in old_list if not mapped(p)}
            if contiguous:
                window = [] if unmapped else list(range(min(mapped(old_list[0])), max(mapped(old_list[-1])) + 1))
            else:
                window = sorted({q for p in old_list for q in mapped(p)})
        if unmapped or not window:
            done("page_unmapped", "cited page could not be matched to a 2026.9 page by content",
                 unmappedPages={str(k): v for k, v in sorted(unmapped.items())}, **found)
            continue
        if on_pages(texts, window, parts):
            near = [p for p in hits if window[0] - 3 <= p <= window[-1] + 3]
            done("new_anchor_missing", "cited wording is not on the crosswalked 2026.9 page(s)",
                 crosswalkPages=window, nearbyWordingPages=near, **found)
            continue
        if len(old_list) == 1:
            # A single-page cite stays a single page (or the page pair the old
            # page reflowed over), narrowed to the page(s) holding the wording.
            new_list = [p for p in window if not on_pages(texts, [p], parts)] or window
        else:
            new_list = window
        status = "verified" if anchor == src else "verified_alt_pagination"
        if inferred:
            row["boundInferred"] = inferred
        reason = ("wording found on the cited old page(s) and on the crosswalked 2026.9 page(s)"
                  if anchor == src else
                  f"page number follows {anchor} rather than the named sourceFile; "
                  "wording found there and on the crosswalked 2026.9 page(s)")
        done(status, reason, newPageRange=format_pages(new_list), crosswalkPages=window,
             pageShift=new_list[0] - old_list[0])
    return {"data": data, "results": results, "walks": walks}


def summarize(results: list[dict]) -> dict:
    by_status = collections.Counter(r["status"] for r in results)
    by_status_type = collections.Counter((r["status"], r["manualType"]) for r in results)
    by_version = collections.Counter((r["manualVersion"], r["status"]) for r in results)
    return {
        "total": len(results),
        "byStatus": dict(sorted(by_status.items())),
        "byStatusAndType": {f"{s}/{t}": n for (s, t), n in sorted(by_status_type.items(), key=str)},
        "byVersionAndStatus": {f"{v}/{s}": n for (v, s), n in sorted(by_version.items(), key=str)},
    }


def write_report(out: dict) -> str:
    results = out["results"]
    walks = out["walks"]
    payload = {
        "generatedBy": "scripts/audit_manual_ref_editions_2026_09.py",
        "newSources": NEW,
        "method": {
            "normalization": "NFKC; dashes folded to '-'; keep Hangul, CJK, ASCII alnum and '-'; ASCII codes boundary-checked",
            "shingle": SHINGLE, "mapShare": MAP_SHARE, "mapCover": MAP_COVER, "minShingles": MIN_SHINGLES,
            "rare": RARE, "neighbour": NEIGHBOUR,
        },
        "summary": summarize(results),
        "crosswalkCoverage": {
            f: {"oldPages": len(w), "mapped": sum(1 for v in w.values() if v["pages"])}
            for f, w in walks.items()
        },
        "refs": results,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def review_list(results: list[dict]) -> str:
    """Markdown list of every distinct ref, grouped by outcome."""
    order = ["verified", "verified_alt_pagination", "old_anchor_missing", "page_unmapped",
             "new_anchor_missing", "unpaged_source", "domain_mismatch", "out_of_scope",
             "current_verified", "current_unanchored"]
    groups: dict[str, dict] = collections.defaultdict(dict)
    for r in results:
        key = (r["manualType"], r["sourceFile"], r["pageRange"], r["section"])
        entry = groups[r["status"]].setdefault(key, {"row": r, "records": [], "count": 0})
        entry["count"] += 1
        if r["record"] not in entry["records"]:
            entry["records"].append(r["record"])

    def cell(text) -> str:
        return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")

    lines = ["# manualRef 2026.9 verification: every distinct ref", "",
             "Generated by `scripts/audit_manual_ref_editions_2026_09.py`; do not edit by hand.",
             "Counts are ref instances in visa_data.json (subCodes and subcodes mirror each other).", ""]
    for status in order + sorted(set(groups) - set(order)):
        if status not in groups:
            continue
        entries = groups[status]
        lines += [f"## {status} ({sum(e['count'] for e in entries.values())} refs, {len(entries)} distinct)", ""]
        lines += ["| type | cited page | 2026.9 page | section | records | n | detail |",
                  "|---|---|---|---|---|---|---|"]
        for (mtype, _src, page, section), e in sorted(entries.items(), key=lambda kv: str(kv[0])):
            r = e["row"]
            detail = (r.get("boundInferred") or r.get("missingParts") or r.get("unmappedPages")
                      or r.get("crosswalkPages") or r.get("reason"))
            if status == "verified_alt_pagination":
                detail = "page number from 260617 export"
            if status in ("old_anchor_missing", "new_anchor_missing", "unpaged_source", "page_unmapped"):
                detail = f"{detail}; wording on {r.get('wordingPageCount', 0)} 2026.9 page(s)"
            lines.append("| " + " | ".join(cell(x) for x in (
                mtype, page, r.get("newPageRange", ""), section,
                ", ".join(map(str, e["records"][:6])) + (" …" if len(e["records"]) > 6 else ""),
                e["count"], detail)) + " |")
        lines.append("")
    return "\n".join(lines)


def apply(out: dict) -> int:
    data = out["data"]
    by_path = {r["path"]: r for r in out["results"] if r["status"] in APPLY_STATUSES}
    changed = 0
    for _code, path, ref in iter_refs(data):
        row = by_path.get("/".join(str(p) for p in path))
        if not row:
            continue
        new = NEW[ref["manualType"]]
        ref["manualVersion"] = NEW_VERSION
        ref["sourceDate"] = new["sourceDate"]
        ref["sourceFile"] = new["text"]
        if "sourcePdf" in ref:
            ref["sourcePdf"] = new["pdf"]
        if "sourceId" in ref:
            ref["sourceId"] = new["sourceId"]
        if "confidence" in ref:
            ref["confidence"] = new["confidence"]
        ref["pageRange"] = row["newPageRange"]
        changed += 1
    VISA_DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if a ref labelled 2026.9 is not anchored on its cited 2026.9 page")
    ap.add_argument("--apply", action="store_true",
                    help="write the audit report, then relabel VERIFIED refs in visa_data.json")
    args = ap.parse_args()
    out = run()
    results = out["results"]
    if args.check:
        bad = [r for r in results if r["status"] == "current_unanchored"]
        for r in bad:
            print(f"UNANCHORED: {r['path']} {r['pageRange']} {r['section']}", file=sys.stderr)
        if bad:
            return 1
        n = sum(1 for r in results if r["status"] == "current_verified")
        print(f"OK: all {n} refs labelled {NEW_VERSION} are anchored on their cited pages")
        return 0
    if args.apply:
        # The report is the record of the verification the relabel rests on,
        # so it is written from the state before the relabel.
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(write_report(out), encoding="utf-8")
        REVIEW_MD.write_text(review_list(results), encoding="utf-8")
        print(f"relabelled {apply(out)} verified refs in visa_data.json")
        return 0
    print(json.dumps(summarize(results), ensure_ascii=False, indent=2))
    print(json.dumps({f: {"oldPages": len(w), "mapped": sum(1 for v in w.values() if v["pages"])}
                      for f, w in out["walks"].items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
