#!/usr/bin/env python3
"""Extract + segment the 「육성형 전문기술인력 제도」 (K-CORE / E-7-M) manual.

Unlike the large HiKorea 사증/체류 안내 매뉴얼 (which ship as 배포용/distribution
HWP whose body is a stub — see docs/hikorea_manual_sync.md), this K-CORE manual
is a **standard, non-distribution** HWP (FileHeader flag 0x1, no 0x4), so the
builtin HWPTAG_PARA_TEXT parser extracts its body fully and deterministically.

This script reproducibly converts the committed source HWP into:
  * a readable full-text .txt
  * a logically segmented sections .json (same record shape the PDF-manual
    section indexes use: source_id / source_file / page / heading / text /
    status_codes_detected / subcodes_detected / domain)
  * a small metadata .json (sha256, char/korean counts, code inventory)

It never edits protected production data (visa_data.json, backend/data/visas.json,
doc_master.json). Output paths are explicit CLI args.

Usage:
  python3 scripts/extract_kcore_manual_260629.py \
      --hwp backend/data/sources/manuals/260629_kcore_manual.hwp \
      --outdir backend/data/sources/manuals
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path

EXT_CONTROLS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}
SOURCE_ID = "kcore_manual_2026_06_29"
DOMAIN = "visa_stay_special_program"  # covers both 사증 and 체류 for the K-CORE pilot

# A-1 … H-2 with optional sub-segment (E-7-1, D-2-1, E-7-M, F-2-7S, …).
CODE_RE = re.compile(r"\b([A-H]-\d{1,2}(?:-[0-9A-Z]{1,3})?)\b")
SUBCODE_RE = re.compile(r"\b([A-H]-\d{1,2}-[0-9A-Z]{1,3})\b")


def para_text(payload: bytes) -> str:
    n = len(payload) // 2
    arr = struct.unpack_from("<%dH" % n, payload, 0)
    out, i = [], 0
    while i < n:
        c = arr[i]
        if c in EXT_CONTROLS:
            i += 8
            continue
        if c in (10, 13):
            out.append("\n")
            i += 1
            continue
        if c < 32:
            i += 1
            continue
        out.append(chr(c))
        i += 1
    return "".join(out)


def extract_full_text(hwp_path: Path) -> str:
    import olefile

    ole = olefile.OleFileIO(str(hwp_path))
    try:
        fh = ole.openstream("FileHeader").read()
        flags = struct.unpack_from("<I", fh, 36)[0]
        if flags & 4:
            raise SystemExit(
                "refusing: this is a 배포용(distribution) HWP (flag 0x4); "
                "body extraction is not reliable — see docs/hikorea_manual_sync.md"
            )
        compressed = bool(flags & 1)
        sects = [
            e for e in ole.listdir()
            if len(e) == 2 and e[0] == "BodyText" and e[1].startswith("Section")
        ]
        sects.sort(key=lambda e: int(re.search(r"(\d+)", e[1]).group(1)))
        paras = []
        for e in sects:
            data = ole.openstream(e).read()
            if compressed:
                try:
                    data = zlib.decompress(data, -15)
                except Exception:
                    continue
            i, n = 0, len(data)
            while i + 4 <= n:
                hdr = struct.unpack_from("<I", data, i)[0]
                i += 4
                tag = hdr & 0x3FF
                size = (hdr >> 20) & 0xFFF
                if size == 0xFFF:
                    size = struct.unpack_from("<I", data, i)[0]
                    i += 4
                if i + size > n:
                    break
                payload = data[i:i + size]
                i += size
                if tag == 67:  # HWPTAG_PARA_TEXT
                    paras.append(para_text(payload))
        return "\n".join(paras)
    finally:
        ole.close()


def clean_text(raw: str) -> str:
    # Collapse runs of spaces/tabs; collapse 3+ blank lines to a single blank.
    txt = re.sub(r"[ \t]{2,}", " ", raw)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip() + "\n"


# Section anchors, in document order. Each entry is (regex, heading label).
# We split the readable text on these heading lines and attach the body that
# follows each anchor up to the next anchor.
SECTION_ANCHORS = [
    (re.compile(r"^Ⅰ\b"), "Ⅰ. 개요 — 목적 및 법적 근거"),
    (re.compile(r"^Ⅱ\b"), "Ⅱ. 육성형 전문기술학과 지정·운영"),
    (re.compile(r"^Ⅲ\b"), "Ⅲ. 체류단계별 특례"),
    (re.compile(r"^\s*1\.\s*\[유학 시\]"), "Ⅲ-1. [유학 시] 육성형 전문기술학과 유학생 (D-2-1)"),
    (re.compile(r"^\s*2\.\s*\[취업 시\]"), "Ⅲ-2. [취업 시] K-CORE 자격 부여 (E-7-M)"),
    (re.compile(r"^Ⅳ\b"), "Ⅳ. 행정 사항"),
    (re.compile(r"^붙임\s*1"), "붙임 1. 2026년 지정 육성형 전문기술학과 목록 (16개)"),
    (re.compile(r"^붙임\s*2"), "붙임 2. 2026년 육성형 전문기술학과 선정 과정"),
    (re.compile(r"^붙임\s*3|^붙임3"), "붙임 3. 주요 질의 응답"),
    (re.compile(r"^서식\s*1"), "서식 1. 육성형 전문기술학과 사업 신청서"),
    (re.compile(r"^서식\s*2"), "서식 2. 광역지방정부 추천서"),
    (re.compile(r"^서식\s*3"), "서식 3. 서약서"),
    (re.compile(r"^서식\s*4"), "서식 4. 육성형 전문기술학과 지정증"),
]


def segment(readable: str, source_file: str) -> list[dict]:
    lines = readable.splitlines()
    # Find the first content anchor (skip cover + 목차).
    anchor_hits = []  # (line_index, heading)
    for idx, line in enumerate(lines):
        for rx, label in SECTION_ANCHORS:
            if rx.match(line.strip()):
                # Skip the 목차 (table of contents) occurrences: those lines end
                # with a trailing page number and appear before the first "Ⅰ"
                # body anchor. We detect the body copy as the *last* run.
                anchor_hits.append((idx, label))
                break
    # Keep only the final occurrence of each label (body copy, not 목차).
    last_by_label: dict[str, int] = {}
    for idx, label in anchor_hits:
        last_by_label[label] = idx
    ordered = sorted(((idx, label) for label, idx in last_by_label.items()))

    sections = []
    for i, (start, label) in enumerate(ordered):
        end = ordered[i + 1][0] if i + 1 < len(ordered) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        codes = sorted(set(CODE_RE.findall(body)))
        subcodes = sorted(set(SUBCODE_RE.findall(body)))
        sections.append({
            "source_id": SOURCE_ID,
            "source_file": source_file,
            "page": str(i + 1),          # logical section index (HWP has no page map)
            "section_no": i + 1,
            "heading": label,
            "text": body,
            "status_codes_detected": json.dumps(codes, ensure_ascii=False),
            "subcodes_detected": json.dumps(subcodes, ensure_ascii=False),
            "domain": DOMAIN,
        })
    return sections


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hwp", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--stem", default="260629_kcore_manual")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    raw = extract_full_text(args.hwp)
    readable = clean_text(raw)

    source_file = str(args.hwp).replace("\\", "/")
    sections = segment(readable, source_file)

    txt_path = args.outdir / f"{args.stem}_readable.txt"
    sections_path = args.outdir / f"{args.stem}_sections.json"
    meta_path = args.outdir / f"{args.stem}_meta.json"

    txt_path.write_text(readable, encoding="utf-8")
    sections_path.write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")

    sha = hashlib.sha256(args.hwp.read_bytes()).hexdigest()
    korean = sum(1 for c in readable if "가" <= c <= "힣")
    all_codes = sorted(set(CODE_RE.findall(readable)))
    all_subcodes = sorted(set(SUBCODE_RE.findall(readable)))
    meta = {
        "source_id": SOURCE_ID,
        "source_hwp": source_file,
        "source_sha256": f"sha256:{sha}",
        "chars": len(readable),
        "korean_chars": korean,
        "sections": len(sections),
        "status_codes_detected": all_codes,
        "subcodes_detected": all_subcodes,
        "title_ko": "「육성형 전문기술인력 제도」 사증·체류관리 매뉴얼",
        "title_en": "Cultivation-type Professional Technical Personnel System (K-CORE) Visa/Stay Management Manual",
        "authority": "법무부 외국인정책과",
        "version": "2026.6",
        "effective_date": "2026-03-05",
        "distributed_date": "2026-06-29",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"readable : {txt_path} ({len(readable)} chars, {korean} korean)")
    print(f"sections : {sections_path} ({len(sections)} sections)")
    print(f"meta     : {meta_path}")
    print(f"sha256   : {sha}")
    print(f"codes    : {all_codes}")
    print(f"subcodes : {all_subcodes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
