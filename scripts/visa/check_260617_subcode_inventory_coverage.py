#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "docs/data/2026_06_17_manual_code_inventory.json"
REPORT = ROOT / "docs/data/2026_06_17_subcode_coverage_report.json"
STATUSES_DIR = ROOT / "backend/data/visa_authoring/statuses"
VISA_DATA = ROOT / "visa_data.json"
BACKEND_VISAS = ROOT / "backend/data/visas.json"

ACTIVE_MANUAL_CLASSES = {"active_subcode"}
SPECIAL_TRACK_CLASSES = {"special_track"}
DEPRECATED_CLASSES = {"deprecated_subcode", "abolished_subcode"}
NON_CANONICAL_CLASSES = {
    "parent_status",
    "visa_only",
    "stay_only",
    "procedure_only",
    "policy_or_multiple_entry_code",
    "manual_reference_only",
    "false_positive",
    "needs_human_review",
}


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_authoring():
    status_files = {}
    subcodes = {}
    for path in sorted(STATUSES_DIR.glob("*.json")):
        data = load_json(path)
        code = data["code"]
        status_files[code] = {"file": rel(path), "data": data}
        for subcode in data.get("subcodes") or []:
            subcode_code = subcode.get("code")
            if not subcode_code:
                continue
            subcodes.setdefault(subcode_code, []).append(
                {
                    "parentCode": code,
                    "file": rel(path),
                    "status": subcode.get("status", "active"),
                    "needsManualReview": bool(subcode.get("needsManualReview")),
                    "manualRefs": subcode.get("manualRefs") or [],
                    "searchAliases": subcode.get("searchAliases") or [],
                    "name": subcode.get("nameKo") or subcode.get("name") or "",
                }
            )
    return status_files, subcodes


def generated_index(path: Path):
    records = load_json(path)
    by_code = {record.get("code"): record for record in records}
    subcode_index = {}
    for record in records:
        parent = record.get("code")
        for field in ("subcodes", "subCodes"):
            for subcode in record.get(field) or []:
                code = subcode.get("code")
                if code:
                    subcode_index.setdefault(code, set()).add(parent)
    return records, by_code, subcode_index


def code_set(arr):
    if not isinstance(arr, list):
        return None
    return {entry.get("code") for entry in arr if isinstance(entry, dict) and entry.get("code")}


def main() -> int:
    inventory = load_json(INVENTORY)
    status_files, authoring_subcodes = load_authoring()
    visa_records, visa_by_code, visa_subcodes = generated_index(VISA_DATA)
    backend_records, backend_by_code, backend_subcodes = generated_index(BACKEND_VISAS)

    items = inventory["items"]
    by_code = {item["code"]: item for item in items}
    issues = {
        "missingActiveSubcodes": [],
        "unrepresentedSpecialTracks": [],
        "deprecatedOrAbolishedShownActive": [],
        "authoringSubcodesWithoutSourceOrReviewFlag": [],
        "manualCodesExcludedWithoutAuditReason": [],
        "generatedSubcodeParityIssues": [],
        "generatedFileSyncIssues": [],
        "exactCodeSearchIssues": [],
    }
    represented = []
    explicit_exclusions = []

    for item in items:
        code = item["code"]
        entries = authoring_subcodes.get(code, [])
        represented_in_authoring = bool(entries)
        represented_as_status = code in status_files

        if item["classification"] in ACTIVE_MANUAL_CLASSES and item["shouldBeInCanonicalSubcodes"]:
            if not represented_in_authoring:
                issues["missingActiveSubcodes"].append(
                    {
                        "code": code,
                        "parentCode": item["parentCode"],
                        "classification": item["classification"],
                        "reason": "Manual-derived active subcode is not present in authoring subcodes.",
                        "sourceRefs": item["sourceRefs"][:2],
                    }
                )
            else:
                represented.append(code)

        if item["classification"] in SPECIAL_TRACK_CLASSES:
            if represented_in_authoring or represented_as_status:
                represented.append(code)
            else:
                issues["unrepresentedSpecialTracks"].append(
                    {
                        "code": code,
                        "parentCode": item["parentCode"],
                        "reason": "Manual-derived special track is not represented in authoring subcodes or status files.",
                        "sourceRefs": item["sourceRefs"][:2],
                    }
                )

        if item["classification"] in DEPRECATED_CLASSES:
            for entry in entries:
                if entry["status"] not in {"deprecated", "abolished", "manual_review_required"}:
                    issues["deprecatedOrAbolishedShownActive"].append(
                        {
                            "code": code,
                            "parentCode": entry["parentCode"],
                            "file": entry["file"],
                            "authoringStatus": entry["status"],
                            "manualClassification": item["classification"],
                            "sourceRefs": item["sourceRefs"][:2],
                        }
                    )

        if item["classification"] in NON_CANONICAL_CLASSES or not item["shouldBeInCanonicalSubcodes"]:
            reason = item.get("notes") or ""
            if reason:
                explicit_exclusions.append({"code": code, "classification": item["classification"], "reason": reason})
            else:
                issues["manualCodesExcludedWithoutAuditReason"].append(
                    {"code": code, "classification": item["classification"], "reason": "No notes/audit reason present."}
                )

    for code, entries in sorted(authoring_subcodes.items()):
        inventory_item = by_code.get(code)
        has_inventory_support = bool(inventory_item and inventory_item["classification"] not in {"false_positive"})
        for entry in entries:
            if not has_inventory_support and not entry["manualRefs"] and not entry["needsManualReview"]:
                issues["authoringSubcodesWithoutSourceOrReviewFlag"].append(
                    {
                        "code": code,
                        "parentCode": entry["parentCode"],
                        "file": entry["file"],
                        "reason": "Authoring subcode lacks 2026-06-17 inventory support, manualRefs, and needsManualReview flag.",
                    }
                )
            elif has_inventory_support and not entry["manualRefs"] and not entry["needsManualReview"]:
                issues["authoringSubcodesWithoutSourceOrReviewFlag"].append(
                    {
                        "code": code,
                        "parentCode": entry["parentCode"],
                        "file": entry["file"],
                        "reason": "Authoring subcode is found in the new manuals but lacks structured source refs or review flag in authoring.",
                    }
                )

    for record in visa_records:
        code = record.get("code")
        canonical = code_set(record.get("subcodes"))
        legacy = code_set(record.get("subCodes"))
        if canonical is not None and legacy is not None and canonical != legacy:
            issues["generatedSubcodeParityIssues"].append(
                {
                    "code": code,
                    "canonicalOnly": sorted(canonical - legacy),
                    "legacyOnly": sorted(legacy - canonical),
                    "reason": "Generated `subcodes` and legacy `subCodes` code sets differ.",
                }
            )
        if canonical is None and legacy:
            issues["generatedSubcodeParityIssues"].append(
                {
                    "code": code,
                    "legacyOnly": sorted(legacy),
                    "reason": "Generated record has legacy `subCodes` but no canonical `subcodes` array.",
                }
            )

    if visa_records != backend_records:
        issues["generatedFileSyncIssues"].append(
            {
                "files": [rel(VISA_DATA), rel(BACKEND_VISAS)],
                "reason": "Generated visa_data.json and backend/data/visas.json differ.",
            }
        )

    for item in items:
        code = item["code"]
        if not item["shouldBeSearchable"]:
            continue
        if code == "K-STAR":
            found = code in visa_by_code or any(code in (record.get("searchAliases") or []) for record in visa_records)
        else:
            found = (
                code in visa_by_code
                or code in visa_subcodes
                or any(code in (record.get("searchAliases") or []) for record in visa_records)
                or bool(authoring_subcodes.get(code))
            )
        if not found:
            issues["exactCodeSearchIssues"].append(
                {
                    "code": code,
                    "classification": item["classification"],
                    "reason": "Code is marked searchable in inventory but not found in generated records, generated subcodes, authoring subcodes, or parent search aliases.",
                }
            )

    issue_counts = {key: len(value) for key, value in issues.items()}
    report = {
        "manualVersion": inventory["manualVersion"],
        "sourceDate": inventory["sourceDate"],
        "sourceDates": inventory.get("sourceDates", {"visa": inventory["sourceDate"]}),
        "inputs": {
            "inventory": rel(INVENTORY),
            "authoringStatuses": rel(STATUSES_DIR),
            "visaData": rel(VISA_DATA),
            "backendVisas": rel(BACKEND_VISAS),
        },
        "summary": {
            "manualCodes": len(items),
            "representedManualActiveOrSpecialCodes": len(sorted(set(represented))),
            "explicitExclusions": len(explicit_exclusions),
            "issueCounts": issue_counts,
            "passes": all(count == 0 for count in issue_counts.values()),
        },
        "representedCodes": sorted(set(represented)),
        "explicitExclusions": explicit_exclusions,
        "issues": issues,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote {rel(REPORT)}")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    if not report["summary"]["passes"]:
        print("[coverage] FAIL — see report issues for required manual refresh work.")
        return 1
    print("[coverage] OK — manual inventory coverage checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
