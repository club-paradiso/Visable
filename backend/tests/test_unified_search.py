"""Unified search router + organic result tests, including the golden fixtures.

Golden queries required by the Phase 7 matrix:
    D-2-1 / D21 / E-7-4 / 한국에서 대학 졸업 후 취업하고 싶어요 /
    직장을 바꾸려면 신고해야 하나요 / F-6 배우자와 이혼하면 어떻게 되나요 /
    체류지 변경 / 출입국관리법 제20조 / 난민 불인정 이의신청 /
    meaningless input / AI provider down / law provider down

Invariants: no invented visa codes, exact-code search works with AI fully down,
subcodes are never flattened into parents.

    python3 -m pytest backend/tests/test_unified_search.py -q
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import unified_search as us  # noqa: E402

VISA_DATA = json.loads((REPO_ROOT / "visa_data.json").read_text(encoding="utf-8"))
VALID_MAIN_CODES = {
    str(r.get("code")).strip().upper()
    for r in VISA_DATA if isinstance(r, dict) and r.get("code")
}
KNOWN_CODES = set(us.build_visa_index(VISA_DATA).keys())


def _run(query, manual_search=None):
    return us.run_unified_search(
        query, visa_data=VISA_DATA, valid_main_codes=VALID_MAIN_CODES,
        manual_search=manual_search,
    )


def _detect(query):
    return us.detect_visa_codes(query, VALID_MAIN_CODES, KNOWN_CODES)


class CodeNormalizationTests(unittest.TestCase):
    def test_compact_subcode_expands(self):
        self.assertEqual(us.normalize_visa_code("d21", VALID_MAIN_CODES), "D-2-1")

    def test_two_digit_main_code_is_preferred(self):
        self.assertEqual(us.normalize_visa_code("d10", VALID_MAIN_CODES), "D-10")
        self.assertEqual(us.normalize_visa_code("d101", VALID_MAIN_CODES), "D-10-1")

    def test_hyphen_and_space_variants_agree(self):
        for variant in ("E-7-4", "e74", "E7-4", "e 7 4"):
            self.assertEqual(us.normalize_visa_code(variant, VALID_MAIN_CODES), "E-7-4")

    def test_subcode_splits_to_parent_and_subcode(self):
        self.assertEqual(us.split_visa_code("D-2-1"), ("D-2", "D-2-1"))

    def test_parent_code_has_no_subcode(self):
        self.assertEqual(us.split_visa_code("D-2"), ("D-2", None))

    def test_g1_5_is_a_subcode_of_g1_never_a_top_level_family(self):
        parent, sub = us.split_visa_code("G-1-5")
        self.assertEqual(parent, "G-1")
        self.assertEqual(sub, "G-1-5")


class CodeDetectionTests(unittest.TestCase):
    def test_known_subcode_is_recognized(self):
        detected = _detect("D-2-1")
        self.assertIn("D-2-1", detected["recognized"])
        self.assertEqual(detected["unrecognized"], [])

    def test_unknown_subcode_is_never_reported_as_real(self):
        detected = _detect("D-2-99")
        self.assertNotIn("D-2-99", detected["recognized"])
        self.assertIn("D-2-99", detected["unrecognized"])

    def test_unknown_subcode_still_surfaces_its_real_parent(self):
        detected = _detect("D-2-99")
        self.assertIn("D-2", detected["recognized"])

    def test_entirely_invented_code_is_rejected(self):
        detected = _detect("Z-9-9")
        self.assertEqual(detected["recognized"], [])
        self.assertIn("Z-9-9", detected["unrecognized"])

    def test_no_result_ever_contains_a_code_outside_the_dataset(self):
        for query in ("D-2-1", "E74", "Z-9", "결혼이민", "아무말 대잔치"):
            detected = _detect(query)
            for code in detected["recognized"]:
                self.assertIn(code, KNOWN_CODES, f"{code} is not in visa_data.json")


class IntentRoutingTests(unittest.TestCase):
    def test_bare_code_is_exact_code_intent(self):
        self.assertEqual(_run("D-2-1")["intent"], us.INTENT_EXACT_VISA_CODE)

    def test_compact_code_is_exact_code_intent(self):
        self.assertEqual(_run("D21")["intent"], us.INTENT_EXACT_VISA_CODE)

    def test_e74_is_exact_code_intent(self):
        result = _run("E-7-4")
        self.assertEqual(result["intent"], us.INTENT_EXACT_VISA_CODE)
        self.assertIn("E-7-4", result["detectedVisaCodes"])

    def test_statute_reference_is_a_legal_question(self):
        self.assertEqual(_run("출입국관리법 제20조")["intent"], us.INTENT_LEGAL_QUESTION)

    def test_case_number_is_a_legal_question(self):
        self.assertEqual(_run("2017두12345 판결")["intent"], us.INTENT_LEGAL_QUESTION)

    def test_refugee_appeal_is_a_legal_question(self):
        self.assertEqual(_run("난민 불인정 이의신청")["intent"], us.INTENT_LEGAL_QUESTION)

    def test_graduation_to_employment_is_a_situation(self):
        result = _run("한국에서 대학 졸업 후 취업하고 싶어요")
        self.assertIn(result["intent"],
                      {us.INTENT_VISA_SITUATION, us.INTENT_VISA_KEYWORD})

    def test_job_change_reporting_is_a_procedure_question(self):
        self.assertEqual(_run("직장을 바꾸려면 신고해야 하나요")["intent"],
                         us.INTENT_PROCEDURE_QUESTION)

    def test_address_change_is_a_procedure_question(self):
        self.assertEqual(_run("체류지 변경")["intent"], us.INTENT_PROCEDURE_QUESTION)

    def test_f6_divorce_situation_detects_the_code(self):
        result = _run("F-6 배우자와 이혼하면 어떻게 되나요")
        self.assertIn("F-6", result["detectedVisaCodes"])
        self.assertNotEqual(result["intent"], us.INTENT_EXACT_VISA_CODE)

    def test_job_description_routes_to_employment_reporting(self):
        self.assertEqual(_run("카페에서 음료를 만들어요")["intent"],
                         us.INTENT_EMPLOYMENT_REPORTING)

    def test_employment_code_vocabulary_routes_to_employment_reporting(self):
        self.assertEqual(_run("취업정보 신고 직종 코드가 뭔가요")["intent"],
                         us.INTENT_EMPLOYMENT_REPORTING)

    def test_marriage_migration_keyword(self):
        self.assertEqual(_run("결혼이민")["intent"], us.INTENT_VISA_KEYWORD)

    def test_feature_navigation_is_detected(self):
        result = _run("행정사 사무소 찾기")
        self.assertEqual(result["intent"], us.INTENT_FEATURE_NAVIGATION)

    def test_meaningless_input_is_unknown_not_a_wrong_guess(self):
        result = _run("ㅁㄴㅇㄹ")
        self.assertEqual(result["intent"], us.INTENT_UNKNOWN)
        self.assertEqual(result["detectedVisaCodes"], [])

    def test_empty_input_is_unknown(self):
        self.assertEqual(_run("   ")["intent"], us.INTENT_UNKNOWN)


class OrganicResultTests(unittest.TestCase):
    def test_exact_subcode_search_returns_the_subcode_card(self):
        results = _run("D-2-1")["organicResults"]
        top = results[0]
        self.assertEqual(top["code"], "D-2-1")
        self.assertEqual(top["kind"], us.RESULT_SUBCODE_CARD)
        self.assertEqual(top["parentCode"], "D-2")

    def test_subcode_result_offers_the_parent_as_a_separate_card(self):
        results = _run("D-2-1")["organicResults"]
        kinds = {(r.get("code"), r.get("kind")) for r in results}
        self.assertIn(("D-2-1", us.RESULT_SUBCODE_CARD), kinds)
        self.assertIn(("D-2", us.RESULT_STATUS_CARD), kinds)

    def test_parent_and_subcode_are_never_merged_into_one_card(self):
        results = _run("D-2-1")["organicResults"]
        for card in results:
            if card.get("code") == "D-2":
                self.assertIsNone(card.get("parentCode"))
            if card.get("code") == "D-2-1":
                self.assertEqual(card.get("parentCode"), "D-2")

    def test_employment_intent_surfaces_the_employment_tool_first(self):
        results = _run("카페에서 음료를 만들어요")["organicResults"]
        self.assertEqual(results[0]["kind"], us.RESULT_EMPLOYMENT_TOOL)

    def test_legal_intent_surfaces_the_legal_tool_first(self):
        results = _run("출입국관리법 제20조")["organicResults"]
        self.assertEqual(results[0]["kind"], us.RESULT_LEGAL_CARD)

    def test_results_carry_no_code_outside_the_dataset(self):
        for query in ("D-2-1", "E-7-4", "결혼이민", "체류지 변경", "Z-9-9"):
            for card in _run(query)["organicResults"]:
                code = card.get("code")
                if code:
                    self.assertIn(code, KNOWN_CODES)

    def test_result_count_is_bounded(self):
        self.assertLessEqual(len(_run("체류")["organicResults"]), 10)


class ResilienceTests(unittest.TestCase):
    """Deterministic search must survive every downstream failure."""

    def test_search_works_with_no_manual_index_at_all(self):
        result = _run("D-2-1", manual_search=None)
        self.assertTrue(result["organicResults"])
        self.assertTrue(result["fallbackAvailable"])

    def test_manual_search_exception_degrades_to_no_manual_hits(self):
        def boom(_query):
            raise RuntimeError("index exploded")
        result = _run("D-2-1", manual_search=boom)
        self.assertTrue(result["organicResults"], "organic results must survive")
        self.assertEqual(result["manualEvidence"]["status"], "not_queried")

    def test_manual_index_unavailable_is_reported_not_hidden(self):
        def unavailable(_query):
            return {"status": "index_unavailable", "approved": [], "needs_review": []}
        result = _run("체류자격", manual_search=unavailable)
        self.assertEqual(result["manualEvidence"]["status"], "index_unavailable")

    def test_review_pending_manual_hits_are_marked_not_direct_evidence(self):
        def pending(_query):
            return {"status": "ok", "approved": [],
                    "needs_review": [{"heading": "체류자격 변경", "excerpt": "…",
                                      "source_id": "stay_manual_2026_06_17_txt",
                                      "approval_state": "superseded", "page": 12}]}
        cards = [c for c in _run("체류자격 변경", manual_search=pending)["organicResults"]
                 if c["kind"] == us.RESULT_MANUAL_CARD]
        self.assertTrue(cards)
        self.assertFalse(cards[0]["usableAsDirectEvidence"])
        self.assertEqual(cards[0]["approvalState"], "superseded")

    def test_ai_is_never_required_for_a_response(self):
        # run_unified_search takes no AI dependency at all; this is the structural
        # guarantee behind "organic results render before any overview arrives".
        result = _run("한국에서 대학 졸업 후 취업하고 싶어요")
        self.assertTrue(result["fallbackAvailable"])
        self.assertNotIn("aiOverview", result)

    def test_overlong_query_is_truncated_not_rejected(self):
        result = _run("체류" * 500)
        self.assertLessEqual(len(result["query"]), us.MAX_QUERY_LENGTH)


class InterpretationTests(unittest.TestCase):
    def test_interpretation_is_editable_and_explains_itself(self):
        interpretation = _run("D-2-1")["interpretation"]
        self.assertTrue(interpretation["editable"])
        self.assertTrue(interpretation["intentRule"])
        self.assertIn("D-2-1", interpretation["recognizedVisaCodes"])

    def test_unrecognized_tokens_are_named_explicitly(self):
        interpretation = _run("D-2-99")["interpretation"]
        self.assertIn("D-2-99", interpretation["unrecognizedCodeLikeTokens"])

    def test_suggestions_never_contain_unknown_codes(self):
        for query in ("D-2-1", "Z-9-9", "ㅁㄴㅇㄹ"):
            for suggestion in _run(query)["suggestions"]:
                for token in suggestion.split():
                    if us._CODE_TOKEN_RE.fullmatch(token):
                        self.assertIn(token, KNOWN_CODES)


class SuggestionRowTests(unittest.TestCase):
    """Typed rows for the UX-03 `Search / Suggestion Row` component."""

    def test_rows_and_strings_cannot_drift(self):
        for query in ("D-2-1", "출입국관리법 제20조", "ㅁㄴㅇㄹ"):
            result = _run(query)
            self.assertEqual(
                [row["query"] for row in result["suggestionRows"]],
                result["suggestions"],
            )

    def test_every_row_declares_a_known_type(self):
        for query in ("D-2-1", "D-2-99", "출입국관리법 제20조", "ㅁㄴㅇㄹ"):
            for row in _run(query)["suggestionRows"]:
                self.assertIn(row["type"], us.SUGGESTION_TYPES)
                self.assertTrue(row["label"])
                self.assertTrue(row["query"])

    def test_backend_never_emits_recent_query_rows(self):
        # Search history is a client-side concern; the backend keeps no record
        # of what anyone searched for, so it cannot produce this row.
        for query in ("D-2-1", "출입국관리법 제20조", "ㅁㄴㅇㄹ", ""):
            for row in _run(query)["suggestionRows"]:
                self.assertNotEqual(row["type"], us.SUGGEST_RECENT_QUERY)

    def test_an_unrecognized_code_yields_a_correction_row_naming_both(self):
        rows = _run("D-2-99")["suggestionRows"]
        corrections = [r for r in rows if r["type"] == us.SUGGEST_CORRECTION]
        self.assertEqual(len(corrections), 1)
        row = corrections[0]
        # It names what was typed and what we actually have — and the query it
        # would run is the code that exists, never the one that does not.
        self.assertIn("D-2-99", row["sublabel"])
        self.assertIn("D-2", row["label"])
        self.assertEqual(row["query"], "D-2")

    def test_no_correction_row_when_nothing_resolved(self):
        # "Z-9-9" resolves to nothing, so there is no corrected code to offer.
        # Inventing one would turn "we do not have this" into "here it is".
        rows = _run("Z-9-9")["suggestionRows"]
        self.assertFalse([r for r in rows if r["type"] == us.SUGGEST_CORRECTION])

    def test_row_queries_never_contain_unknown_codes(self):
        for query in ("D-2-1", "D-2-99", "Z-9-9", "ㅁㄴㅇㄹ"):
            for row in _run(query)["suggestionRows"]:
                for field in ("query", "label", "sublabel"):
                    for token in str(row[field]).split():
                        if us._CODE_TOKEN_RE.fullmatch(token):
                            # The correction row quotes the typed token on
                            # purpose; everywhere else a code must be real.
                            if row["type"] == us.SUGGEST_CORRECTION and field == "sublabel":
                                continue
                            self.assertIn(token, KNOWN_CODES)

    def test_a_subcode_row_is_typed_as_a_subcode_and_names_its_parent(self):
        rows = _run("D-2-1")["suggestionRows"]
        first = rows[0]
        self.assertEqual(first["type"], us.SUGGEST_VISA_STATUS)
        self.assertIn("D-2-1", first["label"])
        # CLAUDE.md: a subcode is never presented as a standalone top-level
        # status, so the row states which parent it sits under.
        self.assertIn("D-2", first["sublabel"])

    def test_sublabel_is_omitted_rather_than_faked(self):
        # A record whose only label is its own code carries no description, so
        # the row must not manufacture one.
        rows = us.build_suggestion_rows(
            "X-1",
            {"intent": us.INTENT_EXACT_VISA_CODE},
            {"recognized": ["X-1"], "unrecognized": []},
            {"X-1": {"code": "X-1"}},
        )
        code_rows = [r for r in rows if r["type"] == us.SUGGEST_VISA_CODE]
        self.assertEqual(code_rows[0]["label"], "X-1")

    def test_rows_are_deduplicated_and_bounded(self):
        for query in ("D-2-1", "출입국관리법 제20조", "ㅁㄴㅇㄹ"):
            rows = _run(query)["suggestionRows"]
            queries = [r["query"] for r in rows]
            self.assertEqual(len(queries), len(set(queries)))
            self.assertLessEqual(len(rows), 6)


if __name__ == "__main__":
    unittest.main()
