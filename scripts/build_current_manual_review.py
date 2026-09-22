#!/usr/bin/env python3
"""Compare the supplied PDFs with the PDF editions behind the existing guides.

Both sides use the same pinned PyMuPDF extraction. Reports locate changes; they
do not approve legal rules. The July HWP approval record remains unchanged.
"""
import json
from pathlib import Path
import pymupdf
from diff_manual_versions import load_manual, diff_manuals, build_report
from build_current_manual_corpus import CODE_RE, DASHES, write_json, extract_page_text

ROOT = Path(__file__).resolve().parents[1]
PAIRS = [
    ('visa', '260617_visa_manual_exported.pdf', 'visa_manual_2026_09_01_pdf'),
    ('stay', '260623_stay_manual_exported.pdf', 'stay_manual_2026_09_18_pdf'),
]
for role, filename, source_id in PAIRS:
    pdf = ROOT / 'backend/data/sources/manuals' / filename
    rows = []
    with pymupdf.open(pdf) as doc:
        for number, page in enumerate(doc, 1):
            text, _ = extract_page_text(page)
            rows.append({'page': number, 'text': text, 'status_codes_detected': sorted(set(CODE_RE.findall(text.upper().translate(DASHES))))})
    old_path = ROOT / 'build/manual-review' / f'{role}_previous_pdf_sections.json'
    write_json(old_path, rows)
    new_path = ROOT / 'data/manual-corpus' / f'{source_id}.json'
    old, new = load_manual(old_path, 'previous PDF'), load_manual(new_path, 'September PDF')
    changes = diff_manuals(old, new, 40)
    md, report = build_report(old, new, old_path, new_path, role, changes, 100)
    out = ROOT / 'audits/manual-refresh-260921'
    out.mkdir(parents=True, exist_ok=True)
    (out / f'{role}_pdf_comparison.md').write_text(md, encoding='utf-8')
    write_json(out / f'{role}_pdf_comparison.json', report)
    print(role, report['summary'])
