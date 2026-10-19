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
from pydantic import BaseModel, Field, field_validator


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
    total_scenarios: int
    approved_drafts_count: int
    errors: List[str]
    warnings: List[str]
    checked_at: str


class ReleaseRequestIn(BaseModel):
    target_procedure: str = Field(default="all", pattern=r"^(all|extension|change|registration)$")
    release_note: str = Field(min_length=3, max_length=2000)


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
