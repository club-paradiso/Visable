"""Procedure Packet Builder + safe Application Typing Helper scaffold.

Paradiso is evolving from an "AI visa search" tool into an official-source-based
stay/residence **administration preparation** platform. This module turns the
official-source data the project already curates (the source-confirmed
structured manual requirements + the per-visa procedure document lists) into
deterministic, source-graded **preparation packets** for common immigration /
residence procedures, plus a privacy-safe **통합신청서 typing helper** scaffold.

Two layers around the 통합신청서 (official Integrated Application Form, the
출입국관리법 시행규칙 별지 제34호 서식):

1. **As an official document** — when a procedure's source data lists 통합신청서
   / 별지 제34호, the packet surfaces it as a real ``PacketDocument`` (source-
   backed when the manual/enforcement-rule source supports it), with its
   official name preserved. It is never reduced to a placeholder.
2. **As a typing helper** — separately, ``applicationTypingHelper`` explains, in
   ``typing_guide_only`` mode, what information a user may need to prepare before
   manually typing the official form. It REFERENCES the official 통합신청서; it
   never replaces it, auto-fills it, submits it, predicts approval, or collects /
   stores / transmits any personal identifier.

Hard guarantees:

* Deterministic. No LLM call. No network.
* No personal data is accepted, stored, logged, or sent anywhere. The typing
  helper emits field *guidance* only — never values.
* No invented documents, fees, deadlines, or channels. Missing coverage is
  represented as a public-safe ``limitationKo`` / ``unavailable`` source lens,
  never as fake rows or raw developer diagnostics.
* Placeholder source strings (e.g. "매뉴얼 확인 필요") are filtered out, never
  shown as documents.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

# ``structured_requirements`` lives at backend/ (top-level when backend/ is on
# sys.path — both in production and in tests that insert BACKEND_DIR). Guard the
# import so the builder degrades gracefully (visa_data only) if it is absent.
try:  # pragma: no cover - import shim
    import structured_requirements as _sr  # type: ignore
except Exception:  # pragma: no cover
    _sr = None  # type: ignore
from . import document_labels as _document_labels


PROCEDURE_PACKET_VERSION = "2026-06-procedure-packet-and-application-helper-v1"

# ---------------------------------------------------------------------------
# Procedure-key mappings
# ---------------------------------------------------------------------------
# visa_data.json procedures.* key  ->  public packet type
PACKET_TYPE_BY_PROCEDURE_KEY: Dict[str, str] = {
    "registration": "foreigner_registration",
    "extension": "extension",
    "statusChange": "status_change",
    "activitiesOutsideStatus": "activities_outside_status",
    "workplaceChange": "workplace_change",
    "reentry": "reentry_permit",
    "statusGrant": "status_grant",
    "visaIssuance": "visa_issuance",
}
PROCEDURE_KEY_BY_PACKET_TYPE: Dict[str, str] = {
    v: k for k, v in PACKET_TYPE_BY_PROCEDURE_KEY.items()
}
# structured_requirements procedureType per packet type (only where a
# source-confirmed manual layer actually exists today).
_SR_PROCEDURE_TYPE_BY_PACKET: Dict[str, Optional[str]] = {
    "foreigner_registration": "registration",
    "extension": "extension",
    "visa_issuance": "visa_issuance",
}
# feeInfo.paradisoDefault202605.procedures.* key per packet type.
_FEE_KEY_BY_PACKET: Dict[str, str] = {
    "foreigner_registration": "foreignRegistration",
    "extension": "extension",
    "status_change": "statusChange",
    "status_grant": "grantStatus",
    "visa_issuance": "visaIssuance",
}

PACKET_TITLES: Dict[str, Tuple[str, str]] = {
    "foreigner_registration": ("외국인등록", "Foreigner Registration"),
    "extension": ("체류기간 연장허가", "Extension of Stay"),
    "status_change": ("체류자격 변경허가", "Change of Status"),
    "activities_outside_status": ("체류자격외활동 허가", "Activities Outside Status"),
    "workplace_change": ("근무처 변경·추가", "Workplace Change / Addition"),
    "reentry_permit": ("재입국허가", "Re-entry Permit"),
    "status_grant": ("체류자격 부여", "Grant of Status"),
    "visa_issuance": ("사증발급", "Visa Issuance"),
}

SUPPORTED_PACKET_TYPES: Tuple[str, ...] = tuple(PACKET_TITLES.keys())

# ---------------------------------------------------------------------------
# Public-safe source lens
# ---------------------------------------------------------------------------
SOURCE_LENS_LEVELS: Tuple[str, ...] = (
    "source_confirmed", "contextual", "limited", "unavailable", "final_agency_discretion",
)
SOURCE_LENS_LABELS_KO: Dict[str, str] = {
    "source_confirmed": "공식근거 직접 확인",
    "contextual": "관련 공식근거 있음",
    "limited": "공식근거 제한",
    "unavailable": "공식근거 확인 불가",
    "final_agency_discretion": "관할기관 최종심사 필요",
}
# Human-authored, public-safe EN labels (navigator chrome only — NOT a
# translation of any official/legal content). Mirrors SOURCE_LENS_LABELS_KO so
# the all-status navigator can render source coverage in English without an LLM.
SOURCE_LENS_LABELS_EN: Dict[str, str] = {
    "source_confirmed": "Confirmed in official source",
    "contextual": "Partially covered by official sources",
    "limited": "Official confirmation required",
    "unavailable": "No current source coverage",
    "final_agency_discretion": "Subject to competent authority's final review",
}

# Required safety note (verbatim per product spec).
FINAL_AGENCY_NOTE_KO = (
    "이 패킷과 통합신청서 작성 도우미는 신청 준비를 돕는 안내이며, 실제 허가 여부와 "
    "제출 가능 여부는 관할 출입국·외국인관서 및 공식 신청서 기준에 따릅니다."
)
FINAL_AGENCY_NOTE_EN = (
    "This packet and the application-form typing helper are preparation guidance "
    "only. Whether your application is accepted or approved is decided by the "
    "competent immigration office and the official application standards."
)

# Public-safe coverage levels (derived from the source lens + document presence)
# so the front-end can deterministically decide between a full Action Packet and
# a coverage-limited packet without re-deriving the rule.
_COVERAGE_LEVEL_BY_LENS: Dict[str, str] = {
    "source_confirmed": "full",
    "contextual": "partial",
    "limited": "limited",
    "unavailable": "unavailable",
}

# Universal "common" documents (regrouping existing doc text, never invented).
_COMMON_DOC_MARKERS = ("통합신청서", "신청서", "여권", "외국인등록증", "수수료", "표준규격사진", "사진")
# The official Integrated Application Form references (출입국관리법 시행규칙 별지 서식).
_OFFICIAL_FORM_MARKERS = ("통합신청서", "별지 제34호", "별지제34호")
_OFFICIAL_FORM_NOTE_KO = "출입국관리법 시행규칙 별지 서식 기준의 공식 신청서(통합신청서)입니다."
# Conditional-document text markers (kept conditional, never silently promoted).
_CONDITIONAL_MARKERS = ("해당자", "해당 시", "해당시", "필요시", "필요 시", "(예:", "선택")
# Needs-review / placeholder strings that must NEVER be shown as a document.
_PLACEHOLDER_MARKERS = (
    "매뉴얼 확인 필요", "확인 필요", "문서명 미상", "미상", "정보 없음",
    "비고 정보 없음", "해당 없음", "준비중", "추후", "TBD", "n/a", "N/A",
)


def _now_path_visas() -> str:
    """Resolve the visa data file path (mirrors the backend's precedence)."""
    explicit = os.environ.get("VISA_DATA_PATH", "").strip()
    if explicit:
        return explicit
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
    repo_root = os.path.dirname(here)
    backend_copy = os.path.join(here, "data", "visas.json")
    if os.path.exists(backend_copy):
        return backend_copy
    return os.path.join(repo_root, "visa_data.json")


_lock = threading.Lock()
_visa_cache: Optional[Dict[str, Dict[str, Any]]] = None


def reset_cache_for_tests() -> None:
    """Clear the visa-record cache (used by tests that swap the data path)."""
    global _visa_cache
    with _lock:
        _visa_cache = None


def _load_visa_index() -> Dict[str, Dict[str, Any]]:
    """Load + cache visa records keyed by ``code`` (defensive; never raises)."""
    global _visa_cache
    if _visa_cache is not None:
        return _visa_cache
    with _lock:
        if _visa_cache is not None:
            return _visa_cache
        index: Dict[str, Dict[str, Any]] = {}
        try:
            with open(_now_path_visas(), "r", encoding="utf-8") as fh:
                records = json.load(fh)
            if isinstance(records, list):
                for rec in records:
                    if isinstance(rec, dict) and rec.get("code"):
                        index[str(rec["code"])] = rec
        except (OSError, json.JSONDecodeError):
            index = {}
        _visa_cache = index
        return _visa_cache


def _parent_code(status_code: str) -> str:
    """Parent code for a sub-code (D-2-1 -> D-2); pass-through otherwise."""
    code = (status_code or "").strip().upper()
    parts = code.split("-")
    if len(parts) >= 3:  # e.g. D-2-1 -> D-2
        return f"{parts[0]}-{parts[1]}"
    return code


def _visa_record(status_code: str) -> Optional[Dict[str, Any]]:
    """Resolve a visa record by exact code, then by parent code."""
    index = _load_visa_index()
    code = (status_code or "").strip().upper()
    if code in index:
        return index[code]
    parent = _parent_code(code)
    return index.get(parent)


# ---------------------------------------------------------------------------
# Source helpers
# ---------------------------------------------------------------------------
def _packet_source(
    *,
    source_family: str,
    source_name_ko: str,
    evidence_level: str,
    version_date: str = "",
    page_range: str = "",
    article: str = "",
    url: str = "",
) -> Dict[str, Any]:
    src: Dict[str, Any] = {
        "sourceFamily": source_family,
        "sourceNameKo": source_name_ko,
        "evidenceLevel": evidence_level,
    }
    for key, value in (
        ("versionDate", version_date), ("pageRange", page_range),
        ("article", article), ("url", url),
    ):
        if value:
            src[key] = value
    return src


def _manual_source_from_sr_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    ms = entry.get("manualSource") or {}
    page = ""
    if ms.get("pageStart") and ms.get("pageEnd"):
        page = f"pp. {ms.get('pageStart')}-{ms.get('pageEnd')}"
    elif ms.get("pageStart"):
        page = f"p. {ms.get('pageStart')}"
    return _packet_source(
        source_family="manual",
        source_name_ko=str(ms.get("manualName") or "외국인체류 안내매뉴얼"),
        evidence_level="source_confirmed",
        version_date=str(ms.get("manualVersion") or ms.get("sourceRevisionDate") or ""),
        page_range=page,
    )


def _manual_source_from_visa_refs(manual_refs: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for ref in manual_refs or []:
        if not isinstance(ref, dict):
            continue
        page = str(ref.get("pageRange") or "")
        if _is_placeholder(page):
            page = ""
        out.append(_packet_source(
            source_family="manual",
            source_name_ko=str(ref.get("manualName") or "체류 안내매뉴얼"),
            evidence_level="contextual",
            version_date=str(ref.get("manualVersion") or ref.get("sourceDate") or ""),
            page_range=page,
        ))
    return out


# ---------------------------------------------------------------------------
# Document normalization + grouping
# ---------------------------------------------------------------------------
def _is_placeholder(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    return any(marker.lower() in t.lower() for marker in _PLACEHOLDER_MARKERS)


def _is_official_form(text: str) -> bool:
    return any(marker in (text or "") for marker in _OFFICIAL_FORM_MARKERS)


def _looks_conditional(text: str) -> bool:
    return any(marker in (text or "") for marker in _CONDITIONAL_MARKERS)


def _is_common_doc(text: str) -> bool:
    return any(marker in (text or "") for marker in _COMMON_DOC_MARKERS)


def _classify_group(text: str, *, requiredness: str = "required", condition_ko: str = "") -> str:
    """Group a document into common / required / conditional / additional."""
    if requiredness in ("conditional",) or condition_ko or _looks_conditional(text):
        return "conditionalDocs"
    if _is_common_doc(text):
        return "commonDocs"
    if requiredness in ("optional", "additional"):
        return "additionalDocs"
    return "requiredDocs"


def _make_document(
    text: str,
    *,
    requiredness: str = "required",
    condition_ko: str = "",
    note_ko: str = "",
    source_backed: bool,
    source_refs: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Build a PacketDocument from a doc string (returns None for placeholders)."""
    # visa_data document arrays mix manual prose with doc_master IDs. An ID that
    # reaches `nameKo` is rendered to the user as the name of a document they
    # must bring to an immigration office, so resolve it to its registered label
    # first. Non-IDs and IDs doc_master does not define pass through unchanged —
    # inventing a label would be fabricating a requirement.
    name = str(_document_labels.resolve_document_label((text or "").strip())).strip()
    if _is_placeholder(name):
        return None
    note = (note_ko or "").strip()
    if _is_official_form(name):
        note = (note + " " if note else "") + _OFFICIAL_FORM_NOTE_KO
    doc: Dict[str, Any] = {
        "nameKo": name,
        "sourceBacked": bool(source_backed),
        "sourceRefs": list(source_refs or []),
    }
    if note:
        doc["noteKo"] = note.strip()
    if condition_ko:
        doc["conditionKo"] = condition_ko
    doc["isOfficialForm"] = _is_official_form(name)
    return doc


def _empty_doc_groups() -> Dict[str, List[Dict[str, Any]]]:
    return {"commonDocs": [], "requiredDocs": [], "conditionalDocs": [], "additionalDocs": []}


def _documents_from_sr_entries(entries: List[Dict[str, Any]]) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    """Source-confirmed documents (with manual page refs) grouped into the 4 sets."""
    groups = _empty_doc_groups()
    sources: List[Dict[str, Any]] = []
    seen = set()
    for entry in entries:
        ref = _manual_source_from_sr_entry(entry)
        _add_unique_source(sources, ref)
        for doc in entry.get("documents") or []:
            if not isinstance(doc, dict):
                continue
            text = str(doc.get("textKo") or "").strip()
            packet_doc = _make_document(
                text,
                requiredness=str(doc.get("requiredness") or "required"),
                condition_ko=str(doc.get("conditionKo") or ""),
                note_ko=str(doc.get("notesKo") or ""),
                source_backed=True,
                source_refs=[ref],
            )
            if packet_doc is None:
                continue
            key = (packet_doc["nameKo"],)
            if key in seen:
                continue
            seen.add(key)
            groups[_classify_group(text, requiredness=str(doc.get("requiredness") or "required"),
                                   condition_ko=str(doc.get("conditionKo") or ""))].append(packet_doc)
    return groups, sources


def _documents_from_visa_groups(
    required_docs: Dict[str, Any], source_refs: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Documents from visa_data procedure.requiredDocs (already grouped strings)."""
    groups = _empty_doc_groups()
    seen = set()
    for group_key in ("commonDocs", "requiredDocs", "conditionalDocs", "additionalDocs"):
        for item in (required_docs.get(group_key) or []):
            if not isinstance(item, str):
                continue
            packet_doc = _make_document(
                item,
                requiredness="conditional" if group_key == "conditionalDocs" else "required",
                source_backed=False,
                source_refs=source_refs,
            )
            if packet_doc is None:
                continue
            key = (packet_doc["nameKo"],)
            if key in seen:
                continue
            seen.add(key)
            # Respect the source grouping, but re-route official form / common
            # docs to commonDocs and conditional-marked docs to conditionalDocs.
            target = group_key
            if group_key in ("requiredDocs", "additionalDocs"):
                if _looks_conditional(item):
                    target = "conditionalDocs"
                elif _is_common_doc(item):
                    target = "commonDocs"
            groups[target].append(packet_doc)
    return groups


def _doc_count(groups: Dict[str, List[Dict[str, Any]]]) -> int:
    return sum(len(v) for v in groups.values())


def _add_unique_source(sources: List[Dict[str, Any]], ref: Dict[str, Any]) -> None:
    key = (ref.get("sourceFamily"), ref.get("sourceNameKo"), ref.get("pageRange"), ref.get("versionDate"))
    if key not in {(s.get("sourceFamily"), s.get("sourceNameKo"), s.get("pageRange"), s.get("versionDate")) for s in sources}:
        sources.append(ref)


# ---------------------------------------------------------------------------
# Fees
# ---------------------------------------------------------------------------
def _build_fees(record: Optional[Dict[str, Any]], packet_type: str) -> Dict[str, Any]:
    fee_key = _FEE_KEY_BY_PACKET.get(packet_type)
    fee_info = ((record or {}).get("feeInfo") or {}).get("paradisoDefault202605") or {}
    caution = str(fee_info.get("displayCaution") or "")
    block = (fee_info.get("procedures") or {}).get(fee_key) if fee_key else None
    if not isinstance(block, dict) or not block.get("items"):
        return {
            "items": [],
            "sourceBacked": False,
            "limitationKo": "이 절차의 수수료는 현재 공식근거로 확정 표시할 수 없습니다. 면제·감면·온라인 신청 여부에 따라 달라질 수 있어 1345/HiKorea/관할기관에서 확인하세요.",
        }
    items = []
    for it in block["items"]:
        if not isinstance(it, dict):
            continue
        label = str(it.get("name") or block.get("labelKo") or "수수료")
        amount = str(it.get("display") or (f"{it.get('amountKRW'):,}원" if it.get("amountKRW") else ""))
        items.append({
            "labelKo": label,
            "amountKo": amount,
            "sourceBacked": False,  # feeInfo is verified:false -> display metadata only
            "sourceRefs": [],
        })
    # feeInfo is explicitly verified:false / needsManualReview -> contextual at best.
    return {
        "items": items,
        "sourceBacked": False,
        "limitationKo": caution or "표시용 기본 수수료이며 최종 금액은 관할기관/1345/HiKorea에서 확인하세요.",
    }


# ---------------------------------------------------------------------------
# Application Typing Helper (safe, typing-guide-only)
# ---------------------------------------------------------------------------
# Generic, non-personal field groups for the official 통합신청서. These describe
# WHAT a field is and WHERE to find the info — never collect or store values.
_FIELD_GROUPS: List[Dict[str, Any]] = [
    {
        "groupId": "applicant_identity",
        "labelKo": "신청인 인적사항",
        "purposeKo": "여권상 신원 정보를 공식 서식에 직접 입력하기 위한 항목입니다.",
        "relevance": "all",
        "fields": [
            {"fieldId": "full_name", "labelKo": "성명(영문/한글)", "explanationKo": "여권에 기재된 성명을 그대로 입력합니다.", "requiredness": "required_if_applicable", "doNotStore": True, "userShouldTypeFrom": ["여권"]},
            {"fieldId": "date_of_birth", "labelKo": "생년월일", "explanationKo": "여권상 생년월일을 입력합니다.", "requiredness": "required_if_applicable", "doNotStore": True, "userShouldTypeFrom": ["여권"]},
            {"fieldId": "sex", "labelKo": "성별", "explanationKo": "여권상 성별을 입력합니다.", "requiredness": "required_if_applicable", "doNotStore": True, "userShouldTypeFrom": ["여권"]},
            {"fieldId": "nationality", "labelKo": "국적", "explanationKo": "여권상 국적을 입력합니다.", "requiredness": "required_if_applicable", "doNotStore": True, "userShouldTypeFrom": ["여권"]},
        ],
    },
    {
        "groupId": "current_stay_status",
        "labelKo": "현재 체류 정보",
        "purposeKo": "현재 체류자격·체류기간·등록정보를 확인하여 입력하기 위한 항목입니다.",
        "relevance": "stay",  # all except visa_issuance
        "fields": [
            {"fieldId": "current_status", "labelKo": "체류자격", "explanationKo": "현재 보유한 체류자격(예: D-2)을 입력합니다.", "requiredness": "required_if_applicable", "doNotStore": True, "userShouldTypeFrom": ["외국인등록증", "여권 사증"]},
            {"fieldId": "period_of_stay", "labelKo": "체류기간(만료일)", "explanationKo": "현재 허가된 체류기간/만료일을 입력합니다.", "requiredness": "required_if_applicable", "doNotStore": True, "userShouldTypeFrom": ["외국인등록증", "여권 사증"]},
            {"fieldId": "registration_no", "labelKo": "외국인등록번호", "explanationKo": "외국인등록을 마친 경우 등록번호를 입력합니다. 개인식별정보이므로 저장하지 않습니다.", "requiredness": "conditional", "doNotStore": True, "userShouldTypeFrom": ["외국인등록증"]},
        ],
    },
    {
        "groupId": "application_request_type",
        "labelKo": "신청 구분",
        "purposeKo": "어떤 절차를 신청하는지 공식 서식의 신청 구분란에 표시하기 위한 항목입니다.",
        "relevance": "all",
        "fields": [
            {"fieldId": "request_type", "labelKo": "신청 구분(절차)", "explanationKo": "이 패킷의 절차(예: 체류기간 연장허가, 체류자격 변경허가, 외국인등록)에 해당하는 항목을 선택/표시합니다.", "requiredness": "required_if_applicable", "doNotStore": False, "userShouldTypeFrom": ["이 절차 안내"]},
        ],
    },
    {
        "groupId": "address_contact",
        "labelKo": "체류지/연락처",
        "purposeKo": "국내 체류지와 연락처를 입력하기 위한 항목입니다.",
        "relevance": "stay",
        "fields": [
            {"fieldId": "address_in_korea", "labelKo": "대한민국 내 체류지", "explanationKo": "현재 거주하는 국내 주소를 입력합니다. 개인정보이므로 저장하지 않습니다.", "requiredness": "required_if_applicable", "doNotStore": True, "userShouldTypeFrom": ["체류지 입증서류"]},
            {"fieldId": "phone", "labelKo": "전화번호", "explanationKo": "연락 가능한 전화번호를 입력합니다. 저장하지 않습니다.", "requiredness": "conditional", "doNotStore": True, "userShouldTypeFrom": ["본인 확인"]},
            {"fieldId": "email", "labelKo": "이메일", "explanationKo": "연락 가능한 이메일을 입력합니다. 저장하지 않습니다.", "requiredness": "conditional", "doNotStore": True, "userShouldTypeFrom": ["본인 확인"]},
        ],
    },
    {
        "groupId": "workplace_school_activity",
        "labelKo": "근무처/학교/활동 정보",
        "purposeKo": "취업·유학·활동 관련 절차에서 소속 또는 활동 정보를 입력하기 위한 항목입니다.",
        "relevance": "activity",  # extension/status_change/activities/workplace
        "fields": [
            {"fieldId": "affiliation", "labelKo": "소속(근무처/학교 등)", "explanationKo": "소속 기관명 등을 공식 증빙서류 기준으로 입력합니다. 저장하지 않습니다.", "requiredness": "conditional", "doNotStore": True, "userShouldTypeFrom": ["재직/재학 증빙서류"]},
            {"fieldId": "activity_detail", "labelKo": "활동 내용", "explanationKo": "신청하는 활동의 내용을 입력합니다.", "requiredness": "conditional", "doNotStore": True, "userShouldTypeFrom": ["관련 증빙서류"]},
        ],
    },
    {
        "groupId": "passport_arc_reference",
        "labelKo": "여권/외국인등록 참조정보",
        "purposeKo": "여권·외국인등록 관련 참조정보를 입력하기 위한 항목입니다.",
        "relevance": "all",
        "fields": [
            {"fieldId": "passport_no", "labelKo": "여권번호", "explanationKo": "여권번호를 입력합니다. 개인식별정보이므로 저장하지 않습니다.", "requiredness": "required_if_applicable", "doNotStore": True, "userShouldTypeFrom": ["여권"]},
            {"fieldId": "passport_dates", "labelKo": "여권 발급일/만료일", "explanationKo": "여권의 발급일과 만료일을 입력합니다.", "requiredness": "required_if_applicable", "doNotStore": True, "userShouldTypeFrom": ["여권"]},
        ],
    },
    {
        "groupId": "accompanying_family",
        "labelKo": "동반가족 정보",
        "purposeKo": "동반가족이 있는 절차에서 가족 정보를 입력하기 위한 항목입니다.",
        "relevance": "family",  # status_change/registration when applicable
        "fields": [
            {"fieldId": "family_members", "labelKo": "동반가족", "explanationKo": "동반가족이 있는 경우에만 가족 정보를 입력합니다. 저장하지 않습니다.", "requiredness": "conditional", "doNotStore": True, "userShouldTypeFrom": ["가족관계 증빙서류"]},
        ],
    },
    {
        "groupId": "signature_date",
        "labelKo": "신청일/서명",
        "purposeKo": "공식 서식의 신청일·서명·대리인 표시 항목입니다.",
        "relevance": "all",
        "fields": [
            {"fieldId": "application_date", "labelKo": "신청일", "explanationKo": "신청서를 작성/제출하는 날짜를 입력합니다.", "requiredness": "required_if_applicable", "doNotStore": False, "userShouldTypeFrom": ["작성일"]},
            {"fieldId": "signature", "labelKo": "신청인 서명", "explanationKo": "공식 서식에 직접 서명합니다. 이 도우미는 서명을 받지 않습니다.", "requiredness": "required_if_applicable", "doNotStore": True, "userShouldTypeFrom": ["본인 서명"]},
        ],
    },
]

_RELEVANCE_BY_PACKET: Dict[str, set] = {
    "foreigner_registration": {"all", "stay", "family"},
    "extension": {"all", "stay", "activity"},
    "status_change": {"all", "stay", "activity", "family"},
    "activities_outside_status": {"all", "stay", "activity"},
    "workplace_change": {"all", "stay", "activity"},
    "reentry_permit": {"all", "stay"},
    "status_grant": {"all", "stay"},
    "visa_issuance": {"all"},
}

_HELPER_WARNINGS_KO = [
    "이 도우미는 통합신청서를 자동으로 작성하거나 제출하지 않습니다.",
    "여권번호, 외국인등록번호, 주소, 연락처, 소속 등 개인정보는 저장하거나 AI로 전송하지 않습니다.",
    "허가 가능성을 예측하지 않습니다.",
    "실제 서식·필수 항목·조건은 공식 통합신청서(출입국관리법 시행규칙 별지 제34호 서식)와 관할기관 기준을 따릅니다.",
]


def build_application_typing_helper(
    packet_type: str,
    *,
    status_code: Optional[str] = None,
    has_official_form_document: bool = False,
    locale: str = "ko",
) -> Dict[str, Any]:
    """Build the safe, typing-guide-only 통합신청서 preparation helper.

    Emits field *guidance* only — never collects, stores, logs, or transmits any
    value. It references the official Integrated Application Form
    (출입국관리법 시행규칙 별지 제34호 서식) but never replaces, fills, or submits it.
    """
    title_ko = PACKET_TITLES.get(packet_type, (packet_type, packet_type))[0]
    relevant = _RELEVANCE_BY_PACKET.get(packet_type, {"all"})
    field_groups: List[Dict[str, Any]] = []
    for group in _FIELD_GROUPS:
        if group["relevance"] not in relevant:
            continue
        field_groups.append({
            "groupId": group["groupId"],
            "labelKo": group["labelKo"],
            "purposeKo": group["purposeKo"],
            # The official Form 34 field layout is the authority; we provide
            # generic, non-personal guidance, so each group is source-limited.
            "sourceBacked": False,
            "limitationKo": "정확한 서식 항목과 필수 여부는 공식 통합신청서(별지 제34호 서식) 기준을 따릅니다.",
            "fields": [
                {
                    "fieldId": f["fieldId"],
                    "labelKo": f["labelKo"],
                    "explanationKo": f["explanationKo"],
                    "requiredness": f.get("requiredness", "unknown"),
                    "doNotStore": bool(f.get("doNotStore", True)),
                    "userShouldTypeFrom": list(f.get("userShouldTypeFrom") or []),
                    **({"cautionKo": f["cautionKo"]} if f.get("cautionKo") else {}),
                    "sourceRefs": [],  # field-level layout not source-confirmed yet
                }
                for f in group["fields"]
            ],
        })
    preparation_notes = [
        "공식 통합신청서(별지 제34호 서식)는 정부 공식 양식을 사용해 직접 작성합니다.",
        "이 도우미는 작성 전에 어떤 정보를 준비하면 되는지 안내만 합니다.",
        "개인식별정보(여권번호, 외국인등록번호, 주소 등)는 여기에 입력하지 말고 공식 서식에 직접 작성하세요.",
    ]
    if has_official_form_document:
        preparation_notes.insert(
            0,
            "이 절차의 준비 서류 목록에 통합신청서(별지 제34호 서식)가 공식 서류로 포함되어 있습니다.",
        )
    helper_id = f"typing-helper.{packet_type}" + (f".{status_code}" if status_code else "")
    return {
        "helperId": helper_id,
        "titleKo": f"{title_ko} 통합신청서 작성 준비 도우미",
        "procedureType": packet_type,
        "mode": "typing_guide_only",
        "privacyMode": "no_storage_no_llm_for_personal_data",
        "referencesOfficialForm": {
            "nameKo": "통합신청서(별지 제34호 서식)",
            "nameEn": "Integrated Application Form",
            "basisKo": "출입국관리법 시행규칙 별지 서식",
            "noteKo": "이 도우미는 공식 서식을 대체하지 않으며 작성 준비만 돕습니다.",
        },
        "fieldGroups": field_groups,
        "preparationNotes": preparation_notes,
        "sourceLens": {
            "overallLevel": "limited",
            "overallLabelKo": SOURCE_LENS_LABELS_KO["limited"],
            "sources": [],
            "limitationKo": "통합신청서 항목 안내는 공식 서식 구조에 기반한 일반 안내이며, 시나리오별 정확한 필수 항목은 공식 서식과 관할기관에서 확인해야 합니다.",
        },
        "warnings": list(_HELPER_WARNINGS_KO),
        "finalAgencyNoteKo": FINAL_AGENCY_NOTE_KO,
    }


# ---------------------------------------------------------------------------
# Packet assembly
# ---------------------------------------------------------------------------
def _normalize_packet_type(procedure_key: str) -> Optional[str]:
    """Accept either a visa_data procedure key or a public packet type."""
    key = (procedure_key or "").strip()
    if key in PACKET_TYPE_BY_PROCEDURE_KEY:
        return PACKET_TYPE_BY_PROCEDURE_KEY[key]
    if key in SUPPORTED_PACKET_TYPES:
        return key
    # tolerant aliases
    alias = {"reentry": "reentry_permit", "statusgrant": "status_grant"}.get(key.lower())
    return alias


_FORM_HELPER_TYPE_BY_PACKET = {
    "foreigner_registration": "foreign_registration",
    "extension": "sojourn_extension",
    "status_change": "status_change",
    "workplace_change": "workplace_change",
    "activities_outside_status": "activity_outside_status",
    "reentry_permit": "reentry_permission",
    "address_report": "address_change",
}


def _decision_support(packet_type: str, status_code: str) -> Dict[str, Any]:
    """Facts and office questions that make a limited packet actionable.

    These are preparation prompts, never legal conclusions.  They stay useful
    even when a source-confirmed document list is unavailable.
    """
    code = status_code or "현재 체류자격"
    facts_by_type = {
        "workplace_change": [
            f"{code} 정확한 세부코드와 승인 직종",
            "기존 근로관계 종료일과 새 근무 시작 예정일",
            "새 사업장의 업종·실제 담당 직무",
            "새 근로계약의 임금·근무시간·계약기간",
        ],
        "extension": [
            "현재 체류기간 만료일",
            "직전 허가 이후 고용주·학교·주소 등 변경사항",
            "연장하려는 체류 목적이 계속되는 근거",
            "온라인 신청 또는 방문예약 가능 여부",
        ],
        "status_change": [
            f"현재 {code}와 변경하려는 목표 체류자격",
            "새 활동·고용·학교의 시작 예정일",
            "목표 체류자격의 핵심 요건을 보여 주는 자료",
            "국내 변경 가능 여부와 접수 시점",
        ],
        "foreigner_registration": [
            "입국일과 부여받은 체류기간",
            "현재 국내 체류지와 숙소 입증자료",
            "여권·사증·체류자격 부여 정보",
            "온라인 예약 또는 방문 접수 가능일",
        ],
        "reentry_permit": [
            "출국·재입국 예정일",
            "현재 체류기간 만료일",
            "단수·복수 재입국 필요 여부",
            "면제 대상 여부와 출국 전 신청 필요성",
        ],
    }
    questions_by_type = {
        "workplace_change": [
            "새 근무 시작 전에 허가가 필요한가요, 사후 신고가 가능한가요?",
            "이 세부코드·직종에서 새 사업장의 업종과 직무가 허용 범위에 맞나요?",
            "정확한 신고·허가 기한과 공식 제출서류는 무엇인가요?",
        ],
        "extension": [
            "언제부터 연장 신청이 가능하고 온라인 신청이 가능한가요?",
            "최근 변경사항 때문에 추가로 필요한 서류가 있나요?",
        ],
        "status_change": [
            "국내에서 이 목표 체류자격으로 변경할 수 있나요?",
            "변경 전 새 활동을 시작해도 되는지와 공식 서류 목록은 무엇인가요?",
        ],
        "foreigner_registration": [
            "등록 대상과 정확한 기산일·마감일은 언제인가요?",
            "현재 체류지 기준 관할기관과 예약 경로는 어디인가요?",
        ],
        "reentry_permit": [
            "재입국허가가 면제되는지, 출국 전에 별도 신청이 필요한가요?",
        ],
    }
    facts = facts_by_type.get(packet_type, [
        "현재 체류자격과 세부코드",
        "원하는 결과와 예정일",
        "직전 허가 이후 달라진 사실",
        "관할기관에 확인할 공식 제출서류",
    ])
    questions = questions_by_type.get(packet_type, [
        "이 절차의 접수 가능 시점과 공식 제출서류는 무엇인가요?",
        "온라인·방문 중 가능한 접수 경로와 관할기관은 어디인가요?",
    ])
    return {"titleKo": "판단 전에 정리할 정보", "factsKo": facts, "officialQuestionsKo": questions}


def _next_actions(packet_type: str, has_docs: bool) -> List[str]:
    actions: List[str] = []
    if packet_type == "workplace_change":
        return [
            "정확한 E-7 세부코드·승인 직종과 새 사업장의 업종·직무를 나란히 정리하세요.",
            "기존 회사 퇴사일과 새 회사 근무 시작 예정일을 확인하세요.",
            "새 근무를 시작하기 전에 1345 또는 관할 출입국기관에 허가·신고 유형을 확인하세요.",
            "확인된 유형에 맞춰 통합신청서와 공식 제출서류를 준비하세요.",
        ]
    if has_docs:
        actions.append("준비 서류 목록을 공식 기준에 맞춰 하나씩 확인·준비하세요.")
    else:
        actions.append("필요 서류는 1345/HiKorea/관할 출입국·외국인관서에서 공식 목록을 확인하세요.")
    actions.append("통합신청서(별지 제34호 서식) 작성 항목을 미리 확인하고, 개인정보는 공식 서식에 직접 작성하세요.")
    actions.append("HiKorea 예약 또는 관할 출입국·외국인관서 방문 가능 여부를 확인하세요.")
    actions.append("정확한 수수료·신청 시점·관할기관은 1345 또는 HiKorea에서 확인하세요.")
    return actions


def _risk_flags(packet_type: str) -> List[Dict[str, Any]]:
    """Conservative, universally-safe preparation risk reminders (not predictions)."""
    flags: List[Dict[str, Any]] = []
    if packet_type in ("extension", "foreigner_registration"):
        flags.append({
            "flagKo": "신청 시점 주의",
            "detailKo": "신청 시점을 놓치면 체류기간 초과 등 불이익이 생길 수 있으니 만료 전 신청 가능 시점을 확인하세요.",
            "severity": "reminder",
        })
    if packet_type == "workplace_change":
        flags.append({
            "flagKo": "신고 기한 주의",
            "detailKo": "근무처 변경·추가는 신고 기한이 정해져 있을 수 있으니 기한 내 신고 여부를 확인하세요.",
            "severity": "reminder",
        })
    return flags


def build_procedure_packet(
    status_code: str,
    procedure_key: str,
    scenario: Optional[Dict[str, Any]] = None,
    locale: str = "ko",
) -> Dict[str, Any]:
    """Build a deterministic, source-graded preparation packet.

    No LLM, no network, no personal data. Insufficient coverage yields a
    public-safe *limited* packet (clear ``limitationKo``), never fabricated
    documents/fees/deadlines and never raw developer diagnostics.
    """
    packet_type = _normalize_packet_type(procedure_key)
    exact_code = (status_code or "").strip().upper()
    parent = _parent_code(exact_code)
    title_ko, title_en = PACKET_TITLES.get(packet_type or "", ("절차 준비 패킷", "Procedure Packet"))

    if packet_type is None:
        return {
            "packetId": f"packet.{exact_code or 'unknown'}.unknown",
            "packetType": "unknown",
            "statusCode": exact_code,
            "exactStatusCode": exact_code,
            "parentStatusCode": parent,
            "titleKo": "지원하지 않는 절차",
            "titleEn": "Unsupported procedure",
            "applicability": {"summaryKo": "", "conditions": [], "limitations": ["요청한 절차 유형을 인식할 수 없습니다."]},
            "documents": {**_empty_doc_groups(), "sourceBacked": False, "limitationKo": "요청한 절차 유형을 인식할 수 없어 서류 안내를 제공할 수 없습니다."},
            "fees": {"items": [], "sourceBacked": False, "limitationKo": "수수료 정보를 제공할 수 없습니다."},
            "sourceLens": _source_lens("unavailable", []),
            "coverageSummary": _coverage_summary(
                overall_level="unavailable", doc_count=0, procedure_available=False
            ),
            "nextActions": ["1345 또는 HiKorea에서 해당 절차를 확인하세요."],
            "finalAgencyNoteKo": FINAL_AGENCY_NOTE_KO,
            "finalAgencyNoteEn": FINAL_AGENCY_NOTE_EN,
            "version": PROCEDURE_PACKET_VERSION,
        }

    record = _visa_record(exact_code)
    procedure_vd_key = PROCEDURE_KEY_BY_PACKET_TYPE.get(packet_type, "")
    procedure_obj = ((record or {}).get("procedures") or {}).get(procedure_vd_key) if record else None
    procedure_available = bool(isinstance(procedure_obj, dict) and procedure_obj.get("available"))

    # --- documents: prefer source-confirmed structured requirements ---------
    sr_type = _SR_PROCEDURE_TYPE_BY_PACKET.get(packet_type)
    sr_entries: List[Dict[str, Any]] = []
    if _sr is not None and sr_type:
        try:
            sr_entries = _sr.get_source_confirmed_structured_requirements(
                parent, {"procedureType": sr_type, "subCode": exact_code if exact_code != parent else None}
            )
            if not sr_entries:  # parent-level entries (subCode None) still apply
                sr_entries = _sr.get_source_confirmed_structured_requirements(parent, {"procedureType": sr_type})
        except Exception:  # pragma: no cover - defensive
            sr_entries = []

    doc_sources: List[Dict[str, Any]] = []
    doc_limitation = ""
    if sr_entries:
        doc_groups, doc_sources = _documents_from_sr_entries(sr_entries)
        documents_level = "source_confirmed"
        documents_source_backed = True
    else:
        doc_groups = _empty_doc_groups()
        documents_level = "unavailable"
        documents_source_backed = False
        if procedure_available and isinstance(procedure_obj.get("requiredDocs"), dict):
            visa_sources = _manual_source_from_visa_refs(procedure_obj.get("manualRefs"))
            doc_groups = _documents_from_visa_groups(procedure_obj["requiredDocs"], visa_sources)
            if _doc_count(doc_groups) > 0:
                doc_sources = visa_sources
                documents_level = "contextual"
                doc_limitation = (
                    "아래 서류는 공식 매뉴얼에서 보수적으로 추출한 안내이며 세부약호·국적·기관·체류 이력별 "
                    "예외가 있어 관할기관 확인이 필요합니다."
                )
            else:
                documents_level = "limited"
                doc_limitation = "이 절차의 공식 서류 목록이 아직 구조화되지 않았습니다. 1345/HiKorea/관할기관에서 확인하세요."
        elif procedure_available:
            documents_level = "limited"
            doc_limitation = "이 절차의 공식 서류 목록이 아직 구조화되지 않았습니다. 1345/HiKorea/관할기관에서 확인하세요."
        else:
            documents_level = "unavailable"
            doc_limitation = "이 체류자격에서는 해당 절차 안내가 확인되지 않습니다. 1345/HiKorea/관할기관에서 확인하세요."

    has_official_form = any(
        d.get("isOfficialForm")
        for grp in doc_groups.values() for d in grp
    )

    documents_block: Dict[str, Any] = {
        "commonDocs": doc_groups["commonDocs"],
        "requiredDocs": doc_groups["requiredDocs"],
        "conditionalDocs": doc_groups["conditionalDocs"],
        "additionalDocs": doc_groups["additionalDocs"],
        "sourceBacked": documents_source_backed,
    }
    if doc_limitation:
        documents_block["limitationKo"] = doc_limitation

    # --- applicability ------------------------------------------------------
    summary_ko = ""
    if isinstance(procedure_obj, dict) and procedure_obj.get("summary"):
        summary_ko = str(procedure_obj.get("summary"))
    applicability = {
        "summaryKo": summary_ko or f"{title_ko} 절차 준비 안내입니다.",
        "conditions": [],
        "limitations": ([] if procedure_available else ["이 체류자격에서 해당 절차의 적용 여부가 공식근거로 확인되지 않았습니다."]),
    }

    # --- timing (conservative; no source-confirmed deadlines in data) -------
    timing = {
        "sourceBacked": False,
        "limitationKo": "정확한 신청 가능 시점·기한은 공식근거로 확정 표시할 수 없습니다. 1345/HiKorea/관할기관에서 확인하세요.",
    }
    if packet_type == "extension":
        timing["triggerEventKo"] = "체류기간 만료 전"
    if isinstance(record, dict) and record.get("period"):
        timing["stayPeriodHintKo"] = str(record.get("period"))

    # --- fees ---------------------------------------------------------------
    fees = _build_fees(record, packet_type)

    # --- channels -----------------------------------------------------------
    channels: Dict[str, Any] = {
        "immigrationOfficeVisit": {"availableKo": "관할 출입국·외국인관서 방문", "sourceBacked": False},
        "limitationKo": "예약 필요 여부·온라인 신청 가능 여부는 HiKorea/1345/관할기관에서 확인하세요.",
    }
    if isinstance(record, dict) and record.get("hikorea_task_type"):
        channels["hikoreaReservation"] = {
            "taskTypeKo": str(record.get("hikorea_task_type")),
            "noteKo": "HiKorea 전자민원 또는 방문예약 가능 여부를 확인하세요.",
            "sourceBacked": False,
        }

    # --- source lens (overall = best evidence level reached) ----------------
    all_sources = list(doc_sources)
    overall = documents_level if documents_level in SOURCE_LENS_LEVELS else "limited"
    source_lens = _source_lens(overall, all_sources, limitation_ko=(
        None if overall in ("source_confirmed", "contextual")
        else "이 절차의 공식근거 연결이 제한적입니다. 최종 기준은 관할기관 안내를 따르세요."
    ))

    # --- application typing helper (typing-guide only) ----------------------
    helper = build_application_typing_helper(
        packet_type, status_code=exact_code, has_official_form_document=has_official_form, locale=locale,
    )

    packet_id = f"packet.{exact_code}.{packet_type}"
    return {
        "packetId": packet_id,
        "packetType": packet_type,
        "statusCode": exact_code,
        "exactStatusCode": exact_code,
        "parentStatusCode": parent,
        "titleKo": title_ko,
        "titleEn": title_en,
        "userScenarioSummaryKo": summary_ko,
        "applicability": applicability,
        "timing": timing,
        "documents": documents_block,
        "fees": fees,
        "channels": channels,
        "officeAndJurisdiction": {
            "summaryKo": "관할 출입국·외국인관서(체류지 기준)에서 처리됩니다.",
            "limitationKo": "정확한 관할 기관은 체류지에 따라 다르므로 HiKorea/1345에서 확인하세요.",
        },
        "riskFlags": _risk_flags(packet_type),
        "sourceLens": source_lens,
        "coverageSummary": _coverage_summary(
            overall_level=overall,
            doc_count=_doc_count(doc_groups),
            procedure_available=procedure_available,
        ),
        "applicationTypingHelper": helper,
        "nextActions": _next_actions(packet_type, _doc_count(doc_groups) > 0),
        "decisionSupport": _decision_support(packet_type, exact_code),
        "formHelper": {
            "formId": "F01",
            "type": _FORM_HELPER_TYPE_BY_PACKET.get(packet_type, ""),
        } if packet_type in _FORM_HELPER_TYPE_BY_PACKET else None,
        "finalAgencyNoteKo": FINAL_AGENCY_NOTE_KO,
        "finalAgencyNoteEn": FINAL_AGENCY_NOTE_EN,
        "version": PROCEDURE_PACKET_VERSION,
    }


def _source_lens(overall_level: str, sources: List[Dict[str, Any]], *, limitation_ko: Optional[str] = None) -> Dict[str, Any]:
    level = overall_level if overall_level in SOURCE_LENS_LEVELS else "limited"
    lens: Dict[str, Any] = {
        "overallLevel": level,
        "overallLabelKo": SOURCE_LENS_LABELS_KO[level],
        "overallLabelEn": SOURCE_LENS_LABELS_EN[level],
        "sources": list(sources or []),
        # Every packet carries the final-agency caveat as part of the lens.
        "finalAgencyDiscretionKo": SOURCE_LENS_LABELS_KO["final_agency_discretion"],
        "finalAgencyDiscretionEn": SOURCE_LENS_LABELS_EN["final_agency_discretion"],
    }
    if limitation_ko:
        lens["limitationKo"] = limitation_ko
    return lens


def _coverage_summary(
    *, overall_level: str, doc_count: int, procedure_available: bool
) -> Dict[str, Any]:
    """Deterministic, public-safe coverage signal for the navigator.

    ``isLimited`` is the single source of truth the front-end uses to choose
    between a full Action Packet and a coverage-limited packet. It is True
    whenever the source lens is not source-grounded/contextual OR no documents
    were surfaced — so the UI can never render an empty packet as if complete.
    """
    level = _COVERAGE_LEVEL_BY_LENS.get(overall_level, "limited")
    has_docs = doc_count > 0
    is_limited = level in ("limited", "unavailable") or not has_docs
    return {
        "level": level,
        "isLimited": is_limited,
        "hasDocuments": has_docs,
        "procedureAvailable": bool(procedure_available),
    }


def build_available_packets_for_status(status_code: str, locale: str = "ko") -> List[Dict[str, Any]]:
    """Summaries of packets buildable for a status (procedures present in data)."""
    record = _visa_record(status_code)
    if not record:
        return []
    procedures = record.get("procedures") or {}
    summaries: List[Dict[str, Any]] = []
    for vd_key, packet_type in PACKET_TYPE_BY_PROCEDURE_KEY.items():
        proc = procedures.get(vd_key)
        if not isinstance(proc, dict) or not proc.get("available"):
            continue
        if packet_type not in SUPPORTED_PACKET_TYPES:
            continue
        packet = build_procedure_packet(status_code, packet_type, locale=locale)
        summaries.append({
            "packetType": packet_type,
            "procedureKey": vd_key,
            "titleKo": packet["titleKo"],
            "titleEn": packet.get("titleEn", ""),
            "sourceLensLevel": packet["sourceLens"]["overallLevel"],
            "sourceLensLabelKo": packet["sourceLens"]["overallLabelKo"],
            "sourceLensLabelEn": packet["sourceLens"].get("overallLabelEn", ""),
            "coverageLevel": packet.get("coverageSummary", {}).get("level", "limited"),
            "isLimited": packet.get("coverageSummary", {}).get("isLimited", True),
            "documentGroupCounts": {
                k: len(packet["documents"][k])
                for k in ("commonDocs", "requiredDocs", "conditionalDocs", "additionalDocs")
            },
            "hasApplicationTypingHelper": "applicationTypingHelper" in packet,
        })
    return summaries
