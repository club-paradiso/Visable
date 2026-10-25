# Mission 002 — Post-merge classification safety verification

Base: `main` at `c7540b015dd446a6b428fe4a1c7540de3bb139db` (PRs #706 and #707 merged).
Scope: executable Python `/api/ask` request path. **Not** a Railway deployment or live-user observation.

## Confirmed gap in merged main

`backend/services/knowledge/understanding.py` marks unknown status parents
(`UNRECOGNIZED_STATUS`, e.g. F-10) and multi-code uncertainty;
`knowledge/coverage.py` can return `NEEDS_CLARIFICATION`. But in merged
`paradiso_backend._ask_internal` the knowledge plan was built *after* grounding
and manual-context selection, and its coverage decision was advisory rather
than an early stop on answer generation. A syntactically recognized status or a
legacy task label could reach unrelated grounding/model generation before that
decision became effective.

Separately, `procedure_classifier.py` treated a passport's mere
`renewed/new` wording as an immigration information-change request because
the shared lexicon calls those words a `change` action. Initial residence-card
requests phrased as “first residence card” were not consistently recognized.

## Defensive repair (this PR)

1. `services/classification_safety.py` evaluates only deterministic identity
   and ambiguity conditions; unrecognized parent status, conflicting selected
   code, multiple unbound codes, directional change routes lacking per-case
   verification, standalone passport issuance/renewal, and unclear card action
   return a language-aware clarification.
2. `_ask_internal` enforces this guard before selecting grounding, building
   structured requirements, retrieving source material, or calling an LLM
   provider. Both streaming and buffered requests use the same preflight.
3. Passport renewal/loss and immigration change-report intent are separated
   without altering official requirements; initial-card and replacement-card
   expressions are distinguished without automatically assigning a legal
   subcode.
4. Tests patch the main grounding selector and the model completion function
   to **raise** if reached by uncertain requests. They also assert ordinary
   source-scoped questions are not mistakenly gated.

## Important trade-offs and remaining NO_GO items

- A conservative gate deliberately withholds a direct answer for **all**
  two-status change questions until a separately grounded route is established.
  The product owner should decide whether a less restrictive source-verified
  transition path is worth enabling. It must not imply eligibility.
- Parent status identity uses the repository's official parent inventory
  (currently linked to the 2026-10-02 Enforcement Decree). It is **not**
  substantive verification of every parent, subcode, or eligibility rule.
- The existing v0 classification benchmark is synthetic and unreviewed.
  Passing its engineering gate is not a legal-accuracy certification.
- Historical source conflicts (including F-4), 303 unreviewed references,
  source-effective-date handling, and independent human-reviewed v1 cases
  remain outside this patch.
- If provider/test infrastructure is unavailable, report unverified rather
  than equating code inspection or simulated tests to production verification.

## Release gate

Review the code and run `backend/tests/test_postmerge_classification_guard.py`,
`backend/tests/test_procedure_classifier.py`, `backend/tests/test_b_fixed.py`,
full backend tests and `scripts/check_repo.sh`. Confirm their results in
GitHub Actions. Do **not** auto-merge or deploy under current NO_GO.
