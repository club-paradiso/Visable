"""Waymaker Knowledge Platform — invariants and acceptance paths.

Every test runs against a fresh in-memory knowledge store seeded from the
committed repository data (the same bootstrap production runs), so no test
depends on — or changes — a developer's local knowledge database.

Acceptance paths covered (task spec section in brackets):
  D-2 verified retrieval [43], unknown query -> deduplicated gap [44],
  missing user fact != knowledge gap [45], conflicting proposals [46],
  operator-created fact end-to-end [85], rejected extraction [86],
  superseded fact + as-of history [87], model outage [88], bad model output [89],
  source-version diff [77], operator workflow over the authenticated API [76].
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import unittest
from typing import Any, Dict, List
from unittest.mock import patch

os.environ.setdefault("WAYMAKER_KNOWLEDGE_DB", ":memory:")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import paradiso_backend as pb  # noqa: E402
from services import structured_answer as sa  # noqa: E402
from services.knowledge import adapters, guard, lifecycle, privacy  # noqa: E402
from services.knowledge.diff import diff_versions  # noqa: E402
from services.knowledge.models import (  # noqa: E402
    EvalCaseIn,
    FeedbackIn,
    KnowledgeError,
    LifecycleState,
    ReviewAction,
    ReviewActionRequest,
)
from services.knowledge.runtime import KnowledgePlatform, get_platform, set_platform_for_tests  # noqa: E402
from services.knowledge.store import KnowledgeStore  # noqa: E402

OPERATOR = "reviewer-alice"
TOKEN = "alice-operator-token-0123456789"
VENDOR_TERMS = ("openrouter", "groq", "ollama", "nemotron", "gemma", "nvidia")
INTERNAL_TERMS = ("fact_id", "lineage_id", "slot_key", "proposal_hash", "verification_note", "artifact_ref",
                  "reviewed_by", "verified_by", "source_file", "kl_", "coverage_state")


def _provider_ok(answer: str, candidates: List[str]) -> Dict[str, Any]:
    model = candidates[0]
    return {
        "ok": True, "answer": answer, "primary_model": model, "requested_model": None,
        "model_candidates": list(candidates), "attempted_models": [model],
        "skipped_models_due_to_cooldown": [], "cooling_down_models": [],
        "model_cooldown_seconds": 0, "cooldown_enabled": False, "final_model": model,
        "model_fallback_used": False, "provider_error_type": None, "upstream_statuses": [],
        "retryable_provider_error": False, "all_candidates_failed": False,
    }


class PlatformCase(unittest.TestCase):
    """Fresh seeded platform per test, installed as the runtime singleton."""

    def setUp(self):
        self._previous = get_platform()
        self.p = KnowledgePlatform.create(":memory:")
        set_platform_for_tests(self.p)

    def tearDown(self):
        set_platform_for_tests(self._previous)

    # helpers ---------------------------------------------------------------
    def version(self, edition: str) -> str:
        return self.p.repo.find_source_version("stay_guide_manual", edition)["source_version_id"]

    def proposal(self, **over) -> Dict[str, Any]:
        base = {
            "status_code": "H-2", "procedure": "extension", "property": "required_document",
            "value_text": "여권", "requirement_level": "common", "origin": "operator_manual",
            "section_title": "방문취업(H-2) 체류기간 연장허가",
            "location": {"source_version_id": self.version("stay_manual_2026_09_18_pdf"),
                         "page_start": 540, "page_end": 540, "locator": "제출서류"},
        }
        base.update(over)
        return base

    def apply(self, proposals, actor=OPERATOR, kind="human_operator"):
        return self.p.ingestion.run("test", proposals, mode="apply", actor=actor, actor_kind=kind)

    def act(self, fact_id, action, reason="checked against the cited page", **kw):
        return self.p.review.act(fact_id, ReviewActionRequest(action=action, reason=reason, **kw), actor=OPERATOR)

    def publish_path(self, fact_id):
        self.act(fact_id, ReviewAction.APPROVE)
        self.act(fact_id, ReviewAction.VERIFY)
        return self.act(fact_id, ReviewAction.PUBLISH)

    def ask(self, question, answer_text="", *, lang="ko", diagnostics=False, **extra):
        async def fake(prompt, requested_model=None, candidate_models=None, max_tokens=None, **kw):
            return _provider_ok(answer_text, list(candidate_models or ["test/model"]))
        headers = {"X-Paradiso-Diagnostics": "1"} if diagnostics else {}
        with patch.object(pb, "OPENROUTER_API_KEY", "sk-test-sentinel"), \
                patch.object(pb, "_openrouter_complete_with_candidates", fake):
            return TestClient(pb.app, headers=headers).post("/api/ask", json={
                "question": question, "consent": True, "lang": lang, "answer_mode": "fast",
                "stream": False, **extra})


# =============================================================================
# Schema, lifecycle and database-level invariants
# =============================================================================
class SchemaAndLifecycleTests(PlatformCase):
    def test_migrations_are_idempotent_and_immutable(self):
        store = self.p.store
        self.assertEqual(store.apply_migrations(), [])
        store.execute("UPDATE schema_migrations SET checksum = 'tampered'")
        with self.assertRaises(RuntimeError):
            store.apply_migrations()

    def test_db_transition_whitelist_matches_the_python_rules(self):
        rows = {(r["from_state"], r["to_state"]) for r in self.p.store.all("SELECT * FROM lifecycle_transitions")}
        self.assertEqual(rows, set(lifecycle.transition_pairs()))

    def test_ai_extraction_cannot_jump_to_published_even_with_raw_sql(self):
        rep = self.apply([self.proposal(origin="ai_extraction",
                                        location={"source_version_id": self.version("stay_manual_2026_09_18_pdf"),
                                                  "page_start": 540, "evidence_excerpt": "여권"})],
                         actor="extractor", kind="ai_extractor")
        fact_id = rep.items[0].fact_id
        self.assertEqual(self.p.repo.get_fact(fact_id)["lifecycle_state"], "AI_EXTRACTED")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "LIFECYCLE_TRANSITION_FORBIDDEN"):
            self.p.store.execute("UPDATE knowledge_facts SET lifecycle_state='PUBLISHED' WHERE fact_id=?", (fact_id,))
        with self.assertRaises(KnowledgeError):
            lifecycle.assert_transition("AI_EXTRACTED", "PUBLISHED", "human_operator")

    def test_facts_can_only_be_inserted_as_proposals(self):
        sql = self.p.store.one("SELECT sql FROM sqlite_master WHERE name='trg_facts_insert_only_proposals'")
        self.assertIn("LIFECYCLE_INSERT_MUST_BE_PROPOSAL", sql[0])
        with self.assertRaisesRegex(sqlite3.IntegrityError, "LIFECYCLE_INSERT_MUST_BE_PROPOSAL"):
            self.p.store.execute(
                "INSERT INTO knowledge_facts(fact_id, lineage_id, variant_id, property, item_key, slot_key, value_text,"
                " authority_type, origin, lifecycle_state, created_by, created_by_kind, created_at, proposal_hash)"
                " SELECT 'kf_x','kl_x', variant_id, 'required_document','x','x','x','approved_manual',"
                " 'operator_manual','PUBLISHED','x','human_operator','2026','hash-x' FROM procedure_variants LIMIT 1")

    def test_ai_actor_can_never_review_and_legacy_actor_cannot_launder(self):
        with self.assertRaises(KnowledgeError):
            lifecycle.assert_transition("HUMAN_REVIEW_REQUIRED", "HUMAN_REVIEWED", "ai_extractor")
        with self.assertRaises(KnowledgeError):
            lifecycle.assert_transition("VERIFIED", "PUBLISHED", "system")
        rep = self.apply([self.proposal(origin="parser_extraction")], actor="parser", kind="parser")
        with self.assertRaisesRegex(KnowledgeError, "legacy import may only review"):
            self.p.repo.transition(rep.items[0].fact_id, LifecycleState.HUMAN_REVIEWED,
                                   actor="legacy:x", actor_kind="legacy_import")

    def test_publish_requires_provenance_at_the_database(self):
        rep = self.apply([self.proposal()])
        fact_id = rep.items[0].fact_id
        self.act(fact_id, ReviewAction.APPROVE)
        self.act(fact_id, ReviewAction.VERIFY)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "REVIEWED_PROVENANCE_IMMUTABLE"):
            self.p.store.execute("DELETE FROM fact_citations WHERE fact_id = ?", (fact_id,))
        # A proposal whose citation was removed before review cannot be published.
        rep2 = self.apply([self.proposal(value_text="외국인등록증")])
        fid2 = rep2.items[0].fact_id
        self.p.store.execute("DELETE FROM fact_citations WHERE fact_id = ?", (fid2,))
        self.act(fid2, ReviewAction.APPROVE)
        self.act(fid2, ReviewAction.VERIFY)
        with self.assertRaises((KnowledgeError, sqlite3.IntegrityError)):
            self.act(fid2, ReviewAction.PUBLISH)
        self.assertEqual(self.p.repo.get_fact(fid2)["lifecycle_state"], "VERIFIED")

    def test_reviewed_content_is_immutable_and_audit_is_append_only(self):
        d2 = self.p.repo.facts_where("v.status_code='D-2' AND f.lifecycle_state='PUBLISHED'")[0]
        with self.assertRaisesRegex(sqlite3.IntegrityError, "REVIEWED_FACT_IMMUTABLE"):
            self.p.store.execute("UPDATE knowledge_facts SET value_text='x' WHERE fact_id=?", (d2["fact_id"],))
        with self.assertRaisesRegex(sqlite3.IntegrityError, "REVIEWED_FACT_NOT_DELETABLE"):
            self.p.store.execute("DELETE FROM knowledge_facts WHERE fact_id=?", (d2["fact_id"],))
        with self.assertRaisesRegex(sqlite3.IntegrityError, "AUDIT_LOG_APPEND_ONLY"):
            self.p.store.execute("UPDATE audit_log SET actor='x'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "AUDIT_LOG_APPEND_ONLY"):
            self.p.store.execute("DELETE FROM audit_log")

    def test_every_published_fact_has_provenance_and_a_reviewer_of_record(self):
        for fact in self.p.repo.facts_where("f.lifecycle_state='PUBLISHED'"):
            self.assertTrue(fact["citations"], fact["fact_id"])
            self.assertTrue(fact["verified_by"] and fact["verified_at"] and fact["published_at"])
            self.assertIn(fact["reviewer_kind"], ("human_operator", "legacy_repository_verification"))

    def test_legacy_seed_is_labelled_as_repository_verification_not_studio_review(self):
        seeded = self.p.repo.facts_where("f.lifecycle_state='PUBLISHED'")
        self.assertEqual(len(seeded), 42)
        self.assertTrue(all(f["reviewer_kind"] == "legacy_repository_verification" for f in seeded))
        self.assertTrue(all(f["origin"] == "legacy_repository_verified" for f in seeded))

    def test_file_store_falls_back_to_memory_when_unwritable(self):
        store = KnowledgeStore("/proc/definitely/not/writable/knowledge.sqlite3")
        self.assertFalse(store.durable)
        self.assertEqual(store.schema_version(), "0001_knowledge_foundation")


# =============================================================================
# Ingestion: idempotency, dry-run, validation, source versions
# =============================================================================
class IngestionTests(PlatformCase):
    def test_bootstrap_is_idempotent(self):
        before = (self.p.repo.state_counts(), self.p.store.one("SELECT COUNT(*) FROM source_versions")[0])
        again = adapters.bootstrap(self.p.repo)
        self.assertEqual(again["seed"]["published"], 0)
        self.assertEqual(again["registry"]["created"], 0)
        after = (self.p.repo.state_counts(), self.p.store.one("SELECT COUNT(*) FROM source_versions")[0])
        self.assertEqual(before, after)

    def test_reimporting_the_same_edition_creates_no_duplicates(self):
        props = adapters.status_guidance_proposals(self.p.repo, statuses=["D-2", "E-7"])
        first = self.p.ingestion.run("sg", props, mode="apply", actor="parser:sg", actor_kind="parser")
        tasks = self.p.store.one("SELECT COUNT(*) FROM review_tasks")[0]
        facts = self.p.store.one("SELECT COUNT(*) FROM knowledge_facts")[0]
        second = self.p.ingestion.run("sg", props, mode="apply", actor="parser:sg", actor_kind="parser")
        self.assertNotIn("duplicate", first.summary)
        self.assertEqual(second.summary, {"duplicate": len(props)})
        self.assertEqual(self.p.store.one("SELECT COUNT(*) FROM review_tasks")[0], tasks)
        self.assertEqual(self.p.store.one("SELECT COUNT(*) FROM knowledge_facts")[0], facts)

    def test_dry_run_and_validate_write_nothing(self):
        props = adapters.status_guidance_proposals(self.p.repo, statuses=["D-2"])
        revision = self.p.store.revision()
        dry = self.p.ingestion.run("sg", props, mode="dry_run")
        self.p.ingestion.run("sg", props, mode="validate")
        self.assertEqual(self.p.store.revision(), revision)
        self.assertEqual(dry.summary, {"reconfirm": 4, "update": 4})

    def test_validation_rejects_bad_proposals_with_stable_codes(self):
        v26 = self.version("stay_manual_2026_09_18_pdf")
        visa = self.p.repo.find_source_version("visa_issuance_manual", "visa_manual_2026_09_01_pdf")["source_version_id"]
        cases = {
            "UNSUPPORTED_STATUS": self.proposal(status_code="Z-9"),
            "UNKNOWN_PROCEDURE": self.proposal(procedure="teleportation"),
            "SOURCE_LOCATION_INVALID": self.proposal(location={"source_version_id": v26, "page_start": 99999}),
            "PROCEDURE_SCOPE_MISMATCH": self.proposal(location={"source_version_id": visa, "page_start": 10}),
            "EXTRACTION_INVALID": self.proposal(origin="ai_extraction"),
            "MALFORMED_VALUE": self.proposal(value_text="<script>alert(1)</script>"),
        }
        for code, prop in cases.items():
            with self.subTest(code=code):
                rep = self.p.ingestion.run("t", [prop], mode="apply", actor=OPERATOR)
                self.assertEqual(rep.items[0].action, "invalid")
                self.assertIn(code, [e["code"] for e in rep.items[0].errors])
        bad_sub = self.proposal(status_code="D-2", subcode="E-7-4")
        rep = self.p.ingestion.run("t", [bad_sub], mode="dry_run")
        self.assertEqual(rep.items[0].action, "invalid")
        missing_source = self.proposal(location={"source_version_id": "srv_nope", "page_start": 1})
        self.assertEqual(self.p.ingestion.run("t", [missing_source], mode="dry_run").items[0].action, "invalid")

    def test_source_versions_keep_identity_lineage_and_state(self):
        stay = [s for s in self.p.repo.list_sources() if s["source_key"] == "stay_guide_manual"][0]
        by_ref = {v["edition_ref"]: v for v in stay["versions"]}
        self.assertEqual(by_ref["stay_manual_2026_07_31_hwp"]["status"], "active")
        self.assertEqual(by_ref["stay_manual_2026_07_31_hwp"]["content_review_state"], "approved")
        self.assertEqual(by_ref["stay_manual_2026_07_31_hwp"]["effective_from"], "2026-07-31")
        self.assertEqual(by_ref["stay_manual_2026_06_23_pdf"]["status"], "superseded")
        self.assertEqual(by_ref["stay_manual_2026_09_18_pdf"]["status"], "staged")
        # Effective dates come only from the approval record; absent = unknown (NULL), never invented.
        approvals = json.load(open(adapters.APPROVAL_INDEX_PATH, encoding="utf-8"))["documents"]
        for ref, version in by_ref.items():
            self.assertEqual(version["effective_from"], (approvals.get(ref) or {}).get("effective_date") or None, ref)
        succ = by_ref["stay_manual_2026_07_31_hwp"]
        self.assertEqual(succ["supersedes_version_id"], by_ref["stay_manual_2026_06_23_pdf"]["source_version_id"])
        # Facts cite a superseded edition while an approved newer one exists.
        self.assertEqual(stay["refresh_state"], "refresh_due")


# =============================================================================
# Review workflow + acceptance cases 85 / 86 / 87
# =============================================================================
class ReviewWorkflowTests(PlatformCase):
    def test_operator_created_fact_end_to_end(self):
        """[85] operator fact -> review -> verify -> publish -> retrieve -> eval."""
        rep = self.apply([self.proposal(value_text="여권", sort_order=0),
                          self.proposal(value_text="외국인등록증", sort_order=1),
                          self.proposal(value_text="고용보험 가입내역 (해당자)", requirement_level="conditional",
                                        condition_kind="conditional", sort_order=2)])
        self.assertEqual(rep.summary, {"add": 3})
        ids = [i.fact_id for i in rep.items]
        for fid in ids:
            self.assertEqual(self.p.repo.get_fact(fid)["lifecycle_state"], "HUMAN_REVIEW_REQUIRED")
            self.publish_path(fid)
        plan = self.p.plan("H-2 체류기간 연장 필요 서류")
        self.assertEqual(plan.decision.state, "VERIFIED_WITH_CONDITIONS")
        self.assertIsNone(plan.decision.gap_reason)
        self.assertEqual([f["value_text"] for f in plan.retrieval.document_facts][:2], ["여권", "외국인등록증"])
        fact = self.p.repo.get_fact(ids[0])
        self.assertEqual(fact["reviewer_kind"], "human_operator")
        self.assertEqual(fact["verified_by"], OPERATOR)
        cit = fact["citations"][0]
        self.assertEqual((cit["version_label"], cit["page_start"]), ("2026.9", 540))
        actions = [a["action"] for a in self.p.repo.audit_trail("fact", ids[0])]
        self.assertEqual(actions, ["propose", "transition:HUMAN_REVIEWED", "transition:VERIFIED", "transition:PUBLISHED"])
        self.p.evals.create_case(EvalCaseIn(case_key="h2.extension.operator", query="H-2 체류기간 연장 필요 서류",
                                            assertions=[{"type": "MUST_INCLUDE_FACT", "value": "외국인등록증"},
                                                        {"type": "EXPECTED_BUCKET", "value": {"item": "고용보험", "bucket": "conditional"}},
                                                        {"type": "SOURCE_MUST_BE", "value": {"edition": "2026.9"}}]),
                                 actor=OPERATOR, state="approved")
        run = self.p.evals.run(selector="h2.extension.operator")
        self.assertEqual((run["total"], run["passed"]), (1, 1), run)

    def test_rejected_extraction_never_becomes_authoritative(self):
        """[86]"""
        rep = self.apply([self.proposal(origin="ai_extraction", value_text="건강진단서",
                                        location={"source_version_id": self.version("stay_manual_2026_09_18_pdf"),
                                                  "page_start": 540, "evidence_excerpt": "건강진단서"})],
                         actor="extractor", kind="ai_extractor")
        fid = rep.items[0].fact_id
        self.act(fid, ReviewAction.START_REVIEW)
        self.act(fid, ReviewAction.REJECT, reason="not on the cited page")
        self.assertEqual(self.p.repo.get_fact(fid)["lifecycle_state"], "REJECTED")
        plan = self.p.plan("H-2 체류기간 연장 필요 서류")
        self.assertNotIn(fid, plan.retrieval.fact_ids if plan.retrieval else [])
        self.assertEqual(plan.decision.state, "NO_DIRECT_SOURCE")
        trail = self.p.repo.audit_trail("fact", fid)
        self.assertEqual(trail[-1]["action"], "transition:REJECTED")
        self.assertEqual(trail[-1]["reason"], "not on the cited page")
        with self.assertRaises(KnowledgeError):
            self.act(fid, ReviewAction.APPROVE)
        with self.assertRaises(KnowledgeError):
            self.p.review.reject(fid, actor=OPERATOR, reason="")

    def test_superseded_fact_current_vs_historical(self):
        """[87] 2026.9 update for D-2 재정입증 서류 supersedes the 2026.6 fact."""
        props = adapters.status_guidance_proposals(self.p.repo, statuses=["D-2"])
        self.p.ingestion.run("sg", props, mode="apply", actor="parser:sg", actor_kind="parser")
        task = [t for t in self.p.review.queue() if t["value_text"] == "재정입증 서류"][0]
        self.assertEqual(task["task_kind"], "update_fact")
        detail = self.p.review.task_detail(task["task_id"])
        self.assertEqual(detail["diff"]["current"]["requirement_level"], "required")
        self.assertEqual(detail["diff"]["proposed"]["requirement_level"], "conditional")
        self.assertIn("requirement_level", detail["diff"]["changed_fields"])
        old_id = detail["current_published"]["fact_id"]
        new_fact = self.publish_path(task["fact_id"])
        old = self.p.repo.get_fact(old_id)
        self.assertEqual(old["lifecycle_state"], "SUPERSEDED")
        self.assertEqual(old["superseded_by_fact_id"], new_fact["fact_id"])
        self.assertEqual(new_fact["supersedes_fact_id"], old_id)
        self.assertEqual(new_fact["lineage_id"], old["lineage_id"])
        self.assertEqual(new_fact["version_no"], old["version_no"] + 1)
        current = self.p.retrieval.retrieve(status_code="D-2", procedure="extension", intent="required_documents")
        finance = [f for f in current.document_facts if f["item_key"] == "재정입증서류"]
        self.assertEqual([f["fact_id"] for f in finance], [new_fact["fact_id"]])
        # As-of a moment between the two publications: the old fact is the answer.
        self.p.store.execute("UPDATE knowledge_facts SET published_at='2026-01-01T00:00:00Z' WHERE fact_id=?", (old_id,))
        self.p.store.execute("UPDATE knowledge_facts SET superseded_at='2026-05-01T00:00:00Z' WHERE fact_id=?", (old_id,))
        self.p.store.execute("UPDATE knowledge_facts SET published_at='2026-05-01T00:00:00Z' WHERE fact_id=?",
                             (new_fact["fact_id"],))
        self.p.retrieval.clear_cache()
        past = self.p.retrieval.retrieve(status_code="D-2", procedure="extension", intent="required_documents",
                                         as_of="2026-03-01")
        self.assertEqual([f["fact_id"] for f in past.document_facts if f["item_key"] == "재정입증서류"], [old_id])
        self.assertEqual(past.temporal_basis, "knowledge_window")

    def test_publish_is_transactional(self):
        props = [p for p in adapters.status_guidance_proposals(self.p.repo, statuses=["D-2"])
                 if p["value_text"] == "재정입증 서류"]
        rep = self.p.ingestion.run("sg", props, mode="apply", actor="parser:sg", actor_kind="parser")
        fid = rep.items[0].fact_id
        self.act(fid, ReviewAction.APPROVE)
        self.act(fid, ReviewAction.VERIFY)
        old = self.p.repo.published_for_slot(self.p.repo.get_fact(fid)["slot_key"])[0]
        with self.assertRaises(KnowledgeError):
            self.p.review.publish(fid, actor=OPERATOR, _fail_after_supersede=True)
        self.assertEqual(self.p.repo.get_fact(old["fact_id"])["lifecycle_state"], "PUBLISHED")
        self.assertEqual(self.p.repo.get_fact(fid)["lifecycle_state"], "VERIFIED")

    def test_future_effective_successor_end_dates_the_current_fact(self):
        slot_fact = self.p.repo.facts_where("v.status_code='D-2' AND f.item_key='여권' AND f.lifecycle_state='PUBLISHED'")[0]
        rep = self.apply([{
            "status_code": "D-2", "procedure": "extension", "property": "required_document",
            "value_text": "여권 (원본)", "item_key": "여권", "requirement_level": "common", "origin": "operator_manual",
            "effective_from": "2099-01-01", "section_title": "유학(D-2)",
            "location": {"source_version_id": self.version("stay_manual_2026_09_18_pdf"), "page_start": 43}}])
        fid = rep.items[0].fact_id
        self.publish_path(fid)
        old = self.p.repo.get_fact(slot_fact["fact_id"])
        self.assertEqual(old["lifecycle_state"], "PUBLISHED")
        self.assertEqual(old["effective_to"], "2099-01-01")
        now = self.p.retrieval.retrieve(status_code="D-2", procedure="extension")
        self.assertIn(slot_fact["fact_id"], now.fact_ids)
        self.assertNotIn(fid, now.fact_ids)
        later = self.p.retrieval.retrieve(status_code="D-2", procedure="extension", as_of="2099-06-01")
        self.assertIn(fid, later.fact_ids)
        self.assertNotIn(slot_fact["fact_id"], later.fact_ids)

    def test_edit_creates_a_new_version_and_never_mutates_published(self):
        pub = self.p.repo.facts_where("v.status_code='D-2' AND f.item_key='여권' AND f.lifecycle_state='PUBLISHED'")[0]
        edited = self.act(pub["fact_id"], ReviewAction.EDIT, value_text="여권 원본")
        self.assertEqual(edited["lifecycle_state"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(edited["lineage_id"], pub["lineage_id"])
        self.assertEqual(edited["version_no"], pub["version_no"] + 1)
        self.assertEqual(self.p.repo.get_fact(pub["fact_id"])["value_text"], "여권")
        self.assertEqual(self.p.review.queue()[0]["compare_fact_id"], pub["fact_id"])
        self.assertEqual(conflicts_open(self.p), 0)

    def test_review_queue_priority_is_transparent(self):
        props = adapters.status_guidance_proposals(self.p.repo, statuses=["D-2"])
        self.p.ingestion.run("sg", props, mode="apply", actor="parser:sg", actor_kind="parser")
        top = self.p.review.queue()[0]
        self.assertIn("procedure_risk", top["priority_factors"])
        self.assertIn("affected_evals", top["priority_factors"])
        self.assertGreater(top["priority_score"], 0)


def conflicts_open(p) -> int:
    return p.store.one("SELECT COUNT(*) FROM knowledge_conflicts WHERE status='open'")[0]


# =============================================================================
# Conflicts [46]
# =============================================================================
class ConflictTests(PlatformCase):
    def test_conflicting_proposals_are_detected_blocked_and_keep_both_provenances(self):
        v = self.version("stay_manual_2026_09_18_pdf")
        a = self.apply([self.proposal(value_text="고용보험 가입내역", item_key="고용보험",
                                      location={"source_version_id": v, "page_start": 540})])
        b = self.apply([self.proposal(origin="ai_extraction", value_text="고용보험 가입내역 (해당자)", item_key="고용보험",
                                      requirement_level="conditional", condition_kind="conditional",
                                      location={"source_version_id": v, "page_start": 541,
                                                "evidence_excerpt": "고용보험 가입내역(해당자)"})],
                       actor="extractor", kind="ai_extractor")
        self.assertEqual(b.items[0].action, "conflict")
        fa, fb = a.items[0].fact_id, b.items[0].fact_id
        rows = self.p.store.all("SELECT * FROM knowledge_conflicts")
        self.assertEqual(len(rows), 1)
        self.assertEqual({rows[0]["fact_a_id"], rows[0]["fact_b_id"]}, {fa, fb})
        self.assertEqual(rows[0]["conflict_kind"], "value_mismatch")
        self.assertEqual(self.p.repo.get_fact(fa)["citations"][0]["page_start"], 540)
        self.assertEqual(self.p.repo.get_fact(fb)["citations"][0]["page_start"], 541)
        with self.assertRaisesRegex(KnowledgeError, "CONFLICT_DETECTED"):
            self.act(fa, ReviewAction.APPROVE)
        self.assertEqual(self.p.repo.published_for_slot(self.p.repo.get_fact(fa)["slot_key"]), [])
        self.p.review.resolve_conflict(rows[0]["conflict_id"], keep_fact_id=fa, actor=OPERATOR,
                                       reason="p.540 is the 제출서류 list; p.541 is a note")
        self.assertEqual(self.p.repo.get_fact(fb)["lifecycle_state"], "REJECTED")
        self.publish_path(fa)
        self.assertEqual(len(self.p.repo.published_for_slot(self.p.repo.get_fact(fa)["slot_key"])), 1)

    def test_operator_contradiction_of_a_published_fact_downgrades_coverage(self):
        """A human-backed contradiction must not yield a silent verified answer."""
        v26 = self.version("stay_manual_2026_06_23_pdf")
        rep = self.apply([{"status_code": "D-2", "procedure": "extension", "property": "required_document",
                           "value_text": "재정입증 서류 (해당자)", "item_key": "재정입증서류",
                           "requirement_level": "conditional", "condition_kind": "conditional",
                           "origin": "operator_manual", "section_title": "유학(D-2)",
                           "location": {"source_version_id": v26, "page_start": 43, "page_end": 44}}])
        self.assertEqual(rep.items[0].action, "conflict")
        plan = self.p.plan("D-2 연장시 필수 서류")
        self.assertEqual(plan.decision.state, "CONFLICTING_SOURCES")
        self.assertEqual(plan.decision.gap_reason, "SOURCE_CONFLICT")
        unverified = [d["source_text"] for d in plan.structured["required_documents"]["missing_or_unverified"]]
        self.assertEqual(unverified, ["재정입증 서류"])
        for bucket in ("common", "required", "conditional"):
            self.assertNotIn("재정입증 서류", [d["source_text"] for d in plan.structured["required_documents"][bucket]])

    def test_unreviewed_parser_update_never_changes_public_answers(self):
        props = adapters.status_guidance_proposals(self.p.repo, statuses=["D-2"])
        self.p.ingestion.run("sg", props, mode="apply", actor="parser:sg", actor_kind="parser")
        plan = self.p.plan("D-2 연장시 필수 서류")
        self.assertIn(plan.decision.state, ("VERIFIED_WITH_CONDITIONS", "DIRECT_VERIFIED"))
        levels = {f["item_key"]: (f["value_json"] or {}).get("requirement_level") for f in plan.retrieval.document_facts}
        self.assertEqual(levels["재정입증서류"], "required")  # still the published 2026.6 value

    def test_unreviewed_import_changes_no_eval_outcome(self):
        """Pending proposals (incl. brand-new sub-code variants such as D-4-2K) are not knowledge."""
        baseline = {r["case_key"]: r["observed"] for r in self.p.evals.run(persist=False)["results"]}
        props = adapters.status_guidance_proposals(self.p.repo, statuses=["D-2", "D-4", "E-7"])
        self.p.ingestion.run("sg", props, mode="apply", actor="parser:sg", actor_kind="parser")
        self.assertIsNotNone(self.p.store.one("SELECT 1 FROM procedure_variants WHERE subcode = 'D-4-2K'"))
        after = self.p.evals.run(persist=False)
        self.assertEqual(after["failed"], 0, [r for r in after["results"] if not r["passed"]])
        for r in after["results"]:
            self.assertEqual(r["observed"], baseline[r["case_key"]], r["case_key"])


# =============================================================================
# Retrieval, understanding, coverage — D-2 [43], unknown [44], missing fact [45]
# =============================================================================
class RetrievalAndCoverageTests(PlatformCase):
    def test_d2_extension_documents_acceptance(self):
        plan = self.p.plan("D-2 연장시 필수 서류")
        u, d, r = plan.understanding, plan.decision, plan.retrieval
        self.assertEqual((u.status_code, u.procedure, u.intent), ("D-2", "extension", "required_documents"))
        self.assertEqual(d.state, "VERIFIED_WITH_CONDITIONS")
        self.assertIsNone(d.gap_reason)
        self.assertTrue(all(f["slot_key"].startswith("D-2|") for f in r.facts))
        self.assertEqual(len(r.document_facts), 8)
        buckets = plan.structured["required_documents"]
        self.assertEqual([x["label"] for x in buckets["common"]], ["신청서", "여권", "외국인등록증", "수수료"])
        self.assertEqual(len(buckets["conditional"]), 1)
        self.assertIn("수료증명서", buckets["conditional"][0]["label"])
        self.assertEqual(plan.structured["source_summary"], "외국인체류 안내매뉴얼 2026.6, 법무부 출입국·외국인정책본부, pp. 43-44")
        blob = json.dumps(plan.structured, ensure_ascii=False)
        self.assertFalse(sa.contains_internal_metadata(blob))
        for term in INTERNAL_TERMS:
            self.assertNotIn(term, blob)

    def test_knowledge_grounding_is_equivalent_to_the_legacy_file(self):
        legacy = pb._load_stay_manual_grounding()
        for entry in legacy["groundings"]:
            with self.subTest(entry=entry["grounding_id"]):
                got = pb._select_grounding(entry["visa_code"], "extension", entry.get("visa_sub_code"))
                for key, value in entry.items():
                    self.assertEqual(got.get(key), value, key)
                bundle = pb._grounding_bundle(got)
                for key in ("source_title", "source_date", "issuing_body", "source_file", "source_revision_date"):
                    self.assertEqual(bundle[key], legacy[key], key)

    def test_subcode_rules_never_flatten(self):
        self.assertIsNotNone(pb._select_grounding("D-4", "extension", "D-4-1"))
        self.assertIsNotNone(pb._select_grounding("D-4", "extension", "D-4-7"))
        for code, sub in (("D-4", "D-4-2K"), ("E-7", "E-7-4"), ("D-10", None), ("F-6", "F-6-1")):
            self.assertIsNone(pb._select_grounding(code, "extension", sub), (code, sub))
        self.assertIsNone(pb._select_grounding("D-2", "overstay_deadline_risk", None))

    def test_unknown_query_creates_and_deduplicates_a_gap(self):
        """[44]"""
        for text in ("H-2 체류기간 연장 필요 서류", "H-2 체류기간 연장 필요 서류 알려주세요"):
            plan = self.p.plan(text)
            self.assertEqual(plan.decision.state, "NO_DIRECT_SOURCE")
            self.assertIsNone(plan.structured)
            self.p.observe(plan, raw_query=text)
        gaps = self.p.learning.list_gaps()
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["reason_code"], "NO_VERIFIED_KNOWLEDGE")
        self.assertEqual(gaps[0]["occurrence_count"], 2)
        self.assertEqual((gaps[0]["status_code"], gaps[0]["procedure"], gaps[0]["intent"]),
                         ("H-2", "extension", "required_documents"))

    def test_missing_user_fact_is_not_a_knowledge_gap(self):
        """[45]"""
        plan = self.p.plan("연장할 때 필요한 서류가 뭐예요?")
        self.assertEqual(plan.decision.state, "NEEDS_CLARIFICATION")
        self.assertEqual(plan.decision.clarify, ["status_code"])
        self.assertIn("D-2", plan.decision.alternatives)
        self.p.observe(plan, raw_query="연장할 때 필요한 서류가 뭐예요?")
        self.assertEqual(self.p.learning.list_gaps(status="all"), [])
        self.assertEqual(self.p.store.one("SELECT COUNT(*) FROM query_observations")[0], 1)

    def test_retrieval_failure_is_unknown_not_no_rule(self):
        with patch.object(self.p.retrieval, "retrieve", side_effect=RuntimeError("db down")):
            plan = self.p.plan("D-2 연장시 필수 서류")
        self.assertEqual(plan.decision.state, "UNKNOWN")
        self.assertEqual(plan.decision.gap_reason, "RETRIEVAL_FAILED")

    def test_high_risk_task_never_gets_a_plain_checklist(self):
        plan = self.p.plan("D-2 비자 만료 임박인데 연장 서류 알려줘")
        self.assertIsNone(plan.understanding.retrieval_procedure)
        self.assertIsNone(plan.structured)

    def test_retrieval_is_cached_and_invalidated_by_writes(self):
        first = self.p.retrieval.retrieve(status_code="D-2", procedure="extension")
        self.assertIs(self.p.retrieval.retrieve(status_code="D-2", procedure="extension"), first)
        self.apply([self.proposal()])
        self.assertIsNot(self.p.retrieval.retrieve(status_code="D-2", procedure="extension"), first)


# =============================================================================
# Answer Guard [89] + runtime integration through /api/ask [42, 88]
# =============================================================================
class RuntimeIntegrationTests(PlatformCase):
    def test_d2_answer_comes_from_the_knowledge_store(self):
        resp = self.ask("D-2 연장시 필수 서류", "D-2 연장에는 기본 서류와 학업·재정·체류지 입증서류가 필요합니다.")
        body = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(body["answer_ref"].startswith("obs_"))
        self.assertNotIn("knowledge_plan", body)
        docs = body["structured_answer"]["required_documents"]
        self.assertEqual(len([d for b in docs.values() for d in b]), 8)
        lowered = resp.text.lower()
        for term in VENDOR_TERMS + ("fact_id", "slot_key", "verification_note", "coverage_state", "review"):
            self.assertNotIn(term, lowered)

    def test_diagnostics_show_the_answer_plan(self):
        body = self.ask("D-2 연장시 필수 서류", "요약", diagnostics=True).json()
        plan = body["knowledge_plan"]
        self.assertEqual(plan["coverage"]["state"], "VERIFIED_WITH_CONDITIONS")
        self.assertEqual(plan["retrieval"]["variant_key"], "D-2|*|extension|general")

    def test_bad_model_output_is_rejected_and_facts_stay_authoritative(self):
        """[89] fake document + guaranteed outcome in the model summary."""
        bad = "D-2 연장에는 건강진단서와 범죄경력증명서가 꼭 필요하며, 이 서류만 내면 100% 허가됩니다."
        body = self.ask("D-2 연장시 필수 서류", bad, diagnostics=True).json()
        structured = body["structured_answer"]
        self.assertEqual(structured["short_answer_source"], "deterministic")
        self.assertNotIn("건강진단서", resp_text := json.dumps(structured, ensure_ascii=False))
        self.assertNotIn("100%", resp_text)
        self.assertNotIn("건강진단서", body["answer"])
        self.assertEqual(body["knowledge_plan"]["guard"]["outcome"], "blocked")
        self.assertTrue(body["knowledge_plan"]["answer_guard_replaced_summary"])
        rendered = sorted(d["source_text"] for b in structured["required_documents"].values() for d in b)
        legacy = [g for g in pb._load_stay_manual_grounding()["groundings"] if g["visa_code"] == "D-2"][0]
        self.assertEqual(rendered, sorted(" ".join(x.split()) for x in legacy["required_documents"]))

    def test_free_form_answer_with_provider_leak_is_withheld(self):
        leak = "OpenRouter gemma 모델 기준으로 H-2는 무조건 허가됩니다."
        body = self.ask("H-2 체류기간 연장 필요 서류", leak, diagnostics=True).json()
        self.assertNotIn("openrouter", body["answer"].lower())
        self.assertNotIn("무조건", body["answer"])
        self.assertTrue(body["knowledge_plan"]["answer_guard_blocked"])
        self.assertTrue(body["deterministic_fallback_answer_used"])

    def test_model_outage_still_returns_the_verified_checklist(self):
        """[88]"""
        async def failing(prompt, requested_model=None, candidate_models=None, max_tokens=None, **kw):
            return {**_provider_ok("", list(candidate_models or ["x"])), "ok": False, "answer": None,
                    "final_model": None, "provider_error_type": "timeout",
                    "retryable_provider_error": True, "all_candidates_failed": True}
        with patch.object(pb, "OPENROUTER_API_KEY", "sk-test-sentinel"), \
                patch.object(pb, "ENABLE_OLLAMA_FALLBACK", False), patch.object(pb, "ALLOW_GROQ_FALLBACK", False), \
                patch.object(pb, "_openrouter_complete_with_candidates", failing):
            resp = TestClient(pb.app).post("/api/ask", json={"question": "D-2 연장시 필수 서류", "stream": False})
        body = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(body["deterministic_fallback_answer_used"])
        self.assertEqual(body["fallback_answer_kind"], "structured_document_checklist")
        for doc in ("신청서", "여권", "외국인등록증", "재정입증 서류", "체류지 입증서류"):
            self.assertIn(doc, body["answer"])

    def test_ask_records_privacy_minimized_observations_and_gaps(self):
        self.ask("H-2 체류기간 연장 서류요. 제 여권번호는 M12345678, 연락처 010-1234-5678", "안내")
        self.ask("H-2 체류기간 연장 서류요", "안내")
        rows = self.p.store.all("SELECT * FROM query_observations")
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertNotIn("M12345678", row["sanitized_query"])
            self.assertNotIn("010-1234-5678", row["sanitized_query"])
        gap = self.p.learning.list_gaps()[0]
        self.assertEqual(gap["occurrence_count"], 2)
        self.assertNotIn("M12345678", gap["example_query"])

    def test_answers_never_become_knowledge(self):
        """[67] no self-training loop."""
        before = self.p.store.one("SELECT COUNT(*) FROM knowledge_facts")[0]
        for q in ("H-2 체류기간 연장 필요 서류", "D-2 연장시 필수 서류", "F-6 연장 온라인 가능?"):
            self.ask(q, "생성된 답변 텍스트")
        self.assertEqual(self.p.store.one("SELECT COUNT(*) FROM knowledge_facts")[0], before)


class GuardUnitTests(PlatformCase):
    def setUp(self):
        super().setUp()
        self.facts = self.p.retrieval.retrieve(status_code="D-2", procedure="extension").facts

    def check(self, text, **kw):
        return guard.check(text, verified_facts=self.facts, status_code="D-2", cited_pages=[43, 44], **kw)

    def test_clean_summary_passes(self):
        self.assertEqual(self.check("D-2 연장에는 신청서·여권·외국인등록증·수수료와 재학·재정·체류지 입증서류가 필요합니다.").outcome,
                         "passed")

    def test_checks(self):
        cases = {
            "unsupported_document": "건강진단서를 제출하세요.",
            "forbidden_certainty": "100% 허가됩니다.",
            "provider_model_leak": "Gemma 기준 답변",
            "internal_metadata_leak": "slot_key 기준",
            "unsafe_html": "<script>x</script>",
            "wrong_status_family": "F-6 결혼이민 서류와 같습니다.",
            "wrong_procedure_scope": "사증발급인정서를 먼저 받으세요.",
            "conditional_promoted_to_universal": "모든 신청자는 반드시 수료증명서를 내야 합니다.",
            "unsupported_citation": "매뉴얼 99쪽에 있습니다.",
            "claims_official_confirmation": "출입국에서 공식 확인했습니다.",
        }
        for check, text in cases.items():
            with self.subTest(check=check):
                self.assertIn(check, {f.check for f in self.check(text).findings})

    def test_omission_only_checked_for_full_answers(self):
        self.assertNotIn("required_fact_omitted", {f.check for f in self.check("여권만 준비하세요").findings})
        full = self.check("여권만 준비하세요", summary_only=False)
        self.assertIn("required_fact_omitted", {f.check for f in full.findings})

    def test_language_mismatch(self):
        text = "You need an application form, passport and the residence card for this extension procedure."
        self.assertIn("language_mismatch", {f.check for f in self.check(text, language="ko").findings})


# =============================================================================
# Learning loop, feedback, privacy, promotion [22, 27, 36]
# =============================================================================
class LearningLoopTests(PlatformCase):
    def test_sanitizer_masks_identifiers_and_sensitive_markers(self):
        text = ("제 이름은 김민수입니다. 여권 M12345678, 외국인등록번호 900101-5123456, 이메일 a.b@c.com, "
                "전화 010-1234-5678, 서울특별시 강남구 역삼동, 잔고 3,000만원, 임신 12주")
        out = privacy.sanitize(text)
        for raw in ("김민수", "M12345678", "900101-5123456", "a.b@c.com", "010-1234-5678", "역삼동", "3,000만원", "12주"):
            self.assertNotIn(raw, out)
        self.assertLessEqual(len(privacy.sanitize("가" * 500)), privacy.EXCERPT_MAX + 1)

    def test_text_retention_can_be_disabled(self):
        with patch.dict(os.environ, {"WAYMAKER_QUERY_TEXT_RETENTION": "none"}):
            plan = self.p.plan("H-2 체류기간 연장 필요 서류")
            self.p.observe(plan, raw_query="H-2 체류기간 연장 필요 서류")
        row = self.p.store.one("SELECT sanitized_query FROM query_observations")
        self.assertEqual(row[0], "")
        self.assertEqual(self.p.learning.list_gaps()[0]["example_query"], "")

    def test_feedback_links_to_observation_and_feeds_the_gap_queue(self):
        plan = self.p.plan("D-2 연장시 필수 서류")
        obs = self.p.observe(plan, raw_query="D-2 연장시 필수 서류")
        self.assertIsNone(obs["gap_id"])
        res = self.p.learning.record_feedback(FeedbackIn(reason="INCORRECT", answer_ref=obs["observation_id"],
                                                         comment="재정입증 서류는 생략됐어요 010-1234-5678"))
        gap = self.p.learning.get_gap(res["gap_id"])
        self.assertEqual((gap["reason_code"], gap["status_code"], gap["feedback_count"]),
                         ("USER_REPORTED_INCORRECT", "D-2", 1))
        fb = self.p.store.one("SELECT * FROM user_feedback")
        self.assertNotIn("010-1234-5678", fb["comment_sanitized"])
        self.assertIn("kf_", fb["fact_ids"])  # linked to the facts that answered
        helpful = self.p.learning.record_feedback(FeedbackIn(reason="HELPFUL", answer_ref=obs["observation_id"]))
        self.assertIsNone(helpful["gap_id"])

    def test_resolved_gap_becomes_a_regression_eval(self):
        """[27] unknown -> knowledge added -> gap resolved -> eval promoted -> passes."""
        plan = self.p.plan("H-2 체류기간 연장 필요 서류")
        gap_id = self.p.observe(plan, raw_query="H-2 체류기간 연장 필요 서류")["gap_id"]
        rep = self.apply([self.proposal(value_text="여권"), self.proposal(value_text="외국인등록증", sort_order=1)])
        for item in rep.items:
            self.publish_path(item.fact_id)
        self.p.learning.update_gap(gap_id, resolution_status="resolved", note="H-2 extension list published",
                                   actor=OPERATOR)
        case = self.p.learning.promote_gap_to_eval(gap_id, EvalCaseIn(
            case_key="gap.h2.extension", query="H-2 체류기간 연장 필요 서류",
            assertions=[{"type": "EXPECTED_COVERAGE_STATE", "value": "DIRECT_VERIFIED"},
                        {"type": "MUST_INCLUDE_FACT", "value": ["여권", "외국인등록증"]},
                        {"type": "MUST_NOT_RECORD_GAP"}]), actor=OPERATOR, evals=self.p.evals)
        self.assertEqual(case["state"], "draft")
        self.assertEqual(self.p.evals.run(selector="gap.h2.extension")["total"], 0)  # drafts never run
        self.p.evals.set_state(case["case_id"], "approved", actor=OPERATOR)
        run = self.p.evals.run(selector="gap.h2.extension")
        self.assertEqual((run["total"], run["passed"]), (1, 1), run)
        self.assertEqual(self.p.learning.get_gap(gap_id)["linked_eval_case_id"], case["case_id"])

    def test_recurring_resolved_gap_reopens(self):
        plan = self.p.plan("H-2 체류기간 연장 필요 서류")
        gap_id = self.p.observe(plan, raw_query="q")["gap_id"]
        self.p.learning.update_gap(gap_id, resolution_status="resolved", note="x", actor=OPERATOR)
        self.p.observe(self.p.plan("H-2 체류기간 연장 필요 서류"), raw_query="q")
        self.assertEqual(self.p.learning.get_gap(gap_id)["resolution_status"], "open")

    def test_expired_observations_are_purged(self):
        self.p.observe(self.p.plan("D-2 연장시 필수 서류"), raw_query="q")
        self.assertEqual(self.p.learning.purge_expired(now="9999-01-01T00:00:00Z"), 1)


# =============================================================================
# Evals [23-26] and source diff [28, 77]
# =============================================================================
class EvalAndDiffTests(PlatformCase):
    def test_seed_corpus_passes(self):
        run = self.p.evals.run(selector="tag:ci")
        self.assertGreaterEqual(run["total"], 19)
        self.assertEqual(run["failed"], 0, [r for r in run["results"] if not r["passed"]])

    def test_golden_questions_are_referenced(self):
        self.assertEqual(len(self.p.evals.list_cases(tag="golden_questions_v1")), 50)
        self.assertEqual(self.p.evals.run(selector="tag:golden_questions_v1")["failed"], 0)

    def test_a_factual_regression_fails_even_if_prose_is_unchanged(self):
        fact = self.p.repo.facts_where("v.status_code='D-2' AND f.item_key='재정입증서류' AND f.lifecycle_state='PUBLISHED'")[0]
        self.p.review.act(fact["fact_id"], ReviewActionRequest(action="withdraw", reason="test"), actor=OPERATOR)
        run = self.p.evals.run(selector="d2.extension.documents.ko")
        self.assertEqual(run["failed"], 1)
        self.assertTrue(any("재정입증 서류" in f for f in run["results"][0]["failures"]))

    def test_assertion_types(self):
        case = {"assertions": [{"type": t} for t in ("MUST_CLARIFY",)] + [
            {"type": "EXPECTED_STATUS", "value": "E-7"}, {"type": "MUST_NOT_INCLUDE_FACT", "value": "여권"},
            {"type": "SOURCE_MUST_NOT_BE", "value": {"edition": "2026.6"}}, {"type": "LANGUAGE_EXPECTED", "value": "en"},
            {"type": "BOGUS"}]}
        observed = {"status_code": "D-2", "coverage_state": "VERIFIED_WITH_CONDITIONS", "clarify": [],
                    "documents": [{"text": "여권", "bucket": "common"}], "sources": [{"edition": "2026.6"}],
                    "locale": "ko", "guard_checks": [], "gap_reason": None}
        self.assertEqual(len(self.p.evals.evaluate(case, observed)), 6)

    def test_source_version_diff_d2(self):
        """[77] 2026.6 (published) vs 2026.9 (proposals)."""
        self.p.ingestion.run("sg", adapters.status_guidance_proposals(self.p.repo, statuses=["D-2", "D-4"]),
                             mode="apply", actor="parser:sg", actor_kind="parser")
        a, b = self.version("stay_manual_2026_06_23_pdf"), self.version("stay_manual_2026_09_18_pdf")
        d = diff_versions(self.p.repo, a, b, status_code="D-2", properties=["required_document"])
        self.assertEqual(d["summary"], {"ADDED": 0, "REMOVED": 0, "CHANGED": 4, "UNCHANGED": 4})
        by_item = {r["slot_key"].rsplit("|", 1)[1]: r for r in d["records"]}
        self.assertEqual(by_item["재정입증서류"]["change"], "CHANGED")
        self.assertIn("requirement_level", by_item["재정입증서류"]["changed_fields"])
        self.assertEqual(by_item["여권"]["change"], "UNCHANGED")
        self.assertEqual(by_item["체류지입증서류"]["changed_fields"], ["wording"])
        self.assertIn("d2.extension.documents.ko", by_item["재정입증서류"]["affected_eval_cases"])
        d4 = diff_versions(self.p.repo, a, b, status_code="D-4", properties=["required_document"])
        kinds = {r["slot_key"].rsplit("|", 1)[1]: r["change"] for r in d4["records"] if "|*|" in r["slot_key"]}
        self.assertEqual(kinds["통합신청서"], "ADDED")
        self.assertEqual(kinds["신청서"], "REMOVED")
        visa = self.p.repo.find_source_version("visa_issuance_manual", "visa_manual_2026_09_01_pdf")
        with self.assertRaises(KnowledgeError):
            diff_versions(self.p.repo, a, visa["source_version_id"])


# =============================================================================
# Operator API: authentication and the Knowledge Studio workflow [37, 76]
# =============================================================================
class OperatorApiTests(PlatformCase):
    def client(self, token=TOKEN):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return TestClient(pb.app, headers=headers)

    def test_studio_is_closed_when_no_operator_tokens_are_configured(self):
        with patch.dict(os.environ, {"WAYMAKER_OPERATOR_TOKENS": ""}):
            self.assertEqual(self.client().get("/api/knowledge/studio/overview").status_code, 503)

    def test_anonymous_and_wrong_token_cannot_mutate(self):
        fact = self.p.repo.facts_where("f.lifecycle_state='PUBLISHED'")[0]
        with patch.dict(os.environ, {"WAYMAKER_OPERATOR_TOKENS": f"{OPERATOR}:{TOKEN}"}):
            for token in (None, "wrong-token-000000000000"):
                c = self.client(token)
                self.assertEqual(c.get("/api/knowledge/studio/overview").status_code, 401)
                self.assertEqual(c.post(f"/api/knowledge/studio/facts/{fact['fact_id']}/actions",
                                        json={"action": "withdraw", "reason": "x"}).status_code, 401)
                self.assertEqual(c.post("/api/knowledge/studio/evals",
                                        json={"case_key": "x.y.z", "query": "q"}).status_code, 401)
                self.assertEqual(c.post("/api/knowledge/studio/ingest",
                                        json={"adapter": "status_guidance", "mode": "apply"}).status_code, 401)
        self.assertEqual(self.p.repo.get_fact(fact["fact_id"])["lifecycle_state"], "PUBLISHED")

    def test_public_export_has_no_review_or_internal_metadata(self):
        resp = self.client(None).get("/api/knowledge/published")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["fact_count"], 42)
        for term in ("reviewed_by", "verified_by", "proposal_hash", "artifact_ref", "verification_note",
                     "backend/data", ".pdf", "reviewer_kind", "created_by"):
            self.assertNotIn(term, resp.text)

    def test_public_feedback_endpoint(self):
        ref = self.ask("D-2 연장시 필수 서류", "요약").json()["answer_ref"]
        resp = self.client(None).post("/api/feedback", json={"reason": "MISSING_INFORMATION", "answer_ref": ref})
        self.assertEqual(resp.json(), {"ok": True})
        self.assertEqual(self.p.learning.list_gaps(kind="feedback")[0]["reason_code"], "USER_REPORTED_INCOMPLETE")
        self.assertEqual(self.client(None).post("/api/feedback", json={"reason": "NOPE"}).status_code, 422)

    def test_full_operator_workflow_over_the_api(self):
        """[76] import -> review -> publish -> Waymaker -> gap -> resolve -> eval."""
        with patch.dict(os.environ, {"WAYMAKER_OPERATOR_TOKENS": f"{OPERATOR}:{TOKEN}"}):
            c = self.client()
            base = "/api/knowledge/studio"
            self.assertEqual(c.get(f"{base}/overview").json()["operator"], OPERATOR)
            dry = c.post(f"{base}/ingest", json={"adapter": "status_guidance", "statuses": ["D-2"],
                                                 "mode": "dry_run"}).json()
            self.assertEqual(dry["summary"], {"reconfirm": 4, "update": 4})
            c.post(f"{base}/ingest", json={"adapter": "status_guidance", "statuses": ["D-2"], "mode": "apply"})
            queue = c.get(f"{base}/review-queue").json()["tasks"]
            task = [t for t in queue if t["value_text"] == "재정입증 서류"][0]
            detail = c.get(f"{base}/review-queue/{task['task_id']}").json()
            self.assertEqual(detail["diff"]["proposed"]["requirement_level"], "conditional")
            self.assertGreaterEqual(detail["impact"]["affected_eval_count"], 1)
            evidence = c.get(f"{base}/evidence/{task['fact_id']}").json()["evidence"][0]
            self.assertEqual(evidence["kind"], "parsed_page_text")
            for action in ("approve", "verify", "publish"):
                r = c.post(f"{base}/facts/{task['fact_id']}/actions", json={"action": action, "reason": "p.43"})
                self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()["fact"]["verified_by"], OPERATOR)
            body = self.ask("D-2 연장시 필수 서류", "요약").json()
            conditional = [d["label"] for d in body["structured_answer"]["required_documents"]["conditional"]]
            self.assertIn("재정입증 서류", conditional)
            self.assertIn("2026.9 / 2026.6", body["structured_answer"]["source_summary"])
            self.assertIn("43 (2026.9); 43-44 (2026.6)", body["structured_answer"]["source_summary"])
            self.ask("H-2 체류기간 연장 필요 서류", "안내")
            gap = c.get(f"{base}/gaps?kind=unknown").json()["gaps"][0]
            self.assertEqual(gap["status_code"], "H-2")
            c.post(f"{base}/gaps/{gap['gap_id']}", json={"resolution_status": "investigating", "note": "sourcing"})
            case = c.post(f"{base}/gaps/{gap['gap_id']}/promote", json={
                "case_key": "api.gap.h2", "query": "H-2 체류기간 연장 필요 서류",
                "assertions": [{"type": "EXPECTED_COVERAGE_STATE", "value": "NO_DIRECT_SOURCE"}]}).json()
            c.post(f"{base}/evals/{case['case_id']}/state", json={"state": "approved"})
            run = c.post(f"{base}/evals/run", json={"selector": "api.gap.h2"}).json()
            self.assertEqual((run["total"], run["passed"]), (1, 1))
            overview = c.get(f"{base}/overview").json()
            self.assertEqual(overview["metrics"]["failing_eval_cases"], 0)
            self.assertGreaterEqual(overview["metrics"]["unresolved_gaps"], 1)
            audit = c.get(f"{base}/audit").json()["audit"]
            self.assertTrue(any(a["actor"] == OPERATOR and a["action"] == "transition:PUBLISHED" for a in audit))
            diff_resp = c.get(f"{base}/diff", params={
                "from_version": self.version("stay_manual_2026_06_23_pdf"),
                "to_version": self.version("stay_manual_2026_09_18_pdf"), "status_code": "D-2"})
            self.assertEqual(diff_resp.status_code, 200)


class KnowledgeStudioContractTests(PlatformCase):
    """Pins the response keys knowledge-studio.js reads (its E2E uses mocks)."""

    def test_studio_api_shapes(self):
        adapters_props = adapters.status_guidance_proposals(self.p.repo, statuses=["D-2"])
        self.p.ingestion.run("sg", adapters_props, mode="apply", actor="parser:sg", actor_kind="parser")
        self.p.observe(self.p.plan("H-2 체류기간 연장 필요 서류"), raw_query="H-2 체류기간 연장 필요 서류")
        self.p.evals.run(selector="tag:ci")
        with patch.dict(os.environ, {"WAYMAKER_OPERATOR_TOKENS": f"{OPERATOR}:{TOKEN}"}):
            c = TestClient(pb.app, headers={"Authorization": f"Bearer {TOKEN}"})
            base = "/api/knowledge/studio"
            o = c.get(f"{base}/overview").json()
            self.assertTrue({"operator", "storage", "metrics", "sources_needing_refresh"} <= set(o))
            self.assertTrue({"pending_review", "open_review_tasks", "open_conflicts", "unresolved_gaps",
                             "new_unknown_clusters_7d", "published_facts", "superseded_facts", "failing_eval_cases",
                             "sources_needing_refresh", "feedback_7d"} <= set(o["metrics"]))
            t = c.get(f"{base}/review-queue").json()["tasks"][0]
            self.assertTrue({"task_id", "fact_id", "task_kind", "priority_score", "priority_factors", "value_text",
                             "lifecycle_state", "status_code", "subcode", "procedure", "variant_key"} <= set(t))
            d = c.get(f"{base}/review-queue/{t['task_id']}").json()
            self.assertTrue({"task", "proposed", "current_published", "diff", "conflicts", "impact", "audit"} <= set(d))
            self.assertTrue({"value_text", "lifecycle_state", "variant_key", "property", "origin", "created_by_kind",
                             "extraction_warnings", "citations", "fact_id"} <= set(d["proposed"]))
            self.assertTrue({"source_title", "version_label", "page_start", "page_end", "section_title", "locator",
                             "content_review_state", "version_status"} <= set(d["proposed"]["citations"][0]))
            self.assertTrue({"affected_eval_count", "affected_eval_cases", "would_supersede",
                             "requires_regression_rerun"} <= set(d["impact"]))
            ev = c.get(f"{base}/evidence/{t['fact_id']}").json()["evidence"][0]
            self.assertTrue({"source", "pages", "kind", "match_found", "text"} <= set(ev))
            src = c.get(f"{base}/sources").json()["sources"][0]
            self.assertTrue({"source_id", "source_key", "title_ko", "refresh_state", "versions"} <= set(src))
            self.assertTrue({"source_version_id", "version_label", "edition_ref", "status", "content_review_state",
                             "effective_from", "published_fact_count", "pending_fact_count"} <= set(src["versions"][0]))
            gap = c.get(f"{base}/gaps?kind=unknown&status=all").json()["gaps"][0]
            self.assertTrue({"gap_id", "reason_code", "status_code", "subcode", "procedure", "intent", "occurrence_count",
                             "feedback_count", "last_seen", "example_query", "resolution_status"} <= set(gap))
            case = c.get(f"{base}/evals").json()["cases"][0]
            self.assertTrue({"case_id", "case_key", "query", "origin", "state", "last_result"} <= set(case))
            a = c.get(f"{base}/audit").json()["audit"][0]
            self.assertTrue({"at", "actor", "actor_kind", "entity_type", "entity_id", "action", "reason"} <= set(a))
            f = c.get(f"{base}/facts").json()["facts"][0]
            self.assertTrue({"verified_by", "reviewer_kind", "condition_kind", "condition_text", "citations"} <= set(f))
            self.assertEqual(c.get(f"{base}/conflicts").json(), {"conflicts": []})


if __name__ == "__main__":
    unittest.main()

