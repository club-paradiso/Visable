from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_outcome_evaluation import validate_outcome_ground_truth_dataset  # noqa: E402
from services.enforcement_outcome_intake import (  # noqa: E402
    EnforcementOutcomeIntakeError,
    derive_private_token,
    normalize_private_intake_dataset,
    promote_reviewed_ground_truth,
    validate_safe_intake_dataset,
)

RECORD_SECRET = "record-secret-for-tests-1234567890"
REVIEWER_SECRET = "reviewer-secret-for-tests-1234567890"


def reviewed_private_record(source_id: str = "private-case-001", provenance_id: str = "official-record-001") -> dict:
    return {
        "sourceRecordId": source_id,
        "reviewStage": "INDEPENDENTLY_REVIEWED",
        "caseFacts": {
            "statusOfStay": "D-2",
            "violationCode": "STATUS_OUTSIDE_ACTIVITY_ART20",
            "durationDays": 18,
            "priorViolations": 0,
            "voluntaryDisclosure": True,
            "authorizationObtained": False,
            "assessmentDate": "2026-08-19",
        },
        "provenance": {
            "sourceType": "VERIFIED_ADMINISTRATIVE_RECORD",
            "authority": "Test administrative authority",
            "recordId": provenance_id,
            "publicUrl": None,
        },
        "outcome": {
            "decisionDate": "2026-08-20",
            "monetaryOutcomeKrw": 2000000,
            "dispositionTypes": ["ADMINISTRATIVE_FINE"],
            "primaryDispositionType": "ADMINISTRATIVE_FINE",
        },
        "independentFromPrediction": True,
        "reviewerRole": "AUTHORIZED_ADMINISTRATIVE_REVIEWER",
        "reviewHistory": [
            {
                "stage": "STAGED",
                "at": "2026-08-20T09:00:00+09:00",
                "reviewerReference": "private-intake-user",
            },
            {
                "stage": "SOURCE_VERIFIED",
                "at": "2026-08-20T09:10:00+09:00",
                "reviewerReference": "private-source-verifier",
            },
            {
                "stage": "INDEPENDENTLY_REVIEWED",
                "at": "2026-08-20T09:30:00+09:00",
                "reviewerReference": "private-outcome-reviewer",
            },
        ],
    }


def staged_private_record(source_id: str = "private-case-staged") -> dict:
    return {
        "sourceRecordId": source_id,
        "reviewStage": "STAGED",
        "caseFacts": {"statusOfStay": "D-2"},
        "provenance": None,
        "outcome": None,
        "independentFromPrediction": None,
        "reviewerRole": None,
        "reviewHistory": [
            {
                "stage": "STAGED",
                "at": "2026-08-20T08:00:00+09:00",
                "reviewerReference": "private-intake-user",
            }
        ],
    }


def dataset(*records: dict) -> dict:
    return {
        "schemaVersion": "1.0.0",
        "datasetVersion": "test-private-corpus-v1",
        "jurisdiction": "KR",
        "records": list(records),
    }


def normalize(data: dict) -> dict:
    return normalize_private_intake_dataset(
        data,
        record_secret=RECORD_SECRET,
        reviewer_secret=REVIEWER_SECRET,
    )


def test_hmac_tokens_are_stable_but_secret_scoped():
    first = derive_private_token(RECORD_SECRET, "case-1", prefix="case")
    second = derive_private_token(RECORD_SECRET, "case-1", prefix="case")
    other = derive_private_token("different-secret-for-tests-1234567890", "case-1", prefix="case")
    assert first == second
    assert first != other
    assert first.startswith("case_")
    assert "case-1" not in first


def test_private_identifiers_and_reviewer_references_do_not_survive_normalization():
    safe = normalize(dataset(reviewed_private_record()))
    blob = json.dumps(safe, ensure_ascii=False)
    assert "private-case-001" not in blob
    assert "official-record-001" not in blob
    assert "private-intake-user" not in blob
    assert "private-source-verifier" not in blob
    assert "private-outcome-reviewer" not in blob
    row = safe["records"][0]
    assert row["caseId"].startswith("case_")
    assert row["provenance"]["recordId"].startswith("src_")
    assert all(event["actorToken"].startswith("reviewer_") for event in row["reviewHistory"])


def test_raw_narrative_or_pii_fields_are_rejected_before_export():
    raw = reviewed_private_record()
    raw["rawText"] = "person-identifying narrative"
    with pytest.raises(EnforcementOutcomeIntakeError, match="forbidden field"):
        normalize(dataset(raw))

    raw = reviewed_private_record()
    raw["caseFacts"]["email"] = "person@example.invalid"
    with pytest.raises(EnforcementOutcomeIntakeError, match="forbidden field"):
        normalize(dataset(raw))


def test_prediction_derived_or_synthetic_labels_are_rejected():
    raw = reviewed_private_record()
    raw["independentFromPrediction"] = False
    with pytest.raises(EnforcementOutcomeIntakeError, match="independent"):
        normalize(dataset(raw))

    raw = reviewed_private_record()
    raw["provenance"]["sourceType"] = "MODEL_GENERATED"
    with pytest.raises(EnforcementOutcomeIntakeError, match="ineligible"):
        normalize(dataset(raw))


def test_review_workflow_cannot_skip_staging_or_move_backward_in_time():
    raw = reviewed_private_record()
    raw["reviewHistory"] = raw["reviewHistory"][1:]
    with pytest.raises(EnforcementOutcomeIntakeError, match="START.*SOURCE_VERIFIED"):
        normalize(dataset(raw))

    raw = reviewed_private_record()
    raw["reviewHistory"][2]["at"] = "2026-08-20T09:05:00+09:00"
    with pytest.raises(EnforcementOutcomeIntakeError, match="chronological"):
        normalize(dataset(raw))


def test_review_timestamps_require_timezone_offsets():
    raw = reviewed_private_record()
    raw["reviewHistory"][0]["at"] = "2026-08-20T09:00:00"
    with pytest.raises(EnforcementOutcomeIntakeError, match="timezone"):
        normalize(dataset(raw))


def test_duplicate_source_records_are_detected_deterministically():
    one = reviewed_private_record("same-private-id", "source-a")
    two = reviewed_private_record("same-private-id", "source-b")
    with pytest.raises(EnforcementOutcomeIntakeError, match="duplicate source"):
        normalize(dataset(one, two))


def test_duplicate_provenance_is_rejected_even_when_case_ids_differ():
    one = reviewed_private_record("private-case-a", "same-official-source")
    two = reviewed_private_record("private-case-b", "same-official-source")
    with pytest.raises(EnforcementOutcomeIntakeError, match="duplicate provenance"):
        normalize(dataset(one, two))


def test_runtime_validator_is_closed_shape_for_private_and_safe_records():
    raw = reviewed_private_record()
    raw["mysteryField"] = "not allowed"
    with pytest.raises(EnforcementOutcomeIntakeError, match="unsupported fields in private record"):
        normalize(dataset(raw))

    safe = normalize(dataset(reviewed_private_record()))
    safe["records"][0]["mysteryField"] = "not allowed"
    with pytest.raises(EnforcementOutcomeIntakeError, match="unsupported fields in safe record"):
        validate_safe_intake_dataset(safe)


def test_safe_validator_rejects_private_only_fields_leaked_after_normalization():
    safe = normalize(dataset(reviewed_private_record()))
    safe["records"][0]["sourceRecordId"] = "should-never-be-here"
    with pytest.raises(EnforcementOutcomeIntakeError, match="private-only field leaked"):
        validate_safe_intake_dataset(safe)

    safe = normalize(dataset(reviewed_private_record()))
    safe["records"][0]["reviewHistory"][0]["reviewerReference"] = "should-never-be-here"
    with pytest.raises(EnforcementOutcomeIntakeError, match="private-only field leaked"):
        validate_safe_intake_dataset(safe)


def test_reviewer_role_must_be_non_identifying_approved_code():
    raw = reviewed_private_record()
    raw["reviewerRole"] = "Jane Doe"
    with pytest.raises(EnforcementOutcomeIntakeError, match="approved role code"):
        normalize(dataset(raw))


def test_public_url_rejects_local_and_private_network_hosts():
    raw = reviewed_private_record()
    raw["provenance"]["publicUrl"] = "https://localhost/private"
    with pytest.raises(EnforcementOutcomeIntakeError, match="local host"):
        normalize(dataset(raw))

    raw = reviewed_private_record()
    raw["provenance"]["publicUrl"] = "https://127.0.0.1/private"
    with pytest.raises(EnforcementOutcomeIntakeError, match="non-public IP"):
        normalize(dataset(raw))


def test_only_independently_reviewed_records_are_promoted_to_evaluator_contract():
    safe = normalize(dataset(staged_private_record(), reviewed_private_record()))
    promoted = promote_reviewed_ground_truth(safe)
    validated = validate_outcome_ground_truth_dataset(promoted)
    assert len(validated["records"]) == 1
    row = validated["records"][0]
    assert row["reviewStatus"] == "INDEPENDENTLY_REVIEWED"
    assert row["independentFromPrediction"] is True
    assert row["caseId"].startswith("case_")
    assert "reviewHistory" not in row


def test_checked_in_intake_template_is_empty_and_schema_is_closed():
    template = json.loads((REPO_ROOT / "backend/data/enforcement/outcome_intake.template.json").read_text(encoding="utf-8"))
    schema = json.loads((REPO_ROOT / "backend/data/enforcement/outcome_intake.schema.json").read_text(encoding="utf-8"))
    assert template["records"] == []
    assert validate_safe_intake_dataset(template)["records"] == []
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["record"]["additionalProperties"] is False
    assert "AUTHORIZED_ADMINISTRATIVE_REVIEWER" in schema["$defs"]["reviewerRole"]["enum"]


def test_cli_deidentifies_validates_and_promotes_without_echoing_private_ids(tmp_path: Path):
    private_path = tmp_path / "private.json"
    safe_path = tmp_path / "safe.json"
    promoted_path = tmp_path / "ground-truth.json"
    private_path.write_text(json.dumps(dataset(reviewed_private_record()), ensure_ascii=False), encoding="utf-8")
    env = os.environ.copy()
    env["VISABLE_ENFORCEMENT_RECORD_HMAC_SECRET"] = RECORD_SECRET
    env["VISABLE_ENFORCEMENT_REVIEWER_HMAC_SECRET"] = REVIEWER_SECRET
    script = REPO_ROOT / "scripts/prepare_enforcement_outcome_corpus.py"

    first = subprocess.run(
        [sys.executable, str(script), "deidentify", "--input", str(private_path), "--output", str(safe_path)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert first.returncode == 0, first.stderr
    assert "private-case-001" not in first.stdout + first.stderr
    assert safe_path.exists()

    second = subprocess.run(
        [sys.executable, str(script), "validate-safe", "--input", str(safe_path)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert second.returncode == 0, second.stderr
    assert "INDEPENDENTLY_REVIEWED=1" in second.stdout

    third = subprocess.run(
        [sys.executable, str(script), "promote-reviewed", "--input", str(safe_path), "--output", str(promoted_path)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert third.returncode == 0, third.stderr
    promoted = json.loads(promoted_path.read_text(encoding="utf-8"))
    assert len(promoted["records"]) == 1
    serialized = json.dumps(promoted, ensure_ascii=False)
    assert "private-case-001" not in serialized
    assert "official-record-001" not in serialized
