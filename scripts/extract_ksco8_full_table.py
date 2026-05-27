#!/usr/bin/env python3
"""Extract the KSCO8 numerical occupation table from pdftotext output.

Input:
    pdftotext -layout "(해설서) 제8차 한국표준직업분류(공개용)_24.6.24_(최종안).pdf" ksco8.txt

Output:
    data/jobcode_master_ksco8_full.csv

The parser is deliberately count-gated. It must extract the official KSCO8
classification counts before it writes the output:

- 10 major groups
- 57 middle groups
- 167 minor groups
- 495 unit groups
- 1,270 detailed unit groups

This script does not fetch remote data. It transforms an officially downloaded
source PDF that has already been converted to text.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_COUNTS = {
    "major": 10,
    "middle": 57,
    "minor": 167,
    "unit": 495,
    "detail": 1270,
}

CODE_RE = re.compile(r"^(?P<pre>\s*)(?P<code>(?:[1-9]\d{0,4}|A\d{0,4}))(?P<after>\s+.*|\s*)$")


def _is_code_line(lines: list[str], idx: int) -> bool:
    return CODE_RE.match(lines[idx]) is not None


def _clean_korean_segment(segment: str) -> str:
    text = segment.strip()
    if not text or "한국표준직업분류" in text or "분류 항목표" in text:
        return ""
    text = re.sub(r"\s+[A-Z][A-Za-z0-9 ,.&()/;\-:\[\]ʼ’]*$", "", text).strip()
    text = re.sub(r"\s+[a-z][A-Za-z0-9 ,.&()/;\-:\[\]ʼ’]+$", "", text).strip()
    if not re.search(r"[가-힣]", text):
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _current_line_title(lines: list[str], idx: int, code: str) -> str:
    line = lines[idx]
    match = CODE_RE.match(line)
    if not match:
        return ""
    segment = line[match.end("code"):41]
    if not segment.strip():
        segment = line[match.end("code"):]
    return _clean_korean_segment(segment)


def _continuation_title(line: str) -> str:
    return _clean_korean_segment(line[:41])


def _extract_title(lines: list[str], idx: int, code: str, start: int, end: int) -> str:
    current = _current_line_title(lines, idx, code)
    parts: list[str] = []
    if current:
        parts.append(current)
        if current.endswith(("및", "관련", "장치", "기계")):
            next_idx = idx + 1
            if next_idx < end and not _is_code_line(lines, next_idx) and lines[next_idx].strip():
                next_part = _continuation_title(lines[next_idx])
                if next_part:
                    parts.append(next_part)
    else:
        prev_idx = idx - 1
        if prev_idx >= start and not _is_code_line(lines, prev_idx):
            prev_part = _continuation_title(lines[prev_idx])
            if prev_part:
                parts.append(prev_part)
        next_idx = idx + 1
        if next_idx < end and not _is_code_line(lines, next_idx):
            next_part = _continuation_title(lines[next_idx])
            if next_part:
                parts.append(next_part)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _sort_code(code: str) -> tuple[str, str]:
    return (code[0].replace("A", "99"), code)


def _level_for_code(code: str) -> str:
    length = len(code)
    if length == 1:
        return "major"
    if length == 2:
        return "middle"
    if length == 3:
        return "minor"
    if length == 4:
        return "unit"
    if length == 5:
        return "detail"
    raise ValueError(f"unsupported code length for {code}")


def _parent_for_code(code: str) -> str:
    level = _level_for_code(code)
    if level == "major":
        return ""
    return code[:-1]


def parse_ksco8_text(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    start = None
    end = None
    for idx, line in enumerate(lines):
        if start is None and "Numerical List of Titles" in line:
            start = idx
        if start is not None and idx > start and "Ⅲ 분류 항목명 및 내용 설명" in line:
            end = idx
            break
    if start is None or end is None:
        raise ValueError("Could not locate KSCO8 numerical-list boundaries")

    positions_by_code: dict[str, list[int]] = defaultdict(list)
    for idx in range(start, end):
        match = CODE_RE.match(lines[idx])
        if match:
            positions_by_code[match.group("code")].append(idx)

    detail_codes = sorted(
        [code for code in positions_by_code if len(code) == 5],
        key=_sort_code,
    )
    code_sets = {
        "major": sorted({code[:1] for code in detail_codes}, key=_sort_code),
        "middle": sorted({code[:2] for code in detail_codes}, key=_sort_code),
        "minor": sorted({code[:3] for code in detail_codes}, key=_sort_code),
        "unit": sorted({code[:4] for code in detail_codes}, key=_sort_code),
        "detail": detail_codes,
    }

    records: list[dict[str, str]] = []
    for level in ["major", "middle", "minor", "unit", "detail"]:
        for code in code_sets[level]:
            idx = positions_by_code[code][0]
            title = _extract_title(lines, idx, code, start, end)
            if not title:
                raise ValueError(f"empty title for {code}")
            records.append(
                {
                    "code": code,
                    "title_ko": title,
                    "level": level,
                    "parent_code": _parent_for_code(code),
                }
            )

    counts = Counter(record["level"] for record in records)
    if dict(counts) != EXPECTED_COUNTS:
        raise ValueError(f"unexpected KSCO8 counts: {dict(counts)}")
    return records


def write_csv(records: list[dict[str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["code", "title_ko", "level", "parent_code"])
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_txt", type=Path, help="pdftotext -layout output from the KSCO8 source PDF")
    parser.add_argument("--out", type=Path, default=Path("data/jobcode_master_ksco8_full.csv"))
    parser.add_argument("--check", action="store_true", help="parse and print counts without writing CSV")
    args = parser.parse_args()

    records = parse_ksco8_text(args.input_txt.read_text(encoding="utf-8"))
    counts = Counter(record["level"] for record in records)
    print(dict(counts))
    if not args.check:
        write_csv(records, args.out)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
