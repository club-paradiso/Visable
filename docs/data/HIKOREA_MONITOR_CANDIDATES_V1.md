# HiKorea Monitor Candidates V1

Date: 2026-05-25

This note documents the first conservative candidate-only source selection for future HiKorea / Korea Immigration Service monitoring. It does not enable monitoring, schedule jobs, fetch live pages, or change user-facing legal data.

## Selection Criteria

A record was selected only when it appeared to be:

- a public official source;
- available without login;
- unrelated to personal-data entry, CAPTCHA-gated flows, or transaction workflows;
- not an e-Application, visit-reservation, office-lookup transaction, or residence-card validity check page;
- a notice index, announcement list, public materials index, or static public metadata index;
- low or medium legal/admin risk; and
- useful for human update briefing rather than automatic user-facing legal or data updates.

Selected records remain `monitor_enabled=false`. Candidate metadata only marks that a later reviewed PR may build a default-off allowlisted fetch adapter.

## Selected Candidates

| Catalog | source_id | Why selected |
|---|---|---|
| `immigration_notice_sources.json` | `hikorea_notice_index` | Primary public HiKorea announcement stream. It is a good human-review signal for portal notices once an exact public index URL is pinned. |
| `immigration_notice_sources.json` | `hikorea_materials_index` | Public materials/downloads index likely to surface manual and form publication changes. File downloads remain link-only unless separately reviewed. |
| `immigration_notice_sources.json` | `immigration_service_notice_index` | Public Korea Immigration Service notice index, useful for policy-update triage before downstream content changes. |
| `immigration_notice_sources.json` | `immigration_service_press_index` | Public Korea Immigration Service press-release index, often an early official signal for policy announcements. |
| `hikorea_source_catalog.json` | `hikorea_civil_petition_forms_index` | Public civil-petition forms metadata index. Candidate monitoring is limited to index metadata and must not submit forms or process personal data. |

Each selected record has:

- `monitor_candidate=true`
- `operator_review_required=true`
- `proposed_monitor_mode="index_snapshot"`
- `proposed_fetch_method="GET"`
- `scrape_allowed=true`
- `monitor_enabled=false`
- `robots_review_status="not_checked"`
- `rate_limit_policy="not_configured"`
- `activation_status="candidate_only"`
- explicit `activation_blockers`

## Excluded Records

High-risk guide pages were excluded because they could be misread as direct legal guidance without manual review. Examples include workplace-change, nationality, refugee, and seasonal-worker guide records.

Transaction and service records were excluded by hard rule. This includes:

- e-Application filing pages;
- visit-reservation pages;
- residence-card validity checks;
- jurisdictional office lookup services; and
- any page that could require personal data, login, CAPTCHA, booking, submission, or transaction behavior.

Link-only roots and broad portals were also excluded because a root page is not a stable content index. Examples include HiKorea root, Korea Immigration Service root, Ministry of Justice root, Visa Portal root, Soci-Net root, 1345 root, KOSIS root, and OKA root.

Statute landing pages were excluded because canonical statute monitoring should use the existing law-source path or a separately reviewed official API path, not an HTML portal snapshot.

## Activation Blockers

Before any selected candidate can move beyond `candidate_only`, a later PR must:

- pin the exact public index URL for each selected record;
- define the allowed official host for each URL;
- review robots.txt and site terms;
- configure conservative rate limits, timeout, and response-size limits;
- ensure redirects cannot escape the official allowlist;
- keep cookies, forms, JavaScript execution, login flows, and personal-data submission out of scope;
- add fixture-based tests that do not call live government services; and
- prove that detected changes generate human review briefs only.

## Proposed PR-C3 Plan

PR-C3 should add a default-off allowlisted fetch adapter that:

- performs no network I/O unless `--allow-network` is explicitly passed;
- fetches only `monitor_candidate=true` records with `activation_status` of `candidate_only` or `allowlist_test`;
- requires `scrape_allowed=true`, `requires_login=false`, an allowed source type, and an allowlisted official host;
- uses GET with a polite User-Agent, short timeout, and response-size cap;
- does not store cookies, submit forms, execute JavaScript, or follow login flows;
- extracts only basic title/text hashes for change detection; and
- is tested with local fixtures/mocks, not live HiKorea, immigration.go.kr, Visa Portal, Soci-Net, or linked services.

PR-C3 must remain default-off and must not add scheduled monitoring or GitHub Actions.
