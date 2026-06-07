#!/usr/bin/env python3
"""Expanded priority-status procedure-journey cleanup (batch 1).

Reuses the merged D-2 golden-path pattern WITHOUT touching D-2. Scope is
limited to the explicit target statuses. It does not invent documents and
does not remove source-backed documents — it:

  * removes literal placeholder/fragment rows that are not real document
    names (매뉴얼 확인 필요, 페이지 확인 필요, OCR headers/fragments),
  * surfaces the domestic foreigner-registration step for long-stay
    statuses with a concise, user-friendly source-limited notice and
    concrete next actions (no fabricated checklist),
  * labels overseas visa issuance as pre-entry and keeps it separate from
    domestic stay procedures,
  * replaces developer-facing "could not auto-extract" summaries with
    user-friendly source-limited wording,
  * preserves every manualRefs block and all existing source-backed
    document rows and conditional logic (e.g. F-6 spouse/family docs).

visa_data.json is canonical; run scripts/sync_visa_data.py afterwards.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "visa_data.json"

# Rows that are never real document names.
PLACEHOLDER_ROWS = {"매뉴얼 확인 필요", "페이지 확인 필요"}
# Curated OCR fragments/headers seen in target statuses that are not documents.
FRAGMENT_ROWS = {"는 다음과 같습니다.", "체류기간 연장허가필수서류", "체류기간 연장허가 필수서류"}

EMPTY_GROUPS = {"commonDocs": [], "requiredDocs": [], "additionalDocs": [], "conditionalDocs": []}

# Long-stay statuses whose holders must register domestically and where the
# registration tab currently only carries a placeholder. We surface the step
# honestly (no invented documents).
LONGSTAY_REG = [
    "D-4", "D-10", "E-1", "E-2", "E-6", "E-7", "E-9",
    "F-1", "F-2", "F-3", "F-5", "G-1", "F-4", "H-2",
]

REG_NEXT_ACTIONS = (
    "다음 단계: ① HiKorea(hikorea.go.kr)에서 방문 예약 → "
    "② 체류지 관할 출입국·외국인관서 방문(입국 후 90일 이내) → "
    "③ 정확한 제출서류는 HiKorea·1345 또는 관할 출입국·외국인관서에서 확인."
)
REG_SOURCE_NOTE = (
    "외국인등록 공통서류(통합신청서 등)와 자격별 추가서류는 2026.5 체류민원 "
    "매뉴얼·HiKorea에서 최종 확인이 필요합니다."
)


def clean_groups(rd):
    """Drop placeholder/fragment/empty rows from every doc group; dedupe."""
    if not isinstance(rd, dict):
        return rd
    out = {}
    for key in ("commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs"):
        seen = []
        for row in rd.get(key, []) or []:
            text = str(row).strip()
            if not text or text in PLACEHOLDER_ROWS or text in FRAGMENT_ROWS:
                continue
            if text not in seen:
                seen.append(text)
        out[key] = seen
    # preserve any other keys verbatim
    for k, v in rd.items():
        if k not in out:
            out[k] = v
    return out


def clean_proc(proc):
    if not isinstance(proc, dict):
        return
    if "requiredDocs" in proc:
        proc["requiredDocs"] = clean_groups(proc["requiredDocs"])


def add_note(proc, text):
    notes = proc.get("notes")
    if not isinstance(notes, list):
        notes = [] if notes in (None, "") else [str(notes)]
    if text not in notes:
        notes.insert(0, text)
    proc["notes"] = notes


def surface_registration(rec):
    code = rec.get("code")
    name = rec.get("nameKo") or rec.get("name") or code
    reg = rec.setdefault("procedures", {}).get("registration")
    if not isinstance(reg, dict):
        return
    clean_proc(reg)
    reg["available"] = True
    reg["summary"] = (
        f"[입국 후 · 국내 체류절차] {name}({code}) 자격으로 90일을 초과하여 "
        "체류하는 경우, 입국일로부터 90일 이내에 체류지 관할 출입국·외국인관서에서 "
        "외국인등록(외국인등록증 발급)을 해야 합니다. 자격별 제출서류는 세부약호·"
        "국적·체류 이력에 따라 달라 공식 확인이 필요합니다."
    )
    reg["notes"] = [REG_NEXT_ACTIONS, REG_SOURCE_NOTE]
    # No invented documents: leave the document groups empty so the UI shows a
    # single source-limited notice.
    reg["requiredDocs"] = dict(EMPTY_GROUPS)


def prefix_preentry(proc, next_action):
    """Mark a visa-issuance summary as pre-entry/overseas and add next steps."""
    if not isinstance(proc, dict):
        return
    summary = str(proc.get("summary") or "").strip()
    if not summary.startswith("[입국 전"):
        proc["summary"] = (
            "[입국 전 · 재외공관 신청] 사증(비자)은 한국 입국 전에 거주지 관할 "
            "재외공관(대사관·총영사관)에서 신청합니다. 입국 후의 외국인등록·"
            "체류기간 연장과는 별개의 절차입니다. " + summary
        )
    if next_action:
        add_note(proc, next_action)


def main() -> int:
    raw = SOURCE.read_text(encoding="utf-8")
    data = json.loads(raw)
    by_code = {r.get("code"): r for r in data if isinstance(r, dict)}

    # Catch-all hygiene: clean placeholder/fragment rows from every procedure
    # of every target status (D-2 excluded — already cleaned, used as baseline).
    targets = [
        "A-1", "A-2", "A-3", "C-3", "D-4", "D-10", "E-1", "E-2", "E-6", "E-7",
        "E-9", "F-1", "F-2", "F-3", "F-4", "F-5", "F-6", "G-1", "H-1", "H-2",
    ]
    for code in targets:
        rec = by_code.get(code)
        if not rec:
            continue
        for proc in (rec.get("procedures") or {}).values():
            clean_proc(proc)

    # --- Long-stay registration surfacing --------------------------------
    for code in LONGSTAY_REG:
        rec = by_code.get(code)
        if rec:
            surface_registration(rec)

    # H-1 is long-stay (working holiday) but we keep registration separate
    # from work-scope guidance explicitly (status focus requirement).
    h1 = by_code.get("H-1")
    if h1:
        surface_registration(h1)
        reg = h1["procedures"]["registration"]
        reg["notes"].insert(0,
            "외국인등록 절차는 취업 범위·근로조건 안내와 별개입니다. 근무 가능 "
            "범위는 관광취업(H-1) 사증·협정 조건을 따로 확인하세요.")

    # --- C-3: short stay. Do NOT imply universal long-term registration. --
    c3 = by_code.get("C-3")
    if c3:
        procs = c3["procedures"]
        prefix_preentry(procs.get("visaIssuance"),
            "다음 단계: ① 입국 목적(방문·상용·의료 등) 입증서류 준비 → "
            "② 거주지 관할 재외공관에 단기방문(C-3) 사증 신청 → "
            "③ 무사증/전자비자 대상 여부는 재외공관·HiKorea에서 확인.")
        reg = procs.get("registration")
        if isinstance(reg, dict):
            add_note(reg,
                "대부분의 단기방문(C-3) 외국인은 외국인등록 대상이 아닙니다. "
                "아래 안내는 91일 이상 체류가 허용되는 특정 사례에 한합니다.")
        ext = procs.get("extension")
        if isinstance(ext, dict):
            add_note(ext,
                "다음 단계: ① 연장 필요성 소명자료 준비 → "
                "② HiKorea에서 연장 신청 또는 방문 예약 → "
                "③ 단기방문은 입국일로부터 90일 범위 내에서만 제한적으로 연장 "
                "가능하므로 가능 여부를 1345·관할 관서에서 확인.")

    # --- F-6: preserve conditional logic; add labels/next actions only. ---
    f6 = by_code.get("F-6")
    if f6:
        procs = f6["procedures"]
        prefix_preentry(procs.get("visaIssuance"),
            "다음 단계: ① 한국인 배우자측·외국인 신청인측 서류를 각각 준비 → "
            "② 거주지 관할 재외공관에 결혼이민(F-6) 사증 신청 → "
            "③ 국제결혼 안내프로그램 이수 등 사전요건을 재외공관·HiKorea에서 확인.")
        reg = procs.get("registration")
        if isinstance(reg, dict):
            add_note(reg,
                "다음 단계: ① HiKorea에서 방문 예약 → "
                "② 입국 후 90일 이내 체류기간 연장·외국인등록 동시 신청 → "
                "③ 혼인관계·체류지 입증서류를 최신본으로 준비.")
        ext = procs.get("extension")
        if isinstance(ext, dict):
            add_note(ext,
                "다음 단계: ① 본인 상황(혼인 유지·자녀양육·혼인단절)에 맞는 "
                "조건부 서류 확인 → ② 체류기간 만료 전 HiKorea에서 연장 신청 → "
                "③ 사안별 추가 입증서류는 관할 출입국·외국인관서에서 확인.")
        sc = procs.get("statusChange")
        if isinstance(sc, dict):
            sc["summary"] = (
                "[국내 체류자격 변경] F-6(결혼이민)로의 또는 F-6 내 체류자격 변경 "
                "가능 여부와 전용 제출서류는 세부 사유(혼인·자녀양육 등)별로 달라 "
                "관할 출입국·외국인관서의 공식 확인이 필요합니다."
            )

    # --- A-series: diplomatic/official/agreement. Minimal, source-limited. -
    # A-1/A-2 extension carry a placeholder or an OCR sentence as a fake doc
    # row; clear those rows (no invented checklist) and keep the summary.
    for code in ("A-1", "A-2"):
        rec = by_code.get(code)
        if not rec:
            continue
        ext = (rec.get("procedures") or {}).get("extension")
        if isinstance(ext, dict):
            ext["requiredDocs"] = dict(EMPTY_GROUPS)

    # --- Extension hygiene for the OCR-summary statuses -------------------
    # Placeholders already removed above; add a next-action note where the
    # section is user-facing but has no confirmed checklist.
    for code in ("E-2", "F-1", "F-2", "H-2"):
        rec = by_code.get(code)
        if not rec:
            continue
        ext = (rec.get("procedures") or {}).get("extension")
        if isinstance(ext, dict):
            add_note(ext,
                "다음 단계: ① 체류기간 만료 전 HiKorea에서 연장 신청 또는 방문 "
                "예약 → ② 자격별 제출서류는 HiKorea·1345 또는 관할 출입국·"
                "외국인관서에서 확인.")

    # F-3 extension is hidden with a developer message; surface it honestly.
    f3 = by_code.get("F-3")
    if f3:
        ext = (f3.get("procedures") or {}).get("extension")
        if isinstance(ext, dict):
            clean_proc(ext)
            ext["available"] = True
            ext["summary"] = (
                "[입국 후 · 국내 체류절차] 동반(F-3) 체류기간 연장은 주된 체류자격자"
                "(가장)의 체류기간 범위에서 함께 검토됩니다. 자격별 제출서류는 "
                "공식 확인이 필요합니다."
            )
            add_note(ext,
                "다음 단계: ① 주된 체류자격자의 체류기간·자격 확인 → "
                "② 체류기간 만료 전 HiKorea에서 연장 신청 → "
                "③ 가족관계·체류지 입증서류는 관할 출입국·외국인관서에서 확인.")

    out = json.dumps(data, ensure_ascii=False, indent=2)
    if raw.endswith("\n"):
        out += "\n"
    SOURCE.write_text(out, encoding="utf-8")
    print("Applied expanded priority-status journey cleanup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
