#!/usr/bin/env python3
"""Build Paradiso occupation-code runtime data from the KSCO8 seed.

The occupation-code result source is the 8th Korean Standard Classification of
Occupations (KSCO8), not the older mixed industry/occupation public-data dump.

Current baseline:
  - 제8차 한국표준직업분류
  - 통계청 고시 제2024-328호
  - 시행일 2025-01-01
  - official KSSC route recorded in docs/data/KSCO8_OCCUPATION_CODE_SOURCE_UPDATE_2026_05.md

The committed seed contains major and middle groups only. Full minor/unit/
detailed-unit extraction must be a later table-validation PR.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KSCO8_SEED = REPO_ROOT / "data" / "jobcode_master_ksco8_major_middle.csv"
OUT_FILE = REPO_ROOT / "data" / "jobcode_master.json"

SOURCE_URL = "https://kssc.mods.go.kr:8443/ksscNew_web/kssc/common/ClassificationContent.do?gubun=1&strCategoryNameCode=002&categoryMenu=007&addGubun=no"


def load_ksco8_seed(path: Path = KSCO8_SEED) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"KSCO8 seed file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        records = [dict(row) for row in reader]
    required = {"code", "title_ko", "level", "parent_code"}
    if set(reader.fieldnames or []) != required:
        raise ValueError(f"Unexpected KSCO8 seed columns: {reader.fieldnames}")
    if not records:
        raise ValueError("KSCO8 seed file is empty")
    return records


def build_payload(records: list[dict[str, str]]) -> dict:
    runtime_rows = [
        {
            "분류": "직업",
            "상세설명": row["title_ko"],
            "코드값": row["code"],
            "직업분류판": "KSCO8",
            "분류수준": row["level"],
            "상위코드": row["parent_code"] or None,
        }
        for row in records
    ]
    return {
        "source": "통계청 제8차 한국표준직업분류(KSCO8) major/middle seed",
        "source_url": SOURCE_URL,
        "source_pdf": "(해설서) 제8차 한국표준직업분류(공개용)_24.6.24_(최종안).pdf",
        "announcement": "통계청 고시 제2024-328호",
        "effective_date": "2025-01-01",
        "coverage": {
            "classification": "제8차 한국표준직업분류",
            "levels": ["major", "middle"],
            "record_count": len(runtime_rows),
            "note": "Runtime occupation-code results use the KSCO8 major/middle seed until full detailed-table extraction is validated.",
        },
        "total_count": len(runtime_rows),
        "categories": {"직업": len(runtime_rows), "산업": 0},
        "data": runtime_rows,
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    records = load_ksco8_seed()
    payload = build_payload(records)
    if "--check" in argv:
        print(json.dumps(payload["coverage"], ensure_ascii=False, indent=2))
        return 0
    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
