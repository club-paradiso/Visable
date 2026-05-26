# AI_FALLBACK_AND_REGRESSION_SMOKE_PR_EF_2026_05

## 1. Executive summary
- This PR delivers PR E/F scope only: safer AI fallback behavior for ungrounded Korean stay/visa questions, plus lightweight regression/smoke coverage hardening.
- No production visa/legal/manual data files were modified.
- Law grounding default mode remains unchanged (disabled-safe by default unless explicitly configured).

## 2. Issue IDs addressed
- PDA-014
- PDA-024
- Regression hardening for fallback/i18n/frontend marker/law-grounding disabled-mode checks (existing script pathways consolidated and re-validated).

## 3. Files changed
- `backend/paradiso_backend.py`
- `backend/tests/test_paradiso_backend.py`
- `docs/audits/AI_FALLBACK_AND_REGRESSION_SMOKE_PR_EF_2026_05.md`

## 4. AI fallback behavior before/after
- Before: ungrounded prompt already had Korea-scoped controls, but included named foreign agency examples and less explicit anti-hallucination category coverage.
- After: ungrounded prompt explicitly blocks non-Korean immigration-system leakage using generic wording and adds stricter category-level anti-invention constraints (documents, deadlines, fees, forms, law-article numbers, eligibility, procedural guarantees).

## 5. Non-Korean immigration system leakage guard
- Ungrounded fallback now instructs:
  - stay in Korea immigration context;
  - avoid non-Korean immigration systems / foreign administrative agencies / foreign legal-process boilerplate unless user explicitly asks about another country;
  - avoid foreign-agency redirection phrasing.
- No new named foreign agency examples were introduced.

## 6. Hallucination guard
Ungrounded fallback now explicitly forbids inventing without verified source:
- documents
- deadlines/grace periods
- fees/costs
- forms/form numbers
- law-article numbers
- eligibility rules
- procedural guarantees/outcome guarantees

## 7. Grounded behavior preserved
- Grounded-path logic for D-2/D-4/E-7 extension routing and manual-source framing is unchanged.
- Only ungrounded fallback instruction text was tightened.

## 8. Regression/smoke checks added or updated
- Added deterministic unit assertions for fallback prompt safety in `backend/tests/test_paradiso_backend.py`:
  - Korea-scoped + non-Korean leakage guard text assertions
  - anti-invention category assertions
- Existing lightweight repo checks remain primary (`scripts/check_repo.sh`, `scripts/smoke_frontend_accessibility.sh`, `scripts/smoke_law_grounding.sh`).

## 9. Law grounding default unchanged
- No changes to law-grounding default enablement behavior.
- No change setting `LAW_GROUNDING_MODE` to production/live.

## 10. Data files unchanged
Confirmed unchanged:
- `visa_data.json`
- `backend/data/visas.json`
- `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`
- `doc_master.json`

## 11. Validation results
- JSON validity checks for required files: passed.
- `visa_data.json` vs `backend/data/visas.json` parity: unchanged/OK in this branch.
- Backend test suite and repo checks were run per command log for this PR.

## 12. Remaining work
- Run final Batch 2 interactive Agent Mode audit via `docs/audits/BATCH_2_FINAL_INTERACTIVE_RERUN_PROMPT_2026_05.md`.
- Proceed with H1/H2/H3 staged law-grounding activation only after disabled/audit-mode smoke remains stable.
- Proceed with D3A/D3B/D3C source-confirmed data corrections only after stronger source extraction and Batch 2 coverage.
