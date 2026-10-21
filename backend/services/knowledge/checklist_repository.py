"""VISABLE Content Operations Studio — Repository & Service Layer.

Provides data access, validation, diff calculation, review workflows,
and the safe publishing pipeline for checklist operations.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .checklist_models import (
    ChecklistReviewState,
    ChecklistScenarioOut,
    DashboardMetricsOut,
    DiffType,
    DraftActionIn,
    DraftCreateIn,
    FieldDiffItem,
    OfficeOverrideIn,
    OperatorRole,
    PublishValidationReport,
    ReleaseManifestOut,
    ReleaseRequestIn,
    RollbackRequestIn,
    ScenarioDiffOut,
    can_edit,
    can_publish,
    can_review,
)
from .models import KnowledgeError, PipelineError
from .store import KnowledgeStore, new_id, today, utc_now

logger = logging.getLogger("visable.checklists")

_ROOT_DIR = Path(__file__).resolve().parents[3]
CHECKLISTS_DATA_DIR = _ROOT_DIR / "data" / "immigration-checklists"
LOCAL_PRACTICE_FILE = _ROOT_DIR / "data" / "local-practice-202609.json"


# ---------------------------------------------------------------------------
# Data Bootstrapping (Idempotent Seed of 647 Cases)
# ---------------------------------------------------------------------------
def bootstrap_checklist_items(store: KnowledgeStore) -> Dict[str, int]:
    """Idempotently seeds checklist_items and checklist_office_overrides from committed JSON files."""
    with store._lock:
        count = store.one("SELECT COUNT(*) AS c FROM checklist_items")["c"]
        if count >= 647:
            return {"scenarios": count, "seeded": 0}

        seeded = 0
        now = utc_now()
        files = [
            ("extension", CHECKLISTS_DATA_DIR / "extension-202609.json"),
            ("change", CHECKLISTS_DATA_DIR / "change-202609.json"),
            ("registration", CHECKLISTS_DATA_DIR / "registration-202609.json"),
        ]

        store.conn.execute("BEGIN IMMEDIATE")
        try:
            for proc, path in files:
                if not path.is_file():
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                items = data.get("items", [])
                for it in items:
                    store.conn.execute(
                        """
                        INSERT OR IGNORE INTO checklist_items (
                            id, procedure, status_code, scenario,
                            required_text, conditional_text, application_text, note_text,
                            source_line, source_section, review_state, editor_note,
                            version_no, created_at, updated_at, updated_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 'bootstrap')
                        """,
                        (
                            it["id"],
                            proc,
                            it["status_code"],
                            it["scenario"],
                            it.get("required_text", ""),
                            it.get("conditional_text", ""),
                            it.get("application_text", ""),
                            it.get("note_text", ""),
                            int(it.get("source_line", 0)),
                            it.get("source_section", ""),
                            it.get("review_state", "COMPILED_NEEDS_REVIEW"),
                            it.get("editor_note", ""),
                            now,
                            now,
                        ),
                    )
                    seeded += 1

            # Seed existing verified local overrides if present
            overrides_path = CHECKLISTS_DATA_DIR / "local-overrides.json"
            if overrides_path.is_file():
                ovr_data = json.loads(overrides_path.read_text(encoding="utf-8"))
                for ov in ovr_data.get("overrides", []):
                    evidence_list = ov.get("evidence", [])
                    ev_url = evidence_list[0].get("url", "") if evidence_list else "https://www.hikorea.go.kr/"
                    ev_title = evidence_list[0].get("title", "") if evidence_list else "관할청 공지"
                    changes = ov.get("changes", {})
                    text_parts = [v for v in changes.values() if isinstance(v, str)]
                    store.conn.execute(
                        """
                        INSERT OR IGNORE INTO checklist_office_overrides (
                            override_id, office_id, item_id, procedure, status_code,
                            diff_type, override_text, evidence_url, evidence_title,
                            evidence_issuer, confirmed_date, effective_start, effective_end,
                            review_state, verifier, verified_at, created_by, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'bootstrap', ?, ?)
                        """,
                        (
                            ov["id"],
                            ov["office_id"],
                            ov["item_id"],
                            ov.get("procedure", "extension"),
                            ov.get("status_code", "UNKNOWN"),
                            "additional_required",
                            "\n".join(text_parts) or "관서별 추가 서류",
                            ev_url,
                            ev_title,
                            ov["office_id"],
                            today(),
                            None,
                            None,
                            ov.get("review_state", "DRAFT"),
                            "bootstrap",
                            now,
                            now,
                            now,
                        ),
                    )

            # Record audit
            store.conn.execute(
                """
                INSERT INTO audit_log (audit_id, entity_type, entity_id, action, actor, actor_kind, before_json, after_json, reason, at)
                VALUES (?, 'checklist_dataset', 'all_647', 'bootstrap_seed', 'system', 'system', '{}', ?, 'Initial R3 content studio bootstrap', ?)
                """,
                (new_id("aud"), json.dumps({"count": seeded}), now),
            )
            store.conn.execute("COMMIT")
        except Exception:
            store.conn.execute("ROLLBACK")
            raise

        logger.info("checklist_bootstrap_completed seeded=%d", seeded)
        return {"scenarios": seeded, "seeded": seeded}


# ---------------------------------------------------------------------------
# RBAC Resolution
# ---------------------------------------------------------------------------
def get_operator_role(store: KnowledgeStore, operator_name: str) -> OperatorRole:
    """Resolves operator role from DB or environment role suffix."""
    row = store.one("SELECT role FROM operator_roles WHERE operator_name = ?", (operator_name,))
    if row and row["role"]:
        try:
            return OperatorRole(row["role"])
        except ValueError:
            pass
    # Fallback to viewer role if unspecified (least-privilege default)
    return OperatorRole.VIEWER


# ---------------------------------------------------------------------------
# Dashboard Metrics
# ---------------------------------------------------------------------------
def get_dashboard_metrics(store: KnowledgeStore) -> DashboardMetricsOut:
    """Computes real, live administrative metrics across the checklist dataset."""
    total = store.one("SELECT COUNT(*) AS c FROM checklist_items")["c"]
    ext_c = store.one("SELECT COUNT(*) AS c FROM checklist_items WHERE procedure = 'extension'")["c"]
    chg_c = store.one("SELECT COUNT(*) AS c FROM checklist_items WHERE procedure = 'change'")["c"]
    reg_c = store.one("SELECT COUNT(*) AS c FROM checklist_items WHERE procedure = 'registration'")["c"]
    rev_c = store.one(
        "SELECT COUNT(*) AS c FROM checklist_items WHERE review_state IN ('APPROVED', 'PUBLISHED')"
    )["c"]
    pend_c = store.one(
        "SELECT COUNT(*) AS c FROM checklist_items WHERE review_state IN ('COMPILED_NEEDS_REVIEW', 'UNDER_REVIEW')"
    )["c"] + store.one("SELECT COUNT(*) AS c FROM checklist_drafts WHERE lifecycle_state IN ('SUBMITTED', 'UNDER_REVIEW')")["c"]
    lack_ev = store.one(
        "SELECT COUNT(*) AS c FROM checklist_items WHERE required_text = '' OR editor_note = ''"
    )["c"]
    sus_conf = store.one(
        "SELECT COUNT(*) AS c FROM checklist_items WHERE required_text LIKE '%대상%아님%' OR required_text LIKE '%불가%'"
    )["c"]
    stale_c = store.one(
        "SELECT COUNT(*) AS c FROM checklist_items WHERE review_state = 'COMPILED_NEEDS_REVIEW'"
    )["c"]
    off_pend = store.one(
        "SELECT COUNT(*) AS c FROM checklist_office_overrides WHERE review_state IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW')"
    )["c"]

    recent_drafts = [
        dict(r)
        for r in store.all(
            "SELECT draft_id, item_id, procedure, status_code, scenario, lifecycle_state, created_by, created_at FROM checklist_drafts ORDER BY created_at DESC LIMIT 10"
        )
    ]
    recent_audit = [
        dict(r)
        for r in store.all(
            "SELECT audit_id, entity_type, entity_id, action, actor, reason, at FROM audit_log ORDER BY at DESC LIMIT 15"
        )
    ]

    return DashboardMetricsOut(
        total_scenarios=total,
        extension_count=ext_c,
        change_count=chg_c,
        registration_count=reg_c,
        reviewed_count=rev_c,
        pending_review_count=pend_c,
        lacking_evidence_count=lack_ev,
        suspected_conflicts_count=sus_conf,
        stale_count=stale_c,
        office_pending_count=off_pend,
        recent_drafts=recent_drafts,
        recent_audit=recent_audit,
    )


# ---------------------------------------------------------------------------
# Scenarios Listing & Details
# ---------------------------------------------------------------------------
def list_scenarios(
    store: KnowledgeStore,
    procedure: Optional[str] = None,
    status_code: Optional[str] = None,
    query: Optional[str] = None,
    review_state: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ChecklistScenarioOut], int]:
    """Lists and searches checklist scenarios with active draft tracking."""
    where: List[str] = []
    params: List[Any] = []

    if procedure and procedure != "all":
        where.append("i.procedure = ?")
        params.append(procedure)
    if status_code:
        where.append("i.status_code LIKE ?")
        params.append(f"{status_code}%")
    if review_state and review_state != "all":
        where.append("i.review_state = ?")
        params.append(review_state)
    if query:
        q = query.strip()
        where.append("(i.status_code LIKE ? OR i.scenario LIKE ? OR i.required_text LIKE ? OR i.id = ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%", q])

    where_sql = " AND ".join(where) if where else "1=1"
    total = store.one(f"SELECT COUNT(*) AS c FROM checklist_items i WHERE {where_sql}", params)["c"]

    sql = f"""
        SELECT i.*, d.draft_id AS active_draft_id
        FROM checklist_items i
        LEFT JOIN checklist_drafts d ON d.item_id = i.id AND d.lifecycle_state IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW')
        WHERE {where_sql}
        ORDER BY i.procedure, i.status_code, i.id
        LIMIT ? OFFSET ?
    """
    rows = store.all(sql, params + [limit, offset])

    results: List[ChecklistScenarioOut] = []
    for r in rows:
        d = dict(r)
        has_draft = bool(d.get("active_draft_id"))
        active_id = d.get("active_draft_id")
        results.append(
            ChecklistScenarioOut(
                id=d["id"],
                procedure=d["procedure"],
                status_code=d["status_code"],
                scenario=d["scenario"],
                required_text=d["required_text"],
                conditional_text=d.get("conditional_text") or "",
                application_text=d.get("application_text") or "",
                note_text=d.get("note_text") or "",
                source_line=d.get("source_line") or 0,
                source_section=d.get("source_section") or "",
                review_state=d.get("review_state") or "COMPILED_NEEDS_REVIEW",
                editor_note=d.get("editor_note") or "",
                version_no=d.get("version_no") or 1,
                updated_at=d.get("updated_at") or "",
                updated_by=d.get("updated_by") or "system",
                has_active_draft=has_draft,
                active_draft_id=active_id,
            )
        )

    return results, total


def get_scenario_detail(store: KnowledgeStore, item_id: str) -> Dict[str, Any]:
    """Retrieves full scenario details including baseline, active drafts, office overrides, and history."""
    item = store.one("SELECT * FROM checklist_items WHERE id = ?", (item_id,))
    if not item:
        raise KnowledgeError(PipelineError.NOT_FOUND, f"Checklist item '{item_id}' not found.")

    drafts = [dict(d) for d in store.all("SELECT * FROM checklist_drafts WHERE item_id = ? ORDER BY created_at DESC", (item_id,))]
    overrides = [dict(o) for o in store.all("SELECT * FROM checklist_office_overrides WHERE item_id = ?", (item_id,))]
    audit = [dict(a) for a in store.all("SELECT * FROM audit_log WHERE entity_id = ? ORDER BY at DESC", (item_id,))]

    return {
        "item": dict(item),
        "drafts": drafts,
        "overrides": overrides,
        "audit": audit,
    }


# ---------------------------------------------------------------------------
# Draft Management & Review Lifecycle
# ---------------------------------------------------------------------------
def create_or_update_draft(
    store: KnowledgeStore, draft_in: DraftCreateIn, actor: str, actor_role: OperatorRole
) -> Dict[str, Any]:
    """Creates or updates a working draft for a checklist scenario."""
    if not can_edit(actor_role):
        raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, f"Role '{actor_role}' does not have edit permissions.")

    item = store.one("SELECT * FROM checklist_items WHERE id = ?", (draft_in.item_id,))
    if not item:
        raise KnowledgeError(PipelineError.NOT_FOUND, f"Checklist item '{draft_in.item_id}' not found.")

    now = utc_now()
    has_legal = 0
    legal_keywords = ["대상 아님", "해당 없음", "불가", "제한", "과태료", "처벌", "출석 필수"]
    combined_text = f"{draft_in.required_text} {draft_in.conditional_text} {draft_in.note_text}"
    if any(k in combined_text for k in legal_keywords):
        has_legal = 1

    # Check for existing open draft
    existing = store.one(
        "SELECT draft_id FROM checklist_drafts WHERE item_id = ? AND lifecycle_state IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW')",
        (draft_in.item_id,),
    )

    with store._lock:
        store.conn.execute("BEGIN IMMEDIATE")
        try:
            if existing:
                draft_id = existing["draft_id"]
                store.conn.execute(
                    """
                    UPDATE checklist_drafts SET
                        required_text = ?, conditional_text = ?, application_text = ?, note_text = ?,
                        editor_note = ?, evidence_url = ?, evidence_title = ?, evidence_issuer = ?,
                        evidence_date = ?, has_legal_impact = ?, lifecycle_state = 'DRAFT'
                    WHERE draft_id = ?
                    """,
                    (
                        draft_in.required_text,
                        draft_in.conditional_text,
                        draft_in.application_text,
                        draft_in.note_text,
                        draft_in.editor_note,
                        draft_in.evidence_url,
                        draft_in.evidence_title,
                        draft_in.evidence_issuer,
                        draft_in.evidence_date,
                        has_legal,
                        draft_id,
                    ),
                )
                action_name = "update_draft"
            else:
                draft_id = new_id("draft_chk")
                store.conn.execute(
                    """
                    INSERT INTO checklist_drafts (
                        draft_id, item_id, procedure, status_code, scenario,
                        required_text, conditional_text, application_text, note_text,
                        editor_note, evidence_url, evidence_title, evidence_issuer, evidence_date,
                        has_legal_impact, lifecycle_state, created_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)
                    """,
                    (
                        draft_id,
                        draft_in.item_id,
                        item["procedure"],
                        item["status_code"],
                        item["scenario"],
                        draft_in.required_text,
                        draft_in.conditional_text,
                        draft_in.application_text,
                        draft_in.note_text,
                        draft_in.editor_note,
                        draft_in.evidence_url,
                        draft_in.evidence_title,
                        draft_in.evidence_issuer,
                        draft_in.evidence_date,
                        has_legal,
                        actor,
                        now,
                    ),
                )
                action_name = "create_draft"

            # Record audit
            store.conn.execute(
                """
                INSERT INTO audit_log (audit_id, entity_type, entity_id, action, actor, actor_kind, before_json, after_json, reason, at)
                VALUES (?, 'checklist_draft', ?, ?, ?, 'human_operator', '{}', ?, ?, ?)
                """,
                (
                    new_id("aud"),
                    draft_id,
                    action_name,
                    actor,
                    json.dumps(draft_in.model_dump()),
                    draft_in.editor_note,
                    now,
                ),
            )
            store.conn.execute("COMMIT")
        except Exception:
            store.conn.execute("ROLLBACK")
            raise

    return {"draft_id": draft_id, "action": action_name, "lifecycle_state": "DRAFT"}


def act_on_draft(
    store: KnowledgeStore, draft_id: str, action_in: DraftActionIn, actor: str, actor_role: OperatorRole
) -> Dict[str, Any]:
    """Transitions a draft through the review lifecycle with strict RBAC and evidence validation."""
    draft = store.one("SELECT * FROM checklist_drafts WHERE draft_id = ?", (draft_id,))
    if not draft:
        raise KnowledgeError(PipelineError.NOT_FOUND, f"Draft '{draft_id}' not found.")

    curr_state = draft["lifecycle_state"]
    action = action_in.action
    now = utc_now()

    with store._lock:
        store.conn.execute("BEGIN IMMEDIATE")
        try:
            if action == "submit":
                if not can_edit(actor_role):
                    raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "Editor permissions required to submit.")
                if curr_state not in ("DRAFT", "REJECTED"):
                    raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, f"Cannot submit from state '{curr_state}'.")
                store.conn.execute(
                    "UPDATE checklist_drafts SET lifecycle_state = 'SUBMITTED' WHERE draft_id = ?",
                    (draft_id,),
                )
                new_state = "SUBMITTED"

            elif action == "start_review":
                if not can_review(actor_role):
                    raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "Reviewer permissions required.")
                if curr_state not in ("SUBMITTED", "DRAFT"):
                    raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, f"Cannot review from state '{curr_state}'.")
                store.conn.execute(
                    "UPDATE checklist_drafts SET lifecycle_state = 'UNDER_REVIEW', reviewed_by = ?, reviewed_at = ? WHERE draft_id = ?",
                    (actor, now, draft_id),
                )
                new_state = "UNDER_REVIEW"

            elif action == "request_changes":
                if not can_review(actor_role):
                    raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "Reviewer permissions required.")
                store.conn.execute(
                    "UPDATE checklist_drafts SET lifecycle_state = 'DRAFT', review_comment = ? WHERE draft_id = ?",
                    (action_in.comment, draft_id),
                )
                new_state = "DRAFT"

            elif action == "reject":
                if not can_review(actor_role):
                    raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "Reviewer permissions required.")
                if not action_in.comment.strip():
                    raise KnowledgeError(PipelineError.EXTRACTION_INVALID, "Rejection requires a documented reason.")
                store.conn.execute(
                    "UPDATE checklist_drafts SET lifecycle_state = 'REJECTED', rejection_reason = ?, reviewed_by = ?, reviewed_at = ? WHERE draft_id = ?",
                    (action_in.comment, actor, now, draft_id),
                )
                new_state = "REJECTED"

            elif action == "approve":
                if not can_review(actor_role):
                    raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "Reviewer permissions required to approve.")
                if curr_state not in ("SUBMITTED", "UNDER_REVIEW"):
                    raise KnowledgeError(
                        PipelineError.TRANSITION_FORBIDDEN,
                        f"Cannot approve draft in state '{curr_state}' (must be SUBMITTED or UNDER_REVIEW).",
                    )
                # Self-approval prevention (Phase 6)
                if draft["created_by"] == actor and not getattr(action_in, "allow_self_approval", False):
                    raise KnowledgeError(
                        PipelineError.TRANSITION_FORBIDDEN,
                        "Self-approval forbidden: An independent reviewer must approve changes. Use emergency override if authorized.",
                    )
                # STRICT EVIDENCE GATE: Cannot approve without valid HTTPS evidence!
                ev_url = (draft["evidence_url"] or "").strip()
                if not ev_url or not ev_url.startswith("https://"):
                    raise KnowledgeError(
                        PipelineError.REVIEW_REQUIRED,
                        "Evidence Gate Failed: Approval requires a verified official HTTPS URL (출처 근거 URL 필수).",
                    )
                ev_title = (draft["evidence_title"] or "").strip()
                ev_issuer = (draft["evidence_issuer"] or "").strip()
                if not ev_title and not ev_issuer:
                    raise KnowledgeError(
                        PipelineError.REVIEW_REQUIRED,
                        "Evidence Governance Failed: Official evidence title or issuing authority must be documented before approval.",
                    )
                store.conn.execute(
                    "UPDATE checklist_drafts SET lifecycle_state = 'APPROVED', reviewed_by = ?, reviewed_at = ?, review_comment = ? WHERE draft_id = ?",
                    (actor, now, action_in.comment, draft_id),
                )
                new_state = "APPROVED"

            elif action == "publish":
                if not can_publish(actor_role):
                    raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "Publisher permissions required to publish.")
                if curr_state != "APPROVED":
                    raise KnowledgeError(
                        PipelineError.TRANSITION_FORBIDDEN,
                        f"Only APPROVED drafts can be published (current: '{curr_state}').",
                    )

                # Apply draft content to canonical checklist_items row in same transaction
                item = store.one("SELECT * FROM checklist_items WHERE id = ?", (draft["item_id"],))
                new_version = item["version_no"] + 1

                store.conn.execute(
                    """
                    UPDATE checklist_items SET
                        required_text = ?, conditional_text = ?, application_text = ?, note_text = ?,
                        review_state = 'PUBLISHED', editor_note = ?, version_no = ?,
                        updated_at = ?, updated_by = ?
                    WHERE id = ?
                    """,
                    (
                        draft["required_text"],
                        draft["conditional_text"],
                        draft["application_text"],
                        draft["note_text"],
                        draft["editor_note"],
                        new_version,
                        now,
                        actor,
                        draft["item_id"],
                    ),
                )

                store.conn.execute(
                    "UPDATE checklist_drafts SET lifecycle_state = 'PUBLISHED', published_by = ?, published_at = ? WHERE draft_id = ?",
                    (actor, now, draft_id),
                )
                new_state = "PUBLISHED"

            else:
                raise KnowledgeError(PipelineError.EXTRACTION_INVALID, f"Unknown action '{action}'.")

            # Audit record
            store.conn.execute(
                """
                INSERT INTO audit_log (audit_id, entity_type, entity_id, action, actor, actor_kind, before_json, after_json, reason, at)
                VALUES (?, 'checklist_draft', ?, ?, ?, 'human_operator', ?, ?, ?, ?)
                """,
                (
                    new_id("aud"),
                    draft_id,
                    f"draft_{action}",
                    actor,
                    json.dumps({"state": curr_state}),
                    json.dumps({"state": new_state}),
                    action_in.comment or action,
                    now,
                ),
            )
            store.conn.execute("COMMIT")
        except Exception:
            store.conn.execute("ROLLBACK")
            raise

    logger.info("draft_action_success draft_id=%s action=%s new_state=%s", draft_id, action, new_state)
    return {"draft_id": draft_id, "action": action, "lifecycle_state": new_state}


# ---------------------------------------------------------------------------
# Diff Calculation & Legal Impact Analysis
# ---------------------------------------------------------------------------
def compute_draft_diff(store: KnowledgeStore, draft_id: str) -> ScenarioDiffOut:
    """Computes structured side-by-side diff comparing proposed draft with baseline scenario."""
    draft = store.one("SELECT * FROM checklist_drafts WHERE draft_id = ?", (draft_id,))
    if not draft:
        raise KnowledgeError(PipelineError.NOT_FOUND, f"Draft '{draft_id}' not found.")

    item = store.one("SELECT * FROM checklist_items WHERE id = ?", (draft["item_id"],))
    if not item:
        raise KnowledgeError(PipelineError.NOT_FOUND, f"Base item '{draft['item_id']}' not found.")

    fields = [
        ("required_text", "기본·명시 서류"),
        ("conditional_text", "조건부·대체·생략"),
        ("application_text", "본인·대리 신청 안내"),
        ("note_text", "비고·원문 근거"),
    ]

    diff_items: List[FieldDiffItem] = []
    legal_notes: List[str] = []

    for key, label in fields:
        base_v = (item[key] or "").strip()
        draft_v = (draft[key] or "").strip()
        changed = base_v != draft_v
        diff_items.append(
            FieldDiffItem(
                field_name=key,
                label=label,
                baseline_value=base_v,
                draft_value=draft_v,
                changed=changed,
            )
        )

        if changed:
            if "대상 아님" in draft_v and "대상 아님" not in base_v:
                legal_notes.append(f"[{label}] 체류자격 제한 또는 연장 불가 조항이 신규 추가되었습니다.")
            elif "대상 아님" in base_v and "대상 아님" not in draft_v:
                legal_notes.append(f"[{label}] 기존 신청 제한(불가) 규정이 해제되었습니다. 정밀 법령 검토가 필요합니다.")

    return ScenarioDiffOut(
        draft_id=draft["draft_id"],
        item_id=draft["item_id"],
        procedure=draft["procedure"],
        status_code=draft["status_code"],
        scenario=draft["scenario"],
        lifecycle_state=draft["lifecycle_state"],
        created_by=draft["created_by"],
        created_at=draft["created_at"],
        reviewed_by=draft["reviewed_by"],
        reviewed_at=draft["reviewed_at"],
        fields=diff_items,
        evidence_url=draft["evidence_url"] or "",
        evidence_title=draft["evidence_title"] or "",
        editor_note=draft["editor_note"] or "",
        has_legal_impact=bool(draft["has_legal_impact"] or legal_notes),
        legal_impact_notes=legal_notes,
    )


# ---------------------------------------------------------------------------
# Office Overrides Management (26 Immigration Offices)
# ---------------------------------------------------------------------------
def list_offices_status(store: KnowledgeStore) -> Dict[str, Any]:
    """Returns directory of all 26 immigration offices with override counts and review states."""
    if not LOCAL_PRACTICE_FILE.is_file():
        offices_list = []
    else:
        practice_data = json.loads(LOCAL_PRACTICE_FILE.read_text(encoding="utf-8"))
        offices_list = practice_data.get("offices", [])

    counts_rows = store.all(
        """
        SELECT office_id,
               COUNT(*) AS total_overrides,
               SUM(CASE WHEN review_state = 'APPROVED' THEN 1 ELSE 0 END) AS approved_count,
               SUM(CASE WHEN review_state IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW') THEN 1 ELSE 0 END) AS pending_count
        FROM checklist_office_overrides
        GROUP BY office_id
        """
    )
    counts_map = {r["office_id"]: dict(r) for r in counts_rows}

    enriched = []
    for o in offices_list:
        oid = o["id"]
        c = counts_map.get(oid, {"total_overrides": 0, "approved_count": 0, "pending_count": 0})
        enriched.append({
            "id": oid,
            "name": o.get("name_ko", oid),
            "region": o.get("region", "기타"),
            "total_overrides": c["total_overrides"],
            "approved_count": c["approved_count"],
            "pending_count": c["pending_count"],
        })

    return {"offices": enriched}


def save_office_override(
    store: KnowledgeStore, ov_in: OfficeOverrideIn, actor: str, actor_role: OperatorRole
) -> Dict[str, Any]:
    """Creates or updates an office-specific override requirement."""
    if not can_edit(actor_role):
        raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "Editor permissions required.")

    # Validate office code
    if LOCAL_PRACTICE_FILE.is_file():
        p_data = json.loads(LOCAL_PRACTICE_FILE.read_text(encoding="utf-8"))
        valid_offices = {o["id"] for o in p_data.get("offices", [])}
        if ov_in.office_id not in valid_offices:
            raise KnowledgeError(PipelineError.EXTRACTION_INVALID, f"Invalid office ID '{ov_in.office_id}'.")

    now = utc_now()
    ovr_id = f"ovr_{ov_in.item_id}_{ov_in.office_id}"

    with store._lock:
        store.conn.execute("BEGIN IMMEDIATE")
        try:
            store.conn.execute(
                """
                INSERT INTO checklist_office_overrides (
                    override_id, office_id, item_id, procedure, status_code,
                    diff_type, override_text, evidence_url, evidence_title, evidence_issuer,
                    confirmed_date, effective_start, effective_end, review_state,
                    created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?, ?)
                ON CONFLICT(override_id) DO UPDATE SET
                    diff_type = excluded.diff_type,
                    override_text = excluded.override_text,
                    evidence_url = excluded.evidence_url,
                    evidence_title = excluded.evidence_title,
                    evidence_issuer = excluded.evidence_issuer,
                    confirmed_date = excluded.confirmed_date,
                    effective_start = excluded.effective_start,
                    effective_end = excluded.effective_end,
                    review_state = 'DRAFT',
                    updated_at = excluded.updated_at
                """,
                (
                    ovr_id,
                    ov_in.office_id,
                    ov_in.item_id,
                    ov_in.procedure,
                    ov_in.status_code,
                    ov_in.diff_type,
                    ov_in.override_text,
                    ov_in.evidence_url,
                    ov_in.evidence_title,
                    ov_in.evidence_issuer,
                    ov_in.confirmed_date,
                    ov_in.effective_start,
                    ov_in.effective_end,
                    actor,
                    now,
                    now,
                ),
            )
            store.conn.execute(
                """
                INSERT INTO audit_log (audit_id, entity_type, entity_id, action, actor, actor_kind, before_json, after_json, reason, at)
                VALUES (?, 'office_override', ?, 'save_office_override', ?, 'human_operator', '{}', ?, 'Office override update', ?)
                """,
                (new_id("aud"), ovr_id, actor, json.dumps(ov_in.model_dump()), now),
            )
            store.conn.execute("COMMIT")
        except Exception:
            store.conn.execute("ROLLBACK")
            raise

    return {"override_id": ovr_id, "status": "saved"}


# ---------------------------------------------------------------------------
# Pre-publish Validation Gate & Safe Release Pipeline
# ---------------------------------------------------------------------------
def run_prepublish_validation(store: KnowledgeStore) -> PublishValidationReport:
    """Pre-publish validation gate checking 647 item preservation, exact counts, canonical IDs, and evidence integrity."""
    errors: List[str] = []
    warnings: List[str] = []
    checks: List[Dict[str, Any]] = []

    # 1. Check exact 647 items count
    total = store.one("SELECT COUNT(*) AS c FROM checklist_items")["c"]
    if total != 647:
        errors.append(f"Data Preservation Error: Found {total} scenarios in database (expected exactly 647).")
        checks.append({"name": "total_items_count_preserved", "status": "FAIL", "expected": 647, "actual": total})
    else:
        checks.append({"name": "total_items_count_preserved", "status": "PASS", "expected": 647, "actual": total, "details": "All 647 scenarios preserved"})

    # 2. Check exact procedure counts (224 / 251 / 172)
    ext_c = store.one("SELECT COUNT(*) AS c FROM checklist_items WHERE procedure = 'extension'")["c"]
    chg_c = store.one("SELECT COUNT(*) AS c FROM checklist_items WHERE procedure = 'change'")["c"]
    reg_c = store.one("SELECT COUNT(*) AS c FROM checklist_items WHERE procedure = 'registration'")["c"]

    if ext_c != 224:
        errors.append(f"Extension count mismatch: {ext_c} (expected exactly 224).")
        checks.append({"name": "extension_items_preserved", "status": "FAIL", "expected": 224, "actual": ext_c})
    else:
        checks.append({"name": "extension_items_preserved", "status": "PASS", "expected": 224, "actual": ext_c})

    if chg_c != 251:
        errors.append(f"Change count mismatch: {chg_c} (expected exactly 251).")
        checks.append({"name": "change_items_preserved", "status": "FAIL", "expected": 251, "actual": chg_c})
    else:
        checks.append({"name": "change_items_preserved", "status": "PASS", "expected": 251, "actual": chg_c})

    if reg_c != 172:
        errors.append(f"Registration count mismatch: {reg_c} (expected exactly 172).")
        checks.append({"name": "registration_items_preserved", "status": "FAIL", "expected": 172, "actual": reg_c})
    else:
        checks.append({"name": "registration_items_preserved", "status": "PASS", "expected": 172, "actual": reg_c})

    # 3. Canonical ID format checks (e-XXXX, c-XXXX, r-XXXX)
    bad_ext_ids = store.one("SELECT COUNT(*) AS c FROM checklist_items WHERE procedure = 'extension' AND id NOT GLOB 'e-[0-9][0-9][0-9][0-9]'")["c"]
    bad_chg_ids = store.one("SELECT COUNT(*) AS c FROM checklist_items WHERE procedure = 'change' AND id NOT GLOB 'c-[0-9][0-9][0-9][0-9]'")["c"]
    bad_reg_ids = store.one("SELECT COUNT(*) AS c FROM checklist_items WHERE procedure = 'registration' AND id NOT GLOB 'r-[0-9][0-9][0-9][0-9]'")["c"]
    if bad_ext_ids + bad_chg_ids + bad_reg_ids > 0:
        errors.append(f"Canonical ID Error: Found non-conforming IDs (ext: {bad_ext_ids}, chg: {bad_chg_ids}, reg: {bad_reg_ids}). Expected e-XXXX, c-XXXX, r-XXXX.")
        checks.append({"name": "id_format_integrity", "status": "FAIL", "details": "Malformed scenario IDs detected"})
    else:
        checks.append({"name": "id_format_integrity", "status": "PASS", "details": "All 647 scenario IDs conform to canonical e-*, c-*, r-* schemes"})

    # 4. Check approved drafts without valid HTTPS evidence
    approved_no_ev = store.one(
        "SELECT COUNT(*) AS c FROM checklist_drafts WHERE lifecycle_state = 'APPROVED' AND (evidence_url = '' OR evidence_url NOT LIKE 'https://%')"
    )["c"]
    if approved_no_ev > 0:
        errors.append(f"Evidence Gate Error: {approved_no_ev} approved drafts lack valid HTTPS evidence URLs.")
        checks.append({"name": "approved_evidence_gate", "status": "FAIL", "actual": approved_no_ev})
    else:
        checks.append({"name": "approved_evidence_gate", "status": "PASS", "details": "All approved drafts have verified HTTPS evidence"})

    # 5. Check pending drafts
    open_drafts_count = store.one(
        "SELECT COUNT(*) AS c FROM checklist_drafts WHERE lifecycle_state IN ('SUBMITTED', 'UNDER_REVIEW')"
    )["c"]
    if open_drafts_count > 0:
        warnings.append(f"Attention: {open_drafts_count} drafts are pending review and will not be published in this release.")

    approved_count = store.one(
        "SELECT COUNT(*) AS c FROM checklist_drafts WHERE lifecycle_state = 'APPROVED'"
    )["c"]

    # 6. Check storage durability
    is_durable = getattr(store, "durable", True)
    if not is_durable:
        warnings.append("경고: SQLite 저장소가 메모리(:memory:) 모드로 실행 중입니다. 서버 재시작 시 휘발될 수 있습니다.")

    # 7. Compute combined canonical dataset checksum
    all_rows = store.all(
        "SELECT id, status_code, scenario, required_text, conditional_text, application_text, note_text, version_no FROM checklist_items ORDER BY id"
    )
    canonical_repr = json.dumps([dict(r) for r in all_rows], sort_keys=True, ensure_ascii=False)
    dataset_checksum = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

    passed = len(errors) == 0

    return PublishValidationReport(
        valid=passed,
        passed=passed,
        total_items=total,
        total_scenarios=total,
        procedure_counts={"extension": ext_c, "change": chg_c, "registration": reg_c},
        approved_drafts_count=approved_count,
        pending_drafts_count=open_drafts_count,
        checks=checks,
        errors=errors,
        warnings=warnings,
        checked_at=utc_now(),
        durable_storage=is_durable,
        dataset_checksum=dataset_checksum,
    )


def execute_publish_release(
    store: KnowledgeStore,
    release_in: ReleaseRequestIn,
    actor: str,
    actor_role: OperatorRole,
) -> Dict[str, Any]:
    """Executes safe atomic release: validates invariants, applies approved drafts, updates files, and records snapshot."""
    if not can_publish(actor_role):
        raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "Publisher permissions required for release.")

    report = run_prepublish_validation(store)
    if not report.valid:
        raise KnowledgeError(
            PipelineError.TRANSITION_FORBIDDEN,
            f"Pre-publish validation failed: {'; '.join(report.errors)}",
        )

    now = utc_now()
    tag = release_in.release_tag
    if tag:
        existing = store.one("SELECT release_id FROM checklist_releases WHERE release_tag = ?", (tag,))
        if existing:
            raise KnowledgeError(PipelineError.DUPLICATE_FACT, f"Release tag '{tag}' already exists. Please choose a unique tag.")
    else:
        tag = f"release-{now[:10].replace('-', '')}-{datetime.now().strftime('%H%M%S')}"

    release_id = new_id("rel")

    # Snapshot existing items before changes for rollback
    pre_snapshot = [dict(r) for r in store.all("SELECT * FROM checklist_items ORDER BY id")]

    with store._lock:
        store.conn.execute("BEGIN IMMEDIATE")
        try:
            # 1. Apply any remaining APPROVED drafts
            approved_drafts = store.all(
                "SELECT * FROM checklist_drafts WHERE lifecycle_state = 'APPROVED'"
            )
            for d in approved_drafts:
                item = store.one("SELECT * FROM checklist_items WHERE id = ?", (d["item_id"],))
                new_ver = (item["version_no"] if item else 1) + 1
                store.conn.execute(
                    """
                    UPDATE checklist_items SET
                        required_text = ?, conditional_text = ?, application_text = ?, note_text = ?,
                        review_state = 'PUBLISHED', editor_note = ?, version_no = ?,
                        updated_at = ?, updated_by = ?
                    WHERE id = ?
                    """,
                    (
                        d["required_text"],
                        d["conditional_text"],
                        d["application_text"],
                        d["note_text"],
                        d["editor_note"],
                        new_ver,
                        now,
                        actor,
                        d["item_id"],
                    ),
                )
                store.conn.execute(
                    "UPDATE checklist_drafts SET lifecycle_state = 'PUBLISHED', published_by = ?, published_at = ? WHERE draft_id = ?",
                    (actor, now, d["draft_id"]),
                )

            # 2. Export updated JSON datasets to disk atomically
            files_map = {
                "extension": CHECKLISTS_DATA_DIR / "extension-202609.json",
                "change": CHECKLISTS_DATA_DIR / "change-202609.json",
                "registration": CHECKLISTS_DATA_DIR / "registration-202609.json",
            }
            checksums = {}
            fs_persisted = True

            for proc, path in files_map.items():
                items = [
                    dict(r)
                    for r in store.all(
                        "SELECT id, status_code, scenario, required_text, conditional_text, application_text, note_text, source_line, source_section, review_state FROM checklist_items WHERE procedure = ? ORDER BY id",
                        (proc,),
                    )
                ]
                existing_meta = {}
                if path.is_file():
                    try:
                        existing_meta = json.loads(path.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                payload = dict(existing_meta) if existing_meta else {}
                payload["schema_version"] = payload.get("schema_version", 1)
                payload["procedure"] = proc
                payload["row_count"] = len(items)
                payload["compiled_date"] = now[:10]
                payload["items"] = items

                serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
                checksums[proc] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

                if store.durable:
                    try:
                        tmp_path = path.with_suffix(".tmp")
                        tmp_path.write_text(serialized, encoding="utf-8")
                        tmp_path.replace(path)
                    except OSError as e:
                        logger.warning("Filesystem unwritable for %s: %s", path, e)
                        fs_persisted = False
                else:
                    fs_persisted = False

            # Record release metadata and snapshot
            rel_meta = {
                "release_id": release_id,
                "release_tag": tag,
                "release_note": release_in.release_note,
                "status": "PUBLISHED",
                "checksums": checksums,
                "fs_persisted": fs_persisted,
                "snapshot": pre_snapshot,
                "applied_draft_ids": [d["draft_id"] for d in approved_drafts],
                "validation": report.model_dump(),
            }

            store.conn.execute(
                """
                INSERT INTO checklist_releases (
                    release_id, release_tag, target_procedure, approved_draft_count,
                    total_scenario_count, validation_passed, validation_report,
                    payload_checksum, published_by, published_at, rollback_ref
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                """,
                (
                    release_id,
                    tag,
                    release_in.target_procedure,
                    len(approved_drafts),
                    report.total_scenarios,
                    json.dumps(rel_meta, ensure_ascii=False),
                    json.dumps(checksums),
                    actor,
                    now,
                    "self",
                ),
            )

            store.conn.execute(
                """
                INSERT INTO audit_log (audit_id, entity_type, entity_id, action, actor, actor_kind, before_json, after_json, reason, at)
                VALUES (?, 'checklist_release', ?, 'publish_release', ?, 'human_operator', '{}', ?, ?, ?)
                """,
                (new_id("aud"), release_id, actor, json.dumps({"tag": tag, "drafts_applied": len(approved_drafts)}), release_in.release_note, now),
            )
            store.conn.execute("COMMIT")
        except Exception:
            store.conn.execute("ROLLBACK")
            raise

    logger.info("publish_release_success release_id=%s tag=%s applied=%d", release_id, tag, len(approved_drafts))
    return {
        "release_id": release_id,
        "release_tag": tag,
        "status": "PUBLISHED",
        "applied_count": len(approved_drafts),
        "total_scenario_count": report.total_scenarios,
        "checksums": checksums,
        "published_at": now,
        "fs_persisted": fs_persisted,
    }


def execute_rollback_release(
    store: KnowledgeStore,
    release_id: str,
    rollback_in: RollbackRequestIn,
    actor: str,
    actor_role: OperatorRole,
) -> Dict[str, Any]:
    """Rolls back checklist_items to the baseline snapshot of a release."""
    if not can_publish(actor_role):
        raise KnowledgeError(PipelineError.TRANSITION_FORBIDDEN, "Publisher permissions required for rollback.")

    rel_row = store.one("SELECT * FROM checklist_releases WHERE release_id = ? OR release_tag = ?", (release_id, release_id))
    if not rel_row:
        raise KnowledgeError(PipelineError.NOT_FOUND, f"Release '{release_id}' not found.")

    try:
        report_data = json.loads(rel_row["validation_report"])
    except Exception:
        report_data = {}

    snapshot = report_data.get("snapshot")
    if not snapshot:
        raise KnowledgeError(PipelineError.EXTRACTION_INVALID, f"Release '{release_id}' does not have a valid baseline snapshot for rollback.")

    now = utc_now()
    rollback_tag = f"rollback-{rel_row['release_tag']}-{now[:10].replace('-', '')}"
    new_rel_id = new_id("rel")

    with store._lock:
        store.conn.execute("BEGIN IMMEDIATE")
        try:
            # 1. Restore checklist_items from snapshot
            for item in snapshot:
                store.conn.execute(
                    """
                    UPDATE checklist_items SET
                        required_text = ?, conditional_text = ?, application_text = ?, note_text = ?,
                        review_state = 'PUBLISHED', editor_note = ?, version_no = version_no + 1,
                        updated_at = ?, updated_by = ?
                    WHERE id = ?
                    """,
                    (
                        item["required_text"],
                        item["conditional_text"],
                        item["application_text"],
                        item["note_text"],
                        f"Rolled back from {rel_row['release_tag']}: {rollback_in.rollback_note}",
                        now,
                        actor,
                        item["id"],
                    ),
                )

            # 2. Update files on disk
            files_map = {
                "extension": CHECKLISTS_DATA_DIR / "extension-202609.json",
                "change": CHECKLISTS_DATA_DIR / "change-202609.json",
                "registration": CHECKLISTS_DATA_DIR / "registration-202609.json",
            }
            checksums = {}
            for proc, path in files_map.items():
                items = [
                    dict(r)
                    for r in store.all(
                        "SELECT id, status_code, scenario, required_text, conditional_text, application_text, note_text, source_line, source_section, review_state FROM checklist_items WHERE procedure = ? ORDER BY id",
                        (proc,),
                    )
                ]
                existing_meta = {}
                if path.is_file():
                    try:
                        existing_meta = json.loads(path.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                payload = dict(existing_meta) if existing_meta else {}
                payload["schema_version"] = payload.get("schema_version", 1)
                payload["procedure"] = proc
                payload["row_count"] = len(items)
                payload["compiled_date"] = now[:10]
                payload["items"] = items
                serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
                checksums[proc] = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
                if store.durable:
                    try:
                        tmp = path.with_suffix(".tmp")
                        tmp.write_text(serialized, encoding="utf-8")
                        tmp.replace(path)
                    except OSError:
                        pass

            # 3. Update original release status and record rollback release
            report_data["status"] = "ROLLED_BACK"
            report_data["rolled_back_at"] = now
            report_data["rolled_back_by"] = actor
            store.conn.execute(
                "UPDATE checklist_releases SET validation_report = ? WHERE release_id = ?",
                (json.dumps(report_data, ensure_ascii=False), rel_row["release_id"]),
            )

            rollback_meta = {
                "release_id": new_rel_id,
                "release_tag": rollback_tag,
                "status": "ROLLED_BACK",
                "release_note": rollback_in.rollback_note,
                "target_release": rel_row["release_tag"],
                "checksums": checksums,
            }
            store.conn.execute(
                """
                INSERT INTO checklist_releases (
                    release_id, release_tag, target_procedure, approved_draft_count,
                    total_scenario_count, validation_passed, validation_report,
                    payload_checksum, published_by, published_at, rollback_ref
                ) VALUES (?, ?, 'all', 0, 647, 1, ?, ?, ?, ?, ?)
                """,
                (
                    new_rel_id,
                    rollback_tag,
                    json.dumps(rollback_meta, ensure_ascii=False),
                    json.dumps(checksums),
                    actor,
                    now,
                    rel_row["release_id"],
                ),
            )

            store.conn.execute(
                """
                INSERT INTO audit_log (audit_id, entity_type, entity_id, action, actor, actor_kind, before_json, after_json, reason, at)
                VALUES (?, 'checklist_release', ?, 'rollback_release', ?, 'human_operator', ?, ?, ?, ?)
                """,
                (new_id("aud"), new_rel_id, actor, json.dumps({"target": rel_row["release_tag"]}), json.dumps({"rollback_tag": rollback_tag}), rollback_in.rollback_note, now),
            )
            store.conn.execute("COMMIT")
        except Exception:
            store.conn.execute("ROLLBACK")
            raise

    return {
        "release_id": new_rel_id,
        "release_tag": rollback_tag,
        "status": "ROLLED_BACK",
        "restored_from": rel_row["release_tag"],
        "checksums": checksums,
        "rolled_back_at": now,
    }


def get_active_published_checklists(store: KnowledgeStore, procedure: Optional[str] = None) -> Dict[str, Any]:
    """Returns currently published checklist dataset across all 3 procedures with checksums and latest release metadata."""
    latest_rel = store.one("SELECT * FROM checklist_releases ORDER BY published_at DESC LIMIT 1")
    ext_items = [dict(r) for r in store.all("SELECT id, status_code, scenario, required_text, conditional_text, application_text, note_text, source_line, source_section, review_state FROM checklist_items WHERE procedure = 'extension' ORDER BY id")]
    chg_items = [dict(r) for r in store.all("SELECT id, status_code, scenario, required_text, conditional_text, application_text, note_text, source_line, source_section, review_state FROM checklist_items WHERE procedure = 'change' ORDER BY id")]
    reg_items = [dict(r) for r in store.all("SELECT id, status_code, scenario, required_text, conditional_text, application_text, note_text, source_line, source_section, review_state FROM checklist_items WHERE procedure = 'registration' ORDER BY id")]

    all_items = ext_items + chg_items + reg_items
    canonical_repr = json.dumps(all_items, sort_keys=True, ensure_ascii=False)
    checksum = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

    rel_tag = latest_rel["release_tag"] if latest_rel else "baseline-202609"
    pub_at = latest_rel["published_at"] if latest_rel else "2026-10-19T00:00:00Z"

    res = {
        "status": "active",
        "release_tag": rel_tag,
        "published_at": pub_at,
        "checksum_sha256": checksum,
        "total_items": len(all_items),
        "extension": {"procedure": "extension", "row_count": len(ext_items), "items": ext_items},
        "change": {"procedure": "change", "row_count": len(chg_items), "items": chg_items},
        "registration": {"procedure": "registration", "row_count": len(reg_items), "items": reg_items},
    }
    if procedure and procedure in res:
        res["filtered_procedure"] = procedure
    return res


def get_release_preview(store: KnowledgeStore, release_id: str) -> Dict[str, Any]:
    """Returns preview dataset for a specified release candidate or release."""
    rel = store.one("SELECT * FROM checklist_releases WHERE release_id = ? OR release_tag = ?", (release_id, release_id))
    if not rel:
        raise KnowledgeError(PipelineError.NOT_FOUND, f"Release '{release_id}' not found.")

    try:
        report_data = json.loads(rel["validation_report"])
    except Exception:
        report_data = {}

    published_data = get_active_published_checklists(store)
    published_data["status"] = report_data.get("status", "PREVIEW_READY")
    published_data["release_tag"] = rel["release_tag"]
    published_data["release_id"] = rel["release_id"]
    published_data["published_at"] = rel["published_at"]
    published_data["is_preview"] = True
    return published_data


def list_releases(store: KnowledgeStore) -> List[Dict[str, Any]]:
    """Returns list of releases with status and audit references."""
    rows = store.all("SELECT * FROM checklist_releases ORDER BY published_at DESC LIMIT 50")
    out = []
    for r in rows:
        try:
            v_report = json.loads(r["validation_report"])
        except Exception:
            v_report = {}
        out.append({
            "release_id": r["release_id"],
            "release_tag": r["release_tag"],
            "target_procedure": r["target_procedure"],
            "approved_draft_count": r["approved_draft_count"],
            "total_scenario_count": r["total_scenario_count"],
            "validation_passed": bool(r["validation_passed"]),
            "payload_checksum": r["payload_checksum"],
            "published_by": r["published_by"],
            "published_at": r["published_at"],
            "status": v_report.get("status", "PUBLISHED"),
            "release_note": v_report.get("release_note", ""),
            "rollback_ref": r["rollback_ref"],
        })
    return out
