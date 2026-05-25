#!/usr/bin/env python3
"""Full foreign-registration coverage audit across all 58 top-level visa_data.json records.

Classifies every record into one primary category and zero or more secondary flags,
then writes a machine-readable JSON report and a console summary.

Primary categories (mutually exclusive, applied in priority order):
  non_visa_helper_record            – FAQ/scenario/guide record; no registration tab expected.
  displayable_registration_docs     – Has concrete, renderable registration documents.
  conditionally_applicable_registration – Short-stay status; registration rarely/never applies.
  placeholder_registration_docs     – available=True but all docs are placeholders (raw text
                                      extracted but not yet structured into schema).
  procedure_only_registration_docs  – Source-grounded page ref exists but docs are all
                                      placeholder and available=False; needs manual structuring.
  no_registration_signal            – No procedures.registration data whatsoever.

Secondary flags (non-exclusive, added alongside primary):
  needs_manual_page_review          – At least one manualRef has needsManualReview=true.
  source_range_missing_or_out_of_bounds – A page number falls outside the canonical manual limit.
  frontend_backend_sync_mismatch    – Registration data differs between visa_data.json and
                                      backend/data/visas.json.
  duplicate_code                    – The same code appears more than once in visa_data.json.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DATA = ROOT / "visa_data.json"
BACKEND_DATA = ROOT / "backend" / "data" / "visas.json"
TOC_MAP = ROOT / "docs" / "data" / "2026_05_21_manual_toc_map.json"
REPORT_OUT = ROOT / "docs" / "data" / "foreign_registration_full_coverage_2026_05.json"

# Canonical page limits from committed TOC map (PR #155 + re-derived).
# Stay manual grew from 774 → 777 pages in the canonical 2026-05-21 PDF.
STAY_MANUAL_PAGES = 777
VISA_MANUAL_PAGES = 484

MANUAL_PAGE_LIMITS: Dict[str, int] = {
    "체류민원": STAY_MANUAL_PAGES,
    "stay": STAY_MANUAL_PAGES,
    "stay_sojourn": STAY_MANUAL_PAGES,
    "사증발급": VISA_MANUAL_PAGES,
    "visa": VISA_MANUAL_PAGES,
    "visa_issuance": VISA_MANUAL_PAGES,
}

PLACEHOLDER_VALUES = {
    "DATA_MISSING",
    "매뉴얼 확인 필요",
    "페이지 확인 필요",
    "Manual review needed",
    "Page review needed",
}

# Helper/FAQ/scenario record categories that are not visa status records.
NON_VISA_HELPER_CATS = {"scn", "faq", "nhis"}

# Additional codes that are helper/guide records regardless of cat field.
NON_VISA_HELPER_CODES = {"K-ETA", "NHIS-1", "OVS-1", "TB-1", "RF-1"}

# Short-stay status codes where foreign registration is generally not required
# (stays under 90 days are the typical use case; registration rarely applies).
SHORT_STAY_CODES = {"B-1", "B-2", "C-1", "C-4"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_json_list(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit(f"ERROR: {path.relative_to(ROOT)} must be a JSON array")
    return [r for r in raw if isinstance(r, dict)]


def load_toc_map() -> Dict[str, Any]:
    if not TOC_MAP.exists():
        return {}
    try:
        return json.loads(TOC_MAP.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Document helpers
# ---------------------------------------------------------------------------

def iter_leaf_strings(value: Any) -> List[str]:
    """Recursively collect all leaf string values from a docs structure."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        result: List[str] = []
        for item in value:
            result.extend(iter_leaf_strings(item))
        return result
    if isinstance(value, dict):
        result = []
        # Named-item shortcut
        for name_key in ("name", "label", "title", "text"):
            if value.get(name_key):
                result.extend(iter_leaf_strings(value[name_key]))
                return result
        # Structured doc bundle
        for bundle_key in ("commonDocs", "requiredDocs", "additionalDocs", "conditionalDocs"):
            result.extend(iter_leaf_strings(value.get(bundle_key)))
        return result
    return []


def concrete_docs(value: Any) -> List[str]:
    return [s for s in iter_leaf_strings(value) if s not in PLACEHOLDER_VALUES]


def get_proc_reg(record: Dict[str, Any]) -> Dict[str, Any]:
    proc = record.get("procedures") or {}
    reg = proc.get("registration")
    return reg if isinstance(reg, dict) else {}


def has_concrete_docs(record: Dict[str, Any]) -> bool:
    proc_reg = get_proc_reg(record)
    if concrete_docs(record.get("documents_registration")):
        return True
    if concrete_docs(proc_reg.get("requiredDocs")):
        return True
    return False


def registration_signature(record: Dict[str, Any]) -> Tuple:
    proc_reg = get_proc_reg(record)
    return (
        record.get("documents_registration"),
        proc_reg.get("summary"),
        proc_reg.get("requiredDocs"),
    )


# ---------------------------------------------------------------------------
# Manual-reference checks
# ---------------------------------------------------------------------------

def extract_pages(page_range: str) -> List[int]:
    return [int(n) for n in re.findall(r"\d+", page_range or "")]


def check_manual_refs_bounds(record: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    code = record.get("code") or "<unknown>"
    proc_reg = get_proc_reg(record)
    refs = proc_reg.get("manualRefs") or []
    if not isinstance(refs, list):
        return [f"{code}: manualRefs must be a list"]
    for idx, ref in enumerate(refs):
        if not isinstance(ref, dict):
            errors.append(f"{code}: manualRefs[{idx}] must be an object")
            continue
        page_range = str(ref.get("pageRange") or "")
        if not page_range:
            errors.append(f"{code}: manualRefs[{idx}] missing pageRange")
            continue
        manual_name = str(ref.get("manualName") or "").strip()
        limit = MANUAL_PAGE_LIMITS.get(manual_name)
        if not limit:
            continue
        pages = extract_pages(page_range)
        if not pages:
            errors.append(f"{code}: manualRefs[{idx}] pageRange has no page numbers: {page_range!r}")
            continue
        out = [p for p in pages if p < 1 or p > limit]
        if out:
            errors.append(
                f"{code}: manualRefs[{idx}] pageRange {page_range!r} outside "
                f"{manual_name} limit {limit}: {out}"
            )
    return errors


def has_needs_manual_review(record: Dict[str, Any]) -> bool:
    proc_reg = get_proc_reg(record)
    refs = proc_reg.get("manualRefs") or []
    if isinstance(refs, list):
        return any(
            isinstance(r, dict) and bool(r.get("needsManualReview"))
            for r in refs
        )
    return False


def manual_ref_summary(record: Dict[str, Any]) -> Optional[str]:
    """Return a concise ref string like '체류민원:pp.27-28' or None."""
    proc_reg = get_proc_reg(record)
    refs = proc_reg.get("manualRefs") or []
    if not isinstance(refs, list) or not refs:
        return None
    parts = []
    for ref in refs:
        if isinstance(ref, dict):
            name = ref.get("manualName", "")
            page = ref.get("pageRange", "")
            if name and page:
                parts.append(f"{name}:{page}")
    return "; ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# TOC map evidence
# ---------------------------------------------------------------------------

def build_toc_index(toc_map: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return {code: {manual, page_range, confidence, notes}} from the committed TOC map."""
    index: Dict[str, Dict[str, Any]] = {}
    for manual_key in ("stay_manual", "visa_manual"):
        manual_data = toc_map.get(manual_key) or {}
        manual_label = "체류민원" if manual_key == "stay_manual" else "사증발급"
        for section in manual_data.get("sections") or []:
            code = section.get("code")
            if not code or code.startswith("special"):
                continue
            if code not in index:
                index[code] = {
                    "manual": manual_label,
                    "page_range": section.get("page_range") or section.get("pageRange"),
                    "confidence": section.get("confidence"),
                    "notes": section.get("notes"),
                }
    return index


# ---------------------------------------------------------------------------
# Per-record classification
# ---------------------------------------------------------------------------

def classify_record(
    record: Dict[str, Any],
    backend_map: Dict[str, Dict[str, Any]],
    code_counts: Counter,
    toc_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    code = str(record.get("code") or "<unknown>")
    cat = str(record.get("cat") or "")
    name = str(record.get("name") or "")

    proc_reg = get_proc_reg(record)
    available = proc_reg.get("available")
    summary = str(proc_reg.get("summary") or "")
    refs_exist = bool(proc_reg.get("manualRefs"))
    notes_list = proc_reg.get("notes") or []
    concrete = concrete_docs(proc_reg.get("requiredDocs")) + concrete_docs(
        record.get("documents_registration")
    )
    direct_docs = concrete_docs(record.get("documents_registration"))
    proc_docs = concrete_docs(proc_reg.get("requiredDocs"))
    all_concrete = bool(direct_docs or proc_docs)

    # Secondary flags
    flags: List[str] = []

    if code_counts[code] > 1:
        flags.append("duplicate_code")

    bounds_errors = check_manual_refs_bounds(record)
    if bounds_errors:
        flags.append("source_range_missing_or_out_of_bounds")

    if has_needs_manual_review(record):
        flags.append("needs_manual_page_review")

    backend_rec = backend_map.get(code)
    if backend_rec is not None and registration_signature(record) != registration_signature(backend_rec):
        flags.append("frontend_backend_sync_mismatch")

    # Primary classification (priority order)
    if cat in NON_VISA_HELPER_CATS or code in NON_VISA_HELPER_CODES:
        primary = "non_visa_helper_record"
        registration_status = "n/a – helper record"
        current_data_path = "none"
    elif all_concrete:
        primary = "displayable_registration_docs"
        registration_status = "displayable"
        if direct_docs:
            current_data_path = "documents_registration"
        else:
            current_data_path = "procedures.registration.requiredDocs"
    elif code in SHORT_STAY_CODES:
        primary = "conditionally_applicable_registration"
        registration_status = "conditionally applicable (short-stay)"
        current_data_path = "procedures.registration (manualRef only)" if refs_exist else "none"
    elif available is True:
        # available=True but all docs are placeholder; raw text likely extracted but not structured
        primary = "placeholder_registration_docs"
        registration_status = "available=True but docs are placeholder"
        current_data_path = "procedures.registration.requiredDocs (placeholder)"
    elif refs_exist:
        primary = "procedure_only_registration_docs"
        registration_status = "source-grounded page ref, not yet structured"
        current_data_path = "procedures.registration.manualRefs (page ref only)"
    elif proc_reg:
        primary = "procedure_only_registration_docs"
        registration_status = "procedures.registration present but no manualRefs"
        current_data_path = "procedures.registration (no refs)"
    else:
        primary = "no_registration_signal"
        registration_status = "no registration data"
        current_data_path = "none"

    # Source / manual evidence
    toc_entry = toc_index.get(code)
    if toc_entry:
        source_evidence = (
            f"Stay-manual section detected: {toc_entry['manual']} "
            f"pp.{toc_entry['page_range']} (conf={toc_entry['confidence']})"
        )
    else:
        ref_str = manual_ref_summary(record)
        if ref_str:
            source_evidence = f"manualRefs from extraction: {ref_str}"
        else:
            source_evidence = "none"

    # Recommended action
    if primary == "non_visa_helper_record":
        action = "Suppress registration tab in UI for helper/FAQ records"
    elif primary == "displayable_registration_docs":
        action = "Already renderable; retain needsManualReview markers until verified"
    elif primary == "conditionally_applicable_registration":
        action = (
            "Manual page review needed to determine if registration subsection exists; "
            "conditionally suppress tab or add scenario note"
        )
    elif primary == "placeholder_registration_docs":
        action = (
            "High priority: raw text in summary — structure docs from manual page "
            + (manual_ref_summary(record) or "see manualRefs")
        )
    elif primary == "procedure_only_registration_docs":
        action = (
            "Manual page review then structured data patch; "
            "page ref: " + (manual_ref_summary(record) or "none")
        )
    else:
        action = "Investigate; no source signal found"

    return {
        "code": code,
        "name": name,
        "cat": cat,
        "primary_category": primary,
        "registration_status": registration_status,
        "current_data_path": current_data_path,
        "available_flag": available,
        "concrete_doc_count": len(direct_docs) + len(proc_docs),
        "direct_docs": direct_docs,
        "proc_docs": proc_docs,
        "has_summary_text": bool(summary),
        "summary_preview": summary[:120] if summary else "",
        "has_manual_refs": refs_exist,
        "manual_ref_summary": manual_ref_summary(record) or "",
        "toc_map_evidence": source_evidence,
        "secondary_flags": flags,
        "bounds_errors": bounds_errors,
        "recommended_action": action,
        "notes": notes_list if isinstance(notes_list, list) else [str(notes_list)],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    frontend = load_json_list(FRONTEND_DATA)
    backend = load_json_list(BACKEND_DATA)
    toc_raw = load_toc_map()
    toc_index = build_toc_index(toc_raw)

    backend_map: Dict[str, Dict[str, Any]] = {r.get("code"): r for r in backend if r.get("code")}
    code_counts: Counter = Counter(r.get("code") for r in frontend)

    results: List[Dict[str, Any]] = []
    for record in frontend:
        results.append(classify_record(record, backend_map, code_counts, toc_index))

    # ---- Summary counts ----
    primary_counts: Counter = Counter(r["primary_category"] for r in results)
    flag_counts: Counter = Counter(
        flag for r in results for flag in r["secondary_flags"]
    )

    by_category: Dict[str, List[str]] = {}
    for r in results:
        by_category.setdefault(r["primary_category"], []).append(r["code"])

    # ---- Console output ----
    print("=" * 70)
    print("Foreign Registration Full Coverage Audit — 2026.05")
    print(f"Source: {FRONTEND_DATA.relative_to(ROOT)}")
    print(f"Stay manual page limit: {STAY_MANUAL_PAGES}  Visa manual: {VISA_MANUAL_PAGES}")
    print("=" * 70)
    print(f"\nTotal top-level records: {len(results)}\n")

    print("Primary classification counts:")
    ordered_primaries = [
        "displayable_registration_docs",
        "placeholder_registration_docs",
        "procedure_only_registration_docs",
        "conditionally_applicable_registration",
        "no_registration_signal",
        "non_visa_helper_record",
    ]
    for cat in ordered_primaries:
        count = primary_counts.get(cat, 0)
        codes = by_category.get(cat, [])
        codes_str = ", ".join(codes)
        print(f"  {cat}: {count}")
        if codes:
            print(f"      codes: {codes_str}")

    other_cats = set(primary_counts) - set(ordered_primaries)
    for cat in sorted(other_cats):
        print(f"  {cat}: {primary_counts[cat]}")

    print("\nSecondary flags:")
    for flag in sorted(flag_counts):
        codes = [r["code"] for r in results if flag in r["secondary_flags"]]
        print(f"  {flag}: {flag_counts[flag]}  ({', '.join(codes)})")

    print("\nTop-priority records to patch:")
    high_pri = [
        r for r in results
        if r["primary_category"] == "placeholder_registration_docs"
    ]
    for r in high_pri:
        print(f"  {r['code']}: {r['recommended_action'][:80]}")

    print("\nRecords that should NOT show a registration tab:")
    helper_codes = [r["code"] for r in results if r["primary_category"] == "non_visa_helper_record"]
    print("  " + ", ".join(helper_codes))

    # ---- Sync and bounds check ----
    sync_errors = [r for r in results if "frontend_backend_sync_mismatch" in r["secondary_flags"]]
    bounds_errors_any = [r for r in results if "source_range_missing_or_out_of_bounds" in r["secondary_flags"]]
    dup_codes = [r for r in results if "duplicate_code" in r["secondary_flags"]]

    print(f"\nFrontend/backend sync mismatches: {len(sync_errors)}")
    print(f"Page-range out-of-bounds errors: {len(bounds_errors_any)}")
    if bounds_errors_any:
        for r in bounds_errors_any:
            for err in r["bounds_errors"]:
                print(f"  ERROR: {err}")
    print(f"Duplicate code entries: {len(dup_codes)}")
    if dup_codes:
        for r in dup_codes:
            print(f"  {r['code']}: {r['name']}")

    # ---- Stale page-limit note ----
    print(
        "\nNote: The prior audit_registration_procedure_coverage.py used stay page limit 774. "
        f"Canonical limit is {STAY_MANUAL_PAGES} (PR #155). No records fall outside the updated limit."
    )

    # ---- JSON report ----
    report = {
        "report_id": "foreign_registration_full_coverage_2026_05",
        "audit_date": "2026-05-25",
        "branch": "claude/serene-dirac-egWL3",
        "after_pr": 173,
        "source_files": {
            "frontend": str(FRONTEND_DATA.relative_to(ROOT)),
            "backend": str(BACKEND_DATA.relative_to(ROOT)),
            "toc_map": str(TOC_MAP.relative_to(ROOT)),
        },
        "manual_page_limits": {
            "stay_체류민원": STAY_MANUAL_PAGES,
            "visa_사증발급": VISA_MANUAL_PAGES,
            "note": f"Stay manual updated from 774 to {STAY_MANUAL_PAGES} pages in canonical 2026-05-21 PDF (PR #155).",
        },
        "summary": {
            "total_records": len(results),
            "primary_counts": dict(primary_counts),
            "secondary_flag_counts": dict(flag_counts),
        },
        "records": results,
    }

    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON report written to: {REPORT_OUT.relative_to(ROOT)}")

    all_ok = (
        len(sync_errors) == 0
        and len(bounds_errors_any) == 0
    )
    if all_ok:
        print("\nPASS: no sync mismatches, no out-of-bounds page references.")
        return 0
    else:
        print("\nFAIL: see errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
