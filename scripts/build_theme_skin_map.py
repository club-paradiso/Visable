#!/usr/bin/env python3
"""Build assets/css/visable-theme-legacy.css.

Some pages still paint with hard-coded civic-green hex values instead of
tokens. This script finds those declarations in each page's own stylesheet
(and inline <style> blocks), and re-emits them scoped to the selected skin:

    :where(:root[data-vt][data-vt-page="<page>"]) <original selector> { prop: var(--vs-*) }

so the four Visable skins (assets/css/visable-theme-skins.css) reach them too.
Nothing in the source stylesheets is modified. Success / verified / checked
states keep their semantic green on purpose.

Dev dependency: tinycss2 (pip install tinycss2). Run:
    python3 scripts/build_theme_skin_map.py          # write
    python3 scripts/build_theme_skin_map.py --check  # fail if stale
"""
import colorsys
import pathlib
import re
import sys

import tinycss2

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/css/visable-theme-legacy.css"

# page id (html[data-vt-page]) -> sources (css files, or html files whose <style> blocks are read)
PAGES = {
    "immigration-checklists": ["assets/css/immigration-checklists.css", "immigration-checklists.html"],
    "agency-directory": ["agency-directory/style.css", "agency-directory/index.html"],
    "enforcement": ["assets/css/enforcement.css", "enforcement.html"],
    "nationality-interview-hub": ["nationality-interview-hub.html"],
    "form-helper": ["assets/css/form-helper.css", "form-helper.html"],
    "knowledge-studio": ["assets/css/knowledge-studio.css", "knowledge-studio.html"],
    "content-studio": ["assets/css/content-studio.css", "content-studio.html"],
}

SEMANTIC = re.compile(r"ok\b|success|done|verified|verify|checked|valid|pass|complete|confirm|correct|positive|good", re.I)
SKIP_SEL = re.compile(r"archive_diary|data-editorial-theme")
HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
COLOR_PROPS = {"color", "fill", "stroke", "caret-color", "text-decoration-color", "-webkit-text-fill-color"}


def hls(h):
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, l, s = colorsys.rgb_to_hls(r, g, b)
    return hh * 360, l, s


def is_green(h):
    hue, l, s = hls(h)
    return 135 <= hue <= 185 and s > 0.08 and 0.04 < l < 0.985


def token_for(prop, h):
    _, l, s = hls(h)
    p = prop.lower()
    if p in COLOR_PROPS:
        if l > 0.75:
            return "var(--vs-hdr-ink)"
        if s > 0.3 or l < 0.3:
            return "var(--vs-ac-text)"
        return "var(--vs-ink3)"
    if p.startswith("background"):
        if l > 0.85:
            return "var(--vs-ac-soft)" if s > 0.3 else "var(--vs-bg2)"
        if l > 0.6:
            return "var(--vs-line2)"
        return "var(--vs-hdr)" if l < 0.25 else "var(--vs-ac)"
    # borders, outlines, shadows, rules
    if l > 0.85:
        return "var(--vs-line)"
    if l > 0.6:
        return "var(--vs-line2)"
    return "var(--vs-ac)"


def scope(page, selector):
    # :where() keeps the original selector's specificity, so the page's own
    # state rules (.active, :hover …) that use tokens still win as before.
    pre = f':where(:root[data-vt][data-vt-page="{page}"])'
    out = []
    for part in selector.split(","):
        part = " ".join(part.split())
        if not part:
            continue
        m = re.match(r"^(?::root|html)((?:\[[^\]]*\]|:not\([^)]*\))*)(.*)$", part)
        if m:
            out.append(pre + m.group(1) + m.group(2))
        else:
            out.append(pre + " " + part)
    return ",\n".join(out)


def rules_from(css, page, media=None):
    emitted = []
    for node in tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True):
        if node.type == "at-rule" and node.lower_at_keyword in ("media", "supports") and node.content:
            cond = tinycss2.serialize(node.prelude).strip()
            inner = rules_from(tinycss2.serialize(node.content), page, media=f"@{node.lower_at_keyword} {cond}")
            emitted.extend(inner)
            continue
        if node.type != "qualified-rule":
            continue
        sel = tinycss2.serialize(node.prelude).strip()
        if SKIP_SEL.search(sel) or SEMANTIC.search(sel) or sel.startswith("@") or "%" in sel:
            continue
        decls = []
        for d in tinycss2.parse_declaration_list(node.content, skip_comments=True, skip_whitespace=True):
            if d.type != "declaration" or d.name.startswith("--"):
                continue
            val = tinycss2.serialize(d.value).strip()
            if not any(is_green(m.group(1)) for m in HEX.finditer(val)):
                continue
            new = HEX.sub(lambda m: token_for(d.name, m.group(1)) if is_green(m.group(1)) else m.group(0), val)
            decls.append(f"  {d.name}: {new}{' !important' if d.important else ''};")
        if decls:
            body = scope(page, sel) + " {\n" + "\n".join(decls) + "\n}"
            emitted.append((media, body))
    return emitted


def css_of(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    if path.endswith(".html"):
        return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", text, re.S))
    return text


def build():
    parts = [
        "/* GENERATED by scripts/build_theme_skin_map.py — do not edit by hand.",
        "   Re-points hard-coded civic-green values on individual pages to the",
        "   active Visable skin tokens. Only applies when html[data-vt] is set. */",
    ]
    for page, sources in PAGES.items():
        rules = []
        for src in sources:
            if (ROOT / src).exists():
                rules.extend(rules_from(css_of(src), page))
        if not rules:
            continue
        parts.append(f"\n/* ---- {page} ---- */")
        for media, body in rules:
            parts.append(f"{media} {{\n{body}\n}}" if media else body)
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    out = build()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != out:
            print("visable-theme-legacy.css is stale — run scripts/build_theme_skin_map.py")
            sys.exit(1)
        print("visable-theme-legacy.css up to date")
    else:
        OUT.write_text(out, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)} ({len(out)} bytes)")
