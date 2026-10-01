#!/usr/bin/env python3
"""Fail when index.html declares a design token that can never apply.

A custom property declared in an unconditional rule is dead when a LATER
unconditional rule with the identical selector declares the same property with
at least the same importance: same specificity, later in the cascade, so the
earlier value never wins. Such duplicates are how the inline token layers drifted
(two different --shadow-lift values, three copies of every font stack).

Only exact-selector, unconditional (no @media/@supports/...) rules are compared,
so the check has no false positives; it does not try to reason across
selectors. Inline <style> blocks only (index.html carries the token layers).

    python3 scripts/check_index_dead_tokens.py [path/to/index.html]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _blank(match: re.Match) -> str:
    return " " * len(match.group(0))


def unconditional_rules(html: str):
    """Yield (selector, body_start, body_end) for top-level rules in <style> blocks."""
    for block in re.finditer(r"<style[^>]*>(.*?)</style>", html, re.S):
        base, css = block.start(1), block.group(1)
        # Comments blanked (offsets kept); strings additionally blanked only for
        # finding braces, so selectors keep their attribute values.
        text = re.sub(r"/\*.*?\*/", _blank, css, flags=re.S)
        clean = re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', _blank, text)
        stack, prelude_start = [], 0
        for i, ch in enumerate(clean):
            if ch == "{":
                stack.append((text[prelude_start:i].strip(), i + 1))
                prelude_start = i + 1
            elif ch == "}":
                if not stack:
                    prelude_start = i + 1
                    continue
                prelude, body_start = stack.pop()
                if not stack and not prelude.startswith("@"):
                    yield " ".join(prelude.split()), base + body_start, base + i
                prelude_start = i + 1
            elif ch == ";" and not stack:
                prelude_start = i + 1


def dead_declarations(html: str):
    decls = []
    for selector, start, end in unconditional_rules(html):
        body = re.sub(r"/\*.*?\*/", _blank, html[start:end], flags=re.S)
        for m in re.finditer(r"(--[A-Za-z0-9_-]+)\s*:([^;]*)(?:;|$)", body):
            decls.append((start + m.start(), selector, m.group(1), "!important" in m.group(2).replace(" ", "")))
    decls.sort()
    dead = []
    for i, (pos, selector, prop, important) in enumerate(decls):
        if any(s == selector and p == prop and (imp or not important) for _, s, p, imp in decls[i + 1:]):
            dead.append((html.count("\n", 0, pos) + 1, selector, prop))
    return dead


def main(argv) -> int:
    path = Path(argv[1]) if len(argv) > 1 else ROOT / "index.html"
    dead = dead_declarations(path.read_text(encoding="utf-8"))
    if dead:
        print(f"[check_index_dead_tokens] FAIL — {len(dead)} token declaration(s) overridden by a later identical rule:")
        for line, selector, prop in dead:
            print(f"  {path.name}:{line}  {selector} {{ {prop} }}")
        print("  Remove the earlier declaration (the later one is what renders).")
        return 1
    print("[check_index_dead_tokens] OK — no dead token declarations")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
