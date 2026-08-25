"""Official-source evidence retrieval for enforcement predictions.

Only verified legal sources and citation-grade official precedent bodies enter
the public pack.  List results, fixtures, demo/synthetic records and secondary
anonymous material are excluded by construction.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from .enforcement_models import (
    EnforcementEvidencePack,
    EvidenceItem,
    LegalBaseline,
    SimilarCaseReference,
    StructuredCase,
)


_FORBIDDEN_MARKERS = ("fixture", "synthetic", "demo", "mock", "example")


def _safe_text(value: Any, limit: int = 700) -> str:
    return " ".join(str(value or "").split())[:limit]


def _contains_forbidden_marker(item: Dict[str, Any]) -> bool:
    blob = " ".join(f"{k} {v}" for k, v in item.items()).lower()
    return any(marker in blob for marker in _FORBIDDEN_MARKERS)


def _query_for_case(case: StructuredCase, baseline: LegalBaseline) -> str:
    labels = {
        "STATUS_OUTSIDE_ACTIVITY_ART20": "체류자격외활동허가 위반 출입국",
        "UNAUTHORIZED_EMPLOYMENT_ART18_2": "취업할 수 없는 체류자격 취업 출입국",
        "UNAUTHORIZED_STAY_OR_WORK_ART18_1": "체류자격 취업활동 위반 출입국",
        "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1": "근무처 변경 추가 허가 위반 출입국",
        "OVERSTAY_ART25": "체류기간 초과 출입국",
    }
    return labels.get(case.violation_code or "", baseline.violation_label or "출입국 사범")


def _baseline_evidence(baseline: LegalBaseline) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for source in baseline.sources:
        source_type = "REGULATION" if "시행규칙" in source.title else "STATUTE"
        items.append(EvidenceItem(
            id=source.id,
            source_type=source_type,
            title=source.title,
            authority=source.authority,
            source_date=source.effective_date,
            source_url=source.url,
            excerpt=source.article,
            citation_grade="DIRECT",
            result_kind="LEGAL_RULE",
        ))
    return items


def _convert_precedent_body(raw: Dict[str, Any], case: StructuredCase) -> tuple[Optional[EvidenceItem], Optional[SimilarCaseReference]]:
    if not isinstance(raw, dict) or _contains_forbidden_marker(raw):
        return None, None
    if raw.get("resultKind") != "body_result" or str(raw.get("citationGrade", "")).lower() != "direct":
        return None, None
    source_id = _safe_text(raw.get("serialNumber") or raw.get("sourceId") or raw.get("id"), 80)
    url = _safe_text(raw.get("sourceUrl") or raw.get("url"), 500)
    title = _safe_text(raw.get("title") or raw.get("caseName"), 240)
    holding = _safe_text(raw.get("holdingSummary") or raw.get("snippet") or raw.get("summary"), 700)
    if not source_id or not url or not title or not holding or "law.go.kr" not in url:
        return None, None
    evidence_id = f"precedent:{source_id}"
    source_date = None
    date_raw = str(raw.get("decisionDate") or "")[:10]
    try:
        source_date = date.fromisoformat(date_raw)
    except ValueError:
        pass
    evidence = EvidenceItem(
        id=evidence_id,
        source_type="COURT",
        title=title,
        authority=_safe_text(raw.get("courtOrAgency") or "대한민국 법원", 100),
        source_date=source_date,
        source_url=url,
        excerpt=holding,
        citation_grade="DIRECT",
        result_kind="BODY_RESULT",
    )
    matching = ["위반 유형"]
    if case.status_of_stay and case.status_of_stay.lower() in (title + " " + holding).lower():
        matching.append("체류자격")
    similar = SimilarCaseReference(
        id=f"similar:{source_id}",
        source_type="COURT",
        matching_factors=matching,
        differing_factors=["공개 결정문만으로 모든 사실관계의 동일성은 확인할 수 없음"],
        outcome_summary=holding,
        source_title=title,
        source_date=source_date,
        source_url=url,
        evidence_id=evidence_id,
    )
    return evidence, similar


def retrieve_enforcement_evidence(
    case: StructuredCase,
    baseline: LegalBaseline,
    *,
    precedent_adapter: Any = None,
    max_cases: int = 3,
) -> EnforcementEvidencePack:
    evidence = _baseline_evidence(baseline)
    similar_cases: list[SimilarCaseReference] = []
    limitations: list[str] = []

    if precedent_adapter is None:
        try:
            from . import precedent_sources as precedent_adapter  # type: ignore
        except Exception:
            precedent_adapter = None

    if precedent_adapter is not None and baseline.status == "AVAILABLE":
        try:
            search = precedent_adapter.search_precedents(_query_for_case(case, baseline), limit=max_cases)
            for candidate in (search.get("items") or [])[:max_cases]:
                # A search result is metadata only. Fetch and expose a case only
                # after a citation-grade body result has been retrieved.
                if not isinstance(candidate, dict) or _contains_forbidden_marker(candidate):
                    continue
                source_id = candidate.get("serialNumber") or candidate.get("sourceId")
                if not source_id:
                    continue
                detail = precedent_adapter.get_precedent_detail(str(source_id))
                for body in detail.get("items") or []:
                    converted, similar = _convert_precedent_body(body, case)
                    if converted and similar:
                        evidence.append(converted)
                        similar_cases.append(similar)
        except Exception:
            # Official-source failure lowers evidence strength but must never
            # break the deterministic legal calculation.
            limitations.append("공식 유사사례 검색을 완료하지 못했습니다.")

    if not similar_cases:
        limitations.append("현재 확인 가능한 유사 공개사례가 충분하지 않습니다.")
    status = "AVAILABLE" if similar_cases else ("LIMITED" if evidence else "UNAVAILABLE")
    return EnforcementEvidencePack(
        evidence=evidence,
        similar_cases=similar_cases,
        retrieval_status=status,
        limitations=limitations,
    )
