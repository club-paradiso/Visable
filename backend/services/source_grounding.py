"""Generalized source-grounding helpers for Paradiso AI.

This module sits above the existing manual/law adapters and produces two
separate views from the same source attempts:

* an internal normalized source-attempt model, stable across JSON/XML/HTML/text
  parser outcomes and law/manual families; and
* public-safe projections and LLM grounding context that hide raw diagnostics.

It is intentionally keyed by procedure/action/issue dimensions, not individual
visa codes.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .legal_analysis import (
    classify_activity_types,
    classify_legal_issue_types,
    extract_immigration_facts,
)


NORMALIZATION_VERSION = "2026-06-generalized-source-grounding-v1"

PUBLIC_LABELS_KO = {
    "manual_available": "공식 매뉴얼 확인됨",
    "law_available": "실시간 법령 확인됨",
    "law_temporarily_unavailable": "실시간 법령 일시 확인 불가",
    "stored_official": "저장된 공식 출처 기준 답변",
    "limited": "출처 제한으로 일반 안내만 가능",
    "confirmation_needed": "관할기관 최종 확인 필요",
}

PUBLIC_LABELS_EN = {
    "manual_available": "Official manual checked",
    "law_available": "Live law checked",
    "law_temporarily_unavailable": "Live law temporarily unavailable",
    "stored_official": "Stored official source used",
    "limited": "Only limited general guidance available",
    "confirmation_needed": "Final confirmation needed from the authority",
}

_SOURCE_STATUS_TO_PUBLIC = {
    "available": "available",
    "temporarily_unavailable": "temporarily_unavailable",
    "not_configured": "unavailable",
    "not_relevant": "unavailable",
    "error": "temporarily_unavailable",
}

_INTERNAL_STATUS_MAP = {
    "ok": "available",
    "used": "available",
    "present": "available",
    "results_found": "available",
    "verified": "available",
    "source_file_compared": "available",
    "attempted": "temporarily_unavailable",
    "unavailable": "temporarily_unavailable",
    "no_results": "temporarily_unavailable",
    "timeout": "temporarily_unavailable",
    "http_error": "error",
    "bad_response": "error",
    "parse_error": "error",
    "official_error": "error",
    "disabled": "not_configured",
    "not_configured": "not_configured",
    "unsupported": "not_configured",
    "planned_not_wired": "not_configured",
    "not_attempted": "not_relevant",
    "not_relevant": "not_relevant",
}

_PROCEDURE_BY_ISSUE = (
    ("documents_needed", "document_requirement_inquiry"),
    ("status_change", "change_of_status"),
    ("extension", "extension_of_stay"),
    ("outside_status_activity", "activities_outside_status"),
    ("activity_scope", "employment_work_activity_inquiry"),
    ("workplace_change_addition", "workplace_change_addition"),
    ("registration_or_residence_report", "foreigner_registration"),
    ("reporting_duty", "registration_information_change"),
    ("reentry", "re_entry_permit"),
    ("overstay_or_risk", "overstay_violation_risk_inquiry"),
    ("nationality_or_refugee_context", "general_eligibility_inquiry"),
)

_ACTION_ALIASES = {
    "paid_work": "paid_work",
    "freelance_work": "freelancing",
    "business_activity": "business_operation",
    "workplace_change": "job_change",
    "workplace_addition": "job_change",
    "additional_employment": "job_change",
    "credit_bearing_study": "study",
    "formal_enrollment": "study",
    "language_training": "study",
    "document_preparation": "document_submission",
    "status_extension": "renewal",
    "reentry_or_departure": "departure_reentry",
    "refugee_or_humanitarian_context": "appeal_exception",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _compact_text(value: Any, *, limit: int = 700) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _normalize_status(raw_status: str) -> str:
    return _INTERNAL_STATUS_MAP.get(str(raw_status or "").strip().lower(), "error")


def _public_status(status: str) -> str:
    return _SOURCE_STATUS_TO_PUBLIC.get(status, "unavailable")


def _snippet(text: str, *, citation: str = "", article: str = "", section: str = "",
             page: str = "", source_name: str = "", url: str = "") -> Optional[Dict[str, str]]:
    clean = _compact_text(text, limit=700)
    if not clean:
        return None
    out = {"text": clean}
    for key, value in (
        ("citation", citation),
        ("article", article),
        ("section", section),
        ("page", page),
        ("sourceName", source_name),
        ("url", url),
    ):
        if value:
            out[key] = str(value)
    return out


def _family_from_source(source: Dict[str, Any], fallback: str = "") -> str:
    raw = str(source.get("source_family") or source.get("source_type") or source.get("target") or fallback or "").lower()
    if raw in {"law", "statute"}:
        return "statute"
    if raw in {"admin_rule", "admrul"}:
        return "administrative_rule"
    if raw in {"law_term", "lstrm"}:
        return "legal_term"
    return raw or "unknown"


def _source_title(source: Dict[str, Any]) -> str:
    return str(
        source.get("title")
        or source.get("source_title")
        or source.get("law_name")
        or source.get("term")
        or source.get("source_file")
        or source.get("sourceName")
        or ""
    )[:180]


def _source_url(source: Dict[str, Any]) -> str:
    return str(source.get("url") or source.get("source_url") or source.get("sanitized_source_url") or "")[:500]


def classify_query_for_grounding(
    question: str,
    *,
    visa_code: Optional[str] = None,
    task_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Return structured query understanding without deciding the legal answer."""
    facts = extract_immigration_facts(question, visa_code=visa_code)
    issues = classify_legal_issue_types(question, facts)
    activities = classify_activity_types(question)

    procedure_type = task_type or "general_eligibility_inquiry"
    for issue, procedure in _PROCEDURE_BY_ISSUE:
        if issue in issues:
            procedure_type = procedure
            break

    actions: List[str] = []
    for activity in activities:
        mapped = _ACTION_ALIASES.get(activity, activity)
        if mapped and mapped not in actions:
            actions.append(mapped)
    if not actions and "activity_scope" in issues:
        actions.append("work")

    missing: List[str] = []
    activity_facts = facts.get("activity_facts") or {}
    if any(a in actions for a in ("work", "paid_work", "freelancing", "business_operation", "job_change")):
        if activity_facts.get("paid") == "unknown":
            missing.append("paid_unpaid")
        if activity_facts.get("employer_or_client_known") == "false":
            missing.append("employer_type")
        if activity_facts.get("duration_known") == "false":
            missing.append("work_duration_or_hours")
    if procedure_type in {"extension_of_stay", "change_of_status", "foreigner_registration"}:
        if not facts.get("current_status"):
            missing.append("current_status")
        if procedure_type == "change_of_status" and not facts.get("target_status"):
            missing.append("intended_status")
        missing.append("application_timing") if "application_timing" not in missing else None
    if "overstay_or_risk" in issues:
        missing.extend([m for m in ("current_stay_validity", "application_timing") if m not in missing])

    return {
        "classifierVersion": NORMALIZATION_VERSION,
        "statusCode": facts.get("current_status"),
        "statusFamily": facts.get("current_parent_status"),
        "previousStatus": facts.get("previous_status"),
        "intendedStatus": facts.get("target_status"),
        "procedureType": procedure_type,
        "actionActivity": actions,
        "legalIssueTypes": issues,
        "facts": facts,
        "missingMaterialFacts": list(dict.fromkeys(missing)),
        "doesNotDecideFinalAnswer": True,
    }


def normalize_source_attempt(
    *,
    family: str,
    status: str,
    internal_code: str = "",
    title: str = "",
    source_name: str = "",
    url: str = "",
    version_date: str = "",
    retrieved_at: str = "",
    snippets: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    normalized_status = _normalize_status(status)
    clean_snippets = []
    for item in snippets or []:
        if isinstance(item, dict):
            snip = _snippet(
                item.get("text") or item.get("summary") or item.get("definition") or item.get("content") or "",
                citation=str(item.get("citation") or item.get("reference") or ""),
                article=str(item.get("article") or item.get("article_no") or ""),
                section=str(item.get("section") or item.get("procedure_type") or ""),
                page=str(item.get("page") or item.get("page_range") or ""),
                source_name=str(item.get("sourceName") or item.get("source_name") or item.get("law_name") or source_name or ""),
                url=str(item.get("url") or item.get("source_url") or url or ""),
            )
            if snip:
                clean_snippets.append(snip)
        else:
            snip = _snippet(str(item), source_name=source_name, url=url)
            if snip:
                clean_snippets.append(snip)

    return {
        "family": family or "unknown",
        "status": normalized_status,
        "publicStatus": _public_status(normalized_status),
        "internalCode": str(internal_code or "").upper()[:80],
        "title": title[:180] if title else "",
        "sourceName": source_name[:180] if source_name else title[:180],
        "url": url[:500] if url else "",
        "versionDate": version_date[:40] if version_date else "",
        "retrievedAt": retrieved_at or _now_iso(),
        "snippets": clean_snippets[:5],
    }


def normalize_manual_source_attempts(
    direct_manual_sources: Sequence[Dict[str, Any]] | None,
    related_manual_sources: Sequence[Dict[str, Any]] | None = None,
    *,
    manual_present: bool = False,
) -> List[Dict[str, Any]]:
    sources = list(direct_manual_sources or []) + list(related_manual_sources or [])
    if not sources and not manual_present:
        return []
    if not sources:
        return [
            normalize_source_attempt(
                family="manual",
                status="present",
                title="Official stay/residence manual",
                source_name="Ministry of Justice immigration manual",
            )
        ]
    attempts: List[Dict[str, Any]] = []
    for source in sources:
        title = _source_title(source) or "Official stay/residence manual"
        text = source.get("excerpt") or source.get("text") or source.get("summary") or title
        attempts.append(normalize_source_attempt(
            family="manual",
            status="present",
            title=title,
            source_name=str(source.get("issuing_body") or source.get("source_name") or "Ministry of Justice immigration manual"),
            url=_source_url(source),
            version_date=str(source.get("source_revision_date") or source.get("source_date") or source.get("version_date") or ""),
            snippets=[{
                "text": text,
                "section": source.get("section") or source.get("procedure_type") or "",
                "page": source.get("page_range") or source.get("page") or "",
                "sourceName": title,
                "url": _source_url(source),
            }],
        ))
    return attempts


def normalize_law_source_attempts(
    *,
    law_sources: Sequence[Dict[str, Any]] | None,
    source_family_statuses: Dict[str, str] | None,
    parser_status_by_family: Dict[str, str] | None = None,
    law_error_type_by_family: Dict[str, str] | None = None,
    source_family_results: Sequence[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    attempts: List[Dict[str, Any]] = []
    statuses = dict(source_family_statuses or {})
    by_family: Dict[str, List[Dict[str, Any]]] = {}
    for source in law_sources or []:
        if isinstance(source, dict):
            by_family.setdefault(_family_from_source(source, "statute"), []).append(source)
    for result in source_family_results or []:
        if isinstance(result, dict):
            family = str(result.get("source_family") or "").lower()
            if family and family not in statuses:
                statuses[family] = str(result.get("status") or "")

    for family, raw_status in statuses.items():
        # The "manual" family is a planning/status signal here, not a law-source
        # row. Manual evidence is normalized separately by
        # ``normalize_manual_source_attempts`` (with real titles/snippets), so
        # emitting it again from the law side only produces an empty duplicate
        # ``manual: available`` source — noise in the LLM prompt and a meaningless
        # "manual" chip in the public source list. Skip it here.
        if family == "manual":
            continue
        items = by_family.get(family, [])
        if items:
            for item in items[:4]:
                title = _source_title(item)
                attempts.append(normalize_source_attempt(
                    family=family,
                    status="results_found",
                    title=title,
                    source_name=title,
                    url=_source_url(item),
                    version_date=str(item.get("decision_date") or item.get("enforcement_date") or item.get("promulgation_date") or ""),
                    snippets=[{
                        "text": item.get("summary") or item.get("definition") or item.get("text") or title,
                        "citation": item.get("reference") or "",
                        "article": item.get("article") or "",
                        "sourceName": title,
                        "url": _source_url(item),
                    }],
                ))
            continue
        attempts.append(normalize_source_attempt(
            family=family,
            status=raw_status,
            internal_code=(law_error_type_by_family or {}).get(family, "") or raw_status,
            title="",
            source_name=family,
            snippets=[],
        ))
        if parser_status_by_family and parser_status_by_family.get(family):
            attempts[-1]["parserStatus"] = parser_status_by_family.get(family)
    return attempts


def _text_from_xml(root: ET.Element) -> str:
    return _compact_text(" ".join(t for t in root.itertext() if t), limit=1200)


def normalize_http_source_response(
    *,
    family: str,
    body: str,
    http_status: int = 200,
    title: str = "",
    source_name: str = "",
    url: str = "",
    retrieved_at: str = "",
) -> Dict[str, Any]:
    """Normalize arbitrary source response shapes without raising."""
    if http_status >= 400:
        return normalize_source_attempt(
            family=family, status="http_error", internal_code="HTTP_ERROR",
            title=title, source_name=source_name, url=url, retrieved_at=retrieved_at,
        )
    raw = body or ""
    stripped = raw.strip()
    if not stripped:
        return normalize_source_attempt(
            family=family, status="no_results", internal_code="EMPTY_BODY",
            title=title, source_name=source_name, url=url, retrieved_at=retrieved_at,
        )
    lower = stripped[:200].lower()
    if lower.startswith("<!doctype html") or lower.startswith("<html") or "<body" in lower:
        return normalize_source_attempt(
            family=family, status="bad_response", internal_code="HTML_RESPONSE",
            title=title, source_name=source_name, url=url, retrieved_at=retrieved_at,
        )
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            payload = json.loads(stripped)
        except Exception:
            return normalize_source_attempt(
                family=family, status="parse_error", internal_code="MALFORMED_JSON",
                title=title, source_name=source_name, url=url, retrieved_at=retrieved_at,
            )
        snippets = _snippets_from_json_payload(payload)
        return normalize_source_attempt(
            family=family,
            status="results_found" if snippets else "no_results",
            internal_code="" if snippets else "UNEXPECTED_SCHEMA",
            title=title or _title_from_json_payload(payload),
            source_name=source_name or title,
            url=url,
            retrieved_at=retrieved_at,
            snippets=snippets,
        )
    if stripped.startswith("<"):
        try:
            root = ET.fromstring(stripped)
        except Exception:
            return normalize_source_attempt(
                family=family, status="parse_error", internal_code="MALFORMED_XML",
                title=title, source_name=source_name, url=url, retrieved_at=retrieved_at,
            )
        text = _text_from_xml(root)
        return normalize_source_attempt(
            family=family,
            status="results_found" if text else "no_results",
            title=title or root.tag.split("}", 1)[-1],
            source_name=source_name or title,
            url=url,
            retrieved_at=retrieved_at,
            snippets=[{"text": text, "sourceName": source_name or title}] if text else [],
        )
    return normalize_source_attempt(
        family=family,
        status="bad_response",
        internal_code="PLAIN_TEXT_RESPONSE",
        title=title,
        source_name=source_name or title,
        url=url,
        retrieved_at=retrieved_at,
        snippets=[],
    )


def _title_from_json_payload(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("title", "law_name", "법령명한글", "법령명", "term", "법령용어명"):
            if payload.get(key):
                return str(payload.get(key))
        for value in payload.values():
            title = _title_from_json_payload(value)
            if title:
                return title
    if isinstance(payload, list):
        for item in payload:
            title = _title_from_json_payload(item)
            if title:
                return title
    return ""


def _snippets_from_json_payload(payload: Any) -> List[Dict[str, Any]]:
    snippets: List[Dict[str, Any]] = []

    def visit(node: Any) -> None:
        if len(snippets) >= 5:
            return
        if isinstance(node, dict):
            text = (
                node.get("summary") or node.get("definition") or node.get("text")
                or node.get("조문내용") or node.get("내용") or node.get("법령용어정의")
            )
            if text:
                snippets.append({
                    "text": text,
                    "article": node.get("article") or node.get("조문번호") or "",
                    "citation": node.get("reference") or node.get("법령ID") or node.get("MST") or "",
                    "sourceName": _source_title(node),
                    "url": _source_url(node),
                })
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    return snippets


def select_answer_policy(query_classification: Dict[str, Any]) -> Dict[str, Any]:
    procedure = str(query_classification.get("procedureType") or "")
    issues = set(query_classification.get("legalIssueTypes") or [])
    if procedure == "document_requirement_inquiry":
        policy = "document_requirement"
        sections = ["결론", "필요한 서류", "조건부 서류", "절차 메모", "공식 출처 상태", "다음 행동"]
    elif procedure in {"extension_of_stay", "change_of_status", "foreigner_registration", "registration_information_change"}:
        policy = "procedure"
        sections = ["결론", "적용되는 경우", "필요한 서류", "절차 메모", "제한/주의", "공식 출처 상태", "다음 행동"]
    elif "overstay_or_risk" in issues:
        policy = "law_risk"
        sections = ["결론", "적용되는 경우", "제한/주의", "확인할 사실", "공식 출처 상태", "다음 행동"]
    elif issues & {"activity_scope", "outside_status_activity", "work_on_non_work_status", "employment_restriction"}:
        policy = "eligibility_activity"
        sections = ["결론", "적용되는 경우", "제한/주의", "확인할 사실", "공식 출처 상태", "다음 행동"]
    else:
        policy = "general_eligibility"
        sections = ["결론", "적용되는 경우", "제한/주의", "공식 출처 상태", "다음 행동"]
    return {"policy": policy, "sectionLabels": sections}


def build_official_grounding_context(
    *,
    query_classification: Dict[str, Any],
    normalized_sources: Sequence[Dict[str, Any]],
    source_plan: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    available = [s for s in normalized_sources if s.get("status") == "available" and s.get("snippets")]
    limited = [s for s in normalized_sources if s.get("status") != "available"]
    uncertainty = []
    if limited:
        families = ", ".join(sorted({str(s.get("family")) for s in limited if s.get("family")}))
        uncertainty.append(f"Some planned source families were unavailable or unwired: {families}.")
    if query_classification.get("missingMaterialFacts"):
        uncertainty.append(
            "Missing facts may change the answer: "
            + ", ".join(query_classification.get("missingMaterialFacts") or [])
            + "."
        )
    if not available:
        uncertainty.append("No directly quotable official-source snippet is available in this context.")
    return {
        "groundingContextVersion": NORMALIZATION_VERSION,
        "queryClassification": query_classification,
        "answerPolicy": select_answer_policy(query_classification),
        "sourcePlan": source_plan or {},
        "sources": [
            {
                "family": s.get("family"),
                "status": s.get("status"),
                "publicStatus": s.get("publicStatus"),
                "title": s.get("title"),
                "sourceName": s.get("sourceName"),
                "versionDate": s.get("versionDate"),
                "url": s.get("url"),
                "reliability": "official" if s.get("family") in {"manual", "statute", "enforcement_decree", "enforcement_rule", "administrative_rule", "legal_term"} else "planned",
                "snippets": s.get("snippets") or [],
            }
            for s in normalized_sources
        ],
        "uncertaintyBoundaries": uncertainty,
        "llmInstructions": [
            "Use official snippets when available.",
            "Do not invent requirements not supported by retrieved sources.",
            "Distinguish confirmed rules from procedural caution.",
            "Ask for missing facts only when they materially affect the answer.",
            "Use 1345/HiKorea/immigration office as final confirmation, not as a substitute for analysis.",
            "If coverage is partial, say which part is confirmed and which remains uncertain.",
        ],
    }


def render_grounding_context_for_prompt(context: Dict[str, Any]) -> str:
    """Compact text block for LLM context; no raw diagnostic codes."""
    qc = context.get("queryClassification") or {}
    policy = context.get("answerPolicy") or {}
    lines = [
        f"query: status={qc.get('statusCode') or 'unknown'}, family={qc.get('statusFamily') or 'unknown'}, procedure={qc.get('procedureType')}",
        "actions: " + ", ".join(qc.get("actionActivity") or ["unknown"]),
        "issues: " + ", ".join(qc.get("legalIssueTypes") or ["unknown"]),
        "missing_material_facts: " + ", ".join(qc.get("missingMaterialFacts") or ["none"]),
        f"answer_policy: {policy.get('policy')} | sections: {', '.join(policy.get('sectionLabels') or [])}",
        "sources:",
    ]
    for source in (context.get("sources") or [])[:8]:
        lines.append(
            f"- {source.get('family')}: {source.get('publicStatus')} | "
            f"{source.get('title') or source.get('sourceName') or 'planned source'}"
            + (f" | version/date: {source.get('versionDate')}" if source.get("versionDate") else "")
        )
        for snip in (source.get("snippets") or [])[:2]:
            prefix = "  excerpt"
            if snip.get("article"):
                prefix += f" {snip.get('article')}"
            elif snip.get("section"):
                prefix += f" {snip.get('section')}"
            lines.append(f"  {prefix}: {_compact_text(snip.get('text'), limit=360)}")
    if context.get("uncertaintyBoundaries"):
        lines.append("uncertainty_boundaries:")
        for item in context.get("uncertaintyBoundaries") or []:
            lines.append(f"- {item}")
    lines.append("instructions:")
    for item in context.get("llmInstructions") or []:
        lines.append(f"- {item}")
    return "\n".join(lines)


def project_public_source_status(
    normalized_sources: Sequence[Dict[str, Any]],
    *,
    lang: str = "ko",
) -> Dict[str, Any]:
    labels = PUBLIC_LABELS_EN if str(lang or "").lower().startswith("en") else PUBLIC_LABELS_KO
    families_available = {s.get("family") for s in normalized_sources if s.get("status") == "available"}
    families_temp = {s.get("family") for s in normalized_sources if s.get("status") == "temporarily_unavailable"}
    label_keys: List[str] = []
    if "manual" in families_available:
        label_keys.append("manual_available")
    if families_available & {"statute", "enforcement_decree", "enforcement_rule", "administrative_rule", "legal_term"}:
        label_keys.append("law_available")
    if families_temp & {"statute", "enforcement_decree", "enforcement_rule", "administrative_rule", "legal_term"}:
        label_keys.append("law_temporarily_unavailable")
    if families_available:
        label_keys.append("stored_official")
    if not families_available:
        label_keys.append("limited")
    label_keys.append("confirmation_needed")
    public_sources = []
    for source in normalized_sources:
        public_sources.append({
            "family": source.get("family"),
            "publicStatus": source.get("publicStatus"),
            "title": source.get("title"),
            "sourceName": source.get("sourceName"),
            "url": source.get("url"),
            "versionDate": source.get("versionDate"),
            "snippetCount": len(source.get("snippets") or []),
        })
    return {
        "labels": [labels[key] for key in list(dict.fromkeys(label_keys))],
        "labelKeys": list(dict.fromkeys(label_keys)),
        "sources": public_sources,
        "hasAvailableOfficialSource": bool(families_available),
        "hasTemporarilyUnavailableSource": bool(families_temp),
    }


def developer_source_diagnostics(normalized_sources: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Developer-only shape; do not render in the normal source panel."""
    return {
        "sourceNormalizationVersion": NORMALIZATION_VERSION,
        "sources": [
            {
                "family": s.get("family"),
                "status": s.get("status"),
                "internalCode": s.get("internalCode"),
                "parserStatus": s.get("parserStatus", ""),
            }
            for s in normalized_sources
            if s.get("internalCode") or s.get("parserStatus")
        ],
    }
