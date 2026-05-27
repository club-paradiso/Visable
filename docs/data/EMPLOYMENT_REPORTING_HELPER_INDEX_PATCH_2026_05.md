# Employment Reporting Helper Index Patch - 2026.5

## Purpose

This PR prepares the frontend patch that renders HiKorea-like employment-information reporting steps inside the existing job/industry-code modal in `index.html`.

The helper flow is based on the previously added `data/employment_reporting_helper_flow.json` seed.

## Intended user-facing flow

The modal should explain that HiKorea employment-information reporting is not just a generic job-code lookup. It asks users to handle:

1. reporting-target stay status,
2. profit-making activity status,
3. occupation lookup using KSCO8,
4. industry lookup using KSIC11,
5. annual-income band,
6. reporting route: visit reservation flow or electronic civil petition flow.

## Scope

This is a frontend/UI guidance patch only.

It does not change:

- `visa_data.json`,
- `backend/data/visas.json`,
- `verified`,
- `needsManualReview`,
- full KSCO8/KSIC11 table coverage.

## Patch method

Because `index.html` is a large single-file frontend, this PR adds a deterministic patch helper:

- `scripts/apply_employment_reporting_helper_index_patch.py`

The script inserts a small guidance block into the existing job-code modal after the natural-language search row.

## Validation expectation

Run:

```bash
python3 scripts/apply_employment_reporting_helper_index_patch.py
python3 -m json.tool data/employment_reporting_helper_flow.json > /tmp/employment_reporting_helper_flow_check.json
git diff -- index.html scripts/apply_employment_reporting_helper_index_patch.py docs/data/EMPLOYMENT_REPORTING_HELPER_INDEX_PATCH_2026_05.md
```

Then commit the resulting `index.html` diff.

## Important limitation

The committed script prepares and applies the deterministic patch, but the final PR should include the resulting `index.html` modification before merge.
