"""Artemis Independent Benchmark Intake & Clean-Room Governance Infrastructure (Mission 005-A).

Provides the technical foundation for future 100-item independently authored blind evaluations:
1. External benchmark intake schema and validator (BenchmarkSubmissionItem).
2. Separation of questions (blind projection) and answer keys (isolated ground truth).
3. Contamination and revision tracking (ContaminationAuditor).
4. Role-based evaluator access-control specifications (EvaluatorAccessControl).
5. Content-hashed frozen manifests; no infrastructure or independence certification.

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

from .evaluation_isolation import isolation_verification_policy


class EvaluatorRole(str, Enum):
    MODEL_RUNNER = "model_runner"           # Read-only access to blind question projection
    EVALUATION_GRADER = "evaluation_grader" # Access to blind projection + ephemeral ground truth
    EXTERNAL_AUDITOR = "external_auditor"   # Audit manifests and contamination attestations
    LEGAL_ADMIN = "legal_admin"             # Intake schema management and partition freeze


class ContaminationRisk(str, Enum):
    UNKNOWN = "unknown"                     # No usable comparison or input
    CLEAN = "clean"                         # No significant lexical overlap in supplied corpus only
    LOW = "low"                             # Lexical overlap >=20% and <50%
    SUSPECTED = "suspected"                 # Lexical overlap >=50% and <80%
    CONTAMINATED = "contaminated"           # Lexical overlap >=80%; not proof of exact duplication


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
    """Projects separate data views; does not enforce filesystem/process isolation."""

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
            "manifest_version": "artemis-frozen-manifest/1.1",
            "benchmark_id": benchmark_id,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "total_items": len(items),
            "blind_partition_sha256": blind_hash,
            "key_partition_sha256": key_hash,
            "isolation_protocol": "blind_projection_only",
            **isolation_verification_policy(),
            "author_attestations_authenticated": False,
            "governance_notice": (
                "Hashes bind content only. No air gap, authenticated author identity or key custody is verified. "
                "Role strings and self-attested signatures do not establish independent isolation. "
                "External enforcement and trusted verification are required before promoting this status."
            ),
        }


class ContaminationAuditor:
    """Screens candidates against the supplied corpus, with explicit coverage limits."""

    def __init__(self, reference_corpus: Sequence[str], corpus_id: Optional[str] = None):
        supplied = list(reference_corpus)
        self._reference_corpus = [unicodedata.normalize("NFC", t).lower() for t in supplied if isinstance(t, str)]
        self._reference_tokens = [self._tokens(t) for t in self._reference_corpus]
        self._usable_tokens = [tokens for tokens in self._reference_tokens if tokens]
        self._supplied_count = len(supplied)
        self._corpus_sha256 = compute_sha256(supplied)
        self._corpus_id = corpus_id or f"content-sha256:{self._corpus_sha256}"

    @staticmethod
    def _tokens(text: str) -> Set[str]:
        return set(re.findall(r"\b\w{2,}\b", unicodedata.normalize("NFC", text).lower()))

    def check_item_report(self, question: str, answer_key: str) -> Dict[str, Any]:
        """Scoped lexical screening, never proof of independence or model training exposure."""
        report = {
            "report_version": "artemis-contamination-screen/1.1",
            "risk": ContaminationRisk.UNKNOWN.value, "score": None,
            "corpus_id": self._corpus_id, "corpus_sha256": self._corpus_sha256,
            "reference_documents_supplied": self._supplied_count,
            "reference_documents_analyzed": len(self._usable_tokens),
            "scope": "question_and_answer_key_against_supplied_corpus",
            "method": "max_unique_token_overlap; NFC/lowercase; unicode word tokens length >= 2",
            "thresholds": {"contaminated": 0.8, "suspected": 0.5, "low": 0.2},
            "independence_verified": False,
            "limitations": [
                "Only supplied corpus entries are searched; absent/private training corpora are not covered",
                "Lexical overlap misses paraphrase/semantic leakage and can flag shared statutory wording",
                "Token overlap is a heuristic, not proof of exact duplication, independence or legal correctness",
            ],
        }
        if not self._usable_tokens:
            report["description"] = "UNKNOWN: no analyzable reference corpus"
            return report
        if (not isinstance(question, str) or not isinstance(answer_key, str)
                or not self._tokens(question) or not self._tokens(answer_key)):
            report["description"] = "UNKNOWN: question or answer key has no analyzable text"
            return report
        tokens = self._tokens(f"{question} {answer_key}")
        overlap = max(len(tokens & ref) / len(tokens) for ref in self._usable_tokens)
        risk = (ContaminationRisk.CONTAMINATED if overlap >= 0.8 else ContaminationRisk.SUSPECTED
                if overlap >= 0.5 else ContaminationRisk.LOW if overlap >= 0.2 else ContaminationRisk.CLEAN)
        report.update(risk=risk.value, score=overlap,
                      description=f"{risk.value}: lexical overlap in supplied corpus only; not an isolation certification")
        return report

    def check_item_contamination(self, question: str, answer_key: str) -> Tuple[ContaminationRisk, Optional[float], str]:
        """Compatibility view. Persist check_item_report for corpus provenance and limitations."""
        report = self.check_item_report(question, answer_key)
        return ContaminationRisk(report["risk"]), report["score"], report["description"]


class EvaluatorAccessController:
    """Declarative role policy only: no identity, OS ACL or sandbox is enforced here."""

    @staticmethod
    def authorize_read(role: EvaluatorRole, partition: str) -> bool:
        if role == EvaluatorRole.MODEL_RUNNER:
            return partition == "blind_partition"
        elif role == EvaluatorRole.EVALUATION_GRADER:
            return partition in ("blind_partition", "key_partition")
        elif role in (EvaluatorRole.EXTERNAL_AUDITOR, EvaluatorRole.LEGAL_ADMIN):
            return True
        return False
