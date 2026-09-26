"""Reference ingestion adapters over existing repository data.

Each adapter turns an existing file into ``FactProposal`` dicts (or source
rows). None of them edits the file it reads.

=====================  ====================================================
adapter                what it reads -> what it produces
=====================  ====================================================
source_registry        data/source_registry.json + data/manual_approval_index.json
                       -> sources / source_versions (identity stays in the registry)
legacy_grounding       backend/data/manual_grounding/stay_manual_grounding_2026_05.json
                       -> PUBLISHED facts, reviewer kind
                          ``legacy_repository_verification`` (the file records
                          a human page recheck: ``verified_locally``)
status_guidance        data/status-guidance-202609.json (2026.9, UNREVIEWED)
                       -> HUMAN_REVIEW_REQUIRED proposals, never published here
extraction_json        a JSON list produced by an AI/parser extractor
                       -> AI_EXTRACTED proposals (the AI-extraction contract)
=====================  ====================================================
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from services import structured_answer as _structured_answer

from .ingestion import IngestionService
from .models import (
    ActorKind,
    ConditionKind,
    FactOrigin,
    FactProperty,
    LifecycleState,
    RequirementLevel,
    SourceRefreshState,
    parent_code,
)
from . import paths as _paths
from .repository import KnowledgeRepository
from .review import ReviewService

logger = logging.getLogger("paradiso.knowledge")

REPO_ROOT = _paths.REPO_ROOT
# Repository-root files resolve to their backend/data deploy copy when the
# root is not in the build context (Railway Root Directory = backend).
SOURCE_REGISTRY_PATH = _paths.repo_data_path("data/source_registry.json", "knowledge_deploy/source_registry.json")
APPROVAL_INDEX_PATH = _paths.repo_data_path("data/manual_approval_index.json",
                                            "knowledge_deploy/manual_approval_index.json")
LEGACY_GROUNDING_PATH = _paths.BACKEND_DIR / "data" / "manual_grounding" / "stay_manual_grounding_2026_05.json"
STATUS_GUIDANCE_PATH = _paths.repo_data_path("data/status-guidance-202609.json",
                                             "knowledge_deploy/status-guidance-202609.json")
# Not copied into the deploy context (3 MB; Studio evidence / page counts only).
MANUAL_CORPUS_DIR = REPO_ROOT / "data" / "manual-corpus"

LEGACY_ACTOR = "legacy:stay_manual_grounding_2026_05.json"

# Registry family -> knowledge source identity.
_FAMILIES = {
    "stay_manual": ("stay_guide_manual", "외국인체류 안내매뉴얼", "Foreigner Stay/Residence Guide Manual", "stay"),
    "visa_manual": ("visa_issuance_manual", "사증발급 안내매뉴얼", "Visa Issuance Guide Manual", "visa"),
    "dongpo_manual": ("dongpo_manual", "재외동포 안내매뉴얼", "Overseas Korean Guide Manual", "stay"),
}
_REGISTRY_STATUS = {"active": "active", "deprecated": "superseded", "needs_manual_review": "staged"}
_LEGACY_TASK_PROCEDURE = {"체류기간 연장허가": "extension"}


def _family_of(registry_id: str) -> Optional[Tuple[str, str, str, str]]:
    for prefix, spec in _FAMILIES.items():
        if registry_id.startswith(prefix):
            return spec
    return None


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# =============================================================================
# 1. Source registry sync
# =============================================================================
def sync_source_registry(repo: KnowledgeRepository, *, actor: str = "registry-sync") -> Dict[str, int]:
    """Mirror manual editions from the registry. Idempotent."""
    registry = _load(SOURCE_REGISTRY_PATH).get("sources") or []
    try:
        approvals = (_load(APPROVAL_INDEX_PATH).get("documents") or {})
    except (OSError, ValueError):
        approvals = {}
    if isinstance(approvals, list):
        approvals = {str(d.get("source_id") or d.get("id")): d for d in approvals}
    created = updated = 0
    id_map: Dict[str, str] = {}
    for entry in registry:
        rid = str(entry.get("id") or "")
        spec = _family_of(rid)
        status = _REGISTRY_STATUS.get(str(entry.get("status") or ""))
        if not spec or not status:
            continue
        source_key, title_ko, title_en, family = spec
        source_id, _ = repo.upsert_source(
            source_key=source_key, title_ko=title_ko, title_en=title_en,
            issuing_body=str(entry.get("authority") or ""), authority_type="approved_manual",
            procedure_family=family, official_url="https://www.hikorea.go.kr/", registry_ref=source_key,
            actor=actor,
        )
        approval = approvals.get(rid) or {}
        state = str(approval.get("approval_state") or "").lower()
        review_state = {"approved": "approved", "rejected": "rejected"}.get(state, "needs_review")
        version_id, is_new = repo.upsert_source_version(
            source_id=source_id, edition_ref=rid, version_label=str(entry.get("version") or ""),
            status=status, content_review_state=review_state,
            revision_date=_date_from_id(rid),
            # Effective date only when the approval record states one; never inferred.
            effective_from=approval.get("effective_date") or None,
            content_sha256=entry.get("last_known_hash") or approval.get("source_sha256") or None,
            artifact_ref=str(entry.get("local_path") or ""), official_url=str(entry.get("url") or ""),
            page_count=_corpus_page_count(rid), actor=actor,
        )
        id_map[rid] = version_id
        created += int(is_new)
        updated += int(not is_new)
    # Version lineage (registry superseded_by -> supersedes_version_id).
    for entry in registry:
        rid, successor = str(entry.get("id") or ""), entry.get("superseded_by")
        if rid in id_map and successor in id_map:
            repo.store.execute(
                "UPDATE source_versions SET supersedes_version_id = ? WHERE source_version_id = ?"
                " AND supersedes_version_id IS NULL", (id_map[rid], id_map[successor]))
    return {"created": created, "existing": updated}


def _date_from_id(rid: str) -> Optional[str]:
    m = re.search(r"(20\d\d)_(\d\d)_(\d\d)", rid)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def _corpus_page_count(rid: str) -> Optional[int]:
    path = MANUAL_CORPUS_DIR / f"{rid}.json"
    if not path.is_file():
        return None
    try:
        pages = _load(path)
        return max(int(p.get("page") or 0) for p in pages) or None
    except (OSError, ValueError, TypeError):
        return None


def evaluate_source_refresh(repo: KnowledgeRepository, *, actor: str = "refresh-evaluator") -> List[Dict[str, Any]]:
    """Mark a source ``refresh_due`` when published facts cite a superseded edition
    while a newer approved edition exists. Never age-based (no repository
    refresh interval is defined)."""
    flagged = []
    for src in repo.list_sources():
        versions = src["versions"]
        approved_active = [v for v in versions if v["status"] == "active" and v["content_review_state"] == "approved"]
        stale = [v for v in versions if v["status"] == "superseded" and v.get("published_fact_count")]
        state = SourceRefreshState.REFRESH_DUE.value if (approved_active and stale) else SourceRefreshState.CURRENT.value
        if src["refresh_state"] in ("superseded", "unavailable"):
            continue
        if state != src["refresh_state"]:
            repo.set_source_refresh_state(
                src["source_id"], state, actor=actor, actor_kind=ActorKind.SYSTEM.value,
                reason=("published facts cite a superseded edition; a newer approved edition exists"
                        if state == "refresh_due" else "all published facts cite a current edition"))
        if state == "refresh_due":
            flagged.append({"source_key": src["source_key"],
                            "stale_editions": [v["edition_ref"] for v in stale],
                            "current_editions": [v["edition_ref"] for v in approved_active]})
    return flagged


# =============================================================================
# 2. Legacy verified grounding (the seed)
# =============================================================================
def _pages(page_range: str) -> Tuple[Optional[int], Optional[int]]:
    nums = [int(n) for n in re.findall(r"\d+", str(page_range or ""))]
    if not nums:
        return None, None
    return nums[0], (nums[1] if len(nums) > 1 else nums[0])


def _doc_level(text: str) -> RequirementLevel:
    """Same bucketing the structured answer renderer uses (single source of truth)."""
    buckets = _structured_answer.bucket_documents([text])
    for key in ("common", "required", "conditional", "additional"):
        if buckets.get(key):
            return RequirementLevel(key)
    return RequirementLevel.REQUIRED


def _note_key(text: str) -> str:
    return "note:" + hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()[:12]


def legacy_grounding_proposals(repo: KnowledgeRepository) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """(proposal_dict, variant_attributes) pairs for every legacy grounding item."""
    bundle = _load(LEGACY_GROUNDING_PATH)
    src_file = str(bundle.get("source_file") or "")
    version = _legacy_source_version(repo, bundle, src_file)
    out: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for entry in bundle.get("groundings") or []:
        procedure = _LEGACY_TASK_PROCEDURE.get(entry.get("procedure_type"))
        if not procedure:
            continue
        legacy = {k: v for k, v in entry.items() if k not in ("required_documents", "caveats")}
        attrs = {"legacy_grounding": legacy}
        page_start, page_end = _pages(entry.get("page_range"))
        base = {
            "status_code": entry["visa_code"], "subcode": entry.get("visa_sub_code"),
            "subcodes_covered": entry.get("sub_codes_covered") or [], "procedure": procedure,
            "scenario": entry.get("scenario") or "general", "section_title": entry.get("section") or "",
            "authority_type": "approved_manual", "origin": FactOrigin.LEGACY_REPOSITORY_VERIFIED.value,
        }
        loc = {"source_version_id": version, "section_title": entry.get("section") or "",
               "page_start": page_start, "page_end": page_end, "locator": "제출서류"}
        for i, doc in enumerate(entry.get("required_documents") or []):
            level = _doc_level(doc)
            out.append(({**base, "property": FactProperty.REQUIRED_DOCUMENT.value, "value_text": doc,
                         "requirement_level": level.value,
                         "condition_kind": (ConditionKind.CONDITIONAL.value if level == RequirementLevel.CONDITIONAL
                                            else ConditionKind.ALWAYS.value),
                         "sort_order": i, "location": loc}, attrs))
        for i, note in enumerate(entry.get("caveats") or []):
            out.append(({**base, "property": FactProperty.PROCEDURAL_NOTE.value, "value_text": note,
                         "item_key": _note_key(note), "sort_order": i,
                         "location": {**loc, "locator": "유의사항"}}, attrs))
    return out


def _legacy_source_version(repo: KnowledgeRepository, bundle: Dict[str, Any], src_file: str) -> str:
    registry = _load(SOURCE_REGISTRY_PATH).get("sources") or []
    rid = next((str(e["id"]) for e in registry if str(e.get("local_path") or "") == src_file), "")
    if rid:
        row = repo.find_source_version("stay_guide_manual", rid)
        if row:
            if not row.get("content_sha256") and bundle.get("source_file_sha256"):
                repo.store.execute("UPDATE source_versions SET content_sha256 = ? WHERE source_version_id = ?",
                                   (bundle["source_file_sha256"], row["source_version_id"]))
            return row["source_version_id"]
    # Registry without the edition (should not happen in this repo): register it.
    source_id, _ = repo.upsert_source(source_key="stay_guide_manual", title_ko=bundle.get("source_title") or "",
                                      authority_type="approved_manual", procedure_family="stay",
                                      issuing_body=bundle.get("issuing_body") or "")
    version_id, _ = repo.upsert_source_version(
        source_id=source_id, edition_ref=rid or Path(src_file).stem, version_label=bundle.get("source_date") or "",
        status="active", revision_date=bundle.get("source_revision_date"),
        content_sha256=bundle.get("source_file_sha256"), artifact_ref=src_file)
    return version_id


def seed_legacy(repo: KnowledgeRepository) -> Dict[str, int]:
    """Import + publish the legacy verified grounding. Idempotent.

    Publication runs under ``legacy_import`` actor kind, which the lifecycle
    only accepts for facts whose origin is ``legacy_repository_verified``.
    """
    ingestion = IngestionService(repo)
    review = ReviewService(repo)
    published = existing = 0
    for proposal, attrs in legacy_grounding_proposals(repo):
        validated, errors, _ = ingestion.validate(proposal)
        if validated is None:
            logger.error("knowledge_seed_invalid errors=%s", errors)
            continue
        fact_id, created = repo.insert_proposal(
            validated, created_by=LEGACY_ACTOR, created_by_kind=ActorKind.LEGACY_IMPORT.value,
            initial_state=LifecycleState.HUMAN_REVIEW_REQUIRED, locator_verified=True,
            verification_note=str((attrs.get("legacy_grounding") or {}).get("verification_note") or ""),
            variant_attributes=attrs, legacy_ref=str((attrs.get("legacy_grounding") or {}).get("grounding_id") or ""),
        )
        fact = repo.get_fact(fact_id)
        if fact["lifecycle_state"] != LifecycleState.HUMAN_REVIEW_REQUIRED.value:
            existing += 1
            continue
        reason = "pre-platform repository verification (source_verification_status=verified_locally)"
        with repo.store.transaction():
            repo.transition(fact_id, LifecycleState.HUMAN_REVIEWED, actor=LEGACY_ACTOR,
                            actor_kind=ActorKind.LEGACY_IMPORT.value, reason=reason)
            repo.transition(fact_id, LifecycleState.VERIFIED, actor=LEGACY_ACTOR,
                            actor_kind=ActorKind.LEGACY_IMPORT.value, reason=reason)
            if repo.published_for_slot(fact["slot_key"]):
                # Never displace a Studio-published successor on re-seed.
                existing += 1
                continue
            review.publish(fact_id, actor=LEGACY_ACTOR, actor_kind=ActorKind.LEGACY_IMPORT.value, reason=reason)
        published += int(created)
    return {"published": published, "existing": existing}


def bootstrap(repo: KnowledgeRepository) -> Dict[str, Any]:
    """Runtime bootstrap: registry sync + legacy seed + refresh evaluation.

    Safe on every process start (idempotent). It never imports unreviewed
    proposals — those are an explicit operator action.
    """
    registry = sync_source_registry(repo)
    seed = seed_legacy(repo)
    refresh = evaluate_source_refresh(repo)
    logger.info("knowledge_bootstrap registry=%s seed=%s refresh_due=%d", registry, seed, len(refresh))
    return {"registry": registry, "seed": seed, "refresh_due": refresh}


# =============================================================================
# 3. 2026.9 status guidance (unreviewed) -> review proposals
# =============================================================================
_LEVEL_MAP = {
    "REQUIRED_BASELINE": None,                        # common/required by base-doc rule
    "CONDITIONAL_REQUIRED": RequirementLevel.CONDITIONAL,
    "ADDITIONAL_IF_APPLICABLE": RequirementLevel.CONDITIONAL,
    "ALTERNATIVE_DOCUMENT": RequirementLevel.CONDITIONAL,
    "PREVIOUSLY_SUBMITTED_MAY_BE_OMITTED": RequirementLevel.CONDITIONAL,
    "MAY_BE_REQUESTED_BY_OFFICER": RequirementLevel.ADDITIONAL,
    "ADMIN_INFO_CHECKABLE": RequirementLevel.REQUIRED,
}
_SKIP_LEVELS = {"SOURCE_MENTIONS_BUT_NOT_STRUCTURED", "NOT_APPLICABLE", "LEGACY_ONLY"}


def status_guidance_proposals(
    repo: KnowledgeRepository,
    *,
    statuses: Optional[Sequence[str]] = None,
    procedures: Sequence[str] = ("extension",),
) -> List[Dict[str, Any]]:
    data = _load(STATUS_GUIDANCE_PATH)
    sources = data.get("sources") or {}
    wanted = {s.upper() for s in statuses} if statuses else None
    out: List[Dict[str, Any]] = []
    for entry in data.get("guidance") or []:
        target, procedure = str(entry.get("target") or ""), str(entry.get("procedure") or "")
        if procedure not in procedures or entry.get("scenario"):
            continue
        parent = parent_code(target)
        if wanted and parent not in wanted and target not in wanted:
            continue
        src = entry.get("source") or {}
        edition = sources.get(src.get("manual")) or {}
        rid = str(edition.get("corpus_source_id") or "")
        family = "stay_guide_manual" if edition.get("domain") == "stay" else "visa_issuance_manual"
        version = repo.find_source_version(family, rid)
        if not version:
            continue
        is_sub = target != parent
        covered = [target, *[a for a in entry.get("aliases") or [] if a.startswith(parent + "-")]] if is_sub else []
        subcode, covered = _resolve_variant_scope(repo, parent, target if is_sub else None, procedure, covered)
        for i, doc in enumerate(entry.get("documents") or []):
            level_code = str(doc.get("requirement_level") or "")
            if level_code in _SKIP_LEVELS:
                continue
            name = " ".join(str(doc.get("name_ko") or "").split())
            if not name:
                continue
            level = _LEVEL_MAP.get(level_code) or _doc_level(name)
            condition = doc.get("applies_when_ko") or (
                f"생략 가능: {doc['does_not_apply_when_ko']}" if doc.get("does_not_apply_when_ko") else "")
            dsrc = doc.get("source") or {}
            translations = {"en": doc["name_en"]} if doc.get("name_en") else {}
            warnings = []
            if dsrc.get("pdf_page") and src.get("pdf_page") and dsrc["pdf_page"] < src["pdf_page"]:
                warnings.append("document anchor resolves before the section heading; verify the page")
            out.append({
                "status_code": parent, "subcode": subcode, "subcodes_covered": covered,
                "procedure": procedure, "scenario": "general", "section_title": str(src.get("section") or ""),
                "property": FactProperty.REQUIRED_DOCUMENT.value, "value_text": name,
                "requirement_level": level.value,
                "condition_kind": (ConditionKind.CONDITIONAL.value if level == RequirementLevel.CONDITIONAL
                                   else ConditionKind.ALWAYS.value),
                "condition_text": str(condition or "")[:1000],
                "display_translations": translations, "sort_order": i,
                "authority_type": "approved_manual", "origin": FactOrigin.PARSER_EXTRACTION.value,
                "extraction_warnings": warnings + [f"source review_state={doc.get('review_state')}"],
                "location": {
                    "source_version_id": version["source_version_id"], "section_title": str(src.get("section") or ""),
                    "page_start": dsrc.get("pdf_page") or src.get("pdf_page"),
                    "page_end": dsrc.get("pdf_page") or src.get("pdf_page"),
                    "locator": f"hwp_line:{dsrc.get('hwp_line')}" if dsrc.get("hwp_line") else "",
                },
            })
    return out


def _resolve_variant_scope(repo: KnowledgeRepository, parent: str, subcode: Optional[str], procedure: str,
                           covered: List[str]) -> Tuple[Optional[str], List[str]]:
    """Map a sub-code-targeted entry onto an existing parent-level variant that
    explicitly covers it (no flattening); otherwise keep it sub-code-scoped."""
    if not subcode:
        return None, []
    for variant in repo.variants_for(parent, procedure):
        if variant.get("subcode") is None and subcode in (variant.get("subcodes_covered") or []):
            return None, list(variant["subcodes_covered"])
    return subcode, covered


# =============================================================================
# 4. AI / parser extraction output (the extraction contract)
# =============================================================================
EXTRACTION_REQUIRED_KEYS = ("status_code", "procedure", "property", "value_text", "location")


def extraction_json_proposals(path: Path | str, *, origin: str = FactOrigin.AI_EXTRACTION.value) -> List[Dict[str, Any]]:
    """Read an extractor's JSON output. Every record is forced to the given origin
    (AI output can never self-declare as operator or legacy-verified)."""
    records = _load(Path(path))
    if isinstance(records, dict):
        records = records.get("proposals") or []
    out = []
    for rec in records:
        rec = dict(rec or {})
        rec["origin"] = origin
        rec.pop("lifecycle_state", None)
        rec.pop("verified_by", None)
        out.append(rec)
    return out


def iter_all_legacy_items(repo: KnowledgeRepository) -> Iterable[Dict[str, Any]]:
    return (p for p, _ in legacy_grounding_proposals(repo))
