# Enforcement Intelligence v3

## Goal

Turn Enforcement Intelligence from a five-code calculator with a thin prediction layer into an extensible, evidence-calibrated enforcement analysis system without weakening the existing deterministic legal baseline.

## Non-negotiable invariants

1. `legal_rules.json` remains the authority for deterministic monetary tiers until a reviewed replacement is explicitly adopted.
2. The ontology describes concepts and material fact dimensions; it must not invent money amounts, probabilities, or disposition outcomes.
3. Unknown or ambiguous facts remain unknown. The classifier must abstain rather than force a plausible-looking provision.
4. Raw user narratives are not used as prediction evidence and must not be persisted merely to improve model quality.
5. AI output never overrides the deterministic legal baseline.

## Phase 1 — semantic foundation (this PR)

- Add a versioned enforcement ontology and JSON Schema.
- Register the five currently supported violation concepts without adding new legal rules.
- Add a loader/validator and make deterministic rule loading fail closed when ontology and legal rules drift.
- Seed a benchmark from the existing, already-tested colloquial Korean parity fixture.
- Keep current production behavior backward compatible.

## Phase 2 — benchmark expansion

Build a reviewed benchmark with at least 100 cases before expanding prediction scope.

Required slices:

- clear vs ambiguous classification
- status/substatus normalization
- exact dates vs duration-only inputs
- first/repeat violation
- voluntary disclosure vs investigation already started
- designated workplace vs workplace change/addition
- multiple simultaneous fact signals
- unsupported fact patterns that must abstain
- historical assessment dates and legal-version boundaries

Metrics must be reported separately:

- violation-code accuracy
- material-fact extraction accuracy
- deterministic baseline accuracy
- abstention precision/recall for ambiguous or unsupported cases
- latency p50/p95

Do not use one aggregate score that can hide a dangerous failure mode.

## Phase 3 — ontology expansion

Only after reviewed legal sourcing, add additional violation concepts as ontology entries first. Each new concept must declare:

- stable code
- Korean public label
- category
- primary legal basis
- material fact dimensions
- lifecycle (`PLANNED`, `ACTIVE`, `DEPRECATED`)
- whether deterministic rules currently support it

A `PLANNED` concept may exist without a money rule. An `ACTIVE` concept marked `supportedByDeterministicRules=true` must have a validated rule entry.

## Phase 4 — evidence retrieval and calibration

Replace one-case evidence behavior with ranked retrieval over multiple verified records where lawful and available.

Target architecture:

`structured facts -> ontology classification -> deterministic baseline -> verified evidence retrieval -> similarity features -> calibrated prediction -> bounded explanation`

Prediction should be driven by structured, reviewable features rather than an LLM guessing directly from prose.

Candidate similarity features include only reviewed fields such as:

- violation concept
- status-of-stay family
- duration band
- prior-violation count
- voluntary disclosure
- investigation state
- authorization/workplace relationship

No feature should be added merely because it correlates in a small dataset. Sensitive or legally inappropriate attributes must not be used.

## Phase 5 — prediction evaluation

Do not ship a broader prediction model until it beats the deterministic-only baseline on a held-out reviewed set and passes calibration checks.

Minimum reporting:

- coverage rate
- abstention rate
- top-1/top-3 disposition accuracy where ground truth exists
- monetary-range coverage where ground truth exists
- confidence calibration
- error severity review, with wrong-provision errors treated as critical

## Immediate next work

1. Grow the benchmark seed from 10 to 100+ reviewed scenarios.
2. Inventory additional enforcement provisions and mark them `PLANNED` only after source review.
3. Introduce a feature-vector contract for similarity retrieval.
4. Add multi-evidence retrieval with deterministic ranking and a hard evidence-count cap.
5. Keep the current user-facing page on v2 behavior until the v3 benchmark demonstrates a measurable improvement.
