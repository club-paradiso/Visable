# HiKorea Source Monitor Extension Notes

## What this PR enables
- Adds a default-off dry-run catalog monitor layer in `scripts/check_source_updates.py` via `--catalog-dry-run`.
- Loads both catalogs:
  - `data/sources/hikorea_source_catalog.json`
  - `data/sources/immigration_notice_sources.json`
- Validates required monitor metadata fields and reports validation errors.
- Filters monitor-eligible records conservatively.
- Produces a dry-run summary grouped by domain and `source_type`.

## What remains disabled
- No scheduled monitoring is enabled.
- No GitHub Actions workflow was added or changed.
- No live fetcher has been implemented for these catalogs.

## How `--allow-network` is guarded
- Network use remains default-off.
- Existing `--allow-network` behavior for legacy `source_registry.json` remains unchanged.
- The catalog dry-run path performs no HTTP requests and is report-only.

## Why no live monitoring is enabled yet
- Source metadata still includes many `monitor_enabled=false`, `scrape_allowed=false`, or `requires_login=true` records.
- Legal/admin-sensitive and link-only service pages must remain non-automated.
- Conservative activation requires explicit policy and per-source readiness review.

## Metadata needed before enabling monitoring
Each source must have:
- `monitor_enabled=true`
- `scrape_allowed=true`
- `requires_login=false`
- stable machine-readable extraction mode and review notes
- approved legal sensitivity and operational policy sign-off

## Next PR recommendation
- Add an explicit allowlist-based fetch adapter behind `--allow-network` for a tiny subset of publicly accessible, scrape-allowed, non-login notice pages, with rate limits and test fixtures.
