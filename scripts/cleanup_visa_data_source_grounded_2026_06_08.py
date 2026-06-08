#!/usr/bin/env python3
"""Source-grounded cleanup of visa_data.json (2026-06-08).

This is a deterministic, idempotent data-cleanup pass. It edits ONLY
visa_data.json (the repo-root canonical file). It never touches the runtime
HTML/backend, and it never edits data/scenario_help_records.json.

What it does (and why each change is runtime/validation safe):

  CANONICAL records (code matches a real status; cat not in scn/faq/nhis):
    1. OCR de-glue: fix the specific merged-token artifacts called out for
       cleanup ("및체류기간", "연장허가1.", "연장허가필수서류", "서류필수서류",
       "필수서류①"). Pure whitespace insertion — no semantic change.
    2. doc-ID reference repair: inside ID-reference arrays only (the same
       field set the migration validator uses), replace the two residual
       migrated Korean-string doc refs with their stable machine IDs
       ("수수료" -> doc_fee_generic, "체류지 입증서류" -> doc_residence_proof_generic).
       Both IDs already exist in doc_master.json and have DOC_DICT labels, so
       the frontend renders a richer label, not a degraded fallback. This also
       clears the pre-existing check_doc_master_id_migration.py failure.
    3. DATA_MISSING hygiene: drop document-object notes/names equal to
       "DATA_MISSING" and remove whole-field "DATA_MISSING" sentinels in the
       legacy documents_* / hikorea_task_type fields. The runtime already
       suppresses these (isDocPlaceholder / isDocFieldMissing / the task-type
       picker), so removal is behavior-identical and removes the user-facing
       placeholder candidates from committed data.
    4. F-5 reframe: permanent residence is not ordinary stay-extension; the
       permanent-resident card (영주증) is what is time-limited (10y reissue).
       Grounded in stay manual pp. 453, 518 (repo crosswalk: "F-5 is not a
       simple stay-extension checklist"). Keeps procedures.extension structure
       required by the schema check; only corrects framing + de-corrupts text.
    5. G-1 de-merge: the parent G-1 extension list had multiple sub-case
       requirements (산업재해 / 질병치료 / 소송 / 임금체불) merged into one
       parent-level rule, plus wrong-code fragments (G 3, G 4). Replaced with
       an honest parent-level statement that defers to sub-code specifics.
       Grounded in stay manual p. 498, pp. 499-503 (repo crosswalk: "Do not
       treat G-1 as a single uniform checklist; G-1-5/6/12/99 need separate
       source support"). G-1-5 stays searchable via subCodes + searchAliases.

  SCENARIO/HELP/FAQ records (the 17 cat scn/faq/nhis codes):
    These are already shadow-migrated to data/scenario_help_records.json and
    gated against removal until the E-4 runtime cutover. The parity validator
    (check_scenario_help_records.py) requires each live record to deep-equal
    its shadow copy *byte-for-byte except migrationMeta*. Because this pass may
    only edit visa_data.json (not the shadow store, not the runtime), the ONLY
    safe edit is to enrich the parity-exempt migrationMeta with a 2026-06-08
    cleanup/classification stamp. Content is intentionally left untouched so
    parity + runtime lookups (ALIAS_MAP -> K-ETA/OVS-1/RF-1 etc.) keep working.
    A quarantine snapshot is written separately to
    data/removed_from_visa_data_scenario_records_20260608.json.

Run:  python3 scripts/cleanup_visa_data_source_grounded_2026_06_08.py
      python3 scripts/cleanup_visa_data_source_grounded_2026_06_08.py --check
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VISA = ROOT / "visa_data.json"

SCENARIO_CATS = {"scn", "faq", "nhis"}

# Whitespace-glue OCR artifacts -> de-glued form. Pure spacing fixes.
GLUE_FIXES = [
    ("연장허가필수서류", "연장허가 필수서류"),
    ("서류필수서류", "서류 필수서류"),
    ("필수서류①", "필수서류 ①"),
    ("연장허가1.", "연장허가 1."),
    ("및체류기간", "및 체류기간"),
]

# Residual migrated Korean-string doc refs -> stable machine IDs (must already
# exist in doc_master.json). Only applied to exact items inside ID arrays.
# This is the established PR-D-batch-2 migration mapping (the OLD->NEW pairing
# enforced by check_doc_master_id_migration.py); every NEW id already has a
# DOC_DICT label in index.html, so the rendered Korean label is unchanged.
KO_DOC_REF_TO_ID = {
    "개별 사안별 증빙서류(매뉴얼 해당 항목 및 관할기관 안내 기준)": "doc_case_specific_evidence",
    "변경 사유 입증서류(활동계획서·초청서·고용계약서 등 해당 자격별)": "doc_change_reason_evidence",
    "사증발급신청서(별지 제17호 서식)": "doc_visa_application_form",
    "사진 1매(해당 시)": "doc_photo_one_optional",
    "수수료": "doc_fee_generic",
    "여권": "doc_passport_generic",
    "여권 및 외국인등록증": "doc_passport_and_arc",
    "체류자격별 개별 첨부서류(매뉴얼 해당 자격 항목 참조)": "doc_status_specific_attachments",
    "체류지 입증서류": "doc_residence_proof_generic",
    "통합신청서": "doc_unified_application_form",
    "통합신청서(체류자격변경허가 신청 포함)": "doc_unified_application_form_change",
    "표준규격사진 1매": "doc_standard_photo_one",
}

# Mirrors check_doc_master_id_migration.py / check_scenario_help_records.py.
ID_ARRAY_FIELDS = {
    "initialReqDocs", "newReqDocs", "extReqDocs", "extensionReqDocs",
    "changeReqDocs", "requiredDocs", "reqDocs", "documents", "cviReqDocs",
    "statusGrantReqDocs", "registrationReqDocs", "activitiesOutsideStatusReqDocs",
    "workplaceChangeReqDocs", "reentryReqDocs", "addReqDocs",
}

LEGACY_DOC_TAB_FIELDS = ("documents_initial", "documents_registration", "documents_extension")


def deglue(obj):
    if isinstance(obj, dict):
        return {k: deglue(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deglue(v) for v in obj]
    if isinstance(obj, str):
        s = obj
        for a, b in GLUE_FIXES:
            if a in s:
                s = s.replace(a, b)
        return s
    return obj


def fix_doc_refs(obj, parent=None):
    if isinstance(obj, dict):
        return {k: fix_doc_refs(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        out = []
        for v in obj:
            if isinstance(v, str) and parent in ID_ARRAY_FIELDS and v in KO_DOC_REF_TO_ID:
                out.append(KO_DOC_REF_TO_ID[v])
            else:
                out.append(fix_doc_refs(v, parent))
        return out
    return obj


def clean_data_missing(rec: dict) -> None:
    for f in LEGACY_DOC_TAB_FIELDS:
        if f not in rec:
            continue
        v = rec[f]
        if v == "DATA_MISSING":
            rec.pop(f, None)
            continue
        if isinstance(v, list):
            cleaned = []
            for it in v:
                if isinstance(it, dict):
                    if it.get("name") == "DATA_MISSING":
                        continue  # no real document name -> drop row
                    if it.get("note") == "DATA_MISSING":
                        it = {k: val for k, val in it.items() if k != "note"}
                    cleaned.append(it)
                else:
                    cleaned.append(it)
            if cleaned:
                rec[f] = cleaned
            else:
                rec.pop(f, None)
    if rec.get("hikorea_task_type") == "DATA_MISSING":
        rec.pop("hikorea_task_type", None)


def _prepend_note(proc: dict, note: str) -> None:
    """Add a source-cross-check note as the first entry, idempotently."""
    notes = proc.get("notes")
    if not isinstance(notes, list):
        notes = [] if notes is None else [notes]
    notes = [n for n in notes if n != note]
    proc["notes"] = [note] + notes


def reframe_f5(rec: dict) -> None:
    ext = (rec.get("procedures") or {}).get("extension")
    if not isinstance(ext, dict):
        return
    ext["summary"] = (
        "[입국 후 · 국내 체류절차] 영주(F-5)는 체류기간 상한이 없는 영주자격으로, "
        "일반적인 '체류기간 연장' 대상이 아닙니다. 다만 영주증(영주카드)의 유효기간은 10년이며 "
        "만료 전 재발급이 필요합니다(영주자격 자체의 연장이 아니라 영주증 재발급 절차). "
        "세부약호·국적·체류 이력에 따라 제출서류가 달라질 수 있어 관할 출입국·외국인관서 및 "
        "체류민원 매뉴얼 확인이 필요합니다."
    )
    rd = ext.get("requiredDocs")
    if isinstance(rd, dict):
        rd["requiredDocs"] = [
            "통합신청서(별지 제34호 서식), 여권 및 외국인등록증, 수수료",
            "체류지 입증서류(임대차계약서, 부동산 등기부등본, 전세계약서, 매매계약서 등 및 숙소제공 확인서)",
            "추가서류: 배우자 또는 부모의 외국인등록증 등(사안별 해당 시)",
            "위 항목은 영주증 재발급 등 절차 기준으로 자동 추출되었으며, 세부 사안은 공식 확인이 필요합니다.",
        ]
    rec["extReq"] = (
        "영주(F-5)는 체류기간 상한이 없는 영주자격으로 일반적인 체류기간 연장 대상이 아니며, "
        "영주증(영주카드)은 유효기간 10년으로 만료 전 재발급이 필요합니다. 제출서류는 세부약호·사안에 "
        "따라 다르므로 관할 출입국·외국인관서 및 체류민원 매뉴얼에서 확인하세요."
    )
    _prepend_note(
        ext,
        "[2026-06-08 출처 대조] 2026-06-01 체류민원 매뉴얼 영주(F-5) 절 '영주증 발급 및 재발급 특례'"
        " 기준: 영주증 유효기간은 발급일로부터 10년이며 만료일 전 재발급이 필요(기간 도과 시 과태료)."
        " 영주(F-5)는 체류기간 상한이 없어 일반적인 '체류기간 연장' 절차와 구분되며, 여기 표시된 항목은"
        " 영주증 재발급 등 절차 기준입니다. 세부약호·사안별 서류는 수동 확인이 필요합니다.",
    )


def reframe_g1(rec: dict) -> None:
    ext = (rec.get("procedures") or {}).get("extension")
    if not isinstance(ext, dict):
        return
    ext["summary"] = (
        "[입국 후 · 국내 체류절차] 기타(G-1) 자격의 체류기간 연장 요건과 제출서류는 "
        "세부약호(예: 산업재해 치료, 질병·사고 치료, 소송 진행, 임금체불 구제, 난민신청 관련 등)에 따라 "
        "크게 다릅니다. 공통적으로 통합신청서(별지 제34호 서식)·여권·외국인등록증·수수료가 필요하며, "
        "세부약호별 추가서류와 허가기간은 관할 출입국·외국인관서 또는 체류민원 매뉴얼에서 확인해야 합니다."
    )
    rd = ext.get("requiredDocs")
    if isinstance(rd, dict):
        rd["requiredDocs"] = [
            "통합신청서(별지 제34호 서식), 여권, 외국인등록증, 수수료 (공통 신청서류)",
            "세부약호별(산업재해·질병치료·소송·임금체불·난민신청 관련 등) 추가 제출서류 및 허가기간은 "
            "사안마다 달라 관할 출입국·외국인관서 또는 체류민원 매뉴얼에서 확인 (G-1은 세부약호별로 요건이 상이)",
        ]
    rec["extReq"] = (
        "기타(G-1)는 세부약호별로 연장 요건·허가기간·제출서류가 크게 다릅니다"
        "(예: 산업재해·질병치료·소송·임금체불·난민신청 관련 등). 공통 신청서류 외 세부약호별 서류는 "
        "관할 출입국·외국인관서 또는 체류민원 매뉴얼에서 확인하세요."
    )
    _prepend_note(
        ext,
        "[2026-06-08 출처 대조] 2026-06-01 체류민원 매뉴얼 기타(G-1) p.498 '해당자(법무부장관이 인정하는"
        " 사람)' 목록 기준: 산업재해 청구·치료, 질병/사고 치료, 소송 진행, 임금체불 중재, 난민신청 등"
        " 세부 사례별로 요건이 상이합니다. 특정 세부 사례(예: 산업재해)의 서류를 G-1 일반 연장요건으로"
        " 일반화하지 않습니다(상위코드 승격 금지). 세부약호별 서류는 수동 확인이 필요합니다.",
    )
    for ref in ext.get("manualRefs", []):
        if isinstance(ref, dict):
            ref["pageRange"] = "pp. 498-513"


def enrich_scenario_migration_meta(rec: dict) -> None:
    """Only touch the parity-exempt migrationMeta of a scenario/help record."""
    meta = rec.get("migrationMeta")
    if not isinstance(meta, dict):
        # Should not happen (all 17 carry it), but never fabricate gating state.
        return
    meta["sourceGroundedCleanup20260608"] = {
        "reviewedAt": "2026-06-08",
        "classification": "non_canonical_scenario_help_faq",
        "notOfficialVisaStatusGuidance": True,
        "verified": False,
        "needsManualReview": True,
        "action": (
            "Retained byte-for-byte in visa_data.json for runtime lookups and "
            "shadow-store parity. Legal-prose stripping / physical removal is "
            "deferred to the E-4 runtime cutover (consume data/scenario_help_records.json "
            "and drop visa_data scenario lookups) and is out of scope for a "
            "visa_data.json-only edit."
        ),
        "quarantineSnapshot": "data/removed_from_visa_data_scenario_records_20260608.json",
        "canonicalStore": "data/scenario_help_records.json",
    }


def transform(data: list) -> list:
    for rec in data:
        if not isinstance(rec, dict):
            continue
        cat = rec.get("cat")
        code = rec.get("code")
        if cat in SCENARIO_CATS:
            enrich_scenario_migration_meta(rec)
            continue
        # canonical record
        if code == "F-5":
            reframe_f5(rec)
        elif code == "G-1":
            reframe_g1(rec)
        clean_data_missing(rec)
    # generic, recursive passes over the whole file. fix_doc_refs and deglue
    # are no-ops on already-clean text and on scenario records (whose ID arrays
    # carry no residual Korean refs / glue artifacts in practice), but we keep
    # them scoped to canonical records to guarantee shadow-store parity.
    canonical_idx = [i for i, r in enumerate(data)
                     if isinstance(r, dict) and r.get("cat") not in SCENARIO_CATS]
    for i in canonical_idx:
        data[i] = deglue(fix_doc_refs(data[i]))
    return data


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="Exit 1 if running the cleanup would still change the file.")
    args = ap.parse_args(argv)

    original = VISA.read_text(encoding="utf-8")
    data = json.loads(original)
    data = transform(data)
    out = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        if out != original:
            print("CHECK FAIL: visa_data.json is not in the cleaned state.", file=sys.stderr)
            return 1
        print("CHECK OK: visa_data.json already matches the cleaned state.")
        return 0

    if out == original:
        print("No changes (already clean).")
        return 0
    VISA.write_text(out, encoding="utf-8")
    print("Updated visa_data.json (source-grounded cleanup 2026-06-08).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
