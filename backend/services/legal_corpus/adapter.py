"""Read-only adapter from the enforcement features to the legal corpus.

The adapter never computes money and never mutates the corpus or the
calculator rules. It answers three questions for a case date:

1. Which stored Korean version was in force on that date?
2. What does the verified article text say?
3. How certain are we — stated with the corpus status vocabulary:

   * ``LOCAL_OFFICIAL_SNAPSHOT`` — the applicable version is the newest
     stored snapshot. It was verified against the official source at
     ``lastVerifiedAt``, but no live API re-check happened just now, so
     it must not be presented as ``LIVE_VERIFIED``.
   * ``HISTORICAL_VERSION_VERIFIED`` — the applicable version is an
     older, preserved version (the normal case for past violations).
   * ``TRANSLATION_OUTDATED`` — attached when the official English
     translation for the applicable version is older than the Korean
     text; the Korean text remains authoritative.
   * ``VERIFICATION_REQUIRED`` — no stored version covers the date, or
     the stored version is not verified. Callers must not present a
     definite legal basis in this state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CORPUS_ROOT = Path(__file__).resolve().parents[2] / "data" / "legal-corpus"


class LegalCorpus:
    def __init__(self, corpus_root: Path | None = None):
        self.root = Path(corpus_root) if corpus_root else DEFAULT_CORPUS_ROOT
        manifest_file = self.root / "manifest.json"
        self.manifest: Dict[str, Any] = (
            json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {"laws": []}
        )
        self._articles_cache: Dict[str, Dict[str, Any]] = {}

    # -- lookups -----------------------------------------------------------

    def _law(self, slug: str) -> Optional[Dict[str, Any]]:
        return next((law for law in self.manifest.get("laws", []) if law["slug"] == slug), None)

    def versions(self, slug: str) -> List[Dict[str, Any]]:
        law = self._law(slug)
        if not law:
            return []
        return sorted(law.get("versions", []), key=lambda v: v["effectiveFrom"])

    def resolve_version(self, slug: str, on_date: str) -> Optional[Dict[str, Any]]:
        """The stored version in force on ``on_date`` (ISO date), or None."""
        applicable = None
        for version in self.versions(slug):
            if version["effectiveFrom"] <= on_date:
                applicable = version
            else:
                break
        return applicable

    def _load_version_doc(self, version: Dict[str, Any]) -> Dict[str, Any]:
        key = version["path"]
        if key not in self._articles_cache:
            vdir = self.root / version["path"]
            self._articles_cache[key] = {
                "metadata": json.loads((vdir / "metadata.json").read_text(encoding="utf-8")),
                "articles": json.loads((vdir / "articles.ko.json").read_text(encoding="utf-8"))["articles"],
                "translation": json.loads((vdir / "translation.json").read_text(encoding="utf-8"))
                if (vdir / "translation.json").exists()
                else {},
            }
        return self._articles_cache[key]

    # -- public API ----------------------------------------------------------

    def get_article(self, slug: str, article_id: str, on_date: str) -> Dict[str, Any]:
        """Verified article text applicable on ``on_date`` + certainty state."""
        version = self.resolve_version(slug, on_date)
        if version is None:
            return {
                "status": "VERIFICATION_REQUIRED",
                "reason": "NO_STORED_VERSION_COVERS_DATE",
                "lawSlug": slug,
                "articleId": article_id,
                "onDate": on_date,
                "article": None,
            }
        doc = self._load_version_doc(version)
        meta = doc["metadata"]
        article = next((a for a in doc["articles"] if a["articleId"] == article_id), None)
        if article is None:
            return {
                "status": "VERIFICATION_REQUIRED",
                "reason": "ARTICLE_NOT_IN_STORED_VERSION",
                "lawSlug": slug,
                "articleId": article_id,
                "onDate": on_date,
                "version": version,
                "article": None,
            }
        versions = self.versions(slug)
        is_latest = versions and versions[-1]["effectiveFrom"] == version["effectiveFrom"]
        if meta.get("verificationStatus") != "VERIFIED_OFFICIAL_SNAPSHOT":
            status = "VERIFICATION_REQUIRED"
        elif is_latest:
            status = "LOCAL_OFFICIAL_SNAPSHOT"
        else:
            status = "HISTORICAL_VERSION_VERIFIED"
        result: Dict[str, Any] = {
            "status": status,
            "lawSlug": slug,
            "articleId": article_id,
            "onDate": on_date,
            "version": {
                "effectiveFrom": version["effectiveFrom"],
                "promulgationNo": meta.get("promulgationNo"),
                "sourceUrl": meta.get("sourceUrl"),
                "lastVerifiedAt": meta.get("lastVerifiedAt"),
            },
            "article": {
                "articleId": article["articleId"],
                "titleKo": article.get("titleKo"),
                "deleted": bool(article.get("deleted")),
                "text": article.get("text"),
                "textSha256": article.get("textSha256"),
            },
            "translationStatus": doc["translation"].get("status"),
        }
        if doc["translation"].get("status") == "OLDER_TRANSLATION":
            result["translationNote"] = "TRANSLATION_OUTDATED: 공식 영문 번역본이 한국어 현행본보다 오래되었습니다. 한국어 원문이 기준입니다."
        return result

    def version_coverage(self, slug: str, start: str, end: str) -> Dict[str, Any]:
        """Which stored versions cover a violation period [start, end].

        A violation spanning a revision boundary needs every version in
        the span; a gap means part of the period is unverifiable locally.
        """
        versions = self.versions(slug)
        covering = []
        for idx, version in enumerate(versions):
            v_from = version["effectiveFrom"]
            v_until = versions[idx + 1]["effectiveFrom"] if idx + 1 < len(versions) else None
            if v_from <= end and (v_until is None or v_until > start):
                covering.append(version)
        gap = not covering or covering[0]["effectiveFrom"] > start
        return {
            "lawSlug": slug,
            "period": {"start": start, "end": end},
            "versions": covering,
            "hasGap": gap,
            "status": "VERIFICATION_REQUIRED" if gap else "COVERED_BY_STORED_VERSIONS",
        }
