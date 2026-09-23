# Visual sign-off — PR #634 (2026-09-23)

Independent, release-gating visual QA of the landing, the journeys, the Waymaker / New Home
entries, the Form Helper UI and every filled official form, done by rasterizing and inspecting
the actual outputs and cross-checking each visual conclusion against the automated checks. Every
defect found was fixed in this pass, re-rendered and re-inspected; nothing is left for a human
to "please look at".

Tools (all in the repo): `scripts/forms/audit_overlay_geometry.py` (every overlay against the
template's own rules and printed text), `scripts/forms/verify_export.py` (export spans vs. preview
ops), `scripts/qa/form_long_text_20260923.mjs` (hostile values in every name / address / employer
cell), `scripts/qa/visual_signoff_20260923.mjs` (125 captures: 9 viewports × landing states and
Form Helper screens, light + dark, 7 languages, with measured overflow / contrast per capture),
`scripts/qa/text_overflow_scan_20260923.mjs` (14 languages × 9 widths × 3 pages), the E2E suites
and the CI WebKit job.

## FORM PDF REVIEW

| | |
| --- | --- |
| Templates inspected | 15 — the 14 SUPPORTED (F01–F05, F07–F15) and F06 (PARTIAL) |
| Filled PDFs | 20 representative samples (child / Chinese / Japanese / address-change / extension variants of F01–F05) + 15 long-text PDFs |
| Pages rasterized and inspected | 24 sample pages + 19 long-text pages, at 1.9–8× (each page cropped to the region that carries values, checkboxes zoomed to 8×) |

Checked on every page: value inside its cell, clear of labels, borders and dividers; dates clear
of labels and separators; ticks inside their `[ ]`; right page; right template (sha256 drift
guard); nothing clipped silently; nothing outside the page; digit grids (13-digit registration
numbers, 11-digit phone cells, F08's hyphen cell) one digit per printed cell; Korean and Latin
glyphs (including `'` and `-`) render.

F01–F05 fields inspected explicitly: surname / given names (centred in their columns), date of
birth (centred in the empty line under 년 / 월 / 일, the printed `yyyy / mm / dd` hints visible),
passport number / issue / expiry, telephone, mobile, e-mail, annual income, 외국인등록번호 grid,
application date (the empty cell right of 신청일), refund bank account, school status row
(ticks for 미취학 / 초 / 중 / 고, school name and phone, 인가 / 비인가 ticks).

Issues found in this pass and fixed. The geometry audit and the export verifier both stayed
green on them: the values sat just beside or just under their labels, below the audit's overlap
threshold. The audit now has a TOUCHES_LABEL rule (≥ 1.5 pt under a label, no label tail running
into a value's start; inline slots after ':' or '(' exempt) and the guard plants the three old
coordinates to prove the rule catches them:

| Form | Field | Defect | Fix |
| --- | --- | --- | --- |
| F10 | applicant phone, applicant date of birth | value butted against "(Phone No.)" / "(Date of Birth)" | moved 7 / 4 pt right, width kept inside the cell |
| F15 | English side: date of birth, passport no. (and name / nationality for alignment) | "Date of Birth1996.08.08", "Passport No.AB123456" | English values in one column 6 pt after the longest label |
| F15 | English "disease name" slot | touching "etc)" | 1.5 pt gap |
| F07 | 대한민국 주소, 근무처 주소 | started 40–75 pt right of the value column, forcing long addresses to the 6.5 pt floor | aligned to the value column (x 150): long addresses now 7.5 pt, no warning. The first attempt put the domestic address directly under its label with no gap; the image showed it, so its baseline moved to 249.5 (≈ 3 pt under the label, like the other F07 values) |

Unresolved: none. Tight by the form's own design (legible, not overlapping): F13 신고일자 year —
the printed slot between "신고일자:" and "년" is 16.8 pt, so the year prints at 6.8 pt; the
희망 자격 brackets of 별지 제34호서식 and its editions (19–30 pt).

## BEFORE / AFTER

`docs/design/screenshots/landing-form-helper-20260923/after/form-geometry-{F01,F03,F06}-before-after.png`
re-inspected row by row. Every corrected value moved from the label cell (or across a border)
into its value cell; F03's birth date went from "年 11 | 월 月02" to 1993 / 11 / 02 under
年 / 月 / 日; no row gained a new overlap, no neighbouring value moved into another cell. The
after images match the current exports (F01 / F03 / F06 coordinates were not touched after they
were generated).

## LONG TEXT

Cases (per template, in every name / address / institution / employer / e-mail cell):
`WOLFESCHLEGELSTEINHAUSEN`, `MARIA-ALEXANDRA JOSEPHINE`, `O'CONNOR-SMITH SEAN PATRICK`,
a 45-character Korean address, a 68-character English address, a long Korean school name, a long
Korean employer name, `Samsung Electronics 삼성전자(주) Suwon`, a 57-character e-mail, a 2-line
reason and a 2-line incident text.

* Minimum drawn size: **6.5 pt** (the engine floor). Nothing smaller is ever drawn.
* Every value either fits, is shrunk to ≤ 7 pt and flagged SHRUNK ("인쇄 확인"), or is clipped
  inside its own cell and flagged OVERFLOW — the field, the review screen and the export dialog
  say so before download (E2E: long-text test, export dialog). Multi-line cells wrap (F08
  address 2 of 3 lines, F12 reason and F14 incident on 2 lines). No FONT issue.
* All 15 long-text exports pass the span verifier: no drawn text outside its cell limit.
* The F08 address input is capped at 120 characters, which always fits its 3 lines.

## HOMEPAGE

* First paint: civic shell from the first frame (landing-boot E2E, 0 legacy frames under fast /
  slow 3G / mobile profiles); no glass, no legacy hero.
* Default landing at 320–1280: one product surface — search, 입국 전 / 입국 후, core tools,
  support tools, source strip; consistent spacing.
* Journey states at every width: PRE open (chevron up, green underline, one panel), PRE → POST
  switch without a closed flash, second click closes (panel hidden, aria-expanded false).
  Fixed here: the mounted purpose pickers carried colour emoji and a second frame inside the
  civic panel — emoji hidden inside the panel and the mounted section's own frame dropped (one
  box level less; labels, hints and behaviour unchanged).
* Waymaker and New Home: visible in the core tool row at every width (measured), ≥ 44 px.

## FORM HELPER UI

* Desktop and mobile, light and dark: landing, search + hand-off, description, editor with the
  step rail, preview (canvas + sheet), review, export warning dialog, error states.
* Primary action contrast 9.3 : 1 light, 10.3 : 1 dark (measured on every capture).
* Fixed here (dark theme): field warnings were #8b2418 on the dark surface (≈ 1.6 : 1) → #ffb4a9
  (9.7 : 1); native radios ignored the theme, so unselected options showed as filled white dots
  and every option looked chosen → `color-scheme: dark`. Both asserted in the E2E.
* Fixed here (hierarchy): the export warning made "그래도 내려받기" the primary action; "고치기"
  is now primary and focused, exporting anyway stays available.
* The mobile step rail and the preview canvas extend past the viewport by design (horizontal
  scroll / zoom containers); document overflow is 0 on every capture.

## MOBILE

| Viewport | Chromium (captures + text scan) | WebKit (CI `mobile-webkit-qa`) |
| --- | --- | --- |
| 320×568 | pass | — |
| 360×800 | pass | — |
| 375×812 | pass | iPhone SE 375×667: pass |
| 390×844 | pass | iPhone 15: pass |
| 393×852 | pass | iPhone Pro: pass |
| 414×896 | pass | — |
| 430×932 | pass | iPhone Pro Max: pass |
| 768×1024 | pass | — (landscape 844×390: pass) |

Chromium: no horizontal overflow, no hidden CTA (mobile bottom bar visible), sheet and dialogs
inside the viewport, controls ≥ 44 px (mobile matrix). WebKit could not run in the sandbox and
the CI screenshot artifact could not be downloaded (egress policy); the WebKit job asserts
overflow, critical elements in viewport, ≥ 16 px inputs, ≥ 40 px targets, the journey
second-tap collapse and the Form Helper phone flow, and it passed on the reviewed head.

## I18N / RTL

KO, EN, DE, RU, VI, JA, AR inspected on the landing, the open journey and the Form Helper
editor (390 px); the text scan covers all 14 languages at 9 widths.

Fixed here:
* Japanese and Chinese: `word-break: keep-all` (right for Korean) removed every break point, so
  the headline ran 60–177 px off-screen at every phone width and route / tool text overflowed at
  320 and 768. Japanese and Chinese now use normal CJK breaking (strict kinsoku), Japanese
  headings break between phrases (答えが見える / 韓国生活。).
* French cards at 768: long chips and subtitles ran past the card border → chips capped at the
  card width, card text wraps. German at 320: the source-strip label could not wrap.
* The mounted journey pickers left four tile titles in Korean in 11 languages → the missing
  keys were derived from the dictionary's own emoji-prefixed translations (no new wording).
* Result: 0 of 378 page loads with clipped or escaping text; E2E asserts the CJK headline, the
  French cards and a fully translated journey panel.

Arabic: RTL from the first paint, mirrored layout (icons, chevrons, radios, the mobile action
bar), no clipped text, the preview sheet laid out right-to-left. Dialogs were not captured in
Arabic; they use the same logical (inline-start / end) layout as the sheet.

## DOCUMENT PHYSICAL-FORM UI

Inspected: explicit 원본 + 사본 (D-2 passport), explicit 사본 (E-9 permits and contracts),
original-present + copy-submit (E-1 고용계약서 원본 및 사본; 외국인등록증 원본 제시 · 돌려받음 on
the address report, 법 제36조), source-unspecified fallback (재학증명서, 체류지 입증서류 →
원본 지참 권장), passport (원본 지참 · 사본 준비), employment contract (E-7-1: 원본 지참 · 사본
준비, never 제출), lease contract (임대차계약서 among the address-report alternatives).

Official requirements are solid chips with "(원문 표기)" / "(법령 규정)"; recommendations are
dashed chips with "(준비 권장 · 공식 표기 없음)". No recommendation uses 제출; 원본 지참 권장
never renders like an official 원본 제출 rule (`check_document_physical_form.mjs`, 633 checks).

## PRINT-GEOMETRY SANITY

All 24 sample pages and 19 long-text pages: 595 × 841 pt portrait (A4 as the official PDFs
define it), MediaBox = CropBox, rotation 0, page count equal to the template, no scaling, no
added margins — pdf-lib draws onto the unmodified template page. Suitable for 100 % /
actual-size printing.

## CROSS-CHECK

Geometry audit 533 overlays, 0 issues (+ 10 planted defects caught); export verifier on 20
samples and 15 long-text PDFs; Form Helper guard 2 492 checks; template edition audit
(VERIFIED_CURRENT ×14, PENDING_HIKOREA ×1); physical-form 633; i18n 1 446 keys; landing shell
34; E2E on desktop-1280 / mobile-390 / mobile-320: form-helper 33 / 33, landing-boot 42 / 42,
landing-utilities + post-search 36 / 36, search + Quick Answer + language 128 / 128 (+ tablet-768);
mobile matrix identical to the committed table; CI WebKit green. The one contradiction found — the F10 /
F15 values that the audit passed but the image showed touching a label — was investigated: the
audit's overlap threshold ignored a value sitting just beside or under its label; the new
TOUCHES_LABEL rule covers that case and the cells were fixed.

## RESIDUAL LIMITATIONS

* No physical printer was used; print suitability rests on the PDF geometry above.
* WebKit is covered by the CI job's assertions, not by images reviewed here.
* F06 remains PARTIAL (HiKorea edition not comparable); statute templates must be re-checked on
  2027-09-16 (pending amendments).
* Narrow official cells shrink long phone numbers / nationality names to 6.5–7 pt with a
  warning; six-character status codes can overflow the Chinese-edition 희망 자격 bracket (flagged).
* Screens were captured with the search API blocked, so searched pages show the honest
  "통합 검색을 불러오지 못했습니다" line; that fallback is what was reviewed.

## EVIDENCE

`docs/design/screenshots/visual-signoff-20260923/`: `home-320-1280`, `journey-states-320-390`,
`journey-states-768-1280`, `core-tools-waymaker-newhome`, `form-helper-widths`,
`form-helper-light-dark-390`, `form-helper-light-dark-1280`, `i18n-home`,
`i18n-journey-and-editor`, `pdf-F07 / F10 / F15-label-gap-before-after` and `capture-facts.json`
(measured overflow, escaping elements, primary-action contrast and journey state for each of the
125 captures). Regenerate: `node scripts/qa/visual_signoff_20260923.mjs`,
`node scripts/qa/text_overflow_scan_20260923.mjs`, `node scripts/qa/form_long_text_20260923.mjs`,
`node scripts/check_form_helper.mjs` (sample PDFs in `artifacts/form-helper-qa/node-export/`).
