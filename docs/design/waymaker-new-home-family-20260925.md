# Waymaker + New Home — product-family redesign (2026-09-25)

Base: `main` @ `d12fd9b` (Unify Visable search results… #635).
Scope: `ai.html` (Waymaker) and `new-home.html` (New Home). Visable landing,
Form Helper and the nationality-interview hub are unchanged (pixel-identical
screenshots against `main`, light and dark).

Screenshots: `docs/design/screenshots/waymaker-new-home-20260925/`.
QA script: `scripts/qa/waymaker_new_home_visual_qa.mjs`.

## 1. Problems verified before the change

Captured on `main` in Chromium (light/dark, 390 and 1440, Pretendard loaded):

| Surface | Verified problem |
|---|---|
| Both | Neither page used the live Visable palette (`--cs-*`: white paper, `#214f43` ink-green, `#10221c` dark). Waymaker defaulted to a dark teal console even for a first visit from the light Visable landing; New Home used a cream/coral palette. |
| Both | No shared chrome: Waymaker had a "메인 화면으로 돌아가기" button plus a two-line title; New Home had "← Visable" pill, `EN`, `Editorial` and a `◐` glyph (rendered as `‹` without the font). Neither showed the Visable wordmark. |
| Both | ~2,000 lines of layered overrides: 1,465-line inline `<style>` in `ai.html`, 570 lines in `new-home.html`, ~780 lines of page-scoped rules (≈400 `!important`) in `visable-product-2026.css`. |
| Waymaker | 390px: the fixed composer (dark box + full-width mint "전송") covered the welcome copy; the mode rail collapsed into a clipped horizontal strip ("서식·제출서류" cut off). |
| Waymaker | Light mode carried dark-mode colours: mint send button, dark composer rim, periwinkle serif "waymaker." wordmark; emoji mode labels (⚡ Fast / ⚖️ Basic). |
| Waymaker | `?nav=1` light: the primary button was dark ink on dark green (unreadable). |
| Waymaker | Long answers scrolled to their **end** on arrival; the reader had to scroll back up. |
| Waymaker | `?domain=nationality`: subtitle, starter chips and placeholder were hard-coded Korean (English UI showed Korean), were reset to the generic visa chips after the first question, and one interview chip broke its `data-chip-text` attribute (unescaped `"`). |
| Waymaker | Context strip values ("질문에서 자동 감지"…) were Korean-only in `waymaker-workspace.js`. |
| New Home | Card soup: 8 equal feature cards with letter tiles, boxed stepper + 5 boxed steps, 10 boxed checklist items, 16 boxed source cards, gradient banners. Page height 9,822px desktop / 17,593px mobile. |
| New Home | Decorative motion with no function: an endless marquee strip and four "aurora dots" that read as carousel pagination. |
| New Home | Skip link used `.sr-only`, so it never became visible on focus. |
| New Home | Dark visitors saw a light flash: brightness was applied only after the four content JSON files loaded. |

## 2. Design system decisions

* **One palette.** `visable-product-2026.css §13` sets the `--vp-*` tokens for
  both products to the values the Visable landing ships (`--cs-*`), light and
  dark, plus Editorial-pop (`archive_diary`). Legacy aliases (`--bg*`, `--t*`,
  `--ac*`, `--bd*`) are mapped once there because the procedure navigator,
  legal-source search and New Home renderers still read them. No new token
  family was introduced.
* **One chrome.** `.vf-bar` (family bar): Visable wordmark → home, hairline,
  product name, the product's own controls. 64px desktop / 56px phone; below
  380px the wordmark becomes the Visable mark so the product name never
  truncates.
* **Shared grammar:** Pretendard, 780-weight display type with −0.045em
  tracking, hairlines instead of boxes, soft mint circles for icons, pill
  chips, 12px-radius primary buttons, 3px green focus outline, 44px minimum
  targets, 12px minimum text.
* **Distinct jobs:** Visable = centred search (find). Waymaker = rail +
  one reading column + docked composer (analyze). New Home = left-aligned
  editorial arrival with a warm light and a journey index (navigate).
* **CSS ownership:** `waymaker-workspace.css` owns `ai.html`; the new
  `new-home.css` owns `new-home.html`; both pages keep zero inline CSS and no
  colour `!important` (only three functional `display:none !important` mode
  switches remain in Waymaker).

## 3. Waymaker

* Family bar; quota shown as "오늘 N회 남음" (localized template); theme icon
  button shows the mode it switches to.
* Rail (≥1024px): three in-product modes with one-line explanations —
  AI 상담 / 절차 찾기 / 법령·판례 찾기 — then "다른 도구" (서식 작성,
  귀화면접 연습) and the source-transparency note. Plain-language labels
  replace ASK/PLAN/SOURCES kickers.
* Welcome: kicker + reference chip, display heading (brand line), the same
  three-part explanation, example questions, then a dominant composer centred
  as one block with the aurora (welcome only, static).
* Composer: one bordered box, 17px text, mode segmented control, counter and
  an icon+label send button inside; status, detection hint and the legal
  disclaimer below. The context strip appears once the visitor types.
* Conversation: aurora off; user turns as compact mint notes; answers as one
  document surface — head (kicker, model, grounding badge), Standard/Easy,
  context, notes, body (68ch measure), status chips, evidence register with
  per-row state labels, actions, closing disclaimer. New answers scroll to
  their first line; the placeholder becomes "이어서 질문하기…".
* Navigator and research reuse the column and tokens; primary buttons fixed
  to readable contrast in light/dark/pop; module controls raised to 44px.
* Phone/tablet (<1024px): document scroll, a three-segment mode control under
  the bar, welcome keeps the composer in flow; in conversation the composer is
  `position: sticky` with `env(safe-area-inset-bottom)` (static on landscape
  phones ≤480px tall). Outbound tools move to a "다른 방법으로 시작" list.
* Light is the default (as on Visable); dark follows the stored choice.
* i18n: all new chrome strings live in `SHELL_CHROME` (ko/en/zh, zh-TW via the
  existing converter); nationality-mode hints and the workspace context strip
  are now localized too.

## 4. New Home

* Family bar with the Visable language control (code badge + native name),
  icon style toggle (current style in the tooltip/hidden label) and brightness.
  Sticky in-page navigation marks the section being read (`aria-current`).
* Arrival: left-aligned kicker, title, "Welcome home.", lead, one primary CTA
  (준비 상태 확인), Visable as a text link, three checked facts, footnote. The
  marquee and fake pagination dots are removed; the warm light stays behind
  the right side only.
* "무엇을 도와드릴까요?": two starting points (readiness check, path finder)
  as the only cards; the six guides/tools as a hairline index.
* Journey band, KIIP, after-approval checklist (two columns), nationality
  centre (grouped index with chevrons), then the next steps: Waymaker hand-off
  and interview prep as Visable-style tool rows, the caution note, and the
  official-source register (two columns). Every official-source warning,
  disclaimer, flag and caution from the data is still rendered.
* Dialogs: family sheet on phones (bottom, 92dvh, safe-area footer), 52px
  options, focus/Escape behaviour unchanged.
* Height: 8,844px desktop / ~15,000px phone (from 9,822 / 17,593) with no
  content removed.

### Source-trust rule (added in review)

"공식 출처로 확인 / Check official sources" is an instruction to the reader,
not a certification. The badge is a neutral text pill — no check glyph, seal,
shield or accent fill. The same reading applies to nearby cues: the hero's
"공식 출처 표기" fact has no check mark (plain middot list), Waymaker's
"공식 매뉴얼 근거" grounding badge has no check, and the after-approval items use
a to-do square rather than a green check circle.

`scripts/check_official_external_sources.mjs` now enforces this on the
effective presentation — `new-home.html` (markup and any inline `<style>`)
plus every local stylesheet it links, including `assets/css/new-home.css` —
and fails if a `::before/::after/::marker`, a check/seal glyph (literal or
CSS escape) or a verification icon is attached to `.nh-official-badge`, or if
the page stops linking its stylesheet. The previous guard only searched
`new-home.html` and went blind once the CSS moved out; it was mutation-tested
after the fix (inline style, `\2713` in new-home.css inside `@media`, an icon
background in the shared sheet, an SVG inside the badge — all four fail).

## 5. Accessibility

Skip links first in tab order on both pages (New Home's now visible); logical
tab order (skip → home → controls → modes → content); visible 3px focus on
every control; `aria-current` on the active mode and section; ≥44px targets
and ≥12px text across the matrix; WCAG AA text contrast measured in every
state (two Editorial-pop failures found and fixed); reduced motion disables
message fade-in, journey drawing and hover motion; no colour-only states
(evidence rows keep their text labels; "helps with / won't claim" keep ✓/✕;
source flags keep a "!" caution mark).

## 6. QA method

`scripts/qa/waymaker_new_home_visual_qa.mjs` drives both pages across
320×568 … 1920×1080 (incl. 844×390 landscape and 1024×768), light/dark,
Editorial-pop, ko/en and de/ru/vi/id/ar/ja/zh-CN; states: Waymaker welcome →
typed → mocked conversation → research, `?nav=1` intro/step, consent dialog;
New Home landing, hand-off, readiness, path-finder result, hub detail,
language menu. It fails on page overflow, overflow masked on `html/body`,
inner scroll-container overflow, hidden critical controls, targets <44px,
text <12px, clipped labels, AA contrast, dialogs outside the viewport, and
state-contract breaks (aurora, sticky composer, focus restore, hand-off href).

Final run on the committed code: **264 state × viewport × theme × locale runs,
0 failures** (`screenshots/waymaker-new-home-20260925/qa-report.md`). Earlier
runs of the same script found and drove the fixes for: 11.5px journey labels
at 320px, 36–40px mode/tab targets, a truncated product name at 320px, a
floating language note covering the hero, two Editorial-pop contrast failures,
the composer below the first screen at 360×800 in English, and a zero-
specificity mistake that recoloured the consent button's label.

## 7. Known limits (not regressions)

* The Waymaker chrome is localized in ko/en/zh only (as before); other
  locales fall back to Korean chrome. New Home content likewise covers
  ko/en/zh with the existing "not yet translated" notice.
* Evidence-row state labels (SOURCED, PARTIAL, …) remain English CSS content,
  as before.
* In this sandbox the Pretendard CDN is blocked, which makes the two New Home
  e2e tests fail on a console error on `main` as well; with the font served
  locally both pass on all six projects.


## 8. Product wordmarks restored from Figma (2026-09-25)

The product-family chrome had regressed from the canonical script wordmarks to plain text product names. The live surfaces now use the existing Figma design-system components as the source of truth:

- New Home: `Logo / New Home Wordmark`, node `203:13`
- Waymaker: `Logo / Waymaker Wordmark`, node `204:13`
- Figma file: `pInhK8Oyg04lpL4PMSCB4l`
- Light fill: `#7F89CE`
- Dark instance fill: `#9BA3E8`, exactly as documented on both Figma components
- New Home hero size: 260×52, matching MASTER `194:5`
- Waymaker hero size: 206×60, matching MASTER `198:5`

The family bar now uses the same canonical product wordmarks at compact sizes, while the Visable wordmark remains the home link. The arrival/welcome block also restores the larger Figma wordmark above each product headline. Local SVG files are committed under `assets/brand/`; no temporary Figma asset URL is used at runtime.

Both the full visual-QA script and the landing Playwright regression now verify that the wordmark is visible and that the SVG actually loads, so a future text-only or broken-asset regression fails CI instead of quietly shipping.
