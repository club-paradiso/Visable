"""Seven-layer claim verification (spec 07 §3).

Why layered: the backend calls a law "verified" when a title search returned
rows, and then lets every article number through. One boolean cannot carry
"the law exists", "this article exists in the version that applies on the
relevant date" and "the sentence follows from that text". ``verify_claim``
reports every layer, always, so an existing article (L3) is never mistaken
for a supported conclusion (L5).

How a claim is checked:

1. Its raw citation strings are parsed (``citations.parse_citation_strings``),
   with the adapter's known titles when it can list them and with the claim's
   ``context_title`` (the law that 같은 법 / 영 / 규칙 refer to).
2. Each citation runs L1-L4 on its own: identity (exact title only), candidate
   version (``temporal.select_candidate_versions``), the provision in the
   candidate version *C*, then heading and quotation.
3. The quotation belongs to the claim, not to one citation. It is attributed
   to the cited provision that contains it, first in the candidate version,
   then in the other versions of the same identity (version attribution, L2).
4. Each of L1-L4 reports the worst outcome over the claim's citations, in the
   order fail, unavailable, needs_review, pass, not_applicable.
5. L5-L7 are claim-level: deterministic support signals, scope and 부칙, and
   operational guidance on the claim's topic.

Blocked layers (spec 07 §3, decided 2026-10-20): a layer that cannot produce
a result because an earlier layer did not pass (no identity after L1, no
candidate after L2, no provision after L3) is still reported. It carries the
blocking layer's *outcome* with the code ``not_checked`` and a detail naming
the blocker, so ``overall()`` reflects the first real problem: an ambiguous
title gives ``human_review_required``, an unreachable source
``verification_unavailable``. L5 judged on guidance alone and L7 do not depend
on the citations and still run. A layer with nothing to check at all (L3 for a
citation of a whole law, L4 with no heading or quotation) is
``not_applicable`` whatever blocked it. "No provision after L3" includes a
cited 항 / 호 / 목 that L3 could not establish inside an article it did
retrieve: L4-L6 then carry L3's outcome instead of judging the rest of the
article. When the quotation was attributed to another version's text, L4-L6
judge that text (L2 has already failed), as they do for an article that is
missing from *C*.

Invariants this module keeps (spec 07 §2):

* A failed lookup is ``unavailable`` / ``verification_unavailable``. Only
  ``NOT_FOUND`` with ``Coverage.COMPLETE`` becomes ``source_not_found`` or
  ``citation_not_found``; partial title coverage becomes
  ``historical_lookup_required``.
* Partial coverage is never "there is nothing there": a partial version
  history makes L2 ``unavailable`` / ``version_history_incomplete``; a 부칙 that
  was not returned or not read makes L6 ``unavailable``; a missing 항 / 호 / 목 is
  ``citation_not_found`` only when ``ProvisionText.structure_complete``.
* Evidence a blocker kept out is not evidence of absence either: L5 never
  reports ``fail`` because a number is missing from the evidence it *could*
  read while a cited provision was blocked by anything other than a ``fail``.
* Titles match exactly after ``compact()``. Near matches appear in ``detail``
  and are never used.
* L5 passes only on a deterministic signal; otherwise ``needs_review``.
* Instruction-like text inside a source is flagged on the report
  (``injection_flags``) and never read by any rule.
* Conflicting guidance produces ``ConflictRecord``s (``VerificationReport.conflicts``)
  and ``needs_review``; authority rank never settles it.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from waymaker_ai.contracts import (
    AnchorKind,
    Citation,
    ClaimInput,
    ClaimVerification,
    ConflictRecord,
    Coverage,
    GuidanceItem,
    LayerOutcome,
    LayerResult,
    LegalSourceAdapter,
    LookupResult,
    LookupStatus,
    ProvisionRef,
    ProvisionText,
    RelevantDates,
    Scope,
    SourceIdentity,
    SourceVersion,
    TemporalAssessment,
    TemporalWarning,
    VerificationCode,
    VerificationLayer,
    compact,
    iter_layer_order,
    normalize_text,
    procedure_scope,
)
from waymaker_ai.legal.citations import parse_citation_strings
from waymaker_ai.legal.identity import exact_matches
from waymaker_ai.legal.injection import scan_flags
from waymaker_ai.legal.temporal import anchor_date_of, effective_for, latest_change_date, select_candidate_versions

L1 = VerificationLayer.SOURCE_IDENTITY
L2 = VerificationLayer.VERSION_IDENTITY
L3 = VerificationLayer.CITATION_IDENTITY
L4 = VerificationLayer.TEXT_CORRESPONDENCE
L5 = VerificationLayer.CLAIM_SUPPORT
L6 = VerificationLayer.APPLICABILITY
L7 = VerificationLayer.CONFLICT_UNCERTAINTY

#: Worst first. Each layer reports the worst outcome over a claim's citations.
OUTCOME_SEVERITY: Tuple[LayerOutcome, ...] = (
    LayerOutcome.FAIL,
    LayerOutcome.UNAVAILABLE,
    LayerOutcome.NEEDS_REVIEW,
    LayerOutcome.PASS,
    LayerOutcome.NOT_APPLICABLE,
)

#: 부칙 kinds that can change which rule governs a case.
TRANSITIONAL_KINDS = frozenset({"transitional", "application"})

#: Upper bounds on the extra get_provision calls one citation may spend on
#: other versions. Each is one upstream request against a live source, and a
#: law can have close to a hundred versions. Hitting a bound only weakens the
#: diagnosis (L4 text_mismatch instead of an L2 version finding; no
#: renumbering hint), never the outcome, and the detail says so.
MAX_ATTRIBUTION_LOOKUPS = 8
MAX_RENUMBERING_LOOKUPS = 4

VersionKey = Tuple[str, Optional[str]]


def severity(outcome: LayerOutcome) -> int:
    return OUTCOME_SEVERITY.index(outcome)


def _result(layer: VerificationLayer, outcome: LayerOutcome, code: VerificationCode, detail: str = "",
            evidence_ids: Sequence[str] = ()) -> LayerResult:
    return LayerResult(layer=layer, outcome=outcome, code=code, detail=detail, evidence_ids=tuple(evidence_ids))


def _blocked(layer: VerificationLayer, blocker: LayerResult) -> LayerResult:
    """A dependent layer that could not run: the blocker's outcome, code ``not_checked`` (spec 07 §3)."""
    outcome = blocker.outcome
    if outcome in (LayerOutcome.PASS, LayerOutcome.NOT_APPLICABLE):   # a blocker never passed; never upgrade
        outcome = LayerOutcome.NOT_APPLICABLE
    detail = f"not checked: blocked by {blocker.layer.value} ({blocker.outcome.value}, {blocker.code.value})"
    return _result(layer, outcome, VerificationCode.NOT_CHECKED, detail)


def worst(results: Sequence[LayerResult]) -> LayerResult:
    """The most severe result; the first one wins a tie."""
    return min(results, key=lambda r: severity(r.outcome))


# ---------------------------------------------------------------------------
# Report types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CitationCheck:
    """What L1-L4 established for one citation (used by the evidence package)."""

    citation: Citation
    title: Optional[str]
    identity: Optional[SourceIdentity]
    versions: Tuple[SourceVersion, ...]
    assessment: Optional[TemporalAssessment]
    candidate: Optional[SourceVersion]
    candidate_provision: Optional[ProvisionText]
    attributed_version: Optional[SourceVersion]
    attributed_provision: Optional[ProvisionText]
    layers: Tuple[LayerResult, ...]


@dataclass(frozen=True)
class VerificationReport(ClaimVerification):
    """A ``ClaimVerification`` plus what it was computed from.

    ``conflicts`` are the conflict records of L7; ``injection_flags`` maps an
    evidence id to the instruction-like-text flags found in its text.
    """

    citation_checks: Tuple[CitationCheck, ...] = ()
    conflicts: Tuple[ConflictRecord, ...] = ()
    evidence: Tuple[ProvisionText, ...] = ()
    guidance: Tuple[GuidanceItem, ...] = ()
    injection_flags: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)

    @property
    def injection_flagged(self) -> bool:
        return any(self.injection_flags.values())

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["conflicts"] = [
            {"topic": c.topic, "evidence_ids": list(c.evidence_ids), "kind": c.kind, "detail": c.detail,
             "requires_review": c.requires_review}
            for c in self.conflicts
        ]
        data["injection_flagged"] = self.injection_flagged
        data["injection_flags"] = {k: list(v) for k, v in sorted(self.injection_flags.items()) if v}
        return data


def conflicts_of(verification: ClaimVerification) -> Tuple[ConflictRecord, ...]:
    """Conflict records of a verification (empty for a plain ``ClaimVerification``)."""
    return tuple(getattr(verification, "conflicts", ()) or ())


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def contains_text(haystack: str, needle: Optional[str]) -> bool:
    """Containment after ``compact()``; an empty needle is never contained."""
    key = compact(needle or "")
    return bool(key) and key in compact(haystack)


def contains_number(haystack: str, number: str) -> bool:
    """'14일' in the text, but not as the tail of '114일' or the head of '140일'."""
    text, key = compact(haystack), compact(number)
    if not key:
        return False
    start = text.find(key)
    while start != -1:
        before = text[start - 1] if start > 0 else ""
        after = text[start + len(key)] if start + len(key) < len(text) else ""
        if not (key[0].isdecimal() and before.isdecimal()) and not (key[-1].isdecimal() and after.isdecimal()):
            return True
        start = text.find(key, start + 1)
    return False


def has_subitem_marker(text: str, letter: str) -> bool:
    """'가.' at the start of a token: the printed form of 가목."""
    marker = f"{letter}."
    index = text.find(marker)
    while index != -1:
        if index == 0 or text[index - 1].isspace() or text[index - 1] in "(（":
            return True
        index = text.find(marker, index + 1)
    return False


def parent_code(code: str) -> str:
    """'E-7-4' → 'E-7'; 'E-7-T' → 'E-7'; a two-segment code is its own parent."""
    parts = code.split("-")
    return "-".join(parts[:2]) if len(parts) >= 3 else code


# ---------------------------------------------------------------------------
# Per-citation work state
# ---------------------------------------------------------------------------
@dataclass
class _Work:
    citation: Citation
    title: Optional[str] = None
    identity: Optional[SourceIdentity] = None
    history: Optional[LookupResult] = None
    versions: Tuple[SourceVersion, ...] = ()
    assessment: Optional[TemporalAssessment] = None
    candidate: Optional[SourceVersion] = None
    provision_lookup: Optional[LookupResult] = None
    provision: Optional[ProvisionText] = None
    attributed: Optional[SourceVersion] = None
    attributed_provision: Optional[ProvisionText] = None
    quote_role: str = "none"          # none | matched | matched_other_version | mismatch | elsewhere | unknown
    asserted: bool = False            # attributed by ClaimInput.asserted_version_key
    asserted_missing: bool = False
    search_capped: bool = False       # MAX_ATTRIBUTION_LOOKUPS reached before every version was read
    unit_missing: bool = False        # L3: the article is in C, the cited 항 / 호 / 목 was not established in it
    layers: Dict[VerificationLayer, LayerResult] = field(default_factory=dict)
    blocker: Optional[LayerResult] = None
    cache: Dict[VersionKey, Tuple[LookupResult, Optional[ProvisionText]]] = field(default_factory=dict)

    @property
    def article_key(self) -> Optional[str]:
        provision = self.citation.provision
        return None if provision.is_empty() else provision.article_key()

    def set(self, result: LayerResult, *, blocking: bool = False) -> None:
        self.layers[result.layer] = result
        if blocking and self.blocker is None:
            self.blocker = result

    def fetch(self, adapter: LegalSourceAdapter, version: SourceVersion) -> Tuple[LookupResult, Optional[ProvisionText]]:
        if version.key not in self.cache:
            assert self.identity is not None
            self.cache[version.key] = adapter.get_provision(self.identity.stable_id, version.key, self.citation.provision)
        return self.cache[version.key]

    def judged_text(self) -> Optional[ProvisionText]:
        """The provision text L4-L6 judge for this citation, or None when a blocker kept it out.

        That is the attributed version's text, except when it is the
        candidate's article and L3 could not establish the cited 항 / 호 / 목
        in it: the cited provision was not established, so the layers that
        depend on it carry L3's outcome (spec 07 §3, blocked layers). Judging
        the rest of the article instead would turn a partly parsed article
        into a text_mismatch or claim_unsupported, which is absence inferred
        from incomplete evidence (§2.1-2.2).
        """
        text = self.attributed_provision
        if (text is not None and self.unit_missing and self.attributed is not None and self.candidate is not None
                and self.attributed.key == self.candidate.key):
            return None
        return text

    def scope_text(self) -> Optional[ProvisionText]:
        """The provision whose scope L6 reads: the judged text, or C's text when nothing blocked this citation."""
        judged = self.judged_text()
        if judged is not None:
            return judged
        return self.provision if self.blocker is None else None


@dataclass(frozen=True)
class _Context:
    adapter: LegalSourceAdapter
    dates: RelevantDates
    anchor: Optional[AnchorKind]
    anchor_date: Optional[dt.date]
    question_date: Optional[dt.date]
    secondary_anchors: Tuple[AnchorKind, ...]
    context_title: Optional[str]


# ---------------------------------------------------------------------------
# L1 source identity
# ---------------------------------------------------------------------------
def _check_source(work: _Work, ctx: _Context) -> None:
    title = work.citation.law_title_as_written or ctx.context_title
    work.title = title
    if not title:
        work.set(_result(L1, LayerOutcome.NEEDS_REVIEW, VerificationCode.SOURCE_AMBIGUOUS,
                         f"{work.citation.raw!r} names no law and there is no context law"), blocking=True)
        return
    lookup, identities = ctx.adapter.resolve_title(title, as_of=ctx.anchor_date)
    if lookup.status.is_failure:
        work.set(_result(L1, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                         f"title lookup failed ({lookup.status.value}); says nothing about absence. {lookup.detail}".strip()),
                 blocking=True)
        return
    exact = exact_matches(identities, title)
    if len(exact) == 1:
        work.identity = exact[0]
        work.set(_result(L1, LayerOutcome.PASS, VerificationCode.SOURCE_VERIFIED,
                         f"{title} → {exact[0].stable_id} ({exact[0].official_title})"))
        return
    if len(exact) > 1:
        ids = ", ".join(f"{i.stable_id} ({i.official_title})" for i in exact)
        work.set(_result(L1, LayerOutcome.NEEDS_REVIEW, VerificationCode.SOURCE_AMBIGUOUS,
                         f"{title} matches several identities exactly: {ids}"), blocking=True)
        return
    # No exact match from here on. Rows that were returned are near matches:
    # named in detail, never substituted (spec 07 §2.3).
    returned = ", ".join(f"{i.official_title} ({i.stable_id})" for i in identities)
    near = f" Near matches (not used): {returned}." if returned else ""
    if lookup.coverage is not Coverage.COMPLETE:
        # Partial coverage is not absence (§2.2), whether or not rows came back:
        # the exact identity may be one the partial index does not hold.
        work.set(_result(L1, LayerOutcome.UNAVAILABLE, VerificationCode.HISTORICAL_LOOKUP_REQUIRED,
                         f"{title}: not in a current-title index; it may have been renamed or repealed.{near} "
                         f"{lookup.detail}".strip()), blocking=True)
        return
    if lookup.status is LookupStatus.NOT_FOUND and not identities:
        # The only authoritative absence (§2.1): no rows, complete coverage.
        work.set(_result(L1, LayerOutcome.FAIL, VerificationCode.SOURCE_NOT_FOUND,
                         f"{title}: not in a complete title index. {lookup.detail}".strip()), blocking=True)
        return
    # Rows came back but none matches exactly (a fuzzy search upstream): not
    # source_not_found, which only an empty authoritative answer may produce.
    # A FOUND answer with no rows is contradictory and is not an absence either.
    what = "returned rows but no exact match" if identities else f"answered {lookup.status.value} with no rows"
    work.set(_result(L1, LayerOutcome.NEEDS_REVIEW, VerificationCode.SOURCE_AMBIGUOUS,
                     f"{title}: the lookup {what}; none substituted.{near} {lookup.detail}".strip()), blocking=True)


# ---------------------------------------------------------------------------
# L2 version identity (selection; attribution is decided after quotes are located)
# ---------------------------------------------------------------------------
def _select_version(work: _Work, ctx: _Context) -> None:
    assert work.identity is not None
    lookup, versions = ctx.adapter.list_versions(work.identity.stable_id)
    work.history, work.versions = lookup, tuple(versions)
    if lookup.status.is_failure:
        work.set(_result(L2, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                         f"version history lookup failed ({lookup.status.value}). {lookup.detail}".strip()), blocking=True)
        return
    assessment = select_candidate_versions(
        list(versions), history=lookup, dates=ctx.dates, anchor=ctx.anchor,
        secondary_anchors=ctx.secondary_anchors, provision_key=work.article_key, question_date=ctx.question_date,
    )
    work.assessment = assessment
    warnings = set(assessment.warnings)
    if TemporalWarning.SOURCE_REPEALED_BEFORE_ANCHOR in warnings:
        work.layers.pop(L1, None)
        work.set(_result(L1, LayerOutcome.FAIL, VerificationCode.SOURCE_REPEALED,
                         f"{work.identity.official_title}: {assessment.detail}"), blocking=True)
        return
    if TemporalWarning.ANCHOR_MISSING in warnings:
        work.set(_result(L2, LayerOutcome.NEEDS_REVIEW, VerificationCode.INSUFFICIENT_CONTEXT,
                         f"the anchor date is unknown; no fallback to the current law. {assessment.detail}"), blocking=True)
        return
    if not assessment.candidates:
        work.set(_result(L2, LayerOutcome.UNAVAILABLE, VerificationCode.VERSION_HISTORY_INCOMPLETE, assessment.detail),
                 blocking=True)
        return
    work.candidate = assessment.candidates[0]
    if work.article_key is not None:
        work.provision_lookup, work.provision = work.fetch(ctx.adapter, work.candidate)


def _attribution_finding(work: _Work, ctx: _Context) -> Optional[LayerResult]:
    """Compare the attributed version V with the candidate C (spec 07 §3 L2)."""
    candidate, attributed = work.candidate, work.attributed
    assert candidate is not None
    if work.asserted_missing:
        coverage = work.history.coverage if work.history else Coverage.PARTIAL
        if coverage is Coverage.COMPLETE:
            return _result(L2, LayerOutcome.FAIL, VerificationCode.WRONG_VERSION,
                           "the asserted version is not in the complete version history")
        return _result(L2, LayerOutcome.UNAVAILABLE, VerificationCode.VERSION_HISTORY_INCOMPLETE,
                       "the asserted version is not in the loaded (partial) history")
    if attributed is None or attributed.key == candidate.key:
        return None
    key = work.article_key
    assert work.assessment is not None
    if attributed.key in {v.key for v in work.assessment.candidates}:
        return _result(L2, LayerOutcome.NEEDS_REVIEW, VerificationCode.HUMAN_REVIEW_REQUIRED,
                       f"the claim relies on {list(attributed.key)}, selected by a secondary anchor")
    v_date, c_date = effective_for(attributed, key), effective_for(candidate, key)
    label = f"the claim relies on {list(attributed.key)}, the candidate is {list(candidate.key)}"
    if v_date is None or c_date is None:
        return _result(L2, LayerOutcome.NEEDS_REVIEW, VerificationCode.HUMAN_REVIEW_REQUIRED, f"{label}; a date is unknown")
    assert ctx.anchor_date is not None
    if v_date > ctx.anchor_date:
        if ctx.question_date is not None and v_date > ctx.question_date:
            return _result(L2, LayerOutcome.FAIL, VerificationCode.FUTURE_NOT_YET_EFFECTIVE,
                           f"{label}; it takes effect {v_date.isoformat()}, after the anchor and the question date")
        return _result(L2, LayerOutcome.FAIL, VerificationCode.WRONG_VERSION,
                       f"{label}; it takes effect {v_date.isoformat()}, after the anchor date {ctx.anchor_date.isoformat()}")
    if v_date < c_date:
        return _result(L2, LayerOutcome.FAIL, VerificationCode.SOURCE_OUTDATED,
                       f"{label}; it was superseded on {c_date.isoformat()}")
    return _result(L2, LayerOutcome.NEEDS_REVIEW, VerificationCode.HUMAN_REVIEW_REQUIRED, f"{label}; same effective date")


def _finish_version(work: _Work, ctx: _Context) -> None:
    if L2 in work.layers or work.blocker is not None:
        return
    assert work.assessment is not None and work.candidate is not None
    warnings = set(work.assessment.warnings)
    findings: List[LayerResult] = []
    attribution = _attribution_finding(work, ctx)
    if attribution is not None:
        findings.append(attribution)
    if TemporalWarning.ANCHOR_BEFORE_KNOWN_HISTORY in warnings:
        findings.append(_result(L2, LayerOutcome.UNAVAILABLE, VerificationCode.VERSION_HISTORY_INCOMPLETE,
                                work.assessment.detail))
    if work.history is not None and work.history.coverage is not Coverage.COMPLETE:
        # Partial coverage is not absence (spec 07 §2.2): a version between the
        # candidate and the anchor may simply not be listed.
        findings.append(_result(L2, LayerOutcome.UNAVAILABLE, VerificationCode.VERSION_HISTORY_INCOMPLETE,
                                f"the loaded version history is partial, so a later version in force on the anchor "
                                f"date cannot be ruled out; candidate {list(work.candidate.key)}"))
    if TemporalWarning.ANCHORS_SELECT_DIFFERENT_VERSIONS in warnings:
        findings.append(_result(L2, LayerOutcome.NEEDS_REVIEW, VerificationCode.HUMAN_REVIEW_REQUIRED,
                                f"the anchors select different versions: {work.assessment.detail}"))
    if findings:
        chosen = worst(findings)
        work.set(replace(chosen, detail="; ".join(f.detail for f in findings)))
        return
    work.set(_result(L2, LayerOutcome.PASS, VerificationCode.VERSION_VERIFIED,
                     f"candidate {list(work.candidate.key)}. {work.assessment.detail}".strip()))


# ---------------------------------------------------------------------------
# Quotation location (version attribution)
# ---------------------------------------------------------------------------
def _apply_asserted_version(works: Sequence[_Work], asserted: Optional[VersionKey]) -> None:
    if asserted is None:
        return
    key = (str(asserted[0]), asserted[1])
    holders = [w for w in works if w.candidate is not None and any(v.key == key for v in w.versions)]
    if not holders:
        for work in works:
            if work.candidate is not None:
                work.asserted_missing = True
        return
    for work in holders:
        work.attributed = next(v for v in work.versions if v.key == key)
        work.asserted = True


def _locate_quote(works: Sequence[_Work], quote: Optional[str], ctx: _Context) -> None:
    """Attribute the claim's quotation to the cited provision that contains it.

    The candidate's text is tried first. Only when no cited provision contains
    the quotation are other versions searched, and only for a citation whose
    candidate text is known not to contain it (retrieved, or authoritatively
    absent). Text that could not be retrieved is never treated as a mismatch.
    """
    active = [w for w in works if w.candidate is not None and w.article_key is not None]
    for work in active:
        if work.asserted and work.attributed is not None:
            work.attributed_provision = work.fetch(ctx.adapter, work.attributed)[1]
        else:
            work.attributed, work.attributed_provision = work.candidate, work.provision
    if not quote:
        return
    owners = [w for w in active if w.attributed_provision and contains_text(w.attributed_provision.full_text(), quote)]
    if not owners:
        for work in active:
            if not work.asserted and _candidate_text_known(work):
                found = _search_other_versions(work, quote, ctx)
                if found is not None:
                    work.attributed, work.attributed_provision = found
                    work.quote_role = "matched_other_version"
                    owners.append(work)
    unretrieved = any(w.attributed_provision is None and not _candidate_text_known(w) for w in active)
    for work in works:
        if work in owners:
            work.quote_role = work.quote_role if work.quote_role != "none" else "matched"
        elif owners:
            work.quote_role = "elsewhere"
        elif work in active and work.attributed_provision is not None and not unretrieved:
            work.quote_role = "mismatch"
        else:
            work.quote_role = "unknown"


def _candidate_text_known(work: _Work) -> bool:
    """The candidate's provision was retrieved, or is authoritatively absent."""
    if work.provision is not None:
        return True
    lookup = work.provision_lookup
    return lookup is not None and lookup.status is LookupStatus.NOT_FOUND and lookup.coverage is Coverage.COMPLETE


def _search_other_versions(work: _Work, quote: str, ctx: _Context) -> Optional[Tuple[SourceVersion, ProvisionText]]:
    """Newer versions first (relying on not-yet-applicable text is the worse error), then older."""
    assert work.candidate is not None
    key = work.article_key
    c_date = effective_for(work.candidate, key) or dt.date.min
    others = [v for v in work.versions if v.key != work.candidate.key and not v.is_repeal]
    newer = sorted((v for v in others if (effective_for(v, key) or dt.date.min) >= c_date),
                   key=lambda v: effective_for(v, key) or dt.date.min)
    older = sorted((v for v in others if (effective_for(v, key) or dt.date.min) < c_date),
                   key=lambda v: effective_for(v, key) or dt.date.min, reverse=True)
    ordered = newer + older
    for version in ordered[:MAX_ATTRIBUTION_LOOKUPS]:
        lookup, text = work.fetch(ctx.adapter, version)
        if lookup.status is LookupStatus.FOUND and text is not None and contains_text(text.full_text(), quote):
            return version, text
    work.search_capped = len(ordered) > MAX_ATTRIBUTION_LOOKUPS
    return None


# ---------------------------------------------------------------------------
# L3 citation identity
# ---------------------------------------------------------------------------
def _missing_subdivision(text: ProvisionText, ref: ProvisionRef) -> Optional[str]:
    if ref.paragraph is not None and ref.paragraph not in text.paragraphs:
        return f"제{ref.paragraph}항 is not in {text.provision_key}"
    if ref.item is not None:
        item_key = f"{ref.paragraph or 0}:{ref.item}" + (f"의{ref.item_branch}" if ref.item_branch else "")
        if item_key not in text.items:
            return f"item {item_key} is not in {text.provision_key}"
        if ref.subitem and not has_subitem_marker(text.items[item_key], ref.subitem):
            return f"{ref.subitem}목 is not in item {item_key} of {text.provision_key}"
    return None


def _other_versions_with_article(work: _Work, ctx: _Context) -> Tuple[List[str], bool]:
    """Other versions holding the article, nearest to the candidate first (a renumbering hint).

    Returns the version keys found and whether MAX_RENUMBERING_LOOKUPS cut the search short.
    """
    assert work.candidate is not None
    key = work.article_key
    c_date = effective_for(work.candidate, key) or dt.date.min

    def distance(version: SourceVersion) -> int:
        return abs(((effective_for(version, key) or dt.date.min) - c_date).days)

    others = sorted((v for v in work.versions if v.key != work.candidate.key and not v.is_repeal), key=distance)
    found: List[str] = []
    for version in others[:MAX_RENUMBERING_LOOKUPS]:
        lookup, text = work.fetch(ctx.adapter, version)
        if lookup.status is LookupStatus.FOUND and text is not None:
            found.append(str(list(version.key)))
    return found, len(others) > MAX_RENUMBERING_LOOKUPS


def _check_citation(work: _Work, ctx: _Context) -> None:
    """L3 on the candidate version C (spec 07 §3): the article, then its cited 항 / 호 / 목."""
    if work.article_key is None:
        work.set(_result(L3, LayerOutcome.NOT_APPLICABLE, VerificationCode.NOT_CHECKED, "no provision cited"))
        return
    if work.blocker is not None:
        work.set(_blocked(L3, work.blocker))
        return
    lookup, text = work.provision_lookup, work.provision
    assert lookup is not None
    key = work.citation.provision.key()
    if lookup.status.is_failure:
        work.set(_result(L3, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                         f"provision lookup failed ({lookup.status.value}). {lookup.detail}".strip()), blocking=True)
        return
    if text is None:
        if lookup.coverage is Coverage.COMPLETE:
            elsewhere, capped = _other_versions_with_article(work, ctx)
            note = f"; present in other versions {', '.join(elsewhere)} (renumbering?)" if elsewhere else ""
            if capped:
                note += f"; only the {MAX_RENUMBERING_LOOKUPS} nearest other versions were searched"
            work.set(_result(L3, LayerOutcome.FAIL, VerificationCode.CITATION_NOT_FOUND,
                             f"{key} is not in {list(work.candidate.key)}{note}"), blocking=True)
        else:
            work.set(_result(L3, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                             f"{key} was not captured; not evidence of absence. {lookup.detail}".strip()), blocking=True)
        return
    missing = _missing_subdivision(text, work.citation.provision)
    if missing is None:
        work.set(_result(L3, LayerOutcome.PASS, VerificationCode.CITATION_VERIFIED,
                         f"{key} in {list(work.candidate.key)}", [text.evidence_id]))
        return
    # The cited provision is the 항 / 호 / 목, not the article around it. Either
    # way it was not established, so it blocks the layers that depend on it.
    work.unit_missing = True
    if text.structure_complete:
        # Only a provision whose every 항 / 호 / 목 was parsed makes a missing sub-unit authoritative.
        work.set(_result(L3, LayerOutcome.FAIL, VerificationCode.CITATION_NOT_FOUND,
                         f"{missing} of {list(work.candidate.key)} (its 항/호/목 structure is complete)",
                         [text.evidence_id]), blocking=True)
    else:
        work.set(_result(L3, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                         f"{missing} of {list(work.candidate.key)}, but its 항/호/목 structure is not marked complete; "
                         f"not evidence of absence", [text.evidence_id]), blocking=True)


# ---------------------------------------------------------------------------
# L4 text correspondence
# ---------------------------------------------------------------------------
def _check_text(work: _Work, quote: Optional[str]) -> None:
    heading = work.citation.claimed_heading
    quote_applies = bool(quote) and work.quote_role != "elsewhere"
    if not heading and not quote_applies:
        work.set(_result(L4, LayerOutcome.NOT_APPLICABLE, VerificationCode.NOT_CHECKED, "no heading or quotation claimed"))
        return
    if work.blocker is not None and work.judged_text() is None:
        work.set(_blocked(L4, work.blocker))
        return
    if work.article_key is None:
        work.set(_result(L4, LayerOutcome.NEEDS_REVIEW, VerificationCode.HUMAN_REVIEW_REQUIRED,
                         "a quotation or heading without a cited provision cannot be compared"))
        return
    source = work.judged_text()
    if source is None:
        work.set(_missing_attributed_text(work))
        return
    problems: List[str] = []
    if heading and compact(heading) != compact(source.heading or ""):
        problems.append(f"claimed heading {heading!r} ≠ source heading {source.heading!r}")
    if quote_applies and work.quote_role == "mismatch":
        note = (f"; only {MAX_ATTRIBUTION_LOOKUPS} other versions were searched for it"
                if work.search_capped else "")
        problems.append(f"the quotation is not in the provision text of the attributed version{note}")
    if problems:
        work.set(_result(L4, LayerOutcome.FAIL, VerificationCode.TEXT_MISMATCH, "; ".join(problems), [source.evidence_id]))
        return
    if quote_applies and work.quote_role == "unknown":
        # The quotation is not here, and another cited provision that may hold it was not retrieved.
        work.set(_result(L4, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                         "the quotation could not be located: some cited text was not retrieved", [source.evidence_id]))
        return
    where = f" (text of {list(work.attributed.key)})" if work.attributed is not None else ""
    work.set(_result(L4, LayerOutcome.PASS, VerificationCode.TEXT_MATCH_VERIFIED, f"matched{where}", [source.evidence_id]))


def _missing_attributed_text(work: _Work) -> LayerResult:
    """L4 when the candidate text exists but the attributed (asserted) version's text does not."""
    lookup = work.cache.get(work.attributed.key)[0] if work.attributed and work.attributed.key in work.cache else None
    label = list(work.attributed.key) if work.attributed else "the attributed version"
    if lookup is not None and lookup.status is LookupStatus.NOT_FOUND and lookup.coverage is Coverage.COMPLETE:
        return _result(L4, LayerOutcome.FAIL, VerificationCode.TEXT_MISMATCH,
                       f"{work.citation.provision.article_key()} is not in {label}, so nothing there can match")
    status = lookup.status.value if lookup is not None else "not requested"
    return _result(L4, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                   f"the text of {label} could not be retrieved ({status}); not evidence of a mismatch")


# ---------------------------------------------------------------------------
# Aggregation over citations
# ---------------------------------------------------------------------------
def _aggregate(layer: VerificationLayer, works: Sequence[_Work]) -> LayerResult:
    if not works:
        return _result(layer, LayerOutcome.NOT_APPLICABLE, VerificationCode.NOT_CHECKED, "claim has no resolvable citation")
    results = [w.layers[layer] for w in works]
    chosen = worst(results)
    if len(works) == 1:
        return chosen
    detail = " | ".join(f"{w.citation.raw}: {r.code.value} {r.detail}".strip() for w, r in zip(works, results))
    evidence_ids: List[str] = []
    for result in results:
        evidence_ids.extend(e for e in result.evidence_ids if e not in evidence_ids)
    return replace(chosen, detail=detail, evidence_ids=tuple(evidence_ids))


# ---------------------------------------------------------------------------
# L5 claim support
# ---------------------------------------------------------------------------
def _support_from_texts(claim: ClaimInput, texts: Sequence[Tuple[str, str]], quote_verified: bool) -> LayerResult:
    ids = [evidence_id for evidence_id, _ in texts]
    if claim.numbers:
        present = [n for n in claim.numbers if any(contains_number(text, n) for _, text in texts)]
        missing = [n for n in claim.numbers if n not in present]
        if not missing:
            return _result(L5, LayerOutcome.PASS, VerificationCode.CLAIM_SUPPORTED,
                           f"every asserted number appears in the evidence: {', '.join(present)}", ids)
        if present:
            return _result(L5, LayerOutcome.NEEDS_REVIEW, VerificationCode.CLAIM_PARTIALLY_SUPPORTED,
                           f"present: {', '.join(present)}; missing: {', '.join(missing)}", ids)
        return _result(L5, LayerOutcome.FAIL, VerificationCode.CLAIM_UNSUPPORTED,
                       f"no asserted number appears in the evidence: {', '.join(missing)}", ids)
    if quote_verified:
        return _result(L5, LayerOutcome.PASS, VerificationCode.CLAIM_SUPPORTED, "the quotation was verified at L4", ids)
    return _result(L5, LayerOutcome.NEEDS_REVIEW, VerificationCode.HUMAN_REVIEW_REQUIRED,
                   "no verified quotation and no numbers: semantic support needs a person", ids)


def _blocked_evidence(works: Sequence[_Work]) -> List[_Work]:
    """Citations whose evidence a blocker kept out (no identity, no candidate, no provision, or no cited 항 / 호 / 목)."""
    return [w for w in works if w.blocker is not None and w.judged_text() is None]


def _carried(layer: VerificationLayer, works: Sequence[_Work]) -> LayerResult:
    """``_blocked`` for a claim-level layer: the worst blocker over the given citations."""
    blockers = [w.blocker for w in works if w.blocker is not None]
    result = _blocked(layer, worst(blockers))
    if len(works) > 1:
        names = " | ".join(f"{w.citation.raw}: {w.blocker.layer.value} {w.blocker.code.value}"
                           for w in works if w.blocker is not None)
        result = replace(result, detail=f"{result.detail} [{names}]")
    return result


def _may_exist(works: Sequence[_Work]) -> List[_Work]:
    """Blocked citations whose text may still exist: blocked by anything but a ``fail`` (an authoritative absence)."""
    return [w for w in works if w.blocker is not None and w.blocker.outcome is not LayerOutcome.FAIL]


def _check_support(claim: ClaimInput, works: Sequence[_Work], guidance: "_Guidance") -> LayerResult:
    if not works:
        if guidance.failed is not None:
            return _result(L5, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                           f"guidance lookup failed or was partial ({guidance.failed.status.value})")
        if not guidance.items:
            return _result(L5, LayerOutcome.FAIL, VerificationCode.CLAIM_UNSUPPORTED,
                           "the claim has no citation and no guidance evidence")
        return _support_from_texts(claim, [(g.evidence_id, g.text) for g in guidance.items], quote_verified=False)

    judged = [w.judged_text() for w in works]
    texts = [(text.evidence_id, text.full_text()) for text in judged if text is not None]
    blocked = _blocked_evidence(works)
    if not texts:
        if not blocked:
            return _result(L5, LayerOutcome.NEEDS_REVIEW, VerificationCode.HUMAN_REVIEW_REQUIRED,
                           "no provision text to compare (the citation names a law only)")
        carried = _carried(L5, blocked)
        if not guidance.items:
            return carried
        # L5 on guidance-only support does not depend on the blocked citations (spec 07 §3).
        result = _support_from_texts(claim, [(g.evidence_id, g.text) for g in guidance.items], quote_verified=False)
        uncertain = _may_exist(blocked)
        if result.outcome is LayerOutcome.FAIL and uncertain:
            # The cited text could still hold the number: not a completed check (§2.1).
            carried = _carried(L5, uncertain)
            return replace(carried, detail=f"{carried.detail}; the guidance alone does not support it "
                                           f"({result.detail})", evidence_ids=result.evidence_ids)
        return replace(result, detail=f"guidance-only support: {result.detail}; cited evidence {carried.detail}")

    # Only a quotation located in text L4 judged counts (not one found beside a cited 항 that L3 did not establish).
    quote_verified = any(w.quote_role in ("matched", "matched_other_version") and w.judged_text() is not None
                         for w in works)
    result = _support_from_texts(claim, texts, quote_verified)
    uncertain = [w for w in _may_exist(blocked) if w.article_key is not None]
    if result.outcome is LayerOutcome.FAIL and uncertain:
        carried = _carried(L5, uncertain)
        return replace(carried, detail=f"{carried.detail}; the retrieved text does not support it "
                                       f"({result.detail}), but a blocked citation may",
                       evidence_ids=result.evidence_ids)
    return result


# ---------------------------------------------------------------------------
# L6 applicability
# ---------------------------------------------------------------------------
def _scope_findings(claim_scope: Scope, evidence_id: str, scope: Scope) -> List[LayerResult]:
    findings: List[LayerResult] = []
    claim_parents = {parent_code(c) for c in claim_scope.status_codes} | {parent_code(s) for s in claim_scope.subcodes}
    evidence_parents = {parent_code(c) for c in scope.status_codes}
    if claim_parents and evidence_parents and not claim_parents & evidence_parents:
        findings.append(_result(L6, LayerOutcome.NEEDS_REVIEW, VerificationCode.HUMAN_REVIEW_REQUIRED,
                                f"{evidence_id} speaks to {sorted(evidence_parents)}, the claim to {sorted(claim_parents)}",
                                [evidence_id]))
    for subcode in claim_scope.subcodes:
        if scope.subcodes:
            if subcode not in scope.subcodes:
                findings.append(_result(L6, LayerOutcome.FAIL, VerificationCode.SUBCODE_APPLICABILITY_UNPROVEN,
                                        f"{evidence_id} lists subcodes {list(scope.subcodes)}, not {subcode}", [evidence_id]))
        elif parent_code(subcode) in evidence_parents and not scope.all_subcodes_explicit:
            findings.append(_result(L6, LayerOutcome.NEEDS_REVIEW, VerificationCode.SUBCODE_APPLICABILITY_UNPROVEN,
                                    f"{evidence_id} is stated for {parent_code(subcode)} only; "
                                    f"that does not establish it for {subcode}", [evidence_id]))
    if not claim_scope.subcodes and claim_scope.status_codes and scope.subcodes:
        parents_only = [c for c in claim_scope.status_codes if c == parent_code(c)]
        if parents_only:
            findings.append(_result(L6, LayerOutcome.FAIL, VerificationCode.SUBCODE_APPLICABILITY_UNPROVEN,
                                    f"{evidence_id} is stated for subcodes {list(scope.subcodes)} only, "
                                    f"not for the parent {parents_only} as a whole", [evidence_id]))
    if claim_scope.all_subcodes_explicit and not scope.all_subcodes_explicit and not scope.subcodes:
        findings.append(_result(L6, LayerOutcome.NEEDS_REVIEW, VerificationCode.SUBCODE_APPLICABILITY_UNPROVEN,
                                f"{evidence_id} does not say it covers every subcode", [evidence_id]))
    if claim_scope.procedures and scope.procedures:
        claim_procs, evidence_procs = set(claim_scope.procedures), set(scope.procedures)
        claim_kinds = {procedure_scope(p) for p in claim_procs}
        evidence_kinds = {procedure_scope(p) for p in evidence_procs}
        if not claim_kinds & evidence_kinds:
            findings.append(_result(L6, LayerOutcome.FAIL, VerificationCode.PROCEDURE_SCOPE_MISMATCH,
                                    f"{evidence_id} is {sorted(evidence_kinds)} scope, the claim {sorted(claim_kinds)}",
                                    [evidence_id]))
        elif not claim_procs & evidence_procs:
            findings.append(_result(L6, LayerOutcome.FAIL, VerificationCode.PROCEDURE_SCOPE_MISMATCH,
                                    f"{evidence_id} covers {sorted(evidence_procs)}, the claim {sorted(claim_procs)}",
                                    [evidence_id]))
    return findings


def _addendum_findings(work: _Work, ctx: _Context) -> List[LayerResult]:
    """L6 on the candidate's 부칙 (spec 07 §3).

    Not failed, not NOT_FOUND, complete coverage and ``has_transitional_provisions``
    not None are all required before "no transitional clause reaches this
    provision" can be said. Every version has a 부칙 (at least its 시행일 clause),
    so NOT_FOUND means it was not captured, never that it is empty.
    """
    if work.identity is None or work.candidate is None:
        return []
    label = list(work.candidate.key)
    lookup, addenda = ctx.adapter.get_addenda(work.identity.stable_id, work.candidate.key)
    if lookup.status.is_failure:
        return [_result(L6, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                        f"부칙 lookup failed ({lookup.status.value}) for {label}")]
    findings: List[LayerResult] = []
    unread: List[str] = []
    if lookup.status is LookupStatus.NOT_FOUND:
        unread.append("no 부칙 was returned")
    if lookup.coverage is not Coverage.COMPLETE:
        unread.append("the 부칙 lookup is partial")
    if work.candidate.has_transitional_provisions is None:
        unread.append("has_transitional_provisions is unknown (부칙 not read)")
    if unread:
        # Not absence (spec 07 §2.2): an unread 부칙 may hold the clause that decides the case.
        findings.append(_result(L6, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                                f"부칙 of {label}: {', '.join(unread)}; a transitional or application clause "
                                f"cannot be ruled out"))
    for addendum in addenda:
        if addendum.kind not in TRANSITIONAL_KINDS:
            continue
        named = work.article_key is not None and work.article_key in addendum.mentions
        if named or not addendum.mentions:
            reason = f"names {work.article_key}" if named else "names no article (it can reach any filing)"
            findings.append(_result(L6, LayerOutcome.NEEDS_REVIEW, VerificationCode.TRANSITIONAL_RULE_UNRESOLVED,
                                    f"{addendum.kind} 부칙 of {list(work.candidate.key)} {reason}: not applied"))
    return findings


def _check_applicability(claim: ClaimInput, works: Sequence[_Work], guidance: "_Guidance", ctx: _Context) -> LayerResult:
    findings: List[LayerResult] = []
    needs_date = bool(works) or ctx.anchor is not None
    if needs_date and ctx.anchor_date is None:
        findings.append(_result(L6, LayerOutcome.NEEDS_REVIEW, VerificationCode.INSUFFICIENT_CONTEXT,
                                "the claim turns on a date that was not provided"))
    # A citation without a candidate (for its 부칙) or, when it cites a provision,
    # without that provision established (for its scope) cannot be assessed: L6 carries its blocker.
    blocked = [w for w in works if w.blocker is not None
               and (w.candidate is None or (w.article_key is not None and w.scope_text() is None))]
    checked = [w for w in works if w not in blocked]
    if works:
        scoped = [w.scope_text() for w in checked]
        evidence = [(p.evidence_id, p.scope) for p in scoped if p is not None]
    else:
        evidence = [(g.evidence_id, g.scope) for g in guidance.items]
    if claim.scope is not None:
        for evidence_id, scope in evidence:
            if scope is not None:
                findings.extend(_scope_findings(claim.scope, evidence_id, scope))
    for work in checked:
        findings.extend(_addendum_findings(work, ctx))
    if blocked:
        findings.append(_carried(L6, blocked))   # last, so a real finding of equal severity is the one reported
    if findings:
        chosen = worst(findings)
        return replace(chosen, detail="; ".join(f.detail for f in findings),
                       evidence_ids=tuple(dict.fromkeys(e for f in findings for e in f.evidence_ids)))
    if not evidence:
        return _result(L6, LayerOutcome.NOT_APPLICABLE, VerificationCode.NOT_CHECKED, "not checked: no evidence to compare")
    if claim.scope is None:
        return _result(L6, LayerOutcome.NOT_APPLICABLE, VerificationCode.NOT_CHECKED, "the claim states no scope")
    unscoped = [e for e, s in evidence if s is None]
    note = f"; no scope recorded for {', '.join(unscoped)}" if unscoped else ""
    return _result(L6, LayerOutcome.PASS, VerificationCode.APPLICABILITY_ESTABLISHED,
                   f"claim scope consistent with the evidence{note}", [e for e, _ in evidence])


# ---------------------------------------------------------------------------
# L7 conflict and uncertainty
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Guidance:
    items: Tuple[GuidanceItem, ...] = ()
    failed: Optional[LookupResult] = None
    consulted: bool = False


def _load_guidance(claim: ClaimInput, ctx: _Context) -> _Guidance:
    """Guidance on the claim's topic. A failed lookup, or an empty answer from a partial one, is unavailable (§2.1-2.2)."""
    if not claim.topic:
        return _Guidance()
    lookup, items = ctx.adapter.guidance(claim.topic)
    if lookup.status.is_failure or (not items and lookup.coverage is not Coverage.COMPLETE):
        return _Guidance(failed=lookup, consulted=True)
    return _Guidance(items=tuple(items), consulted=True)


def _check_conflicts(claim: ClaimInput, works: Sequence[_Work], guidance: _Guidance) -> Tuple[LayerResult, List[ConflictRecord]]:
    """L7 (spec 07 §3). Runs whatever blocked L1-L4; a blocked citation only drops out of the date comparison."""
    if not claim.topic:
        return _result(L7, LayerOutcome.NOT_APPLICABLE, VerificationCode.NOT_CHECKED,
                       "the claim names no topic: no guidance was compared, so no absence of conflict is claimed"), []
    if guidance.failed is not None:
        return _result(L7, LayerOutcome.UNAVAILABLE, VerificationCode.VERIFICATION_UNAVAILABLE,
                       f"guidance lookup failed or was partial ({guidance.failed.status.value}); conflicts unknown"), []
    topic = str(claim.topic)
    cited_ids = tuple(w.attributed_provision.evidence_id for w in works if w.attributed_provision is not None)
    mismatches: List[LayerResult] = []
    predating: List[LayerResult] = []
    conflicts: List[ConflictRecord] = []
    for item in guidance.items:
        if item.value is not None and claim.value is not None and normalize_text(item.value) != normalize_text(claim.value):
            detail = f"{item.evidence_id} says {item.value!r}, the claim {claim.value!r}"
            conflicts.append(ConflictRecord(topic=topic, evidence_ids=cited_ids + (item.evidence_id,),
                                            kind="value_mismatch", detail=detail))
            mismatches.append(_result(L7, LayerOutcome.NEEDS_REVIEW, VerificationCode.CONTRADICTORY_EVIDENCE, detail,
                                      [item.evidence_id]))
        for work in works:
            if work.candidate is None or item.edition_date is None:
                continue
            changed_on, basis = latest_change_date(work.versions, work.candidate, work.article_key, history=work.history)
            if changed_on is not None and item.edition_date < changed_on:
                detail = (f"{item.evidence_id} (edition {item.edition_date.isoformat()}) predates the law change in "
                          f"force from {changed_on.isoformat()}: {basis}")
                law_ids = (work.attributed_provision.evidence_id,) if work.attributed_provision else ()
                ids = law_ids + (item.evidence_id,)
                conflicts.append(ConflictRecord(topic=topic, evidence_ids=ids, kind="manual_predates_law_change",
                                                detail=detail))
                predating.append(_result(L7, LayerOutcome.NEEDS_REVIEW, VerificationCode.MANUAL_PREDATES_LAW_CHANGE,
                                         detail, [item.evidence_id]))
    findings = mismatches + predating
    if findings:
        # Both kinds may apply: the layer code is the more specific contradictory_evidence,
        # and every ConflictRecord of both kinds is kept.
        code = VerificationCode.CONTRADICTORY_EVIDENCE if mismatches else VerificationCode.MANUAL_PREDATES_LAW_CHANGE
        return _result(L7, LayerOutcome.NEEDS_REVIEW, code, "; ".join(f.detail for f in findings),
                       tuple(dict.fromkeys(e for f in findings for e in f.evidence_ids))), conflicts
    return _result(L7, LayerOutcome.PASS, VerificationCode.NO_CONFLICT_DETECTED,
                   f"{len(guidance.items)} guidance item(s) on {topic!r} agree", [g.evidence_id for g in guidance.items]), []


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def _as_anchor(anchor: Any) -> Optional[AnchorKind]:
    if anchor is None or isinstance(anchor, AnchorKind):
        return anchor
    return AnchorKind(str(anchor))


def _known_titles(adapter: LegalSourceAdapter) -> Tuple[str, ...]:
    """Titles the adapter's index answers to, when it can list them (not part of the protocol).

    They let a citation string with leading words ("근거: 가상체류관리법 제5조")
    find its title by longest suffix match. A string whose title is not known
    still takes its leading text as written, so an unknown title is never
    shortened into a known one.
    """
    lister = getattr(adapter, "known_titles", None)
    if not callable(lister):
        return ()
    try:
        return tuple(lister())
    except TypeError:
        return ()


def _injection_flags(works: Sequence[_Work], guidance: _Guidance) -> Dict[str, Tuple[str, ...]]:
    flags: Dict[str, Tuple[str, ...]] = {}
    for work in works:
        for _, text in work.cache.values():
            if text is not None:
                flags[text.evidence_id] = scan_flags(text.full_text())
    for item in guidance.items:
        flags[item.evidence_id] = scan_flags(item.text)
    return flags


def verify_claim(
    claim: ClaimInput,
    adapter: LegalSourceAdapter,
    *,
    dates: RelevantDates,
    anchor: Optional[AnchorKind],
    question_date: Optional[dt.date],
    context_title: Optional[str] = None,
    secondary_anchors: Sequence[AnchorKind] = (),
) -> VerificationReport:
    """Verify one claim through L1-L7 (spec 07 §3). Every layer is always reported.

    The law that 같은 법 / 영 / 규칙 and a bare 제N조 refer to is
    ``claim.context_title``; the ``context_title`` argument is used only when the
    claim carries none.
    """
    anchor_kind = _as_anchor(anchor)
    title_context = (claim.context_title or "").strip() or (context_title or "").strip()
    ctx = _Context(
        adapter=adapter, dates=dates, anchor=anchor_kind,
        anchor_date=anchor_date_of(dates, anchor_kind, question_date),
        question_date=question_date or dates.question_date,
        secondary_anchors=tuple(_as_anchor(a) for a in secondary_anchors if a is not None),
        context_title=normalize_text(title_context) if title_context else None,
    )
    quote = normalize_text(claim.quoted_text) if claim.quoted_text and claim.quoted_text.strip() else None
    citations = parse_citation_strings(list(claim.citations), known_titles=_known_titles(adapter),
                                       context_title=ctx.context_title)
    works = [_Work(citation=c) for c in citations]

    for work in works:
        _check_source(work, ctx)
        if work.identity is not None:
            work.citation = replace(work.citation, resolved_stable_id=work.identity.stable_id)
            _select_version(work, ctx)
    _apply_asserted_version(works, claim.asserted_version_key)
    _locate_quote(works, quote, ctx)
    for work in works:
        if work.blocker is not None:
            for layer in (L2,):
                if layer not in work.layers:
                    work.set(_blocked(layer, work.blocker))
        _finish_version(work, ctx)
        _check_citation(work, ctx)
        _check_text(work, quote)

    guidance = _load_guidance(claim, ctx)
    l7, conflicts = _check_conflicts(claim, works, guidance)
    layers = [_aggregate(layer, works) for layer in (L1, L2, L3, L4)]
    layers.append(_check_support(claim, works, guidance))
    layers.append(_check_applicability(claim, works, guidance, ctx))
    layers.append(l7)
    assert [r.layer for r in layers] == list(iter_layer_order())

    checks = tuple(
        CitationCheck(
            citation=w.citation, title=w.title, identity=w.identity, versions=w.versions, assessment=w.assessment,
            candidate=w.candidate, candidate_provision=w.provision, attributed_version=w.attributed,
            attributed_provision=w.attributed_provision,
            layers=tuple(w.layers[layer] for layer in (L1, L2, L3, L4)),
        )
        for w in works
    )
    evidence: List[ProvisionText] = []
    for work in works:
        for text in (work.provision, work.attributed_provision):
            if text is not None and text not in evidence:
                evidence.append(text)
    return VerificationReport(
        claim_id=claim.claim_id, layers=tuple(layers), citation_checks=checks, conflicts=tuple(conflicts),
        evidence=tuple(evidence), guidance=guidance.items, injection_flags=_injection_flags(works, guidance),
    )


__all__ = [
    "CitationCheck",
    "OUTCOME_SEVERITY",
    "TRANSITIONAL_KINDS",
    "VerificationReport",
    "conflicts_of",
    "contains_number",
    "contains_text",
    "has_subitem_marker",
    "parent_code",
    "severity",
    "verify_claim",
    "worst",
]
