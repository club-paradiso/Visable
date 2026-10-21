# Enforcement Intelligence: 2026-10-21 reliability and evidence audit

## Verified deployment incident
Vercel production logs for `POST /api/enforcement/analyze` at approximately 16:20 KST
contained OpenRouter HTTP 429 `provider_rate_limit` failures for
`google/gemma-4-31b-it:free` and `google/gemma-4-26b-a4b-it:free`.
This establishes provider throttling as a real cause of degraded prediction,
not a parsing error in the user's Korean case description.

## Implemented mitigation
- Warm-instance per-model 60 s cooldown on 429; additional shared cooldown when
  the provider explicitly reports a `free-models-per-min/day` quota.
- No silent paid-model fallback. The OpenRouter quota is shared across free model
  IDs and a per-instance cooldown cannot guarantee global recovery.
- Categorized, non-sensitive prediction failure metadata for UX. No raw case,
  prompt, private model answer or credential enters diagnostic logs.
- Invalid/null AI likely ranges cannot be rendered as valid monetary estimates.
- Calendar-month legal tier ambiguity now fails closed without exact dates in
  both JS and Python. Tests cover two different 30-day calendar placements.
- Frontend treats legal missing facts distinctly from AI provider errors.
- Frontend recovers from second-request timeout without leaving the first
  baseline response permanently in a loading state.

## Law and effective-date limitations: NOT independently signed off
The rule database `backend/data/enforcement/legal_rules.json` uses snapshot
`kr-immigration-enforcement-2026-01-23`, `verifiedAt: 2026-08-26`.
The penalty amounts and article mappings are **unchanged by this PR**.
The relevant primary materials are the Immigration Control Act and its
Enforcement Rule article 86 / Annex 7, as-of the actual violation dates.
General calendar-month computation is addressed in Civil Act article 160,
but its application to the particular enforcement practice and the initial-day
rule must be reviewed by a qualified operator/legal reviewer.

This patch deliberately does not certify the statutory tables as current on
2026-10-21, nor infer that the first violation guarantees mitigation.
A historic incident straddling legal amendment dates requires manual review.

## Actual-outcome evaluation: pre-existing, not magically populated
The repository already has `backend/services/enforcement_outcome_evaluation.py`
and `docs/ENFORCEMENT_V3_OUTCOME_INTAKE.md`. Without independently reviewed,
privacy-safe, ground-truth administrative outcomes, evaluation must remain
`NOT_EVALUABLE`. The fixture and narrative benchmarks test extraction and
rule-engine behavior, **not** case-outcome prediction accuracy.

Before claiming calibrated prediction performance:
1. Lawfully source official disposition records with valid access and use rights.
   Never upload case narratives or identifiers to GitHub, a public Vercel preview,
   or general AI model providers.
2. Privately stage and independently review each record, preserving the
   source, decision/effective date, disposition type and observed amount.
3. Run the existing HMAC-based de-identification, `validate-safe`,
   `promote-reviewed`, and ground-truth evaluator flow, with private files.
4. Evaluate held-out cases on money-range coverage, point-estimate absolute
   error where appropriate, primary disposition top-1 accuracy, abstention and
   error by violation code / date cohort.
5. Set minimum evaluation sample sizes and acceptance criteria **before**
   unblinding performance. Do not use synthetic data as real outcomes.
6. Keep high-confidence administrative-disposition claims disabled pending
   review and legal approval.

## Release checklist
- [ ] `npm run test:enforcement`
- [ ] Repo Validation CI and relevant E2E checks
- [ ] Preview page and an isolated no-PII sample under 429 and valid JSON conditions
- [ ] Human legal verification of Annex 7 snapshot and duration thresholds
- [ ] Production deployment and controlled post-deploy smoke test
- [ ] Reviewed case-outcome dataset and evaluation (separate project; currently unavailable)

The change cannot solve account-wide free-provider exhaustion. Operate with
degraded deterministic mode or explicitly approve a paid, budget-capped provider
after a cost/privacy assessment. Do not enable payment implicitly.
