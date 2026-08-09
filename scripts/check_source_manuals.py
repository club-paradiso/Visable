#!/usr/bin/env python3
"""Validate the current source manual manifest."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/source-manuals/source_manifest.json"
REQUIRED_ROLES = ("visa_issuance_manual", "stay_residence_manual")

# The ministry publishes 배포용 HWP; the PDF editions are exports of it. A PDF is
# pinned by its page count, which an HWP has no equivalent of — so an HWP entry
# is pinned by a recomputed SHA-256 of the declared file instead. That is a
# stronger identity check than a page count, not a weaker one, so neither format
# can be swapped underneath the manifest unnoticed.
EXPECTED_PAGES = {
    "backend/data/sources/manuals/260617_visa_manual_exported.pdf": 487,
    "backend/data/sources/manuals/260623_stay_manual_exported.pdf": 780,
}
REQUIRED_FIELDS = {
    "title_ko",
    "title_en",
    "version",
    "authority",
    "file",
    "role",
    "status",
}
PDF_ONLY_FIELDS = {"pages"}
NON_PDF_REQUIRED_FIELDS = {"file_sha256"}


def fail(message: str) -> None:
    raise SystemExit(f"[check_source_manuals] ERROR: {message}")


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        fail(f"manifest not found: {MANIFEST_PATH.relative_to(ROOT)}")
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"malformed JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")


def pdf_page_count(path: Path) -> int | None:
    pdfinfo = shutil.which("pdfinfo")
    if not pdfinfo:
        print("[check_source_manuals] WARNING: pdfinfo not found; skipping PDF page-count verification.")
        return None
    try:
        proc = subprocess.run(
            [pdfinfo, str(path)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        fail(f"pdfinfo failed for {path.relative_to(ROOT)}: {exc.stderr.strip() or exc}")
    for line in proc.stdout.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                fail(f"pdfinfo returned a non-numeric page count for {path.relative_to(ROOT)}")
    fail(f"pdfinfo did not report Pages for {path.relative_to(ROOT)}")


def main() -> None:
    manifest = load_manifest()
    current = manifest.get("current")
    if not isinstance(current, dict):
        fail("manifest must contain object field `current`")

    if set(current.keys()) != set(REQUIRED_ROLES):
        fail("manifest.current must declare exactly visa_issuance_manual and stay_residence_manual")

    seen_roles: dict[str, int] = {}
    for key in REQUIRED_ROLES:
        entry = current.get(key)
        if not isinstance(entry, dict):
            fail(f"current.{key} must be an object")

        rel_file = entry.get("file")
        if not isinstance(rel_file, str) or not rel_file.endswith((".pdf", ".hwp")):
            fail(f"current.{key}.file must be a .pdf or .hwp path")
        is_pdf = rel_file.endswith(".pdf")

        required = set(REQUIRED_FIELDS)
        required |= PDF_ONLY_FIELDS if is_pdf else NON_PDF_REQUIRED_FIELDS
        missing = sorted(required - set(entry.keys()))
        if missing:
            fail(f"current.{key} missing required field(s): {', '.join(missing)}")

        role = entry.get("role")
        status = entry.get("status")
        if role != key:
            fail(f"current.{key}.role must be {key!r}")
        if status != "current":
            fail(f"current.{key}.status must be 'current'")

        seen_roles[role] = seen_roles.get(role, 0) + 1

        path = ROOT / rel_file
        if not path.exists():
            fail(f"declared manual does not exist: {rel_file}")
        if not path.is_file():
            fail(f"declared manual is not a file: {rel_file}")

        if is_pdf:
            expected_pages = EXPECTED_PAGES.get(rel_file)
            if expected_pages is None:
                fail(f"no expected page count recorded for {rel_file}")
            if entry.get("pages") != expected_pages:
                fail(f"current.{key}.pages must be {expected_pages}")
            actual_pages = pdf_page_count(path)
            if actual_pages is not None and actual_pages != expected_pages:
                fail(f"{rel_file} has {actual_pages} pages; expected {expected_pages}")
        else:
            declared = str(entry.get("file_sha256") or "").lower()
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if declared != actual:
                fail(f"{rel_file} sha256 {actual[:12]}… does not match declared "
                     f"{declared[:12] or '(empty)'}…")

    duplicates = [role for role, count in seen_roles.items() if count != 1]
    if duplicates:
        fail(f"duplicate or missing current manual role(s): {', '.join(duplicates)}")

    print("[check_source_manuals] OK - current source manuals are registered.")


if __name__ == "__main__":
    main()
