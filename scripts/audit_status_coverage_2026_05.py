#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(".")
VISA_DATA = ROOT / "visa_data.json"
OUT_MD = ROOT / "docs/data/VISA_STATUS_COVERAGE_AUDIT_2026_05.md"
OUT_JSON = ROOT / "docs/data/visa_status_coverage_audit_2026_05.json"

CANONICAL_MANUAL_PATHS = [
    "docs/source-manuals/2026-05/stay_manual_2026_05.pdf",
    "docs/source-manuals/2026-05/visa_manual_2026_05.pdf",
    "docs/source-manuals/2026-05/체류민원 안내매뉴얼_260521.pdf",
    "docs/source-manuals/2026-05/사증발급 안내매뉴얼_260521.pdf",
]

# Legal/top-level 체류자격 기준.
# Source basis:
# - 출입국관리법 시행령 별표 1 / 별표 1의2 체류자격 체계
# - 2026.5 체류민원 안내매뉴얼 목차
# Note:
# - F-1-6, F-2-7, E-7-4 같은 세부 약호는 top-level 체류자격이 아님.
# - 이런 코드는 subCode/alias/scenario reference로 검색되어야 함.
EXPECTED_LEGAL_TOP_LEVEL = {
    "A-1": "외교",
    "A-2": "공무",
    "A-3": "협정",
    "B-1": "사증면제",
    "B-2": "관광통과",
    "C-1": "일시취재",
    "C-3": "단기방문",
    "C-4": "단기취업",
    "D-1": "문화예술",
    "D-2": "유학",
    "D-3": "기술연수",
    "D-4": "일반연수",
    "D-5": "취재",
    "D-6": "종교",
    "D-7": "주재",
    "D-8": "기업투자",
    "D-9": "무역경영",
    "D-10": "구직",
    "E-1": "교수",
    "E-2": "회화지도",
    "E-3": "연구",
    "E-4": "기술지도",
    "E-5": "전문직업",
    "E-6": "예술흥행",
    "E-7": "특정활동",
    "E-8": "계절근로",
    "E-9": "비전문취업",
    "E-10": "선원취업",
    "F-1": "방문동거",
    "F-2": "거주",
    "F-3": "동반",
    "F-4": "재외동포",
    "F-5": "영주",
    "F-6": "결혼이민",
    "G-1": "기타",
    "H-1": "관광취업",
    "H-2": "방문취업",
}

# 2026.5 체류민원 매뉴얼 목차상 법정 top-level 외 별도 정책/운영 섹션.
# 이들은 보통 독립 체류자격이라기보다 기존 체류자격의 트랙/운영제도임.
MANUAL_POLICY_TRACKS = {
    "overseas_korean_related": {
        "label": "외국국적동포 관련",
        "expected_terms": ["C-3-8", "F-1", "H-2", "F-4", "F-5", "외국국적동포", "재외동포", "방문취업"],
    },
    "regional_special_visa": {
        "label": "지역특화형비자",
        "expected_terms": ["지역특화형", "F-2-R", "F-4-R"],
    },
    "domestic_growth_youth": {
        "label": "국내 성장 기반 외국인 청소년 취업·정주 체류제도",
        "expected_terms": ["국내 성장", "외국인 청소년", "청소년"],
    },
    "top_tier_visa": {
        "label": "탑티어(Top-Tier) 비자",
        "expected_terms": ["Top-Tier", "탑티어", "D-10-T", "E-7-T", "F-2-T", "F-5-T"],
    },
    "wide_area_pilot": {
        "label": "광역형 비자 시범사업",
        "expected_terms": ["광역형", "시범사업"],
    },
    "k_star_track": {
        "label": "K-STAR 비자트랙 제도",
        "expected_terms": ["K-STAR", "KSTAR", "비자트랙"],
    },
}

DETAIL_CODE_RE = re.compile(r"\b[A-Z]-\d{1,2}(?:-[A-Z0-9]+)+\b")
TOP_CODE_RE = re.compile(r"\b[A-Z]-\d{1,2}\b")

def load_data() -> list[dict[str, Any]]:
    with VISA_DATA.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit("visa_data.json must be a list")
    return data

def norm_code(value: Any) -> str:
    return str(value or "").strip().upper()

def record_text(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True)

def collect_subcodes(record: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for sub in record.get("subCodes") or []:
        if isinstance(sub, dict) and sub.get("code"):
            out.append(norm_code(sub["code"]))
    return out

def main() -> None:
    data = load_data()

    top_codes = {norm_code(r.get("code")) for r in data if r.get("code")}
    top_names = {norm_code(r.get("code")): r.get("name", "") for r in data if r.get("code")}

    subcode_to_parents: dict[str, list[str]] = {}
    text_hit_to_records: dict[str, list[str]] = {}

    all_text_blob_parts: list[str] = []

    for record in data:
        parent = norm_code(record.get("code"))
        txt = record_text(record)
        all_text_blob_parts.append(txt)

        for subcode in collect_subcodes(record):
            subcode_to_parents.setdefault(subcode, []).append(parent)

        for code in sorted(set(DETAIL_CODE_RE.findall(txt))):
            text_hit_to_records.setdefault(code, []).append(parent)

    all_text = "\n".join(all_text_blob_parts)

    missing_top_level = {
        code: label
        for code, label in EXPECTED_LEGAL_TOP_LEVEL.items()
        if code not in top_codes
    }

    covered_top_level = {
        code: {
            "label": label,
            "name_in_visa_data": top_names.get(code, ""),
        }
        for code, label in EXPECTED_LEGAL_TOP_LEVEL.items()
        if code in top_codes
    }

    extra_top_level = sorted(
        code for code in top_codes
        if code
        and code not in EXPECTED_LEGAL_TOP_LEVEL
        and not code.startswith("SCN-")
        and not code.startswith("TB-")
        and code not in {"K-ETA"}
    )

    policy_track_coverage: dict[str, Any] = {}
    for key, spec in MANUAL_POLICY_TRACKS.items():
        terms = spec["expected_terms"]
        hits = []
        missing_terms = []
        for term in terms:
            if term.lower() in all_text.lower():
                hits.append(term)
            else:
                missing_terms.append(term)
        policy_track_coverage[key] = {
            "label": spec["label"],
            "hits": hits,
            "missing_terms": missing_terms,
            "covered": bool(hits),
        }

    f_1_6 = {
        "query": "F-1-6",
        "top_level_record_exists": "F-1-6" in top_codes,
        "subcode_parents": sorted(set(subcode_to_parents.get("F-1-6", []))),
        "text_hit_records": sorted(set(text_hit_to_records.get("F-1-6", []))),
        "interpretation": (
            "F-1-6 is not expected as an independent top-level legal stay status. "
            "It should be searchable as a subcode/reference/alias resolving to its parent or scenario record."
        ),
    }

    detail_codes = sorted(set(subcode_to_parents) | set(text_hit_to_records))
    detail_alias_candidates = []
    for code in detail_codes:
        if code not in top_codes and DETAIL_CODE_RE.match(code):
            detail_alias_candidates.append({
                "detail_code": code,
                "subcode_parents": sorted(set(subcode_to_parents.get(code, []))),
                "text_hit_records": sorted(set(text_hit_to_records.get(code, []))),
            })

    manual_files = {
        path: Path(path).exists()
        for path in CANONICAL_MANUAL_PATHS
    }

    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_basis": [
            "출입국관리법 시행령 별표 1 / 별표 1의2 체류자격 체계",
            "2026.5 체류민원 안내매뉴얼 목차 및 체류자격별 섹션",
            "2026.5 사증발급 안내매뉴얼",
            "HiKorea 체류자격별 안내메뉴얼 및 출입국관련 법령지침정보",
        ],
        "manual_files_present": manual_files,
        "expected_legal_top_level_count": len(EXPECTED_LEGAL_TOP_LEVEL),
        "covered_legal_top_level_count": len(covered_top_level),
        "missing_legal_top_level": missing_top_level,
        "extra_top_level_non_legal_or_review": extra_top_level,
        "policy_track_coverage": policy_track_coverage,
        "f_1_6_diagnosis": f_1_6,
        "detail_alias_candidate_count": len(detail_alias_candidates),
        "detail_alias_candidates": detail_alias_candidates,
        "guardrails": {
            "modified_visa_data": False,
            "automatic_legal_content_edits": False,
            "purpose": "coverage audit only; no source-content promotion",
        },
    }

    OUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines: list[str] = []
    lines.append("# Visa/Stay Status Coverage Audit - 2026.5")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("This audit compares `visa_data.json` against the legal top-level stay-status framework and the 2026.5 immigration manuals.")
    lines.append("")
    lines.append("This is an audit-only artifact. It does not edit `visa_data.json`, does not promote `verified=true`, and does not create new legal-content records.")
    lines.append("")
    lines.append("## Source basis")
    lines.append("")
    for item in result["source_basis"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Canonical manual files checked in repository")
    lines.append("")
    for path, exists in manual_files.items():
        mark = "present" if exists else "not found"
        lines.append(f"- `{path}`: {mark}")
    lines.append("")
    lines.append("## Legal top-level stay-status coverage")
    lines.append("")
    lines.append(f"- Expected legal top-level statuses: {len(EXPECTED_LEGAL_TOP_LEVEL)}")
    lines.append(f"- Covered in `visa_data.json`: {len(covered_top_level)}")
    lines.append(f"- Missing legal top-level statuses: {len(missing_top_level)}")
    lines.append("")
    if missing_top_level:
        lines.append("### Missing legal top-level statuses")
        lines.append("")
        for code, label in missing_top_level.items():
            lines.append(f"- `{code}` - {label}")
        lines.append("")
    else:
        lines.append("No missing legal top-level stay-status code was detected against the expected legal list.")
        lines.append("")
    if extra_top_level:
        lines.append("### Extra top-level records requiring classification review")
        lines.append("")
        for code in extra_top_level:
            lines.append(f"- `{code}`")
        lines.append("")
    else:
        lines.append("No unexpected non-scenario top-level code was detected outside the accepted helper/scenario records.")
        lines.append("")
    lines.append("## 2026.5 manual policy/track section coverage")
    lines.append("")
    for key, info in policy_track_coverage.items():
        status = "covered" if info["covered"] else "needs review"
        lines.append(f"- **{info['label']}**: {status}")
        if info["hits"]:
            lines.append(f"  - Hits: {', '.join(info['hits'])}")
        if info["missing_terms"]:
            lines.append(f"  - Terms not found: {', '.join(info['missing_terms'])}")
    lines.append("")
    lines.append("## F-1-6 diagnosis")
    lines.append("")
    lines.append(f"- Top-level `F-1-6` record exists: `{f_1_6['top_level_record_exists']}`")
    lines.append(f"- `subCodes[]` parents: `{', '.join(f_1_6['subcode_parents']) if f_1_6['subcode_parents'] else 'none'}`")
    lines.append(f"- Text-hit records: `{', '.join(f_1_6['text_hit_records']) if f_1_6['text_hit_records'] else 'none'}`")
    lines.append("")
    lines.append("Interpretation: `F-1-6` should not be treated as a missing independent top-level legal stay status unless a source explicitly defines it that way. It should be handled as a searchable detail code, subcode, alias, or scenario reference resolving to the relevant parent/scenario card.")
    lines.append("")
    lines.append("## Detail-code alias candidates")
    lines.append("")
    lines.append(f"- Detail code candidates not represented as top-level records: {len(detail_alias_candidates)}")
    lines.append("- These are candidates for a future search resolver patch, not automatic new `visa_data.json` records.")
    lines.append("")
    for item in detail_alias_candidates[:80]:
        parents = ", ".join(item["subcode_parents"]) if item["subcode_parents"] else "none"
        refs = ", ".join(item["text_hit_records"][:8]) if item["text_hit_records"] else "none"
        lines.append(f"- `{item['detail_code']}` - subcode parents: {parents}; text-hit records: {refs}")
    if len(detail_alias_candidates) > 80:
        lines.append(f"- ... {len(detail_alias_candidates) - 80} more candidates omitted from markdown; see JSON artifact.")
    lines.append("")
    lines.append("## Recommended next step")
    lines.append("")
    lines.append("Create a separate search-resolver PR so exact detail-code queries such as `F-1-6`, `F-2-7`, or `E-7-4` resolve to their parent/subcode/scenario records instead of returning an empty result.")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    lines.append("- No `visa_data.json` edits.")
    lines.append("- No backend edits.")
    lines.append("- No automatic legal-content creation.")
    lines.append("- No source verification promotion.")
    lines.append("- No deletion of scenario/helper records.")
    lines.append("")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "missing_legal_top_level_count": len(missing_top_level),
        "missing_legal_top_level": missing_top_level,
        "f_1_6": f_1_6,
        "detail_alias_candidate_count": len(detail_alias_candidates),
        "audit_md": str(OUT_MD),
        "audit_json": str(OUT_JSON),
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
