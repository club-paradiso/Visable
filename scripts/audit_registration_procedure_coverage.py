#!/usr/bin/env python3
"""Audit foreign-registration required-document coverage.

The search-result document tabs in index.html historically read
documents_registration, while the newer manual-grounded data usually lives under
procedures.registration. This report makes that split visible and checks the two
synced data files for registration coverage drift.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DATA = ROOT / "visa_data.json"
BACKEND_DATA = ROOT / "backend" / "data" / "visas.json"

MANUAL_PAGE_LIMITS = {
    "체류민원": 774,
    "stay": 774,
    "stay_sojourn": 774,
    "사증발급": 484,
    "visa": 484,
    "visa_issuance": 484,
}

PLACEHOLDER_DOCS = {
    "DATA_MISSING",
    "매뉴얼 확인 필요",
    "페이지 확인 필요",
    "Manual review needed",
    "Page review needed",
}


def load_records(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"ERROR: {path.relative_to(ROOT)} must contain a JSON array")
    return [r for r in data if isinstance(r, dict)]


def is_missing(value: Any) -> bool:
    if value is None or value == "DATA_MISSING":
        return True
    if isinstance(value, list) and not value:
        return True
    return False


def iter_docs(value: Any) -> Iterable[str]:
    if value is None:
        return
    if isinstance(value, str):
        yield value.strip()
        return
    if isinstance(value, list):
        for item in value:
            yield from iter_docs(item)
        return
    if isinstance(value, dict):
        label = value.get("name") or value.get("label") or value.get("title") or value.get("text")
        if label:
            yield str(label).strip()
            return
        for key in ("commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs"):
            yield from iter_docs(value.get(key))


def concrete_docs(value: Any) -> List[str]:
    return [doc for doc in iter_docs(value) if doc and doc not in PLACEHOLDER_DOCS]


def direct_registration_docs(record: Dict[str, Any]) -> List[str]:
    return concrete_docs(record.get("documents_registration"))


def registration_procedure(record: Dict[str, Any]) -> Dict[str, Any]:
    proc = (record.get("procedures") or {}).get("registration")
    return proc if isinstance(proc, dict) else {}


def procedure_registration_docs(record: Dict[str, Any]) -> List[str]:
    return concrete_docs(registration_procedure(record).get("requiredDocs"))


def has_registration_procedure_signal(record: Dict[str, Any]) -> bool:
    proc = registration_procedure(record)
    return bool(proc.get("summary") or proc.get("requiredDocs") or proc.get("manualRefs"))


def document_tabs_would_show(record: Dict[str, Any]) -> bool:
    return any(key in record for key in ("documents_initial", "documents_registration", "documents_extension"))


def extract_page_numbers(page_range: str) -> List[int]:
    return [int(n) for n in re.findall(r"\d+", page_range or "")]


def check_manual_refs(record: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    code = record.get("code") or "<unknown>"
    proc = registration_procedure(record)
    refs = proc.get("manualRefs")
    if not refs:
        if has_registration_procedure_signal(record):
            errors.append(f"{code}: procedures.registration has data but no manualRefs")
        return errors
    if not isinstance(refs, list):
        return [f"{code}: procedures.registration.manualRefs must be a list"]
    for idx, ref in enumerate(refs):
        if not isinstance(ref, dict):
            errors.append(f"{code}: manualRefs[{idx}] must be an object")
            continue
        page_range = str(ref.get("pageRange") or "")
        if not page_range:
            errors.append(f"{code}: manualRefs[{idx}] missing pageRange")
            continue
        manual_name = str(ref.get("manualName") or ref.get("manual") or "").strip()
        limit = MANUAL_PAGE_LIMITS.get(manual_name, MANUAL_PAGE_LIMITS.get(manual_name.lower()))
        if not limit:
            continue
        pages = extract_page_numbers(page_range)
        if not pages:
            errors.append(f"{code}: manualRefs[{idx}] pageRange has no page number: {page_range}")
            continue
        out = [p for p in pages if p < 1 or p > limit]
        if out:
            errors.append(f"{code}: manualRefs[{idx}] pageRange {page_range} outside {manual_name} page limit {limit}")
    return errors


def registration_signature(record: Dict[str, Any]) -> Tuple[Any, Any, Any]:
    proc = registration_procedure(record)
    return (
        record.get("documents_registration"),
        proc.get("summary"),
        proc.get("requiredDocs"),
    )


def compare_frontend_backend(frontend: List[Dict[str, Any]], backend: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    by_code_backend = {r.get("code"): r for r in backend}
    for record in frontend:
        code = record.get("code")
        other = by_code_backend.get(code)
        if not other:
            errors.append(f"{code}: present in visa_data.json but missing from backend/data/visas.json")
            continue
        if registration_signature(record) != registration_signature(other):
            errors.append(f"{code}: registration content differs between visa_data.json and backend/data/visas.json")
    return errors


def summarize(records: List[Dict[str, Any]]) -> Tuple[Dict[str, int], Dict[str, List[str]], List[str]]:
    counts = {
        "records": 0,
        "document_tabs_visible": 0,
        "direct_registration_docs": 0,
        "procedure_registration_docs": 0,
        "procedure_only_registration_docs": 0,
        "procedure_placeholder_or_summary_only": 0,
        "no_registration_signal": 0,
    }
    samples: Dict[str, List[str]] = {
        "procedure_only_registration_docs": [],
        "procedure_placeholder_or_summary_only": [],
        "no_registration_signal": [],
    }
    errors: List[str] = []

    for record in records:
        counts["records"] += 1
        code = str(record.get("code") or "<unknown>")
        direct = direct_registration_docs(record)
        proc_docs = procedure_registration_docs(record)
        has_signal = has_registration_procedure_signal(record)

        if document_tabs_would_show(record):
            counts["document_tabs_visible"] += 1
        if direct:
            counts["direct_registration_docs"] += 1
        if proc_docs:
            counts["procedure_registration_docs"] += 1
        if not direct and proc_docs:
            counts["procedure_only_registration_docs"] += 1
            if len(samples["procedure_only_registration_docs"]) < 20:
                samples["procedure_only_registration_docs"].append(code)
        elif not direct and has_signal:
            counts["procedure_placeholder_or_summary_only"] += 1
            if len(samples["procedure_placeholder_or_summary_only"]) < 20:
                samples["procedure_placeholder_or_summary_only"].append(code)
        elif not direct and not has_signal:
            counts["no_registration_signal"] += 1
            if len(samples["no_registration_signal"]) < 20:
                samples["no_registration_signal"].append(code)

        errors.extend(check_manual_refs(record))

    return counts, samples, errors


def main() -> int:
    frontend = load_records(FRONTEND_DATA)
    backend = load_records(BACKEND_DATA)
    counts, samples, errors = summarize(frontend)
    errors.extend(compare_frontend_backend(frontend, backend))

    print("=== Foreign Registration Procedure Coverage Audit ===")
    print(f"Data source: {FRONTEND_DATA.relative_to(ROOT)}")
    for key, value in counts.items():
        print(f"{key}: {value}")

    print("\nSamples:")
    for key, values in samples.items():
        rendered = ", ".join(values) if values else "(none)"
        print(f"- {key}: {rendered}")

    print("\nInterpretation:")
    print("- direct_registration_docs counts records with concrete documents_registration items.")
    print("- procedure_only_registration_docs counts records where procedures.registration has concrete docs but the legacy direct field does not.")
    print("- procedure_placeholder_or_summary_only counts records with registration metadata that still needs manual structuring.")

    if errors:
        print("\nFAIL:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("\nPASS: registration references are in bounds and frontend/backend registration data are in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
