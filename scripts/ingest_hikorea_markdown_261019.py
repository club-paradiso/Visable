#!/usr/bin/env python3
"""Import digest-pinned 2026-10-19 HiKorea Markdown as review-only documents.

Usage: python3 scripts/ingest_hikorea_markdown_261019.py PATH_TO_ZIP [--check]

This never promotes the new manual to the approved current edition, and never
changes visa_data.json, live requirements, or the AI evidence index.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

SPEC = {
    "visa": {
        "member": "261019 사증민원 자격별 안내 매뉴얼.md",
        "path": "docs/source-manuals/2026-10-19/markdown/visa_manual_261019.md",
        "sha256": "c98677f307dcb362012bfa4935e746390cd80e7e59603201529ea5f352698959",
        "bytes": 1113926, "role": "visa_issuance_manual", "id": "visa_manual_2026_10_19_md",
    },
    "stay": {
        "member": "261019 체류민원 자격별 안내 매뉴얼.md",
        "path": "docs/source-manuals/2026-10-19/markdown/stay_manual_261019.md",
        "sha256": "dd15cc8221c26e55f4d67aa5d4766782d1d79ba3b84efb9a0fb988981c76b563",
        "bytes": 1679699, "role": "stay_residence_manual", "id": "stay_manual_2026_10_19_md",
    },
}


def inspect_zip(path):
    """Read and verify both files before writing anything."""
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) != 2 or {i.filename for i in infos} != {v["member"] for v in SPEC.values()}:
            raise ValueError("ZIP must contain exactly the two named Markdown manuals")
        output = {}
        for kind, spec in SPEC.items():
            info = archive.getinfo(spec["member"])
            if info.is_dir() or info.file_size != spec["bytes"] or info.file_size > 3000000:
                raise ValueError(kind + ": unexpected file size")
            data = archive.read(info)
            if hashlib.sha256(data).hexdigest() != spec["sha256"]:
                raise ValueError(kind + ": SHA-256 mismatch")
            text = data.decode("utf-8", errors="strict")
            if not text.startswith("# 261019 ") or "2026. 10." not in text[:12000]:
                raise ValueError(kind + ": unexpected edition text")
            if "\ufffd" in text or "\x00" in text:
                raise ValueError(kind + ": invalid characters")
            lines = text.splitlines()
            table_lines = sum(line.lstrip().startswith("|") for line in lines)
            if table_lines < 100 or sum(bool(re.match(r"^\s*\|\s*:?-{3,}", l)) for l in lines) < 20:
                raise ValueError(kind + ": missing Markdown table structure")
            output[kind] = {
                "data": data, "path": spec["path"], "sha256": spec["sha256"],
                "role": spec["role"], "id": spec["id"], "bytes": len(data),
                "lines": len(lines), "table_lines": table_lines,
            }
        return output


def stage(source_zip, root, check=False):
    verified = inspect_zip(source_zip)
    if check:
        for item in verified.values():
            path = root / item["path"]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError("Missing or corrupted staged Markdown: " + str(path))
        return {"status": "verified", "files": list(verified)}

    manifest_path = root / "docs/source-manuals/source_manifest.json"
    approvals_path = root / "data/manual_approval_index.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    approvals = json.loads(approvals_path.read_text(encoding="utf-8"))
    pending = manifest.get("pending_review_editions")
    if not isinstance(pending, list):
        raise ValueError("Expected pending_review_editions list")
    staged = {x.get("role"): x for x in pending}
    for item in verified.values():
        role = item["role"]
        old = staged.get(role)
        if not old or old.get("source_date") != "2026-10-19" or old.get("status") != "pending_review":
            raise ValueError("Unknown pending edition: " + role)
        if manifest["current"][role].get("source_date") == "2026-10-19":
            raise ValueError("Unreviewed edition is already current")

    report = {"status": "needs_review", "legal_effective_date_verified": False,
              "original_hwp_table_geometry_verified": False, "runtime_grounding_approved": False,
              "files": {}}
    for kind, item in verified.items():
        target = root / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Refusing to overwrite a different staged Markdown: " + str(target))
        target.write_bytes(item["data"])
        pending_entry = staged[item["role"]]
        derived = [x for x in pending_entry.get("derived_texts", []) if x.get("id") != item["id"]]
        derived.append({
            "id": item["id"], "file": item["path"], "file_sha256": item["sha256"],
            "source_date": "2026-10-19", "status": "needs_review",
            "verification_status": "byte_verified_not_content_approved",
        })
        pending_entry["derived_texts"] = derived
        approvals["documents"][item["id"]] = {
            "approval_state": "needs_review", "effective_date": "",
            "reviewer": "", "reviewed_at": "",
            "parser": "owner-supplied HWP-to-Markdown conversion",
            "source_path": item["path"], "source_sha256": item["sha256"],
            "has_tables_or_annexes": True, "section_locator": "no_verified_pdf_pages",
            "extraction_warnings": ["Not approved as direct evidence. Compare against source HWP."],
            "table_extraction_warnings": ["Merged-cell and table geometry need independent manual review."],
        }
        report["files"][kind] = {k: v for k, v in item.items() if k != "data"}

    approvals_path.write_text(json.dumps(approvals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mirror = root / "backend/data/knowledge_deploy/manual_approval_index.json"
    if mirror.parent.is_dir():
        mirror.write_bytes(approvals_path.read_bytes())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit = root / "audits/manual-refresh-20261019/markdown-intake.json"
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source_zip", type=Path)
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    print(json.dumps(stage(args.source_zip, args.repo_root.resolve(), args.check),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
