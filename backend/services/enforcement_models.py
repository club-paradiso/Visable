"""Typed public contracts for Visable enforcement intelligence.

The models deliberately separate a reproducible legal baseline from an
evidence-grounded prediction.  Public serialization always uses camelCase and
never includes the user's raw narrative.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(piece[:1].upper() + piece[1:] for piece in rest)


class EnforcementModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
        protected_namespaces=(),
    )

    def public_dict(self, *, exclude_none: bool = True) -> Dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json", exclude_none=exclude_none)


Confidence = Literal["VERY_HIGH", "HIGH", "MEDIUM", "LOW", "VERY_LOW", "INSUFFICIENT"]
Likelihood = Literal["VERY_LOW", "LOW", "MODERATE", "HIGH", "VERY_HIGH", "UNKNOWN"]
GroundingBasis = Literal["SUPPORTED", "INFERRED", "UNKNOWN"]


class StructuredCase(EnforcementModel):
    schema_version: Literal["1"] = "1"
    status_of_stay: Optional[str] = None
    nationality: Optional[str] = None
    violation_code: Optional[str] = None
    violation_candidates: List[str] = Field(default_factory=list)
    activity: Optional[str] = None
    workplace_type: Optional[str] = None
    authorization_obtained: Optional[bool] = None
    workplace_change_authorized: Optional[bool] = None
    # Regime claimed/confirmed for a workplace change/addition case. PERMIT and
    # REPORT keep their #761 meaning; NOT_APPLICABLE and UNRESOLVED are produced
    # by the deterministic determination engine (enforcement_workplace.py) or
    # left unset. A regime value alone never proves a duty was breached: the
    # breach conditions live in WorkplaceDetermination / the baseline guards.
    workplace_regime: Optional[Literal["PERMIT", "REPORT", "NOT_APPLICABLE", "UNRESOLVED"]] = None
    # Who produced workplace_regime: the user confirming with the competent
    # office, or the deterministic engine. AI extraction must never set this.
    workplace_regime_source: Optional[Literal["USER_CONFIRMED", "ENGINE"]] = None
    # --- Workplace-change facts (P0/P1). All optional; unknown stays None and
    # is never coerced to False. Facts, legal duty and duty breach stay separate.
    occupation_code: Optional[str] = None
    workplace_change_type: Optional[
        Literal["CHANGE", "ADDITION", "SAME_EMPLOYER_SITE_ONLY", "UNKNOWN"]
    ] = None
    previous_employment_end_reason: Optional[
        Literal[
            "CONTRACT_EXPIRED",
            "RESIGNED_MID_CONTRACT",
            "DISMISSED_OWN_FAULT",
            "DISMISSED_NO_OWN_FAULT",
            "EMPLOYER_CLOSED",
            "NOT_ENDED",
            "OTHER",
            "UNKNOWN",
        ]
    ] = None
    employer_consent: Optional[bool] = None
    alien_registered: Optional[bool] = None
    meets_new_workplace_qualifications: Optional[bool] = None
    actually_started_work: Optional[bool] = None
    new_workplace_start_date: Optional[date] = None
    workplace_change_date: Optional[date] = None
    application_or_report_date: Optional[date] = None
    procedure_status: Optional[
        Literal["PERMIT_GRANTED", "REPORT_FILED", "APPLIED_PENDING", "NONE", "UNKNOWN"]
    ] = None
    duration_days: Optional[int] = Field(default=None, ge=0, le=36500)
    violation_start_date: Optional[date] = None
    violation_end_date: Optional[date] = None
    assessment_date: Optional[date] = None
    prior_violations: Optional[int] = Field(default=None, ge=0, le=100)
    voluntary_disclosure: Optional[bool] = None
    investigation_started: Optional[bool] = None
    employer_involvement: Optional[bool] = None
    false_representation: Optional[bool] = None
    ability_to_pay: Optional[str] = None
    unknown_facts: List[str] = Field(default_factory=list)
    extraction_warnings: List[str] = Field(default_factory=list)

    @field_validator("status_of_stay")
    @classmethod
    def normalize_status(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value

    @model_validator(mode="after")
    def validate_dates(self) -> "StructuredCase":
        if self.violation_start_date and self.violation_end_date:
            if self.violation_end_date < self.violation_start_date:
                raise ValueError("violationEndDate must not precede violationStartDate")
        return self


class SourceReference(EnforcementModel):
    id: str
    authority: str
    title: str
    article: Optional[str] = None
    effective_date: Optional[date] = None
    url: str
    verified_at: Optional[date] = None


class MoneyRange(EnforcementModel):
    minimum_krw: int = Field(ge=0)
    maximum_krw: int = Field(ge=0)
    currency: Literal["KRW"] = "KRW"

    @model_validator(mode="after")
    def ordered(self) -> "MoneyRange":
        if self.minimum_krw > self.maximum_krw:
            raise ValueError("minimumKrw must not exceed maximumKrw")
        return self


WorkplaceRegime = Literal["PERMIT", "REPORT", "NOT_APPLICABLE", "UNRESOLVED"]


class WorkplaceDetermination(EnforcementModel):
    """Deterministic permit/report determination for a workplace change case.

    Produced only by enforcement_workplace.determine_workplace_regime (or its
    JS mirror). Separates three questions the old UI collapsed into one:
    what happened (facts), which duty applied (regime), and whether that duty
    was breached (duty_breach / report_timeliness).
    """

    regime: WorkplaceRegime = "UNRESOLVED"
    determination_status: Literal["CONFIRMED", "USER_CONFIRMED", "UNRESOLVED", "NOT_APPLICABLE"] = "UNRESOLVED"
    determination_source: Literal["ENGINE", "USER_CONFIRMED", "NONE"] = "NONE"
    verified_facts: List[str] = Field(default_factory=list)
    missing_facts: List[str] = Field(default_factory=list)
    applicable_rules: List[str] = Field(default_factory=list)
    exceptions_checked: List[str] = Field(default_factory=list)
    effective_law_version: Optional[str] = None
    evidence: List[SourceReference] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    next_questions: List[str] = Field(default_factory=list)
    human_review_reason: Optional[str] = None
    penalty_track: Literal["CRIMINAL_FINE", "ADMINISTRATIVE_FINE", "NONE", "UNRESOLVED"] = "UNRESOLVED"
    # Duty-breach assessment, independent of the regime classification.
    duty_breach: Literal["ESTABLISHED", "NOT_ESTABLISHED", "UNRESOLVED"] = "UNRESOLVED"
    report_deadline_date: Optional[date] = None
    report_timeliness: Optional[
        Literal["WITHIN_DEADLINE", "LATE", "NOT_REPORTED_DEADLINE_PASSED", "UNKNOWN"]
    ] = None
    # For the administrative-fine track this is the statutory maximum only
    # (Act Art.100(1): up to KRW 2,000,000). It is NOT a computed amount; no
    # verified administrative-fine schedule exists in the rule store.
    administrative_fine_statutory_maximum_krw: Optional[int] = Field(default=None, ge=0)


class LegalBaseline(EnforcementModel):
    status: Literal[
        "AVAILABLE",
        "MISSING_FACTS",
        "UNSUPPORTED",
        "HISTORICAL_RULE_UNAVAILABLE",
        "ADMINISTRATIVE_FINE_TRACK",
        "NOT_APPLICABLE",
    ]
    violation_code: Optional[str] = None
    violation_label: Optional[str] = None
    baseline_amount_krw: Optional[int] = Field(default=None, ge=0)
    legally_adjustable_range: Optional[MoneyRange] = None
    statutory_maximum_krw: Optional[int] = Field(default=None, ge=0)
    duration_days: Optional[int] = Field(default=None, ge=0)
    legal_snapshot_id: Optional[str] = None
    effective_from: Optional[date] = None
    applied_rules: List[str] = Field(default_factory=list)
    legally_available_dispositions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    missing_facts: List[str] = Field(default_factory=list)
    sources: List[SourceReference] = Field(default_factory=list)
    confidence: Confidence = "INSUFFICIENT"
    workplace_determination: Optional[WorkplaceDetermination] = None


class PredictionFactor(EnforcementModel):
    code: str
    label: str
    direction: Literal["AGGRAVATING", "MITIGATING", "NEUTRAL", "UNRESOLVED"]
    basis: GroundingBasis
    evidence_ids: List[str] = Field(default_factory=list)


class EvidenceItem(EnforcementModel):
    id: str
    source_type: Literal["STATUTE", "REGULATION", "OFFICIAL_GUIDANCE", "COURT", "ADMINISTRATIVE_DECISION", "OFFICIAL_CASE"]
    title: str
    authority: str
    source_date: Optional[date] = None
    source_url: str
    excerpt: Optional[str] = None
    citation_grade: Literal["DIRECT", "CONTEXTUAL", "BACKGROUND"]
    result_kind: Literal["LEGAL_RULE", "BODY_RESULT"]
    applicable: bool = True


class SimilarCaseReference(EnforcementModel):
    id: str
    source_type: Literal["COURT", "ADMINISTRATIVE_DECISION", "OFFICIAL_CASE", "OTHER_VERIFIED"]
    similarity_score: Optional[float] = Field(default=None, ge=0, le=1)
    matching_factors: List[str] = Field(default_factory=list)
    differing_factors: List[str] = Field(default_factory=list)
    outcome_summary: str
    monetary_outcome_krw: Optional[int] = Field(default=None, ge=0)
    disposition_outcome: Optional[str] = None
    source_title: Optional[str] = None
    source_date: Optional[date] = None
    source_url: str
    evidence_id: str


class EnforcementEvidencePack(EnforcementModel):
    evidence: List[EvidenceItem] = Field(default_factory=list)
    similar_cases: List[SimilarCaseReference] = Field(default_factory=list)
    retrieval_status: Literal["AVAILABLE", "LIMITED", "UNAVAILABLE"]
    limitations: List[str] = Field(default_factory=list)


class PredictionConfidence(EnforcementModel):
    level: Confidence
    reasons: List[str] = Field(default_factory=list)


class MonetaryPrediction(EnforcementModel):
    legal_baseline_amount_krw: Optional[int] = Field(default=None, ge=0)
    legal_range: MoneyRange
    predicted_likely_range: Optional[MoneyRange] = None
    point_estimate_krw: Optional[int] = Field(default=None, ge=0)
    predicted_direction: Literal["MITIGATED", "BASELINE", "AGGRAVATED", "UNCERTAIN"] = "UNCERTAIN"
    confidence: PredictionConfidence
    rationale: List[PredictionFactor] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_monetary_bounds(self) -> "MonetaryPrediction":
        predicted = self.predicted_likely_range
        if predicted:
            if predicted.minimum_krw < self.legal_range.minimum_krw or predicted.maximum_krw > self.legal_range.maximum_krw:
                raise ValueError("predictedLikelyRange must stay inside legalRange")
            if self.point_estimate_krw is not None and not (
                predicted.minimum_krw <= self.point_estimate_krw <= predicted.maximum_krw
            ):
                raise ValueError("pointEstimateKrw must stay inside predictedLikelyRange")
        elif self.point_estimate_krw is not None:
            raise ValueError("pointEstimateKrw requires predictedLikelyRange")
        return self


class PredictedDisposition(EnforcementModel):
    type: str
    likelihood: Likelihood
    rank: int = Field(ge=1)
    confidence: PredictionConfidence
    rationale: List[PredictionFactor] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)


class EnforcementPrediction(EnforcementModel):
    schema_version: Literal["1"] = "1"
    engine_version: Literal["enforcement-prediction-v1"] = "enforcement-prediction-v1"
    prompt_version: Literal["enforcement-prediction-prompt-v1"] = "enforcement-prediction-prompt-v1"
    status: Literal["AVAILABLE", "LIMITED", "UNAVAILABLE"]
    monetary_prediction: Optional[MonetaryPrediction] = None
    primary_disposition: Optional[PredictedDisposition] = None
    alternative_dispositions: List[PredictedDisposition] = Field(default_factory=list)
    stay_impact: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    similar_cases: List[SimilarCaseReference] = Field(default_factory=list)
    aggravating_factors: List[PredictionFactor] = Field(default_factory=list)
    mitigating_factors: List[PredictionFactor] = Field(default_factory=list)
    unresolved_factors: List[PredictionFactor] = Field(default_factory=list)
    confidence: PredictionConfidence
    limitations: List[str] = Field(default_factory=list)
    model_id: Optional[str] = None

    @model_validator(mode="after")
    def references_exist(self) -> "EnforcementPrediction":
        evidence_ids = {item.id for item in self.evidence}
        refs: List[str] = []
        factor_groups = [self.aggravating_factors, self.mitigating_factors, self.unresolved_factors]
        if self.monetary_prediction:
            factor_groups.append(self.monetary_prediction.rationale)
        for disposition in ([self.primary_disposition] if self.primary_disposition else []) + self.alternative_dispositions:
            refs.extend(disposition.supporting_evidence)
            factor_groups.append(disposition.rationale)
        for group in factor_groups:
            for factor in group:
                refs.extend(factor.evidence_ids)
        refs.extend(case.evidence_id for case in self.similar_cases)
        unknown = sorted({ref for ref in refs if ref and ref not in evidence_ids})
        if unknown:
            raise ValueError(f"unknown evidenceIds: {', '.join(unknown)}")
        return self


class EnforcementAnalysis(EnforcementModel):
    schema_version: Literal["1"] = "1"
    case: StructuredCase
    legal_baseline: LegalBaseline
    prediction: EnforcementPrediction
    workplace_determination: Optional[WorkplaceDetermination] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    disclaimer: str = "이 결과는 공개 법령과 제한된 공개 근거에 기반한 정보 제공용 예상이며, 출입국 당국의 최종 처분이나 법률 자문이 아닙니다."
    privacy_notice: str = "원문 사례 서술은 응답·저장·일반 로그에 남기지 않습니다."
