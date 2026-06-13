#!/usr/bin/env python3
"""Aggregate per-manual converter benchmarks into review artifacts.

Reads the *.benchmark.json files written by scripts/convert_manual_hwp.py (the
scoring/classification lives there — this script does NOT re-implement it) plus
an optional install_log.json, and writes, under --outdir:

  - conversion_report.json   (machine aggregate: install log + every manual)
  - conversion_report.md     (concatenated per-manual benchmark reports)
  - benchmark_summary.md      (top-level human summary)

Never reads or writes production data. Outputs stay under --outdir (build/...).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_install_log(outdir: Path) -> dict:
    p = outdir / "install_log.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _builtin_chars(bench: dict) -> int:
    for b in bench.get("backends", []):
        if b["name"] == "olefile":
            return b["metrics"]["chars"]
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=Path, required=True)
    args = ap.parse_args()
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    install = _load_install_log(outdir)
    benches = []
    for p in sorted(outdir.glob("**/*.benchmark.json")):
        try:
            benches.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue

    # conversion_report.json (aggregate)
    (outdir / "conversion_report.json").write_text(
        json.dumps({"install": install, "manuals": benches}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    # conversion_report.md (concatenated per-manual reports)
    md_parts = []
    for p in sorted(outdir.glob("**/*.extraction_report.md")):
        md_parts.append(p.read_text(encoding="utf-8"))
    (outdir / "conversion_report.md").write_text("\n\n---\n\n".join(md_parts) + "\n", encoding="utf-8")

    # benchmark_summary.md (top-level)
    any_confident = any(b.get("overall_quality") == "confident" for b in benches)
    any_better_than_builtin = False
    lines = ["# HiKorea manual converter benchmark — summary", ""]

    lines += ["## Installed backends", "", "| backend | status | command |", "| --- | --- | --- |"]
    if install:
        for name, info in install.items():
            lines.append(f"| {name} | {info.get('status','?')} | `{info.get('command','')}` |")
    else:
        lines.append("| (no install_log.json) | — | — |")
    lines.append("")

    lines.append(f"## Manuals tested ({len(benches)})")
    lines.append("")
    for b in benches:
        builtin = _builtin_chars(b)
        lines += [
            f"### {b.get('input')} — overall **{b.get('overall_quality')}**",
            f"- HWP format: {b.get('hwp_format')} · candidate: {b.get('candidate_backend') or 'none'} "
            f"({b.get('candidate_chars',0)} chars) · builtin olefile: {builtin} chars"
            + (f" · vs previous committed txt: {b.get('completeness_pct')}%" if b.get('completeness_pct') is not None else ""),
            "",
            "| backend | installed | chars | korean | headings | codes | quality | better than builtin? |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for be in b.get("backends", []):
            m = be["metrics"]
            better = be["name"] != "olefile" and m["chars"] > builtin and m["chars"] > 0
            if better:
                any_better_than_builtin = True
            lines.append(
                f"| {be['name']} | {'yes' if be['installed'] else 'no'} | {m['chars']} | "
                f"{m['korean_ratio']} | {m['headings']} | {m['codes']} | {be['quality']} | "
                f"{'yes' if better else 'no'} |")
        lines.append("")

    lines += [
        "## Verdict",
        "",
        f"- Any backend confident: **{'yes' if any_confident else 'no'}**",
        f"- Any backend beat the builtin olefile extractor: **{'yes' if any_better_than_builtin else 'no'}**",
        "- Safe to treat any result as verified manual text **without review**: **NO**.",
        "- Human review still required: **YES** — even a `confident` extraction must be"
        " diffed and verified by a maintainer before it is promoted. Distribution/DRM HWP"
        " may need Hancom Office (Windows) or a verified human extraction. This benchmark"
        " never updates production data or baseline hashes and never promotes text.",
    ]
    (outdir / "benchmark_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print((outdir / "benchmark_summary.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
