#!/usr/bin/env python3
"""Populate the re-entry permit (재입국허가) procedure document lists in
visa_data.json from each status's own 재입국허가 block in the official
2026-05 stay manual.

User-visible motivation: the index.html document tabs render
``procedures.reentry.requiredDocs``; when empty, users see the
"structured document checklist … not verified yet" fallback. Almost every
long-stay status section in the stay manual carries a uniform, parent-level
재입국허가 block:

  ❍ 재입국허가 면제 제도 — 등록 외국인이 출국일부터 1년 이내 재입국 시 면제 …
  2. 복수재입국허가 (사우디·이란·리비아 제한 …)
     - 신청서류 : 신청서(별지 34호서식), 여권 원본, 외국인등록증, 수수료

This script reads the literal ``신청서류 :`` / ``제출서류 :`` line from each
status's re-entry sub-block (verbatim — nothing invented), records the
exemption rule and the nationality restriction as conditions, cites that
status's printed page (footer re-verified), and writes a structured
``procedures.reentry`` record.

Robust parsing notes:
  - The re-entry sub-block is bounded by the *registration section heading*
    ``외국인등록\\n`` (a heading on its own line) — NOT the substring
    "외국인등록", because the document item "외국인등록증" contains that
    substring and would otherwise truncate the list.
  - The document line may wrap across printed lines and its items contain
    balanced parentheses (e.g. "신청서(별지 34호서식)"). Parsing normalizes
    whitespace, splits on commas, stops at the fee item (every re-entry list
    ends with a 수수료 item), and strips a single unbalanced trailing ")"
    (H-1's parenthetical "(제출서류 : … 수수료)").

Safety:
  - Only populates statuses whose own re-entry sub-block contains the explicit
    doc line (verbatim list). No cross-status extrapolation.
  - Never overwrites a reentry procedure that already carries documents.
  - Keeps needsManualReview=true (auto-extracted, not hand-certified).
  - Conditions preserved as notes/conditionalDocs, not flattened.
  - Idempotent: re-running makes no further change.

Usage:
    pip install pymupdf
    python3 scripts/populate_reentry_procedure_docs_2026_05.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_VISA_DATA = os.path.join(_REPO, "visa_data.json")
_STAY_PDF = os.path.join(
    _REPO, "docs", "source-manuals", "2026-05", "stay_manual_2026_05.pdf"
)

# Status section start pages in the 2026-05 stay manual (printed == PDF, 1:1).
_SECTIONS = [
    ("A-1", 14), ("A-2", 18), ("A-3", 21), ("B-1", 24), ("B-2", 25),
    ("C-1", 26), ("C-3", 27), ("C-4", 29), ("D-1", 32), ("D-2", 35),
    ("D-3", 56), ("D-4", 74), ("D-5", 102), ("D-6", 105), ("D-7", 108),
    ("D-8", 115), ("D-9", 130), ("D-10", 142), ("E-1", 166), ("E-2", 173),
    ("E-3", 185), ("E-4", 195), ("E-5", 200), ("E-6", 205), ("E-7", 212),
    ("E-8", 324), ("E-9", 326), ("E-10", 336), ("F-1", 341), ("F-2", 360),
    ("F-5", 382), ("F-3", 421), ("G-1", 498), ("H-1", 514), ("F-4", 548),
]

# Document line, capturing a generous run (may wrap across printed lines).
_APPLY_RE = re.compile(r"(?:신청서류|제출서류)\s*[:：]\s*(.{1,160})", re.S)
# Registration section heading on its own line (NOT the inline "외국인등록증").
_REG_HEAD_RE = re.compile(r"외국인등록\s*\n")
_FOOTER_RE = re.compile(r"-\s*(\d+)\s*-")

_EXEMPTION_NOTE = (
    "재입국허가 면제 제도: 외국인등록을 마친 외국인이 출국한 날부터 1년 이내에 "
    "재입국하려는 경우 재입국허가가 면제됩니다(체류기간이 1년보다 적게 남은 경우 "
    "남은 체류기간 범위 내 면제). 다만 입국규제 등 대상자는 체류지 관할 "
    "출입국·외국인관서에서 재입국허가를 받아야 합니다."
)


def _section_ranges():
    ss = sorted(_SECTIONS, key=lambda x: x[1])
    out = {}
    for i, (c, p) in enumerate(ss):
        end = ss[i + 1][1] - 1 if i + 1 < len(ss) else 560
        out[c] = (p, end)
    return out


def _reentry_state(rec):
    pr = (rec.get("procedures") or {}).get("reentry")
    if not isinstance(pr, dict):
        return "missing"
    rd = pr.get("requiredDocs")
    if isinstance(rd, dict):
        ne = any((rd.get(g) or []) for g in
                 ("commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs"))
    else:
        ne = bool(rd)
    return "full" if ne else ("avail_empty" if pr.get("available") else "unavail")


def _split_docs(raw: str):
    """Parse the re-entry document line into verbatim items.

    Handles line wraps, balanced parens inside items, and a trailing
    unbalanced ")" from a parenthetical line. Stops at the fee (수수료) item,
    which always terminates the re-entry document list.
    """
    s = re.sub(r"\s+", " ", raw.replace("\n", " ")).strip()
    docs = []
    for part in re.split(r"[,，]", s):
        item = part.strip(" .·-")
        if item.count("(") < item.count(")") and item.endswith(")"):
            item = item[:-1].strip()
        if not item:
            continue
        if "수수료" in item:
            # The fee item ends the list. The capture runs past 수수료 into the
            # following section (no comma separator), so truncate to the fee
            # token itself (keeping an attached "없음" / "면제" qualifier only).
            m = re.match(r".*?수수료(?:\s*없음|\s*면제)?", item)
            docs.append((m.group(0) if m else item).strip())
            break
        docs.append(item)
    return docs


def build():
    import fitz  # type: ignore

    doc = fitz.open(_STAY_PDF)
    ranges = _section_ranges()
    found = {}
    for code, (s, e) in ranges.items():
        for pi in range(s - 1, min(e, doc.page_count)):
            t = doc[pi].get_text()
            idx = t.find("재입국허가")
            if idx < 0:
                continue
            window = t[idx: idx + 1200]
            if "재입국허가 면제" not in window:
                continue
            # Position of the registration section heading within the window;
            # the re-entry doc line must appear before it.
            rh = _REG_HEAD_RE.search(window)
            reg_pos = rh.start() if rh else len(window)
            m = _APPLY_RE.search(window)
            if not m or m.start() >= reg_pos:
                continue
            docs = _split_docs(m.group(1))
            # A valid re-entry list has the application form + fee item.
            if len(docs) < 2 or not any("수수료" in d for d in docs):
                continue
            page = pi + 1
            foot = _FOOTER_RE.findall(t[:30])
            if not (foot and int(foot[0]) == page):
                continue
            has_nat = bool(re.search(r"사우디|이란|리비아", window[:reg_pos]))
            found[code] = {
                "page": page,
                "docs": docs,
                "applyLine": re.sub(r"\s+", " ", m.group(1)).strip(),
                "hasNat": has_nat,
            }
            break
    return found


def make_proc(info):
    conditional = []
    if info["hasNat"]:
        conditional.append(
            "사우디아라비아·이란·리비아 국적자는 복수재입국허가가 제한됩니다"
            "(단, 결혼이민(F-6)·유학(D-2)·일반연수(D-4) 국민은 가능)."
        )
    return {
        "available": True,
        "summary": "재입국허가 면제 제도 및 복수재입국허가(1년 초과 2년 이내 재입국) 안내.",
        "requiredDocs": {
            "commonDocs": [],
            "requiredDocs": info["docs"],
            "additionalDocs": [],
            "conditionalDocs": conditional,
        },
        "notes": [
            _EXEMPTION_NOTE,
            "복수재입국허가는 출국 후 체류기간 범위 내에서 1년을 초과하여 2년 이내에 "
            "재입국하려는 경우에 신청합니다.",
            "2026.5 체류민원 안내매뉴얼의 해당 체류자격 재입국허가 항목에서 추출한 "
            "신청서류입니다. 체류이력·국적별 예외가 있어 신청 전 확인이 필요합니다.",
        ],
        "manualRefs": [
            {
                "manualName": "체류민원",
                "manualVersion": "2026.5",
                "pageRange": f"p. {info['page']}",
                "confidence": "manual_extracted_needs_review",
                "needsManualReview": True,
            }
        ],
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    try:
        import fitz  # noqa: F401
    except ImportError:
        print("ERROR: PyMuPDF required (pip install pymupdf).", file=sys.stderr)
        return 2

    found = build()
    with open(_VISA_DATA, encoding="utf-8") as fh:
        data = json.load(fh)
    recs = {r["code"]: r for r in data if isinstance(r, dict) and r.get("code")}

    planned, skipped_full, missing_rec = [], [], []
    for code, info in sorted(found.items()):
        rec = recs.get(code)
        if rec is None:
            missing_rec.append(code)
            continue
        if _reentry_state(rec) == "full":
            skipped_full.append(code)
            continue
        planned.append((code, info["page"], len(info["docs"])))
        if not args.dry_run:
            rec.setdefault("procedures", {})["reentry"] = make_proc(info)

    report = {
        "manualBlocksFound": sorted(found),
        "planned": planned,
        "skippedAlreadyFull": skipped_full,
        "recordMissing": missing_rec,
        "plannedCount": len(planned),
        "docsByCode": {c: found[c]["docs"] for c in found},
    }
    with open("/tmp/reentry_report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    if not args.dry_run and planned:
        out = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        with open(_VISA_DATA, "w", encoding="utf-8") as fh:
            fh.write(out)

    print(f"re-entry blocks with a document line: {len(found)}")
    print(f"planned populations: {len(planned)}")
    print(f"skipped (already full): {len(skipped_full)}")
    print(f"record missing: {missing_rec}")
    print(f"mode: {'DRY-RUN' if args.dry_run else 'WROTE visa_data.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
