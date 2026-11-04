"""Corpus validation: schema, integrity, translation honesty, secrets.

The validator is the corpus's fail-closed gate. If anything fails, the
corpus (or the affected version) must be treated as
``VERIFICATION_REQUIRED`` — never silently presented as verified law.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

REQUIRED_METADATA_FIELDS = [
    "lawId",
    "titleKo",
    "titleEn",
    "jurisdiction",
    "lawType",
    "promulgationDate",
    "effectiveFrom",
    "effectiveUntil",
    "sourceProvider",
    "sourceUrl",
    "sourceIdentifier",
    "retrievedAt",
    "lastVerifiedAt",
    "contentSha256",
    "sourceFormat",
    "language",
    "translationProvider",
    "translationUpdatedAt",
    "translationAlignment",
    "reusePermission",
    "verificationStatus",
]

TRANSLATION_STATUSES = {"ALIGNED", "OLDER_TRANSLATION", "PARTIAL", "UNVERIFIED", "NOT_AVAILABLE"}
VERIFICATION_STATUSES = {"VERIFIED_OFFICIAL_SNAPSHOT", "VERIFICATION_REQUIRED", "SOURCE_UNAVAILABLE"}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SECRET_PATTERNS = [
    re.compile(r"LAW_API_OC\s*=\s*\S+"),
    re.compile(r"OC=[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+"),  # an OC is an email prefix; never in files
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
]


def canonical_json_hash(obj: Any) -> str:
    """SHA-256 of the canonical JSON encoding used corpus-wide."""
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_metadata(meta: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field in REQUIRED_METADATA_FIELDS:
        if field not in meta:
            errors.append(f"missing field: {field}")
    if errors:
        return errors
    if not re.fullmatch(r"\d{6}", str(meta["lawId"])):
        errors.append(f"lawId must be a 6-digit DRF identifier: {meta['lawId']!r}")
    for field in ("promulgationDate", "effectiveFrom", "effectiveUntil"):
        value = meta[field]
        if value is None:
            continue
        if not _DATE.match(str(value)):
            errors.append(f"{field} is not an ISO date: {value!r}")
            continue
        try:
            date.fromisoformat(str(value))
        except ValueError:
            errors.append(f"{field} is not a real calendar date: {value!r}")
    if meta["promulgationDate"] and meta["effectiveFrom"] and meta["promulgationDate"] > meta["effectiveFrom"]:
        errors.append("promulgationDate is after effectiveFrom")
    if not _SHA256.match(str(meta["contentSha256"])):
        errors.append("contentSha256 is not a SHA-256 hex digest")
    if meta["translationAlignment"] not in TRANSLATION_STATUSES:
        errors.append(f"unknown translationAlignment: {meta['translationAlignment']!r}")
    if meta["verificationStatus"] not in VERIFICATION_STATUSES:
        errors.append(f"unknown verificationStatus: {meta['verificationStatus']!r}")
    if meta["language"] != "ko":
        errors.append("primary corpus language must be 'ko'")
    return errors


def validate_articles(articles: List[Dict[str, Any]], priority_articles: List[str] | None = None) -> List[str]:
    errors: List[str] = []
    ids = [a["articleId"] for a in articles]
    if len(ids) != len(set(ids)):
        errors.append("duplicate articleId values present")
    for art in articles:
        if not art.get("deleted") and not art.get("text"):
            errors.append(f"article {art['articleId']} has no text and is not marked deleted")
        digest = hashlib.sha256((art.get("text") or "").encode("utf-8")).hexdigest()
        if art.get("textSha256") != digest:
            errors.append(f"article {art['articleId']} textSha256 mismatch")
    for wanted in priority_articles or []:
        if wanted not in set(ids):
            errors.append(f"priority article missing: {wanted}")
    return errors


def scan_for_secrets(root: Path) -> List[str]:
    findings: List[str] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix not in {".pdf", ".hwp", ".hwpx"}:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pattern in _SECRET_PATTERNS:
                if pattern.search(text):
                    findings.append(f"possible secret in {path.relative_to(root)}: {pattern.pattern[:24]}…")
    return findings


def validate_corpus(corpus_root: Path) -> Dict[str, Any]:
    """Validate the whole committed corpus. Returns a report dict."""
    errors: List[str] = []
    warnings: List[str] = []
    manifest_path = corpus_root / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "errors": ["manifest.json missing"], "warnings": [], "versionsChecked": 0}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    versions_checked = 0
    for law in manifest.get("laws", []):
        for version in law.get("versions", []):
            versions_checked += 1
            vdir = corpus_root / version["path"]
            label = f"{law['slug']}@{version['effectiveFrom']}"
            if not vdir.is_dir():
                errors.append(f"{label}: version directory missing: {version['path']}")
                continue
            meta_file = vdir / "metadata.json"
            if not meta_file.exists():
                errors.append(f"{label}: metadata.json missing")
                continue
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            errors.extend(f"{label}: {e}" for e in validate_metadata(meta))
            if meta["effectiveFrom"] != version["effectiveFrom"]:
                errors.append(f"{label}: manifest/metadata effectiveFrom mismatch")
            if meta["sourceIdentifier"] != version["sourceIdentifier"]:
                errors.append(f"{label}: manifest/metadata sourceIdentifier (MST) mismatch")

            articles_file = vdir / "articles.ko.json"
            if not articles_file.exists():
                errors.append(f"{label}: articles.ko.json missing")
                continue
            articles_doc = json.loads(articles_file.read_text(encoding="utf-8"))
            articles = articles_doc.get("articles", [])
            errors.extend(f"{label}: {e}" for e in validate_articles(articles))
            if canonical_json_hash(articles_doc) != meta["contentSha256"]:
                errors.append(f"{label}: contentSha256 does not match articles.ko.json")
            if not (vdir / "ko.md").exists():
                errors.append(f"{label}: ko.md missing")
            if not (vdir / "source.json").exists():
                errors.append(f"{label}: source.json missing")

            # Translation honesty guards.
            translation_file = vdir / "translation.json"
            if not translation_file.exists():
                errors.append(f"{label}: translation.json missing")
            else:
                translation = json.loads(translation_file.read_text(encoding="utf-8"))
                if translation.get("status") != meta["translationAlignment"]:
                    errors.append(f"{label}: translation.json status != metadata.translationAlignment")
                if translation.get("status") == "NOT_AVAILABLE" and translation.get("pairs"):
                    errors.append(f"{label}: NOT_AVAILABLE translation must not carry alignment pairs")
            # English body text must never be committed (KLRI licence).
            for forbidden in ("en.md", "articles.en.json"):
                if (vdir / forbidden).exists():
                    errors.append(
                        f"{label}: {forbidden} must not be committed — official English "
                        "translations are metadata-only in this corpus (see SOURCE_POLICY.md)"
                    )

    errors.extend(scan_for_secrets(corpus_root))
    return {"ok": not errors, "errors": errors, "warnings": warnings, "versionsChecked": versions_checked}
