"""Knowledge platform facade used by /api/ask, the operator API and the evals.

Runtime flow (docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md §Runtime):

    question -> understanding (existing detectors) -> retrieval (published facts)
      -> coverage decision -> answer plan -> deterministic facts
      -> optional model summary -> Answer Guard -> structured response -> UI
      -> observation / coverage gap (privacy-minimized)

``grounding_for`` keeps the legacy ``_select_grounding`` contract (same dict
shape, same sub-code rules) but reads PUBLISHED knowledge instead of the
legacy JSON file, so every existing consumer (prompt builder, structured
answer, source card) now draws from the canonical store without a rewrite.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from services import structured_answer as _structured_answer

from . import adapters, guard as guard_mod
from .conflicts import open_conflicts_for_slots
from .coverage import CoverageDecision, decide
from .ingestion import IngestionService
from .learning import LearningService
from .models import KNOWLEDGE_PLATFORM_VERSION, Intent
from .repository import KnowledgeRepository
from .retrieval import RetrievalResult, RetrievalService
from .review import ReviewService
from .store import KnowledgeStore, utc_now
from .understanding import GROUNDABLE_TASKS, QueryUnderstanding, understand

logger = logging.getLogger("paradiso.knowledge")


# ---------------------------------------------------------------------------
# Detector injection (the backend owns detection; no second router here)
# ---------------------------------------------------------------------------
@dataclass
class Detectors:
    detect_codes: Callable[..., Tuple[Optional[str], Optional[str]]]
    detect_task: Callable[[str], Optional[str]]
    risk_for_task: Callable[[Optional[str]], str]


_DETECTORS: Optional[Detectors] = None


def register_detectors(detect_codes, detect_task, risk_for_task) -> None:
    global _DETECTORS
    _DETECTORS = Detectors(detect_codes, detect_task, risk_for_task)


def detectors() -> Detectors:
    if _DETECTORS is None:
        import paradiso_backend  # noqa: F401  (registers its detectors on import)
    assert _DETECTORS is not None, "paradiso_backend did not register its detectors"
    return _DETECTORS


# ---------------------------------------------------------------------------
@dataclass
class AnswerPlan:
    query: str
    understanding: QueryUnderstanding
    retrieval: Optional[RetrievalResult]
    decision: CoverageDecision
    grounding: Optional[Dict[str, Any]] = None
    bundle: Dict[str, Any] = field(default_factory=dict)
    structured: Optional[Dict[str, Any]] = None
    guard: Optional[Dict[str, Any]] = None
    observation: Dict[str, Optional[str]] = field(default_factory=dict)

    def internal(self) -> Dict[str, Any]:
        """Diagnostics-only view. Never part of the public /api/ask payload."""
        return {
            "version": KNOWLEDGE_PLATFORM_VERSION,
            "understanding": self.understanding.to_dict(),
            "coverage": self.decision.to_dict(),
            "retrieval": self.retrieval.internal() if self.retrieval else None,
            "guard": self.guard,
            "observation_id": self.observation.get("observation_id"),
            "gap_id": self.observation.get("gap_id"),
        }


class KnowledgePlatform:
    def __init__(self, store: KnowledgeStore):
        self.store = store
        self.repo = KnowledgeRepository(store)
        self.retrieval = RetrievalService(self.repo)
        self.review = ReviewService(self.repo)
        self.ingestion = IngestionService(self.repo, self.review)
        self.learning = LearningService(store)
        from .evals import EvalService  # local import: evals depends on this module
        self.evals = EvalService(self)
        self.bootstrap_report: Dict[str, Any] = {}

    @classmethod
    def create(cls, path: Optional[str] = None, *, bootstrap: bool = True) -> "KnowledgePlatform":
        platform = cls(KnowledgeStore(path))
        if bootstrap:
            platform.bootstrap_report = adapters.bootstrap(platform.repo)
            try:
                platform.evals.import_seed_corpus()
            except Exception as exc:  # pragma: no cover - evals must not block runtime
                logger.warning("knowledge_eval_seed_failed error=%s", type(exc).__name__)
        return platform

    # ------------------------------------------------------------------
    def grounding_for(self, status_code: Optional[str], task_type: Optional[str],
                      subcode: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Legacy ``_select_grounding`` contract over published knowledge."""
        procedure = GROUNDABLE_TASKS.get(task_type or "")
        if not status_code or not procedure:
            return None
        result = self.retrieval.retrieve(status_code=status_code, subcode=subcode, procedure=procedure,
                                         intent=Intent.REQUIRED_DOCUMENTS.value)
        if not result.document_facts:
            return None
        grounding, _bundle = to_grounding(result)
        return grounding

    # ------------------------------------------------------------------
    def plan(self, query: str, *, payload_code: Optional[str] = None, visa_data: Optional[Dict[str, Any]] = None,
             lang: Optional[str] = None, legal_issue_types: Optional[List[str]] = None,
             detected: Optional[Tuple[Optional[str], Optional[str], Optional[str], str]] = None,
             build_structured: bool = True) -> AnswerPlan:
        """Understanding -> retrieval -> coverage (-> structured facts)."""
        if detected is None:
            det = detectors()
            top, sub = det.detect_codes(payload_code, visa_data, query)
            task = det.detect_task(query)
            detected = (top, sub, task, det.risk_for_task(task))
        top, sub, task, risk = detected
        u = understand(query, status_code=top, subcode=sub, task_type=task, risk_level=risk, lang=lang,
                       legal_issue_types=legal_issue_types)
        retrieval: Optional[RetrievalResult] = None
        failed = False
        try:
            if u.status_code and u.retrieval_procedure:
                retrieval = self.retrieval.retrieve(status_code=u.status_code, subcode=u.subcode,
                                                    procedure=u.retrieval_procedure, intent=u.intent)
        except Exception as exc:  # RETRIEVAL_FAILED is not "no knowledge"
            logger.warning("knowledge_retrieval_failed error=%s", type(exc).__name__)
            failed = True
        statuses = []
        if u.missing_decisive_facts and u.retrieval_procedure:
            statuses = [r["status_code"] for r in self.store.all(
                "SELECT DISTINCT v.status_code FROM procedure_variants v JOIN knowledge_facts f USING(variant_id)"
                " WHERE v.procedure = ? AND f.lifecycle_state = 'PUBLISHED'", (u.retrieval_procedure,))]
        decision = decide(u, retrieval, retrieval_failed=failed, statuses_with_knowledge=statuses)
        plan = AnswerPlan(query=query, understanding=u, retrieval=retrieval, decision=decision)
        if retrieval is not None and retrieval.document_facts:
            plan.grounding, plan.bundle = to_grounding(retrieval)
            if build_structured and u.intent == Intent.REQUIRED_DOCUMENTS.value and decision.state in (
                    "DIRECT_VERIFIED", "VERIFIED_WITH_CONDITIONS", "CONFLICTING_SOURCES"):
                plan.structured = self.structured_answer(plan, lang)
        return plan

    def structured_answer(self, plan: AnswerPlan, lang: Optional[str]) -> Optional[Dict[str, Any]]:
        if not plan.grounding:
            return None
        structured = _structured_answer.build_document_answer(grounding=plan.grounding, bundle=plan.bundle,
                                                              lang=lang)
        if structured and plan.retrieval is not None and plan.retrieval.conflicts:
            structured = apply_conflict_view(structured, plan.retrieval, self.repo)
        return structured

    # ------------------------------------------------------------------
    def check_summary(self, plan: AnswerPlan, text: str, *, lang: Optional[str],
                      summary_only: bool = True) -> guard_mod.GuardResult:
        r = plan.retrieval
        pages: List[int] = []
        for src in (r.sources if r else []):
            if src.get("page_min"):
                pages.extend(range(int(src["page_min"]), int(src.get("page_max") or src["page_min"]) + 1))
        result = guard_mod.check(
            text, language=lang or plan.understanding.query_language,
            verified_facts=(r.facts if r else []), coverage_state=plan.decision.state,
            status_code=plan.understanding.status_code,
            user_mentioned_statuses=plan.understanding.mentioned_statuses,
            procedure_family="stay" if plan.understanding.procedure not in ("visa_issuance",) else "visa",
            cited_pages=pages, summary_only=summary_only)
        plan.guard = result.to_dict()
        if result.findings:
            logger.info("knowledge_answer_guard outcome=%s checks=%s", result.outcome,
                        ",".join(sorted({f.check for f in result.findings})))
        return result

    def observe(self, plan: AnswerPlan, *, raw_query: str) -> Dict[str, Optional[str]]:
        outcome = (plan.guard or {}).get("outcome", "not_run")
        if outcome == "blocked" and not plan.decision.gap_reason:
            # A guard failure on generated text is itself a quality signal.
            plan.decision.gap_reason = "ANSWER_GUARD_FAILURE"
        plan.observation = self.learning.record_observation(
            plan.understanding, plan.decision, raw_query=raw_query, guard_outcome=outcome,
            fact_ids=plan.retrieval.fact_ids if plan.retrieval else [])
        return plan.observation

    # ------------------------------------------------------------------
    def overview(self) -> Dict[str, Any]:
        counts = self.repo.state_counts()
        pending = sum(counts.get(s, 0) for s in ("DRAFT", "AI_EXTRACTED", "HUMAN_REVIEW_REQUIRED",
                                                  "HUMAN_REVIEWED", "VERIFIED"))
        last_run = self.store.one("SELECT * FROM eval_runs ORDER BY started_at DESC LIMIT 1")
        sources = self.repo.list_sources()
        return {
            "version": KNOWLEDGE_PLATFORM_VERSION,
            "schema_version": self.store.schema_version(),
            "storage": {"durable": self.store.durable, "open_error": self.store.open_error},
            "facts_by_state": counts,
            "metrics": {
                "pending_review": pending,
                "open_review_tasks": (self.store.one(
                    "SELECT COUNT(*) FROM review_tasks WHERE status IN ('open','needs_evidence')") or [0])[0],
                "open_conflicts": (self.store.one(
                    "SELECT COUNT(*) FROM knowledge_conflicts WHERE status = 'open'") or [0])[0],
                "published_facts": counts.get("PUBLISHED", 0),
                "superseded_facts": counts.get("SUPERSEDED", 0),
                "failing_eval_cases": (last_run["failed"] if last_run else None),
                "sources_needing_refresh": sum(1 for s in sources if s["refresh_state"] == "refresh_due"),
                **self.learning.metrics(),
            },
            "last_eval_run": dict(last_run) if last_run else None,
            "sources_needing_refresh": [
                {"source_key": s["source_key"], "title": s["title_ko"],
                 "stale_editions": [v["edition_ref"] for v in s["versions"]
                                    if v["status"] == "superseded" and v.get("published_fact_count")],
                 "current_editions": [v["edition_ref"] for v in s["versions"]
                                      if v["status"] == "active" and v["content_review_state"] == "approved"]}
                for s in sources if s["refresh_state"] == "refresh_due"],
        }

    def export_published(self) -> Dict[str, Any]:
        """Portable snapshot of PUBLISHED knowledge (no review metadata, no internal paths)."""
        facts = self.repo.facts_where("f.lifecycle_state = 'PUBLISHED'", limit=100000)
        out = []
        for f in facts:
            out.append({
                "lineage_id": f["lineage_id"], "version_no": f["version_no"],
                "status_code": f["status_code"], "subcode": f.get("subcode"),
                "subcodes_covered": f.get("subcodes_covered") or [], "procedure": f["procedure"],
                "scenario": f["scenario"], "property": f["property"], "item_key": f["item_key"],
                "value_text": f["value_text"], "value": f.get("value_json") or {},
                "condition_kind": f["condition_kind"], "condition_text": f["condition_text"],
                "display_translations": f.get("display_translations") or {},
                "authority_type": f["authority_type"], "effective_from": f.get("effective_from"),
                "effective_to": f.get("effective_to"), "published_at": f["published_at"],
                "citations": [{"source": c["source_title"], "edition": c["version_label"],
                               "issuing_body": c["issuing_body"], "section": c["section_title"],
                               "page_start": c["page_start"], "page_end": c["page_end"], "locator": c["locator"],
                               "official_url": c.get("version_url") or ""} for c in f["citations"]],
            })
        return {"format": "waymaker-published-knowledge/1", "exported_at": utc_now(),
                "platform_version": KNOWLEDGE_PLATFORM_VERSION, "fact_count": len(out), "facts": out}


# ---------------------------------------------------------------------------
# Legacy-shape adapter
# ---------------------------------------------------------------------------
def to_grounding(result: RetrievalResult) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Published facts -> the dict shape every legacy grounding consumer reads."""
    variant = result.variant or {}
    legacy = dict((variant.get("attributes") or {}).get("legacy_grounding") or {})
    docs = [f for f in result.document_facts]
    notes = [f for f in result.note_facts]
    sources = result.sources
    primary = sources[0] if sources else {}
    if len(sources) == 1:
        page_range = primary.get("pages") or ""
        edition = primary.get("edition") or ""
    else:
        page_range = "; ".join(f"{s['pages']} ({s['edition']})" for s in sources if s.get("pages"))
        edition = " / ".join(s["edition"] for s in sources)
    grounding = dict(legacy)
    grounding.update({
        "grounding_id": legacy.get("grounding_id") or variant.get("variant_key"),
        "visa_code": variant.get("status_code"),
        "visa_sub_code": variant.get("subcode"),
        "sub_codes_covered": legacy.get("sub_codes_covered", (variant.get("subcodes_covered") or None)),
        "procedure_type": variant.get("procedure_label_ko") or legacy.get("procedure_type"),
        "section": variant.get("section_title") or legacy.get("section") or "",
        "page_range": page_range,
        "source_verification_status": "verified_locally",
        "required_documents": [f["value_text"] for f in docs],
        # Structured view for the renderer (services.structured_answer). The
        # reviewed requirement level travels with the text.
        "required_document_entries": [_document_entry(f) for f in docs],
        "caveats": [f["value_text"] for f in notes],
    })
    grounding.setdefault("scenario", None if variant.get("scenario") == "general" else variant.get("scenario"))
    grounding.setdefault("source_confidence", "high")
    grounding.setdefault("source_excerpt", "")
    # Private, internal-only knowledge metadata (never serialized publicly).
    bundle = {
        "source_title": primary.get("title") or "",
        "source_date": edition,
        "issuing_body": primary.get("issuing_body") or "",
        "source_file": primary.get("artifact_ref") or "",
        "source_revision_date": primary.get("revision_date") or "",
    }
    grounding["_knowledge"] = {
        "variant_key": variant.get("variant_key"),
        "fact_ids": result.fact_ids,
        "freshness": result.freshness,
        "bundle": bundle,
        "source_version_ids": [s["source_version_id"] for s in sources],
    }
    return grounding, bundle


_LEVEL_REQUIREDNESS = {"common": "required", "required": "required", "conditional": "conditional",
                       "additional": "additional"}


def _document_entry(fact: Dict[str, Any]) -> Dict[str, Any]:
    level = str((fact.get("value_json") or {}).get("requirement_level") or "required")
    if fact.get("condition_kind") in ("conditional", "applicant_specific"):
        level = "conditional"
    return {"textKo": fact["value_text"], "requiredness": _LEVEL_REQUIREDNESS.get(level, "required"),
            "conditionKo": fact.get("condition_text") or ""}


def apply_conflict_view(structured: Dict[str, Any], result: RetrievalResult, repo: KnowledgeRepository) -> Dict[str, Any]:
    """Never pick a side silently: items in conflicting slots move to
    ``missing_or_unverified`` ("확인이 필요한 서류") with an explicit flag."""
    slots = {c["slot_key"] for c in result.conflicts}
    texts = {" ".join(f["value_text"].split()) for f in result.document_facts if f["slot_key"] in slots}
    docs = structured.get("required_documents") or {}
    moved = []
    for bucket in ("common", "required", "conditional", "additional"):
        keep = []
        for item in docs.get(bucket) or []:
            (moved if item.get("source_text") in texts else keep).append(item)
        docs[bucket] = keep
    docs["missing_or_unverified"] = list(docs.get("missing_or_unverified") or []) + moved
    flags = list(structured.get("uncertainty_flags") or [])
    locale = structured.get("locale") or "ko"
    flags.append({
        "ko": "일부 서류는 공식 자료 간 내용이 일치하지 않아 검토 중입니다. 제출 전 관할 출입국·외국인관서 또는 1345에 확인하세요.",
        "en": "Official sources disagree on some documents and they are under review. Confirm with the competent immigration office or 1345 before filing.",
    }.get("en" if locale == "en" else "ko"))
    structured["uncertainty_flags"] = flags
    return structured


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------
_PLATFORM: Optional[KnowledgePlatform] = None
_PLATFORM_LOCK = threading.Lock()


def get_platform() -> KnowledgePlatform:
    global _PLATFORM
    if _PLATFORM is not None:
        return _PLATFORM
    with _PLATFORM_LOCK:
        if _PLATFORM is None:
            try:
                _PLATFORM = KnowledgePlatform.create()
            except Exception as exc:
                # A broken DB file must not take answers down: rebuild in memory
                # from the committed seed and report non-durable storage.
                logger.error("knowledge_platform_init_failed error=%s — falling back to in-memory store",
                             type(exc).__name__)
                _PLATFORM = KnowledgePlatform.create(":memory:")
                _PLATFORM.store.open_error = type(exc).__name__
    return _PLATFORM


def set_platform_for_tests(platform: Optional[KnowledgePlatform]) -> None:
    global _PLATFORM
    _PLATFORM = platform


def platform_if_ready() -> Optional[KnowledgePlatform]:
    return _PLATFORM


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


__all__ = ["KnowledgePlatform", "AnswerPlan", "get_platform", "set_platform_for_tests", "register_detectors",
           "to_grounding", "open_conflicts_for_slots"]
