#!/usr/bin/env python3
"""Resolve the D-4-2K code collision in visa_data.json (2026.5 manual-grounded).

Background
----------
visa_data.json shipped TWO top-level records that used the same ``code``
value ``"D-4-2K"`` (array indices 24 and 55), plus a D-4 sub-code also
labelled ``D-4-2K``. The 2026.5 외국인체류 안내매뉴얼 (Foreigner Stay Guide
Manual) is unambiguous about what these codes mean:

  * ``D-4-2K`` = 기업 맞춤형 인턴십 (K-Trainee)        [stay manual pp. 91-92, 94]
  * 한국어연수 (Korean-language training) = ``D-4-1`` (대학부설어학원),
    외국어연수 = ``D-4-7``                             [stay manual pp. 83, 90-91]

Because both ``index.html`` (the viewer) and ``ai.html`` (the analyzer)
resolve a record with ``VISA_DATA.find(v => v.code === code)`` — first match
wins — the SECOND ``D-4-2K`` record (the real K-Trainee entry) was
unreachable in both the viewer and the analyzer. The repo's own
domain-classification audit
(docs/data/2026_05_21_visa_data_domain_classification.json) flagged this as a
deferred "DUPLICATE CODE (indices 24 & 55) ... resolution via separate
D-content PR (do not delete)". This script is that resolution.

Fix
---
1. D-4 parent sub-code ``D-4-2K``: relabel 한국어연수(K-연수생) -> K-Trainee.
2. Index-24 record (한국어연수): recode ``D-4-2K`` -> ``D-4-1`` and replace its
   cross-section-bled extension docs with the manual's 어학연수생
   (D-4-1, D-4-7) "나. 제출서류" list (p. 91).
3. Index-55 record (K-Trainee): keep ``D-4-2K``, replace the wrongly-bled
   language-trainee extension text with the manual's K-Trainee extension
   (pp. 91-92) and foreigner-registration (p. 94) document lists.

All document lists below are transcribed from the committed source PDF
``docs/source-manuals/2026-05/stay_manual_2026_05.pdf``. The script is
deterministic and asserts its pre-conditions, so re-running it on an
already-patched file is a no-op that exits 0.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VISA = ROOT / "visa_data.json"

# --- Manual-transcribed content (stay_manual_2026_05.pdf) --------------------

# 어학연수생(한국어연수 D-4-1, 외국어연수 D-4-7) 체류기간 연장 — "나. 제출서류" (p. 91)
LANG_TRAINEE_EXT_SUMMARY = (
    "어학연수생(한국어연수 D-4-1, 외국어연수 D-4-7)에 대한 체류기간 연장허가. "
    "개인적 사정·학점미달 등으로 학업을 중단(휴학)한 경우 연장이 제한되며, "
    "질병·사고 등 부득이한 사유는 예외적으로 인정됩니다. 어학원 폐쇄 등 본인 "
    "귀책이 아닌 경우 또는 TOPIK 3급(KIIP) 이상 성적표 소지자는 일반대 이상으로의 "
    "학교 변경이 예외적으로 허용됩니다."
)
LANG_TRAINEE_EXT_DOCS = [
    "신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료",
    "재학을 입증하는 서류(재학증명서, 교환학생 연장증명서, 연구생 증명서 등)",
    "학업을 정상적으로 수행하고 있음을 입증하는 서류(성적증명서, 출석확인서 등)",
    "재정입증 서류(국내 본인계좌 예치금만 인정)",
    "모집요강(연수일정 명시) 또는 연수계획서(어학연수생에 한함)",
    "체류지 입증서류(임대차계약서, 숙소제공 확인서, 체류기간 만료예고 통지우편물, "
    "공공요금 납부영수증, 기숙사비 영수증 등)",
]
LANG_TRAINEE_EXT_NOTE = (
    "2026.5 외국인체류 안내매뉴얼 p.91 '어학연수생(D-4-1, D-4-7) 체류기간 "
    "연장허가 — 나. 제출서류'에서 옮긴 제출서류입니다. 세부 사정에 따라 "
    "가감될 수 있어 관할 출입국·외국인관서 확인이 필요합니다."
)

# 기업 맞춤형 인턴십(K-Trainee, D-4-2K) 체류기간연장 (pp. 91-92, 항목 2)
KTRAINEE_EXT_SUMMARY = (
    "기업 맞춤형 인턴십(K-Trainee, D-4-2K)의 체류기간연장. 인턴기간은 원칙적으로 "
    "6개월을 초과할 수 없으나, 추가로 필요하다고 인정되는 경우 입국한 날부터 "
    "1년을 초과하지 않는 한도 내에서 기간 연장이 가능합니다."
)
KTRAINEE_EXT_DOCS = [
    "신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료",
    "체류지 입증서류",
    "기간연장 사유서 및 인턴·연수 활동 계획서",
]
KTRAINEE_EXT_NOTE = (
    "2026.5 외국인체류 안내매뉴얼 pp.91-92 '기업 맞춤형 인턴십(K-Trainee, "
    "D-4-2K)의 체류기간연장 제출서류'에서 옮긴 제출서류입니다."
)

# 기업 맞춤형 인턴십(K-Trainee, D-4-2K) 외국인등록 (p. 94, 항목 4)
KTRAINEE_REG_SUMMARY = "기업 맞춤형 인턴십(K-Trainee, D-4-2K)의 외국인등록 제출서류."
KTRAINEE_REG_DOCS = [
    "신청서(별지 제34호 서식), 여권, 사진(6개월 내 촬영 반명함) 1장, 수수료",
    "체류지 입증서류",
    "기업 맞춤형 인턴십(D-4-2K) 자격 소지자는 매뉴얼 붙임 1·2 안내문 참고",
]
KTRAINEE_REG_NOTE = (
    "2026.5 외국인체류 안내매뉴얼 p.94 '기업 맞춤형 인턴십(K-Trainee, D-4-2K) "
    "제출서류'(외국인등록)에서 옮긴 제출서류입니다."
)


def _manual_ref(page_range: str) -> dict:
    return {
        "manualName": "체류민원",
        "manualVersion": "2026.5",
        "pageRange": page_range,
        "confidence": "manual_page_extract_needs_review",
        "needsManualReview": True,
    }


def _doc_group(docs: list[str]) -> dict:
    return {
        "commonDocs": [],
        "requiredDocs": list(docs),
        "additionalDocs": [],
        "conditionalDocs": [],
    }


def fix_d4_parent_subcode(record: dict) -> bool:
    changed = False
    for sub in record.get("subCodes") or []:
        if sub.get("code") == "D-4-2K" and "한국어연수" in (sub.get("name") or ""):
            sub["name"] = "기업 맞춤형 인턴십(K-Trainee)"
            changed = True
    return changed


def fix_language_trainee_record(record: dict) -> None:
    """Index-24 record: recode D-4-2K -> D-4-1 (한국어연수, 대학부설어학원)."""
    record["code"] = "D-4-1"
    record["name"] = "한국어연수 (대학부설어학원)"
    record["aliases"] = ["한국어연수", "대학부설어학원", "D-4-1"]
    record["extReq"] = LANG_TRAINEE_EXT_SUMMARY

    ext = record["procedures"]["extension"]
    ext["available"] = True
    ext["summary"] = LANG_TRAINEE_EXT_SUMMARY
    ext["requiredDocs"] = _doc_group(LANG_TRAINEE_EXT_DOCS)
    ext["notes"] = [LANG_TRAINEE_EXT_NOTE]
    ext["manualRefs"] = [_manual_ref("pp. 90-91")]

    ref = record.get("structuredRequirementsRef")
    if isinstance(ref, dict):
        ref["mappingNote"] = "D-4-1 evidence is represented under structured statusCode D-4"


def fix_ktrainee_record(record: dict) -> None:
    """Index-55 record: keep D-4-2K, install the real K-Trainee doc lists."""
    record["extReq"] = KTRAINEE_EXT_SUMMARY

    ext = record["procedures"]["extension"]
    ext["available"] = True
    ext["summary"] = KTRAINEE_EXT_SUMMARY
    ext["requiredDocs"] = _doc_group(KTRAINEE_EXT_DOCS)
    ext["notes"] = [KTRAINEE_EXT_NOTE]
    ext["manualRefs"] = [_manual_ref("pp. 91-92")]

    reg = record["procedures"]["registration"]
    reg["available"] = True
    reg["summary"] = KTRAINEE_REG_SUMMARY
    reg["requiredDocs"] = _doc_group(KTRAINEE_REG_DOCS)
    reg["notes"] = [KTRAINEE_REG_NOTE]
    reg["manualRefs"] = [_manual_ref("p. 94")]


def main() -> int:
    original = VISA.read_text(encoding="utf-8")
    data = json.loads(original)

    d4_parent = next((r for r in data if r.get("code") == "D-4"), None)
    assert d4_parent is not None, "D-4 parent record not found"

    lang_records = [
        r for r in data
        if r.get("code") == "D-4-2K" and "한국어연수" in (r.get("name") or "")
    ]
    ktrainee_records = [
        r for r in data
        if r.get("code") == "D-4-2K" and "K-Trainee" in (r.get("name") or "")
    ]

    already_patched = (
        not lang_records
        and any(r.get("code") == "D-4-1" and "대학부설어학원" in (r.get("name") or "")
                for r in data)
    )
    if already_patched:
        print("No change: visa_data.json already resolved (D-4-1 / D-4-2K).")
        return 0

    assert len(lang_records) == 1, f"expected 1 한국어연수 D-4-2K record, found {len(lang_records)}"
    assert len(ktrainee_records) == 1, f"expected 1 K-Trainee D-4-2K record, found {len(ktrainee_records)}"

    fix_d4_parent_subcode(d4_parent)
    fix_language_trainee_record(lang_records[0])
    fix_ktrainee_record(ktrainee_records[0])

    # Post-conditions: no duplicate top-level codes remain.
    codes = [r.get("code") for r in data]
    dupes = {c for c in codes if codes.count(c) > 1}
    assert not dupes, f"duplicate codes still present after fix: {dupes}"
    assert codes.count("D-4-2K") == 1, "D-4-2K must appear exactly once (K-Trainee)"
    assert codes.count("D-4-1") == 1, "D-4-1 (한국어연수) must appear exactly once"

    VISA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Patched visa_data.json:")
    print("  - D-4 sub-code D-4-2K relabelled to 기업 맞춤형 인턴십(K-Trainee)")
    print("  - index-24 한국어연수 recoded D-4-2K -> D-4-1 (manual p.91 docs)")
    print("  - index-55 K-Trainee D-4-2K extension/registration docs (manual pp.91-92, 94)")
    print(f"  - top-level records: {len(data)}; duplicate codes: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
