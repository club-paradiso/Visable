"""Manual document-family / version / approval layer over the source registry.

Paradiso's manual sources already carry identity and provenance in
``data/source_registry.json`` (id, authority, version, checksum, local path,
active/deprecated). What they did not carry is the *review* dimension: whether a
human has compared an extracted chunk against the original document and approved
it for use as direct evidence.

This module adds that layer without rewriting the existing registry. It composes:

* ``data/source_registry.json``      — untouched, remains the source of identity
* ``data/manual_approval_index.json``— new, review/approval state per document
                                       and per section range

and derives the *document family* view (successive editions of the same manual)
so that a superseded edition is retained and linked rather than deleted.

Governing rules, enforced here rather than left to callers:

1. An unapproved chunk is **never** direct AI evidence. It may still surface as a
   search candidate, explicitly labelled ``needs_review``.
2. The newest approved version of a family is the default; older versions are kept
   so a question about an earlier 시행일 can still be answered from the edition in
   force at that time.
3. A reprocessing failure must not damage the existing approved set — the approval
   index is only ever replaced atomically, and a missing/corrupt index degrades to
   "nothing is approved" rather than to "everything is approved".
4. Table / 별표 extraction failures are tracked separately from body-text warnings,
   because a mangled 별표 is a different (and more dangerous) defect than a
   mid-sentence hyphenation artifact.

Approval states: ``draft`` / ``parsed`` / ``needs_review`` / ``approved`` /
``superseded`` / ``rejected``.

Read-only, stdlib only, never raises on malformed input.

Design influence: the human-approval gate and the "only approved content reaches
the assistant" rule follow ``koul777/Public-Regulation-MCP-Builder`` (MIT). No code
was copied — that project is a Windows Streamlit application; only its governing
principle is adopted. See ``THIRD_PARTY_NOTICES.md``.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

MANUAL_REGISTRY_VERSION = "2026-07-manual-registry-v1"

STATE_DRAFT = "draft"
STATE_PARSED = "parsed"
STATE_NEEDS_REVIEW = "needs_review"
STATE_APPROVED = "approved"
STATE_SUPERSEDED = "superseded"
STATE_REJECTED = "rejected"

APPROVAL_STATES = (
    STATE_DRAFT, STATE_PARSED, STATE_NEEDS_REVIEW,
    STATE_APPROVED, STATE_SUPERSEDED, STATE_REJECTED,
)

# Only these states may back a direct assertion in an answer.
DIRECT_EVIDENCE_STATES = frozenset({STATE_APPROVED})

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SOURCE_REGISTRY_PATH = os.path.join(_REPO_ROOT, "data", "source_registry.json")
APPROVAL_INDEX_PATH = os.path.join(_REPO_ROOT, "data", "manual_approval_index.json")


# ---------------------------------------------------------------------------
# Document family derivation
#
# The registry ids already encode the family ("visa_manual_2026_06_17_pdf"), so a
# family key is derived rather than hand-maintained — a new edition joins its
# family automatically instead of needing a second place to be updated.
# ---------------------------------------------------------------------------
_FAMILY_PATTERNS = (
    (re.compile(r"^visa_manual"), "visa_issuance_manual", "사증발급 안내매뉴얼"),
    (re.compile(r"^stay_manual"), "stay_guide_manual", "외국인체류 안내매뉴얼"),
    (re.compile(r"^dongpo_manual"), "dongpo_manual", "재외동포 안내매뉴얼"),
    (re.compile(r"^hikorea"), "hikorea_notice", "하이코리아 공지"),
    (re.compile(r"^moj_"), "moj_notice", "법무부 공지"),
    (re.compile(r"^law_api"), "law_open_api", "법제처 Open API"),
)


def derive_family(source_id: str) -> Tuple[str, str]:
    """Return ``(family_key, family_title)`` for a registry source id."""
    sid = (source_id or "").strip().lower()
    for pattern, key, title in _FAMILY_PATTERNS:
        if pattern.search(sid):
            return key, title
    return "other", "기타 자료"


def _parse_date(value: Any) -> Optional[date]:
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d", "%Y-%m"):
        try:
            return datetime.strptime(raw[: len(fmt) + 2] if fmt.endswith("S") else raw[: len(fmt)], fmt).date()
        except ValueError:
            continue
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None


@dataclass
class ManualDocumentVersion:
    """One edition of one manual, with provenance and review state."""

    source_id: str
    family_key: str
    family_title: str
    institution: str = ""
    title: str = ""
    title_en: str = ""
    version: str = ""
    source_file: str = ""
    checksum: str = ""
    published_date: str = ""
    effective_date: str = ""
    superseded_date: str = ""
    superseded_by: str = ""
    registry_status: str = ""
    approval_state: str = STATE_NEEDS_REVIEW
    parser: str = ""
    reviewer: str = ""
    reviewed_at: str = ""
    source_confidence: str = ""
    extraction_warnings: List[str] = field(default_factory=list)
    table_extraction_warnings: List[str] = field(default_factory=list)
    has_tables_or_annexes: bool = False
    official_url: str = ""
    section_locator: str = ""
    notes: str = ""

    @property
    def usable_as_direct_evidence(self) -> bool:
        return self.approval_state in DIRECT_EVIDENCE_STATES

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "source_id": self.source_id,
            "family_key": self.family_key,
            "family_title": self.family_title,
            "institution": self.institution,
            "title": self.title,
            "title_en": self.title_en,
            "version": self.version,
            "source_file": self.source_file,
            "checksum": self.checksum,
            "published_date": self.published_date,
            "effective_date": self.effective_date,
            "superseded_date": self.superseded_date,
            "superseded_by": self.superseded_by,
            "registry_status": self.registry_status,
            "approval_state": self.approval_state,
            "parser": self.parser,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
            "source_confidence": self.source_confidence,
            "extraction_warnings": list(self.extraction_warnings),
            "table_extraction_warnings": list(self.table_extraction_warnings),
            "has_tables_or_annexes": self.has_tables_or_annexes,
            "official_url": self.official_url,
            "section_locator": self.section_locator,
            "usable_as_direct_evidence": self.usable_as_direct_evidence,
        }
        return data


def _load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def load_approval_index(path: str = APPROVAL_INDEX_PATH) -> Dict[str, Any]:
    """Load the approval index; a missing/corrupt file approves nothing.

    Fail-closed by construction: if this file cannot be read, every document falls
    back to ``needs_review`` and therefore cannot be used as direct evidence.
    """
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return {"schema_version": "", "documents": {}, "load_error": True}
    documents = payload.get("documents")
    if not isinstance(documents, dict):
        documents = {}
    return {
        "schema_version": payload.get("schema_version", ""),
        "documents": documents,
        "load_error": False,
    }


def load_manual_versions(
    *,
    registry_path: str = SOURCE_REGISTRY_PATH,
    approval_path: str = APPROVAL_INDEX_PATH,
) -> List[ManualDocumentVersion]:
    """Compose registry entries + approval index into document versions."""
    registry = _load_json(registry_path) or {}
    sources = registry.get("sources") if isinstance(registry, dict) else None
    if not isinstance(sources, list):
        sources = []
    approvals = load_approval_index(approval_path)
    approved_docs = approvals["documents"]

    versions: List[ManualDocumentVersion] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id") or "").strip()
        if not source_id:
            continue
        family_key, family_title = derive_family(source_id)
        approval = approved_docs.get(source_id)
        approval = approval if isinstance(approval, dict) else {}

        registry_status = str(source.get("status") or "")
        state = str(approval.get("approval_state") or "").strip().lower()
        if state not in APPROVAL_STATES:
            # No explicit review record -> never silently trusted.
            state = STATE_NEEDS_REVIEW
        if registry_status == "deprecated" and state == STATE_APPROVED:
            # A retired edition stays retrievable but stops being the default.
            state = STATE_SUPERSEDED

        versions.append(ManualDocumentVersion(
            source_id=source_id,
            family_key=family_key,
            family_title=family_title,
            institution=str(source.get("authority") or ""),
            title=str(source.get("title") or ""),
            title_en=str(source.get("title_en") or ""),
            version=str(source.get("version") or ""),
            source_file=str(source.get("local_path") or ""),
            checksum=str(source.get("last_known_hash") or ""),
            published_date=str(source.get("source_date") or ""),
            effective_date=str(approval.get("effective_date") or source.get("source_date") or ""),
            superseded_date=str(approval.get("superseded_date") or ""),
            superseded_by=str(source.get("superseded_by") or ""),
            registry_status=registry_status,
            approval_state=state,
            parser=str(approval.get("parser") or ""),
            reviewer=str(approval.get("reviewer") or ""),
            reviewed_at=str(approval.get("reviewed_at") or ""),
            source_confidence=str(source.get("confidence") or approval.get("source_confidence") or ""),
            extraction_warnings=[str(w) for w in (approval.get("extraction_warnings") or []) if w],
            table_extraction_warnings=[str(w) for w in (approval.get("table_extraction_warnings") or []) if w],
            has_tables_or_annexes=bool(approval.get("has_tables_or_annexes", False)),
            official_url=str(source.get("url") or ""),
            section_locator=str(approval.get("section_locator") or ""),
            notes=str(source.get("notes") or ""),
        ))
    return versions


def group_by_family(versions: Sequence[ManualDocumentVersion]) -> Dict[str, List[ManualDocumentVersion]]:
    """Group versions by family, newest published date first."""
    families: Dict[str, List[ManualDocumentVersion]] = {}
    for version in versions:
        families.setdefault(version.family_key, []).append(version)
    for items in families.values():
        items.sort(
            key=lambda v: (_parse_date(v.published_date) or date.min, v.source_id),
            reverse=True,
        )
    return families


def current_version(
    versions: Sequence[ManualDocumentVersion],
    family_key: str,
    *,
    require_approved: bool = True,
) -> Optional[ManualDocumentVersion]:
    """Newest usable edition of a family.

    With ``require_approved`` (the default) only an approved edition is returned;
    ``None`` means "nothing in this family has been reviewed yet", which callers
    must render as a review-pending state rather than falling back to raw text.
    """
    candidates = [v for v in group_by_family(versions).get(family_key, [])]
    for version in candidates:
        if version.registry_status == "deprecated":
            continue
        if require_approved and not version.usable_as_direct_evidence:
            continue
        return version
    return None


def version_effective_on(
    versions: Sequence[ManualDocumentVersion],
    family_key: str,
    as_of: date,
) -> Optional[ManualDocumentVersion]:
    """Edition in force on ``as_of`` — for "what were the rules back then" questions.

    Older editions are never deleted precisely so this lookup can succeed.
    """
    candidates = group_by_family(versions).get(family_key, [])
    best: Optional[ManualDocumentVersion] = None
    best_date: Optional[date] = None
    for version in candidates:
        effective = _parse_date(version.effective_date) or _parse_date(version.published_date)
        if effective is None or effective > as_of:
            continue
        superseded = _parse_date(version.superseded_date)
        if superseded is not None and superseded <= as_of:
            continue
        if best_date is None or effective > best_date:
            best, best_date = version, effective
    return best


def evidence_gate(version: Optional[ManualDocumentVersion]) -> Dict[str, Any]:
    """Machine-readable verdict on how a manual version may be used."""
    if version is None:
        return {
            "usable_as_direct_evidence": False,
            "searchable": False,
            "approval_state": STATE_NEEDS_REVIEW,
            "reason": "no_version_available",
            "label_key": "manualEvidenceUnavailable",
        }
    if version.approval_state == STATE_REJECTED:
        return {
            "usable_as_direct_evidence": False,
            "searchable": False,
            "approval_state": version.approval_state,
            "reason": "rejected_in_review",
            "label_key": "manualEvidenceRejected",
        }
    if version.usable_as_direct_evidence:
        return {
            "usable_as_direct_evidence": True,
            "searchable": True,
            "approval_state": version.approval_state,
            "reason": "approved",
            "label_key": "manualEvidenceApproved",
        }
    # Everything else is searchable-but-labelled: visible as a candidate, never
    # quoted as settled requirement text.
    return {
        "usable_as_direct_evidence": False,
        "searchable": True,
        "approval_state": version.approval_state,
        "reason": "review_pending",
        "label_key": "manualEvidenceNeedsReview",
    }


def registry_summary(
    *,
    registry_path: str = SOURCE_REGISTRY_PATH,
    approval_path: str = APPROVAL_INDEX_PATH,
) -> Dict[str, Any]:
    """Operator-facing snapshot: families, versions, and approval counts."""
    versions = load_manual_versions(registry_path=registry_path, approval_path=approval_path)
    families = group_by_family(versions)
    counts: Dict[str, int] = {state: 0 for state in APPROVAL_STATES}
    for version in versions:
        counts[version.approval_state] = counts.get(version.approval_state, 0) + 1
    return {
        "registry_version": MANUAL_REGISTRY_VERSION,
        "document_count": len(versions),
        "family_count": len(families),
        "approval_counts": counts,
        "families": {
            key: {
                "family_title": items[0].family_title if items else "",
                "versions": [v.to_dict() for v in items],
                "current": (current_version(versions, key).to_dict()
                            if current_version(versions, key) else None),
            }
            for key, items in families.items()
        },
    }


__all__ = [
    "MANUAL_REGISTRY_VERSION", "APPROVAL_STATES", "DIRECT_EVIDENCE_STATES",
    "STATE_DRAFT", "STATE_PARSED", "STATE_NEEDS_REVIEW", "STATE_APPROVED",
    "STATE_SUPERSEDED", "STATE_REJECTED",
    "ManualDocumentVersion", "derive_family", "load_approval_index",
    "load_manual_versions", "group_by_family", "current_version",
    "version_effective_on", "evidence_gate", "registry_summary",
    "SOURCE_REGISTRY_PATH", "APPROVAL_INDEX_PATH",
]
