# Enforcement Intelligence v3: Outcome Evaluation Gate

## Purpose

The deterministic benchmark answers whether Visable extracts facts, classifies the currently supported violation concepts, fails closed, and computes the versioned legal baseline consistently. It does **not** establish whether an AI-predicted administrative outcome is accurate.

Prediction quality may be evaluated only against outcomes that were independently reviewed from an official or verified administrative record. Until those records exist, the correct evaluation state is `NOT_EVALUABLE`.

## Ground-truth contract

The canonical schema is `backend/data/enforcement/outcome_ground_truth.schema.json`. The checked-in `outcome_ground_truth.template.json` is deliberately empty.

Every populated record must:

- use a pseudonymous `caseId` rather than a person's identifier;
- be marked `INDEPENDENTLY_REVIEWED`;
- record a review date and reviewer role;
- set `independentFromPrediction` to `true`;
- identify an eligible official or verified administrative source by authority and record ID;
- contain only the scoreable outcome components actually established by that source;
- omit raw case narrative, names, passport/registration numbers, contact details, addresses, and model/prediction output.

Synthetic, LLM-generated, prediction-derived, or unreviewed labels are not eligible ground truth. They may be useful for software unit tests, but they must never enter the outcome corpus used to claim prediction quality.

## What the evaluator reports

`backend/services/enforcement_outcome_evaluation.py` reports component-specific descriptive metrics only when reviewed records and matching predictions exist:

- ground-truth count, matched prediction count, and prediction coverage;
- prediction availability among matched cases;
- monetary predicted-range interval coverage where an actual monetary outcome is recorded;
- point-estimate MAE only for predictions that actually contain a point estimate;
- primary-disposition top-1 accuracy and ranked top-k recall where a primary disposition is independently recorded;
- observed success rate within the product's existing qualitative confidence buckets.

The evaluator intentionally does **not** emit a single `overallAccuracy`, a numeric probability-calibration score, or a production-readiness verdict. Those would collapse different failure modes or imply probability semantics that the product does not expose.

## Empty and incomplete data

An empty reviewed dataset returns:

```json
{
  "status": "NOT_EVALUABLE",
  "reason": "NO_REVIEWED_OUTCOME_GROUND_TRUTH"
}
```

A populated ground-truth dataset with no matching prediction records returns `NOT_EVALUABLE` with `NO_MATCHED_PREDICTIONS`. Missing monetary or disposition labels do not get imputed. Metrics for a component remain absent/null when there is no valid denominator.

## Collection workflow

Outcome collection should happen outside the public repository when records are confidential or contain personal information. The source material should be reviewed and reduced to the schema's de-identified fields before any benchmark dataset is created. Public source URLs are optional because verified administrative records may not be publicly accessible; authority and stable record ID remain mandatory.

Do not use Visable's own prediction as a reviewer aid for labeling the record. `independentFromPrediction=true` is a substantive requirement, not decorative metadata.

## CLI

The evaluator can be exercised with:

```bash
python3 scripts/evaluate_enforcement_v3_outcomes.py
```

With the checked-in empty template this must return `NOT_EVALUABLE`. A private reviewed dataset can be supplied with `--ground-truth`, and a JSON object mapping `caseId` to public `EnforcementPrediction` objects can be supplied with `--predictions`.

## Gate before changing Prediction v3 behavior

Before widening the prediction model's claims, narrowing predicted monetary ranges, adding point estimates more aggressively, or ranking dispositions more strongly, collect independently reviewed outcome records and run this evaluator. Model changes should be compared on the same reviewed records and reported by component, with regressions visible rather than hidden inside one aggregate score.
