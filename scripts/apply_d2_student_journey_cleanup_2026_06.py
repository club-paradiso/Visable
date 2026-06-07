#!/usr/bin/env python3
"""One-shot D-2 student-journey golden-path data cleanup.

Scope: ONLY the D-2 record's four core procedure tabs
(visaIssuance, registration, extension, activitiesOutsideStatus).

This does not invent documents, does not remove source-backed documents,
and preserves every existing manualRefs block verbatim. It reorganizes the
already-present source-backed content into readable groups (common vs
conditional), moves guidance text out of the document list and into notes,
preserves the official 통합신청서(별지 제34호 서식) application form, and adds
concrete next-action guidance through the existing notes/eligibility render
fields (no frontend change required).

visa_data.json is canonical; run scripts/sync_visa_data.py afterwards.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "visa_data.json"


def load():
    raw = SOURCE.read_text(encoding="utf-8")
    return raw, json.loads(raw)


def main() -> int:
    raw, data = load()
    d2 = next((r for r in data if r.get("code") == "D-2"), None)
    if d2 is None:
        raise SystemExit("D-2 record not found")
    procs = d2.get("procedures") or {}

    # --- 1. visaIssuance: pre-entry / overseas visa issuance --------------
    vi = procs["visaIssuance"]
    vi["summary"] = (
        "[입국 전 · 재외공관 신청] 유학(D-2) 사증은 한국 입국 전에 거주지 관할 "
        "재외공관(대사관·총영사관)에서 신청합니다. 표준입학허가서, 최종학력"
        "(아포스티유/영사확인), 재정능력 입증, 결핵진단서(고위험국 해당자)를 "
        "준비합니다. 입국 후의 외국인등록·체류기간 연장과는 별개의 절차입니다."
    )
    # Documents are already source-backed and well grouped; keep as-is.
    vi["notes"] = [
        "다음 단계: ① 입학할 학교에서 표준입학허가서를 발급받기 → "
        "② 학력·재정·결핵진단서 등 사증서류를 준비 → "
        "③ 거주지 관할 재외공관에 D-2 사증을 신청.",
        "세부 제출서류는 국적·학교·과정(D-2-1~D-2-8)에 따라 가감될 수 있어 "
        "관할 재외공관과 사증민원 매뉴얼 확인이 필요합니다.",
    ]

    # --- 2. registration: post-entry / domestic ARC registration ---------
    reg = procs["registration"]
    reg["summary"] = (
        "[입국 후 · 국내 체류절차] 유학(D-2)으로 입국한 학생은 입국일로부터 "
        "90일 이내에 체류지 관할 출입국·외국인관서에서 외국인등록(ARC 발급)을 "
        "해야 합니다. 외국인등록과 동시에 체류기간 연장허가를 신청하는 경우에 "
        "한해 연장 수수료가 면제됩니다."
    )
    reg["requiredDocs"] = {
        "commonDocs": [
            "통합신청서(별지 제34호 서식)",
            "doc_passport_generic",
            "doc_passport_copy",
            "doc_standard_photo_one",
            "doc_fee_generic",
        ],
        "requiredDocs": [
            "재학(연구생)증명서 또는 등록금납입증명서 등 대체서류",
            "doc_residence_proof_generic",
        ],
        "additionalDocs": [],
        "conditionalDocs": [
            "(인증대학 이상) 등록금납입증명서로 재학증명 대체 가능",
            "(일반대학 이하) 협조요청서 및 등록금납입증명서 또는 "
            "단체접수 등록금납입증명서",
        ],
    }
    reg["notes"] = [
        "유학(D-2) 외국인등록 시 재정능력 입증서류는 제출 불요입니다"
        "(기관·국적·체류 이력별 예외가 있을 수 있어 확인 필요).",
        "외국인등록증 발급·재발급 수수료는 수수료 면제 대상자도 납부해야 할 수 "
        "있습니다.",
        "다음 단계: ① HiKorea(hikorea.go.kr)에서 방문 예약 → "
        "② 체류지 관할 출입국·외국인관서 방문(입국 후 90일 이내) → "
        "③ 재학 중인 대학 국제처(외국인 유학생 담당)에서 제출서류·발급 절차 확인.",
        "2026.5 체류민원 매뉴얼에서 보수적으로 정리한 제출서류입니다. "
        "세부약호·국적·기관·체류 이력별 예외가 있어 최종 확인이 필요합니다.",
    ]

    # --- 3. extension: common vs conditional documents -------------------
    ext = procs["extension"]
    ext["summary"] = (
        "[입국 후 · 국내 체류절차] 유학(D-2) 체류기간 연장은 체류기간 만료 전에 "
        "신청합니다. 체류기간은 학사일정(재학·수료 예정일 등)을 기준으로 부여되며, "
        "학업 수행 실적(성적·출석)과 재정·체류지 입증이 함께 검토됩니다."
    )
    ext["requiredDocs"] = {
        "commonDocs": [
            "통합신청서(별지 제34호 서식)",
            "doc_passport_generic",
            "외국인등록증",
            "doc_fee_generic",
        ],
        "requiredDocs": [
            "학업 수행 입증서류(재학증명서, 성적증명서, 출석확인서 등)",
            "재정입증 서류",
            "체류지 입증서류(임대차계약서, 숙소제공 확인서, 체류기간 만료예고 "
            "통지우편물, 공공요금 납부영수증, 기숙사비 영수증 등)",
        ],
        "additionalDocs": [],
        "conditionalDocs": [
            "수료(예정)·논문학기 등 해당자: 수료증명서, 지도교수 및 유학담당자 "
            "확인서",
        ],
    }
    ext["notes"] = [
        "다음 단계: ① 체류기간 만료 전(보통 만료 4개월 전부터 신청 가능) "
        "HiKorea에서 연장 신청 또는 방문 예약 → "
        "② 성적·출석 등 학업 수행 요건 충족 여부를 대학 국제처와 확인 → "
        "③ 재정·체류지 입증서류를 최신 발급본으로 준비.",
        "체류기간 만료일을 넘기면 불이익이 있을 수 있으니 만료 전에 신청하세요. "
        "최종 허가 기간·요건은 심사 결과에 따라 달라집니다.",
        "2026.5 체류민원 매뉴얼에서 보수적으로 정리한 제출서류입니다. "
        "세부약호·국적·기관·체류 이력별 예외가 있어 최종 확인이 필요합니다.",
    ]

    # --- 4. activitiesOutsideStatus: part-time work permission -----------
    # No clean source-backed document list exists for this tab, so we do NOT
    # invent document rows. Instead we make the section genuinely useful via
    # eligibility (who/conditions) + summary + notes (next actions + the one
    # source-limited notice), all of which already render.
    aos = procs["activitiesOutsideStatus"]
    aos["summary"] = (
        "[자격외활동 허가 필요] 유학(D-2) 학생이 시간제취업(아르바이트 등) 등 "
        "본래 체류자격 외의 활동을 하려면 사전에 자격외활동 허가를 받아야 합니다. "
        "허용 시간·업종은 학년·과정·한국어능력(TOPIK·KIIP 등) 등에 따라 "
        "제한됩니다."
    )
    aos["eligibility"] = [
        "학생 본인: 학업을 성실히 이수(출석·성적)하고 있어야 하며, 일부 유형은 "
        "입국·등록 후 6개월 경과 등 요건이 적용될 수 있습니다.",
        "학교(국제처): 시간제취업 확인·추천 등 학교 측 확인이 필요할 수 있습니다.",
        "근무처(고용주): 허가받은 업종·시간 범위 내에서만 근무해야 하며, "
        "근무처·근로조건 확인이 필요합니다.",
    ]
    aos["notes"] = [
        "다음 단계: ① 재학 중인 대학 국제처에서 시간제취업 가능 여부·확인서 "
        "발급 절차 문의 → ② HiKorea에서 자격외활동 허가 신청(또는 방문 예약) → "
        "③ 허가받은 범위(시간·업종) 내에서만 근무.",
        "허용 시간·업종, 한국어능력 기준 등 세부 요건은 D-2 세부 유형별로 달라 "
        "2026.5 체류민원 매뉴얼·HiKorea·1345에서 확인이 필요합니다.",
    ]

    out = json.dumps(data, ensure_ascii=False, indent=2)
    if raw.endswith("\n"):
        out += "\n"
    SOURCE.write_text(out, encoding="utf-8")
    print("Updated D-2 procedures: visaIssuance, registration, extension, "
          "activitiesOutsideStatus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
