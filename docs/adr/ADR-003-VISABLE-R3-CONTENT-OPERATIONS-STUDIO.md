# ADR-003: VISABLE Content Operations Studio Architecture & Governance

- **Status**: Accepted
- **Date**: 2026-10-19
- **Authors**: VISABLE Engineering Team
- **Milestone**: PR #662 (VISABLE R3 — Content Operations Studio)
- **Supersedes / Extends**: PR #659 (Data Migration), PR #660 (UX Redesign), PR #661 (Legal Hardening)

---

## 1. Context & Problem Statement

VISABLE provides 647 scenario-based immigration document checklists across 26 immigration offices in the Republic of Korea:
- Extension of Stay (`extension`): 224 scenarios
- Change of Status (`change`): 251 scenarios
- Alien Registration & Residence Reporting (`registration`): 172 scenarios

Prior to Milestone R3, content maintenance required engineers to manually edit JSON files (`data/immigration-checklists/*.json`) or python authoring scripts and submit GitHub pull requests. This workflow had serious operational bottlenecks and risks:
1. **High Barrier for Non-Developer Operators**: Legal analysts and immigration coordinators cannot directly update guidance without git/code proficiency.
2. **Lack of Enforced Pre-Review Evidence Gating**: Changes could be merged without verified HTTPS links to official Ministry of Justice (법무부) notices or HiKorea manuals.
3. **Risk of Silent Data Corruption**: Manual edits risked dropping scenarios, misnumbering identifiers, or violating schema constraints.
4. **Disjointed Office Rules**: Office-specific practices (e.g., Jeju Special Self-Governing Province financial balance criteria) risked contaminating national standard baselines.

---

## 2. Decision & Architecture

We built the **VISABLE Content Operations Studio**, an administrative interface and backend service integrated directly into the existing Waymaker Knowledge Platform (`backend/services/knowledge/`).

### A. Architectural Principles

1. **Single Source of Truth via SQLite Extension (`0002_checklist_operations.sql`)**:
   Instead of inventing an isolated CMS with duplicate storage, we expanded the Waymaker SQLite store. Migration 0002 adds:
   - `checklist_items`: Stores the authoritative baseline of all 647 items.
   - `checklist_drafts`: Full staging and revision history for proposed changes.
   - `checklist_office_overrides`: Dedicated storage for 26 office exceptions.
   - `checklist_releases`: Immutable audit trail of executed publications.
   - `operator_roles`: Role assignments per operator name.

2. **Role-Based Access Control (RBAC)**:
   Four distinct roles with clear segregation of duties:
   - `viewer`: Read-only access to all scenarios, metrics, and diffs.
   - `editor`: Can author, stage, and submit drafts for review.
   - `reviewer`: Can inspect diffs, audit HTTPS evidence, and approve/reject drafts.
   - `publisher`: Can run pre-publish validation gates and trigger production releases.

3. **Strict Evidence Gate Invariant**:
   - Every draft requires a documented change rationale.
   - Any draft submitted for review must supply an official citation.
   - Approval strictly enforces that `evidence_url` begins with `https://`. Any approval attempt without a valid HTTPS citation raises `KnowledgeError(PipelineError.REVIEW_REQUIRED)` and is rejected at the API level.

4. **Zero-Loss 647 Invariant & Pre-Publish Validation Gate**:
   - Before any publication release can be committed, the system executes an automated invariant check:
     - Total scenario count == exactly 647.
     - Extension count == 224, Change count == 251, Registration count == 172.
     - All scenario IDs strictly match schema prefixes (`CHK-EXT-*`, `CHK-CHG-*`, `CHK-REG-*`).
     - Zero unapproved or dangling drafts are applied.
   - If any invariant fails, publication is blocked.

5. **Client-Side Security (Safe DOM & Zero `innerHTML`)**:
   - `content-studio.js` constructs all elements using DOM creation APIs and `textContent`.
   - Never evaluates unsanitized user inputs or API strings as HTML, neutralizing XSS vulnerabilities.
   - Tokens live in memory and `sessionStorage` only, never stored in `localStorage`.

---

## 3. Consequences

### Positive
- Operational independence for non-developer immigration legal researchers.
- Guaranteed preservation of all 647 scenarios with verifiable baseline counts.
- Strict accountability via audit logs and operator identity recording.
- Clear separation between national baseline rules and office-specific practices (e.g. Jeju).

### Negative / Trade-offs
- Operators must possess valid operator bearer tokens configured on the backend server.
- Reviewers cannot approve changes based on oral or unverified hearsay; only official HTTPS sources are accepted.
