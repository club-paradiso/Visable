#!/usr/bin/env python3
"""Map each page of an older PDF edition to the page(s) of the next edition.

Pages are matched by content, not by number: rare 10-character shingles (on at
most RARE pages in either edition) vote for the page that carries them, so a
page that only moved because earlier text grew is still found. A page whose text
changed keeps a match as long as most of its distinctive text is still there.

Read-only; writes the JSON report you name. It never edits an edition or any
citation: moving a citation is a separate, reviewed step.

Usage:
  python3 scripts/crosswalk_manual_pdf_pages.py stay_manual_2026_09_18_pdf stay_manual_2026_10_19_pdf \
      --out audits/manual-refresh-20261019/stay_page_crosswalk.json
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHINGLE = 10
RARE = 3
MIN_SHINGLES = 40
MAP_SHARE = 0.25


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for c in "‐‑‒–—―−－─﹣":
        text = text.replace(c, "-")
    return re.sub(r"[^0-9A-Za-z\-가-힣一-鿿]", "", text)


def shingles(text: str) -> set[str]:
    t = norm(text)
    return {t[i:i + SHINGLE] for i in range(max(0, len(t) - SHINGLE + 1))}


def load(source_id: str) -> dict[int, str]:
    rows = json.loads((ROOT / "data/manual-corpus" / f"{source_id}.json").read_text(encoding="utf-8"))
    return {r["page"]: r["text"] for r in rows}


def crosswalk(old: dict[int, str], new: dict[int, str]) -> dict[int, dict]:
    new_sh = {p: shingles(t) for p, t in new.items()}
    old_sh = {p: shingles(t) for p, t in old.items()}
    new_df = collections.Counter(s for sh in new_sh.values() for s in sh)
    old_df = collections.Counter(s for sh in old_sh.values() for s in sh)
    index: dict[str, list[int]] = collections.defaultdict(list)
    for p, sh in new_sh.items():
        for s in sh:
            if new_df[s] <= RARE:
                index[s].append(p)
    out: dict[int, dict] = {}
    for p, sh in old_sh.items():
        own = [s for s in sh if old_df[s] <= RARE and new_df[s] <= RARE]
        if len(own) < MIN_SHINGLES:
            out[p] = {"pages": [], "reason": "too little distinctive text"}
            continue
        counts: collections.Counter = collections.Counter()
        for s in own:
            for q in index.get(s, ()):
                counts[q] += 1
        if not counts:
            out[p] = {"pages": [], "reason": "no page shares its text"}
            continue
        best, best_n = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))
        picked = sorted({best} | {q for q in (best - 1, best + 1) if counts.get(q, 0) / len(own) >= MAP_SHARE})
        rivals = sorted(q for q, n in counts.items()
                        if q not in picked and n / len(own) >= MAP_SHARE and n >= best_n / 2)
        cover = sum(1 for s in own if any(q in picked for q in index.get(s, ()))) / len(own)
        out[p] = {"pages": picked, "cover": round(cover, 3), "rivals": rivals,
                  "same_text": norm(old[p]) == "".join(norm(new[q]) for q in picked)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("old_id")
    ap.add_argument("new_id")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    old, new = load(args.old_id), load(args.new_id)
    cw = crosswalk(old, new)
    shifts = collections.Counter((v["pages"][0] - p) for p, v in cw.items() if v["pages"])
    summary = {"old_pages": len(old), "new_pages": len(new),
               "mapped": sum(1 for v in cw.values() if v["pages"]),
               "unchanged_text": sum(1 for v in cw.values() if v.get("same_text")),
               "page_shift_counts": {str(k): n for k, n in sorted(shifts.items())}}
    payload = {"old": args.old_id, "new": args.new_id, "summary": summary,
               "pages": {str(p): v for p, v in sorted(cw.items())}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
