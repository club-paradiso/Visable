# HiKorea Monitor Workflow C9 Notes

Date: 2026-05-26
Branch: `ci/polish-hikorea-source-monitor-workflow`

## Summary

C9 polishes the manual HiKorea/Korea Immigration Service source monitor smoke workflow output without changing its activation model.

The workflow remains:

- `workflow_dispatch` only
- default no-network
- artifact-only
- report-only

## Workflow Summary Output

The workflow now writes a GitHub Actions step summary with:

- mode: `no-network` or `allow-network`
- run label
- artifact bundle name
- source monitor JSON generated status
- Markdown brief generated status
- command log generated status
- workflow metadata generated status
- safety note that no GitHub Issue is created automatically
- safety note that no user-facing legal update is made automatically

This is intended to help operators confirm the run shape before downloading artifacts.

## Artifact Review Guidance

Operators should inspect the artifact bundle named:

```text
hikorea-source-monitor-smoke-${{ github.run_id }}-${{ github.run_attempt }}
```

Recommended review order:

1. `*_workflow_metadata.json`
2. `*_command.log`
3. `*_source_monitor.json`
4. `*_source_update_brief.md`

The metadata and command log confirm the run mode and safety posture. The JSON report is the machine-readable monitor output. The Markdown brief is the human-readable review surface.

## Safety Confirmations

- No `schedule` trigger was added.
- No `push` trigger was added.
- No `pull_request` trigger was added.
- `allow_network` still defaults to `false`.
- No GitHub Issue creation was added.
- No `issues: write` permission was requested.
- No automatic user-facing update path was added.
- No catalog `monitor_enabled` values were changed.
- No UI files were changed.
- `visa_data.json`, `backend/data/visas.json`, and `doc_master.json` were not changed.
- No dependencies were added.
- No live HTTP smoke was performed for this PR.

## Next Recommended PR

Use C10 to run the polished manual workflow with `allow_network=false`, verify the new step summary in GitHub Actions, and document the resulting artifact review. Keep C10 report-only unless an operator explicitly approves a separate catalog candidate update.
