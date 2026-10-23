#!/usr/bin/env python3
"""Compare the current PDF edition with the PDF edition it replaced.

Both sides are the committed page corpora (data/manual-corpus/<source_id>.json),
extracted with the same pinned PyMuPDF routine. Reports locate changed pages;
they do not approve legal rules.

2026-10-23: the pairs are now 2026.9 -> 2026.10 (the 2026-10-19 editions). The
earlier 2026.6 -> 2026.9 comparison is kept in audits/manual-refresh-260921/.
"""
from pathlib import Path

from diff_manual_versions import load_manual, diff_manuals, build_report
from build_current_manual_corpus import write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'audits/manual-refresh-20261019'
PAIRS = [
    ('visa', 'visa_manual_2026_09_01_pdf', 'visa_manual_2026_10_19_pdf'),
    ('stay', 'stay_manual_2026_09_18_pdf', 'stay_manual_2026_10_19_pdf'),
]
for role, old_id, new_id in PAIRS:
    old_path = ROOT / 'data/manual-corpus' / f'{old_id}.json'
    new_path = ROOT / 'data/manual-corpus' / f'{new_id}.json'
    old, new = load_manual(old_path, 'September PDF'), load_manual(new_path, 'October PDF')
    changes = diff_manuals(old, new, 40)
    md, report = build_report(old, new, old_path, new_path, role, changes, 100)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{role}_pdf_comparison.md').write_text(md, encoding='utf-8')
    write_json(OUT / f'{role}_pdf_comparison.json', report)
    print(role, report['summary'])
