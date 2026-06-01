# StatusGrant Variant Routing Alias Hotfix — 2026-05

## Purpose

Follow-up hotfix after PR #236.

PR #236 expanded task detection for statusGrant-style wording, but the variant router still needed to mirror the same explicit aliases. Without this, some questions could be detected as `family_status_change` but fail to route to `statusGrant` variant context.

## Fixed Aliases

- `grant of status`
- `child status grant`
- `출생 자녀 체류`
- `국내출생 자녀 체류자격 부여`

## Safety Rule

Generic family-status questions still do not route to `statusGrant`.

Only explicit birth-child/status-grant wording can use the `statusGrant` variant path.

## Validation

To be filled after validation.
