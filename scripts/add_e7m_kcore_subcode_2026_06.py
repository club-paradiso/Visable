#!/usr/bin/env python3
"""Add the new E-7-M (K-CORE) sub-code under E-7 in visa_data.json.

Source: 「육성형 전문기술인력 제도」 사증·체류관리 매뉴얼 (법무부 외국인정책과,
2026.6; 시행일 2026-03-05, 배포 2026-06-29), committed at
backend/data/sources/manuals/260629_kcore_manual.hwp with the readable
extraction + section index alongside it.

Why this is a *safe, surgical* edit (per CLAUDE.md protected-file rules):
  * It appends exactly ONE sub-code object to the E-7 parent's `subCodes`
    and mirror `subcodes` arrays. It never rewrites, reorders, or deletes any
    existing record, and re-serialises with the file's existing format
    (`json.dumps(..., ensure_ascii=False, indent=2)` + trailing newline) so the
    git diff is limited to the inserted block.
  * E-7-M is classified UNDER E-7 (never a top-level family) — the manual
    itself defines it as a 특정활동(E-7) 세부 약호.
  * It does NOT touch the general D-2-1 record: the pilot's 유학(D-2-1) 특례
    rules must not become universal D-2-1 requirements.
  * Every field is grounded verbatim to the committed manual; nothing is
    invented. `needsManualReview` stays true so the UI renders an honest
    "검토 필요" source chip rather than over-claiming certification.

Idempotent: running twice is a no-op (E-7-M is added only if absent).

Usage:
  python3 scripts/add_e7m_kcore_subcode_2026_06.py            # apply
  python3 scripts/add_e7m_kcore_subcode_2026_06.py --check    # exit 1 if E-7-M missing
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VISA_DATA = REPO_ROOT / "visa_data.json"
PARENT_CODE = "E-7"
NEW_CODE = "E-7-M"


def build_subcode() -> "collections.OrderedDict":
    return collections.OrderedDict([
        ("code", "E-7-M"),
        ("name", "K-CORE(육성형 전문기술인력)"),
        ("summary",
         "전문대 ‘육성형 전문기술학과’ 졸업(예정) 유학생이 취득하는 K-CORE 취업비자. "
         "사회통합프로그램 4단계 이상(또는 TOPIK 5급 이상)을 갖추고 전공 연관 업체와 "
         "1년 이상·연봉 2,600만원 이상 고용계약을 체결하면 E-7-M로 체류자격을 변경할 수 있습니다. "
         "체류기간은 고용계약기간+3개월 범위 내 최대 3년, 직종코드 9991, 2년 시범운영"
         "(2026.3.5.~2027.12.31.)."),
        ("addReq",
         "전문대 육성형 전문기술학과 졸업(예정)자가 취득하는 취업비자"
         "(K-CORE, 지역 산업의 핵심 중간기술인력). 사회통합프로그램 4단계 이상 이수"
         "(또는 TOPIK 5급 이상)하고, 전공 연관 업체와 1년 이상·연봉 2,600만원 이상 "
         "고용계약을 체결한 경우 체류자격 변경. 육성형 전문기술학과 유학생(D-2-1) 외 "
         "다른 체류자격자는 E-7-M로 변경 불가."),
        ("addReqDocs", [
            "doc_degree",        # 육성형 전문기술학과 졸업증명서 또는 학위증
            "doc_topik",         # 한국어능력 입증 (TOPIK 5급 등)
            "doc_kiip_cert",     # 사회통합프로그램 4단계 이상 이수증
            "doc_emp_contract",  # 고용계약서 (1년 이상, 연봉 2,600만원 이상)
        ]),
        ("note",
         "직종코드 9991(육성형 전문기술이민), 세부약호 E-7-M(K-CORE 비자) 신설. "
         "체류기간은 고용계약기간+3개월 범위 내 최대 3년. 2년 시범운영"
         "(시행 2026.3.5. ~ 2027.12.31., 매뉴얼 배포 2026.6.29.)."),
        ("searchAliases", [
            "E-7-M", "E7M", "K-CORE", "KCORE", "케이코어",
            "육성형 전문기술인력", "육성형전문기술인력", "육성형 전문기술학과",
        ]),
        ("manualRefs", [
            collections.OrderedDict([
                ("manualName", "「육성형 전문기술인력 제도」 사증·체류관리 매뉴얼"),
                ("manualType", "special_program"),
                ("manualVersion", "2026.6"),
                ("sourceDate", "2026-06-29"),
                ("effectiveDate", "2026-03-05"),
                ("sourceFile", "backend/data/sources/manuals/260629_kcore_manual_readable.txt"),
                ("pageRange", "Ⅲ-2 · Ⅳ"),
                ("section", "[취업 시] K-CORE 자격 부여(E-7-M) — 체류자격 변경 / 행정사항(세부약호·직종코드 9991 신설)"),
                ("confidence", "manual_extracted_260629_hwp"),
                ("needsManualReview", True),
                ("sourceHwp", "backend/data/sources/manuals/260629_kcore_manual.hwp"),
                ("sourceId", "kcore_manual_2026_06_29"),
            ]),
        ]),
        ("status", "active"),
        ("needsManualReview", True),
        ("statusNote",
         "2026.6.29. 배포된 「육성형 전문기술인력 제도」 사증·체류관리 매뉴얼로 신설된 "
         "체류자격(2년 시범운영). 체류자격 변경·연장·근무처 변경 등 트랙별 세부 절차와 "
         "제출서류는 원문(backend/data/sources/manuals/260629_kcore_manual_readable.txt) 및 "
         "관할 출입국·외국인관서 확인이 필요합니다."),
    ])


def load_visas():
    raw = VISA_DATA.read_text(encoding="utf-8")
    return json.loads(raw, object_pairs_hook=collections.OrderedDict)


def has_e7m(visas) -> bool:
    for rec in visas:
        if isinstance(rec, dict) and rec.get("code") == PARENT_CODE:
            for key in ("subCodes", "subcodes"):
                for sub in rec.get(key, []) or []:
                    if isinstance(sub, dict) and sub.get("code") == NEW_CODE:
                        return True
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if E-7-M is not present (no write)")
    args = ap.parse_args(argv)

    visas = load_visas()

    if args.check:
        if has_e7m(visas):
            print(f"OK: {NEW_CODE} present under {PARENT_CODE}")
            return 0
        print(f"MISSING: {NEW_CODE} not found under {PARENT_CODE}", file=sys.stderr)
        return 1

    if has_e7m(visas):
        print(f"no-op: {NEW_CODE} already present under {PARENT_CODE}")
        return 0

    parent = next((r for r in visas
                   if isinstance(r, dict) and r.get("code") == PARENT_CODE), None)
    if parent is None:
        print(f"ERROR: parent {PARENT_CODE} not found in visa_data.json", file=sys.stderr)
        return 1

    subcode = build_subcode()
    added_to = []
    # Append to both the canonical `subCodes` and the mirror `subcodes` the
    # renderer prefers, keeping the two arrays consistent.
    for key in ("subCodes", "subcodes"):
        arr = parent.get(key)
        if isinstance(arr, list):
            arr.append(json.loads(json.dumps(subcode), object_pairs_hook=collections.OrderedDict))
            added_to.append(key)

    if not added_to:
        print(f"ERROR: {PARENT_CODE} has no subCodes/subcodes array", file=sys.stderr)
        return 1

    out = json.dumps(visas, ensure_ascii=False, indent=2) + "\n"
    VISA_DATA.write_text(out, encoding="utf-8")
    print(f"added {NEW_CODE} under {PARENT_CODE} → arrays: {', '.join(added_to)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
