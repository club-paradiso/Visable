"""Deterministic conflict detection between knowledge facts.

Two facts about the same slot (variant + property + item) with different
values are either:

* an **update candidate** — the new one cites a NEWER edition of the SAME
  source than the currently published one. That is the normal "new manual
  arrived" case; it goes to review as an update with a before/after diff; or
* a **conflict** — anything else (same edition disagreeing with itself, a
  different source disagreeing, an older edition contradicting the current
  one, overlapping effective windows). Conflicts are recorded, block
  publication of either side, and never resolve by "whichever row came first".

Equal values from different sources are corroboration, not a conflict.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .models import ConflictKind, authority_rank
from .store import new_id, utc_now

_ACTIVE_STATES = ("DRAFT", "AI_EXTRACTED", "HUMAN_REVIEW_REQUIRED", "HUMAN_REVIEWED", "VERIFIED", "PUBLISHED")


def version_sort_key(label: str) -> Tuple[int, ...]:
    """'2026.6' < '2026.9' < '2026.10' (numeric, not lexicographic)."""
    nums = [int(n) for n in re.findall(r"\d+", str(label or ""))]
    return tuple(nums) or (0,)


def value_signature(fact: Dict[str, Any]) -> Tuple[str, str, str]:
    value = fact.get("value_json") or {}
    return (
        " ".join(str(fact.get("value_text") or "").split()),
        str(fact.get("condition_kind") or "always"),
        str((value or {}).get("requirement_level") or ""),
    )


def _primary_citation(fact: Dict[str, Any]) -> Dict[str, Any]:
    cits = fact.get("citations") or []
    return cits[0] if cits else {}


def _windows_overlap(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    a_from, a_to = a.get("effective_from") or "0000-00-00", a.get("effective_to") or "9999-12-31"
    b_from, b_to = b.get("effective_from") or "0000-00-00", b.get("effective_to") or "9999-12-31"
    return a_from <= b_to and b_from <= a_to


def relation(new: Dict[str, Any], other: Dict[str, Any]) -> Optional[str]:
    """Classify how ``new`` relates to ``other`` for the same slot.

    Returns ``'corroborates'``, ``'update'`` or a :class:`ConflictKind` value,
    or ``None`` when the two cannot clash (disjoint explicit effective windows).
    """
    if value_signature(new) == value_signature(other):
        return "corroborates"
    if new.get("effective_from") and other.get("effective_from") and not _windows_overlap(new, other):
        return None
    c_new, c_other = _primary_citation(new), _primary_citation(other)
    same_source = c_new.get("source_key") and c_new.get("source_key") == c_other.get("source_key")
    if same_source:
        k_new, k_other = version_sort_key(c_new.get("version_label")), version_sort_key(c_other.get("version_label"))
        if c_new.get("source_version_id") == c_other.get("source_version_id"):
            return ConflictKind.VALUE_MISMATCH.value
        if k_new > k_other and other.get("lifecycle_state") in ("PUBLISHED", "SUPERSEDED"):
            return "update"
        if k_new < k_other:
            return ConflictKind.VERSION_CONTRADICTION.value
        return ConflictKind.VALUE_MISMATCH.value
    if new.get("effective_from") and other.get("effective_from"):
        return ConflictKind.TEMPORAL_OVERLAP.value
    if authority_rank(new.get("authority_type")) != authority_rank(other.get("authority_type")):
        return ConflictKind.AUTHORITY_CONTRADICTION.value
    return ConflictKind.VALUE_MISMATCH.value


def detect_for_fact(repo, fact_id: str) -> Dict[str, Any]:
    """Compare one fact against every active fact in its slot; persist conflicts.

    Returns ``{"conflicts": [...ids], "update_of": fact_id|None, "corroborates": [...]}``.
    Idempotent: a pair is recorded once (UNIQUE(fact_a, fact_b)).
    """
    fact = repo.get_fact(fact_id)
    others = repo.facts_where(
        "f.slot_key = ? AND f.fact_id <> ? AND f.lifecycle_state IN (%s)" % ",".join("?" * len(_ACTIVE_STATES)),
        (fact["slot_key"], fact_id, *_ACTIVE_STATES),
    )
    conflicts: List[str] = []
    update_of: Optional[str] = None
    corroborates: List[str] = []
    for other in others:
        # A fact explicitly superseding another is its successor, not a rival.
        if fact.get("supersedes_fact_id") == other["fact_id"] or other.get("supersedes_fact_id") == fact_id:
            continue
        rel = relation(fact, other)
        if rel is None:
            continue
        if rel == "corroborates":
            corroborates.append(other["fact_id"])
            continue
        if rel == "update":
            if other["lifecycle_state"] == "PUBLISHED":
                update_of = other["fact_id"]
            continue
        a, b = sorted((fact_id, other["fact_id"]))
        existing = repo.store.one(
            "SELECT conflict_id FROM knowledge_conflicts WHERE fact_a_id = ? AND fact_b_id = ?", (a, b))
        if existing:
            conflicts.append(existing["conflict_id"])
            continue
        conflict_id = new_id("kc")
        with repo.store.transaction():
            repo.store.execute(
                "INSERT INTO knowledge_conflicts(conflict_id, fact_a_id, fact_b_id, slot_key, conflict_kind,"
                " status, detected_at) VALUES (?,?,?,?,?,'open',?)",
                (conflict_id, a, b, fact["slot_key"], rel, utc_now()),
            )
            repo.store.audit(actor="conflict_detector", actor_kind="system", entity_type="conflict",
                             entity_id=conflict_id, action="detect",
                             after={"slot_key": fact["slot_key"], "kind": rel, "facts": [a, b]})
        conflicts.append(conflict_id)
    return {"conflicts": conflicts, "update_of": update_of, "corroborates": corroborates}


def open_conflicts_for(repo, fact_id: str) -> List[Dict[str, Any]]:
    return [dict(r) for r in repo.store.all(
        "SELECT * FROM knowledge_conflicts WHERE status = 'open' AND (fact_a_id = ? OR fact_b_id = ?)",
        (fact_id, fact_id))]


def open_conflicts_for_slots(repo, slots: List[str]) -> List[Dict[str, Any]]:
    if not slots:
        return []
    marks = ",".join("?" * len(slots))
    return [dict(r) for r in repo.store.all(
        f"SELECT * FROM knowledge_conflicts WHERE status = 'open' AND slot_key IN ({marks})", tuple(slots))]


def list_conflicts(repo, status: str = "open", limit: int = 200) -> List[Dict[str, Any]]:
    rows = [dict(r) for r in repo.store.all(
        "SELECT * FROM knowledge_conflicts WHERE status = ? ORDER BY detected_at DESC LIMIT ?",
        (status, int(limit)))]
    for row in rows:
        row["fact_a"] = _brief(repo, row["fact_a_id"])
        row["fact_b"] = _brief(repo, row["fact_b_id"])
    return rows


def _brief(repo, fact_id: str) -> Dict[str, Any]:
    fact = repo.get_fact(fact_id)
    cit = _primary_citation(fact)
    return {
        "fact_id": fact_id, "value_text": fact["value_text"], "condition_kind": fact["condition_kind"],
        "lifecycle_state": fact["lifecycle_state"], "authority_type": fact["authority_type"],
        "source": {"title": cit.get("source_title"), "version": cit.get("version_label"),
                   "pages": _pages(cit)},
    }


def _pages(cit: Dict[str, Any]) -> str:
    if not cit.get("page_start"):
        return ""
    if cit.get("page_end") and cit["page_end"] != cit["page_start"]:
        return f"{cit['page_start']}-{cit['page_end']}"
    return str(cit["page_start"])
