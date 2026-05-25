# HiKorea Manual Workflow Notes

Date: 2026-05-25
Branch: `ci/manual-hikorea-source-monitor-smoke`

## Purpose

PR-C7 adds a manual GitHub Actions smoke workflow for the HiKorea/Korea Immigration Service source monitor pipeline. The workflow turns the local C6 smoke-test process into an operator-triggered artifact generator.

The workflow is:

- `.github/workflows/hikorea-source-monitor-smoke.yml`
- `workflow_dispatch` only
- report-only
- artifact-producing only

## Manual Trigger Only

The workflow is triggered only by `workflow_dispatch`. It does not run on `push`, `pull_request`, or any automatic event.

## No Cron

No `schedule` trigger is present. This PR does not enable scheduled monitoring, recurring checks, or background source surveillance.

## No Automatic Issue Creation

The workflow does not create GitHub Issues. It calls the existing local smoke helper, which writes JSON and Markdown files under `tmp/source-monitor-smoke/`, then uploads those files as workflow artifacts.

The workflow job has only `contents: read` permission and does not request `issues: write`.

## No Automatic User-Facing Updates

The workflow never commits generated output back to the repository and never updates user-facing legal guidance. Any detected source change remains an operator-review signal only.

This PR does not modify:

- `visa_data.json`
- `backend/data/visas.json`
- production datasets
- UI files
- catalog `monitor_enabled` values

## `allow_network` Input

The workflow has one manual input:

- `allow_network`
- type: boolean
- default: `false`

When `allow_network=false`, the workflow runs the existing helper without `--allow-network`. This is the default path. It produces:

- source monitor JSON
- generated Markdown brief
- command log
- workflow metadata JSON

When `allow_network=true`, the workflow passes `--allow-network` to `scripts/run_hikorea_monitor_smoke.py`. The existing `scripts/check_source_updates.py` adapter guardrails remain in force. That path is only for operator-triggered smoke tests and is still artifact-only.

## Safety Guardrails

The workflow must not:

- submit forms
- access login pages
- access CAPTCHA flows
- access e-Application flows
- access visit-reservation flows
- access residence-card validity-check flows
- access personal-data flows
- create GitHub Issues
- commit generated output
- enable scheduled monitoring
- change catalog `monitor_enabled` values
- update production data

When `allow_network=true`, only already allowlisted, public, non-login, non-transaction candidate records may pass the adapter checks.

## Artifacts

The workflow uploads one artifact bundle named:

```text
hikorea-source-monitor-smoke-${{ github.run_id }}-${{ github.run_attempt }}
```

The artifact bundle includes:

- `tmp/source-monitor-smoke/*_source_monitor.json`
- `tmp/source-monitor-smoke/*_source_update_brief.md`
- `tmp/source-monitor-smoke/*_command.log`
- `tmp/source-monitor-smoke/*_workflow_metadata.json`

These outputs are for human review. They are not committed to the repository by the workflow.

## Next C8 Recommendation

Use C8 to run the manual workflow in GitHub Actions with `allow_network=false`, download the uploaded artifacts, and document the remote runner result. Keep C8 report-only. Do not add a cron schedule or automatic issue creation. Consider a separate, later PR for an explicitly reviewed `allow_network=true` remote smoke only after candidate URLs are pinned and operator safety review is complete.
