# VISABLE Enforcement: multi-subject source registry and legal provenance

## Purpose / scope
This change adds a **new**, standalone, de-identified case/source registry that can
hold employer, business, foreign-national and other respondents involved in one
official case without interpreting an employer's penalty as an individual worker's
penalty. It does not reclassify prior reviewed outcome records or change statutory
amounts. Empty fixture: `backend/data/enforcement/case_registry.template.json`.

### Example (illustrative only; not actual ground truth)
A decision describing an employer notified of a fine and several foreign workers:
- one `caseId`, one or more official `sourceIds`
- subject A `role=EMPLOYER`, with `PENALTY_NOTICE` observation if the document
  actually states the notice and amount;
- subject B `role=FOREIGN_NATIONAL`, **no monetary observation** unless a
  separate verified source establishes that person's assessed amount.
- notice `NOTIFIED` is distinct from paid `PAID` and a court fine `SENTENCED`.

The public sample in previous discussions must **not** be checked in as an actual
reviewed outcome. No real adjudication/individual records are populated by this PR.

## Data safeguards
- Strictly typed subject roles, event types and stage combinations.
- Official-source allowlisted HTTPS URLs only; never persist law API keys,
  internal administrative records, identifying narratives or raw file bodies.
- Identifier fields are opaque case/src/subject/obs tokens generated **outside**
  this registry; source records must be lawfully obtained and independently reviewed.
- Reuse one `sourceId` across multiple subjects in the same case; one public decision
  is not seven independent penalty observations for seven workers.
- `reviewed_observations()` gives narrow reviewed *candidates* only.
  It does not auto-populate or auto-promote the v3 prediction evaluator.
- An attestation of independent review is **not** a cryptographic guarantee.
  Operators must retain internal review proof, access controls, and lawful
  provenance outside the repository.
- Schema: `backend/data/enforcement/case_registry.schema.json`.
  Canonical runtime validator: `backend/services/enforcement_case_registry.py`.

## Independent legal grounding: no MCP implementation cloned
Read about [korean-law-mcp](https://github.com/chrisryugj/korean-law-mcp),
particularly its exposed ideas of historical applicable-law checks and
citation/source verification. **No source code or npm dependency from that
project is incorporated here.** The repository's MIT license permits reuse
subject to attribution, but its NOTICE discloses an independently unlicensed
third-party anti-bot parsing approach. We deliberately do **not** copy that
implementation or evade access controls.

VISABLE already has its own direct, official law.go.kr API adapter
(`lib/enforcement-law-grounding.js`). The original VISABLE
`lib/enforcement-law-validity.js` now checks whether the official API's
current statute/regulation metadata could apply to the **exact violation dates**.
If dates are missing, law effective dates are absent or the official returned
version began **after** conduct, `temporalVerification=REQUIRES_REVIEW` and
`lawGrounding.status` cannot claim `VERIFIED`.
This does not retrieve historical versions automatically; a historical
`get_annexes` equivalent needs a separate official API permission-checked
adapter, and a legal professional should verify transitional provisions and
the actual Annex 7 as-of the offense date.

## Legal/data usage and release conditions
- Copyright Act Article 7 generally excludes statutes and official rulings from
  copyright protection; **API use conditions still apply**. The official
  [law open data guide](https://open.law.go.kr/LSO/information/guide.do)
  requires approved usage and source attribution; some interfaces restrict
  commercial use. Confirm the specific approved API and use scope before batch
  collection or commercialization.
- VISABLE is not officially endorsed by the Ministry of Government Legislation
  or the author of Korean Law MCP. Credit official records as
  "국가법령정보센터(법제처)" and link to the authentic source.
- Keep law API credentials server-side. Never include an OC key in public URLs,
  committed test data, client JS or error logs.
- Independent review and lawfully acquired actual outcome records are still
  missing. Do not claim model training/evaluation success:
  `NOT_EVALUABLE` stays in force until usable verified labels exist.

## Test
- `node scripts/check_enforcement_law_validity.mjs`
- `python3 -m unittest backend.tests.test_enforcement_case_registry`
- `npm run test:enforcement` and full CI

## Proposed next phase (not implemented here)
1. Permission-checked official `prec/decc` search paginated with source provenance,
   deduplication and API-specific commercial-use review.
2. Separate intake that converts authorized public decisions to `STAGED`
   case/subject/observation candidates, followed by human verification.
3. Historical statute and Annex 7 text retrieval using authorized official API
   as-of conduct; fail closed on ambiguous dates, amendments and missing PDFs.
4. Privately reviewed target-specific ground truth, group-disjoint holdout and
   a legal review board before any broader automated outcome predictions.
