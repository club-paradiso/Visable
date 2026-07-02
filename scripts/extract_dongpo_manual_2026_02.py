#!/usr/bin/env python3
"""Extract + segment the 「알기쉬운 외국국적동포 업무 매뉴얼」 (2026.2) source PDF.

This is the standalone distribution copy of the diaspora (외국국적동포) manual
covering 동포방문(C-3-8), 방문취업(H-2), 재외동포(F-4), 외국국적동포 영주(F-5),
동반(F-3)·방문동거(F-1), plus 별첨 1–10 (범죄경력증명서 기준, 한국어능력 입증
기준, H-2 취업 활동범위, 법무부 고시 제2026-35호 F-4 취업활동 제한범위 등).

The same manual content is embedded inside the 2026-06-23 stay manual
(pp. 529-579, see backend/data/sources/manuals/260623_stay_manual_readable.txt);
existing manualRefs in backend/data/visa_authoring/statuses/*.json point there.
This standalone copy is registered as a *corroborating* special-program source:
it carries the 별첨 attachments in full-page form and the 2026.2 baseline text.

The PDF is a 2-up export (each PDF page holds two logical booklet pages), made
with Hancom PDF from the original HWP on 2026-04-21. Because pypdf cannot
recover the logical page split reliably, the section index below is anchored at
PDF-page granularity with headings verified by manual inspection of every page.
The file identity is pinned by SHA-256 so the page map cannot silently drift.

Outputs (same record shape as the other manual section indexes):
  * <stem>_readable.txt   — full text with PDF-page markers
  * <stem>_sections.json  — per-page section records
  * <stem>_meta.json      — sha256, char counts, code inventory

Usage:
  python3 scripts/extract_dongpo_manual_2026_02.py \
      --pdf backend/data/sources/manuals/260421_dongpo_manual.pdf \
      --outdir backend/data/sources/manuals
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SOURCE_ID = "dongpo_manual_2026_02"
DOMAIN = "visa_stay_dongpo_program"
TITLE_KO = "알기쉬운 외국국적동포 업무 매뉴얼"
VERSION = "2026.2"
PINNED_SHA256 = "2f81f947e806749be9d37a687a15e619db9b39f132e07b67d6340d8a84584463"

# A-1 … H-2 with optional sub-segment (C-3-8, F-5-14, F-4-11, …).
CODE_RE = re.compile(r"\b([A-H]-\d{1,2}(?:-[0-9A-Z]{1,3})?)\b")
SUBCODE_RE = re.compile(r"\b([A-H]-\d{1,2}-[0-9A-Z]{1,3})\b")

# PDF-page → section heading, verified by inspecting each extracted page.
# (The 2-up layout means some pages carry the tail of one 별첨 and the head of
# the next; those are labelled as combined pages.)
PAGE_HEADINGS = {
    1: "표지 · 목차 / Ⅰ. 현행 재외동포 정책 개요(시작)",
    2: "별첨 목차 / Ⅰ. 현행 재외동포 정책 개요 — 단기방문(C-3-8)·방문취업(H-2) 신규발급 중단·F-4 일원화",
    3: "Ⅱ. 제도별 세부절차 — 1. 사증발급 절차 흐름도 · 2. 동포방문(C-3-8) 발급절차(시작)",
    4: "Ⅱ-2. 동포방문(C-3-8) 발급절차 — 제출서류 · Ⅱ-3. 방문취업(H-2) 체류관리 세부절차(시작)",
    5: "Ⅱ-3. 방문취업(H-2) 체류관리 — 취업개시·근무처변경 신고",
    6: "Ⅱ-4. 재외동포(F-4) 자격부여 제도 세부절차 — 기본 대상·사증발급",
    7: "Ⅱ-4. 재외동포(F-4) — 조기적응프로그램·자격변경",
    8: "Ⅱ-4. 재외동포(F-4) — 결격·벌금 기준 / Ⅱ-5. 외국국적동포 영주(F-5) 자격부여 세부절차(시작)",
    9: "Ⅱ-5. 영주(F-5) — 소득 요건·증빙",
    10: "Ⅱ-5. 영주(F-5) — 기본소양 요건",
    11: "Ⅱ-5. 영주(F-5) — 국적취득요건자(F-5-7) 등",
    12: "Ⅱ-5. 영주(F-5) — 근속·기술자격(F-5-14 관련) 기준",
    13: "Ⅱ-5. 영주(F-5) — 결격사유",
    14: "Ⅱ-6. 동반(F-3)·방문동거(F-1) 체류관리 절차 / Ⅲ. 기타 참고사항",
    15: "별첨 1. 해외 범죄경력증명서 제출기준 — 제출 대상(F-4)",
    16: "별첨 1. 해외 범죄경력증명서 제출기준 — 영주(F-5) 적용 대상",
    17: "별첨 1(계속) — 사회적 중대범죄 처리 기준 · 별첨 2. 한국어능력 입증서류 제출기준(시작)",
    18: "별첨 2. 한국어능력 입증서류 제출기준 — 면제 대상",
    19: "별첨 3. 방문취업(H-2) 취업 활동범위 — 법적 근거·지정 방식",
    20: "별첨 3. 방문취업(H-2) 허용 업종 상세 (KSIC)",
    21: "별첨 3. 방문취업(H-2) 허용 업종 상세 — 제조업 등",
    22: "별첨 3. 방문취업(H-2) 제외 업종 상세 — 수상 운송업 등",
    23: "별첨 3. 방문취업(H-2) 제외 업종 상세 — 보험업 등",
    24: "별첨 3(끝) — KSIC 확인 안내 · 별첨 4. 건강상태 확인서",
    25: "별첨 5. 건강진단서 · 별첨 6. 기업대표 신원보증서",
    26: "별첨 7. 법무부 고시 제2026-35호 — 재외동포(F-4) 취업활동 제한범위(시작)",
    27: "별첨 7. F-4 취업활동 제한직업 상세 — 음식점 배달원 등",
    28: "별첨 7. F-4 취업활동 제한직업 상세(계속)",
    29: "별첨 7. F-4 취업활동 제한직업 — 공공이익·취업질서 관련 세부직업",
    30: "별첨 8-1·8-2. F-4 취업활동 제한직업 비취업 서약서(영문·중문)",
    31: "별첨 8-3. 비취업 서약서(노문) · 별첨 9. 영주(F-5-14) 부여 자격 종목 및 등급(시작)",
    32: "별첨 9(계속) — 자격 종목·등급 · 별첨 10. 동포체류지원센터 현황",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--stem", default="260421_dongpo_manual")
    ap.add_argument(
        "--allow-unpinned",
        action="store_true",
        help="run even if the PDF sha256 does not match the pinned hash "
        "(the hardcoded page map is only verified for the pinned file)",
    )
    args = ap.parse_args()

    import pypdf

    data = args.pdf.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != PINNED_SHA256 and not args.allow_unpinned:
        raise SystemExit(
            f"refusing: sha256 {sha} != pinned {PINNED_SHA256}; the page-anchored "
            "section map is only verified for the pinned file (--allow-unpinned to override)"
        )

    reader = pypdf.PdfReader(str(args.pdf))
    n_pages = len(reader.pages)
    if n_pages != len(PAGE_HEADINGS) and not args.allow_unpinned:
        raise SystemExit(f"refusing: {n_pages} pages, page map covers {len(PAGE_HEADINGS)}")

    args.outdir.mkdir(parents=True, exist_ok=True)
    source_file = str(args.outdir / f"{args.stem}.pdf").replace("\\", "/")

    page_texts: list[str] = []
    readable_parts: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        page_texts.append(text)
        readable_parts.append(
            f"===== {TITLE_KO} {VERSION} / PDF page {i} of {n_pages} =====\n{text}\n"
        )
    readable = "\n".join(readable_parts)

    sections = []
    for i, text in enumerate(page_texts, start=1):
        codes = sorted(set(CODE_RE.findall(text)))
        subcodes = sorted(set(SUBCODE_RE.findall(text)))
        sections.append(
            {
                "source_id": SOURCE_ID,
                "source_file": source_file,
                "page": str(i),
                "section_no": i,
                "heading": PAGE_HEADINGS.get(i, f"PDF page {i}"),
                "text": text,
                "status_codes_detected": json.dumps(codes, ensure_ascii=False),
                "subcodes_detected": json.dumps(subcodes, ensure_ascii=False),
                "domain": DOMAIN,
            }
        )

    txt_path = args.outdir / f"{args.stem}_readable.txt"
    sections_path = args.outdir / f"{args.stem}_sections.json"
    meta_path = args.outdir / f"{args.stem}_meta.json"

    txt_path.write_text(readable, encoding="utf-8")
    sections_path.write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")

    korean = sum(1 for c in readable if "가" <= c <= "힣")
    all_codes = sorted(set(CODE_RE.findall(readable)))
    all_subcodes = sorted(set(SUBCODE_RE.findall(readable)))
    meta = {
        "source_id": SOURCE_ID,
        "source_pdf": source_file,
        "source_sha256": f"sha256:{sha}",
        "pdf_pages": n_pages,
        "layout_note": "2-up export: each PDF page holds two logical booklet pages (표시 쪽번호 기준 약 61쪽).",
        "chars": len(readable),
        "korean_chars": korean,
        "sections": len(sections),
        "status_codes_detected": all_codes,
        "subcodes_detected": all_subcodes,
        "title_ko": TITLE_KO,
        "title_en": "Easy Guide Manual for Overseas Koreans of Foreign Nationality (C-3-8 / H-2 / F-4 / F-5 / F-3 / F-1)",
        "authority": "법무부 출입국·외국인정책본부",
        "version": VERSION,
        "source_date": "unresolved",
        "source_date_note": "표지 표기는 '2026.2.'뿐이며 일 단위 발행일은 문서 자체에서 확인되지 않음. 파일명 260421은 PDF 내부 생성일(Hancom PDF 변환일 2026-04-21)을 따른 것.",
        "pdf_internal_creation_date": "2026-04-21T15:36:30+09:00",
        "pdf_internal_producer": "Hancom PDF 1.3.0.546 (Hwp 2022 12.0.0.3146)",
        "embedded_copy_note": "동일 내용의 동포 매뉴얼이 2026-06-23 체류 안내매뉴얼 pp. 529-579에 내장되어 있으며 기존 manualRefs는 그쪽을 가리킴. 본 파일은 별첨 원문 확인용 대조 사본.",
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
