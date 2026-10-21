"""Candidate-version selection for one legal identity (spec 06 §3).

Why this is a separate, small function: the backend has no notion of "the
version that applies on a date". It pins law versions by hand, sends no
``efYd``, and reads no 부칙. The question "which text governs this event" turns
on the anchor date chosen from the issue type, on deferred 시행일 of individual
provisions, on versions promulgated but not yet in force, and on transitional
clauses. This function does the mechanical part of that and nothing more:

* it never picks the anchor (the caller chooses an ``AnchorKind`` from the issue
  type) and never falls back to "the current law" when the anchor is unknown;
* it never applies a transitional clause, it only warns that one is unread;
* its result is always ``determination = "candidate_only"``. Which version
  governs in law is decided at L6 review and by people.

The ten rules are implemented in order, one helper per rule where it helps
reading. Rule numbers in comments refer to spec 06 §3.

Provision keys may name an article (제4조) or a unit below it (제4조제4항).
``provision_effective_dates`` is read the same way everywhere (rules 3, 7 and
8): the exact key first, then the nearest enclosing unit's entry, because a
paragraph cannot take effect before the article it belongs to. Rule 8 also
lets a key match the entries of its own sub-units (an article key matches its
paragraphs), because a deferred paragraph means the article's text changes on
that date.

``latest_change_date`` is the date spec 07 §3 L7 compares a manual edition
with: the latest version, not later than the candidate, that changed the
provision.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from waymaker_ai.contracts import (
    AnchorKind,
    Coverage,
    LookupResult,
    ProvisionRef,
    RelevantDates,
    SourceVersion,
    TemporalAssessment,
    TemporalWarning,
)
from waymaker_ai.legal.citations import article_key_of, provision_ref_from_key
from waymaker_ai.legal.identity import provision_key_of

CANDIDATE_ONLY = "candidate_only"


def enclosing_keys(provision_key: Optional[str]) -> List[str]:
    """Keys of the units that contain ``provision_key``, nearest first.

    '제4조제4항제1호' → ['제4조제4항', '제4조']. An article, an annex, a form, or
    a key the citation scanner cannot read has none.
    """
    ref = provision_ref_from_key(provision_key) if provision_key else None
    if ref is None or ref.article is None:
        return []
    parents: List[ProvisionRef] = []
    if ref.subitem:
        parents.append(replace(ref, subitem=None))
    if ref.item is not None:
        parents.append(replace(ref, item=None, item_branch=0, subitem=None))
    if ref.paragraph is not None:
        parents.append(replace(ref, paragraph=None, item=None, item_branch=0, subitem=None))
    keys: List[str] = []
    for parent in parents:
        key = parent.key()
        if key not in keys and key != provision_key_of(provision_key or ""):
            keys.append(key)
    return keys


def _entries(version: SourceVersion) -> Dict[str, Optional[dt.date]]:
    """``provision_effective_dates`` with keys compared without spaces."""
    return {provision_key_of(key): date for key, date in (version.provision_effective_dates or {}).items()}


def own_entry(version: SourceVersion, provision_key: Optional[str]) -> Optional[Tuple[str, Optional[dt.date]]]:
    """The entry that dates ``provision_key`` itself: the exact key, else the nearest enclosing unit's."""
    if not provision_key:
        return None
    entries = _entries(version)
    if not entries:
        return None
    asked = provision_key_of(provision_key)
    if asked in entries:
        return asked, entries[asked]
    for key in enclosing_keys(asked):
        if key in entries:
            return key, entries[key]
    return None


def effective_for(version: SourceVersion, provision_key: Optional[str]) -> Optional[dt.date]:
    """Rule 3: the effective date of a version for the provision.

    ``SourceVersion.effective_date_for`` reads the exact key only. Here a
    sub-article key without its own entry takes the entry of the unit that
    contains it, so 제7조제1항 of a version whose 제7조 is deferred is deferred too.
    """
    entry = own_entry(version, provision_key)
    if entry is not None:
        return entry[1]
    return version.effective_date


def anchor_date_of(
    dates: RelevantDates, anchor: Optional[AnchorKind], question_date: Optional[dt.date]
) -> Optional[dt.date]:
    """The date of ``anchor``. Only the question date may come from the separate argument."""
    if anchor is None:
        return None
    value = dates.get(anchor)
    if value is None and anchor is AnchorKind.QUESTION_DATE:
        return question_date
    return value


def latest_on_or_before(
    versions: Sequence[SourceVersion], when: dt.date, provision_key: Optional[str]
) -> List[SourceVersion]:
    """Rule 4: the versions with the latest effective date ≤ ``when`` (several only on a tie)."""
    dated = [(effective_for(v, provision_key), v) for v in versions]
    eligible = [(date, v) for date, v in dated if date is not None and date <= when]
    if not eligible:
        return []
    best = max(date for date, _ in eligible)
    return [v for date, v in eligible if date == best]


def _key_text(version: SourceVersion, provision_key: Optional[str]) -> str:
    date = effective_for(version, provision_key)
    return f"({version.version_id}, {version.key[1]}) effective {date.isoformat() if date else 'unknown'}"


def changes_provision(version: SourceVersion, provision_key: Optional[str]) -> Optional[bool]:
    """Whether ``version`` changed the provision's article: None when its ``changed_provisions`` is unknown.

    ``changed_provisions`` holds article keys; an entry written below article
    level (제4조제4항) counts for its article.
    """
    if version.changed_provisions is None:
        return None
    article = article_key_of(provision_key)
    return article in {article_key_of(provision_key_of(k)) for k in version.changed_provisions}


def _counts_as_pending(version: SourceVersion, provision_key: Optional[str]) -> bool:
    """Rule 7 relevance. With no provision named, every later version counts; unknown changes count too."""
    if provision_key is None:
        return True
    return changes_provision(version, provision_key) is not False


def pending_versions(
    versions: Sequence[SourceVersion], when: dt.date, provision_key: Optional[str]
) -> List[SourceVersion]:
    """Rule 7: versions taking effect (for the provision) after ``when`` that touch it."""
    return [
        v for v in versions
        if (effective_for(v, provision_key) or dt.date.min) > when and _counts_as_pending(v, provision_key)
    ]


def deferred_entries(candidate: SourceVersion, provision_key: Optional[str]) -> Dict[str, dt.date]:
    """Rule 8: entries of ``provision_effective_dates`` for the provision whose date differs.

    The provision's own entry is the exact key, or else the nearest enclosing
    unit's (제4조 when 제4조제4항 is asked). Entries of the provision's own
    sub-units count too (제4조제4항 when 제4조 is asked): part of the text the
    caller will read is not in force on the version's own date.
    """
    if not provision_key:
        return {}
    entries = _entries(candidate)
    if not entries:
        return {}
    asked = provision_key_of(provision_key)
    found: Dict[str, dt.date] = {}
    own = own_entry(candidate, asked)
    if own is not None and own[1] is not None and own[1] != candidate.effective_date:
        found[own[0]] = own[1]
    for key, date in entries.items():
        if date is not None and asked in enclosing_keys(key) and date != candidate.effective_date:
            found[key] = date
    return found


def latest_change_date(
    versions: Sequence[SourceVersion],
    candidate: SourceVersion,
    provision_key: Optional[str],
    *,
    history: Optional[LookupResult] = None,
) -> Tuple[Optional[dt.date], str]:
    """Spec 07 §3 L7: the effective date of the latest version, not later than the candidate, that changed the provision.

    Returns (date, how it was chosen). The candidate's own date for the
    provision is used, conservatively, whenever the answer is not known: no
    provision named, a version on the way back whose ``changed_provisions`` is
    unknown, a history that is not complete (a missing version may have changed
    it), or no loaded version that records a change to it.
    """
    c_date = effective_for(candidate, provision_key)
    fallback = f"the candidate {list(candidate.key)}"
    if provision_key is None:
        return c_date, f"{fallback} (no provision named)"
    if history is not None and history.coverage is not Coverage.COMPLETE:
        return c_date, f"{fallback} (the version history is partial)"
    if c_date is None:
        return None, f"{fallback} (no effective date)"
    earlier = [
        v for v in versions
        if not v.is_repeal and effective_for(v, provision_key) is not None and effective_for(v, provision_key) <= c_date
    ]
    if candidate.key not in {v.key for v in earlier}:
        earlier.append(candidate)
    earlier.sort(key=lambda v: (effective_for(v, provision_key), v.key == candidate.key), reverse=True)
    for version in earlier:
        changed = changes_provision(version, provision_key)
        if changed is None:
            return c_date, f"{fallback} (changes made by {list(version.key)} are unknown)"
        if changed:
            date = effective_for(version, provision_key)
            return date, f"{list(version.key)}, the latest version that changed {article_key_of(provision_key)}"
    return c_date, f"{fallback} (no loaded version records a change to {article_key_of(provision_key)})"


def _dedupe(warnings: Iterable[TemporalWarning]) -> Tuple[TemporalWarning, ...]:
    seen: List[TemporalWarning] = []
    for warning in warnings:
        if warning not in seen:
            seen.append(warning)
    return tuple(seen)


def _assessment(
    candidates: Sequence[SourceVersion], warnings: Iterable[TemporalWarning], anchor: Optional[AnchorKind],
    anchor_date: Optional[dt.date], notes: Sequence[str],
) -> TemporalAssessment:
    return TemporalAssessment(
        candidates=tuple(candidates), warnings=_dedupe(warnings), anchor=anchor, anchor_date=anchor_date,
        determination=CANDIDATE_ONLY, detail="; ".join(n for n in notes if n),
    )


def select_candidate_versions(
    versions: Sequence[SourceVersion],
    *,
    history: LookupResult,
    dates: RelevantDates,
    anchor: Optional[AnchorKind],
    secondary_anchors: Sequence[AnchorKind] = (),
    provision_key: Optional[str] = None,
    question_date: Optional[dt.date],
) -> TemporalAssessment:
    """Candidate versions of one identity for the anchor date (spec 06 §3, rules 1-10).

    ``versions`` and ``history`` are the two halves of one ``list_versions``
    call. ``provision_key`` is the cited provision's key (usually an article
    key); None asks about the law as a whole. ``question_date`` is used only
    when the anchor is the question date and ``dates`` does not carry it.
    """
    if not isinstance(history, LookupResult):
        raise TypeError("history must be the LookupResult of list_versions, not "
                        f"{type(history).__name__}")
    notes: List[str] = []
    anchor_date = anchor_date_of(dates, anchor, question_date)

    # Rule 1: a failed history lookup says nothing about which versions exist.
    if history.status.is_failure:
        notes.append(f"version history lookup failed: {history.status.value} {history.detail}".strip())
        return _assessment((), [TemporalWarning.VERSION_HISTORY_UNAVAILABLE], anchor, anchor_date, notes)

    # Rule 2: no anchor, or no date for it. Never "the current law".
    if anchor is None or anchor_date is None:
        notes.append("anchor not chosen" if anchor is None else f"no date given for anchor {anchor.value}")
        return _assessment((), [TemporalWarning.ANCHOR_MISSING], anchor, anchor_date, notes)

    if history.coverage.value != "complete":
        notes.append("version history coverage is partial; a version missing from it cannot be ruled out")
    undated = [v for v in versions if effective_for(v, provision_key) is None]
    if undated:
        notes.append("versions without an effective date were not considered: "
                     + ", ".join(v.version_id for v in undated))

    warnings: List[TemporalWarning] = []
    # Rules 3-4: latest effective date (for the provision) on or before the anchor.
    candidates = latest_on_or_before(versions, anchor_date, provision_key)
    if len(candidates) > 1:
        warnings.append(TemporalWarning.ANCHORS_SELECT_DIFFERENT_VERSIONS)
        notes.append("several versions share the selected effective date: "
                     + ", ".join(_key_text(v, provision_key) for v in candidates))

    # Rule 5: nothing loaded reaches back to the anchor. Not evidence the law did not exist.
    if not candidates:
        earliest = min((effective_for(v, provision_key) for v in versions if effective_for(v, provision_key)),
                       default=None)
        notes.append(f"anchor {anchor_date.isoformat()} is before the earliest loaded version"
                     + (f" ({earliest.isoformat()})" if earliest else " (no dated version loaded)"))
        return _assessment((), [TemporalWarning.ANCHOR_BEFORE_KNOWN_HISTORY], anchor, anchor_date, notes)

    # Rule 6: the version in force on the anchor date is the repeal.
    repeals = [v for v in candidates if v.is_repeal]
    if repeals:
        notes.append(f"repealed by {_key_text(repeals[0], provision_key)}, on or before the anchor")
        return _assessment((), [TemporalWarning.SOURCE_REPEALED_BEFORE_ANCHOR], anchor, anchor_date, notes)

    # The primary anchor's candidates: one version, or several only on a tie (rule 4).
    # Rules 8 and 9 read these; secondary-anchor candidates (rule 10) never add those warnings.
    primaries = list(candidates)

    # Rule 7: promulgated versions that take effect after the anchor and touch the provision.
    # With no provision named, every later version counts.
    pending = pending_versions(versions, anchor_date, provision_key)
    if pending:
        warnings.append(TemporalWarning.FUTURE_VERSION_PENDING)
        notes.append("pending after the anchor: " + ", ".join(_key_text(v, provision_key) for v in pending))

    # Rule 8: a deferred 시행일 for the cited provision inside the candidate.
    for primary in primaries:
        deferred = deferred_entries(primary, provision_key)
        if deferred:
            warnings.append(TemporalWarning.PROVISION_EFFECTIVE_DATE_DIFFERS)
            notes.append(f"provision effective dates in {list(primary.key)} differ from the version date: "
                         + ", ".join(f"{k} {d.isoformat()}" for k, d in sorted(deferred.items())))

    # Rule 9: 부칙 unread (None) or present (True) in the primary candidate: never applied here.
    for primary in primaries:
        if primary.has_transitional_provisions is None or primary.has_transitional_provisions:
            warnings.append(TemporalWarning.TRANSITIONAL_PROVISIONS_UNREVIEWED)
            notes.append(f"부칙 of {list(primary.key)} not read" if primary.has_transitional_provisions is None
                         else f"부칙 of {list(primary.key)} has transitional provisions; not assessed")

    # Rule 10: secondary anchors that select a different version.
    selected = list(candidates)
    for secondary in secondary_anchors:
        secondary_date = anchor_date_of(dates, secondary, question_date)
        if secondary_date is None:
            notes.append(f"secondary anchor {secondary.value} has no date; not compared")
            continue
        others = latest_on_or_before(versions, secondary_date, provision_key)
        if not others:
            warnings.append(TemporalWarning.ANCHOR_BEFORE_KNOWN_HISTORY)
            notes.append(f"secondary anchor {secondary.value} ({secondary_date.isoformat()}) is before the loaded history")
            continue
        if {v.key for v in others} == {v.key for v in candidates}:
            continue
        warnings.append(TemporalWarning.ANCHORS_SELECT_DIFFERENT_VERSIONS)
        for other in others:
            if other.is_repeal:
                notes.append(f"secondary anchor {secondary.value} falls after the repeal {_key_text(other, provision_key)}")
            elif other.key not in {v.key for v in selected}:
                selected.append(other)
                notes.append(f"secondary anchor {secondary.value} selects {_key_text(other, provision_key)}")

    return _assessment(selected, warnings, anchor, anchor_date, notes)


__all__ = [
    "CANDIDATE_ONLY",
    "anchor_date_of",
    "changes_provision",
    "deferred_entries",
    "effective_for",
    "enclosing_keys",
    "latest_change_date",
    "latest_on_or_before",
    "own_entry",
    "pending_versions",
    "select_candidate_versions",
]
