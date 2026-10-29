"""Unit and integration tests for Artemis AI Response Evaluation Infrastructure (Mission 004-A).

Covers:
1. Validator and JSON Schema compliance.
2. Dimension 1: Source Fidelity (출처 충실도) — hallucination & leakage checks.
3. Dimension 2: Citation Accuracy (인용 정확성) — precision, recall, forbidden citations.
4. Dimension 3: Procedural Integrity (절차 오류) — visa vs stay scopes, clarification.
5. Dimension 4: Abstention Appropriateness (부적절한 보류) — over-abstention & unwarranted answers.
6. Composite & End-to-End Suite Evaluation on 10 synthetic test cases.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_DIR = EXPERIMENT_ROOT / "artemis_bootstrap"

if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))
if str(BOOTSTRAP_DIR) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_DIR))

from artemis_eval import (
    CASES_10_PATH,
    CORRECT,
    WRONG,
    approval_hash,
    evaluate_suite,
    generate_markdown_report,
    score_abstention_appropriateness,
    score_artemis_response,
    score_citation_accuracy,
    score_procedural_integrity,
    score_source_fidelity,
    validate_dataset,
    validate_eval_item,
)


@pytest.fixture
def cases_10():
    data = json.loads(CASES_10_PATH.read_text(encoding="utf-8"))
    return data["items"] if "items" in data else data


# ---------------------------------------------------------------------------
# 1. Validator & Schema Tests
# ---------------------------------------------------------------------------
def test_validate_10_cases_passes_cleanly(cases_10):
    report = validate_dataset(CASES_10_PATH)
    assert report.valid is True
    assert report.total_items == 10
    assert report.errors == 0
    assert report.warnings == 0
    assert len(report.issues) == 0


def test_validator_catches_missing_required_fields(cases_10):
    bad_item = copy.deepcopy(cases_10[0])
    del bad_item["expected"]
    del bad_item["question"]
    issues = validate_eval_item(bad_item)
    err_fields = {i.field_name for i in issues if i.severity == "error"}
    assert "expected" in err_fields
    assert "question" in err_fields


def test_validator_catches_invalid_dimension(cases_10):
    bad_item = copy.deepcopy(cases_10[0])
    bad_item["dimension"] = "invalid_dimension"
    issues = validate_eval_item(bad_item)
    assert any("Invalid dimension" in i.message for i in issues)


def test_validator_catches_hash_tampering(cases_10):
    tampered_item = copy.deepcopy(cases_10[0])
    # Change text without updating hash
    tampered_item["evidence"][0]["text"] += " (위조된 문구)"
    issues = validate_eval_item(tampered_item, check_hashes=True)
    assert any("Hash mismatch" in i.message for i in issues)


def test_validator_catches_duplicate_evidence_id(cases_10):
    bad_item = copy.deepcopy(cases_10[0])
    dup = copy.deepcopy(bad_item["evidence"][0])
    bad_item["evidence"].append(dup)
    issues = validate_eval_item(bad_item)
    assert any("Duplicate evidence id" in i.message for i in issues)


def test_validator_catches_must_cite_nonexistent_id(cases_10):
    bad_item = copy.deepcopy(cases_10[0])
    bad_item["expected"]["citation_accuracy"]["must_cite"] = ["NON_EXISTENT_DOC_ID"]
    issues = validate_eval_item(bad_item)
    assert any("references non-existent evidence id" in i.message for i in issues)


def test_validator_catches_conflicting_abstention_flags(cases_10):
    bad_item = copy.deepcopy(cases_10[0])
    bad_item["expected"]["abstention_appropriateness"]["should_withhold"] = True
    bad_item["expected"]["abstention_appropriateness"]["forbid_withholding"] = True
    issues = validate_eval_item(bad_item)
    assert any("cannot both be True" in i.message for i in issues)


def test_validator_catches_must_clarify_without_clarify_status(cases_10):
    bad_item = copy.deepcopy(cases_10[6])  # SYN-007
    bad_item["expected"]["allowed_statuses"] = ["answered"]
    bad_item["expected"]["procedural_integrity"]["must_clarify"] = True
    issues = validate_eval_item(bad_item)
    assert any("must_clarify is True but 'clarify' not in allowed_statuses" in i.message for i in issues)


def test_validator_catches_duplicate_item_ids_across_dataset(cases_10):
    bad_dataset = {
        "version": "artemis-eval/1.0",
        "description": "test",
        "items": [cases_10[0], copy.deepcopy(cases_10[0])],
    }
    report = validate_dataset(bad_dataset)
    assert report.valid is False
    assert any("Duplicate item id across dataset" in i.message for i in report.issues)


# ---------------------------------------------------------------------------
# 2. Dimension 1: Source Fidelity (출처 충실도) Tests
# ---------------------------------------------------------------------------
def test_fidelity_passes_on_grounded_answer(cases_10):
    case = cases_10[0]  # SYN-001 (수수료 30,000원, 14일)
    gold_resp = {
        "status": "answered",
        "answer": "Z-9 체류자격 외국인등록 수수료는 30,000원이며, 처리 기간은 접수일로부터 14일입니다.",
        "citations": ["SYN-DOC-001"],
    }
    score = score_source_fidelity(case, gold_resp)
    assert score.passed is True
    assert score.outcome == CORRECT
    assert len(score.failures) == 0


def test_fidelity_catches_invented_fee(cases_10):
    case = cases_10[0]  # SYN-001 expects 30,000원
    fake_resp = {
        "status": "answered",
        "answer": "Z-9 외국인등록 수수료는 50,000원이며 처리 기간은 14일입니다.",
        "citations": ["SYN-DOC-001"],
    }
    score = score_source_fidelity(case, fake_resp)
    assert score.passed is False
    assert score.outcome == WRONG
    assert any("invented_amount" in f for f in score.failures)


def test_fidelity_catches_unapproved_blog_leakage(cases_10):
    case = cases_10[1]  # SYN-002: official is 20,000원, blog claims 5,000원 할인
    leaked_resp = {
        "status": "answered",
        "answer": "인터넷 특례 신청 시 5,000원으로 할인받아 신청할 수 있습니다.",
        "citations": ["SYN-DOC-002"],
    }
    score = score_source_fidelity(case, leaked_resp)
    assert score.passed is False
    assert score.outcome == WRONG
    assert any("forbidden_claim_relayed" in f for f in score.failures)


def test_fidelity_catches_missing_required_facts(cases_10):
    case = cases_10[0]  # requires "30,000원" and "14일"
    missing_facts_resp = {
        "status": "answered",
        "answer": "가상체류관리센터를 방문하여 신청서를 제출하시면 됩니다.",
        "citations": ["SYN-DOC-001"],
    }
    score = score_source_fidelity(case, missing_facts_resp)
    assert score.passed is False
    assert any("required_fact_missing:30,000원" in f for f in score.failures)


# ---------------------------------------------------------------------------
# 3. Dimension 2: Citation Accuracy (인용 정확성) Tests
# ---------------------------------------------------------------------------
def test_citation_accuracy_passes_exact_citations(cases_10):
    case = cases_10[3]  # SYN-004 requires ["SYN-DOC-004A", "SYN-DOC-004B"]
    good_resp = {
        "status": "answered",
        "answer": "가상체류관리센터 3층 체류지원과에서 가상고용확인서를 제출하여 신청합니다.",
        "citations": ["SYN-DOC-004A", "SYN-DOC-004B"],
    }
    score = score_citation_accuracy(case, good_resp)
    assert score.passed is True
    assert score.outcome == CORRECT
    assert score.details["precision"] == 1.0
    assert score.details["recall"] == 1.0


def test_citation_accuracy_catches_missing_required_citation(cases_10):
    case = cases_10[3]  # requires both 4A and 4B
    missing_cite_resp = {
        "status": "answered",
        "answer": "가상체류관리센터 3층 체류지원과에서 가상고용확인서를 제출하여 신청합니다.",
        "citations": ["SYN-DOC-004A"],  # missed 4B
    }
    score = score_citation_accuracy(case, missing_cite_resp)
    assert score.passed is False
    assert any("missing_citations:SYN-DOC-004B" in f for f in score.failures)
    assert score.details["recall"] < 1.0


def test_citation_accuracy_catches_unknown_citation_id(cases_10):
    case = cases_10[4]  # SYN-005
    fake_cite_resp = {
        "status": "answered",
        "answer": "15일 이내에 신고해야 합니다.",
        "citations": ["SYN-DOC-005", "SYN-DOC-FAKE-999"],
    }
    score = score_citation_accuracy(case, fake_cite_resp)
    assert score.passed is False
    assert any("unknown_citation_ids:SYN-DOC-FAKE-999" in f for f in score.failures)


def test_citation_accuracy_catches_unapproved_citation(cases_10):
    case = cases_10[1]  # SYN-002: SYN-BLOG-002 is community/unapproved
    unapproved_cite_resp = {
        "status": "answered",
        "answer": "20,000원입니다.",
        "citations": ["SYN-DOC-002", "SYN-BLOG-002"],
    }
    score = score_citation_accuracy(case, unapproved_cite_resp)
    assert score.passed is False
    assert any("forbidden_citations" in f or "unapproved_citations" in f for f in score.failures)


# ---------------------------------------------------------------------------
# 4. Dimension 3: Procedural Integrity (절차 오류) Tests
# ---------------------------------------------------------------------------
def test_procedural_integrity_passes_on_correct_scope(cases_10):
    case = cases_10[5]  # SYN-006: overseas researcher applying for X-1 visa
    good_visa_resp = {
        "status": "answered",
        "answer": "재외공관에 사증발급신청서, 여권, 고용계약서 원본 및 학위증 사본을 제출해야 합니다.",
        "citations": ["SYN-VISA-006"],
    }
    score = score_procedural_integrity(case, good_visa_resp)
    assert score.passed is True
    assert score.outcome == CORRECT


def test_procedural_integrity_catches_stay_procedure_mixed_in_visa_scope(cases_10):
    case = cases_10[5]  # SYN-006 (abroad applicant)
    bad_mix_resp = {
        "status": "answered",
        "answer": "관할 출입국센터에 통합신청서와 외국인등록증 원본을 제출하여 체류자격 변경을 신청하세요.",
        "citations": ["SYN-STAY-006"],
    }
    score = score_procedural_integrity(case, bad_mix_resp)
    assert score.passed is False
    assert score.outcome == WRONG
    assert any("procedural_scope_mixed:stay_in_visa_scope" in f or "scope_mix_in_citations" in f
               for f in score.failures)


def test_procedural_integrity_enforces_mandatory_clarification(cases_10):
    case = cases_10[6]  # SYN-007 (ambiguous procedure question)
    # 1. Correct clarify response
    clarify_resp = {
        "status": "clarify",
        "answer": "해외에서 사증을 새로 발급받으려는 것인가요, 아니면 국내에서 체류자격 변경을 신청하려는 것인가요?",
        "citations": [],
    }
    score_pass = score_procedural_integrity(case, clarify_resp)
    assert score_pass.passed is True

    # 2. Incorrect direct answer without clarification
    guessed_resp = {
        "status": "answered",
        "answer": "거주국 대한민국 재외공관에 신청하시면 됩니다.",
        "citations": ["SYN-VISA-007"],
    }
    score_fail = score_procedural_integrity(case, guessed_resp)
    assert score_fail.passed is False
    assert any("clarification_missed" in f for f in score_fail.failures)


# ---------------------------------------------------------------------------
# 5. Dimension 4: Abstention Appropriateness (부적절한 보류) Tests
# ---------------------------------------------------------------------------
def test_abstention_catches_inappropriate_withholding(cases_10):
    case = cases_10[7]  # SYN-008: evidence clearly has "4개월 전"
    # Erroneous withholding
    over_abstain_resp = {
        "status": "insufficient_evidence",
        "answer": "공식 근거에 접수 시기 정보가 없어 답변을 보류합니다.",
        "citations": [],
    }
    score = score_abstention_appropriateness(case, over_abstain_resp)
    assert score.passed is False
    assert score.outcome == WRONG
    assert any("inappropriate_withholding" in f for f in score.failures)


def test_abstention_accepts_proper_answer_when_evidence_is_sufficient(cases_10):
    case = cases_10[7]  # SYN-008
    good_resp = {
        "status": "answered",
        "answer": "체류기간 만료일 4개월 전부터 연장허가를 신청할 수 있습니다.",
        "citations": ["SYN-DOC-008"],
    }
    score = score_abstention_appropriateness(case, good_resp)
    assert score.passed is True
    assert score.outcome == CORRECT


def test_abstention_approves_appropriate_withholding_on_absent_facts(cases_10):
    case = cases_10[8]  # SYN-009: asks about express fee which doesn't exist
    withheld_resp = {
        "status": "insufficient_evidence",
        "answer": "당일 특례나 급행 심사 제도는 운영되지 않으며 관련 수수료 정보가 없어 답변을 보류합니다.",
        "citations": ["SYN-DOC-009"],
    }
    score = score_abstention_appropriateness(case, withheld_resp)
    assert score.passed is True
    assert score.outcome == CORRECT


def test_abstention_catches_unwarranted_answer_on_absent_facts(cases_10):
    case = cases_10[8]  # SYN-009: should withhold
    hallucinated_resp = {
        "status": "answered",
        "answer": "당일 급행 수수료는 100,000원입니다.",
        "citations": ["SYN-DOC-009"],
    }
    score = score_abstention_appropriateness(case, hallucinated_resp)
    assert score.passed is False
    assert any("unwarranted_answer" in f for f in score.failures)


# ---------------------------------------------------------------------------
# 6. Composite & End-to-End Suite Evaluation Tests
# ---------------------------------------------------------------------------
def test_composite_conflict_resolution(cases_10):
    case = cases_10[9]  # SYN-010: conflicting notices 18:00 vs 17:00
    # Correct conflict reporting
    conflict_resp = {
        "status": "conflict",
        "answer": "정기 공고(제2026-01호)에는 18:00로 되어 있으나 시설 점검 안내(제2026-15호)에는 17:00로 마감 시간이 상이합니다.",
        "citations": ["SYN-NOTICE-010A", "SYN-NOTICE-010B"],
    }
    item_score = score_artemis_response(case, conflict_resp)
    assert item_score.overall_passed is True

    # Bad response: picked only one time and marked as answered
    bad_resp = {
        "status": "answered",
        "answer": "금요일 접수 마감 시간은 18:00입니다.",
        "citations": ["SYN-NOTICE-010A"],
    }
    bad_score = score_artemis_response(case, bad_resp)
    assert bad_score.overall_passed is False
    assert any("disallowed_status:answered" in f for f in bad_score.all_failures)
    assert any("missing_citations:SYN-NOTICE-010B" in f for f in bad_score.all_failures)


def test_full_suite_evaluation_with_gold_predictions(cases_10):
    gold_predictions = {
        "ARTEMIS-004-SYN-001": {
            "status": "answered",
            "answer": "Z-9 체류자격 외국인등록 수수료는 30,000원이며 처리 기간은 14일입니다.",
            "citations": ["SYN-DOC-001"],
        },
        "ARTEMIS-004-SYN-002": {
            "status": "answered",
            "answer": "Z-9 체류자격의 시간제 취업 허가 신청 수수료는 20,000원입니다.",
            "citations": ["SYN-DOC-002"],
        },
        "ARTEMIS-004-SYN-003": {
            "status": "answered",
            "answer": "Z-9 부여 신청 시 신청서 1부, 여권 사본, 컬러 사진 1매를 제출해야 합니다.",
            "citations": ["SYN-DOC-003"],
        },
        "ARTEMIS-004-SYN-004": {
            "status": "answered",
            "answer": "가상체류관리센터 3층 체류지원과에서 가상고용확인서 원본을 제출하여 신청합니다.",
            "citations": ["SYN-DOC-004A", "SYN-DOC-004B"],
        },
        "ARTEMIS-004-SYN-005": {
            "status": "answered",
            "answer": "전입한 날부터 15일 이내에 관할 센터에 전입 신고를 마쳐야 합니다.",
            "citations": ["SYN-DOC-005"],
        },
        "ARTEMIS-004-SYN-006": {
            "status": "answered",
            "answer": "재외공관에 사증발급신청서, 여권, 고용계약서 원본, 학위증 사본을 제출하여 X-1 사증을 발급받아야 합니다.",
            "citations": ["SYN-VISA-006"],
        },
        "ARTEMIS-004-SYN-007": {
            "status": "clarify",
            "answer": "해외에서 사증을 새로 발급받으시려는 것인지, 국내에서 체류자격 변경을 신청하시려는 것인지 확인이 필요합니다.",
            "citations": [],
        },
        "ARTEMIS-004-SYN-008": {
            "status": "answered",
            "answer": "Z-9 체류자격 연장 신청은 체류기간 만료일 4개월 전부터 가능합니다.",
            "citations": ["SYN-DOC-008"],
        },
        "ARTEMIS-004-SYN-009": {
            "status": "insufficient_evidence",
            "answer": "당일 특례나 급행 심사 제도는 운영하지 않으므로 수수료 정보가 없어 답변을 보류합니다.",
            "citations": ["SYN-DOC-009"],
        },
        "ARTEMIS-004-SYN-010": {
            "status": "conflict",
            "answer": "정기 공고(제2026-01호)에는 18:00, 시설 점검 안내(제2026-15호)에는 17:00로 마감 시간이 상이합니다.",
            "citations": ["SYN-NOTICE-010A", "SYN-NOTICE-010B"],
        },
    }

    summary = evaluate_suite(cases_10, gold_predictions)
    assert summary.total_cases == 10
    assert summary.passed_cases == 10
    assert summary.failed_cases == 0
    assert summary.pass_rate == 1.0
    for dname, rate in summary.dimension_pass_rates.items():
        assert rate == 1.0

    md_report = generate_markdown_report(summary)
    assert "**총 평가 문항**: 10건" in md_report
    assert "**전체 통과**: 10건 (100.0%)" in md_report
    assert "출처 충실도 (Source Fidelity)" in md_report
    assert "부적절한 보류 방지 (Abstention Appropriateness)" in md_report
