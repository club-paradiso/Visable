"""Persistent evaluation corpus + deterministic (offline) eval runner.

An eval asserts FACTS and BEHAVIOUR, not prose: which status / procedure /
intent was understood, which coverage state was decided, which documents are
in which bucket, which source backs them, whether a clarification or a gap was
produced, and that nothing internal leaked. A reworded answer passes; a
changed fact fails.

Offline mode runs the full deterministic path (detectors -> understanding ->
retrieval -> coverage -> structured facts -> guard) without any model or
network. Live-model quality checks stay in scripts/smoke_ai_live_quality.py
and are not part of normal PR CI.

The seed corpus lives in ``backend/data/knowledge/eval_corpus_seed.json``
(reviewed in git) and is imported idempotently into the eval tables; cases
added in Knowledge Studio (e.g. promoted from a resolved gap) live in the DB
and are exported with ``scripts/knowledge/knowledge_cli.py export-evals``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from services import structured_answer as _structured_answer

from . import guard as guard_mod
from .models import EvalAssertionType as A, EvalCaseIn, KnowledgeError, PipelineError
from .store import new_id, row_dict, utc_now

logger = logging.getLogger("paradiso.knowledge")

SEED_CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "eval_corpus_seed.json"
GOLDEN_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "paradiso_ai_golden_questions.json"

_GOLDEN_TASK_PROCEDURE = {
    "extension": "extension", "status_change": "status_change", "workplace_change": "workplace_change",
    "foreigner_registration": "registration", "activities_outside_status": "activities_outside_status",
    "marriage_divorce_status_change": "status_change", "family_status_change": "status_grant",
    "address_report": "address_report", "passport_info_report": "reporting_duty",
    "academic_status_change": "reporting_duty", "overstay_deadline_risk": "extension",
}


def _norm(text: Any) -> str:
    return "".join(str(text or "").split()).lower()


class EvalService:
    def __init__(self, platform):
        self.platform = platform
        self.store = platform.store

    # ------------------------------------------------------------------
    def create_case(self, case: EvalCaseIn, *, actor: str, origin: str = "operator", state: str = "draft",
                    source_gap_id: Optional[str] = None) -> Dict[str, Any]:
        if self.store.one("SELECT 1 FROM eval_cases WHERE case_key = ?", (case.case_key,)):
            raise KnowledgeError(PipelineError.DUPLICATE_FACT, f"eval case {case.case_key} exists")
        case_id = new_id("ev")
        now = utc_now()
        expected = dict(case.expected)
        if case.payload_visa_code:
            expected["payload_visa_code"] = case.payload_visa_code
        approved = state == "approved"
        with self.store.transaction():
            self.store.execute(
                "INSERT INTO eval_cases(case_id, case_key, query, language, expected, assertions, risk_category, tags,"
                " origin, state, source_gap_id, created_by, approved_by, approved_at, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (case_id, case.case_key, case.query, case.language, json.dumps(expected, ensure_ascii=False),
                 json.dumps([a.model_dump(mode="json") for a in case.assertions], ensure_ascii=False),
                 case.risk_category, json.dumps(case.tags), origin, state, source_gap_id, actor,
                 actor if approved else None, now if approved else None, now, now))
            for slot in case.depends_on_slots:
                self.store.execute("INSERT OR IGNORE INTO eval_case_dependencies(case_id, slot_key) VALUES (?,?)",
                                   (case_id, slot))
            self.store.audit(actor=actor, actor_kind="human_operator" if origin in ("operator", "promoted_gap")
                             else "system", entity_type="eval_case", entity_id=case_id, action="create",
                             after={"case_key": case.case_key, "origin": origin, "state": state})
        return self.get_case(case_id)

    def set_state(self, case_id: str, state: str, *, actor: str, reason: str = "") -> Dict[str, Any]:
        if state not in ("draft", "approved", "retired"):
            raise KnowledgeError(PipelineError.MALFORMED_VALUE, "unknown eval state")
        before = self.get_case(case_id)
        with self.store.transaction():
            self.store.execute(
                "UPDATE eval_cases SET state = ?, approved_by = CASE WHEN ? = 'approved' THEN ? ELSE approved_by END,"
                " approved_at = CASE WHEN ? = 'approved' THEN ? ELSE approved_at END, updated_at = ? WHERE case_id = ?",
                (state, state, actor, state, utc_now(), utc_now(), case_id))
            self.store.audit(actor=actor, actor_kind="human_operator", entity_type="eval_case", entity_id=case_id,
                             action=f"state:{state}", reason=reason, before={"state": before["state"]},
                             after={"state": state})
        return self.get_case(case_id)

    def get_case(self, case_id: str) -> Dict[str, Any]:
        row = row_dict(self.store.one("SELECT * FROM eval_cases WHERE case_id = ? OR case_key = ?", (case_id, case_id)),
                       json_fields=("expected", "assertions", "tags"))
        if not row:
            raise KnowledgeError(PipelineError.NOT_FOUND, f"eval case {case_id} not found")
        row["depends_on_slots"] = [r["slot_key"] for r in self.store.all(
            "SELECT slot_key FROM eval_case_dependencies WHERE case_id = ?", (row["case_id"],))]
        return row

    def list_cases(self, *, state: Optional[str] = None, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = [row_dict(r, json_fields=("expected", "assertions", "tags")) for r in self.store.all(
            "SELECT * FROM eval_cases" + (" WHERE state = ?" if state else "") + " ORDER BY case_key",
            (state,) if state else ())]
        if tag:
            rows = [r for r in rows if tag in (r.get("tags") or [])]
        last = {r["case_id"]: r for r in self.store.all(
            "SELECT r.case_id, r.passed, r.failures FROM eval_results r"
            " WHERE r.run_id = (SELECT run_id FROM eval_runs ORDER BY started_at DESC LIMIT 1)")}
        for row in rows:
            res = last.get(row["case_id"])
            row["last_result"] = None if res is None else {"passed": bool(res["passed"]),
                                                          "failures": json.loads(res["failures"])}
        return rows

    # ------------------------------------------------------------------
    def import_seed_corpus(self, path: Path = SEED_CORPUS_PATH, *, include_golden: bool = True) -> Dict[str, int]:
        """Idempotent import of the git-reviewed seed corpus (+ golden questions)."""
        added = 0
        data = json.loads(path.read_text(encoding="utf-8"))
        for raw in data.get("cases") or []:
            if self.store.one("SELECT 1 FROM eval_cases WHERE case_key = ?", (raw["case_key"],)):
                continue
            case = EvalCaseIn.model_validate({k: v for k, v in raw.items() if k != "state"})
            self.create_case(case, actor="seed:eval_corpus_seed.json", origin="seed_foundation",
                             state=raw.get("state", "approved"))
            added += 1
        if include_golden and GOLDEN_PATH.is_file():
            added += self._import_golden()
        return {"added": added}

    def _import_golden(self) -> int:
        """Reference the routing golden set: status / sub-code / procedure assertions."""
        added = 0
        for q in json.loads(GOLDEN_PATH.read_text(encoding="utf-8")).get("questions") or []:
            key = f"golden.{q['id']}".lower()
            if self.store.one("SELECT 1 FROM eval_cases WHERE case_key = ?", (key,)):
                continue
            asserts: List[Dict[str, Any]] = [{"type": A.MUST_NOT_LEAK_INTERNAL_METADATA.value}]
            if q.get("visa_code"):
                asserts.append({"type": A.EXPECTED_STATUS.value, "value": q["visa_code"]})
            if q.get("visa_sub_code"):
                asserts.append({"type": A.EXPECTED_SUBCODE.value, "value": q["visa_sub_code"]})
            proc = _GOLDEN_TASK_PROCEDURE.get(q.get("expected_task_type") or "")
            if proc:
                asserts.append({"type": A.EXPECTED_PROCEDURE.value, "value": proc})
            if q.get("expected_grounding_status") == "active_grounded":
                asserts.append({"type": A.EXPECTED_COVERAGE_STATE.value,
                                "value": ["DIRECT_VERIFIED", "VERIFIED_WITH_CONDITIONS", "PARTIAL_VERIFIED"]})
            elif q.get("expected_grounding_status") in ("candidate_only", "scoped_fallback", "unsupported"):
                asserts.append({"type": A.EXPECTED_COVERAGE_STATE.value,
                                "value": ["NO_DIRECT_SOURCE", "UNKNOWN", "OUT_OF_SCOPE", "NEEDS_CLARIFICATION"]})
            case = EvalCaseIn(case_key=key, query=q["question"], language=q.get("language") or "ko",
                              # Same payload semantics as scripts/evaluate_paradiso_ai_golden_questions.py.
                              payload_visa_code=q.get("visa_sub_code") or q.get("visa_code") or None,
                              assertions=asserts,
                              tags=["golden_questions_v1", q.get("language") or "ko"],
                              risk_category=q.get("expected_risk_level") or "standard")
            self.create_case(case, actor="seed:paradiso_ai_golden_questions.json", origin="golden_questions_v1",
                             state="approved")
            added += 1
        return added

    # ------------------------------------------------------------------
    def observe_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Run one case through the deterministic path; return what happened."""
        expected = case.get("expected") or {}
        plan = self.platform.plan(case["query"], payload_code=expected.get("payload_visa_code"),
                                  lang=case.get("language"))
        structured = plan.structured
        text = _structured_answer.compose_plain_text(structured, case.get("language")) if structured else ""
        docs = []
        if structured:
            for bucket, items in (structured.get("required_documents") or {}).items():
                for item in items:
                    docs.append({"text": item.get("source_text") or item.get("label"), "bucket": bucket})
        sources = [{"title": s["title"], "edition": s["edition"], "pages": s["pages"]}
                   for s in (plan.retrieval.sources if plan.retrieval else [])]
        public_blob = json.dumps(structured or {}, ensure_ascii=False)
        g = guard_mod.check(text + "\n" + public_blob, language=case.get("language") or "ko",
                            verified_facts=[], status_code=plan.understanding.status_code,
                            user_mentioned_statuses=plan.understanding.mentioned_statuses) if (text or structured) else None
        u, d = plan.understanding, plan.decision
        return {
            "status_code": u.status_code, "subcode": u.subcode, "procedure": u.procedure, "intent": u.intent,
            "coverage_state": d.state, "answer_path": d.answer_path, "clarify": d.clarify,
            "gap_reason": d.gap_reason, "documents": docs, "sources": sources,
            "locale": (structured or {}).get("locale"),
            "guard_checks": sorted({f.check for f in (g.findings if g else [])}),
            "slots": sorted({f["slot_key"] for f in (plan.retrieval.facts if plan.retrieval else [])}),
        }

    def evaluate(self, case: Dict[str, Any], observed: Dict[str, Any]) -> List[str]:
        failures: List[str] = []
        docs = observed["documents"]
        doc_norm = [_norm(d["text"]) for d in docs]

        def expect(field: str, value: Any, label: str):
            allowed = value if isinstance(value, list) else [value]
            if observed.get(field) not in allowed:
                failures.append(f"{label}: expected {allowed}, got {observed.get(field)!r}")

        for a in case.get("assertions") or []:
            t, v = a.get("type"), a.get("value")
            if t == A.EXPECTED_STATUS.value:
                expect("status_code", v, t)
            elif t == A.EXPECTED_SUBCODE.value:
                expect("subcode", v, t)
            elif t == A.EXPECTED_PROCEDURE.value:
                expect("procedure", v, t)
            elif t == A.EXPECTED_INTENT.value:
                expect("intent", v, t)
            elif t == A.EXPECTED_COVERAGE_STATE.value:
                expect("coverage_state", v, t)
            elif t == A.MUST_INCLUDE_FACT.value:
                for item in (v if isinstance(v, list) else [v]):
                    if not any(_norm(item) in d for d in doc_norm):
                        failures.append(f"{t}: {item!r} missing")
            elif t == A.MUST_NOT_INCLUDE_FACT.value:
                for item in (v if isinstance(v, list) else [v]):
                    if any(_norm(item) in d for d in doc_norm):
                        failures.append(f"{t}: {item!r} present")
            elif t == A.EXPECTED_BUCKET.value:
                match = [d for d in docs if _norm(v["item"]) in _norm(d["text"])]
                if not match or match[0]["bucket"] != v["bucket"]:
                    failures.append(f"{t}: {v['item']!r} expected in {v['bucket']}, got "
                                    f"{match[0]['bucket'] if match else 'absent'}")
            elif t == A.SOURCE_MUST_BE.value:
                if not any(all(str(s.get(k)) == str(val) for k, val in (v or {}).items()) for s in observed["sources"]):
                    failures.append(f"{t}: no source matches {v}")
            elif t == A.SOURCE_MUST_NOT_BE.value:
                if any(all(str(s.get(k)) == str(val) for k, val in (v or {}).items()) for s in observed["sources"]):
                    failures.append(f"{t}: forbidden source {v} used")
            elif t == A.MUST_CLARIFY.value:
                if observed["coverage_state"] != "NEEDS_CLARIFICATION" or (v and v not in observed["clarify"]):
                    failures.append(f"{t}: expected clarification {v or ''}".strip())
            elif t == A.MUST_NOT_CLARIFY.value:
                if observed["coverage_state"] == "NEEDS_CLARIFICATION":
                    failures.append(f"{t}: unexpected clarification")
            elif t == A.MUST_RECORD_GAP.value:
                if not observed["gap_reason"] or (v and observed["gap_reason"] not in (v if isinstance(v, list) else [v])):
                    failures.append(f"{t}: expected gap {v or ''}, got {observed['gap_reason']!r}")
            elif t == A.MUST_NOT_RECORD_GAP.value:
                if observed["gap_reason"]:
                    failures.append(f"{t}: unexpected gap {observed['gap_reason']}")
            elif t == A.MUST_NOT_CLAIM_CERTAINTY.value:
                if "forbidden_certainty" in observed["guard_checks"] or "claims_official_confirmation" in observed["guard_checks"]:
                    failures.append(t)
            elif t == A.MUST_NOT_LEAK_INTERNAL_METADATA.value:
                if "internal_metadata_leak" in observed["guard_checks"] or "unsafe_html" in observed["guard_checks"]:
                    failures.append(t)
            elif t == A.MUST_NOT_LEAK_MODEL_PROVIDER.value:
                if "provider_model_leak" in observed["guard_checks"]:
                    failures.append(t)
            elif t == A.LANGUAGE_EXPECTED.value:
                if observed.get("locale") and observed["locale"] != v:
                    failures.append(f"{t}: expected {v}, got {observed['locale']}")
            else:
                failures.append(f"unknown assertion type {t}")
        return failures

    def run(self, *, selector: str = "all", persist: bool = True) -> Dict[str, Any]:
        """selector: 'all' | 'tag:<tag>' | '<case_key>'. Only approved cases run."""
        cases = self.list_cases(state="approved")
        if selector.startswith("tag:"):
            cases = [c for c in cases if selector[4:] in (c.get("tags") or [])]
        elif selector != "all":
            cases = [c for c in cases if c["case_key"] == selector]
        run_id = new_id("er")
        started = utc_now()
        results = []
        for case in cases:
            observed = self.observe_case(case)
            failures = self.evaluate(case, observed)
            results.append({"case_id": case["case_id"], "case_key": case["case_key"], "passed": not failures,
                            "failures": failures, "observed": observed})
        passed = sum(1 for r in results if r["passed"])
        if persist:
            with self.store.transaction():
                self.store.execute(
                    "INSERT INTO eval_runs(run_id, started_at, finished_at, selector, mode, total, passed, failed,"
                    " knowledge_revision) VALUES (?,?,?,?,?,?,?,?,?)",
                    (run_id, started, utc_now(), selector, "offline", len(results), passed, len(results) - passed,
                     self.store.revision()))
                for r in results:
                    self.store.execute(
                        "INSERT INTO eval_results(run_id, case_id, passed, failures, observed) VALUES (?,?,?,?,?)",
                        (run_id, r["case_id"], int(r["passed"]), json.dumps(r["failures"], ensure_ascii=False),
                         json.dumps(r["observed"], ensure_ascii=False)))
        logger.info("knowledge_eval_run selector=%s total=%d passed=%d", selector, len(results), passed)
        return {"run_id": run_id, "selector": selector, "mode": "offline", "total": len(results),
                "passed": passed, "failed": len(results) - passed, "results": results}


def report_text(run: Dict[str, Any]) -> str:
    lines = [f"Waymaker knowledge eval — {run['selector']} ({run['mode']})",
             f"  total {run['total']}  passed {run['passed']}  failed {run['failed']}"]
    for r in run["results"]:
        if not r["passed"]:
            lines.append(f"  FAIL {r['case_key']}")
            lines.extend(f"       - {f}" for f in r["failures"])
    return "\n".join(lines)
