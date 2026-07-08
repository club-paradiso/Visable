#!/usr/bin/env python3
"""Structured diff between two versions of a HiKorea 안내 매뉴얼.

Given an OLD and a NEW extraction of the same manual (either the page-anchored
``*_readable.txt`` files or the richer ``*_sections.json`` inventories), this
produces a *review artifact*, not a data edit: it reports which pages changed
and — crucially — which 체류자격 codes those changed pages touch, so a reviewer
knows exactly which status records to re-check instead of diffing a 487/780-page
manual by hand.

Design constraints (see CLAUDE.md):
  * Read-only. Never edits visa_data.json / visas.json / doc_master.json or any
    authoring/grounding data. It only writes the report files you point it at.
  * Deterministic and stdlib-only (json, difflib, re, hashlib) so it runs
    offline in CI with no dependencies.
  * It surfaces *candidates for manual review*; it does not decide anything or
    invent requirements. The page->code mapping comes straight from the
    ``status_codes_detected`` the extraction already recorded.

Page alignment uses difflib.SequenceMatcher over per-page normalized text, so an
inserted or deleted page shifts the alignment correctly instead of reporting
every subsequent page as changed.

Usage:
    python3 scripts/diff_manual_versions.py \
        --old backend/data/sources/manuals/260617_stay_manual_sections.json \
        --new backend/data/sources/manuals/260623_stay_manual_sections.json \
        --role stay \
        --out-md build/manual-diff/stay_260617_to_260623.md \
        --out-json build/manual-diff/stay_260617_to_260623.json

Either input may be a ``*_sections.json`` (preferred — carries per-page
status_codes_detected) or a ``*_readable.txt`` (page text only; code mapping is
then best-effort via a code regex over the page text).
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

# Page banner in *_readable.txt, e.g.
# "===== 외국인체류 안내매뉴얼 2026.6 / PDF page 12 of 780 ====="
_PAGE_BANNER_RE = re.compile(r"=====\s*.*?PDF page\s+(\d+)\s+of\s+(\d+)\s*=====", re.IGNORECASE)

# A 체류자격 code as it appears in manual text: a letter-family + number, with
# optional sub-segments and the top-tier -T / region-S style suffixes.
_CODE_RE = re.compile(r"\b([A-H]-\d{1,2}(?:-\d{1,2}[A-Z]?|-[A-Z])?|K-STAR|REGION-S)\b")

# Whitespace normalization for page-alignment equality: collapse runs of
# whitespace so trivial reflow doesn't register as a content change, but keep
# the actual characters faithful (no lowercasing, no punctuation stripping).
_WS_RE = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS_RE.sub(" ", (text or "").strip())


@dataclass
class Page:
    page: int
    text: str
    codes: List[str] = field(default_factory=list)

    @property
    def norm(self) -> str:
        return _norm(self.text)


@dataclass
class Manual:
    label: str
    pages: List[Page]

    @property
    def page_count(self) -> int:
        return len(self.pages)


def _codes_from_text(text: str) -> List[str]:
    seen: List[str] = []
    for m in _CODE_RE.finditer(text or ""):
        c = m.group(1)
        if c not in seen:
            seen.append(c)
    return seen


def load_manual(path: Path, label: str) -> Manual:
    """Load either a *_sections.json or a page-anchored *_readable.txt."""
    if not path.exists():
        raise SystemExit(f"ERROR: manual extraction not found: {path}")
    if path.suffix == ".json":
        return _load_sections_json(path, label)
    return _load_readable_txt(path, label)


def _load_sections_json(path: Path, label: str) -> Manual:
    """Load a *_sections.json, tolerating both extraction schemas.

    Newer extractions (e.g. 260623) use per-page ``{page, text, heading,
    status_codes_detected, subcodes_detected}``. Older ones (e.g. 260617) use
    ``{pdf_page, title, paragraphs:[{text, status_codes_detected}],
    status_codes_detected}``. Both are normalized to a page-keyed text+codes
    view so the same manual can be diffed across a schema change.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"ERROR: {path} is not a sections.json list")
    pages: List[Page] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        page_no = entry.get("page")
        if not isinstance(page_no, int):
            page_no = entry.get("pdf_page")
        if not isinstance(page_no, int):
            continue

        codes: List[str] = list(entry.get("status_codes_detected") or [])

        text_val = entry.get("text")
        if isinstance(text_val, str) and text_val:
            text = text_val
        else:
            # Older schema: page text lives in a paragraphs[] list.
            paras = entry.get("paragraphs")
            chunks: List[str] = []
            if isinstance(paras, list):
                for para in paras:
                    if isinstance(para, dict):
                        pt = para.get("text")
                        if isinstance(pt, str):
                            chunks.append(pt)
                        for c in para.get("status_codes_detected") or []:
                            if c not in codes:
                                codes.append(c)
                    elif isinstance(para, str):
                        chunks.append(para)
            text = "\n".join(chunks)

        # Fold in subcodes the extractor tracked separately, if present.
        for sc in entry.get("subcodes_detected") or []:
            if sc not in codes:
                codes.append(sc)
        if not codes:
            codes = _codes_from_text(text)
        pages.append(Page(page=page_no, text=text, codes=codes))
    pages.sort(key=lambda p: p.page)
    return Manual(label=label, pages=pages)


def _load_readable_txt(path: Path, label: str) -> Manual:
    raw = path.read_text(encoding="utf-8", errors="replace")
    pages: List[Page] = []
    cur_page: Optional[int] = None
    buf: List[str] = []

    def flush() -> None:
        if cur_page is None:
            return
        text = "\n".join(buf)
        pages.append(Page(page=cur_page, text=text, codes=_codes_from_text(text)))

    for line in raw.splitlines():
        m = _PAGE_BANNER_RE.search(line)
        if m:
            flush()
            cur_page = int(m.group(1))
            buf = []
        else:
            buf.append(line)
    flush()
    pages.sort(key=lambda p: p.page)
    return Manual(label=label, pages=pages)


@dataclass
class PageChange:
    kind: str  # "changed" | "added" | "removed"
    old_page: Optional[int]
    new_page: Optional[int]
    old_codes: List[str]
    new_codes: List[str]
    text_diff: str  # unified diff of the page's normalized lines (truncated)


def _line_diff(old_text: str, new_text: str, max_lines: int) -> str:
    old_lines = [ln for ln in (old_text or "").splitlines() if ln.strip()]
    new_lines = [ln for ln in (new_text or "").splitlines() if ln.strip()]
    diff = list(
        difflib.unified_diff(old_lines, new_lines, lineterm="", n=1)
    )
    # Drop the ---/+++ file header lines; keep hunks.
    body = [ln for ln in diff if not (ln.startswith("---") or ln.startswith("+++"))]
    if len(body) > max_lines:
        body = body[:max_lines] + [f"... (+{len(body) - max_lines} more diff lines truncated)"]
    return "\n".join(body)


def diff_manuals(old: Manual, new: Manual, max_diff_lines: int) -> List[PageChange]:
    old_norms = [p.norm for p in old.pages]
    new_norms = [p.norm for p in new.pages]
    sm = difflib.SequenceMatcher(a=old_norms, b=new_norms, autojunk=False)
    changes: List[PageChange] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            # Pair up old/new pages positionally within the replace block; any
            # overhang becomes added/removed.
            span = max(i2 - i1, j2 - j1)
            for k in range(span):
                op = old.pages[i1 + k] if i1 + k < i2 else None
                npg = new.pages[j1 + k] if j1 + k < j2 else None
                if op is not None and npg is not None:
                    changes.append(
                        PageChange(
                            kind="changed",
                            old_page=op.page,
                            new_page=npg.page,
                            old_codes=op.codes,
                            new_codes=npg.codes,
                            text_diff=_line_diff(op.text, npg.text, max_diff_lines),
                        )
                    )
                elif npg is not None:
                    changes.append(
                        PageChange("added", None, npg.page, [], npg.codes,
                                   _line_diff("", npg.text, max_diff_lines))
                    )
                elif op is not None:
                    changes.append(
                        PageChange("removed", op.page, None, op.codes, [],
                                   _line_diff(op.text, "", max_diff_lines))
                    )
        elif tag == "insert":
            for j in range(j1, j2):
                npg = new.pages[j]
                changes.append(
                    PageChange("added", None, npg.page, [], npg.codes,
                               _line_diff("", npg.text, max_diff_lines))
                )
        elif tag == "delete":
            for i in range(i1, i2):
                op = old.pages[i]
                changes.append(
                    PageChange("removed", op.page, None, op.codes, [],
                               _line_diff(op.text, "", max_diff_lines))
                )
    return changes


def _base_code(code: str) -> str:
    """Return the parent/base code for aggregation (D-2-1 -> D-2)."""
    if code in ("K-STAR", "REGION-S"):
        return code
    parts = code.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return code


def aggregate_affected_codes(changes: List[PageChange]) -> Dict[str, Dict[str, object]]:
    """Map each affected code -> the pages (new-version numbering) touching it."""
    affected: Dict[str, Dict[str, object]] = {}
    for ch in changes:
        page_ref = ch.new_page if ch.new_page is not None else ch.old_page
        for code in sorted(set(ch.old_codes) | set(ch.new_codes)):
            slot = affected.setdefault(code, {"code": code, "base": _base_code(code), "pages": set(), "kinds": set()})
            slot["pages"].add(page_ref)
            slot["kinds"].add(ch.kind)
    # Freeze sets into sorted lists for JSON.
    for slot in affected.values():
        slot["pages"] = sorted(p for p in slot["pages"] if p is not None)
        slot["kinds"] = sorted(slot["kinds"])
    return affected


def load_ledger() -> Dict[str, dict]:
    path = REPO_ROOT / "backend/data/visa_authoring/audit/source_manual_status.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    by_code = data.get("byCode") if isinstance(data, dict) else None
    return by_code if isinstance(by_code, dict) else {}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    """Repo-relative path when possible, else the path as given."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def build_report(
    old: Manual,
    new: Manual,
    old_path: Path,
    new_path: Path,
    role: str,
    changes: List[PageChange],
    max_pages_detail: int,
) -> Tuple[str, dict]:
    affected = aggregate_affected_codes(changes)
    ledger = load_ledger()

    n_changed = sum(1 for c in changes if c.kind == "changed")
    n_added = sum(1 for c in changes if c.kind == "added")
    n_removed = sum(1 for c in changes if c.kind == "removed")

    # Honesty guard: if almost every page "changed", the two inputs were almost
    # certainly produced by DIFFERENT extraction pipelines (e.g. paragraphs[] vs
    # a single text blob), so the diff is dominated by extraction noise rather
    # than real content changes. The tool is only meaningful on same-pipeline
    # extractions. Flag it loudly instead of implying 700 real edits.
    denom = max(old.page_count, new.page_count, 1)
    change_ratio = (n_changed + n_added + n_removed) / denom
    noisy = change_ratio > 0.6

    # Group affected codes by base for a compact reviewer summary.
    bases: Dict[str, List[str]] = {}
    for code, slot in affected.items():
        bases.setdefault(slot["base"], []).append(code)

    version_field = "stayManualVersion" if role == "stay" else "visaManualVersion"

    json_report = {
        "schema_version": "1.0",
        "role": role,
        "old": {
            "path": _rel(old_path),
            "sha256": _sha256(old_path),
            "page_count": old.page_count,
        },
        "new": {
            "path": _rel(new_path),
            "sha256": _sha256(new_path),
            "page_count": new.page_count,
        },
        "summary": {
            "pages_changed": n_changed,
            "pages_added": n_added,
            "pages_removed": n_removed,
            "affected_code_count": len(affected),
            "affected_base_code_count": len(bases),
            "change_ratio": round(change_ratio, 3),
            "extraction_mismatch_suspected": noisy,
        },
        "affected_codes": [
            {
                "code": code,
                "base": slot["base"],
                "pages": slot["pages"],
                "kinds": slot["kinds"],
                "ledger": _ledger_view(ledger.get(code) or ledger.get(slot["base"]), version_field),
            }
            for code, slot in sorted(affected.items())
        ],
        "page_changes": [
            {
                "kind": c.kind,
                "old_page": c.old_page,
                "new_page": c.new_page,
                "codes": sorted(set(c.old_codes) | set(c.new_codes)),
            }
            for c in changes
        ],
    }

    md = _render_markdown(old, new, json_report, changes, bases, affected, ledger,
                          version_field, max_pages_detail, noisy)
    return md, json_report


def _ledger_view(entry: Optional[dict], version_field: str) -> Optional[dict]:
    if not isinstance(entry, dict):
        return None
    return {
        "manualVersion": entry.get(version_field),
        "verified": entry.get("verified"),
        "needsManualReview": entry.get("needsManualReview"),
    }


def _render_markdown(old, new, jr, changes, bases, affected, ledger, version_field,
                     max_pages_detail, noisy) -> str:
    s = jr["summary"]
    lines: List[str] = []
    lines.append(f"# 매뉴얼 구조적 diff — {jr['role']} manual")
    lines.append("")
    lines.append("> 이 리포트는 검토 보조 자료입니다. 어떤 데이터도 자동으로 바꾸지 않으며, "
                 "바뀐 페이지와 그 페이지가 다루는 체류자격만 표시합니다. 실제 반영은 사람이 원문을 "
                 "대조한 뒤 결정하세요.")
    lines.append("")
    if noisy:
        lines.append(
            f"> ⚠️ **추출 파이프라인 불일치 의심** — 전체의 {int(s['change_ratio'] * 100)}%가 변경으로 "
            "잡혔습니다. 두 입력이 서로 다른 방식으로 추출됐을 가능성이 높습니다(예: 구 스키마 "
            "`paragraphs[]` vs 신 스키마 `text`). 이 경우 diff는 실제 내용 변경이 아니라 추출 "
            "노이즈에 지배됩니다. 같은 추출 파이프라인으로 만든 두 버전을 비교하세요.")
        lines.append("")
    lines.append(f"- old: `{jr['old']['path']}` ({old.page_count} pages)")
    lines.append(f"- new: `{jr['new']['path']}` ({new.page_count} pages)")
    lines.append(
        f"- 변경 페이지 **{s['pages_changed']}**, 추가 **{s['pages_added']}**, "
        f"삭제 **{s['pages_removed']}** · 영향 코드 **{s['affected_code_count']}** "
        f"(상위코드 {s['affected_base_code_count']})"
    )
    lines.append("")

    if not changes:
        lines.append("## 결과: 변경 없음")
        lines.append("")
        lines.append("두 추출본은 페이지 텍스트 기준으로 동일합니다 (공백 정규화 후).")
        return "\n".join(lines) + "\n"

    # Affected-codes table, grouped by base code, with ledger status.
    lines.append("## 영향받는 체류자격 (검토 필요 후보)")
    lines.append("")
    lines.append("| 상위코드 | 세부/코드 | 변경 페이지(new) | 원장 매뉴얼버전 | needsManualReview |")
    lines.append("| --- | --- | --- | --- | --- |")
    for base in sorted(bases):
        codes = sorted(set(bases[base]))
        for code in codes:
            slot = affected[code]
            pages = ", ".join(str(p) for p in slot["pages"][:12])
            if len(slot["pages"]) > 12:
                pages += f", …(+{len(slot['pages']) - 12})"
            led = ledger.get(code) or ledger.get(base) or {}
            ver = led.get(version_field, "—")
            nmr = led.get("needsManualReview")
            nmr_s = "true" if nmr is True else ("false" if nmr is False else "—")
            lines.append(f"| {base} | {code} | {pages} | {ver} | {nmr_s} |")
    lines.append("")

    # Per-page detail, truncated to keep the artifact reviewable.
    lines.append("## 페이지별 변경 상세")
    lines.append("")
    shown = 0
    for c in changes:
        if shown >= max_pages_detail:
            lines.append(f"_… 페이지 상세 {len(changes) - shown}건 생략 (JSON 리포트에 전체 목록 있음)_")
            break
        codes = sorted(set(c.old_codes) | set(c.new_codes))
        code_s = ", ".join(codes) if codes else "(코드 미검출)"
        if c.kind == "changed":
            head = f"### 변경 · old p{c.old_page} → new p{c.new_page}"
        elif c.kind == "added":
            head = f"### 추가 · new p{c.new_page}"
        else:
            head = f"### 삭제 · old p{c.old_page}"
        lines.append(head)
        lines.append(f"코드: {code_s}")
        lines.append("")
        if c.text_diff.strip():
            lines.append("```diff")
            lines.append(c.text_diff)
            lines.append("```")
        lines.append("")
        shown += 1

    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Structured diff between two manual extractions")
    ap.add_argument("--old", required=True, help="old *_sections.json or *_readable.txt")
    ap.add_argument("--new", required=True, help="new *_sections.json or *_readable.txt")
    ap.add_argument("--role", choices=["stay", "visa"], required=True)
    ap.add_argument("--out-md", help="write the Markdown review artifact here")
    ap.add_argument("--out-json", help="write the JSON report here")
    ap.add_argument("--max-diff-lines", type=int, default=40,
                    help="max unified-diff lines shown per changed page")
    ap.add_argument("--max-pages-detail", type=int, default=60,
                    help="max changed pages to render in the Markdown detail section")
    ap.add_argument("--fail-on-change", action="store_true",
                    help="exit 2 when any page changed (for CI gating)")
    args = ap.parse_args(argv)

    old_path = Path(args.old)
    new_path = Path(args.new)
    old = load_manual(old_path, "old")
    new = load_manual(new_path, "new")

    changes = diff_manuals(old, new, args.max_diff_lines)
    md, jr = build_report(old, new, old_path, new_path, args.role, changes, args.max_pages_detail)

    if args.out_md:
        out_md = Path(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(md, encoding="utf-8")
    if args.out_json:
        out_json = Path(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(jr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    s = jr["summary"]
    print(
        f"[diff_manual_versions] role={args.role} "
        f"changed={s['pages_changed']} added={s['pages_added']} removed={s['pages_removed']} "
        f"affected_codes={s['affected_code_count']} (base {s['affected_base_code_count']})"
    )
    if not args.out_md and not args.out_json:
        # No output target: print the Markdown to stdout so the tool is useful ad-hoc.
        print()
        print(md)

    if args.fail_on_change and (s["pages_changed"] or s["pages_added"] or s["pages_removed"]):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
