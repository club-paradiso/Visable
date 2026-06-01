# AI Scenario Variant Grounding Post-Merge Smoke — 2026-05

## Purpose

Post-merge hardening pass after PR #235.

This verifies that scenario/sub-code procedure variants are safely routed into Paradiso AI as needs-review local manual context, not as source-confirmed determinations.

## Context

PR #233 introduced `procedures.<key>.variants[]`.
PR #234 populated 24 scenario/sub-code variants.
PR #235 connected those variants to the AI prompt path.

This follow-up strengthens classifier coverage and adds regression tests so variant grounding does not silently disappear.

## Changes Covered

- Added / verified `activities_outside_status` detection.
- Routed explicit activities-outside-status questions to `activitiesOutsideStatus`.
- Preserved cautious statusGrant routing for explicit birth/status-grant questions only.
- Added regression tests for:
  - D-9 statusChange variant context
  - E-9 workplaceChange variant context
  - E-6 activitiesOutsideStatus variant context
  - F-1 explicit statusGrant routing
  - unrelated questions not using variant context
  - safe response metadata shape
  - `grounding_used` semantics remaining unchanged
  - D-2 registration and PR #232 reentry paths remaining available

## Safety Rule

Needs-review scenario variants remain local manual context and are not treated as source-confirmed determinations.

This work does not:
- mark variants as source-confirmed HIGH
- set `verified=true`
- remove `needsManualReview`
- remove safety disclaimers
- rewrite the AI pipeline
- add new bulk scenario variants

## Validation

To be filled after running validation.

## Known Limitations

- Browser/network smoke may still be blocked in Codespaces or sandboxed environments.
- Exact sub-code narrowing still depends on payload metadata.
- Variants remain needs-review local manual context, not final immigration-office determinations.
