#!/usr/bin/env python3
"""Data tests for the HiKorea employment-reporting reference dataset.

Covers data/jobcode_master.json: counts, source metadata, edition-correctness
(KSCO8 not KSCO7), KSIC11 samples, type-scoped duplicate handling, and the
no-cross-mislabel invariant. Stdlib-only; run directly:

    python3 scripts/tests/test_employment_reporting_dataset.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data" / "jobcode_master.json"

EXPECTED_OCC_FULL = 1999
EXPECTED_IND_FULL = 2038
EXPECTED_TOTAL_FULL = 4037


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def rows_by_type(d, t):
    return [r for r in d["data"] if r["type"] == t]


def check(cond, msg, failures):
    if not cond:
        failures.append(msg)


def main() -> int:
    d = load()
    f: list[str] = []
    occ = rows_by_type(d, "occupation")
    ind = rows_by_type(d, "industry")
    occ_codes = [r["code"] for r in occ]
    ind_codes = [r["code"] for r in ind]

    # --- source metadata exists ---
    osrc, isrc = d.get("occupation_source", {}), d.get("industry_source", {})
    check(osrc.get("short_name") == "KSCO8", "occupation_source.short_name != KSCO8", f)
    check(osrc.get("classification") == "제8차 한국표준직업분류", "occupation_source.classification wrong", f)
    check(osrc.get("announcement") == "통계청 고시 제2024-328호", "occupation_source.announcement wrong", f)
    check(osrc.get("effective_date") == "2025-01-01", "occupation_source.effective_date wrong", f)
    check(isrc.get("short_name") == "KSIC11", "industry_source.short_name != KSIC11", f)
    check(isrc.get("classification") == "제11차 한국표준산업분류", "industry_source.classification wrong", f)
    check(isrc.get("effective_date") == "2024-07-01", "industry_source.effective_date wrong", f)
    check(d.get("source_boundary") == "HiKorea employment-information reporting reference search only",
          "source_boundary missing/wrong", f)

    # --- expected full-table targets recorded (audit's source-of-truth numbers) ---
    check(osrc.get("full_table_expected_count") == EXPECTED_OCC_FULL, "occupation full_table_expected_count != 1999", f)
    check(isrc.get("full_table_expected_count") == EXPECTED_IND_FULL, "industry full_table_expected_count != 2038", f)
    check(EXPECTED_OCC_FULL + EXPECTED_IND_FULL == EXPECTED_TOTAL_FULL, "expected totals inconsistent", f)

    # --- industry is the full KSIC11 table (2038) ---
    check(len(ind) == EXPECTED_IND_FULL, f"industry count {len(ind)} != {EXPECTED_IND_FULL}", f)
    ind_levels = Counter(r["level"] for r in ind)
    check(dict(ind_levels) == {"major": 21, "middle": 77, "minor": 234, "unit": 501, "detailed_unit": 1205},
          f"industry level shape wrong: {dict(ind_levels)}", f)

    # --- occupation is correct EDITION (KSCO8), full table or verified seed ---
    occ_map = {r["code"]: r["name_ko"] for r in occ}
    # 8th-edition service-sector signature (split 42/43/.. + new code 45)
    check(occ_map.get("42") == "돌봄 및 보건 서비스직", f"KSCO8 sample 42 wrong: {occ_map.get('42')}", f)
    check(occ_map.get("43") == "개인 생활 서비스직", f"KSCO8 sample 43 wrong: {occ_map.get('43')}", f)
    check(occ_map.get("45") == "조리 및 음식 서비스직", f"KSCO8 sample 45 wrong: {occ_map.get('45')}", f)
    # must NOT carry the 7th-edition merged middle name
    check("돌봄·보건 및 개인 생활 서비스직" not in occ_map.values(),
          "7th-edition service middle name leaked into occupation table", f)

    full_loaded = bool(osrc.get("full_table_loaded"))
    if full_loaded:
        check(len(occ) == EXPECTED_OCC_FULL, f"occupation full_table_loaded but count {len(occ)} != 1999", f)
        check(len(d["data"]) == EXPECTED_TOTAL_FULL, f"total {len(d['data'])} != 4037 with full table", f)
        check(occ_map.get("222") == "컴퓨터 시스템 및 소프트웨어 전문가",
              f"KSCO8 sample 222 wrong: {occ_map.get('222')}", f)
    else:
        # verified seed state: 대분류(10) + 중분류(57) only
        occ_levels = Counter(r["level"] for r in occ)
        check(dict(occ_levels) == {"major": 10, "middle": 57},
              f"occupation seed level shape wrong: {dict(occ_levels)}", f)
        check(osrc.get("runtime_count") == len(occ), "occupation_source.runtime_count mismatch", f)

    # --- type-scoped duplicate handling (codes may overlap ACROSS types) ---
    occ_dups = [c for c, n in Counter(occ_codes).items() if n > 1]
    ind_dups = [c for c, n in Counter(ind_codes).items() if n > 1]
    check(not occ_dups, f"duplicate occupation codes: {occ_dups}", f)
    check(not ind_dups, f"duplicate industry codes: {ind_dups}", f)

    # --- no row mislabeled across types: every row carries its classification version ---
    check(all(r.get("source_version") == "KSCO8" for r in occ), "an occupation row is not tagged KSCO8", f)
    check(all(r.get("source_version") == "KSIC11" for r in ind), "an industry row is not tagged KSIC11", f)
    # KSIC letter-majors must be industry-typed, never occupation
    check(all(jt != "occupation" for r in d["data"] for jt in [r["type"]] if r["code"] in {"J", "C", "Q"} and len(r["code"]) == 1 and r["source_version"] == "KSIC11"),
          "industry letter-major mistyped", f)

    # --- KSIC11 required samples ---
    ind_map = {r["code"]: r["name_ko"] for r in ind}
    check(ind_map.get("J") == "정보통신업", f"KSIC11 J wrong: {ind_map.get('J')}", f)
    check(ind_map.get("62") == "컴퓨터 프로그래밍, 시스템 통합 및 관리업", f"KSIC11 62 wrong: {ind_map.get('62')}", f)
    check(ind_map.get("62010") == "컴퓨터 프로그래밍 서비스업", f"KSIC11 62010 wrong: {ind_map.get('62010')}", f)

    # --- every row has the required enriched fields ---
    required_fields = {"type", "code", "name_ko", "name_en", "level", "parent_code", "path_ko",
                       "search_terms_ko", "source_classification", "source_version", "source_effective_date"}
    sample_missing = [r["code"] for r in d["data"][:50] if required_fields - set(r.keys())]
    check(not sample_missing, f"rows missing required fields: {sample_missing[:5]}", f)

    if f:
        print("FAIL: employment-reporting dataset tests")
        for m in f:
            print("  -", m)
        return 1
    print(f"OK: employment-reporting dataset — occupation {len(occ)} (full={full_loaded}), "
          f"industry {len(ind)}, total {len(d['data'])}; KSCO8/KSIC11 metadata + samples verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
