# Audit — 취업정보 신고용 직종·업종 찾기: guided-flow redesign

**Date:** 2026-06-18
**Branch:** `fix/employment-guided-ux-redesign` (builds on merged #442 analyzer, #443 + #445 UX)
**Scope:** Restructure this feature into a step-by-step guided flow with progressive
disclosure — interpretation → one question → candidates → final HiKorea checklist —
**without** rewriting the analyzer, mixing 직종/업종, inventing codes, or making visa
judgments.

---

## 1. Why the previous UI was hard to use

After #445 the feature was friendlier (interpretation card, one-question clarification,
weak-input examples, separated candidates), but it still rendered **everything at once**:
the interpretation, the clarification, both candidate panes, the income reminder and the
checklist all appeared together after a search. On mobile this is a wall of content —
the user can't tell what the single next action is, and the candidate list reads as a
"result dump" even when the analyzer is still unsure which fork applies.

## 2. User pain points

1. "What do I do after I search?" — no single, obvious next action.
2. 직종 vs 업종 still blurred when both panes appear simultaneously with a pending question.
3. "Why is official-code confirmation needed?" — shown but easy to miss in the stack.
4. "What do I finally check in HiKorea?" — the sticky summary is a copy tool, not a clear
   end-of-flow checklist.

## 3. New guided flow (state machine)

A new `employmentFlowState()` (pure, in `scripts/employment_checklist.mjs`) drives
**progressive disclosure**:

| state | when | what shows |
|---|---|---|
| `idle` | before search | ask heading + example chips + search (candidates area shows the browse/empty prompt) |
| `analyzing` | during analysis | loading |
| `needs_clarification` | a fork question is pending **and** there are candidates to gate | interpretation + **one** large-button question; candidates **held** behind a gate ("그냥 후보 보기"); income/final-check hidden |
| `showing_candidates` | no question, or it was answered / dismissed / revealed, or there are no candidates to gate (weak input) | 직종 후보 → 업종 후보 → 연간소득 reminder → **Step 5 final HiKorea checklist** |

The gate never dead-ends: answering the question, choosing **"잘 모르겠어요"**, or
**"그냥 후보 보기"** all reveal candidates (the latter two keep both possibilities and
leave the fork unresolved → checklist stays `확인이 필요해요`).

## 4. Before / after information architecture

**Before (#445):** search → interpretation → weak-help → clarification → stepper →
**both candidate panes (always)** → income → tips → disclaimer → sticky summary.

**After:** search → interpretation → **one question (candidates gated)** → [answer /
잘 모르겠어요 / 그냥 후보 보기] → 직종 후보 → 업종 후보 → income reminder → **Step 5
"하이코리아에서 마지막으로 확인할 것"** → disclaimer → sticky summary. The progress
stepper remains inline; the candidate dump is hidden until the user is ready.

## 5. Checklist / state-model changes

- Added `employmentFlowState()` (idle / analyzing / needs_clarification /
  showing_candidates) — the flow controller; exported + browser-bridged + unit-tested.
- The per-step checklist state model (`buildEmploymentChecklistState`) is unchanged:
  candidate-found ≠ complete; 공식 코드 확인 필요 ≠ complete; ambiguous holds the forked
  track(s); income pending until selected; **HiKorea final check never complete**; no
  visa-eligibility step. The gate respects these (revealing ≠ resolving the fork).

## 6. Candidate card changes

Unchanged from #445 (compact card: label + 직종/업종 badge + confidence + ✓ 공식 분류 코드 +
short reason + "이 항목이 맞을 수 있는 경우", with "다른 항목이 맞을 수 있는 경우" + path behind
"자세히 보기"; top 2 + "더 보기"; "가장 가까운 후보 / 다른 가능성" or "몇 가지 가능성이 있어요").
The redesign’s contribution is *when* these appear (gated), not their internals.

## 7. Weak-input fallback changes

Weak inputs (`일해요`, no candidates) are **never gated** — `employmentFlowState` returns
`showing_candidates` so the guided examples (카페에서 음료 만들어요 / 공장에서 부품 조립해요 /
호텔 객실 청소해요 / 학원에서 영어 가르쳐요 / 어선에서 생선을 잡아요) are the action, not a dead
end. `알바` (generic candidates + a "what kind?" question) **is** gated, so the user is
asked to be specific before generic 단순 노무 candidates appear.

## 8. Mobile changes

The flow itself is the mobile fix: only one major block shows at a time
(interpretation → question → candidates). Income reminder + final checklist appear only
once the flow reaches candidates. Existing #445 mobile CSS retained (≥44px targets, no
horizontal overflow, top-2 + 더 보기, lists drop nested-scroll ≤520px). New gate + final
card are full-width, single-column, large-tap-target.

## 9. i18n changes

- 6 static keys added to ko/en/zh-CN (parity 1072): `jobCodeFinalCheckTitle`,
  `jobCodeFinalOcc`, `jobCodeFinalInd`, `jobCodeFinalIncome`, `jobCodeFinalConfirm` (+
  `jobCodeStepperTitle` carried from the #445 review polish).
- 3 dynamic keyed ko/en entries added to `CHECKLIST_COPY` (`flow.gateTitle`,
  `flow.gateBody`, `flow.reveal`). Every `jcChecklistCopy` key verified present.

## 10. Tests added

- `employmentFlowState` unit tests (idle / analyzing / gated / answered / revealed /
  weak-not-gated / no-clarification).
- DOM-render smoke extended: real `jcApplyFlow` hides `#jcResults` + `#jcFinalCheck` and
  shows the gate (with reveal button) while gated; `jcDismissClarification` reveals
  candidates + final checklist; a no-clarification query shows candidates immediately.
- `check_employment_reporting_helper.mjs`: assert the gate + Step-5 final checklist exist.
- `npm run test:employment-guided-ux` added (runs the guided-flow suite).
- Total: **474 checks pass**.

## 11. Commands run

`npm run validate` (`scripts/check_repo.sh`, 14 sections) → **exit 0, all regression
checks passed**; `npm run test:employment-guided-ux` / `test:employment-checklist`
(474), plus analyzer (51), modes (504), source audit, reporting-helper, i18n parity
(1072×3), hardcoded-text, static-i18n, dummy-text, ai-shell.

## 12. Manual QA results (flow per required query)

`flow (initial)` = state right after the search, before the user acts.

- **Field labor** (한치잡이 배 / 골프장 청소 / 귤 따요 / 공장 박스 포장 / 수산물 손질 / 리조트 객실 /
  식당 설거지): all `needs_clarification` → interpretation + one question first, candidates
  gated. ✓
- **Weak/ambiguous**: 일해요 (0/0) → `showing_candidates` (guided examples, no gate);
  회사 다녀요 (no question) → `showing_candidates`; 알바/공장/청소/배 (candidates + question)
  → `needs_clarification` (gated). ✓
- **Arts/ent**: 댄서/아이돌 연습생/타투이스트/유튜브 → `needs_clarification`; K-pop trainee (0/0)
  → `showing_candidates` (공식 코드 확인 필요 card). ✓
- **Pro/svc**: English teacher (no question) → `showing_candidates`; software developer /
  researcher / translator / barista / hotel front desk → `needs_clarification`. ✓

Every query verified: screen starts with the interpretation, ≤1 clarification shown,
직종/업종 separated, weak inputs give better examples, 공식 코드 확인 필요 visible and never
complete, income reminder + final HiKorea checklist present after candidates, HiKorea
final check never complete, **no visa-eligibility judgment**.

## 13. Remaining risks

- The gate adds one tap for clarifiable inputs before candidates; mitigated by the always-
  available "그냥 후보 보기" + "잘 모르겠어요" escapes (no dead-end, ≤1 extra action).
- Desktop stays single-column (two-column side-stepper deferred — the 860px modal is tight;
  clarity preferred over density, per the brief).
- zh-CN sees Korean for runtime gate/card copy (pre-existing ko-fallback; brief scoped ko/en).
- `kssc.mods.go.kr` portal URL is inherited from #442’s press-release extraction (flagged
  in the #445 review as worth a human verify; not changed here to avoid a guessed URL and
  to stay consistent with the source-data files).

## 14. Follow-up recommendations

- Optional desktop two-column (main flow + sticky side checklist) for very wide viewports.
- Verify the `kssc.*` portal domain and, if needed, correct it across the #442 data files +
  links in one focused change.
- Persist failure logs (#442 `createFailureLogger`) to mine weak inputs and add aliases.
- Browser-based visual regression for the modal once a harness exists.
