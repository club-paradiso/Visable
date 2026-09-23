#!/usr/bin/env python3
"""Extract one official annex form (one or more consecutive pages) from the
enforcement-rule PDF into a standalone template PDF for the Form Helper.

  python3 scripts/forms/extract_official_form.py --pages 185 --out assets/forms/pdf/F08.pdf
  python3 scripts/forms/extract_official_form.py --pages 119-123 --out assets/forms/pdf/F17.pdf

Prints the sha256, page count and page size that go into the template block of
data/form_schemas.json.
"""
import argparse, hashlib, warnings
warnings.filterwarnings('ignore')
import pymupdf
SRC = 'docs/source-manuals/law/immigration_control_act_enforcement_rule_moj_01106_2026_01_23.pdf'
ap = argparse.ArgumentParser(); ap.add_argument('--src', default=SRC); ap.add_argument('--pages', required=True); ap.add_argument('--out', required=True)
a = ap.parse_args()
lo, _, hi = a.pages.partition('-'); lo = int(lo); hi = int(hi or lo)
src = pymupdf.open(a.src)
out = pymupdf.open()
out.insert_pdf(src, from_page=lo - 1, to_page=hi - 1)
out.set_metadata({'title': '', 'author': '', 'subject': '', 'keywords': '', 'creator': 'Visable form template (extracted from 법무부령 제1106호 PDF)', 'producer': ''})
out.save(a.out, garbage=4, deflate=True)
data = open(a.out, 'rb').read()
doc = pymupdf.open(a.out)
print(f"{a.out}: pages={len(doc)} size={doc[0].rect.width}x{doc[0].rect.height} sha256={hashlib.sha256(data).hexdigest()} bytes={len(data)}")
