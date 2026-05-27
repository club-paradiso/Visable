#!/usr/bin/env python3
"""Build Paradiso job/industry-code runtime data for HiKorea employment reporting.

Paradiso's HiKorea employment-information helper must show both:
  - 직종: 제8차 한국표준직업분류(KSCO8)
  - 업종: 제11차 한국표준산업분류(KSIC11)

After the full-table extraction and sample-validation PRs, this script now
prefers validated generated candidate tables when present:

  - data/generated/employment_reporting_ksco8_full_candidate.csv
  - data/generated/employment_reporting_ksic11_full_candidate.csv

If those generated files are not present, it falls back to the conservative seed
files so local development does not break. Humans demanded graceful degradation;
apparently even scripts now need emotional resilience.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from time import perf_counter

REPO_ROOT = Path(__file__).resolve().parents[1]
KSCO8_SEED = REPO_ROOT / "data" / "jobcode_master_ksco8_major_middle.csv"
KSIC11_SEED = REPO_ROOT / "data" / "industrycode_master_ksic11_major.csv"
KSCO8_FULL = REPO_ROOT / "data" / "generated" / "employment_reporting_ksco8_full_candidate.csv"
KSIC11_FULL = REPO_ROOT / "data" / "generated" / "employment_reporting_ksic11_full_candidate.csv"
OUT_FILE = REPO_ROOT / "data" / "jobcode_master.json"

KSCO8_URL = "https://kssc.mods.go.kr:8443/ksscNew_web/kssc/common/ClassificationContent.do?gubun=1&strCategoryNameCode=002&categoryMenu=007&addGubun=no"
KSIC11_SOURCE = "[별표2-2] 한국표준산업분류 제11차 개정 해설서(신구연계표 포함).pdf"


def load_seed(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"classification file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        records = [dict(row) for row in reader]
    required = {"code", "title_ko", "level", "parent_code"}
    if set(reader.fieldnames or []) != required:
        raise ValueError(f"Unexpected columns in {path}: {reader.fieldnames}")
    if not records:
        raise ValueError(f"classification file is empty: {path}")
    return records


def choose_table(full_path: Path, seed_path: Path) -> tuple[Path, str]:
    if full_path.is_file():
        return full_path, "full_candidate"
    return seed_path, "seed_fallback"


def to_runtime_rows(records: list[dict[str, str]], category: str, version_key: str) -> list[dict[str, str | None]]:
    code_key = "직업분류판" if category == "직업" else "산업분류판"
    return [
        {
            "분류": category,
            "상세설명": row["title_ko"],
            "코드값": row["code"],
            code_key: version_key,
            "분류수준": row["level"],
            "상위코드": row["parent_code"] or None,
        }
        for row in records
    ]


def smoke_search(rows: list[dict[str, str | None]]) -> dict:
    queries = ["영어", "강사", "소프트웨어", "음식", "제조", "정보통신", "농업", "프로그램"]
    started = perf_counter()
    results = {}
    for query in queries:
        q = query.lower()
        matches = [row for row in rows if q in str(row.get("상세설명", "")).lower() or q in str(row.get("코드값", "")).lower()]
        results[query] = min(len(matches), 9999)
    elapsed_ms = round((perf_counter() - started) * 1000, 3)
    return {"queries": results, "elapsed_ms": elapsed_ms, "row_count": len(rows)}


def build_payload(job_records: list[dict[str, str]], industry_records: list[dict[str, str]], job_mode: str, industry_mode: str) -> dict:
    job_rows = to_runtime_rows(job_records, "직업", "KSCO8")
    industry_rows = to_runtime_rows(industry_records, "산업", "KSIC11")
    data = job_rows + industry_rows
    return {
        "source": "통계청 표준분류 기반 취업정보 신고용 직종/업종 검색 데이터",
        "source_url": KSCO8_URL,
        "source_documents": [
            "(해설서) 제8차 한국표준직업분류(공개용)_24.6.24_(최종안).pdf",
            KSIC11_SOURCE,
            "붙임 1. 외국인 취업정보 온라인 신고제 개요_수정.hwpx",
            "붙임 2. 온라인 신고 절차(관서 방문예약 시 함께 신고하는 경우).hwpx",
            "붙임 3. 온라인 신고 절차(방문예약 없이 최초 신고 또는 변경 신고하는 경우).hwpx",
            "붙임 4. 취업정보 신고 자주 묻는 질문(FAQ).docx",
        ],
        "runtime_status": "full_candidate_enabled" if job_mode == industry_mode == "full_candidate" else "seed_fallback_enabled",
        "occupation_source": {
            "classification": "제8차 한국표준직업분류",
            "announcement": "통계청 고시 제2024-328호",
            "effective_date": "2025-01-01",
            "coverage_levels": sorted({row["level"] for row in job_records}),
            "record_count": len(job_rows),
            "table_mode": job_mode,
        },
        "industry_source": {
            "classification": "제11차 한국표준산업분류",
            "announcement": "통계청 고시 제2024-2호 및 제2024-203호 부칙 개정",
            "effective_date": "2024-07-01",
            "coverage_levels": sorted({row["level"] for row in industry_records}),
            "record_count": len(industry_rows),
            "table_mode": industry_mode,
        },
        "employment_reporting_context": {
            "reported_fields": ["직종", "업종", "연간소득"],
            "income_bands": ["소득없음", "연간 1천만 원 미만", "1천만~2천만 원 미만", "2천만~3천만 원 미만", "3천만~4천만 원 미만", "4천만~5천만 원 미만", "5천만 원 이상"],
            "target_statuses": ["E-1", "E-2", "E-3", "E-4", "E-5", "E-6", "E-7", "E-8", "E-9", "E-10", "F-2", "F-4", "F-6", "H-2", "D-7", "D-8", "D-9"],
            "exclusions": ["F-5", "영리활동에 종사하지 않는 사람"],
            "deadline": "변동사항 발생일 또는 영리활동 개시일부터 15일 이내",
            "hikorea_flow_note": "HiKorea 신고 화면은 직종조회와 업종조회를 별도로 선택한 뒤 연간소득 구간을 입력한다.",
        },
        "ui_safeguards": [
            "직종(KSCO8)과 업종(KSIC11)을 별도 결과 패널로 표시",
            "최종 코드는 HiKorea 또는 통계분류포털에서 확인하도록 안내",
            "E-7 적합성 판정으로 오해되지 않도록 안내",
        ],
        "search_smoke": smoke_search(data),
        "total_count": len(data),
        "categories": {"직업": len(job_rows), "산업": len(industry_rows)},
        "data": data,
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    job_path, job_mode = choose_table(KSCO8_FULL, KSCO8_SEED)
    industry_path, industry_mode = choose_table(KSIC11_FULL, KSIC11_SEED)
    job_records = load_seed(job_path)
    industry_records = load_seed(industry_path)
    payload = build_payload(job_records, industry_records, job_mode, industry_mode)
    if "--check" in argv:
        print(json.dumps({
            "categories": payload["categories"],
            "runtime_status": payload["runtime_status"],
            "occupation_mode": job_mode,
            "industry_mode": industry_mode,
            "search_smoke": payload["search_smoke"],
        }, ensure_ascii=False, indent=2))
        return 0
    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
