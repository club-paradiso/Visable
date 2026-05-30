#!/usr/bin/env python3
"""Extract candidate KSCO8/KSIC11 full tables for employment reporting.

This script expects pdftotext output generated from the official/user-provided
classification PDFs:

  pdftotext -layout KSCO8.pdf /tmp/ksco8.txt
  pdftotext -layout KSIC11.pdf /tmp/ksic11.txt

It writes candidate CSV files. The generated files are not automatically enabled
for production runtime. Review counts and spot-check rows before wiring them into
frontend search.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

HANGUL_RE = re.compile(r"[가-힣]")
CODE_KSCO_RE = re.compile(r"^\s*(?P<code>(?:\d{1,5}|A\d{0,4}))(?=\s|$)(?P<rest>.*)$")
CODE_KSIC_RE = re.compile(r"^\s*(?P<code>(?:[A-U]|\d{2,5}))(?=\s|$)(?P<rest>.*)$")
SKIP_WORDS = [
    "분류항목표",
    "Numerical List",
    "한국표준",
    "Titles",
    "Descriptions",
    "목 차",
    "총 설",
    "┃",
    "Published",
    "Publisher",
    "ISBN",
    "통계분류포털",
    "문의하시기",
]
GENERIC_SUFFIXES = {"임원", "관련직", "종사원", "관리자", "전문가", "조작원", "조작직", "종사자", "기능직", "정비원", "도매업", "소매업"}


def level_ksco(code: str) -> str:
    if code == "A" or (code.isdigit() and len(code) == 1):
        return "major"
    if code.startswith("A"):
        return {2: "middle", 3: "minor", 4: "unit", 5: "detailed_unit"}.get(len(code), "unknown")
    return {2: "middle", 3: "minor", 4: "unit", 5: "detailed_unit"}.get(len(code), "unknown")


def level_ksic(code: str) -> str:
    if len(code) == 1 and code.isalpha():
        return "major"
    return {2: "middle", 3: "minor", 4: "unit", 5: "detailed_unit"}.get(len(code), "unknown")


def is_skip(line: str) -> bool:
    if not line.strip():
        return True
    return any(word in line for word in SKIP_WORDS)


def title_left(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    left = re.split(r"\s{2,}", text)[0].strip()
    if not HANGUL_RE.search(left):
        return ""
    left = re.sub(r"\s+[A-Za-z][A-Za-z ,:&/()\-.]+$", "", left).strip()
    return left


def parse_table(path: Path, kind: str) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if kind == "ksco":
        start = next(i for i, line in enumerate(lines) if "Numerical List of Titles" in line)
        end = next(i for i, line in enumerate(lines[start + 1 :], start + 1) if re.match(r".*Ⅲ\s*분류", line))
        code_re = CODE_KSCO_RE
        level_fn = level_ksco
    else:
        start = next(i for i, line in enumerate(lines) if "Ⅱ 분 류 항 목 표" in line or "Ⅱ 분류 항목표" in line)
        end = next(i for i, line in enumerate(lines[start + 1 :], start + 1) if re.match(r".*Ⅲ\s*분류", line))
        code_re = CODE_KSIC_RE
        level_fn = level_ksic

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    i = start

    def prev_title_part(idx: int) -> str:
        k = idx - 1
        while k >= start and k >= idx - 3:
            prev = lines[k]
            if code_re.match(prev):
                break
            if "\x0c" in prev or is_skip(prev):
                k -= 1
                continue
            part = title_left(prev)
            if part:
                return part
            k -= 1
        return ""

    def next_title_parts(idx: int, limit: int = 3) -> list[str]:
        parts: list[str] = []
        k = idx + 1
        while k < end and k <= idx + limit:
            nxt = lines[k]
            if code_re.match(nxt):
                break
            if "\x0c" in nxt or is_skip(nxt):
                k += 1
                continue
            part = title_left(nxt)
            if part:
                parts.append(part)
            k += 1
        return parts

    while i < end:
        line = lines[i]
        match = code_re.match(line)
        if not match or is_skip(line):
            i += 1
            continue
        code = match.group("code")
        title = title_left(match.group("rest"))

        if not title or title in GENERIC_SUFFIXES:
            nxts = next_title_parts(i)
            prev = prev_title_part(i)
            if not title and not nxts:
                i += 1
                continue
            pieces: list[str] = []
            if prev and nxts:
                pieces.append(prev)
            if title:
                pieces.append(title)
            for nxt in nxts:
                if nxt not in pieces:
                    pieces.append(nxt)
            if pieces:
                title = " ".join(pieces).strip()

        # append short Korean continuation fragments
        k = i + 1
        while k < end and k <= i + 3:
            nxt = lines[k]
            if code_re.match(nxt):
                break
            if "\x0c" in nxt or is_skip(nxt):
                k += 1
                continue
            part = title_left(nxt)
            if part and part not in title and not re.search(r"[A-Za-z]{3,}", part):
                title = f"{title} {part}".strip()
                k += 1
                continue
            break

        title = re.sub(r"\s+", " ", title).strip()
        if title and HANGUL_RE.search(title) and code not in seen:
            seen.add(code)
            rows.append({"code": code, "title_ko": title, "level": level_fn(code), "parent_code": ""})
        i += 1

    order = {"major": 1, "middle": 2, "minor": 3, "unit": 4, "detailed_unit": 5}
    stack: dict[int, str] = {}
    for row in rows:
        level = order.get(row["level"], 0)
        row["parent_code"] = stack.get(level - 1, "") if level > 1 else ""
        stack[level] = row["code"]
        for deeper in list(stack):
            if deeper > level:
                stack.pop(deeper, None)
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=["code", "title_ko", "level", "parent_code"])
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict[str, str]], label: str) -> None:
    """Write rows as a JSON list consumable by scripts/fetch_jobcodes.py."""
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = dict(Counter(r["level"] for r in rows))
    payload = {
        "classification": label,
        "row_count": len(rows),
        "counts_by_level": counts,
        "data": rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract KSCO8/KSIC11 full classification tables from pdftotext output.\n"
            "\n"
            "Generate input text files first:\n"
            "  pdftotext -layout KSCO8.pdf /tmp/ksco8.txt\n"
            "  pdftotext -layout KSIC11.pdf /tmp/ksic11.txt\n"
            "\n"
            "Output (in --out-dir):\n"
            "  employment_reporting_ksco8_full_candidate.csv\n"
            "  employment_reporting_ksco8_full_candidate.json\n"
            "  employment_reporting_ksic11_full_candidate.csv\n"
            "  employment_reporting_ksic11_full_candidate.json\n"
            "\n"
            "The JSON files are the preferred input for fetch_jobcodes.py --full.\n"
            "NOT for E-7 eligibility screening; for HiKorea 취업정보 신고 only."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ksco-text", type=Path, required=True, help="pdftotext output of KSCO8 PDF")
    parser.add_argument("--ksic-text", type=Path, required=True, help="pdftotext output of KSIC11 PDF")
    parser.add_argument("--out-dir", type=Path, default=Path("data/generated"))
    args = parser.parse_args()

    ksco = parse_table(args.ksco_text, "ksco")
    ksic = parse_table(args.ksic_text, "ksic")

    write_csv(args.out_dir / "employment_reporting_ksco8_full_candidate.csv", ksco)
    write_json(args.out_dir / "employment_reporting_ksco8_full_candidate.json", ksco, "KSCO8")
    write_csv(args.out_dir / "employment_reporting_ksic11_full_candidate.csv", ksic)
    write_json(args.out_dir / "employment_reporting_ksic11_full_candidate.json", ksic, "KSIC11")

    print("KSCO8 ", len(ksco), dict(Counter(row["level"] for row in ksco)))
    print("KSIC11", len(ksic), dict(Counter(row["level"] for row in ksic)))
    print(f"Wrote CSV and JSON to {args.out_dir}/")
    print("Next: python3 scripts/fetch_jobcodes.py  (auto-detects full candidates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
