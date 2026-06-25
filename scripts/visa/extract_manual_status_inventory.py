#!/usr/bin/env python3
"""Build status/subcode inventory and audit matrix from 2026 PDF sections."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUSES_DIR = ROOT / "backend/data/visa_authoring/statuses"
SECTION_FILES = {
    "stay_manual_260623": ROOT / "backend/data/sources/manuals/260623_stay_manual_sections.json",
    "visa_manual_260617": ROOT / "backend/data/sources/manuals/260617_visa_manual_sections.json",
}
INVENTORY_JSON = ROOT / "backend/data/audits/manual_status_inventory_2026.json"
INVENTORY_MD = ROOT / "backend/data/audits/manual_status_inventory_2026.md"
MATRIX_JSON = ROOT / "backend/data/audits/status_matrix_2026_pdf_refresh.json"

CODE_RE = re.compile(r"\b[A-H]-\d{1,2}(?:-[0-9A-Z]+)?\b|\bK-STAR\b|\bREGION-S\b|\bYOUTH-STAY\b")
MAIN_STATUS_RE = re.compile(r"^(?P<code>[A-H]-\d{1,2}|K-STAR|REGION-S|YOUTH-STAY)$")


def code_sort_key(code: str) -> tuple:
    if code in {"K-STAR", "REGION-S", "YOUTH-STAY"}:
        return ("Z", code)
    parts = code.split("-")
    out: list[object] = [parts[0]]
    for part in parts[1:]:
        match = re.match(r"(\d+)(.*)", part)
        if match:
            out.extend([int(match.group(1)), match.group(2)])
        else:
            out.extend([999, part])
    return tuple(out)


def parent_code(code: str) -> str:
    if code in {"K-STAR", "REGION-S", "YOUTH-STAY"}:
        return code
    parts = code.split("-")
    return "-".join(parts[:2])


def snippet(text: str, code: str, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    idx = clean.find(code)
    if idx < 0:
        return clean[:limit]
    start = max(0, idx - 70)
    return clean[start : start + limit].strip()


def name_candidate(text: str, code: str) -> str:
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if code not in line or len(line) > 160:
            continue
        before = line.split(code, 1)[0].strip(" -·:()[]0123456789.")
        after = line.split(code, 1)[1].strip(" -·:()[]")
        candidate = before or after
        candidate = CODE_RE.sub("", candidate).strip(" -·:()[]")
        if 1 <= len(candidate) <= 60:
            return candidate
    return ""


def load_authoring() -> tuple[dict[str, dict], dict[str, list[dict]]]:
    statuses: dict[str, dict] = {}
    subcodes: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(STATUSES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        code = data["code"]
        statuses[code] = {"path": str(path.relative_to(ROOT)), "data": data}
        for sub in data.get("subcodes") or []:
            subcode = sub.get("code")
            if subcode:
                subcodes[subcode].append({"parent": code, "path": str(path.relative_to(ROOT)), "data": sub})
    return statuses, subcodes


def load_sections() -> list[dict]:
    out: list[dict] = []
    for source_key, path in SECTION_FILES.items():
        for section in json.loads(path.read_text(encoding="utf-8")):
            section["manual_key"] = source_key
            out.append(section)
    return out


def build() -> tuple[dict, list[dict]]:
    statuses, authoring_subcodes = load_authoring()
    sections = load_sections()
    occurrences: dict[str, list[dict]] = defaultdict(list)
    for section in sections:
        text = section.get("text") or ""
        for code in sorted(set(CODE_RE.findall(text)), key=code_sort_key):
            occurrences[code].append(
                {
                    "source_id": section["source_id"],
                    "manual_key": section["manual_key"],
                    "domain": section["domain"],
                    "page": section["page"],
                    "heading": section.get("heading") or "",
                    "snippet": snippet(text, code),
                    "name_candidate": name_candidate(text, code),
                }
            )

    all_codes = set(occurrences) | set(statuses) | set(authoring_subcodes)
    parent_to_subcodes: dict[str, list[dict]] = defaultdict(list)
    for code in all_codes:
        if code in statuses and MAIN_STATUS_RE.match(code):
            continue
        parent = parent_code(code)
        refs = occurrences.get(code, [])
        parent_to_subcodes[parent].append(
            {
                "code": code,
                "name_ko": (authoring_subcodes.get(code) or [{}])[0].get("data", {}).get("nameKo")
                or (authoring_subcodes.get(code) or [{}])[0].get("data", {}).get("name")
                or (refs[0]["name_candidate"] if refs else ""),
                "description": refs[0]["snippet"] if refs else "",
                "source_id": refs[0]["source_id"] if refs else "",
                "page": refs[0]["page"] if refs else "",
                "heading": refs[0]["heading"] if refs else "",
            }
        )

    items = []
    for code in sorted(all_codes, key=code_sort_key):
        if code != parent_code(code) and code not in statuses:
            continue
        refs = occurrences.get(code, [])
        source_manuals = {ref["manual_key"] for ref in refs}
        author = statuses.get(code, {}).get("data", {})
        items.append(
            {
                "code": code,
                "name_ko": author.get("name") or (refs[0]["name_candidate"] if refs else ""),
                "domain_presence": {
                    "stay_manual_260623": "stay_manual_260623" in source_manuals,
                    "visa_manual_260617": "visa_manual_260617" in source_manuals,
                },
                "subcodes": sorted(parent_to_subcodes.get(code, []), key=lambda row: code_sort_key(row["code"])),
                "source_evidence": [
                    {
                        "source_id": ref["source_id"],
                        "page": ref["page"],
                        "heading": ref["heading"],
                        "snippet": ref["snippet"],
                    }
                    for ref in refs[:12]
                ],
            }
        )

    matrix = []
    for item in items:
        code = item["code"]
        refs = item["source_evidence"]
        in_authoring = code in statuses
        in_subcodes = code in authoring_subcodes
        canonical = "canonical" if in_authoring else ("scenario_help" if in_subcodes else "missing")
        if code == "D-2-R" and not refs:
            canonical = "invalid"
        recommended_action = "update" if canonical == "canonical" else "preserve"
        if canonical == "missing":
            recommended_action = "needs_human_review"
        matrix.append(
            {
                "code": code,
                "official_ko_name": item["name_ko"],
                "paradiso_record_path": statuses.get(code, {}).get("path")
                or "; ".join(sorted({entry["path"] for entry in authoring_subcodes.get(code, [])})),
                "canonical_status": canonical,
                "manual_discovery": "both" if refs and (in_authoring or in_subcodes) else ("manual_inventory" if refs else "existing_paradiso"),
                "stay_manual_presence": "present" if item["domain_presence"]["stay_manual_260623"] else "absent",
                "visa_manual_presence": "present" if item["domain_presence"]["visa_manual_260617"] else "absent",
                "subcodes_found": [row["code"] for row in item["subcodes"]],
                "stay_guidance_changed": False,
                "visa_guidance_changed": False,
                "subcode_detail_changed": False,
                "documents_changed": False,
                "notes_changed": False,
                "source_metadata_changed": canonical in {"canonical", "scenario_help"},
                "removed_legacy_claims": [],
                "source_evidence": refs[:6],
                "online_supplement_sources": [],
                "ui_impact": "Source badges and subcode disclosure use PDF-derived source metadata; no broad redesign.",
                "waymaker_impact": "Manual source metadata points to readable PDF-derived text; visa and stay domains remain separated.",
                "recommended_action": recommended_action,
            }
        )

    inventory = {
        "manual_version": "2026.6",
        "sources": {
            "stay_manual_260623": "backend/data/sources/manuals/260623_stay_manual_exported.pdf",
            "visa_manual_260617": "backend/data/sources/manuals/260617_visa_manual_exported.pdf",
        },
        "summary": {
            "inventory_codes": len(items),
            "manual_codes": len([item for item in items if item["source_evidence"]]),
            "manual_subcodes": sum(len(item["subcodes"]) for item in items),
            "presence_counts": dict(Counter(ref["source_id"] for refs in occurrences.values() for ref in refs)),
        },
        "items": items,
    }
    return inventory, matrix


def write_markdown(inventory: dict, matrix: list[dict]) -> None:
    lines = ["# Manual Status Inventory 2026", ""]
    lines.append("## Summary")
    for key, value in inventory["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Codes"])
    for item in inventory["items"]:
        presence = []
        if item["domain_presence"]["stay_manual_260623"]:
            presence.append("stay")
        if item["domain_presence"]["visa_manual_260617"]:
            presence.append("visa")
        subcodes = ", ".join(row["code"] for row in item["subcodes"][:20])
        if len(item["subcodes"]) > 20:
            subcodes += f", ... (+{len(item['subcodes']) - 20})"
        lines.append(f"- `{item['code']}` {item['name_ko']} ({'/'.join(presence) or 'not found in manuals'}): {subcodes or 'no subcodes'}")
    lines.extend(["", "## Matrix Counts"])
    counts = Counter(row["canonical_status"] for row in matrix)
    for key, value in sorted(counts.items()):
        lines.append(f"- {key}: {value}")
    INVENTORY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    INVENTORY_JSON.parent.mkdir(parents=True, exist_ok=True)
    inventory, matrix = build()
    INVENTORY_JSON.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MATRIX_JSON.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(inventory, matrix)
    print(json.dumps({"inventory": inventory["summary"], "matrix_rows": len(matrix)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
