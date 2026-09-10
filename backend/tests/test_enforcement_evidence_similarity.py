from __future__ import annotations

import sys
import time
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.enforcement_evidence import retrieve_enforcement_evidence  # noqa: E402
from services.enforcement_models import StructuredCase  # noqa: E402
from services.enforcement_rules import calculate_legal_baseline  # noqa: E402


def sample_case(**updates) -> StructuredCase:
    values = dict(
        status_of_stay="D-2",
        violation_code="STATUS_OUTSIDE_ACTIVITY_ART20",
        authorization_obtained=False,
        duration_days=18,
        assessment_date=date(2026, 8, 19),
        prior_violations=0,
        voluntary_disclosure=True,
    )
    values.update(updates)
    return StructuredCase(**values)


def body(source_id: str, *, title: str, holding: str) -> dict:
    return {
        "resultKind": "body_result",
        "citationGrade": "direct",
        "serialNumber": source_id,
        "title": title,
        "holdingSummary": holding,
        "courtOrAgency": "대법원",
        "decisionDate": "2026-05-01",
        "sourceUrl": f"https://www.law.go.kr/precInfoP.do?precSeq={source_id}",
    }


class RankedPrecedents:
    def __init__(self):
        self.search_limit = None
        self.detail_calls: list[str] = []

    def search_precedents(self, query, limit=3):
        self.search_limit = limit
        return {
            "status": "results_found",
            "items": [
                {"serialNumber": "weak"},
                {"serialNumber": "strong"},
                {"serialNumber": "medium"},
            ],
        }

    def get_precedent_detail(self, source_id):
        self.detail_calls.append(source_id)
        if source_id == "strong":
            return {"items": [body(
                source_id,
                title="D-2 체류자격외활동허가 사건",
                holding="18일 동안의 위반이고 초범이며 자진신고한 사정을 함께 고려하였다.",
            )]}
        if source_id == "medium":
            return {"items": [body(
                source_id,
                title="체류자격외활동허가 사건",
                holding="200일 동안 근무한 사안에 관하여 판단하였다.",
            )]}
        return {"items": [body(
            source_id,
            title="별도 행정사건",
            holding="E-7 체류자격으로 200일 근무한 사안이다.",
        )]}


class PartialFailurePrecedents(RankedPrecedents):
    def get_precedent_detail(self, source_id):
        if source_id == "medium":
            raise RuntimeError("test-only detail failure")
        return super().get_precedent_detail(source_id)


class SlowParallelPrecedents(RankedPrecedents):
    def get_precedent_detail(self, source_id):
        time.sleep(0.08)
        return super().get_precedent_detail(source_id)


class EnforcementEvidenceSimilarityTests(unittest.TestCase):
    def test_multiple_bodies_are_ranked_by_structured_similarity(self):
        case = sample_case()
        adapter = RankedPrecedents()
        pack = retrieve_enforcement_evidence(
            case,
            calculate_legal_baseline(case),
            precedent_adapter=adapter,
            max_cases=2,
        )

        self.assertEqual(adapter.search_limit, 3)
        self.assertEqual(len(pack.similar_cases), 2)
        self.assertEqual(pack.similar_cases[0].id, "similar:strong")
        self.assertGreater(pack.similar_cases[0].similarity_score, pack.similar_cases[1].similarity_score)
        self.assertEqual(pack.similar_cases[0].similarity_score, 1.0)
        self.assertIn("동일·유사 법적 쟁점", pack.similar_cases[0].matching_factors)
        self.assertIn("동일 체류자격(D-2)", pack.similar_cases[0].matching_factors)
        self.assertIn("유사 위반기간 구간(30일 이하)", pack.similar_cases[0].matching_factors)
        self.assertIn("초범·위반전력 없음", pack.similar_cases[0].matching_factors)
        self.assertIn("자진신고·자진출석 요소", pack.similar_cases[0].matching_factors)
        self.assertTrue(all(0.0 <= item.similarity_score <= 1.0 for item in pack.similar_cases))
        self.assertIn("처분 확률이 아닙니다", " ".join(pack.limitations))

    def test_explicit_comparable_differences_are_not_called_matches(self):
        case = sample_case()
        adapter = RankedPrecedents()
        pack = retrieve_enforcement_evidence(
            case,
            calculate_legal_baseline(case),
            precedent_adapter=adapter,
            max_cases=3,
        )
        weak = next(item for item in pack.similar_cases if item.id == "similar:weak")
        joined = " ".join(weak.differing_factors)
        self.assertIn("체류자격", joined)
        self.assertIn("위반기간 구간", joined)
        self.assertNotIn("동일 체류자격(D-2)", weak.matching_factors)

    def test_partial_detail_failure_does_not_discard_other_verified_bodies(self):
        case = sample_case()
        pack = retrieve_enforcement_evidence(
            case,
            calculate_legal_baseline(case),
            precedent_adapter=PartialFailurePrecedents(),
            max_cases=3,
        )
        self.assertEqual({item.id for item in pack.similar_cases}, {"similar:strong", "similar:weak"})
        self.assertIn("일부 공식 유사사례 본문 조회를 완료하지 못했습니다.", pack.limitations)

    def test_detail_fetches_are_parallel_with_bounded_candidate_count(self):
        case = sample_case()
        adapter = SlowParallelPrecedents()
        started = time.perf_counter()
        pack = retrieve_enforcement_evidence(
            case,
            calculate_legal_baseline(case),
            precedent_adapter=adapter,
            max_cases=3,
        )
        elapsed = time.perf_counter() - started
        self.assertEqual(len(pack.similar_cases), 3)
        self.assertLess(elapsed, 0.20)

    def test_no_deterministic_baseline_skips_precedent_network_calls(self):
        class MustNotCall:
            def search_precedents(self, query, limit=3):
                raise AssertionError("precedent search must not run without an available baseline")

        case = sample_case(duration_days=None)
        baseline = calculate_legal_baseline(case)
        self.assertEqual(baseline.status, "MISSING_FACTS")
        pack = retrieve_enforcement_evidence(case, baseline, precedent_adapter=MustNotCall(), max_cases=3)
        self.assertFalse(pack.similar_cases)


if __name__ == "__main__":
    unittest.main()
