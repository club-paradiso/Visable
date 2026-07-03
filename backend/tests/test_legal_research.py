"""Tests for the deterministic legal-research-depth layer.

Covers services/legal_research.py (depth selection, issue/term derivation,
source-strength labels, pro grouping, safety framing) and the
POST /api/legal/research endpoint, including the §7 sophisticated questions.

All retrieval is mocked, so these run fully offline with no real LAW_API_OC.
Run: python3 backend/tests/test_legal_research.py
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402
import services.law_tools as law_tools  # noqa: E402
from services import legal_research as LR  # noqa: E402
import paradiso_backend as P  # noqa: E402

SOPHISTICATED = [
    "D-2 유학생이 졸업 후 체류기간이 얼마 남지 않았고 출석률 문제가 있는 경우 D-10 변경에서 어떤 쟁점이 생길 수 있어?",
    "F-6 체류자격 변경에서 소득요건과 혼인의 진정성이 함께 문제되는 경우 어떤 자료와 법령을 확인해야 해?",
    "G-1 난민신청자의 체류기간 연장 불허에서 행정소송으로 다툴 수 있는 쟁점은 뭐야?",
    "강제퇴거명령과 출국명령을 비교하고, 각각 다툴 때 확인해야 할 법령과 판례 검색어를 정리해줘.",
    "F-4 재외동포가 단순노무 또는 사행행위 관련 업종에 취업하려는 경우 쟁점과 확인자료를 정리해줘.",
    "E-7 특정활동에서 직종 적합성, 고용 필요성, 학력·경력 요건이 동시에 문제되는 경우 어떻게 쟁점을 나눠야 해?",
    "귀화 불허 처분에서 품행단정 요건이 문제되는 경우 관련 법령과 판례 검색 방향을 정리해줘.",
]

LAW_JSON = json.dumps({"LawSearch": {"law": [{"법령명한글": "출입국관리법", "법령일련번호": "001234", "법령구분명": "법률", "조문내용": "체류"}]}})
PREC_JSON = json.dumps({"PrecSearch": {"prec": [{"사건명": "취소", "사건번호": "2020두1", "법원명": "대법원", "선고일자": "20210115", "판시사항": "재량", "판례상세링크": "https://www.law.go.kr/precInfoP.do?precSeq=9"}]}})


def _transport(*, ok=True, status=200, err=""):
    def send(url, timeout):
        payload = PREC_JSON if "target=prec" in url else LAW_JSON
        if not ok:
            payload = ""
        return law_tools.LawHttpResponse(ok=ok, status_code=status, text=payload, error_type=err)
    return send


class DepthSelectionTests(unittest.TestCase):
    def test_normalize_depth_defaults_to_basic(self):
        self.assertEqual(LR.normalize_depth("nonsense"), "basic")
        self.assertEqual(LR.normalize_depth(None), "basic")
        for d in ("fast", "basic", "pro"):
            self.assertEqual(LR.normalize_depth(d), d)

    def test_auto_select_short_is_fast(self):
        self.assertEqual(LR.auto_select_depth("F-4 뜻이 뭐야?"), "fast")

    def test_auto_select_keyword_is_pro(self):
        for kw_q in ["강제퇴거 다툴 수 있어?", "귀화 불허 어떻게?", "precedent on F-6", "deportation appeal"]:
            self.assertEqual(LR.auto_select_depth(kw_q), "pro", kw_q)

    def test_default_depth_is_basic_for_plain_question(self):
        plan = LR.build_research_plan("D-2에서 D-10으로 바꾸려면 어떤 서류가 필요한가요")
        self.assertIn(plan["depth"], ("basic", "fast", "pro"))
        self.assertEqual(LR.DEFAULT_DEPTH, "basic")

    def test_sophisticated_questions_escalate_to_pro(self):
        # All but the simplest (D-2/D-10, no dispute) should auto-pick pro.
        pro_count = sum(1 for q in SOPHISTICATED if LR.build_research_plan(q)["depth"] == "pro")
        self.assertGreaterEqual(pro_count, 6, "most sophisticated questions should auto-select pro")

    def test_explicit_depth_overrides_auto(self):
        plan = LR.build_research_plan("F-4 뜻이 뭐야?", depth="pro")
        self.assertEqual(plan["depth"], "pro")
        self.assertFalse(plan["depthAutoSelected"])


class ResearchResultTests(unittest.TestCase):
    def test_pro_result_has_all_required_sections(self):
        for q in SOPHISTICATED:
            plan = LR.build_research_plan(q, depth="pro")
            res = LR.build_research_result(plan, law_results=[], precedent_results=[])
            self.assertTrue(res["ok"], q)
            self.assertEqual(len(res["headings"]), 12, q)  # 11 numbered + 주의
            self.assertTrue(res["issues"], f"issues present: {q}")
            self.assertTrue(res["riskFlags"], f"risk flags present: {q}")
            self.assertTrue(res["missingFacts"], f"missing facts present: {q}")
            self.assertTrue(res["nextChecks"], f"next checks present: {q}")
            self.assertTrue(res["limitations"], f"limitations present: {q}")
            self.assertTrue(res["disclaimer"], f"disclaimer present: {q}")
            self.assertTrue(res["lawSearchTerms"], f"law search terms present: {q}")

    def test_fast_omits_risk_and_missing_facts(self):
        plan = LR.build_research_plan("F-4 뜻이 뭐야?", depth="fast")
        res = LR.build_research_result(plan, law_results=[], precedent_results=[])
        self.assertEqual(res["riskFlags"], [])
        self.assertEqual(res["missingFacts"], [])
        self.assertEqual(len(res["headings"]), 4)

    def test_source_strength_labels_applied(self):
        plan = LR.build_research_plan("강제퇴거 다툴 쟁점", depth="basic", locale="ko")
        laws = [{"title": "출입국관리법", "snippet": "강제퇴거", "sourceUrl": "https://www.law.go.kr/법령/x"}]
        res = LR.build_research_result(plan, law_results=laws, precedent_results=[])
        self.assertIn(res["laws"][0]["strength"], LR.SOURCE_STRENGTHS)
        self.assertEqual(res["laws"][0]["strengthLabel"], "직접 근거")

    def test_pro_groups_sources_by_type(self):
        plan = LR.build_research_plan("강제퇴거명령과 출국명령 비교 판례", depth="pro", locale="ko")
        laws = [
            {"title": "출입국관리법", "type": "법률", "snippet": "x", "sourceUrl": "https://www.law.go.kr/법령/a"},
            {"title": "출입국관리법 시행령", "type": "시행령", "snippet": "y", "sourceUrl": "https://www.law.go.kr/법령/b"},
        ]
        precs = [{"title": "취소", "caseNumber": "2020두1", "summary": "z", "sourceUrl": "https://www.law.go.kr/precInfoP.do?precSeq=1"}]
        res = LR.build_research_result(plan, law_results=laws, precedent_results=precs)
        groups = {g["group"] for g in (res["sourceGroups"] or [])}
        self.assertIn("law", groups)
        self.assertIn("subordinate", groups)
        self.assertIn("precedent", groups)
        self.assertIn("loadingSteps", res)


class LanguageAwareTests(unittest.TestCase):
    """§1 language-aware delivery: EN→KO query generation + honest source labels."""

    def test_english_question_generates_korean_queries(self):
        qs = LR.english_korean_queries("What about a deportation order and a departure order?")
        self.assertIn("강제퇴거명령", qs)
        self.assertIn("출국명령", qs)

    def test_korean_question_needs_no_english_bridge(self):
        self.assertEqual(LR.english_korean_queries("강제퇴거명령 다툴 쟁점"), [])

    def test_english_plan_has_korean_law_terms(self):
        plan = LR.build_research_plan(
            "Can I change my marriage-migrant status if my income requirement is borderline?",
            depth="basic", locale="en")
        self.assertEqual(plan["localeRaw"], "en")
        self.assertTrue(plan["lawTerms"], "english question still yields korean law terms")
        self.assertTrue(any(any(ord(ch) > 0x3130 for ch in term) for term in plan["lawTerms"]),
                        "law terms are Korean statutory anchors")

    def test_source_notice_by_locale(self):
        self.assertEqual(LR._source_notice("ko"), "")
        self.assertEqual(LR._source_notice("en"), "Official source text may be in Korean")
        self.assertTrue(LR._source_notice("zh-CN"))

    def test_localize_sources_tags_metadata(self):
        cards = [{"title": "출입국관리법", "snippet": "x"}]
        LR.localize_sources(cards, "en")
        self.assertEqual(cards[0]["language"], "ko")
        self.assertEqual(cards[0]["originalLanguage"], "ko")
        self.assertFalse(cards[0]["isMachineTranslated"])
        self.assertEqual(cards[0]["translationNotice"], "Official source text may be in Korean")
        # KO UI: no translation notice (Korean source shown as-is).
        ko_cards = [{"title": "출입국관리법", "snippet": "x"}]
        LR.localize_sources(ko_cards, "ko")
        self.assertNotIn("translationNotice", ko_cards[0])

    def test_result_carries_facts_and_source_language_notice(self):
        plan = LR.build_research_plan("F-6 변경허가 소득요건", depth="basic", locale="en")
        res = LR.build_research_result(plan, law_results=[], precedent_results=[])
        self.assertIn("extractedFacts", res)
        self.assertEqual(res["sourceLanguageNotice"], "Official source text may be in Korean")


class FactExtractionTests(unittest.TestCase):
    """§3 extract_facts: surfaces only what the text states (never invents)."""

    def test_extracts_visa_and_procedure(self):
        facts = LR.extract_facts("F-6 결혼이민 체류자격 변경에서 소득요건과 혼인의 진정성", visa_hint=None)
        self.assertIn("F-6", facts["visaStatuses"])
        self.assertIn("체류자격 변경허가", facts["procedureTypes"])
        self.assertTrue(facts["legalIssues"])
        self.assertIn("law", facts["likelySourceNeeds"])

    def test_no_visa_no_hallucination(self):
        facts = LR.extract_facts("이 제도는 어떻게 운영되나요?")
        self.assertEqual(facts["visaStatuses"], [])

    def test_deportation_procedure_detected(self):
        facts = LR.extract_facts("강제퇴거명령과 출국명령의 차이")
        self.assertIn("강제퇴거", facts["procedureTypes"])
        self.assertIn("출국명령", facts["procedureTypes"])

    def test_workplace_change_is_not_misclassified_as_e7_occupation(self):
        question = "E-7 체류자격으로 근무처를 변경할 때 사전허가가 필요한가요? 관련 법령과 판례도 알려주세요."
        plan = LR.build_research_plan(question)
        self.assertIn("workplace_change", plan["matchedConcepts"])
        self.assertNotIn("e7_occupation", plan["matchedConcepts"])
        self.assertEqual(plan["lawTerms"][:3], ["출입국관리법", "출입국관리법 시행령", "출입국관리법 시행규칙"])
        self.assertTrue(any("사전허가" in issue for issue in plan["issuesKo"]))
        self.assertIn("근무처 변경·추가", plan["extractedFacts"]["procedureTypes"])

    def test_workplace_change_english_bridge_uses_korean_search_anchors(self):
        plan = LR.build_research_plan("Can an E-7 holder change employer before starting the new job?", locale="en")
        self.assertIn("workplace_change", plan["matchedConcepts"])
        self.assertIn("출입국관리법", plan["lawTerms"])
        self.assertTrue(any("prior permission" in issue for issue in plan["issuesEn"]))


class ResearchEndpointTests(unittest.TestCase):
    def setUp(self):
        self._oc = os.environ.get("LAW_API_OC")
        self._key = os.environ.get("LAW_API_KEY")
        self._t = law_tools._default_transport
        os.environ["LAW_API_OC"] = "test-oc"
        os.environ.pop("LAW_API_KEY", None)
        self.client = TestClient(P.app)

    def tearDown(self):
        law_tools._default_transport = self._t
        for name, val in (("LAW_API_OC", self._oc), ("LAW_API_KEY", self._key)):
            if val is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = val

    def test_empty_question_rejected(self):
        r = self.client.post("/api/legal/research", json={"question": "   "})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "empty_question")

    def test_missing_oc_still_returns_scaffold(self):
        os.environ.pop("LAW_API_OC", None)
        os.environ.pop("LAW_API_KEY", None)
        r = self.client.post("/api/legal/research", json={"question": SOPHISTICATED[3], "depth": "pro"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertFalse(body["retrievalAvailable"])
        self.assertTrue(body["issues"])
        self.assertTrue(body["limitations"])

    def test_pro_research_with_retrieval(self):
        law_tools._default_transport = _transport()
        r = self.client.post("/api/legal/research", json={"question": SOPHISTICATED[3], "depth": "pro", "mode": "memo", "visaStatusHint": "강제퇴거"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["depth"], "pro")
        self.assertEqual(body["mode"], "memo")
        self.assertTrue(body["retrievalAvailable"])
        self.assertTrue(body["laws"])
        self.assertTrue(body["precedents"], "pro runs precedents by default")
        self.assertTrue(body["sourceGroups"])

    def test_workplace_change_research_retrieves_law_and_candidate_precedent(self):
        law_tools._default_transport = _transport()
        r = self.client.post("/api/legal/research", json={
            "question": "E-7 근무처 변경의 사전허가 여부와 관련 판례를 확인해줘",
            "depth": "pro",
        })
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("근무처 변경·추가", body["extractedFacts"]["procedureTypes"])
        self.assertTrue(any("사전허가" in issue for issue in body["issues"]))
        self.assertTrue(body["laws"])
        self.assertTrue(body["precedents"])

    def test_fast_does_not_run_precedents_by_default(self):
        law_tools._default_transport = _transport()
        r = self.client.post("/api/legal/research", json={"question": "체류기간 연장 서류", "depth": "fast"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["precedents"], [])

    def test_oc_never_leaks_in_research_response(self):
        law_tools._default_transport = _transport()
        r = self.client.post("/api/legal/research", json={"question": SOPHISTICATED[2], "depth": "pro"})
        self.assertNotIn("test-oc", r.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
