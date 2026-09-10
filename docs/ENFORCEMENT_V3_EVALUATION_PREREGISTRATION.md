# Enforcement Intelligence v3 evaluation preregistration

The blind prediction freeze prevents outcome labels from being used to rewrite predictions. This preregistration layer prevents a second, quieter form of post-hoc tuning: changing which metrics are reported or lowering the sample threshold after seeing the results.

## Sequence

1. Create the de-identified pre-outcome intake corpus.
2. Export the complete blind case set.
3. Create an evaluation plan **after the case set exists and no later than prediction freeze**.
4. Freeze one prediction for every blind case.
5. Allow independent outcome review to proceed.
6. Evaluate with the frozen predictions and the preregistered plan.

Example:

```bash
python scripts/evaluate_enforcement_v3_preregistered.py create-plan \
  --cases /private/blind-cases.json \
  --metric PREDICTION_AVAILABILITY=20 \
  --metric DISPOSITION_TOP1_ACCURACY=20 \
  --metric MONETARY_INTERVAL_COVERAGE=20 \
  --output /private/evaluation-plan.json
```

The numbers above are examples only. Visable does **not** declare 20, 30, or any other sample size statistically sufficient. The evaluator requires the operator or study design to choose the minimum eligible-case count before outcomes are reviewed.

After prediction freeze and later independent outcome review:

```bash
python scripts/evaluate_enforcement_v3_preregistered.py evaluate \
  --plan /private/evaluation-plan.json \
  --freeze /private/prediction-freeze.json \
  --intake /private/safe-intake-reviewed.json \
  --output /private/preregistered-report.json
```

## Available preregistered metrics

- `PREDICTION_AVAILABILITY`
- `MONETARY_INTERVAL_COVERAGE`
- `MONETARY_POINT_MAE_KRW`
- `DISPOSITION_TOP1_ACCURACY`
- `DISPOSITION_TOPK_RECALL`
- `QUALITATIVE_CONFIDENCE_OBSERVED_SUCCESS`

Each metric has an explicit `minimumEligibleCases`. When the denominator for that metric is below the preregistered minimum, its value is replaced by `null` and its status is `SUPPRESSED_MINIMUM_SAMPLE`. The threshold is not silently lowered.

For qualitative confidence, the same preregistered minimum is applied separately to each confidence bucket. A bucket with too few evaluated cases remains suppressed even when another bucket is large enough.

## Fixed reporting policy

The plan schema and runtime validator permanently require:

- below-minimum metrics are suppressed;
- cohort attrition is reported;
- no performance pass/fail verdict is emitted;
- no probability-calibration claim is emitted.

These are not user-configurable switches. A plan that changes any of them is invalid.

The resulting report always carries cohort, reviewed, rejected, and pending counts. This prevents a small apparently successful reviewed subset from being presented without the size of the original frozen cohort.

## Integrity and chronology

The plan is bound to `datasetVersion`, `caseSetId`, and the blind case-set creation timestamp. Its `planId` is derived from canonical plan content. Changing a metric, minimum sample, timestamp, or policy without recomputing the plan changes the identity and fails validation.

At evaluation time, the plan must match the prediction freeze and its `createdAt` must be no later than `frozenAt`. The blind evaluation is then rerun from the safe intake and frozen prediction bundle rather than accepting a caller-supplied metrics object.

As with the blind freeze itself, local timestamps and hashes are tamper-evident workflow controls, not external notarization. A stronger study can additionally use independent custody, a public preregistration service, or an external timestamp authority.

## What this does not establish

A valid preregistered report does not prove production readiness, legal correctness, statistical significance, causal generalizability, or numeric probability calibration. It only establishes that the locally enforced cohort, prediction snapshot, metric selection, and disclosure thresholds conform to the registered evaluation contract.
