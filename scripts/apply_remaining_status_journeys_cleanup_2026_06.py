#!/usr/bin/env python3
"""Remaining standard status-journey cleanup (batch 2).

Reuses the merged D-2 golden-path and expanded-priority cleanup patterns
WITHOUT reworking the already-cleaned statuses. Scope is limited to the
explicit remaining target statuses. It does not invent documents and does
not remove source-backed documents — it:

  * removes literal placeholder/fragment rows that are not real document
    names (매뉴얼 확인 필요, 페이지 확인 필요, OCR headers/fragments such as
    "체류기간 연장허가"),
  * surfaces the domestic foreigner-registration step for long-stay
    statuses (D-1/D-3/D-5/D-6/D-7/D-8 and E-3/E-4/E-5/E-10) with a concise,
    user-friendly, source-limited notice and concrete next actions (no
    fabricated checklist) — each labelled with its own status name/code so
    distinct purposes are never collapsed,
  * keeps short-stay / visa-exemption statuses (B-1/B-2/C-1/C-4) scoped:
    they are NOT presented as ordinary long-term registration statuses;
    instead the registration tab carries a scoped notice that short-stay
    holders are generally not subject to foreigner registration,
  * preserves D-9's existing source-backed registration summary (it already
    carries real content) while dropping the stray placeholder doc row,
  * replaces developer-facing extraction notes ("자동 추출 … 수동 검토") with
    user-friendly source-limited wording, and adds extension next-actions,
  * preserves every manualRefs block and all existing source-backed
    document rows and conditional logic.

visa_data.json is canonical; run scripts/sync_visa_data.py afterwards.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "visa_data.json"

# Rows that are never real document names.
PLACEHOLDER_ROWS = {
    "매뉴얼 확인 필요", "페이지 확인 필요",
    "문서명 미상", "비고 정보 없음", "DATA_MISSING",
}
# Curated OCR fragments/headers that are not documents.
FRAGMENT_ROWS = {
    "는 다음과 같습니다.",
    "체류기간 연장허가필수서류", "체류기간 연장허가 필수서류",
}

EMPTY_GROUPS = {"commonDocs": [], "requiredDocs": [], "additionalDocs": [], "conditionalDocs": []}

# Long-stay statuses whose holders must register domestically and whose
# registration tab currently carries only a developer placeholder. We surface
# the step honestly (no invented documents).
LONGSTAY_REG = ["D-1", "D-3", "D-5", "D-6", "D-7", "D-8", "E-3", "E-4", "E-5", "E-10"]

# Short-stay / visa-exemption statuses: registration is generally N/A.
SHORTSTAY_REG = ["B-1", "B-2", "C-1", "C-4"]

# Every remaining target status (used for catch-all hygiene + extension fixes).
TARGETS = [
    "B-1", "B-2", "C-1", "C-4",
    "D-1", "D-3", "D-5", "D-6", "D-7", "D-8", "D-9",
    "E-3", "E-4", "E-5", "E-10",
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

EXT_NEXT_ACTION = (
    "다음 단계: ① 체류기간 만료 전 HiKorea(hikorea.go.kr)에서 연장 신청 또는 "
    "방문 예약 → ② 자격별 제출서류는 HiKorea·1345 또는 관할 출입국·외국인관서"
    "에서 확인."
)
FRIENDLY_SOURCE_NOTE = (
    "2026.5 체류민원 매뉴얼을 기준으로 정리한 제출서류입니다. 세부약호·국적·"
    "기관·체류 이력에 따라 가감될 수 있어 최종 확인이 필요합니다."
)
DEV_NOTE_MARKERS = (
    "자동 추출", "자동 확정", "PDF 텍스트", "수동 검토", "수동 대조",
    "구조화해야",
)

STAY_LABEL = "[입국 후 · 국내 체류절차]"


def is_header_fragment(text: str) -> bool:
    """True for OCR rows that are only section-header words, no real document."""
    stripped = re.sub(r"[\s\d.·\-()]", "", text)
    for token in ("체류기간연장허가", "제출서류", "필수서류", "제출", "서류"):
        stripped = stripped.replace(token, "")
    return stripped == ""


def clean_groups(rd):
    """Drop placeholder/fragment/header/empty rows from every doc group; dedupe."""
    if not isinstance(rd, dict):
        return rd
    out = {}
    for key in ("commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs"):
        seen = []
        for row in rd.get(key, []) or []:
            text = str(row).strip()
            if not text or text in PLACEHOLDER_ROWS or text in FRAGMENT_ROWS:
                continue
            if is_header_fragment(text):
                continue
            if text not in seen:
                seen.append(text)
        out[key] = seen
    for k, v in rd.items():  # preserve any other keys verbatim
        if k not in out:
            out[k] = v
    return out


def clean_proc(proc):
    if not isinstance(proc, dict):
        return
    if "requiredDocs" in proc:
        proc["requiredDocs"] = clean_groups(proc["requiredDocs"])


def friendlify_notes(notes):
    """Replace developer-facing extraction notes with a user-friendly one."""
    out = []
    replaced = False
    for n in notes or []:
        s = str(n)
        if any(m in s for m in DEV_NOTE_MARKERS):
            if not replaced:
                out.append(FRIENDLY_SOURCE_NOTE)
                replaced = True
            continue
        out.append(s)
    return out


def add_note(proc, text, *, front=False):
    notes = proc.get("notes")
    if not isinstance(notes, list):
        notes = [] if notes in (None, "") else [str(notes)]
    if text not in notes:
        (notes.insert(0, text) if front else notes.append(text))
    proc["notes"] = notes


def label_summary(proc):
    summary = str(proc.get("summary") or "").strip()
    if summary and not summary.startswith("[입국"):
        proc["summary"] = f"{STAY_LABEL} {summary}"


def docs_empty(rd) -> bool:
    if not isinstance(rd, dict):
        return True
    return not any((rd.get(k) or []) for k in
                   ("commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs"))


def surface_registration(rec):
    """Honest source-limited registration surfacing for long-stay statuses."""
    code = rec.get("code")
    name = rec.get("nameKo") or rec.get("name") or code
    reg = rec.setdefault("procedures", {}).get("registration")
    if not isinstance(reg, dict):
        return
    clean_proc(reg)
    reg["available"] = True
    reg["summary"] = (
        f"{STAY_LABEL} {name}({code}) 자격으로 입국하여 90일을 초과해 체류하는 "
        "경우, 입국일로부터 90일 이내에 체류지 관할 출입국·외국인관서에서 "
        "외국인등록(외국인등록증 발급)을 해야 합니다. 자격별 제출서류는 세부약호·"
        "국적·체류 이력에 따라 달라 공식 확인이 필요합니다."
    )
    reg["notes"] = [REG_NEXT_ACTIONS, REG_SOURCE_NOTE]
    # No invented documents: leave the document groups empty so the UI shows a
    # single source-limited notice.
    reg["requiredDocs"] = dict(EMPTY_GROUPS)


def scope_registration(rec):
    """Scoped short-stay/exemption registration notice (not the long-stay template)."""
    code = rec.get("code")
    name = rec.get("nameKo") or rec.get("name") or code
    reg = rec.setdefault("procedures", {}).get("registration")
    if not isinstance(reg, dict):
        return
    clean_proc(reg)
    reg["available"] = True
    reg["summary"] = (
        f"{STAY_LABEL} {name}({code})는 단기·단수 체류 목적의 자격으로, 원칙적으로 "
        "외국인등록 대상이 아닙니다. 외국인등록은 장기체류(원칙적으로 91일 이상) "
        "자격을 부여·변경받은 경우에 한해 적용됩니다."
    )
    reg["notes"] = [
        "체류 목적·기간이 장기체류 자격으로 바뀌는 경우의 등록 의무·서류는 "
        "HiKorea·1345 또는 관할 출입국·외국인관서에서 확인하세요.",
    ]
    reg["requiredDocs"] = dict(EMPTY_GROUPS)


def fix_extension(rec):
    """Clean fragments, friendly-fy notes, label, and add next-action to extension."""
    ext = (rec.get("procedures") or {}).get("extension")
    if not isinstance(ext, dict):
        return
    clean_proc(ext)
    ext["notes"] = friendlify_notes(ext.get("notes"))
    summary = str(ext.get("summary") or "").strip()
    # If the extension summary is only an OCR header (no real guidance) and no
    # documents survived cleanup, replace it with a concise source-limited notice.
    if is_header_fragment(summary) or not summary:
        if docs_empty(ext.get("requiredDocs")):
            name = rec.get("nameKo") or rec.get("name") or rec.get("code")
            ext["summary"] = (
                f"{STAY_LABEL} {name}({rec.get('code')}) 체류기간 연장은 체류기간 "
                "만료 전에 신청합니다. 자격별 제출서류는 세부 사유·체류 이력에 따라 "
                "달라 공식 확인이 필요합니다."
            )
        else:
            label_summary(ext)
    else:
        label_summary(ext)
    add_note(ext, EXT_NEXT_ACTION, front=True)


def main() -> int:
    raw = SOURCE.read_text(encoding="utf-8")
    data = json.loads(raw)
    by_code = {r.get("code"): r for r in data if isinstance(r, dict)}

    # Catch-all hygiene: clean placeholder/fragment rows from every procedure
    # of every target status.
    for code in TARGETS:
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

    # --- Short-stay / exemption: scoped registration notice --------------
    for code in SHORTSTAY_REG:
        rec = by_code.get(code)
        if rec:
            scope_registration(rec)

    # --- D-9: keep its real source-backed registration summary -----------
    # It already carries embedded document guidance; just drop the stray
    # placeholder row and friendly-fy the developer note (no overwrite).
    d9 = by_code.get("D-9")
    if d9:
        reg = (d9.get("procedures") or {}).get("registration")
        if isinstance(reg, dict):
            clean_proc(reg)
            reg["notes"] = friendlify_notes(reg.get("notes"))
            label_summary(reg)
            add_note(reg, REG_NEXT_ACTIONS, front=False)

    # --- Extension hygiene + next-actions for every target ---------------
    for code in TARGETS:
        rec = by_code.get(code)
        if rec:
            fix_extension(rec)

    out = json.dumps(data, ensure_ascii=False, indent=2)
    if raw.endswith("\n"):
        out += "\n"
    SOURCE.write_text(out, encoding="utf-8")
    print("Applied remaining status-journey cleanup (batch 2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
