# Manual QA Checklist — ko/en/zh-CN i18n system (2026-06-11)

Legend:
- ✅ verified in this patch by automated/static check (script named)
- ☐ needs a human browser pass before Ready-for-review (this PR stays Draft)

## Language switching
- ☐ Korean default load (no `?lang=`, empty localStorage → ko UI)
  - ✅ static guarantee: `manifest.defaultLocale === 'ko'` (`check_official_terms.mjs`), `getStoredLanguage()` defaults `'ko'`
- ☐ English switch — whole visible UI changes
  - ✅ static: `smoke_static_i18n.mjs` asserts ko/en/zh-CN hero text differs; 891-key parity (`check_i18n_coverage.mjs`)
- ☐ zh-CN switch — whole visible UI changes; zh-CN button present and active
  - ✅ static: `supportedLocales` exactly `ko,en,zh-CN` enforced; zh-CN pack loads
- ☐ Reload persistence (`localStorage['paradiso:language']` survives reload)
- ☐ Mobile language selector opens, scrolls, selects, closes
- ☐ No broken buttons after switching (language menu, theme toggles, gateway cards)
- ☐ No missing-key strings visible in any of the three locales
  - ✅ static: key parity makes the raw-key fallback unreachable for shipped keys; dev console warning added for future regressions

## Search & routing (must be unaffected)
- ☐ D-2 search works
- ☐ F-4 search works (route guide renders, F-4 form name shows `tx('f4ApplicationForm')`)
- ☐ E-7 search works
- ☐ G-1 search works (G-1-5 classified under G-1, not top-level)
- ☐ G-1-5 search works
  - ✅ static: `smoke_static_i18n.mjs` confirms visa fixtures (C-3/D-2/F-6) and all inline scripts still parse; `check_repo.sh` full suite passes (exact-code search, procedure journeys, AI shell semantics, golden questions)

## Gateways
- ☐ AI gateway (Waymaker) opens and works
- ☐ HiKorea gateway / 방문예약 guide opens and works
  - ✅ static: no edits were made to gateway markup/handlers; `check_ai_shell_semantics.js` passes in `check_repo.sh`

## Document rendering & official terms
- ☐ Document checklists render in ko exactly as before (no annotation in ko)
  - ✅ simulated: `annotateOfficialDocLabel` returns the Korean label unchanged for ko
- ☐ In en: `통합신청서 (별지 제34호 서식)` renders with appended `(Application Form (Report Form) — Annex Form No. 34)`; `수수료` → `(Fee)`
- ☐ In zh-CN: `수수료` → `(手续费)`; unverified terms (e.g. 통합신청서 zh) stay Korean-only
  - ✅ simulated in node against the real glossary (see PR body): unverified/`needs-verification` and `null` entries render Korean — nothing fabricated
- ☐ Glossary fetch failure (offline/file://) → document labels render Korean-only, console warning, no crash
  - ✅ static: loader catches fetch errors and resets `OFFICIAL_TERMS = {}`
- ☐ Visa/status codes never translated
  - ✅ enforced: `check_official_terms.mjs` fails if a code in a Korean value is missing/altered in en/zh-CN (packs + glossary)

## Console & hygiene
- ☐ No console errors on load in ko/en/zh-CN
- ✅ No invisible/suspicious Unicode (U+202F, U+200B/C/E/F, U+2060, U+FEFF, U+00AD, U+180E) in entry-point HTML or i18n JSON (`check_official_terms.mjs`)
- ✅ No client-side credential exposure (`LAW_OPEN_API_OC`, `DATA_GO_KR_API_KEY`, secret-shaped tokens) (`check_official_terms.mjs`)
- ✅ `sync_official_terms.py` without credentials: warns, exits 0, touches nothing

## Commands run for this patch (all passing)
```
node scripts/check_i18n.js          # coverage 891 keys + hardcoded-text + official-terms
node scripts/smoke_static_i18n.mjs
bash scripts/check_repo.sh          # full repo validation incl. golden questions
python3 -m json.tool data/i18n/{ko,en,zh-CN,official-terms}.json
python3 scripts/sync_official_terms.py   # no credentials → safe skip, exit 0
```
