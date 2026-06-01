#!/usr/bin/env python3
"""Populate remaining complex-subtype procedure variants from the 2026-05 manual.

This batch is additive and deliberately conservative. It keeps the existing
parent procedures intact while adding labeled needs-review scenario cards.
Some F-4/H-2 sections live in an embedded manual whose printed page footer
restarts; their page ranges therefore record both PDF and embedded-manual pages.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (ROOT / "visa_data.json", ROOT / "backend" / "data" / "visas.json")
SOURCE_FILE = "docs/source-manuals/2026-05/stay_manual_2026_05.pdf"
MANUAL_NAME = "체류민원"
MANUAL_VERSION = "2026.5"
SCOPE_NOTE = (
    "이 항목은 안내된 세부 상황에만 적용됩니다. 실제 제출 범위와 허가 여부는 "
    "관할 출입국·외국인관서가 신청인의 구체적 사정에 따라 최종 확인합니다."
)

PROCEDURE_SUMMARIES = {
    "statusChange": "체류자격 변경 제출서류는 변경 대상 자격과 세부 상황별로 다릅니다.",
    "workplaceChange": "근무처 변경·추가 신고 또는 허가 범위는 체류자격과 세부 상황별로 다릅니다.",
    "extension": "체류기간 연장 제출서류는 체류자격과 세부 상황별로 다릅니다.",
    "registration": "외국인등록·거소신고 제출서류는 체류자격과 세부 상황별로 다릅니다.",
}

EMPTY_DOCS = {
    "commonDocs": [],
    "requiredDocs": [],
    "additionalDocs": [],
    "conditionalDocs": [],
}


def docs(
    *,
    common: list[str],
    required: list[str],
    additional: list[str] | None = None,
    conditional: list[str] | None = None,
) -> dict[str, list[str]]:
    return {
        "commonDocs": common,
        "requiredDocs": required,
        "additionalDocs": additional or [],
        "conditionalDocs": conditional or [],
    }


def variant(
    *,
    variant_id: str,
    label: str,
    scenario: str,
    page_range: str,
    required_docs: dict[str, list[str]],
    status_code: str | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": variant_id,
        "labelKo": label,
        "scenarioKo": scenario,
        "requiredDocs": required_docs,
        "manualRefs": [
            {
                "manualName": MANUAL_NAME,
                "manualVersion": MANUAL_VERSION,
                "pageRange": page_range,
                "sourceFile": SOURCE_FILE,
                "confidence": "manual_extracted_needs_review",
                "needsManualReview": True,
            }
        ],
        "notes": [SCOPE_NOTE, *(notes or [])],
    }
    if status_code:
        item["statusCode"] = status_code
    return item


VARIANTS: dict[tuple[str, str], list[dict[str, Any]]] = {
    ("F-6", "extension"): [
        variant(
            variant_id="f-6-1-marriage-maintenance-extension",
            label="F-6-1 혼인관계 유지 중 체류기간 연장",
            status_code="F-6-1",
            scenario="국민의 배우자가 혼인관계를 유지하면서 체류기간 연장을 신청하는 경우",
            page_range="pp. 490-491",
            required_docs=docs(
                common=["신청서(별지 제34호 서식)", "여권", "수수료"],
                required=[
                    "한국인 배우자의 혼인관계증명서(상세)",
                    "한국인 배우자의 주민등록등본",
                    "외국인 직업 신고서",
                    "체류지 입증서류",
                ],
                conditional=[
                    "부부 사이에 출생한 자녀가 있는 경우 자녀의 가족관계증명서",
                    "심사 과정에서 필요하다고 인정되는 경우 추가 입증서류",
                ],
            ),
            notes=[
                "혼인관계 유지 중 연장 시나리오이며 별거·이혼소송·배우자 실종 시나리오와 구분합니다.",
                "한국인 배우자와 혼인관계에서 출생한 자녀를 양육하는 경우 체류기간 부여 범위가 달라질 수 있습니다.",
            ],
        ),
        variant(
            variant_id="f-6-1-separated-extension",
            label="F-6-1 별거 중 체류기간 연장",
            status_code="F-6-1",
            scenario="한국인 배우자와 별거 중인 국민의 배우자가 체류기간 연장을 신청하는 경우",
            page_range="p. 491",
            required_docs=docs(
                common=["신청서(별지 제34호 서식)", "여권", "외국인등록증", "수수료"],
                required=[
                    "한국인 배우자의 혼인관계증명서(상세)",
                    "한국인 배우자의 주민등록등본",
                    "외국인 직업 신고서",
                    "체류지 입증서류",
                    "별거 사유를 입증하는 서류",
                ],
                conditional=[
                    "배우자 가출신고서, 상해 진단서·사진, 가정폭력 피해자 보호시설 확인서, 형사판결문, 지인 확인서 또는 여성단체 확인서 등 해당 사유 입증서류",
                    "배우자가 수감된 경우 수감증명서와 배우자 가족 확인서",
                    "부부 사이에 출생한 자녀가 있는 경우 자녀의 가족관계증명서",
                ],
            ),
            notes=["별거 사유에 맞는 입증서류를 제출해야 하며, 별거 자체가 연장을 자동 보장하지 않습니다."],
        ),
        variant(
            variant_id="f-6-1-divorce-lawsuit-extension",
            label="F-6-1 이혼소송 중 체류기간 연장",
            status_code="F-6-1",
            scenario="한국인 배우자와 이혼소송 중인 국민의 배우자가 체류기간 연장을 신청하는 경우",
            page_range="p. 491",
            required_docs=docs(
                common=["신청서(별지 제34호 서식)", "여권", "외국인등록증", "수수료"],
                required=[
                    "한국인 배우자의 혼인관계증명서(상세)",
                    "한국인 배우자의 주민등록등본",
                    "외국인 직업 신고서",
                    "체류지 입증서류",
                    "이혼소송 계속 사실을 입증하는 서류",
                ],
                conditional=["부부 사이에 출생한 자녀가 있는 경우 자녀의 가족관계증명서"],
            ),
            notes=["이혼소송 진행 사실을 입증하는 서류가 필요한 별도 연장 시나리오입니다."],
        ),
        variant(
            variant_id="f-6-1-spouse-missing-extension",
            label="F-6-1 배우자 실종 중 체류기간 연장",
            status_code="F-6-1",
            scenario="한국인 배우자의 실종선고 전 단계에서 국민의 배우자가 체류기간 연장을 신청하는 경우",
            page_range="p. 491",
            required_docs=docs(
                common=["신청서(별지 제34호 서식)", "여권", "외국인등록증", "수수료"],
                required=[
                    "한국인 배우자의 혼인관계증명서(상세)",
                    "한국인 배우자의 주민등록등본",
                    "외국인 직업 신고서",
                    "체류지 입증서류",
                    "배우자 실종 사실을 입증하는 서류",
                ],
                conditional=[
                    "실종선고 심판청구 접수증, 실종신고서, 지인 확인서 또는 여성단체 확인서 등 해당 사유 입증서류",
                    "부부 사이에 출생한 자녀가 있는 경우 자녀의 가족관계증명서",
                ],
            ),
            notes=["실종선고 전 단계의 입증자료가 필요한 별도 연장 시나리오입니다."],
        ),
    ],
    ("F-2", "statusChange"): [
        variant(
            variant_id="f-2-7-point-based-talent-status-change",
            label="F-2-7 점수제 우수인재 체류자격 변경",
            status_code="F-2-7",
            scenario="점수제 우수인재 요건을 충족하는 신청인이 F-2-7 거주자격으로 변경을 신청하는 경우",
            page_range="pp. 368-374",
            required_docs=docs(
                common=[
                    "신청서",
                    "여권",
                    "외국인등록증",
                    "사진",
                    "수수료",
                    "체류지 입증서류",
                    "고용계약서",
                ],
                required=["점수표", "점수 항목별 입증서류"],
                conditional=[
                    "해외범죄경력증명서",
                    "가족관계 입증서류",
                    "결핵검진 확인서",
                    "학위증",
                    "재직증명서",
                    "사업자등록증",
                    "법인등기부등본",
                    "소득금액증명 등 해당 항목 입증서류",
                ],
            ),
            notes=[
                "대상 유형별 기본요건과 점수요건을 함께 확인해야 합니다.",
                "통상 총점 80점 이상 요건을 포함하며, 세부 대상 유형별 요건은 공식 매뉴얼 범위에서 별도 확인합니다.",
            ],
        ),
        variant(
            variant_id="f-2-7s-potential-talent-status-change",
            label="F-2-7S 잠재적 우수인재 체류자격 변경",
            status_code="F-2-7S",
            scenario="이공계 특성화 대학 또는 연구기관의 석·박사 학위 취득자·취득예정자가 추천을 받아 F-2-7S로 변경을 신청하는 경우",
            page_range="pp. 369-374",
            required_docs=docs(
                common=[
                    "신청서",
                    "여권",
                    "외국인등록증",
                    "사진",
                    "수수료",
                    "체류지 입증서류",
                ],
                required=[
                    "이공계 특성화 대학 또는 연구기관의 석·박사 학위 취득 또는 취득예정 입증서류",
                    "대학 총장 추천서",
                ],
                conditional=[
                    "해외범죄경력증명서",
                    "가족관계 입증서류",
                    "결핵검진 확인서",
                    "재직증명서, 사업자등록증, 법인등기부등본, 소득금액증명 등 해당 항목 입증서류",
                ],
            ),
            notes=[
                "점수요건 면제 대상인 잠재적 우수인재 시나리오이며 일반 F-2-7과 구분합니다.",
                "추천 대상 범위, 추천 가능 시점, 최초 체류기간 및 이후 연장요건을 공식 매뉴얼에서 함께 확인해야 합니다.",
            ],
        ),
        variant(
            variant_id="f-2-8-tourism-investment-status-change",
            label="F-2-8 관광·휴양시설 투자 거주자격 변경",
            status_code="F-2-8",
            scenario="지정된 관광·휴양시설 등에 투자한 신청인이 F-2-8 거주자격으로 변경을 신청하는 경우",
            page_range="pp. 375-378",
            required_docs=docs(
                common=["신청서", "여권", "외국인등록증", "사진", "수수료"],
                required=["투자 대상과 투자금액을 입증하는 서류", "외국환 반입 관련 입증서류"],
                conditional=[
                    "부동산 매매계약서 및 등기부등본",
                    "회원권 취득 관련 입증서류",
                    "미분양 주택 투자 관련 입증서류",
                    "법인을 통한 간접투자 관련 입증서류",
                    "법인의 현직 임원 또는 주주임을 입증하는 서류",
                    "배우자 또는 미혼 자녀가 함께 신청하는 경우 가족관계 입증서류",
                    "해외범죄경력증명서",
                ],
            ),
            notes=[
                "지정된 투자 대상, 투자 방식, 투자금액 및 자기자금 요건을 공식 매뉴얼에서 함께 확인해야 합니다.",
                "공익사업 투자이민 F-2-12·F-2-13·F-2-14 시나리오와 혼합하지 않습니다.",
            ],
        ),
        variant(
            variant_id="f-2-12-13-14-public-interest-investment-status-change",
            label="F-2-12·13·14 공익사업 투자 거주자격 변경",
            scenario="공익사업 투자이민 제도의 일반형·고액형·퇴직이민형 대상자가 거주자격 변경을 신청하는 경우",
            page_range="pp. 379-385",
            required_docs=docs(
                common=["신청서", "여권 사본", "사진", "수수료"],
                required=["투자금 납부 입증서류", "외국환 반입 관련 입증서류"],
                conditional=[
                    "배우자 또는 미혼 자녀가 함께 신청하는 경우 가족관계 입증서류",
                    "법인을 통한 간접투자 관련 입증서류",
                    "법인의 현직 임원 또는 주주임을 입증하는 서류",
                    "해외범죄경력증명서",
                ],
            ),
            notes=[
                "공익사업 투자 유형별 투자금액과 대상 범위를 공식 매뉴얼에서 확인해야 합니다.",
                "관광·휴양시설 투자 F-2-8 시나리오와 혼합하지 않습니다.",
            ],
        ),
    ],
    ("H-2", "registration"): [
        variant(
            variant_id="h-2-existing-holder-registration",
            label="H-2 기존 체류자 외국인등록",
            status_code="H-2",
            scenario="2026년 2월 12일 이전 H-2 체류자격을 부여받은 기존 체류자가 외국인등록을 하는 경우",
            page_range="PDF pp. 524-525 (embedded manual pp. 4-5)",
            required_docs=docs(
                common=["여권", "최근 6개월 이내 촬영한 컬러 사진", "외국인등록 신청서", "수수료"],
                required=["조기적응프로그램 이수증", "지정병원 발급 건강진단서"],
                conditional=[
                    "재외공관에서 체류자격을 부여받을 때 제출하지 않은 경우 한국어능력 입증서류",
                    "재외공관에서 체류자격을 부여받을 때 제출하지 않은 경우 해외범죄경력증명서",
                    "유학생 부모인 경우 유학생의 재학증명서 및 외국인등록증 사본",
                ],
            ),
            notes=[
                "H-2 신규 발급은 2026년 2월 12일부터 중단되었으며, 이 카드는 기존 H-2 체류자의 등록 시나리오만 다룹니다.",
                "입국일부터 90일 이내 등록 의무를 확인해야 합니다.",
            ],
        ),
    ],
    ("H-2", "workplaceChange"): [
        variant(
            variant_id="h-2-employment-start-workplace-change-report",
            label="H-2 취업개시·근무처변경 신고",
            status_code="H-2",
            scenario="기존 H-2 체류자가 허용 업종에서 취업을 시작하거나 근무처를 변경한 뒤 신고하는 경우",
            page_range="PDF pp. 525-526 (embedded manual pp. 5-6)",
            required_docs=docs(
                common=["취업개시 또는 근무처변경 신고서", "외국인등록증 사본"],
                required=["특례고용가능확인서 사본", "표준근로계약서 사본", "사업자등록증 사본"],
                conditional=["온라인 신고 시 시스템이 요구하는 입력정보"],
            ),
            notes=[
                "취업개시 또는 근무처변경일부터 15일 이내 신고 대상입니다.",
                "이 카드는 허용 업종에서의 신고 제출서류를 안내하며, 취업 가능 업종 전체를 requiredDocs로 평탄화하지 않습니다.",
                "F-4 재외동포 체류자격과 혼동하지 않습니다.",
            ],
        ),
    ],
    ("D-10", "statusChange"): [
        variant(
            variant_id="d-10-1-points-status-change",
            label="D-10-1 점수제 구직 체류자격 변경",
            status_code="D-10-1",
            scenario="점수제 일반 구직활동 대상자가 D-10-1 체류자격으로 변경을 신청하는 경우",
            page_range="pp. 143-149",
            required_docs=docs(
                common=["신청서", "사진", "여권 사본", "수수료", "외국인등록증 사본"],
                required=["구직활동계획서", "학력 입증서류", "체류비 입증서류"],
                conditional=[
                    "대학 순위 입증서류",
                    "근무 경력 입증서류",
                    "국내 연수활동 입증서류",
                    "한국어능력 입증서류",
                    "추천서",
                    "고소득 전문가 입증서류",
                    "그 밖의 점수 항목별 입증서류",
                ],
            ),
            notes=[
                "일반 점수제 구직 시나리오이며 점수제 면제 대상과 구분합니다.",
                "기본항목과 총점 요건, 출신국·기존 체류자격에 따른 별도 점수요건을 공식 매뉴얼에서 확인해야 합니다.",
            ],
        ),
        variant(
            variant_id="d-10-1-first-graduate-status-change",
            label="D-10-1 국내 졸업 후 최초 구직 체류자격 변경",
            status_code="D-10-1",
            scenario="국내 정규 대학을 졸업한 신청인이 졸업 후 최초로 D-10-1 구직 체류자격 변경을 신청하는 경우",
            page_range="p. 149",
            required_docs=docs(
                common=["신청서", "사진", "여권 사본", "수수료", "외국인등록증 사본"],
                required=["구직활동계획서", "국내 정규 대학 전문학사 이상 학위증 또는 졸업증명서", "체류지 입증서류"],
                conditional=[],
            ),
            notes=[
                "국내 정규 대학 졸업 후 최초 변경에 한정된 점수제 면제 시나리오입니다.",
                "이 시나리오에서는 체류비 입증서류 제출이 면제됩니다.",
            ],
        ),
        variant(
            variant_id="d-10-2-tech-startup-status-change",
            label="D-10-2 기술창업준비 체류자격 변경",
            status_code="D-10-2",
            scenario="기술창업 준비활동을 하려는 신청인이 D-10-2 체류자격으로 변경을 신청하는 경우",
            page_range="p. 151",
            required_docs=docs(
                common=["신청서", "사진", "여권 사본", "수수료", "외국인등록증 사본"],
                required=["학력 입증서류", "기술창업계획서", "체류비 입증서류"],
                conditional=[
                    "특허·실용신안·디자인 등록증 사본 또는 출원증명서",
                    "OASIS 교육 이수증 또는 참여 입증서류",
                    "OECD 국가 지식재산권 보유 입증서류",
                ],
            ),
            notes=["기술창업 준비 시나리오이며 일반 구직 D-10-1 및 첨단기술 인턴 D-10-3과 구분합니다."],
        ),
        variant(
            variant_id="d-10-3-high-tech-intern-status-change",
            label="D-10-3 첨단기술 인턴 체류자격 변경",
            status_code="D-10-3",
            scenario="해외 우수대학 첨단기술 분야 학생·졸업자가 국내 적격 기업에서 인턴활동을 위해 D-10-3으로 변경을 신청하는 경우",
            page_range="pp. 151-152",
            required_docs=docs(
                common=["신청서", "사진", "여권 사본", "수수료", "외국인등록증 사본"],
                required=[
                    "인턴활동계획서",
                    "학적 또는 학위 입증서류와 대학 순위 입증서류",
                    "업체·분야·기간을 확인할 수 있는 인턴 근로계약서",
                    "초청기업의 사업자등록증 사본",
                    "초청기업의 고용보험가입자 명부 또는 연구시설·연구인력 입증서류",
                    "초청기업 자격요건 입증서류",
                ],
                conditional=["인턴 근로계약서로 지급 수준을 확인할 수 없는 경우 체류비 입증서류"],
            ),
            notes=[
                "대학 순위, 첨단기술 분야, 인턴 기간, 초청기업 자격요건을 공식 매뉴얼에서 함께 확인해야 합니다.",
                "휴학증명서는 인정될 수 있으나 장기 휴학 제한을 공식 매뉴얼에서 확인해야 합니다.",
            ],
        ),
    ],
    ("D-10", "extension"): [
        variant(
            variant_id="d-10-1-points-extension",
            label="D-10-1 점수제 구직 체류기간 연장",
            status_code="D-10-1",
            scenario="점수제 일반 구직활동 대상자가 D-10-1 체류기간 연장을 신청하는 경우",
            page_range="pp. 155-156",
            required_docs=docs(
                common=["신청서", "사진", "여권 사본", "수수료", "외국인등록증 사본"],
                required=["구직활동계획서", "체류지 입증서류", "체류비 입증서류"],
                conditional=["점수 항목별 평가 입증서류"],
            ),
            notes=["점수제 요건과 연장 단계의 체류기간 범위를 공식 매뉴얼에서 함께 확인해야 합니다."],
        ),
        variant(
            variant_id="d-10-2-tech-startup-extension",
            label="D-10-2 기술창업준비 체류기간 연장",
            status_code="D-10-2",
            scenario="기술창업 준비활동을 계속하는 신청인이 D-10-2 체류기간 연장을 신청하는 경우",
            page_range="p. 157",
            required_docs=docs(
                common=["신청서", "사진", "여권 사본", "수수료", "외국인등록증 사본"],
                required=["기술창업 활동계획서", "체류지 입증서류", "체류비 입증서류"],
                conditional=["K-Startup Grand Challenge 참여 입증서류"],
            ),
            notes=["K-Startup Grand Challenge 참여자는 체류비 입증서류 면제 여부를 공식 매뉴얼에서 확인합니다."],
        ),
        variant(
            variant_id="d-10-3-high-tech-intern-extension",
            label="D-10-3 첨단기술 인턴 체류기간 연장",
            status_code="D-10-3",
            scenario="첨단기술 분야 인턴활동을 계속하는 신청인이 D-10-3 체류기간 연장을 신청하는 경우",
            page_range="p. 157",
            required_docs=docs(
                common=["신청서", "사진", "여권 사본", "수수료", "외국인등록증 사본"],
                required=[
                    "인턴 재직증명서",
                    "초청기업의 사업자등록증 사본",
                    "초청기업의 고용보험가입자 명부 또는 연구시설·연구인력 입증서류",
                    "초청기업 자격요건 유지 입증서류",
                    "인턴 또는 구직 활동계획서",
                    "체류지 입증서류",
                ],
                conditional=["근로계약서로 지급 수준을 확인할 수 없는 경우 체류비 입증서류"],
            ),
            notes=["인턴활동의 계속성과 초청기업 자격요건 유지 여부를 공식 매뉴얼에서 확인해야 합니다."],
        ),
    ],
    ("F-4", "statusChange"): [
        variant(
            variant_id="f-4-overseas-korean-status-change",
            label="F-4 재외동포 국내 체류자격 변경",
            status_code="F-4",
            scenario="국내에서 발급하거나 전산으로 확인할 수 있는 입증서류를 갖춘 재외동포가 F-4 체류자격 변경을 신청하는 경우",
            page_range="PDF pp. 528-530 (embedded manual pp. 8-10)",
            required_docs=docs(
                common=["통합신청서(별지 제1호 서식)", "여권 및 사본", "사진", "수수료", "체류지 입증서류"],
                required=["재외동포 해당 여부 입증서류", "한국어능력 입증서류", "해외범죄경력증명서"],
                conditional=["결핵진단서", "조기적응프로그램 이수증", "한국어능력 또는 조기적응프로그램 면제 입증서류"],
            ),
            notes=[
                "국내에서 발급하거나 전산으로 확인할 수 있는 서류를 갖춘 국내 변경 시나리오입니다.",
                "H-2 방문취업 체류자격과 혼동하지 않습니다.",
            ],
        ),
    ],
    ("F-4", "registration"): [
        variant(
            variant_id="f-4-domestic-residence-report",
            label="F-4 국내거소신고",
            status_code="F-4",
            scenario="90일을 초과해 국내에 체류하려는 F-4 재외동포가 국내거소신고를 하는 경우",
            page_range="PDF p. 530 (embedded manual p. 10)",
            required_docs=docs(
                common=["통합신청서(별지 제1호 서식)", "여권 및 사본", "사진", "수수료"],
                required=["체류지 입증서류"],
                conditional=["조기적응프로그램 이수증", "조기적응프로그램 면제 입증서류"],
            ),
            notes=["90일을 초과하여 체류하려는 경우의 국내거소신고 시나리오입니다."],
        ),
    ],
    ("F-4", "extension"): [
        variant(
            variant_id="f-4-overseas-korean-extension",
            label="F-4 재외동포 체류기간 연장",
            status_code="F-4",
            scenario="F-4 재외동포가 체류기간 연장을 신청하는 경우",
            page_range="PDF pp. 530-531 (embedded manual pp. 10-11)",
            required_docs=docs(
                common=["신청서", "수수료"],
                required=["한국어능력 입증서류", "체류지 입증서류"],
                conditional=["한국어능력 면제 입증서류"],
            ),
            notes=[
                "한국어능력 수준과 법 위반 여부 등에 따라 체류기간 부여 범위가 달라질 수 있습니다.",
                "최대 체류기간과 제한 사유를 공식 매뉴얼에서 확인해야 합니다.",
            ],
        ),
    ],
}


def _serialize(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _procedure_shell(procedure_key: str) -> dict[str, Any]:
    return {
        "available": True,
        "summary": PROCEDURE_SUMMARIES[procedure_key],
        "requiredDocs": copy.deepcopy(EMPTY_DOCS),
        "manualRefs": [],
        "notes": [SCOPE_NOTE],
        "variants": [],
    }


def apply_variants(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    updated = copy.deepcopy(data)
    by_code = {record.get("code"): record for record in updated}

    for (status_code, procedure_key), variants in VARIANTS.items():
        record = by_code.get(status_code)
        if record is None:
            raise ValueError(f"missing expected parent status: {status_code}")

        procedures = record.setdefault("procedures", {})
        if not isinstance(procedures, dict):
            raise ValueError(f"{status_code}.procedures must be an object")
        procedure = procedures.setdefault(procedure_key, _procedure_shell(procedure_key))
        if not isinstance(procedure, dict):
            raise ValueError(f"{status_code}.procedures.{procedure_key} must be an object")

        procedure["available"] = True
        legacy_summary = procedure.get("summaryKo")
        if legacy_summary == PROCEDURE_SUMMARIES[procedure_key] and "summary" not in procedure:
            procedure["summary"] = procedure.pop("summaryKo")
        procedure.setdefault("summary", PROCEDURE_SUMMARIES[procedure_key])
        procedure.setdefault("requiredDocs", copy.deepcopy(EMPTY_DOCS))
        procedure.setdefault("manualRefs", [])
        procedure_notes = procedure.setdefault("notes", [])
        if not isinstance(procedure_notes, list):
            raise ValueError(f"{status_code}.procedures.{procedure_key}.notes must be a list")
        if SCOPE_NOTE not in procedure_notes:
            procedure_notes.append(SCOPE_NOTE)

        existing = {item.get("id"): item for item in procedure.setdefault("variants", [])}

        for item in variants:
            current = existing.get(item["id"])
            if current is None:
                procedure["variants"].append(copy.deepcopy(item))
                continue
            if current != item:
                raise ValueError(
                    f"refusing to overwrite existing variant {status_code}/{procedure_key}/{item['id']}"
                )

    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if either target needs an update")
    args = parser.parse_args()

    changed: list[Path] = []
    for target in TARGETS:
        original = target.read_text(encoding="utf-8")
        updated = _serialize(apply_variants(json.loads(original)))
        if original == updated:
            print(f"[OK] {target.relative_to(ROOT)}")
            continue
        if args.check:
            changed.append(target)
            print(f"[NEEDS UPDATE] {target.relative_to(ROOT)}")
            continue
        target.write_text(updated, encoding="utf-8")
        print(f"[UPDATED] {target.relative_to(ROOT)}")

    if changed:
        print("Run this helper without --check to update the mirrored datasets.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
