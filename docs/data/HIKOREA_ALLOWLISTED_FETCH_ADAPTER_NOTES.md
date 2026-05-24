# HiKorea Allowlisted Fetch Adapter Notes

## What This Adapter Does

PR-C3 adds a default-off fetch adapter to `scripts/check_source_updates.py` for
catalog dry-runs. The adapter is limited to future monitor candidates from the
HiKorea and Korea Immigration Service catalogs.

The adapter can extract a small index snapshot from an allowlisted public page:

- HTML title
- normalized visible body text hash
- source id, URL, host, state, and reason
- `fetched_at` only when a fetch actually occurs

This is intended for human update briefing and change detection experiments. It
does not update legal guidance, production datasets, or user-facing content.

## What Remains Disabled

- Scheduled monitoring remains disabled.
- Catalog records remain `monitor_enabled=false`.
- No GitHub Actions workflow is added.
- No UI path is added.
- No `visa_data.json` or production dataset is changed.
- No form submission, login flow, CAPTCHA flow, JavaScript execution, or
  personal-data flow is supported.
- Legacy `data/source_registry.json` network entries still do not fetch; this
  adapter is scoped to catalog dry-runs.

## Host Allowlist Policy

`--allow-network` can only fetch records that satisfy all adapter checks:

- `monitor_candidate=true`
- `activation_status` is `candidate_only` or `allowlist_test`
- `scrape_allowed=true`
- `requires_login=false`
- `source_type` is one of the public index-style types supported by this PR
- `domain` is one of the reviewed candidate domains
- the URL host is an official `hikorea.go.kr` or `immigration.go.kr` host
- the host is present in the computed allowlist for the loaded catalog candidates

Unexpected hosts are reported as `blocked_host`. Redirects are only followed if
the redirect target host is also in the computed allowlist.

## Network Guardrails

Network access is off unless `--allow-network` is passed. Even then, the adapter:

- uses GET only
- sends a polite Paradiso source-monitor research User-Agent
- uses a short configurable timeout
- limits response size
- does not store cookies
- does not submit forms
- does not execute JavaScript
- extracts only basic text suitable for a content hash

## Why Tests Use Fixtures And Mocks

Tests must not contact HiKorea, immigration.go.kr, Visa Portal, Soci-Net, or
linked services. The allowed fetch path is tested with fixture HTML and a fake
fetcher injected into the catalog dry-run helper. Blocking behavior is tested
with local catalog fixtures and does not require network access.

## Future Manual Smoke Test

After exact public index URLs and robots review are completed in a later PR, an
operator can run a manual local smoke test similar to:

```bash
python3 scripts/check_source_updates.py \
  --catalog-dry-run \
  --allow-network \
  --json
```

This command should only be used after the relevant catalog candidate has an
operator-pinned public URL and the host remains inside the official allowlist.

## Proposed PR-C4 Plan

PR-C4 should generate human-readable update briefs from source monitor JSON
output. It should remain preview-only by default, avoid live network in tests,
and make clear that detected source changes require human review before any
downstream legal or production data update.
