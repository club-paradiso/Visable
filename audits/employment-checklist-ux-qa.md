# Audit — 취업정보 신고용 직종·업종 찾기 checklist UX fix & QA

**Date:** 2026-06-18
**Branch:** `fix/employment-checklist-ux` (builds on PR #442)
**Scope:** Fix the broken/unreliable checklist and make the result flow understandable
to non-expert users, **without** undoing the #442 analyzer architecture, inventing
codes, or making visa-eligibility judgments.

---

## 1. Current checklist implementation summary (before)

The "checklist" was a **static 3-item HTML legend** (`<ol id="jcSteps" class="jc2-steps">`)
with hardcoded `<li>` rows (① 내 실제 일 찾기 / ② 회사·사업장 분야 / ③ 연간소득 구간).
A separate sticky summary (`#jcSummary`) showed the manually-selected occupation/
industry + an income `<select>`. The analyzer interpretation/clarification/tips
(from #442) rendered above the results.

## 2. Reproduction steps

1. Open **🧭 취업정보 신고용 직종·업종 찾기**.
2. Note the 3-step strip never changes.
3. Search `골프장 청소해요` → analyzer interpretation + candidates appear, **but the
   strip is identical** to the empty state; nothing tracks progress.
4. Select a 직종 candidate → only the summary line changes; the strip still implies
   the same "3 steps."
5. Search a vague input (`알바`, `일해요`) → no guided recovery beyond the generic
   empty card.

## 3. Root cause

There was **no checklist state at all** — `#jcSteps` was static markup that never
reflected the analyzer result, selections, clarifications, or the
"공식 코드 확인 필요" state, and it **omitted the HiKorea final-check step**. So it
could not guide the user, could not show what was still uncertain, and visually
implied a fixed "3 steps" that tracked nothing. The income item and the
"candidate-found ≠ confirmed" distinction were not represented.

## 4. UX issues found

- Checklist never updated; implied progress that wasn't real.
- No "내가 하는 일 / 회사·사업장이 하는 일 / 연간소득 / 하이코리아 최종 확인" framing.
- Administrative terms (직종/업종/표준분류/연간소득 구간) shown without plain language.
- Ambiguous results could *look* finished (no "still uncertain" signal).
- Weak inputs (`알바`, `일해요`) dead-ended at a generic empty card.
- All clarification questions could appear at once.
- Candidate cards didn't explain *when* a candidate fits vs when another is better.

## 5. Files changed

| File | Change |
|---|---|
| `scripts/employment_checklist.mjs` | **NEW** — `buildEmploymentChecklistState()` state model + keyed ko/en copy + browser bridge. |
| `scripts/check_employment_checklist.mjs` | **NEW** — 11-area test incl. a real **vm DOM-render smoke** of the index.html render code (447 checks). |
| `index.html` | Dynamic checklist (`#jcChecklist`), one-question-at-a-time clarification, weak-input guided examples, plain-language pane labels, candidate-card "맞는 경우 / 다른 경우" helper, placeholder examples, wiring on search/select/income/clear; CSS. |
| `data/i18n/{ko,en,zh-CN}.json` | `jobCodePlaceholder` examples refreshed (parity preserved, 1059 keys). |
| `scripts/check_employment_reporting_helper.mjs` | Assertions updated for the dynamic checklist + plain-language pane labels. |
| `scripts/check_repo.sh`, `package.json` | Wire `check_employment_checklist.mjs`; add `test:employment-checklist` + `validate`. |

## 6. State model — before / after

**Before:** none (static markup).

**After:** `buildEmploymentChecklistState({ analyzerResult, selectedOccupation,
selectedIndustry, clarificationState, incomeState, sourceStatus,
occupationResultCount, industryResultCount, lang })` → `{ schema, lang, concepts,
steps[4] }`. Each step: `{ id, label, plainLanguageLabel, status, statusLabel,
reason, i18nKey, reasonKey, sourceStatus }` with
`status ∈ pending|ready|needs_confirmation|complete|blocked`.

Stable concepts: `occupationCandidateFound, occupationConfirmed,
industryCandidateFound, industryConfirmed, incomeReminderShown, incomeSelected,
officialCodeVerified, officialCodeNeedsConfirmation, clarificationPending,
hikoreaFinalCheckRequired`.

**Status rules (enforced by tests):**
- candidate-found → `ready`, **never** `complete` (only a user selection → `complete`).
- "공식 코드 확인 필요" → `needs_confirmation`, **never** `complete`.
- a pending clarification holds back **only the track it actually forks**
  (track-aware): `software developer`/`골프장 청소` → occupation `ready`, industry
  `needs_confirmation`; a vessel/factory fork holds both.
- income → `pending` until a user-selected bracket (`complete`), never fabricated.
- HiKorea final check → **never** `complete`.
- no visa-eligibility step exists; the feature never says the work is permitted.

## 7. UI structure — before / after

**Before:** static 3-step legend → search → interpretation/clarification(all)/tips →
two panes (직종/업종) → summary.

**After:** **guided checklist** (4 live steps, status text + icon + colour, plain
language) → search (with field-worker placeholder examples) → interpretation →
**weak-input guided examples** (when truly vague) → **one** clarification question →
two panes labeled "직종 후보: 내가 하는 일에 가까운 항목" / "업종 후보: 회사/사업장이
하는 일에 가까운 항목", each card showing "✓ 이 항목이 맞는 경우 / ↔ 다른 항목이 더
맞을 수 있는 경우" → caution → summary + copy memo.

## 8. i18n changes

Checklist/card copy is centralized in `CHECKLIST_COPY` (keyed, ko+en) in the
checklist module — consistent with #442's ko/en dynamic-copy convention, so the
tx-pack ko/en/zh-CN parity (1059 keys) is untouched. `jobCodePlaceholder` updated
in all three packs. Test #10 asserts every copy key has ko+en; the render smoke
runs in `currentLanguage='ko'` and language switch is covered by test #9.

## 9. Test cases added (`check_employment_checklist.mjs`, 447 checks)

1 initial · 2 high-confidence (ready → complete on select) · 3 ambiguous field-labor
(track-separation: golf forks industry; vessel forks both) · 4 official-code-unverified ·
5 no-signal/weak (blocked) · 6 repeated searches clear stale state · 7 clarification
answered → forked track progresses · 8 selection updates only its track · 9 language
switch keeps structure · 10 every copy key in ko+en · 11 full required-query matrix ·
12 **real DOM render smoke** (renders the actual index.html `renderEmploymentChecklist`
/ `renderEmploymentWeakHelp` in a vm sandbox and asserts the markup).

## 10. Manual QA results for required queries

Checklist legend: `O`=직종 `I`=업종 `$`=연간소득 `H`=하이코리아 ·
`pend/ready/confirm(=needs_confirmation)/done(=complete)/block`.

**Field labor** — all field_labor, 1 clarification, income pending, HiKorea never done:
한치잡이 배 `O:confirm I:confirm`; 골프장 청소 `O:ready I:confirm` (occupation clear,
employer forked); 귤 따요 `O:confirm I:confirm`; 공장 박스 포장 `O:confirm I:confirm`;
수산물 공장 손질 `O:confirm I:confirm`; 리조트 객실 청소 `O:confirm I:ready`; 식당 설거지
`O:ready I:confirm`. Tracks stay separate.

**Ambiguous** — 일해요 `0/0` → weak guided examples; 알바 `5/0`; 공장/청소/배 →
field_labor with candidates + one clarification (not a dead end); 회사 다녀요
`O:block I:ready`.

**Arts/ent** — 댄서/아이돌 연습생/K-pop trainee/타투이스트/유튜버 → entertainment/
service, one clarification, never complete; K-pop trainee `0/0` → "공식 코드 확인 필요".

**Pro/svc** — English teacher `O:ready I:ready` (no clarification); software developer
/researcher/translator/barista `O:ready I:confirm` (occupation clear, employer
forked); hotel front desk `O:confirm I:ready`.

Verified for each: occupation/industry separate, ≤1 clarification at a time,
ambiguous never complete, "공식 코드 확인 필요" never complete, income reminder shown,
**no visa-eligibility judgment**, plain-language copy.

## 11. Existing validation results

`npm run validate` (`scripts/check_repo.sh`, 14 sections) → **exit 0, all regression
checks passed**, including: employment dataset, reporting-helper UI, analyzer (51),
mode suites (504), source audit, **checklist (447)**, i18n parity (1059×3),
static-i18n, hardcoded-text, dummy-text, ai-shell semantics.

## 12. Remaining risks

- A factory with an unspecified product still yields broad 업종 candidates (#442
  limitation) — surfaced via the manufacturing↔logistics / product clarification and
  the industry step's `needs_confirmation`, not hidden.
- The live keyword-filter path (typing without Enter) is for browsing the official
  lists and intentionally does not rebuild the checklist; the assistant flow (Enter /
  AI button / multi-word chips) does.
- Income bracket labels remain `unverified` (HiKorea is authoritative) — the income
  step always says to confirm on HiKorea and is never auto-completed.

## 13. Follow-up recommendations

- Persist failure logs (PR #442 `createFailureLogger`) to mine weak-input examples
  and add aliases.
- Consider a track-aware clarification hint emitted by the analyzer itself (today the
  checklist maps the top question's flag/topic → tracks) if more fork types are added.
- Verify live HiKorea income brackets and flip `income_brackets.source_status`.
