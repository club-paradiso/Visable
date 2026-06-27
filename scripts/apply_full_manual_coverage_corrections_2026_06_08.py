#!/usr/bin/env python3
"""Source-grounded full manual coverage corrections (2026-06-08).

Audits the official 2026.5 visa issuance manual and 2026.5/2026-06-01
stay/residence manual against visa_data.json and patches missing or
unsearchable *active* codes/subcodes, fixes label conflicts, and
quarantines deprecated/reference-only/internal markers with written
reasons.

Source files (do not edit the PDFs):
  - docs/source-manuals/2026-05/visa_manual_2026_05.pdf   (484 pp; 사증발급)
  - docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf (777 pp; 체류민원)

Every patched record/subcode carries manualRefs metadata
(manualName / manualVersion / sourceDate / sourceFile / pageRange /
confidence / needsManualReview). The script is idempotent: re-running
merges by code rather than duplicating.

Run:  python3 scripts/apply_full_manual_coverage_corrections_2026_06_08.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VISA_DATA = REPO / "visa_data.json"

STALE_STAY = "docs/source-manuals/2026-05/stay_manual_2026_05.pdf"
CURRENT_STAY = "docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf"
CURRENT_VISA = "docs/source-manuals/2026-05/visa_manual_2026_05.pdf"


# --------------------------------------------------------------------------- #
# manualRefs helpers
# --------------------------------------------------------------------------- #
def stay_ref(page_range, *, confidence="manual_page_extract_needs_review",
             needs_review=True, section=None):
    ref = {
        "manualName": "체류민원",
        "manualVersion": "2026.5",
        "sourceDate": "2026-06-01",
        "sourceFile": CURRENT_STAY,
        "pageRange": page_range,
        "confidence": confidence,
        "needsManualReview": needs_review,
    }
    if section:
        ref["sectionTitle"] = section
    return ref


def visa_ref(page_range, *, confidence="manual_page_extract_needs_review",
             needs_review=True, section=None):
    ref = {
        "manualName": "사증민원",
        "manualVersion": "2026.5",
        "sourceDate": "2026-05-21",
        "sourceFile": CURRENT_VISA,
        "pageRange": page_range,
        "confidence": confidence,
        "needsManualReview": needs_review,
    }
    if section:
        ref["sectionTitle"] = section
    return ref


def sub(code, name, *, addReq="", addReqDocs=None, note="", aliases=None,
        manualRefs=None, status="active", group=None, statusNote=None,
        needsManualReview=True):
    """Build a subcode object using the repo's existing subcode schema
    ({code,name,addReq,addReqDocs,note}) plus searchable/source fields."""
    obj = {
        "code": code,
        "name": name,
        "nameKo": name,
        "addReq": addReq,
        "addReqDocs": addReqDocs or [],
        "note": note,
        "searchAliases": sorted(set((aliases or []) + [code, code.replace("-", "")])),
        "status": status,
        "needsManualReview": needsManualReview,
        "manualRefs": manualRefs or [],
    }
    if group:
        obj["group"] = group
    if statusNote:
        obj["statusNote"] = statusNote
    return obj


# --------------------------------------------------------------------------- #
# generic merge utilities (idempotent)
# --------------------------------------------------------------------------- #
def get_record(data, code):
    for r in data:
        if r.get("code") == code:
            return r
    return None


def merge_subcodes(record, new_subs):
    """Merge into every subcode array the record carries.

    Some legacy records hold BOTH a lowercase ``subcodes`` (richer schema,
    read first by the frontend's getVisaSubcodes) and an uppercase
    ``subCodes`` mirror. Writing to only one leaves the other stale and the
    addition invisible — so we merge by code into all present arrays."""
    keys = [k for k in ("subcodes", "subCodes") if isinstance(record.get(k), list)]
    if not keys:
        record["subCodes"] = []
        keys = ["subCodes"]
    for key in keys:
        existing = record[key]
        by_code = {s.get("code"): s for s in existing}
        for ns in new_subs:
            code = ns["code"]
            if code in by_code:
                by_code[code].update(ns)  # update in place; keep extra fields
            else:
                existing.append(dict(ns))
                by_code[code] = existing[-1]


def merge_aliases(record, aliases):
    cur = record.get("searchAliases") or []
    record["searchAliases"] = sorted(set(cur) | set(aliases))


def count_stale_paths(data):
    """Count (but do NOT rewrite) pre-existing May stay-manual refs.

    The May (2026-05) and June (2026-06-01) stay manuals are 1:1 by
    page-text hashing, so the existing May-path citations remain accurate.
    Migrating those pre-existing scenario-variant refs to the June path is
    deliberately deferred: the repo's own regression tests
    (test_scenario_procedure_variants.py) currently codify the May path as
    the expected sourceFile, and the populate_*/promote_* idempotency
    --check tests are already red on the base branch (an incomplete prior
    migration). All NEW/changed records added here cite the current June
    manual via stay_ref(); completing the dataset-wide migration is tracked
    as a follow-up so this PR introduces no test regressions."""
    n = [0]

    def walk(o):
        if isinstance(o, dict):
            if o.get("sourceFile") == STALE_STAY:
                n[0] += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(data)
    return n[0]


# --------------------------------------------------------------------------- #
# G-1 — full re-grounding from stay manual pp. 497–512 (기타(G-1))
# --------------------------------------------------------------------------- #
def patch_g1(data):
    r = get_record(data, "G-1")
    g1_subs = [
        sub("G-1-1", "산업재해 청구 및 치료 중인 사람과 그 가족",
            addReq="산재보상심사 청구·재심청구서, 산재 병원진단서, 생계유지능력 심사확인서.",
            addReqDocs=["doc_injury_or_death_proof", "doc_medical_treatment_proof",
                        "doc_livelihood_review", "doc_family_guardian_proof"],
            note="산재보상 완료·입원치료 종료 시까지. 가족(배우자·직계가족) 포함.",
            aliases=["산업재해", "산재", "산재 치료"], group="산재·치료",
            manualRefs=[stay_ref("p. 503")]),
        sub("G-1-2", "질병·사고로 치료 중인 사람과 그 가족",
            addReq="의료기관 소견서 등 치료 필요성 입증서류, 치료·체류비용 조달능력 입증서류, 신원보증서.",
            addReqDocs=["doc_medical_treatment_proof", "doc_finance",
                        "doc_guarantee", "doc_livelihood_review"],
            note="장기치료가 불가피한 등록외국인·단기사증 입국자. 단, 검진·질병치료 목적 단기사증 입국자는 외국인환자(G-1-10)로 변경.",
            aliases=["질병 치료", "사고 치료", "장기치료"], group="산재·치료",
            manualRefs=[stay_ref("pp. 503-504")]),
        sub("G-1-3", "각종 소송 진행 중인 사람",
            addReq="소장 사본·소송제기 증명원·법률구조결정서 등 소송 관련 서류, 신원보증서.",
            addReqDocs=["doc_litigation_document", "doc_guarantee",
                        "doc_family_guardian_proof", "doc_livelihood_review"],
            note="민사·형사·가사·행정 소송 수행 중인 사람. 체류허가기간 6월 범위 이내.",
            aliases=["소송", "민사소송", "형사소송", "행정소송", "가사소송"],
            group="소송·임금", manualRefs=[stay_ref("p. 504")]),
        sub("G-1-4", "임금체불로 노동관서에서 중재 중인 사람",
            addReq="노동부 제출 진정서 사본, 노동부 발급 체불금품 확인원 등, 신원보증서.",
            addReqDocs=["doc_labor_complaint", "doc_unpaid_wage_confirmation",
                        "doc_guarantee", "doc_livelihood_review"],
            note="고용노동부 체불임금 진정 중재 중이거나 미해결로 민사소송 중인 사람. 6월 범위 내.",
            aliases=["임금체불", "체불임금", "체불", "노동관서 중재"],
            group="소송·임금", manualRefs=[stay_ref("pp. 504-505")]),
        sub("G-1-5", "난민신청자",
            addReq="난민인정신청 접수증 등 난민신청자임을 입증할 수 있는 서류, 체류지 입증서류.",
            addReqDocs=["doc_refugee", "doc_residence_proof_generic"],
            note="대한민국 안에서 난민인정을 신청한 사람. 신청 6개월 경과 후 체류자격외 취업활동 허가 가능.",
            aliases=["난민신청자", "난민 신청", "난민인정 신청"],
            group="난민·인도적", manualRefs=[stay_ref("p. 505")]),
        sub("G-1-6", "난민불인정자 중 인도적 체류허가자",
            addReq="인도적 체류허가 통지서 등 인도적 체류허가자임을 입증하는 서류, 체류지 입증서류.",
            addReqDocs=["doc_humanitarian_reason_proof", "doc_residence_proof_generic"],
            note="난민불인정자 중 인도적 체류허가를 받은 사람. 통보일부터 체류기간 1년 부여.",
            aliases=["인도적 체류허가", "인도적체류", "인도적 체류자"],
            group="난민·인도적", manualRefs=[stay_ref("p. 505")]),
        sub("G-1-7", "사고 등으로 사망한 사람의 가족",
            addReq="사망사실 및 가족관계 입증서류.",
            addReqDocs=["doc_injury_or_death_proof", "doc_family_guardian_proof"],
            note="사고 등으로 사망한 사람의 가족. 성폭력피해자 등과 함께 체류자격외 활동허가 대상.",
            aliases=["사망 가족", "유가족"], group="아동·가족",
            manualRefs=[stay_ref("pp. 497-498")]),
        sub("G-1-8", "장기체류 아동",
            addReq="장기체류 아동 관련 입증서류 (매뉴얼 해당 항목 및 관할기관 안내 기준).",
            addReqDocs=["doc_case_specific_evidence"],
            note="장기체류 아동(G-1-8, 13, 14) 체계로 분류. 세부 구분·요건은 관할기관 안내 확인 필요.",
            aliases=["장기체류 아동", "장기 체류 아동", "아동"], group="아동·가족",
            manualRefs=[stay_ref("pp. 2-3, 497")], needsManualReview=True),
        sub("G-1-9", "임신·출산 등 인도적 배려가 불가피한 사람",
            addReq="진단서 등 임신·출산 사실을 증명할 수 있는 서류, 신원보증서.",
            addReqDocs=["doc_pregnancy_birth_proof", "doc_guarantee"],
            note="임신·출산 등으로 즉시 출국이 곤란한 사람. 체류기간 1년 부여.",
            aliases=["임신", "출산", "임신 출산"], group="난민·인도적",
            manualRefs=[stay_ref("pp. 505-506")]),
        sub("G-1-10", "외국인환자 (입국 후 장기치료가 필요한 환자와 그 가족)",
            addReq="의료기관 소견서 등 장기치료 필요성 입증서류, 치료·체류비용 조달능력 입증서류.",
            addReqDocs=["doc_medical_treatment_proof", "doc_finance",
                        "doc_family_guardian_proof"],
            note="B-1·B-2·C-3 입국 후 장기치료·요양이 필요한 환자와 동반가족·간병인. 1년 이내.",
            aliases=["외국인환자", "치료요양", "장기치료", "메디컬"],
            group="산재·치료", manualRefs=[stay_ref("p. 506")]),
        sub("G-1-11", "성폭력피해자 등 인도적 고려가 필요한 사람",
            addReq="소송관련 서류 등 권리구제 입증서류, 신원보증서.",
            addReqDocs=["doc_humanitarian_reason_proof", "doc_litigation_document",
                        "doc_guarantee"],
            note="성폭력범죄·성매매 강요·상습폭행·학대 등 피해로 민·형사상 권리구제 절차 진행 중인 사람. 1년 부여.",
            aliases=["성폭력피해자", "성폭력 피해", "권리구제", "인도적 고려"],
            group="난민·인도적", manualRefs=[stay_ref("pp. 506-507")]),
        sub("G-1-12", "인도적 체류허가자의 가족",
            addReq="가족관계 입증서류, 체류지 입증서류.",
            addReqDocs=["doc_family_guardian_proof", "doc_residence_proof_generic"],
            note="인도적 체류허가자의 배우자 및 미성년 자녀(배우자 있는 미성년자 제외). 인도적 체류허가자의 체류기간 범위 내.",
            aliases=["인도적 체류허가자 가족", "인도적 체류 가족"],
            group="아동·가족", manualRefs=[stay_ref("pp. 507-508")]),
        sub("G-1-13", "장기체류 아동 (장기체류 아동 체계)",
            addReq="장기체류 아동 관련 입증서류 (매뉴얼 해당 항목 및 관할기관 안내 기준).",
            addReqDocs=["doc_case_specific_evidence"],
            note="장기체류 아동(G-1-8, 13, 14) 체계로 분류. 정확한 세부 구분·요건은 관할기관 안내 확인 필요.",
            aliases=["장기체류 아동"], group="아동·가족",
            manualRefs=[stay_ref("pp. 2-3")], needsManualReview=True),
        sub("G-1-14", "장기체류 아동 (장기체류 아동 체계)",
            addReq="장기체류 아동 관련 입증서류 (매뉴얼 해당 항목 및 관할기관 안내 기준).",
            addReqDocs=["doc_case_specific_evidence"],
            note="장기체류 아동(G-1-8, 13, 14) 체계로 분류. 정확한 세부 구분·요건은 관할기관 안내 확인 필요.",
            aliases=["장기체류 아동"], group="아동·가족",
            manualRefs=[stay_ref("pp. 2-3")], needsManualReview=True),
        sub("G-1-99", "기타 사유에 해당되는 사람",
            addReq="출생증명서 등 부모와의 관계 입증서류 및 미성년 자녀의 나이 확인서류.",
            addReqDocs=["doc_basic", "doc_family_guardian_proof"],
            note="기타 법무부장관이 인정하는 사유 해당자(예: 난민신청자(G-1-5)의 국내 출생 17세 미만 자녀). 세부 제출범위는 관할기관 확인 필요.",
            aliases=["기타", "기타 사유"], group="아동·가족",
            manualRefs=[stay_ref("p. 503, 507")], needsManualReview=True),
        # Quarantined: G-1-19 is referenced only as a prerequisite marker for
        # E-8-5/E-8-6 seasonal-work re-entry recommendation in the visa manual;
        # it is NOT given user-facing status guidance in the stay manual G-1
        # section. Searchable but flagged reference_only.
        sub("G-1-19", "기타(G-1) 계절근로 참여자 (재입국 추천 연계 표기)",
            addReq="",
            addReqDocs=[],
            note="계절근로(E-8-5·E-8-6) 재입국 추천 연계 표기로만 매뉴얼에 등장합니다. 독립적인 사용자 안내용 체류자격 항목이 아니며, 실제 절차는 관할기관 확인이 필요합니다.",
            aliases=["G-1-19", "계절근로 기타"], group="기타",
            status="reference_only",
            statusNote="사증발급 안내매뉴얼 계절근로(E-8) 항목의 재입국 추천 연계 표기. 독립 체류자격 안내 항목 아님.",
            manualRefs=[visa_ref("pp. 278-279", confidence="reference_only")],
            needsManualReview=True),
    ]
    merge_subcodes(r, g1_subs)
    merge_aliases(r, [s["code"] for s in g1_subs]
                  + ["G-1", "G1", "기타비자", "기타 체류자격"])
    return len(g1_subs)


# --------------------------------------------------------------------------- #
# C-3 — add 도착관광(C-3-7, active) + 교대선원(C-3-11, abolished 2022.6)
# --------------------------------------------------------------------------- #
def patch_c3(data):
    r = get_record(data, "C-3")
    subs = [
        sub("C-3-7", "도착관광",
            addReq="입국목적 입증자료, 왕복항공권 등.",
            addReqDocs=["doc_flight", "doc_purpose"],
            note="공항에서 도착비자를 받아 입국하는 관광객. 사증발급 안내매뉴얼 C-3 약호표에 포함.",
            aliases=["도착관광", "도착비자", "도착 관광"], group="관광",
            manualRefs=[visa_ref("p. 27")]),
        sub("C-3-11", "교대선원 (폐지)",
            addReq="",
            addReqDocs=[],
            note="코로나19 관련 한시적 지침으로 '22.6. 사증발급 정상화에 따라 폐지된 약호입니다. 현재 발급되지 않습니다.",
            aliases=["교대선원"], group="기타",
            status="deprecated",
            statusNote="코로나19 한시 지침. 2022.6. 사증발급 정상화로 폐지(사증발급 안내매뉴얼).",
            manualRefs=[visa_ref("p. 33", confidence="deprecated_source_confirmed",
                                 needs_review=False)],
            needsManualReview=False),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, ["C-3-7", "도착관광", "C-3-11", "교대선원"])
    return len(subs)


# --------------------------------------------------------------------------- #
# C-4 — seasonal short-term (C-4-1~4 visa issuance suspended from 2025) +
#        C-4-5 (계절근로 외 단기취업, active)
# --------------------------------------------------------------------------- #
def patch_c4(data):
    r = get_record(data, "C-4")
    seasonal_note = ("계절근로 단기취업 사증(C-4-1~4)은 '25년부터 발급이 중단되었습니다. "
                     "현행 계절근로는 계절근로(E-8) 자격으로 운영됩니다.")
    subs = [
        sub("C-4-1", "계절근로 단기취업 — MOU 체결 외국지자체, 농업 (2025년 발급중단)",
            note=seasonal_note, aliases=["계절근로", "단기취업 계절근로"],
            group="농업", status="suspended",
            statusNote="'25년부터 단기취업 계절근로(C-4-1~4) 사증발급 중단. 현행은 E-8.",
            manualRefs=[visa_ref("pp. 277-278", needs_review=False,
                                 confidence="suspended_source_confirmed")],
            needsManualReview=False),
        sub("C-4-2", "계절근로 단기취업 — 결혼이민자 추천 친척, 농업 (2025년 발급중단)",
            note=seasonal_note, aliases=["계절근로"], group="농업", status="suspended",
            statusNote="'25년부터 단기취업 계절근로(C-4-1~4) 사증발급 중단. 현행은 E-8.",
            manualRefs=[visa_ref("pp. 277-278", needs_review=False,
                                 confidence="suspended_source_confirmed")],
            needsManualReview=False),
        sub("C-4-3", "계절근로 단기취업 — MOU 체결 외국지자체, 어업 (2025년 발급중단)",
            note=seasonal_note, aliases=["계절근로"], group="어업", status="suspended",
            statusNote="'25년부터 단기취업 계절근로(C-4-1~4) 사증발급 중단. 현행은 E-8.",
            manualRefs=[visa_ref("pp. 277-278", needs_review=False,
                                 confidence="suspended_source_confirmed")],
            needsManualReview=False),
        sub("C-4-4", "계절근로 단기취업 — 결혼이민자 추천 친척, 어업 (2025년 발급중단)",
            note=seasonal_note, aliases=["계절근로"], group="어업", status="suspended",
            statusNote="'25년부터 단기취업 계절근로(C-4-1~4) 사증발급 중단. 현행은 E-8.",
            manualRefs=[visa_ref("pp. 277-278", needs_review=False,
                                 confidence="suspended_source_confirmed")],
            needsManualReview=False),
        sub("C-4-5", "계절근로 외 단기취업",
            addReq="입국목적·초청 입증자료, 고용·계약 관련 서류 등 (직종별 첨부서류는 매뉴얼 확인).",
            addReqDocs=["doc_invitation", "doc_purpose", "doc_emp_contract"],
            note="공연·강연·기술지도·모델 등 90일 이하 단기 수익활동. 단순노무 직종은 해당하지 않음.",
            aliases=["단기취업", "계절근로 외 단기취업", "단기 취업"], group="기타",
            manualRefs=[visa_ref("pp. 277-278")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, [s["code"] for s in subs] + ["계절근로", "단기취업"])
    return len(subs)


# --------------------------------------------------------------------------- #
# E-8 — seasonal worker (active path). Visa manual pp. 277–279.
# --------------------------------------------------------------------------- #
def patch_e8(data):
    r = get_record(data, "E-8")
    rec_docs = ["doc_seasonal_worker_recommendation", "doc_mou_local_government",
                "doc_emp_contract"]
    subs = [
        sub("E-8-1", "계절근로 — 국내지자체·외국지자체 간 MOU 방식, 농업",
            addReqDocs=rec_docs, note="MOU 체결 외국지자체가 주민 추천 → 농가 배정 → 8개월 이내 종사.",
            aliases=["계절근로", "농업 계절근로", "MOU 계절근로"], group="농업",
            manualRefs=[visa_ref("pp. 278-279")]),
        sub("E-8-2", "계절근로 — 결혼이민자가 해외 거주 4촌 이내 친척 추천, 농업",
            addReqDocs=rec_docs + ["doc_fam_rel"],
            note="결혼이민자(국적 취득자 포함)가 해외 거주 4촌 이내 친척 추천 → 농가 배정.",
            aliases=["계절근로", "결혼이민자 친척 계절근로"], group="가족추천",
            manualRefs=[visa_ref("pp. 278-279")]),
        sub("E-8-3", "계절근로 — 국내지자체·외국지자체 간 MOU 방식, 어업",
            addReqDocs=rec_docs, note="MOU 체결 외국지자체가 주민 추천 → 어가 배정 → 8개월 이내 종사.",
            aliases=["계절근로", "어업 계절근로", "MOU 계절근로"], group="어업",
            manualRefs=[visa_ref("pp. 278-279")]),
        sub("E-8-4", "계절근로 — 결혼이민자가 해외 거주 4촌 이내 친척 추천, 어업",
            addReqDocs=rec_docs + ["doc_fam_rel"],
            note="결혼이민자(국적 취득자 포함)가 해외 거주 4촌 이내 친척 추천 → 어가 배정.",
            aliases=["계절근로", "결혼이민자 친척 계절근로"], group="가족추천",
            manualRefs=[visa_ref("pp. 278-279")]),
        sub("E-8-5", "계절근로 — 기타(G-1) 자격 활동 후 재입국 추천, 농업",
            addReqDocs=rec_docs,
            note="기타(G-1-19) 자격으로 농업분야 계절근로 참여 후 고용주가 재고용 추천 → 농가 배정.",
            aliases=["계절근로", "재입국 계절근로"], group="농업",
            manualRefs=[visa_ref("pp. 278-279")]),
        sub("E-8-6", "계절근로 — 기타(G-1) 자격 활동 후 재입국 추천, 어업",
            addReqDocs=rec_docs,
            note="기타(G-1-19) 자격으로 어업분야 계절근로 참여 후 고용주가 재고용 추천 → 어가 배정.",
            aliases=["계절근로", "재입국 계절근로"], group="어업",
            manualRefs=[visa_ref("pp. 278-279")]),
        sub("E-8-7", "계절근로 — 유학생(D-2)의 부모, 농업",
            addReqDocs=rec_docs + ["doc_fam_rel"],
            note="요건을 충족한 유학(D-2) 자격자가 부모를 계절근로자로 초청 → 농가 배정.",
            aliases=["계절근로", "유학생 부모 계절근로"], group="가족추천",
            manualRefs=[visa_ref("pp. 278-279")]),
        sub("E-8-8", "계절근로 — 유학생(D-2)의 부모, 어업",
            addReqDocs=rec_docs + ["doc_fam_rel"],
            note="요건을 충족한 유학(D-2) 자격자가 부모를 계절근로자로 초청 → 어가 배정.",
            aliases=["계절근로", "유학생 부모 계절근로"], group="가족추천",
            manualRefs=[visa_ref("pp. 278-279")]),
        sub("E-8-99", "계절근로 — 언어소통 도우미 등 기타 보조 인력",
            addReqDocs=rec_docs,
            note="해외 지자체에서 언어소통 도우미 등 관리 목적 인력 파견 시 국내 지자체 신청 → 초청.",
            aliases=["계절근로", "언어소통 도우미", "계절근로 보조인력"], group="기타",
            manualRefs=[visa_ref("pp. 278-279")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, [s["code"] for s in subs]
                  + ["계절근로", "계절근로자", "농업 계절근로", "어업 계절근로"])
    return len(subs)


# --------------------------------------------------------------------------- #
# D-8 — add D-8-4S (스타트업 코리아 특별비자, active)
# --------------------------------------------------------------------------- #
def patch_d8(data):
    r = get_record(data, "D-8")
    subs = [
        sub("D-8-4S", "스타트업 코리아 특별비자 (기술창업 특례)",
            addReq="스타트업 코리아 특별비자 관련 부처 추천·창업 입증서류 등 (매뉴얼 확인).",
            addReqDocs=["doc_startup_korea_recommendation", "doc_biz_reg"],
            note="기술창업(D-8-4) 중 스타트업 코리아 특별비자 트랙. 세부 요건·서류는 사증발급 안내매뉴얼 확인 필요.",
            aliases=["스타트업 코리아", "스타트업코리아", "기술창업 특별비자",
                     "startup korea", "D-8-4S"], group="기술창업",
            manualRefs=[visa_ref("pp. 106-107")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, ["D-8-4S", "스타트업 코리아", "스타트업코리아", "startup korea"])
    return len(subs)


# --------------------------------------------------------------------------- #
# D-9 — add D-9-5 (유학생 무역경영자, active)
# --------------------------------------------------------------------------- #
def patch_d9(data):
    r = get_record(data, "D-9")
    subs = [
        sub("D-9-5", "유학생 무역경영자",
            addReq="무역·경영 활동 입증서류, 재정능력(본인 잔고증명 등) 입증서류 (매뉴얼 확인).",
            addReqDocs=["doc_biz_reg", "doc_finance", "doc_bank_bal"],
            note="국내 유학 후 무역·경영 활동을 하는 사람. 국내 형성 자금은 본인 잔고증명 등으로 확인.",
            aliases=["유학생 무역경영", "유학생 무역경영자", "D-9-5"], group="경영",
            manualRefs=[stay_ref("p. 133")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, ["D-9-5", "유학생 무역경영자"])
    return len(subs)


# --------------------------------------------------------------------------- #
# D-3 — D-3-1 legacy registration marker (registered until 2006.12.31)
# --------------------------------------------------------------------------- #
def patch_d3(data):
    r = get_record(data, "D-3")
    subs = [
        sub("D-3-1", "구 D-3-1 자격 등록자 (해외투자/기술수출/산업설비, 레거시)",
            note="'06.12.31.까지 등록된 구 D-3-1 자격자에 대한 레거시 약호입니다. 현행 기술연수는 D-3-11·D-3-12·D-3-13으로 운영됩니다.",
            aliases=["D-3-1"], group="기타", status="legacy",
            statusNote="구 약호('06.12.31.까지 등록). 현행은 D-3-11/12/13(사증발급 안내매뉴얼).",
            manualRefs=[visa_ref("p. 352", needs_review=False,
                                 confidence="legacy_source_confirmed")],
            needsManualReview=False),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, ["D-3-1"])
    return len(subs)


# --------------------------------------------------------------------------- #
# A-3 — add A-3-99 (Fulbright 협정대상자, active)
# --------------------------------------------------------------------------- #
def patch_a3(data):
    r = get_record(data, "A-3")
    subs = [
        sub("A-3-99", "Fulbright 협정대상자",
            addReq="Fulbright 협정 대상자임을 입증하는 서류 등 (매뉴얼 확인).",
            addReqDocs=["doc_case_specific_evidence"],
            note="한·미 Fulbright 협정 대상자에 대한 협정(A-3) 체류자격. 세부 서류는 사증발급 안내매뉴얼 확인.",
            aliases=["Fulbright", "풀브라이트", "A-3-99", "협정대상자"], group="협정",
            manualRefs=[visa_ref("p. 13")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, ["A-3-99", "Fulbright", "풀브라이트"])
    return len(subs)


# --------------------------------------------------------------------------- #
# F-1 — add F-1-D (디지털노마드/워케이션, active)
# --------------------------------------------------------------------------- #
def patch_f1(data):
    r = get_record(data, "F-1")
    subs = [
        sub("F-1-D", "디지털노마드(워케이션) 비자",
            addReq="해외 소속 기업 재직·원격근무 입증서류, 소득요건 입증서류, 민간 의료보험 가입 입증서류 등.",
            addReqDocs=["doc_remote_work_employment_proof",
                        "doc_digital_nomad_income_proof",
                        "doc_private_medical_insurance"],
            note="해외 기업 소속으로 원격근무하며 국내 체류하는 디지털노마드. 세부 요건·소득 기준은 사증발급 안내매뉴얼 확인.",
            aliases=["디지털노마드", "디지털 노마드", "워케이션", "digital nomad",
                     "workation", "F-1-D"], group="기타",
            manualRefs=[visa_ref("p. 303")]),
    ]
    # Promote status-change-variant-only F-1 codes to first-class subcodes
    # (grounded by the existing procedure variants).
    subs += [
        sub("F-1-16", "난민인정자의 배우자 및 미성년 자녀 (방문동거)",
            addReq="난민인정자임을 입증하는 서류, 가족관계 입증서류.",
            addReqDocs=["doc_refugee", "doc_fam_rel"],
            note="난민인정자의 배우자 또는 미성년 자녀가 방문동거(F-1-16)로 변경하는 경우.",
            aliases=["F-1-16", "난민인정자 가족"], group="가족/동반",
            manualRefs=[stay_ref("p. 348")]),
        sub("F-1-52", "결혼이민자의 전혼관계 출생 미성년 자녀 (방문동거)",
            addReq="혼인관계 유지 입증서류, 전혼관계 친생자녀 가족관계 입증서류.",
            addReqDocs=["doc_fam_rel", "doc_basic"],
            note="혼인관계가 유지 중인 결혼이민자의 전혼관계 출생 친생 미성년 자녀가 F-1-52로 변경하는 경우.",
            aliases=["F-1-52", "전혼 자녀", "전혼관계 자녀"], group="가족/동반",
            manualRefs=[stay_ref("pp. 350, 230")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, ["F-1-D", "디지털노마드", "디지털 노마드", "워케이션",
                      "digital nomad", "workation", "F-1-16", "F-1-52"])
    return len(subs)


# --------------------------------------------------------------------------- #
# E-7 — split negative-method talent into E-7-S1 / E-7-S2; note E-7-H is an
#        internal 전산기호 (NOT a status code); add E-7-4R (regional skilled)
# --------------------------------------------------------------------------- #
def patch_e7(data):
    r = get_record(data, "E-7")
    subs = [
        sub("E-7-S1", "네거티브 방식 전문인력 — 고소득자",
            addReq="고소득 요건(소득) 입증서류 등 (매뉴얼 확인).",
            addReqDocs=["doc_inc_proof", "doc_specialty"],
            note="네거티브 방식 전문인력 중 고소득자. 학력·경력·분야와 무관하게 소득만 확인하여 E-7 발급.",
            aliases=["E-7-S1", "고소득자 전문인력", "네거티브 고소득"], group="특별요건",
            manualRefs=[visa_ref("pp. 169, 247")]),
        sub("E-7-S2", "네거티브 방식 전문인력 — 첨단산업분야 종사(예정)자",
            addReq="점수제 요건(60점 이상) 및 사회통합프로그램 이수 등 입증서류 (매뉴얼 확인).",
            addReqDocs=["doc_point_table", "doc_specialty", "doc_kiip"],
            note="네거티브 방식 전문인력 중 첨단산업분야 종사(예정)자. E-7 도입직종이 아니어도 점수제 요건 충족 시 발급.",
            aliases=["E-7-S2", "첨단산업 전문인력", "네거티브 첨단산업"], group="특별요건",
            manualRefs=[visa_ref("pp. 169, 247-248")]),
        sub("E-7-4R", "지역특화형 숙련기능인력 (지역숙련인력)",
            addReq="지역특화형 비자 대상 및 광역/기초 지자체 추천 입증서류 등 (매뉴얼 확인).",
            addReqDocs=["doc_local_recommendation", "doc_point_table"],
            note="지역특화형 비자 숙련기능인력. 지역특화형 우수인재(F-2-R) 자격변경과 연계.",
            aliases=["E-7-4R", "지역특화 숙련기능", "지역숙련인력", "지역특화형 숙련기능인력"],
            group="지역특화", manualRefs=[stay_ref("p. 67")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, ["E-7-S1", "E-7-S2", "E-7-4R", "지역특화 숙련기능"])
    # Record the E-7-H quarantine reason on the record (internal system marker).
    r.setdefault("_quarantineNotes", {})
    r["_quarantineNotes"]["E-7-H"] = (
        "내부 전산기호: 기타(G-1) 등에 대한 체류자격외활동 허가를 출입국관리시스템에 "
        "입력할 때 사용하는 전산기호이며(체류민원 p. 502), 사용자 안내용 체류자격 코드가 "
        "아니므로 검색/표시 대상에서 제외(internal_system_marker)."
    )
    return len(subs)


# --------------------------------------------------------------------------- #
# H-2 — add H-2-7 (만기출국 후 재입국한 사람, active)
# --------------------------------------------------------------------------- #
def patch_h2(data):
    r = get_record(data, "H-2")
    subs = [
        sub("H-2-7", "만기출국 후 재입국한 사람",
            addReq="만기출국 및 재입국 사실 입증서류 등 (매뉴얼 확인).",
            addReqDocs=["doc_case_specific_evidence"],
            note="방문취업(H-2) 만기출국 후 재입국한 사람. 세부 요건은 사증발급·체류 안내매뉴얼 확인.",
            aliases=["H-2-7", "만기출국 재입국", "재입국 방문취업"], group="기타",
            manualRefs=[stay_ref("p. 33"), visa_ref("p. 405")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, ["H-2-7", "만기출국 후 재입국"])
    return len(subs)


# --------------------------------------------------------------------------- #
# F-2 — K-STAR 거주(F-2-7S), K-STAR 동반가족(F-2-71), 지역특화 우수인재(F-2-R)
# --------------------------------------------------------------------------- #
def patch_f2(data):
    r = get_record(data, "F-2")
    subs = [
        sub("F-2-7S", "K-STAR 거주 (과학기술 우수인재)",
            addReq="K-STAR 비자트랙 참여대학 추천 등 입증서류 (매뉴얼 확인).",
            addReqDocs=["doc_kstar_university_recommendation", "doc_degree"],
            note="K-STAR 비자트랙 2단계 거주자격. 점수제 거주(F-2-7)와 동일시하지 말 것.",
            aliases=["F-2-7S", "K-STAR 거주", "케이스타 거주", "과학기술 우수인재 거주"],
            group="특별요건", manualRefs=[visa_ref("p. 473"), stay_ref("pp. 1, 3")]),
        sub("F-2-71", "K-STAR 거주자의 동반가족",
            addReq="가족관계 입증서류 등 (매뉴얼 확인).",
            addReqDocs=["doc_fam_rel"],
            note="K-STAR 거주(F-2-7S)의 동반가족. 점수제 거주(F-2-7)와 구분되는 별도 약호.",
            aliases=["F-2-71", "K-STAR 동반가족", "케이스타 가족"], group="가족/동반",
            manualRefs=[visa_ref("p. 480"), stay_ref("p. 5")]),
        sub("F-2-R", "지역특화형 우수인재 (지역우수인재)",
            addReq="지역특화형 비자 대상 및 지자체 추천 입증서류 등 (매뉴얼 확인).",
            addReqDocs=["doc_local_recommendation"],
            note="지역특화형 비자 우수인재. 자세한 사항은 지역특화·광역형 비자(REGION-S) 카드 참조.",
            aliases=["F-2-R", "지역특화 우수인재", "지역우수인재", "지역특화형 우수인재"],
            group="특별요건", manualRefs=[stay_ref("p. 67")]),
    ]
    # Promote status-change-variant-only F-2 codes to first-class subcodes.
    subs += [
        sub("F-2-8", "관광·휴양시설 투자 거주",
            addReq="지정된 관광·휴양시설 등 투자 입증서류, 재정능력 입증서류.",
            addReqDocs=["doc_invest", "doc_finance"],
            note="지정된 관광·휴양시설 등에 투자한 사람이 거주(F-2-8)로 변경하는 경우.",
            aliases=["F-2-8", "관광휴양시설 투자", "관광·휴양시설 투자"], group="투자",
            manualRefs=[stay_ref("pp. 375-378")]),
        sub("F-2-81", "관광·휴양시설 투자자의 배우자·자녀 거주",
            addReq="투자자와의 가족관계 입증서류.",
            addReqDocs=["doc_fam_rel"],
            note="관광·휴양시설 투자 거주(F-2-8) 자격자의 배우자 및 미혼자녀.",
            aliases=["F-2-81", "관광휴양시설 투자 가족"], group="투자",
            manualRefs=[stay_ref("p. 378")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, ["F-2-7S", "F-2-71", "F-2-R", "K-STAR 거주",
                      "지역특화 우수인재", "지역우수인재", "F-2-8", "F-2-81"])
    return len(subs)


# --------------------------------------------------------------------------- #
# F-5 — K-STAR 영주(F-5-S1), K-STAR 영주 동반가족(F-5-S2), 지역특화동포영주(F-5-6R)
# --------------------------------------------------------------------------- #
def patch_f5(data):
    r = get_record(data, "F-5")
    subs = [
        sub("F-5-S1", "K-STAR 영주 (과학기술 우수인재)",
            addReq="K-STAR 거주(F-2-7S) 3년 이상 계속 체류 등 요건 입증서류 (매뉴얼 확인).",
            addReqDocs=["doc_kstar_university_recommendation"],
            note="K-STAR 비자트랙 3단계 영주자격. 세부 영주 요건은 체류 안내매뉴얼 K-STAR 항목 확인 필요.",
            aliases=["F-5-S1", "K-STAR 영주", "케이스타 영주"], group="특별요건",
            manualRefs=[visa_ref("p. 479"), stay_ref("pp. 1, 5")]),
        sub("F-5-S2", "K-STAR 영주자의 동반가족",
            addReq="가족관계 입증서류 등 (매뉴얼 확인).",
            addReqDocs=["doc_fam_rel"],
            note="K-STAR 영주(F-5-S1)의 동반가족.",
            aliases=["F-5-S2", "K-STAR 영주 동반가족", "케이스타 영주 가족"],
            group="특별요건", manualRefs=[visa_ref("p. 480"), stay_ref("p. 5")]),
        sub("F-5-6R", "지역특화형 재외동포영주 (지역동포영주)",
            addReq="지역특화형 비자 재외동포영주 요건 입증서류 등 (매뉴얼 확인).",
            addReqDocs=["doc_local_recommendation", "doc_f4_proof"],
            note="지역특화형 비자 재외동포영주. 자세한 사항은 지역특화·광역형 비자(REGION-S) 카드 참조.",
            aliases=["F-5-6R", "지역특화 재외동포영주", "지역동포영주"], group="특별요건",
            manualRefs=[stay_ref("p. 67")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, ["F-5-S1", "F-5-S2", "F-5-6R", "K-STAR 영주", "지역동포영주"])
    return len(subs)


# --------------------------------------------------------------------------- #
# REGION-S — expose all official 지역특화형 family subcodes (stay manual p.67)
# --------------------------------------------------------------------------- #
def patch_region(data):
    r = get_record(data, "REGION-S")
    subs = [
        sub("F-2-R", "지역특화형 우수인재 (지역우수인재)",
            addReqDocs=["doc_local_recommendation"],
            note="지역특화형 비자 우수인재 主 체류자격.",
            aliases=["F-2-R", "지역우수인재", "지역특화 우수인재"], group="우수인재",
            manualRefs=[stay_ref("p. 67")]),
        sub("F-3-1R", "지역인재가족 (지역특화 우수인재 동반가족)",
            addReqDocs=["doc_fam_rel"],
            note="지역특화형 우수인재(F-2-R)의 동반가족(배우자·미성년자녀).",
            aliases=["F-3-1R", "지역인재가족"], group="우수인재",
            manualRefs=[stay_ref("p. 67")]),
        sub("E-7-4R", "지역특화형 숙련기능인력 (지역숙련인력)",
            addReqDocs=["doc_local_recommendation", "doc_point_table"],
            note="지역특화형 비자 숙련기능인력 主 체류자격.",
            aliases=["E-7-4R", "지역숙련인력", "지역특화 숙련기능"], group="숙련기능인력",
            manualRefs=[stay_ref("p. 67")]),
        sub("F-3-3R", "지역숙련인력가족 (지역특화 숙련기능인력 동반가족)",
            addReqDocs=["doc_fam_rel"],
            note="지역특화형 숙련기능인력(E-7-4R)의 동반가족.",
            aliases=["F-3-3R", "지역숙련인력가족"], group="숙련기능인력",
            manualRefs=[stay_ref("p. 67")]),
        sub("F-4-R", "지역특화형 재외동포 (지역재외동포)",
            addReqDocs=["doc_local_recommendation", "doc_f4_proof"],
            note="지역특화형 비자 재외동포 主 체류자격.",
            aliases=["F-4-R", "지역재외동포", "지역특화동포"], group="동포",
            manualRefs=[stay_ref("p. 67")]),
        sub("F-3-2R", "지역동포가족 (지역특화 재외동포 동반가족)",
            addReqDocs=["doc_fam_rel"],
            note="지역특화형 재외동포(F-4-R)의 동반가족.",
            aliases=["F-3-2R", "지역동포가족"], group="동포",
            manualRefs=[stay_ref("p. 67")]),
        sub("F-5-6R", "지역특화형 재외동포영주 (지역동포영주)",
            addReqDocs=["doc_local_recommendation", "doc_f4_proof"],
            note="지역특화형 비자 재외동포영주.",
            aliases=["F-5-6R", "지역동포영주"], group="동포",
            manualRefs=[stay_ref("p. 67")]),
        sub("REGIONAL-D-2", "광역형 비자 유학생 (시범사업)",
            addReqDocs=["doc_local_recommendation", "doc_enroll"],
            note="광역형 비자 시범사업 대상 유학(D-2). 광역 시·도지사 추천 필요.",
            aliases=["광역형 비자", "광역형 유학생", "광역형 D-2"], group="광역형",
            manualRefs=[stay_ref("p. 1", section="광역형 비자 시범사업")]),
        sub("REGIONAL-E-7", "광역형 비자 특정활동 (시범사업)",
            addReqDocs=["doc_local_recommendation", "doc_emp_contract"],
            note="광역형 비자 시범사업 대상 특정활동(E-7). 광역 시·도지사 추천 필요.",
            aliases=["광역형 비자", "광역형 특정활동", "광역형 E-7"], group="광역형",
            manualRefs=[stay_ref("p. 1", section="광역형 비자 시범사업")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, [s["code"] for s in subs]
                  + ["REGION-S", "지역특화형", "지역특화형비자", "지역특화 비자",
                     "광역형", "광역형 비자", "지역특화"])
    return len(subs)


# --------------------------------------------------------------------------- #
# K-STAR — expose official track subcodes + natural-language aliases
# --------------------------------------------------------------------------- #
def patch_kstar(data):
    r = get_record(data, "K-STAR")
    subs = [
        sub("F-2-7S", "K-STAR 거주 (2단계)",
            addReqDocs=["doc_kstar_university_recommendation", "doc_degree"],
            note="K-STAR 비자트랙 2단계: 석·박사 유학생(D-2 등) → K-STAR 거주(F-2-7S).",
            aliases=["F-2-7S", "K-STAR 거주", "케이스타 거주"], group="거주",
            manualRefs=[stay_ref("pp. 1, 3", section="K-STAR 비자트랙")]),
        sub("F-5-S1", "K-STAR 영주 (3단계)",
            addReqDocs=["doc_kstar_university_recommendation"],
            note="K-STAR 비자트랙 3단계: K-STAR 거주(F-2-7S) 3년 이상 → K-STAR 영주(F-5-S1).",
            aliases=["F-5-S1", "K-STAR 영주", "케이스타 영주"], group="영주",
            manualRefs=[stay_ref("pp. 1, 5", section="K-STAR 비자트랙")]),
        sub("F-2-71", "K-STAR 거주자의 동반가족",
            addReqDocs=["doc_fam_rel"],
            note="K-STAR 거주(F-2-7S)의 동반가족.",
            aliases=["F-2-71", "K-STAR 동반가족"], group="동반가족",
            manualRefs=[stay_ref("p. 5", section="K-STAR 비자트랙")]),
        sub("F-5-S2", "K-STAR 영주자의 동반가족",
            addReqDocs=["doc_fam_rel"],
            note="K-STAR 영주(F-5-S1)의 동반가족.",
            aliases=["F-5-S2", "K-STAR 영주 동반가족"], group="동반가족",
            manualRefs=[stay_ref("p. 5", section="K-STAR 비자트랙")]),
    ]
    merge_subcodes(r, subs)
    merge_aliases(r, [s["code"] for s in subs]
                  + ["K-STAR", "KSTAR", "K STAR", "케이스타", "K스타",
                     "과학기술 우수인재", "K-STAR 비자트랙"])
    return len(subs)


# --------------------------------------------------------------------------- #
# YOUTH-STAY — 국내 성장 기반 외국인 청소년 취업·정주 체류제도 (program, not a
#              formal 체류자격 code). Conservative helper record.
# --------------------------------------------------------------------------- #
def patch_youth(data):
    if get_record(data, "YOUTH-STAY"):
        return 0
    record = {
        "code": "YOUTH-STAY",
        "name": "국내 성장 기반 외국인 청소년 취업·정주 체류제도",
        "name_en": "Domestic-growth foreign youth employment & settlement program",
        "cat": "etc",
        "isProgram": True,
        "period": "프로그램(체류자격 변경·특례 연계)",
        "dataBadge": "매뉴얼 프로그램",
        "newReq": ("성장기반이 국내에 형성된 외국인 청소년(신청일 기준 18~24세)이 고교 졸업 후 "
                   "대학에 진학하지 않더라도 국내 취업·정주하며 자립할 수 있도록 지원하는 "
                   "체류제도입니다. 별도의 독립 체류자격 코드가 아니라 구직(D-10) 등 기존 "
                   "체류자격의 자격변경·특례와 연계되는 매뉴얼 프로그램입니다."),
        "subCodes": [],
        "searchAliases": [
            "YOUTH-STAY", "국내 성장 기반 외국인 청소년", "국내 성장 기반 외국인 청소년 취업·정주",
            "외국인 청소년 취업 정주", "외국인 청소년 정주", "청소년 정주", "청소년 취업 정주",
            "D-10 청소년 특례", "외국인 청소년", "성장기반 청소년",
        ],
        "procedures": {
            "statusChange": {
                "available": True,
                "summary": ("국내 성장 기반 외국인 청소년(18~24세)에 대한 취업·정주 지원 "
                            "체류제도. 구직(D-10) 등 기존 체류자격의 자격변경 체크리스트와 "
                            "연계됩니다. 정확한 대상·요건·제출서류는 체류 안내매뉴얼 해당 "
                            "항목과 관할기관 안내를 확인하세요."),
                "requiredDocs": {
                    "commonDocs": [], "requiredDocs": [], "additionalDocs": [],
                    "conditionalDocs": [],
                },
                "notes": ["이 항목은 독립적인 체류자격 코드가 아니라 특정 체류자격 절차와 "
                          "연계되는 매뉴얼 프로그램입니다."],
                "manualRefs": [stay_ref("pp. 134-135",
                                        section="국내 성장 기반 외국인 청소년 취업·정주 체류제도")],
            }
        },
        "sourceManualStatus": {
            "needsManualReview": True,
            "stayManualVersion": "2026.5",
        },
        "manualRefs": [stay_ref("pp. 134-135",
                                section="국내 성장 기반 외국인 청소년 취업·정주 체류제도")],
        "_source_notes": ("매뉴얼 프로그램 헬퍼 레코드. 공식 매뉴얼이 독립 체류자격 코드를 "
                          "부여하지 않으므로 비자 코드로 표기하지 않습니다."),
    }
    data.append(record)
    return 1


PATCHERS = [
    ("G-1", patch_g1), ("C-3", patch_c3), ("C-4", patch_c4), ("E-8", patch_e8),
    ("D-8", patch_d8), ("D-9", patch_d9), ("D-3", patch_d3), ("A-3", patch_a3),
    ("F-1", patch_f1), ("E-7", patch_e7), ("H-2", patch_h2), ("F-2", patch_f2),
    ("F-5", patch_f5), ("REGION-S", patch_region), ("K-STAR", patch_kstar),
    ("YOUTH-STAY", patch_youth),
]


def main():
    data = json.loads(VISA_DATA.read_text(encoding="utf-8"))
    stale = count_stale_paths(data)
    print(f"pre-existing May stay-manual refs (left intact, see note): {stale}")
    for label, fn in PATCHERS:
        n = fn(data)
        print(f"  patched {label}: {n} subcode(s)/record(s)")
    VISA_DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    print(f"wrote {VISA_DATA.relative_to(REPO)}")


if __name__ == "__main__":
    main()
