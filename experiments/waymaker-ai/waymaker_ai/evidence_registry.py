"""Mission 005-G: the trust registry evidence is checked against before any model sees it.

Trust comes only from registry records kept outside the documents. A document's
own text or its attached `source` fields (provenance, approval_state, source_url,
approved_sha256 …) never establish authenticity, authority or approval: those are
claims, and a forged document can make them. A missing record is "not verified",
never "verified". SHA-256 shows the bytes match what the registry recorded; it
does not show the document is legally authoritative.

Two registry kinds exist and are never mixed:
- synthetic research fixtures, frozen with an evaluation suite (method synthetic_fixture);
- real-world records from an independently controlled registry or authorized review.
An unreadable registry fails closed (RegistryUnavailable), so the pipeline withholds.
See artemis_bootstrap/trusted_evidence_spec.md.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

VERIFICATION_RESULTS = ("verified", "unverified", "rejected", "review_required")
AUTHORITIES = ("official", "unofficial", "unknown")
REVIEW_STATES = ("approved", "not_required", "pending", "rejected")
PROCEDURES = ("issuance", "change", "extension", "registration", "reentry", "workplace", "address", "activity",
              "family", "any")
APPLICANT_SCOPES = ("domestic", "abroad", "any")
VERIFICATION_METHODS = ("synthetic_fixture", "registry_lookup", "authorized_review")
REQUIRED_FIELDS = ("evidence_id", "source_locator", "issuing_organization", "document_type", "retrieved_at",
                   "content_sha256", "verification", "authority", "jurisdiction", "subject", "status_scope",
                   "all_subcategories_of", "procedures", "applicant_scope", "published", "effective_from",
                   "effective_until", "superseded_by", "review_state", "decision_provenance")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class RegistryUnavailable(RuntimeError):
    """The registry could not be read; trust cannot be established."""


def content_sha256(text: str) -> str:
    """SHA-256 of the exact evidence text as UTF-8, with no normalization."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record_problems(record: Mapping) -> list[str]:
    """Why a record is malformed. A malformed record is treated as absent (not verified)."""
    problems = [f"missing {f}" for f in REQUIRED_FIELDS if f not in record]
    if problems:
        return problems
    v = record["verification"]
    if not isinstance(v, Mapping) or v.get("result") not in VERIFICATION_RESULTS or v.get("method") not in VERIFICATION_METHODS:
        problems.append("bad verification")
    if record["authority"] not in AUTHORITIES:
        problems.append("bad authority")
    if record["review_state"] not in REVIEW_STATES:
        problems.append("bad review_state")
    if not isinstance(record["jurisdiction"], list) or not record["jurisdiction"]:
        problems.append("bad jurisdiction")
    if not set(record["procedures"]) <= set(PROCEDURES) or not record["procedures"]:
        problems.append("bad procedures")
    if not set(record["applicant_scope"]) <= set(APPLICANT_SCOPES) or not record["applicant_scope"]:
        problems.append("bad applicant_scope")
    for key in ("effective_from", "effective_until", "published"):
        if record[key] is not None and not _DATE.match(str(record[key])):
            problems.append(f"bad {key}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(record["content_sha256"])):
        problems.append("bad content_sha256")
    return problems


@dataclass(frozen=True)
class TrustRegistry:
    """Immutable evidence_id -> record map with the kind of registry it is."""
    records: Mapping[str, Mapping]
    kind: str                     # "synthetic_fixture" or "real_world"
    source: str                   # where the records came from, for audit

    def get(self, evidence_id: str) -> Optional[Mapping]:
        record = self.records.get(evidence_id)
        if record is None or record_problems(record) or record.get("evidence_id") != evidence_id:
            return None
        if self.kind == "real_world" and record["verification"]["method"] == "synthetic_fixture":
            return None   # a synthetic fixture can never vouch for real-world evidence
        if self.kind == "synthetic_fixture" and record["verification"]["method"] != "synthetic_fixture":
            return None
        return record

    def jurisdictions(self) -> set:
        return {j for r in self.records.values() if isinstance(r, Mapping)
                for j in (r.get("jurisdiction") or []) if j != "national"}


def synthetic_registry(records: Optional[Mapping[str, Mapping]], source: str) -> TrustRegistry:
    """A frozen fixture registry from evaluation data. None means unavailable."""
    if records is None:
        raise RegistryUnavailable(f"no synthetic registry in {source}")
    return TrustRegistry(records=dict(records), kind="synthetic_fixture", source=source)


def load_real_world_registry(path: Path) -> TrustRegistry:
    """Real-world records from an independently controlled registry file. Missing or unreadable fails closed."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryUnavailable(f"real-world registry unreadable: {exc}") from exc
    records = data.get("records")
    if not isinstance(records, Mapping):
        raise RegistryUnavailable("real-world registry has no records map")
    return TrustRegistry(records=dict(records), kind="real_world", source=str(path))
