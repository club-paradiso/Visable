"""Artemis Evidence Review Workbench & Non-Authoritative Draft Governance (Mission 004-D).

Provides both a scriptable CLI and a lightweight local HTTP server for authorized
human reviewers to:
1. Browse all 60 benchmark candidate items (16 Group A priority + 44 Group B standard).
2. Inspect Question, Proposed Answer, and Supporting Evidence side by side.
3. Access direct official statutory/manual links and provenance metadata.
4. Record draft notes, statutory concerns, legal conflicts, and requests for revision.
5. Export review packages and import external review bundles with schema verification.
6. Track audit trails without silently overwriting prior decisions.
7. Maintain strict fail-closed boundaries: authoritative 'official_gold' promotion remains
   disabled until independent cryptographic human attestation is provided.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime as dt
import http.server
import json
import os
import re
import socketserver
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BOOTSTRAP_DIR = Path(__file__).resolve().parent
EXPERIMENT_ROOT = BOOTSTRAP_DIR.parent
BENCHMARKS_DIR = BOOTSTRAP_DIR / "benchmarks"
REVIEWS_DIR = BOOTSTRAP_DIR / "reviews"
PACKETS_DIR = BOOTSTRAP_DIR / "review_packets"
LEDGER_PATH = REVIEWS_DIR / "legal_review_ledger.json"

if str(BOOTSTRAP_DIR) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_DIR))

from legal_review_governance import (  # noqa: E402
    AuthoritativeGoldPromotionDisabledError,
    LegalReviewLedger,
    ReviewDecision,
    ReviewIntegrityError,
    ReviewStatus,
    compute_evidence_snapshot_hash,
    is_ai_identifier,
)


@dataclass
class ReviewerDraftNote:
    timestamp: str
    author: str
    notes: str
    statutory_conflicts: Optional[str] = None
    action_type: str = "draft_note"  # draft_note, request_revision, flag_source, supersede_draft

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


class ReviewWorkbench:
    """Core backend and controller for the Artemis Review Workbench."""

    def __init__(self, ledger: Optional[LegalReviewLedger] = None, packets_dir: Path = PACKETS_DIR):
        self.ledger = ledger or LegalReviewLedger.load_or_initialize()
        self.packets_dir = packets_dir

    def get_all_items_summary(self, status_filter: Optional[str] = None,
                              group_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns summarized candidate items for workbench browsing."""
        results = []
        for rec in sorted(self.ledger.records.values(), key=lambda r: r.item_id):
            st = rec.review_status.value if isinstance(rec.review_status, ReviewStatus) else rec.review_status
            if status_filter and st != status_filter:
                continue
            if group_filter and group_filter.lower() not in rec.group.lower():
                continue

            has_packet = (self.packets_dir / f"{rec.item_id}.json").exists()
            results.append({
                "item_id": rec.item_id,
                "split": rec.split,
                "group": rec.group,
                "question": rec.question[:80] + ("..." if len(rec.question) > 80 else ""),
                "proposed_answer": rec.proposed_answer[:60],
                "review_status": st,
                "reviewer_id": rec.reviewer_id,
                "has_packet": has_packet,
                "transition_count": len(rec.transition_history),
                "evidence_count": len(rec.evidence_references),
            })
        return results

    def get_item_detail(self, item_id: str) -> Dict[str, Any]:
        """Returns side-by-side review detail including packet, ledger state, and history."""
        if item_id not in self.ledger.records:
            raise KeyError(f"Item '{item_id}' not found in review ledger")

        rec = self.ledger.records[item_id]
        packet_data = None
        pkt_file = self.packets_dir / f"{item_id}.json"
        if pkt_file.exists():
            try:
                packet_data = json.loads(pkt_file.read_text(encoding="utf-8"))
            except Exception:
                packet_data = None

        return {
            "item_id": rec.item_id,
            "record_id": rec.record_id,
            "split": rec.split,
            "group": rec.group,
            "question": rec.question,
            "proposed_answer": rec.proposed_answer,
            "review_status": rec.review_status.value if isinstance(rec.review_status, ReviewStatus) else rec.review_status,
            "reviewer_id": rec.reviewer_id,
            "decision": rec.decision.value if isinstance(rec.decision, ReviewDecision) else rec.decision,
            "decision_reason": rec.decision_reason,
            "evidence_snapshot_sha256": rec.evidence_snapshot_sha256,
            "updated_at": rec.updated_at,
            "evidence_references": rec.evidence_references,
            "transition_history": [t.to_dict() for t in rec.transition_history],
            "packet": packet_data,
            "governance_mode": "local_non_authoritative_prototype",
            "official_gold_promotion_enabled": False,
        }

    def record_draft_annotation(
        self,
        item_id: str,
        author: str,
        notes: str,
        statutory_conflicts: Optional[str] = None,
        action_type: str = "draft_note",
    ) -> Dict[str, Any]:
        """Records a reviewer draft note or revision concern without claiming authoritative approval."""
        if item_id not in self.ledger.records:
            raise KeyError(f"Item '{item_id}' not found in review ledger")
        if not author or not author.strip():
            raise ReviewIntegrityError("Reviewer author name cannot be empty")
        if not notes or not notes.strip():
            raise ReviewIntegrityError("Draft notes cannot be empty")

        rec = self.ledger.records[item_id]
        now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
        prev_status = rec.review_status.value if isinstance(rec.review_status, ReviewStatus) else rec.review_status

        # Transition status if revision requested or item claimed
        target_status = prev_status
        if action_type == "request_revision":
            target_status = ReviewStatus.NEEDS_REVISION.value
            rec.review_status = ReviewStatus.NEEDS_REVISION
        elif action_type == "flag_source":
            target_status = ReviewStatus.NEEDS_REVISION.value
            rec.review_status = ReviewStatus.NEEDS_REVISION
        elif prev_status == ReviewStatus.UNREVIEWED.value:
            target_status = ReviewStatus.IN_REVIEW.value
            rec.review_status = ReviewStatus.IN_REVIEW

        rec.reviewer_id = author.strip()
        rec.updated_at = now_iso

        combined_reason = f"[{action_type.upper()}] {notes.strip()}"
        if statutory_conflicts:
            combined_reason += f" | Conflicts: {statutory_conflicts.strip()}"

        rec.transition_history.append(
            type(rec.transition_history[0] if rec.transition_history else object)(  # type: ignore
                timestamp=now_iso,
                from_status=prev_status,
                to_status=target_status,
                actor_id=author.strip(),
                is_human=True,
                reason=combined_reason,
                notes=statutory_conflicts,
            ) if rec.transition_history else None  # type: ignore
        )
        # If transition_history was empty or object was None, construct manually
        if not rec.transition_history or rec.transition_history[-1] is None:
            from legal_review_governance import StateTransition
            if rec.transition_history and rec.transition_history[-1] is None:
                rec.transition_history.pop()
            rec.transition_history.append(StateTransition(
                timestamp=now_iso,
                from_status=prev_status,
                to_status=target_status,
                actor_id=author.strip(),
                is_human=True,
                reason=combined_reason,
                notes=statutory_conflicts,
            ))

        self.ledger.save()
        return self.get_item_detail(item_id)

    def export_review_package(self, output_path: Path) -> Dict[str, Any]:
        """Exports the entire review package (ledger, packets manifest, and item details)."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        items_full = [self.get_item_detail(cid) for cid in sorted(self.ledger.records.keys())]

        package = {
            "package_version": "artemis-workbench-export/1.0",
            "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "total_items": len(items_full),
            "status_counts": self.ledger.get_status_counts(),
            "items": items_full,
            "export_note": "Non-authoritative draft review package. Official gold promotion disabled.",
        }
        output_path.write_text(json.dumps(package, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "status": "success",
            "output_path": str(output_path),
            "total_items": len(items_full),
        }

    def import_review_package(self, input_path: Path) -> Dict[str, Any]:
        """Imports and merges reviewer draft annotations without overwriting prior audit history."""
        if not input_path.exists():
            raise FileNotFoundError(f"Import package not found at {input_path}")

        data = json.loads(input_path.read_text(encoding="utf-8"))
        if "items" not in data:
            raise ReviewIntegrityError("Invalid package: 'items' array missing")

        imported_count = 0
        new_transitions = 0

        for row in data.get("items", []):
            cid = row.get("item_id")
            if cid not in self.ledger.records:
                continue

            rec = self.ledger.records[cid]
            existing_ts = {t.timestamp for t in rec.transition_history}

            # Import any new transitions from external package
            for t in row.get("transition_history", []):
                if t.get("timestamp") not in existing_ts:
                    from legal_review_governance import StateTransition
                    rec.transition_history.append(StateTransition(
                        timestamp=t["timestamp"],
                        from_status=t["from_status"],
                        to_status=t["to_status"],
                        actor_id=t["actor_id"],
                        is_human=bool(t.get("is_human", True)),
                        reason=t.get("reason"),
                        notes=t.get("notes"),
                    ))
                    new_transitions += 1
            imported_count += 1

        self.ledger.save()
        return {
            "status": "success",
            "imported_items": imported_count,
            "new_transitions": new_transitions,
        }


# ---------------------------------------------------------------------------
# HTML Template for Workbench GUI (Accessible, Keyboard Navigable, Side-by-side)
# ---------------------------------------------------------------------------
WORKBENCH_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Artemis 법률 검토 워크벤치 (Legal Evidence Review Workbench)</title>
<style>
:root {
  --bg: #f8fafc;
  --panel-bg: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --text-muted: #64748b;
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --danger: #dc2626;
  --warning: #d97706;
  --success: #16a34a;
  --badge-unreviewed: #94a3b8;
  --badge-in-review: #38bdf8;
  --badge-needs-revision: #f59e0b;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  height: 100vh;
  display: flex;
  flex-direction: column;
}
header {
  background: var(--panel-bg);
  border-bottom: 1px solid var(--border);
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
header h1 { font-size: 1.15rem; font-weight: 700; color: #1e293b; }
.banner-badge {
  background: #fef3c7;
  color: #92400e;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}
.workbench-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}
.sidebar {
  width: 360px;
  border-right: 1px solid var(--border);
  background: var(--panel-bg);
  display: flex;
  flex-direction: column;
}
.filter-bar {
  padding: 12px;
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 8px;
}
.filter-bar select, .filter-bar input {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.85rem;
  flex: 1;
}
.item-list {
  flex: 1;
  overflow-y: auto;
}
.item-row {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.15s;
}
.item-row:hover, .item-row.active {
  background: #f1f5f9;
}
.item-row .id-badge {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--primary);
  font-weight: 600;
}
.item-row .q-snippet {
  font-size: 0.82rem;
  color: #334155;
  margin-top: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.status-pill {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
}
.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: var(--bg);
}
.card {
  background: var(--panel-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.card h2 { font-size: 1rem; margin-bottom: 12px; color: #1e293b; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; }
.side-by-side {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}
.evidence-block {
  background: #f8fafc;
  border-left: 4px solid var(--primary);
  padding: 12px;
  margin-top: 8px;
  border-radius: 0 4px 4px 0;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  font-size: 0.85rem;
  margin-top: 10px;
}
.meta-item strong { color: var(--text-muted); display: block; font-size: 0.75rem; }
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 0.8rem; font-weight: 600; margin-bottom: 4px; }
.form-group textarea, .form-group input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.85rem;
}
.btn-group { display: flex; gap: 8px; }
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-primary { background: var(--primary); color: white; }
.btn-warning { background: var(--warning); color: white; }
.btn-secondary { background: #e2e8f0; color: #334155; }
.btn:hover { opacity: 0.9; }
.audit-list { font-size: 0.8rem; }
.audit-item { padding: 8px 0; border-bottom: 1px solid #f1f5f9; }
.audit-item:last-child { border-bottom: none; }
</style>
</head>
<body>
<header>
  <div>
    <h1>Artemis 법률 검토 워크벤치 (Review Workbench)</h1>
  </div>
  <div style="display:flex; gap:10px; align-items:center;">
    <span class="banner-badge">로컬 비권위적 프로토타입 (공식 골드 승격 비활성화)</span>
    <button class="btn btn-secondary" onclick="exportPackage()">워크벤치 내보내기</button>
  </div>
</header>
<div class="workbench-container">
  <div class="sidebar">
    <div class="filter-bar">
      <select id="groupFilter" onchange="loadItems()">
        <option value="">모든 그룹 (60문항)</option>
        <option value="Group A">Group A 우선 심사 (16문항)</option>
        <option value="Group B">Group B 표준 대조 (44문항)</option>
      </select>
      <select id="statusFilter" onchange="loadItems()">
        <option value="">모든 상태</option>
        <option value="unreviewed">검토 대기 (unreviewed)</option>
        <option value="in_review">검토 진행 중 (in_review)</option>
        <option value="needs_revision">수정 요청 (needs_revision)</option>
      </select>
    </div>
    <div class="item-list" id="itemList">
      <div style="padding:20px; text-align:center; color:#94a3b8;">목록 로딩 중...</div>
    </div>
  </div>
  <div class="content-area" id="detailArea">
    <div style="padding:40px; text-align:center; color:#94a3b8;">좌측 목록에서 검토할 문항을 선택하십시오.</div>
  </div>
</div>
<script>
let currentItemId = null;

async function loadItems() {
  const g = document.getElementById('groupFilter').value;
  const s = document.getElementById('statusFilter').value;
  const res = await fetch(`/api/items?group=${encodeURIComponent(g)}&status=${encodeURIComponent(s)}`);
  const data = await res.json();
  const listEl = document.getElementById('itemList');
  listEl.innerHTML = '';

  data.forEach(item => {
    const row = document.createElement('div');
    row.className = `item-row ${item.item_id === currentItemId ? 'active' : ''}`;
    row.onclick = () => selectItem(item.item_id);
    row.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span class="id-badge">${item.item_id}</span>
        <span class="status-pill" style="background:#e2e8f0;">${item.review_status}</span>
      </div>
      <div class="q-snippet">${item.question}</div>
      <div style="font-size:0.7rem; color:#94a3b8; margin-top:4px;">
        ${item.group.includes('Group A') ? '🔴 우선심사' : '⚪ 표준대조'} | 이력 ${item.transition_count}건
      </div>
    `;
    listEl.appendChild(row);
  });
}

async function selectItem(itemId) {
  currentItemId = itemId;
  loadItems();
  const res = await fetch(`/api/item/${itemId}`);
  const item = await res.json();
  const area = document.getElementById('detailArea');

  const evHtml = item.evidence_references.map((ev, idx) => `
    <div class="evidence-block">
      <div style="font-weight:600; font-size:0.85rem; color:#1e293b;">증거 #${idx+1}: ${ev.title || ev.evidence_id}</div>
      <div class="meta-grid">
        <div class="meta-item"><strong>문서 식별자</strong>${ev.document_id || '-'}</div>
        <div class="meta-item"><strong>조항/조문</strong>${ev.provision || '-'}</div>
        <div class="meta-item"><strong>시행일자</strong>${ev.effective_date || '-'}</div>
        <div class="meta-item"><strong>공식 출처</strong><a href="${ev.source_url}" target="_blank" rel="noopener">법령/지침 링크 ↗</a></div>
      </div>
      <div style="margin-top:8px; font-size:0.85rem; font-family:var(--font-mono); background:#fff; padding:8px; border:1px solid #e2e8f0; border-radius:4px;">
        ${ev.text_excerpt || '(원문 발췌문 없음)'}
      </div>
      <div style="font-size:0.7rem; color:#94a3b8; margin-top:4px;">SHA-256: ${ev.content_sha256 || '-'}</div>
    </div>
  `).join('');

  const auditHtml = item.transition_history.map(t => `
    <div class="audit-item">
      <div style="font-weight:600;">[${t.to_status}] ${t.actor_id} (${t.timestamp.slice(0,19)})</div>
      <div style="color:#475569;">${t.reason || '-'}</div>
      ${t.notes ? `<div style="color:#d97706; font-size:0.75rem;">충돌사항: ${t.notes}</div>` : ''}
    </div>
  `).join('');

  area.innerHTML = `
    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <span class="id-badge" style="font-size:0.9rem;">${item.item_id}</span>
          <h2 style="border:none; margin-top:4px; font-size:1.1rem;">${item.packet ? item.packet.title : item.item_id}</h2>
        </div>
        <span class="status-pill" style="background:#dbeafe; color:#1d4ed8; padding:4px 10px; font-size:0.8rem;">
          ${item.review_status}
        </span>
      </div>
    </div>

    <div class="side-by-side">
      <div class="card" style="margin-bottom:0;">
        <h2>1. 질의 내용 (Question)</h2>
        <div style="font-size:0.9rem; line-height:1.6; color:#1e293b; background:#f8fafc; padding:12px; border-radius:6px;">
          ${item.question}
        </div>
      </div>
      <div class="card" style="margin-bottom:0;">
        <h2>2. 제안 답변 및 예상 요건 (Proposed Answer)</h2>
        <div style="font-size:0.9rem; line-height:1.6; color:#0f766e; background:#f0fdfa; padding:12px; border-radius:6px;">
          ${item.proposed_answer}
        </div>
      </div>
    </div>

    <div class="card">
      <h2>3. 공공기관 공식 1차 출처 및 증거 원문 (Official Evidence)</h2>
      ${evHtml || '<div style="color:#94a3b8;">등록된 증거가 없습니다.</div>'}
    </div>

    <div class="card">
      <h2>4. 검토자 임시 검토 및 의견 기록 (Draft Workspace)</h2>
      <div class="form-group">
        <label>검토자 성명 또는 행정사 식별자</label>
        <input type="text" id="draftAuthor" placeholder="예: attorney_hong, administrative_agent_kim" value="${item.reviewer_id || ''}">
      </div>
      <div class="form-group">
        <label>법률 검토 실질 메모 및 해석 의견 (Review Notes)</label>
        <textarea id="draftNotes" rows="3" placeholder="지침 조항 대조 확인 결과, 단서 조항 유효성 등을 작성하십시오."></textarea>
      </div>
      <div class="form-group">
        <label>발견된 법령 충돌 또는 쟁점 사항 (Statutory Conflicts)</label>
        <textarea id="draftConflicts" rows="2" placeholder="구 지침과의 충돌, 지자체 조례와의 상이점 등"></textarea>
      </div>
      <div class="btn-group">
        <button class="btn btn-primary" onclick="saveDraft('draft_note')">임시 메모 저장</button>
        <button class="btn btn-warning" onclick="saveDraft('request_revision')">수정 요청 (needs_revision)</button>
        <button class="btn btn-secondary" onclick="saveDraft('flag_source')">출처 보완 플래그</button>
      </div>
      <div style="font-size:0.75rem; color:#94a3b8; margin-top:8px;">
        * 본 화면에서의 기록은 비권위적 로컬 원장에 저장되며, 공인 전자서명 없이는 공식 골드로 승격되지 않습니다.
      </div>
    </div>

    <div class="card">
      <h2>5. 검토 이력 및 변경 감사 로그 (Audit History)</h2>
      <div class="audit-list">
        ${auditHtml || '<div style="color:#94a3b8;">기록된 이력이 없습니다.</div>'}
      </div>
    </div>
  `;
}

async function saveDraft(actionType) {
  const author = document.getElementById('draftAuthor').value.trim();
  const notes = document.getElementById('draftNotes').value.trim();
  const conflicts = document.getElementById('draftConflicts').value.trim();

  if (!author) { alert('검토자 성명을 입력하십시오.'); return; }
  if (!notes) { alert('검토 메모를 입력하십시오.'); return; }

  const res = await fetch(`/api/item/${currentItemId}/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ author, notes, conflicts, action_type: actionType })
  });

  if (res.ok) {
    alert('임시 검토 내용이 성공적으로 기록되었습니다.');
    selectItem(currentItemId);
  } else {
    const err = await res.json();
    alert('저장 실패: ' + (err.error || '알 수 없는 오류'));
  }
}

async function exportPackage() {
  const res = await fetch('/api/export', { method: 'POST' });
  const data = await res.json();
  alert(`검토 패키지 내보내기 완료: 총 ${data.total_items}건이 저장되었습니다.`);
}

window.onload = loadItems;
</script>
</body>
</html>
"""


class WorkbenchHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler for Workbench API and GUI."""

    workbench: ReviewWorkbench

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(WORKBENCH_HTML.encode("utf-8"))

        elif path == "/api/items":
            g_filter = params.get("group", [None])[0]
            s_filter = params.get("status", [None])[0]
            items = self.workbench.get_all_items_summary(status_filter=s_filter, group_filter=g_filter)
            self._send_json(200, items)

        elif path.startswith("/api/item/"):
            item_id = path.replace("/api/item/", "").strip()
            try:
                detail = self.workbench.get_item_detail(item_id)
                self._send_json(200, detail)
            except KeyError as e:
                self._send_json(404, {"error": str(e)})

        elif path.startswith("/api/audit/"):
            item_id = path.replace("/api/audit/", "").strip()
            try:
                detail = self.workbench.get_item_detail(item_id)
                self._send_json(200, {"item_id": item_id, "history": detail["transition_history"]})
            except KeyError as e:
                self._send_json(404, {"error": str(e)})

        else:
            self._send_json(404, {"error": f"Path not found: {path}"})

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        if re.match(r"^/api/item/[A-Za-z0-9_-]+/draft$", path):
            item_id = path.split("/")[3]
            try:
                updated = self.workbench.record_draft_annotation(
                    item_id=item_id,
                    author=payload.get("author", ""),
                    notes=payload.get("notes", ""),
                    statutory_conflicts=payload.get("conflicts"),
                    action_type=payload.get("action_type", "draft_note"),
                )
                self._send_json(200, updated)
            except Exception as e:
                self._send_json(400, {"error": str(e)})

        elif path == "/api/export":
            out_file = REVIEWS_DIR / "workbench_export_latest.json"
            res = self.workbench.export_review_package(out_file)
            self._send_json(200, res)

        elif path == "/api/import":
            in_path = Path(payload.get("input_path", str(REVIEWS_DIR / "workbench_export_latest.json")))
            try:
                res = self.workbench.import_review_package(in_path)
                self._send_json(200, res)
            except Exception as e:
                self._send_json(400, {"error": str(e)})

        else:
            self._send_json(404, {"error": f"POST endpoint not found: {path}"})

    def _send_json(self, status: int, data: Any) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))


def run_workbench_server(port: int = 8420) -> None:
    """Launches local HTTP server for Workbench UI."""
    workbench = ReviewWorkbench()
    handler = WorkbenchHTTPHandler
    handler.workbench = workbench

    # Allow address reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"\n========================================================")
        print(f" Artemis Review Workbench is running at:")
        print(f" http://127.0.0.1:{port}")
        print(f" (Press Ctrl+C to terminate)")
        print(f"========================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Workbench server.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Artemis Legal Review Workbench CLI & Server")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # list
    list_p = subparsers.add_parser("list", help="List review items and status")
    list_p.add_argument("--status", help="Filter by review status")
    list_p.add_argument("--group", help="Filter by group (e.g. 'Group A')")

    # view
    view_p = subparsers.add_parser("view", help="View side-by-side detail of an item")
    view_p.add_argument("item_id", help="Benchmark Item ID")

    # draft
    draft_p = subparsers.add_parser("draft", help="Record draft reviewer note or revision concern")
    draft_p.add_argument("item_id", help="Benchmark Item ID")
    draft_p.add_argument("--author", required=True, help="Reviewer author name")
    draft_p.add_argument("--notes", required=True, help="Substantive draft notes")
    draft_p.add_argument("--conflicts", help="Identified statutory conflicts")
    draft_p.add_argument("--action", choices=["draft_note", "request_revision", "flag_source"], default="draft_note")

    # export
    export_p = subparsers.add_parser("export", help="Export review package to JSON")
    export_p.add_argument("--out", type=Path, default=REVIEWS_DIR / "workbench_export_latest.json")

    # import
    import_p = subparsers.add_parser("import", help="Import external review package JSON")
    import_p.add_argument("input_path", type=Path)

    # audit
    audit_p = subparsers.add_parser("audit", help="Show audit history for an item")
    audit_p.add_argument("item_id", help="Benchmark Item ID")

    # serve
    serve_p = subparsers.add_parser("serve", help="Launch local HTTP Workbench server")
    serve_p.add_argument("--port", type=int, default=8420)

    args = parser.parse_args()
    workbench = ReviewWorkbench()

    if args.subcommand == "list":
        items = workbench.get_all_items_summary(status_filter=args.status, group_filter=args.group)
        print(f"\nTotal items: {len(items)}")
        print(f"{'ITEM ID':<22} {'SPLIT':<8} {'STATUS':<16} {'TRANS':<6} {'EVID':<6} QUESTION")
        print("-" * 80)
        for it in items:
            print(f"{it['item_id']:<22} {it['split']:<8} {it['review_status']:<16} {it['transition_count']:<6} {it['evidence_count']:<6} {it['question'][:30]}...")

    elif args.subcommand == "view":
        detail = workbench.get_item_detail(args.item_id)
        print(f"\n=== [ITEM DETAIL] {detail['item_id']} ===")
        print(f"Status: {detail['review_status']} | Split: {detail['split']} | Group: {detail['group']}")
        print(f"\n[Question]\n{detail['question']}")
        print(f"\n[Proposed Answer]\n{detail['proposed_answer']}")
        print(f"\n[Evidence References ({len(detail['evidence_references'])} items)]")
        for ev in detail['evidence_references']:
            print(f" - {ev.get('title')} ({ev.get('evidence_id')}) | doc: {ev.get('document_id')} | prov: {ev.get('provision')}")
            print(f"   URL: {ev.get('source_url')}")
            print(f"   Excerpt: {ev.get('text_excerpt', '')[:100]}...")
        print(f"\n[Transition History ({len(detail['transition_history'])} entries)]")
        for t in detail['transition_history']:
            print(f" - {t['timestamp'][:19]} [{t['from_status']} -> {t['to_status']}] by {t['actor_id']}: {t.get('reason')}")

    elif args.subcommand == "draft":
        updated = workbench.record_draft_annotation(
            item_id=args.item_id,
            author=args.author,
            notes=args.notes,
            statutory_conflicts=args.conflicts,
            action_type=args.action,
        )
        print(f"Draft annotation recorded for {args.item_id} (status: {updated['review_status']})")

    elif args.subcommand == "export":
        res = workbench.export_review_package(args.out)
        print(f"Exported {res['total_items']} items to {res['output_path']}")

    elif args.subcommand == "import":
        res = workbench.import_review_package(args.input_path)
        print(f"Imported {res['imported_items']} items ({res['new_transitions']} new transitions)")

    elif args.subcommand == "audit":
        detail = workbench.get_item_detail(args.item_id)
        print(f"\nAudit History for {args.item_id}:")
        for t in detail["transition_history"]:
            print(f" - [{t['timestamp']}] {t['actor_id']} ({t['from_status']} -> {t['to_status']}): {t['reason']}")

    elif args.subcommand == "serve":
        run_workbench_server(args.port)


if __name__ == "__main__":
    main()
