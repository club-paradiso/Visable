# Generalized Legal Grounding & Source-Status Handling (2026-06)

## Problem

Paradiso already has evidence-backed **answer synthesis gates** and
answer-shape quality checks (merged earlier). Those gates decide *how strongly*
an answer is allowed to speak, but they can only be as good as the official
source context they receive. Two failure modes remained:

1. Law/statute API results did not always meaningfully improve answer
   generation — snippets were retrieved but not reliably injected, or a law
   failure quietly erased otherwise-usable manual evidence.
2. Raw internal diagnostics (`LAW_API_BAD_RESPONSE`, `SOURCE_UNAVAILABLE`,
   `bad_response`, `unsupported`, `not_attempted`, per-family raw status dumps)
   could surface near user-facing output.

So the answer gates needed a **reliable, generalized official-source grounding
layer** beneath them.

## Why this is not case-by-case

The grounding layer is keyed by **procedure / action / legal-issue / source
family**, never by individual visa codes. There is no per-visa branch for H-1,
G-1-5, D-2, C-3, F-6, E-7, etc. Those codes appear only as **regression
fixtures** that exercise the generalized pipeline and assert structural /
public-safe properties — they cannot become production legal branches.

A query about "documents for an extension" is routed the same way whether the
status is A-1 or F-6; the answer policy is selected from the detected
*procedure type*, not the code.

## Query → source-family pipeline

```
question
  → query understanding        (classify_query_for_grounding)
  → status/code extraction      (extract_immigration_facts)
  → procedure classification    (legal issue → procedure type)
  → activity/action classification
  → source-family retrieval plan (route_source_families / evidence_query_plan)
  → official-source fetch        (manual + law adapters; single network seam)
  → source normalization         (normalize_* → stable internal shape)
  → grounding-context assembly   (build_official_grounding_context)
  → answer policy / answer-shape gate (existing, unchanged)
  → final answer
  → public-safe source status    (project_public_source_status)
```

`classify_query_for_grounding` structures the query (status code/family,
procedure type, action/activity list, legal-issue types, and *material missing
facts*) **without deciding the final legal answer** (`doesNotDecideFinalAnswer:
True`). It only shapes retrieval and answer policy.

The existing answer synthesis gates remain in place and are **integrated, not
replaced**: the grounding context is injected as additional evidence so the
gates benefit from richer, normalized source context.

## Source normalization behavior

Every source attempt — manual or law, JSON/XML/HTML/text/empty/HTTP-error —
normalizes to one stable internal structure with both an internal `status`
(`available` / `temporarily_unavailable` / `not_configured` / `not_relevant` /
`error`) and a `publicStatus` (`available` / `temporarily_unavailable` /
`unavailable`), plus optional title/url/versionDate/snippets and a developer-only
`internalCode`.

Key behaviors:

- A failed source family **does not erase** other available sources. A malformed
  live-law response still leaves manual snippets intact and grounded.
- The `manual` family is normalized **once**, from real manual evidence. The
  law-side normalizer skips the `manual` status signal so it can no longer emit
  an empty duplicate `manual: available` row (prompt noise + a meaningless
  public chip). *(Fixed in this PR.)*

## Law API parser hardening

`normalize_http_source_response` accepts any response shape and never throws
into the answer path:

| Input                         | Internal status          | Internal code        |
|-------------------------------|--------------------------|----------------------|
| Valid JSON with content       | `available`              | —                    |
| Valid JSON, unrecognized      | `temporarily_unavailable`| `UNEXPECTED_SCHEMA`  |
| Malformed JSON                | `error`                  | `MALFORMED_JSON`     |
| Valid XML with text           | `available`              | —                    |
| Malformed XML                 | `error`                  | `MALFORMED_XML`      |
| HTML page                     | `error`                  | `HTML_RESPONSE`      |
| Plain text                    | `error`                  | `PLAIN_TEXT_RESPONSE`|
| Empty body                    | `temporarily_unavailable`| `EMPTY_BODY`         |
| HTTP ≥ 400                    | `error`                  | `HTTP_ERROR`         |

Raw bodies and stack traces are never propagated to the user; detailed codes
are preserved only for developer logs / the opt-in diagnostics panel.

## Grounding-context assembly

`build_official_grounding_context` + `render_grounding_context_for_prompt`
produce a compact LLM context block containing: query classification, procedure
type, source family + title + version/date, short excerpts, a reliability
label, availability status, and explicit **uncertainty boundaries**. The LLM is
instructed to use official snippets when available, not invent unsupported
requirements, distinguish confirmed rules from procedural caution, and treat
1345/HiKorea/the office as final confirmation rather than a substitute for
analysis. The rendered prompt contains **no raw diagnostic codes**.

## User-facing source-status policy

`project_public_source_status` emits only compact, human-readable labels:

- 공식 매뉴얼 확인됨 / Official manual checked
- 실시간 법령 확인됨 / Live law checked
- 실시간 법령 일시 확인 불가 / Live law temporarily unavailable
- 저장된 공식 출처 기준 답변 / Stored official source used
- 출처 제한으로 일반 안내만 가능 / Only limited general guidance available
- 관할기관 최종 확인 필요 / Final confirmation needed from the authority

The frontend renders these labels as chips. Raw developer codes
(`LAW_API_BAD_RESPONSE`, `SOURCE_UNAVAILABLE`, `bad_response`, `unsupported`,
`not_attempted`, per-family raw status) remain in logs and behind an explicit,
opt-in **"developer diagnostics"** `<details>` block — never in the normal
answer or the default source panel.

## Tests added

`backend/tests/test_generalized_source_grounding_regression.py`:

- **Malformed-law degradation** — a `LAW_API_BAD_RESPONSE` law response keeps
  the manual snippet, shows public-safe labels, and leaks no banned code into
  the public projection or the LLM prompt; developer diagnostics still retain
  the raw code.
- **No duplicate empty manual** — regression for the law-side `manual` skip.
- **Parser schema** — unexpected-schema JSON → `UNEXPECTED_SCHEMA`/no_results;
  all response shapes normalize without raising.
- **Public projection safety** — mixed error families project to clean
  KO/EN labels with no banned tokens.
- **Answer policy shape** — procedure-driven sections (eligibility/activity vs
  document-requirement); identical policy across unrelated visa codes.
- **Concrete-visa fixtures** (H-1, G-1-5, D-2, C-3, F-6, E-7) — generalized,
  public-safe assertions only.
- **Grounding context assembly** — partial coverage records uncertainty and
  carries version/date metadata, with no raw codes.

These extend the existing `test_source_grounding_pipeline.py` coverage and use
fixtures/mocks only (no live network; not CI-mandatory on external APIs).

## Known limitations

- Direct official evidence may still not exist for every scenario; the answer
  then degrades to manual-grounded or limited guidance, never fabrication.
- The live law API can fail or return unexpected shapes; this is handled, but
  it means live-law citations are best-effort.
- Final agency determination (1345 / HiKorea / competent office) remains
  required — the system structures and grounds, it does not adjudicate.

## Safety note

The grounding layer never invents legal rules, never treats unofficial blogs /
law-firm pages / AI summaries as authority, and never marks unverified data as
verified. It only normalizes, routes, and presents official-source results, and
degrades to honest "limited guidance" when sources are unavailable.

## Deferred follow-ups (out of scope for this PR)

1. **Manual refresh** — parse/index the updated 2026-06 stay-manual PDF/HWP
   source content into structured snippets (the files are stored; deeper text
   extraction is deferred).
2. **Browser-mode UX/UI cleanup** — broader source-panel/answer-card visual
   cleanup.
3. **Static visa-search rendering contract** — formalize the static
   visa-search rendering surface.
4. **구비서류 / 절차별 안내 duplicate-surface cleanup** — de-duplicate the
   document/procedure surfaces.
