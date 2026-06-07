# Data Coverage Audit — 2026.5 Official Manuals

**Date:** 2026-06-07
**Scope:** Source-backed coverage audit of Paradiso production stay/status data
(`visa_data.json`) against the official manuals committed in the repository.
**Method:** Page-level text extraction from the committed PDFs (PyMuPDF), with
printed-page footer verification (`- N -`), cross-checked against the current
`procedures.*` data and `manualRefs`.

> This audit precedes and justifies the production changes recorded in
> `docs/data/HIGH_CONFIDENCE_DATA_UPDATE_2026_05_MANUALS.md`. A non-production
> machine-readable copy lives at `reports/data-coverage/coverage-audit-2026-05.json`.

---

## 1. Executive summary

**Overall coverage verdict.** Paradiso's stay/status data is already in a
deliberately **conservative** state: every audited record carries
`sourceManualStatus.verified = false` and `needsManualReview = true`, and parent
procedures that lack a clean status-specific source list are left **empty with a
cautious summary** rather than filled by analogy. This is correct and should be
preserved.

**High-confidence areas (direct page-level evidence found).** Three foreigner-
registration (외국인등록) document lists that were empty (`준비 중`) have a single,
status-specific 제출서류/신청서류 list in the 2026.5 stay manual that can be
reproduced verbatim at the parent level without flattening:

- **E-10** registration — stay manual **pp. 338–339**
- **D-8** registration — stay manual **p. 126**
- **H-1** registration — stay manual **p. 517** (H-1-specific, **not** borrowed)

**Major gaps (real, but not safely fillable from these manuals).**

- **D-10** registration — the D-10 chapter (pp. 142–165) covers 변경/연장/재입국/
  배점 but has **no 외국인등록 제출서류 subsection**. The empty list is correct.
- **F-2 / G-1** registration — large multi-sub-code chapters with **no parent-level
  외국인등록 list**; the requirement is genuinely sub-code-specific.
- **H-2** — `신규발급 중단` (policy-limited); stay-manual coverage is appendix-based
  (별첨 3, renumbered pages) with no clean main-chapter registration list.
- **B-1** — short-term waiver; 90일 초과 등록은 예외적이며 status-specific list 없음.

**Unsafe-to-fill areas.** D-10 / F-2 / G-1 / H-2 / B-1 registration; any H-1
extension/reentry list (current values may be borrowed — see §4); all
extension/statusChange lists that are scenario-specific in the source.

**Recommended update order.**
1. E-10, D-8, H-1 registration (done — this PR).
2. Acquire/locate the manual's **general 외국인등록 공통서류** section and any
   per-sub-code registration tables for D-10/F-2/G-1 → dedicated review PR.
3. Re-verify H-1 extension/reentry against the H-1 chapter (borrowed-list check).

---

## 2. Source files inspected

| File name | Type | Date/version | Used for audit? | Notes |
|---|---|---|---|---|
| `docs/source-manuals/2026-06/stay_manual_2026_06_01.pdf` | 체류민원 안내매뉴얼 (stay) | 2026.5 (2026-06-01 build), 777 pp. | **Yes** | Primary source. Printed page N == PDF page N (footer verified on sampled pages). |
| `docs/source-manuals/2026-06/stay_manual_2026_06_01.hwp` | 체류민원 (HWP) | 2026-06-01 | No | HWP twin of the PDF above. |
| `docs/source-manuals/2026-05/stay_manual_2026_05.pdf` | 체류민원 (stay) | 2026.5 (2026-05-21) | No | Superseded by the 2026-06-01 build. |
| `docs/source-manuals/2026-05/visa_manual_2026_05.pdf` | 사증발급 안내매뉴얼 (visa) | 2026.5 | No | Issuance-side; not the source for the stay-side registration gaps audited here. |
| `docs/source-manuals/2026-05/visa_manual_2026_05_21.hwp` | 사증발급 (HWP) | 2026-05-21 | No | HWP twin. |
| `backend/data/manual_grounding/structured_requirements_2026_06_01.json` | Derived extraction | 2026-06-01 | Reference | Pre-existing machine extraction; flagged `requiresHumanReview`. |

The newest stay manual (`stay_manual_2026_06_01.pdf`) was preferred per the
"newest official manual" rule.

---

## 3. Coverage audit table

Verdict legend: `source-confirmed-scenario-specific` (direct, status-specific
list found) · `source-missing` (no status-specific section) · `policy-limited`
(issuance suspended/constrained) · `data-present-needs-source-check`.
Severity: P0 (misleading/unsupported) · P1 (common task missing) · P2
(incomplete, not misleading) · P3 (minor).

| Code | Procedure | Current UI/data status | Manual evidence | Source file | Page/section | Verdict | Next action | Sev |
|---|---|---|---|---|---|---|---|---|
| E-10 | registration | was empty `준비 중` | **found** | stay 2026-06-01 | pp. 338–339 · 외국인등록 신청서류 | source-confirmed-scenario-specific | **FILLED** (this PR) | P1 |
| D-8 | registration | was empty `준비 중` | **found** | stay 2026-06-01 | p. 126 · 외국인등록 신청서류 | source-confirmed-scenario-specific | **FILLED** (this PR) | P1 |
| H-1 | registration | was empty `준비 중` | **found (H-1-specific)** | stay 2026-06-01 | p. 517 · 외국인등록/제출서류 | source-confirmed-scenario-specific | **FILLED** (this PR) | P1 |
| D-10 | registration | empty `준비 중` | none in chapter | stay 2026-06-01 | pp. 142–165 (no 등록 list) | source-missing | leave empty; needs general-등록 source | P2 |
| D-10 | extension | raw auto-extract fragments | partial | stay 2026-06-01 | p. 155 | data-present-needs-source-check | clean up raw strings in later PR | P2 |
| F-2 | registration | empty `준비 중` | none parent-level | stay 2026-06-01 | pp. 360–420 | source-missing (sub-code dependent) | leave empty | P2 |
| G-1 | registration | empty `준비 중` | none parent-level | stay 2026-06-01 | pp. 498–513 | source-missing | leave empty | P2 |
| H-2 | registration | empty `준비 중` | appendix only | stay 2026-06-01 | 별첨 3 (p. 555 region) | policy-limited | leave empty; suspended status | P2 |
| H-1 | extension / reentry | populated (2 / 4 docs) | not re-verified | — | — | data-present-needs-source-check | verify vs H-1 chapter (borrowed-list risk) | P2 |
| B-1 | registration | empty `준비 중` | none | stay 2026-06-01 | p. 24 | source-missing | leave empty | P3 |
| F-2 | statusChange | parent empty, 6 variants filled | variant-level | stay 2026-06-01 | — | source-confirmed-scenario-specific | OK as-is (variants carry docs) | P3 |

---

## 4. Code-specific findings

### D-10 (구직)
- **Available procedures:** extension (docs present, but raw auto-extracted text),
  registration (**empty**), statusChange (parent empty, 4 variants filled).
- **Registration:** the entire D-10 chapter (pp. 142–165) was read; it contains
  활동범위 / 세부약호 / 체류자격 변경허가 + 제출서류 (pp. 148–152) / 점수제 배점
  / 체류기간 연장 제출서류 (pp. 155–157) / 복수재입국 (p. 159) — **but no
  외국인등록(foreigner registration) 제출서류 subsection.** There is no D-10-
  specific registration list to reproduce.
- **Safe to fill later?** Only from the manual's **general 외국인등록** section or a
  per-sub-code table — not present in this chapter. **Do not fill from analogy.**
- **Action:** keep empty + existing cautious summary. (Matches the QA "준비 중" report.)

### H-1 (관광취업)
- **Available procedures:** extension (2 docs), registration (**empty → now FILLED**),
  reentry (4 docs).
- **Registration:** p. 517 has a clean H-1-specific block — header `외국인등록`,
  `대상: 90일을 초과하여 체류하려는 자(협정상 예외 없음)`, `제출서류 ① 신청서
  (별지34호) · 여권 · 표준규격사진 1매 · 수수료 ② 여행일정 및 활동계획서 ③
  근무처의 사업자등록증 사본 및 계약서 등(취업중인 경우) ④ 체류지 입증서류
  (월세계약서 등)`. The `여행일정 및 활동계획서` and `협정상 예외 없음` wording is
  distinctly working-holiday-specific → **direct evidence, not a borrowed list.**
- **Source limitations:** extension/reentry lists were **not** re-verified this run;
  the QA "borrowed list" concern applies to those, not registration. Flagged P2.
- **Action:** registration FILLED from p. 517; extension/reentry left untouched and
  flagged for verification.

### H-2 (방문취업, 신규발급 중단)
- **Available procedures:** extension (empty), registration (empty, 1 variant),
  workplaceChange (1 variant).
- **Findings:** policy-limited. The main stay manual does not carry a clean H-2
  외국인등록 제출서류 list; H-2 material appears in appendix `별첨 3` (renumbered
  pages). The data's `pp. 526-531` ref falls inside the H-1 chapter / appendix
  boundary and is unreliable.
- **Action:** **do not fill.** Preserve `신규발급 중단` framing.

### B-1 (사증면제협정)
- **Available procedures:** extension (2 docs), registration (empty).
- **Findings:** short-term waiver; 외국인등록 only applies to >90-day stays
  (exceptional). No status-specific registration list at p. 24.
- **Action:** do not fill (source-missing). P3.

### D-8 (기업투자)
- **Available procedures:** extension (12 docs), registration (**empty → now FILLED**),
  reentry (5 docs), statusChange (4 variants).
- **Registration:** p. 126 — header `외국인등록 / 1. 외국인등록 신청서류`:
  `① 신청서(별지34호) · 여권원본 · 표준규격사진1장 · 수수료 ② 사업자등록증,
  법인등기사항전부증명서(법인기업인 경우) ③ 체류지입증서류(부동산 임대차계약서
  등)` plus a `☞` note that re-issued-abroad D-8 holders 준용 the 변경 docs. One
  parent list (not sub-code split) → safe.
- **Action:** registration FILLED from p. 126.

### E-10 (선원취업)
- **Available procedures:** extension (empty), registration (**empty → now FILLED**).
- **Registration:** header `외국인등록 / 1. 외국인등록 신청서류` (p. 338) with the
  list on p. 339: `① 신청서(별지34호) · 여권원본 · 표준규격사진1장 · 수수료 ②
  내항여객운송사업면허증 또는 내항화물운송등록증 ③ 건강검진서(밀봉) ④ 마약검사
  확인서(밀봉) ⑤ 산업재해보상보험 또는 상해보험 가입증명원 ⑥ 체류지 입증서류`.
  One parent list → safe.
- **Extension (NOT filled):** p. 338 shows **two distinct extension scenarios**
  (고용해지 구직 3개월 연장 vs. 재고용 특례 연장) with **different** document sets →
  scenario-specific. Filling the parent would flatten → left empty.
- **Action:** registration FILLED from pp. 338–339; extension left empty (flatten risk).

### G-1-5 (G-1 기타 sub-code)
- **Structure:** Paradiso models G-1 as a parent record (sub-codes G-1-1/5/6/10/11/12);
  there is **no separate G-1-5 record**. G-1 statusChange already has 8 variants.
- **Registration:** the G-1 chapter (pp. 498–513) has no parent-level 외국인등록
  제출서류 list; refugee/other-status registration documents are scenario-specific.
- **AI smoke (G-1-5 → F-6):** see Phase 4 in the QA doc — answer relies on F-6
  status-change grounding, which exists.
- **Action:** do not add a parent G-1 registration list; no separate G-1-5 record needed.

### F-2 (거주)
- **Tab interaction:** see `docs/design/INTERACTION_STABILIZATION_QA.md` (Phase 1).
- **Data:** statusChange parent empty but **6 variants filled** (correct — F-2
  변경 is highly sub-code-specific). The F-2 chapter (pp. 360–420) has no parent
  외국인등록 list → registration correctly empty.
- **Action:** no data change. F-2 is variant-driven by design.

---

## 5. Do-not-fill list

Paradiso must **not** add document requirements for the following unless
additional official, status-specific source evidence is located:

- **D-10 registration** — no 외국인등록 list in the D-10 chapter.
- **F-2 registration** — sub-code-specific; no parent list.
- **G-1 registration** (incl. G-1-5) — scenario-specific; no parent list.
- **H-2** (any procedure) — `신규발급 중단`, policy-limited, appendix-only source.
- **B-1 registration** — exceptional; no status-specific list.
- **H-1 extension / reentry** — current values not re-verified (borrowed-list risk).
- Any **extension/statusChange** parent list that is scenario-specific in the
  manual (e.g., E-10 extension's two scenarios).

---

## 6. High-confidence update candidates (acted on in this PR)

Only procedures meeting **all** gates (direct page-level evidence · exact
file+page+section recorded · unambiguous procedure type · clear doc list · clear
sub-code mapping with **no flattening** · real data gap · existing schema):

| Code | Procedure | File | Page | Section |
|---|---|---|---|---|
| E-10 | registration | stay_manual_2026_06_01.pdf | pp. 338–339 | 외국인등록 신청서류 |
| D-8 | registration | stay_manual_2026_06_01.pdf | p. 126 | 외국인등록 신청서류 |
| H-1 | registration | stay_manual_2026_06_01.pdf | p. 517 | 외국인등록 / 제출서류 |

---

## 7. Recommended remaining follow-up PRs

- **Source-limited warnings / UI labels:** none required — empty procedures already
  render cautious summaries; no label was weakened.
- **Additional official source acquisition:** locate the manual's **general
  외국인등록 공통서류** section and per-sub-code registration tables to enable
  D-10 / F-2 / G-1 registration fills.
- **AI grounding update:** none required — no schema field used by AI grounding
  changed (only `procedures.registration.requiredDocs` content + `manualRefs`).
- **Deeper data-update PRs:** (a) verify H-1 extension/reentry vs the H-1 chapter;
  (b) clean D-10 extension's raw auto-extracted strings; (c) H-2 only if/when
  issuance resumes or an appendix-grounded list is confirmed.
