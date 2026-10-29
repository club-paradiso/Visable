"""Artemis Independent Benchmark Intake & Clean-Room Governance Infrastructure (Mission 005-A).

Provides the technical foundation for future 100-item independently authored blind evaluations:
1. External benchmark intake schema and validator (BenchmarkSubmissionItem).
2. Separation of questions (blind projection) and answer keys (isolated ground truth).
3. Contamination and revision tracking (ContaminationAuditor).
4. Role-based evaluator access-control specifications (EvaluatorAccessControl).
5. Cryptographically attested frozen dataset manifests.

CRITICAL GOVERNANCE RULES:
1. NEVER automatically generate benchmark items and label them 'independently authored'.
2. Crypographic hashes demonstrate content integrity, NOT legal correctness or absence of leakage.
3. The answer key must NEVER be passed to model inference runners.
"""
from __future__ import annotations

import copy
import dataclasses
import datetime as dt
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple


class EvaluatorRole(str, Enum):
    MODEL_RUNNER = "model_runner"           # Read-only access to blind question projection
    EVALUATION_GRADER = "evaluation_grader" # Access to blind projection + ephemeral ground truth
    EXTERNAL_AUDITOR = "external_auditor"   # Audit manifests and contamination attestations
    LEGAL_ADMIN = "legal_admin"             # Intake schema management and partition freeze


class ContaminationRisk(str, Enum):
    CLEAN = "clean"                         # No significant overlap with public corpus
    LOW = "low"                             # Common statutory boilerplate overlap (<20%)
    SUSPECTED = "suspected"                 # High overlap with known public training items (>50%)
    CONTAMINATED = "contaminated"           # Exact duplicate of public test item


@dataclass(frozen=True)
class ExternalAuthorAttestation:
    author_id: str
    full_name: str
    organization: str
    license_or_credential: str
    independence_confirmed: bool
    zero_leakage_attested: bool
    submission_date: str
    signature_digest: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class BenchmarkSubmissionItem:
    submission_id: str
    author_attestation: ExternalAuthorAttestation
    target_visa_category: str
    question: str
    user_context: Dict[str, Any]
    authoritative_answer_key: str
    legal_citations: List[Dict[str, Any]]
    rubric_spec: Dict[str, Any]
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "submission_id": self.submission_id,
            "author_attestation": self.author_attestation.to_dict(),
            "target_visa_category": self.target_visa_category,
            "question": self.question,
            "user_context": copy.deepcopy(self.user_context),
            "authoritative_answer_key": self.authoritative_answer_key,
            "legal_citations": copy.deepcopy(self.legal_citations),
            "rubric_spec": copy.deepcopy(self.rubric_spec),
            "version": self.version,
            "created_at": self.created_at,
        }

    def validate(self) -> List[str]:
        issues = []
        if not self.submission_id or not re.match(r"^[A-Z0-9_-]+$", self.submission_id):
            issues.append("Invalid or missing submission_id")
        if not self.question or len(self.question.strip()) < 10:
            issues.append("Question is missing or too short (<10 chars)")
        if not self.authoritative_answer_key or len(self.authoritative_answer_key.strip()) < 5:
            issues.append("Authoritative answer key is missing or too short")
        if not self.author_attestation.independence_confirmed:
            issues.append("Author must confirm independence from model developer")
        if not self.author_attestation.zero_leakage_attested:
            issues.append("Author must attest zero-leakage of benchmark item")
        if not self.legal_citations:
            issues.append("At least one legal citation is required")
        return issues


def compute_sha256(data: Any) -> str:
    if isinstance(data, (dict, list)):
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
    else:
        payload = unicodedata.normalize("NFC", str(data or "")).strip()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class BlindBenchmarkPartitionManager:
    """Manages separation of blind questions and isolated answer keys."""

    @staticmethod
    def project_blind(items: Sequence[BenchmarkSubmissionItem]) -> List[Dict[str, Any]]:
        """Extracts strictly blind inputs for model inference."""
        blind_items = []
        for it in items:
            blind_items.append({
                "submission_id": it.submission_id,
                "target_visa_category": it.target_visa_category,
                "question": it.question,
                "user_context": copy.deepcopy(it.user_context),
                # Strictly omit answer key, legal citations, and grading rubrics!
            })
        return blind_items

    @staticmethod
    def extract_isolated_key(items: Sequence[BenchmarkSubmissionItem]) -> Dict[str, Any]:
        """Extracts answer keys and rubrics for ephemeral grading containers."""
        keys = {}
        for it in items:
            keys[it.submission_id] = {
                "authoritative_answer_key": it.authoritative_answer_key,
                "legal_citations": it.legal_citations,
                "rubric_spec": it.rubric_spec,
            }
        return keys

    @staticmethod
    def create_frozen_manifest(
        benchmark_id: str,
        items: Sequence[BenchmarkSubmissionItem],
    ) -> Dict[str, Any]:
        blind = BlindBenchmarkPartitionManager.project_blind(items)
        keys = BlindBenchmarkPartitionManager.extract_isolated_key(items)

        blind_hash = compute_sha256(blind)
        key_hash = compute_sha256(keys)

        return {
            "manifest_version": "artemis-frozen-manifest/1.0",
            "benchmark_id": benchmark_id,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "total_items": len(items),
            "blind_partition_sha256": blind_hash,
            "key_partition_sha256": key_hash,
            "isolation_protocol": "air_gapped_blind_projection",
            "governance_notice": (
                "Blind partition contains only question and context. "
                "Key partition must only be decrypted inside ephemeral grading sandbox."
            ),
        }


class ContaminationAuditor:
    """Audits benchmark candidates against known public corpora to detect potential leakage."""

    def __init__(self, reference_corpus: Sequence[str]):
        self._reference_corpus = [unicodedata.normalize("NFC", t).lower() for t in reference_corpus if t]

    def check_item_contamination(self, question: str, answer_key: str) -> Tuple[ContaminationRisk, float, str]:
        """Calculates token overlap between submission and reference corpus."""
        combined = f"{question} {answer_key}".lower()
        tokens = set(re.findall(r"\b\w{2,}\b", combined))
        if not tokens:
            return ContaminationRisk.CLEAN, 0.0, "No lexical tokens to analyze"

        max_overlap = 0.0
        matched_sample = ""
        for ref in self._reference_corpus:
            ref_tokens = set(re.findall(r"\b\w{2,}\b", ref))
            if not ref_tokens:
                continue
            common = tokens.intersection(ref_tokens)
            overlap = len(common) / len(tokens)
            if overlap > max_overlap:
                max_overlap = overlap
                matched_sample = ref[:80]

        if max_overlap >= 0.8:
            return ContaminationRisk.CONTAMINATED, max_overlap, f"Near exact duplicate of: {matched_sample}"
        elif max_overlap >= 0.5:
            return ContaminationRisk.SUSPECTED, max_overlap, f"Substantial overlap with: {matched_sample}"
        elif max_overlap >= 0.2:
            return ContaminationRisk.LOW, max_overlap, "Normal statutory boilerplate overlap"
        else:
            return ContaminationRisk.CLEAN, max_overlap, "No significant overlap detected"


class EvaluatorAccessController:
    """Enforces access control policies for blind benchmark artifacts."""

    @staticmethod
    def authorize_read(role: EvaluatorRole, partition: str) -> bool:
        if role == EvaluatorRole.MODEL_RUNNER:
            return partition == "blind_partition"
        elif role == EvaluatorRole.EVALUATION_GRADER:
            return partition in ("blind_partition", "key_partition")
        elif role in (EvaluatorRole.EXTERNAL_AUDITOR, EvaluatorRole.LEGAL_ADMIN):
            return True
        return False
