#!/usr/bin/env python3
"""Build Paradiso's HiKorea employment-information reporting reference dataset.

Output: data/jobcode_master.json

This dataset powers ONLY the HiKorea 취업정보 신고용 직종·업종 참고 검색 helper.
It is NOT an E-7 visa occupation-code list, NOT 한국고용직업분류(KECO), and NOT
National Tax Service business-type codes. It does not determine visa eligibility.

Two classifications are combined, type-scoped so occupation and industry codes
never collide:

  직종 (occupation)  제8차 한국표준직업분류  (KSCO8)  - 통계청 고시 제2024-328호, 시행 2025-01-01
  업종 (industry)    제11차 한국표준산업분류 (KSIC11) - 통계청 고시 제2024-2호,  시행 2024-07-01

Source-of-truth inputs (committed), highest -> lowest priority:

  Occupation
    1. data/generated/employment_reporting_ksco8_full_candidate.csv   (full 1,999 rows)
       Produced by scripts/extract_employment_reporting_full_tables.py from the
       official 제8차 KSCO classification file. Drop it in to ship the full table.
    2. data/jobcode_master_ksco8_major_middle.csv                     (verified seed: 10 대분류 + 57 중분류)

  Industry
    data/sources/ksic11_full_2038.csv                                 (full 2,038 rows, all 5 levels)

Official full-table targets (validated against 통계청/국가데이터처 통계분류포털):
    KSCO8  1,999 rows  (major 10 / middle 57 / minor 167 / unit 495 / detailed_unit 1,270)
    KSIC11 2,038 rows  (major 21 / middle 77 / minor 234 / unit 501 / detailed_unit 1,205)

See docs/audits/hikorea-employment-code-source-audit-2026.md for source verification.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# --- inputs ---------------------------------------------------------------
# Occupation source priority (highest -> lowest):
#   1. full candidate (all 5 levels, 1,999) — from the KSCO-only 분류항목표
#   2. ISCO-linkage candidate (4 levels, 728: 대/중/소/세분류 + EN at 세분류) —
#      from scripts/convert_ksco8_isco_linkage.py
#   3. verified seed (대분류+중분류, 67)
OCC_FULL = REPO / "data" / "generated" / "employment_reporting_ksco8_full_candidate.csv"
OCC_CANDIDATE = REPO / "data" / "generated" / "employment_reporting_ksco8_candidate.csv"
OCC_SEED = REPO / "data" / "jobcode_master_ksco8_major_middle.csv"
IND_FULL = REPO / "data" / "sources" / "ksic11_full_2038.csv"
OUT = REPO / "data" / "jobcode_master.json"

SCHEMA_VERSION = "2026-06-hikorea-employment-reporting-reference"

OCCUPATION_SOURCE = {
    "classification": "제8차 한국표준직업분류",
    "short_name": "KSCO8",
    "announcement": "통계청 고시 제2024-328호",
    "announcement_date": "2024-07-01",
    "effective_date": "2025-01-01",
    "issuing_body": "통계청 / 국가데이터처",
    "portal": "국가데이터처 통계분류포털 (kssc)",
    "full_table_expected_count": 1999,
    "counts_by_level_expected": {
        "major": 10, "middle": 57, "minor": 167, "unit": 495, "detailed_unit": 1270,
    },
}

INDUSTRY_SOURCE = {
    "classification": "제11차 한국표준산업분류",
    "short_name": "KSIC11",
    "announcement": "통계청 고시 제2024-2호 (부칙개정 제2024-203호)",
    "announcement_date": "2024-01-01",
    "effective_date": "2024-07-01",
    "issuing_body": "통계청 / 국가데이터처",
    "portal": "국가데이터처 통계분류포털 (kssc)",
    "full_table_expected_count": 2038,
    "counts_by_level_expected": {
        "major": 21, "middle": 77, "minor": 234, "unit": 501, "detailed_unit": 1205,
    },
}

SOURCE_BOUNDARY = "HiKorea employment-information reporting reference search only"

# Standard KSIC11 대분류(letter) -> 중분류(2-digit) numeric ranges. Used to attach the
# letter parent to 2-digit middles (industry codes are not pure prefixes at that step).
# Validated at build time against the ranges embedded in the source data.
KSIC_MAJOR_RANGES = {
    "A": (1, 3), "B": (5, 8), "C": (10, 34), "D": (35, 35), "E": (36, 39),
    "F": (41, 42), "G": (45, 47), "H": (49, 52), "I": (55, 56), "J": (58, 63),
    "K": (64, 66), "L": (68, 68), "M": (70, 73), "N": (74, 76), "O": (84, 84),
    "P": (85, 85), "Q": (86, 87), "R": (90, 91), "S": (94, 96), "T": (97, 98),
    "U": (99, 99),
}

LEVELS = {1: "major", 2: "middle", 3: "minor", 4: "unit", 5: "detailed_unit"}
LEVEL_LABEL_KO = {
    "major": "대분류", "middle": "중분류", "minor": "소분류",
    "unit": "세분류", "detailed_unit": "세세분류",
}

# Tokens too generic to be useful standalone search terms.
TERM_STOPWORDS = {"및", "그", "외", "관련", "기타", "종사자", "종사원", "그외"}

# Curated layperson-query synonyms keyed by code (type-scoped). Kept conservative:
# every term is a plain-language alias for the category, never a new requirement.
OCC_SYNONYMS = {
    "22": ["개발자", "소프트웨어", "프로그래머", "웹개발", "앱개발", "코딩", "IT", "에스아이", "데이터"],
    "21": ["연구원", "연구", "리서치"],
    "25": ["강사", "영어강사", "학원강사", "선생님", "교사", "과외", "어학", "영어회화"],
    "28": ["번역가", "통역사", "통번역", "디자이너", "작가", "콘텐츠"],
    "24": ["간호사", "사회복지사", "상담사"],
    "42": ["돌봄", "요양보호사", "간병인", "보육", "베이비시터"],
    "44": ["요리사", "셰프", "바리스타", "주방", "카페", "서빙", "홀서빙", "종업원", "조리"],
    "52": ["판매원", "점원", "매장", "자영업", "가게", "캐셔"],
    "51": ["영업", "세일즈", "영업원"],
    "87": ["운전", "운전기사", "배달", "택배", "기사"],
    "8": ["공장", "생산직", "제조"],
    "9": ["단순노무", "알바", "아르바이트"],
}
IND_SYNONYMS = {
    "J": ["IT", "정보통신", "소프트웨어"],
    "62": ["소프트웨어", "IT", "개발", "에스아이", "프로그래밍"],
    "63": ["포털", "데이터", "호스팅", "온라인"],
    "85": ["학원", "교육", "어학원", "과외"],
    "56": ["음식점", "식당", "카페", "레스토랑", "주점", "술집"],
    "55": ["숙박", "호텔", "게스트하우스", "모텔"],
    "C": ["제조업", "공장", "생산"],
    "47": ["소매", "가게", "상점", "자영업"],
    "G": ["도소매", "유통", "판매업"],
    "Q": ["병원", "요양", "복지", "돌봄"],
    "I": ["숙박", "음식점", "외식"],
}


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def level_of(code: str) -> str:
    return LEVELS[len(code)]


def occ_parent(code: str) -> str:
    return "" if len(code) == 1 else code[:-1]


def ind_parent(code: str) -> str:
    if len(code) == 1:  # letter major
        return ""
    if len(code) == 2:  # 2-digit middle -> letter major via range map
        n = int(code)
        for letter, (lo, hi) in KSIC_MAJOR_RANGES.items():
            if lo <= n <= hi:
                return letter
        raise ValueError(f"no KSIC major range contains middle {code}")
    return code[:-1]


def tokens(name: str) -> list[str]:
    parts = re.split(r"[\s·∙,/()]+", name)
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= 2 and p not in TERM_STOPWORDS:
            out.append(p)
    return out


def build_rows(records: list[dict], kind: str) -> list[dict]:
    """kind in {'occupation','industry'}."""
    source = OCCUPATION_SOURCE if kind == "occupation" else INDUSTRY_SOURCE
    parent_fn = occ_parent if kind == "occupation" else ind_parent
    synonyms = OCC_SYNONYMS if kind == "occupation" else IND_SYNONYMS

    by_code = {str(r["code"]): str(r["title_ko"]) for r in records}
    rows = []
    for r in records:
        code = str(r["code"]).strip()
        name = str(r["title_ko"]).strip()
        level = level_of(code)
        parent = parent_fn(code)
        # validate seed-provided parent/level if present
        if r.get("parent_code") not in (None, "") and str(r["parent_code"]) != parent:
            raise ValueError(f"{kind} {code}: derived parent {parent!r} != seed {r['parent_code']!r}")
        if r.get("level") and str(r["level"]) != level:
            raise ValueError(f"{kind} {code}: derived level {level!r} != seed {r['level']!r}")
        # path_ko: walk up the parent chain (root -> leaf)
        path, cur = [], code
        while cur:
            path.append(by_code.get(cur, cur))
            cur = parent_fn(cur)
        path.reverse()
        # KSIC/KSCO repeat a name across single-child levels; collapse consecutive
        # duplicates so the breadcrumb reads cleanly.
        crumb = [p for i, p in enumerate(path) if i == 0 or p != path[i - 1]]
        path_ko = " > ".join(crumb)
        # search terms: own tokens + ancestor tokens + curated synonyms
        terms: list[str] = []
        for piece in path:
            terms.extend(tokens(piece))
        terms.append(name)
        terms.append(code)
        terms.extend(synonyms.get(code, []))
        seen, uniq = set(), []
        for t in terms:
            key = t.lower()
            if key not in seen:
                seen.add(key)
                uniq.append(t)
        name_en = str(r.get("name_en") or "").strip() or None
        rows.append({
            "type": kind,
            "code": code,
            "name_ko": name,
            "name_en": name_en,
            "level": level,
            "level_label_ko": LEVEL_LABEL_KO[level],
            "parent_code": parent or None,
            "path_ko": path_ko,
            "search_terms_ko": uniq,
            "source_classification": source["classification"],
            "source_version": source["short_name"],
            "source_effective_date": source["effective_date"],
        })
    return rows


def coverage(rows: list[dict]) -> dict:
    return dict(Counter(r["level"] for r in rows))


def main() -> int:
    # occupation source priority: full table -> ISCO-linkage (4 levels) -> seed
    if OCC_FULL.is_file():
        occ_records = load_csv(OCC_FULL)
        occ_data_source = "full_candidate"
    elif OCC_CANDIDATE.is_file():
        occ_records = load_csv(OCC_CANDIDATE)
        occ_data_source = "ksco8_isco08_linkage_4level"
    else:
        occ_records = load_csv(OCC_SEED)
        occ_data_source = "verified_seed_major_middle"

    ind_records = load_csv(IND_FULL)

    occ_rows = build_rows(occ_records, "occupation")
    ind_rows = build_rows(ind_records, "industry")

    # type-scoped duplicate check (occupation/industry codes may legitimately overlap)
    for label, rows in (("occupation", occ_rows), ("industry", ind_rows)):
        codes = [r["code"] for r in rows]
        dups = [c for c, n in Counter(codes).items() if n > 1]
        if dups:
            raise ValueError(f"duplicate {label} codes: {dups}")

    occ_cov = coverage(occ_rows)
    ind_cov = coverage(ind_rows)

    occ_meta = dict(OCCUPATION_SOURCE)
    occ_meta.update({
        "runtime_count": len(occ_rows),
        "runtime_coverage_levels": occ_cov,
        "data_source": occ_data_source,
        "full_table_loaded": len(occ_rows) == OCCUPATION_SOURCE["full_table_expected_count"],
    })
    ind_meta = dict(INDUSTRY_SOURCE)
    ind_meta.update({
        "runtime_count": len(ind_rows),
        "runtime_coverage_levels": ind_cov,
        "data_source": "ksic11_full_runtime",
        "full_table_loaded": len(ind_rows) == INDUSTRY_SOURCE["full_table_expected_count"],
    })

    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_boundary": SOURCE_BOUNDARY,
        "not_this": {
            "not_e7_occupation_codes": "E-7 사증 직종코드 목록이 아닙니다.",
            "not_keco": "한국고용직업분류(KECO)가 아닙니다.",
            "not_nts_business_codes": "국세청 업종코드가 아닙니다.",
            "not_eligibility": "체류자격 적격성/자격외활동 허가 여부를 판단하지 않습니다.",
        },
        "occupation_source": occ_meta,
        "industry_source": ind_meta,
        "employment_reporting_context": {
            "reported_fields": ["직종", "업종", "연간소득"],
            "effective_from": "2026-01-02",
            "income_bands": [
                "소득없음", "연간 1천만 원 미만", "1천만~2천만 원 미만",
                "2천만~3천만 원 미만", "3천만~4천만 원 미만",
                "4천만~5천만 원 미만", "5천만 원 이상",
            ],
            "target_statuses": [
                "E-1", "E-2", "E-3", "E-4", "E-5", "E-6", "E-7", "E-8", "E-9", "E-10",
                "F-2", "F-4", "F-6", "H-2", "D-7", "D-8", "D-9",
            ],
            "excluded_statuses": ["F-5"],
            "excluded_cases": ["영리활동에 종사하지 않는 사람"],
            "deadline": "영리활동 개시 또는 신고사항(직종·업종·연간소득 구간) 변경 후 15일 이내",
            "list_source_note": (
                "HiKorea 신고 화면의 직종조회는 국가데이터처 표준직업분류표를, "
                "업종조회는 국가데이터처 표준산업분류표를 기준으로 표시되며 "
                "국가데이터처 통계분류포털에서 확인할 수 있다."
            ),
            "final_confirmation": "최종 신고 코드는 HiKorea 신고 화면 또는 1345에서 반드시 확인",
        },
        # convenience aggregates
        "total_count": len(occ_rows) + len(ind_rows),
        "categories": {"직종": len(occ_rows), "업종": len(ind_rows)},
        "data": occ_rows + ind_rows,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"  occupation ({occ_data_source}): {len(occ_rows)}  levels={occ_cov}")
    print(f"  industry:                       {len(ind_rows)}  levels={ind_cov}")
    print(f"  total: {payload['total_count']}")
    if not occ_meta["full_table_loaded"]:
        print(f"  NOTE: occupation data_source={occ_data_source} ({len(occ_rows)} rows).")
        print("        For the full 1,999-row table (incl. 세세분류/5-digit), drop in")
        print("        data/generated/employment_reporting_ksco8_full_candidate.csv")
        print("        (from the KSCO-only 분류항목표) and re-run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
