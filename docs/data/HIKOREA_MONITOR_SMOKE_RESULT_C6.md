# HiKorea Monitor Smoke Result C6

Date: 2026-05-25
Branch: `docs/hikorea-monitor-smoke-result-c6`

## Summary

This PR-C6 smoke test exercised the current HiKorea/Korea Immigration Service source monitor pipeline using the existing manual runbook and helper:

- Runbook: `docs/data/HIKOREA_MONITOR_MANUAL_SMOKE_TEST_RUNBOOK.md`
- Helper: `scripts/run_hikorea_monitor_smoke.py`

Only the no-network smoke path was run. Live HTTP was not used. No GitHub Issues were created. Scheduled monitoring remains disabled, and all catalog `monitor_enabled` values remain `false`.

## Commands Run

```bash
python3 scripts/run_hikorea_monitor_smoke.py --run-label c6_no_network
```

```bash
python3 scripts/run_hikorea_monitor_smoke.py --run-label c6_issue_preview --issue-preview
```

The helper invoked the source monitor without `--allow-network`:

```bash
python3 scripts/check_source_updates.py --catalog-dry-run --json --list-disabled --fetch-timeout-seconds 5.0 --fetch-max-bytes 524288
```

The helper invoked the Markdown brief generator:

```bash
python3 scripts/generate_source_update_brief.py --input tmp/source-monitor-smoke/c6_no_network_source_monitor.json --output tmp/source-monitor-smoke/c6_no_network_source_update_brief.md --format markdown
```

The issue-preview run invoked the same generator with `--issue-preview`; this produced local Markdown framing only and did not create a GitHub Issue.

## Network Decision

`--allow-network` was not used.

The runbook permits an allow-network smoke only after confirming that candidate URLs are operator-pinned public notice/index URLs and remain inside official allowlisted hosts. In this checkout, all five monitor candidates remain `monitor_enabled=false`, and the candidate URLs are still not pinned (`url=null`). Because the no-network smoke already validated JSON capture, Markdown brief generation, and issue-preview behavior, the optional live HTTP path was skipped for this PR.

## Candidate Records Tested

The no-network run exercised the catalog dry-run path across both catalogs. Five monitor-candidate records reached the network gate and were skipped with `network_disabled`:

| Catalog | Source ID | URL | Result |
| --- | --- | --- | --- |
| `hikorea_source_catalog` | `hikorea_civil_petition_forms_index` | `null` | `skipped`, `network_disabled` |
| `immigration_notice_sources` | `hikorea_notice_index` | `null` | `skipped`, `network_disabled` |
| `immigration_notice_sources` | `hikorea_materials_index` | `null` | `skipped`, `network_disabled` |
| `immigration_notice_sources` | `immigration_service_notice_index` | `null` | `skipped`, `network_disabled` |
| `immigration_notice_sources` | `immigration_service_press_index` | `null` | `skipped`, `network_disabled` |

The remaining 38 catalog records were skipped as `candidate_disabled`.

## Fetch Result

No source was fetched. The smoke JSON reported:

- `allow_network: false`
- `eligible: 0`
- `results: 43`
- all results `state=skipped`
- reason counts: `candidate_disabled=38`, `network_disabled=5`
- fetched records: `0`

## Output Files Produced

The helper wrote ignored local smoke artifacts under `tmp/source-monitor-smoke/`:

- `tmp/source-monitor-smoke/c6_no_network_source_monitor.json`
- `tmp/source-monitor-smoke/c6_no_network_source_update_brief.md`
- `tmp/source-monitor-smoke/c6_issue_preview_source_monitor.json`
- `tmp/source-monitor-smoke/c6_issue_preview_source_update_brief.md`

These files are not committed. The committed summary is:

- `docs/data/HIKOREA_MONITOR_SMOKE_RESULT_C6.md`
- `docs/data/hikorea_monitor_smoke_result_c6.json`

## Brief Generator Output Summary

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

The issue-preview output began with:

```markdown
<!-- GitHub Issue preview only: no issue was created. -->
```

and ended with an issue-preview status confirming that the script does not create GitHub Issues or require a GitHub token.

## Blocked Or Skipped Sources

All 43 records were skipped in the no-network smoke:

- 38 records: `candidate_disabled`
- 5 records: `network_disabled`

The `network_disabled` records were the five monitor candidates listed above. The `candidate_disabled` records included service portals and adjacent official sources such as e-Application, visit reservation, residence-card validity check, law/statute roots, and non-candidate guide pages.

## Safety Confirmations

- No live HTTP was used.
- No forms were submitted.
- No login, CAPTCHA, e-Application, visit-reservation, validity-check, or personal-data flow was accessed.
- No GitHub Issues were created.
- No GitHub Actions were added.
- No scheduled monitoring was enabled.
- No catalog `monitor_enabled` values were changed.
- `monitor_enabled` remains `false` for all 33 records in `data/sources/hikorea_source_catalog.json`.
- `monitor_enabled` remains `false` for all 10 records in `data/sources/immigration_notice_sources.json`.
- `visa_data.json`, `backend/data/visas.json`, and production datasets were not modified.
- UI files were not modified.
- No dependencies were added.

## Next Recommended PR

Keep the next PR default-off: add a manual `workflow_dispatch` smoke workflow only if desired, with no schedule and no issue creation. The workflow should preserve the current no-network default, store JSON/Markdown artifacts for operator review, and require an explicit manual input before any allow-network smoke path is attempted.
