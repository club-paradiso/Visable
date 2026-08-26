#!/usr/bin/env python3
"""Apply the confirmed Top-Tier family sub-code refresh.

The 2026-08-07 visa/stay manuals confirm four active family variants that are
also present in Visable's already-approved 2026-07-31 visa manual but were
missing from the structured authoring layer:

  F-2-T1  Top-Tier residence dependent
  F-5-T1  Top-Tier permanent-residence dependent
  F-3-17  E-7-T dependent
  F-3-10  D-10-T dependent

This script edits the canonical authoring files, then regenerates visa_data.json
and backend/data/visas.json through the normal authoring pipeline.

It is intentionally idempotent: an existing code is never overwritten.

Usage:
  python3 scripts/visa/apply_manual_260807_top_tier_family_refresh.py
  python3 scripts/visa/apply_manual_260807_top_tier_family_refresh.py --check
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATUS_DIR = REPO / "backend" / "data" / "visa_authoring" / "statuses"
BUILD = REPO / "scripts" / "visa" / "build_visa_data.py"

SOURCE_REF = {
    "manualName": "사증발급 안내매뉴얼",
    "manualType": "visa",
    "manualVersion": "2026.7",
    "sourceDate": "2026-07-31",
    "sourceFile": "docs/source-manuals/2026-07-31/extracted/full_text/visa_manual_260731.txt",
    "sourceId": "visa_manual_2026_07_31_hwp",
    "section": "톱티어 비자(D-10-T, E-7-T, F-2-T, F-5-T) - 동반 가족 등",
    "confidence": "approved_manual_260731_hwp",
    "needsManualReview": False,
}

COMMON_DOCS = [
    "doc_app_form",
    "doc_photo",
    "doc_passport_copy",
    "doc_address",
    "doc_fee",
    "doc_id",
    "doc_fam_rel",
]

SUBCODES = {
    "F-2": [
        {
            "code": "F-2-T1",
            "name": "톱티어 동반 거주",
            "addReq": (
                "톱티어 거주(F-2-T) 자격자의 법률상 배우자 및 주 자격자가 친권·양육권을 "
                "가진 미성년 자녀가 대상이다. 국내 출생 자녀도 체류자격 부여 대상이 될 수 "
                "있으며, 체류기간은 주 자격자와 동일하게 부여한다."
            ),
            "addReqDocs": COMMON_DOCS,
            "note": (
                "원문은 혼인의 진정성·가족관계 및 주 자격자의 F-2-T 요건 충족 여부 등을 "
                "심사하도록 하고, 배우자는 제출 이력이 없는 경우 해외 범죄경력증명서를 "
                "요구한다. 시행령 제23조 제2항에 따른 취업활동 특례가 적용되나 별도 "
                "취업제한 분야는 유지된다."
            ),
            "searchAliases": ["F-2-T1", "F2T1", "톱티어 동반 거주", "톱티어거주 동반가족"],
            "manualRefs": [dict(SOURCE_REF)],
            "status": "active",
            "needsManualReview": False,
        }
    ],
    "F-5": [
        {
            "code": "F-5-T1",
            "name": "톱티어 동반 영주",
            "addReq": (
                "톱티어 동반 거주(F-2-T1) 자격으로 국내에서 3년 이상 체류한 경우, 또는 "
                "주 자격자가 톱티어 영주(F-5-T)를 취득한 뒤 동반가족으로 국내에 입국하여 "
                "F-2-T1 자격으로 2년 이상 체류한 경우가 대상 요건에 포함된다."
            ),
            "addReqDocs": COMMON_DOCS,
            "note": (
                "사증발급·자격변경 시 체류허가 제한 대상 여부, 품행 단정 요건 및 "
                "법무부장관이 정하는 요건 등을 종합 심사한다. 해외 발급 가족관계 서류와 "
                "해외 범죄경력증명서 관련 원문 요건을 함께 확인해야 한다."
            ),
            "searchAliases": ["F-5-T1", "F5T1", "톱티어 동반 영주", "톱티어영주 동반가족"],
            "manualRefs": [dict(SOURCE_REF)],
            "status": "active",
            "needsManualReview": False,
        }
    ],
    "F-3": [
        {
            "code": "F-3-17",
            "name": "유망톱티어 특정활동(E-7-T) 동반",
            "addReq": (
                "유망톱티어 특정활동(E-7-T) 자격자의 법률상 배우자 및 미성년 자녀에 "
                "적용되는 동반(F-3) 세부약호다."
            ),
            "addReqDocs": COMMON_DOCS,
            "note": (
                "Top-Tier 대상별 세부약호 표에서 E-7-T의 배우자·자녀를 F-3-17로 명시한다. "
                "부모와 가사보조인은 각각 F-1-15, F-1-24 체계로 별도 관리된다."
            ),
            "searchAliases": ["F-3-17", "F317", "E-7-T 동반", "유망톱티어 동반"],
            "manualRefs": [dict(SOURCE_REF)],
            "status": "active",
            "needsManualReview": False,
        },
        {
            "code": "F-3-10",
            "name": "예비톱티어 구직(D-10-T) 동반",
            "addReq": (
                "예비톱티어 구직(D-10-T) 자격자의 배우자 및 미성년 자녀에게 발급 가능한 "
                "동반(F-3) 세부약호다. D-10-T 주 자격자는 부모 또는 가사보조인을 이 "
                "Top-Tier 가족 체계로 초청할 수 없다."
            ),
            "addReqDocs": COMMON_DOCS,
            "note": (
                "원문은 D-10-T 본인과 동반가족(F-3)의 전자사증 발급이 불가하고, "
                "동반가족 사증은 재외공관 경로로 안내한다."
            ),
            "searchAliases": ["F-3-10", "F310", "D-10-T 동반", "예비톱티어 동반"],
            "manualRefs": [dict(SOURCE_REF)],
            "status": "active",
            "needsManualReview": False,
        },
    ],
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def existing_codes(record: dict) -> set[str]:
    subs = record.get("subcodes")
    if not isinstance(subs, list):
        raise RuntimeError(f"{record.get('code')}: canonical subcodes array is missing")
    return {str(s.get("code")) for s in subs if isinstance(s, dict) and s.get("code")}


def apply() -> int:
    changed = []
    for parent, additions in SUBCODES.items():
        path = STATUS_DIR / f"{parent}.json"
        record = load(path)
        subs = record.get("subcodes")
        if not isinstance(subs, list):
            raise RuntimeError(f"{parent}: canonical subcodes array is missing")
        present = existing_codes(record)
        added = []
        for sub in additions:
            if sub["code"] in present:
                continue
            subs.append(sub)
            present.add(sub["code"])
            added.append(sub["code"])
        if added:
            dump(path, record)
            changed.extend(added)
            print(f"{parent}: added {', '.join(added)}")
        else:
            print(f"{parent}: no-op")

    if not changed:
        print("No authoring changes required.")
        return check()

    res = subprocess.run([sys.executable, str(BUILD)], cwd=REPO)
    if res.returncode:
        return res.returncode
    return check()


def check() -> int:
    failures = []
    for parent, additions in SUBCODES.items():
        record = load(STATUS_DIR / f"{parent}.json")
        present = existing_codes(record)
        for sub in additions:
            if sub["code"] not in present:
                failures.append(f"authoring missing {sub['code']} under {parent}")

    for generated in (REPO / "visa_data.json", REPO / "backend" / "data" / "visas.json"):
        data = load(generated)
        searchable = set()
        for record in data:
            for key in ("subcodes", "subCodes"):
                for sub in record.get(key, []) or []:
                    if isinstance(sub, dict) and sub.get("code"):
                        searchable.add(str(sub["code"]))
        for additions in SUBCODES.values():
            for sub in additions:
                if sub["code"] not in searchable:
                    failures.append(f"{generated.relative_to(REPO)} missing {sub['code']}")

    if failures:
        for failure in failures:
            print("FAIL " + failure, file=sys.stderr)
        return 1
    print("PASS: all four Top-Tier family subcodes are present in authoring and generated data")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return check() if args.check else apply()


if __name__ == "__main__":
    raise SystemExit(main())
