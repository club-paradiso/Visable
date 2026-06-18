# Audit — 취업정보 신고용 직종·업종 찾기: Toss-inspired guided UX

**Date:** 2026-06-18
**Branch:** `fix/employment-finder-toss-inspired-ux` (builds on #442 analyzer + #443 checklist)
**Scope:** Make the feature feel like a friendly guided assistant — plain words,
focused cards, one decision at a time, mobile-first — **without** rewriting the
#442 analyzer, mixing occupation/industry, inventing codes, or making visa
judgments.

---

## 1. Current UX problems (before)

Technically strong but hard to use: a search box wrapped in administrative
controls (전체/직종만/업종만, 세부코드만), a long stack of result sections, bureaucratic
labels (표준직업분류/표준산업분류), an entity-grid interpretation titled "입력 내용 해석",
all candidates shown at once (up to 60 cards), and an at-a-glance checklist whose
status words ("대기", "확인 필요") read as system states rather than next actions.
The "공식 코드 확인 필요" state used a warning-bordered message that read as an error.

## 2. Observed pain points / assumptions

Non-expert users could not tell **what 직종 vs 업종 mean**, why they're separate,
**what to do next**, whether Paradiso's answer is final, or what HiKorea still
needs. The first screen offered no plain "what do you do?" prompt or natural
example inputs. Uncertainty was shown in a slightly scary way; mobile users faced
long scrolling result lists before reaching the clarification.

## 3. UX redesign summary

A Toss-style guided flow, reusing the #442 analyzer and #443 checklist state model:
- **Friendly landing:** "어떤 일을 하나요?" + helper copy + natural-language example
  chips (골프장 청소해요 / 한치잡이 배에서 일해요 / …) that run the analyzer.
- **Plain-language explainer** (expandable): "직종은 ‘내가 하는 일’, 업종은 ‘회사나
  사업장이 하는 일’이에요." with a golf example behind a `<details>`.
- **Interpretation first:** "이렇게 이해했어요" — 일하는 곳 / 대상 / 하는 일 / **더 확인할 점**
  (built from the clarification's options, so uncertainty is concrete and gentle).
- **One question at a time:** large tap-friendly answer buttons + a **"잘 모르겠어요"**
  escape that keeps both possibilities without forcing a choice.
- **Guided stepper** (4 steps) with action-style status labels, placed after the
  clarification.
- **Separated candidates** with a **top recommendation vs alternatives** model:
  "가장 가까운 후보" + "다른 가능성" when confident, "몇 가지 가능성이 있어요" when ambiguous
  (no false certainty). Each card shows a **confidence** chip + **공식 분류 코드** badge
  + short reason + "이 항목이 맞을 수 있는 경우", with the longer caveat behind "자세히 보기".
- **Top 2 visible, rest behind "더 보기"** (mobile-friendly).
- **Gentle "공식 코드 확인 필요"** card with two soft actions (다른 표현으로 다시 검색 /
  통계분류포털에서 확인).
- **Income reminder** card + advanced code-browsing filters collapsed under "🔧 직접 코드 찾기".

## 4. Before / after flow

**Before:** hero → static checklist → search + filters + 14 keyword chips → notes →
entity-grid interpretation → weak help → all clarification questions → all candidates
(≤60 each) → tips → disclaimer → sticky summary.

**After (mobile order):** ask heading + search → concept explainer → example chips →
analyze → **이렇게 이해했어요** → **one** clarification (large buttons + 잘 모르겠어요) →
**stepper (4 steps)** → 직종 후보 (top + alternatives, top 2 + 더 보기) → 업종 후보 →
**연간소득 reminder** → tips → disclaimer → sticky summary. Advanced filters collapsed.

## 5. Checklist / stepper state model

Unchanged engine (`buildEmploymentChecklistState`, #443) — only the status **labels**
became action-oriented and the HiKorea step shows an action label:

| status | before | after |
|---|---|---|
| pending | 대기 | **아직 필요해요** |
| ready | 후보 찾음 · 선택 필요 | **후보를 찾았어요** |
| needs_confirmation | 확인 필요 | **확인이 필요해요** |
| complete | 선택 완료 | **선택했어요** |
| blocked | 입력 보완 필요 | **조금 더 알려주세요** |
| hikorea (any) | (status label) | **하이코리아에서 확인해 주세요** |

Rules preserved: candidate-found ≠ complete; 공식 코드 확인 필요 ≠ complete; ambiguous
holds the **forked track(s) only** (occupation/industry stay separate); income
pending until a user selection; HiKorea final check **never** complete; no
visa-eligibility step.

## 6. Candidate card changes

Added a **confidence band** (가장 가까움 / 비슷함 / 가능성 있음, relative to the top
candidate) and a **✓ 공식 분류 코드** source badge. Default view = code + type badge +
confidence + (🎯 신고용 세부코드) + name + level/source + short reason + "이 항목이
맞을 수 있는 경우". **Progressive disclosure:** "다른 항목이 맞을 수 있는 경우" + the full
classification path move behind "자세히 보기". Grouping: top card under "가장 가까운 후보",
the rest under "다른 가능성" (or all under "몇 가지 가능성이 있어요" when the analyzer is
still clarifying). Only the top 2 show; the rest collapse behind "더 보기 (N)".

## 7. Weak-input fallback changes

Unchanged trigger (#443: no candidates AND no concrete splitter, non-sensitive) but
the example set and copy are the friendly guided ones (카페에서 음료 만들어요 / 공장에서
부품 조립해요 / 호텔 객실 청소해요 / 학원에서 영어 가르쳐요), each rerunning the analyzer.
The no-code case is now a **reassuring card** ("입력하신 업무는 해석할 수 있지만…") with
soft actions, not a warning-bordered error.

## 8. Mobile changes

Recommended stack order implemented (search → interpretation → clarification →
stepper → 직종 → 업종 → income → HiKorea via the checklist). Top 2 candidates + 더 보기;
result lists drop their max-height/scroll on ≤520px so they don't nest-scroll; tap
targets ≥44px (answers, select, 더 보기, chips); `min-width:0` + `overflow-wrap:anywhere`
guard against horizontal overflow; advanced filters collapsed to cut clutter.

## 9. i18n changes

- Static chrome added to the tx packs (ko/en/zh-CN, parity 1066): `jobCodeAskHeading`,
  `jobCodeAskHelper`, `jobCodeConceptExplain`, `jobCodeConceptExpand`,
  `jobCodeExamplesLabel`, `jobCodeIncomeReminderTitle`, `jobCodeIncomeNote`.
- Dynamic guided copy added as keyed **ko/en** entries in `CHECKLIST_COPY`
  (interpret.\*, clarify.dunno, conf.\*, group.\*, card.source/detail, more.\*,
  needcode.\*, status.hikorea) — consistent with #442/#443's dynamic-copy convention;
  zh-CN falls back to ko like the rest of the analyzer output. Every key asserted
  present in ko+en by the test.

## 10. Files changed

| File | Change |
|---|---|
| `index.html` | Hero ask heading + explainer; friendly example chips; collapsed advanced filters; relocated stepper; reframed interpretation ("이렇게 이해했어요" + 더 확인할 점); large-button clarification + 잘 모르겠어요; card confidence/source/progressive-disclosure; top-recommendation grouping + 더 보기; gentle no-code card; income reminder; applyI18n wiring; CSS. |
| `scripts/employment_checklist.mjs` | Action-style STATUS labels; HiKorea action label; ~30 new keyed ko/en copy entries. |
| `data/i18n/{ko,en,zh-CN}.json` | 7 static modal keys (parity preserved). |
| `scripts/check_employment_checklist.mjs` | Updated status-label assertions; extended DOM-render smoke (interpretation title, clarification answers + 잘 모르겠어요, candidate grouping + confidence + source + 더 보기). |
| `scripts/check_employment_reporting_helper.mjs` | Example-chip + plain-label assertions updated to the redesign. |
| `audits/employment-finder-toss-inspired-ux.md` | This report. |

## 11. Tests run

`npm run validate` (`scripts/check_repo.sh`, 14 sections) → **exit 0, all regression
checks passed**, including: employment dataset, reporting-helper UI, analyzer (51),
mode suites (504), source audit, **checklist (457, incl. DOM-render smoke)**, i18n
parity (1066×3), static-i18n, hardcoded-text, dummy-text, ai-shell.

## 12. Manual QA results (required queries)

`O`=직종 `I`=업종 `$`=소득 `H`=하이코리아 · `ready / check(=needs_confirmation) / done / block / pend`

**Field labor** — all field_labor, 1 clarification, income pending, H never done,
grouping "몇 가지 가능성이 있어요": 골프장 청소 `O:ready I:check` (occupation clear, employer
forked); 식당 설거지 `O:ready I:check`; 리조트 객실 청소 `O:check I:ready`; 한치/귤/공장 박스/
수산물 손질 `O:check I:check`.

**Ambiguous** — 일해요 `0/0` → weak guided examples; 알바 `5/0`; 공장/청소/배 → field with
candidates + 1 clarification (not a dead end); 회사 다녀요 `O:block I:ready`, no
clarification → "가장 가까운 후보".

**Arts/ent** — 댄서/아이돌 연습생/타투이스트/유튜브 → 1 clarification, never complete;
K-pop trainee `0/0` → 공식 코드 확인 필요 card.

**Pro/svc** — English teacher `O:ready I:ready`, no clarification, "가장 가까운 후보";
software developer/researcher/translator/barista `O:ready I:check`; hotel front desk
`O:check I:ready`.

Every query verified: interpretation explains the input, 직종/업종 separated, ≤1
clarification at a time, weak inputs show examples, ambiguous never complete, 공식
코드 확인 필요 visible and never complete, income reminder present, **no visa
eligibility judgment**, ko/en copy clean. DOM-render smoke confirms the actual
index.html render code produces the interpretation title, large answer buttons + 잘
모르겠어요, and the grouped/confidence/source candidate markup.

## 13. Remaining risks

- A factory with an unspecified product still yields broad 업종 candidates (#442
  limitation) — surfaced via the manufacturing↔logistics clarification + the industry
  step's `확인이 필요해요`, not hidden.
- Desktop keeps a single column (two-column side-stepper was optional; deferred to
  avoid density risk inside the 860px modal). The stepper sits inline above the
  candidates on all widths.
- The live keyword-browse path (typing without Enter / advanced filters) intentionally
  doesn't run the guided grouping; the assistant flow (Enter / AI button / example
  chips) does.
- Income bracket labels remain `unverified`; the reminder always defers to HiKorea.

## 14. Follow-up recommendations

- Optional desktop two-column layout (main: interpretation/clarification/candidates;
  side: sticky stepper) for very wide screens.
- Persist failure logs (#442 `createFailureLogger`) to mine weak inputs and add aliases.
- Verify live HiKorea income brackets and flip `income_brackets.source_status`.
- Consider screenshot-based visual regression for the modal once a browser harness exists.
