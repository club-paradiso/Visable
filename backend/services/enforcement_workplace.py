"""Deterministic workplace change/addition regime determination.

Separates three questions the legacy UI collapsed into one direct question
("사전허가 대상인지 사후신고 대상인지 확인하셨나요?"):

1. Facts — what actually happened (StructuredCase workplace fact fields).
2. Duty — which procedure the law required (this module, from the verified
   rule store built on MOJ Notice 2020-212, Immigration Act Art.21 and
   Enforcement Decree Art.26-2).
3. Breach — whether that duty was actually breached (procedure status,
   report deadline), evaluated independently of the classification.

Hard rules (mirrored in lib/enforcement-workplace.js; parity is tested
against backend/tests/fixtures/workplace_regime_cases.json):

- E-1~E-7 status alone NEVER confirms REPORT. Every notice requirement and
  every notice exclusion must be checked against stated facts.
- E-7 subtype alone never confirms anything: the occupation code decides
  the notice exclusion check.
- A workplace move alone never confirms a breach.
- Unknown facts stay unknown (None); they are reported in missing_facts,
  never coerced to False.
- The administrative-fine (과태료) track exposes only the verified statutory
  maximum (Act Art.100(1)(3), KRW 2,000,000). No verified administrative-fine
  schedule exists in the rule store, so no amount is ever computed for it.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from .enforcement_models import SourceReference, StructuredCase, WorkplaceDetermination

RULES_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "enforcement" / "workplace_regime_rules.json"
)

WORKPLACE_VIOLATION_CODES = {
    "UNAUTHORIZED_EMPLOYMENT_ART18_2",
    "UNAUTHORIZED_WORKPLACE_CHANGE_ART21_1",
}

_ELIGIBLE_STATUS_RE = re.compile(r"^E-[1-7](?:-|$)", re.I)
_OWN_FAULT_REASONS = {"DISMISSED_OWN_FAULT", "RESIGNED_MID_CONTRACT"}
_CLEAR_NON_OWN_FAULT_REASONS = {
    "CONTRACT_EXPIRED",
    "DISMISSED_NO_OWN_FAULT",
    "EMPLOYER_CLOSED",
    "NOT_ENDED",
}

# Plain-language follow-up question for each missing fact key.
NEXT_QUESTIONS = {
    "체류자격": "변경 당시 어떤 비자(체류자격)로 체류했나요?",
    "실제 직종(직종코드)": "새 근무처에서 실제로 어떤 일을 하나요? 직종코드(예: 441)를 알면 알려 주세요.",
    "E-6 세부 유형": "E-6 중 호텔·유흥시설 공연(E-6-2)에 해당하나요?",
    "해외 온라인상품판매원 해당 여부": "해외 온라인상품 판매 업무를 하나요?",
    "외국인등록 여부": "당시 외국인등록을 하고 체류 중이었나요?",
    "외국인등록 전 신고 예외(1회) 사용 여부": "외국인등록 전에 신고할 수 있는 예외(1회)를 이전에 사용한 적이 있나요?",
    "새 근무처 자격요건 충족 여부": "새 근무처에서 일하는 데 필요한 자격요건(학위·자격 등)을 갖추었나요?",
    "이전 고용 종료 사유": "이전 회사는 왜 그만두게 됐나요? (계약 만료, 본인이 중도에 그만둠, 해고, 회사 폐업 등)",
    "원 고용주 이적 동의 여부": "이전 회사에서 다른 회사로 옮기는 것에 동의받았나요?",
    "근무처 변경일": "새 근무처로 옮기거나 추가한 날짜가 언제인가요?",
    "신고일": "출입국관서에 신고한 날짜가 언제인가요?",
    "허가 취득 여부": "근무를 시작하기 전에 출입국관서에서 근무처 변경·추가 허가를 받았나요?",
    "행정 절차 진행 여부": "출입국관서에 허가 신청이나 신고를 한 적이 있나요?",
    "사건 당시 고시 버전": "사건 날짜를 기준으로 당시 시행 고시를 확인해야 합니다. 변경 날짜를 알려 주세요.",
}


@lru_cache(maxsize=4)
def load_workplace_rules(path: Optional[str] = None) -> Dict[str, Any]:
    target = Path(path) if path else RULES_PATH
    data = json.loads(target.read_text(encoding="utf-8"))
    if data.get("verificationStatus") != "VERIFIED_OFFICIAL_SNAPSHOT":
        raise ValueError("workplace regime rule store is not a verified official snapshot")
    if not data.get("reportEligibility") or not data.get("sources"):
        raise ValueError("workplace regime rule store is incomplete")
    return data


def is_workplace_case(case: StructuredCase) -> bool:
    codes = {case.violation_code} if case.violation_code else set(case.violation_candidates or [])
    if codes & WORKPLACE_VIOLATION_CODES:
        return True
    return bool(
        case.workplace_change_type
        or case.workplace_change_date
        or case.occupation_code
        or case.procedure_status
    )


def _evidence(rules: Dict[str, Any]) -> list[SourceReference]:
    refs = []
    for source in rules.get("sources", []):
        refs.append(
            SourceReference(
                id=f"workplace-regime:{source['id']}",
                authority=source["authority"],
                title=source["lawName"],
                article=source.get("article"),
                effective_date=date.fromisoformat(source["effectiveFrom"]),
                url=source["url"],
                verified_at=date.fromisoformat(rules["verifiedAt"]),
            )
        )
    return refs


def _normalize_occupation(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    # Users type codes with separators ("S-740", "s 740"); the notice lists
    # them without. Strip separators so a formatting variant can never
    # escape the exclusion list.
    return re.sub(r"[\s.\-]+", "", str(value)).upper() or None


def _assess_breach(case: StructuredCase, regime: str, det: WorkplaceDetermination, rules: Dict[str, Any]) -> None:
    """Evaluate duty breach separately from classification. Mutates det."""
    procedure = case.procedure_status
    if regime == "PERMIT":
        det.penalty_track = "CRIMINAL_FINE"
        # An explicitly stated procedure always outranks the legacy
        # authorized flag. In particular a REPORT filing is not a permit:
        # it can never satisfy the prior-permission duty (a narrative like
        # "신고했어요" also sets the legacy flag, which used to mask this).
        if procedure == "PERMIT_GRANTED":
            det.duty_breach = "NOT_ESTABLISHED"
        elif procedure == "APPLIED_PENDING":
            det.duty_breach = "UNRESOLVED"
            det.warnings.append("허가 신청만으로는 허가를 받은 것이 아닙니다. 처리 결과가 확인되어야 합니다.")
        elif procedure in {"REPORT_FILED", "NONE"}:
            det.duty_breach = "ESTABLISHED"
        elif case.workplace_change_authorized is True:
            det.duty_breach = "NOT_ESTABLISHED"
        elif case.workplace_change_authorized is False:
            det.duty_breach = "ESTABLISHED"
        else:
            det.duty_breach = "UNRESOLVED"
            if "허가 취득 여부" not in det.missing_facts:
                det.missing_facts.append("허가 취득 여부")
        return
    if regime == "REPORT":
        det.penalty_track = "ADMINISTRATIVE_FINE"
        det.administrative_fine_statutory_maximum_krw = int(rules["reportDuty"]["statutoryMaximumKrw"])
        deadline_days = int(rules["reportDuty"]["deadlineDays"])
        change_date = case.workplace_change_date or case.new_workplace_start_date or case.violation_start_date
        if change_date:
            det.report_deadline_date = change_date + timedelta(days=deadline_days)
        if procedure == "REPORT_FILED":
            report_date = case.application_or_report_date
            if report_date and change_date:
                if report_date <= det.report_deadline_date:
                    det.report_timeliness = "WITHIN_DEADLINE"
                    det.duty_breach = "NOT_ESTABLISHED"
                else:
                    det.report_timeliness = "LATE"
                    det.duty_breach = "ESTABLISHED"
            else:
                det.report_timeliness = "UNKNOWN"
                det.duty_breach = "UNRESOLVED"
                if not change_date:
                    det.missing_facts.append("근무처 변경일")
                if not report_date:
                    det.missing_facts.append("신고일")
        elif procedure == "NONE":
            reference = case.assessment_date or date.today()
            if change_date and reference > det.report_deadline_date:
                det.report_timeliness = "NOT_REPORTED_DEADLINE_PASSED"
                det.duty_breach = "ESTABLISHED"
            else:
                det.report_timeliness = "UNKNOWN"
                det.duty_breach = "UNRESOLVED"
                if not change_date:
                    det.missing_facts.append("근무처 변경일")
                else:
                    det.warnings.append("아직 신고기한(변경일부터 15일)이 지나지 않았을 수 있어 위반으로 확정하지 않습니다.")
        elif procedure == "PERMIT_GRANTED":
            det.duty_breach = "NOT_ESTABLISHED"
            det.warnings.append("사전허가를 받았다면 신고의무 위반 쟁점은 별도로 발생하지 않습니다.")
        else:
            det.report_timeliness = "UNKNOWN"
            det.duty_breach = "UNRESOLVED"
            if "행정 절차 진행 여부" not in det.missing_facts:
                det.missing_facts.append("행정 절차 진행 여부")


def _finish(det: WorkplaceDetermination) -> WorkplaceDetermination:
    det.missing_facts = list(dict.fromkeys(det.missing_facts))
    det.next_questions = [
        NEXT_QUESTIONS[fact] for fact in det.missing_facts if fact in NEXT_QUESTIONS
    ]
    return det


def _engine_determine(case: StructuredCase, rules: Dict[str, Any]) -> WorkplaceDetermination:
    eligibility = rules["reportEligibility"]
    det = WorkplaceDetermination(
        regime="UNRESOLVED",
        determination_status="UNRESOLVED",
        determination_source="ENGINE",
        effective_law_version=(
            f"{rules['sources'][0]['lawName']} ({rules['sources'][0].get('noticeNo', '')}, "
            f"시행 {rules['sources'][0]['effectiveFrom']})"
        ),
        evidence=_evidence(rules),
        applicable_rules=[
            "출입국관리법 제21조제1항(본문: 사전허가 / 단서: 대통령령으로 정하는 사람의 15일 이내 사후신고)",
            "출입국관리법 시행령 제26조의2제1항(신고 대상: E-1~E-7 중 법무부장관 고시 요건 충족자)",
            "법무부고시 제2020-212호(신고만으로 근무처 변경·추가를 할 수 있는 외국인의 요건)",
        ],
    )

    if case.workplace_change_type == "SAME_EMPLOYER_SITE_ONLY":
        det.warnings.append(
            "같은 고용주 안에서 근무 장소만 바뀐 경우도 근무처 변경에 해당할 수 있어, 비대상이라고 단정하지 않습니다."
        )

    status = (case.status_of_stay or "").upper()
    if not status:
        det.missing_facts.append("체류자격")
        return _finish(det)
    det.verified_facts.append(f"체류자격 {status}")

    change_date = case.workplace_change_date or case.new_workplace_start_date or case.violation_start_date
    notice_source = next(s for s in rules["sources"] if s["id"] == "moj-notice-2020-212")
    notice_effective = date.fromisoformat(notice_source["effectiveFrom"])
    if change_date and change_date < notice_effective:
        det.missing_facts.append("사건 당시 고시 버전")
        det.human_review_reason = (
            "근무처 변경일이 고시 제2020-212호 시행일(2020-06-22)보다 빨라, 사건 당시 고시 버전을 "
            "검증된 스냅샷으로 확인할 수 없습니다."
        )
        return _finish(det)

    if status in eligibility["excludedStatuses"]:
        det.regime = "PERMIT"
        det.determination_status = "CONFIRMED"
        det.exceptions_checked.append(
            "고시 적용제외: 예술흥행(E-6) 중 호텔업시설·유흥업소 등 공연 종사자(E-6-2)는 신고 대상에서 제외"
        )
        det.verified_facts.append("E-6-2는 고시상 신고 적용제외 대상")
        _assess_breach(case, "PERMIT", det, rules)
        return _finish(det)

    if not _ELIGIBLE_STATUS_RE.match(status):
        det.human_review_reason = (
            "검증된 고시 규칙은 E-1~E-7 체류자격의 신고 대상 판별만 다룹니다. "
            "그 밖의 체류자격은 이 엔진으로 사전허가/사후신고를 확정하지 않습니다."
        )
        return _finish(det)

    unresolved = False

    # --- Notice exclusion: E-7 occupations subject to prior management.
    if status.startswith("E-7"):
        occupation = _normalize_occupation(case.occupation_code)
        if occupation is None:
            det.missing_facts.append("실제 직종(직종코드)")
            unresolved = True
        elif occupation in eligibility["conditionalOccupationCodesE7"]:
            # Code 2742 is excluded only for overseas online product
            # sellers. That fact has its own field; unknown stays unknown.
            if case.overseas_online_seller is True:
                det.regime = "PERMIT"
                det.determination_status = "CONFIRMED"
                det.exceptions_checked.append(
                    "고시 적용제외: E-7 직종코드 2742 중 해외 온라인상품판매원은 신고 대상에서 제외"
                )
                det.verified_facts.append("직종코드 2742 · 해외 온라인상품판매원")
                _assess_breach(case, "PERMIT", det, rules)
                return _finish(det)
            elif case.overseas_online_seller is False:
                det.exceptions_checked.append("직종코드 2742이나 해외 온라인상품판매원이 아니어서 조건부 적용제외에 해당하지 않음")
                det.verified_facts.append(f"직종코드 {occupation}")
            else:
                det.missing_facts.append("해외 온라인상품판매원 해당 여부")
                unresolved = True
        elif occupation in eligibility["excludedOccupationCodesE7"]:
            det.regime = "PERMIT"
            det.determination_status = "CONFIRMED"
            det.exceptions_checked.append(
                f"고시 적용제외: E-7 직종코드 {occupation}는 사전관리가 필요한 직종으로 신고 대상에서 제외"
            )
            det.verified_facts.append(f"직종코드 {occupation}")
            _assess_breach(case, "PERMIT", det, rules)
            return _finish(det)
        else:
            det.exceptions_checked.append(f"E-7 직종코드 {occupation}는 고시 적용제외 목록에 없음")
            det.verified_facts.append(f"직종코드 {occupation}")
    elif status.startswith("E-6"):
        # Only E-6-2 is excluded; a bare "E-6" does not prove the subtype,
        # and neither does an unlisted subtype code.
        if status == "E-6" or status not in {"E-6-1", "E-6-3"}:
            det.missing_facts.append("E-6 세부 유형")
            unresolved = True
        else:
            det.exceptions_checked.append("E-6-2가 아닌 E-6 세부 유형은 고시 적용제외에 해당하지 않음")

    # --- Notice requirement: alien registration (with the no-fault exception).
    end_reason = case.previous_employment_end_reason
    if case.alien_registered is None:
        det.missing_facts.append("외국인등록 여부")
        unresolved = True
    elif case.alien_registered is False:
        # Notice proviso: where the contract ended without the person's own
        # fault (no-fault dismissal, closure, or expiry of the contract
        # term), a report is allowed once even before alien registration.
        # "Once" is a real condition: prior use must be asked, never assumed.
        if end_reason in {"DISMISSED_NO_OWN_FAULT", "EMPLOYER_CLOSED", "CONTRACT_EXPIRED"}:
            if case.registration_exception_used is True:
                det.regime = "PERMIT"
                det.determination_status = "CONFIRMED"
                det.exceptions_checked.append(
                    "고시 단서: 외국인등록 전 신고 허용(1회)을 이미 사용해, 등록 전 신고 대상에 해당하지 않음"
                )
                _assess_breach(case, "PERMIT", det, rules)
                return _finish(det)
            elif case.registration_exception_used is False:
                det.exceptions_checked.append(
                    "고시 단서: 본인 귀책사유 없이 고용계약이 종료된 경우 외국인등록 전이라도 1회에 한해 신고 허용"
                )
                det.verified_facts.append("외국인등록 전 신고 예외(1회) 미사용")
            else:
                det.missing_facts.append("외국인등록 전 신고 예외(1회) 사용 여부")
                unresolved = True
        elif end_reason in {"DISMISSED_OWN_FAULT", "RESIGNED_MID_CONTRACT"}:
            det.regime = "PERMIT"
            det.determination_status = "CONFIRMED"
            det.exceptions_checked.append("고시 자격요건: 외국인등록을 하고 체류 중이어야 한다는 요건 미충족")
            _assess_breach(case, "PERMIT", det, rules)
            return _finish(det)
        else:
            # None / UNKNOWN / OTHER: the end reason decides whether the
            # no-fault exception can apply, so nothing is concluded yet.
            det.missing_facts.append("이전 고용 종료 사유")
            unresolved = True
    else:
        det.verified_facts.append("외국인등록 후 체류 중")

    # --- Notice requirement: qualifications for the new workplace activity.
    if case.meets_new_workplace_qualifications is None:
        det.missing_facts.append("새 근무처 자격요건 충족 여부")
        unresolved = True
    elif case.meets_new_workplace_qualifications is False:
        det.regime = "PERMIT"
        det.determination_status = "CONFIRMED"
        det.exceptions_checked.append("고시 자격요건: 변경·추가되는 근무처 활동에 필요한 자격요건을 갖추어야 함")
        det.warnings.append("새 근무처 자격요건 미충족 자체는 체류자격 범위 문제로 별도 검토가 필요할 수 있습니다.")
        _assess_breach(case, "PERMIT", det, rules)
        return _finish(det)
    else:
        det.verified_facts.append("새 근무처 자격요건 충족")

    # --- Notice exclusion: own-fault dismissal / mid-contract resignation
    # without the former employer's transfer consent.
    if case.workplace_change_type == "ADDITION" or end_reason == "NOT_ENDED":
        det.exceptions_checked.append("기존 고용이 유지되는 근무처 추가는 '해고·중도퇴직' 적용제외와 무관")
    elif end_reason in _OWN_FAULT_REASONS:
        if case.employer_consent is True:
            det.exceptions_checked.append("본인 귀책 해고·중도퇴직이나 원 고용주 이적 동의를 받아 적용제외에 해당하지 않음")
            det.verified_facts.append("원 고용주 이적 동의 있음")
        elif case.employer_consent is False:
            det.regime = "PERMIT"
            det.determination_status = "CONFIRMED"
            det.exceptions_checked.append(
                "고시 적용제외: 본인 귀책사유로 해고 또는 중도 퇴직하고 원 고용주의 이적 동의를 받지 못한 자"
            )
            _assess_breach(case, "PERMIT", det, rules)
            return _finish(det)
        else:
            det.missing_facts.append("원 고용주 이적 동의 여부")
            unresolved = True
    elif end_reason in _CLEAR_NON_OWN_FAULT_REASONS:
        det.exceptions_checked.append("계약만료·본인 귀책 없는 해고·폐업 등은 고시의 본인귀책 적용제외에 해당하지 않음")
    else:
        det.missing_facts.append("이전 고용 종료 사유")
        unresolved = True

    if unresolved:
        det.human_review_reason = (
            "고시 요건 중 확인되지 않은 항목이 있어 사전허가/사후신고를 확정할 수 없습니다. "
            "확인되지 않은 요건을 충족한 것으로 가정하지 않습니다."
        )
        return _finish(det)

    det.regime = "REPORT"
    det.determination_status = "CONFIRMED"
    det.verified_facts.append("법무부고시 제2020-212호의 신고 대상 요건을 모두 충족하고 적용제외에 해당하지 않음")
    _assess_breach(case, "REPORT", det, rules)
    return _finish(det)


def determine_workplace_regime(
    case: StructuredCase, *, rules: Optional[Dict[str, Any]] = None
) -> WorkplaceDetermination:
    """Full determination: no-work guard, engine, then user confirmation."""
    rules = rules or load_workplace_rules()

    # A workplace the user never actually started working at cannot ground a
    # work-based workplace-change violation, whatever the regime would be.
    if case.actually_started_work is False:
        det = WorkplaceDetermination(
            regime="NOT_APPLICABLE",
            determination_status="NOT_APPLICABLE",
            determination_source="ENGINE",
            verified_facts=["새 근무처에서 실제로 근무를 시작하지 않음"],
            applicable_rules=["출입국관리법 제21조(근무처 변경·추가) — 실제 근무 사실이 전제"],
            penalty_track="NONE",
            duty_breach="NOT_ESTABLISHED",
            evidence=_evidence(rules),
            warnings=["실제로 근무하지 않았다면 근무를 전제로 한 범칙금·과태료 계산은 하지 않습니다."],
        )
        return _finish(det)

    engine = _engine_determine(case, rules)

    user_regime = case.workplace_regime if case.workplace_regime in {"PERMIT", "REPORT"} else None
    # Legacy contract (documented): a regime value with source None predates
    # the provenance field and is treated as user-confirmed. The pydantic
    # Literal on workplace_regime_source constrains the value space to
    # USER_CONFIRMED / ENGINE / None, so no other provenance can reach here;
    # the JS mirror cannot rely on schema validation and checks explicitly.
    user_confirmed = user_regime is not None and case.workplace_regime_source != "ENGINE"
    if user_confirmed:
        if engine.determination_status == "CONFIRMED" and engine.regime != user_regime:
            engine.warnings.append(
                "관할관서에서 확인받았다는 내용과 검증된 고시 규칙의 판별이 다릅니다. "
                "고시 규칙 판별을 우선 표시하니, 관할 출입국·외국인관서에서 최종 확인해 주세요."
            )
            engine.human_review_reason = "사용자 확인과 결정론적 판별이 충돌합니다."
            return _finish(engine)
        if engine.determination_status != "CONFIRMED":
            det = WorkplaceDetermination(
                regime=user_regime,
                determination_status="USER_CONFIRMED",
                determination_source="USER_CONFIRMED",
                verified_facts=list(engine.verified_facts),
                missing_facts=list(engine.missing_facts),
                applicable_rules=list(engine.applicable_rules),
                exceptions_checked=list(engine.exceptions_checked),
                effective_law_version=engine.effective_law_version,
                evidence=_evidence(rules),
                warnings=[
                    "사용자가 관할관서에서 확인한 구분을 전제로 합니다. Visable이 법적으로 확정한 분류가 아닙니다."
                ],
                human_review_reason=engine.human_review_reason,
            )
            _assess_breach(case, user_regime, det, rules)
            return _finish(det)
    return _finish(engine)
