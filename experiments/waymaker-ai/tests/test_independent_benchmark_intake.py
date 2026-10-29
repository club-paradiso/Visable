"""Unit tests for Artemis Independent Benchmark Intake & Governance (Mission 005-A).

Verifies:
1. Submission validation (catches missing questions, answers, and declarations).
2. Blind partition projection (ensures 100% removal of answer keys and rubrics).
3. Frozen dataset manifest cryptographic hashing.
4. Contamination auditor (detects duplicate or heavily overlapping questions).
5. Role-based access control (blocks model runners from reading answer keys).
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from artemis_bootstrap.independent_benchmark_intake import (
    BenchmarkSubmissionItem,
    BlindBenchmarkPartitionManager,
    ContaminationAuditor,
    ContaminationRisk,
    EvaluatorAccessController,
    EvaluatorRole,
    ExternalAuthorAttestation,
)


@pytest.fixture
def sample_attestation():
    return ExternalAuthorAttestation(
        author_id="AUTH-001",
        full_name="김철수 변호사",
        organization="대한민국 법무법인",
        license_or_credential="변호사 등록번호 12345",
        independence_confirmed=True,
        zero_leakage_attested=True,
        submission_date="2026-10-29",
        signature_digest="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )


@pytest.fixture
def sample_submission(sample_attestation):
    return BenchmarkSubmissionItem(
        submission_id="EXT-100-001",
        author_attestation=sample_attestation,
        target_visa_category="F-2-R",
        question="F-2-R 지역특화형 비자 취득 후 인구감소지역 거주의무 기간은 몇 년인가요?",
        user_context={"location": "in_korea", "current_status": "F-2-R"},
        authoritative_answer_key="최소 5년 이상 지정된 인구감소지역에 거주 및 근무하여야 합니다.",
        legal_citations=[
            {
                "statute": "출입국관리법 시행령",
                "provision": "별표 1의2 24. 거주(F-2) 파목",
                "notice": "법무부고시 제2026-248호",
            }
        ],
        rubric_spec={"required_facts": ["5년", "인구감소지역"], "negative_patterns": ["3년", "자유 이전 가능"]},
    )


def test_submission_validation_success(sample_submission):
    issues = sample_submission.validate()
    assert len(issues) == 0


def test_submission_validation_failure_on_missing_fields(sample_attestation):
    invalid = BenchmarkSubmissionItem(
        submission_id="INVALID_ITEM",
        author_attestation=sample_attestation,
        target_visa_category="D-2",
        question="짧음",  # < 10 chars
        user_context={},
        authoritative_answer_key="",  # empty
        legal_citations=[],  # empty
        rubric_spec={},
    )
    issues = invalid.validate()
    assert len(issues) >= 3
    assert any("question" in i.lower() for i in issues)
    assert any("answer key" in i.lower() for i in issues)
    assert any("citation" in i.lower() for i in issues)


def test_blind_partition_projection_strips_ground_truth(sample_submission):
    blind = BlindBenchmarkPartitionManager.project_blind([sample_submission])
    assert len(blind) == 1
    item = blind[0]
    assert item["submission_id"] == "EXT-100-001"
    assert "question" in item
    assert "user_context" in item
    # Critical security assertion: answer key and rubrics MUST NOT be present!
    assert "authoritative_answer_key" not in item
    assert "legal_citations" not in item
    assert "rubric_spec" not in item


def test_frozen_manifest_generation(sample_submission):
    manifest = BlindBenchmarkPartitionManager.create_frozen_manifest(
        benchmark_id="BENCHMARK-EXT-100-V1",
        items=[sample_submission],
    )
    assert manifest["total_items"] == 1
    assert "blind_partition_sha256" in manifest
    assert "key_partition_sha256" in manifest
    assert manifest["isolation_protocol"] == "air_gapped_blind_projection"


def test_contamination_auditor_detects_duplicates():
    corpus = [
        "F-2-R 지역특화형 비자 취득 후 인구감소지역 거주의무 기간은 몇 년인가요? 최소 5년 이상 거주해야 합니다.",
        "일반적인 대한민국 출입국 절차 및 외국인등록 안내문입니다.",
    ]
    auditor = ContaminationAuditor(corpus)

    # Identical or near identical query
    risk, score, desc = auditor.check_item_contamination(
        question="F-2-R 지역특화형 비자 취득 후 인구감소지역 거주의무 기간은 몇 년인가요?",
        answer_key="최소 5년 이상 거주해야 합니다.",
    )
    assert risk in (ContaminationRisk.CONTAMINATED, ContaminationRisk.SUSPECTED)
    assert score > 0.5

    # Completely novel query
    risk_clean, score_clean, desc_clean = auditor.check_item_contamination(
        question="우주항공청 특별 연구원 초청 사증의 신설 규정과 발급 요건은?",
        answer_key="특별법 제12조에 따른 추천서가 요구됩니다.",
    )
    assert risk_clean in (ContaminationRisk.CLEAN, ContaminationRisk.LOW)
    assert score_clean < 0.2


def test_evaluator_access_control_rules():
    # Model runner can ONLY access blind partition
    assert EvaluatorAccessController.authorize_read(EvaluatorRole.MODEL_RUNNER, "blind_partition") is True
    assert EvaluatorAccessController.authorize_read(EvaluatorRole.MODEL_RUNNER, "key_partition") is False

    # Grader can access both inside ephemeral sandbox
    assert EvaluatorAccessController.authorize_read(EvaluatorRole.EVALUATION_GRADER, "blind_partition") is True
    assert EvaluatorAccessController.authorize_read(EvaluatorRole.EVALUATION_GRADER, "key_partition") is True
