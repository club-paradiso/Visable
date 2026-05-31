#!/usr/bin/env python3
"""Promote PDF-verified parent-level procedure document lists into the
2026-05 structured requirements layer.

This is the deterministic, idempotent generator behind the
"data: expand source-confirmed procedure coverage" change. Each record below
was located in the committed official stay manual
(``docs/source-manuals/2026-05/stay_manual_2026_05.pdf``) at the cited printed
page, hand-verified to be a *single-procedure, parent-code-level* required-
documents list (no sub-code/scenario split inside the list), and structured so
that every applicant-type / substitute-document / sub-code condition is
preserved as a document-level ``conditionKo`` (never flattened into a separate
universal requirement). The page footer ("- N -") is re-verified at run time to
match the cited page.

Each promoted entry is HIGH / STRUCTURED_EVIDENCE_READY, so the existing runtime
accessor (`backend/structured_requirements.py`) exposes it automatically through
``/api/visas``, ``/api/visas/{code}/structured-requirements`` and the AI
source-confirmed grounding block — the same path PR #229/#230 established.

The script appends to BOTH the backend file and its docs mirror, keeps them
byte-identical, and regenerates the per-status index aggregates. Running it
twice is a no-op (records are keyed by statusCode+procedureType+page+boundary).

Usage:
    pip install pymupdf
    python3 scripts/promote_source_confirmed_procedures_2026_05.py
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_BACKEND = os.path.join(
    _REPO, "backend", "data", "manual_grounding", "structured_requirements_2026_05.json"
)
_MIRROR = os.path.join(_REPO, "docs", "data", "structured_requirements_2026_05.json")
_INDEX = os.path.join(
    _REPO,
    "backend",
    "data",
    "manual_grounding",
    "structured_requirements_index_2026_05.json",
)
_STAY_PDF = os.path.join(
    _REPO, "docs", "source-manuals", "2026-05", "stay_manual_2026_05.pdf"
)
_STAY_FILE = "docs/source-manuals/2026-05/stay_manual_2026_05.pdf"
_MANUAL_NAME = "외국인체류 안내매뉴얼"
_MANUAL_VERSION = "2026.5"

_FOOTER_RE = re.compile(r"-\s*(\d+)\s*-")


def _doc(text, *, requiredness="required", condition=None):
    return {
        "textKo": text,
        "docMasterId": None,
        "boundary": "parent_code_level",
        "conditionKo": condition,
        "requiredness": requiredness,
        "notesKo": None,
    }


# Each record: an independently PDF-verified parent-level single-procedure list.
# ``excerptAnchor`` is the literal substring at which the cited block begins; the
# script slices from there so the stored sourceExcerpt is taken verbatim from the
# PDF text at run time (no hand-typed excerpts).
RECORDS = [
    {
        "statusCode": "D-1", "statusNameKo": "문화예술",
        "procedureType": "registration", "page": 34,
        "sectionTitle": "문화예술(D-1) — 외국인등록 / 1. 외국인등록 신청서류",
        "excerptAnchor": "외국인등록\n\U000f007e 목차\n1. 외국인등록 신청서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc("사업자등록증 등 문화예술 단체입증 서류"),
            _doc("체류지 입증서류"),
        ],
        "note": "유학(D-2) 외국인등록(p.44)과 동일한 매뉴얼 템플릿. 단일 절차(외국인등록), 상위코드 수준 목록.",
    },
    {
        "statusCode": "D-5", "statusNameKo": "취재",
        "procedureType": "registration", "page": 104,
        "sectionTitle": "취재(D-5) — 외국인등록 / 1. 외국인등록 신청서류",
        "excerptAnchor": "외국인등록\n\U000f007e 목차\n1. 외국인등록 신청서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc(
                "지국·지사의 설치허가증 또는 「부가가치세법」에 따른 사업자등록증",
                condition="국내에 지국·지사가 없거나 증명을 발급받을 수 없는 외신은 주무부처(문화체육관광부 해외문화홍보원)의 협조공문으로 갈음 가능",
            ),
            _doc("체류지 입증서류"),
        ],
        "note": "대체서류(협조공문 갈음)는 document-level conditionKo로 보존.",
    },
    {
        "statusCode": "D-5", "statusNameKo": "취재",
        "procedureType": "extension", "page": 103,
        "sectionTitle": "취재(D-5) — 체류기간 연장허가 / 1. 제출서류",
        "excerptAnchor": "연장허가\n1. 제출서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권 및 외국인등록증, 수수료"),
            _doc("재직증명서 또는 파견명령서(본사발행)"),
            _doc("체류지 입증서류(임대차계약서, 숙소제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 등)"),
        ],
        "note": "단일 절차(체류기간 연장허가), 상위코드 수준 목록.",
    },
    {
        "statusCode": "D-6", "statusNameKo": "종교",
        "procedureType": "registration", "page": 107,
        "sectionTitle": "종교(D-6) — 외국인등록 / 1. 외국인등록 신청서류",
        "excerptAnchor": "외국인등록\n\U000f007e 목차\n1. 외국인등록 신청서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc("‘종교단체 또는 사회복지단체 설립’ 관련 서류"),
            _doc("체류지 입증서류"),
        ],
        "note": "단일 절차(외국인등록), 상위코드 수준 목록.",
    },
    {
        "statusCode": "D-6", "statusNameKo": "종교",
        "procedureType": "extension", "page": 107,
        "sectionTitle": "종교(D-6) — 체류기간 연장허가 / 1. 제출서류",
        "excerptAnchor": "연장허가\n1. 제출서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권 및 외국인등록증, 수수료"),
            _doc("재직증명서 또는 파송명령서(파송단체 발행)"),
            _doc("체류지 입증서류(임대차계약서, 숙소제공 확인서, 체류기간 만료예고 통지우편물, 공공요금 납부영수증, 기숙사비 영수증 등)"),
        ],
        "note": "단일 절차(체류기간 연장허가), 상위코드 수준 목록.",
    },
    {
        "statusCode": "D-7", "statusNameKo": "주재",
        "procedureType": "registration", "page": 113,
        "sectionTitle": "주재(D-7) — 외국인등록 / 1. 외국인등록 신청서류",
        "excerptAnchor": "1. 외국인등록 신청서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc(
                "사업자등록증",
                condition="외국법자문법률사무소 등록증은 해당자에 한함",
            ),
            _doc("체류지 입증서류"),
        ],
        "note": "신청자 유형 조건(외국법자문법률사무소 등록증 해당자)을 document-level conditionKo로 보존.",
    },
    {
        "statusCode": "D-8", "statusNameKo": "기업투자",
        "procedureType": "registration", "page": 126,
        "sectionTitle": "기업투자(D-8) — 외국인등록 / 1. 외국인등록 신청서류",
        "excerptAnchor": "1. 외국인등록 신청서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc(
                "사업자등록증, 법인등기사항전부증명서",
                condition="법인등기사항전부증명서는 법인기업인 경우에 한함",
            ),
            _doc("체류지입증서류(부동산 임대차계약서 등)"),
        ],
        "note": "법인 여부 조건을 document-level conditionKo로 보존. (재외공관에서 D-8을 직접 받아 입국한 외국인의 변경신청 준용 안내는 sourceExcerpt에 보존.)",
    },
    {
        "statusCode": "E-2", "statusNameKo": "회화지도",
        "procedureType": "registration", "page": 173,
        "sectionTitle": "회화지도(E-2) — 외국인등록 / 1. 외국인등록 신청서류",
        "excerptAnchor": "1. 외국인등록 신청서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc("「부가가치세법」에 따른 사업자등록증"),
            _doc("체류지 입증서류"),
        ],
        "note": "단일 절차(외국인등록), 상위코드 수준 목록.",
    },
    {
        "statusCode": "E-3", "statusNameKo": "연구",
        "procedureType": "registration", "page": 194,
        "sectionTitle": "연구(E-3) — 외국인등록 / 1. 외국인등록 신청서류",
        "excerptAnchor": "1. 외국인등록 신청서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc("「부가가치세법」에 따른 사업자등록증"),
            _doc("체류지 입증서류"),
        ],
        "note": "단일 절차(외국인등록), 상위코드 수준 목록.",
    },
    {
        "statusCode": "E-4", "statusNameKo": "기술지도",
        "procedureType": "registration", "page": 199,
        "sectionTitle": "기술지도(E-4) — 외국인등록 / 1. 외국인등록 신청서류",
        "excerptAnchor": "1. 외국인등록 신청서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc("「부가가치세법」에 따른 사업자등록증"),
            _doc("체류지 입증서류"),
        ],
        "note": "단일 절차(외국인등록), 상위코드 수준 목록.",
    },
    {
        "statusCode": "E-5", "statusNameKo": "전문직업",
        "procedureType": "registration", "page": 204,
        "sectionTitle": "전문직업(E-5) — 외국인등록 / 1. 외국인등록 신청서류",
        "excerptAnchor": "1. 외국인등록 신청서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc("「부가가치세법」에 따른 사업자등록증"),
            _doc("체류지 입증서류"),
        ],
        "note": "단일 절차(외국인등록), 상위코드 수준 목록.",
    },
    {
        "statusCode": "E-6", "statusNameKo": "예술흥행",
        "procedureType": "registration", "page": 211,
        "sectionTitle": "예술흥행(E-6) — 외국인등록 / 1. 외국인등록 신청서류 및 확인사항 / 가. 신청서류",
        "excerptAnchor": "1. 외국인등록 신청서류 및 확인사항",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc(
                "「부가가치세법」에 따른 사업자등록증 사본",
                condition="해당 외국인을 고용한 단체·기업 등의 사업자등록증 또는 고유번호증 등(직접 고용관계가 없는 경우 초청단체 또는 소속 단체 등의 사업자등록증 등)",
            ),
            _doc(
                "채용신체검사서 1부",
                requiredness="conditional",
                condition="E-6-2만 제출. 공무원채용신체검사서 발급 절차에 따르며, HIV반응 및 마약검사 항목은 필수 검사항목이 아님(회화지도(E-2) 강사 등 지정병원제 규정 비적용)",
            ),
            _doc("체류지 입증서류"),
        ],
        "note": "채용신체검사서의 E-6-2 한정 조건은 document-level conditionKo(requiredness=conditional)로 보존 — 별도 보편 요건으로 flatten하지 않음.",
    },
    {
        "statusCode": "E-7", "statusNameKo": "특정활동",
        "procedureType": "registration", "page": 228,
        "sectionTitle": "특정활동(E-7) — 외국인등록 / 1. 외국인등록 신청서류",
        "excerptAnchor": "외국인등록\n1. 외국인등록 신청서류",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc("「부가가치세법」에 따른 사업자등록증"),
            _doc(
                "채용신체검사서",
                requiredness="conditional",
                condition="외국인학교 등의 교사만 해당",
            ),
            _doc("체류지 입증서류"),
        ],
        "note": "이미 promote된 E-7 연장(p.226)과 동일하게 상위코드 수준. 채용신체검사서의 교사 한정 조건은 document-level conditionKo로 보존.",
    },
    {
        "statusCode": "E-10", "statusNameKo": "선원취업",
        "procedureType": "registration", "page": 339,
        "sectionTitle": "선원취업(E-10) — 외국인등록 / 1. 외국인등록 신청서류",
        "excerptAnchor": "① 신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료",
        "documents": [
            _doc("신청서(별지34호 서식), 여권원본, 표준규격사진1장, 수수료"),
            _doc("내항여객운송사업면허증 또는 내항화물운송등록증"),
            _doc("건강검진서", condition="반드시 봉투에 밀봉된 상태로 제출, 개봉 불가"),
            _doc("마약검사 확인서", condition="반드시 봉투에 밀봉된 상태로 제출, 개봉 불가"),
            _doc("산업재해보상보험 또는 상해보험 가입증명원"),
            _doc("체류지 입증서류"),
        ],
        "note": "‘1. 외국인등록 신청서류’ 헤딩은 p.338 하단에 있고 ①~⑥ 목록은 p.339에 이어짐 — 목록 전체가 위치한 p.339를 인용.",
    },
]


def _slice_excerpt(text: str, anchor: str, length: int = 600) -> str:
    i = text.find(anchor)
    if i < 0:
        # fall back to a looser anchor (first line of the anchor)
        first = anchor.split("\n")[-1]
        i = text.find(first)
    if i < 0:
        raise RuntimeError(f"anchor not found: {anchor!r}")
    return text[i : i + length].strip()


def build_entry(rec: dict, excerpt: str) -> dict:
    return {
        "statusCode": rec["statusCode"],
        "statusNameKo": rec["statusNameKo"],
        "subCode": None,
        "subCodeNameKo": None,
        "scenarioId": None,
        "scenarioNameKo": None,
        "procedureType": rec["procedureType"],
        "procedureTypesDetected": [rec["procedureType"]],
        "evidenceType": "required_documents",
        "manualSource": {
            "file": _STAY_FILE,
            "manualName": _MANUAL_NAME,
            "manualVersion": _MANUAL_VERSION,
            "pageStart": rec["page"],
            "pageEnd": rec["page"],
            "sectionTitle": rec["sectionTitle"],
            "sourceExcerpt": excerpt,
        },
        "documents": rec["documents"],
        "boundaryType": "parent_code_level",
        "confidence": "HIGH",
        "reviewStatus": "source_confirmed",
        "readinessLabel": "STRUCTURED_EVIDENCE_READY",
        "doNotFlatten": True,
        "subCodesCovered": None,
        "evidenceSource": "pdf_verified",
        "verificationNote": (
            "Verified via PyMuPDF text extraction of "
            f"{_STAY_FILE}. The list appears on the PDF page bearing the printed "
            f"footer '- {rec['page']} -' (absolute PDF page {rec['page']}, 1:1). "
            "Parent-code-level single-procedure list; applicant-type / substitute / "
            "sub-code conditions captured as document-level conditionKo, not "
            "flattened into universal requirements. " + rec.get("note", "")
        ).strip(),
    }


def _entry_key(e: dict) -> tuple:
    ms = e.get("manualSource") or {}
    return (
        e.get("statusCode"),
        e.get("procedureType"),
        ms.get("pageStart"),
        e.get("boundaryType"),
    )


def regenerate_index(index: dict, entries: list) -> None:
    src = "backend/data/manual_grounding/structured_requirements_2026_05.json"
    by_status = collections.defaultdict(list)
    for e in entries:
        by_status[e.get("statusCode")].append(e)
    idx = index.setdefault("index", {})
    for code, ents in by_status.items():
        node = idx.setdefault(code, {"mappedProductionCodes": [code]})
        node["source"] = src
        node["entryCount"] = len(ents)
        node["documentItemCount"] = sum(len(e.get("documents") or []) for e in ents)
        ready = [
            e
            for e in ents
            if e.get("confidence") == "HIGH"
            and e.get("readinessLabel") == "STRUCTURED_EVIDENCE_READY"
        ]
        node["readyCount"] = len(ready)
        node["hasSubCodeEvidence"] = any(
            e.get("boundaryType") == "sub_code_specific" for e in ents
        )
        node["hasScenarioEvidence"] = any(
            e.get("boundaryType") == "scenario_specific" for e in ents
        )
        node["requiresHumanReview"] = any(
            e.get("readinessLabel")
            in {"NEEDS_PAGE_CITATION", "NEEDS_SUBCODE_REVIEW", "NEEDS_SCENARIO_REVIEW"}
            for e in ents
        )
        node["boundaryTypes"] = dict(
            collections.Counter(e.get("boundaryType") for e in ents)
        )
        node["procedureTypes"] = dict(
            collections.Counter(e.get("procedureType") for e in ents)
        )
        node["confidence"] = dict(
            collections.Counter(e.get("confidence") for e in ents)
        )
        node.setdefault("mappedProductionCodes", [code])
    index["statusCount"] = len(idx)


def main() -> int:
    try:
        import fitz  # type: ignore
    except ImportError:
        print("ERROR: PyMuPDF required (pip install pymupdf).", file=sys.stderr)
        return 2

    doc = fitz.open(_STAY_PDF)

    with open(_BACKEND, encoding="utf-8") as fh:
        data = json.load(fh)
    entries = data["entries"]
    existing_keys = {_entry_key(e) for e in entries}

    added = 0
    for rec in RECORDS:
        page_text = doc[rec["page"] - 1].get_text()
        foot = _FOOTER_RE.findall(page_text[:40])
        if not foot or int(foot[0]) != rec["page"]:
            print(
                f"ERROR: footer mismatch for {rec['statusCode']} "
                f"{rec['procedureType']} p.{rec['page']} (head footer={foot})",
                file=sys.stderr,
            )
            return 1
        excerpt = _slice_excerpt(page_text, rec["excerptAnchor"])
        entry = build_entry(rec, excerpt)
        key = _entry_key(entry)
        if key in existing_keys:
            print(f"skip (exists): {key}")
            continue
        entries.append(entry)
        existing_keys.add(key)
        added += 1
        print(f"added: {rec['statusCode']} {rec['procedureType']} p.{rec['page']}")

    data["entryCount"] = len(entries)
    out = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with open(_BACKEND, "w", encoding="utf-8") as fh:
        fh.write(out)
    with open(_MIRROR, "w", encoding="utf-8") as fh:
        fh.write(out)

    with open(_INDEX, encoding="utf-8") as fh:
        index = json.load(fh)
    regenerate_index(index, entries)
    with open(_INDEX, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(index, ensure_ascii=False, indent=2) + "\n")

    ready_total = sum(
        1
        for e in entries
        if e.get("confidence") == "HIGH"
        and e.get("readinessLabel") == "STRUCTURED_EVIDENCE_READY"
    )
    print(
        f"\nDONE: +{added} entries (total {len(entries)}), "
        f"source-confirmed total = {ready_total}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
