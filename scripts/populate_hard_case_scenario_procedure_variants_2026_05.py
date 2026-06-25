#!/usr/bin/env python3
"""Populate hard-case scenario procedure variants from the 2026.6 stay manual.

This helper is additive and idempotent. It layers a third batch of
scenario/sub-code-scoped procedure variants on top of the batch-1 records
(``populate_scenario_procedure_variants_2026_05.py``) and batch-2 records
(``populate_scenario_procedure_variants_batch2_2026_05.py``). Existing
variants from any batch are preserved; a differing variant with the same id is
refused rather than overwritten, and existing parent-level procedure fields
(e.g. F-6's pre-existing ``statusChange`` shell) are left untouched.

It targets high-value hard cases that earlier batches deferred — change-of-
status (체류자격 변경허가) scenarios for結婚이민(F-6), 기타(G-1) humanitarian
sub-codes, and 거주(F-2) family sub-codes. Every variant is transcribed from the
official 2026.6 stay manual PDF text already committed in the repository
(``backend/data/sources/manuals/260623_stay_manual_readable.txt``) and carries a
provable printed-page citation verified with
``scripts/extract_manual_page_text.py`` (footer "- N -" == printed page N).

The records are intentionally scenario- or sub-code-scoped. They must not be
promoted into parent-level requiredDocs lists, marked verified, or treated as
source-confirmed HIGH determinations. Each retains
``needsManualReview: true`` and only labels a candidate document set whose
applicability depends on the individual's specific facts.

Usage:
    python3 scripts/populate_hard_case_scenario_procedure_variants_2026_05.py
    python3 scripts/populate_hard_case_scenario_procedure_variants_2026_05.py --check
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "visa_data.json"
TARGET = ROOT / "backend" / "data" / "visas.json"
SOURCE_FILE = "backend/data/sources/manuals/260623_stay_manual_readable.txt"
SOURCE_PDF = "backend/data/sources/manuals/260623_stay_manual_exported.pdf"
SOURCE_ID = "stay_manual_2026_06_23_pdf"
SCOPE_NOTE = "세부 자격 또는 신청 사유에 따라 제출서류가 달라질 수 있습니다."

EMPTY_DOCS = {
    "commonDocs": [],
    "requiredDocs": [],
    "additionalDocs": [],
    "conditionalDocs": [],
}

PROCEDURE_SUMMARIES = {
    "statusChange": "체류자격변경 제출서류는 세부 자격과 신청 사유별로 다릅니다.",
    "workplaceChange": "근무처 변경·추가 제출서류는 세부 자격과 신청 사유별로 다릅니다.",
    "activitiesOutsideStatus": "체류자격외활동 제출서류는 활동 유형과 신청 사유별로 다릅니다.",
    "statusGrant": "체류자격부여 제출서류는 신청 사유와 가족관계별로 다릅니다.",
}


def docs(
    required: list[str],
    *,
    common: list[str] | None = None,
    additional: list[str] | None = None,
    conditional: list[str] | None = None,
) -> dict[str, list[str]]:
    return {
        "commonDocs": common or [],
        "requiredDocs": required,
        "additionalDocs": additional or [],
        "conditionalDocs": conditional or [],
    }


def variant(
    parent: str,
    procedure: str,
    variant_id: str,
    label: str,
    scenario: str,
    page_range: str,
    required_docs: dict[str, list[str]],
    *,
    status_code: str | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "parent": parent,
        "procedure": procedure,
        "variant": {
            "id": variant_id,
            "labelKo": label,
            "scenarioKo": scenario,
            "requiredDocs": required_docs,
            "manualRefs": [
                {
                    "manualName": "체류민원",
                    "manualVersion": "2026.6",
                    "pageRange": page_range,
                    "sourceFile": SOURCE_FILE,
                    "sourcePdf": SOURCE_PDF,
                    "sourceId": SOURCE_ID,
                    "confidence": "manual_extracted_needs_review",
                    "needsManualReview": True,
                }
            ],
            "notes": notes or [],
        },
    }
    if status_code:
        record["variant"]["statusCode"] = status_code
    return record


VARIANTS = [
    # ============================================================ 결혼이민(F-6)
    # F-6-2 자녀양육 (child-rearing) change of status — printed page 488.
    variant(
        "F-6",
        "statusChange",
        "f-6-2-child-rearing-status-change",
        "자녀양육자(F-6-2) 체류자격 변경허가",
        "결혼이민(F-6) 이외의 자격으로 체류 중인 사람이 국민과 혼인관계(사실상의 혼인관계 포함)에서 출생한 "
        "미성년 자녀를 국내에서 양육하는 부 또는 모로서 결혼이민(F-6-2)으로 변경하는 경우",
        "p. 488",
        docs(
            [
                "자녀가 국민인 경우 자녀 명의의 기본증명서·가족관계증명서",
                "가족(친자)관계 입증서류(출생증명서, 유전자검사 확인 서류 등)",
                "자녀양육 입증서류(양육권 관련 판결문, 자녀가 등재된 주민등록등본, "
                "자녀의 5촌 이내 한국인 친척이나 주거지 통·반장의 확인서 등)",
                "범죄경력증명서 및 건강진단서(旣제출자로서 해외 6개월 이상 연속 체류 사실이 없는 자는 면제)",
                "그 밖에 심사에 필요하다고 인정되는 서류",
            ],
            common=["신청서(별지 제34호 서식), 여권, 외국인등록증(해당자), 표준규격사진 1매, 수수료"],
            conditional=["혼인단절자(이혼·사망·실종 등)의 경우 그 사유를 입증하는 서류(해당자에 한함)"],
        ),
        status_code="F-6-2",
        notes=[
            "국민과의 혼인관계에서 출생한 미성년 자녀를 양육하는 부·모의 결혼이민(F-6-2) 변경 시나리오에만 적용됩니다.",
            "체류허가기간은 1년이며, 변경 가능 여부는 개별 심사로 결정됩니다.",
        ],
    ),
    # F-6-3 혼인단절자(사망·실종·이혼) change of status — printed pages 488-489.
    variant(
        "F-6",
        "statusChange",
        "f-6-3-marriage-terminated-status-change",
        "혼인단절자(F-6-3) 체류자격 변경허가",
        "결혼이민(F-6) 이외의 자격으로 체류 중 정상적인 혼인생활을 유지하다가 한국인 배우자의 사망·실종 또는 "
        "본인에게 책임 없는 사유로 혼인이 단절되어 혼인단절자(F-6-3)로 변경하는 경우",
        "pp. 488-489",
        docs(
            [
                "범죄경력증명서 및 건강진단서(旣제출자로서 해외 6개월 이상 연속 체류 사실이 없는 자는 면제)",
                "그 밖에 심사에 필요하다고 인정되는 서류",
            ],
            common=["신청서(별지 제34호 서식), 여권, 외국인등록증, 표준규격사진 1매, 수수료"],
            conditional=[
                "[사망] 배우자의 사망 입증서류(사망진단서, 배우자의 사망사실이 기재된 기본증명서 등), 가족관계 입증서류(혼인관계증명서 등)",
                "[이혼] 이혼사실이 기재된 혼인관계증명서, 이혼 관련 소송서류(소장, 이혼 판결문 등), "
                "귀책사유 입증자료(배우자의 가출신고서, 폭행 등 병원 진단서, 검찰 불기소결정문, 공인된 여성관련 단체 확인서, "
                "국민 배우자의 4촌 이내 친척 확인서, 혼인관계 중단 당시 거주지 통·반장 확인서 등)",
                "[실종] 실종사실 증명서류(실종선고심판서), 가족관계 입증서류(혼인관계증명서 등)",
            ],
        ),
        status_code="F-6-3",
        notes=[
            "사망·실종·이혼 등 혼인단절 사유에 본인의 책임이 없어야 하며, 사유별로 제출서류가 달라집니다.",
            "단기체류자·형사범·출국을 위한 연장허가자 등 제한 대상에 해당하면 변경이 제한될 수 있습니다.",
            "신청 당시 국민의 배우자(F-6-1)로 체류 중인 경우에는 변경이 아니라 체류기간 연장허가 대상입니다.",
        ],
    ),
    # ================================================================= 기타(G-1)
    # 체류자격 변경허가 — humanitarian / protected-stay sub-codes, pages 504-507.
    variant(
        "G-1",
        "statusChange",
        "g-1-1-industrial-accident-status-change",
        "산업재해 청구·치료자(G-1-1) 체류자격 변경허가",
        "산재보상심사 청구·재심청구 중이거나 산재로 입원·요양·후유증상 치료 중인 사람 및 그 가족이 "
        "기타(G-1-1)로 변경하는 경우",
        "p. 504",
        docs(
            [
                "산재보상심사청구서 또는 재심청구서",
                "산재로 인한 병원 진단서 등",
                "생계유지능력 심사확인서",
            ],
            common=["신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료"],
            conditional=["가족관계 및 기타 보호자 입증서류(가족 동반 시에 한함)"],
        ),
        status_code="G-1-1",
        notes=["산업재해 청구·치료 중인 사람과 그 가족의 변경 시나리오에만 적용됩니다. 체류허가기간은 1년 범위 내입니다."],
    ),
    variant(
        "G-1",
        "statusChange",
        "g-1-2-illness-treatment-status-change",
        "질병·사고 치료자(G-1-2) 체류자격 변경허가",
        "체류 중 각종 질병·사고로 장기치료가 필요하여 기존 체류자격을 유지할 수 없는 사람 및 그 가족이 "
        "기타(G-1-2)로 변경하는 경우",
        "pp. 504-505",
        docs(
            [
                "의료기관에서 발행한 소견서 등 장기치료의 필요성을 입증하는 서류",
                "치료 및 체류 비용 조달 능력을 입증하는 서류",
                "신원보증서",
                "생계유지능력 심사확인서",
            ],
            common=["신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료"],
            conditional=["가족관계 입증서류(배우자 또는 직계가족 동반 시에 한함)"],
        ),
        status_code="G-1-2",
        notes=[
            "장기치료가 필요한 사람과 그 가족의 변경 시나리오에만 적용됩니다.",
            "단기사증(B-1·B-2·C-3)으로 입국 후 장기치료가 필요한 경우는 외국인환자(G-1-10) 변경 대상일 수 있습니다.",
        ],
    ),
    variant(
        "G-1",
        "statusChange",
        "g-1-3-litigation-status-change",
        "각종 소송 진행자(G-1-3) 체류자격 변경허가",
        "산업재해 손해배상·전세금반환 등 민사소송, 공판 진행 중인 형사소송, 가사·행정소송을 "
        "수행 중인 사람이 기타(G-1-3)로 변경하는 경우",
        "p. 505",
        docs(
            [
                "소장 사본, 소송제기 증명원, 법률구조결정서 사본, 기타 청구권의 존재를 확인할 수 있는 서류",
                "신원보증서",
                "생계유지능력 심사확인서",
            ],
            common=["신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료"],
            conditional=["가족관계 또는 보호자 입증서류(보호자·가족에 한함)"],
        ),
        status_code="G-1-3",
        notes=["각종 소송 수행 중인 사람의 변경 시나리오에만 적용됩니다. 체류허가기간은 6개월 범위 내입니다."],
    ),
    variant(
        "G-1",
        "statusChange",
        "g-1-4-wage-claim-status-change",
        "임금체불 중재자(G-1-4) 체류자격 변경허가",
        "고용노동부에 체불임금 진정을 접수하여 중재 중이거나 미해결로 민사소송 중인 사람이 "
        "기타(G-1-4)로 변경하는 경우",
        "pp. 505-506",
        docs(
            [
                "노동부 제출 진정서 사본",
                "노동부 발급 체불금품 확인원 등",
                "신원보증서",
                "생계유지능력 심사확인서(체류기간 연장 심사 시 활용)",
            ],
            common=["신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료"],
        ),
        status_code="G-1-4",
        notes=["체불임금 진정·중재 중인 사람의 변경 시나리오에만 적용됩니다. 체류허가기간은 6개월 범위 내입니다."],
    ),
    variant(
        "G-1",
        "statusChange",
        "g-1-5-6-refugee-humanitarian-status-change",
        "난민신청자(G-1-5)·인도적체류허가자(G-1-6) 체류자격 변경허가",
        "대한민국 안에서 난민인정을 신청한 사람(G-1-5) 또는 난민불인정자 중 인도적 체류허가를 받은 사람"
        "(G-1-6)이 기타(G-1)로 변경하는 경우",
        "p. 506",
        docs(
            [
                "난민인정신청 접수증 등 난민신청자 또는 인도적 체류허가자임을 입증할 수 있는 서류",
                "체류지 입증서류(임대차계약서, 숙소제공 확인서, 공공요금 납부영수증, 교회·난민지원시설·인권단체·UNHCR 등의 주거확인서 등)",
            ],
            common=["신청서(별지 제34호 서식), 여권 및 외국인등록증, 표준규격사진 1매, 수수료"],
        ),
        notes=[
            "난민신청 또는 인도적 체류허가 사실에 한정된 변경 시나리오이며, 난민 인정 여부나 그 결과를 의미하지 않습니다.",
            "난민인정신청자는 6개월~1년 범위, 인도적 체류허가자는 통보일부터 1년 범위에서 체류기간이 부여됩니다.",
        ],
    ),
    variant(
        "G-1",
        "statusChange",
        "g-1-9-pregnancy-status-change",
        "임신·출산 인도적 배려자(G-1-9) 체류자격 변경허가",
        "임신·출산 등으로 즉시 출국이 곤란하여 기타(G-1-9)로 변경하는 경우",
        "pp. 506-507",
        docs(
            [
                "진단서 등 사유를 증명할 수 있는 서류",
                "신원보증서",
            ],
            common=["신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료"],
        ),
        status_code="G-1-9",
        notes=["임신·출산 등 인도적 배려가 불가피한 사람의 변경 시나리오에만 적용됩니다. 체류기간은 1년이 부여됩니다."],
    ),
    variant(
        "G-1",
        "statusChange",
        "g-1-10-medical-patient-status-change",
        "외국인환자(G-1-10) 체류자격 변경허가",
        "B-1·B-2·C-3(C-3-3 포함) 자격으로 입국한 후 의료기관 검진 등에 의해 장기치료·요양이 필요한 것으로 "
        "인정되는 사람 및 동반가족·간병인이 기타(G-1-10)로 변경하는 경우",
        "p. 507",
        docs(
            [
                "의료기관에서 발행한 소견서 등 장기 치료의 필요성을 입증할 수 있는 서류",
                "치료 및 체류 비용 조달 능력을 입증할 수 있는 서류",
            ],
            common=["신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료"],
            conditional=[
                "가족관계 및 간병인 입증서류(동반가족·간병인 동반 시)",
                "유치 기관 또는 신원보증인이 신원을 보증하는 경우 비용 조달 능력 입증서류 제출 생략 가능",
            ],
        ),
        status_code="G-1-10",
        notes=["장기 치료·요양이 필요한 외국인환자와 동반가족·간병인의 변경 시나리오에만 적용됩니다. 체류기간은 1년 이내 범위입니다."],
    ),
    variant(
        "G-1",
        "statusChange",
        "g-1-11-rights-protection-status-change",
        "성폭력피해자 등 인도적 고려 대상자(G-1-11) 체류자격 변경허가",
        "성폭력범죄·성매매 강요·상습폭행·학대 등 심각한 범죄 피해로 법원 재판, 수사기관 수사 또는 "
        "그 밖의 법률에 따른 민·형사상 권리구제 절차가 진행 중인 사람이 기타(G-1-11)로 변경하는 경우",
        "p. 507",
        docs(
            [
                "소송관련 서류 등 권리구제 입증서류",
                "신원보증서",
            ],
            common=["신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료"],
        ),
        status_code="G-1-11",
        notes=["권리구제 절차가 진행 중인 범죄 피해자의 변경 시나리오에만 적용됩니다. 체류기간은 1년이 부여됩니다."],
    ),
    # ================================================================= 거주(F-2)
    # 체류자격 변경허가 — clearly bounded family sub-codes, page 365.
    variant(
        "F-2",
        "statusChange",
        "f-2-2-national-minor-child-status-change",
        "국민의 미성년 외국인자녀(F-2-2) 거주 체류자격 변경허가",
        "대한민국 국민의 미성년 외국인자녀 또는 국민과의 혼인관계(사실상의 혼인관계 포함)에서 출생한 자녀가 "
        "거주(F-2-2)로 변경하는 경우",
        "p. 365",
        docs(
            [
                "대한민국 국민과 해당 미성년자와의 관계 및 양육권 보유관계를 입증할 수 있는 서류(이혼판결문 등)",
                "국민의 외국인 자녀임을 입증할 수 있는 서류(출생증명서, 호구부 등)",
                "자녀의 호구부 및 거민신분증",
                "부모의 기본증명서, 가족관계증명서, 주민등록등본",
                "신원보증서(양육권을 가진 부 또는 모)",
            ],
            common=["신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료"],
            conditional=[
                "양육권 보유관계를 입증할 수 없을 때에는 ‘친권자’ 또는 ‘후견인’의 동의서"
                "(친권자·후견인도 없는 경우 관련국의 공적서류 또는 공정증서)",
                "기존 방문동거(F-1-1) 자격의 국민의 미성년 외국인자녀는 확인 즉시 수수료 없이 거주(F-2-2)로 변경",
            ],
        ),
        status_code="F-2-2",
        notes=[
            "국민의 미성년 외국인자녀에 한정된 변경 시나리오에만 적용됩니다.",
            "병역 미이행·미면제 상태에서 국적을 이탈·상실한 남성 등 자격부여 제한 대상은 별도 확인이 필요합니다.",
        ],
    ),
    variant(
        "F-2",
        "statusChange",
        "f-2-permanent-resident-family-status-change",
        "영주(F-5) 소지자의 배우자·미성년 자녀 거주 체류자격 변경허가",
        "영주(F-5) 자격 소지자의 배우자 또는 미성년 자녀가 거주(F-2)로 변경하는 경우",
        "p. 365",
        docs(
            [
                "(배우자) 국내 배우자의 신원보증서",
                "(배우자) 초청장",
                "(미성년 자녀) 가족관계 입증서류(출생증명서, 결혼증명서, 호구부 등)",
            ],
            common=["신청서(별지 제34호 서식), 여권, 표준규격사진 1매, 수수료"],
        ),
        notes=[
            "영주(F-5) 소지자의 배우자 또는 미성년 자녀에 한정된 변경 시나리오에만 적용됩니다.",
            "배우자와 미성년 자녀는 제출서류가 다르므로 해당 대상에 맞는 서류만 제출합니다.",
        ],
    ),
]


def _serialize(records: list[dict[str, Any]]) -> str:
    return json.dumps(records, ensure_ascii=False, indent=2) + "\n"


def _procedure_shell(procedure: str) -> dict[str, Any]:
    return {
        "available": True,
        "summary": PROCEDURE_SUMMARIES[procedure],
        "requiredDocs": copy.deepcopy(EMPTY_DOCS),
        "variants": [],
        "manualRefs": [],
        "notes": [SCOPE_NOTE],
    }


def _compatible_existing_variant(existing: dict[str, Any], expected: dict[str, Any]) -> bool:
    for key in ("id", "labelKo", "scenarioKo", "statusCode"):
        if expected.get(key) != existing.get(key):
            return False
    groups = existing.get("requiredDocs")
    if not isinstance(groups, dict) or not any(groups.get(key) for key in groups):
        return False
    refs = existing.get("manualRefs")
    if not isinstance(refs, list) or not refs:
        return False
    for ref in refs:
        if not isinstance(ref, dict):
            return False
        if ref.get("manualVersion") != "2026.6":
            return False
        if ref.get("sourceFile") != SOURCE_FILE:
            return False
        if ref.get("needsManualReview") is not True:
            return False
        if ref.get("verified") is True:
            return False
    return True


def apply_variants(records: list[dict[str, Any]]) -> tuple[int, int]:
    by_code = {str(record.get("code")): record for record in records}
    added = 0
    unchanged = 0
    for item in VARIANTS:
        code = item["parent"]
        procedure_key = item["procedure"]
        new_variant = item["variant"]
        record = by_code.get(code)
        if not record:
            raise RuntimeError(f"Missing parent status: {code}")

        procedures = record.setdefault("procedures", {})
        if not isinstance(procedures, dict):
            raise RuntimeError(f"{code}.procedures must be an object")
        # setdefault preserves any pre-existing parent-level procedure record
        # (e.g. F-6's existing statusChange shell) and only fills gaps.
        procedure = procedures.setdefault(procedure_key, _procedure_shell(procedure_key))
        if not isinstance(procedure, dict):
            raise RuntimeError(f"{code}.procedures.{procedure_key} must be an object")

        procedure["available"] = True
        procedure.setdefault("summary", PROCEDURE_SUMMARIES[procedure_key])
        procedure.setdefault("requiredDocs", copy.deepcopy(EMPTY_DOCS))
        procedure.setdefault("manualRefs", [])
        procedure_notes = procedure.setdefault("notes", [])
        if not isinstance(procedure_notes, list):
            raise RuntimeError(f"{code}.procedures.{procedure_key}.notes must be a list")
        if SCOPE_NOTE not in procedure_notes:
            procedure_notes.append(SCOPE_NOTE)

        variants = procedure.setdefault("variants", [])
        if not isinstance(variants, list):
            raise RuntimeError(f"{code}.procedures.{procedure_key}.variants must be a list")
        existing = next((value for value in variants if value.get("id") == new_variant["id"]), None)
        if existing is None:
            variants.append(copy.deepcopy(new_variant))
            added += 1
        elif existing == new_variant or _compatible_existing_variant(existing, new_variant):
            unchanged += 1
        else:
            raise RuntimeError(
                f"Refusing to overwrite differing variant: "
                f"{code}.procedures.{procedure_key}.variants[{new_variant['id']}]"
            )
    return added, unchanged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if generated JSON would differ.")
    args = parser.parse_args(argv)

    records = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise RuntimeError(f"{SOURCE} must contain a JSON array")
    generated = copy.deepcopy(records)
    added, unchanged = apply_variants(generated)
    expected = _serialize(generated)

    if args.check:
        errors = []
        if SOURCE.read_text(encoding="utf-8") != expected:
            errors.append("visa_data.json is missing hard-case scenario variants or differs from generated output")
        if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != expected:
            errors.append("backend/data/visas.json is missing hard-case scenario variants or differs from generated output")
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"OK: {len(VARIANTS)} hard-case scenario variants present; canonical and deploy mirror match")
        return 0

    SOURCE.write_text(expected, encoding="utf-8")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(expected, encoding="utf-8")
    print(f"Updated {SOURCE.relative_to(ROOT)} and {TARGET.relative_to(ROOT)}")
    print(f"Hard-case variants: {len(VARIANTS)}; added: {added}; unchanged: {unchanged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
