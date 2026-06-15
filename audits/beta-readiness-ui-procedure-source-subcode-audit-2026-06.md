# Paradiso — Beta-Readiness Audit: UI · Procedure · Source · Subcode (2026-06)

**Date:** 2026-06-15
**Branch:** `claude/nifty-galileo-qqsdjm`
**Scope:** Full repository — `index.html`, `ai.html`, all CSS/theme blocks, all visa/stay
data JSON, scenario/FAQ/help data, document taxonomy, source/manual index files, render
logic, F-4 route guide, subcode list + modal UI, responsive behavior, i18n, tests.
**Method:** Multi-agent static repository map (rendering architecture, data model, theme +
responsive inventory, dummy-text scan, test-suite inventory) cross-checked against the
prior Playwright-verified `QA_AUDIT_REPORT.md` (2026-06-13) and re-verified against the
**current** tree (the prior report's line numbers were stale: the file grew 20,677 →
22,000+ lines, and several P0/P1 items were already fixed by later commits).

> This is rendering / data-hygiene / UX work. It does **not** constitute legal
> re-validation of immigration requirements. Every record still carries
> `sourceManualStatus.needsManualReview = true`; legal accuracy requires review by a
> qualified immigration professional (see §10).

---

## 1. Executive summary

The app is **mature and was green at baseline** (`bash scripts/check_repo.sh` passes; 251
backend tests pass). Most headline items from the task brief had **already shipped** in
commits after the 2026-06-13 QA report:

| Area | State at audit | Evidence |
|---|---|---|
| Subcodes collapsed-by-default + "세부유형 N개 보기" reveal button | **Already done** | `renderExpandableSubcodeGroup`, `toggle-subcode-group`, aria-expanded + caret |
| 사증발급 unified into 절차별 안내 | **Already done** | PR #424; `renderVisaIssuanceSection` embedded in the visaIssuance tab |
| 사증발급 not-applicable suppression (B-1/B-2/H-2/F-5) | **Already done** | PR #428; `isVisaIssuanceNotApplicable` |
| F-4 재외동포 hub rebuild | **Already done** | PR #423; `assets/js/f4-route-guide.js`, `data/f4/*` |
| Dedup rendering guards (0 SEVERE) | **Already done** | PR #331; `audit_duplicate_render_content.py --check` |
| Geolocation-on-boot (QA P0-3) | **Already removed** | no `ipapi`/`ip-api`/`restcountries`/`flagcdn` in `index.html` |
| `LANGUAGE_SUPPORT['zh-CN']` = `'full'` falsehood (QA P1-3) | **Already fixed** | now `'preparing'` |
| Missing i18n keys `medTotalCount`/`agentRegionAll`/`agentTotalCount` (QA P1-2) | **Already fixed** | present in ko/en/zh-CN |

**The one genuine remaining headline gap** was that clicking a subcode did nothing — there
was **no subcode detail modal**. Subcode tiles rendered inline as static
`.manual-subcode-card`s. This audit's primary deliverable closes that gap (§4).

---

## 2. Status / subcode audit matrix (full coverage)

Derived directly from `visa_data.json` (canonical). **42 top-level records · 221 subcodes
across 29 parents.** `#var` = procedure variants; `refs` = subcodes carrying `manualRefs`;
`docs` = subcodes carrying `addReqDocs`/`addReq`.

| Code | #sub | #var | refs | docs | Available procedures |
|---|---:|---:|---:|---:|---|
| A-1 | 0 | 0 | 0 | 0 | extension, registration |
| A-2 | 0 | 0 | 0 | 0 | extension, registration |
| A-3 | 1 | 0 | 1 | 1 | extension, registration |
| B-1 | 2 | 0 | 0 | 2 | extension, registration |
| B-2 | 2 | 0 | 0 | 2 | extension, registration |
| C-1 | 0 | 0 | 0 | 0 | extension, registration |
| C-3 | 11 | 0 | 2 | 10 | visaIssuance, extension, registration |
| C-4 | 5 | 0 | 5 | 1 | extension, registration |
| D-1 | 1 | 0 | 0 | 1 | extension, registration, reentry |
| D-2 | 8 | 0 | 0 | 8 | visaIssuance, statusChange, extension, registration, activitiesOutsideStatus, reentry, partTimeWork, schoolChange |
| D-3 | 4 | 0 | 1 | 3 | extension, registration |
| D-4 | 7 | 3 | 0 | 7 | statusChange, extension, registration, reentry |
| D-4-1 | 0 | 0 | 0 | 0 | extension |
| D-4-2K | 0 | 0 | 0 | 0 | extension, registration |
| D-5 | 0 | 0 | 0 | 0 | extension, registration |
| D-6 | 0 | 0 | 0 | 0 | extension, registration, reentry |
| D-7 | 4 | 0 | 0 | 4 | extension, registration, reentry |
| D-8 | 6 | 4 | 1 | 6 | statusChange, extension, registration, reentry |
| D-9 | 5 | 3 | 1 | 5 | statusChange, extension, registration, reentry |
| D-10 | 4 | 7 | 0 | 4 | statusChange, extension, registration |
| E-1 | 0 | 3 | 0 | 0 | statusChange, extension, registration |
| E-2 | 3 | 4 | 0 | 3 | statusChange, extension, registration, workplaceChange, reentry |
| E-3 | 0 | 3 | 0 | 0 | statusChange, extension, registration, workplaceChange, reentry |
| E-4 | 0 | 2 | 0 | 0 | statusChange, extension, registration, workplaceChange, reentry |
| E-5 | 0 | 2 | 0 | 0 | statusChange, extension, registration, workplaceChange, reentry |
| E-6 | 3 | 4 | 0 | 3 | statusChange, extension, registration, workplaceChange, activitiesOutsideStatus, reentry |
| E-7 | 13 | 1 | 5 | 13 | extension, registration, workplaceChange |
| E-8 | 9 | 0 | 9 | 9 | extension |
| E-9 | 9 | 2 | 0 | 9 | extension, registration, workplaceChange |
| E-10 | 3 | 0 | 0 | 3 | extension, registration |
| F-1 | 19 | 7 | 11 | 19 | statusChange, extension, registration, statusGrant |
| F-2 | 18 | 6 | 13 | 18 | statusChange, extension, registration |
| F-3 | 6 | 4 | 3 | 6 | statusChange, extension, registration, activitiesOutsideStatus, reentry, statusGrant |
| F-4 | 15 | 3 | 2 | 15 | statusChange, extension, registration |
| F-5 | 30 | 0 | 25 | 30 | extension, registration |
| F-6 | 3 | 6 | 0 | 3 | visaIssuance, statusChange, extension, registration, reentry, statusGrant |
| G-1 | 16 | 8 | 16 | 15 | statusChange, extension, registration |
| H-1 | 0 | 0 | 0 | 0 | extension, registration, reentry |
| H-2 | 1 | 2 | 1 | 1 | extension, registration, workplaceChange |
| K-STAR | 4 | 0 | 4 | 4 | visaIssuance, statusChange, extension, reentry |
| REGION-S | 9 | 0 | 9 | 9 | **(none flagged available)** ⚠ |
| YOUTH-STAY | 0 | 0 | 0 | 0 | statusChange |

**Procedure availability across the 42 records:** extension 40, registration 37,
statusChange 19, reentry 16, workplaceChange 8, visaIssuance 4, activitiesOutsideStatus 3,
statusGrant 3, partTimeWork 1, schoolChange 1.

### Matrix observations / flags
- **Route separation is sound at the data layer.** 사증발급 (visaIssuance) is present on
  only 4 records and is suppressed for not-applicable statuses; extension/registration are
  near-universal; statusChange/workplaceChange/activitiesOutsideStatus are scoped to the
  statuses where they apply. This matches the task's required separation of overseas visa
  issuance vs. domestic status change vs. extension vs. registration vs. workplace/activity.
- **F-4 거소신고** is handled by the dedicated F-4 hub (`data/f4/*`, `f4-route-guide.js`),
  kept separate from the generic procedure system (correct per CLAUDE.md).
- **Subcode source coverage is uneven** (expected, and now surfaced honestly): F-5 (25/30),
  G-1 (16/16), F-2 (13/18), F-1 (11/19) are strong; D-2, D-10, D-4, E-9 subcodes have docs
  but no per-subcode `manualRefs` → the modal shows honest source-gap copy for those.
- ⚠ **REGION-S** has no procedure flagged `available`. It is a pilot/program code
  (alongside K-STAR, YOUTH-STAY). Flagged for product/data owner — not changed here.

---

## 3. Theme audit

**Confirmed: exactly two editorial themes** (the brief warned against assuming two — this is
verified, not assumed):
- `civic_editorial` (default) — warm civic-editorial paper; `:root` tokens.
- `archive_diary` ("Kitsch Editorial") — Y2K pop palette; `:root[data-theme="archive_diary"]`.
- Orthogonal `light`/`dark` brightness on `<body data-theme>`.

Legacy decorative residue (`starCanvas`, `horizon`, `night-light`, moon/sea/sun) was
**already removed** (code comment dated 2026-06; no references remain). No `moonshot`
strings in user-facing files (enforced by `check_repo.sh` branding scan). All Kitsch
animations are gated behind `@media (prefers-reduced-motion: no-preference)` and there is
thorough `prefers-reduced-motion: reduce` handling (11 CSS rules + 2 JS checks).

**This PR's new subcode modal is theme-correct in both themes** because it is built entirely
from existing theme tokens (`--bg0/1/2`, `--t1/2/3`, `--ac`, `--acG`, `--bd/bd2`) which
`archive_diary` overrides (e.g. `--acG` is blue-tinted under Kitsch at the `archive_diary`
root). No hard-coded colors.

---

## 4. Subcode interaction redesign (primary deliverable)

**Problem:** subcodes were collapsed by default (good), but clicking a subcode did nothing —
tiles were static `.manual-subcode-card` divs with no detail surface. The task requires a
modal/bottom-sheet with structured, source-grounded subcode detail.

**Fix (renderer + additive markup only — no protected-data edits):**
- Subcode list tiles and preview chips are now interactive (`data-action="open-subcode-detail"`,
  `role="button"` + `tabindex="0"` on the div tiles; real `<button>` for preview chips).
  Scoped via a new `--interactive` modifier so the **shared** `.manual-subcode-card` class
  (also used for scenario document tiles) is unaffected.
- New `#subcodeDetailOverlay` modal reusing the existing `openModal/closeModal/trapModalFocus`
  stack (focus trap, focus restore). Closes via ✕ button, **Escape**, and **backdrop click**
  (backdrop click is scoped to the dimmed area only — clicks inside the box never close it,
  avoiding accidental closure). Mobile (≤540px) becomes a full-width **bottom sheet**.
- `buildSubcodeModalView(visa, sub)` is a **pure, side-effect-free** builder (unit-testable)
  producing the task's hierarchy, all via `tx()` (ko/en/zh-CN):
  1. Header — subcode · name · parent status · source-coverage chip.
  2. "이 세부자격은 어떤 경우인가요?" — only when source text exists (no filler).
  3. "세부자격별 추가 확인 서류" — cautious label (not "필수"); from subcode `addReqDocs`/`addReq`.
  4. "이 세부자격 관련 절차" — only `procedures[].variants[]` whose `statusCode` matches the
     subcode; omitted entirely when none.
  5. "주의사항" — deprecated/inactive status notes; omitted when none.
  6. "공식 근거" — subcode `manualRefs`, else honest source-gap copy.
  7. CTA → parent status (shared base docs/procedures live there; avoids duplication).
- **Empty sections are omitted; honest copy is shown** when subcode-specific docs or sources
  are thin (`subcodeModalNoDocs` / `subcodeModalSourceGap`) — never a placeholder card and
  never invented certainty (CLAUDE.md).

**Coverage / test:** `scripts/check_subcode_modal.mjs` exercises the pure builder against
**all 221 subcodes across 29 parents** — asserting required sections, no raw value leaks
(`undefined`/`[object Object]`/`NaN`), honest source-gap usage (112 subcodes), real
reference rendering (109 subcodes), and variant rendering (30 subcodes), plus static
structure/wiring/a11y/i18n checks. Wired into `check_repo.sh` step 9d.

---

## 5. Responsive audit

Breakpoint coverage is broad: ≤480 (29 rules), ≤640 (16), ≤720 (14), ≤768 (20), ≤1024 (5),
plus min-width rules and ≥1200. The new subcode modal adds an explicit **≤540px bottom-sheet**.
Known residual: **360px** has no dedicated breakpoint (relies on flexible units) — acceptable
but listed for future hardening. Sticky elements (`.top-ctrls` z100, searched-mode
`.hero-container` z50) are pre-existing; the modal sits at z2000 above them and traps focus.

---

## 6. Procedure / source separation audit

The renderer keeps the legal routes distinct (see §2 matrix): 재외공관 사증발급, 국내 체류자격
변경, 체류기간 연장, 외국인등록, 근무처 변경/추가, 자격외활동, 재입국, plus the separate F-4
거소신고 hub. Document grouping uses reader-friendly, **non-overclaiming** labels (기본 준비서류 /
상황별 추가서류 / 심사 중 추가 요청 가능) per `audits/browser-document-qa/document_taxonomy_policy.md`.
The new subcode modal deliberately uses the cautious "세부자격별 추가 확인 서류" label and does
**not** copy parent document walls into the subcode view (prevents parent/subcode duplication).

---

## 7. Source coverage status

- doc references: all 87 `doc_*` ids used in `visa_data.json` resolve in `doc_master.json` (0 missing).
- Per-subcode: 109/221 subcodes carry `manualRefs`; the modal renders them, and shows honest
  source-gap copy for the remainder rather than implying certainty.
- Record-level: **every** record retains `needsManualReview = true` and graded evidence
  labels ("공식근거 직접 확인 / 관련 공식근거 있음 / 공식근거 제한 / 공식근거 확인 불가"). These
  are honest uncertainty signals and were preserved (CLAUDE.md).

---

## 8. Dummy / placeholder / stale text findings

The protected data files were already clean of placeholder tokens. The only genuine
user-facing stale items were **dead i18n keys** `agentBanner` / `agentSampleNoun`, which
falsely framed the now-real official agent registry as "샘플 데이터(scaffold)" and were
referenced by **zero** HTML/JS. **Removed from ko/en/zh-CN** (parity preserved: 1048 keys).

Everything else flagged by the scan is legitimate: honest source-gap copy, dev-gated
diagnostics (`?debug=1`), input `placeholder=` attributes, and real Korean words (예시 =
example, 임시 = temporary, 준비 중 = in preparation) — intentionally **not** removed.

**New durable guard:** `scripts/check_dummy_text.mjs` fails CI if user-facing data files
reintroduce a curated, high-confidence dummy/stale marker set (lorem/ipsum/scaffold/샘플
데이터/더미 데이터/테스트 문구/내부용/TODO:/FIXME/…). Wired into `check_repo.sh` step 9d.

---

## 9. Cross-check of prior QA report (P0/P1) — current state

| Prior item | Current state |
|---|---|
| P0-3 geolocation-on-boot without consent | **Resolved** (APIs removed from index.html) |
| P1-2 missing i18n keys (med/agent counts) | **Resolved** (present in all locales) |
| P1-3 `LANGUAGE_SUPPORT zh-CN:'full'` | **Resolved** (`'preparing'`) |
| P0-1 zh-CN 201 keys untranslated | **Open** — needs human translation (see §10) |
| P0-2 "39가지" prose vs displayed 42 | **Open (product decision)** — CLAUDE.md states "39 체류자격"; the displayed stat computes 42. Not changed without an owner decision. |
| P1-4 footer contrast / P1-5 44px tap targets | **Partially addressed in code** (modal close + new buttons are ≥44px); a global footer/header sweep is recommended as a follow-up. |

---

## 10. High-risk items needing human review (out of scope for this PR)

1. **Legal accuracy of all 42 records / 221 subcodes** — every record is
   `needsManualReview = true`; requires an immigration-law professional to validate against
   the official 2026.5 manuals. This PR did not alter legal content.
2. **zh-CN translation completeness** — ~201 values remain Korean. The UI already declares
   zh-CN as `preparing` and shows a "준비 중" notice. New keys in this PR were translated to
   Chinese; the legacy backlog still needs human translation.
3. **"39 vs 42" status-count messaging** — a brand/product decision (CLAUDE.md vs. computed
   stat). Document owner should reconcile.
4. **REGION-S** has no available procedures flagged — pilot data completeness check.

---

## 11. Completed in this PR

- Subcode detail modal (markup + `buildSubcodeModalView`/`openSubcodeModal`/
  `renderSubcodeProcedureVariants`), interactive subcode tiles + preview chips, focus trap,
  Escape + scoped backdrop close, mobile bottom-sheet, both-theme tokens, reduced-motion.
- 11 new i18n keys × ko/en/zh-CN (Chinese properly translated).
- Removed 2 dead/stale i18n keys (×3 locales).
- New tests: `check_subcode_modal.mjs` (full 221-subcode coverage), `check_dummy_text.mjs`;
  both wired into `check_repo.sh`.

## 12. Recommended follow-ups (not done here)

- Human legal validation pass (§10.1) and zh-CN translation completion (§10.2).
- Global a11y sweep: footer small-text contrast, confirm all header controls ≥44px at 390px.
- Add a dedicated 360px breakpoint hardening pass.
- Resolve the 39/42 count and REGION-S procedure data with the product/data owner.
