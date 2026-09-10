# Enforcement Intelligence v3 blind evaluation protocol

This protocol prevents reviewed outcome labels from being used to tune, replace, or selectively omit predictions before evaluation.

## Why this exists

The reviewed-outcome corpus and the prediction system solve different problems. The corpus establishes independently reviewed ground truth. The prediction freeze establishes what Visable predicted **before** that ground truth was independently reviewed. Evaluating predictions created after the reviewer has already recorded the answer is not a blind evaluation.

The freeze mechanism is deliberately local and privacy-safe. It records canonical SHA-256 digests and timestamps, but it is **not external notarization** and must not be described as cryptographic proof that a machine clock was honest.

## Required sequence

1. Prepare the private intake corpus outside Git with `scripts/prepare_enforcement_outcome_corpus.py`.
2. De-identify it. At this point every active case intended for the blind cohort must still be `STAGED` or `SOURCE_VERIFIED`, and `outcome` must be null.
3. Export the complete blind cohort:

   ```bash
   python scripts/freeze_enforcement_v3_predictions.py export-blind-cases \
     --input /private/safe-intake.json \
     --output /private/blind-cases.json
   ```

4. Produce exactly one public `EnforcementPrediction` for every `caseId`. `UNAVAILABLE` is a valid prediction state and must remain in the cohort. Do not delete failed cases.
5. Freeze all predictions with the current UTC clock:

   ```bash
   python scripts/freeze_enforcement_v3_predictions.py freeze \
     --cases /private/blind-cases.json \
     --predictions /private/predictions.json \
     --output /private/prediction-freeze.json
   ```

6. Only after the freeze exists should independent outcome review progress to `INDEPENDENTLY_REVIEWED`.
7. Evaluate the unchanged cohort against the later de-identified intake file:

   ```bash
   python scripts/freeze_enforcement_v3_predictions.py evaluate \
     --intake /private/safe-intake-reviewed.json \
     --freeze /private/prediction-freeze.json \
     --output /private/blind-evaluation.json
   ```

## What is frozen

The blind case set contains only the de-identified `caseId`, normalized `caseFacts`, and a SHA-256 digest of those facts. Provenance, reviewer history, outcome labels, source-record identifiers, and reviewer identifiers are excluded.

The prediction freeze contains the complete case cohort, one prediction per case, the case-facts digest, a canonical prediction digest, the prediction schema/engine/prompt contract, the blind case-set creation timestamp, the UTC freeze timestamp, and a content-derived `freezeId`. The freeze timestamp is required to be equal to or later than the case-set creation timestamp.

## Fail-closed rules

The protocol rejects evaluation when any of the following occurs:

- the blind export contains a reviewed/rejected record or any outcome label;
- any cohort case lacks a prediction;
- predictions contain extra case IDs outside the cohort;
- the freeze is backdated earlier than blind case-set generation;
- a prediction or freeze manifest changes without matching its canonical digest;
- the intake dataset version changes;
- cases are added to or removed from the frozen cohort;
- normalized case facts change after prediction freeze;
- a reviewed outcome timestamp is not strictly later than the prediction freeze;
- a non-reviewed or rejected record contains an outcome label.

These checks are intended to stop accidental leakage, cherry-picking, cohort drift, and ordinary post-hoc rewriting. They do not substitute for an external timestamp authority, independent repository custody, or a preregistered study protocol when stronger evidentiary guarantees are required.

## Interpretation

The final report wraps the existing Enforcement v3 outcome evaluator. Its metrics remain descriptive. A successful protocol validation means the evaluated prediction snapshot satisfies the local blind-freeze contract. It does **not** by itself prove production readiness, legal validity, statistical calibration, or causal generalizability.

Keep blind case sets, prediction freezes, reviewed intake corpora, and evaluation reports outside the public repository unless they contain only data that has separately been approved for publication.
