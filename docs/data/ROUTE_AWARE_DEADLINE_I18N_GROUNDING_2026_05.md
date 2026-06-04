# Route-aware deadline tools, localization, and grounding (2026-05)

Branch: `feat/route-aware-deadline-i18n-grounding`
PR: `feat: add route-aware deadline tools and grounding`

## 1. Purpose

A single practical implementation PR that improves day-to-day usability and
answer trustworthiness without changing the data model or grounding semantics:

- Route-aware UX for F-4 (multiple practical routes, guided).
- Deadline / grace-period calculator with calendar (ICS / Google Calendar) handoff.
- Removal of the HiKorea preliminary-checkbox gate (replaced by a non-blocking caution).
- Deterministic fallback descriptions for the most common procedure sections.
- Activity-scope/study/working-holiday law-grounding intent (incl. the H-1
  seasonal-course case), with clearer, non-overclaiming grounding metadata.
- Model configuration clarity: the OpenRouter default is now the verified
  Gemma free model, with an explicit Groq-fallback gate.
- Broader localization coverage (ko / en / zh / zhHant) for all new surfaces.

Everything added here is a **preparation aid**. See the safety note at the end.

## 2. Site-wide localization coverage improvements (Part A)

- Reused the existing inline `UI_TRANSLATIONS` / `tx()` architecture in
  `index.html` (no new i18n framework). Simplified Chinese is keyed `zh`,
  Traditional Chinese `zhHant`.
- Added **42 new keys** for every new surface to all four target packs
  (`ko`, `en`, `zh`, `zhHant`): F-4 route wizard (title, intro, 5 labels,
  5 descriptions, show-all, source/no-docs notes, aria), deadline calculator
  (title, intro, entry/expiry/custom inputs, registration estimate, extension
  reminders, calendar actions, disclaimer, privacy note, D-day/relative-date
  helpers), the HiKorea pre-check caution, and three procedure fallbacks.
- Korean remains the source/fallback language; `en` values are Hangul-free so
  `node scripts/check_i18n.js` continues to pass (474 keys in `ko` and `en`).
- Official Korean document/scenario names are **not** mass-translated. Non-Korean
  helper copy explains that official Korean terms are preserved where relevant
  (existing `officialDocumentNamesKoNote` / `scenarioOfficialLabelsKoNote`).
- Scope was deliberately limited to UI chrome + guidance for the surfaces this
  PR touches; retro-translating the pre-existing partial packs (ja/vi/… still
  fall back to `ko`) is out of scope to avoid destabilizing official-term handling.

## 3. F-4 route-aware search/detail behavior (Part B)

- New, data-driven `F4_ROUTE_CONFIG` + `renderF4RouteChooser(v)` render a compact,
  keyboard-accessible route chooser **only for F-4**, injected before the
  procedure cards (`renderF4RouteChooser` → `renderProcedures`).
- Five routes: (1) overseas-mission visa issuance → `visaIssuance`; (2) domestic
  change after B-2/C-3 etc. → `statusChange`; (3) H-2 → F-4 → `statusChange`;
  (4) domestic residence report (국내거소신고) → `registration` **labeled as a
  residence report, explicitly distinct from generic foreigner registration**;
  (5) extension → `extension`.
- Selecting a route (button, `aria-pressed`): activates the matching procedure
  tab/panel, de-emphasizes (opacity, never hides) the others, shows a concise
  route explanation plus a cautious source note, and reveals a
  **Show all F-4 routes / 전체 경로 보기** reset.
- If a route has no source-backed procedure data, it shows the explanation only
  and directs the user to HiKorea / 1345 / the competent office.
- Guarantees: no eligibility/approval is implied; existing F-4 variants stay
  exposed; generic F-4 questions don't force a route (nothing auto-selects); the
  wizard never renders raw `manualRefs` / `requiredDocs`.

## 4. Deadline calculator behavior (Part C)

- New collapsible `renderDeadlineCalculator(v, isVisaCode)` near the procedure
  action area on each status card.
- Inputs (no login): entry date, stay expiry date, optional custom reminder
  title + date.
- Outputs: estimated registration deadline (entry + 90 days), extension
  preparation reminders (60 / 30 / 7 days before + on the expiry date), and a
  custom reminder — each with a D-day label and calendar export.
- The 90-day registration estimate is presented as a **general preparation aid**
  with explicit caution ("not a confirmed official deadline"), not as a
  definitive statutory deadline. Extension reminders are explicitly **not** an
  official filing window.
- Timezone-neutral date math: `paradisoDeadlineAddDays` does UTC-based arithmetic
  on `YYYY-MM-DD` strings, so results never drift with the viewer's timezone/DST.
- Privacy: the calculator is **ephemeral** — no `localStorage`, and dates are
  **never** sent to the backend or AI (verified by test).

## 5. Calendar export behavior (Part C)

- `buildDeadlineIcs` emits a minimal all-day `VEVENT`
  (`DTSTART;VALUE=DATE`, `DTEND;VALUE=DATE`, `SUMMARY`, a 7-day `VALARM`).
  The `SUMMARY` carries only the user-facing reminder title; no personal data
  fields are written.
- `downloadDeadlineIcs` triggers a client-side Blob download (`.ics`).
- `deadlineGoogleCalUrl` builds a `calendar.google.com/calendar/render?action=TEMPLATE`
  link with `encodeURIComponent`-escaped title and an all-day date range.
- No account integration / OAuth. External links use `target="_blank" rel="noopener noreferrer"`.

## 6. HiKorea gate removal behavior (Part D)

- The HiKorea booking-assistant pre-check screen previously disabled the
  **Start** button until `emailOk && pwOk && expOk`. That gate is removed:
  - the Start button no longer renders `disabled`;
  - the delegated change listener sets `startBtn.disabled = false`;
  - the `start-hikorea-guide` handler no longer checks the flags.
- A visible, non-blocking caution (`hkPreCheckCaution`, localized) replaces the
  gate; the email/password/expiry inputs remain as optional preparation aids
  (the expiry input still drives the existing days-to-expiry hint).
- The existing HiKorea disclaimers (`hkDisc1`–`hkDisc4`) stay visible, and
  external links keep safe `target`/`rel`. Paradiso still never claims to file
  or reserve on the user's behalf.

## 7. Procedure-description fallback behavior (Part E)

- `renderProcedurePanel` now uses
  `renderProcedureSummaryBlock(...) || renderProcedureFallbackSummary(proc.key)`,
  so a fallback only appears when there is **no** existing/source-backed summary.
- Deterministic, key-based fallbacks for `visaIssuance` (최초 신청/사증발급),
  `registration` (외국인등록), and `extension` (체류기간 연장), localized in all
  four languages. They are generic guidance only — they never invent required
  documents and never claim verification.
- The registration fallback distinguishes general foreigner registration
  (외국인등록) from F-4 domestic residence reporting (국내거소신고).

## 8. Law MCP / Korean law API grounding audit findings (Parts F/G)

Concrete implementation audit of the committed code:

- Law grounding **is** wired into `/api/ask` (`build_law_grounding_context`),
  but only when `LAW_GROUNDING_MODE` is `audit`/`enabled`. The default is
  `disabled` (config + `.env.example`), so out of the box no external call runs.
- When used, compact law context (title + article of up to 3 results) **is**
  injected into the LLM prompt as a clearly-labeled supplemental block.
- Failures are not silently masked: `build_law_grounding_context` converts
  upstream errors into explicit warning markers (`SOURCE_UNAVAILABLE`,
  `LAW_API_KEY_MISSING`, `LAW_GROUNDING_DISABLED`, …).
- **Gap found:** intent patterns covered legal-basis / travel-re-entry /
  foreigner-registration / stay-risk / G-1, but **not** activity-scope, study,
  working-holiday, or H-1 — so the H-1 계절학기 question never triggered grounding
  intent. Also `intent_reasons` / `law_search_query` were computed but not
  surfaced to the frontend.
- **Live smoke:** prior live smoke attempts (`LAW_GROUNDING_LIVE_SMOKE_RESULTS.md`,
  `..._RERUN_RESULTS.md`) never succeeded — they were blocked by network/proxy
  (`CONNECT tunnel failed, response 403`) and verdicts were `NOT_READY` /
  `BLOCKED_BY_ENVIRONMENT`. No external law API call has ever completed in CI.

## 9. H-1 seasonal course regression and grounding behavior (Parts F/G)

- Regression target: `H-1 비자인데 한국 대학에서 계절학기를 수강할 수 있을까요?`
- Now detected as both **study/course-taking** (`유학/수강/계절학기`) and
  **tourism-working-holiday/H-1** (`관광취업/워킹홀리데이/H-1`) intent; a statutory
  search query is built with anchors incl. `출입국관리법`, `시행령`, `활동범위`,
  `체류자격외활동`, `관광취업`, `H-1`, `유학`, `수강`, `계절학기`.
- With grounding disabled (default), metadata reports
  `law_grounding_status="disabled"` plus the detected intent reasons and the
  query that *would* be issued — honest, no fabricated permission/prohibition.
  In `audit` mode without a key it reports `unavailable`. The ungrounded answer
  path retains its Korea-scoped guardrails directing final confirmation to
  HiKorea / 1345 / the competent office.

## 10. Law API / grounding changes (Parts F/G)

- `backend/services/law_grounding.py`: added activity-scope, study, and
  working-holiday/H-1 intent patterns and matching statutory query anchors.
  Existing triggers and the "generic documents question must not trigger"
  behavior are preserved.
- `backend/paradiso_backend.py`: intent is now computed for **every** question
  so the response can distinguish `not_attempted` / `disabled` / `unavailable` /
  `used`. New `AskResponse` fields: `law_grounding_status`,
  `law_grounding_intent_reasons`, `law_search_query` (all non-secret).
- Frontend `renderGroundingSourcePanel` surfaces the law status safely: a law
  row appears only when the question carried legal/activity intent, and never
  overclaims (disabled → "Disabled", unavailable → "Needs review", used →
  "Source present"). No live external law API is required for CI tests.

Required env vars to enable live grounding (documented, none committed):
`LAW_GROUNDING_MODE=audit|enabled`, `LAW_API_KEY`, `LAW_API_BASE_URL`,
`LAW_API_SEARCH_PATH` / `LAW_API_ARTICLE_PATH`. Default stays safe (`disabled`).
`scripts/smoke_law_grounding.sh` (BACKEND_URL-driven) remains the deployed-test
helper; live runs are still environment-blocked here and documented as such.

## 11. Model configuration changes, including Gemma 4 free status (Parts H/H-0)

- **Mismatch reconciled:** the backend default no longer uses random routing.
  The code default is now
  `_DEFAULT_OPENROUTER_MODEL = "qwen/qwen3-next-80b-a3b-instruct:free"`, with
  Gemma free retained as the second explicit OpenRouter fallback candidate.
  Override per-deploy with `OPENROUTER_MODEL` if the catalog changes.
- New `_resolve_llm_config()` centralizes provider/model resolution
  (OpenRouter → Groq-if-allowed → none) and is logged once at startup and
  surfaced on `/health` (`llm.provider`, `llm.model`, `groq_fallback_allowed`) —
  model ids only, never API keys.
- New `ALLOW_GROQ_FALLBACK` env (default `true`, preserving prior behavior).
  Set `false` to hard-require OpenRouter/Qwen-first routing; `/api/ask` then returns 503
  rather than silently answering via Groq.

## 12. Tests added

- `backend/tests/test_law_grounding.py`: activity-scope/study/H-1 intent and
  query-anchor coverage; the H-1 seasonal-course regression; a generic
  "can I work/study with this status?" regression; guards that generic-documents
  questions still don't trigger.
- `backend/tests/test_paradiso_backend.py`: `ModelConfigResolutionTests`
  (Gemma default, env override, no-key → none, Groq-fallback gate, `/health`
  model exposure, no-secret) and `LawGroundingMetadataStatusTests`
  (`not_attempted` / `disabled`-with-intent / `unavailable`, generic activity
  scope, no-key-leak).
- `backend/tests/test_route_aware_deadline_i18n.py` (new): F-4 route wizard
  (titles/labels/intro in 4 languages, residence-report ≠ foreigner-registration,
  no-approval, additive/no-hide, no manualRefs/requiredDocs exposure, keyboard
  buttons); deadline calculator (4-language labels, disclaimer, ICS DTSTART/SUMMARY
  + no personal data, Google Calendar URL encoding, 90-day rule as preparation
  aid, reminder offsets, invalid-date handling, no AI payload leakage, no
  localStorage); HiKorea gate removal (no blocking checkbox, visible caution,
  disclaimers retained); procedure fallbacks; new-key i18n coverage in all four packs.

## 13. Validation results

- `node scripts/check_i18n.js` → OK (474 keys in `ko` and `en`).
- `node --check` on the extracted inline scripts → OK.
- A node harness exercising the real ICS/Google-Calendar/date helpers → all checks pass.
- `python3 -m pytest backend/tests -q` → all pass (incl. the new suites).
- JSON validators (`visa_data.json`, `backend/data/visas.json`, `doc_master.json`),
  `sync_visa_data.py --check`, `check_required_documents_coverage.py`,
  `validate_structured_requirements.py`, and `scripts/check_repo.sh` → see PR body
  for the exact run log. No data files were modified by this PR.

## 14. Known limitations

- Live law-API grounding remains unverified end-to-end (network-blocked in this
  environment); it stays disabled-by-default and must be enabled deliberately.
- Pre-existing partial language packs (ja, vi, …) still fall back to Korean for
  most strings; this PR only fully localizes the new surfaces.
- The deadline calculator's 90-day registration figure is a common-rule
  preparation aid, not a per-status confirmed deadline; actual obligations vary.
- The F-4 route wizard is intentionally F-4-specific for now (data-driven so it
  can extend to other route-complex statuses later).

## 15. Safety note

> Date calculations, route explanations, law grounding, and checklists are
> preparation aids only and do not replace official confirmation by HiKorea,
> 1345, or the competent immigration office.
