#!/usr/bin/env python3
"""Structured diff between two *paragraph-anchored* extractions of a 안내 매뉴얼.

Companion to ``scripts/diff_manual_versions.py``. That tool aligns two
*page-anchored* extractions (``*_readable.txt`` / ``*_sections.json``) and needs
a ``=== PAGE n ===`` banner to anchor on. The 배포용 HWP editions read by
``scripts/decrypt_hwp_distribution.py`` have no page layer at all — the ViewText
stream yields a paragraph sequence — so those inputs cannot be used, and until a
second HWP edition existed there was nothing to compare. This tool covers that
case: it aligns on paragraphs and anchors every change to the nearest preceding
체류자격-bearing heading.

Design constraints (see CLAUDE.md), identical to the page-anchored tool:
  * Read-only. It never edits visa_data.json / visas.json / doc_master.json or
    any authoring/grounding data — it only writes the report files you name.
  * Deterministic and stdlib-only (difflib, json, re) so it runs offline in CI.
  * It surfaces *candidates for manual review*. It does not decide anything,
    does not rank a change as important, and never invents a requirement.

Compare same-pipeline extractions only. A diff between a 배포용-HWP extraction
and a PDF/OCR extraction measures the change of extraction method, not a change
of content; the tool flags that case as ``extraction_mismatch_suspected``.

Usage:
    python3 scripts/diff_manual_paragraph_editions.py \
        --old docs/source-manuals/2026-07-31/extracted/full_text/visa_manual_260731.txt \
        --new docs/source-manuals/2026-09-01/extracted/full_text/visa_manual_260901.txt \
        --role visa --old-label 260731 --new-label 260901 \
        --out-md build/manual-diff/visa.md --out-json build/manual-diff/visa.json
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 체류자격 codes: A-1 … H-2, optional sub-code (D-2-1) and letter variants
# (F-2-7S, D-10-T). Anchored on word boundaries so "2026-09-01" never matches.
CODE_RE = re.compile(r"\b([A-H]-\d{1,2}(?:-\d{1,2}[A-Z]?|-[A-Z])?)\b")
PARENT_RE = re.compile(r"^([A-H]-\d{1,2})")

# A heading that names a status code is what we anchor a change to, e.g.
# "유학(D-2)", "특정활동(E-7)", "3. 일반상용(C-3-4)". Kept deliberately loose:
# an over-broad anchor only makes the report more verbose, never wrong.
HEADING_RE = re.compile(r"^[\s0-9.·\-‣※]*[가-힣][가-힣\s·․,()]{0,40}\(\s*[A-H]-\d{1,2}")

# Extraction-method mismatch heuristic: a same-pipeline pair of consecutive
# editions changes a few percent of its lines. A wholesale difference means the
# two files were produced by different extractors.
MISMATCH_CHANGED_RATIO = 0.35


def normalize(line: str) -> str:
    """Collapse whitespace so re-flowed spacing is not reported as a change."""
    return re.sub(r"\s+", " ", line).strip()


@dataclass
class Paragraph:
    index: int          # 0-based position in the source file
    text: str           # normalized text
    anchor: str         # nearest preceding code-bearing heading ("" if none)
    anchor_index: int   # line number (1-based) of that heading, 0 if none


@dataclass
class Hunk:
    kind: str                     # "changed" | "added" | "removed"
    old_start: Optional[int]      # 1-based line number in the old file
    new_start: Optional[int]      # 1-based line number in the new file
    anchor: str
    old_lines: List[str] = field(default_factory=list)
    new_lines: List[str] = field(default_factory=list)

    @property
    def codes(self) -> List[str]:
        blob = " ".join([self.anchor] + self.old_lines + self.new_lines)
        return sorted(set(CODE_RE.findall(blob)))


def load(path: Path) -> List[Paragraph]:
    """Read a paragraph extraction, tagging each line with its heading anchor."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    out: List[Paragraph] = []
    anchor, anchor_index = "", 0
    for i, line in enumerate(raw.splitlines()):
        text = normalize(line)
        if not text:
            continue
        if HEADING_RE.match(line) and CODE_RE.search(text):
            anchor, anchor_index = text[:120], i + 1
        out.append(Paragraph(index=i + 1, text=text, anchor=anchor,
                             anchor_index=anchor_index))
    return out


def diff(old: List[Paragraph], new: List[Paragraph]) -> List[Hunk]:
    matcher = difflib.SequenceMatcher(
        None, [p.text for p in old], [p.text for p in new], autojunk=False)
    hunks: List[Hunk] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        kind = {"replace": "changed", "delete": "removed", "insert": "added"}[tag]
        # Anchor to the new file where there is one, else the old file.
        if j1 < len(new):
            anchor = new[j1].anchor
        elif i1 < len(old):
            anchor = old[i1].anchor
        else:
            anchor = ""
        hunks.append(Hunk(
            kind=kind,
            old_start=old[i1].index if i1 < i2 and i1 < len(old) else None,
            new_start=new[j1].index if j1 < j2 and j1 < len(new) else None,
            anchor=anchor,
            old_lines=[p.text for p in old[i1:i2]],
            new_lines=[p.text for p in new[j1:j2]],
        ))
    return hunks


def by_code(hunks: List[Hunk]) -> Dict[str, dict]:
    """Group changes by parent status code, keeping the sub-codes seen."""
    slots: Dict[str, dict] = {}
    for h in hunks:
        for code in h.codes:
            parent_m = PARENT_RE.match(code)
            parent = parent_m.group(1) if parent_m else code
            slot = slots.setdefault(
                parent, {"parent": parent, "codes": set(), "hunks": 0,
                         "added": 0, "removed": 0, "changed": 0})
            slot["codes"].add(code)
            slot["hunks"] += 1
            slot[h.kind] += 1
    for slot in slots.values():
        slot["codes"] = sorted(slot["codes"])
    return dict(sorted(slots.items()))


def render_md(hunks: List[Hunk], grouped: Dict[str, dict], meta: dict,
              max_hunks: int, max_lines: int) -> str:
    L: List[str] = []
    L.append(f"# 매뉴얼 개정 대조 — {meta['role']} {meta['old_label']} → {meta['new_label']}")
    L.append("")
    L.append("> 검토용 산출물입니다. 이 파일은 어떤 판단도 내리지 않으며, "
             "확정된 법령 해석이 아닙니다. 아래 코드는 **재검토 후보**이고, "
             "실제 데이터 반영 여부는 사람이 원문과 대조한 뒤 결정합니다.")
    L.append("")
    L.append("| 항목 | 값 |")
    L.append("| --- | --- |")
    L.append(f"| 이전 판 | `{meta['old_path']}` ({meta['old_paragraphs']:,} 문단) |")
    L.append(f"| 신규 판 | `{meta['new_path']}` ({meta['new_paragraphs']:,} 문단) |")
    L.append(f"| 변경 구간 | {meta['hunks']:,} |")
    L.append(f"| 추가 / 삭제 / 수정 문단 | {meta['added_lines']:,} / "
             f"{meta['removed_lines']:,} / {meta['changed_hunks']:,} |")
    L.append(f"| 변경 문단 비율 | {meta['changed_ratio']:.2%} |")
    L.append(f"| 추출 방식 불일치 의심 | {'예 — 대조 무효' if meta['extraction_mismatch_suspected'] else '아니오'} |")
    L.append("")

    if meta["extraction_mismatch_suspected"]:
        L.append("> **경고:** 변경 비율이 임계값을 넘었습니다. 두 파일이 서로 다른 "
                 "추출 방식으로 만들어졌을 가능성이 높으며, 그 경우 이 대조표는 "
                 "내용 변화가 아니라 추출 방식 차이를 보여줍니다. 동일 파이프라인 "
                 "추출본끼리 다시 대조하십시오.")
        L.append("")

    L.append("## 재검토가 필요한 체류자격")
    L.append("")
    if not grouped:
        L.append("변경 구간에서 체류자격 코드가 검출되지 않았습니다.")
    else:
        L.append("| 상위코드 | 검출된 세부코드 | 변경 구간 | 추가 | 삭제 | 수정 |")
        L.append("| --- | --- | ---: | ---: | ---: | ---: |")
        for parent, s in grouped.items():
            L.append(f"| **{parent}** | {', '.join(s['codes'])} | {s['hunks']} | "
                     f"{s['added']} | {s['removed']} | {s['changed']} |")
    L.append("")

    L.append("## 변경 구간 상세")
    L.append("")
    shown = hunks[:max_hunks]
    for n, h in enumerate(shown, 1):
        loc = []
        if h.old_start:
            loc.append(f"이전 L{h.old_start}")
        if h.new_start:
            loc.append(f"신규 L{h.new_start}")
        L.append(f"### {n}. [{h.kind}] {' / '.join(loc)}")
        if h.anchor:
            L.append(f"*구간:* `{h.anchor}`")
        if h.codes:
            L.append(f"*검출 코드:* {', '.join(h.codes)}")
        L.append("")
        L.append("```diff")
        for line in h.old_lines[:max_lines]:
            L.append(f"- {line}")
        if len(h.old_lines) > max_lines:
            L.append(f"- … (+{len(h.old_lines) - max_lines} 줄 생략)")
        for line in h.new_lines[:max_lines]:
            L.append(f"+ {line}")
        if len(h.new_lines) > max_lines:
            L.append(f"+ … (+{len(h.new_lines) - max_lines} 줄 생략)")
        L.append("```")
        L.append("")
    if len(hunks) > len(shown):
        L.append(f"… 변경 구간 {len(hunks) - len(shown)}건이 더 있습니다 "
                 f"(`--max-hunks` 로 조정). 전체는 JSON 리포트를 참조하십시오.")
        L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--old", required=True, type=Path)
    ap.add_argument("--new", required=True, type=Path)
    ap.add_argument("--role", choices=["visa", "stay"], required=True)
    ap.add_argument("--old-label", default="old")
    ap.add_argument("--new-label", default="new")
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--max-hunks", type=int, default=200,
                    help="max change hunks rendered in the Markdown report")
    ap.add_argument("--max-lines", type=int, default=25,
                    help="max lines shown per side of a hunk")
    args = ap.parse_args()

    old = load(args.old)
    new = load(args.new)
    hunks = diff(old, new)
    grouped = by_code(hunks)

    added = sum(len(h.new_lines) for h in hunks if h.kind == "added")
    removed = sum(len(h.old_lines) for h in hunks if h.kind == "removed")
    changed = sum(1 for h in hunks if h.kind == "changed")
    touched = sum(len(h.old_lines) + len(h.new_lines) for h in hunks)
    denom = len(old) + len(new)
    ratio = (touched / denom) if denom else 0.0

    meta = {
        "role": args.role,
        "old_label": args.old_label,
        "new_label": args.new_label,
        "old_path": str(args.old),
        "new_path": str(args.new),
        "old_paragraphs": len(old),
        "new_paragraphs": len(new),
        "hunks": len(hunks),
        "added_lines": added,
        "removed_lines": removed,
        "changed_hunks": changed,
        "changed_ratio": ratio,
        "extraction_mismatch_suspected": ratio > MISMATCH_CHANGED_RATIO,
        "review_status": "candidates_for_human_review",
    }

    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(
            render_md(hunks, grouped, meta, args.max_hunks, args.max_lines),
            encoding="utf-8")
        print(f"wrote {args.out_md}")
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": meta,
            "affected_status_codes": list(grouped.values()),
            "hunks": [
                {"kind": h.kind, "old_start": h.old_start, "new_start": h.new_start,
                 "anchor": h.anchor, "codes": h.codes,
                 "old_lines": h.old_lines, "new_lines": h.new_lines}
                for h in hunks
            ],
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {args.out_json}")

    print(f"{args.role}: {len(hunks)} hunks, {len(grouped)} parent codes touched, "
          f"changed_ratio={ratio:.2%}"
          + (" [EXTRACTION MISMATCH SUSPECTED]"
             if meta["extraction_mismatch_suspected"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
