"""The Artemis structured-response contract, shared by the MLX and CUDA workers.

One definition so both runtimes and the run-record validator judge the same
output the same way. Passing it means well-formed and grounded in listed IDs;
it says nothing about whether the answer is legally correct.
"""
from __future__ import annotations

import json

STATUSES = {"answered", "partial", "insufficient_evidence", "conflict", "clarify"}
# A substantive answer must point at supplied evidence; withholding need not.
REQUIRES_CITATION = {"answered", "partial", "conflict"}


def _no_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate JSON keys")
    return dict(pairs)


def parse_response(raw: str, evidence_ids: set[str]) -> dict:
    if not isinstance(raw, str):
        raise ValueError("Raw output must be text")
    data = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    if (not isinstance(data, dict) or set(data) != {"status", "answer", "citations"}
            or data["status"] not in STATUSES
            or not isinstance(data["answer"], str)
            or not isinstance(data["citations"], list)
            or not all(isinstance(c, str) and c in evidence_ids for c in data["citations"])):
        raise ValueError("Invalid structured response or unlisted citation")
    if len(set(data["citations"])) != len(data["citations"]):
        raise ValueError("Duplicate citation IDs")
    if data["status"] in REQUIRES_CITATION and not data["citations"]:
        raise ValueError(f"Status {data['status']} requires at least one listed citation")
    if data["status"] in {"answered", "partial"} and not data["answer"].strip():
        raise ValueError(f"Status {data['status']} requires a non-empty answer")
    return data
