"""VISABLE Content Operations Studio — Data Models & Schemas.

Covers:
- RBAC operator roles (viewer, editor, reviewer, publisher)
- Scenario & Draft data structures
- Office override entities
- Publishing validation & release reports
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class OperatorRole(str, Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    PUBLISHER = "publisher"


ROLE_HIERARCHY = {
    OperatorRole.VIEWER: 1,
    OperatorRole.EDITOR: 2,
    OperatorRole.REVIEWER: 3,
    OperatorRole.PUBLISHER: 4,
}


def can_edit(role: str | OperatorRole) -> bool:
    r = OperatorRole(role) if isinstance(role, str) else role
    return ROLE_HIERARCHY.get(r, 0) >= ROLE_HIERARCHY[OperatorRole.EDITOR]


def can_review(role: str | OperatorRole) -> bool:
    r = OperatorRole(role) if isinstance(role, str) else role
    return ROLE_HIERARCHY.get(r, 0) >= ROLE_HIERARCHY[OperatorRole.REVIEWER]


def can_publish(role: str | OperatorRole) -> bool:
    r = OperatorRole(role) if isinstance(role, str) else role
    return ROLE_HIERARCHY.get(r, 0) >= ROLE_HIERARCHY[OperatorRole.PUBLISHER]


class ChecklistReviewState(str, Enum):
    COMPILED_NEEDS_REVIEW = "COMPILED_NEEDS_REVIEW"
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"


class DiffType(str, Enum):
    ADDITIONAL_REQUIRED = "additional_required"
    CONDITIONAL_ADDED = "conditional_added"
    EXEMPTION_GRANTED = "exemption_granted"
    PROCEDURAL_NOTICE = "procedural_notice"


class ChecklistScenarioOut(BaseModel):
    id: str
    procedure: str
    status_code: str
    scenario: str
    required_text: str
    conditional_text: str = ""
    application_text: str = ""
    note_text: str = ""
    source_line: int = 0
    source_section: str = ""
    review_state: str = ChecklistReviewState.COMPILED_NEEDS_REVIEW.value
    editor_note: str = ""
    version_no: int = 1
    updated_at: str
    updated_by: str = "system"
    has_active_draft: bool = False
    active_draft_id: Optional[str] = None


class DraftCreateIn(BaseModel):
    item_id: str
    required_text: str = Field(min_length=1, max_length=12000)
    conditional_text: str = Field(default="", max_length=12000)
    application_text: str = Field(default="", max_length=12000)
    note_text: str = Field(default="", max_length=12000)
    editor_note: str = Field(min_length=3, max_length=2000)
    evidence_url: str = Field(default="", max_length=1000)
    evidence_title: str = Field(default="", max_length=500)
    evidence_issuer: str = Field(default="", max_length=200)
    evidence_date: str = Field(default="", max_length=50)
    source_edition: Optional[str] = Field(default=None, max_length=100)
    source_section: Optional[str] = Field(default=None, max_length=200)
    source_locator: Optional[str] = Field(default=None, max_length=100)
    effective_start: Optional[str] = Field(default=None, max_length=50)
    effective_end: Optional[str] = Field(default=None, max_length=50)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "item_id" not in data and "id" in data:
                data["item_id"] = data["id"]
            if not data.get("required_text") and data.get("required_documents"):
                req = data["required_documents"]
                data["required_text"] = "\n".join(req) if isinstance(req, list) else str(req)
            if not data.get("conditional_text") and data.get("conditional_documents"):
                cond = data["conditional_documents"]
                data["conditional_text"] = "\n".join(cond) if isinstance(cond, list) else str(cond)
            if not data.get("note_text") and data.get("notes"):
                data["note_text"] = str(data["notes"])
            if not data.get("editor_note"):
                data["editor_note"] = data.get("change_rationale") or data.get("note") or "운영자 수정 제안"
        return data

    @field_validator("evidence_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        clean = v.strip()
        if clean and not clean.startswith("https://"):
            raise ValueError("Evidence URL must be a valid HTTPS address (https://...)")
        return clean


class DraftActionIn(BaseModel):
    action: str = Field(pattern=r"^(submit|start_review|request_changes|approve|reject|publish)$")
    comment: str = Field(default="", max_length=2000)
    human_decision: Optional[str] = Field(default=None, max_length=100)
    allow_self_approval: bool = Field(default=False)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("comment") and data.get("note"):
                data["comment"] = data["note"]
        return data


class OfficeOverrideIn(BaseModel):
    office_id: str = Field(min_length=2, max_length=50)
    item_id: str
    procedure: str = Field(pattern=r"^(extension|change|registration)$")
    status_code: str
    diff_type: str = Field(pattern=r"^(additional_required|conditional_added|exemption_granted|procedural_notice)$")
    override_text: str = Field(min_length=2, max_length=12000)
    evidence_url: str = Field(min_length=8, max_length=1000)
    evidence_title: str = Field(default="", max_length=500)
    evidence_issuer: str = Field(default="", max_length=200)
    confirmed_date: str = Field(default="", max_length=50)
    effective_start: Optional[str] = None
    effective_end: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("office_id") and data.get("office_code"):
                data["office_id"] = data["office_code"]
            if not data.get("diff_type") and data.get("override_type"):
                mapped = {
                    "additional_document": "additional_required",
                    "conditional_exemption": "exemption_granted",
                    "submission_restriction": "procedural_notice",
                    "jurisdiction_rule": "procedural_notice",
                }.get(data["override_type"], "additional_required")
                data["diff_type"] = mapped
            if not data.get("override_text") and data.get("description"):
                data["override_text"] = data["description"]
            if not data.get("evidence_url") and data.get("official_notice_url"):
                data["evidence_url"] = data["official_notice_url"]
            if not data.get("evidence_title") and data.get("title"):
                data["evidence_title"] = data["title"]
            if not data.get("item_id"):
                code = (data.get("status_code") or "ALL").lower()
                proc = data.get("procedure") or "extension"
                data["item_id"] = f"{code}-{proc}-override"
        return data

    @field_validator("evidence_url")
    @classmethod
    def validate_https(cls, v: str) -> str:
        clean = v.strip()
        if not clean.startswith("https://"):
            raise ValueError("Office-specific differences require a valid official HTTPS notice URL.")
        return clean


class FieldDiffItem(BaseModel):
    field_name: str
    label: str
    baseline_value: str
    draft_value: str
    changed: bool


class ScenarioDiffOut(BaseModel):
    draft_id: str
    item_id: str
    procedure: str
    status_code: str
    scenario: str
    lifecycle_state: str
    created_by: str
    created_at: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    fields: List[FieldDiffItem]
    evidence_url: str
    evidence_title: str
    editor_note: str
    has_legal_impact: bool
    legal_impact_notes: List[str]


class PublishValidationReport(BaseModel):
    valid: bool
    passed: bool
    total_items: int
    total_scenarios: int
    procedure_counts: Dict[str, int] = Field(default_factory=dict)
    approved_drafts_count: int = 0
    pending_drafts_count: int = 0
    checks: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    checked_at: str
    durable_storage: bool = True
    dataset_checksum: str = ""


class ReleaseRequestIn(BaseModel):
    target_procedure: str = Field(default="all", pattern=r"^(all|extension|change|registration)$")
    release_tag: Optional[str] = Field(default=None, max_length=64)
    release_note: str = Field(default="운영 배포 릴리스", min_length=3, max_length=2000)

    @field_validator("release_tag")
    @classmethod
    def validate_tag(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            return None
        if not re.match(r"^[a-zA-Z0-9_\-\.]{3,64}$", clean):
            raise ValueError("Release tag must be 3-64 characters and contain only letters, numbers, hyphens, underscores, or periods.")
        return clean


class RollbackRequestIn(BaseModel):
    rollback_note: str = Field(default="직전 정상 버전으로 긴급 롤백", min_length=3, max_length=2000)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("rollback_note") and data.get("reason"):
                data["rollback_note"] = data["reason"]
        return data


class ReleaseManifestOut(BaseModel):
    release_id: str
    release_tag: str
    target_procedure: str
    approved_draft_count: int
    total_scenario_count: int
    validation_passed: bool
    payload_checksum: str
    published_by: str
    published_at: str
    status: str = "PUBLISHED"
    release_note: str = ""
    rollback_ref: Optional[str] = None


class DashboardMetricsOut(BaseModel):
    total_scenarios: int
    extension_count: int
    change_count: int
    registration_count: int
    reviewed_count: int
    pending_review_count: int
    lacking_evidence_count: int
    suspected_conflicts_count: int
    stale_count: int
    office_pending_count: int
    recent_drafts: List[Dict[str, Any]]
    recent_audit: List[Dict[str, Any]]
