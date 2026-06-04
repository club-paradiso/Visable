# AI Answer Pipeline — Backend/Frontend Contract & Rendering (2026-05)

This note documents the contract between the Paradiso backend `/api/ask`
response and the ai.html answer renderer, and the defensive normalization /
error-classification work done to repair a production rendering regression.

It is a companion to:

- `docs/data/AI_ANSWER_SHELL_SOURCE_SEMANTICS_2026_05.md` (chip / source-panel semantics)
- `docs/data/LIVE_LAW_PARSING_AND_FALLBACK_MEMO_QUALITY_2026_05.md` (law parsing + fallback memo)
- `docs/ai/CITATION_AND_UNCERTAINTY_SCHEMA.md` (disclosure state classes)

## 1. Observed production bug

After PR #271, a user asked (Korean):

> "H-1 외국인등록은 언제 해야 하나요?" — *When do I have to do H-1 foreigner registration?*

The frontend showed:

- `답변 생성 오류` (Answer error)
- `통신 오류` (Network error)

Developer diagnostics reported:

- `Can't find variable: errorType`

Crucially, this was **not** a backend `/api/ask` failure. The backend returned
a usable response; the answer card crashed while rendering it.

## 2. Root cause

`renderGroundingSourcePanel()` in ai.html built a developer-diagnostics block
that referenced `errorType`:

```js
let parserFailed = PARSE_FAIL.indexOf(topParser) !== -1
    || errorType === 'LAW_API_PARSE_ERROR'
    || errorType === 'LAW_API_BAD_RESPONSE';
```

But `errorType` was only ever declared inside the sibling helpers
`sourcePanelCopyForState()` and `lawSourcePanelMessage()` — never inside
`renderGroundingSourcePanel()` itself. Whenever the source panel had at least
one row to render (any law-grounding-attempted / citation / manual-source
case), evaluating that line threw `ReferenceError: errorType`.

The exception propagated out of `appendAiAnswer()`, was caught by `sendAi()`'s
generic `catch`, and was handed to `appendAiError()`. Because the thrown error
carried no HTTP `status` and no `payload` (the fetch had actually *succeeded*),
the error card fell back to its "no status" branch and displayed **`통신 오류`
(Network error)** — a misleading label for what was really a frontend render
crash.

## 3. Broader issue

The single missing declaration was a symptom of a missing contract:

- Multiple renderers (`renderGroundingSourcePanel`, `sourcePanelCopyForState`,
  `lawSourcePanelMessage`, `buildGroundingNote`) each assumed the `/api/ask`
  metadata existed and had a specific shape, reading fields directly.
- A missing, `null`, renamed, or wrong-typed field could produce a
  `ReferenceError` / `TypeError` that crashed the whole answer card.
- The client error path could not distinguish a *render* failure from a
  *network* failure, so a frontend bug looked like a connectivity problem.

The fix repairs the contract defensively rather than patching one variable.

## 4. Metadata contract — stable field names and types

The backend `AskResponse` (pydantic) is the source of truth. Fields the source
panel / answer renderer rely on, with their stable types:

| Field | Type | Notes |
|---|---|---|
| `answer` | string | model/fallback answer text |
| `copy_safe_answer` | string | sanitized, diagnostics-free answer for the clipboard |
| `grounding_used` | bool | |
| `grounding_sources` | array | manual / procedure sources |
| `law_grounding_attempted` / `law_grounding_used` | bool | |
| `law_grounding_status` | string | `not_attempted` / `disabled` / `unavailable` / `used` |
| `law_grounding_warnings` | array | raw codes (e.g. `SOURCE_UNAVAILABLE`) — diagnostics only |
| `law_lookup_error_type` | string | coarse error code, e.g. `LAW_API_PARSE_ERROR` |
| `law_grounding_error` | string | |
| `parser_status` | string | top-level parser status |
| `parser_status_by_family` | object | per source-family parser status |
| `source_family_statuses` | object | per source-family lookup status |
| `law_sources` | array | sanitized supporting legal sources (no OC/keys) |
| `citation_verification` | object \| null | `{ status, warnings }` |
| `legal_analysis` | object | structured analysis (PR #265/#266) |
| `legal_analysis_exists` | bool | |
| `legal_issue_types` / `proposed_activity_type` | array | |
| `immigration_facts` | object | |
| `answer_quality_mode` | string | `source_confirmed` … `generic_advisory` |
| `answer_certainty_level` | string | `direct` / `contextual` / `limited` / `unavailable` |
| `source_panel_state` | string | e.g. `structured_fallback_available` |
| `source_panel_label_key` | string | |
| `deterministic_fallback_answer_used` | bool | |
| `fallback_answer_kind` | string | e.g. `legal_analysis_preparation_note` |
| `related_statuses_not_sources` | array | comparison statuses, **never** a proving source |

**Backend change in this PR:** `parser_status`, `response_shape_hint`,
`source_panel_status` were previously passed to `AskResponse(...)` as undeclared
kwargs and silently dropped (pydantic `extra="ignore"`). They are now declared
fields. `source_family_statuses` and `parser_status_by_family` were never
projected onto the response at all and are now wired through from the law
evidence pack, so the per-family developer-diagnostics rows actually receive
data. All are coarse, non-secret status strings/objects — no URLs, OC values,
or API keys.

## 5. Frontend normalization strategy

`ai.html` adds `normalizeAnswerMetadata(metadata)`. It returns a new object
that:

- **preserves every field** the backend sent (so richer/optional fields keep
  working), and
- **coerces the contract fields to a stable type with a safe default**:
  arrays → `[]`, objects → `{}`, strings → `''`, booleans → `false`,
  `citation_verification` → `null`.

Every renderer routes its input through it:

- `renderGroundingSourcePanel()` — and it now also declares its own
  `const errorType = String(safe.law_lookup_error_type || safe.law_grounding_error || '').toUpperCase();`
- `sourcePanelCopyForState()`
- `lawSourcePanelMessage()`
- `buildGroundingNote()`
- `appendAiAnswer()` (copy-safe answer selection)

Result: **no renderer assumes metadata exists or has a specific shape.** A
missing/renamed/mistyped field can no longer throw.

## 6. Error classification — network vs backend HTTP vs provider vs render

`classifyAskError(error)` returns one of:

| Class | Meaning | Trigger |
|---|---|---|
| `network` | fetch rejected / no HTTP response | `fetch` threw, no `status` |
| `backend_http` | server returned a non-OK status | `response.ok === false` |
| `provider` | AI provider outage / upstream error | detail has `provider_unavailable` / `openrouter_*` / `upstream` |
| `frontend_render` | exception thrown while rendering a successful response | `appendAiAnswer()` threw |

`sendAi()` now wraps `appendAiAnswer()` in its own `try/catch`; a render
exception is tagged `frontend_render` and reported as such — it can no longer be
mislabeled as `통신 오류` / Network error. The error-card badge and the developer
diagnostics reflect the class, and for a render crash the diagnostics carry a
structured `frontend_render_error` record (`{ error_class, message, location }`)
instead of a misleading payload dump.

Scary stack traces are not shown by default; the developer-diagnostics
`<details>` block stays collapsed, and the human-readable classification line
comes first.

## 7. Source panel diagnostics behavior

`renderGroundingSourcePanel()` is safe for all metadata combinations:
warnings absent/empty, `source_family_statuses` / `parser_status_by_family`
absent, `law_lookup_error_type` / `law_grounding_error` absent,
`citation_verification` absent, `legal_analysis` absent, unknown
`source_panel_state`, and malformed-but-non-null metadata.

Guarantees:

- No `ReferenceError` / `TypeError`; `"Can't find variable"` never reaches a
  user-facing surface.
- Raw codes (`SOURCE_UNAVAILABLE`, `LAW_API_BAD_RESPONSE`, …) stay inside the
  collapsed developer-diagnostics block, after the human-readable explanation,
  never as a default panel label.
- The copy-answer payload carries only `copy_safe_answer` (and source lines) —
  never developer diagnostics.

## 8. Tests added

- `scripts/check_ai_shell_semantics.js` (Part F) — static + behavioral:
  - `renderGroundingSourcePanel()` must declare `errorType` (and
    `topParser`/`familyStatuses`/`parserByFamily`/`PARSE_FAIL`/`parserFailed`)
    locally and must call `normalizeAnswerMetadata()`.
  - `normalizeAnswerMetadata()` must default the contract fields.
  - developer diagnostics not open by default; raw codes after the
    human-readable line; copy payload free of diagnostics.
  - `classifyAskError` + four error classes + `frontend_render_error` wired.
  - assembles and runs the real `renderGroundingSourcePanel` against empty /
    null / absent-field / malformed metadata in 4 languages — none may throw.
- `backend/tests/test_ai_answer_pipeline_contract.py` — static frontend
  assertions, the node checker, and backend type-stability of the new fields,
  plus copy-safe / provider-error-detail checks.
- `backend/tests/test_legal_analysis_deterministic_fallback.py` (existing) —
  H-1 registration, G-1-5 study, E-7→F-2-99, C-3 paid-work content guarantees
  remain intact.
- `scripts/smoke_ai_live_quality.py` (Part H) — static signals
  `answer_rendering_contract_ok`, `frontend_contract_risk`,
  `possible_free_variable_errorType`, `missing_source_panel_metadata_defaults`,
  `raw_code_default_ui_leak`, `copy_safe_answer_diagnostic_leak`, plus the H-1 /
  E-7 / G-1-5 / F-2-99 / C-3 sample questions.

## 9. Risk disposition and operator verification

These limits are **not PR blockers**, because fixing them in this rendering-contract
PR would either require live external credentials, change the product safety
model, or expand the source-adapter scope beyond the bug being fixed.

| Risk | Status | Handling |
|---|---|---|
| Live Open Law API returns no direct evidence | Expected product limit | Keep `direct/contextual/limited` states honest; do not invent citations |
| Deterministic fallback is not a full LLM memo | Intentional safety boundary | Keep it as a preparation note; use live LLM only when provider succeeds |
| Source-family support is incremental | Follow-up roadmap | Add legal interpretation / appeal / precedent adapters separately |
| Live-provider wording is not exercised in CI | Environment limit | Use mocked contract tests in CI and post-merge live smoke in production |

Operator post-merge smoke checklist:

```bash
curl -sS https://web-production-14f9a.up.railway.app/health | python3 -m json.tool
BACKEND_URL="https://web-production-14f9a.up.railway.app" python3 scripts/smoke_ai_live_quality.py --json
```

Then open:

```text
https://lucanomics.github.io/Paradiso/?v=answer-contract-272
```

Manual questions:

```text
H-1 외국인등록은 언제 해야 하나요?
E-7에서 F-2-99로 변경 후 부업을 하면 예전 근무처 신고의무가 남나요?
G-1-5로 체류 중인데 대학교에 등록하거나 청강하거나 여름 계절학기를 수강할 수 있나요?
Can I change status to F-2-99?
C-3 단기방문으로 paid work를 할 수 있나요?
```

Pass criteria:

- no `Can't find variable` / frontend render crash;
- render failures, if any, are labeled `frontend_render`, not `network`;
- raw diagnostic codes are not default source-panel labels;
- copy-safe answer does not include developer diagnostics;
- H-1 registration does not mention school enrollment / credits / D-2 / D-4;
- G-1-5 Korean fallback has no snake_case labels and no English questions;
- E-7 to F-2-99 answer remains confidence-gated.

## 10. Known limitations

- The live Open Law API can still return **no direct evidence**; the panel then
  honestly reports limited/contextual authority rather than inventing citations.
- The deterministic fallback is a **preparation note**, not a full LLM legal
  memo; it states what to confirm with 1345 / HiKorea / the competent office.
- Source-family support remains **incremental** — not every statute /
  enforcement-decree / administrative-rule family is parsed yet, so per-family
  diagnostics may show `no_results` / `unsupported` (normal "nothing to cite"
  outcomes, **not** parser failures).
- Live-provider answer wording is not asserted as a hard CI gate because the
  provider response is nondeterministic and requires external credentials. CI
  instead checks the deterministic backend/frontend contract; live wording is
  verified by post-merge smoke.

## 11. Safety note

This work does **not** enable Ollama, change OpenRouter model policy, change law
API credentials, invent official citations, hide real source limitations, or
modify visa/manual data. It only repairs the rendering contract so honest
backend states are displayed safely. Final outcomes must always be confirmed
with 1345, HiKorea, or the competent immigration office.
