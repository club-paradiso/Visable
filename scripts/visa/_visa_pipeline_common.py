#!/usr/bin/env python3
"""Shared helpers for the visa-data authoring pipeline (extract / build / validate / diff).

This module is the single source of truth for:
  * the byte-exact serializer used for visa_data.json,
  * the authoring-file schema constants,
  * summary classification rules (Phase 3.5),
  * the lossless `reconstruct_record()` used by build (and by extract's
    self-check), so that round-tripping is provably byte-identical.

Design contract (why this is safe):
  visa_data.json is a flat JSON array. We verified that
      json.dumps(data, ensure_ascii=False, indent=2) + "\\n"
  reproduces the checked-in file byte-for-byte. Each authoring status file
  records the *exact original top-level key order* (`_authoring.keyOrder`)
  and, for every original key, exactly one *source* (`_authoring.keySource`).
  `reconstruct_record()` walks keyOrder and pulls each key's value from its
  declared source, so on a fresh extract (no human edits) build == original.

Nothing here modifies any file; callers do the I/O.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
VISA_DATA = REPO_ROOT / "visa_data.json"
BACKEND_MIRROR = REPO_ROOT / "backend" / "data" / "visas.json"
DOC_MASTER = REPO_ROOT / "doc_master.json"

AUTHORING_ROOT = REPO_ROOT / "backend" / "data" / "visa_authoring"
STATUSES_DIR = AUTHORING_ROOT / "statuses"
COMMON_DIR = AUTHORING_ROOT / "common"
AUDIT_DIR = AUTHORING_ROOT / "audit"

SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Field buckets
# ---------------------------------------------------------------------------

# Human-editable identity fields, emitted at the top of each authoring file in
# this preferred order when present in the original record.
IDENTITY_FIELDS: Tuple[str, ...] = (
    "code", "nameKo", "nameEn", "name", "cat", "period",
    "stayPeriodCap", "activityScope", "manualDomains",
    "aliases", "searchAliases",
)

# Audit / migration fields relocated out of the status file into consolidated
# audit/*.json files (keyed by code). They are script-only (no runtime
# frontend consumer) and are re-injected verbatim by build at their original
# key position. value = audit-file basename (without .json).
AUDIT_RELOCATED: Dict[str, str] = {
    "manualRequiredDocAudit": "manual_required_doc_audit",
    "_searchAliasAudit": "search_alias_audit",
    "structuredRequirementsRef": "structured_requirements_refs",
    "_source_notes": "source_notes",
    "migrationMeta": "migration_meta",
}

# Procedure inner keys that are authoring-only annotations (never emitted to
# the generated record).
PROC_AUTHORING_ONLY_KEYS = ("summaryQuality", "summaryCleanupStatus", "summaryHiddenInUi")

# Accepted enum values (mirrored by the validator).
REVIEW_STATUSES = {"verified", "needs_review", "partial", "deprecated", "legacy", "suspended"}
SUMMARY_QUALITIES = {
    "human_curated", "source_backed", "generated_legacy",
    "ocr_blob", "template_placeholder", "none",
}

# Banned generated-only fields at authoring top level (must live under
# _generated / audit files instead).
BANNED_TOPLEVEL_FIELDS = {
    "newReq", "newReqDocs", "extReq", "extReqDocs", "changeReq", "changeReqDocs",
    "initialReqDocs", "extensionReqDocs", "documents_initial",
    "documents_registration", "documents_extension", "faq",
    "manualRequiredDocAudit", "structuredRequirementsRef",
    "_source_notes", "_searchAliasAudit", "migrationMeta",
    "addReq", "addReqDocs",
}

# Generic UI boilerplate prefixes that disqualify a string from being a UI
# summary (Phase 3.5 / validator rule 14).
BOILERPLATE_PREFIXES = ("[입국 후", "[입국 전")

# OCR / manual-chunk artifact markers.
OCR_MARKERS = ("□", "■", "◇", "▶", "▷", "☞", "❍", "◦", "ㅁ")

SUMMARY_KEEP_MAX_LEN = 320  # conservative UI-summary length ceiling


# ---------------------------------------------------------------------------
# Serialization (byte-exact)
# ---------------------------------------------------------------------------

def dump_visa_json(data: Any) -> str:
    """Serialize exactly the way the checked-in visa_data.json is formatted."""
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def dump_authoring_json(data: Any) -> str:
    """Deterministic pretty JSON for authoring / audit files."""
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Summary classification (Phase 3.5)
# ---------------------------------------------------------------------------

def classify_summary(text: Any, proc_has_manual_refs: bool) -> Dict[str, Any]:
    """Classify one procedure summary.

    Returns a dict with: classification, summaryQuality, keep (bool — keep in
    the human-editable authoring view), summaryCleanupStatus, risk.

    Conservative rule: a summary is KEPT in the human authoring view only when
    it is concise, free of boilerplate/OCR/placeholder noise, AND its procedure
    is backed by manualRefs. Everything else is preserved verbatim in the
    generated compatibility layer (runtime is never changed) but removed from
    the human surface so editors are not asked to curate dummy text.
    """
    if not isinstance(text, str) or not text.strip():
        return _c("delete_safely", "none", False, "removed", "low")

    s = text.strip()

    if "DATA_MISSING" in s:
        return _c("delete_from_authoring_preserve_in_compat", "template_placeholder",
                  False, "compat_only", "low")

    if s.startswith(BOILERPLATE_PREFIXES):
        return _c("delete_from_authoring_preserve_in_compat", "generated_legacy",
                  False, "compat_only", "medium")

    if any(m in s for m in OCR_MARKERS) or len(s) > 450:
        return _c("move_to_source_excerpt_or_audit", "ocr_blob",
                  False, "compat_only", "medium")

    if len(s) <= SUMMARY_KEEP_MAX_LEN and proc_has_manual_refs:
        return _c("keep_source_backed_summary", "source_backed",
                  True, "kept", "low")

    # Concise-ish but no manual backing, or a bit long: preserve in compat,
    # flag for a human to write a clean curated summary later.
    return _c("needs_human_review", "generated_legacy",
              False, "compat_only", "medium")


def _c(classification: str, quality: str, keep: bool, cleanup_status: str, risk: str) -> Dict[str, Any]:
    return {
        "classification": classification,
        "summaryQuality": quality,
        "keep": keep,
        "summaryCleanupStatus": cleanup_status,
        "risk": risk,
    }


# ---------------------------------------------------------------------------
# Lossless reconstruction (build == original on fresh extract)
# ---------------------------------------------------------------------------

class BuildContext:
    """Shared inputs that build pulls referenced values from."""

    def __init__(self, fees: Dict[str, Any], warnings: Dict[str, Any],
                 audit: Dict[str, Dict[str, Any]]):
        self.fees = fees            # common/fees_2026_05.json content
        self.warnings = warnings    # common/common_warnings_2026_05.json content
        self.audit = audit          # {audit_basename: {code: value}}


def _rebuild_procedures(authoring: Dict[str, Any]) -> Dict[str, Any]:
    meta = authoring["_authoring"]
    removed = authoring.get("_generated", {}).get("removedSummaries", {})
    aproc = authoring.get("procedures", {})
    out: Dict[str, Any] = {}
    for name in meta["procOrder"]:
        src = aproc.get(name, {})
        ordered: Dict[str, Any] = {}
        for k in meta["procKeyOrder"][name]:
            if k == "summary":
                path = f"procedures.{name}.summary"
                if path in removed:
                    ordered["summary"] = removed[path]
                else:
                    ordered["summary"] = src["summary"]
            else:
                ordered[k] = src[k]
        out[name] = ordered
    return out


def reconstruct_record(authoring: Dict[str, Any], ctx: BuildContext) -> Dict[str, Any]:
    """Rebuild one original visa_data.json record from its authoring file."""
    meta = authoring["_authoring"]
    code = authoring["code"]
    compat = authoring.get("_generated", {}).get("compat", {})
    out: Dict[str, Any] = {}

    for key in meta["keyOrder"]:
        src = meta["keySource"][key]
        if src == "identity":
            out[key] = authoring[key]
        elif src == "manualRefs":
            out[key] = authoring["manualRefs"]
        elif src == "sourceManualStatus":
            out[key] = authoring["sourceManualStatus"]
        elif src == "subcodes":
            out[key] = authoring["subcodes"]
        elif src == "procedures":
            out[key] = _rebuild_procedures(authoring)
        elif src == "feeRef":
            out[key] = ctx.fees["feeInfo"]
        elif src == "warnRef":
            out[key] = ctx.warnings["commonWarnings"]
        elif src == "compat":
            out[key] = compat[key]
        elif src.startswith("audit:"):
            basename = src.split(":", 1)[1]
            out[key] = ctx.audit[basename][code]
        else:  # pragma: no cover - defensive
            raise ValueError(f"{code}: unknown keySource {src!r} for key {key!r}")
    return out


def load_build_context() -> BuildContext:
    fees = load_json(COMMON_DIR / "fees_2026_05.json")
    warnings = load_json(COMMON_DIR / "common_warnings_2026_05.json")
    audit: Dict[str, Dict[str, Any]] = {}
    for basename in set(AUDIT_RELOCATED.values()):
        path = AUDIT_DIR / f"{basename}.json"
        audit[basename] = load_json(path).get("byCode", {}) if path.exists() else {}
    return BuildContext(fees=fees, warnings=warnings, audit=audit)


def load_status_files() -> List[Dict[str, Any]]:
    """Load all authoring status files ordered by their recorded recordIndex."""
    files = sorted(STATUSES_DIR.glob("*.json"))
    records = [load_json(p) for p in files]
    records.sort(key=lambda r: r["_authoring"]["recordIndex"])
    return records
