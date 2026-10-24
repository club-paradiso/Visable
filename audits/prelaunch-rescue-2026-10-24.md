# Pre-launch rescue — 2026-10-24

Branch `fix/prelaunch-rescue` (from `main` @ `5e0545a`). Evidence screenshots live in
`audits/prelaunch-rescue-2026-10-24/`. Release decision at the end.

## 1. Executive summary

The reported defects were reproduced from the iPad screenshots of `F-4 체류기간 연장` and
traced to three root causes: (1) the home catalogue shipped expanded in both the static
shell and the hydrated render; (2) a tablet-only header grid that stretched the language
control across a column; (3) a source-only answer (no structured F-4 extension rule in
the guidance bundle) that was rendered with the same section stack as a full answer,
so a conditional special scheme, an unscoped fee-exemption list and six open evidence
records read as the answer. Each was fixed at its cause, with regression coverage:

- Tools directory collapsed by default, native disclosure, header link mirrors state,
  `#csTools` deep link still expands it, language change keeps an expansion.
- Language control is 44px wide at every width from 320 to 1440 (was 590px at 820).
- Result pages now open with identity → primary source action → an "at a glance"
  overview derived from the model (confirmed / depends on your case / check in the
  source) → cost → special schemes as a collapsed, conditional block → labelled action
  rows → evidence with the procedure's own page first and fee law behind a disclosure.
- Search fixes: "A에서 B 변경" without 으로 answers for B; unknown codes (`Z-9`, `F-99`)
  are named instead of dropped; two-code comparison questions hand off to Waymaker;
  Rule Art. 74 exemptions are scoped to the statuses the rule names.
- Edition copy that still said "September 2026" (English and 12 other locale packs,
  quick-answer note, three guidance strings) now follows the bundle edition (October 2026).
- Accessibility: one `<main>` per state, a page `<h1>` on result pages, Waymaker aside is
  a region; axe (WCAG 2.x A/AA + best-practice) is clean on home and result pages at
  390/820/1280 after the fixes.

## 2. Root causes

| # | Symptom (screenshot) | Root cause | Files |
|---|---|---|---|
| 1 | Catalogue open on every visit | `directoryHtml()` emitted `<details … open>`; the static shell is generated from it; the reliability check asserted `open === true` | `assets/js/civic-search.js`, `index.html` (generated), `scripts/check_search_tools_reliability.mjs` |
| 2 | 590px-wide "KO" pill on iPad | `visable-mobile-iphone-20260904.css` turns the searched header into a 2-column grid ≤820px; the language button became a stretched grid item; the absolute-position escape only applied ≤680px | `assets/css/civic-search.css` |
| 3 | "구조화된 안내가 아직 없어요" + long stack | F-4 extension is `SOURCE_ONLY` in `data/status-guidance-202609.json` (p.537 of the stay manual, no structured rule). `renderSourceOnly()` still rendered programs, fees, next and open evidence in the full-answer order | `assets/js/status-guidance.js` |
| 4 | H-2/F-4 통합 shown as a rule that "applies" | `renderPrograms()` printed the scheme attached to the F-4 code with the universal note "아래 조건이 추가로 적용돼요" above the fee | `assets/js/status-guidance.js` |
| 5 | "면제·감경 조건 · 2" on F-4 | the A-1~A-3/D-8 and government-invited D-1/D-2/D-4 exemptions had `scope: null` although the quoted rule names those statuses | `scripts/status_guidance/author_rules.py` → regenerated bundle |
| 6 | Six verbose evidence records | fee-law records (Rule 72/73/74, fee pages) were mixed with the procedure page in one open list | `assets/js/status-guidance.js` `evidenceFor()` / `renderEvidence()` |
| 7 | "2026년 9월판 원문은…" on an October edition | hard-coded month in `evidenceReview`, `unknownCode`, `disclaimerDetail`, quick-answer `unc.review`, and the civic `sourceNote/pendingInfo/unknownCode` strings in 13 locale packs | `status-guidance.js`, `waymaker-quick-answer.js`, `civic-search.js`, `data/i18n/*.json` |
| 8 | "D-2에서 D-10 변경" answered for D-2 | `interpret()` only detected the target with a 으로/→/to marker | `assets/js/status-guidance.js` |
| 9 | "Z-9 연장" silently treated as "연장" | code grammar only accepts A–H; unmatched shapes were dropped | `assets/js/status-guidance.js`, `assets/js/search-suggest.js` |
| 10 | Two `<main>` landmarks on home; no `<h1>` on result pages; `<aside>` inside main | legacy `#mainContent` stays a `<main>` under the civic shell; guidance heading was an sr-only `<h2>`; Waymaker block was an aside | `civic-search.js`, `status-guidance.js` |

Verified, not changed: the ₩60,000 extension fee (Enforcement Rule Art. 72, quote in the
bundle: "체류기간 연장 허가 6만원(F-6 3만원)"), the 20% online reduction (Art. 74(2); F-4 is
not in the electronic-filing exclusion list in the bundle), and the F-4 extension page
reference (stay manual 2026-10-19, p.537). No legal text was added or removed.

## 3. Implementation record

Phase 1 (`d44d794`): collapsed directory, header-link toggle with `aria-expanded`/
`aria-controls`, `hashchange` → expand, language re-render keeps expansion; tablet
language-control CSS; `tests/e2e/tools-directory.spec.mjs` (20 cases × 4 projects).

Phase 2 (`b1cd1e3`, `d788e85`): A에서 B 변경 target inference + current-status
pre-answer; unknown-code reporting (resolver + suggestion note); comparison routing;
exemption scopes (bundle regenerated with `npm run build:status-guidance`); router
checks extended (+3); catalogue-filter e2e opens the directory first.

Phase 3 (this commit): overview section, conditional scheme disclosure, grouped
evidence, action rows, source-first fallback, reading width 820px, edition labels from
the bundle, landmark/heading fixes, F-4 phone band hidden while the structured answer
owns the page; `scripts/check_result_hierarchy.mjs` (wired into
`test:search-waymaker`) and `tests/e2e/result-hierarchy.spec.mjs`.

## 4. Before / after

| View | Before | After |
|---|---|---|
| F-4 extension, iPad portrait 820 | `before-f4-extension-ipad-820.png` | `after-f4-extension-ipad-820.png` |
| F-4 extension, phone 390 | `before-f4-extension-phone-390.png` | `after-f4-extension-phone-390.png` |
| Home, iPad 820 (directory) | `before-home-ipad-820.png` | `after-home-ipad-820.png` |
| F-4 extension, iPad landscape 1180 | — | `after-f4-extension-ipad-landscape-1180.png` |
| D-2 extension, desktop 1280 | — | `after-d2-extension-desktop-1280.png` |
| Unknown code `Z-9 연장`, phone | — | `after-unknown-code-phone-390.png` |
| F-4, phone, Arabic (RTL page, LTR guidance) | — | `after-f4-extension-phone-390-arabic.png` |
| F-4, phone, dark face | — | `after-f4-extension-phone-390-dark.png` |

## 5. Search QA matrix (router → resolver → renderer, Node)

| Query | Expected | Observed after | Note |
|---|---|---|---|
| F-4 체류기간 연장 | STATUS_PROCEDURE, extension, source-only | ✓ source-only; fee ₩60,000 verified; scheme collapsed; p.537 primary | no structured F-4 rule exists (data gap, flagged) |
| F-4 연장 서류 | same, documents facet | ✓ same; overview says documents are in the source | |
| F-4 수수료 | ask the procedure (fee depends on it) | ✓ "F-4에서 무엇을 하려고 하세요?" | acceptable; fee differs per procedure |
| F-4와 F-5 차이 | comparison → Waymaker | ✓ complex/comparison (was: question about F-4) | fixed |
| H-2에서 F-4 변경 | status_change, target F-4 | ✓ (was: STATUS_ONLY H-2) | fixed |
| D-2 체류기간 연장 | resolved, 6 required + 1 conditional docs | ✓ | |
| D-2에서 D-10 변경 | status_change, target D-10 | ✓ (was: STATUS_ONLY D-2) | fixed; D-10 status change is source-only (p.147) |
| E-7 근무처 변경 | workplace_change, fee ₩120,000 | ✓ source-only; only the report-not-permit exemption | |
| F-6 체류기간 연장 | subtype question (F-6-1/2/3) | ✓ | |
| G-1-5 관련 절차 | exact subcode, ask which procedure | ✓ G-1-5 stays under G-1 | |
| 주소 변경 신고 | status-independent common rule | ✓ 3 documents, no fee item | |
| 외국인등록증 재발급 | common rule, ₩35,000 | ✓ | |
| Visa extension documents | need-status | ✓ | |
| Change of status from D-2 to D-10 | status_change D-10 | ✓ | |
| Z-9 연장 / F-99 체류기간 연장 | unknown code named | ✓ warning + need-status (was: silent) | fixed |
| 서류가 뭐예요? | transparent fallback | ✓ no-status with common tasks | |

## 6. Accessibility

Automated: axe-core 4.10 (wcag2a/aa, wcag21a/aa, wcag22aa, best-practice) on home,
home with the directory open, F-4, D-2 and an unknown-code result at 390/820/1280.
Before: `landmark-no-duplicate-main` + `landmark-unique` (home), `page-has-heading-one`
and `landmark-complementary-is-top-level` (results). After: see §7.

Manual (Playwright, Chromium): keyboard Enter/Space on the directory summary; focus
returns to the source button after the page dialog closes; one h2 then h3s in the
result; 44px+ targets for every action row and the language control; no horizontal
overflow at 320–1440; dark face and Arabic (RTL page, LTR guidance block) render the
same structure. Not verified here: VoiceOver/real iPad Safari (no WebKit runtime in this
container; CI's `mobile-webkit-qa` job covers WebKit on pull requests).

## 7. Regression results

See the PR description for the exact commands and outcomes (filled from the final run).

## 8. Deployment

`visable-mu.vercel.app` is the production alias of Vercel project `visable`
(`prj_1HDLkkF74AwSj3bvHB6xQIATeXL5`, team `club-paradiso`). Production deployment
`dpl_4rz6P7CbUyhYWQidgaRNQBSwtrEg` serves `main` @ `5e0545a` ("test(e2e): use promoted
2026-10-19 visa manual source"). Nothing from this branch is deployed; the PR builds a
preview.

## 9. Remaining items / continuation plan

1. F-4 extension (and status change, registration, card reissue) have no structured
   rule in the guidance bundle — the page is honest about it, but authoring the F-4
   chapter (stay manual p.531–553) in `scripts/status_guidance/author_rules.py` is the
   real fix. Same for E-7 근무처 변경 and D-10 체류자격 변경.
2. The 2026-10-19 manual text is still `needs_review`; every page says so.
3. Checklist copy in `immigration-checklists.js` / `visable-i18n.js` still cites the
   "2026년 9월" manual — that product compiles from its own data and was left as is;
   confirm its basis and update together.
4. Real-device Safari pass (iPad portrait/landscape, VoiceOver) before release.
5. The legacy per-status card and the F-4 route guide remain reachable from
   "기존 체류자격 카드 보기"; consider folding the route guide into the action list.
