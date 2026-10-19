# Search-first homepage — audit, decisions and QA (2026-10-19)

Scope: the Visable home (`index.html` civic landing, `assets/js/civic-search.js`
`homeHtml()`), its search entry, and the suggestion layer under the search field.
This is rendering / search-UX work. It does **not** revalidate any immigration
rule, and no canonical dataset (`visa_data.json`, `doc_master.json`,
`backend/data/*`, `data/status-guidance-202609.json`) was edited.

Screenshots: [`screenshots/search-first-home-20261019/`](screenshots/search-first-home-20261019/)
(`before-*` = main at 0c6784b, `after-*` = this change; 320 / 390 / 768 / 1280 / 1440).

## 1. Baseline audit (before)

| Area | Finding |
|---|---|
| Search input | One field (`#civicQuery`), plain `<input type=search>`. Enter → `searchFromHome()` → `executeSearch()`. No suggestions on the home at all; the legacy `#q` autocomplete only exists on the results header. |
| Intent recognition | Strong and deterministic already: `VisableStatusGuidance.interpret()` + `VisableSearchRouter.route()` read codes (incl. `e 7 1`, `e71`), aliases, procedures, objects × actions, offices, question facets. |
| Gaps found | `직장 바꿨어요` and `한국에 와서 처음 등록하려고 해요` read as nothing. **Bug:** a word after a code was read as a subcode — `E-7 Change of status` → unknown code `E-7-CHANGE`, `C-3 Visa issuance` → `C-3-VISA` (English searches got an "unknown code" answer). |
| Ranking | Result-side ranking is per module (guidance resolver; manual-corpus evidence ranking by intent). Nothing ranked suggestions because none existed. |
| Hierarchy | Two large journey cards (한국 입국 전 · 사증 발급 / 한국 입국 후 · 체류 관리) between search and tools forced a before/after choice; tools were split into two equal-weight groups with 70 px icons. |
| Examples | "자주 찾는 질문" — a popularity claim without usage data. |
| URL / history | `?q=` is pushed by `unified-search.js`. **Bug:** Back from the first result to the bare home URL left an empty "searched" page (landing hidden). |
| Failure states | Data-load failure row, boot-failed row and `<noscript>` exist and are kept. |
| AI | AI overview / Waymaker are separate, opt-in, server-side keys; no AI call while typing. Kept as is. |
| Mobile | No overflow at 320; journey cards pushed the tools below two screens. |

## 2. What changed

* **Journey cards removed.** The home no longer asks "before or after entering
  Korea?". Each suggestion row says which side it belongs to instead
  (`입국 전 · 사증` / `입국 후 · 체류`), so issuance and stay procedures stay
  visibly separate without a gate in front of the search.
* **Legacy purpose pickers kept** (`startPreEntryTrack()` / `startInKoreaTrack()`):
  "전체 도구 보기 → 목적별로 둘러보기" opens a browse panel with two small tabs.
  `window.VisableCivicSearch.journey` (CLOSED | PRE_ENTRY_OPEN | POST_ENTRY_OPEN)
  is unchanged as an API, so index.html's `reveal-home-section` handler and the
  early-tap replay still work.
* **Search field = WAI-ARIA combobox** (list autocomplete): `role=combobox`,
  `aria-expanded`, `aria-controls`, `aria-activedescendant`, listbox with named
  options, debounced polite live count, clear button, Arrow/Enter/Escape/Tab,
  IME guards (`isComposing`, keyCode 229, the Safari compositionend→Enter order).
* **Suggestions** (`assets/js/search-suggest.js`, pure, deterministic): exact
  code → exact subcode (always shown *under* its parent) → code × procedure →
  procedure → tools → alias candidates → name matches, stable tie-breaks. Rows
  come only from index entries; every row that searches is re-interpreted before
  it is shown, so the label can never promise more than the search delivers.
  Unknown codes (`XYZ-999`, `E-7-99`) get a note, never a match.
* **Derived index** `data/search-suggest-index.json` (142 KB, ~12 KB gzipped)
  built by `scripts/build_search_suggest_index.mjs` from the guidance bundle in
  the shape `interpret()` reads — no second interpreter, no hand-forked data.
  Fetched on idle; a failure only disables suggestions.
* **Resolver fixes** (benefit the results page too): the subcode regex no longer
  swallows a following word; two colloquial phrases (workplace move, first
  registration after arrival) apply only when no explicit procedure word matched.
* **Back/Forward**: Back to the bare URL restores the search home; Forward to a
  `?q=` entry runs that search again.
* **Examples**: "이렇게 검색해 보세요" — four editorial queries that resolve to a
  procedure (checked by `check_search_suggest.mjs`) plus a direct Form Helper link.
* **Tools**: one compact, secondary grid of six (Form Helper, Waymaker, New Home,
  visit reservations, official source text, immigration office).
* Disclaimer, source PDFs, basis dates, about/pending-review notices: unchanged.

## 3. Privacy and safety

* No network request while typing (tested); queries are not stored or logged.
* Suggestion labels are escaped; tool destinations are an allow-list
  (`form-helper.html`, `ai.html`, `new-home.html`, two existing dialogs).
* No new dependency, service, or inference cost.

## 4. Multilingual

All new strings live in the 14 `civic` packs. Procedure and status *names* exist
in Korean and English only in the source data, so Korean UI shows Korean names,
every other locale shows the official English names and says so in the panel
footer ("…official Korean and English terms"). Natural-language understanding
is strongest for Korean and English; other languages fall back to codes and
the English/Korean procedure words. Official-source excerpts stay Korean (`lang="ko"`).

## 5. Known limitations

* Colloquial coverage is a small, explicit phrase list — not semantic search.
* The results page itself was not redesigned (only the code-reading fix and Back/Forward).
* The 150 ms target is measured as in-browser render time of the panel
  (`VisableCivicSearch.suggestions.state().renderMs`) on the QA machine, not on
  low-end phones.
* The September 2026 guidance is still marked "not reviewed line by line"; the
  suggestions inherit that status and do not change it.
