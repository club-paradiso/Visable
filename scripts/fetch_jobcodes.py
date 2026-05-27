#!/usr/bin/env python3
"""Validate and stage KSCO/KSIC job and industry code source data.

This utility is intentionally conservative. The previous implementation used a
placeholder external API endpoint, which made the job-code data pipeline look
more authoritative than it was. For occupation-code results, Paradiso should use
an official KSCO source baseline.

Current occupation-code baseline:
  - 제8차 한국표준직업분류 (KSCO 8)
  - 통계청 고시 제2024-328호
  - 시행일 2025-01-01
  - official portal route recorded in docs/data/KSCO8_OCCUPATION_CODE_SOURCE_UPDATE_2026_05.md

The committed seed file currently contains major and middle groups only. Full
small/sub/unit-level extraction should be a later PR with table-level validation.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KSCO8_SEED = REPO_ROOT / "data" / "jobcode_master_ksco8_major_middle.csv"
OUT_FILE = REPO_ROOT / "data" / "jobcode_master.json"

SOURCE_META = {
    "classification": "제8차 한국표준직업분류",
    "english": "8th Korean Standard Classification of Occupations (KSCO)",
    "issuing_body": "통계청",
    "announcement": "통계청 고시 제2024-328호",
    "announced_date": "2024-07-01",
    "effective_date": "2025-01-01",
    "official_url": "https://kssc.mods.go.kr:8443/ksscNew_web/kssc/common/ClassificationContent.do?gubun=1&strCategoryNameCode=002&categoryMenu=007&addGubun=no",
    "source_pdf": "(해설서) 제8차 한국표준직업분류(공개용)_24.6.24_(최종안).pdf",
}


def load_ksco8_seed(path: Path = KSCO8_SEED) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"KSCO8 seed file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        records = [dict(row) for row in reader]
    if not records:
        raise ValueError("KSCO8 seed file is empty")
    required = {"code", "title_ko", "level", "parent_code"}
    if set(reader.fieldnames or []) != required:
        raise ValueError(f"Unexpected KSCO8 seed columns: {reader.fieldnames}")
    return records


def build_payload(records: list[dict[str, str]]) -> dict:
    return {
        "schema_version": "1.0",
        "source": SOURCE_META,
        "coverage": {
            "levels": ["major", "middle"],
            "record_count": len(records),
            "note": "Seed data for search/navigation. Full small/sub/unit-level extraction requires a later full-table extraction PR.",
        },
        "records": records,
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
