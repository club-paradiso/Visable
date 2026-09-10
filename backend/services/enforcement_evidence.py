"""Official-source evidence retrieval for enforcement predictions.

Only verified legal sources and citation-grade official precedent bodies enter
the public pack. List results, fixtures, demo/synthetic records and secondary
anonymous material are excluded by construction.
"""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
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
_MAX_SIMILAR_CASES = 3
_VIOLATION_SIMILARITY_TERMS = {
    "STATUS_OUTSIDE_ACTIVITY_ART20": ("체류자격외활동", "체류자격 외 활동", "자격외활동"),
    "UNAUTHORIZED_EMPLOYMENT_ART18_2": ("지정된 근무처", "지정 근무처", "취업활동"),
    "UNAUTHORIZED_STAY_OR_WORK_ART18_1": ("취업활동 가능한 체류자격", "취업 자격", "불법취업"),
    "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1": ("근무처 변경", "근무처 추가", "변경허가"),
    "OVERSTAY_ART25": ("체류기간", "연장허가", "초과체류", "체류기간 연장"),
}
_STATUS_PATTERN = re.compile(r"(?<![A-Z0-9])([A-Z]-?\d{1,2}(?:-\d{1,2})?)(?![A-Z0-9])", re.I)
_DURATION_PATTERN = re.compile(r"(\d{1,4})\s*(일|개월|달|년)")


def _safe_text(value: Any, limit: int = 700) -> str:
    return " ".join(str(value or "").split())[:limit]


def _contains_forbidden_marker(item: Dict[str, Any]) -> bool:
    blob = " ".join(f"{k} {v}" for k, v in item.items()).lower()
    return any(marker in blob for marker in _FORBIDDEN_MARKERS)


def _query_for_case(case: StructuredCase, baseline: LegalBaseline) -> str:
    labels = {
        "STATUS_OUTSIDE_ACTIVITY_ART20": "체류자격외활동허가 출입국관리법",
        "UNAUTHORIZED_EMPLOYMENT_ART18_2": "지정된 근무처 아닌 곳 근무 출입국관리법",
        "UNAUTHORIZED_STAY_OR_WORK_ART18_1": "취업활동 가능한 체류자격 없이 취업 출입국관리법",
        "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1": "근무처 변경 추가 허가 출입국관리법",
        "OVERSTAY_ART25": "체류기간 연장허가 출입국관리법",
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


def _normalize_status(value: str) -> str:
    raw = re.sub(r"\s+", "", str(value or "").upper())
    match = re.fullmatch(r"([A-Z])-?(\d{1,2})(?:-?(\d{1,2}))?", raw)
    if not match:
        return raw
    base = f"{match.group(1)}-{int(match.group(2))}"
    return base + (f"-{int(match.group(3))}" if match.group(3) else "")


def _duration_bucket(days: int) -> str:
    if days <= 30:
        return "30일 이하"
    if days <= 90:
        return "31~90일"
    if days <= 365:
        return "91~365일"
    return "365일 초과"


def _extract_duration_days(text: str) -> Optional[int]:
    match = _DURATION_PATTERN.search(text or "")
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    if unit in {"개월", "달"}:
        return amount * 30
    if unit == "년":
        return amount * 365
    return amount


def _precedent_similarity(raw: Dict[str, Any], case: StructuredCase) -> tuple[float, list[str], list[str]]:
    """Return conservative retrieval relevance, never an outcome probability.

    Missing facts simply earn no points. A differing factor is emitted only
    when the public body text contains an explicit comparable fact that differs
    from the structured case.
    """

    title = _safe_text(raw.get("title") or raw.get("caseName"), 240)
    holding = _safe_text(raw.get("holdingSummary") or raw.get("snippet") or raw.get("summary"), 700)
    blob = f"{title} {holding}"
    lowered = blob.lower()
    score = 0.0
    matching: list[str] = []
    differing: list[str] = []

    terms = _VIOLATION_SIMILARITY_TERMS.get(case.violation_code or "", ())
    if terms and any(term.lower() in lowered for term in terms):
        score += 0.50
        matching.append("동일·유사 법적 쟁점")

    if case.status_of_stay:
        current_status = _normalize_status(case.status_of_stay)
        mentioned_statuses = {_normalize_status(item) for item in _STATUS_PATTERN.findall(blob)}
        if current_status in mentioned_statuses:
            score += 0.20
            matching.append(f"동일 체류자격({current_status})")
        elif mentioned_statuses:
            differing.append(
                f"공개 판결문에 표시된 체류자격({', '.join(sorted(mentioned_statuses))})이 현재 사건({current_status})과 다름"
            )

    if case.duration_days is not None:
        precedent_days = _extract_duration_days(blob)
        if precedent_days is not None:
            current_bucket = _duration_bucket(case.duration_days)
            precedent_bucket = _duration_bucket(precedent_days)
            if current_bucket == precedent_bucket:
                score += 0.15
                matching.append(f"유사 위반기간 구간({current_bucket})")
            else:
                differing.append(f"위반기간 구간이 다름(현재 {current_bucket}, 공개사례 {precedent_bucket})")

    if case.prior_violations == 0:
        if any(term in blob for term in ("초범", "첫 위반", "위반전력 없음", "전력이 없다")):
            score += 0.10
            matching.append("초범·위반전력 없음")
        elif any(term in blob for term in ("재범", "동종 전력", "위반전력 있음", "위반 전력이 있")):
            differing.append("공개사례에는 기존 위반전력이 명시됨")
    elif case.prior_violations is not None and case.prior_violations > 0:
        if any(term in blob for term in ("재범", "동종 전력", "위반전력 있음", "위반 전력이 있")):
            score += 0.10
            matching.append("기존 위반전력 요소")
        elif any(term in blob for term in ("초범", "첫 위반", "위반전력 없음", "전력이 없다")):
            differing.append("공개사례는 초범으로 표시됨")

    if case.voluntary_disclosure is True and any(term in blob for term in ("자진신고", "자진 신고", "자진출석", "자진 방문")):
        score += 0.05
        matching.append("자진신고·자진출석 요소")

    if not matching:
        differing.append("공개 판결문 요약에서 현재 사건과 직접 비교 가능한 구조화 사실요소가 제한적임")

    return round(min(score, 1.0), 3), matching, differing


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
    similarity_score, matching, differing = _precedent_similarity(raw, case)
    similar = SimilarCaseReference(
        id=f"similar:{source_id}",
        source_type="COURT",
        similarity_score=similarity_score,
        matching_factors=matching,
        differing_factors=differing,
        outcome_summary=holding,
        source_title=title,
        source_date=source_date,
        source_url=url,
        evidence_id=evidence_id,
    )
    return evidence, similar


def _bounded_grounding_config():
    """Return the normal law config with an enforcement-specific short timeout.

    Enforcement analysis is synchronous from the user's perspective. A slow
    precedent lookup must not delay the deterministic statutory baseline for
    several seconds per candidate. The normal law tooling keeps its own timeout;
    only this optional similar-case enrichment is bounded here.
    """
    from .grounding_config import load_grounding_config

    raw = (os.environ.get("ENFORCEMENT_PRECEDENT_TIMEOUT_SECONDS") or "0.8").strip()
    try:
        timeout = float(raw)
    except (TypeError, ValueError):
        timeout = 0.8
    timeout = max(0.25, min(timeout, 2.0))
    return replace(load_grounding_config(), timeout_seconds=timeout)


def _candidate_source_id(candidate: Any) -> Optional[str]:
    if not isinstance(candidate, dict) or _contains_forbidden_marker(candidate):
        return None
    source_id = candidate.get("serialNumber") or candidate.get("sourceId")
    return str(source_id) if source_id else None


def _fetch_precedent_detail(precedent_adapter: Any, source_id: str, adapter_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    result = precedent_adapter.get_precedent_detail(source_id, **adapter_kwargs)
    return result if isinstance(result, dict) else {}


def retrieve_enforcement_evidence(
    case: StructuredCase,
    baseline: LegalBaseline,
    *,
    precedent_adapter: Any = None,
    max_cases: int = 2,
) -> EnforcementEvidencePack:
    evidence = _baseline_evidence(baseline)
    similar_pairs: list[tuple[EvidenceItem, SimilarCaseReference]] = []
    limitations: list[str] = []
    adapter_kwargs: Dict[str, Any] = {}

    if precedent_adapter is None:
        try:
            from . import precedent_sources as precedent_adapter  # type: ignore
            adapter_kwargs["config"] = _bounded_grounding_config()
        except Exception:
            precedent_adapter = None
            adapter_kwargs = {}

    requested_cases = max(1, min(int(max_cases or 1), _MAX_SIMILAR_CASES))
    if precedent_adapter is not None and baseline.status == "AVAILABLE":
        try:
            # Search one extra candidate (up to three total) so ranking is not
            # simply the API's first result. Detail requests run concurrently;
            # with the bounded official-source timeout this preserves roughly
            # the same network-stage latency budget as the old single-case path.
            search_limit = min(_MAX_SIMILAR_CASES, requested_cases + 1)
            search = precedent_adapter.search_precedents(
                _query_for_case(case, baseline),
                limit=search_limit,
                **adapter_kwargs,
            )
            source_ids: list[str] = []
            for candidate in (search.get("items") or [])[:search_limit]:
                source_id = _candidate_source_id(candidate)
                if source_id and source_id not in source_ids:
                    source_ids.append(source_id)

            detail_failures = 0
            if source_ids:
                with ThreadPoolExecutor(max_workers=min(len(source_ids), _MAX_SIMILAR_CASES)) as executor:
                    futures = {
                        executor.submit(_fetch_precedent_detail, precedent_adapter, source_id, adapter_kwargs): source_id
                        for source_id in source_ids
                    }
                    for future in as_completed(futures):
                        try:
                            detail = future.result()
                        except Exception:
                            detail_failures += 1
                            continue
                        for body in detail.get("items") or []:
                            converted, similar = _convert_precedent_body(body, case)
                            if converted and similar:
                                similar_pairs.append((converted, similar))

            if detail_failures:
                limitations.append("일부 공식 유사사례 본문 조회를 완료하지 못했습니다.")
        except Exception:
            # Official-source failure lowers evidence strength but must never
            # break the deterministic legal calculation.
            limitations.append("공식 유사사례 검색을 완료하지 못했습니다.")

    # Similarity is a deterministic retrieval-relevance heuristic, not an
    # outcome probability. Stable id tie-breaking keeps tests/output repeatable
    # even though detail requests complete concurrently.
    similar_pairs.sort(key=lambda pair: (-(pair[1].similarity_score or 0.0), pair[1].id))
    selected = similar_pairs[:requested_cases]
    evidence.extend(pair[0] for pair in selected)
    similar_cases = [pair[1] for pair in selected]

    if similar_cases:
        limitations.append("유사도 점수는 공개 판결문과 구조화 사건 사실의 검색 관련성 지표이며 처분 확률이 아닙니다.")
    else:
        limitations.append("현재 확인 가능한 유사 공개사례가 충분하지 않습니다.")
    status = "AVAILABLE" if similar_cases else ("LIMITED" if evidence else "UNAVAILABLE")
    return EnforcementEvidencePack(
        evidence=evidence,
        similar_cases=similar_cases,
        retrieval_status=status,
        limitations=limitations,
    )
