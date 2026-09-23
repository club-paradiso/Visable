#!/usr/bin/env python3
"""Static geometry audit of every Form Helper overlay against its official template.

  python3 scripts/forms/audit_overlay_geometry.py            # all templates, exit 1 on any issue
  python3 scripts/forms/audit_overlay_geometry.py F01 F04    # selected templates
  python3 scripts/forms/audit_overlay_geometry.py --json     # machine-readable report
  python3 scripts/forms/audit_overlay_geometry.py --schema other.json   # audit another schema file

verify_export.py proves that the export draws exactly what the preview drew. This audit
proves that WHERE both draw is inside the right box, for every overlay (not only the
ones a sample happens to fill). For each text overlay the whole writable area —
[x, x + maxWidth] (centred for align=center) × the glyph band of every line — must:

  UNBOUNDED      declare a maxWidth (otherwise the fit engine lets text run to the page
                 edge, across neighbouring cells, without an OVERFLOW warning);
  CROSSES_RULE   not contain a vertical table rule of the template;
  CROSSES_HRULE  not have a horizontal rule running through the glyphs;
  OVERLAPS_TEXT  not overlap printed template text (labels, units, 년/월/일 …), unless
                 that text sits under the overlay's own white-out box (wbox);
  TOUCHES_LABEL  keep a visible gap to printed text it does not overlap: at least 1.5 pt
                 below a label it sits under, and no label tail running into its start
                 (inline slots after ':' or '(' are exempt — the bracket is the boundary);
  OUTSIDE_ROW    stay within the table row it starts in (forms without side borders end
                 a row where its top and bottom rules end);
  OFF_PAGE       stay on the page.

Every digit of a `digits` overlay must sit between two rules, and every check mark
centre must lie inside the page. Requires PyMuPDF (pip install pymupdf).
"""
import json, os, sys, warnings
warnings.filterwarnings('ignore')
import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASC, DESC = 0.80, 0.14          # NanumGothic glyph band around the baseline (em)
EPS = 0.35                      # rules this close to the area edge are its borders, not crossings


def _merge_dots(dots):
    """Dotted rules are drawn as runs of ~0.5 pt dashes: merge collinear dashes whose
    gaps stay under 1.3 pt into one rule segment (pos, start, end)."""
    out, groups = [], {}
    for pos, s, e in dots:
        groups.setdefault(round(pos, 1), []).append((s, e))
    for pos, segs in groups.items():
        segs.sort()
        cs, ce = segs[0]
        for s, e in segs[1:]:
            if s - ce <= 1.3:
                ce = max(ce, e)
            else:
                if ce - cs > 2: out.append((pos, cs, ce))
                cs, ce = s, e
        if ce - cs > 2: out.append((pos, cs, ce))
    return out


def rules(page):
    """Vertical and horizontal rule segments of the template page (lines, dotted lines,
    hairline rectangles and the edges of stroked rectangles)."""
    V, H, vdots, hdots = [], [], [], []
    for d in page.get_drawings():
        stroked = 's' in (d.get('type') or '')
        dr = d['rect']
        if dr.width < 1.0 and dr.height < 1.0:
            # a dotted rule drawn as tiny filled circles/squares: one dot per path
            cx, cy = (dr.x0 + dr.x1) / 2, (dr.y0 + dr.y1) / 2
            vdots.append((cx, dr.y0, dr.y1)); hdots.append((cy, dr.x0, dr.x1))
            continue
        for it in d['items']:
            if it[0] == 'l':
                a, b = it[1], it[2]
                if abs(a.x - b.x) < 0.6:
                    (V if abs(a.y - b.y) > 1 else vdots).append((a.x, min(a.y, b.y), max(a.y, b.y)))
                elif abs(a.y - b.y) < 0.6:
                    (H if abs(a.x - b.x) > 1 else hdots).append((a.y, min(a.x, b.x), max(a.x, b.x)))
            elif it[0] in ('re', 'qu'):
                r = it[1].rect if it[0] == 'qu' else it[1]
                if r.width < 1.6 and r.height > 1:
                    V.append(((r.x0 + r.x1) / 2, r.y0, r.y1))
                elif r.height < 1.6 and r.width > 1:
                    H.append(((r.y0 + r.y1) / 2, r.x0, r.x1))
                elif stroked:
                    V += [(r.x0, r.y0, r.y1), (r.x1, r.y0, r.y1)]
                    H += [(r.y0, r.x0, r.x1), (r.y1, r.x0, r.x1)]
    return _merge_collinear(V + _merge_dots(vdots)), _merge_collinear(H + _merge_dots(hdots))


def _merge_collinear(segs, tol=0.3, gap=0.8):
    """Rules are often drawn as several touching pieces: join pieces on the same line
    (positions within `tol`) whose ends meet within `gap` pt. Keeps (pos, start, end)."""
    out = []
    for pos, s, e in sorted(segs):
        for i, (p2, s2, e2) in enumerate(out):
            if abs(p2 - pos) <= tol and s <= e2 + gap and e >= s2 - gap:
                out[i] = (p2, min(s, s2), max(e, e2))
                break
        else:
            out.append((pos, s, e))
    # a second pass joins pieces that only met through a later merge
    changed = True
    while changed:
        changed = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a, b = out[i], out[j]
                if abs(a[0] - b[0]) <= tol and b[1] <= a[2] + gap and b[2] >= a[1] - gap:
                    out[i] = (a[0], min(a[1], b[1]), max(a[2], b[2])); del out[j]; changed = True
                    break
            if changed:
                break
    return out


def overlap(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0)


def row_bounds(H, x, y, size, reach=30):
    """The table row around a baseline: nearest horizontal rules above the glyph band and
    below the baseline that cover x (within `reach` pt). Returns (top, bottom, left, right)
    where left/right are where both rules end — forms without outer side borders end
    the row there. None when the text does not sit between two rules."""
    top = [(hy, hx0, hx1) for hy, hx0, hx1 in H if hx0 - 0.5 <= x <= hx1 + 0.5 and y - ASC * size - reach <= hy <= y - 0.45 * size]
    bot = [(hy, hx0, hx1) for hy, hx0, hx1 in H if hx0 - 0.5 <= x <= hx1 + 0.5 and y - 0.05 * size <= hy <= y + reach]
    if not top or not bot:
        return None
    t = max(top, key=lambda r: r[0]); b = min(bot, key=lambda r: r[0])
    return (t[0], b[0], max(t[1], b[1]), min(t[2], b[2]))


def audit_spec(fid, spec):
    tpl = pymupdf.open(os.path.join(ROOT, spec['pdf']))
    cache, issues, checked = {}, [], 0
    W, Hh = spec['pageWidth'], spec['pageHeight']
    for key, o in spec.get('overlay', {}).items():
        pi = o.get('page', 0)
        if pi not in cache:
            page = tpl[pi]
            cache[pi] = (page.get_text('words'), *rules(page))
        words, V, H = cache[pi]
        checked += 1
        if o.get('check'):
            if not (0 < o['cx'] < W and 0 < o['cy'] < Hh):
                issues.append((key, 'OFF_PAGE', f"check centre ({o['cx']},{o['cy']})"))
            continue
        if isinstance(o.get('digits'), dict):
            dg = o['digits']; size = dg.get('size', 10); y = dg['y']
            for i, cx in enumerate(dg['cells']):
                hw = 0.31 * size
                for (vx, vy0, vy1) in V:
                    if cx - hw + EPS < vx < cx + hw - EPS and overlap(y - ASC * size, y + DESC * size, vy0, vy1) > 0.3 * size:
                        issues.append((key, 'CROSSES_RULE', f'digit cell {i} at x={cx} crosses the rule x={vx:.1f}'))
            continue
        size = o.get('size', 9)
        if not o.get('maxWidth'):
            issues.append((key, 'UNBOUNDED', f"no maxWidth (x={o['x']}, y={o['y']})"))
            continue
        mw = o['maxWidth']
        x0 = o['x'] - mw / 2 if o.get('align') == 'center' else o['x']
        x1 = x0 + mw
        n = o.get('lines', 1); lh = o.get('lineHeight') or size * 1.2
        y0 = o['y'] - ASC * size
        y1 = o['y'] + (n - 1) * lh + DESC * size
        if x0 < 0 or x1 > W or y0 < 0 or y1 > Hh:
            issues.append((key, 'OFF_PAGE', f'area ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f})'))
        rb = row_bounds(H, x0 + 0.5, o['y'], size)
        if rb and (x1 > rb[3] + 0.5 or x0 < rb[2] - 0.5):
            issues.append((key, 'OUTSIDE_ROW', f'area x {x0:.1f}-{x1:.1f} leaves the row x {rb[2]:.1f}-{rb[3]:.1f}'))
        band = ASC * size + DESC * size
        wb = o.get('wbox')
        for (vx, vy0, vy1) in V:
            if x0 + EPS < vx < x1 - EPS and overlap(y0, y1, vy0, vy1) > 0.3 * band:
                issues.append((key, 'CROSSES_RULE', f'area x {x0:.1f}-{x1:.1f} contains the rule x={vx:.1f} (y {vy0:.1f}-{vy1:.1f})'))
        for (hy, hx0, hx1) in H:
            for li in range(n):
                by = o['y'] + li * lh
                if by - ASC * size + 0.3 * band < hy < by + DESC * size - 0.1 * band and overlap(x0, x1, hx0, hx1) > 1:
                    issues.append((key, 'CROSSES_HRULE', f'line {li} (baseline {by:.1f}) is cut by the rule y={hy:.1f}'))
        for w in words:
            if not w[4].strip():
                continue
            if wb and w[0] >= wb[0] - 0.5 and w[2] <= wb[2] + 0.5 and w[1] >= wb[1] - 0.5 and w[3] <= wb[3] + 0.5:
                continue  # printed placeholder under this overlay's own white-out box
            ix = overlap(x0, x1, w[0], w[2]); iy = overlap(y0, y1, w[1], w[3])
            if not (ix > 0.6 and iy > 0.35 * min(y1 - y0, w[3] - w[1])):
                if ix > 0.6 and w[3] <= o['y'] and -0.35 * min(y1 - y0, w[3] - w[1]) <= y0 - w[3] < 1.5:
                    issues.append((key, 'TOUCHES_LABEL', f"glyph top {y0:.1f} is {y0 - w[3]:.1f} pt under printed '{w[4]}' (bottom {w[3]:.1f})"))
                elif iy > 0 and w[0] < x0 and -3 <= x0 - w[2] < 0.3 and w[4][-1] not in ':：(（[' and o.get('align') != 'center':
                    issues.append((key, 'TOUCHES_LABEL', f"printed '{w[4]}' ends at {w[2]:.1f}, the value starts at {x0:.1f}"))
            if ix > 0.6 and iy > 0.35 * min(y1 - y0, w[3] - w[1]):
                issues.append((key, 'OVERLAPS_TEXT', f"area x {x0:.1f}-{x1:.1f} overlaps printed '{w[4]}' at x {w[0]:.1f}-{w[2]:.1f}"))
    return checked, issues


def main(argv):
    as_json = '--json' in argv
    schema_path = os.path.join(ROOT, 'data/form_schemas.json')
    if '--schema' in argv:
        i = argv.index('--schema'); schema_path = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    ids = [a for a in argv if not a.startswith('--')]
    schema = json.load(open(schema_path, encoding='utf-8'))
    report, total, bad = {}, 0, 0
    for fid, spec in sorted(schema['forms'].items()):
        if ids and fid not in ids:
            continue
        checked, issues = audit_spec(fid, spec)
        total += checked; bad += len(issues)
        report[fid] = {'checked': checked, 'issues': [{'key': k, 'kind': c, 'detail': d} for k, c, d in issues]}
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        for fid, r in report.items():
            print(f"[audit_overlay_geometry] {fid}: {r['checked']} overlays, {len(r['issues'])} issues")
            for i in r['issues']:
                print(f"  {i['kind']:<14} {i['key']:<22} {i['detail']}")
        print(f'[audit_overlay_geometry] {total} overlays checked, {bad} issues')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
