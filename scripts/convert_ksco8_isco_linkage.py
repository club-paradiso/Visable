#!/usr/bin/env python3
"""Extract the KSCO8 occupation table from the official KSCO8↔ISCO08 linkage Excel.

Input  : data/sources/ksco8_isco08_linkage_2026.xlsx
         (통계청/국가데이터처 "한국표준직업분류와 국제표준직업분류의 연계표")
Output : data/generated/employment_reporting_ksco8_candidate.csv
         columns: code,title_ko,level,parent_code,name_en

What this gives us:
  대분류 10 · 중분류 57 · 소분류 167 · 세분류 494  = 728 rows  (제8차 KSCO8)
  + English names at 세분류(unit) level (from the ISCO linkage's 세분류 영문명).

What it does NOT give:
  세세분류 (5-digit, 1,270 items). An ISCO linkage has no 5-digit level, so the
  full 1,999-row table still needs the KSCO-only 분류항목표 (kssc 통계분류포털).

The 세분류 count is 494 (not the sometimes-cited 495): both linkage sheets
(3-1 KSCO→ISCO and 4-1 세분류 KSCO↔ISCO) agree on 494 distinct KSCO unit codes;
the difference is one KSCO-only unit absent from any ISCO linkage. We do NOT
fabricate it. The "제외" note in the sheet lists ISCO-side items (no KSCO match).

Stdlib only (xlsx = zip of XML). NOT E-7 eligibility; HiKorea 취업정보 신고 only.
"""
from __future__ import annotations

import csv
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "data" / "sources" / "ksco8_isco08_linkage_2026.xlsx"
OUT = REPO / "data" / "generated" / "employment_reporting_ksco8_candidate.csv"

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
EXPECT = {"major": 10, "middle": 57, "minor": 167}  # complete levels; unit is 494 (linkage)

# Normalize the several middle-dot glyphs the source mixes to the canonical · (U+00B7)
# used elsewhere in the dataset. Pure glyph normalization — no content change.
DOTS = {"‧": "·", "∙": "·", "·": "·"}


def norm(s: str) -> str:
    s = (s or "").strip()
    for a, b in DOTS.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s)


def col_idx(ref: str) -> int:
    letters = re.match(r"([A-Z]+)", ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def load(z: zipfile.ZipFile):
    shared = ["".join(t.text or "" for t in si.iter(M + "t"))
              for si in ET.fromstring(z.read("xl/sharedStrings.xml"))]
    rels = {r.get("Id"): r.get("Target")
            for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    name2file = {}
    for s in ET.fromstring(z.read("xl/workbook.xml")).iter(M + "sheet"):
        tgt = rels.get(s.get(R + "id"), "")
        name2file[s.get("name")] = "xl/" + tgt.lstrip("/") if not tgt.startswith("xl/") else tgt
    return shared, name2file


def read_sheet(z, fn, shared):
    root = ET.fromstring(z.read(fn))
    rows = []
    for row in root.iter(M + "row"):
        cells = {}
        for c in row.findall(M + "c"):
            t, v, isn = c.get("t"), c.find(M + "v"), c.find(M + "is")
            if t == "s" and v is not None:
                val = shared[int(v.text)]
            elif t == "inlineStr" and isn is not None:
                val = "".join(x.text or "" for x in isn.iter(M + "t"))
            elif v is not None:
                val = v.text
            else:
                val = ""
            cells[col_idx(c.get("r"))] = (val or "").strip()
        rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return rows


def level_of(code: str) -> str:
    return {1: "major", 2: "middle", 3: "minor", 4: "unit"}[len(code)]


def main() -> int:
    if not SRC.is_file():
        print(f"ERROR: source not found: {SRC}", file=sys.stderr)
        return 2
    z = zipfile.ZipFile(SRC)
    shared, name2file = load(z)
    sheet = next((f for n, f in name2file.items() if "KSCO(8" in n and "ISCO" in n), None)
    if not sheet:
        print(f"ERROR: KSCO8-ISCO sheet not found in {list(name2file)}", file=sys.stderr)
        return 2
    rows = read_sheet(z, sheet, shared)

    # locate header row ("대분류"/"중분류"/.. labels), data begins after it
    start = next(i for i, r in enumerate(rows)
                 if any(c.strip() == "대분류" for c in r)) + 1
    # columns: 0 maj_code 1 maj_name 2 mid_code 3 mid_name 4 min_code 5 min_name
    #          6 unit_code 7 unit_name 8 unit_en
    out: "OrderedDict[str, dict]" = OrderedDict()
    code_re = re.compile(r"^(?:\d{1,4}|A\d{0,3})$")
    for r in rows[start:]:
        r = (r + [""] * 9)[:9]
        for code, name in [(r[0], r[1]), (r[2], r[3]), (r[4], r[5]), (r[6], r[7])]:
            code = re.sub(r"[*#\s]", "", code)
            if code and code_re.match(code) and code not in out:
                en = norm(r[8]) if (code == re.sub(r"[*#\s]", "", r[6]) and len(code) == 4) else ""
                out[code] = {"code": code, "title_ko": norm(name),
                             "level": level_of(code), "name_en": en}

    counts = {}
    for v in out.values():
        counts[v["level"]] = counts.get(v["level"], 0) + 1
    for lv, exp in EXPECT.items():
        if counts.get(lv) != exp:
            print(f"ERROR: {lv} count {counts.get(lv)} != expected {exp}", file=sys.stderr)
            return 1
    # service-sector 8th-edition signature
    sig = {c: out.get(c, {}).get("title_ko") for c in ("42", "43", "45")}
    if sig != {"42": "돌봄 및 보건 서비스직", "43": "개인 생활 서비스직", "45": "조리 및 음식 서비스직"}:
        print(f"ERROR: 8th-edition service signature mismatch: {sig}", file=sys.stderr)
        return 1
    # parent by code prefix (hierarchical codes); validate no orphans
    rows_out = []
    codeset = set(out)
    for code, rec in out.items():
        parent = "" if len(code) == 1 else code[:-1]
        if parent and parent not in codeset:
            print(f"ERROR: orphan {code} (parent {parent} missing)", file=sys.stderr)
            return 1
        rows_out.append({**rec, "parent_code": parent})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["code", "title_ko", "level", "parent_code", "name_en"],
                           lineterminator="\n")
        w.writeheader()
        for r in rows_out:
            w.writerow({k: r.get(k, "") for k in w.fieldnames})
    print(f"Wrote {OUT}  rows={len(rows_out)}  counts={counts}")
    print("  NOTE: 세세분류(5-digit) absent from ISCO linkage; full 1,999-row table "
          "still needs the KSCO-only 분류항목표.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
