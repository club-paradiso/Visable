# Structural map: main inline script in index.html, plus the 4 id'd scripts after it

**Line numbers.** All numbers below are from the committed `HEAD` (e9e4a2f, 26,910 lines). The working tree has 2 extra lines because `<script type="module" src="src/main.js">` was added at line 29. **Add +2 to every number when you work in the current working tree.** I modified no files.

## Block boundaries (HEAD)

| Block | Lines | Notes |
|---|---|---|
| Main inline `<script>` | 16104–16318 | Opening tag 16104, `</script>` 16318. 601 top-level statements, 592 distinct top-level names. Preceded by `document-help.js` (16103, classic, non-defer). |
| `DETAIL_CODE_RESOLVER_SHIM_2026_05` | 26320–26488 | IIFE |
| `DOC_SECTION_UNIFICATION_SHIM_2026_05` | 26491–26573 | IIFE |
| `DOC_TERM_FEE_UI_SHIM_2026_05` | 26576–26751 | IIFE |
| `visable-global-settings-20260713` | 26753–26849 | IIFE |
| After these | 26854–26908 | Deferred classic scripts: zh-traditional, index-i18n-fallback, short-stay-checker, f4-route-guide, unified-search, visa-route-guide, complex-status-guide, hikorea-reservation-helper, manual-corpus-search, search-suggest, manual-reader-route, civic-search, search-router, status-guidance, waymaker-quick-answer, local-practice-report. Plus 2 `type=module` scripts: `scripts/employment_code_analyzer.mjs` and `scripts/employment_checklist.mjs`. |

### Scoping fact that affects every extraction step
- In a classic script, top-level `function` declarations become `window` properties.
- Top-level `const`/`let` do **not**. They live in the shared global lexical scope. Other classic scripts and `page.evaluate` can still reach them by bare name, but `window.X` returns `undefined`.
  - Examples: `VISA_DATA`, `dataReady`, `currentLanguage`, `selectedLocale`, `LANGUAGE_OPTIONS`, `UI_TRANSLATIONS`, `API_BASE`, `I18N_MANIFEST`, `DOCUMENT_TAB_CONFIG`, `ALIAS_MAP`, `PREDEF_KEYWORDS`.
  - `visa-route-guide.js:261-262` tries the bare name first, then `window.VISA_DATA`, which is undefined today.
- What breaks if one of these moves into a module:
  - It disappears for every consumer that uses the bare name.
  - A replacement `Object.defineProperty(window,'VISA_DATA',{get})` is only seen if no global `let`/`const` with the same name remains anywhere.
  - Inline writes such as `VISA_DATA = arr` (24658), `dataReady = …` (24658/24681), `currentLanguage = …` and `selectedLocale = …` (24093-24096) fail silently against a getter-only property in sloppy mode.
  - **Rule: mutable lexical globals keep their inline `let` owner until every consumer is migrated.** Modules read them through accessor functions on the bridge.

---

## 1. Top-level declarations, by cluster (HEAD lines)

Kinds: D = data constant, C = config, S = state, P = pure function, R = DOM renderer (builds HTML or writes DOM), E = event wiring or action, I = runs at parse time / init, L = loader (fetch).

### C01 UI helpers — 16105–16127
| Lines | Name | Kind | Purpose |
|---|---|---|---|
| 16108 | `escapeHtml` | P | Escapes via a div's `textContent` → `innerHTML`. **Escapes `& < >` only, not `"` or `'`.** |
| 16109 | `escapeRegExp` | P | Regex-escapes a string |
| 16110–16114 | `hl` | P | Escapes, then wraps keyword hits in `<mark class="h">` |
| 16115–16127 | `showToast` | R | Toast with `role=status` (`textContent`, safe) |

### C02 Document label dictionary — 16129–16166
`COMMON_NEW` (16130) and `COMMON_EXT` (16131) are D: lists of doc keys. `DOC_DICT` (16132–16166, 35 lines) is D: doc key → Korean label, includes fee strings.

### C03 City clock — 16167–16347
| Lines | Name | Kind | Purpose |
|---|---|---|---|
| 16171–16239 | `CITIES` | D | 69-line city list `{n,tz,flag,region}` |
| 16242–16265 | (top-level `try`) | I | Appends Intl time-zone cities to `CITIES` at parse time |
| 16267 | `SELECTED_CITY` | S | |
| 16269 / 16279 | `getTzHour` / `formatTzTime` | P | |
| 16283 | `applyCity` | E | Writes localStorage `paradiso_city`, writes DOM |
| 16290 | `updateHourFromCity` | R | Sets `body[data-hour]` |
| 16297 | `renderCityList` | R | |
| 16323 | `toggleCityMenu` | E | Calls `toggleLanguageMenu` (hoisted, from C27) |
| 16335–16347 | `initCity` IIFE | I | Reads localStorage, calls `applyCity`, `setInterval` every 30 s |

### C04 Core config, state, search debug — 16349–16437
| Lines | Name | Kind | Purpose |
|---|---|---|---|
| 16356–16359 | `API_BASE` | C | `VisableBackend.origin()`, else `PARADISO_BACKEND_URL`, else Railway host (empty string on localhost/file) |
| 16364 | `AI_REQUEST_TIMEOUT_MS` | C | 75000 |
| 16365–16372 | `VISA_DATA`, `VISA_ISSUANCE_RECORDS`, `VISA_ISSUANCE_BY_CODE`, `PROCEDURE_EVIDENCE_BINDINGS`, `PROCEDURE_EVIDENCE_BY_KEY`, `OFFICIAL_WEB_OVERLAYS`, `OFFICIAL_WEB_OVERLAY_POLICY`, `dataReady` | S | |
| 16373 | `qEl` | I | `getElementById('q')` at parse time |
| 16374–16381 | `SEARCH_DEBUG_ENABLED` IIFE | I | Reads URL |
| 16383 / 16403 / 16412 | `getSearchDebugSnapshot` / `ensureSearchDebugPanel` / `debugSearchState` | P / R / R | Debug panel; the last writes `window.__PARADISO_SEARCH_DEBUG__` |
| 16433 | `rcEl` | I | `getElementById('rc')` |
| 16434 | `currentSearchMode` | S | |
| 16435 / 16436 / 16437 | `CC` / `CL` / `getLabels` | D / D / P | Category colours and labels |

### C05 Modal core — 16439–16498
- S: `lastFocusedElement`, `activeModal`.
- P: `modalFocusables`.
- E: `syncModalScrollLock`, `trapModalFocus`.
- E: `openModal` (16463) and `closeModal` (16477). Used by visa-route-guide, short-stay-checker (via `window.`) and e2e.

### C06 Visa drawer — 16499–16567
`openVisaDrawer` (16499) and `closeVisaDrawer` (16543), both R/E. They move the rendered card into `#visaDrawerOverlay`.

### C07 AI modal and Waymaker handoff — 16568–16682
| Lines | Name | Kind | Purpose |
|---|---|---|---|
| 16568–16573 | `currentAiVisaCode`, `currentAiController`, `currentAiSelectedProcedureKey`, `currentAiSelectedProcedureVariantId`, `currentAiAnswerMode` | S | |
| 16574 + 16591 | `setupAiModeSelector` | E | Registered on DOMContentLoaded at 16591 |
| 16592 | `findProcedureVariant` | P | |
| 16597 | `openAiModal` | R | |
| 16645 | `selectedScenarioHandoff` | S | |
| 16646 | `buildWaymakerHandoffUrl` | P | |
| 16655–16674 | `syncWaymakerFab`, `setSelectedScenarioHandoff`, `clearSelectedScenarioHandoff` | R | |
| 16675 | `handleScenarioAiHandoff` | E | |

### C08 Document, subcode and FAQ modals — 16683–16902
- R: `openDocModal` 16683, `renderSubcodeProcedureVariants` 16736, `openSubcodeModal` 16823, `openFaqModal` 16886.
- P: `buildSubcodeModalView` 16760 (returns HTML).
- R: `renderModalFeeBox` 16847–16875. **Contains hard-coded fee strings at 16865–16866.**
- E: `window.verifyFaqWithAi` 16876.

### C09 Job-code finder (KSCO/KSIC) — 16903–18157, about 1,255 lines
**Moved** (2026-11-03) to `src/features/jobcode.js` as one module (not the four-file split suggested in §8 row 10; a split is a later refactor with the module in place). Inline stubs remain for the names in §8 row 10.
| Lines | Contents | Kind |
|---|---|---|
| 16903–16916 | `jcIcon`, `jcEnLike`, `jcLanguageName` | P |
| 16917–16974 | `JOBCODE_TARGET_VISAS`, `_jobcodeData`, `_jobcodeLoadPromise`, debounce timers, `_jcFilter`, `_jcLevel`, `_jcSelected`, `_jcIncome`, `_jcAnalysis`, `_jcAnalysisRequest`, `_jcResultCounts`, `_jcClarificationAnswered`, `_jcFlow`, `JOBCODE_JSON_PATHS` (16933), `JOBCODE_STOP_TERMS`, `JC_AMBIGUOUS_TERMS`, `JC_TYPE_LABEL*`, `JOBCODE_QUERY_EXPANSIONS` (16940–16974) | S / D |
| 16975–16993 | `loadJobcodeData` | L |
| 16994–17160 | Normalising and scoring: `normalizeJobcodeText`, `getJobcodeSearchTerms`, `jc*` accessors, `JC_LEVEL_RANK`, `jcLeafParentSets`, `jcIsLeaf`, `JC_GENERIC_NAME_WORDS`, `jcNormalizedRow`, `scoreJobcodeRow`, `getScoredJobcodeRows`, `jcMatchReason`, `jcConfLabel` | P |
| 17165–17311 | `jcCardHelp`, `renderJobcodeCard`, `jcSelectLabel`, `jobcodeEmptyHtml`, `renderJobcodeList`, `setJobcodeFilter`, `setJobcodeLevel` | R |
| 17312–17560 | `jcLooksNaturalQuery`, `searchJobcodeChip`, `openJobCodeModal`, `renderJobcodeGuidance`, flow helpers (`jcRevealAnswer`, `jcSetStep`, …), `renderJobcodeResults`, `selectJobcode`, `renderJobcodeSelectedSummary`, `buildJobcodeMemo`, `copyJobcodeMemo` | R / E |
| 17561–17611 | `_empLex`, `_empSources`, `_empAnalyzer`, `_empLoadPromise`, `ensureEmploymentAnalyzer` | L. Uses `window.EmploymentCodeAnalyzer` (module script loaded later). |
| 17612–18048 | `JC_CONF_LABEL`, `JC_MODE_LABEL[_EN/_ZH]` (17613–17633), `renderEmploymentInterpretation`, `…FollowupChips`, `jcDismissClarification`, `jcShow`, `jcApplyFlow`, `JC_SPECIAL_*` (17788–17801), `renderEmploymentSpecialStates`, `runEmploymentSpecialAction`, `…Refine`, `…Tips`, `jcLang`, `jcChecklistCopy`, `jcBuildChecklistState`, `JC_STATUS_*`, `renderEmploymentChecklist`, `JC_WEAK_EXAMPLES`, `renderEmploymentWeakHelp`, `clearEmploymentAnalysisUI`, `jcRowsFromAnalysis` | R / D |
| 18049–18150 | `searchJobcodeWithAI` | L / R. Dynamic `import()`. |
| 18151–18157 | `fallbackCopy` | P / E |

### C10 Jurisdiction finder — 18159–18580
- D: `JUR_DB` 18159–18422 (264 lines) and `OFFICE_INFO` 18424–18555 (132 lines).
- R: `initJurisdictionSelects` 18556, `updateSigungu` 18562, `showJurisdiction` 18569.
- E: `openJurisdictionModal` 18580.

### C11 AI analysis call — 18583–18925
- P: `isAiDevDiagnosticsEnabled` 18587 (reads localStorage), `formatAiModalAnswer` 18598 (escapes first), `buildProviderErrorHtml` 18610, `mapLawWarningToFriendly` 18635, `sourcePanelCopyForState` 18651, `lawSourcePanelText` 18669, `renderGroundingSourcePanel` 18693.
- L / R: `submitAiAnalysis` 18832–18924.

### C12 Document help, document guide, doc tags — 18926–19169
| Lines | Name | Kind |
|---|---|---|
| 18926–18928 | `documentHelpData`, `documentHelpMatcher`, `documentHelpLastTrigger` | S |
| 18930 | `loadDocumentHelp` | L |
| 18944 / 18948 | `findDocumentHelp` / `renderDocumentHelpButton` | P |
| 18955 / 18976 | `openDocumentHelp` / `closeDocumentHelp` | R |
| 18990–18991 | `docGuideData`, `loadDocGuide` | S, L |
| 19016–19057 | `buildDocGuideApplicability`, `buildDocGuideDrawer` | P (HTML) |
| 19058 | `toggleDocGuide` | E |
| 19068–19169 | `renderDocTags` | R (HTML) |

### C13 Procedure configuration and fees — 19170–19346
- D: `PROCEDURE_CONFIG` 19170–19193, `COMMON_MANUAL_WARNINGS` 19195–19202, `STAY_FEE_SOURCE_NOTE` 19204, `CARD_DELIVERY_SURCHARGE` 19209 (= 4000), `DEFAULT_PROCEDURE_FEES` 19210–19247.
- P: `formatWon` 19249, `getProcedureFeeInfo` 19254–19305 (**contains per-status fee override strings at 19262–19299**).
- P (HTML): `renderProcedureFeeBox` 19306–19346.

### C14 Code normalisation and visa naming — 19347–19578
**Moved** (2026-11-03) to `src/docs/normalize.js` (one module for C14–C16; `renderProcedureVariant` onward stays inline). 55 stubs remain inline; see DECISIONS ADR-009 addendum 2.
- P: `normalizeVisaCode`, `normalizeCodeLikeQuery`, `isCodeLikeQuery`, `getPrimaryCodeLikeQuery`, `getExactQueryMatchRank` (19406), `isEnglishMode`, `getVisaNameKo/En`, `getLocalizedVisaName`, `getSecondaryVisaName`, `getVisaSubcodes`, `getLocalizedSubcodeName`.
- D: `PROCEDURE_LABEL_INDEX` 19485–19497.
- P: `getProcedureLabelByKey/Label`, `isF5ResidenceCardReissuance`, `getProcedureDisplayLabel`, `localizeResultCount`, `getRecordSearchText`, `keywordMatchesCode`, `getMatchingSubcodes`, `getManualDomains`.
- P (HTML): `renderDomainBadges`, `renderReviewBadge`.

### C15 Document-requirement normalisation — 19579–20528, about 950 lines
**Moved** (2026-11-03) to `src/docs/normalize.js` (one module for C14–C16; `renderProcedureVariant` onward stays inline). 55 stubs remain inline; see DECISIONS ADR-009 addendum 2.
Mostly pure functions. Contents:
- `SOURCE_CONFIRMED_PROCEDURE_KEY_MAP` 19579–19599, `procedureKeyForSourceConfirmedType`, `getSourceConfirmedEntriesForProcedure`.
- `F4_OVERSEAS_KOREANS_FORM_PROCEDURES`, `PARADISO_APP_FORM_PIECE_RE`, `paradisoCanonicalAppFormPiece`, **`paradisoCanonicalAppFormText` (19642)**, `paradisoGlossaryLabelForAppForm`, `canonicalizeSourceConfirmedDocText`, `groupSourceConfirmedDocuments`, `sourceConfirmedManualRefs`, `mergeManualRefs`.
- `remapPermanentResidenceAcquisition`, `isSuppressedProcedureForStatus`, `getVisaIssuanceModeDocGroups`, **`getProcedure` (19782–19834)**.
- `DOC_GROUP_ALIASES` 19835–19840, `PARADISO_PROC_DOC_BLOB_*` regexes, `paradisoSplitProcedureDocBlob`, `toDocArray`, `DOC_PLACEHOLDER_TOKENS` 19920–19923, `isDocPlaceholder`.
- `PARADISO_DOC_*` thresholds and regexes (19935–19944), `paradisoSplitDocItem`, `dedupeDocs`, `paradisoSplitCompoundDocRow`, `PARADISO_DOC_FAMILY_RULES` 20102–20120.
- `DOCUMENT_REQUIREMENT_DISPLAY_FAMILY_RULES` 20168–20177, the `*DocumentRequirement*` helpers, `dedupeDocGroupsAcrossCategories`, `paradisoBuildDocDisplayGroups`, `mergeDocGroups`, `subtractDocGroupsForRender`, `normalizeDocGroups`, `flattenDocGroups`, `hasAnyDocs`, `countRenderableDocs`, `normalizeProcedureVariants` 20507.
- R: `renderDocGroup` 20524.

### C16 Manual text and procedure rendering — 20529–20926
**Moved** (2026-11-03) to `src/docs/normalize.js` (one module for C14–C16; `renderProcedureVariant` onward stays inline). 55 stubs remain inline; see DECISIONS ADR-009 addendum 2.
- P: `MANUAL_*` and `PARADISO_*_NOTE_RE` regexes, `paradisoFilterProcedureNotes`, `paradisoStripInternalReviewArtifacts` (20596), `stripManualArtifacts`, `normalizeManualText`, `paradisoSplitSentences`, `makeManualPreview`, `isLongManualText`.
- R: `renderManualDetailBlock`, `renderLabeledManualBlock`, `renderProcedureSummaryBlock`.
- `PROCEDURE_FEE_TILE_KEYS`; R: `renderProcedureDocGroups`, `renderDocDiscretionaryNote`, `renderDocGroupingSourceNote`.
- D: `PROCEDURE_EVIDENCE_TYPE_BY_KEY` 20719–20731, `SOURCE_EVIDENCE_LABELS` 20733–20755.
- Source-evidence helpers 20757–20857, then R: `renderProcedureHeader`, `renderScenarioSelectedContextBanner`, `renderProcedureVariant` (20893).

### C17 Scenario picker — 20927–21100
S: `scenarioPickerActiveSelector`, `scenarioPickerActivePanel`. E / R: `closeScenarioPicker`, `openScenarioPicker`, `chooseScenarioVariant`, `clearScenarioSelection`, `applyScenarioSelection`, `renderProcedureVariants` (21059).

### C18 Scenario checklist — 21101–21354 (localStorage)
- `SCENARIO_CHECKLIST_STORAGE_PREFIX` 21105, `SCENARIO_CHECKLIST_GROUPS` 21108–21111.
- P: `hashScenarioChecklistItem`, key builders.
- Storage wrappers: `scenarioChecklistStoreGet/Set/Remove` 21134–21143.
- R: `renderScenarioChecklist`.
- E: persist, sync, hydrate, collect, build text and print HTML, status, copy, print, reset (21196–21354).

### C19 Procedure panels — 21355–21439
R: `renderProcedurePanel`, `renderProcedures`. D: `PROCEDURE_FALLBACK_SUMMARY_KEYS`. R: `renderProcedureFallbackSummary`.

### C20 F-4 route wizard — 21440–21700
- D: `ROUTE_WIZARD_CONFIG` 21440–21534 (95 lines).
- `getRouteWizardConfig`, `isF4RouteWizardTarget`, `renderF4RouteChooser`, `selectF4Route`, `applyRouteSelection`.
- S: `routePicker*`. Then `openRoutePicker`, `chooseRoute`, `resetF4Route`.

### C21 Deadline calculator — 21701–21840 (no storage)
**Moved** (2026-11-03) to `src/features/deadline.js`; stubs `computeDeadlines`, `downloadDeadlineIcs` stay inline. `renderDeadlineCalculator` has no caller (unreachable UI; STATUS.md owner decision 5).
- P: `paradisoDeadlineAddDays/DaysFromToday/DdayLabel`, `buildDeadlineIcs` (local `esc` at 21730 is an ICS escaper), `deadlineGoogleCalUrl`.
- E: `downloadDeadlineIcs`.
- R: `deadlineRowHtml`, `computeDeadlines`, `renderDeadlineCalculator`.

### C22 Result-card sections — 21841–22196
- R: `renderSourceConfirmedRequirements`, `subcodeSourceChip`.
- P: `getParentVisaCode`, `isSubcodeOf`, `groupSearchResultsByParent`, `shouldAutoExpandSubcodeGroup`.
- R: `renderSubcodePreview`, `renderExpandableSubcodeGroup`, `renderSubcodes` (21955–22081), `renderParentScopeNotice`, `renderCommonWarnings`, `renderSourceReferences`.
- `openHikoreaGuide`, `renderHikoreaGuide`, `renderManualActions`, `renderNextActionArea`, `renderCardSummary`.

### C23 Visa issuance — 22197–22568
- Getters: `getVisaIssuanceRecord/Binding/Overlays`, `pickLocalizedManualText`.
- R: `renderIssuance*` (doc list, groups, steps, warnings, overlay selector).
- D / P: `GENERIC_VISA_ISSUANCE_EXCLUDED_CODES`, `isGenericVisaIssuanceExcluded`, `VISA_ISSUANCE_NOT_APPLICABLE_*`, `isVisaIssuanceNotApplicable`, `ISSUANCE_ROUTE_CHIP_INDEX` 22333–22340, `deriveIssuanceRouteChips`.
- R: `renderIssuanceRouteChips`, `renderIssuanceModeCard`, `renderIssuanceScenarioPicker`, `renderVisaIssuanceSection`.
- Issuance guide modal (S `issuanceGuideActiveGuide`): open, choose, apply, clear.
- `visaIssuanceProcedureAvailable`, `renderStandaloneVisaIssuanceSection`, `renderCautionBlock` (22565).

### C24 Document tabs and source-evidence panel — 22569–22813
- D: `DOCUMENT_TAB_CONFIG` 22569–22573, `DOCUMENT_DATA_MISSING_NOTICE` 22580, `DOCUMENT_REGISTRATION_MISSING_NOTICE` 22581.
- Helpers: `getDocumentTabLabel`, `isDocFieldMissing`, `formatDocumentTabRefNote`, `normalizeDocumentTabItems`, `getRegistrationProcedureTabItems`, `getDocumentTabItems`, `getDocumentMissingNotice`.
- R: `renderDocumentTabPanel` 22653, `procedureSectionOwnsDocuments`, `renderDocumentTabs` 22717, `activateDocsTab`, `renderSourceEvidencePanel` 22765.

### C25 Easy mode and card view modes — 22814–23093
- `EASY_MODE_*` constants.
- `globalEasyMode` 22820: **IIFE that reads localStorage at parse time.**
- `easyModeApplies`, `renderViewModeToggle`, `isEasyModeNonDocRow`, `cleanEasyModeDocName`, `getEasyModeDocGroups`, `renderEasyModePanel`.
- `applyCardMode`, `setCardMode`, `restoreCardViewModes`, `updateEasyModeButton`, `toggleGlobalEasyMode` (writes storage), `copyVisaResult` 23076.

### C26 Search and results — 23094–23572
- P: `calculateScore`, `getExactCodeMatchRank`. D: `ALIAS_MAP` 23146–23152. P: `expandKeywords`. D: `PREDEF_KEYWORDS` 23185–23190.
- `suggestionTypeForKeyword`; R: `showSuggestions` 23204.
- E: **`executeSearch` 23264**, `setDirectSearchToggleState`, `close/openDirectSearchMode`, `closeSearchBlockingSurfaces`, `handleDirectSearchToggle`, **`resetToLanding` 23358**.
- R: `renderCompactResults`, `reviewStateLabel`, **`renderResults` 23420–23535**.
- S: `dt`. E: `handleInput`, `handleAutocompleteKeydown`, `clearSearch`, `setSearchMode` 23571.

### C27 i18n runtime — 23573–24350
| Lines | Contents |
|---|---|
| 23573 | `LANGUAGE_STORAGE_KEY` |
| 23574–23594 | `LANGUAGE_OPTIONS` (D) |
| 23598–23599 | S: `selectedLocale`, `currentLanguage` |
| 23601–23621 | `contentLocaleFor`, `LANGUAGE_SUPPORT`, `languageSupportLevel`, `isLanguageSelectable` |
| 23622–23664 | `I18N_MANIFEST_PATH`, `I18N_BASE_PATH`, `UI_TRANSLATIONS`, `BOOTSTRAP_KO_FALLBACK` (23625–23657), `I18N_MANIFEST` (S, 23658) |
| 23666 / 23672 | `normalizeLocaleCode` / L: `loadI18nTranslations` |
| 23717–23743 | Visa-name pack |
| 23744–23858 | Official-terms glossary: index, lookup, `annotateOfficialDocLabel`, `renderAnnotatedDocLabel` |
| 23859 | `hasFullKoI18nPack` |
| 23868 | `I18N_DEV_WARNINGS` (**IIFE that reads localStorage at parse time**) |
| 23875 | **`tx`** |
| 23891–23933 | DOM setters `setText/Html/Attr/Indexed*` |
| 23934 | `localizeStaticDom` |
| 23958–23995 | `txArray`, `txAt`, `getLanguageOption`, `getStoredLanguage`, `getInitialLanguage` |
| 23996–24040 | R: `renderLanguageMenu`, `toggleLanguageMenu` |
| 24041–24086 | `getLandingHintItems`, `getQuickFilterItems`, `updateThemeLabel`, `updateSearchMetaText`, `applyTraditionalChineseMode` |
| 24087–24347 | **`applyLanguage`** (261 lines: about 190 `tx`, 95 `setText` calls; re-renders results and `initUI`, dispatches `paradiso-language-applied`) |

### C28 Theme and region labels — 24351–24459
- `updateThemeColorMeta`, `toggleTheme` (writes storage).
- D: `REGION_I18N` 24377–24396; `localizeRegion`, `localizeFinderRegions`.
- Editorial theme: `EDITORIAL_THEME_STORAGE_KEY`, `EDITORIAL_THEMES`, then get, current, label, apply, toggle (24421–24458).

### C29 Boot helpers and data load — 24460–24688
- `toggleAccordions`.
- **`initUI` 24462**: renders landing hints and quick filters (with `?q=` bootstrap), then `renderCmdChips`.
- `injectLocalData` (adds a hard-coded FAQ-0 record, 24510–24518), `setSearchEnabled`, `coverageBucket`, `coverageCodeSortKey`, `updateCategoryCounts`.
- `INTEGRATED_FORM_META`, `renderDocComposerTags`, `loadDocComposerMeta`, `buildProcedureEvidenceIndex`.
- L: **`fetchOptionalJson` 24628**, `loadVisaIssuanceData` 24639, `VISA_DATA_API_TIMEOUT_MS` 24653 (= 4000), **`loadVisaData` 24654–24687**.

### C30 DOMContentLoaded bootstrap and global event delegation — 24689–25138
- The single `[data-action]` dispatcher sits at 24783–24935. It handles about 75 actions; full list at 24787–24929.
- Overlay-backdrop close, outside-click close, keyboard handlers (24967 and 24975), `toggle` listener.
- Archive-diary masthead and random passport stamp at 25039–25136.

### C31 Landing animation — 25140–25326
- `_revealObs`, `_staggerObs`, `runCountUp`, `initScrollReveal` 25154 (called from DOMContentLoaded), `resetReveal`.
- **Anonymous scroll-reveal IIFE 25200–25221 runs at parse time.** It duplicates `initScrollReveal`: two IntersectionObservers on `[data-reveal]`.
- **`initFigmaAnagram` IIFE 25224–25326 runs at parse time.** It uses `load`, `resize`, `orientationchange`, a ResizeObserver and `setInterval`.

### C32 Visa manual journey tracks — 25328–25603
`startPreEntryTrack` 25331, `startInKoreaTrack` 25371, `PURPOSE_TO_CAT`, `ACTION_CAT_LABELS[_EN/_ZH]` 25411–25434, `DOC_MODAL_ACTION_MAP`, `_currentInKoreaAction`, `showVisaRecommendations`, `selectInKoreaAction`, `getCurrentInKoreaAction`, `filterInKoreaVisaList`, `searchInKoreaVisa`, `showVisaDocForAction`.

### C33 Agent finder — 25603–25805
`initAgentFinder` IIFE. **Fetches at parse time.** Local `escapeText` at 25624. Defines `window.updateAgentFinderLanguage` (25728).

### C34 Medical-institution finder — 25807–26005
`initMedFinder` IIFE. **Fetches at parse time.** Local `escapeText` at 25829. Defines `window.updateMedFinderLanguage` (25936).

### C35 Deadline reminders — 26007–26317
Anonymous IIFE. Keys `paradisoReminders` and `paradisoReminderBannerDismiss`. **Reads storage and renders the list and banner at parse time.**

### The four id'd scripts
| Script | What it does |
|---|---|
| DETAIL_CODE_RESOLVER (26320–26488) | On DOMContentLoaded, `installDetailResolver` rewrites the `#q` value in the capture phase of `#searchForm` submit, then restores it after `setTimeout(0)`. Its `warmFallbackRecords()` (26347, called at 26461) **always makes a second `fetch("visa_data.json")`** unless `window.__paradisoDetailAliasData` is already set. |
| DOC_SECTION_UNIFICATION (26491–26573) | On DOMContentLoaded: MutationObserver plus `setInterval` (12 ticks × 400 ms) that collapses duplicate required-doc summaries. |
| DOC_TERM_FEE_UI (26576–26751) | `FEE_BY_LABEL` 26580–26585, `TERM_REPLACEMENTS` 26587–26596. On DOMContentLoaded: MutationObserver plus `setInterval` (15 × 350 ms) running `patchAll`. `updateBareFeeCards` **actively rewrites "수수료" rows with `FEE_BY_LABEL` bodies**. `insertFeeNotice` is dead code (early `return` at 26693). |
| global-settings (26753–26849) | Runs at parse time. Defines `window.setGlobalBrightness`, `window.openGlobalSettings`, `window.closeGlobalSettings`. Listens for `keydown`, `paradiso-language-applied` and the `prefers-color-scheme` change. |

---

## 2. Initialisation and timing

### Listeners on DOMContentLoaded or load
| Line | Registration | Runs |
|---|---|---|
| 16591 | `document.addEventListener('DOMContentLoaded', setupAiModeSelector)` | First on DOMContentLoaded (registered first) |
| 24690 | `document.addEventListener('DOMContentLoaded', async () => {…})` | **Main entry.** Async, so everything after `await loadI18nTranslations()` at 24693 runs after the i18n fetches. |
| 25283–25284 | Anagram: `readyState==='complete' ? buildLines() : addEventListener('load', buildLines)` | window `load` |
| 26482–26483 | Shim 1 `installDetailResolver` | DOMContentLoaded, or immediately if not loading |
| 26567–26568 | Shim 2 `installDocSectionUnifier` | Same |
| 26745–26746 | Shim 3 `install` | Same |

There is no `window.onload`, no `requestIdleCallback`, and no `pageshow`/`popstate`/`hashchange` listener in these blocks.

### Main DOMContentLoaded handler, in order (24690–25138)
1. `ensureSearchDebugPanel()`
2. `applyEditorialTheme(getStoredEditorialTheme(), {persist:false})`
3. **`await loadI18nTranslations()`**
4. `renderLanguageMenu()`
5. `applyLanguage(getInitialLanguage(), {silent:true})`
6. `loadDocumentHelp()`, `loadDocGuide()`, `loadDocComposerMeta()`, `loadVisaData()`. All four are fired without awaiting.
7. Wiring: `qEl` input and keydown; `[data-action="toggle-search"]` in capture phase; `#searchForm` submit → `executeSearch`; `#citySearch`; `#jurSido` / `#jurSigungu`; `#jcSearchInput` input (200 ms debounce) and Enter; `#jcIncome` change.
8. `debugSearchState(...)`
9. Document-level `change` listener (scenario-checklist persistence) and document-level `click` listener (help trigger, `toggle-su`, the `[data-action]` dispatcher, `.ai-action-btn`, backdrop and outside-click closes).
10. Dispatch `visable:landing-actions-ready`. `backend-origin.js` uses it to replay an early tap.
11. Two `keydown` listeners, then `toggle` (capture).
12. `initScrollReveal()`, then archive-diary masthead and stamp (`insertAdjacentHTML`).

### The real "init UI" chain
`loadVisaData` (24654) → `applySuccess` → `await loadVisaIssuanceData()` → set `VISA_DATA`, `dataReady = true` → `setSearchEnabled(true)` → **`initUI()`** (24462) → `updateCategoryCounts()` → dispatch `paradiso:data-ready`.

On failure it dispatches `paradiso:data-failed` instead. `applyLanguage` also calls `initUI()` whenever `dataReady` is true.

### Code with side effects at parse time (corrects ADR-009)
ADR-009 says "every data load, storage read and render … happens in DOMContentLoaded/event handlers". **That is not true.** These run while the main block is being parsed:

| Lines | What runs |
|---|---|
| 16242–16265 | Intl time-zone merge into `CITIES` |
| 16335–16347 | `initCity`: **reads and writes localStorage `paradiso_city`**, writes `#cityBtn*` DOM and `body[data-hour]`, `setInterval(30000)` |
| 16373, 16433 | `qEl` and `rcEl` DOM lookups; 16374 `SEARCH_DEBUG_ENABLED` reads URL |
| 22820 | `globalEasyMode` **reads localStorage `paradiso:easyMode`** |
| 23868 | `I18N_DEV_WARNINGS` **reads localStorage `paradiso:i18n-debug`** (only when not on localhost) |
| 25200–25221 | Scroll-reveal IIFE (IntersectionObserver, inline `transitionDelay` styles) |
| 25224–25326 | Anagram IIFE (DOM build, listeners, ResizeObserver, `setInterval`, `setTimeout`) |
| 25604–25805 | Agent finder: **`fetch('data/agent_registry_2026-04-30.json')`** and listeners |
| 25808–26005 | Medical finder: **`fetch('data/designated_medical_institutions_2026_04_30.json')`** and listeners |
| 26014–26317 | Reminders: **reads localStorage**, `render()` and `showBanner()`, listeners. `tx()` falls back to `BOOTSTRAP_KO_FALLBACK` and Korean literals because `UI_TRANSLATIONS` is still empty. |
| 26753–26849 | Global-settings IIFE: defines window functions, registers listeners |

The `src/main.js` module in `<head>` is deferred. It runs after the whole document is parsed: after every inline classic block, before the defer scripts that come later in the document, and before DOMContentLoaded. So **parse-time inline code cannot call `window.Visable`**. Anything listed above has to stay inline, or be moved into a module and deferred. Deferring changes timing: first-paint city/hour, reminder banner, finder fetch start, and reveal styles.

### Does parse-time code depend on functions or bindings defined later?
- `initCity` → `applyCity` and `updateHourFromCity` are defined earlier. Its later dependency `toggleLanguageMenu` is a hoisted function and only used at event time. OK.
- The reminder, agent-finder and med-finder IIFEs (25604+) call `tx`. `tx` reads `UI_TRANSLATIONS`, `BOOTSTRAP_KO_FALLBACK`, `currentLanguage` and `I18N_DEV_WARNINGS`, all declared earlier (23599–23873), so there is no TDZ error. Finder `tx` calls happen in fetch callbacks anyway.
- **Hazard if extraction reorders code:** any parse-time code moved above line 23599 that touches `currentLanguage`, `UI_TRANSLATIONS` or `LANGUAGE_OPTIONS` would throw a TDZ ReferenceError.
- The shims read `VISA_DATA`, `LANGUAGE_OPTIONS` and `selectedLocale` lazily, inside DOMContentLoaded or event handlers, all with `typeof` guards. No shim depends at parse time on code defined later.
- Ordering detail: shim DOMContentLoaded listeners run **before** the post-`await` part of the main handler. The main click delegation only exists after the i18n packs load.

---

## 3. Cross-block dependencies (compatibility surface)

`fn` = function declaration (already on `window`). `lex` = top-level `let`/`const` (bare name only, not on `window`).

### (a) Main-block globals used by the four id'd scripts
| Global | Kind | Used at |
|---|---|---|
| `VISA_DATA` | lex | 26372–26373 (resolver, `typeof`-guarded) |
| `paradisoCanonicalAppFormText` | fn | 26612 (guarded), **26671 (not guarded)** |
| `LANGUAGE_OPTIONS` | lex | 26768, 26771 |
| `selectedLocale` | lex | 26776, 26780 |
| `updateThemeLabel` | fn | 26810 (guarded) |
| `updateThemeColorMeta` | fn | 26811 (guarded) |
| `localizeStaticDom` | fn | 26820 (guarded) |

Mentions in comments only: `getExactQueryMatchRank`, `qEl`, `renderProcedureFeeBox`.

The reverse direction also exists: the main block calls `window.openGlobalSettings`, `window.closeGlobalSettings` and `window.setGlobalBrightness` (24921–24928) from shim 4, and listens on the `#q` / `#searchForm` that shim 1 rewrites.

### (b) Main-block globals used by `assets/js` classic scripts (verified usages, not just matching names)
| Global | Kind | Consumers |
|---|---|---|
| `currentLanguage` | lex | complex-status-guide:40, f4-route-guide:78, hikorea-reservation-helper:219, legal-source-search:36, short-stay-checker:34, unified-search:44, visa-route-guide:225 (all `typeof`-guarded) |
| `selectedLocale` | lex | civic-search:120, 157 |
| `UI_TRANSLATIONS` | lex | civic-search:125–126 |
| `LANGUAGE_OPTIONS` | lex | civic-search:153 |
| `isLanguageSelectable` | fn | civic-search:160 |
| `dataReady` | lex | civic-search:797, visa-route-guide:1207 |
| `executeSearch` | fn | civic-search:801, status-guidance:1754 |
| `resetToLanding` | fn | civic-search:996 |
| `startPreEntryTrack` / `startInKoreaTrack` | fn | civic-search:486–487 |
| `VISA_DATA` | lex | visa-route-guide:261, complex-status-guide:929–930 |
| `openVisaDrawer` | fn | visa-route-guide:960, complex-status-guide:1238, 1309, 1381 |
| `closeVisaDrawer` | fn | visa-route-guide:1000 |
| `openModal` / `closeModal` | fn | visa-route-guide:633/641, short-stay-checker:1963–1981 (via `window.`) |
| `renderResults` | fn | visa-route-guide:837–845 (civic-search, form-helper-app and waymaker-navigator have their own local `renderResults`, not this one) |
| `openAiModal` | fn | visa-route-guide:908–938 |
| `openHikoreaGuide` | fn | visa-route-guide:975 |
| `showToast` | fn | visa-route-guide:954–978 |
| `paradisoStripInternalReviewArtifacts` | fn | visa-route-guide:296, 309 |
| `getVisaNameEn` | fn | visa-route-guide:304 |
| `isVisaIssuanceNotApplicable` | fn | visa-route-guide:345 |
| `txAt` | fn | visa-route-guide:373 |
| `toggleTheme` | fn | visable-theme.js:145 (`window.toggleTheme`) |

Mirrored by name in other files but not called across files: `PROCEDURE_CONFIG`, `PROCEDURE_LABEL_INDEX`, `VISA_ISSUANCE_NOT_APPLICABLE_CODES` (visa-route-guide keeps its own copies), `getProcedure` (mirrored), and `LANGUAGE_OPTIONS` order (nationality-interview-hub:1054).

**Not used by `assets/js`:** `tx(` (no real calls; `index-i18n-fallback` mentions it in a comment), `applyLanguage`, `API_BASE`, `escapeHtml`, `hl` (document-help, legal-source-search and unified-search define their own `escapeHtml`), `fallbackCopy` (manual-reader has its own).

**External globals the main block consumes** (they must exist on `window` before use): `VisableBackend` (backend-origin.js), `PARADISO_BACKEND_URL`, `PARADISO_DEV_DIAGNOSTICS`, `ParadisoDocumentHelp` (document-help.js), `ParadisoRoute` (visa-route-guide), `ParadisoShortStay`, `VisableReminderDialog`, `VisableCivicSearch`, `ParadisoUnifiedSearch`, `ParadisoIndexFallback`, `ParadisoReservationHelper`, `ParadisoZhT`, `EmploymentCodeAnalyzer`, `EmploymentChecklist` (module scripts, used lazily).

**Custom events (the contract to keep):**
- Emitted on `document`: `paradiso:data-ready` (24660), `paradiso:data-failed` (24684), `paradiso:results-rendered` (23462, 23533), `paradiso:landing-reset` (23366), `visable:landing-actions-ready` (24963).
- Emitted on `window`: `paradiso-language-applied` (24344). Listened to by about 12 `assets/js` files plus C33, C34, C35 and shim 4.

### (c) Main-block globals used by `tests/` (bare-name `page.evaluate` / `waitForFunction`)
| Global | Kind | Specs |
|---|---|---|
| `VISA_DATA` | lex | waymaker-quick-answer, search-smoke, landing-boot, procedure-first-search, search-result-unification, ui-consistency, complex-status-guide, overlay-anchoring, search-first-home, unified-search, restore-trust, application-form-wording, language-control, post-search-guidance |
| `dataReady` | lex | search-resilience, bilingual-doc-names, complex-status-guide, easy-mode |
| `renderResults` | fn | search-smoke, bilingual-doc-names, complex-status-guide, unified-search, easy-mode |
| `executeSearch` | fn | bilingual-doc-names, complex-status-guide, easy-mode |
| `applyLanguage` | fn | bilingual-doc-names, easy-mode |
| `I18N_MANIFEST` | lex | bilingual-doc-names, easy-mode |
| `DOCUMENT_TAB_CONFIG`, `renderDocumentTabPanel`, `renderDocTags`, `renderAnnotatedDocLabel`, `findOfficialTermIdForKoreanLabel` | lex / fn | bilingual-doc-names |
| `paradisoCanonicalAppFormText` | fn | application-form-wording |
| `ALIAS_MAP`, `PREDEF_KEYWORDS` | lex | search-smoke |
| `getLandingHintItems`, `getQuickFilterItems` | fn | search-smoke |
| `LANGUAGE_OPTIONS`, `isLanguageSelectable` | lex / fn | language-control (asserts 15 options) |
| `UI_TRANSLATIONS` | lex | search-first-home:149 (comment: "top-level const, not a window property") |
| `closeModal` | fn | search-first-home:243 |
| `startPreEntryTrack`, `startInKoreaTrack` | fn | landing-boot |
| `loadI18nTranslations` | fn | landing-utilities |
| `window.openGlobalSettings` | shim 4 | easy-mode |

`tests/golden/**` touches **no** inline globals. It only checks DOM, text, `document.documentElement.lang/dir` and `localStorage.getItem`. `golden/helpers/data.mjs` has its own `VISA_DATA` read from the JSON file.

There is also a source-text surface: 38 scripts parse `index.html` text (listed in `docs/rebuild/phase0-legacy-checks.md` §A). Key markers:
- `const DOC_DICT = {…\n};`, `const PROCEDURE_CONFIG = […]`, `const LANGUAGE_OPTIONS = […]`, `const ALIAS_MAP = {…};`, `BOOTSTRAP_KO_FALLBACK`.
- Slices `const LANGUAGE_STORAGE_KEY` … `function toggleTheme()` and `// --- Job Code Modal · HiKorea` … `\nfunction fallbackCopy(`.
- `extractFunction` of `renderResults`, `getProcedure`, `insertFeeNotice`, `buildSubcodeModalView`, `paradisoDeadlineAddDays`…`downloadDeadlineIcs`, `deriveIssuanceRouteChips`, `normalizeCodeLikeQuery`.
- Dispatcher keys such as `'toggle-search':`.

**Moving any of these breaks those scripts** unless they are rewritten first.

---

## 4. Data loading
| Line | Call | URL | Receives | Consumers | Timeout / fallback / errors |
|---|---|---|---|---|---|
| 16983 | `fetch(path,{cache:'default'})` in `loadJobcodeData` | `JOBCODE_JSON_PATHS` = `['./data/jobcode_master.json']` (16933) | `_jobcodeData` (memo via `_jobcodeLoadPromise`) | scoring/rendering in C09, `ensureEmploymentAnalyzer` | Tries each path; checks `json.data` is an array; throws `로드 실패:\n…` (Korean, not an i18n key). `data:`/`about:` protocols throw a Korean literal. |
| 17568 | `grab(p)` = `fetch(p,{cache:'default'}).then(ok?json:null).catch(null)` × 14 | `./data/employment/{synonyms.ko,en,zh; aliases.entertainment.ko,en; aliases.tattoo.ko,en; ambiguous_inputs; classification_sources; colloquial_field_terms_ko,en; disambiguation_rules; income_brackets; multilingual_pivot}.json` | `_empLex`, `_empSources`, `_empAnalyzer` | `searchJobcodeWithAI` | Each file is optional (null). Returns null if `window.EmploymentCodeAnalyzer` is missing. |
| 18074 | `await import('./scripts/employment_interpret_client.mjs')` | That module POSTs `${API_BASE}/api/employment/interpret` (5000 ms default timeout inside the module) | `facts` | `az.analyze` | Wrapped in try/catch: `analysis = null` |
| 18855 | `fetch(\`${API_BASE}/api/ask\`, POST)` | backend | `result` | `formatAiModalAnswer`, `renderGroundingSourcePanel` | `AbortController` plus `AI_REQUEST_TIMEOUT_MS` = 75000 (18853). 503 → `buildProviderErrorHtml`. Timeout → `tx('aiTimeout')`. Other errors → `tx('aiError')`. Empty answer → `tx('aiNoResult')`. |
| 18932 | `fetch('./data/document_help.json',{cache:'no-store'})` | static | `documentHelpData`, `documentHelpMatcher` (needs `window.ParadisoDocumentHelp`) | `findDocumentHelp`, `openDocumentHelp` | Silent; re-renders results if already searched |
| 18993 | `fetch('./data/doc_guide.json',{cache:'no-store'})` | static | `docGuideData` | `buildDocGuideDrawer`, `renderDocTags` | Silent; re-renders results if already searched |
| 23673–23705 | Local `fetchJson` (`no-store`, throws `'i18n load failed: '+url`) in `loadI18nTranslations` | `./data/i18n/manifest.json`, then `./data/i18n/<file>` per supported locale, then `./data/i18n/official-terms.json`, then `./data/i18n/visa-names.json` | `I18N_MANIFEST`, `UI_TRANSLATIONS[locale]`, `OFFICIAL_TERMS` (+ `indexOfficialTerms()`), `VISA_NAME_I18N` | `tx` and everything built on it | Manifest failure → built-in default `{ko,en,zh-CN}`. Missing ko → `BOOTSTRAP_KO_FALLBACK`. Glossary or names missing → `{}`. Only `console.warn`. |
| 24615 | `fetchOptionalJson('./data/integrated_form_metadata.json')` | static | `INTEGRATED_FORM_META` | `renderDocComposerTags` | null |
| 24628–24637 | `fetchOptionalJson(path)` | — | — | — | `no-store`; on failure warns `Optional Visable data not loaded: ${path}` and returns null |
| 24641–24643 | `fetchOptionalJson` × 3 in `loadVisaIssuanceData` | `./data/visa_issuance_records.json`, `./data/procedure_evidence_bindings.json`, `./data/official_web_overlays.json` | `VISA_ISSUANCE_RECORDS` / `_BY_CODE`, `PROCEDURE_EVIDENCE_BINDINGS` / `_BY_KEY`, `OFFICIAL_WEB_OVERLAYS` / `_POLICY` | C23, C16 | Each defaults to `[]` / `{}` |
| 24670 | `fetch(\`${API_BASE}/api/visas\`,{no-store, signal})` | backend | `parse(apiJson)` → `VISA_DATA` | everything | Skipped when `API_BASE` is empty. `VISA_DATA_API_TIMEOUT_MS` = 4000 also covers a stalled body. On any error, falls back to the next row. |
| 24677 | `fetch('./visa_data.json',{no-store})` | static fallback | `VISA_DATA` | — | `parse()` accepts an array, `.data` or `.visas`, then runs `injectLocalData`. Success shows `tx('dataReady',{count,source})` with source `tx('sourceApi')` / `tx('sourceStatic')`. Failure: `dataReady=false`, `tx('visaDataLoadError')`, search disabled, `paradiso:data-failed`. |
| 25784 | `fetch('data/agent_registry_2026-04-30.json',{cache:'no-cache'})` | static, **parse time** | `dataset.meta`, `.regions`, `.agencies` (closure) | `populateRegions`, `applyFilter` | `showError()` plus a retry button |
| 25987 | `fetch('data/designated_medical_institutions_2026_04_30.json',{cache:'no-cache'})` | static, **parse time** | `dataset.meta`, `.institutions` | `applyFilter` | `showError()` plus a retry button |
| 26350 (shim 1) | `fetch("visa_data.json",{no-store})` | **second copy, fired on every DOMContentLoaded** | `window.__paradisoDetailAliasData` | `getResolverRecords` (only if `VISA_DATA` is empty) | `console.warn`, then `[]` |

Cache modes differ and must be preserved byte-for-byte: `default` (job codes, employment), `no-store` (most), `no-cache` (the two finders). The existing `src/data/fetch-json.ts` defaults to `no-store`, so the jobcode and finder call sites have to pass `cache` explicitly. `DATA_PATHS` in `src/data/paths.ts` already matches these strings, including the relative `data/…` form without `./` for the finders.

---

## 5. State and storage (main block plus shims)
| Line | Key | R/W | Functions |
|---|---|---|---|
| 16285 | `paradiso_city` | W (JSON) | `applyCity` |
| 16338 | `paradiso_city` | R (parse time) | `initCity` |
| 18590, 18821 | `paradisoDevDiagnostics` (`'1'`) | R | `isAiDevDiagnosticsEnabled`; `renderGroundingSourcePanel` area (18816–18821). Also used by ai.html. |
| 21135 / 21138 / 21141 | `paradiso:scenario-checklist:` + `<scope>` + item hash (built in 21122–21133) | R / W / remove | `scenarioChecklistStoreGet/Set/Remove` → persist (21196), hydrate (21218), `renderScenarioChecklist` |
| 21341–21342 | Iterates `localStorage.key(i)` for the prefix | R + remove | `resetScenarioChecklist` |
| 22820 | `paradiso:easyMode` (`'1'`/`'0'`) | R (parse time) | `globalEasyMode`. Shared with civic-search.js and ai.html. |
| 23070 | `paradiso:easyMode` | W | `toggleGlobalEasyMode` |
| 23870 | `paradiso:i18n-debug` | R (parse time) | `I18N_DEV_WARNINGS` |
| 23975 | `paradiso:language` | R | `getStoredLanguage` → `getInitialLanguage` |
| 24100 | `paradiso:language` | W | `applyLanguage`. Shared with 6 `assets/js` files, ai.html and new-home.html. |
| 24366 | `paradiso:brightness` | W | `toggleTheme`. Also read by the head inline script at 14479 and by 8 other pages/scripts. |
| 24428 | `paradiso:editorial-theme` | R | `getStoredEditorialTheme` |
| 24450 | `paradiso:editorial-theme` | W | `applyEditorialTheme` (when `persist`). Also used by visable-theme.js and 4 pages. |
| 26063 / 26069 | `paradisoReminders` (JSON array) | R / W | C35 `load` / `save` |
| 26257 / 26275 | `paradisoReminderBannerDismiss` (ISO date) | R / W | C35 `showBanner` / banner close |
| 26764 (shim 4) | `paradiso:brightness` | R | `activeBrightnessChoice` |
| 26809 (shim 4) | `paradiso:brightness` | W (`light`/`dark`/`system`) | `window.setGlobalBrightness` |

- No `sessionStorage` is used anywhere in these blocks.
- All access is wrapped in try/catch, except: 23870 (inside its own IIFE try), 18590/18821 (`typeof` guards), and 26063 (inside a `try`).
- In-memory state that must stay single-owner: `VISA_DATA` and companions, `dataReady`, `currentLanguage`, `selectedLocale`, `I18N_MANIFEST`, `OFFICIAL_TERMS`, `VISA_NAME_I18N`, `currentSearchMode`, `SELECTED_CITY`, `globalEasyMode`, `EASY_MODE_CARD_STATE`, the `_jc*` and `_emp*` variables, the `currentAi*` variables, `selectedScenarioHandoff`, `scenarioPicker*`, `routePicker*`, `issuanceGuideActiveGuide`, `documentHelp*`, `docGuideData`, `INTEGRATED_FORM_META`, `lastFocusedElement` / `activeModal`, `_currentInKoreaAction`, `dt`, `_revealObs` / `_staggerObs`.

---

## 6. Rendering
- **Counts in the main block (16104–16318):** 105 `innerHTML =`, 3 `insertAdjacentHTML` (18144, 25117, 25726), 0 `outerHTML`.
- **Counts in the shims:** 2 `innerHTML =` (26705 is dead code; 26770 is a clear).
- **Helper usage:** 387 calls to `escapeHtml(`, 31 calls to `hl(`.

| Helper | Line | Notes |
|---|---|---|
| `escapeHtml` | 16108 | DOM-based. **Does not escape `"` or `'`.** There are 97 attribute-context uses (`="${escapeHtml(…)}"`). |
| `hl` | 16110 | Escapes, then highlights |
| `escapeText` | 25624 (agent finder), 25829 (med finder) | Local; escapes `& < > " '`. This is the correct attribute-safe version. |
| `esc` | 21730 | ICS text escaper only, not HTML |
| `formatAiModalAnswer` | 18598 | Escapes first, then adds `<strong>` / `<br>` |
| `tx` | 23875 | **Does not escape interpolated vars.** Callers pre-escape (for example 18574 `tx('jurResultMsg',{office: escapeHtml(...)})`, 23459 `escapeHtml(query)`). |

Main HTML-string builders over dynamic data (they mostly use `escapeHtml` / `hl`):
- C08: `buildSubcodeModalView`, `openFaqModal` (escapes q and a), `openDocModal`.
- C09: `renderJobcodeCard`, `renderJobcodeList`, `renderEmployment*`.
- C11: `renderGroundingSourcePanel`, `buildProviderErrorHtml`.
- C12: `renderDocTags`, `buildDocGuideDrawer`, `renderDocumentHelpButton`.
- C13: `renderProcedureFeeBox`.
- C16 / C19: `renderProcedure*`.
- C18: `renderScenarioChecklist`, `buildScenarioChecklistPrintHtml`.
- C20: `renderF4RouteChooser`, `applyRouteSelection`.
- C21: `deadlineRowHtml`.
- C22: `renderSubcodes` and the other result-card sections.
- C23: `renderIssuance*` (22264–22297 verified escaped).
- C24: `renderDocumentTabPanel`.
- C25: `renderEasyModePanel`.
- C26: `renderResults` (23487–23523 template: codes and names via `hl`), `renderCompactResults`, `showSuggestions` (external `ParadisoUnifiedSearch.buildSuggestionRowHtml` with `hl` label).
- C29: `updateCategoryCounts`, `renderDocComposerTags`.
- C32: `startPreEntryTrack`, `startInKoreaTrack`, `showVisaRecommendations`, `selectInKoreaAction`, `filterInKoreaVisaList`.
- C33 / C34: `buildCard` (uses `escapeText`).

### Candidates for the Phase 3 escaping pass (flagged, not fixed)
1. **Inline `onclick` with a JS-string context:** 25471–25472 (`openDocModal('${escapeHtml(v.code)}', 'new')`, `openAiModal(…)`) and 25577 (`showVisaDocForAction('${escapeHtml(v.code)}')`). `escapeHtml` leaves `'` untouched. Codes come from data (low risk), but the pattern is unsafe. Replace with `data-action` dispatch.
2. **97 attribute contexts use `escapeHtml` without quote escaping**, for example 24588 `data-query`/`aria-label`, 23510 `data-guide-slot`, 22280 `href="${escapeHtml(record.sourceUrl)}"` (also no URL-scheme check). Replace with an attribute-safe escaper such as the existing `escapeText` semantics.
3. **16317 `renderCityList`:** `${c.flag}` and `${c.n}` are inserted unescaped. The data is static `CITIES` plus Intl zone names, not user input, but they are dynamic strings.
4. **`tx()` output inserted as HTML without escaping:** 16609, 17386, 17396, 18574 (vars pre-escaped), plus `setHtml`/`setIndexedHtml` (23896/23912) and `localizeStaticDom` `data-i18n-html` (23943). These are trusted i18n pack data (`data/i18n/*.json`); document it as a trust boundary.
5. **Not verified, needs review:** the body of `buildSubcodeModalView` beyond the title and parent HTML (16760–16822), `buildScenarioChecklistPrintHtml` (21265), the `startPreEntryTrack`/`startInKoreaTrack`/`showVisaRecommendations`/`selectInKoreaAction` templates (25337–25536), `renderDomainBadges`/`renderReviewBadge`, `renderJobcodeGuidance` hint (17467), and the inner `renderDocTags` paths.
6. **Shim 3 at 26705** puts `fee.title`/`fee.body` into `innerHTML`. It is static and dead code (early return at 26693).

---

## 7. Hard-coded content that must move byte-identical (HEAD lines)
| Item | Lines | Size | Notes |
|---|---|---|---|
| `COMMON_NEW` / `COMMON_EXT` | 16130 / 16131 | 1 + 1 | Doc-key lists |
| **`DOC_DICT`** | 16132–16166 | 35 | Labels, including fee strings (16135–16136: 35,000원 / 39,000원). Regex-parsed by `check_doc_master_integrity.py` and `check_official_terms.mjs`. |
| `CITIES` | 16171–16239 | 69 | |
| `CC` / `CL` | 16435 / 16436 | 1 + 1 | 199 and 455 characters |
| `JOBCODE_TARGET_VISAS`, `JOBCODE_STOP_TERMS`, `JC_AMBIGUOUS_TERMS`, `JC_TYPE_LABEL*` | 16917–16939 | about 23 | |
| `JOBCODE_QUERY_EXPANSIONS` | 16940–16974 | 35 | |
| `JC_GENERIC_NAME_WORDS` | 17067 | 1 | |
| `JC_MODE_LABEL` / `_EN` / `_ZH` | 17613–17633 | 21 | |
| `JC_SPECIAL_ICON` / `JC_SPECIAL_I18N` | 17788–17800 | 13 | |
| `JC_WEAK_EXAMPLES` | 17996 | 1 | |
| **`JUR_DB`** | 18159–18422 | 264 | |
| **`OFFICE_INFO`** | 18424–18555 | 132 | |
| `renderModalFeeBox` fee strings | 16865–16866 | in function | 80,000원 / 35,000원 |
| **`PROCEDURE_CONFIG`** | 19170–19193 | 24 | Regex-parsed by `audit_procedure_journeys.js` |
| `COMMON_MANUAL_WARNINGS` | 19195–19202 | 8 | |
| `STAY_FEE_SOURCE_NOTE` | 19204 | 1 | |
| `CARD_DELIVERY_SURCHARGE` | 19209 | 1 | = 4000 |
| **`DEFAULT_PROCEDURE_FEES`** | 19210–19247 | 38 | Fee amounts and notes |
| `getProcedureFeeInfo` overrides | 19254–19305 | in function | F-5 200,000원, F-6 40,000/30,000원, 영주증 35,000원 … |
| `PROCEDURE_LABEL_INDEX` | 19485–19497 | 13 | |
| `SOURCE_CONFIRMED_PROCEDURE_KEY_MAP` | 19579–19599 | 21 | |
| `F4_OVERSEAS_KOREANS_FORM_PROCEDURES` | 19613–19615 | 3 | |
| `DOC_GROUP_ALIASES` | 19835–19840 | 6 | |
| **`DOC_PLACEHOLDER_TOKENS`** | 19920–19923 | 4 | |
| `PARADISO_DOC_*` regexes and thresholds | 19935–19944, 20066–20067, 20348 | about 14 | |
| `PARADISO_DOC_FAMILY_RULES` | 20102–20120 | 19 | |
| `DOCUMENT_REQUIREMENT_DISPLAY_FAMILY_RULES` | 20168–20177 | 10 | |
| `MANUAL_*` / `PARADISO_*_RE` note filters | 20529–20595 | about 25 | |
| `PROCEDURE_EVIDENCE_TYPE_BY_KEY` | 20719–20731 | 13 | |
| `SOURCE_EVIDENCE_LABELS` | 20733–20755 | 23 | |
| `SCENARIO_CHECKLIST_GROUPS` | 21108–21111 | 4 | |
| `PROCEDURE_FALLBACK_SUMMARY_KEYS` | 21420–21424 | 5 | |
| **`ROUTE_WIZARD_CONFIG`** | 21440–21534 | 95 | |
| `GENERIC_VISA_ISSUANCE_EXCLUDED_CODES`, `VISA_ISSUANCE_NOT_APPLICABLE_*` | 22299, 22315–22316 | 3 | Regex-checked by scripts |
| `ISSUANCE_ROUTE_CHIP_INDEX` | 22333–22340 | 8 | |
| `DOCUMENT_TAB_CONFIG` | 22569–22573 | 5 | Used by e2e |
| `DOCUMENT_DATA_MISSING_NOTICE` / `DOCUMENT_REGISTRATION_MISSING_NOTICE` | 22580 / 22581 | 1 + 1 | Korean notices, 292 and 300 characters |
| `EASY_MODE_*` | 22814–22861 | about 8 | |
| **`ALIAS_MAP`** | 23146–23152 | 7 | Regex-parsed by `check_exact_code_search_coverage.py` |
| `PREDEF_KEYWORDS` | 23185–23190 | 6 | |
| **`LANGUAGE_OPTIONS`** | 23574–23594 | 21 | Sliced by `check_search_multilingual.mjs` and `check_official_terms.mjs` |
| `LANGUAGE_SUPPORT` | 23607 | 1 | |
| **`BOOTSTRAP_KO_FALLBACK`** | 23625–23657 | 33 | Marker required by `check_index_hardcoded_text` and `smoke_static_i18n` |
| `I18N_MANIFEST` default | 23658–23664 | 7 | |
| `REGION_I18N` | 24377–24396 | 20 | |
| `EDITORIAL_THEMES` | 24422 | 1 | |
| `injectLocalData` FAQ-0 record | 24511–24516 | 6 | |
| Archive-diary stamp SVG and `KS_COUNTRIES` | 25081–25111 | about 30 | |
| `PURPOSE_TO_CAT`, `ACTION_CAT_LABELS[_EN/_ZH]`, `DOC_MODAL_ACTION_MAP` | 25411–25435 | 25 | |
| Reminder `TYPE_LABELS` | 26020–26024 (approx.) | 5 | |
| **`FEE_BY_LABEL`** (shim 3) | 26580–26585 | 6 | Live via `updateBareFeeCards` |
| **`TERM_REPLACEMENTS`** (shim 3) | 26587–26596 | 10 | |

Also embedded: many Korean, English and Chinese ternary literals inside renderers (for example 16880–16896 and 25337–25576). They must move byte-for-byte with their functions.

---

## 8. Recommended extraction order (modules under `src/`, bridged on `window.Visable.*`)

Rules that apply to every step:
- Keep every inline `let`/`const` owner of shared mutable state (list in §1, "Scoping fact").
- Keep every `function` name that §3 lists as an inline shim delegating to the bridge.
- Keep all source markers the §3 legacy scripts parse until those scripts are rewritten.
- Leave parse-time code (§2 list) inline, or defer it deliberately with a visual-golden check.

| # | Module | Absorbs (HEAD lines) | Must stay global during transition | Golden coverage |
|---|---|---|---|---|
| 1 | `src/data/fetch-json.ts` (exists) + `src/data/visa-data.js` | 24628–24687 (`fetchOptionalJson`, `loadVisaIssuanceData`, `loadVisaData` load and parse), 24619 (`buildProcedureEvidenceIndex`), 18930 / 18991 / 24614 load bodies, 16975 (`loadJobcodeData` transport), 23672 transport | Inline `let VISA_DATA`, `dataReady` and siblings stay. The module returns data and the inline code assigns it. Events `paradiso:data-ready` / `data-failed` unchanged. | fail-closed (visa_data abort), search (`?q=`, D-2), tools (jobcode only path, status 200) |
| 2 | `src/data/static-tables.js`, or JSON under `data/ui/` | Pure data with no consumers outside index.html: `CITIES`, `JUR_DB`, `OFFICE_INFO`, `REGION_I18N`, `JOBCODE_QUERY_EXPANSIONS`, `JC_*` labels, `ROUTE_WIZARD_CONFIG`, `PURPOSE_TO_CAT`/`ACTION_CAT_*`. **Defer** `DOC_DICT`, `PROCEDURE_CONFIG`, `ALIAS_MAP`, `LANGUAGE_OPTIONS`, `BOOTSTRAP_KO_FALLBACK` until their regex checks are rewritten. | Same `const` names inline (`const JUR_DB = Visable.tables.JUR_DB` does not work at parse time, so these tables must be consumed only after the module runs; all their readers are event-time) | tools (partial); **gap: jurisdiction, city** |
| 3 | `src/state/storage.ts` | Wrappers for every key in §5, keeping exact key names: 16285/16338, 21134–21143, 21341, 22820/23070, 23975/24100, 24366, 24428/24450, 26063–26069, 26257/26275 | Parse-time readers (16338, 22820, 23870, the C35 reminders) **stay inline** or read raw `localStorage` | home (language persists), easy-mode / ui-consistency e2e |
| 4 | `src/render/escape.ts` | 16108–16114 (`escapeHtml`, `escapeRegExp`, `hl`), 25624/25829 `escapeText`, 21730 ICS `esc`. Add `escapeAttr` for the Phase 3 pass. | `escapeHtml`, `hl` as window functions (internal use; bilingual-doc-names renders through them) | all (page-error-free checks) |
| 5 | `src/i18n/runtime.js` | 23573–24086 minus the mutable owners, plus 24087–24347 `applyLanguage` body | Inline `let currentLanguage`, `selectedLocale`, `I18N_MANIFEST`, `const UI_TRANSLATIONS`, `LANGUAGE_OPTIONS`. Window functions: `tx`, `txAt`, `txArray`, `applyLanguage`, `isLanguageSelectable`, `loadI18nTranslations`, `localizeStaticDom`, `updateThemeLabel`. `check_index_hardcoded_text` slice markers. | home (15 locales, lang/dir, dialog persists), search (ko/en) |
| 6 | `src/ui/modal.js` + `src/ui/theme.js` | 16439–16498 (modal core); 24351–24375, 24421–24458 (theme, editorial theme); shim 4 (26753–26849) | `openModal`, `closeModal`, `toggleTheme`, `updateThemeColorMeta`, `window.openGlobalSettings/closeGlobalSettings/setGlobalBrightness` | home, visual; **gap: settings brightness** |
| 7 | `src/features/city-clock.js` | 16167–16347 | `initCity` stays inline (parse time) or moves to module start with a visual check; `toggleCityMenu`, `applyCity`, `renderCityList` | visual (masthead); **gap** |
| 8 | `src/features/finders.js` (agent + medical) | 25603–26005, 24377–24420 (`localizeRegion`) | `window.updateAgentFinderLanguage`, `window.updateMedFinderLanguage`. Note: moving them makes the fetches deferred. | home (entries link); **gap: no golden opens a finder** |
| 9 | `src/features/reminders.js` | 26007–26317 (parse-time IIFE; the dialog is in `reminder-dialog.js`) | none (closure) | **gap** (ui-consistency e2e touches `VisableReminderDialog`) |
| 10 | `src/features/jobcode/` (`data.js`, `score.js`, `render.js`, `employment.js`) | 16903–18157 | `openJobCodeModal`, `renderJobcodeResults`, `searchJobcodeWithAI`, `selectJobcode`, `copyJobcodeMemo`, `setJobcodeFilter/Level`, `searchJobcodeChip`, `jcGoBackToAsk`, `renderEmploymentChecklist`, `_jc*` (read by the DOMContentLoaded wiring 24728–24740). `check_employment_reporting_helper` and `check_employment_checklist` slice markers. | **tools** (direct) |
| 11 | `src/features/jurisdiction.js` + `src/features/deadline.js` | 18159–18580; 21701–21840 | `openJurisdictionModal`, `updateSigungu`, `showJurisdiction`; `computeDeadlines`, `downloadDeadlineIcs` (`check_deadline_helpers.js` range markers) | **gap** for both |
| 12 | `src/docs/normalize.js` (pure) | 19347–19578 (code and name helpers), 19579–20528 (doc-requirement normalisation), 20529–20718 (manual text) | `paradisoCanonicalAppFormText` (shim 3, e2e), `getProcedure`, `paradisoStripInternalReviewArtifacts`, `getVisaNameEn`, `normalizeVisaCode`, `normalizeCodeLikeQuery`, `getExactQueryMatchRank`, `toDocArray`, `dedupeDocs`, `isDocPlaceholder` (`check_placeholder_suppression` / `check_static_visa_result_cards` `extractFunction`) | procedure (D-2 docs, ARC reissue), search (E-7-1 not flattened, Z-9 fail-closed) |
| 13 | `src/render/procedure-card/` (`fees.js`, `procedures.js`, `scenario.js`, `checklist.js`, `f4-route.js`, `issuance.js`, `doc-tabs.js`, `easy-mode.js`) | 19170–19346, 20719–21439, 21440–21700, 21841–22813, 22814–23093 | `renderDocTags`, `renderDocumentTabPanel`, `DOCUMENT_TAB_CONFIG` (lex), `renderAnnotatedDocLabel`, `findOfficialTermIdForKoreanLabel`, `isVisaIssuanceNotApplicable`, `openHikoreaGuide`, `PROCEDURE_CONFIG`, plus every dispatcher target in 24787–24929 | procedure; **gap: legacy result cards** (see below) |
| 14 | `src/features/modals-ai.js` | 16499–16902 (drawer, AI, doc, subcode, FAQ modals), 18583–18925 (AI submit), 18926–19169 (document help, guide) | `openVisaDrawer`, `closeVisaDrawer`, `openAiModal`, `openDocModal`, `openSubcodeModal`, `openFaqModal`, `window.verifyFaqWithAi`, `buildWaymakerHandoffUrl`, `showToast` | fail-closed (AI layer optional) |
| 15 | `src/search/` (`score.js`, `results.js`, `landing.js`, `journey.js`) and finally `src/boot.js` | 23094–23572, 24460–24592, 25140–25603; boot and delegation 24689–25138 last | `executeSearch`, `renderResults`, `resetToLanding`, `startPreEntryTrack`, `startInKoreaTrack`, `getLandingHintItems`, `getQuickFilterItems`, `ALIAS_MAP` / `PREDEF_KEYWORDS` (lex), `qEl`; all 5 custom events; dispatcher key literals (`check_live_feature_surface`) | search, home, fail-closed, visual |

The four id'd shims are last. They need the absorbed globals named above. Retire or move them only after modules 12–15, because they patch DOM produced by those renderers.

### Golden coverage gaps to close before the matching step
- The golden `search` and `procedure` "안내 · …" guidance comes from `assets/js/status-guidance.js` (`answerTitle`), **not** from the main block's `renderResults` output. Golden therefore does **not** directly assert the legacy result cards. That covers C16–C26: procedure tabs, document tabs, scenario picker and checklist, F-4 wizard, issuance guide, easy mode and deadlines.
- Today those are only covered by e2e: easy-mode, bilingual-doc-names, ui-consistency, search-smoke, complex-status-guide, restore-trust.
- Add golden cases, or promote those e2e specs, before modules 11 and 13.
- Also uncovered by golden: city clock, jurisdiction, agent and medical finders, reminders, global-settings brightness.
