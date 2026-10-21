# Waymaker Knowledge Platform & VISABLE Content Operations Studio Integration Analysis

- **Author**: VISABLE Senior Engineering & Architecture Team
- **Date**: 2026-10-19
- **Scope**: Cohesive Architecture of Knowledge Platform (`services/knowledge/`) and Content Operations Studio (`services/knowledge/checklist_*`)
- **Status**: Production Reference

---

## 1. Executive Summary

VISABLE requires two complementary knowledge management dimensions:
1. **Semantic Fact Knowledge (Waymaker Knowledge Platform)**: Atomic knowledge facts, slot queries, cross-source conflict resolution, coverage gaps, and LLM answer grounding evaluation.
2. **Procedural Document Checklists (VISABLE Content Operations Studio)**: 647 concrete scenario-based checklists covering Extension (224), Change of Status (251), and Registration (172) across 26 immigration offices.

A naive approach would create two separate backends, distinct databases, and divergent operator surfaces. That approach was rejected. Instead, Milestone R3 integrates the Content Operations Studio directly onto the battle-tested Waymaker Knowledge Platform engine, sharing the durable SQLite store, operator authentication, audit logging, and migration framework.

---

## 2. Shared Subsystems vs Specialized Responsibilities

| Dimension | Waymaker Knowledge Platform (Migration 0001) | Content Operations Studio (Migration 0002) | Shared Mechanism |
|---|---|---|---|
| **Primary Unit of Data** | Atomic Fact / Slot (`FactProposal`, `KnowledgeFact`) | Procedural Checklist Scenario (`ChecklistScenario`) | Same SQLite DB (`WAYMAKER_KNOWLEDGE_DB`) |
| **Data Scope** | Generalized status requirements, semantic grounding | Exactly 647 official procedural checklist items | Unified migration sequence (`0001` → `0002`) |
| **Office Differentiation** | Global/General | 26 Distinct Offices (`checklist_office_overrides`) | SQLite relational foreign keys |
| **Authentication & RBAC** | `WAYMAKER_OPERATOR_TOKENS` (`name:token`) | 4-tier RBAC: `viewer`, `editor`, `reviewer`, `publisher` | Constant-time HMAC auth in `require_operator` |
| **Evidence Requirement** | Source edition & page anchors | Mandatory HTTPS official notice / manual citation | Strict pre-approval validation gate |
| **Release Management** | `PUBLISHED` lifecycle transition | Release manifest, pre-publish invariant check | Immutable audit trail & history tables |

---

## 3. Database Architecture & Schema Unification

### Migration `0001_knowledge_foundation.sql`
- `sources`, `source_versions`: Authoritative government manuals (e.g. 2026.06, 2026.09).
- `facts`: Atomic statements of law or regulation.
- `proposals`: Machine or human extractions awaiting review.
- `conflicts`: Detected contradictions between sources or editions.
- `eval_cases`, `eval_runs`: Automated regression tests for question-answering.

### Migration `0002_checklist_operations.sql`
- `checklist_items`: Stores all 647 official procedural checklist items.
- `checklist_drafts`: Full change-staging area for operator proposals.
- `checklist_office_overrides`: Dedicated storage for 26 office practices (e.g. Jeju university student financial criteria).
- `checklist_releases`: Immutable snapshots of production releases.
- `operator_roles`: Explicit RBAC mapping (`editor`, `reviewer`, `publisher`, `viewer`).

Because Migration 0002 is registered in `backend/services/knowledge/migrations/`, the platform's standard `KnowledgeStore` automatically executes both migrations in lockstep on startup, ensuring full reproducibility in production, staging, and in-memory test environments.

---

## 4. Vertical Slice Pilot Grounding

To validate end-to-end integration, four representative targets were implemented and verified across the database, repository, API, and UI:

1. **D-2 (유학 - Study)**:
   - Part-time work permission conditions (시간제취업 허가).
   - Financial balance exemption thresholds (정규과정 평점 2.0 이상 면제).
   - University student advisor proxy submission (대학 유학생 담당자 위임 접수).
2. **E-7-1 (전문인력 - Professional Employment)**:
   - Mandatory employment contract & recommendation letter (고용계약서, 고용추천서).
   - Minimum income criteria (GNI 80% threshold).
   - Employer proxy submission requirements.
3. **F-4 (재외동포 - Overseas Korean)**:
   - Domestic residence reporting (국내거소신고).
   - Basic livelihood and criminal background certificate exemptions.
4. **Jeju Immigration Office (제주출입국·외국인청)**:
   - Office override for local university students: adjusted financial proof threshold without mutating national baseline records.

---

## 5. Security & Invariant Guarantees

1. **Zero Data Loss Invariant**:
   The Content Operations Studio pre-publish validation gate programmatically enforces that all 647 scenario items (224 extension, 251 change, 172 registration) remain intact before any release can be finalized.
2. **Evidence Gate**:
   No reviewer can approve an ungrounded proposal. The backend validates that `evidence_url` begins with `https://`, blocking hearsay or unverified claims.
3. **Segregation of Duties**:
   Editors cannot approve their own changes; Reviewers cannot deploy releases; Publishers must verify passing invariant checks before releasing.
