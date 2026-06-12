# i18n Current State Audit — ko/en/zh-CN system (2026-06-11)

## Scope
Audit performed before the `refactor: build source-grounded ko/en/zh-CN i18n system`
patch. Baseline commit: `0cd34c2` (includes the zh-CN `specialCaseBody`/`aiIntro`
and ko `gwHikoreaLabel` i18n fixes from #350 — those fixes are preserved, not reverted).

## Current active languages
- `ko` (canonical, default), `en`, `zh-CN` — all declared `full` in
  `LANGUAGE_SUPPORT` inside `index.html` and in `data/i18n/manifest.json`
  (`supportedLocales`).
- 17 additional locales (`ja`, `vi`, `th`, …) are selectable in the language
  menu but flagged `partial` ("준비 중" badge) and fall back to Korean. They are
  declared in `manifest.json` `pendingLocales`. This is a deliberate
  transparency feature, not an accident — kept as-is by this patch.

## Current locale files
- `data/i18n/manifest.json` — locale config (defaultLocale, canonicalLocale,
  supportedLocales, localeAliases, pendingLocales, files map). This is the
  repo's existing equivalent of the proposed `data/i18n/config.json`; a
  duplicate config file is intentionally NOT created.
- `data/i18n/ko.json` — canonical pack, 689 top-level keys (888 flattened
  leaf keys including array items).
- `data/i18n/en.json`, `data/i18n/zh-CN.json` — display packs with exact key
  parity (enforced by `scripts/check_i18n_coverage.mjs`). Some zh-CN values are
  still Korean residuals (known partial translation state; tracked for review,
  not a structural problem).

## Where language selector logic lives
All in the main inline script of `index.html` (single `<script>` block starting
~line 12643):
- `LANGUAGE_OPTIONS` (~17146) — selector entries (native names only; not a
  translation dictionary).
- `LANGUAGE_SUPPORT`, `languageSupportLevel` (~17175) — full/partial flags.
- `loadI18nTranslations()` (~17210) — fetches `manifest.json` + per-locale packs
  into `UI_TRANSLATIONS`; `BOOTSTRAP_KO_FALLBACK` is a small Korean-only shell
  used when fetch fails (file:// usage, offline).
- `tx(key, vars)` (~17246) — lookup with active-locale → ko → key fallback and
  `{var}` interpolation.
- `applyLanguage(code)` (~17384) — binds ~200 UI strings to the DOM through
  `setText`/`setHtml`/`setAttr`/`setIndexed*` selector helpers (textContent,
  placeholder, aria-label, title, CSS custom properties for pseudo-content).
  Persistence via `localStorage['paradiso:language']`; `?lang=` URL override.

The repo deliberately uses centralized JS binding instead of `data-i18n`
attributes; it covers the same surfaces (textContent/placeholder/aria-label/
title) and is validated by `scripts/check_index_hardcoded_text.mjs`. This patch
keeps that mechanism rather than introducing a second, competing one.

## Where hardcoded multilingual blocks exist (before this patch)
A previous migration ("PR A") already removed the large per-language UI
dictionaries from `index.html`. Remaining inline multilingual structures found
by this audit:
1. `EDITORIAL_THEME_LABELS` (~17594) — `{ ko, en, ja, zh, vi }` labels for the
   civic/kitsch theme toggle. Inline translation object → migrated to locale
   packs by this patch (`editorialThemeCivic`, `editorialThemeKitsch`).
2. `EDITORIAL_THEME_ARIA` (~17598) — same shape for the toggle aria-label →
   migrated to `editorialThemeAria`.
3. `BOOTSTRAP_KO_FALLBACK` (~17184) — Korean-only bootstrap shell. NOT a
   multilingual dictionary; intentionally kept (offline/file:// resilience) and
   explicitly exempted by the hardcoded-text scanner.
4. `DOC_DICT` (~12671) — Korean-only canonical document-name dictionary keyed
   by stable `doc_*` ids, kept in sync with `doc_master.json`. This is the
   canonical Korean data source, not a translation store; kept.
5. `LANGUAGE_OPTIONS` native names — standard practice (each language named in
   itself); kept.

`ai.html` and `form-helper.html` have their own smaller bilingual helpers
(e.g. `t(lang, ko, en)` in `ai.html`); they are separate surfaces and are out
of scope for this patch (recorded as follow-up).

## Current i18n validation behavior
- `scripts/check_i18n.js` — orchestrator; runs:
  - `check_i18n_coverage.mjs` — manifest sanity + exact flattened key parity +
    per-key type/shape parity across ko/en/zh-CN (currently 888 keys).
  - `check_index_hardcoded_text.mjs` — scans string literals in the i18n region
    of `index.html` for non-allowlisted UI text; verifies runtime markers
    (`I18N_MANIFEST_PATH`, `loadI18nTranslations`, `tx(`, manifest path).
- `scripts/smoke_static_i18n.mjs` — static smoke: packs load, hero text differs
  per locale, interpolation works, missing locale falls back to ko, all inline
  scripts parse (`new Function`), visa fixtures (C-3/D-2/F-6) still present.
- `scripts/check_repo.sh` — runs both of the above plus broader repo checks.

All of the above pass at baseline.

## Gaps / risks in the existing approach (what this patch addresses)
1. **No official terminology glossary.** Official document/law/agency names are
   translated ad hoc inside the locale packs (e.g. `f4ApplicationForm`) with no
   confidence/source metadata and no rule preventing fabricated "official"
   Chinese/English names. Only an unused multilingual template exists at
   `data/ops/translation_glossary.template.json` (explicitly marked as
   requiring native/legal QA).
2. **Dynamic document rendering is Korean-only with no safe localization
   path.** `renderDocTags()` resolves `doc_*` ids through `DOC_DICT` and always
   renders Korean labels — safe, but there is no mechanism to surface a
   *verified* English/Chinese gloss without editing canonical data.
3. **No law/Open-API sync design.** Probe scripts exist
   (`probe_korean_law_open_api_2026_05.py`, `capture_law_api_shape.py`) but
   nothing maintains official English law names for i18n, and no documented
   credential policy for i18n purposes (credentials are correctly absent from
   the frontend today — verified: `LAW_OPEN_API_OC` / `DATA_GO_KR_API_KEY` do
   not appear in `index.html`; `LAW_API_KEY_MISSING` is a backend warning enum,
   not a secret).
4. **Validation gaps.** No checks for: invisible/suspicious Unicode (U+202F
   etc.), visa/status-code preservation across locales, glossary schema
   integrity, selector locales not declared in the manifest, or accidental
   client-side credential exposure.
5. **Residual inline dictionaries.** The two editorial-theme objects above sit
   outside the hardcoded-text scanner's region, so regressions there were
   invisible to CI.
6. **`tx()` missing-key behavior.** A key missing from every pack renders the
   raw key string in the UI with no developer warning (mitigated in practice by
   parity checks, but silent).

## Invisible-Unicode baseline
Scan of `index.html`, `ai.html`, `form-helper.html`, `data/i18n/*.json`:
- No U+202F, U+200B, U+200C, U+200E, U+200F, U+2060, U+FEFF, U+00AD, U+180E.
- 6 × U+200D in `index.html` — all inside the 👨‍👩‍👧‍👦 family emoji (legitimate
  ZWJ sequences). The new validator therefore bans the list above but allows
  U+200D.
