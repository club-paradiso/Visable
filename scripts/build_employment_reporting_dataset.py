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

# Curated layperson-query synonyms, NAME-ANCHORED (not code-keyed) so they stay
# correct regardless of KSCO/KSIC numbering: each group's extra terms attach to any
# row whose name_ko contains one of the anchor substrings. Every term is a plain-
# language alias for the category, never a new requirement.
OCC_ANCHORS = [
    (["정보 통신 전문가", "컴퓨터 시스템", "소프트웨어", "응용 소프트웨어", "웹 개발", "데이터 전문가", "네트워크", "정보 보안"],
     ["개발자", "소프트웨어", "프로그래머", "웹개발", "앱개발", "코딩", "IT", "에스아이", "개발"]),
    (["연구원"], ["연구원", "연구", "리서치"]),
    (["외국어 강사"], ["영어강사", "영어회화", "어학강사", "외국어강사"]),
    (["강사"], ["강사", "학원강사", "과외"]),
    (["학교 교사", "교사"], ["교사", "선생님"]),
    (["번역가 및 통역가", "번역", "통역"], ["통번역", "번역", "통역", "번역가", "통역사"]),
    (["디자이너"], ["디자이너", "디자인"]),
    (["작가", "기자", "콘텐츠"], ["작가", "콘텐츠", "기자"]),
    (["돌봄", "요양", "간병"], ["돌봄", "요양보호사", "간병인", "베이비시터"]),
    (["보육"], ["보육", "어린이집", "유치원"]),
    (["간호사"], ["간호사"]),
    (["의사"], ["의사"]),
    (["사회복지"], ["사회복지사", "복지사"]),
    (["조리", "주방", "요리사", "식음료 서비스"], ["요리사", "셰프", "바리스타", "카페", "주방", "서빙", "홀서빙", "종업원", "조리"]),
    (["미용"], ["미용사", "헤어", "네일"]),
    (["매장 판매", "상점", "판매원"], ["판매원", "점원", "매장", "자영업", "가게", "캐셔"]),
    (["영업"], ["영업", "세일즈", "영업원"]),
    (["운전"], ["운전", "운전기사", "기사"]),
    (["배달", "택배"], ["배달", "택배", "배송"]),
    (["건설", "건축", "토목"], ["건설", "건축", "토목", "현장"]),
    (["용접"], ["용접", "용접공"]),
    (["회계사", "세무사", "경리"], ["회계사", "세무사", "경리"]),
    (["조작", "조립", "생산"], ["공장", "생산직", "제조", "조립"]),
    (["단순"], ["단순노무", "알바", "아르바이트"]),
    (["농업", "작물", "재배", "축산"], ["농업", "농장", "작물", "재배", "축산"]),
]
IND_ANCHORS = [
    (["컴퓨터 프로그래밍", "소프트웨어", "정보통신", "정보 서비스"], ["소프트웨어", "IT", "개발", "에스아이", "프로그래밍", "정보통신"]),
    (["포털", "호스팅", "데이터베이스"], ["포털", "데이터", "호스팅", "온라인"]),
    (["교육 서비스", "학원", "교습"], ["학원", "교육", "어학원", "과외"]),
    (["음식점 및 주점", "음식점업", "주점 및 비알코올", "주점업", "비알코올 음료점"],
     ["음식점", "식당", "카페", "레스토랑", "주점", "술집", "외식", "분식", "치킨집"]),
    (["숙박", "호텔"], ["숙박", "호텔", "게스트하우스", "모텔"]),
    (["제조업"], ["제조", "공장", "생산"]),
    (["소매업", "소매"], ["소매", "가게", "상점", "자영업"]),
    (["도매업", "도매"], ["도매", "유통"]),
    (["병원", "의원", "보건업", "의료"], ["병원", "의료", "보건", "클리닉"]),
    (["사회복지", "요양"], ["요양", "복지", "돌봄"]),
    (["건설업"], ["건설", "시공"]),
    (["운수", "운송", "물류", "택배"], ["운송", "물류", "택배", "배송"]),
    (["미용", "이용업"], ["미용실", "헤어샵", "네일샵"]),
]


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
    anchors = OCC_ANCHORS if kind == "occupation" else IND_ANCHORS

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
        for anchor_keys, extra in anchors:
            if any(a in name for a in anchor_keys):
                terms.extend(extra)
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
            "income_basis": "과세 전 소득 기준이며, 소득 '구간'이 변경된 경우에만 변경 신고",
            "main_job_rule": "복수 직장(부업·겸업 포함) 시 주된 영리활동(근로시간이 가장 많은 직장) 1개 기준으로 신고",
            "legal_basis": "출입국관리법 시행규칙 제47조 및 제49조의2",
            "penalty_note": "기한 내 미신고 시 과태료 부과 가능(최대 100만원); 반복·의도적 불이행 등을 고려해 관할 출입국·외국인관서장이 결정",
            "pilot_period": "2026년 1~6월 시범운영(온라인+기존 서식 병행), 이후 온라인 신고만 가능",
            "list_source_note": (
                "HiKorea 신고 화면의 직종조회는 국가데이터처 표준직업분류표를, "
                "업종조회는 국가데이터처 표준산업분류표를 기준으로 표시되며 "
                "국가데이터처 통계분류포털에서 확인할 수 있다. (FAQ Q7, 붙임2 절차)"
            ),
            "classification_portal_url": "https://kssc.mods.go.kr",
            "official_sources": [
                "data/sources/hikorea_employment_reporting_overview.hwpx",
                "data/sources/hikorea_employment_reporting_procedure_visit.hwpx",
                "data/sources/hikorea_employment_reporting_faq.docx",
            ],
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
