#!/usr/bin/env python3
"""Re-try the 298 unconfirmed manualRefs against the Markdown-derived text.

Why this exists:
  scripts/audit_manual_ref_editions_2026_09.py confirmed 955 of 1,253
  visa_data.json manualRefs against the 2026.9 PDF text. The other 298
  (audits/manual-ref-edition-2026-09/manual_review_list.md) failed largely
  because the PDF text layer interleaves table cells, so a cited row heading
  such as "단기방문(C-3) 자격 해당자 및 활동범위" never appears contiguously.
  The owner-supplied HWP→Markdown text keeps tables intact. This script looks
  for each ref's cited wording in the page-mapped Markdown chunks and reports
  where it is now found. It is read-only: it never edits visa_data.json or
  any other protected file, and it does not relabel anything.

Matching (same normalization and code-boundary rule as the PDF audit):
  * Domain: a stay ref is looked up only in the stay Markdown, a visa ref only
    in the visa Markdown.
  * Every " — " part of `section` must appear in one chunk, or in a chunk and
    the next one when both are page-mapped to the same or adjacent pages.
  * Only chunks that are direct evidence (page-mapped with high/medium
    confidence) give a 2026.9 page. Hits in other chunks are reported as such.

Outcomes, strictest first:
  matches_cited_page       wording is in a page-mapped chunk (or chunk pair)
                           that touches the 2026.9 page(s) the cited old page
                           crosswalks to and lies within one page of them
  near_cited_page          the chunk(s) holding the wording touch or neighbour
                           that window but also span pages beyond it, so the
                           page is not pinned
  located_elsewhere        wording is on page-mapped 2026.9 page(s), but not
                           on the crosswalked page(s) (or the cited page has no
                           crosswalk); listed with pages, never auto-accepted
  only_in_unmapped_chunks  wording is in the Markdown, but only in chunks that
                           are not direct evidence
  not_found                wording is not in the Markdown either
  out_of_scope             not a stay/visa manual ref (unchanged)

Usage:
  python3 scripts/audit_manual_refs_markdown_2026_09.py   # write the report
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import audit_manual_ref_editions_2026_09 as base  # noqa: E402
import build_manual_markdown_corpus as mdc  # noqa: E402

OUT_DIR = REPO / "audits" / "manual-ref-edition-2026-09"
SOURCE = OUT_DIR / "manual_ref_verification.json"
REPORT_JSON = OUT_DIR / "markdown_retry.json"
REPORT_MD = OUT_DIR / "markdown_retry.md"
UNCONFIRMED = ("old_anchor_missing", "page_unmapped", "new_anchor_missing", "unpaged_source", "out_of_scope")
ORDER = ("matches_cited_page", "near_cited_page", "located_elsewhere",
         "only_in_unmapped_chunks", "not_found", "out_of_scope")


def load_chunks() -> dict[str, list[dict]]:
    manifest = json.loads(mdc.MANIFEST.read_text(encoding="utf-8"))
    out = {}
    for role, entry, d in mdc.derived_entries(manifest):
        domain = "visa" if role == "visa_issuance_manual" else "stay"
        built = mdc.build_one(role, entry, d, keep_raw=True)
        committed = json.loads((REPO / d["page_map"]).read_text(encoding="utf-8"))
        # The audit must describe the committed page map, not a newer rebuild.
        if [s["pages"] for s in committed["sections"]] != [s["pages"] for s in built["sections"]]:
            raise SystemExit(f"{d['page_map']} is stale; run scripts/build_manual_markdown_corpus.py")
        for s in built["sections"]:
            s["_norm"] = base.norm_sep(s["heading"] + "\n" + s["raw_text"])
        out[domain] = built["sections"]
    return out


def windows(chunks: list[dict]):
    """(text, direct, pages) for each chunk and each mapped chunk pair."""
    for k, c in enumerate(chunks):
        yield c["_norm"], c["direct_evidence"], c["pages"]
        if k + 1 < len(chunks):
            n = chunks[k + 1]
            if c["direct_evidence"] and n["direct_evidence"] and abs(n["pages"][0] - c["pages"][-1]) <= 1:
                yield c["_norm"] + base.SEP + n["_norm"], True, sorted(set(c["pages"]) | set(n["pages"]))


def crosswalk_windows() -> dict[str, dict[int, dict]]:
    new_pages = {dom: base.load_pages(REPO / base.NEW[dom]["text"]) for dom in base.NEW}
    files = sorted(set(base.OLD_PAGED) | set(base.ALT_PAGINATION.values()))
    return {f: base.crosswalk(base.load_pages(REPO / f), new_pages[base.OLD_DOMAIN[f]]) for f in files}


def expected_pages(ref: dict, walks) -> tuple[list[int], str]:
    """2026.9 page window the cited old page maps to, if any."""
    if ref["status"] == "new_anchor_missing":
        return list(ref.get("crosswalkPages") or []), "crosswalk recorded by the PDF audit"
    old = base.parse_pages(ref.get("pageRange"))
    src = ref.get("sourceFile")
    if not old or src not in base.OLD_PAGED:
        return [], "cited page has no crosswalk (unpaged source or no page number)"
    for f in filter(None, (src, base.ALT_PAGINATION.get(src))):
        mapped = sorted({q for p in old for q in walks[f].get(p, {}).get("pages") or []})
        if mapped:
            via = "named sourceFile" if f == src else f"alternate pagination {Path(f).name}"
            return list(range(mapped[0], mapped[-1] + 1)), f"old page crosswalked via {via}"
    return [], "cited old page could not be crosswalked by content"


def main() -> int:
    record = json.loads(SOURCE.read_text(encoding="utf-8"))
    refs = [r for r in record["refs"] if r["status"] in UNCONFIRMED]
    chunks = load_chunks()
    walks = crosswalk_windows()
    rows = []
    for ref in refs:
        row = {k: ref.get(k) for k in ("record", "path", "manualType", "manualVersion", "sourceFile",
                                       "pageRange", "section", "status")}
        row["previousStatus"] = row.pop("status")
        mtype = ref.get("manualType")
        if mtype not in chunks:
            row["outcome"] = "out_of_scope"
            rows.append(row)
            continue
        parts = base.section_parts(ref.get("section"))
        direct_hits, other_hits = [], 0
        for text, direct, pages in windows(chunks[mtype]):
            if parts and all(base.find_bounded(text, x) for x in parts):
                if direct:
                    direct_hits.append(pages)
                else:
                    other_hits += 1
        pages_found = sorted({p for ps in direct_hits for p in ps})
        expect, why = expected_pages(ref, walks)
        row["expectedPages2026_9"] = expect
        row["expectedBasis"] = why
        row["markdownPages2026_9"] = pages_found
        lo, hi = (min(expect), max(expect)) if expect else (0, -1)
        # A hit counts for the cited page only when the chunk(s) holding the
        # whole wording sit on that window (one page of slack for a chunk that
        # straddles a page break) and touch it.
        on_cited = [ps for ps in direct_hits if set(ps) & set(expect) and lo - 1 <= ps[0] and ps[-1] <= hi + 1]
        adjacent = [ps for ps in direct_hits if any(abs(p - q) <= 1 for p in ps for q in expect)]
        if on_cited:
            row["outcome"] = "matches_cited_page"
            row["matchedPages"] = sorted({p for ps in on_cited for p in ps})
        elif adjacent:
            row["outcome"] = "near_cited_page"
            row["matchedPages"] = sorted({p for ps in adjacent for p in ps})
        elif pages_found:
            row["outcome"] = "located_elsewhere"
        elif other_hits:
            row["outcome"] = "only_in_unmapped_chunks"
        else:
            row["outcome"] = "not_found"
        rows.append(row)

    by = collections.Counter(r["outcome"] for r in rows)
    cross = collections.Counter(f"{r['previousStatus']}/{r['outcome']}" for r in rows)
    summary = {
        "refs": len(rows),
        "byOutcome": {k: by.get(k, 0) for k in ORDER},
        "byPreviousStatusAndOutcome": dict(sorted(cross.items())),
        "distinctSections": len({(r["manualType"], r["section"]) for r in rows}),
    }
    out = {
        "generatedBy": "scripts/audit_manual_refs_markdown_2026_09.py",
        "input": str(SOURCE.relative_to(REPO)),
        "markdownSources": {dom: chunks[dom][0]["source_file"] for dom in chunks},
        "note": ("Read-only re-check. Nothing in visa_data.json was changed. A match locates the cited "
                 "wording on a 2026.9 PDF page via a page-mapped Markdown chunk; it is not a human "
                 "review and does not by itself relabel a ref."),
        "summary": summary,
        "refs": rows,
    }
    REPORT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render(out), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def render(out: dict) -> str:
    s = out["summary"]
    lines = [
        "# manualRef re-check against the Markdown-derived 2026.9 text",
        "",
        "Generated by `scripts/audit_manual_refs_markdown_2026_09.py`; do not edit by hand.",
        "",
        "Input: the 298 refs that `manual_review_list.md` left unconfirmed "
        "(old_anchor_missing, page_unmapped, new_anchor_missing, unpaged_source, out_of_scope).",
        "Text: the owner-supplied HWP→Markdown conversions, chunked and page-mapped by "
        "`scripts/build_manual_markdown_corpus.py`. Only chunks mapped to a PDF page with "
        "high/medium confidence give a page.",
        "",
        "This is a read-only machine re-check. It changes no data and is not a human review. "
        "A `matches_cited_page` row is a candidate for relabelling, which still needs the owner's decision.",
        "",
        "## Summary",
        "",
        "| outcome | refs |",
        "|---|---:|",
    ]
    lines += [f"| `{k}` | {v} |" for k, v in s["byOutcome"].items()]
    lines += ["", f"Total {s['refs']} refs ({s['distinctSections']} distinct type/section pairs).", "",
              "| previous status / outcome | refs |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in s["byPreviousStatusAndOutcome"].items()]

    def cell(t):
        return str(t if t is not None else "").replace("|", "\\|").replace("\n", " ")

    groups = collections.defaultdict(list)
    for r in out["refs"]:
        groups[r["outcome"]].append(r)
    for outcome in ORDER:
        rs = groups.get(outcome) or []
        if not rs:
            continue
        distinct = collections.OrderedDict()
        for r in rs:
            key = (r["manualType"], r["pageRange"], r["section"], r["previousStatus"])
            d = distinct.setdefault(key, {"records": set(), "n": 0, "r": r})
            d["records"].add(r["record"])
            d["n"] += 1
        lines += ["", f"## {outcome} ({len(rs)} refs, {len(distinct)} distinct)", "",
                  "| type | cited page | previous status | expected 2026.9 | Markdown 2026.9 pages | section | records | n |",
                  "|---|---|---|---|---|---|---|---|"]
        for (mtype, pr, section, prev), d in sorted(distinct.items(), key=lambda kv: tuple(map(str, kv[0]))):
            r = d["r"]
            exp = base.format_pages(r["expectedPages2026_9"]) if r.get("expectedPages2026_9") else "-"
            got = base.format_pages(r["markdownPages2026_9"]) if r.get("markdownPages2026_9") else "-"
            lines.append(f"| {cell(mtype)} | {cell(pr)} | {prev} | {exp} | {got} | {cell(section)} | "
                         f"{cell(', '.join(sorted(d['records'])))} | {d['n']} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
