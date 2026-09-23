#!/usr/bin/env python3
"""Print the centre of every printed "[ ]" / "( )" checkbox and the horizontal / vertical
rule lines of an official form page, in PDF points with a top-left origin.

Usage: python3 scripts/forms/bracket_centers.py assets/forms/pdf/F08.pdf [page-index]

The overlay coordinates in data/form_schemas.json are authored from this output
(check = tick centred at (cx, cy)); keep it next to inspect_form_page.py.
"""
import sys
import fitz  # PyMuPDF

path = sys.argv[1]
page_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
doc = fitz.open(path)
page = doc[page_index]
words = page.get_text('words')  # x0, y0, x1, y1, text, block, line, word
opens = [w for w in words if w[4].startswith('[') or w[4] == '(']
closes = [w for w in words if w[4].startswith(']') or w[4].startswith(')')]
pairs = []
for o in opens:
    cands = [c for c in closes if abs(c[1] - o[1]) < 4 and 0 < c[0] - o[0] < 40]
    if not cands:
        continue
    c = min(cands, key=lambda w: w[0] - o[0])
    # glyph boxes: the '[' word may include following text ("[√]" etc.) — use the bracket glyph width (~4.5pt)
    x_open = o[0]
    x_close = c[0] + 4.4 if len(c[4]) > 1 else c[2]
    cx = round((x_open + x_close) / 2, 1)
    cy = round((o[1] + o[3]) / 2, 1)
    label = ' '.join(w[4] for w in words if abs(w[1] - o[1]) < 4 and c[0] <= w[0] < c[0] + 60)[:28]
    pairs.append((cy, cx, o[4], c[4], label))
for cy, cx, ot, ct, label in sorted(pairs):
    print(f"check cx={cx:6.1f} cy={cy:6.1f}  {ot}{ct}  {label}")
drawings = page.get_drawings()
hs, vs = set(), set()
for d in drawings:
    for item in d['items']:
        if item[0] == 'l':
            p1, p2 = item[1], item[2]
            if abs(p1.y - p2.y) < 0.6 and abs(p1.x - p2.x) > 3:
                hs.add((round(p1.y, 1), round(min(p1.x, p2.x), 1), round(max(p1.x, p2.x), 1)))
            elif abs(p1.x - p2.x) < 0.6 and abs(p1.y - p2.y) > 3:
                vs.add((round(p1.x, 1), round(min(p1.y, p2.y), 1), round(max(p1.y, p2.y), 1)))
        elif item[0] == 're':
            r = item[1]
            if r.height < 1.2 and r.width > 3:
                hs.add((round(r.y0, 1), round(r.x0, 1), round(r.x1, 1)))
            elif r.width < 1.2 and r.height > 3:
                vs.add((round(r.x0, 1), round(r.y0, 1), round(r.y1, 1)))
print('H lines (y: x0-x1):')
for y, x0, x1 in sorted(hs):
    print(f"  y={y:6.1f}  x {x0:6.1f}-{x1:6.1f}")
print('V lines (x: y0-y1):')
for x, y0, y1 in sorted(vs):
    print(f"  x={x:6.1f}  y {y0:6.1f}-{y1:6.1f}")
