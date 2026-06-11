# i18n Target Architecture — ko/en/zh-CN system (2026-06-11)

## Goals
Keep `ko`/`en`/`zh-CN` publicly active, switchable through structured locale
resources, with official terminology resolved through a reviewable glossary
instead of ad-hoc UI copy — without rewriting the app or breaking search,
routing, gateways, document rendering, or layout.

## Active locale policy
- `ko` is the canonical source language. All other locales are display layers.
- `en` and `zh-CN` are active public display languages (`full`).
- Pending locales stay selectable with a transparent "준비 중" badge and fall
  back to Korean (existing behavior, unchanged — removing the buttons would
  remove an existing UI feature).
- `data/i18n/manifest.json` is the single locale config (the repo's existing
  equivalent of the proposed `config.json`; no duplicate config is created).
  This patch adds `fallbackLocale`, `localeLabels`, and `policy` fields to it.

## Fallback rules (runtime, unchanged + hardened)
1. Requested locale pack value.
2. Korean pack value.
3. Bootstrap Korean shell (`BOOTSTRAP_KO_FALLBACK`) when packs fail to fetch.
4. Last resort: the key itself (kept for backward compatibility), now with a
   one-time `console.warn` in development (`localhost` / `127.0.0.1` /
   `localStorage['paradiso:i18n-debug']='1'`). Key parity validation makes this
   path unreachable for shipped keys.
- User input is never translated or overwritten. Visa/status codes (D-2, F-4,
  E-7, G-1, G-1-5, …) are never translated; validation now enforces that codes
  appearing in a Korean value also appear verbatim in en/zh-CN values.

## Translation key conventions
- Stable semantic camelCase keys in flat packs (existing convention —
  `heroTitle`, `gwHikoreaLabel`, `qPlaceholder`). New keys follow it
  (`editorialThemeCivic`, `editorialThemeKitsch`, `editorialThemeAria`).
  Visible Korean text is never used as a key.
- DOM binding stays centralized in `applyLanguage()` via `setText`/`setAttr`
  helpers (covers textContent, placeholder, aria-label, title, option labels,
  CSS pseudo-content). This is the repo's established equivalent of
  `data-i18n` attributes; introducing attribute-based binding in parallel would
  create two competing systems for no functional gain on a single-page app.

## Official terminology glossary
New file: `data/i18n/official-terms.json`.

Shape:
```json
{
  "schemaVersion": "1.0",
  "policy": "...Korean canonical; never fabricate official names...",
  "terms": {
    "integrated_application_form_34": {
      "ko": "통합신청서(별지 제34호 서식)",
      "en": "Application Form (Report Form) — Annex Form No. 34",
      "zh-CN": null,
      "sourceType": "manual-derived",
      "source": "stay_manual_260601",
      "confidence": { "ko": "canonical", "en": "manual-derived", "zh-CN": "needs-verification" },
      "preserveKoreanWhenUnverified": true,
      "docIds": ["doc_app_form", "doc_unified_application_form"],
      "notes": "..."
    }
  }
}
```
- `confidence` values: `canonical`, `official`, `manual-derived`, `curated`,
  `fallback`, `needs-verification`.
- `sourceType` values: `law-api`, `english-law`, `manual-derived`, `hikorea`,
  `visa-portal`, `mofa`, `curated`, `unknown`.
- A translation may be **stored** at any confidence (so unverified candidates
  from `data/ops/translation_glossary.template.json` are preserved for review),
  but is only **displayed** at `canonical`/`official`/`manual-derived`/
  `curated`. `needs-verification` and `fallback` render Korean only.
- `docIds` links a term to stable `DOC_DICT` ids so dynamic document rendering
  can resolve names through the glossary without duplicating translations in
  `index.html` or editing protected data files.

### Official terminology source hierarchy
1. `canonical` — the Korean term itself (source manuals / protected data).
2. `official` — published by the issuing authority (law.go.kr English statutes,
   the printed bilingual form/card itself, HiKorea/visa portal official pages).
3. `manual-derived` — taken from the 2026 immigration/visa manuals.
4. `curated` — repo-reviewed safe descriptive rendering (never presented as an
   official name).
5. `fallback` / `needs-verification` — stored but never displayed; Korean shown.

## Runtime resolution (index.html)
- `loadI18nTranslations()` additionally fetches `official-terms.json` into
  `OFFICIAL_TERMS` (failure-tolerant: glossary missing ⇒ Korean-only labels,
  exactly today's behavior).
- `officialTermTranslation(termId, locale)` returns a translation only when the
  locale is non-Korean and confidence is displayable; otherwise `null`.
- `annotateOfficialDocLabel(docId, koreanLabel)` — used by `renderDocTags()`:
  for non-ko locales, appends ` (translation)` after the canonical Korean
  label. Korean always stays primary; nothing is replaced, nothing is
  fabricated; unverified terms render Korean-only.

## Law/Open-API sync strategy (build-time only; no frontend credentials)
New script: `scripts/sync_official_terms.py`.
- Input: `data/i18n/official-terms.allowlist.json` (law terms eligible for
  sync) + curated glossary.
- Credentials: `LAW_OPEN_API_OC` (law.go.kr DRF; legacy `LAW_API_OC` also
  accepted) and optional `DATA_GO_KR_API_KEY`. Environment variables only.
- Without credentials: prints a clear warning, leaves glossary/cache untouched,
  exits 0 — normal local app usage never requires credentials or network.
- With credentials: queries law.go.kr `lawSearch.do` (`target=law`, then
  `target=elaw` for official English statute titles), writes
  `data/i18n/official-terms.cache.json` (generated cache; never writes
  `index.html`, never overwrites curated glossary entries), and writes a report
  (`reports/official-terms-sync/sync_report.md`) listing added / changed /
  unresolved / conflicting terms. Conflicts (API result ≠ curated `en`) are
  reported, not auto-applied.

## Validation (CI/local)
`scripts/check_i18n.js` now runs three checks:
1. `check_i18n_coverage.mjs` (existing) — manifest + key/shape parity.
2. `check_index_hardcoded_text.mjs` (existing) — inline UI-string scan.
3. `check_official_terms.mjs` (new) —
   - all `data/i18n/*.json` parse;
   - manifest invariants: `defaultLocale`/`fallbackLocale` = ko,
     `supportedLocales` exactly `ko,en,zh-CN` (guards against deleting zh-CN or
     narrowing to ko/en), `localeLabels` present for supported locales;
   - every `LANGUAGE_OPTIONS` code in `index.html` is declared in the manifest
     (supported or pending) — no undeclared selector buttons;
   - glossary schema: term-id format, non-empty `ko`, `en`/`zh-CN` string or
     null, enum-valid `confidence`/`sourceType`, displayable translations have
     confidence, unverified non-null translations require
     `preserveKoreanWhenUnverified: true`;
   - `docIds` referenced by the glossary exist in `DOC_DICT`;
   - visa/status codes in Korean values are preserved verbatim in en/zh-CN
     (locale packs and glossary);
   - invisible-Unicode ban (U+202F, U+200B/C/E/F, U+2060, U+FEFF, U+00AD,
     U+180E; U+200D allowed for emoji ZWJ) across HTML entry points and i18n
     JSON;
   - no client-side credential exposure (`LAW_OPEN_API_OC`,
     `DATA_GO_KR_API_KEY`, common secret-token patterns) in
     `index.html`/`ai.html`/`form-helper.html`;
   - unused glossary terms reported as warnings (not failures).
- The previous "888-key parity" expectation is count-agnostic in the script;
  adding the three editorial-theme keys moves it to 891 with parity intact.

## Migration plan executed by this patch
1. Move `EDITORIAL_THEME_LABELS`/`EDITORIAL_THEME_ARIA` from `index.html` into
   the three locale packs (+ Korean bootstrap shell); rewire
   `updateEditorialThemeLabel()` through `tx()`.
2. Add manifest `fallbackLocale`/`localeLabels`/`policy`.
3. Add glossary + allowlist + runtime resolver + `renderDocTags` wiring.
4. Add sync script (network-optional) and the new validator; register it in
   `check_i18n.js`.
5. Audit docs + manual QA checklist.

## What this patch intentionally does NOT solve
- Perfecting every en/zh-CN sentence (zh-CN Korean residuals remain; they are
  now reviewable in locale files and tracked, which is the point of the system).
- Localizing `ai.html` / `form-helper.html` (separate surfaces; their small
  bilingual helpers are follow-up work).
- Verifying official Chinese legal/document names — entries stay `null` or
  `needs-verification` (Korean displayed) until a verified source is recorded.
- Live law-API integration in the browser (explicit non-goal: credentials must
  never ship client-side).
- Translating canonical Korean data in `visa_data.json` / `doc_master.json`
  (protected files; document names render Korean-first by design).
