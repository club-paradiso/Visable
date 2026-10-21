# 07 — Evidence verification design (normative)

Status: **IMPLEMENTED BUT NOT VALIDATED** against real answers. The rules below are
implemented in `experiments/waymaker-ai/waymaker_ai/legal/verification.py` and
exercised by the `legal_verification` benchmark suite. They are not yet wired into
`/api/ask`. Vocabulary: `experiments/waymaker-ai/waymaker_ai/contracts.py`.

This document is the specification. Benchmark labels are written from it, not
from the implementation's output, so a disagreement between the two is a finding,
not something to paper over.

## 1. Why layered

The existing backend calls a law "verified" when a title-list search returned
rows (`citation_verifier.py:136`). When that flag is set, `guard_answer_citations`
lets every article number through (`law_citation_guard.py:126-128`, see
[01 §4](01-existing-system-audit.md)). One boolean cannot carry "the law
exists", "this article exists in the version that applies on the relevant date"
and "the sentence the model wrote follows from that text". WLIE keeps these apart:

| Layer | Question | Typical failure it catches |
|---|---|---|
| L1 `source_identity` | Does the cited document exist, and is it the one named? | wrong-law substitution (A), renamed/repealed law (G) |
| L2 `version_identity` | Is the text from the version that applies on the anchor date? | later amendment applied to a past event (D), promulgated-not-effective text (E), stale cache |
| L3 `citation_identity` | Does the article / 항 / 호 / 별표 exist in that version? | invented article (B) |
| L4 `text_correspondence` | Do the quoted words and the stated heading match the source? | right article, wrong content (C) |
| L5 `claim_support` | Does the statement follow from the retrieved text? | correct citation, unsupported conclusion |
| L6 `applicability` | Are the status / subcode / procedure / date conditions met? | E-7 rule applied to E-7-4 (I), visa rule used for a stay procedure, unread transitional clause (F) |
| L7 `conflict_uncertainty` | Does other evidence disagree, or predate a law change? | manual vs statute (J) |

Each layer reports a `LayerOutcome`:

* `pass`: the check ran and succeeded.
* `fail`: the check ran to completion on evidence that was retrieved, and the
  claim did not pass.
* `unavailable`: the check could not run. **This is never evidence of absence.**
* `needs_review`: only a person can settle it, for example a transitional
  clause, office discretion or semantic support.
* `not_applicable`: there was nothing to check, for example no quotation.

`ClaimVerification.overall()` rolls the layers up in this order:
fail → `failed`; else any unavailable → `verification_unavailable`; else any
needs_review → `human_review_required`; else all seven layers present →
`verified`; else `verified_partial`. `highest_verified_layer()` reports how
far the claim got, so an article that exists (L3) is never mistaken for a
supported conclusion (L5).

## 2. Critical invariants

1. **Failure is not absence.** Network failure, timeout, HTTP 429, an HTML or
   empty body, malformed XML/JSON, a missing or rejected credential, or an
   exhausted request budget all map to `LookupStatus.UNAVAILABLE_*` /
   `UPSTREAM_ERROR`. The layer then becomes `unavailable` with
   `verification_unavailable`. Only `LookupStatus.NOT_FOUND` with
   `Coverage.COMPLETE` can produce `source_not_found` or `citation_not_found`.
2. **Partial coverage is not absence.** `NOT_FOUND` from an index that covers
   only current titles yields `unavailable` with `historical_lookup_required`
   (scenario G).
3. **No substitution.** A title that only resembles the cited one, such as a
   prefix, an enforcement decree in place of the Act, or a near spelling, is
   never accepted. Near matches go into `detail` and are never returned as the
   identity.
4. **A verified article does not verify a conclusion.** L5 passes only when a
   deterministic support signal exists (§3, L5). Otherwise the result is
   `needs_review` with `human_review_required`.
5. **Retrieved text is data.** Instruction-like text inside a source never
   changes a verification result. It is flagged on the evidence item
   (`untrusted_instruction_like_text`), and the context builder quotes it as
   data (scenario N).
6. **Conflicts are recorded, never resolved by rank.** Two inconsistent sources
   produce a `ConflictRecord` and `needs_review`. Authority rank is a display
   default only.

## 3. Rules per layer

Inputs: `ClaimInput` (claim text, raw citations, optional quoted text, numbers,
scope, topic/value, asserted version), a `LegalSourceAdapter`, `RelevantDates`,
the anchor (`AnchorKind`) and the question date.

Citations are parsed by `waymaker_ai.legal.citations.parse_citations`. Each
citation is checked separately, and each layer reports the **worst** outcome over
all of a claim's citations. The order from worst to best is fail, unavailable,
needs_review, pass, not_applicable. A claim with no resolvable citation skips
L1–L4 (`not_applicable`) and is judged by L5–L7 on the guidance evidence alone.
If it has neither citations nor guidance evidence, L5 is `fail` with
`claim_unsupported`.

**Blocked layers (decided 2026-10-20).** When a layer cannot produce a result
because an earlier layer did not pass (no identity after L1, no candidate
version after L2, no provision after L3), the dependent layers are still
reported. They carry the **outcome of the earliest blocking layer** with the
code `not_checked`, and a `detail` naming the blocker. So `overall()` reflects
the first real problem. An ambiguous title (L1 `needs_review`) yields
`human_review_required`, not `verification_unavailable`. An unreachable source
(L1 `unavailable`) yields `verification_unavailable`. Layers that do not depend
on the blocked one still run: L5 on guidance-only support, and L7. No layer is
omitted from the result.

### L1 source identity
- The citation names no law and there is no context law (e.g. a bare "제10조"):
  `needs_review`, `source_ambiguous`.
- `resolve_title` failed: `unavailable`, `verification_unavailable`.
- Exactly one identity has an exact compact-text match on its official, former
  or short title: `pass`, `source_verified`.
- More than one identity matches exactly: `needs_review`, `source_ambiguous`.
- `resolve_title` returned **no rows** (`NOT_FOUND`) and coverage is
  `complete`: `fail`, `source_not_found`.
- `resolve_title` returned rows but **none matches exactly**, for example a
  fuzzy upstream search that returned similar titles: `needs_review`,
  `source_ambiguous`. Near matches go in `detail` and are never substituted
  (scenario A). Invariant §2.1 reserves `source_not_found` for an
  authoritative empty answer.
- No exact match and coverage `partial`: `unavailable`,
  `historical_lookup_required`.
- The identity's version that applies on the anchor date is a repeal:
  `fail`, `source_repealed`.

### L2 version identity
Candidate selection follows [06](06-temporal-law-and-source-identity.md):
`select_candidate_versions`.
- `list_versions` failed: `unavailable`, `verification_unavailable`.
- The anchor date is unknown: `needs_review`, `insufficient_context`. The
  resolver never falls back to "the current law".
- The anchor date is earlier than the loaded history, **or the history
  lookup reports `partial` coverage**: `unavailable`,
  `version_history_incomplete`. A version that is missing from a partial
  list could be the one that applies (invariant §2.2).
- The anchors select different versions: `needs_review`,
  `human_review_required`.
- Otherwise there is a candidate *C*. The version the claim actually relies on
  is decided by **version attribution**: the asserted version key if one is
  given, otherwise the version whose provision text contains the quoted text.
  - The attributed version is *C* (or nothing is attributable):
    `pass`, `version_verified`.
  - The attributed version *V* takes effect after both the anchor date and the
    question date: `fail`, `future_not_yet_effective` (scenario E).
  - *V* takes effect after the anchor date but on or before the question date:
    `fail`, `wrong_version` (scenario D: a later amendment applied to a past
    event).
  - *V* is older than *C*: `fail`, `source_outdated`.
- A pending version changes the cited provision, but the claim relies on *C*:
  still `pass`. `detail` names the pending version and its date, so the
  answer can disclose it.

### L3 citation identity
L3 checks the **candidate version *C*** (the version that applies on the anchor
date). If the article exists only in the attributed version, L2 has already
failed.
- `get_provision` failed: `unavailable`, `verification_unavailable`.
- `NOT_FOUND` with complete coverage: `fail`, `citation_not_found`. `detail`
  names any other version that does contain the article, which flags
  renumbering.
- A cited 항 / 호 / 목 is absent from the provision structure:
  `fail`, `citation_not_found` **only when `ProvisionText.structure_complete`
  is true**. Otherwise the result is `unavailable`, `verification_unavailable`:
  a sub-unit missing from a partially parsed article is not evidence that it
  does not exist.
- Otherwise: `pass`, `citation_verified`. Adapters never return heading units
  (조문여부 = 전문).

### L4 text correspondence
- There is no claimed heading and no quoted text: `not_applicable`,
  `not_checked`.
- Claimed heading ≠ source heading after `compact()` normalization:
  `fail`, `text_mismatch`. The match is exact, deliberately with no
  similarity threshold.
- The quoted text is not contained, after `compact()`, in the provision's full
  text for the attributed version: `fail`, `text_mismatch`.
- Otherwise: `pass`, `text_match_verified`.

### L5 claim support
The deterministic support signals are:
(a) the quoted text was verified at L4, and
(b) every numeric expression in `ClaimInput.numbers`, such as "14일", "90일" or
"3년", appears in the evidence text.
- (a) or (b) holds and none of the claim's numbers is missing:
  `pass`, `claim_supported`.
- Some numbers are present and some are missing: `needs_review`,
  `claim_partially_supported`.
- The claim asserts numbers and none appears in the evidence: `fail`,
  `claim_unsupported`.
- The claim has no quotation and no numbers: `needs_review`,
  `human_review_required`. Deterministic code cannot prove semantic support,
  and an LLM judge would only ever be advisory.
- The evidence could not be retrieved: `unavailable`.

### L6 applicability
Compare `ClaimInput.scope` with each evidence item's `Scope`.
- The claim names subcode *S*. The evidence scope lists parent *P* and no
  subcodes, and `all_subcodes_explicit` is false: `needs_review`,
  `subcode_applicability_unproven` (scenario I).
- The evidence scope lists subcodes and *S* is not among them: `fail`,
  `subcode_applicability_unproven`.
- The claim's procedures and the evidence's procedures fall in different
  visa/stay scopes (`procedure_scope`), or are disjoint: `fail`,
  `procedure_scope_mismatch`.
- `get_addenda` failed, returned `NOT_FOUND`, or returned `partial` coverage,
  or the version's `has_transitional_provisions` is `None` (부칙 not read):
  `unavailable`, `verification_unavailable`. A transitional clause cannot be
  ruled out without reading the 부칙.
- An addendum of kind `transitional` or `application` names the cited article,
  or names no article but sets a filing-date rule: `needs_review`,
  `transitional_rule_unresolved` (scenario F).
- The claim needs a date fact (an anchor) that was not provided:
  `needs_review`, `insufficient_context`.
- Otherwise: `pass`, `applicability_established` when a scope was given, and
  `not_applicable` when none was given.

### L7 conflict and uncertainty
For `ClaimInput.topic`, `guidance(topic)` returns operational guidance items.
- The claim has no `topic`: `not_applicable`, `not_checked`. Nothing was
  compared, so the result does not claim "no conflict".
- `guidance` failed: `unavailable`, `verification_unavailable`.
- A guidance item's `value` differs from the claim's `value`: `needs_review`,
  `contradictory_evidence`, plus a `ConflictRecord(kind="value_mismatch")`.
- A guidance item on the topic has an `edition_date` earlier than the
  effective date of the **latest version that changed the cited provision**.
  When `changed_provisions` is unknown, the comparison uses *C*'s effective
  date, which is conservative. Result: `needs_review`,
  `manual_predates_law_change`, plus a `ConflictRecord`.
- When both a value mismatch and a predating edition apply, the layer code is
  `contradictory_evidence`, the more specific finding, and **both**
  `ConflictRecord`s are emitted. This is scenario J:
  the 2026.9 stay manual (2026-09-18) predates the 출입국관리법 and 시행령
  versions in force from 2026-10-02.
- Otherwise: `pass`, `no_conflict_detected`.

## 4. Mapping to existing backend statuses

New vocabulary is used only where the existing vocabulary cannot express the
state. Each status the backend already uses maps onto WLIE as follows.

| Backend status (file) | WLIE |
|---|---|
| `verified` (law_grounding question citations) | L1 `source_verified` + L3 `citation_verified` (L2 unknown: backend pins no version) |
| `failed_verification` + `CITED_LAW_NOT_FOUND` | `source_not_found` **only if** the search succeeded with complete coverage; otherwise `verification_unavailable` |
| `source_linked_unverified` / `ARTICLE_TEXT_NOT_FOUND` | L1 pass, L3 `unavailable` (parser miss) or `citation_not_found` (authoritative miss) |
| `verified_law_evidence` (citation_verifier) | L1 `source_verified` only |
| statute guard `law_not_in_evidence` / `article_not_in_evidence` / `title_mismatch` / `repealed_law_cited` / `unverifiable` | `source_not_found` / `citation_not_found` / `text_mismatch` / `source_repealed` / `verification_unavailable` |
| ranked `scheduled` | L2 `future_not_yet_effective` when relied upon |
| knowledge `VERIFIED_WITH_CONDITIONS` for a subcode from parent facts | L6 `subcode_applicability_unproven` |

## 5. Response contract

For a legally consequential question the model receives a bounded
`EvidencePackage` (`waymaker_ai.legal.evidence_package`) and must answer in a
structured form that separates: question interpretation, relevant facts,
relevant dates and the anchor, potentially applicable provisions (identity,
version key, effective date, official URL), confirmed requirements, conditional
requirements, unresolved factual questions, conflicting evidence, verification
status per claim, and matters for human review. Every claim is passed back
through this gate before display. Public clients receive
`EvidencePackage.public_view()`. Diagnostics such as upstream call counts,
lookup errors and raw source URLs stay in `diagnostics`.

Package bounds are at most 12 evidence items, at most 2,400 characters per
item and at most 20,000 characters in total. Truncation is recorded and never
silent. When verified provisions exist, a full legal corpus is never passed.
