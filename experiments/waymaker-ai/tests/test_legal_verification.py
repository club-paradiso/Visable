"""Seven-layer verification: one test per rule bullet of spec 07 §3 and per invariant of §2.

Expected outcomes are written from the spec, not from the implementation. All
evidence comes from the synthetic bundle (fictional laws). Dates: the question
is asked on 2026-10-19 unless a test says otherwise. On that date
가상체류관리법 (SYN-ACT-0001) is in its 2026-10-02 version (제5조: 15일), the
2024-03-01 version said 14일 and the pending 2027-06-01 version says 20일.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path

import pytest

from waymaker_ai.contracts import (
    AnchorKind,
    ClaimInput,
    ClaimVerification,
    Coverage,
    LayerOutcome as O,
    LookupResult,
    LookupStatus,
    OverallStatus,
    RelevantDates,
    Scope,
    VerificationCode as V,
    VerificationLayer as L,
    compact,
    iter_layer_order,
)
from waymaker_ai.legal.adapters import FixtureAdapter
from waymaker_ai.legal.injection import UNTRUSTED_FLAG
from waymaker_ai.legal.verification import (
    MAX_ATTRIBUTION_LOOKUPS,
    MAX_RENUMBERING_LOOKUPS,
    OUTCOME_SEVERITY,
    conflicts_of,
    contains_number,
    parent_code,
    verify_claim,
    worst,
)

D = dt.date
Q = D(2026, 10, 19)
CORE = Path(__file__).resolve().parents[1] / "datasets" / "fixtures" / "sources" / "synthetic_core.json"
ABSENCE = {V.SOURCE_NOT_FOUND.value, V.CITATION_NOT_FOUND.value}

ACT = "가상체류관리법"
RULE = "가상체류관리법 시행규칙"
DECREE = "가상체류관리법 시행령"
QUOTE_2024 = "변경한 날부터 14일 이내에"      # SYN-A1-1002, superseded
QUOTE_2026 = "변경한 날부터 15일 이내에"      # SYN-A1-1003, in force on Q
QUOTE_2027 = "변경한 날부터 20일 이내에"      # SYN-A1-1004, pending
RULE_73_NOW = "가상 수수료는 현금으로 납부한다"
RULE_73_2027 = "현금 또는 가상전자납부 방식으로 납부할 수 있다"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def load_core() -> dict:
    return json.loads(CORE.read_text(encoding="utf-8"))


def mutated_core(mutate=None) -> dict:
    bundle = load_core()
    if mutate is not None:
        mutate(bundle)
    return bundle


def core_adapter(mutate=None) -> FixtureAdapter:
    return FixtureAdapter.from_bundle(mutated_core(mutate))


def claim(*citations, claim_id="c", **fields) -> ClaimInput:
    return ClaimInput(claim_id=claim_id, text=fields.pop("text", "synthetic claim"), citations=tuple(citations), **fields)


def verify(item: ClaimInput, *, adapter=None, on=Q, anchor=AnchorKind.QUESTION_DATE, dates=None, question_date=Q,
           **kwargs):
    adapter = adapter or core_adapter()
    dates = dates or RelevantDates(question_date=on)
    return verify_claim(item, adapter, dates=dates, anchor=anchor, question_date=question_date, **kwargs)


def at(result, layer):
    found = result.layer(layer)
    assert found is not None, f"{layer.value} not reported"
    return found.outcome, found.code


def conduct(on):
    return {"dates": RelevantDates(question_date=Q, conduct_date=on), "anchor": AnchorKind.CONDUCT_DATE}


# ---------------------------------------------------------------------------
# §3 preamble: aggregation over citations
# ---------------------------------------------------------------------------
def test_every_layer_is_reported_in_order_for_every_claim():
    claims = [
        claim(f"{ACT} 제5조제1항", numbers=("15일",)),
        claim("가상응답장애법 제2조"),
        claim(),
        claim("제10조"),
    ]
    for item in claims:
        result = verify(item)
        assert [r.layer for r in result.layers] == list(iter_layer_order())
        assert result.overall() is not OverallStatus.VERIFIED_PARTIAL


def test_the_severity_order_is_fail_unavailable_review_pass_not_applicable():
    assert OUTCOME_SEVERITY == (O.FAIL, O.UNAVAILABLE, O.NEEDS_REVIEW, O.PASS, O.NOT_APPLICABLE)


def test_each_layer_reports_the_worst_outcome_over_the_citations():
    result = verify(claim(f"{ACT} 제5조제1항", "같은 법 제99조", numbers=("15일",)))
    assert at(result, L.SOURCE_IDENTITY) == (O.PASS, V.SOURCE_VERIFIED)
    assert at(result, L.CITATION_IDENTITY) == (O.FAIL, V.CITATION_NOT_FOUND)
    assert "제5조제1항" in result.layer(L.CITATION_IDENTITY).detail   # both citations are reported
    assert result.overall() is OverallStatus.FAILED
    good_first = verify(claim("같은 법 제99조", f"{ACT} 제5조제1항"), context_title=ACT)
    assert at(good_first, L.CITATION_IDENTITY) == (O.FAIL, V.CITATION_NOT_FOUND)


def test_a_claim_without_citations_skips_l1_to_l4_and_is_judged_on_guidance():
    result = verify(claim(topic="syn_report_deadline", numbers=("14일",)))
    for layer in (L.SOURCE_IDENTITY, L.VERSION_IDENTITY, L.CITATION_IDENTITY, L.TEXT_CORRESPONDENCE):
        assert at(result, layer) == (O.NOT_APPLICABLE, V.NOT_CHECKED)
    assert at(result, L.CLAIM_SUPPORT) == (O.PASS, V.CLAIM_SUPPORTED)


def test_a_claim_with_neither_citations_nor_guidance_is_unsupported():
    result = verify(claim())
    assert at(result, L.CLAIM_SUPPORT) == (O.FAIL, V.CLAIM_UNSUPPORTED)
    assert result.overall() is OverallStatus.FAILED


# ---------------------------------------------------------------------------
# §3 blocked layers (decided 2026-10-20)
# ---------------------------------------------------------------------------
DEPENDENT = (L.VERSION_IDENTITY, L.CITATION_IDENTITY, L.TEXT_CORRESPONDENCE, L.CLAIM_SUPPORT, L.APPLICABILITY)


@pytest.mark.parametrize("citation, blocker, overall", [
    ("가상특례법 제2조", (O.NEEDS_REVIEW, V.SOURCE_AMBIGUOUS), OverallStatus.HUMAN_REVIEW_REQUIRED),
    ("가상응답장애법 제2조", (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE), OverallStatus.VERIFICATION_UNAVAILABLE),
    ("가상체류관리기본법 제5조", (O.FAIL, V.SOURCE_NOT_FOUND), OverallStatus.FAILED),
    ("가상출국관리법 제3조", (O.FAIL, V.SOURCE_REPEALED), OverallStatus.FAILED),
], ids=["ambiguous", "unreachable", "not_found", "repealed"])
def test_layers_after_an_l1_blocker_carry_its_outcome_with_not_checked(citation, blocker, overall):
    result = verify(claim(citation, quoted_text="가상 문언", numbers=("7일",)))
    assert at(result, L.SOURCE_IDENTITY) == blocker
    for layer in DEPENDENT:
        outcome, code = at(result, layer)
        assert (outcome, code) == (blocker[0], V.NOT_CHECKED), layer
        assert "source_identity" in result.layer(layer).detail, layer   # the detail names the blocker
    assert [r.layer for r in result.layers] == list(iter_layer_order())   # no layer omitted
    assert result.overall() is overall


def test_an_ambiguous_title_is_human_review_not_verification_unavailable():
    assert verify(claim("가상특례법 제2조")).overall() is OverallStatus.HUMAN_REVIEW_REQUIRED


def test_layers_after_an_l2_blocker_carry_its_outcome():
    result = verify(claim(f"{ACT} 제5조", quoted_text=QUOTE_2026), **conduct(D(2010, 1, 1)))
    assert at(result, L.VERSION_IDENTITY) == (O.UNAVAILABLE, V.VERSION_HISTORY_INCOMPLETE)
    for layer in (L.CITATION_IDENTITY, L.TEXT_CORRESPONDENCE, L.CLAIM_SUPPORT, L.APPLICABILITY):
        assert at(result, layer) == (O.UNAVAILABLE, V.NOT_CHECKED), layer
        assert "version_identity" in result.layer(layer).detail
    assert result.overall() is OverallStatus.VERIFICATION_UNAVAILABLE


def test_a_real_finding_of_equal_severity_is_reported_before_a_carried_blocker():
    # Unknown anchor date: L2 needs_review / insufficient_context blocks L3-L5; L6 reports its own finding.
    result = verify(claim(f"{ACT} 제5조"), anchor=AnchorKind.DECISION_DATE)
    assert at(result, L.CITATION_IDENTITY) == (O.NEEDS_REVIEW, V.NOT_CHECKED)
    assert at(result, L.APPLICABILITY) == (O.NEEDS_REVIEW, V.INSUFFICIENT_CONTEXT)
    assert result.overall() is OverallStatus.HUMAN_REVIEW_REQUIRED


def test_layers_after_an_l3_blocker_carry_its_outcome():
    result = verify(claim(f"{ACT} 제8조", quoted_text="가상 보고서를 작성한다"))   # malformed XML
    assert at(result, L.CITATION_IDENTITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)
    for layer in (L.TEXT_CORRESPONDENCE, L.CLAIM_SUPPORT, L.APPLICABILITY):
        assert at(result, layer) == (O.UNAVAILABLE, V.NOT_CHECKED), layer
        assert "citation_identity" in result.layer(layer).detail
    assert at(result, L.VERSION_IDENTITY) == (O.PASS, V.VERSION_VERIFIED)   # earlier layers are not rewritten


@pytest.mark.parametrize("structure_complete, l3, overall", [
    (True, (O.FAIL, V.CITATION_NOT_FOUND), OverallStatus.FAILED),
    (False, (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE), OverallStatus.VERIFICATION_UNAVAILABLE),
], ids=["structure_complete", "structure_not_complete"])
def test_layers_after_a_missing_sub_unit_carry_l3s_outcome(structure_complete, l3, overall):
    """No provision after L3 includes a cited 항 that L3 could not establish in the article it retrieved.

    The rest of 제5조 does not hold the quotation or the number. Judging it
    anyway would report text_mismatch / claim_unsupported, and for a partly
    parsed article that is absence inferred from incomplete evidence (§2.1-2.2).
    """
    adapter = core_adapter() if structure_complete else core_adapter(_structure_incomplete)
    result = verify(claim(f"{ACT} 제5조제3항", quoted_text="변경한 날부터 60일 이내에", numbers=("60일",)), adapter=adapter)
    assert at(result, L.CITATION_IDENTITY) == l3
    for layer in (L.TEXT_CORRESPONDENCE, L.CLAIM_SUPPORT, L.APPLICABILITY):
        assert at(result, layer) == (l3[0], V.NOT_CHECKED), layer
        assert "citation_identity" in result.layer(layer).detail, layer
    assert at(result, L.VERSION_IDENTITY) == (O.PASS, V.VERSION_VERIFIED)
    assert not {V.TEXT_MISMATCH.value, V.CLAIM_UNSUPPORTED.value} & set(result.codes())
    assert result.overall() is overall


def test_a_quotation_elsewhere_in_the_article_does_not_verify_a_missing_sub_unit():
    result = verify(claim(f"{ACT} 제5조제3항", quoted_text=QUOTE_2026, numbers=("15일",)))   # QUOTE_2026 is 제1항
    assert at(result, L.CITATION_IDENTITY) == (O.FAIL, V.CITATION_NOT_FOUND)
    assert at(result, L.TEXT_CORRESPONDENCE) == (O.FAIL, V.NOT_CHECKED)
    assert at(result, L.CLAIM_SUPPORT) == (O.FAIL, V.NOT_CHECKED)
    assert V.TEXT_MATCH_VERIFIED.value not in result.codes() and V.CLAIM_SUPPORTED.value not in result.codes()
    # With a second citation whose text L5 can read, the quotation still does not count as verified at L4.
    paired = verify(claim(f"{ACT} 제5조제3항", f"{ACT} 제6조", quoted_text=QUOTE_2026))
    assert at(paired, L.TEXT_CORRESPONDENCE) == (O.FAIL, V.NOT_CHECKED)
    assert at(paired, L.CLAIM_SUPPORT) == (O.NEEDS_REVIEW, V.HUMAN_REVIEW_REQUIRED)


def test_a_sub_unit_missing_from_c_but_quoted_from_another_version_is_judged_on_that_text():
    """가목 is in the 2024 text only. As for an article missing from C, L2 fails and L4 reads the attributed text."""
    result = verify(claim(f"{ACT} 제5조제2항제1호가목", quoted_text="가. 전자 신고서"))
    check = result.citation_checks[0]
    assert check.attributed_version.key == ("SYN-A1-1002", "2024-03-01")
    assert at(result, L.VERSION_IDENTITY) == (O.FAIL, V.SOURCE_OUTDATED)
    assert at(result, L.CITATION_IDENTITY) == (O.FAIL, V.CITATION_NOT_FOUND)
    assert at(result, L.TEXT_CORRESPONDENCE) == (O.PASS, V.TEXT_MATCH_VERIFIED)
    assert result.overall() is OverallStatus.FAILED


def test_a_layer_with_nothing_to_check_stays_not_applicable_after_a_blocker():
    result = verify(claim("가상특례법"))   # a whole law, no quotation: L3 and L4 have nothing to check
    assert at(result, L.SOURCE_IDENTITY) == (O.NEEDS_REVIEW, V.SOURCE_AMBIGUOUS)
    assert at(result, L.VERSION_IDENTITY) == (O.NEEDS_REVIEW, V.NOT_CHECKED)
    assert at(result, L.CITATION_IDENTITY) == (O.NOT_APPLICABLE, V.NOT_CHECKED)
    assert at(result, L.TEXT_CORRESPONDENCE) == (O.NOT_APPLICABLE, V.NOT_CHECKED)


def test_l5_on_guidance_only_support_still_runs_after_a_blocker():
    result = verify(claim("가상특례법 제2조", numbers=("14일",), topic="syn_report_deadline"))
    assert at(result, L.CLAIM_SUPPORT) == (O.PASS, V.CLAIM_SUPPORTED)
    detail = result.layer(L.CLAIM_SUPPORT).detail
    assert "guidance-only" in detail and "source_identity" in detail
    assert result.overall() is OverallStatus.HUMAN_REVIEW_REQUIRED


def test_l7_still_runs_after_a_blocker():
    result = verify(claim("가상응답장애법 제2조", topic="syn_report_deadline", value="15_days"))
    assert at(result, L.CONFLICT_UNCERTAINTY) == (O.NEEDS_REVIEW, V.CONTRADICTORY_EVIDENCE)
    assert [c.kind for c in conflicts_of(result)] == ["value_mismatch"]   # no candidate, so no date comparison


def test_guidance_only_support_never_fails_while_the_cited_text_may_exist():
    """Invariant §2.1: an unreachable statute might hold the number the guidance lacks."""
    unreachable = verify(claim("가상응답장애법 제2조", numbers=("99일",), topic="syn_report_deadline"))
    assert at(unreachable, L.CLAIM_SUPPORT) == (O.UNAVAILABLE, V.NOT_CHECKED)
    assert "guidance alone does not support" in unreachable.layer(L.CLAIM_SUPPORT).detail
    assert unreachable.overall() is OverallStatus.VERIFICATION_UNAVAILABLE
    absent = verify(claim("가상체류관리기본법 제5조", numbers=("99일",), topic="syn_report_deadline"))
    assert at(absent, L.CLAIM_SUPPORT) == (O.FAIL, V.CLAIM_UNSUPPORTED)   # the cited law authoritatively does not exist


def test_support_from_some_citations_never_fails_while_a_blocked_one_may_hold_the_number():
    ambiguous = verify(claim(f"{ACT} 제5조제1항", "가상특례법 제2조", numbers=("99일",)))
    assert at(ambiguous, L.CLAIM_SUPPORT) == (O.NEEDS_REVIEW, V.NOT_CHECKED)
    assert ambiguous.overall() is OverallStatus.HUMAN_REVIEW_REQUIRED
    absent = verify(claim(f"{ACT} 제5조제1항", f"{ACT} 제99조", numbers=("99일",)))
    assert at(absent, L.CLAIM_SUPPORT) == (O.FAIL, V.CLAIM_UNSUPPORTED)   # 제99조 is authoritatively absent


# ---------------------------------------------------------------------------
# ClaimInput.context_title (같은 법 / 영 / 규칙)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("citation, stable_id", [
    ("제5조제1항", "SYN-ACT-0001"),
    ("같은 법 제5조", "SYN-ACT-0001"),
    ("영 제4조", "SYN-DEC-0001"),
    ("같은 법 시행령 제3조", "SYN-DEC-0001"),
    ("규칙 제73조", "SYN-RUL-0001"),
])
def test_the_claims_context_title_resolves_short_forms(citation, stable_id):
    result = verify(claim(citation, context_title=ACT))
    assert at(result, L.SOURCE_IDENTITY) == (O.PASS, V.SOURCE_VERIFIED)
    assert result.citation_checks[0].identity.stable_id == stable_id
    without = verify(claim(citation))
    assert at(without, L.SOURCE_IDENTITY) == (O.NEEDS_REVIEW, V.SOURCE_AMBIGUOUS)


def test_the_claims_context_title_wins_over_the_call_argument():
    result = verify(claim("제73조", context_title=RULE), context_title=ACT)
    assert result.citation_checks[0].identity.stable_id == "SYN-RUL-0001"
    fallback = verify(claim("제73조"), context_title=RULE)
    assert fallback.citation_checks[0].identity.stable_id == "SYN-RUL-0001"


# ---------------------------------------------------------------------------
# L1 source identity
# ---------------------------------------------------------------------------
def test_l1_a_bare_article_without_a_context_law_is_ambiguous():
    adapter = core_adapter()
    result = verify(claim("제10조"), adapter=adapter)
    assert at(result, L.SOURCE_IDENTITY) == (O.NEEDS_REVIEW, V.SOURCE_AMBIGUOUS)
    assert adapter.total_calls == 0


def test_l1_a_bare_article_uses_the_context_law():
    result = verify(claim("제5조제1항", numbers=("15일",)), context_title=ACT)
    assert at(result, L.SOURCE_IDENTITY) == (O.PASS, V.SOURCE_VERIFIED)
    assert result.citation_checks[0].identity.stable_id == "SYN-ACT-0001"


def test_l1_a_failed_title_lookup_is_unavailable():
    result = verify(claim("가상응답장애법 제2조"))
    assert at(result, L.SOURCE_IDENTITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)


@pytest.mark.parametrize("title", [ACT, "가상외국인체류법", "가상체류법", "가상 체류관리법"])
def test_l1_one_exact_match_on_official_former_or_short_title_passes(title):
    result = verify(claim(f"{title} 제5조"))
    assert at(result, L.SOURCE_IDENTITY) == (O.PASS, V.SOURCE_VERIFIED)
    assert result.citation_checks[0].citation.resolved_stable_id == "SYN-ACT-0001"


def test_l1_several_exact_matches_are_ambiguous_not_a_choice():
    result = verify(claim("가상특례법 제2조"))   # short title of SYN-ACT-0003 and SYN-ACT-0007
    assert at(result, L.SOURCE_IDENTITY) == (O.NEEDS_REVIEW, V.SOURCE_AMBIGUOUS)
    assert result.citation_checks[0].identity is None


def test_l1_no_exact_match_in_a_complete_index_is_source_not_found_with_near_matches_in_detail():
    adapter = core_adapter()
    result = verify(claim("가상체류관리 제5조"), adapter=adapter)
    outcome, code = at(result, L.SOURCE_IDENTITY)
    assert (outcome, code) == (O.FAIL, V.SOURCE_NOT_FOUND)
    assert "가상체류관리법 (SYN-ACT-0001)" in result.layer(L.SOURCE_IDENTITY).detail
    assert result.citation_checks[0].identity is None
    assert adapter.call_counts["list_versions"] == 0   # the near match is not used


def test_l1_no_exact_match_in_a_partial_index_is_historical_lookup_required():
    def current_titles_only(bundle):
        bundle["title_index_coverage"] = "partial"
    result = verify(claim("가상외국인체류법 제5조"), adapter=core_adapter(current_titles_only))
    assert at(result, L.SOURCE_IDENTITY) == (O.UNAVAILABLE, V.HISTORICAL_LOOKUP_REQUIRED)
    assert not ABSENCE & set(result.codes())


class FuzzyTitleAdapter(FixtureAdapter):
    """A title search that returns similar rows (FOUND) instead of an empty answer, like a fuzzy upstream search."""

    def resolve_title(self, title, *, as_of=None):
        lookup, found = super().resolve_title(title, as_of=as_of)
        if found or lookup.status is not LookupStatus.NOT_FOUND:
            return lookup, found
        key = compact(title)
        similar = [i for i in self.identities if key[:4] and key[:4] in compact(i.official_title)]
        if not similar:
            return lookup, found
        return LookupResult(LookupStatus.FOUND, lookup.coverage, detail="fuzzy search rows", calls=1), similar


def fuzzy_adapter(mutate=None) -> FuzzyTitleAdapter:
    return FuzzyTitleAdapter(mutated_core(mutate))


def test_l1_rows_without_an_exact_match_are_ambiguous_not_absent():
    """Spec 07 §3 L1 (decided 2026-10-20): FOUND rows, none exact → needs_review / source_ambiguous."""
    adapter = fuzzy_adapter()
    result = verify(claim("가상체류관리 제5조", quoted_text=QUOTE_2026), adapter=adapter)
    assert at(result, L.SOURCE_IDENTITY) == (O.NEEDS_REVIEW, V.SOURCE_AMBIGUOUS)
    detail = result.layer(L.SOURCE_IDENTITY).detail
    assert "가상체류관리법 (SYN-ACT-0001)" in detail and "not used" in detail   # near matches named ...
    assert result.citation_checks[0].identity is None                          # ... never substituted
    assert adapter.call_counts["list_versions"] == 0
    assert V.SOURCE_NOT_FOUND.value not in result.codes()
    assert result.overall() is OverallStatus.HUMAN_REVIEW_REQUIRED


def test_l1_only_an_empty_complete_answer_is_source_not_found():
    result = verify(claim("가상무관련법 제5조"), adapter=fuzzy_adapter())   # the fuzzy search returns no rows either
    assert at(result, L.SOURCE_IDENTITY) == (O.FAIL, V.SOURCE_NOT_FOUND)


def test_l1_a_found_answer_without_rows_is_not_an_authoritative_absence():
    """§2.1 reserves source_not_found for NOT_FOUND with complete coverage; FOUND with no rows is contradictory."""
    class FoundNothing(FixtureAdapter):
        def resolve_title(self, title, *, as_of=None):
            return LookupResult(LookupStatus.FOUND, Coverage.COMPLETE, calls=1), []
    result = verify(claim(f"{ACT} 제5조"), adapter=FoundNothing(load_core()))
    assert at(result, L.SOURCE_IDENTITY) == (O.NEEDS_REVIEW, V.SOURCE_AMBIGUOUS)
    assert "no rows" in result.layer(L.SOURCE_IDENTITY).detail
    assert not ABSENCE & set(result.codes())


def test_l1_rows_without_an_exact_match_from_a_partial_index_are_a_historical_lookup():
    def current_titles_only(bundle):
        bundle["title_index_coverage"] = "partial"
    result = verify(claim("가상체류관리 제5조"), adapter=fuzzy_adapter(current_titles_only))
    assert at(result, L.SOURCE_IDENTITY) == (O.UNAVAILABLE, V.HISTORICAL_LOOKUP_REQUIRED)
    assert "가상체류관리법 (SYN-ACT-0001)" in result.layer(L.SOURCE_IDENTITY).detail


def test_l1_a_law_repealed_on_the_anchor_date_fails_as_repealed():
    result = verify(claim("가상출국관리법 제3조"))
    assert at(result, L.SOURCE_IDENTITY) == (O.FAIL, V.SOURCE_REPEALED)


def test_l1_the_same_law_before_its_repeal_is_verified():
    result = verify(claim("가상출국관리법 제3조", numbers=("7일",)), **conduct(D(2020, 1, 1)))
    assert at(result, L.SOURCE_IDENTITY) == (O.PASS, V.SOURCE_VERIFIED)
    assert at(result, L.VERSION_IDENTITY) == (O.PASS, V.VERSION_VERIFIED)


# ---------------------------------------------------------------------------
# L2 version identity
# ---------------------------------------------------------------------------
def test_l2_a_failed_version_history_is_unavailable():
    result = verify(claim("가상이력장애법 제2조"))
    assert at(result, L.VERSION_IDENTITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)


def test_l2_an_unknown_anchor_date_needs_context_and_never_falls_back_to_current_law():
    adapter = core_adapter()
    result = verify(claim(f"{ACT} 제5조"), adapter=adapter, anchor=AnchorKind.DECISION_DATE)
    assert at(result, L.VERSION_IDENTITY) == (O.NEEDS_REVIEW, V.INSUFFICIENT_CONTEXT)
    assert result.citation_checks[0].candidate is None
    assert adapter.call_counts["get_provision"] == 0


def test_l2_an_anchor_before_the_loaded_history_is_version_history_incomplete():
    result = verify(claim(f"{ACT} 제5조"), **conduct(D(2010, 1, 1)))
    assert at(result, L.VERSION_IDENTITY) == (O.UNAVAILABLE, V.VERSION_HISTORY_INCOMPLETE)
    assert not ABSENCE & set(result.codes())


def test_l2_anchors_that_select_different_versions_need_review():
    dates = RelevantDates(question_date=Q, conduct_date=D(2025, 1, 1), decision_date=Q)
    result = verify(claim(f"{ACT} 제5조"), dates=dates, anchor=AnchorKind.CONDUCT_DATE,
                    secondary_anchors=(AnchorKind.DECISION_DATE,))
    assert at(result, L.VERSION_IDENTITY) == (O.NEEDS_REVIEW, V.HUMAN_REVIEW_REQUIRED)


def test_l2_a_quotation_from_the_candidate_passes():
    result = verify(claim(f"{ACT} 제5조제1항", quoted_text=QUOTE_2026))
    assert at(result, L.VERSION_IDENTITY) == (O.PASS, V.VERSION_VERIFIED)
    assert result.citation_checks[0].attributed_version.key == ("SYN-A1-1003", "2026-10-02")


def test_l2_nothing_attributable_passes_on_the_candidate():
    result = verify(claim(f"{ACT} 제5조제1항"))
    assert at(result, L.VERSION_IDENTITY) == (O.PASS, V.VERSION_VERIFIED)


def test_l2_text_effective_after_the_anchor_and_the_question_date_is_not_yet_effective():
    """Scenario E: the 2027-09-16 text of 제73조 shares its 일련번호 with the version in force."""
    result = verify(claim(f"{RULE} 제73조", quoted_text=RULE_73_2027))
    assert at(result, L.VERSION_IDENTITY) == (O.FAIL, V.FUTURE_NOT_YET_EFFECTIVE)
    check = result.citation_checks[0]
    assert check.candidate.key == ("SYN-R1-3002", "2026-09-15")
    assert check.attributed_version.key == ("SYN-R1-3002", "2027-09-16")


def test_l2_text_effective_after_the_anchor_but_by_the_question_date_is_the_wrong_version():
    """Scenario D: a later amendment applied to a past event."""
    result = verify(claim(f"{ACT} 제5조제1항", quoted_text=QUOTE_2026), **conduct(D(2025, 5, 1)))
    assert at(result, L.VERSION_IDENTITY) == (O.FAIL, V.WRONG_VERSION)


def test_l2_text_older_than_the_candidate_is_outdated():
    result = verify(claim(f"{ACT} 제5조제1항", quoted_text=QUOTE_2024))
    assert at(result, L.VERSION_IDENTITY) == (O.FAIL, V.SOURCE_OUTDATED)


def test_l2_the_pending_version_is_also_detected_when_quoted():
    result = verify(claim(f"{ACT} 제5조제1항", quoted_text=QUOTE_2027))
    assert at(result, L.VERSION_IDENTITY) == (O.FAIL, V.FUTURE_NOT_YET_EFFECTIVE)


def test_l2_an_asserted_version_key_decides_attribution():
    result = verify(claim(f"{ACT} 제5조", asserted_version_key=("SYN-A1-1002", "2024-03-01")))
    assert at(result, L.VERSION_IDENTITY) == (O.FAIL, V.SOURCE_OUTDATED)
    same = verify(claim(f"{ACT} 제5조", asserted_version_key=("SYN-A1-1003", "2026-10-02")))
    assert at(same, L.VERSION_IDENTITY) == (O.PASS, V.VERSION_VERIFIED)


def test_l2_a_pending_change_to_the_cited_provision_still_passes_and_is_disclosed():
    result = verify(claim(f"{ACT} 제5조제1항", quoted_text=QUOTE_2026))
    assert at(result, L.VERSION_IDENTITY) == (O.PASS, V.VERSION_VERIFIED)
    detail = result.layer(L.VERSION_IDENTITY).detail
    assert "SYN-A1-1004" in detail and "2027-06-01" in detail


def test_l2_a_partial_version_history_cannot_establish_the_candidate():
    """Spec 07 §3 L2 (decided 2026-10-20): partial history coverage is unavailable / version_history_incomplete."""
    result = verify(claim("가상이력미확보법 제2조", numbers=("90일",)))
    assert at(result, L.VERSION_IDENTITY) == (O.UNAVAILABLE, V.VERSION_HISTORY_INCOMPLETE)
    assert at(result, L.CITATION_IDENTITY) == (O.PASS, V.CITATION_VERIFIED)   # a candidate exists: L3 still runs on it
    assert result.overall() is OverallStatus.VERIFICATION_UNAVAILABLE


def test_l2_partial_coverage_wins_over_a_quotation_from_the_candidate():
    def partial_history(bundle):
        bundle["history_coverage"]["SYN-ACT-0001"] = "partial"
    item = claim(f"{ACT} 제5조제1항", quoted_text=QUOTE_2026)
    assert at(verify(item), L.VERSION_IDENTITY) == (O.PASS, V.VERSION_VERIFIED)
    result = verify(item, adapter=core_adapter(partial_history))
    assert at(result, L.VERSION_IDENTITY) == (O.UNAVAILABLE, V.VERSION_HISTORY_INCOMPLETE)
    assert "partial" in result.layer(L.VERSION_IDENTITY).detail
    assert not ABSENCE & set(result.codes())


# ---------------------------------------------------------------------------
# L3 citation identity
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("citation", [f"{ACT} 제8조", f"{ACT} 제9조의2"])   # malformed XML, HTTP 429
def test_l3_a_failed_provision_lookup_is_unavailable(citation):
    result = verify(claim(citation))
    assert at(result, L.CITATION_IDENTITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)


def test_l3_an_article_absent_from_a_completely_parsed_version_is_not_found():
    result = verify(claim(f"{ACT} 제99조"))
    assert at(result, L.CITATION_IDENTITY) == (O.FAIL, V.CITATION_NOT_FOUND)


def test_l3_detail_names_another_version_that_holds_the_article():
    result = verify(claim(f"{ACT} 제11조"))   # in the 2024 version only
    assert at(result, L.CITATION_IDENTITY) == (O.FAIL, V.CITATION_NOT_FOUND)
    assert "SYN-A1-1002" in result.layer(L.CITATION_IDENTITY).detail


@pytest.mark.parametrize("citation", [
    f"{ACT} 제5조제3항",            # no 제3항
    f"{ACT} 제5조제2항제3호",       # no 제3호
    f"{ACT} 제5조제2항제1호가목",   # the 2026 version has no 가목
])
def test_l3_an_absent_paragraph_item_or_subitem_is_not_found(citation):
    result = verify(claim(citation))
    assert at(result, L.CITATION_IDENTITY) == (O.FAIL, V.CITATION_NOT_FOUND)


def test_l3_a_subitem_present_in_the_candidate_passes():
    result = verify(claim(f"{ACT} 제5조제2항제1호가목"), **conduct(D(2025, 1, 1)))
    assert at(result, L.CITATION_IDENTITY) == (O.PASS, V.CITATION_VERIFIED)


@pytest.mark.parametrize("citation", [f"{ACT} 제5조", f"{ACT} 제6조의2", f"{RULE} 별표 1", f"{RULE} [별표 1]"])
def test_l3_a_present_provision_passes(citation):
    result = verify(claim(citation))
    assert at(result, L.CITATION_IDENTITY) == (O.PASS, V.CITATION_VERIFIED)


def test_l3_heading_units_are_never_a_citation():
    assert at(verify(claim(f"{ACT} 제9조")), L.CITATION_IDENTITY) == (O.FAIL, V.CITATION_NOT_FOUND)
    first = verify(claim(f"{ACT} 제1조(목적)"))
    assert at(first, L.CITATION_IDENTITY) == (O.PASS, V.CITATION_VERIFIED)
    assert at(first, L.TEXT_CORRESPONDENCE) == (O.PASS, V.TEXT_MATCH_VERIFIED)


def test_l3_a_missing_article_of_a_partly_parsed_version_is_unavailable_not_absent():
    result = verify(claim("가상체류지원특례법 제3조"))
    assert at(result, L.CITATION_IDENTITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)
    assert not ABSENCE & set(result.codes())


def _structure_incomplete(bundle):
    for record in bundle["provisions"]:
        record.pop("structure_complete", None)   # the default: not marked complete


@pytest.mark.parametrize("citation", [
    f"{ACT} 제5조제3항",
    f"{ACT} 제5조제2항제3호",
    f"{ACT} 제5조제2항제1호가목",
])
def test_l3_a_missing_sub_unit_is_unavailable_unless_the_structure_is_complete(citation):
    """Spec 07 §3 L3 (decided 2026-10-20): citation_not_found only when ProvisionText.structure_complete."""
    assert at(verify(claim(citation)), L.CITATION_IDENTITY) == (O.FAIL, V.CITATION_NOT_FOUND)   # marked complete
    adapter = core_adapter(_structure_incomplete)
    result = verify(claim(citation), adapter=adapter)
    assert result.citation_checks[0].candidate_provision.structure_complete is False
    assert at(result, L.CITATION_IDENTITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)
    assert "not marked complete" in result.layer(L.CITATION_IDENTITY).detail
    assert not ABSENCE & set(result.codes())


def test_l3_a_present_sub_unit_passes_whatever_the_structure_flag():
    result = verify(claim(f"{ACT} 제5조제2항제2호"), adapter=core_adapter(_structure_incomplete))
    assert at(result, L.CITATION_IDENTITY) == (O.PASS, V.CITATION_VERIFIED)


def test_l3_checks_the_candidate_version_not_the_attributed_one():
    """제11조 exists in the 2024 text only. The quotation is attributed to it (L2 fails), but L3 reads C (2026)."""
    result = verify(claim(f"{ACT} 제11조", quoted_text="가상 이전 절차에 관한 것이다"))
    check = result.citation_checks[0]
    assert check.candidate.key == ("SYN-A1-1003", "2026-10-02")
    assert check.attributed_version.key == ("SYN-A1-1002", "2024-03-01")
    assert at(result, L.VERSION_IDENTITY) == (O.FAIL, V.SOURCE_OUTDATED)
    assert at(result, L.CITATION_IDENTITY) == (O.FAIL, V.CITATION_NOT_FOUND)
    assert "SYN-A1-1002" in result.layer(L.CITATION_IDENTITY).detail   # the renumbering hint


# ---------------------------------------------------------------------------
# L4 text correspondence
# ---------------------------------------------------------------------------
def test_l4_without_heading_or_quotation_is_not_applicable():
    assert at(verify(claim(f"{ACT} 제5조")), L.TEXT_CORRESPONDENCE) == (O.NOT_APPLICABLE, V.NOT_CHECKED)


@pytest.mark.parametrize("heading", ["수수료의 면제", "수수료 납부방법"])
def test_l4_a_claimed_heading_that_differs_fails_with_no_similarity_threshold(heading):
    result = verify(claim(f"{RULE} 제73조({heading})"))
    assert at(result, L.TEXT_CORRESPONDENCE) == (O.FAIL, V.TEXT_MISMATCH)


def test_l4_a_claimed_heading_equal_after_compact_passes():
    result = verify(claim(f"{RULE} 제73조(수수료의납부방법)"))
    assert at(result, L.TEXT_CORRESPONDENCE) == (O.PASS, V.TEXT_MATCH_VERIFIED)


def test_l4_a_quotation_in_no_version_fails():
    """Scenario C: the right article, the wrong content."""
    result = verify(claim(f"{ACT} 제5조제1항", quoted_text="변경한 날부터 60일 이내에"))
    assert at(result, L.TEXT_CORRESPONDENCE) == (O.FAIL, V.TEXT_MISMATCH)
    assert at(result, L.VERSION_IDENTITY) == (O.PASS, V.VERSION_VERIFIED)


def test_l4_a_matching_quotation_passes_after_compact():
    result = verify(claim(f"{ACT} 제5조제1항", quoted_text="변경한 날부터  15일이내에"))
    assert at(result, L.TEXT_CORRESPONDENCE) == (O.PASS, V.TEXT_MATCH_VERIFIED)


def test_l4_the_quotation_is_compared_with_the_attributed_version_text():
    result = verify(claim(f"{ACT} 제5조", quoted_text=QUOTE_2024, asserted_version_key=("SYN-A1-1003", "2026-10-02")))
    assert at(result, L.TEXT_CORRESPONDENCE) == (O.FAIL, V.TEXT_MISMATCH)


# ---------------------------------------------------------------------------
# L5 claim support
# ---------------------------------------------------------------------------
def test_l5_a_verified_quotation_supports_the_claim():
    result = verify(claim(f"{ACT} 제5조제1항", quoted_text=QUOTE_2026))
    assert at(result, L.CLAIM_SUPPORT) == (O.PASS, V.CLAIM_SUPPORTED)


def test_l5_every_number_in_the_evidence_supports_the_claim():
    result = verify(claim(f"{ACT} 제5조제1항", numbers=("15일",)))
    assert at(result, L.CLAIM_SUPPORT) == (O.PASS, V.CLAIM_SUPPORTED)


def test_l5_some_numbers_missing_is_partial_support():
    result = verify(claim(f"{ACT} 제5조제1항", numbers=("15일", "30일")))
    assert at(result, L.CLAIM_SUPPORT) == (O.NEEDS_REVIEW, V.CLAIM_PARTIALLY_SUPPORTED)


def test_l5_no_asserted_number_in_the_evidence_is_unsupported():
    result = verify(claim(f"{ACT} 제5조제1항", numbers=("14일",)))   # the 2024 figure, applied today
    assert at(result, L.CLAIM_SUPPORT) == (O.FAIL, V.CLAIM_UNSUPPORTED)


def test_l5_without_quotation_or_numbers_a_person_must_judge_support():
    result = verify(claim(f"{ACT} 제5조제1항"))
    assert at(result, L.CLAIM_SUPPORT) == (O.NEEDS_REVIEW, V.HUMAN_REVIEW_REQUIRED)


def test_l5_evidence_that_could_not_be_retrieved_is_unavailable():
    """L5 depends on the provision L3 could not retrieve: it carries L3's outcome with not_checked (decided 2026-10-20)."""
    result = verify(claim(f"{ACT} 제8조", numbers=("1년",)))
    assert at(result, L.CITATION_IDENTITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)
    assert at(result, L.CLAIM_SUPPORT) == (O.UNAVAILABLE, V.NOT_CHECKED)
    assert "citation_identity" in result.layer(L.CLAIM_SUPPORT).detail
    assert result.overall() is OverallStatus.VERIFICATION_UNAVAILABLE


def test_l5_numbers_match_whole_numbers_only():
    assert contains_number("변경한 날부터 14일 이내", "14일")
    assert not contains_number("변경한 날부터 114일 이내", "14일")
    assert not contains_number("1년 140일", "14일") and contains_number("3 년", "3년")


# ---------------------------------------------------------------------------
# L6 applicability
# ---------------------------------------------------------------------------
E7_4 = Scope(status_codes=("E-7",), subcodes=("E-7-4",), procedures=("extension",))


def test_l6_a_subcode_claim_on_parent_only_evidence_is_unproven():
    """Scenario I: a rule stated for E-7 does not establish it for E-7-4."""
    result = verify(claim(f"{ACT} 제6조", numbers=("90일",), scope=E7_4))
    assert at(result, L.APPLICABILITY) == (O.NEEDS_REVIEW, V.SUBCODE_APPLICABILITY_UNPROVEN)


def test_l6_evidence_that_says_every_subcode_establishes_the_subcode():
    scope = Scope(status_codes=("D-2",), subcodes=("D-2-1",), procedures=("status_change",))
    result = verify(claim(f"{ACT} 제6조의2", numbers=("3년",), scope=scope))
    assert at(result, L.APPLICABILITY) == (O.PASS, V.APPLICABILITY_ESTABLISHED)


def test_l6_a_subcode_missing_from_the_listed_subcodes_fails():
    result = verify(claim(f"{RULE} 별표 1", scope=E7_4))
    assert at(result, L.APPLICABILITY) == (O.FAIL, V.SUBCODE_APPLICABILITY_UNPROVEN)


def test_l6_a_listed_special_variant_is_not_flattened_into_its_parent():
    special = Scope(status_codes=("E-7",), subcodes=("E-7-T",), procedures=("extension",))
    result = verify(claim(f"{RULE} 별표 1", quoted_text="가상 고용계약서", scope=special))
    assert result.layer(L.APPLICABILITY).code is not V.SUBCODE_APPLICABILITY_UNPROVEN
    parent_claim = Scope(status_codes=("E-7",), procedures=("extension",))
    result = verify(claim(f"{RULE} 별표 1", scope=parent_claim))   # subcode rule as a parent rule
    assert at(result, L.APPLICABILITY) == (O.FAIL, V.SUBCODE_APPLICABILITY_UNPROVEN)
    assert parent_code("E-7-T") == "E-7" and parent_code("E-7") == "E-7" and parent_code("G-1-5") == "G-1"


def test_l6_visa_evidence_for_a_stay_procedure_is_a_scope_mismatch():
    result = verify(claim(f"{DECREE} 제3조", scope=Scope(procedures=("extension",))))
    assert at(result, L.APPLICABILITY) == (O.FAIL, V.PROCEDURE_SCOPE_MISMATCH)


def test_l6_disjoint_procedures_in_the_same_scope_are_a_mismatch():
    result = verify(claim(f"{DECREE} 제4조", scope=Scope(procedures=("status_change",))))
    assert at(result, L.APPLICABILITY) == (O.FAIL, V.PROCEDURE_SCOPE_MISMATCH)


def test_l6_a_failed_addenda_lookup_is_unavailable():
    result = verify(claim("가상부칙장애법 제2조", numbers=("10일",)))
    assert at(result, L.APPLICABILITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)


def test_l6_a_transitional_clause_naming_the_cited_article_is_unresolved():
    """Scenario F: 부칙 제2조 of the 2026 version keeps the old 제5조 for filings before it."""
    result = verify(claim(f"{ACT} 제5조제1항", numbers=("15일",)))
    assert at(result, L.APPLICABILITY) == (O.NEEDS_REVIEW, V.TRANSITIONAL_RULE_UNRESOLVED)


def test_l6_an_application_clause_naming_no_article_reaches_every_filing():
    result = verify(claim(f"{RULE} 제2조"))
    assert at(result, L.APPLICABILITY) == (O.NEEDS_REVIEW, V.TRANSITIONAL_RULE_UNRESOLVED)


def test_l6_a_transitional_clause_naming_another_article_does_not_reach_this_one():
    result = verify(claim(f"{ACT} 제6조의2", numbers=("3년",)))
    assert result.layer(L.APPLICABILITY).code is not V.TRANSITIONAL_RULE_UNRESOLVED


def test_l6_a_missing_date_fact_is_insufficient_context():
    result = verify(claim(f"{ACT} 제5조"), anchor=AnchorKind.FILING_DATE)
    assert at(result, L.APPLICABILITY) == (O.NEEDS_REVIEW, V.INSUFFICIENT_CONTEXT)


def test_l6_without_findings_a_given_scope_is_established_and_no_scope_is_not_applicable():
    scope = Scope(status_codes=("D-2",), procedures=("status_change",))
    assert at(verify(claim(f"{ACT} 제6조의2", scope=scope)), L.APPLICABILITY) == (O.PASS, V.APPLICABILITY_ESTABLISHED)
    assert at(verify(claim(f"{ACT} 제6조의2")), L.APPLICABILITY) == (O.NOT_APPLICABLE, V.NOT_CHECKED)


class AddendaAdapter(FixtureAdapter):
    """Overrides what get_addenda reports, so one condition of the L6 부칙 rule can be tested at a time."""

    def __init__(self, bundle, *, status=None, coverage=None):
        super().__init__(bundle)
        self._status, self._coverage = status, coverage

    def get_addenda(self, stable_id, version_key):
        lookup, addenda = super().get_addenda(stable_id, version_key)
        status = self._status or lookup.status
        coverage = self._coverage or lookup.coverage
        return LookupResult(status, coverage, detail=lookup.detail, calls=1), (addenda if status is LookupStatus.FOUND else [])


def test_l6_a_부칙_that_was_not_returned_is_unavailable():
    """Spec 07 §3 L6 (decided 2026-10-20): get_addenda NOT_FOUND → unavailable (every version has a 부칙)."""
    adapter = AddendaAdapter(load_core(), status=LookupStatus.NOT_FOUND, coverage=Coverage.COMPLETE)
    result = verify(claim(f"{ACT} 제6조의2", numbers=("3년",)), adapter=adapter)
    assert at(result, L.APPLICABILITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)
    assert "no 부칙 was returned" in result.layer(L.APPLICABILITY).detail
    # In the bundle: the decree's 2020 version records no 부칙 although it was read.
    scope_free = verify(claim(f"{DECREE} 제4조"))
    assert at(scope_free, L.APPLICABILITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)


def test_l6_a_partial_부칙_lookup_is_unavailable():
    adapter = AddendaAdapter(load_core(), coverage=Coverage.PARTIAL)
    result = verify(claim(f"{ACT} 제6조의2", numbers=("3년",)), adapter=adapter)
    assert at(result, L.APPLICABILITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)
    assert "partial" in result.layer(L.APPLICABILITY).detail


def test_l6_an_unknown_has_transitional_provisions_is_unavailable_even_if_addenda_came_back():
    def unknown(bundle):
        for version in bundle["versions"]:
            if version["version_id"] == "SYN-A1-1003":
                version["has_transitional_provisions"] = None
    adapter = AddendaAdapter(mutated_core(unknown), status=LookupStatus.FOUND, coverage=Coverage.COMPLETE)
    result = verify(claim(f"{ACT} 제6조의2", numbers=("3년",)), adapter=adapter)
    assert at(result, L.APPLICABILITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)
    assert "has_transitional_provisions is unknown" in result.layer(L.APPLICABILITY).detail


def test_l6_a_read_complete_부칙_without_a_clause_for_the_article_passes():
    result = verify(claim(f"{ACT} 제6조의2", numbers=("3년",), scope=Scope(status_codes=("D-2",), procedures=("status_change",))))
    assert at(result, L.APPLICABILITY) == (O.PASS, V.APPLICABILITY_ESTABLISHED)


def test_l6_an_unread_부칙_is_unavailable_not_absent():
    """Spec 07 §3 L6 (decided 2026-10-20): has_transitional_provisions None (부칙 not read) → unavailable."""
    def unread(bundle):
        for version in bundle["versions"]:
            if version["version_id"] == "SYN-A1-1003":
                version["has_transitional_provisions"] = None
        bundle["addenda"] = [a for a in bundle["addenda"] if a["version_id"] != "SYN-A1-1003"]
    result = verify(claim(f"{ACT} 제6조의2", numbers=("3년",)), adapter=core_adapter(unread))
    assert at(result, L.APPLICABILITY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)


# ---------------------------------------------------------------------------
# L7 conflict and uncertainty
# ---------------------------------------------------------------------------
def test_l7_a_failed_guidance_lookup_is_unavailable():
    result = verify(claim(f"{ACT} 제5조제1항", numbers=("15일",), topic="syn_guidance_outage"))
    assert at(result, L.CONFLICT_UNCERTAINTY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)


def test_l7_a_guidance_value_that_differs_is_contradictory_and_recorded():
    result = verify(claim(f"{RULE} 제73조", quoted_text=RULE_73_NOW, topic="syn_fee_payment_method",
                          value="cash_or_electronic"))
    assert at(result, L.CONFLICT_UNCERTAINTY) == (O.NEEDS_REVIEW, V.CONTRADICTORY_EVIDENCE)
    [record] = conflicts_of(result)
    assert record.kind == "value_mismatch" and record.requires_review
    assert "synthetic_core:guidance:fee-method-2026-09" in record.evidence_ids


def test_l7_guidance_older_than_the_candidate_predates_the_law_change():
    """Scenario J: a manual edition (2026-09-18) from before the version in force (2026-10-02)."""
    result = verify(claim(f"{ACT} 제5조제1항", numbers=("15일",), topic="syn_report_deadline"))
    assert at(result, L.CONFLICT_UNCERTAINTY) == (O.NEEDS_REVIEW, V.MANUAL_PREDATES_LAW_CHANGE)
    assert [c.kind for c in conflicts_of(result)] == ["manual_predates_law_change"]


def test_l7_the_same_manual_does_not_predate_the_version_in_force_for_a_deferred_provision():
    # 제7조 of the 2026 version takes effect 2027-03-01, so on Q the 2024 text applies.
    result = verify(claim(f"{ACT} 제7조", topic="syn_fee_payment_method", value="cash_only"))
    assert result.citation_checks[0].candidate.key == ("SYN-A1-1002", "2024-03-01")
    assert at(result, L.CONFLICT_UNCERTAINTY) == (O.PASS, V.NO_CONFLICT_DETECTED)


def test_l7_otherwise_no_conflict_is_detected():
    result = verify(claim(f"{ACT} 제6조", numbers=("90일",), topic="syn_e7_extension_documents"))
    assert at(result, L.CONFLICT_UNCERTAINTY) == (O.PASS, V.NO_CONFLICT_DETECTED)
    assert conflicts_of(result) == ()


def test_l7_without_a_topic_is_not_applicable_and_claims_no_absence_of_conflict():
    """Spec 07 §3 L7 (decided 2026-10-20): no topic → not_applicable / not_checked."""
    adapter = core_adapter()
    result = verify(claim(f"{ACT} 제6조의2", numbers=("3년",)), adapter=adapter)
    assert at(result, L.CONFLICT_UNCERTAINTY) == (O.NOT_APPLICABLE, V.NOT_CHECKED)
    assert V.NO_CONFLICT_DETECTED.value not in result.codes()
    assert adapter.call_counts["guidance"] == 0
    assert result.overall() is OverallStatus.VERIFIED   # not_applicable does not block a verified claim


def test_l7_compares_the_edition_with_the_latest_version_that_changed_the_provision():
    """제1조 was last changed by the 2024 version; the 2026 version in force did not touch it."""
    result = verify(claim(f"{ACT} 제1조", topic="syn_report_deadline"))
    assert result.citation_checks[0].candidate.key == ("SYN-A1-1003", "2026-10-02")
    assert at(result, L.CONFLICT_UNCERTAINTY) == (O.PASS, V.NO_CONFLICT_DETECTED)   # 2026-09-18 is after 2024-03-01
    assert conflicts_of(result) == ()


def test_l7_unknown_changed_provisions_fall_back_to_the_candidates_date():
    def unknown_changes(bundle):
        for version in bundle["versions"]:
            if version["version_id"] == "SYN-A1-1003":
                version["changed_provisions"] = None
    result = verify(claim(f"{ACT} 제1조", topic="syn_report_deadline"), adapter=core_adapter(unknown_changes))
    assert at(result, L.CONFLICT_UNCERTAINTY) == (O.NEEDS_REVIEW, V.MANUAL_PREDATES_LAW_CHANGE)
    [record] = conflicts_of(result)
    assert record.kind == "manual_predates_law_change" and "2026-10-02" in record.detail


def test_l7_a_value_mismatch_and_a_predating_edition_report_contradictory_evidence_and_both_records():
    """Scenario J shape: both apply; the code is contradictory_evidence whatever order the items come in."""
    def two_items(bundle):
        bundle["guidance"] = [g for g in bundle["guidance"] if g["topic"] != "syn_report_deadline"] + [
            {"evidence_id": "synthetic_core:test:old-edition", "family": "immigration_manual",
             "topic": "syn_report_deadline", "text": "가상 매뉴얼(구판): 신고 기한 안내", "value": None,
             "edition_date": "2026-09-01", "review_state": "approved", "scope": None},
            {"evidence_id": "synthetic_core:test:other-value", "family": "public_guidance",
             "topic": "syn_report_deadline", "text": "가상 안내: 30일 이내", "value": "30_days",
             "edition_date": "2026-10-10", "review_state": "unreviewed", "scope": None},
        ]
    result = verify(claim(f"{ACT} 제5조제1항", numbers=("15일",), topic="syn_report_deadline", value="15_days"),
                    adapter=core_adapter(two_items))
    assert at(result, L.CONFLICT_UNCERTAINTY) == (O.NEEDS_REVIEW, V.CONTRADICTORY_EVIDENCE)
    kinds = sorted(c.kind for c in conflicts_of(result))
    assert kinds == ["manual_predates_law_change", "value_mismatch"]
    core = verify(claim(f"{ACT} 제5조제1항", numbers=("15일",), topic="syn_report_deadline", value="15_days"))
    assert at(core, L.CONFLICT_UNCERTAINTY) == (O.NEEDS_REVIEW, V.CONTRADICTORY_EVIDENCE)
    assert sorted(c.kind for c in conflicts_of(core)) == ["manual_predates_law_change", "value_mismatch"]


def test_l7_an_empty_answer_from_a_partial_guidance_lookup_is_unavailable():
    class PartialGuidance(FixtureAdapter):
        def guidance(self, topic):
            lookup, items = super().guidance(topic)
            return LookupResult(lookup.status, Coverage.PARTIAL, calls=1), items
    result = verify(claim(f"{ACT} 제6조", numbers=("90일",), topic="syn_no_such_topic"),
                    adapter=PartialGuidance(load_core()))
    assert at(result, L.CONFLICT_UNCERTAINTY) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)


# ---------------------------------------------------------------------------
# §2 invariants
# ---------------------------------------------------------------------------
SCRIPTED_FAULTS = [
    ("html", claim("가상응답장애법 제2조"), L.SOURCE_IDENTITY),
    ("empty", claim("가상빈응답법 제2조"), L.SOURCE_IDENTITY),
    ("official_error", claim("가상인증장애법 제2조"), L.SOURCE_IDENTITY),
    ("malformed_json", claim("가상이력장애법 제2조"), L.VERSION_IDENTITY),
    ("malformed_xml", claim(f"{ACT} 제8조"), L.CITATION_IDENTITY),
    ("http_429", claim(f"{ACT} 제9조의2"), L.CITATION_IDENTITY),
    ("timeout", claim("가상부칙장애법 제2조", numbers=("10일",)), L.APPLICABILITY),
    ("http_500", claim(topic="syn_guidance_outage", numbers=("14일",)), L.CONFLICT_UNCERTAINTY),
]


@pytest.mark.parametrize("kind, item, layer", SCRIPTED_FAULTS, ids=[k for k, _, _ in SCRIPTED_FAULTS])
def test_invariant_1_every_scripted_fault_is_unavailable_never_absence(kind, item, layer):
    result = verify(item)
    assert at(result, layer) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE), kind
    assert not ABSENCE & set(result.codes())
    assert result.overall() is OverallStatus.VERIFICATION_UNAVAILABLE


FAILURES = [s for s in LookupStatus if s.is_failure]
FAULTED_CALLS = [
    ("resolve_title", {"title": ACT}, L.SOURCE_IDENTITY),
    ("list_versions", {"stable_id": "SYN-ACT-0001"}, L.VERSION_IDENTITY),
    ("get_provision", {"stable_id": "SYN-ACT-0001"}, L.CITATION_IDENTITY),
    ("get_addenda", {"stable_id": "SYN-ACT-0001"}, L.APPLICABILITY),
]


@pytest.mark.parametrize("status", FAILURES, ids=[s.value for s in FAILURES])
@pytest.mark.parametrize("operation, match, layer", FAULTED_CALLS, ids=[op for op, _, _ in FAULTED_CALLS])
def test_invariant_1_every_failure_status_on_every_lookup_is_unavailable(status, operation, match, layer):
    def fault(bundle):
        bundle["faults"] = [{"operation": operation, "match": match, "status": status.value, "raw_body_kind": None,
                             "detail": "scripted by the test"}]
    item = claim(f"{ACT} 제6조의2", numbers=("3년",))   # verified when nothing fails
    assert verify(item).overall() is OverallStatus.VERIFIED
    result = verify(item, adapter=core_adapter(fault))
    assert at(result, layer) == (O.UNAVAILABLE, V.VERIFICATION_UNAVAILABLE)
    assert not ABSENCE & set(result.codes())
    assert result.overall() is OverallStatus.VERIFICATION_UNAVAILABLE


def test_invariant_2_partial_coverage_is_never_absence():
    def partial_index(bundle):
        bundle["title_index_coverage"] = "partial"
    renamed = verify(claim("가상외국인체류법 제5조"), adapter=core_adapter(partial_index))
    unparsed = verify(claim("가상체류지원특례법 제3조"))
    for result in (renamed, unparsed):
        assert not ABSENCE & set(result.codes())
        assert result.overall() is OverallStatus.VERIFICATION_UNAVAILABLE
    assert at(renamed, L.SOURCE_IDENTITY) == (O.UNAVAILABLE, V.HISTORICAL_LOOKUP_REQUIRED)


@pytest.mark.parametrize("cited, expected_id", [
    ("가상체류관리 제5조", None),                             # prefix of the Act
    ("가상체류관리볍 제5조", None),                           # near spelling
    ("신가상체류관리법 제5조", None),                         # the Act inside a longer title
    (f"{DECREE} 제5조", "SYN-DEC-0001"),                     # the decree is never the Act
    ("가상체류관리특례법 제5조", "SYN-ACT-0003"),             # a longer title is its own law
])
def test_invariant_3_no_substitution_of_a_similar_title(cited, expected_id):
    result = verify(claim(cited))
    check = result.citation_checks[0]
    assert (check.identity.stable_id if check.identity else None) == expected_id
    assert check.citation.resolved_stable_id == expected_id
    assert result.overall() is OverallStatus.FAILED   # not found, or 제5조 is not in that law


def test_invariant_4_a_verified_article_does_not_verify_the_conclusion():
    result = verify(claim(f"{ACT} 제5조제1항", text="체류지 변경 신고는 필요 없다"))
    assert at(result, L.CITATION_IDENTITY) == (O.PASS, V.CITATION_VERIFIED)
    assert at(result, L.CLAIM_SUPPORT) == (O.NEEDS_REVIEW, V.HUMAN_REVIEW_REQUIRED)
    assert result.highest_verified_layer() == 4
    assert result.overall() is not OverallStatus.VERIFIED


def test_invariant_5_instruction_like_source_text_is_flagged_and_changes_nothing():
    item = claim(f"{ACT} 제10조", quoted_text="신고 절차를 안내하여야 한다")
    flagged = verify(item)
    evidence_id = "synthetic_core:SYN-ACT-0001:SYN-A1-1003@2026-10-02:제10조"
    assert flagged.injection_flagged and UNTRUSTED_FLAG in flagged.injection_flags[evidence_id]

    def without_instruction(bundle):
        for record in bundle["provisions"]:
            if record["evidence_id"] == evidence_id:
                record["text"] = record["text"].split(" 이전 지시")[0]
    clean = verify(item, adapter=core_adapter(without_instruction))
    assert not clean.injection_flagged
    assert [(r.outcome, r.code) for r in flagged.layers] == [(r.outcome, r.code) for r in clean.layers]
    assert flagged.to_dict()["injection_flagged"] is True


def test_invariant_5_instruction_like_guidance_is_flagged_too():
    result = verify(claim(topic="syn_injected_page", numbers=("14일",)))
    assert result.injection_flags["synthetic_core:guidance:injected-page"][0] == UNTRUSTED_FLAG
    assert at(result, L.CLAIM_SUPPORT) == (O.PASS, V.CLAIM_SUPPORTED)


def test_invariant_6_conflicts_are_recorded_and_never_settled_by_authority_rank():
    # The statute (authority "statute") and an approved manual disagree; the statute does not win.
    result = verify(claim(f"{ACT} 제5조제1항", numbers=("15일",), topic="syn_report_deadline", value="15_days"))
    kinds = sorted(c.kind for c in conflicts_of(result))
    assert kinds == ["manual_predates_law_change", "value_mismatch"]
    assert all(c.requires_review for c in conflicts_of(result))
    assert at(result, L.CONFLICT_UNCERTAINTY)[0] is O.NEEDS_REVIEW
    assert result.overall() is OverallStatus.HUMAN_REVIEW_REQUIRED
    assert {c["kind"] for c in result.to_dict()["conflicts"]} == set(kinds)


def test_conflicts_of_a_plain_claim_verification_is_empty():
    assert conflicts_of(ClaimVerification("x", ())) == ()


def test_worst_keeps_the_first_of_equally_severe_results():
    first = verify(claim(f"{ACT} 제99조")).layer(L.CITATION_IDENTITY)
    second = verify(claim(f"{ACT} 제98조")).layer(L.CITATION_IDENTITY)
    assert worst([first, second]) is first


def test_the_report_is_json_compatible():
    result = verify(claim(f"{ACT} 제5조제1항", numbers=("15일",), topic="syn_report_deadline", value="15_days"))
    data = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
    assert data["overall"] == "human_review_required" and len(data["layers"]) == 7


def _with_old_versions(count):
    """The Act with ``count`` extra, completely parsed versions before 2020, each with its own 제5조."""
    def mutate(bundle):
        for n in range(count):
            version_id, effective = f"SYN-A1-09{n:02d}", f"{2000 + n}-01-01"
            template = copy.deepcopy(bundle["versions"][0])
            template.update(version_id=version_id, effective_date=effective, promulgation_date=None)
            bundle["versions"].append(template)
            bundle["provisions"].append({
                "evidence_id": f"synthetic_core:test:{version_id}:제5조", "stable_id": "SYN-ACT-0001",
                "version_id": version_id, "effective_date": effective, "provision_key": "제5조",
                "unit_kind": "article", "heading": "가상 체류지 변경의 신고", "text": f"제5조 가상 문언 {n}",
                "paragraphs": {}, "items": {}, "scope": None, "official_url": None, "provenance": "synthetic_fixture",
            })
    return mutate


def test_version_attribution_spends_a_bounded_number_of_lookups():
    adapter = core_adapter(_with_old_versions(12))
    result = verify(claim(f"{ACT} 제5조제1항", quoted_text="어느 판에도 없는 문언"), adapter=adapter)
    assert adapter.call_counts["get_provision"] == 1 + MAX_ATTRIBUTION_LOOKUPS
    assert at(result, L.TEXT_CORRESPONDENCE) == (O.FAIL, V.TEXT_MISMATCH)
    assert f"only {MAX_ATTRIBUTION_LOOKUPS} other versions" in result.layer(L.TEXT_CORRESPONDENCE).detail


def test_the_renumbering_hint_spends_a_bounded_number_of_lookups():
    adapter = core_adapter(_with_old_versions(12))
    result = verify(claim(f"{ACT} 제99조"), adapter=adapter)
    assert adapter.call_counts["get_provision"] == 1 + MAX_RENUMBERING_LOOKUPS
    assert at(result, L.CITATION_IDENTITY) == (O.FAIL, V.CITATION_NOT_FOUND)
    assert "nearest other versions" in result.layer(L.CITATION_IDENTITY).detail


def test_claim_citation_strings_with_leading_words_resolve_through_known_titles():
    result = verify(claim(f"근거: {ACT} 제5조제1항", numbers=("15일",)))
    assert at(result, L.SOURCE_IDENTITY) == (O.PASS, V.SOURCE_VERIFIED)
    unknown = verify(claim("근거: 가상무역법 제5조"))
    assert at(unknown, L.SOURCE_IDENTITY) == (O.FAIL, V.SOURCE_NOT_FOUND)
