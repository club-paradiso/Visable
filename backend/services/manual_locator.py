"""Where in the official stay manual a status + procedure is described.

Used by the deterministic preparation note (``build_legal_analysis_fallback_answer``)
when no model answer is available and the knowledge layer holds no verified
document facts for the question (e.g. F-6 / F-4 / H-1 extension). Instead of a
generic memo, the note points at the exact manual section and page.

Rules (CLAUDE.md):
* Source is the existing 2026.9 status guidance (``data/status-guidance-202609.json``,
  deploy copy ``backend/data/knowledge_deploy/``). Nothing is invented and no
  requirement is restated: only the section heading and PDF page are shown,
  labelled as the September 2026 edition that has not been reviewed line by
  line. (Entry summaries are left out on purpose — the note's confidence gate
  rewrites wording such as "가능합니다", which would misquote the source.)
* Stay procedures only, and only sources whose domain is ``stay`` (visa issuance
  material never answers a stay procedure question).
* A parent code lists each sub-code's section under its own sub-code label; a
  sub-code never inherits another sub-code's entry.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, List, Optional

from .knowledge.paths import repo_data_path

STATUS_GUIDANCE_PATH = repo_data_path(
    "data/status-guidance-202609.json", "knowledge_deploy/status-guidance-202609.json"
)

# Backend task type (``_detect_task_type``) -> status-guidance stay procedure id.
TASK_PROCEDURE: Dict[str, str] = {
    "extension": "extension",
    "status_change": "status_change",
    "workplace_change": "workplace_change",
    "activities_outside_status": "activities_outside_status",
    "foreigner_registration": "registration",
    "address_report": "residence_report",
    "passport_info_report": "registration_info_report",
}

MAX_ENTRIES = 10
_SKIP_STATES = {"NOT_APPLICABLE"}


@lru_cache(maxsize=1)
def _bundle() -> Dict[str, Any]:
    try:
        return json.loads(STATUS_GUIDANCE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _parent(code: str) -> str:
    parts = code.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else code


def locate(status_code: Optional[str], subcode: Optional[str], task_type: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return ``{"entries": [...], "needs_subcode": bool, "source": {...}}`` or None."""
    procedure = TASK_PROCEDURE.get(str(task_type or ""))
    code = str(status_code or "").strip().upper()
    sub = str(subcode or "").strip().upper() or None
    if not procedure or not code:
        return None
    data = _bundle()
    sources = data.get("sources") or {}
    codes = data.get("codes") or {}
    if code not in codes or (sub and sub not in codes):
        return None
    if sub and _parent(sub) != code:
        return None

    def stay_source(manual_id: str) -> Optional[Dict[str, Any]]:
        src = sources.get(manual_id) or {}
        return src if src.get("domain") == "stay" else None

    guidance = [g for g in data.get("guidance") or [] if g.get("procedure") == procedure]
    if sub:
        matched = [g for g in guidance if g.get("target") == sub]
        if not matched:
            matched = [g for g in guidance if g.get("target") == code]
    else:
        matched = [g for g in guidance if _parent(str(g.get("target") or "")) == code]

    entries: List[Dict[str, Any]] = []
    manual: Optional[Dict[str, Any]] = None
    for g in matched:
        src = g.get("source") or {}
        edition = stay_source(str(src.get("manual") or ""))
        if not edition or not src.get("pdf_page"):
            continue
        manual = manual or edition
        entries.append({
            "target": str(g.get("target") or ""),
            "section": " ".join(str(src.get("section") or "").split()),
            "page": int(src["pdf_page"]),
        })

    if not entries:
        # Not structured yet: the code index still records the manual page.
        rec = ((codes.get(sub or code) or {}).get("procedures") or {}).get(procedure) or {}
        if rec.get("s") in _SKIP_STATES or rec.get("m") != "stay" or not rec.get("p"):
            return None
        manual = next((s for s in sources.values() if s.get("domain") == "stay"), None)
        if not manual:
            return None
        entries.append({"target": sub or code, "section": "", "page": int(rec["p"])})

    entries.sort(key=lambda e: (e["page"], e["target"]))
    needs_subcode = bool(not sub and len({e["target"] for e in entries}) > 1)
    return {
        "procedure": procedure,
        "entries": entries,
        "needs_subcode": needs_subcode,
        "source": {
            "title_ko": manual.get("title_ko") or "",
            "title_en": manual.get("title_en") or "",
            "edition": manual.get("edition") or "",
            "official_url": manual.get("official_url") or "",
        },
    }


def note_lines(status_code: Optional[str], subcode: Optional[str], task_type: Optional[str], *,
               is_ko: bool) -> List[str]:
    """Plain-text lines for the preparation note; empty when nothing is located."""
    found = locate(status_code, subcode, task_type)
    if not found:
        return []
    src = found["source"]
    entries = found["entries"]
    shown = entries[:MAX_ENTRIES]
    title = src["title_ko"] if is_ko else (src["title_en"] or src["title_ko"])
    lines: List[str] = []
    if is_ko:
        lines.append(f"공식 매뉴얼 위치 ({title} {src['edition']}, 사람이 한 줄씩 대조 검토하기 전 원문 기준):")
        for e in shown:
            section = f" 「{e['section']}」" if e["section"] else " (구조화 전 원문)"
            lines.append(f"* {e['target']}: p.{e['page']}{section}")
        if len(entries) > len(shown):
            lines.append(f"* 외 {len(entries) - len(shown)}건")
        if found["needs_subcode"]:
            lines.append(f"{status_code}은(는) 세부자격과 상황에 따라 항목이 다르므로, 본인 세부자격에 해당하는 항목만 확인하세요.")
        lines.append("같은 원문은 Visable 홈 검색의 체류자격 안내에서도 확인할 수 있습니다.")
        return lines
    lines.append(f"Where the official manual covers this ({title} {src['edition']}, not yet reviewed line by line by a person):")
    for e in shown:
        section = f" — section 「{e['section']}」" if e["section"] else " (source text, not yet structured)"
        lines.append(f"* {e['target']}: p.{e['page']}{section}")
    if len(entries) > len(shown):
        lines.append(f"* and {len(entries) - len(shown)} more")
    if found["needs_subcode"]:
        lines.append(f"{status_code} differs by sub-status and situation; check only the entry for your own sub-status.")
    lines.append("The same source text is available in the status guide on the Visable home search.")
    return lines


__all__ = ["locate", "note_lines", "TASK_PROCEDURE"]
