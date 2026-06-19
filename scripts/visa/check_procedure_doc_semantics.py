#!/usr/bin/env python3
"""Guardrail: keep auto-extracted prose out of procedure document chips.

Phase: data-quality regression guard for the 2026-06-17 manual refresh.

The procedure renderer turns every string in a procedure's document arrays
(`commonDocs`/`requiredDocs`/`additionalDocs`/`conditionalDocs`) into a
"submitted document" chip, and renders `summary` as the procedure description.
PDF/manual extraction can concatenate adjacent section headings and rule prose
into those fields (e.g. an extension summary ending in ``재입국허가1`` or a
document array holding ``단기방문(C-3)은 ... 90일 범위 내에서만 연장 가능``).

This check fails when a document chip or summary still contains one of a small
set of *high-confidence* extraction-bleed signatures. It is deliberately
conservative: it only flags structural artifacts (adjacent-heading+list-digit,
embedded section-number headings, raw PDF bullet glyphs, special-track heading
fragments). Real—if long—document names (e.g. ``체류지 입증서류(예: ...)`` or
``신원보증서 원본(아래 직종에 한해 징구) ...``) are left untouched.

Move valid explanatory sentences to `notes` (or `summary`); never invent
documents to fill an empty array.

Usage:
  python3 scripts/visa/check_procedure_doc_semantics.py        # exit 1 on findings
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATUS_DIR = REPO_ROOT / "backend" / "data" / "visa_authoring" / "statuses"
DOC_KEYS = ("commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs")

# High-confidence extraction-bleed signatures. Each must stay at zero hits on
# clean data; they target structure (headings/markers), not document length.
DOC_PATTERNS = {
    "adjacent procedure-heading + list digit (e.g. 재입국허가1)":
        re.compile(r"(재입국허가|외국인등록|근무처|체류자격외\s*활동|활동범위|체류자격\s*부여)\s*\d"),
    "embedded section-number heading (e.g. …확인)2. 협정상…)":
        re.compile(r"[가-힣\)”]\s*\d+\.\s*[가-힣]{2,}"),
    "raw PDF bullet/box artifact (‣ 󰁾 ▸)":
        re.compile(r"[‣󰁾▸]"),
    "trailing section header (…경우 제출서류)":
        re.compile(r"경우\s*제출서류\s*$"),
    "special-track heading fragment (체류특례/사증특례/특례사항 규정)":
        re.compile(r"(체류특례|사증특례|특례사항\s*규정)"),
}
SUMMARY_PATTERNS = {
    "adjacent procedure-heading + list digit in summary (e.g. 재입국허가1)":
        re.compile(r"(재입국허가|외국인등록|근무처|체류자격외\s*활동|체류자격\s*부여)\s*\d"),
    "table-of-contents marker (목차) in summary":
        re.compile(r"목차"),
}


def main() -> int:
    findings = []
    for path in sorted(STATUS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        code = data.get("code", path.stem)
        for proc_key, proc in (data.get("procedures") or {}).items():
            if not isinstance(proc, dict):
                continue
            req = proc.get("requiredDocs") or {}
            for dk in DOC_KEYS:
                for idx, entry in enumerate(req.get(dk) or []):
                    if not isinstance(entry, str) or entry.startswith("doc_"):
                        continue
                    for label, rgx in DOC_PATTERNS.items():
                        if rgx.search(entry):
                            findings.append((code, f"{proc_key}.requiredDocs.{dk}[{idx}]", label, entry))
            summary = proc.get("summary")
            if isinstance(summary, str):
                for label, rgx in SUMMARY_PATTERNS.items():
                    if rgx.search(summary):
                        findings.append((code, f"{proc_key}.summary", label, summary))

    if findings:
        print(f"[procedure-doc-semantics] FAIL — {len(findings)} document/summary field(s) "
              "still contain extraction bleed (move prose to notes/summary; do not invent documents):",
              file=sys.stderr)
        for code, where, label, text in findings:
            snippet = text if len(text) <= 110 else text[:110] + "…"
            print(f"  - {code} {where}: {label}\n      {snippet}", file=sys.stderr)
        return 1

    print("[procedure-doc-semantics] OK — no procedure summary or document chip "
          "contains adjacent-heading/section/marker extraction bleed (42 status files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
