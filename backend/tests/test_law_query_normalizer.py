"""Law-query normalization, alias resolution, ranking and lifecycle tests.

Covers the Phase 7 law-search matrix: exact official name, 약칭, short names, the
민법/난민법 substring trap, 시행령·시행규칙 hierarchy, repealed and scheduled statutes,
zero results, HTTP 403, timeout, malformed JSON/XML, OC redaction, and cache.

Every external call is mocked; no live law.go.kr access is required.

    python3 -m pytest backend/tests/test_law_query_normalizer.py -q
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import law_query_normalizer as lqn  # noqa: E402
from services import law_tools as lt  # noqa: E402
from services.grounding_config import GroundingConfig  # noqa: E402

LAW_ENV = ("LAW_API_OC", "LAW_API_KEY", "LAW_GROUNDING_MODE", "LAW_API_BASE_URL")


def _cfg(**overrides):
    base = dict(mode="enabled", law_api_oc="secret-oc-value", timeout_seconds=5.0)
    base.update(overrides)
    return GroundingConfig(**base)


_ROW_SEQ = [0]


def _law_row(name, **extra):
    # Distinct ids per row: the payload walker de-duplicates on 법령ID, so shared
    # ids would silently collapse a multi-row fixture into one.
    _ROW_SEQ[0] += 1
    row = {"법령명한글": name, "법령ID": f"00138{_ROW_SEQ[0]}",
           "법령일련번호": f"26758{_ROW_SEQ[0]}", "법령구분명": "법률"}
    row.update(extra)
    return row


def _body(*rows):
    return json.dumps({"LawSearch": {"law": list(rows)}}, ensure_ascii=False)


class _Transport:
    """Records every URL and replies from a per-query script."""

    def __init__(self, script=None, default=None):
        self.script = script or {}
        self.default = default
        self.urls = []

    def __call__(self, url, timeout):
        self.urls.append(url)
        for needle, response in self.script.items():
            if needle in url:
                return response
        if self.default is not None:
            return self.default
        return lt.LawHttpResponse(ok=True, status_code=200, text=_body())


def _ok(text):
    return lt.LawHttpResponse(ok=True, status_code=200, text=text)


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------
class NormalizationTests(unittest.TestCase):
    def test_collapses_spacing_and_full_width_forms(self):
        self.assertEqual(lqn.normalize_law_search_text("출입국  관리법"), "출입국 관리법")
        self.assertEqual(lqn.normalize_law_search_text(" 국적법 "), "국적법")

    def test_section_sign_becomes_article_marker(self):
        self.assertIn("제20", lqn.normalize_law_search_text("출입국관리법 §20"))

    def test_repairs_known_hangul_typos(self):
        self.assertEqual(lqn.normalize_law_search_text("출입국관리벚"), "출입국관리법")

    def test_alias_key_ignores_space_case_and_interpunct(self):
        self.assertEqual(
            lqn.normalize_alias_key("재외동포 법"),
            lqn.normalize_alias_key("재외동포법"),
        )
        self.assertEqual(lqn.normalize_alias_key("A·B"), lqn.normalize_alias_key("ab"))

    def test_latin_hangul_boundary_is_separated(self):
        self.assertEqual(lqn.normalize_law_search_text("FTA특례법"), "FTA 특례법")


# ---------------------------------------------------------------------------
# Alias resolution
# ---------------------------------------------------------------------------
class AliasResolutionTests(unittest.TestCase):
    def test_official_abbreviation_resolves_to_canonical_title(self):
        resolved = lqn.resolve_law_alias("재외동포법")
        self.assertEqual(resolved.canonical, "재외동포의 출입국과 법적 지위에 관한 법률")
        self.assertEqual(resolved.matched_alias, "재외동포법")

    def test_ambiguous_sibling_statute_is_offered_not_substituted(self):
        # 재외동포기본법 is a *different* statute; it must appear as an alternative
        # so the caller can disambiguate rather than be silently redirected.
        resolved = lqn.resolve_law_alias("재외동포법")
        self.assertIn("재외동포기본법", resolved.alternatives)

    def test_unknown_name_is_returned_unchanged(self):
        resolved = lqn.resolve_law_alias("존재하지않는가상법")
        self.assertEqual(resolved.canonical, "존재하지않는가상법")
        self.assertEqual(resolved.alternatives, [])

    def test_embedded_alias_inside_longer_query_is_expanded(self):
        matches = lqn.extract_embedded_aliases("외국인고용법 제9조 신고")
        self.assertTrue(matches)
        self.assertEqual(matches[0]["canonical"], "외국인근로자의 고용 등에 관한 법률")
        self.assertIn("외국인근로자의 고용 등에 관한 법률", matches[0]["expanded_query"])

    def test_longest_alias_wins_over_shorter_prefix(self):
        matches = lqn.extract_embedded_aliases("출입국관리법시행규칙 별표")
        canonicals = [m["canonical"] for m in matches]
        self.assertIn("출입국관리법 시행규칙", canonicals)

    def test_query_expansion_orders_canonical_first(self):
        expansion = lqn.expand_law_query("재외동포법")
        self.assertEqual(expansion.expanded[0], "재외동포의 출입국과 법적 지위에 관한 법률")


class NonLawKeywordTests(unittest.TestCase):
    def test_procedural_words_are_stripped_on_fallback(self):
        self.assertEqual(lqn.strip_non_law_keywords("출입국관리법 과태료 기준"), "출입국관리법")

    def test_bare_statute_token_is_extracted_from_sentence(self):
        self.assertEqual(lqn.extract_law_name_pattern("출입국관리법 제20조"), "출입국관리법")
        self.assertEqual(
            lqn.extract_law_name_pattern("출입국관리법 제20조가 궁금해요"), "출입국관리법")

    def test_sentence_without_a_statute_token_yields_nothing(self):
        self.assertEqual(lqn.extract_law_name_pattern("회사를 옮기려면 어떻게 하나요"), "")


# ---------------------------------------------------------------------------
# The substring trap and the match guard
# ---------------------------------------------------------------------------
class LooseMatchTests(unittest.TestCase):
    def test_interpunct_variants_match(self):
        self.assertTrue(lqn.loose_match_law_name(
            "식품 등의 표시·광고에 관한 법률",
            "식품 등의 표시ㆍ광고에 관한 법률",
        ))

    def test_spacing_variants_match(self):
        self.assertTrue(lqn.loose_match_law_name("출입국 관리법", "출입국관리법"))

    def test_civil_code_does_not_match_refugee_act(self):
        # 「난민법」 contains 「민법」 as a substring — the canonical false positive
        # from the Open Law API's LIKE search.
        self.assertFalse(lqn.loose_match_law_name("민법", "난민법"))

    def test_refugee_act_query_does_not_match_civil_code(self):
        self.assertFalse(lqn.loose_match_law_name("난민법", "민법"))

    def test_parent_act_prefix_matches_its_decree(self):
        self.assertTrue(lqn.loose_match_law_name("출입국관리법", "출입국관리법 시행령"))

    def test_alias_input_matches_official_title(self):
        self.assertTrue(lqn.resolved_law_matches(
            "재외동포법", "재외동포의 출입국과 법적 지위에 관한 법률"))

    def test_unrelated_law_fails_the_guard(self):
        self.assertFalse(lqn.resolved_law_matches("출입국관리법", "도로교통법"))


class RelevanceRankingTests(unittest.TestCase):
    def test_exact_name_outranks_substring_noise(self):
        rows = [
            {"law_name": "난민법"},
            {"law_name": "민법"},
        ]
        ranked = lqn.rank_law_candidates(rows, "민법")
        self.assertEqual(ranked[0]["law_name"], "민법")
        self.assertTrue(ranked[0]["name_match"])
        self.assertFalse(ranked[1]["name_match"])

    def test_parent_act_outranks_its_decree_for_unqualified_query(self):
        rows = [
            {"law_name": "출입국관리법 시행규칙"},
            {"law_name": "출입국관리법 시행령"},
            {"law_name": "출입국관리법"},
        ]
        ranked = lqn.rank_law_candidates(rows, "출입국관리법")
        self.assertEqual(ranked[0]["law_name"], "출입국관리법")
        self.assertEqual(ranked[0]["hierarchy_level"], "statute")

    def test_hierarchy_is_a_layer_not_a_filter(self):
        rows = [{"law_name": "출입국관리법"}, {"law_name": "출입국관리법 시행령"},
                {"law_name": "출입국관리법 시행규칙"}]
        ranked = lqn.rank_law_candidates(rows, "출입국관리법")
        levels = {r["hierarchy_level"] for r in ranked}
        self.assertEqual(levels, {"statute", "enforcement_decree", "enforcement_rule"})
        self.assertEqual(len(ranked), 3, "subordinate instruments must not be dropped")

    def test_ranking_never_drops_rows(self):
        rows = [{"law_name": f"가상법{i}"} for i in range(7)]
        self.assertEqual(len(lqn.rank_law_candidates(rows, "출입국관리법")), 7)


# ---------------------------------------------------------------------------
# Lifecycle: 현행 / 폐지 / 시행예정
# ---------------------------------------------------------------------------
class LifecycleTests(unittest.TestCase):
    def test_repealed_statute_is_flagged(self):
        self.assertEqual(
            lqn.classify_law_lifecycle(status_code="폐지"), lqn.STATUS_REPEALED)

    def test_future_enforcement_date_is_scheduled(self):
        self.assertEqual(
            lqn.classify_law_lifecycle(enforcement_date="20990101", today=date(2026, 7, 26)),
            lqn.STATUS_SCHEDULED,
        )

    def test_past_enforcement_date_is_verified(self):
        self.assertEqual(
            lqn.classify_law_lifecycle(status_code="현행", enforcement_date="20240701",
                                       today=date(2026, 7, 26)),
            lqn.STATUS_VERIFIED,
        )

    def test_unknown_metadata_never_manufactures_a_repeal(self):
        self.assertEqual(lqn.classify_law_lifecycle(), lqn.STATUS_VERIFIED)


class EvidenceStatusMappingTests(unittest.TestCase):
    def test_every_mapped_status_is_a_known_enum_member(self):
        for error_type in ("", "law_api_timeout", "law_api_no_results",
                           "law_api_parse_error", "law_api_http_error"):
            self.assertIn(lqn.evidence_status_for(error_type), lqn.EVIDENCE_STATUSES)

    def test_forbidden_is_distinct_from_generic_unavailable(self):
        self.assertEqual(
            lqn.evidence_status_for("law_api_http_error", http_status=403),
            lqn.STATUS_FORBIDDEN,
        )
        self.assertEqual(
            lqn.evidence_status_for("law_api_http_error", http_status=502),
            lqn.STATUS_UNAVAILABLE,
        )

    def test_timeout_is_not_not_found(self):
        self.assertEqual(lqn.evidence_status_for("law_api_timeout"), lqn.STATUS_TIMEOUT)
        self.assertNotEqual(lqn.evidence_status_for("law_api_timeout"), lqn.STATUS_NOT_FOUND)

    def test_unknown_error_degrades_to_unavailable_never_verified(self):
        self.assertEqual(lqn.evidence_status_for("brand_new_failure"), lqn.STATUS_UNAVAILABLE)


class OutcomeSummaryTests(unittest.TestCase):
    def test_substring_only_results_report_not_found(self):
        ranked = lqn.rank_law_candidates([{"law_name": "난민법"}], "민법")
        outcome = lqn.summarize_search_outcome(ranked, query="민법")
        self.assertEqual(outcome["status"], lqn.STATUS_NOT_FOUND)
        self.assertIsNone(outcome["top"])

    def test_two_equally_scored_matches_are_ambiguous(self):
        ranked = lqn.annotate_lifecycle(lqn.rank_law_candidates(
            [{"law_name": "출입국관리법"}, {"law_name": "출입국관리법"}], "출입국관리법"))
        ranked[1]["law_name"] = "출입국관리법률"
        ranked[1]["name_match"] = True
        outcome = lqn.summarize_search_outcome(ranked, query="출입국관리법")
        self.assertEqual(outcome["status"], lqn.STATUS_AMBIGUOUS)

    def test_error_outcome_carries_status_not_empty_results(self):
        outcome = lqn.summarize_search_outcome([], query="출입국관리법",
                                               error_type="law_api_timeout")
        self.assertEqual(outcome["status"], lqn.STATUS_TIMEOUT)
        self.assertEqual(outcome["match_count"], 0)


# ---------------------------------------------------------------------------
# search_laws_ranked — end to end against a mocked transport
# ---------------------------------------------------------------------------
class RankedSearchTests(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in LAW_ENV}
        for k in LAW_ENV:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_exact_official_name_is_returned_first(self):
        transport = _Transport(default=_ok(_body(
            _law_row("난민법"), _law_row("출입국관리법"), _law_row("출입국관리법 시행령"))))
        result = lt.search_laws_ranked("출입국관리법", config=_cfg(), transport=transport)
        self.assertEqual(result["status"], lqn.STATUS_VERIFIED)
        self.assertEqual(result["top"]["law_name"], "출입국관리법")

    def test_alias_query_falls_back_to_canonical_title(self):
        canonical = "재외동포의 출입국과 법적 지위에 관한 법률"
        transport = _Transport(
            script={"%EC%9E%AC%EC%99%B8%EB%8F%99%ED%8F%AC%EB%B2%95": _ok(_body())},
            default=_ok(_body(_law_row(canonical))),
        )
        result = lt.search_laws_ranked("재외동포법", config=_cfg(), transport=transport)
        self.assertEqual(result["status"], lqn.STATUS_VERIFIED)
        self.assertEqual(result["top"]["law_name"], canonical)
        self.assertGreaterEqual(len(result["attempts"]), 2)

    def test_substring_noise_only_reports_not_found(self):
        transport = _Transport(default=_ok(_body(_law_row("난민법"))))
        result = lt.search_laws_ranked("민법", config=_cfg(), transport=transport)
        self.assertEqual(result["status"], lqn.STATUS_NOT_FOUND)

    def test_zero_rows_report_not_found(self):
        transport = _Transport(default=_ok(_body()))
        result = lt.search_laws_ranked("존재하지않는가상법", config=_cfg(), transport=transport)
        self.assertEqual(result["status"], lqn.STATUS_NOT_FOUND)

    def test_http_403_reports_forbidden_not_not_found(self):
        transport = _Transport(default=lt.LawHttpResponse(
            ok=False, status_code=403, error_type="http_error"))
        result = lt.search_laws_ranked("출입국관리법", config=_cfg(), transport=transport)
        self.assertEqual(result["status"], lqn.STATUS_FORBIDDEN)

    def test_timeout_reports_timeout_not_not_found(self):
        transport = _Transport(default=lt.LawHttpResponse(ok=False, error_type="timeout"))
        result = lt.search_laws_ranked("출입국관리법", config=_cfg(), transport=transport)
        self.assertEqual(result["status"], lqn.STATUS_TIMEOUT)

    def test_malformed_payload_reports_parse_failure(self):
        transport = _Transport(default=_ok("<<< not json and not xml >>>"))
        result = lt.search_laws_ranked("출입국관리법", config=_cfg(), transport=transport)
        self.assertIn(result["status"], {lqn.STATUS_PARSE_FAILED, lqn.STATUS_UNAVAILABLE})
        self.assertNotEqual(result["status"], lqn.STATUS_NOT_FOUND)

    def test_missing_credential_reports_unavailable(self):
        transport = _Transport(default=_ok(_body(_law_row("출입국관리법"))))
        result = lt.search_laws_ranked("출입국관리법", config=_cfg(law_api_oc=""),
                                       transport=transport)
        self.assertEqual(result["status"], lqn.STATUS_UNAVAILABLE)
        self.assertEqual(transport.urls, [], "no request may be issued without a credential")

    def test_repealed_statute_status_is_surfaced(self):
        transport = _Transport(default=_ok(_body(
            _law_row("출입국관리법", **{"현행연혁코드": "폐지"}))))
        result = lt.search_laws_ranked("출입국관리법", config=_cfg(), transport=transport)
        self.assertEqual(result["status"], lqn.STATUS_REPEALED)

    def test_future_enforcement_statute_is_scheduled(self):
        transport = _Transport(default=_ok(_body(
            _law_row("출입국관리법", **{"시행일자": "20990101"}))))
        result = lt.search_laws_ranked("출입국관리법", config=_cfg(), transport=transport,
                                       today=date(2026, 7, 26))
        self.assertEqual(result["status"], lqn.STATUS_SCHEDULED)

    def test_hierarchy_groups_statute_decree_and_rule(self):
        transport = _Transport(default=_ok(_body(
            _law_row("출입국관리법"),
            _law_row("출입국관리법 시행령", **{"법령구분명": "대통령령"}),
            _law_row("출입국관리법 시행규칙", **{"법령구분명": "부령"}))))
        result = lt.search_laws_ranked("출입국관리법", config=_cfg(), transport=transport)
        self.assertIn("statute", result["hierarchy"])
        self.assertIn("enforcement_decree", result["hierarchy"])
        self.assertIn("enforcement_rule", result["hierarchy"])

    def test_source_url_never_leaks_the_oc_credential(self):
        transport = _Transport(default=_ok(_body(_law_row("출입국관리법"))))
        result = lt.search_laws_ranked("출입국관리법", config=_cfg(), transport=transport)
        blob = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("secret-oc-value", blob)
        self.assertTrue(any("secret-oc-value" in u for u in transport.urls),
                        "the outbound URL must still carry the credential")

    def test_wide_display_window_is_requested(self):
        transport = _Transport(default=_ok(_body(_law_row("출입국관리법"))))
        lt.search_laws_ranked("출입국관리법", config=_cfg(), transport=transport)
        self.assertTrue(any("display=100" in u for u in transport.urls))

    def test_empty_query_short_circuits_without_a_request(self):
        transport = _Transport(default=_ok(_body(_law_row("출입국관리법"))))
        result = lt.search_laws_ranked("   ", config=_cfg(), transport=transport)
        self.assertEqual(result["status"], lqn.STATUS_NOT_FOUND)
        self.assertEqual(transport.urls, [])

    def test_retrieval_timestamp_is_recorded(self):
        transport = _Transport(default=_ok(_body(_law_row("출입국관리법"))))
        result = lt.search_laws_ranked("출입국관리법", config=_cfg(), transport=transport)
        self.assertTrue(result["retrieved_at"].endswith("Z"))


if __name__ == "__main__":
    unittest.main()
