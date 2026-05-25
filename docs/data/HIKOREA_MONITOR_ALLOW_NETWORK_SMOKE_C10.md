# HiKorea Monitor Allow-Network Smoke C10

Report date: 2026-05-26 KST
Branch: `docs/hikorea-monitor-allow-network-smoke-c10`

## Summary

C10 records the first manual GitHub Actions run of the HiKorea/Korea Immigration Service source monitor smoke workflow with `allow_network=true`.

- Workflow: `HiKorea Source Monitor Smoke`
- Workflow file: `.github/workflows/hikorea-source-monitor-smoke.yml`
- Run ID: `26409549273`
- Run URL: https://github.com/lucanomics/Paradiso/actions/runs/26409549273
- Trigger: `workflow_dispatch`
- Branch: `main`
- Head SHA: `eca96f2fa17b26ea08aa049877cd223b5f0fc374`
- Run number: `3`
- Run attempt: `1`
- Run conclusion: `success`
- Job: `smoke`
- Job conclusion: `success`

The workflow metadata and command log confirm `allow_network=true`. The helper ran with `--allow-network`, but no monitored source was fetched because all monitor-candidate records still had `url=null`.

## Job Steps

The `smoke` job completed successfully. Observed successful steps:

- `Checkout`
- `Set up Python`
- `Run HiKorea/KIS monitor smoke helper`
- `Validate generated smoke artifacts`
- `Write workflow summary`
- `Upload smoke artifacts`

## Commands Observed

The command log recorded:

```bash
python3 scripts/run_hikorea_monitor_smoke.py --run-label workflow_26409549273_1 --output-dir tmp/source-monitor-smoke --allow-network
```

The helper invoked the source monitor as:

```bash
python3 scripts/check_source_updates.py --catalog-dry-run --json --list-disabled --fetch-timeout-seconds 5.0 --fetch-max-bytes 524288 --allow-network
```

The helper invoked the Markdown brief generator as:

```bash
python3 scripts/generate_source_update_brief.py --input tmp/source-monitor-smoke/workflow_26409549273_1_source_monitor.json --output tmp/source-monitor-smoke/workflow_26409549273_1_source_update_brief.md --format markdown
```

## Artifacts

One artifact bundle was observed:

- Name: `hikorea-source-monitor-smoke-26409549273-1`
- Artifact ID: `7201507373`
- Size: `3864` bytes
- Digest: `sha256:d92442ed6844c1a3ae2357488065aca5a81dd3796b9ad02a6e7c96aa0daaef40`
- Created: `2026-05-25T16:09:44Z`
- Expires: `2026-08-23T16:09:34Z`

The artifact ZIP contained:

- `workflow_26409549273_1_source_monitor.json`
- `workflow_26409549273_1_source_update_brief.md`
- `workflow_26409549273_1_command.log`
- `workflow_26409549273_1_workflow_metadata.json`

The source monitor JSON was produced. The Markdown brief was produced. The command log and workflow metadata JSON were produced.

## Source Monitor Result

The generated source monitor JSON reported:

- `allow_network: true`
- `mode: catalog_dry_run`
- eligible records: 0
- disabled records: 43
- result records: 43
- state counts: `skipped=43`
- reason counts: `candidate_disabled=38`, `no_url=5`
- fetched records: 0
- blocked records: 0

No redirect was blocked. No response was oversized. No response timed out. No fetch attempt reached a network request for a monitored source because the only candidate records had no pinned URLs.

## Candidate Records Tested

Five monitor-candidate records reached the allow-network path but were skipped because they had no URL:

| Catalog | Source ID | URL | State | Reason |
| --- | --- | --- | --- | --- |
| `hikorea_source_catalog` | `hikorea_civil_petition_forms_index` | `null` | `skipped` | `no_url` |
| `immigration_notice_sources` | `hikorea_notice_index` | `null` | `skipped` | `no_url` |
| `immigration_notice_sources` | `hikorea_materials_index` | `null` | `skipped` | `no_url` |
| `immigration_notice_sources` | `immigration_service_notice_index` | `null` | `skipped` | `no_url` |
| `immigration_notice_sources` | `immigration_service_press_index` | `null` | `skipped` | `no_url` |

The remaining 38 catalog records were skipped as `candidate_disabled`.

## Fetched, Blocked, Skipped, Disabled

- Fetched: none
- Blocked: none
- Skipped with `no_url`: 5 records
- Disabled with `candidate_disabled`: 38 records

Service portals and sensitive flows remained disabled. This included HiKorea root, e-Application, visit reservation, residence-card validity check, office lookup, login-adjacent portals, and transaction-oriented surfaces.

## Brief Summary

The generated Markdown brief reported:

- Total records: 43
- High-priority changes: 0
- Medium-priority changes: 0
- Review-needed records: 0
- Blocked or safety-skipped records: 0
- Informational skipped records: 43
- Low-priority/no-op records: 0
- Changed records requiring review: 0
- Recommended next action: no source-change action is needed from this report

## Safety Confirmation

- `allow_network=true` was confirmed in workflow metadata and command log.
- Only allowlisted candidates were eligible for fetching.
- No monitored source was fetched because candidate URLs remain unpinned.
- No service portal was fetched.
- No login page was fetched.
- No transaction page was fetched.
- No e-Application page was fetched.
- No visit-reservation page was fetched.
- No residence-card validity-check page was fetched.
- No redirect was blocked.
- No oversized response was encountered.
- No timeout was encountered.
- No GitHub Issue was created.
- No scheduled monitoring was enabled.
- No schedule or cron trigger was added.
- No automatic user-facing update was performed.
- No production data was updated.
- No UI file was changed by this PR.
- `visa_data.json`, `backend/data/visas.json`, `doc_master.json`, and production datasets were not changed by this PR.
- Catalog `monitor_enabled` values were not changed.
- `monitor_enabled` remains `false` for all 33 records in `data/sources/hikorea_source_catalog.json`.
- `monitor_enabled` remains `false` for all 10 records in `data/sources/immigration_notice_sources.json`.

Normal GitHub Actions infrastructure network access occurred for checkout, action setup, and artifact upload. The source-monitor safety result is that no monitored HiKorea/KIS/source-catalog HTTP fetch occurred despite allow-network mode being enabled.

## Next Recommended PR

Use the next PR to decide whether to pin one narrow, public, non-login, non-transaction candidate URL for a future manual allow-network smoke. Keep that PR conservative: update only catalog metadata if approved, keep `monitor_enabled=false`, and continue to require `workflow_dispatch` before any network smoke.
