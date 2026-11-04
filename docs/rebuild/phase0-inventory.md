# Phase 0 — Feature inventory

Date: 2026-11-03. Produced from a read-only sweep of index.html, the assets/js
modules it loads, and the other HTML pages (Part 2). Tags: **Critical** = wrong or
missing guidance for a foreign national if broken (search, status detail, document
requirements, fees, Waymaker answers, disclaimers, fail-closed and uncertainty
notices); **Important**; **Peripheral**; **UNVERIFIED** with a reason.

Measured facts that correct the brief:
- index.html has **11 inline `<script>` elements** (7 without an id, 4 with one).
- Only `data/jobcode_master.json` exists; the other three job-code fallback paths are dead.
- Fee amounts are **hard-coded in UI code** (shim S10 `FEE_BY_LABEL`, index.html:26577-26582,
  and again at 16135-16136, 16858-16866, 19203-19240) in addition to the data-driven fee
  registry in `data/status-guidance-202609.json`. Any extraction must carry these strings over
  byte-for-byte (hard stop 4: no fee change beyond a byte-identical move).

---

## Part 1 — index.html

### Script blocks in index.html

| # | Lines | Logic or config | Content |
|---|---|---|---|
| S1 | 15-26 | config/boot | Reads `paradiso:editorial-theme` and sets `data-theme` before first paint |
| S2 | 11754-11756 | config | `window.PARADISO_BACKEND_URL = ... \|\| ""` |
| S3 | 14475-14484 | boot logic | 14479 brightness pre-paint; 14483 `?q=` switches body to the `searched` scene |
| S4 | 14489-14509 | logic | Skip-link focus fix, `history.replaceState('#'+id)` |
| S5 | 14618 | logic (trivial) | Masthead date text |
| S6 | 14842 | logic | Prefills `#q` from `?q=` (max 300 chars) |
| S7 | 16104-26316 | **main app logic, with config/data embedded** | Embedded data: DOC_DICT near 16130 (fee strings at 16135-16136); JOBCODE paths 16931; `JUR_DB` 18157-18421; `OFFICE_INFO` 18422-18553 (Naver/Kakao URLs); fee notes 19203-19240; `I18N_MANIFEST` default about 23627; `BOOTSTRAP_KO_FALLBACK`. Sub-IIFEs: initCity 16335, scroll/anagram 25198/25222, initAgentFinder 25602, initMedFinder 25806, reminders 26012-26316 |
| S8 | 26318-26486 `DETAIL_CODE_RESOLVER_SHIM_2026_05` | logic | Resolves a subcode to its parent; background fetch of visa_data.json as fallback |
| S9 | 26489-26571 `DOC_SECTION_UNIFICATION_SHIM_2026_05` | logic | Unifies document-section DOM ("필수서류" titles) |
| S10 | 26574-26749 `DOC_TERM_FEE_UI_SHIM_2026_05` | **config + logic** | Hard-coded `FEE_BY_LABEL` (26577-26582) and `TERM_REPLACEMENTS` |
| S11 | 26751-26847 `visable-global-settings-20260713` | logic | Global settings overlay: language list, brightness, Escape to close |

Hard-coded fee strings seen in S10 (must be preserved verbatim if moved): "외국인등록증 발급 수수료 35,000원 (등기우편 수령 시 39,000원)", "체류기간 연장허가 정부수입인지 60,000원", "체류자격 변경허가 정부수입인지 100,000원…", "국내 체류자격 부여는 정부수입인지 80,000원".

### Feature table (46 features)

Abbreviations: **MAIN** = S7. **Cv** = civic-search.js, **SG** = status-guidance.js, **QA** = waymaker-quick-answer.js, **US** = unified-search.js. **BO** = backend origin: `VisableBackend.origin()` = `PARADISO_BACKEND_URL`, else empty on localhost/127.0.0.1/file:, else `https://web-production-14f9a.up.railway.app` (backend-origin.js:35). Tags: **C** Critical, **I** Important, **P** Peripheral.

| # | Feature | Entry point | Data loaded | Storage | Owner | External | Safety / fail-closed | Tag |
|---|---|---|---|---|---|---|---|---|
| 1 | Home search box | `#civicQuery` "검색"/Search; example chips "이렇게 검색해 보세요"; `?q=`; popstate | via #2, #3 | sessionStorage `visable.example-ids` | Cv (render 430-460, searchFromHome ~777) | — | `bootFailed` "화면을 준비하지 못했어요. 새로고침하면 대부분 해결돼요." plus `civic-boot-failed` class if the script fails (index 26897 onerror); `noscript` text; `unavailable` "안내 데이터를 불러오지 못했습니다. 페이지를 새로고침해 주세요." | C |
| 2 | Search suggestions | Typing in #civicQuery; ArrowUp/Down/Enter/Esc/Tab | `data/search-suggest-index.json` (Cv:529) | — | search-suggest.js + Cv 535, 649-718 | — | Rows come only from the index; tool links allow-listed by `SAFE_TOOL_HREF` (Cv:551) | I |
| 3 | Complex-question handoff to Waymaker | Submitting a question-shaped query (`VisableSearchRouter.assessComplexity`) | — | sessionStorage write `visable.search-handoff` | Cv:777-789 | navigates to `ai.html?handoff=search&lang=` | If storage is blocked, falls back to normal search | I |
| 4 | Status-of-stay results list / data boot | `#q` search, `executeSearch` 23262, `renderResults` 23418, `?q=` (initUI 24463) | `${API_BASE}/api/visas` (4 s timeout), else `./visa_data.json` | — | MAIN 24652-24684 | BO `/api/visas` | `dataReady` "데이터 로드 완료 ({count}개) - {source}" ("API 연동" / "정적 백업"). If both sources fail, search is disabled and `visaDataLoadError` "비자 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요." is shown (fail-closed) | C |
| 5 | Post-search guidance (answer, documents, fees, local office, evidence) | Automatic after search; in-page clarify chips; "실제 방문 내용이 달랐나요?" | `data/status-guidance-202609.json`; optional `data/local-practice-202609.json` | sessionStorage `visable.sg.<query>` (read and write) | SG (load 1600-1606, render, failure 1742) | — | `failed` "안내를 불러오지 못했어요. 아래 원문 검색은 그대로 사용할 수 있어요." with retry. Fee review labels "확인 필요", "근거 불일치 · 확인 필요", "조건부 · 확인 필요". `evidenceReview` "참고용 안내예요 · 신청 전 공식 원문을 확인하세요." `officer` "심사 과정에서 추가 서류가 요청되거나 일부 서류가 생략될 수 있습니다." `formReturnUnknown`. Local-practice layers labelled ("확인되지 …") | C |
| 6 | Waymaker Quick Answer | Question-shaped query inside #5; "이어서 질문하기" link | Guidance bundle (no own fetch) | sessionStorage write/read `visable.waymaker.handoff` | QA | POST **relative** `/api/waymaker/quick-answer` (QA:357; not BO), 9 s timeout | AI may only rephrase; checked by `validateEnhancement`. 404/405/501 or NOT_CONFIGURED stay silent. `aiFailed` "AI 요약을 만들지 못했지만, 확인된 안내는 그대로 볼 수 있어요." `review` "2026년 10월판 매뉴얼을 기준으로 정리했지만, 원문과 한 줄씩 맞춰 보는 검토는 아직 끝나지 않았어요." `fallbackLead`, `feeNotListed` "수수료 항목 없음(확인 필요)" | C |
| 7 | Unified search strip + AI overview | Reacts to `paradiso:results-rendered`; "open-waymaker" button | — | — | US | BO-derived `apiBase()` (US:863; default `VisableBackend.productionOrigin`): `/api/search/unified`, `/ai-overview`, `/ai-overview/stream` | `searchLayerFailed` "통합 검색을 불러오지 못했습니다. 아래 기본 검색 결과는 그대로 사용할 수 있어요." `aiOverviewUnavailable` "AI 요약을 사용할 수 없습니다. 아래 검색 결과와 공식 출처를 확인하세요." `citationUnverifiedHelp`, `aiRefLabel` "참고용 요약", `officialConfirmHelp`. Official links allow-listed; all strings escaped | C |
| 8 | Related source passages ("관련 원문") | Disclosure inside the guidance; "공식 원문 찾기" | `data/manual-corpus/catalog.json`, then each `source.sections` (= `data/manual-corpus/visa_manual_2026_10_19_pdf.json`, `.../stay_manual_2026_11_02_pdf.json`) | — | Cv 803-812 + manual-corpus-search.js | — | `caveat` "표·이미지의 내용과 적용 조건은 원문 페이지에서 확인하세요. 발췌문은 개별 요건을 확정하는 안내가 아닙니다." `error` "원문을 불러오지 못했습니다. 다시 시도하거나 원문 PDF를 열어 확인하세요." | C |
| 9 | Manual reader deep link | Links to `manual.html#c-<chapter>.<v\|s>[.<section>]` | — | — | manual-reader-route.js | — | Visa and stay manuals never mixed; subcodes link to the parent chapter | I |
| 10 | Status detail drawer with procedure tabs | `show-detail`, `select-procedure`, `close-visa-drawer` | from #4 plus #15 data | — | MAIN openVisaDrawer 16499, renderProcedures 21399, renderProcedurePanel 21353 | — | `drawerDisclaimer` "검색 결과는 참고용입니다…", `cautionText`, `docGroupEmpty`/`docReviewFallback`, review badges (`reviewNeeded` "2026.6 매뉴얼 확인 필요", `sourceChipAuto` "자동추출 검토 필요"), `sourcePendingReviewNote`, `sourceProvisionalNote`, `renderSourceLimitationExplanation` 20829 | C |
| 11 | Subcode detail view | `open-subcode-detail` (Enter/Space), `toggle-subcode-group` | visa_data (fallback fetch `visa_data.json` in S8) | — | MAIN openSubcodeModal 16823; S8 | — | `subcodeModalSourceGap` "이 세부자격에 직접 연결된 공식 근거가 제한적입니다…"; parent-scope notice 22080 | C |
| 12 | Required documents tabs / modal | `open-doc-modal`, `select-docs-tab` | — | — | MAIN openDocModal 16683, renderDocumentTabs 22715, renderDocGroup 20522; S9 | — | Unresolved `doc_` ids flagged (19080); `docNameTranslationUnverifiedHint` | C |
| 13 | Document help / glossary | `open-document-help`, `toggle-doc-guide` | `./data/document_help.json`, `./data/doc_guide.json` | — | MAIN 18928-19060; document-help.js | — | UNVERIFIED: failure text not checked | I |
| 14 | Fee boxes | Inside procedure panel / doc modal | inline constants | — | MAIN renderProcedureFeeBox 19304, renderModalFeeBox 16847; S10 | — | `feeAmountCheckNeeded` "금액 확인 필요"; S10 fees are **hard-coded** | C |
| 15 | Visa issuance section / issuance guide | `open-issuance-guide`, `choose-issuance-mode`, `clear-issuance-guide` | `./data/visa_issuance_records.json`, `./data/procedure_evidence_bindings.json`, `./data/official_web_overlays.json` (each optional, null on failure) | — | MAIN 22430-22560, loadVisaIssuanceData 24637 | — | Missing data leaves empty arrays (section silently absent); `console.warn` "Optional Visable data not loaded" | C |
| 16 | Scenario picker / procedure variants | `open-scenario-picker`, `choose-scenario-variant`, `clear-procedure-variant` (Esc) | — | — | MAIN 20891-21057 | — | `scenarioSelectedReferenceNote` "선택한 시나리오는 참고용입니다…", `scenarioToastWarning` | C |
| 17 | Scenario checklist (copy / print / reset) | `copy-`, `print-`, `reset-scenario-checklist` | — | localStorage `paradiso:scenario-checklist:<code>:<proc>:<variant>:<group>:<hash>` (get/set/remove) | MAIN 21099-21350 | — | `scenarioChecklistSafetyNote` "이 체크리스트는 개인 준비용 도구이며, 항목을 체크해도 접수나 허가가 보장되지 않습니다."; never sent to the backend | I |
| 18 | Route picker (G-1/F-4 routes) | `open-route-picker`, `choose-route`, `show-all-f4-routes` | — | — | MAIN 21581-21700 | — | `f4RouteSourceNote`, `g1Route1Desc`/`g1Route2Desc` (no guarantee) | C |
| 19 | Guided route / deep link | `?code=&subcode=&procedure=` | uses visa_data | — | visa-route-guide.js (parse 416, push 984-995, boot 1196-1212) | — | Invalid parts dropped with notice; "수동 검토 필요", "공식 출처 확인 필요", "…맞다면 절차 선택으로 이동하세요. 자격·허가 여부는 보장하지 않습니다." | C |
| 20 | F-4 guided flow | CTA on F-4 result | `data/f4/` + base.json, diagnostic.json, faq.json, countries.json, country_overlays.json, sources.json | — | f4-route-guide.js (2068-2085) | — | `fetchFail` "F-4 안내 데이터를 불러오지 못했습니다. 이 안내 없이 진행하지 마시고…" (fail-closed); `notGuaranteeFootnote`; "공식근거 확인 필요" | C |
| 21 | Complex-status guide (F-6/G-1/E-7/F-5/D-2/D-4) | CTA on result | `doc_master.json` (986) | — | complex-status-guide.js | — | `docsHandoffNote`, `addDocsNote`, `sourcesHandoffNote` "…출처가 연결되지 않은 항목은 "공식근거 확인 필요"로 표시됩니다."; placeholder subcodes not offered | C |
| 22 | Short-stay entry checker | "단기입국 경로"/Short-stay entry routes, `open-short-stay` | `data/short-stay/rules.json` (23) | — | short-stay-checker.js; bootstrap bridge in backend-origin.js | — | `fetchFail` "국가별 목록 데이터를 불러오지 못했습니다. 이 상태에서는 무사증 가능 여부를 안내할 수 없습니다…" (fail-closed); `srcLegalLine`; `dataLoadFailBadge`; "K-ETA is not a visa", "entry never guaranteed" | C |
| 23 | HiKorea visit-reservation helper | "방문예약 안내"/Visit reservations, `open-hikorea-guide` | inline | localStorage `paradiso_hikorea_steps_done` | hikorea-reservation-helper.js | links to hikorea.go.kr | `hkDisc2`/`hkDisc3`; `wExpired`, `wUnsureGuidance`, `resultLeadLow` | I |
| 24 | Find my immigration office | "관할 출입국 찾기", `open-jurisdiction-modal` | inline `JUR_DB`/`OFFICE_INFO` | — | MAIN 18157-18578 | Naver/Kakao map links | `jurMissingInfo` "관할 관서 정보가 누락되었습니다."; `drawerJurisdictionNote` | I |
| 25 | Registered agencies | "등록 민원대행기관", `open-agent-finder` | `data/agent_registry_2026-04-30.json` | — | MAIN 25602-25805 | Naver/Kakao | `agentError` "…급하면 하이코리아 공식 조회에서 바로 확인할 수 있어요." | I |
| 26 | Designated hospitals | "법무부지정 병원", `open-med-finder` | `data/designated_medical_institutions_2026_04_30.json` | — | MAIN 25806-26004 | maps | `medDisclaimer` "…Visable은 의료기관을 추천하거나 검사 가능 여부를 보장하지 않습니다."; `medError` | I |
| 27 | Employment code finder | "직업신고 코드 찾기", `open-jobcode-modal`, chips, Enter | `JOBCODE_JSON_PATHS` (16931): `./data/jobcode_master.json`, `./data/output.json`*, `./jobcode_master.json`*, `./output.json`* (*not present in repo); 14 files `./data/employment/*.json` (17572-17585); dynamic import `./scripts/employment_interpret_client.mjs` | — | MAIN 16931-18100; employment_code_analyzer.mjs; employment_checklist.mjs | `${API_BASE}/api/employment/interpret` (interpret_client:10, 5 s timeout) | `jobCodeDisclaimer`, `jobCodePartial`, `jobCodeFinalCheck`, `jobCodeFinalConfirm`, "공식 코드 확인 필요". Load failure shows a "lookup unavailable" message (18063). Analyzer never invents codes | I |
| 28 | AI analysis modal / FAQ "verify with AI" | `open-ai-modal`, `verify-faq` | — | — | MAIN openAiModal 16597, fetch 18853 | BO `/api/ask` (75 s timeout) | 503 surfaces `aiNoProvider`; `aiTimeout`, `aiError`; `aiSourceDisclosure`, `aiAnswerBasisUnavailable` "확인된 출처 없음 · 공식 확인 필요", `lawGroundingReassure` | C |
| 29 | Status FAQ modal | `open-faq-modal` | inline | — | MAIN 16886 | — | UNVERIFIED | I |
| 30 | Deadline calculator in result card | `compute-deadlines`, `deadline-download-ics` | — | — | MAIN 21754-21838 | calendar.google.com template link; `.ics` download | `deadlineExtCaution` "…공식 신청기간을 보장하지 않습니다.", `deadlineCalendarCaution` | C |
| 31 | Saved reminders | "체류 기한 계산·알림", `#reminderSection` hash, `reveal-home-section` | — | localStorage `paradisoReminders`, `paradisoReminderBannerDismiss` | MAIN 26005-26316; reminder-dialog.js | Google Calendar link, `.ics` | `deadlineCalendarCaution` | I |
| 32 | Local-practice report | "실제 방문 내용이 달랐나요?" (`visable:local-report` event) | `data/local-practice-202609.json` | localStorage `visable.local-report.draft` | local-practice-report.js | POST **relative** `/api/local-practice/report` (not BO) | Never claims receipt; 503 NOT_CONFIGURED shown; PII patterns blocked; `sent` "제보가 접수됐어요 (검토 대기)…" | I |
| 33 | Easy Mode / card view modes | "쉬운 안내"/Easy Mode, `toggle-easy-mode`, `set-card-mode` | — | localStorage `paradiso:easyMode` (MAIN r/w, Cv read) | MAIN 22796-23070 | — | `easyModeNotice` "이것은 쉬운 설명이에요. 신청하기 전에 공식 근거를 꼭 확인하세요.", `easyModeNoDataBody` | C |
| 34 | Language switch / i18n | Language button, `apply-language`, `?lang=` | `./data/i18n/manifest.json`, `./data/i18n/` + `files[locale]`, `./data/i18n/official-terms.json`, `./data/i18n/visa-names.json` | `paradiso:language`, `paradiso:i18n-debug` | MAIN 23571-24100; S11; index-i18n-fallback.js; zh-traditional.js | — | Manifest failure falls back to built-in ko; glossary/names fall back to Korean canonical | I |
| 35 | Theme / brightness / skin | `toggle-theme`, `set-brightness`, `toggle-editorial-theme`, `open-global-settings` | — | `paradiso:brightness`, `paradiso:editorial-theme`, `visable:theme` | S1, S3, MAIN 24358-24453, S11, visable-theme.js, visable-theme-layout.js | Google Fonts, jsDelivr (Pretendard) CSS | Layout script only moves blocks, never drops disclaimers | P |
| 36 | City clock selector | `toggle-city`, `open-city-from-settings` | — | `paradiso_city` | MAIN 16283-16347 | — | — | P |
| 37 | Form composer section (#docComposer) | Home section | `./data/integrated_form_metadata.json` | — | MAIN 24598-24614 | — | `docComposerNote` "서식 작성 도우미는 참고용이며 제출·접수를 대행하지 않습니다…" | I |
| 38 | Eight life pathways / recommendations | "생활 경로 8종", `#pathwaySection` | — | — | MAIN showVisaRecommendations 25437 | — | UNVERIFIED | I |
| 39 | Copy result | `copy-visa-result`, `copy-jobcode-memo` | — | — | MAIN 23074, 17540 | — | UNVERIFIED whether disclaimer is included | P |
| 40 | Tool directory + links to other pages | "전체 도구 보기", `#csTools` hash, group filter | — | — | Cv 302-330 | form-helper, address-helper, immigration-checklists, manual, new-home, enforcement, ai.html | — | P |
| 41 | Waymaker floating button handoff | `.ai-fab` | — | — | MAIN 16640-16675 | `ai.html?visa_code&selected_procedure_key&selected_procedure_variant_id&scenario_label&lang` | Checklist/localStorage state never included | I |
| 42 | Command palette / direct search mode | `toggle-search`, `set-search-mode`, `close-cmd-palette`, `#q` arrow keys | — | — | MAIN 23202-23370, 24491 | — | `cmdDisclaimer` | I |
| 43 | Developer debug panels | `?debugSearch=1` or `#debugSearch`; `?debug=1`/`?dev=1` | — | `paradisoDevDiagnostics` | MAIN 16376, 16403, 18581-18590, 18814-18820 | `diagnostics` flag on `/api/ask` | dev only | P |
| 44 | Official PDF links + footer disclaimer | Source strip, footer | `docs/source-manuals/2026-10-19/visa_manual_261019.pdf`, `docs/source-manuals/2026-11-02/stay_manual_261102.pdf` (links, not fetched) | — | Cv:141, 450-455 | hikorea.go.kr | `disclaimer` "Visable은 공식 정부 서비스가 아닙니다. 제공 정보는 참고용이며 법적 효력이 없습니다. 최종 판단은 HiKorea·1345·관할 출입국·외국인관서에서 확인하세요."; `pendingInfo` "…일부 항목의 내용 검토는 별도로 진행 중이에요…" | C |
| 45 | Skip link / accessibility | Skip link, modal focus trap (Tab), Escape | — | — | S4; MAIN 16450-16550, 24965-25000 | — | — | P |
| 46 | Landing readiness bridge | Early taps before init | — | — | backend-origin.js 95-250 | loads `assets/css/landing-utility-restoration-20260908.css` | Replays exactly one intent | P |

**Total: 46 features. Critical 20, Important 18, Peripheral 8.**

Note on #44: `docs/source-manuals/**.pdf` are linked from the landing (not fetched). Those two
PDFs must stay in the deploy path (Phase 1 constraint).

### A. Every fetch / dynamic import (index.html + the modules above)
No XMLHttpRequest, sendBeacon or EventSource in scope.

| File:line | URL / expression |
|---|---|
| index.html:16981 | `fetch(path)` over `JOBCODE_JSON_PATHS` = `['./data/jobcode_master.json','./data/output.json','./jobcode_master.json','./output.json']` (16931) |
| index.html:17566 | `grab(p)`: `./data/employment/synonyms.ko.json`, `synonyms.en.json`, `synonyms.zh.json`, `aliases.entertainment.ko.json`, `aliases.entertainment.en.json`, `aliases.tattoo.ko.json`, `aliases.tattoo.en.json`, `ambiguous_inputs.json`, `classification_sources.json`, `colloquial_field_terms_ko.json`, `colloquial_field_terms_en.json`, `disambiguation_rules.json`, `income_brackets.json`, `multilingual_pivot.json` (17572-17585) |
| index.html:18072 | `import('./scripts/employment_interpret_client.mjs')` → `${apiBase}/api/employment/interpret` (client:10) |
| index.html:18853 | `` `${API_BASE}/api/ask` `` POST |
| index.html:18930 | `'./data/document_help.json'` |
| index.html:18991 | `'./data/doc_guide.json'` |
| index.html:23672 | `fetchJson(url)`: `I18N_MANIFEST_PATH='./data/i18n/manifest.json'` (23677); `'./data/i18n/' + (files[locale] \|\| locale+'.json')` (23686); `OFFICIAL_TERMS_PATH='./data/i18n/official-terms.json'` (23695/23742); `VISA_NAME_I18N_PATH='./data/i18n/visa-names.json'` (23703/23715) |
| index.html:24628 | `fetchOptionalJson(path)`: `./data/integrated_form_metadata.json` (24613), `./data/visa_issuance_records.json`, `./data/procedure_evidence_bindings.json`, `./data/official_web_overlays.json` (24639-24641) |
| index.html:24668 | `` `${API_BASE}/api/visas` `` |
| index.html:24675 | `'./visa_data.json'` |
| index.html:25782 | `'data/agent_registry_2026-04-30.json'` |
| index.html:25985 | `'data/designated_medical_institutions_2026_04_30.json'` |
| index.html:26348 | `"visa_data.json"` (S8 fallback) |
| civic-search.js:535 | `SUGGEST_INDEX_URL = 'data/search-suggest-index.json'` (529) |
| civic-search.js:806-808 | `'data/manual-corpus/catalog.json'`, then `fetchJson(source.sections)` |
| unified-search.js:951 | `base + '/api/search/unified'` |
| unified-search.js:987 | `apiBase() + '/api/search/unified/ai-overview'` |
| unified-search.js:1020 | `apiBase() + '/api/search/unified/ai-overview/stream'` |
| status-guidance.js:1600 | `'data/status-guidance-202609.json'` |
| status-guidance.js:1605 | `'data/local-practice-202609.json'` |
| waymaker-quick-answer.js:398 | `AI_ENDPOINT = '/api/waymaker/quick-answer'` (357), relative |
| complex-status-guide.js:986 | `'doc_master.json'` |
| f4-route-guide.js:2077 | `DATA_BASE + FILES[name]` = `'data/f4/' +` base/diagnostic/faq/countries/country_overlays/sources `.json` (45-52) |
| short-stay-checker.js:1551 | `RULES_URL = 'data/short-stay/rules.json'` (23) |
| local-practice-report.js:91 | `'data/local-practice-202609.json'` |
| local-practice-report.js:133 | `ENDPOINT = '/api/local-practice/report'` (41), relative POST |

Modules with no fetch: search-router, search-suggest, visa-route-guide, hikorea-reservation-helper, manual-corpus-search, manual-reader-route, reminder-dialog, index-i18n-fallback, zh-traditional, visable-theme, visable-theme-layout, anchored-overlay, backend-origin, document-help, ui-pictograms, employment_code_analyzer.mjs, employment_checklist.mjs.

### B. Every localStorage / sessionStorage key
All localStorage unless marked "ss" (sessionStorage). No cookies.

| Key | File:line | Read/write | Purpose |
|---|---|---|---|
| `paradiso:editorial-theme` | index 17-21; 24419/24426/24448; visable-theme.js:14, 24, 175 | r/w | Editorial theme |
| `paradiso:brightness` | index 14479 (r), 24364 (w), 26762 (r), 26807 (w) | r/w | Light/dark/system |
| `visable:theme` | visable-theme.js:13, 22 (r), 174 (w) | r/w | Skin |
| `paradiso_city` | index 16285 (w), 16338 (r) | r/w | Clock city |
| `paradisoDevDiagnostics` | index 18588, 18819 | r | Dev diagnostics |
| `paradiso:scenario-checklist:<code>:<proc>:<variant>:<group>:<hash>` | index 21102, 21121-21139, 21339-21345 | r/w/remove | Checklist ticks |
| `paradiso:easyMode` | index 22817-22818 (r), 23068 (w); civic-search.js:138 (r) | r/w | Easy Mode |
| `paradiso:language` | index 23571, 23973 (r), 24098 (w) | r/w | UI language |
| `paradiso:i18n-debug` | index 23868 | r | i18n debug |
| `paradisoReminders` | index 26014, 26061 (r), 26067 (w) | r/w | Saved reminders |
| `paradisoReminderBannerDismiss` | index 26015, 26255 (r), 26273 (w) | r/w | Banner dismissed for the day |
| `paradiso_hikorea_steps_done` | hikorea-reservation-helper.js:1361, 1380 (r), 1385 (w) | r/w | Step progress |
| `visable.local-report.draft` | local-practice-report.js:42, 131 (w), 137 (remove) | w/remove | Report draft |
| ss `visable.example-ids` | civic-search.js:289 (r), 291 (w) | r/w | Rotating example chips |
| ss `visable.search-handoff` | civic-search.js:785 | w | Question handed to ai.html |
| ss `visable.sg.<query>` | status-guidance.js:1621-1623 | r/w | Guidance answers/state |
| ss `visable.waymaker.handoff` | waymaker-quick-answer.js:418, 438 (w), 445 (r) | r/w | Quick-answer packet handed to ai.html |

### C. URL query parameters and hash routes
| Name | File:line | What it does |
|---|---|---|
| `?q=` | index 14483 (body → searched scene), 14842 (prefill #q), 24463 (initUI runs renderResults); civic-search.js:994 (popstate), 1007 (delete q, replaceState); unified-search.js:815/822-823, 1127-1129 (pushState `{paradisoQuery}`), 1134 (popstate), 1234 (boot) | Shareable search |
| `?lang=` | index 23985 | Overrides the stored language |
| `?code=`, `?subcode=`, `?procedure=` | visa-route-guide.js:416-431 (parse/serialize), 984-995 (push/replaceState `{paradisoRoute}`), 998, 1196 (popstate), 1202 (boot, polls up to about 12 s for data) | Deep link to status, subcode and procedure |
| `?debugSearch=1` / hash containing `debugSearch` | index 16376-16377 | Search debug panel |
| `?debug=1` / `?dev=1` | index 18589, 18820 | AI dev diagnostics |
| `#csTools` | civic-search.js:411, 999 (hashchange) | Opens the tool directory |
| `#reminderSection` | reminder-dialog.js:86-87 (hashchange) | Opens the reminder dialog |
| `#<id>` | index 14506 | Skip link writes the hash via replaceState |
| Outgoing: `ai.html?handoff=search&lang=` | civic-search.js:786 | Handoff from home search |
| Outgoing: `ai.html?q=` | unified-search.js:1194 | "Open Waymaker" from the strip |
| Outgoing: `ai.html?handoff=quick-answer&visa_code&selected_procedure_key&lang` | waymaker-quick-answer.js:439 | Quick-answer handoff |
| Outgoing: `ai.html?visa_code&selected_procedure_key&selected_procedure_variant_id&scenario_label&lang` | index 16646-16654 | Floating Waymaker button |
| Outgoing: `manual.html#c-<chapter>.<v\|s>[.<section>]` | manual-reader-route.js | Manual reader deep link |

### Things to watch in the rebuild
- Two endpoints do not use the backend origin: `/api/waymaker/quick-answer` and `/api/local-practice/report` are relative (same-host Vercel functions). Every other API call goes through `VisableBackend.origin()` or `API_BASE`.
- Three job-code fallback paths point to missing files (see phase0-data-canon.md).
- The visa issuance data is optional and fails silently (section disappears without a notice). Candidate for a Phase 3 bug-fix commit only if the owner agrees it is a bug; otherwise preserved.
- UNVERIFIED: the FAQ modal (#29), the pathways section (#38), whether copied results include the disclaimer (#39), the exact Korean job-code load-failure message (18063), and how `document_help.json` / `doc_guide.json` failures are shown (#13).

### Language coverage (verified)
- UI packs: 14 locales in `data/i18n/manifest.json` (`ko en zh-CN ja vi tl id ru fr es ar de tr uk`) + `zh-TW` rendered from zh-CN via `assets/js/zh-traditional.js` = **15 selectable UI languages** (language dialog lists 15).
- Post-search guidance (`status-guidance.js`): `STR` has **ko and en only**; `lang()` (line 1595) maps every non-Korean document language to `en`. So guidance renders in English for the 13 other locales (Arabic page stays RTL, guidance block is English LTR).
- Footer disclaimer `footerNotice`: Korean in ko.json; the **English sentence** in every other pack (verified by reading all 14 packs).
- Home copy: `civic` object (128 keys) in every pack; ko/en also embedded in civic-search.js (`scripts/check_landing_shell.mjs` asserts parity).

---

## Part 2 — The other root pages

Pages present after origin/main @ 5082d9d: ai.html, address-helper.html (added by PR #757, 2026-11-03,
not in the brief's count), content-studio.html, enforcement.html, form-helper.html,
immigration-checklists.html, knowledge-studio.html, manual.html, nationality-interview-hub.html,
new-home.html, preview.html = **11 other pages, 12 total**.

### 0. Shared plumbing
Shared stylesheets/scripts on most pages (same `?v=` as index.html): `assets/css/visable-theme-skins.css?v=20261026-original`,
`assets/css/visable-theme-legacy.css?v=20261023`, `assets/js/anchored-overlay.js?v=20261028`,
`assets/js/visable-theme.js?v=20261028-anchor`, `assets/css/ui-consistency.css?v=20261102-ui2`, `assets/js/ui-pictograms.js` (defer).
Exceptions: preview.html loads only ui-consistency.css + ui-pictograms.js; manual.html loads all six.

Version drift: index.html loads `civic-search.css?v=20261026-theme-ui1`; ai/enforcement/form-helper/nationality-interview-hub load it with no `?v`.
`backend-origin.js?v=20260826` on index/ai/nationality-hub/preview; no `?v` on content-studio/enforcement/immigration-checklists/knowledge-studio.
new-home.html loads `visable-product-2026.css?v=20260925-family` while index.html loads `?v=20261026-archive-search` (Phase 2 hashed filenames remove this class of drift).

- `visable-theme.js`: localStorage `visable:theme` (`default|stamp|chrome|neon`), `paradiso:editorial-theme`; injects Google Fonts at runtime.
- `backend-origin.js`: `VisableBackend.origin()` = `PARADISO_BACKEND_URL` → `''` on localhost/127.0.0.1/file: → `https://web-production-14f9a.up.railway.app`. Several scripts hard-code that origin as a fallback too.
- `service-navigation.js` (34 lines): localizes `[data-vs-service-nav]` with an inline 15-locale dictionary, sets `aria-current`.
- Shared storage: `paradiso:brightness` (dark/light/system), `paradiso:editorial-theme` (civic_editorial/archive_diary), `paradiso:language`.
- Pretendard CDN css (jsdelivr) on ai, form-helper (linked twice), manual, nationality-hub, new-home, preview, index.

### 1. ai.html — Waymaker AI chat, procedure navigator, legal research (3,356 lines)
Inline scripts (7): 17-28 editorial theme; 49-54 brightness; 77-87 theme button; 343-3061 main app; 3076-3291 navigator mount; 3292-3353 surface switcher (injects a `<style>` at runtime). No inline `<style>`.
Stylesheets: Pretendard CDN, `waymaker-navigator.css?v=20260628-mobile`, `visable-product-2026.css?v=20261026-archive-search`, `civic-search.css`, `waymaker-workspace.css?v=20260925-answer`, theme CSS, ui-consistency.
Scripts: anchored-overlay, visable-theme, ui-pictograms, `backend-origin.js?v=20260826`, `zh-traditional.js`, `waymaker-navigator.js` (2,354 lines), `waymaker-quick-answer.js`, `legal-source-search.js?v=20260628-mobile` (defer), `waymaker-workspace.js?v=20260703-chat-first`.

| Feature | Entry | Data | Storage | Owner | External | Safety / fail-closed | Tag |
|---|---|---|---|---|---|---|---|
| AI chat (default surface) | nav "AI 상담"; textarea `#aiQ` (500 chars); `#sendBtn` | `${API_BASE}/api/visas` → `./visa_data.json` | `paradiso_ai_consent` `{agreed,at}` (24 h) | inline 343-3061 | POST `${API_BASE}/api/ask` (backend → OpenRouter) | Welcome: "답변은 법적 효력이 없으며, 최종 판단은 HiKorea·1345·관할 출입국기관에서 확인하세요." `#referenceDisclaimer`: "이 서비스는 공개 법령·매뉴얼을 바탕으로 한 참고용 정보 제공 도구이며, 법적 상담이나 민원 대행이 아닙니다…" Grounded: "※ 표시된 공식 매뉴얼 근거 범위 안에서 생성된 참고용 안내입니다…" Ungrounded: "※ 이 답변은 공식 매뉴얼 근거가 확인되지 않은 일반 참고 안내입니다…" 75 s timeout message; 429 message; network error "네트워크 오류: 서버 응답을 받지 못했습니다."; if both visa-data sources fail the status line stays honest | C (BLOCKED for live) |
| Consent modal | before first send; "확인 및 동의" / "동의 거부 (이전으로)" | — | `paradiso_ai_consent` | inline `handleConsent` l.886 | — | "면책 조항: AI가 생성한 결과는 2026년 실무 매뉴얼을 바탕으로 한 참고용 정보일 뿐, 법적 효력이 없습니다…"; refusing → `history.back()` or alert | C |
| Structured answer card (`#pa-answer-card-shell`) | when `/api/ask` returns `structured_answer` | — | — | inline | — | Buckets 기본/증빙/해당하는 경우 제출/추가로 요청될 수 있는 서류/"확인이 필요한 서류" (DATA_MISSING never hidden); slots "수수료·예약", "유의사항", "공식 기관 확인이 꼭 필요한 주제", "공식 근거", `disclaimer_snippet` always last | C |
| Daily quota badge | header "오늘 N회 남음" | — | `paradiso_ai_quota` `{date,count}` limit 30 | inline | — | send disabled at quota (client only) | I |
| Answer mode 빠른/정밀 | `#aiModeSelector` | — | `paradiso:waymakerAnswerMode` | inline ~2835-2860 | `answer_mode` | — | I |
| Easy mode | global pref | `data/i18n/manifest.json`, `data/i18n/<locale>.json` | `paradiso:easyMode` | inline ~1060-1106 | — | — | I |
| Answer feedback | per-answer reasons | — | — | inline ~2262 | POST `${API_BASE}/api/feedback` | "지금은 보내지 못했어요. 잠시 후 다시 시도해 주세요." | P |
| Scenario deep-link context | `?visa_code&selected_procedure_key&selected_procedure_variant_id&scenario_label&lang` | — | — | inline ~775-830 | forwarded to `/api/ask` | — | C |
| Nationality coach framing | `?domain=nationality`, `&mode=naturalization_interview_prep` | — | — | inline ~756-770; 3092 | `/api/ask` | — | I |
| Index search handoff | `?handoff=search` | — | ss `visable.search-handoff` (read, removed) | inline 2992-3008 | — | — | I |
| Quick Answer handoff | `?handoff=quick-answer` | — | ss `visable.waymaker.handoff` (v1) | QA l.418-445 + inline 2956 | — | UNVERIFIED whether `/api/waymaker/quick-answer` ever fires on ai.html | C |
| Procedure navigator | `ai.html?nav=1`; steps intro→language→location→status→procedure→subStatus→packet | `/api/visas` → `./visa_data.json` | `paradiso_waymaker_locale`; `paradiso_waymaker_checklist_v1:<status>:<procedureKey>`; `paradisoDevDiagnostics` | waymaker-navigator.js + inline 3076-3291 | GET `${apiBase}/api/procedure-packet?status=&procedure=&locale=`; `/api/ask`; links hikorea.go.kr, `form-helper.html?source=waymaker&visa=…&procedure=…` | **Fail-closed:** 400/503/network → `makeCoverageLimitedShell` ("fabricates NOTHING": empty documents/fees, `sourceBacked:false`, `coverageSummary.isLimited`); labels "관할기관 확인 필요", "확인 필요 항목", "체류자격 확인 필요" | C |
| Legal source search / research | `#legalSourceSearchRoot`; nav "법령·판례 찾기"; `paradiso:legal-research` event | — | — | legal-source-search.js; waymaker-workspace.js routes hash | GET `/api/legal/laws/search?q=`, `/api/legal/precedents/search?q=`; POST `/api/legal/research/stream` (SSE), `/api/legal/research`; links law.go.kr | "Waymaker 리걸 리서치는 … 참고용 도구입니다. 변호사·행정사의 법률 자문을 대체하지 …"; "판례는 개별 사건 판단이며 결과를 보장하지 않습니다…"; "이번 정리에는 붙은 출처가 없어요…"; error → "…하이코리아·1345 또는 공식 자료에서 확인하세요." | C (BLOCKED) |
| Surface switcher bar | "바로가기" links | — | — | inline 3292-3353 | — | — | P |
| Brightness toggle | `#aiThemeBtn` | — | `paradiso:brightness` | inline 49-54, 77-87 | — | — | P |
| Dev diagnostics | `?debug=1`/`?dev=1` | — | `paradisoDevDiagnostics` | inline ~1277 | `diagnostics:true` | — | P |

Languages: shell `t()/tt()` ko/en/zh/zhHant only (never RTL); answer language detected from the question; Easy mode uses data/i18n packs; navigator content 14 locales + zh-TW; legal search ko/en.
Offline: shell, consent, quota/mode UI, visa_data fallback, navigator steps ending in the coverage-limited shell (fail-closed path), error/timeout messages. **BLOCKED:** chat answers, feedback, procedure packets, legal search/research.

### 2. address-helper.html (added by PR #757; inventoried by this session from the PR diff summary — UNVERIFIED in depth)
Korean road-name address helper: on-device OCR → official MOIS JUSO search → KO/EN copy card. Assets `assets/js/address-helper.js`, `address-ocr-core.js`, `assets/css/address-helper.css`; checks `scripts/check_address_helper.mjs` (repo.sh), `tests/e2e/address-helper.spec.mjs` (not in CI), `tests/unit/address-helper.test.js`. Tag: I. Needs the external JUSO API for live search (BLOCKED for golden); the controller ids (#language, #search, #keyword, #manualHelp, #candidates, #selected, #krResult, #enResult, #unit, #copyComplete) are asserted by its own check.

### 3. content-studio.html — operator CMS (142 lines; no inline script/style; `noindex`)
Stylesheets: `content-studio.css`, theme CSS, ui-consistency. Scripts: anchored-overlay, visable-theme, ui-pictograms, `backend-origin.js` (no `?v`), `content-studio.js` (1,617 lines).
Features: operator login ("운영자 보안 토큰", min 16 chars, "스튜디오 연결"; sessionStorage `visable.cs.token`; GET `/api/knowledge/studio/checklists/auth/me` Bearer; 503 "운영자 인증 시스템이 설정되지 않았습니다 (WAYMAKER_OPERATOR_TOKENS 미설정)."; 401 "토큰이 올바르지 않거나 만료되었습니다.") — I (operator). Tabs 대시보드/편집기/관서별 차이/검토 대기열/Diff/게시 파이프라인, all under `/api/knowledge/studio/checklists/*` — I. Release preview link → `immigration-checklists.html?preview_release=<id>` — P. Korean only. **BLOCKED** beyond the login screen.

### 4. enforcement.html — violation disposition estimator (154 lines; no inline script/style)
Stylesheets: `enforcement.css`, `civic-search.css`, `service-navigation.css`, theme CSS, ui-consistency. Scripts: service-navigation (defer), anchored-overlay, visable-theme, ui-pictograms, `backend-origin.js`, `<script type="module" src="scripts/enforcement-ui.mjs">` (986 lines).
| Feature | Entry | Calls | Notices / fail-closed | Tag |
|---|---|---|---|---|
| Step 1 case input | `#case-text` (3000 chars); example chips; "과거 시점 기준으로 분석하기"; "내용 확인하기" | POST `/api/enforcement/extract` | "개인정보는 빼고 적어 주세요…원문 서술은 저장하지 않습니다." | C (BLOCKED) |
| Step 2 fact confirmation | "맞아요 · 분석하기" / "일부 내용이 달라요" | — | "법률 판단이 아니라 사실 확인 단계입니다." | C |
| Step 3 result | baseline then full; "AI 예상 다시 확인" | POST `/api/enforcement/analyze` `{baselineOnly:true}` (10 s) then full (28 s); backend → OpenRouter | "법령이 정한 기준과 Visable의 예상은 서로 다른 정보입니다."; "검증되지 않은 범칙금은 표시하지 않습니다."; "AI 예상을 받지 못했습니다 (…). 법령 기준은 그대로 유효합니다."; "AI 응답이 근거·형식 검증을 통과하지 못해 표시하지 않았습니다."; "이 위반 유형은 아직 Visable 계산 규칙에 없습니다."; grounding labels VERIFIED/AUDIT_ONLY/LIMITED/UNAVAILABLE; footer "정보 제공용 도구이며 출입국 당국의 최종 처분 또는 법률 자문을 대신하지 않습니다." | C (BLOCKED) |
Note: `<meta name="api-base" content=".">` makes the page call `./api/enforcement/...` on the same origin (Vercel functions under api/enforcement/), never the Railway origin. Missing backend → "Visable 분석 서버에 연결하지 못했습니다…". Korean UI; `detectLocale(text)` picks the response locale. Offline-testable: step UI, examples, validation, connection-error message.

### 5. form-helper.html — fill official forms client-side (77 lines; one inline brightness line at 26)
Stylesheets: Pretendard CDN (×2), `civic-search.css`, `form-helper.css?v=20261026-narrow-rtl`, `service-navigation.css`, theme CSS, ui-consistency. Scripts: service-navigation, anchored-overlay, visable-theme, ui-pictograms, `zh-traditional.js`, `form-engine.js`, `form-helper-app.js`; on demand `assets/forms/vendor/pdf-lib.min.js`, `fontkit.umd.min.js`.
| Feature | Entry | Data | Storage | Notices | Tag |
|---|---|---|---|---|---|
| Form search → explain → edit → review → preview/export | hash `#form=<ID>&screen=<explain\|edit\|review\|preview>&step=<n>`; `?form=`, `type`, `procedure`, `source=waymaker`, `visa`, `lang` | `data/form_definitions.json`, `data/form_schemas.json`, `data/forms_inventory.json` (opt), `assets/forms/fonts/NanumGothic-Regular.charset.json` (opt), `data/i18n/<lang>.json` (`fh` key), font `assets/forms/fonts/NanumGothic-Regular.ttf`, template PDFs `assets/forms/pdf/F01.pdf`… | `paradiso:language`, `paradiso:brightness`; form values never stored | "입력한 내용은 이 브라우저 안에서만 쓰여요. 서버로 보내지 않고 저장하지도 않아요…"; "참고용 도구예요. 허가 여부와 서류 적합성은 관할 출입국·외국인관서가 판단해요."; "Visable — 공식 정부 서비스가 아니에요."; "서명/인은 제출할 때 직접 해요…"; `sourceLine` | C |
| Excluded/blocked form handoff | search results | — | — | "난민·출국기한유예 관련 서식은 사안이 민감해 이 도구에서 다루지 않아요…" / "이 서식은 아직 자동작성이 준비되지 않았어요…"; links hikorea.go.kr, `tel:1345` | C |
| Export PDF | `t('export')`; issues dialog exportFix/exportAnyway | — | — | "PDF를 만들지 못했어요: {error}", "서식 PDF를 불러오지 못했어요…", "글꼴을 불러오지 못했어요." | C |
| Waymaker origin banner | `?source=waymaker` → `ai.html?nav=1` | — | — | — | P |
| Reset/zoom/`#fhLang`/`#fhTheme` | — | — | — | boot failure → `body.fh-boot-failed`, `#fhBootError` | P |
No `/api` calls. 15 locales from `data/i18n/*.json` (`fh` key, ko fallback; zh-TW = zh-CN + ParadisoZhT). Fully offline over HTTP.

### 6. immigration-checklists.html — checklists by situation (791 lines; no inline script/style)
Stylesheets: `immigration-checklists.css`, `service-navigation.css`, theme CSS, ui-consistency. Scripts: `backend-origin.js` (defer), `zh-traditional.js`, `visable-i18n.js` (1,455 lines), `immigration-checklists.js` (2,427 lines), service-navigation, anchored-overlay, visable-theme, ui-pictograms.
| Feature | Entry | Data | Storage | External | Notices | Tag |
|---|---|---|---|---|---|---|
| Guided 4-step finder | `#guided-discovery` task cards `data-procedure=extension\|change\|registration` (+`data-sub=residence`); `#status-picker-input` with chips (D-2, D-10-1, E-7-1, E-9, F-2-7, F-4, F-5, F-6-1, H-2) | `data/immigration-checklists/extension-202609.json`, `change-202609.json`, `registration-202609.json`, `reference-notes-202609.json`, `local-overrides.json`, `data/local-practice-202609.json` | `visable.checklists.checked.v1` | GET `/api/checklists/published` (silent static fallback) | "※ 위 상황 목록은 2026년 9월 매뉴얼 공식 편제 항목을 기준으로 분류된 정본입니다. 임의로 조건을 추가하거나 생략하지 않았습니다."; "참고용 · 원문 확인"; "※ 숫자는 확정된 기본 제출서류만을 기준으로 계산되며…"; "조건부 확인"; "방문 전 확인사항 및 법적 한계"; failure "서류 데이터를 가져오지 못했어요." / "연결을 확인하고 페이지를 새로고침해 주세요." | C |
| Search "서류 찾아보기" | `#search-section`, `#query`, `#office`, "선택 초기화 ↺", "결과 더 보기" | same | — | — | "이 목록은 2026년 9월 매뉴얼에 기반한 편집 자료이며 관서 공식 확정 목록이 아닙니다. '목록 미제시'는 서류가 필요 없다는 뜻이 아니에요…" | C |
| Office callouts | office selects | local-overrides, local-practice | — | — | "관서별 편집 초안 · 공개되지 않음" / "관서 공식 안내 · …" by `review_state` | C |
| Deep link | `?procedure\|proc=`, `code\|status=`, `scenario=`, `office=`, `lang=`; `#operator` | — | — | — | — | I |
| Print / copy link / clear | `#checklist-print-btn`, `#checklist-copy-link-btn`, "체크 상태 초기화" | — | `visable.checklists.checked.v1` | — | — | I |
| Candidate preview (operator) | `?preview_release=`/`?preview=` | — | — | GET `/api/checklists/preview?release_id=` | banner; malformed candidate keeps baseline | I |
| Operator/draft mode | `#operator-mode-toggle`/`#operator`; edit dialog; JSON exports | — | `visable.checklists.nationalDrafts.v1`, `visable.checklists.officeDrafts.v1` | links content-studio, GitHub | "이 기기에는 저장할 수 없습니다. JSON을 먼저 내려받으세요." | P |
| Beta feedback | "베타 개선 의견 보내기" | — | `visable.beta.feedback.v1` | — | PII block `#fb-pii-warning` | P |
| Help / links | "절차 구별 가이드 보기"; HiKorea; `data/immigration-checklists/snapshot-202609.md`; `form-helper.html?lang=` | — | — | — | — | I |
15 locales via `#lang-select` (`visable-i18n.js` inline `CHECKLIST_STRINGS` then packs; `?lang` > `paradiso:language` > ko; ar RTL). Public features offline-testable; preview needs backend.

### 7. knowledge-studio.html — Waymaker Knowledge Studio (87 lines; no inline script/style)
Login "운영자 토큰"/"연결"; sessionStorage `waymaker.ks.token`; tabs 개요/검토 대기열/지식/충돌/출처·버전/커버리지 공백/미지 질문/평가/감사 기록; all `/api/knowledge/studio/*` Bearer. 503 "이 서버에서는 Knowledge Studio가 꺼져 있습니다(운영자 토큰 미설정)."; 401 "토큰이 유효하지 않습니다."; network "서버에 연결하지 못했습니다." Tag I (operator). Korean only. **BLOCKED** beyond login. (tests/e2e/knowledge-studio.spec.mjs runs in CI with a mocked backend.)

### 8. manual.html — official manual reader (54 lines; inline brightness script 13-16)
Stylesheets: Pretendard CDN, `manual-reader.css`, `manual-reader-staging.css`, `service-navigation.css`, theme CSS, ui-consistency. Scripts: `manual-reader-route.js`, `manual-reader.js` (541 lines), service-navigation, anchored-overlay, visable-theme, ui-pictograms.
| Feature | Entry | Data | Storage | Notices | Tag |
|---|---|---|---|---|---|
| Home / task filter | `#home`, task buttons, `#clr` | `data/manual-reader/catalog.json`, `editorial.json` | `visable:manual-reader:task` | Edition banner "…판본은 기준 판본으로 정해졌지만, 변환된 본문을 사람이 한 줄씩 대조한 것은 아닙니다…공식 PDF를 열어 주세요."; intro "…쉬운 말 제목·자격 소개·용어 풀이·서류 체크는 Visable 편집 안내이며 법적 요건이 아닙니다…" | C |
| Chapter reader | `#c-<chapter>.<v\|s>[.<section>]`; v=사증, s=체류 never mixed; subcodes → parent chapter | `data/manual-reader/chapters/<v\|s>/<key>.json` (lazy); `assets/manual-reader/img/` | — | "공식 원문 발췌 … 굵은 제목은 Visable이 붙인 쉬운 말이고… 표·그림과 적용 조건은 공식 PDF에서 확인하세요."; "이 자격에는 해당 항목이 따로 없어요. 전체 안내를 확인하세요." | C |
| Per-section doc checklist | checkboxes | — | `visable:manual-reader:ck:<sectionKey>` | — | I |
| Search `#mr-q` | input | `data/manual-reader/search.json` (lazy) | — | "검색 색인을 불러오지 못했어요…" | C |
| Glossary | `#glossary` | editorial.json | — | — | I |
| Font size | 가−/가+ | — | `visable:manual-reader:fs` (14-22) | — | P |
| Official PDF links | `docs/source-manuals/2026-10-19/visa_manual_261019.pdf`, `docs/source-manuals/2026-11-02/stay_manual_261102.pdf` | — | — | failure "매뉴얼 원문을 불러오지 못했어요. 새로고침하거나 공식 PDF를 여세요"; `<noscript>` PDF links | C |
No external calls. Korean only (service nav localized). Fully offline.

### 9. nationality-interview-hub.html (429 lines; inline script 12-29; inline `<style>` 32-244)
Stylesheets: Pretendard CDN, `visable-product-2026.css?v=20261026-archive-search`, `civic-search.css`, `service-navigation.css`, theme CSS, ui-consistency. Scripts: service-navigation, anchored-overlay, visable-theme, ui-pictograms, `backend-origin.js?v=20260826`, `zh-traditional.js`, `nationality-interview-hub.js?v=20260628` (1,641 lines).
Features: 국적민원 search/filter (`data/nationality_service_guides.json`, 15 guides) C; 관련 법령·지침 tabs (`data/nationality_service_sources.json`, `safeUrl` https/http only) C; 절차·서류 흐름 C; 귀화면접 학습실 (`data/naturalization_interview_questions.json` 52, `data/naturalization_learning_topics.json`) I; mock interview + AI coach (POST `${apiBase}/api/nationality-coach`, 14 s; **fail-closed** local rubric "AI 피드백을 불러오지 못했습니다. 기본 점검 결과를 먼저 확인해 주세요."; every result "이 피드백은 연습용이며 실제 심사 결과를 보장하지 않습니다.") I (AI part BLOCKED); KIIP I; videos (`data/naturalization_video_sources.json`) P; Waymaker CTAs → `ai.html?domain=nationality[&mode=naturalization_interview_prep]` ("합격 여부를 예측하지 않으며…") I; footer "New Home은 공식 기관과 제휴 또는 소속 관계가 없습니다…" + load failure "데이터를 불러오지 못했습니다. 페이지를 새로고침해 주세요." C; `#langToggle`, `#brightToggle` P.
Storage: `paradiso:language` (written only on toggle), `paradiso:brightness`, `paradiso:editorial-theme`. Inline `I18N` dictionary, `SUPPORTED_LANGS` 14 + zh-TW; data body text is mostly Korean (`*_ko`).

### 10. new-home.html — nationality/naturalization landing (1,229 lines)
Inline scripts: 13-22 editorial theme; 42-46 brightness; 240-1227 whole app. No inline style. Stylesheets: Pretendard CDN, `visable-product-2026.css?v=20260925-family`, `civic-search.css`, `new-home.css?v=20260925-family`, `service-navigation.css`, theme CSS, ui-consistency. Scripts: service-navigation, anchored-overlay, visable-theme, ui-pictograms, `zh-traditional.js`.
Features: hero + notice ("국적 업무는 개인 사정과 최신 법령·지침에 따라 달라질 수 있습니다…최종 판단은 관할기관 확인이 필요합니다.") `data/nationality_content.json` C; readiness check modal → pathfinder (`data/nationality_flows.json`, `data/nationality_paths.json`) C; dashboard/pathway I; KIIP I; after-approval checklist ("…모든 분께 동일하게 적용되는 완전한 목록은 아닙니다.") I; hub cards/detail modal I; Waymaker CTA → `ai.html?domain=nationality` ("…AI는 생성된 안내를 설명하는 보조 역할만 하며, 서류·수수료·기한을 새로 만들지 않습니다…") I; interview bridge → nationality-interview-hub P; caution block ("…최종 자격·허가 여부를 단정하거나 법률 자문을 대신하지 않습니다.") C; sources panel (`data/nationality_sources.json`; "링크와 공개 메타데이터는 2026-06-28에 확인했으며…"; no-affiliation note) C; language menu/theme/brightness (untranslated locales: "이 페이지는 선택한 언어 번역 준비 중입니다 · This page is not yet translated into the selected language.") P.
Load failure "콘텐츠를 불러오지 못했습니다. / Content could not be loaded." Storage `paradiso:language`, `paradiso:editorial-theme`, `paradiso:brightness`. Content ko/en/zh-CN (+zh-TW); other 11 locales render Korean with the note. No external calls. Fully offline.

### 11. preview.html — PreView pre-arrival checker MVP (182 lines; inline scripts 12-19, 26-36)
Stylesheets: Pretendard CDN, `preview.css?v=20260704`, `ui-consistency.css?v=20261102-ui2`. Scripts: ui-pictograms, `assets/js/preview/preview-data.js?v=20260704`, `backend-origin.js?v=20260826`, `assets/js/preview/preview-app.js?v=20260704`. No visable-theme.js, no service nav. Orphan: nothing links to it.
Pre-check form (`#pvCountry` vn/mn/uz/other, `#pvNationality`, `#pvPurpose`, `#pvLanguage`, "입국 전 확인사항 보기"): GET `${base}/api/preview/mission?country=` (6 s); links allowed only to overseas.mofa.go.kr, www.mofa.go.kr, www.data.go.kr. **Fallback:** "현재 공공데이터 API 응답을 불러오지 못해 MVP 샘플 데이터를 표시합니다. 최종 정보는 관할 재외공관 공식 원문을 확인해야 합니다."; "MVP 샘플 범위 밖 국가입니다…"; "공식 원문 확인 필요"; "최종 사증 발급 여부, 접수 가능 여부, 요구서류, 심사 결과는 관할 재외공관의 공식 안내와 판단을 따라야 합니다."; "PreView가 하지 않는 것". C. No LLM calls. Korean with English glosses; no i18n. Offline-testable via the fallback path.

### 12. Navigation between pages
Shared service bar `<nav class="vs-service-nav" data-vs-service-nav>`: `index.html#csTools` "전체 도구", `index.html` "비자·체류 검색", `ai.html` "Waymaker 상담". Present on enforcement, form-helper, immigration-checklists, manual, nationality-interview-hub, new-home; absent on ai, content-studio, knowledge-studio, preview. Wordmark → `index.html` everywhere except content-studio (→ immigration-checklists.html).

| From | Links to |
|---|---|
| ai.html | `ai.html`, `ai.html?nav=1`, `ai.html#legalSourceSearchRoot`, `index.html#csTools`, `form-helper.html`, `nationality-interview-hub.html#interview`, `ai.html?domain=nationality`, `ai.html?domain=nationality&mode=naturalization_interview_prep`, `form-helper.html?source=waymaker&visa=…&procedure=…` |
| form-helper.html | `immigration-checklists.html`; `ai.html?nav=1` |
| immigration-checklists.html | `form-helper.html` (+`?lang=`), `content-studio.html`, `#guided-discovery`, `#search-section`; copy-link → `immigration-checklists.html?…` |
| content-studio.html | `immigration-checklists.html`, `knowledge-studio.html`, `immigration-checklists.html?preview_release=<id>` |
| new-home.html | `index.html`, `ai.html?domain=nationality`, `nationality-interview-hub.html` |
| nationality-interview-hub.html | `new-home.html`, `ai.html?domain=nationality`, `…&mode=naturalization_interview_prep` |
| manual.html | `#home`, `#glossary`, `#c-…`, `index.html`, `docs/source-manuals/…pdf` |
| enforcement, knowledge-studio, preview | `index.html` and the service bar where present |
index.html (~14603) links to form-helper, new-home, immigration-checklists, manual, enforcement; JS builds `ai.html?handoff=…`, `manual.html#c-…`. Not linked from index.html: knowledge-studio, content-studio, preview.

### 13. UNVERIFIED (other pages)
- Whether `/api/waymaker/quick-answer` is ever called on ai.html.
- Whether production serves `/api/enforcement/*` from the static host (api/enforcement/*.js exist in the repo, so very likely yes; not exercised here).
- Exact rendered wording of the navigator packet disclaimer/coverage text and the full immigration-checklists "cautions" group.

### Offline testing summary
- Work without any backend over HTTP: form-helper, manual, new-home, preview (sample fallback), immigration-checklists (static fallback), nationality-hub except the AI coach, index.html except the Railway-backed layers (unified-search strip/AI overview, `/api/ask`, `/api/visas` → static fallback).
- BLOCKED (live keys/providers): content-studio, knowledge-studio (operator token), enforcement (backend + OpenRouter), ai.html AI/packet/legal-search, address-helper live JUSO search, Waymaker Quick Answer AI rewrite (deterministic answer works offline). Their fail-closed messages are testable offline.
