#!/usr/bin/env python3
"""Verify an exported Form Helper PDF against the drawing operations the preview used.

  python3 scripts/forms/verify_export.py <export.pdf> <ops.json>

ops.json = {"form": "F08", "edition": "F08", "ops": [...]} as produced by the browser
(VisableFormHelper.state.ops). For every text op the PDF must contain a text span with
the same string whose baseline and left edge sit within 1.5 pt of the op and whose
right edge stays inside the printed cell (op.x + maxWidth); every check op must have
a vector stroke within 4 pt of its centre; no drawn text may lie outside the page.
Exit code 1 on any mismatch. Requires PyMuPDF.
"""
import json, os, sys, warnings
warnings.filterwarnings('ignore')
import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main(pdf_path, ops_path):
    ops_doc = json.load(open(ops_path, encoding='utf-8'))
    schema = json.load(open(os.path.join(ROOT, 'data/form_schemas.json'), encoding='utf-8'))
    spec = schema['forms'][ops_doc.get('edition') or ops_doc['form']]
    template = pymupdf.open(os.path.join(ROOT, spec['pdf']))
    doc = pymupdf.open(pdf_path)
    fails, checked = [], 0
    if len(doc) != len(template):
        fails.append(f'page count {len(doc)} != template {len(template)}')
    # baseline text spans that were NOT on the blank template (added by the export)
    added = {}
    for pi, page in enumerate(doc):
        base = set()
        for b in template[pi].get_text('dict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    base.add((s['text'], round(s['origin'][0]), round(s['origin'][1])))
        spans = []
        for b in page.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    key = (s['text'], round(s['origin'][0]), round(s['origin'][1]))
                    if key in base: continue
                    spans.append({'text': s['text'], 'x0': s['bbox'][0], 'x1': s['bbox'][2], 'y': s['origin'][1], 'size': s['size']})
        added[pi] = spans
    for op in ops_doc['ops']:
        pi = op.get('page', 0)
        if op['type'] == 'text':
            checked += 1
            cands = [s for s in added.get(pi, []) if s['text'] == op['text'] and abs(s['y'] - op['y']) <= 1.5 and abs(s['x0'] - op['x']) <= 1.5]
            if not cands:
                near = [s for s in added.get(pi, []) if abs(s['y'] - op['y']) <= 3]
                fails.append(f"text op {op['key']} '{op['text']}' not found at ({op['x']:.1f},{op['y']:.1f}) p{pi}; nearby: {[ (n['text'], round(n['x0'],1), round(n['y'],1)) for n in near ][:3]}")
                continue
            s = cands[0]
            page_w = spec['pageWidth']
            limit = op['x'] + op['maxWidth'] + 1.5 if op.get('maxWidth') else page_w - 2
            if s['x1'] > limit + 0.01:
                fails.append(f"text op {op['key']} '{op['text']}' right edge {s['x1']:.1f} exceeds cell limit {limit:.1f}")
            if s['x0'] < 0 or s['x1'] > page_w or s['y'] < 0 or s['y'] > spec['pageHeight']:
                fails.append(f"text op {op['key']} outside the page")
            if abs(s['size'] - op['size']) > 0.3:
                fails.append(f"text op {op['key']} size {s['size']} != {op['size']}")
        elif op['type'] == 'check':
            checked += 1
            page = doc[pi]
            found = False
            for d in page.get_drawings():
                for it in d['items']:
                    if it[0] == 'l':
                        for pt in (it[1], it[2]):
                            if abs(pt.x - op['cx']) <= 4 and abs(pt.y - op['cy']) <= 4: found = True
            if not found:
                fails.append(f"check op {op['key']} has no stroke near ({op['cx']},{op['cy']}) p{pi}")
    # every added span must belong to some op (nothing drawn that the preview did not show)
    for pi, spans in added.items():
        for s in spans:
            if not any(o['type'] == 'text' and o.get('page', 0) == pi and o['text'] == s['text'] and abs(o['y'] - s['y']) <= 1.5 for o in ops_doc['ops']):
                fails.append(f"unexpected text in export p{pi}: '{s['text']}' at ({s['x0']:.1f},{s['y']:.1f})")
    print(f"[verify_export] {os.path.basename(pdf_path)}: {checked} ops checked, {sum(len(v) for v in added.values())} added spans, {len(fails)} failures")
    for f in fails: print('  FAIL', f)
    return 1 if fails else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
