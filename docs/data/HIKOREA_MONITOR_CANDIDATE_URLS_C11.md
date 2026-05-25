# HiKorea Monitor Candidate URLs C11

Report date: 2026-05-26 KST
Branch: `data/hikorea-monitor-candidate-urls-c11`

## Summary

C11 follows the C10 allow-network workflow smoke. C10 confirmed that the manual `allow_network=true` workflow completed safely, but no monitored HiKorea/Korea Immigration Service source was fetched because all five conservative monitor candidates still had `url=null`.

This PR pins stable official public index URLs for those five candidate records so a later manual allow-network smoke can test real public index fetch behavior. It does not activate monitoring, add a schedule, create issues, or authorize user-facing legal updates.

## Selected Official URLs

| Catalog | Source ID | Selected URL | Public/non-login rationale |
| --- | --- | --- | --- |
| `data/sources/hikorea_source_catalog.json` | `hikorea_civil_petition_forms_index` | https://www.hikorea.go.kr/board/BoardApplicationListR.pt?page=1 | Official HiKorea public civil-petition application-form index. The selected URL is an index/list page for monitoring metadata only, not a form submission endpoint. It does not require login, personal data input, CAPTCHA, e-Application, visit reservation, or validity-check flow access for an index snapshot. |
| `data/sources/immigration_notice_sources.json` | `hikorea_notice_index` | https://www.hikorea.go.kr/board/BoardNtcListR.pt?page=1 | Official HiKorea public notices index. The selected URL is a public list page suitable for conservative index snapshot monitoring and is not a login, transaction, e-Application, visit reservation, validity-check, or form submission flow. |
| `data/sources/immigration_notice_sources.json` | `hikorea_materials_index` | https://www.hikorea.go.kr/board/BoardDataListR.pt?page=1 | Official HiKorea public materials/data-room index. The selected URL is a public list page. File downloads remain link-only unless a later reviewed PR explicitly approves safe hash monitoring. |
| `data/sources/immigration_notice_sources.json` | `immigration_service_notice_index` | https://www.immigration.go.kr/immigration/1500/subview.do | Official Korea Immigration Service public notice index. The selected URL is a public board page suitable for index snapshot monitoring and is not a service portal or transaction flow. |
| `data/sources/immigration_notice_sources.json` | `immigration_service_press_index` | https://www.immigration.go.kr/immigration/1502/subview.do | Official Korea Immigration Service public press-release index. The selected URL is a public board page suitable for index snapshot monitoring and is not a service portal or transaction flow. |

## Catalog Changes

For each selected candidate:

- `url` was populated with the reviewed official public index URL.
- `url_review_status` was set to `operator_reviewed`.
- `url_reviewed_at` was set to `2026-05-26`.
- `url_review_note` records the public, non-login, non-transaction rationale.
- `robots_review_status` was set to `manual_review_required`.
- `rate_limit_policy` was set to `manual_smoke_only`.
- `activation_status` was set to `url_reviewed_candidate`.
- `activation_blockers` continue to block automation and activation.
- `monitor_enabled` remains `false`.

## Records Still Blocked Or Uncertain

No C11 candidate remains without a URL, but all five remain blocked from activation. The remaining blockers are:

- robots.txt and site terms have not been reviewed in this PR;
- fetching remains limited to a manual `workflow_dispatch` allow-network smoke;
- scheduled monitoring remains blocked;
- automatic GitHub Issue creation remains blocked;
- automatic user-facing legal updates remain blocked;
- `monitor_enabled` remains `false`;
- the next smoke must still confirm redirect behavior, response-size limits, timeouts, and extraction quality from workflow artifacts.

Service portals and sensitive flows remain out of scope, including login pages, e-Application, visit reservation, residence-card validity checks, CAPTCHA-gated flows, personal-data flows, and transaction flows.

## Safety Posture

C11 is URL review only. It does not claim that the linked pages are legally complete or current for user guidance. The URLs are intended only to let a future manual allow-network smoke fetch public index pages and generate human-review artifacts.

This PR does not:

- enable monitoring;
- add a schedule or cron;
- add push or pull request workflow triggers;
- create or enable GitHub Issues;
- update user-facing legal data;
- change UI files;
- modify `visa_data.json`, `backend/data/visas.json`, `doc_master.json`, or production datasets; or
- add dependencies.

## Next Recommended PR

C12 should run the manual HiKorea source monitor workflow with `allow_network=true` against these URL-reviewed candidates, then document which records were fetched, blocked, skipped, redirected, oversized, or timed out. C12 should keep `monitor_enabled=false`, avoid schedules and automatic issue creation, and continue treating the output as a human-review smoke result only.
