"""Data-integrity tests for the committed legal corpus snapshot.

These tests verify the *committed data* (not the network): schema fields,
hash chains, priority articles, translation bookkeeping, the Annex 7
comparison, and the rule that no English body text is stored anywhere.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.services.legal_corpus import registry
from backend.services.legal_corpus.annex7 import compare_with_legal_rules, sniff_format
from backend.services.legal_corpus.parser import sha256_text
from backend.services.legal_corpus.validator import (
    canonical_json_hash,
    scan_for_secrets,
    validate_corpus,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = REPO_ROOT / "backend" / "data" / "legal-corpus"
LEGAL_RULES_PATH = REPO_ROOT / "backend" / "data" / "enforcement" / "legal_rules.json"

P0_LAWS = [registry.IMMIGRATION_ACT, registry.IMMIGRATION_DECREE, registry.IMMIGRATION_RULE]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _version_dirs():
    manifest = _load(CORPUS_ROOT / "manifest.json")
    for law in manifest["laws"]:
        for version in law["versions"]:
            yield law, version, CORPUS_ROOT / version["path"]


def test_whole_corpus_validates():
    report = validate_corpus(CORPUS_ROOT)
    assert report["ok"], report["errors"]
    assert report["errors"] == []
    assert report["versionsChecked"] == 6


def test_manifest_covers_exactly_the_p0_laws():
    manifest = _load(CORPUS_ROOT / "manifest.json")
    by_slug = {law["slug"]: law for law in manifest["laws"]}
    assert set(by_slug) == {law["slug"] for law in P0_LAWS}
    for law in P0_LAWS:
        entry = by_slug[law["slug"]]
        # Law identity must match the official identifiers exactly — a
        # similar-looking law must never slip in under a partial name match.
        assert entry["lawId"] == law["lawId"]
        assert entry["titleKo"] == law["titleKo"]
        assert len(entry["versions"]) >= 2  # current + at least one preserved version


def test_every_version_metadata_and_hash_chain():
    for law, version, vdir in _version_dirs():
        meta = _load(vdir / "metadata.json")
        assert meta["lawId"] == law["lawId"]
        assert meta["effectiveFrom"] == version["effectiveFrom"]
        assert meta["sourceIdentifier"] == version["sourceIdentifier"]
        assert meta["verificationStatus"] == "VERIFIED_OFFICIAL_SNAPSHOT"
        assert meta["sourceUrl"].startswith("https://www.law.go.kr/")
        articles_doc = _load(vdir / "articles.ko.json")
        # The recorded content hash must be the hash of the stored articles.
        assert meta["contentSha256"] == canonical_json_hash(articles_doc)
        for article in articles_doc["articles"]:
            if article["deleted"]:
                assert article["text"] == ""
            else:
                assert article["textSha256"] == sha256_text(article["text"])


def test_priority_articles_present_in_every_version():
    reg_by_slug = {law["slug"]: law for law in P0_LAWS}
    for law, _version, vdir in _version_dirs():
        articles = _load(vdir / "articles.ko.json")["articles"]
        ids = {a["articleId"] for a in articles}
        for wanted in reg_by_slug[law["slug"]]["priority_articles"]:
            assert wanted in ids, f"{law['slug']} missing priority article {wanted}"


def test_no_english_body_text_is_stored():
    # KLRI / ministerial translations may not be redistributed: the corpus
    # must never contain English body files.
    offenders = [
        str(p.relative_to(CORPUS_ROOT))
        for p in CORPUS_ROOT.rglob("*")
        if p.name in {"en.md", "articles.en.json"}
    ]
    assert offenders == []
    # …but every version must carry explicit translation bookkeeping.
    for _law, _version, vdir in _version_dirs():
        assert (vdir / "translation.json").exists()


def test_translation_alignment_facts():
    manifest = _load(CORPUS_ROOT / "manifest.json")
    by_key = {}
    for law in manifest["laws"]:
        for version in law["versions"]:
            by_key[(law["slug"], version["effectiveFrom"])] = version["translationAlignment"]

    # Same-version official translations exist for these two snapshots.
    assert by_key[("immigration-act", "2026-01-23")] == "ALIGNED"
    assert by_key[("immigration-decree", "2025-06-01")] == "ALIGNED"
    # The current versions are ahead of the newest official translation.
    assert by_key[("immigration-act", "2026-10-02")] == "OLDER_TRANSLATION"
    assert by_key[("immigration-decree", "2026-10-02")] == "OLDER_TRANSLATION"
    # The Rule has no served English body at all.
    assert by_key[("immigration-rule", "2026-01-23")] == "NOT_AVAILABLE"
    assert by_key[("immigration-rule", "2026-10-23")] == "NOT_AVAILABLE"

    # ALIGNED versions pair every Korean article; NOT_AVAILABLE pairs none.
    for law, version, vdir in _version_dirs():
        translation = _load(vdir / "translation.json")
        ko_count = len(_load(vdir / "articles.ko.json")["articles"])
        if translation["status"] == "ALIGNED":
            assert len(translation["pairs"]) == ko_count
            assert all(p["status"] == "ALIGNED" for p in translation["pairs"])
            assert all(p["englishTextSha256"] for p in translation["pairs"])
        if translation["status"] == "NOT_AVAILABLE":
            assert translation["pairs"] == []


def test_decree_article_26_2_is_about_reporting_not_permission():
    # Article 26-2 of the Decree is the report-based workplace change rule
    # (신고) for E-1…E-7 holders meeting the MOJ notice — it must not be
    # conflated with the permission (허가) track of Act Article 21(1).
    doc = _load(CORPUS_ROOT / "laws" / "immigration-decree" / "versions" / "2025-06-01" / "articles.ko.json")
    article = next(a for a in doc["articles"] if a["articleId"] == "26-2")
    assert "신고" in article["text"]
    assert "법무부장관" in article["text"] and "고시" in article["text"]


def test_moj_notice_2020_212_stored():
    notice_dir = CORPUS_ROOT / "notices" / "moj-notice-2020-212-workplace-report-eligibility"
    meta = _load(notice_dir / "metadata.json")
    assert "2020-212" in meta["noticeNo"]
    body = (notice_dir / "ko.md").read_text(encoding="utf-8")
    for code in ("E-1", "E-2", "E-7"):
        assert code in body
    assert "E-6-2" in body  # the stated exclusion must be present


def test_annex7_structure_and_calculator_comparison():
    annex_dir = CORPUS_ROOT / "annexes" / "immigration-rule-annex-7" / "versions" / "2026-01-23"
    annex = _load(annex_dir / "annex7.json")
    assert annex["revisedDate"] == "2026-01-23"
    assert len(annex["items"]) == 60
    assert all(not item["needsManualReview"] for item in annex["items"])
    bases = {item["basis"] for item in annex["items"]}
    assert bases == {"PERIOD", "PERSON_COUNT", "RECURRENCE", "REFERENCE"}

    pdf_bytes = (annex_dir / "annex7.pdf").read_bytes()
    assert sniff_format(pdf_bytes) == "pdf"

    legal_rules = _load(LEGAL_RULES_PATH)
    comparison = compare_with_legal_rules(annex, legal_rules)
    compared = comparison["comparisons"]
    assert len(compared) == 5
    assert all(c["status"] == "MATCH" for c in compared), compared


def test_existing_legal_rules_file_untouched():
    # The corpus work must not replace the calculator's rule file.
    rules_doc = _load(LEGAL_RULES_PATH)
    assert len(rules_doc["snapshots"]) == 1
    snapshot = rules_doc["snapshots"][0]
    assert snapshot["id"] == "kr-immigration-enforcement-2026-01-23"
    assert snapshot["effectiveFrom"] == "2026-01-23"
    assert len(snapshot["rules"]) == 5


def test_no_secrets_anywhere_in_corpus():
    assert scan_for_secrets(CORPUS_ROOT) == []


def test_coverage_report_consistency():
    coverage = _load(CORPUS_ROOT / "coverage-report.json")
    total_ko = sum(
        version["articleCount"]
        for law in coverage["laws"]
        for version in law["versions"]
    )
    assert total_ko == 1129
    aligned = sum(
        version["englishArticleCount"] or 0
        for law in coverage["laws"]
        for version in law["versions"]
        if version["translationAlignment"] == "ALIGNED"
    )
    assert aligned == 373
