# HiKorea Monitor URL Fetch Smoke C12

Report date: 2026-05-26 KST
Branch: `docs/hikorea-monitor-url-fetch-smoke-c12`

## Summary

C12 records the first manual HiKorea/Korea Immigration Service source monitor smoke workflow run after C11 populated reviewed public URLs for the five conservative monitor candidates.

The workflow ran successfully with `allow_network=true`, and all expected artifacts were generated. However, the source monitor did not fetch any reviewed candidate URL. The generated source monitor JSON reported every catalog record as `skipped` with reason `candidate_disabled`, including the five C11 URL-reviewed candidates.

This is a safe result, but it is not a successful URL-fetch smoke. It shows that the current manual smoke path still blocks `activation_status="url_reviewed_candidate"` records while `monitor_enabled=false`.

## Workflow Run

- Workflow: `HiKorea Source Monitor Smoke`
- Workflow file: `.github/workflows/hikorea-source-monitor-smoke.yml`
- Run ID: `26411389727`
- Run URL: https://github.com/lucanomics/Paradiso/actions/runs/26411389727
- Trigger: `workflow_dispatch`
- Branch: `main`
- Head SHA: `31d7dd091f3d5f2c6da110155cdce975de8f85c3`
- Created: `2026-05-25T17:00:27Z`
- Updated: `2026-05-25T17:00:40Z`
- Run conclusion: `success`
- Job: `smoke`
- Job URL: https://github.com/lucanomics/Paradiso/actions/runs/26411389727/job/77746392176
- Job conclusion: `success`

## Artifact

- Artifact: `hikorea-source-monitor-smoke-26411389727-1`
- Artifact ID: `7202135787`
- Size: `4009` bytes
- Digest: `sha256:c9d5b8a62ae9ecabe963f3a71195c63e879e53ce93042e68864142ca0f5318bc`
- Created: `2026-05-25T17:00:37Z`
- Expires: `2026-08-23T17:00:28Z`

The artifact contained:

- `workflow_26411389727_1_source_monitor.json`
- `workflow_26411389727_1_source_update_brief.md`
- `workflow_26411389727_1_command.log`
- `workflow_26411389727_1_workflow_metadata.json`

The source monitor JSON was generated. The Markdown brief was generated. The command log and workflow metadata JSON were generated.

## Commands Observed

The command log recorded:

```bash
python3 scripts/run_hikorea_monitor_smoke.py --run-label workflow_26411389727_1 --output-dir tmp/source-monitor-smoke --allow-network
```

The helper invoked the source monitor as:

```bash
python3 scripts/check_source_updates.py --catalog-dry-run --json --list-disabled --fetch-timeout-seconds 5.0 --fetch-max-bytes 524288 --allow-network
```

The helper invoked the Markdown brief generator as:

```bash
python3 scripts/generate_source_update_brief.py --input tmp/source-monitor-smoke/workflow_26411389727_1_source_monitor.json --output tmp/source-monitor-smoke/workflow_26411389727_1_source_update_brief.md --format markdown
```

## Source Monitor Result

The generated source monitor JSON reported:

- `allow_network: true`
- mode: `catalog_dry_run`
- eligible records: 0
- disabled records: 43
- result records: 43
- state counts: `skipped=43`
- reason counts: `candidate_disabled=43`
- fetched records: 0
- blocked records: 0
- content hashes produced: none

No redirect was blocked. No response was oversized. No response timed out. No reviewed candidate URL was fetched.

## Candidate Records Tested

The five C11 URL-reviewed candidates were present in the run output, but each was skipped as `candidate_disabled`.

| Catalog | Source ID | URL | State | Reason |
| --- | --- | --- | --- | --- |
| `hikorea_source_catalog` | `hikorea_civil_petition_forms_index` | https://www.hikorea.go.kr/board/BoardApplicationListR.pt?page=1 | `skipped` | `candidate_disabled` |
| `immigration_notice_sources` | `hikorea_notice_index` | https://www.hikorea.go.kr/board/BoardNtcListR.pt?page=1 | `skipped` | `candidate_disabled` |
| `immigration_notice_sources` | `hikorea_materials_index` | https://www.hikorea.go.kr/board/BoardDataListR.pt?page=1 | `skipped` | `candidate_disabled` |
| `immigration_notice_sources` | `immigration_service_notice_index` | https://www.immigration.go.kr/immigration/1500/subview.do | `skipped` | `candidate_disabled` |
| `immigration_notice_sources` | `immigration_service_press_index` | https://www.immigration.go.kr/immigration/1502/subview.do | `skipped` | `candidate_disabled` |

## Fetched, Skipped, Blocked

- Fetched: none
- Blocked: none
- Skipped: all 43 records with `candidate_disabled`
- Redirects blocked: none
- Timeouts: none
- Oversized responses: none
- Content hashes: none produced

The generated Markdown brief reported 43 informational skipped records, 0 high-priority changes, 0 medium-priority changes, 0 review-needed records, and 0 changed records requiring review.

## Safety Confirmation

- `allow_network=true` was confirmed in workflow metadata and command log.
- No source URL was fetched, so no unreviewed URL, service portal, login page, transaction page, e-Application, visit reservation, residence-card validity check, CAPTCHA-gated flow, or personal-data flow was accessed by the source monitor.
- No GitHub Issue was created.
- No scheduled monitoring was enabled.
- No schedule or cron trigger was added.
- No automatic user-facing legal update was performed.
- No generated output was committed by the workflow.
- No production data was updated.
- No UI file was changed by this PR.
- `visa_data.json`, `backend/data/visas.json`, `doc_master.json`, and production datasets were not changed by this PR.
- Catalog `monitor_enabled` values were not changed.
- `monitor_enabled` remains `false` for all 33 records in `data/sources/hikorea_source_catalog.json`.
- `monitor_enabled` remains `false` for all 10 records in `data/sources/immigration_notice_sources.json`.

Normal GitHub Actions infrastructure network access occurred for checkout, Python setup, and artifact upload. The source-monitor safety result is that no monitored HiKorea/KIS/source-catalog HTTP fetch occurred despite allow-network mode being enabled.

## Unresolved Risk

C12 did not complete the intended reviewed-URL fetch smoke. The run suggests the adapter or smoke helper does not currently treat `activation_status="url_reviewed_candidate"` as eligible for manual smoke fetching while `monitor_enabled=false`.

That behavior is conservative and safe, but it means C11 URL review is not yet sufficient for an allow-network workflow run to fetch the public index pages.

## Next Recommended PR

C13 should make a narrow manual-smoke eligibility fix so `workflow_dispatch` runs with `allow_network=true` can fetch only records that are both reviewed URL candidates and still `monitor_enabled=false`. The fix should keep scheduled monitoring disabled, keep automatic GitHub Issue creation disabled, keep service portals and sensitive flows blocked, and add fixture-based tests before rerunning the allow-network smoke.
