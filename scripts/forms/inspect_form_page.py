#!/usr/bin/env python3
"""Inspect an official form page to author an overlay map.

Dumps every word with its PDF-point bounding box (origin top-left, PyMuPDF
convention — the same convention data/form_schemas.json uses for x / y) and
renders a debug PNG with a 25-pt grid so field cells can be read off the image.

  python3 scripts/forms/inspect_form_page.py assets/forms/pdf/F08.pdf --page 1 --out /tmp/f08_debug.png
"""
import argparse, json, warnings
warnings.filterwarnings('ignore')
import pymupdf

ap = argparse.ArgumentParser()
ap.add_argument('pdf'); ap.add_argument('--page', type=int, default=1); ap.add_argument('--out', default=None)
ap.add_argument('--json', default=None); ap.add_argument('--dpi', type=int, default=110); ap.add_argument('--grid', type=int, default=25)
a = ap.parse_args()
doc = pymupdf.open(a.pdf); page = doc[a.page - 1]
words = [{'x0': round(w[0], 1), 'y0': round(w[1], 1), 'x1': round(w[2], 1), 'y1': round(w[3], 1), 'text': w[4]} for w in page.get_text('words')]
lines = []
for d in page.get_drawings():
    r = d.get('rect')
    if r is None: continue
    if r.width < 2 or r.height < 2:  # thin = rule line
        lines.append({'x0': round(r.x0, 1), 'y0': round(r.y0, 1), 'x1': round(r.x1, 1), 'y1': round(r.y1, 1), 'kind': 'h' if r.height < 2 else 'v'})
print(f'page {a.page}: {page.rect.width}x{page.rect.height} pt, {len(words)} words, {len(lines)} rule lines')
if a.json:
    json.dump({'width': page.rect.width, 'height': page.rect.height, 'words': words, 'lines': lines}, open(a.json, 'w'), ensure_ascii=False, indent=0)
else:
    for w in words: print(f"{w['x0']:6.1f} {w['y0']:6.1f} {w['x1']:6.1f} {w['y1']:6.1f}  {w['text']}")
if a.out:
    shape = page.new_shape()
    W, H = page.rect.width, page.rect.height
    for x in range(0, int(W) + 1, a.grid):
        shape.draw_line((x, 0), (x, H)); shape.finish(color=(1, 0.6, 0.6) if x % 100 else (1, 0, 0), width=0.3 if x % 100 else 0.6)
        if x % 50 == 0: shape.insert_text((x + 1, 8), str(x), fontsize=5, color=(1, 0, 0))
    for y in range(0, int(H) + 1, a.grid):
        shape.draw_line((0, y), (W, y)); shape.finish(color=(0.6, 0.6, 1) if y % 100 else (0, 0, 1), width=0.3 if y % 100 else 0.6)
        if y % 50 == 0: shape.insert_text((1, y - 1), str(y), fontsize=5, color=(0, 0, 1))
    shape.commit()
    page.get_pixmap(dpi=a.dpi).save(a.out)
    print('debug image:', a.out)
