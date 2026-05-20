# Paradiso.ai — Answer Quality Contract (DRAFT)

> **STATUS: DRAFT — documentation-first.**
>
> This document defines the **target contract** for the structure and
> quality of answers produced by the Paradiso.ai assistant. It is a
> specification, not a description of currently shipped behavior.
>
> Producing this contract did **not** change any runtime behavior:
> - Law grounding remains **disabled by default** and is not
>   production-ready.
> - Citation verification is **partial / not fully wired** and must not
>   be described as complete.
> - `index.html`, `ai.html`, the backend, and `visa_data.json` were
>   **not** modified by the PR that introduced this contract.
> - No legal review or attorney review has been performed.
>
> Privacy Policy, Terms of Service, AI Disclaimer, and data
> retention/logging draft notes were introduced in PR #108 under
> `docs/legal/` and remain the canonical disclosure drafts. This
> contract sits alongside them and governs *how an answer is shaped*,
> not *what we promise users legally*.

---

## 1. Purpose

This document defines the **answer quality contract** for Paradiso.ai —
the structured shape, source-handling rules, uncertainty-handling
rules, and high-risk-handling rules that any future implementation of
the assistant's answer pipeline must satisfy before its output is
treated as user-facing.

The goals are:

1. Make it explicit, in advance, what a "good" Paradiso.ai answer
   looks like, so that runtime changes can be validated against a
   contract instead of subjective judgment.
2. Prevent Paradiso.ai from presenting AI-generated text as if it
   were official legal advice, official government interpretation, or
   an administrative determination.
3. Make uncertainty, missing sources, and high-risk topics
   **first-class fields** of the answer object rather than after-the-
   fact UI decorations.
4. Provide a stable interface that the frontend (`ai.html`),
   backend (`/api/ask`), eval harness, and regression tests can all
   agree on once implementation begins.

This contract is **not** a claim that Paradiso.ai currently produces
answers in this shape. It defines the **target**.

## 2. What Paradiso.ai is and is not

Paradiso is an immigration/stay-administration information access
platform. Paradiso.ai is its AI-assisted administrative information
tool.

Paradiso.ai is **not**:

- a lawyer or a law firm,
- an administrative scrivener (행정사 / 行政書士 / similar licensed
  professional),
- a government agency,
- an official decision-maker,
- a substitute for any of the above.

AI answers produced by Paradiso.ai are **informational**. For any
consequential decision (status renewal, change of status, denial risk,
removability, employment authorization, family/dependent
consequences, residency-time counting, fees, deadlines, criminal or
investigative consequences, permanent residence / naturalization
eligibility), the user must confirm with an official source or a
qualified professional before acting.

The contract in this document is written to keep that posture true
in every answer field.

## 3. Structured answer object

Every Paradiso.ai answer that reaches a UI surface MUST conform to the
following object shape. Unsupported or unknown fields MUST be set to
their explicit "missing" / "not_wired" / "unsupported_or_uncertain"
values rather than silently omitted.

The field names below are normative. Locale-specific rendering and
copy live in the UI layer; the contract is about the data.

### 3.1 Top-level fields

| Field                       | Type     | Required | Meaning |
|----------------------------|----------|----------|---------|
| `answer_id`                | string   | yes      | Stable identifier for this answer instance. Used for eval logging, regression, and debug. |
| `locale`                   | string   | yes      | BCP-47-ish locale tag for the rendered answer (e.g. `ko`, `en`, `ja`, `zh`). |
| `user_question`            | string   | yes      | Verbatim user question as received. |
| `interpreted_intent`       | string   | yes      | Short normalized restatement of what the assistant understood the user to be asking. May be coarse. |
| `visa_code_or_topic`       | string \| null | yes  | Detected visa code (e.g. `D-2`, `E-7`, `F-6`) or topic key (e.g. `address_change_notification`). `null` if not confidently detected. |
| `short_answer`             | string   | yes      | One- to three-sentence plain-language answer. MUST NOT contain definitive legal conclusions. |
| `answer_type`              | enum     | yes      | See §3.2. |
| `required_documents`       | object   | yes      | See §3.3. |
| `procedure_steps`          | array    | yes      | Ordered list of plain-language steps. Empty array if not applicable. |
| `fees`                     | array    | yes      | Itemized fee entries. Empty array if not applicable. Each item may carry its own `uncertainty_flag`. |
| `appointment_guidance`     | string \| null | yes  | Plain-language note about appointment booking (e.g. via HiKorea), if applicable. |
| `hikorea_guidance`         | string \| null | yes  | Plain-language note about HiKorea online filing, if applicable. |
| `source_summary`           | string   | yes      | One- to two-sentence summary describing what kind of sources back this answer (e.g. "based on the official D-2 stay manual section and HiKorea procedure page"). MUST NOT overstate verification. |
| `sources`                  | object   | yes      | See §3.4. |
| `law_grounding`            | object   | yes      | See §3.5. |
| `uncertainty_flags`        | array    | yes      | See §3.6. May be empty. |
| `high_risk_flags`          | array    | yes      | See §3.7. May be empty. |
| `user_next_actions`        | array    | yes      | Suggested next actions the user can take (e.g. "check HiKorea", "consult an administrative scrivener", "contact 1345"). |
| `disclaimer_snippet`       | string   | yes      | Locale-appropriate short disclaimer string, pointing back to `docs/legal/AI_DISCLAIMER_DRAFT.md`'s production successor. |
| `last_verified_at`         | string \| null | yes  | ISO-8601 timestamp of the most recent verification of the source data backing this answer, if known. `null` if unknown. |
| `freshness_status`         | enum     | yes      | One of `fresh`, `stale_known`, `stale_unknown`, `not_applicable`. |

### 3.2 `answer_type`

`answer_type` describes the *kind* of answer this is. The pipeline
MUST pick exactly one value.

- `visa_status_info` — general information about a visa/stay status.
- `required_documents` — answer is primarily a document list.
- `procedure_guidance` — answer is primarily a "how to file / where
  to go" workflow.
- `deadline_or_reminder` — answer is about a date, deadline, or
  notification obligation.
- `public_data_lookup` — answer relies primarily on public data
  (e.g. designated medical institution lookups, job-code lookups).
- `legal_grounding_explanation` — answer attempts to explain the
  legal/regulatory basis. While law grounding remains disabled by
  default, this answer_type SHOULD also carry an
  `uncertainty_flags` entry of `not_wired` or `disabled`.
- `unsupported_or_uncertain` — the assistant cannot answer with
  enough confidence; the short answer reflects that.
- `high_risk_defer` — the question falls under §6, and the answer
  intentionally declines to give detailed strategy.

### 3.3 `required_documents`

`required_documents` is an object that buckets documents by
status. Every bucket is an array of document entries; entries SHOULD
include a stable key, a human label, and any per-document
`uncertainty_flag`.

Buckets:

- `common` — documents commonly required regardless of fine sub-
  type.
- `required` — documents required for this specific request.
- `conditional` — documents required only under certain conditions
  (e.g. "only if dependent is included").
- `additional` — documents that may be requested at the officer's
  discretion or in non-standard cases.
- `missing_or_unverified` — documents the assistant suspects may be
  relevant but for which it does not have a verified source. This
  bucket MUST be surfaced; it is the safety valve against hidden
  gaps.

### 3.4 `sources`

`sources` is an object grouping the references behind the answer by
authority class. Each entry SHOULD include a title, an optional URL,
and a per-source verification status (see §5).

Buckets, in the order they should appear:

- `official_manual_sources` — official visa/stay civil manuals
  (e.g. Ministry of Justice civil manuals, regional immigration
  office published manuals).
- `official_government_sources` — official government / HiKorea
  guidance pages and notices.
- `public_data_sources` — public datasets used by Paradiso (e.g.
  designated medical institutions, job-code lists).
- `legal_sources` — statutory or regulatory text. Note that while
  law grounding is disabled by default, this bucket is typically
  empty or flagged.
- `internal_normalized_data_sources` — Paradiso's own normalized
  data such as `visa_data.json`. This is *internal*; it is not a
  primary legal source.

### 3.5 `law_grounding`

`law_grounding` is an object describing what happened with respect to
law-grounding for this answer. It MUST be present even when grounding
is disabled.

Fields:

- `mode` — one of `disabled`, `shadow`, `enabled`. Default is
  `disabled`. This contract does not authorize switching the
  production default.
- `attempted` — boolean. Was law grounding attempted on this
  request?
- `used` — boolean. Did law grounding actually contribute to the
  short answer text?
- `warnings` — array of plain-language warnings produced by the
  grounding subsystem (e.g. "law text retrieved but citation not
  verified").
- `citation_verification_status` — one of the states in §5.

When `mode == "disabled"`, `attempted` and `used` MUST both be
`false`, and `citation_verification_status` MUST be `disabled`.

### 3.6 `uncertainty_flags`

Each entry is one of the uncertainty states in §4, with an optional
free-text reason. The pipeline MUST add an `uncertainty_flag` whenever
it cannot fully back a claim with a verified source. The UI MUST
render uncertainty visibly; "no flag = looks confident" is the
default user reading.

### 3.7 `high_risk_flags`

Each entry is one of the high-risk categories in §6, with an optional
short reason. When `high_risk_flags` is non-empty, `answer_type` MUST
be `high_risk_defer` unless the answer is purely a low-risk factual
lookup that *touches* a high-risk topic without giving strategy.

## 4. Uncertainty states

Every answer-level uncertainty entry, and every per-document /
per-source uncertainty entry, MUST use one of the following states:

- `verified` — backed by a verified official source within freshness
  tolerance.
- `source_supported` — backed by a source, but the source itself has
  not been re-verified within the freshness window.
- `partially_supported` — only part of the claim is backed by a
  source.
- `missing_source` — no source is available for this claim in
  Paradiso's data.
- `outdated_or_unknown` — source exists but is known to be (or may
  be) out of date.
- `conflicting_sources` — multiple sources disagree; the assistant
  surfaces the conflict instead of resolving it silently.
- `not_wired` — the relevant verification path exists in design but
  is not wired up in code (e.g. law grounding pipeline). Used for
  honest disclosure rather than as an excuse.
- `high_risk_defer` — the question was intentionally not answered in
  depth because §6 applied.

`verified` MUST NOT be used unless an explicit verification step has
been performed. The default for AI-generated summary text without an
explicit verification step is `source_supported` at best.

## 5. Citation verification states

`law_grounding.citation_verification_status` and any per-source
verification status MUST use one of:

- `not_applicable` — the answer does not rely on a legal citation.
- `disabled` — law grounding mode is `disabled`; no citation
  verification was attempted.
- `not_wired` — citation verification path is not wired in this
  build.
- `extracted_only` — a citation string was extracted from a source
  but its identity / current validity was not confirmed.
- `source_linked_unverified` — a citation has a link to a source,
  but the link target was not re-fetched or content-checked.
- `verified_by_source` — citation was re-fetched and confirmed
  against the source within freshness tolerance.
- `failed_verification` — verification was attempted and failed.

`verified_by_source` MUST NOT be reported unless an actual
re-fetch / content check happened. While citation verification
remains partial / not fully wired, the contract expects
`disabled`, `not_wired`, `extracted_only`, or
`source_linked_unverified` in nearly all production answers.

## 6. Source hierarchy

When multiple sources are available, the assistant SHOULD prefer
sources in the following order:

1. official current law / regulation
2. official government / HiKorea guidance
3. official visa/stay civil manuals
4. public data sources
5. Paradiso internal normalized data
6. AI-generated summary

Caveat: in practice, day-to-day administrative guidance — exact
document lists, exact office workflows, exact HiKorea forms — often
lives in manuals and official portals rather than in statutory text.
The contract treats manuals and official portals as **authoritative
for procedure**, while statutory text remains authoritative for the
*legal basis* of that procedure. The assistant MUST NOT claim a
statutory basis it has not actually retrieved.

When the assistant can only fall back to AI-generated summary text
(level 6), `uncertainty_flags` MUST include at least
`missing_source` or `outdated_or_unknown`.

## 7. High-risk handling (summary)

See `HIGH_RISK_ESCALATION_RULES.md` for the canonical list and
behavior. For any question matching a §6 high-risk category, the
contract requires:

- a **short informational answer only**, no detailed legal strategy;
- **no definitive legal determination** ("you will / will not be
  deported", "this will be approved", "this is illegal");
- a clear recommendation to contact the relevant **official agency**
  or a **qualified professional**;
- explicit `high_risk_flags` and matching `uncertainty_flags`;
- `answer_type = high_risk_defer` unless the touch is incidental.

## 8. Locale and copy

- `locale` is set by the request context; the assistant does not
  invent a locale.
- Disclaimer snippet copy is owned by `docs/legal/` (drafts from
  PR #108). The contract here only requires that *some* disclaimer
  snippet is attached to every answer; it does not define the exact
  wording.

## 9. What this contract does NOT do

- It does **not** turn on law grounding.
- It does **not** claim citation verification is complete.
- It does **not** claim legal review has been performed.
- It does **not** modify `ai.html`, `index.html`, the backend, or
  `visa_data.json`.
- It does **not** define UI components; only the answer object that
  a future UI will render.
- It does **not** replace the disclaimer / privacy / terms drafts in
  `docs/legal/`. Those remain the canonical user-facing disclosures.

## 10. Implementation roadmap

Implementation is deliberately staged so that runtime behavior does
not change until the schema and rules are stable.

- **Phase A — docs / schema only.** This PR. Define the contract,
  citation/uncertainty schema, high-risk rules, and answer
  examples. No code changes.
- **Phase B — backend schema utilities.** Add typed constructors /
  validators for the answer object in the backend, without changing
  the existing `/api/ask` response shape that the frontend consumes.
  Internal-only.
- **Phase C — `/api/ask` debug field.** Surface the structured
  answer object as an additional *debug* field on `/api/ask`
  responses, gated so it does not change current UI behavior.
- **Phase D — UI answer card rendering.** Update `ai.html` to
  render the structured answer card, including visible uncertainty
  and high-risk treatment. UI change is opt-in / progressive.
- **Phase E — regression tests.** Add eval / regression coverage
  using the answer examples in `ANSWER_EXAMPLES.md` plus the golden
  eval set. Treat contract violations as test failures.

Each phase is a separate PR. No phase implies the next is approved.

## 11. Related documents

- `docs/ai/CITATION_AND_UNCERTAINTY_SCHEMA.md`
- `docs/ai/HIGH_RISK_ESCALATION_RULES.md`
- `docs/ai/ANSWER_EXAMPLES.md`
- `docs/legal/AI_DISCLAIMER_DRAFT.md`
- `docs/legal/PRIVACY_POLICY_DRAFT.md`
- `docs/legal/TERMS_OF_SERVICE_DRAFT.md`
- `docs/legal/DATA_RETENTION_AND_LOGGING_NOTES.md`
