#!/usr/bin/env python3
"""doc_master.json coverage + integrity fixes (2026-06-08).

Adds source-grounded generic document definitions newly referenced by the
manual-coverage corrections and restores parity ids that existed only in
the frontend DOC_DICT. Idempotent: merges by id.

Run: python3 scripts/apply_doc_master_coverage_2026_06_08.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC_MASTER = REPO / "doc_master.json"

# New generic documents referenced by the 2026-06-08 manual coverage patch.
NEW_DOCS = [
    ("doc_labor_complaint", "노동관서 진정서 사본",
     "Labor office complaint copy",
     "고용노동부(노동관서)에 제출한 임금체불 진정서 사본."),
    ("doc_unpaid_wage_confirmation", "체불금품 확인원",
     "Unpaid wage confirmation",
     "노동부가 발급한 체불금품 확인원 등 임금체불 사실을 입증하는 서류."),
    ("doc_litigation_document", "소송 관련 서류",
     "Litigation documents",
     "소장 사본, 소송제기 증명원, 법률구조결정서 등 진행 중인 소송을 입증하는 서류."),
    ("doc_medical_treatment_proof", "치료·요양 필요성 입증서류",
     "Medical treatment necessity proof",
     "의료기관에서 발행한 진단서·소견서 등 치료 또는 장기요양의 필요성을 입증하는 서류."),
    ("doc_family_guardian_proof", "가족관계·보호자 입증서류",
     "Family relationship / guardian proof",
     "가족관계증명서 등 가족·보호자 관계를 입증하는 서류 (가족·보호자 동반 시 해당)."),
    ("doc_livelihood_review", "생계유지능력 심사확인서",
     "Livelihood capacity review form",
     "생계유지능력 심사확인서. 체류기간 연장 심사 시 활용."),
    ("doc_injury_or_death_proof", "산재·사고·사망 입증서류",
     "Industrial accident / injury / death proof",
     "산재보상심사청구서·재심청구서, 사고·사망 사실 확인서류 등 산업재해·사고·사망을 입증하는 서류."),
    ("doc_pregnancy_birth_proof", "임신·출산 입증서류",
     "Pregnancy / childbirth proof",
     "진단서 등 임신·출산 사실 및 즉시 출국이 곤란함을 증명할 수 있는 서류."),
    ("doc_humanitarian_reason_proof", "인도적 사유 입증서류",
     "Humanitarian reason proof",
     "성폭력·피해사실 확인서류, 권리구제 절차 진행 입증서류 등 인도적 고려가 필요한 사유를 입증하는 서류."),
    ("doc_seasonal_worker_recommendation", "계절근로자 추천·배정 서류",
     "Seasonal worker recommendation",
     "지자체의 계절근로자 추천·배정 관련 서류."),
    ("doc_mou_local_government", "지자체 간 계절근로 MOU 서류",
     "Local-government seasonal-work MOU",
     "국내·외국 지방자치단체 간 체결한 계절근로 수급 관련 MOU 서류."),
    ("doc_digital_nomad_income_proof", "디지털노마드 소득 입증서류",
     "Digital nomad income proof",
     "디지털노마드(워케이션) 비자 소득 요건을 입증하는 연간 소득 증빙 서류."),
    ("doc_remote_work_employment_proof", "원격근무·해외 재직 입증서류",
     "Remote work / overseas employment proof",
     "해외 소속 기업 재직 및 원격근무 사실을 입증하는 서류."),
    ("doc_private_medical_insurance", "민간 의료보험 가입 입증서류",
     "Private medical insurance proof",
     "본인 및 동반가족의 의료비 보장을 위한 민간 의료보험 가입을 입증하는 서류."),
    ("doc_startup_korea_recommendation", "스타트업 코리아 추천·창업 입증서류",
     "Startup Korea recommendation",
     "스타트업 코리아 특별비자(D-8-4S) 관련 부처 추천·창업 사실을 입증하는 서류."),
    ("doc_kstar_university_recommendation", "K-STAR 참여대학 추천서",
     "K-STAR participating-university recommendation",
     "K-STAR 비자트랙 참여대학의 추천서 등 K-STAR 자격 입증서류."),
]

# Parity ids that previously existed only in the frontend DOC_DICT.
PARITY_DOCS = [
    ("doc_address_change", "체류지 변경 신고서류",
     "Address change report",
     "체류지 변경 신고서(통합신청서), 신분증, 체류지 입증서류."),
    ("doc_arc_reissue", "외국인등록증 재발급 서류",
     "ARC reissue documents",
     "외국인등록증 재발급 신청서(통합신청서), 여권, 사유 소명 서류(경찰서 분실신고증 등), 사진 1매."),
    ("doc_fam_rel_kr", "가족관계증명서(상세, 한국인 명의)",
     "Korean family relation certificate (detailed)",
     "한국인 배우자 명의 가족관계증명서(상세). 자녀 양육 시 각 자녀 명의로 개별 발급."),
    ("doc_passport_change", "여권 등록사항 변경 신고서류",
     "Passport change report",
     "등록사항 변경 신고서(통합신청서), 신여권 원본 및 사본, 기존 외국인등록증."),
    ("doc_score", "점수제 평가표 및 증빙서류",
     "Points-table and supporting evidence",
     "점수제 평가표 및 해당 항목별 증빙서류 (점수제 적용 비자에 한함)."),
]


def main():
    data = json.loads(DOC_MASTER.read_text(encoding="utf-8"))
    by_id = {x["id"]: x for x in data}
    added = 0
    for doc_id, ko, en, desc in NEW_DOCS + PARITY_DOCS:
        if doc_id in by_id:
            continue
        data.append({"id": doc_id, "ko_name": ko, "en_name": en,
                     "description": desc})
        added += 1
    DOC_MASTER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print(f"doc_master.json: {added} new entries added, total {len(data)}")


if __name__ == "__main__":
    main()
