#!/usr/bin/env python3
"""Authoring aid: measure the free writing slot around each text overlay of a template.

  python3 scripts/forms/suggest_overlay_cells.py F01 [key ...]

For every text overlay it lists the obstacles on the overlay's glyph band (vertical table
rules and printed template text, from the PDF's own vector geometry) and the free slot
around the anchor x.
It prints the free slot holding the anchor and the next slot to its right, so the
right cell can be chosen per field. Nothing is written: the suggestion is reviewed against a rendered
crop before data/form_schemas.json is edited (see audit_overlay_geometry.py).
"""
import json, os, sys, warnings
warnings.filterwarnings('ignore')
import pymupdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_overlay_geometry import rules, row_bounds, overlap, ASC, DESC, ROOT

PAD = 2.5


def obstacles(words, V, y, size, wbox=None):
    b0, b1 = y - ASC * size, y + DESC * size
    band = b1 - b0
    obs = []
    for (vx, vy0, vy1) in V:
        if overlap(b0, b1, vy0, vy1) > 0.3 * band:
            obs.append((vx, vx, 'rule'))
    for w in words:
        if not w[4].strip():
            continue
        if wbox and w[0] >= wbox[0] - 0.5 and w[2] <= wbox[2] + 0.5 and w[1] >= wbox[1] - 0.5 and w[3] <= wbox[3] + 0.5:
            continue
        if overlap(b0, b1, w[1], w[3]) > 0.35 * min(band, w[3] - w[1]):
            obs.append((w[0], w[2], w[4]))
    return sorted(obs)


def slots(obs, page_w):
    """Free intervals between the obstacles of a band, left to right."""
    out, cur = [], 0.0
    for a, b, t in obs:
        if a > cur + 0.01:
            out.append((cur, a))
        cur = max(cur, b)
    if page_w > cur + 0.01:
        out.append((cur, page_w))
    return out


def main(argv):
    fid, keys = argv[0], set(argv[1:])
    spec = json.load(open(os.path.join(ROOT, 'data/form_schemas.json'), encoding='utf-8'))['forms'][fid]
    doc = pymupdf.open(os.path.join(ROOT, spec['pdf']))
    cache = {}
    for key, o in spec['overlay'].items():
        if o.get('check') or isinstance(o.get('digits'), dict) or (keys and key not in keys):
            continue
        pi = o.get('page', 0)
        if pi not in cache:
            cache[pi] = (doc[pi].get_text('words'), *rules(doc[pi]))
        words, V, H = cache[pi]
        size = o.get('size', 9)
        obs = obstacles(words, V, o['y'], size, o.get('wbox'))
        x = o['x']
        rb = row_bounds(H, x, o['y'], size)
        if rb:
            obs = sorted(obs + [(rb[2], rb[2], 'row-end'), (rb[3], rb[3], 'row-end')])
        sl = slots(obs, spec['pageWidth'])
        here = [s for s in sl if s[0] - 0.01 <= x <= s[1]]
        after = [s for s in sl if s[0] > x]
        cur = here[0] if here else None
        nxt = after[0] if after else None
        def fmt(s):
            return '-' if not s else f"({s[0]:.1f},{s[1]:.1f}) w={s[1]-s[0]:.1f}"
        mw = o.get('maxWidth')
        end = (x + mw) if mw else None
        state = 'ok'
        if cur is None: state = 'IN-OBSTACLE'
        elif end is not None and end > cur[1] + 0.3: state = 'MW-TOO-WIDE'
        elif mw is None: state = 'UNBOUNDED'
        tag = ' align=center' if o.get('align') == 'center' else ''
        row = f" row=({rb[0]:.1f}..{rb[1]:.1f}) mid-baseline={(rb[0] + rb[1]) / 2 + 0.36 * size:.1f}" if rb else ''
        print(f"{state:<12} {key:<22} x={x:<6} y={o['y']:<6} s={size:<4} mw={str(mw):<6}{tag} here={fmt(cur)} next={fmt(nxt)}{row}")


if __name__ == '__main__':
    main(sys.argv[1:])
