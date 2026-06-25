# Waymaker All-Status Procedure Navigator — Phase 0 Preflight & Inventory

**Date:** 2026-06-25
**Branch:** `waymaker-all-status-procedure-navigator-mobile-refactor`
**Scope:** Reposition Waymaker from an AI visa chatbot into an official-source-grounded, all-status Korean immigration **procedure navigator**. Authoritative result = deterministic Procedure Packet; AI = secondary support only.

> This report is the required Phase 0 deliverable. It was produced by a fan-out of 8 parallel code readers over `ai.html`, `new-home.html`, `index.html`, the backend, the `assets/js` helpers, the i18n packs, and the test harness, plus deterministic extraction of the canonical status/procedure data. File:line anchors are included so the implementation slice can act directly.

---

## 0. Executive summary & refactor strategy

**Key finding — the deterministic backend already exists and has zero frontend callers.** `GET /api/procedure-packet?status=&procedure=&locale=` and `GET /api/visas/{code}/packets` (backed by `backend/services/procedure_packet_builder.py`) are fully built and tested, returning a ~20-key structured packet that maps almost 1:1 to the spec's 12 Action Packet sections. A repo-wide search confirms **no** frontend caller: `ai.html` only calls `GET /api/visas` and `POST /api/ask`. **The refactor is therefore primarily frontend wiring + copy/i18n + mobile + tests, not new backend.**

**The LLM `/api/ask` path becomes secondary.** Today it is the only render path; it injects status/procedure context as *ignorable free-text prompt* (not constructed from the packet); and its **streaming branch bypasses every post-generation safety/quality gate** (answer-shape, citation guard, `post_generation_review`; `backend/paradiso_backend.py:4745-4759`). Demoting `/api/ask` to a secondary "ask about this packet" affordance — and forcing it onto the **buffered, fully-gated** path — *improves* the safety posture.

**Reusable infra exists but is mounted only in `index.html`.** The 5 `assets/js` helpers (route guides, complex-status guide, F-4 guide, short-stay checker, HiKorea reservation helper) are loaded only in `index.html`; `ai.html` loads no external JS. The HiKorea helper (`ParadisoReservationHelper`) is a verified-safe handoff (no login/booking/payment automation) reusable from the navigator.

**Coverage-limited already works safely.** Unsupported / incomplete status+procedure pairs already return a valid packet with empty document groups and `sourceLens.overallLevel` = `limited`/`unavailable` plus a public-safe `limitationKo` — **never fabricated documents/fees/deadlines**. The frontend only needs to detect this (now exposed as `coverageSummary.isLimited`, added in this work) and render the coverage-limited state.

### Critical blockers
**None make the refactor unsafe.** Hard constraints to honor:
1. Never route the deterministic packet through streaming `/api/ask` (streaming is input-gated but output-ungated). The packet is rendered client-side from JSON; the optional AI follow-up uses the **buffered** path with `stream:false`.
2. Per-item source coverage is **section-level + per-document boolean** (`sourceLens.overallLevel` + each doc's `sourceBacked`/`sourceRefs`). The UI must render confidence at that granularity and must **not** fabricate per-document "verified" badges beyond what `sourceBacked` supports.
3. CLAUDE.md protected-file rule: wiring is renderer/resolver-side. No bulk edits to `visa_data.json` / `backend/data/visas.json` / `doc_master.json`. (This PR adds only additive, human-authored EN scaffolding + a derived coverage flag to the *builder*, not the data.)

---

## 1. Canonical status inventory

`visa_data.json` and `backend/data/visas.json` are **identical** lists of **42 records** (keyed by `code`). Parent statuses carry a `subCodes` array; sub-codes (`D-2-1`, `F-6-1`, …) live inside it and are resolved to their parent for record lookup while the exact sub-code is preserved (`procedure_packet_builder._parent_code`).

**Canonical primary statuses (37):** A-1, A-2, A-3, B-1, B-2, C-1, C-3, C-4, D-1, D-2, D-3, D-4, D-5, D-6, D-7, D-8, D-9, D-10, E-1, E-2, E-3, E-4, E-5, E-6, E-7, E-8, E-9, E-10, F-1, F-2, F-3, F-4, F-5, F-6, G-1, H-1, H-2.

**Sub-code listed at top level (1):** `D-4-1` (한국어연수) — a true `D-4` subcode that also appears as its own top-level record. **Decision: canonical subcode**, render with `parentStatusCode="D-4"`, never flattened into the parent.

**Noncanonical / program / helper records (4)** — selectable but grouped under "프로그램/시범사업" and coverage-limited-first:
- **D-4-2K** (기업맞춤형인턴십 K-Trainee) — thin `D-4` program subcode; no structured grounding → renders coverage-limited. Backend normalizes `D4-2K → D-4-2K`.
- **K-STAR** (K-STAR 비자트랙) — program record, not a numeric subcode.
- **REGION-S** (지역특화·광역형 비자 시범사업) — pilot; **no procedure marked `available`** → all packets coverage-limited.
- **YOUTH-STAY** (국내 성장 기반 외국인 청소년) — manual program; **only `statusChange`**, no `feeInfo`, no `structuredRequirementsRef` → single coverage-limited packet.

**Classification rule (per CLAUDE.md):** `*-N` numeric segments → parent/subcode logic (canonical). Uppercase-named program records and `*-T` variants → classify by actual `procedures`/data structure, never by numeric-subcode inference. No duplicates or invalid codes were found beyond the D-4-1 top-level/subcode duality (intentional in the data).

---

## 2 & 3. Procedure & packet coverage matrix (deterministic)

Generated by calling `build_available_packets_for_status(code)` for every record. **Lens** per cell: `full` = `source_confirmed`, `part` = `contextual`, `lim` = `limited`, `none` = `unavailable`, `–` = procedure not present in the record. Columns: Reg=registration, Ext=extension, Chg=status change, Grant=status grant, Work=workplace change, OutAct=activities-outside-status, Reentry=re-entry, Visa=visa issuance.

| Status | Name | Reg | Ext | Chg | Grant | Work | OutAct | Reentry | Visa | Best lens |
|---|---|---|---|---|---|---|---|---|---|---|
| B-1 | 사증면제협정 | lim | part | – | – | – | – | – | – | part |
| B-2 | 관광통과·무사증 | lim | part | – | – | – | – | – | – | part |
| C-1 | 일시취재 | lim | part | – | – | – | – | – | – | part |
| C-3 | 단기방문 | part | part | – | – | – | – | – | part | part |
| C-4 | 단기취업 | lim | lim | – | – | – | – | – | – | lim |
| A-1 | 외교 | part | lim | – | – | – | – | – | – | part |
| A-2 | 공무 | part | lim | – | – | – | – | – | – | part |
| A-3 | 협정 | part | part | – | – | – | – | – | – | part |
| D-1 | 문화예술 | full | part | – | – | – | – | part | – | full |
| D-2 | 유학 | full | full | part | – | – | part | part | part | full |
| D-3 | 기술연수 | lim | part | – | – | – | – | – | – | part |
| D-4 | 일반연수 | lim | full | lim | – | – | – | part | – | full |
| D-4-1 | 한국어연수 (대학부설어 | – | full | – | – | – | – | – | – | full |
| D-5 | 취재 | full | full | – | – | – | – | – | – | full |
| D-6 | 종교 | full | full | – | – | – | – | part | – | full |
| D-7 | 주재 | full | part | – | – | – | – | part | – | full |
| D-8 | 기업투자 | full | part | lim | – | – | – | part | – | full |
| D-9 | 무역경영 | lim | part | lim | – | – | – | part | – | part |
| D-10 | 구직 | lim | part | lim | – | – | – | – | – | part |
| E-1 | 교수 | lim | part | lim | – | – | – | – | – | part |
| E-2 | 회화지도 | full | lim | lim | – | lim | – | part | – | full |
| E-3 | 연구 | full | part | lim | – | lim | – | part | – | full |
| E-4 | 기술지도 | full | part | lim | – | lim | – | part | – | full |
| E-5 | 전문직업 | full | part | lim | – | lim | – | part | – | full |
| E-6 | 예술흥행 | full | part | lim | – | lim | lim | part | – | full |
| E-7 | 특정활동 | full | full | – | – | lim | – | – | – | full |
| E-8 | 계절근로 | – | part | – | – | – | – | – | – | part |
| E-9 | 비전문취업 | lim | part | – | – | lim | – | – | – | part |
| E-10 | 선원취업 | full | lim | – | – | – | – | – | – | full |
| F-1 | 방문동거 | lim | lim | lim | lim | – | – | – | – | lim |
| F-2 | 거주 | lim | lim | lim | – | – | – | – | – | lim |
| F-3 | 동반 | lim | lim | lim | lim | – | lim | part | – | part |
| F-4 | 재외동포 | lim | part | lim | – | – | – | – | – | part |
| F-5 | 영주 | lim | part | – | – | – | – | – | – | part |
| F-6 | 결혼이민 | part | part | lim | lim | – | – | lim | part | part |
| G-1 | 기타(난민등) | lim | part | lim | – | – | – | – | – | part |
| H-1 | 관광취업 | part | lim | – | – | – | – | part | – | part |
| H-2 | 방문취업 (신규발급 중 | lim | lim | – | – | lim | – | – | – | lim |
| D-4-2K | 기업맞춤형인턴십(K-T | part | full | – | – | – | – | – | – | full |
| K-STAR | K-STAR 비자트랙 | – | part | part | – | – | – | lim | part | part |
| REGION-S | 지역특화·광역형 비자  | – | – | – | – | – | – | – | – | none |
| YOUTH-STAY | 국내 성장 기반 외국인 | – | – | lim | – | – | – | – | – | lim |

**Distribution across all generated packets:** 20 `source_confirmed`, 51 `contextual`, 59 `limited`. **36 of 42 statuses** have at least one `contextual`+ packet; **every** status yields at least one safe packet state (only `REGION-S` is all-coverage-limited, which is itself a safe state). **No status produces a blank result or crash.**

**Packet schema → 12 Action Packet sections** (verbatim top-level keys from `build_procedure_packet`):
`packetId, packetType, statusCode, exactStatusCode, parentStatusCode, titleKo, titleEn, userScenarioSummaryKo, applicability{summaryKo,conditions,limitations}, timing{sourceBacked,limitationKo,triggerEventKo,stayPeriodHintKo}, documents{commonDocs,requiredDocs,conditionalDocs,additionalDocs,sourceBacked,limitationKo}, fees{items[],sourceBacked,limitationKo}, channels{immigrationOfficeVisit,hikoreaReservation,limitationKo}, officeAndJurisdiction{summaryKo,limitationKo}, riskFlags[], sourceLens{overallLevel,overallLabelKo,sources[],finalAgencyDiscretionKo}, coverageSummary{level,isLimited,hasDocuments} (added this PR), applicationTypingHelper, nextActions[], finalAgencyNoteKo, version`.

Each document carries `nameKo, sourceBacked, sourceRefs[{sourceFamily,sourceNameKo,evidenceLevel,versionDate,pageRange,article}], isOfficialForm, conditionKo?, noteKo?` — giving **per-item source coverage** for Phase 7.

**KO/EN gap:** the packet is **Korean-primary** (only `titleEn` exists; ~99 `*Ko` keys vs 2 `*En`). EN parity is therefore delivered as **navigator chrome (frontend i18n) + official Korean administrative terms shown as-is**, plus additive human-authored EN labels in the builder (`SOURCE_LENS_LABELS_EN`, `FINAL_AGENCY_NOTE_EN`, `titleEn` on the unknown packet) — never machine-translation of legal content.

---

## 4. UI inventory (`ai.html`)

Single self-contained file (3308 lines): one `<style>` (26–1253), HTML body (1255–1450), one inline `<script>` (1452–3306). **No external JS includes.** Backend base `DEFAULT_API_BASE` (1459), overridable via `window.PARADISO_BACKEND_URL`.

- **Chat-first DOM:** `<main id="chatHistory" class="chat-history" aria-live="polite">` (1284) with `#welcomeMessage` (1286–1299) and 4 example chips `.ai-welcome-chip` (1292–1295); input footer `.chat-input-area` (1304–1327) with `#aiQ` textarea + `#sendBtn onclick="sendAi()"` + `#charCount`.
- **Model-tier UI:** `#aiModeSelector` (1305–1318), three `.ai-mode-btn` — `⚡ Fast` / `⚖️ Basic`(default) / `💎 Pro`("서비스 예정", disabled). `currentAiAnswerMode` (3205) → sent as `answer_mode` in `/api/ask`.
- **Quota merchandising:** `.quota-badge` + `#quotaCount` (1279), `QUOTA_LIMIT=30`/day, localStorage `paradiso_ai_quota`. **Backend has no quota field — this is pure client-side fiction.**
- **Submit path:** `sendAi()` (3051–3199) → `POST /api/ask` (3097) with `{question,consent,context,lang,visa_code,selected_procedure_key,answer_mode,stream,...}`. Streaming sets `provider:'openrouter'`.
- **Source/grounding:** global `.grounding-badge` (`grounded` modifier) + `.source-panel`; provider/model labels (`OpenRouter · <model>`) via `getModelLabel()` (2050). Raw developer fields dumped only when `localStorage['paradisoDevDiagnostics']==='1'` (2554–2575).
- **Inert structured template:** `<template id="pa-answer-card-shell">` (1339–1429) — an 11-slot card already styled but never cloned.
- **Locale:** per-message `detectUserLang()` + `?lang=` param + inline `t(lang,ko,en)`; **no persistent toggle**, does not read `paradiso:language`.
- **"AI 도우미" framing:** `<title>` (6) and H1 (1268) = "Waymaker by Paradiso — 비자·체류 정보 AI 도우미"; welcome (1288) "참고용 도우미".

### 4b. Entry points
- **Homepage (`new-home.html`)**: Waymaker block 496–505, `#waymakerCta href="ai.html?domain=nationality"`; `waymaker.note` explicitly says "기존 Paradiso AI 도우미와 동일한 엔진". Hero CTAs (439–453) are in-page wizards, **not** Waymaker — the spec's "내 절차 찾기 / Find my immigration procedure" CTA must be added/repositioned here. Copy lives in `data/nationality_content.json` via `data-c` attributes.
- **`index.html`**: 4 `ai.html` links (gateway card 13004, hero AI link 13092, floating FAB 14102, planned 1345 tool 13382). The FAB is the only one passing context (`?visa_code=&selected_procedure_key=&…`).

---

## 5. Mobile UX inventory

- **Breakpoints:** 5 scattered max-width blocks (768, 640, 480×3, a 480 mislabeled "390"); **no 430px** breakpoint though Playwright has a `mobile-430` project. Tokens exist: `--btn-h-lg=48px`, `--sp-*`, `--btn-r-*`, `--btn-tr`.
- **Posture:** at ≤768px `body` flips to `display:block; overflow-y:auto` and `.chat-history` becomes `flex:none; overflow:visible` — so the **composer is NOT pinned on mobile** (scrolls away). `.chat-history{width:100vw;max-width:100vw}` + `.msg-row{width:calc(100vw-…)}` use `100vw` (ignores scrollbar/safe-area → sub-pixel horizontal scroll risk). `.msg-bubble{word-break:break-all}` breaks Latin mid-word.
- **Touch targets <44px:** `.ai-welcome-chip` 36px→32px@480, `.bdg` 28px, `.source-chip` 24px, `.pa-topic-chip` 28px, `.grounding-badge`/`.context-pill` 30px, `.pa-next-action-btn` 38px.
- **Safe-area:** only `safe-area-inset-bottom` on the composer; no `inset-top/left/right`; verify `viewport-fit=cover`.
- **Themes:** `civic_editorial` (dark, default) and `archive_diary` (light paper) via `html[data-editorial-theme]` (inherited from `localStorage['paradiso:editorial-theme']`; no in-page toggle in ai.html). **Low-contrast risk:** `.source-chip` (1073) and `.pa-topic-chip` (742) have **no `archive_diary` override** → mint-on-near-white WCAG fail on the light theme.
- **Reduced-motion:** two partial blocks; do not neutralize `msgIn`, `typingBounce`, hover `translateY`. Needs a blanket override.

> **Implication for the navigator:** ship it as a self-contained, mobile-first, single-column module with its own scoped CSS (`assets/css/waymaker-navigator.css`) that inherits the theme variables, defines explicit 360/390/430/768 behavior, guarantees ≥44px targets, pins a safe-area-aware bottom action bar, provides archive_diary chip contrast, and respects reduced-motion — rather than retrofitting the squeezed chat grid.

---

## 6. Backend & safety inventory

- **`/api/ask` request (`AskRequest` 357–386):** `question, consent, context, lang, visa_code, visa_data, selected_procedure_key, selected_procedure_variant_id, model, answer_mode, stream`. Status/procedure context is **client-supplied** and injected as weak, override-able prompt text — never constructs the answer from the packet.
- **Response (`AskResponse` 389–619):** global `grounding_used`/`grounding_sources`, large law-grounding/citation-guard/evidence blocks, model/provider fields (real OpenRouter model ids surfaced intentionally), safety fields. **No quota field anywhere.**
- **Streaming bypasses output gates** (answer-shape repair, citation guard, confidence gate) — returns early at 4745–4759. Pre-generation safety (`_evaluate_request_safety` 4207) still applies. **Mitigation: Waymaker AI follow-up forces `stream:false` (buffered, fully-gated).**
- **No-LLM safe path:** `provider:"none"` → `503 no_llm_provider_configured`.
- **Item-level coverage:** absent on `/api/ask` (global only) but **present in the packet** (`sourceLens` + per-doc `sourceBacked`/`sourceRefs`) — the navigator consumes the packet's per-item coverage.

### 6b. Reusable helper inventory
All 5 helpers are vanilla IIFE globals under `assets/js/`, deterministic, no LLM, wired only in `index.html`:
- **`ParadisoReservationHelper`** (`hikorea-reservation-helper.js`): `open({visaCode,taskType})`, `reset()`, pure `computeReservationPath(input)` → `{recommendedPurpose, beforeBookingChecklist, afterBookingChecklist, hikoreaClickSteps, warnings, blockedCaseTips}`, `suggestionsFor(code)`. Renders into `#hikoreaGuideBody`/`#hikoreaGuideOverlay` (index.html), reuses index.html `openModal/closeModal`. **No login/booking/payment automation.** The navigator reuses its **pure** functions for HiKorea step guidance.
- **`ParadisoRoute` / complex-status / F-4 / short-stay guides:** config-driven intake flows that already emit snake-case procedure keys matching `PACKET_TYPE_BY_PROCEDURE_KEY` — vocabulary reused, not duplicated.

---

## 7. Test & validation harness inventory

- **Node/browser checks:** dozens of `scripts/check_*.mjs` / `check_*.js` run as plain Node scripts (assert-style; some jsdom). Playwright config `playwright.config.mjs` defines projects incl. `mobile-430`. `tests/e2e/`.
- **Backend:** `unittest`-style under `backend/tests/`, run via `python3 -m unittest` (or pytest). `check_repo.sh` bootstraps a `.venv-check` with FastAPI/httpx/pydantic and runs `test_paradiso_backend.py` + `test_e7_workplace_change_law_grounding.py` + offline `py_compile` of `backend/services/*.py`. **Note:** `test_procedure_packet_builder.py` is **not** in the CI gate today — it should be added now that the builder is load-bearing.
- **Recommended new tests:** (a) `tests/test_waymaker_navigator.mjs` — node tests of the adapter/coverage/checklist/all-status logic against the real `visa_data.json`; (b) backend `test_procedure_packet_builder.py` additions for `coverageSummary` + EN labels + no-fabrication invariants; (c) responsive snapshots at 360/390/430/768; (d) i18n KO/EN parity for the navigator STRINGS.

### 12pre. i18n & copy inventory
Three independent i18n mechanisms (no shared loader): `index.html` `tx()` over `data/i18n/{ko,en,zh-CN}.json` (key `paradiso:language`); `new-home.html` `data-c` dotted-path over `data/nationality_content.json` (same key); `ai.html` per-message `detectUserLang()` + inline literals (no persistence). **EN-mode Korean a11y labels still present in `new-home.html`:** theme toggle `aria-label="테마 전환"` (433), brightness `aria-label="밝기 전환"` (434), close-modal `aria-label="닫기"` (534/546/558) — not swapped on `lang==='en'`.

---

## Decisions & deferrals (carried into implementation)
- **Status classification:** D-4-1 canonical subcode; D-4-2K/K-STAR/REGION-S/YOUTH-STAY noncanonical programs (selectable, coverage-limited-first). All 42 remain selectable; none excluded.
- **EN parity:** chrome via frontend i18n + official KO terms shown as-is; bounded additive EN labels in the builder. Full per-status EN packet prose is **deferred** (would require human-authored translation of legal content — out of safety scope).
- **HiKorea:** reuse `ParadisoReservationHelper` pure logic for step guidance + official link + `tel:1345`; per-procedure deep-link URLs do not exist in HiKorea and are **not fabricated**.
- **Streaming output-gate gap** in the legacy chat is mitigated for Waymaker (follow-up forces buffered path); a broader backend streaming-gate fix is a **recommended follow-up PR**.
- **Add `test_procedure_packet_builder.py` + the new navigator tests to `check_repo.sh`.**

*End of Phase 0 report.*
