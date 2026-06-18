#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUSES_DIR = ROOT / "backend/data/visa_authoring/statuses"
INVENTORY = ROOT / "docs/data/2026_06_17_manual_code_inventory.json"
COVERAGE = ROOT / "docs/data/2026_06_17_subcode_coverage_report.json"
MATRIX = ROOT / "docs/data/2026_06_17_status_review_matrix.json"
AUDIT = ROOT / "docs/data/2026_06_17_full_manual_refresh_audit.json"

FIELD_GROUPS = [
    "identity",
    "period",
    "activityScope",
    "manualDomains",
    "subcodes",
    "procedures",
    "documents",
    "summaries",
    "sourceMetadata",
    "searchAliases",
]


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def parent_code(code: str) -> str:
    if code == "K-STAR":
        return "K-STAR"
    parts = code.split("-")
    return "-".join(parts[:2])


def walk_manual_refs(value, pointer=""):
    found = []
    if isinstance(value, dict):
        if "manualRefs" in value and isinstance(value["manualRefs"], list):
            for idx, ref in enumerate(value["manualRefs"]):
                found.append((f"{pointer}/manualRefs/{idx}", ref))
        for key, nested in value.items():
            found.extend(walk_manual_refs(nested, f"{pointer}/{key}"))
    elif isinstance(value, list):
        for idx, nested in enumerate(value):
            found.extend(walk_manual_refs(nested, f"{pointer}/{idx}"))
    return found


def stale_ref(ref: dict) -> bool:
    text = json.dumps(ref, ensure_ascii=False, sort_keys=True)
    if "2026.6" in text or "2026-06-17" in text or "260617" in text:
        return False
    return any(marker in text for marker in ("2026.5", "2026-05", "2026-06-01", "2026_05", "2026-06/stay_manual_2026_06_01"))


def status_sort_key(code: str) -> tuple:
    if code == "K-STAR":
        return ("Z", 999, code)
    first, *rest = code.split("-")
    parsed = []
    for part in rest[:2]:
        digits = ""
        suffix = ""
        for ch in part:
            if ch.isdigit() and not suffix:
                digits += ch
            else:
                suffix += ch
        parsed.append((int(digits) if digits else 999, suffix))
    while len(parsed) < 2:
        parsed.append((-1, ""))
    return (first, parsed[0][0], parsed[0][1], parsed[1][0], parsed[1][1], code)


def main() -> int:
    inventory = load_json(INVENTORY)
    coverage = load_json(COVERAGE)
    inventory_by_parent = {}
    for item in inventory["items"]:
        inventory_by_parent.setdefault(item["parentCode"], []).append(item)

    coverage_issue_by_parent = {}
    for issue_type, issues in coverage["issues"].items():
        for issue in issues:
            parent = issue.get("parentCode") or parent_code(issue.get("code", ""))
            coverage_issue_by_parent.setdefault(parent, []).append({"type": issue_type, **issue})

    matrix_entries = []
    audit_entries = []

    for path in sorted(STATUSES_DIR.glob("*.json"), key=lambda p: status_sort_key(p.stem)):
        status = load_json(path)
        code = status["code"]
        manual_items = sorted(inventory_by_parent.get(code, []), key=lambda item: status_sort_key(item["code"]))
        authoring_subcodes = [sub.get("code") for sub in status.get("subcodes") or [] if sub.get("code")]
        manual_subcodes = [
            item["code"]
            for item in manual_items
            if item["classification"] in {"active_subcode", "special_track", "abolished_subcode", "deprecated_subcode", "policy_or_multiple_entry_code"}
        ]
        missing_before = [
            item["code"]
            for item in manual_items
            if item["classification"] == "active_subcode"
            and item["shouldBeInCanonicalSubcodes"]
            and item["code"] not in authoring_subcodes
        ]
        excluded_codes = [
            {
                "code": item["code"],
                "classification": item["classification"],
                "reason": item.get("notes", ""),
            }
            for item in manual_items
            if not item["shouldBeInCanonicalSubcodes"] or item["classification"] in {"parent_status", "policy_or_multiple_entry_code"}
        ]
        stale_refs = [
            {"jsonPointer": pointer or "/", "manualRef": ref}
            for pointer, ref in walk_manual_refs(status)
            if stale_ref(ref)
        ]
        refresh = (status.get("sourceManualStatus") or {}).get("manualRefresh260617") or {}
        reviewed = bool(refresh.get("reviewed"))
        reviewed_fields = set(refresh.get("reviewedFields") or [])
        source_refs = [ref for item in manual_items for ref in item["sourceRefs"][:3]]
        visa_refs = [ref for ref in source_refs if ref["manual"] == "visa"]
        stay_refs = [ref for ref in source_refs if ref["manual"] == "stay"]
        manual_sections_checked = sorted(
            {
                f"{ref['manual']} p.{ref['page']} {ref.get('section') or ''}".strip()
                for ref in source_refs
            }
        )
        issues = coverage_issue_by_parent.get(code, [])
        authoring_not_found = sorted(set(authoring_subcodes) - {item["code"] for item in inventory["items"]})
        changed = reviewed
        unresolved = []
        if stale_refs:
            unresolved.append("Existing manualRefs still point to pre-2026-06-17 source metadata.")
        if missing_before:
            unresolved.append("Manual-derived active subcodes are missing from authoring before refresh.")
        if authoring_not_found:
            unresolved.append("Some authoring subcodes were not discovered by the 2026-06-17 manual code regex inventory and require manual classification.")
        if issues:
            unresolved.append("Coverage checker reported issues for this parent status.")
        if manual_items:
            unresolved.append("Documents, procedure text, summaries, and activity scope still require field-by-field legal review against the listed manual sections.")

        matrix_entries.append(
            {
                "code": code,
                "file": rel(path),
                "reviewed": reviewed,
                "manualSectionsChecked": manual_sections_checked,
                "visaManualRefs": visa_refs,
                "stayManualRefs": stay_refs,
                "fieldsReviewed": {field: field in reviewed_fields for field in FIELD_GROUPS},
                "manualSubcodesFound": manual_subcodes,
                "authoringSubcodesBefore": authoring_subcodes,
                "authoringSubcodesAfter": authoring_subcodes,
                "missingSubcodesBefore": missing_before,
                "excludedManualCodes": excluded_codes,
                "changed": changed,
                "changeSummary": [
                    "Attached 2026-06-17 manual source metadata and refreshed subcode review flags conservatively.",
                    "Generated compatibility output must be rebuilt from canonical authoring data.",
                ]
                if changed
                else [],
                "needsManualReview": bool((status.get("sourceManualStatus") or {}).get("needsManualReview")) or bool(unresolved),
                "unresolvedIssues": unresolved,
            }
        )

        audit_entries.append(
            {
                "code": code,
                "file": rel(path),
                "readOnlyEvidenceCollected": True,
                "implementationRefreshApplied": reviewed,
                "manualVersion": "2026.6",
                "sourceDate": "2026-06-17",
                "manualSectionsLocated": manual_sections_checked,
                "visaManualRefs": visa_refs,
                "stayManualRefs": stay_refs,
                "manualDerivedCodes": [
                    {
                        "code": item["code"],
                        "classification": item["classification"],
                        "status": item["status"],
                        "shouldBeInCanonicalSubcodes": item["shouldBeInCanonicalSubcodes"],
                        "shouldBeSearchable": item["shouldBeSearchable"],
                        "notes": item["notes"],
                    }
                    for item in manual_items
                ],
                "authoringSubcodesBefore": authoring_subcodes,
                "activeSubcodesMissingFromAuthoring": missing_before,
                "authoringSubcodesNotFoundInManualInventory": authoring_not_found,
                "deprecatedOrAbolishedSubcodesStillActive": [
                    issue for issue in issues if issue["type"] == "deprecatedOrAbolishedShownActive"
                ],
                "specialTracksNotRepresented": [
                    issue for issue in issues if issue["type"] == "unrepresentedSpecialTracks"
                ],
                "codeAliasesNeededForExactSearch": [
                    item["code"]
                    for item in manual_items
                    if item["shouldBeSearchable"] and not item.get("searchableInCurrentData")
                ],
                "staleSourceRefs": stale_refs,
                "documentProcedureScopeMismatches": [
                    "Not machine-resolved in read-only phase; requires field-by-field manual comparison before authoring edits."
                ]
                if manual_items
                else [],
                "coverageIssues": issues,
                "needsManualReview": bool((status.get("sourceManualStatus") or {}).get("needsManualReview")) or bool(unresolved),
                "unresolvedIssues": unresolved,
            }
        )

    matrix = {
        "manualVersion": "2026.6",
        "sourceDate": "2026-06-17",
        "statusFileCount": len(matrix_entries),
        "reviewPolicy": "Read-only evidence pass only. Do not set reviewed=true until authoring fields are manually checked against source refs.",
        "entries": matrix_entries,
    }
    audit = {
        "manualVersion": "2026.6",
        "sourceDate": "2026-06-17",
        "inputs": {
            "inventory": rel(INVENTORY),
            "coverageReport": rel(COVERAGE),
            "statusDir": rel(STATUSES_DIR),
        },
        "summary": {
            "statusFileCount": len(audit_entries),
            "statusesWithManualDerivedCodes": sum(1 for entry in audit_entries if entry["manualDerivedCodes"]),
            "statusesWithCoverageIssues": sum(1 for entry in audit_entries if entry["coverageIssues"]),
            "statusesWithStaleSourceRefs": sum(1 for entry in audit_entries if entry["staleSourceRefs"]),
            "statusesWithImplementationRefreshApplied": sum(1 for entry in audit_entries if entry["implementationRefreshApplied"]),
            "allStatusesNeedManualReviewBeforeAuthoringEdits": False,
        },
        "entries": audit_entries,
    }

    write_json(MATRIX, matrix)
    write_json(AUDIT, audit)
    print(f"wrote {rel(MATRIX)} ({len(matrix_entries)} statuses)")
    print(f"wrote {rel(AUDIT)} ({len(audit_entries)} statuses)")
    print(json.dumps(audit["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
