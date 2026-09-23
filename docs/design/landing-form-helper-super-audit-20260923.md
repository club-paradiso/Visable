# Landing reliability · journey UI · Form Helper 2.0 · Waymaker / New Home discoverability · document submission-form — super audit (2026-09-23)

Measured on the committed tree at `33c1293` (main, PR #633) served statically
(`python3 -m http.server 4173`) with `/api/*` aborted, which is also the production
fallback when the Railway backend is unreachable. Browser: the pre-installed
Chromium 1194 (Playwright 1.61). WebKit could not be installed in the build
sandbox (Playwright CDN blocked), so WebKit evidence in this sprint comes from the
CI job `mobile-webkit-qa` only. External CDNs (jsdelivr → Pretendard, Google
Fonts) are also blocked here, so screenshots use fallback fonts; layout structure
is unaffected.

Before screenshots: `docs/design/screenshots/landing-form-helper-20260923/before/`
(captured by `scripts/qa/capture_before_20260923.mjs`). First-paint probe:
`scripts/qa/fouc_probe_20260923.mjs`.

Severity scale used throughout — **P0** incorrect immigration/document output,
data corruption, incorrect PDF output, loss of user-entered form data ·
**P1** legacy-UI flash, broken journey toggle, blocked Waymaker/New Home entry,
incorrect document submission-form guidance, broken form generation, mobile
blocker · **P2** weak hierarchy, visual inconsistency, discoverability,
unnecessary friction · **P3** minor polish.

---

## 1. FIRST PAINT / BOOT ARCHITECTURE

`index.html` (26,281 lines, 1.43 MB) is a single document:

| Order | What the parser meets | Effect on first paint |
| --- | --- | --- |
| `<head>` L7–14225 | theme bootstrap script (`paradiso:editorial-theme` → `<html data-theme>`), Pretendard + Google Fonts `<link>`s (render-blocking), ~14,000 lines of inline CSS, then `visable-product-2026.css`, `civic-search.css`, `status-guidance.css` | all stylesheets are present at first paint |
| `<body class="landing product-visable">` L14227 | brightness bootstrap script; skip link; `.k-grain`; reminder banner; `#topCtrls`; global settings overlay | painted (legacy chrome) |
| `<header id="hero">` L14330–14565 | legacy hero: `.k-decor` stickers, `.k-masthead`, wordmark + stamp, `.p-hero-copy`, `.p-gateway` (search pill, "무엇을 도와드릴까요?", 3 primary cards, Enforcement + New Home banners, 8 utility buttons), `#visaManualSection` (legacy track selector), `#searchForm` (`display:none`), disclaimer, kinetic strip | **painted as the page** |
| `<main id="mainContent">` L14567 | landing-scroll sections (brand hero, doc composer, manual section, pathway, reminder …), results area | painted below the hero |
| L15748 `document-help.js` (sync) | injects the mobile authority / hardening stylesheets at parse time | async CSS, arrives later on phones |
| L24088 inline `DOMContentLoaded` | `await loadI18nTranslations()` → `applyLanguage()` → data load → installs the single `[data-action]` delegation | runs after parsing ends |
| L26270 `<script defer src="assets/js/civic-search.js">` | `init()` (runs at end of parse, before `DOMContentLoaded`): `body.classList.add('civic-refresh')`, `#civicLanding` inserted before `#hero`, `home()` renders the civic landing, `#visaManualSection` moved into `#mainContent` | **the only moment the legacy hero is hidden** (`.civic-refresh.landing #hero { display:none !important }` in `civic-search.css`) |

So the boot is exactly the sequence the brief describes: legacy HTML → paint →
end of parse → `civic-refresh` → civic landing replaces it. Nothing in the static
document or `<head>` establishes the civic state; the hide rule exists only as a
class that JavaScript adds after 1.4 MB has been parsed.

### Measured flash (probe, `waitUntil: 'commit'`, 50 ms sampling)

| Profile | First painted state | Frames with legacy hero visible | Legacy visible for | Civic landing at |
| --- | --- | --- | --- | --- |
| Fast (5 ms RTT, 50 Mbps) | **LEGACY_HERO** | 10 | 536 ms | 1,156 ms |
| Slow 3G (400 ms RTT, 500 kbps) | **LEGACY_HERO** | 58 | 3,156 ms | not within the 20 s window |
| Mobile 390 (200 ms RTT, 1.6 Mbps) | **LEGACY_HERO** | 291 | 15,110 ms | not within the 20 s window |

| ID | Sev | Finding |
| --- | --- | --- |
| B-01 | **P1** | The legacy landing is the first-paint state on every network profile; the civic landing is a post-parse replacement. Confirmed root cause: `civic-refresh` is only added by `civic-search.js` `init()`. |
| B-02 | P1 | Nothing degrades gracefully: if `civic-search.js` fails to load or `init()` throws, the user keeps the legacy hero whose controls are bound to the same delegation, i.e. a half-working obsolete page. No error state exists. |
| B-03 | P2 | Two render-blocking font stylesheets in `<head>` (Pretendard dynamic subset; Unbounded / Pixelify Sans / Space Mono used only by the `archive_diary` theme). The second is pure cost on the default theme. |
| B-04 | P2 | `document-help.js` rewrites `<meta viewport>` and injects the mobile stylesheets mid-body: on phones the legacy hero re-lays out once those sheets arrive (visible shift in the "before" mobile capture during load). |
| B-05 | P3 | The wordmark loads with `loading="eager"` in the hidden legacy hero and again in the civic nav (two 120 px SVG requests on every visit). |

### LEGACY LANDING

Still fully shipped and fully styled (`.p-hero-*`, `.p-gateway`, `.p-gw-*`,
`.k-*`, `.hero-actions`, `.p-journey-entry`, `.visa-track-*`). It is reused in the
**searched** state (`#hero .header-inner` carries the search bar, disclaimer and
the searched language button), so it cannot simply be deleted. `applyLanguage()`
binds ~60 i18n keys into it on every language change (`gw*`, `hero*`,
`preTrack*`, `inTrack*`). `check_live_feature_surface.mjs` greps this markup for
the utility buttons and the New Home link, so removing it would fail CI.

### CIVIC LANDING

`assets/js/civic-search.js` (`home()`): nav (wordmark, 검색/서류 작성/이용 안내,
language control) → hero (title, sub, search form, 3 popular questions) →
`.cs-routes` (two journey buttons) → `.cs-tools` (3 tools: 필수 서류 작성 /
방문예약 안내 / 공식 원문 찾기) → source strip → footer → `<details>` "전체 도구
보기" (10 buttons + 2 links + theme) → `<details>` "이용 안내". Copy is a ko/en
object inside the script; `lang()` collapses every non-`en` locale to Korean, so
JA/VI/RU/DE/AR users get a Korean landing today (pre-existing; out of scope to
rewrite, noted in §16).

---

## 2. PRE-ENTRY / POST-ENTRY JOURNEY CONTROLS

Markup (`home()`):

```html
<section class="cs-routes">
  <button data-action="reveal-home-section" data-target="visaManualSection" data-journey-track="pre">…입국 전 · 사증 발급…</button>
  <button data-action="reveal-home-section" data-target="visaManualSection" data-journey-track="in">…입국 후 · 체류 관리…</button>
</section>
```

Handler (`index.html` L24280): adds `is-home-revealed` to `#visaManualSection`,
sets `aria-expanded="true"` on the clicked button, calls `startPreEntryTrack()` /
`startInKoreaTrack()` (L24714 / L24754) which write purpose cards into
`#visaManualDynamic`, then scrolls to the section.

Measured (all three viewports):

| Step | Expected | Observed |
| --- | --- | --- |
| click PRE while closed | opens, `aria-expanded=true` | opens ✓, `aria-expanded=true` ✓ |
| click PRE again | collapses, `aria-expanded=false` | **stays open**, `aria-expanded` **stays `true`** |
| click POST while PRE open | PRE deselects, POST content | POST content replaces the dynamic area ✓ but **PRE keeps `aria-expanded=true`** (both buttons expanded) |

| ID | Sev | Finding |
| --- | --- | --- |
| J-01 | **P1** | Second click on the open control does not collapse; no `CLOSED` transition exists at all. `is-home-revealed` is only ever added. |
| J-02 | **P1** | ARIA state lies: after PRE → POST both triggers report `aria-expanded="true"`. |
| J-03 | P1 | The revealed `#visaManualSection` is the **legacy** section: it contains the old `.visa-track-selector` (two more "입국 전 — 재외공관 사증 발급" / "입국 후 — 외국인 등록·체류 연장" cards, `onclick=` + `tabindex=0 role=button`, no `aria-expanded`) above the dynamic content — the user sees the choice twice, once civic, once legacy. |
| J-04 | P2 | Because `init()` prepends the section into `#mainContent`, the panel opens **below the footer, the "전체 도구 보기" directory and "이용 안내"** (before/desktop-1280-journey-pre-open-full.png) instead of under the control that opened it. |
| J-05 | P2 | The revealed content is styled by the legacy cascade: dark glass container, emoji icon tiles, `.cb` pills — a different design system from the civic landing around it. |
| J-06 | P2 | Labels are bureaucratic only ("사증 발급", "체류 관리"); no ordinary-language framing ("한국에 오기 전 / 한국에 온 뒤"). |
| J-07 | P2 | The journey cards are two identical rounded rectangles with 70 px icon circles and a chevron glued to the title (`.cs-routes strong .cs-icon`), i.e. the legacy card language transplanted into the civic page. |
| J-08 | P3 | `startPreEntryTrack()` renders ko / en / zh-CN only; other locales fall back to Korean. Pre-existing content; presentation only is in scope. |

### HOME DISCLOSURE STATE

`is-home-revealed` is a one-way flag shared by three targets (`visaManualSection`,
`pathwaySection`, `reminderSection`); the directory's "입국 전 · 사증 발급 / 입국
후 · 체류 관리" button reveals the section with **no** track selected (legacy track
selector only). The E2E `landing-utilities.spec.mjs` asserts each target becomes
visible after one click and nothing about closing.

---

## 3. WAYMAKER ENTRY · NEW HOME ENTRY

| Surface | Waymaker | New Home |
| --- | --- | --- |
| Civic landing | one underlined text link **"Waymaker AI"** inside the collapsed `<details>` "전체 도구 보기", after 10 other buttons | one underlined link "국적·귀화 안내" in the same collapsed directory |
| Legacy hero (hidden) | `.p-gw-card-ai` "Waymaker AI 상담" | `.p-gw-newhome` banner (`#gwNewHomeLink`) |
| Searched state | "상황이 복잡한가요? Waymaker로 추가 분석" handoff + Quick Answer follow-up | — |

| ID | Sev | Finding |
| --- | --- | --- |
| E-01 | **P1** | Both specialist tools are only reachable from the homepage through a collapsed disclosure (`<details>` closed by default) — effectively buried. On mobile the directory sits below the footer. |
| E-02 | P2 | "Waymaker AI" is an unexplained product name; nothing says "situation-based guidance". |
| E-03 | P2 | "국적·귀화 안내" drops the New Home brand the rest of the product uses (`gwNewHomeLabel` = "New Home 국적·귀화"). |
| E-04 | P2 | The hierarchy on the civic home is SEARCH → JOURNEY → 3 tools → source strip → footer → directory; Enforcement, pathways, reminders, Waymaker and New Home are all peers in the directory. |

Route integrity today: `ai.html` (chat workspace; `?nav=1` opens the guided
navigator, `?domain=nationality` keeps chat), `new-home.html` (nationality hub,
own language selector reading `paradiso:language`). Both are plain relative
links, no overlay intercepts taps. Back navigation restores the landing because
the landing is the default state.

---

## 4. FORM HELPER — CURRENT ARCHITECTURE

`form-helper.html` (3,485 lines; ~700 lines CSS, ~2,600 lines JS) +
`assets/js/form-helper-i18n.js` (400 KB ko→13-locale display dictionary) +
`data/form_schemas.json` (70 KB overlay maps) + `assets/forms/pdf/*.pdf` +
`assets/forms/fonts/NanumGothic-Regular.ttf` (Latin + Hangul subset) +
`assets/forms/vendor/pdf-lib.min.js`, `fontkit.umd.min.js` (loaded on demand).

Flow: picker (3 cards) → F-4 branch question (for 통합신청서) → 6-step wizard
(유형 → 자격 → 인적 → 추가 → 확인 → 가이드) with a right-hand **text** summary
"신청서에 반영될 내용" (not a visual preview) → step 6 = text guide + download
buttons. State is one in-memory object (`state`), never persisted. Export:
`generateOfficialPdf()` loads pdf-lib + fontkit + the official PDF + font, draws
`spec.overlay[key]` values (single-line shrink-to-fit ≥5 pt, optional white-out
box, 13-digit cell grid for the ARC number, check marks), downloads a Blob.

| ID | Sev | Finding |
| --- | --- | --- |
| F-01 | **P1** | There is no visual preview for F01/F04/F07: the user cannot see where text lands until the PDF is downloaded, and the "preview" aside is a truncated text list (address cut at 18 chars). §37 is unmet. |
| F-02 | **P1** | Text fitting is a silent shrink loop down to **5 pt** with no user warning; an overlong address is exported unreadable instead of flagged (§36). |
| F-03 | **P1** | F06 (거주·숙소제공확인서) is exported from a **hand-drawn canvas replica** ("Visable 참고용 초안" printed on it), not the official HiKorea PDF that is shipped (`assets/forms/pdf/F06.pdf`) and already mapped in `form_schemas.json` (30 overlay keys). Two renderers, two layouts. |
| F-04 | P1 | Coverage: 4 forms (+2 Chinese variants). Address-change, mobile residence card, certificate-of-fact, re-entry-extension, H-2 job-start, employer change report, SES, visa application, CVE, spouse invitation — all absent although the official templates exist in the repo (`docs/source-manuals/law/…1106…pdf`). |
| F-05 | P1 | No form inventory, no coverage report, no exclusion list. Nothing prevents a 출국기한유예 or refugee form from being added by accident, and nothing states that they are out of scope. |
| F-06 | P1 | No template drift protection: the overlay coordinates are applied blindly to whatever PDF is at `spec.pdf`; page count and size are not checked; no checksum. |
| F-07 | P2 | Picker is a bureaucratic 3-card list; no search by task, form number or procedure (§31). |
| F-08 | P2 | Mobile: stepper labels hidden ≤640 px, sticky preview card becomes a second column below the wizard, no zoomable preview, no safe-area handling for bottom actions. |
| F-09 | P2 | Reset uses `window.confirm` and clears the form but keeps `formId/docType`; no "start over" that returns to the picker. |
| F-10 | P2 | Page chrome does not use the shared civic system (paper `#F4EEE0`, `--p-*` tokens, its own header/footer); the landing links to it as a core tool. |
| F-11 | P3 | Step headings / validation copy are Korean-only strings overlaid by a DOM text dictionary; EN falls back to Korean with a "not yet translated" note. |

### SUPPORTED FORMS (before)

| id | Official name | Legal basis | Revision | Pages | Fields | Output | QA |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | 통합신청서(신고서) | 출입국관리법 시행규칙 별지 제34호 | 2022-04-12 | 1 | 42 | overlay on official PDF | manual checklist (never executed) |
| F03 | 통합신청서 (중문 병기) | 별지 제34호의3 | 2023-06-14 | 1 | 41 | variant of F01 | — |
| F04 | 재외동포(F-4) 통합신청서 · 국내거소신고서 | 재외동포법 시행규칙 별지 제1호 | 2022-04-12 | 1 | 32 | overlay | — |
| F05 | 재외동포 통합신청서 (중문) | 별지 제1호의2 | 2022-04-12 | 1 | 31 | variant of F04 | — |
| F06 | 거주/숙소제공확인서 | HiKorea 민원서식 (개정 2024.5) | 2024-05 | 1 | 30 (unused) | canvas replica → PNG/PDF | — |
| F07 | 신원보증서 | 별지 제129호 | 2022-02-07 | 2 | 28 | overlay | — |

### OFFICIAL FORM INVENTORY (sources available offline)

* 출입국관리법 시행규칙 (법무부령 제1106호, 2026-01-23) annex list: **284 unique
  별지 서식** (`docs/source-manuals/law/별지서식_인덱스.txt` + titles extracted from
  `rule_1106_full.txt`; the official PDF of the rule is in the repo, 428 pages).
  The bulk are official-use documents (심사인, 허가서, 통지서, 대장, 명령서,
  보호·강제퇴거·출국정지 서류, 통계표). Applicant-facing civil-petition forms are a
  subset of about 30.
* 재외동포법 시행규칙: 별지 제1호, 제1호의2 held locally; the full annex list is
  not verifiable offline.
* HiKorea 민원서식: 421 download links counted in the 2026-06-12 audit
  (`docs/forms_official/FORM_VERSION_AUDIT.md`); only 거주숙소제공확인서 held locally;
  hikorea.go.kr is unreachable from the build sandbox.
* Explicitly out of scope for auto-fill: 출국기한유예신청서 (별지 제44호),
  출국기한유예 불허결정 통지서 (제44호의2); 난민임시상륙허가 신청서 (제30호의3),
  난민여행증명서 (재)발급신청서 (제126호의10·11), 유효기간 연장허가 신청서
  (제126호의14) and every 난민법 시행규칙 form.

The full machine-readable inventory with per-form status is built in this sprint
(`data/forms_inventory.json`, `docs/forms_official/FORM_HELPER_COVERAGE_20260923.md`).

### PDF RENDERING · TEXT / FIELD MAPPING

* Coordinates are top-left PDF points; `y` is converted with `H - y`. Checkboxes
  are drawn as two lines; the ARC number uses measured cell centers. Values are
  single-line only (no wrapping anywhere), max width = `maxWidth` or page edge.
* Characters outside the embedded font (Vietnamese diacritics, Cyrillic, Arabic,
  漢字) are detected via `font.getCharacterSet()` and the field is left blank with a
  warning — correct behaviour, kept.
* Preview ≠ export: the text summary and the PDF are two separate derivations of
  `state` (§73 violated, low risk today because the summary is read-only).
* F06 canvas replica: fonts and cell geometry differ from the official form.

### FORM DATA PRIVACY (verified by reading every network call)

`fetch()` calls in `form-helper.html`: `data/form_schemas.json`, the template PDF,
the font, `data/i18n/*.json`. No call carries form values; `localStorage` holds
only `paradiso:brightness`, `paradiso:language`, `paradiso:easyMode`. `console`
never logs values. The copy-guide masks the passport number (`****1234`). No
analytics vendor exists in the repository (grep: none). Query string is read
(`?form=…&type=…&source=waymaker&visa=…&procedure=…`) but never written with
personal data.

---

## 5. DOCUMENT PHYSICAL-FORM RULES

Model (`data/guidance-rules-202609.json` → `data/status-guidance-202609.json`,
authored by `scripts/status_guidance/author_rules.py`): every document item
carries `submission_form` from the enum `ORIGINAL_ONLY, COPY_ONLY,
ORIGINAL_AND_COPY, ORIGINAL_PRESENT_COPY_SUBMIT, CERTIFIED_COPY,
ONE_OF_ORIGINAL_OR_COPY, ELECTRONIC_DOCUMENT_ACCEPTED, VARIES_BY_ITEM,
SOURCE_DOES_NOT_SPECIFY, NOT_APPLICABLE`, plus `form_basis`
(`SOURCE_PHRASE | REGULATION | NONE`), `copy_count`, `original_returned`. A form is
set only from the transcribed source phrase or a quoted regulation clause; a bare
"여권" stays `SOURCE_DOES_NOT_SPECIFY` (CI: `check_document_physical_form.mjs`).
Coverage report `reports/data-coverage/document-physical-form-202609.md`: most
rules are silent on form.

Renderer (`assets/js/status-guidance.js` `renderDocItem`): explicit forms get a
row label; `SOURCE_DOES_NOT_SPECIFY` prints, in the details of **every** silent
item including the application form itself:

> 원문에 원본·사본 표기가 없어요. 원본을 지참하면 안전해요(관서 확인).

The same sentence family exists in `waymaker-quick-answer.js` (`focusUnspecified`,
`unc.forms` "…원본을 지참하면 안전해요."). The sentence is asserted by
`check_document_physical_form.mjs` and `check_waymaker_quick_answer.mjs`.

| ID | Sev | Finding |
| --- | --- | --- |
| D-01 | **P1** | The fallback copy is vague ("안전해요"), repetitive (printed on 통합신청서, 여권, 혼인관계증명서, … — 8 times on one F-6-1 answer), and blurs the two dimensions the brief separates: whether a document is required vs what physical form to prepare. |
| D-02 | P1 | No distinction between **official explicit** and **preparation recommendation** exists in the rendered output beyond a parenthesised basis on explicit rows; a user cannot tell "사본 1부 제출" (source) from a heuristic. |
| D-03 | P1 | `원본 지참` (present) and `원본 제출` (surrender) are conflated in the enum labels: `ORIGINAL_ONLY` renders as "원본" with no present/surrender semantics unless `original_returned` happens to be set (only two regulation-backed rules set it). |
| D-04 | P1 | Possession-sensitive originals (passport, contracts, diplomas, licences, ID cards) receive the same generic sentence as a utility bill. Nothing prevents the UI from suggesting surrender of an original when a rule says `ORIGINAL_ONLY` without `original_returned`. |
| D-05 | P2 | The application form (`app_form_34`), fee and photo items carry `SOURCE_DOES_NOT_SPECIFY` and therefore print the disclaimer although a physical-form question is meaningless for them. |
| D-06 | P2 | Passport: the manual is explicit in three ways (여권 원본 ×~20 entries, 여권 및 사본 1부 (D-2 등록), 여권 사본 (D-10·F-2·F-5 등)) and silent in most (bare 여권). There is **no** global "original + copy" rule in the source; the product-owner expectation can only be met as a preparation recommendation, not as an official rule. |

Source facts established for this sprint (stay manual 2026-09-18, full text):
* line 15338 (F-4 chapter): "여권 및 본국 신분증 사본(원본 제시)" — explicit
  present-original / submit-copy;
* line 6944: "사본 제출시 재외공관 공증(아포스티유), 단 원본 제출할 경우 공증 절차
  생략" — explicit original-vs-copy alternative;
* lines 678–900: "여권 원본" for A-/B-/C-series extensions; line 1181/1302:
  "여권 및 사본 1부" (D-2 registration); lines 19242–19461: "여권 사본" (F-2·F-5
  points/visa families); 456–664: bare "여권".
* Contracts: "고용계약서 원본 및 사본" (E-1 extension), "사무실 임대차 계약서 원본"
  (D-8 line 2960), "공동사업자약정서 원본" (D-8), "표준근로계약서 사본" (E-9);
  otherwise bare "고용계약서"/"임대차계약서".

---

## 6. MOBILE / WEBKIT

* CI: `mobile-render-qa` (Chrome, 5 iPhone profiles) and `mobile-webkit-qa`
  (WebKit, PR-only) run against the landing and 8 guidance flows; both check
  overflow, <16 px inputs, <40 px targets, injected mobile sheets.
* Landing (before, Chromium/Safari UA): no horizontal overflow at 320/390; journey
  panel opens below the footer (J-04); the legacy dark panel is the only
  non-civic surface on the page.
* Form Helper (before): usable at 390 but the wizard is a desktop layout stacked;
  the aside "preview" lands under the last step; download status appears far
  below the buttons.
* WebKit-specific PDF concerns to test in CI: Blob download via `<a download>`
  (iOS Safari opens the PDF in a new tab instead of saving), `URL.revokeObjectURL`
  4 s after click (too early for a slow tap-to-share), repeated export creating a
  new Blob each time (fine), canvas `toBlob` memory on 3× A4 (F06).

| ID | Sev | Finding |
| --- | --- | --- |
| M-01 | P1 | iOS Safari + `URL.revokeObjectURL(url)` after 4 s: a user who taps "다운로드" and then chooses "Share…" can hit a revoked URL. |
| M-02 | P2 | No safe-area (`env(safe-area-inset-bottom)`) on the wizard's action row. |
| M-03 | P2 | Preview canvas (F06) is a 794 px-wide image scaled into 350 px — unreadable without pinch zoom, and pinch zoom is not enabled on that container. |

---

## 7. ACCESSIBILITY

| Area | State |
| --- | --- |
| Journey triggers | `<button>` with `aria-expanded` (never reset) and `aria-controls="visaManualSection"` **missing** on the civic buttons (only on the hidden legacy ones); legacy `.visa-track-card` are `div role=button` with `onclick` and no keyboard `Enter`/`Space` handling → J-02, J-03 |
| Journey content | `#visaManualDynamic` has `aria-live="polite"`, purpose cards are `div onclick` — not focusable |
| Directory | `<details>/<summary>` ✓ |
| Language control | dialog with `aria-labelledby`, focus return ✓ (PR #632) |
| Form Helper | labels bound with `for`; required marked `*` (aria-hidden) but no `aria-required`; validation list is not `aria-live`; step panels shown/hidden without heading focus; radio cards use `role=radio` on buttons without a `radiogroup` roving tabindex; touch targets ≥44 px in header only |
| Contrast | civic tokens gated by `check_civic_tokens.mjs` ✓ |
| Reduced motion | civic + mobile sheets honour it ✓ |
| RTL | civic landing has RTL rules for the language dialog only; journey/tool rows are flex/grid and mirror naturally |

---

## 8. I18N IMPACT

* Civic landing copy: ko/en inside `civic-search.js`; other locales → Korean.
* Shared packs `data/i18n/*.json`: 14 locales, 986 keys, strict parity enforced by
  `check_i18n_coverage.mjs` (every key in every pack, same shape) and
  `check_official_terms.mjs` (visa codes preserved). New chrome must be added to
  **all 14 packs** or CI fails.
* zh-TW is a runtime conversion of zh-CN (`zh-traditional.js`); Arabic sets
  `dir=rtl` on `<html>`.
* Form Helper uses a DOM text dictionary (`form-helper-i18n.js`) keyed by exact
  Korean strings — any Korean string I change must either keep its dictionary key
  or be rendered through the shared packs.

---

## 9. IMPLEMENTATION PLAN (this sprint)

1. **Boot** — put the civic state in the static document: `civic-refresh` on the
   static `<body>`, a static pre-rendered Korean civic shell (`#civicLanding`) in
   the HTML that `civic-search.js` hydrates (binds listeners; re-renders only when
   the language differs), a `<noscript>` and a JS-failure state (`script onerror`
   + `try/catch` around `init()` → `civic-boot-failed` reveals a plain retry row
   with official links). Parity between the static shell and `home()` output is
   asserted by a new Node check, and a Playwright first-paint test samples frames
   under throttling and asserts the legacy hero is never displayed. Google Fonts
   for the alternate theme become non-render-blocking.
2. **Journey** — a real state machine in `civic-search.js`
   (`CLOSED | PRE_ENTRY_OPEN | POST_ENTRY_OPEN`), triggers with
   `aria-expanded`/`aria-controls`/`aria-pressed`, keyboard = click, panel mounted
   **inside** the civic landing directly under the triggers, legacy track selector
   hidden in civic mode, dynamic content re-skinned under `.civic-refresh`; the
   existing `startPreEntryTrack()` / `startInKoreaTrack()` / `showVisaRecommendations()`
   / `selectInKoreaAction()` content functions stay untouched (data preserved).
   Ordinary-language copy through the shared packs (KO/EN complete, 12 locales
   translated).
3. **Waymaker / New Home** — "핵심 도구" section on the civic home: 필수 서류
   작성 · Waymaker (상황 기반 절차 안내) · New Home (국적·귀화와 정착 준비),
   subordinate to search; supporting tools stay in a second row; E2E for
   navigation and back on mobile.
4. **Document physical form** — renderer-level preparation policy layered over the
   untouched data: `OFFICIAL_EXPLICIT` rows keep their labels; silent rows get a
   preparation recommendation (`원본 지참 권장`, `원본 지참 · 사본 준비` for
   possession-sensitive classes), application forms / fees / photos get no form
   row, one explanatory sentence per document section instead of one per item,
   `원본 · 돌려받음` vs `원본 제출 (반환되지 않음)` wording for explicit originals,
   Quick Answer wording aligned; tests.
5. **Form Helper 2.0** — single form-engine module (`assets/js/form-engine.js`)
   shared by editor, canvas preview and pdf-lib export; picker by task group +
   search (name / task / form number / procedure); step workflow with backward
   navigation; visual page preview on pre-rendered template PNGs; fit warnings
   before export; reset with confirmation; official F06 template instead of the
   replica; new forms from the official rule PDF (address change, mobile residence
   card, certificate of fact, SES, re-entry extension, H-2 job start, employer
   change report, E-2 health statement, 한자 variant …); inventory + coverage
   report + machine-readable coverage test + template drift test (page count,
   size, anchors, sha256); explicit exclusions.
6. **QA** — repo validation, existing E2E, new E2E (first paint, journey, entries,
   form helper), mobile render QA, screenshots (Chromium; WebKit via CI), i18n
   long-text checks (DE/RU/VI/EN/AR).

## 10. NON-GOALS

* Translating the pre-existing civic landing copy (search/hero/manual results)
  into the 12 non-ko/en locales — the packs and `lang()` model would need a
  separate migration.
* Rewriting the immigration content of the journey tracks (`showVisaRecommendations`,
  `selectInKoreaAction`) or any `visa_data.json` / `doc_master.json` record.
* Refugee / departure-deadline forms in the Form Helper (explicitly excluded).
* The 9-page 외국인 배우자 초청장 (별지 제19호의2) and the 결혼배경 진술서
  (제19호의3): narrative forms whose mapping cannot be validated in this sprint —
  inventoried, not supported.
* Verifying form editions against law.go.kr / HiKorea live (no network from the
  sandbox): recorded as a version risk in the coverage report.
* Any new analytics vendor.

## 11. AFTER — what shipped, with evidence (2026-09-23)

Everything below was measured on this branch (Chromium via Playwright 1.61 in the build
sandbox; WebKit only through the CI job `mobile-webkit-qa`, which this branch extends).

### 11.1 First paint (Issue A)

| Profile | Before (legacy hero visible) | After |
| --- | ---: | ---: |
| fast (no throttling) | 536 ms | 0 frames with the legacy hero, `firstPaintedState = CIVIC` |
| slow 3G (CDP throttling) | 3 156 ms | 0 frames |
| mobile (390 px, 300 ms RTT / 2 Mbps) | 15 110 ms | 0 frames |

Mechanism: a static civic shell inside `index.html` generated byte-for-byte from
`homeHtml()` (`scripts/build_landing_shell.mjs`, guarded by `scripts/check_landing_shell.mjs`,
34 checks in `check_repo.sh`), `civic-refresh` on `<body>` in the markup, inline critical CSS,
non-blocking fonts, `onerror` boot-failed row, `<noscript>` fallback; `civic-search.js` reuses
the shell (`data-cs-hydrated="reused"`). CLS on the landing < 0.25 asserted in
`tests/e2e/landing-boot.spec.mjs` (fast + throttled profiles). No `setTimeout`, no hidden body.

### 11.2 Journey controls (Issue B)

State machine `CLOSED | PRE_ENTRY_OPEN | POST_ENTRY_OPEN` in `assets/js/civic-search.js`
(`window.VisableCivicSearch.journey`). Second click collapses (PASS), PRE → POST switches
without an intermediate closed flash (PASS), `aria-expanded` / `aria-controls` /
Enter / Space / Escape / focus return all asserted in `landing-boot.spec.mjs` (22 runs green on
desktop-1280 + mobile-390 + mobile-320). Content functions `startPreEntryTrack()` /
`startInKoreaTrack()` untouched; the legacy pseudo-labels are hidden by CSS only.

### 11.3 Waymaker / New Home entries (Issue D)

Core tool row on the landing (`.cs-tools-core`: 서류 작성 · Waymaker · New Home) directly under
the journeys, ≥ 44 px targets, situation-based one-line explanations, ordinary-language copy in
all 14 packs (`civic.*`). Route integrity (`ai.html`, `new-home.html`, Back restores the
landing) in `landing-boot.spec.mjs`; the mobile matrix below confirms the targets at every width.

### 11.4 Form Helper 2.0 (Issue C)

| Metric | Value |
| --- | ---: |
| Official forms inventoried (`data/forms_inventory.json`) | 292 |
| Applicant-facing | 46 |
| SUPPORTED before / now | 6 / 14 |
| Newly supported | 9 (F02, F08, F09, F10, F11, F12, F13, F14, F15) |
| Fully QA'd (`support.qa = PASS`: verified export + clean geometry audit) among SUPPORTED | 14 |
| PARTIAL (mapped and QA'd, edition not comparable) | 1 (F06 — HiKorea file, `PENDING_HIKOREA`) |
| BLOCKED (applicant-facing, no field map yet) | 31 |
| EXCLUDED — departure deadline | 2 (44, 44의2) |
| EXCLUDED — refugee | 9 (30의3, 30의4, 30의5, 126의11, 126의12, 126의13, 126의14, 126의15, (all annexes)) |
| Not applicable (official-use / enforcement / deleted) | 233 |
| Unknown (sources not verifiable offline) | 2 |
| Stale / superseded | 0 |

SUPPORTED is strict: `support.qa = PASS` **and** `template.verification = VERIFIED_CURRENT`
(the annex in force, read from law.go.kr through its Open API on 2026-09-23 — 출입국관리법
시행규칙 MST 289833 in force from 2026-09-15, 재외동포법 시행규칙 MST 267499 in force from
2025-02-01 — has the same header revision tag and row / cell structure as the template). The
guard rejects any SUPPORTED form that misses either half.

* **Cell geometry (found and fixed late in the sprint).** The sample-based export check only
  proved that the PDF draws what the preview draws — not that either draws inside the right box.
  A new static audit (`scripts/forms/audit_overlay_geometry.py`, in the guard, self-tested with
  planted defects) checks every one of the 533 overlays against the template's own vector
  rules and printed text. On the pre-fix schema it reports 199 issues (144 cells without a width
  limit, 24 areas running past the row end, 22 containing a table rule, 6 overlapping printed
  text, 3 cut by a divider) — 146 of them already on `main`'s six forms — and 46 values in the
  sample exports crossed a cell border, a divider or a printed label. Pre-existing on `main`
  (F01, F03, F04, F05, F06): phone,
  mobile, e-mail, home-country phone, income, occupation, nationality, passport-expiry and
  application-date values started inside the label cell and ran over the border; the F03 birth
  date put the month in the year cell and the day on top of 月; F06 values started 15 pt left of
  the value column; 144 text cells had no width limit, so an overflow was never flagged. From
  this sprint (F02, F10–F14): F02's name cells ran into the next column and its 13-digit
  registration number was one text run across the digit grid; F12–F14 widths ran past the
  table's right end; F11 / F13 / F14 values touched printed labels. All were re-measured from the
  PDF geometry (values in the empty value cell, birth dates centred in the empty line under
  년 / 월 / 일 with the printed `yyyy / mm / dd` hints left visible, one digit per printed cell):
  audit 199 → 0 issues, sample collisions 46 → 0, every sample export re-inspected as an image.
  Narrow official cells now say so: a mobile number in the 2 cm phone cells or a long
  nationality name shrinks to 6.5–7 pt and is flagged SHRUNK ("인쇄 확인") before export.
* **Contrast and motion (found in final QA).** The element reset `.fh-body button { color:
  inherit }` outranked `.fh-btn-primary`, so every primary action (작성 시작, 다음, PDF 내려받기)
  printed dark text on the dark green: 1.7 : 1 in the light theme, 1.4 : 1 in the dark theme.
  The reset now sits in `:where()` and controls on the green use the page-background token as
  text colour (9.3 : 1 light, 10.3 : 1 dark — plain `#fff` would have failed on the dark
  theme's mint). The screen fade ignored `prefers-reduced-motion` (the page is outside the
  `.civic-refresh` scope that carries the landing's rule); it is now switched off there. Both
  are asserted in `form-helper.spec.mjs` (the contrast test fails on the old stylesheet), and
  the screenshot script no longer captures screens mid-fade.
* One data model (`data/form_definitions.json`) drives editor, preview and export through
  `assets/js/form-engine.js`; the browser export and the Node QA export draw the identical
  operations (`VisableFormHelper.lastExport.ops` == canvas ops, asserted in
  `tests/e2e/form-helper.spec.mjs`; every form's Node export verified span-by-span against the
  ops by `scripts/forms/verify_export.py`).
* Text fit: shrink in 0.5 pt steps to a 6.5 pt floor, wrap where the cell allows lines,
  otherwise clip inside the cell and flag OVERFLOW (field, review screen, export dialog); glyphs
  outside the embedded font leave the cell blank and are flagged FONT — never drawn silently.
* Template drift: sha256 + byte size + page count + page size + anchors recorded per template in
  `data/form_schemas.json` and asserted by `scripts/check_form_helper.mjs` (2 489 checks,
  20 sample exports).
* F06 now fills the official HiKorea PDF (the hand-drawn canvas replica is gone).
* Privacy: the only requests are static assets, the template PDF, the font and the two vendor
  libraries; no storage of values, no analytics (asserted in the E2E request log).
* Exclusions are searchable with the honest hand-off "이 서류는 Visable 자동작성 대상이 아니에요"
  and never fillable (guard + E2E).
* Coverage report: `docs/forms_official/FORM_HELPER_COVERAGE_20260923.md` (generated,
  freshness asserted in CI).

### 11.5 Document physical-form model (Issue E)

Renderer-level policy (`assets/js/status-guidance.js`): `OFFICIAL_EXPLICIT` from the source
phrase (원본 / 사본 / 원본 + 사본 / 원본 제시 · 돌려받음 / 원본 제출 · 반환되지 않음) versus
`PREPARATION_RECOMMENDATION` (dashed chip) computed from the document class — passports,
registration cards, contracts, diplomas → 원본 지참 · 사본 준비; other evidence → 원본 지참 권장;
forms / fees / photos → nothing. The weak sentence "원본을 지참하면 안전해요(관서 확인)" is gone
from the renderer, the Quick Answer and the AI prompt; the basis is shown once per document
details row, the section note once. `check_document_physical_form.mjs` 633 checks (unit rules:
passport keep, contract never 제출, forms/fees not applicable, explicit wins; rendered rows for
D-2 / F-6-1 / address report / card reissue / E-1 / E-9). No data file was edited.

### 11.6 Mobile / WebKit / i18n

* `docs/design/mobile-matrix-20260923.md`: 320 / 360 / 375 / 390 / 393 / 414 / 430 / 768 — no
  horizontal overflow on the landing (journey open and closed) and the Form Helper (home, editor,
  preview sheet), all core targets ≥ 44 px; Form Helper chrome at 320 px in ja / vi / ru / de / ar
  / en without clipped buttons; Arabic RTL from first paint (a skip-link overflow bug found and
  fixed here, now asserted in the E2E).
* WebKit could not run in the sandbox; `scripts/mobile_webkit_qa.mjs` now also drives the journey
  toggle and the Form Helper phone flow on iPhone SE / 15 so the CI job covers them.
* i18n: 14 packs carry the new `civic` (85 keys) and `fh` (113 keys) objects with real
  translations; parity guarded by `check_i18n_coverage.mjs` (1 446 keys). Field labels are
  KO/EN by design (the forms are completed in Korean or English); other locales show the English
  label with the Korean official name underneath.

### 11.7 Test / check status

`bash scripts/check_repo.sh` → exit 0 (backend suites need `backend/requirements-dev.txt`);
E2E on desktop-1280 + mobile-390 + mobile-320: `form-helper` 27 / 27, `landing-boot` 33 / 33,
`landing-utilities` + `post-search-guidance` 36 / 36, search + Quick Answer + language 128 / 128;
guidance suites green (document guidance 936, physical form 633, resolver 61, Quick Answer 21,
navigator 404).

Root causes of the Form Helper E2E failures met on the way (all fixed in production code or in
the test environment, no assertion weakened, no timeout raised):

* edition switch (3 runs): switching F01 → F03 changed the template but the preview canvases were
  not rebuilt → rebuild on edition change;
* workflow (3 runs): fields on a step hidden by the application type (power of attorney) were
  still validated → hidden-step fields are inert in the engine;
* download name (3 runs): Linux Chromium converts the suggested name to the process's native
  multibyte charset and the test browser ran under the POSIX locale, so every non-ASCII name
  became `download` (probe: ASCII names survived, timing and user gesture made no difference,
  `C.UTF-8` fixed all) → `playwright.config.mjs` launches the browser under a UTF-8 locale and
  the test asserts the exact Korean file name;
* CI `validate`: the inventory freshness check depended on PyMuPDF being installed → the annex
  page map is pinned (sha256 of the rule PDF) and the guard re-runs the check with PyMuPDF
  blocked; the CI job installs `pymupdf==1.28.2` for the export and geometry checks.

### 11.8 Known limitations (honest)

* Edition currency: the 14 statute templates were compared with the annexes in force on
  2026-09-23 (law.go.kr Open API; same header revision tag and structure). Amendments already
  promulgated take effect on 2027-09-16 (법무부령 제1125호 / 제1124호): the check has to be re-run
  then. F06 (HiKorea 거주/숙소제공확인서) could not be compared with the current HiKorea file and
  stays PARTIAL.
* This is rendering / placement QA, not legal revalidation: Visable fills what the user types
  into the official cells; it does not decide which form or attachments a case needs.
* Narrow official cells (2 cm phone cells, the 희망 자격 brackets on 별지 제34호서식 and its
  editions) cannot hold every value at a readable size: long values are shrunk to the 6.5 pt
  floor and flagged, or flagged OVERFLOW before export (e.g. a six-character status code such as
  `D-10-1` inside the 19 pt bracket of the Chinese edition).
* 漢字 name cells (F02, F07, F12, F13) are left for handwriting: the embedded font has no CJK
  ideographs; circled reason codes on F14 print as plain letters/digits.
* 31 applicant-facing annexes remain BLOCKED (listed in the coverage report), among them the
  Chinese / Vietnamese / Thai / Russian editions of the 체류지변경신고서 (34의5–34의8).
* Chromium was the only local browser; WebKit evidence comes from CI.
