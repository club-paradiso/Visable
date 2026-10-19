-- VISABLE Content Operations Studio — Schema Extension (migration 0002).
--
-- Extends the Waymaker Knowledge Platform store to manage:
--   1. Checklist scenarios (the authoritative 647 items)
--   2. Working drafts with review lifecycle (DRAFT -> SUBMITTED -> UNDER_REVIEW -> APPROVED -> PUBLISHED / REJECTED)
--   3. Office-specific requirements and verified overrides for all 26 immigration offices
--   4. Publishing releases with checksums, validation gates, and rollback references
--   5. Operator roles and RBAC mappings (viewer, editor, reviewer, publisher)
--
-- Preserves existing audit_log and SQLite relational invariants.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- 1. Canonical Checklist Scenarios (Mirroring 647 Situational Records)
-- ---------------------------------------------------------------------------
CREATE TABLE checklist_items (
    id               TEXT PRIMARY KEY,              -- e.g. 'e-0001', 'c-0118', 'r-0050'
    procedure        TEXT NOT NULL CHECK (procedure IN ('extension', 'change', 'registration')),
    status_code      TEXT NOT NULL,                 -- e.g. 'D-2', 'E-7-1', 'F-4', 'F-5 전체'
    scenario         TEXT NOT NULL,
    required_text    TEXT NOT NULL,
    conditional_text TEXT NOT NULL DEFAULT '',
    application_text TEXT NOT NULL DEFAULT '',
    note_text        TEXT NOT NULL DEFAULT '',
    source_line      INTEGER NOT NULL DEFAULT 0,
    source_section   TEXT NOT NULL DEFAULT '',
    review_state     TEXT NOT NULL DEFAULT 'COMPILED_NEEDS_REVIEW' CHECK (review_state IN (
        'COMPILED_NEEDS_REVIEW', 'DRAFT', 'UNDER_REVIEW', 'APPROVED', 'PUBLISHED', 'REJECTED'
    )),
    editor_note      TEXT NOT NULL DEFAULT '',
    version_no       INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    updated_by       TEXT NOT NULL DEFAULT 'system'
);

CREATE INDEX idx_checklist_items_code ON checklist_items(status_code);
CREATE INDEX idx_checklist_items_proc ON checklist_items(procedure);
CREATE INDEX idx_checklist_items_state ON checklist_items(review_state);

-- ---------------------------------------------------------------------------
-- 2. Checklist Revisions & Review Proposals (Drafts)
-- ---------------------------------------------------------------------------
CREATE TABLE checklist_drafts (
    draft_id         TEXT PRIMARY KEY,              -- 'draft_chk_...'
    item_id          TEXT NOT NULL REFERENCES checklist_items(id) ON DELETE CASCADE,
    procedure        TEXT NOT NULL CHECK (procedure IN ('extension', 'change', 'registration')),
    status_code      TEXT NOT NULL,
    scenario         TEXT NOT NULL,
    required_text    TEXT NOT NULL,
    conditional_text TEXT NOT NULL DEFAULT '',
    application_text TEXT NOT NULL DEFAULT '',
    note_text        TEXT NOT NULL DEFAULT '',
    editor_note      TEXT NOT NULL,                 -- Mandatory rationale
    evidence_url     TEXT NOT NULL DEFAULT '',      -- Must match ^https:// for official promotion
    evidence_title   TEXT NOT NULL DEFAULT '',
    evidence_issuer  TEXT NOT NULL DEFAULT '',
    evidence_date    TEXT NOT NULL DEFAULT '',
    diff_summary     TEXT NOT NULL DEFAULT '',
    has_legal_impact INTEGER NOT NULL DEFAULT 0 CHECK (has_legal_impact IN (0, 1)),
    lifecycle_state  TEXT NOT NULL DEFAULT 'DRAFT' CHECK (lifecycle_state IN (
        'DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'PUBLISHED', 'REJECTED'
    )),
    created_by       TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    reviewed_by      TEXT,
    reviewed_at      TEXT,
    review_comment   TEXT NOT NULL DEFAULT '',
    published_by     TEXT,
    published_at     TEXT,
    rejection_reason TEXT NOT NULL DEFAULT ''
);

CREATE INDEX idx_checklist_drafts_item ON checklist_drafts(item_id);
CREATE INDEX idx_checklist_drafts_state ON checklist_drafts(lifecycle_state);
CREATE INDEX idx_checklist_drafts_code ON checklist_drafts(status_code);

-- ---------------------------------------------------------------------------
-- 3. Office-Specific Requirements & Overrides
-- ---------------------------------------------------------------------------
CREATE TABLE checklist_office_overrides (
    override_id      TEXT PRIMARY KEY,              -- 'ovr_...'
    office_id        TEXT NOT NULL,                 -- 'jeju', 'seoul', 'incheon', etc.
    item_id          TEXT NOT NULL REFERENCES checklist_items(id) ON DELETE CASCADE,
    procedure        TEXT NOT NULL CHECK (procedure IN ('extension', 'change', 'registration')),
    status_code      TEXT NOT NULL,
    diff_type        TEXT NOT NULL CHECK (diff_type IN (
        'additional_required', 'conditional_added', 'exemption_granted', 'procedural_notice'
    )),
    override_text    TEXT NOT NULL,
    evidence_url     TEXT NOT NULL,                 -- Mandatory official notice URL
    evidence_title   TEXT NOT NULL,
    evidence_issuer  TEXT NOT NULL,
    confirmed_date   TEXT NOT NULL,
    effective_start  TEXT,
    effective_end    TEXT,
    review_state     TEXT NOT NULL DEFAULT 'DRAFT' CHECK (review_state IN (
        'DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'PUBLISHED', 'REJECTED'
    )),
    verifier         TEXT,
    verified_at      TEXT,
    created_by       TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX idx_office_overrides_office ON checklist_office_overrides(office_id);
CREATE INDEX idx_office_overrides_item ON checklist_office_overrides(item_id);
CREATE INDEX idx_office_overrides_state ON checklist_office_overrides(review_state);

-- ---------------------------------------------------------------------------
-- 4. Publishing Releases & Gate Audit
-- ---------------------------------------------------------------------------
CREATE TABLE checklist_releases (
    release_id           TEXT PRIMARY KEY,          -- 'rel_...'
    release_tag          TEXT NOT NULL UNIQUE,      -- 'release-20261019-123456'
    target_procedure     TEXT NOT NULL DEFAULT 'all',
    approved_draft_count INTEGER NOT NULL DEFAULT 0,
    total_scenario_count INTEGER NOT NULL DEFAULT 647,
    validation_passed    INTEGER NOT NULL CHECK (validation_passed IN (0, 1)),
    validation_report    TEXT NOT NULL DEFAULT '{}',
    payload_checksum     TEXT NOT NULL,
    git_branch           TEXT NOT NULL DEFAULT '',
    git_pr_url           TEXT NOT NULL DEFAULT '',
    published_by         TEXT NOT NULL,
    published_at         TEXT NOT NULL,
    rollback_ref         TEXT
);

-- ---------------------------------------------------------------------------
-- 5. Operator Roles & RBAC
-- ---------------------------------------------------------------------------
CREATE TABLE operator_roles (
    operator_name    TEXT PRIMARY KEY,
    role             TEXT NOT NULL CHECK (role IN ('viewer', 'editor', 'reviewer', 'publisher')),
    assigned_by      TEXT NOT NULL DEFAULT 'system',
    assigned_at      TEXT NOT NULL
);

-- Seed default administrative roles for standard testing / initial bootstrap
INSERT OR IGNORE INTO operator_roles (operator_name, role, assigned_by, assigned_at) VALUES
    ('admin', 'publisher', 'system', '2026-10-19T00:00:00Z'),
    ('reviewer_lead', 'reviewer', 'system', '2026-10-19T00:00:00Z'),
    ('editor_staff', 'editor', 'system', '2026-10-19T00:00:00Z'),
    ('auditor', 'viewer', 'system', '2026-10-19T00:00:00Z');
