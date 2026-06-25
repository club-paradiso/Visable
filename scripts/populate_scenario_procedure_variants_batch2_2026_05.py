#!/usr/bin/env python3
"""Populate the second batch of page-confirmed scenario procedure variants.

This helper is additive and idempotent. It layers a second batch of
scenario/sub-code-scoped procedure variants on top of the batch-1 records
produced by ``populate_scenario_procedure_variants_2026_05.py``. Existing
variants (batch 1 or batch 2) are preserved; a differing variant with the
same id is refused rather than overwritten.

Every variant in this file is traced to the official 2026.6 stay
manual PDF text committed in the repository
(``backend/data/sources/manuals/260623_stay_manual_readable.txt``) and carries a
provable printed-page citation. Page citations were verified with
``scripts/extract_manual_page_text.py`` (footer "- N -" == printed page N).

The records are intentionally scenario- or sub-code-scoped. They must not be
promoted into parent-level requiredDocs lists, marked verified, or treated as
source-confirmed HIGH determinations. Each retains
``needsManualReview: true``.

Usage:
    python3 scripts/populate_scenario_procedure_variants_batch2_2026_05.py
    python3 scripts/populate_scenario_procedure_variants_batch2_2026_05.py --check
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
    # ---------------------------------------------------------------- E-1 교수
    variant(
        "E-1",
        "statusChange",
        "e-1-d2-d10-status-change",
        "유학(D-2)·구직(D-10) → 교수(E-1) 체류자격 변경허가",
        "합법 체류 중인 유학(D-2) 또는 구직(D-10) 자격 소지자가 교수(E-1) 분야의 고용계약을 체결하여 변경하는 경우",
        "p. 172",
        docs(
            [
                "고용계약서",
                "학위증 또는 경력증명서",
                "고용업체 등 설립관련 서류(사업자등록증, 등기부등본 등)",
            ],
            common=["신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료"],
            conditional=["조교수 이상의 자격기준에 해당하는 전임교수 등은 학위증 또는 경력증명서 제출 생략"],
        ),
        status_code="E-1",
        notes=["유학(D-2) 또는 구직(D-10)에서 교수(E-1)로 변경하는 시나리오에만 적용됩니다."],
    ),
    variant(
        "E-1",
        "statusChange",
        "e-1-professional-spouse-status-change",
        "전문외국인력 배우자(F-3)의 교수(E-1) 등 전문직 체류자격 변경허가",
        "전문외국인력(E-1~E-5, E-6(E-6-2 제외), E-7) 자격 소지자의 배우자로서 동반(F-3) 자격을 가진 자가 교수(E-1) 등 전문직으로 변경하는 경우",
        "p. 171",
        docs(
            [
                "사업자등록증",
                "학위증(원본 및 사본) 또는 경력증명서",
                "고용계약서(원본 및 사본)",
            ],
            common=["신청서(별지 34호 서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료"],
            conditional=["원 근무처의 장의 동의서(원 근무처가 있는 경우만 해당)"],
        ),
        notes=[
            "공식 매뉴얼상 동일 조항은 E-1부터 E-7(E-6-2 제외)까지의 전문직 변경에 적용되며, 본 변형은 교수(E-1) 장에 수록된 시나리오입니다.",
            "전문외국인력 배우자(F-3) 시나리오에만 적용됩니다.",
        ],
    ),
    variant(
        "E-1",
        "statusChange",
        "e-1-science-graduate-status-change",
        "이공계 졸업 유학생(석사 이상)의 교수(E-1) 체류자격 변경허가",
        "이공계 대학을 졸업한 유학생 중 석사 이상의 학위를 취득하고 교육·과학기술 분야의 연구·지도 활동에 종사하려는 경우",
        "p. 172",
        docs(
            [
                "졸업증명서",
                "고용계약서",
                "총(학)장의 고용추천서",
                "사업자등록증",
            ],
            common=["신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료"],
        ),
        status_code="E-1",
        notes=["석사 이상의 학위를 취득한 이공계 졸업 유학생 시나리오에만 적용됩니다."],
    ),
    # ------------------------------------------------------------- E-2 회화지도
    variant(
        "E-2",
        "workplaceChange",
        "e-2-registered-workplace-change",
        "회화지도(E-2) 등록외국인 근무처 변경·추가 신고",
        "회화지도(E-2)로 등록하여 체류 중인 강사가 자격요건을 갖춘 근무처로 변경하거나 근무처를 추가하는 경우",
        "p. 180",
        docs(
            [
                "근무처변경·추가신고서(붙임 9), 여권, 외국인등록증",
                "고용계약서",
                "사업자등록증",
                "시설 설립 관련서류 등",
            ],
            conditional=[
                "원 근무처 장의 동의서(계약기간 만료일 또는 합의한 날짜까지 근무한 경우 면제, 휴·폐업 및 임금체불 등의 사유가 있는 경우 입증서류 또는 사유서로 대체 가능)",
                "잔여 체류기간이 (새 고용계약기간 + 1개월)보다 짧은 경우 체류기간 연장허가 심사에 필요한 구비서류 추가 제출",
            ],
        ),
        status_code="E-2",
        notes=["회화지도(E-2) 등록외국인의 사후 신고 대상 근무처 변경·추가에만 적용됩니다."],
    ),
    variant(
        "E-2",
        "statusChange",
        "e-2-registered-status-change",
        "회화지도(E-2) 요건 등록외국인 체류자격 변경허가",
        "회화지도(E-2) 자격요건을 갖춘 등록외국인(A-1·A-2·A-3 포함)이 회화지도(E-2)로 변경하는 경우",
        "pp. 181-182",
        docs(
            [
                "고용계약서 원본과 사본",
                "사업자등록증 사본",
                "공적확인을 받은 학력증명서",
                "신청일로부터 6개월 이내 발급받은 공적확인 범죄경력증명서",
                "채용신체검사서(반드시 밀봉된 상태로 제출, 개봉 불가)",
            ],
            common=["신청서(별지 34호 서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료"],
            conditional=[
                "과거 공적확인을 받은 학력 입증서류를 제출한 경우 학력증명서 제출 면제",
                "자국 이외의 국가에서 학위를 취득한 경우 공적확인을 받은 제3국 범죄경력증명서 추가 제출",
                "국내 대학에서 학위를 취득한 경우 공적확인 받지 않은 학위증 사본 제출 허용",
            ],
        ),
        status_code="E-2",
        notes=[
            "회화지도(E-2) 자격요건을 갖춘 등록외국인 변경 시나리오에만 적용됩니다.",
            "고용계약서상 임금이 당해연도 최저임금 기준에 미달하면 원칙적으로 변경 허가가 억제됩니다.",
        ],
    ),
    variant(
        "E-2",
        "statusChange",
        "e-2-education-office-instructor-status-change",
        "교육부(시·도교육감) 초청 영어강사 회화지도(E-2) 체류자격 변경허가",
        "교육부 또는 시·도교육감이 초청한 외국인영어강사로 채용되어 초·중·고교생을 대상으로 강의하려는 자가 소지 자격에 상관없이 E-2로 변경하는 경우",
        "p. 181",
        docs(
            [
                "시·도교육감 또는 국립국제교육원장이 발급한 합격통지서 또는 통지서",
                "고용계약서 원본과 사본",
                "학교 사업자등록증 사본(또는 고유번호증 사본)",
            ],
            common=["신청서(별지 34호 서식), 여권 및 외국인등록증(해당자), 표준규격사진 1장, 수수료"],
            conditional=[
                "시·도교육감과 고용계약을 체결한 초·중등학교 영어보조교사 등은 학력·경력 증명서 및 채용신체검사서 제출을 면제하고 합격증명서·고용계약서 등 최소서류만 제출",
            ],
        ),
        status_code="E-2",
        notes=["교육부(시·도교육감) 초청 영어강사 시나리오에만 적용됩니다."],
    ),
    variant(
        "E-2",
        "statusChange",
        "e-2-d2-d10-status-change",
        "유학(D-2)·구직(D-10) → 회화지도(E-2) 체류자격 변경허가",
        "합법 체류 중인 유학(D-2) 또는 구직(D-10) 자격 소지자가 회화지도(E-2) 분야의 고용계약을 체결하여 변경하는 경우",
        "pp. 182-183",
        docs(
            [
                "고용계약서",
                "학위증 또는 경력증명서",
                "고용업체 등 설립관련 서류(사업자등록증, 학원설립증 등)",
            ],
            common=["신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료"],
        ),
        status_code="E-2",
        notes=["유학(D-2) 또는 구직(D-10)에서 회화지도(E-2)로 변경하는 시나리오에만 적용됩니다."],
    ),
    # ----------------------------------------------------------------- E-3 연구
    variant(
        "E-3",
        "workplaceChange",
        "e-3-registered-workplace-change",
        "연구(E-3) 등록외국인 근무처 변경·추가 신고",
        "연구(E-3)로 외국인등록을 하고 체류 중인 자가 자격요건을 갖춘 근무처로 변경하거나 근무처를 추가하는 경우",
        "p. 189",
        docs(
            [
                "통합신청서(별지 제34호 서식), 여권 및 외국인등록증",
                "사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등",
                "고용계약서 또는 임용예정확인서",
            ],
            conditional=[
                "원 근무처 장의 동의서(계약기간 만료일 또는 합의한 날짜까지 근무한 경우 면제, 휴·폐업 및 임금체불 등의 사유가 있는 경우 입증서류 또는 사유서로 대체 가능)",
            ],
        ),
        status_code="E-3",
        notes=["연구(E-3) 등록외국인의 사후 신고 대상 근무처 변경·추가에만 적용됩니다."],
    ),
    variant(
        "E-3",
        "statusChange",
        "e-3-d2-d10-status-change",
        "유학(D-2)·구직(D-10) → 연구(E-3) 체류자격 변경허가",
        "합법 체류 중인 유학(D-2) 또는 구직(D-10) 자격 소지자가 연구(E-3) 분야의 고용계약을 체결하여 변경하는 경우",
        "pp. 192-193",
        docs(
            [
                "고용계약서 또는 임용예정확인서",
                "석사 학위 이상 학위증, 경력증명서(해당자)",
                "고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등)",
            ],
            common=["신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료"],
            conditional=[
                "대학 대표자 명의로 발급된 졸업예정증명서·확인서 및 학위수여 날짜 확인 증명서(해당자)",
                "우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자)",
            ],
        ),
        status_code="E-3",
        notes=["유학(D-2) 또는 구직(D-10)에서 연구(E-3)로 변경하는 시나리오에만 적용됩니다."],
    ),
    variant(
        "E-3",
        "statusChange",
        "e-3-a3-sofa-status-change",
        "협정(A-3) 자격자의 연구(E-3) 체류자격 변경허가",
        "연구(E-3) 자격요건을 충족하는 협정(A-3·SOFA) 자격 소지자가 연구(E-3)로 변경하는 경우",
        "p. 188",
        docs(
            [
                "고용계약서 또는 임용예정확인서",
                "고용기관 설립 관련 서류(사업자등록증 또는 법인등기사항전부증명서 또는 연구기관 입증서류 등)",
                "석사 학위 이상 학위증, 경력증명서(해당자)",
            ],
            common=["신청서(별지 34호 서식), 여권 및 SOFA ID, 수수료"],
            conditional=[
                "SPONSOR인 경우 원 근무처장의 동의서",
                "대학 대표자 명의로 발급된 졸업예정증명서·확인서 및 학위수여 날짜 확인 증명서(해당자)",
                "우수 학술논문의 저자임을 확인할 수 있는 입증자료(해당자)",
            ],
        ),
        notes=["협정(A-3·SOFA) 자격 소지자의 연구(E-3) 변경 시나리오에만 적용됩니다."],
    ),
    # ------------------------------------------------------------- E-7 특정활동
    variant(
        "E-7",
        "workplaceChange",
        "e-7-registered-workplace-change",
        "특정활동(E-7) 등록외국인 근무처 변경·추가 사후신고",
        "특정활동(E-7)으로 외국인등록을 하고 체류 중인 전문인력이 사후신고 대상에 해당하여 근무처를 변경하거나 추가하는 경우",
        "pp. 221-222",
        docs(
            [
                "통합신청서(별지 제34호~제34호의2 서식), 여권 및 외국인등록증",
                "주무부처 장의 고용추천서 또는 고용의 필요성을 입증하는 서류",
                "고용계약서",
                "사업자등록증",
            ],
            conditional=[
                "원 근무처 장의 동의서(계약기간 만료일 또는 합의한 날짜까지 근무한 경우 면제, 휴·폐업 및 임금체불 등의 사유가 있는 경우 입증서류 또는 사유서로 대체 가능)",
            ],
        ),
        status_code="E-7",
        notes=[
            "특정활동(E-7) 등록 전문인력의 사후신고 대상 근무처 변경·추가에만 적용됩니다.",
            "사유서와 신원보증서는 원칙적으로 제출이 생략됩니다.",
            "고용업체별 허용인원 제한 등 사전관리가 필요한 직종은 근무처 변경·추가 허가 대상으로 별도 절차가 적용됩니다.",
        ],
    ),
    # ----------------------------------------------------------------- F-3 동반
    variant(
        "F-3",
        "activitiesOutsideStatus",
        "f-3-language-proofreader-activities-outside-status",
        "동반(F-3) 외국어교열요원(E-7) 체류자격외활동허가",
        "방문동거(F-1)·동반(F-3) 자격 소지자가 국가기관 및 공공단체(지방자치단체, 정부투자기관)에서 외국어교열요원(E-7)으로 활동하려는 경우",
        "pp. 421-422",
        docs(
            [
                "고용계약서",
                "사업자등록증 사본",
                "추천서(해당 기관장)",
                "학위증(원본 및 사본)",
            ],
            common=["신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료"],
        ),
        notes=["국가기관·공공단체의 외국어교열요원(E-7) 자격외활동 시나리오에만 적용됩니다."],
    ),
    variant(
        "F-3",
        "activitiesOutsideStatus",
        "f-3-instructor-teacher-activities-outside-status",
        "동반(F-3) 외국어회화강사(E-2)·외국인학교교사(E-7) 체류자격외활동허가",
        "방문동거(F-1)·동반(F-3) 자격 소지자가 외국어회화강사(E-2) 또는 외국인학교교사(E-7)로 자격외 활동을 하려는 경우",
        "p. 422",
        docs(
            [
                "고용계약서",
                "사업자등록증",
            ],
            common=["신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료"],
            conditional=[
                "E-2 활동: 학위증(E-2 자격요건과 동일), 범죄경력증명서, 채용신체검사서",
                "E-7 활동: 해당국 교원 자격증 원본(교원자격증이 없는 경우 학위증 및 경력증명서), 범죄경력증명서, 채용신체검사서, 학교장 요청서, 외국인교사 현황",
            ],
        ),
        notes=["외국어회화강사(E-2) 또는 외국인학교교사(E-7) 자격외활동 시나리오에만 적용됩니다."],
    ),
    variant(
        "F-3",
        "statusChange",
        "f-3-humanitarian-status-change",
        "인도적 고려 동반(F-3) 체류자격 변경허가",
        "국내 입국 후 임신·출산·양육·질병 등 사정변경으로 인도적 고려가 필요한 자(사증면제·관광통과·단기사증 입국자 또는 국내 합법 장기체류 외국인)가 동반(F-3)으로 변경하는 경우",
        "p. 424",
        docs(
            [
                "가족관계 입증서류(결혼 또는 출생증명서 등)",
                "체류경비 등 재정능력 입증서류",
                "체류지 입증서류",
                "신원보증서",
                "체류자격 변경 사유서 및 관련 증빙 서류",
            ],
            common=["신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료"],
            additional=["주자격자(배우자 또는 부모)의 외국인등록증"],
            conditional=[
                "본국의 공적 서류는 번역자 확인서 첨부, 협약국은 아포스티유 확인, 미체약국은 주재국 대한민국 공관 영사확인 필요",
            ],
        ),
        status_code="F-3",
        notes=["임신·출산·양육·질병 등 인도적 고려가 필요한 동반(F-3) 변경 시나리오에만 적용됩니다."],
    ),
    variant(
        "F-3",
        "statusGrant",
        "f-3-born-child-status-grant",
        "동반(F-3) 국내출생 자녀 체류자격 부여",
        "동반(F-3) 자격 소지자(주자격자의 배우자·미성년 자녀)의 국내출생 자녀에게 동반(F-3) 체류자격을 부여하는 경우",
        "pp. 423-424",
        docs(
            [
                "부 또는 모의 외국인등록증",
                "신원보증서",
                "가족관계 입증서류(본국 출생증명서 원본, 국내 출생증명서, 친자관계 입증서류 등)",
            ],
            common=["신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료"],
            conditional=[
                "중국의 경우 거민신분증, 결혼증, 호구부 등 추가 제출",
                "본국의 공적 서류는 번역자 확인서 첨부, 협약국은 아포스티유 확인, 미체약국은 주재국 대한민국 공관 영사확인 필요",
            ],
        ),
        notes=["동반(F-3) 자격 소지자의 국내출생 자녀 체류자격 부여 시나리오에만 적용됩니다."],
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
            errors.append("visa_data.json is missing batch-2 scenario variants or differs from generated output")
        if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != expected:
            errors.append("backend/data/visas.json is missing batch-2 scenario variants or differs from generated output")
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"OK: {len(VARIANTS)} batch-2 scenario variants present; canonical and deploy mirror match")
        return 0

    SOURCE.write_text(expected, encoding="utf-8")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(expected, encoding="utf-8")
    print(f"Updated {SOURCE.relative_to(ROOT)} and {TARGET.relative_to(ROOT)}")
    print(f"Batch-2 variants: {len(VARIANTS)}; added: {added}; unchanged: {unchanged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
