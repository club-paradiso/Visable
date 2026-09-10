# Enforcement Intelligence v3 — reviewed outcome intake

## Purpose

This workflow creates a privacy-safe path from a **private, independently reviewed enforcement outcome record** to the existing v3 outcome evaluator. It does not collect data automatically, infer labels, change legal rules, or make prediction confidence more assertive.

The repository intentionally contains **zero real outcome records**. `backend/data/enforcement/outcome_intake.template.json` and the existing ground-truth template stay empty.

## Data boundary

Private source files must remain outside the repository. They may contain only the structured fields required by the intake contract. The intake command rejects raw narrative and common direct identifiers rather than attempting to redact them after ingestion.

Never include names, passport numbers, foreigner registration numbers, phone numbers, email addresses, postal addresses, dates of birth, free-text case narratives, model output, or prediction output.

Two private values are consumed transiently and never written to the safe dataset:

- `sourceRecordId`: a local/private record key used only to derive `case_<HMAC>`.
- `reviewerReference`: a local reviewer reference used only to derive `reviewer_<HMAC>` audit tokens.

The official/administrative source record identifier in `provenance.recordId` is also replaced with an `src_<HMAC>` token.

## Secrets

The CLI reads HMAC secrets from environment variables so the values do not have to appear in command history:

```bash
export VISABLE_ENFORCEMENT_RECORD_HMAC_SECRET='use-a-long-random-secret-kept-outside-git'
export VISABLE_ENFORCEMENT_REVIEWER_HMAC_SECRET='use-a-different-long-random-secret-kept-outside-git'
```

Use separate secrets for record and reviewer namespaces. Rotating a secret intentionally changes the derived identifiers, so keep the private secret material under the same access controls as the private review corpus.

## Review-state contract

Every record has one terminal/current `reviewStage`, backed by an ordered `reviewHistory` with timezone-aware timestamps.

```text
STAGED
  ├─> SOURCE_VERIFIED ─> INDEPENDENTLY_REVIEWED
  │                    └> REJECTED
  └─> REJECTED
```

A reviewed record cannot skip `STAGED` or `SOURCE_VERIFIED`. Timestamps cannot move backward. `REJECTED` events use controlled reason codes instead of free-text notes.

`INDEPENDENTLY_REVIEWED` additionally requires:

- eligible official/administrative provenance;
- at least one scoreable outcome component;
- `independentFromPrediction: true`;
- a non-identifying reviewer role label;
- the full staged audit history.

The reviewer role should be a role/category such as `AUTHORIZED_ADMINISTRATIVE_REVIEWER`, never a person's name, email, account ID, or organizational login.

## Eligible provenance

Only these source types are accepted:

- `OFFICIAL_ADMINISTRATIVE_DECISION`
- `COURT_DECISION`
- `VERIFIED_ADMINISTRATIVE_RECORD`

Synthetic, model-generated, LLM-generated, or prediction-derived source types are rejected. A prediction cannot become its own ground truth. Humanity has invented enough circular grading systems already.

## Private input shape

The private input uses schema version `1.0.0`. This illustrative record is synthetic documentation only and is not checked into any ground-truth dataset:

```json
{
  "schemaVersion": "1.0.0",
  "datasetVersion": "private-review-batch-YYYY-MM-DD",
  "jurisdiction": "KR",
  "records": [
    {
      "sourceRecordId": "PRIVATE-LOCAL-KEY",
      "reviewStage": "INDEPENDENTLY_REVIEWED",
      "caseFacts": {
        "statusOfStay": "D-2",
        "violationCode": "STATUS_OUTSIDE_ACTIVITY_ART20",
        "durationDays": 18,
        "priorViolations": 0,
        "voluntaryDisclosure": true,
        "authorizationObtained": false,
        "assessmentDate": "2026-08-19"
      },
      "provenance": {
        "sourceType": "VERIFIED_ADMINISTRATIVE_RECORD",
        "authority": "Authorized administrative authority",
        "recordId": "PRIVATE-SOURCE-RECORD-KEY",
        "publicUrl": null
      },
      "outcome": {
        "decisionDate": "2026-08-20",
        "monetaryOutcomeKrw": 2000000,
        "dispositionTypes": ["ADMINISTRATIVE_FINE"],
        "primaryDispositionType": "ADMINISTRATIVE_FINE"
      },
      "independentFromPrediction": true,
      "reviewerRole": "AUTHORIZED_ADMINISTRATIVE_REVIEWER",
      "reviewHistory": [
        {
          "stage": "STAGED",
          "at": "2026-08-20T09:00:00+09:00",
          "reviewerReference": "PRIVATE-REVIEWER-REF-1"
        },
        {
          "stage": "SOURCE_VERIFIED",
          "at": "2026-08-20T09:10:00+09:00",
          "reviewerReference": "PRIVATE-REVIEWER-REF-2"
        },
        {
          "stage": "INDEPENDENTLY_REVIEWED",
          "at": "2026-08-20T09:30:00+09:00",
          "reviewerReference": "PRIVATE-REVIEWER-REF-3"
        }
      ]
    }
  ]
}
```

Do not use the example outcome as a real label or benchmark case.

## CLI workflow

### 1. De-identify private intake

```bash
python3 scripts/prepare_enforcement_outcome_corpus.py deidentify \
  --input /private/path/outcomes.json \
  --output /private/path/outcomes.safe.json
```

The command reads the two HMAC secrets from the environment, validates the review workflow, derives `case_`, `src_`, and `reviewer_` tokens, rejects duplicate private source IDs, and writes only the safe form.

It refuses to overwrite the input file in place.

### 2. Validate the safe intake dataset

```bash
python3 scripts/prepare_enforcement_outcome_corpus.py validate-safe \
  --input /private/path/outcomes.safe.json
```

The command prints only record/stage counts. It does not print case contents.

### 3. Promote reviewed records

```bash
python3 scripts/prepare_enforcement_outcome_corpus.py promote-reviewed \
  --input /private/path/outcomes.safe.json \
  --output /private/path/outcome-ground-truth.json
```

Only `INDEPENDENTLY_REVIEWED` rows are exported. `STAGED`, `SOURCE_VERIFIED`, and `REJECTED` rows remain outside the evaluator dataset.

The promoted file is passed through `validate_outcome_ground_truth_dataset()` before it is written.

### 4. Evaluate predictions

Use the existing v3 evaluator tooling against the private promoted dataset. Until that dataset contains independently reviewed outcomes matched to predictions, the correct evaluator status remains `NOT_EVALUABLE`.

## Checked-in safe schema

`backend/data/enforcement/outcome_intake.schema.json` documents the persistent, **de-identified** intake shape. It uses closed objects (`additionalProperties: false`) to make accidental source/reviewer identifier leakage easier to catch during external schema validation.

The Python intake validator is the execution-time gate used by the CLI. It additionally validates HMAC token prefixes, state transitions, timezone-aware chronological audit history, source eligibility, duplicate case IDs, scoreable reviewed outcomes, and prediction independence.

## Non-goals

This phase deliberately does not:

- scrape or ingest administrative records automatically;
- commit real outcome labels to Git;
- establish a minimum corpus size for production readiness;
- compute numeric prediction probabilities;
- change the prediction prompt, model, or model routing;
- use similarity scores as outcome confidence;
- add new legal rules or violation types.

Any later calibration or confidence-policy change should be justified by the independently reviewed corpus and evaluated through the v3 contract, not by aesthetic preference for larger confidence numbers.
