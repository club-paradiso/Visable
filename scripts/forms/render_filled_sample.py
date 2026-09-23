#!/usr/bin/env python3
"""Render a form template with overlay-level sample values (PyMuPDF) for field-map QA.

  python3 scripts/forms/render_filled_sample.py F08 [out_dir]

Draws every overlay entry of data/form_schemas.json with the values in
tests/fixtures/form_overlay_samples.json using the same placement rules as the
browser engine (assets/js/form-engine.js): baseline y, shrink-to-fit down to
6.5 pt, wrapping when `lines` > 1, digit cells, centred text, white-out boxes,
vector ticks. Writes <form>-<page>.png (scale 1.5) plus <form>-filled.pdf and
prints the fit result for each key so overflow is visible during authoring.
"""
import json, os, sys, warnings
warnings.filterwarnings('ignore')
import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT = os.path.join(ROOT, 'assets/forms/fonts/NanumGothic-Regular.ttf')
MIN_SIZE = 6.5
FONTOBJ = pymupdf.Font(fontfile=FONT)

def text_width(text, size):
    return FONTOBJ.text_length(text, fontsize=size)

def fit_text(text, size, max_width, lines=1, line_height=None):
    """Return (size, [lines], overflow) mirroring form-engine.js layoutText."""
    tw = lambda s, t: text_width(t, s)
    s = size
    if lines <= 1:
        while s > MIN_SIZE and tw(s, text) > max_width:
            s = round(s - 0.5, 2)
        if tw(s, text) <= max_width:
            return s, [text], False
        # overflow: keep what fits (never write outside the cell)
        kept = text
        while kept and tw(s, kept) > max_width:
            kept = kept[:-1]
        return s, [kept], True
    s = size
    while True:
        out, cur = [], ''
        for ch in text:
            if cur and tw(s, cur + ch) > max_width:
                out.append(cur); cur = ch
            else:
                cur += ch
        if cur: out.append(cur)
        if len(out) <= lines:
            return s, out, False
        if s - 0.5 < MIN_SIZE:
            return s, out[:lines], True
        s = round(s - 0.5, 2)

def render(form_id, out_dir):
    schema = json.load(open(os.path.join(ROOT, 'data/form_schemas.json'), encoding='utf-8'))
    samples = json.load(open(os.path.join(ROOT, 'tests/fixtures/form_overlay_samples.json'), encoding='utf-8'))
    spec = schema['forms'][form_id]
    values = samples.get(form_id, {})
    doc = pymupdf.open(os.path.join(ROOT, spec['pdf']))
    ink = tuple(c / 255 for c in spec['ink'])
    report = []
    for key, o in spec['overlay'].items():
        val = values.get(key)
        if val in (None, '', False):
            continue
        page = doc[o.get('page', 0)]
        if o.get('check'):
            s = o.get('s', 5); cx, cy = o['cx'], o['cy']
            sh = page.new_shape()
            sh.draw_line((cx - 0.45 * s, cy - 0.02 * s), (cx - 0.12 * s, cy + 0.38 * s))
            sh.draw_line((cx - 0.12 * s, cy + 0.38 * s), (cx + 0.55 * s, cy - 0.5 * s))
            sh.finish(color=ink, width=1.1); sh.commit()
            report.append((key, 'check', '')); continue
        if o.get('wbox'):
            x0, y0, x1, y1 = o['wbox']; sh = page.new_shape(); sh.draw_rect((x0, y0, x1, y1)); sh.finish(color=None, fill=(1, 1, 1)); sh.commit()
        text = str(val)
        d = o.get('digits')
        if d and len([c for c in text if c.isdigit()]) == len(d['cells']):
            digits = [c for c in text if c.isdigit()]
            for ch, cx in zip(digits, d['cells']):
                w = text_width(ch, d.get('size', 10))
                page.insert_text((cx - w / 2, d['y']), ch, fontsize=d.get('size', 10), fontname='ko', fontfile=FONT, color=ink)
            report.append((key, 'digits', text)); continue
        size, lines, overflow = fit_text(text, o.get('size', 9), o.get('maxWidth', spec['pageWidth'] - o['x'] - 6), o.get('lines', 1), o.get('lineHeight'))
        lh = o.get('lineHeight', size * 1.2)
        for i, ln in enumerate(lines):
            x = o['x']
            if o.get('align') == 'center':
                x = o['x'] - text_width(ln, size) / 2
            page.insert_text((x, o['y'] + i * lh), ln, fontsize=size, fontname='ko', fontfile=FONT, color=ink)
        report.append((key, f"{'OVERFLOW ' if overflow else ''}{size}pt{' x' + str(len(lines)) if len(lines) > 1 else ''}", text[:30]))
    os.makedirs(out_dir, exist_ok=True)
    pdf_out = os.path.join(out_dir, f'{form_id}-filled.pdf'); doc.save(pdf_out)
    for i, page in enumerate(doc):
        page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(os.path.join(out_dir, f'{form_id}-{i + 1}.png'))
    for r in report:
        print(f"  {r[0]:22s} {r[1]:16s} {r[2]}")
    print(f"{form_id}: {len(report)} entries drawn -> {out_dir}")

if __name__ == '__main__':
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'artifacts/form-helper-qa')
    render(sys.argv[1], out)
