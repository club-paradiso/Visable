-- Waymaker Knowledge Platform — foundation schema (migration 0001).
--
-- Dialect: SQLite 3.35+ (stdlib sqlite3). Written in the portable subset of
-- SQL so a later PostgreSQL port is a mechanical translation: TEXT ids, ISO-8601
-- TEXT timestamps, CHECK constraints for enums, FKs, partial unique indexes.
-- Triggers use SQLite's RAISE(ABORT, ...); the PostgreSQL equivalent is a
-- plpgsql trigger function raising an exception with the same message code.
--
-- Invariants enforced HERE (not only in Python):
--   * lifecycle transitions are whitelisted (lifecycle_transitions table);
--   * a fact can only be INSERTED as a proposal (DRAFT / AI_EXTRACTED /
--     HUMAN_REVIEW_REQUIRED) — never directly as reviewed/verified/published;
--   * PUBLISHED requires >= 1 citation, a verifier and a verification time;
--   * HUMAN_REVIEWED / VERIFIED require a human or legacy-repository reviewer —
--     an AI or system actor can never be the reviewer of record;
--   * reviewed content is immutable — an edit is a new fact version;
--   * the audit log is append-only.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Sources: identity vs version
-- ---------------------------------------------------------------------------
CREATE TABLE sources (
    source_id        TEXT PRIMARY KEY,
    source_key       TEXT NOT NULL UNIQUE,          -- e.g. 'stay_guide_manual'
    title_ko         TEXT NOT NULL,
    title_en         TEXT NOT NULL DEFAULT '',
    issuing_body     TEXT NOT NULL DEFAULT '',
    -- Authority vocabulary = services.immigration_tools.AuthorityType.
    authority_type   TEXT NOT NULL CHECK (authority_type IN (
        'statute', 'approved_manual', 'official_guidance', 'consular_guidance',
        'administrative_source', 'precedent', 'structured_data', 'unapproved_extraction'
    )),
    -- Procedure scope family. 'stay' and 'visa' must never mix (CLAUDE.md).
    procedure_family TEXT NOT NULL CHECK (procedure_family IN ('stay', 'visa', 'law', 'general')),
    official_url     TEXT NOT NULL DEFAULT '',
    refresh_state    TEXT NOT NULL DEFAULT 'current' CHECK (refresh_state IN (
        'current', 'refresh_due', 'superseded', 'unavailable'
    )),
    refresh_interval_days INTEGER CHECK (refresh_interval_days IS NULL OR refresh_interval_days > 0),
    registry_ref     TEXT NOT NULL DEFAULT '',      -- family key in data/source_registry.json
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE source_versions (
    source_version_id    TEXT PRIMARY KEY,
    source_id            TEXT NOT NULL REFERENCES sources(source_id),
    version_label        TEXT NOT NULL,             -- '2026.6'
    edition_ref          TEXT NOT NULL DEFAULT '',  -- registry id, e.g. 'stay_manual_2026_06_23_pdf'
    revision_date        TEXT,                      -- source file / export date (NOT effective date)
    published_date       TEXT,                      -- official publication date when known
    effective_from       TEXT,                      -- NULL = unknown, never invented
    imported_at          TEXT NOT NULL,
    content_sha256       TEXT,
    artifact_ref         TEXT NOT NULL DEFAULT '',  -- INTERNAL path; never public
    page_count           INTEGER CHECK (page_count IS NULL OR page_count > 0),
    status               TEXT NOT NULL CHECK (status IN (
        'active', 'staged', 'superseded', 'future_effective', 'withdrawn'
    )),
    content_review_state TEXT NOT NULL DEFAULT 'needs_review' CHECK (content_review_state IN (
        'approved', 'needs_review', 'rejected', 'not_applicable'
    )),
    supersedes_version_id TEXT REFERENCES source_versions(source_version_id),
    official_url         TEXT NOT NULL DEFAULT '',
    notes                TEXT NOT NULL DEFAULT '',
    UNIQUE (source_id, edition_ref),
    UNIQUE (source_id, content_sha256)
);
CREATE INDEX idx_source_versions_source ON source_versions(source_id, status);

-- Section anchors: the locations a citation may point at. Validation rejects a
-- citation whose page range falls outside the version / section.
CREATE TABLE source_sections (
    section_id        TEXT PRIMARY KEY,
    source_version_id TEXT NOT NULL REFERENCES source_versions(source_version_id),
    section_key       TEXT NOT NULL,
    title             TEXT NOT NULL,
    page_start        INTEGER CHECK (page_start IS NULL OR page_start > 0),
    page_end          INTEGER CHECK (page_end IS NULL OR page_end > 0),
    CHECK (page_start IS NULL OR page_end IS NULL OR page_end >= page_start),
    UNIQUE (source_version_id, section_key)
);

-- ---------------------------------------------------------------------------
-- Procedure variants: one (status, sub-code scope, procedure, scenario) slot.
-- ---------------------------------------------------------------------------
CREATE TABLE procedure_variants (
    variant_id        TEXT PRIMARY KEY,
    variant_key       TEXT NOT NULL UNIQUE,         -- 'D-2|*|extension|general'
    status_code       TEXT NOT NULL,                -- parent code, 'D-2'
    subcode           TEXT,                         -- exact sub-code or NULL (parent-level)
    subcodes_covered  TEXT NOT NULL DEFAULT '[]',   -- JSON list; explicit coverage only
    procedure         TEXT NOT NULL,                -- canonical key, 'extension'
    procedure_label_ko TEXT NOT NULL DEFAULT '',    -- '체류기간 연장허가'
    procedure_family  TEXT NOT NULL CHECK (procedure_family IN ('stay', 'visa')),
    scenario          TEXT NOT NULL DEFAULT 'general',
    section_title     TEXT NOT NULL DEFAULT '',     -- '유학(D-2)'
    legacy_ref        TEXT NOT NULL DEFAULT '',     -- legacy grounding_id, if seeded
    attributes        TEXT NOT NULL DEFAULT '{}',   -- JSON; compatibility metadata only
    created_at        TEXT NOT NULL,
    CHECK (subcode IS NULL OR subcode LIKE status_code || '-%')
);
CREATE INDEX idx_variants_lookup ON procedure_variants(status_code, procedure);

-- ---------------------------------------------------------------------------
-- Knowledge facts. Each row is one immutable fact VERSION; lineage_id groups
-- the versions of one logical fact. slot_key identifies what the fact is about
-- (variant + property + item) independent of its value, so two rows with the
-- same slot and different values are a change (versions) or a conflict.
-- ---------------------------------------------------------------------------
CREATE TABLE lifecycle_transitions (
    from_state TEXT NOT NULL,
    to_state   TEXT NOT NULL,
    PRIMARY KEY (from_state, to_state)
);
INSERT INTO lifecycle_transitions (from_state, to_state) VALUES
    ('DRAFT', 'HUMAN_REVIEW_REQUIRED'),
    ('DRAFT', 'REJECTED'),
    ('AI_EXTRACTED', 'HUMAN_REVIEW_REQUIRED'),
    ('AI_EXTRACTED', 'REJECTED'),
    ('HUMAN_REVIEW_REQUIRED', 'HUMAN_REVIEWED'),
    ('HUMAN_REVIEW_REQUIRED', 'REJECTED'),
    ('HUMAN_REVIEWED', 'VERIFIED'),
    ('HUMAN_REVIEWED', 'HUMAN_REVIEW_REQUIRED'),
    ('HUMAN_REVIEWED', 'REJECTED'),
    ('VERIFIED', 'PUBLISHED'),
    ('VERIFIED', 'HUMAN_REVIEW_REQUIRED'),
    ('VERIFIED', 'REJECTED'),
    ('PUBLISHED', 'SUPERSEDED'),
    ('PUBLISHED', 'WITHDRAWN');

CREATE TABLE knowledge_facts (
    fact_id            TEXT PRIMARY KEY,
    lineage_id         TEXT NOT NULL,
    version_no         INTEGER NOT NULL DEFAULT 1 CHECK (version_no >= 1),
    variant_id         TEXT NOT NULL REFERENCES procedure_variants(variant_id),
    property           TEXT NOT NULL CHECK (property IN (
        'required_document', 'eligibility_rule', 'fee', 'deadline', 'appointment',
        'online_service', 'reporting_duty', 'exception', 'condition', 'procedural_note'
    )),
    item_key           TEXT NOT NULL,               -- normalized identity of the item
    slot_key           TEXT NOT NULL,               -- variant_key|property|item_key
    value_text         TEXT NOT NULL CHECK (length(trim(value_text)) > 0),  -- canonical (Korean) source wording
    value_json         TEXT NOT NULL DEFAULT '{}',  -- structured value (label/examples/requirement_level/amount)
    condition_kind     TEXT NOT NULL DEFAULT 'always' CHECK (condition_kind IN (
        'always', 'conditional', 'applicant_specific', 'office_discretion'
    )),
    condition_text     TEXT NOT NULL DEFAULT '',
    display_translations TEXT NOT NULL DEFAULT '{}', -- JSON {lang: text}; NEVER authoritative
    sort_order         INTEGER NOT NULL DEFAULT 0,
    authority_type     TEXT NOT NULL CHECK (authority_type IN (
        'statute', 'approved_manual', 'official_guidance', 'consular_guidance',
        'administrative_source', 'precedent', 'structured_data', 'unapproved_extraction'
    )),
    origin             TEXT NOT NULL CHECK (origin IN (
        'legacy_repository_verified', 'operator_manual', 'ai_extraction', 'parser_extraction'
    )),
    -- Extraction signal only (e.g. parser/model self-report). NEVER an approval input.
    extraction_confidence REAL CHECK (extraction_confidence IS NULL OR (extraction_confidence >= 0 AND extraction_confidence <= 1)),
    extraction_warnings TEXT NOT NULL DEFAULT '[]',
    lifecycle_state    TEXT NOT NULL CHECK (lifecycle_state IN (
        'DRAFT', 'AI_EXTRACTED', 'HUMAN_REVIEW_REQUIRED', 'HUMAN_REVIEWED', 'VERIFIED',
        'PUBLISHED', 'SUPERSEDED', 'WITHDRAWN', 'REJECTED'
    )),
    -- Temporal. NULL effective_from = unknown (explicit, never invented).
    effective_from     TEXT,
    effective_to       TEXT,
    published_at       TEXT,
    superseded_at      TEXT,
    supersedes_fact_id TEXT REFERENCES knowledge_facts(fact_id),
    superseded_by_fact_id TEXT REFERENCES knowledge_facts(fact_id),
    -- Review provenance. reviewer_kind distinguishes a person from the
    -- pre-platform repository verification record; AI is never a reviewer.
    reviewed_by        TEXT,
    reviewed_at        TEXT,
    verified_by        TEXT,
    verified_at        TEXT,
    reviewer_kind      TEXT CHECK (reviewer_kind IS NULL OR reviewer_kind IN (
        'human_operator', 'legacy_repository_verification'
    )),
    created_by         TEXT NOT NULL,
    created_by_kind    TEXT NOT NULL CHECK (created_by_kind IN (
        'human_operator', 'ai_extractor', 'parser', 'legacy_import', 'system'
    )),
    created_at         TEXT NOT NULL,
    proposal_hash      TEXT NOT NULL UNIQUE,        -- idempotency identity
    CHECK (effective_from IS NULL OR effective_to IS NULL OR effective_to >= effective_from),
    CHECK (lifecycle_state NOT IN ('HUMAN_REVIEWED', 'VERIFIED', 'PUBLISHED', 'SUPERSEDED', 'WITHDRAWN')
           OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND reviewer_kind IS NOT NULL)),
    CHECK (lifecycle_state NOT IN ('VERIFIED', 'PUBLISHED', 'SUPERSEDED', 'WITHDRAWN')
           OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)),
    CHECK (lifecycle_state NOT IN ('PUBLISHED', 'SUPERSEDED', 'WITHDRAWN') OR published_at IS NOT NULL),
    CHECK (lifecycle_state <> 'SUPERSEDED' OR superseded_at IS NOT NULL)
);
CREATE INDEX idx_facts_variant_state ON knowledge_facts(variant_id, lifecycle_state, property, sort_order);
CREATE INDEX idx_facts_slot ON knowledge_facts(slot_key, lifecycle_state);
CREATE INDEX idx_facts_lineage ON knowledge_facts(lineage_id, version_no);
CREATE INDEX idx_facts_state ON knowledge_facts(lifecycle_state);
-- One published fact per slot and effective start. Future-effective versions
-- coexist with the current one; overlapping windows are a detected conflict.
CREATE UNIQUE INDEX uq_facts_published_slot
    ON knowledge_facts(slot_key, COALESCE(effective_from, ''))
    WHERE lifecycle_state = 'PUBLISHED';

-- Provenance: where a fact comes from. A reference, not a copy of the source.
CREATE TABLE fact_citations (
    citation_id       TEXT PRIMARY KEY,
    fact_id           TEXT NOT NULL REFERENCES knowledge_facts(fact_id),
    source_version_id TEXT NOT NULL REFERENCES source_versions(source_version_id),
    section_title     TEXT NOT NULL DEFAULT '',
    page_start        INTEGER CHECK (page_start IS NULL OR page_start > 0),
    page_end          INTEGER CHECK (page_end IS NULL OR page_end > 0),
    locator           TEXT NOT NULL DEFAULT '',     -- '다. 제출서류', article no., etc.
    evidence_excerpt  TEXT NOT NULL DEFAULT '' CHECK (length(evidence_excerpt) <= 4000),
    locator_verified  INTEGER NOT NULL DEFAULT 0 CHECK (locator_verified IN (0, 1)),
    verification_note TEXT NOT NULL DEFAULT '',     -- INTERNAL; never public
    created_at        TEXT NOT NULL,
    CHECK (page_start IS NULL OR page_end IS NULL OR page_end >= page_start),
    UNIQUE (fact_id, source_version_id, page_start, page_end, locator)
);
CREATE INDEX idx_citations_fact ON fact_citations(fact_id);
CREATE INDEX idx_citations_version ON fact_citations(source_version_id);

-- ---------------------------------------------------------------------------
-- Lifecycle triggers
-- ---------------------------------------------------------------------------
CREATE TRIGGER trg_facts_insert_only_proposals
BEFORE INSERT ON knowledge_facts
WHEN NEW.lifecycle_state NOT IN ('DRAFT', 'AI_EXTRACTED', 'HUMAN_REVIEW_REQUIRED')
BEGIN
    SELECT RAISE(ABORT, 'LIFECYCLE_INSERT_MUST_BE_PROPOSAL');
END;

CREATE TRIGGER trg_facts_ai_created_state
BEFORE INSERT ON knowledge_facts
WHEN NEW.created_by_kind = 'ai_extractor' AND NEW.lifecycle_state <> 'AI_EXTRACTED'
BEGIN
    SELECT RAISE(ABORT, 'AI_OUTPUT_MUST_ENTER_AS_AI_EXTRACTED');
END;

CREATE TRIGGER trg_facts_transition_whitelist
BEFORE UPDATE OF lifecycle_state ON knowledge_facts
WHEN OLD.lifecycle_state <> NEW.lifecycle_state
 AND NOT EXISTS (SELECT 1 FROM lifecycle_transitions
                 WHERE from_state = OLD.lifecycle_state AND to_state = NEW.lifecycle_state)
BEGIN
    SELECT RAISE(ABORT, 'LIFECYCLE_TRANSITION_FORBIDDEN');
END;

CREATE TRIGGER trg_facts_publish_requires_citation
BEFORE UPDATE OF lifecycle_state ON knowledge_facts
WHEN NEW.lifecycle_state = 'PUBLISHED'
 AND NOT EXISTS (SELECT 1 FROM fact_citations WHERE fact_id = NEW.fact_id)
BEGIN
    SELECT RAISE(ABORT, 'PUBLISH_WITHOUT_PROVENANCE');
END;

CREATE TRIGGER trg_facts_reviewed_content_immutable
BEFORE UPDATE OF variant_id, property, item_key, slot_key, value_text, value_json,
                 condition_kind, condition_text, authority_type, origin, lineage_id,
                 version_no, proposal_hash
ON knowledge_facts
WHEN OLD.lifecycle_state IN ('HUMAN_REVIEWED', 'VERIFIED', 'PUBLISHED', 'SUPERSEDED', 'WITHDRAWN', 'REJECTED')
BEGIN
    SELECT RAISE(ABORT, 'REVIEWED_FACT_IMMUTABLE');
END;

CREATE TRIGGER trg_citations_frozen_after_review
BEFORE DELETE ON fact_citations
WHEN (SELECT lifecycle_state FROM knowledge_facts WHERE fact_id = OLD.fact_id)
     IN ('HUMAN_REVIEWED', 'VERIFIED', 'PUBLISHED', 'SUPERSEDED', 'WITHDRAWN', 'REJECTED')
BEGIN
    SELECT RAISE(ABORT, 'REVIEWED_PROVENANCE_IMMUTABLE');
END;

CREATE TRIGGER trg_facts_no_delete_after_review
BEFORE DELETE ON knowledge_facts
WHEN OLD.lifecycle_state NOT IN ('DRAFT', 'AI_EXTRACTED', 'HUMAN_REVIEW_REQUIRED')
BEGIN
    SELECT RAISE(ABORT, 'REVIEWED_FACT_NOT_DELETABLE');
END;

-- ---------------------------------------------------------------------------
-- Review workflow + audit
-- ---------------------------------------------------------------------------
CREATE TABLE review_tasks (
    task_id          TEXT PRIMARY KEY,
    fact_id          TEXT NOT NULL REFERENCES knowledge_facts(fact_id),
    task_kind        TEXT NOT NULL CHECK (task_kind IN (
        'new_fact', 'update_fact', 'conflict', 'source_refresh', 'gap_resolution'
    )),
    status           TEXT NOT NULL CHECK (status IN (
        'open', 'needs_evidence', 'resolved', 'rejected'
    )),
    compare_fact_id  TEXT REFERENCES knowledge_facts(fact_id),  -- current published value, if any
    priority_score   INTEGER NOT NULL DEFAULT 0,
    priority_factors TEXT NOT NULL DEFAULT '{}',    -- JSON; transparent inputs only
    note             TEXT NOT NULL DEFAULT '',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    resolved_at      TEXT
);
-- At most one open task per fact (re-import cannot spawn duplicates).
CREATE UNIQUE INDEX uq_review_open_task ON review_tasks(fact_id) WHERE status IN ('open', 'needs_evidence');
CREATE INDEX idx_review_status ON review_tasks(status, priority_score DESC);

CREATE TABLE audit_log (
    audit_id     TEXT PRIMARY KEY,
    at           TEXT NOT NULL,
    actor        TEXT NOT NULL,
    actor_kind   TEXT NOT NULL CHECK (actor_kind IN (
        'human_operator', 'legacy_import', 'parser', 'ai_extractor', 'system'
    )),
    entity_type  TEXT NOT NULL,
    entity_id    TEXT NOT NULL,
    action       TEXT NOT NULL,
    reason       TEXT NOT NULL DEFAULT '',
    before_json  TEXT NOT NULL DEFAULT '{}',
    after_json   TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id, at);

CREATE TRIGGER trg_audit_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'AUDIT_LOG_APPEND_ONLY'); END;
CREATE TRIGGER trg_audit_no_delete BEFORE DELETE ON audit_log
BEGIN SELECT RAISE(ABORT, 'AUDIT_LOG_APPEND_ONLY'); END;

CREATE TABLE knowledge_conflicts (
    conflict_id   TEXT PRIMARY KEY,
    fact_a_id     TEXT NOT NULL REFERENCES knowledge_facts(fact_id),
    fact_b_id     TEXT NOT NULL REFERENCES knowledge_facts(fact_id),
    slot_key      TEXT NOT NULL,
    conflict_kind TEXT NOT NULL CHECK (conflict_kind IN (
        'value_mismatch', 'authority_contradiction', 'version_contradiction', 'temporal_overlap'
    )),
    status        TEXT NOT NULL CHECK (status IN ('open', 'resolved', 'dismissed')),
    detected_at   TEXT NOT NULL,
    resolved_at   TEXT,
    resolution    TEXT NOT NULL DEFAULT '',
    CHECK (fact_a_id <> fact_b_id),
    UNIQUE (fact_a_id, fact_b_id)
);
CREATE INDEX idx_conflicts_status ON knowledge_conflicts(status, slot_key);

-- ---------------------------------------------------------------------------
-- Learning loop (privacy-minimized)
-- ---------------------------------------------------------------------------
CREATE TABLE query_observations (
    observation_id  TEXT PRIMARY KEY,
    observed_at     TEXT NOT NULL,
    expires_at      TEXT NOT NULL,                  -- retention bound
    language        TEXT NOT NULL DEFAULT '',
    status_code     TEXT,
    subcode         TEXT,
    procedure       TEXT,
    intent          TEXT,
    coverage_state  TEXT NOT NULL,
    answer_path     TEXT NOT NULL,
    gap_reason      TEXT,
    guard_outcome   TEXT NOT NULL DEFAULT 'not_run',
    sanitized_query TEXT NOT NULL DEFAULT '' CHECK (length(sanitized_query) <= 240),
    query_fingerprint TEXT NOT NULL DEFAULT '',
    fact_ids        TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX idx_observations_time ON query_observations(observed_at);
CREATE INDEX idx_observations_expiry ON query_observations(expires_at);

CREATE TABLE coverage_gaps (
    gap_id            TEXT PRIMARY KEY,
    dedupe_key        TEXT NOT NULL UNIQUE,         -- status|subcode|procedure|intent|reason
    reason_code       TEXT NOT NULL,
    status_code       TEXT,
    subcode           TEXT,
    procedure         TEXT,
    intent            TEXT,
    occurrence_count  INTEGER NOT NULL DEFAULT 1 CHECK (occurrence_count >= 1),
    feedback_count    INTEGER NOT NULL DEFAULT 0 CHECK (feedback_count >= 0),
    first_seen        TEXT NOT NULL,
    last_seen         TEXT NOT NULL,
    example_query     TEXT NOT NULL DEFAULT '' CHECK (length(example_query) <= 240),
    resolution_status TEXT NOT NULL DEFAULT 'open' CHECK (resolution_status IN (
        'open', 'investigating', 'resolved', 'wont_fix'
    )),
    resolution_note   TEXT NOT NULL DEFAULT '',
    linked_task_id    TEXT REFERENCES review_tasks(task_id),
    linked_eval_case_id TEXT,
    resolved_at       TEXT
);
CREATE INDEX idx_gaps_status ON coverage_gaps(resolution_status, occurrence_count DESC);

CREATE TABLE user_feedback (
    feedback_id     TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    reason          TEXT NOT NULL CHECK (reason IN (
        'INCORRECT', 'MISSING_INFORMATION', 'TOO_LONG', 'HARD_TO_UNDERSTAND',
        'SOURCE_PROBLEM', 'MISUNDERSTOOD_QUESTION', 'OUTDATED', 'OTHER', 'HELPFUL'
    )),
    language        TEXT NOT NULL DEFAULT '',
    status_code     TEXT,
    procedure       TEXT,
    intent          TEXT,
    coverage_state  TEXT NOT NULL DEFAULT '',
    fact_ids        TEXT NOT NULL DEFAULT '[]',
    comment_sanitized TEXT NOT NULL DEFAULT '' CHECK (length(comment_sanitized) <= 300),
    gap_id          TEXT REFERENCES coverage_gaps(gap_id)
);

-- ---------------------------------------------------------------------------
-- Evaluation corpus
-- ---------------------------------------------------------------------------
CREATE TABLE eval_cases (
    case_id        TEXT PRIMARY KEY,
    case_key       TEXT NOT NULL UNIQUE,
    query          TEXT NOT NULL,
    language       TEXT NOT NULL,
    expected       TEXT NOT NULL DEFAULT '{}',      -- JSON: status/subcode/procedure/intent/coverage_state
    assertions     TEXT NOT NULL DEFAULT '[]',      -- JSON list of {type, value}
    risk_category  TEXT NOT NULL DEFAULT 'standard',
    tags           TEXT NOT NULL DEFAULT '[]',
    origin         TEXT NOT NULL CHECK (origin IN (
        'seed_foundation', 'golden_questions_v1', 'promoted_gap', 'operator'
    )),
    state          TEXT NOT NULL CHECK (state IN ('draft', 'approved', 'retired')),
    source_gap_id  TEXT REFERENCES coverage_gaps(gap_id),
    created_by     TEXT NOT NULL,
    approved_by    TEXT,
    approved_at    TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    CHECK (state <> 'approved' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL))
);

-- Which knowledge a case depends on (impact analysis).
CREATE TABLE eval_case_dependencies (
    case_id    TEXT NOT NULL REFERENCES eval_cases(case_id),
    slot_key   TEXT NOT NULL,
    PRIMARY KEY (case_id, slot_key)
);
CREATE INDEX idx_eval_dependency_slot ON eval_case_dependencies(slot_key);

CREATE TABLE eval_runs (
    run_id        TEXT PRIMARY KEY,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    selector      TEXT NOT NULL DEFAULT 'all',
    mode          TEXT NOT NULL CHECK (mode IN ('offline', 'live')),
    total         INTEGER NOT NULL DEFAULT 0,
    passed        INTEGER NOT NULL DEFAULT 0,
    failed        INTEGER NOT NULL DEFAULT 0,
    knowledge_revision TEXT NOT NULL DEFAULT ''
);

CREATE TABLE eval_results (
    run_id   TEXT NOT NULL REFERENCES eval_runs(run_id),
    case_id  TEXT NOT NULL REFERENCES eval_cases(case_id),
    passed   INTEGER NOT NULL CHECK (passed IN (0, 1)),
    failures TEXT NOT NULL DEFAULT '[]',
    observed TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (run_id, case_id)
);
