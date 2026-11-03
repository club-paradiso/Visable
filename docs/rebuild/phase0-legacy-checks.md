# Phase 0 — Legacy checks that read index.html / other pages

Date: 2026-11-03. Source: read-only sweep of scripts/, scripts/tests/, tests/. The brief said
"64 check scripts"; the measured set is **38 checks that read index.html text** + 16 browser
drivers that only navigate to `/index.html` URLs + ~45 checks on other pages or assets/js +
6 generators. Each row below says what breaks on a structural refactor and what to do.

Legend — invoked: `repo.sh` = scripts/check_repo.sh (CI: repo-validation.yml); `i18n.js` = spawned
by scripts/check_i18n.js; `BT` = spawned by backend/tests/* (run inside repo.sh); `npm` = package.json
script; `manual` = nothing invokes it. Coupling: STRUCTURE (parses index.html text/regex, slices inline
script source, new Function/vm/jsdom on raw HTML, asserts `<script src>`/`?v=`), BEHAVIOR (data files,
rendered text, pure functions imported from modules), MIXED.

E2E specs that run in CI (repo-validation.yml landing-restoration-e2e): landing-utilities,
post-search-guidance, tools-directory, question-understanding, landing-boot, search-first-home,
procedure-first-search, waymaker-quick-answer, language-control, search-result-unification,
form-helper, waymaker-answer-card, manual-reader, knowledge-studio. WebKit job: overlay-anchoring,
restore-trust, language-control, result-hierarchy, landing-boot, search-first-home.
immigration-checklists has its own workflow. **Never run in CI:** address-helper,
application-form-wording, bilingual-doc-names, complex-status-guide, content-studio, easy-mode,
multilingual-checklists, new-home, search-resilience, search-smoke, ui-consistency,
unified-search, ux10-a11y, waymaker-navigator.

Baseline (verified 2026-11-03, this sandbox, `PARADISO_PW_EXECUTABLE=/opt/pw-browsers/chromium
npx playwright test --project=desktop-1280 --project=mobile-390 --workers=4`): **563 passed,
69 skipped, 0 failed (8.3 min)**.

## Counts
- Checks reading index.html text: **38** (STRUCTURE 14, MIXED 23, BEHAVIOR 1) plus the inline
  check_repo.sh steps (`git diff --check -- index.html ai.html …`, forbidden-branding `rg` over index/ai).
- Browser drivers navigating to `/index.html`: 16 (behaviour-level; their static servers serve the
  repo root → must point at `dist/` after Phase 2).
- Comment-only mentions: ~10. Generators touching index.html: 6. Checks on other pages/assets only: ~45.
- At risk, not analysed: 16 `backend/tests/*.py` reference index.html and run in repo.sh.

## A. Checks that read index.html

| path | invoked | verifies | coupling / technique | depends on in index.html (breaks) | e2e cover | recommendation |
|---|---|---|---|---|---|---|
| scripts/check_civic_tokens.mjs | repo.sh | WCAG contrast floors of the civic token layer from shipped CSS | STRUCTURE: readFileSync(index.html), regex on inline `<style>` selectors/`--prop:` | token block scoped `:not([data-theme="archive_diary"])`, `color: var(--hue)`, `#0B4F44`, `--cta/--ac2` literals | none | **rewrite**: read the extracted token CSS file (Phase 4) |
| scripts/check_index_dead_tokens.py | repo.sh | no custom property overridden by a later identical selector | STRUCTURE: `re.finditer(<style…>)` over index.html | every inline `<style>` block | none | **rewrite**: parse the .css files (Phase 4) |
| scripts/check_landing_shell.mjs | repo.sh | static civic shell == `civic-search.js homeHtml()` (ko); first-paint contract | STRUCTURE: slice between START/END markers; many regexes | shell markers; `<header class="hero-container" id="hero">`; body classes `civic-refresh landing`; inline head CSS hide rules; exact `<script defer src="assets/js/civic-search.js(?v=…)?" onerror=…>`; `search-suggest.js` ordered before it; Google Fonts `media="print" onload=`; civic-search.css in head; shell ids | landing-boot.spec (CI, chromium+webkit); search-first-home.spec (CI) | **rewrite**: keep the shell-equality build contract (run it against built `dist/index.html`), drop the script/CSS tag regexes (covered) |
| scripts/check_live_feature_surface.mjs | repo.sh, npm | every public feature has a landing entry + implementation hook | STRUCTURE: regex on raw index.html | `id="searchToggleBtn"…data-action="toggle-search"`; dispatcher keys `'toggle-search':`, `'open-short-stay':`, `'open-jobcode-modal':`, `'open-jurisdiction-modal':`, `'open-agent-finder':`, `'open-med-finder':`, `'reveal-home-section':`; `class="p-gw-util"…data-action`; ids gwNewHomeLink, pathwaySection, reminderSection; hrefs to form-helper/ai/new-home; also reads backend-origin.js + landing-utility-restoration CSS | landing-utilities.spec (CI) "all utilities remain reachable"; search-first-home.spec | **rewrite**: retire the dispatcher-key half (covered by landing-utilities + golden), keep a slim markup-entry check |
| scripts/check_index_hardcoded_text.mjs | i18n.js; BT (test_i18n_law_fallback_live_smoke) | no hardcoded UI text in inline JS; i18n runtime markers present | STRUCTURE: `<script>` regex, sliced between `const LANGUAGE_STORAGE_KEY` and `function toggleTheme()` | those markers; `BOOTSTRAP_KO_FALLBACK = {…\n};`; `I18N_MANIFEST_PATH`, `loadI18nTranslations`, `tx(`, `data/i18n/manifest.json` | none | **rewrite**: scan the extracted source modules (otherwise passes with nothing scanned) |
| scripts/smoke_static_i18n.mjs | repo.sh, npm | i18n fallback guards exist; every inline script parses | STRUCTURE: `includes('BOOTSTRAP_KO_FALLBACK')`, `includes('hasFullKoI18nPack()')`, absence of two legacy expressions; `new Function(script)` on every inline script; asserts on check_index_hardcoded_text.mjs source | listed strings | none | **rewrite**: Vite owns parsing; point marker checks at the module |
| scripts/check_employment_reporting_helper.mjs | repo.sh, npm | job-code helper markup/microcopy; real search/scoring/memo functions | STRUCTURE: includes/regex + `vm.runInContext(html.slice('// --- Job Code Modal · HiKorea' … '\nfunction fallbackCopy('))` | ids jcScopeWarn, jcSpecialStates, jcChecklist, jcResultsGate, jcFinalCheck, jcSelOcc, jcSelInd, jcIncome, jcCopyBtn, `type="search" id="jcSearchInput"`; CSS `.jc2-search-input{width:100%}`; functions normalizeJobcodeText, getJobcodeSearchTerms, scoreJobcodeRow, getScoredJobcodeRows, jobcodeEmptyHtml, buildJobcodeMemo, renderJobcodeGuidance, JC_AMBIGUOUS_TERMS; globals `_jobcodeData`, `_jcSelected`, `tx`, `escapeHtml`, `hl` | partial: question-understanding.spec | **rewrite**: extract a jobcode module exporting these functions |
| scripts/check_deadline_helpers.js | manual | deadline maths, D-day label, ICS/Google Calendar builders | STRUCTURE: `extractRange('function paradisoDeadlineAddDays(', '\nfunction downloadDeadlineIcs(')` + new Function | those functions and adjacency | partial: ui-consistency.spec (not CI) | **rewrite**: import from the extracted module |
| scripts/check_placeholder_suppression.js | manual | renderer suppresses placeholder rows/empty blocks/diagnostics; ai.html dev gating | STRUCTURE: brace-matched `extractFunction` + body regex; spawns 4 other manual checks | isDocPlaceholder, dedupeDocs, renderDocTags, renderProcedurePanel, renderDocumentTabPanel, renderProcedureFeeBox, renderDocGroup, renderResults bodies; DOC_PLACEHOLDER_TOKENS; ai.html `devDiagnosticsEnabled`, `data-diagnostics="developer"`, `buildGroundingNote` | partial: application-form-wording.spec (not CI) | **rewrite**: unit-test exported renderers |
| scripts/check_static_visa_result_cards.js | manual | procedure-tab contract: structured requirements merged; fee notice | STRUCTURE: extractFunction renderResults/getProcedure/insertFeeNotice + regex | `getSourceConfirmedEntriesForProcedure`, `mergeDocGroups(structuredDocs, rawDocs, legacyDocs)`, `sourceConfirmed: hasAnyDocs(structuredDocs)`, SOURCE_CONFIRMED_PROCEDURE_KEY_MAP, `통합신청서(별지 제34호 서식)`, `const summarySubs = …` | partial: bilingual-doc-names.spec (not CI) | **rewrite**: function-level unit tests |
| scripts/check_subcode_modal.mjs | repo.sh | subcode modal structure/a11y/wiring; builder over every subcode | STRUCTURE: extractFunction buildSubcodeModalView/renderSubcodeProcedureVariants + eval; regex on markup/CSS | ids subcodeDetailOverlay (role=dialog…), subcodeModalTitle, subcodeModalBody; dispatcher entries; `anyModalOpen = [...'subcodeDetailOverlay'`; `.subcode-detailview .subcode-modal-box{…}` CSS; `titleEl.focus()` | none | **rewrite**: builder test via import; wiring → golden e2e |
| scripts/check_exact_code_search.js | manual | data-testid hooks, `?q=`, exact-rank thresholds | STRUCTURE: HTML.includes of JS literals; regex + new Function on normalizeCodeLikeQuery | `data-testid="visa-search-input"/"visa-search-submit"/"procedure-tab"`, `dataset.testid='visa-result-card'`, `URLSearchParams…get('q')`, `isCodeLikeQuery(qParam)`, `v._exactRank >= 10000/5000` | search-smoke.spec (not CI); search-result-unification.spec (CI) `?q=D-2` | **retire** once golden covers `?q=` and exact-code search (manual-only today) |
| scripts/check_doc_master_integrity.py | manual | every referenced doc id exists + DOC_DICT label; renderDocTags fallback | STRUCTURE: regex `const DOC_DICT = \{(.*?)\n\};` | DOC_DICT literal; `문서요건(`; `docDefinitionNeeded`/`문서 정의 필요` | none | **rewrite**: DOC_DICT → JSON read by app and checks |
| scripts/audit_procedure_journeys.js | manual | per-status procedure matrix and risk flags | STRUCTURE: regex `const PROCEDURE_CONFIG = […]` | PROCEDURE_CONFIG literal | none | **rewrite**: config from module/JSON |
| scripts/check_complex_status_guide.mjs | repo.sh | ComplexStatusGuide pure functions; CTA suppression | MIXED: require modules; regex on index | exact `<script defer src="assets/js/complex-status-guide.js"></script>`; `COMPLEX_GUIDE_MIGRATED = […]` | complex-status-guide.spec (not CI) | **rewrite** index parts: drop tag regex; read COMPLEX_GUIDE_MIGRATED from module |
| scripts/check_complex_status_guide_qa.mjs | repo.sh, npm | same, ko+en, 7 statuses | MIXED | same tags + f4 tag; COMPLEX_GUIDE_MIGRATED | complex-status-guide.spec | **rewrite** index parts |
| scripts/check_visa_route_guide.mjs | repo.sh | route-guide adapter, URL state machine, wiring | MIXED | exact visa-route-guide.js tag; `ParadisoRoute.start(code`; `openVisaDrawer(code)`; `anyModalOpen = [...'routeGuideOverlay'`; `data-procedure-panel=`; `data-action="select-procedure" data-procedure="`; `paradiso:results-rendered` dispatch | partial: complex-status-guide.spec | **rewrite** index parts |
| scripts/check_f4_route_guide.mjs | repo.sh | F-4 hub data/overlays/FAQ/a11y | MIXED: new Function on regex-extracted computeRoute/computeF4Path; index includes | `assets/js/f4-route-guide.js`; `id="f4RouteGuide"`; `GENERIC_VISA_ISSUANCE_EXCLUDED_CODES = new Set(['F-4'`; `renderVisaIssuanceSection…isGenericVisaIssuanceExcluded` | partial: restore-trust, result-hierarchy | **rewrite** index parts |
| scripts/check_visa_issuance_ui.mjs | repo.sh | every non-F-4 issuance record renders; chip derivation | MIXED: extractFunction deriveIssuanceRouteChips/normalizeVisaCode/isGenericVisaIssuanceExcluded + new Function; Set literal regex | those functions/literal; f4 tag/id; SOURCE_EVIDENCE_LABELS | none | **rewrite**: import from module |
| scripts/check_visa_issuance_scenario_guide.mjs | repo.sh | E-8/E-9/E-10 scenario data; popup wiring; i18n keys | MIXED: data + includes | `function renderIssuanceScenarioPicker/openIssuanceGuide/chooseIssuanceMode/applyIssuanceModeSelection/clearIssuanceGuide`; ids issuanceGuideOverlay, issuanceGuideChoices; dispatcher keys; CSS `.issuance-needs-pick.has-selection…` | none | **rewrite** |
| scripts/validate_visa_issuance_enrichment.js | repo.sh, npm | issuance enrichment layer + UI hooks | MIXED: includes/regex; slice renderVisaIssuanceSection…renderCautionBlock (function order) | `v._exactRank` literals, GENERIC Set, `isGenericVisaIssuanceExcluded( v.code )`, f4 tag/id, `deriveIssuanceRouteChips`, `issuance-route-chip`, `tx('issuanceStageLabel')`, adjacency | none | **rewrite** |
| scripts/check_hikorea_reservation_helper.mjs | repo.sh, npm | helper path logic, i18n, wiring | MIXED: brace-extract computeReservationPath from module + new Function; index includes | `assets/js/hikorea-reservation-helper.js`; `ParadisoReservationHelper`; absence of `hikoreaGuideState`, `generateHikoreaPassword` | partial: landing-utilities, ui-consistency | **rewrite** index parts |
| scripts/check_short_stay_rules.mjs | manual | short-stay rules; index stays lightweight | MIXED: new Function(checkerJs); index includes | no obscure country names; `assets/js/short-stay-checker.js`; `id="shortStayChecker"`, `id="shortStayModalOverlay"` | partial: landing-utilities, search-first-home | **rewrite** index parts |
| scripts/check_manual_reader.mjs | repo.sh, npm | manual-reader data, deep links, manual.html wiring | MIXED: require manual-reader-route.js; regex | exact manual-reader-route.js tag, `href="manual.html"`; manual.html script paths, PDF noscript | manual-reader.spec (CI) | **rewrite**: drop the index tag regex |
| scripts/check_document_help.mjs | npm | document-help records, alias resolution, rendering | MIXED: require document-help.js; index includes | `id="documentHelpOverlay"`, `loadDocumentHelp();`, `renderDocumentHelpButton(…)` call sites, `!focusable.includes(document.activeElement)` | none | **rewrite**: call-site markers → module/e2e test |
| scripts/check_employment_checklist.mjs | repo.sh, npm | guided checklist state model; DOM render smoke | MIXED: imports .mjs modules; section 12 vm on the Job Code Modal slice | same slice markers; renderEmploymentChecklist, renderEmploymentWeakHelp, renderEmploymentInterpretation, renderEmploymentRefine, renderJobcodeList, getScoredJobcodeRows, getJobcodeSearchTerms, jcApplyFlow, jcDismissClarification; `_jc*` globals | none | **rewrite** section 12 |
| scripts/check_unified_search.mjs | repo.sh, npm | unified-search builders; UX-10 a11y | MIXED: new Function(module); index regex | CSS `.us-interpret-value…{word-break:keep-all…}`; `<a class="skip-link" href="#mainContent" data-i18n="skipToContent">` first focusable; `id="mainContent"`; `.skip-link{…}` rules | ux10-a11y.spec (not CI) | **rewrite**: CSS asserts → CSS file; skip-link → golden |
| scripts/check_search_multilingual.mjs | repo.sh, npm | home search in all 15 languages | MIXED: new Function on 4 modules; locales from `html.slice('const LANGUAGE_OPTIONS' … '];')` | LANGUAGE_OPTIONS literal | partial: language-control.spec (CI) | **rewrite**: locales from JSON/module |
| scripts/check_official_terms.mjs | i18n.js | glossary/manifest invariants; Unicode/credential scans | MIXED: regex `const LANGUAGE_OPTIONS = […]`, `const DOC_DICT = {…}`; raw scans of index/ai/form-helper | the two literals | none | **rewrite**: literals from JSON; scan src dirs |
| scripts/check_official_external_sources.mjs | repo.sh, npm | official-source registry; New Home rendering; visa UI links | MIXED: data + includes; new-home `<link>`/`<style>` regex | `record.coveredCodes.some`, `issuance-mission-link`, no `<select>${options}</select>`, caution sentence, visa.go.kr / immigration.go.kr hrefs; new-home css link, `nh-official-badge` | partial: new-home.spec (not CI) | **rewrite** |
| scripts/check_exact_code_search_coverage.py | manual | Python re-implementation of exact-code resolution | MIXED: regex `const ALIAS_MAP = {…};` | ALIAS_MAP literal | search-smoke.spec (not CI) | **rewrite**: ALIAS_MAP → JSON |
| scripts/check_status_variant_indexing.py | manual | variant statusCode reachable by exact search | MIXED: `"variant.statusCode" in html and "getExactQueryMatchRank" in html` | two substrings | none | **rewrite** into module check |
| scripts/check_doc_master_id_migration.py | manual | doc_master ids are machine ids; refs resolve | MIXED: `f'"{ref}":' in html` | DOC_DICT key shape | none | **rewrite**: DOC_DICT → JSON |
| scripts/check_dummy_text.mjs | repo.sh | no dummy/provenance markers in data and frontend | MIXED: JSON scans + raw indexOf over index.html, ai.html | file list | none | **rewrite**: add the extracted source dirs |
| scripts/check_public_dummy_text.mjs | repo.sh, npm | rendered-surface + raw scan of entry HTML and asset dirs | MIXED: JSDOM (no scripts) of index/ai/form-helper/new-home; raw scan assets/js, assets/css | `HTML_ENTRY_FILES`, `JS_CSS_DIRS` | none | **keep**; update file/dir lists |
| scripts/check_ai_architecture.py | repo.sh | backend origin single-sourced; provider rules | MIXED: glob `*.html` + `assets/js/**/*.js` | glob roots | none | **keep**; extend globs to src |
| scripts/check_enforcement_ui.mjs | repo.sh, npm | enforcement UI/CSS contracts | MIXED: mostly enforcement.html/enforcement.css/enforcement-ui.mjs; `indexOf('assets/js/backend-origin.js')` ordering | index: `includes('enforcement.html')` only | partial: search-first-home | **keep**; update path asserts |
| scripts/audit_waymaker_production.py | manual | privacy-safe production audit | BEHAVIOR: regex for railway URL fallback across backend-origin.js, ai.html, index.html | none of substance | n/a | **keep** |

## B. Checks on ai.html
| path | invoked | coupling / dependencies | e2e | rec |
|---|---|---|---|---|
| scripts/check_ai_shell_semantics.js | BT (test_ai_shell_source_semantics.py, test_ai_answer_pipeline_contract.py) | STRUCTURE: extractFunction t, tt, generateBadges, renderGroundingSourcePanel, sourcePanelCopyForState, lawSourcePanelMessage, normalizeAnswerMetadata, sendAi; `extractConst('ANSWER_BASIS_LABELS')`; eval; `id="referenceDisclaimer"`, `id="sendBtn"` | partial: waymaker-answer-card.spec (CI) | **rewrite** (Phase 5): import from module |
| scripts/smoke_ai_live_quality.py | manual/live; imported by BT | MIXED: static regex signals from ai.html | waymaker-answer-card | keep; update static part |
| scripts/smoke_ai_payload.js | manual | BEHAVIOR (mirrors matchers, drift risk) | none | keep |

## C. Checks on the other root pages (MIXED; break on hashed filenames / moved paths)
| path | invoked | technique / dependencies | e2e | rec |
|---|---|---|---|---|
| scripts/check_address_helper.mjs | repo.sh, npm | JSDOM address-helper.html `runScripts:'outside-only'`, eval of address-ocr-core.js + address-helper.js; asserts asset order and controller ids; civic-search.js tile string | address-helper.spec (not CI) | keep; rewrite asset-order assert |
| scripts/check_immigration_checklists.mjs | npm; immigration-checklists-mobile-qa.yml | includes `id="cards"`, `id="office"`, `id="edit-dialog"`, `assets/js/immigration-checklists.js` | immigration-checklists.spec | keep; drop path assert |
| scripts/check_checklist_release_fallback.mjs | manual | JSDOM + eval; #office, #count, #guided-discovery, #release-preview-banner | partial | keep |
| scripts/check_navigation_labels.mjs | manual | JSDOM form-helper + immigration-checklists + evals; nav hrefs | partial: multilingual-checklists | keep |
| scripts/check_enforcement_nl_ux.mjs | repo.sh, npm | enforcement.html ids; source substrings of enforcement-ui.mjs, api/enforcement/confirm.js | none | keep |
| scripts/check_preview_mvp.mjs | npm | preview.html includes preview.css/preview-data.js/preview-app.js; vm on the two JS files | none | keep; update path asserts |
| scripts/check_search_tools_reliability.mjs | repo.sh, npm | JSDOM synthetic shell + eval(civic-search.js); enforcement.html + eval; slices `async function request(` … `\nfunction detectLocale` | partial: search-resilience | keep (module-level) |
| scripts/check_legal_source_search_dom.mjs, scripts/check_waymaker_navigator_dom.mjs | repo.sh, npm | BEHAVIOR: JSDOM synthetic HTML; require module | waymaker-navigator.spec | keep |

## D. Behaviour checks loading assets/js modules only (never index.html): keep
new Function/vm/eval loaders: audit_evidence_volume, audit_status_procedure_grid, check_current_manual_corpus, check_document_guidance, check_document_physical_form, check_fee_rules, check_legal_verification_scope, check_local_practice, check_question_understanding, check_result_hierarchy, check_search_result_unification, check_search_router, check_search_suggest, check_status_resolver, check_waymaker_quick_answer, check_i18n_quality, check_r5_review_findings (manual), evaluate_r5_search_benchmark (manual), build_landing_shell `loadCivic`.
require loaders: check_f4_guide_flow, check_form_helper, check_legal_source_search, check_waymaker_navigator, module parts of check_complex_status_guide / check_visa_route_guide, tests/unit/address-helper.test.js, qa/form_long_text_20260923.mjs.
Regex-extract from module source: smoke_f4_hub (`function computeRoute(a){…}`), check_popup_i18n (STR_KO/STR_EN).
**Constraint for Phase 2/3:** these need assets/js files to stay loadable as classic scripts (IIFE/UMD exposing globals or `module.exports`). Converting them to ESM `export` syntax makes `new Function`/`vm` throw. Decision: keep the shipped runtime files as IIFE/UMD and let Vite wrap them; or convert check loaders to `import()` alongside the module conversion (one check per module move; recorded per move in STATUS.md).

## E. Mentions index.html, never reads it
audit_duplicate_render_content.py (repo.sh), check_required_documents_coverage.py (repo.sh), audit_registration_procedure_coverage.py (Python mirrors of renderer logic; drift silently); employment_*.mjs comments; update_short_stay_rules.mjs, cleanup_*_2026_06_08.py, fix_d4_*_2026_05.py, populate_reentry_*_2026_05.py (comments); scripts/tests/test_check_source_updates_catalogs.py (fixture name false positive); requirements-manual-reader.txt.

## F. Browser drivers navigating to page URLs (behaviour-level; need `dist/` as server root after Phase 2)
CI (repo-validation): scripts/mobile_render_qa.mjs (puppeteer), scripts/mobile_webkit_qa.mjs. Manual: browser_status_matrix.mjs, capture_after_screenshots.mjs, capture_baseline_screenshots.mjs, every `scripts/qa/*.mjs` (dated one-offs).

## G. E2E specs that are fragile under the refactor
- Hard-coded asset paths in `page.route`: landing-boot.spec `**/assets/js/civic-search.js*` (CI); landing-utilities.spec `**/assets/js/short-stay-checker.js` (CI). Break with hashed filenames → must become glob `**/civic-search*.js` etc. in Phase 2.
- Calls into inline-script globals that extraction removes: `renderResults` (search-smoke, unified-search, complex-status-guide, bilingual-doc-names); `executeSearch` (easy-mode, bilingual-doc-names, complex-status-guide); `renderDocumentTabPanel`/`DOCUMENT_TAB_CONFIG` (bilingual-doc-names); `VISA_DATA`, `paradisoCanonicalAppFormText` (application-form-wording); `isLanguageSelectable` (language-control, CI); `applyLanguage` (easy-mode, bilingual-doc-names); `window.openGlobalSettings` (easy-mode). Many CI specs also wait on `typeof VISA_DATA !== 'undefined'` in `boot()`. Phase 3 must keep these as explicit window globals (a compatibility surface) until the specs are migrated, and record each removal.
- `playwright.config.mjs` webServer serves the repo root via `python3 -m http.server`.

## H. Build / generate tools (write files; not checks)
| path | writes | kind |
|---|---|---|
| scripts/build_landing_shell.mjs | index.html shell between markers from `civic-search.js homeHtml()` | **live build step** (enforced by check_landing_shell in repo.sh; imported by check_search_suggest, check_search_tools_reliability) |
| scripts/apply_detail_aliases_and_doc_ui_2026_05.py | visa_data.json; index.html (injects S8, S9 shims) | one-off migration (dated) |
| scripts/audit_patch_doc_terms_fees_2026_05.py | visa_data.json, backend visas.json, index.html (S10 shim), reports | one-off (dated) |
| scripts/apply_employment_reporting_helper_index_patch.py | index.html (inserts after `jc-ai-search-row`) | one-off (undated, unreferenced) |
| scripts/build_structured_documents.py | visa_data.json (reads DOC_DICT) | one-off, unreferenced |
| scripts/generate_manual_coverage_audit_2026_06_08.py | audit JSON/MD (DOC_DICT regex) | one-off (dated) |
| scripts/build_theme_skin_map.py | assets/css/visable-theme-legacy.css (reads `<style>` of 7 pages) | generator with `--check`, unwired; needs tinycss2 |
| scripts/build_procedure_classifier_lexicon.cjs | lexicon (requires search-router.js) | live: waymaker-ai-experiments.yml `--check` |
| scripts/build_manual_reader.py | data/manual-reader | live: repo.sh + npm `--check` |

## Key recommendations (feed Phases 2-3, 7)
1. Move shared literals to JSON: DOC_DICT, ALIAS_MAP, LANGUAGE_OPTIONS, PROCEDURE_CONFIG, COMPLEX_GUIDE_MIGRATED (each regex-parsed by 2-6 scripts).
2. Export pure functions from the extracted modules (deadline helpers, jobcode helper ×2, subcode modal, issuance route chips, result-card renderers, ai.html shell).
3. Point CSS checks at CSS files (civic_tokens, index_dead_tokens, unified_search CSS parts, subcode_modal CSS).
4. Drop exact `<script defer src=…>`/`?v=` regexes in ~10 checks (covered by landing-boot, manual-reader, landing-utilities + golden), or run them against built `dist/index.html`.
5. Fix e2e fragility first (section G) before Phase 2/3.

## Retire mapping (to be executed in Phase 7 only when the golden test exists and is green)
| legacy check | covering golden test (tests/golden/) | status |
|---|---|---|
| check_exact_code_search.js (manual) | search.spec: `?q=D-2` opens the searched state; exact code D-2 / subcode E-7-1 interpretation | pending golden |
| check_live_feature_surface.mjs dispatcher-key half | home.spec: every landing tool opens (dialog/page) in ko+en | pending golden |
| check_landing_shell.mjs script/CSS tag regexes | fail-closed.spec: civic script load failure → reload row | pending golden |

## Addendum (2026-11-03) — backend/tests modules that slice index.html source

Missed by the original map; found when the `validate` CI job went red after the first Phase 3 moves. These `unittest` modules read `index.html` (and some read `ai.html`, `assets/js/*.js`) as text and anchor on function names, fetch literals and `tx('…')` keys. Each Phase 3 move must re-run `python3 scripts/run_backend_tests.py` and repoint anchors at the module file the code moved to (never weaken the assertion).

- `backend/tests/_i18n_pack_support.py`
- `backend/tests/test_ai_answer_regression_source_subcode_2026_06.py`
- `backend/tests/test_ai_shell_source_semantics.py`
- `backend/tests/test_core_journey_ux_hardening.py`
- `backend/tests/test_expanded_route_wizard.py`
- `backend/tests/test_grounding_readiness_transparency.py`
- `backend/tests/test_i18n_law_fallback_live_smoke.py`
- `backend/tests/test_i18n_sweep_route_wizard.py`
- `backend/tests/test_law_tools.py`
- `backend/tests/test_openrouter_model_candidates.py`
- `backend/tests/test_paradiso_backend.py`
- `backend/tests/test_reentry_procedure_coverage.py`
- `backend/tests/test_route_aware_deadline_i18n.py`
- `backend/tests/test_scenario_procedure_variants.py`
- `backend/tests/test_waymaker_answer_product_quality.py`
- `backend/tests/test_waymaker_answer_state_polish.py`

Repointed so far: `test_core_journey_ux_hardening.py`, `test_grounding_readiness_transparency.py`, `test_route_aware_deadline_i18n.py` (deadline calculator → `src/features/deadline.js`; `/api/ask` call → `Visable.data.postRaw`), `test_i18n_law_fallback_live_smoke.py` (jurisdiction → `src/features/jurisdiction.js`), `test_i18n_sweep_route_wizard.py`, `test_scenario_procedure_variants.py` (`/api/ask` call).

Repointed with the C14–C16 move (`src/docs/normalize.js`): `scripts/check_exact_code_search.js`, `scripts/check_placeholder_suppression.js`, `scripts/check_static_visa_result_cards.js`, `scripts/validate_visa_issuance_enrichment.js`, `scripts/check_visa_issuance_ui.mjs`, `scripts/check_status_variant_indexing.py`, `backend/tests/test_i18n_sweep_route_wizard.py`, `backend/tests/test_scenario_procedure_variants.py`. Rule: a corpus for brace-matching slicers puts the module before index.html (the inline stub has the same signature).

**Corpus rule, made shared (procedure-panel move):** `scripts/frontend_modules.json` lists the extracted modules; `backend/tests/_i18n_pack_support.frontend_source()` and the Node checks check_exact_code_search.js, check_placeholder_suppression.js, check_static_visa_result_cards.js and check_visa_route_guide.mjs read modules-then-index.html from it. Backend tests switched to `frontend_source()`: test_core_journey_ux_hardening, test_expanded_route_wizard, test_grounding_readiness_transparency, test_i18n_sweep_route_wizard, test_route_aware_deadline_i18n, test_scenario_procedure_variants. Add every new module to the JSON list in the same commit as the move.

Switched to the corpus with the sections move: check_hikorea_reservation_helper.mjs, check_subcode_modal.mjs, check_visa_issuance_ui.mjs, check_f4_route_guide.mjs, check_complex_status_guide.mjs, check_visa_issuance_scenario_guide.mjs, validate_visa_issuance_enrichment.js.
