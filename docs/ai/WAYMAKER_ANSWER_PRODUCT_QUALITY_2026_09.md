# Waymaker answer product quality — 2026-09 repair

Scope: the Waymaker (`ai.html`) answer experience for simple, source-confirmed
document questions, the public `/api/ask` contract, and how provider/model
infrastructure is kept out of the ordinary user experience. This is a
rendering / contract / routing-UX repair. It is **not** a legal revalidation
and it does not change the model policy (`backend/services/model_policy.py`).

## Observed failure

Query `D-2 연장시 필수 서류` (Fast selected) rendered:

```
Waymaker by Paradiso 안내
OpenRouter · nvidia/nemotron-3-ultra-550b-a55b:free
…(외국인체류 안내매뉴얼 2026.6; source file 2026-06-23, pp. 43-44)
### 필수 서류
…
BASIS / SOURCE / DISABLED · 법령 인용 검증: 기능 꺼짐
```

## Root causes

| Symptom | Cause |
|---|---|
| `source file 2026-06-23` in prose | `_build_grounded_prompt()` built `source_date_label = f"{source_date}; source file {source_revision_date}"` and told the model to cite exactly that. `source_grounding.normalize_manual_source_attempts()` also used `source_revision_date` as the manual's public `versionDate`. |
| Raw `###` | `formatAnswerText()` handled only bullets and `**bold**`; headings were escaped and printed literally. The index.html AI modal only converted newlines. |
| Free-form checklist | The whole manual excerpt went into the prompt and the model's Markdown was the answer. The `pa-answer-card-shell` template existed but was never wired. |
| Provider + model id in header | `getModelLabel()` rendered `OpenRouter · ${model}` into `.answer-model`; index.html had `buildModelBadgeHtml()` ("응답 모델"). `/api/ask` returned the full routing chain to every browser. |
| `BASIS / SOURCE / DISABLED` | CSS `::before { content: "…" }` pills on `.source-row` state classes. |
| `법령 인용 검증: 기능 꺼짐` | `citation_verification.status = citation_verification_not_applicable` was not treated as "unavailable/not applicable", so the panel fell through to the `lawVerificationStatus()` "Disabled" label. |
| Fast selected, Basic model shown | See below. |

### Fast vs Basic

Verified facts:

* Current `main` routes `D-2 연장시 필수 서류` / `D-2 연장에 필요한 서류는?` with
  `answer_mode=fast` to the **Fast** chain with no escalation
  (`legal_issue_types = [documents_needed, extension]`, no complex issue, no
  source-heavy / procedure-risk pattern, short). Reproduced offline and now
  pinned by `FastRoutingTests`.
* `ai.html` sends `answer_mode: "fast"` after the Fast button is tapped
  (verified in Chromium at 390px).
* Railway Live Smoke run 67 (2026-09-25, commit `096ee7a`) shows production
  serving `main` with the committed Basic chain
  (`nemotron-3-ultra` → `gemma-4-31b` → `nemotron-3-super`), i.e. model env
  overrides were not active.
* `nvidia/nemotron-3-ultra-550b-a55b:free` is only in the Basic chain.

Conclusion: the observed answer was produced by a request processed as
**Basic**; the backend classifier did not escalate it. The exact client-side
reason could not be proven from the repository (no production request log was
available). Contributing UX defects that made "Fast selected" and "Basic used"
look contradictory, all fixed:

1. The selector reset to Basic on every reload (no persistence).
2. The answer card never said which mode produced it, so the selector's
   *current* state was read as the *answer's* mode.
3. On touch devices `:hover` sticks after a tap/scroll; the mint hover fill on
   the unselected button read as "selected".

## What changed

### Backend

* `services/structured_answer.py` (new): deterministic document buckets
  (`common` / `required` / `conditional` / `additional` /
  `missing_or_unverified`, the `ANSWER_QUALITY_CONTRACT.md` §3 names) from the
  canonical manual grounding. Every canonical document lands in exactly one
  bucket; nothing is added or dropped. The model may supply only the short
  summary (`extract_summary`: prose only, no lists/headings/citations). Manual
  caveats are all kept: provenance → source notes, final-determination
  sentence → disclaimer, the rest → notes.
* `/api/ask` returns `structured_answer` for plain document lookups
  (`is_document_lookup`: explicit `documents_needed`, documents contract,
  non-empty canonical list, no complex issue). The prompt gets a
  "summary only" contract. The answer-shape gate evaluates the composed text;
  a failing model summary is replaced by the deterministic summary, never by
  the long legal-analysis memo. When every model candidate fails, the
  fallback is the canonical checklist (`fallback_answer_kind =
  structured_document_checklist`).
* `_build_grounded_prompt()` uses the public edition label only and forbids
  file names / revision dates / Markdown headings.
* **Public projection.** `/api/ask` now returns `_public_ask_payload()`:
  no `provider`, `model`, `final_model`, `selected_model`, candidate chain,
  cooldown/upstream detail, `fallback_answer_reason`, `law_evidence_pack`, and
  no `source_file` / `source_revision_date` / `verification_note` anywhere.
  Error envelopes never name a vendor. SSE frames are projected the same way.
* **Diagnostics opt-in.** `{"diagnostics": true}` or header
  `X-Paradiso-Diagnostics: 1` returns the full internal payload (model ids are
  public catalog identifiers, never secrets). Operators can refuse the opt-in
  with `PARADISO_CLIENT_DIAGNOSTICS=0`.
* **Telemetry.** Every `/api/ask` logs one `ask_routing` JSON line: requested /
  effective mode, escalation + reasons, provider, primary / final / attempted
  models, fallback flags, provider error class, upstream statuses, latency.
  No prompt, answer or secret is logged.

### Frontend (`ai.html`, `index.html`)

* One canonical structured renderer: `renderStructuredAnswer()` clones
  `pa-answer-card-shell` and fills it with `textContent` only. Real `<ul>`
  lists, `<h3>/<h4>` section headings, compact source component
  (`외국인체류 안내매뉴얼 · 2026.6 / 법무부 출입국·외국인정책본부 /
  D-2 · 체류기간 연장 · pp. 43–44 / 공식 매뉴얼 확인됨`), one disclaimer.
  The verbose evidence register is omitted for structured answers (shown in
  developer mode).
* Header: `Waymaker by Paradiso` / `공식 자료 기반 안내`, plus the effective
  mode chip (`빠른 답변` / `정밀 답변`) and the grounding badge. No provider or
  model anywhere (visible text, attributes, clipboard, error cards).
* Safe formatter for free-form answers: headings, ordered/unordered lists,
  quotes, rules, bold; escape-first.
* Clipboard: structured answers copy readable plain text with section titles;
  free-form answers are stripped of Markdown syntax.
* Source panel: engineering `::before` pills removed; "not applicable / feature
  off" law states are omitted instead of rendered as `기능 꺼짐`.
* Fallback / error copy in product language ("답변을 생성하는 중 일시적인
  문제가 발생했습니다", "확인된 공식 자료를 기준으로 기본 안내를 대신
  표시합니다"). Developer error JSON only in developer mode.
* Mode selector: `빠른 답변` / `정밀 답변` (API values unchanged: `fast` /
  `basic`), persisted in `localStorage['paradiso:waymakerAnswerMode']`,
  hover styling only on hover-capable devices, escalation note:
  "이 질문은 정확한 자료 확인이 필요해 정밀 답변으로 처리했어요."
* Developer diagnostics: `?debug=1`, `?dev=1`,
  `localStorage.paradisoDevDiagnostics = '1'` or
  `window.PARADISO_DEV_DIAGNOSTICS`. Only then does the page request the
  diagnostics payload and show routing detail.

## Verification

* `backend/tests/test_waymaker_answer_product_quality.py` — D-2 structure,
  canonical membership, metadata leak invariants, public projection,
  diagnostics opt-in/refusal, telemetry, SSE projection, Fast routing,
  frontend static guards, fixture drift.
* `tests/e2e/waymaker-answer-card.spec.mjs` — real public payload
  (`tests/fixtures/waymaker/*.json`, regenerated by
  `scripts/build_waymaker_answer_fixtures.py`) at 320/360/390/430/768/1280.
* `scripts/mobile_webkit_qa.mjs` — WebKit (CI) Waymaker answer flow on every
  iPhone profile.
* `.github/workflows/railway-live-smoke.yml` — adds a public (non-diagnostics,
  Fast) D-2 request asserting the structured checklist and no provider /
  model / internal metadata / Markdown in the ordinary response.

## Production follow-up: no structured checklist on Railway

Railway Live Smoke runs 72 (`a5a8b7d`) and 73 (`cdb9ca3`) returned HTTP 200
with no leaks but `structured_answer: false`, while the same request offline
returned the checklist.

Cause (reproduced from a backend-only copy of the tree): the Railway service
is deployed with Root Directory = `backend`, so repository-root files are not
in the build context. The Knowledge Platform (#644) bootstrap read
`<repo root>/data/source_registry.json` and `<repo root>/backend/data/…`,
raised `FileNotFoundError` in `get_platform()` on every request (also in its
in-memory fallback), and `_select_grounding()` swallowed it and returned
`None` — no grounding, no structured answer. `manual_grounding_status` still
read `present` because structured requirements also set it.

Fix: `services/knowledge/paths.py` resolves repository-root files to
byte-identical deploy copies in `backend/data/knowledge_deploy/`
(`source_registry.json`, `manual_approval_index.json`,
`status-guidance-202609.json`; `doc_master.json` reuses the existing copy),
maintained and drift-checked by `scripts/sync_visa_data.py`. The legacy
grounding path is now backend-relative. `data/manual-corpus` (3 MB, Studio
evidence snippets and page counts only) is not copied. Guarded by
`backend/tests/test_knowledge_deploy_context.py`, which runs the platform from
a backend-only copy.

## Known limits

* Manual notes and document labels are Korean source text in every locale
  (official wording); product chrome is localized (ko / en / zh / zh-TW).
* Structured answers cover questions with a source-confirmed manual grounding
  entry (currently D-2, D-4, E-7 extension). Other questions keep the
  free-form answer with the safe formatter.
* Production (Railway) behavior is verified only after the backend deploy and
  the live smoke run.
