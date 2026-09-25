"""Structured, source-grounded answers for simple document questions.

Why this module exists
----------------------
A question such as "D-2 연장시 필수 서류" is a deterministic lookup: the
official stay manual already lists the documents, and Paradiso has that list
in its manual-grounding data. Handing the whole manual excerpt to a language
model and rendering its free-form Markdown back to the user produced
unreadable answers (raw ``###`` headings, repeated disclaimers, internal
source-file metadata in the prose) and let the model decide which documents
were "required".

This module keeps the facts on the data side of the line:

    official grounding data
      -> ``build_document_answer``  (deterministic buckets, no model)
      -> optional model summary     (``extract_summary`` keeps prose only)
      -> ``compose_plain_text``     (clean copy/fallback text)
      -> structured UI renderer     (ai.html ``pa-answer-card-shell``)

The model may phrase a short summary. It never adds, removes or re-buckets a
document: bucket membership is decided here from the canonical data only.

The object follows ``docs/ai/ANSWER_QUALITY_CONTRACT.md`` §3 field names
(``short_answer``, ``required_documents`` with ``common`` / ``required`` /
``conditional`` / ``additional`` / ``missing_or_unverified`` buckets,
``source_summary``, ``uncertainty_flags``, ``user_next_actions``,
``disclaimer_snippet``) so there is one answer contract, not a second one.

It never reads provider/model state and never emits internal source metadata
(file paths, revision dates, hashes, parser notes).
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

STRUCTURED_ANSWER_VERSION = "2026-09-structured-document-answer-v1"
KIND_DOCUMENTS = "documents"

# ---------------------------------------------------------------------------
# Internal-metadata leak guard
# ---------------------------------------------------------------------------
# Phrases that describe Paradiso's grounding machinery rather than the answer.
# They must never reach public answer prose. Used both to scrub model output
# and as the invariant the regression tests assert.
INTERNAL_METADATA_PATTERNS: Sequence[str] = (
    r"source[\s_-]*file",
    r"source_revision_date",
    r"source[\s_-]*revision",
    r"grounding[\s_-]*packet",
    r"grounding[\s_-]*fixture",
    r"\bfixture\b",
    r"internal[\s_-]*source",
    r"parser[\s_-]*status",
    r"source_file_sha256",
    r"\.pdf\b",
)
_INTERNAL_METADATA_RE = re.compile("|".join(INTERNAL_METADATA_PATTERNS), re.IGNORECASE)

# "(2026.6; source file 2026-06-23)" -> "(2026.6)" and similar trailers.
_SOURCE_FILE_TRAILER_RE = re.compile(
    r"\s*[;,·]\s*source[\s_-]*file\s*[:：]?\s*[\w./-]*", re.IGNORECASE
)


def contains_internal_metadata(text: Optional[str]) -> bool:
    """True when ``text`` mentions internal grounding/source metadata."""
    return bool(_INTERNAL_METADATA_RE.search(text or ""))


def scrub_internal_metadata(text: Optional[str]) -> str:
    """Remove internal source metadata from public answer prose.

    Conservative: strips the known ``; source file <date>`` trailer in place,
    then drops any remaining *line* that still names internal machinery. The
    rest of the answer is untouched.
    """
    if not text:
        return text or ""
    cleaned = _SOURCE_FILE_TRAILER_RE.sub("", text)
    if not contains_internal_metadata(cleaned):
        return cleaned
    kept = [line for line in cleaned.split("\n") if not contains_internal_metadata(line)]
    return "\n".join(kept).strip()


# ---------------------------------------------------------------------------
# Public source label
# ---------------------------------------------------------------------------
def public_source(grounding: Dict[str, Any], bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Public, user-facing citation fields only.

    Internal revision metadata (source file path, revision date, sha256,
    extraction notes) stays server-side.
    """
    return {
        "title": str(bundle.get("source_title") or "외국인체류 안내매뉴얼"),
        "edition": str(bundle.get("source_date") or ""),
        "issuing_body": str(bundle.get("issuing_body") or ""),
        "section": str(grounding.get("section") or ""),
        "procedure": str(grounding.get("procedure_type") or ""),
        "page_range": str(grounding.get("page_range") or ""),
        "visa_code": str(grounding.get("visa_code") or ""),
        "verified": str(grounding.get("source_verification_status") or "") == "verified_locally",
        # Sub-code scope of this list (e.g. "어학연수생(D-4-1, D-4-7)"). Always
        # rendered so a sub-code-scoped list is never read as parent-wide.
        "scope": _subcode_scope(str(grounding.get("section") or "")),
    }


def _subcode_scope(section: str) -> str:
    _, sep, tail = section.partition("—")
    if not sep:
        return ""
    tail = re.sub(r"^\s*\d+[.)]\s*", "", tail).strip()
    tail = re.sub(r"에\s*대한\s*.*$", "", tail).strip()
    return tail if re.search(r"[A-Z]-\d+-\w", tail) else ""


def public_source_citation(source: Dict[str, Any]) -> str:
    """"외국인체류 안내매뉴얼 2026.6, 법무부 출입국·외국인정책본부, pp. 43-44"."""
    head = " ".join(p for p in (source.get("title"), source.get("edition")) if p)
    parts = [head, source.get("issuing_body") or ""]
    if source.get("page_range"):
        parts.append(f"pp. {source['page_range']}")
    return ", ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Question eligibility
# ---------------------------------------------------------------------------
# Issue types that make a question more than a checklist lookup. Mirrors the
# Fast->Basic minimum set in model_policy so both layers agree on "complex".
_COMPLEX_ISSUES = frozenset({
    "denial_revocation_or_remedy",
    "constitutional_or_fundamental_rights",
    "discretionary_or_ambiguous_interpretation",
    "overstay_or_risk",
    "nationality_or_refugee_context",
    "workplace_change_addition",
    "status_change",
    "outside_status_activity",
    "work_on_non_work_status",
    "employment_restriction",
    "approval_condition",
    "post_status_change_residual_duty",
    "study_on_non_study_status",
    "activity_scope",
})


def is_document_lookup(
    *,
    legal_issue_types: Iterable[str],
    contract_key: str,
    has_documents: bool,
) -> bool:
    """A plain "which documents?" question with a source-confirmed list.

    Deliberately narrow: an explicit ``documents_needed`` issue, the
    documents answer-shape contract, a non-empty canonical list, and no
    complex legal issue riding along. Anything broader keeps the free-form
    answer so no model content is dropped.
    """
    issues = {str(v or "").strip() for v in (legal_issue_types or []) if str(v or "").strip()}
    return bool(
        has_documents
        and contract_key == "documents_needed"
        and "documents_needed" in issues
        and not (issues & _COMPLEX_ISSUES)
    )


# ---------------------------------------------------------------------------
# Document bucketing (deterministic)
# ---------------------------------------------------------------------------
# The standard application set every stay procedure starts from. Grouping
# these under "기본 서류" is a presentation of the manual's own first line
# ("신청서, 여권, 외국인등록증, 수수료"), not a new requirement.
_BASE_DOCUMENTS = frozenset({
    "신청서", "통합신청서", "통합신청서(신고서)", "여권", "외국인등록증", "수수료", "사진",
})
_CONDITIONAL_MARKER_RE = re.compile(
    r"\(\s*해당자\s*\)|해당자에\s*한|해당하는\s*경우|해당\s*시|필요\s*시|경우에\s*한"
    r"|에\s*한(?:해|하여|함)",
)
_TRAILING_APPLICANT_RE = re.compile(r"\s*\(\s*해당자\s*\)\s*$")
_EXAMPLES_RE = re.compile(r"^(?P<label>.*?)\s*\(\s*예\s*[:：]\s*(?P<examples>[^)]*)\)\s*$")


def _split_document(text: str) -> Dict[str, str]:
    raw = " ".join(str(text or "").split())
    label = _TRAILING_APPLICANT_RE.sub("", raw).strip()
    examples = ""
    m = _EXAMPLES_RE.match(label)
    if m:
        label = m.group("label").strip()
        examples = m.group("examples").strip()
    return {"label": label, "examples": examples, "source_text": raw}


def bucket_documents(documents: Sequence[Any]) -> Dict[str, List[Dict[str, str]]]:
    """Bucket canonical document entries without changing membership.

    Each entry is a string (manual grounding) or a structured-requirement
    dict (``textKo`` / ``requiredness`` / ``conditionKo``). Every input entry
    lands in exactly one bucket; nothing is added or dropped.
    """
    buckets: Dict[str, List[Dict[str, str]]] = {
        "common": [], "required": [], "conditional": [], "additional": [], "missing_or_unverified": [],
    }
    for entry in documents or []:
        if isinstance(entry, dict):
            text = entry.get("textKo") or entry.get("text") or entry.get("label") or ""
            requiredness = str(entry.get("requiredness") or "required").lower()
            condition = str(entry.get("conditionKo") or "").strip()
        else:
            text, requiredness, condition = str(entry or ""), "required", ""
        if not str(text).strip():
            continue
        item = _split_document(text)
        if condition:
            item["condition"] = condition
        if requiredness in {"optional", "additional", "may_request"}:
            buckets["additional"].append(item)
        elif requiredness == "conditional" or _CONDITIONAL_MARKER_RE.search(item["source_text"]):
            buckets["conditional"].append(item)
        elif item["label"].split(" (", 1)[0].strip() in _BASE_DOCUMENTS:
            buckets["common"].append(item)
        else:
            buckets["required"].append(item)
    return buckets


def document_count(buckets: Dict[str, List[Dict[str, str]]]) -> int:
    return sum(len(v) for v in buckets.values())


# ---------------------------------------------------------------------------
# Localized deterministic copy
# ---------------------------------------------------------------------------
def _norm_lang(lang: Optional[str]) -> str:
    low = str(lang or "").strip().lower()
    if low.startswith("en"):
        return "en"
    if low in {"zh-tw", "zh-hant", "zh-hk", "zh-mo"}:
        return "zhHant"
    if low.startswith("zh"):
        return "zh"
    return "ko"


_PROCEDURE_EN = {
    "체류기간 연장허가": "extension of stay",
    "외국인등록": "alien registration",
    "체류자격 변경허가": "change of status",
    "extension": "extension of stay",
    "registration": "alien registration",
}
_PROCEDURE_ZH = {
    "체류기간 연장허가": ("延长居留期限", "延長居留期限"),
    "외국인등록": ("外国人登记", "外國人登記"),
    "체류자격 변경허가": ("变更居留资格", "變更居留資格"),
    "extension": ("延长居留期限", "延長居留期限"),
    "registration": ("外国人登记", "外國人登記"),
}
_PROCEDURE_KO = {"extension": "체류기간 연장허가", "registration": "외국인등록"}


def topic_label(source: Dict[str, Any], lang: Optional[str]) -> str:
    code = source.get("visa_code") or ""
    procedure = source.get("procedure") or ""
    norm = _norm_lang(lang)
    if norm == "en":
        return " ".join(p for p in (code, _PROCEDURE_EN.get(procedure, procedure)) if p)
    if norm in {"zh", "zhHant"}:
        pair = _PROCEDURE_ZH.get(procedure)
        name = (pair[1] if norm == "zhHant" else pair[0]) if pair else procedure
        return " ".join(p for p in (code, name) if p)
    section = source.get("section") or code
    # Manual section headings can carry a numbered sub-heading
    # ("특정활동(E-7) — 1. 제출 서류 및 확인사항"). Keep a sub-heading only when
    # it scopes the list to sub-codes (e.g. "어학연수생(D-4-1, D-4-7)"), which
    # the user must see; drop numbering and generic sub-headings.
    head, sep, tail = section.partition("—")
    if sep:
        tail = re.sub(r"^\s*\d+[.)]\s*", "", tail).strip()
        section = f"{head.strip()} — {tail}" if re.search(r"[A-Z]-\d+-\w", tail) else head.strip()
    procedure_ko = _PROCEDURE_KO.get(procedure, procedure)
    if procedure_ko and procedure_ko in section:
        return section
    return " ".join(p for p in (section, procedure_ko) if p)


def deterministic_short_answer(source: Dict[str, Any], buckets: Dict[str, list], lang: Optional[str]) -> str:
    """Counts-only summary built from the buckets (no model, no new facts)."""
    base = len(buckets.get("common") or [])
    support = len(buckets.get("required") or [])
    cond = len(buckets.get("conditional") or [])
    extra = len(buckets.get("additional") or [])
    topic = topic_label(source, lang)
    norm = _norm_lang(lang)
    if norm == "en":
        parts = []
        if base:
            parts.append(f"{base} basic document{'s' if base != 1 else ''}")
        if support:
            parts.append(f"{support} supporting document{'s' if support != 1 else ''}")
        head = f"For {topic}, the official manual lists " + (" and ".join(parts) or "the documents below") + "."
        if cond:
            head += f" {cond} more appl{'y' if cond != 1 else 'ies'} only if relevant to you."
        if extra:
            head += " The office may request additional documents."
        return head
    if norm in {"zh", "zhHant"}:
        trad = norm == "zhHant"
        parts = []
        if base:
            parts.append(f"{base} 项基本材料" if not trad else f"{base} 項基本材料")
        if support:
            parts.append(f"{support} 项证明材料" if not trad else f"{support} 項證明材料")
        joiner = "、"
        if trad:
            head = f"{topic}：官方手冊列出 " + (joiner.join(parts) or "以下材料") + "。"
            if cond:
                head += f"符合條件者另需 {cond} 項。"
        else:
            head = f"{topic}：官方手册列出 " + (joiner.join(parts) or "以下材料") + "。"
            if cond:
                head += f"符合条件者另需 {cond} 项。"
        return head
    parts = []
    if base:
        parts.append(f"기본 서류 {base}종")
    if support:
        parts.append(f"증빙 서류 {support}종")
    head = f"{topic}에는 " + ("과 ".join(parts) if parts else "아래 서류") + "이 필요합니다."
    if len(parts) == 2:
        head = f"{topic}에는 기본 서류 {base}종과 증빙 서류 {support}종이 필요합니다."
    if cond:
        head += f" 해당하는 경우 {cond}종을 추가로 제출합니다."
    return head


_NEXT_ACTIONS = {
    "ko": [
        "관할 출입국·외국인관서 또는 하이코리아에서 체류기간 만료 전 신청 일정을 확인하세요.",
        "개별 사안에 따라 추가 서류가 요구될 수 있으니 방문 전 1345에 문의하세요.",
    ],
    "en": [
        "Check the filing schedule with the competent immigration office or HiKorea before your stay expires.",
        "Offices may ask for more documents in individual cases, so confirm with 1345 before you visit.",
    ],
    "zh": [
        "请在居留期限届满前，通过管辖出入境·外国人机关或 HiKorea 确认申请日程。",
        "个别情况可能需要补充材料，前往前请向 1345 确认。",
    ],
    "zhHant": [
        "請在居留期限屆滿前，透過管轄出入境·外國人機關或 HiKorea 確認申請日程。",
        "個別情況可能需要補充材料，前往前請向 1345 確認。",
    ],
}
_DISCLAIMER = {
    "ko": "참고용 안내입니다. 최종 허가 여부와 제출서류는 관할 출입국·외국인관서의 판단에 따릅니다.",
    "en": "Reference information only. Final approval and document requirements are decided by the competent immigration office.",
    "zh": "仅供参考。最终许可与所需材料以管辖出入境·外国人机关的判断为准。",
    "zhHant": "僅供參考。最終許可與所需材料以管轄出入境·外國人機關的判斷為準。",
}
_UNCERTAINTY = {
    "ko": "관할 기관은 개별 사안에 따라 서류를 추가로 요구하거나 일부를 면제할 수 있습니다.",
    "en": "The competent office may request additional documents or waive some in individual cases.",
    "zh": "管辖机关可根据个别情况要求补充材料或免除部分材料。",
    "zhHant": "管轄機關可根據個別情況要求補充材料或免除部分材料。",
}


def _classify_caveats(caveats: Sequence[str]) -> Dict[str, Any]:
    """Split manual caveats into provenance / determination / practical notes.

    Every caveat is kept in exactly one place, so nothing is removed:
    provenance ("본 목록은 … 옮긴 것입니다") belongs with the source card,
    the final-determination sentence is the card disclaimer, and the rest are
    user-facing notes.
    """
    provenance: List[str] = []
    determination: List[str] = []
    notes: List[str] = []
    for raw in caveats or []:
        text = " ".join(str(raw or "").split())
        if not text:
            continue
        if text.startswith("본 목록은"):
            provenance.append(text)
        elif "최종" in text and ("판단" in text or "허가" in text):
            determination.append(text)
        else:
            notes.append(text)
    return {"provenance": provenance, "determination": determination, "notes": notes}


def build_document_answer(
    *,
    grounding: Dict[str, Any],
    bundle: Dict[str, Any],
    lang: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Structured answer for a source-confirmed document list.

    ``grounding`` is a manual-grounding entry (``required_documents``,
    ``caveats``, ``section``, ``procedure_type``, ``page_range``) and
    ``bundle`` its manual header. Returns ``None`` when there is no list.
    """
    # Knowledge-backed groundings also carry structured entries (text +
    # requirement level + condition); prefer them so a reviewed "conditional"
    # fact can never be re-bucketed as universal from its bare wording.
    documents = list((grounding or {}).get("required_document_entries")
                     or (grounding or {}).get("required_documents") or [])
    if not documents:
        return None
    buckets = bucket_documents(documents)
    if not document_count(buckets):
        return None
    source = public_source(grounding, bundle or {})
    norm = _norm_lang(lang)
    caveats = _classify_caveats(grounding.get("caveats") or [])
    # The office-discretion sentence is shown once, as the uncertainty flag;
    # drop the same sentence from notes rather than repeating it.
    notes = [n for n in caveats["notes"] if not ("추가" in n and "면제" in n)]
    office_discretion = [n for n in caveats["notes"] if "추가" in n and "면제" in n]
    disclaimer = caveats["determination"][0] if (caveats["determination"] and norm == "ko") else _DISCLAIMER[norm]
    uncertainty = office_discretion[0] if (office_discretion and norm == "ko") else _UNCERTAINTY[norm]
    return {
        "version": STRUCTURED_ANSWER_VERSION,
        "kind": KIND_DOCUMENTS,
        "answer_type": "required_documents",
        "locale": norm,
        "visa_code_or_topic": source["visa_code"],
        "interpreted_intent": topic_label(source, lang),
        "short_answer": deterministic_short_answer(source, buckets, lang),
        "short_answer_source": "deterministic",
        "required_documents": buckets,
        # Notes and caveats are manual text; they stay in Korean (official
        # wording) and the renderer marks them lang="ko".
        "important_notes": notes,
        "notes_locale": "ko",
        "source": source,
        "source_summary": public_source_citation(source),
        "source_notes": caveats["provenance"],
        "uncertainty_flags": [uncertainty],
        "user_next_actions": list(_NEXT_ACTIONS[norm]),
        "disclaimer_snippet": disclaimer,
    }


# ---------------------------------------------------------------------------
# Model summary extraction + plain-text composition
# ---------------------------------------------------------------------------
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
_LIST_RE = re.compile(r"^\s*(?:[-*•·]|\d+[.)])\s+")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_MAX_SUMMARY_CHARS = 360
_LEAD_LABEL_RE = re.compile(r"^\s*(?:요약|핵심|답변|Summary|Short answer|Answer|摘要|简答|簡答)\s*[:：]\s*", re.IGNORECASE)
# "(외국인체류 안내매뉴얼 2026.6, pp. 43-44)" style in-prose citations. The
# source card already shows the citation, so the summary does not repeat it.
_INLINE_CITATION_RE = re.compile(
    r"\s*[\(（][^()（）]*(?:안내매뉴얼|매뉴얼|Manual|manual|手册|手冊|pp\.)[^()（）]*[\)）]"
)


def extract_summary(text: Optional[str], *, max_chars: int = _MAX_SUMMARY_CHARS) -> str:
    """Keep only the model's lead prose (no headings, no lists, no metadata).

    Lists come from the canonical buckets, so any model-written list — even a
    correct one — is discarded here rather than risk a re-bucketed or
    invented document reaching the user.
    """
    if not text:
        return ""
    prose: List[str] = []
    for block in re.split(r"\n\s*\n", scrub_internal_metadata(text).replace("\r\n", "\n")):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        if any(_HEADING_RE.match(ln) or _LIST_RE.match(ln) for ln in lines):
            if prose:
                break
            continue
        joined = " ".join(lines)
        joined = _BOLD_RE.sub(lambda m: m.group(1) or m.group(2) or "", joined)
        joined = _INLINE_CITATION_RE.sub("", joined)
        joined = _LEAD_LABEL_RE.sub("", joined).strip()
        if joined.endswith(":") or joined.endswith("："):
            continue
        prose.append(joined)
        if sum(len(p) for p in prose) >= max_chars // 2:
            break
    summary = " ".join(prose).strip()
    if len(summary) > max_chars:
        cut = summary[:max_chars]
        stop = max(cut.rfind(". "), cut.rfind("다. "), cut.rfind("。"), cut.rfind("요. "))
        summary = (cut[: stop + 1] if stop > max_chars // 3 else cut.rstrip() + "…").strip()
    return summary


_SECTION_TITLES = {
    "common": {"ko": "기본 서류", "en": "Basic documents", "zh": "基本材料", "zhHant": "基本材料"},
    "required": {"ko": "증빙 서류", "en": "Supporting documents", "zh": "证明材料", "zhHant": "證明材料"},
    "conditional": {"ko": "해당하는 경우 제출", "en": "Only if it applies to you", "zh": "符合条件时提交", "zhHant": "符合條件時提交"},
    "additional": {"ko": "추가로 요청될 수 있는 서류", "en": "May be requested", "zh": "可能要求的材料", "zhHant": "可能要求的材料"},
    "missing_or_unverified": {"ko": "확인이 필요한 서류", "en": "Needs confirmation", "zh": "需确认的材料", "zhHant": "需確認的材料"},
    "notes": {"ko": "유의사항", "en": "Notes", "zh": "注意事项", "zhHant": "注意事項"},
    "source": {"ko": "출처", "en": "Source", "zh": "出处", "zhHant": "出處"},
}
BUCKET_ORDER = ("common", "required", "conditional", "additional", "missing_or_unverified")


def compose_plain_text(structured: Dict[str, Any], lang: Optional[str]) -> str:
    """Readable plain text (copy / non-structured clients). No Markdown."""
    norm = _norm_lang(lang)
    out: List[str] = []
    topic = structured.get("interpreted_intent") or ""
    if topic:
        out.append(topic)
        out.append("")
    if structured.get("short_answer"):
        out.append(structured["short_answer"])
        out.append("")
    docs = structured.get("required_documents") or {}
    for key in BUCKET_ORDER:
        items = docs.get(key) or []
        if not items:
            continue
        out.append(_SECTION_TITLES[key][norm])
        for item in items:
            line = f"• {item.get('label') or item.get('source_text')}"
            if item.get("examples"):
                line += f" (예: {item['examples']})"
            if item.get("condition"):
                line += f" — {item['condition']}"
            out.append(line)
        out.append("")
    notes = list(structured.get("important_notes") or []) + list(structured.get("uncertainty_flags") or [])
    if notes:
        out.append(_SECTION_TITLES["notes"][norm])
        out.extend(f"• {n}" for n in notes)
        out.append("")
    if structured.get("source_summary"):
        out.append(_SECTION_TITLES["source"][norm])
        out.append(structured["source_summary"])
    return "\n".join(out).strip()


def apply_model_summary(structured: Dict[str, Any], model_text: Optional[str]) -> Dict[str, Any]:
    """Return a copy whose short answer is the model's lead prose, if usable."""
    summary = extract_summary(model_text)
    result = dict(structured)
    if summary and not contains_internal_metadata(summary):
        result["short_answer"] = summary
        result["short_answer_source"] = "model_summary"
    return result
