# Search result unification audit — 2026-09-23

Sprint: search result reliability · search UX/UI unification · Waymaker integration · legacy FOUC elimination.
Base: `main` @ `f39ff0d` (Stabilize Visable landing, redesign journeys, and expand Form Helper, #634).

## 0. About the reference PDF

The reference PDF `D2검색했을때이렇게나왔음.pdf` was **not available** in this session: it was not
attached to the container and a Google Drive search for its title returned nothing. The failure
classes listed in the sprint brief (sections 4–18) were therefore used as the bug report, and every
class was reproduced against HEAD on a local static server (`python3 -m http.server`, `/api/*`
aborted — the production backend and `visable-mu.vercel.app` are blocked by this session's egress
policy; production assets were compared through the Vercel connector instead, see §4).

Reproduction: search `D-2`, then `D-2 연장`, at 1280 / 390 / 320 px.
`D-2 연장` at 390 px on HEAD is **9,440 px** tall (≈ 11 phone screens); `D-2` is 6,991 px.

## 1. Component map (HEAD, before any edit)

Order is the vertical order inside `#mainContent` after a search. "Backend" = only renders when
`/api/search/unified` answers (production); it is absent in the local reproduction but its code
path was read.

| # | Visual block (as seen) | Source file | Renderer | Data source | Current / legacy | Duplicate of | Decision |
|---|---|---|---|---|---|---|---|
| 1 | Searched header: wordmark, query box, `KO` button | `index.html` `#hero` (legacy header) restyled by `assets/css/civic-search.css` | static HTML + `mountSearchedLangButton()` in `civic-search.js` | — | legacy DOM, current style | — | **Keep**, tighten |
| 2 | "통합 검색을 불러오지 못했습니다…" note under the box | `assets/js/unified-search.js` `setSearchBarState('error')` | `#usSearchNote` | `/api/search/unified` failure | legacy (backend layer) | — | **Remove** in civic mode (the layer it refers to is gated) |
| 3 | Green "본 서비스는 공개 법령·매뉴얼 기반 참고용…" box | `index.html:14560` `.reference-disclaimer` | static | — | legacy | caution also carried by `.sg-disclaimer` + footer | **Gate**: hidden in civic searched state unless guidance failed; its "not legal advice / not an agency" clause is added to the guidance disclaimer so nothing is weakened |
| 4 | "D-2 · 체류기간 연장(으)로 이해했어요 · 수정" | `assets/js/status-guidance.js` `renderInterpretation` | `#statusGuidance .sg-interp` | `data/status-guidance-202609.json` + `search-router.js` | current | #10 | **Keep** — becomes the single interpretation surface; wording by match type |
| 5 | "D-2에서 무엇을 하려고 하세요?" 12 stacked option buttons (bare `D-2`) | `status-guidance.js` `renderQuestion` | `.sg-question` | bundle `codes[].procedures` | current | — | **Keep**, compact 2-column chips |
| 6 | Answer: kicker, `D-2 유학`, "현재 정보로는 D-2 안내와 가장 가까워 보여요.", summary, facts, conditions, notes | `status-guidance.js` `renderAnswer` | `.sg-answer` | bundle `guidance[]` | current | — | **Keep**; definitive wording for exact code; conditions/notes move to their own section after fees |
| 7 | "일부 대상자에게 적용되는 별도 제도: 광역형 비자 시범사업" | `renderPrograms` | `.sg-related-programs` | bundle `programs` | current | — | Keep |
| 8 | 준비할 서류: one row per document, each with its own details and the repeated "공식 안내에 제출 형태가 따로 적혀 있지 않아요…" paragraph | `renderDocuments` / `renderDocItem` | `.sg-docs` | bundle `guidance[].documents` | current | per-row fallback repeated N times + section note | **Keep**, redesign rows (compact label, one section note, issuer/role inline, source in details), group labels 필수 / 조건부 / 해당자만 / 대체 가능 / 생략 가능 / 추가 요청 가능 |
| 9 | 비용 / 납부 with **two** refund sentences ("…반환되지 않습니다." + "…반환되지 않아요.") | `renderFees` | `.sg-fee` | bundle `fees[].notes_ko` (**data**) + `STR.feeNonRefundable` (**renderer**) | current | itself | **Keep**, dedupe at render: one semantic note (see §4) |
| 10 | 공통으로 확인할 것: 7–9 expandable rules (3-month validity, apostille, sealed medical certificates, …) | `renderOverlays` / `applicableOverlays` | `.sg-overlays` | bundle `overlays[]` | current | — | **Keep**, classify CRITICAL / CONTEXTUAL / REFERENCE; only triggered rules visible, rest behind one disclosure |
| 11 | 관할 관서 정보 (national baseline paragraph + office select + report link) | `renderLocal` | `.sg-local` | `data/local-practice-202609.json` | current | — | Keep, **collapsed** by default (open when an office is chosen) |
| 12 | 다음 할 일 (reservation, form, 1345, legacy card, follow-up) | `renderNext` | `.sg-next` | — | current | — | Keep, compact; legacy-card link stays as the deliberate gate for #16 |
| 13 | 공식 근거 N건 (collapsed) | `renderEvidence` | `.sg-evidence` | bundle `sources`, `law_sources` | current | #15 overlaps | Keep; human titles only; one review notice instead of one per row |
| 14 | 이 체류자격의 다른 절차 chips | `renderRelated` | `.sg-related` | bundle `codes[].procedures` | current | — | Keep (compact links) |
| 15 | Tabs 전체 / 체류자격 안내 / 원문 + "관련 공식 원문" raw manual hits (3 passages expanded, 91 hits for `D-2`; top hit for `D-2 연장` is p.173 "유학(D-2), 구직(D-10) ➠ 교수(E-1)자격으로의 변경") | `assets/js/civic-search.js` `renderTabs` / `renderResults` + `assets/js/manual-corpus-search.js` `search` | `#civicResultTabs`, `#civicManualResults` | `data/manual-corpus/*.json` | current, but a **second result system** | #13 | **Move** under the answer as one collapsed "관련 원문" disclosure; tabs removed; intent-aware ranking (§3) |
| 16 | Legacy status card: `D-2 유학 세부 8 Study Abroad`, badges "체류민원" "2026.6 매뉴얼 확인 필요", 기본/쉬운/공식 근거 pills, 사증발급 / 변경 / 연장 / 등록 / 자격외활동 / 재입국 / 시간제취업 tabs, "2026-05 체류민원 안내매뉴얼 기준" | `index.html` `renderResults()` (l.22851) → `#rlist article.vc` + the 2026-05 shims | `#rlist` | `visa_data.json` (`dataDate: "2026-05 체류민원 안내매뉴얼 기준"`, protected) | **legacy** | #6 #8 #9 #14 | **Gate** out of normal rendering; reachable only through "기존 체류자격 카드 보기"; shown automatically only if the guidance layer fails |
| 17 | "이렇게 이해했어요" interpretation strip + AI overview slot + source list + "AI 보조 안내 보기" button (**backend**) | `assets/js/unified-search.js` `buildUnifiedLayerHtml` | `#unifiedSearchLayer` (mounted **after** `#rlist` in civic mode) | `/api/search/unified` | **legacy** | #4 #13 | **Gate**: not fetched or rendered in civic mode (URL sync kept) |
| 18 | Waymaker Quick Answer (question-shaped queries only) | `assets/js/waymaker-quick-answer.js` | `.sg-quick` inside `#statusGuidance` | bundle | current | — | Keep as the primary answer for questions |
| 19 | Waymaker Navigator | `assets/js/waymaker-navigator.js` | only on `ai.html` | — | current | — | Not rendered on the result page (confirmed: not loaded by `index.html`) |
| 20 | Guidance disclaimer + "안내 기준 보기" | `renderDisclaimer` | `.sg-disclaimer` | — | current | #3 | Keep, extended with #3's clause |
| 21 | Footer disclaimer | `index.html` `.p-footer` | static | — | current | — | Keep |

Result systems rendering at once for `D-2 연장` in production: **4 full systems** (#4–#14 status
guidance, #15 raw manual search, #16 legacy status card, #17 unified backend layer) plus two
disclaimers (#3, #20/#21). Waymaker Navigator (#19) is not on this page; Quick Answer (#18) only
appears for question-shaped queries.

### Internal identifiers

`stay_manual_2026_09_18_pdf` / `visa_manual_2026_09_01_pdf` are corpus source ids. In HEAD they are
used as `data-sg-source` attributes and as lookup keys; the visible labels come from
`title_ko`/`title_en`. They reach visible text only when a title is missing (the evidence meta line
concatenates `ev.title_ko` without a fallback) — a regression test now asserts that no visible text
in the result contains `_pdf` or `stay_manual_` / `visa_manual_`.

### Source dates visible after a `D-2` search (HEAD)

| Where | Text | Verdict |
|---|---|---|
| #15 header | 기준일 사증 2026.09.01 · 체류 2026.09.18 | current |
| #13 evidence | 최신 기준일 2026-09-18, per-row 2026-09-18 | current |
| #20 details | 사증 2026-09-01판, 체류 2026-09-18판, 법령 2026-09-22 확인 | current |
| #16 badge | **2026.6 매뉴얼 확인 필요** | stale (legacy) |
| #16 body | **2026-05 체류민원 안내매뉴얼 기준** (`visa_data.json` `dataDate`) | stale (legacy, protected data) |

Resolution: #16 is gated, so the default result carries one source state (September 2026). The
protected `visa_data.json` value is not edited.

## 2. FOUC / legacy flash — findings

See §6 for method and evidence. Summary of the root cause: the landing first paint is clean; the
flash is the **searched state**. `index.html` `renderResults()` paints the legacy `#rlist` card
synchronously on submit, while `#statusGuidance` only renders after `fetch('data/status-guidance-202609.json')`
resolves. For ~300–700 ms (throttled) the only content under the header is the legacy card plus the
legacy disclaimer box. A `?q=` URL (which `unified-search.js` pushes after every search, so every
reload of a result hits it) additionally shows the landing until `initUI()` runs after the data load,
then jumps to that same legacy-first state.


## 3. What changed (implementation)

### 3.1 One result system

| System | Before | After | Mechanism |
|---|---|---|---|
| Status guidance `#statusGuidance` | one of four | **the** result renderer, always first in `#mainContent` | `status-guidance.js` `ensureHost()` prepends it |
| Raw manual search (tabs + 3 expanded passages) | second system, above the legacy card | collapsed "관련 원문 N건" disclosure **inside 공식 근거** (or right after the guidance when a result has no evidence section); tabs removed | `civic-search.js` `#civicRawSources` + `#sgRawSlot` |
| Legacy status card `#rlist` | third system, fully expanded | **gated**: not displayed in the civic searched state; opens only via "기존 체류자격 카드 보기" (`data-legacy-card="open"`), or automatically if the guidance bundle fails to load (`data-sg-state="failed"`) | critical inline CSS in `<head>` |
| Backend unified layer `#unifiedSearchLayer` ("이렇게 이해했어요", AI slot, source list) | fourth system (production only) | **not fetched, not rendered** in civic mode; URL sync kept | `unified-search.js` `civicOwnsResults()` + critical CSS |
| Legacy caution band `.reference-disclaimer` | always above results | hidden in the searched state unless guidance failed; its "법률 상담이나 민원 대행이 아님" clause moved into the guidance disclaimer (ko/en) | critical CSS + `STR.disclaimer` |
| "통합 검색을 불러오지 못했습니다" note | under the query box | gone (the layer it described no longer runs here) | critical CSS + idle state |

### 3.2 Canonical result structure

`A` interpretation → `B/C` answer (title, definitive lead, summary, facts, **one primary action**
"준비 서류 N개 보기" + 방문예약 안내) → `D` documents → `E` fees → `F` 조건과 예외 (rule conditions,
notes, special cases, triggered common rules, "그 밖의 공통 규칙 N개") → `G` 관할 관서 정보
(collapsed until an office is chosen) → `H` 다음 할 일 (one quiet row) → `I` Waymaker resolver
(only for results that need more context) → `J` 공식 근거 N건 · 근거 보기 (collapsed; raw passages
inside) → `K` 관련 절차 → disclaimer.

### 3.3 Interpretation wording by match type (`matchKind`)

| Match | Example | Wording |
|---|---|---|
| EXACT_CODE | `D-2`, `D-2 연장` | `D-2 유학 · 체류기간 연장` (no hedge); answer lead "D-2 기준으로 안내해요." |
| CONFIRMED | user picked the status / procedure | same, definitive |
| EXACT_PROCEDURE | `외국인등록증 재발급` (the procedure's own name) | `외국인등록증 재발급` |
| NATURAL_HIGH | `ARC 잃어버렸어` | "외국인등록증 재발급(으)로 이해했어요" |
| AMBIGUOUS | alias / partial reading | "…(으)로 이해했어요" + "해석이 확실하지 않아요" when LOW; the answer lead may say "가장 가까워 보여요" only here |

### 3.4 Evidence query ≠ answer query; relevance

`status-guidance.js` publishes an **evidence intent** with every render
(`visable:guidance-rendered` → `detail.evidenceIntent`): resolved status, procedure, the status
chapter page range in each manual (`bundle.chapters`), the pages the structured answer cites
(anchors) and the procedure's domain. `manual-corpus-search.js` `search(index, query, { intent })`
then qualifies pages by status (code on page **or** inside the status chapter) and procedure
vocabulary (or an anchor page), and scores: chapter +30, cited page +60 (±1 page +12), own-procedure
vocabulary up to +32 (+18 in the heading), exact subcode on the page +25 / in the heading +15;
penalties: another procedure dominating the page up to −30, an "A ➠ B" transition page −25 when
the intent is not a status change, a heading naming another status family −15, a different domain
(visa manual for a stay procedure) −25. Nothing is hard-coded to D-2.

| Query | Top raw hit before | Top 3 after |
|---|---|---|
| D-2 연장 | p.173 "유학(D-2), 구직(D-10) ➠ 교수(E-1)자격으로의 변경" | p.43 (D-2 연장허가), p.42, p.44 |
| D-2 | p.35 tied with p.173 / p.210 transition pages | p.35 / visa p.62 chapter openings; no ➠ heading in top 5 |
| F-6 연장 | p.503, visa p.327 | stay p.498–502 (F-6 제출서류) |
| E-7-4 (status only) | — | p.294 "숙련기능 점수제 종사자 (E-7-4)", p.298, p.300 |
| D-2 아르바이트 | — | p.39, p.40, p.38 (시간제취업) |

### 3.5 Documents

Group labels: 필수 · 조건부 · 해당자만 · **대체 가능** (ALTERNATIVE_DOCUMENT now has its own group) ·
생략 가능 (행정정보 공동이용 / 이미 제출) · 추가 요청 가능. Each row shows the name, the submission
form as a small tag (solid = official wording, dashed = preparation advice), and on a second small
line the condition, who prepares it and the issuer. Source page, validity and notes sit behind the
row's disclosure. The per-row paragraph "공식 안내에 제출 형태가 따로 적혀 있지 않아요…" is gone; the
one section note explains the dashed tag once. Official-explicit forms (원본, 사본, 원본 + 사본,
원본 제출 · 반환되지 않음) are unchanged.

### 3.6 Fee duplication — root cause and fix

Origin: **data + renderer**. `bundle.fees[extension_general].notes_ko` carries
"심사수수료이므로 접수 후 반환되지 않습니다." and `renderFees` appended its own
`STR.feeNonRefundable` "…반환되지 않아요." for every fee with an amount. English had the same pair
("…once the application is accepted." / "…once accepted."). Fix at the composition layer: every
note line of the fee section goes through one list with `sameNote()` (normalised key without
register endings; word-subset; character-bigram similarity ≥ 0.85). Data untouched.
`check_search_result_unification.mjs` asserts every fee row's refund note collapses with the
renderer note in ko and en, and that no fee section in the matrix has semantically duplicate lines.

### 3.7 Common rules

`tierOverlays()` (renderer only; rule text unchanged): **critical** = presence in Korea, passport
caps the period, rules tied to a listed document (신원보증서 4-year cap); **contextual** = triggered
by the document list (sealed medical documents only when a medical certificate / drug test is
listed, apostille when a document needs it, 3-month validity when a domestic certificate is listed,
administrative data sharing when a document is exemptable) or scoped to the status family (job /
income report for work statuses); **reference** = everything else, behind "그 밖의 공통 규칙 N개".
D-2 extension (verified): 2 critical (presence in Korea, passport cap) + 1 contextual (3-month
validity of domestic certificates) visible; 6 in the disclosure (previously submitted documents,
apostille, administrative data sharing, sealed medical documents, school-age enrolment, TB
certificate).

### 3.8 Waymaker role

| Surface | Where it renders now |
|---|---|
| Quick Answer | primary answer for question-shaped queries (unchanged ownership; full guidance behind "전체 안내") |
| Navigator | ai.html only (never loaded by index.html) |
| AI follow-up | one link in 다음 할 일 for exact results |
| Waymaker resolver block | once, after the answer, only for `unresolved`, `need-status`, `no-status`, `source-only` |
| Legacy "AI 보조 안내 보기" button + backend AI overview | removed from the civic result page (unified layer gated) |

Never more than one large Waymaker surface on a page.

### 3.9 Locales and RTL

The structured guidance exists in ko and en. Before, every locale other than `en` got Korean
(including Arabic, rendered right-to-left with misplaced punctuation). Now Korean readers get
Korean and every other locale gets English; the guidance block carries `lang` and, on an RTL page,
`dir="ltr"` (the page chrome stays RTL). RTL-only guidance rules are scoped to RTL content. The one
new civic string (`rawTitle`) is in all 14 packs. Quick Answer: "준비할 서류: … 외 N개." replaces the
ungrammatical "…등 N개이에요."

## 4. FOUC — method, root cause, fix, evidence

Method: CDP `Page.startScreencast` (every painted frame) and a per-frame rAF probe, cold cache,
throttled (100–300 ms RTT, 2–4 Mbps), Chromium headless at 390×844. Production assets were
compared through the Vercel connector: `civic-search.js` on production equals HEAD,
`cache-control: public, max-age=0, must-revalidate`, weak ETag, no service worker registered
anywhere in the repo. **No evidence that stale caching contributes.** WebKit is not installed in
this container (only Chromium); the CI `mobile_webkit_qa.mjs` job covers WebKit.

Findings:

1. Landing, cold cache, throttled: frames = blank → civic shell. JS disabled: only the civic shell
   is visible (no legacy element anywhere). The landing is clean.
2. **Search** (frame capture `f004_371ms`): searched header + legacy caution band + "안내를
   불러오는 중이에요" + tab bar + "공식 원문을 불러오는 중" + **the fading-in legacy D-2 card**
   (pills "체류민원", "2026.6 매뉴얼 확인 필요", 기본/쉬운/공식 근거). This is the old design the owner
   sees for ~0.2 s: `renderResults()` paints `#rlist` synchronously; the guidance paints only after
   its JSON fetch.
3. **Result URL** (`?q=`, pushed after every search): the landing is painted until `initUI()` runs
   after the 1.4 MB document and the data load, then the page jumps to state 2.

Fix (no timers, no opacity, no body hiding):

- `<head>` critical CSS: in the searched state `#rlist`, `#unifiedSearchLayer`, `#usSearchNote` and
  the legacy band cannot be displayed unless explicitly requested / guidance failed; until
  `data-sg-state="ready"` a neutral skeleton (`#mainContent::before`) holds the space.
- An inline script at the top of `<body>` puts a `?q=` URL into the searched state before the first
  frame and prefills `#q`; `status-guidance.js` starts from it on load and re-renders (not restarts)
  when `initUI()` later announces the same query.

Evidence: `tests/e2e/search-result-unification.spec.mjs` → "no legacy frame" samples every
painted frame from submit to ready under 250 ms / 2 Mbps with cache disabled, and every frame of a
`?q=D-2` load under 200 ms / 4 Mbps: zero frames with the legacy card, band or backend layer, zero
landing frames on a result URL (desktop-1280, mobile-390, mobile-320). The existing
`landing-boot.spec.mjs` frame probe still passes.

## 5. Density (390×844, Chromium, local)

| Query | Before (px) | After (px) | First screen after |
|---|---|---|---|
| D-2 | 6,991 | 1,269 | interpretation, compact procedure picker |
| D-2 연장 | 9,440 | ≈3,700 (evidence closed; 5,781 with evidence and raw passages open) | interpretation, answer, facts, "준비 서류 7개 보기" + 방문예약 |
| F-6 연장 | 7,851 | 1,008 | subtype question |
| 외국인등록증 재발급 | 8,988 | 3,153 | procedure answer |
| D-2 연장하려면 뭐 필요해? | 2,015 | 1,212 | Waymaker Quick Answer |

Nothing was deleted: the removed height is the legacy card, the raw passages (now one click inside
공식 근거), the untriggered common rules and the office picker (both one click away).

## 6. Screenshots

`docs/design/screenshots/search-unification-20260923/{before,after}/` — `*-viewport.png` (first
screen) and `*-full.jpg` (full page): D-2 desktop / 390 / 320, D-2 연장 390 / desktop, F-6 연장,
외국인등록증 재발급, Quick Answer, Arabic, English; `after/evidence-expanded-390.png`.

## 7. Known limitations (needs follow-up / manual review)

- The reference PDF itself was not available; the mapping is against the brief's failure list and
  a local reproduction. The production backend layer (#17) was read from code, not observed live.
- Production and the Railway backend are unreachable from this session (egress policy); the FOUC
  root cause is established on a local server with production-identical assets.
- WebKit frames were not captured locally (no WebKit binary); CI's WebKit job still runs.
- `visa_data.json` (protected) still carries `dataDate: "2026-05 체류민원 안내매뉴얼 기준"`; it only
  shows inside the legacy card, which is now opt-in. Not edited by design.
- Structured guidance exists in ko/en only; the other 13 locales read English guidance (was Korean).
- The raw-passage corpus is page-level OCR; ranking is better but a page can still mix sections.

## 8. Validation run for this change

- `bash scripts/check_repo.sh` — pass (includes the new `check_search_result_unification.mjs`, 38 checks).
- `npm run test:status-guidance` (manifest, documents, resolver, router, physical form, fees, local practice, Quick Answer) — pass.
- `npm run test:i18n` — pass.
- Playwright, Chromium: landing-utilities, post-search-guidance, landing-boot, procedure-first-search,
  waymaker-quick-answer, language-control, search-result-unification, form-helper on
  desktop-1280 / tablet-768 / mobile-390 / mobile-320 — 336 passed; re-run after the last edits
  (all but form-helper, 1280/390/320) — 219 passed.
- `scripts/mobile_render_qa.mjs` (puppeteer-core, local Chromium) — 0 failures.
- Not run locally: `scripts/mobile_webkit_qa.mjs` (no WebKit binary in this container; runs in CI).
