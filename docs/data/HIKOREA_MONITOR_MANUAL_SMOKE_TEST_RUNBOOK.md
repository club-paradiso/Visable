# HiKorea Monitor Manual Smoke Test Runbook

## Purpose

This runbook describes how an operator can manually smoke-test the
HiKorea/Korea Immigration Service source monitor pipeline from a local checkout.
The smoke test connects three default-off pieces:

1. `scripts/check_source_updates.py --catalog-dry-run`
2. saved source monitor JSON output
3. `scripts/generate_source_update_brief.py`

The goal is to confirm that the local source monitor output can be captured and
turned into a human-readable Markdown brief.

## Non-Goals

This smoke test does not:

- verify legal correctness
- create or update user-facing legal guidance
- update `visa_data.json` or production datasets
- create GitHub Issues
- enable scheduled monitoring
- broaden the fetch allowlist
- submit forms, log in, run e-Application flows, reserve visits, or check
  residence-card validity

## Preconditions

Before running this smoke test, confirm:

- PR-C2 candidate metadata exists in the catalogs, including
  `monitor_candidate`, `activation_status`, and `proposed_monitor_mode`.
- PR-C3 allowlisted fetch adapter exists in `scripts/check_source_updates.py`.
- PR-C4 brief generator exists at `scripts/generate_source_update_brief.py`.
- The operator understands this is source-monitor plumbing validation, not legal
  verification.
- The operator has reviewed the target catalog records and understands that
  `monitor_enabled` remains `false`.

## Safety Rules

- Do not fetch transaction pages.
- Do not fetch login pages.
- Do not use e-Application, visit-reservation, or residence-card validity-check
  flows.
- Do not submit forms.
- Do not create GitHub Issues.
- Do not enable scheduled monitoring.
- Do not make automatic user-facing updates.
- Do not modify `visa_data.json`, production datasets, or UI files.
- Do not treat a detected source change as legal advice or as verified legal
  content.

## Exact Manual Commands

Run commands from the repository root.

### No-network dry-run

```bash
python3 scripts/check_source_updates.py \
  --catalog-dry-run \
  --json \
  --list-disabled
```

Expected: no HTTP requests. Candidate records should report states such as
`skipped` with reason `network_disabled`, or `candidate_disabled` for
non-candidates.

### Allow-network smoke test

Only run this after confirming that candidate URLs are operator-pinned public
notice/index URLs and remain inside the allowlisted official hosts.

```bash
python3 scripts/check_source_updates.py \
  --catalog-dry-run \
  --allow-network \
  --json \
  --list-disabled \
  --fetch-timeout-seconds 5 \
  --fetch-max-bytes 524288
```

Expected: only records that pass the C3 allowlist checks may be fetched. Missing
candidate URLs should report `no_url`. Unexpected hosts should report
`blocked_host`.

### Save source monitor JSON output

```bash
mkdir -p tmp/source-monitor-smoke

python3 scripts/check_source_updates.py \
  --catalog-dry-run \
  --json \
  --list-disabled \
  > tmp/source-monitor-smoke/source_monitor_no_network.json
```

For an explicit allow-network smoke test:

```bash
python3 scripts/check_source_updates.py \
  --catalog-dry-run \
  --allow-network \
  --json \
  --list-disabled \
  --fetch-timeout-seconds 5 \
  --fetch-max-bytes 524288 \
  > tmp/source-monitor-smoke/source_monitor_allow_network.json
```

### Generate a Markdown brief

```bash
python3 scripts/generate_source_update_brief.py \
  --input tmp/source-monitor-smoke/source_monitor_no_network.json \
  --output tmp/source-monitor-smoke/source_update_brief.md \
  --format markdown
```

Issue preview is local Markdown framing only; it does not create an issue:

```bash
python3 scripts/generate_source_update_brief.py \
  --input tmp/source-monitor-smoke/source_monitor_no_network.json \
  --output tmp/source-monitor-smoke/source_update_issue_preview.md \
  --format markdown \
  --issue-preview
```

### Optional helper command

The helper chains the JSON monitor run and Markdown generation. It defaults to
no network:

```bash
python3 scripts/run_hikorea_monitor_smoke.py
```

To run the explicit allow-network smoke path:

```bash
python3 scripts/run_hikorea_monitor_smoke.py --allow-network
```

The helper writes files under `tmp/source-monitor-smoke/`, which is ignored by
Git.

## Expected Outputs

Expected local files:

- `tmp/source-monitor-smoke/<run>_source_monitor.json`
- `tmp/source-monitor-smoke/<run>_source_update_brief.md`

Example JSON result shapes:

```json
{
  "source_id": "hikorea_notice_index",
  "state": "skipped",
  "reason": "network_disabled"
}
```

```json
{
  "source_id": "unexpected_host_candidate",
  "state": "blocked",
  "reason": "blocked_host"
}
```

```json
{
  "source_id": "hikorea_notice_index",
  "state": "fetched",
  "reason": "ok",
  "content_hash": "sha256:..."
}
```

Example Markdown brief sections:

```markdown
# Paradiso Source Update Brief - YYYY-MM-DD

## Summary Counts
## High-Priority Changes
## Medium-Priority Changes
## Low-Priority / No-Op
## Blocked / Skipped Sources
## Records Requiring Human Review
## Recommended Next Action
```

## Failure Modes

- `blocked_host`: the URL host or redirect target is outside the computed
  official allowlist.
- `network_disabled`: `--allow-network` was not passed; this is expected for the
  default smoke path.
- `requires_login`: the record requires login and must not be fetched.
- `scrape_not_allowed`: the record is not approved for scraping.
- `response_too_large`: the response exceeded the configured byte limit.
- `no_baseline`: the source has no established baseline and needs human review
  before future changes can be interpreted.

## Operator Checklist

Before considering any next PR:

- Review the source monitor JSON.
- Review the generated Markdown brief.
- Confirm no service portal was fetched.
- Confirm no login, transaction, e-Application, visit-reservation, or
  validity-check flow was touched.
- Confirm no GitHub Issue was created.
- Confirm no user-facing data update was made.
- Confirm `monitor_enabled` remains `false` in both catalogs.
- Decide whether C6 `workflow_dispatch` is safe to attempt.

## Next PR Recommendation

C6 should add a default-off GitHub Actions `workflow_dispatch` only. It should
not add a schedule. It should not create GitHub Issues automatically. It should
produce artifacts for operator review and preserve all C3/C4 safety gates.
