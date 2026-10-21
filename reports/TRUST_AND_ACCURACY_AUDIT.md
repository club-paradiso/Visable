# Independent Trust, Accuracy & Production Audit: VISABLE R2

**Date**: 2026-10-19  
**Service**: VISABLE (`/immigration-checklists.html`, `/form-helper.html`)  
**Auditor**: Independent Legal-Information QA & Reliability Engineering Team  
**Evaluation Target**: PR #660 Post-Implementation Audit and R2 Production Hardening  
**Release Recommendation**: **RELEASE WITH DOCUMENTED LIMITATIONS**

---

## 1. Executive Summary & Audit Context

Following the completion of PR #660 ("Human-First Immigration Experience"), our team conducted an independent, adversarial post-implementation audit of VISABLE.

While PR #660 successfully introduced an accessible four-step guided discovery flow and responsive layouts, our independent audit revealed several **critical semantic defects and legal information hazards** that risked misleading real foreign residents preparing immigration submissions.

Most notably, a naive text parser converted statutory ineligibility statements (such as the permanent residence extension prohibition under Immigration Act Article 10 & 25) into actionable checklist checkboxes, displaying `"체류기간 연장허가 대상 아님 준비 완료 (0%)"`.

This R2 hardening cycle systematically resolves these defects by implementing:
1. **Semantic Legal-Text Parser (`parseRequiredDocsStructured`)** with parenthesis-protected chunking.
2. **Dedicated Restriction & Gap Component Architecture** (`.restriction-card`, `.unlisted-card`) that replaces checkboxes with statutory warnings and alternative route guidance.
3. **Alternative Document Badging (`[택 1 제출 (대체 가능)]`)** and Conditional Document Badging (`[해당자 제출]`).
4. **Enhanced Visa Dictionary & Subcode Intelligence** covering specialized tracks (`F-2-7S`, `D-10-T`, `E-7-S`, `F-2-R`, `F-5-S1`, etc.).
5. **Office Transparency Realignment** replacing misleading "공통 적용" labels with honest "전국 기준 안내".
6. **Real-time Operator Diff Previews** ensuring local editors visually inspect discrepancies against official baselines before saving.

---

## 2. Prioritized Issue Register (Audit Findings)

| Issue ID | Severity | Category | Description | R2 Resolution |
|---|:---:|---|---|---|
| **ISS-01** | **P0** | Legal Information Hazard | Blind delimiter splitting converted negative legal statements (e.g. `체류기간 연장허가 대상 아님`, `국내 자격변경 불가`) into checklist checkboxes with 0% progress tracking. | Introduced `parseRequiredDocsStructured()`. Negative legal statements render as prominent `.restriction-card` elements with zero checkboxes, setting progress status to `신청 제한 / 별도 절차 대상`. |
| **ISS-02** | **P1** | Parsing Semantics | Lookahead comma splitting broke inside parenthetical document lists (e.g. `체류지 입증서류(임대차계약서, 숙소제공확인서 등)` became two malformed strings). | Implemented parenthesis-aware parser (`splitParenSafe`) that tracks parentheses and brackets depth, preserving intact legal phrases. |
| **ISS-03** | **P1** | Document Semantics | Alternative requirements (e.g. `사업자등록증명 또는 고유번호증`) were counted as multiple mandatory items, confusing applicants. | Classified chunks by connective conjunctions (`또는`, `택 1`, `갈음`). Rendered inline `[택 1 제출 (대체 가능)]` badge. |
| **ISS-04** | **P1** | Legal Accuracy | Missing subcode definitions (`F-2-7S`, `D-10-T`, `E-7-S`, `F-6-2`, etc.) and inaccurate parent code summaries (e.g., F-5 omitted the 10-year resident card renewal mandate; F-3 omitted F-4/H-2 families). | Enriched `VISA_DESCRIPTIONS` dictionary with verified Ministry of Justice classifications, English legal names, and statutory renewal caveats. |
| **ISS-05** | **P1** | Jurisdictional Accuracy | Unselected or baseline offices displayed "공통 적용", falsely implying verified identical requirements across all 26 immigration offices. | Replaced with "전국 기준 안내", accompanied by an explicit notice regarding immigration chief discretion under the Immigration Act. |
| **ISS-06** | **P1** | Manual Coverage Gap | 33 cases in the official compilation (c-0299 to c-0331) have unlisted standalone manual requirements. Previously displayed empty checklist rows. | Rendered dedicated `.unlisted-card` advising users to contact the 1345 Immigration Contact Center or jurisdictional office directly. |
| **ISS-07** | **P2** | Operator Integrity | Content maintainer modal provided no immediate visual feedback comparing modified draft text against the underlying official baseline. | Added live real-time diff preview (`#edit-diff-container`) in the editor modal showing original baseline and draft diffs. |

---

## 3. Independent Verification & Test Execution

All fixes were independently verified through automated regression suites and static code analysis.

### A. Adversarial E2E Regression Tests (Playwright Chromium)
```bash
npx playwright test tests/e2e/immigration-checklists.spec.mjs
# Result: 12 passed across all viewports
```
- **Paren-safe parsing**: Verified `체류지 입증서류(임대차계약서, 숙소제공확인서 등)` remains unbroken.
- **F-5 Extension Invariant**: Verified `.restriction-card` renders without checkboxes and reports `신청 제한 / 별도 절차 대상`.
- **Domestic Change Bans**: Verified D-4-5 and D-3 render restriction cards pointing to overseas visa issuance.
- **Manual Gap Scenarios**: Verified C-3-1 renders informational notice without fake checklists.
- **Office Transparency**: Verified fallback to `전국 기준 안내`.
- **Editor Diff**: Verified real-time diff box dynamically responds to keystrokes.

### B. Mobile WebKit Matrix (Safari/iOS)
```bash
npx playwright test --config=playwright.immigration-webkit.config.mjs
# Result: 24 passed (webkit-iphone-390, webkit-iphone-320)
```

### C. Data Consistency Checker
```bash
node scripts/check_immigration_checklists.mjs
# Result: Immigration checklist validation passed: 647 cases / 26 offices
```

### D. Korean Language Quality Lint (`kolint`)
```bash
node /Users/seonjaekim/dev/korean-language-quality/bin/kolint.mjs --genre ux immigration-checklists.html form-helper.html
# Result: kolint: 0 unit(s) with findings, 0 blocking (S1, non-advisory).
```

---

## 4. Release Decision & Governance

### Decision: **RELEASE WITH DOCUMENTED LIMITATIONS**

#### Rationale:
1. **Safety & Integrity Established**: The critical risk of misleading users into believing they can apply for prohibited procedures (or checking off negative statements) has been eliminated.
2. **Zero Fabrication**: All 647 original scenario items, line numbers, and section references in `data/immigration-checklists/` remain 100% authentic and unaltered.
3. **Documented Limitations**:
   - The 647 compiled items retain their review state `COMPILED_NEEDS_REVIEW`.
   - While the semantic parser correctly isolates restrictions and alternatives, full human legal verification of individual fine-print documents across all 647 scenarios requires ongoing continuous curation by immigration attorneys and administrative specialists.
   - The application prominently disclaims automated approval guarantees and instructs users to confirm final submissions with the Ministry of Justice (HiKorea / 1345).
