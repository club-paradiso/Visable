"""Artemis Legal Review Governance & Workflow Subsystem (Mission 004-C Prototype).

Provides a local, non-authoritative prototype for tracking human legal expert
review workflows, controlled state transitions, evidence provenance checks,
and audit trail ledgers for Artemis benchmark candidates.

CRITICAL GOVERNANCE RULES & ARCHITECTURAL LIMITATIONS:
1. Local Prototype / Non-Authoritative: Caller-supplied reviewer identifiers and
   is_human flags are self-asserted and unauthenticated in this local prototype.
   They DO NOT constitute cryptographic identity verification or authenticated human
   legal sign-off.
2. AI Identifier Filtering: Heuristic name matching (is_ai_identifier) rejects obvious
   automated bot identifiers, but cannot prevent an automated caller from supplying an
   ordinary human name. Therefore, name checks must never be claimed as absolute
   impersonation prevention.
3. Authoritative Gold Promotion Disabled: Authoritative promotion to 'official_gold'
   is strictly disabled fail-closed in this local prototype. Promotion requires an
   external signed attestation ceremony with cryptographic verification (e.g., PKI digital
   signature or verified OAuth legal counsel token).
4. Mandatory Official Evidence Snapshot: Recording an approval strictly requires an
   explicit, non-empty evidence snapshot text matching the item's official source references.
   Falling back to question/answer text or inferred excerpts is strictly prohibited.
5. Snapshot & Evidence Integrity: If the candidate item's evidence excerpt was modified
   after review, or if the source content hash mismatches the snapshot, validation fails.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime as dt
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

BOOTSTRAP_DIR = Path(__file__).resolve().parent
EXPERIMENT_ROOT = BOOTSTRAP_DIR.parent
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"
REVIEWS_DIR = BOOTSTRAP_DIR / "reviews"
LEDGER_PATH = REVIEWS_DIR / "legal_review_ledger.json"

if str(BOOTSTRAP_DIR) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_DIR))

import artemis_eval  # noqa: E402


class ReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    IN_REVIEW = "in_review"
    VERIFIED_BY_HUMAN = "verified_by_human"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    SUPERSEDED = "superseded"


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"
    SUPERSEDE = "supersede"


class InvalidTransitionError(ValueError):
    """Raised when an illegal review state transition is attempted."""
    pass


class AIApprovalForbiddenError(PermissionError):
    """Raised when an AI or automated agent attempts to approve an item."""
    pass


class ReviewIntegrityError(ValueError):
    """Raised when review metadata or evidence cryptographic snapshot fails verification."""
    pass


class AuthoritativeGoldPromotionDisabledError(ReviewIntegrityError):
    """Raised when an attempt is made to promote an item to official_gold in this local prototype.

    Authoritative promotion to official_gold is strictly disabled in local prototypes:
    caller-asserted reviewer identities, local boolean flags (is_human=True), and local
    ledger records lack independent cryptographic authentication (e.g., PKI digital signatures,
    OAuth-verified legal counsel tokens, or certified administrative agent attestation tokens).
    All candidate items must remain unverified candidates until external attestation is supplied.
    """
    pass


FORBIDDEN_AI_IDENTIFIERS = frozenset({
    "ai", "bot", "gemini", "claude", "gpt", "agent", "subsystem", "artemis",
    "assistant", "copilot", "auto", "automated", "llm", "pipeline"
})

GROUP_A_PRIORITY_IDS = frozenset({
    "ARTEMIS-004-DEV-013", "ARTEMIS-004-DEV-014",
    "ARTEMIS-004-HLD-004", "ARTEMIS-004-HLD-007", "ARTEMIS-004-HLD-008",
    "ARTEMIS-004-HLD-013", "ARTEMIS-004-HLD-014",
    "ARTEMIS-004-HLD-023", "ARTEMIS-004-HLD-027", "ARTEMIS-004-HLD-028",
    "ARTEMIS-004-HLD-031", "ARTEMIS-004-HLD-032",
    "ARTEMIS-004-HLD-033", "ARTEMIS-004-HLD-034",
    "ARTEMIS-004-HLD-036", "ARTEMIS-004-HLD-037",
})


def is_ai_identifier(name: Optional[str]) -> bool:
    """Checks whether an actor identifier contains common automated/AI substrings.

    NOTE: This is a basic sanitization heuristic, not an authenticated identity check.
    An automated caller can easily pass an ordinary human name.
    """
    if not name:
        return False
    folded = re.sub(r'[^a-zA-Z0-9가-힣]', '', name.lower())
    for token in FORBIDDEN_AI_IDENTIFIERS:
        if token in folded:
            return True
    return False


def compute_evidence_snapshot_hash(text: str) -> str:
    """Computes SHA-256 of normalized evidence text."""
    norm = unicodedata.normalize("NFC", text or "").strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


@dataclass
class StateTransition:
    timestamp: str
    from_status: str
    to_status: str
    actor_id: str
    is_human: bool
    reason: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "actor_id": self.actor_id,
            "is_human": self.is_human,
            "reason": self.reason,
            "notes": self.notes,
        }


@dataclass
class ArtemisReviewRecord:
    record_id: str
    item_id: str
    split: str
    group: str
    question: str
    proposed_answer: str
    evidence_references: List[Dict[str, Any]]
    legal_exceptions: Optional[str] = None
    applicable_conditions: Optional[str] = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    reviewer_id: Optional[str] = None
    is_human_reviewer: bool = False
    reviewed_at: Optional[str] = None
    decision: Optional[ReviewDecision] = None
    decision_reason: Optional[str] = None
    evidence_snapshot_sha256: Optional[str] = None
    updated_at: str = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())
    transition_history: List[StateTransition] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "item_id": self.item_id,
            "split": self.split,
            "group": self.group,
            "question": self.question,
            "proposed_answer": self.proposed_answer,
            "evidence_references": copy.deepcopy(self.evidence_references),
            "legal_exceptions": self.legal_exceptions,
            "applicable_conditions": self.applicable_conditions,
            "review_status": self.review_status.value if isinstance(self.review_status, ReviewStatus) else self.review_status,
            "reviewer_id": self.reviewer_id,
            "is_human_reviewer": self.is_human_reviewer,
            "reviewed_at": self.reviewed_at,
            "decision": self.decision.value if isinstance(self.decision, ReviewDecision) else self.decision,
            "decision_reason": self.decision_reason,
            "evidence_snapshot_sha256": self.evidence_snapshot_sha256,
            "updated_at": self.updated_at,
            "transition_history": [t.to_dict() for t in self.transition_history],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ArtemisReviewRecord:
        record = cls(
            record_id=data["record_id"],
            item_id=data["item_id"],
            split=data.get("split", "dev"),
            group=data.get("group", "standard"),
            question=data.get("question", ""),
            proposed_answer=data.get("proposed_answer", ""),
            evidence_references=data.get("evidence_references", []),
            legal_exceptions=data.get("legal_exceptions"),
            applicable_conditions=data.get("applicable_conditions"),
            review_status=ReviewStatus(data.get("review_status", "unreviewed")),
            reviewer_id=data.get("reviewer_id"),
            is_human_reviewer=bool(data.get("is_human_reviewer", False)),
            reviewed_at=data.get("reviewed_at"),
            decision=ReviewDecision(data["decision"]) if data.get("decision") else None,
            decision_reason=data.get("decision_reason"),
            evidence_snapshot_sha256=data.get("evidence_snapshot_sha256"),
            updated_at=data.get("updated_at", dt.datetime.now(dt.timezone.utc).isoformat()),
        )
        for t in data.get("transition_history", []):
            record.transition_history.append(StateTransition(
                timestamp=t["timestamp"],
                from_status=t["from_status"],
                to_status=t["to_status"],
                actor_id=t["actor_id"],
                is_human=t["is_human"],
                reason=t.get("reason"),
                notes=t.get("notes"),
            ))
        return record


class LegalReviewLedger:
    """Audit ledger maintaining all candidate items and their human review governance state."""

    def __init__(self, records: Optional[Dict[str, ArtemisReviewRecord]] = None):
        self.records: Dict[str, ArtemisReviewRecord] = records or {}

    @classmethod
    def load_or_initialize(cls, ledger_path: Path = LEDGER_PATH,
                           candidates_path: Optional[Path] = None) -> LegalReviewLedger:
        """Loads existing ledger if present, otherwise initializes from candidates benchmark."""
        if ledger_path.exists():
            data = json.loads(ledger_path.read_text(encoding="utf-8"))
            records = {}
            for row in data.get("records", []):
                rec = ArtemisReviewRecord.from_dict(row)
                records[rec.item_id] = rec
            return cls(records)

        # Initialize from candidate benchmark file
        cand_p = candidates_path or (BENCHMARKS_DIR / "artemis_eval_candidates_60.json")
        if not cand_p.exists():
            return cls({})

        data = json.loads(cand_p.read_text(encoding="utf-8"))
        records = {}
        for item in data.get("items", []):
            cid = item["id"]
            rec_id = f"rev_{cid.replace('ARTEMIS-004-', '')}"
            meta = item.get("metadata", {})
            group = (
                "Group A (Priority Review)"
                if cid in GROUP_A_PRIORITY_IDS
                else "Group B (Standard Legal Candidate)"
            )
            ev_refs = []
            for ev in item.get("evidence", []):
                src = ev.get("source", {})
                ev_refs.append({
                    "evidence_id": ev.get("id"),
                    "title": ev.get("title"),
                    "source_url": src.get("source_url"),
                    "document_id": src.get("document_id"),
                    "provision": src.get("provision"),
                    "effective_date": src.get("effective_date"),
                    "content_sha256": src.get("content_sha256") or src.get("approved_sha256"),
                    "text_excerpt": ev.get("text", "")[:300]
                })

            req_facts = item.get("expected", {}).get("source_fidelity", {}).get("required_facts", [])
            proposed = req_facts[0] if req_facts else (item.get("expected", {}).get("allowed_statuses") or [""])[0]

            records[cid] = ArtemisReviewRecord(
                record_id=rec_id,
                item_id=cid,
                split=meta.get("split", "dev"),
                group=group,
                question=item.get("question", ""),
                proposed_answer=str(proposed),
                evidence_references=ev_refs,
                review_status=ReviewStatus.UNREVIEWED,
                is_human_reviewer=False
            )
        ledger = cls(records)
        ledger.save(ledger_path)
        return ledger

    def save(self, ledger_path: Path = LEDGER_PATH) -> None:
        """Persists ledger to JSON file."""
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "artemis-ledger/1.0",
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "total_items": len(self.records),
            "status_counts": self.get_status_counts(),
            "records": [rec.to_dict() for rec in self.records.values()]
        }
        ledger_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_status_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {st.value: 0 for st in ReviewStatus}
        for rec in self.records.values():
            st_val = rec.review_status.value if isinstance(rec.review_status, ReviewStatus) else rec.review_status
            counts[st_val] = counts.get(st_val, 0) + 1
        return counts

    def claim_for_review(self, item_id: str, reviewer_id: str, is_human: bool = True,
                         notes: Optional[str] = None) -> ArtemisReviewRecord:
        """Transitions an item from UNREVIEWED to IN_REVIEW."""
        if item_id not in self.records:
            raise KeyError(f"Item ID '{item_id}' not found in review ledger")
        rec = self.records[item_id]

        if not reviewer_id or not reviewer_id.strip():
            raise ReviewIntegrityError("Reviewer ID cannot be empty")
        if not is_human or is_ai_identifier(reviewer_id):
            raise AIApprovalForbiddenError(f"Automated AI actor '{reviewer_id}' cannot claim review items")

        if rec.review_status not in (ReviewStatus.UNREVIEWED, ReviewStatus.NEEDS_REVISION):
            raise InvalidTransitionError(
                f"Cannot claim item '{item_id}' in status '{rec.review_status.value}'. Must be 'unreviewed' or 'needs_revision'."
            )

        now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
        prev_status = rec.review_status.value
        rec.review_status = ReviewStatus.IN_REVIEW
        rec.reviewer_id = reviewer_id.strip()
        rec.is_human_reviewer = True
        rec.updated_at = now_iso
        rec.transition_history.append(StateTransition(
            timestamp=now_iso,
            from_status=prev_status,
            to_status=ReviewStatus.IN_REVIEW.value,
            actor_id=reviewer_id.strip(),
            is_human=True,
            reason="Claimed by legal reviewer for active examination",
            notes=notes
        ))
        return rec

    def record_decision(
        self,
        item_id: str,
        decision: ReviewDecision | str,
        reviewer_id: str,
        reason: str,
        is_human: bool = True,
        evidence_snapshot_text: Optional[str] = None,
        legal_exceptions: Optional[str] = None,
        applicable_conditions: Optional[str] = None,
        notes: Optional[str] = None
    ) -> ArtemisReviewRecord:
        """Records a human legal expert review decision with strict state transition enforcement."""
        if item_id not in self.records:
            raise KeyError(f"Item ID '{item_id}' not found in review ledger")
        rec = self.records[item_id]

        if isinstance(decision, str):
            try:
                decision = ReviewDecision(decision)
            except ValueError:
                raise ValueError(f"Invalid decision '{decision}'. Expected one of: {[d.value for d in ReviewDecision]}")

        # Governance Check 1: AI cannot approve or decide on human behalf
        if not is_human or is_ai_identifier(reviewer_id):
            raise AIApprovalForbiddenError(f"Automated AI actor '{reviewer_id}' cannot record human legal decisions")

        # Governance Check 2: Reviewer ID and Reason cannot be empty
        if not reviewer_id or not reviewer_id.strip():
            raise ReviewIntegrityError("Reviewer ID cannot be empty")
        if not reason or len(reason.strip()) < 5:
            raise ReviewIntegrityError("Decision reason must be substantive (at least 5 characters)")

        # Governance Check 3: Current status must allow decision
        if rec.review_status != ReviewStatus.IN_REVIEW:
            if rec.review_status == ReviewStatus.VERIFIED_BY_HUMAN and decision == ReviewDecision.SUPERSEDE:
                pass  # Supersede is allowed from verified_by_human
            else:
                raise InvalidTransitionError(
                    f"Item '{item_id}' is in status '{rec.review_status.value}'. Must be 'in_review' to record decisions."
                )

        now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
        prev_status = rec.review_status.value

        if decision == ReviewDecision.APPROVE:
            # Verification strictly requires an explicit, non-empty evidence snapshot from official source
            if not evidence_snapshot_text or not evidence_snapshot_text.strip():
                raise ReviewIntegrityError(
                    "Official evidence snapshot text is strictly required for approval. "
                    "Approvals cannot be recorded without an explicit, non-empty official evidence snapshot "
                    "(falling back to question/answer or cached text is prohibited)."
                )

            if not rec.evidence_references:
                raise ReviewIntegrityError(
                    f"Item '{item_id}' has no official evidence references in ledger; cannot approve without official source reference."
                )

            snap_hash = compute_evidence_snapshot_hash(evidence_snapshot_text)
            snap_norm = unicodedata.normalize("NFC", evidence_snapshot_text).strip()

            # Cross-check snapshot against record's official evidence references
            matched = False
            for ref in rec.evidence_references:
                ref_hash = ref.get("content_sha256")
                excerpt = ref.get("text_excerpt", "")
                excerpt_norm = unicodedata.normalize("NFC", excerpt).strip()
                if ref_hash and snap_hash == ref_hash:
                    matched = True
                    break
                if excerpt and snap_hash == compute_evidence_snapshot_hash(excerpt):
                    matched = True
                    break
                if excerpt_norm and (snap_norm in excerpt_norm or excerpt_norm in snap_norm):
                    matched = True
                    break

            if not matched:
                raise ReviewIntegrityError(
                    f"Provided evidence snapshot text does not match any official evidence references for item '{item_id}'. "
                    f"Snapshot hash: {snap_hash}"
                )

            target_status = ReviewStatus.VERIFIED_BY_HUMAN
            rec.review_status = target_status
            rec.decision = ReviewDecision.APPROVE
            rec.decision_reason = reason.strip()
            rec.reviewer_id = reviewer_id.strip()
            rec.is_human_reviewer = True
            rec.reviewed_at = now_iso.split("T")[0]
            rec.evidence_snapshot_sha256 = snap_hash
            if legal_exceptions:
                rec.legal_exceptions = legal_exceptions
            if applicable_conditions:
                rec.applicable_conditions = applicable_conditions

        elif decision == ReviewDecision.REJECT:
            target_status = ReviewStatus.REJECTED
            rec.review_status = target_status
            rec.decision = ReviewDecision.REJECT
            rec.decision_reason = reason.strip()
            rec.reviewer_id = reviewer_id.strip()
            rec.is_human_reviewer = True
            rec.reviewed_at = now_iso.split("T")[0]

        elif decision == ReviewDecision.REQUEST_REVISION:
            target_status = ReviewStatus.NEEDS_REVISION
            rec.review_status = target_status
            rec.decision = ReviewDecision.REQUEST_REVISION
            rec.decision_reason = reason.strip()
            rec.reviewer_id = reviewer_id.strip()
            rec.is_human_reviewer = True
            rec.reviewed_at = now_iso.split("T")[0]

        elif decision == ReviewDecision.SUPERSEDE:
            target_status = ReviewStatus.SUPERSEDED
            rec.review_status = target_status
            rec.decision = ReviewDecision.SUPERSEDE
            rec.decision_reason = reason.strip()
            rec.reviewer_id = reviewer_id.strip()
            rec.is_human_reviewer = True
            rec.reviewed_at = now_iso.split("T")[0]

        rec.updated_at = now_iso
        rec.transition_history.append(StateTransition(
            timestamp=now_iso,
            from_status=prev_status,
            to_status=target_status.value,
            actor_id=reviewer_id.strip(),
            is_human=True,
            reason=reason.strip(),
            notes=notes
        ))
        return rec

    def validate_item_evidence_integrity(self, item: Dict[str, Any]) -> None:
        """Validates that a candidate item matches its ledger review record and evidence snapshot.

        Raises ReviewIntegrityError if:
        - The item is not recorded in the ledger or not verified_by_human.
        - The official evidence list is missing or empty.
        - Evidence source provenance or required legal metadata is missing.
        - The item's evidence excerpt has been modified after review (hash mismatch).
        - The source content_sha256 contradicts the snapshot hash.
        """
        cid = item.get("id")
        if cid not in self.records:
            raise ReviewIntegrityError(f"Item '{cid}' has no record in the legal review ledger")
        rec = self.records[cid]

        if rec.review_status != ReviewStatus.VERIFIED_BY_HUMAN:
            raise ReviewIntegrityError(
                f"Item '{cid}' review_status is '{rec.review_status.value}' (must be 'verified_by_human')"
            )

        ev_list = item.get("evidence", [])
        if not ev_list:
            raise ReviewIntegrityError(f"Cannot promote item '{cid}': official evidence list is missing or empty")

        if not rec.evidence_snapshot_sha256:
            raise ReviewIntegrityError(f"Item '{cid}' in ledger is missing evidence_snapshot_sha256")

        # Check evidence sources and cryptographic snapshot match
        item_ev_hashes = []
        for ev in ev_list:
            src = ev.get("source", {})
            if src.get("provenance") not in ("official_manual", "official_notice"):
                raise ReviewIntegrityError(
                    f"Evidence '{ev.get('id')}' provenance '{src.get('provenance')}' is not official"
                )
            for req_field in ("document_id", "provision", "effective_date", "source_url"):
                if not src.get(req_field):
                    raise ReviewIntegrityError(
                        f"Evidence '{ev.get('id')}' source is missing required legal metadata '{req_field}'"
                    )

            ev_text = ev.get("text", "")
            if not ev_text.strip():
                raise ReviewIntegrityError(f"Evidence '{ev.get('id')}' text excerpt is empty")

            ev_hash = compute_evidence_snapshot_hash(ev_text)
            item_ev_hashes.append(ev_hash)

            src_hash = src.get("content_sha256")
            if src_hash and src_hash != ev_hash:
                raise ReviewIntegrityError(
                    f"Source content_sha256 '{src_hash}' does not match evidence text hash '{ev_hash}'"
                )

        if rec.evidence_snapshot_sha256 not in item_ev_hashes:
            raise ReviewIntegrityError(
                f"Evidence integrity mismatch for item '{cid}': ledger snapshot hash '{rec.evidence_snapshot_sha256}' "
                f"does not match item evidence hashes {item_ev_hashes}. Evidence was modified after review."
            )

    def promote_to_gold(
        self,
        item: Dict[str, Any],
        external_attestation: Optional[Dict[str, Any]] = None,
        _allow_test_promotion: bool = False,
    ) -> Dict[str, Any]:
        """Promotes an item to official_gold IF AND ONLY IF independently authenticated.

        FAIL-CLOSED GOVERNANCE:
        - In this local prototype, authoritative promotion to 'official_gold' is disabled
          by default because caller-supplied reviewer identities and local ledger flags
          lack cryptographic authentication.
        - An external cryptographic attestation bundle is required.
        - If external_attestation is None or unverified, raises AuthoritativeGoldPromotionDisabledError.
        - If evidence text was modified or snapshot hash mismatches, raises ReviewIntegrityError.
        """
        cid = item.get("id")
        self.validate_item_evidence_integrity(item)
        rec = self.records[cid]

        if external_attestation is None:
            raise AuthoritativeGoldPromotionDisabledError(
                f"Authoritative promotion to official_gold is strictly disabled for item '{cid}' in this local prototype. "
                "Caller-supplied reviewer identifiers and local ledger state lack independent cryptographic authentication. "
                "Promotion to official_gold requires external authenticated human attestation (e.g. PKI / OAuth legal token)."
            )

        # Validate external attestation structure
        for req_field in ("signer_identity", "attestation_token", "signature_sha256", "signed_at", "evidence_snapshot_sha256"):
            if not external_attestation.get(req_field):
                raise ReviewIntegrityError(f"External attestation missing required field '{req_field}'")

        signer = external_attestation["signer_identity"]
        if is_ai_identifier(signer):
            raise AIApprovalForbiddenError(f"External attestation signer '{signer}' is an AI identifier")

        if signer != rec.reviewer_id:
            raise ReviewIntegrityError(
                f"External attestation signer '{signer}' does not match ledger reviewer '{rec.reviewer_id}'"
            )

        if external_attestation["evidence_snapshot_sha256"] != rec.evidence_snapshot_sha256:
            raise ReviewIntegrityError(
                f"External attestation evidence hash '{external_attestation['evidence_snapshot_sha256']}' "
                f"does not match ledger snapshot '{rec.evidence_snapshot_sha256}'"
            )

        if not _allow_test_promotion:
            raise AuthoritativeGoldPromotionDisabledError(
                "External cryptographic PKI authority verification service is not connected in this local environment; "
                "authoritative official_gold certification is disabled fail-closed."
            )

        promoted = copy.deepcopy(item)
        promoted["metadata"]["candidate_status"] = "official_gold"
        promoted["metadata"]["needs_human_review"] = False
        promoted["metadata"]["is_synthetic"] = False
        promoted["metadata"]["legal_review_notes"] = (
            f"Verified by {rec.reviewer_id} on {rec.reviewed_at} "
            f"(Attestation: {external_attestation['attestation_token'][:16]}...)"
        )

        for ev in promoted.get("evidence", []):
            src = ev.get("source", {})
            if src.get("provenance") in ("official_manual", "official_notice"):
                src["approval_state"] = "approved"
                src["review_status"] = "verified_by_human"
                src["reviewed_by"] = rec.reviewer_id
                src["reviewed_at"] = rec.reviewed_at
                src["approved_sha256"] = artemis_eval.approval_hash(ev.get("text", ""))

        return promoted

    def generate_markdown_report(self) -> str:
        """Produces an audit summary report of the legal review ledger."""
        counts = self.get_status_counts()
        lines = [
            "# Artemis 법률 검토 거버넌스 원장 보고서 (Legal Review Ledger Report)",
            f"- **작성 일자**: {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"- **총 후보 문항**: {len(self.records)}건",
            "- **원장 성격**: 로컬 프로토타입 추적 원장 (비권위적, Non-Authoritative Prototype)",
            "- **거버넌스 제약**: 검토자 서명은 로컬 기록용이며, 외부 암호학적 서명(PKI) 부재 시 공식 골드 승격 비활성화 (Fail-Closed)",
            "",
            "## 1. 검토 상태 집계",
            f"- **검토 미진행 (`unreviewed`)**: {counts[ReviewStatus.UNREVIEWED.value]}건",
            f"- **검토 진행 중 (`in_review`)**: {counts[ReviewStatus.IN_REVIEW.value]}건",
            f"- **사람 전문가 승인 (`verified_by_human`)**: {counts[ReviewStatus.VERIFIED_BY_HUMAN.value]}건 (외부 암호학적 서명 대기)",
            f"- **반려 (`rejected`)**: {counts[ReviewStatus.REJECTED.value]}건",
            f"- **수정 요청 (`needs_revision`)**: {counts[ReviewStatus.NEEDS_REVISION.value]}건",
            f"- **개정 대체 (`superseded`)**: {counts[ReviewStatus.SUPERSEDED.value]}건",
            "",
            "## 2. 세부 검토 현황표",
            "| 문항 ID | 그룹 | 분할 | 현재 상태 | 검토자 | 판정 일자 | 비고 |",
            "|:---|:---|:---:|:---:|:---|:---:|:---|"
        ]
        for rec in sorted(self.records.values(), key=lambda r: r.item_id):
            st = rec.review_status.value if isinstance(rec.review_status, ReviewStatus) else rec.review_status
            reviewer = rec.reviewer_id or "-"
            rev_date = rec.reviewed_at or "-"
            reason = (rec.decision_reason or "")[:30].replace("|", "\\|")
            lines.append(f"| `{rec.item_id}` | {rec.group} | `{rec.split}` | `{st}` | {reviewer} | {rev_date} | {reason} |")

        return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Artemis Legal Review Governance CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # list
    list_p = subparsers.add_parser("list", help="List review items and status")
    list_p.add_argument("--status", choices=[s.value for s in ReviewStatus], help="Filter by review status")

    # claim
    claim_p = subparsers.add_parser("claim", help="Claim an item for human review")
    claim_p.add_argument("item_id", help="Benchmark item ID (e.g. ARTEMIS-004-DEV-001)")
    claim_p.add_argument("--reviewer", required=True, help="Human reviewer identifier")
    claim_p.add_argument("--notes", help="Optional claim notes")

    # decide
    decide_p = subparsers.add_parser("decide", help="Record a human legal review decision")
    decide_p.add_argument("item_id", help="Benchmark item ID")
    decide_p.add_argument("--decision", required=True, choices=[d.value for d in ReviewDecision], help="Review decision")
    decide_p.add_argument("--reviewer", required=True, help="Human reviewer identifier")
    decide_p.add_argument("--reason", required=True, help="Substantive reason for decision")
    decide_p.add_argument("--evidence-snapshot", dest="evidence_snapshot_text", help="Explicit text excerpt from official gazette or manual for approval snapshot")
    decide_p.add_argument("--notes", help="Optional notes")

    # report
    report_p = subparsers.add_parser("report", help="Generate ledger markdown report")
    report_p.add_argument("--out", type=Path, help="Output path for markdown report")

    args = parser.parse_args()
    ledger = LegalReviewLedger.load_or_initialize()

    if args.subcommand == "list":
        records = [r for r in ledger.records.values() if not args.status or r.review_status.value == args.status]
        print(f"Total records ({len(records)}/{len(ledger.records)}):")
        for r in records:
            st = r.review_status.value if isinstance(r.review_status, ReviewStatus) else r.review_status
            print(f"  [{st.upper():<18}] {r.item_id:<22} ({r.split}) {r.question[:45]}...")

    elif args.subcommand == "claim":
        rec = ledger.claim_for_review(args.item_id, args.reviewer, is_human=True, notes=args.notes)
        ledger.save()
        print(f"Item '{args.item_id}' claimed by '{args.reviewer}' (status: in_review).")

    elif args.subcommand == "decide":
        rec = ledger.record_decision(
            args.item_id,
            decision=args.decision,
            reviewer_id=args.reviewer,
            reason=args.reason,
            is_human=True,
            evidence_snapshot_text=args.evidence_snapshot_text,
            notes=args.notes
        )
        ledger.save()
        print(f"Decision '{args.decision}' recorded for '{args.item_id}' by '{args.reviewer}' (status: {rec.review_status.value}).")

    elif args.subcommand == "report":
        md = ledger.generate_markdown_report()
        out_p = args.out or (REVIEWS_DIR / "legal_review_ledger_report.md")
        out_p.write_text(md, encoding="utf-8")
        print(f"Ledger report written to {out_p}")


if __name__ == "__main__":
    main()
