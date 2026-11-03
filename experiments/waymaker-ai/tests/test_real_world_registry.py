"""DEV-20 real-world registry: owner-reviewed drafts and the registry built only from owner decisions.

Claude drafts records from each evidence item's own source fields; only the owner's decision in the
review sheet makes a record verified and approved. These tests use fake decisions to check the
mechanics; they approve nothing real and write no registry file.
"""
import json
import sys
from pathlib import Path

import pytest

BOOT = Path(__file__).resolve().parents[1] / "artemis_bootstrap"
sys.path.insert(0, str(BOOT))
import real_world_registry as rwr
from waymaker_ai.evidence_admissibility import select_admissible_evidence
from waymaker_ai.evidence_registry import content_sha256, load_real_world_registry

ITEMS = rwr.dev20_items()
EVIDENCE = rwr.evidence_items(ITEMS)


def decide(action_for):
    return {eid: {"decision": action_for(eid), "decided_at": "2026-11-03T10:00:00Z"} for eid in EVIDENCE}


def test_every_dev20_evidence_item_has_one_proposal():
    assert len(EVIDENCE) == 23 and set(EVIDENCE) == set(rwr.PROPOSALS)
    no_record = sorted(e for e, p in rwr.PROPOSALS.items() if p["action"] == "no_record")
    assert no_record == ["EV-DEV-007-OLD", "EV-DEV-013-PROBE", "EV-DEV-014-PROBE", "EV-DEV-019-BLOG", "EV-DEV-020-CHAT"]


def test_the_committed_drafts_are_what_the_module_builds_and_are_pending():
    committed = json.loads(rwr.DRAFTS.read_text())
    pages = {d["evidence_id"]: [{"book": p["book"], "page": p["page"]} for p in d["manual_pages"]] for d in committed["drafts"]}
    rebuilt = rwr.build_drafts({eid: [{**p, "hits": [], "excerpt": ""} for p in ps] for eid, ps in pages.items()})
    assert rebuilt == committed and committed["status"] == "pending_owner_review"
    assert all(d["content_sha256"] == content_sha256(EVIDENCE[d["evidence_id"]]["evidence"]["text"]) for d in committed["drafts"])


DECISIONS = BOOT / "registry" / "dev20_decisions.json"


def test_the_committed_registry_is_built_from_the_committed_decisions():
    decisions = json.loads(DECISIONS.read_text())
    assert json.loads(rwr.REGISTRY.read_text()) == rwr.build_registry(decisions)


def test_the_decisions_name_who_decided_on_what_authority_and_by_which_rule():
    meta = json.loads(DECISIONS.read_text())["_meta"]
    assert meta["decided_by"] == "Claude (rule-based check) under owner delegation"
    assert "너가 알아서 해줘" in meta["delegation"] and "not a legal review" in meta["rule"]
    registry = json.loads(rwr.REGISTRY.read_text())
    assert registry["decided_by"] == meta["decided_by"]
    assert all(r["decision_provenance"] == meta["provenance"] for r in registry["records"].values())
    assert all(d.get("basis") for k, d in json.loads(DECISIONS.read_text()).items() if k != "_meta")


def test_items_that_contradict_current_text_are_rejected_and_unchecked_ones_left_out():
    registry = json.loads(rwr.REGISTRY.read_text())["records"]
    rejected = sorted(e for e, r in registry.items() if r["verification"]["result"] == "rejected")
    approved = sorted(e for e, r in registry.items() if r["verification"]["result"] == "verified")
    assert rejected == ["EV-DEV-001-A", "EV-DEV-005-A", "EV-DEV-011-A", "EV-DEV-017-A", "EV-DEV-020-OFFICIAL"]
    assert len(approved) == 10 and "EV-DEV-007-CURRENT" not in registry and "EV-DEV-009-A" not in registry
    assert registry["EV-DEV-002-A"]["source_locator"] == "출입국관리법 제9조(사증발급인정서)"


def test_the_registry_refuses_missing_or_unknown_decisions():
    decisions = decide(lambda e: "no_record")
    decisions.pop("EV-DEV-001-A")
    with pytest.raises(ValueError, match="no owner decision"):
        rwr.build_registry(decisions)
    with pytest.raises(ValueError, match="bad decision"):
        rwr.build_registry({**decide(lambda e: "no_record"), "EV-DEV-001-A": {"decision": "maybe", "decided_at": "x"}})
    with pytest.raises(ValueError, match="no decision time"):
        rwr.build_registry({**decide(lambda e: "no_record"), "EV-DEV-001-A": {"decision": "approve"}})


def test_approve_reject_and_no_record_map_to_the_spec_rules(tmp_path):
    plan = {"EV-DEV-012-A": "approve", "EV-DEV-005-A": "reject"}
    reg = rwr.build_registry(decide(lambda e: plan.get(e, "no_record")))
    assert set(reg["records"]) == {"EV-DEV-012-A", "EV-DEV-005-A"}
    approved, rejected = reg["records"]["EV-DEV-012-A"], reg["records"]["EV-DEV-005-A"]
    assert approved["verification"] == {"method": "authorized_review", "verified_at": "2026-11-03T10:00:00Z", "result": "verified"}
    assert approved["review_state"] == "approved" and rejected["verification"]["result"] == "rejected"
    path = tmp_path / "real_world_registry.json"
    path.write_text(json.dumps(reg, ensure_ascii=False))
    registry = load_real_world_registry(path)
    by_id = {i["id"]: i for i in ITEMS}
    sel = select_admissible_evidence(by_id["ARTEMIS-004-DEV-012"]["question"], None, by_id["ARTEMIS-004-DEV-012"]["evidence"],
                                     registry, rwr.EVALUATION_DATE)
    assert sel["outcome"] == "proceed" and [e["id"] for e in sel["admissible"]] == ["EV-DEV-012-A"]
    sel = select_admissible_evidence(by_id["ARTEMIS-004-DEV-005"]["question"], None, by_id["ARTEMIS-004-DEV-005"]["evidence"],
                                     registry, rwr.EVALUATION_DATE)
    assert [d["reason"] for d in sel["decisions"]] == ["verification_rejected"]
    sel = select_admissible_evidence(by_id["ARTEMIS-004-DEV-019"]["question"], None, by_id["ARTEMIS-004-DEV-019"]["evidence"],
                                     registry, rwr.EVALUATION_DATE)
    assert {d["reason"] for d in sel["decisions"]} == {"no_registry_record"}


def test_rejecting_an_item_without_a_draft_gives_a_rejected_record():
    reg = rwr.build_registry({**decide(lambda e: "no_record"),
                              "EV-DEV-019-BLOG": {"decision": "reject", "decided_at": "2026-11-03T10:00:00Z"}})
    rec = reg["records"]["EV-DEV-019-BLOG"]
    assert rec["verification"]["result"] == "rejected" and rec["document_type"] == "unknown" and rec["effective_from"] is None


def test_the_owner_may_change_scope_fields_before_approving():
    fields = {"status_scope": ["D-2"], "procedures": ["registration", "change"], "effective_from": "2026-01-01",
              "authority": "unofficial", "review_state": "pending"}   # the last two are not reviewer fields and are ignored
    reg = rwr.build_registry({**decide(lambda e: "no_record"),
                              "EV-DEV-006-A": {"decision": "approve", "decided_at": "2026-11-03T10:00:00Z", "fields": fields}})
    rec = reg["records"]["EV-DEV-006-A"]
    assert rec["status_scope"] == ["D-2"] and rec["authority"] == "official" and rec["review_state"] == "approved"
    preview = rwr.admission_preview(ITEMS, reg["records"])
    assert preview["ARTEMIS-004-DEV-006"]["decisions"]["EV-DEV-006-A"] == ["admissible", "admissible"]


def test_the_preview_shows_which_questions_drafts_would_not_serve():
    preview = json.loads(rwr.DRAFTS.read_text())["items_preview_if_all_candidates_approved"]
    withheld = sorted(i for i, p in preview.items() if p["outcome"] != "proceed")
    assert withheld == ["ARTEMIS-004-DEV-002", "ARTEMIS-004-DEV-006", "ARTEMIS-004-DEV-010",
                        "ARTEMIS-004-DEV-013", "ARTEMIS-004-DEV-014"]
