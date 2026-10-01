"""Deterministic, versioned Korean immigration enforcement calculator."""

from __future__ import annotations

import calendar
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .enforcement_models import LegalBaseline, MoneyRange, SourceReference, StructuredCase
from .enforcement_ontology import EnforcementOntologyError, validate_legal_rule_database

RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "enforcement" / "legal_rules.json"


class EnforcementRuleError(ValueError):
    pass


# 출입국관리법 제21조제1항 단서·제3항, 시행령 제26조의2: E-1~E-7 중 법무부장관 고시
# 요건을 갖춘 사람은 근무처 변경·추가를 사후 '신고'하며, 이들에게는 제18조제2항이
# 적용되지 않는다. 신고의무 위반은 범칙금(별표 7)이 아니라 과태료(제100조제1항제3호).
_REPORT_PROVISO_STATUS_RE = re.compile(r"^E-[1-7](?:-|$)", re.I)
_WORKPLACE_CODES = {"UNAUTHORIZED_EMPLOYMENT_ART18_2", "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1"}
REPORT_PROVISO_NOTE = (
    "이 금액은 근무처 변경·추가 '허가' 대상자 기준입니다. E-1~E-7 중 법무부장관 고시 요건을 갖춘 "
    "'신고' 대상자라면 제18조제2항은 적용되지 않고(출입국관리법 제21조제3항, 시행령 제26조의2), "
    "신고의무 위반은 범칙금이 아니라 과태료(같은 법 제100조제1항제3호, 200만원 이하) 대상입니다."
)
SHARED_TIER_NOTE = (
    "제18조제2항과 제21조제1항 중 어느 조문이 적용되는지는 정해지지 않았지만, 두 조문의 범칙금 "
    "양정기준(출입국관리법 시행규칙 별표 7 더목·저목)이 같아 기준 금액은 같습니다."
)


def _report_proviso_applies(status: Optional[str], codes: Iterable[str]) -> bool:
    if not (set(codes) & _WORKPLACE_CODES):
        return False
    return not status or bool(_REPORT_PROVISO_STATUS_RE.match(status))


def _shared_candidate_rule(case: StructuredCase, snapshot: Dict[str, Any]) -> Optional[list[Dict[str, Any]]]:
    """Rules for an unresolved case whose candidates all carry the same penalty table.

    When the only open question is which of several provisions applies and every
    candidate has the identical tier table and statutory maximum, the baseline
    amount does not depend on the answer, so it can be stated without choosing.
    """
    candidates = list(dict.fromkeys(case.violation_candidates or []))
    if len(candidates) < 2:
        return None
    rules = [next((row for row in snapshot["rules"] if row["violationCode"] == code), None) for code in candidates]
    if any(rule is None for rule in rules):
        return None
    first = rules[0]
    for rule in rules[1:]:
        if rule["tiers"] != first["tiers"] or rule["statutoryMaximumKrw"] != first["statutoryMaximumKrw"]:
            return None
    return rules


def load_rule_database(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or RULES_PATH
    data = json.loads(target.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != "1.0.0" or not data.get("snapshots"):
        raise EnforcementRuleError("invalid enforcement rule database")
    for snapshot in data["snapshots"]:
        if not snapshot.get("id") or not snapshot.get("effectiveFrom") or not snapshot.get("rules"):
            raise EnforcementRuleError("incomplete enforcement legal snapshot")
        for rule in snapshot["rules"]:
            previous = -1
            for tier in rule.get("tiers", []):
                minimum = int(tier["minimumMonths"])
                if minimum <= previous or int(tier["amountKrw"]) < 0:
                    raise EnforcementRuleError("invalid or unordered enforcement tiers")
                previous = minimum
    try:
        validate_legal_rule_database(data)
    except EnforcementOntologyError as exc:
        raise EnforcementRuleError(str(exc)) from exc
    return data


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _duration_days(case: StructuredCase) -> Optional[int]:
    if case.violation_start_date and case.violation_end_date:
        return (case.violation_end_date - case.violation_start_date).days + 1
    return case.duration_days


def _tier_for_duration(tiers: Iterable[Dict[str, Any]], case: StructuredCase, duration_days: int) -> Dict[str, Any]:
    # Where exact dates exist, compare with true calendar-month anniversaries.
    # A duration-only answer cannot encode calendar shape, so the conservative
    # public convention is 30 days per month and is disclosed as an assumption.
    if case.violation_start_date and case.violation_end_date:
        months = 0
        while months < 1200 and case.violation_end_date >= _add_months(case.violation_start_date, months + 1):
            months += 1
    else:
        months = duration_days / 30.0
    for tier in tiers:
        minimum = float(tier["minimumMonths"])
        maximum = tier.get("maximumMonths")
        if months >= minimum and (maximum is None or months < float(maximum)):
            return tier
    raise EnforcementRuleError("no duration tier matched")


def _resolve_snapshot(case: StructuredCase, database: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    relevant = case.violation_end_date or case.violation_start_date or case.assessment_date or date.today()
    for snapshot in sorted(database["snapshots"], key=lambda row: row["effectiveFrom"], reverse=True):
        start = date.fromisoformat(snapshot["effectiveFrom"])
        end = date.fromisoformat(snapshot["effectiveUntil"]) if snapshot.get("effectiveUntil") else None
        if relevant >= start and (end is None or relevant <= end):
            # A continuing violation that crosses a legal-version boundary is
            # intentionally not guessed; transitional-law review is required.
            if case.violation_start_date and case.violation_start_date < start:
                return None
            return snapshot
    return None


def _source_refs(snapshot: Dict[str, Any]) -> list[SourceReference]:
    refs = []
    for index, source in enumerate(snapshot.get("sources", []), start=1):
        refs.append(SourceReference(
            id=f"{snapshot['id']}:source:{index}",
            authority=source["authority"],
            title=source["lawName"],
            article=source.get("article"),
            effective_date=date.fromisoformat(snapshot["effectiveFrom"]),
            url=source["url"],
            verified_at=date.fromisoformat(snapshot["verifiedAt"]),
        ))
    return refs


def _available_dispositions(violation_code: str) -> list[str]:
    # This list represents legal availability only, never predicted likelihood.
    common = ["STAY_PERMISSION_DISADVANTAGE", "DEPARTURE_ORDER", "DEPORTATION"]
    if violation_code in {"UNAUTHORIZED_STAY_OR_WORK_ART18_1", "UNAUTHORIZED_EMPLOYMENT_ART18_2", "STATUS_OUTSIDE_ACTIVITY_ART20", "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1"}:
        return common + ["CRIMINAL_REFERRAL"]
    if violation_code == "OVERSTAY_ART25":
        return common
    return []


def calculate_legal_baseline(case: StructuredCase, *, database: Optional[Dict[str, Any]] = None) -> LegalBaseline:
    database = database or load_rule_database()
    snapshot = _resolve_snapshot(case, database)
    if snapshot is None:
        return LegalBaseline(
            status="HISTORICAL_RULE_UNAVAILABLE",
            violation_code=case.violation_code,
            missing_facts=["해당 위반기간 전체에 적용되는 검증된 법령 스냅샷"],
            confidence="INSUFFICIENT",
        )

    shared_rules = None if case.violation_code else _shared_candidate_rule(case, snapshot)
    if not case.violation_code and not shared_rules:
        return LegalBaseline(
            status="MISSING_FACTS",
            legal_snapshot_id=snapshot["id"],
            effective_from=date.fromisoformat(snapshot["effectiveFrom"]),
            missing_facts=["위반 유형"],
            sources=_source_refs(snapshot),
            confidence="INSUFFICIENT",
        )
    rule = shared_rules[0] if shared_rules else next(
        (row for row in snapshot["rules"] if row["violationCode"] == case.violation_code), None
    )
    if not rule:
        return LegalBaseline(
            status="UNSUPPORTED",
            violation_code=case.violation_code,
            legal_snapshot_id=snapshot["id"],
            effective_from=date.fromisoformat(snapshot["effectiveFrom"]),
            sources=_source_refs(snapshot),
            confidence="INSUFFICIENT",
        )
    duration = _duration_days(case)
    if duration is None:
        return LegalBaseline(
            status="MISSING_FACTS",
            violation_code=case.violation_code,
            violation_label=rule["label"],
            legal_snapshot_id=snapshot["id"],
            effective_from=date.fromisoformat(snapshot["effectiveFrom"]),
            missing_facts=["위반기간"],
            sources=_source_refs(snapshot),
            confidence="INSUFFICIENT",
        )

    tier = _tier_for_duration(rule["tiers"], case, duration)
    baseline = int(tier["amountKrw"])
    statutory_maximum = int(rule["statutoryMaximumKrw"])
    # 시행규칙 제86조: 기준액의 50% 범위에서 가중·감경하되 법정 상한 준수.
    minimum = max(0, baseline // 2)
    maximum = min(statutory_maximum, baseline + baseline // 2)
    assumptions = []
    if not (case.violation_start_date and case.violation_end_date):
        assumptions.append("정확한 시작·종료일이 없어 30일을 1개월로 환산했습니다.")
    codes = [row["violationCode"] for row in shared_rules] if shared_rules else [case.violation_code]
    if shared_rules:
        assumptions.append(SHARED_TIER_NOTE)
    if _report_proviso_applies(case.status_of_stay, codes):
        assumptions.append(REPORT_PROVISO_NOTE)
    applied = (
        [row["statuteArticle"] for row in shared_rules] if shared_rules else [rule["statuteArticle"]]
    ) + [rule["penaltyArticle"], "출입국관리법 시행규칙 제86조(가중·감경 범위)"]
    return LegalBaseline(
        status="AVAILABLE",
        violation_code=case.violation_code,
        violation_label=(
            " 또는 ".join(row["label"] for row in shared_rules) + " (조문 미확정)" if shared_rules else rule["label"]
        ),
        baseline_amount_krw=baseline,
        legally_adjustable_range=MoneyRange(minimum_krw=minimum, maximum_krw=maximum),
        statutory_maximum_krw=statutory_maximum,
        duration_days=duration,
        legal_snapshot_id=snapshot["id"],
        effective_from=date.fromisoformat(snapshot["effectiveFrom"]),
        applied_rules=applied,
        legally_available_dispositions=_available_dispositions(codes[0]),
        assumptions=assumptions,
        sources=_source_refs(snapshot),
        confidence="HIGH" if assumptions else "VERY_HIGH",
    )
