from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_outcome_intake import normalize_private_intake_dataset  # noqa: E402

RECORD_SECRET = "record-secret-for-tests-1234567890"
REVIEWER_SECRET = "reviewer-secret-for-tests-1234567890"


def _reviewed(source_record_id: str, authority: str) -> dict:
    return {
        "sourceRecordId": f"private-{authority}",
        "reviewStage": "INDEPENDENTLY_REVIEWED",
        "caseFacts": {"statusOfStay": "D-2"},
        "provenance": {
            "sourceType": "VERIFIED_ADMINISTRATIVE_RECORD",
            "authority": authority,
            "recordId": source_record_id,
            "publicUrl": None,
        },
        "outcome": {
            "decisionDate": "2026-08-20",
            "monetaryOutcomeKrw": 1000000,
            "dispositionTypes": ["ADMINISTRATIVE_FINE"],
            "primaryDispositionType": "ADMINISTRATIVE_FINE",
        },
        "independentFromPrediction": True,
        "reviewerRole": "AUTHORIZED_ADMINISTRATIVE_REVIEWER",
        "reviewHistory": [
            {"stage": "STAGED", "at": "2026-08-20T09:00:00+09:00", "reviewerReference": "intake"},
            {"stage": "SOURCE_VERIFIED", "at": "2026-08-20T09:10:00+09:00", "reviewerReference": "source"},
            {"stage": "INDEPENDENTLY_REVIEWED", "at": "2026-08-20T09:20:00+09:00", "reviewerReference": "review"},
        ],
    }


def test_same_record_id_from_different_authorities_has_distinct_provenance_tokens():
    data = {
        "schemaVersion": "1.0.0",
        "datasetVersion": "authority-scope-regression-v1",
        "jurisdiction": "KR",
        "records": [
            _reviewed("123", "Authority A"),
            _reviewed("123", "Authority B"),
        ],
    }
    safe = normalize_private_intake_dataset(
        data,
        record_secret=RECORD_SECRET,
        reviewer_secret=REVIEWER_SECRET,
    )
    tokens = [row["provenance"]["recordId"] for row in safe["records"]]
    assert len(tokens) == 2
    assert tokens[0] != tokens[1]
