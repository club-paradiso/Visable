"""Candidate-version selection: one test per rule of spec 06 §3, plus the shapes of §4."""
from __future__ import annotations

import datetime as dt

import pytest

from waymaker_ai.contracts import (
    AnchorKind,
    Coverage,
    LookupResult,
    LookupStatus,
    RelevantDates,
    SourceVersion,
    TemporalWarning as W,
)
from waymaker_ai.legal.adapters import FixtureAdapter
from waymaker_ai.legal.temporal import (
    deferred_entries,
    effective_for,
    enclosing_keys,
    latest_change_date,
    select_candidate_versions,
)

D = dt.date
FOUND = LookupResult(LookupStatus.FOUND, Coverage.COMPLETE)
Q = AnchorKind.QUESTION_DATE


def v(version_id, effective, *, changed=None, deferred=None, transitional=False, repeal=False):
    return SourceVersion(
        stable_id="SYN-T", version_id=version_id, effective_date=effective, changed_provisions=changed,
        provision_effective_dates=deferred or {}, has_transitional_provisions=transitional, is_repeal=repeal,
    )


HISTORY = [
    v("V1", D(2020, 1, 1)),
    v("V2", D(2024, 3, 1), changed=("제5조",)),
    v("V3", D(2026, 10, 2), changed=("제5조", "제7조"), deferred={"제7조": D(2027, 3, 1)}),
    v("V4", D(2027, 6, 1), changed=("제5조",)),
]


def select(versions=HISTORY, *, history=FOUND, on=None, anchor=Q, provision=None, secondary=(), dates=None,
           question_date=D(2026, 10, 19)):
    dates = dates or RelevantDates(question_date=on or question_date)
    return select_candidate_versions(
        versions, history=history, dates=dates, anchor=anchor, secondary_anchors=secondary,
        provision_key=provision, question_date=question_date,
    )


def test_rule_1_failed_history_gives_no_candidate():
    for status in LookupStatus:
        if not status.is_failure:
            continue
        result = select(history=LookupResult(status, Coverage.PARTIAL))
        assert result.candidates == () and result.warnings == (W.VERSION_HISTORY_UNAVAILABLE,)


@pytest.mark.parametrize("anchor, dates", [
    (None, RelevantDates(question_date=D(2026, 10, 19))),
    (AnchorKind.CONDUCT_DATE, RelevantDates(question_date=D(2026, 10, 19))),
])
def test_rule_2_missing_anchor_never_falls_back_to_current_law(anchor, dates):
    result = select(anchor=anchor, dates=dates)
    assert result.candidates == () and result.warnings == (W.ANCHOR_MISSING,)


def test_rule_3_the_provision_date_is_used_for_selection():
    # 제7조 of V3 is deferred to 2027-03-01, so on 2026-11-01 V2's 제7조 applies.
    assert select(on=D(2026, 11, 1), provision="제7조").candidate_keys() == [["V2", "2024-03-01"]]
    assert select(on=D(2026, 11, 1), provision="제5조").candidate_keys() == [["V3", "2026-10-02"]]


def test_rule_4_latest_effective_on_or_before_the_anchor():
    assert select(on=D(2024, 2, 29)).candidate_keys() == [["V1", "2020-01-01"]]
    assert select(on=D(2024, 3, 1)).candidate_keys() == [["V2", "2024-03-01"]]


def test_rule_4_a_tie_keeps_both_and_warns():
    tied = [v("A", D(2025, 1, 1)), v("B", D(2025, 1, 1))]
    result = select(tied, on=D(2025, 6, 1))
    assert result.candidate_keys() == [["A", "2025-01-01"], ["B", "2025-01-01"]]
    assert W.ANCHORS_SELECT_DIFFERENT_VERSIONS in result.warnings


def test_rule_5_anchor_before_known_history_is_not_absence():
    result = select(on=D(2019, 12, 31))
    assert result.candidates == () and result.warnings == (W.ANCHOR_BEFORE_KNOWN_HISTORY,)
    assert "earliest loaded version (2020-01-01)" in result.detail


def test_rule_6_repeal_in_force_on_the_anchor_gives_no_candidate():
    versions = [v("A", D(2015, 1, 1)), v("R", D(2025, 1, 1), repeal=True)]
    result = select(versions, on=D(2026, 1, 1))
    assert result.candidates == () and result.warnings == (W.SOURCE_REPEALED_BEFORE_ANCHOR,)
    assert select(versions, on=D(2020, 1, 1)).candidate_keys() == [["A", "2015-01-01"]]


def test_rule_7_pending_version_that_changes_the_provision():
    result = select(on=D(2026, 10, 19), provision="제5조")
    assert result.candidate_keys() == [["V3", "2026-10-02"]]
    assert W.FUTURE_VERSION_PENDING in result.warnings
    assert "(V4, 2027-06-01) effective 2027-06-01" in result.detail


def test_rule_7_pending_version_that_does_not_change_the_provision():
    assert W.FUTURE_VERSION_PENDING not in select(on=D(2026, 10, 19), provision="제1조").warnings


def test_rule_7_unknown_changes_or_no_provision_count_as_pending():
    versions = [v("A", D(2020, 1, 1)), v("B", D(2027, 1, 1), changed=None)]
    assert W.FUTURE_VERSION_PENDING in select(versions, provision="제1조").warnings
    versions = [v("A", D(2020, 1, 1)), v("B", D(2027, 1, 1), changed=("제9조",))]
    assert W.FUTURE_VERSION_PENDING in select(versions, provision=None).warnings


def test_rule_8_deferred_provision_inside_the_candidate():
    result = select(on=D(2027, 4, 1), provision="제7조")
    assert result.candidate_keys() == [["V3", "2026-10-02"]]
    assert W.PROVISION_EFFECTIVE_DATE_DIFFERS in result.warnings


def test_rule_8_a_deferred_paragraph_warns_for_its_article():
    versions = [v("A", D(2026, 12, 10), deferred={"제4조제4항": D(2027, 6, 10)})]
    result = select(versions, on=D(2027, 1, 1), provision="제4조")
    assert result.candidate_keys() == [["A", "2026-12-10"]]
    assert W.PROVISION_EFFECTIVE_DATE_DIFFERS in result.warnings
    assert W.PROVISION_EFFECTIVE_DATE_DIFFERS not in select(versions, on=D(2027, 1, 1), provision="제5조").warnings


def test_rule_7_with_no_provision_named_every_later_version_counts():
    """Decided 2026-10-20: changed_provisions is irrelevant when no provision is named."""
    versions = [v("A", D(2020, 1, 1)), v("B", D(2027, 1, 1), changed=("제9조",)), v("C", D(2028, 1, 1), changed=())]
    result = select(versions, provision=None)
    assert W.FUTURE_VERSION_PENDING in result.warnings
    assert "(B, 2027-01-01)" in result.detail and "(C, 2028-01-01)" in result.detail
    assert W.FUTURE_VERSION_PENDING not in select(versions, provision="제1조").warnings


def test_rule_7_changed_provisions_are_compared_at_article_level():
    versions = [v("A", D(2020, 1, 1)), v("B", D(2027, 1, 1), changed=("제4조제4항",))]
    assert W.FUTURE_VERSION_PENDING in select(versions, provision="제4조").warnings
    assert W.FUTURE_VERSION_PENDING in select(versions, provision="제4조제1항").warnings
    assert W.FUTURE_VERSION_PENDING not in select(versions, provision="제4조의2").warnings


def test_rule_8_an_exact_sub_article_key_is_matched_first():
    versions = [v("A", D(2026, 12, 10), deferred={"제4조제4항": D(2027, 6, 10), "제4조": D(2026, 12, 20)})]
    assert deferred_entries(versions[0], "제4조제4항") == {"제4조제4항": D(2027, 6, 10)}
    assert effective_for(versions[0], "제4조제4항") == D(2027, 6, 10)
    assert effective_for(versions[0], "제4조제1항") == D(2026, 12, 20)   # no own entry: its article's


def test_rule_8_a_sub_article_key_without_its_own_entry_takes_its_articles():
    # 제7조 of V3 is deferred to 2027-03-01, so 제7조제1항 is too (rules 3 and 8 read the same entry).
    assert select(on=D(2026, 11, 1), provision="제7조제1항").candidate_keys() == [["V2", "2024-03-01"]]
    later = select(on=D(2027, 4, 1), question_date=D(2027, 4, 1), provision="제7조제1항")
    assert later.candidate_keys() == [["V3", "2026-10-02"]]
    assert W.PROVISION_EFFECTIVE_DATE_DIFFERS in later.warnings and "제7조 2027-03-01" in later.detail


def test_rule_8_an_article_key_matches_its_own_paragraphs_only():
    versions = [v("A", D(2026, 12, 10), deferred={"제4조의2제1항": D(2027, 6, 10)})]
    assert W.PROVISION_EFFECTIVE_DATE_DIFFERS not in select(versions, on=D(2027, 1, 1), provision="제4조").warnings
    assert W.PROVISION_EFFECTIVE_DATE_DIFFERS in select(versions, on=D(2027, 1, 1), provision="제4조의2").warnings
    assert enclosing_keys("제4조제4항제1호가목") == ["제4조제4항제1호", "제4조제4항", "제4조"]
    assert enclosing_keys("제4조") == [] and enclosing_keys("별표1") == []


@pytest.mark.parametrize("transitional, warned", [(None, True), (True, True), (False, False)])
def test_rule_9_unread_or_present_transitional_provisions(transitional, warned):
    versions = [v("A", D(2020, 1, 1), transitional=transitional)]
    assert (W.TRANSITIONAL_PROVISIONS_UNREVIEWED in select(versions).warnings) is warned


def test_rule_9_considers_the_primary_candidate_only():
    """Decided 2026-10-20: a secondary-anchor candidate is reported but adds no transitional warning."""
    dates = RelevantDates(question_date=D(2026, 10, 19), conduct_date=D(2024, 1, 15), decision_date=D(2026, 10, 19))
    versions = [v("OLD", D(2020, 1, 1), transitional=False), v("NEW", D(2026, 10, 2), transitional=None)]
    result = select(versions, dates=dates, anchor=AnchorKind.CONDUCT_DATE, secondary=(AnchorKind.DECISION_DATE,))
    assert result.candidate_keys() == [["OLD", "2020-01-01"], ["NEW", "2026-10-02"]]
    assert W.TRANSITIONAL_PROVISIONS_UNREVIEWED not in result.warnings
    flipped = select(versions, dates=dates, anchor=AnchorKind.DECISION_DATE, secondary=(AnchorKind.CONDUCT_DATE,))
    assert flipped.candidate_keys() == [["NEW", "2026-10-02"], ["OLD", "2020-01-01"]]
    assert W.TRANSITIONAL_PROVISIONS_UNREVIEWED in flipped.warnings


def test_rule_9_a_tie_on_the_primary_anchor_reads_every_tied_candidate():
    tied = [v("A", D(2025, 1, 1), transitional=False), v("B", D(2025, 1, 1), transitional=None)]
    assert W.TRANSITIONAL_PROVISIONS_UNREVIEWED in select(tied, on=D(2025, 6, 1)).warnings


# -- spec 07 §3 L7: the latest version that changed the provision -------------
def test_latest_change_date_walks_back_to_the_version_that_changed_the_article():
    versions = [v("V1", D(2020, 1, 1), changed=("제1조", "제5조")), v("V2", D(2024, 3, 1), changed=("제5조",)),
                v("V3", D(2026, 10, 2), changed=("제6조",))]
    date, basis = latest_change_date(versions, versions[2], "제5조", history=FOUND)
    assert date == D(2024, 3, 1) and "V2" in basis
    assert latest_change_date(versions, versions[2], "제1조", history=FOUND)[0] == D(2020, 1, 1)
    assert latest_change_date(versions, versions[2], "제6조제1항", history=FOUND)[0] == D(2026, 10, 2)


def test_latest_change_date_falls_back_to_the_candidate_when_it_is_not_known():
    candidate = v("V3", D(2026, 10, 2), changed=("제6조",))
    unknown = [v("V1", D(2020, 1, 1), changed=None), v("V2", D(2024, 3, 1), changed=None), candidate]
    assert latest_change_date(unknown, candidate, "제5조", history=FOUND)[0] == D(2026, 10, 2)
    known = [v("V1", D(2020, 1, 1), changed=("제5조",)), candidate]
    partial = LookupResult(LookupStatus.FOUND, Coverage.PARTIAL)
    assert latest_change_date(known, candidate, "제5조", history=FOUND)[0] == D(2020, 1, 1)
    assert latest_change_date(known, candidate, "제5조", history=partial)[0] == D(2026, 10, 2)
    assert latest_change_date(known, candidate, None, history=FOUND)[0] == D(2026, 10, 2)
    assert latest_change_date([candidate], candidate, "제9조", history=FOUND)[0] == D(2026, 10, 2)   # none recorded


def test_latest_change_date_ignores_versions_after_the_candidate():
    candidate = v("V2", D(2024, 3, 1), changed=())
    versions = [v("V1", D(2020, 1, 1), changed=("제5조",)), candidate, v("V3", D(2027, 6, 1), changed=("제5조",))]
    assert latest_change_date(versions, candidate, "제5조", history=FOUND)[0] == D(2020, 1, 1)


def test_rule_10_secondary_anchor_selecting_another_version():
    dates = RelevantDates(question_date=D(2026, 10, 19), conduct_date=D(2024, 1, 15), decision_date=D(2026, 10, 19))
    result = select(dates=dates, anchor=AnchorKind.CONDUCT_DATE, secondary=(AnchorKind.DECISION_DATE,), provision="제5조")
    assert result.candidate_keys() == [["V1", "2020-01-01"], ["V3", "2026-10-02"]]
    assert W.ANCHORS_SELECT_DIFFERENT_VERSIONS in result.warnings


def test_rule_10_secondary_anchor_agreeing_adds_nothing():
    dates = RelevantDates(question_date=D(2026, 10, 19), application_date=D(2026, 10, 5))
    result = select(dates=dates, secondary=(AnchorKind.APPLICATION_DATE,), provision="제5조")
    assert result.candidate_keys() == [["V3", "2026-10-02"]]
    assert W.ANCHORS_SELECT_DIFFERENT_VERSIONS not in result.warnings


def test_determination_is_always_candidate_only():
    for on in (D(2019, 1, 1), D(2026, 10, 19)):
        assert select(on=on).determination == "candidate_only"
    assert select(history=LookupResult(LookupStatus.UNAVAILABLE_TIMEOUT)).determination == "candidate_only"


def test_question_date_argument_fills_a_missing_question_anchor():
    result = select(dates=RelevantDates(), question_date=D(2024, 6, 1))
    assert result.candidate_keys() == [["V2", "2024-03-01"]]


def test_history_must_be_a_lookup_result():
    with pytest.raises(TypeError):
        select_candidate_versions(HISTORY, history=HISTORY, dates=RelevantDates(question_date=D(2026, 10, 19)),
                                  anchor=Q, question_date=D(2026, 10, 19))


# -- spec 06 §4 shapes, on the synthetic bundle --------------------------------
@pytest.fixture()
def adapter():
    return FixtureAdapter.from_id("synthetic_core")


def test_one_promulgation_listed_under_two_effective_dates(adapter):
    """Mirrors 시행규칙 289833: one 법령일련번호, rows at 2026-09-15 and 2027-09-16 (제73조)."""
    lookup, versions = adapter.list_versions("SYN-RUL-0001")
    before = select(versions, history=lookup, on=D(2026, 10, 19), provision="제73조")
    assert before.candidate_keys() == [["SYN-R1-3002", "2026-09-15"]]
    assert W.FUTURE_VERSION_PENDING in before.warnings
    after = select(versions, history=lookup, on=D(2027, 10, 1), question_date=D(2027, 10, 1), provision="제73조")
    assert after.candidate_keys() == [["SYN-R1-3002", "2027-09-16"]]
    assert W.FUTURE_VERSION_PENDING not in after.warnings


def test_anchor_before_the_current_version_does_not_select_it(adapter):
    lookup, versions = adapter.list_versions("SYN-ACT-0001")
    result = select(versions, history=lookup, on=D(2026, 10, 1), provision="제5조")
    assert result.candidate_keys() == [["SYN-A1-1002", "2024-03-01"]]
    assert W.FUTURE_VERSION_PENDING in result.warnings


def test_repealed_law_in_the_bundle(adapter):
    lookup, versions = adapter.list_versions("SYN-ACT-0002")
    assert select(versions, history=lookup, on=D(2026, 10, 19)).warnings == (W.SOURCE_REPEALED_BEFORE_ANCHOR,)


def test_partial_history_is_disclosed_in_detail(adapter):
    lookup, versions = adapter.list_versions("SYN-ACT-0008")
    assert lookup.coverage is Coverage.PARTIAL
    result = select(versions, history=lookup, on=D(2026, 10, 19))
    assert result.candidate_keys() == [["SYN-A8-9001", "2025-01-01"]]
    assert "coverage is partial" in result.detail


def test_provision_level_dates_decide_which_provisions_are_pending():
    """Mirrors 외국인고용법 286817: one version, 2026-12-10 overall, 제25조 on 2027-06-10 (spec 06 §4)."""
    versions = [
        v("OLD", D(2020, 1, 1)),
        v("NEW", D(2026, 12, 10), changed=("제1조", "제25조"), deferred={"제25조": D(2027, 6, 10)}),
    ]
    on = D(2027, 1, 1)
    deferred = select(versions, on=on, question_date=on, provision="제25조")
    assert deferred.candidate_keys() == [["OLD", "2020-01-01"]]
    assert W.FUTURE_VERSION_PENDING in deferred.warnings
    in_force = select(versions, on=on, question_date=on, provision="제1조")
    assert in_force.candidate_keys() == [["NEW", "2026-12-10"]]
    assert W.FUTURE_VERSION_PENDING not in in_force.warnings
