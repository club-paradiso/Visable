"""Artemis Legal Source Versioning and Provenance Infrastructure (Mission 005-A).

Tracks authoritative immigration legal sources, statutes, enforcement decrees,
ministerial notices, and administrative manuals over time.
Provides immutable version references, change diffing, and candidate invalidation analysis.

CRITICAL GOVERNANCE RULES:
1. Old legal evidence must NEVER be silently overwritten.
2. Every source record is keyed by an immutable source_id and version_id.
3. Track publication_date, effective_date, retrieval_date, and content integrity hash.
4. Detect superseded sources and conflicting provisions automatically.
5. Generate version-difference reports identifying which evaluation items may be affected.
"""
from __future__ import annotations

import copy
import dataclasses
import datetime as dt
import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple


class LegalSourceType(str, Enum):
    STATUTE = "statute"                       # 법률 (출입국관리법 등)
    ENFORCEMENT_DECREE = "enforcement_decree" # 대통령령 (출입국관리법 시행령 등)
    ENFORCEMENT_RULE = "enforcement_rule"     # 법무부령 (출입국관리법 시행규칙 등)
    MINISTERIAL_NOTICE = "ministerial_notice" # 법무부 고시
    ADMINISTRATIVE_MANUAL = "administrative_manual" # 체류관리 길라잡이 / 업무편람
    INTERNAL_SECURITY = "internal_security"   # 시스템 안전성 및 프롬프트 가이드


class LegalAuditClassification(str, Enum):
    SOURCE_LOCATED = "source_located"
    SOURCE_NOT_FOUND = "source_not_found"
    VERSION_MISMATCH = "version_mismatch"
    EXCERPT_MISMATCH = "excerpt_mismatch"
    REQUIRES_INTERPRETATION = "requires_interpretation"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    SUPERSEDED_SOURCE = "superseded_source"


@dataclass(frozen=True)
class LegalSourceVersion:
    source_id: str
    version_id: str
    title: str
    issuing_authority: str
    source_type: LegalSourceType
    publication_date: str
    effective_date: str
    retrieval_date: str
    official_url: str
    provision: str
    excerpt_text: str
    content_sha256: str
    is_superseded: bool = False
    superseded_by: Optional[str] = None
    prior_versions: List[str] = field(default_factory=list)
    conflict_indicators: List[str] = field(default_factory=list)
    review_status: str = "pending_human_review"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "version_id": self.version_id,
            "title": self.title,
            "issuing_authority": self.issuing_authority,
            "source_type": self.source_type.value if isinstance(self.source_type, LegalSourceType) else self.source_type,
            "publication_date": self.publication_date,
            "effective_date": self.effective_date,
            "retrieval_date": self.retrieval_date,
            "official_url": self.official_url,
            "provision": self.provision,
            "excerpt_text": self.excerpt_text,
            "content_sha256": self.content_sha256,
            "is_superseded": self.is_superseded,
            "superseded_by": self.superseded_by,
            "prior_versions": list(self.prior_versions),
            "conflict_indicators": list(self.conflict_indicators),
            "review_status": self.review_status,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LegalSourceVersion:
        st = data.get("source_type", "statute")
        if isinstance(st, str):
            try:
                st = LegalSourceType(st)
            except ValueError:
                st = LegalSourceType.STATUTE
        return cls(
            source_id=data["source_id"],
            version_id=data["version_id"],
            title=data["title"],
            issuing_authority=data["issuing_authority"],
            source_type=st,
            publication_date=data["publication_date"],
            effective_date=data["effective_date"],
            retrieval_date=data["retrieval_date"],
            official_url=data.get("official_url", ""),
            provision=data.get("provision", ""),
            excerpt_text=data.get("excerpt_text", ""),
            content_sha256=data.get("content_sha256", ""),
            is_superseded=data.get("is_superseded", False),
            superseded_by=data.get("superseded_by"),
            prior_versions=list(data.get("prior_versions", [])),
            conflict_indicators=list(data.get("conflict_indicators", [])),
            review_status=data.get("review_status", "pending_human_review"),
            notes=data.get("notes", ""),
        )


def compute_content_sha256(text: str) -> str:
    norm = unicodedata.normalize("NFC", text or "").strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


class LegalSourceCatalog:
    """Immutable, append-only registry of versioned legal sources."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path
        self._sources: Dict[Tuple[str, str], LegalSourceVersion] = {}
        if storage_path and storage_path.exists():
            self.load(storage_path)

    def register(self, source: LegalSourceVersion) -> None:
        key = (source.source_id, source.version_id)
        if key in self._sources:
            existing = self._sources[key]
            if existing.content_sha256 != source.content_sha256:
                raise ValueError(
                    f"Integrity conflict: source {key} already exists with differing SHA-256."
                )
        self._sources[key] = source

    def get(self, source_id: str, version_id: str) -> Optional[LegalSourceVersion]:
        return self._sources.get((source_id, version_id))

    def list_versions_for_source(self, source_id: str) -> List[LegalSourceVersion]:
        return [v for (sid, _), v in self._sources.items() if sid == source_id]

    def get_latest_version(self, source_id: str) -> Optional[LegalSourceVersion]:
        versions = self.list_versions_for_source(source_id)
        if not versions:
            return None
        # Sort by effective_date descending
        return sorted(versions, key=lambda v: (v.effective_date, v.version_id), reverse=True)[0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "catalog_version": "artemis-source-catalog/1.0",
            "sources": [s.to_dict() for s in self._sources.values()],
        }

    def save(self, path: Optional[Path] = None) -> None:
        target = path or self.storage_path
        if not target:
            raise ValueError("No storage path provided.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def load(self, path: Path) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for s_dict in data.get("sources", []):
            self.register(LegalSourceVersion.from_dict(s_dict))


@dataclass
class VersionDifferenceImpact:
    item_id: str
    source_id: str
    old_version_id: str
    new_version_id: str
    change_type: str  # e.g. "superseded", "provision_amended", "amount_changed"
    impact_level: str # "high", "medium", "low"
    description: str
    recommended_action: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


def generate_version_difference_report(
    catalog: LegalSourceCatalog,
    benchmark_items: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Generates a structured report identifying candidate benchmark items affected by source changes."""
    impacts: List[VersionDifferenceImpact] = []

    for item in benchmark_items:
        item_id = item.get("id") or item.get("item_id", "UNKNOWN")
        legal_basis = item.get("legal_basis", {})
        doc_version = str(legal_basis.get("document_version", ""))
        claimed_basis = str(legal_basis.get("claimed_basis", ""))

        # Check if the item references a known source
        for (sid, vid), s_ver in catalog._sources.items():
            if s_ver.is_superseded:
                latest = catalog.get_latest_version(sid)
                if latest and latest.version_id != vid:
                    # Check if candidate references the superseded version and not the latest version
                    references_old = (vid in doc_version) or (sid in claimed_basis and latest.version_id not in doc_version)
                    if references_old:
                        impacts.append(
                            VersionDifferenceImpact(
                                item_id=item_id,
                                source_id=sid,
                                old_version_id=vid,
                                new_version_id=latest.version_id,
                                change_type="superseded",
                                impact_level="high",
                                description=(
                                    f"Candidate references superseded source version {vid} "
                                    f"replaced by {latest.version_id} (effective {latest.effective_date})."
                                ),
                                recommended_action="Update candidate expected answer and evidence excerpt to latest provision.",
                            )
                        )

    return {
        "report_version": "artemis-version-diff/1.0",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_impacts": len(impacts),
        "impacts": [i.to_dict() for i in impacts],
    }
