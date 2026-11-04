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
from .enforcement_workplace import WORKPLACE_VIOLATION_CODES, determine_workplace_regime

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
PERMIT_CONFIRMATION_NOTE = (
    "근무처 변경·추가가 사전허가 대상이라는 사용자의 확인을 전제로 한 조건부 계산입니다. "
    "출입국관서의 최종 법적 분류를 의미하지 않습니다."
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


def _ambiguous_calendar_boundary(tiers: Iterable[Dict[str, Any]], duration_days: int) -> bool:
    """Return True if the day count can straddle a statutory calendar-month tier.

    A four-year cycle includes leap and common years, across all valid starting
    days. An exact start/end date is needed when the tier depends on the month.
    Do not assert 30 days always equals a legal calendar month.
    """
    thresholds = sorted({int(row["minimumMonths"]) for row in tiers
                         if 0 < int(row["minimumMonths"]) <= 120})
    for months in thresholds:
        shortest = 10**9
        longest = -1
        for year in range(2024, 2028):
            for month in range(1, 13):
                for day in range(1, calendar.monthrange(year, month)[1] + 1):
                    start = date(year, month, day)
                    needed_days = (_add_months(start, months) - start).days + 1
                    shortest = min(shortest, needed_days)
                    longest = max(longest, needed_days)
        if shortest <= duration_days < longest:
            return True
    return False


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

    # Workplace determination runs BEFORE the fine-snapshot resolution: its
    # terminal outcomes (no breach, administrative-fine track, unresolved
    # regime) do not depend on the 범칙금 snapshot at all, and must not be
    # masked by HISTORICAL_RULE_UNAVAILABLE for incidents that predate the
    # verified fine snapshot (e.g. a report filed in time in 2025). Only the
    # PERMIT fine calculation itself needs the snapshot.
    determination = None
    workplace_codes = [case.violation_code] if case.violation_code else case.violation_candidates
    workplace_gate = bool(set(workplace_codes) & WORKPLACE_VIOLATION_CODES) and (
        bool(case.violation_code) or set(workplace_codes).issubset(WORKPLACE_VIOLATION_CODES)
    )
    if workplace_gate:
        determination = determine_workplace_regime(case)

    snapshot = _resolve_snapshot(case, database)

    if determination is not None:
        in_engine_scope = not case.status_of_stay or bool(
            _REPORT_PROVISO_STATUS_RE.match(case.status_of_stay)
        )
        if determination.regime == "UNRESOLVED" and not in_engine_scope:
            # Outside the verified notice scope (e.g. E-9): keep the legacy
            # path, but never let the old status-only proviso note imply a
            # classification this engine did not make.
            determination = None

    if determination is not None:
        common = dict(
            violation_code=case.violation_code,
            legal_snapshot_id=snapshot["id"] if snapshot else None,
            effective_from=date.fromisoformat(snapshot["effectiveFrom"]) if snapshot else None,
            sources=_source_refs(snapshot) if snapshot else list(determination.evidence),
            workplace_determination=determination,
        )
        if determination.regime == "NOT_APPLICABLE" or (
            determination.determination_status in {"CONFIRMED", "USER_CONFIRMED"}
            and determination.duty_breach == "NOT_ESTABLISHED"
        ):
            return LegalBaseline(
                status="NOT_APPLICABLE",
                assumptions=[
                    "확인된 사실만으로는 근무처 변경·추가 의무 위반이 성립하지 않아 범칙금·과태료를 계산하지 않습니다."
                ],
                confidence="HIGH",
                **common,
            )
        if determination.regime == "REPORT" and determination.determination_status in {
            "CONFIRMED",
            "USER_CONFIRMED",
        }:
            return LegalBaseline(
                status="ADMINISTRATIVE_FINE_TRACK",
                statutory_maximum_krw=determination.administrative_fine_statutory_maximum_krw,
                applied_rules=[
                    "출입국관리법 제21조제1항 단서(사후신고 의무)",
                    "출입국관리법 시행령 제26조의2",
                    "법무부고시 제2020-212호(신고 대상 요건)",
                    "출입국관리법 제100조제1항제3호(과태료, 200만원 이하)",
                ],
                missing_facts=list(determination.missing_facts),
                assumptions=[
                    "사후신고 의무 위반은 범칙금이 아니라 과태료 검토 대상입니다. "
                    "위 금액은 법정 상한이며, 검증된 과태료 양정기준이 없어 구체적인 산정액은 제시하지 않습니다."
                ],
                confidence="HIGH" if determination.duty_breach == "ESTABLISHED" else "INSUFFICIENT",
                **common,
            )
        if determination.regime == "UNRESOLVED" and "사건 당시 고시 버전" not in determination.missing_facts:
            return LegalBaseline(
                status="MISSING_FACTS",
                missing_facts=[
                    "근무처 변경·추가가 사전허가 대상인지 사후신고 대상인지 확정할 수 없습니다.",
                    *determination.missing_facts,
                ],
                confidence="INSUFFICIENT",
                **common,
            )
        if (
            determination.regime == "PERMIT"
            and determination.determination_status == "CONFIRMED"
            and determination.duty_breach == "UNRESOLVED"
        ):
            # An engine-confirmed permission duty with an unproven breach
            # must not reach the fine table: whether a permit was obtained
            # is the very fact that decides liability, so no amount — not
            # even a "conditional" one — is shown. (A user-confirmed regime
            # keeps the legacy conditional-calculation contract below.)
            return LegalBaseline(
                status="MISSING_FACTS",
                missing_facts=[
                    "근무처 변경·추가 허가를 받았는지 확인되지 않았습니다.",
                    *determination.missing_facts,
                ],
                confidence="INSUFFICIENT",
                **common,
            )
        if not case.violation_code and determination.determination_status == "USER_CONFIRMED":
            # Shared-candidate pricing must not bypass the gate: with no
            # resolved provision, a user-confirmed regime alone does not
            # price the case through the identical-tier shortcut. The
            # engine-confirmed and single-provision paths are unaffected.
            return LegalBaseline(
                status="MISSING_FACTS",
                missing_facts=[
                    "적용 조문이 확정되지 않아, 사용자 확인만으로는 조건부 계산을 하지 않습니다.",
                    *determination.missing_facts,
                ],
                confidence="INSUFFICIENT",
                **common,
            )

    if snapshot is None:
        return LegalBaseline(
            status="HISTORICAL_RULE_UNAVAILABLE",
            violation_code=case.violation_code,
            missing_facts=["해당 위반기간 전체에 적용되는 법령 기준"],
            confidence="INSUFFICIENT",
            workplace_determination=determination,
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

    if not (case.violation_start_date and case.violation_end_date) and _ambiguous_calendar_boundary(rule["tiers"], duration):
        return LegalBaseline(
            status="MISSING_FACTS",
            violation_code=case.violation_code,
            violation_label=rule["label"],
            legal_snapshot_id=snapshot["id"],
            effective_from=date.fromisoformat(snapshot["effectiveFrom"]),
            missing_facts=["월 단위 범칙금 구간의 경계입니다. 정확한 위반 시작일과 종료일이 필요합니다."],
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
    if determination is not None and determination.regime == "PERMIT":
        if determination.determination_status == "USER_CONFIRMED":
            assumptions.append(PERMIT_CONFIRMATION_NOTE)
        elif determination.determination_status == "CONFIRMED":
            assumptions.append(
                "법무부고시 제2020-212호 요건·적용제외를 확인한 결과 사전허가 대상으로 판별되어 범칙금 기준으로 계산했습니다."
            )
    elif _report_proviso_applies(case.status_of_stay, codes):
        assumptions.append(PERMIT_CONFIRMATION_NOTE)
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
        workplace_determination=determination,
    )
