"""Statute-citation verification tests (Phase 7 citation matrix).

Covers: real article, non-existent article, wrong law name, existing article with a
wrong 조문 제목, 제N조의M, 원숫자 항 (①), repealed statute, and citations that fall
outside the retrieved evidence pack.

    python3 -m pytest backend/tests/test_statute_citation_guard.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import statute_citation_guard as scg  # noqa: E402


def _law(name, articles=None, lifecycle="verified"):
    return {
        "law_name": name,
        "lifecycle_status": lifecycle,
        "articles": articles or [],
    }


def _article(number, title="", text="", branch=""):
    return {
        "article_number": number,
        "article_branch": branch,
        "article_title": title,
        "article_text": text,
    }


PACK = [
    _law("출입국관리법", [
        _article("19", "외국인을 고용한 자 등의 신고"),
        _article("19", "외국인등록사항의 변경신고", branch="4"),
        _article("20", "체류자격 외 활동"),
    ]),
    _law("국적법", [_article("5", "일반귀화 요건")]),
]


class ExtractionTests(unittest.TestCase):
    def test_plain_article_is_extracted(self):
        found = scg.extract_statute_citations("출입국관리법 제20조에 따라")
        self.assertEqual(found[0]["law_name"], "출입국관리법")
        self.assertEqual(found[0]["article"], "제20조")

    def test_branch_article_is_extracted(self):
        found = scg.extract_statute_citations("출입국관리법 제19조의4")
        self.assertEqual(found[0]["article"], "제19조의4")

    def test_clause_and_subclause_are_extracted(self):
        found = scg.extract_statute_citations("출입국관리법 제20조 제2항 제1호")
        self.assertEqual(found[0]["clause"], "제2항 제1호")

    def test_circled_clause_is_normalized(self):
        found = scg.extract_statute_citations("출입국관리법 제20조 ③")
        self.assertEqual(found[0]["clause"], "제3항")

    def test_article_title_is_extracted(self):
        found = scg.extract_statute_citations("출입국관리법 제20조(체류자격 외 활동)")
        self.assertEqual(found[0]["article_title"], "체류자격 외 활동")

    def test_bracketed_multiword_official_title(self):
        found = scg.extract_statute_citations(
            "「재외동포의 출입국과 법적 지위에 관한 법률」 제10조")
        self.assertEqual(found[0]["law_name"], "재외동포의 출입국과 법적 지위에 관한 법률")

    def test_text_without_citations_yields_none(self):
        self.assertEqual(scg.extract_statute_citations("체류자격 변경은 사전에 신청하세요"), [])


class VerificationTests(unittest.TestCase):
    def test_real_article_verifies(self):
        result = scg.verify_statute_citations("출입국관리법 제20조를 확인하세요", PACK)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["citations"][0]["verification_status"], scg.STATUS_VERIFIED)

    def test_branch_article_verifies(self):
        result = scg.verify_statute_citations("출입국관리법 제19조의4", PACK)
        self.assertEqual(result["citations"][0]["verification_status"], scg.STATUS_VERIFIED)

    def test_nonexistent_article_fails(self):
        result = scg.verify_statute_citations("출입국관리법 제999조", PACK)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["citations"][0]["verification_status"],
                         scg.STATUS_ARTICLE_NOT_IN_EVIDENCE)

    def test_law_outside_the_evidence_pack_fails(self):
        result = scg.verify_statute_citations("도로교통법 제10조", PACK)
        self.assertEqual(result["citations"][0]["verification_status"],
                         scg.STATUS_LAW_NOT_IN_EVIDENCE)

    def test_invented_law_name_fails(self):
        result = scg.verify_statute_citations("외국인체류편의증진법 제3조", PACK)
        self.assertEqual(result["status"], "failed")

    def test_existing_article_with_wrong_title_fails(self):
        result = scg.verify_statute_citations("출입국관리법 제20조(강제퇴거)", PACK)
        self.assertEqual(result["citations"][0]["verification_status"],
                         scg.STATUS_TITLE_MISMATCH)
        self.assertEqual(result["citations"][0]["official_article_title"], "체류자격 외 활동")

    def test_existing_article_with_correct_title_passes(self):
        result = scg.verify_statute_citations("출입국관리법 제20조(체류자격 외 활동)", PACK)
        self.assertEqual(result["citations"][0]["verification_status"], scg.STATUS_VERIFIED)

    def test_repealed_statute_citation_is_flagged(self):
        pack = [_law("가상폐지법", [_article("3", "목적")], lifecycle="repealed")]
        result = scg.verify_statute_citations("가상폐지법 제3조", pack)
        self.assertEqual(result["citations"][0]["verification_status"],
                         scg.STATUS_REPEALED_LAW_CITED)

    def test_law_retrieved_without_article_detail_does_not_pass_an_article(self):
        pack = [_law("출입국관리법")]  # search hit only, no article text fetched
        result = scg.verify_statute_citations("출입국관리법 제20조", pack)
        self.assertEqual(result["citations"][0]["verification_status"],
                         scg.STATUS_ARTICLE_NOT_IN_EVIDENCE)
        self.assertEqual(result["citations"][0]["reason"], "no_article_detail_retrieved")

    def test_missing_evidence_pack_is_unverifiable_not_absent(self):
        result = scg.verify_statute_citations("출입국관리법 제20조", [],
                                              evidence_available=False)
        self.assertEqual(result["status"], "unverifiable")
        self.assertEqual(result["citations"][0]["verification_status"],
                         scg.STATUS_UNVERIFIABLE)

    def test_no_citations_is_its_own_status(self):
        result = scg.verify_statute_citations("체류자격 변경 절차를 확인하세요", PACK)
        self.assertEqual(result["status"], "no_statute_citations")

    def test_bare_article_inherits_the_preceding_law(self):
        result = scg.verify_statute_citations(
            "출입국관리법 제20조를 보세요. 또한 제999조도 참고하세요.", PACK)
        statuses = [c["verification_status"] for c in result["citations"]]
        self.assertIn(scg.STATUS_ARTICLE_NOT_IN_EVIDENCE, statuses)

    def test_failure_summary_carries_no_answer_text(self):
        result = scg.verify_statute_citations(
            "민감한 개인정보가 담긴 문장. 출입국관리법 제999조.", PACK)
        blob = str(result["failure_summary"])
        self.assertNotIn("민감한", blob)
        self.assertIn("제999조", blob)


class RepairTests(unittest.TestCase):
    def test_failed_citation_is_marked_not_silently_deleted(self):
        text = "출입국관리법 제999조에 따라 신고해야 합니다."
        verification = scg.verify_statute_citations(text, PACK)
        repaired = scg.strip_failed_statute_citations(text, verification)
        self.assertIn("미확인 인용", repaired)
        self.assertIn("신고해야 합니다", repaired)

    def test_verified_citation_is_left_untouched(self):
        text = "출입국관리법 제20조에 따라 확인하세요."
        verification = scg.verify_statute_citations(text, PACK)
        self.assertEqual(scg.strip_failed_statute_citations(text, verification), text)


if __name__ == "__main__":
    unittest.main()
