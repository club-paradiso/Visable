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

## Step Summary

C9 adds a GitHub Actions step summary for each manual run. The summary appears on the workflow run page and records:

- mode: `no-network` or `allow-network`
- run label
- artifact bundle name
- whether source monitor JSON was generated
- whether the Markdown brief was generated
- whether the command log was generated
- whether workflow metadata was generated
- safety notes confirming no automatic GitHub Issue creation and no automatic user-facing legal update

The step summary is an operator convenience only. The artifact files remain the audit source for detailed review.

## Operator Artifact Review

After a manual run completes, an operator should open the workflow run, read the step summary, then download the artifact bundle. Review these files in order:

1. `*_workflow_metadata.json` to confirm `allow_network`, run label, and safety booleans.
2. `*_command.log` to confirm the helper command and whether network was disabled or explicitly allowed.
3. `*_source_monitor.json` to inspect machine-readable monitor results.
4. `*_source_update_brief.md` to inspect the human-readable source update brief.

No artifact should be treated as a user-facing legal update. Any source or data follow-up requires a separate reviewed PR.

## Next Recommendation

Use the polished workflow for another manual `allow_network=false` run and confirm the step summary is readable in GitHub Actions. Keep any later `allow_network=true` smoke manual, artifact-only, and explicitly reviewed before use.
