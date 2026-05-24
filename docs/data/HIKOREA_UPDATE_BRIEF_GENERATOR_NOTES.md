# HiKorea Update Brief Generator Notes

## What This Adds

PR-C4 adds `scripts/generate_source_update_brief.py`, a standard-library script
that turns saved source monitor JSON output into a human-readable Markdown
brief. It is intended to help operators review source-monitor signals before
any downstream action is considered.

The generator does not fetch sources, open GitHub Issues, enable monitoring, or
modify production data.

## Input Format

The script accepts JSON output from `scripts/check_source_updates.py`:

```bash
python3 scripts/generate_source_update_brief.py \
  --input path/to/source_monitor_result.json
```

The input must be a JSON object with a `results` list. Records may come from the
legacy source registry path or from the catalog dry-run path. The generator
recognizes fields such as:

- `source_id` or `id`
- `source_type` or `type`
- `state`
- `reason`
- `legal_sensitivity`
- `title`
- `url`
- `content_hash`
- `checked_at` or `fetched_at`

## Output Format

The default output is Markdown printed to stdout. Use `--output` to write a file:

```bash
python3 scripts/generate_source_update_brief.py \
  --input path/to/source_monitor_result.json \
  --output docs/generated/source-update-brief.md \
  --format markdown
```

Generated briefs include:

- title with date
- summary counts
- high-priority changes
- medium-priority changes
- low-priority/no-op records
- blocked or skipped sources
- records requiring human review
- recommended next action
- a disclaimer that detected changes are not automatically user-facing legal
  updates

## Priority Rules

- `changed` or `missing` records with `legal_sensitivity=high` are high
  priority.
- `notice_index` records with `changed` state are medium priority unless their
  legal sensitivity is high.
- `network_disabled`, `monitor_disabled`, `candidate_disabled`, `not_configured`,
  and `no_url` are informational skipped states.
- `blocked_host`, `requires_login`, `scrape_not_allowed`, unsupported domains,
  unsupported source types, and oversized responses are blocked/safety states.
- `no_baseline` records require human review but are not automatically high
  priority.

These categories support triage only. They do not create legal advice and do not
promote any detected change into production guidance.

## GitHub Issue Preview Default

`--issue-preview` adds issue-preview framing to the Markdown only:

```bash
python3 scripts/generate_source_update_brief.py \
  --input path/to/source_monitor_result.json \
  --issue-preview
```

No GitHub token is required. The script does not call the GitHub API and does
not create real Issues. A future PR can decide whether to add explicit manual
Issue creation flags after review.

## Connection To Future GitHub Actions

This PR does not add GitHub Actions or scheduled automation. A future workflow
could run the source monitor, save JSON output, and call this generator to
produce a Markdown artifact or issue preview. That workflow should remain
default-off until operators confirm source URLs, robots review, rate limits, and
review ownership.

## Safety Guardrails

- No live HTTP is performed by the generator or its tests.
- No scheduled monitoring is enabled.
- No GitHub Issue is created by default or in tests.
- No `visa_data.json`, production dataset, or UI file is modified.
- Detected changes require human review before any user-facing legal or data
  update.

## Next PR Recommendation

The next small PR should either:

- add an optional manual smoke-test procedure for one operator-pinned public
  index URL, or
- add a default-off scheduled workflow proposal that only produces artifacts and
  does not open issues or update production data automatically.
