"""Deterministic source-version diff over normalized facts.

Compares the facts that cite edition A with the facts that cite edition B of
the same source, slot by slot:

    ADDED      slot only in B
    REMOVED    slot only in A
    CHANGED    both, different value — with the changed fields named
               (requirement_level / condition / wording), so a wording-only
               change is distinguishable from a changed requirement
    UNCHANGED  both, same normalized value

No model is involved. An LLM may later *explain* a CHANGED record to a
reviewer; it never decides whether two facts are equivalent.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .conflicts import value_signature
from .models import ChangeKind, KnowledgeError, PipelineError

_ANY_STATE = ("DRAFT", "AI_EXTRACTED", "HUMAN_REVIEW_REQUIRED", "HUMAN_REVIEWED", "VERIFIED",
              "PUBLISHED", "SUPERSEDED")


def _facts_citing(repo, source_version_id: str, *, status_code: Optional[str], procedure: Optional[str],
                  properties: Optional[List[str]]) -> Dict[str, Dict[str, Any]]:
    where = ["c.source_version_id = ?", "f.lifecycle_state IN (%s)" % ",".join("?" * len(_ANY_STATE))]
    params: List[Any] = [source_version_id, *_ANY_STATE]
    if status_code:
        where.append("v.status_code = ?")
        params.append(status_code)
    if procedure:
        where.append("v.procedure = ?")
        params.append(procedure)
    if properties:
        where.append("f.property IN (%s)" % ",".join("?" * len(properties)))
        params.extend(properties)
    rows = repo.facts_where(
        "f.fact_id IN (SELECT c.fact_id FROM fact_citations c JOIN knowledge_facts f USING(fact_id)"
        " JOIN procedure_variants v USING(variant_id) WHERE " + " AND ".join(where) + ")",
        params, limit=5000, with_citations=False)
    by_slot: Dict[str, Dict[str, Any]] = {}
    for fact in rows:
        # Prefer the published / most-reviewed representative of a slot.
        current = by_slot.get(fact["slot_key"])
        if current is None or _rank(fact) < _rank(current):
            by_slot[fact["slot_key"]] = fact
    return by_slot


def _rank(fact: Dict[str, Any]) -> int:
    order = ["PUBLISHED", "VERIFIED", "HUMAN_REVIEWED", "SUPERSEDED", "HUMAN_REVIEW_REQUIRED",
             "AI_EXTRACTED", "DRAFT"]
    return order.index(fact["lifecycle_state"]) if fact["lifecycle_state"] in order else 99


def changed_fields(a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
    wa, ca, la = value_signature(a)
    wb, cb, lb = value_signature(b)
    out = []
    if la != lb:
        out.append("requirement_level")
    if ca != cb or (a.get("condition_text") or "") != (b.get("condition_text") or ""):
        out.append("condition")
    if wa != wb:
        out.append("wording")
    return out


def diff_versions(repo, from_version_id: str, to_version_id: str, *, status_code: Optional[str] = None,
                  procedure: Optional[str] = None, properties: Optional[List[str]] = None,
                  include_unchanged: bool = True) -> Dict[str, Any]:
    va, vb = repo.get_source_version(from_version_id), repo.get_source_version(to_version_id)
    if not va or not vb:
        raise KnowledgeError(PipelineError.NOT_FOUND, "source version not found")
    if va["source_id"] != vb["source_id"]:
        raise KnowledgeError(PipelineError.SOURCE_LOCATION_INVALID,
                             "diff compares two editions of the SAME source; these are different sources")
    a = _facts_citing(repo, from_version_id, status_code=status_code, procedure=procedure, properties=properties)
    b = _facts_citing(repo, to_version_id, status_code=status_code, procedure=procedure, properties=properties)
    records: List[Dict[str, Any]] = []
    for slot in sorted(set(a) | set(b)):
        fa, fb = a.get(slot), b.get(slot)
        if fa and not fb:
            kind, fields = ChangeKind.REMOVED, []
        elif fb and not fa:
            kind, fields = ChangeKind.ADDED, []
        else:
            fields = changed_fields(fa, fb)
            kind = ChangeKind.CHANGED if fields else ChangeKind.UNCHANGED
        if kind == ChangeKind.UNCHANGED and not include_unchanged:
            continue
        ref = fb or fa
        records.append({
            "change": kind.value,
            "slot_key": slot,
            "status_code": ref["status_code"], "subcode": ref.get("subcode"), "procedure": ref["procedure"],
            "property": ref["property"],
            "changed_fields": fields,
            "needs_review": kind != ChangeKind.UNCHANGED,
            "from": _view(fa), "to": _view(fb),
            "affected_eval_cases": [r["case_key"] for r in repo.store.all(
                "SELECT c.case_key FROM eval_case_dependencies d JOIN eval_cases c USING(case_id)"
                " WHERE d.slot_key = ?", (slot,))],
        })
    summary: Dict[str, int] = {k.value: 0 for k in ChangeKind}
    for rec in records:
        summary[rec["change"]] += 1
    return {
        "source_key": va["source_key"],
        "from": {"source_version_id": from_version_id, "edition": va["edition_ref"], "version": va["version_label"]},
        "to": {"source_version_id": to_version_id, "edition": vb["edition_ref"], "version": vb["version_label"]},
        "filters": {"status_code": status_code, "procedure": procedure, "properties": properties},
        "summary": summary,
        "records": records,
    }


def _view(fact: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not fact:
        return None
    return {
        "fact_id": fact["fact_id"],
        "value_text": fact["value_text"],
        "requirement_level": (fact.get("value_json") or {}).get("requirement_level"),
        "condition_kind": fact["condition_kind"],
        "condition_text": fact.get("condition_text") or "",
        "lifecycle_state": fact["lifecycle_state"],
    }


def fact_version_history(repo, lineage_id: str) -> List[Dict[str, Any]]:
    return repo.facts_where("f.lineage_id = ?", (lineage_id,), order="f.version_no, f.created_at")
