#!/usr/bin/env python3
"""Fill three empty foreigner-registration (외국인등록) document lists from
page-level evidence in the committed 2026.5 stay manual.

Scope (Phase 3, high-confidence only):
  * E-10 (선원취업) registration  — stay manual pp. 338-339, "외국인등록 / 1. 외국인등록 신청서류"
  * D-8  (기업투자) registration  — stay manual p. 126,     "외국인등록 / 1. 외국인등록 신청서류"
  * H-1  (관광취업) registration  — stay manual p. 517,     "외국인등록 / 제출서류" (협정상 예외 없음)

Each manual section presents ONE registration document list at the parent
status level (it is not split per sub-code), so reproducing it at the
parent `procedures.registration` does not flatten scenario-specific
requirements. Document strings reproduce the manual wording; the universal
common items reuse existing doc_master.json token ids. Records stay
`needsManualReview: true`; the per-procedure manualRef confidence is raised
from the vague "needs_manual_review" (wide page range) to the existing
"manual_page_extract_needs_review" value with a precise page + section.

This script is idempotent and asserts the pre-state (empty requiredDocs)
so it cannot silently overwrite richer data. It updates only
visa_data.json; run scripts/sync_visa_data.py afterwards.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "visa_data.json"

STAY_FILE = "docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf"

FILLS = {
    "E-10": {
        "page": "pp. 338-339",
        "section": "외국인등록 신청서류",
        "requiredDocs": {
            "commonDocs": [
                "신청서(별지 제34호 서식)",
                "여권 원본",
                "doc_standard_photo_one",
                "doc_fee_generic",
            ],
            "requiredDocs": [
                "내항여객운송사업면허증 또는 내항화물운송등록증",
                "건강검진서(밀봉된 상태로 제출, 개봉 불가)",
                "마약검사 확인서(밀봉된 상태로 제출, 개봉 불가)",
                "산업재해보상보험 또는 상해보험 가입증명원",
                "doc_residence_proof_generic",
            ],
            "additionalDocs": [],
            "conditionalDocs": [],
        },
        "note": (
            "외국인등록 제출서류는 2026.5 체류민원 매뉴얼 pp. 338-339 "
            "'외국인등록 신청서류' 항목에서 직접 정리했습니다. 일부 서류는 "
            "선종(내항·어선·순항)·근무처 형태에 따라 달라질 수 있어 관할 "
            "출입국·외국인관서에서 최종 확인이 필요합니다."
        ),
    },
    "D-8": {
        "page": "p. 126",
        "section": "외국인등록 신청서류",
        "requiredDocs": {
            "commonDocs": [
                "신청서(별지 제34호 서식)",
                "여권 원본",
                "doc_standard_photo_one",
                "doc_fee_generic",
            ],
            "requiredDocs": [
                "사업자등록증",
                "체류지 입증서류(부동산 임대차계약서 등)",
            ],
            "additionalDocs": [],
            "conditionalDocs": [
                "법인 등기사항전부증명서(법인기업인 경우)",
            ],
        },
        "note": (
            "외국인등록 제출서류는 2026.5 체류민원 매뉴얼 p. 126 "
            "'외국인등록 신청서류' 항목에서 직접 정리했습니다. 재외공관에서 "
            "기업투자(D-8) 자격을 직접 받아 입국한 경우에는 체류자격 변경신청 "
            "제출서류를 준용하며, 세부 사항은 관할 출입국·외국인관서에서 "
            "최종 확인이 필요합니다."
        ),
    },
    "H-1": {
        "page": "p. 517",
        "section": "외국인등록 제출서류",
        "requiredDocs": {
            "commonDocs": [
                "신청서(별지 제34호 서식)",
                "doc_passport_generic",
                "doc_standard_photo_one",
                "doc_fee_generic",
            ],
            "requiredDocs": [
                "여행일정 및 활동계획서",
                "체류지 입증서류(월세계약서 등)",
            ],
            "additionalDocs": [],
            "conditionalDocs": [
                "근무처의 사업자등록증 사본 및 계약서 등(취업 중인 경우)",
            ],
        },
        "note": (
            "외국인등록 제출서류는 2026.5 체류민원 매뉴얼 p. 517 관광취업(H-1) "
            "'외국인등록 / 제출서류' 항목(90일 초과 체류자 대상, 협정상 예외 없음)에서 "
            "직접 정리했습니다(타 자격에서 빌려온 목록이 아님). 세부 사항은 관할 "
            "출입국·외국인관서에서 최종 확인이 필요합니다."
        ),
    },
}


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    by_code = {v.get("code"): v for v in data}

    changed = []
    for code, spec in FILLS.items():
        v = by_code.get(code)
        if v is None:
            raise SystemExit(f"{code}: record not found")
        reg = (v.get("procedures") or {}).get("registration")
        if not isinstance(reg, dict):
            raise SystemExit(f"{code}: procedures.registration missing")

        rd = reg.get("requiredDocs") or {}
        total = sum(len(rd.get(k, []) or []) for k in
                    ("commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs"))
        if total != 0:
            # Idempotency / safety: refuse to overwrite already-populated docs.
            print(f"SKIP {code}: registration.requiredDocs already populated "
                  f"({total} entries) — not overwriting.")
            continue

        reg["requiredDocs"] = spec["requiredDocs"]

        # Tighten the manualRef to the precise verified page + section.
        refs = reg.get("manualRefs") or []
        if refs and isinstance(refs[0], dict):
            ref = refs[0]
        else:
            ref = {
                "manualName": "체류민원",
                "manualVersion": "2026.5",
                "sourceDate": "2026-06-01",
                "sourceFile": STAY_FILE,
            }
            reg["manualRefs"] = [ref]
        ref["pageRange"] = spec["page"]
        ref["section"] = spec["section"]
        ref["confidence"] = "manual_page_extract_needs_review"
        ref["needsManualReview"] = True
        ref["sourceFile"] = STAY_FILE

        # Append a source note without weakening existing caution notes.
        notes = reg.setdefault("notes", [])
        if spec["note"] not in notes:
            notes.append(spec["note"])

        # Reflect the precise section range in the per-record audit block.
        audit = v.get("manualRequiredDocAudit")
        if isinstance(audit, dict):
            audit["registrationDocsPage"] = spec["page"]
            audit["registrationDocsSection"] = spec["section"]
            audit["registrationDocsMethod"] = "pdf_text_manual_page_verified"
            audit["registrationDocsUpdatedAt"] = "2026-06-07"

        changed.append(code)

    if changed:
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        print("Updated registration docs for:", ", ".join(changed))
    else:
        print("No changes applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
