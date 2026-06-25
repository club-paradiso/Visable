#!/usr/bin/env python3
"""Populate page-confirmed scenario procedure variants from the 2026.6 stay manual.

The curated records in this file are intentionally scenario- or sub-code-scoped.
They must not be promoted into parent-level requiredDocs lists.

Usage:
    python3 scripts/populate_scenario_procedure_variants_2026_05.py
    python3 scripts/populate_scenario_procedure_variants_2026_05.py --check
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
    variant(
        "D-4",
        "statusChange",
        "d-4-1-7-language-training-status-change",
        "어학연수(D-4-1·D-4-7) 체류자격 변경허가",
        "합법 체류 중인 장기체류자가 한국어연수(D-4-1) 또는 외국어연수(D-4-7)로 변경하는 경우",
        "pp. 83-84",
        docs(
            [
                "신청서, 여권, 외국인등록증(소지자), 사진 1매, 수수료",
                "교육기관 사업자등록증 또는 고유번호증 사본",
                "표준입학허가서(대학 총·학장 발행)",
                "재정능력입증서류",
                "재학증명서 또는 최종학력입증서류",
                "연수계획서(강의시간표, 강사구성표, 연수시설 등의 내용을 포함)",
            ],
            conditional=[
                "부·모 잔고증명서 제출 시 가족관계증명서 추가 제출",
                "법무부장관 고시국가 국민 중 연령 등을 고려할 때 어학연수 필요성이 적다고 판단되는 경우 어학연수 필요성 소명자료를 추가로 요구할 수 있음",
            ],
        ),
        notes=[
            "한국어연수(D-4-1) 및 외국어연수(D-4-7) 변경 시나리오에만 적용됩니다.",
            "단기체류자와 일부 등록외국인은 변경이 제한됩니다.",
        ],
    ),
    variant(
        "D-4",
        "statusChange",
        "d-4-2-graduate-training-status-change",
        "졸업생 일반연수(D-4-2) 체류자격 변경허가",
        "국내 대학 졸업자가 공식 매뉴얼에 열거된 기관 또는 단체에서 연수가 필요하여 일반연수(D-4-2) 등으로 변경하는 경우",
        "p. 84",
        docs(
            [
                "신청서, 여권, 외국인등록증, 사진 1매, 수수료",
                "연수의 필요성을 입증하는 서류(취업확인서, 연수계획서 등)",
                "외국인 투자기업 또는 외국에 투자한 국내기업임을 입증하는 서류",
            ]
        ),
        status_code="D-4-2",
        notes=["국내 대학 졸업생의 공식 매뉴얼상 연수기관 시나리오에만 적용됩니다."],
    ),
    variant(
        "D-4",
        "statusChange",
        "d-4-3-school-student-status-change",
        "고등학교 이하 외국인유학생(D-4-3) 체류자격 변경허가",
        "합법적으로 등록하여 장기체류 중인 자비부담 외국인유학생이 허용 교육기관의 입학허가를 받아 D-4-3으로 변경하는 경우",
        "pp. 85-86",
        docs(
            [
                "신청서(별지 제34호 서식), 여권, 외국인등록증(소지자), 표준규격사진 1매, 수수료",
                "교육기관 사업자등록증 또는 고유번호증 사본",
                "입학허가서(학교장 발행) 및 재학증명서(해당자)",
                "최종 학력 입증서류(졸업증명서 또는 재학증명서 등)",
                "학비 납부 내역서",
                "국내 체류비용 부담능력 입증서류",
                "후견 보증서",
                "후견인과의 관계 증명서류",
                "체류지 입증서류",
            ],
            conditional=[
                "후견인 면제 대상자는 학교장 명의 기숙사 입소확인서 제출",
                "불법체류 다발국가 국민은 후견인 재정능력 입증서류 및 가족관계 입증서류 추가 제출",
            ],
        ),
        status_code="D-4-3",
        notes=["고등학교 이하 자비부담 외국인유학생 시나리오에만 적용됩니다."],
    ),
    variant(
        "D-8",
        "statusChange",
        "d-8-1-corporate-investment-status-change",
        "법인 투자(D-8-1) 체류자격 변경허가",
        "외국인투자기업인 대한민국 법인의 경영·관리 또는 생산·기술 분야 필수전문인력이 D-8-1로 변경하는 경우",
        "pp. 119-120",
        docs(
            [
                "신청서(별지 34호 서식), 여권 및 외국인등록증, 표준규격사진 1장",
                "사업자등록증 사본, 법인등기사항전부증명서, 주주변동상황명세서 원본",
                "투자기업등록증 사본",
                "투자자금 도입관련 입증서류",
                "영업실적(수출입실적 등) 증명서",
                "체류지 입증서류",
                "사업장 존재 입증서류",
            ],
            conditional=[
                "주재활동의 경우 파견명령서 및 재직증명서 추가 제출",
                "투자금액 3억원 미만 개인투자자는 자본금 사용내역 입증서류 및 필요시 해당 업종 또는 분야의 사업 경험 관련 국적국 서류 추가 제출",
                "금융지주회사가 100% 출자한 자회사의 필수전문인력은 별도 제출서류 적용",
            ],
        ),
        status_code="D-8-1",
        notes=["법인 투자(D-8-1) 변경 시나리오에만 적용됩니다."],
    ),
    variant(
        "D-8",
        "statusChange",
        "d-8-2-venture-investment-status-change",
        "벤처 투자(D-8-2) 체류자격 변경허가",
        "벤처기업 대표자 등이 벤처 투자(D-8-2)로 변경하는 경우",
        "p. 120",
        docs(
            [
                "신청서(별지 34호 서식), 여권, 외국인등록증(해당자), 표준규격사진 1장",
                "사업자등록증 사본, 법인등기사항전부증명서",
                "벤처기업확인서 또는 예비벤처기업확인서",
                "지식재산권 보유 또는 우수 기술력 입증서류",
                "체류지 입증서류",
                "사무실 임대차계약서",
                "영업실적(수출입실적 등) 증명서",
            ]
        ),
        status_code="D-8-2",
        notes=["벤처 투자(D-8-2) 변경 시나리오에만 적용됩니다."],
    ),
    variant(
        "D-8",
        "statusChange",
        "d-8-3-individual-enterprise-status-change",
        "개인기업 투자(D-8-3) 체류자격 변경허가",
        "대한민국 국민이 경영하는 외국인투자 개인기업의 필수전문인력이 D-8-3으로 변경하는 경우",
        "pp. 120-121",
        docs(
            [
                "신청서(별지 34호 서식), 여권, 외국인등록증(해당자), 표준규격사진 1장",
                "공동사업자가 표시된 사업자등록증 사본, 공동사업자약정서 원본",
                "투자기업등록증 사본",
                "공동사업자인 국민의 사업자금 사용내역 입증서류",
                "투자자금 도입관련 입증서류",
                "영업실적(수출입실적 등) 증명서",
                "체류지 입증서류",
                "사업장 존재 입증서류",
            ],
            conditional=[
                "주재활동의 경우 파견명령서 및 재직증명서 추가 제출",
                "투자금액 3억원 미만 신청자는 자본금 사용내역 입증서류 및 필요시 해당 업종 또는 분야의 사업 경험 관련 국적국 서류 추가 제출",
            ],
        ),
        status_code="D-8-3",
        notes=["개인기업 투자(D-8-3) 변경 시나리오에만 적용됩니다."],
    ),
    variant(
        "D-8",
        "statusChange",
        "d-8-4-tech-startup-status-change",
        "기술창업(D-8-4) 체류자격 변경허가",
        "기술창업 요건을 갖춘 법인 창업자가 D-8-4로 변경하는 경우",
        "pp. 121-122",
        docs(
            [
                "신청서, 여권, 표준규격사진, 체류지 입증서류",
                "법인등기사항전부증명서 및 사업자등록증 사본",
                "학위증명서 사본 또는 관계 중앙행정기관의 장의 추천서",
            ],
            conditional=[
                "법인 설립이 완료되지 않은 점수제 적용 대상자 및 스타트업코리아 특별비자 대상자는 법인등기사항전부증명서 및 사업자등록증 사본 제출을 생략할 수 있으나 6개월 이내 제출 및 체류기간 연장 필요",
                "점수제 적용대상자는 지식재산권, 특허 출원, OASIS 이수 또는 기타 점수제 항목 입증서류 추가 제출",
                "점수제 적용 면제 대상자는 해당 유형에 따른 중기부 확인서·추천 공문 또는 추천서 추가 제출",
            ],
        ),
        status_code="D-8-4",
        notes=["기술창업(D-8-4) 변경 시나리오에만 적용됩니다."],
    ),
    variant(
        "D-9",
        "statusChange",
        "d-9-equipment-specialist-status-change",
        "산업설비·선박건조 필수전문인력(D-9) 체류자격 변경허가",
        "부득이한 사유로 사증면제 또는 단기사증으로 입국한 산업설비 기술제공자 또는 선박건조·설비제작 필수전문인력이 D-9로 변경하는 경우",
        "pp. 131-132",
        docs(
            [
                "신청서(별지 34호 서식), 여권, 표준규격사진 1장, 수수료",
                "체류자격변경 사유서",
                "파견명령서 또는 재직증명서(본사 발급)",
                "선박수주계약서 또는 설비도입계약서",
                "사업자등록증 사본",
                "납세사실증명",
            ],
            conditional=["외국인 개인 납세내역이 없는 경우 회사 납세사실증명으로 접수"],
        ),
        status_code="D-9",
        notes=["산업설비 기술제공자 또는 선박건조·설비제작 필수전문인력 변경 시나리오에만 적용됩니다."],
    ),
    variant(
        "D-9",
        "statusChange",
        "d-9-foreign-sole-proprietor-status-change",
        "외국인 개인사업자(D-9) 체류자격 변경허가",
        "공식 매뉴얼의 투자금 및 사업자 요건을 충족한 외국인 개인사업자가 D-9로 변경하는 경우",
        "pp. 132-133",
        docs(
            [
                "신청서(시행규칙 별지 제34호 서식), 여권, 수수료",
                "사업자등록증 사본, 영업허가증(해당자), 투자기업등록증(소지자)",
                "사업자금 도입관련 입증서류",
                "자본금 사용내역 입증서류",
                "주거지 입증서류",
                "사업장 존재 입증서류",
            ],
            conditional=[
                "공동사업자인 경우 공동사업약정서 원본 및 사본, 공동사업자의 연간 소득 입증서류 추가 제출",
                "해당자는 OASIS 교육 이수증 추가 제출",
                "체류자격 변경 전 단기사증(C-3-4) 등을 소지하고 영업행위를 한 경우 영업실적 입증서류 추가 제출",
            ],
        ),
        status_code="D-9",
        notes=["공식 매뉴얼의 외국인 개인사업자 변경 시나리오에만 적용됩니다."],
    ),
    variant(
        "E-4",
        "workplaceChange",
        "e-4-registered-workplace-change",
        "기술지도(E-4) 등록외국인 근무처 변경·추가 신고",
        "기술지도(E-4)로 등록하여 체류 중인 자가 자격요건을 갖춘 근무처로 변경하거나 근무처를 추가하는 경우",
        "p. 197",
        docs(
            [
                "근무처변경·추가 신고서(별지 제38호의3 서식), 여권 및 외국인등록증",
                "사업자등록증",
                "고용계약서",
                "기술도입계약신고수리서, 기술도입계약서 또는 용역거래인증서, 또는 방위산업체지정서 사본 등",
            ],
            conditional=[
                "원 근무처 장의 동의서(계약기간 만료 등 면제사유가 있거나 휴·폐업 및 임금체불 등의 사유로 대체 가능한 경우 제외)",
                "근무처 변경 시 소관부처 장관의 고용추천서",
            ],
        ),
        status_code="E-4",
        notes=["기술지도(E-4) 등록외국인의 사후 신고 대상 근무처 변경·추가에만 적용됩니다."],
    ),
    variant(
        "E-4",
        "statusChange",
        "e-4-d2-d10-status-change",
        "유학(D-2)·구직(D-10) → 기술지도(E-4) 체류자격 변경허가",
        "요건을 갖춘 유학(D-2) 또는 구직(D-10) 자격 소지자가 기술지도(E-4) 분야의 고용계약을 체결하여 변경하는 경우",
        "pp. 197-198",
        docs(
            [
                "신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료",
                "파견명령서(본사 발행) 또는 재직증명서",
                "기술도입계약신고수리서, 기술도입계약서 또는 용역거래인증서, 또는 방위산업체지정서 사본",
                "사업자등록증 사본",
            ],
            conditional=["소관부처 장관의 고용추천서(필요시)"],
        ),
        status_code="E-4",
        notes=["유학(D-2) 또는 구직(D-10)에서 기술지도(E-4)로 변경하는 시나리오에만 적용됩니다."],
    ),
    variant(
        "E-5",
        "workplaceChange",
        "e-5-registered-workplace-change",
        "전문직업(E-5) 등록외국인 근무처 변경·추가 신고",
        "전문직업(E-5)으로 등록하여 체류 중인 자가 자격요건을 갖춘 근무처로 변경하거나 근무처를 추가하는 경우",
        "pp. 201-202",
        docs(
            [
                "근무처변경·추가 신고서(별지 제38호의3 서식), 여권 및 외국인등록증",
                "사업자등록증",
                "고용계약서",
            ],
            conditional=[
                "원 근무처 장의 동의서(계약기간 만료 등 면제사유가 있거나 휴·폐업 및 임금체불 등의 사유로 대체 가능한 경우 제외)",
                "근무처 변경 시 소관부처 장관의 고용추천서",
            ],
        ),
        status_code="E-5",
        notes=["전문직업(E-5) 등록외국인의 사후 신고 대상 근무처 변경·추가에만 적용됩니다."],
    ),
    variant(
        "E-5",
        "statusChange",
        "e-5-d2-d10-status-change",
        "유학(D-2)·구직(D-10) → 전문직업(E-5) 체류자격 변경허가",
        "요건을 갖춘 유학(D-2) 또는 구직(D-10) 자격 소지자가 전문직업(E-5) 분야의 고용계약을 체결하여 변경하는 경우",
        "p. 202",
        docs(
            [
                "신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료",
                "고용계약서 사본",
                "사업자등록증 사본 또는 허가증이나 등록증(특정사업 허가·등록 업체인 경우) 등",
                "학위증 사본 및 자격증 사본",
                "소관부처 장관의 고용추천서",
            ]
        ),
        status_code="E-5",
        notes=["유학(D-2) 또는 구직(D-10)에서 전문직업(E-5)으로 변경하는 시나리오에만 적용됩니다."],
    ),
    variant(
        "E-6",
        "activitiesOutsideStatus",
        "e-6-broadcast-film-model-activities-outside-status",
        "방송·영화·모델 활동 체류자격외활동허가",
        "합법체류 등록외국인이 E-6-2 활동을 제외한 방송·영화·모델 활동을 하려는 경우",
        "pp. 205-206",
        docs(
            [
                "신청서(별지 34호 서식), 여권 및 외국인등록증, 수수료",
                "고용계약서",
                "공연추천서",
                "사업자등록증 등 단체 설립관련 서류",
            ],
            conditional=[
                "원 근무처장의 동의서(해당자)",
                "A-1, A-2 자격 소지자는 외교부장관 추천서 추가 제출",
            ],
        ),
        notes=[
            "E-6-2 활동은 이 체류자격외활동허가 대상에서 제외됩니다.",
            "비영리 목적의 지상파방송 임시 출연 등은 별도 허가 없이 허용될 수 있습니다.",
        ],
    ),
    variant(
        "E-6",
        "workplaceChange",
        "e-6-1-3-workplace-change",
        "예술흥행(E-6-1·E-6-3) 근무처 변경·추가 신고",
        "E-6-1 또는 E-6-3으로 등록하여 체류 중인 자가 자격요건을 갖춘 근무처로 변경하거나 근무처를 추가하는 경우",
        "pp. 206-207",
        docs(
            [
                "신청서(별지 제34호 서식), 여권 및 외국인등록증",
                "사업자등록증",
                "고용계약서",
                "고용추천서 또는 공연 추천서",
            ],
            conditional=[
                "원 근무처 장의 동의서(계약기간 만료 등 면제사유가 있거나 휴·폐업 및 임금체불 등의 사유로 대체 가능한 경우 제외)"
            ],
        ),
        notes=["E-6-1 또는 E-6-3 등록외국인의 사후 신고 대상 근무처 변경·추가에만 적용됩니다."],
    ),
    variant(
        "E-6",
        "workplaceChange",
        "e-6-2-employer-workplace-change",
        "호텔 등 관광유흥업소 예술흥행(E-6-2) 고용주 변경·추가허가",
        "E-6-2 호텔 등 관광유흥업소 종사 연예인의 소속 공연기획사 등이 변경 또는 추가되어 고용주가 변동되는 경우",
        "p. 207",
        docs(
            [
                "신청서(별지 제34호 서식), 여권 및 외국인등록증, 수수료",
                "사업자등록증",
                "원 근무처 장의 동의서",
                "고용계약서",
                "공연 추천서(영상물등급위원회 발행)",
                "신원보증서 원본",
            ]
        ),
        status_code="E-6-2",
        notes=["E-6-2 공연기획사 등 고용주 변동의 사전 허가 시나리오에만 적용됩니다."],
    ),
    variant(
        "E-6",
        "statusChange",
        "e-6-d2-d10-status-change",
        "유학(D-2)·구직(D-10) → 예술흥행(E-6) 체류자격 변경허가",
        "요건을 갖춘 유학(D-2) 또는 구직(D-10) 자격 소지자가 E-6-1 또는 E-6-3 분야의 고용계약을 체결하여 변경하는 경우",
        "pp. 208-209",
        docs(
            [
                "신청서(별지 34호 서식), 여권 및 외국인등록증, 표준규격사진 1장, 수수료",
                "고용계약서 또는 공연계약서",
                "사업자등록증",
                "고용·공연추천서",
            ]
        ),
        notes=["E-6-1 또는 E-6-3에 해당하는 제한적 변경 시나리오에만 적용됩니다."],
    ),
    variant(
        "E-9",
        "workplaceChange",
        "e-9-standard-workplace-change",
        "비전문취업(E-9) 일반 사업장 변경허가",
        "외국인고용법상 사업장 변경 사유에 해당하는 E-9 외국인근로자가 고용센터 절차 후 근무처 변경허가를 받는 경우",
        "pp. 327-328",
        docs(
            [
                "신청서(별지 34호 서식), 여권, 외국인등록증, 수수료, 체류지 입증서류",
                "고용허가서 사본",
                "표준근로계약서 사본",
                "사업자등록증 등 사업장 관련 입증서류",
            ],
            conditional=["건설업체는 해당 현장 책임건설업체가 작성한 건설현장 외국인력 현황표 추가 제출"],
        ),
        status_code="E-9",
        notes=["외국인고용법상 사업장 변경 사유가 있는 일반 E-9 근무처 변경허가 시나리오에만 적용됩니다."],
    ),
    variant(
        "F-1",
        "statusGrant",
        "f-1-employment-parent-born-child-status-grant",
        "취업계열 체류자격자 등의 국내출생 자녀 체류자격 부여",
        "기술연수(D-3), 비전문취업(E-9), 선원취업(E-10), 방문취업(H-2), 재외동포(F-4) 자격으로 국내 체류 중인 부모의 국내출생 자녀에게 체류자격을 부여하는 경우",
        "p. 343",
        docs(
            [
                "신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료",
                "출생증명서",
                "부모의 외국인등록증 사본",
            ],
            conditional=["중국 국적자는 호구부 추가 제출"],
        ),
        notes=["열거된 부모 체류자격의 국내출생 자녀 체류자격 부여 시나리오에만 적용됩니다."],
    ),
    variant(
        "F-1",
        "statusGrant",
        "f-1-refugee-born-child-status-grant",
        "난민인정자의 국내출생 미성년 자녀 체류자격 부여",
        "난민인정자의 국내출생 미성년 자녀에게 부모의 체류기간 범위 내에서 체류자격을 부여하는 경우",
        "p. 343",
        docs(
            [
                "신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료",
                "출생증명서 등 부모와의 가족관계를 입증할 수 있는 서류 및 미성년 자녀의 나이를 확인할 수 있는 서류",
                "체류지 입증서류",
            ]
        ),
        notes=["난민인정자의 국내출생 미성년 자녀 시나리오에만 적용됩니다."],
    ),
    variant(
        "F-1",
        "statusChange",
        "f-1-6-marriage-cleanup-status-change",
        "혼인단절 결혼이민자 가사정리(F-1-6) 체류자격 변경허가",
        "국민과 혼인이 단절되었으나 F-6-3에 해당하지 않고 재산분할 또는 가사정리로 국내 체류가 불가피한 사람이 F-1-6으로 변경하는 경우",
        "pp. 345-346",
        docs(
            [
                "신청서(별지 제34호 서식), 여권 및 외국인등록증, 사진 1매, 수수료",
                "신원보증서",
                "이혼 사실이 기재된 혼인관계 증명서",
                "체류 불가피성 소명자료",
                "체류지 입증서류",
            ],
            conditional=["기타 심사에 필요하다고 인정되는 서류"],
        ),
        status_code="F-1-6",
        notes=["혼인단절 후 가사정리를 위한 F-1-6 변경 시나리오에만 적용됩니다."],
    ),
    variant(
        "F-1",
        "statusChange",
        "f-1-nationality-procedure-status-change",
        "국적취득절차 진행자 방문동거(F-1) 체류자격 변경허가",
        "국적회복, 귀화 또는 국적판정 절차를 밟고 있는 외국인이 방문동거(F-1)로 변경하는 경우",
        "p. 346",
        docs(
            [
                "신청서(별지 34호 서식), 여권, 표준규격사진 1매, 수수료",
                "신원보증서",
                "귀화허가 또는 국적회복허가 신청사실증명서",
            ]
        ),
        status_code="F-1",
        notes=["국적회복, 귀화 또는 국적판정 절차 진행자 변경 시나리오에만 적용됩니다."],
    ),
    variant(
        "F-1",
        "statusChange",
        "f-1-16-refugee-family-status-change",
        "난민인정자 가족(F-1-16) 체류자격 변경허가",
        "난민인정자의 배우자 또는 미성년 자녀가 방문동거(F-1-16)로 변경하는 경우",
        "p. 348",
        docs(
            [
                "신청서(별지 34호 서식), 여권 및 외국인등록증, 표준규격사진 1매, 수수료",
                "배우자 또는 그 부모의 난민인정증명서",
                "난민인정자의 가족임을 입증하는 서류",
                "체류지 입증서류",
            ]
        ),
        status_code="F-1-16",
        notes=["배우자가 있는 미성년 자녀는 제외됩니다."],
    ),
    variant(
        "F-1",
        "statusChange",
        "f-1-52-prior-marriage-child-status-change",
        "결혼이민자 전혼관계 출생 미성년 자녀(F-1-52) 체류자격 변경허가",
        "혼인관계가 유지 중인 결혼이민자의 전혼관계 출생 친생 미성년 자녀가 F-1-52로 변경하는 경우",
        "p. 350",
        docs(
            [
                "여권, 통합신청서, 표준규격사진 1매, 수수료, 외국인등록증(해당자)",
                "결혼이민자의 한국인 배우자의 기본증명서, 가족관계증명서, 혼인관계증명서, 주민등록등본",
                "결혼이민자의 여권, 신분증, 외국인등록증",
                "미성년 외국인 자녀의 여권 및 출생 관련 공적 증명서류 원본과 사본",
                "양육권 보유관계 입증서류",
                "결혼이민자와 한국인 배우자의 신원보증서",
                "체류지 입증서류",
            ],
            conditional=[
                "공교육 인정 대상 학교에 재학 중인 경우 재학증명서 추가 제출",
                "결핵고위험국가의 경우 결핵진단서 추가 제출",
            ],
        ),
        status_code="F-1-52",
        notes=[
            "결혼이민자의 전혼관계 출생 친생 미성년 자녀 F-1-52 변경 시나리오에만 적용됩니다.",
            "해외 발급 서류는 아포스티유 또는 대한민국 공관 영사확인과 번역문 첨부가 필요합니다.",
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
            errors.append("visa_data.json is missing curated scenario variants or differs from generated output")
        if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != expected:
            errors.append("backend/data/visas.json is missing curated scenario variants or differs from generated output")
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"OK: {len(VARIANTS)} curated scenario variants present; canonical and deploy mirror match")
        return 0

    SOURCE.write_text(expected, encoding="utf-8")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(expected, encoding="utf-8")
    print(f"Updated {SOURCE.relative_to(ROOT)} and {TARGET.relative_to(ROOT)}")
    print(f"Curated variants: {len(VARIANTS)}; added: {added}; unchanged: {unchanged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
