# Paradiso.ai — Citation and Uncertainty Schema (DRAFT)

> **STATUS: DRAFT — documentation-first.**
>
> This document is the normative schema reference for the
> `sources`, `law_grounding`, `uncertainty_flags`, and per-document
> uncertainty fields described in
> `docs/ai/ANSWER_QUALITY_CONTRACT.md`.
>
> No runtime behavior changes. Law grounding remains **disabled by
> default**. Citation verification remains **partial / not fully
> wired**. No legal review has been performed.

---

## 1. Scope

This schema covers:

- the shape of a single **source entry** referenced by an answer,
- the shape of the answer-level **`law_grounding`** object,
- the **uncertainty states** that may decorate the answer as a whole
  or any individual claim / document / source,
- the **citation verification states** that describe how thoroughly a
  citation was checked.

The schema is **target state**. It is not a description of what is
implemented today.

## 2. Source entry

Each entry in the buckets of `sources` (see Contract §3.4) SHOULD use
the following shape:

| Field                     | Type           | Required | Meaning |
|--------------------------|----------------|----------|---------|
| `source_id`              | string         | yes      | Stable identifier within Paradiso (e.g. `manual.d2.extension.v2025-01`). |
| `bucket`                 | enum           | yes      | One of `official_manual_sources`, `official_government_sources`, `public_data_sources`, `legal_sources`, `internal_normalized_data_sources`. |
| `title`                  | string         | yes      | Human-readable title. |
| `publisher`              | string \| null | yes      | E.g. "Ministry of Justice", "HiKorea", "Paradiso internal". |
| `url`                    | string \| null | yes      | Canonical URL if applicable. MUST NOT be invented. |
| `locale`                 | string \| null | yes      | Locale of the source text. |
| `retrieved_at`           | string \| null | yes      | ISO-8601 timestamp of last successful retrieval, if known. |
| `verification_status`    | enum           | yes      | See §4. |
| `verification_notes`     | string \| null | no       | Short reason if verification failed or is incomplete. |
| `uncertainty_flag`       | enum \| null   | no       | If this source contributes to an uncertain claim, the relevant flag from §3. |

A source MUST NOT be fabricated. If Paradiso does not actually hold a
source for a claim, the answer MUST reflect that via
`missing_source` instead of inventing a citation.

## 3. Uncertainty states

`uncertainty_flags` is an array of entries with this shape:

| Field      | Type           | Required | Meaning |
|-----------|----------------|----------|---------|
| `state`   | enum (below)   | yes      | One of the values listed below. |
| `scope`   | enum           | yes      | `answer`, `claim`, `document`, `source`, `fee`, `step`. |
| `target`  | string \| null | no       | Identifier of the scoped item (e.g. document key, step index). |
| `reason`  | string \| null | no       | Short plain-language reason. |

### 3.1 Allowed states

- `verified` — Source-checked within freshness tolerance, and the
  claim/document/source matches the source content.
- `source_supported` — A source exists and supports the claim, but
  was not re-verified within the current freshness window.
- `partially_supported` — Only part of the claim is supported by a
  source; the remainder is inferred or AI-summarized.
- `missing_source` — No usable source. The claim is best-effort AI
  reasoning.
- `outdated_or_unknown` — Source exists but is known to be (or may
  be) out of date; or its freshness cannot be determined.
- `conflicting_sources` — Multiple sources disagree. The assistant
  MUST surface the conflict rather than picking silently.
- `not_wired` — A verification path exists in design (e.g. law
  grounding) but is not wired in the running system.
- `high_risk_defer` — The claim was intentionally not produced in
  detail because the question fell under high-risk rules
  (see `HIGH_RISK_ESCALATION_RULES.md`).

### 3.2 Defaults and prohibitions

- The default state for an AI-summarized claim with no explicit
  verification step is **at best** `source_supported`.
- `verified` MUST NOT be applied without an explicit verification
  step having been executed for that scope.
- A claim with `missing_source` MUST be surfaced in the UI as
  uncertain. It MUST NOT appear in the short answer as if it were a
  confident statement.
- `conflicting_sources` MUST NOT be quietly collapsed into one of
  the conflicting answers; the conflict itself is the answer.

## 4. Citation verification states

These states apply both to `law_grounding.citation_verification_status`
and to per-source `verification_status`.

- `not_applicable` — The answer does not rely on a legal citation,
  or the source does not require verification (e.g. internal
  normalized data identified as internal).
- `disabled` — Law grounding mode is `disabled`; no verification was
  attempted. This is the **current default** for production.
- `not_wired` — A verification path is designed but not wired. The
  assistant MUST be honest about this rather than reporting
  `verified_by_source`.
- `extracted_only` — A citation string was pulled from a source, but
  its identity / current validity was not confirmed.
- `source_linked_unverified` — A citation links to a source URL, but
  the link target was not re-fetched or content-checked in this
  request.
- `verified_by_source` — The citation was re-fetched and confirmed
  against the source within freshness tolerance. MUST NOT be used
  while verification remains partial / not wired.
- `failed_verification` — Verification was attempted and failed.
  This SHOULD trigger an `uncertainty_flag` of
  `outdated_or_unknown` or `conflicting_sources` as appropriate.

## 5. `law_grounding` object

`law_grounding` MUST always be present on an answer, even when
grounding is off.

```jsonc
{
  "mode": "disabled",                   // disabled | shadow | enabled
  "attempted": false,
  "used": false,
  "warnings": [],
  "citation_verification_status": "disabled"
}
```

Invariants:

- If `mode == "disabled"` then `attempted == false`, `used == false`,
  and `citation_verification_status == "disabled"`.
- If `mode == "shadow"` then `used == false`. `attempted` MAY be
  `true`. `citation_verification_status` MUST be one of
  `not_wired`, `extracted_only`, `source_linked_unverified`,
  `failed_verification`, or `disabled`.
- `mode == "enabled"` MUST NOT be set in production until both law
  grounding and citation verification are reviewed and the
  contract's regression tests pass.

## 6. Freshness

`last_verified_at` and `freshness_status` (Contract §3.1) interact
with verification states as follows:

- `freshness_status = fresh` — `last_verified_at` is within the
  freshness window defined by the source class.
- `freshness_status = stale_known` — `last_verified_at` is older
  than the window; the answer SHOULD carry
  `outdated_or_unknown`.
- `freshness_status = stale_unknown` — `last_verified_at` is
  `null`; the answer SHOULD carry `outdated_or_unknown` unless the
  answer type is `not_applicable`-friendly (e.g. pure procedure
  explanation independent of dated data).
- `freshness_status = not_applicable` — the claim does not have a
  meaningful freshness concept.

Specific freshness windows are intentionally not pinned here.
They will be defined in Phase B alongside backend schema utilities.

## 7. Per-document uncertainty

Inside `required_documents`, each entry SHOULD support its own
`uncertainty_flag` field using §3 states. Document-level uncertainty
is especially important because a missing-but-unmentioned document is
one of the higher-impact failure modes for an administrative
assistant.

Documents in the `missing_or_unverified` bucket implicitly carry
`missing_source` or `outdated_or_unknown` at minimum.

## 8. Examples

Concrete examples of how these states are applied to specific
questions are in `docs/ai/ANSWER_EXAMPLES.md`. The examples there
are normative for "how to use the schema"; this document is
normative for "what the schema is".
