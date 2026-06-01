#!/usr/bin/env python3
"""Deterministic coverage check for required-document rendering inputs.

This script validates that visa/status records use document-related fields that are
recognized by the index.html renderer assumptions, and reports potential gaps.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA_CANDIDATES = [ROOT / "visa_data.json", ROOT / "backend" / "data" / "visas.json"]

# Mirrors index.html renderer aliases + procedure legacy aliases.
RENDERER_DOC_FIELDS: Set[str] = {
    # top-level / grouped aliases
    "commonDocs", "common_documents", "common",
    "requiredDocs", "required_documents", "reqDocs", "documents", "document", "docs", "required",
    "additionalDocs", "additional_documents", "addReqDocs", "addReq", "additional",
    "conditionalDocs", "conditional_documents", "conditional",
    # legacy procedure doc arrays / text-backed fields
    "initialReqDocs", "newReqDocs", "newReq",
    "changeReqDocs", "chgReqDocs", "chgReq", "changeReq",
    "extensionReqDocs", "extReqDocs", "extReq",
    "cviReqDocs", "statusGrantReqDocs", "registrationReqDocs",
    "activitiesOutsideStatusReqDocs", "workplaceChangeReqDocs", "reentryReqDocs",
    # Structured 2026-05 manual-grounded document fields (rendered by
    # renderDocumentTabs in index.html).
    "documents_initial", "documents_registration", "documents_extension",
}

# Non-document metadata fields whose names happen to contain a doc/req token
# but which are NOT user-facing document arrays (e.g. pointers into the
# structured manual-evidence layer). These are reference metadata only and are
# intentionally not rendered by the document tabs, so they must be exempt from
# the document-like-field coverage guard.
NON_DOCUMENT_METADATA_FIELDS: Set[str] = {
    "structuredRequirementsRef",
}

PROCEDURE_KEYS = {
    "visaIssuance", "certificateOfVisaIssuance", "statusChange", "extension", "statusGrant",
    "registration", "activitiesOutsideStatus", "workplaceChange", "reentry",
}

PROCEDURE_DOC_GROUP_ALIASES = {
    "commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs",
    "common", "required", "additional", "conditional",
    "documents", "reqDocs", "required_documents",
}
VARIANT_DOC_GROUPS = ("commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs")

PRIORITY_CODES = {"F-1", "F-2", "F-3", "F-5", "F-6", "D-2", "D-4", "D-10", "E-2", "E-7", "G-1", "H-2"}
ALLOWED_DOC_VALUE_TYPES = (str, list, dict)
USEFUL_FALLBACK_KEYS = {"needsManualReview", "verified", "source", "confidence", "status", "note", "updatedAt", "evidence"}


def _load_data() -> Tuple[Path, List[Dict[str, Any]]]:
    for path in DATA_CANDIDATES:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise SystemExit(f"ERROR: {path} must contain a JSON array")
            records = [x for x in data if isinstance(x, dict)]
            return path, records
    raise SystemExit("ERROR: Could not find visa data file (visa_data.json or backend/data/visas.json)")


def _has_useful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_has_useful_value(v) for v in value)
    if isinstance(value, dict):
        return any(_has_useful_value(v) for v in value.values())
    return bool(value)


def _looks_doc_field(field: str) -> bool:
    low = field.lower()
    if low in {"manualrequireddocaudit", "sourcemanualstatus"}:
        return False
    return any(token in low for token in ("doc", "req", "required"))


def _has_fallback_metadata(record: Dict[str, Any]) -> bool:
    status = record.get("sourceManualStatus")
    if isinstance(status, dict) and status:
        if any(key in status and _has_useful_value(status.get(key)) for key in USEFUL_FALLBACK_KEYS):
            return True
        if any(_has_useful_value(v) for v in status.values()):
            return True

    audit = record.get("manualRequiredDocAudit")
    if isinstance(audit, dict) and audit and any(_has_useful_value(v) for v in audit.values()):
        return True

    for key in ("fallbackStatus", "coverageStatus", "sourceReviewStatus"):
        if key in record and _has_useful_value(record.get(key)):
            return True

    procedures = record.get("procedures")
    if isinstance(procedures, dict) and procedures:
        for pval in procedures.values():
            if not isinstance(pval, dict):
                continue
            meta = {k: v for k, v in pval.items() if k not in {"requiredDocs", "commonDocs", "additionalDocs", "conditionalDocs"}}
            if any(_has_useful_value(v) for v in meta.values()):
                return True

    return False


def _extract_doc_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    found: Dict[str, Any] = {}

    for k, v in record.items():
        if k in RENDERER_DOC_FIELDS:
            found[k] = v

    procedures = record.get("procedures")
    if isinstance(procedures, dict):
        for pkey, pval in procedures.items():
            if pkey not in PROCEDURE_KEYS or not isinstance(pval, dict):
                continue
            for alias in PROCEDURE_DOC_GROUP_ALIASES:
                if alias in pval:
                    found[f"procedures.{pkey}.{alias}"] = pval.get(alias)
            variants = pval.get("variants")
            if isinstance(variants, list):
                for index, variant in enumerate(variants):
                    if isinstance(variant, dict) and "requiredDocs" in variant:
                        found[f"procedures.{pkey}.variants[{index}].requiredDocs"] = variant.get("requiredDocs")
    return found


def _check_types(code: str, doc_fields: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field, value in doc_fields.items():
        if value is None:
            continue
        if not isinstance(value, ALLOWED_DOC_VALUE_TYPES):
            errors.append(f"{code}: malformed document field type at '{field}' => {type(value).__name__}")
    return errors


def _validate_manual_refs(path: str, refs: Any) -> List[str]:
    errors: List[str] = []
    if not isinstance(refs, list) or not refs:
        return [f"{path}: source-backed populated variant must include manualRefs"]
    for index, ref in enumerate(refs):
        ref_path = f"{path}.manualRefs[{index}]"
        if not isinstance(ref, dict):
            errors.append(f"{ref_path}: manual reference must be an object")
            continue
        for field in ("manualName", "manualVersion", "pageRange", "confidence"):
            if not isinstance(ref.get(field), str) or not ref[field].strip():
                errors.append(f"{ref_path}: missing/invalid {field}")
        if ref.get("needsManualReview") is not True:
            errors.append(f"{ref_path}: needsManualReview must remain true")
        if ref.get("verified") is True:
            errors.append(f"{ref_path}: verified=true is not allowed for scenario variants")
    return errors


def validate_procedure_variants(records: List[Dict[str, Any]]) -> List[str]:
    """Validate the user-facing scenario/sub-code procedure variant layer."""
    errors: List[str] = []
    for record in records:
        code = str(record.get("code") or "<unknown>")
        procedures = record.get("procedures")
        if not isinstance(procedures, dict):
            continue
        for procedure_key, procedure in procedures.items():
            if procedure_key not in PROCEDURE_KEYS or not isinstance(procedure, dict):
                continue
            variants = procedure.get("variants")
            if variants is None:
                continue
            base_path = f"{code}.procedures.{procedure_key}.variants"
            if not isinstance(variants, list):
                errors.append(f"{base_path}: variants must be a list")
                continue
            seen_ids: Set[str] = set()
            for index, variant in enumerate(variants):
                path = f"{base_path}[{index}]"
                if not isinstance(variant, dict):
                    errors.append(f"{path}: variant must be an object")
                    continue
                variant_id = variant.get("id")
                if not isinstance(variant_id, str) or not variant_id.strip():
                    errors.append(f"{path}: missing/invalid id")
                elif variant_id in seen_ids:
                    errors.append(f"{path}: duplicate id '{variant_id}'")
                else:
                    seen_ids.add(variant_id)
                label = variant.get("labelKo") or variant.get("label")
                if not isinstance(label, str) or not label.strip():
                    errors.append(f"{path}: missing labelKo or label")
                docs = variant.get("requiredDocs")
                if not isinstance(docs, dict):
                    errors.append(f"{path}.requiredDocs: must be an object with grouped document lists")
                    continue
                missing_groups = [group for group in VARIANT_DOC_GROUPS if group not in docs]
                if missing_groups:
                    errors.append(f"{path}.requiredDocs: missing groups {missing_groups}")
                for group in VARIANT_DOC_GROUPS:
                    value = docs.get(group)
                    if value is not None and not isinstance(value, list):
                        errors.append(f"{path}.requiredDocs.{group}: must be a list")
                has_docs = any(_has_useful_value(docs.get(group)) for group in VARIANT_DOC_GROUPS)
                if variant.get("available") is not False and not has_docs:
                    errors.append(f"{path}: populated variant requiredDocs must not be empty unless available=false")
                if has_docs:
                    errors.extend(_validate_manual_refs(path, variant.get("manualRefs")))
    return errors


def main() -> int:
    data_path, records = _load_data()

    with_doc: List[str] = []
    without_doc: List[str] = []
    likely_fallback: List[str] = []
    suspicious_fields: Dict[str, Set[str]] = {}
    errors: List[str] = []
    errors.extend(validate_procedure_variants(records))

    for r in records:
        code = str(r.get("code") or "<unknown>")
        doc_fields = _extract_doc_fields(r)

        if doc_fields:
            with_doc.append(code)
        else:
            without_doc.append(code)
            if _has_fallback_metadata(r):
                likely_fallback.append(code)

        errors.extend(_check_types(code, doc_fields))

        for field in r.keys():
            if (
                _looks_doc_field(field)
                and field not in RENDERER_DOC_FIELDS
                and field not in NON_DOCUMENT_METADATA_FIELDS
                and field not in {"procedures"}
            ):
                suspicious_fields.setdefault(code, set()).add(field)
                value = r.get(field)
                if isinstance(value, (str, list, dict)) and _has_useful_value(value):
                    errors.append(f"{code}: document-like field '{field}' is not covered by renderer mapping inventory")

    by_code = {str(r.get("code") or "<unknown>"): r for r in records}
    for code in sorted(PRIORITY_CODES):
        rec = by_code.get(code)
        if not rec:
            errors.append(f"Priority status missing from data: {code}")
            continue
        doc_fields = _extract_doc_fields(rec)
        if not doc_fields and not _has_fallback_metadata(rec):
            errors.append(f"{code}: priority status missing both document data and fallback classification metadata")

    print("=== Required Documents Rendering Coverage Report ===")
    print(f"Data source: {data_path.relative_to(ROOT)}")
    print(f"Total statuses scanned: {len(records)}")
    print(f"Statuses with document fields: {len(with_doc)}")
    print(f"Statuses without document fields: {len(without_doc)}")
    print(f"Statuses likely requiring fallback: {len(likely_fallback)}")

    print("\nPriority status snapshot:")
    for code in sorted(PRIORITY_CODES):
        rec = by_code.get(code)
        if not rec:
            print(f"- {code}: MISSING")
            continue
        doc_count = len(_extract_doc_fields(rec))
        fallback = _has_fallback_metadata(rec)
        print(f"- {code}: doc_fields={doc_count}, fallback_metadata={'yes' if fallback else 'no'}")

    if suspicious_fields:
        print("\nSuspicious document-like fields not in renderer inventory:")
        for code in sorted(suspicious_fields):
            print(f"- {code}: {', '.join(sorted(suspicious_fields[code]))}")

    if errors:
        print("\nFAIL: Clear regressions detected:")
        for e in errors:
            print(f"- {e}")
        return 1

    print("\nPASS: No clear rendering-coverage regressions detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
