from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_models import EnforcementPrediction, PredictionConfidence  # noqa: E402
from services.enforcement_outcome_intake import normalize_private_intake_dataset  # noqa: E402
from services.enforcement_prediction_freeze import (  # noqa: E402
    EnforcementPredictionFreezeError,
    build_blind_case_set,
    evaluate_frozen_outcomes,
    freeze_predictions,
    validate_blind_case_set,
    validate_prediction_freeze,
)

RECORD_SECRET = "blind-freeze-record-secret-1234567890"
REVIEWER_SECRET = "blind-freeze-reviewer-secret-1234567890"


def _facts(status: str = "D-2") -> dict:
    return {
        "statusOfStay": status,
        "violationCode": "STATUS_OUTSIDE_ACTIVITY_ART20",
        "durationDays": 18,
        "priorViolations": 0,
        "voluntaryDisclosure": True,
        "authorizationObtained": False,
        "assessmentDate": "2026-08-19",
    }


def _private_record(source_id: str, *, stage: str = "STAGED", facts: dict | None = None) -> dict:
    facts = deepcopy(facts or _facts())
    history = [
        {
            "stage": "STAGED",
            "at": "2026-08-20T08:00:00+09:00",
            "reviewerReference": f"{source_id}-intake",
        }
    ]
    provenance = None
    outcome = None
    independent = None
    reviewer_role = None

    if stage in {"SOURCE_VERIFIED", "INDEPENDENTLY_REVIEWED"}:
        provenance = {
            "sourceType": "VERIFIED_ADMINISTRATIVE_RECORD",
            "authority": "Test administrative authority",
            "recordId": f"official-{source_id}",
            "publicUrl": None,
        }
        history.append(
            {
                "stage": "SOURCE_VERIFIED",
                "at": "2026-08-20T08:15:00+09:00",
                "reviewerReference": f"{source_id}-source-reviewer",
            }
        )

    if stage == "INDEPENDENTLY_REVIEWED":
        outcome = {
            "decisionDate": "2026-08-20",
            "monetaryOutcomeKrw": 2000000,
            "dispositionTypes": ["ADMINISTRATIVE_FINE"],
            "primaryDispositionType": "ADMINISTRATIVE_FINE",
        }
        independent = True
        reviewer_role = "AUTHORIZED_ADMINISTRATIVE_REVIEWER"
        history.append(
            {
                "stage": "INDEPENDENTLY_REVIEWED",
                "at": "2026-08-20T10:00:00+09:00",
                "reviewerReference": f"{source_id}-outcome-reviewer",
            }
        )

    return {
        "sourceRecordId": source_id,
        "reviewStage": stage,
        "caseFacts": facts,
        "provenance": provenance,
        "outcome": outcome,
        "independentFromPrediction": independent,
        "reviewerRole": reviewer_role,
        "reviewHistory": history,
    }


def _dataset(*records: dict) -> dict:
    return {
        "schemaVersion": "1.0.0",
        "datasetVersion": "blind-freeze-test-v1",
        "jurisdiction": "KR",
        "records": list(records),
    }


def _normalize(*records: dict) -> dict:
    return normalize_private_intake_dataset(
        _dataset(*records),
        record_secret=RECORD_SECRET,
        reviewer_secret=REVIEWER_SECRET,
    )


def _prediction() -> EnforcementPrediction:
    return EnforcementPrediction(
        status="UNAVAILABLE",
        confidence=PredictionConfidence(level="INSUFFICIENT", reasons=["test fixture"]),
        limitations=["test fixture"],
    )


def _pre_outcome_safe() -> dict:
    return _normalize(
        _private_record("case-a", stage="SOURCE_VERIFIED"),
        _private_record("case-b", stage="STAGED", facts=_facts("F-2")),
    )


def _freeze_from_safe(safe: dict, *, frozen_at: str = "2026-08-20T00:30:00+00:00") -> tuple[dict, dict]:
    cases = build_blind_case_set(
        safe,
        generated_at=datetime.fromisoformat("2026-08-19T23:30:00+00:00"),
    )
    predictions = {row["caseId"]: _prediction() for row in cases["records"]}
    frozen = freeze_predictions(
        cases,
        predictions,
        frozen_at=datetime.fromisoformat(frozen_at),
    )
    return cases, frozen


def test_blind_case_export_requires_complete_pre_outcome_cohort():
    safe = _pre_outcome_safe()
    cases = build_blind_case_set(safe, generated_at=datetime.fromisoformat("2026-08-19T23:30:00+00:00"))
    validated = validate_blind_case_set(cases)
    assert len(validated["records"]) == 2
    assert all(set(row) == {"caseId", "caseFacts", "caseFactsDigest"} for row in validated["records"])
    assert all("outcome" not in row for row in validated["records"])

    reviewed = _normalize(_private_record("case-a", stage="INDEPENDENTLY_REVIEWED"))
    with pytest.raises(EnforcementPredictionFreezeError, match="pre-outcome cohort"):
        build_blind_case_set(reviewed)


def test_freeze_requires_prediction_for_every_case_and_refuses_extras():
    cases = build_blind_case_set(
        _pre_outcome_safe(),
        generated_at=datetime.fromisoformat("2026-08-19T23:30:00+00:00"),
    )
    first_id = cases["records"][0]["caseId"]
    with pytest.raises(EnforcementPredictionFreezeError, match="cohort mismatch"):
        freeze_predictions(cases, {first_id: _prediction()})

    predictions = {row["caseId"]: _prediction() for row in cases["records"]}
    predictions["case_000000000000000000000000"] = _prediction()
    with pytest.raises(EnforcementPredictionFreezeError, match="cohort mismatch"):
        freeze_predictions(cases, predictions)


def test_prediction_and_freeze_digests_detect_tampering():
    _, frozen = _freeze_from_safe(_pre_outcome_safe())
    assert validate_prediction_freeze(frozen)["freezeId"] == frozen["freezeId"]

    tampered_prediction = deepcopy(frozen)
    tampered_prediction["records"][0]["prediction"]["limitations"] = ["changed after freeze"]
    with pytest.raises(EnforcementPredictionFreezeError, match="predictionDigest mismatch"):
        validate_prediction_freeze(tampered_prediction)

    tampered_manifest = deepcopy(frozen)
    tampered_manifest["frozenAt"] = "2026-08-19T00:00:00Z"
    with pytest.raises(EnforcementPredictionFreezeError, match="freezeId"):
        validate_prediction_freeze(tampered_manifest)


def test_evaluation_rejects_case_fact_drift_after_freeze():
    safe = _pre_outcome_safe()
    _, frozen = _freeze_from_safe(safe)
    reviewed = _normalize(
        _private_record("case-a", stage="INDEPENDENTLY_REVIEWED", facts=_facts("E-7")),
        _private_record("case-b", stage="STAGED", facts=_facts("F-2")),
    )
    with pytest.raises(EnforcementPredictionFreezeError, match="caseFacts changed after freeze"):
        evaluate_frozen_outcomes(reviewed, frozen)


def test_evaluation_rejects_freeze_that_does_not_precede_independent_review():
    safe = _pre_outcome_safe()
    _, frozen = _freeze_from_safe(safe, frozen_at="2026-08-20T02:00:00+00:00")
    reviewed = _normalize(
        _private_record("case-a", stage="INDEPENDENTLY_REVIEWED"),
        _private_record("case-b", stage="STAGED", facts=_facts("F-2")),
    )
    with pytest.raises(EnforcementPredictionFreezeError, match="must precede independent review"):
        evaluate_frozen_outcomes(reviewed, frozen)


def test_valid_frozen_cohort_joins_reviewed_outcomes_without_cherry_picking():
    safe = _pre_outcome_safe()
    _, frozen = _freeze_from_safe(safe)
    reviewed = _normalize(
        _private_record("case-a", stage="INDEPENDLY_REVIEWED") if False else _private_record("case-a", stage="INDEPENDENTLY_REVIEWED"),
        _private_record("case-b", stage="STAGED", facts=_facts("F-2")),
    )
    report = evaluate_frozen_outcomes(reviewed, frozen)
    assert report["protocolStatus"] == "VALID"
    assert report["cohortCases"] == 2
    assert report["reviewedCases"] == 1
    assert report["pendingCases"] == 1
    assert report["evaluation"]["status"] == "EVALUATED"
    assert report["evaluation"]["matchedPredictions"] == 1


def test_evaluation_rejects_cohort_growth_after_freeze():
    safe = _pre_outcome_safe()
    _, frozen = _freeze_from_safe(safe)
    grown = _normalize(
        _private_record("case-a", stage="SOURCE_VERIFIED"),
        _private_record("case-b", stage="STAGED", facts=_facts("F-2")),
        _private_record("case-c", stage="STAGED", facts=_facts("D-4")),
    )
    with pytest.raises(EnforcementPredictionFreezeError, match="cohort changed"):
        evaluate_frozen_outcomes(grown, frozen)
