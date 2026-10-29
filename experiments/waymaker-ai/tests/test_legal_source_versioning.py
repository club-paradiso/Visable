"""Unit tests for Artemis Legal Source Versioning (Mission 005-A Workstream C).

Verifies:
1. Source registration and immutable SHA-256 integrity.
2. Chronological version tracking and latest version retrieval.
3. Automated version-difference impact reporting.
4. Catalog JSON serialization and re-loading.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from artemis_bootstrap.legal_source_versioning import (
    LegalAuditClassification,
    LegalSourceCatalog,
    LegalSourceType,
    LegalSourceVersion,
    VersionDifferenceImpact,
    compute_content_sha256,
    generate_version_difference_report,
)


@pytest.fixture
def sample_source_v1():
    text = "구 출입국관리법 제17조 규정 내용"
    return LegalSourceVersion(
        source_id="SRC-STAT-001",
        version_id="법률 제19000호",
        title="출입국관리법 구법",
        issuing_authority="법무부",
        source_type=LegalSourceType.STATUTE,
        publication_date="2023-01-01",
        effective_date="2023-01-01",
        retrieval_date="2026-10-29",
        official_url="https://www.law.go.kr/법령/출입국관리법",
        provision="제17조",
        excerpt_text=text,
        content_sha256=compute_content_sha256(text),
        is_superseded=True,
        superseded_by="법률 제21857호",
    )


@pytest.fixture
def sample_source_v2():
    text = "현행 출입국관리법 제17조 개정 규정 내용"
    return LegalSourceVersion(
        source_id="SRC-STAT-001",
        version_id="법률 제21857호",
        title="출입국관리법 현행",
        issuing_authority="법무부",
        source_type=LegalSourceType.STATUTE,
        publication_date="2026-09-29",
        effective_date="2026-10-02",
        retrieval_date="2026-10-29",
        official_url="https://www.law.go.kr/법령/출입국관리법",
        provision="제17조",
        excerpt_text=text,
        content_sha256=compute_content_sha256(text),
        is_superseded=False,
        prior_versions=["법률 제19000호"],
    )


def test_catalog_register_and_retrieve(sample_source_v1, sample_source_v2):
    catalog = LegalSourceCatalog()
    catalog.register(sample_source_v1)
    catalog.register(sample_source_v2)

    retrieved_v1 = catalog.get("SRC-STAT-001", "법률 제19000호")
    assert retrieved_v1 is not None
    assert retrieved_v1.is_superseded is True
    assert retrieved_v1.superseded_by == "법률 제21857호"

    latest = catalog.get_latest_version("SRC-STAT-001")
    assert latest is not None
    assert latest.version_id == "법률 제21857호"
    assert latest.effective_date == "2026-10-02"


def test_catalog_integrity_conflict_rejection(sample_source_v1):
    catalog = LegalSourceCatalog()
    catalog.register(sample_source_v1)

    # Attempt to register same (source_id, version_id) with altered text and hash
    tampered = LegalSourceVersion(
        source_id=sample_source_v1.source_id,
        version_id=sample_source_v1.version_id,
        title=sample_source_v1.title,
        issuing_authority=sample_source_v1.issuing_authority,
        source_type=sample_source_v1.source_type,
        publication_date=sample_source_v1.publication_date,
        effective_date=sample_source_v1.effective_date,
        retrieval_date=sample_source_v1.retrieval_date,
        official_url=sample_source_v1.official_url,
        provision=sample_source_v1.provision,
        excerpt_text="위조된 텍스트",
        content_sha256=compute_content_sha256("위조된 텍스트"),
    )

    with pytest.raises(ValueError, match="Integrity conflict"):
        catalog.register(tampered)


def test_version_difference_report_detects_superseded_candidates(sample_source_v1, sample_source_v2):
    catalog = LegalSourceCatalog()
    catalog.register(sample_source_v1)
    catalog.register(sample_source_v2)

    # Candidate referencing the old superseded version
    candidates = [
        {
            "id": "CAND-001",
            "legal_basis": {
                "claimed_basis": "SRC-STAT-001",
                "document_version": "법률 제19000호",
            },
        },
        {
            "id": "CAND-002",
            "legal_basis": {
                "claimed_basis": "SRC-STAT-001",
                "document_version": "법률 제21857호",
            },
        },
    ]

    report = generate_version_difference_report(catalog, candidates)
    assert report["total_impacts"] == 1
    impact = report["impacts"][0]
    assert impact["item_id"] == "CAND-001"
    assert impact["old_version_id"] == "법률 제19000호"
    assert impact["new_version_id"] == "법률 제21857호"
    assert impact["impact_level"] == "high"


def test_catalog_save_and_load(tmp_path, sample_source_v1, sample_source_v2):
    save_path = tmp_path / "catalog.json"
    catalog = LegalSourceCatalog(storage_path=save_path)
    catalog.register(sample_source_v1)
    catalog.register(sample_source_v2)
    catalog.save()

    assert save_path.exists()
    loaded_catalog = LegalSourceCatalog(storage_path=save_path)
    assert loaded_catalog.get("SRC-STAT-001", "법률 제19000호") is not None
    assert loaded_catalog.get("SRC-STAT-001", "법률 제21857호") is not None
